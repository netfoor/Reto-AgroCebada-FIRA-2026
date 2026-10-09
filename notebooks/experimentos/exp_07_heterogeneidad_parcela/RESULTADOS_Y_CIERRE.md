# EXP_07 · Resultado y cierre

8 de octubre de 2026. **Cerrado sin adopción.** No se generaron las 59 predicciones de entrega.

## Qué preguntamos

Si la dispersión espacial NDVI Planet aporta información además del NDVI medio y municipio. C0 utiliza el nivel L; C1 añade la dispersión S con la misma arquitectura, ventana, selección y particiones. MUN/MIX son referencias fijas. No se cambió algoritmo, calidad, fechas ni semilla para mejorar el resultado.

## Qué se comprobó antes de evaluar

- 26,255 capturas del ciclo; 18,248 con promedio y std finitos en las mismas fechas.
- Las 197 parcelas tienen descriptores y capturas pareadas en los siete meses. Cero std negativas, infinitos o columnas vacías de entrenamiento.
- Las máscaras de promedio/std son idénticas. Las medias pareadas coinciden con la reconstrucción histórica a menos de `1e-16`: no hubo un cambio efectivo de soporte.
- S tiene variación dentro de municipio en los 250 entrenamientos exteriores/interiores. Sus datos no quedaron reducidos a una constante territorial.
- 92 pruebas previas registradas: motor, factibilidad y orquestación, sin rendimientos reales en los ajustes sintéticos. El registro se guardó antes de ajustar candidatos.
- MUN reproduce las OOF históricas exactamente; MIX difiere como máximo `5.06e-13 t/ha`, por debajo de `1e-8` previsto.

El registro es interno, no un sello temporal de terceros. La hipótesis nace después de observar rondas anteriores: no se presenta como confirmación independiente ni se atribuye a FIRA nuestro criterio de desarrollo.

## Resultado principal — SEEN135

Mismas 135 parcelas, 1,350 OOF por procedimiento, conservando las 138 etiquetas en los entrenamientos correspondientes. Métricas en t/ha salvo R².

| Procedimiento | RMSE | MAE | R² |
|---|---:|---:|---:|
| MUN | 0.493404 | 0.321274 | 0.657475 |
| MIX | **0.487197** | 0.334215 | **0.666039** |
| C0: municipio + nivel NDVI | 0.494064 | 0.321996 | 0.656558 |
| C1: C0 + dispersión | 0.494105 | 0.321769 | 0.656501 |

C1 cambia RMSE respecto de C0 en **+0.000041 t/ha**: prácticamente idéntico, no una mejora. MAE disminuye apenas **0.000227**, pero sigue por encima de MUN. C1 mejora RMSE frente a C0 en **4/10 repeticiones**, no en las ocho exigidas; frente a MIX, en **1/10**.

Ambos cumplen la condición MAE≤MIX, agrupada y en 10/10 repeticiones, pero no RMSE<MIX; por eso **no cumplen competitividad**. Tampoco cumplen el diagnóstico histórico que exige MAE≤MUN. Por tanto, el cambio prospectivo de criterio no altera el cierre.

La selección interior prefirió baseline —pendientes cero, MUN— en **46/50 entrenamientos de C0** y **43/50 de C1**. La mayoría de los entrenamientos no encontró una corrección preferible al respaldo municipal dentro de la rejilla fijada. Eso es evidencia sobre este procedimiento, no prueba de ausencia absoluta de señal.

## Chignahuapan y concentración

En Chignahuapan, RMSE es **0.590964 C0**, **0.591400 C1**, **0.590198 MUN** y **0.573628 MIX**. Añadir S no resuelve el principal foco de error; empeora ligeramente frente a C0. En el resto C1 mejora muy poco frente a C0, sin cambiar la decisión global.

En SEEN, C1 favorece 72 parcelas y perjudica 50 respecto de C0; 13 quedan sin cambio. La ganancia SSE neta es negativa, `−0.05449`, aunque más parcelas mejoren que empeoren: **el conteo no sustituye la magnitud de los errores**. Retirar solo de evaluación las dos o cinco parcelas más favorecidas tampoco convierte C1 en una mejora. Ninguna etiqueta se retiró del entrenamiento.

La concentración frente a MIX también se reporta, pero no usamos estas salidas para escoger un subgrupo o modificar la receta.

## Escenario secundario y soporte de entrega

En FULL138, RMSE es C0 **0.512380**, C1 **0.512418**, MIX **0.493845**, MUN **0.511757**. No se mezclan estas cifras con SEEN para aparentar mejoras.

Las 59 ocultas tienen descriptores disponibles. Seis valores L y dos S están fuera de sus rangos municipales etiquetados; esto es soporte univariado, no prueba de extrapolación segura. AGC_120, Nanacamilpa, permanece como caso con una sola etiqueta municipal y sin evaluación OOF equivalente con esa etiqueta presente. No se resolvió esa limitación mediante una puntuación nueva.

## Presupuesto, reproducibilidad y alcance

Por corrida: **2,400 evaluaciones internas** = 400 baseline + 2,000 ajustes Ridge; 100 reconstrucciones exteriores, de las cuales **11** ajustaron Ridge. Total efectivo: **2,011 ajustes Ridge**, más 100 evaluaciones de referencia separadas.

La corrida registrada y su réplica producen **12 salidas científicas idénticas byte a byte**, incluidas OOF, selecciones, scores y parámetros. Son dos ejecuciones de una pregunta: **4,022 ajustes Ridge físicos con etiquetas reales**, no dos hipótesis. Las pruebas sintéticas y la lectura del notebook se registran aparte; el lector no reentrena.

Las matrices, código, pruebas y protocolo registrados no se modificaron después de la primera corrida. Los documentos de cierre y el notebook se elaboran después y se identifican como tales. La verificación local no equivale a una ejecución real en Colab.

**Verificación del lector:** 778 pruebas del proyecto y Ruff pasan. Dos kernels nuevos completan las 32 celdas sin errores ni ajustes; sus 31 salidas y dos figuras PNG coinciden al normalizar únicamente la fecha de lectura. El cuaderno compartido incluye las salidas de la primera lectura. Los dos intentos de kernel bloqueados por el sandbox no ejecutaron celdas ni modelos; las verificaciones completas se realizaron fuera de esa restricción.

## Qué concluimos y qué no

**La media de dispersión espacial entregada por Planet no aporta una mejora estable bajo este diseño lineal y esta ventana.** Cerramos H7 sin adopción; las referencias siguen siendo el punto de comparación.

No concluimos que toda heterogeneidad espacial, Planet o los modelos lineales sean inútiles. La ausencia de máscaras, número de píxeles y etapas individuales limita la interpretación. Tampoco convertimos siete resultados sin adopción en una demostración de que MIX es el óptimo posible.

La continuación recomendada es discutir cierre de búsqueda y selección del procedimiento de entrega según métricas oficiales, con MIX como referencia provisional para RMSE y MUN para MAE. No se ejecuta automáticamente otra variante ni se congela aquí un modelo final de producción.

## Evidencia dentro del proyecto

- [Protocolo](protocolo_definitivo.md) y [registro previo](registro_previo.json).
- [Factibilidad sin rendimiento](../../../data/exp_07_heterogeneidad_parcela/diagnosticos_X.json).
- [Corrida registrada](../../../resultados/exp_07_heterogeneidad_parcela/registrada/registro_ejecucion.json) y [réplica](../../../resultados/exp_07_heterogeneidad_parcela/replica_determinismo/registro_ejecucion.json).
- [Métricas](../../../resultados/exp_07_heterogeneidad_parcela/registrada/metricas.csv), [reglas](../../../resultados/exp_07_heterogeneidad_parcela/registrada/reglas.csv) y [concentración](../../../resultados/exp_07_heterogeneidad_parcela/registrada/concentracion.csv).
- [Verificación independiente posterior](verificacion_independiente.json): otro agente reconstruyó métricas, decisiones y las 100 predicciones exteriores desde parámetros guardados, sin ajustar modelos. No sustituye una revisión humana ni una validación externa.
