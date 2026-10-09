"""EXP_11: dos mezclas fijas 50/50 sobre predicciones OOF existentes. Cero entrenamientos.

    uv run --locked --all-groups python scripts/experimento_11.py --salida resultados/exp_11_combinacion_modelos/registrada
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from combinacion_11 import (CLAVE, ID, MEZCLAS, agregar_mezclas, ancho, clasificar, contribuciones, metricas,
                            sensibilidad, validar_componentes, validar_particiones)

RAIZ = Path(__file__).resolve().parents[1]
D11 = RAIZ / "data/exp_11_combinacion_modelos"
PART = {"historicas": "data/validacion_03/particiones_externas.csv", "nuevas": "data/exp_09_fuentes_externas/particiones_externas_nuevas.csv"}
MODELOS = ["MIX", "MUN", "J", "K", "E_JK", "E_MK"]
CONJUNTOS = ["historicas", "nuevas"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def escenarios(w):
    for cj in CONJUNTOS:
        base = w[w.conjunto == cj]
        yield cj, "SEEN135", base[base.municipio_visto]
        yield cj, "FULL138", base


def rmse_rep(o, m):
    return o.groupby("repeticion").apply(lambda g: metricas(g.observado, g[m])["RMSE"], include_groups=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    args = ap.parse_args()
    sal = args.salida if args.salida.is_absolute() else RAIZ / args.salida
    if sal.exists() and any(sal.iterdir()):
        raise ValueError("Salida existente: no se sobrescribe")
    sal.mkdir(parents=True, exist_ok=True)
    inicio = datetime.now(timezone.utc).isoformat()
    comp = pd.read_csv(D11 / "oof_componentes.csv")
    validar_componentes(comp)
    validar_particiones(comp, {cj: pd.read_csv(RAIZ / p) for cj, p in PART.items()})
    w = agregar_mezclas(ancho(comp))
    for n, (a, b) in MEZCLAS.items():
        if not ((w[n] >= np.minimum(w[a], w[b]) - 1e-12) & (w[n] <= np.maximum(w[a], w[b]) + 1e-12)).all():
            raise ValueError("Mezcla fuera del intervalo de sus componentes")
    largo = w.melt(id_vars=CLAVE + ["Municipio", "municipio_visto", "observado"], value_vars=list(MEZCLAS), var_name="modelo", value_name="predicho")
    met, rep, pares, zonas, munis, corr, conc, sens, sing = [], [], [], [], [], [], [], [], []
    for cj, esc, o in escenarios(w):
        for m in MODELOS:
            met.append({"conjunto": cj, "escenario": esc, "modelo": m, "n_parcelas": o[ID].nunique(), **metricas(o.observado, o[m])})
            for r, g in o.groupby("repeticion"):
                rep.append({"conjunto": cj, "escenario": esc, "modelo": m, "repeticion": int(r), **metricas(g.observado, g[m])})
        for c in MEZCLAS:
            for ref in ["MIX", "MUN", "J", "K"] + (["E_MK"] if c == "E_JK" else []):
                dr = rmse_rep(o, c) - rmse_rep(o, ref)
                pares.append({"conjunto": cj, "escenario": esc, "candidato": c, "referencia": ref,
                              "delta_RMSE": metricas(o.observado, o[c])["RMSE"] - metricas(o.observado, o[ref])["RMSE"],
                              "delta_MAE": metricas(o.observado, o[c])["MAE"] - metricas(o.observado, o[ref])["MAE"],
                              "reps_mejora_RMSE": int((dr < 0).sum()), "delta_rep_min": float(dr.min()), "delta_rep_max": float(dr.max()), "delta_rep_media": float(dr.mean())})
        if esc == "FULL138":
            u = o[~o.municipio_visto]
            for m in MODELOS:
                sing.append({"conjunto": cj, "modelo": m, "parcelas": ";".join(sorted(u[ID].unique())), **metricas(u.observado, u[m])})
            continue
        for zona, g in [("Chignahuapan", o[o.Municipio.eq("Chignahuapan")]), ("resto", o[~o.Municipio.eq("Chignahuapan")])]:
            for m in MODELOS:
                zonas.append({"conjunto": cj, "zona": zona, "modelo": m, "n_parcelas": g[ID].nunique(), **metricas(g.observado, g[m])})
        for mu, g in o.groupby("Municipio"):
            for m in MODELOS:
                munis.append({"conjunto": cj, "Municipio": mu, "modelo": m, "n_parcelas": g[ID].nunique(), "muestra_pequena": g[ID].nunique() < 10, **metricas(g.observado, g[m])})
        e = {m: o[m] - o.observado for m in MODELOS}
        corr += [{"conjunto": cj, "tipo": "errores", "par": "J vs K", "pearson": float(np.corrcoef(e["J"], e["K"])[0, 1])},
                 {"conjunto": cj, "tipo": "errores", "par": "MUN vs K", "pearson": float(np.corrcoef(e["MUN"], e["K"])[0, 1])},
                 {"conjunto": cj, "tipo": "cambios_vs_MIX", "par": "J−MIX vs K−MIX", "pearson": float(np.corrcoef(o.J - o.MIX, o.K - o.MIX)[0, 1])},
                 {"conjunto": cj, "tipo": "cambios_vs_MIX", "par": "MUN−MIX vs K−MIX", "pearson": float(np.corrcoef(o.MUN - o.MIX, o.K - o.MIX)[0, 1])}]
        rm = {m: metricas(o.observado, o[m])["RMSE"] for m in MODELOS}
        for c, (a, b) in MEZCLAS.items():
            mejor = a if rm[a] <= rm[b] else b
            for ref in ["MIX", mejor]:
                d = contribuciones(o, c, ref)
                conc += [{"conjunto": cj, "candidato": c, "referencia": ref, "orden": i + 1, ID: pid, "delta_sse_10reps": float(v)} for i, (pid, v) in enumerate(d.items())]
                for k in (0, 2, 5):
                    sens.append({"conjunto": cj, "candidato": c, "referencia": ref, "es_mejor_componente": ref == mejor, **sensibilidad(o, c, ref, k)})
    met, rep, pares, sens = pd.DataFrame(met), pd.DataFrame(rep), pd.DataFrame(pares), pd.DataFrame(sens)
    lectura = []
    for c, (a, b) in MEZCLAS.items():
        s = met[met.escenario.eq("SEEN135")].set_index(["conjunto", "modelo"]).RMSE
        rmse = {(cj, m): float(s[(cj, m)]) for cj in CONJUNTOS for m in (a, b, c)}
        p = pares[pares.escenario.eq("SEEN135")].set_index(["conjunto", "candidato", "referencia"])
        reps_vs = {(cj, m): int(p.loc[(cj, c, m), "reps_mejora_RMSE"]) for cj in CONJUNTOS for m in (a, b)}
        s2 = {cj: float(sens[(sens.conjunto == cj) & (sens.candidato == c) & sens.es_mejor_componente & (sens.retiradas == 2)].delta_RMSE.iloc[0]) for cj in CONJUNTOS}
        clase = clasificar(rmse, reps_vs, s2, (a, b))
        lectura.append({"mezcla": c, "componentes": f"{a}+{b}", "clase": clase,
                        **{f"supera_mejor_componente_{cj}": rmse[(cj, c)] < min(rmse[(cj, a)], rmse[(cj, b)]) for cj in CONJUNTOS},
                        **{f"reps_vs_{m}_{cj}": reps_vs[(cj, m)] for cj in CONJUNTOS for m in (a, b)},
                        **{f"sens2_vs_mejor_{cj}": s2[cj] for cj in CONJUNTOS}})
    pjk = pares[pares.escenario.eq("SEEN135") & pares.candidato.eq("E_JK") & pares.referencia.eq("E_MK")].set_index("conjunto")
    aporte_J = bool(all(pjk.loc[cj, "delta_RMSE"] < 0 and pjk.loc[cj, "reps_mejora_RMSE"] >= 8 for cj in CONJUNTOS))
    lectura = pd.DataFrame(lectura)
    salidas = {"predicciones_mezclas.csv": largo, "metricas.csv": met, "repeticiones.csv": rep, "pares.csv": pares,
               "zonas.csv": pd.DataFrame(zonas), "municipios.csv": pd.DataFrame(munis), "correlaciones.csv": pd.DataFrame(corr),
               "concentracion_parcelas.csv": pd.DataFrame(conc), "sensibilidades.csv": sens, "full138_municipios_no_vistos.csv": pd.DataFrame(sing),
               "lectura.csv": lectura}
    for n, df in salidas.items():
        df.to_csv(sal / n, index=False, float_format="%.17g")
    reg = {"id": "EXP_11", "inicio_utc": inicio, "fin_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
           "insumos_sha256": {str(p.relative_to(RAIZ)): sha(p) for p in [D11 / "oof_componentes.csv", D11 / "verificacion_insumos.json",
                              RAIZ / PART["historicas"], RAIZ / PART["nuevas"], RAIZ / "scripts/combinacion_11.py", RAIZ / "scripts/experimento_11.py",
                              RAIZ / "notebooks/experimentos/exp_11_combinacion_modelos/protocolo.md",
                              RAIZ / "notebooks/experimentos/exp_11_combinacion_modelos/registro_previo.json"]},
           "salidas_sha256": {n: sha(sal / n) for n in salidas},
           "presupuesto": {"formulas": 2, "entrenamientos_candidatos": 0, "busqueda_pesos": 0, "variables_nuevas": 0,
                           "seleccion_por_municipio": 0, "predicciones_59": 0, "predicciones_mezcla_calculadas": int(len(largo))},
           "clases": dict(zip(lectura.mezcla, lectura.clase)), "aporte_especifico_J": aporte_J, "confirmacion_independiente": False}
    (sal / "registro_ejecucion.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    pd.set_option("display.width", 220)
    print(met[met.escenario.eq("SEEN135")].pivot(index="modelo", columns="conjunto", values=["RMSE", "MAE"]).reindex(MODELOS).round(5))
    print(pares[pares.escenario.eq("SEEN135")].round(5).to_string(index=False))
    print(lectura.T.to_string())
    print("aporte específico de J:", aporte_J)


if __name__ == "__main__":
    main()
