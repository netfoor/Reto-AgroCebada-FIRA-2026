# EDA — Conjunto_datos_PRO_AgroCebada.csv (Planet, 2025)

Script: `outputs/scripts/03_dataset_pro.R`

## Estructura general
- 47,804 filas × 22 columnas: `ID_POLIGONO`, `fecha_captura`, `sensor` (único valor: Planet), 4 índices × 4 estadísticos (NDVI, EVI, LAI, MSAVI) + `porcentaje_nubosidad`.
- Cobertura temporal: solo **2025** (2025-01-01 a 2025-12-30, 311 fechas distintas) — a diferencia del Básico, no cubre 2022–2024.
- Las 197 parcelas tienen observaciones PRO (cobertura completa).

## Datos faltantes
- Los 4 índices comparten exactamente el mismo % de NA (25.2%, 12,057 filas) — se calculan siempre juntos por observación.
- **Mismo mecanismo que en el Dataset Básico:** cuando el índice es NA, la mediana de `porcentaje_nubosidad` es 100%; cuando está presente, es 0% (media 6.53 vs 100). Confirma que el filtrado por nubosidad total explica el faltante en ambos datasets, de forma consistente.
- `porcentaje_nubosidad` no tiene NA en este archivo (a diferencia del Básico, que tenía 2.8% de NA en esa columna).
- Concentración por parcela: peor caso AGC_067 con 37.0% de NA en NDVI; top-10 entre 33.7% y 37.0% — algo más alto que en el Básico (máximo 30.2%), consistente con que Planet es de mayor resolución y más sensible a nubes parciales/sombras.
- Concentración temporal: pico de faltante en septiembre (46.0%) y junio (44.8%), mínimos en marzo (4.4%) y abril (6.0%) — patrón estacional de nubosidad consistente con el observado en el Básico.

Figuras: `03_hist_obs_por_parcela_pro.png`, `03_hist_nubosidad_pro.png`.

## Distribución de índices clave
- NDVI: 0.007–0.907, media 0.354, mediana 0.275.
- EVI: 0.028–0.877, media 0.215.
- LAI: **-0.112 a 3.66, media 1.22**, mediana 0.962.
- MSAVI: 0.010–0.780, media 0.211.

Figura: `03_hist_indices_clave_pro.png`.

## Outliers (regla IQR 1.5×)
| Índice | N outliers |
|---|---|
| ndvi_promedio | 492 |
| evi_promedio | 3,345 |
| lai_promedio | 1,609 |
| msavi_promedio | 3,073 |

## Observaciones por parcela
Min 233, mediana 243, media 242.7, max 251 — mucho más homogéneo que en el Básico, y con densidad temporal alta dado que Planet ofrece revisita casi diaria dentro de un solo año.

## Relación preliminar con rendimiento (solo ENTRENAMIENTO)
Con las 138 parcelas ENTRENAMIENTO y promedio simple de todo el periodo PRO (2025):

| Índice | Correlación de Pearson con rendimiento |
|---|---|
| evi_promedio | 0.200 |
| msavi_promedio | 0.199 |
| ndvi_promedio | 0.161 |
| lai_promedio | 0.136 |

Figura: `03_scatter_ndvi_vs_rendimiento_pro.png`.

## Hallazgos clave
1. El mecanismo de faltante (nubosidad 100% ⇒ índice NA) se replica de forma idéntica al Dataset Básico, lo que da confianza en tratarlo igual en ambos: **excluir, no imputar, esas observaciones**, o resolver con compuestos temporales.
2. El faltante por parcela es algo mayor que en el Básico (hasta 37% vs 30%), razonable dada la mayor sensibilidad de Planet a nubes parciales.
3. **La correlación preliminar con el rendimiento es más débil en PRO (máx. 0.200) que en el Básico (máx. 0.317 con SAVI)**, a pesar de que PRO cubre exactamente el año del ciclo de producción evaluado (2025) y con mayor densidad temporal — ver sección de comparación Básico vs PRO (`04_comparacion_basico_pro.md`) para hipótesis al respecto.
