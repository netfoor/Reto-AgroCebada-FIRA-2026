# 01 Entender y limpiar los datos

*Prompts de Jared Puga Romero · IA usada: Claude (Anthropic)*

## Una segunda revisión del dataset
**Lo que pedimos:** "Ya revisamos el ZIP del reto y tenemos claro el panorama: 197 parcelas, 138 con rendimiento y 59 por estimar. Antes de seguir queremos asegurarnos de que no se nos escapó nada. ¿Nos ayudas a cruzar los IDs entre el shapefile y los CSV y a revisar fechas, unidades y valores raros? Si encuentras algo que no cuadre, dinos dónde."

**Qué salió:** confirmó los conteos y que los IDs coincidían. Con eso cerramos la auditoría del primer cuaderno.

## Confirmar la unidad de análisis
**Lo que pedimos:** "Decidimos trabajar con una fila por parcela, resumiendo las capturas satelitales por periodo. ¿Ves alguna forma en que esa agregación meta información del rendimiento sin querer? Queremos que alguien del equipo que no vio el código lo entienda."

**Qué hicimos con eso:** dejamos documentada cada agregación (periodo, resumen y faltantes) en el segundo cuaderno.
