"""Orquestación pura: originales → recetas por parcela → tabla sin rendimiento.

Adaptación del 7/oct/2026 de la integración del 21/sep/2026. Las funciones reciben
objetos en memoria; no dependen de una bóveda, Excel, un repositorio o ficheros
extraídos. Las funciones auxiliares también se incrustan en el notebook.
"""

from __future__ import annotations

import io
import re
import zipfile

import numpy as np
import pandas as pd

from auditoria_01 import (
    leer_csv,
    leer_geometrias,
    miembro_unico,
    normalizar_catalogo,
    validar_satelite,
    validar_zip,
)
from fuentes_02_geo import analizar_raster, extraer_raster, metadatos_geo
from fuentes_02_satelite import construir_satelite as construir_satelite
from fuentes_02_satelite import diccionario_sat

ARCHIVOS_RASTER = {
    "precipitacion": "Reto_AgroCebada_CHIRPS_Precipitacion_2022_2025.zip",
    "temperatura": "Reto_AgroCebada_Temperatura_2022_2025_RECORTADA_CHIRPS.zip",
    "topografia": "Reto_AgroCebada_Topografia_INEGI_CEM4.zip",
}


def cargar_fuentes(zip_fuente):
    """Lee y valida originales. Las etiquetas salen aparte, nunca hacia las recetas."""
    catalogo = normalizar_catalogo(
        leer_csv(zip_fuente, "ID_area_rendimiento_70_30_Reto_AgroCebada.csv")
    )
    basico = validar_satelite(leer_csv(zip_fuente, "Conjunto_datos_BASICO_AgroCebada2026.csv"))
    pro = validar_satelite(leer_csv(zip_fuente, "Conjunto_datos_PRO_AgroCebada.csv"))
    atributos, geometrias, crs = leer_geometrias(zip_fuente)
    ids = set(catalogo.ID_POLIGONO)
    if ids != set(atributos.ID_POLIGONO):
        raise ValueError("IDs de catálogo y geometrías distintos")
    for df in (basico, pro):
        if not set(df.ID_POLIGONO) <= ids:
            raise ValueError("ID satelital no presente en catálogo")
    # El lector 01 ya normaliza nombres del DBF; la receta geométrica conserva
    # el contrato de atributos originales. Renombrar no altera sus valores.
    atributos_geo = atributos.rename(
        columns={
            "ID_POLIGONO": "ID_POLIGON",
            "AREA_HA_GEOMETRIA": "área_ha",
            "CONJUNTO_GEOMETRIA": "CONJUNTO",
        }
    )
    geoms, meta = metadatos_geo(atributos_geo, geometrias, crs)
    descripcion = (
        catalogo.drop(columns="RENDIMIENTO_T_HA")
        .merge(meta, on="ID_POLIGONO", validate="one_to_one")
        .sort_values("ID_POLIGONO")
        .reset_index(drop=True)
    )
    if not descripcion.CONJUNTO.eq(descripcion.CONJUNTO_shp).all():
        raise ValueError("CONJUNTO del catálogo y geometría no coincide")
    if not np.allclose(descripcion.AREA_HA, descripcion.AREA_HA_shp, rtol=0, atol=1e-10):
        raise ValueError("Área entregada y área del DBF no coinciden")
    descripcion["dif_area_pct"] = (
        (descripcion.area_geom_ha - descripcion.AREA_HA) / descripcion.AREA_HA * 100
    )
    descripcion = descripcion.drop(columns=["CONJUNTO_shp", "AREA_HA_shp"])
    etiquetas = catalogo.loc[
        catalogo.CONJUNTO.eq("ENTRENAMIENTO"), ["ID_POLIGONO", "RENDIMIENTO_T_HA"]
    ].copy()
    return {
        "metadatos": descripcion,
        "etiquetas": etiquetas,
        "basico": basico,
        "pro": pro,
        "geometrias": geoms,
        "crs_geometrias": crs,
    }


def leer_rasters(zip_fuente):
    """Inventario y bytes verificados de 146 GeoTIFF; no escribe ZIP internos."""
    rasters = {}
    filas = []
    for grupo, nombre in ARCHIVOS_RASTER.items():
        contenido = zip_fuente.read(miembro_unico(zip_fuente, nombre))
        with zipfile.ZipFile(io.BytesIO(contenido)) as interno:
            validar_zip(interno)
            for info in sorted(interno.infolist(), key=lambda item: item.filename):
                if info.is_dir() or not info.filename.lower().endswith((".tif", ".tiff")):
                    continue
                archivo = info.filename.rsplit("/", 1)[-1]
                if archivo in rasters:
                    raise ValueError(f"GeoTIFF con nombre ambiguo: {archivo}")
                bruto = interno.read(info)
                rasters[archivo] = bruto
                filas.append({"grupo": grupo, "archivo": archivo, **analizar_raster(bruto)})
    if not filas:
        raise ValueError("Inventario sin rásteres")
    tabla = pd.DataFrame(filas)
    if len(rasters) != 146:
        raise ValueError("El inventario no contiene los 146 rásteres esperados")
    return rasters, tabla


def extraer_clima(rasters, geoms, crs, cache=None):
    """144 meses × parcelas; conserva receta histórica y añade coberturas aparte."""
    cache = {} if cache is None else cache
    filas = []
    for archivo, bruto in sorted(rasters.items()):
        captura = re.fullmatch(r"(PREC|Tmin|Tmax)_(202[2-5])_(\d{2})\.tif", archivo)
        if captura is None:
            continue
        variable, anio, mes = captura.groups()
        if not 1 <= int(mes) <= 12:
            raise ValueError("Mes climático fuera de 1–12")
        resultado = extraer_raster(bruto, geoms, crs, cache=cache)
        for parcela, valores in resultado.items():
            filas.append(
                {
                    "ID_POLIGONO": parcela,
                    "variable": {"PREC": "prec", "Tmin": "tmin", "Tmax": "tmax"}[variable],
                    "anio": int(anio),
                    "mes": int(mes),
                    "archivo": archivo,
                    **valores,
                }
            )
    if not filas:
        raise ValueError("Clima mensual incompleto: no se encontraron rásteres climáticos")
    tabla = pd.DataFrame(filas)
    esperados = {
        (v, a, m) for v in ("prec", "tmin", "tmax") for a in range(2022, 2026) for m in range(1, 13)
    }
    claves = set(zip(tabla.variable, tabla.anio, tabla.mes, strict=True))
    if claves != esperados or len(tabla) != len(geoms) * 144:
        raise ValueError("Clima mensual incompleto")
    if tabla.duplicated(["ID_POLIGONO", "variable", "anio", "mes"]).any():
        raise ValueError("Clave mensual duplicada")
    return tabla


def resumir_clima(largo, config):
    """Ventana de meses completos de un año; mm sumados y °C por días reales."""
    vo, vf = (pd.Timestamp(config["ventana_objetivo"][k]) for k in ("inicio", "fin"))
    meses = pd.date_range(vo, vf, freq="MS")
    if (
        not len(meses)
        or vo.year != vf.year
        or vo.day != 1
        or vf != meses[-1] + pd.offsets.MonthEnd(0)
    ):
        raise ValueError("El clima requiere una ventana de meses completos dentro de un año")
    mm = list(meses.month)
    ids = sorted(largo.ID_POLIGONO.unique())
    salida = pd.DataFrame(index=pd.Index(ids, name="ID_POLIGONO"))

    def piv(variable, anio, columna="pond"):
        filas = largo.loc[largo.variable.eq(variable) & largo.anio.eq(anio) & largo.mes.isin(mm)]
        return filas.pivot(index="ID_POLIGONO", columns="mes", values=columna).reindex(
            index=ids, columns=mm
        )

    anio_actual = vo.year
    for variable, unidad in (("prec", "mm"), ("tmin", "C"), ("tmax", "C")):
        valores = piv(variable, anio_actual)
        for mes in mm:
            salida[f"clim_{variable}_{anio_actual}_{mes:02d}_{unidad}"] = valores[mes]
    salida["clim_prec_ciclo_mm"] = piv("prec", anio_actual).sum(axis=1, min_count=len(mm))
    salida["clim_prec_ciclo_ctrl_centroide_mm"] = piv("prec", anio_actual, "cent").sum(
        axis=1, min_count=len(mm)
    )
    salida["clim_prec_ciclo_dif_pond_menos_cent_mm"] = (
        salida.clim_prec_ciclo_mm - salida.clim_prec_ciclo_ctrl_centroide_mm
    )
    for variable in ("tmin", "tmax"):
        salida[f"clim_{variable}_ciclo_C"] = np.average(
            piv(variable, anio_actual), axis=1, weights=meses.days_in_month.to_numpy()
        )
    salida["clim_amplitud_ciclo_C"] = salida.clim_tmax_ciclo_C - salida.clim_tmin_ciclo_C
    for anio in config["historico"]["anios"]:
        dias = pd.DatetimeIndex([pd.Timestamp(anio, mes, 1) for mes in mm]).days_in_month.to_numpy()
        salida[f"clim_prec_ciclo_H{anio}_mm"] = piv("prec", anio).sum(axis=1, min_count=len(mm))
        for variable in ("tmin", "tmax"):
            salida[f"clim_{variable}_ciclo_H{anio}_C"] = np.average(
                piv(variable, anio), axis=1, weights=dias
            )
    for variable, tag in (("prec", "prec"), ("tmin", "temp")):
        q = largo.loc[
            largo.variable.eq(variable) & largo.anio.eq(anio_actual) & largo.mes.eq(mm[0])
        ].set_index("ID_POLIGONO")
        salida[f"clim_q_n_celdas_{tag}"] = q.n_celdas
        salida[f"clim_q_frac_area_valida_{tag}"] = q.frac_valida
        salida[f"clim_q_celda_centroide_{tag}"] = q.celda_centroide
    return salida


def extraer_topografia(rasters, geoms, crs, cache=None):
    """Dos superficies; no calcula pendiente desde elevación ni impone cobertura nueva."""
    cache = {} if cache is None else cache
    filas, controles = {}, []
    reconocidos = set()
    for archivo, bruto in sorted(rasters.items()):
        if re.fullmatch(r"(PREC|Tmin|Tmax)_202[2-5]_\d{2}\.tif", archivo):
            continue
        if "Elevacion" in archivo:
            variable, unidad = "elev", "m"
        elif "Pendiente" in archivo:
            variable, unidad = "pend", "grados"
        else:
            raise ValueError(f"Ráster topográfico no identificado: {archivo}")
        if variable in reconocidos:
            raise ValueError(f"Ráster topográfico repetido: {variable}")
        reconocidos.add(variable)
        for parcela, dato in extraer_raster(bruto, geoms, crs, cache=cache, stats=True).items():
            fila = filas.setdefault(parcela, {"ID_POLIGONO": parcela})
            fila.update(
                {
                    f"topo_{variable}_media_{unidad}": dato["pond"],
                    f"topo_{variable}_min_{unidad}": dato["min"],
                    f"topo_{variable}_max_{unidad}": dato["max"],
                    f"topo_{variable}_std_{unidad}": dato["std"],
                    f"topo_{variable}_rango_{unidad}": dato["max"] - dato["min"],
                    f"topo_{variable}_npix": dato["n_validos"],
                    f"topo_{variable}_cobertura": dato["frac_valida"],
                    f"topo_{variable}_ctrl_centroide_{unidad}": dato["cent"],
                }
            )
            controles.append(
                {"ID_POLIGONO": parcela, "variable": variable, "archivo": archivo, **dato}
            )
    if reconocidos != {"elev", "pend"}:
        raise ValueError("Se requieren elevación y pendiente")
    return pd.DataFrame(filas.values()).set_index("ID_POLIGONO"), pd.DataFrame(controles)


def describir_variable(columna, config):
    """Diccionario de las recetas; los metadatos y controles no son predictores finales."""
    meta = {
        "ID_POLIGONO": ("clave", "identificador", "CSV y geometrías", "ID único; no predictor"),
        "AREA_HA": ("candidata", "ha", "CSV de catálogo", "Área entregada"),
        "CONJUNTO": (
            "metadato_excluir",
            "categoría",
            "CSV de catálogo",
            "Rol oficial; excluir como predictor",
        ),
        "Estado": ("metadato_territorial", "categoría", "Shapefile", "Estado entregado"),
        "Municipio": ("metadato_territorial", "categoría", "Shapefile", "Municipio entregado"),
        "cultivo_grafia_original": (
            "metadato_excluir",
            "texto",
            "Shapefile",
            "Grafía original; posible huella de procedencia",
        ),
        "area_geom_ha": ("control", "ha", "Polígono", "Área proyectada EPSG:32614"),
        "dif_area_pct": (
            "bandera_calidad",
            "%",
            "Polígono y catálogo",
            "100*(área geométrica−entregada)/entregada",
        ),
        "x_m": ("metadato_territorial", "m", "Polígono", "Centroide de área en EPSG:32614"),
        "y_m": ("metadato_territorial", "m", "Polígono", "Centroide de área en EPSG:32614"),
        "longitude": (
            "metadato_territorial",
            "grados",
            "Polígono",
            "Centroide UTM reproyectado a longitud",
        ),
        "latitude": (
            "metadato_territorial",
            "grados",
            "Polígono",
            "Centroide UTM reproyectado a latitud",
        ),
        "geom_valida_original": (
            "bandera_calidad",
            "booleano",
            "Polígono",
            "Validez original GEOS; sin reparación",
        ),
        "geom_vertices_repetidos": (
            "bandera_calidad",
            "vértices",
            "Polígono",
            "Vértices consecutivos repetidos",
        ),
    }
    if columna in meta:
        rol, unidad, fuente, agregacion = meta[columna]
        return dict(
            variable=columna,
            bloque="metadatos",
            rol=rol,
            unidad=unidad,
            fuente=fuente,
            sensor="",
            indice="",
            ventana="estática",
            agregacion=agregacion,
            filtro="",
        )
    if columna.startswith(("C_", "H20", "P_")):
        return diccionario_sat(columna, config)
    if columna.startswith("clim_"):
        rol = (
            "bandera_calidad"
            if "_q_" in columna
            else (
                "control" if "ctrl_centroide" in columna or "dif_pond" in columna else "candidata"
            )
        )
        unidad = "mm" if columna.endswith("_mm") else ("°C" if columna.endswith("_C") else "")
        if "_q_n_celdas" in columna:
            unidad = "celdas"
        elif "_q_frac_area" in columna:
            unidad = "fracción"
        elif "_q_celda_" in columna:
            unidad = "fila_columna"
        periodo = (
            f"{columna.split('_H')[1][:4]}-04..10"
            if "_H20" in columna
            else f"{config['ventana_objetivo']['inicio']}..{config['ventana_objetivo']['fin']}"
        )
        agregacion = (
            "Suma mensual"
            if "prec_ciclo" in columna
            else "Media ponderada por días del mes"
            if "ciclo" in columna
            else "Valor mensual"
        )
        mensual = re.fullmatch(r"clim_(?:prec|tmin|tmax)_(\d{4})_(\d{2})_(?:mm|C)", columna)
        if mensual:
            anio, mes = mensual.groups()
            fecha = pd.Timestamp(int(anio), int(mes), 1)
            periodo = f"{fecha.date()}..{(fecha + pd.offsets.MonthEnd(0)).date()}"
        if columna == "clim_amplitud_ciclo_C":
            agregacion = "Tmax del ciclo menos Tmin del ciclo"
        elif columna == "clim_prec_ciclo_dif_pond_menos_cent_mm":
            agregacion = "Acumulado ponderado por área menos acumulado por centroide"
        if "_q_" in columna:
            periodo, agregacion = "malla del primer mes del ciclo", "Control de malla/cobertura"
        espacial = (
            "Celda del centroide planar del ráster"
            if "ctrl_centroide" in columna
            else ("Áreas de intersección en EPSG:32614; normalización sobre área válida")
        )
        return dict(
            variable=columna,
            bloque="clima",
            rol=rol,
            fuente="GeoTIFF climáticos originales",
            sensor="",
            indice="",
            ventana=periodo,
            agregacion=f"{agregacion}; {espacial}",
            filtro="Máscara, NoData y no finitos excluidos",
            unidad=unidad,
        )
    if columna.startswith("topo_"):
        rol = (
            "control"
            if "ctrl_centroide" in columna
            else ("bandera_calidad" if columna.endswith(("npix", "cobertura")) else "candidata")
        )
        unidad = (
            "m"
            if columna.endswith("_m")
            else (
                "grados"
                if columna.endswith("grados")
                else "píxeles"
                if columna.endswith("npix")
                else "fracción"
            )
        )
        agregacion = "Estadística zonal en CRS nativo EPSG:6372; std poblacional ponderada"
        if "ctrl_centroide" in columna:
            agregacion = "Valor de celda bajo el centroide planar de la parcela en EPSG:6372"
        elif columna.endswith("cobertura"):
            agregacion = "Área con dato válido dividida por área de intersecciones dentro de malla"
        elif columna.endswith("npix"):
            agregacion = "Número de celdas con intersección de área positiva y dato válido"
        return dict(
            variable=columna,
            bloque="topografia",
            rol=rol,
            fuente="GeoTIFF topográficos originales",
            sensor="",
            indice="",
            ventana="estática",
            agregacion=agregacion,
            filtro="Máscara, NoData y no finitos excluidos; cobertura reportada",
            unidad=unidad,
        )
    raise ValueError(f"Variable sin receta: {columna}")


def ensamblar_variables(meta, ciclo, historico, clima, topo):
    """No acepta ni usa rendimiento. Joins uno a uno sin imputación ni aprendizaje."""
    piezas = [meta.set_index("ID_POLIGONO"), ciclo, historico, clima, topo]
    ids = piezas[0].index
    nombres = []
    for pieza in piezas:
        if not pieza.index.is_unique or set(pieza.index) != set(ids):
            raise ValueError("Las fuentes no tienen los mismos IDs únicos")
        nombres.extend(pieza.columns)
    if len(nombres) != len(set(nombres)) or any("RENDIMIENTO" in c.upper() for c in nombres):
        raise ValueError("Nombre duplicado o rendimiento entre las variables")
    return pd.concat([p.reindex(ids) for p in piezas], axis=1).reset_index()


def comparar_referencia(calculada, referencia):
    """Contrasta la salida histórica; no la incorpora a ninguna transformación."""
    if list(calculada.columns) != list(referencia.columns):
        raise ValueError("Esquema o orden de columnas distinto del control histórico")
    if any(
        df.ID_POLIGONO.isna().any() or not df.ID_POLIGONO.is_unique
        for df in (calculada, referencia)
    ):
        raise ValueError("El control requiere IDs únicos y no nulos")
    a, b = (df.set_index("ID_POLIGONO").sort_index() for df in (calculada, referencia))
    if not a.index.equals(b.index):
        raise ValueError("IDs del control histórico distintos")
    filas = []
    for columna in a.columns:
        x, y = a[columna], b[columna]
        if not x.isna().equals(y.isna()):
            raise ValueError(f"Máscara de faltantes diferente: {columna}")
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            diferencia = float((x.astype(float) - y.astype(float)).abs().max())
            es_conteo = columna.endswith(
                (
                    "_n",
                    "_npix",
                    "_n_celdas_prec",
                    "_n_celdas_temp",
                    "_q_filas_ventana",
                    "_q_con_indice",
                    "_q_nube100",
                    "_q_nube_desconocida",
                )
            ) or pd.api.types.is_bool_dtype(x)
            tolerancia = 0.0 if es_conteo else (1e-4 if columna.startswith("topo_") else 1e-8)
            coincide = bool(
                np.allclose(
                    x.astype(float), y.astype(float), rtol=0, atol=tolerancia, equal_nan=True
                )
            )
        else:
            diferencia, tolerancia = 0.0, 0.0
            coincide = bool(
                x.fillna("<FALTANTE>").astype(str).eq(y.fillna("<FALTANTE>").astype(str)).all()
            )
        filas.append(
            {
                "variable": columna,
                "diferencia_maxima": diferencia,
                "tolerancia_absoluta": tolerancia,
                "coincide": coincide,
            }
        )
    return pd.DataFrame(filas)
