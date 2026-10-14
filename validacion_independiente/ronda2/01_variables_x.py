"""Ronda 2, paso 1 (solo X): construye H1/H2 para las 197 parcelas y comprueba que varían dentro del municipio
y no son solo una etiqueta de lugar. Regla registrada: si R² por celda CHIRPS ≥ 0.90, la hipótesis no se evalúa."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lib_r2 as R


def r2_por(df, col, grupo):
    m = df.groupby(grupo)[col].transform("mean")
    return float(1 - ((df[col] - m) ** 2).sum() / ((df[col] - df[col].mean()) ** 2).sum())


def main():
    vx = R.variables_externas()
    vx.to_csv(R.AQUI / "variables_externas.csv", index=False, float_format="%.6f")
    tx = R.L.tabla_x()
    d = tx.merge(vx, on=R.L.ID)
    v0 = pd.read_csv(R.L.RAIZ / "data/referencias/variables_v0_197.csv", usecols=[R.L.ID, "topo_elev_media_m"])
    d = d.merge(v0, on=R.L.ID)
    out = {}
    for h, col in R.HIPOTESIS.items():
        ok = d[col].notna()
        dd = d[ok]
        within_sd = float(np.sqrt(((dd[col] - dd.groupby("Municipio")[col].transform("mean")) ** 2).mean()))
        out[h] = {"variable": col, "n_validos": int(ok.sum()), "faltantes": int((~ok).sum()), "media": float(dd[col].mean()), "sd": float(dd[col].std()),
                  "sd_dentro_municipio": within_sd, "R2_municipio": r2_por(dd, col, "Municipio"), "R2_grupo": r2_por(dd, col, "grupo"),
                  "R2_celda_CHIRPS": r2_por(dd, col, "celda"),
                  "pearson_con_elevacion_120m": float(dd[col].corr(dd.topo_elev_media_m)),
                  "parcelas_sin_pixel_centro_dentro": int((dd[[c for c in dd.columns if c.startswith("n_pix_soil") or c == "n_pix_dem"]].min(axis=1) == 0).sum())}
        out[h]["pasa_regla_no_etiqueta"] = bool(out[h]["R2_celda_CHIRPS"] < 0.90 and within_sd > 0)
    out["correlacion_H1_H2"] = float(d.tpi_1km_m.corr(d.soc_0_30_dgkg))
    (R.AQUI / "chequeo_x.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
