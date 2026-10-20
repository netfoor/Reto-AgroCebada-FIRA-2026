# Bloque B: Estreses climáticos de la cebada maltera (hoja de una página)

Marcas: **[V]** verificado (texto completo leído y citado) · **[V-parcial]** visto solo en un extracto, en un resumen o en un documento de otro país o cultivo ·
**[PV]** por verificar · **[CP]** cálculo o razonamiento propio. Preparada el 2026-09-20. Continúa `A_fenologia.md` (mismas etapas Zadoks y mismas
fechas de siembra). En las hipótesis, "signo" es la relación esperada con el rendimiento.

## 1. Los cuatro estreses

| Estrés | Etapa en que daña | Qué dicen las fuentes (cebada) | Umbral con fuente de cebada |
|---|---|---|---|
| **Helada temprana de otoño** | Llenado y madurez de las siembras tardías | Las primeras heladas "se presentan en la última semana de septiembre" **[V]** (INIFAP Tlaxcala 2017, p. 27). Con siembra tardía en ambientes medianos y bajos "la cosecha tiene mayor riesgo de perderse por el daño de las primeras heladas" **[V]**. Estación corta (menos de 100 días) "determinada por heladas de otoño" en ambientes de baja productividad **[V]**. La cebada madura pronto y permite sembrar tarde con menos riesgo **[V]** (Calderón-García et al., 2015) | Sin umbral en °C de fuente mexicana **[PV]** |
| **Helada en espigado y floración** | Desde la emergencia de aristas (Z49) **[V]**; ventana reportada de 40 a 10 días antes del espigado en cebada de dos hileras **[V-parcial]** | Espiguillas vanas, estigmas apelmazados y anteras deformes **[V]** (INIA Uruguay, 2022). Helada de primavera: menos de 0 °C en el cultivo o menos de 2 °C en caseta **[V-parcial]** | Aire dentro del cultivo bajo −3.5 °C, la planta puede llegar a −5 °C **[V]**. Daño importante con −4 a −5 °C en el cultivo **[V-parcial]** (Frederiks et al., 2015). Son datos de Uruguay y Australia, no de México |
| **Calor en el llenado** | Llenado de grano (Z7 a Z8) | Óptimo de 15 °C durante el llenado; días sobre 30 °C dañan **[V]** (Shirdelmoghanloo et al., 2022). Crecimiento inicial del grano óptimo a 16 a 19 °C y al final a 24 °C; de 25 a 32 °C todo el llenado acelera el proceso y baja el peso; 3 a 5 días de calor muy alto reducen número y peso de granos **[V]** (capítulo UNLP, que cita a otros autores). Calor de 15 a 20 días después de antesis bajó el peso cerca de 35% y calor moderado desde ahí hasta madurez cerca de 6% **[V-parcial]**. Variedades modernas más sensibles **[V-parcial]** (Passarella et al., 2005) | Referencia de 30 °C (máxima diaria) **[V]**. Sin dato mexicano **[PV]**. Tablas mexicanas de temperatura media del ciclo: 12 a 18 °C apta, 18 a 22 moderada, 22 a 26 marginal, más de 26 no apta **[V]** (Calderón-García et al., 2015; requisitos tomados de libros, no de ensayos **[PV]**) |
| **Sequía** | Establecimiento; periodo crítico alrededor de la floración (define el número de granos); llenado | Menos agua en el establecimiento y en el periodo crítico baja el rendimiento potencial **[V]** (UNLP). La "canícula" afecta floración y llenado **[V]** (INIFAP Tlaxcala 2017). En 2013 la falta de agua en el llenado dio grano más chico y liviano, menos granos por espiga y menor peso hectolítrico, con caídas de rendimiento de hasta 50% en un sitio **[V]** (González et al., 2016; cinco sitios, uno en Calpulalpan). Sequía en espigado bajó cerca de 48% el rendimiento en cebada de invierno **[V-parcial]** | Lluvia de mayo a octubre: más de 550 mm muy buena, hasta 500 buena, 450 a 500 mediana, menos de 450 baja **[V]** (INIFAP Tlaxcala). Hidalgo: más de 600, 500 a 600, 450 a 500, menos de 450 **[V-parcial]** |
| **Exceso de humedad** | Siembra a macollaje (pérdida de plantas); crecimiento rápido; más enfermedades en el llenado (ver bloque C) | "Excesos de humedad en las primeras etapas" pueden causar pérdida de plantas **[V]** (UNLP). Calpulalpan 2009 y 2011: rendimiento SIAP de 1.8 y 0.47 t/ha contra 2.53 de promedio 2003 a 2012; los autores lo atribuyen a lluvia muy abundante, granizo y lluvias de hasta 50 mm al inicio del ciclo **[V]**, pero es interpretación de ellos **[PV]**. Con dos meses de anegamiento en etapa de 2 a 3 hojas la cebada perdió de 30 a 70% **[V-parcial]** (GRDC, Australia). Se pierde nitrógeno por desnitrificación y lavado **[V-parcial]** | Lluvia del ciclo: 400 a 500 mm apta, 500 a 600 moderada, 600 a 700 marginal, más de 700 no apta **[V]** (Calderón-García et al., 2015, mismo límite de origen **[PV]**) |

## 2. Cómo se vería en nuestros datos y sus límites

Nuestros datos: Tmin y Tmax son el promedio mensual de las mínimas y máximas diarias de CHIRTS-ERA5, en celdas de 0.05° **[V]** (LEEME del dataset); la
lluvia es CHIRPS mensual en mm, también de 0.05° **[V]** (inventario del dataset). Solo hay rendimiento de la campaña 2025.

| Estrés | Variable mensual | Cómo se vería | Límite principal |
|---|---|---|---|
| Helada temprana | Tmin de sep y oct | Tmin baja en el mes de llenado | El promedio de mínimas no cuenta las noches bajo 0 °C **[CP]** |
| Helada en espigado | Tmin de jul y ago | Igual, según la fecha de siembra | Además no sabemos cuándo espigó cada parcela **[PV]** |
| Calor | Tmax de ago y sep | Tmax alta | El promedio de máximas esconde los días sobre 30 °C **[CP]** |
| Sequía | Lluvia de jun a sep, mes más seco | Un mes bajo en floración o llenado | Los mm mensuales no muestran periodos secos dentro del mes **[CP]** |
| Exceso | Lluvia de jun y total del ciclo | Valores muy altos | No hay datos de suelo, drenaje ni granizo |

Límites generales:
- Los umbrales de helada son de temperatura en el cultivo; la diferencia con la caseta es del orden de 1.5 a 2 °C **[V-parcial]**, y no sabemos cuánto se parece el
  dato de reanálisis a la temperatura dentro del cultivo **[PV]**.
- La helada es local: el aire frío se acumula en hondonadas ("bolsas de helada") **[V-parcial]** (tesis UNAM, 1988, teoría general, no cebada). Una celda de 5.5 km no lo ve.
- Con una sola campaña con rendimiento solo vemos diferencias entre parcelas, no entre años. Ra Ximhai usó diez años de SIAP. Los climas 2022 a 2024 permitirían ver
  si 2025 fue atípico **[CP]** (no analizado aquí).
- Pocas celdas por región significan poca variación de clima dentro de región. Conviene contar celdas por región antes de probar cualquier hipótesis **[CP]**.
- Sin fecha de siembra, las ventanas de meses son aproximadas (ver A).

## 3. Lo que no debemos afirmar todavía
- Un umbral de helada o de calor de cebada para México. Los que hay vienen de Uruguay, Australia y Argentina.
- Que la lluvia de Singuilucan explica su menor rendimiento. Es solo una hipótesis. Su lluvia de abril a octubre (1,135 a 1,335 mm) equivale a entre 1.6 y 1.9 veces el
  límite de "no apta" (700 mm) **[CP]**; nuestro ciclo (abril a octubre) es más largo que el de las tablas (mayo a octubre), así que la comparación es aproximada. Dos
  explicaciones posibles, ambas **[PV]**: un año muy húmedo, o sobreestimación de CHIRPS en zonas de sierra o mezcla de celda. Se aclara con estaciones o con los organizadores.
- Que la causa de los rendimientos bajos de Calpulalpan en 2009 y 2011 fue el exceso de humedad. Es lo que dicen los autores, no una prueba.
- Que el calor limita la cebada en Valles Altos **[PV]**.

## 4. Hipótesis medibles (todas dentro de cada región; se registran antes de probarlas)

Aplican también A1, A3, A4, A5 y A6 de `A_fenologia.md`.

| # | Hipótesis (variable, signo, por qué) | Dato disponible | Limitación |
|---|---|---|---|
| B1 | **Calor de llenado.** Tmax de ago y sep, signo −: más calor acorta el llenado y baja el peso del grano **[V]**. Efecto esperado débil en Valles Altos **[PV]** | Tmax mensual por parcela | Promedio de máximas; el daño es por días sobre 30 °C |
| B2 | **Mes más seco de jun a sep** (proxy de canícula), signo +: un mes muy seco en floración o llenado baja granos y peso **[V]** | Lluvia mensual CHIRPS | Un mes seco puede caer en una etapa poco sensible; no vemos días secos |
| B3 | **Lluvia de junio** (inicio del ciclo), forma curva: muy alta baja el rendimiento por pérdida de plantas **[V]**; muy baja también | Lluvia de junio | Junio puede ser antes de sembrar; poca variación dentro de región |
| B4 | **Lluvia total del ciclo, forma curva** dentro de región: sube y luego baja. Zona de mejor respuesta entre 400 y 700 mm según las tablas **[V]** | Suma CHIRPS del ciclo | Nuestro ciclo no es el de las tablas; se espera que Singuilucan caiga en el tramo descendente **[PV]** |
| B5 | **Altitud** de la parcela, signo −: más alto es más frío (0.5 °C por cada 100 m **[V-parcial]**) y con estación de crecimiento más corta **[V]** | Elevación del DEM | Se confunde con lluvia y suelo; el signo es incierto **[PV]** |
| B6 | **Pendiente por lluvia.** Con lluvia alta los terrenos casi planos encharcan (signo −); con lluvia baja lo plano retiene humedad (signo +). INIFAP asocia pendientes menores de 4% con buenos ambientes **[V]** | Pendiente y CHIRPS | Es la pendiente de la parcela, no su posición en el paisaje ni su drenaje |
| B7 | **Caída del NDVI de Planet después del máximo,** signo −: senescencia acelerada por sequía tardía, helada o enfermedad **[PV]** | NDVI Planet 2025 | La maduración normal también lo baja; se confunde con la fecha de siembra; nubes |
| B8 | **Rango térmico de septiembre** (Tmax menos Tmin), signo − débil: noches despejadas favorecen la helada de radiación **[V-parcial]** | Tmax y Tmin | Proxy pobre; también refleja sequedad y altitud **[PV]** |

## 5. Preguntas de repaso (Bloque B)
1. ¿Desde qué etapa la cebada es más sensible a la helada, y por qué un umbral medido en caseta no equivale al de la planta?
2. Una parcela sembrada el 25 de junio llega a madurez a los 98 a 106 días. ¿En qué fechas cae su madurez y qué dice INIFAP Tlaxcala sobre esas fechas?
3. ¿Por qué una Tmin mensual de un mes de septiembre no nos dice si hubo helada?
4. ¿Qué mes de lluvia miraría para sospechar sequía en el llenado y cuál para sospechar exceso de humedad al inicio del ciclo, y por qué?
5. Singuilucan tiene entre 1,135 y 1,335 mm de lluvia y rinde menos. Da una explicación agronómica y una explicación de los datos, y di cómo separarías una de otra.

## 6. Preguntas para los organizadores (del bloque B)
- ¿Hubo heladas o granizo en 2025 en estas parcelas? ¿En qué fechas?
- Fecha de siembra y de cosecha de cada parcela, y variedad.
- ¿Temporal puro o con riego de auxilio?
- ¿De dónde salen las lluvias de Singuilucan (1,135 a 1,335 mm) y hay estaciones que las confirmen?

## Fuentes (estado)
Lectura de texto completo: convertidor a markdown (Agenda Tlaxcala, Ra Ximhai, González, Estrada, tesis UNAM, capítulo UNLP). Los demás: extracto con citas de la herramienta de lectura web.

- INIFAP, Agenda Técnica Agrícola Tlaxcala 2017, cebada (pp. 25 a 30): https://vun.inifap.gob.mx/VUN_MEDIA/BibliotecaWeb/_media/_agendas/4146_4843_Agenda_T%C3%A9cnica_Tlaxcala_2017.pdf **leída (completa)**
- INIFAP, Agenda Técnica Agrícola Hidalgo 2017: https://vun.inifap.gob.mx/VUN_MEDIA/BibliotecaWeb/_media/_agendas/4131_4828_Agenda_T%C3%A9cnica_Hidalgo_2017.pdf **leída (extracto)**
- Calderón-García, Monterroso-Rivas y Gómez-Díaz (2015), Ra Ximhai 11(5): 37 a 46: https://www.redalyc.org/pdf/461/46142593002.pdf **leída (completa)**
- González, Zamora y Solano (2016), líneas avanzadas de cebada maltera, Rev. Mex. Cienc. Agríc.: https://www.redalyc.org/pdf/2631/263144153014.pdf **leída (completa)**
- Da Silva y Dietz, cap. 15, Cebada cervecera: época y densidad de siembra (UNLP, Argentina): https://sedici.unlp.edu.ar/bitstream/handle/10915/156557/Documento_completo.pdf-PDFA.pdf?sequence=1&isAllowed=y **leída (completa)**
- Estrada, Martínez y Morales (UAEMex), trigo y cebada en Valles Altos: http://www.metrice.udl.cat/es/misc/taller_valdivia/1.6%20Trigo%20y%20Cebada%20en%20Mexico%20(Estrada%20et%20al.).pdf **leída (completa)**; no trae heladas ni exceso de humedad, y su Cuadro 1 es de localidades de trigo
- Morales Méndez (1988), tesis UNAM sobre heladas en Tlaxcala: http://huertofenologico.filos.unam.mx/files/2015/11/Las-heladas-y-sus-consecuencias-en-algunos-cultivos-en-el-estado-de-Tlaxcala-.-.pdf **leída (solo capítulo I, teoría general; copia incompleta; sin datos de cebada ni de Tlaxcala)**
- INIA Uruguay (2022), Vaneo en trigo y cebada causado por heladas: https://ainfo.inia.uy/digital/bitstream/item/16798/1/Revista-INIA-70-setiembre-2022-17.pdf **leída (extracto, dos lecturas coinciden)**
- Shirdelmoghanloo et al. (2022), Frontiers in Plant Science: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2022.858652/full **leída (extracto, dos lecturas coinciden)**
- Frederiks et al. (2015), J. Exp. Bot. 66(12): https://academic.oup.com/jxb/article/66/12/3487/524420 **leída (extracto)**
- Frontiers (2021), heladas en trigo y cebada en Australia: https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2021.722637/full **leída (extracto)**
- Passarella et al. (2005), Euphytica: https://link.springer.com/article/10.1007/s10681-005-5068-4 **leída (resumen)**
- Calor y calidad maltera, Aust. J. Agric. Res. (según la URL, vol. 48, núm. 5, p. 615; autores sin leer **[PV]**): https://connectsci.au/cp/article-abstract/48/5/615/32918/Grain-growth-and-malting-quality-of-barley-1 **leída (resumen)**
- GRDC, anegamiento en cebada: https://grdc.com.au/resources-and-publications/grdc-update-papers/tab-content/grdc-update-papers/2022/02/improving-waterlogging-tolerance-of-barley-varieties y https://groundcover.grdc.com.au/innovation/climate/crop-growth-stage-the-key-to-effects-of-waterlogging **leídas (extracto)**
- Sequía en cebada de invierno: https://pmc.ncbi.nlm.nih.gov/articles/PMC12309998/ **leída (extracto)**
- **No accesibles:** Masoni et al. (2016), Crop Science, y Ciancio et al. (2021), J. Agron. Crop Sci. (Wiley, error 403); PMC12081993 (verificación anti robots); Samarah (2005) en ResearchGate (error 429). El Manual de trigo y cebada para el Cono Sur se consultó y no trae cifras de estreses de cebada.
- **Buscado sin éxito:** umbral de helada de cebada en fuente mexicana (búsquedas "heladas cebada maltera Valles Altos INIFAP Tlaxcala" y "cebada temperatura mínima helada umbral México"); serie de días con helada en Calpulalpan o Llanos de Apan (solo notas de prensa); estudios mexicanos de anegamiento en cebada.
