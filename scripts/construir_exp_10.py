"""EXP_10: lector autónomo de la verificación del contraste vecinal, sin reajustar modelos.

    uv run --locked --all-groups python scripts/construir_exp_10.py

Prepara la tabla de etiquetas y la configuración de insumos con hashes, y genera el cuaderno.
El entrenamiento se reproduce con scripts/factibilidad_10.py y scripts/experimento_10.py.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import io
import json
import zipfile
import zlib
from pathlib import Path
from textwrap import dedent

import nbformat
import pandas as pd

BASE = "notebooks/experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb"
BASE_SHA = "8bb5b06266e4b7f3ed3c4761df3a93483a12d003bf4db4ba73a7bea4c9961a66"
CONFIG = "config/exp_10_verificacion_contraste_vecinal.json"
D10 = "data/exp_10_verificacion_contraste_vecinal/"
R10 = "resultados/exp_10_verificacion_contraste_vecinal/registrada/"
N10 = "notebooks/experimentos/exp_10_verificacion_contraste_vecinal/"
INSUMOS = {
    "capturas": D10 + "capturas_receta.csv", "metadatos": D10 + "metadatos.csv", "etiquetas": D10 + "etiquetas_138.csv",
    "variables_control": D10 + "variables_197.csv", "invariancia_control": D10 + "invariancia.csv",
    "cobertura_control": D10 + "cobertura.csv", "diagnosticos_X": D10 + "diagnosticos_X.json",
    "hist_externas": "data/validacion_03/particiones_externas.csv", "hist_internas": "data/validacion_03/particiones_internas.csv",
    "nuevas_externas": "data/exp_09_fuentes_externas/particiones_externas_nuevas.csv",
    "nuevas_internas": "data/exp_09_fuentes_externas/particiones_internas_nuevas.csv",
    "oof": R10 + "predicciones_oof.csv", "parametros": R10 + "parametros_exteriores.csv", "metricas_control": R10 + "metricas.csv",
    "repeticiones_control": R10 + "repeticiones.csv", "municipios_control": R10 + "municipios.csv", "zonas_control": R10 + "zonas.csv",
    "concentracion_control": R10 + "concentracion_parcelas.csv", "sensibilidades_control": R10 + "sensibilidades.csv",
    "nulos_resumen": R10 + "nulos_resumen.json", "nulos_sorteos": R10 + "nulos_sorteos.csv", "reglas_control": R10 + "reglas.csv",
    "soporte_control": R10 + "soporte_59.csv", "registro_ejecucion": R10 + "registro_ejecucion.json",
    "registro_previo": N10 + "registro_previo.json", "verificacion_independiente": N10 + "verificacion_independiente.json",
    "modelo_fuente": "scripts/modelo_10.py", "experimento_fuente": "scripts/experimento_10.py",
}


def preparar(raiz: Path):
    """Etiquetas desde el ZIP verificado y configuración de insumos con tamaño y SHA-256."""
    zp = raiz / "data/raw/DataSet.zip"
    if hashlib.sha256(zp.read_bytes()).hexdigest() != "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5":
        raise ValueError("DataSet.zip distinto")
    z = zipfile.ZipFile(zp)
    e = pd.read_csv(io.BytesIO(z.read("DATASET_RETO_AGRO_2026/ID_area_rendimiento_70_30_Reto_AgroCebada.csv")), encoding="utf-8-sig")
    e[["ID_POLIGONO", "RENDIMIENTO_T_HA"]].dropna().sort_values("ID_POLIGONO").to_csv(raiz / INSUMOS["etiquetas"], index=False)
    cfg = {"id": "EXP_10", "modo": "lector_resultados_experimento_registrado_sin_ajustes", "fecha_original": "2026-10-08",
           "poblacion_principal": "SEEN135", "poblacion_secundaria": "FULL138", "ajustes_actuales_lector": 0, "insumos": {}}
    for k, ruta in INSUMOS.items():
        b = (raiz / ruta).read_bytes()
        cfg["insumos"][k] = {"ruta_local": ruta, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "uso": k, "origen": ruta}
    (raiz / CONFIG).write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return cfg


def cargar(raiz, cfg):
    salida = {}
    for k, c in cfg["insumos"].items():
        b = (raiz / c["ruta_local"]).read_bytes()
        if not 0 < len(b) <= 2 * 1024 * 1024 or len(b) != c["bytes"] or hashlib.sha256(b).hexdigest() != c["sha256"]:
            raise ValueError(f"Insumo distinto o demasiado grande: {k}")
        salida[k] = {**c, "bytes_zlib_base64": base64.b64encode(zlib.compress(b, 9)).decode()}
    return salida


def construir(raiz: Path):
    cfg = preparar(raiz)
    reg = cargar(raiz, cfg)
    if hashlib.sha256((raiz / BASE).read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError("Cambió el cuaderno de soporte verificado")
    anterior = nbformat.read(raiz / BASE, as_version=4)
    tags = {t: c for c in anterior.cells for t in c.metadata.get("tags", [])}
    cells = []

    def texto(s):
        cells.append(nbformat.v4.new_markdown_cell(dedent(s).strip()))

    def codigo(s, tag, titulo=None):
        c = nbformat.v4.new_code_cell(dedent(s).strip())
        c.metadata["tags"] = [tag]
        if titulo:
            c.source = f'# @title {titulo} {{ display-mode: "form" }}\n' + c.source
            c.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        cells.append(c)

    def reutilizar(tag):
        c = copy.deepcopy(tags[tag])
        c.outputs, c.execution_count = [], None
        c.metadata.pop("execution", None)
        cells.append(c)

    texto("""
    # EXP_10. ¿Sigue mejorando K1 cuando el corte temporal se implementa bien?

    **CRISP-DM: volver a preparar los datos y evaluar de nuevo.** EXP_08 encontró que
    corregir MIX con el **contraste vecinal** de la integral NDVI Planet reducía el RMSE.
    EXP_09 fijó esa variable **cortada al 31 de octubre** como K1. Mejoró a MIX en dos
    juegos de particiones, pero no superó su umbral de familia (p ≈ 0.13 > 0.10), y su
    regla recomendó **MIX**.

    **Por qué se repite K1.** Una revisión encontró que el corte estaba mal implementado.
    La curva se suavizaba e interpolaba **con todo el año** y se recortaba después, así que
    capturas de noviembre podían cambiar valores de octubre. Este cuaderno corrige solo eso
    y vuelve a medir.

    **Lectura de la corrida registrada.** Reconstruye ambas variables desde las capturas,
    verifica la invariancia temporal y evalúa las predicciones guardadas. **Cero ajustes
    al ejecutarlo.** No genera las 59 predicciones. No es una confirmación independiente:
    K1 se eligió después de explorar estas mismas etiquetas.

    **Recorrido:** una parcela → las 197 → comparación en dos juegos de particiones →
    territorio y concentración → nulos → decisión y límites.
    """)
    texto("""
    ## 1. Fuentes y alcance

    | Entrada | Se hace aquí | No se hace aquí |
    | --- | --- | --- |
    | 32,257 capturas Planet de la receta (NDVI finito, nube ≤20 %) | Reconstruir las integrales publicada y corregida; probar la invariancia | Leer píxeles ni cambiar la receta |
    | Centroides UTM y conjunto de las 197 parcelas | Vecinos a <1 km y cobertura, solo con X | Usar rendimiento para elegir la receta |
    | Particiones históricas y nuevas | Verificar correspondencia con las predicciones guardadas | Generar particiones nuevas |
    | Predicciones OOF, parámetros y nulos de la corrida | Comprobar la ecuación, recalcular métricas, reglas y concentración | Reentrenar ni recalcular los nulos |

    La celda técnica verifica tamaño y SHA-256 de cada insumo. El código de la corrida
    (`modelo_10.py`, `experimento_10.py`) queda como texto comentado inspeccionable: **no se
    ejecuta**. Para reproducir el entrenamiento, ver la sección 9.
    """)
    for tag in ["soporte-colab", "preparar-colab", "entorno"]:
        reutilizar(tag)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    comentarios = []
    for k in ["modelo_fuente", "experimento_fuente"]:
        fuente = (raiz / cfg["insumos"][k]["ruta_local"]).read_text()
        comentarios.append("\n# Fuente completa solo para inspección: " + k + "\n" + "\n".join("#| " + x for x in fuente.splitlines()))
    codigo("INSUMOS_INCRUSTADOS = " + repr(reg) + "\n\n" + decoder +
           "\n\ndef csv_insumo(k):\n    return leer_csv(k, INSUMOS_INCRUSTADOS[k]['uso'])\n"
           "def json_insumo(k):\n    return json.loads(bytes_insumo(k, INSUMOS_INCRUSTADOS[k]['uso']))\n" + "\n".join(comentarios),
           "insumos-tecnicos", "Insumos verificados y código de la corrida para inspección; no se entrena")
    codigo("""
    ID, Y = "ID_POLIGONO", "RENDIMIENTO_T_HA"
    capturas = csv_insumo("capturas")
    meta = csv_insumo("metadatos")
    etiquetas = csv_insumo("etiquetas")
    variables_control = csv_insumo("variables_control").set_index(ID)
    QA = json_insumo("diagnosticos_X")
    PRE = json_insumo("registro_previo")
    REG = json_insumo("registro_ejecucion")
    VER = json_insumo("verificacion_independiente")
    assert QA["usa_rendimientos"] is False and QA["ajustes_modelos"] == 0
    assert len(meta) == 197 and meta[ID].is_unique and len(etiquetas) == 138
    assert not any("RENDIMIENTO" in c for c in list(capturas) + list(meta))
    assert len(capturas) == 32257 and capturas.porcentaje_nubosidad.le(20).all() and np.isfinite(capturas.ndvi_promedio).all()
    assert PRE["scores_nuevos_antes_de_este_registro"] == 0 and PRE["confirmacion_independiente"] is False
    assert PRE["registrado_utc"] < REG["inicio_utc"]
    assert VER["predicciones_reproducidas"] and VER["replica_determinista"] and VER["N0_reproduce_p_EXP09"]
    print("Registro previo:", PRE["registrado_utc"], "| corrida:", REG["inicio_utc"], "| verificación independiente:", VER["verificado_utc"])
    """, "fuentes-visibles")

    texto("""
    ## 2. Una parcela: cortar antes o después de suavizar

    La receta es la misma de EXP_08/09: mediana diaria → mediana móvil centrada de 15 días
    (±7, mínimo 3) → interpolación solo interior → base abril–mayo → umbral del 50 % →
    integral entre los cruces.

    * **Publicada:** suaviza con capturas de todo el año y después corta en el día 304.
    * **Corregida:** descarta las capturas posteriores al 31/10/2025 y limita la rejilla a
      los días 1–304 **antes** de suavizar. Nada más cambia.

    Mostramos la parcela con **mayor cambio de integral**, elegida solo con X.
    """)
    codigo("""
    CORTE = 304

    def curva(doy, valores, dias):
        s = pd.Series(np.asarray(valores, float)).groupby(np.asarray(doy, int)).median().reindex(np.asarray(dias, int))
        return s.rolling(15, center=True, min_periods=3).median().interpolate(limit_area="inside")

    def integral(c, fin_max=CORTE):
        c = c.loc[:fin_max]; base = c.loc[91:150].median(); temporada = c.loc[150:min(330, fin_max)]
        if temporada.isna().all() or not np.isfinite(base):
            return np.nan
        pico, dia_pico = temporada.max(), temporada.idxmax(); umbral = base + 0.5 * (pico - base)
        subida = c.loc[150:dia_pico]; inicio = subida[subida >= umbral].index.min()
        bajada = c.loc[dia_pico:fin_max]; fin = bajada[bajada < umbral].index.min() if (bajada < umbral).any() else fin_max
        return float((c.loc[inicio:fin] - base).clip(lower=0).sum())

    def integrales(cap, receta):
        c = cap.assign(doy=pd.to_datetime(cap.fecha).dt.dayofyear)
        if receta == "corregida":
            c = c[c.doy <= CORTE]; dias = np.arange(1, CORTE + 1)
        else:
            dias = np.arange(1, 366)
        return pd.Series({p: integral(curva(g.doy, g.ndvi_promedio, dias)) for p, g in c.groupby(ID)}, dtype=float)

    I_pub, I_cor = integrales(capturas, "publicada"), integrales(capturas, "corregida")
    ejemplo = (I_cor - I_pub).abs().idxmax()
    g = capturas[capturas[ID].eq(ejemplo)].assign(doy=lambda d: pd.to_datetime(d.fecha).dt.dayofyear)
    c_pub = curva(g.doy, g.ndvi_promedio, np.arange(1, 366)); c_cor = curva(g[g.doy <= CORTE].doy, g[g.doy <= CORTE].ndvi_promedio, np.arange(1, CORTE + 1))
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.8))
    for a, (x0, x1) in zip(ax, [(1, 365), (250, 335)]):
        a.scatter(g.doy, g.ndvi_promedio, s=10, c=np.where(g.doy > CORTE, "#c0392b", "#9aa5b3"), label="capturas (rojo: después del 31/oct)")
        a.plot(c_pub.index, c_pub, color="#7f8c8d", lw=2, label="publicada: suaviza con todo el año")
        a.plot(c_cor.index, c_cor, color="#1f5f8b", lw=2, ls="--", label="corregida: corta antes de suavizar")
        a.axvline(CORTE, color="k", lw=0.8); a.set_xlim(x0, x1); a.set_xlabel("día del año 2025")
    ax[0].set_title(f"{ejemplo}: curva completa"); ax[1].set_title("Zoom al final de octubre"); ax[1].legend(fontsize=7)
    plt.tight_layout(); plt.show()
    print(f"{ejemplo}: integral publicada {I_pub[ejemplo]:.3f}, corregida {I_cor[ejemplo]:.3f}, diferencia {I_cor[ejemplo]-I_pub[ejemplo]:+.3f} NDVI·día")
    """, "parcela-visible")
    texto("""
    En los días previos al corte, la curva publicada usa la mediana de una ventana que llega
    a noviembre. La corregida solo ve capturas hasta el 31 de octubre. La diferencia es
    pequeña en la mayoría de parcelas, pero **no es cero**, y en principio podría cambiar
    qué parcela queda por encima o por debajo de sus vecinas.
    """)

    texto("""
    ## 3. Las 197 parcelas: cuánto cambia, cobertura y vecinos

    El contraste es la integral propia menos la mediana de las parcelas (de las 197) a menos
    de 1 km, con ≥2 vecinas. La regla publicada cuenta vecinas *geométricas*, y su mediana
    omite valores ausentes. Por eso podría basarse en una sola vecina válida. Se comprueba si
    ocurre.
    """)
    codigo("""
    xy = meta[["x_m", "y_m"]].to_numpy(float); ids = meta[ID].to_numpy()
    dist = np.linalg.norm(xy[:, None] - xy[None], axis=2)
    VEC = {p: ids[(dist[i] < 1000) & (dist[i] > 0)] for i, p in enumerate(ids)}

    def contraste(serie):
        out = {}
        for p, v in VEC.items():
            vals = serie.reindex(v).to_numpy(float)
            out[p] = serie[p] - np.nanmedian(vals) if len(v) >= 2 and np.isfinite(serie[p]) and np.isfinite(vals).any() else np.nan
        return pd.Series(out, dtype=float)

    K_pub, K_cor = contraste(I_pub.reindex(ids)), contraste(I_cor.reindex(ids))
    for nombre, x in [("integral_publicada", I_pub), ("integral_corregida", I_cor), ("K1_publicado", K_pub), ("K1_corregido", K_cor)]:
        np.testing.assert_allclose(x.reindex(variables_control.index), variables_control[nombre], atol=1e-12, rtol=0, equal_nan=True)
    vecinas_finitas = pd.Series({p: int(np.isfinite(I_cor.reindex(v)).sum()) for p, v in VEC.items()})
    geom = pd.Series({p: len(v) for p, v in VEC.items()})
    oculta = meta.set_index(ID).CONJUNTO.eq("PREDICCION")
    dI, dK = I_cor.reindex(ids) - I_pub.reindex(ids), K_cor - K_pub
    resumen_cambio = pd.DataFrame([{"grupo": n, "parcelas": int(m.sum()), "integrales que cambian": int((dI[m].abs() > 1e-12).sum()),
                                    "contrastes disponibles": int(K_cor[m].notna().sum()), "contrastes que cambian": int((dK[m].abs() > 1e-12).sum()),
                                    "|Δ contraste| mediana": float(dK[m].abs().median()), "|Δ contraste| máx.": float(dK[m].abs().max())}
                                   for n, m in [("etiquetadas", ~oculta), ("59 ocultas", oculta), ("todas", oculta | ~oculta)]]).set_index("grupo")
    display(resumen_cambio.round(4))
    print(f"Spearman contraste publicado–corregido: {K_pub.corr(K_cor, method='spearman'):.4f}")
    print("Contrastes con ≥2 vecinas geométricas pero <2 vecinas finitas:", int(((geom >= 2) & (vecinas_finitas < 2)).sum()))
    assert (dI.abs() > 1e-12).sum() == 130 and (dK.abs() > 1e-12).sum() == 131 and K_cor.notna().sum() == 158
    assert ((geom >= 2) & (vecinas_finitas < 2)).sum() == 0
    """, "generalizacion-visible")
    texto("""
    **Resultado.** Cambian 130 de 197 integrales y 131 de 158 contrastes. La cobertura es la
    misma: 108 etiquetadas y 50 ocultas tienen contraste. Los cambios son pequeños frente a
    la escala de la variable, y el orden casi no cambia (Spearman ≈ 0.998). **Ningún
    contraste se apoya en una sola vecina válida**, así que la regla de vecinos no necesitó
    precisarse.

    **Prueba de invariancia.** La receta corregida no debe depender de nada posterior al
    corte. Cambiamos, borramos y añadimos capturas posteriores al 31/oct y recalculamos.
    """)
    codigo("""
    post = pd.to_datetime(capturas.fecha).dt.dayofyear > CORTE
    rng = np.random.default_rng(20261008)
    escenarios = {"cambiar_valores_posteriores": capturas.assign(ndvi_promedio=np.where(post, rng.uniform(-1, 1, len(capturas)), capturas.ndvi_promedio)),
                  "borrar_posteriores": capturas[~post],
                  "añadir_posteriores": pd.concat([capturas, pd.DataFrame({ID: capturas[ID].unique(), "fecha": "2025-11-02", "ndvi_promedio": 0.95, "porcentaje_nubosidad": 0.0})], ignore_index=True)}
    inv = pd.DataFrame([{"escenario": n, "corregida: integrales que cambian": int((integrales(c, "corregida").reindex(I_cor.index) != I_cor).sum()),
                         "publicada: integrales que cambian": int((integrales(c, "publicada").reindex(I_pub.index) != I_pub).sum())} for n, c in escenarios.items()])
    display(inv)
    assert inv["corregida: integrales que cambian"].eq(0).all() and inv["publicada: integrales que cambian"].gt(0).all()
    """, "invariancia-visible")

    texto("""
    ## 4. Comparación en dos juegos de particiones

    | Procedimiento | Qué es |
    | --- | --- |
    | MUN / MIX | Referencias con receta fija (MIX = 0.5 media municipal + 0.5 IDW k=20) |
    | K1_publicado | MIX + β·z con la variable de EXP_09: **control de reproducción** |
    | K1_corregido | MIX + β·z con el corte bien hecho |

    β = Σz̃e/(Σz̃² + 10). Los residuos e de MIX se obtienen dentro del entrenamiento con las
    particiones internas, y z̃ se estandariza con mediana y desviación del entrenamiento.
    Sin contraste, la parcela recibe MIX. Primero comprobamos que cada predicción guardada
    cumple esa ecuación con los parámetros guardados. Eso es aritmética, no reentrenamiento.
    """)
    codigo("""
    oof = csv_insumo("oof"); par = csv_insumo("parametros"); varc = variables_control
    PARTES = {"historicas": ("hist_externas", "hist_internas"), "nuevas": ("nuevas_externas", "nuevas_internas")}
    for cj, (ke, ki) in PARTES.items():
        ext = csv_insumo(ke); o = oof[oof.conjunto.eq(cj)]
        assert len(o) == 4 * 1380 and set(o.modelo) == {"MUN", "MIX", "K1_publicado", "K1_corregido"}
        val = ext[ext.rol.eq("validacion")].set_index(["repeticion", "pliegue", ID]).index
        for m, q in o.groupby("modelo"):
            assert set(q.set_index(["repeticion", "pliegue", ID]).index) == set(val)
    max_dif = 0.0
    for (cj, r, f), q in oof.groupby(["conjunto", "repeticion", "pliegue"]):
        mixp = q[q.modelo.eq("MIX")].set_index(ID).predicho
        for k in ["K1_publicado", "K1_corregido"]:
            p = par[(par.conjunto == cj) & (par.repeticion == r) & (par.pliegue == f) & (par.modelo == k)].iloc[0]
            z = varc.loc[mixp.index, k].to_numpy(float)
            esperado = mixp.to_numpy() + np.where(np.isnan(z), 0.0, p.beta * (z - p.mediana) / p.escala)
            max_dif = max(max_dif, float(np.abs(q[q.modelo.eq(k)].set_index(ID).loc[mixp.index, "predicho"].to_numpy() - esperado).max()))
    print(f"Ecuación MIX + β·z reproducida en 100 pliegues exteriores × 2 candidatos = 200 ecuaciones; diferencia máxima {max_dif:.1e}")
    assert max_dif < 1e-12
    oof = oof.merge(etiquetas.rename(columns={Y: "obs"}), on=ID, validate="many_to_one")
    assert np.allclose(oof.obs, oof.observado)

    def metr(g):
        e = g.predicho - g.obs; sst = ((g.obs - g.obs.mean()) ** 2).sum()
        return pd.Series({"n_oof": len(g), "RMSE": np.sqrt((e ** 2).mean()), "MAE": e.abs().mean(), "R2": 1 - (e ** 2).sum() / sst})

    ESC = {(cj, "SEEN135"): oof[oof.conjunto.eq(cj) & oof.municipio_visto] for cj in PARTES} | {(cj, "FULL138"): oof[oof.conjunto.eq(cj)] for cj in PARTES}
    met = pd.concat({k: v.groupby("modelo").apply(metr, include_groups=False) for k, v in ESC.items()}, names=["conjunto", "escenario", "modelo"])
    ctrl = csv_insumo("metricas_control").set_index(["conjunto", "escenario", "modelo"])
    np.testing.assert_allclose(met[["RMSE", "MAE", "R2"]].to_numpy(), ctrl.loc[met.index, ["RMSE", "MAE", "R2"]].to_numpy(), atol=1e-12, rtol=0)
    tabla = met.xs("SEEN135", level="escenario")[["RMSE", "MAE", "R2"]].unstack("conjunto")
    display(tabla.reindex(["MIX", "K1_publicado", "K1_corregido", "MUN"]).round(5))
    """, "comparacion-visible")
    codigo("""
    rep = pd.concat({cj: ESC[(cj, "SEEN135")].groupby(["modelo", "repeticion"]).apply(lambda g: np.sqrt(((g.predicho - g.obs) ** 2).mean()), include_groups=False).unstack("modelo")
                     for cj in PARTES}, names=["conjunto"])
    dif = pd.DataFrame({"K1c − MIX": rep.K1_corregido - rep.MIX, "K1c − K1pub": rep.K1_corregido - rep.K1_publicado, "K1pub − MIX": rep.K1_publicado - rep.MIX})
    resumen_pareado = dif.groupby("conjunto").agg(["mean", "min", "max", lambda s: int((s < 0).sum())]).rename(columns={"<lambda_0>": "reps<0"}, level=1)
    display(resumen_pareado.round(5))
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.2), sharey=True)
    for a, cj in zip(ax, PARTES):
        d = dif.loc[cj]; a.bar(d.index - 0.2, d["K1c − MIX"], 0.4, label="K1 corregido − MIX"); a.bar(d.index + 0.2, d["K1c − K1pub"], 0.4, label="K1 corregido − K1 publicado")
        a.axhline(0, color="k", lw=0.8); a.set_title(f"Particiones {cj}: ΔRMSE por repetición (SEEN135)"); a.set_xlabel("repetición")
    ax[0].legend(fontsize=8); plt.tight_layout(); plt.show()
    assert (dif["K1c − MIX"] < 0).all() and (dif["K1c − K1pub"] > 0).all()
    """, "pareado-visible")
    texto("""
    **Lectura.**

    * **K1 publicado reproduce EXP_09:** 0.4816 en particiones históricas y 0.4807 en nuevas.
    * **K1 corregido** baja el RMSE de MIX de 0.48720 a **0.48198** (históricas) y de 0.48567
      a **0.48096** (nuevas). Mejora a MIX en las 10 repeticiones de cada juego, y su MAE
      también queda por debajo del de MIX.
    * **Frente a K1 publicado, el corregido es algo peor en las 20 repeticiones.** La
      discrepancia temporal **inflaba** la ganancia, pero solo en ~0.0003–0.0004 t/ha, cerca
      de un 7 %. La mejora no dependía de ella.
    * En las particiones nuevas, la repetición menos favorable queda casi empatada con MIX
      (−0.0004). Las 10 repeticiones reutilizan las mismas 138 parcelas: **no son diez pruebas
      independientes.**
    """)

    texto("""
    ## 5. Dónde está la mejora: territorio y concentración

    Retirar parcelas se hace **solo al evaluar** (las mismas OOF), como sensibilidad. Nunca
    se reentrena sin ellas.
    """)
    codigo("""
    zonas = pd.concat({cj: ESC[(cj, "SEEN135")].assign(zona=lambda d: np.where(d.Municipio.eq("Chignahuapan"), "Chignahuapan", "resto"))
                      .groupby(["zona", "modelo"]).apply(lambda g: np.sqrt(((g.predicho - g.obs) ** 2).mean()), include_groups=False).unstack("modelo") for cj in PARTES}, names=["conjunto"])
    display(zonas[["MUN", "MIX", "K1_publicado", "K1_corregido"]].round(4))
    munis = csv_insumo("municipios_control").pivot_table(index=["conjunto", "Municipio"], columns="modelo", values="RMSE")
    display(munis[["MUN", "MIX", "K1_corregido"]].round(4))

    def sensibilidad(o, cand):
        w = o.pivot_table(index=[ID, "repeticion"], columns="modelo", values="predicho").join(o.groupby([ID, "repeticion"]).obs.first())
        dse = ((w[cand] - w.obs) ** 2 - (w.MIX - w.obs) ** 2).groupby(ID).sum().sort_values()
        filas = []
        for k in (0, 2, 5):
            ww = w[~w.index.get_level_values(ID).isin(dse.index[:k])]
            filas.append({"retiradas": k, "parcelas": ", ".join(dse.index[:k]), "ΔRMSE vs MIX": np.sqrt(((ww[cand] - ww.obs) ** 2).mean()) - np.sqrt(((ww.MIX - ww.obs) ** 2).mean())})
        return dse, pd.DataFrame(filas)

    sens = {}
    for cj in PARTES:
        dse, s = sensibilidad(ESC[(cj, "SEEN135")], "K1_corregido"); sens[cj] = s
        print(f"{cj}: cambio neto de SSE {dse.sum():+.3f}; mejoran {(dse < 0).sum()} parcelas, empeoran {(dse > 0).sum()}")
        display(s.round(5))
    ctrl = csv_insumo("sensibilidades_control")
    for cj, s in sens.items():
        c = ctrl[(ctrl.conjunto == cj) & (ctrl.candidato == "K1_corregido")].sort_values("retiradas_de_evaluacion")
        np.testing.assert_allclose(s["ΔRMSE vs MIX"], c.delta_RMSE, atol=1e-12, rtol=0)
    """, "concentracion-visible")
    texto("""
    **Resultado.**

    * La mejora aparece sobre todo en **Chignahuapan** (0.5736 → 0.5687 en particiones
      históricas), donde estaba la mayor parte del error, y también en Singuilucan y Almoloya.
    * En **Calpulalpan**, K1 corregido queda ligeramente peor que MIX. Fuera de
      Chignahuapan, MUN sigue siendo mejor que ambos.
    * **La ganancia está concentrada.** Sin las 2 parcelas más favorecidas (AGC_162 y
      AGC_172), sigue habiendo mejora, pero de solo ~0.001 t/ha. Sin las 5, se invierte en
      ambos juegos.
    """)

    texto("""
    ## 6. ¿Podría ser azar? Revisión del nulo de EXP_09 y un nulo espacial

    El estadístico es el mismo de EXP_09: **el menor RMSE SEEN entre seis candidatos** (K1,
    borde rojo, radar, AlphaEarth, historia y combinado). No se reduce la familia a un solo
    candidato. Cada nulo se ejecutó **una vez**, con semilla y tamaño fijados en el registro
    previo.

    | Nulo | Cómo genera variables sin relación con el rendimiento | Qué conserva | Qué no conserva |
    | --- | --- | --- | --- |
    | N0 | Permutación de filas dentro de municipio (EXP_09), con K1 publicado | Distribución y correlación entre columnas | Dependencia espacial fina; ubicación de los faltantes |
    | N1 | Igual que N0, con K1 corregido | Igual | Igual |
    | N2 | Aleatorización espectral de Moran: cambia los signos de los coeficientes en vectores propios de la vecindad de 1 km (Wagner y Dray, 2015) | Varianza, I de Moran, espectro espacial, correlaciones entre columnas y ubicación de faltantes | La forma exacta de la distribución marginal |

    **Por qué hace falta N2.** Los contrastes y los residuos de rendimiento tienen dependencia
    espacial a menos de 1 km (EXP_08). Suponer que cualquier asignación dentro del municipio
    es igual de probable **no está justificado**: destruye esa estructura y mueve los
    faltantes. N2 supone en cambio que, sin relación con el rendimiento, el campo es
    invariante a esos cambios de signo, lo que es razonable para un proceso espacial
    estacionario. **Tampoco es una prueba exacta.**
    """)
    codigo("""
    NUL = json_insumo("nulos_resumen"); sorteos = csv_insumo("nulos_sorteos")
    filas = []
    for n in ["N0", "N1", "N2"]:
        d = sorteos[sorteos.nulo.eq(n)]; r = NUL[n]; k = int((d.minimo_familia <= r["rmse_observado"]).sum())
        assert k == r["k"] and len(d) == 200
        filas.append({"nulo": n, "candidato": r["candidato"], "RMSE observado": r["rmse_observado"], "media del mínimo nulo": d.minimo_familia.mean(),
                      "percentil 5 nulo": d.minimo_familia.quantile(0.05), "k/N": k / 200, "(k+1)/(N+1)": (k + 1) / 201, "válido": r["valido"]})
    display(pd.DataFrame(filas).set_index("nulo").round(4))
    print("Conservación MSR verificada en 20 sorteos:", NUL["N2"]["conservacion_msr"])
    fig, ax = plt.subplots(1, 3, figsize=(13, 3), sharey=True)
    for a, n in zip(ax, ["N0", "N1", "N2"]):
        d = sorteos[sorteos.nulo.eq(n)]; a.hist(d.minimo_familia, bins=30, color="#9aa5b3")
        a.axvline(NUL[n]["rmse_observado"], color="#c0392b", lw=2, label=NUL[n]["candidato"]); a.axvline(0.48720, color="k", ls="--", label="MIX")
        a.set_title(n); a.legend(fontsize=7)
    plt.tight_layout(); plt.show()
    assert NUL["N0"]["p_k_sobre_N"] == 0.13
    """, "nulos-visible")
    texto("""
    **Resultado.**

    * **N0 reproduce exactamente el p = 0.13 de EXP_09.**
    * Con el corte corregido, el p de familia es **≈0.18 con la permutación municipal (N1)**
      y **≈0.13 con el nulo espacial (N2)**. Ambos quedan por encima del umbral registrado
      de 0.10.
    * N2 resultó *menos* exigente que N1 en estos datos. No asumimos que un nulo sea siempre
      más conservador que el otro: se reportan ambos y la regla exige los dos.
    * Ningún p-valor depende de repetir permutaciones: cada nulo se ejecutó una vez, con el
      tamaño fijado.
    """)

    texto("""
    ## 7. Regla de desarrollo de EXP_10 y decisión

    Fijada en el protocolo antes de los scores, en SEEN135 y en **ambos** juegos:
    **R1** RMSE < MIX; **R2** ≥8/10 repeticiones; **R3** MAE ≤ MIX; **R4** sin invertirse al
    retirar de la evaluación las 2 parcelas más favorecidas. **S**: p de familia ≤ 0.10 en N1
    y en N2. Cumplir R1–R4 significa "cumple los requisitos predictivos". Solo S
    hablaría de "evidencia estadística suficiente para adoptar".
    """)
    codigo("""
    reglas = csv_insumo("reglas_control").set_index("candidato")
    k = reglas.loc["K1_corregido"]
    tabla_reglas = pd.DataFrame({
        "históricas": [bool(tabla.loc["K1_corregido", ("RMSE", "historicas")] < tabla.loc["MIX", ("RMSE", "historicas")]),
                       int((dif.loc["historicas", "K1c − MIX"] < 0).sum()),
                       bool(tabla.loc["K1_corregido", ("MAE", "historicas")] <= tabla.loc["MIX", ("MAE", "historicas")]),
                       bool(sens["historicas"].iloc[1]["ΔRMSE vs MIX"] < 0)],
        "nuevas": [bool(tabla.loc["K1_corregido", ("RMSE", "nuevas")] < tabla.loc["MIX", ("RMSE", "nuevas")]),
                   int((dif.loc["nuevas", "K1c − MIX"] < 0).sum()),
                   bool(tabla.loc["K1_corregido", ("MAE", "nuevas")] <= tabla.loc["MIX", ("MAE", "nuevas")]),
                   bool(sens["nuevas"].iloc[1]["ΔRMSE vs MIX"] < 0)]},
        index=["R1 RMSE < MIX", "R2 repeticiones < MIX", "R3 MAE ≤ MIX", "R4 sin invertirse quitando 2"])
    display(tabla_reglas)
    REQ = bool(k.requisitos_predictivos); S = bool(k.S)
    assert REQ == bool(tabla_reglas.loc[["R1 RMSE < MIX", "R3 MAE ≤ MIX", "R4 sin invertirse quitando 2"]].all().all() and (tabla_reglas.loc["R2 repeticiones < MIX"] >= 8).all())
    print(f"Requisitos predictivos R1–R4: {REQ} | Evidencia estadística S (p_N1={k.p_N1:.3f}, p_N2={k.p_N2:.3f} ≤ 0.10): {S}")
    DECISION = REG["decision_regla"]; print("Decisión por la regla registrada:", DECISION)
    assert REQ and not S and DECISION.startswith("conservar_MIX")
    """, "regla-visible")
    texto("""
    ### Conclusión

    **a) Discrepancia técnica corregida.** Confirmada: la receta publicada usaba capturas de
    noviembre para valores de octubre. Afectaba 130/197 integrales y 131/158 contrastes. La
    receta corregida es invariante a todo lo posterior al 31/oct, y su cobertura es la misma.

    **b) Mejora predictiva observada.** Con el corte correcto, K1 sigue mejorando a MIX:
    ≈0.0052 t/ha de RMSE en particiones históricas y ≈0.0047 en nuevas (~1 %), con MAE no
    peor. La discrepancia inflaba la ganancia en ~7 %, pero no la explicaba.

    **c) Estabilidad y concentración.** La mejora es estable en dirección (20/20
    repeticiones), pero está concentrada. Depende sobre todo de pocas parcelas de
    Chignahuapan y se invierte al quitar las 5 más favorecidas. No hay evidencia estadística
    suficiente: el p de familia es 0.18 (N1) y 0.13 (N2).

    **d) Recomendación provisional.** Según la regla registrada, **conservar MIX como
    referencia oficial**. K1 corregido queda como **alternativa documentada que cumple los
    requisitos predictivos de desarrollo sin evidencia estadística suficiente**. Elegirlo es
    una decisión explícita del equipo, no un resultado de este experimento.
    """)

    texto("""
    ## 8. Las 59 ocultas: soporte, sin predecirlas
    """)
    codigo("""
    sop = csv_insumo("soporte_control")
    display(sop.groupby("Municipio").agg(ocultas=(ID, "size"), con_contraste=("K1_corregido", lambda s: int(s.notna().sum())),
                                         respaldo_MIX=("respaldo_MIX", "sum"), dentro_del_rango=("dentro_rango_etiquetadas", "sum")))
    nana = sop[sop.Municipio.str.startswith("Nanacamilpa")]
    display(nana)
    assert int(sop.K1_corregido.notna().sum()) == 50 and len(sop) == 59
    """, "soporte-visible")
    texto("""
    50 de 59 ocultas tienen contraste, todas dentro del rango observado en las etiquetadas.
    Las 9 restantes recibirían MIX sin corrección. Un rango univariado no garantiza soporte.

    **Nanacamilpa (AGC_120):** su municipio tiene una sola etiqueta, la parcela no tiene
    vecinas a <1 km y recibiría MIX sin corrección. SEEN135 no puntúa ningún caso
    equivalente, así que su error esperado no está medido por este experimento.
    """)

    texto("""
    ## 9. Cómo reproducir el entrenamiento

    Este cuaderno **no entrena**. Para reproducir la corrida desde la carpeta del proyecto:

    ```bash
    uv run --locked --all-groups python scripts/factibilidad_10.py           # solo X: variables, vecinos, invariancia
    uv run --locked --all-groups python scripts/experimento_10.py --salida resultados/exp_10_verificacion_contraste_vecinal/<nueva>
    uv run --locked --all-groups python scripts/verificar_exp_10_resultados.py
    uv run --locked --all-groups pytest -q tests/test_modelo_10.py
    ```

    `factibilidad_10.py` reescribe las salidas de factibilidad, que deben coincidir con los
    hashes de `registro_previo.json`. `experimento_10.py` no sobrescribe una carpeta
    existente. Presupuesto de una corrida:

    * 100 evaluaciones de referencias exteriores y 400 de MIX interno;
    * 200 ajustes de corrección;
    * el mismo número otra vez como control de fuga;
    * 180,900 ajustes de corrección en los nulos (3 × 201 × 300).

    La réplica de determinismo repitió todo y produjo 13 archivos idénticos.

    ## 10. Relación con EXP_08 y EXP_09

    * Los cuadernos y cierres de EXP_08/09 se conservan sin cambios. Sus cifras "hasta 31 oct"
      corresponden a la receta publicada, con la discrepancia.
    * **EXP_09 K2 (borde rojo) y K3 (radar)** usaban la misma construcción y comparten la
      discrepancia. Aquí solo se usan como miembros del nulo de familia; no se corrigieron
      ni se reevaluaron como candidatos.
    * El cierre de EXP_09 (recomendar MIX) se mantiene, y EXP_10 llega a la misma
      recomendación con la variable corregida.

    ## Referencias

    Wagner, H. H., & Dray, S. (2015). Generating spatially constrained null models for
    irregularly spaced data using Moran spectral randomization methods. *Methods in Ecology
    and Evolution, 6*(10), 1169–1178. https://doi.org/10.1111/2041-210X.12407

    Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent
    selection bias in performance evaluation. *Journal of Machine Learning Research, 11*,
    2079–2107. https://jmlr.org/papers/v11/cawley10a.html

    Jönsson, P., & Eklundh, L. (2004). TIMESAT—a program for analyzing time-series of satellite
    sensor data. *Computers & Geosciences, 30*(8), 833–845. https://doi.org/10.1016/j.cageo.2004.05.006
    """)
    codigo("""
    resumen = {"id": "EXP_10", "modo": "lector_resultados_experimento_registrado_sin_ajustes", "parcelas": 197, "etiquetas": 138,
               "capturas_incorporadas": int(len(capturas)), "integrales_cambian": int((dI.abs() > 1e-12).sum()),
               "contrastes_cambian": int((dK.abs() > 1e-12).sum()), "contrastes_disponibles": int(K_cor.notna().sum()),
               "invariancia_corregida": True, "ecuaciones_oof_reproducidas": 200, "juegos_particiones": 2,
               "oof_total": int(len(oof)), "metricas_recalculadas": True, "ajustes_actuales": 0, "predicciones_finales_generadas": 0,
               "requisitos_predictivos_K1_corregido": REQ, "evidencia_estadistica_K1_corregido": S, "decision_regla": DECISION,
               "rmse_seen": {f"{m}|{cj}": float(tabla.loc[m, ("RMSE", cj)]) for m in tabla.index for cj in PARTES},
               "colab_real_probado": False}
    print("RESUMEN_EXP_10_JSON=" + json.dumps(resumen, ensure_ascii=False, sort_keys=True))
    """, "cierre")
    for i, c in enumerate(cells):
        c.id = f"exp10-{i:03d}"
    md = copy.deepcopy(anterior.metadata)
    md["agrocebada"] = {"id": "EXP_10", "modo": "lector_resultados_experimento_registrado_sin_ajustes", "fecha_original": "2026-10-08",
                        "crisp_dm": [3, 4, 5], "ajustes_actuales": 0, "colab_real_probado": False,
                        "dependencias_requeridas": anterior.metadata.agrocebada.dependencias_requeridas,
                        "perfil_sha256": anterior.metadata.agrocebada.perfil_sha256, "soporte_sha256": anterior.metadata.agrocebada.soporte_sha256,
                        "base_sha256": BASE_SHA, "configuracion_sha256": hashlib.sha256((raiz / CONFIG).read_bytes()).hexdigest(),
                        "insumos": {k: {a: b for a, b in v.items() if a != "bytes_zlib_base64"} for k, v in reg.items()}}
    nb = nbformat.v4.new_notebook(cells=cells, metadata=md)
    nbformat.validate(nb)
    return nb


def main():
    raiz = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, default=raiz / N10 / "exp_10_verificacion_contraste_vecinal.ipynb")
    args = ap.parse_args()
    nb = construir(raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, args.salida)
    print(f"{args.salida}: {len(nb.cells)} celdas; cero ajustes")


if __name__ == "__main__":
    main()
