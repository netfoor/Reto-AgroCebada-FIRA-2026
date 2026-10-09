"""EXP_07: soporte pareado y factibilidad de X, sin leer valores de rendimiento.

La fuente entrega desviación espacial por captura; aquí se promedian esas
desviaciones. No se estima una desviación temporal ni se reconstruyen píxeles.
Las medianas y escalas diagnósticas se calculan separadamente para cada conjunto
de entrenamiento, solo para comprobar que la receta futura es realizable.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from validacion_03 import validar_externas, validar_internas


L = "H7_PL_ndvi_media_pareada"
S = "H7_PL_ndvi_std_media_pareada"
COLUMNAS_CAPTURA = [
    "ID_POLIGONO", "fecha_captura", "sensor", "ndvi_promedio", "ndvi_std",
    "porcentaje_nubosidad",
]
COLUMNAS_METADATA = ["ID_POLIGONO", "Municipio", "Estado", "AREA_HA", "CONJUNTO"]
VENTANA = ("2025-04-01", "2025-10-31")
SHA_DATASET = "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"
SHA_PLANET = "91697f8f8d4ad5e59f766acbce2ef76f3c405eb02b41c1de92d62a07e8321888"
SHA_VARIABLES = "62e39ba23fb33f8834e92943f9714fea38aa731da079e0431d707aab13151595"
SHA_EXTERNA = "02d07dfcdb8064a4daf08b5bebc575f807ccab09ca33f27ec7dfa1a069c300ec"
SHA_INTERNA = "a35412fda33fcea7b379f6d95418eaaa7ebafc5b5330873613b83184cb16ab6a"
MIEMBRO_PLANET = "DATASET_RETO_AGRO_2026/Conjunto_datos_PRO_AgroCebada.csv"
UMBRAL_ESCALA = 1e-12


def _sin_rendimiento(df):
    if any("RENDIMIENTO" in str(c).upper() for c in df.columns):
        raise ValueError("La factibilidad de X no admite columnas de rendimiento")
    if not df.columns.is_unique:
        raise ValueError("Columnas duplicadas")


def validar_entradas(capturas, metadata):
    """Valida, ordena y copia; no modifica las tablas recibidas ni repara datos."""
    for df in (capturas, metadata):
        _sin_rendimiento(df)
    if set(capturas) != set(COLUMNAS_CAPTURA) or not set(COLUMNAS_METADATA) <= set(metadata):
        raise ValueError("Esquema de capturas/metadatos incompatible")
    meta = metadata[COLUMNAS_METADATA].copy()
    if meta.empty or meta.ID_POLIGONO.isna().any() or not meta.ID_POLIGONO.is_unique:
        raise ValueError("IDs de metadatos vacíos o repetidos")
    if not meta.ID_POLIGONO.astype(str).str.fullmatch(r"AGC_\d{3}").all():
        raise ValueError("ID de metadatos mal formado")
    if meta[["Municipio", "Estado", "CONJUNTO"]].isna().any().any():
        raise ValueError("Metadatos territoriales/rol ausentes")
    if meta.Municipio.astype(str).str.strip().eq("").any():
        raise ValueError("Municipio vacío")
    if not set(meta.CONJUNTO) <= {"ENTRENAMIENTO", "PREDICCION"}:
        raise ValueError("Rol oficial desconocido")
    meta["AREA_HA"] = pd.to_numeric(meta.AREA_HA, errors="raise")
    if not np.isfinite(meta.AREA_HA).all() or not meta.AREA_HA.gt(0).all():
        raise ValueError("Área no positiva o no finita")
    cap = capturas[COLUMNAS_CAPTURA].copy()
    if cap.empty or cap[["ID_POLIGONO", "fecha_captura", "sensor"]].isna().any().any():
        raise ValueError("Capturas vacías o claves ausentes")
    if set(cap.sensor) != {"Planet"} or not set(cap.ID_POLIGONO) <= set(meta.ID_POLIGONO):
        raise ValueError("Sensor/ID no previsto")
    if not cap.fecha_captura.astype(str).str.fullmatch(r"\d{2}/\d{2}/\d{4}").all():
        raise ValueError("Se requiere fecha dd/mm/aaaa")
    cap["fecha"] = pd.to_datetime(cap.fecha_captura, format="%d/%m/%Y", errors="raise")
    if not cap.fecha.between(*VENTANA).all():
        raise ValueError("Captura fuera de abril–octubre de 2025")
    if cap.duplicated(["ID_POLIGONO", "fecha", "sensor"]).any():
        raise ValueError("Captura parcela–fecha–sensor duplicada")
    for campo in ["ndvi_promedio", "ndvi_std", "porcentaje_nubosidad"]:
        cap[campo] = pd.to_numeric(cap[campo], errors="raise")
        if np.isinf(cap[campo].to_numpy(float)).any():
            raise ValueError(f"Infinito en {campo}")
    if cap.ndvi_std.dropna().lt(0).any():
        raise ValueError("ndvi_std negativo: detener, no recortar ni tomar absoluto")
    if not cap.ndvi_promedio.dropna().between(-1, 1).all():
        raise ValueError("NDVI promedio fuera de [-1,1]: requiere investigación")
    if not cap.porcentaje_nubosidad.dropna().between(0, 100).all():
        raise ValueError("Nubosidad fuera de [0,100]")
    cap["promedio_finito"] = np.isfinite(cap.ndvi_promedio)
    cap["std_finita"] = np.isfinite(cap.ndvi_std)
    cap["pareada"] = cap.promedio_finito & cap.std_finita
    cap["mes"] = cap.fecha.dt.month
    return cap.sort_values(["ID_POLIGONO", "fecha"], kind="stable"), meta.sort_values("ID_POLIGONO")


def _correlacion(a, b):
    q = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(q) < 3 or q.a.nunique() < 2 or q.b.nunique() < 2:
        return np.nan, len(q)
    return float(q.a.corr(q.b)), len(q)


def diagnosticar_entrenamientos(variables, externas, internas):
    """Disponibilidad y escala de cada columna, solo X de cada entrenamiento."""
    ids = variables.loc[variables.CONJUNTO.eq("ENTRENAMIENTO"), "ID_POLIGONO"]
    nr, nf = externas.repeticion.nunique(), externas.pliegue.nunique()
    ni = internas.pliegue_interno.nunique()
    validar_externas(externas, ids, nr, nf)
    validar_internas(internas, externas, ids, nr, nf, ni)
    x = variables.set_index("ID_POLIGONO")
    filas = []
    niveles = [
        ("exterior", externas, ["repeticion", "pliegue"]),
        ("interior", internas, ["repeticion", "pliegue", "pliegue_interno"]),
    ]
    for nivel, roles, claves in niveles:
        for clave, g in roles.groupby(claves, sort=True):
            clave = clave if isinstance(clave, tuple) else (clave,)
            tr = x.loc[g.loc[g.rol.eq("entrenamiento"), "ID_POLIGONO"]]
            for campo in [L, S]:
                v = tr[campo].to_numpy(float)
                n = int(np.isfinite(v).sum())
                mediana = float(np.nanmedian(v)) if n else np.nan
                imputada = np.where(np.isnan(v), mediana, v)
                if n:
                    serie = pd.Series(imputada, index=tr.index)
                    residuo = serie - serie.groupby(tr.Municipio).transform("mean")
                    escala = float(np.sqrt(np.mean(residuo.to_numpy() ** 2)))
                    umbral = UMBRAL_ESCALA * max(1.0, float(np.max(np.abs(imputada))))
                else:
                    escala, umbral = np.nan, np.nan
                filas.append({
                    "nivel": nivel, **dict(zip(claves, clave, strict=True)),
                    "variable": campo, "n_entrenamiento": len(tr), "n_finitos": n,
                    "mediana_diagnostica": mediana, "escala_intramunicipal": escala,
                    "umbral_escala": umbral, "columna_vacia": n == 0,
                    "escala_degenerada": bool(n == 0 or escala <= umbral),
                })
    return pd.DataFrame(filas)


def construir(capturas, metadata, externas, internas):
    """Devuelve variables, resumen sin y y tablas diagnósticas; cero modelos."""
    for df in (externas, internas):
        _sin_rendimiento(df)
    cap, meta = validar_entradas(capturas, metadata)
    par = cap.loc[cap.pareada]
    medias = par.groupby("ID_POLIGONO")[["ndvi_promedio", "ndvi_std"]].mean().rename(
        columns={"ndvi_promedio": L, "ndvi_std": S}
    )
    variables = meta.merge(medias, on="ID_POLIGONO", how="left", validate="one_to_one")
    qrows = []
    for _, m in meta.iterrows():
        g = cap.loc[cap.ID_POLIGONO.eq(m.ID_POLIGONO)]
        p = g.loc[g.pareada]
        qrows.append({
            "ID_POLIGONO": m.ID_POLIGONO, "Municipio": m.Municipio, "CONJUNTO": m.CONJUNTO,
            "AREA_HA": m.AREA_HA, "n_capturas": len(g),
            "n_promedio_finito": int(g.promedio_finito.sum()),
            "n_std_finita": int(g.std_finita.sum()), "n_pareadas": len(p),
            "n_promedio_sin_std": int((g.promedio_finito & ~g.std_finita).sum()),
            "n_std_sin_promedio": int((g.std_finita & ~g.promedio_finito).sum()),
            "meses_con_par": p.mes.nunique(), "nube_media_toda_ventana": g.porcentaje_nubosidad.mean(),
            "nube_media_pareada": p.porcentaje_nubosidad.mean(),
            "nube_100": int(g.porcentaje_nubosidad.eq(100).sum()),
            "nube_desconocida": int(g.porcentaje_nubosidad.isna().sum()),
            "fraccion_nube_parcial_pareada": float(p.porcentaje_nubosidad.between(0, 100, inclusive="neither").mean()) if len(p) else np.nan,
            "L_historica_recalculada": g.loc[g.promedio_finito, "ndvi_promedio"].mean(),
            "S_historica_recalculada": g.loc[g.promedio_finito, "ndvi_std"].mean(),
        })
    calidad = pd.DataFrame(qrows).merge(variables[["ID_POLIGONO", L, S]], validate="one_to_one")
    mensual = pd.DataFrame(
        [(pid, mes) for pid in meta.ID_POLIGONO for mes in range(4, 11)],
        columns=["ID_POLIGONO", "mes"],
    ).merge(
        par.groupby(["ID_POLIGONO", "mes"]).agg(
            n_pareadas=("ndvi_std", "size"), L_media=("ndvi_promedio", "mean"),
            S_media=("ndvi_std", "mean"), nube_media=("porcentaje_nubosidad", "mean"),
        ).reset_index(), how="left", validate="one_to_one",
    )
    mensual["n_pareadas"] = mensual.n_pareadas.fillna(0).astype(int)
    tren = diagnosticar_entrenamientos(variables, externas, internas)
    correlaciones = []
    factores = [L, "AREA_HA", "n_pareadas", "nube_media_pareada", "fraccion_nube_parcial_pareada"]
    poblaciones = {"TODAS_X": calidad, "ENTRENAMIENTO_X": calidad.loc[calidad.CONJUNTO.eq("ENTRENAMIENTO")],
                   "PREDICCION_X": calidad.loc[calidad.CONJUNTO.eq("PREDICCION")]}
    for poblacion, d in poblaciones.items():
        for factor in factores:
            for tipo in ["global", "intramunicipal"]:
                a, b = d[S], d[factor]
                if tipo == "intramunicipal":
                    a = a - a.groupby(d.Municipio).transform("mean")
                    b = b - b.groupby(d.Municipio).transform("mean")
                r, n = _correlacion(a, b)
                correlaciones.append({"poblacion": poblacion, "tipo": tipo, "variable_1": S,
                                      "variable_2": factor, "pearson": r, "n_pares": n})
    soporte = []
    visible = variables.loc[variables.CONJUNTO.eq("ENTRENAMIENTO")]
    for _, h in variables.loc[variables.CONJUNTO.eq("PREDICCION")].iterrows():
        tr = visible.loc[visible.Municipio.eq(h.Municipio)]
        row = {"ID_POLIGONO": h.ID_POLIGONO, "Municipio": h.Municipio,
               "n_parcelas_etiquetadas_municipio": len(tr), "caso_singleton": len(tr) == 1}
        for campo, corto in [(L, "L"), (S, "S")]:
            vals, valor = tr[campo].dropna(), h[campo]
            row.update({f"{corto}_valor": valor, f"{corto}_ausente": pd.isna(valor),
                        f"{corto}_etiquetadas_disponibles": len(vals),
                        f"{corto}_fuera_rango_municipal": bool(valor < vals.min() or valor > vals.max()) if len(vals) and pd.notna(valor) else None})
        soporte.append(row)
    gates = {
        "sin_columnas_vacias_en_train": not bool(tren.columna_vacia.any()),
        "S_con_variacion_intramunicipal_en_todos_train": not bool(tren.loc[tren.variable.eq(S), "escala_degenerada"].any()),
        "capturas_para_todos_ids": set(cap.ID_POLIGONO) == set(meta.ID_POLIGONO),
    }
    resumen = {
        "id": "EXP_07", "fase": "factibilidad_solo_X", "usa_rendimientos": False,
        "ajustes_modelos": 0, "parcelas": len(meta), "capturas": len(cap), "capturas_pareadas": len(par),
        "mascaras_promedio_std_identicas": bool(cap.promedio_finito.eq(cap.std_finita).all()),
        "parcelas_sin_descriptores": int(variables[S].isna().sum()),
        "meses_esperados": 7, "parcelas_siete_meses_pareados": int(calidad.meses_con_par.eq(7).sum()),
        "entrenamientos_exteriores": int(tren.loc[tren.nivel.eq("exterior")].drop_duplicates(["repeticion", "pliegue"]).shape[0]),
        "entrenamientos_interiores": int(tren.loc[tren.nivel.eq("interior")].drop_duplicates(["repeticion", "pliegue", "pliegue_interno"]).shape[0]),
        "std_negativas": 0, "infinidades": 0, "puertas": gates, "apta": all(gates.values()),
        "umbral_escala": UMBRAL_ESCALA, "ventana": list(VENTANA),
        "regla_soporte": "promedio y std finitos en la misma captura, sin filtro adicional de nube",
        "limitaciones": ["Sin máscara ni conteo de píxeles por captura", "Std del proveedor sin ddof documentado",
                         "Rango univariado no demuestra soporte multivariado", "Correlaciones entre X no son selección mediante rendimiento"],
    }
    tablas = {"calidad_parcela": calidad, "cobertura_mensual": mensual,
              "variacion_entrenamientos": tren, "correlaciones_X": pd.DataFrame(correlaciones),
              "soporte_59_solo_X": pd.DataFrame(soporte)}
    return variables, resumen, tablas


def _bytes_verificados(ruta, sha):
    bruto = Path(ruta).read_bytes()
    if hashlib.sha256(bruto).hexdigest() != sha:
        raise ValueError(f"Hash distinto: {Path(ruta).name}")
    return bruto


def preparar(raiz):
    """Deriva insumos nuevos, solo X, de originales verificados sin alterarlos."""
    raiz = Path(raiz)
    destino = raiz / "data/exp_07_heterogeneidad_parcela"
    if destino.exists():
        raise ValueError("La carpeta de preparación ya existe; no sobrescribir")
    bruto_zip = _bytes_verificados(raiz / "data/raw/DataSet.zip", SHA_DATASET)
    with zipfile.ZipFile(io.BytesIO(bruto_zip)) as z:
        if z.namelist().count(MIEMBRO_PLANET) != 1:
            raise ValueError("Fuente Planet no única en ZIP")
        original = z.read(MIEMBRO_PLANET)
    if hashlib.sha256(original).hexdigest() != SHA_PLANET:
        raise ValueError("Planet original distinto")
    todo = pd.read_csv(io.BytesIO(original), encoding="utf-8-sig", float_precision="round_trip",
                       usecols=COLUMNAS_CAPTURA)
    fechas = pd.to_datetime(todo.fecha_captura, format="%d/%m/%Y", errors="raise")
    capturas = todo.loc[fechas.between(*VENTANA), COLUMNAS_CAPTURA].copy()
    v0 = pd.read_csv(io.BytesIO(_bytes_verificados(raiz / "data/referencias/variables_v0_197.csv", SHA_VARIABLES)),
                     float_precision="round_trip")
    metadata = v0[COLUMNAS_METADATA].copy()
    externas_bytes = _bytes_verificados(raiz / "data/validacion_03/particiones_externas.csv", SHA_EXTERNA)
    internas_bytes = _bytes_verificados(raiz / "data/validacion_03/particiones_internas.csv", SHA_INTERNA)
    externas, internas = pd.read_csv(io.BytesIO(externas_bytes)), pd.read_csv(io.BytesIO(internas_bytes))
    variables, resumen, tablas = construir(capturas, metadata, externas, internas)
    if len(variables) != 197 or not variables.CONJUNTO.eq("ENTRENAMIENTO").sum() == 138:
        raise ValueError("Catálogo real distinto de 197/138")
    control = tablas["calidad_parcela"].merge(
        v0[["ID_POLIGONO", "C_PL_ndvi_media", "C_PL_ndvi_std_media"]], validate="one_to_one"
    )
    for nueva, antigua in [("L_historica_recalculada", "C_PL_ndvi_media"),
                           ("S_historica_recalculada", "C_PL_ndvi_std_media")]:
        np.testing.assert_allclose(control[nueva], control[antigua], rtol=0, atol=1e-12, equal_nan=True)
    tablas["comparacion_v0"] = control[["ID_POLIGONO", L, S, "L_historica_recalculada",
                                       "S_historica_recalculada", "C_PL_ndvi_media", "C_PL_ndvi_std_media"]]
    resumen["control_v0_197_conciliado"] = True
    resumen["diferencia_max_L_pareada_v0"] = float((control[L] - control.C_PL_ndvi_media).abs().max())
    resumen["diferencia_max_S_pareada_v0"] = float((control[S] - control.C_PL_ndvi_std_media).abs().max())
    destino.mkdir(parents=True)
    capturas_ordenadas = capturas.assign(fecha=pd.to_datetime(
        capturas.fecha_captura, format="%d/%m/%Y", errors="raise"
    )).sort_values(["ID_POLIGONO", "fecha"], kind="stable")[COLUMNAS_CAPTURA]
    para_csv = {"capturas_planet": capturas_ordenadas,
                "metadatos": metadata.sort_values("ID_POLIGONO"), "variables_197": variables, **tablas}
    for nombre, tabla in para_csv.items():
        tabla.to_csv(destino / f"{nombre}.csv", index=False, float_format="%.17g")
    (destino / "externas.csv").write_bytes(externas_bytes)
    (destino / "internas.csv").write_bytes(internas_bytes)
    (destino / "diagnosticos_X.json").write_text(json.dumps(resumen, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    registro = {
        "id": "EXP_07", "fase": "preparacion_solo_X", "preparado_utc": datetime.now(timezone.utc).isoformat(),
        "usa_rendimientos": False, "filas_fuente_planet": len(todo), "filas_recorte": len(capturas),
        "originales": {"DataSet.zip": SHA_DATASET, MIEMBRO_PLANET: SHA_PLANET,
                       "variables_v0_197.csv": SHA_VARIABLES, "externas": SHA_EXTERNA, "internas": SHA_INTERNA},
        "insumos": {p.name: {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                    for p in sorted(destino.iterdir())},
    }
    (destino / "procedencia_X.json").write_text(json.dumps(registro, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return variables, resumen, tablas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    _, resumen, _ = preparar(args.raiz)
    print(json.dumps(resumen, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    if not resumen["apta"]:
        raise SystemExit("Factibilidad no apta: detener antes de cualquier ajuste")


if __name__ == "__main__":
    main()
