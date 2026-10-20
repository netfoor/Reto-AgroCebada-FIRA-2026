# Diccionario de variables en lenguaje simple

Cómo leerlo: cada sección corresponde a un archivo. Las unidades van entre paréntesis. "Parcela" es un terreno de cultivo identificado como AGC_001 hasta AGC_197.

## Identificadores y datos del reto

| Columna | Qué significa |
|---|---|
| `ID_POLIGONO` | Código único de la parcela, de AGC_001 a AGC_197. Sirve para unir todas las tablas |
| `AREA_HA` | Área de la parcela (hectáreas) |
| `RENDIMIENTO_T_HA` | Rendimiento de cebada del ciclo abril a octubre de 2025 (toneladas por hectárea). Es lo que queremos predecir. Está vacío en las 59 parcelas ocultas |
| `CONJUNTO` | ENTRENAMIENTO (rendimiento conocido, 138 parcelas) o PREDICCION (rendimiento oculto, 59 parcelas) |

## base_138.csv y base_197_ubicacion.csv

| Columna | Qué significa |
|---|---|
| `Estado`, `Municipio` | Dónde está la parcela |
| `grupo` | Grupo de trabajo regional: Chignahuapan, Tlaxcala, Singuilucan, Almoloya u Otros_Hidalgo. Junta municipios pequeños para tener grupos con datos suficientes |
| `celda_clima` | Número de la celda climática (cuadro de cerca de 5.5 km) donde cae el centro de la parcela. Las parcelas de una misma celda reciben el mismo clima |
| `celda_proxy` | Aproximación antigua de la celda, hecha con valores climáticos iguales. Quedó superada por `celda_clima` y no se usa para decidir |

## Particiones de validación (folds)

| Columna | Qué significa |
|---|---|
| `rep` | Número de repetición de la partición (1 a 100 en V1 y V2, 1 a 5 en V3) |
| `rol` | `ajuste` (parcelas con las que se aprende) o `validacion` (parcelas que se esconden para medir el error) |
| `grupo_fuera` | Solo en V3: el grupo que se deja fuera en esa prueba |

## Datos satelitales originales

Un registro por parcela y fecha. Los índices vienen como `_promedio` (valor medio en la parcela), `_std` (qué tanto varía dentro de la parcela), `_max` y `_min`.

| Columna | Qué significa |
|---|---|
| `fecha_captura` | Fecha de la imagen (día/mes/año) |
| `sensor` | Satélite: Sentinel-2 y Landsat en el paquete Básico, Planet en el PRO |
| `porcentaje_nubosidad` | Qué parte de la escena estaba cubierta por nubes. Con 100% el índice falta, y no se imputa |
| NDVI, SAVI, MSAVI, EVI | Qué tan verde y vigorosa está la vegetación. SAVI y MSAVI corrigen el efecto del suelo |
| LAI, FAPAR | Cantidad de hojas y fracción de luz que la planta absorbe. El LAI del Básico tiene 42% de valores negativos, así que se usa con cuidado |
| NDWI, ENDWI, MSI, EMSI, NDDI, ENDDI, DSWI2 a DSWI5 | Índices de agua y estrés hídrico de la vegetación |
| CRC, MCRC, NDTI, STI, NDSVI | Índices de residuos de cultivo, labranza y vegetación seca |
| SRNDI, MRA, VI6T | Otros índices del proveedor. VI6T viene solo de Landsat |

Regla del proyecto: Básico y PRO nunca se mezclan por nombre, porque vienen de sensores distintos.

## Tablas derivadas

| Columna | Qué significa |
|---|---|
| `anio`, `mes` | Año y mes de la observación climática |
| `precip_mm` | Lluvia acumulada del mes (milímetros) |
| `tmax_c`, `tmin_c` | Promedio mensual de la temperatura máxima y mínima (grados Celsius) |
| `precip_acumulada_ciclo` | Lluvia de abril a octubre de 2025 (mm) |
| `tmax_medio_ciclo`, `tmin_medio_ciclo` | Temperatura promedio de abril a octubre de 2025 (grados Celsius) |
| `n_obs_s2`, `n_obs_pro` | Número de observaciones satelitales de la parcela |
| `area_calculada_ha`, `AREA_HA_SHP` | Área calculada con la geometría y área escrita en el shapefile (hectáreas) |

## Las 148 variables candidatas

Se construyeron sin mirar el rendimiento. Cada una está definida con detalle en `03_hipotesis_y_variables/variables/<familia>_diccionario.csv`. Aquí solo se explica cómo leer el nombre.

**Ventanas del ciclo 2025.** Como no hay fecha de siembra por parcela, se fijaron ventanas de meses: `a` es abril y mayo, `b` es junio y julio, `c` es agosto y septiembre, `d` u `oct` es octubre y `ciclo` es abril a octubre.

| Prefijo | Familia | Cuántas | Qué mide |
|---|---|---|---|
| `clim_` | clima por ventanas | 27 | Lluvia (`precip`), temperatura máxima (`tmax`) y mínima (`tmin`) por ventana o mes, más el rango térmico de septiembre y el mes más seco entre junio y septiembre |
| `anom_` | anomalías de clima | 17 | Qué tan distinto fue 2025 del promedio de 2022 a 2024 en la misma parcela y ventana. La lluvia va en porcentaje (`pct`) y la temperatura en grados |
| `satc_` | compuestos satelitales sin nubes | 40 | Valor mensual (`m04` a `m10`, abril a octubre) de NDVI, SAVI y MSAVI usando solo fechas con menos de 20% de nubes, más promedios por ventana y conteo de observaciones |
| `sat_` con `_s2`, `_planet` o `_landsat` | variables por sensor | 32 | Promedios de índices por ventana en cada sensor, y vigor típico de 2022 a 2024 |
| `sat_` con `_pre`, `_jul_sep` o `_ciclo` | 17 índices adicionales | 32 | Índices de agua, residuos, labranza y variabilidad dentro de la parcela (`std` y `cv`) |

Sufijos de sensor: `_s2` es Sentinel-2, `_planet` es Planet y `_landsat` es Landsat.

**Advertencia.** Las variables del mismo clima (la lluvia y la temperatura) valen casi lo mismo dentro de una celda de 5.5 km, y las anomalías son casi etiquetas de celda. Por eso no son 148 señales independientes.
