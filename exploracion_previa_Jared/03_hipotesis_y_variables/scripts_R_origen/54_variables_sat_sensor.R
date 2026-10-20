# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/54_variables_sat_sensor.R). Original: preparacion/scripts/54_variables_sat_sensor.R.
# ==============================================================================
# 54_variables_sat_sensor.R  --  Familia 4: variables satelitales separadas por sensor
# Reto AgroCebada FIRA 2026
#
# Que hace: para cada parcela, sensor y ventana calcula el PROMEDIO SIMPLE de la
# media-de-parcela del indice (columna *_promedio) entre las observaciones de esa
# ventana con porcentaje_nubosidad < 20 y valor no vacio. Si no hay ninguna, NA
# (no se imputa nada). Los sensores nunca se mezclan: sufijo _s2 o _planet.
#
# Ventanas (2025, fijas de la Semana 2): a = A abr-may, b = B jun-jul,
#   c = C ago-sep, oct = D oct, ciclo = CICLO abr-oct. Aqui se usan b, c y ciclo
#   (mismo sufijo que la familia clim_*).
# Variables:
#   Sentinel-2 (Basico): ndvi, evi, savi, msi, ndwi en b, c, ciclo (15);
#     lai en ciclo (1) con los valores negativos recortados a 0 ANTES de promediar,
#     y la bandera sat_lai_s2_ciclo_frac_neg (fraccion de observaciones validas con
#     LAI negativo).
#   Planet (PRO): ndvi, evi, lai, msavi en b, c, ciclo (12). Misma regla de LAI;
#     la bandera solo se crea si hay algun LAI negativo entre las observaciones usadas.
#   Multianuales de Sentinel-2 (HR1, HR2 y una nueva):
#     sat_savi_s2_tipico_2022_2024 = promedio de los SAVI de ciclo (abr-oct) de 2022, 2023 y 2024
#     sat_cv_interanual_ndvi_s2    = desv. estandar / promedio de los tres NDVI de ciclo
#     sat_savi_s2_dev_2025         = SAVI de ciclo 2025 menos el tipico 2022-2024
#   Si algun anio queda NA, la variable multianual queda NA (no se rellena).
# Landsat no se usa (solo trae VI6T y no se pidio).
# Este script NO lee rendimiento en ningun momento.
#
# Entradas: 01_datos/originales/Conjunto_datos_BASICO_AgroCebada2026.csv
#           01_datos/originales/Conjunto_datos_PRO_AgroCebada.csv
#           01_datos/preparados/base_197_ubicacion.csv (solo la lista de ID)
#           01_datos/derivados/basico_resumen_satelital_por_parcela.csv y
#           pro_resumen_satelital_por_parcela.csv (solo para comparar el orden de magnitud)
# Salidas : 03_hipotesis_y_variables/variables/sat_sensor_features.csv, sat_sensor_diccionario.csv,
#           sat_sensor_hipotesis.csv, sat_sensor_n_obs_resumen.csv
#           04_resultados/logs/54_variables_sat_sensor.log
# Como correr:  Rscript 03_hipotesis_y_variables/scripts/54_variables_sat_sensor.R
# No usa azar.
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
log_con <- file(file.path(PREP, "04_resultados/logs/54_variables_sat_sensor.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)

cat("== 54_variables_sat_sensor.R ==\n")
cat("R:", R.version.string, "| readr", as.character(packageVersion("readr")),
    "| dplyr", as.character(packageVersion("dplyr")),
    "| tidyr", as.character(packageVersion("tidyr")),
    "| tibble", as.character(packageVersion("tibble")), "\n\n")

UMBRAL_NUB <- 20
VENTANAS   <- list(b = 6:7, c = 8:9, ciclo = 4:10)
ANIOS_REF  <- 2022:2024
ANIO_EVAL  <- 2025

# ---- lista oficial de parcelas -------------------------------------------------
ub  <- read_csv(file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"), show_col_types = FALSE, progress = FALSE)
ids <- ub$ID_POLIGONO
stopifnot(length(ids) == 197, !anyDuplicated(ids))

# ---- lectura de los dos conjuntos ---------------------------------------------
DS <- file.path(RAIZ, "01_datos/originales")
preparar <- function(d) {
  d$fecha <- as.Date(d$fecha_captura, format = "%d/%m/%Y")
  stopifnot(!any(is.na(d$fecha)))
  d$anio <- as.integer(format(d$fecha, "%Y"))
  d$mes  <- as.integer(format(d$fecha, "%m"))
  d
}

cols_s2 <- c("ID_POLIGONO", "fecha_captura", "sensor", "ndvi_promedio", "evi_promedio",
             "savi_promedio", "msi_promedio", "ndwi_promedio", "lai_promedio", "porcentaje_nubosidad")
b <- read_csv(file.path(DS, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
              col_select = all_of(cols_s2), show_col_types = FALSE, progress = FALSE)
s2 <- preparar(b %>% filter(sensor == "Sentinel-2"))
cat("Sentinel-2: filas =", nrow(s2), "| parcelas =", n_distinct(s2$ID_POLIGONO),
    "| duplicados parcela-fecha =", sum(duplicated(s2[, c("ID_POLIGONO", "fecha")])), "\n")

pl <- preparar(read_csv(file.path(DS, "Conjunto_datos_PRO_AgroCebada.csv"),
                        col_select = c(ID_POLIGONO, fecha_captura, sensor, ndvi_promedio, evi_promedio,
                                       lai_promedio, msavi_promedio, porcentaje_nubosidad),
                        show_col_types = FALSE, progress = FALSE))
cat("Planet: filas =", nrow(pl), "| parcelas =", n_distinct(pl$ID_POLIGONO),
    "| duplicados parcela-fecha =", sum(duplicated(pl[, c("ID_POLIGONO", "fecha")])), "\n")
stopifnot(all(ids %in% s2$ID_POLIGONO), all(ids %in% pl$ID_POLIGONO))

# ---- observaciones validas: nubosidad < 20 (nubosidad NA no cuenta como valida) ----
valida <- function(d) {
  d <- d %>% filter(!is.na(porcentaje_nubosidad), porcentaje_nubosidad < UMBRAL_NUB)
  d$lai_neg <- d$lai_promedio < 0            # bandera (NA si no hay LAI)
  d$lai_promedio <- pmax(d$lai_promedio, 0)  # LAI negativo se recorta a 0 antes de promediar
  d
}
s2v <- valida(s2)
plv <- valida(pl)
cat("Observaciones validas: S2 =", nrow(s2v), "de", nrow(s2), "| Planet =", nrow(plv), "de", nrow(pl), "\n")
cat("S2: filas validas con algun indice vacio =",
    sum(!complete.cases(s2v[, c("ndvi_promedio", "evi_promedio", "savi_promedio", "msi_promedio",
                                "ndwi_promedio", "lai_promedio")])), "\n")
cat("LAI negativo (antes de recortar), observaciones validas: S2 =", sum(s2v$lai_neg, na.rm = TRUE),
    "de", sum(!is.na(s2v$lai_neg)), "| Planet =", sum(plv$lai_neg, na.rm = TRUE),
    "de", sum(!is.na(plv$lai_neg)), "\n\n")

# ---- funciones -----------------------------------------------------------------
promedio_ventana <- function(d, indices, anio_sel, meses) {
  cols <- paste0(indices, "_promedio")
  d %>%
    filter(anio == anio_sel, mes %in% meses) %>%
    group_by(ID_POLIGONO) %>%
    summarise(across(all_of(cols), ~ if (all(is.na(.x))) NA_real_ else mean(.x, na.rm = TRUE)),
              .groups = "drop") %>%
    right_join(tibble(ID_POLIGONO = ids), by = "ID_POLIGONO") %>%
    arrange(match(ID_POLIGONO, ids))
}

n_validas <- function(d, anio_sel, meses, col_ref) {
  d %>%
    filter(anio == anio_sel, mes %in% meses, !is.na(.data[[col_ref]])) %>%
    count(ID_POLIGONO, name = "n") %>%
    right_join(tibble(ID_POLIGONO = ids), by = "ID_POLIGONO") %>%
    mutate(n = coalesce(n, 0L)) %>%
    arrange(match(ID_POLIGONO, ids))
}

frac_neg <- function(d, anio_sel, meses) {
  d %>%
    filter(anio == anio_sel, mes %in% meses, !is.na(lai_neg)) %>%
    group_by(ID_POLIGONO) %>%
    summarise(f = mean(lai_neg), .groups = "drop") %>%
    right_join(tibble(ID_POLIGONO = ids), by = "ID_POLIGONO") %>%
    arrange(match(ID_POLIGONO, ids)) %>%
    pull(f)
}

armar <- function(d, indices, sufijo) {
  out <- tibble(ID_POLIGONO = ids)
  for (idx in indices) {
    for (v in names(VENTANAS)) {
      r <- promedio_ventana(d, idx, ANIO_EVAL, VENTANAS[[v]])
      out[[paste0("sat_", idx, "_", sufijo, "_", v)]] <- r[[paste0(idx, "_promedio")]]
    }
  }
  out
}

# ---- (a) Sentinel-2 ------------------------------------------------------------
f_s2 <- armar(s2v, c("ndvi", "evi", "savi", "msi", "ndwi"), "s2")
lai_s2 <- promedio_ventana(s2v, "lai", ANIO_EVAL, VENTANAS$ciclo)
f_s2$sat_lai_s2_ciclo          <- lai_s2$lai_promedio
f_s2$sat_lai_s2_ciclo_frac_neg <- frac_neg(s2v, ANIO_EVAL, VENTANAS$ciclo)

# ---- (b) Planet ----------------------------------------------------------------
f_pl <- armar(plv, c("ndvi", "evi", "lai", "msavi"), "planet")
fn_pl <- frac_neg(plv, ANIO_EVAL, VENTANAS$ciclo)
HAY_NEG_PLANET <- any(fn_pl > 0, na.rm = TRUE)
cat("Planet: algun LAI negativo entre las observaciones usadas (ciclo 2025)?", HAY_NEG_PLANET, "\n")
if (HAY_NEG_PLANET) f_pl$sat_lai_planet_ciclo_frac_neg <- fn_pl

# ---- (d) multianuales de Sentinel-2 --------------------------------------------
ref <- tibble(ID_POLIGONO = ids)
for (a in ANIOS_REF) {
  r <- promedio_ventana(s2v, c("savi", "ndvi"), a, VENTANAS$ciclo)
  ref[[paste0("savi_", a)]] <- r$savi_promedio
  ref[[paste0("ndvi_", a)]] <- r$ndvi_promedio
}
M_savi <- as.matrix(ref[, paste0("savi_", ANIOS_REF)])
M_ndvi <- as.matrix(ref[, paste0("ndvi_", ANIOS_REF)])
cat("Parcelas con SAVI de ciclo NA por anio:",
    paste(ANIOS_REF, colSums(is.na(M_savi)), sep = " = ", collapse = " | "), "\n")
cat("Parcelas con NDVI de ciclo NA por anio:",
    paste(ANIOS_REF, colSums(is.na(M_ndvi)), sep = " = ", collapse = " | "), "\n")
cat("Parcelas con algun anio NA (tipico y CV quedan NA): SAVI =", sum(rowSums(is.na(M_savi)) > 0),
    "| NDVI =", sum(rowSums(is.na(M_ndvi)) > 0), "\n")

tipico <- rowMeans(M_savi)                       # NA si falta algun anio
m_ndvi <- rowMeans(M_ndvi)
s_ndvi <- apply(M_ndvi, 1, sd)                   # desviacion estandar muestral (n - 1)
cat("Parcelas con promedio de NDVI <= 0 (CV no definido):", sum(m_ndvi <= 0, na.rm = TRUE), "\n\n")
f_multi <- tibble(
  ID_POLIGONO = ids,
  sat_savi_s2_tipico_2022_2024 = tipico,
  sat_cv_interanual_ndvi_s2    = ifelse(!is.na(m_ndvi) & m_ndvi > 0, s_ndvi / m_ndvi, NA_real_),
  sat_savi_s2_dev_2025         = f_s2$sat_savi_s2_ciclo - tipico
)

# ---- tabla final de variables ----------------------------------------------------
feat <- f_s2 %>% left_join(f_pl, by = "ID_POLIGONO") %>% left_join(f_multi, by = "ID_POLIGONO")
stopifnot(identical(feat$ID_POLIGONO, ids))
cat("Variables construidas:", ncol(feat) - 1, "(tope 45)\n\n")

# ---- (e) numero de observaciones validas por parcela y ventana -----------------
res_n <- function(sensor, d, col_ref, anio_sel, v) {
  n <- n_validas(d, anio_sel, if (v == "ciclo") VENTANAS$ciclo else VENTANAS[[v]], col_ref)$n
  tibble(sensor = sensor, anio = anio_sel, ventana = v, mediana = median(n), minimo = min(n),
         maximo = max(n), parcelas_con_cero = sum(n == 0))
}
tab_n <- bind_rows(
  lapply(names(VENTANAS), function(v) res_n("s2", s2v, "ndvi_promedio", ANIO_EVAL, v)),
  lapply(ANIOS_REF, function(a) res_n("s2", s2v, "ndvi_promedio", a, "ciclo")),
  lapply(names(VENTANAS), function(v) res_n("planet", plv, "ndvi_promedio", ANIO_EVAL, v))
)
cat("Observaciones validas por parcela (nubosidad < 20 y NDVI no vacio):\n")
print(as.data.frame(tab_n), row.names = FALSE)
cat("\n")
write_csv(tab_n, file.path(SAL, "sat_sensor_n_obs_resumen.csv"), na = "")

# ---- hipotesis -------------------------------------------------------------------
V <- function(idx, suf) paste0("sat_", idx, "_", suf, "_", c("b", "c", "ciclo"))
com_ventanas <- paste0(" Ventana principal declarada antes de probar: abr-oct (CICLO), porque promedia mas fechas",
                       " despejadas y es la menos ruidosa (en 2025 la mediana es 32 fechas por parcela en Sentinel-2 y 82 en",
                       " Planet, contra 8 a 22 en jun-jul y ago-sep [CP]); jun-jul (B) y ago-sep (C) son secundarias y no",
                       " cuentan como confirmacion aparte.")
com_nubes <- " Los huecos por nube se dejan vacios, no se imputan."

hip_nueva <- tribble(
  ~id, ~variables, ~signo, ~hipotesis,
  "HP1", paste(V("savi", "s2"), collapse = ";"), "+",
  paste0("El vigor medido con el SAVI de Sentinel-2 (promedio de las fechas con nubosidad menor a 20% de 2025) se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: el SAVI resume verdor y cobertura reduciendo el efecto del brillo del suelo [V] (USGS), y en nuestros datos hay mucho suelo visible (mediana del NDVI de Sentinel-2 0.175 [CP]); ",
         "en el EDA fue el mejor indice individual del Basico (correlacion global 0.317 [V]) pero sin controlar por region.",
         com_ventanas,
         " Limite: la fecha de siembra es desconocida [PV], el promedio simple mezcla etapas, las parcelas chicas tienen pocos pixeles de 10 m (17 miden menos de 1.44 ha [CP]).", com_nubes),
  "HP2", paste(V("ndvi", "s2"), collapse = ";"), "+",
  paste0("El vigor medido con el NDVI de Sentinel-2 se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: el NDVI mide verdor y actividad de la vegetacion [V] (USGS); la saturacion con dosel denso pesa poco aqui (solo 0.04% de las lecturas del Basico pasan de 0.8 [CP]).",
         com_ventanas,
         " Limite: no corrige el suelo, asi que con poca cobertura mezcla vegetacion y suelo; se espera muy parecido al SAVI (misma informacion base), por eso se prueba por separado y no junto.", com_nubes),
  "HP3", paste(V("evi", "s2"), collapse = ";"), "+",
  paste0("El vigor medido con el EVI de Sentinel-2 se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: el EVI usa la banda azul para corregir parcialmente suelo y atmosfera y se satura menos que el NDVI [V-parcial] (USGS; Huete et al., 2011).",
         com_ventanas,
         " Limite: se espera fuertemente relacionado con SAVI y NDVI [PV]; no se asume formula distinta de la del proveedor.", com_nubes),
  "HP4", paste(V("msi", "s2"), collapse = ";"), "-",
  paste0("Un MSI alto de Sentinel-2 (indice de estres hidrico de la vegetacion segun el diccionario del reto [V]) baja el rendimiento dentro de region. Signo: -. ",
         "Motivo: mas estres de agua en la hoja durante macollaje, espigado o llenado. Complementa a HR13 con un promedio simple por ventana.",
         com_ventanas,
         " Limite: el diccionario no da la formula y que un valor mayor signifique mas estres es [PV]; se confunde con senescencia natural y con el suelo desnudo.", com_nubes),
  "HP5", paste(V("ndwi", "s2"), collapse = ";"), "ninguno",
  paste0("Exploratoria, sin signo fijo declarado desde ahora: el NDWI de Sentinel-2 se reporta pero no cuenta como confirmado ni refutado. ",
         "Motivo: el diccionario lo describe como indice de agua o humedad sin dar la formula, y existen definiciones publicadas con sentidos opuestos (agua libre contra agua en la hoja) [PV].",
         com_ventanas,
         " Limite: sin formula no se puede interpretar el signo agronomicamente; si aparece asociacion, se reporta como hallazgo a explicar.", com_nubes),
  "HP6", "sat_lai_s2_ciclo;sat_lai_s2_ciclo_frac_neg", "ninguno",
  paste0("Control de redundancia, sin signo esperado. El LAI de Sentinel-2 del Basico es casi el SAVI reescalado (correlacion de rangos 0.9999 [CP]) y 42.2% de sus lecturas son negativas [V]; ",
         "se recorta a 0 ANTES de promediar y la fraccion de observaciones validas con LAI negativo se conserva como variable aparte (sat_lai_s2_ciclo_frac_neg: mide cuanto del ciclo la parcela se vio casi sin cobertura). ",
         "Se espera que el LAI no aporte nada sobre SAVI; si mejora a B2 pero no aporta sobre SAVI, se descarta por redundante y no se prueba junto con SAVI. ",
         "Limite: recortar a 0 borra las diferencias entre suelos desnudos (por eso la fraccion), un LAI negativo no es area foliar negativa sino la extrapolacion de la formula [CP].", com_nubes),
  "HP7", paste(V("ndvi", "planet"), collapse = ";"), "+",
  paste0("El vigor medido con el NDVI de Planet (3 m, casi diario en 2025) se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: mismo argumento que el NDVI de Sentinel-2, con muchas mas fechas por parcela (mediana de 243 lecturas en 2025 antes de filtrar nubes [V]) y mas detalle dentro de la parcela.",
         com_ventanas,
         " Limite: el NDVI de Planet es 45.6% mayor que el de Sentinel-2 [V], por eso los sensores no se mezclan ni se convierten; solo existe 2025; en el EDA el mejor indice de PRO (EVI) tuvo correlacion global 0.200, menor que el del Basico [V], sin controlar por region.", com_nubes),
  "HP8", paste(V("evi", "planet"), collapse = ";"), "+",
  paste0("El vigor medido con el EVI de Planet se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: EVI con correccion parcial de suelo y atmosfera [V-parcial] (USGS; Huete et al., 2011); fue el indice de PRO con mayor correlacion global en el EDA (0.200 [V]).",
         com_ventanas,
         " Limite: se espera muy relacionado con el NDVI de Planet [PV]; la correlacion global no controla por region.", com_nubes),
  "HP9", paste(V("msavi", "planet"), collapse = ";"), "+",
  paste0("El vigor medido con el MSAVI de Planet se asocia con mayor rendimiento dentro de region. Signo: +. ",
         "Motivo: el MSAVI ajusta la influencia del suelo de forma automatica [V] (USGS) y en el Basico no existe, asi que solo Planet lo aporta.",
         com_ventanas,
         " Limite: se espera muy relacionado con el NDVI y el EVI de Planet [PV]; no se compara de manera directa con el SAVI de Sentinel-2 porque son sensores distintos.", com_nubes),
  "HP10", paste(c(V("lai", "planet"), if (HAY_NEG_PLANET) "sat_lai_planet_ciclo_frac_neg"), collapse = ";"), "ninguno",
  paste0("Control de redundancia, sin signo esperado. El LAI de Planet es casi una funcion del NDVI de Planet (correlacion de rangos 0.98 [CP]) y su escala es unas 9 veces la del Basico [V], por eso nunca se mezcla con el LAI de Sentinel-2. ",
         "Regla de negativos: se recorta a 0 antes de promediar y se anade bandera solo si hay negativos entre las observaciones usadas (en PRO solo 1 de 35,747 lecturas es negativa [V]).",
         com_ventanas,
         " Limite: si mejora a B2 pero no aporta sobre el NDVI de Planet, se descarta por redundante.", com_nubes),
  "HP11", "sat_savi_s2_dev_2025", "+",
  paste0("Que en 2025 la parcela tenga mas vigor que el suyo normal se asocia con mayor rendimiento. Variable: SAVI de Sentinel-2 del ciclo abr-oct de 2025 menos el vigor tipico 2022-2024 de la misma parcela (mismas reglas de ventana y de nubosidad) [CP]. Signo: +. ",
         "Motivo: la parcela rindio por encima de su nivel habitual cuando su vigor de 2025 estuvo por encima del habitual; la resta quita lo estable de la parcela (suelo, manejo) y deja lo propio del anio de evaluacion. ",
         "Limite: solo 3 anios de referencia; es la resta de dos promedios simples de fechas despejadas distintas, con ruido propio; hereda NA de cualquiera de los cuatro anios; y si HR1 se confirma, esta variable es su complemento y no una idea independiente.")
)
hip_nueva$existente <- "no"
hip_nueva$spec <- "lineal"

hip_exist <- tibble(
  id = c("HR1", "HR2"), existente = "si", hipotesis = "",
  variables = c("sat_savi_s2_tipico_2022_2024", "sat_cv_interanual_ndvi_s2"),
  signo = c("+", "-"), spec = "lineal"
)
hip_nueva <- hip_nueva %>% mutate(hipotesis = gsub("[\r\n\"]", " ", hipotesis))
hip <- bind_rows(hip_exist, hip_nueva %>% select(id, existente, hipotesis, variables, signo, spec))
stopifnot(!any(grepl("[^\\x01-\\x7F]", hip$hipotesis, perl = TRUE)))

# ---- diccionario -----------------------------------------------------------------
VENT_TXT <- c(b = "B (jun-jul)", c = "C (ago-sep)", ciclo = "CICLO (abr-oct)")
NOMBRE_IDX <- c(ndvi = "NDVI", evi = "EVI", savi = "SAVI", msi = "MSI", ndwi = "NDWI", lai = "LAI", msavi = "MSAVI")
SENSOR_TXT <- c(s2 = "Sentinel-2 (Basico)", planet = "Planet (PRO)")
NOTA_IDX <- c(
  ndvi = "Sin correccion de suelo.",
  evi = "Formula no asumida; se usa el valor entregado por el proveedor.",
  savi = "Formula no asumida; se usa el valor entregado por el proveedor.",
  msi = "Sentido (mayor = mas estres) por verificar [PV]; formula no dada en el diccionario.",
  ndwi = "Exploratoria: formula no dada en el diccionario, signo desconocido.",
  msavi = "Solo existe en Planet.",
  lai = "LAI: negativos recortados a 0 antes de promediar."
)
HIP_IDX <- c(savi_s2 = "HP1", ndvi_s2 = "HP2", evi_s2 = "HP3", msi_s2 = "HP4", ndwi_s2 = "HP5",
             lai_s2 = "HP6", ndvi_planet = "HP7", evi_planet = "HP8", msavi_planet = "HP9", lai_planet = "HP10")

filas <- list()
for (col in setdiff(names(feat), "ID_POLIGONO")) {
  m <- regmatches(col, regexec("^sat_(ndvi|evi|savi|msi|ndwi|lai|msavi)_(s2|planet)_(b|c|ciclo)$", col))[[1]]
  if (length(m) == 4) {
    idx <- m[2]; suf <- m[3]; v <- m[4]
    filas[[col]] <- tibble(
      variable = col,
      definicion = paste0("Promedio simple de ", NOMBRE_IDX[[idx]], "_promedio (media de la parcela) de ", SENSOR_TXT[[suf]],
                          " entre las observaciones de 2025 en la ventana ", VENT_TXT[[v]],
                          " con porcentaje_nubosidad < 20 y valor no vacio; NA si no hay ninguna"),
      ventana = paste0(v, " = ", VENT_TXT[[v]], " 2025"), sensor = suf,
      unidad = if (idx == "lai") "m2 de hoja por m2 de terreno (recortado a >= 0)" else "indice sin unidad",
      hipotesis_id = HIP_IDX[[paste0(idx, "_", suf)]],
      notas = paste0(NOTA_IDX[[idx]], if (v == "ciclo") " Ventana principal declarada." else " Ventana secundaria.")
    )
  }
}
extras <- tribble(
  ~variable, ~definicion, ~ventana, ~sensor, ~unidad, ~hipotesis_id, ~notas,
  "sat_lai_s2_ciclo_frac_neg",
  "Fraccion de las observaciones validas de Sentinel-2 (nubosidad < 20 y LAI no vacio) del ciclo 2025 cuyo LAI de la parcela era negativo antes de recortar",
  "ciclo = CICLO (abr-oct) 2025", "s2", "fraccion entre 0 y 1", "HP6",
  "Bandera que acompana al recorte a 0 del LAI. Casi equivale a la fraccion de fechas con SAVI menor a 0.1 (suelo casi desnudo) [CP].",
  "sat_savi_s2_tipico_2022_2024",
  "Promedio de los SAVI de ciclo (abr-oct) de Sentinel-2 de 2022, 2023 y 2024; cada anio con la misma regla de ventana y nubosidad (< 20); NA si falta cualquiera de los tres anios",
  "ciclo = CICLO (abr-oct) de 2022, 2023 y 2024", "s2", "indice sin unidad", "HR1",
  "Vigor tipico multianual. Nombre registrado en HR1: savi_s2_tipico_2022_2024.",
  "sat_cv_interanual_ndvi_s2",
  "Desviacion estandar muestral (n - 1) de los tres NDVI de ciclo (abr-oct) de Sentinel-2 de 2022, 2023 y 2024 dividida entre su promedio (coeficiente de variacion); NA si falta cualquiera de los tres anios [CP]",
  "ciclo = CICLO (abr-oct) de 2022, 2023 y 2024", "s2", "adimensional (proporcion)", "HR2",
  "Nombre registrado en HR2: cv_interanual_ndvi. Con 3 datos por parcela el CV es ruidoso.",
  "sat_savi_s2_dev_2025",
  "SAVI de ciclo 2025 de Sentinel-2 (sat_savi_s2_ciclo) menos el tipico 2022-2024 (sat_savi_s2_tipico_2022_2024) [CP]",
  "ciclo = CICLO (abr-oct) 2025 menos promedio 2022-2024", "s2", "indice sin unidad (diferencia)", "HP11",
  "NA si falta cualquiera de los cuatro anios. Positivo = 2025 con mas vigor que el habitual."
)
if (HAY_NEG_PLANET) {
  extras <- bind_rows(extras, tibble(
    variable = "sat_lai_planet_ciclo_frac_neg",
    definicion = "Fraccion de las observaciones validas de Planet (nubosidad < 20 y LAI no vacio) del ciclo 2025 con LAI negativo antes de recortar",
    ventana = "ciclo = CICLO (abr-oct) 2025", sensor = "planet", unidad = "fraccion entre 0 y 1",
    hipotesis_id = "HP10", notas = "Bandera del recorte a 0 del LAI de Planet; solo se crea porque hay negativos."))
}
dic <- bind_rows(filas) %>% bind_rows(extras)
dic$n_na_197  <- vapply(dic$variable, function(v) sum(is.na(feat[[v]])), integer(1))
dic$pct_na_197 <- round(100 * dic$n_na_197 / 197, 1)
dic <- dic %>% select(variable, definicion, ventana, sensor, unidad, n_na_197, pct_na_197, hipotesis_id, notas)
stopifnot(setequal(dic$variable, setdiff(names(feat), "ID_POLIGONO")), !anyDuplicated(dic$variable))
dic <- dic[match(setdiff(names(feat), "ID_POLIGONO"), dic$variable), ]
# toda variable debe estar en alguna hipotesis, y toda variable de hipotesis debe existir
vars_hip <- unlist(strsplit(hip$variables, ";"))
stopifnot(setequal(vars_hip, dic$variable), all(dic$hipotesis_id %in% hip$id))

# ---- pruebas de calidad ----------------------------------------------------------
cat("== Pruebas ==\n")
stopifnot(nrow(feat) == 197, identical(sort(feat$ID_POLIGONO), sort(ids)), !anyDuplicated(feat$ID_POLIGONO))
cat("(i) 197 filas, mismos ID que base_197_ubicacion, sin duplicados: OK\n")
constantes <- names(feat)[-1][vapply(feat[-1], function(x) length(unique(x[!is.na(x)])) <= 1, logical(1))]
cat("(ii) columnas constantes:", if (length(constantes)) paste(constantes, collapse = ", ") else "ninguna", "\n")
stopifnot(length(constantes) == 0)
rango <- feat %>% pivot_longer(-ID_POLIGONO, names_to = "variable", values_to = "x") %>%
  group_by(variable) %>%
  summarise(min = min(x, na.rm = TRUE), mediana = median(x, na.rm = TRUE), max = max(x, na.rm = TRUE),
            n_na = sum(is.na(x)), .groups = "drop") %>%
  arrange(match(variable, names(feat)[-1]))
cat("(iii) rangos:\n"); print(as.data.frame(rango), row.names = FALSE, digits = 4)
en_rango <- function(p, lo, hi) {
  v <- rango$variable[grepl(p, rango$variable)]
  all(rango$min[rango$variable %in% v] >= lo & rango$max[rango$variable %in% v] <= hi)
}
stopifnot(en_rango("^sat_(ndvi|evi|savi|msavi|ndwi)_", -1, 1), en_rango("^sat_msi_", 0, 5),
          en_rango("^sat_lai_.*_(b|c|ciclo)$", 0, 10), en_rango("frac_neg$", 0, 1),
          en_rango("^sat_cv_", 0, 5), en_rango("^sat_savi_s2_tipico", -1, 1), en_rango("_dev_2025$", -1, 1))
cat("(iii) rangos plausibles: OK\n\n")

# ---- comparacion de orden de magnitud con los resumenes sin filtro ---------------
ob <- read_csv(file.path(RAIZ, "01_datos/derivados/basico_resumen_satelital_por_parcela.csv"), show_col_types = FALSE, progress = FALSE)
op <- read_csv(file.path(RAIZ, "01_datos/derivados/pro_resumen_satelital_por_parcela.csv"), show_col_types = FALSE, progress = FALSE)
comp <- function(sensor, ob_tab, idxs) {
  bind_rows(lapply(idxs, function(i) {
    x <- feat[[paste0("sat_", i, "_", sensor, "_ciclo")]]
    y <- ob_tab[[paste0(i, "_promedio")]][match(feat$ID_POLIGONO, ob_tab$ID_POLIGONO)]
    tibble(sensor = sensor, indice = i, mediana_mia = median(x, na.rm = TRUE), mediana_resumen_sin_filtro = median(y, na.rm = TRUE),
           corr_entre_parcelas = cor(x, y, use = "complete.obs"))
  }))
}
cat("Comparacion del ciclo 2025 (filtrado) con el resumen por parcela sin filtro de fecha ni nubosidad (solo orden de magnitud):\n")
print(as.data.frame(bind_rows(comp("s2", ob, c("ndvi", "evi", "savi", "msi", "ndwi", "lai")),
                              comp("planet", op, c("ndvi", "evi", "lai", "msavi")))), row.names = FALSE, digits = 3)
cat("\n")

# ---- escritura -------------------------------------------------------------------
write_csv(feat, file.path(SAL, "sat_sensor_features.csv"), na = "")
write_csv(dic,  file.path(SAL, "sat_sensor_diccionario.csv"), na = "")
write_csv(hip,  file.path(SAL, "sat_sensor_hipotesis.csv"), na = "")
cat("Escritos: sat_sensor_features.csv (", nrow(feat), "x", ncol(feat), "), sat_sensor_diccionario.csv (", nrow(dic),
    " filas), sat_sensor_hipotesis.csv (", nrow(hip), " filas: ", sum(hip$existente == "si"), " existentes y ",
    sum(hip$existente == "no"), " nuevas)\n", sep = "")
cat("Tasa de NA mas alta:", dic$variable[which.max(dic$pct_na_197)], "=", max(dic$pct_na_197), "%\n")
cat("== fin ==\n")
sink()
close(log_con)
