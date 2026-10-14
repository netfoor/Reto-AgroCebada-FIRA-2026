"""Paso 1b: familias F6 y F7, añadidas y registradas en intentos.csv tras ver la CV de desarrollo.
Mismas particiones; solo etiquetas de desarrollo; los congelados se recalculan y se comprueba que coinciden."""

from __future__ import annotations

import csv
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_validacion as L

DEV = L.AQUI / "resultados_desarrollo"


def main():
    destino = DEV / "oof_desarrollo_adicional.csv"
    if destino.exists():
        raise SystemExit("Ya calculado")
    t0 = time.time()
    tx = L.tabla_x()
    t = tx.set_index(L.ID)
    y = L.etiquetas_desarrollo()
    ext = pd.read_csv(L.AQUI / "particiones_externas_desarrollo.csv")
    inn = pd.read_csv(L.AQUI / "particiones_internas_desarrollo.csv")
    previo = pd.read_csv(DEV / "oof_desarrollo.csv", float_precision="round_trip").set_index(["repeticion", "pliegue", L.ID, "modelo"]).predicho
    filas, max_dif = [], 0.0
    for (r, f), g in ext.groupby(["repeticion", "pliegue"], sort=True):
        tr = g.loc[g.rol.eq("entrenamiento"), L.ID].to_numpy()
        va = g.loc[g.rol.eq("validacion"), L.ID].to_numpy()
        fold_int = inn[(inn.repeticion == r) & (inn.pliegue == f)][["pliegue_interno", "rol", L.ID]]
        cong = L.congelados(tx, y, tr, va, fold_int)
        for m in ["MIX", "K", "J", "E_JK"]:
            max_dif = max(max_dif, float(np.abs(cong[m] - previo.loc[[(r, f, i, m) for i in va]].to_numpy()).max()))
        f6 = L.regresion_kriging_jared(tx, y, tr, va, fold_int)
        f7 = 0.5 * f6 + 0.5 * cong["K"]
        visto = t.loc[va, "Municipio"].isin(set(t.loc[tr, "Municipio"])).to_numpy()
        base = pd.DataFrame({"repeticion": r, "pliegue": f, L.ID: va, "Municipio": t.loc[va, "Municipio"].to_numpy(),
                             "municipio_visto": visto, "observado": y.loc[va].to_numpy()})
        filas += [base.assign(modelo="F6", predicho=f6), base.assign(modelo="F7", predicho=f7)]
    assert max_dif < 1e-12, max_dif
    oof = pd.concat(filas, ignore_index=True)
    assert np.isfinite(oof.predicho).all()
    oof.to_csv(destino, index=False, float_format="%.17g")
    todo = pd.concat([pd.read_csv(DEV / "oof_desarrollo.csv", float_precision="round_trip"), oof], ignore_index=True)
    s = todo[todo.municipio_visto]
    rep = s.groupby(["modelo", "repeticion"]).apply(lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")
    ahora = datetime.now(timezone.utc).isoformat()
    with open(L.AQUI / "intentos.csv", "a", newline="") as fh:
        w = csv.writer(fh)
        for m in ["F6", "F7"]:
            gm = s[s.modelo.eq(m)]
            mm = L.metricas(gm.observado, gm.predicho)
            w.writerow([m, "ejecutada", ahora, f"{mm['RMSE']:.6f}", f"{mm['MAE']:.6f}", int((rep[m] < rep["E_JK"]).sum()),
                        int((rep[m] < rep["MIX"]).sum()), "CV desarrollo 10x5, SEEN"])
    met = pd.DataFrame([{"modelo": m, **L.metricas(g.observado, g.predicho)} for m, g in s.groupby("modelo")]).set_index("modelo")
    met["reps_mejor_que_E_JK"] = [(rep[m] < rep["E_JK"]).sum() for m in met.index]
    met["reps_mejor_que_MIX"] = [(rep[m] < rep["MIX"]).sum() for m in met.index]
    print(f"congelados coinciden con la corrida anterior: dif. máx. {max_dif:.1e}; {time.time() - t0:.0f}s")
    print(met.sort_values("RMSE").round(5).to_string())


if __name__ == "__main__":
    main()
