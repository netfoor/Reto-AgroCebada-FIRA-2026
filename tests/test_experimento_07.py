"""Controles de selección, contabilidad y evaluación sin rendimientos reales."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import experimento_07 as exp
from validacion_03 import construir_oof


@pytest.mark.parametrize(
    "scores,esperado",
    [
        ({"baseline": 0.5, 0.01: 0.4, 100.0: 0.4}, 100.0),
        ({"baseline": 0.4, 0.01: 0.4, 100.0: 0.4}, "baseline"),
        ({"baseline": 0.4 + 0.5e-12, 0.01: 0.4}, "baseline"),
        ({"baseline": 0.4 + 2e-12, 0.01: 0.4}, 0.01),
        ({"baseline": 0.7, 0.01: 0.4, 100.0: 0.5}, 0.01),
    ],
)
def test_selector_empate(scores, esperado):
    assert exp.elegir(scores) == esperado


def test_metricas_agrupadas_y_r2_constante():
    g = pd.DataFrame({exp.ID: ["a", "b"], "observado": [1.0, 3.0], "predicho": [2.0, 2.0]})
    m = exp.metricas(g)
    assert m["RMSE"] == m["MAE"] == 1
    assert m["R2"] == 0
    g.observado = 1
    assert np.isnan(exp.metricas(g)["R2"])


def datos_sinteticos():
    ids = [f"AGC_{k:03d}" for k in range(1, 198)]
    mun = ["Comun"] * 135 + ["SingletonA", "SingletonB", "SingletonC"] + ["Comun"] * 59
    x = pd.DataFrame(
        {
            exp.ID: ids,
            "Municipio": mun,
            "CONJUNTO": ["ENTRENAMIENTO"] * 138 + ["PREDICCION"] * 59,
            exp.L: np.arange(197, dtype=float),
            exp.S: np.arange(197) % 7,
            "x_m": np.arange(197, dtype=float),
            "y_m": np.arange(197, dtype=float),
        }
    )
    y = pd.DataFrame({exp.ID: ids[:138], exp.Y: np.zeros(138)})
    exterior, interior = [], []
    for r in range(10):
        for f in range(5):
            train = []
            for j, pid in enumerate(ids[:138]):
                role = "validacion" if j % 5 == f else "entrenamiento"
                exterior.append({"repeticion": r, "pliegue": f, "rol": role, exp.ID: pid})
                if role == "entrenamiento":
                    train.append(pid)
            for k in range(4):
                for j, pid in enumerate(train):
                    interior.append(
                        {
                            "repeticion": r,
                            "pliegue": f,
                            "pliegue_interno": k,
                            "rol": "validacion" if j % 4 == k else "entrenamiento",
                            exp.ID: pid,
                        }
                    )
    return x, y, pd.DataFrame(exterior), pd.DataFrame(interior)


@pytest.fixture(scope="module")
def synthetic():
    return datos_sinteticos()


def test_presupuesto_y_seleccion_sinteticos_sin_ridge(monkeypatch, synthetic):
    x, y, outer, inner = synthetic
    ref = construir_oof(x.iloc[:138].merge(y, on=exp.ID), outer)
    calls = []

    def fake_fit(X, y, g, alpha):
        assert np.array_equal(y, np.zeros(len(y)))
        calls.append((len(y), alpha))
        return {"ridge_ajustado": alpha is not None, "grupos": set(g)}

    def fake_predict(m, X, g):
        return np.zeros(len(g)), ~np.isin(g, list(m["grupos"]))

    monkeypatch.setattr(exp, "ajustar", fake_fit)
    monkeypatch.setattr(exp, "predecir", fake_predict)
    result = exp.ejecutar_comparacion(x, y, outer, inner, ref)
    assert result["presupuesto"]["evaluaciones_internas"] == 2400
    assert result["presupuesto"]["evaluaciones_baseline"] == 400
    assert result["presupuesto"]["opciones_ridge_internas"] == 2000
    assert result["presupuesto"]["reconstrucciones_exteriores"] == 100
    assert len(calls) == 2500
    assert len(result["scores"]) == 600 and len(result["scores_pliegue"]) == 2400
    assert len(result["seleccion"]) == 100 and len(result["oof"]) == 5520
    assert result["seleccion"].opcion_elegida.eq("baseline").all()
    tables = exp.evaluar(result["oof"])
    assert tables["reglas"].competitivo_propuesto.eq(False).all()
    assert tables["reglas"].aporte_H7.eq(False).all()
    assert tables["metricas"].query("escenario == 'SEEN135'").n_oof.eq(1350).all()


def test_no_entrena_si_control_referencia_falla(monkeypatch, synthetic):
    x, y, outer, inner = synthetic
    ref = construir_oof(x.iloc[:138].merge(y, on=exp.ID), outer)
    ref.loc[ref.modelo.eq("MUN"), "predicho"] = 99

    def prohibited(*args):
        raise AssertionError("No se debe ajustar si las referencias no pasan")

    monkeypatch.setattr(exp, "ajustar", prohibited)
    with pytest.raises(ValueError, match="no reproduce"):
        exp.ejecutar_comparacion(x, y, outer, inner, ref)
