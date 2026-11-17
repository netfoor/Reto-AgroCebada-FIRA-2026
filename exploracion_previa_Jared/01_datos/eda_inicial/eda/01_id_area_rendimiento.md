# EDA — ID_area_rendimiento_70_30_Reto_AgroCebada.csv

Script: `outputs/scripts/01_id_area_rendimiento.R`

## Estructura
- 197 filas × 4 columnas útiles (`ID_POLIGONO`, `AREA_HA`, `RENDIMIENTO_T_HA`, `CONJUNTO`); el CSV trae una 5ª columna vacía por una coma sobrante al final de cada línea (se descarta).
- 197 `ID_POLIGONO` únicos, sin duplicados.
- `CONJUNTO`: 138 ENTRENAMIENTO / 59 PREDICCION (coincide con lo documentado: 70/30).

## Datos faltantes
- `AREA_HA`: 0 faltantes (todas las 197 parcelas tienen área).
- `RENDIMIENTO_T_HA`: 59 faltantes, y coinciden exactamente con las 59 parcelas de `CONJUNTO == PREDICCION`. **No es un dato faltante real**, es el target oculto que hay que estimar — no debe tratarse como missing data para imputación.

## Distribución de AREA_HA (todas las parcelas, n=197)
- Media 6.60 ha, mediana 5.46 ha, rango 0.35–64.30 ha, sd 7.44 ha.
- Distribución con cola larga a la derecha (pocas parcelas muy grandes). Media > mediana confirma asimetría positiva.
- 11 parcelas marcadas como outlier por regla IQR 1.5×, la mayoría entre 18–25 ha y dos casos extremos: **AGC_047 (64.3 ha, ENTRENAMIENTO)** y **AGC_065 (60.9 ha, PREDICCION)**. No hay evidencia de error de captura (son áreas plausibles para parcelas agrícolas grandes), pero conviene vigilar su influencia (leverage) en cualquier modelo lineal por área.
- ENTRENAMIENTO y PREDICCION tienen distribuciones de área muy similares (medias 6.58 vs 6.67 ha) → el split 70/30 no introduce sesgo evidente de tamaño de parcela.

Figuras: `outputs/figuras/01_hist_area_ha.png`, `01_box_area_por_conjunto.png`.

## Distribución de RENDIMIENTO_T_HA (solo ENTRENAMIENTO, n=138)
- Rango 2.00–5.59 t/ha, media 3.96, mediana 4.34, sd 0.85.
- Media < mediana → ligera asimetría negativa (cola hacia rendimientos bajos).
- Sin outliers evidentes por regla IQR 1.5×.

Figura: `outputs/figuras/01_hist_rendimiento_entrenamiento.png`.

## Relación Área vs Rendimiento (ENTRENAMIENTO)
- Correlación de Pearson: **-0.078** → prácticamente nula. El área de la parcela por sí sola no explica el rendimiento por hectárea (razonable: rendimiento es una variable normalizada por área, no se espera relación mecánica fuerte).

Figura: `outputs/figuras/01_scatter_area_vs_rendimiento.png`.

## Hallazgos clave
1. El archivo está limpio: sin duplicados, sin inconsistencias de ID, sin missing real en el target de entrenamiento.
2. El "faltante" en rendimiento es 100% explicado por el diseño del reto (target oculto de PREDICCION) — cualquier pipeline de limpieza debe excluir esta columna del tratamiento genérico de NA.
3. Área y rendimiento no están correlacionados linealmente; el área no debería usarse como proxy directo del rendimiento, aunque sí puede ser útil como variable de control o para ponderar heterogeneidad espacial.
4. Existen parcelas grandes (>18 ha) en ambos conjuntos que actúan como outliers de área — vigilar su influencia en modelos sensibles a leverage (regresión lineal, KNN con distancias no normalizadas).

## Dudas / sugerencias para los organizadores
- Confirmar si el rendimiento en PREDICCION realmente no está disponible en ninguna fuente auxiliar (evidente, pero vale confirmarlo formalmente).
- Preguntar si las parcelas outlier de área (AGC_047, AGC_065, etc.) corresponden a polígonos verificados en campo o si podrían incluir errores de digitalización (unión accidental de polígonos vecinos).
