"""Ronda 2, paso 2: CV 10×5 con semilla nueva (20261021) sobre las 103 parcelas de desarrollo de la ronda 1.
Evalúa congelados, las 7 familias de la ronda 1 (para el nulo) y las correcciones H×{E_JK, MIX}. No lee la caja."""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

import lib_r2 as R

L = R.L
SAL = R.AQUI / "resultados_cv"


def particiones(ids_dev):
    ids = np.array(sorted(ids_dev))
    ext, inn = [], []
    for r in range(10):
        for f, (a, b) in enumerate(KFold(5, shuffle=True, random_state=R.SEMILLA_CV2 + r).split(ids)):
            ext += [(r, f, "entrenamiento", i) for i in ids[a]] + [(r, f, "validacion", i) for i in ids[b]]
            tr = np.sort(ids[a])
            for k, (c, d) in enumerate(KFold(4, shuffle=True, random_state=R.SEMILLA_CV2 + 1000 + 10 * r + f).split(tr)):
                inn += [(r, f, k, "entrenamiento", i) for i in tr[c]] + [(r, f, k, "validacion", i) for i in tr[d]]
    return (pd.DataFrame(ext, columns=["repeticion", "pliegue", "rol", L.ID]),
            pd.DataFrame(inn, columns=["repeticion", "pliegue", "pliegue_interno", "rol", L.ID]))


def main():
    if SAL.exists():
        raise SystemExit("resultados_cv/ ya existe")
    SAL.mkdir()
    t0 = time.time()
    reg = json.loads((R.AQUI / "registro_previo.json").read_text())
    chequeo = json.loads((R.AQUI / "chequeo_x.json").read_text())
    hip = [h for h in R.HIPOTESIS if chequeo[h]["pasa_regla_no_etiqueta"]]
    tx = L.tabla_x()
    t = tx.set_index(L.ID)
    vx = pd.read_csv(R.AQUI / "variables_externas.csv").set_index(L.ID)
    y = L.etiquetas_desarrollo()
    ext, inn = particiones(y.index)
    ext.to_csv(SAL / "particiones_externas.csv", index=False)
    inn.to_csv(SAL / "particiones_internas.csv", index=False)
    assert L.sha(SAL / "particiones_externas.csv") == reg["particiones"]["externas_sha256"]
    filas = []
    for (r, f), g in ext.groupby(["repeticion", "pliegue"], sort=True):
        tr = g.loc[g.rol.eq("entrenamiento"), L.ID].to_numpy()
        va = g.loc[g.rol.eq("validacion"), L.ID].to_numpy()
        fi = inn[(inn.repeticion == r) & (inn.pliegue == f)][["pliegue_interno", "rol", L.ID]]
        cong, e = R.bases_y_residuos(tx, y, tr, va, fi, R.SEMILLA_CV2 + 5000 + 100 * int(r) + 10 * int(f))
        prop, _ = L.familias_propias(tx, y, tr, va, cong)
        prop["F6"] = L.regresion_kriging_jared(tx, y, tr, va, fi)
        prop["F7"] = 0.5 * prop["F6"] + 0.5 * cong["K"]
        nuevas = {}
        for h in hip:
            for b in R.BASES:
                nuevas[f"{h}_{b}"], _ = R.corregir(cong[b], e[b], vx[R.HIPOTESIS[h]], va)
        visto = t.loc[va, "Municipio"].isin(set(t.loc[tr, "Municipio"])).to_numpy()
        base = pd.DataFrame({"repeticion": r, "pliegue": f, L.ID: va, "Municipio": t.loc[va, "Municipio"].to_numpy(),
                             "municipio_visto": visto, "observado": y.loc[va].to_numpy()})
        for m, p in {**cong, **prop, **nuevas}.items():
            filas.append(base.assign(modelo=m, predicho=np.asarray(p, float)))
        print(f"rep {r} pliegue {f} ({time.time() - t0:.0f}s)", flush=True)
    oof = pd.concat(filas, ignore_index=True)
    assert np.isfinite(oof.predicho).all()
    oof.to_csv(SAL / "oof.csv", index=False, float_format="%.17g")
    s = oof[oof.municipio_visto]
    rep = s.groupby(["modelo", "repeticion"]).apply(lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")
    met = pd.DataFrame([{"modelo": m, **L.metricas(g.observado, g.predicho)} for m, g in s.groupby("modelo")]).set_index("modelo")
    met["reps_mejor_que_E_JK"] = [int((rep[m] < rep["E_JK"]).sum()) for m in met.index]
    met["reps_mejor_que_MIX"] = [int((rep[m] < rep["MIX"]).sum()) for m in met.index]
    met.to_csv(SAL / "metricas.csv", float_format="%.10g")
    zonas = s.assign(zona=np.where(s.Municipio.eq("Chignahuapan"), "Chignahuapan", "resto")).groupby(["zona", "modelo"]).apply(
        lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")
    zonas.to_csv(SAL / "rmse_zona.csv", float_format="%.10g")
    ahora = datetime.now(timezone.utc).isoformat()
    with open(R.AQUI / "intentos.csv", "a", newline="") as fh:
        w = csv.writer(fh)
        for m in [f"{h}_{b}" for h in hip for b in R.BASES]:
            w.writerow([m, "ejecutada", ahora, f"{met.loc[m, 'RMSE']:.6f}", f"{met.loc[m, 'MAE']:.6f}", met.loc[m, "reps_mejor_que_E_JK"],
                        met.loc[m, "reps_mejor_que_MIX"], "CV 10x5 semilla 20261021, 103 de desarrollo, SEEN"])
    pd.set_option("display.width", 200)
    print(met.sort_values("RMSE").round(5).to_string())
    print(zonas.round(4).T.to_string())


if __name__ == "__main__":
    main()
