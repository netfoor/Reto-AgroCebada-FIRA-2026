# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/28_registro_hipotesis_semana2.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
suppressPackageStartupMessages({ library(readr); library(dplyr) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
PREP <- file.path(RAIZ, "preparacion")
f <- file.path(PREP, "registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)

familias <- c("clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17")
hip <- bind_rows(lapply(familias, function(fam) {
  h <- read_csv(file.path(PREP, "variables", paste0(fam, "_hipotesis.csv")),
                col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)
  h$familia <- fam
  h
}))
nuevas <- hip[hip$existente == "no", ]
stopifnot(!anyDuplicated(nuevas$id), all(grepl("Signo:|sin signo", nuevas$hipotesis, ignore.case = TRUE)),
          !any(grepl("\n", nuevas$hipotesis)))
nuevas <- nuevas |> transmute(id, hipotesis, variables = gsub(";", "; ", gsub("; *", ";", variables)))

e2 <- tibble(
  id = "E2",
  hipotesis = paste(
    "(No es una hipotesis; registro del diseno de la Semana 2, anotado ANTES de evaluar.)",
    "Las variables se construyeron sin usar el rendimiento, en 5 familias (scripts 51 a 55, carpeta preparacion/variables/): 148 columnas candidatas, 2 de ellas de control de calidad (satc_nobs_*).",
    "Regla de prueba: cada variable se prueba sola contra B2 con el modelo rendimiento ~ grupo + variable (pendiente comun); las columnas se estandarizan con las 197 parcelas, sin rendimiento. Una hipotesis con varias variables se reporta como 'k de n pasan E1', nunca como 'alguna pasa'. Si a una parcela de validacion le falta la variable se predice con B2 (no se imputa).",
    "Controles: (a) permutacion (el rendimiento se baraja dentro de cada grupo, 100 veces) para estimar cuantas variables pasan E1 solo por azar; (b) seleccion dentro de cada particion (la mejor variable segun el ajuste, y las 3 mejores) para estimar lo que entrega elegir variables.",
    "Operacionalizacion fijada antes de ver resultados: HC2 no es evaluable (el indicador Tmedia jul-ago entre 15 y 20 C vale 1 en las 197 parcelas, Tmedia de 17.16 a 18.66 C [CP]) y su variable coincide con la de HC1, asi que no cuenta como prueba independiente. HA6 se evalua solo con precip jun y jul; ago y sep se prueban en HW7 (exploratoria). Las columnas satc_meses_validos_* eran constantes (7 de 7 meses) y se reemplazaron por satc_nobs_*_ciclo (HS7). HR10 usa la diferencia en mm (anom_precip_mm_jun_ago). Los nombres de columna difieren de los del texto registrado (por ejemplo ndvi_max_ciclo_s2 es satc_ndvi_max_ciclo_s2); el mapeo esta en preparacion/variables/*_hipotesis.csv.",
    "Quedan fuera de esta tanda: HA1, HA2, HB7 (fenologia de Planet), HB5, HB6, HC3, HD1 a HD3 (topografia), HR4, HR5, HR7, HR8.",
    sep = " "),
  variables = "148 columnas de preparacion/variables/*_features.csv")

todas <- bind_rows(nuevas, e2)
todas <- todas[!todas$id %in% reg$id, ]
if (nrow(todas) == 0) {
  cat("Todo ya estaba registrado; no se modifica nada.\n")
} else {
  todas$fecha     <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  todas$esquema   <- "V1 (principal) y V2; se evalua sobre B2 dentro de la CV"
  todas$semillas  <- "V1: 1-100; V2: 1001-1100"
  todas$resultado <- ""
  todas$decision  <- ""
  todas$esquema[todas$id == "E2"]  <- "todos"
  todas$semillas[todas$id == "E2"] <- "permutaciones: 2026"
  todas <- todas[, names(reg)]
  write_csv(bind_rows(reg, todas), f)
  cat("Registradas", nrow(todas), "filas nuevas (", sum(todas$id != "E2"), "hipotesis y E2 ), fecha:", todas$fecha[1], "\n")
}
