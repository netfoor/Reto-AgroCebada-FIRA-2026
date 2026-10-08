"""Genera NB02 autocontenido sin ejecutar celdas ni modificar sus insumos."""

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


MODULOS = ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite", "fuentes_02")
REQUERIDOS = ("numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown", "rasterio")


def _hash(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def derivar_soporte(texto: str) -> str:
    """Añade una raíz de NB02 sin editar el soporte compartido ni sus guardas."""
    original = 'REQUERIDOS_AUDITORIA = (\n    "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown",\n)'
    derivado = 'REQUERIDOS_AUDITORIA = (\n    "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown", "rasterio",\n)'
    if texto.count(original) != 1:
        raise ValueError("El soporte compartido cambió: revisar la derivación antes de generar NB02.")
    return texto.replace(original, derivado, 1)


def construir(raiz: Path | None = None) -> nbformat.NotebookNode:
    """Incrusta módulos, contratos, perfil y controles; no depende de rutas al ejecutarse."""
    raiz = Path(raiz) if raiz is not None else Path(__file__).resolve().parents[1]
    config_path = raiz / "config/fuentes_02_recetas.json"
    dataset_path = raiz / "config/auditoria_01_dataset.json"
    perfil_path = raiz / "requirements-colab-auditoria.txt"
    soporte_path = raiz / "scripts/colab_soporte.py"
    config_texto = config_path.read_text(encoding="utf-8")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    config = json.loads(config_texto)
    perfil = perfil_path.read_text(encoding="utf-8")
    fijadas = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)", perfil, flags=re.MULTILINE))
    versiones = {nombre: fijadas[nombre] for nombre in REQUERIDOS}
    soporte_base = soporte_path.read_text(encoding="utf-8")
    soporte_derivado = derivar_soporte(soporte_base)
    fuentes = {}
    for nombre in MODULOS:
        contenido = (raiz / "scripts" / f"{nombre}.py").read_bytes()
        fuentes[nombre] = {"source": contenido.decode("utf-8"), "sha256": _hash(contenido)}
    referencias = {}
    for nombre, contrato in config["referencias"].items():
        contenido = (raiz / contrato["ruta_local"]).read_bytes()
        if len(contenido) != contrato["bytes"] or _hash(contenido) != contrato["sha256"]:
            raise ValueError(f"Referencia histórica distinta del contrato: {nombre}")
        referencias[nombre] = {
            "bytes_zlib_base64": base64.b64encode(zlib.compress(contenido, level=9)).decode("ascii"),
            "sha256": contrato["sha256"], "bytes": contrato["bytes"], "origen": contrato["origen"],
        }
    celdas = []

    def texto(contenido):
        celdas.append(nbformat.v4.new_markdown_cell(dedent(contenido).strip()))

    def codigo(contenido, tags=None, oculta=False):
        celda = nbformat.v4.new_code_cell(dedent(contenido).strip())
        if tags:
            celda.metadata["tags"] = tags
        if oculta:
            celda.metadata["jupyter"] = {"source_hidden": True}
        celdas.append(celda)

    texto("""
    # 02. Fuentes a variables: ¿cómo se convierte una parcela en una fila?

    **Pregunta central:** ¿podemos reconstruir y explicar las variables de las 197 parcelas
    desde los archivos originales, conservando significado, unidades, cobertura y faltantes?

    **CRISP-DM:** preparar los datos. **Modo:** recalcular fuentes, variables y controles;
    modelos entrenados: **0**. Las 138 etiquetas se mantienen aparte desde la lectura.

    Seguimos primero **AGC_001** y después repetimos las mismas recetas sobre todas las
    parcelas. Reconstruimos la **tabla integrada del 21 de septiembre de 2026**; los
    resúmenes de Andrea y la integral de Codex se identifican antes de utilizarlos.
    Retomamos los antecedentes de extracción del **1 de octubre de 2026** para
    incorporar controles espaciales aparte. La adaptación y las comprobaciones de
    esta implementación corresponden al **7 de octubre de 2026**;
    no constituye un preregistro ni una nueva ronda experimental.

    El resultado es una tabla de **197 × 539**, un diccionario de **660 variables** y
    una salida separada de noviembre–diciembre. Son variables candidatas y controles,
    no 539 predictores finales ni una demostración de utilidad predictiva.
    """)
    texto("""
    ## 1. Identificar el entorno y las reglas

    **Qué comprobamos y por qué.** Las mismas recetas necesitan archivos y versiones
    identificables. Local utiliza Python **3.13.13**; Colab administra su parche real,
    y el cuaderno exige la serie **3.13**, registra el parche y comprueba ocho bibliotecas.

    `PREPARAR_COLAB = True` prepara únicamente dentro de Colab las bibliotecas requeridas
    cuya versión falta o difiere. El perfil completo procede de uv. Si cambia una
    biblioteca ya cargada, solicita reiniciar manualmente la sesión y ejecutar todas
    las celdas. En local no instala nada. El soporte técnico puede mantenerse contraído.
    """)
    codigo(soporte_derivado, tags=["soporte-colab"], oculta=True)
    celdas[-1].source = soporte_derivado  # Conservar también el salto final del texto identificado.
    codigo("""
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
    assert hashlib.sha256(REQUIREMENTS_COLAB.encode("utf-8")).hexdigest() == __HASH_PERFIL__
    preparacion_entorno = preparar_colab(
        REQUIREMENTS_COLAB, en_colab=EN_COLAB, habilitar=PREPARAR_COLAB,
    )
    print("Preparación:", preparacion_entorno["estado"])
    """.replace("__PERFIL__", repr(perfil)).replace("__VERSIONES__", repr(versiones)).replace(
        "__HASH_PERFIL__", repr(_hash(perfil_path.read_bytes()))), tags=["preparar-colab"])
    codigo("""
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
    import numpy as np
    import pandas as pd
    from IPython.display import display
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable
    from matplotlib.patches import Polygon as ParchePoligono
    from matplotlib.ticker import MaxNLocator

    FECHA_EJECUCION_UTC = datetime.now(timezone.utc).isoformat()
    tabla_entorno = pd.DataFrame([
        {"biblioteca": nombre, "esperada": version, "instalada": metadata.version(nombre)}
        for nombre, version in VERSIONES.items()
    ])
    assert sys.version_info[:2] == (3, 13)
    assert tabla_entorno.esperada.eq(tabla_entorno.instalada).all(), "Prepara el perfil requerido."
    print("Python:", platform.python_version(), "| Ejecución UTC:", FECHA_EJECUCION_UTC)
    display(tabla_entorno)
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    """, tags=["entorno"])
    codigo("""
    CONFIG_JSON = __CONFIG__
    assert hashlib.sha256(CONFIG_JSON.encode("utf-8")).hexdigest() == __HASH_CONFIG__
    CONFIG = json.loads(CONFIG_JSON)
    display(pd.DataFrame([
        {"regla": "Ventana del ciclo", "valor": str(CONFIG["ventana_objetivo"])},
        {"regla": "Nubosidad máxima", "valor": str(CONFIG["nubosidad_max_por_sensor"])},
        {"regla": "LAI negativo", "valor": CONFIG["lai_negativos"]},
        {"regla": "Hueco máximo integral", "valor": str(CONFIG["integral_hueco_max_dias"]) + " días"},
        {"regla": "Histórico", "valor": "Abril–octubre de 2022, 2023 y 2024, separados"},
        {"regla": "Postciclo", "valor": "Noviembre–diciembre de 2025, separado; admisibilidad pendiente"},
    ]))
    """.replace("__CONFIG__", repr(config_texto)).replace(
        "__HASH_CONFIG__", repr(_hash(config_path.read_bytes()))), tags=["config-recetas"])
    texto("""
    **Resultado e interpretación.** La receta histórica no impone umbral de nubes:
    `None` significa que se exige índice presente. Una nube desconocida no es cero.
    LAI negativo se conserva y se identifica con una bandera. Abril–octubre es una
    ventana de calendario documentada; no revela siembra o cosecha de cada parcela.
    La admisibilidad de noviembre–diciembre sigue pendiente, sin convertir esta
    separación en una regla agronómica universal.

    Las siguientes celdas contienen los módulos y los controles históricos completos,
    con hashes. No hace falta Git, otro notebook, una bóveda ni módulos de otra máquina.
    """)
    codigo("""
    FUENTES_MODULOS = __FUENTES__
    for nombre, registro in FUENTES_MODULOS.items():
        fuente = registro["source"]
        assert hashlib.sha256(fuente.encode("utf-8")).hexdigest() == registro["sha256"]
        modulo = types.ModuleType(nombre)
        modulo.__file__ = "<notebook02/" + nombre + ".py>"
        sys.modules[nombre] = modulo
        exec(compile(fuente, modulo.__file__, "exec"), modulo.__dict__)
    auditoria = sys.modules["auditoria_01"]
    geo02 = sys.modules["fuentes_02_geo"]
    sat02 = sys.modules["fuentes_02_satelite"]
    fuentes02 = sys.modules["fuentes_02"]
    SHA256_DATASET = auditoria.SHA256_DATASET
    """.replace("__FUENTES__", repr(fuentes)), tags=["modulos-tecnicos"], oculta=True)
    codigo("""
    # Controles de salida; jamás se utilizan para construir una variable.
    REFERENCIAS_INCRUSTADAS = __REFERENCIAS__

    def leer_referencia(nombre):
        registro = REFERENCIAS_INCRUSTADAS[nombre]
        comprimido = base64.b64decode(registro["bytes_zlib_base64"], validate=True)
        decoder = zlib.decompressobj()
        contenido = decoder.decompress(comprimido, registro["bytes"] + 1)
        if (len(contenido) != registro["bytes"] or not decoder.eof
                or decoder.unused_data or decoder.unconsumed_tail):
            raise ValueError("Referencia comprimida incompleta o fuera del límite de bytes")
        if hashlib.sha256(contenido).hexdigest() != registro["sha256"]:
            raise ValueError("La referencia no coincide con su SHA-256")
        return pd.read_csv(io.BytesIO(contenido), encoding="utf-8-sig")
    """.replace("__REFERENCIAS__", repr(referencias)), tags=["referencias-tecnicas"], oculta=True)
    texto("""
    ## 2. Leer originales y separar etiquetas

    **Qué comprobamos.** El ZIP original del reto, su tamaño y SHA-256, las rutas
    internas y la unión por ID. El rendimiento sale inmediatamente a `etiquetas`;
    las recetas reciben geometrías, índices y clima, nunca el objetivo.

    En Colab se puede descargar el ZIP compartido por Fortino si falta una copia local;
    el ID corresponde al dataset. Una copia existente incorrecta se rechaza. La descarga
    se valida antes de aceptarse y no usa cookies, publica archivos ni cambia permisos.
    """)
    codigo("""
    RUTA_DATASET = None  # Si hace falta, indica la ruta de una copia local del ZIP original.
    ID_DRIVE_DATASET = __DRIVE_ID__
    DESCARGAR_DATASET = EN_COLAB
    candidatos = [Path("data/raw/DataSet.zip"), Path("../data/raw/DataSet.zip"),
                  Path("DataSet.zip"), Path("/content/DataSet.zip")]
    ruta_dataset = (Path(RUTA_DATASET).expanduser() if RUTA_DATASET is not None
                    else next((ruta for ruta in candidatos if ruta.is_file()), None))
    if ruta_dataset is None:
        ruta_dataset = Path("/content/DataSet.zip") if EN_COLAB else Path("data/raw/DataSet.zip")
    ruta_dataset = obtener_dataset(
        ruta_dataset, file_id=ID_DRIVE_DATASET, sha256_esperado=SHA256_DATASET,
        bytes_esperados=29_687_194, permitir_descarga=DESCARGAR_DATASET,
    )
    hash_inicial = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    zip_fuente = auditoria.cargar_zip(ruta_dataset)
    fuentes = fuentes02.cargar_fuentes(zip_fuente)
    meta, etiquetas = fuentes["metadatos"], fuentes["etiquetas"]
    basico, pro = fuentes["basico"], fuentes["pro"]
    geoms, crs_geoms = fuentes["geometrias"], fuentes["crs_geometrias"]
    ids = meta.ID_POLIGONO.tolist()
    assert len(ids) == 197 and len(set(ids)) == 197 and len(etiquetas) == 138
    assert "RENDIMIENTO_T_HA" not in meta
    assert meta.CONJUNTO.value_counts().to_dict() == {"ENTRENAMIENTO": 138, "PREDICCION": 59}
    print("ZIP:", ruta_dataset.name, "| Bytes:", ruta_dataset.stat().st_size, "| SHA-256:", hash_inicial)
    display(meta.groupby("CONJUNTO").size().rename("parcelas").reset_index())
    print("Etiquetas separadas:", len(etiquetas), "| Por predecir:", 197 - len(etiquetas))
    """.replace("__DRIVE_ID__", repr(dataset["transporte"]["drive"]["file_id"])), tags=["acceso-dataset"])
    texto("""
    **Decisión y límite.** Unimos por ID, conservando 197 parcelas y 138 etiquetas aparte.
    `CONJUNTO` y la grafía del cultivo son metadatos que se excluyen como predictores.
    Estado, municipio y coordenadas conservan procedencia; su eventual uso predictivo
    requiere una evaluación posterior. Las fechas y píxeles no crean nuevas etiquetas.
    """)
    texto("""
    ## 3. Seguir el polígono de AGC_001

    **Qué comprobamos y cómo.** Proyectamos la geometría de WGS84 a **EPSG:32614**,
    calculamos área en metros cuadrados y centroide de área, y dividimos el área entre
    10,000 para obtener hectáreas. El área entregada y la geométrica responden a fuentes
    distintas; calculamos su diferencia sin obligarlas a coincidir.
    """)
    codigo("""
    PARCELA = "AGC_001"
    meta_uno = meta.loc[meta.ID_POLIGONO.eq(PARCELA)].copy()
    geom_uno = {PARCELA: geoms[PARCELA]}
    geometria_utm = geo02.proyectar_geometrias(geom_uno, crs_geoms, 32614)[PARCELA]

    def dibujar_borde(ax, geometria, **opciones):
        partes = [geometria] if geometria.geom_type == "Polygon" else list(geometria.geoms)
        for parte in partes:
            ax.plot(*parte.exterior.xy, **opciones)
            for anillo in parte.interiors:
                ax.plot(*anillo.xy, **opciones)

    fig, ax = plt.subplots(figsize=(6.5, 4))
    dibujar_borde(ax, geometria_utm, color="#225f37", linewidth=2)
    ax.scatter([geometria_utm.centroid.x], [geometria_utm.centroid.y], color="#b34b16", label="Centroide de área")
    ax.set(xlabel="Este (m), EPSG:32614", ylabel="Norte (m), EPSG:32614", title="AGC_001: polígono y centroide UTM")
    ax.set_aspect("equal"); ax.ticklabel_format(style="plain", useOffset=False)
    ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    fig.tight_layout(); plt.show()
    display(meta_uno[["ID_POLIGONO", "AREA_HA", "area_geom_ha", "dif_area_pct", "x_m", "y_m",
                      "geom_valida_original", "geom_vertices_repetidos"]].round(6))
    """, tags=["parcela-geometria"])
    texto("""
    **Resultado e interpretación.** La tabla conserva ambas áreas y explicita el CRS del
    centroide. La diferencia no demuestra un error de medición ni una causa agronómica.
    No reparamos polígonos, densificamos bordes ni ajustamos coordenadas a una rejilla.
    """)
    texto("""
    ## 4. Ubicar celdas, esquinas y centros

    **Qué comprobamos.** Los 146 GeoTIFF se leen de ZIP internos en memoria. La malla
    incluye CRS, dimensiones y seis coeficientes de la transformada afín: sus huellas
    exactas evitan reutilizar pesos de una rejilla diferente.

    Un índice de fila/columna identifica una celda, no un punto del polígono. La esquina
    superior izquierda y el centro del píxel tienen coordenadas distintas. Dibujamos
    ambas posiciones y las intersecciones reales de AGC_001 con elevación.
    """)
    codigo("""
    rasters, inventario_rasters = fuentes02.leer_rasters(zip_fuente)
    assert len(rasters) == 146
    mallas = inventario_rasters.drop_duplicates("huella_malla")
    assert len(mallas) == 3
    display(inventario_rasters.groupby("grupo").size().rename("GeoTIFF").reset_index())
    display(mallas[["archivo", "epsg", "width", "height", "transform", "huella_malla"]])
    matrices_clima = np.asarray(inventario_rasters.loc[
        inventario_rasters.grupo.isin(["precipitacion", "temperatura"]), "transform"
    ].tolist(), dtype=float)
    diferencia_afin_clima = float(np.ptp(matrices_clima, axis=0).max())
    print("Diferencia del origen Y entre mallas climáticas (grados):", diferencia_afin_clima)
    assert np.isclose(diferencia_afin_clima, 2.980232238769531e-7, atol=1e-12, rtol=0)
    archivo_elev = "Elevacion_INEGI_CEM4_120m.tif"
    piezas_elev = geo02.piezas_parcela_raster(rasters[archivo_elev], geoms[PARCELA], crs_geoms)
    print("Celda del centroide:", piezas_elev["celda_centroide"], "| CRS:", piezas_elev["metadata"]["epsg"])
    """, tags=["inventario-mallas"])
    codigo("""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    valores_validos = [p["valor"] for p in piezas_elev["piezas"] if p["valido"]]
    norma = Normalize(min(valores_validos), max(valores_validos))
    for numero, pieza in enumerate(piezas_elev["piezas"]):
        color = plt.cm.terrain(norma(pieza["valor"])) if pieza["valido"] else "#d4d4d4"
        ax.add_patch(ParchePoligono(np.asarray(pieza["pixel"].exterior.coords),
                                    facecolor=color, edgecolor="#555555", alpha=.6))
        ax.scatter(*pieza["esquina_ul"], marker="s", s=22, facecolors="none", edgecolors="#b34b16",
                   label="Esquina superior izquierda" if numero == 0 else None)
        ax.scatter(*pieza["centro"], marker="x", s=24, color="#222222",
                   label="Centro del píxel" if numero == 0 else None)
    dibujar_borde(ax, piezas_elev["geometria_raster"], color="#17472a", linewidth=2)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.ticklabel_format(style="plain", useOffset=False)
    ax.set(xlabel="x (m), EPSG:6372", ylabel="y (m), EPSG:6372", title="AGC_001: celdas de elevación de 120 m")
    ax.xaxis.set_major_locator(MaxNLocator(nbins=3))
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, -.25))
    fig.colorbar(ScalarMappable(norm=norma, cmap="terrain"), ax=ax, label="Elevación entregada (m)")
    fig.tight_layout(); plt.show()
    display(pd.DataFrame([{k: pieza[k] for k in ["fila", "col", "valor", "valido", "area_peso",
                                               "peso_valido_normalizado"]}
                          for pieza in piezas_elev["piezas"]]).round(6))
    """, tags=["figura-pixeles"])
    texto("""
    **Resultado y decisión.** Lluvia y temperatura tienen dos mallas distintas;
    elevación y pendiente comparten la misma malla EPSG:6372. El origen Y de las
    mallas climáticas difiere aproximadamente **2.98×10⁻⁷ grados**. La caché se identifica por
    malla y geometrías. Contar varios píxeles no aumenta el número de parcelas ni etiquetas.
    """)
    texto("""
    ## 5. Conservar sensor, promedio de parcela y píxel extremo

    **Qué comprobamos y cómo.** Reconstruimos para AGC_001 los resúmenes por captura
    contrastados con el aporte de **Andrea el 21/09/2026**. Sentinel-2 y Planet aportan
    NDVI en series separadas; Landsat aporta VI6T, cuya definición y escala son distintas.
    La media temporal usa `*_promedio`; el píxel extremo usa `*_max` o `*_min`.
    """)
    codigo("""
    basico_uno = basico.loc[basico.ID_POLIGONO.eq(PARCELA)].copy()
    pro_uno = pro.loc[pro.ID_POLIGONO.eq(PARCELA)].copy()
    ciclo_uno, historico_uno, post_uno = sat02.construir_satelite(basico_uno, pro_uno, [PARCELA], CONFIG)
    fig, axes = plt.subplots(3, 1, figsize=(8, 6), sharex=True)
    filas_sat = []
    for ax, sensor, tabla, indice, nombre in [
        (axes[0], "S2", basico_uno, "ndvi", "Sentinel-2"),
        (axes[1], "PL", pro_uno, "ndvi", "Planet"),
        (axes[2], "LS", basico_uno, "vi6t", "Landsat"),
    ]:
        observaciones = tabla.loc[tabla.sensor.eq(nombre) & tabla.FECHA.between(
            CONFIG["ventana_objetivo"]["inicio"], CONFIG["ventana_objetivo"]["fin"]
        )].sort_values("FECHA")
        ax.plot(observaciones.FECHA, observaciones[f"{indice}_promedio"], ".-", linewidth=1, label="Promedio de parcela")
        parcial = observaciones.loc[observaciones.porcentaje_nubosidad.gt(0)
                                     & observaciones[f"{indice}_promedio"].notna()]
        ax.scatter(parcial.FECHA, parcial[f"{indice}_promedio"], marker="D", s=20,
                   facecolors="none", edgecolors="#b34b16", label="Índice presente y nube parcial")
        ax.set(ylabel=indice.upper(), title=nombre); ax.legend(fontsize=8, loc="upper left")
        p = f"C_{sensor}_{indice}"
        q = f"C_{sensor}_q"
        row = ciclo_uno.loc[PARCELA]
        filas_sat.append({"sensor": nombre, "índice": indice.upper(), "media_por_captura": row[p + "_media"],
                          "pico_promedio": row[p + "_pico_prom"], "píxel_máximo": row[p + "_pixmax"],
                          "capturas_usadas": int(row[p + "_n"]), "filas_ventana": int(row[q + "_filas_ventana"]),
                          "hueco_máximo_días": row[q + "_hueco_max_dias"]})
    fig.tight_layout(); plt.show()
    display(pd.DataFrame(filas_sat).round(6))
    assert ciclo_uno.loc[PARCELA, "C_PL_ndvi_pixmax"] == .993
    assert ciclo_uno.loc[PARCELA, "C_PL_ndvi_pico_prom"] == .836
    extremo = pro_uno.loc[pro_uno.FECHA.eq(pd.Timestamp("2025-10-21")),
                          ["FECHA", "ndvi_promedio", "ndvi_max", "porcentaje_nubosidad"]]
    display(extremo)
    assert extremo.ndvi_max.eq(.993).all() and extremo.porcentaje_nubosidad.eq(0).all()
    """, tags=["satelite-parcela"])
    texto("""
    **Resultado y límite.** Planet muestra un pico del promedio de **0.836 el 2 de
    septiembre** y un píxel extremo de **0.993 el 21 de octubre**. La nubosidad registrada
    de esa última captura es **0 %**; no atribuimos el extremo a una nube.
    `std_media` es media de la heterogeneidad intraparcela entregada por captura,
    no dispersión temporal. Los índices ausentes permanecen ausentes, nunca cero.
    """)
    texto("""
    ## 6. Distinguir media por captura, media mensual e integral

    **Qué comprobamos.** Un mes con más capturas pesa más en la media por captura.
    Para explicar la media mensual ponderada por días, primero obtenemos una media
    por mes y después ponderamos esas medias por **30, 31, 30, 31, 31, 30 y 31 días**.
    El diagnóstico queda fuera de las 539 columnas: no sustituye una receta histórica.

    La integral parcial de **Codex**, incorporada en la integración del 21/09/2026,
    suma trapecios entre fechas reales, acepta huecos de hasta 30 días y no extrapola.
    Abril–octubre contiene **214 días calendario**, pero entre sus extremos transcurren
    **213 días**. Los días cubiertos por observaciones pueden ser todavía menos.
    """)
    codigo("""
    diagnostico_temporal, mensual_planet = sat02.diagnosticos_media_vs_tiempo(
        pro_uno, "PL", "ndvi", [PARCELA], "2025-04-01", "2025-10-31",
        nube_max=CONFIG["nubosidad_max_por_sensor"]["PL"], max_gap=CONFIG["integral_hueco_max_dias"],
    )
    display(mensual_planet[["ID_POLIGONO", "mes", "media", "n", "dias_mes"]].round(6))
    display(diagnostico_temporal.round(6))
    assert np.isclose(diagnostico_temporal.loc[PARCELA, "media_captura"], .40209278350515465, atol=1e-12, rtol=0)
    assert np.isclose(diagnostico_temporal.loc[PARCELA, "media_mensual_por_dias"], .42670903877176214, atol=1e-12, rtol=0)
    assert diagnostico_temporal.loc[PARCELA, "dias_integrados"] == 210
    assert sat02.partial_integral(["2025-04-01", "2025-04-11", "2025-06-30"], [1., 3., 9.]) == (20., 10.)
    assert sat02.partial_integral(["2025-04-01", "2025-05-01", "2025-06-01"], [1., 3., 9.]) == (60., 30.)
    print("Integral sintética: el hueco de 30 días entra y el de 31 queda fuera.")
    """, tags=["diagnostico-temporal"])
    texto("""
    **Interpretación.** Las tres medias responden preguntas diferentes. Ni la media
    mensual ni el cociente integral/días reconstruyen automáticamente el verdadero
    promedio diario. La integral describe los tramos admitidos y conserva el signo del
    índice; no es biomasa. Un mes ausente conserva NaN en los diagnósticos de meses.
    Esta comparación de recetas no utiliza rendimiento ni decide cuál predice mejor.
    """)
    texto("""
    ## 7. Extraer clima por intersecciones de área

    **Qué comprobamos y cómo.** Para cada celda intersectada, usamos el área de su
    intersección con la parcela: **Σ(valor × área válida) / Σ(área válida)**.
    Para clima calculamos esas áreas en EPSG:32614; NoData y máscaras se excluyen.
    Extraemos los **144 meses** disponibles de AGC_001 reutilizando una caché por malla.

    El control por centroide toma la celda bajo el centroide planar del polígono en el
    **CRS del ráster**. No es el centroide UTM de los metadatos reproyectado después.
    Precipitación se acumula sumando mm mensuales; temperaturas se promedian en °C
    ponderando por días de cada mes. No se ajusta la receta con rendimiento.
    """)
    codigo("""
    cache_pesos = {}
    clima_uno_largo = fuentes02.extraer_clima(rasters, geom_uno, crs_geoms, cache=cache_pesos)
    clima_uno = fuentes02.resumir_clima(clima_uno_largo, CONFIG)
    assert len(clima_uno_largo) == 144
    display(clima_uno_largo.loc[clima_uno_largo.anio.eq(2025) & clima_uno_largo.mes.between(4, 10),
                                ["variable", "anio", "mes", "pond", "cent", "n_celdas", "frac_valida"]].round(6))
    display(clima_uno[["clim_prec_ciclo_mm", "clim_prec_ciclo_ctrl_centroide_mm",
                       "clim_tmin_ciclo_C", "clim_tmax_ciclo_C"]].round(6))
    piezas_prec = geo02.piezas_parcela_raster(rasters["PREC_2025_04.tif"], geoms[PARCELA], crs_geoms)
    display(pd.DataFrame([{k: p[k] for k in ["fila", "col", "valor", "valido", "area_peso",
                                           "peso_valido_normalizado"]} for p in piezas_prec["piezas"]]))
    """, tags=["clima-parcela"])
    texto("""
    **Decisión y límite.** La lluvia ponderada queda como valor histórico y el centroide
    viaja como control. Si una parcela toca una sola celda válida, ambos pueden coincidir;
    eso no demuestra que coincidan en todas. La cobertura acompaña al valor y los pesos
    se normalizan sobre área válida, sin tratar NoData como cero.
    """)
    texto("""
    ## 8. Extraer elevación y pendiente con cobertura

    **Qué comprobamos.** Calculamos media y desviación poblacional ponderadas por área,
    mínimo, máximo y rango de las celdas válidas; elevación en metros y pendiente
    entregada en grados. Conservamos la cobertura histórica: área válida dividida
    por área de intersecciones dentro de la malla. Los controles de cobertura respecto
    del área total de parcela quedan aparte.

    La receta histórica de topografía no impone cobertura ≥0.99. Usamos AGC_170 para
    observar qué significa un valor zonal con muy poca cobertura y un centroide sin dato.
    """)
    codigo("""
    topo_uno, controles_topo_uno = fuentes02.extraer_topografia(rasters, geom_uno, crs_geoms, cache=cache_pesos)
    display(controles_topo_uno[["ID_POLIGONO", "variable", "pond", "cent", "min", "max", "std",
                               "n_validos", "frac_valida", "cobertura_total"]].round(6))
    archivo_pend = "Pendiente_INEGI_CEM4_120m_grados.tif"
    control_170 = geo02.extraer_raster(rasters[archivo_pend], {"AGC_170": geoms["AGC_170"]},
                                      crs_geoms, cache=cache_pesos, stats=True)["AGC_170"]
    display(pd.DataFrame([{"ID_POLIGONO": "AGC_170", **control_170}]).round(6))
    assert np.isclose(control_170["frac_valida"], .021, atol=.001, rtol=0)
    assert np.isnan(control_170["cent"]) and np.isfinite(control_170["pond"])
    """, tags=["topografia-parcela"])
    texto("""
    **Resultado y límite.** AGC_170 tiene cobertura de pendiente cercana a **2.1 %**.
    El promedio zonal existe porque hay área con dato, pero el centroide es NaN.
    Un valor calculable no garantiza representar bien toda la parcela. Conservarlo
    reproduce la receta; la bandera evita confundir disponibilidad con calidad suficiente.
    """)
    texto("""
    ## 9. Repetir las recetas sobre las 197 parcelas

    **Qué comprobamos y cómo.** Generalizamos sin cambiar reglas ni unir por posición.
    La caché distingue conjunto de geometrías y malla. La tabla base contiene
    **14 metadatos + 320 satélite del ciclo + 147 históricos + 42 clima + 16 topografía**.
    Incluye la clave ID; el rendimiento nunca entra en estas piezas.

    La historia 2022–2024 se resume por año y sensor; no son nuevas campañas etiquetadas.
    Noviembre–diciembre de 2025 sale a otra tabla: **121 estadísticas y una clave ID**.
    """)
    codigo("""
    ciclo, historico, postciclo = sat02.construir_satelite(basico, pro, ids, CONFIG)
    clima_largo = fuentes02.extraer_clima(rasters, geoms, crs_geoms, cache=cache_pesos)
    clima = fuentes02.resumir_clima(clima_largo, CONFIG)
    topo, controles_topografia = fuentes02.extraer_topografia(rasters, geoms, crs_geoms, cache=cache_pesos)
    tabla_base = fuentes02.ensamblar_variables(meta, ciclo, historico, clima, topo)
    tabla_postciclo = postciclo.reset_index()
    tabla_uno = fuentes02.ensamblar_variables(meta_uno, ciclo_uno, historico_uno, clima_uno, topo_uno)
    assert tabla_base.shape == (197, 539) and tabla_base.ID_POLIGONO.is_unique
    assert tabla_postciclo.shape == (197, 122) and postciclo.shape[1] == 121
    assert len(clima_largo) == 197 * 144 == 28_368
    assert not any("RENDIMIENTO" in c.upper() for c in tabla_base.columns)
    assert not any(c.startswith("P_") for c in tabla_base.columns)
    contraste_uno = fuentes02.comparar_referencia(
        tabla_uno, tabla_base.loc[tabla_base.ID_POLIGONO.eq(PARCELA)]
    )
    assert contraste_uno.coincide.all(), "El recorrido de una parcela difiere de la generalización."
    display(pd.DataFrame({"bloque": ["Metadatos (incluye ID)", "Satélite ciclo", "Satélite histórico", "Clima", "Topografía"],
                          "columnas": [meta.shape[1], ciclo.shape[1], historico.shape[1], clima.shape[1], topo.shape[1]]}))
    vista = ["ID_POLIGONO", "AREA_HA", "C_PL_ndvi_media", "C_PL_ndvi_pico_prom", "C_S2_ndvi_media",
             "clim_prec_ciclo_mm", "topo_elev_media_m", "topo_pend_cobertura"]
    display(tabla_base[vista].head(6).round(6))
    print("Control una parcela ↔ 197:", int(contraste_uno.coincide.sum()), "columnas coincidentes")
    """, tags=["ensamblar-197"])
    texto("""
    **Decisión y límite.** La misma parcela conserva su fila al generalizar. Ningún
    faltante se imputa y ningún índice se selecciona según rendimiento. Las 539
    columnas incluyen clave, metadatos, controles y banderas: su tamaño no es el
    número de predictores de un modelo elegido.
    """)
    texto("""
    ## 10. Explicar cada columna en el diccionario

    **Qué comprobamos.** Para cada variable registramos fuente, sensor, ventana,
    agregación, filtro, unidad, rol, archivo lógico y faltantes. Hay **539 entradas de
    base + 121 estadísticas postciclo = 660**; no repetimos el ID en el segundo bloque.
    Los nombres de archivo identifican productos lógicos, sin exportarlos por defecto.
    """)
    codigo("""
    CAMPOS_DICCIONARIO = ["variable", "bloque", "rol", "fuente", "sensor", "indice", "ventana",
                          "agregacion", "filtro", "unidad", "archivo", "faltantes", "origen"]
    filas_diccionario = []
    for archivo, tabla in [("variables_v0_197.csv", tabla_base),
                           ("postciclo_PENDIENTE_197.csv", postciclo)]:
        for columna in tabla.columns:
            registro = fuentes02.describir_variable(columna, CONFIG)
            registro.update(archivo=archivo, faltantes=int(tabla[columna].isna().sum()),
                            origen="reconstruido desde DataSet.zip (sin Excel procesado)")
            filas_diccionario.append(registro)
    diccionario = pd.DataFrame(filas_diccionario, columns=CAMPOS_DICCIONARIO)
    assert diccionario.shape == (660, 13) and diccionario.variable.is_unique
    assert diccionario.variable.tolist() == list(tabla_base) + list(postciclo)
    assert diccionario.loc[diccionario.bloque.eq("satelite_postciclo"), "rol"].eq("pendiente_admisibilidad").all()
    claves_dic = ["AREA_HA", "C_PL_ndvi_media", "C_PL_ndvi_pico_prom", "C_PL_ndvi_pixmax",
                  "C_PL_ndvi_integral", "C_S2_q_lai_frac_neg", "H2022_S2_ndvi_media",
                  "clim_prec_ciclo_mm", "topo_pend_cobertura", "P_PL_ndvi_media"]
    display(diccionario.set_index("variable").loc[claves_dic,
            ["rol", "fuente", "ventana", "agregacion", "filtro", "unidad", "faltantes"]])
    display(diccionario.groupby(["bloque", "rol"]).size().rename("variables").reset_index())
    display(diccionario.loc[diccionario.faltantes.gt(0), ["variable", "rol", "faltantes"]])
    """, tags=["diccionario-660"])
    texto("""
    **Interpretación.** La procedencia permite distinguir un cálculo reproducible de una
    hipótesis predictiva. La unidad del índice conserva el valor entregado; no lo
    reinterpretamos como biomasa o una medición física nueva. Las banderas y NaN viajan
    con los valores. Postciclo conserva el rol de admisibilidad pendiente.
    """)
    texto("""
    ## 11. Contrastar la reconstrucción con las salidas históricas

    **Qué comprobamos y por qué.** Abrimos ahora los CSV de control incrustados de la
    **tabla integrada del 21/09/2026** y de su postciclo separado. Primero se verifica
    tamaño y SHA-256; después se interpretan los CSV. No alimentan ninguna transformación.

    Comparamos orden de columnas, IDs, textos y máscaras de faltantes. Los conteos
    deben coincidir exactamente; tolerancia absoluta **10⁻⁸** para metadatos, satélite
    y clima, y **10⁻⁴** para topografía, en la unidad de cada columna. Son controles de
    reproducción numérica, no una evaluación predictiva.
    """)
    codigo("""
    referencia_base = leer_referencia("base")
    referencia_postciclo = leer_referencia("postciclo")
    contraste_base = fuentes02.comparar_referencia(tabla_base, referencia_base)
    contraste_postciclo = fuentes02.comparar_referencia(tabla_postciclo, referencia_postciclo)
    assert len(contraste_base) == 538 and len(contraste_postciclo) == 121
    assert contraste_base.coincide.all(), "La base no reproduce el control histórico."
    assert contraste_postciclo.coincide.all(), "El postciclo no reproduce su control histórico."
    display(pd.DataFrame([
        {"producto": "Base", "filas": len(tabla_base), "columnas_con_ID": tabla_base.shape[1],
         "columnas_comparadas_sin_ID": len(contraste_base), "coinciden": int(contraste_base.coincide.sum())},
        {"producto": "Postciclo", "filas": len(tabla_postciclo), "columnas_con_ID": tabla_postciclo.shape[1],
         "columnas_comparadas_sin_ID": len(contraste_postciclo), "coinciden": int(contraste_postciclo.coincide.sum())},
    ]))
    display(contraste_base.sort_values("diferencia_maxima", ascending=False).head(8))
    """, tags=["contraste-referencias"])
    texto("""
    **Resultado y límite.** Una coincidencia muestra que se conservaron las recetas y
    su resultado dentro de tolerancias explícitas. No valida la medición de rendimiento,
    el significado agronómico de cada índice ni la selección de un modelo. Los controles
    modernos de cobertura se conservan aparte de la base histórica reconstruida.
    """)
    texto("""
    ## 12. Cierre: una fila trazable, todavía sin modelo

    **Respuesta comprobable.** Podemos seguir AGC_001 desde geometría y capturas hasta
    sus variables y repetir la operación sobre 197 IDs. El diccionario explica 660
    variables, las etiquetas quedan separadas y el postciclo conserva su propio producto.
    La siguiente celda registra conteos y comprueba otra vez que el ZIP sigue intacto.

    **Siguiente pregunta — NB03:** ¿qué referencias sencillas debemos reconstruir y
    cómo compararlas sobre parcelas no utilizadas para ajustarlas? La utilidad de estas
    variables se estudiará mediante validación; este cuaderno no anticipa sus resultados.
    """)
    codigo("""
    hash_final = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    assert hash_final == hash_inicial == SHA256_DATASET
    resumen_fuentes = {
        "notebook": "02_fuentes_a_variables", "fecha_adaptacion": "2026-10-07",
        "trabajo_original": "2026-09-21", "antecedente_geo": "2026-10-01",
        "verificacion_actual": "2026-10-07",
        "fecha_ejecucion_utc": FECHA_EJECUCION_UTC, "python": platform.python_version(),
        "sha256_dataset": hash_final, "bytes_dataset": int(ruta_dataset.stat().st_size),
        "parcelas": int(len(tabla_base)), "columnas_base": int(tabla_base.shape[1]),
        "columnas_postciclo": int(postciclo.shape[1]), "variables_diccionario": int(len(diccionario)),
        "etiquetas": int(len(etiquetas)), "por_predecir": int(meta.CONJUNTO.eq("PREDICCION").sum()),
        "rasteres": int(len(rasters)), "mallas": int(len(mallas)), "filas_clima": int(len(clima_largo)),
        "columnas_ciclo": int(ciclo.shape[1]), "columnas_historico": int(historico.shape[1]),
        "faltantes_base": int(tabla_base.isna().sum().sum()),
        "variables_con_faltantes": int(tabla_base.isna().any().sum()),
        "banderas_calidad_base": int(diccionario.loc[diccionario.archivo.eq("variables_v0_197.csv"), "rol"].eq("bandera_calidad").sum()),
        "agc170_cobertura_pendiente": float(control_170["frac_valida"]),
        "base_reproduce_referencia": bool(contraste_base.coincide.all()),
        "postciclo_reproduce_referencia": bool(contraste_postciclo.coincide.all()),
        "objetivos_imputados": 0, "modelos_entrenados": 0,
        "predicciones_finales_generadas": 0, "tablas_exportadas": 0,
        "archivo_original_inalterado": True,
    }
    zip_fuente.close()
    print(json.dumps(resumen_fuentes, ensure_ascii=False, indent=2))
    print("RESUMEN_FUENTES_02_JSON=" + json.dumps(resumen_fuentes, ensure_ascii=False, sort_keys=True))
    """, tags=["cierre-verificable"])
    texto("""
    ### Fuentes y referencias — APA 7

    Equipo AgroCebada. (2026, 21 de septiembre). *Tabla integrada de fuentes y
    diccionario v0* [Trabajo interno]. Resúmenes de Andrea reconstruidos desde
    originales, integral parcial de Codex y recetas explícitas de integración.
    Las referencias históricas de salida están incrustadas con tamaño y SHA-256.

    Equipo AgroCebada. (2026, 1 de octubre). *Controles de extracción espacial*
    [Antecedente interno de extracción]. Identidad de mallas, caché, afín, máscaras y cobertura.
    La implementación de este cuaderno se adapta y comprueba el 7 de octubre de 2026;
    no constituye una nueva hipótesis.

    Rasterio contributors. (s. f.). *In-memory files*.
    https://rasterio.readthedocs.io/en/stable/topics/memory-files.html

    Rasterio contributors. (s. f.). *Transforms*.
    https://rasterio.readthedocs.io/en/stable/topics/transforms.html

    pyproj contributors. (s. f.). *Transformer*.
    https://pyproj4.github.io/pyproj/stable/api/transformer.html

    Shapely contributors. (s. f.). *shapely.intersection*.
    https://shapely.readthedocs.io/en/stable/reference/shapely.intersection.html

    Las referencias de herramientas respaldan las operaciones geométricas y la lectura;
    no acreditan las inferencias agronómicas ni la capacidad predictiva de una variable.
    """)
    cuaderno = nbformat.v4.new_notebook(cells=celdas)
    cuaderno.metadata = {
        "kernelspec": {"display_name": "Python 3 (AgroCebada uv)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
        "agrocebada": {
            "id": "FUENTES_02", "tipo": "preparacion_fuentes", "modo": "recalcular_sin_entrenar",
            "crisp_dm": [3], "trabajo_original": "2026-09-21", "antecedente_geo": "2026-10-01",
            "verificacion_actual": "2026-10-07",
            "adaptacion": "2026-10-07", "python_minor": "3.13", "python_local": "3.13.13",
            "modulos_sha256": {nombre: registro["sha256"] for nombre, registro in fuentes.items()},
            "config_recetas_sha256": _hash(config_path.read_bytes()),
            "dataset_config_sha256": _hash(dataset_path.read_bytes()),
            "perfil_colab_sha256": _hash(perfil_path.read_bytes()),
            "soporte_base_sha256": _hash(soporte_path.read_bytes()),
            "soporte_derivado_sha256": _hash(soporte_derivado.encode("utf-8")),
            "dependencias_requeridas": versiones, "dataset_sha256": dataset["sha256"],
            "dataset_bytes": dataset["bytes"], "drive_file_id": dataset["transporte"]["drive"]["file_id"],
            "referencias": {nombre: {k: v for k, v in registro.items() if k != "bytes_zlib_base64"}
                            for nombre, registro in referencias.items()},
        },
    }
    for numero, celda in enumerate(cuaderno.cells, start=1):
        celda.id = f"fuentes02-{numero:02d}"
    nbformat.validate(cuaderno)
    return cuaderno


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if args.salida.exists():
        raise ValueError("Elige una salida nueva; no se sobrescribe un cuaderno existente")
    cuaderno = construir(args.raiz)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(cuaderno, args.salida)
    print(f"Cuaderno generado sin ejecutar: {args.salida}")


if __name__ == "__main__":
    main()
