# AgroCebada

Este proyecto reúne la explicación y la evidencia reproducible para predecir el rendimiento de las parcelas de cebada del reto. El recorrido parte del problema, comprueba los datos, construye variables y compara hipótesis hasta justificar una solución.

**La lectura principal está dentro de esta carpeta.** No requiere conocer documentos previos ni los nombres usados durante la exploración. Los aportes de Andrea y Jared se reconocen en las comprobaciones correspondientes; sus documentos originales son contexto adicional, no un requisito de lectura.

## Recorrido para el equipo

1. [El problema y las preguntas del recorrido](docs/01_contexto_y_estado.md).
2. [Cómo investigamos y por qué usamos esta metodología](docs/02_metodologia.md).
3. [Etapas y evidencias que produce cada una](docs/03_plan_de_trabajo.md).
4. [Cómo leer y ejecutar los notebooks](docs/04_notebooks_y_colab.md).
5. [Primer cuaderno: auditoría y unidad parcela](notebooks/01_auditoria_y_unidad_parcela.ipynb).

Si aparece un término nuevo, consultar el [glosario breve](docs/06_glosario.md). No hace falta leerlo completo antes de empezar.

El formato común de los cuadernos es **pregunta → comprobación → resultado → decisión y límite**. Cada decisión se explica junto a la evidencia que la motiva. El orden de lectura es pedagógico; las fechas reales de los trabajos se conservan.

El primer cuaderno contiene sus salidas y se recalcula desde `data/raw/DataSet.zip`, cuya integridad se verifica antes de leerlo. En Colab utiliza Python 3.13 y, si falta el ZIP, descarga la copia de Drive autorizada por Fortino. El ID del archivo y su SHA-256 se incorporan desde el manifiesto al generar el cuaderno.

La preparación de bibliotecas se anuncia antes de ejecutarla y solo opera en Colab. Si necesita reiniciar por un módulo ya cargado, lo solicita: no reinicia automáticamente. Para compartir notebook e insumos juntos, sin Git, sigue disponible el paquete local `artefactos_locales/01_auditoria_equipo.zip`.

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

| Grupo         | Para qué sirve                           |
| ------------- | ----------------------------------------- |
| Núcleo       | Tablas, estadística, métricas y modelos |
| `notebooks` | Cuadernos, gráficos y Jupyter            |
| `geo`       | Geometrías, ráster y proyecciones       |
| `colab`     | Descarga con gdown y gráficos            |
| `dev`       | Pruebas y revisión del código           |

## Información técnica opcional

La [verificación técnica](docs/05_verificacion_preparacion.md) y el [registro operativo](gestion/estado_y_decisiones.md) documentan comprobaciones, alcance de la edición y tareas de mantenimiento. No forman parte del recorrido de estudio ni sustituyen la evidencia de los cuadernos.
