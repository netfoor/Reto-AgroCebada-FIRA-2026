"""30_lineas_base.py: lineas base B0, B1 y B2 con los esquemas V1, V2 y V3.

B0 media global, B1 media por Estado, B2 media por grupo. Se ajusta solo con el
"ajuste" de cada particion y se mide en la "validacion". Lo que no se puede
calcular queda vacio (NaN), no se rellena.
Entradas : 01_datos/preparados/base_138.csv y folds_V1/V2/V3.csv
Salidas  : 04_resultados/lineas_base.csv, lineas_base_resumen.csv, mejora_vs_B0.csv,
           rmse_por_grupo.csv, fig_lineas_base_rmse.png y logs/30_lineas_base.log
Correr   : python 02_validacion_y_lineas_base/scripts/30_lineas_base.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import comun as c

log = c.iniciar_log("30_lineas_base")
base, y, g, ids = c.carga_base()
estado = base["Estado"].to_numpy()


def media_nivel(clave, fit, val):
    """Media del ajuste por nivel; NaN si algun nivel de validacion no existe en el ajuste."""
    niveles = pd.Series(y[fit]).groupby(clave[fit]).mean()
    if not set(clave[val]) <= set(niveles.index):
        return np.full(len(val), np.nan)
    return niveles.loc[clave[val]].to_numpy()


def metricas(yv, pred, mu):
    if np.isnan(pred).any():
        return np.nan, np.nan, np.nan
    e = yv - pred
    return c.rmse(e), float(np.mean(np.abs(e))), 1 - float((e ** 2).sum()) / float(((yv - mu) ** 2).sum())


filas, filas_g = [], []
for esq in ["V1", "V2", "V3"]:
    for p in c.carga_particiones(esq, ids):
        fit, val = p["fit"], p["val"]
        assert len(set(fit) & set(val)) == 0 and len(fit) + len(val) == 138
        mu = y[fit].mean()
        preds = {"B0": np.full(len(val), mu),
                 "B1": media_nivel(estado, fit, val),
                 "B2": media_nivel(base["grupo"].to_numpy(), fit, val)}
        for mod, pr in preds.items():
            r, m, r2 = metricas(y[val], pr, mu)
            filas.append({"esquema": esq, "rep": p["rep"], "grupo_fuera": p.get("grupo_fuera", np.nan),
                          "modelo": mod, "n_val": len(val), "rmse": r, "mae": m, "r2_val": r2})
            for k, gn in enumerate(c.GRUPOS):
                i = np.where(g[val] == k)[0]
                if len(i) > 0 and not np.isnan(pr[i]).any():
                    filas_g.append({"esquema": esq, "rep": p["rep"], "modelo": mod, "grupo": gn,
                                    "n_val_grupo": len(i), "rmse_grupo": c.rmse(y[val][i] - pr[i])})
lb = pd.DataFrame(filas)
lbg = pd.DataFrame(filas_g)
lb.to_csv(c.ruta("04_resultados", "lineas_base.csv"), index=False)
print("lineas_base.csv:", len(lb), "filas (esquema x repeticion x modelo)")


def q(v, p):
    v = v.dropna()
    return np.nan if len(v) == 0 else float(np.quantile(v, p))


def resumen_de(d, col, pref):
    v = d[col]
    return {f"{pref}_media": v.mean() if v.notna().any() else np.nan,
            f"{pref}_sd": v.std(ddof=1) if v.notna().sum() >= 2 else np.nan,
            f"{pref}_p5": q(v, .05), f"{pref}_p95": q(v, .95)}


res = []
for (esq, mod), d in lb.groupby(["esquema", "modelo"], sort=False):
    fila = {"esquema": esq, "modelo": mod, "n_reps_calculadas": int(d["rmse"].notna().sum()),
            "n_reps": len(d), "n_val_media": d["n_val"].mean()}
    for col, pref in [("rmse", "rmse"), ("mae", "mae"), ("r2_val", "r2")]:
        fila.update(resumen_de(d, col, pref))
    res.append(fila)
resumen = pd.DataFrame(res).round(3)
resumen.to_csv(c.ruta("04_resultados", "lineas_base_resumen.csv"), index=False)
print("\n== Resumen por esquema y modelo (media entre repeticiones; rango = p5 a p95) ==")
print(resumen[["esquema", "modelo", "n_reps_calculadas", "n_val_media", "rmse_media", "rmse_p5", "rmse_p95"]].to_string(index=False))

ancho = lb.pivot_table(index=["esquema", "rep"], columns="modelo", values="rmse", aggfunc="first").reset_index()
mej = []
for esq, d in ancho.groupby("esquema"):
    for nombre, (a, b) in {"B1_vs_B0_pct": ("B0", "B1"), "B2_vs_B0_pct": ("B0", "B2"), "B2_vs_B1_pct": ("B1", "B2")}.items():
        v = (100 * (d[a] - d[b]) / d[a]).dropna()
        if len(v):
            mej.append({"esquema": esq, "comparacion": nombre, "n_reps": len(v), "media": v.mean(),
                        "p5": float(np.quantile(v, .05)), "p95": float(np.quantile(v, .95))})
mejora = pd.DataFrame(mej).round(2)
mejora.to_csv(c.ruta("04_resultados", "mejora_vs_B0.csv"), index=False)
print("\n== Reduccion % del RMSE (positivo = mejora) ==")
print(mejora.to_string(index=False))

rg = (lbg.groupby(["esquema", "modelo", "grupo"], sort=False)
      .agg(reps_con_datos=("rmse_grupo", "size"), n_val_grupo_media=("n_val_grupo", "mean"),
           rmse_media=("rmse_grupo", "mean"), rmse_p5=("rmse_grupo", lambda v: np.quantile(v, .05)),
           rmse_p95=("rmse_grupo", lambda v: np.quantile(v, .95))).reset_index().round(3))
rg.to_csv(c.ruta("04_resultados", "rmse_por_grupo.csv"), index=False)

# Comprobacion contra lo que produjo R
print("\n== Comprobacion contra los CSV que produjo R ==")
todo_ok = True
msg, ok = c.compara_con_R(lb, "lineas_base.csv", ["esquema", "rep", "modelo"], ["rmse", "mae", "r2_val"], 1e-9)
print(msg); todo_ok &= ok
msg, ok = c.compara_con_R(resumen, "lineas_base_resumen.csv", ["esquema", "modelo"], ["rmse_media", "rmse_p5", "rmse_p95", "mae_media", "r2_media"], 2e-3)
print(msg); todo_ok &= ok
print("RMSE de B2: V1", round(lb[(lb.esquema == "V1") & (lb.modelo == "B2")]["rmse"].mean(), 4),
      "| V2", round(lb[(lb.esquema == "V2") & (lb.modelo == "B2")]["rmse"].mean(), 4))

# Figura sencilla
fig, ax = plt.subplots(figsize=(8, 4.5))
ancho_b = 0.25
for j, mod in enumerate(["B0", "B1", "B2"]):
    vals = [lb[(lb.esquema == e) & (lb.modelo == mod)]["rmse"].mean() for e in ["V1", "V2"]]
    ax.bar(np.arange(2) + (j - 1) * ancho_b, vals, ancho_b, label=mod)
    for x, v in zip(np.arange(2) + (j - 1) * ancho_b, vals):
        ax.text(x, v + 0.01, f"{v:.3f}", ha="center", fontsize=9)
ax.set_xticks([0, 1]); ax.set_xticklabels(["V1", "V2"])
ax.set_ylabel("RMSE (t/ha), menor es mejor"); ax.set_title("Error de las lineas base")
ax.legend(); ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig(c.ruta("04_resultados", "fig_lineas_base_rmse.png"), dpi=150)
print("\nHecho." if todo_ok else "\nHecho, pero hay diferencias contra R: revisar.")
