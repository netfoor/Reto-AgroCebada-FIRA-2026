# 05. Qué está verificado y qué falta

Edición del 7 de octubre de 2026. Esta comprobación cubre entorno, auditoría descriptiva, acceso a insumos y reconstrucción de variables; no equivale a evaluar un modelo nuevo.

## Entorno preparado

- Python 3.13.13 en local y serie 3.13 en Colab; NumPy 2.4.4, pandas 2.2.3, SciPy 1.18.0 y scikit-learn 1.9.1.
- Bloqueo generado por uv 0.11.7: 124 paquetes resueltos entre plataformas y 120 distribuciones instaladas en este Linux.
- 175 pruebas, sin fallos ni omisiones, y revisión con Ruff: pasan con Python 3.13.13. Incluyen datos sintéticos, fuentes reales, recetas y autonomía de ambos cuadernos. La migración inicial había comprobado 102 pruebas e importación de 14 módulos; se conserva su registro.
- `uv sync --check --locked --all-groups --offline`: entorno sincronizado.
- `requirements-colab.txt` y `requirements-colab-auditoria.txt` exportados desde el bloqueo; conservan exactamente los perfiles anteriores.

La preparación inicial se hizo con Python 3.12.14. La migración a 3.13.13 conserva los 124 pares paquete–versión; no cambia modelos, datos ni criterios de evaluación. El entorno anterior se conserva como copia recuperable, no como segunda versión de trabajo.

Las comprobaciones se registran con versión y alcance. Importar correctamente una biblioteca no prueba la receta de extracción ni la capacidad predictiva de un modelo.

## Evidencia y cambios controlados

El catálogo identifica seis rondas y conserva su procedencia. En la preparación inicial se contrastaron 25 fuentes y los dos CSV de particiones sin cambios. Estos controles son trazabilidad técnica, no lectura adicional obligatoria para el equipo.

El primer notebook se ejecutó completo en kernels nuevos con Python 3.13.13: 18 celdas de código, cero errores. Los 14 bloques preservados —el lector y 13 de análisis— son idénticos a los de la versión anterior. Sus tablas, resúmenes numéricos y dos PNG también coinciden, normalizando únicamente la fecha de ejecución. La celda adicional contiene soporte técnico de Colab y descarga, no análisis nuevo.

Se comprobó una descarga real desde el enlace de Drive autorizado por Fortino: mismo tamaño y SHA-256 que el ZIP original, sin cookies. Los controles sintéticos cubren caché, descarga rechazada, concurrencia, instalación y reinicio solicitado. Fortino confirmó después que el cuaderno 01 actualizado funciona en Colab: se registra como evidencia reportada por el usuario, no ejecución independiente de Codex.

## Segundo cuaderno: reconstrucción verificada

El cuaderno 02 sigue AGC_001 y generaliza a 197 parcelas. Se ejecutó en dos kernels nuevos de Python 3.13.13: 18 celdas de código, cero errores. La segunda ejecución se hizo desde una carpeta con solo el notebook y el ZIP, sin Git, scripts ni tablas de referencia externas. Sus salidas y tres PNG coinciden, normalizando únicamente la fecha de ejecución.

- Tabla base: 197 × 539, incluyendo ID, metadatos, variables candidatas y controles. Etiquetas separadas: 138. No se seleccionan 539 predictores.
- Postciclo: 197 × 122, con ID y 121 estadísticas. No entra en la base; el diccionario reúne 660 entradas sin duplicar el ID.
- Las 538 columnas de base y las 121 de postciclo distintas del ID reproducen sus controles históricos. Orden, claves y máscaras de faltantes se validan; conteos y textos son exactos. Tolerancias numéricas absolutas: 10⁻⁸ en metadatos, satélite y clima; 10⁻⁴ en topografía, en unidades de cada columna.
- 146 rásteres, tres mallas exactas y 28,368 registros climáticos parcela–variable–año–mes. Pruebas sintéticas cubren malla rotada y desplazada, contacto de área cero, centros frente a esquinas, máscaras, NoData y caché con distintos conjuntos de geometrías.
- La base conserva tres NaN en el control de pendiente por centroide; no imputa. La cobertura respecto al área total se muestra aparte de la cobertura histórica. El valor de pendiente de AGC_170 existe sobre aproximadamente 2.1 % de cobertura: reproducirlo no demuestra que represente toda la parcela.

Los CSV históricos incrustados tienen controles de tamaño y SHA-256 y se abren únicamente después de reconstruir las variables. Son referencias de salida, no insumos de extracción. Los originales de Andrea, Jared y la integración previa no se editan. El cuaderno 01 y los archivos de configuración del entorno uv conservan sus hashes.

Las recetas originales corresponden a la integración del 21 de septiembre; la verificación de extracción del 1 de octubre es un antecedente. El código educativo y sus comprobaciones actuales son del 7 de octubre. No se presentan como un preregistro retrospectivo ni como una ronda predictiva nueva.

Los registros anteriores conservan su fecha y alcance. El registro de esta migración documenta archivos, pruebas y recuperación del entorno anterior. Los informes de preparación no se reescriben como si hubieran usado Python 3.13 desde el comienzo.

## Pendiente antes de una entrega completa

- Incorporar las seis rondas predictivas con el formato común; comprobar sus ejecuciones y la paridad de resultados en este entorno.
- Ejecutar el cuaderno 02 en una sesión real de Colab. La autonomía local y el acceso a Drive están verificados, pero no se confunden con esa comprobación. El cuaderno 01 sí tiene confirmación de Fortino en Colab.
- Verificar las 59 predicciones de entrega y la herramienta que las consulta.

Todavía no se ha entrenado en este proyecto ni generado predicciones finales. Codex no ha subido datos a la nube ni cambiado permisos; el ZIP de Drive lo compartió Fortino. `main.py` continúa como plantilla; no es una aplicación de predicción.
