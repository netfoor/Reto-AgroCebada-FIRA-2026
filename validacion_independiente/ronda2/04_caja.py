"""Ronda 2, paso 4: SEGUNDO uso de la caja cerrada de la ronda 1 (declarado, menos limpio). Se ejecuta una sola vez."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_r2 as R

L = R.L
SAL = R.AQUI / "resultados_caja"


def main():
    if SAL.exists():
        raise SystemExit("Segundo uso ya realizado")
    c = json.loads((R.AQUI / "congelado.json").read_text())
    if L.sha(R.AQUI / "04_caja.py") != c["hashes"]["caja_script"] or L.sha(R.AQUI / "lib_r2.py") != c["hashes"]["lib_r2"]:
        raise SystemExit("El código cambió después de congelar")
    SAL.mkdir()
    apertura = datetime.now(timezone.utc).isoformat()
    tx = L.tabla_x()
    t = tx.set_index(L.ID)
    vx = pd.read_csv(R.AQUI / "variables_externas.csv").set_index(L.ID)
    y_dev = L.etiquetas_desarrollo()
    dev = y_dev.index.to_numpy()
    caja = np.array(L.caja_registrada())
    internas = L.internas_unicas(dev, L.SEMILLA_CAJA_INTERNA)              # las mismas de la ronda 1
    cong, e = R.bases_y_residuos(tx, y_dev, dev, caja, internas, R.SEMILLA_CAJA2)
    pred = dict(cong)
    for m in [c["procedimiento_final"]] + ([c["variante_declarada"]] if c["variante_declarada"] else []):
        h, b = m.split("_", 1)
        pred[m], _ = R.corregir(cong[b], e[b], vx[R.HIPOTESIS[h]], caja)
    # --- etiquetas de la caja
    y = L.etiquetas_caja().loc[caja]
    prev = pd.read_csv(R.AQUI.parent / "resultados_caja/predicciones_caja.csv", index_col=0, float_precision="round_trip")
    dif_r1 = max(float(np.abs(pred[m] - prev.loc[caja, m].to_numpy()).max()) for m in ["MUN", "MIX", "J", "K", "E_JK"])
    final, variante = c["procedimiento_final"], c["variante_declarada"]
    modelos = ["MUN", "MIX", "J", "K", "E_JK", final] + ([variante] if variante else [])
    P = pd.DataFrame({m: pred[m] for m in modelos}, index=caja).assign(observado=y.to_numpy(), Municipio=t.loc[caja, "Municipio"].to_numpy())
    P.to_csv(SAL / "predicciones_caja.csv", float_format="%.17g")
    met = pd.DataFrame({m: L.metricas(P.observado, P[m]) for m in modelos}).T
    zonas = pd.DataFrame({z: {m: L.metricas(g.observado, g[m])["RMSE"] for m in modelos}
                          for z, g in [("Chignahuapan", P[P.Municipio.eq("Chignahuapan")]), ("resto", P[~P.Municipio.eq("Chignahuapan")])]})
    sens = {}
    for ref in ["E_JK", "MIX"]:
        d = ((P[ref] - P.observado) ** 2 - (P[final] - P.observado) ** 2).sort_values(ascending=False)
        q = P.drop(index=d.index[:2])
        sens[ref] = {"retiradas": list(d.index[:2]), "RMSE_final": L.metricas(q.observado, q[final])["RMSE"], "RMSE_ref": L.metricas(q.observado, q[ref])["RMSE"]}
        sens[ref]["sigue_mejor"] = bool(sens[ref]["RMSE_final"] < sens[ref]["RMSE_ref"])
    c1 = bool(met.loc[final, "RMSE"] < met.loc["E_JK", "RMSE"] and met.loc[final, "RMSE"] < met.loc["MIX", "RMSE"])
    c3 = bool(met.loc[final, "MAE"] <= met.loc["MIX", "MAE"])
    c4 = bool(sens["E_JK"]["sigue_mejor"] and sens["MIX"]["sigue_mejor"])
    c2, c5 = c["condicion_2_cv"]["cumple"], c["condicion_5_nulo"]["cumple"]
    decision = "FAVORABLE" if (c1 and c2 and c3 and c4 and c5) else ("PARCIAL" if met.loc[final, "RMSE"] < met.loc["MIX", "RMSE"] else "NO FAVORABLE")
    out = {"apertura_utc": apertura, "uso_de_la_caja": "segundo (declarado, menos limpio)", "final": final, "variante": variante,
           "congelados_identicos_a_ronda1_dif_max": dif_r1, "metricas_caja": met.to_dict(orient="index"), "rmse_zona": zonas.to_dict(orient="index"),
           "sensibilidad_sin_2": sens, "condiciones": {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5}, "decision": decision}
    (SAL / "resultado.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    pd.set_option("display.width", 200)
    print(met.round(5).to_string())
    print(zonas.round(4).to_string())
    print(json.dumps({k: out[k] for k in ["congelados_identicos_a_ronda1_dif_max", "sensibilidad_sin_2", "condiciones", "decision"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
