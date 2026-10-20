"""comparar_modelo_externo.py: mide un modelo ajeno con LAS MISMAS particiones y la MISMA regla E1 del proyecto.

Sirve para comparar el trabajo de otra persona (por ejemplo la referencia MIX) contra B2, B3 y el modelo final
sin discutir sobre el esquema de validacion. Las particiones son las de 01_datos/preparados (folds_V1 y folds_V2).

DOS FORMAS DE USARLO

1) Con una funcion en Python (el modelo se reajusta en cada particion, como debe ser):
     python comparar_modelo_externo.py --modelo mi_modelo.py --nombre MIX
   mi_modelo.py debe definir   predecir(ajuste, validacion)   y devolver un arreglo con una prediccion
   por fila de `validacion` (t/ha). Ambos son DataFrames de pandas:
     ajuste      las parcelas de ajuste, con RENDIMIENTO_T_HA
     validacion  las parcelas de validacion, SIN RENDIMIENTO_T_HA (la columna no existe)
   Columnas de los dos: ID_POLIGONO, Estado, Municipio, grupo, celda_clima y las 148 variables candidatas
   SIN estandarizar (las de 03_hipotesis_y_variables/variables). Todo lo que el modelo elija o ajuste
   (variables, hiperparametros, medias) debe hacerse DENTRO de predecir con `ajuste`; si usa las 138 parcelas
   para elegir algo fuera de la funcion, el resultado queda inflado y no es comparable.

2) Con predicciones ya hechas (CSV con columnas esquema, rep, ID_POLIGONO, prediccion):
     python comparar_modelo_externo.py --predicciones mis_predicciones.csv --nombre MIX
   esquema es V1 o V2, rep va de 1 a 100 y cada fila es una parcela de validacion de esa particion.
   Cada prediccion debe haberse hecho SIN ver el rendimiento de esa parcela ni elegir nada con ella
   (si se eligio con las 138, se anota en el reporte como no comparable).

Salidas (04_resultados/comparacion_externo/): <nombre>_por_particion.csv y <nombre>_resumen.csv
Tambien se imprime el veredicto E1 (a: mejora media > 0.02 en V1; b: mejora en >= 75 de 100 particiones de V1;
c: mejora media >= 0 en V2), la diferencia contra el modelo final (top1_global) y el RMSE por grupo.

Prueba del comparador (usa B2 y top1_global como si fueran modelos ajenos; debe dar V1 0.5021 y 0.4734):
     python comparar_modelo_externo.py --demo
"""
import argparse
import importlib.util
import sys
from pathlib import Path
for p in Path(__file__).resolve().parents:
    if (p / "02_validacion_y_lineas_base" / "scripts" / "comun.py").exists():
        sys.path.insert(0, str(p / "02_validacion_y_lineas_base" / "scripts"))
        break
import numpy as np
import pandas as pd
import comun as c

TOL = 1e-9   # diferencias menores que esto se cuentan como empate
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--modelo", help="archivo .py con predecir(ajuste, validacion)")
ap.add_argument("--funcion", default="predecir", help="nombre de la funcion (por defecto predecir)")
ap.add_argument("--predicciones", help="CSV con esquema, rep, ID_POLIGONO, prediccion")
ap.add_argument("--nombre", default="externo", help="nombre para los archivos de salida")
ap.add_argument("--demo", action="store_true", help="prueba con B2 y top1_global")
a = ap.parse_args()
if not (a.modelo or a.predicciones or a.demo):
    ap.error("indica --modelo, --predicciones o --demo")

base, y, g, ids = c.carga_base()
X, lin, hip, F, Z = c.carga_variables(ids)
ESQ = {e: c.carga_particiones(e, ids) for e in ["V1", "V2"]}
RAW = F.set_index("ID_POLIGONO")[lin["variable"].tolist()]
META = base[["ID_POLIGONO", "Estado", "Municipio", "grupo", "celda_clima"]]


def tabla(idx):
    t = META.iloc[idx].reset_index(drop=True)
    return pd.concat([t, RAW.loc[t["ID_POLIGONO"]].reset_index(drop=True)], axis=1)


# ---------------------------------------------------------------------------
# Predicciones del modelo ajeno en cada particion
# ---------------------------------------------------------------------------
def predice_con_funcion(fun):
    out = {}
    for e, P in ESQ.items():
        for p in P:
            aj = tabla(p["fit"]).assign(RENDIMIENTO_T_HA=y[p["fit"]])
            va = tabla(p["val"])
            pr = np.asarray(fun(aj.copy(), va.copy()), float).ravel()
            if len(pr) != len(p["val"]) or np.isnan(pr).any():
                raise ValueError(f"{e} rep {p['rep']}: la funcion debe devolver {len(p['val'])} numeros sin NA")
            out[(e, p["rep"])] = pr
    return out


def predice_con_csv(ruta_csv):
    d = pd.read_csv(ruta_csv)
    faltan = {"esquema", "rep", "ID_POLIGONO", "prediccion"} - set(d.columns)
    if faltan:
        raise ValueError(f"Faltan columnas en el CSV: {faltan}")
    out = {}
    for e, P in ESQ.items():
        for p in P:
            ids_val = [ids[i] for i in p["val"]]
            s = d[(d.esquema == e) & (d.rep == p["rep"])].set_index("ID_POLIGONO")["prediccion"]
            if set(s.index) != set(ids_val) or len(s) != len(ids_val):
                raise ValueError(f"{e} rep {p['rep']}: las parcelas del CSV no son las de validacion de esa particion")
            out[(e, p["rep"])] = s.loc[ids_val].to_numpy(float)
    return out


def modelos_demo():
    def b2(aj, va):
        m = aj.groupby("grupo")["RENDIMIENTO_T_HA"].mean()
        return va["grupo"].map(m).to_numpy()

    def top1(aj, va):
        cols = lin["variable"].tolist()
        mu, sd = F[cols].mean(), F[cols].std(ddof=1)        # estandarizar con las 197 es parte del modelo del proyecto
        A, V = (aj[cols] - mu) / sd, (va[cols] - mu) / sd
        yy, gg = aj["RENDIMIENTO_T_HA"], aj["grupo"]
        yc = yy - yy.groupby(gg).transform("mean")
        Ac = A - A.groupby(gg).transform("mean")
        r = (Ac.mul(yc, axis=0).sum()) / np.sqrt((Ac ** 2).sum() * (yc ** 2).sum())
        j = r.abs().idxmax()
        beta = (Ac[j] * yc).sum() / (Ac[j] ** 2).sum()
        mg, mx = yy.groupby(gg).mean(), A[j].groupby(gg).mean()
        return (va["grupo"].map(mg) + beta * (V[j] - va["grupo"].map(mx))).to_numpy()
    return b2, top1


if a.demo:
    b2f, t1f = modelos_demo()
    trabajos = [("demo_B2", predice_con_funcion(b2f)), ("demo_top1_global", predice_con_funcion(t1f))]
elif a.modelo:
    spec = importlib.util.spec_from_file_location("modelo_ajeno", a.modelo)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    trabajos = [(a.nombre, predice_con_funcion(getattr(mod, a.funcion)))]
else:
    trabajos = [(a.nombre, predice_con_csv(a.predicciones))]

# ---------------------------------------------------------------------------
# Referencias del proyecto en las mismas particiones
# ---------------------------------------------------------------------------
idx_fam = {f: np.where(lin["familia"].to_numpy() == f)[0] for f in c.FAMILIAS}
ref = {e: c.corre_esquema(P, y, g, X, idx_fam, con_seleccion=True) for e, P in ESQ.items()}
b2_rm = {e: ref[e]["b2"] for e in ESQ}
t1_rm = {e: ref[e]["sel"]["top1_global"] for e in ESQ}
b3 = pd.read_csv(c.ruta("04_resultados", "62_b3_resumen.csv")).set_index("esquema")
sal = c.ruta("04_resultados", "comparacion_externo")
sal.mkdir(exist_ok=True)

for nombre, pred in trabajos:
    filas = []
    for e, P in ESQ.items():
        for k, p in enumerate(P):
            err = y[p["val"]] - pred[(e, p["rep"])]
            filas.append({"esquema": e, "rep": p["rep"], "rmse_modelo": c.rmse(err),
                          "rmse_B2": b2_rm[e][k], "rmse_top1_global": t1_rm[e][k]})
    D = pd.DataFrame(filas)
    D.to_csv(sal / f"{nombre}_por_particion.csv", index=False, float_format="%.6f")
    V1, V2 = D[D.esquema == "V1"], D[D.esquema == "V2"]
    d1, d2 = (V1.rmse_B2 - V1.rmse_modelo).to_numpy(), (V2.rmse_B2 - V2.rmse_modelo).to_numpy()
    ok = (d1.mean() > c.DELTA_MIN, (d1 > TOL).sum() >= c.N_MEJORA_MIN, d2.mean() >= 0)
    ver = c.veredicto(*ok)
    t1v1, t1v2 = (V1.rmse_top1_global - V1.rmse_modelo).to_numpy(), (V2.rmse_top1_global - V2.rmse_modelo).to_numpy()
    resumen = pd.DataFrame({"concepto": [
        "rmse_V1", "rmse_V1_B2", "rmse_V1_B3", "rmse_V1_top1_global", "delta_V1_vs_B2", "n_mejora_V1_vs_B2",
        "rmse_V2", "rmse_V2_B2", "rmse_V2_top1_global", "delta_V2_vs_B2", "n_mejora_V2_vs_B2",
        "E1_a", "E1_b", "E1_c", "veredicto_E1",
        "mejora_V1_vs_top1_global", "n_mejor_V1_vs_top1_global", "mejora_V2_vs_top1_global"],
        "valor": [V1.rmse_modelo.mean(), V1.rmse_B2.mean(), b3.loc["V1", "rmse_B3"], V1.rmse_top1_global.mean(),
                  d1.mean(), int((d1 > TOL).sum()), V2.rmse_modelo.mean(), V2.rmse_B2.mean(),
                  V2.rmse_top1_global.mean(), d2.mean(), int((d2 > TOL).sum()), *ok, ver,
                  t1v1.mean(), int((t1v1 > TOL).sum()), t1v2.mean()]})
    resumen["valor"] = resumen["valor"].map(lambda v: f"{v:.4f}" if isinstance(v, (float, np.floating)) else str(v))
    resumen.to_csv(sal / f"{nombre}_resumen.csv", index=False, lineterminator="\n")
    # RMSE por grupo en V1 (agrupando todas las parcelas de validacion de las 100 particiones)
    err_g = {k: [] for k in range(c.NG)}
    for p in ESQ["V1"]:
        e_ = y[p["val"]] - pred[("V1", p["rep"])]
        for k in range(c.NG):
            err_g[k] += list(e_[g[p["val"]] == k])
    print(f"\n===== {nombre} =====")
    print(resumen.to_string(index=False))
    print("RMSE por grupo en V1: " + ", ".join(f"{c.GRUPOS[k]} {c.rmse(np.array(v)):.3f}" for k, v in err_g.items() if v))
    print(f"Lectura: {'cumple E1 contra B2' if ver == 'pasa E1' else 'NO cumple E1 (' + ver + ')'}; "
          f"{'mejora' if t1v1.mean() > TOL else 'no mejora'} al modelo final en V1 por {t1v1.mean():+.4f} t/ha "
          f"({int((t1v1 > TOL).sum())} de 100 particiones) y {t1v2.mean():+.4f} en V2.")
print("\nNota: un RMSE menor en V1/V2 solo vale si todo lo que el modelo elige se eligio con las parcelas de ajuste. "
      "V2 deja celdas climaticas enteras fuera y es la prueba mas dura; con 23 celdas y una sola temporada "
      "las diferencias pequenas (menos de 0.01) no deben leerse como ventaja.")
