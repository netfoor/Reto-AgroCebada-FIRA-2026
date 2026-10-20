# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 02_validacion_y_lineas_base/scripts/62_linea_base_B3.R). Original: preparacion/scripts/62_linea_base_B3.R.
# ==============================================================================
# 62_linea_base_B3.R  --  Semana 3: linea base B3 (media por celda encogida hacia B2)
# Reto AgroCebada FIRA 2026
#
# B3 predice cada parcela de validacion con (n * media_celda + k * media_grupo) / (n + k):
#   n = parcelas de su celda climatica en el ajuste, media_grupo = B2. Sin parcelas de la
#   celda en el ajuste se usa B2. k se elige en cada particion SOLO con el ajuste, dejando
#   una parcela fuera, sobre una rejilla fija; en empate se toma el k mayor. Sin azar.
#
# Registra la hipotesis H5 ANTES de calcular (con respaldo del registro) y al final completa
# solo resultado y decision de esa fila.
# Entradas : datos/base_138.csv, datos/folds_V1.csv, datos/folds_V2.csv,
#            resultados/lineas_base.csv (solo para comprobar B2), resultados/60_pruebas_por_variable.csv
# Salidas  : resultados/62_b3_por_particion.csv, resultados/62_b3_resumen.csv,
#            resultados/logs/62_linea_base_B3.log, resultados/logs/registro_antes_62.csv
# Como correr:  Rscript 02_validacion_y_lineas_base/scripts/62_linea_base_B3.R
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/62_linea_base_B3.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 62_linea_base_B3.R ==\n")
cat("R:", R.version.string, "| dplyr", as.character(packageVersion("dplyr")),
    "| readr", as.character(packageVersion("readr")), "\n")

GRUPOS <- c("Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo")
NG     <- length(GRUPOS)
K_GRID <- c(0, 0.5, 1, 2, 4, 8, 16, 32, 64, Inf)
TOL    <- 1e-12

# ------------------------------------------------------------------------------
# 1. Registro: respaldo y fila H5 ANTES de calcular
# ------------------------------------------------------------------------------
f_reg <- file.path(PREP, "03_hipotesis_y_variables/registro_experimentos.csv")
copia <- file.path(PREP, "04_resultados/logs/registro_antes_62.csv")
if (!file.exists(copia)) file.copy(f_reg, copia)
lee_reg <- function() read_csv(f_reg, col_types = cols(.default = col_character()), na = character(),
                               show_col_types = FALSE)
reg <- lee_reg()
if (!"H5" %in% reg$id) {
  h5 <- tibble(
    id = "H5", fecha = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    hipotesis = paste(
      "B3 (media de la celda climatica encogida hacia la media del grupo, es decir hacia B2) mejora a B2 en V1.",
      "Prediccion de cada parcela de validacion: (n * media_celda + k * media_grupo) / (n + k), con n = parcelas de su celda en el ajuste y media_grupo = B2; si la celda no tiene parcelas en el ajuste se usa B2.",
      "k se elige en cada particion solo con el ajuste, dejando una parcela fuera (sin semillas nuevas), sobre la rejilla 0, 0.5, 1, 2, 4, 8, 16, 32, 64 e infinito (infinito = B2); en empate se toma el k mayor.",
      "RESULTADO ESPERADO, escrito antes de correr: en V1 delta (RMSE de B2 menos RMSE de B3) positivo, entre +0.03 y +0.06 t/ha (RMSE de B3 de 0.44 a 0.47 frente a 0.502), con mejora en al menos 80 de las 100 particiones; en V2 delta exactamente 0, porque en V2 ninguna parcela de validacion tiene celda en el ajuste (0% de vecinos, E0) y B3 cae en B2 por construccion, asi que V2 no puede evaluar B3.",
      "LECTURA FIJADA DE ANTEMANO: si el delta de B3 en V1 es de 0.03 o mas, comparable con los deltas de 0.022 a 0.044 de las variables que pasan E1, la mejora de esas variables en V1 se explica en gran parte por saber en que celda esta la parcela; si es menor a 0.015, las variables aportan mas que la ubicacion; entre 0.015 y 0.03, la lectura es mixta.",
      "Lo que B3 no puede explicar es el delta positivo de esas variables en V2 (0.03 a 0.09).",
      "Limite: hay 3 celdas con parcelas de dos grupos (1984, 2049, 2304) que se usan tal cual, y solo hay 23 celdas.",
      sep = " "),
    variables = "celda_clima; grupo", esquema = "V1 (principal) y V2",
    semillas = "V1: 1-100; V2: 1001-1100; sin semillas nuevas", resultado = "", decision = "")
  write_csv(bind_rows(reg, h5[, names(reg)]), f_reg)
  cat("Registrada H5 antes de calcular.\n")
}

# ------------------------------------------------------------------------------
# 2. Datos y particiones (las mismas que B2)
# ------------------------------------------------------------------------------
base <- read_csv(file.path(PREP, "01_datos/preparados/base_138.csv"), show_col_types = FALSE, progress = FALSE)
stopifnot(nrow(base) == 138, !anyNA(base$RENDIMIENTO_T_HA), !anyNA(base$celda_clima))
y   <- base$RENDIMIENTO_T_HA
g   <- as.integer(factor(base$grupo, levels = GRUPOS)); stopifnot(!anyNA(g))
cel <- as.character(base$celda_clima)
pos <- setNames(seq_len(138), base$ID_POLIGONO)
cat("Celdas climaticas distintas:", length(unique(cel)), "\n")

leer_part <- function(nombre) {
  f <- read_csv(file.path(PREP, "01_datos/preparados", paste0("folds_", nombre, ".csv")), show_col_types = FALSE, progress = FALSE)
  lapply(split(f, f$rep), function(fk)
    list(fit = unname(pos[fk$ID_POLIGONO[fk$rol == "ajuste"]]),
         val = unname(pos[fk$ID_POLIGONO[fk$rol == "validacion"]])))
}
P <- list(V1 = leer_part("V1"), V2 = leer_part("V2"))
stopifnot(length(P$V1) == 100, length(P$V2) == 100)

# ------------------------------------------------------------------------------
# 3. B3 en una particion
# ------------------------------------------------------------------------------
pred_b3 <- function(n, mc, mg, k) {
  if (is.infinite(k)) return(mg)
  ifelse(n > 0, (n * mc + k * mg) / (n + k), mg)
}

b3_particion <- function(fit, val) {
  yF <- y[fit]; gF <- g[fit]; cF <- cel[fit]
  ng <- tabulate(gF, NG)
  Sg <- tapply(yF, factor(gF, levels = seq_len(NG)), sum)
  Sc <- tapply(yF, cF, sum)
  Nc <- tapply(yF, cF, length)
  stopifnot(all(ng[gF] >= 2))

  # Eleccion de k con el ajuste: cada parcela del ajuste se predice sin ella misma
  n_i  <- as.numeric(Nc[cF]) - 1
  mc_i <- ifelse(n_i > 0, (as.numeric(Sc[cF]) - yF) / n_i, NA_real_)
  mg_i <- (as.numeric(Sg[gF]) - yF) / (ng[gF] - 1)
  rm_k <- vapply(K_GRID, function(k) sqrt(mean((yF - pred_b3(n_i, mc_i, mg_i, k))^2)), numeric(1))
  k_star <- max(K_GRID[rm_k <= min(rm_k) + TOL])

  # Prediccion en validacion
  yV <- y[val]; gV <- g[val]; cV <- cel[val]
  stopifnot(all(ng[gV] > 0))
  mg_v <- as.numeric(Sg[gV]) / ng[gV]
  n_v  <- as.numeric(Nc[cV]); n_v[is.na(n_v)] <- 0
  mc_v <- ifelse(n_v > 0, as.numeric(Sc[cV]) / n_v, NA_real_)
  p3   <- pred_b3(n_v, mc_v, mg_v, k_star)
  c(k = k_star, n_val = length(val), n_val_sin_celda = sum(n_v == 0),
    rmse_B2 = sqrt(mean((yV - mg_v)^2)), rmse_B3 = sqrt(mean((yV - p3)^2)))
}

corre <- function(esq) {
  bind_rows(lapply(seq_along(P[[esq]]), function(i) {
    r <- b3_particion(P[[esq]][[i]]$fit, P[[esq]][[i]]$val)
    tibble(esquema = esq, rep = as.integer(names(P[[esq]])[i]), k = r[["k"]], n_val = r[["n_val"]],
           n_val_sin_celda = r[["n_val_sin_celda"]], rmse_B2 = r[["rmse_B2"]], rmse_B3 = r[["rmse_B3"]],
           delta = r[["rmse_B2"]] - r[["rmse_B3"]])
  }))
}
res <- bind_rows(corre("V1"), corre("V2"))

# Comprobacion: el B2 recalculado coincide con lineas_base.csv en las 200 particiones
lb <- read_csv(file.path(PREP, "04_resultados/lineas_base.csv"), show_col_types = FALSE, progress = FALSE)
for (e in c("V1", "V2")) {
  ref <- lb[lb$esquema == e & lb$modelo == "B2", ]
  ref <- ref$rmse[order(ref$rep)]
  obt <- res$rmse_B2[res$esquema == e][order(res$rep[res$esquema == e])]
  stopifnot(max(abs(ref - obt)) < 1e-9)
}
cat("Comprobacion: B2 coincide con lineas_base.csv en las 200 particiones.\n")

# ------------------------------------------------------------------------------
# 4. Resumen
# ------------------------------------------------------------------------------
resumen <- res |>
  group_by(esquema) |>
  summarise(n_part = n(), rmse_B2 = mean(rmse_B2), rmse_B3 = mean(rmse_B3), delta_medio = mean(delta),
            delta_p5 = unname(quantile(delta, .05)), delta_p95 = unname(quantile(delta, .95)),
            n_mejora = sum(delta > TOL), n_igual = sum(abs(delta) <= TOL), n_empeora = sum(delta < -TOL),
            k_mediano = median(k), n_k_infinito = sum(is.infinite(k)),
            pct_val_sin_celda = 100 * sum(n_val_sin_celda) / sum(n_val), .groups = "drop") |>
  mutate(across(where(is.numeric), ~ round(.x, 4)))
write_csv(res |> mutate(across(c(rmse_B2, rmse_B3, delta), ~ round(.x, 4))),
          file.path(PREP, "04_resultados/62_b3_por_particion.csv"))
write_csv(resumen, file.path(PREP, "04_resultados/62_b3_resumen.csv"))
cat("\n== B3 frente a B2 (delta = RMSE B2 - RMSE B3; positivo = mejora) ==\n")
print(as.data.frame(resumen), row.names = FALSE)
cat("\nk elegido en V1 (numero de particiones por valor):\n")
print(table(res$k[res$esquema == "V1"]))

# ------------------------------------------------------------------------------
# 5. Resultado y decision en la fila H5 (solo esa fila)
# ------------------------------------------------------------------------------
v1 <- resumen[resumen$esquema == "V1", ]; v2 <- resumen[resumen$esquema == "V2", ]
pr  <- read_csv(file.path(PREP, "04_resultados/60_pruebas_por_variable.csv"), show_col_types = FALSE, progress = FALSE)
pas <- pr[pr$veredicto == "pasa E1", ]
d <- v1$delta_medio
resultado <- sprintf(
  "V1: RMSE B2 %.3f, B3 %.3f, delta %+.4f (rango 5-95%%: %+.4f a %+.4f); B3 mejora a B2 en %d de 100 particiones (%d iguales, %d peores); k mediano %s, k infinito en %d; %.1f%% de la validacion sin parcelas de su celda en el ajuste. V2: RMSE B2 %.3f, B3 %.3f, delta %+.4f, %.1f%% sin celda en el ajuste. Las %d variables que pasan E1 tienen delta V1 de %.4f a %.4f (media %.4f); B3 alcanza %.0f%% de esa media.",
  v1$rmse_B2, v1$rmse_B3, d, v1$delta_p5, v1$delta_p95, v1$n_mejora, v1$n_igual, v1$n_empeora,
  format(v1$k_mediano), v1$n_k_infinito, v1$pct_val_sin_celda,
  v2$rmse_B2, v2$rmse_B3, v2$delta_medio, v2$pct_val_sin_celda,
  nrow(pas), min(pas$delta_v1), max(pas$delta_v1), mean(pas$delta_v1), 100 * d / mean(pas$delta_v1))
cumple <- d > 0 && d >= 0.03 && d <= 0.06 && v1$n_mejora >= 80 && abs(v2$delta_medio) < 1e-9
lectura <- if (d >= 0.03) {
  "la mejora de las variables en V1 se explica en gran parte por la ubicacion (celda)"
} else if (d < 0.015) {
  "las variables aportan mas que la ubicacion"
} else {
  "lectura mixta"
}
decision <- paste0(
  if (d <= 0) "NO CUMPLIDA: B3 no mejora a B2 en V1. "
  else if (cumple) "CUMPLIDA: direccion y magnitud dentro de lo esperado. "
  else "CUMPLIDA EN DIRECCION, NO EN MAGNITUD O EN NUMERO DE PARTICIONES. ",
  "Lectura fijada de antemano: ", lectura, ". V2 no puede evaluar B3 (sin vecinos), asi que el delta de las variables en V2 no queda explicado por ubicacion.")
reg <- lee_reg()
i <- which(reg$id == "H5"); stopifnot(length(i) == 1)
reg$resultado[i] <- resultado; reg$decision[i] <- decision
write_csv(reg, f_reg)
cat("\nResultado y decision registrados en H5.\nHecho. Sin errores.\n")
