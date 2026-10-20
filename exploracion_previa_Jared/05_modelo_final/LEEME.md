# 05_modelo_final: el modelo que predice las 59 parcelas ocultas

Aquí está el script (en Python) que ajusta el modelo final y predice, y la explicación de por qué se eligió ese modelo y no otro.

## Cómo se eligió el modelo (criterio, sin cambiar ninguna regla)

Solo se usaron reglas que ya estaban en el registro de experimentos. El razonamiento está escrito en la fila E4, antes de ajustar el modelo.

1. **Candidatos:** B2 (media por grupo), B3 (media por celda climática) y los dos procedimientos de elegir variable dentro de cada partición que se definieron en la fila E2: `top1_global` (la mejor variable) y `top3_global` (las 3 mejores).
2. **Se aplicó la regla E1** (explicada en `03_hipotesis_y_variables/LEEME.md`) a los resultados que ya estaban calculados:

| Candidato | Mejora vs B2 en V1 | Particiones V1 donde mejora | Mejora vs B2 en V2 | ¿Cumple E1? |
|---|---|---|---|---|
| B3 | +0.0032 | 56 de 100 | 0.0000 | **No** (necesita más de 0.02 y 75 de 100) |
| top1_global | +0.0287 | 86 de 100 | +0.0558 | Sí |
| top3_global | +0.0289 | 85 de 100 | +0.0611 | Sí |

3. **Desempate.** La regla no decía cómo desempatar. Jared lo delegó el 30 de septiembre de 2026 y se fijó así: entre los que cumplen E1 se elige el de menos parámetros, porque con 138 parcelas conviene el modelo más simple. Ese es `top1_global`. La diferencia con `top3_global` en V1 es 0.0002 t/ha, mucho menor que la variación entre particiones.

4. **Candidatos nuevos (filas E6 y E7).** Después se probaron candidatos más complejos (residuo por celda, ridge, árboles). Ninguno cumplió la regla de reemplazo escrita antes de correrlos, así que `top1_global` se mantiene (detalle en `03_hipotesis_y_variables/LEEME.md`).

Si ninguna variable hubiera cumplido E1, el modelo final habría sido B2 y así se habría dicho. No fue el caso.

## Qué hace el modelo

Es una regresión lineal: **rendimiento ~ grupo + una variable**. Cada grupo (Chignahuapan, Tlaxcala, Singuilucan, Almoloya y Otros_Hidalgo) tiene su nivel, y la variable elegida mueve la predicción hacia arriba o hacia abajo con la misma pendiente para todos.

La variable se elige con las 138 parcelas de entrenamiento: entre las 148 candidatas (estandarizadas con las 197 parcelas) se toma la que tiene mayor correlación en valor absoluto con el rendimiento dentro de cada grupo. Si a una parcela le faltara la variable se predeciría con B2, sin imputar (en las 59 ocultas no faltó en ninguna).

## Qué salió

* **Variable elegida: `anom_precip_pct_d`**, la anomalía de la lluvia de octubre de 2025 frente al promedio de 2022 a 2024 (hipótesis HN3, familia de anomalías climáticas). Su correlación dentro de grupo es 0.3872 y su coeficiente es 0.596 t/ha por cada desviación estándar (error estándar 0.1235).
* Las 5 variables con mayor correlación fueron `anom_precip_pct_d` (0.3872), `anom_tmin_c` (0.3416), `anom_tmin_sep_oct` (0.3397), `clim_rango_termico_sep` (-0.3378) y `anom_tmax_d` (0.3356). Las diferencias entre ellas son pequeñas, así que el primer lugar no es muy distinto del segundo.
* Error esperado (RMSE en t/ha): V1 0.4734 contra 0.5021 de B2, y V2 0.4679 contra 0.5237 de B2.
* Las 59 predicciones van de 2.91 a 4.69 t/ha. Están en `06_prediccion/predicciones_59_parcelas.csv`.

## Cómo leer el resultado (límites)

* La variable elegida **no tenía un signo registrado de antemano**, así que es un hallazgo exploratorio, no una hipótesis confirmada.
* Las anomalías climáticas son casi etiquetas de celda (entre 98.9% y casi 100% de su variación se explica con la celda), y en el entrenamiento solo hay 23 celdas. Por eso la variable puede estar reflejando en qué zona está la parcela y no el efecto de la lluvia de octubre.
* La mejora es pequeña frente al error: 0.03 t/ha contra un error de 0.47 a 0.50.
* El rendimiento es de una sola temporada (2025).
* El error esperado es el RMSE de V1 y V2, **no un intervalo de confianza** de las predicciones.
* La variable se eligió con las mismas 138 parcelas con las que se ajusta el modelo. El delta de V1 ya incluye la elección dentro de cada partición, y por eso es la cifra a usar como error esperado.

## Archivos

| Archivo | Qué es |
|---|---|
| `modelo_final.py` | El script. No usa azar, así que siempre da lo mismo. Al final compara con lo que produjo R |
| `../04_resultados/logs/modelo_final.log` | Lo que imprimió al correr |
| `modelo_final_resumen.csv` | Variable elegida, correlación, coeficiente, RMSE de B2, B3 y modelo final, y si cumple E1 |
| `modelo_final_coeficientes.csv` | La tabla de coeficientes del modelo (nivel de cada grupo y pendiente de la variable) |
| `modelo_final_top5_variables.csv` | Las 5 variables con mayor correlación dentro de grupo |

## Cómo correrlo

Desde la carpeta FINAL, con los resultados de los scripts 60 y 62 ya generados:

```
python 05_modelo_final/modelo_final.py
```

Necesita `numpy`, `pandas` y `scipy` (ver `requirements.txt`). Las 59 predicciones y los coeficientes salen iguales a los de R (diferencia máxima 0.00 t/ha y 3e-14). El script se detiene con un mensaje si `top1_global` no cumpliera E1 en los resultados que lee. Escribe las predicciones en `06_prediccion/` y los archivos de esta carpeta.
