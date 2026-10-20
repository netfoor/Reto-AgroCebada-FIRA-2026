"""tablas_y_graficas.py: tablas finales y figuras de la carpeta 04_resultados (version Python).

Lee los CSV que ya produjeron los scripts 30, 60, 62 y 70 y arma:
  variables_que_pasan_E1.csv  las variables que pasan E1 (13) mas la que solo pasa con vecinos (1)
  comparacion_modelos.csv     B2, B3, top1_global, top3_global y los candidatos C1 a C5 en V1 y V2
  fig_variables_que_pasan_E1.png y fig_comparacion_modelos.png
No calcula nada nuevo: todas las cifras salen de los CSV de entrada.
Correr: python 04_resultados/tablas_y_graficas.py   (despues de los scripts 30, 60, 62 y 70)
"""
import sys
from pathlib import Path
for p in Path(__file__).resolve().parents:
    if (p / "02_validacion_y_lineas_base" / "scripts" / "comun.py").exists():
        sys.path.insert(0, str(p / "02_validacion_y_lineas_base" / "scripts"))
        break
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import comun as c

log = c.iniciar_log("tablas_y_graficas")
R = c.ruta("04_resultados")
AZUL, NARANJA, GRIS, TINTA = "#2a6fbb", "#d9822b", "#8a8a8a", "#222222"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": GRIS, "axes.labelcolor": TINTA, "xtick.color": TINTA, "ytick.color": TINTA})

# ----------------------------------------------------------------------------
# 1. Variables que pasan E1
# ----------------------------------------------------------------------------
pr = pd.read_csv(R / "60_pruebas_por_variable.csv")
v = pr[pr["veredicto"].isin(["pasa E1", "solo con vecinos (falla c)"])].copy()
v["orden"] = (v["veredicto"] != "pasa E1").astype(int)
v = v.sort_values(["orden", "delta_v1"], ascending=[True, False])
cols = ["hipotesis", "familia", "variable", "signo_registrado", "signo_coincide", "delta_v1", "n_mejora_v1",
        "delta_v2", "n_mejora_v2", "veredicto", "lectura"]
v = v[cols].copy()
v["n_mejora_v1"] = v["n_mejora_v1"].astype(int)
v["n_mejora_v2"] = v["n_mejora_v2"].astype(int)
v.to_csv(R / "variables_que_pasan_E1.csv", index=False, lineterminator="\n")
print(f"variables_que_pasan_E1.csv: {len(v)} filas ({(v.veredicto == 'pasa E1').sum()} pasan E1, "
      f"{(v.veredicto != 'pasa E1').sum()} solo con vecinos)")

# ----------------------------------------------------------------------------
# 2. Comparacion de modelos
# ----------------------------------------------------------------------------
sel = pd.read_csv(R / "60_seleccion_en_particion.csv")
b3 = pd.read_csv(R / "62_b3_resumen.csv").set_index("esquema")
cand = pd.read_csv(R / "70_candidatos_resumen.csv").set_index("candidato")


def fila_sel(nombre, proc):
    a = sel[(sel.esquema == "V1") & (sel.procedimiento == proc)].iloc[0]
    b = sel[(sel.esquema == "V2") & (sel.procedimiento == proc)].iloc[0]
    e1 = c.veredicto(a.delta_medio > c.DELTA_MIN, a.n_mejora >= c.N_MEJORA_MIN, b.delta_medio >= 0) == "pasa E1"
    return [nombre, a.rmse_proc, a.delta_medio, int(a.n_mejora), b.rmse_proc, b.delta_medio, int(b.n_mejora), e1]


a1 = sel[(sel.esquema == "V1") & (sel.procedimiento == "top1_global")].iloc[0]
a2 = sel[(sel.esquema == "V2") & (sel.procedimiento == "top1_global")].iloc[0]
filas = [["B2 (media por grupo)", a1.rmse_B2, 0.0, np.nan, a2.rmse_B2, 0.0, np.nan, np.nan]]
e1_b3 = c.veredicto(b3.loc["V1", "delta_medio"] > c.DELTA_MIN, b3.loc["V1", "n_mejora"] >= c.N_MEJORA_MIN,
                    b3.loc["V2", "delta_medio"] >= 0) == "pasa E1"
filas.append(["B3 (media por celda con encogimiento)", b3.loc["V1", "rmse_B3"], b3.loc["V1", "delta_medio"],
              int(b3.loc["V1", "n_mejora"]), b3.loc["V2", "rmse_B3"], b3.loc["V2", "delta_medio"],
              int(b3.loc["V2", "n_mejora"]), e1_b3])
filas.append(fila_sel("Modelo final: mejor variable (top1_global)", "top1_global"))
filas.append(fila_sel("Mejores 3 variables (top3_global)", "top3_global"))
nombres = {"C1_celda": "C1: top1_global mas residuo por celda", "C2_ridge17": "C2: ridge con 17 anomalias",
           "C3_ridge148": "C3: ridge con 148 variables", "C5_arboles": "C5: arboles con 10 variables"}
for k, n in nombres.items():
    r = cand.loc[k]
    filas.append([n, r.rmse_V1, r.delta_V1_vs_B2, int(r.n_mejora_V1_vs_B2), r.rmse_V2, r.delta_V2_vs_B2,
                  int(r.n_mejora_V2_vs_B2), r.E1 == "pasa E1"])
comp = pd.DataFrame(filas, columns=["modelo", "rmse_V1", "delta_V1", "mejora_V1", "rmse_V2", "delta_V2",
                                    "mejora_V2", "cumple_E1"])
comp.to_csv(R / "comparacion_modelos.csv", index=False, float_format="%.4f", lineterminator="\n")
print("\n" + comp.round(4).to_string(index=False))

# ----------------------------------------------------------------------------
# 3. Figuras
# ----------------------------------------------------------------------------
# 3a. mejora frente a B2 de cada modelo (V1 y V2)
d = comp.iloc[1:].iloc[::-1].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.2, 4.4))
y0 = np.arange(len(d))
ax.barh(y0 + 0.19, d["delta_V1"], height=0.34, color=AZUL, label="V1 (mismo tipo de parcela)")
ax.barh(y0 - 0.19, d["delta_V2"], height=0.34, color=NARANJA, label="V2 (celdas climaticas nuevas)")
ax.axvline(0, color=GRIS, lw=0.8)
ax.axvline(c.DELTA_MIN, color=GRIS, lw=0.8, ls="--")
ax.text(c.DELTA_MIN, len(d) - 0.35, " umbral E1 (0.02)", color=TINTA, fontsize=8, va="bottom")
for yy, a, b in zip(y0, d["delta_V1"], d["delta_V2"]):
    ax.text(max(a, 0) + 0.002, yy + 0.19, f"{a:+.3f}", va="center", fontsize=8, color=TINTA)
    ax.text(max(b, 0) + 0.002, yy - 0.19, f"{b:+.3f}", va="center", fontsize=8, color=TINTA)
ax.set_yticks(y0)
ax.set_yticklabels(d["modelo"], fontsize=8.5)
ax.set_xlabel("Mejora del RMSE frente a B2 (t/ha, positivo = mejor que B2)")
ax.set_title("Comparacion de modelos frente a B2 (media de 100 particiones)", loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
ax.set_xlim(min(-0.02, d[["delta_V1", "delta_V2"]].min().min() - 0.01), 0.1)
fig.tight_layout()
fig.savefig(R / "fig_comparacion_modelos.png", dpi=160)
plt.close(fig)

# 3b. las 14 variables: mejora en V1 y V2
w = v.iloc[::-1].reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.2, 5.2))
y1 = np.arange(len(w))
for yy, a, b in zip(y1, w["delta_v1"], w["delta_v2"]):
    ax.plot([a, b], [yy, yy], color="#cfcfcf", lw=1.2, zorder=1)
ax.scatter(w["delta_v1"], y1, s=42, color=AZUL, edgecolor="white", linewidth=1.2, zorder=3, label="V1", marker="o")
ax.scatter(w["delta_v2"], y1, s=42, color=NARANJA, edgecolor="white", linewidth=1.2, zorder=3, label="V2", marker="s")
ax.axvline(0, color=GRIS, lw=0.8)
ax.axvline(c.DELTA_MIN, color=GRIS, lw=0.8, ls="--")
ax.set_yticks(y1)
ax.set_yticklabels([f"{h}  {n}" for h, n in zip(w["hipotesis"], w["variable"])], fontsize=8.5)
ax.set_xlabel("Mejora del RMSE frente a B2 (t/ha); la linea punteada es el umbral E1 de V1 (0.02)")
ax.set_title("Variables que pasan E1 (13) y la que solo pasa con vecinos (HW6 clim_tmin_a)", loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.tight_layout()
fig.savefig(R / "fig_variables_que_pasan_E1.png", dpi=160)
plt.close(fig)
print("\nFiguras: fig_comparacion_modelos.png y fig_variables_que_pasan_E1.png")
print("Hecho.")
