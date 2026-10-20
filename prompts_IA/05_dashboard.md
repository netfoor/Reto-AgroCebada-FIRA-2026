# 05 Dashboard

*Prompts de Jared Puga Romero · IA usada: Claude (Anthropic)*

## Explorar opciones antes de construir
**Lo que pedimos:** "Ya tenemos el backend en Python con uv y una idea de lo que queremos mostrar: el mapa de las parcelas con la vista satelital y una forma clara de explicar el modelo. Traíamos en mente algo tipo holograma, con estática azul y que al dar clic se resalte la parcela. ¿Nos armas ejemplos sencillos de algunas variantes para compararlas, diciendo qué biblioteca usa cada una?"

**Qué salió:** cinco prototipos en HTML con las parcelas reales. Elegimos el holograma porque sale directo de la data del reto.

## Juntar lo que más nos gustó
**Lo que pedimos:** "Decidimos quedarnos con el mapa y las funciones del holograma, pero con la estética limpia y la presentación de datos del sitio que ya teníamos. Queremos que el mapa se explique solo mientras bajas, con pasos que también se puedan elegir con clic, y una sección al final con las herramientas y el código que usamos."

**Qué salió:** la versión DashBoardV1: mapa satelital con recorrido de siete pasos, ficha por parcela, cálculo paso a paso y la sección "Herramientas de la página".

## Que cualquiera lo entienda
**Lo que pedimos:** "El jurado no tiene por qué saber de ciencia de datos. Revisamos los títulos y queremos que sean fáciles de explicar en voz alta, con un solo nombre para cada cosa. Ayúdanos a encontrar dónde quedó jerga o nombres que cambian de una sección a otra."

**Qué hicimos con eso:** acordamos los nombres ("sin dato", "referencia (municipio + vecinas)", "índice de vegetación (NDVI) contra las parcelas cercanas"), agregamos un glosario y simplificamos los títulos.

## Auditoría antes de publicar
**Lo que pedimos:** "Antes de mandarlo queremos revisarlo completo desde tres frentes: que todo funcione en computadora y celular, que cada número coincida con los datos y que se lea bien. Repártelo en revisiones separadas y tráenos solo lo que se confirme."

**Qué salió:** las 59 estimaciones recalculadas coincidieron con la entrega. Corregimos una frase que exageraba la ventaja del modelo, un porcentaje mal etiquetado y detalles de redacción y contraste.

## Que funcione bien en el celular
**Lo que pedimos:** "Lo probamos en el celular y al bajar la página nos regresaba, y el mapa no dejaba avanzar. ¿Qué lo provoca y cómo lo arreglamos sin quitar el recorrido?"

**Qué salió:** la barra de pasos ya no mueve la página, un dedo desplaza la página y dos dedos mueven el mapa, y la ficha solo se abre cuando tocas una parcela.
