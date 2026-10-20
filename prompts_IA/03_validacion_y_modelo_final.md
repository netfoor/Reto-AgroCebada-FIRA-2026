# 03 Validación y modelo final

*Prompts de Jared Puga Romero · IA usada: Claude (Anthropic)*

## Combinar en lugar de elegir
**Lo que pedimos:** "Notamos que J (grupo regional y lluvia de octubre) y K (MIX corregido por NDVI) fallan en parcelas distintas. Queremos probar si promediarlos 50/50 ayuda de verdad o es casualidad. ¿Nos ayudas a compararlo contra un control que use la media municipal?"

**Qué salió:** E_JK = ½·J + ½·K mejoró a sus dos componentes en la validación cruzada. La decisión de entregarlo la registramos como equipo antes de la última prueba.

## Una prueba que no pudiéramos acomodar
**Lo que pedimos:** "Vamos a apartar 35 parcelas antes de ver cualquier rendimiento, congelar el procedimiento con las demás y abrir la caja una sola vez. Revisa que el código no toque esas 35 en ningún paso. Si sale mal, lo reportamos igual."

**Qué salió:** la caja cerrada no favoreció a ningún procedimiento nuevo y E_JK se mantuvo, con un error esperado de 0.47 a 0.49 t/ha.

## Revisar las 59 predicciones
**Lo que pedimos:** "Ya generamos las 59 predicciones con el modelo final y les pusimos un intervalo calculado con los errores de la validación. Antes de entregarlas, ¿puedes revisar que la cobertura del intervalo se sostenga en particiones que no usamos para calcularlo?"

**Qué salió:** confirmamos la cobertura y dejamos `predicciones_59.csv` e `intervalos_59.csv` con rangos de 80 % y 90 %.
