"""Controles de las recetas de fuentes satelitales, sin entrenamientos."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _cargar(nombre):
    ruta = Path(__file__).resolve().parents[1] / "scripts" / f"{nombre}.py"
    if not ruta.is_file():
        ruta = Path(__file__).with_name(f"{nombre}.py")
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


sat = _cargar("fuentes_02_satelite")


def _serie(values, dates, sensor="PL", indice="ndvi", nubes=None):
    return pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001"] * len(values),
            "S": [sensor] * len(values),
            "fecha": pd.to_datetime(dates),
            "porcentaje_nubosidad": nubes if nubes is not None else [0.0] * len(values),
            f"{indice}_promedio": values,
            f"{indice}_max": np.array(values) + 0.1,
            f"{indice}_min": np.array(values) - 0.1,
            f"{indice}_std": [0.05] * len(values),
        }
    )


def _config():
    return {
        "ventana_objetivo": {"inicio": "2025-04-01", "fin": "2025-10-31"},
        "ventana_postciclo": {"inicio": "2025-11-01", "fin": "2025-12-31"},
        "historico": {
            "anios": [2022, 2023, 2024],
            "mes_inicio": 4,
            "mes_fin": 10,
            "indices": {"S2": ["ndvi", "evi", "savi", "lai", "ndwi", "msi"], "LS": ["vi6t"]},
        },
        "postciclo_indices": {
            "S2": ["ndvi", "evi", "crc", "mcrc", "ndti", "sti", "ndsvi"],
            "PL": ["ndvi", "evi", "lai", "msavi"],
        },
        "nubosidad_max_por_sensor": {"S2": None, "LS": None, "PL": None},
        "integral_hueco_max_dias": 30,
        "lai_negativos": "conservar",
    }


def _archivos_sinteticos():
    rows = []
    for sensor, sensor_name in [("S2", "Sentinel-2"), ("LS", "Landsat"), ("PL", "Planet")]:
        for year, month, value in [
            (2022, 5, 0.2),
            (2023, 5, 0.3),
            (2024, 5, 0.4),
            (2025, 5, 0.5),
            (2025, 6, 0.6),
            (2025, 11, 0.9),
        ]:
            row = {
                "ID_POLIGONO": "AGC_001",
                "sensor": sensor_name,
                "FECHA": pd.Timestamp(year, month, 1),
                "porcentaje_nubosidad": 0.0,
            }
            for ix in sat.SENSOR_IDX[sensor]:
                for suffix, offset in [("promedio", 0), ("max", 0.1), ("min", -0.1), ("std", 0)]:
                    row[f"{ix}_{suffix}"] = 0.05 if suffix == "std" else value + offset
            rows.append(row)
    d = pd.DataFrame(rows)
    return d[d.sensor.ne("Planet")].copy(), d[d.sensor.eq("Planet")].copy()


def test_integral_hueco_30_inclusivo_sin_extrapolar_y_31_excluido():
    assert sat.partial_integral(["2025-04-01", "2025-05-01", "2025-06-01"], [1.0, 3.0, 9.0]) == (
        60.0,
        30.0,
    )
    area, days = sat.partial_integral(["2025-04-01"], [1.0])
    assert np.isnan(area) and days == 0
    assert sat.partial_integral(["2025-04-01", "2025-04-11", "2025-06-30"], [1.0, 3.0, 9.0]) == (
        20.0,
        10.0,
    )


def test_integral_orden_fechas_repetidas_y_faltantes():
    assert sat.partial_integral(
        ["2025-04-11", "2025-04-01", "2025-04-01", "2025-04-05"], [3.0, 1.0, 3.0, np.nan]
    ) == (25.0, 10.0)


def test_pixel_maximo_y_pico_promedio_son_recetas_distintas():
    d = _serie([0.4, 0.8, 0.6], ["2025-05-01", "2025-06-01", "2025-07-01"])
    d["ndvi_max"] = [0.993, 0.9, 0.7]
    row = sat.summarize(d, "PL", ["ndvi"], "2025-04-01", "2025-10-31", None, "C_PL").iloc[0]
    assert row.C_PL_ndvi_pico_prom == 0.8 and row.C_PL_ndvi_pixmax == 0.993
    assert row.C_PL_ndvi_doy_pico_prom == 152 and row.C_PL_ndvi_doy_pixmax == 121
    assert np.isclose(row.C_PL_ndvi_std_media, 0.05, atol=1e-14, rtol=0)


def test_lai_conservado_y_anulado_antes_de_contar():
    d = _serie([-0.3, -0.2], ["2025-05-01", "2025-05-11"], sensor="S2", indice="lai")
    conserved = sat.summarize(d, "S2", ["lai"], "2025-04-01", "2025-10-31", None, "C_S2")
    assert np.isclose(conserved.iloc[0].C_S2_lai_media, -0.25)
    missing = sat.summarize(
        d,
        "S2",
        ["lai"],
        "2025-04-01",
        "2025-10-31",
        None,
        "C_S2",
        lai_regla="anular_negativos",
        ids=["AGC_001", "AGC_002"],
    )
    assert missing.C_S2_lai_n.eq(0).all() and missing.C_S2_lai_dias_integ.eq(0).all()
    measurement_cols = [c for c in missing if not c.endswith(("_n", "_dias_integ"))]
    assert missing[measurement_cols].isna().all().all()


def test_nubes_desconocidas_sin_umbral_y_con_umbral_sin_convertir_indice_en_cero():
    d = _serie(
        [0.2, 0.4, np.nan], ["2025-05-01", "2025-05-11", "2025-05-21"], nubes=[np.nan, 80.0, 100.0]
    )
    no_threshold = sat.summarize(d, "PL", ["ndvi"], "2025-04-01", "2025-10-31", None, "C_PL")
    assert no_threshold.iloc[0].C_PL_ndvi_n == 2
    assert np.isclose(no_threshold.iloc[0].C_PL_ndvi_media, 0.3)
    filtered = sat.summarize(d, "PL", ["ndvi"], "2025-04-01", "2025-10-31", 20, "C_PL")
    assert filtered.iloc[0].C_PL_ndvi_n == 0 and np.isnan(filtered.iloc[0].C_PL_ndvi_media)
    quality = sat.quality(d, "PL", "ndvi", "2025-04-01", "2025-10-31", None, "C_PL", ["AGC_001"])
    assert quality.iloc[0].C_PL_q_nube_desconocida == 1
    assert quality.iloc[0].C_PL_q_nube100 == 1
    assert quality.iloc[0].C_PL_q_nube_media_pct == 90


def test_construccion_separa_sensores_anos_y_postciclo_sin_mutar_fuentes():
    b, p = _archivos_sinteticos()
    before_b, before_p = b.copy(deep=True), p.copy(deep=True)
    cycle, historical, post = sat.construir_satelite(b, p, ["AGC_001"], _config())
    assert cycle.shape == (1, 320) and historical.shape == (1, 147) and post.shape == (1, 121)
    assert cycle.index.name == historical.index.name == post.index.name == "ID_POLIGONO"
    assert np.isclose(cycle.loc["AGC_001", "C_PL_ndvi_media"], 0.55)
    assert historical.loc["AGC_001", "H2022_S2_ndvi_media"] == 0.2
    assert historical.loc["AGC_001", "H2023_S2_ndvi_media"] == 0.3
    assert historical.loc["AGC_001", "H2024_S2_ndvi_media"] == 0.4
    assert post.loc["AGC_001", "P_PL_ndvi_media"] == 0.9
    assert "C_LS_ndvi_media" not in cycle and "C_S2_vi6t_media" not in cycle
    pd.testing.assert_frame_equal(b, before_b)
    pd.testing.assert_frame_equal(p, before_p)


def test_adaptacion_rechaza_fecha_no_validada_sensor_inesperado_y_duplicados():
    b, p = _archivos_sinteticos()
    with pytest.raises(ValueError, match="FECHA"):
        sat.construir_satelite(b.drop(columns="FECHA"), p, ["AGC_001"], _config())
    with pytest.raises(ValueError, match="Sensores"):
        sat.construir_satelite(b, p.assign(sensor="Otro"), ["AGC_001"], _config())
    with pytest.raises(ValueError, match="duplicadas"):
        sat.construir_satelite(pd.concat([b, b.iloc[:1]]), p, ["AGC_001"], _config())


def test_construccion_independiente_de_etiquetas_y_empate_de_pico_por_fecha():
    b, p = _archivos_sinteticos()
    original = sat.construir_satelite(b, p, ["AGC_001"], _config())
    b["RENDIMIENTO_T_HA"] = 999.0
    p["RENDIMIENTO_T_HA"] = -999.0
    changed = sat.construir_satelite(b, p, ["AGC_001"], _config())
    for first, second in zip(original, changed, strict=True):
        pd.testing.assert_frame_equal(first, second)
    tied = _serie([0.8, 0.8], ["2025-08-01", "2025-06-01"])
    row = sat.summarize(tied, "PL", ["ndvi"], "2025-04-01", "2025-10-31", None, "C_PL").iloc[0]
    assert row.C_PL_ndvi_doy_pico_prom == 152


def test_diccionario_distingue_definicion_filtro_y_admisibilidad():
    assert "píxel extremo" in sat.diccionario_sat("C_PL_ndvi_pixmax", _config())["agregacion"]
    assert "por captura" in sat.diccionario_sat("C_PL_ndvi_media", _config())["agregacion"]
    assert sat.diccionario_sat("P_PL_ndvi_media", _config())["rol"] == "pendiente_admisibilidad"
    assert sat.diccionario_sat("H2022_S2_lai_media", _config())["ventana"] == "2022-04..2022-10"
    assert "conservar" in sat.diccionario_sat("C_S2_lai_media", _config())["filtro"]
    assert "toda la ventana" in sat.diccionario_sat("C_PL_q_nube_media_pct", _config())["filtro"]


def test_media_por_captura_mensual_y_dias_diferentes_con_frecuencia_desigual():
    d = _serie([0.2, 0.2, 0.8], ["2025-04-01", "2025-04-02", "2025-05-01"])
    out, monthly = sat.diagnosticos_media_vs_tiempo(
        d, "PL", "ndvi", ["AGC_001"], "2025-04-01", "2025-05-31"
    )
    assert np.isclose(out.iloc[0].media_captura, 0.4)
    assert np.isclose(out.iloc[0].media_mensual_simple, 0.5)
    assert np.isclose(out.iloc[0].media_mensual_por_dias, (0.2 * 30 + 0.8 * 31) / 61)
    assert monthly.n.tolist() == [2, 1]
    assert monthly.dias_mes.tolist() == [30, 31]


def test_diagnostico_mes_ausente_conserva_nan_no_imputa():
    d = _serie([0.4], ["2025-04-01"])
    out, monthly = sat.diagnosticos_media_vs_tiempo(
        d, "PL", "ndvi", ["AGC_001", "AGC_002"], "2025-04-01", "2025-05-31"
    )
    assert out.media_mensual_simple.isna().all() and out.media_mensual_por_dias.isna().all()
    assert monthly.loc[monthly.n.eq(0), "media"].isna().all()
    assert out.loc["AGC_002", "n_capturas"] == 0
    assert np.isnan(out.loc["AGC_002", "media_captura"])


def test_paridad_v0_real_desde_insumos_centralizados_o_boveda():
    """Control completo, solo lectura, de las 467 columnas conservadas."""
    vault = os.environ.get("AGRO_VAULT")
    root = Path(vault) if vault else Path(__file__).resolve().parents[1]
    config_path = root / (
        "integracion_v0/config_v0.json" if vault else "config/fuentes_02_recetas.json"
    )
    referencia_path = root / (
        "integracion_v0/salidas/variables_v0_197.csv"
        if vault
        else "data/referencias/variables_v0_197.csv"
    )
    if not all(p.is_file() for p in (root / "data/raw/DataSet.zip", config_path, referencia_path)):
        pytest.skip("Faltan ZIP o referencias locales; usar insumos del proyecto o AGRO_VAULT")
    audit = _cargar("auditoria_01")
    with audit.cargar_zip(root / "data/raw/DataSet.zip") as archive:
        b = audit.validar_satelite(
            audit.leer_csv(archive, "Conjunto_datos_BASICO_AgroCebada2026.csv")
        )
        p = audit.validar_satelite(audit.leer_csv(archive, "Conjunto_datos_PRO_AgroCebada.csv"))
    old = pd.read_csv(referencia_path).set_index("ID_POLIGONO")
    config = json.loads(config_path.read_text())
    cycle, historical, post = sat.construir_satelite(b, p, old.index, config)
    assert cycle.shape == (197, 320) and historical.shape == (197, 147) and post.shape == (197, 121)
    for current in (cycle, historical):
        anchor = old[current.columns]
        assert anchor.isna().equals(current.isna())
        np.testing.assert_allclose(
            current.to_numpy(), anchor.to_numpy(), atol=1e-12, rtol=0, equal_nan=True
        )
    row = cycle.loc["AGC_001"]
    assert row.C_PL_ndvi_pixmax == 0.993 and row.C_PL_ndvi_pico_prom == 0.836
    assert np.isclose(row.C_PL_ndvi_media, 0.40209278350515465, atol=1e-12, rtol=0)
