"""EXP_07: lector autónomo de la ronda registrada, sin reajustar modelos."""
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
CONFIG = "config/exp_07_heterogeneidad_parcela.json"


def cargar_insumos(raiz):
    cfg = json.loads((Path(raiz) / CONFIG).read_text())
    salida = {}
    for k, c in cfg["insumos"].items():
        b = (Path(raiz) / c["ruta_local"]).read_bytes()
        if not 0 < len(b) <= 2 * 1024 * 1024 or len(b) != c["bytes"] or hashlib.sha256(b).hexdigest() != c["sha256"]:
            raise ValueError(f"Insumo distinto o demasiado grande: {k}")
        salida[k] = {**c, "bytes_zlib_base64": base64.b64encode(zlib.compress(b, 9)).decode()}
    return cfg, salida


def construir(raiz=None):
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    cfg, registros = cargar_insumos(raiz)
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
    # EXP_07. ¿La heterogeneidad espacial añade información al NDVI medio?

    **CRISP-DM: entender, preparar, modelar y evaluar.** Dos parcelas pueden tener
    el mismo verdor medio y diferente dispersión interna. Preguntamos si la
    desviación espacial NDVI **entregada por Planet** añade información fuera de
    muestra después de municipio y NDVI medio. No es variación temporal ni una
    medición de incertidumbre del rendimiento.

    La ronda se ejecutó con un registro previo propio el **8/oct/2026**. Este
    cuaderno **lee esa corrida**: reconstruye L/S desde capturas y recalcula métricas
    desde OOF guardadas. **Cero ajustes al ejecutarlo**; no vuelve a entrenar ni
    genera los 59 rendimientos de entrega. No es una confirmación independiente:
    la hipótesis aprovechó etiquetas y resultados de rondas anteriores.

    **Recorrido:** una captura → soporte pareado → 197 parcelas → factibilidad X →
    comparación C0/C1 → selector → ecuación guardada → errores → decisión.
    Basta este notebook, sin Git, Drive, ZIP ni otros cuadernos. El código científico
    es visible; dos bloques técnicos pueden desplegarse para inspeccionar detalles.
    """)
    texto("""
    ## 1. Fuentes y alcance de esta lectura

    | Entrada | Se hace aquí | No se hace aquí |
    | --- | --- | --- |
    | Capturas Planet del ciclo, seis columnas | Parear promedio/std y reconstruir L/S | Leer píxeles, fabricar una máscara o filtrar nubes |
    | Metadatos y roles guardados | Verificar soporte y cada entrenamiento solo con X | Usar rendimiento para elegir fechas o receta |
    | Scores, parámetros y OOF de la corrida | Verificar selección y recalcular errores | Reentrenar ni transformar esas OOF en etiquetas |
    | Código del motor y registro previo | Inspeccionar implementación y hashes | Ejecutar el motor automáticamente |

    En la celda técnica los insumos se verifican por tamaño/SHA-256. El código
    completo del motor queda también como texto comentado inspeccionable: **no
    se ejecuta**. La implementación ajustada originalmente no está oculta detrás
    de resultados, pero estudiarla no exige leer toda la infraestructura.
    """)
    for tag in ["soporte-colab", "preparar-colab", "entorno"]:
        reutilizar(tag)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    comentarios = []
    for k in ["modelo_fuente", "experimento_fuente"]:
        fuente = (raiz / cfg["insumos"][k]["ruta_local"]).read_text()
        comentarios.append("\n# Fuente completa solo para inspección: " + k + "\n" +
                           "\n".join("#| " + line for line in fuente.splitlines()))
    codigo("INSUMOS_INCRUSTADOS = " + repr(registros) + "\n\n" + decoder +
           "\n\n# Acceso por rol fijado en el manifiesto, no por rutas externas.\n"
           "def csv_insumo(k):\n    return leer_csv(k, INSUMOS_INCRUSTADOS[k]['uso'])\n"
           "def json_insumo(k):\n    return json.loads(bytes_insumo(k, INSUMOS_INCRUSTADOS[k]['uso']))\n" +
           "\n".join(comentarios), "insumos-tecnicos", "Insumos verificados y código de la corrida para inspección; no se entrena")
    codigo("""
    L = "H7_PL_ndvi_media_pareada"
    S = "H7_PL_ndvi_std_media_pareada"
    metadata = csv_insumo("metadata")
    capturas = csv_insumo("capturas")
    externas = csv_insumo("externas")
    internas = csv_insumo("internas")
    QA = json_insumo("diagnosticos_X")
    assert QA["usa_rendimientos"] is False and QA["ajustes_modelos"] == 0
    assert QA["apta"] and len(metadata) == 197 and metadata.ID_POLIGONO.is_unique
    assert not any("RENDIMIENTO" in c for c in metadata) and not any("RENDIMIENTO" in c for c in capturas)
    assert set(metadata.CONJUNTO) == {"ENTRENAMIENTO", "PREDICCION"}
    assert metadata.CONJUNTO.eq("ENTRENAMIENTO").sum() == 138
    assert metadata.CONJUNTO.eq("PREDICCION").sum() == 59
    assert set(capturas) == {"ID_POLIGONO","fecha_captura","sensor","ndvi_promedio","ndvi_std","porcentaje_nubosidad"}
    assert len(capturas) == 26255 and set(capturas.sensor) == {"Planet"}
    assert set(capturas.ID_POLIGONO) == set(metadata.ID_POLIGONO)
    capturas["fecha"] = pd.to_datetime(capturas.fecha_captura,format="%d/%m/%Y",errors="raise")
    assert capturas.fecha.between("2025-04-01","2025-10-31").all()
    assert not capturas.duplicated(["ID_POLIGONO","fecha","sensor"]).any()
    for c in ["ndvi_promedio","ndvi_std","porcentaje_nubosidad"]:
        assert not np.isinf(capturas[c].to_numpy(float)).any()
    assert capturas.ndvi_std.dropna().ge(0).all()
    assert capturas.ndvi_promedio.dropna().between(-1,1).all()
    assert capturas.porcentaje_nubosidad.dropna().between(0,100).all()
    display(metadata.groupby(["Municipio","CONJUNTO"]).size().rename("parcelas").to_frame())
    print("197 metadatos sin rendimiento; todavía no se cargan las etiquetas.")
    """, "fuentes-visibles")
    texto("""
    ## 2. Una parcela antes de generalizar

    `ndvi_promedio` es el nivel medio de una captura; `ndvi_std` describe su
    dispersión espacial dentro de la parcela. **S = media de esas desviaciones**,
    no desviación del promedio a lo largo del tiempo. El diccionario no especifica
    número de píxeles válidos, máscara o ddof: usamos la estadística entregada.

    Ventana abril–octubre, inclusiva, sin un nuevo filtro de nube. Cada captura
    debe tener ambas estadísticas finitas para participar en **ambas medias**.
    Las ausencias se conservan, no se sustituyen por cero. AGC_001 mantiene el
    ejemplo del recorrido anterior; no se elige por su rendimiento/error.
    """)
    codigo("""
    capturas["promedio_finito"] = np.isfinite(capturas.ndvi_promedio)
    capturas["std_finita"] = np.isfinite(capturas.ndvi_std)
    capturas["pareada"] = capturas.promedio_finito & capturas.std_finita
    capturas["mes"] = capturas.fecha.dt.month
    par = capturas.loc[capturas.pareada].copy()
    ejemplo = par.loc[par.ID_POLIGONO.eq("AGC_001")].sort_values("fecha")
    l_uno = float(ejemplo.ndvi_promedio.sum()/len(ejemplo))
    s_uno = float(ejemplo.ndvi_std.sum()/len(ejemplo))
    display(ejemplo[["fecha","ndvi_promedio","ndvi_std","porcentaje_nubosidad"]].head(8))
    display(pd.DataFrame([{"parcela":"AGC_001","capturas_pareadas":len(ejemplo),"L":l_uno,"S":s_uno,
                          "otra_operacion_std_temporal_de_promedios":ejemplo.ndvi_promedio.std(ddof=0)}]))
    fig,axes = plt.subplots(2,1,figsize=(10,4.8),sharex=True)
    axes[0].plot(ejemplo.fecha,ejemplo.ndvi_promedio,color="#287d77",label="Promedio de cada captura")
    axes[0].axhline(l_uno,color="#75849b",ls="--",label="L: media por captura")
    axes[1].plot(ejemplo.fecha,ejemplo.ndvi_std,color="#b64834",label="Desviación espacial entregada")
    axes[1].axhline(s_uno,color="#75849b",ls="--",label="S: media de desviaciones espaciales")
    axes[0].set(ylabel="NDVI promedio",title="AGC_001: dos estadísticas distintas sobre las mismas capturas")
    axes[1].set(ylabel="NDVI std espacial",xlabel="Fecha 2025")
    for ax in axes: ax.legend(fontsize=8)
    fig.tight_layout(); plt.show()
    """, "parcela-visible")
    texto("""
    ## 3. La misma regla para las 197 parcelas

    Agrupar por ID y promediar dos columnas sobre `par` crea L/S. Los nombres
    nuevos preservan las columnas históricas. La extracción anterior omitía NaN
    de std por separado; primero comprobamos las máscaras. **Aquí coinciden**:
    el pareado no cambia efectivamente la receta; el control posterior lo demuestra.
    Construir primero y contrastar después evita usar una salida como entrada.
    """)
    codigo("""
    medias = par.groupby("ID_POLIGONO")[["ndvi_promedio","ndvi_std"]].mean().rename(columns={"ndvi_promedio":L,"ndvi_std":S})
    variables = metadata.merge(medias,on="ID_POLIGONO",how="left",validate="one_to_one").sort_values("ID_POLIGONO").reset_index(drop=True)
    control = csv_insumo("variables_control").sort_values("ID_POLIGONO").reset_index(drop=True)
    pd.testing.assert_frame_equal(variables,control,check_exact=True)
    np.testing.assert_allclose(variables.set_index("ID_POLIGONO").loc["AGC_001",[L,S]].to_numpy(float),[l_uno,s_uno],atol=1e-12,rtol=0)
    hist = csv_insumo("comparacion_v0_control").set_index("ID_POLIGONO").sort_index()
    actual = variables.set_index("ID_POLIGONO").sort_index()
    np.testing.assert_allclose(actual[[L,S]],hist[["C_PL_ndvi_media","C_PL_ndvi_std_media"]],atol=1e-12,rtol=0,equal_nan=True)
    assert capturas.promedio_finito.eq(capturas.std_finita).all()
    assert len(par) == 18248 and len(variables) == 197 and variables[[L,S]].notna().all().all()
    assert "RENDIMIENTO_T_HA" not in variables
    display(variables.head(8))
    print("18,248 capturas pareadas; 197 filas preservadas; igualdad con v0 a 10⁻¹².")
    """, "variables-visibles")
    texto("""
    ## 4. Factibilidad sin rendimiento

    Hay capturas pareadas en los siete meses para todas las parcelas. No exigimos
    el mismo número de escenas ni inventamos valores diarios. Una media por captura
    pesa más las fechas observadas con mayor frecuencia; cambiar eso reabriría EXP_02.

    En cada uno de los **50 entrenamientos exteriores y 200 interiores** se
    comprueba disponibilidad para imputar y variación intramunicipal de S. Solo se
    usan sus propias X: mediana → centrado por municipio → escala poblacional.
    Estas estadísticas sirven de control de factibilidad, no se reutilizan para
    ajustar candidatos. Columnas vacías o S sin variación habrían detenido la ronda.
    """)
    codigo("""
    mensual = pd.MultiIndex.from_product([metadata.ID_POLIGONO,range(4,11)],names=["ID_POLIGONO","mes"]).to_frame(index=False).merge(
        par.groupby(["ID_POLIGONO","mes"]).agg(n_pareadas=("ndvi_std","size"),L_media=("ndvi_promedio","mean"),S_media=("ndvi_std","mean"),nube_media=("porcentaje_nubosidad","mean")).reset_index(),
        how="left",validate="one_to_one")
    mensual.n_pareadas = mensual.n_pareadas.fillna(0).astype(int)
    mensual_control = csv_insumo("mensual_control")
    pd.testing.assert_frame_equal(mensual,mensual_control,check_exact=True)
    assert mensual.n_pareadas.gt(0).all() and len(mensual) == 1379
    x = variables.set_index("ID_POLIGONO")
    var_rows = []
    for nivel,roles,keys in [("exterior",externas,["repeticion","pliegue"]),("interior",internas,["repeticion","pliegue","pliegue_interno"])]:
        for clave,g in roles.groupby(keys,sort=True):
            tr = x.loc[g.loc[g.rol.eq("entrenamiento"),"ID_POLIGONO"]]
            for campo in [L,S]:
                v = tr[campo].to_numpy(float); n = int(np.isfinite(v).sum())
                if n == 0: raise ValueError("Columna vacía en entrenamiento: detener")
                mediana = float(np.nanmedian(v)); imp = np.where(np.isnan(v),mediana,v)
                serie = pd.Series(imp,index=tr.index)
                residuo = serie-serie.groupby(tr.Municipio).transform("mean")
                escala = float(np.sqrt(np.mean(residuo.to_numpy()**2)))
                umbral = 1e-12*max(1.,float(np.max(np.abs(imp))))
                var_rows.append({"nivel":nivel,**dict(zip(keys,clave)),"variable":campo,"n_entrenamiento":len(tr),"n_finitos":n,
                                 "mediana_diagnostica":mediana,"escala_intramunicipal":escala,"umbral_escala":umbral,"columna_vacia":False,"escala_degenerada":bool(escala<=umbral)})
    variacion = pd.DataFrame(var_rows)
    var_control = csv_insumo("variacion_control")
    pd.testing.assert_frame_equal(variacion,var_control,check_exact=False,atol=1e-12,rtol=0)
    assert len(variacion) == 500 and not variacion.loc[variacion.variable.eq(S),"escala_degenerada"].any()
    display(mensual.loc[mensual.ID_POLIGONO.eq("AGC_001")])
    display(variacion.groupby(["nivel","variable"]).agg(train=("n_entrenamiento","size"),min_finitos=("n_finitos","min"),min_escala=("escala_intramunicipal","min")))
    """, "factibilidad-visible")
    texto("""
    **Calidad y alcance:** área, nubosidad y número de capturas pueden acompañar
    a la señal. Sus asociaciones con S son diagnósticos entre X, no razones para
    seleccionar otra receta según rendimiento. Una correlación baja no elimina
    confusión no lineal ni demuestra precisión de la medición.

    Las 59 ocultas tienen L/S disponibles. Se muestran rangos frente a sus municipios
    etiquetados, sin predecirlas. Nanacamilpa sigue con una etiqueta y no tiene un
    caso OOF equivalente a la entrega. Rango univariado no es garantía de soporte.
    """)
    codigo("""
    calidad = csv_insumo("calidad_control")
    corrs = csv_insumo("correlaciones_X_control")
    assert calidad.ID_POLIGONO.is_unique and len(calidad) == 197
    assert calidad.n_pareadas.sum() == len(par) and calidad.meses_con_par.eq(7).all()
    assert calidad.n_promedio_sin_std.sum() == calidad.n_std_sin_promedio.sum() == 0
    correlacion_recalculada = variables.loc[variables.CONJUNTO.eq("ENTRENAMIENTO"),["Municipio",L,S]].copy()
    for c in [L,S]:
        correlacion_recalculada[c] -= correlacion_recalculada.groupby("Municipio")[c].transform("mean")
    r_x = correlacion_recalculada[L].corr(correlacion_recalculada[S])
    r_control = corrs.loc[corrs.poblacion.eq("ENTRENAMIENTO_X") & corrs.tipo.eq("intramunicipal") & corrs.variable_2.eq(L),"pearson"].iloc[0]
    np.testing.assert_allclose(r_x,r_control,atol=1e-12,rtol=0)
    soporte = csv_insumo("soporte_control")
    assert len(soporte) == 59 and not soporte.L_ausente.any() and not soporte.S_ausente.any()
    assert set(soporte.ID_POLIGONO) == set(variables.loc[variables.CONJUNTO.eq("PREDICCION"),"ID_POLIGONO"])
    display(corrs.loc[corrs.poblacion.eq("ENTRENAMIENTO_X") & corrs.tipo.eq("intramunicipal"),["variable_2","pearson","n_pares"]])
    display(soporte.groupby("Municipio").agg(ocultas=("ID_POLIGONO","size"),etiquetadas=("n_parcelas_etiquetadas_municipio","first"),L_fuera=("L_fuera_rango_municipal","sum"),S_fuera=("S_fuera_rango_municipal","sum")))
    display(soporte.loc[soporte.caso_singleton])
    print("Factibilidad superada usando X; esto aún no demuestra aporte predictivo de S.")
    """, "calidad-soporte-visible")
    texto("""
    ## 5. La comparación que responde la hipótesis

    | Procedimiento | Variables numéricas | Qué responde |
    | --- | --- | --- |
    | C0 | L | Control de nivel, con corrección municipal + Ridge |
    | C1 | L + S | Añadido de una dimensión espacial, misma arquitectura |
    | MUN / MIX | Recetas fijas del recorrido | Competitividad frente a referencias fuertes |

    Por entrenamiento: mediana de X → restar medias municipales de X e y →
    escalar residuos → Ridge sin intercepto → sumar media municipal al predecir.
    Los interceptos municipales no se penalizan. Municipio no visto: media global
    sin corrección. Esta arquitectura es la extensión multivariable de las rondas
    de lluvia, **no E2**, que penalizaba one-hot municipal.

    La imputación es común a C0/C1 y aprendida dentro de cada entrenamiento.
    Las columnas de ausencia no entran como predictores. Una escala degenerada
    anula solo esa corrección, no las otras; singleton participa con residuo cero.
    Una opción `baseline` recupera MUN exactamente. No se corrige MIX con residuos
    históricos OOF ni se usan las 59 X para estimar estadísticas de entrenamiento.
    """)
    codigo("""
    PRE = json_insumo("registro_previo")
    REG = json_insumo("registro_ejecucion")
    assert REG["registro_sha256"] == hashlib.sha256(bytes_insumo("registro_previo",INSUMOS_INCRUSTADOS["registro_previo"]["uso"])).hexdigest()
    etiquetas = csv_insumo("etiquetas")
    assert len(etiquetas) == 138 and etiquetas.ID_POLIGONO.is_unique
    assert set(etiquetas.ID_POLIGONO) == set(metadata.loc[metadata.CONJUNTO.eq("ENTRENAMIENTO"),"ID_POLIGONO"])
    assert np.isfinite(etiquetas.RENDIMIENTO_T_HA).all()
    assert REG["predicciones_59_generadas"] == 0
    print("Solo ahora se cargan etiquetas y resultados de la corrida registrada.")
    print("Registro previo UTC:",PRE["registrado_utc"])
    print("Corrida UTC:",REG["inicio_utc"],"→",REG["fin_utc"])
    print("Entorno de la corrida:",REG["python"],"| presupuesto real:",REG["presupuesto"])
    print("Esta ejecución del lector no suma ningún ajuste a ese presupuesto.")
    """, "registro-visible")
    texto("""
    ## 6. Particiones y selector interior, sin nueva búsqueda

    Conservamos los mismos CSV: cinco pliegues × diez repeticiones y cuatro
    interiores por entrenamiento exterior, siempre por parcela. Medianas, medias
    y escala originales se aprendieron otra vez en cada entrenamiento interior.
    Selección original sobre FULL interior; SEEN135 solo es población de evaluación
    principal. No se busca otra semilla o se cambia selector por el resultado.
    """)
    reutilizar("particiones-visibles")
    texto("""
    Seis opciones: baseline y alpha 0.01/0.1/1/10/100. RMSE interior agrupado =
    raíz de suma SSE de las cuatro validaciones / número total de sus predicciones.
    Empate a 10⁻¹²: baseline primero, después alpha mayor. Los archivos conservan
    **2,400 SSE interiores**, **600 scores agrupados** y **100 decisiones**; podemos
    comprobar esa aritmética sin ejecutar modelos.

    Presupuesto de una corrida: 2,400 evaluaciones internas —400 baseline y 2,000
    opciones Ridge—, 100 reconstrucciones exteriores y 100 evaluaciones de
    referencias. El registro separa llamadas Ridge efectivas de opciones y
    reconstrucciones. Una réplica determinista repite coste físico, no añade hipótesis.
    """)
    codigo("""
    scores = csv_insumo("scores")
    pliegues = csv_insumo("scores_pliegue")
    seleccion = csv_insumo("seleccion")
    assert len(scores) == 600 and len(pliegues) == 2400 and len(seleccion) == 100
    keys_sel = ["modelo","repeticion","pliegue"]
    assert not scores.duplicated(keys_sel+["opcion"]).any()
    assert not pliegues.duplicated(keys_sel+["pliegue_interno","opcion"]).any()
    assert not seleccion.duplicated(keys_sel).any()
    pooled = pliegues.groupby(keys_sel+["opcion"],as_index=False).agg(SSE=("SSE","sum"),n_validacion=("n_validacion","sum"))
    pooled["RMSE"] = np.sqrt(pooled.SSE/pooled.n_validacion)
    a,b = pooled.set_index(keys_sel+["opcion"]).sort_index(),scores.set_index(keys_sel+["opcion"]).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a[["SSE","n_validacion","RMSE"]],b[["SSE","n_validacion","RMSE"]],atol=1e-12,rtol=0)
    elegidas = []
    for key,g in scores.groupby(keys_sel,sort=True):
        vals = g.set_index("opcion").RMSE
        assert set(vals.index) == {"baseline","0.01","0.1","1.0","10.0","100.0"}
        empate = vals[vals <= vals.min()+1e-12].index.tolist()
        opcion = "baseline" if "baseline" in empate else str(max(float(o) for o in empate))
        elegidas.append({**dict(zip(keys_sel,key)),"opcion_elegida":opcion,"RMSE_interior":float(vals[opcion])})
    dec = pd.DataFrame(elegidas).set_index(keys_sel).sort_index()
    sel = seleccion.set_index(keys_sel).sort_index()
    np.testing.assert_array_equal(dec.opcion_elegida,sel.opcion_elegida)
    np.testing.assert_allclose(dec.RMSE_interior,sel.RMSE_interior,atol=1e-12,rtol=0)
    assert REG["presupuesto"]["evaluaciones_internas"] == 2400
    display(seleccion.groupby(["modelo","opcion_elegida"]).size().rename("exteriores").to_frame())
    print("600 scores desde 2,400 SSE y 100 elecciones reproducidos; cero nuevas llamadas Ridge.")
    """, "seleccion-visible")
    texto("""
    ## 7. Abrir una predicción, con parámetros guardados

    Para un municipio visto:

    `ŷ = media_y_del_municipio + Σ β_j × (X_imputada_j − media_X_municipal_j) / escala_j`.

    Se usan mediana, medias, escala y β **guardados de ese entrenamiento**, no
    estadísticas calculadas con la parcela validada. Abrimos C1, repetición 0,
    pliegue 0 y su primer ID de validación ordenado. No se elige por el error.
    Comprobar esta ecuación reproduce la aplicación de parámetros, **no reentrena**
    el modelo ni acredita por sí solo toda la selección interior.
    """)
    codigo("""
    parametros = json_insumo("parametros")
    oof = csv_insumo("oof")
    assert len(parametros) == 100 and len(oof) == 5520
    p = next(p for p in parametros if p["modelo"] == "C1" and p["repeticion"] == 0 and p["pliegue"] == 0)
    m = p["modelo_ajustado"]
    id_uno = sorted(externas.loc[externas.repeticion.eq(0)&externas.pliegue.eq(0)&externas.rol.eq("validacion"),"ID_POLIGONO"])[0]
    fila = variables.set_index("ID_POLIGONO").loc[id_uno]
    raw = fila[p["columnas"]].to_numpy(float)
    imp = np.where(np.isnan(raw),np.asarray(m["medianas"],float),raw)
    activa = np.asarray(m["activa"],bool); beta = np.asarray(m["beta"],float)
    conocido = fila.Municipio in m["media_y"]
    if conocido:
        media_x = np.asarray(m["media_x"][fila.Municipio],float)
        escala = np.asarray(m["escala"],float)
        z = np.zeros(len(raw)); z[activa] = (imp[activa]-media_x[activa])/escala[activa]
        componentes = beta*z
        territorial = m["media_y"][fila.Municipio]
    else:
        z = np.zeros(len(raw)); componentes = np.zeros(len(raw)); territorial = m["media_global_y"]
    pred_uno = float(territorial+componentes.sum())
    guardada = oof.loc[oof.modelo.eq("C1")&oof.repeticion.eq(0)&oof.pliegue.eq(0)&oof.ID_POLIGONO.eq(id_uno),"predicho"].iloc[0]
    np.testing.assert_allclose(pred_uno,guardada,atol=1e-12,rtol=0)
    display(pd.DataFrame({"columna":p["columnas"],"entrada":raw,"imputada":imp,"z_train":z,"beta_guardada":beta,"correccion":componentes}))
    print(id_uno,"· componente municipal",territorial,"+ corrección",float(componentes.sum()),"=",pred_uno,"t/ha")
    """, "ecuacion-visible")
    texto("""
    ## 8. Evaluación OOF sobre las mismas parcelas

    Cada procedimiento tiene 1,380 OOF: diez predicciones fuera de muestra de
    cada una de 138 parcelas. No son 1,380 muestras independientes. **SEEN135**
    puntúa solo municipio presente en su entrenamiento exterior: 1,350 OOF por
    procedimiento, sin retirar las tres etiquetas singleton del entrenamiento.
    FULL138 sigue como secundario; no se comparan cifras de poblaciones diferentes.

    RMSE y MAE se calculan sobre errores concatenados, sin promediar primero por
    parcela o pliegue. R² ordena igual que RMSE sobre la misma muestra/pesos; no
    queda definido cuando no hay variación efectiva del objetivo. Se conserva la
    guarda numérica de la corrida: SST > 10⁻¹⁴ × max(1, suma y²).
    """)
    codigo("""
    MODELOS = ["MUN","MIX","C0","C1"]
    assert set(oof.modelo) == set(MODELOS) and not oof.duplicated(["modelo"]+claves).any()
    esperado = set(map(tuple,validaciones[claves].to_numpy()))
    y_oficial = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    mascara_rows = []
    for (r,f),g in externas.groupby(["repeticion","pliegue"]):
        mun_tr = set(g.loc[g.rol.eq("entrenamiento"),"ID_POLIGONO"].map(x.Municipio))
        va = g.loc[g.rol.eq("validacion"),claves].copy()
        va["municipio_visto"] = va.ID_POLIGONO.map(x.Municipio).isin(mun_tr)
        mascara_rows.append(va)
    mascara = pd.concat(mascara_rows,ignore_index=True)
    for modelo,g in oof.groupby("modelo"):
        assert len(g) == 1380 and set(map(tuple,g[claves].to_numpy())) == esperado
        np.testing.assert_array_equal(g.observado,g.ID_POLIGONO.map(y_oficial))
        np.testing.assert_array_equal(g.Municipio,g.ID_POLIGONO.map(x.Municipio))
        q = g.merge(mascara,on=claves,validate="one_to_one",suffixes=("_guardada",""))
        np.testing.assert_array_equal(q.municipio_visto_guardada,q.municipio_visto)
        assert int(g.municipio_visto.sum()) == 1350
    assert np.isfinite(oof[["observado","predicho"]]).all().all()
    seen = oof.loc[oof.municipio_visto].copy()
    ESCENARIOS = {"SEEN135":seen,"FULL138":oof}

    def metricas(df):
        if df.empty: raise ValueError("No puntuar población vacía")
        y,p = df.observado.to_numpy(float),df.predicho.to_numpy(float)
        if not np.isfinite(y).all() or not np.isfinite(p).all(): raise ValueError("Errores no finitos")
        e = y-p; sse = float(e@e); sst = float((y-y.mean())@(y-y.mean()))
        return {"n_oof":len(df),"n_parcelas":df.ID_POLIGONO.nunique(),"RMSE":float(np.sqrt(sse/len(df))),
                "MAE":float(np.mean(abs(e))),"R2":1-sse/sst if sst>1e-14*max(1,float(y@y)) else np.nan}

    def contrastar(tabla,key,keys):
        control = csv_insumo(key)
        a,b = tabla.set_index(keys).sort_index(),control.set_index(keys).sort_index()
        assert a.index.equals(b.index)
        cols = a.select_dtypes(include="number").columns
        np.testing.assert_allclose(a[cols],b[cols],atol=1e-12,rtol=0,equal_nan=True)
        for c in a.columns.difference(cols):
            # CSV representa la lista vacía de IDs como campo vacío/NaN.
            vacio = "" if c == "IDs_excluidos" else "<NA>"
            np.testing.assert_array_equal(a[c].fillna(vacio),b[c].fillna(vacio))

    met = pd.DataFrame([{"escenario":s,"modelo":m,**metricas(g)} for s,d in ESCENARIOS.items() for m,g in d.groupby("modelo")])
    reps = pd.DataFrame([{"escenario":s,"modelo":m,"repeticion":r,**metricas(g)} for s,d in ESCENARIOS.items() for (m,r),g in d.groupby(["modelo","repeticion"])])
    contrastar(met,"metricas_control",["escenario","modelo"])
    contrastar(reps,"repeticiones_control",["escenario","modelo","repeticion"])
    principal = met.loc[met.escenario.eq("SEEN135")].set_index("modelo").reindex(MODELOS)
    display(principal[["n_parcelas","n_oof","RMSE","MAE","R2"]])
    fig,axes = plt.subplots(1,2,figsize=(10,3.4))
    for ax,c in zip(axes,["RMSE","MAE"]):
        ax.bar(MODELOS,principal[c],color=["#9aa5b3","#75849b","#7cbbb2","#287d77"])
        ax.set(ylabel=c+" (t/ha)",title="SEEN135: menor es mejor")
    fig.tight_layout(); plt.show()
    """, "metricas-visibles")
    texto("""
    ## 9. Dos preguntas de decisión, no solo una tabla ganadora

    **Aporte H7:** C1 reduce RMSE frente a C0 agrupado y en ≥8/10 repeticiones.
    **Competitividad prospectiva:** RMSE<MIX y MAE≤MIX agrupados, ambas condiciones
    en ≥8/10 repeticiones. Se conserva también el criterio histórico MAE≤MUN,
    sin recalificar cierres anteriores. La política frente a MIX se comunicó y
    quedó registrada antes de ajustar esta ronda; no es la fórmula oficial de FIRA.

    Un C0 competitivo no confirma H7 si S no aporta. Cumplir una regla de desarrollo
    no demuestra significación, robustez causal o extrapolación a otros años.
    """)
    codigo("""
    reglas_rows = []
    for escenario,d in ESCENARIOS.items():
        g = pd.DataFrame({m:metricas(q) for m,q in d.groupby("modelo")}).T
        r = reps.loc[reps.escenario.eq(escenario)].pivot(index="repeticion",columns="modelo",values="RMSE")
        a = reps.loc[reps.escenario.eq(escenario)].pivot(index="repeticion",columns="modelo",values="MAE")
        incremental = int((r.C1<r.C0).sum())
        for m in ["C0","C1"]:
            nr,nmix,nmun = int((r[m]<r.MIX).sum()),int((a[m]<=a.MIX).sum()),int((a[m]<=a.MUN).sum())
            rm = g.loc[m,"RMSE"]<g.loc["MIX","RMSE"] and nr>=8
            reglas_rows.append({"escenario":escenario,"modelo":m,"n_RMSE_mejor_MIX":nr,"n_MAE_no_peor_MIX":nmix,"n_MAE_no_peor_MUN":nmun,
                               "competitivo_propuesto":bool(rm and g.loc[m,"MAE"]<=g.loc["MIX","MAE"] and nmix>=8),
                               "cumple_criterio_historico":bool(rm and g.loc[m,"MAE"]<=g.loc["MUN","MAE"] and nmun>=8),
                               "n_RMSE_C1_mejor_C0":incremental,"aporte_H7":bool(m=="C1" and incremental>=8 and g.loc["C1","RMSE"]<g.loc["C0","RMSE"])})
    reglas = pd.DataFrame(reglas_rows)
    contrastar(reglas,"reglas_control",["escenario","modelo"])
    display(reglas.loc[reglas.escenario.eq("SEEN135")])
    print("ΔRMSE C1−C0:",float(principal.loc["C1","RMSE"]-principal.loc["C0","RMSE"]),"t/ha")
    print("ΔMAE C1−C0:",float(principal.loc["C1","MAE"]-principal.loc["C0","MAE"]),"t/ha")
    """, "reglas-visibles")
    texto("""
    ## 10. Dónde cambia el error y cuán concentrada está la mejora

    Chignahuapan y resto se puntúan aparte, sin confundir un promedio general
    favorable con solución del error interno. Ganancia SSE positiva significa menor
    error cuadrático del candidato. Sumar los diez errores por parcela conserva la
    unidad de análisis. Quitamos las dos/cinco parcelas favorables **solo del
    puntaje de sensibilidad**, nunca del entrenamiento ni para elegir otra receta.
    Fracción positiva bruta no es fracción de ganancia neta.
    """)
    codigo("""
    zonas = pd.DataFrame([{"escenario":s,"modelo":m,"zona":z,**metricas(q.loc[mask])}
                         for s,d in ESCENARIOS.items() for m,q in d.groupby("modelo")
                         for z,mask in [("Chignahuapan",q.Municipio.eq("Chignahuapan")),("Resto",q.Municipio.ne("Chignahuapan"))]])
    municipios = pd.DataFrame([{"escenario":s,"modelo":m,"Municipio":mun,**metricas(q)}
                              for s,d in ESCENARIOS.items() for (m,mun),q in d.groupby(["modelo","Municipio"])])
    contrastar(zonas,"zonas_control",["escenario","modelo","zona"])
    contrastar(municipios,"municipios_control",["escenario","modelo","Municipio"])
    deltas_rows,conc_rows = [],[]
    for escenario,d in ESCENARIOS.items():
        for candidato,control in [("C1","C0"),("C1","MIX"),("C0","MIX")]:
            a,b = [d.loc[d.modelo.eq(m)].sort_values(claves).reset_index(drop=True) for m in [candidato,control]]
            assert a[claves].equals(b[claves])
            delta = a[claves+["Municipio"]].copy()
            delta["ganancia_SSE"] = (b.observado-b.predicho)**2-(a.observado-a.predicho)**2
            dg = delta.groupby(["ID_POLIGONO","Municipio"],sort=True).ganancia_SSE.sum().reset_index().sort_values(["ganancia_SSE","ID_POLIGONO"],ascending=[False,True])
            positivo = float(dg.ganancia_SSE.clip(lower=0).sum())
            deltas_rows.extend({"escenario":escenario,"candidato":candidato,"control":control,**row} for row in dg.to_dict("records"))
            for k in [0,2,5]:
                excluidos = dg.loc[dg.ganancia_SSE.gt(0),"ID_POLIGONO"].head(k).tolist()
                mask = ~a.ID_POLIGONO.isin(excluidos)
                share = float(dg.loc[dg.ID_POLIGONO.isin(excluidos),"ganancia_SSE"].sum())/positivo if positivo else np.nan
                conc_rows.append({"escenario":escenario,"candidato":candidato,"control":control,"top_k_solicitado":k,
                                  "n_parcelas_excluidas_solo_evaluacion":len(excluidos),"IDs_excluidos":"|".join(excluidos),
                                  "ganancia_SSE_neta_total":float(dg.ganancia_SSE.sum()),"fraccion_ganancia_positiva_top_k":share,
                                  "n_parcelas_mejoran":int(dg.ganancia_SSE.gt(0).sum()),"n_parcelas_empeoran":int(dg.ganancia_SSE.lt(0).sum()),
                                  "RMSE_candidato":metricas(a[mask])["RMSE"],"RMSE_control":metricas(b[mask])["RMSE"],
                                  "MAE_candidato":metricas(a[mask])["MAE"],"MAE_control":metricas(b[mask])["MAE"]})
    deltas,concentracion = pd.DataFrame(deltas_rows),pd.DataFrame(conc_rows)
    contrastar(deltas,"contrastes_control",["escenario","candidato","control","ID_POLIGONO","Municipio"])
    contrastar(concentracion,"concentracion_control",["escenario","candidato","control","top_k_solicitado"])
    display(zonas.loc[zonas.escenario.eq("SEEN135"),["modelo","zona","n_parcelas","RMSE","MAE"]])
    display(concentracion.loc[concentracion.escenario.eq("SEEN135")&concentracion.candidato.eq("C1")&concentracion.control.eq("C0")])
    display(met.loc[met.escenario.eq("FULL138"),["modelo","RMSE","MAE","R2"]])
    """, "concentracion-visible")
    texto("""
    ## 11. Cierre y límites

    **Cierre sin adopción:** en SEEN135, RMSE C0 **0.494064** y C1 **0.494105**
    t/ha, frente a MIX **0.487197**. C1 mejora C0 en solo **4/10 repeticiones**;
    no cumple aporte H7 ni competitividad. MAE baja ligeramente **0.321996 →
    0.321769**, todavía por encima de MUN **0.321274**. No llamamos esa pequeña
    reducción de MAE una mejora global ni buscamos otra receta para rescatarla.

    El resultado de abajo proviene de las comparaciones declaradas, no de una
    búsqueda añadida por este lector. Se distingue aporte de S, competitividad
    del procedimiento completo y eventual adopción. La adopción final no ocurre
    automáticamente: requiere comprobar estabilidad, soporte e inferencia.

    - Una sola campaña etiquetada y reutilización adaptativa de las mismas etiquetas.
    - La anidación protege la selección interior; no borra la adaptación entre rondas.
    - Sin píxeles/máscara ni metadatos de procesamiento no se identifica la causa
      agronómica de S. No se anuncian diagnósticos de enfermedades o manejo.
    - Un resultado negativo vale para esta media espacial, ventana y corrección
      lineal, no para toda heterogeneidad o toda familia de modelos.
    - El lector verifica hashes, variables, selector, aplicación de parámetros y
      métricas conservadas. La corrida y réplica reales se ejecutan con el script
      registrado; esta lectura no sustituye esos controles de entrenamiento.

    **Después:** discutir la decisión y congelar la receta de entrega. No se
    ejecuta automáticamente otra ventana, índice, árbol o filtro para rescatar H7.
    """)
    codigo("""
    regla_seen = reglas.loc[reglas.escenario.eq("SEEN135")].set_index("modelo")
    aporte = bool(regla_seen.loc["C1","aporte_H7"])
    competitivos = regla_seen.index[regla_seen.competitivo_propuesto].tolist()
    print("Aporte incremental H7 según regla:",aporte)
    print("Procedimientos competitivos según regla prospectiva:",competitivos)
    print("Ningún procedimiento se adopta ni se generan las 59 predicciones por ejecutar esta lectura.")
    resumen = {"id":"EXP_07","modo":"lector_resultados_experimento_registrado_sin_ajustes","parcelas":197,"etiquetas":138,
               "capturas_incorporadas":26255,"capturas_pareadas":18248,"variables_recalculadas":2,
               "mascaras_pareadas_identicas":True,"factibilidad_apta":True,"entrenamientos_X_verificados":250,
               "procedimientos":4,"candidatos":1,"controles_modelo":1,"oof_total":5520,"oof_por_procedimiento":1380,
               "poblacion":"SEEN135","oof_seen_por_procedimiento":1350,"poblacion_secundaria":"FULL138",
               "decisiones_verificadas":100,"scores_guardados_verificados":600,"sse_interiores_verificadas":2400,
               "ecuaciones_oof_reproducidas":1,"ajustes_actuales":0,"predicciones_finales_generadas":0,
               "oof_regeneradas":False,"errores_interiores_regenerados":False,"scores_desde_sse_recalculados":600,"metricas_recalculadas":True,
               "aporte_H7_regla":aporte,"competitivos_prospectivos":competitivos,"variantes_adoptadas":[],
               "metricas_seen":principal[["RMSE","MAE","R2"]].to_dict(orient="index"),
               "fecha_ejecucion_utc":datetime.now(timezone.utc).isoformat()}
    print("RESUMEN_EXP_07_JSON="+json.dumps(resumen,ensure_ascii=False,sort_keys=True,allow_nan=False))
    """, "cierre")
    texto("""
    ## Referencias y glosario para profundizar

    Equipo AgroCebada. (2026). *Diccionario de índices satelitales* [Documento
    suministrado con el reto]. Define std como variabilidad espacial dentro de
    parcela por observación; no especifica máscara, conteo de píxeles o ddof.

    Equipo AgroCebada. (2026, 8 de octubre). *EXP_07: heterogeneidad espacial
    NDVI Planet* [Protocolo y registro interno]. Receta, código y evidencia están
    incorporados al cuaderno; no hace falta consultar archivos de otra máquina.

    Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection
    and subsequent selection bias in performance evaluation. *Journal of Machine
    Learning Research, 11*, 2079–2107. https://jmlr.org/papers/v11/cawley10a.html

    scikit-learn developers. (s. f.). *Ridge*.
    https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html

    **Glosario:** soporte pareado = las mismas capturas para dos estadísticas;
    heterogeneidad espacial = diferencias dentro de una parcela en una observación;
    imputación = regla de reemplazo aprendida en entrenamiento; efecto municipal =
    nivel territorial no penalizado; OOF = predicción fuera de muestra; SSE = suma
    de errores cuadrados; baseline = corrección cero; SEEN135 = municipio presente
    en entrenamiento; sensibilidad = cambiar solo la población evaluada, sin reajuste.
    """)
    for i, c in enumerate(cells):
        c.id = f"exp07-{i:03d}"
    metadata_nb = copy.deepcopy(anterior.metadata)
    metadata_nb["agrocebada"] = {
        "id": "EXP_07", "modo": "lector_resultados_experimento_registrado_sin_ajustes",
        "fecha_original": "2026-10-08", "fecha_adaptacion": "2026-10-08", "crisp_dm": [2,3,4,5],
        "ajustes_actuales": 0, "colab_real_probado": False,
        "dependencias_requeridas": anterior.metadata.agrocebada.dependencias_requeridas,
        "perfil_sha256": anterior.metadata.agrocebada.perfil_sha256,
        "soporte_sha256": anterior.metadata.agrocebada.soporte_sha256,
        "base_sha256": BASE_SHA, "configuracion_sha256": hashlib.sha256((raiz / CONFIG).read_bytes()).hexdigest(),
        "insumos": {k: {a: b for a, b in v.items() if a != "bytes_zlib_base64"} for k, v in registros.items()},
    }
    nb = nbformat.v4.new_notebook(cells=cells, metadata=metadata_nb)
    nbformat.validate(nb)
    return nb


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=raiz / "notebooks/experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb")
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("Elige una salida nueva; no sobrescribir el cuaderno revisado")
    nb = construir(raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, args.salida)
    print(f"{args.salida}: {len(nb.cells)} celdas; cero ajustes")


if __name__ == "__main__":
    main()
