# EXP_07 propuesto · Heterogeneidad espacial dentro de la parcela

8 de octubre de 2026. **Plan para discusión; no ejecutado, no preregistrado, sin notebook de resultados.**

## 1. Pregunta, antecedente y novedad

¿La dispersión espacial del NDVI Planet aporta información de rendimiento, fuera de muestra, después de considerar municipio y NDVI medio?

Dos parcelas pueden tener igual verdor medio y diferente uniformidad interna. Esa diferencia podría reflejar estados del cultivo, pero también bordes, mezcla de píxeles o procesamiento. No suponemos una dirección obligatoria ni interpretamos el coeficiente como efecto causal.

Las seis rondas estudiaron bloques generales, ponderación temporal, dinámica, lluvia y fechas de pico. La exploración inicial de 56 agregados ya incluyó otros índices, pero no `*_std` satelital. **La novedad es añadir esa dimensión espacial**, no otro nombre para una media temporal.

Reutilizamos centrado municipal + Ridge de EXP_04/05. Eso mantiene explícita la referencia territorial. E2 penalizaba las columnas municipales: comparar directamente C1 con E2 no aislaría heterogeneidad; necesitamos un control C0 con la misma arquitectura.

## 2. Variables y receta propuesta

Fuente: `ndvi_promedio` y `ndvi_std` de Planet, en el PRO original. Ventana inclusiva **1 de abril–31 de octubre de 2025**. Sin filtro adicional de nubosidad, igual que la extracción histórica del cuaderno 02. No añadimos otro sensor, ventana, índice, ratio ni regla de calidad durante esta ronda.

Para cada parcela usamos únicamente capturas con **ambas estadísticas finitas**, respetando IDs y fechas ya validados:

- **L:** media aritmética de `ndvi_promedio` sobre esas capturas.
- **S:** media aritmética de `ndvi_std` sobre exactamente esas mismas capturas.

Nombres propuestos: `H7_PL_ndvi_media_pareada` y `H7_PL_ndvi_std_media_pareada`. No se sobrescriben `C_PL_ndvi_media` ni `C_PL_ndvi_std_media` históricos. Si las máscaras coinciden, se demuestra su igualdad; si no, se explican las diferencias.

**Por qué recalcular algo ya extraído:** la implementación histórica promedia NDVI sobre sus filas disponibles, pero omite por separado los NaN de std. No garantiza el mismo soporte. Parear ambos evita atribuir a S una diferencia causada por usar fechas distintas en L. Es un control de comparación, no repetir toda la ingeniería de variables.

S no es la desviación temporal de L, ni la desviación de todos los píxeles de toda la campaña juntos, ni un intervalo de incertidumbre de rendimiento. Promediar por captura conserva el peso de fechas más observadas; no reabrimos EXP_02. Abril–octubre conserva la ventana conocida sin inventar etapas de crecimiento individuales.

El proveedor no entrega máscara ni conteo de píxeles por captura ni especifica la convención exacta de std. Se utiliza la estadística entregada y se limita su interpretación; no se reconstruye desde píxeles inexistentes.

## 3. Primera puerta: factibilidad solo con X

Antes de abrir etiquetas para esta corrida, el cuaderno debe mostrar:

1. Fuente, tamaño/hash y columnas correctos; 197 IDs conservados, sin duplicados parcela–fecha–sensor ni cruces con etiquetas.
2. Una parcela completa: capturas, L, S y cálculos visibles antes del código generalizado.
3. Conteos de fechas con promedio, con std y pareadas; meses observados, faltantes y rangos. Comparación con las dos columnas históricas como control de aritmética, no selección de receta.
4. Distribución de S entre parcelas del mismo municipio, variación tras el centrado municipal en cada entrenamiento y vínculo descriptivo con L, nubosidad, área y número de capturas, **sin rendimiento**. Variación únicamente entre municipios no sustenta esta hipótesis. Controlar L linealmente no elimina toda dependencia no lineal.
5. Soporte de las 59 ocultas, incluido Nanacamilpa: faltantes y rango frente a los datos etiquetados, sin producir predicciones.
6. Pruebas sintéticas de soporte pareado, fila ausente, grupo vacío, orden de filas, duplicados y parcela sin descriptor; controles de imputación/centrado/escala train-only con etiquetas inventadas. Comprobar equivalencia con Ridge e interceptos municipales no penalizados, baseline=MUN exacto, columna degenerada sin anular otras y ausencia de dependencia al modificar etiquetas del holdout.

No eliminamos parcelas por faltar S. Si no hay variación intramunicipal utilizable, algún entrenamiento interior no dispone de valores para imputar una variable, se detecta `ndvi_std < 0`, o aparece otro problema material de definición/calidad, **se detiene antes de medir rendimiento**. Se investiga la causa; no se corrigen negativos con valor absoluto o recorte silencioso. Cualquier nueva receta necesita otra decisión previa. No se selecciona nube 10/20/40 % según puntuaciones ni se reemplaza NDVI por otro índice automáticamente.

Esta puerta evalúa viabilidad, no demuestra una relación agronómica. Los metadatos que no vienen en el ZIP quedan como limitaciones explícitas.

## 4. Comparación que responde la pregunta

| Procedimiento | Entradas numéricas | Qué permite concluir |
|---|---|---|
| C0 · control | L | Qué logra corregir municipio usando nivel medio, con la arquitectura común. |
| C1 · candidato | L + S | C1−C0 estudia añadir heterogeneidad a esa representación. |
| MUN / MIX | Recetas históricas fijas | Si la mejora, además de incremental, compite con las referencias. |

En cada entrenamiento se imputan las variables con su mediana de entrenamiento, se centran X e y por municipio y se aplica la escala aprendida en entrenamiento. **V3 no imputaba entradas no finitas:** la imputación aquí es una extensión prospectiva común a C0/C1, no reproducción exacta de su tratamiento de faltantes. Las columnas de ausencia son diagnósticos, no predictores nuevos.

Se conserva la convención de escala de V3, extendida por columna: `escala_j = sqrt(mean(residuo_X_j²))`, incluyendo las filas singleton con residuo cero. Se considera degenerada si `escala_j <= 1e-12 × max(1, max(abs(X_train_j)))`; X es la entrada imputada antes de centrar. Esa columna queda sin corrección, sin anular las otras. Municipio no visto recibe media global sin corrección. Los interceptos municipales quedan sin penalizar. Con pendientes cero se recupera exactamente MUN.

Medianas, medias, escala y alpha se aprenden de nuevo **dentro de cada entrenamiento interior y exterior**, nunca en toda la tabla. Las variables de las 59 no intervienen en esos ajustes. Para entrenar el artefacto final habrá otro paso explícito con las 138 etiquetas.

No corregimos MIX mediante residuos calculados incluyendo la propia etiqueta ni con OOF globales históricas: eso podría introducir información del holdout. Hacerlo bien exige cross-fitting dentro de cada entrenamiento y otro presupuesto; no forma parte de esta pregunta.

## 5. Evaluación y controles comunes

Reutilizar `COD-CV-5x10-20260920`: 50 particiones exteriores y cuatro interiores por entrenamiento exterior, todas por parcela. No buscar otra semilla ni reconstruir una partición más favorable.

- SHA-256 exterior: `02d07dfcdb8064a4daf08b5bebc575f807ccab09ca33f27ec7dfa1a069c300ec`.
- SHA-256 interior: `a35412fda33fcea7b379f6d95418eaaa7ebafc5b5330873613b83184cb16ab6a`.

**SEEN135 principal; FULL138 secundario**, sin excluir etiquetas del entrenamiento. SEEN se determina por IDs, municipios y particiones, no por errores. Nanacamilpa con una sola etiqueta mantiene su limitación: no existe un caso OOF equivalente con esa etiqueta municipal disponible.

Selector interior común: RMSE agrupado de todas las validaciones interiores, como en V3; no cambiar a SEEN solo para favorecer un candidato. Opciones: `baseline`, alpha `0.01`, `0.1`, `1`, `10`, `100`. Empate a `1e-12`: primero baseline, después alpha mayor. Baseline significa pendiente cero y referencia municipal, no alpha cero.

Reportar RMSE, MAE y R² agrupados y por repetición, con las mismas filas/pesos para los candidatos. R² y RMSE ordenan igual sobre la misma muestra y ponderación; no garantizarlo para promedios de R² entre pliegues. Las 1,350 OOF principales no son 1,350 parcelas independientes.

Antes de interpretar candidatos, reproducir MUN/MIX con las particiones históricas a tolerancia `1e-8 t/ha`. Separar la comprobación de referencias de los nuevos resultados; guardar OOF, opciones interiores, selección y presupuesto reales.

## 6. Regla propuesta: distinguir señal y candidatura

**Aporte incremental:** C1 debe reducir RMSE respecto de C0, agrupado y en al menos 8/10 repeticiones de SEEN. Se reporta siempre su cambio de MAE. Si C0 resulta competitivo sin aporte de S, no lo presentamos como confirmación de H7.

**Competitividad propuesta, por ratificar:** RMSE menor que MIX y MAE no mayor que MIX, agrupados y cada condición en al menos 8/10 repeticiones de SEEN. No fijamos una tolerancia MAE arbitraria. MUN permanece en la tabla y se muestra también si se cumple la regla histórica más exigente, RMSE<MIX y MAE≤MUN.

La razón de proponer MAE frente a MIX es comparar el nuevo candidato con un procedimiento completo: la regla anterior exige superar el RMSE de un campeón y el MAE de otro. Ambas políticas son posibles; **Fortino debe ratificar cuál aplica antes del registro y de cualquier ajuste**. Mientras no se ratifique, este plan no autoriza cambiar la regla vigente ni ejecutar. Los seis cierres históricos no se recalifican.

Estos criterios son reglas de desarrollo, no significación estadística ni fórmula oficial de FIRA. Cambiar de política también es una decisión humana adaptativa tras resultados previos; aplicarla hacia adelante no la vuelve científicamente superior ni elimina ese antecedente. Aunque se cumpla, la adopción requiere revisar los límites y soporte de entrega; una mejora pequeña puede seguir siendo incierta.

## 7. Presupuesto cerrado propuesto

Dos procedimientos × 50 exteriores × cuatro interiores × seis opciones = **2,400 evaluaciones internas**:

- 400 evaluaciones baseline sin ajuste Ridge.
- 2,000 ajustes Ridge internos.
- 100 reconstrucciones exteriores del procedimiento elegido; habrá ajuste Ridge si se elige un alpha numérico en lugar de baseline, aunque el ajuste devuelva coeficientes cero.
- 100 evaluaciones exteriores de referencia aparte: 50 MUN + 50 MIX. No añaden búsquedas de parámetros.

Como máximo, 2,100 ajustes Ridge para los candidatos en una corrida. Una réplica determinista repite el coste físico y se registra como réplica, no como candidato nuevo. Pruebas sintéticas y controles de X se contabilizan aparte. **Presupuesto ejecutado a esta fecha: cero.**

No se añaden modelos, interacciones, ventanas ni filtros tras ver resultados. Una ampliación exigiría justificar la pregunta y registrar una nueva decisión, no completar una rejilla hasta obtener un ganador.

## 8. Lectura del resultado y cierre

Diagnósticos previstos: Chignahuapan/resto; municipios; faltantes/calidad; contribución de las dos y cinco parcelas más favorables; concentración por zona. Son sensibilidades de evaluación, no permiso para borrar etiquetas ni reentrenar retirando casos difíciles. Mostrar también cuántas parcelas favorecen/perjudican la mejora y su magnitud.

Una ganancia concentrada, un deterioro importante dentro de Chignahuapan o soporte problemático para las ocultas impiden afirmar robustez sin matices. No se adaptarán recetas para reparar esas salidas en la misma ronda. El resultado confirma o cuestiona **esta representación lineal, ventana y fuente**, no la heterogeneidad espacial en general.

La validación anidada controla selección dentro de la ronda, no nuestra adaptación acumulada a las mismas etiquetas. El registro nuevo debe reconocer explícitamente ese antecedente; no lo llamamos evidencia confirmatoria independiente.

Después de esta ronda: decidir si conservar un candidato, MUN o MIX; congelar receta, verificar las 59 predicciones y completar la herramienta. La recomendación es reservar el resto del plazo de entrega para ese cierre, no encadenar automáticamente las hipótesis de reserva.

## 9. Estructura del futuro notebook

1. Pregunta y evidencia previa — entender el problema.
2. Qué significa std y qué no sabemos — entender los datos.
3. Una parcela y soporte pareado — preparar los datos.
4. Generalización a 197, controles y factibilidad — preparar los datos.
5. Comparación, protocolo ratificado y presupuesto — modelar.
6. Entrenamiento acotado separado de controles históricos — modelar/evaluar.
7. Tabla común, errores y concentración — evaluar.
8. Decisión, límites y qué se entrega — evaluar/desplegar.

Será autónomo en Colab, con insumos identificados por hash y código técnico explicado antes de mostrarse. No necesita ejecutar otro cuaderno ni comprender código incrustado sin contexto. Aquí todavía no se generan ese notebook, una corrida ni sus resultados.

El historial de comparaciones está en la [bitácora](../../../docs/bitacora_experimentos.md).
