# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/55_variables_sat_indices17.R). Original: preparacion/scripts/55_variables_sat_indices17.R.
# ==============================================================================
# 55_variables_sat_indices17.R  --  Familia 5: los 17 indices satelitales sin evaluar
# Reto AgroCebada FIRA 2026
#
# Proposito: construir variables candidatas (medias de ventana y variabilidad dentro de
# la parcela) para las 197 parcelas, con el mismo codigo para todas y SIN mirar el
# rendimiento. Las hipotesis se escriben aqui y se registran despues, antes de probar.
#
# Definiciones fijas:
#   Observacion valida = porcentaje_nubosidad < 20 (NA en nubosidad no cuenta) y valor no vacio.
#   media de ventana   = promedio de la columna _promedio en las observaciones validas.
#   std de ventana     = promedio de la columna _std en las mismas observaciones validas
#                        (deben tener tambien _std no vacia).
#   cv de ventana      = promedio de (_std / |_promedio|) solo en observaciones con
#                        |_promedio| > 0.05.
#   Sin observaciones validas en la ventana -> NA (no se imputa).
# Ventanas (2025): pre = feb-may, a = abr-may, jul_sep = jul-sep, ago = agosto,
#                  ciclo = abr-oct.
# Sufijo de sensor: _s2, _landsat, _planet (nunca se mezclan). No se usa LAI.
#
# Entradas (solo lectura, sin rendimiento):
#   01_datos/originales/Conjunto_datos_BASICO_AgroCebada2026.csv
#   01_datos/originales/Conjunto_datos_PRO_AgroCebada.csv
#   01_datos/preparados/base_197_ubicacion.csv, 01_datos/derivados/parcelas_atributos.csv
# Salidas (03_hipotesis_y_variables/variables/):
#   sat_indices17_features.csv, sat_indices17_diccionario.csv, sat_indices17_hipotesis.csv
#   log en 04_resultados/logs/55_variables_sat_indices17.log
# Como correr:
#   Rscript 03_hipotesis_y_variables/scripts/55_variables_sat_indices17.R
# Sin azar en este script.
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
SAL  <- file.path(PREP, "03_hipotesis_y_variables/variables")
dir.create(SAL, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/55_variables_sat_indices17.log"),
                open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 55_variables_sat_indices17.R ==\n")
cat("R:", R.version.string, "| readr", as.character(packageVersion("readr")),
    "| dplyr", as.character(packageVersion("dplyr")),
    "| tidyr", as.character(packageVersion("tidyr")),
    "| tibble", as.character(packageVersion("tibble")), "\n\n")

ANIO       <- 2025L
UMBRAL_NUB <- 20
UMBRAL_CV  <- 0.05
VENTANAS   <- list(pre = 2:5, a = 4:5, jul_sep = 7:9, ago = 8L, ciclo = 4:10)

# ---- 1. Lista oficial de parcelas y datos satelitales ------------------------
ubic <- read_csv(file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"),
                 show_col_types = FALSE, progress = FALSE)
IDS <- ubic$ID_POLIGONO
stopifnot(length(IDS) == 197, !anyDuplicated(IDS))

tipos_col <- cols(.default = col_double(), ID_POLIGONO = col_character(),
                  fecha_captura = col_character(), sensor = col_character())
DS <- file.path(RAIZ, "01_datos/originales")
basico <- read_csv(file.path(DS, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
                   col_types = tipos_col, progress = FALSE)
pro    <- read_csv(file.path(DS, "Conjunto_datos_PRO_AgroCebada.csv"),
                   col_types = tipos_col, progress = FALSE)
stopifnot(names(basico)[1] == "ID_POLIGONO", names(pro)[1] == "ID_POLIGONO",
          all(basico$ID_POLIGONO %in% IDS), all(pro$ID_POLIGONO %in% IDS))

preparar <- function(d) {
  d$fecha <- as.Date(d$fecha_captura, format = "%d/%m/%Y")
  stopifnot(!any(is.na(d$fecha)))
  d$anio <- as.integer(format(d$fecha, "%Y"))
  d$mes  <- as.integer(format(d$fecha, "%m"))
  d[d$anio == ANIO, ]
}
FUENTE <- list(
  s2      = preparar(filter(basico, sensor == "Sentinel-2")),
  landsat = preparar(filter(basico, sensor == "Landsat")),
  planet  = preparar(pro)
)
for (s in names(FUENTE)) {
  cat(sprintf("Fuente %-8s: %6d filas en %d | nubosidad NA: %d | sin nube (<%d): %d\n",
              s, nrow(FUENTE[[s]]), ANIO, sum(is.na(FUENTE[[s]]$porcentaje_nubosidad)),
              UMBRAL_NUB, sum(FUENTE[[s]]$porcentaje_nubosidad < UMBRAL_NUB, na.rm = TRUE)))
}
cat("\n")

# ---- 2. Especificacion de variables ------------------------------------------
# tipo: media | std | cv. primer_orden: variable elegida como de primer orden antes de ver
# resultados (por el diccionario y por las hipotesis ya registradas).
mk <- function(indice, tipo, sensor, ventana, hip, primer = FALSE) {
  tibble(indice = indice, tipo = tipo, sensor = sensor, ventana = ventana,
         hipotesis_id = hip, primer_orden = primer)
}
ESPEC <- bind_rows(
  # HR9: residuo, labranza y suelo antes de la siembra (feb-may)
  mk("crc",   "media", "s2", "pre", "HR9", TRUE),
  mk("mcrc",  "media", "s2", "pre", "HR9", TRUE),
  mk("ndti",  "media", "s2", "pre", "HR9", TRUE),
  mk("sti",   "media", "s2", "pre", "HR9", TRUE),
  mk("ndsvi", "media", "s2", "pre", "HR9", TRUE),
  # HR14: senescencia en agosto
  mk("ndsvi", "media", "s2", "ago", "HR14", TRUE),
  # HR3: humedad antes de la siembra (abr-may), exploratoria
  mk("ndwi",  "media", "s2", "a", "HR3"),
  mk("nddi",  "media", "s2", "a", "HR3"),
  # HR13: estres hidrico espectral en jul-sep
  mk("msi",   "media", "s2", "jul_sep", "HR13", TRUE),
  mk("emsi",  "media", "s2", "jul_sep", "HR13", TRUE),
  mk("nddi",  "media", "s2", "jul_sep", "HR13", TRUE),
  mk("enddi", "media", "s2", "jul_sep", "HR13", TRUE),
  # HI5: parte exploratoria de HR13
  mk("dswi2", "media", "s2", "jul_sep", "HI5"),
  mk("dswi3", "media", "s2", "jul_sep", "HI5"),
  mk("dswi4", "media", "s2", "jul_sep", "HI5"),
  mk("dswi5", "media", "s2", "jul_sep", "HI5"),
  # HI1: vigor y fotosintesis
  mk("fapar", "media", "s2", "jul_sep", "HI1", TRUE),
  mk("fapar", "media", "s2", "ciclo",   "HI1", TRUE),
  # HI2: agua
  mk("endwi", "media", "s2", "jul_sep", "HI2", TRUE),
  # HI3: exploratorios de significado incierto
  mk("srndi", "media", "s2", "jul_sep", "HI3"),
  mk("mra",   "media", "s2", "ciclo",   "HI3"),
  # HI4: espectral-termico
  mk("vi6t",  "media", "landsat", "jul_sep", "HI4"),
  # HR6 y HI6: coeficiente de variacion dentro de la parcela (jul-sep)
  mk("savi", "cv", "s2",     "jul_sep", "HR6", TRUE),
  mk("ndvi", "cv", "planet", "jul_sep", "HR6", TRUE),
  mk("ndvi", "cv", "s2",     "jul_sep", "HI6", TRUE),
  mk("evi",  "cv", "s2",     "jul_sep", "HI6", TRUE),
  # HI7: desviacion absoluta dentro de la parcela (jul-sep), exploratoria
  mk("savi", "std", "s2",     "jul_sep", "HI7"),
  mk("ndvi", "std", "s2",     "jul_sep", "HI7"),
  mk("evi",  "std", "s2",     "jul_sep", "HI7"),
  mk("ndvi", "std", "planet", "jul_sep", "HI7"),
  # HI8: heterogeneidad de suelo y agua
  mk("ndti", "std", "s2", "pre",     "HI8"),
  mk("msi",  "cv",  "s2", "jul_sep", "HI8")
)
ESPEC$variable <- paste0("sat_", ESPEC$indice,
                         ifelse(ESPEC$tipo == "media", "", paste0("_", ESPEC$tipo)),
                         "_", ESPEC$sensor, "_", ESPEC$ventana)
stopifnot(!anyDuplicated(ESPEC$variable), nrow(ESPEC) <= 90)
cat("Variables construidas:", nrow(ESPEC), "| de primer orden:", sum(ESPEC$primer_orden), "\n\n")

# ---- 3. Calculo ---------------------------------------------------------------
calc_var <- function(fuente, indice, tipo, meses) {
  cp <- paste0(indice, "_promedio")
  cs <- paste0(indice, "_std")
  x <- fuente %>%
    filter(mes %in% meses, !is.na(porcentaje_nubosidad), porcentaje_nubosidad < UMBRAL_NUB) %>%
    transmute(ID_POLIGONO, m = .data[[cp]], s = .data[[cs]])
  x <- switch(tipo,
    media = x %>% filter(!is.na(m)) %>% mutate(v = m),
    std   = x %>% filter(!is.na(m), !is.na(s)) %>% mutate(v = s),
    cv    = x %>% filter(!is.na(m), !is.na(s), abs(m) > UMBRAL_CV) %>% mutate(v = s / abs(m)))
  r <- x %>% group_by(ID_POLIGONO) %>%
    summarise(valor = mean(v), n_obs = n(), .groups = "drop")
  tibble(ID_POLIGONO = IDS) %>%
    left_join(r, by = "ID_POLIGONO") %>%
    mutate(n_obs = coalesce(n_obs, 0L))
}

feat <- tibble(ID_POLIGONO = IDS)
nobs <- list()
for (i in seq_len(nrow(ESPEC))) {
  e <- ESPEC[i, ]
  r <- calc_var(FUENTE[[e$sensor]], e$indice, e$tipo, VENTANAS[[e$ventana]])
  feat[[e$variable]] <- r$valor
  nobs[[e$variable]] <- r$n_obs
}
stopifnot(nrow(feat) == 197, identical(feat$ID_POLIGONO, IDS))

# ---- 4. Escala de cada indice (observaciones validas 2025, todas las parcelas) --
escala <- function(fuente, indice) {
  m <- fuente[[paste0(indice, "_promedio")]]
  ok <- !is.na(fuente$porcentaje_nubosidad) & fuente$porcentaje_nubosidad < UMBRAL_NUB & !is.na(m)
  m <- m[ok]
  tibble(min = min(m), p1 = unname(quantile(m, 0.01)), mediana = median(m),
         p99 = unname(quantile(m, 0.99)), max = max(m),
         pct_abs_bajo = 100 * mean(abs(m) <= UMBRAL_CV), n_obs = length(m))
}
pares <- distinct(ESPEC, indice, sensor)
ESC <- bind_cols(pares, bind_rows(lapply(seq_len(nrow(pares)), function(i)
  escala(FUENTE[[pares$sensor[i]]], pares$indice[i]))))
cat("Escala de cada indice (obs. validas 2025, todas las parcelas):\n")
print(as.data.frame(mutate(ESC, across(where(is.numeric), ~ round(.x, 3)))), row.names = FALSE)
cat("\n")

# ---- 5. Diccionario -------------------------------------------------------------
TXT_VENT <- c(pre = "febrero-mayo 2025 (PRE)", a = "abril-mayo 2025 (ventana A)",
              jul_sep = "julio-septiembre 2025", ago = "agosto 2025",
              ciclo = "abril-octubre 2025 (CICLO)")
TXT_SENS <- c(s2 = "Sentinel-2", landsat = "Landsat", planet = "Planet (PRO)")
TXT_VENT_MOTIVO <- c(
  pre = paste("Ventana PRE: antes de la siembra (recomendada 1 mayo-15 junio [V], A_fenologia.md) el suelo y el rastrojo",
              "del ciclo anterior estan expuestos y el cultivo aun no cubre el suelo; es la ventana de HR9. Los pocos casos de",
              "siembra en mayo pueden mezclar cultivo emergente al final de la ventana [PV]."),
  a   = "Ventana A comun de la Semana 2 (abr-may); la fija HR3 (humedad del suelo antes de la siembra).",
  jul_sep = paste("Ventana JUL-SEP: con siembra de mayo-junio, floracion a 45-72 dias de la siembra [V] y llenado de grano",
                  "caen aproximadamente en jul-sep; sin fecha de siembra por parcela esto es una suposicion [PV]."),
  ago = "Solo agosto: la fija HR14 (senescencia); solo observaciones validas de agosto 2025.",
  ciclo = "Ventana CICLO (abr-oct) porque el indice no tiene una ventana natural o mide acumulacion sobre todo el ciclo."
)
NOTA_INDICE <- c(
  crc   = "CRC: respuesta espectral ligada a cobertura de residuos de cultivo (diccionario del reto).",
  mcrc  = "MCRC: variante modificada de indices de residuos (diccionario del reto).",
  ndti  = "NDTI: indice de onda corta para suelo, residuos y labranza (diccionario del reto).",
  sti   = "STI: relacion simple para residuos y labranza; razon no acotada por arriba.",
  ndsvi = "NDSVI: sensible a vegetacion senescente y material no fotosintetico (diccionario del reto).",
  ndwi  = "NDWI: contraste de bandas relacionado con agua o humedad; ya evaluado en otra familia como media del ciclo, aqui solo la ventana A que exige HR3.",
  nddi  = "NDDI: integra vegetacion y humedad para caracterizar sequedad (diccionario del reto).",
  msi   = "MSI: sensible al contenido de agua de la vegetacion; razon positiva no acotada; ya evaluado en otra familia, aqui la ventana jul-sep que exige HR13.",
  emsi  = "EMSI: variante del indice de estres hidrico; razon positiva no acotada.",
  enddi = "ENDDI: variante del indice de sequedad con una senal hidrica adicional (diccionario del reto).",
  dswi2 = "DSWI2: familia Disease-Water Stress Index; razon positiva no acotada; exploratoria.",
  dswi3 = "DSWI3: familia Disease-Water Stress Index; razon positiva no acotada; exploratoria.",
  dswi4 = "DSWI4: familia Disease-Water Stress Index; razon positiva cerca de 1; exploratoria.",
  dswi5 = "DSWI5: familia Disease-Water Stress Index; razon positiva cerca de 1; exploratoria.",
  fapar = "FAPAR: fraccion de radiacion fotosinteticamente activa absorbida (diccionario del reto); no se recorta ni se transforma; no se usa LAI.",
  endwi = "ENDWI: variante de un indice normalizado de agua o humedad (diccionario del reto).",
  srndi = "SRNDI: contraste entre onda corta y rojo (diccionario del reto); significado agronomico [PV].",
  mra   = paste("MRA: abreviatura del proveedor, significado desconocido. Toma unos 22 valores distintos (0.020 a 0.041,",
                "3 decimales); su _std dentro de la parcela vale 0.000 en 61% de las observaciones (maximo 0.007): resolucion muy baja."),
  vi6t  = "VI6T: indice espectral-termico solo de Landsat (30 m optico, 100 m termico [V-parcial]); formula desconocida.",
  savi  = "SAVI (Sentinel-2): ya evaluado como media en otra familia; aqui solo su variabilidad dentro de la parcela.",
  ndvi  = "NDVI: ya evaluado como media en otra familia; aqui solo su variabilidad dentro de la parcela.",
  evi   = "EVI (Sentinel-2): ya evaluado como media en otra familia; aqui solo su variabilidad dentro de la parcela."
)
TXT_TIPO <- c(
  media = "Promedio de la media de parcela (_promedio)",
  std   = "Promedio de la desviacion estandar dentro de la parcela (_std)",
  cv    = "Promedio del coeficiente de variacion dentro de la parcela (_std / |_promedio|, solo con |_promedio| > 0.05)")

dic <- ESPEC %>%
  mutate(
    n_na_197 = vapply(variable, function(v) sum(is.na(feat[[v]])), integer(1)),
    pct_na_197 = round(100 * n_na_197 / 197, 2),
    rango = vapply(variable, function(v) {
      x <- feat[[v]]
      if (all(is.na(x))) return("sin datos")
      sprintf("Valores entre parcelas: min %.3f, mediana %.3f, max %.3f", min(x, na.rm = TRUE),
              median(x, na.rm = TRUE), max(x, na.rm = TRUE))
    }, character(1)),
    obs = vapply(variable, function(v) sprintf("obs. validas por parcela: mediana %d, minimo %d",
                                               as.integer(median(nobs[[v]])), min(nobs[[v]])), character(1))
  ) %>%
  left_join(ESC, by = c("indice", "sensor")) %>%
  mutate(
    definicion = sprintf("%s de %s, %s, en las observaciones de %s con nubosidad < 20 y valor no vacio; NA si no hay ninguna.",
                         TXT_TIPO[tipo], toupper(indice), TXT_SENS[sensor], TXT_VENT[ventana]),
    escala_txt = sprintf("Escala del indice en 2025 (obs. validas): min %.3f, mediana %.3f, max %.3f; %s; |media| <= 0.05 en %.1f%% de las obs.",
                         min, mediana, max, ifelse(min > 0, "solo valores positivos", "con valores negativos"), pct_abs_bajo),
    unidad = ifelse(tipo == "cv", "adimensional (cociente std/|media|)",
                    ifelse(indice %in% c("sti", "msi", "emsi", "dswi2", "dswi3", "dswi4", "dswi5"),
                           "razon adimensional (indice)", "indice adimensional")),
    notas = paste0(ifelse(primer_orden, "[Primer orden] ", "[Exploratoria o secundaria] "),
                   NOTA_INDICE[indice], " ", TXT_VENT_MOTIVO[ventana], " ", escala_txt, " ", rango, "; ", obs, ".",
                   ifelse(tipo != "media", " Ruidosa en parcelas menores de 1.44 ha (pocos pixeles).", ""))
  ) %>%
  transmute(variable, definicion, ventana = unname(TXT_VENT[ventana]), sensor, unidad,
            n_na_197, pct_na_197, hipotesis_id, notas)

# ---- 6. Hipotesis ---------------------------------------------------------------
V <- function(...) paste(c(...), collapse = ";")
hip <- tribble(
  ~id, ~existente, ~hipotesis, ~variables, ~signo, ~spec,
  "HR3", "si", "", V("sat_ndwi_s2_a", "sat_nddi_s2_a"), "ninguno", "lineal",
  "HR6", "si", "", V("sat_savi_cv_s2_jul_sep", "sat_ndvi_cv_planet_jul_sep"), "-", "lineal",
  "HR9", "si", "", V("sat_crc_s2_pre", "sat_mcrc_s2_pre", "sat_ndti_s2_pre", "sat_sti_s2_pre", "sat_ndsvi_s2_pre"), "ninguno", "lineal",
  "HR13", "si", "", V("sat_msi_s2_jul_sep", "sat_emsi_s2_jul_sep", "sat_nddi_s2_jul_sep", "sat_enddi_s2_jul_sep"), "-", "lineal",
  "HR14", "si", "", V("sat_ndsvi_s2_ago"), "-", "lineal",
  "HI1", "no",
  paste("Una mayor fraccion de radiacion fotosinteticamente activa absorbida (FAPAR de Sentinel-2, media de jul-sep y media del ciclo abr-oct) se asocia con mayor rendimiento dentro de region. Signo: +.",
        "Motivo: la biomasa de un cultivo crece con la radiacion que su follaje absorbe a lo largo del ciclo (idea del modelo de eficiencia de uso de radiacion [PV]); la media del ciclo aproxima esa absorcion acumulada y la de jul-sep la del periodo de espigado y llenado (floracion a 45-72 dias de la siembra [V]).",
        "Limite: el diccionario no da la formula y en 2025 la FAPAR de jul-sep tiene correlacion de rangos 0.98 con el SAVI de jul-sep [CP], por lo que casi no aporta informacion nueva frente a un indice de vegetacion (la media del ciclo es menos redundante, 0.79); un promedio de fechas con huecos por nubes no es una integral; sin fecha de siembra por parcela la ventana es una suposicion [PV]."),
  V("sat_fapar_s2_jul_sep", "sat_fapar_s2_ciclo"), "+", "lineal",
  "HI2", "no",
  paste("Un mayor valor del indice de agua ENDWI (Sentinel-2, jul-sep) se asocia con mayor rendimiento dentro de region. Signo: +.",
        "Motivo: es la contraparte de los indices de estres hidrico de HR13; una vegetacion con mas agua en la hoja durante espigado y llenado sufre menos estres.",
        "Limite: el diccionario solo dice que es una variante de un indice de agua o humedad y no da la formula; puede seguir sobre todo al verdor (mas cobertura, mas agua aparente) y no al agua disponible, y la nubosidad residual lo puede contaminar."),
  V("sat_endwi_s2_jul_sep"), "+", "lineal",
  "HI3", "no",
  paste("Exploratoria, sin signo declarado: SRNDI (Sentinel-2, jul-sep) y MRA (Sentinel-2, media del ciclo abr-oct).",
        "Motivo: el diccionario describe SRNDI como un contraste entre onda corta y rojo, cuya lectura agronomica es [PV], y no explica MRA (abreviatura del proveedor); se prueban solo para no dejar sin evaluar dos de los 17 indices.",
        "Limite: sin formula ni significado confirmados; MRA toma unos 22 valores distintos entre 0.020 y 0.041 y su desviacion dentro de la parcela vale 0.000 en 61% de las observaciones, asi que su resolucion es muy baja; alto riesgo de un hallazgo por azar."),
  V("sat_srndi_s2_jul_sep", "sat_mra_s2_ciclo"), "ninguno", "lineal",
  "HI4", "no",
  paste("Exploratoria, sin signo declarado: VI6T (Landsat, media de jul-sep), indice que combina una banda espectral con informacion termica de la superficie.",
        "Motivo: una superficie con mas estres o menos cobertura tiende a calentarse mas [PV], pero no conocemos como entra el termino termico en VI6T ni en que direccion, por eso no se fija signo; es el unico indice de un sensor distinto a Sentinel-2.",
        "Limite: la parte termica tiene 100 m de resolucion [V-parcial], o sea unos 5 pixeles termicos en una parcela mediana [CP]; alrededor de 36% de las filas Landsat vienen sin dato por nubes [V] y en jul-sep 5 parcelas tienen solo 1 o 2 observaciones validas [CP]; formula desconocida."),
  V("sat_vi6t_landsat_jul_sep"), "ninguno", "lineal",
  "HI5", "no",
  paste("Parte exploratoria de HR13, sin signo declarado: DSWI2, DSWI3, DSWI4 y DSWI5 (Sentinel-2, jul-sep).",
        "Motivo: son indices de la familia Disease-Water Stress Index, descritos como sensibles a estres hidrico y condicion de la vegetacion (posible sensibilidad a enfermedad, sin verificar); el signo depende de la combinacion de bandas de cada uno, que no conocemos.",
        "Limite: cuatro variables parecidas entre si aumentan el riesgo de un hallazgo por azar; son razones no acotadas con valores hasta cerca de 4."),
  V("sat_dswi2_s2_jul_sep", "sat_dswi3_s2_jul_sep", "sat_dswi4_s2_jul_sep", "sat_dswi5_s2_jul_sep"), "ninguno", "lineal",
  "HI6", "no",
  paste("Extension de HR6: un mayor coeficiente de variacion dentro de la parcela del NDVI y del EVI de Sentinel-2 (jul-sep) baja el rendimiento. Signo: -.",
        "Motivo: igual que en HR6, heterogeneidad de emergencia, suelo o plagas dentro del lote; NDVI y EVI se prueban ademas del SAVI porque responden distinto al suelo y al dosel denso.",
        "Limite: las tres columnas de CV de Sentinel-2 seran muy parecidas entre si; las parcelas menores de 1.44 ha tienen pocos pixeles y la desviacion es ruidosa; el CV se promedia solo sobre fechas con |media| mayor a 0.05."),
  V("sat_ndvi_cv_s2_jul_sep", "sat_evi_cv_s2_jul_sep"), "-", "lineal",
  "HI7", "no",
  paste("Exploratoria, sin signo declarado: desviacion estandar dentro de la parcela (en unidades del indice) de SAVI, NDVI y EVI de Sentinel-2 y de NDVI de Planet, promedio de jul-sep.",
        "Motivo: mide la dispersion espacial sin dividir por el nivel del indice, por lo que puede reflejar heterogeneidad (efecto negativo) o un dosel mas desarrollado, que tiene mas variacion en valor absoluto (efecto positivo); por eso no se fija signo.",
        "Limite: mezcla heterogeneidad con vigor; depende del numero de pixeles de la parcela; es ruidosa en parcelas menores de 1.44 ha."),
  V("sat_savi_std_s2_jul_sep", "sat_ndvi_std_s2_jul_sep", "sat_evi_std_s2_jul_sep", "sat_ndvi_std_planet_jul_sep"), "ninguno", "lineal",
  "HI8", "no",
  paste("Una mayor heterogeneidad interna de suelo y agua baja el rendimiento. Signo: -. Variables: desviacion dentro de la parcela de NDTI en feb-may (indice de labranza y residuo) y coeficiente de variacion de MSI en jul-sep (indice de contenido de agua de la vegetacion).",
        "Motivo: cobertura de residuo o labranza despareja antes de la siembra puede dar emergencia despareja, y un estres hidrico despareja dentro del lote refleja diferencias de suelo o de humedad; ambas son extensiones de la idea de HR6.",
        "Limite: la razon agronomica es mas debil que la de HR6; la desviacion de NDTI puede incluir franjas de labranza que no danan; formulas sin confirmar; ruidosas en parcelas pequenas."),
  V("sat_ndti_std_s2_pre", "sat_msi_cv_s2_jul_sep"), "-", "lineal"
)

# ---- 7. Chequeos internos y escritura --------------------------------------------
todas_hip <- unlist(strsplit(hip$variables, ";", fixed = TRUE))
stopifnot(!anyDuplicated(todas_hip), setequal(todas_hip, ESPEC$variable),
          all(ESPEC$hipotesis_id %in% hip$id), all(hip$id %in% ESPEC$hipotesis_id))
for (i in seq_len(nrow(hip))) {  # cada hipotesis lista justo las variables que la citan en el diccionario
  stopifnot(setequal(strsplit(hip$variables[i], ";", fixed = TRUE)[[1]],
                     ESPEC$variable[ESPEC$hipotesis_id == hip$id[i]]))
}
stopifnot(all(hip$signo %in% c("+", "-", "ninguno")),
          !any(grepl("[\"\r\n]", hip$hipotesis)),
          all(hip$hipotesis[hip$existente == "no"] != ""))
stopifnot(!any(vapply(feat[-1], function(x) length(unique(x[!is.na(x)])) <= 1, logical(1))))

write_csv(feat, file.path(SAL, "sat_indices17_features.csv"), na = "NA")
write_csv(dic,  file.path(SAL, "sat_indices17_diccionario.csv"), na = "NA")
write_csv(hip,  file.path(SAL, "sat_indices17_hipotesis.csv"), na = "NA")
cat("Escritos: sat_indices17_features.csv (", nrow(feat), "x", ncol(feat), "), diccionario (",
    nrow(dic), "), hipotesis (", nrow(hip), ", existentes:", sum(hip$existente == "si"),
    ", nuevas:", sum(hip$existente == "no"), ")\n\n")

# ---- 8. Informes para las notas (solo informar) ------------------------------------
cat("== NA por variable (n_na_197) y observaciones validas por parcela ==\n")
print(as.data.frame(dic %>% transmute(variable, n_na_197,
        n_obs_mediana = vapply(variable, function(v) as.integer(median(nobs[[v]])), integer(1)),
        n_obs_min = vapply(variable, function(v) min(nobs[[v]]), integer(1)))), row.names = FALSE)
cat("\nNA maximo:", max(dic$pct_na_197), "%\n\n")

cat("== Rango de cada variable entre parcelas ==\n")
print(as.data.frame(bind_rows(lapply(names(feat)[-1], function(v) {
  x <- feat[[v]]
  tibble(variable = v, min = min(x, na.rm = TRUE), p5 = unname(quantile(x, 0.05, na.rm = TRUE)),
         mediana = median(x, na.rm = TRUE), p95 = unname(quantile(x, 0.95, na.rm = TRUE)),
         max = max(x, na.rm = TRUE))
})) %>% mutate(across(where(is.numeric), ~ round(.x, 4)))), row.names = FALSE)

cat("\n== Redundancia: pares con |rho de Spearman| >= 0.85 entre variables construidas ==\n")
R <- cor(as.matrix(feat[-1]), method = "spearman", use = "pairwise.complete.obs")
idx <- which(upper.tri(R) & abs(R) >= 0.85, arr.ind = TRUE)
pr <- tibble(a = rownames(R)[idx[, 1]], b = colnames(R)[idx[, 2]], rho = round(R[idx], 3)) %>%
  arrange(desc(abs(rho)))
print(as.data.frame(pr), row.names = FALSE)
cat("Pares con |rho| >= 0.85:", nrow(pr), "de", choose(ncol(R), 2), "\n")

cat("\n== Referencia (no se exporta): correlacion de cada media jul-sep con SAVI, NDVI y EVI de S2 jul-sep ==\n")
ref <- tibble(ID_POLIGONO = IDS)
for (ix in c("savi", "ndvi", "evi")) {
  ref[[ix]] <- calc_var(FUENTE$s2, ix, "media", VENTANAS$jul_sep)$valor
}
vs <- ESPEC$variable[ESPEC$tipo == "media" & ESPEC$sensor == "s2" & ESPEC$ventana %in% c("jul_sep", "ciclo", "ago")]
print(as.data.frame(bind_rows(lapply(vs, function(v) tibble(variable = v,
  rho_savi = round(cor(feat[[v]], ref$savi, method = "spearman", use = "complete.obs"), 3),
  rho_ndvi = round(cor(feat[[v]], ref$ndvi, method = "spearman", use = "complete.obs"), 3),
  rho_evi  = round(cor(feat[[v]], ref$evi,  method = "spearman", use = "complete.obs"), 3))))),
  row.names = FALSE)

cat("\n== Parcelas pequenas (variabilidad dentro de la parcela con pocos pixeles) ==\n")
att <- read_csv(file.path(RAIZ, "01_datos/derivados/parcelas_atributos.csv"),
                show_col_types = FALSE, progress = FALSE)
att <- att[match(IDS, att$ID_POLIGONO), ]
stopifnot(!anyNA(att$area_calculada_ha))
cat("Parcelas con area_calculada_ha < 1.44:", sum(att$area_calculada_ha < 1.44),
    "| por CONJUNTO:", paste(names(table(att$CONJUNTO[att$area_calculada_ha < 1.44])),
                             table(att$CONJUNTO[att$area_calculada_ha < 1.44]), collapse = ", "), "\n")
cat("Con AREA_HA_SHP < 1.44:", sum(att$AREA_HA_SHP < 1.44, na.rm = TRUE),
    "| area_calculada_ha < 1:", sum(att$area_calculada_ha < 1),
    "| < 0.5:", sum(att$area_calculada_ha < 0.5), "\n")
cat("Area mediana (ha):", round(median(att$area_calculada_ha), 2),
    "| pixeles de 10 m en la mediana:", round(median(att$area_calculada_ha) / 0.01),
    "| en la parcela mas chica:", round(min(att$area_calculada_ha) / 0.01), "\n")
vv <- ESPEC$variable[ESPEC$tipo != "media"]
cat("Spearman de cada variable de variabilidad con log(area):\n")
print(data.frame(variable = vv, rho_log_area = round(vapply(vv, function(v)
  cor(feat[[v]], log(att$area_calculada_ha), method = "spearman", use = "complete.obs"), numeric(1)), 3)),
  row.names = FALSE)
cat("\nFin.\n")
