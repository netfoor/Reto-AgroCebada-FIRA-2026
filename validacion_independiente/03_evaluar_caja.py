"""Paso 3: evaluación ÚNICA en la caja cerrada.

Entrena cada procedimiento con las 103 parcelas de desarrollo y predice las 35 de la caja.
Se niega a correr dos veces.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_validacion as L

SALIDA = L.AQUI / "resultados_caja"
B = 5000


def main():
    if SALIDA.exists():
        raise SystemExit("La caja ya se abrió una vez: no se repite")
    cong = json.loads((L.AQUI / "congelado.json").read_text())
    if L.sha(L.AQUI / "03_evaluar_caja.py") != cong["hashes"]["evaluar_caja"] or L.sha(L.AQUI / "lib_validacion.py") != cong["hashes"]["lib_opus"]:
        raise SystemExit("El código cambió después de congelar")
    SALIDA.mkdir()
    apertura = datetime.now(timezone.utc).isoformat()
    tx = L.tabla_x()
    t = tx.set_index(L.ID)
    y_dev = L.etiquetas_desarrollo()
    caja = L.caja_registrada()
    dev = y_dev.index.to_numpy()
    internas = L.internas_unicas(dev, L.SEMILLA_CAJA_INTERNA)
    pred = L.congelados(tx, y_dev, dev, np.array(caja), internas)
    final, variante = cong["procedimiento_final"], cong["variante_declarada"]
    for fam in [final] + ([variante] if variante else []):
        if fam == "F4":
            m = L.ModeloMixto(**L.FAMILIAS["F2"]).fit(t.loc[dev].reset_index(), y_dev.to_numpy())
            pred["F4"] = (pred["J"] + pred["K"] + m.predict(t.loc[caja].reset_index())) / 3.0
        elif fam in ("F6", "F7"):
            pred["F6"] = L.regresion_kriging_jared(tx, y_dev, dev, np.array(caja), internas)
            pred["F7"] = 0.5 * pred["F6"] + 0.5 * pred["K"]
        else:
            m = L.ModeloMixto(**L.FAMILIAS[fam]).fit(t.loc[dev].reset_index(), y_dev.to_numpy())
            pred[fam] = m.predict(t.loc[caja].reset_index())
    # ---- a partir de aquí se leen las etiquetas de la caja (una sola vez)
    y = L.etiquetas_caja().loc[caja]
    modelos = ["MUN", "MIX", "J", "K", "E_JK", final] + ([variante] if variante else [])
    P = pd.DataFrame({m: pred[m] for m in modelos}, index=caja).assign(observado=y.to_numpy(), Municipio=t.loc[caja, "Municipio"].to_numpy(),
                                                                        celda=t.loc[caja, "celda"].to_numpy())
    P.to_csv(SALIDA / "predicciones_caja.csv", float_format="%.17g")
    met = pd.DataFrame({m: L.metricas(P.observado, P[m]) for m in modelos}).T
    zonas = pd.DataFrame({z: {m: L.metricas(g.observado, g[m])["RMSE"] for m in modelos}
                          for z, g in [("Chignahuapan", P[P.Municipio.eq("Chignahuapan")]), ("resto", P[~P.Municipio.eq("Chignahuapan")])]})
    # concentración y sensibilidad: quitar de la evaluación las 2 parcelas más favorables al final frente a cada referencia
    sens, conc = {}, {}
    for ref in ["E_JK", "MIX"]:
        d = ((P[ref] - P.observado) ** 2 - (P[final] - P.observado) ** 2).sort_values(ascending=False)  # positivo = favorece al final
        conc[ref] = d.round(6).to_dict()
        q = P.drop(index=d.index[:2])
        sens[ref] = {"parcelas_retiradas": list(d.index[:2]), "RMSE_final": L.metricas(q.observado, q[final])["RMSE"],
                     "RMSE_ref": L.metricas(q.observado, q[ref])["RMSE"]}
        sens[ref]["sigue_mejor"] = bool(sens[ref]["RMSE_final"] < sens[ref]["RMSE_ref"])
    # bootstrap por conglomerados (celdas) de la diferencia de MSE en la caja (secundario, informativo)
    rng = np.random.default_rng(L.SEMILLA_BOOT + 100)
    unicos = P.celda.unique()
    boot = {}
    for ref in ["E_JK", "MIX"]:
        dd = ((P[ref] - P.observado) ** 2 - (P[final] - P.observado) ** 2).to_numpy()
        idx = {c: np.flatnonzero(P.celda.to_numpy() == c) for c in unicos}
        bs = np.array([dd[np.concatenate([idx[c] for c in rng.choice(unicos, len(unicos))])].mean() for _ in range(B)])
        boot[ref] = {"delta_mse_observado": float(dd.mean()), "ic90": [float(np.quantile(bs, 0.05)), float(np.quantile(bs, 0.95))],
                     "fraccion_bootstrap_sin_mejora": float((bs <= 0).mean())}
    c1 = bool(met.loc[final, "RMSE"] < met.loc["E_JK", "RMSE"] and met.loc[final, "RMSE"] < met.loc["MIX", "RMSE"])
    c3 = bool(met.loc[final, "MAE"] <= met.loc["MIX", "MAE"])
    c4 = bool(sens["E_JK"]["sigue_mejor"] and sens["MIX"]["sigue_mejor"])
    c2, c5 = cong["condicion_2_desarrollo"]["cumple"], cong["condicion_5_nulo"]["cumple"]
    if c1 and c2 and c3 and c4 and c5:
        decision = "FAVORABLE"
    elif met.loc[final, "RMSE"] < met.loc["MIX", "RMSE"]:
        # Regla del equipo: supera a MIX pero no a E_JK → PARCIAL. Hueco no definido por el equipo, fijado en el
        # registro previo: si supera a MIX y a E_JK en la caja pero falla otra condición, también PARCIAL.
        decision = "PARCIAL"
    else:
        decision = "NO FAVORABLE"
    out = {"apertura_caja_utc": apertura, "procedimiento_final": final, "variante": variante,
           "metricas_caja": met.to_dict(orient="index"), "rmse_por_zona": zonas.to_dict(orient="index"),
           "sensibilidad_sin_2": sens, "bootstrap_caja": boot,
           "condiciones": {"C1_caja_RMSE_menor_que_E_JK_y_MIX": c1, "C2_desarrollo_8de10": c2, "C3_caja_MAE_no_peor_que_MIX": c3,
                           "C4_no_se_invierte_sin_2": c4, "C5_nulo_p_le_0.10": c5},
           "decision": decision, "concentracion": conc}
    (SALIDA / "resultado_caja.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    pd.set_option("display.width", 200)
    print(met.round(5).to_string())
    print(zonas.round(4).to_string())
    print(json.dumps({k: out[k] for k in ["condiciones", "decision", "sensibilidad_sin_2", "bootstrap_caja"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
