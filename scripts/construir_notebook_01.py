"""Construye el primer cuaderno de estudio sin ejecutar ni modificar sus insumos."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from textwrap import dedent

import nbformat


def construir(
    modulo: Path, requisitos: Path, *, soporte: Path | None = None,
    config_dataset: Path | None = None,
) -> nbformat.NotebookNode:
    """Incrusta el lector verificado para que el cuaderno no dependa de módulos locales."""
    celdas = []

    def texto(contenido: str) -> None:
        celdas.append(nbformat.v4.new_markdown_cell(dedent(contenido).strip()))

    def codigo(contenido: str, tags: list[str] | None = None) -> None:
        celda = nbformat.v4.new_code_cell(dedent(contenido).strip())
        if tags:
            celda.metadata = {"tags": tags}
        celdas.append(celda)

    soporte = soporte or Path(__file__).with_name("colab_soporte.py")
    config_dataset = config_dataset or (
        Path(__file__).resolve().parents[1] / "config" / "auditoria_01_dataset.json"
    )
    contrato_dataset = json.loads(config_dataset.read_text(encoding="utf-8"))
    id_drive_dataset = contrato_dataset.get("transporte", {}).get("drive", {}).get("file_id")

    texto("""
    # 01. Auditar los datos: ¿cuál es una observación del problema?

    **Pregunta central:** ¿qué contiene el paquete y cómo podemos relacionar sus fuentes
    sin confundir observaciones satelitales con parcelas que tienen un rendimiento conocido?

    **Etapas CRISP-DM:** entender el problema y entender los datos.
    **Modo:** recalcular comprobaciones descriptivas; **no se entrena ningún modelo**,
    no se extraen valores de los rásteres y no se generan las 59 predicciones finales.

    Partimos del ZIP original y comprobamos identidad, unidades, fechas, cobertura y
    calidad. Cada salida sustenta una decisión o identifica algo que todavía no demuestra.

    - Trabajo original de auditoría: 15 de septiembre de 2026; consolidación: 16 de septiembre.
    - Adaptación a este cuaderno autocontenido: 7 de octubre de 2026.
    - Revisión de compatibilidad con Python 3.13 y acceso autorizado desde Drive:
      7 de octubre de 2026; no cambia las operaciones de la auditoría.
    - La fecha de una nueva ejecución se imprime al iniciar. Esta adaptación no constituye
      un registro previo a la llegada de los datos.
    """)
    texto("""
    ## 1. Preparar una ejecución explícita

    **Qué comprobamos.** Que el entorno y el archivo sean identificables.
    **Por qué importa.** Leer las salidas guardadas no requiere instalar nada; recalcularlas
    requiere las bibliotecas y el mismo paquete original.

    **Local:** abrir este cuaderno en el entorno uv del proyecto con los grupos
    `notebooks` y `geo`. **Colab:** usar Python **3.13**; el bloque de acceso permite
    descargar el ZIP original autorizado desde Drive si no hay una copia local. No hace
    falta Git. El cuaderno no sube datos, no publica archivos y no cambia permisos.

    **Antes de ejecutar:** `PREPARAR_COLAB = True` permite preparar las bibliotecas
    necesarias **solo dentro de Colab**. Primero imprime el plan; instala únicamente
    paquetes requeridos cuya versión falta o difiere, con ruedas binarias y dependencias
    limitadas por el perfil exportado de uv. En local no instala nada.

    Si cambia una biblioteca ya cargada, se detiene y pide reiniciar la sesión y volver
    a ejecutar todas las celdas; no mata ni reinicia automáticamente el entorno.
    Las comprobaciones cubren las bibliotecas de este cuaderno, no todos los paquetes
    preinstalados en Colab. Numba, por ejemplo, no se utiliza ni se actualiza.

    La celda técnica siguiente contiene el soporte de preparación y descarga para
    que el cuaderno sea autocontenido; puede mantenerse contraída durante la lectura.
    """)
    celda_soporte = nbformat.v4.new_code_cell(soporte.read_text(encoding="utf-8"))
    celda_soporte.metadata = {"tags": ["soporte-colab"], "jupyter": {"source_hidden": True}}
    celdas.append(celda_soporte)
    requisitos_texto = requisitos.read_text(encoding="utf-8")
    versiones_perfil = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)",
                                      requisitos_texto, flags=re.MULTILINE))
    versiones_visibles = {nombre: versiones_perfil[nombre] for nombre in [
        "numpy", "pandas", "matplotlib", "pyshp", "shapely", "pyproj", "gdown",
    ]}
    bootstrap = dedent("""
    # Acción visible: prepara paquetes SOLO dentro de Colab; uv se ocupa del entorno local.
    PREPARAR_COLAB = True
    import importlib.util
    import sys
    from pathlib import Path

    try:
        EN_COLAB = importlib.util.find_spec("google.colab") is not None
    except ModuleNotFoundError:
        EN_COLAB = False

    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("Local y Colab requieren Python 3.13; no se instala otro perfil.")

    # Perfil completo exportado de uv.lock; incluye dependencias transitivas.
    REQUIREMENTS_COLAB = __PERFIL_REQUISITOS__
    VERSIONES = __VERSIONES_VISIBLES__
    preparacion_entorno = preparar_colab(
        REQUIREMENTS_COLAB, en_colab=EN_COLAB, habilitar=PREPARAR_COLAB,
    )
    print("Preparación:", preparacion_entorno["estado"])
    """).strip()
    codigo(bootstrap.replace("__PERFIL_REQUISITOS__", repr(requisitos_texto)).replace(
        "__VERSIONES_VISIBLES__", repr(versiones_visibles)), tags=["preparar-colab"])
    codigo("""
    import hashlib
    import importlib.metadata as metadata
    import io
    import json
    import platform
    import zipfile
    from datetime import datetime, timezone
    from pathlib import Path

    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    from IPython.display import display
    from matplotlib.patches import Polygon as ParchePoligono
    from pyproj import Transformer
    from shapely.ops import transform

    tabla_entorno = pd.DataFrame([
        {"biblioteca": nombre, "esperada": esperada,
         "instalada": metadata.version(nombre)}
        for nombre, esperada in VERSIONES.items()
    ])
    FECHA_EJECUCION_UTC = datetime.now(timezone.utc).isoformat()
    print("Python:", platform.python_version())
    print("Ejecución UTC:", FECHA_EJECUCION_UTC)
    print("Superficie:", "Colab" if EN_COLAB else "entorno local")
    display(tabla_entorno)
    assert sys.version_info[:2] == (3, 13), "El proyecto y Colab utilizan Python 3.13."
    assert tabla_entorno["esperada"].eq(tabla_entorno["instalada"]).all(), (
        "Las versiones difieren. Prepara el perfil uv o usa la instalación explícita de Colab."
    )
    plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False,
                         "axes.spines.right": False, "font.size": 10})
    """)
    texto("""
    **Celda técnica del lector.** El siguiente bloque contiene completo el código de lectura
    y validación, en lugar de importar un módulo de una máquina particular. Se puede
    desplegar para revisar los controles; las comprobaciones y sus resultados se presentan
    después. No repara polígonos, no rellena faltantes y no cambia los archivos originales.
    """)
    celda_lector = nbformat.v4.new_code_cell(modulo.read_text(encoding="utf-8"))
    celda_lector.metadata = {"tags": ["lector-tecnico"], "jupyter": {"source_hidden": True}}
    celdas.append(celda_lector)
    texto("""
    ## 2. Identificar el paquete antes de usarlo

    **Qué comprobamos.** Nombre, tamaño, SHA-256, miembros y CRC del ZIP.
    **Por qué importa.** Un resultado reproducible debe identificar exactamente qué
    versión leyó. Un hash acredita identidad de bytes, no la fecha en que se creó un archivo.

    Es el `DataSet.zip` proporcionado para el reto, no una tabla de variables ya procesada.
    Si no está en una ubicación sugerida, escribe la ruta en `RUTA_DATASET`. En Colab,
    `DESCARGAR_DATASET = True` permite descargar la copia de Drive compartida para el
    equipo. El ID debe corresponder al **ZIP**, no al notebook.

    La descarga se escribe primero en un archivo temporal; solo se acepta como
    `DataSet.zip` tras comprobar tamaño y SHA-256. Una copia existente incorrecta se
    rechaza sin sustituirla; una descarga fallida se conserva en cuarentena para revisarla.
    Los permisos los concede quien comparte el archivo: este cuaderno no los cambia
    ni utiliza credenciales o cookies del navegador.
    """)
    codigo("""
    # Cambia únicamente esta configuración si el archivo está en otra ubicación.
    RUTA_DATASET = None  # Ejemplo: Path("/content/DataSet.zip")
    ID_DRIVE_DATASET = __ID_DRIVE_DATASET__  # ID del ZIP original autorizado, no del notebook.
    DESCARGAR_DATASET = EN_COLAB  # En local no se descarga por defecto.
    candidatos = [
        Path("data/raw/DataSet.zip"), Path("../data/raw/DataSet.zip"),
        Path("DataSet.zip"), Path("/content/DataSet.zip"),
    ]
    ruta_dataset = (
        Path(RUTA_DATASET).expanduser() if RUTA_DATASET is not None
        else next((ruta for ruta in candidatos if ruta.is_file()), None)
    )
    if ruta_dataset is None:
        ruta_dataset = Path("/content/DataSet.zip") if EN_COLAB else Path("data/raw/DataSet.zip")
    ruta_dataset = obtener_dataset(
        ruta_dataset, file_id=ID_DRIVE_DATASET,
        sha256_esperado=SHA256_DATASET, bytes_esperados=29_687_194,
        permitir_descarga=DESCARGAR_DATASET,
    )
    hash_inicial = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    zip_fuente = cargar_zip(ruta_dataset)
    inventario = pd.DataFrame(validar_zip(zip_fuente))
    print("Entrada:", ruta_dataset.name)
    print("Bytes:", ruta_dataset.stat().st_size)
    print("SHA-256:", hash_inicial)
    assert hash_inicial == SHA256_DATASET
    assert ruta_dataset.stat().st_size == 29_687_194
    display(inventario.assign(
        archivo=inventario["nombre"].map(lambda nombre: nombre.rsplit("/", 1)[-1]),
        sha256_corto=inventario["sha256"].str[:16],
    )[["archivo", "bytes", "sha256_corto"]])
    """.replace("__ID_DRIVE_DATASET__", repr(id_drive_dataset)), tags=["acceso-dataset"])
    texto("""
    **Qué significa.** La tabla distingue dos CSV satelitales, un catálogo de rendimientos,
    geometrías, cartografía y documentación. Las huellas completas permanecen en
    `inventario`; la tabla solo abrevia su visualización.

    **No demuestra:** que los datos carezcan de sesgos, ni que las fechas internas del ZIP
    sean sellos de tiempo independientes. Integridad y validez científica son cosas distintas.

    Ahora abrimos los ZIP internos en memoria para contar sus miembros. No se extraen
    valores de los píxeles ni se comparan sus mallas todavía.
    """)
    codigo("""
    componentes = [
        ("Geometrías", "Parcelas_Reto_AGC_CONJUNTO_70_30.zip", 0),
        ("Precipitación", "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip", 48),
        ("Temperatura", "Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip", 96),
        ("Topografía", "Reto_AgroCebada_Topografia_INEGI_CEM4.zip", 2),
    ]
    filas_componentes = []
    for componente, nombre_zip, cantidad_tif in componentes:
        nombre = miembro_unico(zip_fuente, nombre_zip)
        with zipfile.ZipFile(io.BytesIO(zip_fuente.read(nombre))) as interno:
            detalles = validar_zip(interno)
            n_tif = sum(fila["nombre"].lower().endswith((".tif", ".tiff"))
                        for fila in detalles)
            assert n_tif == cantidad_tif, f"Inventario inesperado: {componente}"
            filas_componentes.append({
                "componente": componente, "archivos": len(detalles), "rásteres": n_tif,
                "integridad": "CRC y rutas válidos",
            })
    tabla_componentes = pd.DataFrame(filas_componentes)
    display(tabla_componentes)
    """)
    texto("""
    ## 3. El objetivo: una etiqueta por parcela

    **Qué comprobamos.** El catálogo, sus unidades y la consistencia de los conjuntos.
    **Por qué importa.** El objetivo es un número continuo —rendimiento en **t/ha**—:
    es regresión supervisada, no clasificación de parcelas.

    Conservamos la lectura original en `catalogo_crudo`. La copia de trabajo solo retira
    una columna sin nombre si **todos** sus valores están vacíos; nunca la elimina a ciegas.
    El lector exige IDs únicos, áreas positivas y etiquetas coherentes con `CONJUNTO`.
    """)
    codigo("""
    catalogo_crudo = leer_csv(zip_fuente, "ID_area_rendimiento_70_30_Reto_AgroCebada.csv")
    catalogo = normalizar_catalogo(catalogo_crudo)
    columnas_vacias = [columna for columna in catalogo_crudo.columns
                      if columna not in catalogo.columns]
    print("Dimensión física del CSV:", catalogo_crudo.shape)
    print("Columnas con significado:", list(catalogo.columns))
    print("Columna vacía retirada de la copia:", columnas_vacias)
    assert catalogo_crudo.shape == (197, 5)
    assert catalogo.shape == (197, 4)
    muestra = catalogo[["ID_POLIGONO", "AREA_HA", "CONJUNTO"]].head(6).copy()
    muestra["etiqueta_disponible"] = catalogo["RENDIMIENTO_T_HA"].notna().head(6)
    display(muestra)
    """)
    codigo("""
    tabla_objetivo = catalogo.groupby("CONJUNTO").agg(
        parcelas=("ID_POLIGONO", "nunique"),
        etiquetas_visibles=("RENDIMIENTO_T_HA", "count"),
    ).reset_index()
    tabla_objetivo["etiquetas_ausentes"] = (
        tabla_objetivo["parcelas"] - tabla_objetivo["etiquetas_visibles"]
    )
    n_parcelas = catalogo["ID_POLIGONO"].nunique()
    n_etiquetas = catalogo["RENDIMIENTO_T_HA"].notna().sum()
    n_ocultas = catalogo["RENDIMIENTO_T_HA"].isna().sum()
    assert (n_parcelas, n_etiquetas, n_ocultas) == (197, 138, 59)
    assert set(catalogo["ID_POLIGONO"]) == {f"AGC_{i:03d}" for i in range(1, 198)}
    display(tabla_objetivo)
    """)
    texto("""
    **Respuesta.** Hay 197 parcelas y **138 etiquetas de rendimiento**, no 197 etiquetas.
    Las 59 ausencias son intencionales: corresponden a los casos que se deben predecir,
    no a valores que haya que rellenar durante la auditoría.

    La documentación entregada fija el ciclo objetivo: **abril–octubre de 2025**
    (*Descripción general del conjunto de datos*, s. f., sección 1). El CSV no contiene
    una columna de campaña; esta delimitación procede del documento, no de inferirla
    al mirar las fechas satelitales.
    """)
    texto("""
    ## 4. Muchas fechas no crean nuevas etiquetas

    **Qué comprobamos.** Filas, IDs, fechas y claves de los dos CSV satelitales.
    **Por qué importa.** Una fila satelital es una observación de una parcela en una fecha
    y un sensor. Varias filas de una misma parcela comparten el mismo rendimiento objetivo.

    El lector interpreta las fechas explícitamente como `día/mes/año`, añade `FECHA` a
    una copia y verifica la clave **ID + fecha + sensor**. No decide aquí qué fechas o
    mediciones se convertirán en variables del modelo.
    """)
    codigo("""
    basico_crudo = leer_csv(zip_fuente, "Conjunto_datos_BASICO_AgroCebada2026.csv")
    pro_crudo = leer_csv(zip_fuente, "Conjunto_datos_PRO_AgroCebada.csv")
    basico = validar_satelite(basico_crudo)
    pro = validar_satelite(pro_crudo)
    ids_catalogo = set(catalogo["ID_POLIGONO"])
    assert set(basico["ID_POLIGONO"]) == ids_catalogo
    assert set(pro["ID_POLIGONO"]) == ids_catalogo
    assert basico_crudo.shape == (107_666, 96)
    assert pro_crudo.shape == (47_804, 20)
    assert set(basico["sensor"]) == {"Sentinel-2", "Landsat"}
    assert set(pro["sensor"]) == {"Planet"}

    filas_fuentes = []
    for fuente, tabla in [("Básico", basico), ("PRO", pro)]:
        for sensor, grupo in tabla.groupby("sensor"):
            filas_fuentes.append({
                "fuente": fuente, "sensor": sensor, "filas": len(grupo),
                "parcelas_distintas": grupo["ID_POLIGONO"].nunique(),
                "desde": grupo["FECHA"].min().date().isoformat(),
                "hasta": grupo["FECHA"].max().date().isoformat(),
                "años": ", ".join(map(str, sorted(grupo["FECHA"].dt.year.unique()))),
            })
    tabla_fuentes = pd.DataFrame(filas_fuentes)
    display(tabla_fuentes)
    print("Filas satelitales:", len(basico) + len(pro))
    print("Etiquetas de rendimiento:", int(n_etiquetas))
    """)
    texto("""
    **Respuesta.** Los CSV contienen 155,470 filas satelitales, pero siguen siendo
    **138 parcelas con rendimiento conocido en una sola campaña**. Los años 2022–2024
    son historia por parcela, no campañas adicionales etiquetadas.

    **Decisión derivada:** cuando más adelante simulemos parcelas desconocidas, la unidad
    de separación será la parcela, nunca una fila satelital. Poner fechas de una misma
    parcela en entrenamiento y validación mezclaría información de la misma unidad.
    """)
    codigo("""
    # Diagnóstico de orden y repetición; no transforma la receta de variables.
    diagnosticos_fechas = []
    for fuente, tabla in [("Básico", basico), ("PRO", pro)]:
        for sensor, grupo in tabla.groupby("sensor"):
            ordenado_por_parcela = grupo.groupby("ID_POLIGONO")["FECHA"].apply(
                lambda serie: serie.is_monotonic_increasing
            )
            repeticiones = grupo.groupby("ID_POLIGONO").size()
            diagnosticos_fechas.append({
                "sensor": sensor, "mínimo_filas_por_parcela": int(repeticiones.min()),
                "mediana_filas_por_parcela": float(repeticiones.median()),
                "máximo_filas_por_parcela": int(repeticiones.max()),
                "parcelas_fuera_de_orden": int((~ordenado_por_parcela).sum()),
                "claves_repetidas": int(grupo.duplicated(
                    ["ID_POLIGONO", "FECHA", "sensor"]).sum()),
            })
    display(pd.DataFrame(diagnosticos_fechas))
    """)
    texto("""
    **Qué significa.** Una tabla puede contener fechas válidas sin estar ordenada.
    Para tendencias o picos habrá que ordenar y documentar la ventana; eso no cambia
    el número de parcelas ni justifica elegir ahora una regla temporal.

    **Límite:** que el paquete incluya meses posteriores a octubre no demuestra por sí
    mismo su admisibilidad como predictores ni que estemos construyendo una predicción
    disponible antes de la cosecha. El momento de disponibilidad se documenta al definir
    cada variable.
    """)
    texto("""
    ## 5. Relacionar geometrías y catálogo sin perder parcelas

    **Qué comprobamos.** Que la capa tenga los mismos IDs y que la unión sea uno a uno.
    **Por qué importa.** Una unión por posición de fila puede asignar datos a la parcela
    equivocada. Por eso usamos el ID y exigimos correspondencia completa.

    Leemos las geometrías sin repararlas. Comparamos el área **declarada** en ambas
    fuentes; esto todavía no es un recálculo del área física del polígono ni una receta de
    intersección con rásteres. Las grafías de cultivo se conservan para mostrar su procedencia.
    """)
    codigo("""
    atributos_geo, geometrias, crs_original = leer_geometrias(zip_fuente)
    assert len(atributos_geo) == len(geometrias) == 197
    assert set(atributos_geo["ID_POLIGONO"]) == ids_catalogo
    parcela = catalogo.merge(atributos_geo, on="ID_POLIGONO", how="outer",
                             validate="one_to_one", indicator=True)
    assert parcela["_merge"].eq("both").all()
    assert parcela["CONJUNTO"].eq(parcela["CONJUNTO_GEOMETRIA"]).all()
    diferencia_area_declarada = (
        parcela["AREA_HA"] - parcela["AREA_HA_GEOMETRIA"]
    ).abs().max()
    assert diferencia_area_declarada <= 1e-9
    print("CRS de origen:", crs_original.to_string())
    print("Uniones uno a uno:", len(parcela))
    print("Diferencia máxima de área declarada (ha):", float(diferencia_area_declarada))
    print("Geometrías vacías:", sum(geom.is_empty for geom in geometrias))
    print("Geometrías no válidas:", sum(not geom.is_valid for geom in geometrias))
    display(parcela["Cultivo"].value_counts(dropna=False).rename_axis(
        "grafía_original").reset_index(name="parcelas"))
    """)
    texto("""
    **Respuesta.** Se puede relacionar el catálogo y la capa por ID sin eliminar filas.
    Las diferencias de escritura de `Cultivo` son un diagnóstico de formato; no prueban
    variedades distintas ni autorizan usar una huella de captura como explicación agronómica.

    Para calcular variables espaciales después tendremos que comprobar proyección,
    transformaciones, cuadrícula, NoData y pesos. La coincidencia de dos campos de área
    no certifica todos esos procedimientos.
    """)
    texto("""
    ## 6. ¿Qué territorio representa realmente la muestra?

    **Qué comprobamos.** Conteos por estado y municipio, junto con el mapa de las parcelas.
    **Por qué importa.** Una muestra en tres estados no equivale a una muestra representativa
    de toda su superficie productiva. El alcance debe describirse con la distribución real.

    Usamos los nombres incluidos en la capa, sin certificar límites administrativos externos.
    No deducimos el procedimiento oficial de separación a partir de estos conteos.
    """)
    codigo("""
    tabla_estados = pd.crosstab(parcela["Estado"], parcela["CONJUNTO"]).reindex(
        columns=["ENTRENAMIENTO", "PREDICCION"], fill_value=0
    )
    tabla_estados["TOTAL"] = tabla_estados.sum(axis=1)
    tabla_municipios = pd.crosstab(
        [parcela["Estado"], parcela["Municipio"]], parcela["CONJUNTO"]
    ).reindex(columns=["ENTRENAMIENTO", "PREDICCION"], fill_value=0)
    tabla_municipios["TOTAL"] = tabla_municipios.sum(axis=1)
    assert tabla_estados["TOTAL"].sum() == tabla_municipios["TOTAL"].sum() == 197
    assert len(tabla_municipios) == 9
    display(tabla_estados)
    display(tabla_municipios)
    concentracion = tabla_municipios.loc[("Puebla", "Chignahuapan")]
    print("Chignahuapan:", int(concentracion["TOTAL"]), "parcelas;",
          int(concentracion["ENTRENAMIENTO"]), "etiquetas y",
          int(concentracion["PREDICCION"]), "casos por predecir.")
    """)
    codigo("""
    # Solo para representar las geometrías en metros: UTM 14N, EPSG:32614.
    # No calcula extracciones ni áreas para el modelo.
    convertir_mapa = Transformer.from_crs(crs_original, "EPSG:32614", always_xy=True)
    geo_utm = [transform(convertir_mapa.transform, geom) for geom in geometrias]
    geometria_por_id = dict(zip(atributos_geo["ID_POLIGONO"], geo_utm, strict=True))
    colores_estado = {"Hidalgo": "#427f9b", "Puebla": "#b47728", "Tlaxcala": "#64875e"}
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for fila in parcela.itertuples(index=False):
        geom = geometria_por_id[fila.ID_POLIGONO]
        partes = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for parte in partes:
            xy = np.asarray(parte.exterior.coords) / 1000
            ax.add_patch(ParchePoligono(
                xy, closed=True, facecolor=colores_estado[fila.Estado],
                edgecolor="#333333", linewidth=0.35, alpha=0.75,
            ))
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlabel("Este UTM 14N (km)")
    ax.set_ylabel("Norte UTM 14N (km)")
    ax.set_title("Geometrías de las 197 parcelas; color según Estado de la capa")
    for estado, color in colores_estado.items():
        ax.plot([], [], marker="s", linestyle="", color=color, label=estado)
    ax.legend(title="Atributo de origen", frameon=False)
    fig.tight_layout()
    plt.show()
    """)
    texto("""
    **Respuesta.** La muestra se concentra en nueve municipios; Chignahuapan reúne
    100 de las 197 parcelas, incluidas 71 de las 138 etiquetas y 29 de las 59 predicciones.

    **Decisión derivada:** describir el modelo como calibrado en esta muestra de Valles
    Altos, no como validado para toda Hidalgo, Tlaxcala y Puebla. Al evaluar modelos
    revisaremos también resultados por región.

    **Límite:** el mapa no demuestra autocorrelación, causalidad ni que el split oficial
    sea aleatorio. Esas preguntas necesitan un análisis específico y, para el mecanismo
    oficial de separación, información de los organizadores.
    """)
    texto("""
    ## 7. ¿Cómo se distribuye lo que queremos predecir?

    **Qué comprobamos.** Escala, dispersión y precisión de las etiquetas visibles.
    **Por qué importa.** Hay que distinguir un diagnóstico del objetivo de una explicación
    causal o una regla que obligue a redondear futuras predicciones.

    Utilizamos solo las 138 etiquetas disponibles. No imputamos los faltantes ni medimos
    capacidad predictiva: una media o un histograma aquí son estadísticas descriptivas.
    """)
    codigo("""
    etiquetadas = parcela.loc[parcela["RENDIMIENTO_T_HA"].notna()].copy()
    rendimiento = etiquetadas["RENDIMIENTO_T_HA"]
    descripcion = rendimiento.describe().to_frame("rendimiento_t_ha")
    descripcion.loc["valores_distintos"] = rendimiento.nunique()
    display(descripcion)
    display(etiquetadas.groupby("Estado")["RENDIMIENTO_T_HA"].agg(
        parcelas="count", media="mean", desviacion="std", minimo="min", maximo="max",
        valores_distintos="nunique",
    ).round(4))
    es_multiplo_medio = np.isclose(
        rendimiento.to_numpy() * 2, np.rint(rendimiento.to_numpy() * 2),
        atol=1e-10, rtol=0,
    )
    n_redondeadas = int(es_multiplo_medio.sum())
    print("Múltiplos de 0.5 t/ha, tolerancia 1e-10:", n_redondeadas,
          "de", len(rendimiento))
    """)
    codigo("""
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    bordes = np.arange(1.75, 5.76, 0.25)
    ax.hist(rendimiento, bins=bordes, color="#427f9b", edgecolor="white")
    ax.set_xlabel("Rendimiento observado (t/ha)")
    ax.set_ylabel("Parcelas con etiqueta")
    ax.set_title("Distribución de las 138 etiquetas; no son predicciones")
    fig.tight_layout()
    plt.show()
    valores_tlaxcala = etiquetadas.loc[
        etiquetadas["Estado"].eq("Tlaxcala"), "RENDIMIENTO_T_HA"
    ].value_counts().sort_index()
    display(valores_tlaxcala.rename_axis("t_ha").reset_index(name="parcelas_Tlaxcala"))
    """)
    texto("""
    **Respuesta.** El objetivo visible va de 2.00 a 5.59 t/ha. Parte de las etiquetas está
    discretizada: 45 son múltiplos de 0.5 t/ha, y Tlaxcala tiene solo tres valores distintos.
    Las regiones difieren tanto en nivel como en precisión aparente del registro.

    **Límite:** esto es compatible con redondeo o procedimientos diferentes de captura,
    pero no prueba cómo se midió el rendimiento, un piso de error irreducible o etiquetas
    incorrectas. Tampoco convierte la regresión en clasificación ni justifica redondear
    automáticamente las 59 estimaciones.
    """)
    texto("""
    ## 8. Faltantes y valores problemáticos: diagnóstico, no receta

    **Qué comprobamos.** Disponibilidad de índices por sensor, nubosidad y LAI negativo.
    **Por qué importa.** No todos los `NaN` significan nube ni todos los sensores entregan
    las mismas variables. Primero distinguimos ausencia estructural de una medición faltante.

    No recortamos LAI, no rellenamos `NaN` y no elegimos un umbral de nubosidad. Esas
    decisiones corresponden a la preparación de variables y deberán justificarse por separado.
    """)
    codigo("""
    disponibilidad = []
    for tabla in [basico, pro]:
        for sensor, grupo in tabla.groupby("sensor"):
            for indice in ["ndvi_promedio", "vi6t_promedio"]:
                existe = indice in grupo.columns
                presentes = int(grupo[indice].notna().sum()) if existe else 0
                disponibilidad.append({
                    "sensor": sensor, "índice": indice, "columna_en_fuente": existe,
                    "filas": len(grupo), "valores_presentes": presentes,
                    "ausentes": len(grupo) - presentes,
                })
    tabla_disponibilidad = pd.DataFrame(disponibilidad)
    display(tabla_disponibilidad)
    # En Básico, NDVI no es la medición disponible de Landsat; vi6t sí lo es.
    assert basico.loc[basico["sensor"].eq("Landsat"), "ndvi_promedio"].isna().all()
    assert basico.loc[basico["sensor"].eq("Sentinel-2"), "vi6t_promedio"].isna().all()
    """)
    codigo("""
    calidad = []
    for tabla in [basico, pro]:
        for sensor, grupo in tabla.groupby("sensor"):
            columna_disponible = "vi6t_promedio" if sensor == "Landsat" else "ndvi_promedio"
            faltante = grupo[columna_disponible].isna()
            nubes_100 = grupo["porcentaje_nubosidad"].eq(100)
            assert grupo["porcentaje_nubosidad"].dropna().between(0, 100).all()
            calidad.append({
                "sensor": sensor, "índice_de_control": columna_disponible,
                "faltantes": int(faltante.sum()),
                "faltantes_pct": float(100 * faltante.mean()),
                "filas_nubosidad_100": int(nubes_100.sum()),
                "nubosidad_desconocida": int(grupo["porcentaje_nubosidad"].isna().sum()),
                "faltantes_con_nube_desconocida": int((
                    faltante & grupo["porcentaje_nubosidad"].isna()).sum()),
                "faltantes_con_nube_conocida_menor_100": int((
                    faltante & grupo["porcentaje_nubosidad"].notna() & ~nubes_100).sum()),
            })
    display(pd.DataFrame(calidad).round(2))
    sentinel = basico.loc[basico["sensor"].eq("Sentinel-2")]
    ciclo_sentinel = sentinel.loc[sentinel["FECHA"].between("2025-04-01", "2025-10-31")]
    lai_observado = ciclo_sentinel["lai_promedio"].dropna()
    print("LAI negativo en Sentinel-2, abril–octubre de 2025:",
          int(lai_observado.lt(0).sum()), "de", len(lai_observado),
          f"({100 * lai_observado.lt(0).mean():.2f} % de los valores presentes)")
    """)
    texto("""
    **Respuesta.** Landsat aporta `vi6t`, no NDVI. Las columnas comunes del CSV no implican
    mediciones comunes entre sensores. La nubosidad debe leerse junto con disponibilidad
    y procedencia, no usarse como explicación automática de toda ausencia. Una nubosidad
    desconocida **no equivale a un cielo despejado**.

    Un LAI negativo merece revisar definición y tratamiento; eliminarlo o conservarlo
    cambia los resúmenes. **Esta auditoría señala el problema, pero no elige la receta**
    según cuál produzca después la mejor puntuación.
    """)
    texto("""
    ## 9. Cierre: qué quedó demostrado

    | Pregunta | Respuesta comprobable | Consecuencia para el recorrido |
    |---|---|---|
    | ¿Qué se predice? | Rendimiento continuo, t/ha, abril–octubre de 2025 | Regresión supervisada de una campaña |
    | ¿Cuántas etiquetas hay? | 138 visibles; 59 intencionalmente ocultas | No imputar el objetivo faltante |
    | ¿Cuál es la unidad? | Parcela; 155,470 filas satelitales no son nuevas etiquetas | Separar y evaluar por parcela |
    | ¿Cómo se unen las fuentes? | Mismos 197 IDs; unión catálogo–capa uno a uno | Unir por ID, no por posición |
    | ¿Qué territorio cubre? | Nueve municipios; 100 parcelas en Chignahuapan | Explicitar alcance y evaluar por región |
    | ¿Es todo faltante equivalente? | Índices distintos por sensor y calidad heterogénea | Definir tratamientos por fuente |

    **No concluimos** una receta óptima, efectos causales, el mecanismo oficial del split,
    la precisión de un modelo ni capacidad para extrapolar a otros ciclos o regiones.

    La siguiente celda deja un resumen verificable y comprueba que el ZIP no cambió.
    No guarda datos ni predicciones en disco.
    """)
    codigo("""
    hash_final = hashlib.sha256(ruta_dataset.read_bytes()).hexdigest()
    assert hash_final == hash_inicial == SHA256_DATASET
    resumen_auditoria = {
        "notebook": "01_auditoria_y_unidad_parcela",
        "fecha_adaptacion": "2026-10-07",
        "fecha_ejecucion_utc": FECHA_EJECUCION_UTC,
        "sha256_dataset": hash_final,
        "bytes_dataset": int(ruta_dataset.stat().st_size),
        "parcelas": int(n_parcelas), "etiquetas": int(n_etiquetas),
        "por_predecir": int(n_ocultas),
        "filas_basico": int(len(basico)), "filas_pro": int(len(pro)),
        "filas_satelitales": int(len(basico) + len(pro)),
        "estados": int(parcela["Estado"].nunique()),
        "municipios": int(len(tabla_municipios)),
        "chignahuapan_etiquetas": int(concentracion["ENTRENAMIENTO"]),
        "chignahuapan_ocultas": int(concentracion["PREDICCION"]),
        "rendimiento_minimo_t_ha": float(rendimiento.min()),
        "rendimiento_maximo_t_ha": float(rendimiento.max()),
        "multiplos_05_t_ha": n_redondeadas,
        "diferencia_area_declarada_max_ha": float(diferencia_area_declarada),
        "geometrias_validas": int(sum(geom.is_valid for geom in geometrias)),
        "objetivos_imputados": 0,
        "modelos_entrenados": 0, "predicciones_finales_generadas": 0,
        "extracciones_raster": 0, "archivo_original_inalterado": True,
    }
    zip_fuente.close()
    print(json.dumps(resumen_auditoria, ensure_ascii=False, indent=2))
    print("RESUMEN_AUDITORIA_JSON=" + json.dumps(
        resumen_auditoria, sort_keys=True, ensure_ascii=False))
    """)
    texto("""
    ## 10. La siguiente pregunta

    **¿Cómo convertir las fuentes de una parcela en una fila de variables sin desplazarla,
    cambiar sus unidades o confundir píxeles extremos con promedios?**

    El cuaderno 02 retomará **preparar los datos**, porque esta auditoría identificó qué
    debe controlarse antes de modelar: geometría y proyección, mallas y NoData,
    intersecciones y pesos, ventanas temporales y significado de los resúmenes.
    Las recetas se contrastarán con controles independientes; su utilidad predictiva
    se estudiará después, mediante comparaciones fuera de muestra.

    ### Conceptos breves

    - **Etiqueta:** rendimiento conocido que queremos aprender a estimar.
    - **Unidad de observación:** la parcela cuyo rendimiento constituye un caso del problema.
    - **Ausencia estructural:** variable que una fuente no entrega; no es una medición nublada.
    - **CRS:** referencia espacial que da significado a las coordenadas; grados no son metros.
    - **Integridad:** identidad del archivo. No acredita representatividad ni ausencia de sesgos.

    ### Fuentes y referencias — APA 7

    *Descripción general del conjunto de datos*. (s. f.). [Documento proporcionado con el
    dataset del Reto AgroCebada 2026]. Archivo `Descripcion_general_variables_DataSet.docx`,
    sección 1, dentro de `DataSet.zip`. Es la fuente de la campaña objetivo y de la
    descripción de los sensores; los conteos se recalculan aquí desde los datos.

    *DataSet.zip*. (s. f.). [Paquete de datos proporcionado para el Reto AgroCebada 2026].
    Identificador SHA-256 impreso en las secciones 2 y 9.

    Para revisar las herramientas de lectura y transformación, sin convertirlas en
    respaldo de las conclusiones agronómicas:

    pandas development team. (s. f.). *pandas documentation*. https://pandas.pydata.org/docs/

    PyShp contributors. (s. f.). *PyShp: Python Shapefile Library*.
    https://github.com/GeospatialPython/pyshp

    pyproj contributors. (s. f.). *pyproj documentation*. https://pyproj4.github.io/pyproj/stable/
    """)

    cuaderno = nbformat.v4.new_notebook(cells=celdas)
    cuaderno.metadata = {
        "kernelspec": {"display_name": "Python 3 (AgroCebada uv)",
                       "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.13"},
        "agrocebada": {
            "id": "AUDITORIA_01", "tipo": "auditoria_descriptiva",
            "modo": "recalcular_sin_entrenar", "crisp_dm": [1, 2],
            "trabajo_original": "2026-09-15", "consolidacion_original": "2026-09-16",
            "adaptacion": "2026-10-07", "lector_sha256": hashlib.sha256(
                modulo.read_bytes()).hexdigest(),
            "perfil_colab_sha256": hashlib.sha256(requisitos.read_bytes()).hexdigest(),
            "soporte_colab_sha256": hashlib.sha256(soporte.read_bytes()).hexdigest(),
            "compatibilidad_revision": "2026-10-07", "python_minor": "3.13",
            "dependencias_requeridas": versiones_visibles,
            "dataset_sha256": contrato_dataset["sha256"],
            "dataset_bytes": contrato_dataset["bytes"],
            "drive_file_id": id_drive_dataset,
        },
    }
    for numero, celda in enumerate(cuaderno.cells, start=1):
        celda.id = f"audit01-{numero:02d}"
    nbformat.validate(cuaderno)
    return cuaderno


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--modulo", type=Path, default=Path(__file__).with_name("auditoria_01.py"))
    parser.add_argument("--soporte", type=Path,
                        default=Path(__file__).with_name("colab_soporte.py"))
    parser.add_argument("--config-dataset", type=Path,
                        default=Path(__file__).resolve().parents[1] /
                        "config" / "auditoria_01_dataset.json")
    candidatos = [Path(__file__).with_name("requirements-colab-auditoria.txt"),
                  Path(__file__).resolve().parents[1] / "requirements-colab-auditoria.txt"]
    parser.add_argument("--requirements", type=Path,
                        default=next((p for p in candidatos if p.is_file()), candidatos[0]))
    args = parser.parse_args()
    cuaderno = construir(args.modulo, args.requirements, soporte=args.soporte,
                        config_dataset=args.config_dataset)
    if args.salida.exists():
        raise ValueError("Elige una salida nueva; no se sobrescribe un cuaderno existente")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(cuaderno, args.salida)
    print(f"Cuaderno construido: {len(cuaderno.cells)} celdas; sin ejecución.")


if __name__ == "__main__":
    main()
