# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/06_raster_precipitacion.R). Original: outputs/scripts/06_raster_precipitacion.R.
# ==============================================================================
# EDA - 06. Rasters de precipitacion mensual CHIRPS (2022-2025)
# Reto AgroCebada 2026
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(terra)
library(sf)
library(tidyverse)

RASTER_DIR <- "01_datos/originales/rasters_completos/precipitacion/Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025/Precipitacion_mensual"
SHP_PATH   <- "01_datos/originales/parcelas/Parcelas_Reto_AGC_CONJUNTO.shp"
FIG_DIR    <- "01_datos/eda_inicial/figuras"
EDA_DIR    <- "01_datos/eda_inicial/eda"
DER_DIR    <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(DER_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga de rasters (48 GeoTIFF mensuales, 2022-2025)
# ------------------------------------------------------------------------------
archivos <- list.files(RASTER_DIR, pattern = "\\.tif$", recursive = TRUE, full.names = TRUE)
cat("N de archivos raster encontrados:", length(archivos), "(esperado: 48)\n")

precip_stack <- rast(archivos)

# Nombres de capa a partir del nombre de archivo: PREC_AAAA_MM.tif
nombres <- basename(archivos)
info_capas <- tibble(archivo = nombres) |>
  mutate(
    anio = as.integer(str_extract(archivo, "(?<=PREC_)\\d{4}")),
    mes  = as.integer(str_extract(archivo, "(?<=_)\\d{2}(?=\\.tif)"))
  )
names(precip_stack) <- paste0(info_capas$anio, "_", sprintf("%02d", info_capas$mes))

cat("Extension:", paste(round(as.vector(ext(precip_stack)), 4), collapse = ", "), "\n")
cat("Resolucion:", paste(round(res(precip_stack), 5), collapse = " x "), "\n")
cat("Dimensiones (filas x columnas):", nrow(precip_stack), "x", ncol(precip_stack), "\n")
cat("N de capas:", nlyr(precip_stack), "\n")
cat("CRS:", crs(precip_stack, describe = TRUE)$name, "\n")
cat("Rango de anios:", min(info_capas$anio), "-", max(info_capas$anio),
    "| meses por anio esperados: 12 | meses unicos encontrados:", n_distinct(info_capas$mes), "\n")

# ------------------------------------------------------------------------------
# 2. Cruce con el shapefile de parcelas
# ------------------------------------------------------------------------------
parcelas <- st_read(SHP_PATH, quiet = TRUE) |> rename(ID_POLIGONO = ID_POLIGON)
parcelas_v <- vect(parcelas)

cat("\nCRS parcelas == CRS raster?", st_crs(parcelas)$epsg == "4326" && crs(precip_stack) == crs(parcelas_v), "\n")

extraccion <- terra::extract(precip_stack, parcelas_v, fun = mean, na.rm = TRUE, ID = TRUE, exact = TRUE)
extraccion$ID_POLIGONO <- parcelas$ID_POLIGONO[extraccion$ID]

precip_long <- extraccion |>
  select(-ID) |>
  pivot_longer(-ID_POLIGONO, names_to = "periodo", values_to = "precip_mm") |>
  separate(periodo, into = c("anio", "mes"), sep = "_", convert = TRUE)

cat("\nFilas en tabla larga parcela x mes:", nrow(precip_long), "(esperado:", nrow(parcelas) * 48, ")\n")
cat("NA en precip_mm extraida:", sum(is.na(precip_long$precip_mm)), "\n")

write_csv(precip_long, file.path(DER_DIR, "precipitacion_mensual_por_parcela.csv"))

# ------------------------------------------------------------------------------
# 3. Estadisticas descriptivas
# ------------------------------------------------------------------------------
cat("\nResumen global de precipitacion mensual por parcela (mm/mes):\n")
print(summary(precip_long$precip_mm))

precip_anual <- precip_long |>
  group_by(ID_POLIGONO, anio) |>
  summarise(precip_anual_mm = sum(precip_mm, na.rm = TRUE), .groups = "drop")
cat("\nResumen de precipitacion ACUMULADA ANUAL por parcela:\n")
print(precip_anual |> group_by(anio) |> summarise(media = mean(precip_anual_mm), mediana = median(precip_anual_mm),
                                                    min = min(precip_anual_mm), max = max(precip_anual_mm), .groups = "drop"))

precip_promedio_mensual_parcela <- precip_long |>
  group_by(ID_POLIGONO) |>
  summarise(precip_media_mensual = mean(precip_mm, na.rm = TRUE),
            precip_sd_mensual = sd(precip_mm, na.rm = TRUE), .groups = "drop")

# ------------------------------------------------------------------------------
# 4. Figuras
# ------------------------------------------------------------------------------
p_ciclo_mensual <- precip_long |>
  group_by(mes) |>
  summarise(media = mean(precip_mm, na.rm = TRUE), sd = sd(precip_mm, na.rm = TRUE), .groups = "drop") |>
  ggplot(aes(x = factor(mes), y = media)) +
  geom_col(fill = "#2c7fb8") +
  geom_errorbar(aes(ymin = media - sd, ymax = media + sd), width = 0.2) +
  labs(title = "Ciclo mensual promedio de precipitacion (todas las parcelas, 2022-2025)",
       x = "Mes", y = "Precipitacion (mm/mes)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "06_precipitacion_ciclo_mensual.png"), p_ciclo_mensual, width = 8, height = 5, dpi = 150)

p_box_anual <- ggplot(precip_anual, aes(x = factor(anio), y = precip_anual_mm)) +
  geom_boxplot(fill = "#41b6c4") +
  labs(title = "Precipitacion acumulada anual por parcela", x = "Anio", y = "Precipitacion anual (mm)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "06_box_precipitacion_anual.png"), p_box_anual, width = 7, height = 5, dpi = 150)

p_hist_media_parcela <- ggplot(precip_promedio_mensual_parcela, aes(x = precip_media_mensual)) +
  geom_histogram(bins = 30, fill = "#2c7fb8", color = "white") +
  labs(title = "Precipitacion media mensual por parcela (promedio 2022-2025)",
       x = "Precipitacion media mensual (mm)", y = "N parcelas") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "06_hist_precip_media_por_parcela.png"), p_hist_media_parcela, width = 7, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 5. Outliers evidentes (regla IQR) en precipitacion mensual
# ------------------------------------------------------------------------------
q1 <- quantile(precip_long$precip_mm, 0.25, na.rm = TRUE)
q3 <- quantile(precip_long$precip_mm, 0.75, na.rm = TRUE)
iqr <- q3 - q1
outliers_precip <- precip_long |> filter(precip_mm < q1 - 1.5 * iqr | precip_mm > q3 + 1.5 * iqr)
cat("\nN de observaciones parcela-mes marcadas como outlier (IQR 1.5x):", nrow(outliers_precip), "de", nrow(precip_long), "\n")
cat("Meses donde se concentran los outliers (top 10):\n")
print(outliers_precip |> count(anio, mes, sort = TRUE) |> head(10))

# ------------------------------------------------------------------------------
# 6. Relacion preliminar precipitacion vs rendimiento (ENTRENAMIENTO)
#    Ciclo de produccion: abril - octubre 2025
# ------------------------------------------------------------------------------
id_area_rend <- read_csv(file.path(DER_DIR, "id_area_rendimiento_limpio.csv"), show_col_types = FALSE)

precip_ciclo_2025 <- precip_long |>
  filter(anio == 2025, mes >= 4, mes <= 10) |>
  group_by(ID_POLIGONO) |>
  summarise(precip_acumulada_ciclo = sum(precip_mm, na.rm = TRUE), .groups = "drop")

datos_rel <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  inner_join(precip_ciclo_2025, by = "ID_POLIGONO")

cor_precip_rend <- cor(datos_rel$precip_acumulada_ciclo, datos_rel$RENDIMIENTO_T_HA, use = "complete.obs")
cat("\nCorrelacion precipitacion acumulada (abr-oct 2025) vs rendimiento (ENTRENAMIENTO):",
    round(cor_precip_rend, 3), "\n")

p_scatter <- ggplot(datos_rel, aes(x = precip_acumulada_ciclo, y = RENDIMIENTO_T_HA)) +
  geom_point(color = "#2c7fb8") +
  geom_smooth(method = "lm", color = "#d95f0e") +
  labs(title = "Precipitacion acumulada (abr-oct 2025) vs Rendimiento - ENTRENAMIENTO",
       x = "Precipitacion acumulada del ciclo (mm)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "06_scatter_precip_ciclo_vs_rendimiento.png"), p_scatter, width = 7, height = 5, dpi = 150)

write_csv(precip_ciclo_2025, file.path(DER_DIR, "precipitacion_acumulada_ciclo_2025_por_parcela.csv"))

cat("\n06_raster_precipitacion.R completado.\n")
