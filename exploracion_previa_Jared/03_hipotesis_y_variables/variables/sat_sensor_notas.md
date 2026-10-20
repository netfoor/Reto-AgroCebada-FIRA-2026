# Familia 4: variables satelitales separadas por sensor (script 54_variables_sat_sensor.R)

Total: 32 variables (tope 45): 15 de Sentinel-2 (ndvi, evi, savi, msi, ndwi en b, c, ciclo), lai_s2 de ciclo y su bandera, 12 de Planet, y 3 multianuales. Hipótesis: 13 (2 existentes, HR1 y HR2; 11 nuevas, HP1 a HP11). No leí rendimiento en ningún momento.

## Decisiones y por qué
- Regla única: promedio simple de `*_promedio` de las fechas con nubosidad < 20 y valor no vacío; si no hay, NA. Una nubosidad vacía no cuenta como válida (solo pasa en 3,056 filas de Landsat, que no uso).
- Nombres de ventana: b = B (jun-jul), c = C (ago-sep), ciclo = abr-oct, el mismo sufijo que usa la familia clim_* (`clim_precip_b`). Solo pedí B, C y CICLO; no construí A ni D.
- LAI: se recorta a 0 antes de promediar y se guarda `sat_lai_s2_ciclo_frac_neg`. En Planet, ninguna observación válida tiene LAI negativo, así que no hay bandera (una columna toda en 0 sería constante).
- HR1 y HR2 se operacionalizan como `sat_savi_s2_tipico_2022_2024` y `sat_cv_interanual_ndvi_s2` (el registro los llama `savi_s2_tipico_2022_2024` y `cv_interanual_ndvi`; el prefijo y el sufijo de sensor son obligatorios). CV con desviación estándar de n-1 sobre solo 3 datos, así que es ruidoso.
- Ventana principal declarada por hipótesis: CICLO, porque promedia más fechas y es la menos ruidosa. b y c son secundarias y no cuentan como confirmación aparte (así se evita elegir la mejor de tres ventanas después de mirar).
- Sin signo fijo (declarado desde ahora): HP5 (NDWI, fórmula desconocida), HP6 (LAI S2 y su bandera) y HP10 (LAI Planet) son controles o exploratorias.

## Observaciones válidas por parcela (mediana / mínimo)
| Sensor | b | c | ciclo 2025 | ciclo 2022 | ciclo 2023 | ciclo 2024 |
|---|---|---|---|---|---|---|
| Sentinel-2 | 8 / 4 | 9 / 6 | 32 / 26 | 21 / 17 | 24 / 18 | 25 / 15 |
| Planet | 13 / 5 | 22 / 12 | 82 / 56 | no aplica | no aplica | no aplica |

Tasa de NA: 0% en las 32 variables. Ninguna parcela quedó sin fechas válidas y ninguna tiene año NA en 2022-2024 (0 parcelas con NA en tipico, CV o desviación). Detalle en `sat_sensor_n_obs_resumen.csv`.

## Avisos
- La regla de nubosidad descarta 4,657 filas de Sentinel-2 que sí traían índices (nubosidad de 20% o más); no es un error, es la regla.
- Redundancia alta (correlación de rangos, ciclo, sin rendimiento): S2 SAVI con EVI 0.99, con LAI 0.95 y con NDVI 0.94; MSI con NDWI -0.96 (HP4 y HP5 casi son la misma señal); Planet EVI con MSAVI 0.99 y NDVI con LAI 0.96. Probarlas juntas en un mismo modelo no tiene sentido; conviene una por sensor o regularización.
- `sat_savi_s2_dev_2025` casi siempre es positivo (solo 1 parcela negativa) y se parece mucho al SAVI de 2025 (rangos 0.76): 2025 tuvo más vigor que 2022-2024 en casi todas. Buena parte de la variable es un efecto de año común y no de parcela; su aporte sobre `sat_savi_s2_ciclo` habrá que juzgarlo con cuidado.
- El LAI de S2 recortado y promediado correlaciona 0.95 con SAVI (no 0.9999 como el dato crudo): el recorte y el promedio rompen parte de la copia. Sigue siendo casi redundante.
- Comparación de orden de magnitud con los resúmenes sin filtro: los míos son más altos (S2 NDVI 0.36 contra 0.24; Planet NDVI 0.41 contra 0.35), lo esperado porque los resúmenes incluyen invierno y suelo desnudo fuera del ciclo. Correlación entre parcelas de 0.64 a 0.85.
- Las 17 parcelas de menos de 1.44 ha tienen menos píxeles de 10 m y un promedio más ruidoso; no se trataron aparte.

## Lo que NO hice
- No construí compuestos mensuales (familia 3), ni desviaciones (`_std`) ni máximos/mínimos dentro de parcela, ni variables de Landsat, ni ventanas A y D, ni mezclas de sensores.
- No probé nada contra el rendimiento ni elegí umbrales; no imputé.

## Preguntas para Jared
1. ¿Confirmas el sufijo de ventana b/c/ciclo (igual al de clim_*)? Si otra familia usa el mismo nombre de columna, debe tener la misma definición.
2. ¿Aceptas declarar CICLO como ventana principal de cada hipótesis satelital antes de probar?
3. ¿Se probará un modelo con S2 y Planet juntos? Cada variable tiene un solo sensor, pero la pregunta #2 del EDA (si eso es "fusión") sigue abierta.
4. HP4 y HP5 están casi duplicadas; ¿se mantienen las dos para no decidir a ojo?
