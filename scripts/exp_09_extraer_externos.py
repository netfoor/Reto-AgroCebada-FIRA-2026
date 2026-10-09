"""Extrae fuentes externas públicas por parcela para EXP_09 (solo X, sin etiquetas).

Fuentes:
  s2   Sentinel-2 L2A (Microsoft Planetary Computer): B03,B04,B05,B08,B8A,B11 a 20 m,
       píxeles con SCL ∈ {4,5}, reflectancia = (DN − 1000)/10000 (línea base 05.11).
  s1   Sentinel-1 RTC (Planetary Computer), órbita relativa 5 ascendente: media lineal VV, VH.
  aef  AlphaEarth Foundations Satellite Embedding V1 (source.coop, CC-BY 4.0), 2022–2025:
       media por parcela del vector de 64 dimensiones, decuantizado.

Uso, desde la raíz del proyecto:
    uv run --locked --all-groups python scripts/exp_09_extraer_externos.py s2 [--limite N] [--salida DIR]

Las escenas se toman de data/exp_09_fuentes_externas/escenas_usadas.json para reproducir el
mismo conjunto. La extracción completa tarda ~15 min (S2), ~9 min (S1) y ~5 min (AEF).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
import shapefile
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom
from rasterio.windows import Window, from_bounds
from shapely.geometry import mapping, shape
from shapely.ops import transform, unary_union

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "data/exp_09_fuentes_externas"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
os.environ.update(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
                  GDAL_HTTP_MAX_RETRY="5", GDAL_HTTP_RETRY_DELAY="2", AWS_NO_SIGN_REQUEST="YES")
AEF = {  # archivos que cubren las 197 parcelas, localizados con aef_index.gpkg (EPSG:32614)
    y: [f"https://data.source.coop/tge-labs/aef/v1/annual/{y}/14N/{n}-0000000000-{c}.tiff" for c in ("0000000000", "0000008192")]
    for y, n in {2022: "x0bnk6qdg6ccaxr9e", 2023: "xr2iq8hxgl7y7da7q", 2024: "xat06bojgt1wm9ti3", 2025: "xzpmwhy67773ngskj"}.items()
}


def parcelas():
    z = zipfile.ZipFile(RAIZ / "data/raw/DataSet.zip")
    interno = zipfile.ZipFile(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/Parcelas_Reto_AGC_CONJUNTO_70_30.zip")))
    partes = {n.rsplit(".", 1)[-1].lower(): n for n in interno.namelist() if n.lower().endswith((".shp", ".dbf", ".shx"))}
    r = shapefile.Reader(shp=io.BytesIO(interno.read(partes["shp"])), dbf=io.BytesIO(interno.read(partes["dbf"])),
                         shx=io.BytesIO(interno.read(partes["shx"])), encoding="utf-8")
    a_utm = Transformer.from_crs(4326, 32614, always_xy=True).transform
    out = {}
    for rec, s in zip(r.records(), r.shapes()):
        g = transform(lambda x, y, z=None: (x, y), shape(s.__geo_interface__))
        out[rec["ID_POLIGON"]] = {"ll": g, "utm": transform(lambda x, y, z=None: a_utm(x, y), g)}
    return out


P = parcelas()


def grupos(pids, buffer_m=600):
    u = unary_union([P[p]["utm"].buffer(buffer_m) for p in pids])
    return [[p for p in pids if g.intersects(P[p]["utm"])] for g in getattr(u, "geoms", [u])]


class Token:
    def __init__(self, coleccion):
        self.c, self.t, self.ts, self.lock = coleccion, None, 0.0, threading.Lock()

    def __call__(self):
        with self.lock:
            for k in range(8):
                if time.time() - self.ts <= 1800:
                    break
                try:
                    self.t = requests.get(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{self.c}", timeout=60).json()["token"]
                    self.ts = time.time()
                except Exception:
                    time.sleep(5 * (k + 1))
            return self.t


def items(coleccion, ids):
    out = []
    for i in range(0, len(ids), 100):
        d = requests.post(STAC, json={"collections": [coleccion], "ids": ids[i:i + 100], "limit": 100}, timeout=120).json()
        out += d["features"]
    assert len(out) == len(ids), "Faltan escenas en el catálogo"
    return sorted(out, key=lambda f: f["id"])


def s2(it, tok, cl_por_tesela):
    bandas = ["B03", "B04", "B05", "B08", "B8A", "B11", "SCL"]
    tesela, fecha, filas = it["properties"]["s2:mgrs_tile"], it["properties"]["datetime"][:10], []
    src = {b: rasterio.open(it["assets"][b]["href"] + "?" + tok()) for b in bandas}
    ref = src["SCL"]
    for cl in cl_por_tesela[tesela]:
        b = unary_union([P[p]["utm"] for p in cl]).buffer(40).bounds
        w = from_bounds(*b, transform=ref.transform).round_offsets().round_lengths()
        wt, forma = ref.window_transform(w), (int(w.height), int(w.width))
        arr = {}
        for k, s in src.items():
            ww = from_bounds(*rasterio.windows.bounds(w, ref.transform), transform=s.transform)
            arr[k] = s.read(1, window=ww, out_shape=forma, boundless=True, fill_value=0,
                            resampling=Resampling.nearest if k == "SCL" else Resampling.average).astype("float32")
        valido = np.isin(arr["SCL"], [4, 5])
        for p in cl:
            m = ~geometry_mask([mapping(P[p]["utm"])], out_shape=forma, transform=wt)
            mv = m & valido
            fila = {"ID_POLIGONO": p, "fecha": fecha, "tile": tesela, "n_pix": int(m.sum()), "n_valid": int(mv.sum())}
            for k in bandas[:-1]:
                fila[k] = float(((arr[k][mv] - 1000) / 10000).mean()) if mv.any() else np.nan
            filas.append(fila)
    for s in src.values():
        s.close()
    return filas


def s1(it, tok, cl):
    fecha, filas = it["properties"]["datetime"][:10], []
    src = {b: rasterio.open(it["assets"][b]["href"] + "?" + tok()) for b in ("vv", "vh")}
    crs = src["vv"].crs
    for g in cl:
        geoms = {p: transform_geom("EPSG:32614", crs, mapping(P[p]["utm"])) for p in g}
        b = unary_union([shape(x) for x in geoms.values()]).buffer(40).bounds
        w = from_bounds(*b, transform=src["vv"].transform).round_offsets().round_lengths()
        wt, forma = src["vv"].window_transform(w), (int(w.height), int(w.width))
        a = {k: s.read(1, window=w, boundless=True, fill_value=0).astype("float64") for k, s in src.items()}
        ok = (a["vv"] > 0) & (a["vh"] > 0) & np.isfinite(a["vv"]) & np.isfinite(a["vh"])
        for p in g:
            m = ~geometry_mask([geoms[p]], out_shape=forma, transform=wt)
            mv = m & ok
            filas.append({"ID_POLIGONO": p, "fecha": fecha, "n_pix": int(m.sum()), "n_valid": int(mv.sum()),
                          **{k: float(a[k][mv].mean()) if mv.any() else np.nan for k in ("vv", "vh")}})
    for s in src.values():
        s.close()
    return filas


def aef():
    filas = []
    for anio, urls in AEF.items():
        for url in urls:
            with rasterio.open(url) as s:   # archivos orientados al sur: ventana calculada con la transformada inversa
                inv = ~s.transform
                for p, v in P.items():
                    b = v["utm"].buffer(30).bounds
                    cs, rs = zip(*[inv * (x, y) for x in (b[0], b[2]) for y in (b[1], b[3])])
                    c0, c1, r0, r1 = int(np.floor(min(cs))), int(np.ceil(max(cs))), int(np.floor(min(rs))), int(np.ceil(max(rs)))
                    if c0 < 0 or r0 < 0 or c1 > s.width or r1 > s.height:
                        continue   # parcela en el borde entre archivos: queda sin valor
                    w = Window(c0, r0, c1 - c0, r1 - r0)
                    a = s.read(window=w).astype("float32")
                    m = ~geometry_mask([mapping(v["utm"])], out_shape=a.shape[1:], transform=s.window_transform(w))
                    valido = m & (a != -128).all(0)
                    if valido.any():
                        x = a[:, valido]
                        x = ((x / 127.5) ** 2) * np.sign(x)
                        filas.append({"ID_POLIGONO": p, "year": anio, "n_pix": int(valido.sum()),
                                      **{f"A{i:02d}": e for i, e in enumerate(x.mean(1))}})
    return pd.DataFrame(filas).drop_duplicates(["ID_POLIGONO", "year"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fuente", choices=["s2", "s1", "aef"])
    ap.add_argument("--limite", type=int, default=None, help="solo las primeras N escenas (prueba)")
    ap.add_argument("--salida", type=Path, default=DATOS)
    ap.add_argument("--hilos", type=int, default=6)
    args = ap.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)
    escenas = json.loads((DATOS / "escenas_usadas.json").read_text())
    if args.fuente == "aef":
        aef().to_csv(args.salida / "alphaearth_parcela_anio.csv", index=False)
        return
    coleccion, clave = {"s2": ("sentinel-2-l2a", "sentinel-2-l2a"), "s1": ("sentinel-1-rtc", "sentinel-1-rtc_orbita5")}[args.fuente]
    its = items(coleccion, escenas[clave])[: args.limite]
    tok = Token(coleccion)
    if args.fuente == "s2":
        huella = {}
        for it in its:
            huella.setdefault(it["properties"]["s2:mgrs_tile"], shape(it["geometry"]))
        asig = {p: ("14QNG" if "14QNG" in huella and huella["14QNG"].contains(v["ll"]) else "14QNH") for p, v in P.items()}
        cl = {t: grupos([p for p in P if asig[p] == t]) for t in huella}
        fn, nombre = (lambda it: s2(it, tok, cl)), "s2_l2a_parcela_fecha.csv"
    else:
        cl = grupos(list(P))
        fn, nombre = (lambda it: s1(it, tok, cl)), "s1_rtc_parcela_fecha.csv"
    filas = []
    with ThreadPoolExecutor(args.hilos) as ex:
        for i, f in enumerate(ex.map(fn, its)):
            filas += f
            print(f"{i + 1}/{len(its)}", flush=True)
    pd.DataFrame(filas).to_csv(args.salida / nombre, index=False)


if __name__ == "__main__":
    main()
