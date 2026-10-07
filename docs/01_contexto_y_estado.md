# 01. El problema y la evidencia que buscamos

Edición del 7 de octubre de 2026.

## Qué queremos resolver

Estimar el rendimiento de cebada, en **toneladas por hectárea**, para las **59 parcelas sin etiqueta** de un catálogo de **197**. Las otras **138** tienen rendimiento conocido y permiten aprender y evaluar una regla de predicción.

Es **aprendizaje supervisado** porque tenemos ejemplos con respuesta conocida, y **regresión** porque esa respuesta es un número, no una categoría. Una fila de aprendizaje representa una parcela; sus imágenes y fechas se convierten en variables de esa fila. Véanse estos conceptos en el [glosario](06_glosario.md).

La campaña objetivo es abril–octubre de 2025. La información de 2022–2024 describe antecedentes de las parcelas; no aporta más rendimientos etiquetados. Primero cumplimos el objetivo del catálogo entregado. Predecir nuevas regiones o campañas exigiría otra evaluación.

## Preguntas que guían el recorrido

1. **¿Qué conocemos realmente?** Comprobar IDs, etiquetas, fechas, unidades, cobertura geográfica y calidad.
2. **¿Cómo se convierte una fuente en una variable?** Seguir una parcela desde su polígono hasta una fila, explicando extracción, periodo, agregación y faltantes.
3. **¿Qué logra una regla sencilla?** Evaluar referencias antes de añadir complejidad.
4. **¿Qué información mejora esas referencias?** Comparar hipótesis sobre las mismas parcelas y particiones.
5. **¿Qué conclusión permite la evidencia?** Distinguir mejora numérica, estabilidad, adopción y límites de uso.

Cada respuesta se apoya en una salida reproducible, no solo en una afirmación del texto.

## Balance de las seis rondas — consulta rápida

| Ronda de lectura | Pregunta estudiada | Conclusión registrada |
|---|---|---|
| `exp_01_bloques` | ¿Aportan clima, satélite o historia? | Historia mejora poco RMSE, pero empeora MAE; no se adopta. |
| `exp_02_ponderacion_temporal` | ¿Ayuda ponderar las medias por tiempo? | No supera su control ni las referencias. |
| `exp_03_variables_y_familias` | ¿Ayudan descriptores temporales o Ridge/HGB? | Sin mejora adoptada en el contraste acotado. |
| `exp_04_lluvia_octubre` | ¿Ayudan anomalías y agrupaciones? | J5_PCT queda con reservas; parte de la ventaja depende del escenario y los grupos. |
| `exp_05_historico_octubre` | ¿Qué aporta separar lluvia histórica y actual? | Ninguna receta cumple la regla principal. |
| `exp_06_pico_soportado` | ¿Ayuda redefinir la fecha del pico? | Mejora poco su control, pero no supera las referencias. |

**No hay una mejora adoptada.** Eso no significa que todas las hipótesis tengan efecto nulo ni que una familia completa de modelos sea inútil. Las auditorías, diagnósticos y réplicas son comprobaciones, no rondas predictivas adicionales.

Este balance sintetiza las conclusiones; cada cuaderno explica la evidencia que las sostiene con un formato común. La evaluación distingue RMSE, MAE y R² y separa los criterios internos de desarrollo de la fórmula oficial del reto. No se atribuye a FIRA una métrica principal sin confirmación documentada.
