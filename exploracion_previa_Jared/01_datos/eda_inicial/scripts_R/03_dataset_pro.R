# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/03_dataset_pro.R). Original: outputs/scripts/03_dataset_pro.R.
# ==============================================================================
# EDA - 03. Conjunto_datos_PRO_AgroCebada.csv (Planet, 2025)
# Reto AgroCebada 2026
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(tidyverse)
library(skimr)

DATA_DIR <- "01_datos/originales"
FIG_DIR  <- "01_datos/eda_inicial/figuras"
EDA_DIR  <- "01_datos/eda_inicial/eda"
DER_DIR  <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(DER_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga
# ------------------------------------------------------------------------------
pro <- read_csv(
  file.path(DATA_DIR, "Conjunto_datos_PRO_AgroCebada.csv"),
  locale = locale(encoding = "UTF-8"),
  show_col_types = FALSE
) |>
  mutate(
    fecha_captura = dmy(fecha_captura),
    anio = year(fecha_captura),
    mes  = month(fecha_captura)
  )

cat("Dimensiones:", nrow(pro), "x", ncol(pro), "\n")
cat("Sensores:\n"); print(table(pro$sensor, useNA = "ifany"))
cat("Rango de fechas:", as.character(min(pro$fecha_captura)), "a",
    as.character(max(pro$fecha_captura)), "\n")
cat("Parcelas distintas:", n_distinct(pro$ID_POLIGONO), "de 197\n")

# ------------------------------------------------------------------------------
# 2. Estructura general
# ------------------------------------------------------------------------------
skim_out <- skim(pro)
print(skim_out)

# ------------------------------------------------------------------------------
# 3. Datos faltantes por columna y por parcela
# ------------------------------------------------------------------------------
faltantes_col <- pro |>
  summarise(across(where(is.numeric), ~ mean(is.na(.)) * 100)) |>
  pivot_longer(everything(), names_to = "variable", values_to = "pct_na") |>
  arrange(desc(pct_na))
cat("\n% de NA por columna numerica:\n")
print(faltantes_col)

obs_por_parcela <- pro |>
  count(ID_POLIGONO, name = "n_observaciones") |>
  arrange(n_observaciones)
cat("\nObservaciones por parcela (PRO) - resumen:\n")
print(summary(obs_por_parcela$n_observaciones))
cat("Parcelas SIN ninguna observacion PRO:", 197 - n_distinct(pro$ID_POLIGONO), "\n")

p_obs_parcela <- ggplot(obs_por_parcela, aes(x = n_observaciones)) +
  geom_histogram(bins = 30, fill = "#238443", color = "white") +
  labs(title = "Numero de observaciones por parcela - Dataset PRO",
       x = "Observaciones por parcela", y = "N parcelas") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "03_hist_obs_por_parcela_pro.png"), p_obs_parcela, width = 7, height = 5, dpi = 150)

faltantes_ndvi_por_parcela <- pro |>
  group_by(ID_POLIGONO) |>
  summarise(n = n(), pct_na_ndvi = mean(is.na(ndvi_promedio)) * 100, .groups = "drop") |>
  arrange(desc(pct_na_ndvi))
cat("\nParcelas con mayor % de NA en ndvi_promedio (top 10):\n")
print(head(faltantes_ndvi_por_parcela, 10))

faltantes_por_fecha <- pro |>
  group_by(anio, mes) |>
  summarise(n = n(), pct_na_ndvi = mean(is.na(ndvi_promedio)) * 100, .groups = "drop") |>
  arrange(mes)
cat("\nFaltante de NDVI por mes (PRO, 2025):\n")
print(faltantes_por_fecha)

# ------------------------------------------------------------------------------
# 4. Distribucion de variables clave
# ------------------------------------------------------------------------------
indices_clave <- c("ndvi_promedio", "evi_promedio", "lai_promedio", "msavi_promedio")

resumen_indices <- pro |>
  select(all_of(indices_clave)) |>
  summarise(across(everything(),
                    list(min = ~min(., na.rm = TRUE), media = ~mean(., na.rm = TRUE),
                         mediana = ~median(., na.rm = TRUE), max = ~max(., na.rm = TRUE),
                         sd = ~sd(., na.rm = TRUE), n_na = ~sum(is.na(.))),
                    .names = "{.col}__{.fn}")) |>
  pivot_longer(everything(), names_to = c("variable", "stat"), names_sep = "__") |>
  pivot_wider(names_from = stat, values_from = value)
cat("\nResumen de indices clave - Dataset PRO:\n")
print(resumen_indices)

pro_long_clave <- pro |>
  select(all_of(indices_clave)) |>
  pivot_longer(everything(), names_to = "indice", values_to = "valor") |>
  filter(!is.na(valor))

p_hist_indices <- ggplot(pro_long_clave, aes(x = valor)) +
  geom_histogram(bins = 40, fill = "#238443", color = "white") +
  facet_wrap(~indice, scales = "free", ncol = 2) +
  labs(title = "Distribucion de indices clave - Dataset PRO (Planet, 2025)", x = NULL, y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "03_hist_indices_clave_pro.png"), p_hist_indices, width = 9, height = 7, dpi = 150)

# ------------------------------------------------------------------------------
# 5. Porcentaje de nubosidad: distribucion y relacion con faltantes/outliers
# ------------------------------------------------------------------------------
cat("\nResumen de porcentaje_nubosidad (PRO):\n")
print(summary(pro$porcentaje_nubosidad))

p_hist_nube <- ggplot(pro, aes(x = porcentaje_nubosidad)) +
  geom_histogram(bins = 30, fill = "#41b6c4", color = "white") +
  labs(title = "Distribucion de porcentaje de nubosidad - Dataset PRO",
       x = "% nubosidad", y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "03_hist_nubosidad_pro.png"), p_hist_nube, width = 7, height = 5, dpi = 150)

nube_vs_na <- pro |>
  mutate(ndvi_faltante = is.na(ndvi_promedio)) |>
  group_by(ndvi_faltante) |>
  summarise(n = n(), media_nubosidad = mean(porcentaje_nubosidad, na.rm = TRUE),
            mediana_nubosidad = median(porcentaje_nubosidad, na.rm = TRUE), .groups = "drop")
cat("\nNubosidad segun si ndvi_promedio es NA (PRO):\n")
print(nube_vs_na)

# ------------------------------------------------------------------------------
# 6. Deteccion de outliers evidentes (regla IQR 1.5x)
# ------------------------------------------------------------------------------
detectar_outliers_iqr <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE); q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  x < (q1 - 1.5 * iqr) | x > (q3 + 1.5 * iqr)
}
outliers_resumen <- pro |>
  select(all_of(indices_clave)) |>
  summarise(across(everything(), ~ sum(detectar_outliers_iqr(.), na.rm = TRUE))) |>
  pivot_longer(everything(), names_to = "variable", values_to = "n_outliers_iqr")
cat("\nN de outliers (regla IQR 1.5x) por indice clave (PRO):\n")
print(outliers_resumen)

# ------------------------------------------------------------------------------
# 7. Relacion preliminar variables satelitales (PRO) vs rendimiento (ENTRENAMIENTO)
# ------------------------------------------------------------------------------
id_area_rend <- read_csv(file.path(DER_DIR, "id_area_rendimiento_limpio.csv"), show_col_types = FALSE)

resumen_pro_parcela <- pro |>
  group_by(ID_POLIGONO) |>
  summarise(across(all_of(indices_clave), ~ mean(., na.rm = TRUE)), n_obs_pro = n(), .groups = "drop")

datos_rel <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  inner_join(resumen_pro_parcela, by = "ID_POLIGONO")

cat("\nParcelas ENTRENAMIENTO con datos PRO disponibles:", nrow(datos_rel), "de 138\n")

if (nrow(datos_rel) > 2) {
  correlaciones_rend <- datos_rel |>
    select(RENDIMIENTO_T_HA, all_of(indices_clave)) |>
    summarise(across(-RENDIMIENTO_T_HA, ~ cor(., RENDIMIENTO_T_HA, use = "complete.obs"))) |>
    pivot_longer(everything(), names_to = "indice", values_to = "cor_pearson_con_rendimiento") |>
    arrange(desc(abs(cor_pearson_con_rendimiento)))
  cat("\nCorrelacion preliminar PRO vs rendimiento:\n")
  print(correlaciones_rend)

  p_scatter <- ggplot(datos_rel, aes(x = ndvi_promedio, y = RENDIMIENTO_T_HA)) +
    geom_point(color = "#238443") +
    geom_smooth(method = "lm", color = "#d95f0e") +
    labs(title = "NDVI promedio (Planet, media temporal) vs Rendimiento - ENTRENAMIENTO",
         x = "NDVI promedio (Planet)", y = "Rendimiento (t/ha)") +
    theme_minimal()
  ggsave(file.path(FIG_DIR, "03_scatter_ndvi_vs_rendimiento_pro.png"), p_scatter, width = 7, height = 5, dpi = 150)
}

write_csv(resumen_pro_parcela, file.path(DER_DIR, "pro_resumen_satelital_por_parcela.csv"))
write_csv(pro |> select(ID_POLIGONO, fecha_captura, sensor, porcentaje_nubosidad),
          file.path(DER_DIR, "pro_metadatos_observaciones.csv"))

cat("\n03_dataset_pro.R completado.\n")
