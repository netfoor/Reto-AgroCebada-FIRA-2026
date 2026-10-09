# EXP_10 · Verificación y decisión sobre la señal vecinal

8 de octubre de 2026. **Ronda registrada antes de los scores; lector sin ajustes; sin las 59 predicciones.**

**Pregunta:** ¿K1 (MIX + corrección lineal con el contraste vecinal de la integral NDVI Planet) conserva una mejora útil cuando el corte al 31 de octubre se implementa correctamente?

**Respuesta corta:** sí, conserva una mejora pequeña (~1 % de RMSE frente a MIX, en 20/20 repeticiones de dos juegos de particiones, con MAE no peor). Pero está concentrada y no alcanza evidencia estadística suficiente: p de familia 0.18 y 0.13 con dos nulos distintos. **Recomendación provisional: conservar MIX; K1 corregido queda como alternativa documentada.** Detalle en [RESULTADOS_Y_CIERRE.md](RESULTADOS_Y_CIERRE.md).

## Cómo leer y reproducir

| Paso | Archivo / comando |
|---|---|
| Leer (sin entrenar; autónomo, Colab con Python 3.13) | [exp_10_verificacion_contraste_vecinal.ipynb](exp_10_verificacion_contraste_vecinal.ipynb) |
| Protocolo y registro previo | [protocolo.md](protocolo.md), [registro_previo.json](registro_previo.json) |
| Factibilidad solo con X | `uv run --locked --all-groups python scripts/factibilidad_10.py` |
| Corrida (no sobrescribe) | `uv run --locked --all-groups python scripts/experimento_10.py --salida resultados/exp_10_verificacion_contraste_vecinal/<nueva>` |
| Verificación independiente | `uv run --locked --all-groups python scripts/verificar_exp_10_resultados.py` |
| Pruebas sintéticas | `uv run --locked --all-groups pytest -q tests/test_modelo_10.py` |
| Regenerar y ejecutar el lector | `scripts/construir_exp_10.py`, `scripts/ejecutar_notebook_exp_10.py --salida <nueva>` |

El lector se verificó en **dos kernels limpios locales** (`resultados_locales/exp_10_verificacion_contraste_vecinal/kernel_1` y `kernel_2`), con salidas idénticas. **No se ha probado todavía en Colab real.**

## Relación con experimentos anteriores

- **EXP_08** (C1, contraste vecinal) y **EXP_09** (K1 y fuentes externas) se conservan sin cambios. Sus cifras "hasta 31 oct" usan la receta con la discrepancia.
- **K2/K3 de EXP_09** comparten la misma construcción. En EXP_10 solo sirven como miembros del nulo de familia; no se reevaluaron.
- **EXP_07** (dispersión NDVI) cerró sin adopción y no se modifica.
