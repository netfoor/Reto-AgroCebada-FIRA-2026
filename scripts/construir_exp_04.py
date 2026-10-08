"""EXP04: lluvia, agrupación y diagnóstico; lector retrospectivo sin ajustes."""
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

BASE_SHA256 = "ca84ad2999bda26496848898a4e77385423e8a544699a1c2883ec28267457fc0"


def huella(contenido):
    return hashlib.sha256(contenido).hexdigest()


def cargar_insumos(raiz):
    cfg = json.loads((Path(raiz)/"config/exp_04_lluvia_octubre.json").read_text())
    salida = {}
    for k,c in cfg["insumos"].items():
        bruto = (Path(raiz)/c["ruta_local"]).read_bytes()
        if len(bruto) != c["bytes"] or huella(bruto) != c["sha256"] or not 0 < len(bruto) <= 2*1024*1024:
            raise ValueError(f"Insumo distinto o fuera del límite: {k}")
        salida[k] = {**c,"contenido":bruto}
    return salida


def construir(raiz=None):
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    cfg_rel = "config/exp_04_lluvia_octubre.json"
    cfg = json.loads((raiz/cfg_rel).read_text())
    base_rel = "notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb"
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
        c.outputs, c.execution_count = [], None
        c.metadata.pop("execution",None)
        celdas.append(c)

    texto("""
    # EXP_04. ¿La lluvia de octubre aporta sobre la referencia territorial?

    **CRISP-DM: preparar, modelar y evaluar.** Una variable prometedora no basta:
    importa cómo se obtiene, qué procedimiento la utiliza y dónde mejora sus errores.
    La hipótesis procede del análisis de Jared, no de una prueba independiente nueva.

    Comparamos cinco recetas con una numérica y región: anomalía porcentual,
    diferencia en milímetros o lluvia actual; cinco grupos o nueve municipios;
    OLS o Ridge. Son contrastes acotados, no una búsqueda exhaustiva.

    **Lector retrospectivo, sin reentrenamiento.** Reconstruimos 788 lluvias y sus
    variables desde valores de píxel y áreas **guardadas**. Puntúamos OOF guardadas;
    comprobamos decisiones desde scores guardados. No volvemos a intersectar polígonos,
    estimar pendientes, calcular scores interiores ni generar las 59 predicciones finales.

    Original: **1 de octubre de 2026**. Adaptación: **8 de octubre**. El registro local
    fija esta corrida exploratoria; no borra la selección previa entre 148 candidatas
    de Jared, ni las rondas anteriores con las mismas etiquetas. No es confirmatorio.

    **Recorrido:** área → lluvia → anomalía → recetas → errores → reservas.
    Basta este `.ipynb`: sin ZIP, Drive, Git u otro cuaderno. Dos bloques técnicos
    plegados; las operaciones científicas permanecen visibles. Colab real se verifica
    por separado de las ejecuciones locales.
    """)
    texto("""
    ## 1. Preparación y fuentes identificadas

    Colab prepara NumPy, pandas y Matplotlib con el perfil uv; en local no instala.
    Si una biblioteca cargada necesita cambiar, solicita reinicio manual.
    «Mostrar código» abre soporte e insumos: no hay modelos escondidos.

    | Insumo | Qué permite | Qué no demuestra |
    | --- | --- | --- |
    | 230 áreas parcela×píxel guardadas | Rehacer la media ponderada | Nueva intersección/proyección |
    | 116 valores de cuatro GeoTIFF | Leer 29 celdas × cuatro octubres | Lluvia real sin error de medición |
    | Catálogo y grupos, etiquetas aparte | Verificar unidad y población | Generalización territorial |
    | OOF y scores guardados | Recalcular métricas y comprobar selección | Reentrenamiento |

    El recorte de píxeles se deriva **el 8/oct** de los cuatro TIF oficiales, que están
    dentro del ZIP climático anidado. Se comprueba identidad con el paquete registrado;
    hashes originales y del recorte son distintos. No fingimos que este recorte existía
    antes de V2. Los CSV conservan bytes y se leen con precisión `round_trip`.
    """)
    for tag in ("soporte-colab","preparar-colab","entorno"):
        reutilizar(tag)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    decoder = decoder.replace('encoding="utf-8-sig")','encoding="utf-8-sig", float_precision="round_trip")')
    codigo("INSUMOS_INCRUSTADOS = "+repr(registros)+"\n\n"+decoder,
           "insumos-tecnicos","Insumos: tamaño, SHA-256, descompresión limitada y roles")
    codigo("""
    PRE = json.loads(bytes_insumo("registro_previo","registro_historico"))
    REG = json.loads(bytes_insumo("registro_ejecucion","registro_historico"))
    RECORTE = __RECORTE__
    pesos = leer_csv("pesos","areas_guardadas")
    pixeles = leer_csv("pixeles","valores_pixel_derivados")
    grupos = leer_csv("grupos","metadatos").set_index("ID_POLIGONO").sort_index()
    catalogo = leer_csv("catalogo","catalogo_oficial")
    vacias = [c for c in catalogo if c.startswith("Unnamed")]
    assert not catalogo[vacias].notna().any().any()
    catalogo = catalogo.drop(columns=vacias)
    assert len(catalogo) == len(grupos) == 197 and catalogo.ID_POLIGONO.is_unique and grupos.index.is_unique
    assert set(catalogo.ID_POLIGONO) == set(grupos.index)
    assert catalogo.RENDIMIENTO_T_HA.notna().equals(catalogo.CONJUNTO.eq("ENTRENAMIENTO"))
    etiquetas = catalogo.loc[catalogo.RENDIMIENTO_T_HA.notna(),["ID_POLIGONO","RENDIMIENTO_T_HA"]].copy()
    assert len(etiquetas) == 138 and np.isfinite(etiquetas.RENDIMIENTO_T_HA).all()
    externas = leer_csv("externas","particiones")
    internas = leer_csv("internas","particiones")
    display(pd.DataFrame([{"anio":a,**f} for a,f in RECORTE["fuentes_tif"].items()]))
    print("Registro original UTC:", PRE["registrado_utc"])
    print("Corrida original UTC:", REG["inicio_utc"], "| Python histórico:", REG["versiones"]["python"])
    print("Recorte actual:", RECORTE["fecha_recorte"], "|",len(pixeles),"valores;",len(pesos),"piezas")
    """.replace("__RECORTE__",repr(cfg["recorte_pixeles"])),"insumos-visibles")
    texto(r"""
    ## 2. Del espacio a una suma verificable

    La receta original intersecta en el CRS del ráster (EPSG:4326), transforma cada
    pieza a UTM 14N (EPSG:32614) y usa su área en m². El centro del píxel no es una
    esquina; el centroide de parcela no sustituye la intersección.

    $P_{i,a}=\sum_{j\,válido}a_{ij}P_{j,a}/\sum_{j\,válido}a_{ij}$.
    Cobertura = área válida / área **total** de la parcela; mínimo 0.99.
    NoData y no finitos no reciben peso; sin dato suficiente se detiene, no se imputa.

    **Alcance del lector:** reconstruimos esta aritmética desde áreas previamente
    verificadas; no recalculamos geometrías, intersecciones o reproyecciones. El área
    total proviene del control histórico, **no su lluvia ponderada**. Comparar con
    la lluvia guardada se hace después de sumar. Los controles geoespaciales históricos
    (95 y 32 pruebas) no se presentan como una nueva ejecución de esa batería.
    """)
    codigo("""
    # Abrimos solo los metadatos de soporte: no tomamos P_mm como entrada.
    soporte = leer_csv("lluvia_control","control_posterior")
    cols_soporte = ["ID_POLIGONO","area_parcela_m2","fila_centroide","col_centroide"]
    areas = soporte[cols_soporte].drop_duplicates().sort_values("ID_POLIGONO")
    assert len(areas) == 197 and areas.ID_POLIGONO.is_unique
    assert len(pesos) == 230 and len(pixeles) == 116
    celdas_parcela = pesos.groupby("ID_POLIGONO").size()
    display(celdas_parcela.value_counts().sort_index().rename("parcelas").to_frame())
    ejemplo_piezas = pesos.loc[pesos.ID_POLIGONO.isin(["AGC_001","AGC_051","AGC_180"]),
                                ["ID_POLIGONO","fila","col","area_m2_utm14n","peso_normalizado"]]
    display(ejemplo_piezas)

    def lluvia_ponderada(pesos, pixeles, areas):
        wp = ["ID_POLIGONO","fila","col","area_m2_utm14n"]
        pp = ["anio","fila","col","P_pixel_mm"]
        if not set(wp) <= set(pesos) or not set(pp) <= set(pixeles):
            raise ValueError("Columnas de piezas/píxeles incompletas")
        if not {"ID_POLIGONO","area_parcela_m2"} <= set(areas):
            raise ValueError("Falta área total de parcela")
        w, p = pesos[wp].copy(), pixeles[pp].copy()
        if w.empty or w[wp[:3]].isna().any().any() or w.duplicated(wp[:3]).any():
            raise ValueError("Piezas vacías, ambiguas o duplicadas")
        if p[pp[:3]].isna().any().any() or p.duplicated(pp[:3]).any():
            raise ValueError("Píxeles ambiguos o duplicados")
        for df, campos in [(w,["fila","col"]),(p,["anio","fila","col"])]:
            for c in campos:
                v = pd.to_numeric(df[c],errors="raise").to_numpy(float)
                if not np.isfinite(v).all() or not np.equal(v,np.floor(v)).all() or (v < 0).any():
                    raise ValueError("Índice de malla/año incompatible")
                df[c] = v.astype(int)
        if set(p.anio) != {2022,2023,2024,2025}:
            raise ValueError("Se requieren cuatro octubres; no sustituir años")
        area = areas.set_index("ID_POLIGONO").area_parcela_m2
        if not area.index.is_unique or set(area.index) != set(w.ID_POLIGONO):
            raise ValueError("Áreas/IDs incompatibles")
        if not np.isfinite(area.to_numpy(float)).all() or not area.gt(0).all():
            raise ValueError("Área total inválida")
        w["area_m2_utm14n"] = pd.to_numeric(w.area_m2_utm14n,errors="raise")
        if not np.isfinite(w.area_m2_utm14n).all() or not w.area_m2_utm14n.gt(0).all():
            raise ValueError("Pieza sin área positiva; bordes de área cero no reciben peso")
        celdas = set(map(tuple,w[["fila","col"]].to_numpy()))
        esperado = {(a,f,c) for a in (2022,2023,2024,2025) for f,c in celdas}
        if set(map(tuple,p[pp[:3]].to_numpy())) != esperado:
            raise ValueError("Recorte de píxeles incompleto o con celdas ajenas")
        p["P_pixel_mm"] = pd.to_numeric(p.P_pixel_mm,errors="raise")
        lookup = p.set_index(pp[:3]).P_pixel_mm.to_dict()
        filas = []
        for pid,q in w.groupby("ID_POLIGONO",sort=True):
            for a in (2022,2023,2024,2025):
                validos = [(lookup[(a,int(r.fila),int(r.col))],float(r.area_m2_utm14n)) for r in q.itertuples()]
                validos = [(v,s) for v,s in validos if np.isfinite(v) and v != -9999]
                area_valida = sum(s for _,s in validos)
                cobertura = area_valida/float(area.loc[pid])
                estado = "ok" if cobertura >= .99 else ("sin_dato" if area_valida == 0 else "cobertura_insuficiente")
                media = sum(v*s for v,s in validos)/area_valida if area_valida > 0 else np.nan
                filas.append({"ID_POLIGONO":pid,"anio":a,"P_mm":media if estado == "ok" else np.nan,
                              "cobertura":cobertura,"estado":estado,"n_celdas":len(q),"n_celdas_validas":len(validos)})
        return pd.DataFrame(filas)

    lluvia = lluvia_ponderada(pesos,pixeles,areas)
    assert len(lluvia) == 788 and lluvia.estado.eq("ok").all()
    assert lluvia.cobertura.ge(.99).all()
    control_lluvia = leer_csv("lluvia_control","control_posterior").set_index(["ID_POLIGONO","anio"]).sort_index()
    recalculada = lluvia.set_index(["ID_POLIGONO","anio"]).sort_index()
    assert recalculada.index.equals(control_lluvia.index)
    for c in ["P_mm","cobertura","n_celdas","n_celdas_validas"]:
        np.testing.assert_allclose(recalculada[c],control_lluvia[c],atol=1e-9,rtol=0)
    assert recalculada.estado.equals(control_lluvia.estado)
    display(lluvia.loc[lluvia.ID_POLIGONO.isin(["AGC_001","AGC_051","AGC_180"])])
    print("788 sumas verificadas. Cobertura mínima/máxima:",lluvia.cobertura.min(),lluvia.cobertura.max())
    ""","lluvia-visible")
    texto("""
    La cobertura puede superar 1 por unas millonésimas al proyectar por separado
    piezas y vértices originales: se muestra, no se recorta ni se impone ≤1 exacto.
    En estas parcelas no hay NoData; la regla de detención también necesita controles
    sintéticos. Las 31 parcelas multicelda son sensibles a la definición de peso.

    Ponderar área de pieza y ponderar **fracción de píxel** son convenciones diferentes.
    La segunda reproduce numéricamente a Jared al usar fracción geodésica; no se ejecutó
    R/terra ni se validó toda su implementación. Diferencia histórica máxima: 0.001791 mm.
    Área frente a centroide cambia hasta 9.6533 puntos de anomalía en AGC_051. No escogemos
    la receta espacial por el resultado del modelo.
    """)
    codigo("""
    # Un cálculo manual de la parcela multicelda, sin rendimiento.
    piezas_051 = pesos.loc[pesos.ID_POLIGONO.eq("AGC_051"),["fila","col","area_m2_utm14n"]]
    caso = piezas_051.merge(pixeles.loc[pixeles.anio.eq(2025)],on=["fila","col"],validate="one_to_one")
    caso["peso"] = caso.area_m2_utm14n/caso.area_m2_utm14n.sum()
    caso["contribucion_mm"] = caso.peso*caso.P_pixel_mm
    display(caso[["fila","col","P_pixel_mm","area_m2_utm14n","peso","contribucion_mm"]])
    np.testing.assert_allclose(caso.contribucion_mm.sum(),recalculada.loc[("AGC_051",2025),"P_mm"],atol=1e-12,rtol=0)
    ""","ejemplo-area")
    texto(r"""
    ## 3. De cuatro lluvias a una variable

    $H=(P_{2022}+P_{2023}+P_{2024})/3$;
    $A_{mm}=P_{2025}-H$; $A_{pct}=100A_{mm}/H$.
    P_actual es P2025. Todos los años deben existir; H debe ser ≥1 mm.
    **H es una referencia de tres años**, no una normal climatológica de largo plazo.

    Un mismo exceso en milímetros produce porcentajes distintos si cambia H. Por eso
    R9_PCT frente a R9_MM no demuestra que una representación sea superior en general,
    ni identifica el aporte incremental de H como predictor independiente.
    """)
    codigo("""
    def variables_octubre(lluvia):
        cols = {"ID_POLIGONO","anio","P_mm","estado"}
        if not cols <= set(lluvia) or lluvia.empty or lluvia.duplicated(["ID_POLIGONO","anio"]).any():
            raise ValueError("Lluvia vacía, incompleta o duplicada")
        if not lluvia.estado.eq("ok").all() or set(lluvia.anio) != {2022,2023,2024,2025}:
            raise ValueError("Año ausente o cobertura detenida")
        P = lluvia.pivot(index="ID_POLIGONO",columns="anio",values="P_mm").reindex(columns=[2022,2023,2024,2025])
        if not np.isfinite(P.to_numpy(float)).all():
            raise ValueError("Falta lluvia de uno o más años; no se imputa")
        H = (P[2022]+P[2023]+P[2024])/3
        if H.lt(1).any():
            raise ValueError("Referencia histórica menor de 1 mm")
        V = P.rename(columns={a:f"P_{a}_mm" for a in P.columns}).copy()
        V["H_mm"], V["A_mm"] = H, P[2025]-H
        V["A_pct"], V["P_actual_mm"] = 100*V.A_mm/H, P[2025]
        return V

    variables = variables_octubre(lluvia)
    control_var = leer_csv("variables_control","control_posterior").set_index("ID_POLIGONO").sort_index()
    assert variables.index.equals(control_var.index) and len(variables) == 197
    np.testing.assert_allclose(variables,control_var[variables.columns],atol=1e-9,rtol=0)
    display(variables.loc[["AGC_001","AGC_051","AGC_180"]])
    display(pd.DataFrame({"H_mm":[50.,100.],"A_mm":[20.,20.],"A_pct":[40.,20.]}))
    print("Ejemplo inventado de denominador, separado de las parcelas reales.")
    fig,ax = plt.subplots(figsize=(7.8,3.2))
    for pid in ["AGC_001","AGC_051","AGC_180"]:
        ax.plot([2022,2023,2024,2025],variables.loc[pid,[f"P_{a}_mm" for a in (2022,2023,2024,2025)]],"o-",label=pid)
    ax.set(xlabel="Año (solo octubre)",ylabel="Lluvia ponderada, mm",title="Cuatro octubres: referencia reciente, no cuatro rendimientos")
    ax.set_xticks([2022,2023,2024,2025]); ax.legend(); fig.tight_layout(); plt.show()
    ""","variables-visibles")
    texto("""
    ## 4. Cinco recetas: qué cambia y qué se conserva

    | Código | Región | Numérica | Ajuste histórico |
    | --- | --- | --- | --- |
    | J5_PCT | Cinco grupos de Jared | A_pct | OLS |
    | J9_PCT | Nueve municipios | A_pct | OLS |
    | R9_PCT | Municipio | A_pct | Ridge |
    | R9_MM | Municipio | A_mm | Ridge |
    | R9_RAW | Municipio | P_actual_mm | Ridge |

    GLOBAL, MUN y MIX conservan sus recetas; G5 es la media del grupo; R_B/E2 es
    control histórico, no un sexto candidato. **J5−J9 cambia una agrupación completa**:
    medias, residuos, escala y respaldo cuando el grupo no está en entrenamiento.
    No aísla un mecanismo causal. Ningún contraste suma H manteniendo todo lo demás fijo.
    """)
    codigo("""
    J5 = {"Chignahuapan":"Chignahuapan","Singuilucan":"Singuilucan","Almoloya":"Almoloya",
          "Calpulalpan":"Tlaxcala","Nanacamilpa de Mariano Arista":"Tlaxcala",
          "Cuautepec de Hinojosa":"Otros_Hidalgo","Emiliano Zapata":"Otros_Hidalgo",
          "Apan":"Otros_Hidalgo","Tepeapulco":"Otros_Hidalgo"}
    np.testing.assert_array_equal(grupos.Municipio.map(J5),grupos.grupo_J5)
    assert grupos.Municipio.nunique() == 9 and grupos.grupo_J5.nunique() == 5
    display(grupos.groupby(["grupo_J5","Municipio","CONJUNTO"]).size().rename("parcelas").to_frame())
    CANDIDATOS = ["J5_PCT","J9_PCT","R9_PCT","R9_MM","R9_RAW"]
    MODELOS = ["GLOBAL","MUN","MIX","G5","R_B"]+CANDIDATOS
    ESPEC = {"J5_PCT":("grupo_J5","A_pct"),"J9_PCT":("Municipio","A_pct"),
             "R9_PCT":("Municipio","A_pct"),"R9_MM":("Municipio","A_mm"),"R9_RAW":("Municipio","P_actual_mm")}
    ""","recetas-visibles")
    texto(r"""
    En cada entrenamiento original se calcularon medias del grupo, luego
    $u=X-\bar X_g$, $v=y-\bar y_g$, escala $s=\sqrt{\mathrm{media}(u^2)}$,
    $z=u/s$. OLS: $\beta=\sum zv/\sum z^2$; Ridge: $\beta=\sum zv/(\sum z^2+\alpha)$.
    Predicción: $\bar y_g+\beta(X-\bar X_g)/s$.

    Todas las medias y escalas pertenecen al entrenamiento del pliegue; los singleton
    aportan u=0 y se incluyen en la escala. Si s≤1e−12·max(1,max|X_train|), pendiente
    cero. Grupo no visto → media global sin corrección. «Baseline» también pone β=0.
    La pendiente en unidades originales es **β/s**, no β.

    Mostramos parámetros históricos, sin volver a estimarlos. A_pct se mide en puntos
    porcentuales; A_mm, en milímetros. Comparar β directamente confunde escalas.
    """)
    codigo("""
    parametros = leer_csv("parametros","parametros_guardados")
    assert len(parametros) == 250 and set(parametros.modelo) == set(CANDIDATOS)
    assert not parametros.duplicated(["modelo","repeticion","pliegue"]).any()
    assert np.isfinite(parametros[["beta","escala"]]).all().all() and parametros.escala.gt(0).all()
    assert not parametros.degenerada.any()
    for m,(region,num) in ESPEC.items():
        q = parametros.loc[parametros.modelo.eq(m)]
        assert len(q) == 50 and q.region.eq(region).all() and q.numerica.eq(num).all()
    parametros["pendiente_unidad_original"] = parametros.beta/parametros.escala
    display(parametros.groupby("modelo").agg(beta_mediana=("beta","median"),escala_mediana=("escala","median"),
              pendiente_unidad_original_mediana=("pendiente_unidad_original","median"),
              beta_cero=("beta",lambda s:int(s.eq(0).sum())),no_vistos=("n_validacion_grupo_no_visto","sum")))
    display(parametros.loc[parametros.repeticion.eq(0)&parametros.pliegue.eq(0),
                          ["modelo","beta","escala","pendiente_unidad_original","alpha_elegido"]])
    ""","parametros-visibles")
    texto("""
    ## 5. Misma validación, selección interior y presupuesto explícito

    Parcela es la unidad. Se conservan los CSV de 5 pliegues × 10 repeticiones,
    con cuatro pliegues interiores contenidos en cada entrenamiento exterior.
    Más OOF no son más etiquetas. No regeneramos semillas ni escogemos particiones favorables.
    """)
    reutilizar("particiones-visibles")
    texto("""
    Ridge seleccionó entre `baseline, 0.01, 0.1, 1, 10, 100` por **RMSE de todos los
    errores interiores concatenados**, no promedio de cuatro RMSE. Empate a 1e−12:
    baseline, luego alpha mayor. OLS no tiene selección de alpha.

    Aquí comprobamos 150 decisiones desde 900 scores guardados; además 50 decisiones
    R_B desde 250 scores. No recalculamos los errores interiores que originaron esos
    scores. Candidatos históricos: 3,600 evaluaciones interiores (600 baseline sin
    ajuste, 3,000 Ridge) y 250 reajustes exteriores. Controles originales aparte.
    **Presupuesto actual de entrenamiento: cero.**
    """)
    codigo("""
    GRID = ["baseline",.01,.1,1.,10.,100.]

    def seleccionar_alpha_guardado(scores):
        v = np.asarray(scores,dtype=float)
        if v.shape != (6,) or not np.isfinite(v).all() or (v < 0).any():
            raise ValueError("Seis RMSE guardados finitos y no negativos requeridos")
        empatados = [GRID[i] for i in range(6) if v[i] <= v.min()+1e-12]
        return "baseline" if "baseline" in empatados else max(empatados)

    seleccion = leer_csv("seleccion","scores_guardados")
    assert len(seleccion) == 900 and set(seleccion.modelo) == {"R9_PCT","R9_MM","R9_RAW"}
    assert not seleccion.duplicated(["modelo","repeticion","pliegue","alpha"]).any()
    decisiones = []
    for (m,r,f),q in seleccion.groupby(["modelo","repeticion","pliegue"]):
        q = q.copy(); q["clave"] = q.alpha.map(lambda a:"baseline" if a == "baseline" else float(a))
        assert set(q.clave) == set(GRID) and len(q) == 6
        valores = q.set_index("clave").loc[GRID,"rmse_interior"].to_numpy()
        elegido = seleccionar_alpha_guardado(valores)
        filas = q.loc[q.elegido]
        assert len(filas) == 1 and filas.clave.iloc[0] == elegido
        param = parametros.loc[parametros.modelo.eq(m)&parametros.repeticion.eq(r)&parametros.pliegue.eq(f)]
        assert len(param) == 1
        almacenado = param.alpha_elegido.iloc[0]
        assert elegido == ("baseline" if almacenado == "baseline" else float(almacenado))
        decisiones.append({"modelo":m,"repeticion":r,"pliegue":f,"elegido":str(elegido)})
    decisiones = pd.DataFrame(decisiones)
    assert len(decisiones) == 150
    rb = leer_csv("rb_seleccion","scores_guardados")
    v1sel = leer_csv("v1_seleccion","scores_guardados").query("modelo == 'R_B'")
    ctrl_rb = rb.merge(v1sel,on=["repeticion","pliegue"],validate="one_to_one")
    assert len(ctrl_rb) == 50
    for _,q in ctrl_rb.iterrows():
        vals = json.loads(q.scores_internos_x); antes = json.loads(q.scores_internos_y)
        assert len(vals) == len(antes) == 5
        np.testing.assert_allclose(vals,antes,atol=1e-8,rtol=0)
        ix = next(i for i,s in enumerate(vals) if s <= min(vals)+1e-12)
        assert [100.,10.,1.,.1,.01][ix] == q.alpha == json.loads(q.parametros)["alpha"]
    assert REG["presupuesto"] == {"evaluaciones_internas":3600,"evaluaciones_baseline":600,
                                  "ajustes_ridge_internos":3000,"reajustes_exteriores":250}
    display(decisiones.groupby(["modelo","elegido"]).size().rename("pliegues").to_frame())
    print("200 decisiones verificadas desde 1,150 scores guardados; cero selección nueva.")
    ""","seleccion-visible")
    texto("""
    ## 6. Resultado registrado: cada error conserva su parcela y pliegue

    Se abren las OOF después de construir variables. Verificamos claves, etiquetas,
    región y pertenencia a validación; comparamos las tres referencias y R_B con V1.
    Este lector puntúa predicciones **guardadas**: no las vuelve a producir ni vuelve
    a aprender pendientes. Igualdad de métricas no demuestra paridad del entrenamiento
    entre Python histórico 3.12.3 y el lector 3.13.
    """)
    codigo("""
    oof = leer_csv("oof","resultados_guardados")
    assert len(oof) == 13800 and set(oof.modelo) == set(MODELOS)
    assert not oof.duplicated(["modelo"]+claves).any()
    esperado = set(map(tuple,validaciones[claves].to_numpy()))
    y = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    for m,q in oof.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple,q[claves].to_numpy())) == esperado
        np.testing.assert_array_equal(q.observado,q.ID_POLIGONO.map(y))
        np.testing.assert_array_equal(q.Municipio,q.ID_POLIGONO.map(grupos.Municipio))
        np.testing.assert_array_equal(q.grupo_J5,q.ID_POLIGONO.map(grupos.grupo_J5))
        np.testing.assert_array_equal(q.celda,q.ID_POLIGONO.map(grupos.celda_centroide))
        assert np.isfinite(q.predicho).all()
    v1oof = leer_csv("v1_oof","resultados_guardados")
    for m in ["GLOBAL","MUN","MIX","R_B"]:
        a = oof.loc[oof.modelo.eq(m)].set_index(claves).sort_index()
        b = v1oof.loc[v1oof.modelo.eq(m)].set_index(claves).sort_index()
        assert a.index.equals(b.index)
        np.testing.assert_allclose(a.predicho,b.predicho,atol=1e-8,rtol=0)
        np.testing.assert_array_equal(a.observado,b.observado)
    print("13,800 OOF conciliadas. R_B y tres referencias conservan sus predicciones a tolerancia 1e-8.")

    def metricas(df):
        y,p = df.observado.to_numpy(float),df.predicho.to_numpy(float)
        if len(y) == 0 or not np.isfinite(y).all() or not np.isfinite(p).all():
            raise ValueError("Métricas vacías o no finitas")
        error = p-y; den = np.sum((y-y.mean())**2)
        return pd.Series({"RMSE":np.sqrt(np.mean(error**2)),"MAE":np.mean(np.abs(error)),
                          "R2":1-np.sum(error**2)/den if den > 1e-12 else np.nan})

    def tabla_metricas(df):
        return pd.DataFrame({m:metricas(q) for m,q in df.groupby("modelo")}).T.reindex(MODELOS)

    globales = tabla_metricas(oof)
    control_m = leer_csv("metricas_control","control_posterior").set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(globales,control_m[["RMSE","MAE","R2"]],atol=1e-12,rtol=0)
    por_rep = pd.DataFrame([{"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                           for (m,r),q in oof.groupby(["modelo","repeticion"])])
    display(globales)
    print("Errores individuales agrupados; no promedio de predicciones por parcela ni de RMSE por pliegue.")
    ""","metricas-visibles")
    texto("""
    ## 7. ¿Supera la regla original?

    Regla interna, no criterio oficial del jurado: RMSE < MIX y MAE ≤ MUN globalmente,
    cada condición en al menos 8/10 repeticiones. Repeticiones comparten etiquetas:
    son estabilidad descriptiva, no diez estudios ni p-valores independientes.
    """)
    codigo("""
    def regla_avance(df):
        g = tabla_metricas(df)
        reps = pd.DataFrame([{"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                             for (m,r),q in df.groupby(["modelo","repeticion"])])
        R = reps.pivot(index="repeticion",columns="modelo",values="RMSE")
        A = reps.pivot(index="repeticion",columns="modelo",values="MAE")
        if set(R.index) != set(range(10)) or R.isna().any().any() or A.isna().any().any():
            raise ValueError("Repeticiones/modelos incompletos")
        filas = []
        for m in CANDIDATOS:
            nr,na = int((R[m]<R.MIX).sum()),int((A[m]<=A.MUN).sum())
            cumple = bool(g.loc[m,"RMSE"]<g.loc["MIX","RMSE"] and g.loc[m,"MAE"]<=g.loc["MUN","MAE"] and nr>=8 and na>=8)
            filas.append({"modelo":m,"reps_RMSE_menor_MIX":nr,"reps_MAE_menor_o_igual_MUN":na,"cumple":cumple})
        return pd.DataFrame(filas).set_index("modelo")

    regla_full = regla_avance(oof)
    ctrl_regla = leer_csv("regla_control","control_posterior").set_index("modelo").loc[CANDIDATOS]
    np.testing.assert_array_equal(regla_full.iloc[:,:2],ctrl_regla[regla_full.columns[:2]])
    np.testing.assert_array_equal(regla_full.cumple,ctrl_regla.avance_candidato)
    assert regla_full.index[regla_full.cumple].tolist() == ["J5_PCT"]
    display(regla_full)
    fig,axes = plt.subplots(1,2,figsize=(10.5,3.6))
    for ax,c,ref in zip(axes,["RMSE","MAE"],["MIX","MUN"]):
        ax.bar(CANDIDATOS,globales.loc[CANDIDATOS,c],color=["#287d77"]+["#75849b"]*4)
        ax.axhline(globales.loc[ref,c],color="#b64834",ls="--",label=ref)
        ax.set(ylabel=f"{c} (t/ha)",title="FULL138: resultado registrado")
        ax.tick_params(axis="x",rotation=25); ax.legend()
    fig.tight_layout(); plt.show()
    ""","regla-visible")
    texto("""
    **J5_PCT cumple la regla original.** No borramos ese resultado porque un diagnóstico
    posterior sea menos favorable. Para interpretar el avance hay que revisar el intercambio
    RMSE/MAE, el cambio conjunto de agrupación y dónde se concentran los errores.
    """)
    codigo("""
    # Etiquetas corregidas; no se altera el CSV histórico del contraste.
    PARES = [("J9_PCT","J5_PCT","Cambio conjunto de agrupación"),
             ("R9_PCT","J9_PCT","Regularización + selección"),
             ("R9_MM","R9_PCT","Cambio de representación, con intercambio RMSE/MAE"),
             ("R9_RAW","R9_MM","Reemplazar desviación por lluvia actual")]
    ctrl_c = leer_csv("contrastes_control","control_posterior").set_index(["modelo","base"])
    contrastes = []
    for m,b,descripcion in PARES:
        delta = globales.loc[m]-globales.loc[b]
        np.testing.assert_allclose(delta[["RMSE","MAE"]],ctrl_c.loc[(m,b),["delta_RMSE","delta_MAE"]].to_numpy(float),atol=1e-12,rtol=0)
        contrastes.append({"nuevo":m,"base":b,"lectura":descripcion,"delta_RMSE":delta.RMSE,"delta_MAE":delta.MAE})
    display(pd.DataFrame(contrastes))
    assert globales.loc["R9_PCT","RMSE"]<globales.loc["R9_MM","RMSE"]
    assert globales.loc["R9_PCT","MAE"]>globales.loc["R9_MM","MAE"]
    print("Porcentual reduce RMSE frente a mm, pero empeora MAE; no prueba aporte independiente de H.")
    ""","contrastes-visibles")
    texto("""
    ## 8. Diagnóstico posterior: municipio presente en entrenamiento

    Apan, Nanacamilpa y Tepeapulco tienen una etiqueta cada uno. Cuando esa parcela
    se valida, su municipio desaparece de entrenamiento: 30 OOF por procedimiento.
    La máscara se deriva de **IDs, municipio y roles**, no de los errores. Su aplicación
    como análisis se decidió después de ver V2: es **diagnóstico posterior**, no reemplazo
    retrospectivo de la evaluación registrada.

    SEEN135 conserva las OOF con municipio visto; no retira etiquetas de entrenamiento
    ni reentrena. Es una aproximación parcial, **no equivale a las 59 ocultas**. AGC_120
    pertenece a Nanacamilpa, con solo AGC_048 conocida y otra celda. No existe una OOF
    equivalente para evaluar ese caso entrenando con la única etiqueta municipal.
    """)
    codigo("""
    vistos = []
    for (r,f),q in externas.groupby(["repeticion","pliegue"]):
        mun_train = set(q.loc[q.rol.eq("entrenamiento"),"ID_POLIGONO"].map(grupos.Municipio))
        v = q.loc[q.rol.eq("validacion"),claves].copy()
        v["municipio_visto"] = v.ID_POLIGONO.map(grupos.Municipio).isin(mun_train)
        vistos.append(v)
    mascara = pd.concat(vistos,ignore_index=True)
    assert not mascara.duplicated(claves).any() and len(mascara) == 1380
    assert mascara.municipio_visto.sum() == 1350
    oof_esc = oof.merge(mascara,on=claves,validate="many_to_one")
    seen = oof_esc.loc[oof_esc.municipio_visto].copy()
    assert len(seen) == 13500 and seen.ID_POLIGONO.nunique() == 135
    regla_seen = regla_avance(seen)
    metricas_seen = tabla_metricas(seen)
    ctrl_post = leer_csv("metricas_escenarios_control","control_posterior_diagnostico")
    q = ctrl_post.loc[ctrl_post.escenario.eq("solo municipio visto (posterior)")].set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(metricas_seen,q[["RMSE","MAE","R2"]],atol=1e-12,rtol=0)
    ctrl_post_r = leer_csv("regla_escenarios_control","control_posterior_diagnostico")
    q = ctrl_post_r.loc[ctrl_post_r.escenario.eq("solo municipio visto (posterior)")].set_index("modelo").loc[CANDIDATOS]
    np.testing.assert_array_equal(regla_seen.iloc[:,:2],q[regla_seen.columns[:2]])
    np.testing.assert_array_equal(regla_seen.cumple,q.cumpliria_regla)
    assert not regla_seen.cumple.any()
    display(pd.concat({"FULL138 registrado":globales.loc[["J5_PCT","MIX","MUN"]],
                       "SEEN135 posterior":metricas_seen.loc[["J5_PCT","MIX","MUN"]]},names=["escenario"]))
    display(regla_seen)
    display(grupos.loc[["AGC_048","AGC_120"],["Municipio","CONJUNTO","celda_centroide"]])
    print("Sin reentrenar: J5 conserva RMSE menor, pero su MAE es peor que MUN en 10/10 repeticiones.")
    ""","escenarios-visibles")
    texto("""
    ## 9. ¿La mejora está distribuida?

    Comparamos J5 con MIX en las mismas claves. Sumar cambios de error cuadrático
    permite localizar el beneficio; no es rendimiento explicado ni causalidad.
    El porcentaje de los singleton usa la mejora **neta**. El de las mejores parcelas
    o celdas usa la mejora **bruta** entre casos que mejoran: denominadores distintos.
    Quitar los cinco más favorecidos es diagnóstico posterior, solo de evaluación.
    """)
    codigo("""
    a = oof.query("modelo == 'J5_PCT'").set_index(claves).sort_index()
    b = oof.query("modelo == 'MIX'").set_index(claves).sort_index()
    assert a.index.equals(b.index)
    d = a[["observado","predicho","celda","Municipio"]].copy()
    d["delta_se"] = (a.predicho-a.observado)**2-(b.predicho-b.observado)**2
    por_parcela = d.reset_index().groupby("ID_POLIGONO").agg(delta_se=("delta_se","sum"),celda=("celda","first"))
    neto = float(por_parcela.delta_se.sum())
    singletons = ["AGC_164","AGC_048","AGC_047"]
    contrib_singletons = float(por_parcela.loc[singletons,"delta_se"].sum())
    top5 = por_parcela.nsmallest(5,"delta_se")
    bruta = -float(por_parcela.loc[por_parcela.delta_se.lt(0),"delta_se"].sum())
    celdas = por_parcela.groupby("celda").delta_se.sum()
    bruta_celdas = -float(celdas.loc[celdas.lt(0)].sum())
    fraccion_top2_celdas_bruta = -float(celdas.nsmallest(2).sum())/bruta_celdas
    assert neto < 0 and neto-top5.delta_se.sum() > 0
    assert por_parcela.loc["AGC_164","delta_se"] > 0
    display(por_parcela.loc[singletons])
    display(top5)
    display(pd.DataFrame([{"delta_SE_neto":neto,"singleton_fraccion_neta":contrib_singletons/neto,
                           "top5_fraccion_bruta":-top5.delta_se.sum()/bruta,
                           "top2_celdas_fraccion_bruta":fraccion_top2_celdas_bruta,
                           "neto_sin_top5_solo_evaluacion":neto-top5.delta_se.sum(),
                           "parcelas_mejoran":int(por_parcela.delta_se.lt(0).sum()),
                           "parcelas_empeoran":int(por_parcela.delta_se.gt(0).sum())}]))
    train_ids = set(etiquetas.ID_POLIGONO)
    celdas_inter_train = pesos.loc[pesos.ID_POLIGONO.isin(train_ids),["fila","col"]].drop_duplicates()
    assert len(celdas_inter_train) == 27 and grupos.loc[list(train_ids),"celda_centroide"].nunique() == 23
    display(pd.DataFrame({"conteo":["Centroides, 138 etiquetas","Píxeles de intersección, 138 etiquetas",
                                   "Píxeles de intersección, 197 parcelas"],"celdas":[23,27,29]}))
    ""","concentracion-visible")
    texto("""
    Las tres parcelas singleton aportan **58.49 % del beneficio neto**; una de ellas
    (AGC_164) empeora. Sin los cinco casos más favorables, J5 pierde frente a MIX en
    suma de errores cuadrados. No se eliminan esos casos para entrenar ni se redefine
    la regla. **23 celdas de centroide no son un tamaño muestral efectivo de 23.**
    La extracción utiliza 27 píxeles para las etiquetas y 29 para todas las parcelas;
    también puede haber dependencia entre píxeles.

    La sensibilidad sin AGC_127/171 sí estaba prevista: conserva las mismas OOF,
    retirando esas dos parcelas **solo al evaluar**. No sustituye el resultado principal.
    """)
    codigo("""
    sensibilidad = tabla_metricas(oof.loc[~oof.ID_POLIGONO.isin(["AGC_127","AGC_171"])])
    ctrl_sens = leer_csv("sensibilidad_control","control_posterior").set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(sensibilidad,ctrl_sens[["RMSE","MAE","R2"]],atol=1e-12,rtol=0)
    zonas = pd.DataFrame([{"modelo":m,"zona":z,**metricas(q).to_dict()}
                          for (m,z),q in oof.groupby(["modelo","zona"])])
    display(sensibilidad.loc[["J5_PCT","MIX","MUN"]])
    display(zonas.loc[zonas.modelo.isin(["J5_PCT","MIX","MUN"])].set_index(["modelo","zona"]))
    ""","sensibilidad-visible")
    texto("""
    ## 10. Decisión y límites

    **J5_PCT cumple la regla histórica y permanece como candidato exploratorio con
    reservas; no es modelo final.** El diagnóstico posterior no revoca su resultado:
    limita qué podemos creer sobre su aplicación a las parcelas sin etiqueta.

    - PCT mejora RMSE frente a mm, pero empeora MAE; H no fue probado aquí como aporte separado.
    - Cambiar de agrupación cambia medias, residuos, escala y respaldos; no aísla causalidad.
    - Beneficio concentrado y soporte climático compartido reducen la fuerza de la evidencia.
    - Una temporada, tres años de referencia y selección adaptativa: no extrapolar a otras campañas o territorios.
    - La política para municipios con una etiqueta requiere decisión explícita antes de predicciones finales.

    Igualdad aritmética y hashes prueban reconstrucción e integridad, no medición sin error,
    fecha externa ni validez crediticia. No descarta el clima, octubre ni toda familia lineal.
    La continuación estudia H con una pregunta nueva; no se ejecuta ni selecciona aquí.
    """)
    codigo("""
    resumen = {"id":"EXP_04","modo":"lector_retrospectivo_sin_ajustes","parcelas":197,"etiquetas":138,
               "piezas_guardadas":230,"pixeles_derivados":116,"lluvias_recalculadas":788,
               "procedimientos":10,"oof_por_procedimiento":1380,"oof_total":13800,
               "particiones_externas":50,"particiones_internas":200,
               "decisiones_verificadas":200,"scores_guardados_verificados":1150,
               "ajustes_actuales":0,"predicciones_finales_generadas":0,"poblacion":"FULL138",
               "scores_interiores_recalculados":False,"predicciones_recalculadas":False,
               "intersecciones_recalculadas":False,"variables_recalculadas":True,"metricas_recalculadas":True,
               "candidato_con_reservas":["J5_PCT"],"variantes_adoptadas":[],
               "diagnostico_posterior":"SEEN135","oof_seen_por_procedimiento":1350,
               "regla_full_cumplen":regla_full.index[regla_full.cumple].tolist(),
               "regla_seen_cumplen":regla_seen.index[regla_seen.cumple].tolist(),
               "fecha_original":"2026-10-01","fecha_adaptacion":"2026-10-08",
               "metricas":globales.to_dict(orient="index"),"metricas_seen":metricas_seen.to_dict(orient="index"),
               "fecha_ejecucion_utc":datetime.now(timezone.utc).isoformat()}
    print("RESUMEN_EXP_04_JSON="+json.dumps(resumen,sort_keys=True,ensure_ascii=False,allow_nan=False))
    ""","cierre")
    texto("""
    ## Referencias y conceptos para profundizar (APA 7)

    Equipo AgroCebada. (2026, 1 de octubre). *Protocolo definitivo V2: señal climática
    de octubre* [Registro interno exploratorio]. Registro, hashes y resultados
    identificados en los insumos de este cuaderno; no es necesario otro documento.

    Equipo AgroCebada. (2026, 1 de octubre). *V2: fe de erratas y cierre de revisión*
    [Nota interna]. Sus precisiones sobre métricas, agrupación, escenarios y soporte
    espacial están incorporadas aquí; los archivos registrados no se reescriben.

    NumPy Developers. (s. f.). *numpy.average*. https://numpy.org/doc/stable/reference/generated/numpy.average.html

    NumPy Developers. (s. f.). *numpy.std*. https://numpy.org/doc/stable/reference/generated/numpy.std.html

    Rasterio Developers. (s. f.). *Reading datasets*. https://rasterio.readthedocs.io/en/stable/topics/reading.html

    **Glosario breve:** OOF = predicción para una parcela fuera del entrenamiento;
    singleton = grupo con una etiqueta; OLS = mínimos cuadrados; Ridge = penalización
    de pendiente; baseline = pendiente cero; beneficio neto = mejora menos empeoramiento;
    beneficio bruto = solo casos que mejoran. FULL138 es la evaluación registrada;
    SEEN135, un diagnóstico posterior. No son dos conjuntos ocultos independientes.
    """)
    for i,c in enumerate(celdas):
        c.id = f"exp04-{i:03d}"
    metadata = copy.deepcopy(base.metadata)
    metadata["agrocebada"] = {
        "id":"EXP_04","modo":"lector_retrospectivo_sin_ajustes","crisp_dm":[3,4,5],
        "fecha_original":"2026-10-01","fecha_adaptacion":"2026-10-08","ajustes_actuales":0,
        "colab_real_probado":False,"dependencias_requeridas":base.metadata.agrocebada.dependencias_requeridas,
        "perfil_sha256":base.metadata.agrocebada.perfil_sha256,"soporte_sha256":base.metadata.agrocebada.soporte_sha256,
        "fuentes_sha256":{cfg_rel:huella((raiz/cfg_rel).read_bytes()),base_rel:BASE_SHA256},
        "insumos":cfg["insumos"],"recorte_pixeles":cfg["recorte_pixeles"],
    }
    return nbformat.v4.new_notebook(cells=celdas,metadata=metadata)


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida",type=Path,default=raiz/"notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb")
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
