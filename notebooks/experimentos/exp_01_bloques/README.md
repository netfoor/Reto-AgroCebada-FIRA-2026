# EXP_01. Bloques de variables sobre municipio

Abrir `exp_01_bloques.ipynb`. Contiene explicación, código, tablas verificadas y salidas; basta subir ese archivo a Colab. No necesita ZIP, Drive, Git ni ejecutar los cuadernos anteriores.

Pregunta: ¿clima/topografía, satélite del ciclo o historia mejoran una regresión municipal? El recorrido abre las 14 variables, la preparación dentro de cada entrenamiento, el selector y la comparación sobre las mismas parcelas.

**Modo de ejecución:** lector retrospectivo, cero ajustes nuevos. Recalcula métricas de OOF guardadas y la elección de alpha desde scores interiores guardados; no reproduce el entrenamiento ni genera las 59 predicciones finales.

**Conclusión conservada:** E3 (historia) baja ligeramente RMSE frente a E0, pero empeora MAE y no supera MIX. El beneficio se concentra en pocas parcelas. No se adopta un bloque por ese resultado.

Trabajo original: 21/09/2026. Adaptación y comprobación local: 08/10/2026. La primera ronda conserva FULL138; no se le aplican criterios de rondas posteriores. Colab real se comprueba por separado.
