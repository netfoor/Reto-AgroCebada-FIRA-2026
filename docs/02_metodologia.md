# 02. Cómo investigamos y por qué

Edición del 7 de octubre de 2026. La metodología organiza decisiones; no garantiza que un modelo nuevo supere al anterior.

## Por qué elegimos CRISP-DM

El reto no consiste solo en ajustar un algoritmo: debemos entender el objetivo, comprobar fuentes espaciales y temporales, construir variables, evaluar predicciones y entregar una herramienta. **CRISP-DM** organiza esas seis tareas y permite regresar a una etapa cuando aparece nueva evidencia (IBM, s. f.).

Lo elegimos por ese encaje con el proyecto y porque ofrece un lenguaje común al equipo, **no porque sea exclusivo de regresión**. “Regresión supervisada” describe qué aprendemos; CRISP-DM describe cómo organizamos el trabajo.

Para situarlo frente a otros enfoques:

- **KDD** describe el proceso de obtener conocimiento útil a partir de datos, del que la minería de datos es una parte. Es una referencia relevante; aquí necesitamos también hacer explícitos el objetivo y la entrega tecnológica (Fayyad et al., 1996).
- **CRISP-ML(Q)** amplía el enfoque de proceso con calidad y riesgos de ML. Tomamos de él la idea de controles por etapa, sin afirmar que implementamos todo su ciclo operativo (Studer et al., 2021).

Esta elección es una adaptación razonada, no una demostración de superioridad universal de una metodología.

## Qué produce cada etapa

| Etapa CRISP-DM | Pregunta del proyecto | Evidencia esperada |
|---|---|---|
| Entender el problema | ¿Qué falta predecir y para qué? | Objetivo, unidad, alcance y criterios oficiales conocidos |
| Entender los datos | ¿Qué contienen y qué límites tienen? | Conteos, fechas, mapas y controles de calidad |
| Preparar los datos | ¿Cómo obtenemos variables defendibles? | Recetas, unidades, pruebas y tabla por parcela |
| Modelar | ¿Qué hipótesis y procedimiento probamos? | Referencias, candidatos y ajustes delimitados |
| Evaluar | ¿Mejora y dónde falla? | Predicciones fuera de muestra, contrastes y sensibilidad |
| Desplegar | ¿Cómo se consulta la solución? | Predicciones, artefacto e interfaz verificables |

**El recorrido no es lineal.** Si la evaluación revela que una mejora depende de pocas parcelas, regresamos a entender los datos o a preparar variables. Registramos la evidencia que motivó ese regreso; no reiniciamos el proyecto ni borramos resultados.

## Cómo nace una decisión

Seguimos **pregunta → evidencia → hipótesis → comprobación → decisión y límite**.

Por ejemplo, antes de elegir una ponderación espacial identificamos qué mide la fuente, contrastamos recetas y comprobamos sus diferencias. Antes de elegir un modelo, medimos qué logra una referencia sencilla. Antes de incorporar una variable, preguntamos si aporta algo además de la ubicación.

Cada prueba tendrá una hipótesis concreta, fuentes y controles, comparación prevista y presupuesto. Separaremos lo definido antes de una corrida de lo analizado después de ver su resultado.

## Por qué evaluamos fuera del entrenamiento

Un modelo puede memorizar particularidades de las parcelas conocidas sin predecir bien otras. La **validación cruzada** aparta parcelas para evaluarlas sin usar sus etiquetas en el ajuste. Reutilizamos las mismas particiones entre candidatos para que la comparación no cambie de muestra.

Cuando seleccionamos hiperparámetros, usamos **validación anidada**: los pliegues interiores eligen el ajuste; los exteriores evalúan el procedimiento. También aprendemos imputación y escalado solo con el entrenamiento correspondiente. Así evitamos que la respuesta que queremos evaluar influya en su propia predicción (Scikit-learn developers, s. f.).

Eso no elimina la selección humana entre rondas ya observadas. Las cifras siguen siendo evidencia de desarrollo, no una confirmación independiente definitiva (Cawley & Talbot, 2010).

## Reglas que deben explicarse junto a sus resultados

- **Una parcela, una etiqueta:** todas sus fechas permanecen juntas al dividir datos.
- **Comparación común:** mismas particiones, IDs, población puntuada y métricas. Una variable diferente sí puede compararse; atribuir la mejora exige identificar qué cambió.
- **Dos escenarios separados:** FULL138 puntúa todas las parcelas; SEEN135 puntúa aquellas cuyo municipio está presente en el entrenamiento de su pliegue. El segundo se motiva por las 59 ocultas, que tienen municipios con etiquetas; no reproduce exactamente la entrega ni resuelve el caso de Nanacamilpa con una sola etiqueta.
- **Criterio conservador de las últimas rondas:** RMSE menor que MIX y MAE no mayor que MUN, agrupados y cada condición en al menos 8/10 repeticiones. Busca evitar adoptar una ganancia aislada o intercambiar una mejora por un deterioro no discutido. Es una regla del proyecto, no significación estadística ni calificación oficial.
- **Historia preservada:** cada ronda mantiene su criterio original. Una regla nueva aplica hacia adelante; no recalifica el pasado.

El cuaderno de referencias explicará cómo se construyen MUN/MIX y las particiones 5×10. Los términos están en el [glosario](06_glosario.md); los detalles ejecutables aparecerán donde se comprueban, no como supuestos ocultos.

## Para profundizar — referencias APA 7

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research, 11*, 2079–2107. https://jmlr.org/papers/v11/cawley10a.html

Fayyad, U., Piatetsky-Shapiro, G., & Smyth, P. (1996). From data mining to knowledge discovery in databases. *AI Magazine, 17*(3), 37. https://doi.org/10.1609/aimag.v17i3.1230

IBM. (s. f.). *CRISP-DM help overview*. https://www.ibm.com/docs/en/spss-modeler/saas?topic=dm-crisp-help-overview

Scikit-learn developers. (s. f.). *Nested versus non-nested cross-validation*. https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html

Studer, S., Bui, T. B., Drescher, C., Hanuschkin, A., Winkler, L., Peters, S., & Müller, K.-R. (2021). *Towards CRISP-ML(Q): A machine learning process model with quality assurance methodology* (Versión 2) [Prepublicación]. arXiv. https://arxiv.org/abs/2003.05155v2

Las fuentes respaldan el marco y sus riesgos. Los umbrales, ventanas y recetas concretos son decisiones del proyecto que necesitan su propia comprobación.
