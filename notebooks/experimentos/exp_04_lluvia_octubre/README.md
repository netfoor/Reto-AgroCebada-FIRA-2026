# EXP_04 · Lluvia de octubre y agrupación territorial

Abrir [exp_04_lluvia_octubre.ipynb](exp_04_lluvia_octubre.ipynb). Es el recorrido autónomo de V2: **píxeles y áreas → lluvia ponderada → referencia histórica → anomalías → procedimientos → evaluación y reservas**. No necesita Git, ZIP externo, Drive ni ejecutar otro notebook.

## Qué se pregunta

¿La lluvia de octubre y su desviación respecto de 2022–2024 aportan información al rendimiento?, ¿cambia el resultado al agrupar municipios? La hipótesis proviene de exploraciones de Jared con las mismas etiquetas: el registro previo a V2 no la convierte en una prueba confirmatoria independiente.

La media histórica H, la anomalía absoluta `P2025 − H` y la porcentual `100 × (P2025 − H) / H` se calculan visiblemente. Tres años de referencia no son una climatología de largo plazo. El contraste porcentual frente a absoluto no aísla el papel incremental de H.

## Qué ocurre al ejecutar

El lector muestra la ponderación por área de una parcela y generaliza a las 197. Usa **230 áreas de intersección históricas** y **116 valores de píxel derivados de los GeoTIFF originales el 8 de octubre**, para recalcular **788 lluvias parcela–año** y las variables de octubre. **No vuelve a ejecutar las intersecciones geoespaciales.** Reproducir esta aritmética no es una segunda verificación completa desde GeoTIFF; ambos soportes conservan procedencia, tamaño y SHA-256 propios. Solo el recorte de valores de píxel es nuevo: no se le atribuye una fecha previa al entrenamiento.

Se evalúan **13,800 OOF guardadas de diez procedimientos**, con 138 etiquetas y 1,380 OOF por procedimiento. Cinco son candidatos históricos: J5_PCT/J9_PCT (OLS, cinco/nueve grupos) y R9_PCT/R9_MM/R9_RAW (regularización municipal, anomalía porcentual/absoluta/lluvia actual). GLOBAL, MUN, MIX, G5 y R_B se mantienen como comparadores.

Se comprueban **200 selecciones** desde **1,150 scores internos guardados**: 150/900 de los candidatos Ridge y 50/250 del control R_B. **Hace cero ajustes de modelos.** No recalcula esos scores, no reconstruye nuevas predicciones y no genera las 59 de entrega. Las operaciones científicas permanecen visibles; preparar dependencias solo opera en Colab y solicita reinicio manual cuando corresponde.

La ejecución histórica usó Python **3.12.3/scikit-learn 1.9.1**; esta lectura usa Python 3.13. Coincidir en métricas desde OOF conservadas no demuestra paridad del entrenamiento entre entornos. Las mismas particiones exteriores e interiores se conservan sin regenerar semillas ni buscar variantes.

## Resultado y límites

J5_PCT cumple la regla original en **FULL138**, ambas condiciones en **10/10** repeticiones: RMSE 0.4797 frente a MIX 0.4938 t/ha; MAE 0.3291 frente a MUN 0.3354. Es un candidato exploratorio **con reservas, no un modelo final**.

El diagnóstico **posterior SEEN135** conserva 1,350 OOF por procedimiento, sin reentrenar: mejora RMSE frente a MIX en 8/10 repeticiones, pero no cumple la condición MAE frente a MUN en ninguna. No revoca el cumplimiento registrado ni equivale a la evaluación sobre las 59 ocultas. AGC_120, en Nanacamilpa, carece de un caso OOF equivalente con su única etiqueta municipal presente.

La fe de erratas acompaña los resultados: R9_PCT mejora RMSE a costa de MAE frente a R9_MM, no es superior en general. J5 frente a J9 cambia conjuntamente medias, residuos, escala y respaldos, no aísla una causa. La mejora se concentra en pocas parcelas y no demuestra un efecto causal de la lluvia. Las etiquetas ocupan **23 celdas por centroide**, pero reciben aportaciones de **27 píxeles**; el conjunto completo recibe 29. Son conteos distintos, no una estimación de tamaño muestral efectivo.

Trabajo V2 y cierre: **01/10/2026**. Adaptación del lector: **08/10/2026**. No es una ronda nueva ni un registro previo retrospectivo.

## Ejecución local

Desde la raíz del proyecto:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_04.py
```

El ejecutor guarda una carpeta nueva en `resultados_locales/exp_04_lluvia_octubre/`. El generador es `scripts/construir_exp_04.py`, el contrato `config/exp_04_lluvia_octubre.json` y las pruebas específicas `tests/test_exp_04.py`. La distribución local es `artefactos_locales/exp_04_lluvia_octubre_equipo.zip`.

Verificación local: **497 pruebas pasan, 94 específicas de EXP_04**; Ruff pasa sobre scripts/tests. Dos kernels nuevos con solo el notebook producen 39 salidas y dos figuras idénticas, normalizando únicamente la fecha de ejecución. Son 36 celdas, 19 de código: dos técnicas plegadas y 17 visibles. **No hay confirmación de ejecución en Colab real.** Las fuentes históricas y los cuadernos anteriores se conservan sin cambios.
