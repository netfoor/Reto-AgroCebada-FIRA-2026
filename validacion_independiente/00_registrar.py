"""Paso 0: caja cerrada y registro previo. Solo usa X (municipio y conjunto); no lee ningún rendimiento."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import lib_validacion as L


def main():
    reg_path = L.AQUI / "registro_previo.json"
    if reg_path.exists():
        raise SystemExit("registro_previo.json ya existe: no se vuelve a sortear")
    tx = L.tabla_x()
    caja = L.sortear_caja(tx)
    t = tx.set_index(L.ID)
    etiquetadas = tx.loc[tx.CONJUNTO.eq("ENTRENAMIENTO"), L.ID]
    dev = sorted(set(etiquetadas) - set(caja))
    ext, inn = L.particiones_desarrollo(dev)
    ext.to_csv(L.AQUI / "particiones_externas_desarrollo.csv", index=False)
    inn.to_csv(L.AQUI / "particiones_internas_desarrollo.csv", index=False)
    with open(L.AQUI / "intentos.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["familia", "evento", "fecha_utc", "rmse_dev_seen", "mae_dev_seen", "reps_vs_E_JK", "reps_vs_MIX", "nota"])
        ahora = datetime.now(timezone.utc).isoformat()
        for f in ["F1", "F2", "F3", "F4", "F5"]:
            w.writerow([f, "planeada", ahora, "", "", "", "", "declarada en el registro previo"])
    ahora_utc = datetime.now(timezone.utc)
    reg = {
        "id": "PRUEBA_FINAL_OPUS_11OCT",
        "registrado_utc": ahora_utc.isoformat(),
        "registrado_cdmx": ahora_utc.astimezone(ZoneInfo("America/Mexico_City")).isoformat(),
        "autor": "Claude (Opus 5.5), a pedido de Fortino",
        "solicitud": "Prueba final independiente — Reto AgroCebada 2026 (mensaje de Fortino del 11 oct 2026)",
        "rendimientos_leidos_antes_de_este_registro_en_esta_ronda": False,
        "exposicion_previa_declarada": (
            "El mismo asistente analizó las 138 etiquetas (incluidas las de esta caja) en EXP_08–EXP_11 el 8 oct: "
            "eligió K1, vio la correlación de log(área) (−0.21 dentro de municipio), el variograma con dependencia "
            "<500 m, el éxito de E_JK y la anomalía de lluvia de J como casi etiqueta de celda. Todas las familias "
            "propias están informadas por esa exploración, así que la caja NO es ciega para sus ideas: solo protege "
            "contra la selección adaptativa dentro de esta ronda. Igual que para los candidatos congelados."),
        "caja_cerrada": {
            "ids": caja, "n": len(caja), "sha256_lista": L.hash_lista(caja), "semilla": L.SEMILLA_CAJA,
            "regla": "estratificada por municipio con X: k = floor(0.25·n + 0.5) si n ≥ 3; municipios con n < 3 (Apan, Tepeapulco, Nanacamilpa) quedan en desarrollo; numpy default_rng, municipios alfabéticos, IDs ordenados",
            "conteo_por_municipio": t.loc[caja, "Municipio"].value_counts().to_dict(),
            "justificacion_tamano": (
                "25 % (35 parcelas): deja 103 para desarrollar (pliegues de entrenamiento de ~82, cerca del régimen de 110 de las rondas previas) "
                "y conserva todos los municipios de las 59 ocultas en desarrollo, incluido Nanacamilpa. Con 35 parcelas la caja detecta fallas grandes, "
                "pero no diferencias de ~1 % de RMSE: es una comprobación de cordura y la comparación más limpia de los candidatos, no una prueba de potencia alta."),
        },
        "desarrollo": {"n": len(dev), "conteo_por_municipio": t.loc[dev, "Municipio"].value_counts().to_dict()},
        "semillas": {"caja": L.SEMILLA_CAJA, "cv_desarrollo": L.SEMILLA_CV, "bootstrap": L.SEMILLA_BOOT, "internas_K_en_caja": L.SEMILLA_CAJA_INTERNA},
        "particiones_desarrollo": {
            "esquema": "10 repeticiones × 5 pliegues (KFold barajado, semilla 20261012 + repetición); 4 pliegues internos por entrenamiento exterior (semilla 20261012 + 1000 + 10·rep + pliegue). Distinta de 20261009 y 20260920.",
            "externas": {"ruta": "particiones_externas_desarrollo.csv", "sha256": L.sha(L.AQUI / "particiones_externas_desarrollo.csv")},
            "internas": {"ruta": "particiones_internas_desarrollo.csv", "sha256": L.sha(L.AQUI / "particiones_internas_desarrollo.csv")},
        },
        "candidatos_congelados": {
            "MUN": "media municipal del entrenamiento; municipio no visto → media global (validacion_03.predecir_referencias)",
            "MIX": "0.5·MUN + 0.5·IDW (k=20, potencia 2, piso 1 m) (validacion_03.predecir_referencias)",
            "K": "MIX + β·z(K1 corregido), α=10, residuos de MIX por 4 pliegues internos (modelo_10.predecir_fold)",
            "J": "Jared procedimiento completo: elige entre 148 variables la de mayor |correlación| dentro de grupo con las etiquetas del entrenamiento; OLS con 5 niveles de grupo + pendiente común (preparar_exp_11.jared_completo)",
            "E_JK": "0.5·J + 0.5·K",
            "codigo_sha256": {f: L.sha(L.RAIZ / "scripts" / f) for f in ["validacion_03.py", "modelo_10.py", "preparar_exp_11.py"]},
        },
        "familias_propias": {
            "F1": {"receta": "Modelo mixto jerárquico (REML): niveles fijos por grupo (5) + interceptos aleatorios de municipio y de celda CHIRPS de centroide; predicción BLUP.",
                   "motivo": "Agrupamiento parcial entre escalas territoriales anidadas (Battese, Harter y Fuller, 1988; áreas pequeñas). Formaliza lo que E_JK hace a mano con pesos 50/50.",
                   "preinformada": "Sí: la idea de varias escalas viene de ver E_JK y J (celda) con las 138."},
            "F2": {"receta": "F1 + K1 corregido como efecto fijo (estandarizado con mediana y desviación del entrenamiento; sin dato → 0).",
                   "motivo": "Única señal satelital que pasó filtros.", "preinformada": "Sí: K1 se eligió en EXP_08 con las 138."},
            "F3": {"receta": "F2 + componente espacial gaussiano exponencial (σ²_s y rango estimados por REML, rango en [50, 20000] m).",
                   "motivo": "Dependencia espacial corta del residuo.", "preinformada": "Sí: variograma de EXP_08 con las 138."},
            "F4": {"receta": "⅓·(J + K + F2), pesos iguales fijos.",
                   "motivo": "Rompecabezas de la combinación de pronósticos: pesos iguales suelen ganar a pesos estimados (Claeskens et al., 2016).",
                   "preinformada": "Sí: inspirada en el resultado de E_JK."},
            "F5": {"receta": "F2 + log(área) como efecto fijo (estandarizado con el entrenamiento).",
                   "motivo": "Relación inversa tamaño–rendimiento en rendimientos reportados por productores (Desiere y Jolliffe, 2018; Gourlay, Kilic y Lobell, 2019); la etiqueta es reportada.",
                   "preinformada": "Sí: correlación −0.21 vista con las 138."},
            "sin_ajuste_de_hiperparametros": "Ninguna familia busca hiperparámetros: las varianzas se estiman por REML dentro de cada entrenamiento.",
        },
        "presupuesto": {"max_familias": 10, "declaradas": 5, "regla": "cualquier intento adicional, fallido o corregido se anota en intentos.csv y entra al nulo"},
        "seleccion_final": "La familia propia con menor RMSE agrupado SEEN en la CV de desarrollo. Variante declarada: si la final es F5 (usa área), la variante es F2; en otro caso no hay variante.",
        "criterio_decision_interpretacion": {
            "C1": "Caja (35, todas SEEN): RMSE(final) < RMSE(E_JK) y < RMSE(MIX).",
            "C2": "CV de desarrollo (103, particiones nuevas, SEEN): RMSE(final) < E_JK en ≥8/10 repeticiones Y < MIX en ≥8/10.",
            "C3": "Caja: MAE(final) ≤ MAE(MIX).",
            "C4": "Caja: tras retirar de la evaluación las 2 parcelas con mayor ventaja del final (orden por Δ error cuadrático, por separado frente a E_JK y frente a MIX), el final sigue con menor RMSE frente a ambos.",
            "C5": "Reality Check de White (2000) sobre la CV de desarrollo con TODAS las familias de intentos.csv, benchmark E_JK: p ≤ 0.10.",
            "FAVORABLE": "C1–C5 se cumplen.",
            "PARCIAL": "No favorable, pero el RMSE del final en la caja es menor que el de MIX (si además supera a E_JK y falla otra condición, se reporta qué falló).",
            "NO_FAVORABLE": "En otro caso.",
        },
        "nulo": {"metodo": "Reality Check de White (2000)", "perdida": "por parcela, media del error cuadrático en sus filas SEEN de la CV de desarrollo",
                 "estadistico": "T = max_k √n · media(L_bench − L_k)", "remuestreo": "bootstrap por conglomerados (celdas CHIRPS), recentrado",
                 "B": 5000, "semilla": L.SEMILLA_BOOT, "benchmark_decisivo": "E_JK", "benchmark_informativo": "MIX",
                 "limite": "aproximación: las pérdidas de CV comparten entrenamientos y vecindad; el bootstrap por celdas atenúa, no elimina, esa dependencia"},
        "prohibiciones": {"grafia_cultivo": "no se usa (la columna cultivo_grafia_original de v0 se excluye)", "precision_decimal_etiquetas": "no se usa",
                          "datos_posteriores_31oct": "ninguno: K1 corregido se corta antes de suavizar; las 148 variables de Jared son abr–oct 2025 e historia 2022–2024",
                          "reglas_por_municipio": "ninguna", "caja": "sus etiquetas solo se leen en 03_evaluar_caja.py, una vez"},
        "codigo_sha256": {f: L.sha(L.AQUI / f) for f in ["lib_validacion.py", "00_registrar.py", "01_desarrollo.py", "02_nulo_y_congelar.py", "03_evaluar_caja.py"]},
        "x_sha256": {p: L.sha(L.RAIZ / p) for p in ["data/exp_10_verificacion_contraste_vecinal/metadatos.csv", "data/exp_10_verificacion_contraste_vecinal/variables_197.csv",
                                                   "data/exp_04_lluvia_octubre/grupos.csv", "data/referencias/variables_v0_197.csv", "data/raw/DataSet.zip"]},
    }
    reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: reg[k] for k in ["registrado_cdmx", "caja_cerrada", "desarrollo", "semillas"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
