# 05. Qué está verificado y qué falta

Edición del 8 de octubre de 2026. Esta comprobación cubre entorno, auditoría descriptiva, acceso a insumos, reconstrucción de variables, reproducción de referencias predictivas e incorporación de lectores de las dos primeras rondas; no equivale a evaluar un candidato nuevo.

## Entorno preparado

- Python 3.13.13 en local y serie 3.13 en Colab; NumPy 2.4.4, pandas 2.2.3, SciPy 1.18.0 y scikit-learn 1.9.1.
- Bloqueo generado por uv 0.11.7: 124 paquetes resueltos entre plataformas y 120 distribuciones instaladas en este Linux.
- La edición de referencias había comprobado 241 pruebas, sin fallos ni omisiones, y revisión con Ruff en Python 3.13.13. Incluyen datos sintéticos, fuentes reales, recetas, particiones, referencias, autonomía de los tres cuadernos, presentación Colab y ejemplos de cálculo visibles. La edición didáctica del 02 había comprobado 232 pruebas; la de presentación, 224; la de referencias, 220; la de variables, 175; la migración inicial, 102 e importación de 14 módulos. Se conservan sus registros y alcances. El cierre de EXP_01 incorpora 28 pruebas más; la verificación actual se detalla abajo.
- `uv sync --check --locked --all-groups --offline`: entorno sincronizado.
- `requirements-colab.txt` y `requirements-colab-auditoria.txt` exportados desde el bloqueo; conservan exactamente los perfiles anteriores.

La preparación inicial se hizo con Python 3.12.14. La migración a 3.13.13 conserva los 124 pares paquete–versión; no cambia modelos, datos ni criterios de evaluación. El entorno anterior se conserva como copia recuperable, no como segunda versión de trabajo.

Las comprobaciones se registran con versión y alcance. Importar correctamente una biblioteca no prueba la receta de extracción ni la capacidad predictiva de un modelo.

## Evidencia y cambios controlados

El catálogo identifica seis rondas y conserva su procedencia. En la preparación inicial se contrastaron 25 fuentes y los dos CSV de particiones sin cambios. Estos controles son trazabilidad técnica, no lectura adicional obligatoria para el equipo.

El primer notebook se ejecutó completo en kernels nuevos con Python 3.13.13: 18 celdas de código, cero errores. Los 14 bloques preservados —el lector y 13 de análisis— son idénticos a los de la versión anterior. Sus tablas, resúmenes numéricos y dos PNG también coinciden, normalizando únicamente la fecha de ejecución. La celda adicional contiene soporte técnico de Colab y descarga, no análisis nuevo.

Se comprobó una descarga real desde el enlace de Drive autorizado por Fortino: mismo tamaño y SHA-256 que el ZIP original, sin cookies. Los controles sintéticos cubren caché, descarga rechazada, concurrencia, instalación y reinicio solicitado. Fortino confirmó después que el cuaderno 01 actualizado funciona en Colab: se registra como evidencia reportada por el usuario, no ejecución independiente de Codex.

## Segundo cuaderno: reconstrucción verificada

El cuaderno 02 sigue AGC_001 y generaliza a 197 parcelas. Su primera edición se ejecutó en dos kernels nuevos de Python 3.13.13: 18 celdas de código, cero errores. La segunda ejecución se hizo desde una carpeta con solo el notebook y el ZIP, sin Git, scripts ni tablas de referencia externas. Sus salidas y tres PNG coinciden, normalizando únicamente la fecha de ejecución.

- Tabla base: 197 × 539, incluyendo ID, metadatos, variables candidatas y controles. Etiquetas separadas: 138. No se seleccionan 539 predictores.
- Postciclo: 197 × 122, con ID y 121 estadísticas. No entra en la base; el diccionario reúne 660 entradas sin duplicar el ID.
- Las 538 columnas de base y las 121 de postciclo distintas del ID reproducen sus controles históricos. Orden, claves y máscaras de faltantes se validan; conteos y textos son exactos. Tolerancias numéricas absolutas: 10⁻⁸ en metadatos, satélite y clima; 10⁻⁴ en topografía, en unidades de cada columna.
- 146 rásteres, tres mallas exactas y 28,368 registros climáticos parcela–variable–año–mes. Pruebas sintéticas cubren malla rotada y desplazada, contacto de área cero, centros frente a esquinas, máscaras, NoData y caché con distintos conjuntos de geometrías.
- La base conserva tres NaN en el control de pendiente por centroide; no imputa. La cobertura respecto al área total se muestra aparte de la cobertura histórica. El valor de pendiente de AGC_170 existe sobre aproximadamente 2.1 % de cobertura: reproducirlo no demuestra que represente toda la parcela.

Los CSV históricos incrustados tienen controles de tamaño y SHA-256 y se abren únicamente después de reconstruir las variables. Son referencias de salida, no insumos de extracción. Los originales de Andrea, Jared y la integración previa no se editan. El cuaderno 01 y los archivos de configuración del entorno uv conservan sus hashes.

Las recetas originales corresponden a la integración del 21 de septiembre; la verificación de extracción del 1 de octubre es un antecedente. El código educativo y sus comprobaciones actuales son del 7 de octubre. No se presentan como un preregistro retrospectivo ni como una ronda predictiva nueva.

Los registros anteriores conservan su fecha y alcance. El registro de esta migración documenta archivos, pruebas y recuperación del entorno anterior. Los informes de preparación no se reescriben como si hubieran usado Python 3.13 desde el comienzo.

## Tercer cuaderno: referencias y validación verificadas

El cuaderno 03 reproduce GLOBAL, MUN y MIX en las particiones guardadas del 20 de septiembre, con las recetas de la integración del 21. Su primera edición se ejecutó en dos kernels nuevos de Python 3.13.13: 17 celdas de código, cero errores. La segunda carpeta contenía únicamente notebook y ZIP: sin Git, módulos ni CSV externos. Salidas y tres PNG coinciden, normalizando solo la fecha de ejecución.

- Se comprueban los 50 entrenamientos exteriores y 200 particiones internas, excluyendo de estas últimas la validación exterior. Las internas explican dónde se seleccionaría un ajuste; en este cuaderno no seleccionan nada.
- Tres referencias × 138 parcelas × diez repeticiones: 4,140 predicciones OOF. Sus claves, rendimientos observados y tamaños coinciden exactamente con el control histórico; predicciones y medias reproducen a menos de 10⁻⁸ t/ha. Los controles históricos se abren después del cálculo, nunca alimentan las predicciones.
- FULL138 puntúa los errores de las 1,380 predicciones de cada referencia. GLOBAL: RMSE 0.854426 y MAE 0.753994; MUN: 0.511757 y 0.335394; MIX: 0.493845 y 0.341711. MIX mejora RMSE, pero no MAE. El R² estándar de GLOBAL es −0.015043, no cero.
- SEEN135 filtra las mismas predicciones, sin reentrenar ni cambiar los datos de entrenamiento. Solo conserva validaciones con municipio presente en entrenamiento; excluye los casos de tres municipios con una etiqueta. MUN: RMSE 0.493404 y MAE 0.321274; MIX: 0.487197 y 0.334215. Es un escenario adicional, no una estimación garantizada del error en las 59 ocultas. AGC_120, en Nanacamilpa, no tiene un caso OOF equivalente con la única etiqueta municipal presente en entrenamiento.

Las diez repeticiones no crean nuevas etiquetas ni observaciones independientes. No se promedian predicciones por parcela antes de puntuar. Las diferencias pareadas se describen sin pruebas de significancia que traten repeticiones como independientes. Esta reproducción conserva referencias, no selecciona un ganador ni constituye una séptima ronda.

Las fechas originales y la adaptación del 7 de octubre se distinguen. `docs/registros/20261007_notebook03.json` conserva pruebas, hashes, alcance y ejecución; los cuadernos 01 y 02, las recetas de extracción y el entorno permanecen intactos. La ejecución real del cuaderno 03 en Colab aún debe registrarse aparte de sus comprobaciones locales.

## Presentación de los bloques técnicos en Colab

Los cuadernos 02 y 03 incorporan título de formulario y `cellView="form"` solo en sus tres celdas técnicas. La marca original de Jupyter se conserva; ninguna celda didáctica se oculta. Retirar la primera línea de comentario recupera cada cuerpo anterior byte a byte; el código de todas las celdas conserva su AST. Los hashes de módulos, recetas, perfiles y datos no cambian. El hash del soporte derivado sigue identificando el cuerpo sin el título visual; el registro de presentación distingue ambas huellas.

Después del cambio se ejecutó cada cuaderno completo en un kernel nuevo, desde una carpeta con solo su notebook y el ZIP. Todas las salidas y las seis figuras reproducen las versiones anteriores, normalizando únicamente la fecha de ejecución. El registro `docs/registros/20261007_colab_vista_02_03.json` identifica los archivos actualizados y las copias recuperables. La revisión de metadatos y la ejecución local no se presentan como una comprobación visual en una sesión real de Colab.

## Segundo cuaderno: operaciones visibles para estudiar

El 02 incorpora un mapa de los bloques técnicos y diez ejemplos visibles: área y centroide; afín e intersección; resúmenes Planet; denominador de LAI; medias mensuales y trapecios; lluvia por área; NoData sintético; agregación climática; dispersión y cobertura de elevación; unión por ID. Cada ejemplo muestra entradas, operación y contraste con la función automática. AGC_051 ilustra lluvia en dos celdas; AGC_001 solo toca una en el mes elegido.

La edición tiene 63 celdas, 28 de código: tres técnicas plegadas y 25 visibles. Se ejecutó dos veces en kernels nuevos desde una carpeta con solo notebook y ZIP. Los cálculos originales, los tres PNG y el resumen reproducen la edición anterior; las nuevas tablas también coinciden entre ejecuciones. Solo se normaliza la fecha de ejecución al comparar salidas. Las recetas, módulos, dependencias, referencias y tabla de 197 × 539 permanecen iguales. El 03 no se modifica.

Las comprobaciones aritméticas no se presentan como validación independiente de todo el motor. Los ejemplos no agregan variables, no imputan las fuentes ni usan rendimiento para seleccionar reglas. El caso de NoData es inventado y está separado de los datos reales. Un primer ensayo detectó un problema de tipo al comparar números seleccionados de una tabla mixta; se corrigió la comparación con conversión explícita a números y se añadieron pruebas con un mes completo y uno ausente. No se alteró ningún valor de extracción.

`docs/registros/20261007_notebook02_didactico.json` identifica ejecuciones, pruebas y archivos recuperables. Estas comprobaciones locales no sustituyen una sesión real de Colab.

## Tercer cuaderno: referencias y errores abiertos paso a paso

La edición didáctica del 8 de octubre añade un mapa de módulos e insumos y seis ejemplos visibles: IDs externos e internos; vecinos, pesos y aportes de IDW hasta MIX; una fila OOF; RMSE, MAE y R² calculados directamente; un ejemplo inventado de promediar predicciones; pertenencia municipal para FULL138/SEEN135. GLOBAL y MUN se reconstruyen como suma/conteo antes del contraste. IDW usa todo el entrenamiento y el piso histórico de 1 m incluso en distancia cero. Ante municipio ausente, solo la parte MUN vuelve a GLOBAL: MIX conserva IDW.

El cuaderno tiene 53 celdas, 23 de código: tres técnicas plegadas y 20 visibles. Dos ejecuciones en kernels nuevos con solo notebook y ZIP reproducen el código, las salidas y las tres figuras anteriores; las nuevas tablas también coinciden entre ejecuciones. Solo se normaliza la fecha de ejecución al comparar salidas. Se conservan particiones, recetas, métricas, módulos y dependencias. El 02 y su paquete de distribución permanecen intactos. Las demostraciones no alimentan las OOF ni seleccionan ajustes; los 150 ajustes declarados corresponden exclusivamente a la evaluación, con controles didácticos aparte.

`docs/registros/20261008_notebook03_didactico.json` documenta pruebas, ejecuciones, hashes y copias recuperables. Las fechas de adaptación original del 7 de octubre y de las particiones del 20 de septiembre se conservan; la edición didáctica tiene su propia fecha. Estas comprobaciones locales no sustituyen una sesión real de Colab.

## Confirmación de Colab del equipo

El 8 de octubre Fortino confirmó: «Muy bien ya revise el 02 y corre en colab, podemos continuar». Se registra como evidencia reportada por el usuario, no como ejecución independiente de Codex ni comprobación del hash de su copia de Drive. El archivo local de referencia se identifica en `docs/registros/20261008_confirmacion_colab02_usuario.json`. El 01 ya contaba con confirmación del usuario.

## Pendiente antes de una entrega completa

- Incorporar las otras cuatro rondas con el formato común. Separar paridad de resultados guardados y paridad de entrenamiento en este entorno.
- Ejecutar el cuaderno 03, EXP_01 y EXP_02 en una sesión real de Colab. La autonomía local no se confunde con esa comprobación. Los cuadernos 01 y 02 sí tienen confirmación de Fortino en Colab.
- Verificar las 59 predicciones de entrega y la herramienta que las consulta.

El cuaderno 03 reajusta las tres referencias sencillas en los 50 entrenamientos exteriores: 150 ajustes, sin selección de hiperparámetros ni candidatos nuevos. No genera predicciones finales de las 59 parcelas. Codex no ha subido datos a la nube ni cambiado permisos; el ZIP de Drive lo compartió Fortino. `main.py` continúa como plantilla; no es una aplicación de predicción.

## EXP_01: lector verificado de la primera ronda

Se incorpora `notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb`, generado por `scripts/construir_exp_01.py`. El lector contiene CSV históricos identificados por tamaño y SHA-256; no necesita el ZIP del reto, Drive ni módulos de otra máquina. El ejecutor `scripts/ejecutar_exp_01.py` conserva cada ejecución en `resultados_locales/exp_01_bloques/`; la distribución local es `artefactos_locales/exp_01_bloques_equipo.zip`.

Alcance de esta edición: reconstruir la selección de 14 variables declaradas, incluidas sus tres medias históricas derivadas, comprobar claves OOF y recalcular métricas agrupadas y contrastes; reproducir la elección de alpha desde scores guardados. **No reproduce los 5,000 ajustes internos ni 250 reajustes originales**, y no recalcula scores internos porque no están guardados sus errores individuales. Las predicciones son resultados usados para evaluar, nunca entradas de entrenamiento. Se conserva FULL138, las reglas originales y el cierre sin adopción; no se generan las 59 predicciones.

El trabajo original es del 21 de septiembre; la lectura se adapta el 8 de octubre. Python 3.10.12/scikit-learn 1.7.2 corresponden a la ejecución histórica; Python 3.13.13 y el perfil actual, al lector. La igualdad de métricas desde OOF conservados no demuestra igualdad de ajustes entre esos entornos.

**Verificación local:** 269 pruebas pasan, sin fallos ni omisiones, y Ruff pasa. El notebook tiene 30 celdas, 16 de código: dos técnicas plegadas y 14 abiertas. Dos kernels nuevos con únicamente el notebook, sin ZIP, tablas externas ni módulos locales, producen 27 salidas y un PNG idénticos al normalizar solo la fecha de ejecución. Las 11,040 OOF, las 250 decisiones de alpha y las métricas de ocho procedimientos se concilian; las numéricas coinciden con el control histórico a 10⁻¹². Se conserva el umbral histórico de R² y se normalizan solo alias de lectura de referencias, sin editar sus CSV.

Los diez insumos conservan tamaño y SHA-256; los notebooks 01–03, entorno uv, paquetes anteriores y fuentes históricas permanecen intactos. Los controles de tamaño y descompresión limitan la lectura incrustada. Se corrigió un control de nombres entre «Media global»/GLOBAL y sus otros dos alias; no cambió ninguna predicción ni métrica. La incorporación se registra en `docs/registros/20261008_exp01_bloques.json`, con copias recuperables de los archivos de índice modificados. La carpeta temporal de preparación anterior se perdió antes de publicar; esta edición se recuperó y verificó de nuevo en almacenamiento persistente.

No se ejecutó en una sesión real de Colab ni se reprodujo el entrenamiento histórico. El catálogo identifica un lector verificado sin reentrenamiento, no una ronda adicional ni una certificación predictiva independiente.

## EXP_02: ponderación temporal — verificación local

Se incorpora `notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb`, construido por `scripts/construir_exp_02.py` con el contrato `config/exp_02_ponderacion_temporal.json`. El ejecutor `scripts/ejecutar_exp_02.py` guarda salidas nuevas en `resultados_locales/exp_02_ponderacion_temporal/`; la distribución local es `artefactos_locales/exp_02_ponderacion_temporal_equipo.zip`. No requiere ZIP externo, Drive, otro notebook ni módulos locales para leer sus insumos.

La lectura reconstruye tres variables desde un recorte de capturas originales: NDVI Planet, NDVI Sentinel-2 y NDWI Sentinel-2. Primero calcula medias mensuales y conteos por índice; luego pondera los siete meses de abril–octubre de 2025 por sus días sobre 214. Comprueba meses completos, claves, fechas, sensores, ausencias y coincidencia con los controles mensuales y atributos T1. No filtra nubes ni imputa meses; conserva las otras tres entradas de E2.

El recorte es un artefacto derivado el **8 de octubre**, no un nuevo archivo atribuido al registro previo T1. Su tamaño, SHA-256, regla de extracción y huellas de fuentes originales se comprueban en el contrato. Los originales se contrastaron byte a byte con los miembros del ZIP: 26,255 filas Planet y 9,986 Sentinel-2 en los recortes, conservando ausencias. El trabajo original sigue fechado el **29 de septiembre**, con Python 3.12.14/scikit-learn 1.9.1. El lector en Python 3.13.13 no repite los **2,100 ajustes históricos**: 1,050 de control E2 y 1,050 de T1. Verifica decisiones de alpha desde scores guardados, no su cálculo interno ni el entrenamiento que los produjo.

Se conserva FULL138, las mismas claves OOF y etiquetas, y el cierre sin adopción: T1 RMSE 0.5225 frente a E2 0.5192 y MIX 0.4938 t/ha. La sensibilidad sin dos focos estaba prevista en T1 y modifica únicamente la evaluación. No se generan las 59 predicciones, no se cambia el criterio original ni se adopta retrospectivamente SEEN135.

**Verificación final:** 327 pruebas pasan, incluidas 58 de EXP_02; Ruff pasa sobre `scripts tests`. Dos kernels nuevos, cada uno iniciado con solo el notebook, producen 33 salidas y dos PNG iguales, normalizando exclusivamente la fecha de ejecución. Hay 33 celdas: 17 de código, dos técnicas plegadas y 15 visibles. Se reconstruyen 4,137 medias mensuales, se concilian 8,280 OOF de seis procedimientos y se verifican 100 decisiones de alpha; T1 cambia alpha frente a E2 en 13 exteriores. Veinte insumos identificados; cero ajustes en el cuaderno y cero predicciones finales.

El registro `docs/registros/20261008_exp02_ponderacion_temporal.json` conserva hashes, controles, copias recuperables del índice y las incidencias de preparación. Los notebooks 01–03 y EXP_01, entorno uv, paquetes anteriores y fuentes históricas permanecen intactos. La generación limpia salidas antiguas al reutilizar celdas; una guarda de prueba se corrigió para distinguir el helper de descarga inactivo de una descarga ejecutada. Ninguna corrección cambia variables, predicciones o resultados históricos. No se ha probado EXP_02 en una sesión real de Colab ni reproducido su entrenamiento original. Es otra lectura de una ronda existente, no un experimento nuevo.
