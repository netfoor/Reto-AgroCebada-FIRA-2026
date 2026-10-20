# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/52_variables_clima_anomalias.R). Original: preparacion/scripts/52_variables_clima_anomalias.R.
# ==============================================================================
# 52_variables_clima_anomalias.R  --  Familia 2: anomalias climaticas de 2025
# Reto AgroCebada FIRA 2026
#
# Idea: separar "como es el clima de la zona" (que ya lo sabe el grupo/region) de
# "que tan atipico fue 2025 en esa parcela". Para cada parcela y ventana:
#   referencia = promedio de 2022, 2023 y 2024 de la MISMA parcela y MISMA ventana
#                (primero se agrega cada anio por ventana, despues se promedian los 3 anios)
#   anomalia   = valor de 2025 menos referencia
# Solo hay 3 anios de referencia: NO se calculan desviaciones estandar ni z-scores.
#
# Como se agrega cada ventana (igual en 2022, 2023, 2024 y 2025):
#   lluvia: SUMA de los meses de la ventana (mm)
#   Tmin y Tmax: PROMEDIO simple de los meses de la ventana (grados C)
# Ventanas fijas: A = abr-may, B = jun-jul, C = ago-sep, D = oct, CICLO = abr-oct.
# Ventanas de hipotesis ya registradas: jun-ago (HR10) y sep-oct (HR11).
#
# Variables (17):
#   anom_precip_pct_{a,b,c,d,ciclo} : (lluvia2025 - ref) / ref * 100, en %. NA si ref < 1 mm.
#   anom_tmin_{a,b,c,d,ciclo}       : Tmin2025 - ref, en grados C.
#   anom_tmax_{a,b,c,d,ciclo}       : Tmax2025 - ref, en grados C.
#   anom_precip_mm_jun_ago          : suma jun-ago 2025 menos promedio 2022-2024, en mm (HR10).
#   anom_tmin_sep_oct               : Tmin sep-oct 2025 menos promedio 2022-2024, en C (HR11).
#
# No usa rendimiento en ningun momento. No hay azar.
#
# Entradas : 01_datos/derivados/precipitacion_mensual_por_parcela.csv
#            01_datos/derivados/temperatura_mensual_por_parcela.csv
#            01_datos/preparados/base_197_ubicacion.csv
# Salidas  : 03_hipotesis_y_variables/variables/clima_anomalias_features.csv
#            03_hipotesis_y_variables/variables/clima_anomalias_diccionario.csv
#            03_hipotesis_y_variables/variables/clima_anomalias_hipotesis.csv
#            03_hipotesis_y_variables/variables/clima_anomalias_r2_grupo.csv
#            04_resultados/logs/52_variables_clima_anomalias.log
# Como correr: Rscript 03_hipotesis_y_variables/scripts/52_variables_clima_anomalias.R
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
DERIV <- file.path(RAIZ, "01_datos/derivados")
SALIDA <- file.path(PREP, "03_hipotesis_y_variables/variables")
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
dir.create(SALIDA, recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/52_variables_clima_anomalias.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 52_variables_clima_anomalias.R ==\n")
cat("R:", R.version.string, "| readr", as.character(packageVersion("readr")),
    "| dplyr", as.character(packageVersion("dplyr")),
    "| tidyr", as.character(packageVersion("tidyr")),
    "| tibble", as.character(packageVersion("tibble")), "\n")
cat("Sin azar en este script.\n\n")

# ---- Parametros fijos --------------------------------------------------------
ANIOS_REF  <- 2022:2024
ANIO_OBJ   <- 2025
REF_MIN_MM <- 1   # referencia de lluvia menor a 1 mm se considera casi 0: anomalia en % queda NA
VENTANAS <- list(
  a = 4:5, b = 6:7, c = 8:9, d = 10L, ciclo = 4:10,
  jun_ago = 6:8, sep_oct = 9:10
)

# ---- Lectura y revisiones (d): meses completos --------------------------------
ubic <- read_csv(file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"), show_col_types = FALSE, progress = FALSE)
ids <- ubic$ID_POLIGONO
stopifnot(length(ids) == 197, !anyDuplicated(ids))

pp <- read_csv(file.path(DERIV, "precipitacion_mensual_por_parcela.csv"), show_col_types = FALSE, progress = FALSE)
tt <- read_csv(file.path(DERIV, "temperatura_mensual_por_parcela.csv"), show_col_types = FALSE, progress = FALSE)

revisar <- function(d, cols, nombre) {
  cat("Revision de", nombre, "\n")
  cat("  renglones:", nrow(d), "| anios:", paste(sort(unique(d$anio)), collapse = ","),
      "| parcelas:", n_distinct(d$ID_POLIGONO), "\n")
  cat("  ID iguales a base_197_ubicacion:", setequal(d$ID_POLIGONO, ids), "\n")
  cat("  llaves (ID, anio, mes) duplicadas:", sum(duplicated(d[c("ID_POLIGONO", "anio", "mes")])), "\n")
  cat("  NA en columnas de datos:", sum(is.na(d[cols])), "\n")
  n_mes <- d %>% filter(anio %in% c(ANIOS_REF, ANIO_OBJ)) %>%
    group_by(ID_POLIGONO, anio) %>% summarise(n = n_distinct(mes), .groups = "drop")
  cat("  parcela-anio con 12 meses (2022-2025):", sum(n_mes$n == 12), "de", nrow(n_mes),
      "(esperado", 197 * 4, ")\n")
  stopifnot(setequal(d$ID_POLIGONO, ids), !any(duplicated(d[c("ID_POLIGONO", "anio", "mes")])),
            !anyNA(d[cols]), nrow(n_mes) == 197 * 4, all(n_mes$n == 12),
            all(d$mes %in% 1:12))
}
revisar(pp, "precip_mm", "lluvia")
revisar(tt, c("tmax_c", "tmin_c"), "temperatura")
cat("  rango lluvia mensual (mm):", round(range(pp$precip_mm), 2),
    "| Tmax (C):", round(range(tt$tmax_c), 2), "| Tmin (C):", round(range(tt$tmin_c), 2), "\n")
cat("  Tmin <= Tmax en todos los renglones:", all(tt$tmin_c <= tt$tmax_c), "\n\n")

# ---- Agregacion por ventana (misma definicion para todos los anios) ------------
tabla_meses <- bind_rows(lapply(names(VENTANAS), function(v)
  tibble(ventana = v, mes = VENTANAS[[v]], n_meses_vent = length(VENTANAS[[v]]))))

agrega <- function(d, funcion_agrega) {
  d %>%
    filter(anio %in% c(ANIOS_REF, ANIO_OBJ)) %>%
    inner_join(tabla_meses, by = "mes", relationship = "many-to-many") %>%
    group_by(ID_POLIGONO, anio, ventana, n_meses_vent) %>%
    summarise(across(any_of(c("precip_mm", "tmax_c", "tmin_c")), funcion_agrega),
              n_meses = n(), .groups = "drop") %>%
    { stopifnot(all(.$n_meses == .$n_meses_vent)); . }
}
lluvia_v <- agrega(pp, sum)    # suma de los meses
temp_v   <- agrega(tt, mean)   # promedio de los meses

anomalia <- function(d, col) {
  # d: parcela-anio-ventana; regresa referencia, valor 2025 y diferencia por parcela-ventana
  ref <- d %>% filter(anio %in% ANIOS_REF) %>%
    group_by(ID_POLIGONO, ventana) %>%
    summarise(ref = mean(.data[[col]]), n_ref = n(), .groups = "drop")
  stopifnot(all(ref$n_ref == length(ANIOS_REF)))
  obj <- d %>% filter(anio == ANIO_OBJ) %>% select(ID_POLIGONO, ventana, v2025 = all_of(col))
  ref %>% left_join(obj, by = c("ID_POLIGONO", "ventana")) %>%
    mutate(dif = v2025 - ref)
}
an_p  <- anomalia(lluvia_v, "precip_mm")
an_tn <- anomalia(temp_v, "tmin_c")
an_tx <- anomalia(temp_v, "tmax_c")

# ---- Revision de la referencia de lluvia (casi 0) ------------------------------
cat("Referencia de lluvia (mm) por ventana, minimo y mediana sobre las 197 parcelas:\n")
print(an_p %>% group_by(ventana) %>%
        summarise(ref_min = round(min(ref), 2), ref_mediana = round(median(ref), 2),
                  n_ref_menor_umbral = sum(ref < REF_MIN_MM), .groups = "drop"), n = Inf)
cat("\n")
an_p <- an_p %>% mutate(pct = ifelse(ref < REF_MIN_MM, NA_real_, dif / ref * 100))

# ---- Tabla de variables (una fila por parcela) ---------------------------------
ancho <- function(d, col, prefijo, ventanas) {
  d %>% filter(ventana %in% ventanas) %>%
    transmute(ID_POLIGONO, nombre = paste0(prefijo, ventana), valor = .data[[col]]) %>%
    pivot_wider(names_from = nombre, values_from = valor)
}
V4 <- c("a", "b", "c", "d", "ciclo")
f_pct <- ancho(an_p,  "pct", "anom_precip_pct_", V4)
f_tn  <- ancho(an_tn, "dif", "anom_tmin_", V4)
f_tx  <- ancho(an_tx, "dif", "anom_tmax_", V4)
f_hr10 <- an_p  %>% filter(ventana == "jun_ago") %>% transmute(ID_POLIGONO, anom_precip_mm_jun_ago = dif)
f_hr11 <- an_tn %>% filter(ventana == "sep_oct") %>% transmute(ID_POLIGONO, anom_tmin_sep_oct = dif)

orden <- c(paste0("anom_precip_pct_", V4), paste0("anom_tmin_", V4), paste0("anom_tmax_", V4),
           "anom_precip_mm_jun_ago", "anom_tmin_sep_oct")
feat <- tibble(ID_POLIGONO = ids) %>%
  left_join(f_pct, by = "ID_POLIGONO") %>% left_join(f_tn, by = "ID_POLIGONO") %>%
  left_join(f_tx, by = "ID_POLIGONO") %>% left_join(f_hr10, by = "ID_POLIGONO") %>%
  left_join(f_hr11, by = "ID_POLIGONO") %>%
  select(ID_POLIGONO, all_of(orden))
stopifnot(nrow(feat) == 197, ncol(feat) == 1 + 17)
write_csv(feat, file.path(SALIDA, "clima_anomalias_features.csv"), na = "")

# ---- Resumen numerico ----------------------------------------------------------
cat("Resumen de las 17 variables (197 parcelas):\n")
resumen <- feat %>% select(-ID_POLIGONO) %>% pivot_longer(everything(), names_to = "variable") %>%
  group_by(variable) %>%
  summarise(n_na = sum(is.na(value)), minimo = min(value, na.rm = TRUE),
            mediana = median(value, na.rm = TRUE), maximo = max(value, na.rm = TRUE),
            sd = sd(value, na.rm = TRUE), valores_distintos = n_distinct(value), .groups = "drop") %>%
  mutate(across(minimo:sd, ~ round(.x, 3))) %>% arrange(match(variable, orden))
print(resumen, n = Inf, width = Inf)
cat("\n")

# ---- (c) Cuanta varianza explica el grupo (no usa rendimiento) -----------------
GRUPOS <- c("Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo")
d_r2 <- feat %>% left_join(ubic %>% select(ID_POLIGONO, grupo, celda_clima), by = "ID_POLIGONO") %>%
  mutate(grupo = factor(grupo, levels = GRUPOS), celda_clima = factor(celda_clima))
r2_de <- function(y, g) {
  ok <- !is.na(y)
  ajuste <- lm(y[ok] ~ g[ok])
  c(n = sum(ok), r2 = summary(ajuste)$r.squared, r2_ajustado = summary(ajuste)$adj.r.squared)
}
r2_tab <- bind_rows(lapply(orden, function(v) {
  a <- r2_de(d_r2[[v]], d_r2$grupo)
  b <- r2_de(d_r2[[v]], d_r2$celda_clima)
  tibble(variable = v, n = a[["n"]], r2_grupo = a[["r2"]], r2_ajustado_grupo = a[["r2_ajustado"]],
         r2_celda = b[["r2"]], r2_ajustado_celda = b[["r2_ajustado"]])
})) %>% mutate(across(where(is.double), ~ round(.x, 3)))
cat("R2 de anomalia ~ grupo (5 grupos) y anomalia ~ celda_clima (", nlevels(d_r2$celda_clima),
    " celdas) sobre las 197 parcelas:\n", sep = "")
print(r2_tab, n = Inf, width = Inf)
write_csv(r2_tab, file.path(SALIDA, "clima_anomalias_r2_grupo.csv"), na = "")
cat("\nCorrelaciones (Pearson) entre las 17 variables, valores absolutos mayores a 0.8:\n")
cm <- suppressWarnings(cor(feat %>% select(-ID_POLIGONO), use = "pairwise.complete.obs"))
alto <- which(abs(cm) > 0.8 & upper.tri(cm), arr.ind = TRUE)
if (nrow(alto) > 0) {
  print(tibble(a = rownames(cm)[alto[, 1]], b = colnames(cm)[alto[, 2]], r = round(cm[alto], 3)), n = Inf)
} else cat("  ninguna\n")
cat("\n")

# ---- Diccionario ---------------------------------------------------------------
nom_v <- c(a = "A (abr-may)", b = "B (jun-jul)", c = "C (ago-sep)", d = "D (oct)", ciclo = "CICLO (abr-oct)")
dic_pct <- tibble(
  variable = paste0("anom_precip_pct_", V4),
  definicion = paste0("Anomalia de lluvia 2025 en % de la referencia: (suma de lluvia de la ventana en 2025 - promedio 2022-2024 de esa suma) / promedio 2022-2024 * 100. NA si la referencia es menor a ", REF_MIN_MM, " mm"),
  ventana = unname(nom_v[V4]), sensor = "ninguno", unidad = "% de la referencia",
  hipotesis_id = c("HN1", "HN1", "HN2", "HN3", "HN3"),
  notas = "[CP]. Referencia de la misma parcela y ventana. Lluvia de celdas CHIRPS de ~5.5 km promediadas por area, por lo que parcelas vecinas comparten valor. Sin winsorizar.")
dic_tn <- tibble(
  variable = paste0("anom_tmin_", V4),
  definicion = "Anomalia de temperatura minima 2025: promedio de las Tmin mensuales de la ventana en 2025 menos el promedio 2022-2024 de ese promedio",
  ventana = unname(nom_v[V4]), sensor = "ninguno", unidad = "grados C",
  hipotesis_id = c("HN4", "HN5", "HN5", "HN7", "HN7"),
  notas = "[CP]. Promedio simple de los meses (sin ponderar por dias). Tmin de CHIRTS-ERA5 a 5 km nominales: no ve heladas locales.")
dic_tx <- tibble(
  variable = paste0("anom_tmax_", V4),
  definicion = "Anomalia de temperatura maxima 2025: promedio de las Tmax mensuales de la ventana en 2025 menos el promedio 2022-2024 de ese promedio",
  ventana = unname(nom_v[V4]), sensor = "ninguno", unidad = "grados C",
  hipotesis_id = c("HN6", "HN6", "HN6", "HN7", "HN7"),
  notas = "[CP]. Promedio simple de los meses (sin ponderar por dias).")
dic_hr <- tibble(
  variable = c("anom_precip_mm_jun_ago", "anom_tmin_sep_oct"),
  definicion = c("Lluvia acumulada jun-ago 2025 (mm) menos el promedio 2022-2024 de la misma suma, misma parcela",
                 "Promedio de Tmin de sep-oct 2025 menos el promedio 2022-2024 de ese promedio, misma parcela"),
  ventana = c("jun-ago", "sep-oct"), sensor = "ninguno", unidad = c("mm", "grados C"),
  hipotesis_id = c("HR10", "HR11"),
  notas = c("[CP]. El registro HR10 la llama anom_precip_jun_ago; aqui lleva el sufijo mm para distinguirla de las anomalias en %.",
            "[CP]. Ventana fija por la hipotesis registrada HR11."))
dic <- bind_rows(dic_pct, dic_tn, dic_tx, dic_hr) %>%
  mutate(n_na_197 = sapply(variable, function(v) sum(is.na(feat[[v]]))),
         pct_na_197 = round(100 * n_na_197 / 197, 2)) %>%
  select(variable, definicion, ventana, sensor, unidad, n_na_197, pct_na_197, hipotesis_id, notas)
stopifnot(setequal(dic$variable, orden), nrow(dic) == 17)
write_csv(dic, file.path(SALIDA, "clima_anomalias_diccionario.csv"), na = "")

# ---- Hipotesis -----------------------------------------------------------------
hip <- tribble(
  ~id, ~existente, ~hipotesis, ~variables, ~signo, ~spec,
  "HN1", "no",
  "Una lluvia de abr-may (A) y de jun-jul (B) de 2025 mayor a la de 2022-2024 sube el rendimiento. Signo: +. Motivo: la cebada de temporal en Valles Altos depende de la humedad del suelo en la siembra, emergencia y macollamiento [PV]; en 2025 una ventana con mas lluvia que su propia historia deberia reducir el deficit hidrico. Limite: no hay fecha de siembra por parcela, asi que A y B son una suposicion; la lluvia viene de celdas de 5.5 km compartidas entre parcelas vecinas; solo 3 anios de referencia y un solo anio con rendimiento; un exceso puede danar y contradice al signo.",
  "anom_precip_pct_a; anom_precip_pct_b", "+", "lineal",
  "HN2", "no",
  "Una lluvia de ago-sep (C) de 2025 mayor a la de 2022-2024 baja el rendimiento. Signo: -. Motivo: mas humedad en espigado y llenado favorece enfermedades foliares y de la espiga y vuelco [PV]; es la misma idea de HR10 pero con la ventana fija C en porcentaje. Limite: se traslapa con HR10 (jun-ago) y con la variable B, sus resultados no son independientes; celdas de 5.5 km; la ventana C depende de la siembra, que no conocemos.",
  "anom_precip_pct_c", "-", "lineal",
  "HN3", "no",
  "Las anomalias de lluvia de octubre (D) y de todo el ciclo abr-oct (CICLO) se exploran sin signo declarado. Signo: ninguno. Motivo: octubre es madurez y cosecha, donde mas lluvia puede afectar la calidad pero no necesariamente el rendimiento; la suma del ciclo mezcla efectos de signo contrario (falta al inicio, exceso al final). Limite: exploratoria; el porcentaje de octubre puede tener valores extremos porque la referencia es pequena.",
  "anom_precip_pct_d; anom_precip_pct_ciclo", "ninguno", "lineal",
  "HN4", "no",
  "Una Tmin de abr-may (A) de 2025 mas alta que la de 2022-2024 sube el rendimiento. Signo: +. Motivo: noches menos frias reducen el riesgo de helada en la emergencia y el macollamiento inicial [PV]. Limite: CHIRTS-ERA5 tiene resolucion nominal de 5 km y su variacion diaria viene de ERA5 (mucho mas gruesa), por lo que no ve heladas locales; no hay fecha de siembra y la siembra puede ser posterior a mayo; el efecto de un mes o dos promediados es debil.",
  "anom_tmin_a", "+", "lineal",
  "HN5", "no",
  "Las anomalias de Tmin de jun-jul (B) y de ago-sep (C) se exploran sin signo declarado. Signo: ninguno. Motivo: noches mas calidas en macollamiento y llenado pueden acelerar el desarrollo y acortar el llenado (efecto negativo) o reducir el frio limitante en zonas altas (efecto positivo); no hay base propia para elegir el signo. Limite: exploratoria; Tmin de 5 km nominales sin heladas locales.",
  "anom_tmin_b; anom_tmin_c", "ninguno", "lineal",
  "HN6", "no",
  "Una Tmax de abr-may, jun-jul y ago-sep de 2025 mas alta que la de 2022-2024 baja el rendimiento. Signo: -. Motivo: mas calor aumenta la evaporacion y el estres hidrico en cebada de temporal y acorta el llenado [PV]. Limite: en Valles Altos la Tmax suele quedar por debajo de umbrales de estres por calor, asi que el efecto puede ser pequeno; se relaciona con la lluvia (dias nublados son mas frescos), por lo que puede duplicar a las anomalias de lluvia; celdas de 5.5 km.",
  "anom_tmax_a; anom_tmax_b; anom_tmax_c", "-", "lineal",
  "HN7", "no",
  "Las anomalias de Tmin y Tmax de octubre (D) y de todo el ciclo (CICLO) se exploran sin signo declarado. Signo: ninguno. Motivo: octubre es madurez y el promedio del ciclo mezcla ventanas con efectos de signo distinto; se incluyen para completar la familia y ver si alguna resume el ano mejor que las ventanas por separado. Limite: exploratoria; el promedio del ciclo diluye la ventana critica; octubre puede tener heladas locales que la fuente no capta.",
  "anom_tmin_d; anom_tmax_d; anom_tmin_ciclo; anom_tmax_ciclo", "ninguno", "lineal",
  "HR10", "si", "", "anom_precip_mm_jun_ago", "-", "lineal",
  "HR11", "si", "", "anom_tmin_sep_oct", "+", "lineal"
)
vars_hip <- unlist(strsplit(hip$variables, ";\\s*"))
stopifnot(setequal(vars_hip, orden), !anyDuplicated(vars_hip),
          !any(grepl("[^\\x01-\\x7F]", hip$hipotesis, perl = TRUE)),
          !any(grepl("\"|\n", hip$hipotesis)))
stopifnot(setequal(dic$hipotesis_id, hip$id))
# el id de hipotesis del diccionario debe contener a la variable en la hipotesis
chk <- dic %>% rowwise() %>%
  mutate(ok = variable %in% unlist(strsplit(hip$variables[hip$id == hipotesis_id], ";\\s*"))) %>% pull(ok)
stopifnot(all(chk))
write_csv(hip, file.path(SALIDA, "clima_anomalias_hipotesis.csv"), na = "")

cat("Variables construidas:", length(orden), "(tope 25) | hipotesis:", nrow(hip),
    "(", sum(hip$existente == "si"), "existentes,", sum(hip$existente == "no"), "nuevas )\n")
cat("Mayor tasa de NA:", max(dic$pct_na_197), "% \n")
cat("Escrito en:", SALIDA, "\n== fin ==\n")
