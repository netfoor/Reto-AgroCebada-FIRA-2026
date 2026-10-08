# Notebooks — recorrido de evidencia

1. [Auditoría y unidad parcela](01_auditoria_y_unidad_parcela.ipynb): inventario, objetivo, fechas y geografía.
2. [De las fuentes a las variables](02_fuentes_a_variables.ipynb): una parcela, recetas espaciales y temporales, tabla de 197 parcelas y diccionario.
3. [Referencias y validación](03_referencias_y_validacion.ipynb): particiones, GLOBAL/MUN/MIX, métricas fuera de muestra y límites de comparación.
4. [EXP_01: bloques de variables sobre municipio](experimentos/exp_01_bloques/exp_01_bloques.ipynb): hipótesis A/B/C, Ridge, selector interno y resultados guardados de la primera ronda.
5. [EXP_02: ponderación temporal](experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb): capturas, medias mensuales, pesos por días y contraste T1 frente a E2.
6. [EXP_03: variables temporales y familias](experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb): cuatro descriptores de curva y comparación controlada Ridge/HGB.

Cada cuaderno incorpora sus lectores y controles; puede ejecutarse en una sesión nueva de Colab sin ejecutar el anterior. El segundo reconstruye la tabla integrada y contrasta su resultado, sin entrenar ni seleccionar predictores.

El tercero recalcula **150 ajustes de referencias sencillas**, no una búsqueda de modelos: medias aprendidas solo del entrenamiento y una mezcla espacial fija. Sus cuatro CSV de particiones y comprobación están incrustados con hashes. La validación interna se comprueba y explica; no se eligen hiperparámetros ni se predicen las 59 parcelas oficiales.

EXP_01 incorpora sus tablas históricas y controles: **no necesita el ZIP original ni descargar datos de Drive**. Ejecutarlo no ajusta modelos. Recalcula métricas desde predicciones guardadas y reproduce la elección de alpha usando scores internos guardados, sin recalcular esos scores ni el entrenamiento que los produjo. `exp_01` identifica la ronda de lectura; `E0`–`E4` identifican sus cinco procedimientos, no otros notebooks.

EXP_02 también es autónomo y hace **cero ajustes**. Añade capturas reales recortadas de los originales para recalcular tres variables temporales, y después puntúa las OOF guardadas de T1 y sus comparadores. El recorte se prepara el 8 de octubre; las predicciones y el cierre T1 conservan su fecha del 29 de septiembre. Recalcular variables y métricas no equivale a producir nuevas predicciones.

EXP_03 conserva las seis entradas E2, añade cuatro descriptores calculados visiblemente desde las capturas y cruza las dos representaciones con Ridge/HGB. También hace **cero ajustes** y es autónomo: reconstruye variables y recalcula evaluación y selecciones desde resultados guardados, sin entrenar ni recalcular scores internos. No depende de haber ejecutado EXP_02.

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

## EXP_03. Distinguir representación y procedimiento

[Variables temporales y familias](experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb) plantea dos preguntas: ¿cuatro descriptores de curva añaden información a los seis resúmenes E2?, ¿cambia la respuesta con un procedimiento no lineal? No sustituye medias como T1: mantiene la base y añade el bloque. Las reglas, capturas de AGC_001, medias mensuales y cuatro cálculos están visibles antes de verificar las 197 filas.

Las nuevas variables son dos cambios de NDVI Planet entre bimestres, su amplitud mensual y un cambio de NDWI Sentinel-2. Cada bimestre pondera **medias mensuales por días**, no fotografías por días. Las dos series requieren siete meses: **2,758 medias** en total. No hay imputación mensual, filtro de nubes ni identificación de etapas fenológicas. Los seis resúmenes originales se comprueban sin alterar sus definiciones.

La comparación 2×2 distingue **R_B/R_T** (Ridge con base/bloque ampliado) y **H_B/H_T** (HGB con base/bloque ampliado). Las rejillas históricas son pequeñas y tienen presupuestos diferentes; no representan una comparación exhaustiva de familias. Se conserva el ajuste de preprocesamiento dentro de cada entrenamiento y los CSV de particiones originales. La lectura examina sus resultados guardados, no repite el ajuste.

V1 se registró el **29 de septiembre de 2026 a las 18:22 UTC** y se ejecutó el **30 a las 02:06 UTC**, todavía 29 de septiembre en México. La adaptación didáctica es del **8 de octubre**. Se mantiene FULL138: **1,380 OOF por procedimiento**, siete procedimientos, **9,660 predicciones**. Se comprueban **200 selecciones** desde **900 scores interiores guardados**; no se recalculan esos scores. El presupuesto original fue **2,000 ajustes Ridge interiores + 1,600 HGB interiores + 200 reajustes exteriores**. El lector hace cero.

Ninguna variante cumplió la regla previa de avanzar frente a MIX por RMSE y MUN por MAE. R_T empeoró frente a R_B; H_T mejoró ligeramente RMSE frente a H_B, pero empeoró MAE. Las diferencias por repetición, Chignahuapan/resto y la sensibilidad prevista sin AGC_127/171 evitan rescatar una variante por su única métrica favorable. Se conserva el cierre sin adopción, no una conclusión universal sobre índices o árboles.

Para compartirlo basta el `.ipynb`; no requiere ZIP, Drive, módulos locales ni otro notebook. `artefactos_locales/exp_03_variables_y_familias_equipo.zip` reúne la distribución. `scripts/ejecutar_exp_03.py` guarda una ejecución nueva en `resultados_locales/exp_03_variables_y_familias/`, sin modificar fuentes ni producir las 59 predicciones finales. La versión histórica Python 3.12.14/scikit-learn 1.9.1 se distingue del entorno lector Python 3.13: recalcular métricas no demuestra paridad del entrenamiento.

El [formato común](../docs/04_notebooks_y_colab.md) define estas convenciones. El [glosario](../docs/06_glosario.md) permite consultar términos sin interrumpir el recorrido.
