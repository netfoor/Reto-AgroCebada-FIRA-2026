"""Controles independientes EXP_07: únicamente etiquetas y covariables sintéticas."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest


RUTA = Path(__file__).resolve().parents[1] / "scripts" / "modelo_07.py"
SPEC = importlib.util.spec_from_file_location("modelo_07_prueba", RUTA)
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


def independiente(X, y, g, Xt, gt, alpha):
    """Diseño aumentado y lstsq: sin llamar al ajustador ni residualizar y."""
    X, Xt = np.asarray(X, float), np.asarray(Xt, float)
    y, g, gt = np.asarray(y, float), np.asarray(g, object), np.asarray(gt, object)
    medianas = np.array([np.median(col[np.isfinite(col)]) for col in X.T])
    X = np.where(np.isnan(X), medianas[None, :], X)
    Xt = np.where(np.isnan(Xt), medianas[None, :], Xt)
    niveles = sorted(set(g))
    posicion = {municipio: i for i, municipio in enumerate(niveles)}
    medias_x = {municipio: X[g == municipio].mean(axis=0) for municipio in niveles}
    medias_y = {municipio: float(y[g == municipio].mean()) for municipio in niveles}
    residuos = np.vstack([x - medias_x[municipio] for x, municipio in zip(X, g, strict=True)])
    escala = np.sqrt((residuos**2).sum(axis=0) / len(X))
    activa = escala > 1e-12 * np.maximum(1.0, np.abs(X).max(axis=0))
    no_visto = np.array([municipio not in posicion for municipio in gt], dtype=bool)
    if alpha is None or not activa.any():
        return np.array([medias_y.get(municipio, float(y.mean())) for municipio in gt]), no_visto
    dummy = np.eye(len(niveles))[[posicion[municipio] for municipio in g]]
    diseno = np.column_stack([dummy, X[:, activa] / escala[activa]])
    penalizacion = np.zeros((int(activa.sum()), diseno.shape[1]))
    penalizacion[:, len(niveles) :] = np.sqrt(alpha) * np.eye(int(activa.sum()))
    coef = np.linalg.lstsq(
        np.vstack([diseno, penalizacion]), np.r_[y, np.zeros(int(activa.sum()))], rcond=None
    )[0]
    pred = np.full(len(Xt), y.mean(), dtype=float)
    for i, (x, municipio) in enumerate(zip(Xt, gt, strict=True)):
        if municipio in posicion:
            pred[i] = (
                coef[posicion[municipio]] + (x[activa] / escala[activa]) @ coef[len(niveles) :]
            )
    return pred, no_visto


@pytest.fixture
def sintetico():
    rng = np.random.default_rng(707)
    X = rng.normal(size=(17, 2))
    g = np.array(["A"] * 8 + ["B"] * 8 + ["singleton"], dtype=object)
    y = np.array([4.0] * 8 + [6.0] * 8 + [9.0]) + 0.7 * X[:, 0] - 0.25 * X[:, 1]
    X[1, 0], X[9, 1] = np.nan, np.nan
    return X, y, g


@pytest.mark.parametrize("alpha", [None, 0.01, 0.1, 1.0, 10.0, 100.0])
def test_multicolumna_con_imputacion_vs_diseno_independiente(sintetico, alpha):
    X, y, g = sintetico
    Xt = np.array([[np.nan, -0.7], [2.1, np.nan], [99.0, -77.0], [np.nan, np.nan]])
    gt = np.array(["A", "B", "NUEVO", "singleton"], dtype=object)
    modelo = E.ajustar(X, y, g, alpha)
    actual, flags = E.predecir(modelo, Xt, gt)
    esperado, flags_ref = independiente(X, y, g, Xt, gt, alpha)
    np.testing.assert_allclose(actual, esperado, atol=1e-10, rtol=1e-10)
    np.testing.assert_array_equal(flags, flags_ref)


def test_baseline_mun_exacto_incluso_nan_y_no_visto(sintetico):
    X, y, g = sintetico
    m = E.ajustar(X, y, g, None)
    pred, nv = E.predecir(m, [[np.nan, 99], [999, np.nan], [np.nan, np.nan]], ["A", "B", "NUEVO"])
    np.testing.assert_array_equal(pred, [y[g == "A"].mean(), y[g == "B"].mean(), y.mean()])
    np.testing.assert_array_equal(nv, [False, False, True])
    assert m["alpha"] is None and not m["alpha_numerico_solicitado"]
    assert not m["ridge_ajustado"] and m["n_llamadas_ridge"] == 0


def test_baseline_no_llama_ridge(sintetico):
    X, y, g = sintetico
    with patch.object(E, "Ridge", side_effect=AssertionError("Ridge no permitido")):
        E.ajustar(X, y, g, None)


def test_opcion_numerica_se_contabiliza_con_columnas_degeneradas():
    X = np.array([[10.0], [10.0], [40.0], [40.0]])
    m = E.ajustar(X, [2, 6, 20, 22], ["A", "A", "B", "B"], 100)
    assert m["alpha_numerico_solicitado"]
    assert not m["ridge_ajustado"] and m["n_llamadas_ridge"] == 0
    np.testing.assert_array_equal(m["activa"], [False])
    pred, _ = E.predecir(m, [[-999.0], [999.0]], ["A", "B"])
    np.testing.assert_array_equal(pred, [4.0, 21.0])


def test_ridge_ajustado_no_depende_de_beta_no_cero():
    m = E.ajustar([[1], [3], [10], [14]], [2, 2, 20, 20], ["A", "A", "B", "B"], 1)
    assert m["alpha_numerico_solicitado"] and m["ridge_ajustado"]
    assert m["n_llamadas_ridge"] == 1
    np.testing.assert_array_equal(m["beta"], [0.0])


@pytest.mark.parametrize("alpha", [0.01, 1.0, 100.0])
def test_interceptos_municipales_sin_penalizar(alpha):
    X = [[1], [3], [10], [14]]
    y = [2, 2, 200, 200]
    g = ["A", "A", "B", "B"]
    pred, _ = E.predecir(E.ajustar(X, y, g, alpha), X, g)
    np.testing.assert_array_equal(pred, y)


def test_mediana_se_aprende_solo_del_entrenamiento_no_por_grupo():
    m = E.ajustar([[1], [np.nan], [9], [11]], [2, 6, 20, 22], ["A", "A", "B", "B"], 1)
    np.testing.assert_array_equal(m["medianas"], [9.0])
    np.testing.assert_array_equal(m["media_x"]["A"], [5.0])
    np.testing.assert_array_equal(m["media_x"]["B"], [10.0])
    primera, _ = E.predecir(m, [[np.nan]], ["A"])
    dos, _ = E.predecir(m, [[np.nan], [1e9]], ["A", "A"])
    assert primera[0] == dos[0]
    np.testing.assert_array_equal(m["medianas"], [9.0])


def test_mutar_holdout_y_otras_x_no_afecta_entrenamiento(sintetico):
    X, y, g = sintetico
    tr, va = np.arange(12), np.arange(12, 17)
    m = E.ajustar(X[tr], y[tr], g[tr], 1)
    referencia, _ = E.predecir(m, X[va], g[va])
    y_otro, X_otro = y.copy(), X.copy()
    y_otro[va] += 1e8
    X_otro[va[1:]] = 1e9
    m_otro = E.ajustar(X_otro[tr], y_otro[tr], g[tr], 1)
    otra, _ = E.predecir(m_otro, X_otro[va], g[va])
    assert referencia[0] == otra[0]
    for campo in ("medianas", "escala", "activa", "beta"):
        np.testing.assert_array_equal(m[campo], m_otro[campo])


def test_orden_entrenamiento_equivariante(sintetico):
    X, y, g = sintetico
    orden = np.random.default_rng(2).permutation(len(y))
    ma = E.ajustar(X, y, g, 0.1)
    mb = E.ajustar(X[orden], y[orden], g[orden], 0.1)
    pa, _ = E.predecir(ma, X, g)
    pb, _ = E.predecir(mb, X, g)
    np.testing.assert_allclose(pa, pb, atol=1e-12, rtol=1e-12)


def test_no_muta_entradas_ni_modelo_al_predecir(sintetico):
    X, y, g = sintetico
    original_X, original_y, original_g = X.copy(), y.copy(), g.copy()
    m = E.ajustar(X, y, g, 1)
    copia = copy.deepcopy(m)
    E.predecir(m, X, g)
    np.testing.assert_array_equal(X, original_X)
    np.testing.assert_array_equal(y, original_y)
    np.testing.assert_array_equal(g, original_g)
    for campo in ("medianas", "escala", "umbral_escala", "activa", "beta"):
        np.testing.assert_array_equal(m[campo], copia[campo])
    for municipio in m["media_x"]:
        np.testing.assert_array_equal(m["media_x"][municipio], copia["media_x"][municipio])
    assert m["media_y"] == copia["media_y"]


def test_columna_degenerada_no_anula_otra():
    X = [[1, 50], [3, 50], [10, 100], [14, 100]]
    y, g = [2, 6, 20, 22], ["A", "A", "B", "B"]
    m = E.ajustar(X, y, g, 1)
    np.testing.assert_array_equal(m["activa"], [True, False])
    assert m["beta"][1] == 0
    pred, _ = E.predecir(m, [[5, -999], [11, 999]], ["A", "B"])
    np.testing.assert_allclose(pred, [5.92, 20.36], atol=1e-12)


def test_singleton_incluido_en_denominador_de_escala():
    m = E.ajustar([[1], [3], [10], [14], [999]], [2, 6, 20, 22, 9], ["A", "A", "B", "B", "C"], 1)
    np.testing.assert_allclose(m["escala"], [np.sqrt(2.0)], atol=1e-15)
    np.testing.assert_array_equal(m["media_x"]["C"], [999.0])
    assert m["n_entrenamiento"] == 5
    pred, _ = E.predecir(m, [[1000]], ["C"])
    assert pred[0] != 9.0  # Pendiente común; no se fuerza corrección cero al predecir.


def test_guarda_relativa_usa_x_imputada_sin_centrar():
    m = E.ajustar(
        [[1e9], [1e9 + 1e-5], [2e9], [2e9 + 1e-5]], [2, 6, 20, 22], ["A", "A", "B", "B"], 1
    )
    assert m["escala"][0] > 1e-12
    assert m["umbral_escala"][0] > 1e-3
    np.testing.assert_array_equal(m["activa"], [False])


def test_municipio_no_visto_usa_global_sin_correccion(sintetico):
    X, y, g = sintetico
    m = E.ajustar(X, y, g, 0.01)
    pred, nv = E.predecir(m, [[np.nan, np.nan], [1e9, -1e9]], ["NUEVO", "NUEVO"])
    np.testing.assert_array_equal(pred, [y.mean(), y.mean()])
    np.testing.assert_array_equal(nv, [True, True])


def test_no_filtra_x_negativa_regla_de_calidad_es_externa():
    m = E.ajustar([[-3], [-1], [1], [3]], [2, 3, 4, 5], ["A"] * 4, 1)
    assert m["ridge_ajustado"]


@pytest.mark.parametrize("alpha", [0, -1, np.nan, np.inf, -np.inf, True, False, "baseline", "1"])
def test_alpha_invalido(alpha):
    with pytest.raises(ValueError, match="Alpha"):
        E.ajustar([[1], [2]], [3, 4], ["A", "A"], alpha)


@pytest.mark.parametrize("alpha", [None, 1.0])
def test_columna_sin_finitos_detiene_incluso_baseline(alpha):
    with pytest.raises(ValueError, match="sin valores finitos"):
        E.ajustar([[1, np.nan], [2, np.nan]], [3, 4], ["A", "A"], alpha)


@pytest.mark.parametrize("X", [[[np.inf]], [[-np.inf]], np.empty((2, 0)), np.zeros((2, 1, 1))])
def test_x_invalida(X):
    with pytest.raises(ValueError):
        E.ajustar(X, [1] * len(X), ["A"] * len(X), 1)


@pytest.mark.parametrize("y", [[], [np.nan, 3], [np.inf, 3], [[1], [2]], [1]])
def test_etiquetas_invalidas(y):
    with pytest.raises(ValueError):
        E.ajustar([[1], [2]], y, ["A", "A"], 1)


@pytest.mark.parametrize(
    "g", [["A"], ["A", None], ["A", ""], ["A", "  "], [["A"], ["B"]], ["A", np.inf]]
)
def test_grupos_invalidos(g):
    with pytest.raises(ValueError):
        E.ajustar([[1], [2]], [3, 4], g, 1)


def test_entrenamiento_vacio():
    with pytest.raises(ValueError):
        E.ajustar(np.empty((0, 1)), [], [], 1)


@pytest.mark.parametrize(
    "X,g", [([[np.inf]], ["A"]), ([[1, 2]], ["A"]), ([[1]], []), ([[1]], [None])]
)
def test_prediccion_invalida(X, g):
    m = E.ajustar([[1], [2]], [3, 4], ["A", "A"], 1)
    with pytest.raises(ValueError):
        E.predecir(m, X, g)


def test_prediccion_vacia_tiene_vectores_vacios():
    m = E.ajustar([[1], [2]], [3, 4], ["A", "A"], 1)
    pred, nv = E.predecir(m, np.empty((0, 1)), [])
    assert pred.shape == nv.shape == (0,)
    assert pred.dtype == float and nv.dtype == bool
