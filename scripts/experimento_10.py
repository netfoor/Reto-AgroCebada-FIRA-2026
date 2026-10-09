"""EXP_10: verificación de K1 con corte temporal correcto, comparación acotada, nulos y reglas.

    uv run --locked --all-groups python scripts/experimento_10.py --salida resultados/exp_10_verificacion_contraste_vecinal/registrada
    uv run --locked --all-groups python scripts/experimento_10.py --salida resultados/exp_10_verificacion_contraste_vecinal/replica_determinismo

No genera las 59 predicciones finales.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import io
import json
import platform
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from modelo_10 import ALPHA, ID, Y, ajustar_correccion, aplicar_correccion, predecir_fold

RAIZ = Path(__file__).resolve().parents[1]
D10 = RAIZ / "data/exp_10_verificacion_contraste_vecinal"
PARTICIONES = {
    "historicas": ("data/validacion_03/particiones_externas.csv", "data/validacion_03/particiones_internas.csv"),
    "nuevas": ("data/exp_09_fuentes_externas/particiones_externas_nuevas.csv", "data/exp_09_fuentes_externas/particiones_internas_nuevas.csv"),
}
CANDIDATOS = ["K1_publicado", "K1_corregido"]
MODELOS = ["MUN", "MIX"] + CANDIDATOS
N_PERM = 200
SEMILLAS = {"N0": 20261009, "N1": 20261010, "N2": 20261011}
CUENTA = {"referencias_exteriores": 0, "mix_internos": 0, "ajustes_correccion": 0,
          "control_fuga_referencias": 0, "control_fuga_mix_internos": 0, "control_fuga_correcciones": 0,
          "nulo_ajustes_correccion": 0}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def etiquetas():
    z = zipfile.ZipFile(RAIZ / "data/raw/DataSet.zip")
    e = pd.read_csv(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv")), encoding="utf-8-sig")
    e = e[[ID, Y]].dropna()
    assert len(e) == 138 and e[ID].is_unique
    return e


def metricas(y, p):
    e = np.asarray(p, float) - np.asarray(y, float)
    sse = float(e @ e)
    yc = np.asarray(y, float) - np.mean(y)
    return {"n_oof": len(e), "RMSE": float(np.sqrt(sse / len(e))), "MAE": float(np.mean(np.abs(e))),
            "R2": float(1 - sse / (yc @ yc)) if (yc @ yc) > 1e-12 else np.nan}


def correr(tabla, contrastes, conjunto, alterar_validacion=False):
    ext, inn = [pd.read_csv(RAIZ / p) for p in PARTICIONES[conjunto]]
    filas, params, residuos = [], [], []
    ids138 = set(tabla.loc[tabla[Y].notna(), ID])
    for (r, f), g in ext.groupby(["repeticion", "pliegue"], sort=True):
        tr = g.loc[g.rol.eq("entrenamiento"), ID].to_numpy()
        va = g.loc[g.rol.eq("validacion"), ID].to_numpy()
        assert set(tr) | set(va) == ids138
        t = tabla.set_index(ID)
        if alterar_validacion:   # control de fuga: etiquetas exteriores de validación sustituidas
            t = t.copy()
            t.loc[va, Y] = 99.0
        a = t.loc[tr].reset_index()
        v = t.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
        fold_int = inn[(inn.repeticion == r) & (inn.pliegue == f)]
        preds, par, e = predecir_fold(a, v, fold_int, contrastes)
        pref = "control_fuga_" if alterar_validacion else ""
        CUENTA[pref + ("referencias" if alterar_validacion else "referencias_exteriores")] += 1
        CUENTA[pref + "mix_internos"] += fold_int.pliegue_interno.nunique()
        CUENTA[pref + ("correcciones" if alterar_validacion else "ajustes_correccion")] += len(contrastes)
        visto = v.Municipio.isin(set(a.Municipio)).to_numpy()
        for m in MODELOS:
            filas.append(pd.DataFrame({"conjunto": conjunto, "repeticion": int(r), "pliegue": int(f), ID: va,
                                       "Municipio": v.Municipio.to_numpy(), "municipio_visto": visto, "modelo": m, "predicho": preds[m]}))
        for m, p in par.items():
            params.append({"conjunto": conjunto, "repeticion": int(r), "pliegue": int(f), "modelo": m, **p})
        if not alterar_validacion:
            residuos.append(pd.DataFrame({"conjunto": conjunto, "repeticion": int(r), "pliegue": int(f), ID: e.index, "residuo_mix_interno": e.to_numpy()}))
    oof = pd.concat(filas, ignore_index=True)
    return oof, pd.DataFrame(params), (pd.concat(residuos, ignore_index=True) if residuos else None)


# ---------------------------------------------------------------- nulos de familia
def preparar_nulo(tabla, oof, res):
    """Por pliegue histórico: MIX, y, máscara SEEN, IDs de entrenamiento/validación y residuos internos."""
    o = oof[(oof.conjunto == "historicas") & (oof.modelo == "MIX")].copy()
    o[Y] = o[ID].map(tabla.set_index(ID)[Y])
    rr = res[res.conjunto == "historicas"]
    folds = []
    for (r, f), g in o.groupby(["repeticion", "pliegue"], sort=True):
        e = rr[(rr.repeticion == r) & (rr.pliegue == f)].set_index(ID).residuo_mix_interno
        folds.append({"tr": e.index.to_numpy(), "e": e, "va": g[ID].to_numpy(), "mix": g.predicho.to_numpy(),
                      "y": g[Y].to_numpy(float), "visto": g.municipio_visto.to_numpy()})
    return folds


def rmse_familia(K, folds):
    """RMSE SEEN de K1x, K2..K5 y K6 (los cinco juntos) con la receta de EXP_09."""
    cols = list(K.columns)
    se = {c: [] for c in cols + ["K6"]}
    vis = []
    for fd in folds:
        for c in cols:
            p = ajustar_correccion(K[c], fd["e"])
            se[c].append((fd["mix"] + aplicar_correccion(p, K[c], fd["va"])[0] - fd["y"]) ** 2)
        X = K.loc[fd["tr"], cols]
        med, sd = X.median(), X.std()
        Z = ((X - med) / sd).fillna(0.0).to_numpy()
        beta = np.linalg.solve(Z.T @ Z + ALPHA * np.eye(len(cols)), Z.T @ fd["e"].to_numpy())
        Zv = ((K.loc[fd["va"], cols] - med) / sd).fillna(0.0).to_numpy()
        se["K6"].append((fd["mix"] + Zv @ beta - fd["y"]) ** 2)
        vis.append(fd["visto"])
        CUENTA["nulo_ajustes_correccion"] += len(cols) + 1
    vis = np.concatenate(vis)
    return {c: float(np.sqrt(np.concatenate(v)[vis].mean())) for c, v in se.items()}


def permutar_municipio(K, municipio, rng):
    """Igual que EXP_09: filas permutadas juntas dentro de cada municipio."""
    out = K.copy()
    for _, g in municipio.groupby(municipio):
        idx = g.index.to_numpy()
        out.loc[idx] = K.loc[rng.permutation(idx)].to_numpy()
    return out


class MSR:
    """Aleatorización espectral de Moran (singleton) con signos comunes a todas las columnas."""

    def __init__(self, K, meta, radio=1000.0):
        self.dom = K.index[K.notna().any(axis=1)]
        xy = meta.set_index(ID).loc[self.dom, ["x_m", "y_m"]].to_numpy(float)
        d = np.linalg.norm(xy[:, None] - xy[None], axis=2)
        W = ((d > 0) & (d < radio)).astype(float)
        n = len(self.dom)
        M = np.eye(n) - 1.0 / n
        val, U = np.linalg.eigh(M @ W @ M)
        const = np.argmax(np.abs(U.T @ np.ones(n)) / np.sqrt(n))
        assert np.abs(U[:, const] @ np.ones(n)) / np.sqrt(n) > 1 - 1e-8
        self.U = np.delete(U, const, axis=1)
        self.lam = np.delete(val, const)
        self.W = W
        self.mask = K.loc[self.dom].isna().to_numpy()
        X = K.loc[self.dom].to_numpy(float).copy()
        med = np.nanmedian(X, axis=0)
        X[self.mask] = np.take(med, np.where(self.mask)[1])
        self.mu = X.mean(0)
        self.A = self.U.T @ (X - self.mu)
        self.cols = K.columns
        self.index = K.index
        rec = self.mu + self.U @ self.A
        assert np.allclose(rec, X, atol=1e-10)

    def moran(self, X):
        Xc = X - X.mean(0)
        return np.einsum("ij,ik,kj->j", Xc, self.W, Xc) / np.einsum("ij,ij->j", Xc, Xc) * len(X) / self.W.sum()

    def sorteo(self, rng):
        s = rng.choice([-1.0, 1.0], size=self.A.shape[0])
        X = self.mu + self.U @ (s[:, None] * self.A)
        Xf = X.copy()
        Xf[self.mask] = np.nan
        out = pd.DataFrame(np.nan, index=self.index, columns=self.cols)
        out.loc[self.dom] = Xf
        return out, X


def nulo(nombre, K, folds, municipio, meta, k1):
    rng = np.random.default_rng(SEMILLAS[nombre])
    obs = rmse_familia(K, folds)
    filas = []
    msr = MSR(K, meta) if nombre == "N2" else None
    conservacion = []
    for i in range(N_PERM):
        if msr is None:
            Kp = permutar_municipio(K, municipio, rng)
        else:
            Kp, Xfull = msr.sorteo(rng)
            if i < 20:
                X0 = msr.mu + msr.U @ msr.A
                conservacion.append({"sorteo": i, "max_dif_moran": float(np.abs(msr.moran(Xfull) - msr.moran(X0)).max()),
                                     "max_dif_covarianza": float(np.abs(np.cov(Xfull.T) - np.cov(X0.T)).max()),
                                     "faltantes_iguales": bool((Kp.isna() == K.isna()).all().all())})
        r = rmse_familia(Kp, folds)
        filas.append({"nulo": nombre, "sorteo": i, **r, "minimo_familia": min(r.values())})
    dr = pd.DataFrame(filas)
    kk = int((dr.minimo_familia <= obs[k1]).sum())
    resumen = {"nulo": nombre, "candidato": k1, "rmse_observado": obs[k1], "observado_familia": obs,
               "k": kk, "N": N_PERM, "p_k_sobre_N": kk / N_PERM, "p_k1_sobre_N1": (kk + 1) / (N_PERM + 1),
               "media_minimo_nulo": float(dr.minimo_familia.mean()), "p5_minimo_nulo": float(dr.minimo_familia.quantile(0.05)),
               "semilla": SEMILLAS[nombre]}
    if conservacion:
        c = pd.DataFrame(conservacion)
        resumen["conservacion_msr"] = {"max_dif_moran": float(c.max_dif_moran.max()), "max_dif_covarianza": float(c.max_dif_covarianza.max()),
                                       "faltantes_iguales": bool(c.faltantes_iguales.all())}
        resumen["valido"] = bool(c.max_dif_moran.max() < 1e-8 and c.max_dif_covarianza.max() < 1e-8 and c.faltantes_iguales.all())
    else:
        resumen["valido"] = True
    return dr, resumen


# ---------------------------------------------------------------- diagnósticos
def diagnosticos(oof):
    filas, reps, munis, zonas, parc, sens = [], [], [], [], [], []
    for (cj, esc), o in [((c, e), d) for c in PARTICIONES for e, d in [("SEEN135", oof[(oof.conjunto == c) & oof.municipio_visto]), ("FULL138", oof[oof.conjunto == c])]]:
        for m, g in o.groupby("modelo"):
            filas.append({"conjunto": cj, "escenario": esc, "modelo": m, "n_parcelas": g[ID].nunique(), **metricas(g.observado, g.predicho)})
            for r, gr in g.groupby("repeticion"):
                reps.append({"conjunto": cj, "escenario": esc, "modelo": m, "repeticion": r, **metricas(gr.observado, gr.predicho)})
            if esc == "SEEN135":
                for mu, gm in g.groupby("Municipio"):
                    munis.append({"conjunto": cj, "modelo": m, "Municipio": mu, "n_parcelas": gm[ID].nunique(), **metricas(gm.observado, gm.predicho)})
                for z, gz in [("Chignahuapan", g[g.Municipio.eq("Chignahuapan")]), ("resto", g[~g.Municipio.eq("Chignahuapan")])]:
                    zonas.append({"conjunto": cj, "modelo": m, "zona": z, **metricas(gz.observado, gz.predicho)})
        if esc != "SEEN135":
            continue
        w = o.pivot_table(index=[ID, "repeticion"], columns="modelo", values="predicho").join(o.groupby([ID, "repeticion"]).observado.first())
        for c in CANDIDATOS:
            for ref in ["MIX", "K1_publicado"]:
                if c == ref:
                    continue
                dse = ((w[c] - w.observado) ** 2 - (w[ref] - w.observado) ** 2).groupby(ID).sum().sort_values()
                for pid, v in dse.items():
                    parc.append({"conjunto": cj, "candidato": c, "referencia": ref, ID: pid, "delta_sse_10reps": v})
                if ref == "MIX":
                    for k in (0, 2, 5):
                        quitar = set(dse.index[:k])
                        ww = w[~w.index.get_level_values(ID).isin(quitar)]
                        rc = metricas(ww.observado, ww[c])["RMSE"]
                        rm = metricas(ww.observado, ww["MIX"])["RMSE"]
                        sens.append({"conjunto": cj, "candidato": c, "retiradas_de_evaluacion": k, "parcelas_retiradas": ";".join(sorted(quitar)),
                                     "RMSE_candidato": rc, "RMSE_MIX": rm, "delta_RMSE": rc - rm})
    return (pd.DataFrame(filas), pd.DataFrame(reps), pd.DataFrame(munis), pd.DataFrame(zonas), pd.DataFrame(parc), pd.DataFrame(sens))


def reglas(met, rep, sens, nulos_res):
    out = []
    for c in CANDIDATOS:
        fila = {"candidato": c}
        for cj in PARTICIONES:
            s = met[(met.conjunto == cj) & (met.escenario == "SEEN135")].set_index("modelo")
            rr = rep[(rep.conjunto == cj) & (rep.escenario == "SEEN135")].pivot(index="repeticion", columns="modelo", values="RMSE")
            fila[f"R1_{cj}"] = bool(s.loc[c, "RMSE"] < s.loc["MIX", "RMSE"])
            fila[f"R2_{cj}_reps"] = int((rr[c] < rr["MIX"]).sum())
            fila[f"R3_{cj}"] = bool(s.loc[c, "MAE"] <= s.loc["MIX", "MAE"])
            fila[f"R4_{cj}"] = bool(sens[(sens.conjunto == cj) & (sens.candidato == c) & (sens.retiradas_de_evaluacion == 2)].delta_RMSE.iloc[0] < 0)
        fila["R1"] = all(fila[f"R1_{cj}"] for cj in PARTICIONES)
        fila["R2"] = all(fila[f"R2_{cj}_reps"] >= 8 for cj in PARTICIONES)
        fila["R3"] = all(fila[f"R3_{cj}"] for cj in PARTICIONES)
        fila["R4"] = all(fila[f"R4_{cj}"] for cj in PARTICIONES)
        fila["requisitos_predictivos"] = fila["R1"] and fila["R2"] and fila["R3"] and fila["R4"]
        if c == "K1_corregido":
            n1, n2 = nulos_res["N1"], nulos_res["N2"]
            fila["p_N1"] = n1["p_k1_sobre_N1"]
            fila["p_N2"] = n2["p_k1_sobre_N1"] if n2["valido"] else np.nan
            fila["S_evaluable"] = bool(n2["valido"])
            fila["S"] = bool(n2["valido"] and n1["p_k1_sobre_N1"] <= 0.10 and n2["p_k1_sobre_N1"] <= 0.10)
        else:
            fila["p_N0_publicado"] = nulos_res["N0"]["p_k_sobre_N"]
        out.append(fila)
    return pd.DataFrame(out)


def decision(reg):
    k = reg.set_index("candidato").loc["K1_corregido"]
    if not k.requisitos_predictivos:
        return "conservar_MIX_K1_corregido_sin_adopcion"
    if not k.S:
        return "conservar_MIX_K1_corregido_alternativa_documentada_sin_evidencia_estadistica_suficiente"
    return "considerar_K1_corregido_candidato_provisional_para_revision"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, required=True)
    args = ap.parse_args()
    salida = args.salida if args.salida.is_absolute() else RAIZ / args.salida
    if salida.exists() and any(salida.iterdir()):
        raise ValueError("Salida existente: no se sobrescribe")
    salida.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    inicio = datetime.now(timezone.utc).isoformat()
    meta = pd.read_csv(D10 / "metadatos.csv")
    var = pd.read_csv(D10 / "variables_197.csv").set_index(ID)
    fam = pd.read_csv(D10 / "familia_exp09_publicada.csv").set_index(ID)
    tabla = meta.merge(etiquetas(), on=ID, how="left")
    contr = {c: var[c] for c in CANDIDATOS}
    oofs, pars, ress = [], [], []
    for cj in PARTICIONES:
        o, p, r = correr(tabla, contr, cj)
        oofs.append(o)
        pars.append(p)
        ress.append(r)
        o2, _, _ = correr(tabla, contr, cj, alterar_validacion=True)
        if not np.array_equal(o.predicho.to_numpy(), o2.predicho.to_numpy()):
            raise ValueError("Fuga: cambiar etiquetas de validación cambió predicciones")
    oof = pd.concat(oofs, ignore_index=True).merge(tabla[[ID, Y]].rename(columns={Y: "observado"}), on=ID, how="left")
    assert oof.observado.notna().all()
    params, res = pd.concat(pars, ignore_index=True), pd.concat(ress, ignore_index=True)
    met, rep, munis, zonas, parc, sens = diagnosticos(oof)
    folds = preparar_nulo(tabla, oof, res)
    municipio = meta.set_index(ID).Municipio
    K0 = pd.concat([var.K1_publicado.rename("K1_publicado"), fam[["K2", "K3", "K4", "K5"]]], axis=1).sort_index()
    K1c = pd.concat([var.K1_corregido.rename("K1_corregido"), fam[["K2", "K3", "K4", "K5"]]], axis=1).sort_index()
    nul_d, nul_r = [], {}
    for nombre, K, k1 in [("N0", K0, "K1_publicado"), ("N1", K1c, "K1_corregido"), ("N2", K1c, "K1_corregido")]:
        d, r = nulo(nombre, K, folds, municipio.loc[K.index], meta, k1)
        nul_d.append(d)
        nul_r[nombre] = r
    reg = reglas(met, rep, sens, nul_r)
    dec = decision(reg)
    oculta = meta.CONJUNTO.eq("PREDICCION").to_numpy()
    sop = var.loc[meta[ID][oculta], ["Municipio", "K1_corregido", "K1_publicado", "vecinos_geometricos"]].assign(
        respaldo_MIX=lambda d: d.K1_corregido.isna(),
        dentro_rango_etiquetadas=lambda d: d.K1_corregido.between(var.loc[meta[ID][~oculta], "K1_corregido"].min(), var.loc[meta[ID][~oculta], "K1_corregido"].max())).reset_index()
    salidas = {"predicciones_oof.csv": oof, "parametros_exteriores.csv": params, "residuos_internos.csv": res, "metricas.csv": met,
               "repeticiones.csv": rep, "municipios.csv": munis, "zonas.csv": zonas, "concentracion_parcelas.csv": parc,
               "sensibilidades.csv": sens, "nulos_sorteos.csv": pd.concat(nul_d, ignore_index=True), "reglas.csv": reg, "soporte_59.csv": sop}
    for n, df in salidas.items():
        df.to_csv(salida / n, index=False, float_format="%.17g")
    (salida / "nulos_resumen.json").write_text(json.dumps(nul_r, indent=2, ensure_ascii=False) + "\n")
    insumos = ["data/raw/DataSet.zip", *[p for par in PARTICIONES.values() for p in par],
               *[f"data/exp_10_verificacion_contraste_vecinal/{n}" for n in ("metadatos.csv", "variables_197.csv", "familia_exp09_publicada.csv")],
               "scripts/modelo_10.py", "scripts/experimento_10.py", "scripts/validacion_03.py",
               "notebooks/experimentos/exp_10_verificacion_contraste_vecinal/protocolo.md",
               "notebooks/experimentos/exp_10_verificacion_contraste_vecinal/registro_previo.json"]
    registro = {"id": "EXP_10", "inicio_utc": inicio, "fin_utc": datetime.now(timezone.utc).isoformat(), "segundos": round(time.time() - t0, 1),
                "python": platform.python_version(), "paquetes": {k: md.version(k) for k in ("numpy", "pandas", "scikit-learn")},
                "insumos_sha256": {p: sha(RAIZ / p) for p in insumos}, "salidas_sha256": {n: sha(salida / n) for n in [*salidas, "nulos_resumen.json"]},
                "presupuesto": {**CUENTA, "nulos_sorteos": {k: N_PERM for k in SEMILLAS}, "lecturas_notebook": 0, "predicciones_finales": 0},
                "control_fuga_identico": True, "decision_regla": dec, "confirmacion_independiente": False}
    (salida / "registro_ejecucion.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False) + "\n")
    pd.set_option("display.width", 220)
    print(met[met.escenario == "SEEN135"].round(5).to_string(index=False))
    print(reg.T.to_string())
    print({k: {kk: vv for kk, vv in v.items() if kk != "observado_familia"} for k, v in nul_r.items()})
    print("Decisión por regla:", dec)
    print(json.dumps(registro["presupuesto"], indent=1))


if __name__ == "__main__":
    main()
