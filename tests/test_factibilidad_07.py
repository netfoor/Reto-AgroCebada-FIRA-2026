"""Factibilidad H7: controles con X sintética, sin rendimiento ni modelos."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("factibilidad_07", ROOT / "scripts/factibilidad_07.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def datos():
    ids = [f"AGC_{i:03d}" for i in range(1, 10)]
    meta = pd.DataFrame({"ID_POLIGONO": ids, "Municipio": ["A"] * 9, "Estado": ["H"] * 9,
                         "AREA_HA": np.arange(1, 10), "CONJUNTO": ["ENTRENAMIENTO"] * 8 + ["PREDICCION"]})
    cap = pd.DataFrame([{"ID_POLIGONO": pid, "fecha_captura": date, "sensor": "Planet",
                         "ndvi_promedio": .2 + .015 * i + .01 * j,
                         "ndvi_std": .02 + .005 * i + .001 * j,
                         "porcentaje_nubosidad": 10.0}
                        for i, pid in enumerate(ids) for j, date in enumerate(["01/04/2025", "01/05/2025"])])
    ext = pd.DataFrame([{"repeticion": 0, "pliegue": k, "ID_POLIGONO": pid,
                         "rol": "validacion" if (i < 4) == (k == 0) else "entrenamiento"}
                        for k in range(2) for i, pid in enumerate(ids[:8])])
    inside = []
    for k, g in ext.groupby("pliegue"):
        tr = g.loc[g.rol.eq("entrenamiento"), "ID_POLIGONO"].tolist()
        inside.extend({"repeticion": 0, "pliegue": k, "pliegue_interno": j, "ID_POLIGONO": pid,
                       "rol": "validacion" if (i < 2) == (j == 0) else "entrenamiento"}
                      for j in range(2) for i, pid in enumerate(tr))
    return cap, meta, ext, pd.DataFrame(inside)


def test_soporte_pareado_y_receta_exacta():
    cap, meta, ext, inter = datos()
    cap.loc[0, "ndvi_std"] = np.nan
    v, d, tables = f.construir(cap, meta, ext, inter)
    r = v.set_index("ID_POLIGONO").loc["AGC_001"]
    assert r[f.L] == cap.loc[1, "ndvi_promedio"]
    assert r[f.S] == cap.loc[1, "ndvi_std"]
    assert d["apta"] and not d["mascaras_promedio_std_identicas"]
    assert tables["calidad_parcela"].n_promedio_sin_std.sum() == 1
    assert len(tables["cobertura_mensual"]) == 9 * 7


def test_todas_las_variables_sin_y():
    cap, meta, ext, inter = datos()
    v, d, tablas = f.construir(cap, meta, ext, inter)
    assert list(v) == f.COLUMNAS_METADATA + [f.L, f.S]
    assert d["usa_rendimientos"] is False and d["ajustes_modelos"] == 0
    assert d["entrenamientos_exteriores"] == 2 and d["entrenamientos_interiores"] == 4
    assert all(not any("RENDIMIENTO" in c for c in t) for t in tablas.values())


def test_orden_invariante_y_entradas_intactas():
    cap, meta, ext, inter = datos()
    before = [t.copy(deep=True) for t in [cap, meta, ext, inter]]
    a = f.construir(cap, meta, ext, inter)
    b = f.construir(cap.sample(frac=1, random_state=5), meta.sample(frac=1, random_state=7), ext, inter)
    pd.testing.assert_frame_equal(a[0].reset_index(drop=True), b[0].reset_index(drop=True))
    assert a[1] == b[1]
    for old, now in zip(before, [cap, meta, ext, inter], strict=True):
        pd.testing.assert_frame_equal(old, now, check_exact=True)


def test_parcela_sin_descriptor_no_se_elimina():
    cap, meta, ext, inter = datos()
    cap.loc[cap.ID_POLIGONO.eq("AGC_009"), "ndvi_std"] = np.nan
    v, d, tables = f.construir(cap, meta, ext, inter)
    assert len(v) == 9 and v.set_index("ID_POLIGONO").loc["AGC_009", [f.L, f.S]].isna().all()
    assert d["parcelas_sin_descriptores"] == 1 and d["apta"]
    assert tables["soporte_59_solo_X"].S_ausente.all()


def test_columna_vacia_train_detiene_puerta():
    cap, meta, ext, inter = datos()
    cap.loc[cap.ID_POLIGONO.ne("AGC_009"), "ndvi_std"] = np.nan
    _, d, t = f.construir(cap, meta, ext, inter)
    assert not d["apta"] and not d["puertas"]["sin_columnas_vacias_en_train"]
    assert t["variacion_entrenamientos"].columna_vacia.all()


def test_std_solo_entre_municipios_no_sustenta_h7():
    cap, meta, ext, inter = datos()
    cap["ndvi_std"] = .05
    _, d, _ = f.construir(cap, meta, ext, inter)
    assert not d["apta"] and not d["puertas"]["S_con_variacion_intramunicipal_en_todos_train"]


@pytest.mark.parametrize("columna,valor", [("ndvi_std", -0.01), ("ndvi_std", np.inf),
                                          ("ndvi_promedio", np.inf), ("ndvi_promedio", 1.1),
                                          ("porcentaje_nubosidad", 101), ("porcentaje_nubosidad", np.inf)])
def test_valores_invalidos_se_detienen(columna, valor):
    cap, meta, ext, inter = datos()
    cap.loc[0, columna] = valor
    with pytest.raises(ValueError):
        f.construir(cap, meta, ext, inter)


@pytest.mark.parametrize("columna,valor", [("sensor", "Landsat"), ("fecha_captura", "2025-04-01"),
                                          ("fecha_captura", "01/11/2025"), ("ID_POLIGONO", "AGC_999")])
def test_claves_invalidas(columna, valor):
    cap, meta, ext, inter = datos()
    cap.loc[0, columna] = valor
    with pytest.raises(ValueError):
        f.construir(cap, meta, ext, inter)


def test_duplicados_no_se_promedian_silenciosamente():
    cap, meta, ext, inter = datos()
    with pytest.raises(ValueError, match="duplicada"):
        f.construir(pd.concat([cap, cap.iloc[[0]]]), meta, ext, inter)


@pytest.mark.parametrize("numero", [0, 1, 2, 3])
def test_cualquier_columna_rendimiento_se_rechaza(numero):
    args = list(datos())
    args[numero] = args[numero].assign(RENDIMIENTO_T_HA=9)
    with pytest.raises(ValueError, match="rendimiento"):
        f.construir(*args)


def test_las_ocultas_no_entran_en_entrenamientos_diagnosticos():
    cap, meta, ext, inter = datos()
    a = f.construir(cap, meta, ext, inter)
    cap.loc[cap.ID_POLIGONO.eq("AGC_009"), "ndvi_promedio"] = -.9
    cap.loc[cap.ID_POLIGONO.eq("AGC_009"), "ndvi_std"] = .9
    b = f.construir(cap, meta, ext, inter)
    pd.testing.assert_frame_equal(a[2]["variacion_entrenamientos"], b[2]["variacion_entrenamientos"], check_exact=True)


def test_qa_desconocida_no_equivale_a_cero():
    cap, meta, ext, inter = datos()
    cap.loc[cap.ID_POLIGONO.eq("AGC_001"), "porcentaje_nubosidad"] = np.nan
    _, _, t = f.construir(cap, meta, ext, inter)
    r = t["calidad_parcela"].set_index("ID_POLIGONO").loc["AGC_001"]
    assert pd.isna(r.nube_media_pareada) and r.nube_desconocida == 2
    assert r.n_pareadas == 2


def test_soporte_municipio_sin_etiquetas_no_inventa_rango():
    cap, meta, ext, inter = datos()
    meta.loc[meta.ID_POLIGONO.eq("AGC_009"), "Municipio"] = "B"
    _, _, tables = f.construir(cap, meta, ext, inter)
    s = tables["soporte_59_solo_X"].iloc[0]
    assert s.n_parcelas_etiquetadas_municipio == 0
    assert pd.isna(s.S_fuera_rango_municipal)


def test_std_negativa_aun_con_promedio_ausente_es_error():
    cap, meta, ext, inter = datos()
    cap.loc[0, ["ndvi_promedio", "ndvi_std"]] = [np.nan, -.2]
    with pytest.raises(ValueError, match="negativo"):
        f.construir(cap, meta, ext, inter)


def test_un_id_sin_capturas_se_conserva_y_cierra_puerta():
    cap, meta, ext, inter = datos()
    cap = cap.loc[~cap.ID_POLIGONO.eq("AGC_009")]
    v, d, _ = f.construir(cap, meta, ext, inter)
    assert len(v) == 9 and v.set_index("ID_POLIGONO").loc["AGC_009", [f.L, f.S]].isna().all()
    assert not d["apta"] and not d["puertas"]["capturas_para_todos_ids"]


def test_fechas_limite_son_inclusivas():
    cap, meta, ext, inter = datos()
    cap.loc[1, "fecha_captura"] = "31/10/2025"
    v, d, _ = f.construir(cap, meta, ext, inter)
    assert len(v) == 9 and d["capturas"] == 18


def test_holdout_X_no_cambia_mediana_escala_de_su_train():
    cap, meta, ext, inter = datos()
    a = f.construir(cap, meta, ext, inter)[2]["variacion_entrenamientos"]
    va = set(ext.loc[ext.pliegue.eq(0) & ext.rol.eq("validacion"), "ID_POLIGONO"])
    cap.loc[cap.ID_POLIGONO.isin(va), "ndvi_std"] = .9
    b = f.construir(cap, meta, ext, inter)[2]["variacion_entrenamientos"]
    mask = a.nivel.eq("exterior") & a.pliegue.eq(0)
    pd.testing.assert_frame_equal(a.loc[mask], b.loc[mask], check_exact=True)


def test_interna_con_holdout_externo_se_rechaza():
    cap, meta, ext, inter = datos()
    inter.loc[0, "ID_POLIGONO"] = "AGC_001"
    with pytest.raises(ValueError):
        f.construir(cap, meta, ext, inter)


def test_insumos_reales_X_reproducen_preparacion_guardada():
    import json

    d = ROOT / "data/exp_07_heterogeneidad_parcela"
    if not d.exists():
        pytest.skip("Preparación real no publicada en este checkout")
    def leer(nombre):
        return pd.read_csv(d / f"{nombre}.csv", float_precision="round_trip")
    v, resumen, _ = f.construir(leer("capturas_planet"), leer("metadatos"), leer("externas"), leer("internas"))
    control = leer("variables_197")
    pd.testing.assert_frame_equal(v, control, check_exact=True)
    guardado = json.loads((d / "diagnosticos_X.json").read_text())
    assert resumen == {k: guardado[k] for k in resumen}
    assert resumen["apta"] and resumen["capturas_pareadas"] == 18248
    assert resumen["mascaras_promedio_std_identicas"]
