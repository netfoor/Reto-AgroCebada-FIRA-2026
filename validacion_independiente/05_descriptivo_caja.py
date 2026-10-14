"""Paso 5 (descriptivo POSTERIOR a abrir la caja; no decide nada ni reentrena):
incertidumbre de las diferencias entre los candidatos congelados en la caja y concentración por parcela.
Usa solo resultados_caja/predicciones_caja.csv."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib_validacion as L

B = 5000


def main():
    P = pd.read_csv(L.AQUI / "resultados_caja/predicciones_caja.csv", index_col=0, float_precision="round_trip")
    mods = ["MUN", "MIX", "J", "K", "E_JK", "F7"]
    se = {m: (P[m] - P.observado) ** 2 for m in mods}
    rng = np.random.default_rng(L.SEMILLA_BOOT + 200)
    celdas = P.celda.to_numpy()
    unicos = np.unique(celdas)
    idx = {c: np.flatnonzero(celdas == c) for c in unicos}
    muestras = [np.concatenate([idx[c] for c in rng.choice(unicos, len(unicos))]) for _ in range(B)]
    filas = []
    for a in mods:
        for b in mods:
            if a >= b:
                continue
            d = (se[a] - se[b]).to_numpy()                 # positivo: a tiene más error que b
            bs = np.array([np.sqrt(se[a].to_numpy()[s].mean()) - np.sqrt(se[b].to_numpy()[s].mean()) for s in muestras])
            filas.append({"a": a, "b": b, "dRMSE_a_menos_b": float(np.sqrt(se[a].mean()) - np.sqrt(se[b].mean())),
                          "ic90_inf": float(np.quantile(bs, 0.05)), "ic90_sup": float(np.quantile(bs, 0.95)),
                          "parcelas_a_mejor": int((d < 0).sum()), "parcelas_b_mejor": int((d > 0).sum())})
    pares = pd.DataFrame(filas)
    pares.to_csv(L.AQUI / "resultados_caja/pares_bootstrap_descriptivo.csv", index=False, float_format="%.6g")
    conc = {}
    for ref in ["MIX", "E_JK", "MUN"]:
        d = (se[ref] - se["K"]).sort_values(ascending=False)  # positivo: favorece a K
        q = P.drop(index=d.index[:2])
        conc[f"K_vs_{ref}"] = {"mas_favorecidas": list(d.index[:3]), "dRMSE_completo": float(np.sqrt(se["K"].mean()) - np.sqrt(se[ref].mean())),
                               "dRMSE_sin_2": float(np.sqrt(((q["K"] - q.observado) ** 2).mean()) - np.sqrt(((q[ref] - q.observado) ** 2).mean())),
                               "parcelas_K_mejor": int((d > 0).sum()), "parcelas_K_peor": int((d < 0).sum())}
    (L.AQUI / "resultados_caja/concentracion_K_descriptivo.json").write_text(json.dumps(conc, indent=2, ensure_ascii=False) + "\n")
    pd.set_option("display.width", 200)
    print(pares.round(4).to_string(index=False))
    print(json.dumps(conc, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
