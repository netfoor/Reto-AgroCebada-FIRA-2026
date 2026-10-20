# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 01_datos/eda_inicial/scripts/04_comparacion_basico_pro.R). Original: outputs/scripts/04_comparacion_basico_pro.R.
# ==============================================================================
# EDA - 04. Comparacion Dataset Basico (Sentinel-2/Landsat) vs Dataset PRO (Planet)
# Reto AgroCebada 2026
# IMPORTANTE: ambos datasets NO deben fusionarse automaticamente (sensores
# distintos, resoluciones y procesamientos distintos). Este script solo
# compara cobertura y distribuciones para documentar las diferencias.
# Script independiente y ejecutable por si solo.
# ==============================================================================

library(tidyverse)

DATA_DIR <- "01_datos/originales"
FIG_DIR  <- "01_datos/eda_inicial/figuras"
EDA_DIR  <- "01_datos/eda_inicial/eda"
DER_DIR  <- "01_datos/derivados"

dir.create(FIG_DIR, showWarnings = FALSE, recursive = TRUE)
dir.create(EDA_DIR, showWarnings = FALSE, recursive = TRUE)

# ------------------------------------------------------------------------------
# 1. Carga de ambos datasets
# ------------------------------------------------------------------------------
basico <- read_csv(file.path(DATA_DIR, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
                    locale = locale(encoding = "UTF-8"), show_col_types = FALSE) |>
  mutate(fecha_captura = dmy(fecha_captura), dataset = "Basico")

pro <- read_csv(file.path(DATA_DIR, "Conjunto_datos_PRO_AgroCebada.csv"),
                locale = locale(encoding = "UTF-8"), show_col_types = FALSE) |>
  mutate(fecha_captura = dmy(fecha_captura), dataset = "PRO")

# ------------------------------------------------------------------------------
# 2. Cobertura temporal
# ------------------------------------------------------------------------------
cobertura <- tibble(
  dataset = c("Basico", "PRO"),
  n_filas = c(nrow(basico), nrow(pro)),
  n_parcelas = c(n_distinct(basico$ID_POLIGONO), n_distinct(pro$ID_POLIGONO)),
  fecha_min = c(as.character(min(basico$fecha_captura)), as.character(min(pro$fecha_captura))),
  fecha_max = c(as.character(max(basico$fecha_captura)), as.character(max(pro$fecha_captura))),
  n_fechas_distintas = c(n_distinct(basico$fecha_captura), n_distinct(pro$fecha_captura)),
  sensores = c(paste(sort(unique(basico$sensor)), collapse = "/"), paste(sort(unique(pro$sensor)), collapse = "/"))
)
cat("Cobertura temporal y de sensores:\n")
print(cobertura)
write_csv(cobertura, file.path(EDA_DIR, "04_cobertura_basico_vs_pro.csv"))

# ------------------------------------------------------------------------------
# 3. Numero de observaciones por parcela: comparacion
# ------------------------------------------------------------------------------
obs_basico <- basico |> count(ID_POLIGONO, name = "n_obs_basico")
obs_pro    <- pro    |> count(ID_POLIGONO, name = "n_obs_pro")
obs_comparado <- full_join(obs_basico, obs_pro, by = "ID_POLIGONO")

cat("\nResumen de observaciones por parcela - Basico:\n"); print(summary(obs_comparado$n_obs_basico))
cat("Resumen de observaciones por parcela - PRO:\n"); print(summary(obs_comparado$n_obs_pro))

obs_long <- obs_comparado |>
  pivot_longer(-ID_POLIGONO, names_to = "dataset", values_to = "n_obs") |>
  mutate(dataset = recode(dataset, n_obs_basico = "Basico", n_obs_pro = "PRO"))

p_obs_comparado <- ggplot(obs_long, aes(x = dataset, y = n_obs, fill = dataset)) +
  geom_boxplot() +
  labs(title = "Observaciones por parcela: Basico vs PRO", x = NULL, y = "N observaciones") +
  theme_minimal() + theme(legend.position = "none")
ggsave(file.path(FIG_DIR, "04_box_obs_basico_vs_pro.png"), p_obs_comparado, width = 6, height = 5, dpi = 150)

# ------------------------------------------------------------------------------
# 4. Comparacion de rango/comportamiento de indices con el mismo nombre
#    (NDVI, EVI, LAI aparecen en ambos datasets)
# ------------------------------------------------------------------------------
indices_comunes <- c("ndvi_promedio", "evi_promedio", "lai_promedio")

basico_comunes <- basico |> select(dataset, sensor, all_of(indices_comunes)) |>
  filter(sensor == "Sentinel-2") |>            # unico sensor Basico con estos indices
  mutate(fuente = "Basico (Sentinel-2)")
pro_comunes <- pro |> select(dataset, sensor, all_of(indices_comunes)) |>
  mutate(fuente = "PRO (Planet)")

comparacion_indices <- bind_rows(basico_comunes, pro_comunes) |>
  select(fuente, all_of(indices_comunes)) |>
  pivot_longer(-fuente, names_to = "indice", values_to = "valor") |>
  filter(!is.na(valor))

resumen_comparacion <- comparacion_indices |>
  group_by(fuente, indice) |>
  summarise(n = n(), min = min(valor), media = mean(valor), mediana = median(valor),
            max = max(valor), sd = sd(valor), .groups = "drop") |>
  arrange(indice, fuente)
cat("\nComparacion de rango/distribucion por indice comun (Basico Sentinel-2 vs PRO Planet):\n")
print(resumen_comparacion, n = Inf)
write_csv(resumen_comparacion, file.path(EDA_DIR, "04_resumen_indices_comunes_basico_vs_pro.csv"))

p_comparacion <- ggplot(comparacion_indices, aes(x = fuente, y = valor, fill = fuente)) +
  geom_boxplot() +
  facet_wrap(~indice, scales = "free_y") +
  labs(title = "Indices con el mismo nombre: Basico (Sentinel-2) vs PRO (Planet)",
       subtitle = "No deben fusionarse automaticamente: provienen de sensores distintos",
       x = NULL, y = "Valor del indice") +
  theme_minimal() + theme(legend.position = "none", axis.text.x = element_text(angle = 20, hjust = 1))
ggsave(file.path(FIG_DIR, "04_box_indices_comunes_basico_vs_pro.png"), p_comparacion, width = 9, height = 5, dpi = 150)

# Diferencia relativa de medias como resumen rapido
diferencia_medias <- resumen_comparacion |>
  select(fuente, indice, media) |>
  pivot_wider(names_from = fuente, values_from = media) |>
  rename(media_basico = `Basico (Sentinel-2)`, media_pro = `PRO (Planet)`) |>
  mutate(diferencia_relativa_pct = (media_pro - media_basico) / media_basico * 100)
cat("\nDiferencia relativa de medias PRO vs Basico (mismo nombre de indice):\n")
print(diferencia_medias)

# ------------------------------------------------------------------------------
# 5. Solapamiento temporal 2025 (unico periodo donde ambos datasets coexisten)
# ------------------------------------------------------------------------------
basico_2025 <- basico |> filter(year(fecha_captura) == 2025, sensor == "Sentinel-2")
pro_2025 <- pro
cat("\nObservaciones Sentinel-2 (Basico) en 2025:", nrow(basico_2025),
    "| Observaciones PRO (Planet) en 2025:", nrow(pro_2025), "\n")

comparacion_2025 <- bind_rows(
  basico_2025 |> select(all_of(indices_comunes)) |> mutate(fuente = "Basico S2 (2025)"),
  pro_2025 |> select(all_of(indices_comunes)) |> mutate(fuente = "PRO Planet (2025)")
) |>
  pivot_longer(-fuente, names_to = "indice", values_to = "valor") |>
  filter(!is.na(valor)) |>
  group_by(fuente, indice) |>
  summarise(n = n(), media = mean(valor), mediana = median(valor), sd = sd(valor), .groups = "drop")
cat("\nComparacion restringida a 2025 (periodo de solapamiento real):\n")
print(comparacion_2025, n = Inf)

cat("\n04_comparacion_basico_pro.R completado.\n")
