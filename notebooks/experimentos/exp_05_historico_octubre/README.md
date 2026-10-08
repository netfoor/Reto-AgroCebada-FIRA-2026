# EXP_05 · Histórico y lluvia actual de octubre

Abrir [exp_05_historico_octubre.ipynb](exp_05_historico_octubre.ipynb). Recorrido autónomo: **cuatro lluvias → representaciones H/P/porcentaje → recetas comparables → selección guardada → errores, decisión y límites**. No requiere Git, ZIP, Drive, GeoTIFF ni ejecutar otro notebook.

## Qué se pregunta

¿El histórico corto H, la lluvia actual P o su combinación explican la señal del porcentaje? Una correlación del porcentaje con su denominador no responde por sí sola. Se compara H, P, H+P y `100 × (P − H) / H` conservando municipio, Ridge, extracción, ventana, particiones y rejilla. H resume octubre de 2022–2024: **no es una normal climatológica**. H+P es una representación aditiva; el porcentaje es una razón no lineal, no el mismo modelo expresado en otras unidades.

La pregunta procede de exploraciones con las mismas etiquetas. Registrar V3 antes de ajustar sus candidatos acota esta ronda, pero no la convierte en confirmación independiente.

## Qué ocurre al ejecutar

El lector calcula visiblemente las variables de **197 parcelas desde cuatro lluvias guardadas por parcela** y comprueba el control histórico después. No vuelve a extraer rásteres ni intersectar geometrías. Contiene **21 insumos** con tamaño y SHA-256.

Evalúa **9,660 OOF guardadas de siete procedimientos**: R9_H/R9_HP/R9_P/R9_PCT, MUN/MIX y el candidato histórico J5_PCT. Verifica **200 selecciones de alpha desde 1,200 scores guardados**; no recalcula esos scores. Parámetros y predicciones son evidencia histórica, no entradas para entrenar otro modelo. **Cero ajustes y ninguna predicción final de las 59 parcelas.**

El presupuesto original fue 4,800 evaluaciones internas —800 baseline y 4,000 ajustes Ridge— y 200 reajustes exteriores; las 34 pruebas históricas y nueve autopruebas del cuaderno original se citan por separado. La ejecución original usó Python **3.12.14**; este lector usa Python 3.13. Coincidir en variables y métricas conservadas no demuestra paridad del entrenamiento entre entornos.

## Qué concluye

**Ninguna receta avanza.** La regla principal exige RMSE menor que MIX y MAE no mayor que MUN, agrupados y cada condición en al menos 8/10 repeticiones. No es una prueba de significancia ni la fórmula oficial de calificación de FIRA.

En **SEEN135, el escenario principal fijado para V3**, el porcentaje obtiene RMSE 0.4851 t/ha frente a MIX 0.4872, pero mejora solo en 6/10 repeticiones; MAE 0.3247 frente a MUN 0.3213, peor. H tiene RMSE 0.4946; H+P, 0.4931. Añadir P a H reduce poco RMSE y empeora MAE. Ambos quedan detrás del porcentaje en RMSE: esto cuestiona que H sola explique su capacidad predictiva, sin demostrar inutilidad general del histórico o del clima.

SEEN135 conserva 1,350 OOF/procedimiento sobre 135 parcelas repetidas, no observaciones independientes. **FULL138 es secundario**, 1,380 OOF/procedimiento. La máscara principal deriva de IDs, municipios y particiones, sin mirar errores y sin retirar etiquetas del entrenamiento. La decisión se tomó después de V2, sin cambiar retrospectivamente su veredicto. No equivale a las 59 ocultas: Nanacamilpa tiene una sola etiqueta, AGC_048, para AGC_120 y carece de un caso OOF equivalente.

MUN/MIX permanecen como referencias; J5_PCT se conserva como candidato histórico con reservas. No se rescata una receta eligiendo otra población, suprimiendo parcelas o buscando nuevas variantes. Se muestran colinealidad, concentración y soporte territorial como diagnósticos, no como causas agronómicas ni estimaciones de tamaño muestral efectivo.

Diseño y ejecución: **01/10/2026 México, 02/10/2026 UTC**. Adaptación: **08/10/2026**. R1 corrigió un control que leía `alpha` en vez de `alpha_estado`; el intento inicial se detuvo antes de ajustar H/HP. No cambió la hipótesis ni se borró ese antecedente.

## Ejecución local

Desde la raíz del proyecto:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_05.py
```

Se guarda una carpeta nueva en `resultados_locales/exp_05_historico_octubre/`. Generador: `scripts/construir_exp_05.py`; contrato: `config/exp_05_historico_octubre.json`; pruebas específicas: `tests/test_exp_05.py`; distribución local: `artefactos_locales/exp_05_historico_octubre_equipo.zip`.

**Verificación local cerrada:** 580 pruebas (83 de EXP_05) y Ruff pasan. Dos kernels nuevos reproducen 35 salidas y dos figuras, salvo fecha. 37 celdas, 19 de código: dos bloques técnicos plegados y 17 visibles. **No se ha probado este lector en Colab real.**

El R² municipal sin variación del objetivo se muestra como NaN: corrige la presentación de 14 valores espurios de Tepeapulco por redondeo, sin cambiar los CSV, OOF, RMSE, MAE ni decisiones originales.
