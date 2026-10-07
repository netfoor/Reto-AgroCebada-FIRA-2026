"""Controles sintéticos de la auditoría; no entrenan ni usan etiquetas reales."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import shapefile
from pyproj import CRS


def _cargar_modulo():
    raiz = Path(__file__).resolve().parents[1]
    candidatas = (
        raiz / "scripts" / "auditoria_01.py",
        Path(__file__).with_name("auditoria_01.py"),
    )
    for ruta in candidatas:
        if ruta.is_file():
            spec = importlib.util.spec_from_file_location("auditoria_01", ruta)
            modulo = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(modulo)
            return modulo
    raise FileNotFoundError("No se encontró scripts/auditoria_01.py.")


auditoria = _cargar_modulo()


@pytest.fixture
def catalogo():
    return pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_002", "AGC_003"],
            "AREA_HA": [2.0, 3.0, 1.0],
            "RENDIMIENTO_T_HA": [4.0, np.nan, 2.5],
            "CONJUNTO": ["ENTRENAMIENTO", "PREDICCION", "ENTRENAMIENTO"],
        }
    )


@pytest.fixture
def satelite():
    return pd.DataFrame(
        {
            "ID_POLIGONO": ["AGC_001", "AGC_001", "AGC_002"],
            "fecha_captura": ["01/02/2025", "02/02/2025", "01/02/2025"],
            "sensor": ["Sentinel-2", "Sentinel-2", "Planet"],
            "ndvi_promedio": [0.6, np.nan, 0.7],
            "porcentaje_nubosidad": [0.0, 100.0, 15.0],
        }
    )


def _zip_memoria(entradas):
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archivo:
            for nombre, contenido in entradas:
                archivo.writestr(nombre, contenido)
    buffer.seek(0)
    return buffer


def test_catalogo_valido_no_modifica_original(catalogo):
    original = catalogo.copy(deep=True)
    salida = auditoria.normalizar_catalogo(catalogo)
    pd.testing.assert_frame_equal(catalogo, original)
    pd.testing.assert_frame_equal(salida, original)
    assert salida is not catalogo


def test_columna_sin_nombre_se_elimina_solo_si_esta_vacia(catalogo):
    catalogo["Unnamed: 4"] = np.nan
    original = catalogo.copy(deep=True)
    salida = auditoria.normalizar_catalogo(catalogo)
    assert "Unnamed: 4" not in salida.columns
    pd.testing.assert_frame_equal(catalogo, original)


def test_columna_sin_nombre_con_dato_no_se_descarta(catalogo):
    catalogo["Unnamed: 4"] = [np.nan, "dato que no debe perderse", np.nan]
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


@pytest.mark.parametrize("columna", ["ID_POLIGONO", "AREA_HA", "CONJUNTO", "RENDIMIENTO_T_HA"])
def test_catalogo_exige_columnas_significativas(catalogo, columna):
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo.drop(columns=columna))


def test_catalogo_rechaza_columna_inesperada(catalogo):
    catalogo["variable_no_documentada"] = 1
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


def test_catalogo_rechaza_identificador_duplicado(catalogo):
    catalogo.loc[1, "ID_POLIGONO"] = "AGC_001"
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_catalogo_rechaza_identificador_vacio(catalogo, valor):
    catalogo.loc[1, "ID_POLIGONO"] = valor
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


def test_catalogo_rechaza_conjunto_desconocido(catalogo):
    catalogo.loc[1, "CONJUNTO"] = "TEST"
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


def test_catalogo_rechaza_entrenamiento_sin_etiqueta(catalogo):
    catalogo.loc[0, "RENDIMIENTO_T_HA"] = np.nan
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


def test_catalogo_rechaza_oculta_con_etiqueta(catalogo):
    catalogo.loc[1, "RENDIMIENTO_T_HA"] = 3.0
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


@pytest.mark.parametrize("valor", [0.0, -1.0, np.inf, -np.inf, np.nan])
def test_catalogo_rechaza_area_no_positiva_finita(catalogo, valor):
    catalogo.loc[0, "AREA_HA"] = valor
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


@pytest.mark.parametrize("valor", [0.0, -1.0, np.inf, -np.inf])
def test_catalogo_rechaza_rendimiento_no_positivo_finito(catalogo, valor):
    catalogo.loc[0, "RENDIMIENTO_T_HA"] = valor
    with pytest.raises(ValueError):
        auditoria.normalizar_catalogo(catalogo)


def test_satelite_valido_no_modifica_original(satelite):
    original = satelite.copy(deep=True)
    auditoria.validar_satelite(satelite)
    pd.testing.assert_frame_equal(satelite, original)


@pytest.mark.parametrize("fecha", ["2025-02-01", "31/02/2025", "13/31/2025", "", None])
def test_satelite_fecha_invalida_no_se_infiere(satelite, fecha):
    satelite.loc[0, "fecha_captura"] = fecha
    with pytest.raises(ValueError):
        auditoria.validar_satelite(satelite)


def test_satelite_rechaza_duplicado_de_clave_compuesta(satelite):
    duplicado = pd.concat([satelite, satelite.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        auditoria.validar_satelite(duplicado)


def test_satelite_misma_fecha_sensor_distinto_no_es_duplicado(satelite):
    fila = satelite.iloc[[0]].copy()
    fila["sensor"] = "Landsat"
    valido = pd.concat([satelite, fila], ignore_index=True)
    auditoria.validar_satelite(valido)


def test_satelite_nubosidad_ausente_permanece_ausente(satelite):
    satelite.loc[0, "porcentaje_nubosidad"] = np.nan
    original = satelite.copy(deep=True)
    salida = auditoria.validar_satelite(satelite)
    assert pd.isna(salida.loc[0, "porcentaje_nubosidad"])
    pd.testing.assert_frame_equal(satelite, original)


@pytest.mark.parametrize("valor", [-0.01, 100.01, np.inf, -np.inf])
def test_satelite_rechaza_nubosidad_presente_invalida(satelite, valor):
    satelite.loc[0, "porcentaje_nubosidad"] = valor
    with pytest.raises(ValueError):
        auditoria.validar_satelite(satelite)


def test_zip_valido_inventaria_bytes_y_hash_sin_extraer(tmp_path):
    contenido = b"a,b\n1,2\n"
    buffer = _zip_memoria([("datos/tabla.csv", contenido)])
    with zipfile.ZipFile(buffer) as archivo:
        salida = auditoria.validar_zip(archivo)
    assert len(salida) == 1
    assert salida[0]["nombre"] == "datos/tabla.csv"
    assert salida[0]["bytes"] == len(contenido)
    assert salida[0]["sha256"] == hashlib.sha256(contenido).hexdigest()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "nombre",
    ["../archivo.csv", "/archivo.csv", "datos/../archivo.csv", "C:/archivo.csv", "datos\\archivo.csv"],
)
def test_zip_rechaza_rutas_ambiguas_o_fuera_de_raiz(nombre):
    with zipfile.ZipFile(_zip_memoria([(nombre, b"x")])) as archivo:
        with pytest.raises(ValueError):
            auditoria.validar_zip(archivo)


@pytest.mark.parametrize(
    "nombres", [("datos/tabla.csv", "datos/tabla.csv"), ("datos/tabla.csv", "DATOS/TABLA.CSV")]
)
def test_zip_rechaza_nombres_duplicados_o_colision_de_mayusculas(nombres):
    with zipfile.ZipFile(_zip_memoria([(nombre, b"x") for nombre in nombres])) as archivo:
        with pytest.raises(ValueError):
            auditoria.validar_zip(archivo)


def test_zip_limite_por_archivo_antes_de_cargar(monkeypatch):
    monkeypatch.setattr(auditoria, "MAX_ARCHIVO_BYTES", 3)
    with zipfile.ZipFile(_zip_memoria([("tabla.csv", b"1234")])) as archivo:
        with pytest.raises(ValueError):
            auditoria.validar_zip(archivo)


def test_zip_limite_total_antes_de_cargar(monkeypatch):
    monkeypatch.setattr(auditoria, "MAX_TOTAL_BYTES", 5)
    with zipfile.ZipFile(_zip_memoria([("a.csv", b"123"), ("b.csv", b"456")])) as archivo:
        with pytest.raises(ValueError):
            auditoria.validar_zip(archivo)


def test_zip_crc_corrupto_no_pasa():
    buffer = _zip_memoria([("tabla.csv", b"marca_original")])
    roto = buffer.getvalue().replace(b"marca_original", b"marca_alterada", 1)
    assert len(roto) == len(buffer.getvalue())
    with zipfile.ZipFile(io.BytesIO(roto)) as archivo:
        with pytest.raises((ValueError, zipfile.BadZipFile)):
            auditoria.validar_zip(archivo)


def test_miembro_unico_identifica_sufijo_exacto():
    with zipfile.ZipFile(_zip_memoria([("a/tabla.csv", b"x"), ("b/otra.csv", b"x")])) as archivo:
        assert auditoria.miembro_unico(archivo, "tabla.csv") == "a/tabla.csv"


@pytest.mark.parametrize("entradas", [[], [("a/tabla.csv", b"x"), ("b/tabla.csv", b"x")]])
def test_miembro_unico_rechaza_ausencia_y_ambiguedad(entradas):
    with zipfile.ZipFile(_zip_memoria(entradas)) as archivo:
        with pytest.raises(ValueError):
            auditoria.miembro_unico(archivo, "tabla.csv")


def test_leer_csv_acepta_bom_utf8():
    texto = "\ufeffID_POLIGONO,fecha_captura\nAGC_001,01/02/2025\n"
    with zipfile.ZipFile(_zip_memoria([("fuente/tabla.csv", texto.encode("utf-8"))])) as archivo:
        salida = auditoria.leer_csv(archivo, "tabla.csv")
    assert list(salida.columns) == ["ID_POLIGONO", "fecha_captura"]
    assert salida.loc[0, "ID_POLIGONO"] == "AGC_001"


def test_cargar_zip_rechaza_hash_no_oficial(tmp_path):
    ruta = tmp_path / "DataSet.zip"
    ruta.write_bytes(_zip_memoria([("tabla.csv", b"x")]).getvalue())
    original = ruta.read_bytes()
    with pytest.raises(ValueError):
        auditoria.cargar_zip(ruta)
    assert ruta.read_bytes() == original
    assert list(tmp_path.iterdir()) == [ruta]


def _zip_geometrias(anillos):
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    escritor = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    for campo in ["ID_POLIGON", "Estado", "Municipio", "Cultivo", "CONJUNTO"]:
        escritor.field(campo, "C", size=60)
    escritor.field("área_ha", "N", size=12, decimal=4)
    for numero, anillo in enumerate(anillos, 1):
        escritor.poly([anillo])
        escritor.record(f"AGC_{numero:03d}", "Puebla", "Chignahuapan", "Cebada", "ENTRENAMIENTO", 1.0)
    escritor.close()
    interno = _zip_memoria(
        [
            ("parcelas.shp", shp.getvalue()),
            ("parcelas.shx", shx.getvalue()),
            ("parcelas.dbf", dbf.getvalue()),
            ("parcelas.prj", CRS.from_epsg(4326).to_wkt().encode("utf-8")),
        ]
    )
    return _zip_memoria([("fuente/Parcelas_Reto_AGC_CONJUNTO_70_30.zip", interno.getvalue())])


def test_geometrias_conserva_poligono_y_crs_sin_extraer(tmp_path):
    anillo = [(-99, 20), (-99, 21), (-98, 21), (-98, 20), (-99, 20)]
    with zipfile.ZipFile(_zip_geometrias([anillo])) as archivo:
        tabla, geometrias, crs = auditoria.leer_geometrias(archivo)
    assert tabla.ID_POLIGONO.tolist() == ["AGC_001"]
    assert tabla.Municipio.tolist() == ["Chignahuapan"]
    assert tabla.AREA_HA_GEOMETRIA.tolist() == [1.0]
    assert geometrias[0].is_valid
    assert tuple(geometrias[0].exterior.coords) == tuple(anillo)
    assert crs == CRS.from_epsg(4326)
    assert list(tmp_path.iterdir()) == []


def test_geometrias_rechaza_autointerseccion_sin_repararla():
    anillo = [(-99, 20), (-98, 21), (-99, 21), (-98, 20), (-99, 20)]
    with zipfile.ZipFile(_zip_geometrias([anillo])) as archivo:
        original = archivo.read(archivo.namelist()[0])
        with pytest.raises(ValueError):
            auditoria.leer_geometrias(archivo)
        assert archivo.read(archivo.namelist()[0]) == original


def test_miembro_unico_exige_nombre_y_no_solo_sufijo():
    with zipfile.ZipFile(_zip_memoria([("a/notabla.csv", b"x")])) as archivo:
        with pytest.raises(ValueError):
            auditoria.miembro_unico(archivo, "tabla.csv")


def test_sensor_vacio_no_es_categoria_valida():
    tabla = pd.DataFrame({
        "ID_POLIGONO": ["AGC_001"], "fecha_captura": ["01/02/2025"],
        "sensor": ["  "], "porcentaje_nubosidad": [np.nan],
    })
    with pytest.raises(ValueError):
        auditoria.validar_satelite(tabla)
