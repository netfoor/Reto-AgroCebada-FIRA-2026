# 06_prediccion: las 59 predicciones

`predicciones_59_parcelas.csv` tiene la predicción de rendimiento (t/ha) de las 59 parcelas cuyo rendimiento está oculto. La produce `05_modelo_final/modelo_final.py`.

## [incierto] El formato de entrega es provisional

Ni en las bases ni en las reglas del reto aparece el formato exacto en que hay que entregar las predicciones. Por decisión de Jared (30 de septiembre de 2026) se usa de forma provisional el formato del CSV base del reto. **Antes del 19 de octubre hay que confirmar el formato con los organizadores** (el borrador de mensaje está en `02_validacion_y_lineas_base/plan_y_contexto/` y no se envió). Si el formato final es otro, solo hay que reordenar o renombrar las columnas de este archivo.

## Qué trae el archivo

| Columna | Qué es |
|---|---|
| `ID_POLIGONO` | El identificador de la parcela, por ejemplo AGC_003 |
| `AREA_HA` | El área de la parcela en hectáreas, tal como viene en la base del reto |
| `RENDIMIENTO_T_HA` | La predicción, en toneladas por hectárea, con 2 decimales |
| `CONJUNTO` | Siempre dice `PREDICCION`, igual que en el archivo original del reto |

Son 59 filas más el encabezado.

## Cómo se hicieron

Con el modelo de `05_modelo_final/`: rendimiento ~ grupo + `anom_precip_pct_d`, ajustado con las 138 parcelas de entrenamiento. Las 59 parcelas tenían el valor de la variable, así que ninguna se predijo solo con la media del grupo.

| Grupo | Parcelas ocultas | Predicción media (t/ha) | Media de entrenamiento (t/ha) |
|---|---|---|---|
| Chignahuapan | 29 | 4.443 | 4.477 |
| Tlaxcala | 15 | 2.976 | 2.984 |
| Singuilucan | 7 | 3.067 | 3.081 |
| Almoloya | 4 | 4.650 | 4.521 |
| Otros_Hidalgo | 4 | 4.562 | 4.094 |

El rango de las 59 predicciones es de 2.91 a 4.69 t/ha.

## Cómo usarlas con cuidado

* El error esperado de cada predicción es de unos 0.47 t/ha (RMSE de V1 y V2 del modelo final). No es un intervalo de confianza.
* Casi toda la diferencia entre parcelas viene del grupo al que pertenecen. La variable agrega una mejora pequeña (ver `05_modelo_final/LEEME.md`).
* Los grupos pequeños (Almoloya y Otros_Hidalgo, 4 parcelas ocultas cada uno) son los más inciertos, porque se estiman con 10 parcelas de entrenamiento cada uno.
