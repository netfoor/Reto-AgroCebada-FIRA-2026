# Entrega FIRA, equipo UNO

Reto AgroCebada FIRA 2026. Fecha límite: 19 de octubre de 2026, 23:59 (hora de la Ciudad de México). Todo se envía también a innovacion@fira.gob.mx.

| Entregable | Dónde está |
|---|---|
| Predicciones de las 59 parcelas (`nombre_del_equipo_prediccion.csv`) | [`UNO_prediccion.csv`](UNO_prediccion.csv), mismas columnas que la base original: ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO |
| Aplicación y dashboard | https://d6wslbico5u76.cloudfront.net (código en [`web/`](../web) y [`api/`](../api)) |
| Código fuente | este repositorio |
| Métricas de validación con RMSE, MAE y R² | [`resultados/04_seleccion_modelo_final/metricas_validacion_con_r2.csv`](../resultados/04_seleccion_modelo_final/metricas_validacion_con_r2.csv), generado por [`scripts/agregar_r2.py`](../scripts/agregar_r2.py) |
| Prompts de IA | [`prompts_IA/`](../prompts_IA) |
| Exploración previa de Jared (R y Python, registro de experimentos) | [`exploracion_previa_Jared/`](../exploracion_previa_Jared) |
| Informe, bibliografía y anexo técnico en PDF | se envían por correo y por la plataforma; el PDF final se agrega aquí cuando el equipo lo exporte |

## Modelo y cifras

El modelo final es E_JK = 0.5·J + 0.5·K. Las predicciones son las de `resultados/04_seleccion_modelo_final/predicciones_59.csv`, con los mismos valores a cuatro decimales. El archivo de entrega solo agrega el área de cada parcela y la columna CONJUNTO para respetar el formato de la base original.

Validación cruzada de 5 pliegues repetida 10 veces, 135 parcelas (SEEN135), particiones históricas:

| Modelo | RMSE (t/ha) | MAE (t/ha) | R² |
|---|---|---|---|
| MUN | 0.4934 | 0.3213 | 0.657 |
| MIX | 0.4872 | 0.3342 | 0.666 |
| J | 0.4835 | 0.3315 | 0.671 |
| K | 0.4820 | 0.3334 | 0.673 |
| E_JK | 0.4757 | 0.3214 | 0.682 |

Son estimaciones de desempeño; no equivalen al error sobre las 59 parcelas que FIRA mantiene ocultas.
