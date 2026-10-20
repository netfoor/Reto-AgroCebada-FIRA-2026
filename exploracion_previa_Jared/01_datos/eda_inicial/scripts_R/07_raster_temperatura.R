# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/07_raster_temperatura.R). Original: outputs/scripts/07_raster_temperatura.R.
# ==============================================================================
# EDA - 07. Rasters de temperatura mensual (Tmax / Tmin), 2022-2025
# Reto AgroCebada 2026
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(terra)
library(sf)
library(tidyverse)

TMAX_DIR  <- "01_datos/originales/rasters_completos/temperatura/Reto_AgroCebada_Temperatura_2022_2025/Tmax"
TMIN_DIR  <- "01_datos/originales/rasters_completos/temperatura/Reto_AgroCebada_Temperatura_2022_2025/Tmin"
SHP_PATH  <- "01_datos/originales/parcelas/Parcelas_Reto_AGC_CONJUNTO.shp"
FIG_DIR   <- "01_datos/eda_inicial/figuras"
EDA_DIR   <- "01_datos/eda_inicial/eda"
DER_DIR   <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(DER_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga de rasters (48 GeoTIFF mensuales por variable, 2022-2025)
# ------------------------------------------------------------------------------
cargar_variable <- function(dir_var, etiqueta) {
  archivos <- list.files(dir_var, pattern = "\\.tif$", recursive = TRUE, full.names = TRUE)
  cat("N de archivos", etiqueta, "encontrados:", length(archivos), "(esperado: 48)\n")
  s <- rast(archivos)
  nombres <- basename(archivos)
  info <- tibble(archivo = nombres) |>
    mutate(
      anio = as.integer(str_extract(archivo, "\\d{4}")),
      mes  = as.integer(str_extract(archivo, "(?<=_)\\d{2}(?=\\.tif)"))
    )
  names(s) <- paste0(info$anio, "_", sprintf("%02d", info$mes))
  cat("  Extension:", paste(round(as.vector(ext(s)), 4), collapse = ", "), "\n")
  cat("  Resolucion:", paste(round(res(s), 5), collapse = " x "), "\n")
  cat("  Dimensiones (filas x columnas):", nrow(s), "x", ncol(s), "\n")
  cat("  N de capas:", nlyr(s), "| anios:", min(info$anio), "-", max(info$anio),
      "| meses unicos:", n_distinct(info$mes), "\n")
  s
}

tmax_stack <- cargar_variable(TMAX_DIR, "Tmax")
tmin_stack <- cargar_variable(TMIN_DIR, "Tmin")

# ------------------------------------------------------------------------------
# 2. Cruce con el shapefile de parcelas
# ------------------------------------------------------------------------------
parcelas   <- st_read(SHP_PATH, quiet = TRUE) |> rename(ID_POLIGONO = ID_POLIGON)
parcelas_v <- vect(parcelas)

extraer_long <- function(stack, parcelas_v, ids, valor_nombre) {
  ext <- terra::extract(stack, parcelas_v, fun = mean, na.rm = TRUE, ID = TRUE, exact = TRUE)
  ext$ID_POLIGONO <- ids[ext$ID]
  ext |>
    select(-ID) |>
    pivot_longer(-ID_POLIGONO, names_to = "periodo", values_to = valor_nombre) |>
    separate(periodo, into = c("anio", "mes"), sep = "_", convert = TRUE)
}

tmax_long <- extraer_long(tmax_stack, parcelas_v, parcelas$ID_POLIGONO, "tmax_c")
tmin_long <- extraer_long(tmin_stack, parcelas_v, parcelas$ID_POLIGONO, "tmin_c")

temp_long <- tmax_long |> inner_join(tmin_long, by = c("ID_POLIGONO", "anio", "mes"))

cat("\nFilas en tabla larga parcela x mes (Tmax/Tmin combinadas):", nrow(temp_long),
    "(esperado:", nrow(parcelas) * 48, ")\n")
cat("NA en tmax_c:", sum(is.na(temp_long$tmax_c)), "| NA en tmin_c:", sum(is.na(temp_long$tmin_c)), "\n")

write_csv(temp_long, file.path(DER_DIR, "temperatura_mensual_por_parcela.csv"))

# ------------------------------------------------------------------------------
# 3. Estadisticas descriptivas
# ------------------------------------------------------------------------------
cat("\nResumen global Tmax (C):\n"); print(summary(temp_long$tmax_c))
cat("\nResumen global Tmin (C):\n"); print(summary(temp_long$tmin_c))

# Consistencia fisica: Tmax debe ser >= Tmin en cada parcela-mes
inconsistencias <- temp_long |> filter(tmax_c < tmin_c)
cat("\nN de filas con Tmax < Tmin (inconsistencia fisica):", nrow(inconsistencias), "de", nrow(temp_long), "\n")

amplitud_termica <- temp_long |> mutate(amplitud = tmax_c - tmin_c)
cat("\nResumen amplitud termica mensual (Tmax - Tmin, C):\n"); print(summary(amplitud_termica$amplitud))

# ------------------------------------------------------------------------------
# 4. Outliers evidentes (regla IQR) en Tmax y Tmin
# ------------------------------------------------------------------------------
detectar_outliers <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE); q3 <- quantile(x, 0.75, na.rm = TRUE); iqr <- q3 - q1
  which(x < q1 - 1.5 * iqr | x > q3 + 1.5 * iqr)
}
out_tmax <- detectar_outliers(temp_long$tmax_c)
out_tmin <- detectar_outliers(temp_long$tmin_c)
cat("\nN outliers Tmax (IQR 1.5x):", length(out_tmax), "| N outliers Tmin (IQR 1.5x):", length(out_tmin), "\n")

# ------------------------------------------------------------------------------
# 5. Figuras
# ------------------------------------------------------------------------------
ciclo_mensual <- temp_long |>
  group_by(mes) |>
  summarise(tmax_media = mean(tmax_c, na.rm = TRUE), tmin_media = mean(tmin_c, na.rm = TRUE), .groups = "drop") |>
  pivot_longer(-mes, names_to = "variable", values_to = "valor")

p_ciclo <- ggplot(ciclo_mensual, aes(x = factor(mes), y = valor, color = variable, group = variable)) +
  geom_line(linewidth = 1) + geom_point() +
  labs(title = "Ciclo mensual promedio de temperatura (todas las parcelas, 2022-2025)",
       x = "Mes", y = "Temperatura (C)", color = NULL) +
  theme_minimal()
ggsave(file.path(FIG_DIR, "07_temperatura_ciclo_mensual.png"), p_ciclo, width = 8, height = 5, dpi = 150)

p_hist_tmax <- ggplot(temp_long, aes(x = tmax_c)) +
  geom_histogram(bins = 30, fill = "#d95f0e", color = "white") +
  labs(title = "Distribucion de Tmax mensual por parcela", x = "Tmax (C)", y = "N observaciones parcela-mes") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "07_hist_tmax.png"), p_hist_tmax, width = 7, height = 5, dpi = 150)

p_hist_tmin <- ggplot(temp_long, aes(x = tmin_c)) +
  geom_histogram(bins = 30, fill = "#2c7fb8", color = "white") +
  labs(title = "Distribucion de Tmin mensual por parcela", x = "Tmin (C)", y = "N observaciones parcela-mes") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "07_hist_tmin.png"), p_hist_tmin, width = 7, height = 5, dpi = 150)

p_box_anual <- temp_long |>
  pivot_longer(c(tmax_c, tmin_c), names_to = "variable", values_to = "valor") |>
  ggplot(aes(x = factor(anio), y = valor, fill = variable)) +
  geom_boxplot() +
  labs(title = "Tmax/Tmin por anio (todas las parcelas y meses)", x = "Anio", y = "Temperatura (C)", fill = NULL) +
  theme_minimal()
ggsave(file.path(FIG_DIR, "07_box_temperatura_por_anio.png"), p_box_anual, width = 8, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 6. Relacion preliminar temperatura vs rendimiento (ENTRENAMIENTO)
#    Ciclo de produccion: abril - octubre 2025
# ------------------------------------------------------------------------------
id_area_rend <- read_csv(file.path(DER_DIR, "id_area_rendimiento_limpio.csv"), show_col_types = FALSE)

temp_ciclo_2025 <- temp_long |>
  filter(anio == 2025, mes >= 4, mes <= 10) |>
  group_by(ID_POLIGONO) |>
  summarise(tmax_medio_ciclo = mean(tmax_c, na.rm = TRUE),
            tmin_medio_ciclo = mean(tmin_c, na.rm = TRUE), .groups = "drop")

datos_rel <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  inner_join(temp_ciclo_2025, by = "ID_POLIGONO")

cor_tmax_rend <- cor(datos_rel$tmax_medio_ciclo, datos_rel$RENDIMIENTO_T_HA, use = "complete.obs")
cor_tmin_rend <- cor(datos_rel$tmin_medio_ciclo, datos_rel$RENDIMIENTO_T_HA, use = "complete.obs")
cat("\nCorrelacion Tmax medio ciclo (abr-oct 2025) vs rendimiento (ENTRENAMIENTO):", round(cor_tmax_rend, 3), "\n")
cat("Correlacion Tmin medio ciclo (abr-oct 2025) vs rendimiento (ENTRENAMIENTO):", round(cor_tmin_rend, 3), "\n")

p_scatter_tmax <- ggplot(datos_rel, aes(x = tmax_medio_ciclo, y = RENDIMIENTO_T_HA)) +
  geom_point(color = "#d95f0e") + geom_smooth(method = "lm", color = "#2c7fb8") +
  labs(title = "Tmax medio del ciclo (abr-oct 2025) vs Rendimiento - ENTRENAMIENTO",
       x = "Tmax medio del ciclo (C)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "07_scatter_tmax_ciclo_vs_rendimiento.png"), p_scatter_tmax, width = 7, height = 5, dpi = 150)

write_csv(temp_ciclo_2025, file.path(DER_DIR, "temperatura_media_ciclo_2025_por_parcela.csv"))

cat("\n07_raster_temperatura.R completado.\n")
