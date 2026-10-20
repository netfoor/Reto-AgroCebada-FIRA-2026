"""Exporta los datos que lee el sitio y los archivos que ofrece para descargar.

No entrena ni cambia resultados. Lee el ZIP original del reto, las salidas del cuaderno 04 y los
cuadernos de los experimentos, y comprueba que la fórmula del modelo final, escrita como en el
navegador, reproduce las 59 estimaciones publicadas.

Escribe:
    web/public/datos/       parcelas, modelo, vitrina, evidencia, relieve y manifiesto (JSON)
    web/public/descargas/   predicciones_59.csv, intervalos_59.csv y detalle_59.csv (copias exactas)
                            y agrocebada_estimaciones.xlsx

El manifiesto guarda la SHA-256 de cada archivo; el sitio la comprueba en el navegador antes de usarlo.
Si nada cambió, los archivos salen idénticos byte a byte y `terraform apply` no vuelve a subirlos.

Desde la raíz del repositorio (necesita data/raw/DataSet.zip y las carpetas de data/ del cuaderno 04):
    uv run --group geo python scripts/exportar_web.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
import shapefile
from pyproj import CRS, Transformer
from rasterio.io import MemoryFile
from shapely import force_2d
from shapely.geometry import box, shape
from shapely.ops import transform as sh_transform

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import modelo_10 as M10  # noqa: E402  (receta K1 corregida, sin cambios)

ID, Y = "ID_POLIGONO", "RENDIMIENTO_T_HA"
ZIPP = REPO / "data/raw/DataSet.zip"
PREF = "DATASET_RETO_AGRO_2026/"
FINAL = REPO / "resultados/04_seleccion_modelo_final"
NB04 = REPO / "notebooks/04_seleccion_modelo_final.ipynb"
BITACORA = REPO / "docs/bitacora_experimentos.md"
DATOS = REPO / "web/public/datos"
DESCARGAS = REPO / "web/public/descargas"
UTM = CRS.from_epsg(32614)
ENTREGA = ["predicciones_59.csv", "intervalos_59.csv", "detalle_59.csv"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args: str) -> str | None:
    """Solo lectura: no toca el índice ni crea archivos de bloqueo."""
    try:
        r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def json_bytes(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def r(v, d=4):
    return None if v is None or not np.isfinite(v) else round(float(v), d)


Z = zipfile.ZipFile(ZIPP)
resumen = json.loads((FINAL / "resumen.json").read_text(encoding="utf-8"))
for n in ENTREGA:
    assert sha((FINAL / n).read_bytes()) == resumen["sha256"][n], f"{n} no coincide con resumen.json"

# ---------------------------------------------------------------- parcelas
zp = zipfile.ZipFile(io.BytesIO(Z.read(PREF + "Parcelas_Reto_AGC_CONJUNTO_70_30.zip")))
rd = shapefile.Reader(shp=io.BytesIO(zp.read("Parcelas_Reto_AGC_CONJUNTO.shp")),
                      dbf=io.BytesIO(zp.read("Parcelas_Reto_AGC_CONJUNTO.dbf")),
                      shx=io.BytesIO(zp.read("Parcelas_Reto_AGC_CONJUNTO.shx")), encoding="utf-8")
campos = [f[0] for f in rd.fields[1:]]
crs_shp = CRS.from_wkt(zp.read("Parcelas_Reto_AGC_CONJUNTO.prj").decode())
a_utm = Transformer.from_crs(crs_shp, UTM, always_xy=True).transform
geo = {}
for sr in rd.iterShapeRecords():
    rec = dict(zip(campos, sr.record))
    geo[rec["ID_POLIGON"].strip()] = force_2d(shape(sr.shape.__geo_interface__))

meta = pd.read_csv(REPO / "data/exp_10_verificacion_contraste_vecinal/metadatos.csv").set_index(ID)
ub = pd.read_csv(REPO / "data/exp_11_combinacion_modelos/procedencia_jared/base_197_ubicacion.csv").set_index(ID)
with Z.open(PREF + "ID_area_rendimiento_70_30_Reto_AgroCebada.csv") as f:
    lab = pd.read_csv(f, encoding="utf-8-sig")
lab.columns = [c.strip() for c in lab.columns]
lab[ID] = lab[ID].str.strip()
lab = lab.set_index(ID)
assert len(geo) == len(meta) == 197 and set(geo) == set(meta.index) == set(lab.index)

det = pd.read_csv(FINAL / "detalle_59.csv").set_index(ID)
v197 = pd.read_csv(REPO / "data/exp_10_verificacion_contraste_vecinal/variables_197.csv").set_index(ID)
anom = pd.read_csv(REPO / "data/exp_11_combinacion_modelos/procedencia_jared/variables_jared/"
                   "clima_anomalias_features.csv").set_index(ID)["anom_precip_pct_d"]

# ------------------------------------------- modelo final, como en el navegador
K, J = resumen["K"], resumen["J_coeficientes"]
assert resumen["J_variable"] == "anom_precip_pct_d"
etq = lab[lab.CONJUNTO.str.strip() == "ENTRENAMIENTO"]
yv = etq[Y].astype(float)
mun_media = yv.groupby(meta.loc[yv.index, "Municipio"]).mean()
XYe = meta.loc[yv.index, ["x_m", "y_m"]].to_numpy(float)


def predecir(pid: str) -> dict:
    mun = meta.at[pid, "Municipio"]
    m = float(mun_media.get(mun, yv.mean()))
    d = np.linalg.norm(XYe - meta.loc[pid, ["x_m", "y_m"]].to_numpy(float), axis=1)
    idx = np.argsort(d)[:20]
    w = 1 / np.maximum(d[idx], 1.0) ** 2
    w = w / w.sum()
    idw = float((w * yv.to_numpy()[idx]).sum())
    mix = 0.5 * m + 0.5 * idw
    k1 = v197.at[pid, "K1_corregido"]
    z = (k1 - K["mediana"]) / K["escala"] if np.isfinite(k1) else 0.0
    kk = mix + K["beta"] * z
    jj = J[ub.at[pid, "grupo"]] + J["pendiente"] * float(anom.at[pid])
    return dict(MUN=m, IDW=idw, MIX=mix, z=z, K=kk, J=jj, E_JK=0.5 * jj + 0.5 * kk,
                d_min=float(d.min()))


for pid in det.index:
    p = predecir(pid)
    for col in ["MUN", "MIX", "K", "J", "E_JK"]:
        assert abs(p[col] - det.at[pid, col]) < 1e-9, (pid, col, p[col], det.at[pid, col])
print("La fórmula del navegador reproduce las 59 estimaciones (MUN, MIX, K, J, E_JK) con diferencia < 1e-9")
dist_conocida = float(np.median([predecir(p)["d_min"] for p in det.index]))
print(f"Distancia mediana de una parcela oculta a la conocida más cercana: {dist_conocida:.0f} m")

# ------------------------------------------------------- OOF de las 138
oof = pd.read_csv(REPO / "data/exp_11_combinacion_modelos/oof_componentes.csv")
oof = oof[oof.conjunto == "historicas"]
w = oof.pivot_table(index=["repeticion", "pliegue", ID], columns="modelo", values="predicho").reset_index()
w["E_JK"] = 0.5 * w.J + 0.5 * w.K
oof_par = w.groupby(ID)[["E_JK", "MIX", "MUN"]].mean()


def poly_coords(g):
    g = sh_transform(a_utm, g).simplify(1.0, preserve_topology=True)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return [[[round(x), round(yy)] for x, yy in p.exterior.coords] for p in polys]


a_geo = Transformer.from_crs(UTM, CRS.from_epsg(4326), always_xy=True).transform
parcelas = []
for pid in sorted(geo):
    conj = lab.at[pid, "CONJUNTO"].strip()
    lon, lat = a_geo(meta.at[pid, "x_m"], meta.at[pid, "y_m"])
    k1 = v197.at[pid, "K1_corregido"]
    reg = dict(id=pid, mun=meta.at[pid, "Municipio"], edo=ub.at[pid, "Estado"], grupo=ub.at[pid, "grupo"],
               celda=str(ub.at[pid, "celda_clima"]), oculta=conj == "PREDICCION", ha=r(float(lab.at[pid, "AREA_HA"]), 3),
               # coordenadas, verdor relativo y lluvia sin redondear: el navegador recalcula el modelo con ellas
               x=float(meta.at[pid, "x_m"]), y=float(meta.at[pid, "y_m"]), lon=round(lon, 6), lat=round(lat, 6),
               k1=float(k1) if np.isfinite(k1) else None, anom=float(anom.at[pid]), poly=poly_coords(geo[pid]))
    if conj == "ENTRENAMIENTO":
        reg.update(obs=float(lab.at[pid, Y]), oof=r(oof_par.at[pid, "E_JK"]), oof_mix=r(oof_par.at[pid, "MIX"]))
    else:
        f = det.loc[pid]
        reg.update(pred=r(f.E_JK), e_jk=float(f.E_JK), mix=r(f.MIX), mun_p=r(f.MUN), jv=r(f.J), kv=r(f.K), zona=f.zona,
                   lo80=r(f["inferior 80 %"], 3), hi80=r(f["superior 80 %"], 3),
                   lo90=r(f["inferior 90 %"], 3), hi90=r(f["superior 90 %"], 3),
                   sin_k1=bool(f["sin K1 (K = MIX)"]), celda_sin=bool(f["celda CHIRPS sin etiquetas"]))
    parcelas.append(reg)
# el valor de pred debe ser el del CSV entregado
entregado = pd.read_csv(FINAL / "predicciones_59.csv", dtype={Y: str}).set_index(ID)[Y]
for p in parcelas:
    if p["oculta"]:
        assert f"{p['pred']:.4f}" == entregado[p["id"]], p["id"]

# el navegador recalcula E_JK solo con lo que trae parcelas.json y modelo.json: comprobarlo aquí
conocidas = [q for q in parcelas if not q["oculta"]]
XYc = np.array([[q["x"], q["y"]] for q in conocidas])
yc = np.array([q["obs"] for q in conocidas])
media_mun = pd.Series(yc).groupby([q["mun"] for q in conocidas]).mean()
for q in parcelas:
    if q["oculta"]:
        d = np.hypot(XYc[:, 0] - q["x"], XYc[:, 1] - q["y"])
        idx = np.argsort(d, kind="stable")[:20]
        w_ = 1 / np.maximum(d[idx], 1.0) ** 2
        mix = 0.5 * media_mun.get(q["mun"], yc.mean()) + 0.5 * float((w_ / w_.sum() * yc[idx]).sum())
        z = 0.0 if q["k1"] is None else (q["k1"] - K["mediana"]) / K["escala"]
        e = 0.5 * (J[q["grupo"]] + J["pendiente"] * q["anom"]) + 0.5 * (mix + K["beta"] * z)
        assert abs(e - det.at[q["id"], "E_JK"]) < 1e-9 and f"{e:.4f}" == entregado[q["id"]], q["id"]
print("Con los datos exportados, el cálculo del navegador da las 59 estimaciones del CSV (diferencia < 1e-9)")

# -------------------------------------------------------- parcela vitrina
cap = M10.capturas_receta(pd.read_csv(Z.open(PREF + "Conjunto_datos_PRO_AgroCebada.csv"), encoding="utf-8-sig"))
cap["doy"] = pd.to_datetime(cap.fecha).dt.dayofyear
corte = cap[cap.doy <= M10.DIA_CORTE]
dias = np.arange(1, M10.DIA_CORTE + 1)
vec = M10.vecinos_geometricos(meta.reset_index())
integ = M10.integrales(cap, "corregida")
contr = M10.contraste(integ, vec)
assert np.allclose(contr.reindex(v197.index).to_numpy(), v197.K1_corregido.to_numpy(), equal_nan=True, atol=1e-9)
print("Contraste de verdor recalculado = variables_197.csv")

with Z.open(PREF + "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip") as f:
    zc = zipfile.ZipFile(io.BytesIO(f.read()))
oct_tif = {a: zc.read(f"Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/Precipitacion_mensual/{a}/PREC_{a}_10.tif")
           for a in (2022, 2023, 2024, 2025)}


def celdas_lluvia(pid):
    """Celdas CHIRPS de octubre alrededor de la parcela, con su área de intersección (UTM)."""
    g_utm = sh_transform(a_utm, geo[pid])
    out = {}
    for a, b in oct_tif.items():
        with MemoryFile(b) as mf, mf.open() as src:
            crs_r = CRS.from_wkt(src.crs.to_wkt())
            a_r = Transformer.from_crs(UTM, crs_r, always_xy=True).transform
            de_r = Transformer.from_crs(crs_r, UTM, always_xy=True).transform
            arr = src.read(1).astype(float)
            nod = src.nodata
            minx, miny, maxx, maxy = sh_transform(a_r, g_utm).bounds
            r0, c0 = src.index(minx, maxy)
            r1, c1 = src.index(maxx, miny)
            celdas = []
            for rr in range(min(r0, r1) - 1, max(r0, r1) + 2):
                for cc in range(min(c0, c1) - 1, max(c0, c1) + 2):
                    x0, y0 = src.xy(rr, cc, offset="ul")
                    x1, y1 = src.xy(rr, cc, offset="lr")
                    cel_u = sh_transform(de_r, box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
                    v = arr[rr, cc]
                    celdas.append(dict(valor=None if (nod is not None and v == nod) else round(float(v), 2),
                                       area=round(float(cel_u.intersection(g_utm).area), 1),
                                       area_celda=round(float(cel_u.area)),
                                       poly=[[round(x), round(yy)] for x, yy in cel_u.exterior.coords]))
            out[a] = celdas
    pond = {}
    for a, cs in out.items():
        ok = [c for c in cs if c["area"] > 0 and c["valor"] is not None]
        pond[a] = sum(c["valor"] * c["area"] for c in ok) / sum(c["area"] for c in ok)
    ref = float(np.mean([pond[2022], pond[2023], pond[2024]]))
    return out, pond, ref, float((pond[2025] - ref) / ref * 100)


# Regla fija, solo con X: oculta, en Chignahuapan, con verdor relativo, ≥3 vecinas a <1 km y que toque
# ≥2 celdas de lluvia; entre ellas, la de mayor |K − MIX|.
cand = sorted(((abs(det.at[p, "K"] - det.at[p, "MIX"]), p) for p in det.index
               if meta.at[p, "Municipio"] == "Chignahuapan" and np.isfinite(v197.at[p, "K1_corregido"])
               and len(vec[p]) >= 3), reverse=True)
vit = None
for _, pid in cand:
    cs, pond, ref, an = celdas_lluvia(pid)
    if sum(1 for c in cs[2025] if c["area"] > 0) >= 2:
        vit = pid
        break
if vit is None:
    vit = cand[0][1]
    cs, pond, ref, an = celdas_lluvia(vit)
print("Vitrina:", vit, "anomalía recalculada", round(an, 3), "frente a la variable de J", round(float(anom.at[vit]), 3))


def detalle_curva(pid):
    g = corte[corte[ID] == pid]
    c = M10.curva(g.doy, g.ndvi_promedio, dias)
    base = float(c.loc[M10.DIA_BASE[0]:M10.DIA_BASE[1]].median())
    temp = c.loc[M10.DIA_PICO_INI:min(330, M10.DIA_CORTE)]
    pico, dpico = float(temp.max()), int(temp.idxmax())
    umbral = base + 0.5 * (pico - base)
    sub = c.loc[M10.DIA_PICO_INI:dpico]
    ini = int(sub[sub >= umbral].index.min())
    baj = c.loc[dpico:M10.DIA_CORTE]
    fin = int(baj[baj < umbral].index.min()) if (baj < umbral).any() else M10.DIA_CORTE
    integral = float((c.loc[ini:fin] - base).clip(lower=0).sum())
    assert abs(integral - integ.get(pid, np.nan)) < 1e-9
    return dict(id=pid, curva=[r(v, 3) for v in c.to_numpy()],
                capturas=[[int(d), round(float(v), 3)] for d, v in zip(g.doy, g.ndvi_promedio)],
                base=r(base), pico=r(pico), dia_pico=dpico, umbral=r(umbral), inicio=ini, fin=fin,
                integral=r(integral, 3))


pv = predecir(vit)
vecinas_1km = [p for p in vec[vit] if np.isfinite(integ.get(p, np.nan))]
curvas = [detalle_curva(vit)] + [detalle_curva(p) for p in vecinas_1km]
med_vec = float(np.median([integ[p] for p in vecinas_1km]))

with Z.open(PREF + "Reto_AgroCebada_Topografia_INEGI_CEM4.zip") as f:
    zt = zipfile.ZipFile(io.BytesIO(f.read()))
tif_elev = zt.read("Reto_AgroCebada_Topografia_INEGI_CEM4/Reto_AgroCebada_Topografia_INEGI_CEM4/"
                   "Elevacion_INEGI_CEM4_120m.tif")


def muestrear_elevacion(gx, gy):
    """Rejilla UTM (filas de norte a sur) con el valor de la celda del CEM que contiene cada punto."""
    with MemoryFile(tif_elev) as mf, mf.open() as src:
        a_r = Transformer.from_crs(UTM, CRS.from_wkt(src.crs.to_wkt()), always_xy=True).transform
        arr = src.read(1).astype(float)
        filas = []
        for yy in gy[::-1]:
            fila = []
            for xx in gx:
                rx, ry = a_r(xx, yy)
                rr, cc = src.index(rx, ry)
                v = arr[rr, cc] if 0 <= rr < src.height and 0 <= cc < src.width else np.nan
                ok = np.isfinite(v) and not (src.nodata is not None and v == src.nodata)
                fila.append(round(float(v)) if ok else None)
            filas.append(fila)
    return filas


cx, cy = meta.at[vit, "x_m"], meta.at[vit, "y_m"]
paso, n = 120.0, 41
gx = cx + (np.arange(n) - n // 2) * paso
gy = cy + (np.arange(n) - n // 2) * paso
elev = muestrear_elevacion(gx, gy)

cel25 = cs[2025]
principal = max(cel25, key=lambda c: c["area"])
vitrina = dict(
    id=vit, mun=meta.at[vit, "Municipio"], grupo=ub.at[vit, "grupo"],
    mun_media=r(pv["MUN"]), mun_n=int((meta.loc[yv.index, "Municipio"] == meta.at[vit, "Municipio"]).sum()),
    idw=r(pv["IDW"]), mix=r(pv["MIX"]), k1=r(v197.at[vit, "K1_corregido"], 3), z=r(pv["z"]), k=r(pv["K"]),
    integral=r(integ[vit], 3), mediana_vecinas=r(med_vec, 3), vecinas_1km=vecinas_1km, curvas=curvas,
    anom=r(anom.at[vit], 3), anom_recalc=r(an, 3),
    lluvia_pond={str(a): round(v, 2) for a, v in pond.items()}, lluvia_ref=round(ref, 2),
    celdas={str(a): c for a, c in cs.items()}, celda_ha=round(principal["area_celda"] / 1e4),
    j=r(pv["J"]), ejk=r(pv["E_JK"]),
    elev=dict(paso=paso, n=n, x0=float(gx[0]), y0=float(gy[-1]), valores=elev),
)

# ------------------------------------------- relieve de la zona (fondo de la portada)
xs, ys = meta.x_m.to_numpy(float), meta.y_m.to_numpy(float)
mg = 6000.0
x0, x1, y0, y1 = xs.min() - mg, xs.max() + mg, ys.min() - mg, ys.max() + mg
paso_r = float(np.ceil(max(x1 - x0, y1 - y0) / 96 / 10) * 10)
rx = np.arange(x0, x1 + paso_r, paso_r)
ry = np.arange(y0, y1 + paso_r, paso_r)
relieve = dict(paso=paso_r, nx=len(rx), ny=len(ry), x0=float(rx[0]), y_norte=float(ry[-1]),
               valores=[v for fila in muestrear_elevacion(rx, ry) for v in fila])
print(f"Relieve: {len(rx)}×{len(ry)} puntos cada {paso_r:.0f} m")

# ------------------------------------------- evidencia (salidas de los cuadernos)


def textos_salida(ruta: Path) -> list[str]:
    nb = json.loads(ruta.read_text(encoding="utf-8"))
    out = []
    for c in nb["cells"]:
        if c["cell_type"] != "code":
            continue
        for o in c.get("outputs", []):
            t = "".join(o.get("text", [])) if "text" in o else "".join(o.get("data", {}).get("text/plain", []))
            if t.strip():
                out.append(t)
    return out


def buscar(textos: list[str], patron: str, flags=re.M) -> list[re.Match]:
    hall = [m for t in textos for m in re.finditer(patron, t, flags)]
    assert hall, f"No se encontró en el cuaderno: {patron}"
    return hall


S04 = textos_salida(NB04)
num = r"(\d+\.\d+)"

# cinco evaluaciones: tabla con columnas MUN MIX J K E_JK (celda «E_JK − MIX»)
tabla = next(t for t in S04 if "E_JK − MIX" in t and re.search(r"MUN\s+MIX\s+J\s+K\s+E_JK", t))
NOMBRES_EVAL = {1: ("Validación cruzada, particiones históricas", "Validación cruzada, históricas", 138),
                2: ("Validación cruzada, particiones nuevas", "Validación cruzada, nuevas", 138),
                3: ("Validación independiente, ronda 1", "Validación independiente, ronda 1", 103),
                4: ("Validación independiente, ronda 2", "Validación independiente, ronda 2", 103),
                5: ("Caja cerrada, abierta una sola vez", "Caja cerrada", 35)}
evaluaciones = {}
for m in re.finditer(rf"^(\d) .+?\s{num}\s+{num}\s+{num}\s+{num}\s+{num}\s*$", tabla, re.M):
    i = int(m.group(1))
    if i in NOMBRES_EVAL and i not in evaluaciones:
        nombre, corto, nn = NOMBRES_EVAL[i]
        evaluaciones[i] = dict(nombre=nombre, corto=corto, parcelas=nn,
                               rmse=dict(zip(["MUN", "MIX", "J", "K", "E_JK"], map(float, m.groups()[1:]))))
assert sorted(evaluaciones) == [1, 2, 3, 4, 5], evaluaciones

# R² de validación cruzada = 1 − MSE / Var(y), con la varianza de las 135 parcelas evaluadas (SEEN135).
# Esa varianza sale del R² publicado de MIX en el cuaderno 03 (RMSE 0.487197, R² 0.666039) y se comprueba con MUN (0.493404, 0.657475).
VAR_Y_SEEN135 = 0.487197 ** 2 / (1 - 0.666039)
assert abs(0.493404 ** 2 / (1 - 0.657475) - VAR_Y_SEEN135) < 1e-5
for i in (1, 2):
    evaluaciones[i]["r2"] = {k: round(1 - v ** 2 / VAR_Y_SEEN135, 3) for k, v in evaluaciones[i]["rmse"].items()}

# escalera de error (celda «agrega»)
bloque = next(t for t in S04 if "media global" in t and "agrega" in t)
escalera = {}
for m in re.finditer(rf"^(GLOBAL|MUN|MIX|K|J|E_JK)\s+.+?\s{num}\s+(?:{num}|NaN)\s*$", bloque, re.M):
    escalera.setdefault(m.group(1), float(m.group(2)))
assert set(escalera) == {"GLOBAL", "MUN", "MIX", "K", "J", "E_JK"}, escalera

m = buscar(S04, rf"El municipio explica {num}% de la varianza")[0]
varianza_municipio = round(float(m.group(1)) / 100, 4)
m = buscar(S04, rf"E_JK quita: históricas {num}%, nuevas {num}%")[0]
quita_mun = [round(float(m.group(1)) / 100, 4), round(float(m.group(2)) / 100, 4)]

# diferencias entre parcelas por distancia
semiv = {}
for m in buscar(S04, r"^(\d+–\d+)\s+(\d+)\s+(\d+\.\d+)\s*$"):
    semiv.setdefault(m.group(1), dict(rango=m.group(1), pares=int(m.group(2)), semivarianza=float(m.group(3))))
for m in buscar(S04, r"^(\d+–\d+)\s+(\d+\.\d+)\s*$"):
    semiv[m.group(1)].setdefault("diferencia", float(m.group(2)))
semivariograma = list(semiv.values())
assert all("diferencia" in s for s in semivariograma) and semivariograma[0]["rango"] == "0–250"

# curva de aprendizaje de MIX y techo
m_n = buscar(S04, r"^n\s+((?:\d+\s+)+\d+)\s*$")[0]
ns = [int(v) for v in m_n.group(1).split()]
m_mix = buscar(S04, r"^MIX\s+((?:0\.\d{4}\s+){" + str(len(ns) - 1) + r"}0\.\d{4})\s*$")[0]
mix_n = [float(v) for v in m_mix.group(1).split()]
m_t = buscar(S04, rf"^MIX\s+{num}\s+{num}\s+{num}\s+{num}\s+{num}\s*$")
techo_fila = [list(map(float, x.groups())) for x in m_t if len(x.groups()) == 5]
buscar(S04, r"RMSE con 124 \(observado\)\s+con 138\s+con 197\s+con 220\s+techo s")
techo_fila = [f for f in techo_fila if abs(f[0] - mix_n[-1]) < 1e-9][0]
aprendizaje = dict(n=ns, rmse_mix=mix_n, con_220=techo_fila[3], techo=techo_fila[4])

# banda de RMSE esperada para un conjunto como las 59 (percentiles de E_JK)
p_lo = buscar(S04, rf"^percentil 2\.5\s+{num}\s+{num}\s+{num}\s+{num}\s+{num}\s*$")[0]
p_hi = buscar(S04, rf"^percentil 97\.5\s+{num}\s+{num}\s+{num}\s+{num}\s+{num}\s*$")[0]
banda_59 = [float(p_lo.group(5)), float(p_hi.group(5))]

# experimentos: mejor resultado de cada uno frente a MIX en su mismo escenario
NB_EXP = REPO / "notebooks/experimentos"
EXPERIMENTOS = [
    ("EXP_01", "Clima, relieve, satélite e historia", "FULL", "0.504668", "0.493845",
     NB_EXP / "exp_01_bloques/exp_01_bloques.ipynb"),
    ("EXP_02", "Medias mensuales ponderadas", "FULL", "0.5192", "0.4938", BITACORA),
    ("EXP_03", "Descriptores temporales, Ridge y árboles", "FULL", "0.519202", "0.493845",
     NB_EXP / "exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb"),
    ("EXP_04", "Lluvia de octubre y cinco regiones", "FULL", "0.4797", "0.4938", BITACORA),
    ("EXP_05", "Lluvia histórica y actual de octubre", "SEEN", "0.4851", "0.4872", BITACORA),
    ("EXP_06", "Fecha del pico de verdor", "SEEN", "0.5015", "0.4872", BITACORA),
    ("EXP_07", "Dispersión del verdor dentro de la parcela", "SEEN", "0.494064", "0.487197", BITACORA),
    ("EXP_08", "Verdor contra las vecinas", "SEEN", "0.4817", "0.4872", BITACORA),
    ("EXP_09", "Cinco fuentes en contraste vecinal", "SEEN", "0.4816", "0.4872", BITACORA),
    ("EXP_10", "Verdor con el corte de octubre corregido", "SEEN", "0.48198", "0.48720", BITACORA),
    ("EXP_11", "Promedio de dos modelos (E_JK)", "SEEN", "0.475655", "0.4872", NB04),
]
experimentos = []
for clave, nombre, esc, mejor, ref, fuente in EXPERIMENTOS:
    texto = fuente.read_text(encoding="utf-8")
    assert mejor in texto and ref in texto, (clave, fuente)
    experimentos.append(dict(id=clave, nombre=nombre, escenario=esc, rmse=float(mejor), mix=float(ref),
                             fuente=str(fuente.relative_to(REPO))))

planet = pd.read_csv(Z.open(PREF + "Conjunto_datos_PRO_AgroCebada.csv"), encoding="utf-8-sig",
                     usecols=[ID, "fecha_captura"])
evidencia = dict(
    evaluaciones=[evaluaciones[i] for i in range(1, 6)],
    escalera=escalera, varianza_municipio=varianza_municipio, quita_error_mun=quita_mun,
    semivariograma=semivariograma, aprendizaje=aprendizaje, banda_59=banda_59,
    experimentos=experimentos, distancia_mediana_oculta_conocida_m=round(dist_conocida),
    planet=dict(imagenes_mediana_por_parcela=float(corte.groupby(ID).size().median()),
                imagenes_temporada=int(len(corte)), capturas_totales=int(len(planet))),
    fuentes=dict(cuaderno="notebooks/04_seleccion_modelo_final.ipynb",
                 bitacora="docs/bitacora_experimentos.md"),
)

# ------------------------------------------- modelo
cobertura = {re.sub(r"^CV \S+ \(103\)", "validación independiente (103)", k): v
             for k, v in resumen["cobertura"].items()}
modelo = dict(
    entrega="E_JK = 0.5·J + 0.5·K", referencia="MIX = 0.5·MUN + 0.5·IDW",
    K=K, J=J, J_variable=resumen["J_variable"], semilla_interna_K=resumen["semilla_interna_K"],
    idw=dict(k=20, potencia=2, piso_m=1.0),
    cuantiles=resumen["cuantiles_residuos"], cobertura=cobertura,
    sin_k1=resumen["sin_K1"], celdas_sin_etiquetas=resumen["celdas_sin_etiquetas"],
    sha256_entrega={n: resumen["sha256"][n] for n in ENTREGA},
)

# ------------------------------------------- libro de Excel (OOXML mínimo, sin dependencias)
commit = git("rev-parse", "--short", "HEAD")
fecha_commit = git("log", "-1", "--format=%cI")


def col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, k = divmod(i - 1, 26)
        s = chr(65 + k) + s
    return s


def hoja_xml(filas: list[list], anchos: list[float]) -> str:
    cols = "".join(f'<col min="{i + 1}" max="{i + 1}" width="{a}" customWidth="1"/>' for i, a in enumerate(anchos))
    xml_filas = []
    for i, fila in enumerate(filas):
        celdas = []
        for j, v in enumerate(fila):
            ref = f"{col(j)}{i + 1}"
            if v is None:
                continue
            if isinstance(v, str) and not (i > 0 and re.fullmatch(r"-?\d+\.\d+", v)):
                s = ' s="1"' if i == 0 else ""
                celdas.append(f'<c r="{ref}" t="inlineStr"{s}><is><t xml:space="preserve">{escape(v)}</t></is></c>')
            else:
                celdas.append(f'<c r="{ref}" s="2"><v>{v}</v></c>')
        xml_filas.append(f'<row r="{i + 1}">{"".join(celdas)}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft"'
            ' state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="15"/>'
            f'<cols>{cols}</cols><sheetData>{"".join(xml_filas)}</sheetData></worksheet>')


def libro(hojas: dict[str, tuple[list[list], list[float]]]) -> bytes:
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    nr = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pk = "http://schemas.openxmlformats.org/package/2006/relationships"
    cab = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    nombres = list(hojas)
    archivos = {
        "[Content_Types].xml": cab + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.styles+xml"/>'
        + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/'
                  f'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(nombres)))
        + "</Types>",
        "_rels/.rels": cab + f'<Relationships xmlns="{pk}"><Relationship Id="rId1" Type="{nr}/officeDocument"'
        ' Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": cab + f'<workbook xmlns="{ns}" xmlns:r="{nr}"><sheets>'
        + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(nombres))
        + "</sheets></workbook>",
        "xl/_rels/workbook.xml.rels": cab + f'<Relationships xmlns="{pk}">'
        + "".join(f'<Relationship Id="rId{i + 1}" Type="{nr}/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                  for i in range(len(nombres)))
        + f'<Relationship Id="rId{len(nombres) + 1}" Type="{nr}/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": cab + f'<styleSheet xmlns="{ns}"><numFmts count="1"><numFmt numFmtId="164"'
        ' formatCode="0.0000"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill'
        ' patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1">'
        '<border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0"'
        ' fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0"'
        ' fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"'
        ' applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
    }
    for i, n in enumerate(nombres):
        archivos[f"xl/worksheets/sheet{i + 1}.xml"] = hoja_xml(*hojas[n])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre, contenido in archivos.items():
            info = zipfile.ZipInfo(nombre, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, contenido.encode("utf-8"))
    return buf.getvalue()


def n4(v) -> str:
    return f"{float(v):.4f}"


pred_csv = pd.read_csv(FINAL / "predicciones_59.csv", dtype=str)
inter = pd.read_csv(FINAL / "intervalos_59.csv", dtype=str)
xlsx = libro({
    "Estimaciones": ([[ID, Y]] + pred_csv[[ID, Y]].values.tolist(), [16, 20]),
    "Rangos": ([["ID_POLIGONO", "Municipio", "Zona", "Estimado (t/ha)", "Inferior 80 %", "Superior 80 %",
                 "Inferior 90 %", "Superior 90 %"]]
               + inter[[ID, "Municipio", "zona", "prediccion_t_ha", "inferior_80", "superior_80", "inferior_90",
                        "superior_90"]].values.tolist(), [16, 30, 14, 16, 14, 14, 14, 14]),
    "Componentes": ([["ID_POLIGONO", "Municipio", "MUN", "MIX", "K", "J", "E_JK"]]
                    + [[i, f.Municipio, n4(f.MUN), n4(f.MIX), n4(f.K), n4(f.J), n4(f.E_JK)] for i, f in det.iterrows()],
                    [16, 30, 10, 10, 10, 10, 10]),
    "Metadatos": ([["Campo", "Valor"],
                   ["Modelo", "E_JK = ½·J + ½·K"],
                   ["J", "5 grupos regionales + anomalía de la lluvia de octubre de 2025 frente a 2022–2024"],
                   ["K", "MIX corregida por el verdor relativo (NDVI Planet frente a vecinas a menos de 1 km)"],
                   ["Referencia", "MIX = ½·media municipal + ½·IDW (20 vecinas conocidas, potencia 2)"],
                   ["Campaña", "abril a octubre de 2025"],
                   ["Parcelas", "59 estimadas a partir de 138 con rendimiento conocido"],
                   ["Rangos", "cuantiles empíricos de errores de validación por zona (Chignahuapan y resto)"],
                   ["Commit del repositorio", commit or "—"],
                   ["SHA-256 de predicciones_59.csv", resumen["sha256"]["predicciones_59.csv"]]],
                  [30, 90]),
})

# ------------------------------------------- escribir y manifiesto
DATOS.mkdir(parents=True, exist_ok=True)
DESCARGAS.mkdir(parents=True, exist_ok=True)
salidas = {
    DATOS / "parcelas.json": json_bytes(parcelas),
    DATOS / "modelo.json": json_bytes(modelo),
    DATOS / "vitrina.json": json_bytes(vitrina),
    DATOS / "evidencia.json": json_bytes(evidencia),
    DATOS / "relieve.json": json_bytes(relieve),
    DESCARGAS / "agrocebada_estimaciones.xlsx": xlsx,
}
for n in ENTREGA:
    salidas[DESCARGAS / n] = (FINAL / n).read_bytes()
for ruta, b in salidas.items():
    if not ruta.exists() or ruta.read_bytes() != b:
        ruta.write_bytes(b)

manifiesto = dict(
    commit=commit, fecha_commit=fecha_commit,
    archivos={str(p.relative_to(REPO / "web/public")): dict(bytes=len(b), sha256=sha(b)) for p, b in salidas.items()},
    entrega={n: dict(ruta=f"resultados/04_seleccion_modelo_final/{n}", sha256=resumen["sha256"][n]) for n in ENTREGA},
)
(DATOS / "manifiesto.json").write_bytes(json_bytes(manifiesto))
for p, b in salidas.items():
    print(f"{p.relative_to(REPO)}  {len(b) / 1024:7.1f} KB  {sha(b)[:16]}")
print("Manifiesto:", (DATOS / "manifiesto.json").relative_to(REPO))
