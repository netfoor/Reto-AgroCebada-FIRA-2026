# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/61_registro_resultados_semana2.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
suppressPackageStartupMessages({ library(readr); library(dplyr) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
PREP <- file.path(RAIZ, "preparacion")
f <- file.path(PREP, "registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)
pr  <- read_csv(file.path(PREP, "resultados/60_pruebas_por_variable.csv"), show_col_types = FALSE, progress = FALSE)
pe  <- read_csv(file.path(PREP, "resultados/60_permutacion.csv"), show_col_types = FALSE, progress = FALSE)
se  <- read_csv(file.path(PREP, "resultados/60_seleccion_en_particion.csv"), show_col_types = FALSE, progress = FALSE)

sg <- function(x) sprintf("%+.4f", x)
b2v1 <- unique(pr$rmse_B2_v1[!is.na(pr$rmse_B2_v1)]); b2v2 <- unique(pr$rmse_B2_v2[!is.na(pr$rmse_B2_v2)])
LIM_ANOM <- " Limite: cada anomalia climatica es casi una etiqueta de celda (R2 con la celda mayor a 0.99), asi que el resultado puede reflejar donde esta la parcela y no el clima de 2025."

decide <- function(d) {
  n <- nrow(d); k <- sum(d$veredicto == "pasa E1"); kv <- sum(d$veredicto == "solo con vecinos (falla c)")
  mejor <- d[which.max(d$delta_v1), ]
  pasan <- d[d$veredicto %in% c("pasa E1", "solo con vecinos (falla c)"), ]
  res <- sprintf("%d prueba(s) contra B2 (RMSE medio V1 %.3f, V2 %.3f). Pasan E1: %d; solo fallan (c): %d; descartadas: %d.",
                 n, b2v1, b2v2, k, kv, n - k - kv)
  if (nrow(pasan) > 0) {
    res <- paste0(res, " Pasan: ", paste(sprintf("%s (delta V1 %s, mejora en %d de 100, delta V2 %s, signo observado %s)",
                  pasan$variable, sg(pasan$delta_v1), pasan$n_mejora_v1, sg(pasan$delta_v2),
                  ifelse(is.na(pasan$signo_observado), "curva", pasan$signo_observado)), collapse = "; "), ".")
  } else {
    res <- paste0(res, sprintf(" Mejor: %s con delta V1 %s (mejora en %d de 100) y delta V2 %s.",
                               mejor$variable, sg(mejor$delta_v1), mejor$n_mejora_v1, sg(mejor$delta_v2)))
  }
  lect <- unique(pasan$lectura)
  dec <- if (nrow(pasan) == 0) {
    sprintf("DESCARTADA: %s mejora a B2 segun la regla E1 (mejor delta V1 %s t/ha; el umbral es +0.0200).",
            if (n == 1) "la prueba no" else sprintf("ninguna de las %d pruebas", n), sg(mejor$delta_v1))
  } else if (k == 0 && kv > 0) {
    sprintf("DEPENDE DE VECINOS: %s mejora a B2 en V1 pero no en V2 (falla c); no se acepta y la hipotesis no tenia signo registrado que confirmar o refutar.",
            paste(pasan$variable, collapse = ", "))
  } else if (any(pasan$lectura == "contradice el signo registrado")) {
    sprintf("CONTRADICE EL SIGNO: %d de %d prueba(s) mejoran a B2 pero con signo opuesto al registrado (%s); no se acepta como confirmada.%s",
            nrow(pasan), n, paste(pasan$variable[pasan$lectura == "contradice el signo registrado"], collapse = ", "),
            if (any(grepl("^anom_", pasan$variable))) LIM_ANOM else "")
  } else if (all(pasan$lectura == "confirmada (signo coincide)")) {
    sprintf("CONFIRMADA SEGUN E1 (%d de %d prueba(s), signo coincide con el registrado). Es una asociacion dentro de region con n=138 y una sola temporada; no prueba causa.%s",
            nrow(pasan), n, if (any(grepl("^anom_", pasan$variable))) LIM_ANOM else "")
  } else {
    sprintf("HALLAZGO EXPLORATORIO: %d de %d prueba(s) pasan E1 pero la hipotesis no tenia signo registrado; no cuenta como confirmada ni refutada. Se reporta como candidata para la Semana 3.%s%s",
            nrow(pasan), n, if (any(grepl("^anom_", pasan$variable))) LIM_ANOM else "",
            if (any(pasan$veredicto == "solo con vecinos (falla c)")) " Alguna variable depende de vecinos (falla c)." else "")
  }
  c(resultado = res, decision = dec)
}

ids <- setdiff(unique(pr$hipotesis[pr$veredicto != "no evaluable"]), "")
for (id in ids) {
  i <- which(reg$id == id); stopifnot(length(i) == 1)
  o <- decide(pr[pr$hipotesis == id, ])
  if (id == "HS7") o["decision"] <- paste0(o["decision"], " Control de calidad: satc_nobs_planet_ciclo (numero de imagenes sin nubes) mejora a B2 en V2 pero no pasa E1; el numero de imagenes depende de la nubosidad de la zona, asi que es una etiqueta de lugar y no agronomia.")
  if (id %in% c("HB3", "HB4")) o["decision"] <- paste0(o["decision"], " El coeficiente cuadratico salio positivo (se esperaba negativo) y en V2 la curva extrapola mal (delta muy negativo).")
  reg$resultado[i] <- o[["resultado"]]; reg$decision[i] <- o[["decision"]]
}
i <- which(reg$id == "HC2")
reg$resultado[i] <- "No evaluable (ver E2)."
reg$decision[i] <- "NO EVALUABLE: el indicador Tmedia jul-ago entre 15 y 20 C vale 1 en las 197 parcelas (Tmedia de 17.16 a 18.66 C [CP]) y su variable coincide con la de HC1. No se probo."

# E2 y E3: resultado de los controles
np <- sum(pr$veredicto != "no evaluable")
pasan <- sum(pr$veredicto == "pasa E1"); solov <- sum(pr$veredicto == "solo con vecinos (falla c)")
pg <- pe[pe$nulo == "grupo", ]; pc <- pe[pe$nulo == "celda", ]
s <- function(e, p) se[se$esquema == e & se$procedimiento == p, ]
sel_txt <- sprintf("Elegir la mejor variable dentro de cada particion (todas las familias): V1 delta %s (mejora en %d de 100), V2 delta %s (%d de 100); con las 3 mejores V1 %s, V2 %s. Por familia en V1: %s.",
  sg(s("V1", "top1_global")$delta_medio), s("V1", "top1_global")$n_mejora, sg(s("V2", "top1_global")$delta_medio), s("V2", "top1_global")$n_mejora,
  sg(s("V1", "top3_global")$delta_medio), sg(s("V2", "top3_global")$delta_medio),
  paste(sprintf("%s %s", sub("top1_", "", se$procedimiento[se$esquema == "V1" & grepl("top1_", se$procedimiento) & se$procedimiento != "top1_global"]),
                sg(se$delta_medio[se$esquema == "V1" & grepl("top1_", se$procedimiento) & se$procedimiento != "top1_global"])), collapse = ", "))
reg$resultado[reg$id == "E2"] <- sprintf(
  "%d pruebas (148 variables lineales + 2 curvas; HC2 no evaluable). Pasan E1: %d; solo fallan (c): %d; descartadas: %d. Control por grupo (rendimiento barajado dentro de grupo): por azar pasan en promedio %.2f variables (alguna pasa en %d de 100 repeticiones, maximo %d); mejor delta V1 por azar maximo %.4f frente a %.4f real. %s Con el rendimiento barajado esa misma seleccion empeora a B2 (V1 %s, V2 %s).",
  np, pasan, solov, np - pasan - solov, mean(pg$pasan_ab), sum(pg$pasan_ab >= 1), max(pg$pasan_ab), max(pg$mejor_delta_v1),
  max(pr$delta_v1, na.rm = TRUE), sel_txt, sg(mean(pg$sel_top1_delta_v1)), sg(mean(pg$sel_top1_delta_v2)))
reg$decision[reg$id == "E2"] <- "Hay senal por encima del azar, concentrada en clima (sobre todo anomalias, que son casi etiquetas de celda) y en NDVI/SAVI de abril-mayo; las variables de vigor satelital de las hipotesis principales no aportan sobre B2. Todo con n=138, una temporada y 23 celdas climaticas distintas: se reporta como candidatas, no como causas. Detalle en resultados/60_*.csv."
reg$resultado[reg$id == "E3"] <- sprintf(
  "Control estricto (filas de variables repartidas entre celdas del mismo grupo, 100 repeticiones): por azar pasan en promedio %.2f variables (alguna pasa en %d de 100 repeticiones, maximo %d) frente a %d reales; mejor delta V1 por azar maximo %.4f frente a %.4f real. Elegir la mejor variable dentro de la particion con este control: V1 %s, V2 %s.",
  mean(pc$pasan_ab), sum(pc$pasan_ab >= 1), max(pc$pasan_ab), pasan + solov, max(pc$mejor_delta_v1), max(pr$delta_v1, na.rm = TRUE),
  sg(mean(pc$sel_top1_delta_v1)), sg(mean(pc$sel_top1_delta_v2)))
supera <- sum(pc$pasan_ab >= pasan + solov) == 0 && max(pc$mejor_delta_v1) < max(pr$delta_v1, na.rm = TRUE)
reg$decision[reg$id == "E3"] <- paste0(
  if (supera) sprintf("La senal real supera al azar con este control: ninguna de las 100 repeticiones llega a %d variables que pasen ni al mejor delta real, aunque el maximo por azar es %d variables, asi que la distancia no es holgada.", pasan + solov, max(pc$pasan_ab))
  else "La senal real NO se distingue con claridad del azar con este control estricto: alguna repeticion iguala lo observado.",
  " Advertencia: las variables que pasan no son senales independientes (muchas son casi la misma) y 23 celdas son pocas; un control mas duro (media por celda con encogimiento, B3) queda propuesto para la Semana 3.")
write_csv(reg, f)
cat("Resultados registrados para", length(ids) + 1, "hipotesis y para E2 y E3.\n")
