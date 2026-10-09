# AgroCebada

Este proyecto reúne la explicación y la evidencia reproducible para predecir el rendimiento de las parcelas de cebada del reto. El recorrido parte del problema, comprueba los datos, construye variables y compara hipótesis hasta justificar una solución.

**La lectura principal está dentro de esta carpeta.** No requiere conocer documentos previos ni los nombres usados durante la exploración. Los aportes de Andrea y Jared se reconocen en las comprobaciones correspondientes; sus documentos originales son contexto adicional, no un requisito de lectura.

## Recorrido para el equipo

1. [El problema y las preguntas del recorrido](docs/01_contexto_y_estado.md).
2. [Cómo investigamos y por qué usamos esta metodología](docs/02_metodologia.md).
3. [Etapas y evidencias que produce cada una](docs/03_plan_de_trabajo.md).
4. [Cómo leer y ejecutar los notebooks](docs/04_notebooks_y_colab.md).
5. [Primer cuaderno: auditoría y unidad parcela](notebooks/01_auditoria_y_unidad_parcela.ipynb).
6. [Segundo cuaderno: de las fuentes a las variables](notebooks/02_fuentes_a_variables.ipynb).
7. [Tercer cuaderno: referencias y validación](notebooks/03_referencias_y_validacion.ipynb).
8. [Primera ronda: bloques de variables sobre municipio](notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb).
9. [Segunda ronda: ponderación temporal de tres medias](notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb).
10. [Tercera ronda: variables temporales y familias de modelos](notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb).
11. [Cuarta ronda: lluvia de octubre y agrupación territorial](notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb).
12. [Quinta ronda: histórico y lluvia actual de octubre](notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb).
13. [Sexta ronda: fecha de pico NDVI con soporte](notebooks/experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb).

Después de las seis rondas, la [síntesis y priorización del siguiente paso](docs/07_sintesis_y_priorizacion.md) explica qué aprendimos y qué queda por verificar. La [bitácora comparativa](gestion/bitacora_experimentos.md) reúne hipótesis, controles, presupuestos y cierres. El [plan propuesto de EXP_07](notebooks/experimentos/exp_07_heterogeneidad_parcela/PLAN_PROPUESTO.md) estudia heterogeneidad espacial de NDVI; **todavía no hay séptima corrida, protocolo ratificado ni notebook de resultados**.

Si aparece un término nuevo, consultar el [glosario breve](docs/06_glosario.md). No hace falta leerlo completo antes de empezar.

El formato común de los cuadernos es **pregunta → comprobación → resultado → decisión y límite**. Cada decisión se explica junto a la evidencia que la motiva. El orden de lectura es pedagógico; las fechas reales de los trabajos se conservan.

Los cuadernos **01–03** contienen sus salidas y se recalculan desde `data/raw/DataSet.zip`, cuya integridad se verifica antes de leerlo. En Colab utilizan Python 3.13 y, si falta el ZIP, descargan la copia de Drive autorizada por Fortino. El ID del archivo y su SHA-256 se incorporan desde el manifiesto al generar cada cuaderno.

La preparación de bibliotecas se anuncia antes de ejecutarla y solo opera en Colab. Si necesita reiniciar por un módulo ya cargado, lo solicita: no reinicia automáticamente. Los cuadernos 02 y 03 incorporan los mismos lectores verificados, sin cambiar la preparación del primero. Los paquetes locales `artefactos_locales/01_auditoria_equipo.zip`, `artefactos_locales/02_fuentes_equipo.zip` y `artefactos_locales/03_referencias_equipo.zip` permiten compartir notebook e insumos juntos, sin Git.

El cuaderno 02 sigue una parcela y generaliza a las 197. Reconstruye 539 columnas de metadatos, resúmenes y controles, con diccionario y etiquetas aparte. **No son 539 predictores seleccionados.** La comparación con la salida integrada del 21 de septiembre comprueba reconstrucción, no desempeño predictivo. Los controles históricos incorporados se usan solo después de calcular las variables.

El cuaderno 03 explica por qué necesitamos una referencia antes de incorporar complejidad. Reconstruye GLOBAL, MUN y MIX sobre las 50 particiones exteriores históricas, con **150 ajustes sencillos de referencia**. Comprueba las particiones internas para explicar validación anidada, sin seleccionar hiperparámetros. Muestra RMSE, MAE y R² sobre predicciones fuera de muestra; separa FULL138 y SEEN135 y no genera las 59 predicciones de entrega.

**EXP_01** estudia si clima/topografía, satélite del ciclo o historia agregaron información sobre municipio. Es un lector autónomo de la ronda del **21 de septiembre**, adaptado el **8 de octubre**: incorpora tablas históricas con tamaño y SHA-256, sin necesitar el ZIP original, Drive ni otro cuaderno. Ejecutarlo recalcula variables derivadas, métricas de predicciones OOF guardadas y la elección de alpha desde sus scores internos guardados; realiza **cero ajustes nuevos**. No reproduce el entrenamiento ni vuelve a calcular esos scores. Conserva FULL138 y la regla de comparación de esa ronda; E0 es Ridge municipal penalizado, no exactamente MUN. El paquete `artefactos_locales/exp_01_bloques_equipo.zip` permite compartirlo sin Git.

El resultado original se distingue de su reproducción: la historia E3 bajó algo el RMSE frente a E0, pero empeoró MAE, concentró su beneficio en pocas parcelas y no superó MIX. La lectura explica ese contraste sin adoptar un modelo final ni generar las 59 predicciones oficiales.

**EXP_02** pregunta si la frecuencia desigual de capturas puede tratarse cambiando tres medias satelitales de E2: NDVI Planet, NDVI Sentinel-2 y NDWI Sentinel-2. Primero calcula una media por mes; después pondera abril–octubre por sus días, **30, 31, 30, 31, 31, 30, 31 sobre 214**. Muestra las capturas de una parcela y comprueba las 197. Conserva sin cambios las otras tres variables, municipio, ventana, calidad, Ridge y particiones. No filtra nubes ni imputa meses.

Es la lectura autónoma de **T1, ejecutado el 29 de septiembre**, adaptada el **8 de octubre**. Incluye un recorte de capturas originales preparado en esa adaptación, con procedencia y hashes propios; no lo presenta como un nuevo insumo registrado antes de T1. Recalcula las variables y métricas desde OOF guardadas, sin reentrenar ni recalcular scores internos. T1 obtuvo RMSE **0.5225 t/ha**, frente a 0.5192 de E2 y 0.4938 de MIX: se cerró **sin adopción**. Cambiar una representación temporal no garantiza mejorar la predicción ni reconstruir el verdadero promedio diario.

**EXP_03** conserva las seis variables de E2 y añade cuatro descriptores de forma temporal: dos diferencias entre periodos y la amplitud de NDVI Planet, más una diferencia de NDWI Sentinel-2. Las capturas, medias mensuales y operaciones se muestran antes de compararlas con el control histórico. Son ventanas de calendario, no fechas de siembra o cosecha conocidas. A diferencia de T1, **añade información sin sustituir las medias originales**.

El diseño cruza dos representaciones con dos procedimientos: Ridge original y ampliado (**R_B/R_T**), y HistGradientBoosting original y ampliado (**H_B/H_T**). Así separa añadir el bloque de cambiar de familia, dentro de las rejillas registradas. Ninguna variante superó MIX/MUN; el bloque empeoró Ridge y, con HGB, redujo ligeramente RMSE mientras empeoró MAE. No demuestra inutilidad de toda ingeniería temporal ni de todos los árboles.

Es la lectura autónoma de **V1 del 29 de septiembre en México**, adaptada el **8 de octubre**. Recalcula cuatro variables y evalúa **9,660 OOF guardadas de siete procedimientos**; verifica 200 selecciones usando 900 scores guardados. Hace **cero ajustes actuales**, no recalcula los scores y no genera las 59 predicciones de entrega. La fecha UTC de la corrida, 30 de septiembre, se conserva junto a la fecha local del 29; no se presenta un registro previo nuevo.

**EXP_04** pregunta si la lluvia de octubre y su desviación respecto de 2022–2024 aportan información, y cómo cambia el resultado al agrupar municipios. Muestra los píxeles de una parcela, sus áreas válidas y la suma ponderada; generaliza a **788 lluvias parcela–año** y construye las variables de 197 parcelas. Usa **230 áreas de intersección históricas** y **116 valores de píxel derivados de los GeoTIFF originales el 8 de octubre**: recalcula la aritmética, **no vuelve a intersectar polígonos ni certifica una extracción geoespacial independiente**.

Conserva los cinco candidatos históricos y sus comparadores: **13,800 OOF de diez procedimientos**. Comprueba 200 selecciones desde 1,150 scores guardados, sin recalcular esos scores, entrenar modelos ni reconstruir nuevas predicciones. J5_PCT cumple la regla original en FULL138, pero no en el diagnóstico posterior SEEN135; este último no equivale al desempeño sobre las 59 ocultas. El candidato permanece **con reservas, no como modelo final**.

La lectura incorpora las precisiones del cierre: la representación porcentual mejora RMSE a costa de MAE, no es superior en general; cambiar grupos modifica conjuntamente medias, residuos, escala y respaldos. Tampoco demuestra causalidad de la lluvia ni que haya exactamente 23 observaciones independientes: son 23 celdas por centroide de las etiquetas, frente a 27 píxeles aportantes. El trabajo V2 es del **1 de octubre**, la adaptación del **8 de octubre**; su registro previo interno no borra la selección exploratoria anterior de la hipótesis.

**EXP_05** pregunta si el histórico corto H, la lluvia actual P o ambos explican la ventaja aparente del porcentaje. Calcula **H = media de octubre de 2022–2024**, **P = octubre de 2025** y **A_pct = 100 × (P − H) / H** desde las cuatro lluvias guardadas de las 197 parcelas. No vuelve a leer GeoTIFF ni a intersectar polígonos. Tres años no son una normal climatológica; una correlación con el denominador no demuestra que H sola prediga mejor.

La comparación mantiene municipio, Ridge, ventana, extracción, particiones y rejilla: **R9_H, R9_HP, R9_P y R9_PCT**, con MUN/MIX como referencias y J5_PCT como contexto histórico. El escenario principal **SEEN135** se fijó antes de ajustar V3; FULL138 se conserva como secundario. No cambia retrospectivamente la evaluación de V2 ni garantiza el error de las 59 ocultas. Ninguna receta avanza: H y H+P quedan detrás del porcentaje en RMSE, y este tampoco cumple la regla conservadora.

Es el lector autónomo de **V3 del 1 de octubre en México —2 de octubre UTC—**, adaptado el **8 de octubre**. Incorpora 21 insumos; recalcula las variables, evalúa **9,660 OOF guardadas de siete procedimientos** y verifica **200 selecciones desde 1,200 scores guardados**. No recalcula los scores, reentrena ni produce nuevas predicciones. La comparación es exploratoria: el registro de esta ronda no elimina el uso anterior de las mismas etiquetas.

Cuando un municipio solo tiene un rendimiento observado repetido, R² no está definido. El lector muestra NaN en 14 entradas numéricamente espurias de Tepeapulco, preservando el CSV histórico; RMSE, MAE y decisiones no cambian.

**EXP_06** pregunta si una fecha de máximo menos sensible a una captura aislada mejora E2. Calcula primero NDVI diario de Planet; después una mediana móvil centrada de **±7 días de calendario**, con al menos tres días finitos. Las guardas de cobertura, amplitud y soporte bilateral determinan si la fecha se conserva o queda ausente. **Solo sustituye la fecha de pico crudo de E2**: mantiene las otras cinco variables numéricas y municipio. La bandera de soporte es un diagnóstico, no un predictor adicional.

La receta produce fechas soportadas en **158 de 197 parcelas**; deja 39 ausentes, incluidas 30 etiquetadas. No elimina esas parcelas: el procedimiento histórico imputó la mediana aprendida exclusivamente en cada entrenamiento. La fecha suavizada no es una fecha de floración verificada y una curva más interpretable no garantiza mejores predicciones.

V4, ejecutado el **6 de octubre**, conserva SEEN135 principal y FULL138 secundario. En SEEN135 baja RMSE de E2 **0.5065 → 0.5015 t/ha**, pero MAE empeora ligeramente y no alcanza MIX, **0.4872**. Frente a E2 mejora RMSE en 9/10 repeticiones; frente a MIX, en ninguna. Se cerró **sin adopción**. El beneficio se concentra en pocos casos y no resuelve la variación dentro de Chignahuapan.

La adaptación del **8 de octubre** incorpora 24 insumos, incluido un recorte identificado de **26,255 capturas Planet**. Reconstruye la fecha, evalúa **6,900 OOF guardadas de cinco procedimientos** y verifica **100 selecciones desde 500 scores guardados**, sin recalcular los scores ni reentrenar. La factibilidad del 2 de octubre y el registro de V4 conservan sus fechas. El lector está **verificado localmente, sin reentrenar**; no se declara una ejecución de Colab ni se generan las 59 predicciones de entrega.

## Ejecutar en local

Desde esta carpeta, con uv instalado:

```bash
uv sync --locked --all-groups
uv run --locked --all-groups python scripts/verificar_entorno.py --completo
uv run --locked --all-groups pytest -q
uv run --locked --all-groups ruff check scripts tests
uv run --locked --all-groups jupyter lab
```

Seleccionar el Python de `.venv` en Jupyter. El proyecto utiliza la serie **Python 3.13** y fija **3.13.13** en local. `uv.lock` fija las dependencias; la verificación comprueba versiones antes de trabajar. Cambiar intérprete no significa cambiar la receta de datos ni aceptar nuevas hipótesis predictivas.

Para recalcular la auditoría en un kernel nuevo y guardar una ejecución separada:

```bash
uv run --locked --all-groups python scripts/ejecutar_notebook_01.py
```

La salida se guarda en `resultados_locales/auditoria_01/`, sin sobrescribir el cuaderno de lectura ni los insumos.

Para recalcular el recorrido de fuentes a variables:

```bash
uv run --locked --all-groups python scripts/ejecutar_notebook_02.py
```

La ejecución se guarda en `resultados_locales/fuentes_02/`. Cada cuaderno puede ejecutarse por separado; el segundo no necesita las variables de una sesión previa del primero.

Para reconstruir las referencias y su evaluación:

```bash
uv run --locked --all-groups python scripts/ejecutar_notebook_03.py
```

La ejecución se guarda en `resultados_locales/referencias_03/`. Las particiones y los controles históricos vienen incrustados en el cuaderno; no se necesitan otro notebook ni descargas adicionales. Los controles de salida se abren después de predecir, no alimentan los estimadores.

Para recalcular los resultados guardados de la primera ronda, sin reentrenar:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_01.py
```

La ejecución se guarda en `resultados_locales/exp_01_bloques/`, sin sobrescribir la evidencia original. `scripts/construir_exp_01.py` genera el lector a partir de los insumos identificados; el cuaderno incorpora esos insumos y puede ejecutarse solo. La ronda original utilizó Python 3.10.12 y scikit-learn 1.7.2; esta lectura utiliza el entorno Python 3.13 del proyecto. La coincidencia de métricas desde OOF guardados no demuestra paridad del entrenamiento entre entornos.

Para recalcular las variables temporales y resultados guardados de T1:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_02.py
```

La salida se guarda en `resultados_locales/exp_02_ponderacion_temporal/`. El generador `scripts/construir_exp_02.py` utiliza `config/exp_02_ponderacion_temporal.json`; el notebook contiene sus insumos y no necesita ZIP, Drive ni ejecutar otro cuaderno. La distribución local es `artefactos_locales/exp_02_ponderacion_temporal_equipo.zip`. **Cero ajustes actuales** y ninguna predicción final de las 59 parcelas. T1 utilizó Python 3.12.14/scikit-learn 1.9.1; el control histórico de E2 se distingue de esta lectura en Python 3.13.

Para reconstruir las cuatro variables y recalcular los resultados guardados de V1:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_03.py
```

La salida se conserva en `resultados_locales/exp_03_variables_y_familias/`. `scripts/construir_exp_03.py` utiliza `config/exp_03_variables_y_familias.json`; los insumos y controles quedan incorporados en el notebook, sin archivos externos ni otro cuaderno. La distribución local es `artefactos_locales/exp_03_variables_y_familias_equipo.zip`. La corrida histórica utilizó Python 3.12.14/scikit-learn 1.9.1 y 3,800 ajustes; el lector en Python 3.13 **no reproduce esos ajustes**. Coincidir en métricas guardadas no acredita paridad de entrenamiento entre entornos.

Para recalcular la aritmética espacial y evaluar los resultados guardados de V2:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_04.py
```

La salida se guarda en `resultados_locales/exp_04_lluvia_octubre/`. El generador `scripts/construir_exp_04.py` utiliza `config/exp_04_lluvia_octubre.json`; el notebook contiene sus insumos sin necesitar ZIP, Drive, GeoTIFF externos ni otro cuaderno. La distribución local es `artefactos_locales/exp_04_lluvia_octubre_equipo.zip`. El entrenamiento histórico utilizó **Python 3.12.3/scikit-learn 1.9.1**; esta lectura usa Python 3.13 y hace **cero ajustes**. Reproducir variables desde áreas guardadas y métricas desde OOF no demuestra paridad de extracción completa ni de entrenamiento entre entornos.

Para reconstruir las representaciones de octubre y evaluar los resultados guardados de V3:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_05.py
```

La salida se conserva en `resultados_locales/exp_05_historico_octubre/`. `scripts/construir_exp_05.py` utiliza `config/exp_05_historico_octubre.json`; el notebook contiene sus insumos y no necesita ZIP, Drive, rásteres ni otro cuaderno. La distribución local es `artefactos_locales/exp_05_historico_octubre_equipo.zip`. V3 utilizó Python **3.12.14**; el lector Python 3.13 hace **cero ajustes** y no repite las 4,800 evaluaciones interiores ni 200 reajustes exteriores históricos. Coincidir en variables y métricas guardadas no demuestra paridad de entrenamiento entre entornos.

Para reconstruir la fecha soportada y evaluar los resultados guardados de V4:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_06.py
```

La salida se conserva en `resultados_locales/exp_06_pico_soportado/`. `scripts/construir_exp_06.py` utiliza `config/exp_06_pico_soportado.json`; el notebook incorpora sus insumos sin ZIP, Drive ni otro cuaderno. La distribución local es `artefactos_locales/exp_06_pico_soportado_equipo.zip`. V4 usó Python **3.12.14**; este lector Python 3.13 hace **cero ajustes**, no repite los 2,100 ajustes por corrida histórica ni demuestra paridad del entrenamiento entre entornos. Dos corridas históricas sumaron 4,200 ajustes físicos para comprobar determinismo, no dos candidatos nuevos.

| Grupo         | Para qué sirve                           |
| ------------- | ----------------------------------------- |
| Núcleo       | Tablas, estadística, métricas y modelos |
| `notebooks` | Cuadernos, gráficos y Jupyter            |
| `geo`       | Geometrías, ráster y proyecciones       |
| `colab`     | Descarga con gdown y gráficos            |
| `dev`       | Pruebas y revisión del código           |

## Información técnica opcional

La [verificación técnica](docs/05_verificacion_preparacion.md) y el [registro operativo](gestion/estado_y_decisiones.md) documentan comprobaciones, alcance de la edición y tareas de mantenimiento. No forman parte del recorrido de estudio ni sustituyen la evidencia de los cuadernos.
