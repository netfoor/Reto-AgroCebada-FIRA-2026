# EXP_11 · Combinación fija de modelos (exploratoria)

8 de octubre de 2026. **Cero entrenamientos; dos fórmulas fijas; sin las 59 predicciones.**

**Respuesta corta:**

- **E_JK = ½·Jared + ½·(MIX + K1 corregido)** mejora a sus dos componentes en ambos juegos de particiones: RMSE SEEN 0.4757/0.4744 frente a 0.4820/0.4810 del mejor componente, en 10/10 repeticiones frente a K. Clase **C**: candidato para revisión.
- **El control E_MK = ½·MUN + ½·K no mejora a K** (clase A). La ganancia no se explica solo por reducir la interpolación espacial.
- **Reservas:** la hipótesis es posterior a ver los datos, la ganancia frente a K casi desaparece sin las 5 parcelas más favorecidas, y no hay nulo estadístico. Detalle en [RESULTADOS_Y_CIERRE.md](RESULTADOS_Y_CIERRE.md).

| Paso | Archivo / comando |
|---|---|
| Leer (autónomo, sin entrenar) | [exp_11_combinacion_modelos.ipynb](exp_11_combinacion_modelos.ipynb) |
| Protocolo y registro previo | [protocolo.md](protocolo.md), [registro_previo.json](registro_previo.json) |
| Preparar y verificar insumos (incluye reproducción de J) | `uv run --locked --all-groups python scripts/preparar_exp_11.py` |
| Corrida (no sobrescribe) | `uv run --locked --all-groups python scripts/experimento_11.py --salida resultados/exp_11_combinacion_modelos/<nueva>` |
| Verificación independiente | `uv run --locked --all-groups python scripts/verificar_exp_11_resultados.py` |
| Pruebas | `uv run --locked --all-groups pytest -q tests/test_combinacion_11.py tests/test_notebook_exp_11.py` |
| Regenerar y ejecutar el lector | `scripts/construir_exp_11.py`, `scripts/ejecutar_notebook_exp_11.py --salida <nueva>` |

**Procedencia de J:** `data/exp_11_combinacion_modelos/procedencia_jared/` conserva el script, las predicciones y las variables de la comparación temporal (`tmp_comparacion_jared/`, carpeta ignorada por Git). Las variables se comprobaron byte a byte contra el ZIP original de Jared. La entrega no depende de la carpeta temporal.

**Verificación del lector:** dos kernels limpios locales con salidas idénticas. **No probado en Colab real.**
