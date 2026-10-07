# Notebooks — recorrido de evidencia

El recorrido de estudio es **auditoría → fuentes y variables → referencias y validación → seis rondas**. El contexto y la metodología presentan el objetivo antes de empezar con las comprobaciones.

## 01. Entender los datos

[Auditoría y unidad de observación](01_auditoria_y_unidad_parcela.ipynb) responde qué contienen los insumos y cuántos rendimientos conocemos realmente. Incluye inventario, controles de etiquetas y fechas, cobertura por sensor, distribución territorial y límites de interpretación.

El cuaderno contiene las salidas de una ejecución comprobada y su código completo. **Leer no requiere ejecutar; recalcular no entrena modelos ni modifica el ZIP original.** Local y Colab utilizan Python 3.13. La preparación de bibliotecas se anuncia y solo opera en Colab; si requiere reinicio, lo pide sin reiniciar automáticamente.

En local utiliza `data/raw/DataSet.zip`. En Colab puede descargar la copia autorizada de Drive si no existe una copia local. Ambos caminos exigen el mismo tamaño y SHA-256 antes de leer el archivo. Una caché válida evita descargarlo de nuevo; una incorrecta detiene la ejecución. La celda de acceso permite señalar otra ubicación del mismo ZIP.

Cada cuaderno explica su etapa CRISP-DM y, cuando corresponde, por qué volvemos a una etapa anterior. Cada bloque incluye pregunta y motivo, operación, salida e interpretación. El cierre reúne respuesta, decisión, límite y siguiente pregunta.

Las comprobaciones de aportes de Andrea y Jared incluyen explicación y contraste, sin exigir leer sus documentos. Los modos **leer, recalcular y reentrenar** se identifican antes de ejecutar; por defecto no se realizan nuevos ajustes.

El [formato común](../docs/04_notebooks_y_colab.md) define estas convenciones. El [glosario](../docs/06_glosario.md) permite consultar términos sin interrumpir el recorrido.
