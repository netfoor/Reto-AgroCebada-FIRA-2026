# 06. Glosario breve

Consulta opcional: buscar el término que aparezca durante la lectura. Estas definiciones explican el proyecto; no sustituyen las comprobaciones de cada cuaderno.

## Problema y modelos

**Aprendizaje supervisado.** Aprender a partir de ejemplos con respuesta conocida. Aquí relacionamos características de parcelas con su rendimiento observado.

**Regresión / clasificación.** La regresión predice un número, como t/ha; la clasificación predice una categoría. Nuestro objetivo es de regresión.

**Variable (`X`) / etiqueta (`y`).** Las variables describen la parcela —por ejemplo, lluvia o un resumen satelital—; la etiqueta es el rendimiento que queremos predecir. Una fila corresponde a una parcela.

**Familia de modelos.** Forma de construir una regla de predicción. Modelos lineales y árboles son familias diferentes; ambas pueden resolver regresión. No confundir familia con metodología de proyecto.

**Referencia o baseline.** Regla sencilla usada como control. **MUN** usa la media municipal aprendida del entrenamiento; **MIX** combina esa referencia con interpolación espacial IDW. Un municipio no visto requiere una regla de respaldo explícita.

**Ridge / regularización.** Ridge es regresión lineal con una penalización de los coeficientes para controlar complejidad. No garantiza mejorar; su intensidad es un hiperparámetro.

**Hiperparámetro.** Elección del procedimiento, como intensidad de penalización o profundidad de un árbol. Si se ajusta con datos, debe seleccionarse sin mirar las etiquetas usadas para evaluar.

Las distinciones entre datos de entrada, respuesta, regresión y estimadores siguen la introducción de scikit-learn (Scikit-learn developers, s. f.).

## Evaluación

**Pliegue / validación cruzada.** Una división entre entrenamiento y validación. Varias divisiones permiten evaluar sin usar la etiqueta apartada en el ajuste que la predice.

**Validación anidada.** Divisiones interiores para seleccionar el ajuste y exteriores para evaluar ese procedimiento. No elimina por sí sola decisiones adaptativas entre experimentos.

**OOF, fuera de muestra.** Predicción de una parcela obtenida sin usar su etiqueta en ese ajuste. Si la parcela se predice en diez repeticiones, sigue siendo una parcela, no diez observaciones independientes.

**Fuga de información.** Uso indebido de información de validación al entrenar o preparar el modelo. Ejemplo: aprender una imputación con datos que debían permanecer apartados.

**RMSE / MAE / R².** RMSE es la raíz del promedio de errores cuadrados y penaliza más los errores grandes; MAE promedia errores absolutos. Ambos se expresan aquí en t/ha y menor es mejor. R² compara el error cuadrático con predecir la media del conjunto evaluado; puede ser negativo.

**FULL138 / SEEN135.** Dos poblaciones de evaluación: todas las 138 parcelas, o las 135 cuyo municipio está presente en el entrenamiento correspondiente. No comparar una cifra de una población con otra como si fueran el mismo contraste.

**Correlación / causalidad.** Que dos variables se muevan juntas no demuestra que una cause la otra. La región puede explicar parte de una asociación aparente entre clima y rendimiento.

## Datos y trazabilidad

**CRS / ráster / NoData.** CRS define cómo se representan coordenadas; un ráster es una malla de píxeles con valores; NoData marca ausencia de medición, no necesariamente un cero.

**Ingeniería de variables.** Convertir fuentes en características utilizables. Exige explicar qué se mide, periodo, unidad, agregación y calidad; no solo añadir columnas.

**Pipeline.** Secuencia explícita de preparación y predicción. Las operaciones que aprenden de datos se ajustan con el entrenamiento de cada división, no con todo el conjunto.

**Preregistro / reconstrucción.** El primero fija una prueba antes de sus nuevos resultados; la segunda organiza evidencia ya existente. Preparar hoy un notebook con resultados anteriores no lo convierte en un preregistro de aquella fecha.

**Hash / entorno bloqueado.** Un hash permite detectar cambios de bytes, no demostrar por sí solo cuándo se crearon. `uv.lock` fija dependencias; no valida automáticamente datos, modelos ni un runtime distinto.

## Para profundizar

La [metodología](02_metodologia.md) explica selección, validación y límites. La [guía de notebooks](04_notebooks_y_colab.md) explica ejecución y resultados.

Scikit-learn developers. (s. f.). *Getting started*. https://scikit-learn.org/stable/getting_started.html
