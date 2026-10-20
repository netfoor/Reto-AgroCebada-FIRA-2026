# EDA — Raster de precipitación mensual CHIRPS (2022–2025)

Script: `outputs/scripts/06_raster_precipitacion.R` · Log: `outputs/logs/06_raster_precipitacion.log`

## 1. Estructura del raster

- 48 archivos GeoTIFF mensuales (`PREC_AAAA_MM.tif`), 2022–2025, 12 meses × 4 años — completo, sin huecos.
- Extensión: lon [-99.95, -96.70], lat [17.80, 21.40] · resolución 0.05° (~5.5 km, resolución nativa CHIRPS).
- Dimensiones: 72 filas × 65 columnas · CRS: WGS 84 (EPSG:4326).

## 2. Cruce con el shapefile de parcelas

- Extracción con `terra::extract(..., fun = mean, exact = TRUE)` (promedio ponderado por fracción de píxel
  cubierta por cada parcela): 197 parcelas × 48 meses = 9,456 filas, **0 valores NA** — todas las parcelas
  cayeron dentro de la cobertura del raster.
- El chequeo de igualdad de CRS en el script imprime `FALSE`. Esto es una comparación de cadenas WKT
  (la del shapefile trae metadatos ligeramente distintos a la del raster aunque ambos son WGS84), **no un
  desalineamiento real**: la extracción sin NAs y la ubicación geográfica correcta de las parcelas dentro
  del extent confirman que ambos están en el mismo sistema de referencia. `terra::extract()` reproyecta
  automáticamente el vector si detecta una discrepancia real de CRS.

## 3. Estadísticos descriptivos

- Precipitación mensual por parcela: media 69.5 mm, mediana 38.2 mm, rango 0–392 mm (distribución con
  cola larga a la derecha, esperable en un régimen de lluvias estacional con meses secos en invierno).
- Precipitación acumulada anual por parcela: tendencia creciente año con año — media 609 mm (2022), 668 mm
  (2023), 1,006 mm (2024), 1,054 mm (2025). **2024 y 2025 fueron sustancialmente más lluviosos que
  2022–2023** (~65% más precipitación anual).
- Outliers (regla IQR 1.5×): 263 de 9,456 observaciones parcela-mes (2.8%), concentrados en **julio 2024**
  (162 de 263, 62% del total) y, en menor medida, junio y septiembre de 2024–2025 — consistente con el salto
  de precipitación anual observado en 2024.

## 4. Relación preliminar con el rendimiento (ENTRENAMIENTO)

- Se acumuló la precipitación de abril–octubre 2025 (ciclo productivo típico) por parcela y se cruzó con
  `RENDIMIENTO_T_HA` de las parcelas de ENTRENAMIENTO.
- Correlación: **-0.469** — relación negativa moderada. Contraintuitivo a primera vista (más lluvia,
  menor rendimiento), pero plausible si el exceso de precipitación en 2025 (el año más lluvioso de la
  serie) generó anegamiento, enfermedades fúngicas o pérdida de nitrógeno en cebada, o si hay factores de
  confusión (parcelas con mayor precipitación pueden coincidir con otra característica agronómica no
  observada aquí).

## Hallazgos clave

- Cobertura temporal y espacial completa, sin necesidad de imputación.
- Salto marcado de precipitación en 2024–2025 vs. 2022–2023 — variable temporal relevante que un modelo
  de rendimiento debería capturar (no asumir un régimen estable).
- Correlación negativa con rendimiento (-0.47) contraria a la intuición simple "más lluvia = más
  rendimiento" — amerita explorar con variables adicionales (temperatura, fecha de siembra) antes de
  sacar conclusiones causales.

## Dudas / sugerencias metodológicas

- ¿La ventana abril–octubre es la ventana de ciclo de cultivo correcta para cebada en esta zona, o los
  organizadores tienen fechas de siembra/cosecha específicas por parcela?
- Verificar si el exceso de precipitación de 2024–2025 coincide con años de menor rendimiento reportado en
  el dataset (solo se pudo cruzar 2025 porque es el único año con rendimiento en `ID_area_rendimiento`).
- Considerar variables derivadas (precipitación acumulada por sub-periodo, días con lluvia intensa) en
  lugar de solo el total del ciclo, dado que la relación simple es débil/contraintuitiva.
