# COPIA PARA "para el equipo": solo cambiaron las rutas (relativas a la carpeta "para el equipo", desde donde se corre:
# Rscript 03_hipotesis_y_variables/agronomia/40_chequeos_1B.R). Original: preparacion/scripts/40_chequeos_1B.R.
# Produce 04_resultados/1B_chequeos.csv, las cifras [CP] de la hoja E_teledeteccion_validacion.
suppressPackageStartupMessages({ library(readr); library(dplyr) })
RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
D <- file.path(RAIZ, "01_datos/originales")
out <- list()
add <- function(bloque, medida, valor, nota = "") {
  out[[length(out) + 1]] <<- data.frame(bloque = bloque, medida = medida, valor = round(as.numeric(valor), 4), nota = nota)
}

# Basico, Sentinel-2
b <- read_csv(file.path(D, "Conjunto_datos_BASICO_AgroCebada2026.csv"),
              col_select = c(sensor, ndvi_promedio, savi_promedio, lai_promedio), show_col_types = FALSE)
s2 <- filter(b, grepl("entinel", sensor, ignore.case = TRUE))
n_ok <- filter(s2, !is.na(ndvi_promedio))
add("a_ndvi", "S2 mediana NDVI", median(n_ok$ndvi_promedio))
add("a_ndvi", "S2 p99 NDVI", quantile(n_ok$ndvi_promedio, 0.99))
add("a_ndvi", "S2 % lecturas con NDVI > 0.8", 100 * mean(n_ok$ndvi_promedio > 0.8))
l <- filter(s2, !is.na(lai_promedio), !is.na(savi_promedio))
add("a_lai", "S2 lecturas con LAI y SAVI", nrow(l))
add("a_lai", "S2 % LAI negativo", 100 * mean(l$lai_promedio < 0))
add("a_lai", "S2 % SAVI < 0.1", 100 * mean(l$savi_promedio < 0.1))
add("a_lai", "S2 Spearman LAI vs SAVI", cor(l$lai_promedio, l$savi_promedio, method = "spearman"))
add("a_lai", "S2 lecturas con LAI > 3", sum(l$lai_promedio > 3))
m <- filter(l, savi_promedio < 0.69)
pred <- -log((0.69 - m$savi_promedio) / 0.59) / 0.91
d <- abs(pred - m$lai_promedio)
add("a_lai", "Forma Allen 2007: mediana |dif| con LAI", median(d), "candidata; no es la formula confirmada del proveedor")
add("a_lai", "Forma Allen 2007: % lecturas a menos de 0.02", 100 * mean(d < 0.02))
add("a_lai", "LAI minimo observado", min(m$lai_promedio))
add("a_lai", "Forma Allen 2007 evaluada en el SAVI de ese minimo", pred[which.min(m$lai_promedio)])

# PRO, Planet
p <- read_csv(file.path(D, "Conjunto_datos_PRO_AgroCebada.csv"),
              col_select = c(ndvi_promedio, lai_promedio), show_col_types = FALSE)
p <- filter(p, !is.na(ndvi_promedio), !is.na(lai_promedio))
add("a_ndvi", "PRO mediana NDVI", median(p$ndvi_promedio))
add("a_ndvi", "PRO % lecturas con NDVI > 0.8", 100 * mean(p$ndvi_promedio > 0.8))
add("a_lai", "PRO % lecturas con LAI > 3", 100 * mean(p$lai_promedio > 3))
add("a_lai", "PRO Spearman LAI vs NDVI", cor(p$lai_promedio, p$ndvi_promedio, method = "spearman"))

# Tamano de parcela y pixeles
ar <- read_csv(file.path(RAIZ, "01_datos/derivados/id_area_rendimiento_limpio.csv"), show_col_types = FALSE)$AREA_HA
add("c_res", "Area mediana de parcela (ha)", median(ar))
add("c_res", "Parcelas menores que una celda DEM 120 m (1.44 ha)", sum(ar < 1.44))
for (r in c(3, 10, 20, 30)) add("c_res", paste0("Pixeles por parcela mediana a ", r, " m"), median(ar * 10000 / r^2))

# Celdas y varianza dentro de grupo (138 de entrenamiento)
bs <- read_csv(file.path(RAIZ, "01_datos/preparados/base_138.csv"), show_col_types = FALSE)
add("b_val", "Celdas climaticas distintas en las 138", n_distinct(bs$celda_clima))
tc <- sort(table(bs$celda_clima), decreasing = TRUE)
add("b_val", "Parcelas en las dos celdas mas grandes", sum(tc[1:2]))
g <- bs |> group_by(grupo) |> summarise(n = n(), sd = sd(RENDIMIENTO_T_HA), ss = (n() - 1) * var(RENDIMIENTO_T_HA))
add("b_val", "Suma de cuadrados dentro de grupos", sum(g$ss))
add("b_val", "Suma de cuadrados total", (nrow(bs) - 1) * var(bs$RENDIMIENTO_T_HA))
add("b_val", "% de la variacion interna que esta en Chignahuapan", 100 * g$ss[g$grupo == "Chignahuapan"] / sum(g$ss))
add("b_val", "sd interna de Chignahuapan", g$sd[g$grupo == "Chignahuapan"])

res <- bind_rows(out)
write_csv(res, file.path(RAIZ, "04_resultados/1B_chequeos.csv"))
print(as.data.frame(res), row.names = FALSE)
