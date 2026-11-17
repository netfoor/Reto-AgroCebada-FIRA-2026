# Plan de trabajo — Reto AgroCebada FIRA 2026

Borrador para discutir con el equipo. Objetivo: entender bien los datos y la agronomía de la cebada **antes** de
modelar, y usar la IA como acelerador y revisor, no como piloto automático. El dashboard se mantiene en un mínimo
viable (Fase 5).

Se apoya en `outputs/eda/` y en los tres documentos previos de esta carpeta. No hay fechas porque falta la fecha
de entrega (ver "Decisiones abiertas").

## Punto de partida (cifras ya verificadas)

- 138 parcelas de entrenamiento, 59 ocultas, split estratificado por región. Evaluación: 70% modelo, 30% dashboard.
- **El Estado solo explica ~50% de la varianza (R² = 0.503).**
- **Corrección a lo que se dijo antes:** Tmin (+0.61) no es un efecto térmico a nivel parcela. Dentro de cada Estado
  su correlación es casi cero (−0.07 a −0.12); marca la región. La lluvia (−0.47) depende de un solo municipio
  (Singuilucan): en Hidalgo pasa de −0.65 a +0.35 al quitarlo.
- El clima viene en celdas de ~5.5 km (~50 valores distintos para 197 parcelas). Vecinos comparten clima.
- Consecuencia: **la pregunta central es qué explica la diferencia entre parcelas de una misma región**, y ahí el
  clima grueso ayuda poco. El satélite, el manejo y la fenología pesan más de lo que parecía.

## Reglas de trabajo

1. Toda variable se evalúa **por encima de la línea base regional**, no contra cero.
2. Validación agrupada por zona, repetida con varias semillas. Nunca CV aleatoria.
3. Selección de variables **dentro** de cada partición (con 138 filas, elegir mirando todo el entrenamiento es fuga).
4. Cada hipótesis se escribe antes de probarla (qué variable, qué signo, por qué agronómicamente).
5. Un registro de experimentos: fecha, variables, esquema de CV, resultado, decisión. Semillas y folds fijos.
6. Datos originales de solo lectura; productos nuevos en carpeta nueva.

---

## Fase 0 — Comprender agronomía y datos (paralela a la Fase 1)

Cada bloque termina con un producto concreto (una hoja de una página y una lista de hipótesis medibles con los datos
que tenemos), para que el estudio alimente las variables y no se quede en teoría.

### Bloque A — Fisiología y fenología de la cebada
- Etapas (escala Zadoks/Feekes): emergencia, macollaje, encañado, espigado, floración, llenado de grano, madurez.
- Qué determina el rendimiento: espigas/m², granos/espiga, peso de mil granos; en qué etapa se define cada uno.
- Duración aproximada de cada etapa y cómo cambia con fecha de siembra y temperatura.
- **Producto:** línea de tiempo del ciclo con etapas críticas y qué estrés daña cada una.

### Bloque B — Requerimientos y estreses climáticos
- Temperatura óptima por etapa; heladas (tempranas y en espigado), calor en llenado de grano.
- Déficit hídrico vs exceso de humedad (encharcamiento, enfermedades favorecidas por lluvia).
- Radiación y amplitud térmica; efecto de la altitud.
- **Producto:** tabla etapa → variable climática relevante → signo esperado → limitación de nuestros datos mensuales.

### Bloque C — Sanidad, manejo y calidad maltera
- Enfermedades principales de la cebada en el Altiplano (roya, mancha reticulada, escaldadura, fusarium; verificar
  cuáles aplican a Tlaxcala, Puebla e Hidalgo) y su relación con lluvia y humedad.
- Fecha de siembra, variedad, fertilización nitrogenada, densidad, temporal vs riego, rotación.
- La cebada es maltera: exceso de nitrógeno o de humedad afecta la calidad y puede afectar decisiones de manejo.
- **Producto:** lista de factores de manejo que **no** están en los datos y explican gran parte de la variación
  entre parcelas vecinas (útil para las preguntas a organizadores y para redactar limitaciones).

### Bloque D — Contexto regional
- Zonas cebaderas de Hidalgo (Llanos de Apan, Singuilucan), Tlaxcala y Puebla: altitud, suelos, régimen de lluvias.
- Por qué Singuilucan (1135–1335 mm, 3.08 t/ha) se comporta distinto: ¿suelo, altitud, manejo, variedad?
- **Producto:** una ficha por municipio con lo que se sabe y lo que hay que preguntar.

### Bloque E — Cómo se miden las cosas (teledetección y datos)
- NDVI, EVI, SAVI, MSAVI, LAI: qué miden, cuándo saturan, cómo cambian con el suelo desnudo y con la senescencia.
- Sentinel-2, Landsat y Planet: resolución espacial, frecuencia de paso, por qué las nubes dejan huecos de
  junio a octubre (temporada de lluvias).
- CHIRPS (lluvia por satélite), CHIRTS-ERA5 (temperatura) y DEM de 120 m: su resolución real y por qué dos parcelas
  vecinas reciben el mismo valor.
- **Producto:** una hoja "qué puede y qué no puede decir cada fuente".

### Bloque F — Estadística para n pequeño (lo de las recomendaciones)
- Validación agrupada y espacial, fuga de información, sobreajuste con 138 filas.
- Regularización (ridge/elastic net), árboles con poca profundidad, ensambles modestos, efectos mixtos por región.
- Incertidumbre: intervalos por parcela (cuantiles, conformal) y cómo reportar el error esperado.
- **Producto:** un esquema de validación escrito y aprobado por el equipo (ver Fase 1).

**Cómo estudiar con la IA:** pedirle que explique cada bloque y luego que te haga preguntas de repaso; comparar sus
afirmaciones con fuentes (INIFAP, FIRA, SIAP, artículos de cebada maltera) antes de darlas por ciertas. Marca cada
dato agronómico como "verificado con fuente" o "por verificar". Los rangos numéricos (días por etapa, umbrales de
helada) los dejo sin fijar hasta contrastarlos.

## Fase 1 — Línea base y esquema de validación

- Decidir el esquema de CV agrupada (por municipio o por zona; ojo con municipios de 1–5 parcelas).
- Línea base 1: media global. Línea base 2: solo `reg_estado`. Línea base 3: estado + municipio agrupado.
- Definir la métrica (RMSE, MAE, R²) y cuál se reporta como principal.
- Limpieza: normalizar `Cultivo`, reparar AGC_070 y AGC_078 (`st_make_valid()`), tratar el LAI negativo.
- **Salida:** cuánto error queda por explicar dentro de cada región. Ese es el objetivo real del modelado.

## Fase 2 — Ingeniería de variables (según `02_ideas_feature_engineering.md`)

Orden: P1 (#1–#5), luego P2 (#6–#11) solo si hay tiempo.

- Cada variable entra con hipótesis escrita (Fase 0) y se evalúa contra la línea base, dentro de la CV.
- Variables satelitales: compuestos sin nubes por mes, sufijos de sensor, conteo de meses válidos.
- Variables climáticas: ventanas fenológicas y anomalías, sabiendo que heredan la resolución de 5.5 km.
- Extra a considerar dado el hallazgo de confusión regional: residuos de rendimiento respecto a la región como
  variable objetivo auxiliar para ver qué explica la variación **dentro** de cada zona.

## Fase 3 — Modelado

1. Modelo lineal regularizado con región + un puñado de variables.
2. Random forest / GBM poco profundos como comparación.
3. Ensamble simple solo si mejora bajo la misma CV.
4. Descartar todo lo que no supere la línea base regional de forma consistente entre semillas.

## Fase 4 — Interpretación y robustez

- Leave-one-cluster-out: ¿el modelo sobrevive si se quita un municipio? (el caso Singuilucan).
- Importancia de variables y dependencia parcial, comparando con lo que dice la agronomía.
- Estimar el error esperado en las 59 parcelas ocultas a partir de la CV, con intervalo.
- Enfoque causal (`03_ideas_efecto_causal.md`) solo como análisis exploratorio, sin afirmar causalidad.

## Fase 5 — Entrega

- Predicciones finales para las 59 parcelas, reproducibles desde un script único.
- **Dashboard mínimo viable** (tú lo has marcado como no prioritario, pero es 30% de la nota, así que conviene
  repartirlo): mapa de parcelas con predicción, tabla con intervalo, 3–4 variables clave y una sección de
  limitaciones. Idealmente lo toma otro integrante; yo puedo ayudar con el código en R.
- Documento corto de metodología: qué se hizo, qué no funcionó, error esperado y supuestos.

## Uso de la IA por fase

| Fase | Para qué sí | Cuidado |
|---|---|---|
| 0 | Explicar, hacer preguntas de repaso, resumir literatura | Verificar cifras agronómicas con fuentes |
| 1–2 | Escribir y revisar scripts en R, revisar fuga de datos | No aceptar variables sin hipótesis previa |
| 3–4 | Comparar modelos, criticar la validación | No elegir modelo por el mejor R² de una sola semilla |
| 5 | Código del dashboard, redacción | Que el equipo pueda explicar cada decisión |

## Preguntas pendientes para los organizadores

(De `resumen_general.md` y de la sesión previa; conviene enviarlas juntas.)
1. Fechas de siembra y cosecha, o al menos la ventana fenológica del ciclo 2025.
2. Rendimientos de años previos por parcela (si existen).
3. Regla oficial para combinar Básico y PRO (¿la fusión está permitida?).
4. Fuente oficial del área de parcela y del LAI negativo.
5. Registros de eventos climáticos (heladas, granizo, sequía) de 2025.
6. Variedad, sistema (temporal/riego) y manejo si están disponibles.

## Decisiones abiertas (necesito tu respuesta)

1. **Fecha de entrega** del reto y de cualquier entrega intermedia, para poner fechas a las fases.
2. Cuánto tiempo por semana pueden dedicar tú y tu equipo, y quién toma qué (por ejemplo, a quién asignar el dashboard).
3. Si el equipo tiene acceso a alguien con conocimiento agronómico (asesor, profesor, contacto de FIRA/INIFAP).
