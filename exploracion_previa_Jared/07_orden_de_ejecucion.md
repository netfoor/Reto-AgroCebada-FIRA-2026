# 07_orden_de_ejecucion: en qué orden correr los scripts

Todos los scripts se corren **desde la carpeta FINAL** o desde cualquier lugar: los de Python encuentran la carpeta solos. Ejemplo:

```
python 02_validacion_y_lineas_base/scripts/30_lineas_base.py
```

Se necesita Python 3.10 o más nuevo y los paquetes de `requirements.txt` (`pip install -r requirements.txt`): numpy, pandas, scipy, matplotlib, scikit-learn y python-docx. Solo `numpy`, `pandas`, `scipy` y `matplotlib` son indispensables para repetir los resultados; `scikit-learn` lo usa el script 70 y `python-docx` solo sirve para revisar la guía.

Los scripts usan semillas fijas (V1: 1 a 100, V2: 1001 a 1100, permutación: 2026 y 2027, árboles: 2026), así que repetirlos da los mismos resultados.

## Orden de los scripts de Python

| Paso | Script | Qué hace | Entradas | Salidas |
|---|---|---|---|---|
| 1 | `02_validacion_y_lineas_base/scripts/30_lineas_base.py` | Calcula B0, B1 y B2 en V1, V2 y V3 | `01_datos/preparados/base_138.csv`, `folds_V*.csv` | `04_resultados/lineas_base.csv`, `lineas_base_resumen.csv`, `mejora_vs_B0.csv`, `rmse_por_grupo.csv`, `fig_lineas_base_rmse.png` |
| 2 | `.../62_linea_base_B3.py` | Calcula B3 (media por celda encogida hacia B2) | `base_138.csv`, `folds_V1/V2.csv` | `04_resultados/62_b3_por_particion.csv`, `62_b3_resumen.csv` |
| 3 | `03_hipotesis_y_variables/scripts/60_evaluacion_variables.py` | Aplica la regla E1 a las 148 variables, hace los controles de permutación (el más lento, unos minutos) y la selección dentro de partición | `base_138.csv`, `folds_V*.csv`, `variables/*_features.csv` y `*_hipotesis.csv` | `04_resultados/60_pruebas_por_variable.csv`, `60_resumen_hipotesis.csv`, `60_permutacion.csv`, `60_seleccion_en_particion.csv` |
| 4 | `.../70_candidatos_E6.py` | Prueba los candidatos C1, C2, C3 y C5 de la fila E6 contra el modelo actual | igual que el paso 3 | `04_resultados/70_candidatos_por_particion.csv`, `70_candidatos_resumen.csv` |
| 5 | `05_modelo_final/modelo_final.py` | Elige la variable, ajusta el modelo final y predice las 59 parcelas. Compara contra R | `base_138.csv`, `base_197_ubicacion.csv`, CSV de ID y rendimiento, `variables/`, resultados 60 y 62 | `06_prediccion/predicciones_59_parcelas.csv`, `05_modelo_final/modelo_final_*.csv` |
| 6 | `04_resultados/tablas_y_graficas.py` | Resume en tablas y gráficas | resultados 60, 62 y 70 | `variables_que_pasan_E1.csv`, `comparacion_modelos.csv`, `fig_comparacion_modelos.png`, `fig_variables_que_pasan_E1.png` |

El paso 3 debe ir antes del 5 y del 6, y el 2 antes del 6. Los pasos 1 y 2 no dependen del 3.

Cada script escribe lo que imprime en `04_resultados/logs/`.

## Herramienta para comparar con otro modelo

| Script | Qué hace |
|---|---|
| `02_validacion_y_lineas_base/scripts/comparar_modelo_externo.py` | Mide un modelo ajeno en las mismas particiones V1 y V2 y le aplica la regla E1. Lee una función `predecir(ajuste, validacion)` en Python o un CSV de predicciones. Escribe en `04_resultados/comparacion_externo/` |
| `.../ejemplo_modelo_externo.py` | Plantilla para escribir la función `predecir` |

Prueba rápida del comparador (debe dar V1 0.5021 para B2 y 0.4734 para el modelo final): `python 02_validacion_y_lineas_base/scripts/comparar_modelo_externo.py --demo`. Para el modelo de otra persona: `python .../comparar_modelo_externo.py --modelo su_modelo.py --nombre MIX`.

## Pasos ya hechos (siguen en R)

Estos pasos producen las entradas de todo lo demás. Sus resultados ya vienen en la carpeta, no hace falta repetirlos. Para rehacerlos se necesita R 4.5 con `readr`, `dplyr`, `tidyr`, `tibble`, `ggplot2`, `sf` y `terra`, y los rasters en `01_datos/originales/` (no se copiaron). Se corren desde la carpeta FINAL, por ejemplo `Rscript 03_hipotesis_y_variables/scripts_R_origen/10_limpieza.R`.

| Paso | Script (R) | Qué hace | Salidas |
|---|---|---|---|
| 0 | `01_datos/eda_inicial/scripts_R/01` a `08` | Primer análisis exploratorio y tablas por parcela | `01_datos/derivados/`, `eda/`, `figuras/` |
| R1 | `03_hipotesis_y_variables/scripts_R_origen/10_limpieza.R` | Limpia las parcelas y cuenta LAI negativo | `01_datos/preparados/parcelas_limpias.gpkg` |
| R2 | `.../20_folds.R` | Arma la base de 138 parcelas, los grupos, las celdas y los esquemas V1, V2 y V3 | `base_138.csv`, `base_197_ubicacion.csv`, `folds_V*.csv` |
| R3 a R7 | `.../51_` a `55_variables_*.R` | Construyen las 148 variables en 5 familias (27, 17, 40, 32 y 32) | `03_hipotesis_y_variables/variables/` |
| R8 | `.../40_chequeos_1B.R` | Cifras [CP] de la hoja E de agronomía (opcional) | `04_resultados/1B_chequeos.csv` |
| R9 | `.../30_lineas_base.R`, `60_evaluacion_variables.R`, `62_linea_base_B3.R` | Versión original de los pasos 1 a 3 en R | `04_resultados/referencia_R/` guarda sus resultados para comparar |

Los scripts `25` a `29`, `35` y `61` de `scripts_historicos_registro/` escribieron las filas del registro de experimentos. **No se corren:** tienen las rutas del proyecto original y modificarían ese registro.

## Cosas a tener en cuenta

* Los scripts de Python **no modifican** `03_hipotesis_y_variables/registro_experimentos.csv`. Las filas E4 a E7 se escribieron a mano (E6 antes de correr el script 70, E7 con su resultado).
* Los controles de permutación de Python dan números distintos a los de R por el generador de azar (ver `03_hipotesis_y_variables/LEEME.md`). Todo lo demás es idéntico.
* El formato de las 59 predicciones es provisional [incierto] (ver `06_prediccion/LEEME.md`).
