# Notas de la familia 3: compuestos satelitales sin nubes (prefijo satc_)

Script: `preparacion/scripts/53_variables_sat_compuestos.R` (log en `resultados/logs/53_variables_sat_compuestos.log`). No se abrió ningún archivo con rendimiento.

## Qué se construyó (40 variables, el tope)
- 28 compuestos mensuales abril a octubre de 2025: NDVI y SAVI de Sentinel-2 (`_s2`), NDVI y MSAVI de Planet (`_planet`). Compuesto = mediana del promedio de parcela con nubosidad < 20 y valor no vacío; sin observación válida sería NA.
- 2 máximos del ciclo de NDVI (HA3): `satc_ndvi_max_ciclo_s2` y `_planet` (máximo de las medianas mensuales).
- 8 promedios de compuestos por ventana B (jun-jul) y C (ago-sep), 2 índices por 2 sensores.
- 2 de calidad: `satc_nobs_s2_ciclo`, `satc_nobs_planet_ciclo` (observaciones sin nubes de abril a octubre).
- 9 hipótesis: 2 ya registradas (HA3, HR12) y 7 nuevas (HS1 a HS7). Cada variable está en una sola hipótesis.
- Los nombres de HR12 se reutilizaron tal como se pidieron (`satc_ndvi_s2_m08`, etc.); en el registro HA3 y HR12 usan otros nombres (`ndvi_max_ciclo_s2`, `ndvi_comp_ago`...), hay que mapearlos.

## Decisiones y por qué
- Ningún mes tiene NA: las 197 parcelas tienen compuesto válido en los 7 meses y en los 2 sensores. La regla de excluir meses con más de 60% de NA no se activó; se conservaron los 28.
- `satc_meses_validos_s2` y `_planet` salen constantes (7 en las 197), así que por la regla "ninguna columna constante" no van en las features. Las reemplacé por el conteo de observaciones sin nubes (HS7), que sí varía (S2: 26 a 42; Planet: 56 a 96). Es una decisión mía, avísame si prefieres otra.
- El NA "cero" no significa que no haya nubes: hay meses con pocas imágenes (S2 en junio: mediana 2 observaciones, mínimo 1; en junio y septiembre 6% y 5% de las parcelas tienen un compuesto de una sola imagen; ver `sat_compuestos_calidad_mes.csv`). Una mediana de 1 o 2 imágenes es más ruidosa que una de 7.
- Promedios de ventana: se promedian los meses con compuesto (hoy son los 2 siempre) y sería NA solo si ninguno lo tiene. Máximo del ciclo: máximo de medianas mensuales, no de observaciones sueltas.
- Sin LAI en esta familia, así que no hubo negativos que recortar.
- Sensibilidad (<10 contra <20, archivo `sat_compuestos_sensibilidad_umbral10.csv`): sin NA en ambos; cambian entre 25 y 68 parcelas por variable, con diferencia máxima de 0.08 y correlación de 0.98 a 0.999 con las versiones principales. El umbral 20 no se ajustó viendo esto.
- Verificaciones: fechas dd/mm/aaaa coinciden en las 107,666 filas con las fechas ISO de `basico_metadatos_observaciones.csv`; el sensor se filtra con igualdad exacta ("Sentinel-2", "Planet"; Landsat no entra). Observaciones válidas por parcela-mes: S2 4.67, Planet 11.5 en promedio.

## Lo que NO hice
- No evalué nada contra el rendimiento ni escribí en el registro de experimentos.
- No usé Landsat, EVI, LAI, desviaciones (_std) ni máximos/mínimos dentro de parcela.
- No interpolé ni imputé; no construí diferencias ni pendientes entre meses (se pueden probar con `spec`, por ejemplo `satc_ndvi_s2_c_prom + satc_ndvi_s2_b_prom`, sin variables nuevas).
- No agregué máximos de SAVI/MSAVI por el tope de 40.

## Avisos (no corregí nada)
- El máximo de NDVI de S2 nunca pasa de 0.8 (0 parcelas) y en Planet 21 parcelas pasan de 0.8: la saturación afecta poco, sobre todo en S2 [CP].
- En S2, los compuestos de agosto y septiembre casi no se correlacionan entre sí (r = -0.03), aunque cada uno se correlaciona 0.87 con el promedio C. Con 3 a 7 imágenes por mes, el desfase de fechas o una sola imagen distinta mueve mucho el compuesto; hay que mirarlo antes de interpretar HR12 mes por mes. S2 y Planet coinciden bien en la ventana C (r = 0.95).
- El pico del NDVI mensual cae en agosto-septiembre en 162 de 197 parcelas (S2) y 177 (Planet), coherente con siembra en mayo-junio [PV].
- El conteo de observaciones varía por grupo (Singuilucan tiene menos en Planet: media 64.5 contra 78 a 88), es decir depende de región y órbita; por eso HS7 es solo control de calidad.
- `basico_metadatos_observaciones.csv` difiere del original en 83 filas de S2 por ruido de punto flotante (1e-14) en la nubosidad; irrelevante para el umbral.
- 3,056 filas de Landsat traen nubosidad NA (no afecta esta familia).

## Preguntas para Jared
1. ¿Aceptas reemplazar `satc_meses_validos_*` (constantes) por `satc_nobs_*_ciclo`, o prefieres dejar solo la constancia documentada?
2. HS3 (promedio C) es casi redundante con HR12 y HS1: en el arnes conviene probar una u otra, no las dos, para no inflar el número de pruebas.
3. HS4, HS5 y HS6 son exploratorias con signo "ninguno" (20 variables). ¿Las quieres en la tanda principal o solo como perfil descriptivo?
