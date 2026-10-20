# Notas de la familia 2: anomalias climaticas de 2025 (prefijo anom_)

Script: `preparacion/scripts/52_variables_clima_anomalias.R` (sin azar, sin rendimiento). 17 variables (tope 25), 9 hipotesis (2 existentes HR10 y HR11, 7 nuevas HN1 a HN7). 0 NA en todas.

## Decisiones y por que
- Referencia = promedio 2022-2024 de la misma parcela y misma ventana; primero se agrega cada anio por ventana y luego se promedian los 3 anios. Anomalia = 2025 menos referencia.
- Lluvia de la ventana = suma de los meses (mm); Tmin y Tmax = promedio simple de los meses (sin ponderar por dias). Ventanas A, B, C, D y CICLO fijas; jun-ago y sep-oct solo para HR10 y HR11.
- Anomalia de lluvia en % solo para las 5 ventanas comunes; HR10 va en mm como dice el registro. Umbral de "referencia casi 0": menos de 1 mm; ninguna parcela lo alcanza (la referencia minima de lluvia es 52 mm en A y 53 mm en D), asi que no hay NA.
- No hay desviaciones estandar ni z-scores: 3 anios de referencia son demasiado pocos para que sean estables.
- Nombres: el registro HR10 dice `anom_precip_jun_ago`; la columna se llama `anom_precip_mm_jun_ago` (como se pidio). El agente principal debe usar el nombre de la columna.
- Sin winsorizar ni transformar. Todo dato agronomico de las hipotesis va marcado [PV].

## Verificaciones (d)
- Lluvia y temperatura: 9,456 renglones cada una, 197 parcelas x 4 anios x 12 meses, sin faltantes, sin llaves duplicadas, mismos ID que base_197_ubicacion. El script se detiene si algo de esto falla.
- 2022-2024 y 2025 usan exactamente la misma tabla de meses por ventana (una sola funcion `agrega`). Tmin <= Tmax en todo renglon.
- Recalculo independiente en python3 (3 parcelas x 17 variables): diferencia maxima 4e-14.

## (c) Cuanta varianza explica el grupo (R2 de anomalia ~ grupo, 197 parcelas)
- Lluvia en %: A 0.85, B 0.91, C 0.88, D 0.90, CICLO 0.93; HR10 (mm jun-ago) 0.90.
- Tmin: A 0.36, B 0.73, C 0.88, D 0.94, CICLO 0.92; HR11 (sep-oct) 0.94. Tmax: A 0.65, B 0.93, C 0.92, D 0.90, CICLO 0.92.
- Con la celda climatica (25 celdas) el R2 es 0.99 o mas en todas: cada anomalia es practicamente una etiqueta de celda. Tabla completa: `clima_anomalias_r2_grupo.csv`.
- Consecuencia: sobre B2 (que ya conoce el grupo) casi toda la anomalia esta "gastada". Lo que queda es variacion entre celdas del mismo grupo (por ejemplo Chignahuapan, jun-ago: 75 a 122 mm), es decir, unas pocas celdas, no 138 datos independientes. Un resultado positivo sobre B2 se leeria como "esta celda fue mas humeda que las otras del grupo", no como efecto causal del clima. Excepcion parcial: anom_tmin_a (R2 0.36), pero su desviacion es 0.02 C, menor que cualquier error razonable de la fuente.
- Ademas hay colinealidad fuerte: 59 pares con correlacion absoluta mayor a 0.8 (por ejemplo anom_tmax_b con anom_tmax_c 0.99 y con anom_tmin_d 0.98). Las 17 variables son en el fondo pocas dimensiones; probarlas todas cuenta como muchas pruebas sobre casi la misma informacion (riesgo de falsos hallazgos).

## Avisos
- 2025 fue mas lluvioso que la referencia en TODAS las parcelas: anom_precip_pct_ciclo va de +33% a +82%; A de +59% a +123%. No hay parcelas con deficit. Causa: la lluvia media abr-oct de las 197 parcelas fue 531 mm (2022), 541 (2023), 938 (2024) y 963 (2025); la referencia mezcla dos anios secos con uno humedo. La "anomalia" es en realidad casi un "que tanto crecio la lluvia de 2024-2025 respecto de 2022-2023". Sugiero que Jared confirme (PV) que CHIRPS 2022-2023 no tiene un problema de version o calibracion; yo no lo corrijo.
- Tmax B de 2025 quedo ~1.7 C por debajo de la referencia en todas las parcelas (sd entre parcelas 0.15), coherente con el anio humedo.
- Solo hay un anio con rendimiento (2025): cualquier anomalia se confunde con la region, porque todas las parcelas vivieron el mismo 2025. No se puede aprender el efecto "anio atipico" con un solo anio; solo el gradiente entre celdas.
- Anomalia en % de octubre (D): rango +2.7% a +121%, con referencia pequena (53 a ~75 mm); no se recorta.
- Las celdas son de ~5.5 km y CHIRTS-ERA5 solo tiene variacion diaria de ERA5 (~25-30 km): la temperatura ve la region, no la parcela.
- El registro HR10 habla de "misma celda"; aqui se usa la misma parcela (promedio ponderado por area de celdas), que en la practica es lo mismo salvo parcelas que cruzan celdas.

## Lo que NO hice
No evalue nada contra el rendimiento, no abri archivos con rendimiento, no escribi en el registro ni en outputs/derivados/, no calcule z-scores, no imputé, no use paquetes fuera de readr, dplyr, tidyr, tibble.

## Preguntas para Jared
1. Dado el R2 por celda cercano a 1, conviene probar solo un subconjunto (HR10, HR11 y una o dos anomalias de HN) para no inflar el numero de pruebas? Mi sugerencia: HR10, HR11, anom_precip_pct_b y anom_tmax_b.
2. Confirmar si se acepta la referencia con 2022 y 2023 secos, o si se prefiere usar solo 2024 (un anio) como referencia; no lo cambie porque la instruccion fija los 3 anios.
