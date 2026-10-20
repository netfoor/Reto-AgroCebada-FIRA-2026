# 02_validacion_y_lineas_base: cómo medimos el error y contra qué comparamos

**En FINAL el código nuevo está en Python.** Los scripts de limpieza y de particiones (10 y 20) siguen en R, en `03_hipotesis_y_variables/scripts_R_origen/`, porque sus resultados (`01_datos/preparados/`) son la entrada de todo lo demás y rehacerlos con otro generador de azar cambiaría las particiones registradas. Las líneas base B0 a B3 sí se hicieron en Python y dan lo mismo que en R (diferencia máxima 3e-14).

Aquí se explica, paso a paso, cómo se prepararon las 138 parcelas con rendimiento conocido, cómo se simuló la situación real de las 59 parcelas ocultas (esquemas V1, V2 y V3) y cuáles son los modelos de comparación (líneas base B0, B1, B2 y B3).

## La idea en una frase

Antes de probar cualquier variable hay que saber cuánto error se comete usando solo la ubicación de la parcela. Si una variable no baja ese error de forma clara, no sirve.

## Paso 1. Limpiar los datos (script 10)

`scripts_R_origen/10_limpieza.R` (en R) hace tres cosas sin tocar los originales:

1. Escribe "CEBADA" de una sola forma, porque venía como "Cebada" y como "CEBADA".
2. Repara las dos geometrías inválidas (AGC_070 y AGC_078). Solo se reparó lo que estaba mal, porque reparar todo movía polígonos que ya eran válidos.
3. Cuenta los valores negativos de LAI. En el paquete Básico son 18,916 de 44,877 lecturas (42.2%), y en PRO es 1 de 35,747. No se corrigió nada, solo se documentó.

Resultado: `01_datos/preparados/parcelas_limpias.gpkg` y `04_resultados/lai_negativo_conteo.csv`.

## Paso 2. Armar la base y las particiones (script 20)

`scripts_R_origen/20_folds.R` (en R) define cinco grupos de trabajo para las 138 parcelas: Chignahuapan (71), Tlaxcala (31), Singuilucan (16), Almoloya (10) y Otros_Hidalgo (10). Después ubica cada parcela en su celda climática real (cuadro de 5.5 km) y construye tres esquemas de validación.

Una celda climática importa porque las parcelas vecinas comparten el mismo clima. De las 59 ocultas, 57 (96.6%) están en una celda donde ya hay parcelas con rendimiento conocido. En el entrenamiento hay 23 celdas, y dos de ellas reúnen 34 parcelas cada una, es decir 68 de las 138 (49%).

| Esquema | Qué hace | Para qué sirve |
|---|---|---|
| **V1** (principal) | 100 divisiones 70/30. Cada una aparta el 30% de cada grupo al azar (41 parcelas). Semillas 1 a 100 | Imita cómo se separaron las 59 ocultas. En V1, 92.2% de las parcelas de validación tienen una vecina de su celda en el ajuste, contra 96.6% en la realidad |
| **V2** (prueba de esfuerzo) | 100 divisiones que apartan celdas completas, de modo que ninguna parcela de validación tiene vecina en su celda. Semillas 1001 a 1100, con reintentos | Es más difícil que la realidad. Dice si un modelo aprende algo de la parcela o solo memoriza la zona |
| **V3** | 5 pruebas, cada una deja fuera un grupo completo. Sin azar | Revisa si el modelo funciona en una región que nunca vio |

Reglas de V2: ningún grupo puede quedar sin parcelas en el ajuste, y ningún grupo puede tener más de 50% de sus parcelas en validación. Aunque son 100 repeticiones, solo hay 84 particiones de validación distintas, así que no son 100 pruebas independientes.

Resultado: `01_datos/preparados/base_138.csv`, `base_197_ubicacion.csv`, `folds_V1.csv`, `folds_V2.csv` y `folds_V3.csv`.

## Paso 3. Las líneas base B0, B1 y B2 (script 30)

`scripts/30_lineas_base.py` (Python, usa las funciones de `scripts/comun.py`).

Cada modelo se ajusta solo con las parcelas de `ajuste` y se mide en las de `validacion`. La métrica principal es el RMSE (error típico en t/ha, mientras más bajo mejor).

| Modelo | Qué predice | En palabras simples |
|---|---|---|
| **B0** | La media del rendimiento del ajuste | Decir siempre el promedio de todo |
| **B1** | La media de cada Estado | Saber en qué Estado está la parcela |
| **B2** | La media de cada grupo regional | Saber en qué grupo está la parcela |

Resultados (RMSE en t/ha, media de las 100 repeticiones):

| Esquema | B0 | B1 | B2 |
|---|---|---|---|
| V1 | 0.843 | 0.588 | **0.502** |
| V2 | 0.921 | 0.619 | **0.524** |

Lo que se encontró:

* Saber el Estado baja el error cerca de 30% frente a B0, y saber el grupo lo baja cerca de 41% en V1 (40.55%) y 42% en V2 (42.39%).
* B2 es la línea base contra la que se compara todo lo demás.
* Dentro de Chignahuapan, que es la mitad del entrenamiento, el error de B2 (0.55) es casi igual a la variación interna del rendimiento (0.58). Ahí el promedio regional no explica nada más, y es donde las variables tendrían que ayudar.
* En V3, B2 no se puede calcular porque el grupo que se deja fuera no existe en el ajuste. Se deja vacío y no se rellena.

Resultados completos: `04_resultados/lineas_base.csv`, `lineas_base_resumen.csv`, `rmse_por_grupo.csv`, `mejora_vs_B0.csv` y la figura `fig_lineas_base_rmse.png`.

## Paso 4. La línea base B3 (script 62)

`scripts/62_linea_base_B3.py` (Python). No usa azar.

B3 es la media de la celda climática encogida hacia la media del grupo. Predice cada parcela con `(n × media_celda + k × media_grupo) / (n + k)`, donde n es el número de parcelas de su celda en el ajuste y k se elige dentro de cada partición con solo las parcelas de ajuste (dejando una parcela fuera). Si la celda no tiene parcelas en el ajuste, usa B2.

Para qué se probó: el clima viene en celdas, y muchas variables de clima valen casi lo mismo dentro de una celda. B3 responde cuánta mejora se explica solamente por saber en qué celda está la parcela. La hipótesis H5 se escribió en el registro de experimentos antes de correrla.

Resultado (RMSE en t/ha):

| Esquema | B2 | B3 | Diferencia (B2 menos B3) | Particiones donde B3 mejora |
|---|---|---|---|---|
| V1 | 0.5021 | 0.4989 | +0.0032 | 56 de 100 |
| V2 | 0.5237 | 0.5237 | 0.0000 | 0 de 100 |

Cómo leerlo: en V1 B3 casi no mejora a B2, y en V2 no puede mejorar porque ninguna parcela de validación tiene vecina de celda. B3 no cumple la regla E1 (explicada en `03_hipotesis_y_variables/LEEME.md`), que pide una mejora mayor a 0.02 t/ha en 75 de 100 particiones o más. La lectura fijada de antemano en H5 dice que, con una mejora menor a 0.015, las variables aportan más que la sola ubicación.

## Material de contexto: `plan_y_contexto/`

Son documentos que se escribieron antes o durante esta fase. Se copiaron tal cual, sin corregir nada, para que quede constancia de cómo se decidió el trabajo.

| Archivo | Qué es |
|---|---|
| `00_mensaje_maestro.md` | El mensaje que definió el trabajo y las reglas del proyecto (por ejemplo que todo va en R, regla del proyecto original, y que cada variable se evalúa contra una línea base regional). Es copia textual del texto del 20 de septiembre de 2026 |
| `01_plan_fase1.md` | El plan de esta fase (limpieza, validación y líneas base). Quedó aprobado y ejecutado el 20 de septiembre de 2026. Al final tiene los resultados y las correcciones al plan |
| `borrador_mensaje_organizadores.md` | Borrador de un mensaje para los organizadores del reto. **NO SE ENVIÓ.** Está aquí solo como copia |

Aviso: estas copias conservan una fecha de entrega distinta a la actual en `00_mensaje_maestro.md` (dice 20 de octubre, y la fecha de entrega es el 19 de octubre). No se corrigió porque son copias del original; está anotado como pendiente en el resumen final.

## Para medir un modelo ajeno con estas mismas particiones

`scripts/comparar_modelo_externo.py` toma el modelo de otra persona (una función `predecir` en Python o un CSV de predicciones) y lo mide en las mismas particiones V1 y V2, con la misma regla E1 y contra B2, B3 y el modelo final. `scripts/ejemplo_modelo_externo.py` es una plantilla. La instrucción completa está en el encabezado del script. Prueba rápida: `python 02_validacion_y_lineas_base/scripts/comparar_modelo_externo.py --demo`.

## Cómo repetirlo

Desde la carpeta FINAL, en este orden:

```
python 02_validacion_y_lineas_base/scripts/30_lineas_base.py
python 02_validacion_y_lineas_base/scripts/62_linea_base_B3.py
```

Los pasos 1 y 2 (R) ya están hechos y sus resultados vienen en `01_datos/preparados/`. Para rehacerlos: `Rscript 03_hipotesis_y_variables/scripts_R_origen/10_limpieza.R` y luego `.../20_folds.R`.

El script 62 necesita antes los resultados del script 60 (carpeta 03). El orden completo está en `07_orden_de_ejecucion.md`. Cada script de Python compara su resultado con el CSV que produjo R (guardados en `04_resultados/referencia_R/`) y lo imprime al final. Salen iguales.

## Cambios en las copias de los scripts

Los scripts 30 y 62 de Python son una traducción de los de R (que siguen en `03_hipotesis_y_variables/scripts_R_origen/`). El 62 de Python no modifica el registro de experimentos; la fila H5 ya está escrita.
