# EXP_11 · Protocolo: combinación fija de modelos (exploratoria)

**Escrito el 8 de octubre de 2026, 22:3x h CDMX (9 oct UTC), después de verificar los insumos y antes de calcular cualquier métrica de las mezclas.** Autor: Claude (asistente), a pedido de Fortino. Los hashes se fijan en `registro_previo.json`.

## 1. De dónde viene la pregunta (reconocimiento explícito)

Esta hipótesis **nació después de examinar resultados anteriores** sobre las mismas 138 etiquetas:

- EXP_10 cerró con MIX como referencia y K = MIX + K1 corregido como alternativa documentada.
- Una comparación posterior no documentada (`tmp_comparacion_jared/`) mostró que J (Jared, procedimiento completo) y K tienen RMSE parecido y mejoran zonas distintas: K en Chignahuapan, J fuera de Chignahuapan. En Calpulalpan, la media municipal es ligeramente mejor que J.
- La correlación ≈ 0.037 reportada es entre las **correcciones respecto a MIX** (J − MIX y K − MIX). No es la correlación entre sus errores y no demuestra que combinarlos mejore.

Registrar esta ronda limita nuevas decisiones adaptativas, **pero no convierte estas etiquetas en una evaluación independiente**. Las particiones "nuevas" reutilizan las mismas etiquetas: son sensibilidad a la partición, no un conjunto de prueba.

## 2. Fórmulas (únicas que se evalúan)

Componentes (predicciones OOF completas ya existentes):

- **J:** Jared, procedimiento completo. En cada entrenamiento exterior elige entre 148 variables la de mayor |correlación| dentro de grupo, y ajusta OLS con nivel por grupo (5) y pendiente común.
- **K:** MIX + K1 corregido (EXP_10).
- **M:** MUN, media municipal (EXP_10).
- **MIX:** referencia (EXP_10).

Mezclas:

- **E_JK = 0.5 × J + 0.5 × K** (hipótesis principal)
- **E_MK = 0.5 × M + 0.5 × K** (control: ¿basta con reducir el peso de la interpolación espacial?)

Se promedian predicciones completas, no correcciones sobre MIX.

## 3. Presupuesto (cerrado)

| Concepto | Cantidad |
|---|---|
| Fórmulas evaluadas | 2 |
| Entrenamientos nuevos de candidatos | 0 |
| Búsqueda de pesos | 0 |
| Variables nuevas | 0 |
| Selección por municipio | 0 |
| Predicciones de las 59 | 0 |
| Ajustes solo de verificación (ya ejecutados en la preparación) | 200 reproducciones del procedimiento de Jared: 100 pliegues × (normal + etiquetas de validación sustituidas) |

No se probarán 25/75, 75/25, stacking, gating ni mezclas regionales, aunque el resultado lo sugiera.

## 4. Insumos verificados (`scripts/preparar_exp_11.py`, sin calcular mezclas)

- `data/exp_11_combinacion_modelos/oof_componentes.csv`: MIX, MUN y K copiados de EXP_10; J de la comparación temporal. Clave única (conjunto, repetición, pliegue, ID, modelo); 2,760 filas por modelo; mismas etiquetas, municipio y máscara.
- **Concordancia:** las filas coinciden con las particiones originales. MIX, MUN y K reproducen EXP_10 (dif. ≤ 1e-15). Las métricas de MIX, MUN y K coinciden con `metricas.csv` de EXP_10 (≤ 1e-16). Las de J coinciden con lo reportado (0.4835/0.4821 RMSE; 0.3315/0.3314 MAE).
- **Procedencia de J:** implementación independiente desde las variables **sin estandarizar**. Dif. máx. 1.3e-13 con las predicciones guardadas. Al sustituir las etiquetas de validación, las predicciones y la variable elegida no cambian. Elige `anom_precip_pct_d` en 48/50 y 49/50 pliegues.
- **Transformación de X en la comparación original:** estandarización con las 197 parcelas (solo X), como en el script de Jared. Es invariante para la correlación y el OLS con niveles por grupo. No se modifica.
- Copias de procedencia en `data/exp_11_combinacion_modelos/procedencia_jared/`: script, métricas y predicciones de la comparación temporal, y las variables de Jared comprobadas byte a byte contra su ZIP original.

## 5. Evaluación

- **SEEN135** (máscara `municipio_visto`) principal; **FULL138** como sensibilidad, con la explicación de los municipios de una sola etiqueta.
- Particiones históricas y nuevas, por separado.
- RMSE y MAE agrupados sobre las filas OOF, sin promediar antes por parcela.
- Diferencias pareadas frente a MIX, J, K y M; E_JK frente a E_MK; por repetición y número de repeticiones con mejora; Chignahuapan/resto; municipios con tamaño de muestra.
- No se usan pruebas que traten las 1,350/1,380 filas como independientes.

**Diagnósticos:**

- Correlación de errores (J vs K, M vs K) y de cambios respecto a MIX (J − MIX vs K − MIX; M − MIX vs K − MIX). Son explicativos, no prueba de mejora.
- **Concentración, orden declarado ahora:** para cada candidato c, referencia r y juego s, se calcula d_i = Σ_rep [(ŷ_c − y)² − (ŷ_r − y)²] sobre las filas SEEN135 de la parcela i. Se ordena ascendente (la más favorecida primero), con empates por ID ascendente. Se retiran solo de la evaluación las 2 y las 5 primeras, frente a MIX y frente al mejor componente individual (menor RMSE SEEN agrupado en ese juego).

## 6. Criterio de lectura (no es regla de adopción)

**Señal favorable** para una mezcla, en SEEN135:

1. RMSE agrupado < el del mejor de sus componentes, en **ambos** juegos.
2. ≥8/10 repeticiones con mejora frente a **cada** componente, en cada juego.
3. Cualquier deterioro de MAE se expone frente a MIX, MUN, J y K. No se exige superar el MAE de MUN para hablar de mejora de RMSE, pero el compromiso se informa.

**Clasificación:**

- **A.** No supera al mejor componente en algún juego.
- **B.** Lo supera en ambos, pero falla la estabilidad (punto 2) o la ganancia frente al mejor componente se invierte al retirar las 2 parcelas más favorecidas en algún juego. Es frágil o concentrada.
- **C.** Lo supera en ambos, con estabilidad y sin invertirse al retirar 2 parcelas. Merece revisión como candidato.

**Interpretación con el control:**

- Si **E_MK iguala o supera a E_JK** en RMSE agrupado en algún juego, no se atribuye la mejora a información específica de Jared.
- Hablar de "aporte específico de J" requiere E_JK < E_MK en ambos juegos y ≥8/10 repeticiones en cada uno.
- Si E_JK gana, se habla de **complementariedad predictiva observada**, no de causalidad agronómica ni de generalización demostrada.

Las reglas históricas de adopción (R1–R4 y S de EXP_10) se mantienen separadas y no se reinterpretan. **No se buscarán variantes después de conocer el resultado.** La ablación sin territorio queda fuera.
