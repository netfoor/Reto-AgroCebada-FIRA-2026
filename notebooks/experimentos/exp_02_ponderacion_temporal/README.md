# EXP_02. Ponderación temporal de tres medias

[Abrir el notebook](exp_02_ponderacion_temporal.ipynb). Basta compartir este `.ipynb`: contiene sus capturas, tablas, controles y explicaciones. No requiere descargar el ZIP original, acceder a Drive, aprender Git ni ejecutar otro cuaderno.

## Qué pregunta y qué ejecuta

¿Cambiar tres medias por captura por medias mensuales ponderadas por días mejora E2? El recorrido muestra **regla → capturas de una parcela → media mensual → pesos de siete meses → controles para las 197 → errores OOF → decisión y límite**.

Las tres variables son NDVI Planet, NDVI Sentinel-2 y NDWI Sentinel-2. Se calcula primero la media de cada mes; después se aplican los pesos **30, 31, 30, 31, 31, 30, 31 / 214** de abril–octubre de 2025. No se pondera cada fotografía por los días del mes, no se mezclan sensores, no se filtran nubes ni se imputan meses. Las otras tres variables de E2, municipio, ventana y procedimiento Ridge se conservan.

**Modo lector: cero ajustes de modelos.** Recalcula variables desde capturas, métricas desde predicciones OOF guardadas y decisiones de alpha desde scores internos guardados. No recalcula esos scores, no vuelve a entrenar, no genera nuevas OOF ni las 59 predicciones de entrega.

## Fechas y resultado conservado

T1 se ejecutó el **29 de septiembre de 2026**; esta adaptación es del **8 de octubre**. El recorte de capturas se deriva de los originales durante la adaptación y conserva procedencia, tamaño y hashes propios. No se presenta como un archivo registrado antes de T1 ni como otro experimento.

La evaluación original es FULL138: 138 parcelas y 1,380 predicciones por procedimiento sobre las particiones comunes. El coste histórico fue 1,050 ajustes de T1 y 1,050 del control E2, en Python 3.12.14/scikit-learn 1.9.1. Esta lectura utiliza Python 3.13 y no repite aquel control de entrenamiento.

**Cierre sin adopción:** T1 RMSE 0.5225 t/ha; E2 0.5192; MIX 0.4938. El MAE apenas cambia frente a E2. La sensibilidad sin dos focos solo modifica la puntuación; no retira etiquetas del entrenamiento. El resultado no demuestra que toda representación temporal sea inútil ni que estas medias sean promedios diarios verdaderos.

## Ejecutar

En Colab, subir únicamente el notebook y ejecutar las celdas en orden. La preparación de NumPy, pandas y Matplotlib se anuncia; si necesita reiniciar un módulo cargado, solicita hacerlo manualmente. No descarga datos ni reinicia la sesión automáticamente.

En local, desde la raíz del proyecto uv:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_02.py
```

El ejecutor guarda una ejecución nueva en `resultados_locales/exp_02_ponderacion_temporal/`, sin sobrescribir fuentes históricas. `scripts/construir_exp_02.py` genera el notebook con `config/exp_02_ponderacion_temporal.json`; `artefactos_locales/exp_02_ponderacion_temporal_equipo.zip` reúne su distribución local. Leer el cuaderno no exige abrir esos archivos técnicos.
