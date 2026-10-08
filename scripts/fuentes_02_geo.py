"""Geometría y extracción del cuaderno 02, autocontenidas para incrustar en Colab.

Adaptación del 7 de octubre de 2026 de integracion_v0/agro_v0/base.py y
raster.py, con los controles de malla, afín completa y caché de
fortino-pruebas/v2-lluvia-octubre-validacion-comun-30sep/verificacion/nucleo_lluvia.py
(verificación del 1 de octubre de 2026). No entrena ni consulta rendimiento.

Se conserva la receta histórica: intersecciones en el CRS del ráster, áreas
UTM14N para EPSG:4326 y áreas nativas para topografía EPSG:6372, sin
densificación ni ajuste de coordenadas. La media y desviación poblacional se
normalizan sobre área válida. frac_valida usa la suma de piezas como
denominador; cobertura_total y cobertura_malla son diagnósticos adicionales,
con área de la parcela como denominador. No se impone el umbral V2 de lluvia
a las variables históricas de topografía.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer
from rasterio.io import MemoryFile
from shapely import force_2d, wkb
from shapely.geometry import Polygon
from shapely.ops import transform as geo_transform


VERSION_GEO_02 = "v0-area-con-controles-20261007"


def _validar_geometria(geometria):
    if geometria is None or geometria.is_empty or not geometria.is_valid:
        raise ValueError("Geometría nula, vacía o inválida; no se repara automáticamente")
    if geometria.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("La parcela debe ser Polygon o MultiPolygon")
    return force_2d(geometria)


def _vertices_geo(geometria):
    poligonos = [geometria] if geometria.geom_type == "Polygon" else list(geometria.geoms)
    partes = []
    for poligono in poligonos:
        partes.append(np.asarray(poligono.exterior.coords)[:, :2])
        partes.extend(np.asarray(anillo.coords)[:, :2] for anillo in poligono.interiors)
    return np.vstack(partes)


def proyectar_geometrias(geometrias, crs_origen, crs_destino):
    """Devuelve un dict nuevo con los mismos IDs y geometrías 2D válidas."""
    origen, destino = CRS.from_user_input(crs_origen), CRS.from_user_input(crs_destino)
    proyectar = Transformer.from_crs(origen, destino, always_xy=True).transform
    return {
        identificador: _validar_geometria(geo_transform(proyectar, _validar_geometria(g)))
        for identificador, g in geometrias.items()
    }


def metadatos_geo(tabla_shp, geometrias, crs_origen):
    """(dict de geometrías, DataFrame) con los 13 campos de base.load_geometries.

    tabla_shp contiene ID_POLIGON, Estado, Municipio, Cultivo, área_ha y
    CONJUNTO. geometrias puede ser un dict por ID o una secuencia en el orden
    de tabla_shp. Las geometrías devueltas permanecen en crs_origen.
    """
    tabla = pd.DataFrame(tabla_shp).copy()
    requeridas = ["ID_POLIGON", "Estado", "Municipio", "Cultivo", "área_ha", "CONJUNTO"]
    faltan = set(requeridas) - set(tabla.columns)
    if faltan:
        raise ValueError(f"Faltan atributos del shapefile: {sorted(faltan)}")
    if tabla.ID_POLIGON.isna().any() or tabla.ID_POLIGON.duplicated().any():
        raise ValueError("Los IDs del shapefile deben ser únicos y no nulos")
    if isinstance(geometrias, Mapping):
        if set(geometrias) != set(tabla.ID_POLIGON):
            raise ValueError("Los IDs de las geometrías y atributos difieren")
        originales = dict(geometrias)
    else:
        secuencia = list(geometrias)
        if len(secuencia) != len(tabla):
            raise ValueError("El número de geometrías y registros difiere")
        originales = dict(zip(tabla.ID_POLIGON, secuencia))
    origen = CRS.from_user_input(crs_origen)
    a_metros = Transformer.from_crs(origen, 32614, always_xy=True).transform
    a_grados = Transformer.from_crs(32614, 4326, always_xy=True).transform
    salida, filas = {}, []
    for registro in tabla.to_dict("records"):
        identificador = registro["ID_POLIGON"]
        g = _validar_geometria(originales[identificador])
        pts = _vertices_geo(g)
        repetidos = int((np.abs(np.diff(pts, axis=0)).sum(axis=1) == 0).sum())
        gm = geo_transform(a_metros, g)
        centro = gm.centroid
        longitud, latitud = a_grados(centro.x, centro.y)
        salida[identificador] = g
        filas.append(
            {
                "ID_POLIGONO": identificador,
                "Estado": registro["Estado"],
                "Municipio": registro["Municipio"],
                "cultivo_grafia_original": registro["Cultivo"],
                "AREA_HA_shp": registro["área_ha"],
                "area_geom_ha": gm.area / 1e4,
                "x_m": centro.x,
                "y_m": centro.y,
                "longitude": longitud,
                "latitude": latitud,
                "geom_valida_original": True,
                "geom_vertices_repetidos": repetidos,
                "CONJUNTO_shp": registro["CONJUNTO"],
            }
        )
    return salida, pd.DataFrame(filas).sort_values("ID_POLIGONO").reset_index(drop=True)


def _crs_area_geo(crs_raster):
    crs = CRS.from_user_input(crs_raster)
    if crs.to_epsg() == 4326:
        return CRS.from_epsg(32614)
    if crs.is_projected and all(eje.unit_conversion_factor == 1 for eje in crs.axis_info[:2]):
        return crs
    raise ValueError("La receta requiere EPSG:4326 o un CRS proyectado en metros")


def _metadata_geo(src):
    if src.crs is None:
        raise ValueError("Ráster sin CRS")
    if src.count != 1:
        raise ValueError("Se requiere un ráster de una banda")
    afin = tuple(float(v) for v in tuple(src.transform)[:6])
    a, b, _, d, e, _ = afin
    det = a * e - b * d
    if not all(math.isfinite(v) for v in afin) or not math.isfinite(det) or det == 0:
        raise ValueError("Transformada afín no finita o no invertible")
    if src.width <= 0 or src.height <= 0:
        raise ValueError("Dimensiones de ráster no positivas")
    crs = CRS.from_user_input(src.crs)
    area = _crs_area_geo(crs)
    tags = src.tags()
    if tags.get("AREA_OR_POINT") == "Point":
        raise ValueError("La receta histórica requiere píxeles de área, no PixelIsPoint")
    documento = {
        "transform": [repr(v) for v in afin],
        "width": src.width,
        "height": src.height,
        "crs": crs.to_wkt(version="WKT2_2019"),
    }
    huella = hashlib.sha256(json.dumps(documento, sort_keys=True).encode()).hexdigest()
    return {
        "transform": afin,
        "width": src.width,
        "height": src.height,
        "crs_wkt": crs.to_wkt(),
        "epsg": crs.to_epsg(),
        "nodata": src.nodata,
        "dtype": src.dtypes[0],
        "count": src.count,
        "tags": tags,
        "tipo_pixel": tags.get("AREA_OR_POINT"),
        "crs_area_wkt": area.to_wkt(),
        "epsg_area": area.to_epsg(),
        "huella_malla": huella,
        "rotada": b != 0 or d != 0,
    }


def analizar_raster(contenido_bytes):
    """Metadatos de un GeoTIFF en memoria, incluida la huella exacta de su malla."""
    with MemoryFile(contenido_bytes) as archivo, archivo.open() as src:
        return _metadata_geo(src)


def _a_mundo_geo(afin, col, fila):
    a, b, c, d, e, f = afin
    return a * col + b * fila + c, d * col + e * fila + f


def _a_pixel_geo(afin, x, y):
    a, b, c, d, e, f = afin
    det = a * e - b * d
    dx, dy = np.asarray(x, dtype=float) - c, np.asarray(y, dtype=float) - f
    return (e * dx - b * dy) / det, (-d * dx + a * dy) / det


def _pesos_geo(metadata, geometria_raster):
    g = _validar_geometria(geometria_raster)
    crs = CRS.from_wkt(metadata["crs_wkt"])
    crs_area = CRS.from_wkt(metadata["crs_area_wkt"])
    a_area = (
        (lambda x, y, z=None: (x, y))
        if crs == crs_area
        else Transformer.from_crs(crs, crs_area, always_xy=True).transform
    )
    afin = metadata["transform"]
    u, v = _a_pixel_geo(afin, *_vertices_geo(g).T)
    col0, col1 = math.floor(u.min()), math.floor(u.max())
    fila0, fila1 = math.floor(v.min()), math.floor(v.max())
    piezas = []
    for fila in range(max(fila0, 0), min(fila1, metadata["height"] - 1) + 1):
        for col in range(max(col0, 0), min(col1, metadata["width"] - 1) + 1):
            esquinas = [
                _a_mundo_geo(afin, co, fi)
                for co, fi in [(col, fila), (col + 1, fila), (col + 1, fila + 1), (col, fila + 1)]
            ]
            pixel = Polygon(esquinas)
            pieza = g.intersection(pixel)
            if pieza.is_empty or pieza.area <= 0:
                continue
            area_peso = float(geo_transform(a_area, pieza).area)
            piezas.append(
                {
                    "fila": fila,
                    "col": col,
                    "area_peso": area_peso,
                    "area_crs": float(pieza.area),
                    "fraccion_celda": float(pieza.area / pixel.area),
                    "pixel": pixel,
                    "interseccion": pieza,
                    "esquinas": esquinas,
                    "esquina_ul": esquinas[0],
                    "centro": _a_mundo_geo(afin, col + 0.5, fila + 0.5),
                }
            )
    centro = g.centroid
    cu, cv = _a_pixel_geo(afin, centro.x, centro.y)
    area_total = float(geo_transform(a_area, g).area)
    if not math.isfinite(area_total) or area_total <= 0:
        raise ValueError("El área de la parcela debe ser finita y positiva")
    return {
        "piezas": piezas,
        "area_parcela": area_total,
        "area_malla": float(sum(p["area_peso"] for p in piezas)),
        "celda_centroide": (math.floor(float(cv)), math.floor(float(cu))),
        "centroide_xy": (centro.x, centro.y),
        "geometria_raster": g,
    }


def _clave_cache_geo(metadata, geometrias, crs_geoms):
    documento = {
        "version": VERSION_GEO_02,
        "malla": metadata["huella_malla"],
        "crs_geoms": CRS.from_user_input(crs_geoms).to_wkt(version="WKT2_2019"),
        "crs_area": CRS.from_wkt(metadata["crs_area_wkt"]).to_wkt(version="WKT2_2019"),
    }
    huella = hashlib.sha256(json.dumps(documento, sort_keys=True).encode())
    for identificador in sorted(geometrias, key=str):
        g = _validar_geometria(geometrias[identificador])
        huella.update(
            repr(identificador).encode() + b"\0" + wkb.dumps(g, output_dimension=2) + b"\0"
        )
    return huella.hexdigest()


def _valores_y_mascara_geo(src):
    valores = src.read(1).astype(float)
    malos = ~np.isfinite(valores) | (src.dataset_mask() == 0) | (src.read_masks(1) == 0)
    if src.nodata is not None and np.isfinite(src.nodata):
        malos |= valores == src.nodata
    return valores, malos


def extraer_raster(contenido_bytes, geomsdict, crs_geoms, cache=None, stats=False):
    """ID -> pond, cent, frac_valida y diagnósticos; opcionalmente min/max/std/n_validos.

    El centroide del control se calcula en el CRS propio del ráster. Su celda
    se asigna mediante floor de la afín inversa (bordes semiabiertos). La
    caché almacena geometría/pesos; cada archivo aporta sus valores y máscara.
    """
    cache = {} if cache is None else cache
    with MemoryFile(contenido_bytes) as archivo, archivo.open() as src:
        metadata = _metadata_geo(src)
        clave = _clave_cache_geo(metadata, geomsdict, crs_geoms)
        if clave not in cache:
            proyectadas = proyectar_geometrias(geomsdict, crs_geoms, metadata["crs_wkt"])
            cache[clave] = {
                identificador: _pesos_geo(metadata, g) for identificador, g in proyectadas.items()
            }
        pesos = cache[clave]
        valores, malos = _valores_y_mascara_geo(src)
        salida = {}
        for identificador, datos in pesos.items():
            validas = [
                (float(valores[p["fila"], p["col"]]), p["area_peso"])
                for p in datos["piezas"]
                if not malos[p["fila"], p["col"]]
            ]
            den = float(sum(peso for _, peso in validas))
            tot = datos["area_malla"]
            pond = sum(valor * peso for valor, peso in validas) / den if den > 0 else np.nan
            fila, col = datos["celda_centroide"]
            dentro = 0 <= fila < src.height and 0 <= col < src.width
            cent = float(valores[fila, col]) if dentro and not malos[fila, col] else np.nan
            resultado = {
                "pond": pond,
                "cent": cent,
                "frac_valida": den / tot if tot > 0 else np.nan,
                "n_celdas": len(datos["piezas"]),
                "celda_centroide": f"R{fila}_C{col}",
                "cobertura_total": den / datos["area_parcela"],
                "cobertura_malla": tot / datos["area_parcela"],
            }
            if stats:
                v = np.asarray([valor for valor, _ in validas])
                w = np.asarray([peso for _, peso in validas])
                resultado.update(
                    {
                        "min": float(v.min()) if len(v) else np.nan,
                        "max": float(v.max()) if len(v) else np.nan,
                        "n_validos": len(v),
                        "std": float(np.sqrt(np.average((v - pond) ** 2, weights=w)))
                        if len(v)
                        else np.nan,
                    }
                )
            salida[identificador] = resultado
        return salida


def piezas_parcela_raster(contenido_bytes, geometria, crs_geoms):
    """Geometría, piezas, esquinas/centros, pesos y valores para una figura didáctica.

    Devuelve dict con metadata, geometria_raster, centroide_xy,
    celda_centroide (fila,col), area_parcela, area_malla y piezas. Cada pieza
    incluye pixel/interseccion shapely, área-peso, coordenadas, valor,
    valido y pesos normalizados sobre todas las piezas y sobre piezas válidas.
    """
    with MemoryFile(contenido_bytes) as archivo, archivo.open() as src:
        metadata = _metadata_geo(src)
        g = proyectar_geometrias({"parcela": geometria}, crs_geoms, metadata["crs_wkt"])["parcela"]
        datos = _pesos_geo(metadata, g)
        valores, malos = _valores_y_mascara_geo(src)
        area_valida = sum(p["area_peso"] for p in datos["piezas"] if not malos[p["fila"], p["col"]])
        for pieza in datos["piezas"]:
            fila, col = pieza["fila"], pieza["col"]
            valido = not bool(malos[fila, col])
            pieza.update(
                {
                    "valor": float(valores[fila, col]),
                    "valido": valido,
                    "peso_normalizado": pieza["area_peso"] / datos["area_malla"],
                    "peso_valido_normalizado": pieza["area_peso"] / area_valida
                    if valido and area_valida > 0
                    else 0.0,
                }
            )
        return {"metadata": metadata, **datos}
