"""Verificación independiente de EXP_10: reimplementa MIX, residuos internos y corrección sin
importar modelo_10 ni validacion_03; recalcula métricas y reglas; compara la réplica.

    uv run --locked --all-groups python scripts/verificar_exp_10_resultados.py
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RES = RAIZ / "resultados/exp_10_verificacion_contraste_vecinal"
D10 = RAIZ / "data/exp_10_verificacion_contraste_vecinal"
PART = {"historicas": ("data/validacion_03/particiones_externas.csv", "data/validacion_03/particiones_internas.csv"),
        "nuevas": ("data/exp_09_fuentes_externas/particiones_externas_nuevas.csv", "data/exp_09_fuentes_externas/particiones_internas_nuevas.csv")}


def mix_indep(xy_a, y_a, mun_a, xy_t, mun_t):
    g = pd.Series(y_a).groupby(mun_a).mean()
    mun = np.array([g.get(m, y_a.mean()) for m in mun_t])
    d = np.sqrt(((xy_t[:, None, :] - xy_a[None, :, :]) ** 2).sum(-1))
    orden = np.argsort(d, axis=1, kind="quicksort")[:, :20]
    w = 1.0 / np.maximum(np.take_along_axis(d, orden, 1), 1.0) ** 2
    idw = (w * y_a[orden]).sum(1) / w.sum(1)
    return mun, 0.5 * mun + 0.5 * idw


def main():
    z = zipfile.ZipFile(RAIZ / "data/raw/DataSet.zip")
    lab = pd.read_csv(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv")), encoding="utf-8-sig")
    y = lab.set_index("ID_POLIGONO").RENDIMIENTO_T_HA.dropna()
    meta = pd.read_csv(D10 / "metadatos.csv").set_index("ID_POLIGONO")
    var = pd.read_csv(D10 / "variables_197.csv").set_index("ID_POLIGONO")
    oof = pd.read_csv(RES / "registrada/predicciones_oof.csv")
    max_dif = 0.0
    for cj, (pe, pi) in PART.items():
        ext, inn = pd.read_csv(RAIZ / pe), pd.read_csv(RAIZ / pi)
        for (r, f), g in ext.groupby(["repeticion", "pliegue"]):
            tr = g.loc[g.rol == "entrenamiento", "ID_POLIGONO"].to_numpy()
            va = g.loc[g.rol == "validacion", "ID_POLIGONO"].to_numpy()
            M = lambda ids: (meta.loc[ids, ["x_m", "y_m"]].to_numpy(float), meta.loc[ids, "Municipio"].to_numpy())  # noqa: E731
            xa, ma = M(tr)
            xv, mv = M(va)
            mun, mix = mix_indep(xa, y.loc[tr].to_numpy(float), ma, xv, mv)
            e = pd.Series(np.nan, index=tr)
            for _, gi in inn[(inn.repeticion == r) & (inn.pliegue == f)].groupby("pliegue_interno"):
                itr = gi.loc[gi.rol == "entrenamiento", "ID_POLIGONO"].to_numpy()
                iva = gi.loc[gi.rol == "validacion", "ID_POLIGONO"].to_numpy()
                xi, mi = M(itr)
                xj, mj = M(iva)
                e.loc[iva] = y.loc[iva].to_numpy() - mix_indep(xi, y.loc[itr].to_numpy(float), mi, xj, mj)[1]
            preds = {"MUN": mun, "MIX": mix}
            for c in ("K1_publicado", "K1_corregido"):
                x = var.loc[tr, c].to_numpy(float)
                ok = ~np.isnan(x)
                med, sd = np.median(x[ok]), np.std(x[ok], ddof=1)
                zz = (x[ok] - med) / sd
                beta = zz @ e.to_numpy()[ok] / (zz @ zz + 10.0)
                xv_ = var.loc[va, c].to_numpy(float)
                preds[c] = mix + np.where(np.isnan(xv_), 0.0, beta * (xv_ - med) / sd)
            o = oof[(oof.conjunto == cj) & (oof.repeticion == r) & (oof.pliegue == f)]
            for m, p in preds.items():
                q = o[o.modelo == m].set_index("ID_POLIGONO").loc[va, "predicho"].to_numpy()
                max_dif = max(max_dif, float(np.abs(q - p).max()))
    # métricas recalculadas
    met = pd.read_csv(RES / "registrada/metricas.csv")
    dm = 0.0
    for _, fila in met.iterrows():
        o = oof[(oof.conjunto == fila.conjunto) & (oof.modelo == fila.modelo)]
        if fila.escenario == "SEEN135":
            o = o[o.municipio_visto]
        er = o.predicho - o.observado
        dm = max(dm, abs(np.sqrt((er ** 2).mean()) - fila.RMSE), abs(er.abs().mean() - fila.MAE))
    # réplica
    rep_dir = RES / "replica_determinismo"
    iguales, distintos = [], []
    for p in sorted((RES / "registrada").iterdir()):
        if p.name == "registro_ejecucion.json":
            continue
        q = rep_dir / p.name
        (iguales if q.exists() and q.read_bytes() == p.read_bytes() else distintos).append(p.name)
    nul = json.loads((RES / "registrada/nulos_resumen.json").read_text())
    out = {"verificado_utc": datetime.now(timezone.utc).isoformat(), "implementacion_independiente": True,
           "max_dif_predicciones_oof": max_dif, "predicciones_reproducidas": bool(max_dif < 1e-10),
           "max_dif_metricas": dm, "metricas_reproducidas": bool(dm < 1e-12),
           "replica_archivos_identicos": iguales, "replica_archivos_distintos": distintos, "replica_determinista": not distintos and bool(iguales),
           "N0_reproduce_p_EXP09": bool(abs(nul["N0"]["p_k_sobre_N"] - 0.13) < 1e-12), "N0_p": nul["N0"]["p_k_sobre_N"],
           "registrada_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((RES / "registrada").iterdir())}}
    destino = RAIZ / "notebooks/experimentos/exp_10_verificacion_contraste_vecinal/verificacion_independiente.json"
    destino.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "registrada_sha256"}, indent=2, ensure_ascii=False))
    if not (out["predicciones_reproducidas"] and out["metricas_reproducidas"] and out["replica_determinista"]):
        raise SystemExit("Verificación fallida")


if __name__ == "__main__":
    main()
