"""Paso 1: validación cruzada repetida y anidada SOLO con las parcelas de desarrollo.

Evalúa los candidatos congelados (MUN, MIX, J, K, E_JK) y las familias propias F1–F5 sobre las mismas
particiones nuevas (semilla 20261012). Las etiquetas de la caja nunca se leen aquí.
"""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_validacion as L

SALIDA = L.AQUI / "resultados_desarrollo"
MODELOS = ["MUN", "MIX", "J", "K", "E_JK", "F1", "F2", "F3", "F4", "F5"]
PROPIAS = ["F1", "F2", "F3", "F4", "F5"]


def main():
    if SALIDA.exists():
        raise SystemExit("resultados_desarrollo/ ya existe: no se repite la corrida")
    SALIDA.mkdir()
    t0 = time.time()
    tx = L.tabla_x()
    y = L.etiquetas_desarrollo()
    ext, inn = L.particiones_desarrollo(y.index)
    reg = json.loads((L.AQUI / "registro_previo.json").read_text())
    for nombre, df in [("externas", ext), ("internas", inn)]:
        ruta = L.AQUI / f"particiones_{nombre}_desarrollo.csv"
        assert L.sha(ruta) == reg["particiones_desarrollo"][nombre]["sha256"]
        assert df.equals(pd.read_csv(ruta))
    t = tx.set_index(L.ID)
    filas, varz = [], []
    for (r, f), g in ext.groupby(["repeticion", "pliegue"], sort=True):
        tr = g.loc[g.rol.eq("entrenamiento"), L.ID].to_numpy()
        va = g.loc[g.rol.eq("validacion"), L.ID].to_numpy()
        fold_int = inn[(inn.repeticion == r) & (inn.pliegue == f)][["pliegue_interno", "rol", L.ID]]
        cong = L.congelados(tx, y, tr, va, fold_int)
        prop, info = L.familias_propias(tx, y, tr, va, cong)
        visto = t.loc[va, "Municipio"].isin(set(t.loc[tr, "Municipio"])).to_numpy()
        base = pd.DataFrame({"repeticion": r, "pliegue": f, L.ID: va, "Municipio": t.loc[va, "Municipio"].to_numpy(),
                             "municipio_visto": visto, "observado": y.loc[va].to_numpy()})
        for m in MODELOS:
            filas.append(base.assign(modelo=m, predicho=np.asarray(({**cong, **prop})[m], float)))
        for fam, d in info.items():
            varz.append({"repeticion": r, "pliegue": f, "familia": fam, **d})
        print(f"rep {r} pliegue {f} listo ({time.time() - t0:.0f}s)", flush=True)
    oof = pd.concat(filas, ignore_index=True)
    assert np.isfinite(oof.predicho).all() and not oof.duplicated(["repeticion", "pliegue", L.ID, "modelo"]).any()
    oof.to_csv(SALIDA / "oof_desarrollo.csv", index=False, float_format="%.17g")
    pd.DataFrame(varz).to_csv(SALIDA / "varianzas_reml.csv", index=False, float_format="%.10g")
    s = oof[oof.municipio_visto]
    met = pd.DataFrame([{"modelo": m, **L.metricas(g.observado, g.predicho)} for m, g in s.groupby("modelo")]).set_index("modelo").reindex(MODELOS)
    rep = s.groupby(["modelo", "repeticion"]).apply(lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")
    met["reps_mejor_que_E_JK"] = [(rep[m] < rep["E_JK"]).sum() for m in MODELOS]
    met["reps_mejor_que_MIX"] = [(rep[m] < rep["MIX"]).sum() for m in MODELOS]
    met.to_csv(SALIDA / "metricas_desarrollo.csv", float_format="%.10g")
    rep.to_csv(SALIDA / "rmse_por_repeticion.csv", float_format="%.10g")
    zonas = s.assign(zona=np.where(s.Municipio.eq("Chignahuapan"), "Chignahuapan", "resto")).groupby(["zona", "modelo"]).apply(
        lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")[MODELOS]
    zonas.to_csv(SALIDA / "rmse_por_zona.csv", float_format="%.10g")
    ahora = datetime.now(timezone.utc).isoformat()
    with open(L.AQUI / "intentos.csv", "a", newline="") as fh:
        w = csv.writer(fh)
        for m in PROPIAS:
            w.writerow([m, "ejecutada", ahora, f"{met.loc[m, 'RMSE']:.6f}", f"{met.loc[m, 'MAE']:.6f}",
                        int(met.loc[m, "reps_mejor_que_E_JK"]), int(met.loc[m, "reps_mejor_que_MIX"]), "CV desarrollo 10x5, SEEN"])
    (SALIDA / "registro_ejecucion.json").write_text(json.dumps({
        "inicio_fin_utc": ahora, "segundos": round(time.time() - t0, 1), "parcelas_desarrollo": int(len(y)),
        "filas_oof": int(len(oof)), "filas_seen_por_modelo": int(len(s) / len(MODELOS)),
        "lib_sha256": L.sha(L.AQUI / "lib_validacion.py"), "script_sha256": L.sha(__file__),
        "caja_leida": False}, indent=2) + "\n")
    pd.set_option("display.width", 200)
    print(met.round(5).to_string())
    print(zonas.round(4).to_string())


if __name__ == "__main__":
    main()
