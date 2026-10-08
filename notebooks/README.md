# Notebooks — recorrido de evidencia

1. [Auditoría y unidad parcela](01_auditoria_y_unidad_parcela.ipynb): inventario, objetivo, fechas y geografía.
2. [De las fuentes a las variables](02_fuentes_a_variables.ipynb): una parcela, recetas espaciales y temporales, tabla de 197 parcelas y diccionario.
3. [Referencias y validación](03_referencias_y_validacion.ipynb): particiones, GLOBAL/MUN/MIX, métricas fuera de muestra y límites de comparación.
4. [EXP_01: bloques de variables sobre municipio](experimentos/exp_01_bloques/exp_01_bloques.ipynb): hipótesis A/B/C, Ridge, selector interno y resultados guardados de la primera ronda.
5. [EXP_02: ponderación temporal](experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb): capturas, medias mensuales, pesos por días y contraste T1 frente a E2.

Cada cuaderno incorpora sus lectores y controles; puede ejecutarse en una sesión nueva de Colab sin ejecutar el anterior. El segundo reconstruye la tabla integrada y contrasta su resultado, sin entrenar ni seleccionar predictores.

El tercero recalcula **150 ajustes de referencias sencillas**, no una búsqueda de modelos: medias aprendidas solo del entrenamiento y una mezcla espacial fija. Sus cuatro CSV de particiones y comprobación están incrustados con hashes. La validación interna se comprueba y explica; no se eligen hiperparámetros ni se predicen las 59 parcelas oficiales.

EXP_01 incorpora sus tablas históricas y controles: **no necesita el ZIP original ni descargar datos de Drive**. Ejecutarlo no ajusta modelos. Recalcula métricas desde predicciones guardadas y reproduce la elección de alpha usando scores internos guardados, sin recalcular esos scores ni el entrenamiento que los produjo. `exp_01` identifica la ronda de lectura; `E0`–`E4` identifican sus cinco procedimientos, no otros notebooks.

EXP_02 también es autónomo y hace **cero ajustes**. Añade capturas reales recortadas de los originales para recalcular tres variables temporales, y después puntúa las OOF guardadas de T1 y sus comparadores. El recorte se prepara el 8 de octubre; las predicciones y el cierre T1 conservan su fecha del 29 de septiembre. Recalcular variables y métricas no equivale a producir nuevas predicciones.

El recorrido de estudio es **auditoría → fuentes y variables → referencias y validación → seis rondas**. El contexto y la metodología presentan el objetivo antes de empezar con las comprobaciones.

## 01. Entender los datos

[Auditoría y unidad de observación](01_auditoria_y_unidad_parcela.ipynb) responde qué contienen los insumos y cuántos rendimientos conocemos realmente. Incluye inventario, controles de etiquetas y fechas, cobertura por sensor, distribución territorial y límites de interpretación.

El cuaderno contiene las salidas de una ejecución comprobada y su código completo. **Leer no requiere ejecutar; recalcular no entrena modelos ni modifica el ZIP original.** Local y Colab utilizan Python 3.13. La preparación de bibliotecas se anuncia y solo opera en Colab; si requiere reinicio, lo pide sin reiniciar automáticamente.

En local utiliza `data/raw/DataSet.zip`. En Colab puede descargar la copia autorizada de Drive si no existe una copia local. Ambos caminos exigen el mismo tamaño y SHA-256 antes de leer el archivo. Una caché válida evita descargarlo de nuevo; una incorrecta detiene la ejecución. La celda de acceso permite señalar otra ubicación del mismo ZIP.

Cada cuaderno explica su etapa CRISP-DM y, cuando corresponde, por qué volvemos a una etapa anterior. Cada bloque incluye pregunta y motivo, operación, salida e interpretación. El cierre reúne respuesta, decisión, límite y siguiente pregunta.

Las comprobaciones de aportes de Andrea y Jared incluyen explicación y contraste, sin exigir leer sus documentos. Los modos **leer, recalcular y reentrenar** se identifican antes de ejecutar. Los cuadernos 01 y 02 no ajustan modelos; el 03 anuncia sus referencias y coste antes de reconstruirlas. Ninguno abre por sorpresa una nueva ronda de búsqueda.

## EXP_01. Comprobar qué aportan los bloques

[Bloques de variables sobre municipio](experimentos/exp_01_bloques/exp_01_bloques.ipynb) explica una pregunta concreta: ¿qué añadieron clima/topografía, satélite del ciclo e historia a un procedimiento municipal? Recorre las 14 variables declaradas, la derivación de historia, el motivo para usar Ridge y la selección interna de alpha. Después contrasta OOF, métricas, repeticiones, regiones y concentración de los cambios por parcela.

La ronda original es del **21 de septiembre de 2026**; la adaptación de lectura, del **8 de octubre**. Conserva **FULL138: 138 parcelas y 1,380 predicciones OOF por procedimiento**. No aplica retrospectivamente SEEN135 ni el criterio conservador de rondas posteriores. E0 es Ridge con indicadores municipales penalizados, no la media municipal MUN; las dos referencias deben distinguirse.

El presupuesto original fue **5,000 ajustes internos y 250 reajustes externos**. Esta lectura hace **cero ajustes**: los OOF y scores son resultados verificados como insumos, no datos para entrenar otro modelo. Reconstruir la elección desde scores no demuestra cómo se obtuvieron; no hay errores interiores guardados para recalcularlos. El entrenamiento original utilizó Python 3.10.12/scikit-learn 1.7.2; la lectura trabaja en Python 3.13, sin afirmar una réplica de ese entrenamiento.

La historia E3 mejoró poco el RMSE frente a E0, pero empeoró MAE y no superó MIX. Las celdas permiten comprobar también la concentración del beneficio. El cierre no adopta bloques ni genera predicciones para las 59 parcelas ocultas.

Para compartirlo basta el notebook; el paquete local `artefactos_locales/exp_01_bloques_equipo.zip` reúne su distribución. Puede recalcularse en una sesión nueva sin Git, rutas personales ni ejecutar 01–03. El ejecutor `scripts/ejecutar_exp_01.py` guarda una nueva ejecución en `resultados_locales/exp_01_bloques/`.

## EXP_02. Cambiar cómo representamos el tiempo

[Ponderación temporal](experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb) sigue **regla → capturas de una parcela → media de un mes → siete medias y pesos → controles para las 197 → errores comparables → límite**. NDVI Planet, NDVI Sentinel-2 y NDWI Sentinel-2 pasan de media por captura a media mensual ponderada por días. Los pesos se aplican a las medias mensuales, no a cada fotografía. Se mantienen los sensores separados, abril–octubre, las otras tres variables de E2 y el procedimiento Ridge.

La receta exige los siete meses, sin imputar ni renormalizar meses ausentes. No filtra nubes. El notebook incorpora un recorte de capturas derivado de los originales el **8 de octubre**, con su propio hash y la procedencia del archivo fuente. Reconstruye las **4,137 medias mensuales** y tres variables para 197 parcelas; conserva la identidad y el cierre del experimento **T1 del 29 de septiembre**, no crea una séptima ronda.

La evaluación mantiene **FULL138 y 1,380 OOF por procedimiento**, las mismas particiones y la selección interna de alpha. El lector verifica esa selección desde scores guardados; no recalcula esos scores ni los ajustes. El presupuesto histórico fue **1,050 ajustes para T1 y 1,050 para el control de E2**. T1 corrió en Python 3.12.14/scikit-learn 1.9.1; esta lectura en Python 3.13 no reproduce aquel control de entrenamiento.

T1 no se adopta: RMSE **0.5225 t/ha**, frente a 0.5192 de E2 y 0.4938 de MIX; MAE prácticamente igual a E2. Las diferencias por repetición, zona y parcela explican por qué una mejora local no basta. La sensibilidad sin AGC_127/171 estaba prevista para T1 y solo cambia la puntuación, no los entrenamientos. No se infiere causalidad, extrapolación ni inutilidad general de las representaciones temporales.

Para compartirlo basta el `.ipynb`. No requiere subir un ZIP, descargar de Drive, conocer Git ni ejecutar otro notebook. `artefactos_locales/exp_02_ponderacion_temporal_equipo.zip` reúne su distribución; `scripts/ejecutar_exp_02.py` guarda una ejecución nueva en `resultados_locales/exp_02_ponderacion_temporal/`, sin modificar la evidencia histórica ni generar las 59 predicciones finales.

El [formato común](../docs/04_notebooks_y_colab.md) define estas convenciones. El [glosario](../docs/06_glosario.md) permite consultar términos sin interrumpir el recorrido.
