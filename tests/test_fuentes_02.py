"""Contratos de fuentes y paridad histórica, sin ajuste ni predicción.

La ausencia de rendimiento se prueba por separación de tablas e invariancia;
no se usa una correlación con Y como certificado de ausencia de fuga. Las
fuentes reales se leen desde los insumos centralizados; AGRO_BOVEDA permite
contrastar directamente con los originales históricos. No se escribe en ellos.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box


def _cargar_modulo(nombre):
    raiz = Path(__file__).resolve().parents[1]
    ruta = raiz / "scripts" / f"{nombre}.py"
    if not ruta.is_file():
        ruta = Path(__file__).with_name(f"{nombre}.py")
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


for _nombre in ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite"):
    _cargar_modulo(_nombre)
F = _cargar_modulo("fuentes_02")


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


@pytest.fixture
def clima_sintetico():
    filas = []
    for identificador in ("AGC_001", "AGC_002"):
        for anio in range(2022, 2026):
            for mes in range(1, 13):
                for variable in ("prec", "tmin", "tmax"):
                    valor = (
                        mes * 10.0
                        if variable == "prec"
                        else mes + (5.0 if variable == "tmin" else 20.0)
                    )
                    filas.append(
                        {
                            "ID_POLIGONO": identificador,
                            "variable": variable,
                            "anio": anio,
                            "mes": mes,
                            "pond": valor,
                            "cent": valor + 3.0,
                            "frac_valida": 1.0,
                            "n_celdas": 1,
                            "celda_centroide": "R0_C0",
                        }
                    )
    return pd.DataFrame(filas)


def test_lluvia_suma_y_temperatura_media_por_dias_sin_mutar(clima_sintetico):
    original = clima_sintetico.copy(deep=True)
    config = _config()
    resultado = F.resumir_clima(clima_sintetico, config)
    meses = np.arange(4, 11)
    dias = np.array([30, 31, 30, 31, 31, 30, 31])
    assert resultado.shape == (2, 42)
    assert resultado.clim_prec_ciclo_mm.eq(sum(meses * 10)).all()
    assert resultado.clim_prec_ciclo_ctrl_centroide_mm.eq(sum(meses * 10) + 21).all()
    assert resultado.clim_prec_ciclo_dif_pond_menos_cent_mm.eq(-21).all()
    assert np.allclose(
        resultado.clim_tmin_ciclo_C, np.average(meses + 5.0, weights=dias), rtol=0, atol=1e-12
    )
    assert not np.isclose(
        resultado.clim_tmin_ciclo_C.iloc[0], np.mean(meses + 5.0), rtol=0, atol=1e-12
    )
    assert resultado.clim_amplitud_ciclo_C.eq(15).all()
    assert config["ventana_objetivo"] == {"inicio": "2025-04-01", "fin": "2025-10-31"}
    pd.testing.assert_frame_equal(clima_sintetico, original)


@pytest.mark.parametrize(
    "variable,salida",
    [("prec", "clim_prec_ciclo_mm"), ("tmin", "clim_tmin_ciclo_C"), ("tmax", "clim_tmax_ciclo_C")],
)
@pytest.mark.parametrize("tipo_faltante", ["fila", "valor"])
def test_mes_faltante_no_se_imputa_ni_se_omite_en_suma(
    clima_sintetico, variable, salida, tipo_faltante
):
    seleccion = (
        clima_sintetico.ID_POLIGONO.eq("AGC_001")
        & clima_sintetico.variable.eq(variable)
        & clima_sintetico.anio.eq(2025)
        & clima_sintetico.mes.eq(6)
    )
    if tipo_faltante == "fila":
        datos = clima_sintetico.loc[~seleccion]
    else:
        datos = clima_sintetico.copy()
        datos.loc[seleccion, "pond"] = np.nan
    resultado = F.resumir_clima(datos, _config())
    assert np.isnan(resultado.loc["AGC_001", salida])
    assert np.isfinite(resultado.loc["AGC_002", salida])


def test_mes_historico_faltante_no_se_sustituye_por_otro_anio(clima_sintetico):
    quitar = (
        clima_sintetico.ID_POLIGONO.eq("AGC_001")
        & clima_sintetico.variable.eq("prec")
        & clima_sintetico.anio.eq(2023)
        & clima_sintetico.mes.eq(6)
    )
    r = F.resumir_clima(clima_sintetico.loc[~quitar], _config())
    assert np.isnan(r.loc["AGC_001", "clim_prec_ciclo_H2023_mm"])
    assert r.loc["AGC_001", "clim_prec_ciclo_H2022_mm"] == 490
    assert r.loc["AGC_001", "clim_prec_ciclo_mm"] == 490


def test_dias_por_anio_incluyen_febrero_bisiesto_en_ventana_sintetica(clima_sintetico):
    config = _config()
    config["ventana_objetivo"] = {"inicio": "2025-01-01", "fin": "2025-03-31"}
    config["historico"]["mes_inicio"], config["historico"]["mes_fin"] = 1, 3
    r = F.resumir_clima(clima_sintetico, config)
    valores = np.array([6.0, 7.0, 8.0])
    assert np.isclose(
        r.clim_tmin_ciclo_C.iloc[0], np.average(valores, weights=[31, 28, 31]), rtol=0, atol=1e-12
    )
    assert np.isclose(
        r.clim_tmin_ciclo_H2024_C.iloc[0],
        np.average(valores, weights=[31, 29, 31]),
        rtol=0,
        atol=1e-12,
    )
    # Valores asimétricos hacen observable la diferencia entre 28 y 29 días.
    datos = clima_sintetico.copy()
    datos.loc[datos.variable.eq("tmin") & datos.mes.eq(2), "pond"] = 100.0
    r = F.resumir_clima(datos, config)
    assert r.clim_tmin_ciclo_H2024_C.iloc[0] != r.clim_tmin_ciclo_C.iloc[0]


def test_ventana_parcial_y_claves_mensuales_duplicadas_se_rechazan(clima_sintetico):
    config = _config()
    config["ventana_objetivo"]["inicio"] = "2025-04-02"
    with pytest.raises(ValueError, match="meses completos"):
        F.resumir_clima(clima_sintetico, config)
    duplicada = clima_sintetico.loc[clima_sintetico.anio.eq(2025) & clima_sintetico.mes.eq(4)].iloc[
        :1
    ]
    with pytest.raises(ValueError):
        F.resumir_clima(pd.concat([clima_sintetico, duplicada]), _config())


@pytest.mark.parametrize("inicio,fin", [("2025-10-01", "2026-01-31"), ("2025-10-01", "2025-04-30")])
def test_ventana_clima_cruzada_o_invertida_se_rechaza(clima_sintetico, inicio, fin):
    config = _config()
    config["ventana_objetivo"] = {"inicio": inicio, "fin": fin}
    with pytest.raises(ValueError, match="meses completos dentro de un año"):
        F.resumir_clima(clima_sintetico, config)


def _dato_extraccion():
    return {
        "pond": 2.0,
        "cent": 3.0,
        "frac_valida": 1.0,
        "n_celdas": 1,
        "celda_centroide": "R0_C0",
        "cobertura_total": 1.0,
        "cobertura_malla": 1.0,
        "min": 2.0,
        "max": 2.0,
        "std": 0.0,
        "n_validos": 1,
    }


def _rasters_clima_sinteticos():
    return {
        f"{variable}_{anio}_{mes:02d}.tif": b"solo_prueba_de_claves"
        for variable in ("PREC", "Tmin", "Tmax")
        for anio in range(2022, 2026)
        for mes in range(1, 13)
    }


def test_extraccion_climatica_exige_144_meses_y_claves_completas(monkeypatch):
    monkeypatch.setattr(
        F, "extraer_raster", lambda bruto, geoms, crs, **kw: {k: _dato_extraccion() for k in geoms}
    )
    rasters = _rasters_clima_sinteticos()
    geoms = {"AGC_001": None, "AGC_002": None}
    r = F.extraer_clima(rasters, geoms, 4326)
    assert len(r) == 288 and not r.duplicated(["ID_POLIGONO", "variable", "anio", "mes"]).any()
    del rasters["PREC_2025_06.tif"]
    with pytest.raises(ValueError, match="incompleto"):
        F.extraer_clima(rasters, geoms, 4326)
    rasters["PREC_2025_13.tif"] = b"mes_invalido"
    with pytest.raises(ValueError, match="1–12"):
        F.extraer_clima(rasters, geoms, 4326)


def test_extraccion_climatica_vacia_se_rechaza_con_error_de_contrato():
    with pytest.raises(ValueError, match="incompleto"):
        F.extraer_clima({}, {"AGC_001": None}, 4326)


def test_topografia_exige_un_archivo_por_superficie(monkeypatch):
    monkeypatch.setattr(
        F, "extraer_raster", lambda bruto, geoms, crs, **kw: {k: _dato_extraccion() for k in geoms}
    )
    geoms = {"AGC_001": None}
    buenos = {"Elevacion_INEGI_CEM4_120m.tif": b"e", "Pendiente_INEGI_CEM4_120m_grados.tif": b"p"}
    r, qa = F.extraer_topografia(buenos, geoms, 4326)
    assert r.shape == (1, 16) and len(qa) == 2
    with pytest.raises(ValueError):
        F.extraer_topografia({"Elevacion_A.tif": b"e", "Elevacion_B.tif": b"e"}, geoms, 4326)


def _piezas_ensamble():
    meta = pd.DataFrame(
        {"ID_POLIGONO": ["AGC_001", "AGC_002"], "CONJUNTO": ["ENTRENAMIENTO", "PREDICCION"]}
    )
    indice = pd.Index(["AGC_002", "AGC_001"], name="ID_POLIGONO")
    piezas = [
        pd.DataFrame({nombre: [1.0, np.nan]}, index=indice)
        for nombre in (
            "C_PL_ndvi_media",
            "H2022_S2_ndvi_media",
            "clim_prec_ciclo_mm",
            "topo_elev_media_m",
        )
    ]
    return [meta, *piezas]


def test_ensamble_alinea_ids_conserva_faltantes_y_no_mutaciones():
    piezas = _piezas_ensamble()
    antes = [p.copy(deep=True) for p in piezas]
    r = F.ensamblar_variables(*piezas)
    assert list(r.ID_POLIGONO) == ["AGC_001", "AGC_002"]
    assert np.isnan(r.loc[0, "C_PL_ndvi_media"])
    assert r.loc[1, "C_PL_ndvi_media"] == 1.0
    assert not any("RENDIMIENTO" in c.upper() for c in r)
    for original, actual in zip(antes, piezas, strict=True):
        pd.testing.assert_frame_equal(original, actual)


@pytest.mark.parametrize(
    "problema", ["id_duplicado", "id_faltante", "id_extra", "columna_duplicada", "objetivo"]
)
def test_ensamble_rechaza_claves_y_columnas_inadmisibles(problema):
    piezas = _piezas_ensamble()
    if problema == "id_duplicado":
        piezas[1].index = ["AGC_001", "AGC_001"]
    elif problema == "id_faltante":
        piezas[1] = piezas[1].iloc[:1]
    elif problema == "id_extra":
        piezas[1].index = ["AGC_001", "AGC_003"]
    elif problema == "columna_duplicada":
        piezas[2].columns = piezas[1].columns
    else:
        piezas[2]["RENDIMIENTO_T_HA"] = 7.0
    with pytest.raises(ValueError):
        F.ensamblar_variables(*piezas)


def test_referencia_compara_mascaras_esquema_ids_y_tolerancias():
    base = pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_002"],
            "clim_prec_ciclo_mm": [2.0, np.nan],
            "topo_elev_media_m": [2500.0, 2600.0],
            "C_PL_ndvi_n": [2.0, 3.0],
            "Municipio": ["M", "N"],
        }
    )
    copia = base.iloc[::-1].copy()
    copia.loc[copia.ID_POLIGONO.eq("AGC_001"), "clim_prec_ciclo_mm"] += 5e-9
    copia.loc[copia.ID_POLIGONO.eq("AGC_001"), "topo_elev_media_m"] += 5e-5
    r = F.comparar_referencia(copia, base).set_index("variable")
    assert r.coincide.all() and r.loc["clim_prec_ciclo_mm", "tolerancia_absoluta"] == 1e-8
    assert r.loc["topo_elev_media_m", "tolerancia_absoluta"] == 1e-4
    assert r.loc["C_PL_ndvi_n", "tolerancia_absoluta"] == 0
    copia.loc[copia.ID_POLIGONO.eq("AGC_001"), "C_PL_ndvi_n"] += 1e-9
    assert (
        not F.comparar_referencia(copia, base).set_index("variable").loc["C_PL_ndvi_n", "coincide"]
    )
    with pytest.raises(ValueError, match="Máscara"):
        F.comparar_referencia(base.fillna(0), base)
    with pytest.raises(ValueError, match="Esquema"):
        F.comparar_referencia(base[base.columns[::-1]], base)
    with pytest.raises(ValueError, match="IDs"):
        F.comparar_referencia(base.assign(ID_POLIGONO=["AGC_001", "AGC_003"]), base)


def test_referencia_exige_ids_unicos_incluso_si_ambas_tablas_repiten():
    tabla = pd.DataFrame({"ID_POLIGONO": ["AGC_001", "AGC_001"], "clim_prec_ciclo_mm": [2.0, 2.0]})
    with pytest.raises(ValueError):
        F.comparar_referencia(tabla, tabla.copy())


@pytest.mark.parametrize(
    "columna",
    ["C_S2_q_filas_ventana", "C_PL_q_con_indice", "C_LS_q_nube100", "C_S2_q_nube_desconocida"],
)
def test_conteos_de_calidad_tambien_se_comparan_exactamente(columna):
    referencia = pd.DataFrame({"ID_POLIGONO": ["AGC_001"], columna: [2.0]})
    calculada = referencia.copy()
    calculada[columna] += 1e-9
    r = F.comparar_referencia(calculada, referencia).iloc[0]
    assert r.tolerancia_absoluta == 0 and not r.coincide


def test_diccionario_distingue_metadatos_controles_y_candidatas():
    config = _config()
    assert F.describir_variable("CONJUNTO", config)["rol"] == "metadato_excluir"
    assert F.describir_variable("Municipio", config)["rol"] == "metadato_territorial"
    assert F.describir_variable("clim_prec_ciclo_ctrl_centroide_mm", config)["rol"] == "control"
    assert F.describir_variable("clim_prec_ciclo_mm", config)["rol"] == "candidata"
    assert F.describir_variable("topo_pend_cobertura", config)["rol"] == "bandera_calidad"
    with pytest.raises(ValueError):
        F.describir_variable("RENDIMIENTO_T_HA", config)


@pytest.fixture
def fuentes_simuladas(monkeypatch):
    catalogo = pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_002"],
            "AREA_HA": [1.0, 2.0],
            "RENDIMIENTO_T_HA": [4.0, np.nan],
            "CONJUNTO": ["ENTRENAMIENTO", "PREDICCION"],
        }
    )
    atributos = pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_002"],
            "AREA_HA_GEOMETRIA": [1.0, 2.0],
            "CONJUNTO_GEOMETRIA": ["ENTRENAMIENTO", "PREDICCION"],
            "Estado": ["Puebla", "Puebla"],
            "Municipio": ["M", "M"],
            "Cultivo": ["Cebada", "Cebada"],
        }
    )
    basico = pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_002"],
            "fecha_captura": ["01/05/2025"] * 2,
            "sensor": ["Sentinel-2"] * 2,
            "porcentaje_nubosidad": [0.0, 0.0],
            "ndvi_promedio": [0.5, 0.6],
        }
    )
    pro = basico.assign(sensor="Planet")
    tablas = {
        "ID_area_rendimiento_70_30_Reto_AgroCebada.csv": catalogo,
        "Conjunto_datos_BASICO_AgroCebada2026.csv": basico,
        "Conjunto_datos_PRO_AgroCebada.csv": pro,
    }
    geometrias = [box(-98.5, 19.5, -98.499, 19.501), box(-98.49, 19.49, -98.488, 19.492)]
    monkeypatch.setattr(F, "leer_csv", lambda z, nombre: tablas[nombre].copy(deep=True))
    monkeypatch.setattr(
        F, "leer_geometrias", lambda z: (atributos.copy(deep=True), geometrias, "EPSG:4326")
    )
    return tablas, atributos


def test_carga_separa_rendimiento_y_metadatos_invariantes_a_etiquetas(fuentes_simuladas):
    tablas, _ = fuentes_simuladas
    originales = {k: v.copy(deep=True) for k, v in tablas.items()}
    primero = F.cargar_fuentes(None)
    assert primero["metadatos"].shape == (2, 14) and primero["etiquetas"].shape == (1, 2)
    assert not any("RENDIMIENTO" in c.upper() for c in primero["metadatos"])
    for nombre, tabla in tablas.items():
        pd.testing.assert_frame_equal(tabla, originales[nombre])
    tablas["ID_area_rendimiento_70_30_Reto_AgroCebada.csv"].loc[0, "RENDIMIENTO_T_HA"] = 77.0
    cambiado = F.cargar_fuentes(None)
    for nombre in ("metadatos", "basico", "pro"):
        pd.testing.assert_frame_equal(primero[nombre], cambiado[nombre])
    assert cambiado["etiquetas"].RENDIMIENTO_T_HA.iloc[0] == 77.0


@pytest.mark.parametrize("problema", ["id_catalogo", "id_satelite", "area", "conjunto"])
def test_carga_rechaza_inconsistencias_entre_fuentes(fuentes_simuladas, problema):
    tablas, atributos = fuentes_simuladas
    if problema == "id_catalogo":
        atributos.loc[0, "ID_POLIGONO"] = "AGC_003"
    elif problema == "id_satelite":
        tablas["Conjunto_datos_BASICO_AgroCebada2026.csv"].loc[0, "ID_POLIGONO"] = "AGC_003"
    elif problema == "area":
        atributos.loc[0, "AREA_HA_GEOMETRIA"] = 9.0
    else:
        atributos.loc[0, "CONJUNTO_GEOMETRIA"] = "PREDICCION"
    with pytest.raises(ValueError):
        F.cargar_fuentes(None)


@pytest.fixture(scope="session")
def reales_02():
    valor = os.environ.get("AGRO_BOVEDA")
    raiz = Path(valor) if valor else Path(__file__).resolve().parents[1]
    zip_path = raiz / "data/raw/DataSet.zip"
    config_path = raiz / (
        "integracion_v0/config_v0.json" if valor else "config/fuentes_02_recetas.json"
    )
    referencia_path = raiz / (
        "integracion_v0/salidas/variables_v0_197.csv"
        if valor
        else "data/referencias/variables_v0_197.csv"
    )
    if not all(p.is_file() for p in (zip_path, config_path, referencia_path)):
        pytest.skip("Faltan ZIP o referencias locales; usar insumos del proyecto o AGRO_BOVEDA")
    rutas = [zip_path, config_path, referencia_path]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in rutas}
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert antes[zip_path] == config["zip_sha256"]
    with zipfile.ZipFile(zip_path) as z:
        F.validar_zip(z)
        fuentes = F.cargar_fuentes(z)
        rasters, inventario = F.leer_rasters(z)
    ids = list(fuentes["metadatos"].ID_POLIGONO)
    ciclo, historico, postciclo = F.construir_satelite(
        fuentes["basico"], fuentes["pro"], ids, config
    )
    cache = {}
    largo = F.extraer_clima(rasters, fuentes["geometrias"], fuentes["crs_geometrias"], cache)
    clima = F.resumir_clima(largo, config)
    topo, qa_topo = F.extraer_topografia(
        rasters, fuentes["geometrias"], fuentes["crs_geometrias"], cache
    )
    tabla = F.ensamblar_variables(fuentes["metadatos"], ciclo, historico, clima, topo)
    referencia = pd.read_csv(referencia_path)
    yield {
        "fuentes": fuentes,
        "rasters": rasters,
        "inventario": inventario,
        "ciclo": ciclo,
        "historico": historico,
        "postciclo": postciclo,
        "largo": largo,
        "clima": clima,
        "topo": topo,
        "qa_topo": qa_topo,
        "tabla": tabla,
        "referencia": referencia,
        "config": config,
    }
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in rutas} == antes


def test_carga_real_separa_etiquetas_y_los_14_metadatos(reales_02):
    fuentes = reales_02["fuentes"]
    meta, etiquetas = fuentes["metadatos"], fuentes["etiquetas"]
    assert meta.shape == (197, 14) and meta.ID_POLIGONO.is_unique
    assert etiquetas.shape == (138, 2) and etiquetas.ID_POLIGONO.is_unique
    assert set(etiquetas.columns) == {"ID_POLIGONO", "RENDIMIENTO_T_HA"}
    assert etiquetas.RENDIMIENTO_T_HA.notna().all()
    assert meta.CONJUNTO.value_counts().to_dict() == {"ENTRENAMIENTO": 138, "PREDICCION": 59}
    assert not any("RENDIMIENTO" in c.upper() for c in meta)
    assert set(fuentes["geometrias"]) == set(meta.ID_POLIGONO)


def test_carga_real_146_rasters_con_mallas_propias(reales_02):
    inventario = reales_02["inventario"]
    assert len(reales_02["rasters"]) == len(inventario) == 146
    assert inventario.grupo.value_counts().to_dict() == {
        "temperatura": 96,
        "precipitacion": 48,
        "topografia": 2,
    }
    assert inventario.huella_malla.nunique() == 3
    assert inventario.groupby("grupo").huella_malla.nunique().eq(1).all()
    lluvia = inventario.loc[inventario.grupo.eq("precipitacion")].iloc[0]
    temperatura = inventario.loc[inventario.grupo.eq("temperatura")].iloc[0]
    assert temperatura["transform"][5] - lluvia["transform"][5] == -2.980232238769531e-7
    assert len(reales_02["largo"]) == 197 * 144
    assert not reales_02["largo"].duplicated(["ID_POLIGONO", "variable", "anio", "mes"]).any()


def test_base_real_197_por_539_y_postciclo_separado(reales_02):
    r = reales_02
    assert r["ciclo"].shape == (197, 320)
    assert r["historico"].shape == (197, 147)
    assert r["postciclo"].shape == (197, 121)
    assert r["clima"].shape == (197, 42) and r["topo"].shape == (197, 16)
    assert r["tabla"].shape == (197, 539) and r["tabla"].ID_POLIGONO.is_unique
    assert r["tabla"].columns.is_unique
    assert not any(c.startswith("P_") or "RENDIMIENTO" in c.upper() for c in r["tabla"])
    assert all(c.startswith("P_") for c in r["postciclo"])
    diccionario = pd.DataFrame([F.describir_variable(c, r["config"]) for c in r["tabla"]])
    assert list(diccionario.variable) == list(r["tabla"])
    assert not diccionario.variable.duplicated().any()


def test_paridad_real_539_columnas_mascaras_y_conteos(reales_02):
    contraste = F.comparar_referencia(reales_02["tabla"], reales_02["referencia"])
    assert len(contraste) == 538 and contraste.coincide.all(), contraste.loc[~contraste.coincide]
    assert list(reales_02["tabla"].columns) == list(reales_02["referencia"].columns)
    assert (
        reales_02["tabla"]
        .set_index("ID_POLIGONO")
        .sort_index()
        .isna()
        .equals(reales_02["referencia"].set_index("ID_POLIGONO").sort_index().isna())
    )
    conteos = [
        c
        for c in reales_02["tabla"]
        if c.endswith(
            (
                "_n",
                "_npix",
                "_n_celdas_prec",
                "_n_celdas_temp",
                "_q_filas_ventana",
                "_q_con_indice",
                "_q_nube100",
                "_q_nube_desconocida",
            )
        )
    ]
    a, b = (
        r.set_index("ID_POLIGONO").sort_index()[conteos]
        for r in (reales_02["tabla"], reales_02["referencia"])
    )
    np.testing.assert_array_equal(a.to_numpy(), b.to_numpy())


def test_topografia_real_conserva_cobertura_baja_sin_umbral_de_lluvia(reales_02):
    topo = reales_02["topo"]
    assert topo.topo_elev_cobertura.lt(0.99).sum() == 4
    assert topo.topo_pend_cobertura.lt(0.99).sum() == 5
    assert np.isfinite(topo.loc["AGC_170", "topo_elev_media_m"])
    assert np.isfinite(topo.loc["AGC_170", "topo_pend_media_grados"])
    assert {"cobertura_total", "cobertura_malla"} <= set(reales_02["qa_topo"])
    assert "cobertura_total" not in reales_02["tabla"]
