# Reto AgroCebada FIRA 2026, equipo Beluga: carpeta FINAL

> **Primero lee `00_EMPIEZA_AQUI_guia_de_codigos.docx`**: explica qué hace cada código y cada archivo, uno por uno.

FINAL es la versión cerrada del proyecto, con el mismo orden y la misma lógica de la carpeta "para el equipo", pero con el código nuevo en **Python**. Junta todo lo que se hizo para predecir el rendimiento de cebada: desde el análisis de los datos y la investigación de agronomía hasta las 59 predicciones. Está pensada para que alguien que no vio el proyecto pueda entenderlo y repetirlo. Todo lo de aquí son copias o archivos nuevos: los archivos originales siguen intactos en `preparacion\` y `outputs\`.

## De qué trata el reto

Hay 197 parcelas de cebada de Puebla, Hidalgo y Tlaxcala, con datos de satélite, clima (celdas de unos 5.5 km) y topografía del ciclo abril a octubre de 2025. De 138 parcelas sabemos el rendimiento (toneladas por hectárea, t/ha) y de 59 está oculto. El trabajo es **predecir el rendimiento de esas 59**. La entrega es el 19 de octubre de 2026.

## Qué hicimos, en una página

1. **Conocer los datos** (`01_datos/eda_inicial/`). Se revisó cada fuente.
2. **Investigar agronomía** (`03_hipotesis_y_variables/agronomia/`). Cinco hojas sobre cómo crece la cebada y qué la daña, para proponer variables con sentido.
3. **Decidir cómo medir el error** (`02_validacion_y_lineas_base/`). Se aparta una parte de las 138 parcelas, se predice y se mide el error (RMSE en t/ha; menor es mejor). Tres esquemas: V1 (el principal), V2 (más difícil, aparta celdas climáticas completas) y V3 (deja fuera un grupo regional).
4. **Fijar las líneas base.** **B2**, la media de cada grupo regional, es la principal. B3 usa la media de la celda climática.
5. **Probar 148 variables con una regla escrita antes** (`03_hipotesis_y_variables/`). La regla **E1** dice que una variable sirve si baja el error de B2 en más de 0.02 t/ha, lo hace en al menos 75 de 100 particiones de V1 y no empeora en V2. Se hizo también un control de permutación.
6. **Probar candidatos más complejos** (filas E6 y E7 del registro): residuo por celda, ridge y árboles. Ninguno superó al modelo simple con la regla escrita antes.
7. **Elegir el modelo final** (`05_modelo_final/`): grupo más una variable (`anom_precip_pct_d`, la anomalía de lluvia de octubre).
8. **Predecir las 59 parcelas** (`06_prediccion/`).
9. **Comparar con el trabajo de otras personas** (`02_validacion_y_lineas_base/scripts/comparar_modelo_externo.py`): mide cualquier modelo con las mismas particiones y la misma regla E1.

## Resultado principal

RMSE en t/ha, media de 100 particiones (menor es mejor):

| Modelo | V1 | V2 |
|---|---|---|
| B2, media por grupo (línea base) | 0.5021 | 0.5237 |
| B3, media por celda climática | 0.4989 | 0.5237 |
| Modelo final (grupo más una variable) | 0.4734 | 0.4679 |

De 150 pruebas, 13 variables pasan E1, 1 pasa solo con vecinas y 136 se descartan. El modelo final mejora a B2 en 86 de 100 particiones de V1 y 94 de 100 de V2, pero la mejora es pequeña (0.03 t/ha) frente a un error de 0.47 a 0.50 t/ha. B3 no pasa E1. Los candidatos nuevos (C1 a C5) no superan al modelo final.

## Python contra R

Los resultados de B0 a B3, de las 150 pruebas de variables, de la selección dentro de partición y del modelo final (las 59 predicciones y los coeficientes) **salen iguales** que en R. Cada script de Python lo comprueba al final contra los CSV que produjo R (guardados en `04_resultados/referencia_R/`). Hay dos diferencias que conviene conocer:

* **Controles de permutación.** Python y R generan números al azar distintos, así que esos números cambian un poco (ver `03_hipotesis_y_variables/LEEME.md`). La conclusión no cambia.
* **Lo que sigue en R.** La limpieza (10), las particiones (20) y las variables (51 a 55) siguen en R, en `03_hipotesis_y_variables/scripts_R_origen/`, y sus resultados vienen ya hechos. Rehacerlos en Python con otro generador de azar habría cambiado las particiones y las cifras ya registradas. Los rasters tampoco se copiaron por su tamaño.

## Lo que no hay que olvidar

* **Las 13 variables son pocas señales repetidas.** Solo hay 23 celdas climáticas en el entrenamiento, y las anomalías climáticas son casi etiquetas de celda (entre 98.9% y casi 100% de su variación se explica con la celda). No son 13 hallazgos independientes.
* La variable del modelo final no tenía signo registrado: es un **hallazgo exploratorio**, no una hipótesis confirmada. Las variables son candidatas, no causas.
* Solo hay una temporada (2025), la más lluviosa de la serie.
* El error esperado es el RMSE de V1 y V2, no un intervalo de confianza.
* **[incierto]** El formato de entrega de las predicciones no aparece en las bases ni en las reglas del reto. Se usó de forma provisional el del CSV base. Hay que confirmarlo con los organizadores antes del 19 de octubre. El borrador del mensaje no se envió.
* **[incierto]** La referencia "MIX" de otra persona del equipo no está en el proyecto, así que no se pudo comparar. El comparador está listo para medirla.
* Las familias de variables satelitales no promedian igual (la 53 promedia medianas mensuales; la 54 y la 55 promedian observaciones). Está documentado y no se unificó.

## Cómo recorrer la carpeta

| Carpeta | Qué hay |
|---|---|
| `01_datos/` | Las bases (originales, derivadas y preparadas), el diccionario de variables y el EDA inicial |
| `02_validacion_y_lineas_base/` | Esquemas V1, V2 y V3, líneas base B0 a B3, el módulo común `comun.py`, el comparador de modelos y los documentos de plan y contexto |
| `03_hipotesis_y_variables/` | Agronomía, registro de hipótesis (hasta la fila E7), las 148 variables, scripts 60 y 70 en Python y los de R de origen |
| `04_resultados/` | Tablas y gráficas clave, resultados de los scripts y `referencia_R/` |
| `05_modelo_final/` | El script del modelo final y el criterio con el que se eligió |
| `06_prediccion/` | Las 59 predicciones |
| `07_orden_de_ejecucion.md` | El orden numerado de los scripts, con entradas y salidas |
| `requirements.txt` | Paquetes de Python que se necesitan |

## Cómo repetirlo

Desde esta carpeta, con `pip install -r requirements.txt` hecho una vez y siguiendo `07_orden_de_ejecucion.md`. Para solo obtener las predicciones a partir de lo ya calculado: `python 05_modelo_final/modelo_final.py`.

## Palabras que se usan

| Palabra | Qué significa |
|---|---|
| RMSE | El error típico de las predicciones, en t/ha. Menor es mejor |
| Línea base | Un modelo simple contra el que se compara. Si una variable no lo mejora de forma clara, no sirve |
| Partición | Una división de las 138 parcelas en "ajuste" (para entrenar) y "validación" (para medir el error) |
| Celda climática | Un cuadro de unos 5.5 km donde el clima vale casi lo mismo. Parcelas vecinas comparten celda |
| Grupo | Una de las 5 regiones de trabajo: Chignahuapan, Tlaxcala, Singuilucan, Almoloya y Otros_Hidalgo |
| Anomalía | Qué tan distinto fue 2025 frente al promedio de 2022 a 2024 |
| [CP], [V], [V-parcial], [PV] | Marcas de las hojas de agronomía: cálculo propio, verificado, verificado en parte y por verificar |
