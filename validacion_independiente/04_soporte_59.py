"""Paso 4 (solo X): soporte de las variables del procedimiento final en las 59 parcelas ocultas.

No predice las 59. Compara cada oculta con las 138 etiquetadas (las que usaría un entrenamiento final).
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib_validacion as L


def main():
    tx = L.tabla_x()
    t = tx.set_index(L.ID)
    lab = tx.loc[tx.CONJUNTO.eq("ENTRENAMIENTO"), L.ID].to_numpy()
    ocu = tx.loc[tx.CONJUNTO.eq("PREDICCION"), L.ID].to_numpy()
    xy = t[["x_m", "y_m"]]
    d = np.linalg.norm(xy.loc[ocu].to_numpy()[:, None] - xy.loc[lab].to_numpy()[None], axis=2)
    filas = []
    for i, p in enumerate(ocu):
        mun, cel = t.loc[p, "Municipio"], t.loc[p, "celda"]
        filas.append({L.ID: p, "Municipio": mun, "grupo": t.loc[p, "grupo"], "celda": cel,
                      "etiquetadas_en_municipio": int((t.loc[lab, "Municipio"] == mun).sum()),
                      "etiquetadas_en_celda": int((t.loc[lab, "celda"] == cel).sum()),
                      "tiene_K1": bool(np.isfinite(t.loc[p, "K1_corregido"])),
                      "log_area_dentro_rango": bool(t.loc[lab, "log_area"].min() <= t.loc[p, "log_area"] <= t.loc[lab, "log_area"].max()),
                      "dist_etiquetada_mas_cercana_m": float(d[i].min())})
    s = pd.DataFrame(filas)
    s.to_csv(L.AQUI / "soporte_59.csv", index=False, float_format="%.6g")
    resumen = {
        "ocultas": len(s), "sin_K1": int((~s.tiene_K1).sum()), "celda_sin_etiquetadas": int((s.etiquetadas_en_celda == 0).sum()),
        "log_area_fuera_de_rango": int((~s.log_area_dentro_rango).sum()),
        "dist_mediana_m": float(s.dist_etiquetada_mas_cercana_m.median()), "con_vecina_a_menos_de_1km": int((s.dist_etiquetada_mas_cercana_m < 1000).sum()),
        "AGC_120": s.set_index(L.ID).loc["AGC_120"].to_dict(),
    }
    print(json.dumps(resumen, indent=2, ensure_ascii=False, default=str))
    print(s.groupby("Municipio")[["tiene_K1", "log_area_dentro_rango"]].mean().round(2).join(s.groupby("Municipio").size().rename("n")))


if __name__ == "__main__":
    main()
