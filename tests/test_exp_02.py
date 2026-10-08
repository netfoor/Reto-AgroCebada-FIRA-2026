"""EXP_02: contratos y aritmética visible, sin kernel ni ajustes históricos.

Controles: T1/29-sep (mensuales, atributos, OOF, alphas y métricas), más
particiones y resultados de ronda 1. Se prueban funciones extraídas por AST;
puntuar las OOF y reseleccionar scores guardados no reproduce entrenamientos.
"""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import re
import sys
import zlib
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/exp_02_ponderacion_temporal.json"
BASE = "notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb"
BASE_SHA = "c74f4703d46a83022d675c42e5834ffea721112be531edab5deae6592b7e318c"
ALPHAS = (.01, .1, 1., 10., 100.)
DIAS = pd.Series([30, 31, 30, 31, 31, 30, 31], index=range(4, 11))
CLAVES = ["repeticion", "pliegue", "ID_POLIGONO"]
CAMBIOS = ("C_PL_ndvi_media", "C_S2_ndvi_media", "C_S2_ndwi_media")
FIJAS = ("C_PL_ndvi_pico_prom", "C_PL_ndvi_doy_pico_prom", "C_LS_vi6t_media")
MODELOS = ("GLOBAL", "MUN", "MIX", "E0", "E2", "T1")
VISIBLES = ("insumos-visibles", "una-media-visible", "pesos-visibles", "agregacion-visible",
            "variables-control", "particiones-visibles", "seleccion-visible", "control-e2-visible",
            "oof-validacion", "metricas-visibles", "pareadas-visibles", "sensibilidad-visible", "cierre")


def _sha(contenido):
    return hashlib.sha256(contenido).hexdigest()


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("exp02_generador_pruebas", ROOT / "scripts/construir_exp_02.py")
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def config():
    return json.loads((ROOT / CONFIG).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def insumos(builder):
    return builder.cargar_insumos(ROOT)


@pytest.fixture(scope="module")
def notebook(builder, config):
    protegidos = [ROOT / BASE, ROOT / CONFIG, ROOT / "scripts/colab_soporte.py",
                  ROOT / "requirements-colab-auditoria.txt"]
    protegidos += [ROOT / c["ruta_local"] for c in config["insumos"].values()]
    antes = {p: _sha(p.read_bytes()) for p in protegidos}
    nb = builder.construir(ROOT)
    assert all(_sha(p.read_bytes()) == h for p, h in antes.items())
    return nb


def _celda(nb, tag):
    celdas = [c for c in nb.cells if tag in c.metadata.get("tags", [])]
    assert len(celdas) == 1, f"Celda única requerida: {tag}"
    return celdas[0]


def _funciones(nb, nombres, **extra):
    defs = {}
    for c in nb.cells:
        if c.cell_type == "code":
            for n in ast.parse(c.source).body:
                if isinstance(n, ast.FunctionDef) and n.name in nombres:
                    assert n.name not in defs
                    if n.name not in ("bytes_insumo", "leer_csv"):
                        assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
                    defs[n.name] = copy.deepcopy(n)
    assert set(defs) == set(nombres)
    arbol = ast.fix_missing_locations(ast.Module(body=list(defs.values()), type_ignores=[]))
    ns = {"np": np, "pd": pd, "DIAS": DIAS.copy(), "ALPHAS": ALPHAS,
          "base64": base64, "zlib": zlib, "hashlib": hashlib, "io": io, **extra}
    exec(compile(arbol, "<EXP_02:funciones-visibles>", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def ciencias(notebook):
    return _funciones(notebook, ["agregar_meses", "seleccionar_alpha", "metricas"])


@pytest.fixture(scope="module")
def tablas(insumos):
    return {k: pd.read_csv(io.BytesIO(r["contenido"]), encoding="utf-8-sig")
            for k, r in insumos.items() if r["ruta_local"].endswith(".csv")}


def _registros(notebook):
    for n in ast.parse(_celda(notebook, "insumos-tecnicos").source).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSUMOS_INCRUSTADOS"
                                             for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError("Faltan insumos incrustados")


def _toy():
    return pd.DataFrame([{"ID_POLIGONO": pid, "sensor": "Planet",
                          "fecha_captura": f"{dia:02d}/{mes:02d}/2025",
                          "ndvi_promedio": mes/10 + offset}
                         for pid, offset in [("A", 0.), ("B", .2)]
                         for mes in range(4, 11) for dia in (1, 2)])


def test_api_construccion_determinista_y_metadatos(builder, notebook, config):
    assert all(callable(getattr(builder, k)) for k in ("construir", "cargar_insumos", "huella"))
    assert builder.huella(b"T1") == _sha(b"T1")
    nbformat.validate(notebook)
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == []
            assert "execution" not in c.metadata
    reg = notebook.metadata.agrocebada
    assert reg.id == "EXP_02" and reg.modo == "lector_retrospectivo_sin_ajustes"
    assert reg.fecha_original == "2026-09-29" and reg.fecha_adaptacion == "2026-10-08"
    assert reg.ajustes_actuales == 0 and reg.colab_real_probado is False
    assert set(reg.dependencias_requeridas) == {"numpy", "pandas", "matplotlib"}
    assert reg.recortes_derivados == config["recortes_derivados"]
    nuevo = builder.construir()
    assert [(c.id, c.cell_type, c.source) for c in nuevo.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells]


def test_exp01_intacto_y_celdas_completas_copiadas_solo_al_construir(builder, notebook):
    assert builder.BASE_SHA256 == BASE_SHA == _sha((ROOT / BASE).read_bytes())
    base = nbformat.read(ROOT / BASE, as_version=4)
    for tag in ("soporte-colab", "preparar-colab", "entorno", "particiones-visibles"):
        assert _celda(notebook, tag).source == _celda(base, tag).source
    reg = notebook.metadata.agrocebada
    assert reg.fuentes_sha256[BASE] == BASE_SHA
    assert reg.soporte_sha256 == base.metadata.agrocebada.soporte_sha256
    assert reg.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())


def test_dos_tecnicas_plegadas_y_ciencia_visible(notebook):
    ocultas = [c for c in notebook.cells if c.cell_type == "code"
               and c.metadata.get("jupyter", {}).get("source_hidden", False)]
    assert len(ocultas) == 2
    for tag in ("soporte-colab", "insumos-tecnicos"):
        c = _celda(notebook, tag)
        assert c in ocultas and c.metadata.get("cellView") == "form"
        titulo, salto, cuerpo = c.source.partition("\n")
        assert titulo.startswith("# @title ") and titulo.endswith('{ display-mode: "form" }')
        assert salto and len(titulo) < 180
        assert ast.dump(ast.parse(c.source)) == ast.dump(ast.parse(cuerpo))
    for tag in ("preparar-colab", "entorno") + VISIBLES:
        c = _celda(notebook, tag)
        assert c.cell_type == "code" and c.metadata.get("cellView") != "form"
        assert not c.metadata.get("jupyter", {}).get("source_hidden", False)


def test_cero_modelos_descargas_datos_y_dependencias_locales(notebook):
    modelos = {"fit", "fit_transform", "fit_predict", "partial_fit", "predict", "predict_proba",
               "GridSearchCV", "RandomizedSearchCV"}
    descargas = {"obtener_dataset", "download", "urlopen", "urlretrieve"}
    for c in notebook.cells:
        if c.cell_type != "code":
            continue
        soporte = "soporte-colab" in c.metadata.get("tags", [])
        arbol = ast.parse(c.source)
        for n in ast.walk(arbol):
            if isinstance(n, ast.Call):
                nombre = n.func.attr if isinstance(n.func, ast.Attribute) else (
                    n.func.id if isinstance(n.func, ast.Name) else None)
                assert nombre not in modelos, f"Llamada prohibida: {nombre}"
                if not soporte:
                    assert nombre not in descargas
                    assert nombre not in {"open", "read_bytes", "read_text", "read_json", "read_pickle"}
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                modulos = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                prohibidos = {"sklearn", "scripts"} | (set() if soporte else {"gdown", "requests", "google"})
                assert not any(m.split(".")[0] in prohibidos
                               or "construir_exp" in m for m in modulos)
        if soporte:
            # El soporte conserva un helper de datos inactivo. Prohibir su import
            # interno no prueba descargas: comprobamos que no se activa al ejecutar.
            activo = ast.Module(body=[n for n in arbol.body if not isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], type_ignores=[])
            for n in ast.walk(activo):
                if isinstance(n, ast.Call):
                    nombre = n.func.attr if isinstance(n.func, ast.Attribute) else (
                        n.func.id if isinstance(n.func, ast.Name) else None)
                    assert nombre not in descargas
    loader = _funciones(notebook, ["bytes_insumo", "leer_csv"])
    assert callable(loader["leer_csv"])
    assert "io.BytesIO(bytes_insumo" in _celda(notebook, "insumos-tecnicos").source


def test_20_contratos_compresion_sha_uso_y_recortes_no_preregistrados(notebook, config, insumos):
    registros = _registros(notebook)
    assert len(registros) == len(config["insumos"]) == 20
    assert set(registros) == set(insumos) == set(config["insumos"])
    ns = _funciones(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS=registros)
    for k, contrato in config["insumos"].items():
        bruto = insumos[k]["contenido"]
        assert bruto == (ROOT / contrato["ruta_local"]).read_bytes()
        assert type(contrato["bytes"]) is int and 0 < contrato["bytes"] <= 2*1024*1024
        assert len(bruto) == contrato["bytes"] and _sha(bruto) == contrato["sha256"]
        assert ns["bytes_insumo"](k, contrato["uso"]) == bruto
        assert notebook.metadata.agrocebada.insumos[k]["sha256"] == contrato["sha256"]
    for nombre, key in [("planet", "capturas_planet"), ("s2", "capturas_s2")]:
        r = config["recortes_derivados"][nombre]
        assert r["fecha_recorte"] == "2026-10-08" and r["filtro_nubes"] is False
        assert r["sha256_recorte"] == config["insumos"][key]["sha256"] != r["sha256_original"]
        assert r["ventana"] == ["2025-04-01", "2025-10-31"]


@pytest.mark.parametrize("alteracion", ["contenido", "bytes", "sha", "ausente"])
def test_loader_rechaza_manipulacion_en_fixture_propio(builder, tmp_path, alteracion):
    bruto = b"columna\n1\n"
    contrato = {"ruta_local": "dato.csv", "bytes": len(bruto), "sha256": _sha(bruto), "uso": "prueba"}
    (tmp_path / "config").mkdir()
    if alteracion == "bytes":
        contrato["bytes"] += 1
    if alteracion == "sha":
        contrato["sha256"] = "0"*64
    (tmp_path / CONFIG).write_text(json.dumps({"insumos": {"dato": contrato}}), encoding="utf-8")
    if alteracion != "ausente":
        (tmp_path / "dato.csv").write_bytes(b"columna\n2\n" if alteracion == "contenido" else bruto)
    with pytest.raises((ValueError, FileNotFoundError)):
        builder.cargar_insumos(tmp_path)


@pytest.mark.parametrize("alteracion", ["uso", "sha", "bytes_menos", "bytes_mas", "bytes_cero",
    "bytes_negativo", "bytes_bool", "bytes_float", "bytes_limite", "base64", "base64_limite",
    "truncado", "concatenado", "sobrante"])
def test_decoder_acotado_rechaza_corrupcion_antes_de_parsear(notebook, alteracion):
    bruto = b"dato\n1\n"
    comprimido = zlib.compress(bruto)
    reg = {"uso": "prueba", "bytes": len(bruto), "sha256": _sha(bruto),
           "bytes_zlib_base64": base64.b64encode(comprimido).decode()}
    if alteracion == "uso":
        reg["uso"] = "otro"
    elif alteracion == "sha":
        reg["sha256"] = "0"*64
    elif alteracion.startswith("bytes_"):
        reg["bytes"] = {"bytes_menos": len(bruto)-1, "bytes_mas": len(bruto)+1, "bytes_cero": 0,
                        "bytes_negativo": -1, "bytes_bool": True, "bytes_float": float(len(bruto)),
                        "bytes_limite": 2*1024*1024+1}[alteracion]
    elif alteracion == "base64":
        reg["bytes_zlib_base64"] = "!no_base64!"
    elif alteracion == "base64_limite":
        reg["bytes_zlib_base64"] = "A"*(4*1024*1024+1)
    else:
        mal = {"truncado": comprimido[:-1], "concatenado": comprimido+zlib.compress(b"otra"),
               "sobrante": comprimido+b"extra"}[alteracion]
        reg["bytes_zlib_base64"] = base64.b64encode(mal).decode()
    ns = _funciones(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS={"dato": reg})
    with pytest.raises((ValueError, zlib.error)):
        ns["bytes_insumo"]("dato", "prueba")


def test_agregacion_conocida_pesos_y_orden_de_ids(ciencias):
    fn = ciencias["agregar_meses"]
    t, viejo, meses = fn(_toy(), "Planet", "ndvi_promedio", ["B", "A"])
    esperado = np.dot(np.arange(4, 11)/10, DIAS)/214
    np.testing.assert_allclose(t.to_numpy(), [esperado+.2, esperado], atol=1e-14, rtol=0)
    np.testing.assert_allclose(viejo.to_numpy(), [.9, .7], atol=1e-14, rtol=0)
    assert len(meses) == 14 and meses.n.eq(2).all()
    assert meses.dias_mes.tolist() == DIAS.tolist()*2
    movido = fn(_toy().sample(frac=1, random_state=4), "Planet", "ndvi_promedio", ["B", "A"])
    pd.testing.assert_series_equal(t, movido[0])


def test_nan_no_es_cero_muestreo_adicional_no_cambia_peso_del_mes_y_no_usa_y(ciencias):
    fn = ciencias["agregar_meses"]
    datos = _toy().query("ID_POLIGONO == 'A'").copy()
    datos["RENDIMIENTO_T_HA"] = np.arange(len(datos))
    base = fn(datos, "Planet", "ndvi_promedio", ["A"])
    extra = datos.iloc[[0]].copy()
    extra.fecha_captura = "03/04/2025"
    aumentado = fn(pd.concat([datos, extra]), "Planet", "ndvi_promedio", ["A"])
    np.testing.assert_allclose(base[0], aumentado[0], atol=1e-14, rtol=0)
    assert not np.isclose(base[1].iloc[0], aumentado[1].iloc[0])
    extra.ndvi_promedio = np.nan
    con_nan = fn(pd.concat([datos, extra]), "Planet", "ndvi_promedio", ["A"])
    pd.testing.assert_series_equal(base[0], con_nan[0])
    assert con_nan[2].n.eq(2).all()
    datos.RENDIMIENTO_T_HA = -999.
    pd.testing.assert_series_equal(base[0], fn(datos, "Planet", "ndvi_promedio", ["A"])[0])


@pytest.mark.parametrize("mal", ["sensor", "fecha_formato", "fecha_imposible", "fecha_fuera",
    "mes_ausente", "mes_nan", "duplicado", "inf", "menos_inf", "id_ausente", "id_null",
    "sensor_null", "fecha_null", "columna", "valor_texto", "ids_duplicados", "ids_vacios"])
def test_agregacion_detiene_fuente_incompatible_sin_imputar(ciencias, mal):
    datos = _toy()
    ids = ["A", "B"]
    if mal in {"sensor", "sensor_null"}:
        datos.loc[0, "sensor"] = "Sentinel-2" if mal == "sensor" else None
    elif mal.startswith("fecha_"):
        datos.loc[0, "fecha_captura"] = {"fecha_formato": "2025-04-01", "fecha_imposible": "31/04/2025",
                                        "fecha_fuera": "01/11/2025", "fecha_null": None}[mal]
    elif mal in {"mes_ausente", "mes_nan"}:
        abril_a = datos.ID_POLIGONO.eq("A") & datos.fecha_captura.str.contains("/04/")
        if mal == "mes_ausente":
            datos = datos.loc[~abril_a]
        else:
            datos.loc[abril_a, "ndvi_promedio"] = np.nan
    elif mal == "duplicado":
        datos = pd.concat([datos, datos.iloc[[0]]])
    elif mal in {"inf", "menos_inf", "valor_texto"}:
        datos["ndvi_promedio"] = datos.ndvi_promedio.astype(object)
        datos.loc[0, "ndvi_promedio"] = {"inf": np.inf, "menos_inf": -np.inf, "valor_texto": "ausente?"}[mal]
    elif mal == "id_ausente":
        ids.append("C")
    elif mal == "id_null":
        datos.loc[0, "ID_POLIGONO"] = None
    elif mal == "columna":
        datos = datos.drop(columns="ndvi_promedio")
    elif mal == "ids_duplicados":
        ids = ["A", "B", "A"]
    elif mal == "ids_vacios":
        ids = []
    with pytest.raises(ValueError):
        ciencias["agregar_meses"](datos, "Planet", "ndvi_promedio", ids)


def test_reales_197_recortes_nan_meses_y_tres_variables_control(ciencias, tablas, config):
    x = tablas["variables"].set_index("ID_POLIGONO")
    guardado = tablas["atributos"].set_index("ID_POLIGONO")
    assert x.shape == (197, 538) and x.index.is_unique and guardado.index.is_unique
    for nombre, fuente, sensor, campo in [(CAMBIOS[0], "capturas_planet", "Planet", "ndvi_promedio"),
        (CAMBIOS[1], "capturas_s2", "Sentinel-2", "ndvi_promedio"),
        (CAMBIOS[2], "capturas_s2", "Sentinel-2", "ndwi_promedio")]:
        recorte = config["recortes_derivados"]["planet" if fuente == "capturas_planet" else "s2"]
        d = tablas[fuente]
        assert len(d) == recorte["filas"] and d[campo].notna().sum() == recorte["no_ausentes"][campo]
        assert d[campo].isna().any() and "RENDIMIENTO_T_HA" not in d
        assert set(d.sensor) == {sensor} and set(d.ID_POLIGONO) == set(x.index)
        temporal, original, meses = ciencias["agregar_meses"](d, sensor, campo, x.index)
        np.testing.assert_allclose(original, x[nombre], atol=1e-12, rtol=0)
        np.testing.assert_allclose(temporal, guardado.loc[x.index, nombre], atol=1e-12, rtol=0)
        esperado = tablas["mensuales"].loc[tablas["mensuales"].variable.eq(nombre)]
        claves = ["ID_POLIGONO", "mes"]
        a, b = meses.set_index(claves).sort_index(), esperado.set_index(claves).sort_index()
        assert len(a) == 197*7 and a.index.equals(b.index) and not a.index.has_duplicates
        np.testing.assert_allclose(a.media, b.media, atol=1e-12, rtol=0)
        np.testing.assert_array_equal(a[["n", "dias_mes"]], b[["n", "dias_mes"]])
    np.testing.assert_allclose(guardado.loc[x.index, list(FIJAS)], x[list(FIJAS)], atol=1e-12, rtol=0)
    pd.testing.assert_frame_equal(guardado.loc[x.index, ["Municipio", "Estado"]], x[["Municipio", "Estado"]])
    assert len(tablas["mensuales"]) == 4137
    np.testing.assert_allclose(guardado.loc["AGC_001", list(CAMBIOS)].astype(float),
                              [.42670903877176214, .3141702825990209, .07854105473965287], atol=1e-12, rtol=0)


@pytest.mark.parametrize("scores,esperado", [([1., 1., 1., 1., 1.], 100.),
    ([1., 1.+5e-13, 1.+2e-12, 2., 3.], .1), ([3., 2., 1., 4., 5.], 1.),
    ([0., 1e-12, 2e-12, 3., 4.], .1)])
def test_selector_scores_guardados_minimo_tolerancia_y_orden(ciencias, scores, esperado):
    fila = pd.Series({f"rmse_interno_alpha_{a:g}": s for a, s in zip(ALPHAS, scores, strict=True)})
    fila["alpha"] = -999.
    assert ciencias["seleccionar_alpha"](fila.iloc[::-1]) == esperado


@pytest.mark.parametrize("valor", [np.nan, np.inf, -np.inf, -.1])
def test_selector_rechaza_scores_invalidos(ciencias, valor):
    fila = {f"rmse_interno_alpha_{a:g}": valor for a in ALPHAS}
    with pytest.raises(ValueError):
        ciencias["seleccionar_alpha"](fila)


def test_100_decisiones_alpha_y_control_e2_guardado(ciencias, tablas):
    for key, modelo in [("alpha_t1", "T1"), ("alpha_control_e2", "E2")]:
        d = tablas[key]
        assert d.shape == (50, 9) and set(d.modelo) == {modelo}
        assert not d.duplicated(CLAVES[:2]).any()
        np.testing.assert_array_equal(d.apply(ciencias["seleccionar_alpha"], axis=1), d.alpha)
    claves = ["modelo", "repeticion", "pliegue"]
    origen = tablas["alpha_ronda1"].query("modelo == 'E2'")
    j = tablas["alpha_control_e2"].merge(origen, on=claves, validate="one_to_one", suffixes=("", "_origen"))
    assert len(j) == 50 and j.alpha.eq(j.alpha_origen).all()
    for a in ALPHAS:
        c = f"rmse_interno_alpha_{a:g}"
        np.testing.assert_allclose(j[c], j[c+"_origen"], atol=1e-8, rtol=0)
    pareadas = tablas["alpha_t1"].merge(tablas["alpha_control_e2"], on=CLAVES[:2], validate="one_to_one")
    assert pareadas.alpha_x.ne(pareadas.alpha_y).sum() == 13
    control = tablas["oof_control_e2"].merge(tablas["oof_ronda1"].query("modelo == 'E2'"),
                                            on=["modelo"]+CLAVES, validate="one_to_one", suffixes=("", "_origen"))
    assert len(control) == 1380 and control.observado.eq(control.observado_origen).all()
    assert control.alpha.eq(control.alpha_origen).all()
    np.testing.assert_allclose(control.predicho, control.predicho_origen, atol=1e-8, rtol=0)


def test_metricas_negativo_umbral_historico_y_pooled_no_promedios(ciencias):
    fn = ciencias["metricas"]
    r = fn(pd.DataFrame({"observado": [1., 2., 3.], "predicho": [10., 10., 10.]}))
    np.testing.assert_allclose(r, [np.sqrt(194/3), 8., -96.], atol=1e-12, rtol=0)
    for y, indefinido in [([2., 2.], True), ([0., 1e-6], True), ([0., 2e-6], False)]:
        r = fn(pd.DataFrame({"observado": y, "predicho": np.zeros(len(y))}))
        assert bool(np.isnan(r.R2)) == indefinido
    d = pd.DataFrame({"ID_POLIGONO": ["A", "A", "B", "B"], "observado": [1., 1., 3., 3.],
                      "predicho": [0., 2., 2., 4.]})
    assert fn(d).RMSE == 1.
    assert fn(d.groupby("ID_POLIGONO")[["observado", "predicho"]].mean()).RMSE == 0.
    distinto = pd.DataFrame({"observado": [0.]*4, "predicho": [0., 2., 2., 2.]})
    assert np.isclose(fn(distinto).RMSE, np.sqrt(3.), atol=1e-12, rtol=0)
    assert np.mean([fn(distinto.iloc[:1]).RMSE, fn(distinto.iloc[1:]).RMSE]) == 1.


@pytest.mark.parametrize("y,p", [([], []), ([1., np.nan], [1., 2.]), ([1., 2.], [1., np.inf])])
def test_metricas_rechaza_vacios_no_finitos(ciencias, y, p):
    with pytest.raises(ValueError):
        ciencias["metricas"](pd.DataFrame({"observado": y, "predicho": p}))


def test_roles_guardados_containment_y_oof_full138_sin_59(ciencias, tablas):
    ext, inner = tablas["externas"], tablas["internas"]
    etiquetas = tablas["etiquetas"].set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    assert len(etiquetas) == 138 and etiquetas.index.is_unique and np.isfinite(etiquetas).all()
    assert ext.shape == (6900, 4) and inner.shape == (22080, 5)
    assert set(ext.rol) == set(inner.rol) == {"entrenamiento", "validacion"}
    assert not ext.duplicated(CLAVES).any()
    assert not inner.duplicated(CLAVES[:2]+["pliegue_interno", "ID_POLIGONO"]).any()
    validaciones = ext.loc[ext.rol.eq("validacion")]
    assert validaciones.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()
    for (r, f), grupo in ext.groupby(CLAVES[:2]):
        tr = set(grupo.loc[grupo.rol.eq("entrenamiento"), "ID_POLIGONO"])
        va = set(grupo.loc[grupo.rol.eq("validacion"), "ID_POLIGONO"])
        assert not tr & va and tr | va == set(etiquetas.index)
        dentro = inner.loc[inner.repeticion.eq(r) & inner.pliegue.eq(f)]
        assert set(dentro.ID_POLIGONO) == tr and not set(dentro.ID_POLIGONO) & va
        assert set(dentro.pliegue_interno) == {0, 1, 2, 3}
        assert dentro.loc[dentro.rol.eq("validacion")].ID_POLIGONO.is_unique
        for _, q in dentro.groupby("pliegue_interno"):
            assert q.ID_POLIGONO.is_unique and set(q.ID_POLIGONO) == tr
    alias = {"Media global": "GLOBAL", "Media municipal": "MUN", "Municipio + IDW fijo": "MIX"}
    ref = tablas["referencias"].loc[tablas["referencias"].modelo.isin(alias)].copy()
    ref["modelo"] = ref.modelo.map(alias)
    oof = pd.concat([tablas["oof_ronda1"].query("modelo in ['E0', 'E2']"), tablas["oof_t1"], ref])
    assert len(oof) == 8280 and set(oof.modelo) == set(MODELOS)
    assert not oof.duplicated(["modelo"]+CLAVES).any()
    esperado = set(map(tuple, validaciones[CLAVES].to_numpy()))
    control = tablas["metricas_control"].set_index("modelo")
    assert control.index.is_unique and set(control.index) == set(MODELOS) | {"E1", "E3", "E4"}
    for modelo, q in oof.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple, q[CLAVES].to_numpy())) == esperado
        np.testing.assert_array_equal(q.observado, q.ID_POLIGONO.map(etiquetas))
        assert np.isfinite(q[["observado", "predicho"]]).all().all()
        np.testing.assert_allclose(ciencias["metricas"](q), control.loc[modelo, ["RMSE", "MAE", "R2"]],
                                   atol=1e-12, rtol=0)
        sensibilidad = q.loc[~q.ID_POLIGONO.isin(["AGC_127", "AGC_171"])]
        assert len(sensibilidad) == 1360 and sensibilidad.ID_POLIGONO.nunique() == 136
        c = tablas["sensibilidad_control"].set_index("modelo")
        np.testing.assert_allclose(ciencias["metricas"](sensibilidad), c.loc[modelo, ["RMSE", "MAE", "R2"]],
                                   atol=1e-12, rtol=0)


def test_narrativa_limites_fechas_recortes_y_cierre_honesto(notebook, config, insumos):
    texto = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split()).lower()
    for concepto in ("captura", "mensual", "214", "sin filtro de nubes", "nan", "guardad",
                     "exploratori", "posterior", "intervalo de confianza", "no promover", "59"):
        assert concepto in texto
    assert re.search(r"recortes.{0,110}8 de octubre.{0,100}no.{0,100}29", texto)
    assert re.search(r"(?:no|sin).{0,120}(?:recalculamos|recalcul|reproduc).{0,130}(?:scores|ajustes)", texto)
    assert re.search(r"(?:errores|scores).{0,100}(?:intern|interior)", texto)
    man = json.loads(insumos["manifiesto"]["contenido"])
    assert man["meses"] == list(DIAS.index) and man["pesos_dias"] == list(DIAS)
    assert man["denominador_dias"] == 214 and tuple(man["cambios"]) == CAMBIOS
    assert sum(man["presupuesto"].values()) == 2100
    assert config["ajustes_historicos_t1"] == config["ajustes_historicos_control_e2"] == 1050
    campos = {}
    for n in ast.walk(ast.parse(_celda(notebook, "cierre").source)):
        if isinstance(n, ast.Dict):
            campos.update({k.value: v.value for k, v in zip(n.keys, n.values, strict=True)
                           if isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Constant)})
    assert campos["ajustes_actuales"] == campos["predicciones_finales_generadas"] == 0
    assert campos["scores_interiores_recalculados"] is campos["predicciones_recalculadas"] is False
    assert campos["T1_adoptado"] is False and campos["poblacion"] == "FULL138"
    assert campos["procedimientos"] == 6 and campos["decisiones_alpha_verificadas"] == 100
