"""Ronda 2, paso 3: Reality Check (White, 2000) frente a E_JK con las 7 familias de la ronda 1 y las nuevas, y congelación.
Se ejecuta ANTES del segundo uso de la caja."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import lib_r2 as R

L = R.L
SAL = R.AQUI / "resultados_cv"
spec = importlib.util.spec_from_file_location("nulo_r1", R.AQUI.parent / "02_nulo_y_congelar.py")
N1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N1)          # reutiliza perdidas() y reality_check() de la ronda 1, sin modificarlas


def main():
    if (R.AQUI / "congelado.json").exists():
        raise SystemExit("congelado.json ya existe")
    oof = pd.read_csv(SAL / "oof.csv", float_precision="round_trip")
    met = pd.read_csv(SAL / "metricas.csv", index_col=0)
    nuevas = sorted(m for m in met.index if m.startswith("H"))
    familias = [f"F{i}" for i in range(1, 8)] + nuevas
    Lp = N1.perdidas(oof)
    celdas = L.tabla_x().set_index(L.ID).celda
    rc = {b: N1.reality_check(Lp, b, familias, celdas, R.SEMILLA_CV2 + 7 + i) for i, b in enumerate(["E_JK", "MIX"])}
    final = met.loc[nuevas, "RMSE"].idxmin()
    h, base = final.split("_", 1)
    variante = f"{h}_{'MIX' if base == 'E_JK' else 'E_JK'}"
    if variante not in met.index:
        variante = None
    c = {"congelado_utc": datetime.now(timezone.utc).isoformat(), "procedimiento_final": final, "variante_declarada": variante,
         "regla": "corrección nueva con menor RMSE SEEN en la CV de la ronda 2; variante = misma hipótesis sobre la otra base",
         "metricas_cv": met.loc[[*nuevas, "E_JK", "MIX", "K", "J", "MUN", "F7"]].to_dict(orient="index"),
         "reality_check": rc,
         "condicion_2_cv": {"reps_vs_E_JK": int(met.loc[final, "reps_mejor_que_E_JK"]), "reps_vs_MIX": int(met.loc[final, "reps_mejor_que_MIX"]),
                            "cumple": bool(met.loc[final, "reps_mejor_que_E_JK"] >= 8 and met.loc[final, "reps_mejor_que_MIX"] >= 8)},
         "condicion_5_nulo": {"p_vs_E_JK": rc["E_JK"]["p_valor"], "cumple": bool(rc["E_JK"]["p_valor"] <= 0.10)},
         "hashes": {"registro_previo": L.sha(R.AQUI / "registro_previo.json"), "lib_r2": L.sha(R.AQUI / "lib_r2.py"),
                    "lib_validacion": L.sha(R.AQUI.parent / "lib_validacion.py"), "caja_script": L.sha(R.AQUI / "04_caja.py"), "oof": L.sha(SAL / "oof.csv")},
         "caja_segundo_uso_abierto": False}
    (R.AQUI / "congelado.json").write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in c.items() if k != "metricas_cv"}, indent=2, ensure_ascii=False))
    _ = np


if __name__ == "__main__":
    main()
