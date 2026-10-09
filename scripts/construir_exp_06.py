"""EXP06: pico NDVI soportado, lector histórico con extracción visible y cero ajustes."""
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

BASE_SHA256 = "f99e113361c5546929eadb9c43abf92ecc1944592fc2fb84860d9c7b469ba6f2"


def huella(contenido):
    return hashlib.sha256(contenido).hexdigest()


def cargar_insumos(raiz):
    cfg = json.loads((Path(raiz)/"config/exp_06_pico_soportado.json").read_text())
    salida = {}
    for k,c in cfg["insumos"].items():
        b = (Path(raiz)/c["ruta_local"]).read_bytes()
        if len(b) != c["bytes"] or huella(b) != c["sha256"] or not 0 < len(b) <= 2*1024*1024:
            raise ValueError(f"Insumo distinto o fuera del límite: {k}")
        salida[k] = {**c,"contenido":b}
    return salida


def construir(raiz=None):
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    cfg_rel = "config/exp_06_pico_soportado.json"
    cfg = json.loads((raiz/cfg_rel).read_text())
    base_rel = "notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb"
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
    # EXP_06. ¿Una fecha de pico NDVI mejor soportada mejora la predicción?

    **CRISP-DM: preparar, modelar y evaluar.** Un máximo aislado puede depender del
    muestreo. Hipótesis acotada: sustituir **solo la fecha del máximo crudo** de NDVI
    Planet por la fecha del máximo suavizado, con guardas explícitas de soporte.
    No añadimos variables ni cambiamos municipio, Ridge, ventana o particiones.

    **Lector retrospectivo sin ajustes:** reconstruye la curva y la fecha de 197
    parcelas desde capturas; verifica 100 elecciones de alpha a partir de 500 scores
    guardados; puntúa 6,900 OOF guardadas. No ajusta modelos ni recalcula errores
    interiores ni genera los 59 rendimientos ocultos.

    Factibilidad original: **2/oct/2026**, solo X. Experimento original: **6/oct**;
    adaptación de lectura: **8/oct**. No se vuelven a declarar decisiones como si
    fueran nuevas. El registro previo es interno; no elimina la exploración adaptativa.

    **Recorrido:** capturas → curva diaria → guardas → una columna → comparación → decisión.
    Basta este `.ipynb`, sin Git, Drive, ZIP ni otro cuaderno. Dos bloques técnicos
    plegados; cálculos científicos visibles. La prueba local no es prueba real en Colab.
    """)
    texto("""
    ## 1. Preparación y trazabilidad

    | Entrada incorporada | Qué hacemos aquí | Qué no hacemos |
    | --- | --- | --- |
    | 26,255 capturas, cinco columnas Planet, abril–octubre de 2025 | Media diaria, mediana móvil y fecha soportada | Extraer píxeles ni leer otros sensores |
    | Seis variables E2 y 138 etiquetas separadas | Sustituir solo una columna | Rehacer las otras cinco variables |
    | Roles, 500 scores y 6,900 OOF originales | Verificar selector y recalcular métricas | Reentrenar ni reconstruir scores interiores |
    | Controles de salida | Contrastar después del cálculo | Usarlos para construir la variable |

    El recorte de capturas se creó el **8/oct** desde el CSV Planet original,
    previamente comprobado byte a byte contra DataSet.zip. No es un archivo sellado
    el 2/oct: conserva procedencia y hash propio. Los otros insumos mantienen bytes
    históricos. SHA-256 detecta cambios, no certifica por sí solo una fecha.
    No se filtran nubes ni duplicados; no se rellena NDVI ausente.
    """)
    for tag in ("soporte-colab","preparar-colab","entorno"):
        reutilizar(tag)
    decoder = tags["insumos-tecnicos"].source
    decoder = decoder[decoder.index("def bytes_insumo"):]
    codigo("INSUMOS_INCRUSTADOS = "+repr(registros)+"\n\n"+decoder,
           "insumos-tecnicos","Insumos con tamaño y SHA-256; sin motores predictivos ocultos")
    codigo("""
    PRE = json.loads(bytes_insumo("registro_previo","registro_historico"))
    REG = json.loads(bytes_insumo("registro_ejecucion","registro_historico"))
    FACT = json.loads(bytes_insumo("registro_factibilidad","registro_historico"))
    RECETA = json.loads(bytes_insumo("receta","receta_historica"))
    MAN = json.loads(bytes_insumo("manifiesto","registro_historico"))
    assert REG["registro_sha256"] == hashlib.sha256(bytes_insumo("registro_previo","registro_historico")).hexdigest()
    for k in ["variables_fuente","etiquetas","externas","internas","e2_oof","e2_alpha","referencias","receta","manifiesto","protocolo","descriptores_control"]:
        origen = INSUMOS_INCRUSTADOS[k]["origen"].split("::")[-1]
        assert INSUMOS_INCRUSTADOS[k]["sha256"] == PRE["archivos_sellados"][origen]
    fuente = leer_csv("variables_fuente","variables_e2_guardadas")
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
    grupos = fuente.set_index("ID_POLIGONO").sort_index()
    print("Factibilidad UTC:",FACT.get("ejecutado_utc",FACT.get("inicio_utc")))
    print("Registro previo UTC:",PRE["registrado_utc"])
    print("Corrida UTC:",REG["inicio_utc"],"→",REG["fin_utc"])
    print("Python histórico:",REG["entorno"]["python"],"| lectura actual: Python 3.13")
    display(fuente.groupby(["Municipio","CONJUNTO"]).size().rename("parcelas").to_frame())
    ""","insumos-visibles")
    texto("""
    ## 2. De capturas a una observación diaria

    Una fila satelital no es una etiqueta adicional. Si varias capturas comparten
    parcela y fecha, se promedian sus NDVI **finitos**; las ausencias y QA quedan
    contadas. Un valor fuera de [−1,1] no se recorta ni descarta: invalida el pico
    de esa parcela. Las fechas son calendáricas, sin hora; se leen como dd/mm/aaaa.
    La política no cambia por observar rendimientos o errores.
    """)
    codigo("""
    capturas = leer_csv("capturas","capturas_derivadas")
    assert set(capturas) == set(RECETA["columnas_lectura"])
    assert len(capturas) == 26255 and capturas.ID_POLIGONO.nunique() == 197
    assert set(capturas.sensor) == {"Planet"}
    assert capturas.ID_POLIGONO.str.fullmatch(r"AGC_\\d{3}").all()
    capturas["fecha"] = pd.to_datetime(capturas.fecha_captura,format="%d/%m/%Y",errors="raise")
    assert capturas.fecha.between(RECETA["ventana"]["inicio"],RECETA["ventana"]["fin"]).all()
    capturas["duplicada_exacta"] = capturas.duplicated(RECETA["columnas_lectura"],keep=False)
    display(capturas.loc[capturas.ID_POLIGONO.eq("AGC_001"),RECETA["columnas_lectura"]].head(8))
    print("26,255 capturas del ciclo: no se filtra nubosidad ni se imputan filas.")
    ""","capturas-visibles")
    codigo("""
    def agregar_diario(raw):
        raw = raw.copy()
        req = ["ID_POLIGONO","fecha_captura","sensor","ndvi_promedio","porcentaje_nubosidad"]
        if raw.empty or not set(req) <= set(raw) or raw.ID_POLIGONO.isna().any() or not raw.ID_POLIGONO.astype(str).str.fullmatch(r"AGC_\\d{3}").all():
            raise ValueError("Capturas/IDs inválidos")
        if set(raw.sensor) != {"Planet"}:
            raise ValueError("No mezclar sensores")
        raw["fecha"] = pd.to_datetime(raw.fecha_captura,format="%d/%m/%Y",errors="raise")
        raw["duplicada_exacta"] = raw.duplicated(req,keep=False)
        for col in ["ndvi_promedio","porcentaje_nubosidad"]:
            raw[col] = pd.to_numeric(raw[col],errors="raise")
        rows = []
        for (pid,fecha),g in raw.groupby(["ID_POLIGONO","fecha"],sort=True):
            vals = g.ndvi_promedio.to_numpy(float); finite = vals[np.isfinite(vals)]
            qa = g.porcentaje_nubosidad.to_numpy(float); qafin = qa[np.isfinite(qa)]
            rows.append({"ID_POLIGONO":pid,"fecha":fecha,"doy":fecha.dayofyear,
                         "ndvi_diario":float(np.mean(finite)) if len(finite) else np.nan,
                         "ndvi_min_del_dia":float(np.min(finite)) if len(finite) else np.nan,
                         "ndvi_max_del_dia":float(np.max(finite)) if len(finite) else np.nan,
                         "n_filas":len(g),"n_indice_finito":len(finite),
                         "n_fuera_rango":int(((finite < -1)|(finite > 1)).sum()),
                         "n_qa_desconocida":int((~np.isfinite(qa)).sum()),
                         "n_qa_100":int((qa == 100).sum()),"n_qa_gt20":int((qa > 20).sum()),
                         "qa_min":float(qafin.min()) if len(qafin) else np.nan,
                         "qa_max":float(qafin.max()) if len(qafin) else np.nan,
                         "n_filas_duplicadas_exactas":int(g.duplicada_exacta.sum())})
        return pd.DataFrame(rows)

    diarios = agregar_diario(capturas)
    assert len(diarios) == 26255 and not diarios.duplicated(["ID_POLIGONO","fecha"]).any()
    assert np.isfinite(diarios.ndvi_diario).sum() == 18248
    display(diarios.loc[diarios.ID_POLIGONO.eq("AGC_001")].head(8))
    print("Diario conserva",int(diarios.n_filas.sum()),"filas fuente;",int(diarios.n_fuera_rango.sum()),"NDVI fuera de rango.")
    ""","diarios-visibles")
    texto("""
    ## 3. Definición de pico y guardas, antes de mirar y

    Mediana centrada en **±7 días calendáricos**, solo en fechas observadas y con
    al menos tres días finitos. No son siete filas ni una interpolación a diario.
    Si máximos empatados abarcan ≤14 días, fecha = centro de primera y última
    fecha (permite .5); si abarcan más, se declara ambigua.

    | Guarda operativa original | Requisito para liberar la fecha |
    | --- | --- |
    | Observaciones | ≥20 días finitos; ningún NDVI fuera de [−1,1] |
    | Cobertura temporal | Huecos ≤21 días; extremos de ventana sin soporte ≤14 días |
    | Curva | ≥3 medianas finitas; máximo menos q10 diario ≥0.10 |
    | Pico | A ≥14 días de bordes de ventana y serie; meseta ≤14 días |
    | Soporte bilateral | ≥2 días antes y después de la meseta, dentro de ±21 días del centro |

    Si una falla, **NaN y motivo explícito**, nunca cero. Son guardas del equipo,
    no umbrales agronómicos validados por USGS ni fechas de espigamiento/cosecha.
    La anchura del lóbulo se exploró como otro descriptor, pero **no entra a V4**;
    aquí no se reconstruye. Una anchura ausente no invalida automáticamente el pico.
    """)
    codigo("""
    def mediana_movil(t,x,radio,minimo):
        t,x = np.asarray(t,float),np.asarray(x,float)
        if t.ndim != 1 or x.shape != t.shape or not np.isfinite(t).all() or not np.isfinite(x).all() or (np.diff(t) <= 0).any() or radio < 0 or minimo < 1:
            raise ValueError("Mediana requiere días únicos ordenados y valores finitos")
        return np.array([np.median(x[np.abs(t-ti) <= radio])
                         if np.sum(np.abs(t-ti) <= radio) >= minimo else np.nan for ti in t])

    def pico_soportado(g,receta):
        if g.empty or g.ID_POLIGONO.nunique() != 1 or g.fecha.duplicated().any():
            raise ValueError("Se requiere una parcela con fechas únicas")
        c,q = receta["curva"],receta["politica_calidad"]
        finite = g.loc[np.isfinite(g.ndvi_diario)].sort_values("fecha").copy()
        t,x = finite.doy.to_numpy(float),finite.ndvi_diario.to_numpy(float)
        start = pd.Timestamp(receta["ventana"]["inicio"]).dayofyear
        end = pd.Timestamp(receta["ventana"]["fin"]).dayofyear
        if len(t) and (t.min() < start or t.max() > end):
            raise ValueError("Observaciones fuera de ventana")
        flags = []
        row = {"ID_POLIGONO":g.ID_POLIGONO.iloc[0],"n_dias_observados":len(g),"n_dias_finitos":len(t),
               "n_filas":int(g.n_filas.sum()),"n_dias_con_varias_filas":int(g.n_filas.gt(1).sum()),
               "n_indice_ausente_o_no_finito":int((g.n_filas-g.n_indice_finito).sum()),
               "n_ndvi_fuera_rango":int(g.n_fuera_rango.sum()),"n_qa_desconocida":int(g.n_qa_desconocida.sum()),
               "n_qa_gt20":int(g.n_qa_gt20.sum()),"n_qa_100":int(g.n_qa_100.sum()),
               "n_filas_duplicadas_exactas":int(g.n_filas_duplicadas_exactas.sum()),
               "pico_soportado_doy":np.nan,"pico_observado_suavizado_doy":np.nan,
               "pico_meseta_inicio_doy":np.nan,"pico_meseta_fin_doy":np.nan,
               "baseline_q10":np.nan,"amplitud":np.nan,"n_dias_suavizados":0,
               "hueco_maximo_dias":float(np.diff(t).max()) if len(t)>1 else np.nan,
               "sin_soporte_inicio_dias":float(t[0]-start) if len(t) else np.nan,
               "sin_soporte_fin_dias":float(end-t[-1]) if len(t) else np.nan}
        if len(t) < q["minimo_dias_finitos"]: flags.append("pocos_dias")
        if g.n_fuera_rango.sum(): flags.append("ndvi_fuera_rango")
        if len(t)>1 and np.diff(t).max() > q["hueco_maximo_global_dias"]: flags.append("hueco_global")
        if len(t) and max(t[0]-start,end-t[-1]) > q["soporte_bordes_maximo_dias"]: flags.append("ventana_incompleta")
        smooth = mediana_movil(t,x,c["semiventana_dias"],c["minimo_dias_en_ventana"])
        curve = finite.assign(ndvi_suavizado=smooth)
        ts,xs = t[np.isfinite(smooth)],smooth[np.isfinite(smooth)]
        row["n_dias_suavizados"] = len(ts)
        if len(ts) < 3:
            flags.append("sin_curva_suavizada")
        else:
            base = float(np.quantile(x,.1,method="linear")); amp = float(xs.max()-base)
            peaks = np.flatnonzero(np.abs(xs-xs.max()) <= c["meseta_empate_tolerancia"])
            peak = float((ts[peaks[0]]+ts[peaks[-1]])/2)
            row.update(baseline_q10=base,amplitud=amp,pico_observado_suavizado_doy=peak,
                       pico_meseta_inicio_doy=float(ts[peaks[0]]),pico_meseta_fin_doy=float(ts[peaks[-1]]))
            if amp < c["amplitud_minima_ndvi"]: flags.append("amplitud_baja")
            if ts[peaks[-1]]-ts[peaks[0]] > c["meseta_maxima_dias"]: flags.append("pico_ambiguo")
            if min(peak-start,end-peak,peak-t[0],t[-1]-peak) < q["soporte_bordes_maximo_dias"]: flags.append("pico_censurado")
            radius = c["radio_soporte_pico_dias"]
            nleft = int(((t<ts[peaks[0]])&(t>=peak-radius)).sum())
            nright = int(((t>ts[peaks[-1]])&(t<=peak+radius)).sum())
            row.update(n_soporte_izq=nleft,n_soporte_der=nright)
            if min(nleft,nright) < c["minimo_dias_soporte_por_lado"]: flags.append("pico_sin_soporte_bilateral")
            if not flags: row["pico_soportado_doy"] = peak
        row["estado_pico"] = "ok" if not flags else "|".join(flags)
        return row,curve

    resultados = [pico_soportado(g,RECETA) for _,g in diarios.groupby("ID_POLIGONO",sort=True)]
    descriptores = pd.DataFrame([a for a,b in resultados]).set_index("ID_POLIGONO").sort_index()
    curvas = pd.concat([b for a,b in resultados],ignore_index=True)
    # Controles abiertos después de reconstruir: nunca alimentan la receta.
    control_d = leer_csv("descriptores_control","control_posterior").set_index("ID_POLIGONO").sort_index()
    assert descriptores.index.equals(control_d.index)
    nums = descriptores.select_dtypes(include="number").columns
    np.testing.assert_allclose(descriptores[nums],control_d[nums],atol=1e-12,rtol=0,equal_nan=True)
    np.testing.assert_array_equal(descriptores.estado_pico,control_d.estado_pico)
    control_c = leer_csv("curvas_control","control_posterior")
    control_c["fecha"] = pd.to_datetime(control_c.fecha,format="%Y-%m-%d",errors="raise")
    a,b = curvas.set_index(["ID_POLIGONO","fecha"]).sort_index(),control_c.set_index(["ID_POLIGONO","fecha"]).sort_index()
    assert a.index.equals(b.index) and len(a) == 18248
    np.testing.assert_allclose(a,b[a.columns],atol=1e-12,rtol=0,equal_nan=True)
    assert descriptores.pico_soportado_doy.notna().sum() == 158
    assert descriptores.pico_soportado_doy.isna().sum() == 39
    display(descriptores.estado_pico.value_counts().rename("parcelas").to_frame())
    print("197 picos/diagnósticos y 18,248 puntos de curva contrastados; anchura no reconstruida.")
    ""","pico-visible")
    texto("""
    **AGC_001:** comparar el máximo crudo con el centro de la meseta suavizada.
    El segundo ejemplo es el primer ID ordenado con guarda fallida, seleccionado
    por disponibilidad de X, no por rendimiento/error. Una curva bonita no prueba
    que la fecha sea una etapa biológica ni que mejore las predicciones.
    """)
    codigo("""
    NUM = ["C_PL_ndvi_media","C_PL_ndvi_pico_prom","C_PL_ndvi_doy_pico_prom",
           "C_S2_ndvi_media","C_S2_ndwi_media","C_LS_vi6t_media"]
    PEAK = NUM[2]
    fallo = descriptores.index[descriptores.estado_pico.ne("ok")][0]
    fig,axes = plt.subplots(1,2,figsize=(11,3.8))
    for ax,pid in zip(axes,["AGC_001",fallo]):
        d = diarios.loc[diarios.ID_POLIGONO.eq(pid)]
        c = curvas.loc[curvas.ID_POLIGONO.eq(pid)]
        ax.scatter(d.doy,d.ndvi_diario,s=12,color="#9aa5b3",label="NDVI diario finito")
        ax.plot(c.doy,c.ndvi_suavizado,color="#287d77",label="Mediana ±7 días")
        ax.axvline(grupos.loc[pid,PEAK],color="#b64834",ls=":",label="Fecha cruda E2")
        pico = descriptores.loc[pid,"pico_soportado_doy"]
        if pd.notna(pico): ax.axvline(pico,color="#287d77",ls="--",label="Fecha soportada")
        ax.set(xlabel="Día del año 2025",ylabel="NDVI",title=pid+" · "+descriptores.loc[pid,"estado_pico"])
        ax.legend(fontsize=8)
    fig.tight_layout(); plt.show()
    display(pd.concat([grupos.loc[["AGC_001",fallo],[PEAK]],descriptores.loc[["AGC_001",fallo],
            ["pico_soportado_doy","pico_meseta_inicio_doy","pico_meseta_fin_doy","estado_pico"]]],axis=1))
    ""","ejemplo-visible")
    texto("""
    ## 4. Una sustitución, no otra familia de modelo

    | Se conserva | Se cambia |
    | --- | --- |
    | Municipio, seis columnas numéricas y su orden | Contenido de la tercera columna: fecha de pico Planet |
    | NDVI medio/máximo Planet, NDVI/NDWI medios Sentinel y vi6t medio Landsat | Fecha suavizada o NaN bajo receta fija |
    | One-hot municipal + Ridge y alpha de cinco valores | No se agrega `estado_pico`, QA ni anchura |

    La reconstrucción actual usa solo X. **39 NaN no eliminan parcelas**: en el
    experimento original se imputaron mediante mediana dentro de cada entrenamiento.
    Municipio one-hot **también fue penalizado** por Ridge: E2/V4 no usan las medias
    municipales no penalizadas de las rondas de lluvia. Municipio desconocido =
    one-hot en cero, no necesariamente predicción de media global.
    """)
    codigo("""
    base = fuente[["ID_POLIGONO","Municipio","Estado"]+NUM].copy()
    alternativa = base.copy()
    alternativa[PEAK] = alternativa.ID_POLIGONO.map(descriptores.pico_soportado_doy)
    pd.testing.assert_frame_equal(base.drop(columns=PEAK),alternativa.drop(columns=PEAK),check_exact=True)
    assert list(alternativa) == list(base) and "estado_pico" not in alternativa
    assert alternativa[PEAK].isna().sum() == 39
    conocido = alternativa.ID_POLIGONO.isin(etiquetas.ID_POLIGONO)
    assert alternativa.loc[conocido,PEAK].notna().sum() == 108
    assert alternativa.loc[~conocido,PEAK].notna().sum() == 50
    finitos = alternativa[PEAK].notna()
    iguales = np.isclose(alternativa.loc[finitos,PEAK],base.loc[finitos,PEAK],atol=1e-12,rtol=0)
    assert int(iguales.sum()) == 8
    display(pd.DataFrame({"columna":NUM,"unidad":["NDVI","NDVI","día del año","NDVI","NDWI","vi6t"],
                          "operacion":["conservar","conservar","sustituir","conservar","conservar","conservar"]}))
    print("158 fechas disponibles: 150 cambian y 8 coinciden; 39 NaN se conservan, sin bandera predictora.")
    ""","variables-visibles")
    texto("""
    **Cómo se manejó cada pliegue original:** mediana numérica aprendida en
    entrenamiento → imputación → StandardScaler (media y desviación de entrenamiento)
    → concatenar one-hot municipal sin escalar → Ridge con intercepto. En cada
    pliegue interior se volvió a aprender todo sin sus filas de validación.
    Si una columna carece de valores finitos en entrenamiento, se detiene; no se
    borra la columna. El ejemplo siguiente es inventado y solo ilustra la regla.
    """)
    codigo("""
    x_train = np.array([100.,120.,np.nan,140.])
    x_validacion = np.array([np.nan,200.])
    mediana_train = np.nanmedian(x_train)
    train_imputado = np.where(np.isnan(x_train),mediana_train,x_train)
    validacion_imputada = np.where(np.isnan(x_validacion),mediana_train,x_validacion)
    media_train,escala_train = train_imputado.mean(),train_imputado.std(ddof=0)
    display(pd.DataFrame({"original_validacion":x_validacion,"imputado":validacion_imputada,
                          "estandarizado":(validacion_imputada-media_train)/escala_train}))
    print("Ejemplo sintético: mediana",mediana_train,"; la validación no modifica mediana ni escala.")
    ""","preprocesamiento-visible")
    texto("""
    ## 5. Particiones y selector sin cambiarlos por los resultados

    Cinco pliegues × diez repeticiones; cuatro interiores por entrenamiento
    exterior. Siempre parcela, nunca captura. Los CSV fijan exactamente quién
    entrenó/validó, sin regenerar semillas. La disponibilidad se comprueba solo con X.
    """)
    reutilizar("particiones-visibles")
    codigo("""
    alt = alternativa.set_index("ID_POLIGONO")
    soportes = []
    for _,roles in internas.groupby(["repeticion","pliegue","pliegue_interno"]):
        q = alt.loc[roles.loc[roles.rol.eq("entrenamiento"),"ID_POLIGONO"],NUM]
        if np.isinf(q.to_numpy(float)).any() or not np.isfinite(q.to_numpy(float)).any(axis=0).all():
            raise ValueError("Una columna no permite imputación en entrenamiento")
        soportes.append(int(q[PEAK].notna().sum()))
    assert len(soportes) == 200 and min(soportes) == 59
    print("Los 200 entrenamientos interiores tenían al menos",min(soportes),"picos finitos; no hay columna vacía.")
    ""","disponibilidad-visible")
    texto("""
    Alpha ∈ {0.01, 0.1, 1, 10, 100}. Selector original: RMSE de los errores
    interiores concatenados, **sin restringir a municipio visto**. Empate ≤1e−12:
    alpha mayor. No incluye opción «baseline» ni pendiente cero como en lluvia.

    Presupuesto histórico por corrida: E2 control 1,000 ajustes interiores +50
    exteriores; V4 otros 1,000+50. Dos réplicas = **4,200 ajustes físicos**, no
    4,200 variantes. Único candidato nuevo: V4. Aquí: **cero ajustes**.
    Los scores guardados permiten verificar el selector, no recalcular sus errores:
    no se guardaron residuos interiores individuales.
    """)
    codigo("""
    GRID = [.01,.1,1.,10.,100.]
    SCORE_COLS = [f"rmse_interno_alpha_{a:g}" for a in GRID]
    def seleccionar_alpha_guardado(df):
        req = ["modelo","repeticion","pliegue","alpha"]+SCORE_COLS
        if df.empty or not set(req) <= set(df) or df.duplicated(req[:3]).any():
            raise ValueError("Selección vacía, incompleta o repetida")
        scores = df[SCORE_COLS].to_numpy(float)
        if not np.isfinite(scores).all() or (scores < 0).any():
            raise ValueError("Scores no finitos o negativos")
        filas = []
        for _,r in df.iterrows():
            vals = r[SCORE_COLS].to_numpy(float)
            elegido = max(a for a,v in zip(GRID,vals) if v <= vals.min()+1e-12)
            filas.append({"modelo":r.modelo,"repeticion":int(r.repeticion),"pliegue":int(r.pliegue),"alpha_elegido":elegido})
        return pd.DataFrame(filas)

    alphas = leer_csv("alphas","scores_guardados")
    decisiones = seleccionar_alpha_guardado(alphas)
    assert len(decisiones) == 100
    assert set(map(tuple,decisiones[["modelo","repeticion","pliegue"]].to_numpy())) == {(m,r,f) for m in ["E2","V4"] for r in range(10) for f in range(5)}
    np.testing.assert_array_equal(decisiones.alpha_elegido,alphas.alpha)
    old_a = leer_csv("e2_alpha","scores_guardados").query("modelo == 'E2'").set_index(["repeticion","pliegue"]).sort_index()
    new_a = alphas.query("modelo == 'E2'").set_index(["repeticion","pliegue"]).sort_index()
    assert len(old_a) == 50 and old_a.index.equals(new_a.index)
    np.testing.assert_array_equal(new_a.alpha,old_a.alpha)
    np.testing.assert_allclose(new_a[SCORE_COLS],old_a[SCORE_COLS],atol=1e-8,rtol=0)
    assert PRE["ajustes_fisicos_programados"] == 4200 and REG["presupuesto"]["total_ajustes"] == 2100
    display(decisiones.groupby(["modelo","alpha_elegido"]).size().rename("pliegues").to_frame())
    print("100 decisiones / 500 scores verificados; 50 controles E2 conciliados, sin reaprender.")
    ""","seleccion-visible")
    texto("""
    ## 6. OOF y escenario de evaluación

    **SEEN135** es el escenario principal declarado: municipio presente en el
    entrenamiento exterior. Se construye con roles/metadatos, nunca errores;
    igual para los cinco procedimientos. FULL138 sigue visible. No se retiran
    las tres etiquetas singleton del entrenamiento: sus 30 OOF solo quedan
    fuera del puntaje principal. Repetir diez veces no crea nuevas etiquetas.
    Las referencias se concilian a tolerancia absoluta 1e−12: su lectura y
    serialización histórica dejaron diferencias del último dígito (≤9e−16),
    no cambios en los procedimientos. Los archivos originales se conservan.
    """)
    codigo("""
    MODELOS = ["GLOBAL","MUN","MIX","E2","V4"]
    oof = leer_csv("oof","resultados_guardados")
    assert len(oof) == 6900 and set(oof.modelo) == set(MODELOS)
    assert not oof.duplicated(["modelo"]+claves).any()
    esperado = set(map(tuple,validaciones[claves].to_numpy()))
    y = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    for m,q in oof.groupby("modelo"):
        assert len(q) == 1380 and set(map(tuple,q[claves].to_numpy())) == esperado
        assert q.ID_POLIGONO.nunique() == 138 and np.isfinite(q.predicho).all()
        np.testing.assert_array_equal(q.observado,q.ID_POLIGONO.map(y))
        np.testing.assert_array_equal(q.Municipio,q.ID_POLIGONO.map(grupos.Municipio))
    viejo = leer_csv("e2_oof","resultados_guardados").query("modelo == 'E2'").set_index(claves).sort_index()
    nuevo = oof.query("modelo == 'E2'").set_index(claves).sort_index()
    assert nuevo.index.equals(viejo.index)
    np.testing.assert_array_equal(nuevo.observado,viejo.observado)
    np.testing.assert_allclose(nuevo.predicho,viejo.predicho,atol=1e-8,rtol=0)
    refs = leer_csv("referencias","resultados_guardados")
    refs["modelo"] = refs.modelo.map({"Media global":"GLOBAL","Media municipal":"MUN","Municipio + IDW fijo":"MIX"})
    assert refs.modelo.notna().all()
    for m in ["GLOBAL","MUN","MIX"]:
        a = oof.loc[oof.modelo.eq(m)].set_index(claves).sort_index()
        b = refs.loc[refs.modelo.eq(m)].set_index(claves).sort_index()
        assert a.index.equals(b.index)
        np.testing.assert_array_equal(a.observado,b.observado)
        np.testing.assert_allclose(a.predicho,b.predicho,atol=1e-12,rtol=0)
    d = oof.loc[oof.modelo.isin(["E2","V4"])].merge(decisiones,on=["modelo","repeticion","pliegue"],validate="many_to_one")
    np.testing.assert_array_equal(d.alpha,d.alpha_elegido)
    mask_rows = []
    for (r,f),q in externas.groupby(["repeticion","pliegue"]):
        mun_train = set(q.loc[q.rol.eq("entrenamiento"),"ID_POLIGONO"].map(grupos.Municipio))
        v = q.loc[q.rol.eq("validacion"),claves].copy()
        v["municipio_visto"] = v.ID_POLIGONO.map(grupos.Municipio).isin(mun_train)
        mask_rows.append(v)
    mascara = pd.concat(mask_rows,ignore_index=True)
    assert len(mascara) == 1380 and int(mascara.municipio_visto.sum()) == 1350
    check = oof.merge(mascara,on=claves,validate="many_to_one",suffixes=("_guardado",""))
    np.testing.assert_array_equal(check.municipio_visto_guardado,check.municipio_visto)
    seen = oof.loc[oof.municipio_visto].copy()
    assert len(seen) == 6750 and seen.ID_POLIGONO.nunique() == 135
    ESCENARIOS = {"SEEN135":seen,"FULL138":oof}
    display(mascara.groupby("municipio_visto").agg(oof=("ID_POLIGONO","size"),parcelas=("ID_POLIGONO","nunique")))
    print("E2 y referencias preservados; máscaras comunes e idénticas. No se han recalculado predicciones.")
    ""","oof-visible")
    texto("""
    ## 7. Comparación agrupada y estabilidad

    Cada error OOF participa: no se promedian primero las diez predicciones por
    parcela ni los RMSE de pliegues. RMSE/MAE en t/ha; R² adimensional, no definido
    cuando la varianza del objetivo es degenerada. Los 6,900 errores son repeticiones
    de 138 parcelas y cinco procedimientos, no observaciones independientes.
    Guarda numérica de este lector: R² no definido si SST≤1e−12; el motor histórico
    usó SST>0. Ninguna población real de estos controles cambia por esa precisión.
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

    def contrastar(tabla,control,keys):
        a,b = tabla.set_index(keys).sort_index(),control.set_index(keys).sort_index()
        assert a.index.equals(b.index)
        nums = a.select_dtypes(include="number").columns
        np.testing.assert_allclose(a[nums],b[nums],atol=1e-12,rtol=0,equal_nan=True)
        for c in a.columns.difference(nums):
            np.testing.assert_array_equal(a[c].fillna("<NA>"),b[c].fillna("<NA>"))

    metricas_esc = pd.DataFrame([{"escenario":s,"modelo":m,**metricas(q).to_dict()}
                              for s,df in ESCENARIOS.items() for m,q in df.groupby("modelo")])
    por_rep = pd.DataFrame([{"escenario":s,"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                           for s,df in ESCENARIOS.items() for (m,r),q in df.groupby(["modelo","repeticion"])])
    contrastar(metricas_esc,leer_csv("metricas_control","control_posterior"),["escenario","modelo"])
    contrastar(por_rep,leer_csv("repeticiones_control","control_posterior"),["escenario","modelo","repeticion"])
    principales = metricas_esc.loc[metricas_esc.escenario.eq("SEEN135")].set_index("modelo").reindex(MODELOS)
    full = metricas_esc.loc[metricas_esc.escenario.eq("FULL138")].set_index("modelo").reindex(MODELOS)
    display(principales[["n_parcelas","n_oof","RMSE","MAE","R2"]])
    fig,axes = plt.subplots(1,2,figsize=(10,3.5))
    for ax,met,ref in zip(axes,["RMSE","MAE"],["MIX","MUN"]):
        ax.bar(["E2","V4"],principales.loc[["E2","V4"],met],color=["#75849b","#287d77"])
        ax.axhline(principales.loc[ref,met],ls="--",color="#b64834",label=ref)
        ax.set(ylabel=f"{met} (t/ha)",title="SEEN135 · menor es mejor"); ax.legend()
    fig.tight_layout(); plt.show()
    ""","metricas-visibles")
    texto("""
    Regla interna de avance, no puntuación oficial ni test de significación:
    RMSE<MIX y MAE≤MUN agrupados, cada condición en ≥8/10 repeticiones.
    Mejorar E2 explica el contraste, pero no basta para adoptar el candidato.
    """)
    codigo("""
    def regla_avance(df):
        g = pd.DataFrame({m:metricas(q) for m,q in df.groupby("modelo")}).T
        reps = pd.DataFrame([{"modelo":m,"repeticion":r,**metricas(q).to_dict()}
                             for (m,r),q in df.groupby(["modelo","repeticion"])])
        R = reps.pivot(index="repeticion",columns="modelo",values="RMSE")
        A = reps.pivot(index="repeticion",columns="modelo",values="MAE")
        if set(R.index) != set(range(10)) or set(R.columns) != set(MODELOS) or R.isna().any().any() or A.isna().any().any():
            raise ValueError("Repeticiones/modelos incompletos")
        nr,na = int((R.V4<R.MIX).sum()),int((A.V4<=A.MUN).sum())
        return {"mejora_E2_RMSE":bool(g.loc["V4","RMSE"]<g.loc["E2","RMSE"]),
                "mejora_E2_repeticiones":int((R.V4<R.E2).sum()),
                "supera_MIX_RMSE_agrupado":bool(g.loc["V4","RMSE"]<g.loc["MIX","RMSE"]),
                "no_empeora_MUN_MAE_agrupado":bool(g.loc["V4","MAE"]<=g.loc["MUN","MAE"]),
                "rep_RMSE_mejor_MIX":nr,"rep_MAE_no_peor_MUN":na,
                "cumple_regla":bool(g.loc["V4","RMSE"]<g.loc["MIX","RMSE"] and g.loc["V4","MAE"]<=g.loc["MUN","MAE"] and nr>=8 and na>=8)}

    decision = {"escenario_principal":"SEEN135",**regla_avance(seen)}
    assert decision == REG["decision"] and not decision["cumple_regla"]
    display(pd.DataFrame([decision]))
    print("ΔRMSE V4−E2:",float(principales.loc["V4","RMSE"]-principales.loc["E2","RMSE"]),"t/ha")
    print("9/10 frente a E2; 0/10 frente a MIX; 0/10 MAE≤MUN. Cerrar sin adopción.")
    display(full[["RMSE","MAE","R2"]].rename_axis("FULL138: modelo"))
    ""","regla-visible")
    texto("""
    ## 8. Territorio y concentración de la mejora

    Chignahuapan concentra 71 etiquetas: E2 0.6033 → V4 0.6009 RMSE, todavía
    detrás de MIX 0.5736; el MAE aumenta. No se resolvió la variación interna.
    Ganancia SSE = error² de referencia menos error² de V4. Sumar por parcela
    conserva diez errores; fracción positiva bruta no es porcentaje de ganancia neta.

    Retirar las parcelas más favorecidas **solo al evaluar** es sensibilidad
    registrada, no nuevo entrenamiento ni permiso para borrar datos. Los controles
    se leen después del cálculo; las exclusiones no seleccionan el modelo.
    """)
    codigo("""
    zonas = pd.DataFrame([{"escenario":s,"modelo":m,"region":z,**metricas(a).to_dict()}
                         for s,df in ESCENARIOS.items() for m,g in df.groupby("modelo")
                         for z,a in [("Chignahuapan",g.loc[g.Municipio.eq("Chignahuapan")]),("Resto",g.loc[~g.Municipio.eq("Chignahuapan")])]])
    contrastar(zonas,leer_csv("region_control","control_posterior"),["escenario","modelo","region"])
    conc,sens = [],[]
    for s,df in ESCENARIOS.items():
        for m,g in df.groupby("modelo"):
            sens.append({"escenario":s,"modelo":m,"sensibilidad":"sin_AGC_127_171",
                         **metricas(g.loc[~g.ID_POLIGONO.isin(["AGC_127","AGC_171"])]).to_dict()})
        for comp in ["E2","MIX"]:
            p = df.loc[df.modelo.eq("V4")].merge(df.loc[df.modelo.eq(comp)],on=claves,suffixes=("_v4","_ref"),validate="one_to_one")
            np.testing.assert_array_equal(p.observado_v4,p.observado_ref)
            gain = (p.predicho_ref-p.observado_ref)**2-(p.predicho_v4-p.observado_v4)**2
            byplot = pd.DataFrame({"ID_POLIGONO":p.ID_POLIGONO,"gain":gain}).groupby("ID_POLIGONO").gain.sum().sort_values(ascending=False)
            positivo,neto = float(byplot.clip(lower=0).sum()),float(byplot.sum())
            for n in [2,5]:
                ids = byplot.head(n).index.tolist()
                conc.append({"escenario":s,"comparador":comp,"top_n":n,"ids":";".join(ids),
                             "ganancia_sse_neta":neto,"ganancia_sse_top":float(byplot.head(n).sum()),
                             "fraccion_ganancia_positiva_top":float(byplot.head(n).clip(lower=0).sum()/positivo) if positivo>0 else np.nan})
                for m in ["V4",comp]:
                    a = df.loc[df.modelo.eq(m)&~df.ID_POLIGONO.isin(ids)]
                    sens.append({"escenario":s,"modelo":m,"sensibilidad":f"sin_top{n}_favorables_V4_vs_{comp}",**metricas(a).to_dict()})
    concentracion,sensibilidad = pd.DataFrame(conc),pd.DataFrame(sens)
    contrastar(concentracion,leer_csv("concentracion_control","control_posterior"),["escenario","comparador","top_n"])
    contrastar(sensibilidad,leer_csv("sensibilidad_control","control_posterior"),["escenario","modelo","sensibilidad"])
    display(zonas.loc[zonas.escenario.eq("SEEN135"),["modelo","region","n_parcelas","RMSE","MAE"]])
    display(concentracion.loc[concentracion.escenario.eq("SEEN135")])
    display(sensibilidad.loc[sensibilidad.escenario.eq("SEEN135")&sensibilidad.sensibilidad.eq("sin_top5_favorables_V4_vs_E2")])
    print("Las cinco más favorecidas aportan más SSE que la mejora neta; sin ellas se invierte V4/E2.")
    ""","concentracion-visible")
    texto("""
    ## 9. Disponibilidad en las 59 ocultas, sin predecirlas

    Hay 50 fechas soportadas y nueve ausentes. Cuatro fechas quedan fuera del
    rango municipal etiquetado; rango univariado no equivale a soporte multivariado
    ni proporciona precisión. Cuautepec tiene cinco etiquetas pero solo un pico
    disponible; sus cuatro ocultas carecen de pico. Nanacamilpa tiene una etiqueta
    y AGC_120 oculta: SEEN135 no evalúa ese caso. No inventamos su incertidumbre.
    """)
    codigo("""
    train_x = alternativa.loc[alternativa.ID_POLIGONO.isin(etiquetas.ID_POLIGONO)]
    hidden_x = alternativa.loc[~alternativa.ID_POLIGONO.isin(etiquetas.ID_POLIGONO)]
    rows = []
    for _,h in hidden_x.iterrows():
        a = train_x.loc[train_x.Municipio.eq(h.Municipio)]; vals = a[PEAK].dropna(); v = h[PEAK]
        rows.append({"ID_POLIGONO":h.ID_POLIGONO,"Municipio":h.Municipio,
                     "n_etiquetas_municipio":len(a),"n_picos_soportados_municipio":len(vals),
                     "pico_soportado_doy":float(v) if pd.notna(v) else np.nan,"pico_ausente":bool(pd.isna(v)),
                     "fuera_rango_municipal":bool(v<vals.min() or v>vals.max()) if pd.notna(v) and len(vals) else None,
                     "caso_singleton":bool(len(a)==1)})
    soporte = pd.DataFrame(rows)
    contrastar(soporte,leer_csv("soporte_control","control_posterior"),["ID_POLIGONO"])
    assert len(soporte) == 59 and int(soporte.pico_ausente.sum()) == 9 and int(soporte.caso_singleton.sum()) == 1
    assert int(soporte.fuera_rango_municipal.eq(True).sum()) == 4
    display(soporte.groupby("Municipio").agg(ocultas=("ID_POLIGONO","size"),pico_ausente=("pico_ausente","sum"),
            etiquetas=("n_etiquetas_municipio","first"),picos_etiquetados=("n_picos_soportados_municipio","first")))
    print("Solo X y presencia de etiquetas, ningún rendimiento oculto calculado.")
    ""","soporte-visible")
    texto("""
    ## 10. Cierre del experimento y del recorrido histórico

    - **Cerrar V4 sin adopción:** mejora pequeña frente a E2 (≈0.005 t/ha en RMSE),
      con MAE ligeramente peor y sin superar MUN/MIX bajo la regla declarada.
    - El contraste cambia conjuntamente suavizado, guardas y faltantes. No aísla
      la contribución de cada componente ni demuestra precisión fenológica.
    - No demuestra que Planet, fenología o Ridge sean inútiles: se evaluó esta
      única sustitución, esta ventana, estas seis variables y una sola campaña.
    - Conservar las referencias simples y diagnósticos por territorio. Curvas
      más interpretables no sustituyen desempeño fuera de muestra.

    Esta lectura completa las **seis rondas históricas centralizadas**. Recalcular
    variables, métricas y decisiones no es una nueva prueba independiente ni
    demuestra paridad de reentrenamiento Python 3.12/3.13. Una siguiente hipótesis
    requiere decisión y registro propios; este cuaderno no la ejecuta automáticamente.
    Las 46 pruebas sintéticas del registro original no se presentan como ejecutadas aquí.
    """)
    codigo("""
    resumen = {"id":"EXP_06","modo":"lector_retrospectivo_sin_ajustes","parcelas":197,"etiquetas":138,
               "capturas_incorporadas":26255,"dias_diarios_recalculados":26255,"curva_puntos":18248,
               "picos_recalculados":197,"picos_soportados":158,"picos_ausentes":39,
               "picos_soportados_etiquetados":108,"picos_soportados_ocultos":50,
               "columnas_sustituidas":1,"columnas_numericas":6,"bandera_como_predictor":False,
               "anchuras_recalculadas":False,"otras_variables_recalculadas":False,
               "procedimientos":5,"candidatos":1,"oof_total":6900,"oof_por_procedimiento":1380,
               "particiones_externas":50,"particiones_internas":200,"decisiones_verificadas":100,
               "scores_guardados_verificados":500,"controles_alpha_E2":50,
               "ajustes_actuales":0,"predicciones_finales_generadas":0,"predicciones_recalculadas":False,
               "scores_interiores_recalculados":False,"metricas_recalculadas":True,
               "poblacion":"SEEN135","oof_seen_por_procedimiento":1350,"poblacion_secundaria":"FULL138",
               "regla_seen_cumplen":[],"variantes_adoptadas":[],"decision":decision,
               "soporte_ocultas_ausentes":9,"soporte_ocultas_fuera_rango":4,"soporte_ocultas_singleton":1,
               "fecha_original":"2026-10-06","fecha_factibilidad":"2026-10-02","fecha_adaptacion":"2026-10-08",
               "metricas_seen":principales[["RMSE","MAE","R2"]].to_dict(orient="index"),
               "metricas_full":full[["RMSE","MAE","R2"]].to_dict(orient="index"),
               "fecha_ejecucion_utc":datetime.now(timezone.utc).isoformat()}
    print("RESUMEN_EXP_06_JSON="+json.dumps(resumen,sort_keys=True,ensure_ascii=False,allow_nan=False))
    ""","cierre")
    texto("""
    ## Referencias y conceptos para profundizar (APA 7)

    Equipo AgroCebada. (2026, 2 de octubre). *Receta de factibilidad fenológica V4*
    [Registro interno]. Equipo AgroCebada. (2026, 6 de octubre). *V4: sustitución de
    fecha de pico NDVI en E2* [Protocolo exploratorio]. Recetas y resultados están
    incorporados, sin necesidad de consultar otro documento.

    U.S. Geological Survey. (s. f.). *Methods for deriving metrics*.
    https://www.usgs.gov/special-topics/remote-sensing-phenology/science/methods-deriving-metrics
    Fuente de contexto sobre métricas de series de vegetación, no validación de
    nuestras guardas o de su aplicación a cebada.

    scikit-learn developers. (s. f.). *Pipeline*.
    https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html

    Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and
    subsequent selection bias in performance evaluation. *Journal of Machine Learning
    Research, 11*, 2079–2107. https://jmlr.org/papers/v11/cawley10a.html

    **Glosario:** DOY = día del año; mediana móvil = centro robusto de valores en una
    ventana; meseta = máximos empatados según tolerancia; censura = pico sin margen
    temporal suficiente; guarda = regla para no liberar un descriptor sin soporte;
    imputación = reemplazar NaN con una regla aprendida en entrenamiento; OOF =
    predicción fuera de muestra; SSE = suma de errores cuadrados; SEEN135 = municipio
    presente en entrenamiento, no muestra nueva ni cobertura completa de la entrega.
    """)
    for i,c in enumerate(celdas):
        c.id = f"exp06-{i:03d}"
    metadata = copy.deepcopy(base.metadata)
    metadata["agrocebada"] = {
        "id":"EXP_06","modo":"lector_retrospectivo_sin_ajustes","crisp_dm":[3,4,5],
        "fecha_original":"2026-10-06","fecha_factibilidad":"2026-10-02","fecha_adaptacion":"2026-10-08",
        "ajustes_actuales":0,"colab_real_probado":False,
        "dependencias_requeridas":base.metadata.agrocebada.dependencias_requeridas,
        "perfil_sha256":base.metadata.agrocebada.perfil_sha256,"soporte_sha256":base.metadata.agrocebada.soporte_sha256,
        "recorte_capturas":cfg["recorte_capturas"],
        "insumos":{k:{a:b for a,b in v.items() if a != "bytes_zlib_base64"} for k,v in registros.items()},
        "configuracion_sha256":huella((raiz/cfg_rel).read_bytes()),"base_sha256":BASE_SHA256,
    }
    nb = nbformat.v4.new_notebook(cells=celdas,metadata=metadata)
    nbformat.validate(nb)
    return nb


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida",type=Path,default=raiz/"notebooks/experimentos/exp_06_pico_soportado/exp_06_pico_soportado.ipynb")
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("Elige una salida nueva; no sobrescribir el cuaderno revisado")
    nb = construir(raiz)
    args.salida.parent.mkdir(parents=True,exist_ok=True)
    nbformat.write(nb,args.salida)
    print(f"{args.salida}: {len(nb.cells)} celdas, {sum(c.cell_type == 'code' for c in nb.cells)} de código; cero ajustes")


if __name__ == "__main__":
    main()
