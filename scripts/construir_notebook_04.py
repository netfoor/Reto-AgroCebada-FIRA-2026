"""NB04: selección del modelo final, evaluaciones reunidas y las 59 predicciones (E_JK).

    uv run --locked --all-groups python scripts/construir_notebook_04.py
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import zlib
from pathlib import Path
from textwrap import dedent

import nbformat

BASE = "notebooks/experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb"
BASE_SHA = "8bb5b06266e4b7f3ed3c4761df3a93483a12d003bf4db4ba73a7bea4c9961a66"
CONFIG = "config/04_seleccion_modelo_final.json"
SALIDA = "notebooks/04_seleccion_modelo_final.ipynb"
D10 = "data/exp_10_verificacion_contraste_vecinal/"
PJ = "data/exp_11_combinacion_modelos/procedencia_jared/"
OP = "validacion_independiente/"
FAM = ["clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17"]
DOC_DECISION = "docs/comprension_fortino_8oct.md"
INSUMOS = {
    "metadatos": D10 + "metadatos.csv", "k1": D10 + "variables_197.csv", "etiquetas": D10 + "etiquetas_138.csv",
    "grupos_celda": "data/exp_04_lluvia_octubre/grupos.csv", "base_jared": PJ + "base_197_ubicacion.csv",
    **{f"jared_{f}_features": PJ + f"variables_jared/{f}_features.csv" for f in FAM},
    **{f"jared_{f}_hipotesis": PJ + f"variables_jared/{f}_hipotesis.csv" for f in FAM},
    "hist_externas": "data/validacion_03/particiones_externas.csv", "hist_internas": "data/validacion_03/particiones_internas.csv",
    "nuevas_externas": "data/exp_09_fuentes_externas/particiones_externas_nuevas.csv",
    "nuevas_internas": "data/exp_09_fuentes_externas/particiones_internas_nuevas.csv",
    "oof_componentes": "data/exp_11_combinacion_modelos/oof_componentes.csv",
    "j_elegidas": "data/exp_11_combinacion_modelos/j_variables_elegidas.csv",
    "metricas_exp11": "resultados/exp_11_combinacion_modelos/registrada/metricas.csv",
    "oof_global_hist": "data/validacion_03/oof_referencias_historico.csv",
    "r1_registro": OP + "registro_previo.json", "r1_oof": OP + "resultados_desarrollo/oof_desarrollo.csv",
    "r1_metricas": OP + "resultados_desarrollo/metricas_desarrollo_todas.csv", "r1_congelado": OP + "congelado.json",
    "r1_caja_pred": OP + "resultados_caja/predicciones_caja.csv", "r1_caja_res": OP + "resultados_caja/resultado_caja.json",
    "r2_registro": OP + "ronda2/registro_previo.json", "r2_chequeo": OP + "ronda2/chequeo_x.json",
    "r2_descargas": OP + "ronda2/datos/registro_descargas.json", "r2_oof": OP + "ronda2/resultados_cv/oof.csv",
    "r2_metricas": OP + "ronda2/resultados_cv/metricas.csv", "r2_congelado": OP + "ronda2/congelado.json",
    "r2_caja_pred": OP + "ronda2/resultados_caja/predicciones_caja.csv", "r2_caja_res": OP + "ronda2/resultados_caja/resultado.json",
}


def extracto_decision(raiz):
    """Solo la sección de la decisión (22:05) y su aplicación; el resto del documento personal no se incrusta."""
    t = (raiz / DOC_DECISION).read_text(encoding="utf-8")
    i, j = t.index("## Decisión del modelo final"), t.index("### Pendientes de cierre")
    return t[i:j].encode("utf-8"), hashlib.sha256(t.encode("utf-8")).hexdigest()


def preparar(raiz):
    contenidos = {k: ((raiz / r).read_bytes(), r) for k, r in INSUMOS.items()}
    ext, sha_doc = extracto_decision(raiz)
    contenidos["decision_fortino"] = (ext, f"{DOC_DECISION} (extracto: 'Decisión del modelo final' hasta 'Pendientes de cierre'; archivo completo sha256 {sha_doc})")
    cfg = {"id": "NB04", "modo": "seleccion_final_y_59_predicciones", "fecha": "2026-10-11", "modelo_entrega": "E_JK",
           "referencia": "MIX", "insumos": {}}
    out = {}
    for k, (b, origen) in contenidos.items():
        if not 0 < len(b) <= 2 * 1024 * 1024:
            raise ValueError(f"Insumo demasiado grande: {k}")
        c = {"ruta_local": origen, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "uso": k}
        cfg["insumos"][k] = c
        out[k] = {**c, "bytes_zlib_base64": base64.b64encode(zlib.compress(b, 9)).decode()}
    (raiz / CONFIG).write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    return cfg, out


def construir(raiz):
    cfg, reg = preparar(raiz)
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

    # ------------------------------------------------------------------ portada
    texto("""
    # 04. Selección del modelo final y las 59 predicciones

    **Reto AgroCebada FIRA 2026.** Este notebook explica, paso a paso, por qué entregamos el modelo que entregamos y genera las predicciones de las 59 parcelas ocultas.

    No es un experimento nuevo ni una búsqueda de modelos. **Reúne lo que ya existe, aplica una decisión registrada antes de conocer el último resultado y la documenta.**

    | | |
    | --- | --- |
    | **Modelo de entrega** | **E_JK = ½·J + ½·K**: promedio del modelo regional de Jared (J) y de MIX corregido con el contraste de verdor frente a las vecinas (K) |
    | **Referencia declarada** | **MIX** = ½·media municipal + ½·interpolación de vecinas |
    | **Error esperado** | RMSE ≈ 0.47–0.49 t/ha, no el 0.4757 de la validación cruzada. Por el azar de qué parcelas quedaron ocultas, en un conjunto como el de las 59 puede caer entre ≈0.35 y ≈0.63 |
    | **Por qué E_JK** | Superó a MIX en las cinco evaluaciones con el margen más estable, aunque pequeño (0.003–0.017 t/ha); combina dos modelos cuyo orden cambia entre evaluaciones |
    | **Qué limita al modelo** | La información disponible, no el algoritmo. El municipio explica ≈69 % de la variación, y de lo que queda recuperamos ≈7 % |

    Cada sección sigue el formato **pregunta → comprobación → resultado → decisión y límite**. Las cifras se recalculan aquí desde archivos guardados con SHA-256. Un `assert` detiene el notebook si alguna no coincide con lo registrado.
    """)
    for tag in ["soporte-colab", "preparar-colab", "entorno"]:
        reutilizar(tag)
    dec = tags["insumos-tecnicos"].source
    dec = dec[dec.index("def bytes_insumo"):]
    codigo("INSUMOS_INCRUSTADOS = " + repr(reg) + "\n\n" + dec +
           "\n\ndef csv_insumo(k):\n    return leer_csv(k, INSUMOS_INCRUSTADOS[k]['uso'])\n"
           "def json_insumo(k):\n    return json.loads(bytes_insumo(k, INSUMOS_INCRUSTADOS[k]['uso']))\n"
           "def texto_insumo(k):\n    return bytes_insumo(k, INSUMOS_INCRUSTADOS[k]['uso']).decode('utf-8')\n",
           "insumos-tecnicos", "Insumos incrustados: tamaño y SHA-256 verificados antes de leerlos")
    codigo("""
    display(pd.DataFrame([{"insumo": k, "origen": v["ruta_local"], "bytes": v["bytes"], "sha256": v["sha256"][:16] + "…"}
                          for k, v in INSUMOS_INCRUSTADOS.items()]).set_index("insumo"))
    """, "inventario-insumos")

    # ------------------------------------------------------------------ 1
    texto("""
    ## 1. El problema y los datos en una página

    **Pregunta.** ¿Qué se predice, con cuántas etiquetas y sobre qué población se evalúa?

    * Hay **197 parcelas** de cebada de una sola campaña (abril–octubre de 2025) en Hidalgo, Puebla y Tlaxcala.
    * **138** tienen rendimiento conocido en t/ha (ENTRENAMIENTO); **59** lo tienen oculto (PREDICCION). Esas 59 son las que entregamos.
    * Las variables X de las 197 son públicas en el reto: satélite, clima, topografía y geometría. Ninguna tabla X contiene rendimientos.

    **Dos poblaciones de evaluación:**

    * **SEEN135** (principal): en validación cruzada se evalúan solo las parcelas cuyo municipio aparece en el entrenamiento de ese pliegue. Se queda con 135 parcelas, porque 3 municipios tienen una sola etiqueta: AGC_047, AGC_048 y AGC_164. Representa lo que ocurre con las 59: todas están en municipios con etiquetas.
    * **FULL138** (sensibilidad): evalúa las 138, incluidas esas 3, que en el pliegue donde se validan se predicen sin datos de su municipio.
    """)
    codigo("""
    ID, Y = "ID_POLIGONO", "RENDIMIENTO_T_HA"
    meta = csv_insumo("metadatos")
    etiquetas = csv_insumo("etiquetas")
    k1 = csv_insumo("k1")[[ID, "K1_corregido"]]
    grupo = csv_insumo("base_jared")[[ID, "grupo"]]
    celda = csv_insumo("grupos_celda")[[ID, "celda_centroide"]].rename(columns={"celda_centroide": "celda"})
    T = meta.merge(k1, on=ID, validate="1:1").merge(grupo, on=ID, validate="1:1").merge(celda, on=ID, validate="1:1").set_index(ID).sort_index()
    y = etiquetas.set_index(ID)[Y].sort_index()
    assert len(T) == 197 and T.index.is_unique and not any("RENDIMIENTO" in c or "Cultivo" in c for c in T.columns)
    assert len(y) == 138 and y.notna().all() and set(y.index) == set(T.index[T.CONJUNTO.eq("ENTRENAMIENTO")])
    OCULTAS = np.array(sorted(T.index[T.CONJUNTO.eq("PREDICCION")]))
    ETIQUETADAS = np.array(sorted(y.index))
    assert len(OCULTAS) == 59 and not set(OCULTAS) & set(y.index)
    por_mun = pd.DataFrame({"etiquetadas": T.loc[ETIQUETADAS].Municipio.value_counts(), "ocultas": T.loc[OCULTAS].Municipio.value_counts()}).fillna(0).astype(int)
    display(por_mun.sort_values("etiquetadas", ascending=False))
    print(f"Rendimiento observado: media {y.mean():.3f} t/ha, desviación {y.std():.3f}, rango {y.min():.2f}–{y.max():.2f}")
    """, "datos")
    texto("""
    **Resultado.** Chignahuapan concentra la mitad de las parcelas, tanto etiquetadas como ocultas. Nanacamilpa tiene **una sola** etiqueta (AGC_048) y una oculta (AGC_120), un caso especial que se trata en la sección 7.

    **Límite.** Es una sola campaña: nada de lo que sigue permite afirmar cómo se comportaría el modelo en otro año.
    """)

    # ------------------------------------------------------------------ 2
    texto("""
    ## 2. Los candidatos congelados y de dónde salió cada uno

    | Candidato | Receta exacta | Origen |
    | --- | --- | --- |
    | **MUN** | Media del rendimiento del municipio en el entrenamiento; si el municipio no está, media global | [NB03](03_referencias_y_validacion.ipynb) |
    | **MIX** | 0.5·MUN + 0.5·IDW. IDW: 20 vecinas etiquetadas más cercanas por centroide (UTM 14N), peso 1/d², piso de 1 m | [NB03](03_referencias_y_validacion.ipynb) |
    | **K** | MIX + β·z. z = K1 corregido estandarizado con mediana y desviación del entrenamiento; β = Σz·e/(Σz²+10), con e = residuos de MIX obtenidos por 4 pliegues internos; sin K1, z = 0 | [EXP_08](experimentos/exp_08_contraste_vecinal/exp_08_contraste_vecinal.ipynb) → [EXP_09](experimentos/exp_09_fuentes_externas/exp_09_fuentes_externas.ipynb) → [EXP_10](experimentos/exp_10_verificacion_contraste_vecinal/exp_10_verificacion_contraste_vecinal.ipynb) |
    | **J** | Nivel por cada uno de los 5 grupos regionales + **una** variable elegida dentro del entrenamiento entre 148 candidatas de Jared (la de mayor correlación dentro de grupo), ajustado por mínimos cuadrados | Jared; verificado en [EXP_11](experimentos/exp_11_combinacion_modelos/exp_11_combinacion_modelos.ipynb) |
    | **E_JK** | ½·J + ½·K, fila por fila, sin pesos estimados | [EXP_11](experimentos/exp_11_combinacion_modelos/exp_11_combinacion_modelos.ipynb) |

    **K1 corregido** es la integral del NDVI de Planet durante la temporada (hasta el 31 de octubre de 2025) **menos la mediana de las parcelas vecinas a menos de 1 km**. Compara cada parcela con su entorno inmediato, no con la región.

    ### Declaración honesta del origen

    * **E_JK es post-hoc.** La idea de promediar J y K surgió en EXP_11, *después* de ver que J y K mejoraban zonas distintas.
    * **K1 también se eligió explorando** en EXP_08 las mismas 138 etiquetas.
    * **Todo se desarrolló con las mismas 138 etiquetas.** Las validaciones cruzadas reutilizan esos datos, así que los errores reportados tienen **sesgo de selección** (*data snooping*; Cawley y Talbot, 2010).
    * Formular la hipótesis después de ver los resultados se llama **HARKing**. Por eso la sección 5 añade una caja cerrada y un nulo que descuenta las búsquedas.

    **Comprobación.** Las recetas se escriben completas en la celda siguiente, sin importar código del proyecto. Antes de usarlas para las 59, deben reproducir **todas** las predicciones guardadas:

    * los 4 componentes en las 2,760 filas OOF de EXP_11 (dos juegos de particiones de 10×5);
    * los 5 candidatos en la caja cerrada de la prueba de Opus (entrenados con 103 parcelas).
    """)
    codigo('''
    def kfold(n, k, semilla):
        """Igual que sklearn.model_selection.KFold(k, shuffle=True, random_state=semilla): índices ordenados de entrenamiento y validación."""
        idx = np.arange(n)
        np.random.RandomState(semilla).shuffle(idx)
        tam = np.full(k, n // k)
        tam[: n % k] += 1
        ini = 0
        for t in tam:
            m = np.zeros(n, bool)
            m[idx[ini:ini + t]] = True
            ini += t
            yield np.flatnonzero(~m), np.flatnonzero(m)


    def internas(ids, semilla, k=4):
        """Pliegues internos (solo IDs del entrenamiento) para obtener residuos honestos de MIX."""
        ids, filas = np.array(sorted(ids)), []
        for p, (a, b) in enumerate(kfold(len(ids), k, semilla)):
            filas += [(p, "entrenamiento", i) for i in ids[a]] + [(p, "validacion", i) for i in ids[b]]
        return pd.DataFrame(filas, columns=["pliegue_interno", "rol", ID])


    def referencias(a, v):
        """MUN y MIX. a: entrenamiento con Municipio, x_m, y_m y rendimiento; v: validación SIN rendimiento."""
        assert Y not in v
        media = a[Y].mean()
        mun = v.Municipio.map(a.groupby("Municipio")[Y].mean()).fillna(media).to_numpy()
        d = np.linalg.norm(v[["x_m", "y_m"]].to_numpy()[:, None, :] - a[["x_m", "y_m"]].to_numpy()[None, :, :], axis=2)
        idx = np.argsort(d, axis=1)[:, : min(20, len(a))]
        w = 1 / np.maximum(np.take_along_axis(d, idx, axis=1), 1.0) ** 2
        w /= w.sum(axis=1, keepdims=True)
        idw = (w * a[Y].to_numpy()[idx]).sum(axis=1)
        return {"MUN": mun, "MIX": 0.5 * mun + 0.5 * idw}


    def residuos_mix(a, intern):
        """e = y − MIX para cada parcela del entrenamiento, predicha sin su propia etiqueta."""
        t = a.set_index(ID)
        e = pd.Series(np.nan, index=t.index)
        for _, g in intern.groupby("pliegue_interno"):
            ai = t.loc[g.loc[g.rol.eq("entrenamiento"), ID]].reset_index()
            vi = g.loc[g.rol.eq("validacion"), ID].to_numpy()
            e.loc[vi] = t.loc[vi, Y].to_numpy(float) - referencias(ai, t.loc[vi].drop(columns=Y).reset_index())["MIX"]
        assert not e.isna().any()
        return e


    def ajustar_beta(z, e, alpha=10.0):
        """β = Σ z̃·e / (Σ z̃² + α), z̃ estandarizado con mediana y desviación de las filas de entrenamiento con K1."""
        x = z.reindex(e.index).to_numpy(float)
        ok = np.isfinite(x)
        med, sd = float(np.median(x[ok])), float(np.std(x[ok], ddof=1))
        zz = (x[ok] - med) / sd
        return {"mediana": med, "escala": sd, "beta": float(zz @ e.to_numpy(float)[ok] / (zz @ zz + alpha)), "n_ajuste": int(ok.sum())}


    def corregir(p, z, ids):
        """Corrección de K; sin K1 → 0 (la parcela recibe MIX)."""
        x = z.reindex(ids).to_numpy(float)
        return np.where(np.isfinite(x), p["beta"] * (x - p["mediana"]) / p["escala"], 0.0)


    def jared(Fx, grupo, y, tr, va):
        """Elige la variable con mayor |correlación| dentro de grupo usando SOLO el entrenamiento; luego MCO con un nivel por grupo + una pendiente."""
        gtr, gva = grupo.loc[tr].to_numpy(), grupo.loc[va].to_numpy()
        ytr = y.loc[tr].to_numpy(float)
        X = Fx.loc[tr].to_numpy(float)
        niveles = sorted(set(gtr))
        yc, Xc = ytr.copy(), X.copy()
        for g in niveles:
            m = gtr == g
            yc[m] -= ytr[m].mean()
            Xc[m] -= X[m].mean(0)
        r = (Xc * yc[:, None]).sum(0) / np.sqrt(np.maximum((Xc ** 2).sum(0) * (yc ** 2).sum(), 1e-24))
        j = int(np.argmax(np.abs(r)))
        D = lambda x, g: np.column_stack([(g[:, None] == np.array(niveles)[None]).astype(float), x[:, None]])  # noqa: E731
        b = np.linalg.lstsq(D(X[:, j], gtr), ytr, rcond=None)[0]
        return D(Fx.loc[va].to_numpy(float)[:, j], gva) @ b, Fx.columns[j], dict(zip(niveles + ["pendiente"], b))


    def candidatos(tr, va, intern, etiquetas_y=None):
        """MUN, MIX, J, K y E_JK para va, entrenados con tr. va nunca recibe rendimientos."""
        yy = y if etiquetas_y is None else etiquetas_y
        a = T.loc[tr, ["Municipio", "x_m", "y_m"]].assign(**{Y: yy.loc[tr].to_numpy()}).reset_index()
        v = T.loc[va, ["Municipio", "x_m", "y_m"]].reset_index()
        ref = referencias(a, v)
        pb = ajustar_beta(T.K1_corregido, residuos_mix(a, intern))
        k = ref["MIX"] + corregir(pb, T.K1_corregido, np.asarray(va))
        j, var, coef = jared(FX, T.grupo, yy, np.asarray(tr), np.asarray(va))
        return {"MUN": ref["MUN"], "MIX": ref["MIX"], "J": j, "K": k, "E_JK": 0.5 * j + 0.5 * k}, {"K": pb, "J_variable": var, "J_coef": coef}


    # 148 candidatas de Jared (sin estandarizar: correlación y MCO con niveles por grupo son invariantes a esa transformación)
    F, hip = None, []
    for f in ["clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17"]:
        d = csv_insumo(f"jared_{f}_features")
        F = d if F is None else F.merge(d, on=ID, how="left")
        h = pd.read_csv(io.BytesIO(bytes_insumo(f"jared_{f}_hipotesis", f"jared_{f}_hipotesis")), dtype=str, keep_default_na=False)
        hip.append(h)
    hip = pd.concat(hip)
    hip = hip[(hip.spec == "lineal") & (hip.id != "HC2")]
    VARS_J = []
    for v in hip.variables:
        for x in v.replace(" ", "").split(";"):
            if x and x not in VARS_J:
                VARS_J.append(x)
    FX = F.set_index(ID)[VARS_J]
    assert len(VARS_J) == 148 and not FX.loc[ETIQUETADAS].isna().any().any()
    print("Recetas definidas; candidatas de Jared:", len(VARS_J))
    ''', "recetas")
    codigo("""
    comp = csv_insumo("oof_componentes")
    CLAVE = ["conjunto", "repeticion", "pliegue", ID]
    dif_max, n_filas = 0.0, 0
    for cj, (ke, ki) in {"historicas": ("hist_externas", "hist_internas"), "nuevas": ("nuevas_externas", "nuevas_internas")}.items():
        E, I = csv_insumo(ke), csv_insumo(ki)
        guard = comp[comp.conjunto.eq(cj)].pivot_table(index=["repeticion", "pliegue", ID], columns="modelo", values="predicho")
        for (r, f), g in E.groupby(["repeticion", "pliegue"]):
            tr = g.loc[g.rol.eq("entrenamiento"), ID].to_numpy()
            va = g.loc[g.rol.eq("validacion"), ID].to_numpy()
            p, _ = candidatos(tr, va, I[(I.repeticion == r) & (I.pliegue == f)][["pliegue_interno", "rol", ID]])
            gg = guard.loc[[(r, f, i) for i in va]]
            dif_max = max(dif_max, max(float(np.abs(p[m] - gg[m].to_numpy()).max()) for m in ["MUN", "MIX", "J", "K"]))
            n_filas += len(va)
    assert n_filas == 2760 and dif_max < 1e-9
    print(f"EXP_11: {n_filas} filas OOF × 4 componentes reproducidas; diferencia máxima {dif_max:.1e} t/ha")

    R1 = json_insumo("r1_registro")
    CAJA = sorted(R1["caja_cerrada"]["ids"])
    assert hashlib.sha256(",".join(CAJA).encode()).hexdigest() == R1["caja_cerrada"]["sha256_lista"] and len(CAJA) == 35
    DESARROLLO = np.array(sorted(set(ETIQUETADAS) - set(CAJA)))
    p_caja, _ = candidatos(DESARROLLO, np.array(CAJA), internas(DESARROLLO, 20261014))
    caja_guardada = csv_insumo("r1_caja_pred").set_index("Unnamed: 0").loc[CAJA]
    dif_caja = max(float(np.abs(p_caja[m] - caja_guardada[m].to_numpy()).max()) for m in ["MUN", "MIX", "J", "K", "E_JK"])
    assert dif_caja < 1e-12
    print(f"Caja cerrada de Opus (103 → 35): 5 candidatos reproducidos; diferencia máxima {dif_caja:.1e} t/ha")
    """, "reproduccion")
    texto("""
    **Resultado.** El código de este notebook reproduce las predicciones guardadas: diferencias del orden de 1e-13 t/ha, producto del redondeo en coma flotante. Las mismas funciones generan las 59 predicciones de la sección 7.
    """)

    # ------------------------------------------------------------------ 3
    texto("""
    ## 3. Todas las evaluaciones en una sola tabla

    **Pregunta.** ¿Qué tan bien predice cada candidato, según cada forma de evaluarlo que tenemos?

    **Comprobación.** Leemos las predicciones fuera de muestra guardadas, sin reentrenar, y recalculamos las métricas. Cada RMSE y MAE debe coincidir con el registrado en su corrida.

    | Evaluación | Parcelas | Particiones |
    | --- | --- | --- |
    | CV histórica | 138 (SEEN135) | 10×5, semilla 20260920 |
    | CV nueva | 138 (SEEN135) | 10×5, semilla 20261009 (EXP_09) |
    | CV desarrollo Opus R1 | 103 (sin la caja) | 10×5, semilla 20261012 |
    | CV desarrollo Opus R2 | las mismas 103 | 10×5, semilla 20261021 |
    | Caja cerrada | 35, entrenando con 103 | una sola apertura (R1). La R2 la reutilizó: segundo uso, menos limpio, con predicciones idénticas para estos 5 candidatos |

    **R²** se calcula de dos formas: **1 − SSE/SST** (proporción de varianza explicada) y **correlación²**. Dan casi lo mismo; si difieren, hay sesgo o escala.
    """)
    codigo("""
    def metricas(obs, pred):
        obs, pred = np.asarray(obs, float), np.asarray(pred, float)
        e = pred - obs
        return {"n": len(obs), "RMSE": float(np.sqrt((e ** 2).mean())), "MAE": float(np.abs(e).mean()),
                "R2 (1−SSE/SST)": float(1 - (e ** 2).sum() / ((obs - obs.mean()) ** 2).sum()), "R2 (corr²)": float(np.corrcoef(obs, pred)[0, 1] ** 2)}

    MODELOS = ["MUN", "MIX", "J", "K", "E_JK"]
    w = comp.pivot_table(index=CLAVE, columns="modelo", values="predicho").join(
        comp.drop_duplicates(CLAVE).set_index(CLAVE)[["observado", "Municipio", "municipio_visto"]]).reset_index()
    w["E_JK"] = 0.5 * w.J + 0.5 * w.K
    r1 = csv_insumo("r1_oof"); r2 = csv_insumo("r2_oof")
    caja_obs = caja_guardada.observado
    EVAL = {
        "1 CV histórica (138, SEEN)": {m: (g.observado, g[m]) for g in [w[w.conjunto.eq("historicas") & w.municipio_visto]] for m in MODELOS},
        "2 CV nueva (138, SEEN)": {m: (g.observado, g[m]) for g in [w[w.conjunto.eq("nuevas") & w.municipio_visto]] for m in MODELOS},
        "3 CV desarrollo Opus R1 (103)": {m: (g.observado, g.predicho) for m in MODELOS for g in [r1[r1.modelo.eq(m) & r1.municipio_visto]]},
        "4 CV desarrollo Opus R2 (103)": {m: (g.observado, g.predicho) for m in MODELOS for g in [r2[r2.modelo.eq(m) & r2.municipio_visto]]},
        "5 Caja cerrada (35)": {m: (caja_obs, caja_guardada[m]) for m in MODELOS},
    }
    TABLA = pd.DataFrame([{"evaluación": ev, "modelo": m, **metricas(*par)} for ev, d in EVAL.items() for m, par in d.items()]).set_index(["evaluación", "modelo"])
    # Controles contra lo registrado en cada corrida
    m11 = csv_insumo("metricas_exp11").query("escenario == 'SEEN135'").set_index(["conjunto", "modelo"])
    for cj, ev in [("historicas", "1 CV histórica (138, SEEN)"), ("nuevas", "2 CV nueva (138, SEEN)")]:
        for m in MODELOS:
            assert abs(TABLA.loc[(ev, m), "RMSE"] - m11.loc[(cj, m), "RMSE"]) < 1e-12 and abs(TABLA.loc[(ev, m), "MAE"] - m11.loc[(cj, m), "MAE"]) < 1e-12
    for ins, ev in [("r1_metricas", "3 CV desarrollo Opus R1 (103)"), ("r2_metricas", "4 CV desarrollo Opus R2 (103)")]:
        mm = csv_insumo(ins).set_index("modelo")
        for m in MODELOS:
            assert abs(TABLA.loc[(ev, m), "RMSE"] - mm.loc[m, "RMSE"]) < 1e-9 and TABLA.loc[(ev, m), "n"] == mm.loc[m, "n"]
    rc1 = json_insumo("r1_caja_res")["metricas_caja"]
    for m in MODELOS:
        assert abs(TABLA.loc[("5 Caja cerrada (35)", m), "RMSE"] - rc1[m]["RMSE"]) < 1e-12 and abs(TABLA.loc[("5 Caja cerrada (35)", m), "MAE"] - rc1[m]["MAE"]) < 1e-12
    caja_r2 = csv_insumo("r2_caja_pred").set_index("Unnamed: 0").loc[CAJA]
    assert all(np.array_equal(caja_r2[m].to_numpy(), caja_guardada[m].to_numpy()) for m in MODELOS)
    display(TABLA.round(4))
    """, "tabla-evaluaciones")
    codigo("""
    rm = TABLA.RMSE.unstack("modelo")[MODELOS]
    rm["E_JK − MIX"] = rm.E_JK - rm.MIX
    rm["mejor"] = rm[MODELOS].idxmin(axis=1)
    display(rm.round(4))
    assert (rm["E_JK − MIX"] < 0).all()
    r2a, r2b = TABLA["R2 (1−SSE/SST)"], TABLA["R2 (corr²)"]
    print(f"Diferencia máxima entre las dos formas de R²: {np.abs(r2a - r2b).max():.3f}")
    e1, e2 = rm.loc["3 CV desarrollo Opus R1 (103)", "E_JK"], rm.loc["4 CV desarrollo Opus R2 (103)", "E_JK"]
    assert round(e1, 4) == 0.4750 and round(e2, 4) == 0.4871
    print(f"Mismas 103 parcelas, otra semilla: E_JK {e1:.4f} → {e2:.4f} (Δ {e2 - e1:+.4f}); "
          f"brecha E_JK − MIX {rm.loc['3 CV desarrollo Opus R1 (103)', 'E_JK − MIX']:+.4f} → {rm.loc['4 CV desarrollo Opus R2 (103)', 'E_JK − MIX']:+.4f}")
    """, "tabla-rmse")
    texto("""
    **Resultado.**

    * **E_JK tiene menor RMSE que MIX en las cinco evaluaciones**, aunque la ventaja es pequeña: de 0.003 a 0.017 t/ha.
    * **El ganador cambia según la evaluación.** E_JK gana las dos CV con 138 y la CV R1 de Opus (por 0.0002 sobre J); J gana la CV R2; K gana la caja, donde J queda último.
    * **El reparto de pliegues mueve tanto como lo que separa a los modelos.** Con las mismas 103 parcelas y otra semilla, E_JK pasa de 0.4750 a 0.4871 (+0.012). En cambio, la brecha E_JK − MIX sí se mantiene (−0.016 y −0.017).
    * Las dos formas de R² difieren como mucho 0.02: no hay sesgo grande ni problemas de escala.

    **Decisión y límite.** Ninguna diferencia entre E_JK, J y K es estable. Lo único consistente es que E_JK no pierde contra MIX. Con 35 parcelas, la caja no puede distinguir diferencias de 1–2 % (Varoquaux, 2018, muestra que con ~100 casos las barras de error de la validación cruzada son del orden de ±10 %).
    """)

    # ------------------------------------------------------------------ 4
    texto("""
    ## 4. Por qué todo queda en 0.4x

    ### 4.1 Cuánto explica el territorio

    **Pregunta.** ¿Qué parte de la variación del rendimiento se explica solo con saber el municipio, y cuánto añade nuestro mejor modelo?

    **Comprobación.**

    * Con las 138 etiquetas, la proporción de varianza entre municipios es 1 − SS_dentro/SS_total.
    * Fuera de muestra, comparamos el error cuadrático medio de E_JK con el de MUN.
    """)
    codigo("""
    L = T.loc[ETIQUETADAS].assign(y=y)
    r2_mun = 1 - ((L.y - L.groupby("Municipio").y.transform("mean")) ** 2).sum() / ((L.y - L.y.mean()) ** 2).sum()
    assert abs(r2_mun - 0.686) < 5e-4
    quita = {cj: 1 - rm.loc[ev, "E_JK"] ** 2 / rm.loc[ev, "MUN"] ** 2 for cj, ev in [("históricas", "1 CV histórica (138, SEEN)"), ("nuevas", "2 CV nueva (138, SEEN)")]}
    assert all(0.06 < v < 0.08 for v in quita.values())
    print(f"El municipio explica {r2_mun:.1%} de la varianza del rendimiento (dentro de muestra).")
    print("Del error que deja MUN fuera de muestra, E_JK quita: " + ", ".join(f"{k} {v:.1%}" for k, v in quita.items()))
    """, "varianza")
    texto("""
    **Resultado.** El municipio explica **68.6 %**. Del error que deja la media municipal, E_JK quita **≈7 %**. Todo lo que probamos, con 619 variables propias y varias fuentes externas, cabe en ese 7 %.

    ### 4.2 Parcelas vecinas: hay estructura, pero corta

    **Pregunta.** Dentro de un municipio, ¿las parcelas cercanas se desvían en la misma dirección?

    **Comprobación.** Semivarianza de los residuos respecto de la media municipal, solo entre pares del mismo municipio, por distancia (receta de EXP_08).
    """)
    codigo("""
    res = (L.y - L.groupby("Municipio").y.transform("mean")).to_numpy()
    xy = L[["x_m", "y_m"]].to_numpy()
    Dm = np.linalg.norm(xy[:, None] - xy[None], axis=2)
    mismo = L.Municipio.to_numpy()[:, None] == L.Municipio.to_numpy()[None]
    iu = np.triu_indices(len(L), 1)
    gam = (0.5 * (res[:, None] - res[None]) ** 2)[iu]
    cortes = [0, 250, 500, 1000, 2000, 4000, 8000]
    vario = pd.DataFrame([{"distancia (m)": f"{a}–{b}", "pares": int(m.sum()), "semivarianza": gam[m].mean(),
                           "diferencia típica entre dos parcelas (t/ha)": np.sqrt(2 * gam[m].mean())}
                          for a, b in zip(cortes[:-1], cortes[1:]) for m in [((Dm >= a) & (Dm < b) & mismo)[iu]]]).set_index("distancia (m)")
    display(vario.round(3))
    assert abs(vario.iloc[0].semivarianza - 0.090) < 1e-3 and abs(vario.iloc[0, 2] - 0.42) < 0.01
    """, "semivarianza")
    texto("""
    **Resultado.** A menos de 250 m la semivarianza es ≈0.09, frente a ≈0.27–0.35 a partir de 500 m. Las parcelas muy cercanas se parecen más, y eso es lo que aprovechan MIX y K. Aun así, **dos parcelas a menos de 250 m difieren típicamente ≈0.42 t/ha**. Esa diferencia no la explica la ubicación, y ningún dato disponible la explicó.

    **Límite.** Son solo 23 pares a menos de 250 m.

    ### 4.3 ¿Ayudarían más parcelas del mismo tipo? Curva de aprendizaje

    **Pregunta.** Si tuviéramos más parcelas etiquetadas como estas, ¿cuánto bajaría el error?

    **Comprobación.**

    * Submuestreamos entre el 30 % y el 90 % de las 138 (200 sorteos por fracción, semilla 20261016).
    * Entrenamos MUN y MIX y evaluamos en el resto (solo municipios vistos).
    * Ajustamos **MSE(n) = s² + c/n**: *s* es el error que no desaparece aunque haya muchas parcelas, y *c/n* la parte que se reduce con más datos.

    Es una **aproximación**: supone parcelas nuevas parecidas a las actuales, y la extrapolación más allá de 138 es incierta.
    """)
    codigo("""
    rng = np.random.default_rng(20261016)
    filas = []
    for frac in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        n = int(round(frac * len(ETIQUETADAS)))
        for _ in range(200):
            tr = np.sort(rng.choice(ETIQUETADAS, n, replace=False))
            va = np.setdiff1d(ETIQUETADAS, tr)
            a = T.loc[tr, ["Municipio", "x_m", "y_m"]].assign(**{Y: y.loc[tr].to_numpy()}).reset_index()
            p = referencias(a, T.loc[va, ["Municipio", "x_m", "y_m"]].reset_index())
            vis = T.loc[va, "Municipio"].isin(set(T.loc[tr, "Municipio"])).to_numpy()
            for m in ["MUN", "MIX"]:
                e = (p[m] - y.loc[va].to_numpy())[vis]
                filas.append({"modelo": m, "n": n, "sse": (e ** 2).sum(), "k": len(e)})
    curva = pd.DataFrame(filas).groupby(["modelo", "n"]).sum()
    curva["RMSE"] = np.sqrt(curva.sse / curva.k)
    ajuste = {}
    for m in ["MUN", "MIX"]:
        q = curva.loc[m]
        s2, c = np.linalg.lstsq(np.column_stack([np.ones(len(q)), 1 / q.index.to_numpy()]), (q.RMSE ** 2).to_numpy(), rcond=None)[0]
        ajuste[m] = {"RMSE con 124 (observado)": q.RMSE.loc[124], "con 138": np.sqrt(s2 + c / 138), "con 197": np.sqrt(s2 + c / 197),
                     "con 220": np.sqrt(s2 + c / 220), "techo s": np.sqrt(s2), "s2": s2, "c": c}
    ajuste = pd.DataFrame(ajuste).T
    display(curva.RMSE.unstack("modelo").round(4).T)
    display(ajuste.drop(columns=["s2", "c"]).round(4))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    nn = np.linspace(40, 260, 100)
    for m, col in [("MUN", "#888888"), ("MIX", "#1f5f8b")]:
        q = curva.loc[m]
        ax.plot(q.index, q.RMSE, "o", color=col, label=f"{m} observado")
        ax.plot(nn, np.sqrt(ajuste.loc[m, "s2"] + ajuste.loc[m, "c"] / nn), "--", color=col, label=f"{m}: s² + c/n")
        ax.axhline(ajuste.loc[m, "techo s"], color=col, lw=0.6, ls=":")
    ax.axvline(138, color="k", lw=0.6); ax.text(140, ax.get_ylim()[1] * 0.995, "138 etiquetas", va="top", fontsize=8)
    ax.set_xlabel("parcelas de entrenamiento"); ax.set_ylabel("RMSE (t/ha)"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
    mx = ajuste.loc["MIX"]
    assert 0.44 < mx["techo s"] < mx["RMSE con 124 (observado)"] < 0.50 and mx["RMSE con 124 (observado)"] - mx["con 220"] < 0.01
    print("Cifras rápidas de Fortino (11 oct), solo para contraste: MIX con 124 → 0.481; extrapolado a ~220 → 0.474; techo ≈0.465.")
    """, "curva")
    texto("""
    **Resultado.** La curva es casi plana: pasar de 124 a ~220 parcelas mejoraría MIX en menos de 0.01 t/ha, y el techo estimado (*s*) queda en ≈0.47. Las cifras difieren algo de las que Fortino calculó rápidamente el 11 de octubre (0.481 → 0.474, techo 0.465) por el sorteo y el ajuste, pero la conclusión es la misma: **más parcelas del mismo tipo no resuelven el problema; haría falta información distinta** (sección 9).

    ### 4.4 ¿Qué RMSE puede salir en las 59? Simulación

    **Pregunta.** Si el error esperado es ≈0.48, ¿cuánto puede variar en un conjunto concreto de 59 parcelas? ¿Con qué frecuencia E_JK supera a MIX y a MUN?

    **Comprobación.**

    * Para cada parcela etiquetada, tomamos su error cuadrático OOF medio por modelo (EXP_11, ambos juegos, FULL138).
    * Simulamos 10,000 conjuntos con la **composición municipal de las 59 ocultas**: 29 Chignahuapan, 14 Calpulalpan, 7 Singuilucan, 4 Almoloya, 4 Cuautepec y 1 Nanacamilpa.
    * Cada conjunto se obtiene por bootstrap dentro de cada municipio (semilla 20261017).
    """)
    codigo("""
    err = w.assign(**{m: (w[m] - w.observado) ** 2 for m in MODELOS}).groupby(ID)[MODELOS].mean()
    err["Municipio"] = T.loc[err.index, "Municipio"]
    comp59 = T.loc[OCULTAS, "Municipio"].value_counts()
    pools = {mu: err[err.Municipio.eq(mu)][MODELOS].to_numpy() for mu in comp59.index}
    rng = np.random.default_rng(20261017)
    sims = []
    for _ in range(10000):
        s = np.vstack([pools[mu][rng.integers(0, len(pools[mu]), k)] for mu, k in comp59.items()])
        sims.append(np.sqrt(s.mean(0)))
    sims = pd.DataFrame(sims, columns=MODELOS)
    banda = sims.quantile([0.025, 0.5, 0.975]).rename(index={0.025: "percentil 2.5", 0.5: "mediana", 0.975: "percentil 97.5"})
    display(banda.round(3))
    P_MIX, P_MUN = float((sims.E_JK < sims.MIX).mean()), float((sims.E_JK < sims.MUN).mean())
    print(f"P(E_JK < MIX) = {P_MIX:.3f}   P(E_JK < MUN) = {P_MUN:.3f}")
    fig, ax = plt.subplots(figsize=(7, 3))
    for m, c in [("MIX", "#888888"), ("E_JK", "#1f5f8b")]:
        ax.hist(sims[m], bins=60, alpha=0.55, color=c, label=m)
    ax.set_xlabel("RMSE simulado en un conjunto tipo 59 (t/ha)"); ax.legend(); plt.tight_layout(); plt.show()
    BANDA_EJK = (float(banda.loc["percentil 2.5", "E_JK"]), float(banda.loc["percentil 97.5", "E_JK"]))
    assert 0.30 < BANDA_EJK[0] < 0.40 and 0.55 < BANDA_EJK[1] < 0.70
    """, "simulacion")
    texto("""
    **Resultado.**

    * La mediana simulada de E_JK es ≈0.47, pero **en un conjunto concreto de 59 parcelas su RMSE puede caer entre ≈0.35 y ≈0.63**, solo por cuáles parcelas quedaron ocultas. La banda es más ancha hacia arriba porque Chignahuapan, la zona más difícil, aporta la mitad de las 59.
    * Fortino estimó rápidamente ~0.35–0.60. Esta simulación, más completa, alarga el extremo superior a ≈0.63.

    **Límite importante.** La probabilidad de que E_JK supere a MIX (≈0.99) está **sobreestimada**:

    * Usa los errores de la misma validación cruzada en la que se eligió E_JK, que tiene sesgo de selección.
    * Supone que el error de cada parcela es fijo.

    En la caja cerrada, la evidencia más limpia que tenemos, E_JK superó a MIX por solo 0.003 t/ha. La lectura correcta es que **E_JK probablemente no será peor que MIX, pero la diferencia esperada es pequeña**.
    """)

    # ------------------------------------------------------------------ 5
    texto("""
    ## 5. Pruebas finales independientes (Opus)

    Fueron dos rondas con **caja cerrada**: 35 de las 138 parcelas apartadas por sorteo estratificado por municipio (semilla 20261011) **antes** de leer rendimientos. Todo se registró y congeló antes de abrirla. Aquí solo se resumen y se comprueban sus cifras guardadas; no se reejecutan. Detalle en [`validacion_independiente/`](../validacion_independiente/README.md) y [`ronda2/`](../validacion_independiente/ronda2/README.md).

    ### Ronda 1 (11 oct, 14:09–14:14 CDMX): siete familias nuevas

    Las familias, nombradas como en los registros de Opus:

    | Familia | Receta |
    | --- | --- |
    | F1 | Modelo jerárquico REML con municipio y celda |
    | F2 | F1 + K1 |
    | F3 | F2 + proceso gaussiano |
    | F4 | ⅓(J+K+F2) |
    | F5 | F2 + log(área) |
    | F6 | Regresión-kriging de J |
    | F7 | ½F6 + ½K |
    """)
    codigo("""
    m1 = csv_insumo("r1_metricas").set_index("modelo").sort_values("RMSE")
    display(m1[["RMSE", "MAE", "reps_mejor_que_E_JK", "reps_mejor_que_MIX"]].round(4))
    c1 = json_insumo("r1_congelado"); rr1 = json_insumo("r1_caja_res")
    print("Reality Check (White, 2000) de F1–F7 frente a E_JK: p =", c1["reality_check"]["E_JK"]["p_valor"], "| frente a MIX: p =", round(c1["reality_check"]["MIX"]["p_valor"], 3))
    display(pd.DataFrame(rr1["metricas_caja"]).T[["RMSE", "MAE", "R2"]].sort_values("RMSE").round(4))
    print("Procedimiento congelado:", c1["procedimiento_final"], "| condiciones:", rr1["condiciones"], "| decisión:", rr1["decision"])
    assert c1["reality_check"]["E_JK"]["p_valor"] == 1.0 and rr1["decision"] == "NO FAVORABLE" and c1["procedimiento_final"] == "F7"
    """, "opus-r1")
    texto("""
    **Ronda 1.** Ninguna familia superó a E_JK en la CV (p = 1.0). La elegida, F7, quedó peor que E_JK y que MIX en la caja. **Decisión registrada: NO FAVORABLE.**

    ### Ronda 2 (11 oct, 22:14–22:18 CDMX): información externa que cambie dentro del municipio

    * **Fase A:** inventario de datos públicos a escala de parcela (tabla completa en la sección 9).
    * **Fase B:** dos hipótesis registradas a las 22:14, antes de calcularlas:
      * **H1:** posición topográfica (TPI a 1 km con Copernicus DEM de 30 m), como indicador de bolsas de aire frío y heladas.
      * **H2:** carbono orgánico del suelo de 0–30 cm (SoilGrids, 250 m).
    * Cada una se probó como corrección penalizada sobre E_JK y sobre MIX.
    """)
    codigo("""
    chx = json_insumo("r2_chequeo")
    display(pd.DataFrame({h: {k: chx[h][k] for k in ["variable", "sd_dentro_municipio", "R2_municipio", "R2_celda_CHIRPS", "pasa_regla_no_etiqueta"]} for h in ["H1", "H2"]}).T)
    m2 = csv_insumo("r2_metricas").set_index("modelo")
    display(m2.loc[["E_JK", "H1_E_JK", "H2_E_JK", "MIX", "H2_MIX", "H1_MIX"], ["RMSE", "MAE", "reps_mejor_que_E_JK", "reps_mejor_que_MIX"]].round(4))
    c2, rr2 = json_insumo("r2_congelado"), json_insumo("r2_caja_res")
    print("Reality Check con 11 familias (F1–F7 + 4 nuevas) frente a E_JK: p =", c2["reality_check"]["E_JK"]["p_valor"])
    display(pd.DataFrame(rr2["metricas_caja"]).T[["RMSE", "MAE"]].loc[["E_JK", "H1_E_JK", "MIX", "H1_MIX"]].round(5))
    print("Congelado:", c2["procedimiento_final"], "| condiciones:", rr2["condiciones"], "| decisión mecánica:", rr2["decision"])
    assert c2["reality_check"]["E_JK"]["p_valor"] == 1.0 and rr2["decision"] == "PARCIAL" and len(c2["reality_check"]["E_JK"]["modelos"]) == 11
    assert rr2["metricas_caja"]["H1_E_JK"]["RMSE"] > rr2["metricas_caja"]["E_JK"]["RMSE"] and rr2["congelados_identicos_a_ronda1_dif_max"] == 0.0
    """, "opus-r2")
    texto("""
    **Ronda 2.** Ambas variables varían dentro del municipio: la celda CHIRPS explica solo 47 % y 60 % de ellas, así que no son una simple etiqueta de lugar. Pero **ninguna mejora a su base**:

    * E_JK + TPI empeora a E_JK en la CV (2 de 10 repeticiones mejores) y en la caja (0.48277 frente a 0.48217).
    * La pendiente estimada es ≈0.

    La regla mecánica da **PARCIAL** solo porque cumple MAE ≤ MIX, algo que E_JK ya lograba. **En sustancia, el resultado es nulo.**
    """)

    # ------------------------------------------------------------------ 6
    texto("""
    ## 6. La decisión

    **Regla fijada de antemano** por Fortino, a las 22:05 (CDMX) del 11 de octubre, antes de conocer la ronda 2:

    > Si la ronda 2 sale FAVORABLE según su criterio registrado, se reabre la elección. Si sale PARCIAL o NO FAVORABLE, **E_JK queda sin cambios**, con MIX como referencia.

    **Comprobación.** Leemos el extracto registrado de la decisión y las horas de la ronda 2, verificamos el orden y aplicamos la regla.
    """)
    codigo("""
    from zoneinfo import ZoneInfo
    cdmx = ZoneInfo("America/Mexico_City")
    extracto = texto_insumo("decision_fortino")
    assert "(11 oct 2026, 22:05 CDMX)" in extracto and "Modelo de entrega: E_JK" in extracto and "Si sale PARCIAL o NO FAVORABLE, E_JK queda sin cambios" in extracto
    reg2 = json_insumo("r2_registro")
    horas = pd.DataFrame([
        {"evento": "Decisión y regla de Fortino", "hora CDMX": "2026-10-11 22:05", "fuente": "docs/comprension_fortino_8oct.md"},
        {"evento": "Hipótesis de la ronda 2 registradas", "hora CDMX": datetime.fromisoformat(reg2["registrado_cdmx"]).strftime("%Y-%m-%d %H:%M:%S"), "fuente": "ronda2/registro_previo.json"},
        {"evento": "Ronda 2 congelada (antes de abrir la caja)", "hora CDMX": datetime.fromisoformat(c2["congelado_utc"]).astimezone(cdmx).strftime("%Y-%m-%d %H:%M:%S"), "fuente": "ronda2/congelado.json"},
        {"evento": "Resultado de la ronda 2 (caja, segundo uso)", "hora CDMX": datetime.fromisoformat(rr2["apertura_utc"]).astimezone(cdmx).strftime("%Y-%m-%d %H:%M:%S"), "fuente": "ronda2/resultados_caja/resultado.json"},
    ])
    display(horas)
    assert list(horas["hora CDMX"]) == sorted(horas["hora CDMX"])
    MODELO_FINAL = "E_JK" if rr2["decision"] != "FAVORABLE" else None
    assert MODELO_FINAL == "E_JK"
    # Razones verificables
    gana_mix = bool((rm["E_JK − MIX"] < 0).all())
    cota = all(rm.loc[ev, "E_JK"] <= (rm.loc[ev, "J"] + rm.loc[ev, "K"]) / 2 + 1e-12 for ev in rm.index)
    k_mix = bool((rm.K < rm.MIX).all())
    assert gana_mix and cota and k_mix
    display((rm[["J", "K", "E_JK"]].sub(rm.MIX, axis=0)).rename(columns=lambda c: f"{c} − MIX").round(4))
    print(f"Ronda 2: {rr2['decision']} → la regla mantiene {MODELO_FINAL}. E_JK < MIX en las {len(rm)} evaluaciones: {gana_mix}. "
          f"RMSE(E_JK) ≤ promedio de RMSE(J) y RMSE(K) en todas: {cota}.")
    """, "decision")
    texto("""
    **Por qué E_JK:**

    1. **Supera a MIX en las cinco evaluaciones** (sección 3), con márgenes de 0.003 a 0.017 t/ha. K también queda por debajo de MIX en las cinco, pero con márgenes de 0.0001 a 0.014: en las dos CV de Opus prácticamente empata. J pierde contra MIX en la caja.
    2. **Promediar con igual peso acota el error.** Por la desigualdad del triángulo, el RMSE del promedio nunca supera el promedio de los RMSE de J y K, así que E_JK no puede caer al nivel del peor de los dos. Como no sabemos cuál de los dos será mejor en las 59 (en la caja invirtieron su orden), esta es la elección prudente. Además, pesos estimados suelen rendir peor que pesos iguales (Claeskens et al., 2016).
    3. **La regla se fijó antes del último resultado**, así que la decisión no se ajustó a él. La hora 22:05 es la que Fortino declaró en su documento; no tiene un sello externo. Las horas de la ronda 2 sí quedaron en los registros JSON.

    **Cómo se reporta:**

    * RMSE esperado **≈0.47–0.49 t/ha** (rango de las CV y la caja), no el 0.4757 de la CV histórica.
    * En las 59 concretas, banda **≈0.35–0.63** (sección 4.4).
    * Origen post-hoc de E_JK declarado.
    * MIX como referencia.
    """)

    # ------------------------------------------------------------------ 7
    texto("""
    ## 7. Ajuste final y las 59 predicciones

    **Pregunta.** ¿Qué predice E_JK para las 59 parcelas, cuánto cambia frente a MIX y con qué incertidumbre?

    **Comprobación.** Entrenamos los cinco candidatos con las **138** etiquetas:

    * Para los residuos internos de K usamos 4 pliegues con la semilla declarada **20261015**, no usada antes.
    * Registramos qué variable eligió J.
    * La sensibilidad de β a otras semillas se muestra solo como información; no se elige nada con ella.
    """)
    codigo("""
    SEMILLA_FINAL = 20261015
    PRED, INFO = candidatos(ETIQUETADAS, OCULTAS, internas(ETIQUETADAS, SEMILLA_FINAL))
    PRED = pd.DataFrame(PRED, index=pd.Index(OCULTAS, name=ID))
    print(f"K: β = {INFO['K']['beta']:+.4f} t/ha por desviación de K1 (mediana {INFO['K']['mediana']:.2f}, desviación {INFO['K']['escala']:.2f}, {INFO['K']['n_ajuste']} parcelas con K1)")
    print(f"J: variable elegida = {INFO['J_variable']}")
    display(pd.Series(INFO["J_coef"], name="coeficiente J").to_frame().round(4))
    sens = pd.Series({s: candidatos(ETIQUETADAS, OCULTAS, internas(ETIQUETADAS, s))[1]["K"]["beta"] for s in [SEMILLA_FINAL, 1, 2, 3, 4, 5]}, name="β")
    print("β con otras semillas internas (informativo):", sens.round(4).to_dict())
    assert INFO["J_variable"] == "anom_precip_pct_d" and INFO["K"]["beta"] < 0 and sens.std() < 0.01
    """, "ajuste-final")
    texto("""
    * **β < 0**, igual que en las 50 particiones de EXP_08: una parcela más verde y más temprana que sus vecinas rinde **menos** de lo que predice su territorio.
    * β apenas cambia con la semilla (entre −0.086 y −0.094), así que la elección de la semilla interna no importa.
    * J eligió, como en casi todos los pliegues, la **anomalía de lluvia de octubre (% del histórico)**.

    ### 7.1 Intervalos de predicción

    **Receta:**

    * Cuantiles empíricos de los residuos OOF de E_JK (observado − predicho), por zona: Chignahuapan contra el resto. Se usan ambos juegos de EXP_11, SEEN.
    * Niveles nominales: **80 %** (cuantiles 10–90) y **90 %** (cuantiles 5–95).

    **Cobertura empírica**, comprobada en tres pruebas:

    * cuantiles de las particiones históricas aplicados a las nuevas, y al revés (mismas etiquetas, no independiente);
    * cuantiles de la CV de desarrollo de Opus (103 parcelas) aplicados a la **caja de 35**.
    """)
    codigo("""
    def zona(m):
        return np.where(np.asarray(m) == "Chignahuapan", "Chignahuapan", "resto")

    NIVELES = {"80 %": (0.10, 0.90), "90 %": (0.05, 0.95)}
    def cuantiles(df):
        return {(z, n): tuple(np.quantile(g.res, q)) for z, g in df.groupby("zona") for n, q in NIVELES.items()}
    def cobertura(df, Q):
        return {n: float(np.mean([Q[(z, n)][0] <= r <= Q[(z, n)][1] for z, r in zip(df.zona, df.res)])) for n in NIVELES}

    S = w[w.municipio_visto].assign(res=lambda d: d.observado - d.E_JK, zona=lambda d: zona(d.Municipio))
    d1 = r1[r1.modelo.eq("E_JK") & r1.municipio_visto].assign(res=lambda d: d.observado - d.predicho, zona=lambda d: zona(d.Municipio))
    cj = caja_guardada.assign(res=lambda d: d.observado - d.E_JK, zona=lambda d: zona(d.Municipio))
    COB = pd.DataFrame({
        "históricas → nuevas": cobertura(S[S.conjunto.eq("nuevas")], cuantiles(S[S.conjunto.eq("historicas")])),
        "nuevas → históricas": cobertura(S[S.conjunto.eq("historicas")], cuantiles(S[S.conjunto.eq("nuevas")])),
        "CV Opus (103) → caja (35)": cobertura(cj, cuantiles(d1)),
    }).T
    display(COB.round(3))
    Q = cuantiles(S)
    display(pd.DataFrame(Q, index=["inferior", "superior"]).T.round(3))
    assert all(abs(COB.iloc[i, 0] - 0.80) < 0.02 and abs(COB.iloc[i, 1] - 0.90) < 0.02 for i in range(2))
    """, "intervalos")
    texto("""
    **Resultado.**

    * Entre juegos de particiones, la cobertura coincide con la nominal (≈0.80 y ≈0.90), pero esa prueba no es independiente.
    * En la caja, con 35 parcelas, cubre **0.71 y 0.86**: algo menos que lo nominal.
    * Los intervalos son **aproximados**, por tres razones:
      * los residuos vienen de modelos entrenados con ~110 parcelas, no con 138;
      * suponen que las 59 se parecen a las etiquetadas de su zona;
      * no cubren un cambio de campaña.
    * En Chignahuapan el intervalo es más ancho: ±0.62 t/ha al 80 %, frente a ±0.49 en el resto.

    ### 7.2 Tabla de las 59
    """)
    codigo("""
    DET = PRED.copy()
    DET.insert(0, "Municipio", T.loc[OCULTAS, "Municipio"].to_numpy())
    DET["E_JK − MIX"] = DET.E_JK - DET.MIX
    DET["zona"] = zona(DET.Municipio)
    for n in NIVELES:
        DET[f"inferior {n}"] = DET.E_JK + [Q[(z, n)][0] for z in DET.zona]
        DET[f"superior {n}"] = DET.E_JK + [Q[(z, n)][1] for z in DET.zona]
    DET["sin K1 (K = MIX)"] = ~np.isfinite(T.loc[OCULTAS, "K1_corregido"].to_numpy())
    celdas_lab = set(T.loc[ETIQUETADAS, "celda"])
    DET["celda CHIRPS sin etiquetas"] = ~T.loc[OCULTAS, "celda"].isin(celdas_lab).to_numpy()
    pd.set_option("display.max_rows", 80)
    display(DET.round(3))
    dif = DET["E_JK − MIX"]
    print(f"|E_JK − MIX|: media {dif.abs().mean():.3f} t/ha, máximo {dif.abs().max():.3f} ({dif.abs().idxmax()}); "
          f"{int((dif.abs() > 0.10).sum())} de 59 difieren más de 0.10 t/ha")
    fig, ax = plt.subplots(figsize=(10, 3.4))
    o = DET.sort_values("E_JK")
    xs = np.arange(len(o))
    ax.fill_between(xs, o["inferior 80 %"], o["superior 80 %"], color="#1f5f8b", alpha=0.15, label="intervalo 80 %")
    ax.plot(xs, o.E_JK, "o", color="#1f5f8b", ms=4, label="E_JK (entrega)")
    ax.plot(xs, o.MIX, "x", color="#888888", ms=4, label="MIX (referencia)")
    ax.set_xticks(xs, o.index, rotation=90, fontsize=6); ax.set_ylabel("t/ha"); ax.legend(fontsize=8); plt.tight_layout(); plt.show()
    """, "tabla-59")
    texto("""
    **Lectura.** E_JK y MIX difieren en promedio 0.06 t/ha y como máximo 0.20 (AGC_129); solo 12 de las 59 cambian más de 0.10. La elección del modelo mueve la entrega mucho menos que la incertidumbre de cada predicción (±0.5–0.6 t/ha al 80 %).

    ### 7.3 Casos especiales
    """)
    codigo("""
    xy_lab = T.loc[ETIQUETADAS, ["x_m", "y_m"]].to_numpy()
    d120 = np.linalg.norm(xy_lab - T.loc["AGC_120", ["x_m", "y_m"]].to_numpy(float), axis=1)
    caso = {"municipio": T.loc["AGC_120", "Municipio"], "etiquetas en su municipio": int((T.loc[ETIQUETADAS, "Municipio"] == T.loc["AGC_120", "Municipio"]).sum()),
            "K1": T.loc["AGC_120", "K1_corregido"], "vecina etiquetada más cercana": ETIQUETADAS[d120.argmin()], "distancia (km)": round(d120.min() / 1000, 2),
            "etiquetadas en su celda CHIRPS": int((T.loc[ETIQUETADAS, "celda"] == T.loc["AGC_120", "celda"]).sum()), "grupo de J": T.loc["AGC_120", "grupo"]}
    print("AGC_120:", caso)
    display(DET.loc[["AGC_120"], MODELOS + ["E_JK − MIX"]].round(3))
    SIN_K1 = list(DET.index[DET["sin K1 (K = MIX)"]])
    SIN_CELDA = list(DET.index[DET["celda CHIRPS sin etiquetas"]])
    vj = FX[INFO["J_variable"]]
    print("Sin K1 (K cae a MIX):", SIN_K1)
    print("En celdas CHIRPS sin parcelas etiquetadas:", SIN_CELDA, "| valor de la variable de J:", vj.loc[SIN_CELDA].round(2).tolist(),
          f"| rango en las etiquetadas: {vj.loc[ETIQUETADAS].min():.2f}–{vj.loc[ETIQUETADAS].max():.2f}")
    assert caso["etiquetas en su municipio"] == 1 and not np.isfinite(caso["K1"]) and caso["distancia (km)"] == 1.26
    assert len(SIN_K1) == 9 and np.allclose(DET.loc[SIN_K1, "K"], DET.loc[SIN_K1, "MIX"]) and len(SIN_CELDA) == 2
    assert vj.loc[SIN_CELDA].between(vj.loc[ETIQUETADAS].min(), vj.loc[ETIQUETADAS].max()).all()
    """, "casos-especiales")
    texto("""
    * **AGC_120 (Nanacamilpa)** es el caso más débil de la entrega:
      * MUN usa la única etiqueta de su municipio (AGC_048, 2.5 t/ha);
      * no tiene K1, así que K = MIX;
      * su vecina etiquetada más cercana está a 1.26 km, más allá del alcance donde la vecindad informa (sección 4.2);
      * J usa su grupo regional.

      Los cinco candidatos van de 2.50 a 2.91 t/ha. Su intervalo, tomado del "resto", **probablemente subestima** la incertidumbre.
    * **9 parcelas sin K1** (sin capturas Planet suficientes o sin ≥2 vecinas): K = MIX exactamente, y E_JK = ½J + ½MIX.
    * **2 parcelas en celdas CHIRPS sin etiquetas** (AGC_147, AGC_174): la variable de J está dentro del rango observado, así que no hay extrapolación. Aun así, el valor de esa celda nunca se contrastó con un rendimiento.

    ### 7.4 Controles de la entrega
    """)
    codigo("""
    assert list(PRED.index) == list(OCULTAS) and PRED.index.is_unique and len(PRED) == 59
    assert set(PRED.index) == set(meta.loc[meta.CONJUNTO.eq("PREDICCION"), ID])
    assert np.isfinite(PRED.to_numpy()).all()
    assert PRED.E_JK.between(y.min(), y.max()).all()
    R2_, I2_ = candidatos(ETIQUETADAS, OCULTAS, internas(ETIQUETADAS, SEMILLA_FINAL))
    assert all(np.array_equal(R2_[m], PRED[m].to_numpy()) for m in MODELOS)
    # Fuga: (a) ninguna etiqueta de las 59 existe; (b) va nunca recibe rendimientos (assert en referencias);
    # (c) si cambiamos las X de las otras ocultas, la selección de J y su coeficiente no cambian (solo usan el entrenamiento).
    FX_orig = FX.copy()
    FX.loc[OCULTAS] = FX.loc[OCULTAS] * 0 + 999.0
    _, I3_ = candidatos(ETIQUETADAS, OCULTAS[:1], internas(ETIQUETADAS, SEMILLA_FINAL))
    FX = FX_orig
    assert I3_["J_variable"] == INFO["J_variable"] and I3_["J_coef"] == INFO["J_coef"] and I3_["K"] == INFO["K"]
    # (d) control positivo: cambiar una etiqueta de entrenamiento sí cambia las predicciones (los controles anteriores no son triviales).
    y_alt = y.copy(); y_alt.iloc[0] += 1.0
    alt, _ = candidatos(ETIQUETADAS, OCULTAS, internas(ETIQUETADAS, SEMILLA_FINAL), etiquetas_y=y_alt)
    assert not np.array_equal(alt["MIX"], PRED.MIX.to_numpy())
    print(f"59 IDs únicos = lista PREDICCION; sin NaN; rango {PRED.E_JK.min():.2f}–{PRED.E_JK.max():.2f} dentro de lo observado ({y.min():.2f}–{y.max():.2f}); "
          "réplica idéntica; selección de J y β independientes de las X de las ocultas; el modelo sí responde a las etiquetas de entrenamiento.")
    """, "controles")
    codigo("""
    from pathlib import Path
    RAIZ = next((p for p in [Path.cwd(), Path.cwd().parent] if (p / "pyproject.toml").exists() and (p / "notebooks").exists()), Path.cwd())
    SAL = RAIZ / "resultados/04_seleccion_modelo_final"
    SAL.mkdir(parents=True, exist_ok=True)
    salidas = {
        "predicciones_59.csv": PRED[["E_JK"]].rename(columns={"E_JK": Y}).to_csv(float_format="%.4f"),
        "intervalos_59.csv": DET[["Municipio", "zona", "E_JK", "inferior 80 %", "superior 80 %", "inferior 90 %", "superior 90 %"]]
            .rename(columns={"E_JK": "prediccion_t_ha", "inferior 80 %": "inferior_80", "superior 80 %": "superior_80", "inferior 90 %": "inferior_90", "superior 90 %": "superior_90"})
            .to_csv(float_format="%.4f"),
        "detalle_59.csv": DET.to_csv(float_format="%.17g"),
    }
    salidas["resumen.json"] = json.dumps({
        "modelo_entrega": "E_JK = 0.5*J + 0.5*K", "referencia": "MIX", "semilla_interna_K": SEMILLA_FINAL,
        "K": INFO["K"], "J_variable": INFO["J_variable"], "J_coeficientes": INFO["J_coef"],
        "cuantiles_residuos": {f"{z}|{n}": list(v) for (z, n), v in Q.items()}, "cobertura": COB.to_dict(orient="index"),
        "sin_K1": SIN_K1, "celdas_sin_etiquetas": SIN_CELDA, "caso_AGC_120": {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in caso.items()},
        "sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in salidas.items()},
    }, indent=2, ensure_ascii=False, default=float) + "\\n"
    for nombre, contenido in salidas.items():
        p = SAL / nombre
        if p.exists():
            assert p.read_text(encoding="utf-8") == contenido, f"{p} ya existe con otro contenido: no se sobrescribe"
            estado = "idéntico al existente"
        else:
            p.write_text(contenido, encoding="utf-8")
            estado = "escrito"
        print(f"{nombre}: {estado} (sha256 {hashlib.sha256(contenido.encode()).hexdigest()[:16]}…)")
    print("Carpeta:", SAL)
    """, "salidas")
    texto("""
    Las bases del reto no fijan un formato para el archivo de predicciones; lo revisamos en los documentos *Introducción al Reto* y *Descripción general y parcelas*. Por eso `predicciones_59.csv` usa las mismas columnas que el archivo original de etiquetas: `ID_POLIGONO` y `RENDIMIENTO_T_HA`. Los intervalos van aparte, en `intervalos_59.csv`.

    Si los archivos ya existen, el notebook **no los sobrescribe**: verifica que sean idénticos. Así, una segunda ejecución en un kernel limpio comprueba el determinismo de la entrega. **Ningún archivo se envía a ningún lado.**
    """)

    # ------------------------------------------------------------------ 8
    texto("""
    ## 8. Preguntas guía de las bases

    Las importancias de variables de un modelo sin control territorial son engañosas aquí: cualquier variable que cambie entre regiones parece "importante" porque sustituye al municipio. Por eso respondemos con evidencia que **controla el territorio**.

    ### 8.1 ¿Cuál es el índice más importante?

    **Respuesta.** El **NDVI de Planet**, pero no su valor absoluto, sino su **integral de temporada comparada con la de las parcelas vecinas a menos de 1 km** (K1). Es el único índice que mostró señal *dentro* del municipio. Su efecto es pequeño y no siempre se repite: lo que añade K a MIX en cada evaluación es:
    """)
    codigo("""
    aporte_k = (rm.K - rm.MIX).rename("K − MIX (t/ha)").to_frame()
    aporte_k["mejora relativa"] = (1 - rm.K / rm.MIX).map("{:.1%}".format)
    display(aporte_k.round(4))
    assert (rm.K <= rm.MIX + 1e-12).all()
    """, "guia-indice")
    texto("""
    El aporte va de ≈0 % (CV de Opus R2) a 2.8 % (caja). El signo es negativo: más verde y más temprana que sus vecinas → menos rendimiento que su territorio. Una explicación plausible, no demostrada, es que siembras o desarrollos más tempranos quedan más expuestos a heladas o déficit en el llenado.

    ### 8.2 ¿Qué variable climática tiene mayor peso?

    **Respuesta.** La que elige J en 97 de 100 pliegues y en el ajuste final: la **anomalía de lluvia de octubre** (`anom_precip_pct_d`), con +0.017 t/ha por punto porcentual. Pero **funciona como ubicación, no como clima**.
    """)
    codigo("""
    je = csv_insumo("j_elegidas")
    display(je.groupby(["conjunto", "variable"]).size().rename("pliegues (de 50)").to_frame())
    g = T.assign(v=FX["anom_precip_pct_d"])
    r2_por = {k: float(1 - ((g.v - g.groupby(k).v.transform("mean")) ** 2).sum() / ((g.v - g.v.mean()) ** 2).sum()) for k in ["celda", "Municipio", "grupo"]}
    print("R² de anom_precip_pct_d explicado por:", {k: round(v, 4) for k, v in r2_por.items()}, "| celdas distintas:", T.celda.nunique())
    assert r2_por["celda"] >= 0.99
    """, "guia-clima")
    texto("""
    La celda CHIRPS de ≈5 km explica **más del 99.9 %** de su variación. Dentro de una celda, todas las parcelas tienen prácticamente el mismo valor. J la usa para distinguir zonas dentro de su grupo regional; no mide la lluvia que recibió cada parcela. **No puede interpretarse como "la lluvia de octubre causa el rendimiento".**

    ### 8.3 ¿Cuál es la mejor combinación de variables?

    **Respuesta.** Ubicación (municipio + vecinas) + contraste NDVI con las vecinas + nivel regional con la anomalía de lluvia, en un promedio de dos modelos. El aporte incremental, con cifras ya calculadas (CV, SEEN135):
    """)
    codigo("""
    gl = csv_insumo("oof_global_hist")
    gl = gl[gl.modelo.eq("Media global")].merge(w[w.conjunto.eq("historicas")][["repeticion", "pliegue", ID, "municipio_visto"]], on=["repeticion", "pliegue", ID], validate="1:1")
    glob = gl[gl.municipio_visto]
    inc = pd.DataFrame({
        "agrega": ["media global", "+ municipio", "+ vecinas (IDW)", "+ contraste NDVI vecinal", "(J solo: grupo + anomalía de lluvia)", "promedio J y K"],
        "modelo": ["GLOBAL", "MUN", "MIX", "K", "J", "E_JK"],
        "RMSE históricas": [metricas(glob.observado, glob.predicho)["RMSE"]] + [rm.loc["1 CV histórica (138, SEEN)", m] for m in ["MUN", "MIX", "K", "J", "E_JK"]],
        "RMSE nuevas": [np.nan] + [rm.loc["2 CV nueva (138, SEEN)", m] for m in ["MUN", "MIX", "K", "J", "E_JK"]],
    }).set_index("modelo")
    display(inc.round(4))
    assert len(glob) == 1350 and inc.loc["GLOBAL", "RMSE históricas"] > 0.8
    """, "guia-combinacion")
    texto("""
    El salto grande es **GLOBAL → MUN**: saber el municipio reduce el error de ≈0.85 a ≈0.49. Cada paso siguiente aporta del orden de 0.005 t/ha. Ninguna variable satelital, climática o topográfica por sí sola se acercó al aporte del municipio, porque casi toda su variación también es regional.

    ## 9. ¿Qué necesitaríamos para un mejor modelo?

    ### 9.1 Datos públicos: qué existe y a qué escala (Fase A de la ronda 2)

    | Dato necesario | ¿Existe público? | Escala | Fuente y licencia |
    | --- | --- | --- | --- |
    | Rendimiento medido por parcela, con método documentado | **No** | — | Solo hay rendimiento municipal estimado ([SIAP, SIACON](https://www.gob.mx/siap/documentos/siacon-ng-161430)) |
    | Varias campañas de las mismas parcelas | **No** | — | Solo series municipales (SIAP) |
    | Fecha de siembra, variedad, fertilización, densidad, cultivo anterior | **No** por parcela | Regional | Solo recomendaciones técnicas del INIFAP |
    | Riego o temporal | Solo consulta web | Polígonos 1:10,000 | [SIAP, Frontera Agrícola](https://www.gob.mx/siap/acciones-y-programas/frontera-agricola). Sin descarga reproducible encontrada; la capa ya no se publica por WFS en IDEGEO |
    | Suelo (carbono, textura) | Sí | 250 m (modelado) | [SoilGrids 2.0](https://www.isric.org/explore/soilgrids), CC-BY 4.0 ([Poggio et al., 2021](https://doi.org/10.5194/soil-7-217-2021)). **Probado en la ronda 2 (H2): sin aporte** |
    | Suelo, mapa nacional | Sí | 1:250,000 | [INEGI Edafología](https://www.inegi.org.mx/temas/edafologia/). Demasiado grueso para distinguir parcelas |
    | Elevación fina (posición topográfica, heladas) | Sí | 30 m y 15 m | [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/), licencia libre con atribución; [INEGI CEM 3.0](https://www.inegi.org.mx/app/geo2/elevacionesmex/). **Probado con 30 m (H1): sin aporte** |
    | Temperatura diaria (heladas) | Sí | ≈10 km | [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land), 0.1°. Escala de celda, no de parcela |
    | Rendimiento municipal por año | Sí | Municipio | SIAP. No varía dentro del municipio. Además, la cifra del mismo año sería casi una fuga de información, y su servidor de cierre no respondió el 11 de octubre |

    **Contexto agronómico verificado:**

    * El Altiplano (Hidalgo, Puebla, Tlaxcala y Estado de México) concentra el 75 % de la superficie de cebada maltera, sembrada bajo temporal en verano. Para temporal en el Altiplano se recomienda la variedad Esmeralda, y Adabella en ambientes de buena productividad ([González González et al., 2016](https://www.redalyc.org/pdf/2631/263144153014.pdf)).
    * Los Valles Altos presentan irregularidad de lluvia y **heladas tempranas** ([Zamora Díaz et al., 2017](https://cienciasagricolas.inifap.gob.mx/index.php/agricolas/article/download/317/547/1917)).
    * Una fecha límite de siembra hacia el 30 de julio–5 de agosto apareció en búsquedas, pero **no la verificamos en una fuente primaria**: no se cita.

    ### 9.2 ¿Es el rendimiento reportado por el productor?

    **No está confirmado.** Las bases solo dicen "rendimiento del cultivo al final de cosecha". Hay un indicio: muchas etiquetas son múltiplos exactos de 0.5 t/ha, algo típico de cifras redondeadas de memoria. Este dato **solo se describe; nunca se usó para modelar**.
    """)
    codigo("""
    multiplos = int((np.abs(y * 2 - np.round(y * 2)) < 1e-9).sum())
    print(f"{multiplos} de {len(y)} etiquetas son múltiplos exactos de 0.5 t/ha")
    assert multiplos == 45
    """, "multiplos")
    texto("""
    ### 9.3 Párrafo para el reporte

    > Con los 138 rendimientos disponibles, la ubicación explica la mayor parte de lo que se puede predecir: el municipio solo explica ≈69 % de la variación. De lo que queda, nuestro mejor modelo recupera ≈7 %. Parcelas a menos de 250 m todavía difieren ≈0.42 t/ha. La curva de aprendizaje es casi plana: más parcelas del mismo tipo bajarían el error menos de 0.01 t/ha.
    >
    > Probamos 619 variables propias, fuentes satelitales externas (Sentinel-1/2, AlphaEarth), topografía a 30 m y suelo a 250 m. Ninguna mostró señal dentro del municipio, incluso con una muestra apartada antes del análisis. **Lo que limita al modelo no es el algoritmo, sino la información disponible.**
    >
    > Cuatro datos podrían moverlo:
    >
    > 1. Rendimiento **medido** con un método documentado, como la cosecha de subparcelas. En otros contextos, el rendimiento reportado por el productor se desvía sistemáticamente del medido (Desiere y Jolliffe, 2018; Gourlay, Kilic y Lobell, 2019), y los rendimientos satelitales explican tanto o más la cosecha completa de la parcela que el reporte del productor o la cosecha de subparcelas (Lobell et al., 2020). No sabemos si las etiquetas del reto son reportadas o medidas.
    > 2. **Manejo** por parcela: fecha de siembra, variedad, fertilización y densidad.
    > 3. **Muestreo de suelo** por parcela.
    > 4. **Varias campañas** de las mismas parcelas.
    >
    > Ninguno es público en la zona; obtenerlos requeriría colaborar con FIRA o con las organizaciones de productores. Con varias campañas, además, un modelo jerárquico del tipo de Battese, Harter y Fuller (1988) podría combinar el dato municipal con el de parcela de forma estadísticamente fundada.

    ### 9.4 Estado de verificación de las referencias

    Se verificó, el 11 de octubre de 2026, que cada referencia existe y dice lo que se le atribuye:

    | Referencia | Qué se le atribuye | Estado |
    | --- | --- | --- |
    | Lobell, D. B., Azzari, G., Burke, M., Gourlay, S., Jin, Z., Kilic, T. y Murray, S. (2020). Eyes in the sky, boots on the ground: Assessing satellite- and ground-based approaches to crop yield measurement and analysis. *American Journal of Agricultural Economics*, 102(1). [PDF](https://web.stanford.edu/~mburke/papers/lobell_et_al_AJAE_2019.pdf) | En Uganda, los rendimientos satelitales explican tanto o más la cosecha completa de la parcela que el reporte del productor o la cosecha de subparcelas | Verificada (publicada en línea en 2019) |
    | Desiere, S. y Jolliffe, D. (2018). Land productivity and plot size: Is measurement error driving the inverse relationship? *Journal of Development Economics*, 130, 84–98. [IDEAS](https://ideas.repec.org/a/eee/deveco/v130y2018icp84-98.html) | En Etiopía, la relación inversa tamaño–productividad aparece con producción reportada y desaparece con cosecha de subparcelas | Verificada |
    | Gourlay, S., Kilic, T. y Lobell, D. B. (2019). A new spin on an old debate: Errors in farmer-reported production and their implications for inverse scale-productivity relationship in Uganda. *Journal of Development Economics*, 141. [IDEAS](https://ideas.repec.org/a/eee/deveco/v141y2019ics0304387818306588.html) | Los productores sobreestiman la producción, sobre todo en parcelas pequeñas | Verificada |
    | Battese, G. E., Harter, R. M. y Fuller, W. A. (1988). An error-components model for prediction of county crop areas using survey and satellite data. *JASA*, 83(401), 28–36. [RTI](https://www.rti.org/publication/error-components-model-prediction-county-crop-areas-using-survey-satellite-data) | Modelo de errores anidados (unidad dentro de área) que combina encuesta y satélite | Verificada |
    | Claeskens, G., Magnus, J. R., Vasnev, A. L. y Wang, W. (2016). The forecast combination puzzle: A simple theoretical explanation. *International Journal of Forecasting*, 32(3), 754–762. [EUR](https://repub.eur.nl/pub/81568) | Estimar los pesos de una combinación añade varianza y sesgo; por eso los pesos iguales suelen ganar | Verificada |
    | White, H. (2000). A reality check for data snooping. *Econometrica*, 68(5), 1097–1126. [Econometric Society](https://www.econometricsociety.org/publications/econometrica/2000/09/01/reality-check-data-snooping) | Prueba de si el mejor de muchos modelos supera a un punto de referencia, descontando la búsqueda | Verificada |
    | Hansen, P. R. (2005). A test for superior predictive ability. *Journal of Business & Economic Statistics*, 23(4), 365–380. [IDEAS](https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html) | Versión mejorada (SPA) del Reality Check | Verificada |
    | Cawley, G. C. y Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *JMLR*, 11, 2079–2107. [JMLR](https://www.jmlr.org/papers/v11/cawley10a.html) | Seleccionar modelos con la misma validación sesga optimistamente el error reportado | Verificada |
    | Varoquaux, G. (2018). Cross-validation failure: Small sample sizes lead to large error bars. *NeuroImage*, 180, 68–77. [arXiv](https://arxiv.org/abs/1706.07581) | Con ~100 casos, las barras de error de la validación cruzada son grandes (≈±10 %) | Verificada |
    | Poggio, L. et al. (2021). SoilGrids 2.0. *SOIL*, 7, 217–240. [DOI](https://doi.org/10.5194/soil-7-217-2021) | Fuente y licencia del suelo de la ronda 2 | Verificada (enlace resuelve) |
    | González González, M., Zamora Díaz, M. y Solano Hernández, S. (2016). *Revista Mexicana de Ciencias Agrícolas*, 7(1), 159–171. [Redalyc](https://www.redalyc.org/pdf/2631/263144153014.pdf) | Altiplano: 75 % de la superficie de cebada maltera, de temporal; variedades Esmeralda y Adabella | Verificada |
    | Zamora Díaz, M. R. et al. (2017). Maravilla: variedad de cebada forrajera para Valles Altos de México. *Revista Mexicana de Ciencias Agrícolas*, 8(6), 1449–1454. [INIFAP](https://cienciasagricolas.inifap.gob.mx/index.php/agricolas/article/download/317/547/1917) | Valles Altos: lluvia irregular y heladas tempranas | Verificada |
    | Fecha límite de siembra 30 de julio–5 de agosto | — | **No verificada**: no se cita |

    ## 10. Límites: lo que esta evidencia no permite afirmar

    * **Causalidad.** Ni K1 ni la anomalía de lluvia demuestran un mecanismo. Son asociaciones predictivas en una campaña, y la anomalía de lluvia actúa como etiqueta de lugar.
    * **Otras campañas.** Todo es abril–octubre de 2025. Un año con otro régimen de lluvias o de heladas puede cambiar el orden de los modelos y el nivel de error.
    * **Municipios nuevos.** Las 59 están en municipios con etiquetas. Para un municipio sin etiquetas, MUN cae a la media global y el error sería mucho mayor (FULL138, EXP_11).
    * **AGC_120.** Su predicción descansa en una sola etiqueta municipal y en vecinas a más de 1 km; su intervalo probablemente subestima la incertidumbre.
    * **Superioridad de E_JK.** No está demostrada estadísticamente: ningún nulo descartó el azar frente a MIX. Lo que sí se sostiene es que E_JK no fue peor que MIX en ninguna evaluación.
    * **Independencia de las evaluaciones.** Todas usan las mismas 138 etiquetas. La caja de 35 es la más limpia, pero se apartó después de EXP_08–11, que ya habían visto esas etiquetas, y la ronda 2 la reutilizó.
    * **Colab.** Este notebook se probó en dos kernels limpios locales con Python 3.13. **No se probó en Colab real.**
    """)
    codigo("""
    resumen = {"id": "NB04", "modo": "seleccion_final_y_59_predicciones", "modelo_final": MODELO_FINAL, "referencia": "MIX",
               "predicciones_59": int(len(PRED)), "componentes_reproducidos": n_filas, "caja_reproducida": dif_caja < 1e-12,
               "decision_ronda2": rr2["decision"], "J_variable": INFO["J_variable"], "beta_K": round(INFO["K"]["beta"], 10),
               "rmse_E_JK": {ev: round(float(rm.loc[ev, "E_JK"]), 6) for ev in rm.index}, "banda_59_E_JK": [round(v, 3) for v in BANDA_EJK],
               "cobertura": {k: {n: round(v, 3) for n, v in d.items()} for k, d in COB.to_dict(orient="index").items()},
               "sha256_salidas": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in salidas.items()}, "colab_real_probado": False}
    print("RESUMEN_04_JSON=" + json.dumps(resumen, ensure_ascii=False, sort_keys=True))
    """, "cierre")

    for i, c in enumerate(cells):
        c.id = f"nb04-{i:03d}"
    md = copy.deepcopy(anterior.metadata)
    md["agrocebada"] = {"id": "NB04", "modo": "seleccion_final_y_59_predicciones", "fecha": "2026-10-11",
                        "crisp_dm": [5, 6], "colab_real_probado": False,
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
    ap.add_argument("--salida", type=Path, default=raiz / SALIDA)
    args = ap.parse_args()
    nb = construir(raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, args.salida)
    print(f"{args.salida}: {len(nb.cells)} celdas")


if __name__ == "__main__":
    main()
