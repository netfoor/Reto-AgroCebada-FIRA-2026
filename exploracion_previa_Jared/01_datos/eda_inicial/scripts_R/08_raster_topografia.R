# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/08_raster_topografia.R). Original: outputs/scripts/08_raster_topografia.R.
# ==============================================================================
# EDA - 08. Rasters de topografia: elevacion y pendiente (INEGI CEM4, 120 m)
# Reto AgroCebada 2026
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(terra)
library(sf)
library(tidyverse)

TOPO_DIR  <- "01_datos/originales/rasters_completos/topografia/Reto_AgroCebada_Topografia_INEGI_CEM4/Reto_AgroCebada_Topografia_INEGI_CEM4"
SHP_PATH  <- "01_datos/originales/parcelas/Parcelas_Reto_AGC_CONJUNTO.shp"
FIG_DIR   <- "01_datos/eda_inicial/figuras"
EDA_DIR   <- "01_datos/eda_inicial/eda"
DER_DIR   <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(DER_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga de rasters
# ------------------------------------------------------------------------------
elevacion <- rast(file.path(TOPO_DIR, "Elevacion_INEGI_CEM4_120m.tif"))
pendiente <- rast(file.path(TOPO_DIR, "Pendiente_INEGI_CEM4_120m_grados.tif"))

describir <- function(r, etiqueta) {
  cat("\n--", etiqueta, "--\n")
  cat("Extension:", paste(round(as.vector(ext(r)), 2), collapse = ", "), "\n")
  cat("Resolucion:", paste(round(res(r), 2), collapse = " x "), "\n")
  cat("Dimensiones (filas x columnas):", nrow(r), "x", ncol(r), "\n")
  cat("N de capas:", nlyr(r), "\n")
  cat("CRS:", crs(r, describe = TRUE)$name, "\n")
}
describir(elevacion, "Elevacion")
describir(pendiente, "Pendiente")

# ------------------------------------------------------------------------------
# 2. Cruce con el shapefile de parcelas
#    Nota: el raster esta en EPSG:6372 (LCC), el shapefile en WGS84 (EPSG:4326).
#    terra::extract reproyecta el vector automaticamente si detecta CRS distinto.
# ------------------------------------------------------------------------------
parcelas   <- st_read(SHP_PATH, quiet = TRUE) |> rename(ID_POLIGONO = ID_POLIGON)
parcelas_v <- vect(parcelas)

cat("\nCRS parcelas:", st_crs(parcelas)$input, "| CRS elevacion:", crs(elevacion, describe = TRUE)$code, "\n")

ext_elev <- terra::extract(elevacion, parcelas_v, fun = mean, na.rm = TRUE, ID = TRUE, exact = TRUE)
ext_pend <- terra::extract(pendiente, parcelas_v, fun = mean, na.rm = TRUE, ID = TRUE, exact = TRUE)

topo_parcela <- tibble(
  ID_POLIGONO = parcelas$ID_POLIGONO,
  elevacion_m = ext_elev[[2]],
  pendiente_grados = ext_pend[[2]]
)

cat("\nN de parcelas con topografia extraida:", nrow(topo_parcela),
    "| NA en elevacion:", sum(is.na(topo_parcela$elevacion_m)),
    "| NA en pendiente:", sum(is.na(topo_parcela$pendiente_grados)), "\n")

write_csv(topo_parcela, file.path(DER_DIR, "topografia_por_parcela.csv"))

# ------------------------------------------------------------------------------
# 3. Estadisticas descriptivas
# ------------------------------------------------------------------------------
cat("\nResumen elevacion por parcela (m s.n.m.):\n"); print(summary(topo_parcela$elevacion_m))
cat("\nResumen pendiente por parcela (grados):\n"); print(summary(topo_parcela$pendiente_grados))

# Outliers (IQR 1.5x)
detectar_outliers <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE); q3 <- quantile(x, 0.75, na.rm = TRUE); iqr <- q3 - q1
  which(x < q1 - 1.5 * iqr | x > q3 + 1.5 * iqr)
}
out_elev <- detectar_outliers(topo_parcela$elevacion_m)
out_pend <- detectar_outliers(topo_parcela$pendiente_grados)
cat("\nN parcelas outlier en elevacion (IQR 1.5x):", length(out_elev), "\n")
cat("N parcelas outlier en pendiente (IQR 1.5x):", length(out_pend), "\n")
if (length(out_pend) > 0) {
  cat("Parcelas con pendiente atipica:\n")
  print(topo_parcela[out_pend, ])
}

# ------------------------------------------------------------------------------
# 4. Figuras
# ------------------------------------------------------------------------------
p_hist_elev <- ggplot(topo_parcela, aes(x = elevacion_m)) +
  geom_histogram(bins = 25, fill = "#41ab5d", color = "white") +
  labs(title = "Distribucion de elevacion media por parcela", x = "Elevacion (m s.n.m.)", y = "N parcelas") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "08_hist_elevacion.png"), p_hist_elev, width = 7, height = 5, dpi = 150)

p_hist_pend <- ggplot(topo_parcela, aes(x = pendiente_grados)) +
  geom_histogram(bins = 25, fill = "#fe9929", color = "white") +
  labs(title = "Distribucion de pendiente media por parcela", x = "Pendiente (grados)", y = "N parcelas") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "08_hist_pendiente.png"), p_hist_pend, width = 7, height = 5, dpi = 150)

p_scatter_topo <- ggplot(topo_parcela, aes(x = elevacion_m, y = pendiente_grados)) +
  geom_point(color = "#41ab5d") +
  labs(title = "Elevacion vs pendiente por parcela", x = "Elevacion (m s.n.m.)", y = "Pendiente (grados)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "08_scatter_elevacion_vs_pendiente.png"), p_scatter_topo, width = 7, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 5. Relacion preliminar topografia vs rendimiento (ENTRENAMIENTO)
# ------------------------------------------------------------------------------
id_area_rend <- read_csv(file.path(DER_DIR, "id_area_rendimiento_limpio.csv"), show_col_types = FALSE)

datos_rel <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  inner_join(topo_parcela, by = "ID_POLIGONO")

cor_elev_rend <- cor(datos_rel$elevacion_m, datos_rel$RENDIMIENTO_T_HA, use = "complete.obs")
cor_pend_rend <- cor(datos_rel$pendiente_grados, datos_rel$RENDIMIENTO_T_HA, use = "complete.obs")
cat("\nCorrelacion elevacion vs rendimiento (ENTRENAMIENTO):", round(cor_elev_rend, 3), "\n")
cat("Correlacion pendiente vs rendimiento (ENTRENAMIENTO):", round(cor_pend_rend, 3), "\n")

p_scatter_elev_rend <- ggplot(datos_rel, aes(x = elevacion_m, y = RENDIMIENTO_T_HA)) +
  geom_point(color = "#41ab5d") + geom_smooth(method = "lm", color = "#d95f0e") +
  labs(title = "Elevacion vs Rendimiento - ENTRENAMIENTO", x = "Elevacion (m s.n.m.)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "08_scatter_elevacion_vs_rendimiento.png"), p_scatter_elev_rend, width = 7, height = 5, dpi = 150)

p_scatter_pend_rend <- ggplot(datos_rel, aes(x = pendiente_grados, y = RENDIMIENTO_T_HA)) +
  geom_point(color = "#fe9929") + geom_smooth(method = "lm", color = "#d95f0e") +
  labs(title = "Pendiente vs Rendimiento - ENTRENAMIENTO", x = "Pendiente (grados)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "08_scatter_pendiente_vs_rendimiento.png"), p_scatter_pend_rend, width = 7, height = 5, dpi = 150)

cat("\n08_raster_topografia.R completado.\n")
