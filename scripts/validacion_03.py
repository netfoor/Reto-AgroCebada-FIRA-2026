"""Reconstrucción retrospectiva de GLOBAL/MUN/MIX y evaluación OOF.

Adaptación del 7/oct/2026 de integracion_v0/agro_v0/evaluacion.py y
particiones.py. Se conservan las referencias del 20–21/sep/2026, el orden de
entrenamiento y np.argsort de la receta IDW original. Las particiones internas
de ronda1/ejecutar_ronda1.py se verifican, sin seleccionar ajustes ni entrenar
candidatos. No se crean predicciones de las 59 parcelas sin etiqueta.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd


MODELOS_03 = ("GLOBAL", "MUN", "MIX")
ALIAS_HISTORICOS_03 = {
    "Media global": "GLOBAL",
    "Media municipal": "MUN",
    "Municipio + IDW fijo": "MIX",
}
ROLES_03 = {"entrenamiento", "validacion"}
CLAVES_OOF_03 = ["modelo", "repeticion", "pliegue", "ID_POLIGONO"]


def _ids_03(ids):
    valores = list(ids)
    indice = pd.Index(valores)
    if (
        not valores
        or indice.hasnans
        or not indice.is_unique
        or any(not isinstance(x, str) or not x.strip() for x in valores)
    ):
        raise ValueError("Se requieren IDs únicos, no vacíos y no nulos")
    return set(valores)


def _columnas_03(tabla, columnas):
    if not tabla.columns.is_unique:
        raise ValueError("Columnas duplicadas")
    faltan = set(columnas) - set(tabla.columns)
    if faltan:
        raise ValueError(f"Faltan columnas: {sorted(faltan)}")


def _enteros_03(tabla, columnas):
    for columna in columnas:
        s = tabla[columna]
        if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
            raise ValueError(f"{columna} requiere enteros numéricos")
        v = s.to_numpy(dtype=float)
        if not np.isfinite(v).all() or not np.equal(v, np.floor(v)).all() or (v < 0).any():
            raise ValueError(f"{columna} contiene valores no enteros, negativos o no finitos")


def _roles_03(tabla, columnas):
    _columnas_03(tabla, columnas + ["rol", "ID_POLIGONO"])
    if tabla.empty or tabla.rol.isna().any() or not set(tabla.rol) <= ROLES_03:
        raise ValueError("Particiones vacías o roles inválidos")
    if tabla.ID_POLIGONO.isna().any():
        raise ValueError("ID nulo en particiones")
    _enteros_03(tabla, columnas)
    if tabla.duplicated(columnas + ["ID_POLIGONO"]).any():
        raise ValueError("ID duplicado o solapamiento entre entrenamiento y validación")


def validar_externas(externas, ids, n_repeticiones=10, n_pliegues=5):
    """Cada ID se valida una vez por repetición; cada pliegue cubre todo el catálogo visible."""
    esperados = _ids_03(ids)
    _roles_03(externas, ["repeticion", "pliegue"])
    if set(externas.ID_POLIGONO) != esperados:
        raise ValueError("IDs externos distintos de las parcelas etiquetadas")
    if set(externas.repeticion) != set(range(n_repeticiones)):
        raise ValueError("Repeticiones externas incompletas o no comienzan en cero")
    for repeticion, grupo in externas.groupby("repeticion", sort=True):
        if set(grupo.pliegue) != set(range(n_pliegues)):
            raise ValueError(f"Pliegues externos incompletos en repetición {repeticion}")
        val = grupo.loc[grupo.rol.eq("validacion")]
        if set(val.ID_POLIGONO) != esperados or not val.ID_POLIGONO.is_unique:
            raise ValueError("Cada ID debe aparecer una vez en validación por repetición")
    tamanos = []
    for clave, grupo in externas.groupby(["repeticion", "pliegue"], sort=True):
        if set(grupo.ID_POLIGONO) != esperados or set(grupo.rol) != ROLES_03:
            raise ValueError(f"Pliegue externo {clave} incompleto o sin ambos roles")
        tamanos.append(int(grupo.rol.eq("validacion").sum()))
    return {
        "repeticiones": n_repeticiones,
        "pliegues_por_repeticion": [n_pliegues],
        "parcelas": len(esperados),
        "filas": len(externas),
        "validacion_por_pliegue": sorted(set(tamanos)),
        "n_particiones": n_repeticiones * n_pliegues,
    }


def validar_internas(
    internas, externas, ids, n_repeticiones=10, n_pliegues=5, n_pliegues_internos=4
):
    """Las internas contienen exactamente entrenamiento exterior y jamás su validación."""
    validar_externas(externas, ids, n_repeticiones, n_pliegues)
    _roles_03(internas, ["repeticion", "pliegue", "pliegue_interno"])
    claves = set(
        map(
            tuple,
            externas[["repeticion", "pliegue"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    recibidas = set(
        map(
            tuple,
            internas[["repeticion", "pliegue"]]
            .drop_duplicates()
            .itertuples(index=False, name=None),
        )
    )
    if claves != recibidas:
        raise ValueError("Las internas no cubren exactamente todos los pliegues externos")
    exteriores = {k: g for k, g in externas.groupby(["repeticion", "pliegue"], sort=True)}
    for clave, grupo in internas.groupby(["repeticion", "pliegue"], sort=True):
        exterior = exteriores[clave]
        tr = set(exterior.loc[exterior.rol.eq("entrenamiento"), "ID_POLIGONO"])
        va = set(exterior.loc[exterior.rol.eq("validacion"), "ID_POLIGONO"])
        if set(grupo.ID_POLIGONO) & va:
            raise ValueError(f"Validación externa presente en internas de {clave}")
        if set(grupo.pliegue_interno) != set(range(n_pliegues_internos)):
            raise ValueError(f"Pliegues internos incompletos en {clave}")
        for interno, subgrupo in grupo.groupby("pliegue_interno"):
            if set(subgrupo.ID_POLIGONO) != tr or set(subgrupo.rol) != ROLES_03:
                raise ValueError(
                    f"Interna {clave}/{interno} no contiene exactamente entrenamiento exterior"
                )
        validacion = grupo.loc[grupo.rol.eq("validacion")]
        if set(validacion.ID_POLIGONO) != tr or not validacion.ID_POLIGONO.is_unique:
            raise ValueError("Cada ID exterior de entrenamiento debe validarse una vez en internas")
    return {
        "particiones_externas": len(claves),
        "pliegues_internos_por_externa": [n_pliegues_internos],
        "filas": len(internas),
        "contencion_ok": True,
        "sin_validacion_externa_en_internas": True,
    }


def particiones_desde_csv(externas, tabla_entrenamiento, n_repeticiones=10, n_pliegues=5):
    """(repetición, pliegue, índices tr, índices va), manteniendo orden de la tabla original."""
    _columnas_03(tabla_entrenamiento, ["ID_POLIGONO"])
    validar_externas(externas, tabla_entrenamiento.ID_POLIGONO, n_repeticiones, n_pliegues)
    posiciones = {
        identificador: i for i, identificador in enumerate(tabla_entrenamiento.ID_POLIGONO)
    }
    resultado = []
    for (r, f), grupo in externas.groupby(["repeticion", "pliegue"], sort=True):
        tr = np.asarray(
            sorted(posiciones[i] for i in grupo.loc[grupo.rol.eq("entrenamiento"), "ID_POLIGONO"]),
            dtype=int,
        )
        va = np.asarray(
            sorted(posiciones[i] for i in grupo.loc[grupo.rol.eq("validacion"), "ID_POLIGONO"]),
            dtype=int,
        )
        resultado.append((int(r), int(f), tr, va))
    return resultado


def validar_recetas_referencias(config):
    """Impide declarar parámetros distintos de la receta fija realmente reconstruida."""
    mix = config["referencias"]["MIX"]
    esperado = {
        "peso_municipal": 0.5,
        "idw_k": 20,
        "idw_potencia": 2,
        "distancia_minima_m": 1.0,
        "crs_distancias": "EPSG:32614",
    }
    if any(mix.get(k) != v for k, v in esperado.items()):
        raise ValueError("La configuración MIX no coincide con la receta histórica fija")
    if config["referencias"]["MUN"].get("municipio_no_visto") != "GLOBAL":
        raise ValueError("La referencia municipal requiere fallback GLOBAL")
    return True


def _tabla_referencia_03(tabla, entrenamiento):
    columnas = ["Municipio", "x_m", "y_m"] + (["RENDIMIENTO_T_HA"] if entrenamiento else [])
    _columnas_03(tabla, columnas)
    if entrenamiento and tabla.empty:
        raise ValueError("Entrenamiento vacío")
    if tabla.Municipio.isna().any() or tabla.Municipio.astype(str).str.strip().eq("").any():
        raise ValueError("Municipio ausente")
    numericas = ["x_m", "y_m"] + (["RENDIMIENTO_T_HA"] if entrenamiento else [])
    if not np.isfinite(tabla[numericas].to_numpy(dtype=float)).all():
        raise ValueError("Coordenadas o etiquetas de entrenamiento no finitas")


def predecir_referencias(a, t):
    """GLOBAL, MUN y MIX; ningún valor de rendimiento de t se consulta."""
    _tabla_referencia_03(a, True)
    _tabla_referencia_03(t, False)
    media = a.RENDIMIENTO_T_HA.mean()
    municipal = (
        t.Municipio.map(a.groupby("Municipio").RENDIMIENTO_T_HA.mean()).fillna(media).to_numpy()
    )
    axy, txy = a[["x_m", "y_m"]].to_numpy(), t[["x_m", "y_m"]].to_numpy()
    d = np.linalg.norm(txy[:, None, :] - axy[None, :, :], axis=2)
    idx = np.argsort(d, axis=1)[:, : min(20, len(a))]
    seleccion = np.take_along_axis(d, idx, axis=1)
    pesos = 1 / np.maximum(seleccion, 1.0) ** 2
    pesos /= pesos.sum(axis=1, keepdims=True)
    idw = (pesos * a.RENDIMIENTO_T_HA.to_numpy()[idx]).sum(axis=1)
    salida = {
        "GLOBAL": np.full(len(t), media),
        "MUN": municipal,
        "MIX": 0.5 * municipal + 0.5 * idw,
    }
    if not all(np.isfinite(v).all() for v in salida.values()):
        raise ValueError("Predicción no finita")
    return salida


def construir_oof(tabla138, externas, n_repeticiones=10, n_pliegues=5):
    """Una predicción por modelo/ID/repetición; municipio_visto usa solo pertenencia de grupos."""
    _columnas_03(tabla138, ["ID_POLIGONO"])
    _ids_03(tabla138.ID_POLIGONO)
    _tabla_referencia_03(tabla138, True)
    filas = []
    for r, f, tr, va in particiones_desde_csv(externas, tabla138, n_repeticiones, n_pliegues):
        a, t = tabla138.iloc[tr], tabla138.iloc[va]
        referencias = predecir_referencias(a, t)
        media = a.RENDIMIENTO_T_HA.mean()
        vistos = t.Municipio.isin(set(a.Municipio)).to_numpy()
        for modelo in MODELOS_03:
            for i, (_, registro) in enumerate(t.iterrows()):
                filas.append(
                    {
                        "modelo": modelo,
                        "repeticion": r,
                        "pliegue": f,
                        "ID_POLIGONO": registro.ID_POLIGONO,
                        "observado": registro.RENDIMIENTO_T_HA,
                        "predicho": float(referencias[modelo][i]),
                        "ref_media_entrenamiento": media,
                        "n_entrenamiento": len(a),
                        "n_validacion": len(t),
                        "municipio_visto": bool(vistos[i]),
                        "Municipio": registro.Municipio,
                    }
                )
    resultado = pd.DataFrame(filas)
    validar_oof(resultado, externas, n_repeticiones, n_pliegues)
    return resultado


def validar_oof(oof, externas, n_repeticiones=10, n_pliegues=5):
    """Comprueba claves exactas, observaciones consistentes, dimensiones y valores finitos."""
    ids = externas.ID_POLIGONO.drop_duplicates()
    validar_externas(externas, ids, n_repeticiones, n_pliegues)
    necesarias = CLAVES_OOF_03 + [
        "observado",
        "predicho",
        "ref_media_entrenamiento",
        "n_entrenamiento",
        "n_validacion",
        "municipio_visto",
        "Municipio",
    ]
    _columnas_03(oof, necesarias)
    if (
        set(oof.modelo) != set(MODELOS_03)
        or oof[CLAVES_OOF_03].isna().any().any()
        or oof.duplicated(CLAVES_OOF_03).any()
    ):
        raise ValueError("Modelos OOF inesperados, claves nulas o duplicadas")
    _enteros_03(oof, ["repeticion", "pliegue", "n_entrenamiento", "n_validacion"])
    if not np.isfinite(
        oof[["observado", "predicho", "ref_media_entrenamiento"]].to_numpy(dtype=float)
    ).all():
        raise ValueError("Valores OOF no finitos")
    if not pd.api.types.is_bool_dtype(oof.municipio_visto) or oof.municipio_visto.isna().any():
        raise ValueError("municipio_visto debe ser booleano no nulo")
    esperado = set(
        map(
            tuple,
            externas.loc[externas.rol.eq("validacion"), CLAVES_OOF_03[1:]].itertuples(
                index=False, name=None
            ),
        )
    )
    for modelo, grupo in oof.groupby("modelo"):
        recibido = set(map(tuple, grupo[CLAVES_OOF_03[1:]].itertuples(index=False, name=None)))
        if recibido != esperado:
            raise ValueError(f"{modelo}: claves OOF distintas de validación externa")
    if oof.groupby("ID_POLIGONO").observado.nunique().ne(1).any():
        raise ValueError("Observaciones distintas para el mismo ID")
    if (
        oof.Municipio.isna().any()
        or oof.Municipio.astype(str).str.strip().eq("").any()
        or oof.groupby("ID_POLIGONO").Municipio.nunique().ne(1).any()
    ):
        raise ValueError("Municipio nulo o inconsistente para el mismo ID")
    if oof.groupby(CLAVES_OOF_03[1:]).municipio_visto.nunique().ne(1).any():
        raise ValueError("Máscaras de municipios distintos entre modelos")
    if oof.groupby(["repeticion", "pliegue"]).ref_media_entrenamiento.nunique().ne(1).any():
        raise ValueError("Referencia media de entrenamiento inconsistente")
    tamanos = externas.groupby(["repeticion", "pliegue", "rol"]).size()
    municipio_por_id = oof.drop_duplicates("ID_POLIGONO").set_index("ID_POLIGONO").Municipio
    for (r, f), grupo in oof.groupby(["repeticion", "pliegue"]):
        if (
            not grupo.n_entrenamiento.eq(tamanos.loc[(r, f, "entrenamiento")]).all()
            or not grupo.n_validacion.eq(tamanos.loc[(r, f, "validacion")]).all()
        ):
            raise ValueError("Dimensiones OOF distintas de su partición")
        ids_tr = externas.loc[
            externas.repeticion.eq(r) & externas.pliegue.eq(f) & externas.rol.eq("entrenamiento"),
            "ID_POLIGONO",
        ]
        vistos = set(municipio_por_id.reindex(ids_tr))
        esperado_visto = grupo.Municipio.isin(vistos)
        if not grupo.municipio_visto.eq(esperado_visto).all():
            raise ValueError("municipio_visto no coincide con municipios de entrenamiento exterior")
    return {
        "modelos": list(MODELOS_03),
        "filas_por_modelo": len(esperado),
        "filas": len(oof),
        "parcelas": len(ids),
        "claves_completas": True,
        "valores_finitos": True,
    }


def metricas_regresion(y, p):
    """R² estándar con media del conjunto evaluado; SST<=1e-12 produce NaN."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if (
        y.ndim != 1
        or y.shape != p.shape
        or not len(y)
        or not np.isfinite(y).all()
        or not np.isfinite(p).all()
    ):
        raise ValueError("Se requieren vectores finitos, no vacíos y de igual longitud")
    error = p - y
    den = np.sum((y - y.mean()) ** 2)
    return {
        "RMSE": float(np.sqrt(np.mean(error**2))),
        "MAE": float(np.mean(np.abs(error))),
        "R2": float(1 - np.sum(error**2) / den) if den > 1e-12 else np.nan,
    }


def _escenario_03(oof, escenario):
    if escenario == "FULL138":
        return oof
    if escenario != "SEEN135":
        raise ValueError("Escenario desconocido")
    _columnas_03(oof, ["municipio_visto"])
    if not pd.api.types.is_bool_dtype(oof.municipio_visto) or oof.municipio_visto.isna().any():
        raise ValueError("Máscara SEEN ausente o no booleana")
    if oof.groupby(CLAVES_OOF_03[1:]).municipio_visto.nunique().ne(1).any():
        raise ValueError("La máscara SEEN debe ser igual para todos los modelos")
    return oof.loc[oof.municipio_visto]


def _resumir_03(oof, escenario, agrupadores):
    datos = _escenario_03(oof, escenario)
    _columnas_03(datos, ["modelo", "ID_POLIGONO", "observado", "predicho"] + agrupadores)
    if datos.empty:
        raise ValueError("Escenario sin predicciones OOF")
    filas = []
    for clave, grupo in datos.groupby(["modelo"] + agrupadores, sort=False):
        clave = clave if isinstance(clave, tuple) else (clave,)
        filas.append(
            {
                **dict(zip(["modelo"] + agrupadores, clave)),
                "escenario": escenario,
                "n_parcelas": grupo.ID_POLIGONO.nunique(),
                "n_oof": len(grupo),
                **metricas_regresion(grupo.observado, grupo.predicho),
            }
        )
    return pd.DataFrame(filas)


def resumen_metricas(oof, escenario="FULL138"):
    """Puntúa todas las predicciones OOF; no promedia predicciones ni métricas de pliegues."""
    return _resumir_03(oof, escenario, [])


def por_repeticion(oof, escenario="FULL138"):
    return _resumir_03(oof, escenario, ["repeticion"])


def por_municipio(oof, escenario="FULL138"):
    return _resumir_03(oof, escenario, ["Municipio"])


metricas_por_repeticion = por_repeticion
metricas_por_municipio = por_municipio


def comparar_oof(actual, control, tolerancia=1e-8):
    """Claves/observado/conteos exactos; predicciones y media a tolerancia absoluta.

    Normaliza solo nombres de modelos históricos conocidos. La cuarta referencia
    IDW sola se omite del control, nunca de la tabla calculada. El hash de bytes
    del insumo se comprueba antes de cargarlo; aquí se informa la huella de claves.
    """
    if not np.isfinite(tolerancia) or tolerancia < 0:
        raise ValueError("Tolerancia inválida")
    control = control.copy()
    control = control.loc[~control.modelo.eq("IDW k=20 solo")].copy()
    control["modelo"] = control.modelo.replace(ALIAS_HISTORICOS_03)
    columnas = CLAVES_OOF_03 + [
        "observado",
        "predicho",
        "ref_media_entrenamiento",
        "n_entrenamiento",
        "n_validacion",
    ]
    for df in (actual, control):
        _columnas_03(df, columnas)
        if (
            df[CLAVES_OOF_03].isna().any().any()
            or df.duplicated(CLAVES_OOF_03).any()
            or set(df.modelo) != set(MODELOS_03)
        ):
            raise ValueError("Control OOF con claves duplicadas/nulas o modelos desconocidos")
        _enteros_03(df, ["repeticion", "pliegue", "n_entrenamiento", "n_validacion"])
        if not np.isfinite(
            df[["observado", "predicho", "ref_media_entrenamiento"]].to_numpy(dtype=float)
        ).all():
            raise ValueError("Control OOF no finito")
    a, b = (df.set_index(CLAVES_OOF_03).sort_index() for df in (actual, control))
    if not a.index.equals(b.index):
        raise ValueError("Claves OOF distintas del control histórico")
    for columna in ("observado", "n_entrenamiento", "n_validacion"):
        if not np.array_equal(a[columna].to_numpy(), b[columna].to_numpy()):
            raise ValueError(f"{columna} distinto del control histórico")
    documento = [list(clave) for clave in a.index.tolist()]
    huella = hashlib.sha256(json.dumps(documento, ensure_ascii=False).encode()).hexdigest()
    filas = []
    for modelo in MODELOS_03:
        pred = float((a.loc[modelo, "predicho"] - b.loc[modelo, "predicho"]).abs().max())
        media = float(
            (a.loc[modelo, "ref_media_entrenamiento"] - b.loc[modelo, "ref_media_entrenamiento"])
            .abs()
            .max()
        )
        filas.append(
            {
                "modelo": modelo,
                "n_oof": len(a.loc[modelo]),
                "max_abs_dif_predicho": pred,
                "max_abs_dif_ref": media,
                "tolerancia": tolerancia,
                "coincide": pred <= tolerancia and media <= tolerancia,
                "sha256_claves": huella,
            }
        )
    return pd.DataFrame(filas)
