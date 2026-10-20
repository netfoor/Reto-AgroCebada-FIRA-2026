# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/29_registro_E3.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
suppressPackageStartupMessages({ library(readr); library(dplyr); library(tibble) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
f <- file.path(RAIZ, "preparacion/registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)

e3 <- tibble(
  id = "E3",
  hipotesis = paste(
    "(No es una hipotesis; nota de diseno anotada DESPUES de ver el primer control de permutacion y ANTES de correr el segundo.)",
    "Primer resultado con el control por grupo (se baraja el rendimiento dentro de cada grupo): 13 variables pasan E1 y por azar pasan en promedio 0.08 (maximo 5 en 100 repeticiones).",
    "Ese control tambien rompe el parecido de rendimiento entre parcelas vecinas de una misma celda climatica, y las variables de clima valen casi lo mismo dentro de una celda, asi que puede ser demasiado benigno.",
    "Se agrega un control estricto: las filas de variables se reparten entre celdas climaticas del mismo grupo (100 repeticiones, semilla 2027), de modo que el rendimiento conserva su parecido entre vecinos.",
    "Tambien se define, despues de ver los primeros resultados, la lectura de cada variable que pasa E1: confirmada (el signo coincide con el registrado), hallazgo exploratorio (sin signo registrado; no cuenta como confirmado ni refutado) o contradice el signo registrado.",
    "Limite conocido de antemano por la familia 2: las anomalias climaticas son casi etiquetas de celda (R2 con la celda mayor a 0.99), asi que sus resultados se interpretan con ese limite.",
    sep = " "),
  variables = "las 148 columnas de E2",
  esquema = "V1 (principal) y V2", semillas = "permutaciones: 2027", resultado = "", decision = "")
e3$fecha <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
e3 <- e3[, names(reg)]
if ("E3" %in% reg$id) {
  cat("E3 ya estaba registrada; no se modifica nada.\n")
} else {
  write_csv(bind_rows(reg, e3), f)
  cat("Registrada E3, fecha:", e3$fecha, "\n")
}
