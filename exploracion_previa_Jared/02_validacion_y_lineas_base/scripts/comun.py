"""Funciones comunes del proyecto Reto AgroCebada FIRA 2026 (Python).

Todos los scripts importan este modulo. Encuentran la carpeta FINAL solos,
asi que se pueden correr desde cualquier lugar.
"""
from pathlib import Path
import numpy as np
import pandas as pd

GRUPOS = ["Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo"]
NG = len(GRUPOS)
FAMILIAS = ["clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17"]
NO_EVALUABLES = ["HC2"]
DELTA_MIN = 0.02      # E1 (a)
N_MEJORA_MIN = 75     # E1 (b)


def _buscar_raiz():
    for p in Path(__file__).resolve().parents:
        if (p / "01_datos").is_dir() and (p / "03_hipotesis_y_variables").is_dir():
            return p
    raise RuntimeError("No encuentro la carpeta FINAL (debe tener 01_datos y 03_hipotesis_y_variables)")


RAIZ = _buscar_raiz()


def ruta(*partes):
    return RAIZ.joinpath(*partes)


# ----------------------------------------------------------------------------
# Datos
# ----------------------------------------------------------------------------
def carga_base():
    """Las 138 parcelas de entrenamiento. Devuelve (DataFrame, y, g, ids)."""
    base = pd.read_csv(ruta("01_datos", "preparados", "base_138.csv"))
    assert len(base) == 138 and base["RENDIMIENTO_T_HA"].notna().all()
    base["g"] = base["grupo"].map({n: i for i, n in enumerate(GRUPOS)})
    assert base["g"].notna().all() and base["celda_clima"].notna().all()
    base["g"] = base["g"].astype(int)
    return base, base["RENDIMIENTO_T_HA"].to_numpy(float), base["g"].to_numpy(), base["ID_POLIGONO"].tolist()


def carga_ubicacion():
    return pd.read_csv(ruta("01_datos", "preparados", "base_197_ubicacion.csv"))


def carga_particiones(nombre, ids):
    """Lista de dicts con indices (posicion en base_138) de ajuste y validacion."""
    f = pd.read_csv(ruta("01_datos", "preparados", f"folds_{nombre}.csv"))
    pos = {k: i for i, k in enumerate(ids)}
    out = []
    for rep, fk in f.groupby("rep", sort=True):
        d = {"rep": int(rep),
             "fit": np.array([pos[i] for i in fk.loc[fk["rol"] == "ajuste", "ID_POLIGONO"]]),
             "val": np.array([pos[i] for i in fk.loc[fk["rol"] == "validacion", "ID_POLIGONO"]])}
        if "grupo_fuera" in fk.columns:
            d["grupo_fuera"] = fk["grupo_fuera"].iloc[0]
        out.append(d)
    return out


def carga_variables(ids):
    """Las 148 variables candidatas, estandarizadas con las 197 parcelas.

    Devuelve (X de las 138, tabla de hipotesis lineales, F197 sin estandarizar, Z de las 197).
    """
    base_dir = ruta("03_hipotesis_y_variables", "variables")
    feats = [pd.read_csv(base_dir / f"{f}_features.csv") for f in FAMILIAS]
    F = feats[0]
    for d in feats[1:]:
        F = F.merge(d, on="ID_POLIGONO", how="left")
    assert len(F) == 197 and not F.columns.duplicated().any()
    hips = []
    for fam in FAMILIAS:
        h = pd.read_csv(base_dir / f"{fam}_hipotesis.csv", dtype=str, keep_default_na=False)
        h["familia"] = fam
        h["variables"] = h["variables"].str.replace(r"\s+", "", regex=True)
        hips.append(h)
    hip = pd.concat(hips, ignore_index=True)
    lin = hip[(hip["spec"] == "lineal") & (~hip["id"].isin(NO_EVALUABLES))].copy()
    lin["variables"] = lin["variables"].str.split(";")
    lin = lin.explode("variables").rename(columns={"variables": "variable"})
    lin = lin[lin["variable"] != ""][["id", "familia", "variable", "signo"]]
    lin = lin.drop_duplicates("variable", keep="first").reset_index(drop=True)
    assert set(lin["variable"]) <= set(F.columns)
    Z = F.set_index("ID_POLIGONO")[lin["variable"]]
    Z = (Z - Z.mean()) / Z.std(ddof=1)
    X = Z.loc[ids].to_numpy(float)
    if np.isnan(X).any():
        raise ValueError("Hay NA en las variables de las 138 parcelas")
    return X, lin, hip, F, Z


# ----------------------------------------------------------------------------
# Nucleo: rendimiento ~ grupo + variable (pendiente comun), calculado a mano
# ----------------------------------------------------------------------------
def medias_g(M, g):
    M = np.asarray(M, float)
    out = np.full((NG,) + M.shape[1:], np.nan)
    for k in range(NG):
        m = g == k
        if m.any():
            out[k] = M[m].mean(axis=0)
    return out


def rmse(e):
    return float(np.sqrt(np.mean(np.square(e))))


def nucleo(X, y, g, fit, val):
    gF, gV = g[fit], g[val]
    cnt = np.bincount(gF, minlength=NG)
    if np.any(cnt[np.unique(gV)] == 0):
        raise ValueError("Un grupo de validacion no esta en el ajuste")
    MY = medias_g(y[fit], gF)
    MX = medias_g(X[fit], gF)
    Xc = X[fit] - MX[gF]
    yc = y[fit] - MY[gF]
    sxy = Xc.T @ yc
    sxx = (Xc ** 2).sum(axis=0)
    syy = float((yc ** 2).sum())
    beta = np.where(sxx > 1e-12, sxy / np.where(sxx > 1e-12, sxx, 1.0), 0.0)
    pB2 = MY[gV]
    yV = y[val]
    Xv = X[val] - MX[gV]
    err = yV[:, None] - (pB2[:, None] + Xv * beta)
    return {"b2": rmse(yV - pB2), "rm": np.sqrt((err ** 2).mean(axis=0)),
            "r": sxy / np.sqrt(np.maximum(sxx * syy, 1e-24)),
            "Xc": Xc, "yc": yc, "Xv": Xv, "pB2": pB2, "yV": yV, "MX": MX, "MY": MY, "gF": gF, "gV": gV}


def top_k(nu, cols, k):
    """RMSE de validacion usando las k variables con mayor |r| dentro de grupo en el ajuste."""
    cols = np.asarray(cols)
    o = cols[np.argsort(-np.abs(nu["r"][cols]), kind="stable")[:k]]
    if k == 1:
        return float(nu["rm"][o[0]])
    A = nu["Xc"][:, o]
    try:
        b = np.linalg.solve(A.T @ A, A.T @ nu["yc"])
    except np.linalg.LinAlgError:
        return np.nan
    return rmse(nu["yV"] - (nu["pB2"] + nu["Xv"][:, o] @ b))


def corre_esquema(P, y, g, X, idx_fam=None, con_seleccion=False):
    """RMSE de B2 y de cada variable en todas las particiones de un esquema."""
    R, K = len(P), X.shape[1]
    b2 = np.zeros(R)
    rm = np.zeros((R, K))
    sel = None
    if con_seleccion:
        nombres = ["top1_global", "top3_global"] + [f"top1_{f}" for f in FAMILIAS]
        sel = {n: np.full(R, np.nan) for n in nombres}
    for i, p in enumerate(P):
        nu = nucleo(X, y, g, p["fit"], p["val"])
        b2[i], rm[i] = nu["b2"], nu["rm"]
        if con_seleccion:
            sel["top1_global"][i] = top_k(nu, np.arange(K), 1)
            sel["top3_global"][i] = top_k(nu, np.arange(K), 3)
            for f in FAMILIAS:
                sel[f"top1_{f}"][i] = top_k(nu, idx_fam[f], 1)
    return {"b2": b2, "rm": rm, "sel": sel}


def resume_delta(E):
    d = E["b2"][:, None] - E["rm"]
    return {"media": d.mean(axis=0), "n_mejora": (d > 0).sum(axis=0), "rmse": E["rm"].mean(axis=0)}


def veredicto(a, b, c):
    if not (a and b):
        return "descartar"
    return "pasa E1" if c else "solo con vecinos (falla c)"


# ----------------------------------------------------------------------------
# Utilidades de salida
# ----------------------------------------------------------------------------
class _Tee:
    def __init__(self, *flujos):
        self.flujos = flujos

    def write(self, s):
        for f in self.flujos:
            f.write(s)

    def flush(self):
        for f in self.flujos:
            f.flush()


def iniciar_log(nombre):
    """Todo lo que se imprima tambien se guarda en 04_resultados/logs/<nombre>.log"""
    import sys
    d = ruta("04_resultados", "logs")
    d.mkdir(parents=True, exist_ok=True)
    f = open(d / f"{nombre}.log", "w", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, f)
    return f


def compara_con_R(df_py, nombre_ref, claves, columnas, tol=1e-6):
    """Compara columnas numericas con el CSV que produjo R (04_resultados/referencia_R)."""
    ref = pd.read_csv(ruta("04_resultados", "referencia_R", nombre_ref))
    a = df_py.sort_values(claves).reset_index(drop=True)
    b = ref.sort_values(claves).reset_index(drop=True)
    if len(a) != len(b):
        return f"{nombre_ref}: DISTINTO NUMERO DE FILAS ({len(a)} contra {len(b)})", False
    peor = 0.0
    for c in columnas:
        x = pd.to_numeric(a[c], errors="coerce").to_numpy(float)
        z = pd.to_numeric(b[c], errors="coerce").to_numpy(float)
        if not np.array_equal(np.isnan(x), np.isnan(z)):
            return f"{nombre_ref}: valores vacios distintos en {c}", False
        m = ~np.isnan(x)
        if m.any():
            peor = max(peor, float(np.abs(x[m] - z[m]).max()))
    return f"{nombre_ref}: diferencia maxima contra R = {peor:.2e} ({'OK' if peor <= tol else 'REVISAR'})", peor <= tol
