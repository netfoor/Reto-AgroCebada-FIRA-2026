# Ideas iniciales sobre efecto causal — precipitación y rendimiento

**Estado de este documento:** puntos de partida para discutir con For y Daf, no un análisis decidido ni un
resultado. Ninguna de las opciones se ha ejecutado.

## 1. La pregunta

En las 138 parcelas de entrenamiento, la lluvia acumulada del ciclo (abril–octubre 2025) se correlaciona
**negativamente** con el rendimiento (r = −0.469). Es contraintuitivo: se esperaría que más lluvia ayudara a un
cultivo de temporal. ¿La lluvia *causa* menor rendimiento (anegamiento, enfermedades fúngicas, pérdida de
nitrógeno), o la correlación refleja otra cosa?

## 2. Qué dicen los datos hoy, con honestidad

**Lo que sí sabemos**
- La correlación es −0.469 con las 138 parcelas de entrenamiento y es el número del EDA original.
- 2025 fue el año más lluvioso de la serie: en abril–octubre, ~531 mm en 2022, ~541 en 2023, ~938 en 2024 y ~963
  en 2025 (medias entre parcelas, calculadas de `precipitacion_mensual_por_parcela.csv`).

**Lo que complica una lectura causal**
- 🆕 **La región confunde.** El Estado solo explica ~50% de la varianza del rendimiento (Puebla 4.48, Hidalgo
  3.76, Tlaxcala 2.98 t/ha). La lluvia media del ciclo también difiere por Estado (Puebla 881 mm, Hidalgo 1,045,
  Tlaxcala 1,004), pero no en el mismo orden que el rendimiento (Tlaxcala llueve más que Puebla, y rinde mucho
  menos). Puebla es en la práctica un solo municipio (Chignahuapan, 71 de 71 parcelas de entrenamiento y 29 de
  29 en predicción).
- 🆕 **Dentro de cada región la relación es inestable.** Al comparar dentro de Estado: Tlaxcala +0.08, Puebla
  −0.23 (rango angosto, 794–961 mm) e Hidalgo −0.65. Pero en Hidalgo casi todo viene de un solo municipio: sin
  Singuilucan (16 parcelas, 1,135–1,335 mm, rendimiento medio 3.08) la correlación pasa a **+0.35**. Un solo
  grupo de parcelas vecinas (probablemente compartiendo celdas de lluvia y también manejo, suelo o variedad)
  está moviendo el resultado.
- 🆕 **Agregar lluvia a un modelo con Estado mejora poco pero algo** (R² de 0.503 a 0.566). Puede haber una señal
  real, pero es mucho más pequeña que el −0.47 inicial y no está probada como causal.
- **Resolución de la lluvia:** celdas de ~5.5 km, ~53 valores distintos para 197 parcelas. Es una variable de
  "zona", no de parcela. Dos parcelas vecinas con manejos muy distintos reciben exactamente la misma lluvia.
- **Datos observacionales:** nadie asignó la lluvia; llegó según la ubicación. Las parcelas que reciben más lluvia
  difieren en muchas cosas que no vemos (suelo, drenaje, variedad, fecha de siembra, fertilización, agricultor).
- **Un solo ciclo con rendimiento** (2025). No hay variación temporal del rendimiento para una misma parcela.
- **138 parcelas**, muy agrupadas geográficamente, con pocos municipios y varios de 1–5 parcelas.
- **No hay una variable de tratamiento clara:** la lluvia no es una intervención, es una condición ambiental
  continua, y no tenemos las variables de manejo que la moderan (riego, drenaje, fertilización, fecha de siembra).

## 3. Marco para discutir: qué se necesita para hablar de causalidad

Un diagrama causal sencillo, para ordenar la discusión (no es un resultado):

```
Región/ubicación ──► Lluvia ─────────────────► Rendimiento
       │                                            ▲
       └──► Manejo, suelo, variedad, altitud ───────┘
```

- Si lo único que cambia entre parcelas es la región, entonces la asociación lluvia–rendimiento no separa la
  lluvia de todo lo que viene con la región.
- Para estimar el efecto de la lluvia habría que **bloquear esos otros caminos**: comparar parcelas *parecidas en
  todo lo demás* que solo difieran en lluvia, o usar variación que no dependa de la ubicación.

## 4. Tres formas de explorarlo (para discutir con For y Daf)

### Opción A — Emparejamiento (matching) o comparación dentro de estratos
- **Idea:** comparar parcelas que sean parecidas en Estado/Municipio, elevación, pendiente, temperatura y
  vegetación satelital, pero distintas en lluvia. Con 138 parcelas se puede hacer con emparejamiento simple por
  vecino más cercano o por estratos (por ejemplo, "lluvia alta vs baja" dentro de cada Estado).
- **Insumos:** `precipitacion_acumulada_ciclo_2025_por_parcela.csv`, `parcelas_atributos.csv`,
  `topografia_por_parcela.csv`, `temperatura_media_ciclo_2025_por_parcela.csv`,
  `basico_resumen_satelital_por_parcela.csv`.
- **Qué aporta:** obliga a mirar dónde hay parcelas realmente comparables y dónde no (solapamiento). Lo
  probable es que el resultado sea "no hay parcelas comparables" en varias regiones, y eso también es un hallazgo.
- **Limitaciones reales:**
  - El solapamiento entre Estados es pobre: Puebla llueve poco (794–961 mm), Hidalgo tiene el rango más amplio
    (703–1,335) y Tlaxcala llega a 1,459 mm.
  - Solo controla lo que observamos; el manejo, la variedad y el suelo siguen ocultos.
  - Con ~50 celdas de lluvia, "lluvia distinta" muchas veces significa "otra zona".
  - Los resultados serán muy sensibles a Singuilucan.
- **Chequeos mínimos:** balance de covariables antes y después de emparejar, tamaño de la muestra emparejada y
  sensibilidad al quitar Singuilucan.

### Opción B — Variación entre años como cuasi-experimento
- **Idea:** el clima sí varía entre años para la misma parcela: en abril–octubre, ~535 mm en 2022–23 y ~950 mm
  en 2024–25. Con rendimiento de varios años se podría comparar cada parcela consigo misma (efectos fijos por
  parcela), eliminando todo lo que no cambia en el tiempo: suelo, ubicación, agricultor.
- **Problema central:** solo 2025 tiene rendimiento en `ID_area_rendimiento_70_30`. Con un solo año por parcela
  no hay variación interna para estimar nada. **Con los datos actuales esta opción no es ejecutable.**
- **Lo que sí se puede hacer hoy:**
  - Preguntar a los organizadores si existen rendimientos de ciclos anteriores (2022–2024), aunque sean
    regionales o agregados.
  - Usar el satélite como *proxy* de productividad en 2022–2024 (por ejemplo, el vigor máximo del ciclo con
    Sentinel-2/Landsat) y ver si sigue la lluvia de cada año. Es un experimento débil: el índice no es
    rendimiento y hay que decirlo claramente.
- 🆕 **Advertencia para la lectura:** el orden de las parcelas por lluvia es muy estable entre años (correlación
  de 0.77–0.83 entre 2025 y cada uno de los años previos). Es decir, "más lluvia" en 2025 sigue siendo en buena
  medida "estar en la zona lluviosa", y no un factor que cambie por sí solo.

### Opción C — Quedarse en asociación y dejar claro qué faltaría
- **Idea:** con los datos actuales, lo honesto es hablar de **asociación** y no de efecto. Esto también es un
  resultado presentable en el dashboard: "la lluvia se asocia con menor rendimiento, pero en su mayoría refleja
  diferencias entre zonas".
- **Qué se puede hacer con lo que hay** (descriptivo, no causal):
  - Estimar la asociación de la lluvia **controlando por región** y reportar cuánto baja el −0.47 (por ejemplo,
    R² de 0.503 con solo Estado, 0.566 al agregar lluvia).
  - Mostrar mapas y gráficos por municipio para que se vea la estructura regional.
  - Reportar la sensibilidad a Singuilucan.
- **Qué haría falta para hablar de causalidad:**
  1. **Más ciclos con rendimiento** por parcela (panel), para usar efectos fijos por parcela.
  2. **Variables de manejo y suelo:** variedad, fecha de siembra, fertilización, riego o drenaje, tipo de suelo,
     historial de heladas o de enfermedades.
  3. **Lluvia con mayor resolución espacial** (estaciones locales o datos diarios) que distinga entre parcelas
     vecinas, y con **distribución en el tiempo** (no solo total).
  4. **Alguna fuente de variación de lluvia que no dependa de la ubicación**, o registros de eventos concretos
     (anegamiento, granizo) reportados por el productor.

## 5. Comparación rápida

| | A. Emparejamiento | B. Variación entre años | C. Solo asociación |
|---|---|---|---|
| ¿Ejecutable con los datos actuales? | Sí, con reservas | **No** (solo hay rendimiento de 2025) | Sí |
| ¿Qué controla? | Lo observado (región, topografía, clima, satélite) | Todo lo constante por parcela | Nada; describe |
| Riesgo principal | Sin parcelas comparables; manejo oculto | Falta el dato | Que se lea como causa |
| Esfuerzo | Medio | Alto si se consiguen datos | Bajo |
| Utilidad para el reto | Diagnóstico y sensibilidad | Depende de los organizadores | Explicación honesta en el dashboard |

## 6. Preguntas para la reunión

1. ¿Nos interesa el efecto causal de la lluvia por sí mismo, o solo evitar que el modelo la use mal (por ejemplo,
   que sirva de etiqueta regional)?
2. ¿Puede alguien (For o Daf) proponer un diagrama causal mejor que el de la sección 3? ¿Qué otros caminos hay?
3. ¿Preguntamos a los organizadores por rendimientos de años anteriores y por registros de manejo, heladas o
   anegamiento en 2025?
4. ¿Con cuánto esfuerzo pagamos esto frente al modelo predictivo (70% de la nota) y el dashboard (30%)? Sugerencia:
   la Opción C es barata y aporta valor al dashboard; A es un buen diagnóstico si sobra tiempo.
5. ¿Aplica el mismo cuidado a Tmin (+0.61)? Dentro de cada Estado casi desaparece, así que la misma discusión
   causal le corresponde.

---
*Cifras marcadas con 🆕: calculadas solo leyendo `outputs/derivados/`; son descriptivas, con pocas parcelas por
grupo, y no son resultados de modelado ni de inferencia causal. Los rangos de lluvia por Estado y los promedios
anuales son de las 138 parcelas de entrenamiento (rangos) y de las 197 parcelas (promedios anuales), según el
caso; ver `01_sintesis_para_equipo.md`.*
