# EXP_11 · Resultados y cierre

8 de octubre de 2026, CDMX. Registro previo: 22:32 h (04:32:20 UTC del 9 oct). Autor: Claude (asistente), a pedido de Fortino. **Exploratorio**: la hipótesis nació después de ver EXP_10 y la comparación temporal con Jared sobre las mismas 138 etiquetas.

## Pregunta

¿Una mezcla fija **E_JK = ½·J + ½·K** (J = Jared, procedimiento completo; K = MIX + K1 corregido) mejora a sus componentes? ¿O basta **E_MK = ½·MUN + ½·K**?

## Resultados (SEEN135)

| Procedimiento | RMSE hist. | RMSE nuevas | MAE hist. | MAE nuevas |
|---|---|---|---|---|
| MIX | 0.48720 | 0.48567 | 0.33421 | 0.33571 |
| MUN | 0.49340 | 0.49222 | 0.32127 | 0.32133 |
| J | 0.48354 | 0.48214 | 0.33152 | 0.33137 |
| K | 0.48198 | 0.48096 | 0.33337 | 0.33488 |
| **E_JK** | **0.47566** | **0.47440** | 0.32137 | 0.32245 |
| E_MK | 0.48235 | 0.48107 | 0.32125 | 0.32247 |

**Diferencias pareadas de E_JK** (RMSE; repeticiones con mejora):

| Frente a | Históricas | Nuevas |
|---|---|---|
| K (mejor componente) | −0.0063; 10/10 | −0.0066; 10/10 |
| J | −0.0079; 10/10 | −0.0077; 9/10 |
| MIX | −0.0115; 10/10 | −0.0113; 10/10 |
| E_MK | −0.0067; 10/10 | −0.0067; 10/10 |

**E_MK frente a K:** +0.0004 (5/10) y +0.0001 (5/10). No mejora.

**MAE:** E_JK mejora a MIX, J y K en ambos juegos. Frente a MUN queda +0.0001 (históricas) y +0.0011 (nuevas): un compromiso pequeño pero real.

**FULL138 (sensibilidad):** E_JK 0.4775/0.4764; J 0.4833/0.4819; K 0.4879/0.4870; MIX 0.4938/0.4923. Las 3 parcelas de municipios con una sola etiqueta (AGC_047, AGC_048, AGC_164) se validan sin la media de su municipio. Ahí J usa su grupo regional y es claramente mejor (RMSE ≈0.47 frente a ≈0.71 de K y ≈1.05 de MUN). E_JK queda en medio (≈0.56).

## Diagnósticos

- **Correlación entre errores:** J vs K 0.94; MUN vs K 0.96. Ambos fallan juntos en las parcelas difíciles.
- **Correlación entre cambios respecto a MIX:** J−MIX vs K−MIX 0.03–0.04; MUN−MIX vs K−MIX ≈ −0.03.
- Ninguna de las dos prueba la mejora. Explican que la ganancia sale de la pequeña parte del error que J y K no comparten, según la identidad MSE(½a+½b) = ¼MSE_a + ¼MSE_b + ½·media(e_a·e_b), verificada numéricamente.
- **Zonas:** E_JK es el mejor tanto en Chignahuapan (0.5664 / 0.5642) como en el resto (0.3483 / 0.3486). En Calpulalpan (30 parcelas), MUN y J siguen siendo mejores que E_JK. Cuautepec (5) y Emiliano Zapata (3) son muestras pequeñas y no se interpretan.
- **Concentración** (orden declarado; retiro solo de la evaluación):

| Mezcla frente a referencia | Sin retirar | Sin 2 más favorecidas | Sin 5 más favorecidas |
|---|---|---|---|
| E_JK vs K, históricas | −0.0063 | −0.0035 | −0.0008 |
| E_JK vs K, nuevas | −0.0066 | −0.0037 | −0.0006 |
| E_JK vs MIX, históricas | −0.0115 | −0.0082 | −0.0044 |
| E_JK vs MIX, nuevas | −0.0113 | −0.0083 | −0.0047 |
| E_MK vs K | +0.0004 / +0.0001 | +0.0042 / +0.0041 | +0.0076 / +0.0075 |

## Lectura según el criterio registrado

- **E_JK: clase C.** Supera a su mejor componente en ambos juegos, con ≥8/10 repeticiones frente a J y frente a K, y sin invertirse al retirar 2 parcelas. Frente a K, la ventaja se reduce a casi nada al retirar 5.
- **E_MK: clase A.** No supera a K.
- **El control dice:** reducir el peso de la interpolación espacial (E_MK) **no** reproduce la ganancia. E_JK supera a E_MK en ambos juegos y en 10/10 repeticiones, así que se cumple la condición registrada para hablar de un aporte de J sobre el control. Lo describimos como **complementariedad predictiva observada** entre una corrección regional (J) y una local (K). No es causalidad agronómica ni generalización demostrada.

## Decisión que permite y que no permite

- **Permite:** conservar E_JK como **candidato para revisión** del equipo.
- **No permite:**
  - Sustituir MIX automáticamente ni cambiar las reglas de adopción de EXP_10, que se mantienen separadas.
  - Afirmar significancia: no se ejecutó un nulo para la mezcla.
  - Olvidar la selección exploratoria de K1 (EXP_08) ni el origen posterior de esta hipótesis.
  - Generar las 59 predicciones. Antes haría falta revisar el soporte de J y K en las ocultas, incluido Nanacamilpa.
- **No se buscó ninguna variante después del resultado.** Otros pesos, stacking, gating y mezclas regionales serían continuaciones con protocolo propio; no se ejecutaron. La ablación sin territorio es otra pregunta.

## Presupuesto consumido

| Concepto | Cantidad |
|---|---|
| Fórmulas evaluadas | 2 |
| Entrenamientos de candidatos | 0 |
| Búsqueda de pesos / variables nuevas / reglas por municipio / predicciones de las 59 | 0 |
| Predicciones mezcla calculadas | 5,520 por corrida (2 fórmulas × 2,760 filas OOF) |
| Ajustes solo de verificación de J, en la preparación y antes del registro | 200 (100 pliegues × normal + etiquetas de validación sustituidas) |
| Réplica de determinismo | 1 (11 archivos científicos idénticos) |
| Lecturas del notebook | 2 kernels limpios locales, 0 ajustes. **Colab real no probado.** |

## Verificaciones

- **Insumos** (`data/exp_11_combinacion_modelos/verificacion_insumos.json`):
  - Claves únicas y alineadas; etiquetas, municipio y máscara iguales; filas iguales a las particiones originales.
  - MIX/MUN/K frente a EXP_10 con diferencia ≤ 9e-16, por redondeo al leer el CSV; las métricas coinciden con EXP_10 a ≤ 1e-16.
  - J reproducido de forma independiente desde las variables sin estandarizar (1.3e-13) e invariante a las etiquetas de validación.
  - Los archivos de Jared son idénticos a su ZIP.
- **Resultados** (`verificacion_independiente.json`): métricas recalculadas sin pandas (≤ 5.6e-17); réplica idéntica; registro previo anterior a la corrida; ni los archivos registrados ni los 58 originales (carpeta temporal y EXP_10) cambiaron.
- **Pruebas:** `tests/test_combinacion_11.py`, 13 pruebas (alineación, rechazo de defectos, etiquetas y máscaras, fórmulas, intervalo, orden de concentración, clasificación, reproducción de métricas de referencia e implementación independiente de las métricas de las mezclas).
