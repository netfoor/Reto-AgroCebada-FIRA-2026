# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/02_dataset_basico.R). Original: outputs/scripts/02_dataset_basico.R.
# ==============================================================================
# EDA - 02. Conjunto_datos_BASICO_AgroCebada2026.csv (Sentinel-2 + Landsat)
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
basico <- read_csv(
  file.path(DATA_DIR, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
  locale = locale(encoding = "UTF-8"),
  show_col_types = FALSE
) |>
  mutate(
    fecha_captura = dmy(fecha_captura),
    anio = year(fecha_captura),
    mes  = month(fecha_captura)
  )

cat("Dimensiones:", nrow(basico), "x", ncol(basico), "\n")
cat("Sensores:\n"); print(table(basico$sensor, useNA = "ifany"))
cat("Rango de fechas:", as.character(min(basico$fecha_captura)), "a",
    as.character(max(basico$fecha_captura)), "\n")
cat("Parcelas distintas:", n_distinct(basico$ID_POLIGONO), "de 197\n")

# ------------------------------------------------------------------------------
# 2. Estructura general
# ------------------------------------------------------------------------------
skim_out <- skim(basico)
print(skim_out)

# ------------------------------------------------------------------------------
# 3. Datos faltantes por columna (global y por sensor)
# ------------------------------------------------------------------------------
faltantes_col <- basico |>
  summarise(across(where(is.numeric), ~ mean(is.na(.)) * 100)) |>
  pivot_longer(everything(), names_to = "variable", values_to = "pct_na") |>
  arrange(desc(pct_na))
cat("\n% de NA por columna numerica (top 15):\n")
print(head(faltantes_col, 15))
write_csv(faltantes_col, file.path(EDA_DIR, "02_basico_pct_na_por_columna.csv"))

faltantes_por_sensor <- basico |>
  group_by(sensor) |>
  summarise(
    n = n(),
    pct_na_ndvi = mean(is.na(ndvi_promedio)) * 100,
    pct_na_evi  = mean(is.na(evi_promedio)) * 100,
    pct_na_lai  = mean(is.na(lai_promedio)) * 100,
    pct_na_savi = mean(is.na(savi_promedio)) * 100,
    pct_na_vi6t = mean(is.na(vi6t_promedio)) * 100,
    .groups = "drop"
  )
cat("\n% NA de indices clave por sensor (confirma que VI6T es exclusivo de Landsat\n",
    "y el resto de indices provienen de Sentinel-2):\n")
print(faltantes_por_sensor)

# Dentro de cada sensor, aun asi hay NA residual en su indice principal
# (posible efecto de nubosidad / calidad de la escena). Se explora en la seccion 6.

# ------------------------------------------------------------------------------
# 4. Observaciones por parcela y concentracion de faltantes
# ------------------------------------------------------------------------------
obs_por_parcela <- basico |>
  count(ID_POLIGONO, name = "n_observaciones") |>
  arrange(n_observaciones)

cat("\nObservaciones por parcela - resumen:\n")
print(summary(obs_por_parcela$n_observaciones))

p_obs_parcela <- ggplot(obs_por_parcela, aes(x = n_observaciones)) +
  geom_histogram(bins = 30, fill = "#2c7fb8", color = "white") +
  labs(title = "Numero de observaciones (fecha x sensor) por parcela - Dataset Basico",
       x = "Observaciones por parcela", y = "N parcelas") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "02_hist_obs_por_parcela_basico.png"), p_obs_parcela, width = 7, height = 5, dpi = 150)

# Parcelas con muy pocas observaciones (posible cobertura pobre)
parcelas_pocas_obs <- obs_por_parcela |> filter(n_observaciones < quantile(n_observaciones, 0.05))
cat("\nParcelas en el 5% con menos observaciones:\n")
print(parcelas_pocas_obs)

# Faltante de ndvi_promedio concentrado en algunas parcelas (dentro de Sentinel-2)
faltantes_ndvi_por_parcela <- basico |>
  filter(sensor == "Sentinel-2") |>
  group_by(ID_POLIGONO) |>
  summarise(n = n(), pct_na_ndvi = mean(is.na(ndvi_promedio)) * 100, .groups = "drop") |>
  arrange(desc(pct_na_ndvi))
cat("\nParcelas (Sentinel-2) con mayor % de NA en ndvi_promedio (top 10):\n")
print(head(faltantes_ndvi_por_parcela, 10))

# Faltante por fecha (mes-anio): identifica si hay meses con escenas mas incompletas
faltantes_por_fecha <- basico |>
  filter(sensor == "Sentinel-2") |>
  group_by(anio, mes) |>
  summarise(n = n(), pct_na_ndvi = mean(is.na(ndvi_promedio)) * 100, .groups = "drop") |>
  arrange(desc(pct_na_ndvi))
cat("\nMeses (Sentinel-2) con mayor % de NA en ndvi_promedio (top 10):\n")
print(head(faltantes_por_fecha, 10))

# ------------------------------------------------------------------------------
# 5. Distribucion de variables clave
# ------------------------------------------------------------------------------
indices_clave <- c("ndvi_promedio", "evi_promedio", "lai_promedio",
                    "savi_promedio", "ndwi_promedio", "msi_promedio", "vi6t_promedio")

resumen_indices <- basico |>
  select(all_of(indices_clave)) |>
  summarise(across(everything(),
                    list(min = ~min(., na.rm = TRUE), media = ~mean(., na.rm = TRUE),
                         mediana = ~median(., na.rm = TRUE), max = ~max(., na.rm = TRUE),
                         sd = ~sd(., na.rm = TRUE), n_na = ~sum(is.na(.))),
                    .names = "{.col}__{.fn}")) |>
  pivot_longer(everything(), names_to = c("variable", "stat"), names_sep = "__") |>
  pivot_wider(names_from = stat, values_from = value)
cat("\nResumen de indices clave (todas las observaciones, ambos sensores):\n")
print(resumen_indices)

basico_long_clave <- basico |>
  select(sensor, all_of(indices_clave)) |>
  pivot_longer(-sensor, names_to = "indice", values_to = "valor") |>
  filter(!is.na(valor))

p_hist_indices <- ggplot(basico_long_clave, aes(x = valor)) +
  geom_histogram(bins = 40, fill = "#2c7fb8", color = "white") +
  facet_wrap(~indice, scales = "free", ncol = 3) +
  labs(title = "Distribucion de indices clave - Dataset Basico", x = NULL, y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "02_hist_indices_clave_basico.png"), p_hist_indices, width = 11, height = 8, dpi = 150)

p_box_ndvi_sensor <- basico |>
  filter(!is.na(ndvi_promedio)) |>
  ggplot(aes(x = sensor, y = ndvi_promedio, fill = sensor)) +
  geom_boxplot() +
  labs(title = "NDVI promedio por sensor - Dataset Basico", x = NULL, y = "NDVI promedio") +
  theme_minimal() + theme(legend.position = "none")
ggsave(file.path(FIG_DIR, "02_box_ndvi_por_sensor.png"), p_box_ndvi_sensor, width = 6, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 6. Porcentaje de nubosidad: distribucion y relacion con faltantes/outliers
# ------------------------------------------------------------------------------
cat("\nResumen de porcentaje_nubosidad:\n")
print(summary(basico$porcentaje_nubosidad))

p_hist_nube <- ggplot(basico, aes(x = porcentaje_nubosidad)) +
  geom_histogram(bins = 30, fill = "#41b6c4", color = "white") +
  facet_wrap(~sensor) +
  labs(title = "Distribucion de porcentaje de nubosidad por sensor",
       x = "% nubosidad", y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "02_hist_nubosidad_basico.png"), p_hist_nube, width = 8, height = 5, dpi = 150)

# Nubosidad vs faltante de ndvi (dentro de Sentinel-2): compara nubosidad cuando
# ndvi esta presente vs ausente
nube_vs_na <- basico |>
  filter(sensor == "Sentinel-2") |>
  mutate(ndvi_faltante = is.na(ndvi_promedio)) |>
  group_by(ndvi_faltante) |>
  summarise(n = n(), media_nubosidad = mean(porcentaje_nubosidad, na.rm = TRUE),
            mediana_nubosidad = median(porcentaje_nubosidad, na.rm = TRUE), .groups = "drop")
cat("\nNubosidad segun si ndvi_promedio es NA (Sentinel-2):\n")
print(nube_vs_na)

p_box_nube_na <- basico |>
  filter(sensor == "Sentinel-2") |>
  mutate(ndvi_faltante = ifelse(is.na(ndvi_promedio), "NDVI faltante", "NDVI presente")) |>
  ggplot(aes(x = ndvi_faltante, y = porcentaje_nubosidad, fill = ndvi_faltante)) +
  geom_boxplot() +
  labs(title = "Nubosidad segun disponibilidad de NDVI (Sentinel-2)", x = NULL, y = "% nubosidad") +
  theme_minimal() + theme(legend.position = "none")
ggsave(file.path(FIG_DIR, "02_box_nubosidad_vs_ndvi_faltante.png"), p_box_nube_na, width = 6, height = 5, dpi = 150)

# Correlacion nubosidad vs variabilidad intra-parcela del indice (std) como proxy de calidad
cor_nube_std <- basico |>
  filter(sensor == "Sentinel-2", !is.na(ndvi_std)) |>
  summarise(cor = cor(porcentaje_nubosidad, ndvi_std, use = "complete.obs")) |>
  pull(cor)
cat("\nCorrelacion nubosidad vs ndvi_std (Sentinel-2):", round(cor_nube_std, 3), "\n")

# ------------------------------------------------------------------------------
# 7. Deteccion de outliers evidentes (regla IQR 1.5x) en indices clave
# ------------------------------------------------------------------------------
detectar_outliers_iqr <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE); q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  x < (q1 - 1.5 * iqr) | x > (q3 + 1.5 * iqr)
}

outliers_resumen <- basico |>
  select(all_of(indices_clave)) |>
  summarise(across(everything(), ~ sum(detectar_outliers_iqr(.), na.rm = TRUE))) |>
  pivot_longer(everything(), names_to = "variable", values_to = "n_outliers_iqr")
cat("\nN de outliers (regla IQR 1.5x) por indice clave:\n")
print(outliers_resumen)

# ------------------------------------------------------------------------------
# 8. Relacion preliminar variables satelitales vs rendimiento (solo ENTRENAMIENTO)
# ------------------------------------------------------------------------------
id_area_rend <- read_csv(file.path(DER_DIR, "id_area_rendimiento_limpio.csv"), show_col_types = FALSE)

resumen_satelital_parcela <- basico |>
  filter(sensor == "Sentinel-2") |>
  group_by(ID_POLIGONO) |>
  summarise(across(all_of(setdiff(indices_clave, "vi6t_promedio")), ~ mean(., na.rm = TRUE)),
            n_obs_s2 = n(), .groups = "drop")

datos_rel <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  inner_join(resumen_satelital_parcela, by = "ID_POLIGONO")

cat("\nParcelas ENTRENAMIENTO con datos Sentinel-2 disponibles:", nrow(datos_rel), "de 138\n")

correlaciones_rend <- datos_rel |>
  select(RENDIMIENTO_T_HA, ndvi_promedio, evi_promedio, lai_promedio, savi_promedio, ndwi_promedio, msi_promedio) |>
  summarise(across(-RENDIMIENTO_T_HA, ~ cor(., RENDIMIENTO_T_HA, use = "complete.obs"))) |>
  pivot_longer(everything(), names_to = "indice", values_to = "cor_pearson_con_rendimiento") |>
  arrange(desc(abs(cor_pearson_con_rendimiento)))
cat("\nCorrelacion preliminar (promedio de todas las fechas por parcela) vs rendimiento:\n")
print(correlaciones_rend)

p_scatter_ndvi_rend <- ggplot(datos_rel, aes(x = ndvi_promedio, y = RENDIMIENTO_T_HA)) +
  geom_point(color = "#2c7fb8") +
  geom_smooth(method = "lm", color = "#d95f0e") +
  labs(title = "NDVI promedio (media temporal, S2) vs Rendimiento - ENTRENAMIENTO",
       x = "NDVI promedio (media de todas las fechas)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "02_scatter_ndvi_vs_rendimiento.png"), p_scatter_ndvi_rend, width = 7, height = 5, dpi = 150)

write_csv(resumen_satelital_parcela, file.path(DER_DIR, "basico_resumen_satelital_por_parcela.csv"))
write_csv(basico |> select(ID_POLIGONO, fecha_captura, sensor, porcentaje_nubosidad),
          file.path(DER_DIR, "basico_metadatos_observaciones.csv"))

cat("\n02_dataset_basico.R completado.\n")
