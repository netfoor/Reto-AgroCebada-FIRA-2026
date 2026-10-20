# 01_datos: las bases que usamos

Esta carpeta guarda una copia de todas las bases que usa el proyecto, para que se pueda repetir el trabajo sin el resto de nuestros archivos. Nada de lo que está aquí se modifica a mano: lo que cambia lo escriben los scripts.

## Qué hay y de dónde viene

| Subcarpeta | Qué contiene | Quién la produce |
|---|---|---|
| `originales/` | Los datos que entregó el reto, sin tocar. Incluye `rasters_completos/` con los mapas mensuales de lluvia, temperatura y topografía | Organizadores del reto |
| `derivados/` | Tablas por parcela hechas a partir de los rasters y de los CSV satelitales (12 archivos) | Los scripts 01 a 08 del análisis exploratorio inicial, que están en `eda_inicial/scripts/` |
| `eda_inicial/` | El primer análisis exploratorio de los datos (reportes, figuras, logs y scripts 01 a 08) | Es el punto de partida del proyecto, hecho antes de las fases de validación y de variables |
| `preparados/` | Parcelas limpias, la tabla base de 138 parcelas y las particiones de validación | Scripts 10 y 20 de la carpeta `02_validacion_y_lineas_base` |

Las 148 variables candidatas no están aquí: viven en `03_hipotesis_y_variables/variables/`, porque las producen los scripts 51 a 55 de esa carpeta.

## Qué es cada archivo

### originales/

* `ID_area_rendimiento_70_30_Reto_AgroCebada.csv`: las 197 parcelas con su área y su rendimiento (t/ha). El rendimiento está visible en 138 parcelas (ENTRENAMIENTO) y oculto en 59 (PREDICCION). El archivo trae una quinta columna vacía por una coma sobrante, que los scripts descartan.
* `Conjunto_datos_BASICO_AgroCebada2026.csv`: observaciones de Sentinel-2 y Landsat de 2022 a 2025, una fila por parcela y fecha, con índices de vegetación y el porcentaje de nubosidad.
* `Conjunto_datos_PRO_AgroCebada.csv`: observaciones de Planet de 2025 (NDVI, EVI, LAI y MSAVI), con nubosidad.
* `parcelas/`: el shapefile con los polígonos de las 197 parcelas (cinco archivos que deben estar juntos).
* `precipitacion/PREC_2025_01.tif`: raster de lluvia (CHIRPS) de enero de 2025. Solo se usa como cuadrícula de referencia para saber en qué celda climática cae cada parcela (celdas de 0.05 grados, cerca de 5.5 km).
* `Descripcion_general_variables_DataSet.docx` y `Diccionario_de_indices_satelitales.docx`: los documentos del reto que describen los datos.

### derivados/

Son tablas con una fila por parcela (o por parcela y mes) que salieron de los rasters y de los CSV satelitales. Los scripts de variables las usan como entrada.

* `id_area_rendimiento_limpio.csv`: copia limpia del archivo de ID, área y rendimiento.
* `parcelas_atributos.csv`: cultivo, municipio, estado, conjunto y área calculada de cada parcela.
* `precipitacion_mensual_por_parcela.csv` y `temperatura_mensual_por_parcela.csv`: lluvia, Tmax y Tmin por parcela y mes, de 2022 a 2025.
* `precipitacion_acumulada_ciclo_2025_por_parcela.csv` y `temperatura_media_ciclo_2025_por_parcela.csv`: resumen del ciclo abril a octubre de 2025.
* `basico_metadatos_observaciones.csv`: fecha, sensor y nubosidad de cada observación del paquete Básico.
* `basico_resumen_satelital_por_parcela.csv` y `pro_resumen_satelital_por_parcela.csv`: promedios satelitales por parcela.

Las 12 tablas se pueden rehacer con los scripts de `eda_inicial/scripts/` (ver más abajo). Se comprobó al armar esta carpeta: al correr los 8 scripts desde aquí, las 12 tablas, los 12 archivos de `eda/` y las 32 figuras salen idénticos a los del proyecto original.

### eda_inicial/

Es el primer análisis exploratorio, el que se hizo al empezar el proyecto para conocer los datos antes de modelar. Tiene cuatro subcarpetas:

* `scripts/`: los scripts 01 a 08, uno por cada fuente de datos (01 ID, área y rendimiento; 02 paquete Básico; 03 paquete PRO; 04 comparación Básico contra PRO; 05 shapefile de parcelas; 06 lluvia; 07 temperatura; 08 topografía). Cada uno corre solo y escribe en `derivados/`, `eda/` y `figuras/`.
* `eda/`: un reporte corto por script (`01_...md` a `08_...md`), más `resumen_general.md`, que junta lo más importante, y algunas tablas CSV de apoyo.
* `figuras/`: las 32 gráficas del EDA (histogramas, cajas, dispersiones y el mapa de parcelas).
* `logs/`: lo que imprimió cada script al correr.

Estos 8 scripts siguen en R (están en `eda_inicial/scripts_R/`) porque leen los rasters, que no se copiaron a FINAL por su tamaño. Sus resultados (`derivados/` y `eda/`) ya están aquí, así que no hace falta repetirlos. Si se quisiera, se corren desde la carpeta FINAL con los rasters en `originales/`: `Rscript 01_datos/eda_inicial/scripts_R/01_id_area_rendimiento.R` y así hasta el 08. Los scripts 02 y 03 usan los paquetes `tidyverse` y `skimr`, el script 05 usa `sf`, y los scripts 06 a 08 usan `sf` y `terra`.

Lo que dejó el EDA, y que condicionó lo demás: la lluvia del ciclo abril a octubre se correlaciona con el rendimiento en -0.469 y la temperatura mínima en +0.61, y el clima viene en celdas de unos 5.5 km. La lectura posterior de esas cifras (el Estado explica cerca de la mitad de la varianza y la temperatura mínima marca sobre todo la región) está en los documentos de `03_hipotesis_y_variables/contexto_previo/`. El detalle del EDA está en `eda_inicial/eda/resumen_general.md`.

Qué cambió al copiar: solo las rutas de los 8 scripts, que ahora son relativas a la carpeta FINAL. Los logs son los originales. Las 12 tablas de `derivados/` están en el proyecto original en `outputs\derivados\`.

### originales/rasters_completos/

Los mapas mensuales de 2022 a 2025 que usan los scripts 06, 07 y 08: lluvia (CHIRPS), temperatura máxima y mínima, y topografía (INEGI, CEM 4). Son los mismos archivos que vienen en los zips del reto, ya descomprimidos. Los zips originales no se copiaron porque pesan lo mismo y no aportan nada más.

### preparados/

* `parcelas_limpias.gpkg`: los 197 polígonos con la geometría reparada (AGC_070 y AGC_078 estaban inválidas) y el cultivo escrito de una sola forma.
* `base_197_ubicacion.csv`: las 197 parcelas con estado, municipio, grupo de trabajo y celda climática, sin rendimiento.
* `base_138.csv`: las 138 parcelas de entrenamiento con su rendimiento. Es la base sobre la que se valida y se ajusta todo.
* `folds_V1.csv`, `folds_V2.csv`, `folds_V3.csv`: las particiones de validación. Se explican en `02_validacion_y_lineas_base/LEEME.md`.

## Diccionario

El archivo `diccionario_de_variables.md` explica en lenguaje simple cada columna de estas bases y cómo leer los nombres de las 148 variables candidatas.
