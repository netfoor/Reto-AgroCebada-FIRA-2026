"""Prueba final independiente (Claude Opus, 11 oct 2026): biblioteca común.

Reglas de uso:
- Las X de las 197 parcelas se pueden usar siempre (no contienen rendimientos).
- Los rendimientos solo se leen con `etiquetas_desarrollo()`, que descarta la caja cerrada al leer.
- `etiquetas_caja()` solo se llama en 03_evaluar_caja.py, una vez.
- Los candidatos congelados usan las implementaciones del proyecto (importadas, sin modificarlas).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import cho_factor, cho_solve
from scipy.optimize import minimize
from sklearn.model_selection import KFold

sys.dont_write_bytecode = True                      # no escribir .pyc dentro de scripts/ del proyecto
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ / "scripts"))
from modelo_10 import predecir_fold                   # noqa: E402  receta K (EXP_10), sin cambios
from preparar_exp_11 import jared_completo, variables_jared_crudas  # noqa: E402  receta J (EXP_11)
from validacion_03 import predecir_referencias        # noqa: E402  receta MUN/MIX

ID, Y = "ID_POLIGONO", "RENDIMIENTO_T_HA"
ZIP_SHA = "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"
SEMILLA_CAJA = 20261011
SEMILLA_CV = 20261012            # distinta de 20261009 (EXP_09) y de la histórica 20260920
SEMILLA_BOOT = 20261013
SEMILLA_CAJA_INTERNA = 20261014  # pliegues internos de K al entrenar con las 103 de desarrollo
FRACCION_CAJA = 0.25
N_REP, N_PLIEGUES, N_INTERNOS = 10, 5, 4


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------ X (sin rendimientos)
def tabla_x() -> pd.DataFrame:
    """197 parcelas: municipio, conjunto, coordenadas UTM, grupo de Jared, celda CHIRPS, K1 corregido, área."""
    m = pd.read_csv(RAIZ / "data/exp_10_verificacion_contraste_vecinal/metadatos.csv")
    v = pd.read_csv(RAIZ / "data/exp_10_verificacion_contraste_vecinal/variables_197.csv")[[ID, "K1_corregido"]]
    g = pd.read_csv(RAIZ / "data/exp_04_lluvia_octubre/grupos.csv")[[ID, "Estado", "grupo_J5", "celda_centroide"]]
    a = pd.read_csv(RAIZ / "data/referencias/variables_v0_197.csv", usecols=[ID, "AREA_HA"])
    t = m.merge(v, on=ID).merge(g, on=ID).merge(a, on=ID).rename(columns={"grupo_J5": "grupo", "celda_centroide": "celda"})
    t["log_area"] = np.log(t.AREA_HA)
    assert len(t) == 197 and t[ID].is_unique and not any("RENDIMIENTO" in c for c in t.columns)
    return t.sort_values(ID).reset_index(drop=True)


def sortear_caja(tx: pd.DataFrame) -> list[str]:
    """Estratificado por municipio (solo X): k = floor(0.25·n + 0.5) si n ≥ 3; municipios con n < 3 quedan en desarrollo.
    Orden reproducible: municipios alfabéticos, IDs ordenados, un solo generador."""
    rng = np.random.default_rng(SEMILLA_CAJA)
    lab = tx[tx.CONJUNTO.eq("ENTRENAMIENTO")]
    caja = []
    for mun, g in lab.groupby("Municipio", sort=True):
        n = len(g)
        k = int(np.floor(FRACCION_CAJA * n + 0.5)) if n >= 3 else 0
        if k:
            caja += list(rng.choice(np.sort(g[ID].to_numpy()), size=k, replace=False))
    return sorted(caja)


def hash_lista(ids) -> str:
    return hashlib.sha256(",".join(sorted(ids)).encode()).hexdigest()


# ------------------------------------------------------------------ etiquetas (con caja cerrada)
def _etiquetas_zip() -> pd.DataFrame:
    zp = RAIZ / "data/raw/DataSet.zip"
    if sha(zp) != ZIP_SHA:
        raise ValueError("DataSet.zip distinto")
    z = zipfile.ZipFile(zp)
    e = pd.read_csv(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv")), encoding="utf-8-sig")
    return e[[ID, Y]].dropna()


def caja_registrada() -> list[str]:
    reg = json.loads((AQUI / "registro_previo.json").read_text())
    ids = reg["caja_cerrada"]["ids"]
    if hash_lista(ids) != reg["caja_cerrada"]["sha256_lista"]:
        raise ValueError("La lista de la caja no coincide con su hash registrado")
    return ids


def etiquetas_desarrollo() -> pd.Series:
    """Rendimientos de las parcelas de desarrollo. La caja se descarta inmediatamente al leer."""
    caja = set(caja_registrada())
    e = _etiquetas_zip()
    e = e[~e[ID].isin(caja)]
    assert not (set(e[ID]) & caja) and len(e) == 138 - len(caja)
    return e.set_index(ID)[Y].sort_index()


def etiquetas_caja() -> pd.Series:
    """Solo para la evaluación final (03_evaluar_caja.py)."""
    caja = set(caja_registrada())
    e = _etiquetas_zip()
    return e[e[ID].isin(caja)].set_index(ID)[Y].sort_index()


# ------------------------------------------------------------------ particiones nuevas (solo IDs)
def particiones_desarrollo(ids_dev) -> tuple[pd.DataFrame, pd.DataFrame]:
    ids = np.array(sorted(ids_dev))
    ext, inn = [], []
    for r in range(N_REP):
        for f, (a, b) in enumerate(KFold(N_PLIEGUES, shuffle=True, random_state=SEMILLA_CV + r).split(ids)):
            ext += [(r, f, "entrenamiento", i) for i in ids[a]] + [(r, f, "validacion", i) for i in ids[b]]
            tr = np.sort(ids[a])
            for k, (c, d) in enumerate(KFold(N_INTERNOS, shuffle=True, random_state=SEMILLA_CV + 1000 + 10 * r + f).split(tr)):
                inn += [(r, f, k, "entrenamiento", i) for i in tr[c]] + [(r, f, k, "validacion", i) for i in tr[d]]
    return (pd.DataFrame(ext, columns=["repeticion", "pliegue", "rol", ID]),
            pd.DataFrame(inn, columns=["repeticion", "pliegue", "pliegue_interno", "rol", ID]))


def internas_unicas(ids_tr, semilla) -> pd.DataFrame:
    tr = np.array(sorted(ids_tr))
    filas = []
    for k, (c, d) in enumerate(KFold(N_INTERNOS, shuffle=True, random_state=semilla).split(tr)):
        filas += [(k, "entrenamiento", i) for i in tr[c]] + [(k, "validacion", i) for i in tr[d]]
    return pd.DataFrame(filas, columns=["pliegue_interno", "rol", ID])


# ------------------------------------------------------------------ candidatos congelados (recetas exactas)
_FX = None


def _jared_x():
    global _FX
    if _FX is None:
        _FX = variables_jared_crudas()[0]
    return _FX


def congelados(tx: pd.DataFrame, y: pd.Series, tr, va, internas_fold: pd.DataFrame) -> dict:
    """MUN, MIX, K = MIX + K1 corregido (α=10), J = Jared procedimiento completo, E_JK = ½J + ½K."""
    t = tx.set_index(ID)
    a = t.loc[tr, ["Municipio", "x_m", "y_m"]].assign(**{Y: y.loc[tr].to_numpy()}).reset_index()
    v = t.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
    preds, _, _ = predecir_fold(a, v, internas_fold, {"K": t["K1_corregido"]})
    ref = predecir_referencias(a, v)
    assert np.array_equal(ref["MIX"], preds["MIX"]) and np.array_equal(ref["MUN"], preds["MUN"])
    j, _ = jared_completo(_jared_x(), t["grupo"], y, np.asarray(tr), np.asarray(va))
    return {"MUN": preds["MUN"], "MIX": preds["MIX"], "J": j, "K": preds["K"], "E_JK": 0.5 * j + 0.5 * preds["K"]}


# ------------------------------------------------------------------ modelo mixto jerárquico (REML)
class ModeloMixto:
    """y = X·β + Σ_l u_l[nivel] + g(ubicación) + ε, con u_l ~ N(0, σ²_l), g ~ PG(0, σ²_s·exp(−d/ρ)), ε ~ N(0, σ²_e).
    X: un nivel fijo por grupo (5) + covariables estandarizadas con el entrenamiento.
    Varianzas (y ρ) por máxima verosimilitud restringida (REML); predicción = BLUP."""

    LIM_VAR = (np.log(1e-6), np.log(5.0))
    LIM_RHO = (np.log(50.0), np.log(20000.0))

    def __init__(self, aleatorios=("Municipio", "celda"), gp=False, covariables=()):
        self.aleatorios, self.gp, self.covariables = tuple(aleatorios), gp, tuple(covariables)

    def _fijas(self, df):
        G = (df["grupo"].to_numpy()[:, None] == np.array(self.grupos_)[None]).astype(float)
        cols = [G]
        for c in self.covariables:
            x = df[c].to_numpy(float)
            z = (x - self.centro_[c]) / self.escala_[c]
            cols.append(np.where(np.isfinite(z), z, 0.0)[:, None])   # sin dato → 0 (como K)
        return np.column_stack(cols)

    def _cov(self, th, A, D, n):
        V = np.zeros((n, n))
        for k, Ak in enumerate(A):
            V += np.exp(th[k]) * Ak
        i = len(A)
        if self.gp:
            V += np.exp(th[i]) * np.exp(-D / np.exp(th[i + 1]))
            i += 2
        V[np.diag_indices(n)] += np.exp(th[i])
        return V

    def _reml(self, th, A, D, X, y):
        n = len(y)
        try:
            L = cho_factor(self._cov(th, A, D, n), lower=True)
            VX, Vy = cho_solve(L, X), cho_solve(L, y)
            XVX = X.T @ VX
            L2 = cho_factor(XVX, lower=True)
            b = cho_solve(L2, X.T @ Vy)
            r = y - X @ b
            return 0.5 * (2 * np.log(np.diag(L[0])).sum() + 2 * np.log(np.diag(L2[0])).sum() + r @ cho_solve(L, r))
        except np.linalg.LinAlgError:
            return 1e10

    def fit(self, df: pd.DataFrame, y: np.ndarray):
        y = np.asarray(y, float)
        self.grupos_ = sorted(df["grupo"].unique())
        self.centro_, self.escala_ = {}, {}
        for c in self.covariables:
            x = df[c].to_numpy(float)
            x = x[np.isfinite(x)]
            if c == "K1_corregido":                    # misma estandarización robusta que K
                self.centro_[c], self.escala_[c] = float(np.median(x)), float(np.std(x, ddof=1))
            else:
                self.centro_[c], self.escala_[c] = float(np.mean(x)), float(np.std(x, ddof=1))
        X = self._fijas(df)
        self.niveles_ = {a: df[a].to_numpy() for a in self.aleatorios}
        A = [(v[:, None] == v[None]).astype(float) for v in self.niveles_.values()]
        self.xy_ = df[["x_m", "y_m"]].to_numpy(float)
        D = np.linalg.norm(self.xy_[:, None] - self.xy_[None], axis=2) if self.gp else None
        s2 = float(np.var(y))
        inicios = []
        for f_ale in (0.1, 0.4):
            for f_e in (0.3, 0.8):
                base = [np.log(f_ale * s2)] * len(A)
                if self.gp:
                    for rho in (300.0, 2000.0):
                        inicios.append(base + [np.log(0.2 * s2), np.log(rho), np.log(f_e * s2)])
                else:
                    inicios.append(base + [np.log(f_e * s2)])
        lims = [self.LIM_VAR] * len(A) + ([self.LIM_VAR, self.LIM_RHO] if self.gp else []) + [self.LIM_VAR]
        mejor = None
        for th0 in inicios:
            th0 = np.clip(th0, [lo for lo, _ in lims], [hi for _, hi in lims])
            res = minimize(self._reml, th0, args=(A, D, X, y), method="L-BFGS-B", bounds=lims)
            if mejor is None or res.fun < mejor.fun:
                mejor = res
        self.theta_ = mejor.x
        V = self._cov(self.theta_, A, D, len(y))
        L = cho_factor(V, lower=True)
        VX = cho_solve(L, X)
        self.beta_ = np.linalg.solve(X.T @ VX, X.T @ cho_solve(L, y))
        self.alfa_ = cho_solve(L, y - X @ self.beta_)
        self.n_grupo_ = df["grupo"].value_counts()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        X = self._fijas(df)
        fijo = X @ self.beta_
        ausente = ~df["grupo"].isin(self.grupos_).to_numpy()
        if ausente.any():                              # grupo no visto: media de niveles ponderada por tamaño
            w = self.n_grupo_.reindex(self.grupos_).to_numpy(float)
            fijo[ausente] = (w @ self.beta_[: len(self.grupos_)]) / w.sum() + X[ausente, len(self.grupos_):] @ self.beta_[len(self.grupos_):]
        K = np.zeros((len(df), len(self.alfa_)))
        for k, a in enumerate(self.aleatorios):
            K += np.exp(self.theta_[k]) * (df[a].to_numpy()[:, None] == self.niveles_[a][None])
        if self.gp:
            i = len(self.aleatorios)
            d = np.linalg.norm(df[["x_m", "y_m"]].to_numpy(float)[:, None] - self.xy_[None], axis=2)
            K += np.exp(self.theta_[i]) * np.exp(-d / np.exp(self.theta_[i + 1]))
        return fijo + K @ self.alfa_

    def varianzas(self) -> dict:
        nombres = [f"var_{a}" for a in self.aleatorios] + (["var_gp", "rango_gp_m"] if self.gp else []) + ["var_residual"]
        vals = [float(np.exp(v)) for v in self.theta_]
        return dict(zip(nombres, vals))


# Familias propias (recetas fijas, declaradas en el registro previo)
FAMILIAS = {
    "F1": dict(aleatorios=("Municipio", "celda"), gp=False, covariables=()),
    "F2": dict(aleatorios=("Municipio", "celda"), gp=False, covariables=("K1_corregido",)),
    "F3": dict(aleatorios=("Municipio", "celda"), gp=True, covariables=("K1_corregido",)),
    "F5": dict(aleatorios=("Municipio", "celda"), gp=False, covariables=("K1_corregido", "log_area")),
}


def familias_propias(tx: pd.DataFrame, y: pd.Series, tr, va, congel: dict) -> tuple[dict, dict]:
    t = tx.set_index(ID)
    a, v = t.loc[tr].reset_index(), t.loc[va].reset_index()
    out, info = {}, {}
    for nombre, cfg in FAMILIAS.items():
        m = ModeloMixto(**cfg).fit(a, y.loc[tr].to_numpy())
        out[nombre] = m.predict(v)
        info[nombre] = m.varianzas()
    out["F4"] = (congel["J"] + congel["K"] + out["F2"]) / 3.0       # ensamble de pesos iguales
    return out, info


# ------------------------------------------------------------------ métricas
def metricas(y, p) -> dict:
    y, p = np.asarray(y, float), np.asarray(p, float)
    e = p - y
    sst = float(((y - y.mean()) ** 2).sum())
    return {"n": int(len(e)), "RMSE": float(np.sqrt(np.mean(e ** 2))), "MAE": float(np.mean(np.abs(e))),
            "R2": float(1 - (e @ e) / sst) if sst > 0 else np.nan}


# ------------------------------------------------------------------ familias añadidas tras la CV de desarrollo (F6, F7)
def idw_valores(xy_tr: np.ndarray, v_tr: np.ndarray, xy_va: np.ndarray, k: int = 20, p: float = 2.0) -> np.ndarray:
    """Misma aritmética que el IDW de validacion_03 (k vecinos, potencia 2, piso de 1 m)."""
    d = np.linalg.norm(xy_va[:, None, :] - xy_tr[None, :, :], axis=2)
    idx = np.argsort(d, axis=1)[:, : min(k, len(v_tr))]
    w = 1 / np.maximum(np.take_along_axis(d, idx, axis=1), 1.0) ** p
    w /= w.sum(axis=1, keepdims=True)
    return (w * np.asarray(v_tr, float)[idx]).sum(axis=1)


def regresion_kriging_jared(tx: pd.DataFrame, y: pd.Series, tr, va, internas_fold: pd.DataFrame) -> np.ndarray:
    """F6 = J(validación) + 0.5·IDW de los residuos de J en el entrenamiento, obtenidos sin su etiqueta
    con los pliegues internos (cada residuo viene de un J ajustado sin esa parcela)."""
    t = tx.set_index(ID)
    fx, grupo = _jared_x(), t["grupo"]
    j_va, _ = jared_completo(fx, grupo, y, np.asarray(tr), np.asarray(va))
    e = pd.Series(np.nan, index=np.asarray(tr))
    for _, g in internas_fold.groupby("pliegue_interno"):
        itr = g.loc[g.rol.eq("entrenamiento"), ID].to_numpy()
        iva = g.loc[g.rol.eq("validacion"), ID].to_numpy()
        p, _ = jared_completo(fx, grupo, y, itr, iva)
        e.loc[iva] = y.loc[iva].to_numpy() - p
    if e.isna().any():
        raise ValueError("Residuo interno de J ausente")
    r = idw_valores(t.loc[e.index, ["x_m", "y_m"]].to_numpy(float), e.to_numpy(), t.loc[va, ["x_m", "y_m"]].to_numpy(float))
    return j_va + 0.5 * r
