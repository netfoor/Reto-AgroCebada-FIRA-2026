"""EXP_11: alineación, rechazo de defectos, fórmulas de mezcla y reproducción de métricas."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import combinacion_11 as C  # noqa: E402


def componentes_sinteticos(n=6, semilla=0):
    rng = np.random.default_rng(semilla)
    filas = []
    for i in range(n):
        y = 4 + rng.normal()
        for m in C.COMPONENTES:
            filas.append({"conjunto": "historicas", "repeticion": 0, "pliegue": i % 2, C.ID: f"P{i}", "Municipio": "A" if i < 4 else "B",
                          "municipio_visto": i < 5, "modelo": m, "predicho": y + rng.normal(0, 0.3), "observado": y})
    return pd.DataFrame(filas)


def test_componentes_validos_pasan():
    C.validar_componentes(componentes_sinteticos())


@pytest.mark.parametrize("defecto", ["duplicado", "faltante_fila", "nan", "inf", "etiqueta", "mascara", "municipio"])
def test_defectos_se_rechazan(defecto):
    d = componentes_sinteticos()
    if defecto == "duplicado":
        d = pd.concat([d, d.iloc[[0]]])
    elif defecto == "faltante_fila":
        d = d.drop(index=d[(d.modelo == "J") & (d[C.ID] == "P0")].index)
    elif defecto == "nan":
        d.loc[3, "predicho"] = np.nan
    elif defecto == "inf":
        d.loc[3, "predicho"] = np.inf
    elif defecto == "etiqueta":
        d.loc[(d.modelo == "K") & (d[C.ID] == "P1"), "observado"] += 0.1
    elif defecto == "mascara":
        d.loc[(d.modelo == "K") & (d[C.ID] == "P1"), "municipio_visto"] = False
    else:
        d.loc[(d.modelo == "K") & (d[C.ID] == "P1"), "Municipio"] = "Z"
    with pytest.raises(ValueError):
        C.validar_componentes(d)


def test_particiones_deben_coincidir():
    d = componentes_sinteticos()
    ext = pd.DataFrame([{"repeticion": 0, "pliegue": i % 2, "rol": "validacion", C.ID: f"P{i}"} for i in range(6)])
    C.validar_particiones(d, {"historicas": ext})
    with pytest.raises(ValueError):
        C.validar_particiones(d, {"historicas": ext.iloc[1:]})


def test_formula_exacta_y_dentro_del_intervalo():
    w = C.agregar_mezclas(C.ancho(componentes_sinteticos()))
    np.testing.assert_array_equal(w.E_JK, 0.5 * w.J + 0.5 * w.K)
    np.testing.assert_array_equal(w.E_MK, 0.5 * w.MUN + 0.5 * w.K)
    for n, (a, b) in C.MEZCLAS.items():
        assert ((w[n] >= np.minimum(w[a], w[b])) & (w[n] <= np.maximum(w[a], w[b]))).all()


def test_contribuciones_orden_declarado_y_clasificacion():
    w = C.agregar_mezclas(C.ancho(componentes_sinteticos(n=8)))
    d = C.contribuciones(w, "E_JK", "MIX")
    assert list(d.values) == sorted(d.values)
    rm = {("h", "J"): 0.50, ("h", "K"): 0.48, ("h", "E"): 0.47, ("n", "J"): 0.50, ("n", "K"): 0.48, ("n", "E"): 0.49}
    reps = {(c, m): 10 for c in "hn" for m in "JK"}
    assert C.clasificar(rm, reps, {"h": -1, "n": -1}, ("J", "K")) == "A"
    rm[("n", "E")] = 0.475
    assert C.clasificar(rm, reps, {"h": -1, "n": -1}, ("J", "K")) == "C"
    assert C.clasificar(rm, {**reps, ("n", "J"): 7}, {"h": -1, "n": -1}, ("J", "K")) == "B"
    assert C.clasificar(rm, reps, {"h": -1, "n": 0.001}, ("J", "K")) == "B"


def test_metricas_de_referencia_reproducen_exp10():
    comp = pd.read_csv(RAIZ / "data/exp_11_combinacion_modelos/oof_componentes.csv")
    met = pd.read_csv(RAIZ / "resultados/exp_10_verificacion_contraste_vecinal/registrada/metricas.csv")
    nombres = {"MIX": "MIX", "MUN": "MUN", "K": "K1_corregido"}
    for (cj, m), g in comp[comp.municipio_visto & comp.modelo.isin(nombres)].groupby(["conjunto", "modelo"]):
        r = met[(met.conjunto == cj) & (met.escenario == "SEEN135") & (met.modelo == nombres[m])].iloc[0]
        e = g.predicho.to_numpy() - g.observado.to_numpy()
        assert np.sqrt(np.mean(e ** 2)) == pytest.approx(r.RMSE, abs=1e-12)
        assert np.mean(np.abs(e)) == pytest.approx(r.MAE, abs=1e-12)


def test_metricas_de_mezclas_por_implementacion_independiente():
    res = RAIZ / "resultados/exp_11_combinacion_modelos/registrada/metricas.csv"
    if not res.exists():
        pytest.skip("Corrida registrada aún no ejecutada")
    comp = pd.read_csv(RAIZ / "data/exp_11_combinacion_modelos/oof_componentes.csv")
    met = pd.read_csv(res)
    piv = {m: g.set_index(["conjunto", "repeticion", "pliegue", "ID_POLIGONO"]).sort_index() for m, g in comp.groupby("modelo")}
    base = piv["MIX"]
    for nombre, (a, b) in {"E_JK": ("J", "K"), "E_MK": ("MUN", "K")}.items():
        pred = (piv[a].predicho.to_numpy() + piv[b].predicho.to_numpy()) / 2
        for cj in ("historicas", "nuevas"):
            for esc in ("SEEN135", "FULL138"):
                m = (base.index.get_level_values(0) == cj) & (base.municipio_visto.to_numpy() | (esc == "FULL138"))
                err = pred[m] - base.observado.to_numpy()[m]
                r = met[(met.conjunto == cj) & (met.escenario == esc) & (met.modelo == nombre)].iloc[0]
                assert r.RMSE == pytest.approx(float(np.sqrt((err ** 2).mean())), abs=1e-12)
                assert r.MAE == pytest.approx(float(np.abs(err).mean()), abs=1e-12)
