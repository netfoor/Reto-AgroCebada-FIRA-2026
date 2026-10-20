# HISTORICO, NO CORRER. Copia textual del original (preparacion/scripts/27_registro_hipotesis_2C.R), con rutas ABSOLUTAS del proyecto original: si se corre, escribe en el registro del proyecto original.
# Se guarda solo como constancia de como se escribieron las filas del registro. El registro final ya esta en 03_hipotesis_y_variables/registro_experimentos.csv.
suppressPackageStartupMessages({ library(readr); library(dplyr); library(tibble) })
RAIZ <- "C:/Users/jared/Downloads/RetoAgrocebada_Beluga"
f <- file.path(RAIZ, "preparacion/registro_experimentos.csv")
reg <- read_csv(f, col_types = cols(.default = col_character()), na = character(), show_col_types = FALSE)

nuevas <- tribble(
  ~id, ~hipotesis, ~variables,
  "E1", "Regla de decision fijada antes de probar (Prompt 2C). Una variable se considera util si, sobre las mismas 100 particiones V1: (a) baja el RMSE frente a B2 en mas de 0.02 t/ha en promedio (comparacion pareada); (b) mejora en al menos 75 de las 100 particiones; (c) en V2 la mejora promedio no es negativa. Si falla (a) o (b) se descarta; si falla solo (c) se reporta como dependiente de vecinos. La seleccion de variables se repite dentro de cada particion. HR7 queda exenta de (c) porque V2 deja 0% de vecinos. Se reporta el numero total de variables probadas.", "regla de decision",
  "HR1", "El vigor tipico multianual de la parcela (SAVI de Sentinel-2, 2022-2024) se asocia con mayor rendimiento dentro de region. Signo: +. Motivo: recoge suelo y manejo estables (fertilidad, profundidad, drenaje) que el clima de una celda no distingue. Limite: no es lo mismo que el suelo.", "savi_s2_tipico_2022_2024",
  "HR2", "Una mayor variabilidad interanual del NDVI de la parcela (coeficiente de variacion 2022-2024) baja el rendimiento. Signo: -. Motivo: parcelas inestables suelen ser de temporal marginal o de manejo irregular.", "cv_interanual_ndvi",
  "HR3", "La humedad del suelo antes de la siembra (NDWI y NDDI, abr-may) se asocia con el rendimiento dentro de region. Exploratoria, sin signo fijo declarado antes de probar. Motivo: proxy de agua almacenada y de textura. Limite: con cobertura de residuo se confunde.", "ndwi_abr_may; nddi_abr_may",
  "HR4", "La elevacion de la parcela relativa a la de su celda climatica (elevacion menos promedio de la celda) baja el rendimiento. Signo: -. Motivo: dentro de una celda de clima constante, subir es mas frio y mas corta la estacion. Se evalua dentro de Chignahuapan y de Tlaxcala. Limite: DEM de 120 m.", "elev_relativa_celda",
  "HR5", "Un indice de posicion topografica a 1 km (DEM de 120 m) alto, es decir lomas frente a fondos de valle, se asocia con mayor rendimiento. Signo: +. Motivo: mejor drenaje y menos encharcamiento; los fondos acumulan frio y agua. Limite: resolucion gruesa.", "tpi_1km",
  "HR6", "Una mayor variabilidad dentro de la parcela (coeficiente de variacion del SAVI de Sentinel-2 o del NDVI de Planet, jul-sep) baja el rendimiento. Signo: -. Motivo: heterogeneidad de emergencia, suelo o plagas. Limite: parcelas de menos de 1.44 ha tienen pocos pixeles de 10 m y la desviacion es ruidosa.", "cv_savi_s2_intraparcela; cv_ndvi_planet_intraparcela",
  "HR7", "El residual promedio de las parcelas vecinas (kNN) dentro del conjunto de ajuste predice el residual de la parcela sobre B2. Signo: +. Motivo: el manejo y el suelo se comparten por cercania. Se calcula solo con parcelas del conjunto de ajuste de cada particion. Exenta de la condicion (c) de E1 porque V2 deja 0% de vecinos. Limite: solo sirve si las 59 parcelas ocultas tienen vecinos, y hay 96.6% de vecinas.", "residual_knn_vecinos",
  "HR8", "El logaritmo del area de la parcela se asocia con el rendimiento. Exploratoria, sin signo fijo. Motivo: el tamano puede reflejar tipo de productor o de manejo. Limite: el area tiene un origen por confirmar con los organizadores.", "log_area_ha",
  "HR9", "Los indices de residuo y labranza (CRC, MCRC, NDTI, STI, NDSVI, feb-may) se asocian con el rendimiento dentro de region. Sin signo fijo declarado antes de probar. Motivo: proxy de manejo del rastrojo y de labranza. Limite: los indices confunden residuo con suelo desnudo seco.", "crc; mcrc; ndti; sti; ndsvi_feb_may",
  "HR10", "Una anomalia de lluvia jun-ago 2025 (lluvia 2025 menos promedio 2022-2024 de la misma celda) alta baja el rendimiento. Signo: -. Motivo: exceso de humedad en espigado y enfermedades. Limite: 3 anios de referencia son pocos.", "anom_precip_jun_ago",
  "HR11", "Una anomalia de Tmin sep-oct 2025 alta (mas calido que el promedio 2022-2024) sube el rendimiento. Signo: +. Motivo: menos dano por helada temprana en el llenado.", "anom_tmin_sep_oct",
  "HR12", "Los compuestos mensuales sin nubes (ago-sep, nubosidad menor a 20%) de NDVI y SAVI se asocian con mayor rendimiento. Signo: +. Motivo: vigor en llenado, con menos huecos por nube que el promedio simple. Limite: no se imputan valores faltantes.", "ndvi_comp_ago; ndvi_comp_sep; savi_comp_ago; savi_comp_sep",
  "HR13", "El estres hidrico espectral (MSI, EMSI, NDDI y ENDDI) baja el rendimiento. Signo: -. DSWI2 a DSWI5 son exploratorias, sin signo fijo. Motivo: contenido de agua en la hoja. Limite: se confunde con senescencia natural.", "msi; emsi; nddi; enddi; exploratoria: dswi2 a dswi5",
  "HR14", "Una senescencia temprana medida con NDSVI en agosto baja el rendimiento. Signo: -. Motivo: la planta amarilla antes de tiempo llena menos grano. Limite: se confunde con la fecha de siembra.", "ndsvi_ago"
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
  nuevas$esquema[nuevas$id == "E1"]  <- "todos"
  nuevas$semillas[nuevas$id == "E1"] <- "no aplica"
  nuevas <- nuevas[, names(reg)]
  write_csv(bind_rows(reg, nuevas), f)
  cat("Registradas", nrow(nuevas), "filas nuevas, fecha:", nuevas$fecha[1], "\n")
}
