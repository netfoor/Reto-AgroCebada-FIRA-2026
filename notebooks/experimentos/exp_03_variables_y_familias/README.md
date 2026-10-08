# EXP_03 · Variables temporales y familias de modelos

Abrir [exp_03_variables_y_familias.ipynb](exp_03_variables_y_familias.ipynb). Es el recorrido autónomo de la ronda histórica V1: **capturas → medias mensuales → cuatro variables → controles → comparación 2×2 → conclusión**. Puede compartirse y recalcularse sin Git, ZIP, Drive ni ejecutar otro notebook.

## Qué se pregunta

¿Conservar la forma temporal de las curvas añade información a seis resúmenes satelitales?, ¿cambia la respuesta con otro procedimiento? La base E2 permanece intacta; se añaden dos cambios de NDVI Planet entre bimestres, su amplitud mensual y un cambio de NDWI Sentinel-2. Cada bimestre pondera medias mensuales por días; no son etapas fenológicas verificadas. No se introducen filtro de nubes ni imputación de meses.

La comparación separa representación y procedimiento:

| Entradas | Ridge | HistGradientBoosting |
|---|---|---|
| Municipio + seis resúmenes E2 | R_B | H_B |
| Base + cuatro descriptores | R_T | H_T |

Comparar R_T−R_B o H_T−H_B estudia añadir el bloque; comparar H_B−R_B o H_T−R_T estudia cambiar el procedimiento con iguales entradas. Las rejillas acotadas tienen presupuestos diferentes: no prueban la superioridad universal de una familia.

## Qué ocurre al ejecutar

El lector reconstruye cuatro variables para 197 parcelas y comprueba **2,758 medias mensuales** de dos series. Puntúa **9,660 predicciones OOF guardadas** de siete procedimientos, con 138 etiquetas y 1,380 OOF por procedimiento. También comprueba **200 selecciones** desde sus **900 scores interiores guardados**.

**Hace cero ajustes de modelos.** No recalcula los scores ni las predicciones que los originaron y no genera las 59 predicciones de entrega. Los insumos incrustados se identifican por tamaño, SHA-256 y procedencia; las operaciones científicas están visibles. Preparar dependencias solo opera en Colab y solicita reinicio manual cuando corresponde.

La corrida histórica usó Python 3.12.14/scikit-learn 1.9.1 y **3,800 ajustes**. Esta lectura usa Python 3.13: reproducir métricas desde OOF conservadas no acredita paridad del entrenamiento entre entornos. Los mismos CSV exteriores e interiores se conservan, sin regenerar semillas ni filtrar retrospectivamente FULL138.

## Resultado conservado

Ninguna variante supera las referencias: R_T empeora frente a R_B; H_T reduce ligeramente RMSE frente a H_B, pero empeora MAE. El análisis por repetición, zona y sensibilidad prevista solo en evaluación conserva ese resultado negativo. Se cierra sin adopción; no descarta otras variables temporales ni todos los árboles.

Registro previo: **29/09/2026, 18:22 UTC**. Corrida: **30/09, 02:06–02:08 UTC**, aún 29 de septiembre en México. Adaptación del lector: **08/10/2026**. No es una ronda nueva ni un registro previo retrospectivo.

## Ejecución local

Desde la raíz del proyecto:

```bash
uv run --locked --all-groups python scripts/ejecutar_exp_03.py
```

El ejecutor guarda una carpeta nueva en `resultados_locales/exp_03_variables_y_familias/`. El generador es `scripts/construir_exp_03.py`, el contrato `config/exp_03_variables_y_familias.json` y las pruebas específicas `tests/test_exp_03.py`. La distribución local es `artefactos_locales/exp_03_variables_y_familias_equipo.zip`.

Verificación local: **403 pruebas pasan, 76 específicas de EXP_03**; Ruff pasa sobre scripts/tests. Dos kernels nuevos con solo el notebook reproducen 35 salidas y dos figuras, normalizando únicamente la fecha de ejecución. Son 33 celdas, 17 de código: dos técnicas plegadas y 15 visibles. Las fuentes y los cuadernos anteriores permanecen intactos. No hay todavía confirmación de ejecución real en Colab; no se confunde autonomía local con esa comprobación.
