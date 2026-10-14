# Bitácora comparativa de hipótesis y presupuestos

Consolidada el 8 de octubre de 2026. **Seis rondas históricas, una séptima ejecutada después de planificación y registro, y cuatro rondas del 8 de octubre (EXP_08 exploratoria; EXP_09 y EXP_10 con registro previo; EXP_11 exploratoria con registro previo).** No crea preregistros retrospectivos ni modifica los criterios originales.

## Cómo leerla

Una ronda puede comparar varios procedimientos y tener réplicas. Un nuevo cuaderno de lectura no es una nueva ronda. Los seis lectores EXP_01–06 recalculan variables y/o métricas desde resultados guardados: **hacen cero ajustes nuevos**.

FULL138 puntúa 138 parcelas / 1,380 predicciones OOF por procedimiento. SEEN135 puntúa 135 / 1,350, excluyendo de la puntuación las validaciones cuyo municipio no estaba en entrenamiento; **no retira esas etiquetas de los entrenamientos**. Es principal desde EXP_05, no una corrección retrospectiva del protocolo de EXP_04.

MUN es la media municipal aprendida en entrenamiento. MIX combina 50 % MUN y 50 % IDW espacial fijo. E0/E2 usan Ridge con columnas municipales penalizadas y no son iguales a MUN. Comparar cifras de FULL y SEEN como si fueran la misma muestra sería incorrecto.

## Comparaciones cerradas

| ID y fecha real del trabajo | Pregunta y cambio | Control / evaluación | Conclusión y decisión |
|---|---|---|---|
| EXP_01 · 21 sep · RONDA1 | Añadir clima/topografía, satélite del ciclo, historia o todos los bloques. | E0 municipal Ridge; E1–E4. FULL138; MUN/MIX como referencias. | Historia reduce poco RMSE contra E0, empeora MAE y concentra la ganancia; no supera MIX. **Sin adopción.** |
| EXP_02 · 29 sep · T1 | Sustituir tres medias por captura por medias mensuales ponderadas por días. | E2 reconstruido frente a T1; restantes variables y modelo constantes. FULL138. | RMSE T1 0.5225, E2 0.5192, MIX 0.4938 t/ha. **Sin adopción.** No prueba inutilidad de toda representación temporal. |
| EXP_03 · 29 sep México · V1 | Añadir cuatro descriptores temporales y comparar Ridge/HGB en un diseño 2×2. | R_B/R_T y H_B/H_T; mismas particiones y entradas dentro de cada contraste. FULL138. | El bloque empeora Ridge; con HGB mejora algo RMSE y empeora MAE. **Sin adopción.** No descarta toda la familia de árboles. |
| EXP_04 · 1 oct · V2 | Lluvia octubre: porcentaje, mm, valor actual y agrupación de 5/9 regiones. | J5_PCT/J9_PCT/R9_PCT/R9_MM/R9_RAW; referencias comunes. FULL138 principal; SEEN posterior. | J5_PCT: RMSE 0.4797 y MAE 0.3291 en FULL; cumple su regla. En SEEN, MAE no cumple. Grupos cambian varios mecanismos y el beneficio se concentra. **Candidato con reservas, no adoptado.** |
| EXP_05 · 1 oct México · V3 | Separar histórico H, actual P, H+P y porcentaje. | R9_H/R9_HP/R9_P/R9_PCT; centrado municipal y Ridge comunes. SEEN principal / FULL secundario. | PCT RMSE 0.4851 vs MIX 0.4872 en SEEN, pero solo mejora en 6/10 repeticiones y empeora MAE vs MUN. H y HP quedan detrás. **Sin adopción.** |
| EXP_06 · 6 oct · V4 | Sustituir la fecha de máximo crudo por una fecha de pico soportado. | E2 frente a V4; mismas cinco variables restantes. SEEN principal / FULL secundario. | RMSE 0.5065 → 0.5015 en SEEN; MAE 0.3474 → 0.3476. MIX RMSE 0.4872. **Sin adopción.** Mejorar el control no basta. |
| EXP_07 · 8 oct · H7 | Añadir dispersión espacial NDVI sobre soporte pareado con la media. | C0/C1 con arquitectura municipal común; MUN/MIX fijos. SEEN principal / FULL secundario. | RMSE C0 0.494064, C1 0.494105, MIX 0.487197. C1 mejora C0 en 4/10. **Sin adopción**, incluso bajo el criterio prospectivo. |
| EXP_08 · 8 oct · contraste vecinal (Claude, a pedido de Fortino) | Diagnóstico de dónde está el error, barrido de señal con nulo por permutación y una hipótesis nueva: corregir MIX con β·(integral NDVI Planet − mediana de vecinas a <1 km). | MIX; selección honesta dentro del pliegue; nulos por permutación; réplica Sentinel-2 predeclarada (12:09 h). Particiones históricas, SEEN/FULL. | C1 0.4817 vs MIX 0.4872 en SEEN, 10/10 repeticiones; selección honesta 0.4831. Ganancia concentrada; MAE no ≤ MUN. **Exploratorio, sin protocolo ratificado.** Variable y radio elegidos tras ver etiquetas. |
| EXP_09 · 8 oct · fuentes externas (Claude, a pedido de Fortino) | Cinco contrastes vecinales con lista cerrada: K1 NDVI Planet al 31 oct, K2 NDRE propio, K3 radar VH/VV, K4 AlphaEarth, K5 historia; K6 combinado. | Registro previo (13:17 h) antes de cruzar variables nuevas con etiquetas. Particiones históricas y 50 nuevas (semilla 20261009). Nulo de familia de 6 candidatos. | K1 0.4816/0.4807 (históricas/nuevas) vs MIX 0.4872/0.4857; ninguna fuente externa lo supera; p de familia 0.13 > 0.10. **La regla recomendó MIX.** Fe de erratas: el corte al 31 oct se aplicaba después de suavizar (véase EXP_10). |
| EXP_10 · 8 oct · verificación (Claude, a pedido de Fortino) | Repetir K1 con el corte temporal bien implementado: capturas posteriores al 31/oct fuera **antes** de suavizar. | MUN, MIX, K1 publicado (control de reproducción) y K1 corregido. Ambos juegos de particiones. Nulos N0 (reproducción), N1 (permutación municipal) y N2 (aleatorización espectral de Moran). Registro previo 17:36 h. | K1 corregido 0.48198/0.48096 vs MIX 0.48720/0.48567; 20/20 repeticiones; MAE ≤ MIX; se invierte sin las 5 parcelas más favorecidas. p de familia 0.184 (N1) y 0.129 (N2). **Cumple los requisitos predictivos sin evidencia estadística suficiente: conservar MIX; K1 corregido como alternativa documentada.** |
| EXP_11 · 8 oct · combinación fija (Claude, a pedido de Fortino; exploratoria) | ¿E_JK = ½·Jared (procedimiento completo) + ½·(MIX+K1 corregido) mejora a sus componentes? Control E_MK = ½·MUN + ½·K. | Predicciones OOF existentes, 0 entrenamientos, ambos juegos de particiones, SEEN principal / FULL sensibilidad. Registro previo 22:32 h. Hipótesis posterior a ver resultados. | E_JK 0.4757/0.4744 vs K 0.4820/0.4810 y MIX 0.4872/0.4857; 10/10 vs K; MAE ≈ MUN (+0.0001/+0.0011). E_MK no supera a K. Frente a K, casi se anula sin 5 parcelas. **Clase C: candidato para revisión, sin adopción automática ni nulo estadístico.** |

Los resultados de V1/V3 conservan también sus fechas UTC; el día local anterior no representa otra corrida. Cada cuaderno muestra los controles, scores internos, OOF y límites correspondientes.

**Antecedente exploratorio, no séptima ronda controlada:** antes de EXP_01 se probaron 56 agregados de índices con Ridge y corrección municipal. Incluían NDVI/EVI/LAI/MSAVI Planet y diez índices del BÁSICO, con media/máximo/p90/suma y nubosidad ≤20 %. No incluían `*_std` satelital. Su columna `auc` era suma de capturas, no integral por tiempo; receta y métricas no son equivalentes a las actuales. Este antecedente impide afirmar que esos índices nunca fueron estudiados.

## Presupuestos históricos por corrida

Los números siguientes son los consignados en la evidencia histórica, no una nueva ejecución ni un recuento global de todos los procesos. **Una evaluación baseline sin Ridge no cuenta como ajuste Ridge.** Los controles y réplicas se separan.

| Ronda | Núcleo registrado por corrida | Controles y réplicas que no deben confundirse |
|---|---|---|
| EXP_01 | 5,000 ajustes internos + 250 exteriores. | Cinco procedimientos; auditorías y lectores no son candidatos adicionales. |
| EXP_02 | T1: 1,000 internos + 50 exteriores. | E2: otros 1,050 ajustes. Total de ambos: 2,100 por corrida. |
| EXP_03 | 2,000 internos Ridge + 1,600 internos HGB + 200 exteriores. | Total 3,800; las familias tuvieron rejillas/presupuestos diferentes. |
| EXP_04 | 3,600 evaluaciones internas = 600 baseline + 3,000 Ridge; 250 reconstrucciones exteriores. | Aparte: E2, 1,050 ajustes; cuatro referencias × 50 particiones; pruebas sintéticas. |
| EXP_05 | 4,800 evaluaciones internas = 800 baseline + 4,000 Ridge; 200 reconstrucciones exteriores. | 50 controles MUN. Corrida registrada, determinismo y cuaderno histórico son ejecuciones, no tres hipótesis. |
| EXP_06 | E2 1,050 + V4 1,050 = 2,100 ajustes. | Dos corridas de determinismo: 4,200 ajustes físicos, una hipótesis. |
| EXP_07 | 2,400 evaluaciones internas: 400 baseline + 2,000 Ridge; 100 reconstrucciones exteriores, 11 Ridge efectivas. | 100 referencias aparte; dos corridas, 4,022 ajustes Ridge físicos. El lector añade cero. |
| EXP_08 | 50 correcciones lineales por procedimiento (C1, selección honesta y siete sensibilidades) sobre residuos de 200 MIX internos. Además: 50 ajustes GP de residuos y 2,400 evaluaciones internas de MIX afinado (diagnóstico). | Nulos: 200 (C1) + 100 (selección) permutaciones × 50 pliegues. Sin réplica de determinismo. |
| EXP_09 | 6 candidatos × 50 pliegues × 2 juegos de particiones = 600 correcciones; 400 MIX internos. | Nulo de familia: 200 permutaciones × 6 × 50. Descargas externas: 172 escenas S2, 72 S1 y 8 archivos AlphaEarth (solo X). |
| EXP_10 | 100 evaluaciones de referencias exteriores, 400 MIX internos y 200 correcciones (2 K1 × 100 pliegues). | Control de fuga: otro tanto. Nulos: 180,900 correcciones (3 × 201 × 6 × 50). Réplica de determinismo con el mismo presupuesto y 13 salidas idénticas. El lector añade cero. |
| EXP_11 | 2 fórmulas fijas; 0 entrenamientos; 5,520 predicciones mezcla por corrida. | 200 ajustes solo de verificación de J (antes del registro). Réplica de determinismo con 11 salidas idénticas. El lector añade cero. |

No sumamos una cifra de “todo lo entrenado” mezclando unidades y registros de distinto alcance. La reproducción actual de cuadernos añade **cero** ajustes a esos presupuestos históricos.

## Dónde está la evidencia dentro de este proyecto

| Ronda | Lectura del equipo | Presupuesto, registro y resultados conservados |
|---|---|---|
| EXP_01 | [Cuaderno](../notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb) | [Manifiesto](../data/exp_01_bloques/manifiesto.json), [ejecución](../data/exp_01_bloques/registro.json), [métricas](../data/exp_01_bloques/metricas_control.csv) |
| EXP_02 | [Cuaderno](../notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb) | [Mapa de insumos y controles](../config/exp_02_ponderacion_temporal.json) |
| EXP_03 | [Cuaderno](../notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb) | [Mapa de insumos y controles](../config/exp_03_variables_y_familias.json) |
| EXP_04 | [Cuaderno](../notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb) | [Ejecución](../data/exp_04_lluvia_octubre/registro_ejecucion.json), [mapa completo](../config/exp_04_lluvia_octubre.json) |
| EXP_05 | [Cuaderno](../notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb) | [Ejecución](../data/exp_05_historico_octubre/registro_ejecucion.json), [mapa completo](../config/exp_05_historico_octubre.json) |
| EXP_06 | [Cuaderno](../notebooks/experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb) | [Ejecución](../data/exp_06_pico_soportado/registro_ejecucion.json), [mapa completo](../config/exp_06_pico_soportado.json) |
| EXP_07 | [Cuaderno](../notebooks/experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb) | [Registro previo](../notebooks/experimentos/exp_07_heterogeneidad_parcela/registro_previo.json), [corrida](../resultados/exp_07_heterogeneidad_parcela/registrada/registro_ejecucion.json), [verificación independiente](../notebooks/experimentos/exp_07_heterogeneidad_parcela/verificacion_independiente.json) |
| EXP_08 | [Cuaderno](../notebooks/experimentos/exp_08_contraste_vecinal/exp_08_contraste_vecinal.ipynb) | [README y fe de erratas](../notebooks/experimentos/exp_08_contraste_vecinal/README.md), [predeclaración S2](../notebooks/experimentos/exp_08_contraste_vecinal/PREDECLARACION_replica_S2.md) |
| EXP_09 | [Cuaderno](../notebooks/experimentos/exp_09_fuentes_externas/exp_09_fuentes_externas.ipynb) | [Registro previo](../notebooks/experimentos/exp_09_fuentes_externas/REGISTRO_PREVIO.md), [README y fe de erratas](../notebooks/experimentos/exp_09_fuentes_externas/README.md), [datos externos](../data/exp_09_fuentes_externas/) |
| EXP_10 | [Cuaderno](../notebooks/experimentos/exp_10_verificacion_contraste_vecinal/exp_10_verificacion_contraste_vecinal.ipynb) | [Protocolo](../notebooks/experimentos/exp_10_verificacion_contraste_vecinal/protocolo.md), [registro previo](../notebooks/experimentos/exp_10_verificacion_contraste_vecinal/registro_previo.json), [corrida](../resultados/exp_10_verificacion_contraste_vecinal/registrada/registro_ejecucion.json), [verificación independiente](../notebooks/experimentos/exp_10_verificacion_contraste_vecinal/verificacion_independiente.json), [cierre](../notebooks/experimentos/exp_10_verificacion_contraste_vecinal/RESULTADOS_Y_CIERRE.md) |
| EXP_11 | [Cuaderno](../notebooks/experimentos/exp_11_combinacion_modelos/exp_11_combinacion_modelos.ipynb) | [Protocolo](../notebooks/experimentos/exp_11_combinacion_modelos/protocolo.md), [registro previo](../notebooks/experimentos/exp_11_combinacion_modelos/registro_previo.json), [corrida](../resultados/exp_11_combinacion_modelos/registrada/registro_ejecucion.json), [verificación](../notebooks/experimentos/exp_11_combinacion_modelos/verificacion_independiente.json), [cierre](../notebooks/experimentos/exp_11_combinacion_modelos/RESULTADOS_Y_CIERRE.md) |

| Prueba final Opus R1/R2 · 11 oct | [README ronda 1](../validacion_independiente/README.md), [README ronda 2](../validacion_independiente/ronda2/README.md) | Caja cerrada de 35 (semilla 20261011), registros previos, `intentos.csv`, congelación y resultados. R1: NO FAVORABLE (p = 1.0). R2 (segundo uso de la caja): PARCIAL por la regla mecánica, nula en sustancia (p = 1.0 con 11 familias) |
| NB04 · cierre · 11 oct | [Cuaderno](../notebooks/04_seleccion_modelo_final.ipynb) | [Insumos con SHA-256](../config/04_seleccion_modelo_final.json), [predicciones y resumen](../resultados/04_seleccion_modelo_final/). Aplica la decisión de las 22:05: E_JK, con MIX como referencia |

Las particiones y distinciones históricas se identifican en el [catálogo](../config/indice_experimentos.json). Los análisis posteriores se presentan como posteriores, no como comparaciones predefinidas.

## EXP_07 — registro y cierre de la nueva pregunta

| Campo | EXP_07 ejecutado |
|---|---|
| Pregunta | ¿La dispersión espacial NDVI añade información sobre su media y municipio? |
| Único bloque nuevo | Promedio de `ndvi_std` Planet sobre las mismas capturas que el control de nivel. |
| Control pareado | C0: municipio + corrección Ridge con media NDVI; C1: mismo procedimiento + dispersión. |
| Escenario / selector | SEEN principal, FULL secundario; mismas particiones históricas. RMSE interior agrupado FULL para elegir parámetros. |
| Criterio | Aporte C1<C0 en RMSE y competitividad RMSE<MIX/MAE≤MIX, agrupados y en ≥8/10. Fijado antes de ajustar; se reportó también criterio histórico. Ninguno se cumple. |
| Presupuesto previsto | 2,400 evaluaciones internas: 400 baseline + 2,000 ajustes Ridge; 100 reconstrucciones exteriores. 100 evaluaciones de referencias aparte. |
| Ejecución real | Una corrida y réplica: 2,011 ajustes Ridge cada una, 12 salidas científicas idénticas. Cero predicciones finales. |
| Registro previo | Interno, conservado antes de primera corrida; reconoce exposición previa a etiquetas y no tiene sello de terceros. |
| Puertas y resultado | Factibilidad X y referencias pasan. C1 no mejora de forma estable ni compite con MIX. Cierre sin adopción. |

Lectura y evidencia: [cuaderno](../notebooks/experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb), [protocolo](../notebooks/experimentos/exp_07_heterogeneidad_parcela/protocolo_definitivo.md), [registro previo](../notebooks/experimentos/exp_07_heterogeneidad_parcela/registro_previo.json) y [cierre](../notebooks/experimentos/exp_07_heterogeneidad_parcela/RESULTADOS_Y_CIERRE.md). Las fechas originales y criterios de EXP_01–06 permanecen sin cambios.

Para cada corrida futura se registrará: fecha real, receta/hash previo, comparación, población, particiones/hash, criterio, presupuesto previsto/real, réplica, resultados, concentración, decisión y análisis posterior. Véase el [plan detallado](../notebooks/experimentos/exp_07_heterogeneidad_parcela/PLAN_PROPUESTO.md).

## EXP_08–EXP_10 — contraste vecinal, fuentes externas y verificación

| Campo | Registro |
|---|---|
| Autoría y fechas reales | Claude (asistente), a pedido de Fortino, 8 oct 2026. EXP_08 terminó hacia las 12:30 h; EXP_09 se registró a las 13:17 h y se ejecutó después; EXP_10 se registró a las 17:36 h (23:36 UTC) y se ejecutó después. Horario CDMX. |
| Exposición previa | El contraste vecinal se eligió tras explorar las mismas 138 etiquetas en EXP_08. Los registros de EXP_09/10 fijan hacia adelante; no son confirmaciones independientes. |
| Discrepancia corregida | En EXP_08 ("hasta 31 oct") y EXP_09 (K1–K3), el corte al 31 de octubre se aplicaba después de suavizar. Lo detectó una revisión del equipo. EXP_10 corrigió K1 y verificó la invariancia; K2/K3 no se reevaluaron. |
| Resultado vigente | K1 corregido cumple R1–R4 (RMSE<MIX en ambos juegos y 20/20 repeticiones, MAE≤MIX, no se invierte sin 2 parcelas), pero no S (p 0.184/0.129 > 0.10). |
| Decisión | **Conservar MIX como referencia oficial.** K1 corregido queda como alternativa documentada para decisión explícita del equipo. Sin las 59 predicciones. |


## Cierre — selección del modelo final (NB04, 11 oct 2026)

| Campo | Registro |
|---|---|
| Autoría y fechas reales | Fortino registró la decisión y la regla a las 22:05 h (CDMX). Opus registró las hipótesis de la ronda 2 a las 22:14:06, las congeló a las 22:17:44 y abrió la caja (segundo uso) a las 22:18:02. Claude construyó NB04 hacia las 22:45, a pedido de Fortino (`gestion/08_prompt_notebook_cierre.md`). |
| Decisión | Si la ronda 2 salía FAVORABLE, se reabría la elección. Salió PARCIAL (nula en sustancia), así que **se entrega E_JK = ½·J + ½·K, con MIX como referencia**. |
| Evidencia reunida | E_JK < MIX en las cinco evaluaciones: CV histórica 0.4757, CV nueva 0.4744, CV Opus R1 0.4750, CV Opus R2 0.4871 y caja 0.4822 (MIX: 0.4872, 0.4857, 0.4906, 0.5043, 0.4855). K también queda por debajo de MIX en las cinco, pero casi empata en las dos CV de Opus. J pierde en la caja. |
| Controles | Las recetas del cuaderno reproducen las 2,760 OOF × 4 componentes de EXP_11 (diferencia ≤1e-12) y la caja de Opus (≤3e-13). Hay dos kernels limpios con salidas idénticas, una réplica determinista y controles de fuga. **No se probó en Colab real.** |
| Ajuste final | Se entrenó con las 138 etiquetas. Semilla de los pliegues internos de K: 20261015. β = −0.0944; J eligió `anom_precip_pct_d`. Las semillas de los análisis son 20261016 (curva de aprendizaje) y 20261017 (simulación). |
| Cómo se reporta | RMSE esperado ≈0.47–0.49 t/ha. En un conjunto tipo 59, la banda simulada es 0.35–0.63. Intervalos por zona al 80/90 %: cobertura de 0.80/0.90 entre particiones y de 0.71/0.86 en la caja. Origen post-hoc de E_JK declarado. |
| Corrección a la ronda 2 | El resumen de la Fase A atribuía al INIFAP las variedades "Esperanza, Adabella y Armida" para Valles Altos y un "75 % de temporal". La fuente dice otra cosa: Esperanza y Armida son de riego en el Bajío, y para temporal en el Altiplano se recomiendan Esmeralda y Adabella. El 75 % es la parte de la superficie de cebada maltera que está en el Altiplano, sembrada bajo temporal. La fecha límite de siembra (30 jul–5 ago) no se verificó y no se cita. |
