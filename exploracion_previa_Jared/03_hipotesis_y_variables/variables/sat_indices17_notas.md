# Notas de la familia 5 (sat_indices17): los 17 índices sin evaluar y su variabilidad interna

**Total construido: 32 variables** (tope 90), 13 hipótesis (5 ya registradas: HR3, HR6, HR9, HR13, HR14; 8 nuevas: HI1 a HI8). Script: `scripts/55_variables_sat_indices17.R`. No se leyó ningún archivo con rendimiento; sí se leyeron las filas HR3, HR6, HR9, HR13 y HR14 del registro (y, por el corte de bytes al abrirlo, las filas H1 a H4 con resultados agregados de las líneas base, sin datos por parcela).

**De primer orden (17, elegidas por el diccionario y las hipótesis ya registradas, sin mirar resultados):** los 5 de HR9 (`crc`, `mcrc`, `ndti`, `sti`, `ndsvi` en feb-may), `ndsvi_ago` (HR14), MSI, EMSI, NDDI y ENDDI de jul-sep (HR13), FAPAR jul-sep y del ciclo (HI1), ENDWI jul-sep (HI2), y el CV de SAVI-S2, NDVI-Planet, NDVI-S2 y EVI-S2 en jul-sep (HR6, HI6). Las otras 15 son exploratorias o secundarias (HR3, DSWI2-5, SRNDI, MRA, VI6T, desviaciones absolutas, HI8). Con 138 parcelas conviene probar primero las 17 y tratar el resto como pistas.

## Decisiones y por qué
- Ventanas por criterio agronómico, no por resultados: PRE (feb-may) para residuo, labranza y suelo, porque antes de la siembra (1 mayo-15 junio [V]) el suelo y el rastrojo están expuestos; JUL-SEP para vigor, agua y estrés (floración a 45-72 días de la siembra [V], llenado en jul-sep, con la suposición [PV] de siembra mayo-junio); CICLO para FAPAR (aproxima la radiación absorbida acumulada) y MRA (sin ventana natural); agosto solo para NDSVI (HR14) y abr-may solo para NDWI y NDDI (HR3).
- Un solo criterio de observación válida: nubosidad < 20 y valor no vacío (NA en nubosidad no cuenta). No hay ningún NA en las 32 variables (mínimo de observaciones válidas por parcela: 19 en PRE, 8 en abr-may, 10 en jul-sep S2, 4 en agosto, 26 en CICLO, 16 en Planet jul-sep y solo 1 en VI6T jul-sep).
- CV = promedio de std/|media| solo en fechas con |media| > 0.05. Lo construí para SAVI, NDVI y EVI (media de 0.03 a 0.6) y para MSI (razón cerca de 1). No lo construí para NDDI, NDWI y ENDWI porque su media cae en |x| <= 0.05 en 38%, 13% y 21% de las observaciones (el cociente explota).
- La desviación absoluta (HI7) va sin signo porque mezcla heterogeneidad con nivel de vigor; el CV lleva signo negativo (HR6, HI6). HI8 (desviación de NDTI en PRE y CV de MSI) tiene una razón agronómica más débil; queda con signo negativo pero es la más prescindible.
- HR13 se dividió: sus 4 índices con signo negativo van en HR13; DSWI2-5 (exploratorios sin signo dentro de HR13) van en HI5 para poder darles otro signo.
- Nombres: `sat_<índice>[_std|_cv]_<sensor>_<ventana>`; ventanas `pre`, `a`, `jul_sep`, `ago`, `ciclo`. Los registrados como `cv_savi_s2_intraparcela` etc. corresponden a `sat_savi_cv_s2_jul_sep` y `sat_ndvi_cv_planet_jul_sep`.

## Lo que NO hice
No usé LAI (por eso no hay recorte ni bandera de negativos), ni MSAVI, ni las columnas `_max` y `_min`. No imputé nada ni ajusté umbrales. No probé segundas ventanas por índice salvo NDSVI y FAPAR. No evalué nada contra el rendimiento.

## (d) Informes solo descriptivos
- NA: 0% en todas las variables, porque toda parcela tiene al menos una fecha sin nube en cada ventana (la mediana va de 6 fechas en agosto a 32 en el ciclo).
- Casi redundantes (|rho de Spearman| >= 0.95 entre parcelas): NDTI-STI 0.999; CV de SAVI-CV de EVI 0.997; EMSI-ENDWI -0.995; STD de SAVI-STD de EVI 0.985; MSI-ENDWI -0.984; MSI-EMSI 0.981; MSI-DSWI5 -0.964; DSWI5-ENDWI 0.963; MCRC-NDSVI (PRE) 0.951; NDWI(A)-NDDI(A) -0.950; CV SAVI-CV NDVI 0.950. En total 39 de 496 pares con |rho| >= 0.85.
- Frente a un índice de vigor de S2 en jul-sep: FAPAR 0.98 con SAVI (casi el mismo dato), ENDWI 0.89, EMSI -0.88, MSI -0.86, DSWI4 0.91, DSWI5 0.89. Poco redundantes con vigor: NDDI jul-sep (-0.53), DSWI2 (-0.34), ENDDI (-0.31), SRNDI (-0.08).
- Escala rara: STI, MSI, EMSI y DSWI2-5 son razones solo positivas y sin tope (valores por lectura hasta 2.4, 2.1, 1.8 y 3.9); CRC, MCRC y NDSVI llegan a valores negativos en fechas de suelo desnudo (mínimos -0.51, -0.36, -0.22); MRA toma unos 22 valores entre 0.020 y 0.041 (su std es 0.000 en 61% de las lecturas); VI6T es siempre negativo y varía poco entre parcelas (-0.655 a -0.615).
- Parcelas menores de 1.44 ha: 18 con `area_calculada_ha` (13 de entrenamiento, 5 de predicción); 9 menores de 1 ha y 4 menores de 0.5 ha. La mediana de 5.42 ha son unos 542 píxeles de 10 m; la más chica, unos 35. La correlación de las variables de variabilidad con log(área) es débil (|rho| <= 0.13).

## Avisos
- La hoja E dice 17 parcelas menores de 1.44 ha; con `area_calculada_ha` salen 18 (con `AREA_HA_SHP` salen 17).
- En 2025, 723 de 10,936 filas Landsat no traen nubosidad (ninguna trae VI6T) y en todos los años hay 4,657 filas S2 y 2,976 Landsat con nubosidad >= 20 pero con índices no vacíos; todas se excluyen por la regla.
- FAPAR de jul-sep es casi un duplicado del SAVI de jul-sep (0.98): si SAVI ya se evaluó, HI1 aporta sobre todo por la versión de CICLO (0.79 con SAVI).
- Cinco parcelas tienen 1 o 2 lecturas Landsat válidas en jul-sep; VI6T de esas parcelas es poco confiable.
- Las CV de S2 (SAVI, NDVI, EVI) y sus desviaciones casi se copian entre sí; se probarán como grupo, no como evidencia independiente.

## Preguntas para Jared
1. ¿Se conserva `sat_fapar_s2_jul_sep` dado que duplica al SAVI, o solo se prueba el de CICLO?
2. ¿HI8 (signo negativo) vale la pena con su razón débil, o se deja como exploratoria sin signo?
3. ¿Se aceptan las 17 de primer orden como el conjunto principal y las otras 15 como exploratorias?
