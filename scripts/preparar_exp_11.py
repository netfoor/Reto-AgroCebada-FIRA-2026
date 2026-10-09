"""EXP_11, preparación sin calcular mezclas: copia trazable de insumos, verificación de componentes,
concordancia con EXP_10 y con las particiones, y reproducción independiente de J (Jared, procedimiento
completo) desde sus variables sin estandarizar, incluida una prueba de fuga de etiquetas.

    uv run --locked --all-groups python scripts/preparar_exp_11.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from combinacion_11 import CLAVE, ID, metricas, validar_componentes, validar_particiones

RAIZ = Path(__file__).resolve().parents[1]
TMP = RAIZ / "tmp_comparacion_jared"
SAL = RAIZ / "data/exp_11_combinacion_modelos"
ZIP_JARED = RAIZ.parent / "jared/para el equipo.zip"
E10 = RAIZ / "resultados/exp_10_verificacion_contraste_vecinal/registrada"
PART = {"historicas": "data/validacion_03/particiones_externas.csv", "nuevas": "data/exp_09_fuentes_externas/particiones_externas_nuevas.csv"}
FAM = ["clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17"]
NOMBRES = {"MIX": "MIX", "MUN (media municipal)": "MUN", "MIX + K1 corregido": "K", "Jared procedimiento completo": "J"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def info(p):
    st = Path(p).stat()
    return {"sha256": sha(p), "bytes": st.st_size, "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}


def copiar_procedencia():
    dst = SAL / "procedencia_jared"
    (dst / "variables_jared").mkdir(parents=True, exist_ok=True)
    reg = {"zip_jared": {"ruta": "../jared/para el equipo.zip", **info(ZIP_JARED)}, "archivos": {}}
    z = zipfile.ZipFile(ZIP_JARED)
    miembros = {Path(n).name: n for n in z.namelist() if "03_hipotesis_y_variables/variables/" in n or n.endswith("01_datos/preparados/base_197_ubicacion.csv")}
    for f in sorted((TMP / "variables_jared").iterdir()) + [TMP / "base_197_ubicacion.csv"]:
        destino = dst / ("variables_jared" if f.parent.name == "variables_jared" else "") / f.name
        shutil.copy2(f, destino)
        m = miembros.get(f.name)
        igual_zip = m is not None and hashlib.sha256(z.read(m)).hexdigest() == sha(f)
        if not igual_zip:
            raise ValueError(f"{f.name}: no coincide con su miembro en el ZIP de Jared")
        reg["archivos"][str(destino.relative_to(RAIZ))] = {**info(destino), "origen_tmp": str(f.relative_to(RAIZ)), "miembro_zip": m, "igual_al_zip": True}
    for f in ["comparar.py", "metricas.py", "elegidas.csv", "oof_comparacion.csv"]:
        shutil.copy2(TMP / f, dst / f)
        reg["archivos"][str((dst / f).relative_to(RAIZ))] = {**info(dst / f), "origen_tmp": f"tmp_comparacion_jared/{f}", "mtime_tmp_utc": info(TMP / f)["mtime_utc"]}
    return reg


def variables_jared_crudas():
    """148 candidatas sin estandarizar (las predicciones de J son invariantes a esa transformación afín)."""
    base = SAL / "procedencia_jared/variables_jared"
    F, hip = None, []
    for f in FAM:
        d = pd.read_csv(base / f"{f}_features.csv")
        F = d if F is None else F.merge(d, on=ID, how="left")
        h = pd.read_csv(base / f"{f}_hipotesis.csv", dtype=str, keep_default_na=False)
        hip.append(h)
    hip = pd.concat(hip)
    hip = hip[(hip.spec == "lineal") & (hip.id != "HC2")]
    lin = []
    for v in hip.variables:
        for x in re.sub(r"\s+", "", v).split(";"):
            if x and x not in lin:
                lin.append(x)
    if len(lin) != 148:
        raise ValueError("No son 148 candidatas")
    return F.set_index(ID)[lin], lin


def jared_completo(Fx, grupo, y, tr, va):
    """Implementación independiente: correlación dentro de grupo con etiquetas de entrenamiento,
    luego OLS con nivel por grupo y una pendiente común."""
    gtr, gva = grupo.loc[tr].to_numpy(), grupo.loc[va].to_numpy()
    ytr = y.loc[tr].to_numpy(float)
    X = Fx.loc[tr].to_numpy(float)
    niveles = sorted(set(gtr))
    yc = ytr.copy()
    Xc = X.copy()
    for g in niveles:
        m = gtr == g
        yc[m] -= ytr[m].mean()
        Xc[m] -= X[m].mean(0)
    r = (Xc * yc[:, None]).sum(0) / np.sqrt(np.maximum((Xc ** 2).sum(0) * (yc ** 2).sum(), 1e-24))
    j = int(np.argmax(np.abs(r)))
    D = lambda x, g: np.column_stack([(g[:, None] == np.array(niveles)[None]).astype(float), x[:, None]])  # noqa: E731
    b = np.linalg.lstsq(D(X[:, j], gtr), ytr, rcond=None)[0]
    return D(Fx.loc[va].to_numpy(float)[:, j], gva) @ b, Fx.columns[j]


def main():
    SAL.mkdir(parents=True, exist_ok=True)
    proc = copiar_procedencia()
    # --- componentes: MIX, MUN, K desde EXP_10; J desde la comparación temporal
    e10 = pd.read_csv(E10 / "predicciones_oof.csv")
    comp10 = e10[e10.modelo.isin(["MIX", "MUN", "K1_corregido"])].replace({"modelo": {"K1_corregido": "K"}})
    tmp = pd.read_csv(SAL / "procedencia_jared/oof_comparacion.csv")
    j = tmp[tmp.modelo.eq("Jared procedimiento completo")].assign(modelo="J")
    cols = CLAVE + ["Municipio", "municipio_visto", "modelo", "predicho", "observado"]
    comp = pd.concat([comp10[cols], j[cols]], ignore_index=True).sort_values(CLAVE + ["modelo"]).reset_index(drop=True)
    validar_componentes(comp)
    externas = {cj: pd.read_csv(RAIZ / p) for cj, p in PART.items()}
    validar_particiones(comp, externas)
    # Concordancia de MIX/MUN/K de la comparación temporal con EXP_10
    t = tmp[tmp.modelo.isin(NOMBRES)].replace({"modelo": NOMBRES})
    cmp = t.merge(comp, on=CLAVE + ["modelo"], suffixes=("_tmp", ""))
    dif_tmp = float((cmp.predicho_tmp - cmp.predicho).abs().max())
    if len(cmp) != len(comp) or dif_tmp > 1e-12:
        raise ValueError("La comparación temporal no coincide con EXP_10")
    # Métricas de referencia frente a EXP_10 y frente a lo reportado
    met10 = pd.read_csv(E10 / "metricas.csv")
    dif_met = 0.0
    nombres10 = {"MIX": "MIX", "MUN": "MUN", "K": "K1_corregido"}
    for (cj, m), g in comp[comp.municipio_visto & comp.modelo.isin(nombres10)].groupby(["conjunto", "modelo"]):
        r = met10[(met10.conjunto == cj) & (met10.escenario == "SEEN135") & (met10.modelo == nombres10[m])].iloc[0]
        mm = metricas(g.observado, g.predicho)
        dif_met = max(dif_met, abs(mm["RMSE"] - r.RMSE), abs(mm["MAE"] - r.MAE))
    j_met = {cj: metricas(g.observado, g.predicho) for cj, g in comp[comp.municipio_visto & comp.modelo.eq("J")].groupby("conjunto")}
    reportado = {"historicas": (0.4835, 0.3315), "nuevas": (0.4821, 0.3314)}
    if dif_met > 1e-12 or any(abs(round(j_met[c]["RMSE"], 4) - v[0]) > 0 or abs(round(j_met[c]["MAE"], 4) - v[1]) > 0 for c, v in reportado.items()):
        raise ValueError("Métricas de referencia no reproducidas")
    # --- reproducción independiente de J y prueba de fuga
    Fx, _ = variables_jared_crudas()
    grupo = pd.read_csv(SAL / "procedencia_jared/base_197_ubicacion.csv").set_index(ID).grupo
    y = comp.drop_duplicates(ID).set_index(ID).observado
    if Fx.loc[y.index].isna().any().any():
        raise ValueError("Faltantes en variables de Jared para etiquetadas")
    rep_max, fuga_max, elegidas, n_ajustes = 0.0, 0.0, [], 0
    jw = comp[comp.modelo.eq("J")].set_index(CLAVE).predicho
    for cj, e in externas.items():
        for (r, f), g in e.groupby(["repeticion", "pliegue"]):
            tr = g.loc[g.rol.eq("entrenamiento"), ID].to_numpy()
            va = g.loc[g.rol.eq("validacion"), ID].to_numpy()
            p, var = jared_completo(Fx, grupo, y, tr, va)
            y2 = y.copy()
            y2.loc[va] = 99.0                          # etiquetas de validación sustituidas
            p2, var2 = jared_completo(Fx, grupo, y2, tr, va)
            n_ajustes += 2
            guardado = jw.loc[[(cj, r, f, i) for i in va]].to_numpy()
            rep_max = max(rep_max, float(np.abs(p - guardado).max()))
            fuga_max = max(fuga_max, float(np.abs(p - p2).max()) + (var != var2))
            elegidas.append({"conjunto": cj, "repeticion": int(r), "pliegue": int(f), "variable": var})
    if rep_max > 1e-9 or fuga_max != 0:
        raise ValueError("J no reproducido o depende de etiquetas de validación")
    comp.to_csv(SAL / "oof_componentes.csv", index=False, float_format="%.17g")
    pd.DataFrame(elegidas).to_csv(SAL / "j_variables_elegidas.csv", index=False)
    ver = {"fecha_utc": datetime.now(timezone.utc).isoformat(), "mezclas_calculadas": False,
           "filas_por_modelo": int(len(comp) / 4), "modelos": ["MIX", "MUN", "J", "K"],
           "claves_unicas_y_alineadas": True, "etiquetas_municipio_mascara_iguales": True, "particiones_concordantes": True,
           "dif_max_tmp_vs_exp10": dif_tmp, "dif_max_metricas_referencia_vs_exp10": dif_met,
           "metricas_J_reproducen_lo_reportado": {c: j_met[c] for c in j_met},
           "J_reproducido_independiente_desde_variables_sin_estandarizar": True, "dif_max_J_reproducido": rep_max,
           "J_invariante_a_etiquetas_de_validacion": True, "ajustes_de_verificacion_J": n_ajustes,
           "variable_elegida_conteo": pd.DataFrame(elegidas).groupby(["conjunto", "variable"]).size().reset_index(name="n").to_dict("records"),
           "transformacion_X_comparacion_original": "En comparar.py, las 148 variables se estandarizaron con media y desviación de las 197 parcelas (solo X), como en el script de Jared. La correlación y el OLS con niveles por grupo son invariantes a esa transformación afín; la reproducción sin estandarizar lo confirma. No se modifica.",
           "procedencia": proc, "oof_componentes_sha256": sha(SAL / "oof_componentes.csv"),
           "exp10_predicciones_sha256": sha(E10 / "predicciones_oof.csv")}
    (SAL / "verificacion_insumos.json").write_text(json.dumps(ver, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in ver.items() if k not in ("procedencia",)}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
