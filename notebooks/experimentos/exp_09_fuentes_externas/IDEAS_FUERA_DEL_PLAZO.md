# Ideas que no caben en jueves–viernes (lista aparte)

8 de octubre de 2026. Están ordenadas por **valor esperado / esfuerzo** según el diagnóstico de EXP_08. Ese diagnóstico mostró que el error que queda está entre parcelas vecinas del mismo municipio, que los agregados satelitales no muestran señal individual y que afinar hiperparámetros con 138 parcelas empeora.

Ninguna entra a la decisión del modelo sin pasar por el mismo protocolo: receta fija antes de ver etiquetas, MIX como referencia y nulo por permutación.

## Pueden arrancar en paralelo (1–2 días, otra persona)

| Idea | Qué aporta | Por qué podría valer la pena | Riesgo / límite | Perfil sugerido |
|---|---|---|---|---|
| **Intervalos de predicción por parcela** (conformal o cuantiles OOF) | No baja el RMSE; mejora el **producto** (30 % de la app): rango creíble por parcela | Un analista de crédito necesita incertidumbre, no solo un número. Ya tenemos 1,380 OOF por modelo para calibrarlos. | Cobertura empírica con 138 parcelas, no garantía para las 59 | Software / estadística |
| **Respuesta a las preguntas bonus de clima e índices** con evidencia | Narrativa defendible ante el jurado | EXP_08 ya da la respuesta central: el territorio domina; el satélite solo aporta como contraste vecinal. Falta el análisis explicativo de clima entre municipios (CHIRPS/ERA5). | Es explicativo, no predictivo; no mezclar con la selección del modelo | Economía (Jared/Dafne) |
| **Etiquetas redondeadas como intervalos** (modelo con censura: 3.0 = [2.75, 3.25)) | Medias municipales mejor estimadas en Calpulalpan/Singuilucan | Representa honestamente la precisión distinta por procedencia | Ganancia en RMSE probablemente pequeña; el jurado lo valoraría como rigor | Estadística / econometría |
| **Preguntar a FIRA** por fechas de siembra, productor o unidad de manejo y método de medición | Podría explicar la variación dentro de Chignahuapan | La dependencia espacial de <500 m sugiere productores o manejo compartidos | Puede no haber respuesta antes del 19 | Coordinación |

## Requieren más de una semana o tienen bajo retorno esperado con n = 138

| Idea | Por qué no ahora |
|---|---|
| **SCYM** (Lobell et al., 2015): entrenar con simulaciones de un modelo de cultivo (AquaCrop/DSSAT para cebada) en lugar de etiquetas | Requiere calibrar el modelo de cultivo a Valles Altos: suelos, variedad, fechas. Son semanas, aunque es la vía clásica cuando hay pocas etiquetas. |
| **Afinar modelos fundacionales** (Prithvi-EO en Hugging Face) | Con 138 etiquetas, afinar un modelo grande sobreajusta. Los embeddings AlphaEarth (K4 de EXP_09) dan la misma idea lista para usar. |
| **Modelo a nivel píxel** (aprendizaje de instancias múltiples: una etiqueta por bolsa de píxeles) | La heterogeneidad intra-parcela (EXP_07) no mostró señal; gran esfuerzo para poca evidencia previa. |
| **DEM de 15 m o LiDAR de INEGI**: posición topográfica y bolsas de helada | Descarga manual y procesamiento. La topografía de 120 m no mostró señal en el barrido, pero la resolución podría ser el problema. Bajo–medio. |
| **Clima diario** (ERA5-Land: heladas, grados-día) para predecir | Resolución de 9–25 km: no distingue vecinas. Útil para la narrativa, no para bajar el error. |
| **Rendimientos municipales SIAP** | Nivel municipal (ya está en MUN); usar el mismo año sería fuga. |

## Referencias

Lobell, D. B., Thau, D., Seifert, C., Engle, E., & Little, B. (2015). A scalable satellite-based crop yield mapper. *Remote Sensing of Environment, 164*, 324–333. https://doi.org/10.1016/j.rse.2015.04.021
