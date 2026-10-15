# API de reentrenamiento

Función de AWS Lambda que vuelve a ajustar el modelo final con las 138 parcelas de rendimiento conocido y estima las 59 ocultas. Usa las mismas recetas que la sección 7 del [cuaderno 04](../notebooks/04_seleccion_modelo_final.ipynb).

| Ruta | Respuesta |
|---|---|
| `GET /api/reentrenar` | JSON con β de K, la variable y los coeficientes de J, las 59 estimaciones con sus componentes (MUN, MIX, K, J, E_JK), el tiempo de ajuste y la SHA-256 del CSV resultante, comparada con la entrega. |
| `GET /api/reentrenar?formato=csv` | `predicciones_59.csv`, idéntico al archivo entregado. |
| `GET /api/salud` | Versiones de Python, numpy y pandas, commit e insumos verificados. |

Cada llamada a `/api/reentrenar` reentrena; no hay resultados guardados.

## Archivos

| Archivo | Contenido |
|---|---|
| `agrocebada_api/recetas.py` | Copia literal de las recetas del cuaderno 04: MUN, MIX, K (β con 4 pliegues internos, semilla 20261015), J (5 grupos y una variable elegida entre 148) y E_JK. |
| `agrocebada_api/datos.py` | Lee los 14 insumos con la misma configuración que el cuaderno y verifica su SHA-256. |
| `agrocebada_api/handler.py` | Rutas de la función. |
| `empaquetar.py` | Arma `dist/agrocebada_api.zip`: código, insumos y numpy/pandas para Linux arm64. |
| `verificar.py` | Comprueba sin AWS que el reentrenamiento reproduce la entrega byte a byte. |
| `tests/` | Pruebas: `uv run pytest api/tests`. |

Los insumos salen de `data/` cuando existe. Esa carpeta no se publica en GitHub; en un clon sin ella se extraen de la copia incrustada en el cuaderno 04, con la misma verificación.

## Uso local

Desde la raíz del repositorio:

```bash
uv run python api/verificar.py      # reentrena y compara con la entrega
uv run pytest api/tests             # pruebas
uv run python api/empaquetar.py     # paquete para Lambda
```

El despliegue está en [`infra/`](../infra/README.md).
