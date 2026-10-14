"""Ronda 2: registro previo de hipótesis y recetas, ANTES de calcular variables o mirar rendimientos."""

from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import lib_r2 as R

L = R.L


def main():
    p = R.AQUI / "registro_previo.json"
    if p.exists():
        raise SystemExit("ya registrado")
    spec = importlib.util.spec_from_file_location("cv2", R.AQUI / "02_cv.py")
    cv2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cv2)
    tx = L.tabla_x()
    dev = sorted(set(tx.loc[tx.CONJUNTO.eq("ENTRENAMIENTO"), L.ID]) - set(L.caja_registrada()))
    ext, _ = cv2.particiones(dev)
    tmp = R.AQUI / "_particiones_externas_registro.csv"
    ext.to_csv(tmp, index=False)
    ahora = datetime.now(timezone.utc)
    reg = {
        "id": "PRUEBA_FINAL_OPUS_RONDA2", "registrado_utc": ahora.isoformat(),
        "registrado_cdmx": ahora.astimezone(ZoneInfo("America/Mexico_City")).isoformat(),
        "autor": "Claude (Opus 5.5), a pedido de Fortino", "rendimientos_leidos_en_esta_ronda_antes_del_registro": False,
        "exposicion_previa": "Se conocen las 138 etiquetas (EXP_08–11) y los resultados de la ronda 1, incluida la caja (K primero, J último). Las hipótesis se eligieron por mecanismo agronómico y disponibilidad de datos (Fase A), sin correlaciones con el rendimiento; H1 y H2 no se habían calculado nunca.",
        "hipotesis": {
            "H1": {"variable": "tpi_1km_m", "mecanismo": "Bolsas de aire frío: el aire frío nocturno drena hacia las depresiones relativas; en Valles Altos las heladas tempranas (sep–oct) durante el llenado de grano reducen el rendimiento de la cebada de temporal. Parcelas más bajas que su entorno → más heladas → menor rendimiento.",
                   "signo_esperado": "+ (TPI mayor → rendimiento mayor)",
                   "receta": "Copernicus DEM GLO-30 (tile N19 W099). Elevación de la parcela = media de píxeles con centro dentro del polígono (si ninguno, píxel del centroide). TPI = elevación de la parcela − media de los píxeles con centro a ≤1000 m del centroide (distancias en UTM 14N). Radio fijado por escala de valle, no ajustado."},
            "H2": {"variable": "soc_0_30_dgkg", "mecanismo": "Fertilidad y humedad: más carbono orgánico implica más nitrógeno mineralizable y mayor retención de agua, lo que aumenta el rendimiento de la cebada de temporal.",
                   "signo_esperado": "+",
                   "receta": "SoilGrids 2.0 soc (dg/kg), media de 0-5, 5-15 y 15-30 cm ponderada por espesor (5, 10, 15 cm). Valor por parcela = media de píxeles de 250 m (proyección Homolosine) con centro dentro del polígono; si ninguno, píxel del centroide."},
            "por_que_no_una_tercera": "La pendiente ya entró sin señal en el barrido de EXP_08 (120 m); manejo, siembra y riego no son públicos a escala de parcela (Fase A). Dos hipótesis reducen la multiplicidad.",
        },
        "chequeo_solo_X": "Por variable: R² explicado por municipio, grupo y celda CHIRPS; desviación dentro de municipio; correlación con la elevación de 120 m. Regla: si R²(celda) ≥ 0.90 o no varía dentro del municipio, la hipótesis NO se evalúa.",
        "correccion": "Para base ∈ {E_JK, MIX}: residuos de la base en el entrenamiento por los 4 pliegues internos (cada predicción interna de E_JK reajusta J y K; K usa sus propios 4 pliegues internos con semilla base+k). z = (v − mediana)/desviación del entrenamiento; β = Σz·e/(Σz² + 10); sin dato → 0 (receta de K). Sin búsqueda de hiperparámetros.",
        "familias_nuevas": "H1_E_JK, H1_MIX, H2_E_JK, H2_MIX (solo las hipótesis que pasen el chequeo)",
        "cv": {"parcelas": "las 103 de desarrollo de la ronda 1", "esquema": "10×5, semilla 20261021+rep; internas 4 con semilla 20261021+1000+10·rep+pliegue",
               "nota": "También se reevalúan F1–F7 de la ronda 1 con estas particiones para incluirlas en el nulo."},
        "particiones": {"externas_sha256": L.sha(tmp)},
        "nulo": "Reality Check de White (2000) frente a E_JK con F1–F7 + familias nuevas; pérdida por parcela SEEN; bootstrap por celdas CHIRPS, B=5000. Informativo frente a MIX.",
        "seleccion": "Final = familia nueva con menor RMSE SEEN en la CV de la ronda 2; variante declarada = misma hipótesis sobre la otra base.",
        "criterio": "El mismo de la ronda 1 (C1 caja RMSE < E_JK y < MIX; C2 CV ≥8/10 frente a ambos; C3 caja MAE ≤ MIX; C4 no se invierte sin las 2 más favorables; C5 nulo p ≤ 0.10). FAVORABLE / PARCIAL / NO FAVORABLE, sin cambiar umbrales.",
        "caja": {"ids_sha256": L.hash_lista(L.caja_registrada()), "uso": "SEGUNDO uso de la caja de la ronda 1: menos limpia, porque ya se conocen sus resultados para los congelados.",
                 "entrenamiento": "las 103 de desarrollo; pliegues internos de K iguales a la ronda 1 (semilla 20261014); para los residuos internos de E_JK se usa la semilla 20261024+k."},
        "prohibiciones": "Nada posterior al 31 oct 2025 (DEM y suelo son estáticos); nada derivado de etiquetas de validación; ni la grafía de Cultivo ni la precisión de las etiquetas.",
        "datos_sha256": json.loads((R.DATOS / "registro_descargas.json").read_text())["archivos"],
        "codigo_sha256": {f: L.sha(R.AQUI / f) for f in ["lib_r2.py", "00_descargar.py", "00b_registrar.py", "01_variables_x.py", "02_cv.py", "03_nulo_congelar.py", "04_caja.py"]},
    }
    tmp.unlink()
    p.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    with open(R.AQUI / "intentos.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["familia", "evento", "fecha_utc", "rmse_cv_seen", "mae_cv_seen", "reps_vs_E_JK", "reps_vs_MIX", "nota"])
        for f in ["H1_E_JK", "H1_MIX", "H2_E_JK", "H2_MIX"]:
            w.writerow([f, "planeada", ahora.isoformat(), "", "", "", "", "registro previo ronda 2"])
    print(reg["registrado_cdmx"], reg["particiones"])


if __name__ == "__main__":
    main()
