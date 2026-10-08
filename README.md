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

| Grupo         | Para qué sirve                           |
| ------------- | ----------------------------------------- |
| Núcleo       | Tablas, estadística, métricas y modelos |
| `notebooks` | Cuadernos, gráficos y Jupyter            |
| `geo`       | Geometrías, ráster y proyecciones       |
| `colab`     | Descarga con gdown y gráficos            |
| `dev`       | Pruebas y revisión del código           |

## Información técnica opcional

La [verificación técnica](docs/05_verificacion_preparacion.md) y el [registro operativo](gestion/estado_y_decisiones.md) documentan comprobaciones, alcance de la edición y tareas de mantenimiento. No forman parte del recorrido de estudio ni sustituyen la evidencia de los cuadernos.
