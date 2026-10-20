# Familia 1: clima por ventanas fenológicas (notas)
Script: `preparacion/scripts/51_variables_clima_ventanas.R` (log en `resultados/logs/51_variables_clima_ventanas.log`). Fuente: solo los dos CSV mensuales de derivados, año 2025, abril a octubre. No se leyó rendimiento.

## Qué se construyó
- 27 variables, 0 NA (los dos CSV mensuales están completos para las 197 parcelas). Tope de 40 respetado.
- 15 base: lluvia (suma), Tmax y Tmin (promedio) en las ventanas A, B, C, D y CICLO. Sufijos `_a`, `_b`, `_c`, `_ciclo`, igual que la familia de anomalías. La ventana D es un solo mes, por eso sus columnas se llaman `_oct` (`clim_tmin_oct` es la Tmin de D y la que pide HA5); así no hay columnas duplicadas.
- 12 más para las hipótesis registradas: Tmin de jul, ago y sep; Tmax de ago y sep; lluvia de jun, jul, ago y sep; lluvia jul-ago; lluvia del mes más seco jun-sep; rango térmico de septiembre (Tmax menos Tmin) [CP].
- 17 hipótesis: 10 existentes (HA4, HA5, HA6, HB1, HB2, HB3, HB4, HB8, HC1, HC2) y 7 nuevas (HW1 a HW7).
## Decisiones y por qué
- HW1 y HW4 llevan signo (+ lluvia de A y B; - Tmax de B y C) porque tienen motivo agronómico prudente; el resto es exploratorio y así se declara desde ahora.
- HA6 dice que la lluvia de ago y sep es exploratoria. Para que HA6 (signo +) se evalúe solo con jun y jul, separé ago y sep en HW7 (sin signo). Si prefieres mantenerlas dentro de HA6, hay que cambiar esa fila.
- HB3 y HB4 llevan signo "ninguno" en la columna `signo` porque el registro dice "sin signo lineal"; lo esperado es coeficiente cuadrático negativo en la spec `x + I(x^2)`. HB4 además dice que Singuilucan cae en el tramo descendente: eso no cabe en la variable, se revisa aparte.
- HB2: el registro dice "Signo: +" sobre la variable (lluvia del mes más seco), se respetó.

## Desviación de HC2 (importante)
- Operacionalicé HC2 como interacción con el indicador `clim_ind_tmedia_jul_ago_15_20` (1 si la Tmedia jul-ago, (Tmax+Tmin)/2 [CP], está entre 15 y 20 °C). Resultó CONSTANTE: vale 1 en las 197 parcelas (la Tmedia jul-ago va de 17.16 a 18.66 °C).
- Consecuencia: la interacción no existe y HC2 se reduce a "más lluvia jul-ago baja el rendimiento", que es HC1. No exporté la columna constante (regla: ninguna columna constante); el cálculo queda en el script y en el log. La fila HC2 de `clima_ventanas_hipotesis.csv` apunta a `clim_precip_jul_ago` con spec "lineal": es la misma prueba que HC1, no debe contarse como prueba independiente.
- No moví el umbral 15-20 °C: es lo registrado y hacerlo mirando los datos sería ajustar la hipótesis.

## Hallazgos para tener presentes
- Celdas compartidas: 159 de 197 parcelas comparten el valor exacto de lluvia del CICLO con al menos otra; solo 38 tienen valor único; hay 53 valores distintos. Grupos de mismo valor de tamaño 48 y 39 (dos celdas grandes).
- Casi nada de la variación es interna a la región: R2 de `lm(x ~ grupo)` (sin rendimiento) va de 0.90 (rango térmico sep) y 0.78 a 0.86 (todas las Tmin) hasta 0.16 a 0.19 (Tmax de B, C, ago y ciclo). La Tmin y la lluvia de A y de octubre quedan en buena parte absorbidas por B2.
- Poca variación en Tmax: p. ej. `clim_tmax_a` va de 25.8 a 26.3 °C (0.5 °C de rango); son décimas de grado sobre una fuente con resolución nominal de 5 km [V-parcial, ver hoja E].
- Redundancia entre las 15 base (Pearson): lluvia B, C y CICLO (r 0.99); Tmax B, C y CICLO (r 0.996 a 0.998); Tmin B, C, oct y CICLO (r 0.98 a 0.997); Tmin de todas las ventanas con la lluvia de octubre (r 0.92 a 0.95, es estructura regional). Son 21 pares con |r| >= 0.9. No borré nada.
- Todas las parcelas comparten un único año: las diferencias de clima entre parcelas son geográficas (altitud, ubicación), no de años. Puede confundirse con el ambiente que B2 ya captura.
## Lo que NO hice
No usé 2022-2024 (eso es la familia de anomalías), no usé datos diarios ni fecha de siembra, no combiné con satélite, no evalué nada contra rendimiento, no escribí en el registro ni en `outputs/derivados/`.

## Verificación
Recalculé con python3 (ruta independiente, sobre los CSV crudos) las 27 variables para las 197 parcelas: 5,319 valores, 0 diferencias mayores a 1e-9. Se comprobó también que Tmax > Tmin todos los meses y lluvia >= 0.

## Avisos
- En `base_197_ubicacion.csv`, `celda_clima` tiene 25 valores pero hay 53 valores distintos de lluvia: algunas celdas_clima agrupan parcelas con lluvia ligeramente distinta (hasta 6 valores en una celda). No lo investigué.
- La primera cifra de `celda_proxy` coincide con la lluvia del CICLO de esta familia (p. ej. AGC_196: 799.46); es coherente, pero conviene saber que ese campo ya lleva clima.

## Preguntas para Jared
1. ¿Se acepta que HC2 quede como no separable de HC1 (indicador constante)? Alternativa exploratoria: Tmedia jul-ago continua por lluvia jul-ago, pero su rango es de solo 1.5 °C y sería una hipótesis nueva.
2. ¿Se separan ago y sep de HA6 en HW7, como hice?
3. ¿Se aceptan las ventanas suposición (siembra mayo-junio [PV]) o prefieres otras?
