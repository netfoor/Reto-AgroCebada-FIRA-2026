# 06 Selección del modelo final

*Prompts de Fortino Romero Mantilla · IA usada: Claude (Anthropic)*

## Entender antes de seguir probando
**Lo que pedimos:** "Antes de abrir otra ronda, explícame con mis propias palabras qué encontró el experimento del contraste vecinal y qué no demuestra. Quiero saber si la mejora es real o solo de unas cuantas parcelas."

**Qué salió:** separamos lo que sí sostenía la evidencia (una mejora pequeña y concentrada) de lo que no (sin evidencia estadística suficiente). Con eso decidimos conservar MIX como referencia y no adoptar nada automáticamente.

## Una prueba decisiva con reglas fijadas antes
**Lo que pedimos:** "Quiero que una revisión independiente ponga a prueba los candidatos con parcelas apartadas desde el inicio. Fija tú la regla de decisión antes de ver resultados y, si sale nula, la aceptamos."

**Qué salió:** la caja cerrada y las dos rondas de desarrollo. La segunda ronda salió parcial (nula en sustancia), así que no se reabrió la elección y se entregó E_JK con MIX como referencia.

## Un cuaderno final que cualquiera pueda reproducir
**Lo que pedimos:** "Arma el cuaderno de cierre: que reproduzca las evaluaciones, explique por qué elegimos E_JK y genere las 59 predicciones con su rango. Tiene que dar el mismo archivo cada vez que se ejecute."

**Qué salió:** el cuaderno 04 y sus salidas en `resultados/04_seleccion_modelo_final/`, con la huella SHA-256 de cada archivo para comprobar que no cambian entre ejecuciones.

## Ordenar el repositorio para quien lo consulte
**Lo que pedimos:** "Revisa el repositorio como lo vería alguien que no estuvo en el equipo: que el README lleve el recorrido en orden y que los nombres de archivos y carpetas digan lo que contienen."

**Qué salió:** README con el resultado final, la tabla de evaluaciones y el recorrido de cuadernos. Los nombres y el tono los definimos nosotros.
