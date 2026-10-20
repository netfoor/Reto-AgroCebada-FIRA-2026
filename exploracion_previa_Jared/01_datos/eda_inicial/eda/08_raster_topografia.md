# EDA — Rasters de topografía: elevación y pendiente (INEGI CEM4, 120 m)

Script: `outputs/scripts/08_raster_topografia.R` · Log: `outputs/logs/08_raster_topografia.log`

## 1. Estructura del raster

- Dos rasters de una sola capa cada uno, 120 m de resolución nativa, 3,362 × 2,900 celdas.
- CRS: **EPSG:6372 (México ITRF2008 / LCC)**, proyectado — distinto del WGS84 (EPSG:4326) del shapefile de
  parcelas y de los rasters climáticos. `terra::extract()` lo detecta y reproyecta el vector de parcelas
  automáticamente antes de extraer (confirmado por el aviso `[extract] transforming vector data to the CRS
  of the raster` en el log) — **este es el mismo mecanismo que ya operaba silenciosamente en los rasters
  de precipitación/temperatura**, y aquí queda documentado de forma explícita en el log.
- NODATA declarado: -9999. Control de calidad del proveedor (LEEME.txt): elevación 8–5,608 m s.n.m. media
  1,828 m; pendiente 0–70.6° media 10.2° — rango completo del INEGI CEM4 para Hidalgo/Puebla/Tlaxcala, no
  el subconjunto de las parcelas del reto.

## 2. Cruce con el shapefile de parcelas

- 197 parcelas, **0 valores NA** en elevación y pendiente extraídas.

## 3. Estadísticos descriptivos (a nivel de las 197 parcelas del reto)

- Elevación media por parcela: 2,497–2,906 m s.n.m., media 2,667 m — rango mucho más angosto que el rango
  completo del insumo INEGI (8–5,608 m), como se espera al acotar a la zona agrícola de Españita, Tlaxcala.
- Pendiente media por parcela: 0.28°–9.40°, media 2.79° — terreno mayormente plano a suavemente ondulado,
  consistente con parcelas agrícolas.
- Outliers (IQR 1.5×): 3 parcelas en elevación, 2 en pendiente (**AGC_060**: 9.40°, **AGC_057**: 8.24°) —
  ambas notablemente más inclinadas que el resto; vale la pena verificarlas visualmente en el mapa de
  parcelas si se van a usar variables de pendiente en el modelo.

## 4. Relación preliminar con el rendimiento (ENTRENAMIENTO)

- Correlación elevación vs. rendimiento: **+0.290** (positiva, débil).
- Correlación pendiente vs. rendimiento: **+0.311** (positiva, débil).
- Ambas señales son más débiles que Tmin (+0.61) pero del mismo orden que Tmax o precipitación — es
  probable que elevación y pendiente actúen como proxies indirectos de microclima (parcelas más altas o
  con más pendiente podrían tener temperaturas distintas) en lugar de un efecto agronómico directo.

## Hallazgos clave

- Datos completos, sin NA, y coherentes con el control de calidad del proveedor.
- El desajuste de CRS entre el raster de topografía (proyectado, EPSG:6372) y las parcelas (geográfico,
  EPSG:4326) es real (a diferencia del falso positivo notado en precipitación) pero **`terra::extract()`
  lo resuelve automáticamente y de forma correcta** — no requiere reproyección manual previa.
- Dos parcelas (AGC_060, AGC_057) se distinguen por pendiente notablemente mayor al resto — candidatas a
  revisión conjunta con los outliers de área/rendimiento ya detectados en otros archivos.
- Elevación y pendiente muestran correlaciones débiles-positivas con el rendimiento, menores que la
  temperatura mínima pero no despreciables.

## Dudas / sugerencias metodológicas

- Confirmar si conviene usar elevación/pendiente directamente en el modelo o solo como variables de
  control/interacción, dado que su señal es débil comparada con Tmin.
- Preguntar si existe un DEM de mayor resolución o corregido hidrológicamente que sea preferible al CEM4
  de 120 m para pendiente, dado que el tamaño de parcela puede ser menor a la celda del raster (120×120 m)
  y el promedio por parcela podría estar suavizando variabilidad interna real.
