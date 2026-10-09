# EXP_06 · Fecha de pico NDVI con soporte

Abrir [exp_06_pico_soportado.ipynb](exp_06_pico_soportado.ipynb). Recorrido autónomo: **capturas → NDVI diario → suavizado por días → guardas de soporte → sustituir una variable → selección guardada → errores, decisión y límites**. No requiere Git, ZIP, Drive ni ejecutar otro notebook.

## Qué se pregunta

¿La fecha de una curva suavizada y suficientemente observada mejora E2 frente a la fecha de su máximo crudo? Se sustituye **solo la fecha de pico NDVI Planet**: quedan iguales las otras cinco variables numéricas, municipio, Ridge, particiones y rejilla. La bandera de soporte es un diagnóstico, **no un predictor adicional**. No se añaden anchura ni otras variables fenológicas.

La receta promedia los valores finitos de cada día y toma una mediana centrada de **±7 días de calendario**, con al menos tres días finitos. No interpola una curva diaria ni filtra nubes. Las guardas controlan días disponibles, huecos, cobertura temporal, amplitud, meseta ambigua, censura y soporte bilateral. Son reglas operativas propias: no certifican fechas de floración o cosecha.

## Qué ocurre al ejecutar

El lector reconstruye la fecha desde **26,255 capturas Planet** de abril–octubre de 2025, para las 197 parcelas. Primero calcula; después compara curvas y descriptores históricos. Incorpora **24 insumos** con tamaño y SHA-256. El recorte se preparó el **8 de octubre**, con procedencia y hash propios; no se presenta como archivo registrado antes de V4.

Resultan **158 fechas soportadas y 39 ausencias**, 30 entre las etiquetas y nueve entre las ocultas. No se eliminan parcelas: el procedimiento original imputó la mediana aprendida exclusivamente en cada entrenamiento. Municipio se codifica one-hot y también se penaliza con Ridge; E2 no equivale a la media municipal MUN.

Se evalúan **6,900 OOF guardadas de cinco procedimientos**: E2, V4, GLOBAL, MUN y MIX. Se verifican **100 selecciones desde 500 scores guardados**, con control de E2 anterior. Los scores no se recalculan desde errores internos y no se vuelven a producir las OOF. **Cero ajustes actuales y ninguna predicción final de las 59 parcelas.**

Factibilidad: **02/10/2026**. Registro y ejecución V4: **06/10**. Adaptación: **08/10**. El presupuesto original fue **2,100 ajustes por corrida**, 1,050 de E2 y 1,050 de V4. Dos corridas para comprobar determinismo sumaron 4,200 ajustes físicos, no dos candidatos. El original usó Python **3.12.14**; el lector usa Python 3.13 y no acredita paridad de entrenamiento entre entornos.

## Qué concluye

**Se mantiene cerrado sin adopción.** En SEEN135, el escenario principal fijado para V4, RMSE baja de E2 **0.5065 a V4 0.5015 t/ha**, pero MAE empeora ligeramente: **0.3474 → 0.3476**. MIX obtiene RMSE **0.4872** y MUN MAE **0.3213**. V4 mejora RMSE frente a E2 en 9/10 repeticiones; frente a MIX, en ninguna. No cumple la regla conservadora, que no es una prueba de significancia ni la fórmula oficial de calificación de FIRA.

La mejora frente a E2 se concentra en pocas parcelas: al retirar solo de la evaluación las cinco más favorecidas, V4 queda peor que E2. No se usa esta sensibilidad para escoger una nueva receta ni quitar etiquetas del entrenamiento. En Chignahuapan sigue por detrás de MIX. Una curva más interpretable no implica una predicción mejor.

SEEN135 conserva **1,350 OOF por procedimiento** y FULL138, como secundario, **1,380**. Las diez repeticiones no crean nuevas etiquetas independientes. La máscara principal utiliza IDs, municipios y particiones, no errores; no modifica el entrenamiento. No equivale a la entrega: AGC_120 en Nanacamilpa no tiene un caso OOF equivalente con su única etiqueta municipal presente.

Suavizado, guardas y ausencias cambian conjuntamente; este diseño no permite atribuirles efectos por separado. Una sola campaña y la exploración previa con las mismas etiquetas limitan la inferencia. No se demuestra inutilidad general de la fenología, causalidad ni extrapolación a otras regiones.

## Ejecución local

Desde la raíz del proyecto:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_06.py
```

Se guarda una carpeta nueva en `resultados_locales/exp_06_pico_soportado/`. Generador: `scripts/construir_exp_06.py`; contrato: `config/exp_06_pico_soportado.json`; pruebas específicas: `tests/test_exp_06.py`; distribución local: `artefactos_locales/exp_06_pico_soportado_equipo.zip`.

**Verificado localmente sin reentrenar:** suite completa de 665 pruebas (85 específicas), Ruff y dos kernels nuevos con solo este notebook. Las 36 salidas y dos figuras coinciden salvo fecha; 36 celdas, 20 de código, solo dos técnicas plegadas. **Colab real no probado.** Esta es la sexta lectura de las seis rondas históricas; no crea un experimento nuevo.
