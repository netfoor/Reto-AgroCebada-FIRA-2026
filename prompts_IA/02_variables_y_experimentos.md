# 02 Variables y experimentos

*Prompts de Jared Puga Romero · IA usada: Claude (Anthropic)*

## Pasar de las fuentes a variables
**Lo que pedimos:** "Queremos seguir una sola parcela desde su polígono hasta su fila final con NDVI de Planet y Sentinel, lluvia CHIRPS, temperatura y topografía, y después generalizarlo a las 197. Ayúdanos a armar el código y a separar cuáles columnas son controles y cuáles podrían ser predictores."

**Qué salió:** más de 500 columnas con su diccionario. Nos quedó claro que no eran 500 predictores, sino material para probar hipótesis.

## Probar una idea sin engañarnos
**Lo que pedimos (se repitió en casi todas las rondas):** "Esta es la hipótesis de esta ronda: [lluvia de octubre / fecha del pico de NDVI / dispersión dentro de la parcela], y esta la regla con la que la vamos a aceptar o rechazar. Revisa que la comparación contra MUN y MIX use las mismas particiones y que no estemos cambiando nada más sin darnos cuenta."

**Qué hicimos con eso:** once rondas registradas en la bitácora. La mayoría se cerraron sin adopción, y eso también lo dejamos escrito.

## Buscar señal dentro del municipio
**Lo que pedimos:** "Vimos que el municipio explica casi todo. Tenemos la sospecha de que comparar una parcela con sus vecinas puede decir algo más. ¿Nos ayudas a probarlo contra el azar con permutaciones y a ver si la mejora está concentrada en pocas parcelas?"

**Qué salió:** el contraste vecinal de NDVI (la parcela menos la mediana de sus vecinas a menos de 1 km), que después verificamos con registro previo.
