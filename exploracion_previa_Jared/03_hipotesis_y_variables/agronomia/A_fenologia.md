# Bloque A — Fenología y etapas críticas de la cebada maltera (hoja de una página)

Marcas: **[V]** verificado con fuente leída · **[V-parcial]** visto solo en resumen de búsqueda o en un manual de *trigo* ·
**[PV]** por verificar · **[CP]** cálculo propio a partir de datos verificados. Preparada el 2026-09-20.

## 1. Etapas (escala Zadoks, código de 2 dígitos)

| Zadoks | Etapa | Qué pasa | Nota |
|---|---|---|---|
| 0 | Germinación | Semilla → plántula | **[V]** 10 estadios principales, FAO/SAG |
| 1 | Hojas | Crece el tallo principal (Z1.4 = 4 hojas) | **[V]** |
| 2 | Macollos | Se forman tallos secundarios (Z2.2 = 2 macollos) | **[V]** el nº de macollos es el primer componente del rendimiento **[V-parcial]** |
| 3 | Encañado | Alargamiento del tallo, nudos | **[V]** |
| 4 | Vaina engrosada | La espiga viaja dentro de la vaina | **[V]** |
| 5 | Espigado | Z5.1 = 10% de espigas emergidas; Z5.9 = 90% | **[V]** |
| 6 | Antesis (floración) | Z6.5 = mitad de la floración | **[V]** |
| 7 | Grano lechoso | Empieza el llenado de grano | **[V]** |
| 8 | Grano pastoso | Se acumula el almidón | **[V]** |
| 9 | Madurez | Grano seco | **[V]** |

## 2. Duración en Valles Altos (temporal, siembra de primavera-verano)

- Floración/espigamiento: **45–72 días después de la siembra** según variedad. Adabella 48–72 d, Maravilla 45–57 d,
  líneas de Calpulalpan 46–57 d. **[V]**
- Madurez fisiológica: **90–132 días** (Adabella 90–132, Maravilla 94–115, Calpulalpan 98–106). **[V]**
- Cosecha con 13–14% de humedad, 20–25 días después de la madurez. **[V]** (INIFAP, 2022)
- **Fecha de siembra recomendada:** 1 mayo–15 junio (ambientes buenos, >500 mm); 1–30 junio (medianos, 450–500 mm);
  10–30 junio (bajos, <450 mm). **[V]**

**Calendario resultante (cálculo propio, [CP]; supone las duraciones de arriba y que la siembra ocurrió en esas fechas):**

| Siembra | Floración | Madurez fisiológica | Cosecha (+20–25 d) |
|---|---|---|---|
| 1 mayo | 15 jun – 12 jul | 30 jul – 10 sep | hasta ≈ 5 oct |
| 15 junio | 30 jul – 26 ago | 13 sep – 25 oct | hasta ≈ 19 nov |

**Consecuencia para nuestros datos:** la ventana "abril–octubre" incluye abril (antes de sembrar) y puede dejar fuera la
cosecha de las siembras tardías (noviembre). Las fechas de siembra reales **no las tenemos [PV]**: es la pregunta #1 a los
organizadores.

## 3. Qué define el rendimiento

- Tres componentes: **espigas por m²**, **granos por espiga** y **peso de mil granos**. El nº de espigas/m² es el que más
  aporta en cereales de grano pequeño **[V-parcial]**; los granos por espiga dependen del nº de flores formadas **[V-parcial]**.
- Qué etapa define cada uno (macollaje → espigas/m²; encañado–antesis → granos/espiga; llenado → peso del grano) es
  fisiología general de cereales. **[PV]** con fuente específica de cebada.
- Periodo más sensible: el que va del final del encañado a una semana después de la antesis (Z3.3–Z7.05): la radiación
  baja con temperatura alta reduce el nº de granos. **[V-parcial]** (manual FAO de *trigo*)

## 4. Lo que no debemos afirmar todavía
- Umbrales exactos de helada o calor **para cebada**: lo leído es de trigo (FAO): tallos vegetativos mueren a −5 °C;
  heladas entre espigado (Z5.1) y grano lechoso (Z7.1) son críticas; el rendimiento cae hasta 4% por cada °C durante el
  llenado; 1.5 °C en la caseta ≈ 0 °C a nivel del cultivo. **[V-parcial]**
- El rendimiento nacional "medio de 2 t/ha" salió solo en un resumen de búsqueda. **[PV]** Nuestros datos: 2.0–5.59 t/ha,
  media 3.96; los ensayos INIFAP de temporal reportan 1.7–6.9 t/ha (2012–2013) y 2.1–5.2/2.9–5.4 para variedades. **[V]**

## 5. Hipótesis medibles con nuestros datos (se registran antes de probarlas; todas dentro de región)

| # | Hipótesis (variable, signo, por qué) | Dato disponible | Limitación |
|---|---|---|---|
| A1 | **Siembra tardía ⇒ menor rendimiento.** Fecha en que el NDVI de PRO cruza un umbral (proxy de emergencia) y rendimiento: signo −. Más helada temprana y menos ciclo | PRO (Planet 2025) por fecha | Nubes de jun–oct; el umbral hay que elegirlo |
| A2 | **Ciclo largo ⇒ más rendimiento** hasta un punto: días entre el ascenso y la caída del NDVI, signo + | PRO 2025 | Igual que A1; suavizado necesario |
| A3 | **NDVI máximo del ciclo** (vigor en espigado) se asocia + con el rendimiento | PRO y Básico S2 | Saturación del NDVI a valores altos (ver 1B) |
| A4 | **Tmin de jul–ago** (espigado/floración de siembras de mayo–junio): signo dentro de región, sin fijar | `temperatura_mensual_por_parcela.csv` | Datos mensuales; heladas son eventos diarios |
| A5 | **Tmin de sep–oct** (llenado; heladas tempranas): signo + (más frío ⇒ más daño) | igual | igual |
| A6 | **Lluvia de jun–jul** (macollaje/encañado): + ; **de ago–sep** (llenado): sin signo fijo | `precipitacion_mensual_por_parcela.csv` | Celdas de 5.5 km |

## 6. Preguntas de repaso (Bloque A)
1. ¿Cuántos estadios principales tiene la escala Zadoks y qué es Z6.5?
2. Una parcela sembrada el 15 de junio: ¿en qué meses cae aproximadamente su floración y su madurez?
3. ¿Cuáles son los tres componentes del rendimiento y cuál suele aportar más?
4. ¿Por qué el periodo entre espigado y grano lechoso es tan sensible a heladas?
5. ¿Por qué la ventana "abril–octubre" que usamos en el EDA puede no ser la correcta?

## Fuentes
- FAO, escala decimal Zadoks: https://www.fao.org/4/x8234s/x8234s05.htm (manual de diagnóstico de trigo) y factores
  ambientales: https://www.fao.org/4/x8234s/x8234s08.htm
- SAG (Chile), escala de desarrollo de cereales: https://www.sag.gob.cl/curso-de-semillas/4-escala-de-medicion-del-desarrollo-de-cereales
- INIFAP (R. Gómez Mercado, 2022), cebada maltera de temporal: https://www.gob.mx/inifap/articulos/cebada-maltera-de-temporal-en-valles-altos-de-mexico
- Zamora et al. (2008), variedad Adabella, Agricultura Técnica en México 34(4): https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S0568-25172008000400012
- Zamora et al. (2017), variedad Maravilla, Rev. Mex. Cienc. Agríc. 8(6): https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S2007-09342017000601449
- Líneas avanzadas de cebada maltera (Calpulalpan, Tlax.), Rev. Mex. Cienc. Agríc. 7(1), 2016: https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S2007-09342016000100159
- Componentes del rendimiento (resultados de búsqueda; no leído a fondo): https://www.scielo.org.co/scielo.php?script=sci_arttext&pid=S0123-42262011000200006
- **No se pudieron leer:** Agenda Técnica INIFAP Tlaxcala 2017 (error 403), presentación de Estrada et al. y el documento de
  la UNAM sobre heladas en Tlaxcala (servidor no responde). Se reintentarán.
- No aplica a nuestro caso: Gómez-Espinoza et al. (2025), Celaya, Gto., **riego** otoño-invierno, 4.2–7.4 t/ha.
