"""Construye el lector autónomo EXP_01 sin entrenar ni crear candidatos nuevos."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import zlib
from pathlib import Path
from textwrap import dedent

import nbformat

REQUERIDOS = ("numpy", "pandas", "matplotlib")
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)


def huella(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def derivar_soporte(texto: str) -> str:
    """Reutiliza el soporte comprobado sin requerir bibliotecas geo en este lector."""
    antes = 'REQUERIDOS_AUDITORIA = (\n    "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown",\n)'
    geo = '    from pyproj import Transformer\n    from shapely.geometry import Point\n'
    pruebas = '''    if Point(0, 0).is_empty:
        raise RuntimeError("No pasó la comprobación mínima de Shapely.")
    x, y = Transformer.from_crs(4326, 3857, always_xy=True).transform(0, 0)
    if not np.allclose([x, y], [0, 0]):
        raise RuntimeError("No pasó la comprobación mínima de PROJ.")
'''
    for bloque in (antes, geo, pruebas):
        if texto.count(bloque) != 1:
            raise ValueError("Cambió el soporte compartido: revisar la derivación de EXP_01")
    return texto.replace(antes, 'REQUERIDOS_AUDITORIA = ("numpy", "pandas", "matplotlib")', 1).replace(geo, "", 1).replace(pruebas, "", 1)


def cargar_insumos(raiz: Path) -> dict:
    config = json.loads((raiz / "config/exp_01_bloques.json").read_text())
    salida = {}
    for nombre, contrato in config["insumos"].items():
        contenido = (raiz / contrato["ruta_local"]).read_bytes()
        if len(contenido) != contrato["bytes"] or huella(contenido) != contrato["sha256"]:
            raise ValueError(f"Insumo diferente del contrato: {nombre}")
        salida[nombre] = {**contrato, "contenido": contenido}
    return salida


def construir(raiz: Path | None = None) -> nbformat.NotebookNode:
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    config_path = raiz / "config/exp_01_bloques.json"
    config = json.loads(config_path.read_text())
    perfil_path = raiz / "requirements-colab-auditoria.txt"
    perfil = perfil_path.read_text()
    fijadas = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)", perfil, re.MULTILINE))
    versiones = {nombre: fijadas[nombre] for nombre in REQUERIDOS}
    soporte_path = raiz / "scripts/colab_soporte.py"
    soporte = derivar_soporte(soporte_path.read_text())
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
            celda.source = f'# @title {titulo} {{ display-mode: "form" }}\n' + celda.source
            celda.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        celdas.append(celda)

    texto("""
    # EXP_01. ¿Qué aporta cada bloque de variables sobre el municipio?

    **CRISP-DM: modelar y evaluar.** Preguntamos si añadir clima, satélite del ciclo
    o historia a una regresión municipal mejora sus predicciones. Acotamos bloques,
    procedimiento y comparación; no escogemos columnas hasta encontrar un resultado favorable.

    **Modo: lector retrospectivo, cero ajustes de modelo.** Reconstruimos 14 variables,
    abrimos su preparación y recalculamos métricas de predicciones fuera de muestra
    **guardadas**. No recalculamos esas predicciones ni los scores interiores: eso
    requeriría volver a entrenar. No se generan las 59 predicciones finales.

    Trabajo original: **21 de septiembre de 2026**. Adaptación: **8 de octubre de 2026**.
    Es la primera de seis rondas históricas, no una ronda nueva ni un preregistro actual.
    El original utilizó Python 3.10.12/scikit-learn 1.7.2; este lector usa Python 3.13.

    **Recorrido:** hipótesis → variables → procedimiento → errores comparables → decisión.
    Basta subir **este notebook** a Colab: contiene sus tablas y controles. No necesita
    ZIP, Drive, Git ni otro cuaderno. Los bloques técnicos están plegados; los cálculos
    científicos que explican la comparación están visibles.
    """)
    texto("""
    ## 1. ¿Qué ejecutamos y de dónde salen los insumos?

    Colab prepara solo NumPy, pandas y Matplotlib con las versiones de uv.
    `PREPARAR_COLAB = True` anuncia instalaciones necesarias; si cambia un módulo
    cargado, solicita reiniciar manualmente. En local no instala nada.

    Los dos bloques plegados no son modelos ocultos: uno prepara el entorno; otro
    comprueba y descomprime las tablas. «Mostrar código» abre su contenido completo.
    """)
    codigo(soporte, "soporte-colab", "Preparación de Colab: tres bibliotecas, sin descargar datos")
    celdas[-1].source = celdas[-1].source.split("\n", 1)[0]+"\n"+soporte
    codigo("""
    PREPARAR_COLAB = True
    import importlib.util
    import sys
    try:
        EN_COLAB = importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:
        EN_COLAB = False
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("Este lector requiere Python 3.13 en local y Colab.")
    REQUIREMENTS_COLAB = __PERFIL__
    VERSIONES = __VERSIONES__
    assert hashlib.sha256(REQUIREMENTS_COLAB.encode()).hexdigest() == __HASH__
    preparacion = preparar_colab(REQUIREMENTS_COLAB, en_colab=EN_COLAB, habilitar=PREPARAR_COLAB)
    print(preparacion["estado"])
    """.replace("__PERFIL__", repr(perfil)).replace("__VERSIONES__", repr(versiones))
           .replace("__HASH__", repr(huella(perfil.encode()))), "preparar-colab")
    codigo("""
    import base64
    import hashlib
    import importlib.metadata as metadata
    import io
    import json
    import platform
    import zlib
    from datetime import datetime, timezone
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    from IPython.display import display

    FECHA_EJECUCION_UTC = datetime.now(timezone.utc).isoformat()
    assert all(metadata.version(k) == v for k, v in VERSIONES.items())
    print("Python:", platform.python_version(), "| Ejecución UTC:", FECHA_EJECUCION_UTC)
    display(pd.DataFrame([{"biblioteca": k, "version": v} for k, v in VERSIONES.items()]))
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})
    """, "entorno")
    texto("""
    | Tabla | Uso aquí | Lo que no implica |
    | --- | --- | --- |
    | Variables y etiquetas aparte | Derivar candidatos; verificar 138 rendimientos | 539 columnas no son 539 predictores |
    | Roles exteriores/interiores | Comprobar quién entrena y quién se aparta | No revelan el split oficial |
    | OOF y scores guardados | Recalcular errores y la decisión de alpha | No reproducen los ajustes Ridge |
    | Métricas históricas | Contraste posterior del recálculo | No seleccionan candidatos |
    | Manifiesto y registro | Recetas, fechas y versiones originales | Hash no certifica fecha ante terceros |

    Las OOF son **insumos de esta lectura**, no respuestas usadas para entrenar.
    La tabla de variables contiene la reconstrucción de 197 parcelas; aquí no volvemos
    a extraer rásteres o capturas. Preparar fuentes y evaluar hipótesis son tareas distintas.
    """)
    codigo("""
    INSUMOS_INCRUSTADOS = __INSUMOS__

    def bytes_insumo(nombre, uso):
        reg = INSUMOS_INCRUSTADOS[nombre]
        if reg["uso"] != uso:
            raise ValueError("Uso incompatible con el contrato")
        if (type(reg["bytes"]) is not int or not 0 < reg["bytes"] <= 2*1024*1024
                or len(reg["bytes_zlib_base64"]) > 4*1024*1024):
            raise ValueError("Contrato de tamaño fuera del límite del lector")
        comprimido = base64.b64decode(reg["bytes_zlib_base64"], validate=True)
        dec = zlib.decompressobj()
        contenido = dec.decompress(comprimido, reg["bytes"]+1)
        if len(contenido) != reg["bytes"] or not dec.eof or dec.unused_data or dec.unconsumed_tail:
            raise ValueError("Contenido comprimido incompleto o fuera del límite")
        if hashlib.sha256(contenido).hexdigest() != reg["sha256"]:
            raise ValueError("La tabla no coincide con su SHA-256")
        return contenido

    def leer_csv(nombre, uso):
        return pd.read_csv(io.BytesIO(bytes_insumo(nombre, uso)), encoding="utf-8-sig")
    """.replace("__INSUMOS__", repr(registros)), "insumos-tecnicos", "Tablas verificadas: tamaño, SHA-256 y uso")
    codigo("""
    MAN = json.loads(bytes_insumo("manifiesto", "receta_historica"))
    REG = json.loads(bytes_insumo("registro", "registro_historico"))
    X = leer_csv("variables", "predictores_fuente")
    etiquetas = leer_csv("etiquetas", "etiquetas")
    externas = leer_csv("externas", "particiones")
    internas = leer_csv("internas", "particiones")
    assert X.shape == (197, 539) and X.ID_POLIGONO.is_unique
    assert etiquetas.shape == (138, 2) and etiquetas.ID_POLIGONO.is_unique
    assert "RENDIMIENTO_T_HA" not in X
    assert set(etiquetas.ID_POLIGONO) <= set(X.ID_POLIGONO)
    assert np.isfinite(etiquetas.RENDIMIENTO_T_HA).all()
    display(pd.DataFrame([{"insumo": k, "uso": v["uso"], "bytes": v["bytes"], "sha256": v["sha256"]}
                          for k, v in INSUMOS_INCRUSTADOS.items()]))
    print("197 parcelas; 138 etiquetas. Las 59 sin etiqueta no se predicen aquí.")
    print("Calidad histórica:", MAN["configuracion_calidad"])
    """, "insumos-visibles")
    texto("""
    ## 2. Tres hipótesis pequeñas, cinco procedimientos

    | Bloque | Pregunta predictiva, no afirmación causal | Variables |
    | --- | --- | --- |
    | A: ambiente | ¿Agua, temperaturas y relieve añaden información? | Lluvia, Tmin, Tmax, elevación y pendiente |
    | B: ciclo 2025 | ¿Nivel, pico, fecha observada y sensores separados ayudan? | Tres Planet, dos Sentinel-2 y VI6T Landsat |
    | C: historia | ¿Persistencia del paisaje aporta más allá del municipio? | Tres medias de resúmenes 2022–2024 |

    **E0: municipio; E1: municipio+A; E2: municipio+B; E3: municipio+C;
    E4: municipio+A+B+C.** Conservamos ventana abril–octubre, calidad, etiquetas,
    familia y particiones. No probamos todas las combinaciones. La redundancia entre
    candidatos se revisó sin usar rendimiento. VI6T conserva la definición suministrada;
    no le atribuimos una fórmula o mecanismo físico no verificado.

    Las medias por captura coinciden con la integración y los resúmenes comprobados
    de Andrea. Cambiar su representación sería otra hipótesis, no corregir su aritmética.
    """)
    codigo("""
    A = MAN["bloques"]["A_clima_ciclo_y_topografia"]["columnas"]
    B = MAN["bloques"]["B_satelite_abr_oct_2025_sensores_separados"]["columnas"]
    derivadas = MAN["bloques"]["C_historia_2022_2024"]["columnas_derivadas"]
    C = list(derivadas)
    candidatos = {"E0": [], "E1": A, "E2": B, "E3": C, "E4": A+B+C}
    assert [len(candidatos[k]) for k in candidatos] == [0, 5, 6, 3, 14]
    assert len(set(A+B+[c for cols in derivadas.values() for c in cols])) == 20
    display(pd.DataFrame([{"procedimiento": k, "numericas": len(v), "columnas": ", ".join(v)}
                          for k, v in candidatos.items()]))
    """, "bloques-visibles")
    texto("""
    **Una parcela, una derivación.** La media por fila de tres resúmenes anuales no usa
    etiquetas. `skipna=True` omite años ausentes; si faltan los tres queda NaN.
    Son antecedentes de la parcela, **no tres rendimientos nuevos**, ni prueba de que
    hubo cebada antes de 2025. Media de medias no equivale a juntar todas las capturas.
    """)
    codigo("""
    for nombre, columnas in derivadas.items():
        X[nombre] = X[columnas].mean(axis=1, skipna=True)
    parcela = X.loc[X.ID_POLIGONO.eq("AGC_001")].iloc[0]
    historia = []
    for nombre, columnas in derivadas.items():
        valores = parcela[columnas].to_numpy(dtype=float)
        validos = valores[np.isfinite(valores)]
        manual = validos.sum()/len(validos) if len(validos) else np.nan
        np.testing.assert_allclose(manual, parcela[nombre], atol=1e-12, rtol=0)
        historia.append({"variable": nombre, "2022": valores[0], "2023": valores[1],
                         "2024": valores[2], "años_disponibles": len(validos), "media": manual})
    display(pd.DataFrame(historia))
    display(X[["ID_POLIGONO", "Municipio"]+A+B+C].head())
    """, "historia-visible")
    texto("""
    ## 3. Misma parcela apartada, misma comparación

    La evaluación original es **FULL138**: cinco pliegues y diez repeticiones, 50
    exteriores. Cada parcela aparece diez veces fuera de muestra. Cada entrenamiento
    exterior contiene cuatro divisiones interiores para elegir alpha. Sus IDs deben
    excluir toda validación exterior. No adoptamos retrospectivamente SEEN135.

    Son particiones de desarrollo guardadas, no el procedimiento oficial del reto.
    Repetir divisiones no crea etiquetas independientes.
    """)
    codigo("""
    ids = set(etiquetas.ID_POLIGONO)
    assert len(externas) == 6900 and len(internas) == 22080
    assert not externas.duplicated(["repeticion", "pliegue", "ID_POLIGONO"]).any()
    assert not internas.duplicated(["repeticion", "pliegue", "pliegue_interno", "ID_POLIGONO"]).any()
    assert set(externas.rol) == set(internas.rol) == {"entrenamiento", "validacion"}
    assert set(externas.repeticion) == set(range(10)) and set(externas.pliegue) == set(range(5))
    assert set(internas.pliegue_interno) == set(range(4))
    assert set(internas.groupby(["repeticion", "pliegue"]).groups) == set(externas.groupby(["repeticion", "pliegue"]).groups)
    for (r, f), parte in externas.groupby(["repeticion", "pliegue"]):
        train_ids = set(parte.loc[parte.rol.eq("entrenamiento"), "ID_POLIGONO"])
        val_ids = set(parte.loc[parte.rol.eq("validacion"), "ID_POLIGONO"])
        assert train_ids.isdisjoint(val_ids) and train_ids | val_ids == ids
        dentro = internas.loc[internas.repeticion.eq(r) & internas.pliegue.eq(f)]
        assert set(dentro.ID_POLIGONO) == train_ids
        for _, iparte in dentro.groupby("pliegue_interno"):
            assert set(iparte.ID_POLIGONO) == train_ids
        frecuencia = dentro.loc[dentro.rol.eq("validacion")].groupby("ID_POLIGONO").size()
        assert set(frecuencia.index) == train_ids and frecuencia.eq(1).all()
    claves = ["repeticion", "pliegue", "ID_POLIGONO"]
    validaciones = externas.loc[externas.rol.eq("validacion"), claves].copy()
    frecuencia = validaciones.groupby(["repeticion", "ID_POLIGONO"]).size()
    assert len(validaciones) == len(frecuencia) == 1380 and frecuencia.eq(1).all()
    ejemplo_roles = externas.loc[externas.repeticion.eq(0) & externas.pliegue.eq(0)]
    display(ejemplo_roles.groupby("rol").size().rename("parcelas").to_frame())
    display(internas.loc[internas.repeticion.eq(0) & internas.pliegue.eq(0)]
            .groupby(["pliegue_interno", "rol"]).size().rename("parcelas").to_frame())
    """, "particiones-visibles")
    texto(r"""
    ## 4. ¿Por qué Ridge y qué significa preparar variables?

    Una familia lineal regularizada permite examinar bloques con pocos parámetros y
    controlar una receta. Ridge minimiza $\sum_i(y_i-\hat y_i)^2+\alpha\sum_j w_j^2$;
    penaliza coeficientes, no el intercepto. No prueba que la relación real sea lineal.
    Véase la [definición oficial de Ridge](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html).

    **Pipeline histórico:** municipio → indicadores completos 0/1, sin escalar;
    numéricas → mediana → estandarización → Ridge con intercepto. Medianas, medias,
    escalas y categorías se aprenden **solo del entrenamiento correspondiente**.
    Para alpha ocurre dentro de cada división interior, no una vez globalmente.
    La [documentación de preprocesamiento](https://scikit-learn.org/stable/modules/preprocessing.html)
    explica aplicar al apartado las estadísticas de entrenamiento.

    **E0 no es MUN.** Penaliza efectos municipales; MUN usa la media municipal sin
    esa penalización. Municipio desconocido en Ridge → indicadores cero → intercepto
    y, si hay numéricas, su contribución. No tiene fallback explícito a GLOBAL.
    """)
    codigo("""
    # Abrimos la preparación de E3 en el exterior 0/0; no ajustamos Ridge.
    base = X.set_index("ID_POLIGONO")
    train_ids = ejemplo_roles.loc[ejemplo_roles.rol.eq("entrenamiento"), "ID_POLIGONO"]
    val_ids = ejemplo_roles.loc[ejemplo_roles.rol.eq("validacion"), "ID_POLIGONO"]
    train, val = base.loc[train_ids], base.loc[val_ids]
    categorias = sorted(train.Municipio.unique())
    Dtrain = pd.get_dummies(train.Municipio, dtype=float).reindex(columns=categorias)
    Dval = pd.get_dummies(val.Municipio, dtype=float).reindex(columns=categorias, fill_value=0)
    mediana = train[C].median()
    assert mediana.notna().all()
    completos = train[C].fillna(mediana)
    media = completos.mean()
    escala = completos.std(ddof=0).replace(0, 1)
    Ztrain = (completos-media)/escala
    Zval = (val[C].fillna(mediana)-media)/escala
    np.testing.assert_allclose(Ztrain.mean(), 0, atol=1e-12)
    diseno_train = pd.concat([Dtrain.add_prefix("mun_"), Ztrain], axis=1)
    diseno_val = pd.concat([Dval.add_prefix("mun_"), Zval], axis=1)
    display(pd.DataFrame({"mediana_train": mediana, "media_train": media, "escala_train_ddof0": escala}))
    display(diseno_val.head())
    print("Matrices:", diseno_train.shape, diseno_val.shape, "| Ajustes Ridge actuales: 0")
    """, "diseno-visible")
    texto("""
    La demostración abre un exterior; no reproduce las estadísticas de los 5,250
    ajustes. No usa rendimiento para construir la matriz. Los coeficientes y estadísticas
    históricas ajustadas no están guardados aquí: no los inventamos.

    ## 5. ¿Cómo se eligió alpha sin consultar la evaluación exterior?

    Rejilla: **0.01, 0.1, 1, 10, 100**. Se entrenó cada opción en las cuatro interiores,
    puntuando sus errores concatenados: RMSE agrupado, no media de cuatro RMSE.
    Se eligió el menor; dentro de una tolerancia de 10⁻¹², el alpha mayor. Después se
    reajustó en todo el entrenamiento exterior.

    La [validación cruzada](https://scikit-learn.org/stable/modules/cross_validation.html)
    separa selección y evaluación. No elimina sesgos al formular nuevas hipótesis tras
    ver resultados: la ronda reconoce exploración previa y es **exploratoria**.
    """)
    codigo("""
    ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
    seleccion = leer_csv("seleccion", "scores_guardados")

    def seleccionar_alpha(fila):
        scores = np.array([fila[f"rmse_interno_alpha_{a:g}"] for a in ALPHAS], dtype=float)
        if not np.isfinite(scores).all() or (scores < 0).any():
            raise ValueError("Scores internos inválidos")
        return float(np.array(ALPHAS)[scores <= scores.min()+1e-12].max())

    assert len(seleccion) == 250 and set(seleccion.modelo) == set(candidatos)
    assert not seleccion.duplicated(["modelo", "repeticion", "pliegue"]).any()
    assert set(seleccion.alpha) <= set(ALPHAS)
    for _, grupo in seleccion.groupby("modelo"):
        assert set(zip(grupo.repeticion, grupo.pliegue)) == set(externas.groupby(["repeticion", "pliegue"]).groups)
    decisiones = seleccion.apply(seleccionar_alpha, axis=1)
    np.testing.assert_array_equal(decisiones, seleccion.alpha)
    fila = seleccion.loc[seleccion.modelo.eq("E3") & seleccion.repeticion.eq(0) & seleccion.pliegue.eq(0)].iloc[0]
    display(pd.DataFrame({"alpha": ALPHAS, "RMSE_interno_guardado": [fila[f"rmse_interno_alpha_{a:g}"] for a in ALPHAS]}))
    print("Alpha registrado y recalculado:", fila.alpha, seleccionar_alpha(fila))
    print("250 decisiones coinciden. Presupuesto histórico: 5×5×4×50 = 5,000 + 250 reajustes.")
    print("Presupuesto actual de este lector: 0 ajustes.")
    """, "seleccion-visible")
    texto("""
    **Límite:** verificamos la decisión desde cinco scores interiores guardados por
    exterior. Faltan sus errores individuales: no recalculamos scores ni reproducimos
    entrenamiento. Coincidencia con registros y comprobación de IDs dan trazabilidad,
    no certifican por sí solas ausencia de toda fuga.

    ## 6. ¿Son comparables las predicciones que puntuamos?

    Cada candidato y referencia debe tener las mismas claves `(repetición, pliegue,
    parcela)` y la etiqueta original. MIX = 50 % MUN + 50 % IDW, k=20, potencia 2 y
    piso 1 m. Coordenadas intervienen en MIX, **no en los candidatos Ridge**.
    """)
    codigo("""
    oof = leer_csv("oof", "resultados_guardados")
    ref = leer_csv("referencias", "resultados_guardados")
    alias = {"Media global": "GLOBAL", "Media municipal": "MUN", "Municipio + IDW fijo": "MIX"}
    ref = ref.loc[ref.modelo.isin(alias)].copy()
    ref["modelo"] = ref.modelo.map(alias)
    assert set(oof.modelo) == set(candidatos) and len(oof) == 6900
    assert set(ref.modelo) == {"GLOBAL", "MUN", "MIX"} and len(ref) == 4140
    todos = pd.concat([oof.drop(columns="alpha"), ref], ignore_index=True)
    esperado = set(map(tuple, validaciones[claves].to_numpy()))
    oficial = etiquetas.set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    assert not todos.duplicated(["modelo"]+claves).any()
    for _, grupo in todos.groupby("modelo"):
        assert len(grupo) == 1380 and set(map(tuple, grupo[claves].to_numpy())) == esperado
        np.testing.assert_allclose(grupo.observado, grupo.ID_POLIGONO.map(oficial), atol=0, rtol=0)
        assert np.isfinite(grupo[["observado", "predicho"]].to_numpy()).all()
    alphas_oof = oof.merge(seleccion[["modelo", "repeticion", "pliegue", "alpha"]],
                          on=["modelo", "repeticion", "pliegue"], validate="many_to_one", suffixes=("", "_seleccion"))
    np.testing.assert_array_equal(alphas_oof.alpha, alphas_oof.alpha_seleccion)
    todos = todos.merge(X[["ID_POLIGONO", "Municipio", "Estado"]], on="ID_POLIGONO", validate="many_to_one")
    todos["error"] = todos.predicho-todos.observado
    todos["error2"] = todos.error**2
    todos["zona"] = np.where(todos.Municipio.eq("Chignahuapan"), "Chignahuapan", "Resto")
    print("8 procedimientos; 11,040 OOF comprobadas. No son 11,040 etiquetas independientes.")
    display(todos.loc[todos.ID_POLIGONO.eq("AGC_001") & todos.repeticion.eq(0),
                      ["modelo"]+claves+["observado", "predicho", "error"]])
    """, "oof-validacion")
    texto(r"""
    ## 7. ¿Mejoró el error global? Calcular antes de consultar el control

    Agrupamos **1,380 errores por procedimiento**, sin promediar primero diez predicciones:
    $RMSE=\sqrt{\overline{e^2}}$, $MAE=\overline{|e|}$,
    $R^2=1-\sum e^2/\sum(y-\bar y)^2$. RMSE/MAE están en t/ha; R² no tiene unidades.
    Media de RMSE de pliegues sería otra cantidad. Conservamos la guarda histórica:
    si la suma centrada de cuadrados es ≤10⁻¹², R² se muestra como NaN.
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

    resultados = pd.DataFrame({nombre: metricas(grupo) for nombre, grupo in todos.groupby("modelo")}).T
    resultados = resultados.loc[list(candidatos)+["GLOBAL", "MUN", "MIX"]]
    display(resultados.round(9))
    figura, ejes = plt.subplots(1, 2, figsize=(10, 3.8))
    colores = ["#718096" if k.startswith("E") else "#207f89" for k in resultados.index]
    for eje, metrica in zip(ejes, ["RMSE", "MAE"]):
        resultados[metrica].plot.bar(ax=eje, color=colores)
        eje.set_ylabel(metrica+" (t/ha)")
        eje.set_xlabel("")
        eje.tick_params(axis="x", rotation=0)
    figura.suptitle("FULL138: menor error es mejor; dos métricas, no un ganador automático")
    figura.tight_layout()
    plt.show()
    """, "metricas-visibles")
    codigo("""
    # Control posterior: no origina las métricas anteriores ni selecciona variantes.
    control = leer_csv("metricas_control", "control_posterior").set_index("modelo")
    control = control.rename(index=alias)  # Solo alias de lectura; bytes originales intactos.
    assert control.index.is_unique and set(control.index) == set(resultados.index)
    for nombre in resultados.index:
        recalculado = resultados.loc[nombre, ["RMSE", "MAE", "R2"]].to_numpy(dtype=float)
        guardado = control.loc[nombre, ["RMSE_agrupado", "MAE_agrupado", "R2_agrupado"]].to_numpy(dtype=float)
        np.testing.assert_allclose(recalculado, guardado, atol=1e-12, rtol=0)
    print("Las métricas de los ocho procedimientos coinciden con el control histórico a 10⁻¹².")
    """, "control-posterior")
    texto("""
    E3 reduce RMSE frente a E0 aproximadamente 0.0059 t/ha, pero aumenta MAE 0.0209.
    Combinar todos los bloques no gana. MIX mantiene menor RMSE y MUN menor MAE.
    Mejorar un control no basta para superar la referencia competitiva.

    ## 8. ¿La mejora se repite sobre las mismas parcelas?

    Comparación **pareada** por repetición: candidato menos referencia; negativo favorece
    al candidato. La etiqueta histórica exigía menor RMSE global y en ≥8/10 frente a E0.
    No exigía mejorar MAE; no añadimos criterios posteriores. Es descriptiva,
    **no significancia estadística ni aprobación de un modelo final**.
    """)
    codigo("""
    rep = pd.DataFrame([{ "modelo": nombre, "repeticion": r, **metricas(grupo).to_dict()}
                        for (nombre, r), grupo in todos.groupby(["modelo", "repeticion"])])
    rep_rmse = rep.pivot(index="repeticion", columns="modelo", values="RMSE")
    rep_mae = rep.pivot(index="repeticion", columns="modelo", values="MAE")
    comparaciones = []
    for nombre in ["E1", "E2", "E3", "E4"]:
        for referencia in ["E0", "MUN", "MIX"]:
            delta = resultados.loc[nombre, "RMSE"]-resultados.loc[referencia, "RMSE"]
            favorables = int((rep_rmse[nombre] < rep_rmse[referencia]).sum())
            desfavorables = int((rep_rmse[nombre] > rep_rmse[referencia]).sum())
            etiqueta = ("mejora_consistente" if delta < 0 and favorables >= 8 else
                        "empeora_consistente" if delta > 0 and desfavorables >= 8 else "no_concluyente")
            comparaciones.append({"candidato": nombre, "referencia": referencia,
                                  "delta_RMSE": delta, "delta_MAE": resultados.loc[nombre, "MAE"]-resultados.loc[referencia, "MAE"],
                                  "repeticiones_menor_RMSE": favorables,
                                  "etiqueta_original_vs_E0": etiqueta if referencia == "E0" else "no aplica"})
    display(pd.DataFrame(comparaciones))
    display(pd.DataFrame({"E3−E0_RMSE": rep_rmse.E3-rep_rmse.E0,
                         "E3−MIX_RMSE": rep_rmse.E3-rep_rmse.MIX,
                         "E3−E0_MAE": rep_mae.E3-rep_mae.E0}))
    """, "pareadas-visibles")
    texto("""
    E3 cumple la etiqueta prefijada frente a E0 en 8/10, pero supera MIX solo en 1/10.
    Las divisiones comparten datos: su rango no es un intervalo de confianza; las diez
    repeticiones no son diez experimentos independientes.

    ## 9. ¿Dónde cambia el error y de qué casos depende?

    Separamos **71 parcelas de Chignahuapan y 67 del resto**, sin cambiar entrenamiento.
    Es diagnóstico posterior, no permiso para escoger otro modelo por región.
    No hubo validación territorial sistemática dejando municipios fuera; sí hay municipios
    singleton que quedan sin etiquetas en entrenamiento al apartar su única parcela.
    """)
    codigo("""
    zonas = pd.DataFrame([{ "modelo": nombre, "zona": zona, "parcelas": grupo.ID_POLIGONO.nunique(),
                           **metricas(grupo).to_dict()}
                         for (nombre, zona), grupo in todos.groupby(["modelo", "zona"])])
    display(zonas.loc[zonas.modelo.isin(["E0", "E3", "MUN", "MIX"])])
    error_parcela = todos.groupby(["ID_POLIGONO", "modelo"]).error2.mean().unstack()
    error_parcela["ganancia_E3_vs_E0"] = error_parcela.E0-error_parcela.E3
    focos = ["AGC_127", "AGC_171"]
    ganancia_neta = error_parcela.ganancia_E3_vs_E0.sum()
    aporte_focos = error_parcela.loc[focos, "ganancia_E3_vs_E0"].sum()
    fraccion_focos = aporte_focos/ganancia_neta
    display(error_parcela[["E0", "E3", "ganancia_E3_vs_E0"]].sort_values("ganancia_E3_vs_E0", ascending=False).head(7))
    print("Parcelas con menor error cuadrático:", int(error_parcela.ganancia_E3_vs_E0.gt(0).sum()))
    print("Parcelas con mayor error cuadrático:", int(error_parcela.ganancia_E3_vs_E0.lt(0).sum()))
    print("Dos focos / ganancia cuadrática neta:", round(100*fraccion_focos, 3), "%")
    sin_focos = todos.loc[~todos.ID_POLIGONO.isin(focos)]
    sensibilidad = pd.DataFrame({k: metricas(g) for k, g in sin_focos.groupby("modelo")}).T
    display(sensibilidad.loc[["E0", "E3", "MIX"]])
    assert sensibilidad.loc["E3", "RMSE"] > sensibilidad.loc["E0", "RMSE"]
    """, "sensibilidad-visible")
    texto("""
    **166.2 %:** la mejora de dos casos excede el beneficio neto porque compensa deterioros
    en otras parcelas. Mejoran 55 y empeoran 83. Al omitir esos dos **solo de la puntuación**,
    E3 deja de mejorar RMSE frente a E0. Cambia la población; no se reajusta nada ni se
    propone retirar etiquetas. No predice qué pasaría quitándolas del entrenamiento.

    En Chignahuapan E3 baja RMSE (0.5903 → 0.5706); en el resto lo sube (0.4095 → 0.4238).
    La señal agregada no es una mejora territorial uniforme.

    ## 10. Decisión, límites y siguiente pregunta

    **Decisión conservada:** no adoptar automáticamente A/B/C ni su combinación.
    E3 aporta una mejora pequeña y frágil frente a E0; no reemplaza MIX. Conservamos
    evidencia negativa en lugar de buscar una métrica favorable.

    **Límite:** una temporada y representaciones concretas. No demuestra que clima,
    historia, satélite o la familia lineal sean inútiles; tampoco causalidad ni extrapolación.
    Recalcular errores y métricas de las OOF guardadas no valida de nuevo su entrenamiento.

    **Siguiente pregunta:** ¿la media por captura concede más peso a los meses con más
    observaciones? El diagnóstico posterior del 24 de septiembre planteó una prueba de
    ponderación temporal. Esa prueba será EXP_02; no cambiamos esta ronda ni anticipamos
    su resultado.

    Manifiesto local e informe: 21 de septiembre; diagnóstico posterior: 24; adaptación:
    8 de octubre. Hash prueba integridad, no anterioridad certificada. Esta lectura no
    ratifica decisiones por todo el equipo.
    """)
    codigo("""
    resumen = {
        "id": "EXP_01", "modo": "lector_retrospectivo_sin_ajustes",
        "parcelas": 197, "etiquetas": 138, "numericas": 14,
        "procedimientos": 8, "oof_por_procedimiento": 1380, "oof_total": len(todos),
        "particiones_externas": 50, "particiones_internas": 200,
        "decisiones_alpha_verificadas": len(seleccion), "ajustes_actuales": 0,
        "predicciones_finales_generadas": 0, "poblacion": "FULL138",
        "scores_interiores_recalculados": False, "predicciones_recalculadas": False,
        "metricas_recalculadas": True, "bloques_adoptados": [],
        "fecha_original": "2026-09-21", "fecha_adaptacion": "2026-10-08",
        "metricas": resultados.to_dict(orient="index"), "fecha_ejecucion_utc": FECHA_EJECUCION_UTC,
    }
    print("RESUMEN_EXP_01_JSON="+json.dumps(resumen, sort_keys=True))
    print("Cierre: resultados guardados conciliados; cero ajustes y cero predicciones finales.")
    """, "cierre")
    texto("""
    ## Referencias y glosario breve

    **Bloque:** conjunto pequeño de variables con una pregunta común. **Ridge:** regresión
    lineal con penalización L2. **Alpha:** fuerza de penalización elegida dentro del
    entrenamiento. **OOF:** predicción para una parcela apartada. **Pareado:** comparar
    procedimientos sobre las mismas claves. **Post hoc:** diagnóstico decidido después
    de conocer resultados; no es confirmación independiente.

    scikit-learn developers. (s. f.). *Ridge* [Documentación de software].
    https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.Ridge.html

    scikit-learn developers. (s. f.). *Preprocessing data*.
    https://scikit-learn.org/stable/modules/preprocessing.html

    scikit-learn developers. (s. f.). *Cross-validation: Evaluating estimator performance*.
    https://scikit-learn.org/stable/modules/cross_validation.html

    **Evidencia del equipo incorporada:** manifiesto `ronda1_bloques_sobre_municipio`,
    registro y tablas, integración de fuentes y referencias fijas (21 de septiembre de 2026).
    Sus bytes se identifican en la sección 1; no hace falta abrir documentos de procedencia
    para seguir esta lectura.
    """)
    nb = nbformat.v4.new_notebook(cells=celdas)
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3 (AgroCebada uv)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
        "agrocebada": {**{k: config[k] for k in ("id", "modo", "fecha_original", "fecha_adaptacion", "ajustes_actuales")},
                       "crisp_dm": [4, 5], "colab_real_probado": False,
                       "perfil_sha256": huella(perfil.encode()), "soporte_sha256": huella(soporte.encode()),
                       "fuentes_sha256": {"config/exp_01_bloques.json": huella(config_path.read_bytes()),
                                          "scripts/colab_soporte.py": huella(soporte_path.read_bytes())},
                       "insumos": {k: {clave: v for clave, v in reg.items() if clave != "bytes_zlib_base64"} for k, reg in registros.items()},
                       "dependencias_requeridas": versiones},
    }
    for n, celda in enumerate(nb.cells, 1):
        celda.id = f"exp01-{n:02d}"
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
