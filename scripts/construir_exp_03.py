"""EXP_03: cuatro descriptores y dos procedimientos; lector autónomo sin ajustes."""
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

BASE_SHA256 = "47c777915832c940bd0df2a8d8339ca77a05953c4921e94a8181141e65bdcc47"


def huella(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def cargar_insumos(raiz: Path) -> dict:
    config = json.loads((raiz / "config/exp_03_variables_y_familias.json").read_text())
    salida = {}
    for nombre, contrato in config["insumos"].items():
        contenido = (raiz / contrato["ruta_local"]).read_bytes()
        if len(contenido) != contrato["bytes"] or huella(contenido) != contrato["sha256"]:
            raise ValueError(f"Insumo distinto del contrato: {nombre}")
        if not 0 < len(contenido) <= 2*1024*1024:
            raise ValueError("Insumo excede límite de lectura")
        salida[nombre] = {**contrato, "contenido": contenido}
    return salida


def construir(raiz: Path | None = None) -> nbformat.NotebookNode:
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    cfg_path = raiz / "config/exp_03_variables_y_familias.json"
    cfg = json.loads(cfg_path.read_text())
    base_path = raiz / "notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb"
    if huella(base_path.read_bytes()) != BASE_SHA256:
        raise ValueError("Cambió el soporte de referencia; revisar antes de construir")
    base = nbformat.read(base_path, as_version=4)
    tags = {t: c for c in base.cells for t in c.metadata.get("tags", [])}
    registros = {k: {**{a: b for a, b in v.items() if a != "contenido"},
                     "bytes_zlib_base64": base64.b64encode(zlib.compress(v["contenido"], 9)).decode()}
                 for k, v in cargar_insumos(raiz).items()}
    celdas = []

    def texto(contenido):
        celdas.append(nbformat.v4.new_markdown_cell(dedent(contenido).strip()))

    def codigo(contenido, tag, titulo=None):
        c = nbformat.v4.new_code_cell(dedent(contenido).strip())
        c.metadata["tags"] = [tag]
        if titulo:
            c.source = f'# @title {titulo} {{ display-mode: "form" }}\n'+c.source
            c.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        celdas.append(c)

    def reutilizar(tag):
        # Solo al construir: la salida incrusta todo y no requiere otros notebooks.
        c = copy.deepcopy(tags[tag])
        c.execution_count = None
        c.outputs = []
        c.metadata.pop("execution", None)
        celdas.append(c)

    texto("""
    # EXP_03. ¿La forma de las curvas aporta, y cambia la respuesta con árboles?

    **CRISP-DM: preparar, modelar y evaluar.** Una media de todo el ciclo puede ocultar
    cambios de la curva. Añadimos cuatro descriptores definidos por calendario y
    separamos dos preguntas: efecto del bloque y efecto de usar otro procedimiento.

    **Cambio clave frente a EXP_02:** conservamos las seis variables **originales de
    E2**; no sustituimos sus medias por las de T1. Añadimos forma temporal. Diseño
    2 × 2: seis/diez numéricas × Ridge/HGB, más las referencias GLOBAL, MUN y MIX.

    **Lector retrospectivo, cero ajustes.** Recalculamos cuatro variables desde
    capturas y métricas de OOF **guardadas**. Verificamos selección desde scores
    guardados, sin recalcular scores, entrenamientos, OOF ni las 59 predicciones finales.

    Original: **29 de septiembre de 2026 en México** (la corrida UTC inicia el 30).
    Adaptación: **8 de octubre**. Python histórico 3.12.14/scikit-learn 1.9.1; lectura
    Python 3.13. Registro local exploratorio, posterior a EDA, sin sello externo.

    **Recorrido:** hipótesis → capturas → cuatro descriptores → 2 × 2 → errores → decisión.
    Basta este `.ipynb` en Colab, en orden: no necesita ZIP, Drive, Git ni otro cuaderno.
    Dos bloques técnicos plegados; las operaciones científicas permanecen visibles.
    """)
    texto("""
    ## 1. Preparación e identidad de las fuentes

    Colab prepara solo NumPy, pandas y Matplotlib con el perfil uv. Si cambia un módulo
    cargado, pide reiniciar manualmente. En local no instala nada. «Mostrar código»
    abre los bloques de soporte e insumos: no hay entrenamiento escondido.
    """)
    for tag in ("soporte-colab", "preparar-colab", "entorno"):
        reutilizar(tag)
    texto("""
    | Insumo | Uso aquí | Límite |
    | --- | --- | --- |
    | Recortes de capturas originales | Recalcular dos series y cuatro descriptores | Derivados el 8/oct, no inscritos en septiembre |
    | Seis variables E2 y etiquetas aparte | Conservar base y verificar rendimiento | No se usan 539 columnas como predictores |
    | Particiones y scores interiores | Comprobar roles y selección | No repetir 3,800 ajustes |
    | OOF guardadas | Recalcular métricas y diferencias | No son etiquetas adicionales |
    | Controles, manifiesto y registro | Contrastar después del cálculo | No certifican fecha ante terceros |

    Los recortes conservan NaN y seleccionan columnas, sensor y abril–octubre de 2025.
    No filtran nubes ni usan rendimiento. Se reutilizan los recortes verificados del
    8/oct: hashes originales y derivados separados. Sentinel NDVI está disponible en
    el recorte, pero **no es una tercera serie temporal nueva** en esta hipótesis.
    """)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    codigo("INSUMOS_INCRUSTADOS = "+repr(registros)+"\n\n"+decoder,
           "insumos-tecnicos", "Insumos: descompresión limitada, tamaño, SHA-256 y uso")
    codigo("""
    MAN = json.loads(bytes_insumo("manifiesto", "receta_historica"))
    REG = json.loads(bytes_insumo("registro", "registro_historico"))
    RECORTES = __RECORTES__
    X = leer_csv("variables_base", "predictores_fuente")
    etiquetas = leer_csv("etiquetas", "etiquetas")
    externas = leer_csv("externas", "particiones")
    internas = leer_csv("internas", "particiones")
    planet = leer_csv("capturas_planet", "capturas_derivadas")
    s2 = leer_csv("capturas_s2", "capturas_derivadas")
    assert X.shape == (197, 539) and X.ID_POLIGONO.is_unique
    assert len(etiquetas) == 138 and etiquetas.ID_POLIGONO.is_unique
    assert np.isfinite(etiquetas.RENDIMIENTO_T_HA).all()
    assert set(etiquetas.ID_POLIGONO) <= set(X.ID_POLIGONO)
    for key, d in [("planet", planet), ("s2", s2)]:
        assert len(d) == RECORTES[key]["filas"] and set(d.ID_POLIGONO) == set(X.ID_POLIGONO)
    display(pd.DataFrame([{"recorte":k, "filas":v["filas"], "sha256_original":v["sha256_original"],
                          "sha256_derivado":v["sha256_recorte"], "fecha":v["fecha_recorte"]} for k,v in RECORTES.items()]))
    print("Registro local:", MAN["registrado_utc"])
    print("Ejecución original UTC:", REG["inicio_utc"], "| noche del 29/sep en México")
    """.replace("__RECORTES__", repr(cfg["recortes_derivados"])), "insumos-visibles")
    texto("""
    ## 2. Qué se conserva y qué añadimos

    Base E2: media, pico del **promedio de parcela** y día del pico NDVI Planet;
    media NDVI y NDWI Sentinel-2; media VI6T Landsat. Las medias son por captura;
    empate del pico → fecha más temprana. No es el píxel extremo.

    | Descriptor nuevo | Operación | Pregunta descriptiva |
    | --- | --- | --- |
    | Planet NDVI jun–jul − abr–may | Diferencia bimestral ponderada por días | ¿Cómo cambia frente al inicio? |
    | Planet NDVI sep–oct − jul–ago | Diferencia bimestral ponderada por días | ¿Cómo cambia hacia el final? |
    | Amplitud mensual Planet NDVI | Máximo − mínimo de siete medias mensuales | ¿Cuánto varía la curva observada? |
    | Sentinel NDWI sep–oct − jul–ago | Diferencia bimestral ponderada por días | ¿Cómo cambia este índice? |

    Son contrastes **calendáricos**, no etapas fenológicas verificadas. NDWI no demuestra
    agua disponible; amplitud no es biomasa. Julio participa en dos contrastes; el bloque
    no aísla el efecto individual de cada descriptor. No entran historia, postciclo,
    clima, calidad, ID, Estado o coordenadas como nuevas entradas de estas variantes.
    """)
    codigo("""
    OLD = MAN["variantes"]["R_B"]["variables"]
    NEW = MAN["variantes"]["R_T"]["variables"][len(OLD):]
    assert len(OLD) == 6 and len(NEW) == 4 and not set(OLD) & set(NEW)
    assert MAN["variantes"]["H_B"]["variables"] == OLD
    assert MAN["variantes"]["H_T"]["variables"] == OLD+NEW
    base_x = X.set_index("ID_POLIGONO")
    base = base_x[["Municipio", "Estado"]+OLD].copy()
    assert np.isfinite(base[OLD]).all().all()
    display(pd.DataFrame({"columna_base_conservada":OLD}))
    display(base.loc[["AGC_001"], OLD])
    print("Seis E2 originales conservadas; las medias sustituidas de T1 no entran.")
    """, "base-visible")
    texto("""
    ## 3. Abrir una curva antes de derivar variables

    AGC_001 es el ejemplo de continuidad, no una parcela escogida por su error.
    Parseamos día/mes/año y contamos capturas con índice presente; NaN no se convierte
    en cero. Sin filtro de nubes, interpolación ni clipping. Siete medias completas
    se exigen a **Planet NDVI y Sentinel NDWI**, no a todas las series de E2.
    """)
    codigo("""
    DIAS = pd.Series([30,31,30,31,31,30,31], index=range(4,11), name="dias_mes")

    def medias_mensuales(datos, sensor, campo, ids):
        ids = list(ids)
        columnas = ["ID_POLIGONO", "sensor", "fecha_captura", campo]
        if not ids or len(set(ids)) != len(ids) or not set(columnas) <= set(datos):
            raise ValueError("IDs o columnas incompatibles")
        df = datos[columnas].copy()
        if df[columnas[:3]].isna().any().any() or set(df.ID_POLIGONO) != set(ids) or not df.sensor.eq(sensor).all():
            raise ValueError("ID, sensor o fecha incompatible")
        if not df.fecha_captura.astype(str).str.fullmatch(r"\\d{2}/\\d{2}/\\d{4}").all():
            raise ValueError("Formato de fecha distinto de dd/mm/aaaa")
        df["fecha"] = pd.to_datetime(df.fecha_captura, format="%d/%m/%Y", errors="raise")
        if not df.fecha.between("2025-04-01", "2025-10-31").all() or df.duplicated(["ID_POLIGONO","sensor","fecha"]).any():
            raise ValueError("Ventana o duplicados incompatibles")
        df[campo] = pd.to_numeric(df[campo], errors="raise")
        q = df.dropna(subset=[campo]).copy()
        if not np.isfinite(q[campo].to_numpy(dtype=float)).all():
            raise ValueError("Valor presente no finito")
        q["mes"] = q.fecha.dt.month
        tabla = q.groupby(["ID_POLIGONO","mes"])[campo].agg(media="mean", n="count").reset_index()
        valores = tabla.pivot(index="ID_POLIGONO", columns="mes", values="media").reindex(index=ids, columns=DIAS.index)
        conteos = tabla.pivot(index="ID_POLIGONO", columns="mes", values="n").reindex(index=ids, columns=DIAS.index)
        if not np.isfinite(valores.to_numpy()).all() or not conteos.gt(0).all().all():
            raise ValueError("Mes ausente o sin valores; no se imputa ni renormaliza")
        tabla["sensor"], tabla["indice"] = sensor, campo
        tabla["dias_mes"] = tabla.mes.map(DIAS)
        return valores, tabla

    ids_todos = X.ID_POLIGONO.tolist()
    P, pm = medias_mensuales(planet, "Planet", "ndvi_promedio", ids_todos)
    W, wm = medias_mensuales(s2, "Sentinel-2", "ndwi_promedio", ids_todos)
    mensuales = pd.concat([pm,wm], ignore_index=True)
    assert len(mensuales) == 197*2*7 == 2758
    abril = planet.loc[planet.ID_POLIGONO.eq("AGC_001") & planet.fecha_captura.str.contains("/04/2025")]
    display(abril[["fecha_captura","ndvi_promedio"]])
    presentes = abril.ndvi_promedio.dropna().to_numpy(dtype=float)
    np.testing.assert_allclose(presentes.sum()/len(presentes), P.loc["AGC_001",4], atol=1e-12, rtol=0)
    ejemplo = mensuales.loc[mensuales.ID_POLIGONO.eq("AGC_001")]
    display(ejemplo[["sensor","indice","mes","media","n","dias_mes"]])
    figura, eje = plt.subplots(figsize=(8,3.4))
    eje.plot(DIAS.index, P.loc["AGC_001"], "o-", label="Planet NDVI")
    eje.plot(DIAS.index, W.loc["AGC_001"], "s-", label="Sentinel-2 NDWI")
    eje.set(xlabel="Mes de 2025", ylabel="Índice medio observado", title="AGC_001: siete medias, no trayectoria diaria reconstruida")
    eje.set_xticks(DIAS.index)
    eje.legend()
    figura.tight_layout()
    plt.show()
    """, "mensuales-visibles")
    texto(r"""
    ## 4. Cuatro operaciones explícitas

    Media del bimestre $B$: $\bar x_B=\sum_{m\in B}d_m\bar x_m/\sum_{m\in B}d_m$.
    Primero agregamos por mes, después por días: no damos más peso a un mes por tener
    más capturas. Jun–jul suma 61 días; jul–ago, 62. La amplitud es entre medias
    **mensuales**, no el máximo de cada captura ni del píxel.
    """)
    codigo("""
    def media_periodo(mensual, meses):
        meses = list(meses)
        if not meses or len(set(meses)) != len(meses) or not set(meses) <= set(DIAS.index):
            raise ValueError("Periodo incompatible con la receta")
        valores = mensual[meses]
        if not np.isfinite(valores.to_numpy(dtype=float)).all():
            raise ValueError("Mes faltante o no finito en contraste")
        pesos = DIAS.loc[meses]
        return valores.mul(pesos, axis=1).sum(axis=1)/pesos.sum()

    def descriptores_temporales(p, w):
        if not p.index.equals(w.index) or not p.columns.equals(DIAS.index) or not w.columns.equals(DIAS.index):
            raise ValueError("IDs o meses incompatibles entre series")
        if not np.isfinite(p.to_numpy()).all() or not np.isfinite(w.to_numpy()).all():
            raise ValueError("Curva mensual incompleta")
        nuevas = pd.DataFrame(index=p.index)
        nuevas[NEW[0]] = media_periodo(p,[6,7])-media_periodo(p,[4,5])
        nuevas[NEW[1]] = media_periodo(p,[9,10])-media_periodo(p,[7,8])
        nuevas[NEW[2]] = p.max(axis=1)-p.min(axis=1)
        nuevas[NEW[3]] = media_periodo(w,[9,10])-media_periodo(w,[7,8])
        return nuevas

    nuevas = descriptores_temporales(P,W)
    periodos = pd.DataFrame({"abr–may":media_periodo(P,[4,5]), "jun–jul":media_periodo(P,[6,7]),
                            "jul–ago":media_periodo(P,[7,8]), "sep–oct":media_periodo(P,[9,10])})
    display(periodos.loc[["AGC_001"]])
    # Comprobación manual de una resta y del intervalo mensual, sin etiquetas.
    p = P.loc["AGC_001"]
    manual = (p[6]*30+p[7]*31)/61-(p[4]*30+p[5]*31)/61
    np.testing.assert_allclose(manual, nuevas.loc["AGC_001",NEW[0]], atol=1e-12, rtol=0)
    np.testing.assert_allclose(p.max()-p.min(), nuevas.loc["AGC_001",NEW[2]], atol=1e-12, rtol=0)
    display(nuevas.loc[["AGC_001"]].T.rename(columns={"AGC_001":"descriptor_calculado"}))
    features = base.join(nuevas, validate="one_to_one")
    assert features.shape == (197,12) and np.isfinite(features[OLD+NEW]).all().all()
    display(features.head())
    """, "descriptores-visibles")
    texto("""
    **Control posterior:** recién ahora abrimos variables y meses guardados. Las seis
    E2 proceden de la integración ya reconstruida; aquí las conservamos y contrastamos,
    no volvemos a extraer geometrías ni las seis fuentes completas. Los campos de
    geometría del control histórico no se incorporan a estos candidatos.
    """)
    codigo("""
    ctrl_features = leer_csv("variables_control","control_posterior").set_index("ID_POLIGONO")
    assert ctrl_features.shape == (197,16) and ctrl_features.index.is_unique
    assert set(ctrl_features.index) == set(features.index)
    np.testing.assert_allclose(features[OLD+NEW].to_numpy(), ctrl_features.loc[ids_todos,OLD+NEW].to_numpy(), atol=1e-12, rtol=0)
    np.testing.assert_array_equal(features[OLD].to_numpy(), base_x.loc[ids_todos,OLD].to_numpy())
    pd.testing.assert_frame_equal(features[["Municipio","Estado"]], ctrl_features.loc[ids_todos,["Municipio","Estado"]])
    ctrl_months = leer_csv("mensuales_control","control_posterior")
    keys_month = ["ID_POLIGONO","sensor","indice","mes"]
    a, b = mensuales.set_index(keys_month).sort_index(), ctrl_months.set_index(keys_month).sort_index()
    assert a.index.is_unique and a.index.equals(b.index)
    np.testing.assert_allclose(a.media,b.media,atol=1e-12,rtol=0)
    np.testing.assert_array_equal(a[["n","dias_mes"]],b[["n","dias_mes"]])
    print("2,758 medias y cuatro variables coinciden a 10⁻¹²; seis E2 originales intactas.")
    """, "variables-control")
    texto("""
    ## 5. El diseño 2 × 2 evita confundir dos cambios

    | | Seis originales + municipio | Añadir cuatro descriptores |
    | --- | --- | --- |
    | Ridge | R_B: control E2 | R_T |
    | HGB | H_B | H_T |

    R_T−R_B y H_T−H_B comparan el bloque dentro de un procedimiento. H_B−R_B y
    H_T−R_T comparan procedimientos con las mismas entradas. No se atribuye una
    diferencia que cambia ambos factores exclusivamente a las variables.

    **Ridge** es lineal regularizado ([documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html)).
    **HGB** combina árboles mediante gradient boosting, una alternativa no lineal
    ([documentación oficial](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)).
    No demuestra que alguna familia sea óptima.

    Ambos: municipio one-hot completo; numéricas → mediana → escala → estimador.
    Todo se aprende dentro de cada entrenamiento. Árboles no requieren escalado;
    mantenerlo común evitó introducir otra diferencia. Municipio desconocido →
    indicadores cero, no fallback explícito global como MUN.
    """)
    codigo("""
    variantes = MAN["variantes"]
    display(pd.DataFrame([{"procedimiento":k,"algoritmo":v["algoritmo"],
                          "numéricas":len(v["variables"]),"municipio":True} for k,v in variantes.items()]))
    display(pd.DataFrame([{"algoritmo":alg,"opción":i,"parámetros":json.dumps(params,sort_keys=True)}
                          for alg, grid in MAN["algoritmos"].items() for i,params in enumerate(grid)]))
    display(pd.DataFrame([MAN["HGB_fijos"]]).T.rename(columns={0:"valor_fijo"}))
    print("Ridge: cinco opciones; HGB: cuatro. No son presupuestos equivalentes ni búsqueda exhaustiva.")
    """, "diseno-visible")
    texto("""
    ## 6. Separar selección interior de evaluación exterior

    FULL138, cinco pliegues × diez repeticiones; cuatro interiores por exterior.
    Los CSV guardados son la autoridad: no buscamos otra semilla ni regeneramos roles.
    Cada interior se contiene en el entrenamiento exterior; nunca incluye su evaluación.
    """)
    reutilizar("particiones-visibles")
    texto("""
    **Selector:** RMSE de errores interiores concatenados, no media de cuatro RMSE.
    Tolerancia 10⁻¹². La primera opción dentro del mínimo favorece Ridge alpha mayor;
    HGB menos hojas y, a igual número, más observaciones por hoja. Verificamos decisiones
    desde cinco/cuatro scores almacenados, no volvemos a calcular esos scores.
    """)
    codigo("""
    def seleccionar_parametros(algoritmo, scores):
        if algoritmo not in MAN["algoritmos"]:
            raise ValueError("Algoritmo fuera del protocolo")
        grid = MAN["algoritmos"][algoritmo]
        scores = np.asarray(scores,dtype=float)
        if scores.shape != (len(grid),) or not np.isfinite(scores).all() or (scores<0).any():
            raise ValueError("Scores incompatibles")
        elegido = int(np.flatnonzero(scores <= scores.min()+1e-12)[0])
        return grid[elegido]

    seleccion = leer_csv("seleccion","scores_guardados")
    assert len(seleccion) == 200 and set(seleccion.modelo) == set(variantes)
    assert not seleccion.duplicated(["modelo","repeticion","pliegue"]).any()
    exteriores = set(externas.groupby(["repeticion","pliegue"]).groups)
    scores_verificados = 0
    for nombre,g in seleccion.groupby("modelo"):
        assert len(g) == 50 and set(zip(g.repeticion,g.pliegue)) == exteriores
        alg = variantes[nombre]["algoritmo"]
        for _,fila in g.iterrows():
            scores = json.loads(fila.scores_internos)
            guardado = json.loads(fila.parametros)
            assert seleccionar_parametros(alg,scores) == guardado
            scores_verificados += len(scores)
    assert scores_verificados == 900
    ejemplo_seleccion = seleccion.loc[seleccion.repeticion.eq(0)&seleccion.pliegue.eq(0)]
    display(ejemplo_seleccion)
    print("200 decisiones / 900 scores guardados. No hay errores internos individuales para recalcular scores.")
    print("Presupuesto histórico: 900 opciones × 4 interiores + 200 reajustes = 3,800. Actual: 0.")
    """, "seleccion-visible")
    texto("""
    Anidar evita una fuga durante selección, pero no borra exploración previa sobre las
    mismas 138 etiquetas. Elegir después el mejor de cuatro añade sesgo de selección.
    Este resultado sigue siendo exploratorio, no una prueba confirmatoria independiente.

    ## 7. Control histórico y claves OOF

    R_B reprodujo E2 antes de probar las otras variantes; las tres referencias también
    se contrastaron contra sus OOF previas a 10⁻⁸ t/ha, con alphas E2 iguales. Hoy
    cotejamos **registros guardados**; no reproducimos esos entrenamientos de nuevo.
    MIX = 0.5 MUN + 0.5 IDW, k=20, potencia 2 y piso 1 m; coordenadas solo allí.
    """)
    codigo("""
    todos = leer_csv("oof","resultados_guardados")
    modelos = ["GLOBAL","MUN","MIX","R_B","R_T","H_B","H_T"]
    esperado = set(map(tuple,validaciones[claves].to_numpy()))
    oficial = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    assert len(todos) == 9660 and set(todos.modelo) == set(modelos)
    assert not todos.duplicated(["modelo"]+claves).any()
    assert set(todos.ID_POLIGONO) == set(oficial.index)
    for _,g in todos.groupby("modelo"):
        assert len(g) == 1380 and set(map(tuple,g[claves].to_numpy())) == esperado
        np.testing.assert_allclose(g.observado,g.ID_POLIGONO.map(oficial),atol=0,rtol=0)
        assert np.isfinite(g[["observado","predicho"]].to_numpy()).all()
        for campo in ["Municipio","Estado"]:
            np.testing.assert_array_equal(g[campo],g.ID_POLIGONO.map(base[campo]))
    assert todos.zona.eq(np.where(todos.Municipio.eq("Chignahuapan"),"Chignahuapan","Resto")).all()
    old_oof = leer_csv("oof_ronda1","resultados_guardados")
    refs = leer_csv("referencias","resultados_guardados")
    alias = {"GLOBAL":"Media global","MUN":"Media municipal","MIX":"Municipio + IDW fijo"}
    controles_delta = {}
    for actual,previo in {"R_B":"E2",**alias}.items():
        origen = old_oof if actual == "R_B" else refs
        a = todos.loc[todos.modelo.eq(actual)].set_index(claves).sort_index()
        b = origen.loc[origen.modelo.eq(previo)].set_index(claves).sort_index()
        assert a.index.is_unique and a.index.equals(b.index) and len(a) == 1380
        np.testing.assert_allclose(a.observado,b.observado,atol=0,rtol=0)
        np.testing.assert_allclose(a.predicho,b.predicho,atol=1e-8,rtol=0)
        controles_delta[actual] = float(np.abs(a.predicho-b.predicho).max())
    alpha_previos = leer_csv("alpha_ronda1","scores_guardados").query("modelo == 'E2'")
    rb = seleccion.query("modelo == 'R_B'").merge(alpha_previos,on=["repeticion","pliegue"],validate="one_to_one")
    assert len(rb) == 50
    assert all(json.loads(p)["alpha"] == a for p,a in zip(rb.parametros,rb.alpha,strict=True))
    for _,fila in rb.iterrows():
        previo = [fila[f"rmse_interno_alpha_{p['alpha']:g}"] for p in MAN["algoritmos"]["Ridge"]]
        np.testing.assert_allclose(json.loads(fila.scores_internos),previo,atol=1e-8,rtol=0)
    display(pd.Series(controles_delta,name="máximo_delta_OOF_guardadas"))
    todos["error"] = todos.predicho-todos.observado
    todos["error2"] = todos.error**2
    print("9,660 OOF conciliadas, siete procedimientos, 138 etiquetas. Cero predicciones finales.")
    """, "oof-validacion")
    texto(r"""
    ## 8. Recalcular errores antes de abrir el control

    Cada fila evalúa los mismos 1,380 errores de FULL138. RMSE/MAE en t/ha;
    R² sin unidades. $RMSE=\sqrt{\overline{e^2}}$, $MAE=\overline{|e|}$,
    $R^2=1-\sum e^2/\sum(y-\bar y)^2$. Denominador ≤10⁻¹² → NaN.
    No promediar primero diez predicciones por parcela ni los RMSE de pliegues.
    """)
    codigo("""
    def metricas(df):
        y,p = df.observado.to_numpy(dtype=float),df.predicho.to_numpy(dtype=float)
        if len(y) == 0 or not np.isfinite(y).all() or not np.isfinite(p).all():
            raise ValueError("Métrica vacía o no finita")
        e = p-y
        denom = np.sum((y-y.mean())**2)
        return pd.Series({"RMSE":np.sqrt(np.mean(e**2)),"MAE":np.mean(np.abs(e)),
                          "R2":1-np.sum(e**2)/denom if denom>1e-12 else np.nan})

    resultados = pd.DataFrame({k:metricas(g) for k,g in todos.groupby("modelo")}).T.loc[modelos]
    display(resultados.round(9))
    figura,ejes = plt.subplots(1,2,figsize=(10,3.6))
    candidatos = ["R_B","R_T","H_B","H_T"]
    for eje,m in zip(ejes,["RMSE","MAE"]):
        resultados.loc[candidatos,m].plot.bar(ax=eje,color=["#718096","#207f89","#718096","#207f89"])
        referencia = "MIX" if m == "RMSE" else "MUN"
        eje.axhline(resultados.loc[referencia,m],color="#a14b3a",linestyle="--",label=referencia)
        eje.set_ylabel(m+" (t/ha)")
        eje.set_xlabel("")
        eje.tick_params(axis="x",rotation=0)
        eje.legend()
    figura.suptitle("FULL138: el contraste 2 × 2 debe superar referencias, no solo otra variante")
    figura.tight_layout()
    plt.show()
    control = leer_csv("metricas_control","control_posterior").set_index("modelo")
    assert control.index.is_unique and set(control.index) == set(modelos)
    np.testing.assert_allclose(resultados.to_numpy(),control.loc[modelos,["RMSE","MAE","R2"]].to_numpy(),atol=1e-12,rtol=0)
    """, "metricas-visibles")
    texto("""
    R_T empeora R_B: RMSE 0.5192 → 0.5293; MAE 0.3597 → 0.3759.
    H_T baja RMSE de H_B: 0.5804 → 0.5770, pero sube MAE 0.4151 → 0.4229.
    HGB queda por detrás de Ridge bajo estas rejillas. No equivale a demostrar
    superioridad universal de Ridge ni inutilidad de los árboles.

    ## 9. Comparaciones pareadas y regla de avance

    Negativo favorece al primer procedimiento. La regla original exigía RMSE menor
    que MIX y MAE no mayor que MUN, con cada sentido en ≥8/10 repeticiones.
    Es regla de desarrollo, no la rúbrica oficial ni significancia estadística.
    Las diez repeticiones reutilizan datos: sus rangos no son intervalos de confianza.
    """)
    codigo("""
    rep = pd.DataFrame([{"modelo":k,"repeticion":r,**metricas(g).to_dict()}
                        for (k,r),g in todos.groupby(["modelo","repeticion"])])
    rr = rep.pivot(index="repeticion",columns="modelo",values="RMSE")
    rm = rep.pivot(index="repeticion",columns="modelo",values="MAE")
    pares = MAN["comparaciones"]+[[k,b] for k in variantes for b in ["MUN","MIX"]]
    contrastes = pd.DataFrame([{"modelo":k,"base":b,
        "delta_RMSE":resultados.loc[k,"RMSE"]-resultados.loc[b,"RMSE"],
        "delta_MAE":resultados.loc[k,"MAE"]-resultados.loc[b,"MAE"],
        "reps_menor_RMSE":int((rr[k]<rr[b]).sum()),
        "reps_menor_MAE":int((rm[k]<rm[b]).sum())} for k,b in pares])
    display(contrastes)
    ctrl_pares = leer_csv("contrastes_control","control_posterior").set_index(["modelo","base"])
    actual = contrastes.set_index(["modelo","base"])
    assert actual.index.is_unique and set(actual.index) == set(ctrl_pares.index)
    np.testing.assert_allclose(actual.to_numpy(),ctrl_pares.loc[actual.index,actual.columns].to_numpy(),atol=1e-12,rtol=0)
    regla = pd.DataFrame([{"procedimiento":k,
        "RMSE_menor_MIX":bool(resultados.loc[k,"RMSE"]<resultados.loc["MIX","RMSE"]),
        "MAE_no_mayor_MUN":bool(resultados.loc[k,"MAE"]<=resultados.loc["MUN","MAE"]),
        "reps_RMSE_menor_MIX":int((rr[k]<rr.MIX).sum()),
        "reps_MAE_no_mayor_MUN":int((rm[k]<=rm.MUN).sum())} for k in variantes]).set_index("procedimiento")
    regla["cumple"] = regla.RMSE_menor_MIX & regla.MAE_no_mayor_MUN & regla.reps_RMSE_menor_MIX.ge(8) & regla.reps_MAE_no_mayor_MUN.ge(8)
    assert not regla.cumple.any()
    display(regla)
    """, "pareadas-visibles")
    texto("""
    El bloque mejora RMSE de Ridge solo en 1/10; con HGB en 6/10, pero empeora
    MAE global. **Ninguna variante cumple la regla**. No rescatamos la prueba eligiendo
    solo su métrica favorable.

    ## 10. Territorio y dependencia de dos focos

    Conservamos 71 parcelas de Chignahuapan y 67 del resto. La sensibilidad sin
    AGC_127/171 ya estaba prevista; modifica solo puntuación, no entrenamiento.
    No elimina supuestos datos malos ni sirve para escoger otro modelo por región.
    """)
    codigo("""
    zonas = pd.DataFrame([{"modelo":k,"zona":z,"parcelas":g.ID_POLIGONO.nunique(),**metricas(g).to_dict()}
                          for (k,z),g in todos.groupby(["modelo","zona"])])
    display(zonas.loc[zonas.modelo.isin(candidatos+["MIX"])])
    ep = todos.groupby(["ID_POLIGONO","modelo"]).error2.mean().unstack()
    ep["delta_Ridge"] = ep.R_T-ep.R_B
    ep["delta_HGB"] = ep.H_T-ep.H_B
    focos = ["AGC_127","AGC_171"]
    display(ep[["delta_Ridge","delta_HGB"]].loc[focos])
    display(pd.DataFrame({"mejoran":[int(ep[c].lt(0).sum()) for c in ["delta_Ridge","delta_HGB"]],
        "empeoran":[int(ep[c].gt(0).sum()) for c in ["delta_Ridge","delta_HGB"]],
        "suma_delta_MSE":[ep[c].sum() for c in ["delta_Ridge","delta_HGB"]]},index=["Ridge","HGB"]))
    print("ΔMSE: error cuadrático medio por parcela; suma en (t/ha)², no ΔSSE de 1,380 OOF.")
    sin_focos = todos.loc[~todos.ID_POLIGONO.isin(focos)]
    sensibilidad = pd.DataFrame({k:metricas(g) for k,g in sin_focos.groupby("modelo")}).T.loc[modelos]
    display(sensibilidad)
    control_sens = leer_csv("sensibilidad_control","control_posterior").set_index("modelo")
    np.testing.assert_allclose(sensibilidad.to_numpy(),control_sens.loc[modelos,["RMSE","MAE","R2"]].to_numpy(),atol=1e-12,rtol=0)
    assert sin_focos.ID_POLIGONO.nunique() == 136 and len(sin_focos) == 7*1360
    assert resultados.loc["H_T","RMSE"]<resultados.loc["H_B","RMSE"]
    assert sensibilidad.loc["H_T","RMSE"]>sensibilidad.loc["H_B","RMSE"]
    """, "sensibilidad-visible")
    texto("""
    Al puntuar las otras 136, se invierte la pequeña mejora HGB: H_B RMSE 0.541243;
    H_T 0.544034. Los dos focos compensaban deterioros del resto. Es sensibilidad
    exploratoria prevista, no una validación independiente ni una propuesta de retirarlos.
    Para Ridge, el cambio en Chignahuapan es pequeño (0.6033 → 0.6028) y fuera
    empeora (0.4118 → 0.4382): no hay avance territorial uniforme.

    ## 11. Decisión y siguiente pregunta

    **Cierre conservado: no adoptar el bloque ni reemplazar las referencias.**
    R_T empeora; H_T intercambia una reducción frágil de RMSE por mayor MAE.
    Ninguno supera la regla frente a MIX/MUN. Se conserva la prueba negativa.

    Límite: solo estas cuatro variables, calendarios, rejillas, una temporada y
    FULL138. No descarta clima, nuevas representaciones, otras familias o calidad.
    No demuestra causalidad ni extrapolación. Tampoco confunde fidelidad de cálculo
    con validación agronómica o desempeño oficial en las 59 parcelas.

    **Continuidad:** evaluar otra hipótesis concreta de representación, con sus
    referencias y reglas propias. La siguiente ronda histórica aborda lluvia de
    octubre; no la incorporamos a V1 ni anticipamos su resultado.

    Registro local: 29/sep; ejecución: noche del 29 en México, 30 en UTC; adaptación:
    8/oct. Hash identifica bytes, no certifica anterioridad externa ni acuerdo del equipo.
    """)
    codigo("""
    resumen = {"id":"EXP_03","modo":"lector_retrospectivo_sin_ajustes",
        "parcelas":197,"etiquetas":138,"medias_mensuales":len(mensuales),
        "variables_base":OLD,"variables_nuevas":NEW,"procedimientos":7,
        "oof_por_procedimiento":1380,"oof_total":len(todos),
        "particiones_externas":50,"particiones_internas":200,
        "decisiones_verificadas":len(seleccion),"scores_guardados_verificados":scores_verificados,
        "ajustes_actuales":0,"predicciones_finales_generadas":0,"poblacion":"FULL138",
        "scores_interiores_recalculados":False,"predicciones_recalculadas":False,
        "variables_recalculadas":True,"metricas_recalculadas":True,"variantes_adoptadas":[],
        "fecha_original":"2026-09-29","fecha_adaptacion":"2026-10-08",
        "metricas":resultados.to_dict(orient="index"),"fecha_ejecucion_utc":FECHA_EJECUCION_UTC}
    print("RESUMEN_EXP_03_JSON="+json.dumps(resumen,sort_keys=True))
    print("Cierre: cuatro variables y resultados históricos conciliados; cero ajustes actuales.")
    """, "cierre")
    texto("""
    ## Referencias y glosario breve

    **Descriptor:** resumen definido de una curva. **Diseño 2 × 2:** cruzar dos
    representaciones con dos procedimientos para separar comparaciones.
    **HGB:** gradient boosting con árboles e histogramas. **Ridge:** regresión lineal L2.
    **OOF:** predicción guardada para una parcela apartada. **Selección interior:**
    elegir parámetros sin usar la evaluación exterior. **Sensibilidad:** cambiar una
    condición explícita de puntuación, no ocultar casos para promover un resultado.

    scikit-learn developers. (s. f.). *Ridge* [Documentación de software].
    https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html

    scikit-learn developers. (s. f.). *HistGradientBoostingRegressor* [Documentación de software].
    https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html

    **Evidencia incorporada del equipo:** protocolo, manifiesto `V1_temporal_2x2`,
    registro y tablas, 29/sep/2026 en México; controles E2 y referencias. Los contratos
    del cuaderno identifican sus bytes. No hace falta abrir otros archivos para seguirlo.
    """)
    nb = nbformat.v4.new_notebook(cells=celdas)
    nb.metadata = {"kernelspec":copy.deepcopy(base.metadata.kernelspec),
        "language_info":{"name":"python","version":"3.13"},
        "agrocebada":{**{k:cfg[k] for k in ("id","modo","fecha_original","fecha_adaptacion","ajustes_actuales")},
            "crisp_dm":[3,4,5],"colab_real_probado":False,
            "perfil_sha256":base.metadata.agrocebada.perfil_sha256,
            "soporte_sha256":base.metadata.agrocebada.soporte_sha256,
            "fuentes_sha256":{str(base_path.relative_to(raiz)):BASE_SHA256,
                              "config/exp_03_variables_y_familias.json":huella(cfg_path.read_bytes())},
            "recortes_derivados":cfg["recortes_derivados"],
            "insumos":{k:{a:b for a,b in v.items() if a!="bytes_zlib_base64"} for k,v in registros.items()},
            "dependencias_requeridas":dict(base.metadata.agrocebada.dependencias_requeridas)}}
    for i,c in enumerate(nb.cells,1):
        c.id = f"exp03-{i:02d}"
    nbformat.validate(nb)
    return nb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--salida",type=Path,required=True)
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("La construcción requiere una salida nueva")
    args.salida.parent.mkdir(parents=True,exist_ok=True)
    nbformat.write(construir(args.raiz),args.salida)
    print(f"Lector generado sin entrenar: {args.salida}")


if __name__ == "__main__":
    main()
