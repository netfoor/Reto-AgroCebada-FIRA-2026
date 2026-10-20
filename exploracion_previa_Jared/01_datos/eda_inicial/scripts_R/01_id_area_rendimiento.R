# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/01_id_area_rendimiento.R). Original: outputs/scripts/01_id_area_rendimiento.R.
# ==============================================================================
# EDA - 01. ID_area_rendimiento_70_30_Reto_AgroCebada.csv
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
id_area_rend <- read_csv(
  file.path(DATA_DIR, "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"),
  locale = locale(encoding = "UTF-8"),
  show_col_types = FALSE
) |>
  select(-any_of("...5")) |>          # columna vacia final del csv (coma sobrante)
  mutate(CONJUNTO = str_trim(CONJUNTO))

cat("Dimensiones:", nrow(id_area_rend), "x", ncol(id_area_rend), "\n")

# ------------------------------------------------------------------------------
# 2. Estructura general
# ------------------------------------------------------------------------------
str(id_area_rend)
skim_out <- skim(id_area_rend)
print(skim_out)

# ------------------------------------------------------------------------------
# 3. Duplicados y consistencia del ID
# ------------------------------------------------------------------------------
n_ids_unicos <- n_distinct(id_area_rend$ID_POLIGONO)
n_duplicados <- sum(duplicated(id_area_rend$ID_POLIGONO))
cat("IDs unicos:", n_ids_unicos, " | filas duplicadas de ID:", n_duplicados, "\n")

# ------------------------------------------------------------------------------
# 4. Datos faltantes por columna y por CONJUNTO
# ------------------------------------------------------------------------------
faltantes_col <- id_area_rend |>
  summarise(across(everything(), ~ sum(is.na(.)))) |>
  pivot_longer(everything(), names_to = "variable", values_to = "n_faltantes")
print(faltantes_col)

faltantes_por_conjunto <- id_area_rend |>
  group_by(CONJUNTO) |>
  summarise(
    n_parcelas = n(),
    area_na = sum(is.na(AREA_HA)),
    rendimiento_na = sum(is.na(RENDIMIENTO_T_HA)),
    .groups = "drop"
  )
print(faltantes_por_conjunto)

# El rendimiento oculto en PREDICCION es esperado (no es un "faltante" real,
# es el target a estimar por los equipos). Se documenta explicitamente.
cat("\nNota: el rendimiento de PREDICCION esta oculto por diseno del reto,",
    "no es un dato faltante real.\n\n")

# ------------------------------------------------------------------------------
# 5. Distribucion de AREA_HA y RENDIMIENTO_T_HA
# ------------------------------------------------------------------------------
resumen_area <- id_area_rend |>
  group_by(CONJUNTO) |>
  summarise(
    n = n(),
    min = min(AREA_HA, na.rm = TRUE),
    media = mean(AREA_HA, na.rm = TRUE),
    mediana = median(AREA_HA, na.rm = TRUE),
    max = max(AREA_HA, na.rm = TRUE),
    sd = sd(AREA_HA, na.rm = TRUE),
    .groups = "drop"
  )
print(resumen_area)

resumen_rendimiento <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  summarise(
    n = n(),
    min = min(RENDIMIENTO_T_HA, na.rm = TRUE),
    media = mean(RENDIMIENTO_T_HA, na.rm = TRUE),
    mediana = median(RENDIMIENTO_T_HA, na.rm = TRUE),
    max = max(RENDIMIENTO_T_HA, na.rm = TRUE),
    sd = sd(RENDIMIENTO_T_HA, na.rm = TRUE)
  )
print(resumen_rendimiento)

# Histograma de AREA_HA (todas las parcelas)
p_area_hist <- ggplot(id_area_rend, aes(x = AREA_HA)) +
  geom_histogram(bins = 30, fill = "#2c7fb8", color = "white") +
  labs(title = "Distribucion del area por parcela (197 parcelas)",
       x = "Area (ha)", y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "01_hist_area_ha.png"), p_area_hist, width = 7, height = 5, dpi = 150)

# Boxplot de AREA_HA por CONJUNTO
p_area_box <- ggplot(id_area_rend, aes(x = CONJUNTO, y = AREA_HA, fill = CONJUNTO)) +
  geom_boxplot() +
  labs(title = "Area por parcela segun CONJUNTO", x = NULL, y = "Area (ha)") +
  theme_minimal() +
  theme(legend.position = "none")
ggsave(file.path(FIG_DIR, "01_box_area_por_conjunto.png"), p_area_box, width = 6, height = 5, dpi = 150)

# Histograma de RENDIMIENTO_T_HA (solo ENTRENAMIENTO, unico con dato visible)
p_rend_hist <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  ggplot(aes(x = RENDIMIENTO_T_HA)) +
  geom_histogram(bins = 25, fill = "#d95f0e", color = "white") +
  labs(title = "Distribucion del rendimiento (t/ha) - solo ENTRENAMIENTO",
       x = "Rendimiento (t/ha)", y = "Frecuencia") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "01_hist_rendimiento_entrenamiento.png"), p_rend_hist, width = 7, height = 5, dpi = 150)

# Dispersion Area vs Rendimiento (ENTRENAMIENTO)
p_scatter <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  ggplot(aes(x = AREA_HA, y = RENDIMIENTO_T_HA)) +
  geom_point(alpha = 0.7, color = "#2c7fb8") +
  geom_smooth(method = "lm", se = TRUE, color = "#d95f0e") +
  labs(title = "Area vs Rendimiento (ENTRENAMIENTO)", x = "Area (ha)", y = "Rendimiento (t/ha)") +
  theme_minimal()
ggsave(file.path(FIG_DIR, "01_scatter_area_vs_rendimiento.png"), p_scatter, width = 7, height = 5, dpi = 150)

cor_area_rend <- id_area_rend |>
  filter(CONJUNTO == "ENTRENAMIENTO") |>
  summarise(cor_pearson = cor(AREA_HA, RENDIMIENTO_T_HA, use = "complete.obs")) |>
  pull(cor_pearson)
cat("Correlacion Pearson AREA_HA vs RENDIMIENTO_T_HA (ENTRENAMIENTO):", round(cor_area_rend, 3), "\n")

# ------------------------------------------------------------------------------
# 6. Deteccion de outliers evidentes (regla IQR 1.5x)
# ------------------------------------------------------------------------------
detectar_outliers_iqr <- function(x) {
  q1 <- quantile(x, 0.25, na.rm = TRUE)
  q3 <- quantile(x, 0.75, na.rm = TRUE)
  iqr <- q3 - q1
  which(x < (q1 - 1.5 * iqr) | x > (q3 + 1.5 * iqr))
}

idx_out_area <- detectar_outliers_iqr(id_area_rend$AREA_HA)
outliers_area <- id_area_rend[idx_out_area, c("ID_POLIGONO", "AREA_HA", "CONJUNTO")]
cat("\nOutliers en AREA_HA (regla IQR 1.5x):", nrow(outliers_area), "\n")
print(outliers_area)

rend_entren <- id_area_rend |> filter(CONJUNTO == "ENTRENAMIENTO")
idx_out_rend <- detectar_outliers_iqr(rend_entren$RENDIMIENTO_T_HA)
outliers_rend <- rend_entren[idx_out_rend, c("ID_POLIGONO", "RENDIMIENTO_T_HA")]
cat("Outliers en RENDIMIENTO_T_HA (ENTRENAMIENTO, regla IQR 1.5x):", nrow(outliers_rend), "\n")
print(outliers_rend)

# ------------------------------------------------------------------------------
# 7. Guardar datos derivados para uso en otros scripts
# ------------------------------------------------------------------------------
write_csv(id_area_rend, file.path(DER_DIR, "id_area_rendimiento_limpio.csv"))

cat("\n01_id_area_rendimiento.R completado.\n")
