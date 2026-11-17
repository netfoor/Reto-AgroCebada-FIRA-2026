# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/53_variables_sat_compuestos.R). Original: preparacion/scripts/53_variables_sat_compuestos.R.
# ==============================================================================
# 53_variables_sat_compuestos.R  --  Familia 3: compuestos satelitales sin nubes
# Reto AgroCebada FIRA 2026
#
# Proposito: construir, con el mismo codigo para las 197 parcelas, compuestos
#   mensuales sin nubes (abril a octubre de 2025) y algunos resumenes por ventana.
#   NO usa el rendimiento y NO evalua nada: solo define variables candidatas.
#
# Definicion de compuesto (fija): para cada parcela, mes y sensor, MEDIANA del
#   promedio de parcela del indice (columna _promedio) entre las observaciones del
#   mes con porcentaje_nubosidad < 20 y valor no vacio. Sin observacion valida en el
#   mes: NA (no se interpola ni se imputa). Los sensores no se mezclan.
#   Sentinel-2 (_s2): ndvi, savi. Planet (_planet): ndvi, msavi. Landsat no entra.
#
# Variables (40 en total):
#   28 compuestos mensuales  satc_<indice>_<sensor>_m04 ... m10
#    4 max. del ciclo (NDVI)  satc_ndvi_max_ciclo_s2 / _planet  (2 columnas)
#    8 promedios por ventana  satc_<indice>_<sensor>_b_prom (jun-jul) y _c_prom (ago-sep)
#    2 calidad (observaciones sin nubes abril-octubre)  satc_nobs_s2_ciclo, satc_nobs_planet_ciclo
#   (satc_meses_validos_* se calculan, pero si resultan constantes se excluyen de las
#    variables; ver el log y las notas.)
#
# Entradas (solo lectura):
#   01_datos/originales/Conjunto_datos_BASICO_AgroCebada2026.csv
#   01_datos/originales/Conjunto_datos_PRO_AgroCebada.csv
#   01_datos/derivados/basico_metadatos_observaciones.csv  (solo para revisar fechas)
#   01_datos/preparados/base_197_ubicacion.csv  (lista oficial de las 197 parcelas)
# Salidas (todas en 03_hipotesis_y_variables/variables/):
#   sat_compuestos_features.csv, sat_compuestos_diccionario.csv,
#   sat_compuestos_hipotesis.csv, sat_compuestos_calidad_mes.csv,
#   sat_compuestos_sensibilidad_umbral10.csv
#   log: 04_resultados/logs/53_variables_sat_compuestos.log
# Como correr:  Rscript 03_hipotesis_y_variables/scripts/53_variables_sat_compuestos.R
# Este script no usa azar.
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
VARS <- file.path(PREP, "03_hipotesis_y_variables/variables")
DATA <- file.path(RAIZ, "01_datos/originales")
dir.create(VARS, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/53_variables_sat_compuestos.log"),
                open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 53_variables_sat_compuestos.R ==\n")
cat("R:", R.version.string, "| readr", as.character(packageVersion("readr")),
    "| dplyr", as.character(packageVersion("dplyr")),
    "| tidyr", as.character(packageVersion("tidyr")),
    "| tibble", as.character(packageVersion("tibble")), "\n")
cat("Sin azar en este script.\n\n")

UMBRAL      <- 20   # umbral principal de nubosidad (%), fijo del proyecto
UMBRAL_SENS <- 10   # solo para el chequeo de sensibilidad
ANIO        <- 2025
MESES       <- 4:10
MES_NOM     <- c("abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre")
names(MES_NOM) <- sprintf("m%02d", MESES)

# ---- 1. Lista oficial de parcelas ---------------------------------------------
ubic <- read_csv(file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"),
                 col_select = c(ID_POLIGONO), show_col_types = FALSE, progress = FALSE)
IDS <- ubic$ID_POLIGONO
stopifnot(length(IDS) == 197, !anyDuplicated(IDS))

# ---- 2. Lectura de los datos satelitales --------------------------------------
basico <- read_csv(
  file.path(DATA, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
  col_select = c(ID_POLIGONO, fecha_captura, sensor, ndvi_promedio, savi_promedio,
                 porcentaje_nubosidad),
  col_types = cols(ID_POLIGONO = "c", fecha_captura = "c", sensor = "c",
                   ndvi_promedio = "d", savi_promedio = "d", porcentaje_nubosidad = "d"),
  progress = FALSE)
pro <- read_csv(
  file.path(DATA, "Conjunto_datos_PRO_AgroCebada.csv"),
  col_select = c(ID_POLIGONO, fecha_captura, sensor, ndvi_promedio, msavi_promedio,
                 porcentaje_nubosidad),
  col_types = cols(ID_POLIGONO = "c", fecha_captura = "c", sensor = "c",
                   ndvi_promedio = "d", msavi_promedio = "d", porcentaje_nubosidad = "d"),
  progress = FALSE)
meta <- read_csv(file.path(RAIZ, "01_datos/derivados/basico_metadatos_observaciones.csv"),
                 col_types = cols(ID_POLIGONO = "c", fecha_captura = "c", sensor = "c",
                                  porcentaje_nubosidad = "d"), progress = FALSE)
cat("Filas Basico:", nrow(basico), "| filas PRO:", nrow(pro), "\n")

# ---- 3. Revision de fechas y de sensor ----------------------------------------
# Las fechas vienen como dd/mm/aaaa; se comparan contra el archivo de metadatos (ISO).
basico$fecha <- as.Date(basico$fecha_captura, format = "%d/%m/%Y")
pro$fecha    <- as.Date(pro$fecha_captura,    format = "%d/%m/%Y")
stopifnot(!anyNA(basico$fecha), !anyNA(pro$fecha), nrow(meta) == nrow(basico))
stopifnot(identical(basico$ID_POLIGONO, meta$ID_POLIGONO),
          identical(basico$sensor, meta$sensor),
          all(basico$fecha == as.Date(meta$fecha_captura)))
dif_nub <- abs(basico$porcentaje_nubosidad - meta$porcentaje_nubosidad)
stopifnot(all(is.na(basico$porcentaje_nubosidad) == is.na(meta$porcentaje_nubosidad)),
          max(dif_nub, na.rm = TRUE) < 1e-9)
cat("Fechas dd/mm/aaaa coinciden con las fechas ISO de basico_metadatos_observaciones.csv en",
    nrow(basico), "filas; nubosidad coincide (dif. maxima", format(max(dif_nub, na.rm = TRUE)), ").\n")
cat("Valores de sensor en Basico:", paste(sort(unique(basico$sensor)), collapse = " | "),
    "| en PRO:", paste(sort(unique(pro$sensor)), collapse = " | "), "\n")
stopifnot(setequal(unique(basico$sensor), c("Sentinel-2", "Landsat")),
          identical(unique(pro$sensor), "Planet"))
stopifnot(all(basico$ID_POLIGONO %in% IDS), all(pro$ID_POLIGONO %in% IDS),
          setequal(unique(basico$ID_POLIGONO), IDS), setequal(unique(pro$ID_POLIGONO), IDS))

s2 <- basico %>% filter(sensor == "Sentinel-2")        # filtro exacto de sensor
stopifnot(nrow(s2) == sum(basico$sensor == "Sentinel-2"))
pl <- pro %>% filter(sensor == "Planet")
prep_obs <- function(d) d %>%
  mutate(anio = as.integer(format(fecha, "%Y")), mes = as.integer(format(fecha, "%m")))
s2 <- prep_obs(s2); pl <- prep_obs(pl)
cat("Sentinel-2 2025 (abr-oct): filas =", sum(s2$anio == ANIO & s2$mes %in% MESES),
    "| Planet 2025 (abr-oct): filas =", sum(pl$anio == ANIO & pl$mes %in% MESES), "\n\n")

# ---- 4. Compuestos mensuales --------------------------------------------------
# Devuelve una tabla ancha: ID_POLIGONO, satc_<indice>_<tag>_mMM (compuesto) y
# el numero de observaciones validas usadas (n_<indice>_mMM).
compuestos <- function(d, indices, tag, umbral) {
  largo <- d %>%
    filter(anio == ANIO, mes %in% MESES,
           !is.na(porcentaje_nubosidad), porcentaje_nubosidad < umbral) %>%
    pivot_longer(all_of(paste0(indices, "_promedio")),
                 names_to = "indice", values_to = "valor") %>%
    mutate(indice = sub("_promedio$", "", indice)) %>%
    filter(!is.na(valor)) %>%
    group_by(ID_POLIGONO, indice, mes) %>%
    summarise(comp = median(valor), n_obs = n(), .groups = "drop")
  rejilla <- expand_grid(ID_POLIGONO = IDS, indice = indices, mes = MESES) %>%
    left_join(largo, by = c("ID_POLIGONO", "indice", "mes")) %>%
    mutate(n_obs = coalesce(n_obs, 0L),
           col = sprintf("satc_%s_%s_m%02d", indice, tag, mes),
           coln = sprintf("nobs_%s_%s_m%02d", indice, tag, mes))
  comp <- rejilla %>% select(ID_POLIGONO, col, comp) %>%
    pivot_wider(names_from = col, values_from = comp)
  nobs <- rejilla %>% select(ID_POLIGONO, coln, n_obs) %>%
    pivot_wider(names_from = coln, values_from = n_obs)
  list(comp = comp[match(IDS, comp$ID_POLIGONO), ],
       nobs = nobs[match(IDS, nobs$ID_POLIGONO), ])
}

c_s2 <- compuestos(s2, c("ndvi", "savi"),  "s2",     UMBRAL)
c_pl <- compuestos(pl, c("ndvi", "msavi"), "planet", UMBRAL)

# ---- 5. Porcentaje de NA por mes y sensor (decision de que meses conservar) ---
# Regla: un mes con mas de 60% de NA en 197 parcelas y en un sensor puede excluirse.
mensuales <- bind_cols(c_s2$comp, select(c_pl$comp, -ID_POLIGONO))
cols_mes  <- grep("^satc_.*_m[0-9]{2}$", names(mensuales), value = TRUE)
na_mes <- tibble(variable = cols_mes,
                 n_na = colSums(is.na(mensuales[cols_mes])),
                 pct_na = round(100 * n_na / length(IDS), 2))
cat("Porcentaje de NA de cada compuesto mensual (197 parcelas):\n")
print(as.data.frame(na_mes), row.names = FALSE)
MESES_EXCLUIDOS <- na_mes$variable[na_mes$pct_na > 60]
cat("\nCompuestos mensuales con mas de 60% de NA (se excluyen):",
    if (length(MESES_EXCLUIDOS)) paste(MESES_EXCLUIDOS, collapse = ", ") else "ninguno", "\n\n")

# ---- 6. Tabla de calidad por sensor y mes -------------------------------------
resumen_calidad <- function(d, nobs_tab, tag, indice_ref) {
  filas <- lapply(MESES, function(m) {
    nm <- sprintf("m%02d", m)
    v  <- nobs_tab[[sprintf("nobs_%s_%s_%s", indice_ref, tag, nm)]]
    tot <- d %>% filter(anio == ANIO, mes == m) %>% count(ID_POLIGONO)
    tot_por_parcela <- tot$n[match(IDS, tot$ID_POLIGONO)]
    tot_por_parcela[is.na(tot_por_parcela)] <- 0L
    tibble(sensor = tag, mes = m, mes_nombre = MES_NOM[nm],
           n_parcelas_validas = sum(v > 0),
           pct_na = round(100 * mean(v == 0), 2),
           obs_totales_media = round(mean(tot_por_parcela), 2),
           obs_validas_media_todas = round(mean(v), 2),
           obs_validas_media_validas = round(mean(v[v > 0]), 2),
           obs_validas_mediana = median(v),
           obs_validas_min = min(v),
           pct_parcelas_con_1_obs = round(100 * mean(v == 1), 2))
  })
  bind_rows(filas)
}
calidad <- bind_rows(resumen_calidad(s2, c_s2$nobs, "s2", "ndvi"),
                     resumen_calidad(pl, c_pl$nobs, "planet", "ndvi"))
cat("Calidad por sensor y mes (indice de referencia: NDVI):\n")
print(as.data.frame(calidad), row.names = FALSE)
write_csv(calidad, file.path(VARS, "sat_compuestos_calidad_mes.csv"))
cat("\nObservaciones validas por parcela-mes (promedio sobre las 197 x 7 celdas):",
    "S2 =", round(mean(as.matrix(select(c_s2$nobs, starts_with("nobs_ndvi")))), 2),
    "| Planet =", round(mean(as.matrix(select(c_pl$nobs, starts_with("nobs_ndvi")))), 2), "\n")
mismo_patron <- function(a, b) all((unname(as.matrix(a)) > 0) == (unname(as.matrix(b)) > 0))
stopifnot(mismo_patron(select(c_s2$nobs, starts_with("nobs_ndvi")), select(c_s2$nobs, starts_with("nobs_savi"))),
          mismo_patron(select(c_pl$nobs, starts_with("nobs_ndvi")), select(c_pl$nobs, starts_with("nobs_msavi"))))
cat("El patron de meses validos es el mismo para ndvi/savi (S2) y ndvi/msavi (Planet).\n\n")

# ---- 7. Resumenes y calidad ---------------------------------------------------
fila_max <- function(df) {
  m <- as.matrix(df); r <- suppressWarnings(apply(m, 1, max, na.rm = TRUE))
  r[!is.finite(r)] <- NA_real_; r
}
fila_prom <- function(df) {
  m <- as.matrix(df); r <- rowMeans(m, na.rm = TRUE); r[is.nan(r)] <- NA_real_; r
}
cols_de <- function(tab, indice, tag, meses) sprintf("satc_%s_%s_m%02d", indice, tag, meses)

res <- tibble(ID_POLIGONO = IDS)
# HA3: maximo del ciclo de los compuestos mensuales de NDVI, por sensor
res$satc_ndvi_max_ciclo_s2     <- fila_max(mensuales[cols_de(mensuales, "ndvi", "s2", MESES)])
res$satc_ndvi_max_ciclo_planet <- fila_max(mensuales[cols_de(mensuales, "ndvi", "planet", MESES)])
# Promedios de los compuestos mensuales en las ventanas B (jun-jul) y C (ago-sep)
VENT <- list(b = 6:7, c = 8:9)
IND  <- list(s2 = c("ndvi", "savi"), planet = c("ndvi", "msavi"))
for (tag in names(IND)) for (ind in IND[[tag]]) for (v in names(VENT)) {
  res[[sprintf("satc_%s_%s_%s_prom", ind, tag, v)]] <-
    fila_prom(mensuales[cols_de(mensuales, ind, tag, VENT[[v]])])
}
# Calidad: numero de observaciones sin nubes abril-octubre y meses validos (NDVI)
calid <- tibble(
  ID_POLIGONO = IDS,
  satc_nobs_s2_ciclo          = rowSums(as.matrix(select(c_s2$nobs, starts_with("nobs_ndvi")))),
  satc_nobs_planet_ciclo      = rowSums(as.matrix(select(c_pl$nobs, starts_with("nobs_ndvi")))),
  satc_meses_validos_s2       = rowSums(!is.na(mensuales[cols_de(mensuales, "ndvi", "s2", MESES)])),
  satc_meses_validos_planet   = rowSums(!is.na(mensuales[cols_de(mensuales, "ndvi", "planet", MESES)]))
)
cat("Distribucion de satc_meses_validos_s2:\n");     print(table(calid$satc_meses_validos_s2))
cat("Distribucion de satc_meses_validos_planet:\n"); print(table(calid$satc_meses_validos_planet))
constante <- function(x) length(unique(x[!is.na(x)])) <= 1
MV <- c("satc_meses_validos_s2", "satc_meses_validos_planet")
mv_const <- MV[sapply(calid[MV], constante)]
cat("Variables de calidad constantes (se excluyen de las features):",
    if (length(mv_const)) paste(mv_const, collapse = ", ") else "ninguna", "\n\n")

features <- mensuales %>%
  select(ID_POLIGONO, all_of(setdiff(cols_mes, MESES_EXCLUIDOS))) %>%
  left_join(res, by = "ID_POLIGONO") %>%
  left_join(select(calid, -all_of(mv_const)), by = "ID_POLIGONO")
# Orden final de columnas
orden <- c("ID_POLIGONO",
           setdiff(cols_mes, MESES_EXCLUIDOS),
           "satc_ndvi_max_ciclo_s2", "satc_ndvi_max_ciclo_planet",
           grep("_prom$", names(features), value = TRUE),
           "satc_nobs_s2_ciclo", "satc_nobs_planet_ciclo",
           setdiff(MV, mv_const))
features <- features[, orden]

# ---- 8. Pruebas internas ------------------------------------------------------
VARIABLES <- setdiff(names(features), "ID_POLIGONO")
stopifnot(nrow(features) == 197, identical(features$ID_POLIGONO, IDS),
          !anyDuplicated(features$ID_POLIGONO), length(VARIABLES) <= 40)
const <- VARIABLES[sapply(features[VARIABLES], constante)]
stopifnot(length(const) == 0)
idx_cols <- setdiff(VARIABLES, c("satc_nobs_s2_ciclo", "satc_nobs_planet_ciclo", MV))
rng <- sapply(features[idx_cols], range, na.rm = TRUE)
stopifnot(all(rng >= -1 & rng <= 1))
cat("Variables construidas:", length(VARIABLES), "(tope 40). Rango global de los indices:",
    paste(round(range(rng), 3), collapse = " a "), "\n")

# ---- 9. Sensibilidad al umbral de nubosidad (< 10) ----------------------------
s2_10 <- compuestos(s2, c("ndvi", "savi"),  "s2",     UMBRAL_SENS)$comp
pl_10 <- compuestos(pl, c("ndvi", "msavi"), "planet", UMBRAL_SENS)$comp
sens <- tibble(
  ID_POLIGONO = IDS,
  satc_ndvi_s2_m08_u10 = s2_10$satc_ndvi_s2_m08,
  satc_ndvi_s2_m09_u10 = s2_10$satc_ndvi_s2_m09,
  satc_savi_s2_m08_u10 = s2_10$satc_savi_s2_m08,
  satc_savi_s2_m09_u10 = s2_10$satc_savi_s2_m09,
  satc_ndvi_max_ciclo_s2_u10     = fila_max(s2_10[cols_de(s2_10, "ndvi", "s2", MESES)]),
  satc_ndvi_max_ciclo_planet_u10 = fila_max(pl_10[cols_de(pl_10, "ndvi", "planet", MESES)])
)
write_csv(sens, file.path(VARS, "sat_compuestos_sensibilidad_umbral10.csv"))
comp_sens <- tibble(
  variable_u10 = names(sens)[-1],
  variable_u20 = sub("_u10$", "", names(sens)[-1])) %>%
  rowwise() %>%
  mutate(n_na_u10 = sum(is.na(sens[[variable_u10]])),
         n_na_u20 = sum(is.na(features[[variable_u20]])),
         dif_abs_max = round(max(abs(sens[[variable_u10]] - features[[variable_u20]]), na.rm = TRUE), 4),
         n_parcelas_distintas = sum(abs(sens[[variable_u10]] - features[[variable_u20]]) > 1e-9, na.rm = TRUE),
         cor = round(cor(sens[[variable_u10]], features[[variable_u20]], use = "complete.obs"), 4)) %>%
  ungroup()
cat("\nSensibilidad al umbral (<10 contra <20, mismas parcelas):\n")
print(as.data.frame(comp_sens), row.names = FALSE)

# ---- 10. Diccionario ----------------------------------------------------------
ETQ_IND <- c(ndvi = "NDVI", savi = "SAVI", msavi = "MSAVI")
ETQ_SEN <- c(s2 = "Sentinel-2 (Basico)", planet = "Planet (PRO)")
dic <- lapply(VARIABLES, function(v) {
  p <- strsplit(sub("^satc_", "", v), "_")[[1]]
  base <- list(variable = v, definicion = NA_character_, ventana = NA_character_,
               sensor = "ninguno", unidad = "indice (adimensional)",
               hipotesis_id = NA_character_, notas = "")
  if (grepl("_m[0-9]{2}$", v)) {                      # compuesto mensual
    ind <- p[1]; tag <- p[2]; mm <- p[3]
    base$definicion <- sprintf(
      "Mediana de %s_promedio de parcela (%s) entre las observaciones de %s de 2025 con porcentaje_nubosidad < 20 y valor no vacio; NA si el mes no tiene observacion valida",
      toupper(ind), ETQ_SEN[[tag]], MES_NOM[[mm]])
    base$ventana <- sprintf("mes de %s 2025", MES_NOM[[mm]]); base$sensor <- tag
    base$hipotesis_id <- if (tag == "s2" && mm %in% c("m08", "m09")) "HR12"
      else if (tag == "planet" && mm %in% c("m08", "m09")) "HS1"
      else if (mm %in% c("m04", "m05")) "HS4"
      else if (mm %in% c("m06", "m07")) "HS5" else "HS6"
    base$notas <- "Sin uso de LAI. Mismo nombre y definicion en cualquier otra familia."
  } else if (grepl("^satc_ndvi_max_ciclo_", v)) {   # HA3
    tag <- p[length(p)]
    base$definicion <- sprintf(
      "Maximo de los compuestos mensuales de NDVI (%s) de abril a octubre de 2025; NA solo si ningun mes tiene compuesto", ETQ_SEN[[tag]])
    base$ventana <- "CICLO (abril-octubre 2025)"; base$sensor <- tag; base$hipotesis_id <- "HA3"
    base$notas <- "Maximo de medianas mensuales, menos ruidoso que el maximo de observaciones sueltas. En el registro se llama ndvi_max_ciclo_<sensor>."
  } else if (grepl("_prom$", v)) {                  # promedios por ventana
    ind <- p[1]; tag <- p[2]; vt <- p[3]
    base$definicion <- sprintf(
      "Promedio de los compuestos mensuales de %s (%s) en la ventana %s; se promedian los meses con compuesto y es NA solo si ninguno lo tiene",
      toupper(ind), ETQ_SEN[[tag]], if (vt == "b") "B (junio-julio)" else "C (agosto-septiembre)")
    base$ventana <- if (vt == "b") "B (jun-jul 2025)" else "C (ago-sep 2025)"
    base$sensor <- tag; base$hipotesis_id <- if (vt == "b") "HS2" else "HS3"
    base$notas <- if (vt == "c") "Resume en una variable lo que HR12 (S2) y HS1 (Planet) prueban por mes; se recomienda probar una u otra, no ambas." else ""
  } else if (grepl("^satc_nobs_", v)) {             # calidad: conteo de observaciones
    tag <- p[2]
    base$definicion <- sprintf(
      "Numero de observaciones de %s de abril a octubre de 2025 con porcentaje_nubosidad < 20 y NDVI no vacio (suma de los 7 meses)", ETQ_SEN[[tag]])
    base$ventana <- "CICLO (abril-octubre 2025)"; base$sensor <- tag
    base$unidad <- "observaciones"; base$hipotesis_id <- "HS7"
    base$notas <- "Control de calidad de datos, no agronomia."
  } else {                                          # meses validos (si no fuera constante)
    tag <- p[3]
    base$definicion <- sprintf("Numero de meses de abril a octubre de 2025 con compuesto de NDVI valido (%s)", ETQ_SEN[[tag]])
    base$ventana <- "CICLO (abril-octubre 2025)"; base$sensor <- tag
    base$unidad <- "meses"; base$hipotesis_id <- "HS7"
    base$notas <- "Control de calidad de datos, no agronomia."
  }
  as_tibble(base)
}) %>% bind_rows()
dic$n_na_197  <- sapply(dic$variable, function(v) sum(is.na(features[[v]])))
dic$pct_na_197 <- round(100 * dic$n_na_197 / 197, 2)
dic <- dic[, c("variable", "definicion", "ventana", "sensor", "unidad",
               "n_na_197", "pct_na_197", "hipotesis_id", "notas")]
stopifnot(identical(dic$variable, VARIABLES), !anyNA(dic$hipotesis_id))

# ---- 11. Hipotesis ------------------------------------------------------------
v_b <- c("satc_ndvi_s2_b_prom", "satc_savi_s2_b_prom", "satc_ndvi_planet_b_prom", "satc_msavi_planet_b_prom")
v_c <- c("satc_ndvi_s2_c_prom", "satc_savi_s2_c_prom", "satc_ndvi_planet_c_prom", "satc_msavi_planet_c_prom")
mens <- function(ind, tag, meses) sprintf("satc_%s_%s_m%02d", ind, tag, meses)
todos_meses <- function(meses) c(mens("ndvi", "s2", meses), mens("savi", "s2", meses),
                                 mens("ndvi", "planet", meses), mens("msavi", "planet", meses))
hip <- tribble(
  ~id, ~existente, ~hipotesis, ~variables, ~signo, ~spec,
  "HA3", "si", "",
    paste(c("satc_ndvi_max_ciclo_s2", "satc_ndvi_max_ciclo_planet"), collapse = ";"), "+", "lineal",
  "HR12", "si", "",
    paste(c(mens("ndvi", "s2", 8:9), mens("savi", "s2", 8:9)), collapse = ";"), "+", "lineal",
  "HS1", "no",
    "Los compuestos mensuales sin nubes de agosto y septiembre de NDVI y MSAVI de Planet se asocian con mayor rendimiento dentro de region. Signo: +. Motivo: es el mismo razonamiento de HR12 (vigor en espigado y llenado de grano si la siembra fue de mayo a junio [PV]) pero con otro sensor; Planet tiene mas observaciones validas por parcela y mes que Sentinel-2 (ver sat_compuestos_calidad_mes.csv), asi que la mediana mensual es menos ruidosa, y MSAVI es el indice con correccion de suelo que existe en Planet [V]. Limite: Planet y Sentinel-2 no se mezclan; sin fecha de siembra no se sabe que etapa ve cada mes; los meses sin dato quedan vacios.",
    paste(c(mens("ndvi", "planet", 8:9), mens("msavi", "planet", 8:9)), collapse = ";"), "+", "lineal",
  "HS2", "no",
    "El promedio de los compuestos mensuales de junio y julio (ventana B) de NDVI y SAVI en Sentinel-2 y de NDVI y MSAVI en Planet se asocia con mayor rendimiento dentro de region. Signo: +. Motivo: si la siembra de temporal fue de mayo a junio [PV], junio-julio es emergencia y macollaje y un dosel ya bien establecido indicaria un buen arranque del cultivo [PV]. Limite: con poca cobertura el suelo domina el indice, y el valor puede reflejar la fecha de siembra o la maleza mas que el vigor del cultivo; el signo es el mas incierto de las ventanas y cada sensor se prueba por separado.",
    paste(v_b, collapse = ";"), "+", "lineal",
  "HS3", "no",
    "El promedio de los compuestos mensuales de agosto y septiembre (ventana C) de NDVI y SAVI en Sentinel-2 y de NDVI y MSAVI en Planet se asocia con mayor rendimiento dentro de region. Signo: +. Motivo: resume en una sola variable por indice y sensor lo que HR12 y HS1 prueban mes por mes, y con 138 parcelas conviene menos variables; agosto-septiembre corresponde a espigado y llenado si la siembra fue de mayo a junio [PV]. Limite: si la siembra fue temprana esos meses pueden ser madurez y un indice bajo seria maduracion y no bajo rendimiento, y el NDVI se satura con dosel denso [V-parcial] aunque es raro en estos datos [CP]; es casi redundante con HR12 y HS1, asi que se prueba una u otra.",
    paste(v_c, collapse = ";"), "+", "lineal",
  "HS4", "no",
    "Exploratoria, sin signo previo: los compuestos mensuales de abril y mayo (NDVI y SAVI en Sentinel-2; NDVI y MSAVI en Planet) se prueban para ver si aportan algo sobre la region. Signo: ninguno. Motivo: son meses previos o cercanos a la siembra de temporal [PV], asi que el indice mide sobre todo suelo desnudo, rastrojo del cultivo anterior o maleza de barbecho, que podrian reflejar manejo o humedad previa con signo incierto. Limite: son 8 variables probadas una a una y aumenta el riesgo de un hallazgo por casualidad; solo se toma en cuenta si sobrevive a la seleccion dentro de cada particion; sin fecha de siembra.",
    paste(todos_meses(4:5), collapse = ";"), "ninguno", "lineal",
  "HS5", "no",
    "Exploratoria, sin signo previo: los compuestos mensuales de junio y julio por separado (NDVI y SAVI en Sentinel-2; NDVI y MSAVI en Planet). Signo: ninguno. Motivo: permiten ver si lo que capte HS2 viene de un mes especifico, ya que en el arranque del cultivo un mes de diferencia puede cambiar mucho el dosel [PV]. Limite: 8 variables muy correlacionadas con HS2 y entre si; el riesgo de hallazgo por casualidad es alto y solo cuenta si sobrevive a la seleccion dentro de cada particion.",
    paste(todos_meses(6:7), collapse = ";"), "ninguno", "lineal",
  "HS6", "no",
    "Exploratoria, sin signo previo: los compuestos mensuales de octubre (NDVI y SAVI en Sentinel-2; NDVI y MSAVI en Planet). Signo: ninguno. Motivo: octubre es final de ciclo (madurez o cosecha [PV]); un indice alto puede indicar cultivo tardio, maleza o rebrote y uno bajo, madurez completa o parcela ya cosechada, asi que el signo no se puede fijar de antemano. Limite: 4 variables, la ventana D es la mas dependiente de la fecha de siembra y de cosecha, que no tenemos.",
    paste(todos_meses(10), collapse = ";"), "ninguno", "lineal",
  "HS7", "no",
    "Control de calidad de datos, no agronomia: el numero de observaciones sin nubes entre abril y octubre (Sentinel-2 y Planet) no debe asociarse con el rendimiento. Signo: ninguno. Motivo: sirve para detectar si la nubosidad, que depende de la region y del clima, se cuela como senal, y para saber que tan respaldado esta cada compuesto; los conteos de meses validos se calcularon pero resultaron constantes (7 de 7 meses en todas las parcelas) y por regla se excluyen. Limite: el conteo depende de la region y de la orbita del satelite, no de la parcela.",
    paste(c("satc_nobs_s2_ciclo", "satc_nobs_planet_ciclo"), collapse = ";"), "ninguno", "lineal"
)
# Comprobaciones: cada variable en una hipotesis y coherencia con el diccionario
vars_hip <- unlist(strsplit(hip$variables, ";"))
stopifnot(!anyDuplicated(vars_hip), setequal(vars_hip, VARIABLES))
chk <- tibble(variable = vars_hip, id = rep(hip$id, lengths(strsplit(hip$variables, ";"))))
stopifnot(all(dic$hipotesis_id[match(chk$variable, dic$variable)] == chk$id))
stopifnot(!any(grepl("[^ -~]", unlist(hip))), !any(grepl("\"", hip$hipotesis)),
          !any(grepl("\n", hip$hipotesis)))
stopifnot(!any(grepl("[^ -~]", unlist(dic))))

write_csv(features, file.path(VARS, "sat_compuestos_features.csv"))
write_csv(dic,      file.path(VARS, "sat_compuestos_diccionario.csv"))
write_csv(hip,      file.path(VARS, "sat_compuestos_hipotesis.csv"))

cat("\nResumen final\n")
cat("Variables:", length(VARIABLES), "| filas:", nrow(features),
    "| hipotesis:", nrow(hip), "(existentes:", sum(hip$existente == "si"),
    ", nuevas:", sum(hip$existente == "no"), ")\n")
cat("NA maximo por variable:", max(dic$pct_na_197), "%\n")
cat("Archivos escritos en", VARS, "\n")
