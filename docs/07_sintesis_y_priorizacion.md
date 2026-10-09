# 07. Qué aprendimos y qué vamos a comprobar

8 de octubre de 2026. **Plan propuesto, sin ejecutar ni congelar un protocolo nuevo.**

## La decisión en una frase

Conservar la señal territorial y probar **una dimensión todavía no evaluada: la variabilidad espacial del NDVI dentro de la parcela**, además de su nivel medio. Primero comprobar su calidad y soporte sin consultar rendimientos; después, si es viable, realizar una comparación pequeña y previamente delimitada.

No empezamos de cero. Los nueve cuadernos reúnen tres fundamentos y seis rondas históricas; reconstruirlos no creó seis experimentos adicionales ni una evaluación independiente.

## Lo aprendido que cambia el siguiente paso

| Evidencia | Consecuencia para trabajar |
|---|---|
| Municipio y proximidad espacial son referencias fuertes. | Toda información nueva debe demostrar qué añade sobre territorio, no solo correlacionar con rendimiento entre municipios. |
| Buena parte del error pendiente está dentro de Chignahuapan. | Priorizar una medición que pueda distinguir parcelas de un mismo municipio; mostrar por separado Chignahuapan y el resto. |
| La historia de EXP_01 mejoró poco RMSE, pero no fue adoptable. Las variantes temporales y el pico soportado tampoco superaron las referencias. | No repetir otra media, fecha o amplitud con un nombre nuevo. Mejorar un control no equivale a mejorar el procedimiento de entrega. |
| El aparente avance de J5_PCT depende de grupos, municipios con una sola etiqueta y pocas parcelas. EXP_05 no confirmó una solución adoptable separando lluvia actual e histórica. | Mantener el escenario de evaluación fijado y diagnosticar concentración. No interpretar la anomalía porcentual como efecto causal de lluvia. |
| El contraste Ridge/HGB fue acotado y no dio una mejora adoptada. | No descartar todos los árboles; tampoco cambiar a XGBoost sin identificar qué limitación queremos resolver. |
| Extracción reproducible y coincidencia con Andrea son comprobaciones de cálculo. | No convierten automáticamente una estadística en una medición agronómica válida o en un buen predictor. |

**Balance:** no hay una mejora adoptada sobre las referencias. Sí hay avances pequeños contra controles particulares y conocimiento útil sobre qué no repetir. Las cifras comparables son las de la misma población: MIX tiene RMSE aproximado **0.4938 t/ha en FULL138** y **0.4872 en SEEN135**; no son dos mejoras sucesivas.

La arquitectura territorial + corrección ya fue explorada en EXP_04/05. Se reutiliza como instrumento de comparación; **lo nuevo sería la información de heterogeneidad**, no esa arquitectura.

## Qué queda por verificar o aprovechar del dataset

Aquí distinguimos **extraer correctamente**, **entender qué mide** y **probar utilidad predictiva**. Son comprobaciones diferentes.

| Fuente disponible | Qué ya conocemos | Qué queda abierto y para qué importa |
|---|---|---|
| Catálogo y polígonos: 197 parcelas, 138 etiquetas, 59 faltantes | IDs, grupos, geometrías, áreas y referencias territoriales comprobados. | Método exacto del split y medición del rendimiento pendientes de documentación. El caso de Nanacamilpa, con una sola etiqueta, no tiene evaluación OOF equivalente a su parcela oculta. |
| Planet 2025: NDVI, EVI, LAI, MSAVI; promedio, extremos, std y nubosidad por captura | Fechas, faltantes, resúmenes y curvas reconstruidos. | **Prioridad inmediata:** soporte común de promedio/std, dispersión intramunicipal, relación con nubosidad y área. Máscaras y número de píxeles válidos no vienen entregados; no sabemos si el porcentaje de nube representa escena o parcela. |
| Sentinel-2 2022–2025: 22 índices | Inventario, resúmenes y ausencias por sensor comprobados. | Fórmulas/productos exactos de algunos índices, LAI negativo y calidad de medición. No llamar NDWI “NDMI” ni asumir una fórmula por el nombre. |
| Landsat 2022–2025: VI6T | Separación de sensores y resúmenes comprobados. | Definición exacta de VI6T; no es una temperatura en °C. Su menor soporte temporal limita algunas representaciones. |
| Clima: 144 rásteres mensuales, 2022–2025 | Extracción por área, unidades y controles; octubre tiene verificaciones adicionales. | Otras ventanas no agotan su utilidad, pero la resolución es territorial. Tmin/Tmax mensuales no permiten contar heladas diarias ni calcular grados-día truncados exactos. Tres años no son normales climatológicas. |
| Elevación y pendiente de 120 m | Extracción zonal, CRS y cobertura comprobados; medias probadas en EXP_01. | AGC_170 tiene solo 2.10 % de cobertura válida de pendiente. Otras estadísticas zonales no son nuevos candidatos automáticos; cualquier cambio de cobertura requiere una decisión separada. |
| Noviembre–diciembre de 2025 | Datos reconstruidos y separados del ciclo principal. | Documentar admisibilidad y alcance antes de usarlos. Una estimación retrospectiva con datos posteriores no es una predicción anticipada. |

No tenemos suelos medidos, manejo, variedades, fechas individuales de siembra/cosecha, bandas crudas ni varias campañas de rendimiento. No se deben inventar ni convertir fechas de calendario en etapas agronómicas verificadas. La falta de máscaras originales limita la interpretación de `std`, pero no obliga a detener todas las tareas del proyecto.

También falta confirmación documental de la métrica principal y su conversión a puntos. Las bases siguen siendo la autoridad; los comentarios de la reunión no se convierten aquí en una fórmula oficial nueva.

## Mapa priorizado de hipótesis

1. **H7 — Heterogeneidad espacial de Planet.** Dos parcelas pueden tener el mismo NDVI medio y diferente dispersión interna. Preguntamos si esa información adicional reduce el error fuera de muestra. Es prioritaria porque opera a escala de parcela y no fue predictor en las seis rondas ni en los 56 agregados exploratorios iniciales.
2. **Calidad de observaciones.** Solo se convierte en experimento si las comprobaciones de X demuestran un problema material. No elegir umbrales de nubes mirando RMSE ni mezclar esa corrección con H7.
3. **Persistencia temporal con soporte explícito.** Una integral por días reales sería distinta de una suma de capturas. Queda como reserva, no como una variante que se ejecuta automáticamente si H7 falla.
4. **Historia óptica propia.** Puede merecer una pregunta específica, pero añadir H y C−H a un modelo que ya tiene H y C no aporta información nueva: es una transformación lineal invertible. Regularización, ventanas o interacciones tendrían que justificarse y controlarse.

La exploración inicial ya incluyó medias, máximos, percentiles y sumas de varios índices de Sentinel/Planet. Por eso **“añadir EVI o MSAVI” no sería, por sí solo, una hipótesis nueva**. Aquella exploración tuvo otra receta y evaluación; sus métricas no se mezclan con las referencias actuales.

## Cómo continúa el recorrido

**Entender/preparar:** comprobar H7 solo con X → **modelar/evaluar:** registrar y comparar dos procedimientos → **decidir/desplegar:** conservar un candidato respaldado o las referencias y verificar la entrega.

Mantendremos las particiones históricas, SEEN135 principal y FULL138 secundario. SEEN135 aproxima el caso de municipio conocido, pero no reproduce exactamente las 59 parcelas ocultas. RMSE será el selector provisional; MAE y R² se reportarán. La política de adopción debe ratificarse antes de ajustar: su propuesta está explicada en el plan, sin cambiar los cierres anteriores.

Se recomienda una sola ronda nueva tras factibilidad, seguida de decisión y cierre de búsqueda para reservar tiempo a las 59 predicciones y a la herramienta. Un resultado nulo también cierra la pregunta; no autoriza una búsqueda indefinida de ventanas, semillas o modelos.

El presupuesto y las comparaciones históricas quedan reunidos en la [bitácora](../gestion/bitacora_experimentos.md). La receta, los controles y el futuro cuaderno se describen en el [plan de EXP_07](../notebooks/experimentos/exp_07_heterogeneidad_parcela/PLAN_PROPUESTO.md).

## Fundamento y límites — referencias APA 7

El estudio de Wood et al. motiva observar variabilidad dentro de campos de trigo y cebada; **no demuestra que nuestro promedio de std prediga rendimiento**. Cawley y Talbot y Varoquaux respaldan la cautela sobre selección y muestras pequeñas: la anidación no elimina nuestra adaptación entre rondas, y no trasladamos sus cifras de incertidumbre a este dataset.

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research, 11*, 2079–2107. https://jmlr.org/papers/v11/cawley10a.html

Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage, 180*, 68–77. https://doi.org/10.1016/j.neuroimage.2017.06.061 — Prepublicación: https://arxiv.org/abs/1706.07581

Wood, G. A., Taylor, J. C., & Godwin, R. J. (2003). Calibration methodology for mapping within-field crop variability using remote sensing. *Biosystems Engineering, 84*(4), 409–423. https://doi.org/10.1016/S1537-5110(02)00281-7
