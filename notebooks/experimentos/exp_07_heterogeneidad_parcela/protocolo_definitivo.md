# EXP_07 · Protocolo de ejecución

8 de octubre de 2026. Registro previo interno, antes de ajustar candidatos.

## Autorización y alcance

Fortino autorizó: «Perfecto correlo y verifiquemos que sucede». Se comunicó antes de la corrida que se interpreta como aprobación del plan, incluido el criterio propuesto MAE≤MIX; también se reporta MAE≤MUN histórico. No se afirma un acuerdo anterior del equipo ni una métrica oficial de FIRA.

Este protocolo operacionaliza el plan propuesto sin cambiar la hipótesis, ventana, comparadores, selector ni presupuesto. La hipótesis deriva de seis rondas y exploraciones anteriores sobre las mismas etiquetas: es desarrollo adaptativo, no confirmación independiente. El hash garantiza integridad, no sello temporal de terceros. Se preserva el plan original como antecedente.

## Hipótesis y variables

H7: añadir la dispersión espacial NDVI Planet mejora el error respecto del mismo procedimiento con nivel medio, conservando municipio.

Original PRO, abril–octubre2025 inclusive, sin filtro adicional de nubes. L=media de ndvi_promedio y S=media de ndvi_std sobre exactamente las capturas donde ambos son finitos. Ningún recorte de valores, ventanas alternativas, nueva familia o variable adicional. Negativos de std detienen antes de evaluar. Las parcelas sin descriptor se conservan.

C0 usa L; C1 usa L+S. Mediana numérica de entrenamiento, centrado por municipio y Ridge sin intercepto sobre residuos. Medianas/medias/escala/alpha exclusivamente train-only dentro de cada interior/exterior. Mediana es extensión prospectiva común respecto de V3.

Escala por columna=sqrt(mean(residuo_X²)), incluyendo singleton. Guarda relativa: escala≤1e−12×max(1,max|X_train_imputada|). Columna degenerada se anula individualmente. Grupo desconocido usa media global sin corrección. Baseline equivale a pendientes cero/MUN. No corregir MIX con residuales que incorporen su propia etiqueta.

## Factibilidad y referencias

Verificar hashes de originales/controles, roles197/138/59, sensor/fechas/duplicados, soporte pareado, rangos, cobertura temporal y variación intramunicipal en250 entrenamientos(50externos+200internos), sin valores de rendimiento. Si alguna columna carece de datos para imputar en algún entrenamiento o no presenta variación útil, detener. Mostrar asociaciones X-X con nivel, nubosidad y área, sin usarlas para elegir recetas.

Pruebas sintéticas: lector/soporte pareado, negativos/Inf, faltantes, escala/degeneración, interceptos no penalizados, singleton, unknown, orden/mutación, invariancia al holdout. Contabilidad y selector probados con etiquetas inventadas. Las pruebas sintéticas se registran aparte del presupuesto real.

Después del registro, reproducir MUN/MIX con mismas particiones y orden de entrenamiento a1e−8t/ha antes de ajustar C0/C1. MUN=media municipal/fallbackGLOBAL; MIX=0.5MUN+0.5IDW fijo,k20,p2,piso1m,centroidesUTM14N y np.argsort histórico.

## Evaluación fijada

Outer COD-CV-5x10-20260920 (SHA02d07dfcdb8064a4daf08b5bebc575f807ccab09ca33f27ec7dfa1a069c300ec); interior4 por exterior(SHAa35412fda33fcea7b379f6d95418eaaa7ebafc5b5330873613b83184cb16ab6a). No nuevas semillas.

SEEN135 principal, FULL138 secundario, sin retirar etiquetas del entrenamiento. Selector interior: RMSE agrupado FULL. Opciones baseline,0.01,0.1,1,10,100. Empate≤1e−12: primero baseline; después alpha mayor. Solver Ridge Cholesky determinista; equivale al problema penalizado fijado.

OOF=1,380por procedimiento FULL y1,350SEEN. RMSE/MAE/R² agrupados, por repetición, municipio y Chignahuapan/resto. R² indefinido se presenta NaN. Ninguna predicción de las59 ni entrenamiento final en esta corrida.

## Reglas de decisión

Aporte H7: C1 RMSE<C0 agrupado y en≥8/10repeticiones SEEN. Siempre mostrar MAE. C0 competitivo sin aporte S no confirmaH7.

Competitividad aprobada para esta ejecución: RMSE<MIX y MAE≤MIX, agrupados y cada condición en≥8/10repeticiones SEEN. Diagnóstico histórico adicional: RMSE<MIX y MAE≤MUN con mismo umbral. No recalificar resultados anteriores. No inventar tolerancia MAE para salvar un ganador.

El conteo8/10no es significación y las repeticiones no son muestras independientes. Una mejora pequeña o concentrada sigue siendo incierta. Revisar soporte de ocultas y limitación Nanacamilpa sin una OOF equivalente con su única etiqueta presente.

Concentración prevista: ganancia SSE por parcela C1−C0,C1−MIX,C0−MIX; top2/top5 solo retirados de evaluación, nunca de entrenamiento. Reportar ganancia neta y fracción de ganancias positivas con nombres distintos. No seleccionar recetas según estos diagnósticos.

## Presupuesto y cierre

2procedimientos×50outer×4inner×6opciones=2,400evaluaciones interiores:400baseline+2,000opcionesRidge.100reconstrucciones exteriores; máximo2,100ajustesRidge efectivos por corrida.100evaluaciones de referencia(50MUN+50MIX) aparte. Contabilizar ajustes reales y opciones numéricas: una opción puede encontrar columnas degeneradas.

Una corrida registrada y una réplica de determinismo, sin nuevas variantes; los costes físicos se identifican por ejecución. El notebook podrá leer OOF o replicar la receta explícita, indicando su modalidad. Los controles no se presentan como nuevos candidatos.

Cerrar la hipótesis con su evidencia y límites. No lanzar otra ventana, filtro o algoritmo automáticamente si falla. La selección del artefacto final y producción son otro paso, posterior a este cierre.
