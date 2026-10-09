"""Verificación independiente de EXP_11: métricas con numpy puro desde los componentes, réplica byte a byte,
originales y registro previo intactos.

    uv run --locked --all-groups python scripts/verificar_exp_11_resultados.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados/exp_11_combinacion_modelos"
N11 = RAIZ / "notebooks/experimentos/exp_11_combinacion_modelos"


def h(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    # Implementación sin pandas: diccionarios por clave
    pred, obs, vis = defaultdict(dict), {}, {}
    with open(RAIZ / "data/exp_11_combinacion_modelos/oof_componentes.csv", newline="") as f:
        for r in csv.DictReader(f):
            k = (r["conjunto"], r["repeticion"], r["pliegue"], r["ID_POLIGONO"])
            pred[k][r["modelo"]] = float(r["predicho"])
            obs[k] = float(r["observado"])
            vis[k] = r["municipio_visto"] == "True"
    formulas = {"E_JK": ("J", "K"), "E_MK": ("MUN", "K")}
    calc = {}
    for cj in ("historicas", "nuevas"):
        for esc in ("SEEN135", "FULL138"):
            ks = [k for k in pred if k[0] == cj and (vis[k] or esc == "FULL138")]
            for m in ["MIX", "MUN", "J", "K", "E_JK", "E_MK"]:
                e = [((pred[k][formulas[m][0]] + pred[k][formulas[m][1]]) / 2 if m in formulas else pred[k][m]) - obs[k] for k in ks]
                calc[(cj, esc, m)] = (math.sqrt(sum(x * x for x in e) / len(e)), sum(abs(x) for x in e) / len(e), len(e))
    dif = 0.0
    with open(RES / "registrada/metricas.csv", newline="") as f:
        for r in csv.DictReader(f):
            c = calc[(r["conjunto"], r["escenario"], r["modelo"])]
            dif = max(dif, abs(c[0] - float(r["RMSE"])), abs(c[1] - float(r["MAE"])))
            assert c[2] == int(r["n_oof"])
    iguales, distintos = [], []
    for p in sorted((RES / "registrada").iterdir()):
        if p.name != "registro_ejecucion.json":
            (iguales if (RES / "replica_determinismo" / p.name).read_bytes() == p.read_bytes() else distintos).append(p.name)
    pre = json.loads((N11 / "registro_previo.json").read_text())
    cambiados_registro = [a for a, v in pre["archivos"].items() if h(RAIZ / a) != v["sha256"]]
    cambiados_originales = [a for a, v in pre["originales_a_preservar"].items() if h(RAIZ / a) != v]
    reg = json.loads((RES / "registrada/registro_ejecucion.json").read_text())
    out = {"verificado_utc": datetime.now(timezone.utc).isoformat(), "implementacion_independiente": "csv+math, sin pandas ni combinacion_11",
           "max_dif_metricas": dif, "metricas_reproducidas": dif < 1e-12,
           "replica_archivos_identicos": iguales, "replica_archivos_distintos": distintos, "replica_determinista": bool(iguales) and not distintos,
           "registro_previo_anterior_a_corrida": pre["registrado_utc"] < reg["inicio_utc"],
           "archivos_registrados_cambiados": cambiados_registro, "originales_cambiados": cambiados_originales}
    (N11 / "verificacion_independiente.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if not (out["metricas_reproducidas"] and out["replica_determinista"] and out["registro_previo_anterior_a_corrida"]
            and not cambiados_registro and not cambiados_originales):
        raise SystemExit("Verificación fallida")


if __name__ == "__main__":
    main()
