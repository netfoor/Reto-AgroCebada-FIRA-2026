# Plan de la Fase 1 — Limpieza, validación interna y líneas base

**Estado: APROBADO y EJECUTADO (2026-09-20).** Aprobado por el usuario: V1 principal, V2 prueba de esfuerzo, V3 para la
Fase 4; 5 grupos de trabajo (conteos corroborados: 71 / 31 / 16 / 10 / 10); entrega el **19 de octubre**; hojas de
agronomía en `preparacion/agronomia/`. Los resultados y las correcciones al plan están en la sección final
"Resultados de la ejecución". El texto de abajo es el plan original, sin cambios.
Semana 1 (21–27 sep). Todo en R, con solo los paquetes ya instalados. Fuentes: `outputs/prep_equipo/04_plan_de_trabajo.md`
(Fase 1), `outputs/eda/resumen_general.md` y las cifras verificadas abajo.

## Qué se quiere lograr, en una frase

Saber **cuánto error queda por explicar dentro de cada región** antes de agregar cualquier variable, con un esquema
de validación que imite bien lo que pasará con las 59 parcelas ocultas.

## Fase 0 — Verificación de herramientas (hecha)

| Qué | Verificado |
|---|---|
| R | 4.5.2, `Rscript.exe` en `C:\Program Files\R\R-4.5.2\bin\` (fuera del PATH) |
| Paquetes disponibles para la Fase 1 | `readr`, `dplyr`, `tidyr`, `sf` 1.1.3, `terra`, `ggplot2`, `broom` (ya instalados) |
| Reparar geometrías | `sf::st_make_valid(x, ...)` y `sf::st_is_valid(x, ...)` existen; en `parcelas_validadas.gpkg` las inválidas son AGC_070 y AGC_078 |
| Semillas | `set.seed(seed)` con Mersenne-Twister / Inversion / Rejection (se registra en el log) |
| Datos originales | `DataSet/DATASET_RETO_AGRO_2026/` (CSV, zips y `descomprimidos/`), solo lectura |
| **No instalados** (no hacen falta hoy) | `glmnet`, `ranger`, `xgboost`, `lightgbm`, `rsample`, `tidymodels`, `caret`, `blockCV`, `spatialsample`, `patchwork`, `leaflet`, `quarto`, `MatchIt` |

**Antipatrones a evitar:** inventar funciones o argumentos; usar paquetes de la lista "no instalados" sin tu
aprobación; escribir fuera de `preparacion/`; tocar `DataSet/` u `outputs/`; usar el rendimiento de las 59 ocultas
(no existe) o mirar sus etiquetas para elegir esquema de validación.

## Hallazgos nuevos que definen el esquema de validación (calculados solo leyendo `derivados/`)

1. Las 59 parcelas ocultas **no son ajenas** a las de entrenamiento: **49 de 59 (83%)** comparten celda climática con
   al menos una parcela de entrenamiento; 10 (17%) están en celdas donde no hay ninguna. (La "celda" se aproximó por
   valores climáticos idénticos; se confirmará con las coordenadas del raster.)
2. Si en las 138 hago una división 70/30 estratificada por región y aleatoria dentro de cada una (≈98 ajuste y 40
   validación), **el 78% de la validación comparte celda con el ajuste**, casi igual al 83% real. Es una buena imitación
   de lo que pasará con las 59.
3. Una validación que aparte celdas completas deja 0% de parcelas con vecino, es decir, es **más difícil que la
   realidad**. Sirve como prueba de esfuerzo, no como estimación del error esperado.
4. Los grupos de trabajo (municipio agrupado) en las 138:

   | Grupo | Parcelas | Celdas climáticas | Máx. parcelas en una celda |
   |---|---|---|---|
   | Chignahuapan (Puebla) | 71 | 11 | **33** |
   | Tlaxcala (todo el Estado) | 31 | 15 | 11 |
   | Singuilucan (Hidalgo) | 16 | 7 | 6 |
   | Almoloya (Hidalgo) | 10 | 7 | 3 |
   | Otros Hidalgo (Cuautepec 5, E. Zapata 3, Apan 1, Tepeapulco 1) | 10 | 7 | 3 |

   Nanacamilpa (1 parcela) se junta con Calpulalpan en "Tlaxcala". Una sola celda contiene 33 parcelas de
   Chignahuapan (24% del entrenamiento): apartar esa celda entera destruye cualquier validación.

   > **Nota posterior a la ejecución:** las columnas de celdas y el "33" de esta tabla vienen de la aproximación por
   > valores climáticos idénticos y **quedaron superadas**. Con las celdas reales del raster los grupos ocupan 4
   > (Chignahuapan), 7 (Tlaxcala), 4 (Singuilucan), 5 (Almoloya) y 7 (Otros Hidalgo) celdas, con máximos de 34, 15, 7, 5
   > y 3 parcelas por celda. Ver "Celdas climáticas (corrección al plan)" en la sección final.

## Decisión que necesito de ti (afecta el diseño)

La regla 2 del mensaje dice "validación agrupada por zona, nunca CV aleatoria". Tu petición nueva (tratar el 70%
conocido como el 100%) es, en esencia, una división aleatoria dentro de cada región. **No se contradicen si se
hace en tres niveles**, pero hay que decidirlo:

| Nivel | Qué es | Para qué sirve |
|---|---|---|
| **V1 — Espejo del reto** | 100 divisiones 70/30 de las 138, estratificadas por grupo, aleatorias dentro | **Estimación principal del error esperado en las 59.** Es la que mejor imita cómo se hizo la separación real |
| **V2 — Por celda climática** | 100 divisiones que apartan celdas completas (~30% de las parcelas), sin dejar ningún grupo sin representar | Prueba de esfuerzo: ¿el modelo aprende algo de la parcela o solo memoriza la zona? Da el peor caso razonable |
| **V3 — Dejar un grupo fuera** | 5 pruebas fijas: quitar Chignahuapan, Tlaxcala, Singuilucan, Almoloya, Otros Hidalgo | Fase 4: ¿sobrevive el modelo en una región que nunca vio? |

**Mi recomendación:** reportar V1 y V2 **juntas**; el error real esperado debería quedar entre las dos, más cerca de V1.
Reinterpretar la regla 2 como "nunca usar una CV aleatoria *como única evidencia*". Si prefieres mantener la regla
tal cual, V2 pasa a ser la métrica principal y V1 solo la de referencia.

## Fase 1.1 — Carpeta y registro

Crear en `preparacion/`: `scripts/`, `datos/` (productos limpios), `resultados/` y `registro_experimentos.csv`
(columnas: id, fecha, hipótesis escrita antes, variables, esquema, semillas, resultado, decisión).
**Verificación:** el registro existe y la hipótesis de cada experimento está fechada antes de ejecutarlo.

## Fase 1.2 — Limpieza (`scripts/10_limpieza.R`)

1. **Cultivo:** normalizar "Cebada"/"CEBADA" a una sola forma (mayúsculas). Verificar: 197 filas, un solo valor.
2. **Geometrías:** leer el shapefile original desde `DataSet/.../descomprimidos/` (solo lectura), aplicar
   `st_make_valid()` y guardar `preparacion/datos/parcelas_limpias.gpkg`. Verificar: `st_is_valid()` todo TRUE,
   197 polígonos, área recalculada de AGC_070 y AGC_078 sin cambios apreciables.
3. **LAI negativo:** no se modifica ninguna columna original. Se cuenta cuántas observaciones lo tienen (Básico
   y PRO) y se define la regla que aplicará la Fase 2 (propuesta: crear `lai_recortado = max(lai, 0)` y una bandera
   `lai_negativo`). En la Fase 1 no se usa LAI; solo se documenta.
4. **Área:** conservar `AREA_HA` (atributo) y `area_calculada_ha`; la decisión de cuál es oficial queda para los
   organizadores y no bloquea esta fase.

## Fase 1.3 — Tabla base y folds (`scripts/20_folds.R`)

1. Tabla `datos/base_138.csv`: `ID_POLIGONO`, `Estado`, `Municipio`, `grupo`, `celda_clima`, `RENDIMIENTO_T_HA`.
   `celda_clima` se obtiene con las coordenadas de cada parcela sobre el raster de lluvia de `descomprimidos/`
   (`terra`, solo lectura), no por coincidencia de valores.
2. **V1:** 100 repeticiones, semillas 1 a 100, 30% de cada grupo a validación (40 parcelas). Guardar en
   `datos/folds_V1.csv` (repetición, ID, rol).
3. **V2:** 100 repeticiones, semillas 1001 a 1100, apartar celdas completas hasta cubrir ≈30% de las parcelas, con
   la regla de que ningún grupo quede sin parcelas en el ajuste. Guardar en `datos/folds_V2.csv`. La celda de 33
   parcelas de Chignahuapan se trata como una sola unidad y se reporta cuántas repeticiones la apartan.
4. **V3:** 5 folds deterministas (sin azar) por grupo.
5. Reportar por esquema: tamaño real de validación, y qué % de la validación comparte celda con el ajuste
   (objetivo de V1: cerca del 83%; V2: 0%).

**Verificación:** ningún ID en ajuste y validación a la vez, todos los grupos presentes en cada ajuste (salvo V3 por
diseño), y correr el script dos veces produce archivos idénticos (mismo hash).

## Fase 1.4 — Líneas base (`scripts/30_lineas_base.R`)

| Modelo | Definición |
|---|---|
| B0 | media del rendimiento del conjunto de ajuste |
| B1 | promedio por Estado (regresión lineal solo con Estado) |
| B2 | promedio por grupo (Estado + municipio agrupado) |

- **Métricas:** RMSE (principal, en t/ha), MAE y R² de validación (`1 − SSE / suma de cuadrados respecto a la
  media del ajuste`, para que B0 dé ≈ 0). Se reporta la media entre repeticiones con el rango (5º–95º percentil).
- **Dentro de cada región:** RMSE de B1 y B2 por grupo. Ese es el "error por explicar" que buscan las variables.
- En V3, B1 y B2 no se pueden calcular para el grupo que se deja fuera (no tienen ese nivel); solo B0, y B1 cuando
  el Estado sigue presente. Se documenta, no se rellena.
- **Salidas:** `resultados/lineas_base.csv` y una tabla resumen; una fila por experimento en el registro.

### Hipótesis (escritas antes de correr)

- **H1:** B1 baja el RMSE frente a B0 en ≈25–30% (R² del Estado en el EDA ≈ 0.50, sd del rendimiento 0.85 t/ha ⇒ RMSE
  esperado ≈ 0.60–0.65 vs ≈ 0.85–0.87).
- **H2:** B2 mejora un poco más que B1, solo por separar Singuilucan (3.08 t/ha) de Almoloya y Otros Hidalgo
  (≈4.5), que están en el mismo Estado.
- **H3:** Para las líneas base, V1 y V2 darán casi lo mismo, porque solo usan la etiqueta del grupo y no el clima ni
  el satélite. La diferencia entre V1 y V2 aparecerá en la Fase 2–3, con variables que sí dependen de la ubicación.
- **H4:** el error de B2 será mayor en Chignahuapan que en Tlaxcala, si la variación interna es mayor donde hay más
  manejos distintos (a contrastar con las sd por Estado del EDA: Puebla 0.58, Hidalgo 0.78, Tlaxcala 0.38; no
  es una predicción firme).

## Verificación final de la fase

- Tabla de lo generado y dónde vive cada archivo; nada nuevo fuera de `preparacion/`.
- Los originales de `DataSet/` y `outputs/` no cambian (fecha de modificación y tamaño antes y después).
- Los tres esquemas se reproducen desde cero con `Rscript` y dan el mismo resultado.
- Se responde a la pregunta: **¿cuánto error queda dentro de cada región con la mejor línea base?**

## Fuera de esta fase (para no mezclar)

Agronomía (1A), teoría de teledetección y validación (1B), variables (Fase 2) y modelos (Fase 3).
Para la Fase 3 harán falta `glmnet` y `ranger`, y probablemente `rsample`; los pediré con aprobación cuando llegue.

---

## Resultados de la ejecución (2026-09-20)

Todo se corrió en R con los paquetes ya instalados (sin instalar nada) y solo se escribió dentro de `preparacion/`.
Cada script se ejecutó dos veces y los archivos de salida quedaron **idénticos** (mismos hashes MD5 en los CSV y en la
figura). Excepción: `datos/parcelas_limpias.gpkg` cambia de hash en cada corrida por una marca de tiempo interna del
formato GeoPackage; sus atributos y geometrías sí son idénticos (comprobado). Los originales de `DataSet/` y
`outputs/` no cambiaron (mismo tamaño y fecha en los 239 archivos revisados, antes y después).

Una segunda persona (subagente independiente) recalculó las líneas base con código propio (diferencia máxima 3e-14),
las celdas del raster, el LAI negativo y las propiedades de los folds, y confirmó todas las cifras de abajo.

### Qué se generó

| Archivo | Contenido |
|---|---|
| `scripts/10_limpieza.R` | Cultivo normalizado, 2 geometrías reparadas, conteo de LAI negativo |
| `scripts/20_folds.R` | Grupos, celdas climáticas reales, folds V1/V2/V3 |
| `scripts/25_registro_hipotesis.R`, `35_registro_resultados.R` | Hipótesis escritas antes de correr y resultados después |
| `scripts/30_lineas_base.R` | Líneas base B0/B1/B2, métricas y figura |
| `datos/` | `parcelas_limpias.gpkg`, `base_138.csv`, `base_197_ubicacion.csv`, `folds_V1/V2/V3.csv` |
| `resultados/` | `lineas_base.csv` (detalle), `lineas_base_resumen.csv`, `rmse_por_grupo.csv`, `mejora_vs_B0.csv`, `resumen_esquemas.csv`, `lai_negativo_conteo.csv`, `fig_lineas_base_rmse.png`, `logs/` |
| `registro_experimentos.csv` | H1–H4 con fecha de escritura, resultado y decisión |

### Limpieza

- **Cultivo:** 50 "Cebada" y 147 "CEBADA" pasaron a un solo valor (197 = "CEBADA").
- **Geometrías:** AGC_070 y AGC_078 eran las dos inválidas; tras `st_make_valid()` las 197 son válidas. El área
  recalculada cambió 0.00015 ha (AGC_070) y −0.00004 ha (AGC_078), o sea, nada. Se reparó **solo lo inválido**: aplicar
  `st_make_valid()` a las 197 movía hasta 0.0003 ha en polígonos que ya eran válidos. La coordenada Z (siempre 0) se descartó.
- **LAI negativo (cifra mayor de lo que decía el EDA):** en Básico, **18,916 de 44,877 lecturas con LAI (42.2%) son
  negativas**, en las 197 parcelas, con mínimo −0.192. En PRO solo 1 de 35,747 (mínimo −0.112). No se modificó nada;
  la regla propuesta (columnas nuevas `lai_recortado` y `lai_negativo`) queda para la Fase 2. Con esta magnitud, vale la
  pena preguntar a los organizadores si el LAI de Básico es utilizable.

### Celdas climáticas (corrección al plan)

Con las celdas reales del raster (por centroide de la parcela) en lugar de la aproximación por valores idénticos:

| | Plan (aproximación) | Real |
|---|---|---|
| Celdas distintas en las 197 parcelas | 53 | **25** (31 parcelas tocan más de una; se usa la del centroide) |
| Ocultas con vecino de celda en el entrenamiento | 49 de 59 (83%) | **57 de 59 (97%)** |
| V1 (70/30 interno): validación con vecino en el ajuste | 78% | **92%** (rango 83–100%) |
| V2 (celdas completas) | 0% | 0% |

La conclusión no cambia y se refuerza: **V1 imita bien lo que pasará con las 59** (92% vs 97%), y V2 es una prueba
más dura que la realidad. Además, en el entrenamiento hay **dos celdas de 34 parcelas cada una** (una con 34 de
Chignahuapan y otra con 33 de Chignahuapan y 1 de Otros Hidalgo), es decir, **68 de las 138 parcelas (49%) están en
solo dos celdas**. V2 aparta la primera en 23 de 100 repeticiones y la segunda en 25. Otros detalles: V1 deja **41**
parcelas en validación (no 40); V2 deja entre 35 y 48 (media 39.6); 71 de las 100 repeticiones de V2 salieron al
primer intento y el máximo de reintentos fue 6.

Dos detalles de V2 que no estaban en el plan original (los reveló la verificación):
- **Regla adicional del algoritmo:** ningún grupo puede tener más del 50% de sus parcelas en validación (además de no
  quedar sin parcelas en el ajuste). Está en `20_folds.R` (líneas 179–204) y el máximo observado es justo 50%.
- **Menos particiones distintas de lo que parece:** de las 100 repeticiones de V2 solo hay **84 particiones de
  validación distintas** (8 se repiten 2 veces y 4 se repiten 3 veces), porque hay pocas formas de apartar celdas
  completas. Los rangos 5–95% y los promedios por grupo de V2 pesan menos que si fueran 100 particiones independientes;
  además, el 29% de las repeticiones usó semillas de reintento fuera de 1001–1100 (2000+, 3000+…), registradas en el log.

### Líneas base (RMSE, t/ha; media de 100 repeticiones y rango 5%–95%)

| Esquema | B0 (media global) | B1 (solo Estado) | B2 (Estado + municipio agrupado) |
|---|---|---|---|
| **V1 — espejo del reto** | 0.843 (0.746–0.946) | 0.588 (0.467–0.713) | **0.502 (0.386–0.626)** |
| V2 — por celda | 0.921 (0.758–1.019) | 0.619 (0.525–0.691) | 0.524 (0.397–0.626) |

| Esquema | Métrica | B0 | B1 | B2 |
|---|---|---|---|---|
| V1 | MAE (t/ha) | 0.746 | 0.438 | 0.354 |
| V1 | R² de validación | 0 (por construcción) | 0.512 (0.370–0.636) | 0.641 (0.497–0.761) |
| V2 | MAE (t/ha) | 0.807 | 0.474 | 0.379 |
| V2 | R² de validación | 0 (por construcción) | 0.534 (0.309–0.677) | 0.655 (0.382–0.814) |

**Error que queda dentro de cada región (RMSE de B2 en V1):** Otros Hidalgo 0.68, Chignahuapan 0.55, Singuilucan 0.43,
Tlaxcala 0.38, Almoloya 0.18. Referencia: la desviación interna del rendimiento en Chignahuapan es 0.58, casi igual al
error de B2 (0.55): **ahí el promedio regional no explica nada más y es donde las variables tienen que trabajar**
(71 parcelas, 51% del entrenamiento). Ese es el objetivo real de la Fase 2.

**V3 (un grupo fuera, RMSE):** con B0 el error va de 0.63 a 1.31 según el grupo. B1 solo se puede calcular en los tres
grupos de Hidalgo y ahí **empeora** frente a B0 (0.77–1.30): predecir un municipio de Hidalgo con los otros dos es peor
que usar la media global. B2 no se puede calcular en V3 por construcción (el grupo que se deja fuera no está en el
ajuste); se deja NA, no se rellena. Detalle en `resultados/lineas_base.csv` y en el log.

### Contraste con las hipótesis (escritas antes de correr; ver `registro_experimentos.csv`)

| | Hipótesis | Resultado | Veredicto |
|---|---|---|---|
| H1 | B1 baja el RMSE ~25–30% vs B0 | 30.4% en V1 y 32.2% en V2; RMSE de B1 0.588, por debajo del 0.60–0.65 previsto | **Cumplida**, algo mejor de lo previsto |
| H2 | B2 mejora "un poco" a B1 | 14.8% en V1 (rango 2.7–23.9) y 15.5% en V2 (rango −1.9–28.4) | **Cumplida en dirección, no en magnitud**: es más que "un poco"; en V2 hay repeticiones donde no mejora |
| H3 | V1 ≈ V2 para las líneas base | B1: 0.588 vs 0.619; B2: 0.502 vs 0.524 (diferencias pequeñas frente al rango). B0: 0.843 vs 0.921 | **Cumplida para B1 y B2, no para B0**. Explicación probable, no comprobada a fondo: al apartar celdas de 34 parcelas, la media del ajuste se desplaza |
| H4 | Error de B2 mayor en Chignahuapan que en Tlaxcala | V1: 0.550 vs 0.380; V2: 0.484 vs 0.352 | **Cumplida** |

### Pendientes y advertencias

- El intervalo 5%–95% mide la variación entre divisiones repetidas de **las mismas 138 parcelas**; no es un intervalo de
  confianza para las 59 ocultas (las 100 repeticiones no son independientes entre sí).
- Las líneas base usan solo la etiqueta de región; el error de V1 y V2 no distinguirá tanto entre esquemas hasta que
  entren variables que dependan de la ubicación (Fase 2).
- **Ruido en los grupos pequeños:** el RMSE por grupo de Almoloya, Otros Hidalgo y Singuilucan sale de 3–5 parcelas de
  validación por repetición; cifras como el 0.18 de Almoloya son muy ruidosas. En V2 esas cifras usan 83–93
  repeticiones (columna `reps_con_datos`), no 100.
- **Premisa de H2 imprecisa:** se escribió que Almoloya y Otros Hidalgo rondan 4.5 t/ha; en realidad Almoloya es 4.52 y
  Otros Hidalgo 4.09. Por eso B2 casi no mejora en Otros Hidalgo. No cambia el veredicto, pero queda anotado.
- La celda climática se asigna por el centroide; 31 parcelas cruzan más de una celda. No es un problema para las líneas
  base (no usan clima), pero conviene recordarlo al construir variables climáticas.
- Aún sin hacer (fuera de esta fase): agronomía (1A), teoría de teledetección y validación (1B), variables (Fase 2).
