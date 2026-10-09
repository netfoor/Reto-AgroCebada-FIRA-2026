"""EXP07: comparación acotada y previamente registrada, sin predicciones de entrega."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from modelo_07 import ajustar, predecir
from validacion_03 import (
    ALIAS_HISTORICOS_03,
    particiones_desde_csv,
    predecir_referencias,
    validar_externas,
    validar_internas,
)

ID = "ID_POLIGONO"
Y = "RENDIMIENTO_T_HA"
KEY = ["repeticion", "pliegue", ID]
L = "H7_PL_ndvi_media_pareada"
S = "H7_PL_ndvi_std_media_pareada"
SPECS = {"C0": [L], "C1": [L, S]}
OPCIONES = ("baseline", 0.01, 0.1, 1.0, 10.0, 100.0)
TOL = 1e-12


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def leer(path):
    return pd.read_csv(path, float_precision="round_trip")


def metricas(g):
    if g.empty:
        return {"n_oof": 0, "n_parcelas": 0, "RMSE": np.nan, "MAE": np.nan, "R2": np.nan}
    y, p = g.observado.to_numpy(float), g.predicho.to_numpy(float)
    e = y - p
    sse = float(e @ e)
    sst = float((y - y.mean()) @ (y - y.mean()))
    return {
        "n_oof": len(g),
        "n_parcelas": g[ID].nunique(),
        "RMSE": float(np.sqrt(sse / len(g))),
        "MAE": float(np.mean(abs(e))),
        "R2": 1 - sse / sst if sst > 1e-14 * max(1, float(y @ y)) else np.nan,
    }


def elegir(scores):
    minimo = min(scores.values())
    empates = [k for k, v in scores.items() if v <= minimo + TOL]
    return "baseline" if "baseline" in empates else max(empates)


def ejecutar_comparacion(variables, etiquetas, externas, internas, ref_historica):
    """Una sola corrida: referencia primero, 2,400 evaluaciones, selección train-only."""
    if Y in variables or len(variables) != 197 or not variables[ID].is_unique:
        raise ValueError("Contrato X incorrecto")
    if len(etiquetas) != 138 or not etiquetas[ID].is_unique:
        raise ValueError("Contrato etiquetas incorrecto")
    ids = set(variables.loc[variables.CONJUNTO.eq("ENTRENAMIENTO"), ID])
    if ids != set(etiquetas[ID]) or not np.isfinite(etiquetas[Y]).all():
        raise ValueError("Etiquetas/roles oficiales incoherentes")
    validar_externas(externas, ids)
    validar_internas(internas, externas, ids)
    tabla = variables.loc[variables.CONJUNTO.eq("ENTRENAMIENTO")].copy()
    tabla[Y] = tabla[ID].map(etiquetas.set_index(ID)[Y])
    tabla = tabla.reset_index(drop=True)  # conserva orden histórico de la tabla X
    y = tabla[Y].to_numpy(float)
    municipios = tabla.Municipio.to_numpy(object)
    folds = particiones_desde_csv(externas, tabla)
    rows = []
    # Comprobar referencias antes de ajustar candidatos.
    for r, f, tr, va in folds:
        train, test = tabla.iloc[tr], tabla.iloc[va]
        ref = predecir_referencias(train, test)
        seen = test.Municipio.isin(set(train.Municipio)).to_numpy()
        for modelo in ("MUN", "MIX"):
            for j, i in enumerate(va):
                rows.append(
                    {
                        "modelo": modelo,
                        "repeticion": r,
                        "pliegue": f,
                        ID: tabla.iloc[i][ID],
                        "observado": y[i],
                        "predicho": ref[modelo][j],
                        "municipio_visto": bool(seen[j]),
                        "Municipio": municipios[i],
                    }
                )
    refs = pd.DataFrame(rows)
    hist = ref_historica.copy()
    hist.modelo = hist.modelo.replace(ALIAS_HISTORICOS_03)
    controles = {}
    for modelo in ("MUN", "MIX"):
        a = refs[refs.modelo.eq(modelo)].sort_values(KEY).reset_index(drop=True)
        b = hist[hist.modelo.eq(modelo)].sort_values(KEY).reset_index(drop=True)
        if not a[KEY].equals(b[KEY]) or not np.array_equal(a.observado, b.observado):
            raise ValueError("Claves/etiquetas de referencia distintas")
        diferencia = float(np.max(abs(a.predicho - b.predicho)))
        if diferencia > 1e-8:
            raise ValueError(f"Referencia {modelo} no reproduce histórico: {diferencia}")
        controles[modelo] = diferencia
    print("Referencias reproducidas:", controles, flush=True)
    score_rows, fold_score_rows, selected, parametros = [], [], [], []
    counts = {
        "evaluaciones_internas": 0,
        "evaluaciones_baseline": 0,
        "opciones_ridge_internas": 0,
        "ajustes_ridge_internos": 0,
        "reconstrucciones_exteriores": 0,
        "ajustes_ridge_exteriores": 0,
        "evaluaciones_referencia": 100,
    }
    for r, f, tr, va in folds:
        inn = internas[internas.repeticion.eq(r) & internas.pliegue.eq(f)]
        positions = {pid: i for i, pid in enumerate(tabla[ID])}
        inner_folds = []
        for k, sub in inn.groupby("pliegue_interno", sort=True):
            ti = np.array(sorted(positions[i] for i in sub.loc[sub.rol.eq("entrenamiento"), ID]))
            vi = np.array(sorted(positions[i] for i in sub.loc[sub.rol.eq("validacion"), ID]))
            inner_folds.append((int(k), ti, vi))
        for modelo, columnas in SPECS.items():
            x = tabla[columnas].to_numpy(float)
            scores = {}
            for opcion in OPCIONES:
                sse, n = 0.0, 0
                for k, ti, vi in inner_folds:
                    fit = ajustar(
                        x[ti],
                        y[ti],
                        municipios[ti],
                        None if opcion == "baseline" else float(opcion),
                    )
                    pred, _ = predecir(fit, x[vi], municipios[vi])
                    error = y[vi] - pred
                    sq = float(error @ error)
                    sse += sq
                    n += len(vi)
                    counts["evaluaciones_internas"] += 1
                    if opcion == "baseline":
                        counts["evaluaciones_baseline"] += 1
                    else:
                        counts["opciones_ridge_internas"] += 1
                        counts["ajustes_ridge_internos"] += int(fit["ridge_ajustado"])
                    fold_score_rows.append(
                        {
                            "modelo": modelo,
                            "repeticion": r,
                            "pliegue": f,
                            "pliegue_interno": k,
                            "opcion": str(opcion),
                            "SSE": sq,
                            "n_validacion": len(vi),
                            "ridge_ajustado": bool(fit["ridge_ajustado"]),
                        }
                    )
                scores[opcion] = float(np.sqrt(sse / n))
                score_rows.append(
                    {
                        "modelo": modelo,
                        "repeticion": r,
                        "pliegue": f,
                        "opcion": str(opcion),
                        "RMSE": scores[opcion],
                        "SSE": sse,
                        "n_validacion": n,
                    }
                )
            choice = elegir(scores)
            fit = ajustar(
                x[tr], y[tr], municipios[tr], None if choice == "baseline" else float(choice)
            )
            pred, no_visto = predecir(fit, x[va], municipios[va])
            counts["reconstrucciones_exteriores"] += 1
            counts["ajustes_ridge_exteriores"] += int(fit["ridge_ajustado"])
            selected.append(
                {
                    "modelo": modelo,
                    "repeticion": r,
                    "pliegue": f,
                    "opcion_elegida": str(choice),
                    "RMSE_interior": scores[choice],
                    "ridge_ajustado": bool(fit["ridge_ajustado"]),
                }
            )
            parametros.append(
                {
                    "modelo": modelo,
                    "repeticion": r,
                    "pliegue": f,
                    "columnas": columnas,
                    "modelo_ajustado": fit,
                }
            )
            for j, i in enumerate(va):
                rows.append(
                    {
                        "modelo": modelo,
                        "repeticion": r,
                        "pliegue": f,
                        ID: tabla.iloc[i][ID],
                        "observado": y[i],
                        "predicho": pred[j],
                        "municipio_visto": not bool(no_visto[j]),
                        "Municipio": municipios[i],
                    }
                )
        print(f"Exterior {r}/{f}: C0/C1 completados", flush=True)
    assert counts["evaluaciones_internas"] == 2400
    assert counts["evaluaciones_baseline"] == 400
    assert counts["opciones_ridge_internas"] == 2000
    assert counts["reconstrucciones_exteriores"] == 100
    oof = pd.DataFrame(rows).sort_values(["modelo"] + KEY).reset_index(drop=True)
    expected = (
        externas.loc[externas.rol.eq("validacion"), KEY].sort_values(KEY).reset_index(drop=True)
    )
    for modelo, group in oof.groupby("modelo"):
        assert group[KEY].sort_values(KEY).reset_index(drop=True).equals(expected), modelo
        assert len(group) == 1380 and group.municipio_visto.sum() == 1350
        assert group[ID].nunique() == 138 and group.loc[group.municipio_visto, ID].nunique() == 135
    assert not oof.duplicated(["modelo"] + KEY).any()
    assert np.isfinite(oof[["observado", "predicho"]].to_numpy()).all()
    return {
        "oof": oof,
        "scores": pd.DataFrame(score_rows),
        "scores_pliegue": pd.DataFrame(fold_score_rows),
        "seleccion": pd.DataFrame(selected),
        "parametros": parametros,
        "presupuesto": counts,
        "controles": controles,
    }


def evaluar(oof):
    metric_rows, rep_rows, mun_rows, zona_rows, rule_rows, delta_rows, conc_rows = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for escenario, datos in (("SEEN135", oof[oof.municipio_visto]), ("FULL138", oof)):
        met = {}
        rep = {}
        for modelo, grupo in datos.groupby("modelo", sort=True):
            met[modelo] = metricas(grupo)
            metric_rows.append({"escenario": escenario, "modelo": modelo, **met[modelo]})
            rep[modelo] = {}
            for r, g in grupo.groupby("repeticion", sort=True):
                rep[modelo][r] = metricas(g)
                rep_rows.append(
                    {"escenario": escenario, "modelo": modelo, "repeticion": r, **rep[modelo][r]}
                )
            for municipio, g in grupo.groupby("Municipio", sort=True):
                mun_rows.append(
                    {
                        "escenario": escenario,
                        "modelo": modelo,
                        "Municipio": municipio,
                        **metricas(g),
                    }
                )
            for zona, mask in (
                ("Chignahuapan", grupo.Municipio.eq("Chignahuapan")),
                ("Resto", grupo.Municipio.ne("Chignahuapan")),
            ):
                zona_rows.append(
                    {
                        "escenario": escenario,
                        "modelo": modelo,
                        "zona": zona,
                        **metricas(grupo[mask]),
                    }
                )
        for modelo in SPECS:
            n_rmse = sum(rep[modelo][r]["RMSE"] < rep["MIX"][r]["RMSE"] for r in range(10))
            n_mae_mix = sum(rep[modelo][r]["MAE"] <= rep["MIX"][r]["MAE"] for r in range(10))
            n_mae_mun = sum(rep[modelo][r]["MAE"] <= rep["MUN"][r]["MAE"] for r in range(10))
            cumple_rmse = met[modelo]["RMSE"] < met["MIX"]["RMSE"] and n_rmse >= 8
            cumple_mix = met[modelo]["MAE"] <= met["MIX"]["MAE"] and n_mae_mix >= 8
            cumple_mun = met[modelo]["MAE"] <= met["MUN"]["MAE"] and n_mae_mun >= 8
            n_incremental = sum(rep["C1"][r]["RMSE"] < rep["C0"][r]["RMSE"] for r in range(10))
            rule_rows.append(
                {
                    "escenario": escenario,
                    "modelo": modelo,
                    "n_RMSE_mejor_MIX": n_rmse,
                    "n_MAE_no_peor_MIX": n_mae_mix,
                    "n_MAE_no_peor_MUN": n_mae_mun,
                    "competitivo_propuesto": cumple_rmse and cumple_mix,
                    "cumple_criterio_historico": cumple_rmse and cumple_mun,
                    "n_RMSE_C1_mejor_C0": n_incremental,
                    "aporte_H7": modelo == "C1"
                    and n_incremental >= 8
                    and met["C1"]["RMSE"] < met["C0"]["RMSE"],
                }
            )
        for candidato, control in (("C1", "C0"), ("C1", "MIX"), ("C0", "MIX")):
            a = datos[datos.modelo.eq(candidato)].sort_values(KEY).reset_index(drop=True)
            b = datos[datos.modelo.eq(control)].sort_values(KEY).reset_index(drop=True)
            assert a[KEY].equals(b[KEY])
            delta = a[KEY + ["Municipio"]].copy()
            delta["ganancia_SSE"] = (b.observado - b.predicho) ** 2 - (
                a.observado - a.predicho
            ) ** 2
            dg = delta.groupby([ID, "Municipio"], sort=True).ganancia_SSE.sum().reset_index()
            dg = dg.sort_values(["ganancia_SSE", ID], ascending=[False, True])
            positivos = float(dg.ganancia_SSE.clip(lower=0).sum())
            for row in dg.to_dict("records"):
                delta_rows.append(
                    {"escenario": escenario, "candidato": candidato, "control": control, **row}
                )
            for k in (0, 2, 5):
                excluidos = dg.loc[dg.ganancia_SSE.gt(0), ID].head(k).tolist()
                mask = ~a[ID].isin(excluidos)
                share = (
                    float(dg.loc[dg[ID].isin(excluidos), "ganancia_SSE"].sum()) / positivos
                    if positivos
                    else np.nan
                )
                conc_rows.append(
                    {
                        "escenario": escenario,
                        "candidato": candidato,
                        "control": control,
                        "top_k_solicitado": k,
                        "n_parcelas_excluidas_solo_evaluacion": len(excluidos),
                        "IDs_excluidos": "|".join(excluidos),
                        "ganancia_SSE_neta_total": float(dg.ganancia_SSE.sum()),
                        "fraccion_ganancia_positiva_top_k": share,
                        "n_parcelas_mejoran": int(dg.ganancia_SSE.gt(0).sum()),
                        "n_parcelas_empeoran": int(dg.ganancia_SSE.lt(0).sum()),
                        "RMSE_candidato": metricas(a[mask])["RMSE"],
                        "RMSE_control": metricas(b[mask])["RMSE"],
                        "MAE_candidato": metricas(a[mask])["MAE"],
                        "MAE_control": metricas(b[mask])["MAE"],
                    }
                )
    return {
        "metricas": pd.DataFrame(metric_rows),
        "repeticiones": pd.DataFrame(rep_rows),
        "municipios": pd.DataFrame(mun_rows),
        "zonas": pd.DataFrame(zona_rows),
        "reglas": pd.DataFrame(rule_rows),
        "deltas": pd.DataFrame(delta_rows),
        "concentracion": pd.DataFrame(conc_rows),
    }


def json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    raise TypeError(type(obj).__name__)


def registrar(raiz):
    folder = raiz / "data/exp_07_heterogeneidad_parcela"
    qa = json.loads((folder / "diagnosticos_X.json").read_text())
    if not qa["apta"]:
        raise ValueError("Factibilidad fallida; no se registran candidatos")
    files = [
        "scripts/experimento_07.py",
        "scripts/modelo_07.py",
        "scripts/factibilidad_07.py",
        "scripts/validacion_03.py",
        "tests/test_modelo_07.py",
        "tests/test_factibilidad_07.py",
        "tests/test_experimento_07.py",
        "pyproject.toml",
        "uv.lock",
        "notebooks/experimentos/exp_07_heterogeneidad_parcela/protocolo_definitivo.md",
    ]
    files += [str(p.relative_to(raiz)) for p in sorted(folder.iterdir()) if p.is_file()]
    destino = raiz / "notebooks/experimentos/exp_07_heterogeneidad_parcela/registro_previo.json"
    if destino.exists():
        raise ValueError("El registro previo ya existe; no se sobrescribe")
    registro = {
        "id": "EXP_07",
        "registrado_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "registro_previo_interno_no_sello_de_terceros",
        "autorizacion_literal": "Perfecto correlo y verifiquemos que sucede",
        "interpretacion_comunicada_antes_de_ajustar": "Aprobación del plan incluido MAE<=MIX; criterio histórico MAE<=MUN también reportado",
        "exposicion_previa_etiquetas": True,
        "confirmacion_independiente": False,
        "archivos": {
            f: {"sha256": sha(raiz / f), "bytes": (raiz / f).stat().st_size} for f in files
        },
    }
    destino.write_text(json.dumps(registro, indent=2, ensure_ascii=False) + "\n")
    print("Registro previo guardado:", destino, registro["registrado_utc"])


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registrar", action="store_true")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    if args.registrar:
        registrar(raiz)
        return
    regpath = raiz / "notebooks/experimentos/exp_07_heterogeneidad_parcela/registro_previo.json"
    registro = json.loads(regpath.read_text())
    for f, rec in registro["archivos"].items():
        if sha(raiz / f) != rec["sha256"] or (raiz / f).stat().st_size != rec["bytes"]:
            raise ValueError("Archivo registrado cambió: " + f)
    inicio = datetime.now(timezone.utc)
    salida = args.salida or raiz / "resultados/exp_07_heterogeneidad_parcela" / inicio.strftime(
        "%Y%m%dT%H%M%S_%fZ"
    )
    if salida.exists():
        raise ValueError("La salida debe ser nueva")
    folder = raiz / "data/exp_07_heterogeneidad_parcela"
    variables = leer(folder / "variables_197.csv").merge(
        leer(folder / "coordenadas.csv"), on=ID, how="left", validate="one_to_one", sort=False
    )
    resultado = ejecutar_comparacion(
        variables,
        *(
            leer(folder / f)
            for f in ("etiquetas.csv", "externas.csv", "internas.csv", "referencias_historicas.csv")
        ),
    )
    tablas = evaluar(resultado["oof"])
    salida.mkdir(parents=True)
    for nombre, tabla in {
        "predicciones_oof": resultado["oof"],
        "scores_internos": resultado["scores"],
        "scores_por_pliegue": resultado["scores_pliegue"],
        "seleccion": resultado["seleccion"],
        **tablas,
    }.items():
        tabla.to_csv(
            salida / f"{nombre}.csv", index=False, float_format="%.17g", lineterminator="\n"
        )
    (salida / "parametros_exteriores.json").write_text(
        json.dumps(
            resultado["parametros"],
            indent=2,
            ensure_ascii=False,
            default=json_default,
            sort_keys=True,
        )
        + "\n"
    )
    resumen = {
        "id": "EXP_07",
        "inicio_utc": inicio.isoformat(),
        "fin_utc": datetime.now(timezone.utc).isoformat(),
        "registro_sha256": sha(regpath),
        "python": platform.python_version(),
        "presupuesto": resultado["presupuesto"],
        "controles_referencias": resultado["controles"],
        "oof": len(resultado["oof"]),
        "predicciones_59_generadas": 0,
        "colab_real_probado": False,
        "salidas_sha256": {p.name: sha(p) for p in sorted(salida.iterdir())},
    }
    (salida / "registro_ejecucion.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False) + "\n"
    )
    print(tablas["metricas"].to_string(index=False))
    print(tablas["reglas"].to_string(index=False))
    print(json.dumps(resumen, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
