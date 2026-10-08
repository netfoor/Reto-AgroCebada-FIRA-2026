"""Controles sintéticos de receta histórica y controles geoespaciales adicionales."""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pyproj import Geod
from rasterio.io import MemoryFile
from rasterio.transform import Affine
from shapely.geometry import Polygon, box


ARCHIVO = Path(__file__).resolve().parents[1] / "scripts/fuentes_02_geo.py"
SPEC = importlib.util.spec_from_file_location("fuentes_02_geo", ARCHIVO)
G = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(G)
X0, Y0 = 500_000.0, 2_200_000.0
AFIN = Affine(100, 0, X0, 0, -100, Y0)


def geotiff(valores=None, afin=AFIN, crs="EPSG:32614", nodata=-9999.0, mascara=None, punto=False):
    v = (
        np.arange(12, dtype=np.float32).reshape(3, 4)
        if valores is None
        else np.asarray(valores, dtype=np.float32)
    )
    with MemoryFile() as mf:
        with mf.open(
            driver="GTiff",
            width=v.shape[1],
            height=v.shape[0],
            count=1,
            dtype="float32",
            crs=crs,
            transform=afin,
            nodata=nodata,
        ) as src:
            src.write(v, 1)
            if mascara is not None:
                src.write_mask(np.asarray(mascara, dtype=np.uint8))
            if punto:
                src.update_tags(AREA_OR_POINT="Point")
        return mf.read()


def test_campo_constante_y_pesos_03_07():
    g = box(X0 + 70, Y0 - 80, X0 + 170, Y0 - 30)
    v = np.full((3, 4), 42.5)
    r = G.extraer_raster(geotiff(v), {"a": g}, 32614, stats=True)["a"]
    assert r["pond"] == 42.5 and r["std"] == 0 and r["n_celdas"] == 2
    assert r["cobertura_total"] == 1 and r["frac_valida"] == 1
    v[0, 0], v[0, 1] = 10, 20
    r = G.extraer_raster(geotiff(v), {"a": g}, 32614)["a"]
    assert r["pond"] == 17 and r["cent"] == 20
    p = G.piezas_parcela_raster(geotiff(v), g, 32614)["piezas"]
    assert [x["peso_normalizado"] for x in p] == [0.3, 0.7]


def test_contacto_borde_y_esquina_tienen_area_cero():
    g = box(X0 + 20, Y0 - 80, X0 + 100, Y0 - 20)
    r = G.extraer_raster(geotiff(), {"a": g}, 32614)["a"]
    assert r["n_celdas"] == 1 and r["pond"] == 0
    g = Polygon([(X0 + 100, Y0 - 100), (X0 + 150, Y0 - 150), (X0 + 100, Y0 - 150)])
    assert G.extraer_raster(geotiff(), {"a": g}, 32614)["a"]["n_celdas"] == 1


def test_nodata_nan_infinito_y_mascara_explicita():
    g = box(X0 + 50, Y0 - 80, X0 + 150, Y0 - 20)
    for malo, nodata in [(-9999.0, -9999.0), (np.nan, None), (np.inf, None), (np.nan, np.nan)]:
        v = np.full((3, 4), 7.0)
        v[0, 1] = malo
        r = G.extraer_raster(geotiff(v, nodata=nodata), {"a": g}, 32614, stats=True)["a"]
        assert r["pond"] == 7 and r["frac_valida"] == 0.5 and r["cobertura_total"] == 0.5
        assert r["n_validos"] == 1
        v[0, 0] = malo
        r = G.extraer_raster(geotiff(v, nodata=nodata), {"a": g}, 32614, stats=True)["a"]
        assert np.isnan(r["pond"]) and r["frac_valida"] == 0 and r["n_validos"] == 0
    mask = np.full((3, 4), 255)
    mask[0, 1] = 0
    r = G.extraer_raster(geotiff(np.full((3, 4), 5.0), mascara=mask), {"a": g}, 32614)["a"]
    assert r["pond"] == 5 and r["frac_valida"] == 0.5


def test_fuera_parcial_y_denominadores_cobertura():
    geoms = {
        "fuera": box(X0 - 200, Y0 - 80, X0 - 100, Y0 - 20),
        "parcial": box(X0 - 10, Y0 - 80, X0 + 90, Y0 - 20),
    }
    r = G.extraer_raster(geotiff(np.ones((3, 4))), geoms, 32614)
    assert np.isnan(r["fuera"]["pond"]) and np.isnan(r["fuera"]["frac_valida"])
    assert np.isnan(r["fuera"]["cent"]) and r["fuera"]["n_celdas"] == 0
    assert r["parcial"]["pond"] == 1 and r["parcial"]["frac_valida"] == 1
    assert r["parcial"]["cobertura_total"] == 0.9 and r["parcial"]["cobertura_malla"] == 0.9


def test_centro_de_pixel_no_es_esquina_ni_centroide():
    g = box(X0 + 95, Y0 - 105, X0 + 105, Y0 - 95)
    p = G.piezas_parcela_raster(geotiff(), g, 32614)
    assert len(p["piezas"]) == 4 and p["celda_centroide"] == (1, 1)
    primera = p["piezas"][0]
    assert primera["esquina_ul"] == (X0, Y0) and primera["centro"] == (X0 + 50, Y0 - 50)
    assert G.extraer_raster(geotiff(), {"a": g}, 32614)["a"]["pond"] == 2.5


@pytest.mark.parametrize("grados", [30.0, -17.0])
def test_rotacion_y_cizalla_contra_calculo_en_pixel(grados):
    afin = Affine.translation(X0, Y0) @ Affine.rotation(grados) @ Affine(100, 13, 0, 0, -100, 0)
    v = np.arange(36, dtype=float).reshape(6, 6)
    vertices = [(1.3, 0.7), (3.6, 1.1), (4.2, 3.9), (0.8, 2.5)]
    g = Polygon([afin @ p for p in vertices])
    gp = Polygon(vertices)
    piezas = G.piezas_parcela_raster(geotiff(v, afin), g, 32614)["piezas"]
    pesos = {(p["fila"], p["col"]): p["area_peso"] for p in piezas}
    ref = {
        (fi, co): gp.intersection(box(co, fi, co + 1, fi + 1)).area * abs(afin.determinant)
        for fi in range(6)
        for co in range(6)
        if gp.intersection(box(co, fi, co + 1, fi + 1)).area > 0
    }
    assert set(pesos) == set(ref) and max(abs(pesos[k] - ref[k]) for k in ref) < 1e-6


def test_cache_geometria_subconjunto_orden_y_malla_desplazada():
    b = geotiff()
    a = box(X0 + 10, Y0 - 90, X0 + 90, Y0 - 10)
    z = box(X0 + 210, Y0 - 290, X0 + 290, Y0 - 210)
    cache = {}
    assert G.extraer_raster(b, {"a": a}, 32614, cache)["a"]["pond"] == 0
    full = G.extraer_raster(b, {"a": a, "z": z}, 32614, cache)
    assert set(full) == {"a", "z"} and full["z"]["pond"] == 10 and len(cache) == 2
    assert G.extraer_raster(b, {"z": z, "a": a}, 32614, cache) == full and len(cache) == 2
    assert G.extraer_raster(b, {"a": z}, 32614, cache)["a"]["pond"] == 10 and len(cache) == 3
    desplazada = geotiff(afin=Affine(100, 0, X0 - 50, 0, -100, Y0))
    assert G.extraer_raster(desplazada, {"a": a}, 32614, cache)["a"]["pond"] == 0.5
    assert len(cache) == 4
    minima = geotiff(afin=Affine(100, 0, X0 + 1e-9, 0, -100, Y0))
    assert G.analizar_raster(minima)["huella_malla"] != G.analizar_raster(b)["huella_malla"]


def test_cache_no_reutiliza_valores_ni_mascara():
    g = box(X0 + 50, Y0 - 80, X0 + 150, Y0 - 20)
    cache = {}
    assert G.extraer_raster(geotiff(np.ones((3, 4))), {"a": g}, 32614, cache)["a"]["pond"] == 1
    v = np.full((3, 4), 9.0)
    v[0, 1] = -9999
    r = G.extraer_raster(geotiff(v), {"a": g}, 32614, cache)["a"]
    assert len(cache) == 1 and r["pond"] == 9 and r["frac_valida"] == 0.5


def test_area_geografica_utm_no_grados_y_topografia_area_nativa():
    afin = Affine(0.05, 0, -98.6, 0, -0.05, 19.9)
    g = box(-98.545, 19.80, -98.505, 19.89)
    p = G.piezas_parcela_raster(geotiff(np.ones((4, 4)), afin, "EPSG:4326"), g, 4326)
    assert p["metadata"]["epsg_area"] == 32614
    geod = Geod(ellps="WGS84")
    pesos = np.array([x["area_peso"] for x in p["piezas"]])
    pesos /= pesos.sum()
    geodesicos = np.array(
        [abs(geod.geometry_area_perimeter(x["interseccion"])[0]) for x in p["piezas"]]
    )
    geodesicos /= geodesicos.sum()
    grados = np.array([x["area_crs"] for x in p["piezas"]])
    grados /= grados.sum()
    assert np.max(abs(pesos - geodesicos)) < 1e-5 and np.max(abs(pesos - grados)) > 1e-6
    assert G.analizar_raster(geotiff(crs="EPSG:6372"))["epsg_area"] == 6372


def test_geometrias_invalidas_y_point_rechazados():
    invalida = Polygon(
        [(X0 + 10, Y0 - 10), (X0 + 90, Y0 - 90), (X0 + 90, Y0 - 10), (X0 + 10, Y0 - 90)]
    )
    for g in [None, Polygon(), invalida]:
        with pytest.raises(ValueError):
            G.extraer_raster(geotiff(), {"a": g}, 32614)
    with pytest.raises(ValueError):
        G.analizar_raster(geotiff(punto=True))
    with pytest.raises(ValueError, match="no invertible"):
        G._metadata_geo(
            type("Fuente", (), {"crs": "EPSG:32614", "count": 1, "transform": (1, 1, 0, 1, 1, 0)})()
        )


def test_metadatos_del_shapefile_y_proyeccion_ejes():
    g = box(-98.5, 19.5, -98.49, 19.51)
    tabla = pd.DataFrame(
        [
            {
                "ID_POLIGON": "AGC_001",
                "Estado": "Puebla",
                "Municipio": "M",
                "Cultivo": "Cebada",
                "área_ha": 10.0,
                "CONJUNTO": "PREDICCION",
            }
        ]
    )
    geoms, meta = G.metadatos_geo(tabla, [g], 4326)
    assert len(meta.columns) == 13 and "RENDIMIENTO_T_HA" not in meta
    assert geoms["AGC_001"].equals_exact(g, 0) and meta.geom_vertices_repetidos.iloc[0] == 0
    assert -99 < meta.longitude.iloc[0] < -98 and 19 < meta.latitude.iloc[0] < 20
    assert meta.area_geom_ha.iloc[0] > 0 and meta.geom_valida_original.iloc[0]
