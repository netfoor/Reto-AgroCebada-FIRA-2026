# EDA — Conjunto_datos_BASICO_AgroCebada2026.csv (Sentinel-2 + Landsat)

Script: `outputs/scripts/02_dataset_basico.R`

## Estructura general
- 107,666 filas × 98 columnas: `ID_POLIGONO`, `fecha_captura`, `sensor`, 22 índices × 4 estadísticos (promedio/std/max/min) + `vi6t_*`, y `porcentaje_nubosidad`.
- Rango temporal: 2022-01-01 a 2025-12-31 (608 fechas distintas).
- Sensores: Landsat 48,626 filas / Sentinel-2 59,040 filas.
- Las 197 parcelas tienen al menos una observación (cobertura completa a nivel de parcela).

## Datos faltantes: mecanismo estructural, no aleatorio
1. **Separación por sensor (100% determinística):** todos los índices Sentinel-2 (NDVI, EVI, LAI, SAVI, FAPAR, etc.) están `NA` en el 100% de las filas Landsat, y `VI6T` está `NA` en el 100% de las filas Sentinel-2. Esto es por diseño (cada sensor entrega variables distintas) — **no debe tratarse como missing data a imputar**, sino separarse antes de cualquier análisis por sensor.
2. **Dentro de cada sensor, sigue habiendo NA real:** NDVI (y el resto de índices Sentinel-2) falta en 24.0% de las filas Sentinel-2 (14,163 de 59,040); VI6T falta en 36.1% de las filas Landsat.
3. **Hallazgo clave — la nubosidad explica casi perfectamente el faltante Sentinel-2:** cuando `ndvi_promedio` es NA, la mediana de `porcentaje_nubosidad` es **100%**; cuando está presente, la mediana es **0%** (media 100 vs 6.85). Es decir, el faltante es MNAR pero completamente explicable: la escena estaba 100% cubierta de nubes. Esto es muy útil metodológicamente — el filtrado por nubosidad ya "impone" el patrón de missingness, así que imputar estos NA no tendría sentido físico; mejor excluir esas observaciones o usar interpolación temporal explícita.
4. `porcentaje_nubosidad` en sí tiene 3,056 NA (2.8%) — un faltante secundario y menor, no explicado por lo anterior.
5. **Concentración temporal:** el % de NA en NDVI (Sentinel-2) varía fuertemente por mes: picos en sep-2022 (77.9%), ago-2023 (63.6%), jun-2025 (60.0%), sep-2024 (56.8%), etc. — consistente con la temporada de lluvias en México (jun–oct), que aumenta la cobertura de nubes.
6. **Concentración por parcela:** hay dispersión pero no parcelas completamente sin datos; el peor caso (AGC_049) tiene 30.2% de NA en NDVI, dentro de un rango razonable (top-10 entre 28.6% y 30.2%).
7. Observaciones (fecha × sensor) por parcela: min 494, mediana 511, media 546.5, max 692 — hay algo de heterogeneidad en la frecuencia de paso de los sensores por parcela, sin casos extremos de escasez.

Figuras: `02_hist_obs_por_parcela_basico.png`, `02_hist_nubosidad_basico.png`, `02_box_nubosidad_vs_ndvi_faltante.png`.

## Distribución de índices clave
- Rangos generales razonables para vegetación de secano/temporal: NDVI 0–0.82 (media 0.24), EVI 0–0.9 (media 0.19), SAVI 0–0.62 (media 0.15), NDWI -0.36 a 0.70 (media -0.05), MSI 0.18–2.17 (media 1.16).
- **Anomalía a destacar:** `lai_promedio` toma valores mínimos negativos (hasta -0.19). El LAI (índice de área foliar) es conceptualmente ≥ 0; valores negativos sugieren que la fórmula del proveedor no está acotada o que hay ruido/artefactos en píxeles con vegetación muy escasa o suelo desnudo. No se debe interpretar literalmente como "área foliar negativa"; conviene documentar el rango observado y, si se usa como predictor, quizás truncar en 0 o tratarlo como score relativo.
- Comparando NDVI entre sensores no aplica directamente (Sentinel-2 es el único con NDVI en este dataset básico), pero se guardó el boxplot NDVI para referencia.

Figuras: `02_hist_indices_clave_basico.png`, `02_box_ndvi_por_sensor.png`.

## Outliers (regla IQR 1.5×)
| Índice | N outliers |
|---|---|
| ndvi_promedio | 3,719 |
| evi_promedio | 4,909 |
| lai_promedio | 5,236 |
| savi_promedio | 4,262 |
| ndwi_promedio | 2,016 |
| msi_promedio | 88 |
| vi6t_promedio | 1,042 |

El volumen es alto en términos absolutos, pero esperable: la regla IQR marca como "outlier" cualquier observación de una fase fenológica extrema (pico vegetativo o suelo desnudo) dentro de una serie con fuerte estacionalidad de 4 años — **no son errores de captura**, sino variabilidad fenológica real. No se recomienda eliminarlos sin más contexto; conviene revisar outliers solo dentro de ventanas fenológicas específicas.

## Relación preliminar con rendimiento (solo ENTRENAMIENTO)
Usando el promedio simple de cada índice a lo largo de todo el periodo disponible por parcela (138/138 parcelas ENTRENAMIENTO con datos Sentinel-2):

| Índice | Correlación de Pearson con rendimiento |
|---|---|
| savi_promedio | **0.317** |
| ndvi_promedio | **0.283** |
| evi_promedio | 0.252 |
| lai_promedio | 0.115 |
| msi_promedio | 0.063 |
| ndwi_promedio | -0.059 |

Los índices de vigor vegetal (SAVI, NDVI, EVI) muestran una correlación positiva moderada con el rendimiento incluso con un promedio temporal "ingenuo" (todas las fechas mezcladas, sin distinguir etapa fenológica). Esto sugiere que restringir el promedio a ventanas fenológicas relevantes (p. ej. floración/llenado de grano) probablemente mejore sustancialmente la señal predictiva.

Figura: `02_scatter_ndvi_vs_rendimiento.png`.

## Hallazgos clave
1. El "missing" está mayormente explicado por dos causas estructurales y documentables: separación por sensor (NDVI vs VI6T) y nubosidad 100% (MNAR pero determinístico). Ninguna requiere imputación clásica.
2. Fuerte estacionalidad del faltante por nubosidad, concentrada en meses de lluvia — relevante para decidir ventanas de composición temporal (compuestos mensuales/estacionales) en vez de usar observaciones individuales.
3. LAI con valores negativos es una anomalía a documentar, no necesariamente un error.
4. Ya con un promedio temporal simple, SAVI/NDVI/EVI muestran señal razonable hacia el rendimiento — buen punto de partida para features más sofisticadas (fenológicas, por trimestre, etc.).

## Dudas / sugerencias para los organizadores
- Confirmar si el faltante de VI6T en Landsat (36.1%) también está ligado a nubosidad, o si responde a otro criterio de calidad de escena Landsat no capturado en `porcentaje_nubosidad` (el dataset no reporta nubosidad separada por sensor de forma explícita en filas Landsat con NA generalizado — valdría confirmar que el campo de nubosidad aplica igual a ambos sensores).
- Preguntar si el rango negativo de LAI es esperado por el algoritmo del proveedor o si debe tratarse como ruido a truncar.
- Consultar si existe una recomendación oficial de ventana fenológica (p. ej. meses de floración/llenado de grano de cebada en la región) para construir agregados más informativos que el promedio anual completo.
