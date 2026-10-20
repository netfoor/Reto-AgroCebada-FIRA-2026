# 06 Selección del modelo final

*Prompts de Fortino Romero Mantilla · IA usada: Claude (Anthropic)*

## Entender antes de seguir probando
**Lo que pedimos:** "Lee los resultados y el código del experimento del contraste vecinal que tenemos en el repositorio. Yo ya leí las tablas y mi lectura es que la mejora es pequeña y viene de pocas parcelas; dime si estás de acuerdo o qué estoy pasando por alto, y explícame con claridad qué no demuestra."

**Qué salió:** separamos lo que sí sostenía la evidencia (una mejora pequeña y concentrada) de lo que no (sin evidencia estadística suficiente). Con eso decidimos conservar MIX como referencia y no adoptar nada automáticamente.

## Una prueba decisiva con reglas fijadas antes
**Lo que pedimos:** "Queremos poner a prueba los candidatos con parcelas apartadas desde el inicio, y que la regla de decisión quede escrita antes de ver resultados: si sale nula, la aceptamos. Te paso la regla que propongo; revisa si es clara, si deja huecos o si se podría ajustar después de ver los números."

**Qué salió:** la caja cerrada y las dos rondas de desarrollo, con la regla definida por el equipo antes de correrlas. La segunda ronda salió parcial (nula en sustancia), así que no se reabrió la elección y se entregó E_JK con MIX como referencia.

## Un cuaderno final que cualquiera pueda reproducir
**Lo que pedimos:** "Con los scripts y resultados que ya tenemos en el repositorio, quiero armar el cuaderno de cierre. Yo defino la estructura (evaluaciones, justificación de E_JK, las 59 predicciones con su rango); ayúdame a escribir el código de cada sección y a comprobar que, ejecutado dos veces, da exactamente el mismo archivo."

**Qué salió:** el cuaderno 04 y sus salidas en `resultados/04_seleccion_modelo_final/`, con la huella SHA-256 de cada archivo para comprobar que no cambian entre ejecuciones.

## Ordenar el repositorio para quien lo consulte
**Lo que pedimos:** "Lee el README y la estructura de carpetas como si no hubieras estado en el equipo y dime dónde te pierdes o qué nombres no dicen lo que contienen. Los cambios los decidimos nosotros."

**Qué salió:** README con el resultado final, la tabla de evaluaciones y el recorrido de cuadernos. Los nombres y el tono los definimos nosotros.
