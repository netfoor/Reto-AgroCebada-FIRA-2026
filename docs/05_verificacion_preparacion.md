# 05. Qué está verificado y qué falta

Edición del 7 de octubre de 2026. Esta comprobación cubre entorno, auditoría descriptiva y acceso a los insumos; no equivale a evaluar un modelo nuevo.

## Entorno preparado

- Python 3.13.13 en local y serie 3.13 en Colab; NumPy 2.4.4, pandas 2.2.3, SciPy 1.18.0 y scikit-learn 1.9.1.
- Bloqueo generado por uv 0.11.7: 124 paquetes resueltos entre plataformas y 120 distribuciones instaladas en este Linux.
- 102 pruebas, revisión con Ruff e importación de 14 módulos: pasan con Python 3.13.13.
- `uv sync --check --locked --all-groups --offline`: entorno sincronizado.
- `requirements-colab.txt` y `requirements-colab-auditoria.txt` exportados desde el bloqueo; conservan exactamente los perfiles anteriores.

La preparación inicial se hizo con Python 3.12.14. La migración a 3.13.13 conserva los 124 pares paquete–versión; no cambia modelos, datos ni criterios de evaluación. El entorno anterior se conserva como copia recuperable, no como segunda versión de trabajo.

Las comprobaciones se registran con versión y alcance. Importar correctamente una biblioteca no prueba la receta de extracción ni la capacidad predictiva de un modelo.

## Evidencia y cambios controlados

El catálogo identifica seis rondas y conserva su procedencia. En la preparación inicial se contrastaron 25 fuentes y los dos CSV de particiones sin cambios. Estos controles son trazabilidad técnica, no lectura adicional obligatoria para el equipo.

El primer notebook se ejecutó completo en kernels nuevos con Python 3.13.13: 18 celdas de código, cero errores. Los 14 bloques preservados —el lector y 13 de análisis— son idénticos a los de la versión anterior. Sus tablas, resúmenes numéricos y dos PNG también coinciden, normalizando únicamente la fecha de ejecución. La celda adicional contiene soporte técnico de Colab y descarga, no análisis nuevo.

Se comprobó una descarga real desde el enlace de Drive autorizado por Fortino: mismo tamaño y SHA-256 que el ZIP original, sin cookies. Los controles sintéticos cubren caché, descarga rechazada, concurrencia, instalación y reinicio solicitado; no sustituyen una prueba real del cuaderno actualizado dentro de Colab.

Los registros anteriores conservan su fecha y alcance. El registro de esta migración documenta archivos, pruebas y recuperación del entorno anterior. Los informes de preparación no se reescriben como si hubieran usado Python 3.13 desde el comienzo.

## Pendiente antes de una entrega completa

- Incorporar los notebooks, insumos y resultados con el formato común.
- Comprobar sus ejecuciones y la paridad con los resultados documentados en este entorno.
- Ejecutar el nuevo notebook generado en una sesión real de Colab. La descarga autorizada ya se verificó con el mismo cliente; la prueba de la copia previa de Fortino es evidencia reportada, no ejecución independiente de esta versión.
- Verificar las 59 predicciones de entrega y la herramienta que las consulta.

Todavía no se ha entrenado en este proyecto ni generado predicciones finales. Codex no ha subido datos a la nube ni cambiado permisos; el ZIP de Drive lo compartió Fortino. `main.py` continúa como plantilla; no es una aplicación de predicción.
