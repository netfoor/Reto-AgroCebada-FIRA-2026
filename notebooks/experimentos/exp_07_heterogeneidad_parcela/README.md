# EXP_07 · Heterogeneidad espacial de NDVI

Pregunta: ¿la dispersión espacial aporta información que el nivel medio y municipio no explican?

El [cuaderno](exp_07_heterogeneidad_parcela.ipynb) muestra una parcela, reconstruye L/S sobre soporte pareado, comprueba las 197 y evalúa OOF y elecciones guardadas de la corrida del 8 de octubre. Es autónomo y **no ajusta modelos al ejecutarlo**. La corrida real y el lector se distinguen; no necesita otro notebook, Git ni módulos locales.

**Cierre sin adopción:** en SEEN135, C0 RMSE 0.494064, C1 0.494105, MIX 0.487197 t/ha. C1 mejora sobre C0 solo en 4/10 repeticiones. Véase el [resultado y sus límites](RESULTADOS_Y_CIERRE.md).

Para replicar entrenamiento en local, desde el proyecto y sin sobrescribir la corrida registrada:

```bash
uv run --locked --all-groups python scripts/experimento_07.py
```

El script comprueba el registro y sus hashes antes de ajustar; conserva fuentes y particiones fijadas y crea una salida nueva. Cada corrida tiene 2,400 evaluaciones interiores y hasta 2,100 ajustes Ridge: no es el modo de lectura del notebook.

Para verificar el lector en un kernel nuevo:

```bash
uv run --locked --all-groups python scripts/ejecutar_notebook_exp_07.py
```

Los artefactos originales, las seis rondas anteriores y las 59 parcelas sin rendimiento permanecen sin predicciones finales nuevas.
