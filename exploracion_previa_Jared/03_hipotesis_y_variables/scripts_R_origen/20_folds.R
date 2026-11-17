# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 02_validacion_y_lineas_base/scripts/20_folds.R). Original: preparacion/scripts/20_folds.R.
# ==============================================================================
# 20_folds.R  --  Fase 1.3: tabla base y esquemas de validación V1, V2 y V3
# Reto AgroCebada FIRA 2026
#
# Qué hace:
#   1. Arma datos/base_138.csv (parcelas de entrenamiento con grupo, celda climática
#      y rendimiento) y datos/base_197_ubicacion.csv (las 197, sin rendimiento).
#   2. Define 5 grupos de trabajo (municipio agrupado) y CORROBORA sus conteos.
#   3. Genera los folds:
#        V1  espejo del reto: 100 divisiones 70/30 estratificadas por grupo, aleatorias
#            dentro de cada grupo (semillas 1..100).           -> datos/folds_V1.csv
#        V2  por celda climática: 100 divisiones que apartan celdas completas
#            (semillas 1001..1100, con reintentos deterministas). -> datos/folds_V2.csv
#        V3  dejar un grupo fuera: 5 folds sin azar.             -> datos/folds_V3.csv
#   4. Mide qué % de la validación comparte celda con el ajuste en cada esquema y lo
#      compara con lo que pasa realmente con las 59 parcelas ocultas.
#
# Cómo correr:  Rscript 02_validacion_y_lineas_base/scripts/20_folds.R   (después de 10_limpieza.R)
# Los datos originales (01_datos/originales/, 01_datos/derivados/) solo se leen.
# ==============================================================================
suppressPackageStartupMessages({
  library(sf)
  library(terra)
  library(readr)
  library(dplyr)
  library(tidyr)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
DATA <- file.path(RAIZ, "01_datos/originales")
DERI <- file.path(RAIZ, "01_datos/derivados")
PREP <- RAIZ
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)

log_con <- file(file.path(PREP, "04_resultados/logs/20_folds.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 20_folds.R ==\n")
cat("R:", R.version.string, "\n")
cat("Paquetes: sf", as.character(packageVersion("sf")), "| terra", as.character(packageVersion("terra")),
    "| dplyr", as.character(packageVersion("dplyr")), "| readr", as.character(packageVersion("readr")), "\n")
cat("RNGkind:", paste(RNGkind(), collapse = " / "), "\n\n")

# ------------------------------------------------------------------------------
# 1. Parcelas limpias + rendimiento
# ------------------------------------------------------------------------------
p <- st_read(file.path(PREP, "01_datos/preparados/parcelas_limpias.gpkg"), quiet = TRUE)
stopifnot(nrow(p) == 197)

# El CSV trae una 5ª columna vacía por una coma sobrante al final de cada línea: se descarta.
rend <- read_csv(file.path(DATA, "ID_area_rendimiento_70_30_Reto_AgroCebada.csv"),
                 col_select = c(ID_POLIGONO, AREA_HA, RENDIMIENTO_T_HA, CONJUNTO),
                 show_col_types = FALSE, progress = FALSE)
stopifnot(nrow(rend) == 197, !anyDuplicated(rend$ID_POLIGONO))

atr <- p |> st_drop_geometry() |> select(ID_POLIGONO, Estado, Municipio, CONJUNTO_shp = CONJUNTO)
x <- atr |> left_join(rend, by = "ID_POLIGONO")
stopifnot(!any(is.na(x$CONJUNTO)), all(x$CONJUNTO == x$CONJUNTO_shp))   # shapefile y CSV coinciden
cat("CONJUNTO (shapefile = CSV):\n"); print(table(x$CONJUNTO))

# ------------------------------------------------------------------------------
# 2. Grupos de trabajo (municipio agrupado) y corroboración de conteos
# ------------------------------------------------------------------------------
# Regla: Chignahuapan (todo Puebla); Tlaxcala entero (Nanacamilpa, 1 parcela, va con
# Calpulalpan); en Hidalgo, Singuilucan y Almoloya por separado y el resto en "Otros_Hidalgo"
# (Cuautepec de Hinojosa, Emiliano Zapata, Apan, Tepeapulco).
x <- x |>
  mutate(grupo = case_when(
    Municipio == "Chignahuapan" ~ "Chignahuapan",
    Estado == "Tlaxcala"        ~ "Tlaxcala",
    Municipio == "Singuilucan"  ~ "Singuilucan",
    Municipio == "Almoloya"     ~ "Almoloya",
    Estado == "Hidalgo"         ~ "Otros_Hidalgo",
    TRUE                        ~ NA_character_))
stopifnot(!any(is.na(x$grupo)))
GRUPOS <- c("Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo")

esperado <- c(Chignahuapan = 71, Tlaxcala = 31, Singuilucan = 16, Almoloya = 10, Otros_Hidalgo = 10)
obs <- table(x$grupo[x$CONJUNTO == "ENTRENAMIENTO"])[GRUPOS]
cat("\nConteos de grupos en ENTRENAMIENTO (observado vs esperado por el plan):\n")
print(rbind(observado = obs, esperado = esperado))
stopifnot(all(as.integer(obs) == as.integer(esperado)))
cat("Conteos de grupos en PREDICCION (ocultas):\n"); print(table(x$grupo[x$CONJUNTO == "PREDICCION"])[GRUPOS])
cat("Municipios dentro de Otros_Hidalgo (entrenamiento):\n")
print(table(x$Municipio[x$grupo == "Otros_Hidalgo" & x$CONJUNTO == "ENTRENAMIENTO"]))

# ------------------------------------------------------------------------------
# 3. Celda climática real (raster de precipitación, ~5.5 km), por centroide
# ------------------------------------------------------------------------------
r_file <- list.files(file.path(DATA, "precipitacion"), pattern = "PREC_2025_01\\.tif$",
                     recursive = TRUE, full.names = TRUE)
stopifnot(length(r_file) == 1)
r <- rast(r_file)                                   # solo lectura
cat("\nRaster de referencia:", basename(r_file), "| resolución:", paste(round(res(r), 4), collapse = " x "),
    "grados | CRS:", crs(r, describe = TRUE)$code, "\n")
cat("CRS parcelas (EPSG):", st_crs(p)$epsg, "
")
stopifnot(isTRUE(st_crs(p)$epsg == 4326))   # las parcelas están en WGS84, igual que el raster

cent <- suppressWarnings(st_centroid(st_geometry(p)))
xy <- st_coordinates(cent)[, 1:2]
x$celda_clima <- terra::cellFromXY(r, xy)          # id de celda del raster
stopifnot(!any(is.na(x$celda_clima)))

# ¿Cuántas parcelas tocan más de una celda? (el centroide asigna una sola)
tocan <- terra::extract(r, terra::vect(p), cells = TRUE)
n_celdas_por_parcela <- tapply(tocan$cell, tocan$ID, function(v) length(unique(v)))
cat("Parcelas que tocan más de una celda del raster:", sum(n_celdas_por_parcela > 1), "de", length(n_celdas_por_parcela), "\n")
cat("Celdas climáticas distintas (197 parcelas):", n_distinct(x$celda_clima), "\n")

# Comparación con la aproximación usada antes (valores climáticos idénticos en derivados/)
pr <- read_csv(file.path(DERI, "precipitacion_acumulada_ciclo_2025_por_parcela.csv"), show_col_types = FALSE)
tm <- read_csv(file.path(DERI, "temperatura_media_ciclo_2025_por_parcela.csv"), show_col_types = FALSE)
prox <- x |> select(ID_POLIGONO, celda_clima) |>
  left_join(pr, by = "ID_POLIGONO") |> left_join(tm, by = "ID_POLIGONO") |>
  mutate(celda_proxy = paste(round(precip_acumulada_ciclo, 2), round(tmin_medio_ciclo, 3), round(tmax_medio_ciclo, 3)))
x$celda_proxy <- prox$celda_proxy[match(x$ID_POLIGONO, prox$ID_POLIGONO)]
n_real <- n_distinct(x$celda_clima); n_prox <- n_distinct(x$celda_proxy)
n_par  <- n_distinct(paste(x$celda_clima, x$celda_proxy))
cat("Celdas reales:", n_real, "| celdas por aproximación:", n_prox, "| pares distintos (real, aprox.):", n_par, "\n")
# Parcelas 'discrepantes': aquellas cuyo grupo de celda difiere entre las dos definiciones
disc <- x |> group_by(celda_clima) |> mutate(n_prox_en_real = n_distinct(celda_proxy)) |> ungroup() |>
  group_by(celda_proxy) |> mutate(n_real_en_prox = n_distinct(celda_clima)) |> ungroup()
n_disc <- sum(disc$n_prox_en_real > 1 | disc$n_real_en_prox > 1)
cat("Parcelas que discrepan entre celda real y aproximación:", n_disc, "de 197\n")

# Base 197 (ubicación, sin rendimiento) y base 138 (con rendimiento)
base_197 <- x |> select(ID_POLIGONO, CONJUNTO, Estado, Municipio, grupo, celda_clima, celda_proxy)
write_csv(base_197, file.path(PREP, "01_datos/preparados/base_197_ubicacion.csv"))

base <- x |> filter(CONJUNTO == "ENTRENAMIENTO") |>
  select(ID_POLIGONO, Estado, Municipio, grupo, celda_clima, RENDIMIENTO_T_HA) |>
  arrange(ID_POLIGONO)
stopifnot(nrow(base) == 138, !any(is.na(base$RENDIMIENTO_T_HA)))
write_csv(base, file.path(PREP, "01_datos/preparados/base_138.csv"))
cat("\nbase_138.csv:", nrow(base), "filas | sin NA en rendimiento: OK\n")

# ¿Qué % de las 59 ocultas comparte celda con alguna parcela de entrenamiento?
celdas_tr <- unique(base$celda_clima)
ocultas <- x |> filter(CONJUNTO == "PREDICCION")
comp_real <- sum(ocultas$celda_clima %in% celdas_tr)
comp_prox <- sum(ocultas$celda_proxy %in% unique(x$celda_proxy[x$CONJUNTO == "ENTRENAMIENTO"]))
cat("Ocultas con vecino de celda en entrenamiento -> celda REAL:", comp_real, "de", nrow(ocultas),
    sprintf("(%.1f%%)", 100 * comp_real / nrow(ocultas)),
    "| aproximación:", comp_prox, sprintf("(%.1f%%)", 100 * comp_prox / nrow(ocultas)), "\n")

# Celdas del entrenamiento: tamaño y grupos que contiene cada una
tab_celdas <- base |> group_by(celda_clima) |>
  summarise(n = n(), grupos = paste(sort(unique(grupo)), collapse = " + "), .groups = "drop")
cat("\nCeldas distintas en ENTRENAMIENTO:", nrow(tab_celdas), "| celdas que mezclan más de un grupo:",
    sum(grepl("+", tab_celdas$grupos, fixed = TRUE)), "\n")
cat("Celda más grande:", max(tab_celdas$n), "parcelas (", tab_celdas$grupos[which.max(tab_celdas$n)], ")\n")
cat("Tamaños de celda (parcelas de entrenamiento), de mayor a menor:",
    paste(sort(tab_celdas$n, decreasing = TRUE), collapse = " "), "\n")

# ------------------------------------------------------------------------------
# 4. V1: espejo del reto (70/30 estratificado por grupo, aleatorio dentro)
# ------------------------------------------------------------------------------
PROP_VAL <- 0.30
N_REP <- 100
ids_por_grupo <- split(base$ID_POLIGONO, base$grupo)
ids_por_grupo <- lapply(ids_por_grupo, sort)          # orden fijo antes de sortear
n_val_grupo <- sapply(ids_por_grupo, function(v) round(PROP_VAL * length(v)))
cat("\n-- V1 -- validación por grupo (round(0.30 * n)):\n"); print(n_val_grupo[GRUPOS])

hacer_v1 <- function(rep) {
  set.seed(rep)                                       # semillas 1..100
  val <- unlist(lapply(GRUPOS, function(g) sample(ids_por_grupo[[g]], n_val_grupo[[g]])))
  tibble(rep = rep, ID_POLIGONO = base$ID_POLIGONO,
         rol = ifelse(base$ID_POLIGONO %in% val, "validacion", "ajuste"))
}
folds_V1 <- bind_rows(lapply(1:N_REP, hacer_v1))
write_csv(folds_V1, file.path(PREP, "01_datos/preparados/folds_V1.csv"))

# ------------------------------------------------------------------------------
# 5. V2: por celda climática (se apartan celdas completas)
# ------------------------------------------------------------------------------
# Algoritmo (por repetición, con semilla base 1000 + rep):
#   1. Se barajan las celdas del entrenamiento.
#   2. Se recorren en ese orden. Una celda pasa a validación solo si, con ella:
#        (a) la validación no supera 48 parcelas (35% de 138), y
#        (b) ningún grupo queda con más del 50% de sus parcelas en validación
#            (o sea, cada grupo conserva al menos la mitad en el ajuste), y
#        (c) todavía no se llegó a la meta de 41 parcelas (30% de 138).
#   3. La repetición es válida si la validación queda entre 35 y 48 parcelas (25%–35%).
#   4. Si no, se REINTENTA con semilla = semilla base + 1000 * intento (intento = 1, 2, ...),
#      hasta 50 intentos. Es determinista: el mismo script da siempre los mismos folds.
V2_MIN <- 35; V2_MAX <- 48; V2_META <- round(PROP_VAL * nrow(base)); MAX_INT <- 50
celdas <- sort(unique(base$celda_clima))
n_grupo_total <- table(base$grupo)[GRUPOS]

hacer_v2 <- function(rep) {
  for (intento in 0:MAX_INT) {
    set.seed(1000 + rep + 1000 * intento)             # semillas base 1001..1100
    orden <- sample(celdas)
    val <- character(0)
    for (cel in orden) {
      if (length(val) >= V2_META) break
      ids_cel <- base$ID_POLIGONO[base$celda_clima == cel]
      cand <- c(val, ids_cel)
      if (length(cand) > V2_MAX) next
      en_val_g <- table(factor(base$grupo[base$ID_POLIGONO %in% cand], levels = GRUPOS))
      if (any(en_val_g > 0.5 * n_grupo_total)) next
      val <- cand
    }
    if (length(val) >= V2_MIN && length(val) <= V2_MAX)
      return(list(val = val, intentos = intento))
  }
  stop("V2: no se logró una partición válida en la repetición ", rep)
}
res_v2 <- lapply(1:N_REP, hacer_v2)
# (dentro de tibble() el nombre `rep` ya es una columna; por eso se usa `k` para indexar)
folds_V2 <- bind_rows(lapply(1:N_REP, function(k) {
  val_k <- res_v2[[k]]$val
  tibble(rep = k, ID_POLIGONO = base$ID_POLIGONO,
         rol = ifelse(base$ID_POLIGONO %in% val_k, "validacion", "ajuste"))
}))
write_csv(folds_V2, file.path(PREP, "01_datos/preparados/folds_V2.csv"))
intentos <- sapply(res_v2, `[[`, "intentos")
cat("\n-- V2 -- reintentos por repetición: ", sum(intentos == 0), "repeticiones válidas al primer intento;",
    "máximo de reintentos usados:", max(intentos), "\n")
# Celdas "gigantes" (>= 30 parcelas de entrenamiento): con qué frecuencia las aparta V2
gigantes <- tab_celdas[tab_celdas$n >= 30, ]
for (i in seq_len(nrow(gigantes))) {
  ids_g <- base$ID_POLIGONO[base$celda_clima == gigantes$celda_clima[i]]
  n_apartada <- sum(sapply(res_v2, function(z) all(ids_g %in% z$val)))
  cat("Celda gigante", i, "(", length(ids_g), "parcelas;", gigantes$grupos[i], ") apartada en",
      n_apartada, "de", N_REP, "repeticiones
")
}

# ------------------------------------------------------------------------------
# 6. V3: dejar un grupo fuera (sin azar)
# ------------------------------------------------------------------------------
folds_V3 <- bind_rows(lapply(seq_along(GRUPOS), function(i)
  tibble(rep = i, grupo_fuera = GRUPOS[i], ID_POLIGONO = base$ID_POLIGONO,
         rol = ifelse(base$grupo == GRUPOS[i], "validacion", "ajuste"))))
write_csv(folds_V3, file.path(PREP, "01_datos/preparados/folds_V3.csv"))

# ------------------------------------------------------------------------------
# 7. Verificaciones
# ------------------------------------------------------------------------------
verifica <- function(folds, nombre, exigir_todos_los_grupos) {
  for (k in unique(folds$rep)) {
    f <- folds[folds$rep == k, ]
    aj <- f$ID_POLIGONO[f$rol == "ajuste"]; va <- f$ID_POLIGONO[f$rol == "validacion"]
    stopifnot(length(intersect(aj, va)) == 0,                     # ningún ID en ambos
              length(aj) + length(va) == 138,                     # todos los IDs asignados
              length(va) > 0)
    if (exigir_todos_los_grupos)
      stopifnot(all(GRUPOS %in% base$grupo[base$ID_POLIGONO %in% aj]))  # todos los grupos en el ajuste
  }
  cat(nombre, ": OK (sin traslape ajuste/validación; 138 IDs por repetición",
      if (exigir_todos_los_grupos) "; todos los grupos presentes en el ajuste)" else ")", "\n")
}
cat("\n== Verificaciones ==\n")
verifica(folds_V1, "V1", TRUE)
verifica(folds_V2, "V2", TRUE)
verifica(folds_V3, "V3", FALSE)
stopifnot(length(unique(table(folds_V1$rol[folds_V1$rep == 1]))) == 2,
          all(tapply(folds_V1$rol == "validacion", folds_V1$rep, sum) == sum(n_val_grupo)))
cat("V1: tamaño de validación constante =", sum(n_val_grupo), "\n")
cat("Sin NA en rendimiento de las 138: OK\n")

# ------------------------------------------------------------------------------
# 8. Resumen por esquema (tamaño y % de validación con vecino de celda en el ajuste)
# ------------------------------------------------------------------------------
celda_de <- setNames(base$celda_clima, base$ID_POLIGONO)
grupo_de <- setNames(base$grupo, base$ID_POLIGONO)
resume <- function(folds, nombre) {
  por_rep <- lapply(split(folds, folds$rep), function(f) {
    aj <- f$ID_POLIGONO[f$rol == "ajuste"]; va <- f$ID_POLIGONO[f$rol == "validacion"]
    tibble(n_val = length(va), pct_val = 100 * length(va) / 138,
           pct_vecino = 100 * mean(celda_de[va] %in% celda_de[aj]))
  }) |> bind_rows()
  tibble(esquema = nombre, n_reps = nrow(por_rep),
         n_val_min = min(por_rep$n_val), n_val_media = mean(por_rep$n_val), n_val_max = max(por_rep$n_val),
         pct_vecino_media = mean(por_rep$pct_vecino), pct_vecino_min = min(por_rep$pct_vecino),
         pct_vecino_max = max(por_rep$pct_vecino))
}
resumen <- bind_rows(resume(folds_V1, "V1 espejo (aleatorio dentro del grupo)"),
                     resume(folds_V2, "V2 por celda climática"),
                     resume(folds_V3, "V3 dejar un grupo fuera")) |>
  bind_rows(tibble(esquema = "REAL: 59 ocultas vs 138 (celda real)", n_reps = 1,
                   n_val_min = nrow(ocultas), n_val_media = nrow(ocultas), n_val_max = nrow(ocultas),
                   pct_vecino_media = 100 * comp_real / nrow(ocultas),
                   pct_vecino_min = 100 * comp_real / nrow(ocultas), pct_vecino_max = 100 * comp_real / nrow(ocultas)),
            tibble(esquema = "REAL: 59 ocultas vs 138 (aproximación por valores)", n_reps = 1,
                   n_val_min = nrow(ocultas), n_val_media = nrow(ocultas), n_val_max = nrow(ocultas),
                   pct_vecino_media = 100 * comp_prox / nrow(ocultas),
                   pct_vecino_min = 100 * comp_prox / nrow(ocultas), pct_vecino_max = 100 * comp_prox / nrow(ocultas)))
resumen <- resumen |> mutate(across(where(is.numeric), ~ round(.x, 2)))
write_csv(resumen, file.path(PREP, "04_resultados/resumen_esquemas.csv"))
cat("\n== Resumen por esquema ==\n"); print(as.data.frame(resumen), row.names = FALSE)

# Cobertura de grupos en la validación de V2 (para saber cuánto pesa cada región)
cob_v2 <- folds_V2 |> filter(rol == "validacion") |> mutate(grupo = grupo_de[ID_POLIGONO]) |>
  count(rep, grupo) |> complete(rep = 1:N_REP, grupo = GRUPOS, fill = list(n = 0)) |>
  group_by(grupo) |> summarise(reps_con_parcelas_en_validacion = sum(n > 0),
                                media_parcelas_en_validacion = round(mean(n), 1), .groups = "drop")
cat("\nV2: presencia de cada grupo en la validación:\n"); print(as.data.frame(cob_v2), row.names = FALSE)

cat("\nHecho. Sin errores.\n")
