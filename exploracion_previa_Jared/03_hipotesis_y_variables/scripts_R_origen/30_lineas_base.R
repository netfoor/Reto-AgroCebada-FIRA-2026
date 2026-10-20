# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 02_validacion_y_lineas_base/scripts/30_lineas_base.R). Original: preparacion/scripts/30_lineas_base.R.
# ==============================================================================
# 30_lineas_base.R  --  Fase 1.4: líneas base con los esquemas V1, V2 y V3
# Reto AgroCebada FIRA 2026
#
# Modelos (todos se ajustan SOLO con las parcelas de "ajuste" de cada repetición):
#   B0  media global del rendimiento en el ajuste.
#   B1  lm(RENDIMIENTO_T_HA ~ Estado): promedio por Estado.
#   B2  lm(RENDIMIENTO_T_HA ~ grupo): promedio por grupo (Estado + municipio agrupado).
#       Los 5 grupos están anidados dentro de los Estados (cada grupo pertenece a un solo
#       Estado), así que un factor de 5 niveles produce exactamente los mismos valores
#       ajustados que Estado + municipio agrupado; agregar Estado sería redundante.
#
# Métricas (en las parcelas de validación de cada repetición):
#   RMSE (principal, t/ha), MAE (t/ha) y R2_val = 1 - SSE / sum((y - media_del_ajuste)^2).
#   Con R2_val, B0 da exactamente 0 por construcción (su predicción es la media del ajuste).
#
# Lo que no se puede calcular queda como NA (no se rellena): en V3 el grupo que se deja
# fuera no tiene nivel en el ajuste (B2 siempre NA; B1 NA si el Estado desaparece).
#
# Entradas: 01_datos/preparados/base_138.csv y folds_V1/V2/V3.csv
# Salidas : resultados/lineas_base.csv, lineas_base_resumen.csv, rmse_por_grupo.csv,
#           mejora_vs_B0.csv y fig_lineas_base_rmse.png
# Cómo correr:  Rscript 02_validacion_y_lineas_base/scripts/30_lineas_base.R  (después de 20_folds.R)
# Este script no usa azar: las semillas ya están fijadas en los folds.
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(ggplot2)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/30_lineas_base.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 30_lineas_base.R ==\n")
cat("R:", R.version.string, "| dplyr", as.character(packageVersion("dplyr")),
    "| ggplot2", as.character(packageVersion("ggplot2")), "\n")
cat("RNGkind:", paste(RNGkind(), collapse = " / "), "(sin azar en este script)\n\n")

GRUPOS <- c("Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo")
base <- read_csv(file.path(PREP, "01_datos/preparados/base_138.csv"), show_col_types = FALSE, progress = FALSE)
stopifnot(nrow(base) == 138, !any(is.na(base$RENDIMIENTO_T_HA)))
base$Estado <- factor(base$Estado)
base$grupo  <- factor(base$grupo, levels = GRUPOS)
cat("sd del rendimiento (138):", round(sd(base$RENDIMIENTO_T_HA), 3), "t/ha | media:",
    round(mean(base$RENDIMIENTO_T_HA), 3), "\n")

leer_folds <- function(nombre) {
  f <- read_csv(file.path(PREP, "01_datos/preparados", paste0("folds_", nombre, ".csv")),
                show_col_types = FALSE, progress = FALSE)
  f$esquema <- nombre
  f
}
folds <- list(V1 = leer_folds("V1"), V2 = leer_folds("V2"), V3 = leer_folds("V3"))
stopifnot(!("grupo_fuera" %in% names(folds$V1)))

# ------------------------------------------------------------------------------
# Métricas de una predicción
# ------------------------------------------------------------------------------
metricas <- function(y, pred, mu_ajuste) {
  if (anyNA(pred)) return(c(rmse = NA_real_, mae = NA_real_, r2_val = NA_real_))
  sse <- sum((y - pred)^2)
  sst <- sum((y - mu_ajuste)^2)
  c(rmse = sqrt(mean((y - pred)^2)), mae = mean(abs(y - pred)), r2_val = 1 - sse / sst)
}

# Predicción de un modelo lineal solo si todos los niveles de validación existen en el ajuste
predice_lm <- function(formula, var, fit, val) {
  if (!all(as.character(val[[var]]) %in% as.character(fit[[var]]))) return(rep(NA_real_, nrow(val)))
  m <- lm(formula, data = droplevels(fit))
  as.numeric(predict(m, newdata = val))
}

# ------------------------------------------------------------------------------
# Evaluar todas las repeticiones de un esquema
# ------------------------------------------------------------------------------
evalua <- function(f, esquema) {
  filas <- list(); filas_g <- list()
  for (k in sort(unique(f$rep))) {
    fk  <- f[f$rep == k, ]
    fit <- base[base$ID_POLIGONO %in% fk$ID_POLIGONO[fk$rol == "ajuste"], ]
    val <- base[base$ID_POLIGONO %in% fk$ID_POLIGONO[fk$rol == "validacion"], ]
    stopifnot(nrow(fit) + nrow(val) == 138, length(intersect(fit$ID_POLIGONO, val$ID_POLIGONO)) == 0)
    mu <- mean(fit$RENDIMIENTO_T_HA)
    preds <- list(
      B0 = rep(mu, nrow(val)),
      B1 = predice_lm(RENDIMIENTO_T_HA ~ Estado, "Estado", fit, val),
      B2 = predice_lm(RENDIMIENTO_T_HA ~ grupo,  "grupo",  fit, val)
    )
    fuera <- if ("grupo_fuera" %in% names(fk)) unique(fk$grupo_fuera) else NA_character_
    for (mod in names(preds)) {
      m <- metricas(val$RENDIMIENTO_T_HA, preds[[mod]], mu)
      filas[[length(filas) + 1]] <- tibble(esquema = esquema, rep = k, grupo_fuera = fuera, modelo = mod,
                                           n_val = nrow(val), rmse = m[["rmse"]], mae = m[["mae"]], r2_val = m[["r2_val"]])
      # RMSE dentro de cada grupo (región): "error que queda por explicar" en cada zona
      for (g in GRUPOS) {
        i <- which(val$grupo == g)
        if (length(i) > 0 && !anyNA(preds[[mod]][i])) {
          filas_g[[length(filas_g) + 1]] <- tibble(esquema = esquema, rep = k, modelo = mod, grupo = g,
                                                   n_val_grupo = length(i),
                                                   rmse_grupo = sqrt(mean((val$RENDIMIENTO_T_HA[i] - preds[[mod]][i])^2)))
        }
      }
    }
  }
  list(global = bind_rows(filas), por_grupo = bind_rows(filas_g))
}

res <- Map(evalua, folds, names(folds))
lb  <- bind_rows(lapply(res, `[[`, "global"))
lbg <- bind_rows(lapply(res, `[[`, "por_grupo"))
write_csv(lb, file.path(PREP, "04_resultados/lineas_base.csv"))
cat("lineas_base.csv:", nrow(lb), "filas (esquema x repetición x modelo)\n")

# ------------------------------------------------------------------------------
# Resúmenes: media, sd, p5 y p95 entre repeticiones (solo donde se pudo calcular)
# ------------------------------------------------------------------------------
media_ok <- function(v) if (all(is.na(v))) NA_real_ else mean(v, na.rm = TRUE)
sd_ok    <- function(v) if (sum(!is.na(v)) < 2) NA_real_ else sd(v, na.rm = TRUE)
q_ok     <- function(v, p) if (all(is.na(v))) NA_real_ else as.numeric(quantile(v, p, na.rm = TRUE, names = FALSE))

resumen <- lb |>
  group_by(esquema, modelo) |>
  summarise(n_reps_calculadas = sum(!is.na(rmse)), n_reps = n(),
            n_val_media = mean(n_val),
            rmse_media = media_ok(rmse), rmse_sd = sd_ok(rmse), rmse_p5 = q_ok(rmse, .05), rmse_p95 = q_ok(rmse, .95),
            mae_media = media_ok(mae),   mae_sd = sd_ok(mae),   mae_p5 = q_ok(mae, .05),   mae_p95 = q_ok(mae, .95),
            r2_media = media_ok(r2_val), r2_sd = sd_ok(r2_val), r2_p5 = q_ok(r2_val, .05), r2_p95 = q_ok(r2_val, .95),
            .groups = "drop") |>
  mutate(across(where(is.numeric), ~ round(.x, 3)))
write_csv(resumen, file.path(PREP, "04_resultados/lineas_base_resumen.csv"))
cat("\n== Resumen por esquema y modelo (media entre repeticiones; rango = p5-p95) ==\n")
print(as.data.frame(resumen |> select(esquema, modelo, n_reps_calculadas, n_val_media, rmse_media, rmse_p5, rmse_p95,
                                       mae_media, mae_p5, mae_p95, r2_media, r2_p5, r2_p95)), row.names = FALSE)

# Mejora pareada (misma repetición): % que baja el RMSE frente a B0, y B2 frente a B1
ancho <- lb |> select(esquema, rep, modelo, rmse) |> pivot_wider(names_from = modelo, values_from = rmse)
mejora <- ancho |>
  transmute(esquema, rep,
            B1_vs_B0_pct = 100 * (B0 - B1) / B0,
            B2_vs_B0_pct = 100 * (B0 - B2) / B0,
            B2_vs_B1_pct = 100 * (B1 - B2) / B1) |>
  pivot_longer(-c(esquema, rep), names_to = "comparacion", values_to = "reduccion_rmse_pct") |>
  filter(!is.na(reduccion_rmse_pct)) |>
  group_by(esquema, comparacion) |>
  summarise(n_reps = n(), media = mean(reduccion_rmse_pct), p5 = q_ok(reduccion_rmse_pct, .05),
            p95 = q_ok(reduccion_rmse_pct, .95), .groups = "drop") |>
  mutate(across(where(is.numeric), ~ round(.x, 2)))
write_csv(mejora, file.path(PREP, "04_resultados/mejora_vs_B0.csv"))
cat("\n== Reducción % del RMSE (positivo = mejora) ==\n"); print(as.data.frame(mejora), row.names = FALSE)

# RMSE por grupo (región)
rg <- lbg |>
  group_by(esquema, modelo, grupo) |>
  summarise(reps_con_datos = n(), n_val_grupo_media = mean(n_val_grupo),
            rmse_media = mean(rmse_grupo), rmse_p5 = q_ok(rmse_grupo, .05), rmse_p95 = q_ok(rmse_grupo, .95),
            .groups = "drop") |>
  mutate(across(where(is.numeric), ~ round(.x, 3)))
write_csv(rg, file.path(PREP, "04_resultados/rmse_por_grupo.csv"))
cat("\n== RMSE por grupo (V1 y V2, media entre repeticiones) ==\n")
print(as.data.frame(rg |> filter(esquema %in% c("V1", "V2")) |>
                      select(esquema, modelo, grupo, reps_con_datos, rmse_media, rmse_p5, rmse_p95)), row.names = FALSE)

# Desviación estándar del rendimiento dentro de cada grupo (todo el entrenamiento): referencia
sd_grupo <- base |> group_by(grupo) |> summarise(n = n(), media = round(mean(RENDIMIENTO_T_HA), 2),
                                                 sd = round(sd(RENDIMIENTO_T_HA), 3), .groups = "drop")
cat("\nReferencia: media y sd del rendimiento por grupo (138 parcelas):\n"); print(as.data.frame(sd_grupo), row.names = FALSE)

cat("\n== V3 (un grupo fuera): resultado por fold ==\n")
print(as.data.frame(lb |> filter(esquema == "V3") |>
                      select(grupo_fuera, modelo, n_val, rmse, mae, r2_val) |>
                      mutate(across(where(is.numeric), ~ round(.x, 3)))), row.names = FALSE)

# ------------------------------------------------------------------------------
# Figura sencilla: RMSE por modelo y esquema
# ------------------------------------------------------------------------------
etiq <- c(V1 = "V1 - Espejo del reto (70/30)", V2 = "V2 - Por celda climática", V3 = "V3 - Un grupo fuera")
res_plot <- resumen |> filter(esquema %in% c("V1", "V2")) |> mutate(panel = etiq[esquema])
v3_plot  <- lb |> filter(esquema == "V3", !is.na(rmse)) |> mutate(panel = etiq[esquema])

g <- ggplot() +
  geom_pointrange(data = res_plot, aes(x = modelo, y = rmse_media, ymin = rmse_p5, ymax = rmse_p95, colour = modelo),
                  size = 0.7, linewidth = 1) +
  geom_point(data = v3_plot, aes(x = modelo, y = rmse, colour = modelo, shape = grupo_fuera), size = 3) +
  geom_text(data = tibble(panel = etiq[["V3"]], modelo = "B2", y = 0.9),
            aes(x = modelo, y = y, label = "No calculable:
el grupo dejado fuera
no está en el ajuste"),
            size = 3, colour = "#d95f02") +
  facet_wrap(~ panel, nrow = 1) +
  scale_colour_manual(values = c(B0 = "#7f7f7f", B1 = "#1f77b4", B2 = "#d95f02"), guide = "none") +
  labs(title = "Error de las líneas base al predecir el rendimiento",
       subtitle = "B0 = media global · B1 = solo Estado · B2 = Estado + municipio agrupado. Menor es mejor.\nV1 y V2: media y rango 5%-95% entre 100 repeticiones. V3: un punto por grupo dejado fuera.",
       x = "Modelo", y = "RMSE (toneladas por hectárea)", shape = "Grupo dejado fuera (V3)") +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom", plot.subtitle = element_text(size = 9))
ggsave(file.path(PREP, "04_resultados/fig_lineas_base_rmse.png"), g, width = 11, height = 5.5, dpi = 150, bg = "white")
cat("\nFigura guardada: resultados/fig_lineas_base_rmse.png\n")
cat("\nHecho. Sin errores.\n")
