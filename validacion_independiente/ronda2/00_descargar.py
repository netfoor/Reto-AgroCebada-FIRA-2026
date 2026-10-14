"""Ronda 2, paso 0: descargas reproducibles (solo X). Registra URL, fecha UTC, tamaño y SHA-256.

Fuentes (atribución obligatoria):
- Copernicus DEM GLO-30 (2021), tile N19 W099. Licencia Copernicus DEM (uso libre con atribución):
  "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018
  provided under COPERNICUS by the European Union and ESA; all rights reserved". Bucket público s3://copernicus-dem-30m.
- SoilGrids 2.0 (ISRIC), carbono orgánico del suelo (soc), media 0-5, 5-15 y 15-30 cm, 250 m, CC-BY 4.0
  (Poggio et al., 2021). Se recorta solo la ventana de la zona de estudio.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from rasterio.windows import from_bounds

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
DATOS = AQUI / "datos"
DEM_URL = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N19_00_W099_00_DEM/Copernicus_DSM_COG_10_N19_00_W099_00_DEM.tif"
SOIL_URL = "https://files.isric.org/soilgrids/latest/data/soc/soc_{p}_mean.vrt"
PROFUNDIDADES = ["0-5cm", "5-15cm", "15-30cm"]
BBOX_LL = (-98.70, 19.45, -98.10, 20.06)       # parcelas: lon -98.613..-98.197, lat 19.524..19.984, con margen de ~5 km


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    DATOS.mkdir(parents=True, exist_ok=True)
    reg = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "archivos": {}}
    dem = DATOS / "copernicus_dem_glo30_N19_W099.tif"
    if not dem.exists():
        r = requests.get(DEM_URL, timeout=600)
        r.raise_for_status()
        dem.write_bytes(r.content)
    reg["archivos"][dem.name] = {"url": DEM_URL, "bytes": dem.stat().st_size, "sha256": sha(dem),
                                 "licencia": "Copernicus DEM licence (gratuita, con atribución)"}
    igh = "+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs"
    tf = Transformer.from_crs(4326, igh, always_xy=True)
    xs, ys = tf.transform([BBOX_LL[0], BBOX_LL[2], BBOX_LL[0], BBOX_LL[2]], [BBOX_LL[1], BBOX_LL[1], BBOX_LL[3], BBOX_LL[3]])
    caja = (min(xs), min(ys), max(xs), max(ys))
    for p in PROFUNDIDADES:
        out = DATOS / f"soilgrids_soc_{p}_mean.tif"
        if not out.exists():
            with rasterio.open("/vsicurl/" + SOIL_URL.format(p=p)) as s:
                w = from_bounds(*caja, transform=s.transform).round_offsets().round_lengths()
                a = s.read(1, window=w)
                perfil = s.profile.copy()
                perfil.update(driver="GTiff", width=a.shape[1], height=a.shape[0], transform=s.window_transform(w), compress="deflate", tiled=False)
                perfil.pop("blockxsize", None)
                perfil.pop("blockysize", None)
                with rasterio.open(out, "w", **perfil) as d:
                    d.write(a, 1)
        with rasterio.open(out) as d:
            a = d.read(1)
            info = {"nodata": d.nodata, "crs": str(d.crs)[:60], "forma": a.shape, "min": int(a.min()), "max": int(a.max())}
        reg["archivos"][out.name] = {"url": SOIL_URL.format(p=p), "bytes": out.stat().st_size, "sha256": sha(out),
                                     "licencia": "CC-BY 4.0, ISRIC SoilGrids 2.0", "unidades": "dg/kg (soc×10 = g/kg)", **info}
    (DATOS / "registro_descargas.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(reg, indent=2, ensure_ascii=False, default=str))
    _ = np


if __name__ == "__main__":
    main()
