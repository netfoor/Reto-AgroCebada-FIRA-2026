# EDA — Comparación Dataset Básico (Sentinel-2/Landsat) vs Dataset PRO (Planet)

Script: `outputs/scripts/04_comparacion_basico_pro.R`

## Cobertura temporal y de sensores
| | Básico | PRO |
|---|---|---|
| Filas | 107,666 | 47,804 |
| Parcelas | 197 | 197 |
| Periodo | 2022-01-01 a 2025-12-31 | 2025-01-01 a 2025-12-30 |
| Fechas distintas | 608 | 311 |
| Sensores | Landsat / Sentinel-2 | Planet |

El Básico cubre 4 años completos; PRO cubre únicamente 2025 (que coincide con el ciclo de producción evaluado, abril–octubre 2025).

## Observaciones por parcela
- Básico: min 494, mediana 511, media 546.5, max 692 (acumulado de 4 años).
- PRO: min 233, mediana 243, media 242.7, max 251 (un solo año, pero con revisita casi diaria — de ahí la densidad comparable o mayor en términos anuales).

Figura: `04_box_obs_basico_vs_pro.png`.

## Comparación de índices con el mismo nombre — NO son equivalentes
Restringiendo el Básico a Sentinel-2 (mismo sensor multiespectral óptico que Planet, para una comparación más justa que incluir Landsat):

| Índice | Media Básico (S2) | Media PRO (Planet) | Diferencia relativa |
|---|---|---|---|
| NDVI | 0.243 | 0.354 | **+45.6%** |
| EVI | 0.190 | 0.215 | +12.8% |
| LAI | 0.131 | 1.22 | **+828%** |

**Hallazgo crítico:** el LAI del Dataset PRO está en una escala completamente distinta al del Básico (media casi 10× mayor). El NDVI también difiere de forma no trivial (+45.6%). Esto **confirma explícitamente** la advertencia del Diccionario de índices satelitales: aunque el nombre del índice coincide, los valores provienen de sensores/algoritmos distintos (Sentinel-2 vs Planet) y **no deben tratarse como la misma variable ni fusionarse/promediarse directamente**. Cualquier feature engineering que use LAI o NDVI debe mantener el origen del sensor como parte del nombre de la variable (p. ej. `ndvi_s2` vs `ndvi_planet`) y, si se combinan en un modelo, hacerlo como variables separadas o mediante una normalización/calibración explícita y documentada — nunca por concatenación simple de filas.

Figura: `04_box_indices_comunes_basico_vs_pro.png`.

## Comparación restringida al periodo de solapamiento real (2025)
Cuando se comparan solo las observaciones de 2025 (único año donde ambos datasets coexisten), las diferencias de escala se mantienen: NDVI 0.289 (Básico S2) vs 0.354 (PRO), LAI 0.204 vs 1.22. Es decir, la discrepancia **no se debe a que comparen años distintos**, sino al sensor/algoritmo en sí.

## Hallazgos clave
1. PRO es el único dataset satelital que cubre exactamente el ciclo de producción evaluado (abril–octubre 2025), lo que lo hace atractivo por relevancia temporal, pero su cobertura histórica es nula (no permite construir baselines multianuales por parcela).
2. Básico aporta profundidad histórica (2022–2025) y dos sensores (Sentinel-2 + Landsat/VI6T), útil para tendencias y estacionalidad de largo plazo, pero con menor densidad de observaciones que PRO durante 2025.
3. Las diferencias de escala entre índices homónimos son sustanciales, sobre todo en LAI — deben tratarse como variables distintas en el modelado, consistente con la instrucción explícita del dataset de no fusionarlos automáticamente.
4. Pese a que PRO cubre el año exacto del rendimiento, su correlación preliminar con rendimiento fue más débil que la del Básico (ver `02_dataset_basico.md` y `03_dataset_pro.md`) — posiblemente porque el Básico, al promediar 4 años, captura mejor el "carácter" estructural de cada parcela (suelo, pendiente, manejo histórico) que se correlaciona con su potencial productivo, mientras que PRO captura solo la variabilidad de una temporada. Vale la pena probar ambos como fuentes de features complementarias (Básico para features estructurales/históricas, PRO para dinámica fenológica fina del ciclo 2025) en vez de elegir uno solo.

## Dudas / sugerencias para los organizadores
- Confirmar si existe algún factor de calibración cruzada publicado entre Planet y Sentinel-2/Landsat para estos índices, o si efectivamente se espera que los equipos los traten como fuentes independientes sin intentar armonizarlos.
- Preguntar si el criterio de "no fusionar automáticamente" también aplica a construir features combinadas (p. ej. promedio ponderado NDVI_S2/NDVI_Planet) o si eso ya se consideraría fusión no permitida.
