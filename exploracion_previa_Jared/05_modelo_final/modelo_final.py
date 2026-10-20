"""modelo_final.py: modelo final y prediccion de las 59 parcelas ocultas (version Python de modelo_final.R).

Regla de eleccion (registro E2, E4 y E7, sin cambiar ninguna regla):
  procedimiento top1_global: entre las 148 variables candidatas se elige la de mayor |correlacion| con el
  rendimiento DENTRO de cada grupo, con las 138 parcelas de entrenamiento.
  Modelo: rendimiento ~ grupo + variable elegida (pendiente comun).
  Si a una parcela le falta la variable se predice con B2 (media del grupo), sin imputar.
  El script se detiene si top1_global no cumple E1 en los resultados ya calculados (script 60).
Entradas : 01_datos/preparados/base_138.csv y base_197_ubicacion.csv
           01_datos/originales/ID_area_rendimiento_70_30_Reto_AgroCebada.csv
           03_hipotesis_y_variables/variables/*_features.csv y *_hipotesis.csv
           04_resultados/60_seleccion_en_particion.csv y 62_b3_resumen.csv
Salidas  : 06_prediccion/predicciones_59_parcelas.csv
           05_modelo_final/modelo_final_resumen.csv, modelo_final_coeficientes.csv,
           modelo_final_top5_variables.csv y logs/modelo_final.log
Correr   : python 05_modelo_final/modelo_final.py
Sin azar. Al final compara contra lo que produjo R (04_resultados/referencia_R).
"""
import sys
from pathlib import Path
for p in Path(__file__).resolve().parents:
    if (p / "02_validacion_y_lineas_base" / "scripts" / "comun.py").exists():
        sys.path.insert(0, str(p / "02_validacion_y_lineas_base" / "scripts"))
        break
import numpy as np
import pandas as pd
from scipy import stats
import comun as c

log = c.iniciar_log("modelo_final")
print("== modelo_final.py ==")

# 1. Datos
base, y, g, ids = c.carga_base()
ubic = c.carga_ubicacion()
rend = pd.read_csv(c.ruta("01_datos", "originales", "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"),
                   usecols=["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"])
assert len(ubic) == 197 and len(rend) == 197

# 2. Las 148 variables (mismo armado que el script 60)
X, lin, hip, F, Z = c.carga_variables(ids)
assert X.shape == (138, 148)

# 3. Eleccion de la variable (top1_global)
MY, MX = c.medias_g(y, g), c.medias_g(X, g)
yc, Xc = y - MY[g], X - MX[g]
r = (Xc.T @ yc) / np.sqrt(np.maximum((Xc ** 2).sum(0) * (yc ** 2).sum(), 1e-24))
orden = np.argsort(-np.abs(r), kind="stable")
j = int(orden[0])
elegida = lin["variable"].iloc[j]
fila = lin.iloc[j]
print(f"\nVariable elegida (top1_global): {elegida} | hipotesis {fila['id']} | familia {fila['familia']} "
      f"| correlacion dentro de grupo: {r[j]:.4f}")
top5 = pd.DataFrame({"posicion": range(1, 6),
                     "variable": lin["variable"].iloc[orden[:5]].to_numpy(),
                     "correlacion_en_grupo": np.round(r[orden[:5]], 4)})
top5 = top5.merge(lin.rename(columns={"id": "hipotesis", "signo": "signo"}), on="variable", how="left")
top5 = top5[["posicion", "variable", "correlacion_en_grupo", "hipotesis", "familia", "signo"]]
print("\nLas 5 variables con mayor |correlacion| dentro de grupo:")
print(top5.to_string(index=False))

# 4. Comprobacion de E1 con los resultados ya calculados
sel = pd.read_csv(c.ruta("04_resultados", "60_seleccion_en_particion.csv"))
b3 = pd.read_csv(c.ruta("04_resultados", "62_b3_resumen.csv"))
s1 = sel[(sel.esquema == "V1") & (sel.procedimiento == "top1_global")].iloc[0]
s2 = sel[(sel.esquema == "V2") & (sel.procedimiento == "top1_global")].iloc[0]
cumple = bool(s1.delta_medio > c.DELTA_MIN and s1.n_mejora >= c.N_MEJORA_MIN and s2.delta_medio >= 0)
print(f"\ntop1_global frente a B2: V1 delta {s1.delta_medio:+.4f} (mejora en {int(s1.n_mejora)} de 100); "
      f"V2 delta {s2.delta_medio:+.4f} (mejora en {int(s2.n_mejora)} de 100); cumple E1: {cumple}")
if not cumple:
    raise SystemExit("top1_global no cumple E1: no se genera el modelo final; consultar al equipo")

# 5. Ajuste con las 138 y prediccion de las 59 (minimos cuadrados: intercepto, grupos 2 a 5, variable)
D = np.column_stack([np.ones(138)] + [(g == k).astype(float) for k in range(1, c.NG)] + [X[:, j]])
inv = np.linalg.inv(D.T @ D)
b = inv @ D.T @ y
res = y - D @ b
df = 138 - D.shape[1]
se = np.sqrt(np.diag(inv) * (res @ res) / df)
tv = b / se
pv = 2 * stats.t.sf(np.abs(tv), df)
terminos = ["(Intercept)"] + [f"grupo{c.GRUPOS[k]}" for k in range(1, c.NG)] + ["x"]
coef_tab = pd.DataFrame({"termino": terminos, "Estimate": b, "Std. Error": se, "t value": tv, "Pr(>|t|)": pv})
print("\nCoeficientes (x = variable elegida, estandarizada con las 197 parcelas):")
print(coef_tab.to_string(index=False))

oc = ubic[ubic["CONJUNTO"] == "PREDICCION"].copy()
assert len(oc) == 59 and not oc["ID_POLIGONO"].isin(ids).any()
oc["g"] = oc["grupo"].map({n: i for i, n in enumerate(c.GRUPOS)})
assert oc["g"].notna().all() and (np.bincount(g, minlength=c.NG)[oc["g"].astype(int)] > 0).all()
oc["g"] = oc["g"].astype(int)
oc["x"] = Z.loc[oc["ID_POLIGONO"], elegida].to_numpy()
p_b2 = MY[oc["g"].to_numpy()]
Do = np.column_stack([np.ones(59)] + [(oc["g"].to_numpy() == k).astype(float) for k in range(1, c.NG)] +
                     [np.nan_to_num(oc["x"].to_numpy())])
p_m = Do @ b
sin_var = oc["x"].isna().to_numpy()
pred = np.where(sin_var, p_b2, p_m)
print(f"\nParcelas ocultas sin valor de la variable (se predicen con B2): {int(sin_var.sum())}")

out = pd.DataFrame({"ID_POLIGONO": oc["ID_POLIGONO"].to_numpy(),
                    "AREA_HA": rend.set_index("ID_POLIGONO").loc[oc["ID_POLIGONO"], "AREA_HA"].to_numpy(),
                    "RENDIMIENTO_T_HA": np.round(pred, 2), "CONJUNTO": "PREDICCION"}).sort_values("ID_POLIGONO")
oc_reto = rend[rend["CONJUNTO"] == "PREDICCION"]
assert len(out) == 59 and not out.isna().any().any() and not out["ID_POLIGONO"].duplicated().any()
assert set(out["ID_POLIGONO"]) == set(oc_reto["ID_POLIGONO"]) and oc_reto["RENDIMIENTO_T_HA"].isna().all()
c.ruta("06_prediccion").mkdir(exist_ok=True)
c.ruta("05_modelo_final").mkdir(exist_ok=True)
out.to_csv(c.ruta("06_prediccion", "predicciones_59_parcelas.csv"), index=False, lineterminator="\n")

print("\nPrediccion media por grupo frente a la media de entrenamiento (t/ha):")
pg = out.assign(grupo=oc.set_index("ID_POLIGONO").loc[out["ID_POLIGONO"], "grupo"].to_numpy())
pg = pg.groupby("grupo").agg(n_ocultas=("RENDIMIENTO_T_HA", "size"), pred_media=("RENDIMIENTO_T_HA", "mean")).round(3)
pg["media_entrenamiento"] = [round(MY[c.GRUPOS.index(k)], 3) for k in pg.index]
print(pg.to_string())
print(f"Rango de las 59 predicciones: {out['RENDIMIENTO_T_HA'].min()} a {out['RENDIMIENTO_T_HA'].max()}")
print("[incierto] El formato de entrega no esta definido en las bases ni en las reglas del reto; "
      "se uso el formato del CSV base (ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO).")

# 6. Resumen
b3v1 = b3[b3.esquema == "V1"].iloc[0]
resumen = pd.DataFrame({
    "concepto": ["procedimiento", "variable_elegida", "hipotesis", "familia", "correlacion_en_grupo",
                 "coeficiente_por_1_desv_est", "n_parcelas_ajuste", "n_ocultas",
                 "ocultas_predichas_con_B2_por_falta_de_variable",
                 "V1_rmse_B2", "V1_rmse_modelo_final", "V1_delta", "V1_particiones_que_mejoran",
                 "V2_rmse_B2", "V2_rmse_modelo_final", "V2_delta", "V2_particiones_que_mejoran",
                 "V1_rmse_B3", "V1_delta_B3", "cumple_E1"],
    "valor": ["top1_global", elegida, fila["id"], fila["familia"], round(r[j], 4), round(b[-1], 4), 138, 59,
              int(sin_var.sum()), s1.rmse_B2, s1.rmse_proc, s1.delta_medio, int(s1.n_mejora),
              s2.rmse_B2, s2.rmse_proc, s2.delta_medio, int(s2.n_mejora),
              b3v1["rmse_B3"], b3v1["delta_medio"], "TRUE" if cumple else "FALSE"]})
resumen["valor"] = resumen["valor"].astype(str)
resumen.to_csv(c.ruta("05_modelo_final", "modelo_final_resumen.csv"), index=False, lineterminator="\n")
coef_tab.to_csv(c.ruta("05_modelo_final", "modelo_final_coeficientes.csv"), index=False, lineterminator="\n")
top5.to_csv(c.ruta("05_modelo_final", "modelo_final_top5_variables.csv"), index=False, lineterminator="\n")

# 7. Comparacion contra R
print("\n== Comparacion contra lo que produjo R ==")
ref = c.ruta("04_resultados", "referencia_R")
pr = pd.read_csv(ref / "predicciones_R.csv").sort_values("ID_POLIGONO").reset_index(drop=True)
o = out.reset_index(drop=True)
dif = float(np.abs(pr["RENDIMIENTO_T_HA"] - o["RENDIMIENTO_T_HA"]).max())
print(f"Predicciones: ids iguales {list(pr['ID_POLIGONO']) == list(o['ID_POLIGONO'])}; "
      f"diferencia maxima contra R = {dif:.4f} t/ha")
cr = pd.read_csv(ref / "modelo_final_coeficientes.csv")
print(f"Coeficientes: diferencia maxima contra R = {np.abs(cr.iloc[:, 1:5].to_numpy() - coef_tab.iloc[:, 1:5].to_numpy()).max():.2e}")
rr = pd.read_csv(ref / "modelo_final_resumen.csv", dtype=str)
print("Resumen: filas distintas contra R:",
      [k for k, v in zip(resumen.concepto, resumen.valor) if rr.set_index("concepto").loc[k, "valor"] != v] or "ninguna")
print("\nHecho. Sin errores.")
