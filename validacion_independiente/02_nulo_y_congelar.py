"""Paso 2: nulo que descuenta todo el registro de intentos (White, 2000) y congelación del procedimiento final.

Se ejecuta ANTES de abrir la caja. Solo usa las predicciones OOF de desarrollo.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_validacion as L

DEV = L.AQUI / "resultados_desarrollo"
B = 5000


def perdidas(oof: pd.DataFrame) -> pd.DataFrame:
    """Pérdida por parcela = media del error cuadrático en sus filas SEEN (una por repetición)."""
    s = oof[oof.municipio_visto].assign(se=lambda d: (d.predicho - d.observado) ** 2)
    return s.pivot_table(index=L.ID, columns="modelo", values="se", aggfunc="mean")


def reality_check(Lp: pd.DataFrame, bench: str, modelos: list[str], clusters: pd.Series, semilla: int) -> dict:
    """H0: ninguno de los modelos probados supera al benchmark en pérdida esperada.
    d_ki = L_bench,i − L_k,i;  T = max_k √n·mean(d_k);  bootstrap por conglomerados (celdas CHIRPS), recentrado."""
    d = pd.DataFrame({m: Lp[bench] - Lp[m] for m in modelos})
    n = len(d)
    T_k = np.sqrt(n) * d.mean().to_numpy()
    T = float(T_k.max())
    cl = clusters.reindex(d.index).to_numpy()
    unicos = np.unique(cl)
    idx_por = {c: np.flatnonzero(cl == c) for c in unicos}
    centro = d.mean().to_numpy()
    D = d.to_numpy()
    rng = np.random.default_rng(semilla)
    Tb = np.empty(B)
    for b in range(B):
        sel = np.concatenate([idx_por[c] for c in rng.choice(unicos, size=len(unicos), replace=True)])
        Tb[b] = (np.sqrt(len(sel)) * (D[sel].mean(0) - centro)).max()
    return {"benchmark": bench, "modelos": modelos, "n_parcelas": n, "conglomerados": int(len(unicos)),
            "T_por_modelo": dict(zip(modelos, map(float, T_k))), "T_max": T,
            "delta_mse_por_modelo": dict(zip(modelos, map(float, centro))),
            "p_valor": float((1 + (Tb >= T).sum()) / (B + 1)), "B": B, "semilla": semilla}


def main():
    if (L.AQUI / "congelado.json").exists():
        raise SystemExit("congelado.json ya existe")
    oof = pd.concat([pd.read_csv(DEV / n, float_precision="round_trip") for n in ["oof_desarrollo.csv", "oof_desarrollo_adicional.csv"]],
                    ignore_index=True)
    intentos = pd.read_csv(L.AQUI / "intentos.csv")
    probados = sorted(intentos.loc[intentos.evento.eq("ejecutada"), "familia"].unique())
    Lp = perdidas(oof)
    celdas = L.tabla_x().set_index(L.ID).celda
    rc = {b: reality_check(Lp, b, probados, celdas, L.SEMILLA_BOOT + i) for i, b in enumerate(["E_JK", "MIX"])}
    s = oof[oof.municipio_visto]
    rep = s.groupby(["modelo", "repeticion"]).apply(lambda g: np.sqrt(((g.predicho - g.observado) ** 2).mean()), include_groups=False).unstack("modelo")
    met = pd.DataFrame([{"modelo": m, **L.metricas(g.observado, g.predicho)} for m, g in s.groupby("modelo")]).set_index("modelo")
    met["reps_mejor_que_E_JK"] = [int((rep[m] < rep["E_JK"]).sum()) for m in met.index]
    met["reps_mejor_que_MIX"] = [int((rep[m] < rep["MIX"]).sum()) for m in met.index]
    met.to_csv(DEV / "metricas_desarrollo_todas.csv", float_format="%.10g")
    final = met.loc[probados, "RMSE"].idxmin()
    variante = "F2" if final == "F5" else None                      # regla declarada en el registro previo
    congelado = {
        "congelado_utc": datetime.now(timezone.utc).isoformat(),
        "procedimiento_final": final, "receta_final": L.FAMILIAS.get(final, "⅓·(J + K + F2)"),
        "variante_declarada": variante,
        "regla_de_seleccion": "familia propia con menor RMSE agrupado SEEN en la CV de desarrollo",
        "metricas_desarrollo": met.loc[[*probados, "E_JK", "MIX", "J", "K", "MUN"]].to_dict(orient="index"),
        "reality_check": rc,
        "condicion_2_desarrollo": {
            "reps_final_mejor_que_E_JK": int(met.loc[final, "reps_mejor_que_E_JK"]),
            "reps_final_mejor_que_MIX": int(met.loc[final, "reps_mejor_que_MIX"]),
            "cumple": bool(met.loc[final, "reps_mejor_que_E_JK"] >= 8 and met.loc[final, "reps_mejor_que_MIX"] >= 8)},
        "condicion_5_nulo": {"p_reality_check_vs_E_JK": rc["E_JK"]["p_valor"], "cumple": bool(rc["E_JK"]["p_valor"] <= 0.10)},
        "hashes": {"registro_previo": L.sha(L.AQUI / "registro_previo.json"), "lib_validacion": L.sha(L.AQUI / "lib_validacion.py"),
                   "oof_desarrollo": L.sha(DEV / "oof_desarrollo.csv"), "oof_desarrollo_adicional": L.sha(DEV / "oof_desarrollo_adicional.csv"),
                   "intentos": L.sha(L.AQUI / "intentos.csv"),
                   "evaluar_caja": L.sha(L.AQUI / "03_evaluar_caja.py")},
        "caja_abierta": False,
    }
    (L.AQUI / "congelado.json").write_text(json.dumps(congelado, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in congelado.items() if k != "metricas_desarrollo"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
