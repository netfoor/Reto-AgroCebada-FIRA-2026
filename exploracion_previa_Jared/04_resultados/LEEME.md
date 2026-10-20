# 04_resultados: las tablas y gráficas que salieron

Aquí están todos los resultados que producen los scripts de las carpetas 02 y 03, más las dos gráficas y las dos tablas que resumen lo más importante. Esta carpeta no tiene scripts de modelado: solo `tablas_y_graficas.py`, que ordena resultados que ya existían. En `referencia_R/` están, sin tocar, los resultados que produjo la versión en R (sirven para comprobar que Python da lo mismo).

## Aviso que va primero

**Las 13 variables que pasan la regla E1 son pocas señales repetidas, no 13 descubrimientos independientes.** En el entrenamiento solo hay 23 celdas climáticas, y dos de ellas reúnen 34 parcelas cada una (68 de las 138). Las anomalías climáticas explican entre 98.9% y casi 100% de su variación con la celda, es decir que son casi etiquetas de celda, y muchas de las 13 llevan la misma información. Además, el rendimiento es de una sola temporada (2025, la más lluviosa de la serie) y las 100 particiones de validación no son independientes. Las variables son candidatas, no causas.

## Las gráficas y tablas principales

| Archivo | Qué muestra |
|---|---|
| `fig_comparacion_modelos.png` | El error (RMSE) de B2, B3 y del modelo final en V1 y V2. Mientras más bajo, mejor |
| `comparacion_modelos.csv` | Los números de esa gráfica |
| `fig_variables_que_pasan_E1.png` | Las 14 variables que pasan E1 (13 completas y 1 solo con vecinas), con su mejora frente a B2 en V1 y en V2. B3 va como referencia |
| `variables_que_pasan_E1.csv` | La tabla de esas 14 variables con su hipótesis, el signo registrado de antemano, si coincide, y la lectura |
| `fig_lineas_base_rmse.png` | El error de B0, B1 y B2 |

## Cuánto error tiene cada modelo

RMSE en t/ha, media de las 100 particiones (menor es mejor):

| Modelo | V1 | V2 |
|---|---|---|
| B2 (media por grupo, la línea base) | 0.5021 | 0.5237 |
| B3 (media por celda climática, encogida hacia B2) | 0.4989 | 0.5237 |
| Modelo final (grupo más una variable) | 0.4734 | 0.4679 |

`comparacion_modelos.csv` también trae los candidatos nuevos C1, C2, C3 y C5 (ver `03_hipotesis_y_variables/LEEME.md`); ninguno supera al modelo final.

Cómo leerlo: B3 casi no mejora a B2, así que saber en qué celda está la parcela explica poco. El modelo final baja el error 0.0287 t/ha en V1 (mejora en 86 de 100 particiones) y 0.0558 en V2 (94 de 100). Es una mejora real pero pequeña frente a un error de 0.50 t/ha.

## Qué se encontró con las 148 variables

Se hicieron 150 pruebas (148 variables lineales y 2 curvas). La regla E1 está explicada en `03_hipotesis_y_variables/LEEME.md`.

| Veredicto | Cuántas |
|---|---|
| Pasan E1 | 13 (9 anomalías climáticas, el rango térmico de septiembre y 3 índices Sentinel-2 de abril y mayo) |
| Pasa solo con vecinas | 1 (Tmin de abril y mayo) |
| Descartadas | 136 |
| No evaluable | 1 (HC2, su indicador vale 1 en las 197 parcelas) |

Control de permutación (versión Python): con el rendimiento barajado pasan por azar en promedio 0.33 variables por el control por grupo (máximo 18 en 100 repeticiones) y 0.53 por el control estricto por celda (máximo 11). En R fueron 0.08 (máximo 5) y 0.16 (máximo 11); la diferencia es solo el generador de números al azar. En lo real pasan 13. La distancia al máximo por azar de los controles no es holgada.

Las variables de vigor satelital de las hipótesis principales (NDVI, EVI, SAVI, MSAVI, LAI, índices de agua y variabilidad dentro de la parcela) no mejoran a B2.

## Todos los archivos, por script que los produce

| Archivo | Script | Contenido |
|---|---|---|
| `lai_negativo_conteo.csv` | 10 (R) | Conteo de valores negativos de LAI. Está en `referencia_R/` |
| `resumen_esquemas.csv` | 20 (R) | Descripción de V1, V2 y V3. Está en `referencia_R/` |
| `lineas_base.csv`, `lineas_base_resumen.csv`, `mejora_vs_B0.csv`, `rmse_por_grupo.csv`, `fig_lineas_base_rmse.png` | 30 | Error de B0, B1 y B2 por partición, resumen, mejora y error por grupo |
| `62_b3_por_particion.csv`, `62_b3_resumen.csv` | 62 | Línea base B3 |
| `60_pruebas_por_variable.csv` | 60 | Una fila por prueba (150), con deltas, número de particiones que mejoran y veredicto |
| `60_resumen_hipotesis.csv` | 60 | Resumen por hipótesis |
| `60_permutacion.csv` | 60 | Resultado de los dos controles de permutación |
| `60_seleccion_en_particion.csv` | 60 | Resultado de elegir la variable dentro de cada partición (top1_global y top3_global) |
| `1B_chequeos.csv` | 40 (en `03_hipotesis_y_variables/agronomia/`) | Cifras [CP] de la hoja E de agronomía |
| `70_candidatos_por_particion.csv`, `70_candidatos_resumen.csv` | 70 | Candidatos nuevos de la fila E6 |
| `variables_que_pasan_E1.csv`, `comparacion_modelos.csv`, las dos gráficas | `tablas_y_graficas.py` | Resumen de lo anterior |
| `comparacion_externo/` | `comparar_modelo_externo.py` | Resultados de medir un modelo ajeno (solo si se corre) |
| `logs/` | todos | Lo que imprimió cada script al correr. `60_salida_consola.txt` es la salida completa del script 60. `registro_antes_62.csv` es una copia del registro que hace el script 62 antes de modificarlo |

Los scripts 51 a 55 no escriben aquí resultados, solo sus logs; sus variables van a `03_hipotesis_y_variables/variables/`.

## Cómo repetirlo

Desde la carpeta FINAL, después de correr los scripts 30, 60, 62 y 70 (ver `07_orden_de_ejecucion.md`):

```
python 04_resultados/tablas_y_graficas.py
```

## Cambios y errores corregidos en esta copia

* `tablas_y_graficas.py` es la versión en Python de las tablas y gráficas, y suma los candidatos nuevos. Las cifras salen solo de los CSV de los scripts 60, 62 y 70.
* Los logs de `logs/` son los de la última corrida de los scripts de Python. Los CSV de 30, 60 (menos la permutación) y 62 salen idénticos a los de R.
