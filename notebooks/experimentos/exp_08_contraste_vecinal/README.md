# EXP_08 · Contraste vecinal del verdor

8 de octubre de 2026. **Exploratorio con elementos predeclarados. Sin protocolo ratificado y sin las 59 predicciones de entrega.**

> **Fe de erratas (8 oct 2026, posterior; ver [EXP_10](../exp_10_verificacion_contraste_vecinal/RESULTADOS_Y_CIERRE.md)).** La variante "contraste 1 km hasta 31 oct" suavizaba con capturas de todo el año y recortaba después. Por eso noviembre influía en octubre. Con el corte bien implementado (EXP_10), la mejora frente a MIX se mantiene, pero ~7 % menor: SEEN135 0.48198 frente a 0.4816 de la variante publicada. C1 con todo el año, que usa noviembre de forma declarada, daba 0.4817. Este cuaderno y sus cifras se conservan sin cambios como registro histórico.

## Qué contiene

| Archivo | Qué es |
| --- | --- |
| `exp_08_contraste_vecinal.ipynb` | Cuaderno ejecutado, con salidas. Formato pregunta → comprobación → resultado → decisión y límite. |
| `PREDECLARACION_replica_S2.md` | Receta y criterio de la réplica con Sentinel-2, escritos **antes** de calcularla (12:09 h CDMX). |
| `../../../scripts/construir_exp_08.py` | Generador del cuaderno. Las celdas están en el script; no hay motores ocultos. |

## La pregunta y por qué cambia de enfoque

Las seis rondas y EXP_07 preguntaron "¿esta variable mejora la referencia?". Este cuaderno pregunta primero **por qué casi nada la mejora**:

1. **El error está dentro de los municipios.** Chignahuapan concentra el 73 % del error cuadrático de MIX.
2. **Ninguna de las 619 variables ya construidas** (ciclo, historia, clima, topografía, nov–dic, área) muestra señal individual dentro del municipio distinguible del azar. El máximo observado, |r| = 0.25, es típico del nulo por permutación (p = 0.60). La dispersión de EXP_07 tiene r = 0.08.
3. **El residuo municipal tiene dependencia espacial corta (<500 m).** MIX ya la aprovecha. Un kriging y un MIX con hiperparámetros afinados son **peores** que MIX fijo: con n = 138, elegir hiperparámetros cuesta más de lo que aporta.

De ahí sale **H8**: comparar la curva de verdor de cada parcela con la de sus vecinas a <1 km cancela lo que comparten (territorio, fechas de captura, clima, ventana de lluvias). Lo que queda puede ser propio de la parcela.

## Resultado (SEEN135 principal)

| Procedimiento | RMSE | MAE | Repeticiones con RMSE < MIX |
| --- | --- | --- | --- |
| MIX (referencia) | 0.4872 | 0.3342 | — |
| MUN | 0.4934 | 0.3213 | 1/10 |
| **C1 · MIX + β·contraste de integral a 1 km** | **0.4817** | 0.3333 | 10/10 |
| C1 cortado al 31 oct | 0.4816 | 0.3330 | 10/10 |
| C2 · selección honesta entre 32 contrastes dentro de cada entrenamiento | 0.4831 | 0.3347 | 7/10 |
| Sentinel-2 · mismo contraste (réplica predeclarada) | 0.4806 | 0.3311 | 10/10 |
| Integral sin contraste | 0.4859 | 0.3345 | 9/10 |

* β < 0 en las 50 particiones: más verde y más temprana que sus vecinas → rinde **menos** de lo que predice el territorio.
* Nulo por permutación: p ≈ 0.03 con receta fija (C1); p ≈ 0.05 descontando la selección (C2).
* Concentración: sin las 2 parcelas más favorecidas queda ~1/5 de la ganancia; sin las 5, se invierte.
* Reglas del proyecto: cumple RMSE < MIX; **no** cumple MAE ≤ MUN; MAE ≤ MIX en 7/10 repeticiones.

**Lectura:** es la única señal satelital encontrada que pasa todos estos filtros a la vez. Su efecto es pequeño (~1 % de RMSE) y está concentrado. Es un **candidato con reservas**, no un ganador.

## Recomendación al equipo

1. Cerrar la búsqueda de agregados (otro índice, ventana, estadística o umbral de nube).
2. Si se hace una ronda más, que sea C1 en su versión **al 31 de octubre**, ratificada antes de ajustar y sin cambiar radio, variable ni α. Después, congelar y dedicar el tiempo a las 59 predicciones y a la herramienta.
3. Elegir entre MIX y MIX + C1 cuando FIRA confirme la métrica. Con RMSE/R², C1 tiene una ventaja esperada pequeña. Con MAE, MUN sigue siendo mejor.

## Ejecutar

```bash
uv run --locked --all-groups python scripts/construir_exp_08.py --ejecutar
```

Tarda ~4 minutos. Lee `data/raw/DataSet.zip`, las particiones de `data/validacion_03/` y las tablas de `data/referencias/`, y verifica sus SHA-256. Hace ajustes nuevos: el presupuesto está en la sección 9 del cuaderno.

## Pendiente de integrar (no se tocó para no interferir con EXP_07 en curso)

- Fila de EXP_08 en `gestion/bitacora_experimentos.md`.
- Enlace en `README.md` y `notebooks/README.md`.
- Actualizar `docs/07_sintesis_y_priorizacion.md` con el barrido del bloque B: explica por qué las rondas anteriores no encontraron señal.
