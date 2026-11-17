# COPIA PARA "para el equipo": solo cambiaron las rutas (ahora relativas a la carpeta "para el equipo",
# desde donde se corre: Rscript 03_hipotesis_y_variables/scripts/60_evaluacion_variables.R). Original: preparacion/scripts/60_evaluacion_variables.R.
# ==============================================================================
# 60_evaluacion_variables.R  --  Semana 2: evalua cada variable candidata contra B2
# Reto AgroCebada FIRA 2026
#
# Que hace (regla E1 y diseno E2 del registro de experimentos):
#   1. Junta las 148 variables de las 5 familias (03_hipotesis_y_variables/variables/*_features.csv)
#      y las hipotesis de 03_hipotesis_y_variables/variables/*_hipotesis.csv.
#   2. Para cada variable ajusta, dentro de cada particion V1 y V2, el modelo
#      rendimiento ~ grupo + variable (pendiente comun) SOLO con las parcelas de ajuste
#      y lo compara con B2 (rendimiento ~ grupo) en las mismas parcelas de validacion.
#      Diferencia pareada: delta = RMSE(B2) - RMSE(modelo); positivo = mejora.
#   3. Regla E1 por variable: (a) delta medio en V1 > 0.02 t/ha; (b) delta > 0 en al
#      menos 75 de las 100 particiones V1; (c) delta medio en V2 >= 0.
#      Falla (a) o (b): descartar. Falla solo (c): depende de vecinos.
#   4. Control de permutacion: se baraja el rendimiento dentro de cada grupo (100 veces)
#      y se cuenta cuantas variables pasan E1 por puro azar.
#   5. Seleccion DENTRO de cada particion: la mejor variable (o las 3 mejores) segun el
#      ajuste, global y por familia. Es lo que entrega elegir variables sin hacer trampa.
#   6. Control de permutacion estricto (agregado DESPUES de ver el primero, registrado como
#      E3): se intercambian las filas de variables entre celdas climaticas del mismo grupo
#      (100 veces), de modo que el rendimiento conserva su parecido entre parcelas vecinas.
#   7. Lectura de cada resultado: confirmada (pasa E1 y el signo coincide), hallazgo
#      exploratorio (pasa E1 sin signo registrado), contradice el signo, o descartada.
#
# Faltantes: ninguna variable tiene NA en las 138 parcelas; el script se detiene si aparece uno.
# Entradas : 01_datos/preparados/base_138.csv, folds_V1.csv, folds_V2.csv,
#            03_hipotesis_y_variables/variables/*_features.csv y *_hipotesis.csv,
#            04_resultados/lineas_base.csv (solo para comprobar B2)
# Salidas  : 04_resultados/60_pruebas_por_variable.csv, 60_resumen_hipotesis.csv,
#            60_permutacion.csv, 60_seleccion_en_particion.csv y el log
# Como correr:  Rscript 03_hipotesis_y_variables/scripts/60_evaluacion_variables.R
# Semilla fija de las permutaciones: 2026.
# ==============================================================================
suppressPackageStartupMessages({
  library(readr)
  library(dplyr)
  library(tidyr)
  library(tibble)
})

RAIZ <- "."   # carpeta "para el equipo": correr siempre desde ahi
PREP <- RAIZ
dir.create(file.path(PREP, "04_resultados/logs"), recursive = TRUE, showWarnings = FALSE)
log_con <- file(file.path(PREP, "04_resultados/logs/60_evaluacion_variables.log"), open = "wt", encoding = "UTF-8")
sink(log_con, split = TRUE)
on.exit({ sink(); close(log_con) }, add = TRUE)

cat("== 60_evaluacion_variables.R ==\n")
cat("R:", R.version.string, "| dplyr", as.character(packageVersion("dplyr")),
    "| readr", as.character(packageVersion("readr")), "\n")
cat("RNGkind:", paste(RNGkind(), collapse = " / "), "\n")

DELTA_MIN     <- 0.02
N_MEJORA_MIN  <- 75
N_PERM        <- 100
SEMILLA_PERM  <- 2026
GRUPOS        <- c("Chignahuapan", "Tlaxcala", "Singuilucan", "Almoloya", "Otros_Hidalgo")
NG            <- length(GRUPOS)
FAMILIAS      <- c("clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17")
NO_EVALUABLES <- c(HC2 = "el indicador Tmedia jul-ago 15-20 C vale 1 en las 197 parcelas; misma variable que HC1")

# ------------------------------------------------------------------------------
# 1. Datos
# ------------------------------------------------------------------------------
base <- read_csv(file.path(PREP, "01_datos/preparados/base_138.csv"), show_col_types = FALSE, progress = FALSE)
stopifnot(nrow(base) == 138, !anyNA(base$RENDIMIENTO_T_HA))
base$g <- as.integer(factor(base$grupo, levels = GRUPOS))
stopifnot("celda_clima" %in% names(base), !anyNA(base$celda_clima))
stopifnot(!anyNA(base$g))
y   <- base$RENDIMIENTO_T_HA
ids <- base$ID_POLIGONO
pos <- setNames(seq_along(ids), ids)

feats <- lapply(FAMILIAS, function(fam)
  read_csv(file.path(PREP, "03_hipotesis_y_variables/variables", paste0(fam, "_features.csv")), show_col_types = FALSE, progress = FALSE))
F197 <- Reduce(function(a, b) left_join(a, b, by = "ID_POLIGONO"), feats)
stopifnot(nrow(F197) == 197, !anyDuplicated(names(F197)))
fam_de <- setNames(rep(FAMILIAS, vapply(feats, ncol, 1L) - 1L),
                   unlist(lapply(feats, function(d) setdiff(names(d), "ID_POLIGONO"))))
cat("Variables candidatas:", length(fam_de), "| por familia:",
    paste(names(table(fam_de)), table(fam_de), collapse = ", "), "\n")
stopifnot(all(ids %in% F197$ID_POLIGONO))

hip <- bind_rows(lapply(FAMILIAS, function(fam) {
  h <- read_csv(file.path(PREP, "03_hipotesis_y_variables/variables", paste0(fam, "_hipotesis.csv")),
                col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)
  h$familia <- fam
  h
}))
hip$variables <- gsub("\\s+", "", hip$variables)

# Pruebas lineales: una fila por variable
lin <- hip |>
  filter(spec == "lineal", !id %in% names(NO_EVALUABLES)) |>
  separate_rows(variables, sep = ";") |>
  rename(variable = variables) |>
  filter(variable != "") |>
  select(id, familia, variable, signo)
stopifnot(all(lin$variable %in% names(F197)))
if (anyDuplicated(lin$variable)) {
  cat("AVISO: variable en mas de una hipotesis lineal; se conserva la primera:",
      paste(unique(lin$variable[duplicated(lin$variable)]), collapse = ", "), "\n")
  lin <- lin[!duplicated(lin$variable), ]
}
sin_hipotesis <- setdiff(names(fam_de), c(lin$variable, unlist(strsplit(hip$variables[hip$spec != "lineal"], ";"))))
cat("Pruebas lineales:", nrow(lin), "| variables sin hipotesis asignada:",
    if (length(sin_hipotesis)) paste(sin_hipotesis, collapse = ", ") else "ninguna", "\n")

# Estandariza con las 197 parcelas (sin rendimiento) y toma las 138
Z <- scale(as.matrix(F197[, lin$variable]))
rownames(Z) <- F197$ID_POLIGONO
X <- Z[ids, , drop = FALSE]
if (anyNA(X)) stop("Hay NA en las variables de las 138 parcelas: este script no imputa; revisar.")
if (any(apply(X, 2, sd) == 0)) stop("Columna constante entre las 138 parcelas.")
K <- ncol(X)
idx_fam <- lapply(FAMILIAS, function(f) which(lin$familia == f))
names(idx_fam) <- FAMILIAS

# Pruebas de curva o interaccion (spec = formula)
curv <- hip |> filter(!spec %in% c("lineal", "NO_EVALUABLE"), !id %in% names(NO_EVALUABLES))
D_curv <- lapply(seq_len(nrow(curv)), function(i) {
  D <- model.matrix(as.formula(paste("~", curv$spec[i], "- 1")), data = as.data.frame(F197))
  D <- scale(D); rownames(D) <- F197$ID_POLIGONO
  D[ids, , drop = FALSE]
})
cat("Pruebas de curva:", if (nrow(curv)) paste(curv$id, collapse = ", ") else "ninguna",
    "| no evaluables:", paste(names(NO_EVALUABLES), collapse = ", "), "\n")

# ------------------------------------------------------------------------------
# 2. Particiones
# ------------------------------------------------------------------------------
leer_part <- function(nombre) {
  f <- read_csv(file.path(PREP, "01_datos/preparados", paste0("folds_", nombre, ".csv")), show_col_types = FALSE, progress = FALSE)
  lapply(split(f, f$rep), function(fk)
    list(fit = unname(pos[fk$ID_POLIGONO[fk$rol == "ajuste"]]),
         val = unname(pos[fk$ID_POLIGONO[fk$rol == "validacion"]])))
}
P1 <- leer_part("V1"); P2 <- leer_part("V2")
stopifnot(length(P1) == 100, length(P2) == 100)

# ------------------------------------------------------------------------------
# 3. Nucleo: ajuste dentro de una particion (equivale a lm(y ~ grupo + x) con pendiente comun)
# ------------------------------------------------------------------------------
medias_g <- function(M, gF, cnt) {
  s <- rowsum(M, gF, reorder = TRUE)
  out <- matrix(NA_real_, NG, ncol(s))
  k <- as.integer(rownames(s))
  out[k, ] <- s / cnt[k]
  out
}

nucleo <- function(Xm, yv, fit, val) {
  gF <- base$g[fit]; gV <- base$g[val]
  cnt <- tabulate(gF, NG)
  if (any(cnt[unique(gV)] == 0)) stop("Un grupo de validacion no esta en el ajuste")
  yF  <- yv[fit]
  MY  <- medias_g(as.matrix(yF), gF, cnt)[, 1]
  XF  <- Xm[fit, , drop = FALSE]
  MX  <- medias_g(XF, gF, cnt)
  Xc  <- XF - MX[gF, , drop = FALSE]
  yc  <- yF - MY[gF]
  sxy <- colSums(Xc * yc); sxx <- colSums(Xc^2); syy <- sum(yc^2)
  beta <- ifelse(sxx > 1e-12, sxy / sxx, 0)
  pB2 <- MY[gV]; yV <- yv[val]
  Xv  <- Xm[val, , drop = FALSE] - MX[gV, , drop = FALSE]
  err <- yV - (pB2 + sweep(Xv, 2, beta, "*"))
  list(b2 = sqrt(mean((yV - pB2)^2)), rm = sqrt(colMeans(err^2)),
       r = sxy / sqrt(pmax(sxx * syy, 1e-24)), Xc = Xc, yc = yc, Xv = Xv, pB2 = pB2, yV = yV)
}

sel_top <- function(nu, cols, k) {
  o <- cols[order(abs(nu$r[cols]), decreasing = TRUE)[seq_len(k)]]
  if (k == 1) return(nu$rm[o])
  A <- nu$Xc[, o, drop = FALSE]
  b <- tryCatch(solve(crossprod(A), crossprod(A, nu$yc)), error = function(e) NULL)
  if (is.null(b)) return(NA_real_)
  sqrt(mean((nu$yV - (nu$pB2 + nu$Xv[, o, drop = FALSE] %*% b))^2))
}

# Evalua un esquema completo: matrices (particiones x variables) de RMSE y B2
corre_esquema <- function(P, yv, con_seleccion = FALSE, Xm = X) {
  R <- length(P)
  b2 <- numeric(R); rm <- matrix(NA_real_, R, K)
  sel <- if (con_seleccion) matrix(NA_real_, R, 2 + length(FAMILIAS),
                                   dimnames = list(NULL, c("top1_global", "top3_global", paste0("top1_", FAMILIAS)))) else NULL
  for (i in seq_len(R)) {
    nu <- nucleo(Xm, yv, P[[i]]$fit, P[[i]]$val)
    b2[i] <- nu$b2; rm[i, ] <- nu$rm
    if (con_seleccion) {
      sel[i, 1] <- sel_top(nu, seq_len(K), 1)
      sel[i, 2] <- sel_top(nu, seq_len(K), 3)
      for (j in seq_along(FAMILIAS)) sel[i, 2 + j] <- sel_top(nu, idx_fam[[FAMILIAS[j]]], 1)
    }
  }
  list(b2 = b2, rm = rm, sel = sel)
}

# ------------------------------------------------------------------------------
# 4. Comprobaciones: el nucleo reproduce lm() y B2 reproduce las lineas base
# ------------------------------------------------------------------------------
set.seed(1)
for (t in 1:5) {
  i <- sample(100, 1); k <- sample(K, 1)
  pt <- P1[[i]]
  fit <- data.frame(y = y[pt$fit], x = X[pt$fit, k], grupo = factor(base$g[pt$fit], levels = 1:NG))
  val <- data.frame(x = X[pt$val, k], grupo = factor(base$g[pt$val], levels = 1:NG))
  m <- lm(y ~ grupo + x, data = droplevels(fit))
  val$grupo <- factor(val$grupo, levels = levels(droplevels(fit)$grupo))
  rmse_lm <- sqrt(mean((y[pt$val] - predict(m, newdata = val))^2))
  stopifnot(abs(rmse_lm - nucleo(X, y, pt$fit, pt$val)$rm[k]) < 1e-9)
}
cat("Comprobacion 1: el calculo rapido coincide con lm() en 5 casos al azar.\n")
lb <- read_csv(file.path(PREP, "04_resultados/lineas_base.csv"), show_col_types = FALSE, progress = FALSE)

# ------------------------------------------------------------------------------
# 5. Evaluacion real
# ------------------------------------------------------------------------------
E1 <- corre_esquema(P1, y, con_seleccion = TRUE)
E2 <- corre_esquema(P2, y, con_seleccion = TRUE)
for (esq in c("V1", "V2")) {
  ref <- lb$rmse[lb$esquema == esq & lb$modelo == "B2"][order(lb$rep[lb$esquema == esq & lb$modelo == "B2"])]
  obt <- if (esq == "V1") E1$b2 else E2$b2
  stopifnot(max(abs(ref - obt)) < 1e-9)
}
cat("Comprobacion 2: el RMSE de B2 coincide con lineas_base.csv en las 200 particiones. B2 medio V1:",
    round(mean(E1$b2), 3), "| V2:", round(mean(E2$b2), 3), "\n")

resume_delta <- function(E) {
  d <- E$b2 - E$rm
  list(media = colMeans(d), n_mejora = colSums(d > 0), rmse = colMeans(E$rm))
}
r1 <- resume_delta(E1); r2 <- resume_delta(E2)

# Pendiente y correlacion parcial dentro de grupo con las 138 parcelas
cnt_all <- tabulate(base$g, NG)
MXa <- medias_g(X, base$g, cnt_all); Xca <- X - MXa[base$g, , drop = FALSE]
yca <- y - medias_g(as.matrix(y), base$g, cnt_all)[base$g, 1]
r_par <- colSums(Xca * yca) / sqrt(colSums(Xca^2) * sum(yca^2))
sig_obs <- ifelse(r_par > 0, "+", "-")

veredicto <- function(a, b, c) ifelse(!(a & b), "descartar", ifelse(c, "pasa E1", "solo con vecinos (falla c)"))

pruebas <- tibble(
  hipotesis = lin$id, familia = lin$familia, variable = lin$variable, signo_registrado = lin$signo,
  r_parcial_en_grupo = round(r_par, 3), signo_observado = sig_obs,
  signo_coincide = ifelse(lin$signo == "ninguno", "sin signo", ifelse(lin$signo == sig_obs, "si", "no")),
  rmse_B2_v1 = round(mean(E1$b2), 4), rmse_modelo_v1 = round(r1$rmse, 4),
  delta_v1 = round(r1$media, 4), n_mejora_v1 = r1$n_mejora,
  rmse_B2_v2 = round(mean(E2$b2), 4), rmse_modelo_v2 = round(r2$rmse, 4),
  delta_v2 = round(r2$media, 4), n_mejora_v2 = r2$n_mejora
) |>
  mutate(E1_a = delta_v1 > DELTA_MIN, E1_b = n_mejora_v1 >= N_MEJORA_MIN, E1_c = delta_v2 >= 0,
         veredicto = veredicto(E1_a, E1_b, E1_c))

# Pruebas de curva
curv_filas <- lapply(seq_len(nrow(curv)), function(i) {
  D <- D_curv[[i]]
  ev <- function(P) {
    d <- numeric(length(P))
    for (j in seq_along(P)) {
      fit <- P[[j]]$fit; val <- P[[j]]$val
      gF <- base$g[fit]; gV <- base$g[val]; cnt <- tabulate(gF, NG)
      MY <- medias_g(as.matrix(y[fit]), gF, cnt)[, 1]
      MD <- medias_g(D[fit, , drop = FALSE], gF, cnt)
      A <- D[fit, , drop = FALSE] - MD[gF, , drop = FALSE]
      b <- solve(crossprod(A), crossprod(A, y[fit] - MY[gF]))
      pred <- MY[gV] + (D[val, , drop = FALSE] - MD[gV, , drop = FALSE]) %*% b
      d[j] <- sqrt(mean((y[val] - MY[gV])^2)) - sqrt(mean((y[val] - pred)^2))
    }
    d
  }
  d1 <- ev(P1); d2 <- ev(P2)
  MDa <- medias_g(D, base$g, cnt_all); Aa <- D - MDa[base$g, , drop = FALSE]
  ba <- solve(crossprod(Aa), crossprod(Aa, yca))
  tibble(hipotesis = curv$id[i], familia = curv$familia[i], variable = curv$spec[i],
         signo_registrado = curv$signo[i], r_parcial_en_grupo = NA_real_, signo_observado = NA_character_,
         signo_coincide = paste0("coef. cuadratico ", ifelse(ba[2] < 0, "negativo", "positivo")),
         rmse_B2_v1 = round(mean(E1$b2), 4), rmse_modelo_v1 = round(mean(E1$b2) - mean(d1), 4),
         delta_v1 = round(mean(d1), 4), n_mejora_v1 = sum(d1 > 0),
         rmse_B2_v2 = round(mean(E2$b2), 4), rmse_modelo_v2 = round(mean(E2$b2) - mean(d2), 4),
         delta_v2 = round(mean(d2), 4), n_mejora_v2 = sum(d2 > 0)) |>
    mutate(E1_a = delta_v1 > DELTA_MIN, E1_b = n_mejora_v1 >= N_MEJORA_MIN, E1_c = delta_v2 >= 0,
           veredicto = veredicto(E1_a, E1_b, E1_c))
})
pruebas <- bind_rows(pruebas, bind_rows(curv_filas))
pruebas$nota <- ""
pruebas$lectura <- ifelse(!pruebas$veredicto %in% c("pasa E1", "solo con vecinos (falla c)"), "descartada",
                   ifelse(pruebas$veredicto == "solo con vecinos (falla c)", "depende de vecinos (falla c)",
                   ifelse(pruebas$signo_registrado == "ninguno", "hallazgo exploratorio (sin signo registrado)",
                   ifelse(pruebas$signo_coincide == "si", "confirmada (signo coincide)",
                   ifelse(pruebas$signo_coincide == "no", "contradice el signo registrado", "curva: revisar")))))
for (id in names(NO_EVALUABLES)) {
  pruebas <- bind_rows(pruebas, tibble(hipotesis = id, familia = "clima_ventanas", variable = "(no evaluable)",
                                       veredicto = "no evaluable", lectura = "no evaluable", nota = NO_EVALUABLES[[id]]))
}
write_csv(pruebas, file.path(PREP, "04_resultados/60_pruebas_por_variable.csv"))

n_prob <- sum(!pruebas$veredicto %in% "no evaluable")
cat("\nPruebas realizadas (variables lineales + curvas):", n_prob, "\n")
cat("Veredicto E1 sobre las pruebas reales:\n"); print(table(pruebas$veredicto))
cat("\nLectura de las pruebas:\n"); print(table(pruebas$lectura))
cat("\nPasan E1 o solo fallan (c), ordenadas por delta V1:\n")
print(as.data.frame(pruebas |> filter(veredicto %in% c("pasa E1", "solo con vecinos (falla c)")) |>
                      arrange(desc(delta_v1)) |>
                      select(hipotesis, variable, signo_registrado, signo_coincide, delta_v1, n_mejora_v1, delta_v2, lectura)),
      row.names = FALSE)
cat("\nLas 12 con mayor delta V1 (pasen o no):\n")
print(as.data.frame(pruebas |> arrange(desc(delta_v1)) |> head(12) |>
                      select(hipotesis, variable, signo_registrado, signo_coincide, delta_v1, n_mejora_v1, delta_v2, veredicto)),
      row.names = FALSE)

# Resumen por hipotesis
res_hip <- pruebas |>
  filter(veredicto != "no evaluable") |>
  group_by(hipotesis) |>
  summarise(n_variables = n(), n_pasan = sum(veredicto == "pasa E1"),
            n_solo_vecinos = sum(veredicto == "solo con vecinos (falla c)"),
            n_descartadas = sum(veredicto == "descartar"),
            mejor_variable = variable[which.max(delta_v1)], mejor_delta_v1 = max(delta_v1),
            .groups = "drop")
write_csv(res_hip, file.path(PREP, "04_resultados/60_resumen_hipotesis.csv"))

# ------------------------------------------------------------------------------
# 6. Permutacion: cuantas variables pasan E1 con el rendimiento barajado dentro de grupo
# ------------------------------------------------------------------------------
set.seed(SEMILLA_PERM)
perm <- lapply(seq_len(N_PERM), function(p) {
  yp <- y
  for (gg in seq_len(NG)) { i <- which(base$g == gg); yp[i] <- y[i][sample.int(length(i))] }
  a <- corre_esquema(P1, yp, con_seleccion = TRUE); b <- corre_esquema(P2, yp, con_seleccion = TRUE)
  ra <- resume_delta(a); rb <- resume_delta(b)
  ok_ab <- ra$media > DELTA_MIN & ra$n_mejora >= N_MEJORA_MIN
  tibble(perm = p, pasan_ab = sum(ok_ab), pasan_abc = sum(ok_ab & rb$media >= 0),
         mejor_delta_v1 = max(ra$media), mejor_n_mejora_v1 = max(ra$n_mejora),
         sel_top1_delta_v1 = mean(a$b2 - a$sel[, "top1_global"]),
         sel_top3_delta_v1 = mean(a$b2 - a$sel[, "top3_global"], na.rm = TRUE),
         sel_top1_delta_v2 = mean(b$b2 - b$sel[, "top1_global"]))
})
perm <- bind_rows(perm); perm$nulo <- "grupo"

# Control estricto: las filas de variables se reparten entre celdas climaticas del mismo grupo
bloque <- paste(base$g, base$celda_clima)
donante_celda <- function() {
  don <- integer(nrow(base))
  for (gg in seq_len(NG)) {
    celdas <- unique(bloque[base$g == gg])
    dest <- sample(celdas)
    for (k in seq_along(celdas)) {
      miembros <- which(bloque == celdas[k])
      donantes <- which(bloque == dest[k])
      don[miembros] <- donantes[sample.int(length(donantes), length(miembros), replace = TRUE)]
    }
  }
  don
}
set.seed(SEMILLA_PERM + 1)
perm_c <- lapply(seq_len(N_PERM), function(p) {
  Xp <- X[donante_celda(), , drop = FALSE]
  a <- corre_esquema(P1, y, con_seleccion = TRUE, Xm = Xp); b <- corre_esquema(P2, y, con_seleccion = TRUE, Xm = Xp)
  ra <- resume_delta(a); rb <- resume_delta(b)
  ok_ab <- ra$media > DELTA_MIN & ra$n_mejora >= N_MEJORA_MIN
  tibble(perm = p, pasan_ab = sum(ok_ab), pasan_abc = sum(ok_ab & rb$media >= 0),
         mejor_delta_v1 = max(ra$media), mejor_n_mejora_v1 = max(ra$n_mejora),
         sel_top1_delta_v1 = mean(a$b2 - a$sel[, "top1_global"]),
         sel_top3_delta_v1 = mean(a$b2 - a$sel[, "top3_global"], na.rm = TRUE),
         sel_top1_delta_v2 = mean(b$b2 - b$sel[, "top1_global"]))
})
perm_c <- bind_rows(perm_c); perm_c$nulo <- "celda"
perm <- bind_rows(perm, perm_c)
write_csv(perm |> mutate(across(where(is.numeric), ~ round(.x, 4))), file.path(PREP, "04_resultados/60_permutacion.csv"))
real_ab  <- sum(pruebas$E1_a & pruebas$E1_b, na.rm = TRUE)
real_abc <- sum(pruebas$veredicto == "pasa E1")
for (nl in c("grupo", "celda")) {
  pp <- perm[perm$nulo == nl, ]
  cat("\n== Control de permutacion, nulo por ", nl, " (", N_PERM, " repeticiones) ==\n", sep = "")
  cat("Variables que pasan (a)+(b) por azar: media", round(mean(pp$pasan_ab), 2), "| p95", quantile(pp$pasan_ab, .95),
      "| max", max(pp$pasan_ab), "| REAL:", real_ab, "\n")
  cat("Variables que pasan E1 completa por azar: media", round(mean(pp$pasan_abc), 2), "| p95", quantile(pp$pasan_abc, .95),
      "| max", max(pp$pasan_abc), "| REAL:", real_abc, "\n")
  cat("Mejor delta V1 entre todas las variables, por azar: media", round(mean(pp$mejor_delta_v1), 4),
      "| p95", round(quantile(pp$mejor_delta_v1, .95), 4), "| REAL:", round(max(r1$media), 4), "\n")
  cat("Elegir la mejor variable dentro de la particion con el nulo: delta medio V1", round(mean(pp$sel_top1_delta_v1), 4),
      "| V2", round(mean(pp$sel_top1_delta_v2), 4), "(negativo = empeora a B2)\n")
}

# ------------------------------------------------------------------------------
# 7. Seleccion dentro de cada particion, con el rendimiento real
# ------------------------------------------------------------------------------
res_sel <- function(E, esq) {
  bind_rows(lapply(colnames(E$sel), function(nm) {
    d <- E$b2 - E$sel[, nm]
    tibble(esquema = esq, procedimiento = nm, rmse_B2 = mean(E$b2), rmse_proc = mean(E$sel[, nm], na.rm = TRUE),
           delta_medio = mean(d, na.rm = TRUE), delta_p5 = quantile(d, .05, na.rm = TRUE),
           delta_p95 = quantile(d, .95, na.rm = TRUE), n_mejora = sum(d > 0, na.rm = TRUE), n_part = sum(!is.na(d)))
  }))
}
sel <- bind_rows(res_sel(E1, "V1"), res_sel(E2, "V2")) |> mutate(across(where(is.numeric), ~ round(.x, 4)))
write_csv(sel, file.path(PREP, "04_resultados/60_seleccion_en_particion.csv"))
cat("\n== Seleccion dentro de cada particion (delta = B2 - procedimiento; positivo = mejora) ==\n")
print(as.data.frame(sel), row.names = FALSE)
cat("\nHecho. Sin errores.\n")
