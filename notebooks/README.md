# Notebooks — recorrido de evidencia

1. [Auditoría y unidad parcela](01_auditoria_y_unidad_parcela.ipynb): inventario, objetivo, fechas y geografía.
2. [De las fuentes a las variables](02_fuentes_a_variables.ipynb): una parcela, recetas espaciales y temporales, tabla de 197 parcelas y diccionario.
3. [Referencias y validación](03_referencias_y_validacion.ipynb): particiones, GLOBAL/MUN/MIX, métricas fuera de muestra y límites de comparación.
4. [EXP_01: bloques de variables sobre municipio](experimentos/exp_01_bloques/exp_01_bloques.ipynb): hipótesis A/B/C, Ridge, selector interno y resultados guardados de la primera ronda.
5. [EXP_02: ponderación temporal](experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb): capturas, medias mensuales, pesos por días y contraste T1 frente a E2.
6. [EXP_03: variables temporales y familias](experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb): cuatro descriptores de curva y comparación controlada Ridge/HGB.
7. [EXP_04: lluvia de octubre](experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb): áreas y píxeles, anomalías, cinco candidatos y reservas sobre agrupación y validación.
8. [EXP_05: histórico y lluvia actual](experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb): separar H, P, H+P y porcentaje bajo el mismo procedimiento municipal.
9. [EXP_06: pico soportado](experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb): NDVI diario, suavizado y guardas para sustituir una fecha de E2.
10. [EXP_07: heterogeneidad espacial](experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb): soporte pareado de NDVI medio/dispersión y contraste C0/C1 registrado.
11. [EXP_08: contraste vecinal](experimentos/exp_08_contraste_vecinal/exp_08_contraste_vecinal.ipynb): dónde está el error, barrido con nulo por permutación, estructura espacial y corrección de MIX con el contraste vecinal (exploratorio; ver fe de erratas en su README).
12. [EXP_09: fuentes externas](experimentos/exp_09_fuentes_externas/exp_09_fuentes_externas.ipynb): Sentinel-2 propio (borde rojo), Sentinel-1, AlphaEarth e historia como contrastes vecinales, con registro previo y nulo de familia.
13. [EXP_10: verificación del contraste vecinal](experimentos/exp_10_verificacion_contraste_vecinal/exp_10_verificacion_contraste_vecinal.ipynb): corte temporal corregido, invariancia, dos juegos de particiones, nulo espacial y decisión. Lector sin ajustes.
14. [EXP_11: combinación fija](experimentos/exp_11_combinacion_modelos/exp_11_combinacion_modelos.ipynb): ½·Jared + ½·(MIX+K1) frente a sus componentes, con el control ½·MUN + ½·K. Cero entrenamientos.
15. [04: selección del modelo final y 59 predicciones](04_seleccion_modelo_final.ipynb): reúne todas las evaluaciones, explica por qué el error queda en 0.4x, resume las pruebas con caja cerrada, aplica la decisión registrada (E_JK, referencia MIX) y genera las 59 predicciones con intervalos. Antes de predecir, reproduce las 2,760 OOF de EXP_11 y la caja cerrada. Se construye con `scripts/construir_notebook_04.py` y se ejecuta con `scripts/ejecutar_notebook_04.py`. Probado en dos kernels locales limpios, no en Colab real.

Cada cuaderno incorpora sus lectores y controles y está diseñado para ejecutarse en una sesión nueva de Colab sin ejecutar el anterior. La autonomía comprobada localmente no sustituye una ejecución real en Colab. El segundo reconstruye la tabla integrada y contrasta su resultado, sin entrenar ni seleccionar predictores.

El tercero recalcula **150 ajustes de referencias sencillas**, no una búsqueda de modelos: medias aprendidas solo del entrenamiento y una mezcla espacial fija. Sus cuatro CSV de particiones y comprobación están incrustados con hashes. La validación interna se comprueba y explica; no se eligen hiperparámetros ni se predicen las 59 parcelas oficiales.

EXP_01 incorpora sus tablas históricas y controles: **no necesita el ZIP original ni descargar datos de Drive**. Ejecutarlo no ajusta modelos. Recalcula métricas desde predicciones guardadas y reproduce la elección de alpha usando scores internos guardados, sin recalcular esos scores ni el entrenamiento que los produjo. `exp_01` identifica la ronda de lectura; `E0`–`E4` identifican sus cinco procedimientos, no otros notebooks.

EXP_02 también es autónomo y hace **cero ajustes**. Añade capturas reales recortadas de los originales para recalcular tres variables temporales, y después puntúa las OOF guardadas de T1 y sus comparadores. El recorte se prepara el 8 de octubre; las predicciones y el cierre T1 conservan su fecha del 29 de septiembre. Recalcular variables y métricas no equivale a producir nuevas predicciones.

EXP_03 conserva las seis entradas E2, añade cuatro descriptores calculados visiblemente desde las capturas y cruza las dos representaciones con Ridge/HGB. También hace **cero ajustes** y es autónomo: reconstruye variables y recalcula evaluación y selecciones desde resultados guardados, sin entrenar ni recalcular scores internos. No depende de haber ejecutado EXP_02.

EXP_04 muestra la ponderación por área de píxeles de octubre, calcula las lluvias y anomalías desde soportes guardados y evalúa los cinco candidatos de V2. También hace **cero ajustes**: recalcular sumas ponderadas no equivale a repetir las intersecciones geoespaciales; puntuar OOF guardadas no equivale a producir nuevas predicciones. FULL138 y el diagnóstico posterior SEEN135 permanecen separados.

EXP_05 recalcula H, P y A_pct desde cuatro lluvias guardadas por parcela, no desde GeoTIFF. Mantiene el procedimiento municipal regularizado y distingue histórico solo, lluvia actual, representación aditiva y razón porcentual. **Cero ajustes**: verifica selección y métricas desde resultados guardados. SEEN135 es principal desde el diseño de esta ronda, no una máscara elegida por sus resultados ni un cambio del veredicto de V2.

EXP_06 reconstruye la fecha de pico soportado desde capturas Planet y sustituye solo la fecha cruda de E2. Suaviza por días de calendario, no por número de filas; las guardas dejan ausencias sin eliminar parcelas. La bandera no entra como predictor. **Cero ajustes**: el lector evalúa OOF guardadas y verifica selecciones desde scores guardados. V4 conserva SEEN135 principal y se cerró sin adopción.

El recorrido de estudio es **auditoría → fuentes y variables → referencias y validación → siete rondas**. Las seis primeras son trabajos históricos reorganizados; EXP_07 es la nueva comparación ejecutada el 8 de octubre. El contexto y la metodología presentan el objetivo antes de empezar con las comprobaciones.

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

## EXP_04. Lluvia, representación y territorio

[Lluvia de octubre](experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb) sigue **píxeles y áreas → suma ponderada → referencia histórica → anomalías → procedimientos → evaluación y reservas**. La hipótesis proviene de la exploración de Jared, no de un descubrimiento confirmatorio independiente. Primero explica cómo una parcela puede recibir aportaciones de varios píxeles; después generaliza a las 197.

El lector usa 230 áreas de intersección guardadas y 116 valores de píxel de cuatro rásteres, derivados de los originales el **8 de octubre**. Recalcula **788 lluvias**, la media histórica H de octubre de 2022–2024, la desviación absoluta y la porcentual. No vuelve a ejecutar GEOS, no reconstruye las intersecciones y no presenta esos recortes actuales como insumos del registro previo de V2. Los controles históricos se contrastan después de calcular las variables.

La comparación conserva cinco candidatos: **J5_PCT/J9_PCT** usan OLS y cinco/nueve grupos; **R9_PCT/R9_MM/R9_RAW** usan el procedimiento municipal regularizado con anomalía porcentual, absoluta o lluvia actual. Cambiar J9 por J5 modifica conjuntamente medias, residuos, escala y respaldos: no aísla una sola causa. R9_PCT mejora RMSE frente a R9_MM, pero empeora MAE; no prueba superioridad general de la representación ni aporte incremental de H por sí sola.

Se evalúan **13,800 OOF de diez procedimientos**, incluidas GLOBAL/MUN/MIX, G5 y R_B. Se verifican **150 selecciones Ridge con 900 scores guardados**, más **50 selecciones del control R_B con 250 scores**. No se recalculan esos scores ni las predicciones, y no se entrenan modelos. La ejecución histórica V2 utilizó Python **3.12.3**, no el intérprete de V1; la lectura utiliza Python 3.13.

J5_PCT cumple la regla original en FULL138: RMSE 0.4797 frente a MIX 0.4938 y MAE 0.3291 frente a MUN 0.3354; ambas condiciones se cumplen en 10/10 repeticiones. El diagnóstico posterior de municipio visto conserva 135 parcelas y 1,350 OOF por procedimiento: mejora RMSE frente a MIX en 8/10 repeticiones, pero no cumple la condición MAE en ninguna. **No reemplaza retrospectivamente el veredicto registrado ni equivale a las 59 ocultas.** AGC_120, en Nanacamilpa, no tiene una validación OOF equivalente con su única etiqueta municipal presente.

Las etiquetas ocupan 23 celdas por centroide, pero reciben aportaciones de 27 píxeles; el conjunto completo recibe 29. Son conteos de soporte, no un tamaño muestral efectivo estimado. Las diez repeticiones tampoco crean parcelas independientes. La mejora se concentra en pocos casos; el cierre conserva a J5_PCT como candidato exploratorio con reservas, sin causalidad ni adopción final.

V2 se registró y ejecutó el **1 de octubre de 2026**; esta adaptación de lectura es del **8 de octubre**. Para compartirlo basta el notebook, sin ZIP externo, Drive, módulos locales ni ejecutar otro cuaderno. `artefactos_locales/exp_04_lluvia_octubre_equipo.zip` reúne la distribución y `scripts/ejecutar_exp_04.py` conserva una ejecución nueva en `resultados_locales/exp_04_lluvia_octubre/`. No genera las 59 predicciones de entrega.

## EXP_05. Aislar una pregunta predictiva sobre octubre

[Histórico y lluvia actual de octubre](experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb) sigue **cuatro lluvias por parcela → fórmulas de H/P/porcentaje → cuatro recetas comparables → selección guardada → evaluación principal y límites**. El porcentaje combina P e H en una razón no lineal: no es un simple cambio de unidades de H+P. Por eso su correlación con el histórico no resuelve cuál de estas representaciones predice mejor.

Se reconstruyen variables de **197 parcelas** desde las lluvias de octubre de 2022–2025 ya verificadas. No se lee GeoTIFF, recalcula una intersección ni cambia la receta espacial. Las operaciones y el contraste con el control se muestran separados. H resume solo tres años; no se lo denomina normal climatológica.

Los cuatro candidatos **R9_H, R9_HP, R9_P y R9_PCT** mantienen municipio, Ridge, ventana, particiones y rejilla. R9_PCT/R9_P conservan la identidad de R9_PCT/R9_RAW de V2. MUN/MIX son referencias fijas; J5_PCT aporta contexto, no reemplaza a las referencias según convenga. Los parámetros guardados ayudan a explicar regularización y colinealidad, no se interpretan como efectos agronómicos causales.

Se evalúan **9,660 OOF guardadas de siete procedimientos**. **SEEN135 es el escenario principal**, 1,350 predicciones por procedimiento; **FULL138 es secundario**, 1,380. La máscara deriva de IDs, municipios y particiones sin mirar errores; no retira etiquetas del entrenamiento. Se fijó para V3 después de conocer V2, sin recalificar el pasado. No equivale a la entrega: AGC_120 en Nanacamilpa sigue sin un caso OOF equivalente con su única etiqueta municipal presente.

La regla exige RMSE menor que MIX y MAE no mayor que MUN, globalmente y en al menos 8/10 repeticiones por condición. Ninguna receta cumple. H+P reduce poco el RMSE frente a H y empeora MAE; H y H+P quedan detrás del porcentaje en RMSE. Este tampoco avanza: mejora RMSE frente a MIX solo en 6/10 repeticiones y su MAE agrupado es peor que MUN. El resultado limita estas recetas, no demuestra inutilidad general del histórico ni del clima.

V3 se diseñó y ejecutó el **1 de octubre en México**, con fecha UTC del **2 de octubre**; adaptación de lectura: **8 de octubre**. Se verifican **200 selecciones desde 1,200 scores guardados**, sin recalcular los scores ni repetir ajustes. El presupuesto histórico fue 4,800 evaluaciones internas, 800 baseline, 4,000 ajustes Ridge y 200 reajustes exteriores. Las 34 pruebas históricas y nueve autopruebas del cuaderno original se distinguen de las comprobaciones actuales del lector. Un intento inicial se detuvo por leer alpha de una columna vacía; r1 corrigió solo ese control antes de ajustar H/HP.

Para compartirlo basta el `.ipynb`; no requiere ZIP, Drive, módulos locales ni ejecutar otro notebook. `artefactos_locales/exp_05_historico_octubre_equipo.zip` reúne la distribución; `scripts/ejecutar_exp_05.py` conserva una ejecución nueva en `resultados_locales/exp_05_historico_octubre/`. Python 3.12.14 histórico y Python 3.13 lector se identifican por separado. No se producen las 59 predicciones finales ni se declara una ejecución en Colab real.

R² municipal requiere variación del objetivo: el cuaderno muestra como NaN 14 entradas espurias de Tepeapulco por redondeo, sin reescribir CSV ni modificar RMSE, MAE o decisiones.

## EXP_06. Verificar una fecha antes de usarla

[Fecha de pico NDVI con soporte](experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb) sigue **capturas → promedio diario → mediana por ventana de calendario → guardas → sustitución de una variable → errores comparables → decisión**. Pregunta si la fecha de una curva suavizada y suficientemente observada mejora E2 frente al máximo crudo. No cambia simultáneamente de familia ni añade un bloque de nuevas variables.

La ventana conserva abril–octubre de 2025. La mediana utiliza observaciones dentro de **±7 días**, con al menos tres días finitos; no inventa observaciones por interpolación ni aplica un filtro nuevo de nubes. Las guardas controlan cantidad de días, huecos, ventana observada, amplitud, meseta ambigua, censura y soporte a ambos lados. Son decisiones operativas de esta receta, no una certificación agronómica de la fecha.

Se reconstruyen **158 fechas soportadas y 39 ausencias** entre las 197 parcelas. La sustitución mantiene las otras cinco entradas numéricas de E2, municipio y el orden de columnas. La bandera de soporte no es un predictor. La mediana de imputación y la escala del procedimiento original se aprendieron dentro de cada entrenamiento: un control didáctico no se presenta como un reajuste del modelo.

El lector incorpora **24 insumos**, incluido un recorte de **26,255 capturas** derivado el 8 de octubre con procedencia y hash propios. Primero calcula las variables, luego las contrasta con descriptores y curvas históricos. No presenta ese recorte como insumo registrado antes de V4. La factibilidad se realizó el **2 de octubre**; registro y corrida V4, el **6**; adaptación de lectura, el **8**.

Se puntúan **6,900 OOF guardadas** de E2, V4, GLOBAL, MUN y MIX. Se verifican **100 selecciones desde 500 scores internos guardados** y el control E2 anterior, sin recalcular los scores. SEEN135 conserva 1,350 OOF por procedimiento y FULL138, 1,380. La máscara principal usa metadatos y particiones, no errores; no retira etiquetas del entrenamiento ni equivale a las 59 ocultas.

En SEEN135, V4 reduce RMSE frente a E2 de **0.5065 a 0.5015 t/ha**, pero no mejora MAE ni supera MIX, **0.4872**. La regla conservadora no se cumple. La mejora frente a E2 se concentra: al retirar únicamente de la evaluación las cinco parcelas más favorecidas, se invierte ese orden. Esto no autoriza excluirlas del entrenamiento. Chignahuapan sigue detrás de MIX y una fecha soportada no resuelve por sí sola la predicción dentro de región.

V4 histórico utilizó Python **3.12.14** y 2,100 ajustes por corrida; se hicieron dos corridas para verificar determinismo, 4,200 ajustes físicos y un solo candidato. El lector Python 3.13 hace **cero ajustes**, no produce predicciones nuevas y no acredita paridad del entrenamiento. Recalcula solo la fecha de pico utilizada: no incorpora anchura de curva ni otro descriptor fenológico.

Para compartirlo basta el `.ipynb`; no requiere ZIP, Drive, módulos locales ni otro cuaderno. `scripts/ejecutar_exp_06.py` guarda una ejecución nueva en `resultados_locales/exp_06_pico_soportado/`; `artefactos_locales/exp_06_pico_soportado_equipo.zip` reúne la distribución local. **Lector verificado localmente sin reentrenar; Colab real no probado.** Con esta sexta lectura se cubren las seis rondas históricas, sin crear una ronda adicional.

## EXP_07. Una dimensión distinta: dispersión espacial

[Heterogeneidad de NDVI](experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb) distingue dispersión entre píxeles de variación temporal de una curva. Primero calcula NDVI medio y std media sobre las mismas capturas; muestra una parcela y generaliza a 197. La factibilidad sin rendimiento comprobó soporte común, siete meses y variación intramunicipal en los entrenamientos.

C0 usa municipio más corrección Ridge con nivel medio; C1 añade únicamente dispersión. La corrida se registró antes de ajustar; hubo 2,400 evaluaciones interiores por ejecución, 2,000 ajustes Ridge internos y 11 exteriores efectivos. Una réplica produjo las 12 salidas científicas idénticas. El lector puntúa las 5,520 OOF y verifica 100 selecciones con scores guardados: **no repite esos entrenamientos**.

En SEEN135, C1 no mejora RMSE: 0.494105 frente a C0 0.494064; MIX sigue en 0.487197. MAE cambia mínimamente y el apoyo incremental es solo 4/10 repeticiones. Se cerró **sin adopción**, sin nuevas variantes ni predicciones finales. La verificación local no equivale a Colab real.

El [formato común](../docs/04_notebooks_y_colab.md) define estas convenciones. El [glosario](../docs/06_glosario.md) permite consultar términos sin interrumpir el recorrido.
