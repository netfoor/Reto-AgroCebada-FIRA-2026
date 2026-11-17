# EDA — Rasters de temperatura mensual Tmax / Tmin (2022–2025)

Script: `outputs/scripts/07_raster_temperatura.R` · Log: `outputs/logs/07_raster_temperatura.log`

## 1. Estructura del raster

- Tmax y Tmin: 48 GeoTIFF mensuales cada uno (2022–2025, 12 meses × 4 años), completos sin huecos.
- Misma extensión, resolución (0.05°) y dimensiones (72×65) que el raster de precipitación — ambos
  productos comparten grilla, lo que simplifica cualquier combinación futura de variables climáticas.

## 2. Cruce con el shapefile de parcelas

- Extracción con `terra::extract(..., fun = mean, exact = TRUE)`: 197 parcelas × 48 meses = 9,456 filas
  para Tmax y Tmin combinadas, **0 valores NA** en ambas variables.
- **Chequeo de consistencia física**: 0 filas con Tmax < Tmin — el par de rasters es internamente
  consistente en las 9,456 observaciones.

## 3. Estadísticos descriptivos

- Tmax mensual por parcela: media 23.5 °C, rango 18.8–30.2 °C.
- Tmin mensual por parcela: media 11.2 °C, rango 5.4–16.3 °C.
- Amplitud térmica (Tmax−Tmin): media 12.3 °C, rango 7.5–17.8 °C — amplitud considerable, típica de zonas
  de clima templado/semiárido de altiplano.
- Outliers (IQR 1.5×): **137 en Tmax, 0 en Tmin** — Tmax tiene mayor variabilidad extrema mes a mes que
  Tmin, que se mantiene más estable.

## 4. Relación preliminar con el rendimiento (ENTRENAMIENTO)

Se promedió Tmax y Tmin de abril–octubre 2025 (mismo ciclo usado para precipitación) por parcela y se
cruzó con `RENDIMIENTO_T_HA` de ENTRENAMIENTO:

- Correlación Tmax medio del ciclo vs. rendimiento: **-0.285** (negativa, débil-moderada).
- Correlación Tmin medio del ciclo vs. rendimiento: **+0.610** (positiva, la más fuerte encontrada hasta
  ahora entre todas las variables climáticas/satelitales revisadas).

## Hallazgos clave

- Datos de temperatura completos y físicamente consistentes (sin NA, sin inversiones Tmax<Tmin) — no
  requieren limpieza previa al modelado.
- **Tmin es, con diferencia, la variable climática con la correlación más fuerte con el rendimiento hasta
  ahora (+0.61)** — más relevante que precipitación (-0.47) o Tmax (-0.29). Temperaturas mínimas más
  altas durante el ciclo (noches menos frías) se asocian con mayor rendimiento, lo cual es agronómicamente
  plausible en cebada de altiplano si el riesgo de heladas nocturnas limita el desarrollo del cultivo en
  las parcelas más frías.
- Tmax muestra 137 outliers mensuales (probablemente meses de ola de calor puntual) que conviene revisar
  si se usan estadísticos mensuales individuales en vez de promedios de ciclo.

## Dudas / sugerencias metodológicas

- Dado que Tmin explica más varianza que precipitación o Tmax, vale la pena preguntar a los organizadores
  si hay registros de heladas o de fechas de siembra por parcela — permitiría afinar la ventana de
  temperatura crítica (p. ej. solo meses de llenado de grano) en vez de un promedio simple abr–oct.
  Correlación reportada aquí es descriptiva a nivel de todas las parcelas.
- Confirmar con los organizadores si Tmax/Tmin provienen de la misma fuente/resolución que se usó para
  generar los índices satelitales, y si conviene usar variables derivadas (grados-día acumulados,
  n° de noches con Tmin bajo cierto umbral) en el modelo final en lugar de promedios simples.
