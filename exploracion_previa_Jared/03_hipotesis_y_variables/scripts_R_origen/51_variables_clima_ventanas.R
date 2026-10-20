# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/51_variables_clima_ventanas.R). Original: preparacion/scripts/51_variables_clima_ventanas.R.
# ==============================================================================
# 51_variables_clima_ventanas.R  --  Familia 1: clima por ventanas fenologicas
# Reto AgroCebada FIRA 2026
#
# Proposito: construir, con el mismo codigo para las 197 parcelas, variables de lluvia y
# temperatura por ventana del ciclo 2025 (y las que exigen hipotesis ya registradas) y
# dejar por escrito una hipotesis para cada variable o grupo de variables afines.
# Este script NO lee rendimiento ni evalua nada: solo define variables a ciegas.
#
# Ventanas (anio 2025, suposicion: no hay fecha de siembra por parcela):
#   A = abril-mayo, B = junio-julio, C = agosto-septiembre, D = octubre, CICLO = abril-octubre.
#   Nombres de columna: sufijo _a, _b, _c, _ciclo (como la familia de anomalias). Como D es un solo mes, sus columnas se nombran por el mes (_oct): clim_tmin_oct es la
#   Tmin de la ventana D y es la misma columna que pide la hipotesis HA5.
#
# Reglas: lluvia = suma de los promedios mensuales (mm); Tmax y Tmin = promedio de los meses
# de la ventana (grados C); si falta un mes, la variable queda NA (no se imputa).
#
# Entradas (solo lectura):
#   01_datos/derivados/precipitacion_mensual_por_parcela.csv
#   01_datos/derivados/temperatura_mensual_por_parcela.csv
#   01_datos/preparados/base_197_ubicacion.csv  (lista oficial de las 197 parcelas, sin rendimiento)
# Salidas (03_hipotesis_y_variables/variables/):
#   clima_ventanas_features.csv, clima_ventanas_diccionario.csv, clima_ventanas_hipotesis.csv
#   y el log 04_resultados/logs/51_variables_clima_ventanas.log
# Como correr (PowerShell):
#   Rscript "03_hipotesis_y_variables\scripts\51_variables_clima_ventanas.R"
# Sin azar en este script.
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
DER  <- file.path(RAIZ, "01_datos/derivados")
PREP <- RAIZ
OUT  <- file.path(PREP, "03_hipotesis_y_variables/variables")
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/51_variables_clima_ventanas.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 51_variables_clima_ventanas.R ==\n")
cat("R:", R.version.string, "| readr", as.character(packageVersion("readr")),
    "| dplyr", as.character(packageVersion("dplyr")),
    "| tidyr", as.character(packageVersion("tidyr")),
    "| tibble", as.character(packageVersion("tibble")), "\n")
cat("Sin azar en este script.\n\n")

# ---- 1. Lectura y comprobaciones de entrada ---------------------------------
base <- read_csv(file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"), show_col_types = FALSE, progress = FALSE)
stopifnot(nrow(base) == 197, !anyDuplicated(base$ID_POLIGONO))
ids <- base$ID_POLIGONO

pp <- read_csv(file.path(DER, "precipitacion_mensual_por_parcela.csv"), show_col_types = FALSE, progress = FALSE) |>
  filter(anio == 2025, mes %in% 4:10)
tt <- read_csv(file.path(DER, "temperatura_mensual_por_parcela.csv"), show_col_types = FALSE, progress = FALSE) |>
  filter(anio == 2025, mes %in% 4:10)

stopifnot(setequal(pp$ID_POLIGONO, ids), setequal(tt$ID_POLIGONO, ids))
stopifnot(all(count(pp, ID_POLIGONO)$n == 7), all(count(tt, ID_POLIGONO)$n == 7))
stopifnot(!anyDuplicated(pp[c("ID_POLIGONO", "mes")]), !anyDuplicated(tt[c("ID_POLIGONO", "mes")]))
cat("Entradas: 197 parcelas x 7 meses (abr-oct 2025) en lluvia y en temperatura. NA en entradas:",
    sum(is.na(pp$precip_mm)), "(lluvia),", sum(is.na(tt$tmax_c)) + sum(is.na(tt$tmin_c)), "(temperatura)\n\n")

# ---- 2. Tabla ancha por mes: p4..p10, tx4..tx10, tn4..tn10 -------------------
ancho <- function(d, col, pre) {
  d |> transmute(ID_POLIGONO, nm = paste0(pre, mes), v = .data[[col]]) |>
    pivot_wider(names_from = nm, values_from = v)
}
w <- tibble(ID_POLIGONO = ids) |>
  left_join(ancho(pp, "precip_mm", "p"),  by = "ID_POLIGONO") |>
  left_join(ancho(tt, "tmax_c",   "tx"), by = "ID_POLIGONO") |>
  left_join(ancho(tt, "tmin_c",   "tn"), by = "ID_POLIGONO")

suma  <- function(pre, meses) rowSums(w[paste0(pre, meses)])   # NA si falta algun mes
media <- function(pre, meses) rowMeans(w[paste0(pre, meses)])  # NA si falta algun mes

A <- 4:5; B <- 6:7; C <- 8:9; D <- 10; CICLO <- 4:10

# ---- 3. Variables --------------------------------------------------------------
# Tmedia jul-ago = ((Tmax + Tmin) / 2) promediada en jul y ago [CP]; se usa solo para el indicador de HC2.
# El indicador (1 si Tmedia esta entre 15 y 20 grados C) resulto constante (=1 en las 197 parcelas),
# asi que NO se exporta como variable; se deja calculado aqui para el informe del log.
tmedia_jul_ago <- (media("tx", 7:8) + media("tn", 7:8)) / 2
ind_hc2 <- as.integer(tmedia_jul_ago >= 15 & tmedia_jul_ago <= 20)

f <- tibble(
  ID_POLIGONO = ids,
  # (a) 15 variables base
  clim_precip_a    = suma("p", A),
  clim_precip_b    = suma("p", B),
  clim_precip_c    = suma("p", C),
  clim_precip_oct   = suma("p", D),
  clim_precip_ciclo = suma("p", CICLO),
  clim_tmax_a      = media("tx", A),
  clim_tmax_b      = media("tx", B),
  clim_tmax_c      = media("tx", C),
  clim_tmax_oct     = media("tx", D),
  clim_tmax_ciclo   = media("tx", CICLO),
  clim_tmin_a      = media("tn", A),
  clim_tmin_b      = media("tn", B),
  clim_tmin_c      = media("tn", C),
  clim_tmin_oct     = media("tn", D),
  clim_tmin_ciclo   = media("tn", CICLO),
  # (b) exigidas por hipotesis ya registradas
  clim_tmin_jul     = w$tn7,
  clim_tmin_ago     = w$tn8,
  clim_tmin_sep     = w$tn9,
  clim_tmax_ago     = w$tx8,
  clim_tmax_sep     = w$tx9,
  clim_precip_jun   = w$p6,
  clim_precip_jul   = w$p7,
  clim_precip_ago   = w$p8,
  clim_precip_sep   = w$p9,
  clim_precip_jul_ago = suma("p", 7:8),
  clim_precip_min_mensual_jun_sep = apply(as.matrix(w[paste0("p", 6:9)]), 1, min),
  clim_rango_termico_sep = w$tx9 - w$tn9
)
cat("Variables construidas:", ncol(f) - 1, "(tope 40)\n\n")

# ---- 4. Diccionario -------------------------------------------------------------
d <- function(variable, definicion, ventana, unidad, hip, notas = "") {
  tibble(variable = variable, definicion = definicion, ventana = ventana, unidad = unidad,
         hipotesis_id = hip, notas = notas)
}
nota_v <- "Un solo anio (2025): la variacion entre parcelas es espacial (altitud, ubicacion), no de anios. "
dic <- bind_rows(
  d("clim_precip_a", "Lluvia acumulada: suma de los promedios mensuales de abr y may 2025", "A (abr-may)", "mm", "HW1", "Celdas CHIRPS de ~5.5 km compartidas entre parcelas vecinas"),
  d("clim_precip_b", "Lluvia acumulada: suma de jun y jul 2025", "B (jun-jul)", "mm", "HW1", "Celdas de ~5.5 km compartidas"),
  d("clim_precip_c", "Lluvia acumulada: suma de ago y sep 2025", "C (ago-sep)", "mm", "HW2", "Celdas de ~5.5 km compartidas"),
  d("clim_precip_oct", "Lluvia de octubre 2025 (ventana D es un solo mes)", "D (oct)", "mm", "HW2", "Celdas de ~5.5 km compartidas"),
  d("clim_precip_ciclo", "Lluvia acumulada: suma de abr a oct 2025", "CICLO (abr-oct)", "mm", "HW3;HB4", "Mezcla etapas; para HB4 se prueba tambien su cuadrado"),
  d("clim_tmax_a", "Tmax media: promedio de los promedios mensuales de abr y may 2025", "A (abr-may)", "grados C", "HW5", ""),
  d("clim_tmax_b", "Tmax media: promedio de jun y jul 2025", "B (jun-jul)", "grados C", "HW4", ""),
  d("clim_tmax_c", "Tmax media: promedio de ago y sep 2025", "C (ago-sep)", "grados C", "HW4", ""),
  d("clim_tmax_oct", "Tmax media de octubre 2025", "D (oct)", "grados C", "HW5", ""),
  d("clim_tmax_ciclo", "Tmax media: promedio de abr a oct 2025", "CICLO (abr-oct)", "grados C", "HW5", "El promedio de 7 meses mezcla etapas"),
  d("clim_tmin_a", "Tmin media: promedio de abr y may 2025", "A (abr-may)", "grados C", "HW6", ""),
  d("clim_tmin_b", "Tmin media: promedio de jun y jul 2025", "B (jun-jul)", "grados C", "HW6", ""),
  d("clim_tmin_c", "Tmin media: promedio de ago y sep 2025", "C (ago-sep)", "grados C", "HW6", ""),
  d("clim_tmin_oct", "Tmin media de octubre 2025 (ventana D es un solo mes; es la Tmin de HA5)", "D (oct)", "grados C", "HA5", "Mismo dato que la Tmin de la ventana D"),
  d("clim_tmin_ciclo", "Tmin media: promedio de abr a oct 2025", "CICLO (abr-oct)", "grados C", "HW6", "El promedio de 7 meses mezcla etapas"),
  d("clim_tmin_jul", "Tmin media de julio 2025", "jul", "grados C", "HA4", "Promedio mensual: no cuenta noches bajo 0 C"),
  d("clim_tmin_ago", "Tmin media de agosto 2025", "ago", "grados C", "HA4", "Promedio mensual: no cuenta noches bajo 0 C"),
  d("clim_tmin_sep", "Tmin media de septiembre 2025", "sep", "grados C", "HA5", "Promedio mensual: no cuenta noches bajo 0 C"),
  d("clim_tmax_ago", "Tmax media de agosto 2025", "ago", "grados C", "HB1", ""),
  d("clim_tmax_sep", "Tmax media de septiembre 2025", "sep", "grados C", "HB1", ""),
  d("clim_precip_jun", "Lluvia de junio 2025", "jun", "mm", "HA6;HB3", "Para HB3 se prueba con su cuadrado"),
  d("clim_precip_jul", "Lluvia de julio 2025", "jul", "mm", "HA6", ""),
  d("clim_precip_ago", "Lluvia de agosto 2025", "ago", "mm", "HW7", "Exploratoria (en el texto de HA6)"),
  d("clim_precip_sep", "Lluvia de septiembre 2025", "sep", "mm", "HW7", "Exploratoria (en el texto de HA6)"),
  d("clim_precip_jul_ago", "Lluvia acumulada: suma de jul y ago 2025", "jul-ago", "mm", "HC1;HC2", "HC2 se reduce a esta variable porque su condicion de temperatura se cumple en las 197 parcelas (ver notas)"),
  d("clim_precip_min_mensual_jun_sep", "Lluvia del mes mas seco entre junio y septiembre 2025 (minimo de los 4 totales mensuales)", "jun-sep", "mm", "HB2", "Proxy de canicula; mensual, no detecta periodos secos de dias"),
  d("clim_rango_termico_sep", "Tmax media de septiembre menos Tmin media de septiembre (rango termico) [CP]", "sep", "grados C", "HB8", "Proxy pobre de helada de radiacion")
) |>
  mutate(sensor = "ninguno")

nas <- vapply(f[-1], function(x) sum(is.na(x)), numeric(1))
dic <- dic |>
  mutate(n_na_197 = unname(nas[variable]), pct_na_197 = round(100 * n_na_197 / 197, 2)) |>
  select(variable, definicion, ventana, sensor, unidad, n_na_197, pct_na_197, hipotesis_id, notas)
stopifnot(setequal(dic$variable, names(f)[-1]), !anyDuplicated(dic$variable))
dic <- dic[match(names(f)[-1], dic$variable), ]

# ---- 5. Hipotesis ----------------------------------------------------------------
lim_celda <- "la lluvia y la temperatura vienen de celdas de ~5.5 km que varias parcelas comparten, y solo hay un ciclo (2025), asi que la variacion entre parcelas es espacial (altitud, ubicacion) y no de anios"
h <- function(id, existente, hipotesis, variables, signo, spec = "lineal") {
  tibble(id = id, existente = existente, hipotesis = hipotesis, variables = variables, signo = signo, spec = spec)
}
hip <- bind_rows(
  h("HA4", "si", "", "clim_tmin_jul;clim_tmin_ago", "ninguno"),
  h("HA5", "si", "", "clim_tmin_sep;clim_tmin_oct", "+"),
  h("HA6", "si", "", "clim_precip_jun;clim_precip_jul", "+"),
  h("HB1", "si", "", "clim_tmax_ago;clim_tmax_sep", "-"),
  h("HB2", "si", "", "clim_precip_min_mensual_jun_sep", "+"),
  h("HB3", "si", "", "clim_precip_jun", "ninguno", "clim_precip_jun + I(clim_precip_jun^2)"),
  h("HB4", "si", "", "clim_precip_ciclo", "ninguno", "clim_precip_ciclo + I(clim_precip_ciclo^2)"),
  h("HB8", "si", "", "clim_rango_termico_sep", "-"),
  h("HC1", "si", "", "clim_precip_jul_ago", "-"),
  # HC2: el indicador de Tmedia 15-20 es constante (=1 en las 197), la interaccion no existe; queda solo la lluvia jul-ago
  h("HC2", "si", "", "clim_precip_jul_ago", "-"),
  h("HW1", "no",
    paste0("La lluvia acumulada de abr-may (ventana A) y de jun-jul (ventana B) se asocia con mayor rendimiento dentro de region. Signo: +. ",
           "Motivo: la cebada de temporal en Valles Altos depende de la lluvia para establecerse y para definir espigas por m2 en el macollaje y el encanado (siembra aproximada mayo-junio [PV]). ",
           "Limite: las ventanas son una suposicion porque no hay fecha de siembra (abr-may puede caer antes de sembrar); ", lim_celda, "; se traslapa con HA6, que prueba jun y jul por separado."),
    "clim_precip_a;clim_precip_b", "+"),
  h("HW2", "no",
    paste0("La lluvia de ago-sep (ventana C) y la de octubre (ventana D) son exploratorias, sin signo fijo declarado antes de probar. ",
           "Motivo: en espigado y llenado el agua ayuda, pero la humedad tambien favorece enfermedades de la hoja (ver HC1, signo -), y los dos efectos pueden cancelarse; octubre puede caer despues de la madurez en siembras tempranas [PV]. ",
           "Limite: ", lim_celda, ". No cuenta como confirmada ni refutada."),
    "clim_precip_c;clim_precip_oct", "ninguno"),
  h("HW3", "no",
    paste0("La lluvia acumulada de abr-oct 2025 se prueba aqui solo como termino lineal, sin signo fijo; la forma de curva esta en HB4. ",
           "Motivo: resume el agua del ciclo, pero mezcla etapas con necesidades muy distintas (siembra, macollaje, espigado, llenado), por eso no se le da signo. ",
           "Limite: ", lim_celda, "; una relacion en curva puede verse plana como recta."),
    "clim_precip_ciclo", "ninguno"),
  h("HW4", "no",
    paste0("Una Tmax media alta en jun-jul (ventana B) y en ago-sep (ventana C) baja el rendimiento. Signo: -. ",
           "Motivo: el calor aumenta la demanda de agua y acorta el llenado del grano (relacionada con HB1, que usa ago y sep por separado); efecto esperado debil en Valles Altos. ",
           "Limite: la Tmax mensual no ve olas de calor de pocos dias; ", lim_celda, ", asi que la Tmax puede reflejar sobre todo la altitud del sitio."),
    "clim_tmax_b;clim_tmax_c", "-"),
  h("HW5", "no",
    paste0("La Tmax media de abr-may (ventana A), la de octubre (ventana D) y la del ciclo abr-oct son exploratorias, sin signo fijo declarado antes de probar. ",
           "Motivo: abr-may y octubre caen en emergencia y en madurez o cosecha, donde no hay razon clara para un signo; el promedio de 7 meses mezcla etapas. ",
           "Limite: ", lim_celda, ". No cuenta como confirmada ni refutada."),
    "clim_tmax_a;clim_tmax_oct;clim_tmax_ciclo", "ninguno"),
  h("HW6", "no",
    paste0("La Tmin media de abr-may (A), jun-jul (B), ago-sep (C) y del ciclo abr-oct es exploratoria, sin signo fijo declarado antes de probar. ",
           "Motivo: una Tmin alta reduce el dano por helada (+), pero tambien puede marcar un sitio mas calido y de menor altitud con ciclo mas corto (-), la misma ambiguedad de HA4; la Tmin de octubre y septiembre esta en HA5. ",
           "Limite: el promedio mensual no cuenta noches bajo 0 C; ", lim_celda, ". No cuenta como confirmada ni refutada."),
    "clim_tmin_a;clim_tmin_b;clim_tmin_c;clim_tmin_ciclo", "ninguno"),
  h("HW7", "no",
    paste0("La lluvia de agosto y la de septiembre, cada una por separado, son exploratorias, sin signo fijo. ",
           "Motivo: el texto de HA6 ya las declara exploratorias; se separan aqui para que HA6 (signo +) se evalue solo con jun y jul, y porque en espigado y llenado el agua puede ayudar o favorecer enfermedades (HC1). ",
           "Limite: ", lim_celda, ". No cuenta como confirmada ni refutada."),
    "clim_precip_ago;clim_precip_sep", "ninguno")
)
stopifnot(!anyDuplicated(hip$id))
stopifnot(!any(grepl("[^\\x01-\\x7F]", unlist(hip), perl = TRUE)), !any(grepl("\"|\n", hip$hipotesis)))

# Cada variable listada existe; cada spec se evalua sobre las columnas; cada variable tiene hipotesis
for (i in seq_len(nrow(hip))) {
  vs <- strsplit(hip$variables[i], ";", fixed = TRUE)[[1]]
  stopifnot(all(vs %in% names(f)))
  if (hip$spec[i] != "lineal") {
    fm <- as.formula(paste("~", hip$spec[i]))
    stopifnot(all(all.vars(fm) %in% names(f)))
    mm <- model.matrix(fm, data = f)
    stopifnot(nrow(mm) == 197, !anyNA(mm))
  }
}
en_hip <- unique(unlist(strsplit(hip$variables, ";", fixed = TRUE)))
stopifnot(setequal(en_hip, names(f)[-1]))
hid <- strsplit(dic$hipotesis_id, ";", fixed = TRUE)
stopifnot(all(unlist(hid) %in% hip$id))
# la hipotesis principal de cada variable (primer id del diccionario) la lista en su columna variables
for (i in seq_len(nrow(dic))) stopifnot(dic$variable[i] %in% strsplit(hip$variables[hip$id == hid[[i]][1]], ";", fixed = TRUE)[[1]])

# ---- 6. Escritura -----------------------------------------------------------------
write_csv(f,   file.path(OUT, "clima_ventanas_features.csv"))
write_csv(dic, file.path(OUT, "clima_ventanas_diccionario.csv"))
write_csv(hip, file.path(OUT, "clima_ventanas_hipotesis.csv"), na = "")

# ---- 7. Chequeos e informes ---------------------------------------------------------
cat("---- Chequeos ----\n")
g <- read_csv(file.path(OUT, "clima_ventanas_features.csv"), show_col_types = FALSE, progress = FALSE)
cat("Filas:", nrow(g), "| ID distintos:", n_distinct(g$ID_POLIGONO), "| mismos ID que base_197:", setequal(g$ID_POLIGONO, ids), "\n")
ncte <- sum(vapply(g[-1], function(x) n_distinct(x, na.rm = TRUE) <= 1, logical(1)))
cat("Columnas constantes:", ncte, "\n")
stopifnot(ncte == 0)
cat("NA totales:", sum(is.na(g)), "| tasa maxima de NA por variable:", max(dic$pct_na_197), "%\n")
stopifnot(all(w$tx4 > w$tn4), all(vapply(paste0("tx", 4:10), function(v) all(w[[v]] > w[[sub("tx", "tn", v)]]), logical(1))))
stopifnot(all(f$clim_precip_ciclo >= 0))

cat("\nRangos (min / media / max):\n")
rg <- t(vapply(g[-1], function(x) c(min(x), mean(x), max(x)), numeric(3)))
colnames(rg) <- c("min", "media", "max")
print(round(rg, 2))

cat("\nIndicador HC2 (Tmedia jul-ago entre 15 y 20 C), NO exportado por ser constante:\n")
print(table(indicador = ind_hc2, useNA = "ifany"))
cat("Tmedia jul-ago [CP]: min", round(min(tmedia_jul_ago), 2), "| mediana", round(median(tmedia_jul_ago), 2),
    "| max", round(max(tmedia_jul_ago), 2), "\n")
print(table(grupo = base$grupo, indicador = ind_hc2))

cat("\nCeldas compartidas (valor identico de lluvia del CICLO):\n")
v <- round(f$clim_precip_ciclo, 6)
cat("Valores distintos de celda_clima por cada valor de lluvia, y viceversa (tabla de numero de valores de lluvia por celda):\n")
print(table(valores_de_lluvia_por_celda = as.integer(tapply(round(f$clim_precip_ciclo, 6), base$celda_clima, n_distinct))))
cat("Valores distintos de clim_precip_ciclo:", n_distinct(v), "| celdas distintas (celda_clima) en las 197:", n_distinct(base$celda_clima), "\n")
cat("Parcelas cuyo valor coincide con el de al menos otra parcela:", sum(duplicated(v) | duplicated(v, fromLast = TRUE)), "de 197\n")
cat("Parcelas con valor unico:", sum(!(duplicated(v) | duplicated(v, fromLast = TRUE))), "\n")
cat("Cada celda tiene un solo valor de lluvia:", all(tapply(v, base$celda_clima, n_distinct) == 1),
    "| cada valor pertenece a una sola celda:", all(tapply(base$celda_clima, v, n_distinct) == 1), "\n")
cat("Tamano de los grupos de parcelas con el mismo valor (tabla de tamanos):\n")
print(table(tamano_del_grupo = as.integer(table(v))))

cat("\nParte de la variacion de cada variable que explica solo el grupo regional (R2 de lm(x ~ grupo)); sin rendimiento:\n")
r2g <- vapply(g[-1], function(x) summary(lm(x ~ base$grupo))$r.squared, numeric(1))
print(round(sort(r2g, decreasing = TRUE), 3))

base15 <- c("clim_precip_a", "clim_precip_b", "clim_precip_c", "clim_precip_oct", "clim_precip_ciclo",
            "clim_tmax_a", "clim_tmax_b", "clim_tmax_c", "clim_tmax_oct", "clim_tmax_ciclo",
            "clim_tmin_a", "clim_tmin_b", "clim_tmin_c", "clim_tmin_oct", "clim_tmin_ciclo")
R <- cor(g[base15])
cat("\nCorrelacion (Pearson) entre las 15 variables base:\n")
print(round(R, 2))
ok <- which(upper.tri(R) & abs(R) >= 0.9, arr.ind = TRUE)
cat("\nPares con |r| >= 0.9:", nrow(ok), "\n")
if (nrow(ok) > 0) print(data.frame(a = rownames(R)[ok[, 1]], b = colnames(R)[ok[, 2]], r = round(R[ok], 3)))
ok8 <- which(upper.tri(R) & abs(R) >= 0.8 & abs(R) < 0.9, arr.ind = TRUE)
cat("Pares con 0.8 <= |r| < 0.9:", nrow(ok8), "\n")
if (nrow(ok8) > 0) print(data.frame(a = rownames(R)[ok8[, 1]], b = colnames(R)[ok8[, 2]], r = round(R[ok8], 3)))

cat("\nHipotesis:", nrow(hip), "(existentes:", sum(hip$existente == "si"), "| nuevas:", sum(hip$existente == "no"), ")\n")
cat("Fin.\n")
