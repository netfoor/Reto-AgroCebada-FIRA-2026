"""Construye EXP_02: capturas→medias→evaluación histórica; cero ajustes de modelo."""
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

BASE_SHA256 = "c74f4703d46a83022d675c42e5834ffea721112be531edab5deae6592b7e318c"


def huella(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def cargar_insumos(raiz: Path) -> dict:
    config = json.loads((raiz / "config/exp_02_ponderacion_temporal.json").read_text())
    salida = {}
    for nombre, contrato in config["insumos"].items():
        contenido = (raiz / contrato["ruta_local"]).read_bytes()
        if len(contenido) != contrato["bytes"] or huella(contenido) != contrato["sha256"]:
            raise ValueError(f"Insumo diferente del contrato: {nombre}")
        if not 0 < len(contenido) <= 2*1024*1024:
            raise ValueError("Insumo excede el límite del lector")
        salida[nombre] = {**contrato, "contenido": contenido}
    return salida


def construir(raiz: Path | None = None) -> nbformat.NotebookNode:
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    config_path = raiz / "config/exp_02_ponderacion_temporal.json"
    config = json.loads(config_path.read_text())
    base_path = raiz / "notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb"
    if huella(base_path.read_bytes()) != BASE_SHA256:
        raise ValueError("Cambió el soporte de referencia: revisar antes de construir")
    base = nbformat.read(base_path, as_version=4)
    # Reutilización solo al construir. La salida contiene las celdas completas y
    # nunca necesita otro notebook, archivo .py o configuración al ejecutarse.
    por_tag = {tag: c for c in base.cells for tag in c.metadata.get("tags", [])}
    registros = {
        nombre: {**{k: v for k, v in reg.items() if k != "contenido"},
                 "bytes_zlib_base64": base64.b64encode(zlib.compress(reg["contenido"], 9)).decode()}
        for nombre, reg in cargar_insumos(raiz).items()
    }
    celdas = []

    def texto(contenido):
        celdas.append(nbformat.v4.new_markdown_cell(dedent(contenido).strip()))

    def codigo(contenido, tag, titulo=None):
        celda = nbformat.v4.new_code_cell(dedent(contenido).strip())
        celda.metadata["tags"] = [tag]
        if titulo:
            celda.source = f'# @title {titulo} {{ display-mode: "form" }}\n'+celda.source
            celda.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        celdas.append(celda)

    def reutilizar(tag):
        celda = copy.deepcopy(por_tag[tag])
        celda.execution_count = None
        celda.outputs = []
        celda.metadata.pop("execution", None)
        celdas.append(celda)

    texto("""
    # EXP_02. ¿Cambiar el peso de los meses mejora la predicción?

    **CRISP-DM: preparar datos, modelar y evaluar.** Una media por captura concede
    más peso a los meses con más valores disponibles. La hipótesis T1 cambia esa
    representación: primero promediar dentro de cada mes; después ponderar las siete
    medias por los días del mes. Preguntamos si mejora E2, no si su aritmética era errónea.

    **Lector retrospectivo: cero ajustes de modelo.** Reconstruimos tres variables
    desde capturas reales y recalculamos métricas de OOF **guardadas**. No recalculamos
    predicciones, scores interiores ni las 59 predicciones finales.

    Trabajo original: **29 de septiembre de 2026**, posterior a exploración del 24.
    Adaptación: **8 de octubre de 2026**. El original usó Python 3.12.14/scikit-learn
    1.9.1; este lector usa Python 3.13. Es la segunda ronda histórica, no otra búsqueda.

    **Recorrido:** capturas → pesos → tres variables → comparación pareada → decisión.
    Sube solo este `.ipynb` a Colab y ejecuta en orden. Contiene capturas, tablas y
    controles; no necesita Drive, ZIP, Git ni otro cuaderno. Dos bloques técnicos están
    plegados; todos los cálculos que explican el experimento permanecen visibles.
    """)
    texto("""
    ## 1. Entorno e insumos: ¿qué corre realmente?

    Colab prepara NumPy, pandas y Matplotlib con las versiones de uv. Si cambia un
    módulo ya cargado, solicita reiniciar manualmente. En local no instala nada.
    «Mostrar código» abre los dos bloques técnicos: entorno y tablas comprimidas.
    No contienen un modelo oculto ni extracción científica sin explicar.
    """)
    for tag in ("soporte-colab", "preparar-colab", "entorno"):
        reutilizar(tag)
    texto("""
    | Insumo | Uso | Alcance |
    | --- | --- | --- |
    | Capturas Planet NDVI y Sentinel-2 NDVI/NDWI | Reconstruir medias mensuales | Recortes nuevos de los CSV originales, no resultados entrenados |
    | Variables y etiquetas separadas | Comprobar columnas y rendimientos | 197 parcelas; solo 138 etiquetas |
    | Particiones y scores guardados | Revisar roles y elección de alpha | No reproducir scores mediante ajustes |
    | OOF guardadas | Calcular errores y métricas | No son 1,380 etiquetas independientes |
    | Tablas de control, manifiesto y registro | Contrastar después | Hash comprueba integridad, no anterioridad externa |

    Los recortes se crearon **el 8 de octubre**, no se registraron el 29 de septiembre.
    Seleccionan columnas, sensor y abril–octubre de 2025; conservan los valores ausentes.
    No filtran nubes, agrupan, interpolan ni usan rendimiento. Los CSV originales se
    comprobaron byte a byte contra miembros de `DataSet.zip` durante la preparación.
    Sus hashes y los de los recortes se muestran por separado.
    """)
    decoder = por_tag["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    codigo("INSUMOS_INCRUSTADOS = "+repr(registros)+"\n\n"+decoder,
           "insumos-tecnicos", "Tablas: descompresión limitada, SHA-256 y contrato de uso")
    codigo("""
    MAN = json.loads(bytes_insumo("manifiesto", "receta_historica"))
    REG = json.loads(bytes_insumo("registro", "registro_historico"))
    RECORTES = __RECORTES__
    X = leer_csv("variables", "predictores_fuente")
    etiquetas = leer_csv("etiquetas", "etiquetas")
    externas = leer_csv("externas", "particiones")
    internas = leer_csv("internas", "particiones")
    planet = leer_csv("capturas_planet", "capturas_derivadas")
    s2 = leer_csv("capturas_s2", "capturas_derivadas")
    assert X.shape == (197, 539) and X.ID_POLIGONO.is_unique
    assert len(etiquetas) == 138 and etiquetas.ID_POLIGONO.is_unique
    assert etiquetas.RENDIMIENTO_T_HA.notna().all()
    assert set(etiquetas.ID_POLIGONO) <= set(X.ID_POLIGONO)
    assert len(planet) == RECORTES["planet"]["filas"] == 26255
    assert len(s2) == RECORTES["s2"]["filas"] == 9986
    display(pd.DataFrame([{"recorte": k, "capturas": v["filas"],
                          "sha256_original": v["sha256_original"], "sha256_recorte": v["sha256_recorte"],
                          "fecha_recorte": v["fecha_recorte"]} for k, v in RECORTES.items()]))
    display(planet.head())
    print("T1 registrado localmente:", MAN["registrado_utc"], "| Exploratorio, posterior a EDA.")
    """.replace("__RECORTES__", repr(config["recortes_derivados"])), "insumos-visibles")
    texto("""
    ## 2. Una parcela: de las capturas a una media mensual

    AGC_001 sirve de ejemplo, no se elige por mejorar su rendimiento. Abrimos abril
    de Planet NDVI: parseo explícito `día/mes/año`; NaN significa ausencia, no cero.
    Calculamos suma/conteo de valores presentes. Esta prueba no incorpora un filtro de
    calidad: conserva la misma regla histórica, **sin filtro de nubes**.
    """)
    codigo("""
    ejemplo = planet.loc[planet.ID_POLIGONO.eq("AGC_001")].copy()
    ejemplo["fecha"] = pd.to_datetime(ejemplo.fecha_captura, format="%d/%m/%Y", errors="raise")
    ejemplo["mes"] = ejemplo.fecha.dt.month
    abril = ejemplo.loc[ejemplo.mes.eq(4), ["fecha_captura", "ndvi_promedio"]]
    display(abril)
    valores = abril.ndvi_promedio.dropna().to_numpy(dtype=float)
    assert len(valores) > 0 and np.isfinite(valores).all()
    media_abril = valores.sum()/len(valores)
    mensual_ejemplo = ejemplo.groupby("mes").ndvi_promedio.agg(media="mean", n="count").reindex(range(4, 11))
    np.testing.assert_allclose(media_abril, mensual_ejemplo.loc[4, "media"], atol=1e-12, rtol=0)
    print("Capturas abril:", len(abril), "| Valores presentes:", len(valores), "| Media:", media_abril)
    """, "una-media-visible")
    texto(r"""
    ## 3. ¿Qué cambia exactamente en la ponderación?

    Para el mes $m$, $\bar x_m$ es su media y $n_m$ su número de valores presentes:

    $\text{por captura}=\sum_m n_m\bar x_m/\sum_m n_m$;
    $\text{T1}=\sum_m d_m\bar x_m/214$.

    Días: **30, 31, 30, 31, 31, 30, 31**, abril–octubre. T1 pondera medias mensuales,
    no cada captura directamente por días. Cada captura del mes recibe efectivamente
    peso $d_m/(214n_m)$. No equivale a reconstruir un promedio diario verdadero.
    """)
    codigo("""
    DIAS = pd.Series([30, 31, 30, 31, 31, 30, 31], index=range(4, 11), name="dias_mes")
    assert DIAS.sum() == 214
    assert mensual_ejemplo.n.gt(0).all() and mensual_ejemplo.media.notna().all()
    mensual_ejemplo["peso_capturas"] = mensual_ejemplo.n/mensual_ejemplo.n.sum()
    mensual_ejemplo["peso_dias"] = DIAS/DIAS.sum()
    mensual_ejemplo["aporte_capturas"] = mensual_ejemplo.media*mensual_ejemplo.peso_capturas
    mensual_ejemplo["aporte_dias"] = mensual_ejemplo.media*mensual_ejemplo.peso_dias
    media_capturas = mensual_ejemplo.aporte_capturas.sum()
    media_temporal = mensual_ejemplo.aporte_dias.sum()
    media_uniforme_meses = mensual_ejemplo.media.mean()
    display(mensual_ejemplo)
    print("Por captura:", media_capturas, "| Por días (T1):", media_temporal,
          "| Meses iguales (otra receta):", media_uniforme_meses)
    figura, ejes = plt.subplots(1, 2, figsize=(10, 3.5))
    mensual_ejemplo[["peso_capturas", "peso_dias"]].plot.bar(ax=ejes[0], color=["#718096", "#207f89"])
    mensual_ejemplo.media.plot(marker="o", ax=ejes[1], color="#207f89")
    ejes[0].set_ylabel("Peso: fracción del total")
    ejes[1].set_ylabel("NDVI medio observado")
    for eje in ejes:
        eje.set_xlabel("Mes de 2025")
        eje.tick_params(axis="x", rotation=0)
    figura.suptitle("AGC_001 / Planet: cambia el peso, no los valores observados")
    figura.tight_layout()
    plt.show()
    """, "pesos-visibles")
    texto("""
    Planet NDVI pasa de **0.402093 a 0.426709** para esta parcela. Es una definición
    diferente, no una mejora predictiva demostrada. La media uniforme de meses es otra
    receta y no se ensaya. Los resúmenes de Andrea por captura no estaban mal calculados.

    ## 4. Generalizar la regla y detener inconsistencias

    Esta función visible no recibe etiquetas. Exige fechas, sensor, IDs y valores
    finitos presentes; rechaza duplicados. Un mes sin valores detiene: no lo imputa,
    borra ni redistribuye su peso. Conserva las observaciones ausentes hasta contarlas.
    """)
    codigo("""
    def agregar_meses(datos, sensor, campo, ids):
        ids = list(ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("Lista de parcelas vacía o duplicada")
        columnas = ["ID_POLIGONO", "sensor", "fecha_captura", campo]
        if not set(columnas) <= set(datos.columns):
            raise ValueError("Faltan columnas de capturas")
        df = datos[columnas].copy()
        if df[columnas[:3]].isna().any().any():
            raise ValueError("ID, sensor o fecha ausente")
        if set(df.ID_POLIGONO) != set(ids) or not df.sensor.eq(sensor).all():
            raise ValueError("Sensor o cobertura de parcelas incompatible")
        if not df.fecha_captura.astype(str).str.fullmatch(r"\\d{2}/\\d{2}/\\d{4}").all():
            raise ValueError("Formato de fecha distinto de dd/mm/aaaa")
        df["fecha"] = pd.to_datetime(df.fecha_captura, format="%d/%m/%Y", errors="raise")
        if not df.fecha.between("2025-04-01", "2025-10-31").all():
            raise ValueError("Captura fuera de la ventana registrada")
        if df.duplicated(["ID_POLIGONO", "sensor", "fecha"]).any():
            raise ValueError("Captura duplicada")
        df[campo] = pd.to_numeric(df[campo], errors="raise")
        validos = df.dropna(subset=[campo]).copy()
        if not np.isfinite(validos[campo].to_numpy(dtype=float)).all():
            raise ValueError("Valor presente no finito")
        validos["mes"] = validos.fecha.dt.month
        mensual = validos.groupby(["ID_POLIGONO", "mes"])[campo].agg(media="mean", n="count")
        medias = mensual.media.unstack().reindex(index=ids, columns=DIAS.index)
        conteos = mensual.n.unstack().reindex(index=ids, columns=DIAS.index)
        if not np.isfinite(medias.to_numpy()).all() or not conteos.gt(0).all().all():
            raise ValueError("Mes ausente o sin valores; no se imputa")
        original = (medias*conteos).sum(axis=1)/conteos.sum(axis=1)
        temporal = (medias*DIAS).sum(axis=1)/DIAS.sum()
        tabla = mensual.reset_index()
        tabla["dias_mes"] = tabla.mes.map(DIAS)
        return temporal, original, tabla

    CAMBIOS = {"C_PL_ndvi_media": (planet, "Planet", "ndvi_promedio"),
               "C_S2_ndvi_media": (s2, "Sentinel-2", "ndvi_promedio"),
               "C_S2_ndwi_media": (s2, "Sentinel-2", "ndwi_promedio")}
    FIJAS = ["C_PL_ndvi_pico_prom", "C_PL_ndvi_doy_pico_prom", "C_LS_vi6t_media"]
    assert list(CAMBIOS) == MAN["cambios"]
    np.testing.assert_array_equal(DIAS.to_numpy(), MAN["pesos_dias"])
    ids_todos = X.ID_POLIGONO.tolist()
    atributos = X.set_index("ID_POLIGONO")[["Municipio", "Estado"]+list(CAMBIOS)+FIJAS].copy()
    originales = pd.DataFrame(index=ids_todos)
    tablas_mensuales = []
    for nombre, (fuente, sensor, campo) in CAMBIOS.items():
        temporal, original, mensual = agregar_meses(fuente, sensor, campo, ids_todos)
        originales[nombre] = original
        atributos[nombre] = temporal
        tablas_mensuales.append(mensual.assign(variable=nombre))
    mensuales = pd.concat(tablas_mensuales, ignore_index=True)
    assert len(mensuales) == 197*3*7 == 4137
    display(atributos.head())
    print("197 parcelas × 3 variables × 7 meses: 4,137 medias calculadas sin rendimiento.")
    """, "agregacion-visible")
    texto("""
    **Comprobación posterior:** ahora consultamos los controles guardados. La media
    por captura debe recuperar la receta anterior; la ponderada debe recuperar T1.
    Los picos, fecha del pico, VI6T y municipio permanecen fijos. Tolerancia absoluta
    10⁻¹²: CSV y lectura flotante pueden diferir en los últimos decimales.
    """)
    codigo("""
    base_x = X.set_index("ID_POLIGONO")
    np.testing.assert_allclose(originales.to_numpy(), base_x.loc[ids_todos, list(CAMBIOS)].to_numpy(), atol=1e-12, rtol=0)
    guardado = leer_csv("atributos", "control_posterior").set_index("ID_POLIGONO")
    assert guardado.index.is_unique and set(guardado.index) == set(ids_todos)
    np.testing.assert_allclose(atributos[list(CAMBIOS)+FIJAS].to_numpy(),
                               guardado.loc[ids_todos, list(CAMBIOS)+FIJAS].to_numpy(), atol=1e-12, rtol=0)
    np.testing.assert_allclose(atributos[FIJAS].to_numpy(), base_x.loc[ids_todos, FIJAS].to_numpy(), atol=0, rtol=0)
    pd.testing.assert_frame_equal(atributos[["Municipio", "Estado"]], guardado.loc[ids_todos, ["Municipio", "Estado"]])
    claves_mes = ["ID_POLIGONO", "variable", "mes"]
    control_meses = leer_csv("mensuales", "control_posterior")
    assert not control_meses.duplicated(claves_mes).any()
    actual = mensuales.set_index(claves_mes).sort_index()
    esperado_mes = control_meses.set_index(claves_mes).sort_index()
    assert actual.index.equals(esperado_mes.index)
    np.testing.assert_allclose(actual.media, esperado_mes.media, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(actual[["n", "dias_mes"]], esperado_mes[["n", "dias_mes"]])
    delta_variables = atributos[list(CAMBIOS)]-originales
    display(delta_variables.describe().T[["mean", "std", "min", "max"]])
    display(pd.DataFrame({"por_captura": originales.loc["AGC_001"],
                          "por_dias_T1": atributos.loc["AGC_001", list(CAMBIOS)]}))
    print("Medias mensuales y finales coinciden con los controles; tres columnas fijas intactas.")
    """, "variables-control")
    texto("""
    ## 5. Misma comparación, selección separada de evaluación

    Conservamos **FULL138**, cinco pliegues y diez repeticiones exteriores. Cada
    parcela aparece diez veces fuera de muestra. Los cuatro pliegues interiores
    contienen solo IDs del entrenamiento exterior: sirven para elegir alpha.
    Repetir particiones no crea etiquetas; no son el split oficial del reto.
    """)
    reutilizar("particiones-visibles")
    texto("""
    **Pipeline histórico:** municipio → indicadores completos 0/1 sin escalar;
    seis numéricas → mediana → escala → Ridge con intercepto. Categorías, medianas,
    medias y escalas se aprenden dentro de cada entrenamiento. E0 penaliza efectos
    municipales y no equivale a MUN. En Ridge un municipio desconocido tiene indicadores
    cero; no un fallback explícito a la media global.

    Elegimos Ridge para controlar la representación, no por demostrar que es el modelo
    óptimo. La [definición oficial](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html)
    explica su penalización L2. T1 conserva las seis numéricas, solo sustituye tres.

    **Alpha se reselecciona**, no se fija al de E2: misma rejilla 0.01, 0.1, 1, 10, 100;
    mínimo RMSE de errores interiores concatenados; empate ≤10⁻¹² → mayor alpha.
    La [validación cruzada](https://scikit-learn.org/stable/modules/cross_validation.html)
    separa selección y evaluación, sin convertir la hipótesis posterior a EDA en confirmatoria.
    """)
    codigo("""
    ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)

    def seleccionar_alpha(fila):
        scores = np.array([fila[f"rmse_interno_alpha_{a:g}"] for a in ALPHAS], dtype=float)
        if not np.isfinite(scores).all() or (scores < 0).any():
            raise ValueError("Scores internos inválidos")
        return float(np.array(ALPHAS)[scores <= scores.min()+1e-12].max())

    alpha_t1 = leer_csv("alpha_t1", "scores_guardados")
    alpha_e2 = leer_csv("alpha_control_e2", "scores_guardados")
    clave_pliegue = ["repeticion", "pliegue"]
    exteriores = set(externas.groupby(clave_pliegue).groups)
    for tabla, modelo in [(alpha_t1, "T1"), (alpha_e2, "E2")]:
        assert len(tabla) == 50 and set(tabla.modelo) == {modelo}
        assert not tabla.duplicated(clave_pliegue).any()
        assert set(zip(tabla.repeticion, tabla.pliegue)) == exteriores
        np.testing.assert_array_equal(tabla.apply(seleccionar_alpha, axis=1), tabla.alpha)
    pares_alpha = alpha_t1.merge(alpha_e2, on=clave_pliegue, validate="one_to_one", suffixes=("_T1", "_E2"))
    cambios_alpha = int(pares_alpha.alpha_T1.ne(pares_alpha.alpha_E2).sum())
    fila = alpha_t1.loc[alpha_t1.repeticion.eq(0) & alpha_t1.pliegue.eq(0)].iloc[0]
    display(pd.DataFrame({"alpha": ALPHAS, "RMSE_interno_guardado": [fila[f"rmse_interno_alpha_{a:g}"] for a in ALPHAS]}))
    print("100 decisiones verificadas; cambios de alpha T1 frente a E2:", cambios_alpha)
    assert cambios_alpha == 13
    print("Ajustes históricos: 1,050 T1 + 1,050 control E2 = 2,100. Ajustes actuales: 0.")
    """, "seleccion-visible")
    texto("""
    Los cinco scores por exterior están guardados; sus errores internos individuales,
    coeficientes y transformaciones ajustadas no. Verificamos la elección, **no
    recalculamos scores**. Los 13 cambios de alpha forman parte del mismo procedimiento.

    **Control histórico de entorno:** antes de ensayar T1 se volvió a ejecutar E2
    porque cambió Python/scikit-learn respecto de la ronda anterior. Ahora cotejamos
    esas OOF y scores almacenados con los originales; no afirmamos repetir sus ajustes.
    El control E2 no es otro candidato ni debe duplicarse al contar predicciones.
    """)
    codigo("""
    oof_ronda = leer_csv("oof_ronda1", "resultados_guardados")
    control_oof = leer_csv("oof_control_e2", "resultados_guardados")
    origen_e2 = oof_ronda.loc[oof_ronda.modelo.eq("E2")]
    comparacion_e2 = origen_e2.merge(control_oof, on=["modelo"]+claves,
                                    validate="one_to_one", suffixes=("_original", "_control"))
    assert len(comparacion_e2) == len(control_oof) == len(origen_e2) == 1380
    np.testing.assert_array_equal(comparacion_e2.observado_original, comparacion_e2.observado_control)
    np.testing.assert_array_equal(comparacion_e2.alpha_original, comparacion_e2.alpha_control)
    np.testing.assert_allclose(comparacion_e2.predicho_original, comparacion_e2.predicho_control, atol=1e-8, rtol=0)
    origen_alpha = leer_csv("alpha_ronda1", "scores_guardados")
    origen_alpha = origen_alpha.loc[origen_alpha.modelo.eq("E2")]
    comparacion_alpha = origen_alpha.merge(alpha_e2, on=["modelo"]+clave_pliegue,
                                          validate="one_to_one", suffixes=("_original", "_control"))
    assert len(comparacion_alpha) == 50
    np.testing.assert_array_equal(comparacion_alpha.alpha_original, comparacion_alpha.alpha_control)
    max_score = 0.0
    for a in ALPHAS:
        k = f"rmse_interno_alpha_{a:g}"
        dif = np.abs(comparacion_alpha[k+"_original"]-comparacion_alpha[k+"_control"])
        max_score = max(max_score, float(dif.max()))
        np.testing.assert_allclose(comparacion_alpha[k+"_original"], comparacion_alpha[k+"_control"], atol=1e-8, rtol=0)
    print("Control guardado / original: máximo ΔOOF =", float(np.abs(comparacion_e2.predicho_original-comparacion_e2.predicho_control).max()),
          "| máximo Δscore =", max_score)
    print("Tolerancia histórica: 10⁻⁸; 50 alphas idénticos. No hubo reentrenamiento actual.")
    """, "control-e2-visible")
    texto("""
    ## 6. ¿Son comparables las predicciones que puntuamos?

    Comparadores: GLOBAL, MUN, MIX, E0, E2 y T1. MIX conserva 50 % MUN + 50 % IDW
    (k=20, potencia 2, piso 1 m). Ubicación interviene en MIX, no como coordenadas
    en los candidatos Ridge. Cada procedimiento debe tener exactamente las mismas
    claves `(repetición, pliegue, parcela)` y el rendimiento original.
    """)
    codigo("""
    oof_t1 = leer_csv("oof_t1", "resultados_guardados")
    ref = leer_csv("referencias", "resultados_guardados")
    alias = {"Media global": "GLOBAL", "Media municipal": "MUN", "Municipio + IDW fijo": "MIX"}
    ref = ref.loc[ref.modelo.isin(alias)].copy()
    ref["modelo"] = ref.modelo.map(alias)
    assert set(oof_t1.modelo) == {"T1"}
    ridge = pd.concat([oof_ronda.loc[oof_ronda.modelo.isin(["E0", "E2"])], oof_t1], ignore_index=True)
    seleccion_oof = pd.concat([leer_csv("alpha_ronda1", "scores_guardados").query("modelo in ['E0', 'E2']"), alpha_t1])
    ver_alpha = ridge.merge(seleccion_oof[["modelo"]+clave_pliegue+["alpha"]],
                           on=["modelo"]+clave_pliegue, validate="many_to_one", suffixes=("", "_seleccion"))
    np.testing.assert_array_equal(ver_alpha.alpha, ver_alpha.alpha_seleccion)
    todos = pd.concat([ridge.drop(columns="alpha"), ref], ignore_index=True)
    modelos = ["GLOBAL", "MUN", "MIX", "E0", "E2", "T1"]
    assert set(todos.modelo) == set(modelos) and len(todos) == 8280
    assert not todos.duplicated(["modelo"]+claves).any()
    esperado = set(map(tuple, validaciones[claves].to_numpy()))
    oficial = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    for _, grupo in todos.groupby("modelo"):
        assert len(grupo) == 1380 and set(map(tuple, grupo[claves].to_numpy())) == esperado
        np.testing.assert_allclose(grupo.observado, grupo.ID_POLIGONO.map(oficial), atol=0, rtol=0)
        assert np.isfinite(grupo[["observado", "predicho"]].to_numpy()).all()
    todos = todos.merge(X[["ID_POLIGONO", "Municipio", "Estado"]], on="ID_POLIGONO", validate="many_to_one")
    todos["error"] = todos.predicho-todos.observado
    todos["error2"] = todos.error**2
    todos["zona"] = np.where(todos.Municipio.eq("Chignahuapan"), "Chignahuapan", "Resto")
    print("6 procedimientos × 1,380 OOF: claves y etiquetas verificadas. Sin 59 predicciones finales.")
    """, "oof-validacion")
    texto(r"""
    ## 7. Calcular métricas antes de mirar el control

    $RMSE=\sqrt{\overline{e^2}}$, $MAE=\overline{|e|}$,
    $R^2=1-\sum e^2/\sum(y-\bar y)^2$. RMSE/MAE: t/ha; R²: sin unidades.
    Agrupamos 1,380 errores por procedimiento; no promediamos primero las predicciones
    de cada parcela ni los RMSE de pliegues. Denominador R² ≤10⁻¹² → NaN.
    """)
    codigo("""
    def metricas(df):
        y = df.observado.to_numpy(dtype=float)
        p = df.predicho.to_numpy(dtype=float)
        if len(y) == 0 or not np.isfinite(y).all() or not np.isfinite(p).all():
            raise ValueError("Predicciones vacías o no finitas")
        e = p-y
        denominador = np.sum((y-y.mean())**2)
        return pd.Series({"RMSE": np.sqrt(np.mean(e**2)), "MAE": np.mean(np.abs(e)),
                          "R2": 1-np.sum(e**2)/denominador if denominador > 1e-12 else np.nan})

    resultados = pd.DataFrame({k: metricas(g) for k, g in todos.groupby("modelo")}).T.loc[modelos]
    display(resultados.round(9))
    figura, ejes = plt.subplots(1, 2, figsize=(10, 3.5))
    for eje, metrica in zip(ejes, ["RMSE", "MAE"]):
        resultados[metrica].plot.bar(ax=eje, color=["#718096"]*5+["#207f89"])
        eje.set_ylabel(metrica+" (t/ha)")
        eje.set_xlabel("")
        eje.tick_params(axis="x", rotation=0)
    figura.suptitle("FULL138: cambiar la media no garantiza mejorar la predicción")
    figura.tight_layout()
    plt.show()
    control_metricas = leer_csv("metricas_control", "control_posterior").set_index("modelo")
    assert control_metricas.index.is_unique and set(modelos) <= set(control_metricas.index)
    np.testing.assert_allclose(resultados.to_numpy(), control_metricas.loc[modelos, ["RMSE", "MAE", "R2"]].to_numpy(), atol=1e-12, rtol=0)
    print("Las métricas agrupadas de los seis procedimientos coinciden con el control histórico a 10⁻¹².")
    """, "metricas-visibles")
    texto("""
    T1 RMSE **0.522472** frente a E2 **0.519202**: empeora 0.003270 t/ha.
    MAE baja solo 0.000056 t/ha. No supera MIX en RMSE ni MUN en MAE.
    La comparación es honesta porque cambia la representación, manteniendo el resto
    del procedimiento, pero no demuestra significancia ni desempeño oficial.

    ## 8. ¿Se repite el cambio y es uniforme en el territorio?

    Diferencia pareada: T1 menos comparador, negativa favorece T1. Las divisiones
    comparten datos: su rango no es un intervalo de confianza. Mostramos también
    Chignahuapan y el resto sin elegir otro modelo por región.
    """)
    codigo("""
    rep = pd.DataFrame([{"modelo": k, "repeticion": r, **metricas(g).to_dict()}
                        for (k, r), g in todos.groupby(["modelo", "repeticion"])])
    rep_rmse = rep.pivot(index="repeticion", columns="modelo", values="RMSE")
    rep_mae = rep.pivot(index="repeticion", columns="modelo", values="MAE")
    pareadas = pd.DataFrame({"T1−E2_RMSE": rep_rmse.T1-rep_rmse.E2,
                             "T1−E2_MAE": rep_mae.T1-rep_mae.E2,
                             "T1−MIX_RMSE": rep_rmse.T1-rep_rmse.MIX,
                             "T1−MUN_MAE": rep_mae.T1-rep_mae.MUN})
    display(pareadas)
    mejoras_rmse = int(pareadas["T1−E2_RMSE"].lt(0).sum())
    mejoras_mae = int(pareadas["T1−E2_MAE"].lt(0).sum())
    print("Frente a E2: menor RMSE", mejoras_rmse, "/10; menor MAE", mejoras_mae, "/10.")
    assert mejoras_rmse == 3 and mejoras_mae == 5
    assert pareadas["T1−MIX_RMSE"].gt(0).all() and pareadas["T1−MUN_MAE"].gt(0).all()
    zonas = pd.DataFrame([{"modelo": k, "zona": z, "parcelas": g.ID_POLIGONO.nunique(), **metricas(g).to_dict()}
                          for (k, z), g in todos.groupby(["modelo", "zona"])])
    display(zonas.loc[zonas.modelo.isin(["E2", "T1", "MIX", "MUN"])])
    """, "pareadas-visibles")
    texto("""
    En Chignahuapan (71 etiquetas) RMSE baja ligeramente: 0.6033 → 0.5999;
    MIX sigue en 0.5736. En las otras 67 sube: 0.4118 → 0.4254.
    No es una mejora global uniforme.

    ## 9. ¿De qué parcelas depende? Sensibilidad prevista

    El diagnóstico anterior identificó AGC_127/171. El manifiesto T1 ya incluyó
    omitirlas **solo al calcular métricas**: sensibilidad prevista, exploratoria;
    no retirar etiquetas del entrenamiento ni volver a ajustar modelos.
    Contar cuántas mejoran no basta: importa cuánto cambia el error cuadrático.
    """)
    codigo("""
    error_parcela = todos.groupby(["ID_POLIGONO", "modelo"]).error2.mean().unstack()
    error_parcela["delta_MSE_T1_E2"] = error_parcela.T1-error_parcela.E2
    display(error_parcela[["E2", "T1", "delta_MSE_T1_E2"]].sort_values("delta_MSE_T1_E2").head(5))
    display(error_parcela[["E2", "T1", "delta_MSE_T1_E2"]].sort_values("delta_MSE_T1_E2", ascending=False).head(5))
    print("Menor MSE:", int(error_parcela.delta_MSE_T1_E2.lt(0).sum()),
          "| Mayor MSE:", int(error_parcela.delta_MSE_T1_E2.gt(0).sum()))
    print("Suma ΔMSE de 138 parcelas:", error_parcela.delta_MSE_T1_E2.sum(), "(t/ha)²")
    print("No es ΔSSE de 1,380 OOF: este vale diez veces esa suma.")
    focos = ["AGC_127", "AGC_171"]
    sin_focos = todos.loc[~todos.ID_POLIGONO.isin(focos)]
    sensibilidad = pd.DataFrame({k: metricas(g) for k, g in sin_focos.groupby("modelo")}).T
    display(sensibilidad.loc[["E2", "T1", "MIX", "MUN"]])
    control_sensibilidad = leer_csv("sensibilidad_control", "control_posterior").set_index("modelo")
    np.testing.assert_allclose(sensibilidad.loc[modelos].to_numpy(), control_sensibilidad.loc[modelos, ["RMSE", "MAE", "R2"]].to_numpy(), atol=1e-12, rtol=0)
    assert sin_focos.ID_POLIGONO.nunique() == 136
    assert sensibilidad.loc["T1", "RMSE"] > sensibilidad.loc["E2", "RMSE"]
    """, "sensibilidad-visible")
    texto("""
    Mejoran 71 parcelas y empeoran 67; aun así el RMSE global empeora porque los
    deterioros pesan más. Sin los dos focos, E2 RMSE 0.4685 frente a T1 0.4770.
    Esta población de 136 es un diagnóstico, no la tarea principal ni una nueva
    evaluación independiente. No predice qué ocurriría excluyéndolas al entrenar.

    ## 10. Decisión y límite del resultado negativo

    **Decisión conservada: no promover T1 ni reemplazar la referencia.** Equilibrar
    los pesos parece razonable, pero esta receta concreta no mejora E2 globalmente
    ni supera MIX/MUN. Se conserva la evidencia negativa; no se buscan ventanas o
    alphas nuevos para cambiar el desenlace.

    No demuestra que toda ingeniería temporal, satélite, clima o Ridge sean inútiles.
    No reconstruye la trayectoria diaria verdadera ni identifica fases fenológicas o
    causas. Es una temporada, estas variables y estas particiones de desarrollo.

    **Siguiente pregunta:** estudiar una representación con una hipótesis diferente,
    conservando referencias y separación selección/evaluación. Esa continuidad se
    documentará como otra ronda; no alteramos T1 ni anticipamos su resultado.

    Exploración: 24 de septiembre; registro local y ejecución: 29; recortes/adaptación:
    8 de octubre. No se inventan fechas, sello externo ni ratificación de todo el equipo.
    """)
    codigo("""
    resumen = {
        "id": "EXP_02", "modo": "lector_retrospectivo_sin_ajustes",
        "parcelas": 197, "etiquetas": 138, "medias_mensuales": len(mensuales),
        "variables_modificadas": list(CAMBIOS), "variables_fijas": FIJAS,
        "procedimientos": 6, "oof_por_procedimiento": 1380, "oof_total": len(todos),
        "particiones_externas": 50, "particiones_internas": 200,
        "decisiones_alpha_verificadas": 100, "cambios_alpha_T1_E2": cambios_alpha,
        "ajustes_actuales": 0, "predicciones_finales_generadas": 0, "poblacion": "FULL138",
        "scores_interiores_recalculados": False, "predicciones_recalculadas": False,
        "variables_recalculadas": True, "metricas_recalculadas": True, "T1_adoptado": False,
        "fecha_original": "2026-09-29", "fecha_adaptacion": "2026-10-08",
        "metricas": resultados.to_dict(orient="index"), "fecha_ejecucion_utc": FECHA_EJECUCION_UTC,
    }
    print("RESUMEN_EXP_02_JSON="+json.dumps(resumen, sort_keys=True))
    print("Cierre: receta reconstruida y métricas conciliadas; cero ajustes y cero predicciones finales.")
    """, "cierre")
    texto("""
    ## Referencias y glosario breve

    **Media por captura:** cada valor disponible pesa igual. **Ponderación temporal:**
    cada media mensual pesa según sus días. **NaN:** dato ausente, no cero.
    **OOF:** predicción guardada para una parcela apartada. **Alpha:** fuerza de
    penalización seleccionada dentro del entrenamiento. **Sensibilidad:** cambiar
    explícitamente una condición de evaluación para entender dependencia, no borrar
    casos desfavorables. **Retrospectivo:** organiza y recalcula evidencia ya obtenida.

    scikit-learn developers. (s. f.). *Ridge* [Documentación de software].
    https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html

    scikit-learn developers. (s. f.). *Cross-validation: Evaluating estimator performance*.
    https://scikit-learn.org/stable/modules/cross_validation.html

    **Evidencia del equipo incorporada:** manifiesto `T1_ponderacion_temporal`, registro
    y tablas (29 de septiembre de 2026); integración y referencias originales. Sus bytes
    se identifican en los contratos del cuaderno. No hace falta abrir archivos de
    procedencia para seguir o ejecutar esta lectura.
    """)
    nb = nbformat.v4.new_notebook(cells=celdas)
    nb.metadata = {
        "kernelspec": copy.deepcopy(base.metadata.kernelspec),
        "language_info": {"name": "python", "version": "3.13"},
        "agrocebada": {**{k: config[k] for k in ("id", "modo", "fecha_original", "fecha_adaptacion", "ajustes_actuales")},
                       "crisp_dm": [3, 4, 5], "colab_real_probado": False,
                       "perfil_sha256": base.metadata.agrocebada.perfil_sha256,
                       "soporte_sha256": base.metadata.agrocebada.soporte_sha256,
                       "fuentes_sha256": {"config/exp_02_ponderacion_temporal.json": huella(config_path.read_bytes()),
                                          str(base_path.relative_to(raiz)): BASE_SHA256},
                       "recortes_derivados": config["recortes_derivados"],
                       "insumos": {k: {clave: v for clave, v in reg.items() if clave != "bytes_zlib_base64"} for k, reg in registros.items()},
                       "dependencias_requeridas": dict(base.metadata.agrocebada.dependencias_requeridas)},
    }
    for n, celda in enumerate(nb.cells, 1):
        celda.id = f"exp02-{n:02d}"
    nbformat.validate(nb)
    return nb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("La construcción requiere una salida nueva")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(construir(args.raiz), args.salida)
    print(f"Lector generado sin entrenar: {args.salida}")


if __name__ == "__main__":
    main()
