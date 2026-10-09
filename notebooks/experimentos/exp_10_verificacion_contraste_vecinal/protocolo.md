# EXP_10 · Protocolo: verificación y decisión sobre la señal vecinal

**Escrito el 8 de octubre de 2026 (CDMX), después de la factibilidad solo con X y antes de obtener cualquier score nuevo.** Los hashes de este archivo, del código y de los insumos se fijan en `registro_previo.json`.

## 1. Por qué existe EXP_10

EXP_08 (8 oct, propuesto por Claude a pedido de Fortino) encontró que MIX + una corrección lineal con el contraste vecinal de la integral NDVI Planet (C1) reducía el RMSE. EXP_09 (8 oct, mismo autor, con registro previo) fijó esa variable **cortada al 31 de octubre** como K1. K1 mejoró a MIX en las particiones históricas y en las nuevas, pero no cumplió el umbral de familia (p ≈ 0.13 > 0.10). Su regla recomendó **MIX**, y ese cierre se conserva.

Una revisión posterior encontró una **discrepancia material** en la implementación del corte. En `construir_exp_09.py` (y en la variante "hasta 31 oct" de EXP_08), `curva()` suaviza e interpola con capturas de todo el año y `integral()` recorta después al día 304. La mediana móvil centrada (±7 días) y la interpolación permiten que capturas de noviembre modifiquen valores de octubre.

**Reconocimiento explícito:** K1 se eligió después de explorar estas mismas 138 etiquetas (barrido de EXP_08, selección de descriptor y radio). Este registro fija la verificación hacia adelante; **no convierte la hipótesis en una confirmación independiente.**

## 2. Factibilidad solo con X (ya ejecutada, `scripts/factibilidad_10.py`)

| Comprobación | Resultado |
|---|---|
| Integrales que cambian al cortar antes de suavizar | 130/197 (|Δ| mediana 0.082, máx. 1.24 NDVI·día; la integral mediana ≈ 46) |
| Contrastes que cambian | 131/158; Spearman publicado–corregido 0.9985 |
| Cobertura | 197 integrales y 158 contrastes en ambas recetas: 108 etiquetadas y 50 ocultas |
| Contrastes con <2 vecinas finitas | 0. La regla publicada (≥2 vecinas geométricas, mediana que omite NaN) coincide con "≥2 vecinas finitas". **No se modifica la regla.** |
| Invariancia (cambiar, borrar o añadir capturas posteriores al corte) | Receta corregida: 0 integrales cambian en los tres escenarios. Receta publicada: 114, 130 y 131 cambian. |

## 3. Procedimientos comparados

| Código | Definición |
|---|---|
| MUN | Media municipal del entrenamiento; municipio no visto → media global (`validacion_03.predecir_referencias`) |
| MIX | 0.5·MUN + 0.5·IDW (k=20, potencia 2, piso 1 m), receta fija |
| K1_publicado | MIX + β·z con la integral de EXP_09 K1 (suavizado con todo el año, recorte después). **Control de reproducción.** |
| K1_corregido | Igual, pero las capturas posteriores al 31/10/2025 se descartan **antes** del suavizado y la rejilla se limita a los días 1–304. Todo lo demás se conserva: Planet, nubosidad ≤20 %, mediana diaria, mediana móvil de 15 días con mínimo 3, base días 91–150, umbral del 50 %, integral, radio 1 km, ≥2 vecinas y α = 10. |

**Corrección (ambos K1):** residuos e = y − MIX de cada parcela de entrenamiento, predicha con las particiones internas sin su etiqueta. z̃ = (z − mediana)/desviación (ddof=1), calculadas solo con las filas de entrenamiento con contraste. β = Σz̃e/(Σz̃² + 10). Validación sin contraste → corrección 0 (respaldo MIX). No se elimina ninguna parcela de la evaluación.

No se optimizan radio, α, ventana ni índice. No hay árboles ni otras fuentes.

## 4. Evaluación

- **Particiones:** históricas (`data/validacion_03`, 50 exteriores + 200 interiores) y nuevas de EXP_09 (`data/exp_09_fuentes_externas`, semilla 20261009). No se buscan otras semillas.
- **Población:** SEEN135 principal; FULL138 secundario. Métricas RMSE, MAE y R² agrupados sobre las mismas filas para todos los procedimientos.
- **Diferencias pareadas** frente a MIX y frente a K1_publicado: agrupadas y por repetición. También Chignahuapan/resto, municipios, concentración por parcela y sensibilidad retirando **solo de la evaluación** las 2 y las 5 parcelas más favorecidas frente a MIX.
- **Soporte de las 59:** disponibilidad y rango del contraste. Nanacamilpa (1 etiqueta) no tiene evaluación OOF equivalente.
- **Control de fuga:** las predicciones se recalculan con las etiquetas exteriores de validación sustituidas; deben ser idénticas.

## 5. Regla de desarrollo de EXP_10 (fijada antes de los scores)

**Requisitos predictivos (R), en SEEN135:**

- **R1.** RMSE agrupado < MIX en las particiones históricas **y** en las nuevas.
- **R2.** RMSE < MIX en ≥8/10 repeticiones de cada juego.
- **R3.** MAE agrupado ≤ MIX en cada juego.
- **R4.** En cada juego, al retirar de la evaluación las 2 parcelas más favorecidas frente a MIX, el RMSE del candidato sigue < MIX en las filas restantes.

Las 10 repeticiones reutilizan las mismas 138 parcelas: **no son diez pruebas independientes.**

**Evidencia estadística (S):** p ajustado por familia ≤ 0.10 en **N1 y N2** (sección 6), con p = (k + 1)/(N + 1). Se reporta también k/N para comparar con EXP_09.

**Mapa de decisión (provisional, para revisión del equipo):**

| R1–R4 | S | Recomendación |
|---|---|---|
| Alguna falla | — | Conservar MIX. K1 corregido se cierra sin adopción. |
| Todas se cumplen | No | Conservar MIX como referencia oficial. K1 corregido queda como alternativa documentada que **cumple requisitos predictivos de desarrollo sin evidencia estadística suficiente**; la decisión es del equipo. |
| Todas se cumplen | Sí | Considerar K1 corregido como candidato provisional para revisión del equipo. No es una confirmación independiente. |

## 6. Nulos (presupuesto fijo, una sola ejecución cada uno, sin repetir para cruzar umbrales)

La familia sigue siendo la de EXP_09: **seis candidatos** (K1, K2 NDRE, K3 radar, K4 AlphaEarth, K5 historia y K6 combinado). Estadístico: el menor RMSE SEEN de los seis (particiones históricas). K2–K5 se usan con su receta publicada de EXP_09: solo sirven para calibrar "el mejor de seis" y no se reportan como candidatos.

- **N0 · reproducción del nulo publicado.** Familia con K1_publicado, permutación de filas dentro de municipio, semilla 20261009, 200 permutaciones. Debe reproducir p ≈ 0.13. Es un control.
- **N1 · mismo esquema con K1_corregido.** Semilla 20261010, 200 permutaciones.
- **N2 · aleatorización espectral de Moran (MSR, variante *singleton*; Wagner y Dray, 2015).**
  - Sobre las parcelas con algún contraste, con la misma matriz de vecindad binaria (0 < d < 1 km), se descompone cada columna centrada en los vectores propios de la matriz doblemente centrada M W M (sin el vector constante).
  - Se invierten los signos de sus coeficientes con un vector común a todas las columnas. Esto conserva exactamente la varianza, el I de Moran y el espectro de autocorrelación de cada columna, sus productos cruzados y **la localización de los faltantes**.
  - Semilla 20261011, 200 sorteos.

**Qué contrasta cada nulo y su supuesto:**

- **N0/N1** contrastan "los contrastes no tienen relación con el rendimiento, y cualquier asignación dentro de municipio es igualmente probable". Ese intercambio **no está justificado**: los contrastes y los residuos tienen dependencia espacial fina (<1 km), y la permutación la destruye y mueve los faltantes. Por eso pueden ser **anticonservadores**.
- **N2** contrasta "los contrastes son un campo espacial con la misma autocorrelación, independiente del rendimiento". Supone que, bajo H0, la distribución del campo es invariante a cambiar el signo de sus coeficientes en la base de vectores propios. Es aproximadamente cierto para procesos gaussianos estacionarios cuya covarianza es diagonal en esa base. No conserva exactamente la forma de la distribución marginal.

Si N2 falla numéricamente o sus conservaciones no se verifican, S se declara **no evaluable** y se aplica la recomendación conservadora.

## 7. Presupuesto previsto (por corrida)

| Concepto | Cantidad |
|---|---|
| Evaluaciones de referencias exteriores (MUN+MIX) | 100 pliegues (2 juegos × 50) |
| Evaluaciones MIX internas para residuos | 400 |
| Ajustes de corrección (2 K1 × 100 pliegues) | 200 |
| Control de fuga | otras 100 + 400 + 200, contadas aparte |
| Permutaciones/sorteos | N0, N1 y N2: 200 cada uno × 6 candidatos × 50 pliegues = 60,000 ajustes de corrección cada uno |
| Réplica de determinismo | Repite todo lo anterior; se cuenta como réplica, no como candidato |
| Lectura del notebook | 0 ajustes |

## 8. Lo que EXP_10 no hace

No genera las 59 predicciones. No prueba otra variable, radio, ventana, índice, fuente ni familia de modelo. No corrige ni reevalúa K2/K3 como candidatos, aunque comparten la misma discrepancia temporal; se registra como limitación de EXP_09. No modifica los notebooks ni los cierres de EXP_08/09.

## Referencias

Wagner, H. H., & Dray, S. (2015). Generating spatially constrained null models for irregularly spaced data using Moran spectral randomization methods. *Methods in Ecology and Evolution, 6*(10), 1169–1178. https://doi.org/10.1111/2041-210X.12407
