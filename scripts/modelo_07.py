"""Corrección Ridge con efectos municipales no penalizados para EXP_07.

La imputación por mediana es una extensión prospectiva común a C0 y C1.
Medianas, medias municipales y escala se aprenden únicamente del entrenamiento
recibido. Este módulo no lee archivos, selecciona opciones ni ejecuta la ronda.
"""

from __future__ import annotations

from numbers import Real

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


TOL_ESCALA = 1e-12


def _matriz(X):
    """Admite NaN como ausencia; nunca convierte Inf en un dato ausente."""
    try:
        matriz = np.asarray(X, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("X debe ser una matriz numérica") from exc
    if matriz.ndim == 1:
        matriz = matriz.reshape(-1, 1)
    if matriz.ndim != 2 or matriz.shape[1] == 0:
        raise ValueError("X debe tener dos dimensiones y al menos una columna")
    if np.isinf(matriz).any():
        raise ValueError("X contiene infinito; no se imputa")
    return matriz


def _grupos(g, n):
    grupos = np.asarray(g, dtype=object)
    if grupos.ndim != 1 or len(grupos) != n:
        raise ValueError("Dimensiones municipales incompatibles")
    if pd.isna(grupos).any():
        raise ValueError("Municipio ausente")
    for valor in grupos:
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError("Municipio debe ser una categoría textual no vacía")
    return grupos


def _alpha_valido(alpha):
    if alpha is None:
        return False
    if (
        isinstance(alpha, (bool, np.bool_))
        or not isinstance(alpha, Real)
        or not np.isfinite(alpha)
        or alpha <= 0
    ):
        raise ValueError("Alpha debe ser None (baseline) o un número positivo finito")
    return True


def ajustar(X, y, g, alpha):
    """Aprende medianas y una pendiente común con interceptos municipales libres.

    ``alpha=None`` representa baseline: se calculan controles de X, pero no se
    llama a Ridge. ``alpha_numerico_solicitado`` contabiliza la opción solicitada
    incluso si todas las columnas son degeneradas; ``ridge_ajustado`` identifica
    la llamada efectiva a ``Ridge.fit``. No depende de que la pendiente sea cero.
    """
    matriz = _matriz(X)
    objetivo = np.asarray(y, dtype=float)
    if (
        objetivo.ndim != 1
        or len(objetivo) != len(matriz)
        or len(objetivo) == 0
        or not np.isfinite(objetivo).all()
    ):
        raise ValueError("Etiquetas de entrenamiento vacías, no finitas o incompatibles")
    grupos = _grupos(g, len(objetivo))
    numerico = _alpha_valido(alpha)
    if not np.isfinite(matriz).any(axis=0).all():
        raise ValueError("Columna de entrenamiento sin valores finitos para imputar")

    medianas = np.nanmedian(matriz, axis=0)
    imputada = np.where(np.isnan(matriz), medianas[None, :], matriz)
    frame = pd.DataFrame(imputada, columns=list(range(imputada.shape[1])))
    frame["y"], frame["g"] = objetivo, grupos
    medias_x = frame.groupby("g", sort=True)[list(range(imputada.shape[1]))].mean()
    medias_y = frame.groupby("g", sort=True).y.mean()
    residuo_x = imputada - medias_x.reindex(grupos).to_numpy()
    residuo_y = objetivo - medias_y.reindex(grupos).to_numpy()

    # Misma definición V3: escala poblacional de los residuos, singleton incluido.
    escala = np.sqrt(np.mean(residuo_x * residuo_x, axis=0))
    umbral = TOL_ESCALA * np.maximum(1.0, np.max(np.abs(imputada), axis=0))
    activa = escala > umbral
    beta = np.zeros(imputada.shape[1], dtype=float)
    ridge_ajustado = bool(numerico and activa.any())
    if ridge_ajustado:
        diseno = residuo_x[:, activa] / escala[activa]
        estimador = Ridge(alpha=float(alpha), fit_intercept=False, solver="cholesky")
        estimador.fit(diseno, residuo_y)
        beta[activa] = np.asarray(estimador.coef_, dtype=float)
    if not np.isfinite(beta).all():
        raise ValueError("Pendientes Ridge no finitas")

    return {
        "medianas": medianas.copy(),
        "media_x": {municipio: fila.to_numpy().copy() for municipio, fila in medias_x.iterrows()},
        "media_y": medias_y.to_dict(),
        "media_global_y": float(objetivo.mean()),
        "escala": escala.copy(),
        "umbral_escala": umbral.copy(),
        "activa": activa.copy(),
        "beta": beta.copy(),
        "n_entrenamiento": len(objetivo),
        "alpha": None if alpha is None else float(alpha),
        "alpha_numerico_solicitado": bool(numerico),
        "ridge_ajustado": ridge_ajustado,
        "n_llamadas_ridge": int(ridge_ajustado),
    }


def predecir(m, X, g):
    """Transforma con las medianas y estadísticas guardadas, sin reajustarlas.

    Municipio no visto: media global de entrenamiento, sin corrección numérica.
    La presencia de otras filas de validación no modifica una predicción.
    """
    matriz = _matriz(X)
    grupos = _grupos(g, len(matriz))
    if matriz.shape[1] != len(m["beta"]):
        raise ValueError("Número de columnas incompatible con el modelo")
    imputada = np.where(np.isnan(matriz), m["medianas"][None, :], matriz)
    if not np.isfinite(imputada).all():
        raise ValueError("Entrada de predicción no finita después de imputar")
    pred = np.empty(len(grupos), dtype=float)
    no_visto = np.zeros(len(grupos), dtype=bool)
    activa = m["activa"]
    for i, municipio in enumerate(grupos):
        if municipio not in m["media_y"]:
            pred[i] = m["media_global_y"]
            no_visto[i] = True
        else:
            correccion = 0.0
            if activa.any():
                z = (imputada[i, activa] - m["media_x"][municipio][activa]) / m["escala"][activa]
                correccion = float(m["beta"][activa] @ z)
            pred[i] = m["media_y"][municipio] + correccion
    if not np.isfinite(pred).all():
        raise ValueError("Predicción no finita")
    return pred, no_visto
