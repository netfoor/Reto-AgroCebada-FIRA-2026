"""62_linea_base_B3.py: linea base B3, media por celda climatica encogida hacia B2.

Predice cada parcela de validacion con (n * media_celda + k * media_grupo) / (n + k),
con n = parcelas de su celda en el ajuste. Sin parcelas de su celda en el ajuste usa B2.
k se elige en cada particion SOLO con el ajuste, dejando una parcela fuera, sobre la
rejilla 0, 0.5, 1, 2, 4, 8, 16, 32, 64 e infinito (infinito = B2). En empate, el k mayor.
No usa azar. La hipotesis H5 ya esta registrada con su resultado (copia del registro en 03).
Entradas : 01_datos/preparados/base_138.csv y folds_V1/V2.csv
Salidas  : 04_resultados/62_b3_por_particion.csv, 62_b3_resumen.csv y logs/62_linea_base_B3.log
Correr   : python 02_validacion_y_lineas_base/scripts/62_linea_base_B3.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import comun as c

K_GRID = [0, 0.5, 1, 2, 4, 8, 16, 32, 64, np.inf]
TOL = 1e-12
log = c.iniciar_log("62_linea_base_B3")
base, y, g, ids = c.carga_base()
cel = base["celda_clima"].astype(str).to_numpy()
print("Celdas climaticas distintas:", len(set(cel)))


def pred_b3(n, mc, mg, k):
    if np.isinf(k):
        return mg
    den = np.where(n + k > 0, n + k, 1.0)
    return np.where(n > 0, (n * np.nan_to_num(mc) + k * mg) / den, mg)


def b3_particion(fit, val):
    yF, gF, cF = y[fit], g[fit], cel[fit]
    ng = np.bincount(gF, minlength=c.NG)
    Sg = np.bincount(gF, weights=yF, minlength=c.NG)
    ser = pd.Series(yF)
    Sc = ser.groupby(cF).sum()
    Nc = ser.groupby(cF).size()
    assert (ng[gF] >= 2).all()
    n_i = Nc.loc[cF].to_numpy(float) - 1
    mc_i = np.where(n_i > 0, (Sc.loc[cF].to_numpy() - yF) / np.where(n_i > 0, n_i, 1), np.nan)
    mg_i = (Sg[gF] - yF) / (ng[gF] - 1)
    rm_k = np.array([np.sqrt(np.mean((yF - pred_b3(n_i, mc_i, mg_i, k)) ** 2)) for k in K_GRID])
    k_star = max(k for k, r in zip(K_GRID, rm_k) if r <= rm_k.min() + TOL)
    yV, gV, cV = y[val], g[val], cel[val]
    assert (ng[gV] > 0).all()
    mg_v = Sg[gV] / ng[gV]
    n_v = np.array([Nc.get(x, 0) for x in cV], float)
    mc_v = np.where(n_v > 0, np.array([Sc.get(x, 0.0) for x in cV]) / np.where(n_v > 0, n_v, 1), np.nan)
    p3 = pred_b3(n_v, mc_v, mg_v, k_star)
    return {"k": k_star, "n_val": len(val), "n_val_sin_celda": int((n_v == 0).sum()),
            "rmse_B2": c.rmse(yV - mg_v), "rmse_B3": c.rmse(yV - p3)}


filas = []
for esq in ["V1", "V2"]:
    for p in c.carga_particiones(esq, ids):
        r = b3_particion(p["fit"], p["val"])
        r.update({"esquema": esq, "rep": p["rep"], "delta": r["rmse_B2"] - r["rmse_B3"]})
        filas.append(r)
res = pd.DataFrame(filas)[["esquema", "rep", "k", "n_val", "n_val_sin_celda", "rmse_B2", "rmse_B3", "delta"]]

# B2 recalculado frente a lineas_base.csv de este mismo proyecto
lb = pd.read_csv(c.ruta("04_resultados", "lineas_base.csv"))
for e in ["V1", "V2"]:
    ref = lb[(lb.esquema == e) & (lb.modelo == "B2")].sort_values("rep")["rmse"].to_numpy()
    obt = res[res.esquema == e].sort_values("rep")["rmse_B2"].to_numpy()
    assert np.abs(ref - obt).max() < 1e-9
print("Comprobacion: B2 coincide con lineas_base.csv en las 200 particiones.")

filas_r = []
for esq, d in res.groupby("esquema"):
    dl = d["delta"]
    filas_r.append({"esquema": esq, "n_part": len(d), "rmse_B2": d["rmse_B2"].mean(), "rmse_B3": d["rmse_B3"].mean(),
                    "delta_medio": dl.mean(), "delta_p5": float(np.quantile(dl, .05)), "delta_p95": float(np.quantile(dl, .95)),
                    "n_mejora": int((dl > TOL).sum()), "n_igual": int((dl.abs() <= TOL).sum()), "n_empeora": int((dl < -TOL).sum()),
                    "k_mediano": float(np.median(d["k"])), "n_k_infinito": int(np.isinf(d["k"]).sum()),
                    "pct_val_sin_celda": 100 * d["n_val_sin_celda"].sum() / d["n_val"].sum()})
resumen = pd.DataFrame(filas_r).round(4)
res_out = res.copy()
for col in ["rmse_B2", "rmse_B3", "delta"]:
    res_out[col] = res_out[col].round(4)
res_out.to_csv(c.ruta("04_resultados", "62_b3_por_particion.csv"), index=False)
resumen.to_csv(c.ruta("04_resultados", "62_b3_resumen.csv"), index=False)
print("\n== B3 frente a B2 (delta = RMSE B2 menos RMSE B3; positivo = mejora) ==")
print(resumen.to_string(index=False))
print("\nk elegido en V1 (particiones por valor):")
print(res[res.esquema == "V1"]["k"].value_counts().sort_index().to_string())

print("\n== Comprobacion contra los CSV que produjo R ==")
m1, o1 = c.compara_con_R(resumen, "62_b3_resumen.csv", ["esquema"],
                         ["rmse_B2", "rmse_B3", "delta_medio", "delta_p5", "delta_p95", "n_mejora", "n_igual", "n_empeora", "pct_val_sin_celda"], 1e-4)
m2, o2 = c.compara_con_R(res_out, "62_b3_por_particion.csv", ["esquema", "rep"], ["k", "rmse_B2", "rmse_B3", "delta"], 1e-4)
print(m1); print(m2)
print("\nHecho." if (o1 and o2) else "\nHecho, pero hay diferencias contra R: revisar.")
