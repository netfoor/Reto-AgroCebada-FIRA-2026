# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/25_registro_hipotesis.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
# ==============================================================================
# 25_registro_hipotesis.R -- Regla 4: las hipótesis se escriben ANTES de probarlas
#
# Crea preparacion/registro_experimentos.csv con las hipótesis H1-H4 de la Fase 1
# (texto del plan, sección "Hipótesis"), con fecha-hora, y con `resultado` y
# `decision` vacíos. Se corre ANTES de 30_lineas_base.R. Si el registro ya existe,
# NO se sobrescribe (así la fecha original de cada hipótesis queda intacta).
# ==============================================================================
suppressPackageStartupMessages({ library(readr); library(tibble) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
f <- file.path(RAIZ, "preparacion/registro_experimentos.csv")
if (file.exists(f)) {
  cat("El registro ya existe; no se modifica:", f, "\n")
} else {
  ahora <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  reg <- tribble(
    ~id, ~hipotesis, ~variables, ~esquema, ~semillas,
    "H1", "B1 (solo Estado) baja el RMSE frente a B0 (media global) en ~25-30%: R2 del Estado en el EDA ~0.50 y sd del rendimiento 0.85 t/ha implican RMSE ~0.60-0.65 vs ~0.85-0.87.",
          "Estado", "V1 (principal) y V2", "V1: 1-100; V2: 1001-1100",
    "H2", "B2 (Estado + municipio agrupado) mejora un poco mas que B1, solo por separar Singuilucan (3.08 t/ha) de Almoloya y Otros Hidalgo (~4.5), que estan en el mismo Estado.",
          "grupo (5 grupos)", "V1 y V2", "V1: 1-100; V2: 1001-1100",
    "H3", "Para las lineas base, V1 y V2 daran casi lo mismo, porque solo usan la etiqueta del grupo y no el clima ni el satelite. La diferencia entre V1 y V2 aparecera en las Fases 2-3, con variables que dependen de la ubicacion.",
          "Estado, grupo", "V1 vs V2", "V1: 1-100; V2: 1001-1100",
    "H4", "El error de B2 sera mayor en Chignahuapan que en Tlaxcala, si la variacion interna es mayor donde hay mas manejos distintos (sd por Estado en el EDA: Puebla 0.58, Hidalgo 0.78, Tlaxcala 0.38; no es una prediccion firme).",
          "grupo", "V1 y V2", "V1: 1-100; V2: 1001-1100"
  )
  reg$fecha <- ahora
  reg$resultado <- ""
  reg$decision  <- ""
  reg <- reg[, c("id", "fecha", "hipotesis", "variables", "esquema", "semillas", "resultado", "decision")]
  write_csv(reg, f)
  cat("Registro creado con", nrow(reg), "hipotesis, fecha:", ahora, "\n")
}
