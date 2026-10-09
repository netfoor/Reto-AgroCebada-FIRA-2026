"""EXP_11: validación de componentes, mezclas fijas 50/50 y diagnósticos. Funciones puras."""

from __future__ import annotations

import numpy as np
import pandas as pd

ID = "ID_POLIGONO"
CLAVE = ["conjunto", "repeticion", "pliegue", ID]
COMPONENTES = ["MIX", "MUN", "J", "K"]
MEZCLAS = {"E_JK": ("J", "K"), "E_MK": ("MUN", "K")}
PESO = 0.5


def validar_componentes(df: pd.DataFrame, modelos=COMPONENTES) -> None:
    """Clave única, mismas filas por modelo, mismas etiquetas/máscaras y predicciones finitas."""
    req = set(CLAVE) | {"modelo", "predicho", "observado", "Municipio", "municipio_visto"}
    if not req <= set(df):
        raise ValueError("Faltan columnas")
    if df[list(req)].isna().any().any():
        raise ValueError("Valores faltantes")
    if not np.isfinite(df.predicho.to_numpy(float)).all() or not np.isfinite(df.observado.to_numpy(float)).all():
        raise ValueError("Valores no finitos")
    if df.duplicated(CLAVE + ["modelo"]).any():
        raise ValueError("Clave duplicada")
    if set(df.modelo) != set(modelos):
        raise ValueError("Modelos inesperados")
    claves = {m: set(map(tuple, g[CLAVE].to_numpy())) for m, g in df.groupby("modelo")}
    ref = claves[modelos[0]]
    if any(c != ref for c in claves.values()):
        raise ValueError("Las filas no coinciden entre modelos")
    atrib = df.groupby(CLAVE)[["observado", "Municipio", "municipio_visto"]].nunique()
    if (atrib > 1).any().any():
        raise ValueError("Etiqueta, municipio o máscara distinta entre modelos")


def validar_particiones(df: pd.DataFrame, externas: dict) -> None:
    """Las filas de cada (conjunto, repetición, pliegue) son exactamente su validación exterior."""
    filas = set(map(tuple, df[CLAVE].drop_duplicates().to_numpy()))
    esperadas = set()
    for cj, e in externas.items():
        v = e[e.rol.eq("validacion")]
        esperadas |= {(cj, int(r), int(f), i) for r, f, i in v[["repeticion", "pliegue", ID]].to_numpy()}
    if filas != esperadas:
        raise ValueError("Las filas no coinciden con las particiones originales")


def ancho(df: pd.DataFrame) -> pd.DataFrame:
    w = df.pivot(index=CLAVE, columns="modelo", values="predicho")
    attr = df.drop_duplicates(CLAVE).set_index(CLAVE)[["observado", "Municipio", "municipio_visto"]]
    return w.join(attr).reset_index()


def mezclar(w: pd.DataFrame, a: str, b: str, peso=PESO) -> np.ndarray:
    """Promedio de predicciones completas (no de correcciones)."""
    return peso * w[a].to_numpy(float) + (1 - peso) * w[b].to_numpy(float)


def agregar_mezclas(w: pd.DataFrame) -> pd.DataFrame:
    w = w.copy()
    for n, (a, b) in MEZCLAS.items():
        w[n] = mezclar(w, a, b)
    return w


def metricas(y, p) -> dict:
    e = np.asarray(p, float) - np.asarray(y, float)
    return {"n_oof": int(len(e)), "RMSE": float(np.sqrt(np.mean(e ** 2))), "MAE": float(np.mean(np.abs(e)))}


def contribuciones(w: pd.DataFrame, cand: str, ref: str) -> pd.Series:
    """Δ SSE por parcela sumado sobre repeticiones; orden declarado: ascendente (más favorecida primero),
    empates por ID ascendente."""
    d = ((w[cand] - w.observado) ** 2 - (w[ref] - w.observado) ** 2).groupby(w[ID]).sum()
    return d.reset_index().sort_values([0, ID], kind="mergesort").set_index(ID)[0]


def sensibilidad(w: pd.DataFrame, cand: str, ref: str, k: int) -> dict:
    d = contribuciones(w, cand, ref)
    quitar = list(d.index[:k])
    ww = w[~w[ID].isin(quitar)]
    rc, rr = metricas(ww.observado, ww[cand])["RMSE"], metricas(ww.observado, ww[ref])["RMSE"]
    return {"retiradas": k, "parcelas": ";".join(quitar), "RMSE_candidato": rc, "RMSE_referencia": rr, "delta_RMSE": rc - rr}


def clasificar(rmse: dict, reps_vs: dict, sens2_vs_mejor: dict, componentes: tuple) -> str:
    """rmse[(conjunto, modelo)], reps_vs[(conjunto, componente)] = repeticiones con mejora,
    sens2_vs_mejor[conjunto] = ΔRMSE frente al mejor componente sin las 2 parcelas más favorecidas."""
    conjuntos = sorted({c for c, _ in rmse})
    cand = [m for _, m in rmse if m not in componentes][0]
    supera = all(rmse[(c, cand)] < min(rmse[(c, m)] for m in componentes) for c in conjuntos)
    if not supera:
        return "A"
    estable = all(reps_vs[(c, m)] >= 8 for c in conjuntos for m in componentes)
    robusta = all(sens2_vs_mejor[c] < 0 for c in conjuntos)
    return "C" if estable and robusta else "B"
