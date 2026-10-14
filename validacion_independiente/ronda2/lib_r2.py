"""Ronda 2: variables externas a escala de parcela (solo X) y corrección penalizada sobre E_JK y MIX."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import shapefile
import shapely
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import lib_validacion as L  # noqa: E402  (no se modifica)
from modelo_10 import aplicar_correccion, ajustar_correccion  # noqa: E402  (misma fórmula de K, α = 10)

DATOS = AQUI / "datos"
SEMILLA_CV2 = 20261021
SEMILLA_CAJA2 = 20261024
RADIO_TPI_M = 1000.0
ESPESORES = {"0-5cm": 5.0, "5-15cm": 10.0, "15-30cm": 15.0}
HIPOTESIS = {"H1": "tpi_1km_m", "H2": "soc_0_30_dgkg"}
BASES = ["E_JK", "MIX"]


def poligonos() -> dict:
    z = zipfile.ZipFile(L.RAIZ / "data/raw/DataSet.zip")
    inner = zipfile.ZipFile(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30.zip")))
    pt = {n.rsplit(".", 1)[-1].lower(): n for n in inner.namelist() if n.lower().endswith((".shp", ".dbf", ".shx"))}
    r = shapefile.Reader(shp=io.BytesIO(inner.read(pt["shp"])), dbf=io.BytesIO(inner.read(pt["dbf"])),
                         shx=io.BytesIO(inner.read(pt["shx"])), encoding="utf-8")
    return {rec["ID_POLIGON"]: transform(lambda x, y, z=None: (x, y), shape(s.__geo_interface__)) for rec, s in zip(r.records(), r.shapes())}


def _media_en_poligono(src, poly_crs, valores_validos=lambda a: np.isfinite(a)):
    """Media de los píxeles con centro dentro del polígono; si ninguno, el píxel que contiene el centroide."""
    minx, miny, maxx, maxy = poly_crs.bounds
    w = rasterio.windows.from_bounds(minx, miny, maxx, maxy, transform=src.transform).round_offsets(op="floor").round_lengths(op="ceil")
    w = rasterio.windows.Window(w.col_off - 1, w.row_off - 1, w.width + 2, w.height + 2)
    a = src.read(1, window=w, boundless=True, fill_value=src.nodata if src.nodata is not None else np.nan).astype(float)
    if src.nodata is not None:
        a[a == src.nodata] = np.nan
    t = src.window_transform(w)
    cols, rows = np.meshgrid(np.arange(a.shape[1]) + 0.5, np.arange(a.shape[0]) + 0.5)
    xs, ys = t * (cols, rows)
    dentro = shapely.contains_xy(poly_crs, xs, ys) & valores_validos(a)
    if dentro.any():
        return float(a[dentro].mean()), int(dentro.sum())
    c = poly_crs.centroid
    r, cc = src.index(c.x, c.y)
    v = src.read(1, window=rasterio.windows.Window(cc, r, 1, 1), boundless=True).astype(float)[0, 0]
    return (np.nan if (src.nodata is not None and v == src.nodata) else float(v)), 0


def variables_externas() -> pd.DataFrame:
    polys = poligonos()
    utm = Transformer.from_crs(4326, 32614, always_xy=True)
    filas = {p: {} for p in polys}
    # H1: TPI a 1 km con Copernicus DEM GLO-30 (EPSG:4326)
    with rasterio.open(DATOS / "copernicus_dem_glo30_N19_W099.tif") as dem:
        for p, g in polys.items():
            elev, n = _media_en_poligono(dem, g)
            cx, cy = utm.transform(g.centroid.x, g.centroid.y)
            minx, miny, maxx, maxy = g.centroid.buffer(0.012).bounds              # ~1.3 km en grados
            w = rasterio.windows.from_bounds(minx, miny, maxx, maxy, transform=dem.transform).round_offsets().round_lengths()
            a = dem.read(1, window=w).astype(float)
            t = dem.window_transform(w)
            cols, rows = np.meshgrid(np.arange(a.shape[1]) + 0.5, np.arange(a.shape[0]) + 0.5)
            lon, lat = t * (cols, rows)
            ux, uy = utm.transform(lon, lat)
            disco = np.hypot(ux - cx, uy - cy) <= RADIO_TPI_M
            filas[p].update(elev_dem30_m=elev, n_pix_dem=n, tpi_1km_m=elev - float(a[disco].mean()), n_pix_disco=int(disco.sum()))
    # H2: carbono orgánico 0-30 cm (SoilGrids, Homolosine), media ponderada por espesor
    igh = Transformer.from_crs(4326, "+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs", always_xy=True)
    capas = {}
    for prof in ESPESORES:
        with rasterio.open(DATOS / f"soilgrids_soc_{prof}_mean.tif") as s:
            for p, g in polys.items():
                v, n = _media_en_poligono(s, transform(lambda x, y, z=None: igh.transform(x, y), g))
                capas.setdefault(prof, {})[p] = v
                filas[p][f"n_pix_soil_{prof}"] = n
    for p in polys:
        vals = [capas[prof][p] for prof in ESPESORES]
        filas[p]["soc_0_30_dgkg"] = float(np.dot(vals, list(ESPESORES.values())) / sum(ESPESORES.values())) if np.all(np.isfinite(vals)) else np.nan
    return pd.DataFrame.from_dict(filas, orient="index").rename_axis(L.ID).reset_index().sort_values(L.ID).reset_index(drop=True)


def bases_y_residuos(tx, y, tr, va, internas_fold, semilla_base):
    """Predicciones de E_JK y MIX en va (entrenadas con tr) y sus residuos en tr obtenidos por pliegues internos.
    Para cada pliegue interno, K necesita sus propios pliegues internos: semilla_base + k."""
    cong = L.congelados(tx, y, tr, va, internas_fold)
    e = {b: pd.Series(np.nan, index=np.asarray(tr)) for b in BASES}
    for k, g in internas_fold.groupby("pliegue_interno"):
        itr = g.loc[g.rol.eq("entrenamiento"), L.ID].to_numpy()
        iva = g.loc[g.rol.eq("validacion"), L.ID].to_numpy()
        ci = L.congelados(tx, y, itr, iva, L.internas_unicas(itr, semilla_base + int(k)))
        for b in BASES:
            e[b].loc[iva] = y.loc[iva].to_numpy() - ci[b]
    assert all(not s.isna().any() for s in e.values())
    return cong, e


def corregir(base_va, e_tr, z: pd.Series, va):
    p = ajustar_correccion(z, e_tr)
    c, respaldo = aplicar_correccion(p, z, np.asarray(va))
    return base_va + c, p
