"""Recetas del modelo final (E_JK) copiadas del cuaderno 04, sin cambios de cálculo.

Origen: `scripts/construir_notebook_04.py`, celda «recetas». Las funciones `kfold`, `internas`,
`referencias`, `residuos_mix`, `ajustar_beta`, `corregir` y `jared` son copia literal. `ajustar`
equivale a `candidatos(tr, va, intern)`, con los datos como argumentos en lugar de globales.

La copia se vigila con `api/verificar.py` y `api/tests/`: reentrenar con las 138 parcelas debe
producir `resultados/04_seleccion_modelo_final/predicciones_59.csv` byte a byte (misma SHA-256).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ID, Y = "ID_POLIGONO", "RENDIMIENTO_T_HA"
SEMILLA_FINAL = 20261015  # semilla de los 4 pliegues internos de K en el ajuste final (cuaderno 04, sección 7)


def kfold(n, k, semilla):
    """Igual que sklearn.model_selection.KFold(k, shuffle=True, random_state=semilla): índices ordenados de entrenamiento y validación."""
    idx = np.arange(n)
    np.random.RandomState(semilla).shuffle(idx)
    tam = np.full(k, n // k)
    tam[: n % k] += 1
    ini = 0
    for t in tam:
        m = np.zeros(n, bool)
        m[idx[ini:ini + t]] = True
        ini += t
        yield np.flatnonzero(~m), np.flatnonzero(m)


def internas(ids, semilla, k=4):
    """Pliegues internos (solo IDs del entrenamiento) para obtener residuos honestos de MIX."""
    ids, filas = np.array(sorted(ids)), []
    for p, (a, b) in enumerate(kfold(len(ids), k, semilla)):
        filas += [(p, "entrenamiento", i) for i in ids[a]] + [(p, "validacion", i) for i in ids[b]]
    return pd.DataFrame(filas, columns=["pliegue_interno", "rol", ID])


def referencias(a, v):
    """MUN y MIX. a: entrenamiento con Municipio, x_m, y_m y rendimiento; v: validación SIN rendimiento."""
    assert Y not in v
    media = a[Y].mean()
    mun = v.Municipio.map(a.groupby("Municipio")[Y].mean()).fillna(media).to_numpy()
    d = np.linalg.norm(v[["x_m", "y_m"]].to_numpy()[:, None, :] - a[["x_m", "y_m"]].to_numpy()[None, :, :], axis=2)
    idx = np.argsort(d, axis=1)[:, : min(20, len(a))]
    w = 1 / np.maximum(np.take_along_axis(d, idx, axis=1), 1.0) ** 2
    w /= w.sum(axis=1, keepdims=True)
    idw = (w * a[Y].to_numpy()[idx]).sum(axis=1)
    return {"MUN": mun, "MIX": 0.5 * mun + 0.5 * idw}


def residuos_mix(a, intern):
    """e = y − MIX para cada parcela del entrenamiento, predicha sin su propia etiqueta."""
    t = a.set_index(ID)
    e = pd.Series(np.nan, index=t.index)
    for _, g in intern.groupby("pliegue_interno"):
        ai = t.loc[g.loc[g.rol.eq("entrenamiento"), ID]].reset_index()
        vi = g.loc[g.rol.eq("validacion"), ID].to_numpy()
        e.loc[vi] = t.loc[vi, Y].to_numpy(float) - referencias(ai, t.loc[vi].drop(columns=Y).reset_index())["MIX"]
    assert not e.isna().any()
    return e


def ajustar_beta(z, e, alpha=10.0):
    """β = Σ z̃·e / (Σ z̃² + α), z̃ estandarizado con mediana y desviación de las filas de entrenamiento con K1."""
    x = z.reindex(e.index).to_numpy(float)
    ok = np.isfinite(x)
    med, sd = float(np.median(x[ok])), float(np.std(x[ok], ddof=1))
    zz = (x[ok] - med) / sd
    return {"mediana": med, "escala": sd, "beta": float(zz @ e.to_numpy(float)[ok] / (zz @ zz + alpha)), "n_ajuste": int(ok.sum())}


def corregir(p, z, ids):
    """Corrección de K; sin K1 → 0 (la parcela recibe MIX)."""
    x = z.reindex(ids).to_numpy(float)
    return np.where(np.isfinite(x), p["beta"] * (x - p["mediana"]) / p["escala"], 0.0)


def jared(Fx, grupo, y, tr, va):
    """Elige la variable con mayor |correlación| dentro de grupo usando SOLO el entrenamiento; luego MCO con un nivel por grupo + una pendiente."""
    gtr, gva = grupo.loc[tr].to_numpy(), grupo.loc[va].to_numpy()
    ytr = y.loc[tr].to_numpy(float)
    X = Fx.loc[tr].to_numpy(float)
    niveles = sorted(set(gtr))
    yc, Xc = ytr.copy(), X.copy()
    for g in niveles:
        m = gtr == g
        yc[m] -= ytr[m].mean()
        Xc[m] -= X[m].mean(0)
    r = (Xc * yc[:, None]).sum(0) / np.sqrt(np.maximum((Xc ** 2).sum(0) * (yc ** 2).sum(), 1e-24))
    j = int(np.argmax(np.abs(r)))
    D = lambda x, g: np.column_stack([(g[:, None] == np.array(niveles)[None]).astype(float), x[:, None]])  # noqa: E731
    b = np.linalg.lstsq(D(X[:, j], gtr), ytr, rcond=None)[0]
    return D(Fx.loc[va].to_numpy(float)[:, j], gva) @ b, Fx.columns[j], dict(zip(niveles + ["pendiente"], b))


def ajustar(T, y, FX, tr, va, intern):
    """MUN, MIX, J, K y E_JK para va, entrenados con tr (equivale a `candidatos` del cuaderno 04). va nunca recibe rendimientos."""
    a = T.loc[tr, ["Municipio", "x_m", "y_m"]].assign(**{Y: y.loc[tr].to_numpy()}).reset_index()
    v = T.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
    ref = referencias(a, v)
    pb = ajustar_beta(T.K1_corregido, residuos_mix(a, intern))
    k = ref["MIX"] + corregir(pb, T.K1_corregido, np.asarray(va))
    j, var, coef = jared(FX, T.grupo, y, np.asarray(tr), np.asarray(va))
    return {"MUN": ref["MUN"], "MIX": ref["MIX"], "J": j, "K": k, "E_JK": 0.5 * j + 0.5 * k}, {"K": pb, "J_variable": var, "J_coef": coef}


def csv_entrega(pred: pd.DataFrame) -> str:
    """Mismo formato que `predicciones_59.csv`: columnas ID_POLIGONO y RENDIMIENTO_T_HA, 4 decimales."""
    return pred[["E_JK"]].rename(columns={"E_JK": Y}).to_csv(float_format="%.4f")
