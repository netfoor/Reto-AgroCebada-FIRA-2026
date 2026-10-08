"""Recetas satelitales autocontenidas para el cuaderno 02.

Andrea: resúmenes por captura y extremos de las columnas entregadas, reconstruidos
y contrastados el 21 de septiembre de 2026 en la integración v0. Codex: integral
parcial por trapecios de ``reunion_utils.py``, incorporada en esa integración.
Adaptación educativa: 7 de octubre de 2026. Se conserva la receta de v0; los
diagnósticos de medias mensuales explican otra agregación y quedan separados.
Este módulo no lee archivos, no consulta etiquetas y no entrena modelos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


PROCEDENCIA_SATELITE = {
    "resumenes": "Andrea; reconstrucción y contraste de integración v0, 2026-09-21",
    "integral": "Codex, reunion_utils.partial_integral; integración v0, 2026-09-21",
    "adaptacion": "2026-10-07",
}
S2_IDX = [
    "ndvi",
    "evi",
    "crc",
    "mcrc",
    "ndsvi",
    "srndi",
    "mra",
    "lai",
    "fapar",
    "savi",
    "ndti",
    "sti",
    "ndwi",
    "endwi",
    "msi",
    "emsi",
    "dswi2",
    "dswi3",
    "dswi4",
    "dswi5",
    "nddi",
    "enddi",
]
SENSOR_IDX = {"S2": S2_IDX, "PL": ["ndvi", "evi", "lai", "msavi"], "LS": ["vi6t"]}
STATS = [
    "media",
    "mediana",
    "pico_prom",
    "doy_pico_prom",
    "integral",
    "dias_integ",
    "pixmax",
    "doy_pixmax",
    "pixmin",
    "std_media",
    "n",
]


def partial_integral(dates, values, max_gap_days=30):
    """Trapecios solo entre fechas válidas separadas como máximo por el hueco indicado.

    Los valores de fechas repetidas se promedian antes de integrar. No se añaden
    puntos al inicio o al final. Sin dos fechas compatibles: área NaN, días cero.
    El área conserva el signo del índice; no representa biomasa por definición.
    """
    d = pd.DataFrame({"date": pd.to_datetime(dates), "v": values}).dropna()
    d = d.sort_values("date").groupby("date", as_index=False).v.mean()
    if len(d) < 2:
        return np.nan, 0.0
    dt = np.diff(d.date.to_numpy()) / np.timedelta64(1, "D")
    valid = (dt > 0) & (dt <= max_gap_days)
    area = ((d.v.to_numpy()[1:] + d.v.to_numpy()[:-1]) / 2 * dt)[valid].sum()
    days = dt[valid].sum()
    return (float(area) if days > 0 else np.nan), float(days)


def eligible(d: pd.DataFrame, inicio, fin, nube_max):
    """Ventana inclusiva; sin umbral se conserva la nubosidad desconocida.

    La presencia de cada índice se comprueba después. Con un umbral, una nube
    desconocida queda excluida porque no se puede demostrar que lo cumple.
    """
    w = d[d.fecha.between(pd.Timestamp(inicio), pd.Timestamp(fin))]
    if nube_max is not None:
        w = w[w.porcentaje_nubosidad.le(nube_max)]
    return w


def lai_rule(s: pd.Series, regla: str) -> pd.Series:
    """Reglas explícitas de v0; la configuración histórica conserva negativos."""
    if regla == "conservar":
        return s
    if regla == "recortar_en_cero":
        return s.clip(lower=0)
    if regla == "anular_negativos":
        return s.where(s >= 0)
    raise ValueError(f"Regla LAI desconocida: {regla}")


def summarize(
    d, sensor, idxs, inicio, fin, nube_max, prefix, max_gap=30, lai_regla="conservar", ids=None
):
    """Once resúmenes por índice con la misma receta y orden de columnas que v0.

    La media y el pico usan *_promedio; pixmax usa *_max. La desviación media
    resume *_std dentro de cada captura, no la dispersión temporal de la curva.
    Sin observaciones se conservan NaN salvo n=0 y dias_integ=0.
    """
    w = eligible(d[d.S.eq(sensor)], inicio, fin, nube_max)
    w = w.sort_values(["ID_POLIGONO", "fecha"])
    ids = ids if ids is not None else sorted(d.ID_POLIGONO.unique())
    index = pd.Index(ids, name="ID_POLIGONO")
    columns = {}
    for ix in idxs:
        col, cmax, cmin, cstd = f"{ix}_promedio", f"{ix}_max", f"{ix}_min", f"{ix}_std"
        v = w[["ID_POLIGONO", "fecha", col, cmax, cmin, cstd]].copy()
        if ix == "lai":
            for c in (col, cmax, cmin):
                v[c] = lai_rule(v[c], lai_regla)
        v = v.dropna(subset=[col])
        g = v.groupby("ID_POLIGONO")
        p = f"{prefix}_{ix}"
        columns[f"{p}_media"] = g[col].mean()
        columns[f"{p}_mediana"] = g[col].median()
        pk = v.loc[g[col].idxmax()] if len(v) else v
        pk = pk.set_index("ID_POLIGONO")
        columns[f"{p}_pico_prom"] = pk[col]
        columns[f"{p}_doy_pico_prom"] = pk.fecha.dt.dayofyear
        integ = {k: partial_integral(q.fecha, q[col], max_gap) for k, q in g}
        columns[f"{p}_integral"] = pd.Series(
            {k: a for k, (a, _) in integ.items()},
            dtype=float,
        )
        columns[f"{p}_dias_integ"] = pd.Series(
            {k: b for k, (_, b) in integ.items()},
            dtype=float,
        ).reindex(index, fill_value=0.0)
        vm = v.dropna(subset=[cmax])
        px = vm.loc[vm.groupby("ID_POLIGONO")[cmax].idxmax()] if len(vm) else vm
        px = px.set_index("ID_POLIGONO")
        columns[f"{p}_pixmax"] = px[cmax]
        columns[f"{p}_doy_pixmax"] = px.fecha.dt.dayofyear
        columns[f"{p}_pixmin"] = g[cmin].min()
        columns[f"{p}_std_media"] = g[cstd].mean()
        columns[f"{p}_n"] = g.size().reindex(index, fill_value=0)
    return pd.DataFrame(columns, index=index)


def quality(d, sensor, ref_idx, inicio, fin, nube_max, prefix, ids):
    """Banderas v0; la nubosidad media usa toda la ventana, incluso índices ausentes.

    Fracción parcial, hueco y LAI negativo usan capturas admitidas con el índice
    de referencia disponible. No sustituyen la medición del índice faltante.
    """
    s = d[d.S.eq(sensor)]
    wall = s[s.fecha.between(pd.Timestamp(inicio), pd.Timestamp(fin))]
    w = eligible(s, inicio, fin, nube_max).dropna(subset=[f"{ref_idx}_promedio"])
    w = w.sort_values(["ID_POLIGONO", "fecha"])
    gall, g = wall.groupby("ID_POLIGONO"), w.groupby("ID_POLIGONO")
    columns = {
        f"{prefix}_q_filas_ventana": gall.size(),
        f"{prefix}_q_con_indice": gall[f"{ref_idx}_promedio"].count(),
        f"{prefix}_q_nube100": gall.porcentaje_nubosidad.apply(
            lambda x: int((x == 100).sum()),
        ),
        f"{prefix}_q_nube_desconocida": gall.porcentaje_nubosidad.apply(
            lambda x: int(x.isna().sum()),
        ),
        f"{prefix}_q_nube_media_pct": gall.porcentaje_nubosidad.mean(),
        f"{prefix}_q_frac_nube_parcial": g.porcentaje_nubosidad.apply(
            lambda x: float(((x > 0) & (x < 100)).mean()),
        ),
        f"{prefix}_q_hueco_max_dias": g.fecha.apply(lambda x: x.diff().dt.days.max()),
    }
    if "lai_promedio" in s.columns and sensor in ("S2", "PL"):
        columns[f"{prefix}_q_lai_frac_neg"] = g.lai_promedio.apply(
            lambda x: float((x < 0).mean()),
        )
    out = pd.DataFrame(columns, index=pd.Index(ids, name="ID_POLIGONO"))
    return out.fillna({c: 0 for c in out.columns if c.endswith(("_filas_ventana", "_con_indice"))})


def _adaptar_satelite(d, sensores, ids):
    """Adapta una copia del lector del cuaderno 01; no utiliza columnas adicionales."""
    necesarias = {"ID_POLIGONO", "FECHA", "sensor", "porcentaje_nubosidad"}
    if not necesarias <= set(d.columns):
        raise ValueError("Se requiere la tabla satelital validada del cuaderno 01 (FECHA).")
    if set(d.sensor) != set(sensores):
        raise ValueError("Sensores inesperados o ausentes en el archivo satelital.")
    if set(d.ID_POLIGONO) != set(ids):
        raise ValueError("Los IDs satelitales no coinciden con el catálogo.")
    if not pd.api.types.is_datetime64_any_dtype(d.FECHA):
        raise ValueError("FECHA debe estar validada como fecha antes de resumir.")
    if d.duplicated(["ID_POLIGONO", "FECHA", "sensor"]).any():
        raise ValueError("Capturas parcela-fecha-sensor duplicadas.")
    columnas = ["ID_POLIGONO", "sensor", "porcentaje_nubosidad", "FECHA"]
    columnas += [c for c in d if c.endswith(("_promedio", "_max", "_min", "_std"))]
    out = d[columnas].copy(deep=True).reset_index(drop=True)
    out["fecha"] = out.FECHA
    out["S"] = out.sensor.map(sensores)
    return out


def construir_satelite(basico_validado, pro_validado, ids, config):
    """Devuelve ciclo, histórico y postciclo separados, con índice ID_POLIGONO.

    La configuración v0 da 320, 147 y 121 columnas respectivamente para todos
    los IDs suministrados. No se incorpora postciclo a la base del ciclo 2025.
    """
    ids = list(ids)
    if not pd.Index(ids).is_unique or not ids:
        raise ValueError("Se requiere una lista no vacía de IDs únicos.")
    b = _adaptar_satelite(basico_validado, {"Sentinel-2": "S2", "Landsat": "LS"}, ids)
    p = _adaptar_satelite(pro_validado, {"Planet": "PL"}, ids)
    src = {"S2": b, "LS": b, "PL": p}
    ref = {"S2": "ndvi", "LS": "vi6t", "PL": "ndvi"}
    ventana = config["ventana_objetivo"]
    nube = config["nubosidad_max_por_sensor"]
    gap, lai = config["integral_hueco_max_dias"], config["lai_negativos"]
    ciclo = [
        summarize(
            src[s],
            s,
            SENSOR_IDX[s],
            ventana["inicio"],
            ventana["fin"],
            nube[s],
            f"C_{s}",
            gap,
            lai,
            ids,
        )
        for s in src
    ]
    calidad = [
        quality(src[s], s, ref[s], ventana["inicio"], ventana["fin"], nube[s], f"C_{s}", ids)
        for s in src
    ]
    hist = config["historico"]
    keep = ["media", "pico_prom", "doy_pico_prom", "integral", "dias_integ", "std_media", "n"]
    historico = []
    for year in hist["anios"]:
        inicio = f"{year}-{hist['mes_inicio']:02d}-01"
        fin = pd.Timestamp(f"{year}-{hist['mes_fin']:02d}-01") + pd.offsets.MonthEnd(0)
        for sensor, indices in hist["indices"].items():
            prefix = f"H{year}_{sensor}"
            resumen = summarize(
                src[sensor], sensor, indices, inicio, fin, nube[sensor], prefix, gap, lai, ids
            )
            historico.append(resumen[[f"{prefix}_{ix}_{stat}" for ix in indices for stat in keep]])
    post = config["ventana_postciclo"]
    postciclo = [
        summarize(src[s], s, indices, post["inicio"], post["fin"], nube[s], f"P_{s}", gap, lai, ids)
        for s, indices in config["postciclo_indices"].items()
    ]
    return (
        pd.concat(ciclo + calidad, axis=1),
        pd.concat(historico, axis=1),
        pd.concat(postciclo, axis=1),
    )


def diccionario_sat(col, config):
    """Describe una variable satelital sin presentarla como predictor seleccionado."""
    parts = col.split("_")
    ventana_id, sensor = parts[:2]
    fuentes = {"S2": "BASICO · Sentinel-2", "LS": "BASICO · Landsat", "PL": "PRO · Planet"}
    if sensor not in fuentes or ventana_id not in ("C", "P") and not ventana_id.startswith("H20"):
        raise ValueError(f"Variable satelital desconocida: {col}")
    if ventana_id in ("C", "P"):
        window = config["ventana_objetivo" if ventana_id == "C" else "ventana_postciclo"]
        ventana = f"{window['inicio']}..{window['fin']}"
        bloque = "satelite_ciclo" if ventana_id == "C" else "satelite_postciclo"
    else:
        hist = config["historico"]
        ventana = (
            f"{ventana_id[1:]}-{hist['mes_inicio']:02d}..{ventana_id[1:]}-{hist['mes_fin']:02d}"
        )
        bloque = "satelite_historico"
    nube = config["nubosidad_max_por_sensor"][sensor]
    filtro = (
        f"índice presente; nubosidad ≤ {nube}; nubosidad desconocida excluida"
        if nube is not None
        else "índice presente (sin umbral de nubosidad)"
    )
    result = dict(
        variable=col,
        bloque=bloque,
        rol="candidata",
        fuente=fuentes[sensor],
        sensor=sensor,
        indice="",
        ventana=ventana,
        agregacion="",
        filtro=filtro,
        unidad="",
    )
    if parts[2] == "q":
        flag = "_".join(parts[3:])
        desc = {
            "filas_ventana": ("filas de toda la ventana, con o sin índice", "filas"),
            "con_indice": ("filas de la ventana con índice de referencia presente", "filas"),
            "nube100": ("filas de toda la ventana con nubosidad 100 %", "filas"),
            "nube_desconocida": ("filas de toda la ventana con nubosidad ausente", "filas"),
            "nube_media_pct": ("media de nubosidad de toda la ventana", "%"),
            "frac_nube_parcial": (
                "fracción 0 < nube < 100 entre capturas admitidas con índice",
                "fracción",
            ),
            "hueco_max_dias": (
                "mayor hueco entre capturas admitidas con índice de referencia",
                "días",
            ),
            "lai_frac_neg": (
                "fracción LAI < 0 entre capturas admitidas con índice de referencia",
                "fracción",
            ),
        }
        result.update(rol="bandera_calidad", agregacion=desc[flag][0], unidad=desc[flag][1])
        if flag in ("filas_ventana", "con_indice", "nube100", "nube_desconocida", "nube_media_pct"):
            result["filtro"] = "toda la ventana; sin filtrar por nubosidad"
        return result
    indice, stat = parts[2], "_".join(parts[3:])
    desc = {
        "media": "media por captura de *_promedio; no pondera meses ni días",
        "mediana": "mediana de *_promedio",
        "pico_prom": "máximo de *_promedio (pico del promedio de parcela)",
        "doy_pico_prom": "día del año del pico del promedio; empate: primera fecha",
        "integral": f"trapecios con días reales, hueco ≤{config['integral_hueco_max_dias']} d, sin extrapolar",
        "dias_integ": "días cubiertos por los tramos admitidos de la integral",
        "pixmax": "máximo de *_max (píxel extremo)",
        "doy_pixmax": "día del año del píxel extremo máximo; empate: primera fecha",
        "pixmin": "mínimo de *_min (píxel extremo)",
        "std_media": "media de *_std; heterogeneidad dentro de capturas, no desviación temporal",
        "n": "capturas admitidas con *_promedio presente",
    }
    unit = {
        "doy_pico_prom": "día del año",
        "doy_pixmax": "día del año",
        "integral": "índice·día",
        "dias_integ": "días",
        "n": "observaciones",
    }
    result.update(
        indice=indice,
        agregacion=desc[stat],
        unidad=unit.get(stat, "unidad del índice entregado"),
        rol="pendiente_admisibilidad" if ventana_id == "P" else "candidata",
    )
    if indice == "lai":
        result["filtro"] += f"; LAI negativos: {config['lai_negativos']}"
    return result


def diagnosticos_media_vs_tiempo(d, sensor, indice, ids, inicio, fin, nube_max=None, max_gap=30):
    """Medias didácticas separadas de la base; devuelve diagnóstico y meses largos.

    Requiere meses completos. Un mes ausente mantiene NaN en ambas medias de
    meses; no se rellena ni se elimina una parcela. La integral dividida por
    sus días describe solo tramos admitidos, no todos los días de la ventana.
    """
    inicio, fin = pd.Timestamp(inicio), pd.Timestamp(fin)
    meses = pd.date_range(inicio, fin, freq="MS")
    if inicio.day != 1 or not len(meses) or fin != meses[-1] + pd.offsets.MonthEnd(0):
        raise ValueError("El diagnóstico mensual requiere una ventana de meses completos.")
    copia = d.copy(deep=True)
    if "fecha" not in copia:
        copia["fecha"] = copia.FECHA
    if "S" not in copia:
        copia["S"] = copia.sensor.map({"Sentinel-2": "S2", "Landsat": "LS", "Planet": "PL"})
    col = f"{indice}_promedio"
    usados = eligible(copia[copia.S.eq(sensor)], inicio, fin, nube_max).dropna(subset=[col]).copy()
    usados["mes"] = usados.fecha.dt.to_period("M")
    grid = pd.MultiIndex.from_product(
        [list(ids), meses.to_period("M")], names=["ID_POLIGONO", "mes"]
    )
    mensual = usados.groupby(["ID_POLIGONO", "mes"])[col].agg(media="mean", n="count").reindex(grid)
    mensual["n"] = mensual.n.fillna(0).astype(int)
    mensual = mensual.reset_index()
    mensual["dias_mes"] = mensual.mes.dt.days_in_month
    monthly = mensual.pivot(index="ID_POLIGONO", columns="mes", values="media").reindex(index=ids)
    weights = meses.days_in_month.to_numpy()
    complete = monthly.notna().all(axis=1)
    out = pd.DataFrame(index=pd.Index(ids, name="ID_POLIGONO"))
    out["media_captura"] = usados.groupby("ID_POLIGONO")[col].mean()
    out["media_mensual_simple"] = monthly.mean(axis=1).where(complete)
    out["media_mensual_por_dias"] = (
        monthly.mul(weights, axis=1).sum(axis=1, min_count=len(meses)) / weights.sum()
    )
    out["meses_con_dato"] = monthly.notna().sum(axis=1)
    out["meses_esperados"] = len(meses)
    out["n_capturas"] = usados.groupby("ID_POLIGONO").size().reindex(out.index, fill_value=0)
    integrales = {
        k: partial_integral(q.fecha, q[col], max_gap) for k, q in usados.groupby("ID_POLIGONO")
    }
    out["integral"] = pd.Series({k: a for k, (a, _) in integrales.items()}, dtype=float)
    out["dias_integrados"] = pd.Series(
        {k: dias for k, (_, dias) in integrales.items()}, dtype=float
    ).reindex(out.index, fill_value=0.0)
    out["media_sobre_tramos_integrados"] = out.integral / out.dias_integrados.where(
        out.dias_integrados.gt(0)
    )
    mensual["mes"] = mensual.mes.astype(str)
    mensual["sensor"] = sensor
    mensual["indice"] = indice
    return out, mensual
