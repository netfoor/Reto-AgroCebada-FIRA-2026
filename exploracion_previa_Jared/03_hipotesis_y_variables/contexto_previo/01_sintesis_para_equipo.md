# Síntesis para la sesión de equipo — Reto AgroCebada FIRA 2026

Pensada para explicarse en voz alta (unos 15–20 min). Se basa en `outputs/eda/resumen_general.md` y en los 8
reportes individuales, más unas cifras nuevas calculadas solo leyendo `outputs/derivados/` (marcadas con 🆕).
No se modificó nada del EDA original.

**Contexto:** predecir el rendimiento de cebada (t/ha, ciclo abril–octubre 2025) en 197 parcelas de Puebla,
Hidalgo y Tlaxcala. Conocemos el rendimiento de 138 (entrenamiento); las otras 59 están ocultas (predicción).
Calificación final: 70% modelo, 30% dashboard. Entrega: **19 de octubre**. Mañana se define el plan de trabajo.

---

## 1. Qué información tenemos

| Fuente | Qué es, dicho simple | Cobertura | Estado |
|---|---|---|---|
| **Rendimiento y área** | La tabla de las 197 parcelas con su área en ha y su rendimiento (solo las 138 de entrenamiento) | 197 parcelas | Limpia, sin duplicados |
| **Shapefile de parcelas** | Los polígonos en el mapa, con Estado, Municipio y cultivo | 197 polígonos | 2 polígonos con un defecto menor |
| **Satélite Básico** | Índices de vegetación de Sentinel-2 y Landsat, una lectura cada pocos días | 2022–2025 | 24% de huecos por nubes en Sentinel-2 |
| **Satélite PRO (Planet)** | Índices de vegetación con lecturas casi diarias | Solo 2025 | 25% de huecos por nubes |
| **Lluvia (CHIRPS)** | Precipitación mensual en mm | 2022–2025, celdas de ~5.5 km | Completa |
| **Temperatura (Tmax/Tmin)** | Temperatura máxima y mínima mensual | 2022–2025, celdas de ~5.5 km | Completa y coherente |
| **Topografía (INEGI)** | Elevación y pendiente del terreno | Fija, resolución de 120 m | Completa |

Tres cosas conviene decir en voz alta:
- **Las 197 parcelas están en todas las fuentes**, con los mismos IDs y sin huérfanas.
- Las parcelas están más concentradas de lo que sugiere "3 estados": **Chignahuapan (Puebla) tiene 100 parcelas**,
  la mitad del total; Calpulalpan (Tlaxcala) tiene 44 y Singuilucan (Hidalgo) 23. Hay 9 municipios en total.
- 🆕 Como la lluvia y la temperatura vienen en celdas de ~5.5 km, las 197 parcelas comparten unos **50 valores
  climáticos distintos** (53 de lluvia y 50 de Tmin). Muchas parcelas vecinas tienen exactamente el mismo clima.

## 2. Qué ya sabemos con algo de confianza

**Sobre la calidad de los datos**
- Los huecos del satélite **no son azar: son nubes**. Cuando falta el índice, la escena estaba 100% nublada
  (pasa igual en Básico y en PRO). Rellenarlos con estadística no tendría sentido; se excluyen o se resuelven
  con compuestos en el tiempo.
- Los huecos se concentran en meses de lluvia (junio a octubre).
- **Básico y PRO no se pueden mezclar por nombre de índice.** El "LAI" de PRO es unas 8–10 veces mayor que el del
  Básico y el NDVI difiere ~46%. Son variables distintas aunque se llamen igual.
- El área de la parcela no tiene relación con el rendimiento (r = −0.08).
- El reparto entrenamiento/predicción es equilibrado en tamaño de parcela.

**Sobre la relación con el rendimiento** (correlaciones simples, solo con las 138 parcelas de entrenamiento; 0 es
"sin relación" y 1 es "relación perfecta"):

| Variable | Correlación | Cómo leerla |
|---|---|---|
| Temperatura mínima del ciclo | **+0.61** | La más fuerte; noches menos frías, más rendimiento |
| Lluvia acumulada del ciclo | **−0.47** | Contraintuitiva: más lluvia, menos rendimiento |
| SAVI / NDVI / EVI (Básico) | +0.32 / +0.28 / +0.25 | Débil-moderada |
| Pendiente y elevación | +0.31 / +0.29 | Débil |
| Temperatura máxima del ciclo | −0.29 | Débil |
| Índices de PRO (EVI, MSAVI, NDVI) | +0.20 / +0.20 / +0.16 | Más débil que el Básico, aunque PRO cubre el año exacto |
| Área de la parcela | −0.08 | Prácticamente nula |

Ninguna variable sola pasa de 0.65. Se espera que el modelo mejore combinando fuentes.

## 3. 🆕 El matiz que cambia la lectura de la tabla anterior: la región

Al cruzar el rendimiento con Estado y Municipio (`parcelas_atributos.csv`) aparece esto:

| Estado | Parcelas (entren.) | Rendimiento medio (t/ha) | Tmin del ciclo (°C) | Lluvia del ciclo (mm) |
|---|---|---|---|---|
| Puebla | 71 | **4.48** | 13.3 | 881 |
| Hidalgo | 36 | 3.76 | 12.8 | 1,045 |
| Tlaxcala | 31 | **2.98** | 12.0 | 1,004 |

- **Solo saber el Estado explica el 50% de la variación del rendimiento** (R² = 0.503).
- **Tmin distingue regiones, no parcelas dentro de una región.** Dentro de cada Estado su correlación con el
  rendimiento es casi cero (Tlaxcala −0.07, Puebla −0.05, Hidalgo −0.12). Si ya sabemos el Estado, agregar Tmin no
  mejora el ajuste (R² pasa de 0.503 a 0.507).
- Como Puebla es prácticamente un solo municipio, Tmin puede estar funcionando como etiqueta de "zona"
  (variedad, manejo, suelo, tecnología), no necesariamente como efecto térmico directo. **Las heladas siguen siendo
  una hipótesis plausible, pero el dato actual no la sostiene por sí solo.**
- **La lluvia conserva algo dentro de cada Estado, pero es frágil.** Agregarla al Estado sube el R² a 0.566. En
  Hidalgo la correlación interna es −0.65, pero **casi todo viene de un solo municipio: sin Singuilucan
  (16 parcelas, 1,135–1,335 mm, rendimiento medio 3.08) esa correlación pasa a +0.35.** Dentro de Chignahuapan es
  −0.23 en un rango estrecho (794–961 mm).
- **El reparto entrenamiento/predicción está estratificado por región** (Puebla 71/29, Hidalgo 36/15, Tlaxcala
  31/15). Usar Estado o Municipio como variable es legítimo para las 59 parcelas ocultas; no hay Estados que
  aparezcan solo en predicción.

Mensaje para el equipo: **antes de creer una señal climática hay que comprobar que sobrevive después de tener en
cuenta la región.**

## 4. Anomalías y dudas que persisten

**Del EDA original (documentadas, no corregidas)**
- **LAI con valores negativos** en ambos datasets satelitales (hasta −0.19 en Básico y −0.11 en PRO).
- **2 polígonos inválidos** por vértice duplicado: AGC_070 y AGC_078. Se arreglan con `st_make_valid()`.
- **"Cebada" vs "CEBADA"** en el campo `Cultivo` (50 vs 147 parcelas).
- **Área del atributo vs área geométrica:** el atributo es ~0.68% menor de forma sistemática. Falta decidir cuál
  se toma como oficial.
- **Outliers de área:** 11 parcelas, sobre todo AGC_047 (64.3 ha) y AGC_065 (60.9 ha). Vigilar su influencia.
- **Outliers de pendiente:** AGC_060 (9.4°) y AGC_057 (8.2°).
- **2025 fue el año más lluvioso de la serie** (2022–23 rondan 530–540 mm abr–oct y 2024–25 rondan 940–960).
- **Resolución de los datos:** las celdas de lluvia y temperatura son de ~5.5 km, y el DEM de 120 m es mayor que
  varias parcelas.

**Inconsistencias que encontré al leer los reportes del EDA** (no las corregí porque `eda/` no se toca):
- `08_raster_topografia.md`, sección 3, dice que la elevación se acota "a la zona agrícola de Españita,
  Tlaxcala". Es un error: las parcelas están en Puebla, Hidalgo y Tlaxcala. Los números (elevación media
  2,667 m) no se ven afectados.
- `05_shapefile_parcelas.md` (hallazgo 5) nombra a Singuilucan como tercer municipio, pero por conteo el tercero
  es Almoloya (14 parcelas) en la tabla de esa misma sección. Cambia poco, pero conviene tener claro el orden
  real: Chignahuapan 100, Calpulalpan 44, Singuilucan 23, Almoloya 14.
- `resumen_general.md` dice "ENTRENOMIENTO" en la sección 1 (es un typo de "ENTRENAMIENTO").
- Fuera de esos tres detalles, el resto de las cifras que revisé coincide entre los reportes (por ejemplo,
  138/59 en el shapefile y en `ID_area_rendimiento`).

## 5. Decisiones que hay que tomar en equipo

1. **Ventana del ciclo.** ¿Seguimos con abril–octubre para todas las parcelas o definimos ventanas fenológicas
   (siembra, macollaje, floración, llenado)? No tenemos fecha de siembra ni de cosecha por parcela.
2. **Región como variable.** ¿Usamos Estado y/o Municipio como variable explícita del modelo? Mi lectura: sí,
   porque el split está estratificado, pero eso baja el peso atribuible al clima.
3. **Cómo validar el modelo.** Validación cruzada al azar (optimista, porque parcelas vecinas comparten clima) o
   por grupos de municipio (más exigente, pero varios municipios tienen 1–5 parcelas).
4. **Cómo tratar Básico y PRO.** Como familias separadas con sufijo por sensor, y si combinarlas en un mismo
   modelo cuenta como "fusión" que el reto no permite (duda #2 para los organizadores).
5. **Fuente oficial del área** (atributo o geométrica) y qué hacer con las 2 geometrías inválidas.
6. **LAI negativo:** truncar en 0, dejarlo o descartar LAI.
7. **Cómo tratar los outliers** de área y de pendiente.
8. **Qué preguntar a los organizadores** y en qué orden. Prioridad sugerida:
   1. Fechas de siembra/cosecha o ventana fenológica.
   2. Si existen rendimientos de ciclos anteriores.
   3. Si combinar features de Planet y Sentinel-2 se considera fusión.
   4. Registros de heladas o de exceso de lluvia en 2025.
   5. Área oficial, LAI negativo, geometrías inválidas, DEM de mayor resolución.
9. **Reparto del trabajo hasta el 19 de octubre**, sin olvidar el dashboard (30% de la nota). Para mañana, For y
   Daf traen ideas de feature engineering y de efecto causal; ver los archivos 02 y 03 de esta carpeta.

## 6. Para la sesión de hoy con QGIS (sugerencias)

- Cargar `parcelas_validadas.gpkg` (en `outputs/derivados/`) o el shapefile original y colorear por `CONJUNTO`.
- Unir `parcelas_atributos.csv` por `ID_POLIGONO` para ver Estado y Municipio, y colorear por rendimiento para ver
  visualmente el efecto regional.
- Revisar en el mapa AGC_070, AGC_078, AGC_047, AGC_065, AGC_060 y AGC_057.
- Superponer un raster de lluvia o de Tmin para ver que varias parcelas caen en la misma celda.
- Los rasters de topografía están en EPSG:6372 y las parcelas en EPSG:4326; QGIS los reproyecta al vuelo.

---
*Cifras marcadas con 🆕: calculadas solo leyendo `outputs/derivados/` (rendimiento por Estado/Municipio,
correlaciones dentro de Estado, R² de modelos con Estado, valores climáticos únicos y efecto de Singuilucan).
Son descriptivas y con pocas parcelas por grupo; no son resultados de modelado.*
