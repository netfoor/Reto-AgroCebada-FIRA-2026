# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/05_shapefile_parcelas.R). Original: outputs/scripts/05_shapefile_parcelas.R.
# ==============================================================================
# EDA - 05. Shapefile de parcelas (Parcelas_Reto_AGC_CONJUNTO.shp)
# Reto AgroCebada 2026
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(sf)
library(tidyverse)

DATA_DIR <- "01_datos/originales/parcelas"
FIG_DIR  <- "01_datos/eda_inicial/figuras"
EDA_DIR  <- "01_datos/eda_inicial/eda"
DER_DIR  <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(DER_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga
# ------------------------------------------------------------------------------
parcelas <- st_read(file.path(DATA_DIR, "Parcelas_Reto_AGC_CONJUNTO.shp"), quiet = TRUE)

cat("N de parcelas:", nrow(parcelas), "(esperado: 197)\n")
cat("Campos:", paste(names(parcelas), collapse = ", "), "\n")
cat("CRS:", st_crs(parcelas)$input, "\n")
cat("Tipo de geometria:", paste(unique(st_geometry_type(parcelas)), collapse = ", "), "\n")

# El campo de identificador se llama ID_POLIGON (truncado a 10 caracteres por el
# formato .dbf/shapefile); se renombra para ser consistente con los demas archivos.
parcelas <- parcelas |> rename(ID_POLIGONO = ID_POLIGON)

# ------------------------------------------------------------------------------
# 2. Validez de geometrias
# ------------------------------------------------------------------------------
validez <- st_is_valid(parcelas, reason = TRUE)
n_validas <- sum(st_is_valid(parcelas))
cat("\nGeometrias validas:", n_validas, "de", nrow(parcelas), "\n")
if (n_validas < nrow(parcelas)) {
  invalidas <- parcelas |>
    st_drop_geometry() |>
    mutate(razon = validez) |>
    filter(!st_is_valid(parcelas)) |>
    select(ID_POLIGONO, CONJUNTO, razon)
  cat("Parcelas con geometria invalida:\n")
  print(invalidas)
}

# Poligonos duplicados o vacios
cat("Geometrias vacias:", sum(st_is_empty(parcelas)), "\n")
cat("IDs duplicados:", sum(duplicated(parcelas$ID_POLIGONO)), "\n")

# ------------------------------------------------------------------------------
# 3. Campo CONJUNTO: distribucion
# ------------------------------------------------------------------------------
cat("\nDistribucion de CONJUNTO:\n")
print(table(parcelas$CONJUNTO, useNA = "ifany"))

# ------------------------------------------------------------------------------
# 4. Area por parcela: consistencia con el CSV area_ha del shapefile vs
#    AREA_HA del archivo ID_area_rendimiento, y estadisticos
# ------------------------------------------------------------------------------
# El campo de area en el shapefile puede venir con nombre no-ASCII (área_ha)
col_area_shp <- names(parcelas)[str_detect(names(parcelas), "rea_ha|AREA_HA|area_ha")]
cat("\nColumna de area detectada en el shapefile:", col_area_shp, "\n")

parcelas <- parcelas |> rename(AREA_HA_SHP = all_of(col_area_shp))

resumen_area_shp <- parcelas |>
  st_drop_geometry() |>
  group_by(CONJUNTO) |>
  summarise(n = n(), min = min(AREA_HA_SHP), media = mean(AREA_HA_SHP),
            mediana = median(AREA_HA_SHP), max = max(AREA_HA_SHP), sd = sd(AREA_HA_SHP), .groups = "drop")
cat("\nEstadisticos de AREA_HA (shapefile) por CONJUNTO:\n")
print(resumen_area_shp)

# Area geometrica calculada (proyectando a un CRS metrico: EPSG:6372 - Mexico ITRF2008 LCC)
parcelas_proj <- st_transform(parcelas, 6372)
parcelas <- parcelas |> mutate(area_calculada_ha = as.numeric(st_area(parcelas_proj)) / 10000)

comparacion_area <- parcelas |>
  st_drop_geometry() |>
  mutate(diferencia_pct = (area_calculada_ha - AREA_HA_SHP) / AREA_HA_SHP * 100) |>
  select(ID_POLIGONO, AREA_HA_SHP, area_calculada_ha, diferencia_pct)
cat("\nResumen de diferencia % entre area reportada (atributo) y area calculada de la geometria:\n")
print(summary(comparacion_area$diferencia_pct))

grandes_diferencias <- comparacion_area |> filter(abs(diferencia_pct) > 5)
cat("\nParcelas con diferencia >5% entre area reportada y area geometrica calculada:", nrow(grandes_diferencias), "\n")
print(head(grandes_diferencias, 10))

# ------------------------------------------------------------------------------
# 5. Cultivo y Municipio/Estado (metadatos adicionales)
# ------------------------------------------------------------------------------
if ("Cultivo" %in% names(parcelas)) {
  cat("\nCultivo(s) reportado(s):\n"); print(table(parcelas$Cultivo, useNA = "ifany"))
}
if ("Municipio" %in% names(parcelas)) {
  cat("\nParcelas por Municipio:\n"); print(table(parcelas$Municipio, useNA = "ifany"))
}
if ("Estado" %in% names(parcelas)) {
  cat("\nParcelas por Estado:\n"); print(table(parcelas$Estado, useNA = "ifany"))
}

# ------------------------------------------------------------------------------
# 6. Mapa simple coloreado por CONJUNTO
# ------------------------------------------------------------------------------
p_mapa <- ggplot(parcelas) +
  geom_sf(aes(fill = CONJUNTO), color = "grey30", linewidth = 0.1) +
  scale_fill_manual(values = c("ENTRENAMIENTO" = "#2c7fb8", "PREDICCION" = "#d95f0e")) +
  labs(title = "Parcelas Reto AgroCebada 2026 - por CONJUNTO",
       subtitle = paste0(nrow(parcelas), " parcelas | ",
                          sum(parcelas$CONJUNTO == "ENTRENAMIENTO"), " ENTRENAMIENTO / ",
                          sum(parcelas$CONJUNTO == "PREDICCION"), " PREDICCION")) +
  theme_minimal()
ggsave(file.path(FIG_DIR, "05_mapa_parcelas_por_conjunto.png"), p_mapa, width = 8, height = 7, dpi = 150)

# Boxplot de area por conjunto (usando area de la geometria, mas confiable)
p_area_box <- ggplot(parcelas, aes(x = CONJUNTO, y = area_calculada_ha, fill = CONJUNTO)) +
  geom_boxplot() +
  labs(title = "Area (calculada de la geometria) por CONJUNTO", x = NULL, y = "Area (ha)") +
  theme_minimal() + theme(legend.position = "none")
ggsave(file.path(FIG_DIR, "05_box_area_geometrica_por_conjunto.png"), p_area_box, width = 6, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 7. Guardar datos derivados
# ------------------------------------------------------------------------------
st_write(parcelas, file.path(DER_DIR, "parcelas_validadas.gpkg"), delete_dsn = TRUE, quiet = TRUE)
write_csv(parcelas |> st_drop_geometry(), file.path(DER_DIR, "parcelas_atributos.csv"))

cat("\n05_shapefile_parcelas.R completado.\n")
