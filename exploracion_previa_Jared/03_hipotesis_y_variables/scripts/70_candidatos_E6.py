"""70_candidatos_E6.py: candidatos nuevos contra el modelo final provisional (top1_global).

Diseno registrado ANTES de correr este script en el registro_experimentos.csv, fila E6.
Candidatos (todos con efectos de grupo; todo lo que se elige, se elige SOLO con las parcelas de ajuste):
  top1_global : rendimiento ~ grupo + 1 variable (la de mayor |r| dentro de grupo). Es el modelo provisional.
  C1_celda    : top1_global mas encogimiento del residuo por celda climatica (k por LOO, rejilla 0.5 a 64).
  C2_ridge17  : ridge con las 17 anomalias climaticas (alpha por LOO, forma cerrada).
  C3_ridge148 : ridge con las 148 variables (alpha por LOO, forma cerrada).
  C5_arboles  : ExtraTrees (200 arboles, hoja minima 3, semilla 2026) con indicadores de grupo y las 10 variables
                de mayor |r| dentro de grupo.
Regla de reemplazo (fijada antes): un candidato sustituye a top1_global solo si
  (1) cumple E1 contra B2, (2) mejora a top1_global en V1 en mas de 0.01 de RMSE medio y en >= 75 de 100
  particiones comparadas una a una, y (3) en V2 su RMSE medio no es peor que el de top1_global.
Entradas : 01_datos/preparados (base_138, folds_V1, folds_V2) y 03_hipotesis_y_variables/variables
Salidas  : 04_resultados/70_candidatos_por_particion.csv, 70_candidatos_resumen.csv y logs/70_candidatos_E6.log
Correr   : python 03_hipotesis_y_variables/scripts/70_candidatos_E6.py   (tarda unos minutos)
No toca el registro; la fila E7 con el resultado se anota aparte.
"""
import sys
from pathlib import Path
for p in Path(__file__).resolve().parents:
    if (p / "02_validacion_y_lineas_base" / "scripts" / "comun.py").exists():
        sys.path.insert(0, str(p / "02_validacion_y_lineas_base" / "scripts"))
        break
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
import comun as c

log = c.iniciar_log("70_candidatos_E6")
base, y, g, ids = c.carga_base()
X, lin, hip, F, Z = c.carga_variables(ids)
cel = base["celda_clima"].astype(str).to_numpy()
idx17 = np.where(lin["familia"].to_numpy() == "clima_anomalias")[0]
print(f"Variables lineales: {X.shape[1]}; anomalias climaticas: {len(idx17)}")

K_GRID = [0.5, 1, 2, 4, 8, 16, 32, 64, np.inf]
A_GRID = [0.1, 1, 10, 30, 100, 300, 1000, 3000, 10000]
NOMBRES = ["B2", "top1_global", "C1_celda", "C2_ridge17", "C3_ridge148", "C5_arboles"]


def ridge_loo(A, yc, cols):
    """Ridge sobre datos centrados por grupo; alpha por LOO (forma cerrada). Devuelve beta."""
    A = A[:, cols]
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    Uy = U.T @ yc
    mejor, a_mejor = np.inf, None
    for a in A_GRID:
        fit = U @ (s ** 2 / (s ** 2 + a) * Uy)
        h = (U ** 2 * (s ** 2 / (s ** 2 + a))).sum(axis=1)
        loo = (yc - fit) / (1 - h)
        m = float(np.mean(loo ** 2))
        if m <= mejor:          # en empate, el alpha mayor
            mejor, a_mejor = m, a
    return Vt.T @ (s / (s ** 2 + a_mejor) * Uy), a_mejor


def k_residuo(res, cF):
    """k de la rejilla con menor error LOO del ajuste de residuos por celda."""
    ser = pd.Series(res)
    S = ser.groupby(cF).transform("sum").to_numpy()
    N = ser.groupby(cF).transform("size").to_numpy()
    mejor, k_mejor = np.inf, np.inf
    for k in K_GRID:
        if np.isinf(k):
            adj = np.zeros_like(res)
        else:
            adj = np.where(N > 1, (S - res) / (N - 1 + k), 0.0)
        m = float(np.mean((res - adj) ** 2))
        if m <= mejor:
            mejor, k_mejor = m, k
    return k_mejor


def una_particion(p):
    fit, val = p["fit"], p["val"]
    nu = c.nucleo(X, y, g, fit, val)
    Xc, yc, Xv, pB2, yV = nu["Xc"], nu["yc"], nu["Xv"], nu["pB2"], nu["yV"]
    out = {"B2": c.rmse(yV - pB2)}
    j = int(np.argmax(np.abs(nu["r"])))            # empate: la primera, igual que top_k
    beta1 = (Xc[:, j] @ yc) / (Xc[:, j] @ Xc[:, j])
    p1 = pB2 + Xv[:, j] * beta1
    out["top1_global"] = c.rmse(yV - p1)
    # C1: residuo por celda
    res = yc - Xc[:, j] * beta1
    cF, cV = cel[fit], cel[val]
    k = k_residuo(res, cF)
    ser = pd.Series(res)
    S, N = ser.groupby(cF).sum(), ser.groupby(cF).size()
    adj = np.array([0.0 if (ci not in N.index or np.isinf(k)) else S[ci] / (N[ci] + k) for ci in cV])
    out["C1_celda"] = c.rmse(yV - (p1 + adj))
    out["k_C1"] = k
    # C2 y C3: ridge
    for nombre, cols in [("C2_ridge17", idx17), ("C3_ridge148", np.arange(X.shape[1]))]:
        b, a = ridge_loo(Xc, yc, cols)
        out[nombre] = c.rmse(yV - (pB2 + Xv[:, cols] @ b))
        out["alpha_" + nombre[:2]] = a
    # C5: arboles extra con grupo + 10 variables
    top = np.argsort(-np.abs(nu["r"]), kind="stable")[:10]
    D = np.eye(c.NG)
    Aff = np.hstack([D[g[fit]], X[fit][:, top]])
    Avv = np.hstack([D[g[val]], X[val][:, top]])
    m = ExtraTreesRegressor(n_estimators=200, min_samples_leaf=3, random_state=2026, n_jobs=1)
    m.fit(Aff, y[fit])
    out["C5_arboles"] = c.rmse(yV - m.predict(Avv))
    return out


filas = []
for esq in ["V1", "V2"]:
    P = c.carga_particiones(esq, ids)
    for p in P:
        r = una_particion(p)
        r.update({"esquema": esq, "rep": p["rep"]})
        filas.append(r)
    print(f"{esq}: {len(P)} particiones listas", flush=True)
D = pd.DataFrame(filas)
D.to_csv(c.ruta("04_resultados", "70_candidatos_por_particion.csv"), index=False, float_format="%.6f")

# comprobacion: top1_global debe coincidir con la tabla del script 60
ref = pd.read_csv(c.ruta("04_resultados", "60_seleccion_en_particion.csv"))
for esq in ["V1", "V2"]:
    r = ref[(ref.esquema == esq) & (ref.procedimiento == "top1_global")].iloc[0]
    d = D[D.esquema == esq]
    print(f"Comprobacion {esq}: top1_global aqui {d.top1_global.mean():.4f} contra script 60 {r.rmse_proc:.4f}; "
          f"B2 {d.B2.mean():.4f} contra {r.rmse_B2:.4f}")

res = []
V1, V2 = D[D.esquema == "V1"], D[D.esquema == "V2"]
for n in NOMBRES[1:]:
    d1 = (V1.B2 - V1[n]).to_numpy()
    d2 = (V2.B2 - V2[n]).to_numpy()
    a, b, cc = d1.mean() > c.DELTA_MIN, (d1 > 0).sum() >= c.N_MEJORA_MIN, d2.mean() >= 0
    row = {"candidato": n,
           "rmse_V1": V1[n].mean(), "delta_V1_vs_B2": d1.mean(), "n_mejora_V1_vs_B2": int((d1 > 0).sum()),
           "rmse_V2": V2[n].mean(), "delta_V2_vs_B2": d2.mean(), "n_mejora_V2_vs_B2": int((d2 > 0).sum()),
           "E1": c.veredicto(a, b, cc)}
    if n != "top1_global":
        e1 = (V1.top1_global - V1[n]).to_numpy()
        e2 = (V2.top1_global - V2[n]).to_numpy()
        row.update({"mejora_V1_vs_top1": e1.mean(), "n_mejor_V1_vs_top1": int((e1 > 0).sum()),
                    "mejora_V2_vs_top1": e2.mean()})
        row["reemplaza_a_top1"] = bool(row["E1"] == "pasa E1" and e1.mean() > 0.01
                                       and (e1 > 0).sum() >= 75 and e2.mean() >= 0)
    res.append(row)
R = pd.DataFrame(res)
R.to_csv(c.ruta("04_resultados", "70_candidatos_resumen.csv"), index=False, float_format="%.4f")
pd.set_option("display.width", 250, "display.max_columns", 30)
print()
print(R.round(4).to_string(index=False))
print(f"\nB2: V1 {V1.B2.mean():.4f}, V2 {V2.B2.mean():.4f}")
print("k elegido en C1 (V1): ", V1.k_C1.value_counts().to_dict())
print("alpha elegido C2 (V1):", V1.alpha_C2.value_counts().to_dict())
print("alpha elegido C3 (V1):", V1.alpha_C3.value_counts().to_dict())
print("\nHecho.")
