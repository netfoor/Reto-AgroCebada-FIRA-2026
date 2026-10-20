# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/26_registro_hipotesis_agro.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
suppressPackageStartupMessages({ library(readr); library(dplyr); library(tibble) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
f <- file.path(RAIZ, "preparacion/registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)

nuevas <- tribble(
  ~id, ~hipotesis, ~variables,
  "HA1", "Siembra tardia baja el rendimiento dentro de region. Signo: -. Motivo: menos ciclo y mas riesgo de helada temprana (Bloque A). Proxy: fecha en que el NDVI de Planet sale del suelo desnudo; el umbral se fija antes de correr.", "fecha_ascenso_ndvi_planet",
  "HA2", "Un ciclo verde mas largo sube el rendimiento hasta un punto. Signo: +. Motivo: mas tiempo de captura de luz (Bloque A). Proxy: dias entre el ascenso y la caida del NDVI de Planet, suavizado.", "dias_ciclo_ndvi_planet",
  "HA3", "El NDVI maximo del ciclo (vigor en espigado) se asocia con mayor rendimiento dentro de region. Signo: +. Limite: el NDVI se satura con dosel denso.", "ndvi_max_ciclo_planet; ndvi_max_ciclo_s2",
  "HA4", "La Tmin de jul-ago (espigado y floracion de siembras de mayo-junio) se relaciona con el rendimiento dentro de region. Signo: sin signo fijo, declarado antes de probar (la helada en espigado dana, pero un mes menos frio puede indicar otro ambiente). Limite: el promedio mensual no cuenta noches bajo 0 C.", "tmin_jul; tmin_ago",
  "HA5", "Una Tmin alta en sep-oct (llenado y heladas tempranas) se asocia con mayor rendimiento. Signo: +. Motivo: menos frio, menos dano por helada en el llenado.", "tmin_sep; tmin_oct",
  "HA6", "La lluvia de jun-jul (macollaje y encanado) se asocia con mayor rendimiento dentro de region. Signo: +. Motivo: agua en las etapas que definen espigas por m2 y granos por espiga. La lluvia de ago-sep es exploratoria, sin signo fijo: se reporta pero no cuenta como confirmada ni refutada.", "precip_jun; precip_jul; exploratoria: precip_ago; precip_sep",
  "HB1", "Una Tmax alta en ago-sep baja el rendimiento. Signo: -. Motivo: el calor acorta el llenado y baja el peso del grano. Efecto esperado debil en Valles Altos.", "tmax_ago; tmax_sep",
  "HB2", "Un mes muy seco entre jun y sep (proxy de canicula) baja el rendimiento. Variable: lluvia del mes mas seco. Signo: +.", "precip_min_mensual_jun_sep",
  "HB3", "La lluvia de junio tiene forma de curva: muy alta pierde plantas, muy baja limita el establecimiento. Sin signo lineal; se espera coeficiente cuadratico negativo.", "precip_jun; precip_jun^2",
  "HB4", "La lluvia total del ciclo (abr-oct) tiene forma de curva dentro de region: sube y luego baja. Se espera coeficiente cuadratico negativo y que Singuilucan caiga en el tramo descendente.", "precip_ciclo; precip_ciclo^2",
  "HB5", "Mayor altitud baja el rendimiento dentro de region. Signo: -. Motivo: mas frio (0.5 C por cada 100 m) y estacion mas corta. Signo incierto: se confunde con lluvia y suelo.", "elevacion_m",
  "HB6", "Interaccion pendiente x lluvia: con lluvia alta los terrenos casi planos encharcan y con lluvia baja retienen humedad. Signo: coeficiente de la interaccion > 0. Limite: es la pendiente de la parcela, no su drenaje.", "pendiente_grados x precip_ciclo",
  "HB7", "Una caida rapida del NDVI de Planet despues del maximo baja el rendimiento. Signo: -. Motivo: senescencia acelerada por sequia tardia, helada o enfermedad. Limite: se confunde con la fecha de siembra y con la maduracion normal.", "pendiente_caida_ndvi_planet",
  "HB8", "Un rango termico alto en septiembre (Tmax - Tmin) baja el rendimiento (helada de radiacion). Signo: - debil. Proxy pobre.", "rango_termico_sep",
  "HC1", "Mucha lluvia en jul-ago baja el rendimiento. Signo: -. Motivo: mas humedad en espigado favorece las manchas foliares.", "precip_jul_ago",
  "HC2", "Una temperatura media de jul-ago entre 15 y 20 C con lluvia alta baja el rendimiento (condiciones de roya de la hoja). Signo: -. Tmedia = (Tmax + Tmin) / 2 [CP]. Lluvia alta = por encima de la mediana del conjunto de ajuste. Proxy pobre.", "tmedia_jul_ago_15_20 x precip_jul_ago_alta",
  "HC3", "Interaccion altitud x lluvia: en sitios altos y humedos (desde 2,500 msnm) el rendimiento baja mas. Signo: coeficiente de la interaccion < 0. Se confunde con region.", "elevacion_m x precip_ciclo",
  "HD1", "Dentro de Singuilucan, mayor altitud implica menor rendimiento. Signo: -. Motivo: estacion corta y helada temprana. Solo 16 parcelas de entrenamiento: ruido alto.", "elevacion_m dentro de Singuilucan",
  "HD2", "La lluvia de Singuilucan funciona como etiqueta de municipio: sobre B2 la lluvia no aporta en Hidalgo (mejora del RMSE frente a B2 cercana a 0 o negativa).", "precip_ciclo sobre B2",
  "HD3", "Dentro de Chignahuapan, el satelite y la topografia aportan mas que el clima, porque el clima toma unos 4 valores distintos.", "sat_* y topo_* frente a clim_* en Chignahuapan",
  "HD4", "Chequeo descriptivo, no hipotesis de modelo: revisar la altitud por grupo antes de interpretar el +0.29 global; si Singuilucan es el grupo mas alto, esa correlacion seria enganosa.", "elevacion_m por grupo"
)

nuevas <- filter(nuevas, !id %in% reg$id)
if (nrow(nuevas) == 0) {
  cat("Todas las hipotesis ya estaban registradas; no se modifica nada.\n")
} else {
  nuevas$fecha     <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  nuevas$esquema   <- "V1 (principal) y V2; se evalua sobre B2 dentro de la CV"
  nuevas$semillas  <- "V1: 1-100; V2: 1001-1100"
  nuevas$resultado <- ""
  nuevas$decision  <- ""
  nuevas$esquema[nuevas$id == "HD4"]  <- "descriptivo, sin CV"
  nuevas$semillas[nuevas$id == "HD4"] <- "no aplica"
  nuevas <- nuevas[, names(reg)]
  write_csv(bind_rows(reg, nuevas), f)
  cat("Registradas", nrow(nuevas), "hipotesis nuevas, fecha:", nuevas$fecha[1], "\n")
}
