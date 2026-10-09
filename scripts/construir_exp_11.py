"""EXP_11: lector autónomo de la combinación fija de modelos (cero entrenamientos).

    uv run --locked --all-groups python scripts/construir_exp_11.py
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
CONFIG = "config/exp_11_combinacion_modelos.json"
D = "data/exp_11_combinacion_modelos/"
R = "resultados/exp_11_combinacion_modelos/registrada/"
N = "notebooks/experimentos/exp_11_combinacion_modelos/"
E10 = "resultados/exp_10_verificacion_contraste_vecinal/registrada/"
INSUMOS = {
    "componentes": D + "oof_componentes.csv", "verificacion_insumos": D + "verificacion_insumos.json",
    "j_elegidas": D + "j_variables_elegidas.csv",
    "hist_externas": "data/validacion_03/particiones_externas.csv", "nuevas_externas": "data/exp_09_fuentes_externas/particiones_externas_nuevas.csv",
    "exp10_oof": E10 + "predicciones_oof.csv", "exp10_metricas": E10 + "metricas.csv",
    "metricas_control": R + "metricas.csv", "repeticiones_control": R + "repeticiones.csv", "pares_control": R + "pares.csv",
    "zonas_control": R + "zonas.csv", "municipios_control": R + "municipios.csv", "correlaciones_control": R + "correlaciones.csv",
    "sensibilidades_control": R + "sensibilidades.csv", "no_vistos_control": R + "full138_municipios_no_vistos.csv",
    "lectura_control": R + "lectura.csv", "mezclas_control": R + "predicciones_mezclas.csv",
    "registro_previo": N + "registro_previo.json", "registro_ejecucion": R + "registro_ejecucion.json",
    "verificacion_independiente": N + "verificacion_independiente.json",
    "comparar_fuente": D + "procedencia_jared/comparar.py", "combinacion_fuente": "scripts/combinacion_11.py",
}


def preparar(raiz):
    cfg = {"id": "EXP_11", "modo": "lector_exploratorio_sin_entrenamientos", "fecha_original": "2026-10-08",
           "poblacion_principal": "SEEN135", "poblacion_secundaria": "FULL138", "ajustes_actuales_lector": 0, "insumos": {}}
    for k, ruta in INSUMOS.items():
        b = (raiz / ruta).read_bytes()
        cfg["insumos"][k] = {"ruta_local": ruta, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(), "uso": k, "origen": ruta}
    (raiz / CONFIG).write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    out = {}
    for k, c in cfg["insumos"].items():
        b = (raiz / c["ruta_local"]).read_bytes()
        if not 0 < len(b) <= 2 * 1024 * 1024:
            raise ValueError(f"Insumo demasiado grande: {k}")
        out[k] = {**c, "bytes_zlib_base64": base64.b64encode(zlib.compress(b, 9)).decode()}
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

    texto("""
    # EXP_11. ¿Combinar dos modelos mejora a cada uno por separado?

    **Ronda exploratoria, sin entrenamientos nuevos.** No elige el modelo final ni genera las 59 predicciones.

    ## 1. Qué aprendimos y qué pregunta queda

    * **EXP_10** dejó a **K = MIX + K1 corregido** como alternativa documentada a MIX. K usa un contraste local: el verdor de la parcela frente al de sus vecinas.
    * Una comparación posterior puso al **modelo de Jared (J)** en las mismas particiones. J usa un nivel por grupo regional y una variable elegida entre 148, casi siempre la anomalía de lluvia de octubre.
    * J y K tuvieron un RMSE parecido, pero **mejoraban zonas distintas**: K en Chignahuapan, J fuera de Chignahuapan.

    **Pregunta:** ¿una mezcla fija **E_JK = ½J + ½K** mejora a sus dos componentes? ¿O basta con mezclar K con algo más sencillo, como la media municipal (**E_MK = ½MUN + ½K**)?

    **Advertencia desde el inicio:** esta pregunta nació *después* de ver esos resultados con las mismas 138 etiquetas. El registro previo limita decisiones nuevas, pero no vuelve independiente la evaluación. Las particiones "nuevas" reutilizan esas etiquetas.
    """)
    texto("""
    ## 2. Qué significa combinar predicciones

    Cada modelo ya produjo, para cada parcela de validación, una predicción completa en t/ha. Combinar es promediarlas:

    $$E_{JK} = 0.5\\,\\hat y_J + 0.5\\,\\hat y_K \\qquad E_{MK} = 0.5\\,\\hat y_{MUN} + 0.5\\,\\hat y_K$$

    No se entrena nada nuevo ni se eligen pesos. Promediar **predicciones completas** no es lo mismo que sumar a MIX las correcciones de J y K; eso sería otro procedimiento.

    **Por qué podría mejorar.** Si $e_a$ y $e_b$ son los errores de dos modelos, el error cuadrático medio de su promedio es

    $$\\mathrm{MSE}\\big(\\tfrac{a+b}{2}\\big) = \\tfrac14\\mathrm{MSE}_a + \\tfrac14\\mathrm{MSE}_b + \\tfrac12\\,\\overline{e_a e_b}.$$

    Cuanto menos se parezcan los errores, mayor es la ganancia. Si fueran idénticos, no habría ninguna.

    ## 3. Por qué estas dos mezclas

    * **E_JK** es la hipótesis: J y K podrían compensarse porque usan información distinta (regional frente a local).
    * **E_MK** es el **control**. Mezclar K con la media municipal también reduce a la mitad el peso de la interpolación espacial de MIX. Si E_MK mejorara tanto como E_JK, la ganancia vendría de "menos interpolación" y no de algo propio de Jared.

    ## 4. Qué se mantiene fijo

    | Fijo | Valor |
    | --- | --- |
    | Predicciones de cada componente | Las existentes: MIX, MUN y K de EXP_10; J de la comparación verificada |
    | Pesos | 0.5 y 0.5, sin búsqueda |
    | Particiones | Históricas y nuevas (EXP_09), sin semillas nuevas |
    | Población | SEEN135 principal; FULL138 como sensibilidad |
    | Presupuesto | 2 fórmulas, 0 entrenamientos, 0 variables nuevas, 0 reglas por municipio |

    No se probarán 25/75, stacking, gating ni mezclas regionales, aunque el resultado lo sugiera.
    """)
    for tag in ["soporte-colab", "preparar-colab", "entorno"]:
        reutilizar(tag)
    dec = tags["insumos-tecnicos"].source
    dec = dec[dec.index("def bytes_insumo"):]
    coment = []
    for k in ["comparar_fuente", "combinacion_fuente"]:
        fuente = (raiz / cfg["insumos"][k]["ruta_local"]).read_text()
        coment.append("\n# Fuente completa solo para inspección: " + k + "\n" + "\n".join("#| " + x for x in fuente.splitlines()))
    codigo("INSUMOS_INCRUSTADOS = " + repr(reg) + "\n\n" + dec +
           "\n\ndef csv_insumo(k):\n    return leer_csv(k, INSUMOS_INCRUSTADOS[k]['uso'])\n"
           "def json_insumo(k):\n    return json.loads(bytes_insumo(k, INSUMOS_INCRUSTADOS[k]['uso']))\n" + "\n".join(coment),
           "insumos-tecnicos", "Insumos verificados por SHA-256 y código fuente para inspección; no se ejecuta ningún entrenamiento")

    texto("""
    ## 5. Cómo verificamos que la comparación es justa

    Antes de combinar comprobamos que los cuatro componentes están **exactamente sobre las mismas filas**:

    * misma clave (juego de particiones, repetición, pliegue, parcela);
    * mismo rendimiento observado, municipio y máscara SEEN;
    * ningún duplicado, faltante o valor no finito;
    * filas que coinciden con las particiones originales;
    * MIX, MUN y K iguales a EXP_10. La copia difiere como mucho en 9e-16 por redondeo al leer el CSV, sin efecto en las métricas.

    La procedencia de J se comprobó en la preparación (`scripts/preparar_exp_11.py`):

    * Una **reimplementación independiente** reprodujo sus predicciones desde las variables de Jared sin estandarizar.
    * Su selector **no cambia** si se sustituyen las etiquetas de validación.
    * Sus archivos son idénticos byte a byte a los del ZIP original de Jared.
    * La comparación original estandarizó las 148 variables con las 197 parcelas (solo X). La correlación y la regresión con niveles por grupo no cambian con esa transformación, así que no se modifica.
    """)
    codigo("""
    ID = "ID_POLIGONO"; CLAVE = ["conjunto", "repeticion", "pliegue", ID]
    comp = csv_insumo("componentes"); VI = json_insumo("verificacion_insumos"); PRE = json_insumo("registro_previo")
    REG = json_insumo("registro_ejecucion"); VER = json_insumo("verificacion_independiente")
    assert set(comp.modelo) == {"MIX", "MUN", "J", "K"} and not comp.duplicated(CLAVE + ["modelo"]).any()
    assert comp[["predicho", "observado"]].notna().all().all() and np.isfinite(comp[["predicho", "observado"]].to_numpy(float)).all()
    claves = {m: set(map(tuple, g[CLAVE].to_numpy())) for m, g in comp.groupby("modelo")}
    assert all(c == claves["MIX"] for c in claves.values()) and len(claves["MIX"]) == 2760
    assert (comp.groupby(CLAVE)[["observado", "Municipio", "municipio_visto"]].nunique() == 1).all().all()
    esperadas = set()
    for cj, k in [("historicas", "hist_externas"), ("nuevas", "nuevas_externas")]:
        e = csv_insumo(k); v = e[e.rol.eq("validacion")]
        esperadas |= {(cj, int(r), int(f), i) for r, f, i in v[["repeticion", "pliegue", ID]].to_numpy()}
    assert claves["MIX"] == esperadas
    e10 = csv_insumo("exp10_oof").replace({"modelo": {"K1_corregido": "K"}})
    m10 = comp[comp.modelo.isin(["MIX", "MUN", "K"])].merge(e10, on=CLAVE + ["modelo"], suffixes=("", "_e10"))
    dif10 = (m10.predicho - m10.predicho_e10).abs().max()
    assert len(m10) == 3 * 2760 and dif10 < 1e-12 and (m10.observado == m10.observado_e10).all()
    print(f"MIX/MUN/K frente a EXP_10: diferencia máxima {dif10:.1e} (redondeo de lectura CSV en la preparación; etiquetas idénticas)")
    assert VI["J_reproducido_independiente_desde_variables_sin_estandarizar"] and VI["dif_max_J_reproducido"] < 1e-9 and VI["J_invariante_a_etiquetas_de_validacion"]
    assert PRE["metricas_mezclas_calculadas_antes"] is False and PRE["registrado_utc"] < REG["inicio_utc"]
    assert VER["metricas_reproducidas"] and VER["replica_determinista"] and not VER["originales_cambiados"]
    display(csv_insumo("j_elegidas").groupby(["conjunto", "variable"]).size().rename("pliegues").to_frame())
    print(f"Registro previo {PRE['registrado_utc']} < corrida {REG['inicio_utc']}; reproducción independiente de J: dif. máx. {VI['dif_max_J_reproducido']:.1e}")
    """, "verificacion-visible")

    texto("""
    ## 6. Resultados

    ### 6.1 Las mezclas, calculadas aquí mismo

    Las fórmulas se aplican fila por fila. Cada predicción mezclada queda **entre** sus dos componentes. Las métricas se calculan sobre todas las filas OOF, sin promediar antes por parcela, y deben coincidir con las de la corrida registrada.
    """)
    codigo("""
    w = comp.pivot(index=CLAVE, columns="modelo", values="predicho").join(comp.drop_duplicates(CLAVE).set_index(CLAVE)[["observado", "Municipio", "municipio_visto"]]).reset_index()
    w["E_JK"] = 0.5 * w.J + 0.5 * w.K
    w["E_MK"] = 0.5 * w.MUN + 0.5 * w.K
    for n, (a, b) in {"E_JK": ("J", "K"), "E_MK": ("MUN", "K")}.items():
        assert ((w[n] >= np.minimum(w[a], w[b]) - 1e-12) & (w[n] <= np.maximum(w[a], w[b]) + 1e-12)).all()
    ctrl_mez = csv_insumo("mezclas_control").pivot(index=CLAVE, columns="modelo", values="predicho")
    assert np.abs(w.set_index(CLAVE)[["E_JK", "E_MK"]].sort_index().to_numpy() - ctrl_mez.sort_index()[["E_JK", "E_MK"]].to_numpy()).max() < 1e-12
    MODELOS = ["MIX", "MUN", "J", "K", "E_JK", "E_MK"]

    def met(o, m):
        e = o[m] - o.observado
        return np.sqrt((e ** 2).mean()), e.abs().mean()

    filas = []
    for cj in ["historicas", "nuevas"]:
        for esc in ["SEEN135", "FULL138"]:
            o = w[(w.conjunto == cj) & (w.municipio_visto | (esc == "FULL138"))]
            for m in MODELOS:
                r, a = met(o, m); filas.append({"conjunto": cj, "escenario": esc, "modelo": m, "n_oof": len(o), "RMSE": r, "MAE": a})
    MET = pd.DataFrame(filas)
    ctrl = csv_insumo("metricas_control")
    assert np.allclose(MET.set_index(["conjunto", "escenario", "modelo"]).loc[ctrl.set_index(["conjunto", "escenario", "modelo"]).index, ["RMSE", "MAE"]], ctrl[["RMSE", "MAE"]], atol=1e-12, rtol=0)
    tabla = MET[MET.escenario.eq("SEEN135")].pivot(index="modelo", columns="conjunto", values=["RMSE", "MAE"]).reindex(MODELOS)
    display(tabla.round(5))
    """, "mezclas-visible")
    codigo("""
    S = w[w.municipio_visto]
    pares = csv_insumo("pares_control")
    vista = pares[pares.escenario.eq("SEEN135")].pivot_table(index=["candidato", "referencia"], columns="conjunto", values=["delta_RMSE", "delta_MAE", "reps_mejora_RMSE"])
    display(vista.round(5))
    rep = S.groupby(["conjunto", "repeticion"]).apply(lambda g: pd.Series({m: np.sqrt(((g[m] - g.observado) ** 2).mean()) for m in MODELOS}), include_groups=False)
    fig, ax = plt.subplots(1, 2, figsize=(12, 3.4), sharey=True)
    for a, cj in zip(ax, ["historicas", "nuevas"]):
        r = rep.loc[cj]
        for m, c in [("E_JK", "#1f5f8b"), ("E_MK", "#d68910")]:
            a.plot(r.index, r[m] - r.K, "o-", color=c, label=f"{m} − K")
        a.plot(r.index, r.E_JK - r.J, "s--", color="#1f5f8b", alpha=0.5, label="E_JK − J")
        a.axhline(0, color="k", lw=0.8); a.set_title(f"Particiones {cj}: ΔRMSE por repetición (SEEN135)"); a.set_xlabel("repetición")
    ax[0].set_ylabel("t/ha (negativo = mejora)"); ax[0].legend(fontsize=8); plt.tight_layout(); plt.show()
    ctrl_rep = csv_insumo("repeticiones_control")
    c = ctrl_rep[ctrl_rep.escenario.eq("SEEN135")].pivot_table(index=["conjunto", "repeticion"], columns="modelo", values="RMSE")[MODELOS]
    assert np.allclose(rep[MODELOS].to_numpy(), c.loc[rep.index].to_numpy(), atol=1e-12, rtol=0)
    """, "pares-visible")
    texto("""
    **Lectura de las tablas (SEEN135):**

    * **E_JK** baja el RMSE del mejor componente (K) en **≈0.0063 t/ha (históricas) y ≈0.0066 (nuevas)**, y el de MIX en ≈0.0115 (~2.4 %). Mejora a K en 10/10 repeticiones de ambos juegos, y a J en 10/10 y 9/10.
    * El **MAE** de E_JK (≈0.3214 / 0.3225) mejora a MIX, J y K. Queda prácticamente igual al de MUN: +0.0001 en históricas y +0.0011 en nuevas, ligeramente peor. Es un compromiso pequeño, pero existe.
    * **E_MK no supera a K** en RMSE: +0.0004 y +0.0001, con 5/10 repeticiones en cada juego. Solo bajar el peso de la interpolación **no reproduce** la ganancia.
    * **E_JK frente a E_MK:** −0.0067 en ambos juegos, 10/10 repeticiones. La diferencia entre las dos mezclas está en lo que aporta J.
    """)

    texto("""
    ### 6.2 Por qué funciona: errores muy parecidos, correcciones distintas

    Hay dos correlaciones que **no deben confundirse**:

    * **Entre errores** (ŷ − y): mide cuánto fallan juntos.
    * **Entre cambios respecto a MIX** (ŷ − MIX): mide si corrigen en la misma dirección.
    """)
    codigo("""
    corr = csv_insumo("correlaciones_control")
    display(corr.pivot(index=["tipo", "par"], columns="conjunto", values="pearson").round(3))
    for cj in ["historicas", "nuevas"]:
        o = S[S.conjunto == cj]; ej, ek = o.J - o.observado, o.K - o.observado
        izq = ((0.5 * o.J + 0.5 * o.K - o.observado) ** 2).mean()
        der = 0.25 * (ej ** 2).mean() + 0.25 * (ek ** 2).mean() + 0.5 * (ej * ek).mean()
        assert abs(izq - der) < 1e-14
        print(f"{cj}: MSE_J={np.mean(ej**2):.5f}  MSE_K={np.mean(ek**2):.5f}  promedio(e_J·e_K)={np.mean(ej*ek):.5f}  ⇒ MSE(E_JK)={izq:.5f}")
    """, "correlacion-visible")
    texto("""
    Los errores de J y K se parecen mucho (≈0.94): ambos fallan juntos en las parcelas difíciles, porque ambos parten del territorio. Sus **correcciones** respecto a MIX casi no se parecen (≈0.03). La fórmula muestra que basta esa pequeña parte no compartida para bajar el MSE. **Ninguna de las dos correlaciones prueba la mejora por sí sola: la prueba es la tabla de la sección 6.1.**
    """)

    texto("""
    ### 6.3 ¿Dónde mejora? Zonas y municipios

    Los municipios con menos de 10 parcelas evaluadas (Cuautepec 5, Emiliano Zapata 3) dan cifras muy inestables: se muestran, pero no se interpretan.
    """)
    codigo("""
    z = csv_insumo("zonas_control").pivot_table(index=["conjunto", "zona"], columns="modelo", values="RMSE")[MODELOS]
    display(z.round(4))
    mu = csv_insumo("municipios_control")
    display(mu[mu.conjunto.eq("historicas")].pivot_table(index=["Municipio", "n_parcelas", "muestra_pequena"], columns="modelo", values="RMSE")[MODELOS].round(4))
    """, "zonas-visible")
    texto("""
    E_JK es la mejor opción tanto en **Chignahuapan** como en el **resto**, en ambos juegos. Por municipio no domina en todas partes. En **Calpulalpan** (30 parcelas), MUN y J siguen siendo mejores que E_JK. **No se construyen reglas por municipio con estos resultados**; eso sería una búsqueda nueva.
    """)

    texto("""
    ### 6.4 ¿Está concentrada la ganancia?

    Orden declarado antes de calcular: por parcela, Δ = Σ_repeticiones [(error de la mezcla)² − (error de la referencia)²], de la más favorecida a la menos. Retiramos **solo de la evaluación** las 2 y las 5 primeras. No es una nueva estimación imparcial; todas las parcelas se quedan en los ajustes originales.
    """)
    codigo("""
    sens = csv_insumo("sensibilidades_control")
    display(sens.pivot_table(index=["candidato", "referencia", "retiradas"], columns="conjunto", values="delta_RMSE").round(5))
    """, "concentracion-visible")
    texto("""
    * **Frente a K (su mejor componente):** E_JK sigue mejorando sin las 2 más favorecidas (−0.0035 / −0.0037) y sin las 5 (−0.0008 / −0.0006). La ventaja se reduce mucho, pero no se invierte.
    * **Frente a MIX:** se mantiene clara aun sin 5 parcelas (−0.0044 / −0.0047).
    * **E_MK frente a K:** empeora en cuanto se quitan parcelas.

    **Sensibilidad FULL138.** Incluye 3 parcelas cuyo municipio tiene una sola etiqueta (AGC_047, AGC_048, AGC_164). Cuando se validan, MUN no tiene media de su municipio y usa la media global. J usa su grupo regional y ahí es claramente mejor.
    """)
    codigo("""
    display(MET[MET.escenario.eq("FULL138")].pivot(index="modelo", columns="conjunto", values=["RMSE", "MAE"]).reindex(MODELOS).round(4))
    display(csv_insumo("no_vistos_control").pivot(index="modelo", columns="conjunto", values="RMSE").reindex(MODELOS).round(4))
    """, "full-visible")

    texto("""
    ## 7. Lectura y decisión

    Criterio fijado antes de calcular (no es regla de adopción):

    * **A:** no supera al mejor componente en algún juego.
    * **B:** lo supera en ambos, pero con menos de 8/10 repeticiones frente a algún componente, o la ganancia se invierte sin las 2 parcelas más favorecidas.
    * **C:** lo supera de forma consistente en ambos juegos.

    Para atribuir algo a Jared se exige E_JK < E_MK en ambos juegos, con ≥8/10 repeticiones.
    """)
    codigo("""
    lectura = csv_insumo("lectura_control").set_index("mezcla")
    display(lectura.T)
    clases = REG["clases"]; aporte = REG["aporte_especifico_J"]
    print("Clases:", clases, "| aporte específico de J sobre el control:", aporte)
    assert clases == {"E_JK": "C", "E_MK": "A"} and aporte is True
    resumen = {"id": "EXP_11", "modo": "lector_exploratorio_sin_entrenamientos", "filas_por_modelo": 2760, "formulas": 2,
               "entrenamientos": 0, "busqueda_pesos": 0, "predicciones_59": 0, "clases": clases, "aporte_especifico_J": aporte,
               "rmse_seen": {f"{m}|{cj}": float(tabla.loc[m, ("RMSE", cj)]) for m in MODELOS for cj in ["historicas", "nuevas"]},
               "metricas_recalculadas": True, "colab_real_probado": False}
    print("RESUMEN_EXP_11_JSON=" + json.dumps(resumen, ensure_ascii=False, sort_keys=True))
    """, "cierre")
    texto("""
    ### Qué permite decidir esta ronda

    * **E_JK** queda en la clase **C**. En estos datos se observa **complementariedad predictiva** entre el modelo regional de Jared y la corrección local de K. Merece revisarse como candidato.
    * **E_MK** queda en la clase **A**. El control muestra que la ganancia **no** se explica solo por reducir el peso de la interpolación.

    ### Qué **todavía no** permite decidir

    * **No es un modelo final ni una adopción automática.** La hipótesis nació después de ver los resultados, sobre las mismas etiquetas. Los dos juegos de particiones no son independientes.
    * **K hereda su propia selección exploratoria.** K1 se eligió en EXP_08 viendo las etiquetas, y en EXP_10 no alcanzó evidencia estadística suficiente. E_JK no borra esas reservas.
    * **No hay un nulo estadístico para la mezcla en esta ronda.** La lectura es predictiva, no una prueba de significancia.
    * **No dice nada sobre causalidad agronómica** ni sobre generalización a otras campañas o regiones.
    * **No se han generado las 59 predicciones.** Para ellas haría falta revisar el soporte de J y K en las ocultas, incluido el caso de Nanacamilpa.

    **Continuaciones posibles, NO ejecutadas:** otros pesos (25/75, 75/25), stacking, gating y mezclas regionales. Cualquiera de ellas exigiría un protocolo propio y aumentaría el riesgo de ajustarse a estas mismas etiquetas. La ablación completa sin territorio es otra pregunta y se planificará por separado.

    **Reproducir:** `scripts/preparar_exp_11.py` (insumos y verificación de J), `scripts/experimento_11.py --salida <nueva>`, `scripts/verificar_exp_11_resultados.py` y `pytest tests/test_combinacion_11.py`.
    """)
    for i, c in enumerate(cells):
        c.id = f"exp11-{i:03d}"
    md = copy.deepcopy(anterior.metadata)
    md["agrocebada"] = {"id": "EXP_11", "modo": "lector_exploratorio_sin_entrenamientos", "fecha_original": "2026-10-08",
                        "crisp_dm": [4, 5], "ajustes_actuales": 0, "colab_real_probado": False,
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
    ap.add_argument("--salida", type=Path, default=raiz / N / "exp_11_combinacion_modelos.ipynb")
    args = ap.parse_args()
    nb = construir(raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, args.salida)
    print(f"{args.salida}: {len(nb.cells)} celdas; cero entrenamientos")


if __name__ == "__main__":
    main()
