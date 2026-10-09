"""Pruebas sintéticas de EXP_10: corte temporal, fuga, faltantes, vecinos y particiones."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import modelo_10 as M  # noqa: E402
from validacion_03 import predecir_referencias  # noqa: E402


def capturas_sinteticas(n_parcelas=4, semilla=0):
    rng = np.random.default_rng(semilla)
    filas = []
    for k in range(n_parcelas):
        for doy in range(1, 366, 3):
            fase = np.clip((doy - 160) / 60, 0, 1) * np.clip((330 - doy) / 50, 0, 1)
            filas.append({M.ID: f"AGC_{k:03d}", "fecha": (pd.Timestamp("2025-01-01") + pd.Timedelta(days=doy - 1)).strftime("%Y-%m-%d"),
                          "ndvi_promedio": 0.2 + 0.6 * fase + rng.normal(0, 0.01), "porcentaje_nubosidad": 0.0})
    return pd.DataFrame(filas)


# ----------------------------------------------------------------- corte temporal
def test_corregida_invariante_a_capturas_posteriores():
    cap = capturas_sinteticas()
    base = M.integrales(cap, "corregida")
    doy = pd.to_datetime(cap.fecha).dt.dayofyear
    cambiada = cap.assign(ndvi_promedio=np.where(doy > M.DIA_CORTE, 0.99, cap.ndvi_promedio))
    borrada = cap[doy <= M.DIA_CORTE]
    extra = pd.concat([cap, cap[doy > 300].assign(fecha="2025-11-01", ndvi_promedio=0.9)], ignore_index=True)
    for variante in (cambiada, borrada, extra):
        pd.testing.assert_series_equal(M.integrales(variante, "corregida"), base)


def test_publicada_si_depende_de_noviembre():
    cap = capturas_sinteticas()
    doy = pd.to_datetime(cap.fecha).dt.dayofyear
    cambiada = cap.assign(ndvi_promedio=np.where(doy > M.DIA_CORTE, 0.99, cap.ndvi_promedio))
    assert not np.allclose(M.integrales(cap, "publicada"), M.integrales(cambiada, "publicada"))


def test_receta_filtra_nubes_y_no_finitos():
    pro = pd.DataFrame({M.ID: ["A", "A", "A"], "fecha_captura": ["01/05/2025", "02/05/2025", "03/05/2025"], "sensor": "Planet",
                        "ndvi_promedio": [0.3, np.nan, 0.4], "porcentaje_nubosidad": [0.0, 0.0, 20.1]})
    assert len(M.capturas_receta(pro)) == 1


# ----------------------------------------------------------------- vecinos
def meta_lineal(xs):
    return pd.DataFrame({M.ID: [f"P{i}" for i in range(len(xs))], "x_m": xs, "y_m": 0.0})


def test_vecinos_y_regla_de_finitos():
    meta = meta_lineal([0, 400, 800, 5000])
    vec = M.vecinos_geometricos(meta)
    assert set(vec["P1"]) == {"P0", "P2"} and len(vec["P3"]) == 0
    s = pd.Series({"P0": 1.0, "P1": 2.0, "P2": np.nan, "P3": 5.0})
    pub, fin = M.contraste(s, vec, "publicada"), M.contraste(s, vec, "finitos")
    assert pub["P1"] == 1.0          # publicada: 2 vecinas geométricas, solo 1 finita
    assert np.isnan(fin["P1"])       # finitos: exige 2 vecinas con valor
    assert np.isnan(pub["P3"]) and np.isnan(pub["P2"])


# ----------------------------------------------------------------- corrección y faltantes
def test_correccion_formula_y_exclusion_de_faltantes():
    z = pd.Series([1.0, 2.0, np.nan, 4.0, 5.0], index=list("abcde"))
    e = pd.Series([0.1, 0.2, 9.0, 0.4, 0.5], index=list("abcde"))
    p = M.ajustar_correccion(z, e, alpha=10)
    x = np.array([1, 2, 4, 5.0])
    zz = (x - np.median(x)) / np.std(x, ddof=1)
    assert p["beta"] == pytest.approx(zz @ np.array([0.1, 0.2, 0.4, 0.5]) / (zz @ zz + 10))
    assert p["n_ajuste"] == 4
    c, respaldo = M.aplicar_correccion(p, pd.Series({"v1": np.nan, "v2": 3.0}), ["v1", "v2"])
    assert respaldo.tolist() == [True, False] and c[0] == 0.0


# ----------------------------------------------------------------- particiones y fuga
def escenario(n=40, semilla=1):
    rng = np.random.default_rng(semilla)
    ids = [f"AGC_{i:03d}" for i in range(n)]
    tabla = pd.DataFrame({M.ID: ids, "Municipio": np.where(np.arange(n) % 2, "A", "B"),
                          "x_m": rng.uniform(0, 3000, n), "y_m": rng.uniform(0, 3000, n), M.Y: rng.normal(4, 0.5, n)})
    tr, va = ids[:30], ids[30:]
    filas = [(k, "entrenamiento" if i % 4 != k else "validacion", pid) for k in range(4) for i, pid in enumerate(tr)]
    internas = pd.DataFrame(filas, columns=["pliegue_interno", "rol", M.ID])
    z = {"K": pd.Series(rng.normal(0, 1, n), index=ids)}
    return tabla, tr, va, internas, z


def test_fuga_etiquetas_de_validacion_no_cambian_prediccion():
    tabla, tr, va, internas, z = escenario()
    t = tabla.set_index(M.ID)
    v = t.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
    p1, _, _ = M.predecir_fold(t.loc[tr].reset_index(), v, internas, z)
    t2 = t.copy()
    t2.loc[va, M.Y] = -50.0
    p2, _, _ = M.predecir_fold(t2.loc[tr].reset_index(), v, internas, z)
    for k in p1:
        np.testing.assert_array_equal(p1[k], p2[k])
    with pytest.raises(ValueError):
        M.predecir_fold(t.loc[tr].reset_index(), t.loc[va].reset_index(), internas, z)


def test_mix_es_la_receta_historica_y_sin_contraste_se_recupera_mix():
    tabla, tr, va, internas, z = escenario()
    t = tabla.set_index(M.ID)
    v = t.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
    sin = {"K": pd.Series(np.nan, index=t.index).where(t.index.isin(tr), np.nan)}
    sin["K"].loc[tr] = np.arange(len(tr), dtype=float)
    p, par, _ = M.predecir_fold(t.loc[tr].reset_index(), v, internas, sin)
    np.testing.assert_array_equal(p["MIX"], predecir_referencias(t.loc[tr].reset_index(), v)["MIX"])
    np.testing.assert_array_equal(p["K"], p["MIX"])
    assert par["K"]["n_validacion_respaldo"] == len(va)


def test_particiones_internas_mal_formadas_se_rechazan():
    tabla, tr, va, internas, z = escenario()
    M.validar_fold(tr, va, internas)
    fuera = internas.copy()
    fuera.loc[0, M.ID] = va[0]
    with pytest.raises(ValueError):
        M.validar_fold(tr, va, fuera)
    doble = internas.copy()
    doble.loc[(doble.pliegue_interno == 1) & (doble.rol == "validacion"), "rol"] = "entrenamiento"
    with pytest.raises(ValueError):
        M.validar_fold(tr, va, doble)
    with pytest.raises(ValueError):
        M.validar_fold(tr, list(va) + [tr[0]], internas)


def test_residuos_internos_no_usan_la_propia_etiqueta():
    tabla, tr, va, internas, z = escenario()
    t = tabla.set_index(M.ID)
    e1 = M.residuos_mix(t.loc[tr].reset_index(), internas)
    objetivo = tr[0]
    t2 = t.copy()
    t2.loc[objetivo, M.Y] += 10
    e2 = M.residuos_mix(t2.loc[tr].reset_index(), internas)
    # El residuo de la propia parcela cambia exactamente por el cambio de su etiqueta (su predicción no la usa).
    assert e2[objetivo] - e1[objetivo] == pytest.approx(10.0)
