"""Genera NB03 autocontenido: referencias, particiones y evaluación retrospectiva."""

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


MODULOS = ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite", "fuentes_02", "validacion_03")
REQUERIDOS = ("numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown", "rasterio")


def _hash(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def derivar_soporte(texto: str) -> str:
    """Incorpora rasterio como raíz requerida sin modificar el soporte compartido."""
    antes = 'REQUERIDOS_AUDITORIA = (\n    "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown",\n)'
    despues = 'REQUERIDOS_AUDITORIA = (\n    "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown", "rasterio",\n)'
    if texto.count(antes) != 1:
        raise ValueError(
            "El soporte compartido cambió: revisar la derivación antes de generar NB03."
        )
    return texto.replace(antes, despues, 1)


def construir(raiz: Path | None = None) -> nbformat.NotebookNode:
    """Empaqueta fuentes y controles sin ejecutar ni escribir durante la construcción."""
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    config_path = raiz / "config/validacion_03_recetas.json"
    dataset_path = raiz / "config/auditoria_01_dataset.json"
    perfil_path = raiz / "requirements-colab-auditoria.txt"
    soporte_path = raiz / "scripts/colab_soporte.py"
    config_texto = config_path.read_text(encoding="utf-8")
    config = json.loads(config_texto)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    perfil = perfil_path.read_text(encoding="utf-8")
    fijadas = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)", perfil, flags=re.MULTILINE))
    versiones = {nombre: fijadas[nombre] for nombre in REQUERIDOS}
    soporte_derivado = derivar_soporte(soporte_path.read_text(encoding="utf-8"))
    modulos = {}
    for nombre in MODULOS:
        contenido = (raiz / "scripts" / f"{nombre}.py").read_bytes()
        modulos[nombre] = {"source": contenido.decode("utf-8"), "sha256": _hash(contenido)}
    insumos = {}
    for nombre, contrato in config["insumos"].items():
        contenido = (raiz / contrato["ruta_local"]).read_bytes()
        if len(contenido) != contrato["bytes"] or _hash(contenido) != contrato["sha256"]:
            raise ValueError(f"Insumo distinto de su contrato: {nombre}")
        insumos[nombre] = {
            "bytes_zlib_base64": base64.b64encode(zlib.compress(contenido, 9)).decode("ascii"),
            **{k: contrato[k] for k in ("sha256", "bytes", "uso", "origen")},
        }
    cells = []

    def texto(source):
        cells.append(nbformat.v4.new_markdown_cell(dedent(source).strip()))

    def codigo(source, tags=None, oculta=False):
        cell = nbformat.v4.new_code_cell(dedent(source).strip())
        if tags:
            cell.metadata["tags"] = tags
        if oculta:
            cell.metadata["jupyter"] = {"source_hidden": True}
        cells.append(cell)

    texto("""
    # 03. Referencias y validación: ¿con qué debemos comparar una predicción?

    **Pregunta central:** ¿podemos reconstruir tres referencias sencillas y evaluarlas
    sobre parcelas que no participaron en su ajuste, con particiones y métricas verificables?

    **CRISP-DM:** modelar y evaluar. **Modo:** recalcular referencias fijas y controles.
    Las medias se aprenden del entrenamiento de cada pliegue: **50 particiones × tres
    referencias = 150 ajustes de referencia para la evaluación OOF**. No se crean candidatos nuevos, no se
    seleccionan hiperparámetros y no se generan las 59 predicciones oficiales.

    Reconstruimos las particiones del **20 de septiembre de 2026** y las referencias e
    integración del **21 de septiembre**. La adaptación y comprobación de este cuaderno
    son del **7 de octubre de 2026**: no constituyen un preregistro ni una ronda nueva.
    No hace falta ejecutar otros cuadernos, leer una bóveda o clonar un repositorio.

    **Cómo leerlo:** parcela apartada → referencia calculada con otras parcelas →
    predicción → error → comparación sobre los mismos casos. La edición didáctica
    del **8 de octubre** abre estas operaciones sin cambiar las recetas históricas.
    Los bloques técnicos están plegados; las decisiones se estudian en las celdas visibles.
    """)
    texto("""
    ## 1. Preparar un entorno y recetas identificables

    **Qué comprobamos y por qué.** Python local **3.13.13** y Colab **3.13** deben
    utilizar las mismas bibliotecas requeridas. Colab administra su parche, que se registra.
    `PREPARAR_COLAB = True` prepara únicamente dentro de Colab las ocho bibliotecas
    faltantes o diferentes, con versiones limitadas por el perfil exportado de uv.

    Si cambia una biblioteca ya cargada, el soporte pide reiniciar manualmente y ejecutar
    todas las celdas. En local no instala nada. El soporte y las fuentes técnicas pueden
    mantenerse contraídos; sus textos y controles tienen SHA-256.
    En Colab, «Mostrar código» permite revisar el soporte y las fuentes técnicas.
    """)
    codigo(soporte_derivado, tags=["soporte-colab"], oculta=True)
    cells[-1].source = soporte_derivado
    codigo(
        """
    PREPARAR_COLAB = True
    import importlib.util
    import sys
    from pathlib import Path
    try:
        EN_COLAB = importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:
        EN_COLAB = False
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("Local y Colab requieren Python 3.13; no se cambia el intérprete.")
    REQUIREMENTS_COLAB = __PERFIL__
    VERSIONES = __VERSIONES__
    assert hashlib.sha256(REQUIREMENTS_COLAB.encode()).hexdigest() == __HASH_PERFIL__
    preparacion_entorno = preparar_colab(REQUIREMENTS_COLAB, en_colab=EN_COLAB, habilitar=PREPARAR_COLAB)
    print("Preparación:", preparacion_entorno["estado"])
    """.replace("__PERFIL__", repr(perfil))
        .replace("__VERSIONES__", repr(versiones))
        .replace("__HASH_PERFIL__", repr(_hash(perfil_path.read_bytes()))),
        tags=["preparar-colab"],
    )
    codigo(
        """
    import base64
    import hashlib
    import importlib.metadata as metadata
    import io
    import json
    import platform
    import types
    import zlib
    from datetime import datetime, timezone
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    import numpy as np
    import pandas as pd
    from IPython.display import display

    FECHA_EJECUCION_UTC = datetime.now(timezone.utc).isoformat()
    tabla_entorno = pd.DataFrame([{"biblioteca": nombre, "esperada": version,
                                  "instalada": metadata.version(nombre)} for nombre, version in VERSIONES.items()])
    assert sys.version_info[:2] == (3, 13)
    assert tabla_entorno.esperada.eq(tabla_entorno.instalada).all(), "Prepara el perfil requerido."
    print("Python:", platform.python_version(), "| Ejecución UTC:", FECHA_EJECUCION_UTC)
    display(tabla_entorno)
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    """,
        tags=["entorno"],
    )
    codigo(
        """
    CONFIG_JSON = __CONFIG__
    assert hashlib.sha256(CONFIG_JSON.encode()).hexdigest() == __HASH_CONFIG__
    CONFIG = json.loads(CONFIG_JSON)
    display(pd.DataFrame([{"referencia": nombre, **regla} for nombre, regla in CONFIG["referencias"].items()]).fillna(""))
    print("Unidad de separación:", CONFIG["particiones"]["unidad"])
    print("Agregación:", CONFIG["evaluacion"]["agregacion"])
    """.replace("__CONFIG__", repr(config_texto)).replace(
            "__HASH_CONFIG__", repr(_hash(config_path.read_bytes()))
        ),
        tags=["config-recetas"],
    )
    texto("""
    **Qué hace el motor y dónde se explica.** Cargar código permite repetir las reglas;
    no sustituye los ejemplos que siguen.

    | Bloque | Responsabilidad | Recorrido visible |
    | --- | --- | --- |
    | Soporte de Colab | Versiones, instalación controlada y acceso al ZIP | Secciones 1–2 |
    | `auditoria_01` | Integridad, lectores e identificadores | Sección 2 |
    | `fuentes_02` y `fuentes_02_geo` | Catálogo, etiquetas aparte y centroides UTM | Sección 2 |
    | `fuentes_02_satelite` | Dependencia del módulo de fuentes; aquí no resume satélite | No se construyen las 539 variables |
    | `validacion_03` | Particiones, GLOBAL/MUN/MIX, OOF y métricas | Secciones 3–9 |

    **Dos tipos de CSV incrustados.** `externas` e `internas` indican quién entrena
    y quién se aparta: sí organizan el cálculo. `oof_historico` y `metricas_historicas`
    son **salidas de control**, abiertas solo al final, no respuestas usadas para predecir.
    Los hashes comprueban identidad, no capacidad predictiva ni ausencia de toda fuga.
    """)
    codigo(
        """
    FUENTES_MODULOS = __MODULOS__
    for nombre, registro in FUENTES_MODULOS.items():
        assert hashlib.sha256(registro["source"].encode()).hexdigest() == registro["sha256"]
        modulo = types.ModuleType(nombre)
        modulo.__file__ = "<notebook03/" + nombre + ".py>"
        sys.modules[nombre] = modulo
        exec(compile(registro["source"], modulo.__file__, "exec"), modulo.__dict__)
    auditoria = sys.modules["auditoria_01"]
    fuentes02 = sys.modules["fuentes_02"]
    validacion = sys.modules["validacion_03"]
    SHA256_DATASET = auditoria.SHA256_DATASET
    assert validacion.validar_recetas_referencias(CONFIG)
    """.replace("__MODULOS__", repr(modulos)),
        tags=["modulos-tecnicos"],
        oculta=True,
    )
    codigo(
        """
    INSUMOS_INCRUSTADOS = __INSUMOS__

    def leer_insumo(nombre, uso):
        registro = INSUMOS_INCRUSTADOS[nombre]
        if registro["uso"] != uso:
            raise ValueError("El uso solicitado no corresponde al contrato del insumo.")
        comprimido = base64.b64decode(registro["bytes_zlib_base64"], validate=True)
        decoder = zlib.decompressobj()
        contenido = decoder.decompress(comprimido, registro["bytes"] + 1)
        if (len(contenido) != registro["bytes"] or not decoder.eof
                or decoder.unused_data or decoder.unconsumed_tail):
            raise ValueError("Insumo comprimido incompleto o fuera del límite de bytes.")
        if hashlib.sha256(contenido).hexdigest() != registro["sha256"]:
            raise ValueError("El insumo no coincide con su SHA-256.")
        return pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig")
    """.replace("__INSUMOS__", repr(insumos)),
        tags=["insumos-tecnicos"],
        oculta=True,
    )
    texto("""
    **Decisión y límite.** Las reglas quedan fijas antes de recalcular. Los CSV de
    particiones identifican quién se aparta; los CSV de predicciones y métricas históricas
    se abrirán después del cálculo para contrastar salidas. No son entradas predictivas.
    """)
    texto("""
    ## 2. Reconstruir las parcelas desde el ZIP original

    **Qué comprobamos y cómo.** Validamos tamaño, SHA-256, CRC e IDs; reconstruimos
    los metadatos y separamos las 138 etiquetas. Para estas referencias usamos municipio
    y centroides de área en **EPSG:32614**, no promedio de vértices ni coordenadas en grados.
    No necesitamos calcular las 539 variables satelitales, climáticas y topográficas.

    La descarga de Drive se habilita por defecto solo en Colab si falta una copia local.
    Una caché incorrecta se rechaza sin sustituirla. No se suben datos, cambian permisos
    ni utilizan cookies del navegador.
    """)
    codigo(
        """
    RUTA_DATASET = None
    ID_DRIVE_DATASET = __DRIVE__
    DESCARGAR_DATASET = EN_COLAB
    candidatos = [Path("data/raw/DataSet.zip"), Path("../data/raw/DataSet.zip"),
                  Path("DataSet.zip"), Path("/content/DataSet.zip")]
    ruta_dataset = (Path(RUTA_DATASET).expanduser() if RUTA_DATASET is not None
                    else next((ruta for ruta in candidatos if ruta.is_file()), None))
    if ruta_dataset is None:
        ruta_dataset = Path("/content/DataSet.zip") if EN_COLAB else Path("data/raw/DataSet.zip")
    ruta_dataset = obtener_dataset(ruta_dataset, file_id=ID_DRIVE_DATASET, sha256_esperado=SHA256_DATASET,
                                   bytes_esperados=29_687_194, permitir_descarga=DESCARGAR_DATASET)
    hash_inicial = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    zip_fuente = auditoria.cargar_zip(ruta_dataset)
    fuentes = fuentes02.cargar_fuentes(zip_fuente)
    meta, etiquetas = fuentes["metadatos"], fuentes["etiquetas"]
    tabla138 = meta.loc[meta.CONJUNTO.eq("ENTRENAMIENTO"), ["ID_POLIGONO", "Municipio", "x_m", "y_m"]].merge(
        etiquetas, on="ID_POLIGONO", validate="one_to_one"
    ).sort_values("ID_POLIGONO").reset_index(drop=True)
    ocultas = meta.loc[meta.CONJUNTO.eq("PREDICCION"), ["ID_POLIGONO", "Municipio"]].copy()
    assert len(meta) == 197 and len(tabla138) == 138 and len(ocultas) == 59
    assert tabla138.ID_POLIGONO.is_unique and tabla138.RENDIMIENTO_T_HA.notna().all()
    print("Dataset:", ruta_dataset.name, "| SHA-256:", hash_inicial)
    display(pd.DataFrame({"grupo": ["Catálogo", "Etiquetas visibles", "Rendimientos ocultos"], "parcelas": [197, 138, 59]}))
    """.replace("__DRIVE__", repr(dataset["transporte"]["drive"]["file_id"])),
        tags=["acceso-dataset"],
    )
    texto("""
    **Resultado y límite.** Tenemos 138 casos para desarrollar una comparación y 59
    rendimientos intencionalmente ausentes. Las 59 parcelas no participan en ajustes,
    elección de reglas ni puntuaciones de este cuaderno. El ID sirve para unir y apartar
    parcelas; no se usa como predictor. El alcance corresponde a este catálogo y campaña.
    """)
    texto("""
    ## 3. Reutilizar particiones externas por parcela

    **Qué comprobamos.** Abrimos las particiones guardadas del 20/09/2026 y comprobamos
    cobertura, claves únicas y separación. Son **cinco pliegues × diez repeticiones**:
    cada parcela se valida una vez en cada repetición. Cada ajuste aprende con 110–111
    parcelas y evalúa 27–28 que no vio.

    **Pliegue** es una separación concreta entre entrenamiento y validación;
    **repetición** es otro reparto completo de los cinco pliegues. **Ajustar** una
    referencia significa aprender su media o usar los rendimientos del entrenamiento:
    una regla sencilla también aprende de datos.

    Estos archivos proceden de un esquema aleatorio de desarrollo **no estratificado**;
    no regeneramos semillas. No conocemos el mecanismo del split oficial de FIRA ni
    afirmamos que este esquema represente municipios o campañas completamente nuevos.
    """)
    codigo(
        """
    externas = leer_insumo("externas", "particiones")
    internas = leer_insumo("internas", "particiones")
    resumen_externas = validacion.validar_externas(externas, tabla138.ID_POLIGONO)
    resumen_internas = validacion.validar_internas(internas, externas, tabla138.ID_POLIGONO)
    particiones = validacion.particiones_desde_csv(externas, tabla138)
    assert len(particiones) == 50
    display(pd.DataFrame([resumen_externas]))
    tamanos = externas.groupby(["repeticion", "pliegue", "rol"]).size().unstack("rol").reset_index()
    display(tamanos.head(10))
    assert externas.loc[externas.rol.eq("validacion")].groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()
    """,
        tags=["particiones-externas"],
    )
    texto("""
    **Decisión.** La identidad de los IDs apartados forma parte del control: cambiar una
    partición cambia la comparación. Las capturas satelitales de una misma parcela no se
    separan como si tuvieran objetivos independientes.
    """)
    texto("""
    ## 4. Ver la jerarquía exterior e interior

    **Qué comprobamos y cómo.** Las **200 particiones internas** tienen cuatro pliegues
    dentro de cada entrenamiento exterior. Ninguna parcela de validación externa puede
    aparecer en ellas. La figura muestra una repetición exterior y las internas de su
    primer pliegue; el blanco representa parcelas ausentes del entrenamiento exterior.

    En procedimientos con ajustes, la elección ocurriría dentro de estas internas y
    la evaluación externa se reservaría para después. Aquí solo verificamos esa estructura:
    las referencias tienen parámetros fijos y no seleccionan ajustes internos.
    """)
    codigo(
        """
    assert resumen_internas["sin_validacion_externa_en_internas"] and resumen_internas["contencion_ok"]
    assert internas[["repeticion", "pliegue", "pliegue_interno"]].drop_duplicates().shape[0] == 200
    ids138 = tabla138.ID_POLIGONO.tolist()
    codigos_roles = {"entrenamiento": 1, "validacion": 2}
    matriz_ext = externas.loc[externas.repeticion.eq(0)].assign(valor=lambda d: d.rol.map(codigos_roles)).pivot(
        index="pliegue", columns="ID_POLIGONO", values="valor"
    ).reindex(columns=ids138)
    matriz_int = internas.loc[internas.repeticion.eq(0) & internas.pliegue.eq(0)].assign(
        valor=lambda d: d.rol.map(codigos_roles)
    ).pivot(index="pliegue_interno", columns="ID_POLIGONO", values="valor").reindex(columns=ids138).fillna(0)
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.7), sharex=True)
    colores_roles = ListedColormap(["#eeeeee", "#759cb9", "#c16a35"])
    for ax, matriz, titulo in [(axes[0], matriz_ext, "Exterior: repetición 0, cinco pliegues"),
                               (axes[1], matriz_int, "Interior: repetición 0 / exterior 0, cuatro pliegues")]:
        ax.imshow(matriz.to_numpy(), cmap=colores_roles, vmin=0, vmax=2, interpolation="nearest", aspect="auto")
        ax.set(title=titulo, ylabel="Pliegue")
        ax.set_yticks(range(len(matriz)), matriz.index.tolist())
    ticks = np.linspace(0, 137, 8, dtype=int)
    axes[1].set_xticks(ticks, [ids138[i] for i in ticks], rotation=30, ha="right")
    axes[1].set_xlabel("Parcelas en el mismo orden en ambas matrices")
    fig.legend(handles=[Patch(color="#759cb9", label="Entrenamiento"), Patch(color="#c16a35", label="Validación"),
                        Patch(color="#eeeeee", label="Ausente de internas: validación exterior")],
               loc="upper center", ncol=3, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, .9)); plt.show()
    display(pd.DataFrame([resumen_internas]))
    """,
        tags=["jerarquia-particiones"],
    )
    texto("""
    **Abrir los IDs apartados.** Buscamos en el CSV la primera validación de AGC_001,
    sin mirar su rendimiento. Formamos dos conjuntos de IDs: deben ser disjuntos y
    cubrir las 138 parcelas. Después comprobamos que cada interna contiene solo el
    entrenamiento de ese exterior. La figura anterior usa exterior 0; este ejemplo
    muestra el pliegue donde se aparta AGC_001, identificado en la salida.

    Un **hiperparámetro** es una regla fijada antes del ajuste, como el número de vecinos.
    Si lo comparáramos para elegirlo, usaríamos las internas; aquí no elegimos ninguno.
    """)
    codigo("""
    asignacion_visible = externas.loc[externas.ID_POLIGONO.eq("AGC_001") &
                                       externas.rol.eq("validacion")].sort_values(["repeticion", "pliegue"]).iloc[0]
    r_visible, f_visible = int(asignacion_visible.repeticion), int(asignacion_visible.pliegue)
    exterior_visible = externas.loc[externas.repeticion.eq(r_visible) & externas.pliegue.eq(f_visible)]
    ids_train_visible = set(exterior_visible.loc[exterior_visible.rol.eq("entrenamiento"), "ID_POLIGONO"])
    ids_val_visible = set(exterior_visible.loc[exterior_visible.rol.eq("validacion"), "ID_POLIGONO"])
    assert ids_train_visible.isdisjoint(ids_val_visible)
    assert ids_train_visible | ids_val_visible == set(tabla138.ID_POLIGONO)
    assert "AGC_001" in ids_val_visible and "AGC_001" not in ids_train_visible
    _, _, indices_train_motor, indices_val_motor = next(p for p in particiones if p[:2] == (r_visible, f_visible))
    assert set(tabla138.iloc[indices_train_motor].ID_POLIGONO) == ids_train_visible
    assert set(tabla138.iloc[indices_val_motor].ID_POLIGONO) == ids_val_visible
    controles_internos_visibles = []
    internas_visibles = internas.loc[internas.repeticion.eq(r_visible) & internas.pliegue.eq(f_visible)]
    for numero, grupo in internas_visibles.groupby("pliegue_interno"):
        tr_interno = set(grupo.loc[grupo.rol.eq("entrenamiento"), "ID_POLIGONO"])
        va_interno = set(grupo.loc[grupo.rol.eq("validacion"), "ID_POLIGONO"])
        assert tr_interno.isdisjoint(va_interno)
        assert tr_interno | va_interno == ids_train_visible
        assert set(grupo.ID_POLIGONO).isdisjoint(ids_val_visible)
        controles_internos_visibles.append({"interna": numero, "entrenan": len(tr_interno),
                                             "se validan": len(va_interno), "del exterior excluidas": len(ids_val_visible)})
    print("AGC_001 apartada: repetición", r_visible, "pliegue", f_visible,
          "| Entrenan:", len(ids_train_visible), "| Se validan:", len(ids_val_visible))
    display(exterior_visible.loc[exterior_visible.ID_POLIGONO.eq("AGC_001")])
    display(pd.DataFrame(controles_internos_visibles))
    """, tags=["particiones-calculo-visible"])
    texto("""
    **Resultado y límite.** La contención queda comprobada sin usar valores de rendimiento.
    Una estructura anidada limita fuga durante la selección, pero no borra el uso adaptativo
    previo de estos datos ni transforma esta reconstrucción retrospectiva en un estudio confirmatorio.
    """)
    texto("""
    ## 5. Seguir AGC_001 en un pliegue donde se aparta

    **Qué comprobamos.** Buscamos su primera validación guardada, retiramos la parcela
    antes de calcular medias y mostramos el entrenamiento que sustenta la referencia municipal.
    GLOBAL aprende la media del entrenamiento; MUN su media municipal, con GLOBAL si el
    municipio no existe allí. MIX combina **0.5 MUN + 0.5 IDW**: 20 vecinos, potencia 2,
    distancia mínima 1 m, sin buscar parámetros mejores.
    En el mensaje del control de invariancia, «municipio nuevo utiliza GLOBAL» se refiere
    a **MUN**, no a MIX completo: la parte IDW permanece.

    En IDW, los pesos son proporcionales a **1 / max(distancia, 1 m)²**, normalizados
    sobre los vecinos seleccionados. Las distancias usan centroides de área UTM14N.
    """)
    texto("""
    **Abrir MIX: de vecinos a una predicción.** IDW significa ponderación por distancia
    inversa: los centroides cercanos reciben mayor peso. Buscamos los 20 vecinos entre
    **todo el entrenamiento**, no solo el municipio. La tabla muestra distancia en m,
    peso adimensional y **aporte = peso × rendimiento de entrenamiento**, en t/ha.
    Sumamos los aportes y mezclamos con MUN. IDW es un componente, no una cuarta
    referencia evaluada aquí.

    Conservamos el orden de entrenamiento y `np.argsort`. El piso de 1 m evita dividir
    por cero; incluso una distancia cero usa ese piso, no una regla nueva de copiar la
    etiqueta del vecino. Calculamos primero y después contrastamos con la función.
    No abrimos el rendimiento de AGC_001 para construir esta predicción.
    """)
    codigo("""
    entrenamiento_visible = tabla138.loc[tabla138.ID_POLIGONO.isin(ids_train_visible)].copy()
    objetivo_visible = tabla138.loc[tabla138.ID_POLIGONO.eq("AGC_001"),
                                    ["ID_POLIGONO", "Municipio", "x_m", "y_m"]].copy()
    assert "RENDIMIENTO_T_HA" not in objetivo_visible
    y_train_visible = entrenamiento_visible.RENDIMIENTO_T_HA.to_numpy(dtype=float)
    global_visible = y_train_visible.sum() / len(y_train_visible)
    municipio_visible = objetivo_visible.iloc[0].Municipio
    y_municipio_visible = entrenamiento_visible.loc[entrenamiento_visible.Municipio.eq(municipio_visible),
                                                    "RENDIMIENTO_T_HA"].to_numpy(dtype=float)
    mun_visible = y_municipio_visible.sum() / len(y_municipio_visible) if len(y_municipio_visible) else global_visible
    receta_mix_visible = CONFIG["referencias"]["MIX"]
    xy_train_visible = entrenamiento_visible[["x_m", "y_m"]].to_numpy(dtype=float)
    xy_objetivo_visible = objetivo_visible[["x_m", "y_m"]].to_numpy(dtype=float)[0]
    distancias_visibles = np.linalg.norm(xy_train_visible - xy_objetivo_visible, axis=1)
    vecinos_idx = np.argsort(distancias_visibles)[:min(receta_mix_visible["idw_k"], len(entrenamiento_visible))]
    distancias_vecinos = distancias_visibles[vecinos_idx]
    pesos_brutos_visibles = 1 / np.maximum(distancias_vecinos, receta_mix_visible["distancia_minima_m"]) ** receta_mix_visible["idw_potencia"]
    pesos_visibles = pesos_brutos_visibles / pesos_brutos_visibles.sum()
    aportes_visibles = pesos_visibles * y_train_visible[vecinos_idx]
    idw_visible = aportes_visibles.sum()
    mix_visible = (receta_mix_visible["peso_municipal"] * mun_visible +
                   (1 - receta_mix_visible["peso_municipal"]) * idw_visible)
    predicciones_visibles = {"GLOBAL": global_visible, "MUN": mun_visible, "MIX": mix_visible}
    vecinos_visibles = entrenamiento_visible.iloc[vecinos_idx][["ID_POLIGONO", "Municipio", "RENDIMIENTO_T_HA"]].copy()
    vecinos_visibles["distancia_m"] = distancias_vecinos
    vecinos_visibles["peso"] = pesos_visibles
    vecinos_visibles["aporte_t_ha"] = aportes_visibles
    motor_visible = validacion.predecir_referencias(entrenamiento_visible, objetivo_visible)
    for nombre, valor in predicciones_visibles.items():
        np.testing.assert_allclose(valor, motor_visible[nombre][0], atol=1e-12, rtol=0)
    np.testing.assert_allclose(pesos_visibles.sum(), 1., atol=1e-12, rtol=0)
    display(vecinos_visibles.reset_index(drop=True).round(6))
    display(pd.DataFrame([{"referencia": nombre, "cálculo visible (t/ha)": valor,
                           "motor (t/ha)": motor_visible[nombre][0]} for nombre, valor in predicciones_visibles.items()]).round(6))
    print("GLOBAL usa", len(y_train_visible), "etiquetas; MUN usa", len(y_municipio_visible),
          "| Componente IDW:", idw_visible)
    """, tags=["referencias-calculo-visible"])
    codigo(
        """
    PARCELA = "AGC_001"
    primer_validacion = externas.loc[externas.ID_POLIGONO.eq(PARCELA) & externas.rol.eq("validacion")].sort_values(
        ["repeticion", "pliegue"]
    ).iloc[0]
    r_demo, f_demo = int(primer_validacion.repeticion), int(primer_validacion.pliegue)
    _, _, tr_demo, va_demo = next(p for p in particiones if p[:2] == (r_demo, f_demo))
    a_demo = tabla138.iloc[tr_demo].copy()
    t_demo = tabla138.iloc[va_demo].drop(columns="RENDIMIENTO_T_HA").copy()
    assert PARCELA not in set(a_demo.ID_POLIGONO) and PARCELA in set(t_demo.ID_POLIGONO)
    pred_demo = validacion.predecir_referencias(a_demo, t_demo)
    posicion_demo = t_demo.ID_POLIGONO.tolist().index(PARCELA)
    municipio_demo = t_demo.iloc[posicion_demo].Municipio
    entrenamiento_municipal = a_demo.loc[a_demo.Municipio.eq(municipio_demo)]
    media_global_demo = float(a_demo.RENDIMIENTO_T_HA.mean())
    media_municipal_demo = float(entrenamiento_municipal.RENDIMIENTO_T_HA.mean()) if len(entrenamiento_municipal) else media_global_demo
    print("Parcela apartada:", PARCELA, "| Repetición:", r_demo, "| Pliegue:", f_demo)
    print("Entrenamiento:", len(a_demo), "| Validación:", len(t_demo), "| Municipio:", municipio_demo)
    display(entrenamiento_municipal[["ID_POLIGONO", "Municipio", "RENDIMIENTO_T_HA"]])
    assert np.isclose(pred_demo["GLOBAL"][posicion_demo], media_global_demo, atol=1e-12, rtol=0)
    assert np.isclose(pred_demo["MUN"][posicion_demo], media_municipal_demo, atol=1e-12, rtol=0)
    observado_demo = float(tabla138.set_index("ID_POLIGONO").loc[PARCELA, "RENDIMIENTO_T_HA"])
    display(pd.DataFrame([{"referencia": nombre, "predicho_t_ha": valores[posicion_demo],
                           "observado_t_ha": observado_demo, "error_t_ha": valores[posicion_demo] - observado_demo}
                          for nombre, valores in pred_demo.items()]).round(6))
    """,
        tags=["parcela-apartada"],
    )
    codigo(
        """
    # Control sintético y control real: modificar etiquetas de validación no cambia predicciones.
    a_sintetico = pd.DataFrame({"Municipio": ["A", "A", "B"], "x_m": [0., 3., 9.],
                                "y_m": [0., 0., 0.], "RENDIMIENTO_T_HA": [1., 5., 8.]})
    t_sintetico = pd.DataFrame({"Municipio": ["A", "N"], "x_m": [1., 8.], "y_m": [0., 0.],
                                "RENDIMIENTO_T_HA": [999., 999.]})
    antes = validacion.predecir_referencias(a_sintetico, t_sintetico)
    despues = validacion.predecir_referencias(a_sintetico, t_sintetico.assign(RENDIMIENTO_T_HA=-999.))
    for nombre in antes:
        np.testing.assert_array_equal(antes[nombre], despues[nombre])
    np.testing.assert_allclose(antes["MUN"], [3., 14. / 3.], atol=1e-12, rtol=0)
    t_modificado = t_demo.assign(RENDIMIENTO_T_HA=12345.)
    for nombre, prediccion in validacion.predecir_referencias(a_demo, t_modificado).items():
        np.testing.assert_array_equal(prediccion, pred_demo[nombre])
    print("Invariancia a etiquetas de validación: comprobada; municipio nuevo utiliza GLOBAL.")
    """,
        tags=["invariancia-validacion"],
    )
    texto("""
    **Decisión y límite.** El observado se utiliza después de predecir para calcular error.
    La receta municipal nunca incorpora a la parcela apartada. Estas comprobaciones
    demuestran una propiedad del cálculo; no certifican por sí solas ausencia de toda fuga
    ni que la ubicación mantenga su utilidad en otras regiones o campañas.
    """)
    texto("""
    ## 6. Construir predicciones fuera de muestra verificables

    **Qué comprobamos y cómo.** Repetimos las tres recetas en las 50 particiones externas,
    guardando en memoria modelo, repetición, pliegue, ID, observado y predicho, media y
    tamaños del entrenamiento. La bandera municipal usa únicamente pertenencia de grupos.

    Cada referencia genera **138 × 10 = 1,380 predicciones OOF**; tres referencias suman
    **4,140** filas. Siguen siendo **138 parcelas**, no 1,380 casos independientes.

    **OOF** (*out-of-fold*) significa fuera del pliegue que ajustó la referencia:
    conocemos la etiqueta para evaluar, pero no la usamos en ese ajuste. No significa
    fuera de todo el desarrollo ni borra decisiones adaptativas anteriores.
    """)
    codigo(
        """
    oof = validacion.construir_oof(tabla138, externas)
    resumen_oof = validacion.validar_oof(oof, externas)
    assert len(oof) == 4140 and oof.groupby("modelo").size().eq(1380).all()
    assert oof.ID_POLIGONO.nunique() == 138
    display(pd.DataFrame([resumen_oof]))
    display(oof.loc[oof.ID_POLIGONO.eq(PARCELA) & oof.repeticion.eq(r_demo),
                    ["modelo", "repeticion", "pliegue", "ID_POLIGONO", "observado", "predicho",
                     "ref_media_entrenamiento", "n_entrenamiento", "n_validacion", "municipio_visto"]].round(6))
    """,
        tags=["construir-oof"],
    )
    texto("""
    **Abrir una fila OOF.** Para AGC_001 unimos la predicción ya calculada con su
    observado, únicamente para medir el error. La clave es **modelo + repetición +
    pliegue + ID**. Construimos sus tres filas y las contrastamos con `construir_oof`.
    Después contamos sus diez apariciones por referencia: es la misma parcela con
    distintos entrenamientos, no diez parcelas nuevas. Esta demostración no alimenta
    la tabla OOF usada para puntuar.
    """)
    codigo("""
    assert (r_demo, f_demo) == (r_visible, f_visible)
    filas_oof_visibles = pd.DataFrame([
        {"modelo": nombre, "repeticion": r_visible, "pliegue": f_visible, "ID_POLIGONO": "AGC_001",
         "observado": observado_demo, "predicho": valor}
        for nombre, valor in predicciones_visibles.items()
    ])
    claves_visibles = ["modelo", "repeticion", "pliegue", "ID_POLIGONO"]
    filas_oof_motor = oof.loc[oof.ID_POLIGONO.eq("AGC_001") & oof.repeticion.eq(r_visible) &
                              oof.pliegue.eq(f_visible), filas_oof_visibles.columns]
    pd.testing.assert_frame_equal(filas_oof_visibles.set_index(claves_visibles).sort_index(),
                                   filas_oof_motor.set_index(claves_visibles).sort_index(),
                                   check_exact=False, atol=1e-12, rtol=0)
    display(filas_oof_visibles.round(6))
    apariciones_visibles = oof.groupby(["modelo", "ID_POLIGONO"]).size()
    assert apariciones_visibles.eq(10).all()
    display(apariciones_visibles.xs("AGC_001", level="ID_POLIGONO").rename("predicciones de esta misma parcela"))
    """, tags=["oof-fila-visible"])
    texto("""
    **Resultado y límite.** Las claves corresponden exactamente a las validaciones
    guardadas. Las repeticiones comparten parcelas y entrenamientos; no permiten tratar
    sus resultados como réplicas independientes de un experimento de campo.
    """)
    texto("""
    ## 7. Puntuar los errores originales: FULL138

    **Qué comprobamos.** Sobre las 1,380 predicciones de cada referencia calculamos:

    - **RMSE = √media((predicho − observado)²)**, en t/ha.
    - **MAE = media(|predicho − observado|)**, en t/ha.
    - **R² = 1 − Σ(error²) / Σ(observado − media evaluada)²**, adimensional.

    La media del denominador de R² pertenece al conjunto evaluado. No promediamos
    primero las diez predicciones de una parcela ni mezclamos medias de métricas de pliegues.
    FULL138 evalúa todas las parcelas etiquetadas con la agregación histórica agrupada.
    """)
    codigo(
        """
    metricas_full = validacion.resumen_metricas(oof, escenario="FULL138")
    assert metricas_full.n_parcelas.eq(138).all() and metricas_full.n_oof.eq(1380).all()
    display(metricas_full.round(6))
    global_oof = oof.loc[oof.modelo.eq("GLOBAL")]
    sse_global = float(((global_oof.predicho - global_oof.observado) ** 2).sum())
    sse_media_train = float(((global_oof.ref_media_entrenamiento - global_oof.observado) ** 2).sum())
    habilidad_vs_media_train = 1 - sse_global / sse_media_train
    assert np.isclose(habilidad_vs_media_train, 0., atol=1e-12, rtol=0)
    assert metricas_full.set_index("modelo").loc["GLOBAL", "R2"] < 0
    assert metricas_full.sort_values("RMSE").modelo.tolist() == metricas_full.sort_values("R2", ascending=False).modelo.tolist()
    print("R² estándar GLOBAL:", metricas_full.set_index("modelo").loc["GLOBAL", "R2"])
    print("Habilidad de GLOBAL frente a su media de entrenamiento:", habilidad_vs_media_train)
    orden_refs = ["GLOBAL", "MUN", "MIX"]
    colores = ["#999999", "#356f91", "#b9683a"]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.7))
    valores = metricas_full.set_index("modelo").loc[orden_refs]
    for ax, metrica in zip(axes, ["RMSE", "MAE"]):
        barras = ax.bar(orden_refs, valores[metrica], color=colores)
        ax.bar_label(barras, fmt="%.4f", padding=3, fontsize=9)
        ax.set(ylabel="t/ha", title=metrica, ylim=(0, float(valores[metrica].max()) * 1.18))
    fig.suptitle("FULL138: mismas 1,380 predicciones OOF por referencia", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, .92)); plt.show()
    """,
        tags=["metricas-full"],
    )
    texto("""
    **Abrir las métricas: errores, no una función sin explicación.** Conservamos las
    1,380 filas de cada referencia. De cada error salen su valor absoluto y cuadrado;
    sus medias producen MAE y RMSE. Para R² calculamos SSE (suma de error cuadrático)
    y SST (variación de los observados respecto a su propia media evaluada).
    La tabla muestra los primeros errores de MIX; la suma usa **todas** sus filas.
    Si SST ≤ 10⁻¹², la receta devuelve NaN: por ejemplo, evaluar diez predicciones
    de una sola parcela no define R² porque su observado no cambia.
    """)
    codigo("""
    metricas_visibles = []
    for nombre, grupo in oof.groupby("modelo", sort=False):
        y_visible = grupo.observado.to_numpy(dtype=float)
        p_visible = grupo.predicho.to_numpy(dtype=float)
        errores_visibles = p_visible - y_visible
        sse_visible = (errores_visibles ** 2).sum()
        sst_visible = ((y_visible - y_visible.mean()) ** 2).sum()
        metricas_visibles.append({"modelo": nombre, "n_oof": len(grupo),
                                  "RMSE": np.sqrt((errores_visibles ** 2).mean()),
                                  "MAE": np.abs(errores_visibles).mean(),
                                  "R2": 1 - sse_visible / sst_visible if sst_visible > 1e-12 else np.nan})
    metricas_visibles = pd.DataFrame(metricas_visibles).set_index("modelo")
    control_metricas_visibles = metricas_full.set_index("modelo").loc[metricas_visibles.index]
    np.testing.assert_allclose(metricas_visibles[["RMSE", "MAE", "R2"]].to_numpy(dtype=float),
                               control_metricas_visibles[["RMSE", "MAE", "R2"]].to_numpy(dtype=float),
                               atol=1e-12, rtol=0)
    assert metricas_visibles.n_oof.eq(control_metricas_visibles.n_oof).all()
    errores_muestra = oof.loc[oof.modelo.eq("MIX"), ["repeticion", "pliegue", "ID_POLIGONO", "observado", "predicho"]].head(6).copy()
    errores_muestra["error_t_ha"] = errores_muestra.predicho - errores_muestra.observado
    errores_muestra["absoluto_t_ha"] = errores_muestra.error_t_ha.abs()
    errores_muestra["cuadrado_t2_ha2"] = errores_muestra.error_t_ha ** 2
    display(errores_muestra.round(6))
    display(metricas_visibles.round(6))
    """, tags=["metricas-calculo-visible"])
    texto("""
    **Por qué no promediamos antes de puntuar.** Este ejemplo es **inventado**:
    dos parcelas, dos repeticiones y errores de +1/−1. Al promediar sus predicciones,
    esos errores se cancelan y el resultado cambia. Promediar sería evaluar otra
    regla de predicción, no el mismo procedimiento histórico. No usamos este ejemplo
    para afirmar cuánto cambiarían las métricas reales ni para crear un candidato.
    """)
    codigo("""
    ejemplo_promedios = pd.DataFrame({"parcela": ["A", "B", "A", "B"], "repeticion": [0, 0, 1, 1],
                                      "observado": [1., 3., 1., 3.], "predicho": [0., 4., 2., 2.]})
    errores_sinteticos = ejemplo_promedios.predicho - ejemplo_promedios.observado
    rmse_antes_promediar = np.sqrt((errores_sinteticos ** 2).mean())
    promedios_sinteticos = ejemplo_promedios.groupby("parcela").agg(observado=("observado", "first"),
                                                                    predicho=("predicho", "mean"))
    rmse_despues_promediar = np.sqrt(((promedios_sinteticos.predicho - promedios_sinteticos.observado) ** 2).mean())
    assert rmse_antes_promediar == 1. and rmse_despues_promediar == 0.
    display(ejemplo_promedios)
    display(promedios_sinteticos)
    print("RMSE de los errores individuales:", rmse_antes_promediar,
          "| RMSE después de cancelar errores al promediar:", rmse_despues_promediar)
    """, tags=["agregacion-sintetica-visible"])
    texto("""
    **Interpretación.** GLOBAL puede tener R² estándar negativo aunque su habilidad
    frente a la media del entrenamiento valga cero por construcción: son denominadores
    distintos. Con los mismos observados y agregación agrupada, menor RMSE equivale a
    mayor R² porque su denominador es fijo; no son dos evidencias predictivas independientes.
    MAE sí puede preferir MUN mientras RMSE prefiere MIX. Ese intercambio no selecciona
    un modelo final ni resuelve el criterio oficial de FIRA.
    """)
    texto("""
    ## 8. Separar municipios vistos: SEEN135

    **Qué comprobamos y cómo.** SEEN conserva las mismas predicciones OOF y todos los
    entrenamientos originales, pero puntúa únicamente validaciones cuyo municipio
    estaba presente en entrenamiento. La máscara se define sin rendimiento y es igual
    para las tres referencias. No reajustamos sobre 135 parcelas ni cambiamos FULL138.

    Revisamos también cobertura municipal de las 59 parcelas ocultas para describir
    su escenario, sin generar predicciones. Compartir municipio no garantiza compartir
    dificultad ni tener evidencia suficiente para una parcela particular.
    """)
    codigo(
        """
    metricas_seen = validacion.resumen_metricas(oof, escenario="SEEN135")
    oof_seen = oof.loc[oof.municipio_visto]
    assert oof_seen.ID_POLIGONO.nunique() == 135
    assert metricas_seen.n_parcelas.eq(135).all() and metricas_seen.n_oof.eq(1350).all()
    display(metricas_seen.round(6))
    removidas = oof.loc[oof.modelo.eq("GLOBAL") & ~oof.municipio_visto]
    display(removidas.groupby(["ID_POLIGONO", "Municipio"]).size().rename("OOF excluidas por referencia").reset_index())
    assert set(removidas.ID_POLIGONO) == {"AGC_047", "AGC_048", "AGC_164"}
    assert len(removidas) == 30
    conteos_municipales = pd.concat([
        tabla138.groupby("Municipio").size().rename("etiquetadas"),
        ocultas.groupby("Municipio").size().rename("ocultas"),
        removidas.groupby("Municipio").size().rename("OOF excluidas por referencia"),
    ], axis=1).fillna(0).astype(int).reset_index()
    display(conteos_municipales)
    assert ocultas.Municipio.isin(set(tabla138.Municipio)).all()
    print("Ocultas con municipio representado en las etiquetas:", len(ocultas), "de 59")
    display(meta.loc[meta.ID_POLIGONO.isin(["AGC_048", "AGC_120"]), ["ID_POLIGONO", "Municipio", "CONJUNTO"]])
    """,
        tags=["escenarios-full-seen"],
    )
    texto("""
    **Abrir la máscara, sin elegir por error.** Comparamos la primera validación de
    AGC_001 y la de **AGC_048**, la única etiqueta de Nanacamilpa. Solo contamos otras
    etiquetas de su municipio en el entrenamiento: no miramos sus valores ni el error
    para incluirlas en SEEN. Contrastamos esta pertenencia con la bandera OOF.

    Si falta el municipio, **MUN** vuelve a GLOBAL; **MIX** conserva su componente
    IDW, por lo que no tiene que ser igual a GLOBAL. FULL138 conserva esos casos;
    SEEN135 los excluye al puntuar, sin reentrenar. Que la entrega tenga municipios
    representados no garantiza que este filtro estime su error.
    """)
    codigo("""
    pertenencias_visibles = []
    for id_mascara in ["AGC_001", "AGC_048"]:
        fila_asignada = externas.loc[externas.ID_POLIGONO.eq(id_mascara) & externas.rol.eq("validacion")].sort_values(
            ["repeticion", "pliegue"]).iloc[0]
        r_mascara, f_mascara = int(fila_asignada.repeticion), int(fila_asignada.pliegue)
        ids_mascara_train = set(externas.loc[externas.repeticion.eq(r_mascara) & externas.pliegue.eq(f_mascara)
                                            & externas.rol.eq("entrenamiento"), "ID_POLIGONO"])
        municipio_mascara = tabla138.set_index("ID_POLIGONO").loc[id_mascara, "Municipio"]
        n_municipales = int((tabla138.ID_POLIGONO.isin(ids_mascara_train) & tabla138.Municipio.eq(municipio_mascara)).sum())
        visto_visible = n_municipales > 0
        filas_mascara_motor = oof.loc[oof.ID_POLIGONO.eq(id_mascara) & oof.repeticion.eq(r_mascara) & oof.pliegue.eq(f_mascara)]
        assert len(filas_mascara_motor) == 3 and filas_mascara_motor.municipio_visto.eq(visto_visible).all()
        pertenencias_visibles.append({"parcela": id_mascara, "municipio": municipio_mascara,
                                       "repetición": r_mascara, "pliegue": f_mascara,
                                       "etiquetas municipales en entrenamiento": n_municipales,
                                       "municipio visto": visto_visible,
                                       "entra en FULL138": True, "entra en SEEN135": visto_visible})
    display(pd.DataFrame(pertenencias_visibles))
    display(pd.concat([metricas_full, metricas_seen])[['modelo', 'escenario', 'n_parcelas', 'n_oof']])
    """, tags=["escenario-mascara-visible"])
    texto("""
    **Resultado y límite.** Las 30 exclusiones por referencia corresponden a AGC_047
    (Tepeapulco), AGC_048 (Nanacamilpa) y AGC_164 (Apan), diez veces cada una.
    Las 59 ocultas tienen municipios representados entre las etiquetas, pero Nanacamilpa
    tiene una sola etiqueta, AGC_048. Cuando esa parcela se aparta, no queda entrenamiento
    municipal; AGC_120, oculta del mismo municipio, no tiene una situación OOF equivalente.
    SEEN135 es un escenario de lectura adicional, no una garantía sobre el error final.
    """)
    texto("""
    ## 9. Comparar repeticiones de forma pareada y descriptiva

    **Qué comprobamos.** MUN y MIX se puntúan sobre los mismos IDs de cada repetición.
    Restamos métricas MIX−MUN para observar el intercambio entre error cuadrático y
    absoluto. Un valor negativo indica menor error de MIX en esa repetición.

    Las diez diferencias son descriptivas: no calculamos pruebas t, p-valores ni intervalos
    de confianza tratando pliegues o repeticiones como observaciones independientes.
    """)
    codigo(
        """
    metricas_repeticion = validacion.por_repeticion(oof, escenario="FULL138")
    pares_rmse = metricas_repeticion.pivot(index="repeticion", columns="modelo", values="RMSE")
    pares_mae = metricas_repeticion.pivot(index="repeticion", columns="modelo", values="MAE")
    diferencias_pareadas = pd.DataFrame({"MIX_menos_MUN_RMSE": pares_rmse.MIX - pares_rmse.MUN,
                                         "MIX_menos_MUN_MAE": pares_mae.MIX - pares_mae.MUN})
    display(diferencias_pareadas.round(6))
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4))
    for ax, columna, titulo in zip(axes, diferencias_pareadas.columns, ["Cambio de RMSE", "Cambio de MAE"]):
        ax.axhline(0, color="#555555", linewidth=1)
        ax.plot(diferencias_pareadas.index, diferencias_pareadas[columna], "o-", color="#356f91")
        ax.set(title=titulo, xlabel="Repetición", ylabel="MIX − MUN (t/ha)")
        ax.set_xticks(range(10))
    fig.tight_layout(); plt.show()
    print("Repeticiones con menor RMSE de MIX:", int(diferencias_pareadas.MIX_menos_MUN_RMSE.lt(0).sum()), "de 10")
    print("Repeticiones con menor MAE de MIX:", int(diferencias_pareadas.MIX_menos_MUN_MAE.lt(0).sum()), "de 10")
    """,
        tags=["comparacion-pareada"],
    )
    texto("""
    **Decisión y límite.** La consistencia ayuda a describir el intercambio, pero no basta
    para afirmar significancia o seleccionar una solución oficial. Este cuaderno no vuelve
    a puntuar las rondas de experimentos ni modifica sus criterios de avance.
    """)
    texto("""
    ## 10. Reproducir predicciones y métricas históricas

    **Qué comprobamos y por qué.** Después de recalcular abrimos los controles de salida
    de la integración del 21/09/2026. Se validan sus bytes y SHA-256; el contraste exige
    claves OOF, observados y tamaños exactos, con tolerancia absoluta **10⁻⁸ t/ha** para
    predicciones y medias de entrenamiento. Las métricas agrupadas también se contrastan.

    Los nombres descriptivos históricos se corresponden aquí con GLOBAL, MUN y MIX.
    La referencia histórica IDW sola se conserva en el archivo de control, pero no forma
    parte de las tres referencias reconstruidas en este cuaderno.
    """)
    codigo(
        """
    oof_control = leer_insumo("oof_historico", "control_de_salida")
    metricas_control = leer_insumo("metricas_historicas", "control_de_salida")
    tol_control = CONFIG["evaluacion"]["tol_reproduccion_predicciones_t_ha"]
    contraste_oof = validacion.comparar_oof(oof, oof_control, tolerancia=tol_control)
    assert contraste_oof.coincide.all()
    display(contraste_oof)
    metricas_control = metricas_control.loc[metricas_control.modelo.isin(validacion.ALIAS_HISTORICOS_03)].copy()
    metricas_control["modelo"] = metricas_control.modelo.map(validacion.ALIAS_HISTORICOS_03)
    metricas_control = metricas_control.set_index("modelo")
    actuales = metricas_full.set_index("modelo").loc[metricas_control.index]
    assert actuales.n_parcelas.eq(metricas_control.n_parcelas).all()
    assert actuales.n_oof.eq(metricas_control.n_oof).all()
    contraste_metricas = pd.DataFrame([
        {"modelo": modelo, "metrica": metrica,
         "diferencia_absoluta": abs(actuales.loc[modelo, metrica] - metricas_control.loc[modelo, metrica + "_agrupado"]),
         "unidad": "adimensional" if metrica == "R2" else "t/ha"}
        for modelo in metricas_control.index for metrica in ["RMSE", "MAE", "R2"]
    ])
    assert contraste_metricas.diferencia_absoluta.le(1e-8).all()
    display(contraste_metricas)
    """,
        tags=["contraste-historico"],
    )
    texto("""
    **Resultado y límite.** Reproducir estas salidas permite conservar un control común.
    No acredita precisión para otras campañas, municipios nuevos o rendimientos ocultos.
    Las particiones y la evaluación son herramientas de desarrollo del proyecto, no una
    reconstrucción del mecanismo desconocido del split oficial.
    """)
    texto("""
    ## 11. Cierre: controles antes de probar nuevas hipótesis

    **Respuesta comprobable.** Reconstruimos tres referencias sobre las mismas parcelas
    apartadas, validamos la jerarquía de particiones, distinguimos FULL138 y SEEN135 y
    conservamos errores OOF individuales. La celda final comprueba que el ZIP no cambió
    y registra lo recalculado. No exporta tablas ni predicciones por defecto.

    Una referencia es un control, no una ecuación oficial ni un ganador final. Añadir
    variables o un algoritmo complejo no obliga a superar estas referencias; no hacerlo
    tampoco demuestra automáticamente un error de extracción. Habrá que comprobar
    procedimiento, variables y validación antes de interpretar una nueva hipótesis.

    Las operaciones visibles explican vecinos, pesos, filas OOF y métricas; los módulos
    plegados repiten las mismas reglas. Las demostraciones no alimentan las predicciones
    evaluadas ni seleccionan parámetros nuevos. Sus comprobaciones de cálculo no prueban
    causalidad, precisión en las 59 ocultas ni independencia entre repeticiones.

    **Siguiente pregunta:** ¿qué cambio concreto merece probarse manteniendo estos
    controles y la misma población de comparación? Los experimentos se estudiarán
    después, con sus recetas y límites propios, sin anticipar sus resultados aquí.
    """)
    codigo(
        """
    hash_final = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    assert hash_final == hash_inicial == SHA256_DATASET
    resumen_referencias = {
        "notebook": "03_referencias_y_validacion", "fecha_adaptacion": "2026-10-07",
        "particiones_originales": "2026-09-20", "integracion_original": "2026-09-21",
        "fecha_ejecucion_utc": FECHA_EJECUCION_UTC,
        "python": platform.python_version(), "sha256_dataset": hash_final,
        "parcelas": int(len(meta)), "etiquetas": int(len(tabla138)), "por_predecir": int(len(ocultas)),
        "repeticiones": int(resumen_externas["repeticiones"]), "pliegues_externos": int(len(particiones)),
        "pliegues_internos": int(internas[["repeticion", "pliegue", "pliegue_interno"]].drop_duplicates().shape[0]),
        "referencias": int(oof.modelo.nunique()), "oof_por_referencia": int(resumen_oof["filas_por_modelo"]),
        "oof_total": int(len(oof)), "parcelas_seen": int(oof_seen.ID_POLIGONO.nunique()),
        "oof_seen_por_referencia": int(oof_seen.groupby("modelo").size().iloc[0]),
        "referencias_reproducidas": bool(contraste_oof.coincide.all() and contraste_metricas.diferencia_absoluta.le(1e-8).all()),
        # Solo evaluación OOF; las demostraciones e invariancias son controles aparte.
        "ajustes_referencia": int(len(particiones) * oof.modelo.nunique()),
        "modelos_nuevos": 0, "hiperparametros_seleccionados": 0,
        "predicciones_finales_generadas": 0, "tablas_exportadas": 0,
        "archivo_original_inalterado": True,
    }
    zip_fuente.close()
    print(json.dumps(resumen_referencias, ensure_ascii=False, indent=2))
    print("RESUMEN_REFERENCIAS_03_JSON=" + json.dumps(resumen_referencias, ensure_ascii=False, sort_keys=True))
    """,
        tags=["cierre-verificable"],
    )
    texto("""
    ### Fuentes y referencias — APA 7

    Equipo AgroCebada. (2026, 20 de septiembre). *Particiones de desarrollo por parcela*
    [Trabajo interno]. Identidad externa COD-CV-5x10-20260920, CSV incrustado con SHA-256.

    Equipo AgroCebada. (2026, 21 de septiembre). *Integración y conciliación de referencias*
    [Trabajo interno]. GLOBAL, MUN, MIX, particiones internas y salidas históricas
    identificadas por hash. Adaptación y comprobación del cuaderno: 7 de octubre de 2026.

    scikit-learn developers. (s. f.). *Cross-validation: Evaluating estimator performance*.
    https://scikit-learn.org/stable/modules/cross_validation.html

    scikit-learn developers. (s. f.). *Metrics and scoring: Quantifying the quality of predictions*.
    https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics

    Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and
    subsequent selection bias in performance evaluation. *Journal of Machine Learning
    Research, 11*, 2079–2107. https://www.jmlr.org/papers/v11/cawley10a.html

    Estas referencias sustentan separación, métricas y límites de selección; no certifican
    el mecanismo oficial de partición ni extrapolación a nuevos territorios o campañas.
    """)
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata = {
        "kernelspec": {
            "display_name": "Python 3 (AgroCebada uv)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.13"},
        "agrocebada": {
            "id": "REFERENCIAS_03",
            "tipo": "referencias_y_validacion",
            "modo": "recalcular_referencias_fijas_y_evaluacion",
            "crisp_dm": [4, 5],
            "particiones_originales": "2026-09-20",
            "trabajo_original": "2026-09-21",
            "adaptacion": "2026-10-07",
            "verificacion_actual": "2026-10-07",
            "edicion_didactica": "2026-10-08",
            "python_minor": "3.13",
            "python_local": "3.13.13",
            "colab_real_probado": False,
            "modulos_sha256": {nombre: registro["sha256"] for nombre, registro in modulos.items()},
            "config_recetas_sha256": _hash(config_path.read_bytes()),
            "dataset_config_sha256": _hash(dataset_path.read_bytes()),
            "perfil_colab_sha256": _hash(perfil_path.read_bytes()),
            "soporte_base_sha256": _hash(soporte_path.read_bytes()),
            "soporte_derivado_sha256": _hash(soporte_derivado.encode()),
            "dependencias_requeridas": versiones,
            "dataset_sha256": dataset["sha256"],
            "dataset_bytes": dataset["bytes"],
            "drive_file_id": dataset["transporte"]["drive"]["file_id"],
            "insumos": {
                nombre: {k: v for k, v in registro.items() if k != "bytes_zlib_base64"}
                for nombre, registro in insumos.items()
            },
        },
    }
    titulos_colab = {
        "soporte-colab": "Soporte de Colab: entorno y acceso al ZIP",
        "modulos-tecnicos": "Fuentes técnicas incrustadas: auditoría, variables y validación",
        "insumos-tecnicos": "Particiones y controles históricos: integridad de los insumos",
    }
    for cell in notebook.cells:
        if (
            cell.cell_type == "code"
            and cell.metadata.get("jupyter", {}).get("source_hidden") is True
        ):
            tag = next(t for t in cell.metadata.get("tags", []) if t in titulos_colab)
            cell.source = (
                f'# @title {titulos_colab[tag]} {{ display-mode: "form" }}\n' + cell.source
            )
            cell.metadata["cellView"] = "form"
    for n, cell in enumerate(notebook.cells, 1):
        cell.id = f"referencias03-{n:02d}"
    nbformat.validate(notebook)
    return notebook


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("Elige una salida nueva; no se sobrescribe un cuaderno existente")
    notebook = construir(args.raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, args.salida)
    print(f"Cuaderno generado sin ejecutar: {args.salida}")


if __name__ == "__main__":
    main()
