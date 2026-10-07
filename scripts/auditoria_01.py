"""Lectores y controles del cuaderno 01; sin extracción de variables ni modelos.

Se leen los archivos en memoria. Ninguna función modifica o descomprime los
originales en el sistema de archivos. El mismo texto se incrusta en el notebook.
"""

import hashlib
import io
import re
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd
import shapefile
from pyproj import CRS
from shapely.geometry import shape


SHA256_DATASET = "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"
MAX_ARCHIVO_BYTES = 256 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_MIEMBROS = 1000


def validar_zip(z):
    """Rechaza nombres ambiguos/peligrosos y limita bytes antes de leerlos."""
    vistos, inventario = set(), []
    infos = z.infolist()
    if len(infos) > MAX_MIEMBROS:
        raise ValueError("ZIP con demasiados miembros")
    if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
        raise ValueError("ZIP excede el límite total de bytes descomprimidos")
    for info in infos:
        nombre = info.filename
        ruta = PurePosixPath(nombre)
        clave = nombre.rstrip("/").casefold()
        if (
            "\\" in nombre or "\x00" in nombre or ruta.is_absolute()
            or ".." in ruta.parts or re.match(r"^[A-Za-z]:", nombre)
            or not ruta.parts or clave in vistos
        ):
            raise ValueError(f"Ruta insegura o duplicada en ZIP: {nombre!r}")
        vistos.add(clave)
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError(f"Enlace simbólico no admitido: {nombre}")
        if info.file_size > MAX_ARCHIVO_BYTES:
            raise ValueError(f"Miembro excede el límite de bytes: {nombre}")
        if info.flag_bits & 1:
            raise ValueError("ZIP cifrado no admitido en esta auditoría")
    # z.read comprueba CRC; no se escriben rutas del ZIP en disco.
    for info in infos:
        if not info.is_dir():
            contenido = z.read(info)
            inventario.append({
                "nombre": info.filename,
                "bytes": len(contenido),
                "sha256": hashlib.sha256(contenido).hexdigest(),
            })
    return inventario


def cargar_zip(path):
    ruta = Path(path)
    if ruta.stat().st_size > MAX_TOTAL_BYTES:
        raise ValueError("Archivo de entrada demasiado grande")
    contenido = ruta.read_bytes()
    digest = hashlib.sha256(contenido).hexdigest()
    if digest != SHA256_DATASET:
        raise ValueError(f"Dataset incorrecto: SHA-256 {digest}; se detiene la lectura")
    archivo = zipfile.ZipFile(io.BytesIO(contenido))
    validar_zip(archivo)
    return archivo


def miembro_unico(z, terminacion):
    nombres = [i.filename for i in z.infolist()
               if not i.is_dir() and (
                   i.filename.endswith(terminacion) if terminacion.startswith(".")
                   else PurePosixPath(i.filename).name == terminacion
               )]
    if len(nombres) != 1:
        raise ValueError(f"Se esperaba un miembro para {terminacion!r}, hay {len(nombres)}")
    return nombres[0]


def leer_csv(z, terminacion):
    return pd.read_csv(io.BytesIO(z.read(miembro_unico(z, terminacion))), encoding="utf-8-sig")


def normalizar_catalogo(df):
    """Solo elimina separadores vacíos; no imputa, redondea ni cambia etiquetas."""
    copia = df.copy(deep=True)
    vacias = [col for col in copia.columns if str(col).startswith("Unnamed:")]
    if any(copia[col].notna().any() for col in vacias):
        raise ValueError("Una columna sin nombre contiene datos; no se elimina")
    copia = copia.drop(columns=vacias)
    requeridas = ["ID_POLIGONO", "AREA_HA", "RENDIMIENTO_T_HA", "CONJUNTO"]
    if list(copia.columns) != requeridas:
        raise ValueError("Esquema de catálogo inesperado")
    ids = copia.ID_POLIGONO
    if ids.isna().any() or not ids.astype(str).str.fullmatch(r"AGC_\d{3}").all():
        raise ValueError("Identificadores vacíos o mal formados")
    if ids.duplicated().any():
        raise ValueError("Identificador de parcela duplicado")
    if not copia.CONJUNTO.isin(["ENTRENAMIENTO", "PREDICCION"]).all():
        raise ValueError("CONJUNTO desconocido")
    for col in ["AREA_HA", "RENDIMIENTO_T_HA"]:
        copia[col] = pd.to_numeric(copia[col], errors="raise")
    if not np.isfinite(copia.AREA_HA).all() or (copia.AREA_HA <= 0).any():
        raise ValueError("Área no positiva o no finita")
    train = copia.CONJUNTO.eq("ENTRENAMIENTO")
    if copia.loc[train, "RENDIMIENTO_T_HA"].isna().any():
        raise ValueError("Rendimiento ausente en entrenamiento")
    if copia.loc[~train, "RENDIMIENTO_T_HA"].notna().any():
        raise ValueError("Etiqueta visible en PREDICCION")
    y = copia.loc[train, "RENDIMIENTO_T_HA"]
    if not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("Rendimiento observado no positivo o no finito")
    return copia


def validar_satelite(df):
    copia = df.copy(deep=True)
    requeridas = {"ID_POLIGONO", "fecha_captura", "sensor", "porcentaje_nubosidad"}
    if not requeridas <= set(copia.columns):
        raise ValueError("Columnas satelitales requeridas ausentes")
    if copia[["ID_POLIGONO", "fecha_captura", "sensor"]].isna().any().any():
        raise ValueError("ID, fecha o sensor ausente")
    if not copia.ID_POLIGONO.astype(str).str.fullmatch(r"AGC_\d{3}").all():
        raise ValueError("ID satelital mal formado")
    if copia.sensor.astype(str).str.strip().eq("").any():
        raise ValueError("Sensor vacío")
    if not copia.fecha_captura.astype(str).str.fullmatch(r"\d{2}/\d{2}/\d{4}").all():
        raise ValueError("Fecha satelital no tiene formato dd/mm/aaaa")
    copia["FECHA"] = pd.to_datetime(copia.fecha_captura, format="%d/%m/%Y", errors="raise")
    if copia.duplicated(["ID_POLIGONO", "FECHA", "sensor"]).any():
        raise ValueError("Observación parcela-fecha-sensor duplicada")
    nube = pd.to_numeric(copia.porcentaje_nubosidad, errors="raise")
    presentes = nube.dropna()
    if not np.isfinite(presentes).all() or not presentes.between(0, 100).all():
        raise ValueError("Nubosidad fuera de 0–100 o no finita")
    return copia


def leer_geometrias(z):
    contenido = z.read(miembro_unico(z, "Parcelas_Reto_AGC_CONJUNTO_70_30.zip"))
    with zipfile.ZipFile(io.BytesIO(contenido)) as interno:
        validar_zip(interno)
        lector = shapefile.Reader(
            shp=io.BytesIO(interno.read(miembro_unico(interno, ".shp"))),
            shx=io.BytesIO(interno.read(miembro_unico(interno, ".shx"))),
            dbf=io.BytesIO(interno.read(miembro_unico(interno, ".dbf"))),
            encoding="utf-8", encodingErrors="strict",
        )
        crs = CRS.from_wkt(interno.read(miembro_unico(interno, ".prj")).decode("utf-8"))
        registros = list(lector.iterShapeRecords())
        tabla = pd.DataFrame([r.record.as_dict() for r in registros]).rename(columns={
            "ID_POLIGON": "ID_POLIGONO", "área_ha": "AREA_HA_GEOMETRIA",
            "CONJUNTO": "CONJUNTO_GEOMETRIA",
        })
        geometrias = [shape(r.shape.__geo_interface__) for r in registros]
        lector.close()
    esperadas = {
        "ID_POLIGONO", "AREA_HA_GEOMETRIA", "CONJUNTO_GEOMETRIA", "Estado", "Municipio", "Cultivo",
    }
    if set(tabla.columns) != esperadas or tabla.ID_POLIGONO.duplicated().any():
        raise ValueError("Esquema o identificadores del shapefile inesperados")
    if any(g.is_empty or not g.is_valid or g.geom_type not in {"Polygon", "MultiPolygon"}
           for g in geometrias):
        raise ValueError("Geometría inválida/vacía/no poligonal: se requiere revisión, no reparación")
    if len(tabla) != len(geometrias):
        raise ValueError("Geometrías y atributos no alineados")
    return tabla, geometrias, crs
