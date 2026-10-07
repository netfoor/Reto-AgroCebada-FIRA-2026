# 03. Plan de trabajo y evidencias

Edición del 7 de octubre de 2026. El plan organiza las preguntas, comprobaciones y productos de cada etapa del proyecto.

## 1. Definir el problema y comprobar los datos

**CRISP-DM: entender el problema y los datos.**

Empezamos por el rendimiento faltante, la unidad parcela y el alcance del reto. El análisis incluye conteos, etiquetas, campañas, localización y calidad. Cerramos cuando podemos describir qué se predice y qué información existe, sin confundir fechas con ejemplos independientes.

**Evidencia:** descripción del objetivo, inventario y comprobaciones de estructura y calidad.

## 2. Seguir una parcela hasta sus variables

**CRISP-DM: preparar los datos.**

Conectamos polígono, ráster, observaciones satelitales y periodos. Explicamos cada receta antes de calcularla y comprobamos sus unidades, cobertura y faltantes. Después generalizamos a la tabla de parcelas.

Cuando una receta parte de un aporte del equipo, identificamos autor, fuente y fecha, explicamos su procedimiento y contrastamos el resultado. La comprobación se entiende sin consultar documentos adicionales.

**Evidencia:** recorrido de una parcela, pruebas de extracción, diccionario y tabla de variables.

## 3. Construir referencias y una comparación honesta

**CRISP-DM: modelar y evaluar.**

Comprobamos cuánto predicen reglas sencillas y explicamos por qué son controles útiles. Mostramos cómo apartamos parcelas, seleccionamos ajustes y calculamos errores. Cerramos cuando una comparación puede repetirse sobre los mismos IDs, particiones y escenario.

**Evidencia:** referencias, particiones identificadas y predicciones fuera de muestra con sus métricas.

## 4. Evaluar hipótesis

**CRISP-DM: preparación, modelado y evaluación.**

Cada prueba responde una pregunta concreta: qué información podría aportar una variable o un procedimiento, qué cambia respecto al control y cómo se identifica su efecto. Delimitamos candidatos, presupuesto y criterio antes de la nueva corrida.

Comparamos resultados, estabilidad y errores por región. Una ganancia numérica pequeña no basta por sí sola para incorporar una variante; un resultado desfavorable también ayuda a delimitar la siguiente pregunta.

**Evidencia:** hipótesis, receta, controles, comparación, sensibilidad y conclusión con límites.

## 5. Seleccionar y entregar la solución

**CRISP-DM: evaluación y despliegue.**

Seleccionamos un procedimiento de acuerdo con la evidencia y los criterios del reto. Verificamos las 59 predicciones y conectamos una única receta de preparación y predicción a la herramienta de consulta.

El alcance del producto debe corresponder a lo evaluado. Predecir otras regiones o campañas no se presenta como una capacidad demostrada por este catálogo.

**Evidencia:** decisión de selección, tabla de entrega, artefacto del modelo y comprobaciones de la herramienta.

## Cómo se documenta cada regreso

El ciclo no es lineal. La evaluación puede motivar volver a estudiar los datos o preparar variables. Registramos **qué evidencia motivó el regreso, qué se revisa y qué permanece fijo**.

Para comparar una nueva hipótesis conservamos los controles pertinentes y distinguimos los cambios de receta de los cambios de muestra o evaluación. Así una conclusión conduce a otra pregunta sin perder el historial de evidencia.
