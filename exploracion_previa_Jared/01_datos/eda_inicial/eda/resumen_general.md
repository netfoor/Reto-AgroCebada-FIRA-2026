# Resumen general del EDA — Reto AgroCebada FIRA 2026

Este documento consolida los hallazgos de los 8 análisis individuales realizados sobre el dataset del reto.
Cada sección remite al `.md` detallado correspondiente y a los scripts/figuras que lo respaldan.

| # | Archivo analizado | Reporte detallado | Script |
|---|---|---|---|
| 1 | ID_area_rendimiento_70_30 | `01_id_area_rendimiento.md` | `01_id_area_rendimiento.R` |
| 2 | Dataset Básico (Sentinel-2/Landsat) | `02_dataset_basico.md` | `02_dataset_basico.R` |
| 3 | Dataset PRO (Planet) | `03_dataset_pro.md` | `03_dataset_pro.R` |
| 4 | Comparación Básico vs PRO | `04_comparacion_basico_pro.md` | `04_comparacion_basico_pro.R` |
| 5 | Shapefile de parcelas | `05_shapefile_parcelas.md` | `05_shapefile_parcelas.R` |
| 6 | Raster precipitación CHIRPS | `06_raster_precipitacion.md` | `06_raster_precipitacion.R` |
| 7 | Raster temperatura Tmax/Tmin | `07_raster_temperatura.md` | `07_raster_temperatura.R` |
| 8 | Raster topografía (elevación/pendiente) | `08_raster_topografia.md` | `08_raster_topografia.R` |

## 1. Estructura general del dataset

- **197 parcelas** en total, confirmadas de forma consistente en los 3 archivos que las enumeran
  (shapefile, ID_area_rendimiento, y presencia en ambos datasets satelitales): **138 ENTRENOMIENTO / 59
  PREDICCION** (split 70/30 exacto, sin discrepancias entre archivos).
- El **rendimiento (`RENDIMIENTO_T_HA`)** solo existe para ENTRENAMIENTO — el 100% del "faltante" en
  PREDICCION es el target oculto del reto, no un dato perdido real.
- Dos fuentes satelitales **no comparables directamente**: Básico (Sentinel-2 + Landsat, 2022–2025, mayor
  profundidad histórica) y PRO (Planet, solo 2025, mayor densidad temporal). Índices con el mismo nombre
  (NDVI, LAI, EVI) tienen **escalas distintas entre sensores** (LAI difiere ~8× en media) — deben tratarse
  como variables separadas, nunca fusionadas por nombre.
- Tres fuentes climáticas/topográficas rasterizadas (precipitación CHIRPS, temperatura Tmax/Tmin,
  topografía INEGI) con cobertura completa (0% NA tras cruce espacial con las 197 parcelas) y consistentes
  internamente (Tmax ≥ Tmin siempre; ninguna parcela fuera del extent de los rasters climáticos).

## 2. Calidad de datos — hallazgos transversales

- **Sin duplicados ni IDs huérfanos** en ningún archivo; los 197 `ID_POLIGONO` son consistentes en las 8
  fuentes revisadas.
- **Datos faltantes en los índices satelitales son estructurales, no aleatorios**: explicados casi
  perfectamente por `porcentaje_nubosidad = 100%` (mismo mecanismo, confirmado de forma idéntica en Básico
  y PRO). Implicación metodológica: **no imputar** estas observaciones; excluirlas o resolver con
  compuestos temporales/interpolación explícita.
- **Anomalías menores documentadas, no corregidas automáticamente** (se deja explícito para que el
  colectivo/equipo decida):
  - `lai_promedio` con valores negativos en ambos datasets satelitales (Básico y PRO) — fuera del rango
    conceptual del índice.
  - 2 geometrías inválidas por vértice duplicado en el shapefile (AGC_070, AGC_078) — no afectan el área
    reportada, corregibles con `st_make_valid()`.
  - Inconsistencia de mayúsculas en el campo `Cultivo` ("Cebada" vs "CEBADA").
  - Sesgo sistemático pequeño (~0.68%) entre el área del atributo del shapefile y el área geométrica
    recalculada — no es un error, pero conviene decidir cuál se considera oficial.
- **Outliers evidentes** identificados por regla IQR en área de parcela (11 casos, notablemente
  AGC_047 y AGC_065), en pendiente (AGC_060, AGC_057), y en múltiples índices satelitales — en estos
  últimos, el volumen alto de outliers es interpretado como **variabilidad fenológica real**, no error de
  captura, dado el fuerte componente estacional de las series de 4 años.

## 3. Relación preliminar de cada fuente con el rendimiento (solo ENTRENAMIENTO)

Vista comparativa de todas las correlaciones de Pearson calculadas contra `RENDIMIENTO_T_HA`, usando
promedios simples por parcela (sin distinguir aún fenología ni ventanas óptimas):

| Variable | Fuente | Correlación | Comentario |
|---|---|---|---|
| Tmin medio del ciclo (abr–oct 2025) | Temperatura | **+0.610** | Señal más fuerte encontrada |
| SAVI promedio (todo el periodo) | Básico (S2) | +0.317 | Mejor índice satelital individual |
| Pendiente | Topografía | +0.311 | Débil |
| NDVI promedio (todo el periodo) | Básico (S2) | +0.283 | — |
| EVI promedio (todo el periodo) | Básico (S2) | +0.252 | — |
| Elevación | Topografía | +0.290 | Débil |
| EVI promedio (2025) | PRO (Planet) | +0.200 | Más débil que su análogo en Básico |
| MSAVI promedio (2025) | PRO (Planet) | +0.199 | — |
| NDVI promedio (2025) | PRO (Planet) | +0.161 | — |
| Tmax medio del ciclo (abr–oct 2025) | Temperatura | -0.285 | Negativa moderada |
| Precipitación acumulada (abr–oct 2025) | Precipitación | -0.469 | Negativa moderada, contraintuitiva |
| LAI promedio | Básico / PRO | +0.115 / +0.136 | Débil en ambos |
| Área de la parcela | ID_area_rendimiento | -0.078 | Prácticamente nula |

**Lectura conjunta:** la señal más fuerte y consistente hasta ahora es climática (Tmin), no satelital —
sugiere que el rendimiento en esta zona está más limitado por condiciones térmicas (posible riesgo de
heladas/noches frías) que por vigor vegetal medido vía índices. Entre los satelitales, el Dataset Básico
(con su profundidad histórica de 4 años) predice mejor que PRO (solo 2025), pese a que PRO cubre
exactamente el ciclo evaluado — hipótesis: el promedio multianual del Básico captura mejor características
estructurales/de manejo de cada parcela que se correlacionan con su potencial productivo. Ninguna
correlación individual supera 0.65; se espera que el poder predictivo real venga de combinar variables
(fenología + clima + topografía) más que de una sola fuente.

## 4. Dudas metodológicas más relevantes para los organizadores

Consolidando las dudas planteadas en cada análisis individual, por prioridad:

1. **Ventana de ciclo productivo:** se asumió abril–octubre 2025 para todas las relaciones preliminares
   con rendimiento. ¿Existe una fecha de siembra/cosecha oficial por parcela, o una ventana fenológica
   recomendada (floración, llenado de grano) que debiera usarse en vez de un promedio simple de 7 meses?
2. **Escalas no comparables entre sensores:** ¿existe algún factor de calibración cruzada publicado entre
   Planet (PRO) y Sentinel-2/Landsat (Básico) para los índices homónimos, o se espera que los equipos los
   traten siempre como variables independientes? ¿Aplica esta restricción también a features combinadas
   (no solo a fusión directa de filas)?
3. **Faltante de VI6T en Landsat (36.1%):** ¿responde también a nubosidad (como en Sentinel-2/Planet) o a
   otro criterio de calidad de escena no capturado explícitamente en `porcentaje_nubosidad`?
4. **LAI con valores negativos** en ambos datasets satelitales: ¿es un comportamiento esperado del
   algoritmo del proveedor o debe tratarse como ruido a truncar en 0?
5. **Área del shapefile vs área geométrica:** el atributo `área_ha` es sistemáticamente ~0.68% menor que
   el área recalculada geométricamente. ¿Cuál debe considerarse la fuente oficial para normalizar
   rendimiento?
6. **Geometrías inválidas** (AGC_070, AGC_078, vértice duplicado): ¿los organizadores desean corregir el
   shapefile fuente, o basta con `st_make_valid()` de nuestro lado?
7. **Correlación negativa de precipitación con rendimiento (-0.469):** dado que 2025 fue el año más
   lluvioso de la serie (2022–2025), ¿hay registros de anegamiento, enfermedades o pérdida de nutrientes
   reportados por el colectivo agronómico que expliquen esta relación contraintuitiva?
8. **Resolución del DEM (120 m):** ¿existe un insumo topográfico de mayor resolución, dado que varias
   parcelas son más pequeñas que una celda del raster (120×120 m) y el promedio por parcela podría estar
   suavizando variabilidad real de pendiente/elevación?

## 5. Sugerencias metodológicas generales para el modelado

- Tratar Básico y PRO como **familias de variables separadas** (sufijo por sensor), no fusionarlas por
  nombre de índice.
- Excluir observaciones con nubosidad ~100% en vez de imputar; considerar compuestos mensuales/estacionales
  para suavizar el patrón de faltante estacional (pico en meses de lluvia).
- Explorar agregados de temperatura más allá del promedio simple (grados-día, conteo de noches frías) dado
  que Tmin ya muestra la señal más fuerte con promedios ingenuos.
- Vigilar leverage de outliers de área y de pendiente en modelos sensibles a valores extremos.
- Normalizar el campo `Cultivo` y decidir la fuente oficial de área antes de construir features derivadas
  de rendimiento por hectárea.
- Dado que ninguna variable individual supera |r|=0.65, priorizar modelos que combinen features de las
  distintas fuentes (satelital + clima + topografía) sobre modelos univariados.
