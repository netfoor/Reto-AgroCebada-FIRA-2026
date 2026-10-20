"""Agrega R² a las métricas de validación de EXP_11 (sin reentrenar nada).

R² = 1 − MSE / Var(y), con MSE = RMSE² (RMSE sobre predicciones fuera de muestra) y Var(y) la varianza
del rendimiento de las parcelas evaluadas:
  FULL138: varianza poblacional de los 138 rendimientos de ID_area_rendimiento_70_30_Reto_AgroCebada.csv.
  SEEN135: varianza que reproduce el R² publicado de MIX y MUN en el cuaderno 03 (se comprueba abajo).
Entrada:  resultados/exp_11_combinacion_modelos/registrada/metricas.csv
Salida:   resultados/04_seleccion_modelo_final/metricas_validacion_con_r2.csv
Uso:      python scripts/agregar_r2.py
"""
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENTRADA = REPO / "resultados/exp_11_combinacion_modelos/registrada/metricas.csv"
SALIDA = REPO / "resultados/04_seleccion_modelo_final/metricas_validacion_con_r2.csv"

VAR_FULL138 = 0.7192248687250578          # var(y) de las 138 parcelas con rendimiento (ddof=0)
VAR_SEEN135 = 0.487196515 ** 2 / (1 - 0.666039)   # R² publicado de MIX en SEEN135 (cuaderno 03)

# comprobaciones contra los R² publicados en el cuaderno 03
assert abs(0.493404031 ** 2 / VAR_SEEN135 - (1 - 0.657475)) < 1e-5     # MUN SEEN135
assert abs(0.493845245 ** 2 / VAR_FULL138 - (1 - 0.660908)) < 1e-5     # MIX FULL138
assert abs(0.511757012 ** 2 / VAR_FULL138 - (1 - 0.635865)) < 1e-5     # MUN FULL138
VAR = {"SEEN135": VAR_SEEN135, "FULL138": VAR_FULL138}

with open(ENTRADA, newline="", encoding="utf-8") as f:
    filas = list(csv.DictReader(f))
campos = list(filas[0].keys()) + ["R2"]
for fila in filas:
    fila["R2"] = f"{1 - float(fila['RMSE']) ** 2 / VAR[fila['escenario']]:.6f}"
with open(SALIDA, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
    w.writeheader()
    w.writerows(filas)
print(f"Escrito {SALIDA.relative_to(REPO)} ({len(filas)} filas)")
