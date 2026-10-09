"""EXP_10: receta K1 (publicada y con corte temporal correcto) y corrección lineal sobre MIX.

Funciones puras: no leen variables globales ni guardan cachés. Las referencias MUN/MIX se
toman sin cambios de validacion_03.predecir_referencias.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from validacion_03 import predecir_referencias

ID = "ID_POLIGONO"
Y = "RENDIMIENTO_T_HA"
NUBE_MAX = 20.0
VENTANA_DIAS = 15
MINIMO_DIAS = 3
DIA_CORTE = 304            # 31/10/2025, año no bisiesto
DIA_BASE = (91, 150)       # abril–mayo
DIA_PICO_INI = 150
RADIO_M = 1000.0
MIN_VECINOS = 2
ALPHA = 10.0
RECETAS = ("publicada", "corregida")


def capturas_receta(pro: pd.DataFrame) -> pd.DataFrame:
    """Capturas Planet que usa la receta: NDVI finito y nubosidad ≤ 20 %, año 2025."""
    req = {ID, "fecha_captura", "sensor", "ndvi_promedio", "porcentaje_nubosidad"}
    if not req <= set(pro):
        raise ValueError("Faltan columnas de capturas")
    if set(pro.sensor) != {"Planet"}:
        raise ValueError("Solo Planet")
    fecha = pd.to_datetime(pro.fecha_captura, format="%d/%m/%Y", errors="raise")
    ok = np.isfinite(pro.ndvi_promedio.to_numpy(float)) & (pro.porcentaje_nubosidad.to_numpy(float) <= NUBE_MAX)
    out = pd.DataFrame({ID: pro[ID].to_numpy(), "fecha": fecha.dt.strftime("%Y-%m-%d").to_numpy(),
                        "ndvi_promedio": pro.ndvi_promedio.to_numpy(float),
                        "porcentaje_nubosidad": pro.porcentaje_nubosidad.to_numpy(float)})[ok]
    if (pd.to_datetime(out.fecha).dt.year != 2025).any():
        raise ValueError("Capturas fuera de 2025")
    return out.sort_values([ID, "fecha"]).reset_index(drop=True)


def curva(doy, valores, dias):
    """Mediana diaria → mediana móvil centrada de 15 días (mín. 3) → interpolación solo interior."""
    s = pd.Series(np.asarray(valores, float)).groupby(np.asarray(doy, int)).median()
    s = s.reindex(np.asarray(dias, int))
    return s.rolling(VENTANA_DIAS, center=True, min_periods=MINIMO_DIAS).median().interpolate(limit_area="inside")


def integral(c, fin_max=DIA_CORTE):
    """Integral sobre la base entre los cruces del 50 % de la amplitud (receta de EXP_08/09)."""
    c = c.loc[:fin_max]
    base = c.loc[DIA_BASE[0]:DIA_BASE[1]].median()
    temporada = c.loc[DIA_PICO_INI:min(330, fin_max)]
    if temporada.isna().all() or not np.isfinite(base):
        return np.nan
    pico, dia_pico = temporada.max(), temporada.idxmax()
    umbral = base + 0.5 * (pico - base)
    subida = c.loc[DIA_PICO_INI:dia_pico]
    inicio = subida[subida >= umbral].index.min()
    bajada = c.loc[dia_pico:fin_max]
    fin = bajada[bajada < umbral].index.min() if (bajada < umbral).any() else fin_max
    return float((c.loc[inicio:fin] - base).clip(lower=0).sum())


def integrales(capturas: pd.DataFrame, receta: str) -> pd.Series:
    """publicada: suaviza con todo el año y recorta después (EXP_09 K1).
    corregida: descarta capturas posteriores al 31/10 y limita la rejilla ANTES de suavizar."""
    if receta not in RECETAS:
        raise ValueError("Receta desconocida")
    doy = pd.to_datetime(capturas.fecha).dt.dayofyear.to_numpy()
    c = capturas.assign(doy=doy)
    if receta == "corregida":
        c = c[c.doy <= DIA_CORTE]
        dias = np.arange(1, DIA_CORTE + 1)
    else:
        dias = np.arange(1, 366)
    return pd.Series({p: integral(curva(g.doy, g.ndvi_promedio, dias)) for p, g in c.groupby(ID)}, dtype=float)


def vecinos_geometricos(meta: pd.DataFrame, radio=RADIO_M) -> dict:
    """Vecinos por centroide UTM, distancia en (0, radio), entre las 197 parcelas."""
    ids = meta[ID].to_numpy()
    xy = meta[["x_m", "y_m"]].to_numpy(float)
    d = np.linalg.norm(xy[:, None] - xy[None], axis=2)
    return {p: ids[(d[i] < radio) & (d[i] > 0)] for i, p in enumerate(ids)}


def contraste(serie: pd.Series, vecinos: dict, regla="publicada") -> pd.Series:
    """Valor propio − mediana de vecinas.
    publicada: ≥2 vecinas geométricas; la mediana omite NaN (puede quedar con 1 vecina válida).
    finitos: ≥2 vecinas con valor finito."""
    out = {}
    for p, v in vecinos.items():
        propio = serie.get(p, np.nan)
        vals = serie.reindex(v).to_numpy(float)
        n_ok = int(np.isfinite(vals).sum())
        cond = len(v) >= MIN_VECINOS if regla == "publicada" else n_ok >= MIN_VECINOS
        out[p] = propio - np.nanmedian(vals) if cond and np.isfinite(propio) and n_ok > 0 else np.nan
    return pd.Series(out, dtype=float)


def diagnostico_vecinos(serie: pd.Series, vecinos: dict) -> pd.DataFrame:
    return pd.DataFrame([{ID: p, "vecinos_geometricos": len(v),
                          "vecinos_finitos": int(np.isfinite(serie.reindex(v).to_numpy(float)).sum())}
                         for p, v in vecinos.items()])


def ajustar_correccion(z: pd.Series, e: pd.Series, alpha=ALPHA) -> dict:
    """β = Σ z̃·e / (Σ z̃² + α), z̃ estandarizado con mediana y desviación (ddof=1) de las filas
    de entrenamiento con valor finito; las demás no entran al ajuste."""
    x = z.reindex(e.index).to_numpy(float)
    ok = np.isfinite(x)
    if ok.sum() < 3:
        raise ValueError("Muy pocas filas con contraste en entrenamiento")
    med = float(np.median(x[ok]))
    sd = float(np.std(x[ok], ddof=1))
    if not sd > 0:
        raise ValueError("Escala degenerada")
    zz = (x[ok] - med) / sd
    beta = float(zz @ e.to_numpy(float)[ok] / (zz @ zz + alpha))
    return {"mediana": med, "escala": sd, "beta": beta, "alpha": alpha, "n_ajuste": int(ok.sum())}


def aplicar_correccion(param: dict, z: pd.Series, ids) -> tuple[np.ndarray, np.ndarray]:
    """Corrección para ids; sin contraste → 0 (respaldo MIX). Devuelve corrección y máscara de respaldo."""
    x = z.reindex(ids).to_numpy(float)
    respaldo = ~np.isfinite(x)
    c = np.where(respaldo, 0.0, param["beta"] * (x - param["mediana"]) / param["escala"])
    return c, respaldo


def validar_fold(tr, va, internas_fold: pd.DataFrame) -> None:
    """Correspondencia de particiones: internas ⊂ entrenamiento exterior; validaciones internas
    disjuntas que cubren el entrenamiento; exterior sin solapamiento."""
    tr, va = set(tr), set(va)
    if tr & va:
        raise ValueError("Entrenamiento y validación exteriores se solapan")
    vistos = []
    for _, g in internas_fold.groupby("pliegue_interno"):
        itr = set(g.loc[g.rol.eq("entrenamiento"), ID])
        iva = set(g.loc[g.rol.eq("validacion"), ID])
        if not (itr | iva) <= tr or itr & iva or (itr | iva) != tr:
            raise ValueError("Partición interna fuera del entrenamiento exterior")
        vistos += list(iva)
    if len(vistos) != len(set(vistos)) or set(vistos) != tr:
        raise ValueError("Validaciones internas no particionan el entrenamiento")


def residuos_mix(entrenamiento: pd.DataFrame, internas_fold: pd.DataFrame) -> pd.Series:
    """e = y − MIX con cada parcela de entrenamiento predicha sin su etiqueta (validación interna).
    entrenamiento: filas exteriores de entrenamiento con ID, Municipio, x_m, y_m, Y."""
    t = entrenamiento.set_index(ID)
    e = pd.Series(np.nan, index=t.index)
    for _, g in internas_fold.groupby("pliegue_interno"):
        a = t.loc[g.loc[g.rol.eq("entrenamiento"), ID]].reset_index()
        vi = g.loc[g.rol.eq("validacion"), ID].to_numpy()
        v = t.loc[vi, ["Municipio", "x_m", "y_m"]].reset_index()
        e.loc[vi] = t.loc[vi, Y].to_numpy(float) - predecir_referencias(a, v)["MIX"]
    if e.isna().any():
        raise ValueError("Residuo interno ausente")
    return e


def predecir_fold(entrenamiento: pd.DataFrame, validacion_X: pd.DataFrame, internas_fold: pd.DataFrame,
                  contrastes: dict, alpha=ALPHA) -> tuple[dict, dict, pd.Series]:
    """Predicciones de un pliegue exterior, parámetros y residuos internos de MIX.
    validacion_X no debe contener etiquetas."""
    if Y in validacion_X:
        raise ValueError("La validación exterior no debe traer etiquetas")
    validar_fold(entrenamiento[ID], validacion_X[ID], internas_fold)
    ref = predecir_referencias(entrenamiento, validacion_X[[ID, "Municipio", "x_m", "y_m"]])
    preds = {"MUN": np.asarray(ref["MUN"], float), "MIX": np.asarray(ref["MIX"], float)}
    params = {}
    e = residuos_mix(entrenamiento, internas_fold)
    for nombre, z in contrastes.items():
        p = ajustar_correccion(z, e, alpha)
        c, respaldo = aplicar_correccion(p, z, validacion_X[ID].to_numpy())
        preds[nombre] = preds["MIX"] + c
        params[nombre] = {**p, "n_validacion_respaldo": int(respaldo.sum()), "n_validacion": len(c)}
    return preds, params, e
