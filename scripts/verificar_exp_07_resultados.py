"""Revisión independiente posterior de EXP_07, sin ajustar modelos.

Lee evidencia guardada, recalcula métricas, decisiones y aritmética de las
predicciones desde parámetros. No importa el motor constructor, no resuelve
coeficientes y no produce rendimientos para las 59 parcelas de entrega.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ID = "ID_POLIGONO"
KEY = ["repeticion", "pliegue", ID]
L = "H7_PL_ndvi_media_pareada"
S = "H7_PL_ndvi_std_media_pareada"
AGENTE = "/root/critica_priorizacion_ml"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exigir(condicion, descripcion):
    if not bool(condicion):
        raise ValueError("Verificación independiente fallida: " + descripcion)


def cerca(a, b, descripcion, tol=1e-14):
    exigir(np.allclose(a, b, rtol=0, atol=tol, equal_nan=True), descripcion)


def leer(path):
    return pd.read_csv(path, float_precision="round_trip")


def metricas(grupo):
    y = grupo.observado.to_numpy(float)
    error = grupo.predicho.to_numpy(float) - y
    sse = float(np.sum(error**2))
    sst = float(np.sum((y - y.mean()) ** 2))
    return {
        "RMSE": float(np.sqrt(sse / len(y))),
        "MAE": float(np.mean(np.abs(error))),
        "R2": 1 - sse / sst if sst > 1e-14 * max(1, float(y @ y)) else np.nan,
    }


def verificar(raiz):
    raiz = Path(raiz)
    evidencia = raiz / "notebooks/experimentos/exp_07_heterogeneidad_parcela"
    datos = raiz / "data/exp_07_heterogeneidad_parcela"
    corrida = raiz / "resultados/exp_07_heterogeneidad_parcela/registrada"
    replica = raiz / "resultados/exp_07_heterogeneidad_parcela/replica_determinismo"
    prereg_path = evidencia / "registro_previo.json"
    prereg = json.loads(prereg_path.read_text())
    registro = json.loads((corrida / "registro_ejecucion.json").read_text())
    reg_replica = json.loads((replica / "registro_ejecucion.json").read_text())
    exigir(sha(prereg_path) == registro["registro_sha256"], "hash del registro previo")
    for nombre, rec in prereg["archivos"].items():
        archivo = raiz / nombre
        exigir(archivo.stat().st_size == rec["bytes"] and sha(archivo) == rec["sha256"], nombre)
    exigir(
        datetime.fromisoformat(prereg["registrado_utc"])
        < datetime.fromisoformat(registro["inicio_utc"])
        < datetime.fromisoformat(registro["fin_utc"]),
        "orden temporal interno previo a la corrida",
    )
    for nombre, digest in registro["salidas_sha256"].items():
        exigir(sha(corrida / nombre) == digest, "salida: " + nombre)
        exigir(sha(replica / nombre) == digest, "réplica: " + nombre)
        exigir((corrida / nombre).read_bytes() == (replica / nombre).read_bytes(), nombre)
    exigir(registro["salidas_sha256"] == reg_replica["salidas_sha256"], "manifiestos réplica")
    exigir(registro["registro_sha256"] == reg_replica["registro_sha256"], "preregistro común")
    exigir(registro["presupuesto"] == reg_replica["presupuesto"], "presupuesto réplica")

    oof = leer(corrida / "predicciones_oof.csv")
    guardadas = leer(corrida / "metricas.csv")
    reglas = leer(corrida / "reglas.csv")
    zonas = leer(corrida / "zonas.csv")
    concentracion = leer(corrida / "concentracion.csv")
    scores = leer(corrida / "scores_internos.csv")
    scores_fold = leer(corrida / "scores_por_pliegue.csv")
    seleccion = leer(corrida / "seleccion.csv")
    externas = leer(datos / "externas.csv")
    x = leer(datos / "variables_197.csv").set_index(ID)
    esperadas = externas.loc[externas.rol.eq("validacion"), KEY].sort_values(KEY).reset_index(drop=True)
    exigir(len(oof) == 5520 and set(oof.modelo) == {"C0", "C1", "MUN", "MIX"}, "OOF completas")
    exigir(not oof.duplicated(["modelo"] + KEY).any(), "OOF sin duplicados")
    exigir(oof.groupby(ID).observado.nunique().eq(1).all(), "objetivo consistente por parcela")
    exigir(np.isfinite(oof[["observado", "predicho"]]).all().all(), "OOF finitas")
    exigir(pd.api.types.is_bool_dtype(oof.municipio_visto), "máscara booleana")
    for modelo, grupo in oof.groupby("modelo"):
        exigir(grupo[KEY].sort_values(KEY).reset_index(drop=True).equals(esperadas), modelo)
        exigir(len(grupo) == 1380 and grupo[ID].nunique() == 138, "FULL de " + modelo)
        exigir(grupo.municipio_visto.sum() == 1350, "SEEN de " + modelo)
        exigir(grupo.loc[grupo.municipio_visto, ID].nunique() == 135, "IDs SEEN de " + modelo)
    for (rep, fold), grupo in externas.groupby(["repeticion", "pliegue"]):
        tr = grupo.loc[grupo.rol.eq("entrenamiento"), ID]
        q = oof[oof.repeticion.eq(rep) & oof.pliegue.eq(fold)]
        exigir(np.array_equal(q.Municipio.isin(set(x.loc[tr, "Municipio"])), q.municipio_visto), "máscara por metadatos")
    historica = leer(datos / "referencias_historicas.csv")
    historica["modelo"] = historica.modelo.replace({
        "Media municipal": "MUN", "Municipio + IDW fijo": "MIX",
    })
    controles_referencias = {}
    for modelo in ("MUN", "MIX"):
        nueva = oof[oof.modelo.eq(modelo)].sort_values(KEY).reset_index(drop=True)
        vieja = historica[historica.modelo.eq(modelo)].sort_values(KEY).reset_index(drop=True)
        exigir(nueva[KEY].equals(vieja[KEY]), "referencia histórica: claves " + modelo)
        exigir(np.array_equal(nueva.observado, vieja.observado), "referencia histórica: objetivo " + modelo)
        diferencia = float(np.max(abs(nueva.predicho - vieja.predicho)))
        exigir(diferencia <= 1e-8, "referencia histórica: predicciones " + modelo)
        cerca(diferencia, registro["controles_referencias"][modelo], "control guardado " + modelo)
        controles_referencias[modelo] = diferencia

    tablas_metricas, tablas_reglas, tablas_zonas, tablas_concentracion = [], [], [], []
    for escenario, df in (("SEEN135", oof[oof.municipio_visto]), ("FULL138", oof)):
        grupos = dict(tuple(df.groupby("modelo")))
        met = {modelo: metricas(g) for modelo, g in grupos.items()}
        rep = {modelo: {r: metricas(g) for r, g in q.groupby("repeticion")} for modelo, q in grupos.items()}
        for modelo, valores in met.items():
            row = guardadas[guardadas.escenario.eq(escenario) & guardadas.modelo.eq(modelo)].iloc[0]
            cerca(list(valores.values()), row[["RMSE", "MAE", "R2"]].to_numpy(float), "métricas " + modelo)
            tablas_metricas.append({"escenario": escenario, "modelo": modelo, **valores})
            for zona in ("Chignahuapan", "Resto"):
                g = grupos[modelo]
                mask = g.Municipio.eq("Chignahuapan")
                medida = metricas(g[mask if zona == "Chignahuapan" else ~mask])
                z = zonas[zonas.escenario.eq(escenario) & zonas.modelo.eq(modelo) & zonas.zona.eq(zona)].iloc[0]
                cerca(list(medida.values()), z[["RMSE", "MAE", "R2"]].to_numpy(float), "zona " + zona)
                tablas_zonas.append({"escenario": escenario, "modelo": modelo, "zona": zona, **medida})
        n_inc = sum(rep["C1"][r]["RMSE"] < rep["C0"][r]["RMSE"] for r in range(10))
        for modelo in ("C0", "C1"):
            nr = sum(rep[modelo][r]["RMSE"] < rep["MIX"][r]["RMSE"] for r in range(10))
            nmix = sum(rep[modelo][r]["MAE"] <= rep["MIX"][r]["MAE"] for r in range(10))
            nmun = sum(rep[modelo][r]["MAE"] <= rep["MUN"][r]["MAE"] for r in range(10))
            rmse_ok = met[modelo]["RMSE"] < met["MIX"]["RMSE"] and nr >= 8
            competitivo = rmse_ok and met[modelo]["MAE"] <= met["MIX"]["MAE"] and nmix >= 8
            historico = rmse_ok and met[modelo]["MAE"] <= met["MUN"]["MAE"] and nmun >= 8
            aporte = modelo == "C1" and met["C1"]["RMSE"] < met["C0"]["RMSE"] and n_inc >= 8
            row = reglas[reglas.escenario.eq(escenario) & reglas.modelo.eq(modelo)].iloc[0]
            exigir(tuple(row[["n_RMSE_mejor_MIX", "n_MAE_no_peor_MIX", "n_MAE_no_peor_MUN", "n_RMSE_C1_mejor_C0"]]) == (nr, nmix, nmun, n_inc), "conteos de reglas")
            exigir(row.competitivo_propuesto == competitivo and row.cumple_criterio_historico == historico and row.aporte_H7 == aporte, "decisión")
            tablas_reglas.append({"escenario": escenario, "modelo": modelo, "RMSE_mejor_MIX": nr, "MAE_no_peor_MIX": nmix, "MAE_no_peor_MUN": nmun, "RMSE_C1_mejor_C0": n_inc, "competitivo": bool(competitivo), "aporte_H7": bool(aporte)})
        for candidato, control in (("C1", "C0"), ("C1", "MIX"), ("C0", "MIX")):
            a = grupos[candidato].sort_values(KEY).reset_index(drop=True)
            b = grupos[control].sort_values(KEY).reset_index(drop=True)
            exigir(a[KEY].equals(b[KEY]), "comparación pareada")
            ganancia = a[[ID, "Municipio"]].copy()
            ganancia["SSE"] = (b.predicho - b.observado) ** 2 - (a.predicho - a.observado) ** 2
            dg = ganancia.groupby([ID, "Municipio"]).SSE.sum().reset_index().sort_values(["SSE", ID], ascending=[False, True])
            positivos = float(dg.SSE.clip(lower=0).sum())
            for k in (0, 2, 5):
                excluidos = dg.loc[dg.SSE.gt(0), ID].head(k).tolist()
                mask = ~a[ID].isin(excluidos)
                share = float(dg.loc[dg[ID].isin(excluidos), "SSE"].sum()) / positivos if positivos else np.nan
                row = concentracion[concentracion.escenario.eq(escenario) & concentracion.candidato.eq(candidato) & concentracion.control.eq(control) & concentracion.top_k_solicitado.eq(k)].iloc[0]
                cerca(float(dg.SSE.sum()), row.ganancia_SSE_neta_total, "SSE neta", 1e-12)
                cerca(share, row.fraccion_ganancia_positiva_top_k, "fracción positiva")
                exigir(row.n_parcelas_excluidas_solo_evaluacion == len(excluidos), "exclusiones solo evaluación")
                exigir(row.n_parcelas_mejoran == dg.SSE.gt(0).sum() and row.n_parcelas_empeoran == dg.SSE.lt(0).sum(), "conteos de concentración")
                ma, mb = metricas(a[mask]), metricas(b[mask])
                cerca([ma["RMSE"], mb["RMSE"], ma["MAE"], mb["MAE"]], row[["RMSE_candidato", "RMSE_control", "MAE_candidato", "MAE_control"]].to_numpy(float), "sensibilidad")
                tablas_concentracion.append({"escenario": escenario, "candidato": candidato, "control": control, "top_k": k, "ganancia_SSE_neta": float(dg.SSE.sum()), "fraccion_ganancias_positivas": share, "RMSE_candidato": ma["RMSE"], "RMSE_control": mb["RMSE"]})

    exigir(len(scores) == 600 and len(scores_fold) == 2400 and len(seleccion) == 100, "scores y decisiones")
    for key, grupo in scores_fold.groupby(["modelo", "repeticion", "pliegue", "opcion"]):
        exigir(len(grupo) == 4 and set(grupo.pliegue_interno) == set(range(4)), "cuatro scores por opción")
        row = scores[scores.modelo.eq(key[0]) & scores.repeticion.eq(key[1]) & scores.pliegue.eq(key[2]) & scores.opcion.eq(key[3])].iloc[0]
        cerca(grupo.SSE.sum(), row.SSE, "SSE interior agrupada", 1e-12)
        exigir(grupo.n_validacion.sum() == row.n_validacion, "n interior agrupado")
        cerca(np.sqrt(grupo.SSE.sum() / grupo.n_validacion.sum()), row.RMSE, "RMSE interior")
    for key, grupo in scores.groupby(["modelo", "repeticion", "pliegue"]):
        exigir(set(grupo.opcion) == {"baseline", "0.01", "0.1", "1.0", "10.0", "100.0"}, "rejilla exacta")
        empates = grupo.loc[grupo.RMSE.le(grupo.RMSE.min() + 1e-12), "opcion"].tolist()
        choice = "baseline" if "baseline" in empates else str(max(float(v) for v in empates))
        row = seleccion[seleccion.modelo.eq(key[0]) & seleccion.repeticion.eq(key[1]) & seleccion.pliegue.eq(key[2])].iloc[0]
        exigir(choice == row.opcion_elegida, "selección y desempate")

    parametros = json.loads((corrida / "parametros_exteriores.json").read_text())
    exigir(len(parametros) == 100, "100 parámetros exteriores")
    max_error_pred = 0.0
    baselines = 0
    objetivo_oof = oof[[ID, "observado"]].drop_duplicates().set_index(ID).observado
    for rec in parametros:
        m = rec["modelo_ajustado"]
        r, fold, modelo, cols = rec["repeticion"], rec["pliegue"], rec["modelo"], rec["columnas"]
        exigir(cols == ([L] if modelo == "C0" else [L, S]), "entradas de cada procedimiento")
        part = externas[externas.repeticion.eq(r) & externas.pliegue.eq(fold)]
        tr = part.loc[part.rol.eq("entrenamiento"), ID]
        grupo = x.loc[tr]
        xx = grupo[cols].to_numpy(float)
        exigir(len(xx) == m["n_entrenamiento"], "tamaño del entrenamiento")
        mediana = np.nanmedian(xx, axis=0)
        cerca(mediana, m["medianas"], "medianas train-only")
        imputada = np.where(np.isnan(xx), mediana, xx)
        frame = pd.DataFrame(imputada, index=grupo.index, columns=cols)
        medias = frame.groupby(grupo.Municipio).mean()
        u = imputada - medias.reindex(grupo.Municipio).to_numpy()
        escala = np.sqrt(np.mean(u * u, axis=0))
        umbral = 1e-12 * np.maximum(1, np.max(abs(imputada), axis=0))
        activa = escala > umbral
        cerca(escala, m["escala"], "escala train-only")
        cerca(umbral, m["umbral_escala"], "umbral relativo", 1e-24)
        exigir(np.array_equal(activa, m["activa"]), "columna activa")
        for mun, row in medias.iterrows():
            cerca(row.to_numpy(), m["media_x"][mun], "media X municipal train-only")
        objetivo_tr = objetivo_oof.reindex(tr)
        medias_y = objetivo_tr.groupby(grupo.Municipio).mean()
        for mun, media in medias_y.items():
            cerca(media, m["media_y"][mun], "media y municipal train-only")
        cerca(objetivo_tr.mean(), m["media_global_y"], "media y global train-only")
        held = oof[oof.modelo.eq(modelo) & oof.repeticion.eq(r) & oof.pliegue.eq(fold)]
        pred = []
        beta = np.asarray(m["beta"], float)
        for row in held.itertuples():
            valor = x.loc[getattr(row, ID), cols].to_numpy(float)
            valor = np.where(np.isnan(valor), mediana, valor)
            if row.Municipio not in m["media_y"]:
                estimado = m["media_global_y"]
            else:
                residuo = valor[activa] - np.asarray(m["media_x"][row.Municipio])[activa]
                estimado = m["media_y"][row.Municipio] + float(beta[activa] @ (residuo / escala[activa]))
            pred.append(estimado)
        error = float(np.max(abs(held.predicho.to_numpy() - np.asarray(pred))))
        max_error_pred = max(max_error_pred, error)
        exigir(error < 1e-14, "predicciones desde parámetros guardados")
        if m["alpha"] is None:
            base = oof[oof.modelo.eq("MUN") & oof.repeticion.eq(r) & oof.pliegue.eq(fold)].set_index(ID).loc[held[ID], "predicho"].to_numpy()
            exigir(np.array_equal(held.predicho.to_numpy(), base), "baseline=MUN exacto")
            baselines += 1

    qa = json.loads((datos / "diagnosticos_X.json").read_text())
    train_qa = leer(datos / "variacion_entrenamientos.csv")
    exigir(qa["apta"] and len(train_qa) == 500 and not train_qa.columna_vacia.any(), "factibilidad X")
    exigir(not train_qa[train_qa.variable.eq(S)].escala_degenerada.any(), "S intramunicipal")
    presupuesto = registro["presupuesto"]
    exigir(len(scores_fold) == presupuesto["evaluaciones_internas"] == 2400, "presupuesto interior")
    exigir(scores_fold.opcion.eq("baseline").sum() == presupuesto["evaluaciones_baseline"] == 400, "baseline interior")
    exigir(scores_fold.ridge_ajustado.sum() == presupuesto["ajustes_ridge_internos"] == 2000, "Ridge interior")
    exigir(seleccion.ridge_ajustado.sum() == presupuesto["ajustes_ridge_exteriores"] == 11, "Ridge exterior")
    exigir(len(seleccion) == presupuesto["reconstrucciones_exteriores"] == 100, "reconstrucciones")
    exigir(presupuesto["evaluaciones_referencia"] == 100 and baselines == 89, "referencias y baseline")
    exigir(registro["predicciones_59_generadas"] == reg_replica["predicciones_59_generadas"] == 0, "sin predicciones finales")
    exigir(len(registro["salidas_sha256"]) == 12, "12 salidas idénticas")
    conteos = {m: g.opcion_elegida.value_counts().to_dict() for m, g in seleccion.groupby("modelo")}
    return {
        "id": "EXP_07",
        "verificado_utc": datetime.now(timezone.utc).isoformat(),
        "tipo": "revision_independiente_posterior_a_resultados_sin_ajustar",
        "autor_agente": AGENTE,
        "agente_distinto_del_constructor": True,
        "revision_humana": False,
        "sello_temporal_externo": False,
        "registros_previos_y_salidas_intactos": True,
        "registro_previo_sha256": sha(prereg_path),
        "registro_previo_utc": prereg["registrado_utc"],
        "inicio_corrida_utc": registro["inicio_utc"],
        "fin_corrida_utc": registro["fin_utc"],
        "script_verificador_sha256": sha(Path(__file__)),
        "ajustes_modelos_esta_revision": 0,
        "coeficientes_reestimados": 0,
        "variantes_nuevas": 0,
        "predicciones_59_generadas": 0,
        "oof_verificadas": len(oof),
        "scores_por_pliegue_verificados": len(scores_fold),
        "scores_agrupados_verificados": len(scores),
        "selecciones_verificadas": len(seleccion),
        "modelos_exteriores_reconstruidos_desde_parametros": len(parametros),
        "max_error_predicciones_reconstruidas": max_error_pred,
        "medianas_medias_X_y_escalas_train_only_verificadas": True,
        "mascara_SEEN_derivada_solo_de_metadatos": True,
        "baselines_exactamente_MUN": baselines,
        "controles_referencias_historicas": controles_referencias,
        "selecciones": conteos,
        "presupuesto_por_corrida": presupuesto,
        "salidas_identicas_byte_a_byte": 12,
        "ajustes_Ridge_fisicos_dos_corridas": 2 * (presupuesto["ajustes_ridge_internos"] + presupuesto["ajustes_ridge_exteriores"]),
        "factibilidad_X": qa,
        "metricas_recalculadas": tablas_metricas,
        "reglas_recalculadas": tablas_reglas,
        "zonas_recalculadas": tablas_zonas,
        "concentracion_recalculada": tablas_concentracion,
        "conclusion": "Cierre sin adopción: C1 no cumple aporte H7; C0/C1 no cumplen competitividad ni criterio histórico.",
        "limites": [
            "Verificar aritmética y parámetros no es repetir el entrenamiento ni confirmar generalización independiente.",
            "Ambos candidatos cumplen MAE<=MIX, pero fallan RMSE<MIX; el cambio de política no altera el cierre.",
            "La SSE neta C1-C0 es negativa; la fracción positiva top2/top5 no describe una mejora neta.",
            "No se descarta la heterogeneidad espacial en general ni relaciones no lineales.",
            "CV y política son desarrollo adaptativo sobre las mismas etiquetas; repeticiones no independientes.",
            "No acredita ejecución real en Colab ni producción de las 59 predicciones finales.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    reporte = verificar(args.raiz)
    texto = json.dumps(reporte, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.salida:
        if args.salida.exists():
            raise ValueError("El reporte debe ser nuevo; no se sobrescribe evidencia")
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(texto)
    print(texto)


if __name__ == "__main__":
    main()
