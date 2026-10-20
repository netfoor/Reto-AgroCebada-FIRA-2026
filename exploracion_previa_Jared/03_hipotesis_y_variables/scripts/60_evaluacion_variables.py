"""60_evaluacion_variables.py: evalua cada variable candidata contra B2 (regla E1).

Para cada una de las 148 variables ajusta, dentro de cada particion V1 y V2 y solo con
las parcelas de ajuste, rendimiento ~ grupo + variable (pendiente comun) y lo compara con
B2 en las mismas parcelas de validacion. delta = RMSE(B2) menos RMSE(modelo); positivo es mejora.
Regla E1: (a) delta medio en V1 mayor a 0.02; (b) delta positivo en al menos 75 de 100 particiones V1;
(c) delta medio en V2 no negativo. Falla (a) o (b): se descarta. Falla solo (c): solo con vecinos.
Tambien hace: pruebas de curva (HB3 y HB4), dos controles de permutacion (por grupo, semilla 2026;
estricto por celda, semilla 2027), y la seleccion de la mejor variable DENTRO de cada particion.
Los controles de permutacion usan el generador de numeros de numpy, asi que sus cifras no son
identicas a las de R (que usa el suyo); lo demas se compara con R y debe coincidir.
Entradas : base_138.csv, folds_V1/V2.csv, variables/*_features.csv y *_hipotesis.csv
Salidas  : 04_resultados/60_pruebas_por_variable.csv, 60_resumen_hipotesis.csv, 60_permutacion.csv,
           60_seleccion_en_particion.csv y logs/60_evaluacion_variables.log
Correr   : python 03_hipotesis_y_variables/scripts/60_evaluacion_variables.py
"""
import sys
from pathlib import Path
for _p in Path(__file__).resolve().parents:
    if (_p / "02_validacion_y_lineas_base" / "scripts" / "comun.py").exists():
        sys.path.insert(0, str(_p / "02_validacion_y_lineas_base" / "scripts"))
        break
import numpy as np
import pandas as pd
import comun as c

N_PERM, SEMILLA = 100, 2026
log = c.iniciar_log("60_evaluacion_variables")
base, y, g, ids = c.carga_base()
X, lin, hip, F, Z = c.carga_variables(ids)
K = X.shape[1]
print("Variables candidatas:", K, "| por familia:", lin["familia"].value_counts().to_dict())
idx_fam = {f: np.where(lin["familia"].to_numpy() == f)[0] for f in c.FAMILIAS}
P1, P2 = c.carga_particiones("V1", ids), c.carga_particiones("V2", ids)
assert len(P1) == 100 and len(P2) == 100

# Comprobacion 1: el calculo rapido coincide con una regresion por minimos cuadrados completa
rng0 = np.random.default_rng(1)
for _ in range(5):
    p, k = P1[rng0.integers(100)], int(rng0.integers(K))
    D = np.column_stack([np.eye(c.NG)[g[p["fit"]]], X[p["fit"], k]])
    b, *_ = np.linalg.lstsq(D, y[p["fit"]], rcond=None)
    Dv = np.column_stack([np.eye(c.NG)[g[p["val"]]], X[p["val"], k]])
    r_lm = c.rmse(y[p["val"]] - Dv @ b)
    assert abs(r_lm - c.nucleo(X, y, g, p["fit"], p["val"])["rm"][k]) < 1e-9
print("Comprobacion 1: el calculo rapido coincide con minimos cuadrados completos en 5 casos al azar.")

E1 = c.corre_esquema(P1, y, g, X, idx_fam, True)
E2 = c.corre_esquema(P2, y, g, X, idx_fam, True)
lb = pd.read_csv(c.ruta("04_resultados", "lineas_base.csv"))
for esq, E in [("V1", E1), ("V2", E2)]:
    ref = lb[(lb.esquema == esq) & (lb.modelo == "B2")].sort_values("rep")["rmse"].to_numpy()
    assert np.abs(ref - E["b2"]).max() < 1e-9
print("Comprobacion 2: el RMSE de B2 coincide con lineas_base.csv en las 200 particiones.",
      "B2 medio V1:", round(E1["b2"].mean(), 3), "| V2:", round(E2["b2"].mean(), 3))
r1, r2 = c.resume_delta(E1), c.resume_delta(E2)

# Correlacion parcial dentro de grupo con las 138
MXa = c.medias_g(X, g)
Xca = X - MXa[g]
yca = y - c.medias_g(y, g)[g]
r_par = (Xca.T @ yca) / np.sqrt((Xca ** 2).sum(axis=0) * (yca ** 2).sum())
sig_obs = np.where(r_par > 0, "+", "-")


def lectura(r):
    if r["veredicto"] not in ("pasa E1", "solo con vecinos (falla c)"):
        return "descartada"
    if r["veredicto"] == "solo con vecinos (falla c)":
        return "depende de vecinos (falla c)"
    if r["signo_registrado"] == "ninguno":
        return "hallazgo exploratorio (sin signo registrado)"
    if r["signo_coincide"] == "si":
        return "confirmada (signo coincide)"
    if r["signo_coincide"] == "no":
        return "contradice el signo registrado"
    return "curva: revisar"


b2v1, b2v2 = E1["b2"].mean(), E2["b2"].mean()
pr = pd.DataFrame({
    "hipotesis": lin["id"], "familia": lin["familia"], "variable": lin["variable"], "signo_registrado": lin["signo"],
    "r_parcial_en_grupo": np.round(r_par, 3), "signo_observado": sig_obs,
    "rmse_B2_v1": round(b2v1, 4), "rmse_modelo_v1": np.round(r1["rmse"], 4),
    "delta_v1": np.round(r1["media"], 4), "n_mejora_v1": r1["n_mejora"],
    "rmse_B2_v2": round(b2v2, 4), "rmse_modelo_v2": np.round(r2["rmse"], 4),
    "delta_v2": np.round(r2["media"], 4), "n_mejora_v2": r2["n_mejora"]})
pr["signo_coincide"] = np.where(pr["signo_registrado"] == "ninguno", "sin signo",
                                np.where(pr["signo_registrado"] == pr["signo_observado"], "si", "no"))

# Pruebas de curva (variable y su cuadrado, estandarizadas con las 197)
curv = hip[(~hip["spec"].isin(["lineal", "NO_EVALUABLE"])) & (~hip["id"].isin(c.NO_EVALUABLES))]
filas_curva = []
for _, h in curv.iterrows():
    v = h["spec"].split("+")[0].strip()
    x = F.set_index("ID_POLIGONO")[v]
    D197 = pd.DataFrame({"x": x, "x2": x ** 2})
    D197 = (D197 - D197.mean()) / D197.std(ddof=1)
    D = D197.loc[ids].to_numpy()

    def ev(P):
        d = np.zeros(len(P))
        for j, p in enumerate(P):
            fit, val = p["fit"], p["val"]
            gF, gV = g[fit], g[val]
            MY, MD = c.medias_g(y[fit], gF), c.medias_g(D[fit], gF)
            A = D[fit] - MD[gF]
            b = np.linalg.solve(A.T @ A, A.T @ (y[fit] - MY[gF]))
            pred = MY[gV] + (D[val] - MD[gV]) @ b
            d[j] = c.rmse(y[val] - MY[gV]) - c.rmse(y[val] - pred)
        return d
    d1, d2 = ev(P1), ev(P2)
    Aa = D - c.medias_g(D, g)[g]
    ba = np.linalg.solve(Aa.T @ Aa, Aa.T @ yca)
    filas_curva.append({"hipotesis": h["id"], "familia": h["familia"], "variable": h["spec"],
                        "signo_registrado": h["signo"], "r_parcial_en_grupo": np.nan, "signo_observado": np.nan,
                        "signo_coincide": "coef. cuadratico " + ("negativo" if ba[1] < 0 else "positivo"),
                        "rmse_B2_v1": round(b2v1, 4), "rmse_modelo_v1": round(b2v1 - d1.mean(), 4),
                        "delta_v1": round(d1.mean(), 4), "n_mejora_v1": int((d1 > 0).sum()),
                        "rmse_B2_v2": round(b2v2, 4), "rmse_modelo_v2": round(b2v2 - d2.mean(), 4),
                        "delta_v2": round(d2.mean(), 4), "n_mejora_v2": int((d2 > 0).sum())})
pr = pd.concat([pr, pd.DataFrame(filas_curva)], ignore_index=True)
pr["E1_a"] = pr["delta_v1"] > c.DELTA_MIN
pr["E1_b"] = pr["n_mejora_v1"] >= c.N_MEJORA_MIN
pr["E1_c"] = pr["delta_v2"] >= 0
pr["veredicto"] = [c.veredicto(a, b, cc) for a, b, cc in zip(pr["E1_a"], pr["E1_b"], pr["E1_c"])]
pr["nota"] = ""
pr["lectura"] = pr.apply(lectura, axis=1)
nota_hc2 = "el indicador Tmedia jul-ago 15-20 C vale 1 en las 197 parcelas; misma variable que HC1"
pr = pd.concat([pr, pd.DataFrame([{"hipotesis": "HC2", "familia": "clima_ventanas", "variable": "(no evaluable)",
                                   "veredicto": "no evaluable", "lectura": "no evaluable", "nota": nota_hc2}])], ignore_index=True)
pr.to_csv(c.ruta("04_resultados", "60_pruebas_por_variable.csv"), index=False)

ev_ok = pr[pr["veredicto"] != "no evaluable"]
print("\nPruebas realizadas (variables lineales mas curvas):", len(ev_ok))
print("Veredicto E1 sobre las pruebas reales:\n" + ev_ok["veredicto"].value_counts().to_string())
print("\nLectura de las pruebas:\n" + pr["lectura"].value_counts().to_string())
cols = ["hipotesis", "variable", "signo_registrado", "signo_coincide", "delta_v1", "n_mejora_v1", "delta_v2", "lectura"]
print("\nPasan E1 o solo fallan (c), ordenadas por delta V1:")
print(ev_ok[ev_ok["veredicto"].isin(["pasa E1", "solo con vecinos (falla c)"])].sort_values("delta_v1", ascending=False)[cols].to_string(index=False))

res_hip = (ev_ok.groupby("hipotesis")
           .apply(lambda d: pd.Series({"n_variables": len(d), "n_pasan": int((d["veredicto"] == "pasa E1").sum()),
                                       "n_solo_vecinos": int((d["veredicto"] == "solo con vecinos (falla c)").sum()),
                                       "n_descartadas": int((d["veredicto"] == "descartar").sum()),
                                       "mejor_variable": d["variable"].iloc[int(np.argmax(d["delta_v1"].to_numpy()))],
                                       "mejor_delta_v1": d["delta_v1"].max()}), include_groups=False).reset_index())
res_hip.to_csv(c.ruta("04_resultados", "60_resumen_hipotesis.csv"), index=False)

# Seleccion dentro de cada particion, con el rendimiento real
def res_sel(E, esq):
    filas = []
    for nm, v in E["sel"].items():
        d = E["b2"] - v
        ok = ~np.isnan(d)
        filas.append({"esquema": esq, "procedimiento": nm, "rmse_B2": E["b2"].mean(), "rmse_proc": np.nanmean(v),
                      "delta_medio": np.nanmean(d), "delta_p5": np.nanquantile(d, .05), "delta_p95": np.nanquantile(d, .95),
                      "n_mejora": int((d[ok] > 0).sum()), "n_part": int(ok.sum())})
    return pd.DataFrame(filas)


sel = pd.concat([res_sel(E1, "V1"), res_sel(E2, "V2")], ignore_index=True).round(4)
sel.to_csv(c.ruta("04_resultados", "60_seleccion_en_particion.csv"), index=False)
print("\n== Seleccion dentro de cada particion (delta = B2 menos procedimiento; positivo = mejora) ==")
print(sel.to_string(index=False))

# Controles de permutacion
def corre_perm(yp, Xp):
    a = c.corre_esquema(P1, yp, g, Xp, idx_fam, True)
    b = c.corre_esquema(P2, yp, g, Xp, idx_fam, True)
    ra, rb = c.resume_delta(a), c.resume_delta(b)
    ok_ab = (ra["media"] > c.DELTA_MIN) & (ra["n_mejora"] >= c.N_MEJORA_MIN)
    return {"pasan_ab": int(ok_ab.sum()), "pasan_abc": int((ok_ab & (rb["media"] >= 0)).sum()),
            "mejor_delta_v1": ra["media"].max(), "mejor_n_mejora_v1": int(ra["n_mejora"].max()),
            "sel_top1_delta_v1": float(np.mean(a["b2"] - a["sel"]["top1_global"])),
            "sel_top3_delta_v1": float(np.nanmean(a["b2"] - a["sel"]["top3_global"])),
            "sel_top1_delta_v2": float(np.mean(b["b2"] - b["sel"]["top1_global"]))}


rng = np.random.default_rng(SEMILLA)
perm = []
for p in range(1, N_PERM + 1):
    yp = y.copy()
    for k in range(c.NG):
        i = np.where(g == k)[0]
        yp[i] = y[i][rng.permutation(len(i))]
    perm.append({"perm": p, **corre_perm(yp, X), "nulo": "grupo"})

bloque = np.array([f"{a}_{b}" for a, b in zip(g, base["celda_clima"])])
def donante_celda(rg):
    don = np.zeros(len(y), int)
    for k in range(c.NG):
        celdas = np.unique(bloque[g == k])
        dest = rg.permutation(celdas)
        for a, b in zip(celdas, dest):
            miembros = np.where(bloque == a)[0]
            donantes = np.where(bloque == b)[0]
            don[miembros] = donantes[rg.integers(0, len(donantes), len(miembros))]
    return don


rng2 = np.random.default_rng(SEMILLA + 1)
for p in range(1, N_PERM + 1):
    perm.append({"perm": p, **corre_perm(y, X[donante_celda(rng2)]), "nulo": "celda"})
perm = pd.DataFrame(perm)
perm.round(4).to_csv(c.ruta("04_resultados", "60_permutacion.csv"), index=False)

real_ab = int((pr["E1_a"] & pr["E1_b"]).sum())
real_abc = int((pr["veredicto"] == "pasa E1").sum())
refp = pd.read_csv(c.ruta("04_resultados", "referencia_R", "60_permutacion.csv"))
for nl in ["grupo", "celda"]:
    pp, rr = perm[perm["nulo"] == nl], refp[refp["nulo"] == nl]
    print(f"\n== Control de permutacion, nulo por {nl} ({N_PERM} repeticiones) ==")
    print(f"Variables que pasan E1 completa por azar: media Python {pp.pasan_abc.mean():.2f} (max {pp.pasan_abc.max()}) | R {rr.pasan_abc.mean():.2f} (max {rr.pasan_abc.max()}) | REAL: {real_abc}")
    print(f"Variables que pasan (a)+(b) por azar: media Python {pp.pasan_ab.mean():.2f} (max {pp.pasan_ab.max()}) | R {rr.pasan_ab.mean():.2f} | REAL: {real_ab}")
    print(f"Mejor delta V1 entre todas por azar: media Python {pp.mejor_delta_v1.mean():.4f} | R {rr.mejor_delta_v1.mean():.4f} | REAL: {r1['media'].max():.4f}")
    print(f"Elegir la mejor variable dentro de la particion con el nulo: delta V1 Python {pp.sel_top1_delta_v1.mean():.4f} | R {rr.sel_top1_delta_v1.mean():.4f}; V2 Python {pp.sel_top1_delta_v2.mean():.4f} | R {rr.sel_top1_delta_v2.mean():.4f} (negativo = empeora a B2)")

# Comprobacion contra lo que produjo R (lo determinista)
print("\n== Comprobacion contra los CSV que produjo R ==")
a = pr[pr["veredicto"] != "no evaluable"][["hipotesis", "variable", "delta_v1", "n_mejora_v1", "delta_v2", "n_mejora_v2", "veredicto"]]
b = pd.read_csv(c.ruta("04_resultados", "referencia_R", "60_pruebas_por_variable.csv"))
b = b[b["veredicto"] != "no evaluable"][["hipotesis", "variable", "delta_v1", "n_mejora_v1", "delta_v2", "n_mejora_v2", "veredicto"]]
m = a.merge(b, on=["hipotesis", "variable"], suffixes=("_py", "_R"))
print(f"Pruebas emparejadas con R: {len(m)} de {len(a)} (R tiene {len(b)})")
dif = max(float((m[f"{k}_py"] - m[f"{k}_R"]).abs().max()) for k in ["delta_v1", "n_mejora_v1", "delta_v2", "n_mejora_v2"])
print(f"Diferencia maxima en deltas y conteos: {dif:.1e}; veredictos distintos: {int((m['veredicto_py'] != m['veredicto_R']).sum())}")
msg, ok = c.compara_con_R(sel, "60_seleccion_en_particion.csv", ["esquema", "procedimiento"],
                          ["rmse_B2", "rmse_proc", "delta_medio", "delta_p5", "delta_p95", "n_mejora"], 1e-4)
print(msg)
print("\nHecho." if (len(m) == len(a) == len(b) and dif < 1e-3 and ok) else "\nHecho, pero hay diferencias contra R: revisar.")
