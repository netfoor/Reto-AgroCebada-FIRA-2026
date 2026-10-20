# Ideas de feature engineering — Reto AgroCebada FIRA 2026

Lista priorizada de variables derivadas para construir **antes** de modelar. Solo ideas, sin código todavía.
Se apoya en lo ya documentado en `outputs/eda/` y en cifras nuevas calculadas leyendo `outputs/derivados/`.
Son propuestas para discutir con el equipo (incluidos For y Daf), no un plan cerrado.

## Puntos de partida que condicionan todo

1. **Los huecos satelitales son nubes** (nubosidad 100% ⇒ índice vacío): excluir o hacer compuestos, no imputar.
2. **Básico (S2/Landsat) y PRO (Planet) no son comparables por nombre de índice**: siempre con sufijo de sensor.
3. **La señal más fuerte hasta ahora es Tmin (+0.61) y ninguna variable sola pasa de 0.65.**
4. 🆕 **Pero Tmin distingue regiones más que parcelas:** dentro de cada Estado su correlación con el rendimiento
   es casi cero (−0.07 a −0.12), y el Estado solo ya explica ~50% de la varianza. Cualquier variable climática hay
   que evaluarla **después de controlar por región**, si no, se está premiando una etiqueta de zona.
5. 🆕 **Lluvia y temperatura vienen en celdas de ~5.5 km:** solo ~50 valores climáticos distintos para 197
   parcelas. Las variables derivadas del clima mensual heredan esa limitación: dos parcelas vecinas tendrán el
   mismo valor.
6. 🆕 **Los valores por fecha del satélite no están en `derivados/`**: allí solo hay promedios por parcela y los
   metadatos de nubosidad. Los compuestos temporales requieren leer el CSV original en `DataSet/` (solo lectura);
   los productos nuevos deberían guardarse en una carpeta nueva, no en `derivados/`.
7. Solo hay **138 parcelas de entrenamiento**: conviene pocas variables bien pensadas y no cientos de candidatas.

Nomenclatura sugerida: sufijo de sensor (`_s2`, `_landsat`, `_planet`), de ventana (`_w1`…) y prefijo de origen
(`clim_`, `sat_`, `topo_`, `reg_`).

---

## Prioridad 1 — construir primero

### 1. Contexto regional (`reg_estado`, `reg_municipio_agrupado`)
- **Por qué:** explica ~50% de la varianza por sí solo y el split está estratificado por región, así que es válido
  para las 59 parcelas ocultas. Es también la línea base contra la cual medir si el resto de variables aporta algo.
- **Insumo:** `parcelas_atributos.csv` → `Estado`, `Municipio`. Agrupar los municipios con menos de ~5 parcelas
  (Apan, Tepeapulco, Nanacamilpa, Emiliano Zapata) en una categoría "otros".
- **Cuidado:** decidir si va como categórica o como efecto aleatorio; con 9 municipios y varios de 1–5 parcelas,
  la validación por grupos será inestable.

### 2. Ventanas fenológicas de temperatura y lluvia (en vez del promedio abril–octubre)
- **Por qué:** el promedio de 7 meses mezcla etapas con necesidades muy distintas (siembra, macollaje, espigado,
  llenado de grano). El EDA ya lo señala como duda #1.
- **Insumo:** `temperatura_mensual_por_parcela.csv` (`anio`, `mes`, `tmax_c`, `tmin_c`) y
  `precipitacion_mensual_por_parcela.csv` (`anio`, `mes`, `precip_mm`), año 2025.
- **Propuesta:** 3–4 ventanas de 1–2 meses (p. ej. abr–may, jun–jul, ago–sep, oct) y evaluar cuál se asocia mejor
  con el rendimiento. **Limitación:** con datos mensuales no se puede hacer mejor que eso, y sin fecha de siembra
  las ventanas son una suposición.

### 3. Anomalías climáticas de 2025 contra la historia de cada parcela
- **Por qué:** separa "cómo es el clima de esta zona" (que se parece mucho a la región) de "qué tan atípico fue
  2025" (lo que sí varía año a año). Hay datos climáticos de 2022–2024 para construir la referencia.
- **Insumo:** los dos CSV mensuales de arriba, 2022–2024 como línea base.
- **Propuesta:** `clim_prec_anom_2025` (mm o %) y `clim_tmin_anom_2025` (°C) por ventana. Ojo: el ranking de lluvia
  entre parcelas es muy estable entre años (r = 0.77–0.83), así que las anomalías tendrán poca variación entre
  parcelas y mucha entre años (1 solo año con rendimiento).

### 4. Compuestos satelitales sin nubes, por mes o por ventana
- **Por qué:** los huecos por nube se concentran de junio a octubre, justo en el ciclo. Un compuesto mensual
  (mediana o máximo con nubosidad baja) suaviza el patrón en vez de dejar observaciones sueltas.
- **Insumo:** CSV original Básico (`fecha_captura`, `sensor`, índices, `porcentaje_nubosidad`) y PRO. Los
  metadatos ya están en `basico_metadatos_observaciones.csv` y `pro_metadatos_observaciones.csv`.
- **Propuesta:** filtrar nubosidad < umbral (probar 10–20%), compuesto mensual del índice y **contar cuántos
  meses quedan con dato válido** como variable de calidad (`sat_meses_validos_s2`).
- **Cuidado:** decidir el umbral de nubosidad y cómo tratar meses sin ningún dato válido (dejar vacío y que el
  modelo lo maneje, o interpolar de forma explícita y documentada).

### 5. Variables separadas por sensor, con sufijo
- **Por qué:** LAI de PRO es ~8× el de Básico y el NDVI difiere ~46%. Mezclarlas por nombre sería un error.
- **Insumo:** `basico_resumen_satelital_por_parcela.csv` (`ndvi_promedio`, `evi_promedio`, `lai_promedio`,
  `savi_promedio`, …) y `pro_resumen_satelital_por_parcela.csv` (`ndvi_promedio`, `evi_promedio`, `lai_promedio`,
  `msavi_promedio`).
- **Propuesta:** renombrar a `ndvi_s2`, `ndvi_planet`, etc. Mantener SAVI de S2 (mejor índice individual, +0.32) y
  probar S2 y Planet como familias separadas.
- **Duda abierta:** si combinar ambas familias en un mismo modelo se considera "fusión" (pregunta #2 del EDA).

---

## Prioridad 2 — valor probable, construir si hay tiempo

### 6. Grados-día en el ciclo
- **Por qué:** el EDA lo sugiere y resume el calor acumulado útil de forma más agronómica que un promedio.
- **Insumo:** `temperatura_mensual_por_parcela.csv` (`tmax_c`, `tmin_c`) → temperatura media mensual × días del mes.
- **Limitación:** es una aproximación mensual, no diaria; y las diferencias entre parcelas dependerán de las mismas
  ~50 celdas.

### 7. Proxy de "noches frías" con datos mensuales
- **Por qué:** Tmin tiene la señal más fuerte y la hipótesis agronómica son las heladas. Con datos mensuales no
  hay conteo real de noches frías.
- **Insumo:** `temperatura_mensual_por_parcela.csv` → `tmin_c` mínimo del ciclo, y número de meses con Tmin por
  debajo de un umbral (p. ej. 10 °C; la Tmin media de 2025 fue ~11 °C en abril y ~11 °C en octubre).
- **Cuidado:** es un proxy débil de heladas reales. Si los organizadores tienen registros de heladas o datos
  diarios, vale mucho más.

### 8. Perfil fenológico del ciclo 2025 con PRO
- **Por qué:** Planet tiene lecturas casi diarias solo en 2025 y aporta dinámica fina que Básico no tiene.
- **Insumo:** CSV original PRO (`fecha_captura`, `ndvi_promedio`, `evi_promedio`, `msavi_promedio`).
- **Propuesta:** NDVI máximo del ciclo, mes en que ocurre, área bajo la curva abril–octubre y pendiente de
  subida. Todas con sufijo `_planet`.

### 9. Perfil de vegetación multianual con Básico
- **Por qué:** el Básico correlaciona mejor que PRO (+0.32 vs +0.20); la hipótesis es que el promedio de 4 años
  captura características estables de la parcela (suelo, manejo).
- **Insumo:** CSV original Básico, 2022–2025.
- **Propuesta:** promedio de S2 en la misma ventana del ciclo de 2022, 2023 y 2024 (vigor "típico") y
  `sat_ndvi_s2_2025 − típico` (desviación del año de evaluación).

### 10. Exceso hídrico
- **Por qué:** la lluvia se asocia negativamente con el rendimiento y 2025 fue el año más lluvioso. Un total
  acumulado oculta si fue la lluvia de una ventana o concentrada en pocos meses.
- **Insumo:** `precipitacion_mensual_por_parcela.csv` (`precip_mm`).
- **Propuesta:** máximo mensual del ciclo, número de meses con más de X mm, y fracción de la lluvia del ciclo que
  cayó en los 2 meses más lluviosos.
- **Cuidado:** ver `03_ideas_efecto_causal.md`: el −0.47 puede reflejar sobre todo diferencias regionales.

### 11. Interacciones entre topografía y clima
- **Por qué:** elevación y pendiente son débiles solas (+0.29 y +0.31); probablemente actúan como proxies de
  microclima o drenaje. 🆕 Elevación y Tmax están fuertemente relacionadas (r = −0.68), así que se solapan.
- **Insumo:** `topografia_por_parcela.csv` (`elevacion_m`, `pendiente_grados`) con los agregados climáticos.
- **Propuesta:** `pendiente × lluvia` (drenaje) y `elevación × Tmin` (frío por altitud), y evaluar si Tmax se puede
  dejar fuera por ser casi redundante con elevación.
- **Cuidado:** el DEM de 120 m es mayor que varias parcelas, así que la pendiente por parcela está suavizada.

---

## Prioridad 3 — exploratorio

| Idea | Insumo | Nota |
|---|---|---|
| Amplitud térmica del ciclo (Tmax − Tmin) | `temperatura_mensual_por_parcela.csv` | Se calcula con los mismos insumos que Tmax y Tmin; puede ser redundante, sin verificar |
| Área en escala logarítmica, como control | `id_area_rendimiento_limpio.csv` → `AREA_HA` | Cola larga; AGC_047 y AGC_065 dominan sin transformar |
| Número de observaciones válidas de cada sensor | `basico_metadatos_observaciones.csv`, `pro_metadatos_observaciones.csv` | Calidad de datos, no agronomía |
| Estabilidad interanual del NDVI en S2 (2022–2024) | CSV original Básico | Puede aproximar homogeneidad del manejo |
| Distancia a otras parcelas o a un centroide de municipio | `parcelas_validadas.gpkg` | Solo si se usa un modelo espacial; riesgo de fuga entre entrenamiento y predicción |

## Cuidados generales antes de modelar

- **Normalizar `Cultivo`** ("Cebada" vs "CEBADA") y reparar AGC_070 y AGC_078 con `st_make_valid()` si se usa la
  geometría.
- **Truncar o tratar el LAI negativo** de forma explícita y documentada.
- **Fuga de información:** si las variables se eligen mirando la correlación con el rendimiento, hacerlo dentro de
  cada partición de validación, no con todo el entrenamiento, porque con 138 parcelas el sobreajuste es fácil.
- **Validación:** los vecinos comparten clima; una validación cruzada al azar será optimista. Decidir en equipo si
  se valida por grupos de municipio (más estricta, pero con varios municipios de 1–5 parcelas).
- **Comparar contra una línea base** con solo `reg_estado`: cualquier variable nueva debe mejorar esa base para
  justificar su inclusión.
- **Documentar cada variable** con su ventana, su sensor y su origen.

## Propuesta de orden de trabajo (para discutir)

1. Línea base con región (#1) y control de calidad de los datos (cuidados).
2. Ventanas climáticas y anomalías (#2, #3) y compuestos satelitales por sensor (#4, #5).
3. Con eso, primer modelo y evaluación de qué aporta cada familia por encima de la región.
4. Solo entonces, ampliar con #6–#11 lo que muestre valor.
