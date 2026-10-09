"""EXP_10, factibilidad solo con X: reconstruye K1 publicado y corregido, vecinos, cobertura e
invariancia temporal. No lee rendimientos.

    uv run --locked --all-groups python scripts/factibilidad_10.py
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import shapefile
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from modelo_10 import DIA_CORTE, ID, capturas_receta, contraste, diagnostico_vecinos, integrales, vecinos_geometricos

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "data/exp_10_verificacion_contraste_vecinal"
ZIP_SHA = "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"
E9 = RAIZ / "data/exp_09_fuentes_externas"
V0 = RAIZ / "data/referencias/variables_v0_197.csv"
PREF = "DATASET_RETO_AGRO_2026/"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def leer_zip():
    ruta = RAIZ / "data/raw/DataSet.zip"
    if sha(ruta) != ZIP_SHA:
        raise ValueError("DataSet.zip distinto")
    z = zipfile.ZipFile(ruta)
    pro = pd.read_csv(z.open(PREF + "Conjunto_datos_PRO_AgroCebada.csv"), encoding="utf-8-sig")
    inner = zipfile.ZipFile(io.BytesIO(z.read(PREF + "Parcelas_Reto_AGC_CONJUNTO_70_30.zip")))
    pt = {n.rsplit(".", 1)[-1].lower(): n for n in inner.namelist() if n.lower().endswith((".shp", ".dbf", ".shx"))}
    r = shapefile.Reader(shp=io.BytesIO(inner.read(pt["shp"])), dbf=io.BytesIO(inner.read(pt["dbf"])),
                         shx=io.BytesIO(inner.read(pt["shx"])), encoding="utf-8")
    utm = Transformer.from_crs(4326, 32614, always_xy=True).transform
    filas = []
    for rec, s in zip(r.records(), r.shapes()):
        c = transform(lambda x, y, z=None: utm(x, y), shape(s.__geo_interface__)).centroid
        filas.append({ID: rec["ID_POLIGON"], "Municipio": rec["Municipio"], "CONJUNTO": rec["CONJUNTO"], "x_m": c.x, "y_m": c.y})
    meta = pd.DataFrame(filas).sort_values(ID).reset_index(drop=True)
    return pro, meta


# --- Receta publicada de EXP_09 para K2–K5 (con su discrepancia temporal); solo para el nulo de familia ---
def _curva09(doy, val, ventana, minimo):
    s = pd.Series(np.asarray(val)).groupby(np.asarray(doy)).median().reindex(np.arange(1, 366))
    return s.rolling(ventana, center=True, min_periods=minimo).median().interpolate(limit_area="inside")


def _integrales09(df, col, ventana, minimo):
    from modelo_10 import integral
    return pd.Series({p: integral(_curva09(pd.to_datetime(g.fecha).dt.dayofyear, g[col], ventana, minimo))
                      for p, g in df.groupby(ID)}, dtype=float)


def familia_exp09(meta, vec, k1_publicado):
    s2 = pd.read_csv(E9 / "s2_l2a_parcela_fecha.csv")
    s2 = s2[(s2.n_pix > 0) & (s2.n_valid >= 0.5 * s2.n_pix)].copy()
    s2["ndre"] = (s2.B8A - s2.B05) / (s2.B8A + s2.B05)
    s2 = s2.groupby([ID, "fecha"], as_index=False)[["ndre"]].mean()
    s1 = pd.read_csv(E9 / "s1_rtc_parcela_fecha.csv")
    s1 = s1[s1.n_valid > 0].assign(cr=lambda d: d.vh / d.vv)
    aef = pd.read_csv(E9 / "alphaearth_parcela_anio.csv")
    v0 = pd.read_csv(V0).set_index(ID)
    ids = meta[ID].to_numpy()
    K = pd.DataFrame(index=ids)
    K["K2"] = contraste(_integrales09(s2, "ndre", 21, 2), vec)
    K["K3"] = contraste(_integrales09(s1, "cr", 25, 2), vec)
    A = aef[aef.year.eq(2025)].set_index(ID).reindex(ids)[[f"A{i:02d}" for i in range(64)]]
    CA = pd.DataFrame({c: contraste(A[c], vec) for c in A})
    ok = CA.notna().all(axis=1)
    X = CA[ok].to_numpy() - CA[ok].to_numpy().mean(0)
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    K["K4"] = pd.Series(X @ vt[0], index=CA.index[ok]).reindex(ids)
    both = K.K4.notna() & k1_publicado.reindex(ids).notna()
    if np.corrcoef(K.K4[both], k1_publicado.reindex(ids)[both])[0, 1] < 0:
        K["K4"] = -K.K4
    h = pd.concat([contraste(v0[f"H{y}_S2_ndvi_integral"], vec) for y in (2022, 2023, 2024)], axis=1)
    K["K5"] = h.mean(axis=1).where(h.notna().any(axis=1))
    return K.rename_axis(ID).reset_index()


def invariancia(capturas, base_corregida):
    """Cambiar, añadir o borrar capturas posteriores al corte no debe cambiar la receta corregida."""
    doy = pd.to_datetime(capturas.fecha).dt.dayofyear
    post = doy > DIA_CORTE
    rng = np.random.default_rng(20261008)
    escenarios = {
        "cambiar_valores_posteriores": capturas.assign(ndvi_promedio=np.where(post, rng.uniform(-1, 1, len(capturas)), capturas.ndvi_promedio)),
        "borrar_posteriores": capturas[~post],
        "añadir_posteriores": pd.concat([capturas, pd.DataFrame({ID: capturas[ID].unique(), "fecha": "2025-11-02",
                                         "ndvi_promedio": 0.95, "porcentaje_nubosidad": 0.0})], ignore_index=True),
    }
    filas = []
    base_pub = integrales(capturas, "publicada")
    for nombre, cap in escenarios.items():
        cor = integrales(cap, "corregida").reindex(base_corregida.index)
        pub = integrales(cap, "publicada").reindex(base_pub.index)
        filas.append({"escenario": nombre, "filas_posteriores_afectadas": int(post.sum()) if nombre != "añadir_posteriores" else int(capturas[ID].nunique()),
                      "corregida_integrales_cambiadas": int((~np.isclose(cor, base_corregida, rtol=0, atol=0, equal_nan=True)).sum()),
                      "publicada_integrales_cambiadas": int((~np.isclose(pub, base_pub, rtol=0, atol=0, equal_nan=True)).sum())})
    return pd.DataFrame(filas)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    pro, meta = leer_zip()
    if len(meta) != 197 or not meta[ID].is_unique:
        raise ValueError("Catálogo inesperado")
    cap = capturas_receta(pro)
    vec = vecinos_geometricos(meta)
    I_pub, I_cor = integrales(cap, "publicada").reindex(meta[ID]), integrales(cap, "corregida").reindex(meta[ID])
    K_pub, K_cor = contraste(I_pub, vec, "publicada"), contraste(I_cor, vec, "publicada")
    K_cor_fin = contraste(I_cor, vec, "finitos")
    dv_pub, dv_cor = diagnostico_vecinos(I_pub, vec).set_index(ID), diagnostico_vecinos(I_cor, vec).set_index(ID)
    var = meta.set_index(ID).assign(
        integral_publicada=I_pub, integral_corregida=I_cor, K1_publicado=K_pub, K1_corregido=K_cor,
        K1_corregido_regla_finitos=K_cor_fin, vecinos_geometricos=dv_cor.vecinos_geometricos,
        vecinos_finitos_publicada=dv_pub.vecinos_finitos, vecinos_finitos_corregida=dv_cor.vecinos_finitos,
        capturas_receta=cap.groupby(ID).size(),
        capturas_hasta_corte=cap[pd.to_datetime(cap.fecha).dt.dayofyear <= DIA_CORTE].groupby(ID).size(),
    ).reset_index()
    if not np.allclose(K_cor, K_cor_fin, equal_nan=True, rtol=0, atol=0):
        raise ValueError("La regla de vecinos finitos cambia contrastes: decidir antes de evaluar")
    inv = invariancia(cap, I_cor)
    if inv.corregida_integrales_cambiadas.any():
        raise ValueError("La receta corregida depende de capturas posteriores al corte")
    oculta = var.CONJUNTO.eq("PREDICCION")
    dI, dK = (var.integral_corregida - var.integral_publicada), (var.K1_corregido - var.K1_publicado)
    cobertura = pd.DataFrame([{"grupo": g, "parcelas": int(m.sum()),
                               "integral_publicada": int(var.integral_publicada[m].notna().sum()), "integral_corregida": int(var.integral_corregida[m].notna().sum()),
                               "K1_publicado": int(var.K1_publicado[m].notna().sum()), "K1_corregido": int(var.K1_corregido[m].notna().sum()),
                               "integrales_cambian": int((dI[m].abs() > 1e-12).sum()), "contrastes_cambian": int((dK[m].abs() > 1e-12).sum())}
                              for g, m in [("etiquetadas_138", ~oculta), ("ocultas_59", oculta), ("todas_197", oculta | ~oculta)]])
    familia = familia_exp09(meta, vec, K_pub)
    diag = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(), "usa_rendimientos": False, "ajustes_modelos": 0,
        "capturas_receta": len(cap), "capturas_posteriores_al_corte": int((pd.to_datetime(cap.fecha).dt.dayofyear > DIA_CORTE).sum()),
        "integrales_cambian": int((dI.abs() > 1e-12).sum()), "contrastes_finitos": int(var.K1_corregido.notna().sum()),
        "contrastes_cambian": int((dK.abs() > 1e-12).sum()),
        "dif_integral_abs_mediana": float(dI.abs().median()), "dif_integral_abs_max": float(dI.abs().max()),
        "dif_contraste_abs_mediana": float(dK.abs().median()), "dif_contraste_abs_max": float(dK.abs().max()),
        "spearman_contrastes": float(var.K1_publicado.corr(var.K1_corregido, method="spearman")),
        "contrastes_con_menos_de_2_vecinas_finitas": int(((var.vecinos_geometricos >= 2) & (var.vecinos_finitos_corregida < 2)).sum()),
        "regla_vecinos_precisada": False, "invariancia_corregida_ok": True,
    }
    archivos = {"capturas_receta.csv": cap, "metadatos.csv": meta, "variables_197.csv": var, "cobertura.csv": cobertura,
                "invariancia.csv": inv, "familia_exp09_publicada.csv": familia}
    for nombre, df in archivos.items():
        df.to_csv(SALIDA / nombre, index=False)
    diag["salidas_sha256"] = {n: sha(SALIDA / n) for n in archivos}
    (SALIDA / "diagnosticos_X.json").write_text(json.dumps(diag, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in diag.items() if k != "salidas_sha256"}, indent=2, ensure_ascii=False))
    print(cobertura.to_string(index=False))
    print(inv.to_string(index=False))


if __name__ == "__main__":
    main()
