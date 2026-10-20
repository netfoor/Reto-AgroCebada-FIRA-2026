# Mensaje maestro y plan por semanas (texto pegado por el usuario el 2026-09-20)

Copia textual del mensaje que definió el trabajo. No se edita; las notas y discrepancias están al final.

```
=== MENSAJE MAESTRO (pegar primero) ===
Contexto: Reto AgroCebada FIRA 2026 (rendimiento de cebada, 138 parcelas de entrenamiento y 59 ocultas). Entrega el 2026-10-20. Nota: 70% modelo, 30% dashboard. Todo el código va en R (Rscript está en C:\Program Files\R\R-4.5.2\bin\Rscript.exe, no está en el PATH). Lee primero outputs/prep_equipo/04_plan_de_trabajo.md, los otros tres documentos de esa carpeta y outputs/eda/resumen_general.md.
Hallazgos que condicionan todo: el Estado explica ~50% de la varianza; Tmin (+0.61) solo marca la región; la lluvia (-0.47) depende de Singuilucan; el clima viene en celdas de ~5.5 km.
Reglas: (1) toda variable se evalúa por encima de la línea base regional; (2) validación agrupada por zona y repetida con varias semillas, nunca CV aleatoria; (3) selección de variables dentro de cada partición; (4) cada hipótesis se escribe antes de probarla; (5) registro de experimentos con semillas y folds fijos; (6) datos originales de solo lectura; (7) cualquier dato agronómico se marca "verificado con fuente" o "por verificar", nunca se inventa; (8) pídeme aprobación antes de instalar paquetes de R.
Estilo: explícame en español claro, sin tecnicismos innecesarios, porque necesito poder defender cada decisión ante el jurado.

=== SEMANA 1 (21-27 sep): aprender + línea base ===
Prompt 1A (skill learn + WebSearch/WebFetch + markitdown):
"Usa la skill learn para enseñarme la agronomía de la cebada maltera, bloque por bloque: A) fenología y etapas críticas (Zadoks), B) estreses climáticos (heladas, calor en llenado, sequía, exceso de humedad), C) sanidad y manejo (roya, mancha reticulada, fecha de siembra, nitrógeno, temporal vs riego, calidad maltera), D) contexto de Hidalgo, Tlaxcala y Puebla y por qué Singuilucan es distinto. Busca en la web fuentes de INIFAP, FIRA, SIAP y artículos, léelas con WebFetch (si son PDF, con markitdown) y marca cada dato como verificado o por verificar. Al final de cada bloque hazme 5 preguntas de repaso y guarda una hoja de una página en outputs/prep_equipo/agronomia/. Termina cada bloque con una lista de hipótesis medibles con nuestros datos."

Prompt 1B (skill learn):
"Con la skill learn, enséñame cómo se miden NDVI, EVI, SAVI, MSAVI y LAI, qué diferencias hay entre Sentinel-2, Landsat y Planet, y qué resolución real tienen CHIRPS, CHIRTS-ERA5 y el DEM. Después, validación agrupada, fuga de información y por qué con n=138 conviene un modelo simple. Quiero ejemplos con nuestros propios datos."

Prompt 1C (skill claude-mem:make-plan y luego do):
"Con la skill make-plan, arma el plan detallado de la Fase 1: limpieza (Cultivo, AGC_070 y AGC_078 con st_make_valid, LAI negativo), esquema de CV agrupada por zona repetida con semillas, y líneas base (media global, solo Estado, Estado + municipio agrupado). Muéstramelo y espera mi aprobación. Luego ejecútalo con la skill do."

=== SEMANA 2 (28 sep-4 oct): variables ===
Prompt 2A (skill do + agentes en paralelo):
"Ejecuta la Prioridad 1 de 02_ideas_feature_engineering.md (#1 a #5) con la skill do, un agente por familia de variables (climáticas por ventana, anomalías, compuestos satelitales sin nubes, variables por sensor). Cada variable debe traer su hipótesis escrita y evaluarse contra la línea base regional dentro de la CV. Guarda los productos nuevos en una carpeta nueva, no en derivados/."
Prompt 2B (skill code-review):
"Con la skill code-review nivel alto, revisa los scripts de variables buscando fuga de datos (selección fuera de la CV), errores de unidades, mezcla de sensores y ventanas mal definidas. Aplica los arreglos con --fix solo si te lo confirmo."
Prompt 2C:
"Con lo que aprendí en agronomía, propón hipótesis nuevas para explicar la variación DENTRO de cada región (suelo, altitud, manejo, fenología) y qué variable de nuestros datos podría aproximarlas."

=== SEMANA 3 (5-11 oct): modelado y robustez ===
Prompt 3A (make-plan + do):
"Modelos en este orden: lineal regularizado con región + pocas variables; random forest/GBM poco profundos; ensamble solo si mejora bajo la misma CV. Descarta lo que no supere la línea base regional de forma consistente entre semillas. Reporta RMSE, MAE y R² con intervalo entre semillas."
Prompt 3B (skill code-review + simplify):
"Revisa el pipeline completo con code-review y luego simplify. Haz una prueba leave-one-cluster-out (quitar Singuilucan y cada municipio) y dime si el modelo sobrevive. Calcula el error esperado para las 59 parcelas con intervalo (cuantiles o conformal)."
Prompt 3C (skill dataviz):
"Con la skill dataviz, crea las figuras del análisis: error por región, importancia de variables, predicho vs observado con incertidumbre, para usarlas en el documento y el dashboard."

=== SEMANA 4 (12-18 oct): entrega ===
Prompt 4A (dashboard mínimo):
"Primero dime qué formato de dashboard exige el reto. Con la skill dataviz y, si sirve HTML autocontenido, la herramienta Artifact, arma un dashboard mínimo: mapa de parcelas con predicción, tabla con intervalo, 3-4 variables clave y una sección de limitaciones. Que sea simple y claro."
Prompt 4B (skills docx y human):
"Con la skill docx, redacta el documento de metodología: datos, variables, validación, resultados, error esperado, limitaciones y qué no funcionó. Con la skill human, revisa el texto para que suene natural y de nuestro equipo."
Prompt 4C:
"Genera un script único que reproduzca las predicciones finales de las 59 parcelas desde los datos originales, y comprueba que corre de cero. Prepara también una lista de preguntas probables del jurado con mis respuestas."

=== 19-20 oct: colchón, revisión final y envío ===

=== TRANSVERSAL (opcional) ===
- Skill task-observer: sigue activa durante todo el trabajo.
- Skill loop o schedule: un recordatorio semanal que compare el avance con este plan.
- Skill mem-search: al empezar cada sesión, "¿qué decidimos y en qué quedamos?".
- Preguntas a los organizadores (envíalas ya, no en la semana 3): fechas de siembra/cosecha, rendimientos previos, si se permite fusionar Básico y PRO, fuente del área y del LAI negativo, eventos climáticos 2025, variedad y manejo.
```

## Petición adicional del usuario (mismo mensaje)

Dividir la muestra para validar el modelo: tomar el 70% conocido (las 138 parcelas de entrenamiento) como si fuera el
100% y comprobar si el modelo valida bien. Ver `01_plan_fase1.md`.

## Notas del asistente (no forman parte del texto pegado)

1. **Fecha de entrega:** el mensaje maestro dice 2026-10-20, pero el usuario confirmó (2026-09-20) que la fecha de entrega
   es el **19 de octubre**. Se trabaja para entregar antes de esa fecha; el 20 queda como colchón (consistente con el
   bloque "19-20 oct").
2. **Regla 2 ("nunca CV aleatoria")** vs. la petición de dividir el 70% conocido: resuelto con tres niveles (V1
   principal, V2 prueba de esfuerzo, V3 un grupo fuera), aprobados por el usuario; ver `01_plan_fase1.md`.
3. **Ruta de las hojas de agronomía:** el prompt 1A dice `outputs/prep_equipo/agronomia/`. Como la carpeta nueva es
   `preparacion/` en la raíz del proyecto, la ruta aprobada por el usuario es **`preparacion/agronomia/`** (ya creada,
   vacía por ahora).
4. `outputs/prep_equipo/04_plan_de_trabajo.md` existe (lo agregó el usuario después de los tres primeros
   documentos) y su Fase 1 es la base de `01_plan_fase1.md`.
