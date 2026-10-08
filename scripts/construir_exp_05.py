"""EXP05: separar representaciones de octubre, lector retrospectivo sin ajustes."""
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

BASE_SHA256 = "b5086d1acaab17ae53dd9e260692b754bc198f7976dd372696e4b2ba88730f39"


def huella(contenido):
    return hashlib.sha256(contenido).hexdigest()


def cargar_insumos(raiz):
    cfg = json.loads((Path(raiz)/"config/exp_05_historico_octubre.json").read_text())
    salida = {}
    for k,c in cfg["insumos"].items():
        b = (Path(raiz)/c["ruta_local"]).read_bytes()
        if len(b) != c["bytes"] or huella(b) != c["sha256"] or not 0 < len(b) <= 2*1024*1024:
            raise ValueError(f"Insumo distinto o fuera del límite: {k}")
        salida[k] = {**c,"contenido":b}
    return salida


def construir(raiz=None):
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    cfg_rel = "config/exp_05_historico_octubre.json"
    cfg = json.loads((raiz/cfg_rel).read_text())
    base_rel = "notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb"
    if huella((raiz/base_rel).read_bytes()) != BASE_SHA256:
        raise ValueError("Cambió el soporte de referencia")
    base = nbformat.read(raiz/base_rel,as_version=4)
    tags = {t:c for c in base.cells for t in c.metadata.get("tags",[])}
    registros = {k:{**{a:b for a,b in v.items() if a != "contenido"},
                    "bytes_zlib_base64":base64.b64encode(zlib.compress(v["contenido"],9)).decode()}
                 for k,v in cargar_insumos(raiz).items()}
    celdas = []

    def texto(s):
        celdas.append(nbformat.v4.new_markdown_cell(dedent(s).strip()))

    def codigo(s,tag,titulo=None):
        c = nbformat.v4.new_code_cell(dedent(s).strip())
        c.metadata["tags"] = [tag]
        if titulo:
            c.source = f'# @title {titulo} {{ display-mode: "form" }}\n'+c.source
            c.metadata.update({"cellView":"form","jupyter":{"source_hidden":True}})
        celdas.append(c)

    def reutilizar(tag):
        c = copy.deepcopy(tags[tag])
        c.outputs,c.execution_count = [],None
        c.metadata.pop("execution",None)
        celdas.append(c)

    texto("""
    # EXP_05. ¿Qué aporta el histórico de lluvia de octubre?

    **CRISP-DM: preparar, modelar y evaluar.** El porcentaje combina lluvia actual
    e histórica. Que su denominador explique parte de su variación **no demuestra**
    que ese histórico, por sí solo, prediga mejor el rendimiento.

    Pregunta acotada: manteniendo municipio, Ridge, extracción, ventana y particiones,
    ¿qué cambia con **H, P, H+P o 100·(P−H)/H**? No cambiamos de familia ni buscamos
    otra ventana. J5_PCT se conserva como contexto, no como candidato nuevo de esta ronda.

    **Lector retrospectivo sin ajustes:** reconstruye cuatro variables desde las
    lluvias anuales **guardadas**, comprueba 200 selecciones desde scores guardados
    y recalcula métricas de 9,660 OOF guardadas. No extrae GeoTIFF, reintersecta
    geometrías, aprende pendientes, recalcula scores internos ni predice las 59 ocultas.

    Diseño y ejecución originales: **1/oct/2026 en México (2/oct UTC)**, versión r1.
    Adaptación de lectura: **8/oct**. El registro interno previo acota V3; no elimina
    las exploraciones anteriores con estas mismas etiquetas ni constituye confirmación.

    **Recorrido:** lluvia guardada → representaciones → controles → escenario → resultado.
    Basta este `.ipynb`, sin Git, Drive, ZIP u otro cuaderno. Solo dos bloques técnicos
    plegados; todas las operaciones científicas quedan visibles. Colab se verifica aparte.
    """)
    texto("""
    ## 1. Preparación y procedencia

    Colab prepara NumPy, pandas y Matplotlib con el perfil uv; en local no instala.
    Si necesita cambiar una biblioteca cargada, solicita reinicio manual.

    | Insumo incorporado | Operación visible | Límite |
    | --- | --- | --- |
    | Lluvias 2022–2025 y metadatos de 197 parcelas | Rehacer H, P, diferencia y porcentaje | No es nueva extracción espacial |
    | 138 etiquetas aparte y particiones | Comprobar unidad y escenario | No son campañas adicionales |
    | 1,200 scores y 250 filas de parámetros | Verificar 200 elecciones históricas | No repetir los ajustes |
    | OOF y controles registrados | Volver a puntuar y contrastar | No son predicciones nuevas |

    Los 21 insumos conservan bytes y SHA-256. Los controles de salida se abren
    **después** de cada cálculo; no alimentan variables, máscaras ni estimadores.
    El lector usa `round_trip` para no cambiar el último dígito al leer los CSV.
    """)
    for tag in ("soporte-colab","preparar-colab","entorno"):
        reutilizar(tag)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    codigo("INSUMOS_INCRUSTADOS = "+repr(registros)+"\n\n"+decoder,
           "insumos-tecnicos","Insumos: tamaño, SHA-256 y lectura limitada; no hay modelos ocultos")
    codigo("""
    PRE = json.loads(bytes_insumo("registro_previo","registro_historico"))
    REG = json.loads(bytes_insumo("registro_ejecucion","registro_historico"))
    MAN = json.loads(bytes_insumo("manifiesto","registro_historico"))
    assert hashlib.sha256(bytes_insumo("protocolo","protocolo_historico")).hexdigest() == PRE["sha256"]["protocolo.md"]
    assert REG["registro_previo_sha256"] == hashlib.sha256(bytes_insumo("registro_previo","registro_historico")).hexdigest()
    fuente = leer_csv("variables_fuente","variables_octubre_guardadas")
    etiquetas = leer_csv("etiquetas","etiquetas_oficiales")
    externas = leer_csv("externas","particiones")
    internas = leer_csv("internas","particiones")
    assert len(fuente) == 197 and fuente.ID_POLIGONO.is_unique
    assert "RENDIMIENTO_T_HA" not in fuente and len(etiquetas) == 138 and etiquetas.ID_POLIGONO.is_unique
    assert np.isfinite(etiquetas.RENDIMIENTO_T_HA).all()
    assert set(fuente.CONJUNTO) == {"ENTRENAMIENTO","PREDICCION"}
    assert set(fuente.loc[fuente.CONJUNTO.eq("ENTRENAMIENTO"),"ID_POLIGONO"]) == set(etiquetas.ID_POLIGONO)
    assert fuente.CONJUNTO.eq("PREDICCION").sum() == 59
    assert fuente.Municipio.notna().all() and fuente.Municipio.nunique() == 9
    assert fuente.cobertura_min.ge(.99).all() and fuente.estado.eq("ok").all()
    grupos = fuente.set_index("ID_POLIGONO").sort_index()
    print("Registro previo UTC:",PRE["registrado_utc"])
    print("Corrida UTC:",REG["inicio_utc"],"→",REG["fin_utc"])
    print("Original: 1/oct México; Python",REG["python"],"| adaptación: 8/oct, Python 3.13")
    display(fuente.groupby(["Municipio","CONJUNTO"]).size().rename("parcelas").to_frame())
    ""","insumos-visibles")
    texto(r"""
    ## 2. De cuatro octubres a cuatro representaciones

    $H=(P_{2022}+P_{2023}+P_{2024})/3$, $P=P_{2025}$,
    $A_{mm}=P-H$, $A_{pct}=100(P-H)/H$.

    **H es un histórico corto de tres años, no una normal climatológica** (usualmente
    30 años). Los cuatro octubres no son cuatro etiquetas: el rendimiento corresponde
    a un solo ciclo. La extracción conserva la ponderación por área de piezas en
    UTM 14N, cobertura ≥0.99 y H≥1 mm, verificada antes de V3. Aquí la recibimos
    como tabla: no volvemos a comprobar las intersecciones ni a leer los TIF.
    """)
    codigo("""
    def variables_octubre(fuente):
        cols = ["P_2022_mm","P_2023_mm","P_2024_mm","P_2025_mm"]
        if not {"ID_POLIGONO",*cols} <= set(fuente):
            raise ValueError("Se requieren ID y cuatro lluvias de octubre")
        ids = fuente.ID_POLIGONO
        if fuente.empty or ids.isna().any() or ids.duplicated().any() or not ids.astype(str).str.fullmatch(r"AGC_\\d{3}").all():
            raise ValueError("IDs vacíos, duplicados o mal formados")
        p = fuente.set_index("ID_POLIGONO")[cols].astype(float).sort_index()
        if not np.isfinite(p).all().all() or p.lt(0).any().any():
            raise ValueError("Lluvia ausente, no finita o negativa; no imputar")
        h = p[cols[:3]].mean(axis=1)
        if not h.ge(1).all():
            raise ValueError("H menor a 1 mm; se detiene el porcentaje")
        return pd.DataFrame({"H_mm":h,"P_actual_mm":p[cols[3]],
                             "A_mm":p[cols[3]]-h,"A_pct":100*(p[cols[3]]-h)/h})

    variables = variables_octubre(fuente)
    control_v = fuente.set_index("ID_POLIGONO").sort_index()
    np.testing.assert_allclose(variables,control_v[variables.columns],atol=1e-9,rtol=0)
    assert len(variables) == 197
    display(pd.concat([control_v.loc[["AGC_001","AGC_051","AGC_180"],["P_2022_mm","P_2023_mm","P_2024_mm","P_2025_mm"]],
                       variables.loc[["AGC_001","AGC_051","AGC_180"]]],axis=1))
    print("197 fórmulas reconstruidas desde cuatro lluvias; cero ajustes y cero nueva extracción.")
    fig,ax = plt.subplots(figsize=(8,3.4))
    for pid in ["AGC_001","AGC_051","AGC_180"]:
        ax.plot([2022,2023,2024,2025],control_v.loc[pid,["P_2022_mm","P_2023_mm","P_2024_mm","P_2025_mm"]],marker="o",label=pid)
    ax.set(xticks=[2022,2023,2024,2025],ylabel="Lluvia de octubre (mm)",title="Cuatro entradas climáticas; una campaña etiquetada")
    ax.legend(); fig.tight_layout(); plt.show()
    ""","variables-visibles")
    texto("""
    ## 3. Qué se mantiene fijo y qué cambia

    | Receta | Numéricas | Pregunta |
    | --- | --- | --- |
    | R9_PCT | A_pct | Control del porcentaje de V2 |
    | R9_P | P | Control de R9_RAW de V2 |
    | R9_H | H | ¿Historia sola agrega información al municipio? |
    | R9_HP | H y P | ¿La combinación aditiva mejora esas alternativas? |

    Todos: **nueve municipios, medias municipales no penalizadas, Ridge residual y
    misma rejilla**. MUN y MIX conservan sus recetas; J5_PCT es contexto histórico.
    Los contrastes comparan procedimientos predictivos, no efectos agronómicos causales.

    El porcentaje es una razón no lineal: no es cambiar unidades de H+P. Una columna
    creada antes del modelo puede contener una interacción que dos pendientes aditivas
    no representan. Eso no demuestra que toda familia no lineal gane.
    """)
    codigo("""
    CANDIDATOS = ["R9_PCT","R9_P","R9_H","R9_HP"]
    MODELOS = ["MUN","MIX","J5_PCT"]+CANDIDATOS
    ESPEC = {"R9_PCT":["A_pct"],"R9_P":["P_actual_mm"],"R9_H":["H_mm"],"R9_HP":["H_mm","P_actual_mm"]}
    GRID = ["baseline",.01,.1,1.,10.,100.]
    display(pd.DataFrame([{"procedimiento":m,"variables":", ".join(c),"columnas":len(c)} for m,c in ESPEC.items()]))
    # Ejemplo inventado, sin rendimiento ni entrenamiento: igual exceso, distinto porcentaje.
    ejemplo = pd.DataFrame({"H_mm":[50.,100.],"P_actual_mm":[70.,120.]})
    ejemplo["A_mm"] = ejemplo.P_actual_mm-ejemplo.H_mm
    ejemplo["A_pct"] = 100*ejemplo.A_mm/ejemplo.H_mm
    display(ejemplo)
    print("Ejemplo sintético: 20 mm de exceso no equivalen al mismo porcentaje; no prueba causalidad.")
    ""","recetas-visibles")
    texto(r"""
    El ajuste original centró X e y dentro del municipio usando **solo entrenamiento**:
    $u_j=X_j-\bar X_{g,j}$, $v=y-\bar y_g$, $s_j=\sqrt{\mathrm{media}(u_j^2)}$,
    $Z_j=u_j/s_j$. Ridge minimiza $\|v-Z\beta\|^2+\alpha\|\beta\|^2$.

    En HP el mismo alpha penaliza ambas pendientes, con escala propia por columna.
    Singleton: u=0 y participa en la escala. Columna degenerada si
    s≤1e−12·max(1,max|X_train|); se anula solo esa columna. Baseline: todas β=0.
    Municipio no visto: media global, sin corrección numérica.
    Predicción en municipio conocido: $\bar y_g+\sum_j\beta_j(X_j-\bar X_{g,j})/s_j$.
    La pendiente en unidades originales es β/s. H y P correlacionadas dificultan
    interpretar cada coeficiente como una contribución física independiente.

    El lector muestra parámetros guardados; **no calcula ni aprende esas pendientes**.
    """)
    texto("""
    ## 4. Particiones fijas y selección verificable

    CSV originales: cinco pliegues × diez repeticiones; cuatro interiores contenidos
    en cada entrenamiento exterior. Parcela es la unidad, no cada observación climática.
    No regeneramos semillas ni modificamos etiquetas de entrenamiento.
    """)
    reutilizar("particiones-visibles")
    texto("""
    Selector original: RMSE de **todos** los errores interiores concatenados, no
    promedio de cuatro RMSE ni el RMSE interior «visto». Empate ≤1e−12: baseline,
    después alpha mayor. Cambia el escenario de evaluación exterior, **no el selector**.

    Presupuesto histórico: 4,800 evaluaciones interiores (800 baseline y 4,000 Ridge),
    200 reajustes exteriores; MUN se reprodujo 50 veces como control. Las repeticiones
    posteriores comprobaron determinismo, no buscaron variantes. Aquí verificamos
    200 elecciones desde 1,200 scores: **presupuesto actual de entrenamiento cero**.
    """)
    codigo("""
    def seleccionar_alpha_guardado(scores):
        cols = ["modelo","repeticion","pliegue","alpha","RMSE_interior"]
        if not set(cols) <= set(scores) or scores.empty or scores.duplicated(cols[:4]).any():
            raise ValueError("Scores ausentes o claves repetidas")
        if not np.isfinite(scores.RMSE_interior).all() or scores.RMSE_interior.lt(0).any():
            raise ValueError("Scores no finitos o negativos")
        filas = []
        for (m,r,f),q in scores.groupby(cols[:3],sort=True):
            q = q.copy(); q["clave"] = q.alpha.map(lambda a:"baseline" if a == "baseline" else float(a))
            if len(q) != 6 or set(q.clave) != set(GRID):
                raise ValueError("Se requieren los seis alphas registrados")
            minimo = q.RMSE_interior.min()
            empate = q.loc[q.RMSE_interior.le(minimo+1e-12),"clave"].tolist()
            elegido = "baseline" if "baseline" in empate else max(empate)
            filas.append({"modelo":m,"repeticion":r,"pliegue":f,"alpha_elegido":str(elegido)})
        return pd.DataFrame(filas)

    seleccion = leer_csv("seleccion","scores_guardados")
    assert len(seleccion) == 1200 and set(seleccion.modelo) == set(CANDIDATOS)
    assert seleccion.n_ajustes.eq(4).all() and seleccion.n_ajustes_degenerados.eq(0).all()
    decisiones = seleccionar_alpha_guardado(seleccion)
    assert len(decisiones) == 200
    assert set(map(tuple,decisiones[["modelo","repeticion","pliegue"]].to_numpy())) == {(m,r,f) for m in CANDIDATOS for r in range(10) for f in range(5)}
    elegidos_guardados = seleccion.loc[seleccion.elegido,["modelo","repeticion","pliegue","alpha"]].rename(columns={"alpha":"alpha_elegido"})
    assert len(elegidos_guardados) == 200
    d = decisiones.merge(elegidos_guardados,on=["modelo","repeticion","pliegue"],validate="one_to_one",suffixes=("","_control"))
    np.testing.assert_array_equal(d.alpha_elegido,d.alpha_elegido_control)
    assert PRE["presupuesto"] == {"internas":4800,"baseline":800,"ridge":4000,"exteriores":200,"control_MUN":50}
    assert REG["presupuesto"] == {"evaluaciones_internas":4800,"baseline_interno":800,"ajustes_ridge_internos":4000,"reajustes_exteriores":200,"controles_MUN":50}
    display(decisiones.groupby(["modelo","alpha_elegido"]).size().rename("pliegues").to_frame())
    display(seleccion.loc[seleccion.modelo.eq("R9_H")&seleccion.repeticion.eq(0)&seleccion.pliegue.eq(0),
                          ["alpha","RMSE_interior","RMSE_interior_visto","elegido"]])
    print("200 decisiones desde 1,200 scores guardados; RMSE_interior_visto no selecciona.")
    ""","seleccion-visible")
    codigo("""
    parametros = leer_csv("parametros","parametros_guardados")
    assert len(parametros) == 250 and set(parametros.modelo) == set(CANDIDATOS)
    assert not parametros.duplicated(["modelo","repeticion","pliegue","variable"]).any()
    assert np.isfinite(parametros[["beta_estandarizada","escala","pendiente_unidad_original"]]).all().all()
    assert parametros.escala.gt(0).all() and not parametros.columna_degenerada.any()
    for m,cs in ESPEC.items():
        q = parametros.loc[parametros.modelo.eq(m)]
        assert len(q) == 50*len(cs) and set(q.variable) == set(cs)
        assert q.groupby(["repeticion","pliegue"]).size().eq(len(cs)).all()
    np.testing.assert_allclose(parametros.beta_estandarizada/parametros.escala,parametros.pendiente_unidad_original,atol=1e-12,rtol=0)
    p = parametros.merge(decisiones,on=["modelo","repeticion","pliegue"],validate="many_to_one")
    np.testing.assert_array_equal(p.alpha,p.alpha_elegido)
    display(parametros.groupby(["modelo","variable"]).agg(escala_mediana=("escala","median"),
             beta_mediana=("beta_estandarizada","median"),pendiente_original_mediana=("pendiente_unidad_original","median")))
    print("250 filas de parámetros corresponden a 200 modelos: HP guarda dos pendientes por modelo.")
    ""","parametros-visibles")
    texto("""
    ## 5. Controles de continuidad con V2

    Antes de interpretar H/HP, la corrida original reprodujo PCT y P frente a V2:
    100 elecciones idénticas y 2×1,380 predicciones a tolerancia 1e−8 t/ha. Las
    referencias MUN/MIX/J5 también conservan sus claves y objetivos. Aquí comprobamos
    las salidas guardadas entre rondas; no ejecutamos los ajustes que las produjeron.

    El primer intento se detuvo por leer `alpha` vacío en vez de **`alpha_estado`**
    del control V2. No llegó a las métricas H/HP. r1 corrigió solo el lector, conservó
    el fallo y registró antes de reiniciar: no fue una búsqueda motivada por resultados.
    """)
    codigo("""
    oof = leer_csv("oof","resultados_guardados")
    v2 = leer_csv("v2_oof","resultados_guardados")
    assert len(oof) == 9660 and set(oof.modelo) == set(MODELOS)
    assert not oof.duplicated(["modelo"]+claves).any()
    esperado = set(map(tuple,validaciones[claves].to_numpy()))
    y = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    for m,q in oof.groupby("modelo"):
        assert len(q) == 1380 and set(map(tuple,q[claves].to_numpy())) == esperado
        assert q.ID_POLIGONO.nunique() == 138 and np.isfinite(q.predicho).all()
        np.testing.assert_array_equal(q.observado,q.ID_POLIGONO.map(y))
        for c in ["Municipio","grupo_J5","celda_centroide"]:
            np.testing.assert_array_equal(q[c],q.ID_POLIGONO.map(grupos[c]))
        np.testing.assert_array_equal(q.zona,np.where(q.Municipio.eq("Chignahuapan"),"Chignahuapan","resto"))
    for m,anterior in [("R9_PCT","R9_PCT"),("R9_P","R9_RAW"),("MUN","MUN"),("MIX","MIX"),("J5_PCT","J5_PCT")]:
        a = oof.loc[oof.modelo.eq(m)].set_index(claves).sort_index()
        b = v2.loc[v2.modelo.eq(anterior)].set_index(claves).sort_index()
        assert a.index.equals(b.index)
        np.testing.assert_array_equal(a.observado,b.observado)
        np.testing.assert_allclose(a.predicho,b.predicho,atol=1e-8,rtol=0)
        if m in {"R9_PCT","R9_P"}:
            for _,q in b.reset_index().groupby(["repeticion","pliegue"]):
                alpha_v2 = q.alpha_estado.dropna().astype(str).str.split("|",regex=False).str[0].unique()
                assert len(alpha_v2) == 1
                r,f = q.repeticion.iloc[0],q.pliegue.iloc[0]
                nuevo = decisiones.loc[decisiones.modelo.eq(m)&decisiones.repeticion.eq(r)&decisiones.pliegue.eq(f),"alpha_elegido"].item()
                assert nuevo == alpha_v2[0]
            np.testing.assert_array_equal(a.alpha,decisiones.set_index(["modelo","repeticion","pliegue"]).loc[(m,),"alpha_elegido"].reindex(a.index.droplevel("ID_POLIGONO")))
    print("P/PCT: 100 elecciones y 2,760 predicciones guardadas conciliadas con V2; referencias intactas.")
    ""","controles-visibles")
    texto("""
    ## 6. Escenario principal fijado para esta ronda

    V3 evalúa principalmente **municipios presentes en entrenamiento (SEEN135)**,
    porque las 59 ocultas pertenecen a municipios con etiquetas. Esta decisión se
    registró antes de ajustar V3, pero después de V2; no cambia su regla retrospectivamente.

    Máscara solo con ID, Municipio y roles; idéntica para candidatos y referencias,
    no la máscara particular de J5. Conserva 1,350 OOF por procedimiento sobre 135
    parcelas repetidas. **No retira etiquetas del entrenamiento.** FULL138 y los 30
    casos de municipio no visto se conservan como escenarios secundarios.
    """)
    codigo("""
    filas_mascara = []
    for (r,f),q in externas.groupby(["repeticion","pliegue"]):
        mun_train = set(q.loc[q.rol.eq("entrenamiento"),"ID_POLIGONO"].map(grupos.Municipio))
        v = q.loc[q.rol.eq("validacion"),claves].copy()
        v["municipio_visto"] = v.ID_POLIGONO.map(grupos.Municipio).isin(mun_train)
        filas_mascara.append(v)
    mascara = pd.concat(filas_mascara,ignore_index=True)
    assert len(mascara) == 1380 and not mascara.duplicated(claves).any()
    assert mascara.municipio_visto.sum() == 1350
    check_m = oof.merge(mascara,on=claves,validate="many_to_one",suffixes=("_guardado",""))
    np.testing.assert_array_equal(check_m.municipio_visto_guardado,check_m.municipio_visto)
    seen = oof.loc[oof.municipio_visto].copy()
    no_vistos = oof.loc[~oof.municipio_visto].copy()
    assert len(seen) == 9450 and seen.ID_POLIGONO.nunique() == 135
    assert len(no_vistos) == 210 and no_vistos.ID_POLIGONO.nunique() == 3
    ESCENARIOS = {"municipio_visto":seen,"todas":oof,"municipio_no_visto":no_vistos}
    display(mascara.groupby("municipio_visto").agg(oof=("ID_POLIGONO","size"),parcelas=("ID_POLIGONO","nunique")))
    ""","escenarios-visibles")
    texto("""
    ## 7. Un mejor RMSE aislado no basta

    Puntuar cada error fuera de muestra, sin promediar las diez predicciones de una
    parcela ni los RMSE de pliegues. RMSE y MAE están en t/ha; R² no. Son 138 etiquetas,
    no 9,660 observaciones independientes. R² se deja sin definir si la varianza del
    objetivo es nula o numéricamente degenerada; las dos métricas de error sí existen.
    """)
    codigo("""
    def metricas(df):
        y,p = df.observado.to_numpy(float),df.predicho.to_numpy(float)
        if len(y) == 0 or not np.isfinite(y).all() or not np.isfinite(p).all():
            raise ValueError("Métricas vacías o no finitas")
        e = p-y; sst = np.sum((y-y.mean())**2)
        return pd.Series({"n_oof":len(df),"n_parcelas":df.ID_POLIGONO.nunique(),
                          "RMSE":np.sqrt(np.mean(e**2)),"MAE":np.mean(np.abs(e)),
                          "R2":1-np.sum(e**2)/sst if sst > 1e-12 else np.nan})

    def tabla_metricas(df):
        return pd.DataFrame({m:metricas(q) for m,q in df.groupby("modelo")}).T.reindex(MODELOS)

    metricas_esc = pd.concat([tabla_metricas(q).rename_axis("modelo").reset_index().assign(escenario=s)
                              for s,q in ESCENARIOS.items()],ignore_index=True)
    ctrl_m = leer_csv("metricas_control","control_posterior")
    orden = ["escenario","modelo"]
    a,b = metricas_esc.set_index(orden).sort_index(),ctrl_m.set_index(orden).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a,b[a.columns],atol=1e-12,rtol=0,equal_nan=True)
    por_rep = pd.DataFrame([{"escenario":s,"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                            for s,df in ESCENARIOS.items() for (m,r),q in df.groupby(["modelo","repeticion"])])
    ctrl_r = leer_csv("repeticiones_control","control_posterior").set_index(["escenario","modelo","repeticion"]).sort_index()
    a = por_rep.set_index(ctrl_r.index.names).sort_index()
    assert a.index.equals(ctrl_r.index)
    np.testing.assert_allclose(a,ctrl_r[a.columns],atol=1e-12,rtol=0,equal_nan=True)
    principales = tabla_metricas(seen)
    full = tabla_metricas(oof)
    display(principales)
    fig,axes = plt.subplots(1,2,figsize=(10.5,3.6))
    for ax,met,ref in zip(axes,["RMSE","MAE"],["MIX","MUN"]):
        ax.bar(CANDIDATOS,principales.loc[CANDIDATOS,met],color=["#287d77"]+["#75849b"]*3)
        ax.axhline(principales.loc[ref,met],color="#b64834",ls="--",label=ref)
        ax.set(ylabel=f"{met} (t/ha)",title="SEEN135: escenario principal registrado")
        ax.legend()
    fig.tight_layout(); plt.show()
    ""","metricas-visibles")
    texto("""
    Regla interna de desarrollo, **no test de significación ni puntuación oficial de
    FIRA**: RMSE<MIX y MAE≤MUN agrupados, cada condición en al menos 8/10 repeticiones.
    Los diez conteos describen estabilidad; no son diez estudios independientes.
    """)
    codigo("""
    def regla_avance(df):
        g = tabla_metricas(df)
        reps = pd.DataFrame([{"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                             for (m,r),q in df.groupby(["modelo","repeticion"])])
        R = reps.pivot(index="repeticion",columns="modelo",values="RMSE")
        A = reps.pivot(index="repeticion",columns="modelo",values="MAE")
        if set(R.index) != set(range(10)) or set(R.columns) != set(MODELOS) or R.isna().any().any() or A.isna().any().any():
            raise ValueError("Repeticiones/modelos incompletos")
        filas = []
        for m in CANDIDATOS:
            nr,na = int((R[m]<R.MIX).sum()),int((A[m]<=A.MUN).sum())
            drm,dma = float(g.loc[m,"RMSE"]-g.loc["MIX","RMSE"]),float(g.loc[m,"MAE"]-g.loc["MUN","MAE"])
            filas.append({"modelo":m,"RMSE":g.loc[m,"RMSE"],"MAE":g.loc[m,"MAE"],
                          "delta_RMSE_MIX":drm,"delta_MAE_MUN":dma,"reps_RMSE_MIX":nr,"reps_MAE_MUN":na,
                          "cumple":bool(drm<0 and dma<=0 and nr>=8 and na>=8)})
        return pd.DataFrame(filas)

    regla = pd.concat([regla_avance(df).assign(escenario=s) for s,df in [("municipio_visto",seen),("todas",oof)]],ignore_index=True)
    ctrl_regla = leer_csv("regla_control","control_posterior")
    a,b = regla.set_index(["escenario","modelo"]).sort_index(),ctrl_regla.set_index(["escenario","modelo"]).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a.select_dtypes(exclude="bool"),b[a.select_dtypes(exclude="bool").columns],atol=1e-12,rtol=0)
    np.testing.assert_array_equal(a.cumple,b.cumple)
    assert not regla.cumple.any()
    display(regla.loc[regla.escenario.eq("municipio_visto")])
    print("Ninguna receta avanza. PCT mejora RMSE agrupado a MIX, pero solo en 6/10 y con MAE peor que MUN.")
    ""","regla-visible")
    texto("""
    ## 8. Qué responde cada contraste

    HP−H y HP−P evalúan añadir una columna bajo el mismo procedimiento; al reajustar
    conjuntamente también pueden cambiar pendientes y alpha. H−PCT y HP−PCT comparan
    representaciones. No son aislamiento causal de historia ni de lluvia de 2025.
    Una diferencia agrupada pequeña debe leerse junto a MAE y repeticiones.
    """)
    codigo("""
    PARES = [("R9_HP","R9_H","adición de P a H"),("R9_HP","R9_P","adición de H a P"),
             ("R9_H","R9_PCT","histórico frente a razón"),("R9_HP","R9_PCT","aditivo frente a razón")]
    filas = []
    for s in ["municipio_visto","todas"]:
        mm = metricas_esc.loc[metricas_esc.escenario.eq(s)].set_index("modelo")
        rr = por_rep.loc[por_rep.escenario.eq(s)].set_index(["modelo","repeticion"])
        for m,b,label in PARES:
            for met in ["RMSE","MAE"]:
                delta = rr.loc[m,met]-rr.loc[b,met]
                filas.append({"escenario":s,"contraste":label,"modelo":m,"referencia":b,"metrica":met,
                              "delta_agrupado":float(mm.loc[m,met]-mm.loc[b,met]),"repeticiones_mejora":int(delta.lt(0).sum())})
    contrastes = pd.DataFrame(filas)
    ctrl_c = leer_csv("contrastes_control","control_posterior").set_index(["escenario","modelo","referencia","metrica"]).sort_index()
    c = contrastes.set_index(ctrl_c.index.names).sort_index()
    assert c.index.equals(ctrl_c.index)
    np.testing.assert_array_equal(c.contraste,ctrl_c.contraste)
    np.testing.assert_allclose(c[["delta_agrupado","repeticiones_mejora"]],ctrl_c[["delta_agrupado","repeticiones_mejora"]],atol=1e-12,rtol=0)
    display(contrastes.loc[contrastes.escenario.eq("municipio_visto")])
    print("H y HP quedan detrás de PCT en RMSE en 10/10 repeticiones; HP−H cambia RMSE y MAE en sentidos opuestos.")
    ""","contrastes-visibles")
    texto("""
    **Lectura:** H sola no sustituye al porcentaje en estas recetas; agregar P a H
    baja RMSE unos 0.0015 t/ha y empeora MAE unos 0.0011. PCT es más competitivo,
    pero tampoco avanza. Se cuestiona «la señal viene del histórico más que de la
    desviación de 2025»; no se concluye que H, octubre o el clima sean inútiles.
    """)
    texto("""
    ## 9. Territorio y regularización

    El problema dentro de Chignahuapan no se resuelve con H ni HP. Leer los errores
    por territorio evita confundir una mejora entre municipios con otra dentro de uno.
    Pendiente cero es decisión del selector, no ausencia demostrada de un efecto físico.
    R² en municipios con un único rendimiento no es informativo.

    **Precisión de presentación:** el CSV histórico de Tepeapulco contiene 14 R²
    extremos: 4.45 repetido diez veces dejó una suma de cuadrados de apenas
    7.9·10⁻³⁰ por redondeo. Aquí sst≤1e−12 se muestra como NaN (no definido),
    preservando ese CSV. RMSE, MAE, resultados globales y regla no cambian.
    """)
    codigo("""
    zonas = pd.DataFrame([{"escenario":s,"modelo":m,"zona":z,**metricas(q).to_dict()}
                          for s,df in ESCENARIOS.items() for (m,z),q in df.groupby(["modelo","zona"])])
    ctrl_z = leer_csv("zonas_control","control_posterior").set_index(["escenario","modelo","zona"]).sort_index()
    z = zonas.set_index(ctrl_z.index.names).sort_index()
    assert z.index.equals(ctrl_z.index)
    np.testing.assert_allclose(z,ctrl_z[z.columns],atol=1e-12,rtol=0,equal_nan=True)
    municipios = pd.DataFrame([{"escenario":s,"modelo":m,"Municipio":mun,**metricas(q).to_dict()}
                               for s,df in ESCENARIOS.items() for (m,mun),q in df.groupby(["modelo","Municipio"])])
    ctrl_mun = leer_csv("municipios_control","control_posterior").set_index(["escenario","modelo","Municipio"]).sort_index()
    a = municipios.set_index(ctrl_mun.index.names).sort_index()
    assert a.index.equals(ctrl_mun.index)
    np.testing.assert_allclose(a[["n_oof","n_parcelas","RMSE","MAE"]],ctrl_mun[["n_oof","n_parcelas","RMSE","MAE"]],atol=1e-12,rtol=0)
    informativo = a.R2.notna()
    np.testing.assert_allclose(a.loc[informativo,"R2"],ctrl_mun.loc[informativo,"R2"],atol=1e-12,rtol=0)
    r2_redondeo = (~informativo)&np.isfinite(ctrl_mun.R2)
    assert int(r2_redondeo.sum()) == 14
    # R² degenerado: NaN pedagógico en vez de cociente amplificado por redondeo.
    display(zonas.loc[zonas.escenario.eq("municipio_visto"),["modelo","zona","n_parcelas","RMSE","MAE"]])
    ceros = decisiones.alpha_elegido.eq("baseline").groupby(decisiones.modelo).sum().astype(int)
    assert ceros.to_dict() == {"R9_H":13,"R9_HP":15,"R9_P":32,"R9_PCT":1}
    display(ceros.rename("pendiente_cero_en_50").to_frame())
    print("14 R² municipales espurios se muestran como NaN; no se cambia ningún CSV ni error de predicción.")
    ""","territorio-visible")
    texto("""
    ## 10. Municipio visto no equivale a la entrega

    Todas las 59 ocultas tienen municipio con etiquetas, pero cambian las proporciones
    territoriales y el entrenamiento final (138 frente a 110–111 en CV). En Nanacamilpa
    solo AGC_048 está etiquetada y AGC_120 oculta: no existe OOF equivalente a
    entrenar con la única etiqueta y validar otra parcela de ese municipio.

    Los rangos siguientes describen soporte, **no precisión**. No reponderamos para
    elegir ganador ni calculamos rendimientos ocultos. Fuera de rango municipal
    univariado no demuestra por sí solo estar fuera del soporte multivariado global.
    """)
    codigo("""
    def soporte_entrega(variables,externas):
        requeridas = {"ID_POLIGONO","Municipio","CONJUNTO","H_mm","P_actual_mm","A_pct"}
        if not requeridas <= set(variables) or variables.ID_POLIGONO.duplicated().any():
            raise ValueError("Metadatos o claves de soporte inválidas")
        if variables[list(requeridas)].isna().any().any() or not np.isfinite(variables[["H_mm","P_actual_mm","A_pct"]]).all().all():
            raise ValueError("Soporte con entradas ausentes o no finitas")
        if set(variables.CONJUNTO) != {"ENTRENAMIENTO","PREDICCION"}:
            raise ValueError("Roles oficiales incompatibles")
        meta = variables.set_index("ID_POLIGONO")
        if not set(externas.ID_POLIGONO) <= set(meta.index):
            raise ValueError("Particiones con IDs fuera de la tabla")
        n_ocultas = int(variables.CONJUNTO.eq("PREDICCION").sum())
        if n_ocultas == 0:
            raise ValueError("Sin parcelas ocultas para describir soporte")
        filas = []
        for mun,q in variables.groupby("Municipio",sort=True):
            tr,te = q.loc[q.CONJUNTO.eq("ENTRENAMIENTO")],q.loc[q.CONJUNTO.eq("PREDICCION")]
            total,visto,una = 0,0,0
            for _,pa in externas.groupby(["repeticion","pliegue"]):
                nt = int(meta.loc[pa.loc[pa.rol.eq("entrenamiento"),"ID_POLIGONO"],"Municipio"].eq(mun).sum())
                nv = int(meta.loc[pa.loc[pa.rol.eq("validacion"),"ID_POLIGONO"],"Municipio"].eq(mun).sum())
                total += nv; visto += nv if nt > 0 else 0; una += nv if nt == 1 else 0
            sin = len(tr) == 1 and len(te) > 0
            row = {"Municipio":mun,"n_etiquetadas":len(tr),"n_ocultas":len(te),"fraccion_ocultas":len(te)/n_ocultas,
                   "n_oof":total,"n_oof_municipio_visto":visto,"n_oof_train_una_etiqueta":una,
                   "caso_singleton_sin_validacion":sin,"nota":"Caso entrega con una etiqueta no evaluado" if sin else ""}
            for c in ["H_mm","P_actual_mm","A_pct"]:
                row[c+"_fuera_rango_municipal"] = int(((te[c]<tr[c].min())|(te[c]>tr[c].max())).sum()) if len(tr) else len(te)
            filas.append(row)
        return pd.DataFrame(filas)

    meta_variables = grupos.drop(columns=variables.columns).join(variables).reset_index()
    soporte = soporte_entrega(meta_variables,externas)
    ctrl_s = leer_csv("soporte_control","control_posterior")
    np.testing.assert_allclose(soporte.select_dtypes(include="number"),ctrl_s[soporte.select_dtypes(include="number").columns],atol=1e-12,rtol=0)
    np.testing.assert_array_equal(soporte.caso_singleton_sin_validacion,ctrl_s.caso_singleton_sin_validacion)
    np.testing.assert_array_equal(soporte.Municipio,ctrl_s.Municipio)
    np.testing.assert_array_equal(soporte.nota,ctrl_s.nota.fillna(""))
    assert soporte.n_etiquetadas.sum() == 138 and soporte.n_ocultas.sum() == 59
    assert soporte.loc[soporte.caso_singleton_sin_validacion,"Municipio"].tolist() == ["Nanacamilpa de Mariano Arista"]
    display(soporte[["Municipio","n_etiquetadas","n_ocultas","n_oof_municipio_visto","n_oof_train_una_etiqueta","caso_singleton_sin_validacion"]])
    display(meta_variables.set_index("ID_POLIGONO").loc[["AGC_048","AGC_120"],["Municipio","CONJUNTO","celda_centroide","H_mm","P_actual_mm","A_pct"]])
    display(soporte.loc[soporte.n_ocultas.gt(0),["Municipio","H_mm_fuera_rango_municipal","P_actual_mm_fuera_rango_municipal","A_pct_fuera_rango_municipal"]])
    ""","soporte-visible")
    texto("""
    ## 11. ¿Dónde se distribuyen las ganancias y pérdidas?

    Ganancia SSE = error² MIX − error² candidato, positiva si el candidato mejora.
    Se suman sobre las mismas claves parcela×repetición. Beneficio **neto** incluye
    pérdidas; top5 parcelas y top2 celdas usan beneficio **bruto positivo**. No se
    eliminan casos ni se repite la selección. Celda de centroide es agrupación
    diagnóstica, no totalidad de píxeles aportantes ni tamaño muestral efectivo.
    """)
    codigo("""
    filas = []
    for s,df in ESCENARIOS.items():
        mix = df.loc[df.modelo.eq("MIX")].set_index(claves).sort_index()
        for m in CANDIDATOS:
            p = df.loc[df.modelo.eq(m)].set_index(claves).sort_index()
            assert p.index.equals(mix.index)
            delta = p[["Municipio","celda_centroide"]].copy()
            delta["ganancia_SSE_vs_MIX"] = (mix.predicho-mix.observado)**2-(p.predicho-p.observado)**2
            q = delta.reset_index().groupby("ID_POLIGONO").agg(ganancia_SSE_vs_MIX=("ganancia_SSE_vs_MIX","sum"),
                                                               Municipio=("Municipio","first"),celda_centroide=("celda_centroide","first"))
            filas.append(q.reset_index().assign(escenario=s,modelo=m))
    deltas = pd.concat(filas,ignore_index=True)
    ctrl_d = leer_csv("deltas_control","control_posterior").set_index(["escenario","modelo","ID_POLIGONO"]).sort_index()
    d = deltas.set_index(ctrl_d.index.names).sort_index()
    assert d.index.equals(ctrl_d.index)
    np.testing.assert_allclose(d.ganancia_SSE_vs_MIX,ctrl_d.ganancia_SSE_vs_MIX,atol=1e-12,rtol=0)
    for c in ["Municipio","celda_centroide"]:
        np.testing.assert_array_equal(d[c],ctrl_d[c])
    filas = []
    for (s,m),q in deltas.groupby(["escenario","modelo"]):
        gain = q.ganancia_SSE_vs_MIX
        bruta = float(gain.clip(lower=0).sum())
        cells = q.groupby("celda_centroide").ganancia_SSE_vs_MIX.sum()
        bruta_celdas = float(cells.clip(lower=0).sum())
        filas.append({"escenario":s,"modelo":m,"ganancia_SSE_neta":float(gain.sum()),"ganancia_SSE_bruta_positiva":bruta,
                      "fraccion_mejora_bruta_top5_parcelas":float(gain.nlargest(5).clip(lower=0).sum())/bruta if bruta else np.nan,
                      "fraccion_mejora_bruta_top2_celdas_centroide":float(cells.nlargest(2).clip(lower=0).sum())/bruta_celdas if bruta_celdas else np.nan,
                      "n_parcelas_mejoran":int(gain.gt(0).sum()),"n_parcelas_empeoran":int(gain.lt(0).sum())})
    concentracion = pd.DataFrame(filas)
    ctrl_c = leer_csv("concentracion_control","control_posterior").set_index(["escenario","modelo"]).sort_index()
    c = concentracion.set_index(ctrl_c.index.names).sort_index()
    assert c.index.equals(ctrl_c.index)
    np.testing.assert_allclose(c,ctrl_c[c.columns],atol=1e-12,rtol=0,equal_nan=True)
    display(concentracion.loc[concentracion.escenario.eq("municipio_visto")])
    print("Diagnóstico registrado: no se quitaron parcelas para ganar ni se estimó n efectivo por contar celdas.")
    ""","concentracion-visible")
    texto("""
    ## 12. Decisión, alcance y continuidad

    - **Cerrar sin adopción:** H y HP no justifican aumentar el modelo bajo estas
      representaciones, esta ventana, Ridge y esta rejilla. PCT tampoco cumple la regla principal.
    - **Corregir la interpretación fuerte:** la dependencia del porcentaje respecto
      de H no se convirtió en ventaja predictiva de H sola. Correlación entre variables
      no es aportación al rendimiento ni causalidad.
    - Mantener MUN/MIX como referencias y J5_PCT como candidato histórico con reservas,
      no modelo final. Este experimento no identifica el motivo único de la ventaja de J5.
    - Una campaña y etiquetas ya exploradas limitan generalización. SEEN135 no evalúa
      todo el soporte de las 59; no se inventa incertidumbre para AGC_120.

    Reproducir fórmulas, métricas y decisiones guardadas verifica esta lectura, no
    la paridad de reentrenamiento entre Python 3.12.14 histórico y Python 3.13 actual.
    Las 34 pruebas y 9 autopruebas originales no se presentan como corridas aquí.
    La siguiente ronda plantea otra hipótesis con registro propio; no se ejecuta aquí.
    """)
    codigo("""
    resumen = {"id":"EXP_05","modo":"lector_retrospectivo_sin_ajustes","parcelas":197,"etiquetas":138,
               "variables_recalculadas":True,"lluvias_reextraidas":False,"intersecciones_recalculadas":False,
               "procedimientos":7,"candidatos":4,"oof_por_procedimiento":1380,"oof_total":9660,
               "particiones_externas":50,"particiones_internas":200,"decisiones_verificadas":200,
               "scores_guardados_verificados":1200,"parametros_guardados":250,
               "ajustes_actuales":0,"predicciones_finales_generadas":0,"predicciones_recalculadas":False,
               "scores_interiores_recalculados":False,"metricas_recalculadas":True,
               "r2_municipales_presentacion_nan":int(r2_redondeo.sum()),
               "poblacion":"SEEN135","oof_seen_por_procedimiento":1350,"poblacion_secundaria":"FULL138",
               "regla_seen_cumplen":regla.loc[regla.escenario.eq("municipio_visto")&regla.cumple,"modelo"].tolist(),
               "regla_full_cumplen":regla.loc[regla.escenario.eq("todas")&regla.cumple,"modelo"].tolist(),
               "variantes_adoptadas":[],"candidato_historico_con_reservas":["J5_PCT"],
               "fecha_original_mexico":"2026-10-01","fecha_original_utc":"2026-10-02","fecha_adaptacion":"2026-10-08",
               "metricas_seen":principales[["RMSE","MAE","R2"]].to_dict(orient="index"),
               "metricas_full":full[["RMSE","MAE","R2"]].to_dict(orient="index"),
               "fecha_ejecucion_utc":datetime.now(timezone.utc).isoformat()}
    print("RESUMEN_EXP_05_JSON="+json.dumps(resumen,sort_keys=True,ensure_ascii=False,allow_nan=False))
    ""","cierre")
    texto("""
    ## Referencias y conceptos para profundizar (APA 7)

    Equipo AgroCebada. (2026, 1 de octubre). *V3: protocolo de histórico y lluvia actual
    de octubre, versión r1* [Registro interno exploratorio]. Su diseño y resultados
    están incorporados; no se requiere otro documento. El fallo del lector alpha
    se conserva como antecedente, no se atribuye a un cambio de hipótesis.

    Funk, C., Peterson, P., Landsfeld, M., Pedreros, D., Verdin, J., Shukla, S., Husak,
    G., Rowland, J., Harrison, L., Hoell, A., & Michaelsen, J. (2015). The climate hazards
    infrared precipitation with stations—a new environmental record for monitoring
    extremes. *Scientific Data, 2*, 150066. https://doi.org/10.1038/sdata.2015.66

    National Centers for Environmental Information. (s. f.). *WMO climate normals*.
    https://www.ncei.noaa.gov/products/wmo-climate-normals

    scikit-learn developers. (s. f.). *Ridge*.
    https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html

    **Glosario:** H = media de tres octubres históricos; P = octubre de 2025;
    aditivo = sumar contribuciones de columnas; razón = dividir P por H;
    baseline = pendiente cero; OOF = predicción fuera del entrenamiento;
    SEEN135 = municipio presente en entrenamiento; soporte = covariables y contexto
    cubiertos, no rendimiento conocido. Aquí SEEN135 es principal registrado para V3,
    no diagnóstico posterior de esta ronda ni una nueva muestra independiente.
    """)
    for i,c in enumerate(celdas):
        c.id = f"exp05-{i:03d}"
    metadata = copy.deepcopy(base.metadata)
    metadata["agrocebada"] = {
        "id":"EXP_05","modo":"lector_retrospectivo_sin_ajustes","crisp_dm":[3,4,5],
        "fecha_original_mexico":"2026-10-01","fecha_original_utc":"2026-10-02","fecha_adaptacion":"2026-10-08",
        "ajustes_actuales":0,"colab_real_probado":False,
        "dependencias_requeridas":base.metadata.agrocebada.dependencias_requeridas,
        "perfil_sha256":base.metadata.agrocebada.perfil_sha256,"soporte_sha256":base.metadata.agrocebada.soporte_sha256,
        "fuentes_sha256":{cfg_rel:huella((raiz/cfg_rel).read_bytes()),base_rel:BASE_SHA256},
        "insumos":cfg["insumos"],"poblacion_principal":"SEEN135","poblacion_secundaria":"FULL138",
        "r2_municipales_presentacion_nan":14,
    }
    return nbformat.v4.new_notebook(cells=celdas,metadata=metadata)


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida",type=Path,default=raiz/"notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb")
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("Salida existente; elige una ruta nueva")
    nb = construir(raiz)
    nbformat.validate(nb)
    args.salida.parent.mkdir(parents=True,exist_ok=True)
    nbformat.write(nb,args.salida)
    print(args.salida)


if __name__ == "__main__":
    main()
