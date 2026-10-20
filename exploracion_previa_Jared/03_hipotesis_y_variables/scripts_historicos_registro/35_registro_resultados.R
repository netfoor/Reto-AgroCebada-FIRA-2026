# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/35_registro_resultados.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
# ==============================================================================
# 35_registro_resultados.R -- Regla 5: registra resultado y decisión de H1-H4
#
# Se corre DESPUÉS de 30_lineas_base.R. Lee los resultados ya calculados (para no
# copiar números a mano) y completa las columnas `resultado` y `decision` del registro.
# El texto original de cada hipótesis y su fecha NO se tocan. Agrega (una sola vez) la
# fila E0 con el diseño de los folds, marcada como registrada después de ejecutar.
# ==============================================================================
suppressPackageStartupMessages({ library(readr); library(dplyr) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
PREP <- file.path(RAIZ, "preparacion")
f <- file.path(PREP, "registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), show_col_types = FALSE)

res <- read_csv(file.path(PREP, "resultados/lineas_base_resumen.csv"), show_col_types = FALSE)
mej <- read_csv(file.path(PREP, "resultados/mejora_vs_B0.csv"), show_col_types = FALSE)
rg  <- read_csv(file.path(PREP, "resultados/rmse_por_grupo.csv"), show_col_types = FALSE)
esq <- read_csv(file.path(PREP, "resultados/resumen_esquemas.csv"), show_col_types = FALSE)

r  <- function(e, m, col = "rmse_media") res[[col]][res$esquema == e & res$modelo == m]
mj <- function(e, comp, col) mej[[col]][mej$esquema == e & mej$comparacion == comp]
gr <- function(e, m, g) rg$rmse_media[rg$esquema == e & rg$modelo == m & rg$grupo == g]
n2 <- function(x) sprintf("%.3f", x); p1 <- function(x) sprintf("%.1f", x)

h1_res <- sprintf("V1: RMSE B0 %s -> B1 %s (reduccion %s%%, rango 5-95%%: %s a %s). V2: B0 %s -> B1 %s (reduccion %s%%).",
  n2(r("V1","B0")), n2(r("V1","B1")), p1(mj("V1","B1_vs_B0_pct","media")), p1(mj("V1","B1_vs_B0_pct","p5")), p1(mj("V1","B1_vs_B0_pct","p95")),
  n2(r("V2","B0")), n2(r("V2","B1")), p1(mj("V2","B1_vs_B0_pct","media")))
h2_res <- sprintf("V1: B2 %s vs B1 %s (reduccion adicional %s%%, rango %s a %s). V2: B2 %s vs B1 %s (%s%%, rango %s a %s). Por grupo (V1, RMSE B1->B2): Singuilucan %s->%s, Almoloya %s->%s, Otros_Hidalgo %s->%s.",
  n2(r("V1","B2")), n2(r("V1","B1")), p1(mj("V1","B2_vs_B1_pct","media")), p1(mj("V1","B2_vs_B1_pct","p5")), p1(mj("V1","B2_vs_B1_pct","p95")),
  n2(r("V2","B2")), n2(r("V2","B1")), p1(mj("V2","B2_vs_B1_pct","media")), p1(mj("V2","B2_vs_B1_pct","p5")), p1(mj("V2","B2_vs_B1_pct","p95")),
  n2(gr("V1","B1","Singuilucan")), n2(gr("V1","B2","Singuilucan")), n2(gr("V1","B1","Almoloya")), n2(gr("V1","B2","Almoloya")),
  n2(gr("V1","B1","Otros_Hidalgo")), n2(gr("V1","B2","Otros_Hidalgo")))
h3_res <- sprintf("RMSE V1 vs V2: B0 %s vs %s; B1 %s vs %s; B2 %s vs %s. Rango 5-95%% de B1 en V1: %s-%s.",
  n2(r("V1","B0")), n2(r("V2","B0")), n2(r("V1","B1")), n2(r("V2","B1")), n2(r("V1","B2")), n2(r("V2","B2")),
  n2(r("V1","B1","rmse_p5")), n2(r("V1","B1","rmse_p95")))
h4_res <- sprintf("RMSE de B2 por grupo. V1: Chignahuapan %s, Tlaxcala %s, Singuilucan %s, Otros_Hidalgo %s, Almoloya %s. V2: Chignahuapan %s, Tlaxcala %s.",
  n2(gr("V1","B2","Chignahuapan")), n2(gr("V1","B2","Tlaxcala")), n2(gr("V1","B2","Singuilucan")), n2(gr("V1","B2","Otros_Hidalgo")),
  n2(gr("V1","B2","Almoloya")), n2(gr("V2","B2","Chignahuapan")), n2(gr("V2","B2","Tlaxcala")))

decision <- c(
  H1 = "CUMPLIDA, algo mejor de lo previsto: la reduccion (~30%) queda en el borde alto del rango 25-30% y el RMSE de B1 (0.588 en V1) quedo por debajo del 0.60-0.65 esperado. Conclusion: solo saber el Estado ya recorta cerca de un tercio del error.",
  H2 = "CUMPLIDA EN DIRECCION, NO EN MAGNITUD: B2 mejora a B1 en ~15% (mas que 'un poco'). En V1 mejora en casi todas las repeticiones (p5 > 0); en V2 hay repeticiones donde no mejora (p5 < 0). La mejora viene de separar Singuilucan y Almoloya; Otros_Hidalgo casi no cambia.",
  H3 = "CUMPLIDA PARA B1 Y B2 (diferencia de ~0.02-0.03 t/ha, pequena frente al rango 5-95% entre repeticiones), NO PARA B0 (0.08 de diferencia). Explicacion probable, no comprobada a fondo: al apartar celdas completas (a veces 34 parcelas de Chignahuapan) la media del ajuste se desplaza. No se hizo prueba formal.",
  H4 = "CUMPLIDA: el error de B2 es mayor en Chignahuapan que en Tlaxcala en V1 y V2. Nota: en Chignahuapan el error de B2 (0.55) es casi igual a su desviacion interna (0.58); ahi la region no explica nada mas y es donde las variables tendran mas trabajo (71 parcelas, 51% del entrenamiento)."
)
resultado <- c(H1 = h1_res, H2 = h2_res, H3 = h3_res, H4 = h4_res)
for (id in names(resultado)) {
  i <- which(reg$id == id); stopifnot(length(i) == 1)
  reg$resultado[i] <- resultado[[id]]; reg$decision[i] <- decision[[id]]
}

# Fila E0: diseño de folds (no es una hipótesis; se registra después de ejecutar 20_folds.R)
fecha_e0 <- if ("E0" %in% reg$id) reg$fecha[reg$id == "E0"] else format(Sys.time(), "%Y-%m-%d %H:%M:%S")
reg <- reg[reg$id != "E0", ]   # se reconstruye siempre, conservando su fecha original
{
  v <- function(k, col = "pct_vecino_media") esq[[col]][grepl(k, esq$esquema, fixed = TRUE)][1]
  reg <- bind_rows(reg, tibble(
    id = "E0", fecha = fecha_e0,
    hipotesis = "(No es una hipotesis; registro del diseno de folds, anotado DESPUES de ejecutar 20_folds.R.) Esquemas V1 (70/30 estratificado por grupo), V2 (celdas climaticas completas) y V3 (un grupo fuera).",
    variables = "grupo, celda_clima (centroide sobre raster CHIRPS 0.05 grados)", esquema = "V1, V2, V3",
    semillas = "V1: 1-100; V2: 1001-1100 (+1000 por reintento); V3: sin azar",
    resultado = sprintf("Parcelas de validacion con vecino de celda en el ajuste: V1 %s%% (rango %s-%s), V2 %s%%, V3 %s%%; REAL 59 ocultas: %s%% (celda real) / %s%% (aproximacion por valores). Las 197 parcelas caen en 25 celdas reales del raster (31 parcelas tocan mas de una celda; se asigna la del centroide).",
                        p1(v("V1")), p1(v("V1","pct_vecino_min")), p1(v("V1","pct_vecino_max")), p1(v("V2")), p1(v("V3")),
                        p1(v("celda real")), p1(v("aproximaci"))),
    decision = "V1 imita bien la relacion real entre ajuste y validacion (92% vs 97%); usar V1 como esquema principal y V2 como prueba de esfuerzo (aprobado por el usuario el 2026-09-20)."))
}
write_csv(reg, f)
cat("Registro actualizado:", nrow(reg), "filas\n")
print(as.data.frame(reg[, c("id", "resultado")]), right = FALSE)
