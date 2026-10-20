# 03_hipotesis_y_variables: qué probamos, con qué regla y qué salió

Esta carpeta explica cómo se construyeron 148 variables candidatas, cómo se decidió si una variable sirve (regla E1) y cómo se comprobó que los aciertos no fueran casualidad (control de permutación).

## La idea en una frase

Cada variable entra con una hipótesis escrita antes de probarla, y solo se acepta si mejora de forma clara a la línea base B2 (el promedio por grupo) en la validación.

## Contenido

| Archivo o carpeta | Qué contiene |
|---|---|
| `registro_experimentos.csv` | Copia del registro de experimentos: cada hipótesis con su fecha de escritura, la variable, el esquema, las semillas, el resultado y la decisión |
| `variables/` | Las 148 variables (`*_features.csv`, una fila por parcela), su diccionario, sus hipótesis y notas de cada familia |
| `scripts/` | Los scripts 51 a 55 (construyen las variables) y 60 (las evalúa) |
| `agronomia/` | Las cinco hojas de investigación agronómica (A a E), en `.md` y `.docx`, de donde salieron las hipótesis, y el script 40 que calcula las cifras de la hoja E |
| `contexto_previo/` | La síntesis para el equipo, las ideas de variables y de efecto causal, el plan de trabajo y los borradores del proyecto |
| `scripts_historicos_registro/` | Los scripts que escribieron las filas del registro. Son solo constancia: **no se corren** |

## Paso 0. La investigación agronómica (carpeta `agronomia/`)

Antes de proponer variables se investigó cómo crece la cebada maltera y qué le hace daño en los Valles Altos. Son cinco hojas, cada una con su versión `.md` y su `.docx`:

| Hoja | Qué contiene |
|---|---|
| `A_fenologia` | Las etapas del cultivo (escala Zadoks), su duración en Valles Altos, qué define el rendimiento y las hipótesis medibles con nuestros datos |
| `B_estreses` | Los cuatro estreses climáticos (por ejemplo la helada temprana de otoño), cómo se verían en nuestros datos, sus límites y las hipótesis medibles |
| `C_sanidad_manejo` | Enfermedades y plagas en Valles Altos, manejo recomendado por estado, calidad maltera y las hipótesis medibles |
| `D_contexto_regional` | El marco por estado, nuestros datos frente a los promedios oficiales, por qué Singuilucan es distinto y el problema de las celdas en Chignahuapan |
| `E_teledeteccion_validacion` | Qué mide cada índice satelital y dónde falla, validación agrupada y fuga de información, y qué aportan y qué no aportan las fuentes |

Cada hoja termina con preguntas de repaso y con la lista de fuentes y su estado. Las hojas A, B, C y E traen además "Lo que no debemos afirmar todavía". Las hipótesis medibles de las hojas A a D están en el registro de experimentos (prefijos HA, HB, HC y HD).

Cada afirmación lleva una marca: **[V]** verificado con fuente leída, **[V-parcial]** visto solo en un resumen o en un documento de otro cultivo o país, **[PV]** por verificar, y **[CP]** cálculo propio. Lo marcado [V-parcial] o [PV] no debe tomarse como dato confirmado. Las hojas son copias textuales del original; no se editaron.

El script `scripts_R_origen/40_chequeos_1B.R` (en R) calcula las cifras [CP] de la hoja E. Se corre desde la carpeta FINAL con `Rscript 03_hipotesis_y_variables/scripts_R_origen/40_chequeos_1B.R` y escribe `04_resultados/1B_chequeos.csv` (sale idéntico al original). Solo cambiaron sus rutas.

### Otros documentos previos (carpeta `contexto_previo/`)

| Archivo | Qué es |
|---|---|
| `01_sintesis_para_equipo.md` | Resumen del EDA pensado para explicarse en voz alta (unos 15 a 20 minutos) |
| `02_ideas_feature_engineering.md` | Lista priorizada de variables por construir. Solo ideas, sin código |
| `03_ideas_efecto_causal.md` | Ideas sobre por qué la lluvia se correlaciona negativamente con el rendimiento. Ninguna opción se ejecutó |
| `04_plan_de_trabajo.md` | Plan de trabajo por fases que se discutió con el equipo |
| `Notas_comparacion_Reto_vs_EDA.docx` | Notas que comparan el planteamiento del reto con el EDA |
| `Borrador_consolidado_Reto_AgroCebada.docx` y `Borrador_para_el_equipo_Reto_AgroCebada.docx` | Borradores del 20 de septiembre de 2026 que juntan el contexto para el equipo |

Se copiaron sin cambios. Algunos de estos documentos son de antes de la regla E1, así que sus ideas son propuestas y no resultados.

### Scripts históricos del registro (carpeta `scripts_historicos_registro/`)

Los scripts 25 a 29, 35 y 61 fueron los que escribieron en el registro de experimentos las hipótesis y sus resultados. Son copias textuales con rutas del proyecto original, y por eso llevan una línea al inicio que dice "NO CORRER": si se corrieran, escribirían en el registro del proyecto original. El registro final completo está en `registro_experimentos.csv`, y no hace falta correr nada para reproducir los resultados.

## Paso 1. El registro de experimentos

Antes de probar algo se escribe en el registro qué se espera y por qué. Después se completa el resultado y la decisión. Así queda constancia de que las hipótesis no se ajustaron después de ver los datos. Hay filas de dos tipos: hipótesis (con prefijo H, por ejemplo HB8 o HN3) y notas de diseño (con prefijo E, por ejemplo E1 a E5), que no son hipótesis sino reglas o decisiones del método.

El registro indica con "[CP]" los cálculos propios y con "[PV]" los datos agronómicos por verificar.

## Paso 2. Construir las 148 variables (scripts 51 a 55)

Cada script construye una familia de variables sin leer el rendimiento. Ninguna variable tiene valores faltantes en las 138 parcelas.

Los scripts 51 a 55 siguen en R (`scripts_R_origen/`): construyen las variables desde las tablas de clima y satélite, y sus resultados ya están en `variables/`. No se pasaron a Python para no arriesgar cambiar cifras ya registradas.

| Script | Familia | Variables | Idea |
|---|---|---|---|
| `51_variables_clima_ventanas.R` | clima por ventanas (`clim_`) | 27 | Lluvia, Tmax y Tmin del ciclo 2025 por ventana de meses |
| `52_variables_clima_anomalias.R` | anomalías (`anom_`) | 17 | Qué tan atípico fue 2025 frente al promedio de 2022 a 2024 |
| `53_variables_sat_compuestos.R` | compuestos sin nubes (`satc_`) | 40 | NDVI, SAVI y MSAVI por mes, usando solo fechas con menos de 20% de nubes |
| `54_variables_sat_sensor.R` | por sensor (`sat_`) | 32 | Índices por ventana y por sensor, y el vigor típico de 2022 a 2024 |
| `55_variables_sat_indices17.R` | 17 índices adicionales (`sat_`) | 32 | Agua, residuos, labranza y variabilidad dentro de la parcela |

Las ventanas del ciclo 2025 son: `a` abril y mayo, `b` junio y julio, `c` agosto y septiembre, `d` octubre y `ciclo` abril a octubre. Se fijaron así porque no hay fecha de siembra por parcela.

### Aviso sobre las ponderaciones entre familias (no se unificó)

Las familias no promedian igual los datos satelitales, y se documenta tal como está:

* La familia 53 calcula primero una mediana por mes y luego promedia los meses de la ventana. Cada mes pesa lo mismo, tenga una imagen o muchas.
* Las familias 54 y 55 promedian directamente las observaciones válidas de la ventana. Un mes con más imágenes pesa más.

Esto no se corrigió. Según el estado del proyecto, no cambia las conclusiones, porque la familia 54 no pasa la regla E1.

## Paso 3. La regla E1

La regla se escribió y se registró antes de probar las variables. Una variable se considera útil si, sobre las mismas 100 particiones V1 (ver carpeta 02):

1. **(a)** baja el RMSE de B2 en más de 0.02 t/ha en promedio, comparando partición por partición, y
2. **(b)** mejora en al menos 75 de las 100 particiones, y
3. **(c)** en V2 la mejora promedio no es negativa.

Qué pasa si falla: si falla (a) o (b), se descarta. Si falla solo (c), se reporta como dependiente de vecinos, porque funciona cuando hay parcelas de la misma celda en el ajuste pero no cuando faltan.

Cómo se prueba cada variable (script 60): se ajusta `rendimiento ~ grupo + variable` solo con las parcelas de ajuste de cada partición y se mide el error en las de validación. Eso se compara con B2 en las mismas parcelas. Si a una parcela de validación le falta la variable, se predice con B2 y no se imputa.

## Paso 4. El control de permutación

Con 148 variables probadas, alguna podría pasar solo por azar. El control estima cuántas pasan sin que haya señal real. Se baraja el rendimiento a propósito, de modo que no exista relación con las variables, se repite la prueba completa 100 veces y se cuenta cuántas variables pasan E1.

Se hicieron dos versiones, y la segunda se agregó después de ver la primera (queda anotado en la fila E3 del registro):

| Control | Qué baraja | Variables que pasan E1 por azar (promedio) | Máximo en 100 repeticiones | Reales |
|---|---|---|---|---|
| Por grupo (semilla 2026) | El rendimiento dentro de cada grupo | 0.08 | 5 | 13 (14 sin la condición c) |
| Estricto, por celda (semilla 2027) | Las filas de variables entre celdas del mismo grupo, conservando el parecido entre vecinas | 0.16 | 11 | 13 (14 sin la condición c) |

Cómo leerlo: por azar casi no pasa ninguna variable, y en lo real pasan 13. Pero el máximo por azar en el control estricto llega a 11, así que la distancia no es holgada.

## Paso 5. Elegir la variable dentro de cada partición

Elegir la variable mirando todas las 138 parcelas sería hacer trampa (fuga de información). Por eso el script 60 también prueba un procedimiento honesto: en cada partición elige la mejor variable según el ajuste, y evalúa en la validación. Resultados (diferencia contra B2, positiva significa mejora):

| Procedimiento | V1 | Particiones V1 donde mejora | V2 | Particiones V2 donde mejora |
|---|---|---|---|---|
| Mejor variable (`top1_global`) | +0.0287 | 86 de 100 | +0.0558 | 94 de 100 |
| Mejores 3 variables (`top3_global`) | +0.0289 | 85 de 100 | +0.0611 | 99 de 100 |

Con el rendimiento barajado, esa misma selección empeora a B2: -0.0184 en V1 y -0.0347 en V2 (control por grupo), y -0.0166 y -0.0739 con el control estricto. Es una señal de que el procedimiento no inventa mejoras.

## Qué salió

Se hicieron 150 pruebas (148 variables lineales y 2 curvas). La hipótesis HC2 no se pudo evaluar, porque su indicador vale 1 en las 197 parcelas.

* **Pasan E1: 13 variables.** Casi todas de clima: 9 anomalías de 2025 contra 2022 a 2024, el rango térmico de septiembre y 3 de NDVI y SAVI de Sentinel-2 de abril y mayo.
* **Pasa solo con vecinas: 1** (la Tmin de abril y mayo).
* **Descartadas: 136.**
* Las variables de vigor satelital de las hipótesis principales (NDVI, EVI, SAVI, MSAVI, LAI, índices de agua, los 17 índices nuevos y la variabilidad dentro de la parcela) no mejoran a B2.
* Solo 2 de las 13 coinciden con el signo registrado de antemano (la anomalía de Tmin de septiembre y octubre, y el rango térmico de septiembre). Tres contradicen el signo registrado, y las demás no tenían signo declarado, así que son hallazgos exploratorios y no confirmaciones.

La lista de las 13 variables con sus cifras está en `04_resultados/variables_que_pasan_E1.csv`.

## Advertencias que no hay que olvidar

* **Las 13 variables son pocas señales repetidas.** En el entrenamiento solo hay 23 celdas climáticas. Las anomalías climáticas explican entre 98.9% y casi 100% de su variación con la celda, es decir que son casi etiquetas de celda. Muchas de las 13 son prácticamente la misma información.
* Las 100 particiones no son independientes entre sí, porque salen de las mismas 138 parcelas.
* El rendimiento es de una sola temporada (2025) y 2025 fue el año más lluvioso de la serie. No se puede aprender el efecto de un año atípico con un solo año.
* Las 13 variables se presentan como candidatas, no como causas.

## Cómo repetirlo

Desde la carpeta FINAL (después de los scripts 10, 20 y 30 de la carpeta 02):

```
python 03_hipotesis_y_variables/scripts/60_evaluacion_variables.py
python 03_hipotesis_y_variables/scripts/70_candidatos_E6.py
```

El 60 aplica E1 a las 148 variables. El 70 prueba los candidatos de la fila E6 (ver más abajo). Las variables (scripts 51 a 55) ya vienen hechas en `variables/`; para rehacerlas: `Rscript 03_hipotesis_y_variables/scripts_R_origen/51_variables_clima_ventanas.R` y así hasta el 55 (desde la carpeta FINAL).

El script 60 tarda unos minutos (los controles de permutación son lo más lento). Las semillas están fijas, así que se repite el mismo resultado.

**Python contra R.** Las 150 pruebas coinciden con las de R (diferencia máxima 0, ningún veredicto distinto) y la selección dentro de partición también. La única diferencia son los **controles de permutación**: Python y R generan números al azar distintos aunque la semilla sea la misma, así que esos números cambian un poco. Control por grupo: pasan por azar en promedio 0.33 variables (máximo 18) en Python contra 0.08 (máximo 5) en R. Control estricto por celda: 0.53 (máximo 11) en Python contra 0.16 (máximo 11) en R. En lo real pasan 13. La conclusión es la misma, y conviene leer el máximo por azar del control por celda (11) como cercano a 13: la distancia no es holgada. Los datos reales y las particiones no cambian.

## Cambios en las copias de los scripts

Los scripts de R en `scripts_R_origen/` solo cambiaron en sus rutas, que ahora son relativas a la carpeta FINAL. Los scripts 25 a 29, 35 y 61, que escribieron en el registro de experimentos, se guardan en `scripts_historicos_registro/` sin cambios (con rutas del original y la marca de no correr). El registro final, hasta la fila E7, ya está incluido aquí.

## Candidatos nuevos (filas E6 y E7 del registro)

Antes de cerrar, se probó si algo más complejo superaba al modelo final provisional (`top1_global`). La regla de reemplazo se escribió en la fila E6 antes de correr nada: un candidato sustituye a `top1_global` solo si cumple E1 y además lo mejora en V1 por más de 0.01 t/ha y en al menos 75 de 100 particiones comparadas una a una, sin empeorar en V2. Resultado (script `scripts/70_candidatos_E6.py`, archivo `04_resultados/70_candidatos_resumen.csv`):

| Candidato | RMSE V1 | RMSE V2 | E1 | ¿Reemplaza? |
|---|---|---|---|---|
| top1_global (modelo actual) | 0.4734 | 0.4679 | pasa | (referencia) |
| C1: top1_global más residuo por celda climática | 0.4734 | 0.4679 | pasa | No (elige no ajustar la celda en 99 de 100 particiones) |
| C2: ridge con las 17 anomalías climáticas | 0.4739 | 0.4840 | pasa | No (peor en V2) |
| C3: ridge con las 148 variables | 0.4975 | 0.5055 | descartado | No |
| C5: árboles con 10 variables | 0.4916 | 0.5392 | descartado | No |

Ningún candidato supera al modelo final, que se mantiene. La fila E7 registra el resultado.
