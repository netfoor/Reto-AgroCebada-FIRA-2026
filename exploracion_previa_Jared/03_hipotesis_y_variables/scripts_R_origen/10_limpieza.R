# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 02_validacion_y_lineas_base/scripts/10_limpieza.R). Original: preparacion/scripts/10_limpieza.R.
# ==============================================================================
# 10_limpieza.R  --  Fase 1.2: limpieza (Reto AgroCebada FIRA 2026)
#
# Qué hace:
#   1. Lee el shapefile ORIGINAL (solo lectura), normaliza `Cultivo` a mayúsculas,
#      renombra ID_POLIGON -> ID_POLIGONO y repara geometrías con st_make_valid().
#   2. Compara el área recalculada de AGC_070 y AGC_078 antes y después de reparar.
#   3. Guarda 01_datos/preparados/parcelas_limpias.gpkg (archivo NUEVO).
#   4. Cuenta valores negativos de lai_promedio en Básico y PRO (solo se documenta;
#      no se modifica ninguna columna ni se crea un LAI recortado todavía).
#
# Reglas: los datos originales de 01_datos/originales/ no se tocan; todo lo nuevo va en las carpetas numeradas.
# Cómo correr:  Rscript 02_validacion_y_lineas_base/scripts/10_limpieza.R
# ==============================================================================
suppressPackageStartupMessages({
  library(sf)
  library(readr)
  library(dplyr)
})

RAIZ    <- "."   # carpeta "para el equipo": correr siempre desde ahi
DATA    <- file.path(RAIZ, "01_datos/originales")
PREP    <- RAIZ
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(PREP, "01_datos/preparados"), recursive = TRUE, showWarnings = FALSE)

# Todo lo que se imprime también queda en un log
log_con <- file(file.path(PREP, "04_resultados/logs/10_limpieza.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 10_limpieza.R ==\n")
cat("R:", R.version.string, "| sf:", as.character(packageVersion("sf")), "\n")
cat("RNGkind:", paste(RNGkind(), collapse = " / "), " (este script no usa azar)\n\n")

# ------------------------------------------------------------------------------
# 1. Leer shapefile original (solo lectura)
# ------------------------------------------------------------------------------
shp <- file.path(DATA, "parcelas/Parcelas_Reto_AGC_CONJUNTO.shp")
stopifnot(file.exists(shp))
p0 <- st_read(shp, quiet = TRUE)
cat("Filas leídas:", nrow(p0), "| columnas:", paste(names(p0), collapse = ", "), "\n")

# El campo de área tiene nombre con acento (área_ha); se renombra por posición del patrón
col_area <- grep("rea_ha", names(p0), value = TRUE)
stopifnot(length(col_area) == 1)
names(p0)[names(p0) == col_area] <- "AREA_HA_SHP"
names(p0)[names(p0) == "ID_POLIGON"] <- "ID_POLIGONO"

cat("\nCultivo ANTES de normalizar:\n"); print(table(p0$Cultivo))
p0$Cultivo <- toupper(p0$Cultivo)
cat("Cultivo DESPUÉS de normalizar:\n"); print(table(p0$Cultivo))
stopifnot(length(unique(p0$Cultivo)) == 1)

stopifnot(nrow(p0) == 197, !anyDuplicated(p0$ID_POLIGONO))

# Las geometrías traen coordenada Z (POLYGON Z) siempre igual a 0, según el EDA.
# Se comprueba y se descarta: st_make_valid() trabaja en 2D y mezclar 2D con Z rompe
# la reasignación de geometrías (error "Length of input WKB is too small").
z <- st_coordinates(p0)
if ("Z" %in% colnames(z)) {
  cat("
Coordenada Z: mín =", min(z[, "Z"]), " máx =", max(z[, "Z"]), "-> se descarta con st_zm()
")
  stopifnot(all(z[, "Z"] == 0))
  p0 <- st_zm(p0, drop = TRUE, what = "ZM")
}

# ------------------------------------------------------------------------------
# 2. Geometrías: validar, reparar y comparar área antes/después
# ------------------------------------------------------------------------------
# Área en hectáreas sobre un CRS métrico (EPSG:6372, el mismo que usó el EDA)
area_ha <- function(x) as.numeric(st_area(st_transform(x, 6372))) / 10000

valida_antes <- st_is_valid(p0)
invalidas    <- p0$ID_POLIGONO[!valida_antes]
cat("\nGeometrías inválidas antes de reparar:", length(invalidas), "->",
    paste(invalidas, collapse = ", "), "\n")
stopifnot(setequal(invalidas, c("AGC_070", "AGC_078")))   # lo que documentó el EDA

area_antes <- area_ha(p0)

# Se repara SOLO lo inválido: en una prueba previa, aplicar st_make_valid() a las 197
# cambió ligeramente (hasta 0.0003 ha) polígonos que ya eran válidos (normaliza vértices),
# y no queremos alterar geometrías buenas.
p1 <- p0
g_rep <- st_geometry(p0)
g_rep[!valida_antes] <- st_make_valid(st_geometry(p0)[!valida_antes])   # st_make_valid(x, ...) de sf
st_geometry(p1) <- g_rep

valida_despues <- st_is_valid(p1)
cat("Válidas después de reparar:", sum(valida_despues), "de", nrow(p1), "\n")
stopifnot(all(valida_despues), nrow(p1) == 197)

area_despues <- area_ha(p1)
cmp <- tibble(
  ID_POLIGONO = p0$ID_POLIGONO,
  area_antes_ha = area_antes,
  area_despues_ha = area_despues,
  dif_ha = area_despues - area_antes,
  dif_pct = 100 * (area_despues - area_antes) / area_antes,
  tipo_antes = as.character(st_geometry_type(p0)),
  tipo_despues = as.character(st_geometry_type(p1))
)
cat("\nÁrea recalculada antes/después en las parcelas reparadas:\n")
print(as.data.frame(cmp %>% filter(ID_POLIGONO %in% invalidas)), digits = 8)
cat("\nMáxima diferencia absoluta de área en las 197 parcelas (ha):",
    format(max(abs(cmp$dif_ha)), digits = 3), "\n")
cat("Tipos de geometría después:\n"); print(table(cmp$tipo_despues))
# Solo las reparadas deben poder cambiar
stopifnot(all(abs(cmp$dif_ha[!p0$ID_POLIGONO %in% invalidas]) < 1e-9))

# ------------------------------------------------------------------------------
# 3. Guardar producto NUEVO (no se sobrescribe nada original)
# ------------------------------------------------------------------------------
out_gpkg <- file.path(PREP, "01_datos/preparados/parcelas_limpias.gpkg")
if (file.exists(out_gpkg)) file.remove(out_gpkg)
st_write(p1, out_gpkg, layer = "parcelas_limpias", quiet = TRUE)
chk <- st_read(out_gpkg, quiet = TRUE)
stopifnot(nrow(chk) == 197, all(st_is_valid(chk)))
cat("\nGuardado:", out_gpkg, "(", nrow(chk), "polígonos, todos válidos )\n")

# ------------------------------------------------------------------------------
# 4. LAI negativo: solo se cuenta y se documenta
# ------------------------------------------------------------------------------
cuenta_lai <- function(archivo, nombre) {
  d <- read_csv(file.path(DATA, archivo), col_select = c(ID_POLIGONO, lai_promedio),
                show_col_types = FALSE, progress = FALSE)
  validas <- d$lai_promedio[!is.na(d$lai_promedio)]
  tibble(
    dataset = nombre,
    n_filas = nrow(d),
    n_con_lai = length(validas),
    n_negativos = sum(validas < 0),
    pct_negativos_de_con_lai = round(100 * sum(validas < 0) / length(validas), 3),
    minimo = min(validas),
    n_parcelas_con_negativo = n_distinct(d$ID_POLIGONO[!is.na(d$lai_promedio) & d$lai_promedio < 0])
  )
}
lai <- bind_rows(
  cuenta_lai("Conjunto_datos_BASICO_AgroCebada2026.csv", "BASICO (Sentinel-2)"),
  cuenta_lai("Conjunto_datos_PRO_AgroCebada.csv", "PRO (Planet)")
)
cat("\nLAI negativo (solo conteo; los originales no se modifican):\n"); print(as.data.frame(lai))
write_csv(lai, file.path(PREP, "04_resultados/lai_negativo_conteo.csv"))

cat("\nRegla PROPUESTA para la Fase 2 (no aplicada aquí): crear columnas nuevas
  lai_recortado = max(lai_promedio, 0) y lai_negativo = (lai_promedio < 0),
  conservando siempre la columna original y separando por sensor.
  Pendiente de confirmar con los organizadores (¿el negativo es esperado?).\n")

cat("\nHecho. Sin errores.\n")
