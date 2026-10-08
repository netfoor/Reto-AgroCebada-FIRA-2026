# 04. Cómo estudiar y ejecutar los notebooks

Edición del 7 de octubre de 2026. Esta guía define el formato de lectura, comprobación y ejecución de los cuadernos.

## Una historia comprobable, no un conjunto de scripts

Cada notebook debe responder una pregunta central. La explicación y las salidas permiten entender qué se comprueba y qué se puede concluir, sin recurrir a trabajos previos.

**Encabezado común:** pregunta, etapa(s) CRISP-DM, objetivo, fuentes, fecha del trabajo original y fecha de adaptación. Si retomamos una etapa, explicamos qué evidencia motivó el regreso.

**Cada bloque de celdas sigue este patrón:**

1. **Qué comprobamos y por qué importa:** explicación breve antes del código.
2. **Cómo lo comprobamos:** operación y controles visibles.
3. **Qué obtuvimos:** tabla, gráfico o prueba reproducible.
4. **Qué significa:** interpretación, decisión posible y límite.

Ejemplo de presentación de un aporte: “Andrea propuso este resumen; aquí reconstruimos su receta y comparamos por ID”. La salida permite distinguir coincidencia de cálculo de diferencias de definición. El nombre de fuente y la fecha deben estar documentados.

## Orden de lectura

| Parte del recorrido | Qué debe demostrar | Etapa principal |
|---|---|---|
| Contexto y metodología | Objetivo y organización del trabajo | Entender el problema |
| `01_auditoria_y_unidad_parcela` | Qué contiene el dataset y qué limita su uso | Entender los datos |
| `02_fuentes_a_variables` | Cómo una parcela se convierte en una fila de variables | Preparar los datos |
| `03_referencias_y_validacion` | Referencias y comparaciones fuera de muestra | Modelar y evaluar |
| `exp_01` a `exp_06` | Hipótesis, contraste y cierre de cada ronda | Preparar, modelar y evaluar |

Los nombres organizan la lectura; los IDs de los experimentos se conservan como metadatos. “E2” es el nombre de un procedimiento de control, no del segundo cuaderno.

## Formato común de resultados

Antes de una tabla de modelos se indican **escenario, parcelas distintas, predicciones OOF, particiones, unidades y referencia del contraste**. Todas sus filas se puntúan sobre la misma población.

La tabla muestra: **procedimiento, RMSE, MAE, R², cambio frente a la referencia y criterio de avance**. Incluimos estabilidad por repetición y región cuando corresponde. Los resultados de FULL138 y SEEN135 se presentan separados.

Si la pregunta es de extracción o calidad, mostramos cobertura, diferencias entre recetas o controles pertinentes, no una tabla de modelos innecesaria. Siempre distinguimos “cálculo verificado” de “hipótesis predictiva apoyada”.

**Cierre común:** respuesta a la pregunta, decisión, límites y siguiente pregunta. No escondemos resultados desfavorables ni tratamos las repeticiones como parcelas nuevas.

## Qué hace ejecutar una celda

- **Leer:** muestra salidas documentadas.
- **Recalcular:** vuelve a calcular variables, métricas o controles; identifica si utiliza resultados guardados y no entrena por defecto.
- **Reentrenar:** repite ajustes de forma explícita, con presupuesto y salida nuevos.

El modo debe estar identificado antes de la primera ejecución. Estudiar la evidencia no debe activar por sorpresa miles de ajustes.

## Entorno local y Colab

Local y Colab utilizan **Python 3.13**. En local, uv prepara `.venv` y `.python-version` fija el parche 3.13.13. Colab administra su intérprete: comprobamos que pertenezca a la serie 3.13 y registramos el parche real, sin afirmar que uv controle su runtime (Astral, s. f.-d; Google, s. f.).

Para trabajar sin Git, el notebook incluye su lector y soporte técnico con hashes. Deben conservarse variables, particiones y fórmulas, además de comprobar versiones y resultados; exportar dependencias no demuestra por sí solo la paridad (Astral, s. f.-b, s. f.-c).

`requirements-colab.txt` se genera desde `uv.lock`, sin editar versiones a mano (Astral, s. f.-a):

```bash
uv export --locked --no-default-groups --group colab --no-emit-project --no-hashes --no-header --output-file requirements-colab.txt
```

El perfil incluye núcleo, gráficos y gdown. El perfil `requirements-colab-auditoria.txt` incorpora también `geo`, exportado con el mismo comando y `--group geo`.

Los cuadernos se ejecutan por separado. El 01 necesita sus bibliotecas de lectura y geometría; el 02 añade Rasterio para leer los GeoTIFF directamente desde el ZIP en memoria. Ambos incluyen todo el código que utilizan y comparten el contrato del ZIP original. No requieren Git ni haber ejecutado otro notebook.

**Preparación visible en Colab:** antes de leer datos, `PREPARAR_COLAB = True` permite instalar las bibliotecas requeridas cuya versión falta o difiere. La celda imprime el plan, utiliza paquetes binarios y limita las dependencias necesarias mediante el perfil de uv. No intenta reinstalar todo el entorno de Google ni modifica el entorno local.

Si cambia un módulo ya importado, la ejecución se detiene y solicita reiniciar la sesión y ejecutar todas las celdas. No mata el proceso ni reinicia automáticamente. La comprobación cubre las bibliotecas utilizadas, no todos los paquetes preinstalados de Colab; los avisos sobre bibliotecas ajenas se distinguen de un fallo de la auditoría.

## Identificación y comprobación de insumos

Cada cuaderno identifica sus entradas por **nombre, versión, contenido, tamaño y SHA-256**. El bloque de acceso explica dónde obtener el paquete y qué permisos requiere, sin depender de rutas personales ni ocultar una autenticación necesaria.

Para el cuaderno 01, Fortino compartió y autorizó la descarga del ZIP original desde Drive. Su ID figura en `config/auditoria_01_dataset.json` y se incorpora al generar el notebook; no es el ID del cuaderno. En Colab se descarga solo si falta una copia local. En local no se conecta a Drive por defecto. gdown no cambia permisos ni sustituye una autorización: si el acceso o la cuota fallan, el cuaderno se detiene (Wada, s. f.).

La descarga llega a un archivo temporal y solo se acepta tras comprobar tamaño y SHA-256. Una caché incorrecta no se sustituye silenciosamente; una descarga rechazada queda separada para diagnóstico. Una caché correcta se reutiliza sin conexión. No se utilizan cookies del navegador.

Antes de usar un paquete se comprueba su integridad. Al descomprimir se rechazan rutas inseguras, colisiones inesperadas y tamaños fuera de los límites definidos. Ante un archivo incorrecto o incompleto, la ejecución se detiene con un mensaje claro.

Estos controles son los mismos independientemente del proveedor de almacenamiento. Las credenciales no forman parte del contenido compartido del notebook.

## Para profundizar — referencias APA 7

Astral. (s. f.-a). *Exporting lockfiles*. https://docs.astral.sh/uv/concepts/projects/export/

Astral. (s. f.-b). *Managing dependencies*. https://docs.astral.sh/uv/concepts/projects/dependencies/

Astral. (s. f.-c). *Using uv with Jupyter*. https://docs.astral.sh/uv/guides/integration/jupyter/

Google. (s. f.). *Colaboratory: Frequently asked questions*. https://research.google.com/colaboratory/faq.html

Astral. (s. f.-d). *Python versions*. https://docs.astral.sh/uv/concepts/python-versions/

Wada, K. (s. f.). *gdown: Google Drive public file downloader* [Software]. GitHub. https://github.com/wkentaro/gdown
