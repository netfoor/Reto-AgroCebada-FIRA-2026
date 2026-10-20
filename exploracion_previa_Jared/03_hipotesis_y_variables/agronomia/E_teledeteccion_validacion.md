# Hoja E: Teledetección y validación, cómo se miden las cosas y cómo se prueba

Reto AgroCebada FIRA 2026, preparación de agronomía. Preparado el 20 de septiembre de 2026.

Marcas usadas en todo el documento: **[V]** verificado (texto completo leído y citado; en páginas oficiales, la página o el extracto con cita textual), **[V-parcial]** visto solo en un extracto, en un resumen de búsqueda o en un documento de otro país, **[PV]** por verificar, **[CP]** cálculo o razonamiento propio (las cifras [CP] salen de `scripts/40_chequeos_1B.R` y de `resultados/1B_chequeos.csv`). Esta hoja continúa los bloques A a D y corresponde al Prompt 1B. No fija hipótesis nuevas; las que dependen de ella ya están registradas (HA1 a HA3, HB7 y HD3).

## 1. Qué mide cada índice y dónde falla (bloque a)

| Índice | Fórmula | Qué mide | Dónde falla |
|---|---|---|---|
| NDVI | (NIR − R) / (NIR + R) **[V]** (U.S. Geological Survey [USGS], s. f.-a) | Verdor y vigor de la vegetación | Se satura con dosel denso (LAI mayor a 3) **[V-parcial]** (Tian et al., 2025); con poca cobertura lo afecta el brillo del suelo **[V-parcial]** (Baret y Guyot, 1991) |
| EVI | 2.5 × (NIR − R) / (NIR + 6R − 7.5B + 1) **[V]** (USGS, s. f.-b) | Vigor con corrección parcial de suelo y atmósfera; se satura menos **[V-parcial]** (Huete et al., 2011) | Necesita la banda azul (B) |
| SAVI | (NIR − R) / (NIR + R + L) × (1 + L), con L = 0.5 **[V]** (USGS, s. f.-c) | Vigor con menor influencia del suelo cuando la cobertura es baja | L es fijo y no se adapta a cada parcela |
| MSAVI | (2 NIR + 1 − √((2 NIR + 1)² − 8 (NIR − R))) / 2 **[V]** (USGS, s. f.-d) | Como SAVI, pero el ajuste de suelo se calcula solo | En nuestros datos solo está en PRO **[V]** ("Diccionario de índices satelitales", 2026) |
| LAI | m² de hoja verde por m² de terreno **[V]** (National Aeronautics and Space Administration [NASA], s. f.) | Cantidad de hojas del dosel | No se mide desde el satélite, se estima con un modelo o una fórmula sobre bandas o sobre otro índice **[V-parcial]** (Baret y Guyot, 1991; Allen et al., 2007) |

**Por qué el NDVI se satura.** Con dosel denso, el rojo ya casi no cambia al sumar hojas y el cociente se aplana; además la propia fórmula comprime los valores altos **[V-parcial]** (Tian et al., 2025). Los autores ubican el problema con un LAI mayor a 3, y Huete et al. (2011) explican que el NDVI depende de la banda roja, que penetra poco en el dosel, mientras que el EVI se apoya más en el infrarrojo cercano y por eso se satura menos **[V-parcial]**. En nuestros datos esto pesa poco: solo 0.97% de las lecturas de PRO y 0.04% de las del Básico (Sentinel-2) tienen NDVI mayor a 0.8, y la mediana del NDVI es 0.175 en el Básico y 0.275 en PRO **[CP]**. El problema principal es el contrario, suelo desnudo y rastrojo, y por eso conviene SAVI o MSAVI antes que preocuparse por la saturación.

**Qué es el LAI y por qué sale negativo.** El LAI es la superficie de hoja verde de un solo lado por unidad de superficie de terreno **[V]** (NASA, s. f.), así que nunca debería ser negativo. Pero el satélite no lo mide, lo calcula el proveedor. En el Básico el LAI es casi una copia reescalada de SAVI: la correlación de rangos entre ambos es 0.9999 y el LAI cruza cero justo donde SAVI vale 0.1 **[CP]**. Como 42.4% de las lecturas de Sentinel-2 tienen SAVI menor a 0.1 (suelo desnudo o rastrojo), 42.2% salen con LAI negativo, es decir 18,916 de 44,877 lecturas con mínimo de −0.192 **[V]** (Equipo Reto AgroCebada, 2026c). Una fórmula publicada de la forma LAI = −ln((0.69 − SAVI) / 0.59) / 0.91 **[V-parcial]** (Allen et al., 2007) reproduce esos valores: la mediana de la diferencia es 0.001, 92.5% de las lecturas quedan a menos de 0.02 y en el SAVI del mínimo da −0.1926 **[CP]**. No afirmamos que sea la fórmula del proveedor, porque el diccionario pide no asumir otra fórmula **[PV]** ("Diccionario de índices satelitales", 2026), pero explica el signo: un LAI negativo no es área foliar negativa, es la extrapolación de la fórmula con suelo casi desnudo.

En PRO el LAI es casi una función del NDVI (correlación de rangos 0.98 **[CP]**), su media es 1.22 y solo 1 de 35,747 lecturas es negativa **[V]** (Equipo Reto AgroCebada, 2026c). Consecuencias para el modelo **[CP]**: el LAI del Básico no aporta información propia frente a SAVI, así que no conviene meter ambos; si se usa, va recortado a 0 con una bandera de LAI negativo, como se propuso en la Fase 1; y el LAI de PRO y el del Básico nunca se mezclan (media 1.22 contra 0.131, unas 9 veces) **[V]** (Equipo Reto AgroCebada, 2026b).

## 2. Validación agrupada, fuga de información y por qué un modelo simple (bloque b)

**Fuga de información.** Hay fuga cuando el modelo, al ajustarse, ve algo que en la vida real no vería. Aparece de dos formas. La primera es por vecinos: las parcelas de una misma celda climática comparten exactamente el mismo clima, y si una queda en la validación y su vecina en el ajuste, el modelo puede acertar recordando la celda y no entendiendo la parcela. En Chignahuapan, 68 de las 138 parcelas de entrenamiento (49%) están en solo dos celdas de 34 **[V]** (Equipo Reto AgroCebada, 2026a). Con la validación V1, 92.2% de las parcelas de validación tiene un vecino de su misma celda en el ajuste (rango 82.9 a 100), contra 0% en V2 **[V]** (Equipo Reto AgroCebada, 2026c). La segunda forma es elegir variables con todos los datos y validar después: la selección también aprende del rendimiento y el error sale demasiado optimista **[V-parcial]** (Ambroise y McLachlan, 2002); por eso la regla 3 exige repetir la selección dentro de cada partición.

**Qué validación creer.** Roberts et al. (2017) recomiendan validar por bloques cuando hay dependencia, porque la validación al azar subestima el error **[V-parcial]**; Wadoux et al. (2021) responden que la validación debe reproducir cómo se usará el modelo y que los métodos espaciales no tienen fundamento teórico para medir la exactitud de un mapa **[V-parcial]**. Ambas posturas caben en nuestro diseño. Como 96.6% de las 59 parcelas ocultas tiene un vecino de su celda en las 138 **[V]** (Equipo Reto AgroCebada, 2026c), V1 imita la situación real (92.2% contra 96.6%) y es la estimación principal, mientras que V2 es la prueba de esfuerzo (0% de vecinos). El error esperado en las 59 debe quedar entre las dos, más cerca de V1 **[CP]**.

**Por qué n = 138 pide un modelo simple.**

- Hay pocos datos independientes: son 138 parcelas pero solo 23 celdas climáticas distintas **[CP]**, así que para las variables de clima la información real se parece más a 23 puntos que a 138.
- La vara de medir es ruidosa: con unas 41 parcelas de validación, el RMSE de B2 en V1 va de 0.386 a 0.626 entre las 100 divisiones (percentiles 5 y 95) **[V]** (Equipo Reto AgroCebada, 2026c). Varoquaux (2017) muestra que con unas 100 muestras el error de la validación cruzada ronda ±10% y que el error estándar entre pliegues lo subestima **[V-parcial]**. Por eso se comparan los modelos sobre los mismos pliegues (diferencia contra B2 en cada repetición) y se exige que la mejora se repita entre semillas.
- Ya hay una base fuerte: B2, con solo cinco promedios de grupo, logra un R² de 0.641 en V1 **[V]** (Equipo Reto AgroCebada, 2026c). Cada variable nueva debe mejorar eso con una vara ruidosa, así que conviene pocas variables y modelos con pocos parámetros (lineal regularizado, árboles poco profundos) y no cientos de candidatas.

**El caso Chignahuapan.** En todos los grupos el error de B2 se parece a la desviación interna del grupo, porque B2 es el promedio del grupo; eso no es una señal especial de Chignahuapan. Lo que la distingue es el peso: concentra 68.2% de la variación que queda dentro de los grupos (23.9 de 35.0 en suma de cuadrados) **[CP]**, y su desviación interna es 0.584 t/ha frente a un error de B2 de 0.55 **[V]** (Equipo Reto AgroCebada, 2026c). Ahí es donde las variables tienen que trabajar.

## 3. Qué aportan y qué no aportan las fuentes (bloque c)

Una parcela mediana mide 5.46 ha (mínimo 0.35, máximo 64.3) **[CP]**, lo que da unos 546 píxeles a 10 m, 136 a 20 m, 61 a 30 m y unos 6,000 a 3 m.

| Fuente | Resolución y frecuencia | Qué aporta en nuestros datos | Qué no aporta o cuidado |
|---|---|---|---|
| Básico, Sentinel-2 | 10 m (B2, B3, B4, B8), 20 m (B5, B6, B7, B8a, B11, B12) y 60 m (B1, B9, B10); cada 5 días **[V]** (SentiWiki, s. f.). Los índices con onda corta (B11, B12) van a 20 m; cuáles son en el Básico **[PV]** | 2022 a 2025, 22 índices (16 sin evaluar) y la desviación dentro de la parcela **[V]** ("Diccionario de índices satelitales", 2026) | 24.0% de las filas sin valor por nubes, sobre todo de junio a octubre **[V]** (Equipo Reto AgroCebada, 2026b); su LAI duplica a SAVI **[CP]** |
| Básico, Landsat 8 y 9 | 30 m en el óptico y 100 m en la térmica; cada 8 días entre los dos satélites **[V]** (USGS, s. f.-e). La térmica llega remuestreada a 30 m **[V-parcial]** | Solo VI6T **[V]** ("Diccionario de índices satelitales", 2026), una señal espectral y térmica distinta | 36.1% de las filas Landsat sin VI6T **[V]** (Equipo Reto AgroCebada, 2026b); píxel grueso, 61 en una parcela mediana y unos 17 en las chicas (percentil 10) **[CP]** |
| PRO, Planet | 3 m, casi diaria, 8 bandas en SuperDove **[V]** (Planet Labs PBC, s. f.). Tamaño nativo del píxel y ruido de la banda infrarroja **[PV]** | Solo 2025, el ciclo evaluado, con 243 lecturas por parcela (mediana) y detalle del ciclo (HA1, HA2, HB7) **[V]** (Equipo Reto AgroCebada, 2026b) | Sin historia previa, no permite una base multianual; 25.2% de huecos por nubes; NDVI 45.6% mayor y LAI unas 9 veces el del Básico, por eso no se mezclan **[V]** |
| CHIRPS | 0.05° (unos 5 km) **[V]** (Funk et al., 2015); mensual en nuestro archivo | Lluvia de 2022 a 2025 en toda la zona | Una celda cubre unas 3,000 ha, más de 500 parcelas medianas **[CP]**; sesgos documentados en México **[V-parcial]** (ver Bloque D) |
| CHIRTS-ERA5 | 0.05° (unos 5 km), diaria desde 1983; los campos mensuales de CHIRTS se reparten en días con la variación de ERA5 **[V]** (Climate Hazards Center [CHC], 2025) | Tmin y Tmax mensuales, promedio de las diarias **[V]** ("Descripción general del conjunto de datos", 2026) | La variación día a día viene de ERA5, más gruesa (del orden de 25 a 30 km) **[V-parcial]**, así que 5 km es resolución nominal; no ve heladas locales (Bloque B) |
| DEM del CEM | El documento del reto cita CEM 4.0 con 15 m **[V]** ("Descripción general del conjunto de datos", 2026), y los rasters entregados son de 120 m **[V]** (Equipo Reto AgroCebada, 2026b) | Elevación y pendiente | 17 de 197 parcelas (8.6%) miden menos que una celda de 120 m (1.44 ha) **[CP]**; pregunta abierta a los organizadores |

Ninguna fuente trae fecha de siembra, variedad, dosis de nitrógeno, fungicida ni si fue temporal o riego (Bloque C). El satélite ve el efecto del manejo en la vegetación, no el manejo. Por eso Chignahuapan, con 4 celdas climáticas, depende de lo que el satélite y el terreno puedan decir (HD3). Además, la comparación de SAVI (0.317, Básico) contra EVI (0.200, PRO) con el rendimiento es global y no controla por región **[V]** (Equipo Reto AgroCebada, 2026b); no sabemos si PRO o el Básico aportan sobre B2 hasta probarlo en la Semana 2.

## 4. Preguntas de repaso

Bloque a, índices y LAI:

1. ¿Por qué el NDVI casi no cambia cuando el dosel ya es muy denso y a partir de qué LAI se vuelve un problema?
2. ¿Qué diferencia práctica hay entre NDVI, SAVI y MSAVI cuando la parcela tiene mucho suelo desnudo?
3. Define LAI con sus unidades y explica por qué un LAI de −0.19 no significa hojas negativas.
4. En el Básico, ¿por qué LAI y SAVI casi no aportan información distinta y qué haces al armar las variables?
5. Con nuestros datos, ¿preocupa más la saturación del NDVI o el suelo desnudo? Da una cifra.

Bloque b, validación:

1. ¿Qué es la fuga de información? Da un ejemplo con vecinos de la misma celda y otro con selección de variables.
2. ¿Qué significa que en V1 el 92.2% de la validación tenga vecino en el ajuste y en V2 el 0%? ¿Cuál se parece más a las 59 ocultas y por qué?
3. Resume en una frase el desacuerdo entre Roberts et al. (2017) y Wadoux et al. (2021) y cómo lo resuelve nuestro diseño.
4. Con 138 parcelas y 23 celdas, ¿por qué conviene un modelo simple? Usa el rango de 0.386 a 0.626.
5. ¿Por qué el error de B2 en Chignahuapan es casi igual a su desviación y por qué eso no basta como argumento ante el jurado? ¿Qué dato sí sirve?

Bloque c, Básico y PRO:

1. Una parcela mediana tiene unos 546 píxeles a 10 m y 136 a 20 m: ¿qué implica para un índice con onda corta?
2. ¿Por qué no se mezclan el LAI de PRO y el del Básico? Da dos cifras.
3. ¿Qué aporta PRO que el Básico no, y qué aporta el Básico que PRO no?
4. Si CHIRTS-ERA5 tiene celdas de 5 km, ¿por qué su resolución real puede ser peor?
5. Menciona tres datos de manejo que ninguna fuente satelital trae y explica cómo eso limita el modelo.

## 5. Preguntas para los organizadores que salen de esta hoja

- ¿El LAI del Básico se calcula con una ecuación basada en SAVI, como la de Allen et al. (2007)? ¿Cuál es la fórmula exacta de cada índice?
- ¿Qué producto de Planet se usó (nombre, nivel de corrección y remuestreo)?
- ¿Los rasters oficiales son el CEM de 15 m o los de 120 m que recibimos?
- ¿Combinar Básico y PRO en un mismo modelo se considera fusión?

## 6. Lo que no debemos afirmar todavía

- Que la ecuación de Allen et al. (2007) sea la del proveedor: coincide con los datos, pero no está confirmada **[PV]**.
- Que la saturación del NDVI sea un problema en nuestras parcelas: solo aparece en menos de 1% de las lecturas, con promedios por parcela y fecha **[CP]**.
- Que PRO sea peor que el Básico: la comparación es global, no controla por región y usa periodos distintos **[CP]**.
- Que el rango de 5 a 95% entre divisiones sea un intervalo de confianza para las 59 ocultas **[V]** (Equipo Reto AgroCebada, 2026a).

## Fuentes (estado)

Referencias en APA 7:

- Allen, R. G., Tasumi, M. y Trezza, R. (2007). Satellite-based energy balance for mapping evapotranspiration with internalized calibration (METRIC): Model. Journal of Irrigation and Drainage Engineering, 133(4), 380–394. https://doi.org/10.1061/(ASCE)0733-9437(2007)133:4(380)
- Ambroise, C. y McLachlan, G. J. (2002). Selection bias in gene extraction on the basis of microarray gene-expression data. Proceedings of the National Academy of Sciences, 99(10), 6562–6566. https://doi.org/10.1073/pnas.102102699
- Baret, F. y Guyot, G. (1991). Potentials and limits of vegetation indices for LAI and APAR assessment. Remote Sensing of Environment, 35(2–3), 161–173. https://www.sciencedirect.com/science/article/abs/pii/003442579190009U
- Climate Hazards Center. (2025). CHIRTS-ERA5 data repository. University of California, Santa Barbara. https://doi.org/10.15780/G2F08J
- Descripción general del conjunto de datos. (2026). [Documento del conjunto de datos]. Reto AgroCebada FIRA 2026.
- Diccionario de índices satelitales. (2026). [Documento del conjunto de datos]. Reto AgroCebada FIRA 2026.
- Equipo Reto AgroCebada. (2026a). Plan de la Fase 1: Limpieza, validación interna y líneas base [Documento interno]. Reto AgroCebada FIRA 2026.
- Equipo Reto AgroCebada. (2026b). Reportes del EDA: resumen_general.md y reportes 02 a 04 y 08 [Documentos internos]. Reto AgroCebada FIRA 2026.
- Equipo Reto AgroCebada. (2026c). Resultados de la Fase 1: resumen_esquemas.csv, lineas_base_resumen.csv y lai_negativo_conteo.csv [Archivos internos]. Reto AgroCebada FIRA 2026.
- Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak, G., Rowland, J., Harrison, L., Hoell, A. y Michaelsen, J. (2015). The climate hazards infrared precipitation with stations: A new environmental record for monitoring extremes. Scientific Data, 2, Artículo 150066. https://doi.org/10.1038/sdata.2015.66
- Huete, A., Didan, K., van Leeuwen, W., Miura, T. y Glenn, E. (2011). MODIS vegetation indices. En B. Ramachandran, C. O. Justice y M. J. Abrams (Eds.), Land remote sensing and global environmental change (pp. 579–602). Springer. https://doi.org/10.1007/978-1-4419-6749-7_26
- National Aeronautics and Space Administration. (s. f.). Leaf area index. Earthdata. https://www.earthdata.nasa.gov/topics/biosphere/leaf-area-index
- Planet Labs PBC. (s. f.). PlanetScope. Planet Documentation. https://docs.planet.com/data/imagery/planetscope/
- Roberts, D. R., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography, 40, 913–929. https://www.wsl.ch/lud/biodiversity_events/papers/Roberts_et_al-2017-Ecography.pdf
- SentiWiki. (s. f.). S2 mission. Copernicus. https://sentiwiki.copernicus.eu/web/s2-mission
- Tian, Z., Fan, J., Yu, T., de Leon, N., Kaeppler, S. M. y Zhang, Z. (2025). Mitigating NDVI saturation in imagery of dense and healthy vegetation. ISPRS Journal of Photogrammetry and Remote Sensing, 227, 234–250. https://www.sciencedirect.com/science/article/abs/pii/S0924271625002394
- U.S. Geological Survey. (s. f.-a). Landsat normalized difference vegetation index. https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index
- U.S. Geological Survey. (s. f.-b). Landsat enhanced vegetation index. https://www.usgs.gov/landsat-missions/landsat-enhanced-vegetation-index
- U.S. Geological Survey. (s. f.-c). Landsat soil adjusted vegetation index. https://www.usgs.gov/landsat-missions/landsat-soil-adjusted-vegetation-index
- U.S. Geological Survey. (s. f.-d). Landsat modified soil adjusted vegetation index. https://www.usgs.gov/landsat-missions/landsat-modified-soil-adjusted-vegetation-index
- U.S. Geological Survey. (s. f.-e). Landsat 8. https://www.usgs.gov/landsat-missions/landsat-8
- Varoquaux, G. (2017). Cross-validation failure: Small sample sizes lead to large error bars [Preprint]. arXiv. https://arxiv.org/abs/1706.07581
- Wadoux, A. M. J.-C., Heuvelink, G. B. M., de Bruin, S. y Brus, D. J. (2021). Spatial cross-validation is not the right way to evaluate map accuracy. Ecological Modelling, 457, Artículo 109692. https://research.wur.nl/en/publications/spatial-cross-validation-is-not-the-right-way-to-evaluate-map-acc/

Estado de lectura. Páginas oficiales leídas con cita textual: NASA (LAI), USGS (NDVI, EVI, SAVI, MSAVI y Landsat 8), SentiWiki, Planet, Climate Hazards Center, resumen de Funk et al. (2015) y los dos documentos del reto. Solo extracto o resumen: Tian et al., Huete et al. (capítulo), Baret y Guyot, Roberts et al. (autores completos sin verificar), Wadoux et al., Ambroise y McLachlan y Varoquaux. La ecuación de Allen et al. (2007) se vio reproducida en un artículo secundario (ecuación 8) y el texto original no se leyó. No accesibles y no citadas: Fang et al. (2019) y Riley et al. (2019), con error 403, y la página de Huete et al. (2002) en ADS, bloqueada. Buscado sin éxito: la fórmula del LAI del proveedor, el ruido de la banda infrarroja de Planet, el tamaño nativo del píxel de Planet y el remuestreo de la banda térmica de Landsat en la página de USGS consultada.
