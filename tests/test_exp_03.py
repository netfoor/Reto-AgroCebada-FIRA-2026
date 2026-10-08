"""EXP_03: receta visible, contratos y resultados guardados; cero entrenamientos.

Las pruebas extraen funciones científicas del cuaderno por AST. Reconstruir
descriptores y puntuar OOF no equivale a repetir los ajustes históricos de V1.
"""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import importlib.util
import io
import json
import sys
import zlib
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/exp_03_variables_y_familias.json"
BASE = "notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb"
BASE_SHA = "47c777915832c940bd0df2a8d8339ca77a05953c4921e94a8181141e65bdcc47"
DIAS = pd.Series([30, 31, 30, 31, 31, 30, 31], index=range(4, 11), name="dias_mes")
CLAVES = ["repeticion", "pliegue", "ID_POLIGONO"]
OLD = ["C_PL_ndvi_media", "C_PL_ndvi_pico_prom", "C_PL_ndvi_doy_pico_prom",
       "C_S2_ndvi_media", "C_S2_ndwi_media", "C_LS_vi6t_media"]
NEW = ["PL_ndvi_junjul_menos_abrmay", "PL_ndvi_sepoct_menos_julago",
       "PL_ndvi_amplitud_mensual", "S2_ndwi_sepoct_menos_julago"]
MODELOS = ["GLOBAL", "MUN", "MIX", "R_B", "R_T", "H_B", "H_T"]
VISIBLES = ["insumos-visibles", "base-visible", "mensuales-visibles", "descriptores-visibles",
            "variables-control", "diseno-visible", "particiones-visibles", "seleccion-visible",
            "oof-validacion", "metricas-visibles", "pareadas-visibles", "sensibilidad-visible", "cierre"]


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("exp03_generador_pruebas", ROOT / "scripts/construir_exp_03.py")
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
        if c.cell_type != "code":
            continue
        for node in ast.parse(c.source).body:
            if isinstance(node, ast.FunctionDef) and node.name in nombres:
                assert node.name not in defs
                if node.name not in {"bytes_insumo", "leer_csv"}:
                    assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
                defs[node.name] = copy.deepcopy(node)
    assert set(defs) == set(nombres)
    arbol = ast.fix_missing_locations(ast.Module(body=list(defs.values()), type_ignores=[]))
    ns = {"np": np, "pd": pd, "DIAS": DIAS.copy(), "NEW": NEW.copy(),
          "base64": base64, "zlib": zlib, "hashlib": hashlib, "io": io, **extra}
    exec(compile(arbol, "<EXP_03:funciones-visibles>", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def ciencias(notebook, insumos):
    man = json.loads(insumos["manifiesto"]["contenido"])
    return _funciones(notebook, ["medias_mensuales", "media_periodo", "descriptores_temporales",
                                "seleccionar_parametros", "metricas"], MAN=man)


@pytest.fixture(scope="module")
def tablas(insumos):
    return {k: pd.read_csv(io.BytesIO(r["contenido"]), encoding="utf-8-sig")
            for k, r in insumos.items() if r["ruta_local"].endswith(".csv")}


def _registros(notebook):
    for node in ast.parse(_celda(notebook, "insumos-tecnicos").source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSUMOS_INCRUSTADOS"
                                                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Faltan insumos incrustados")


def _toy(sensor="Planet", campo="ndvi_promedio"):
    return pd.DataFrame([{"ID_POLIGONO": pid, "sensor": sensor,
                          "fecha_captura": f"{dia:02d}/{mes:02d}/2025", campo: mes/10 + offset}
                         for pid, offset in [("A", 0.), ("B", .2)]
                         for mes in range(4, 11) for dia in (1, 2)])


def test_construccion_determinista_metadatos_y_celdas_limpias(builder, notebook, config):
    assert all(callable(getattr(builder, k)) for k in ("construir", "cargar_insumos", "huella"))
    assert builder.huella(b"V1") == _sha(b"V1")
    nbformat.validate(notebook)
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == []
            assert "execution" not in c.metadata
    reg = notebook.metadata.agrocebada
    assert reg.id == "EXP_03" and reg.modo == "lector_retrospectivo_sin_ajustes"
    assert reg.fecha_original == "2026-09-29" and reg.fecha_adaptacion == "2026-10-08"
    assert reg.ajustes_actuales == 0 and reg.colab_real_probado is False
    assert reg.recortes_derivados == config["recortes_derivados"]
    assert set(reg.dependencias_requeridas) == {"numpy", "pandas", "matplotlib"}
    nuevo = builder.construir()
    assert [(c.id, c.cell_type, c.source) for c in nuevo.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells]


def test_soporte_autonomo_copiado_de_exp02_sin_modificarlo(builder, notebook):
    assert builder.BASE_SHA256 == BASE_SHA == _sha((ROOT / BASE).read_bytes())
    base = nbformat.read(ROOT / BASE, as_version=4)
    for tag in ("soporte-colab", "preparar-colab", "entorno", "particiones-visibles"):
        assert _celda(notebook, tag).source == _celda(base, tag).source
    reg = notebook.metadata.agrocebada
    assert reg.fuentes_sha256[BASE] == BASE_SHA
    assert reg.soporte_sha256 == base.metadata.agrocebada.soporte_sha256
    assert reg.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())


def test_solo_dos_bloques_tecnicos_plegados_y_ciencia_visible(notebook):
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
    for tag in ["preparar-colab", "entorno"] + VISIBLES:
        c = _celda(notebook, tag)
        assert c.cell_type == "code" and c.metadata.get("cellView") != "form"
        assert not c.metadata.get("jupyter", {}).get("source_hidden", False)


def test_cero_ajustes_descargas_activas_y_lecturas_externas(notebook):
    modelos = {"fit", "fit_transform", "fit_predict", "partial_fit", "predict", "predict_proba",
               "GridSearchCV", "RandomizedSearchCV"}
    descargas = {"obtener_dataset", "download", "urlopen", "urlretrieve"}
    for c in notebook.cells:
        if c.cell_type != "code":
            continue
        soporte = "soporte-colab" in c.metadata.get("tags", [])
        arbol = ast.parse(c.source)
        for node in ast.walk(arbol):
            if isinstance(node, ast.Call):
                nombre = node.func.attr if isinstance(node.func, ast.Attribute) else (
                    node.func.id if isinstance(node.func, ast.Name) else None)
                assert nombre not in modelos, f"Ajuste o predicción prohibidos: {nombre}"
                if not soporte:
                    assert nombre not in descargas
                    assert nombre not in {"open", "read_bytes", "read_text", "read_json", "read_pickle"}
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modulos = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                prohibidos = {"sklearn", "scripts"} | (set() if soporte else {"gdown", "requests", "google"})
                assert not any(m.split(".")[0] in prohibidos or "construir_exp" in m for m in modulos)
        if soporte:
            # Un downloader definido pero inactivo no es una descarga ejecutada.
            activo = ast.Module(body=[n for n in arbol.body if not isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], type_ignores=[])
            for node in ast.walk(activo):
                if isinstance(node, ast.Call):
                    nombre = node.func.attr if isinstance(node.func, ast.Attribute) else (
                        node.func.id if isinstance(node.func, ast.Name) else None)
                    assert nombre not in descargas
    assert "io.BytesIO(bytes_insumo" in _celda(notebook, "insumos-tecnicos").source


def test_18_contratos_y_recortes_con_hashes_originales_separados(notebook, config, insumos):
    registros = _registros(notebook)
    assert len(registros) == len(config["insumos"]) == 18
    assert set(registros) == set(insumos) == set(config["insumos"])
    ns = _funciones(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS=registros)
    for key, contrato in config["insumos"].items():
        bruto = insumos[key]["contenido"]
        assert bruto == (ROOT / contrato["ruta_local"]).read_bytes()
        assert type(contrato["bytes"]) is int and 0 < contrato["bytes"] <= 2*1024*1024
        assert len(bruto) == contrato["bytes"] and _sha(bruto) == contrato["sha256"]
        assert ns["bytes_insumo"](key, contrato["uso"]) == bruto
        assert notebook.metadata.agrocebada.insumos[key]["sha256"] == contrato["sha256"]
    for nombre, key in [("planet", "capturas_planet"), ("s2", "capturas_s2")]:
        rec = config["recortes_derivados"][nombre]
        assert rec["fecha_recorte"] == "2026-10-08" and rec["filtro_nubes"] is False
        assert rec["sha256_recorte"] == config["insumos"][key]["sha256"] != rec["sha256_original"]
        assert rec["ventana"] == ["2025-04-01", "2025-10-31"]


@pytest.mark.parametrize("alteracion", ["contenido", "bytes", "sha", "ausente"])
def test_loader_rechaza_cambios_sin_tocar_fixtures(builder, tmp_path, alteracion):
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
def test_decoder_acotado_rechaza_corrupcion(notebook, alteracion):
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
        reg["bytes_zlib_base64"] = base64.b64encode({"truncado": comprimido[:-1],
            "concatenado": comprimido+zlib.compress(b"otra"), "sobrante": comprimido+b"extra"}[alteracion]).decode()
    ns = _funciones(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS={"dato": reg})
    with pytest.raises((ValueError, zlib.error)):
        ns["bytes_insumo"]("dato", "prueba")


def test_medias_mensuales_conocidas_orden_y_pesos(ciencias):
    fn = ciencias["medias_mensuales"]
    valores, tabla = fn(_toy(), "Planet", "ndvi_promedio", ["B", "A"])
    np.testing.assert_allclose(valores.loc["A"], np.arange(4, 11)/10, atol=1e-14, rtol=0)
    np.testing.assert_allclose(valores.loc["B"], np.arange(4, 11)/10+.2, atol=1e-14, rtol=0)
    assert valores.index.tolist() == ["B", "A"] and valores.columns.tolist() == list(range(4, 11))
    assert len(tabla) == 14 and tabla.n.eq(2).all()
    assert tabla.dias_mes.tolist() == DIAS.tolist()*2
    cambiado = fn(_toy().sample(frac=1, random_state=8), "Planet", "ndvi_promedio", ["B", "A"])
    pd.testing.assert_frame_equal(valores, cambiado[0])
    assert ciencias["media_periodo"](valores, [4, 5]).loc["A"] == pytest.approx((.4*30+.5*31)/61)


def test_nan_no_es_cero_nubes_no_filtradas_y_cero_dependencia_de_etiquetas(ciencias):
    fn = ciencias["medias_mensuales"]
    datos = _toy().query("ID_POLIGONO == 'A'").copy()
    datos["RENDIMIENTO_T_HA"] = 999.
    datos["porcentaje_nubosidad"] = 100.
    before = fn(datos, "Planet", "ndvi_promedio", ["A"])
    datos["RENDIMIENTO_T_HA"] = -999.
    datos["porcentaje_nubosidad"] = 0.
    after = fn(datos, "Planet", "ndvi_promedio", ["A"])
    pd.testing.assert_frame_equal(before[0], after[0])
    extra = datos.iloc[[0]].copy()
    extra.fecha_captura = "03/04/2025"
    mismo = fn(pd.concat([datos, extra]), "Planet", "ndvi_promedio", ["A"])
    pd.testing.assert_frame_equal(before[0], mismo[0])
    extra.ndvi_promedio = np.nan
    nan = fn(pd.concat([datos, extra]), "Planet", "ndvi_promedio", ["A"])
    pd.testing.assert_frame_equal(before[0], nan[0])
    assert nan[1].n.eq(2).all()


@pytest.mark.parametrize("mal", ["sensor", "fecha_formato", "fecha_imposible", "fecha_fuera",
    "mes_ausente", "mes_nan", "duplicado", "inf", "menos_inf", "id_ausente", "id_null",
    "sensor_null", "fecha_null", "columna", "valor_texto", "ids_duplicados", "ids_vacios"])
def test_medias_detienen_recorte_incompatible_sin_imputar(ciencias, mal):
    datos, ids = _toy(), ["A", "B"]
    if mal in {"sensor", "sensor_null"}:
        datos.loc[0, "sensor"] = "Sentinel-2" if mal == "sensor" else None
    elif mal.startswith("fecha_"):
        datos.loc[0, "fecha_captura"] = {"fecha_formato": "2025-04-01", "fecha_imposible": "31/04/2025",
            "fecha_fuera": "01/11/2025", "fecha_null": None}[mal]
    elif mal in {"mes_ausente", "mes_nan"}:
        abril = datos.ID_POLIGONO.eq("A") & datos.fecha_captura.str.contains("/04/")
        if mal == "mes_ausente":
            datos = datos.loc[~abril]
        else:
            datos.loc[abril, "ndvi_promedio"] = np.nan
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
        ciencias["medias_mensuales"](datos, "Planet", "ndvi_promedio", ids)


def test_cuatro_descriptores_sinteticos_pesos_y_amplitud(ciencias):
    p, _ = ciencias["medias_mensuales"](_toy(), "Planet", "ndvi_promedio", ["A", "B"])
    w = p/10
    actual = ciencias["descriptores_temporales"](p, w)
    esperado = [(.6*30+.7*31)/61-(.4*30+.5*31)/61,
                (.9*30+1.*31)/61-(.7*31+.8*31)/62, .6,
                (.09*30+.1*31)/61-(.07*31+.08*31)/62]
    np.testing.assert_allclose(actual.to_numpy(), np.tile(esperado, (2, 1)), atol=1e-14, rtol=0)
    assert actual.columns.tolist() == NEW
    const = p.copy()
    const[:] = .35
    np.testing.assert_allclose(ciencias["descriptores_temporales"](const, const), 0., atol=1e-14, rtol=0)


@pytest.mark.parametrize("meses", [[], [4, 4], [3], [11]])
def test_periodo_rechaza_meses_fuera_de_la_receta(ciencias, meses):
    p, _ = ciencias["medias_mensuales"](_toy(), "Planet", "ndvi_promedio", ["A", "B"])
    with pytest.raises(ValueError):
        ciencias["media_periodo"](p, meses)


@pytest.mark.parametrize("mal", ["ids", "orden_meses", "mes_faltante", "nan", "inf"])
def test_descriptores_detienen_series_incompatibles(ciencias, mal):
    p, _ = ciencias["medias_mensuales"](_toy(), "Planet", "ndvi_promedio", ["A", "B"])
    w = p.copy()
    if mal == "ids":
        w = w.iloc[::-1]
    elif mal == "orden_meses":
        w = w.iloc[:, ::-1]
    elif mal == "mes_faltante":
        w = w.drop(columns=4)
    else:
        w.iloc[0, 0] = np.nan if mal == "nan" else np.inf
    with pytest.raises(ValueError):
        ciencias["descriptores_temporales"](p, w)


def test_2758_mensuales_reales_cuatro_nuevas_y_seis_base_intactas(ciencias, tablas, config, notebook):
    base = tablas["variables_base"].set_index("ID_POLIGONO")
    ctrl = tablas["variables_control"].set_index("ID_POLIGONO")
    assert len(base) == len(ctrl) == 197 and base.index.is_unique and ctrl.index.is_unique
    outputs = []
    curves = []
    for key, sensor, campo in [("capturas_planet", "Planet", "ndvi_promedio"),
                               ("capturas_s2", "Sentinel-2", "ndwi_promedio")]:
        rec = config["recortes_derivados"]["planet" if key == "capturas_planet" else "s2"]
        fuente = tablas[key]
        assert len(fuente) == rec["filas"] and fuente[campo].notna().sum() == rec["no_ausentes"][campo]
        assert fuente[campo].isna().any() and "RENDIMIENTO_T_HA" not in fuente
        values, mensual = ciencias["medias_mensuales"](fuente, sensor, campo, base.index)
        curves.append(values)
        outputs.append(mensual)
    todas = pd.concat(outputs, ignore_index=True)
    keys = ["ID_POLIGONO", "sensor", "indice", "mes"]
    a = todas.set_index(keys).sort_index()
    b = tablas["mensuales_control"].set_index(keys).sort_index()
    assert len(a) == len(b) == 2758 and a.index.is_unique and a.index.equals(b.index)
    np.testing.assert_allclose(a.media, b.media, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(a[["n", "dias_mes"]], b[["n", "dias_mes"]])
    nuevas = ciencias["descriptores_temporales"](*curves)
    assert nuevas.shape == (197, 4) and np.isfinite(nuevas.to_numpy()).all()
    np.testing.assert_allclose(nuevas, ctrl.loc[base.index, NEW], atol=1e-12, rtol=0)
    np.testing.assert_allclose(base[OLD], ctrl.loc[base.index, OLD], atol=1e-12, rtol=0)
    pd.testing.assert_frame_equal(base[["Municipio", "Estado"]], ctrl.loc[base.index, ["Municipio", "Estado"]])
    np.testing.assert_allclose(nuevas.loc["AGC_001"], [.11623540126433077, .31886896670042164,
        .6270855614973262, .2999777517564403], atol=1e-12, rtol=0)
    for c in ["mensuales-visibles", "descriptores-visibles"]:
        # Las funciones de extracción operan sobre capturas, nunca sobre etiquetas.
        for node in ast.parse(_celda(notebook, c).source).body:
            if isinstance(node, ast.FunctionDef):
                assert not any(isinstance(n, ast.Name) and n.id in {"etiquetas", "observado", "predicho"}
                               for n in ast.walk(node))
    assert len(OLD) == 6


@pytest.mark.parametrize("algoritmo,scores,esperado", [
    ("Ridge", [1., 1., 1., 1., 1.], {"alpha": 100.}),
    ("Ridge", [1.+5e-13, 1., 2., 3., 4.], {"alpha": 100.}),
    ("Ridge", [1.+2e-12, 1., 2., 3., 4.], {"alpha": 10.}),
    ("HGB", [1., 1., 1., 1.], {"max_leaf_nodes": 3, "min_samples_leaf": 16}),
    ("HGB", [2., 1., 1., 3.], {"max_leaf_nodes": 3, "min_samples_leaf": 8}),
    ("HGB", [3., 2., 1.+5e-13, 1.], {"max_leaf_nodes": 7, "min_samples_leaf": 16}),
    ("HGB", [3., 2., 1.+2e-12, 1.], {"max_leaf_nodes": 7, "min_samples_leaf": 8}),
])
def test_selector_orden_registrado_tolerancia_y_complejidad(ciencias, algoritmo, scores, esperado):
    assert ciencias["seleccionar_parametros"](algoritmo, scores) == esperado


@pytest.mark.parametrize("alg,scores", [("Otra", [1.]*4), ("Ridge", [1.]*4),
    ("HGB", [1.]*5), ("Ridge", [np.nan]*5), ("HGB", [np.inf]*4),
    ("Ridge", [-1.]*5), ("HGB", [[1.]*4])])
def test_selector_rechaza_algoritmos_o_scores_incompatibles(ciencias, alg, scores):
    with pytest.raises(ValueError):
        ciencias["seleccionar_parametros"](alg, scores)


def test_200_decisiones_900_scores_y_control_ridge_e2(ciencias, tablas):
    d = tablas["seleccion"]
    assert len(d) == 200 and set(d.modelo) == {"R_B", "R_T", "H_B", "H_T"}
    assert not d.duplicated(["modelo", "repeticion", "pliegue"]).any()
    scores = 0
    for _, row in d.iterrows():
        alg = "Ridge" if row.modelo.startswith("R_") else "HGB"
        valores = json.loads(row.scores_internos)
        assert ciencias["seleccionar_parametros"](alg, valores) == json.loads(row.parametros)
        scores += len(valores)
    assert scores == 900
    previos = tablas["alpha_ronda1"].query("modelo == 'E2'")
    control = d.query("modelo == 'R_B'").merge(previos, on=["repeticion", "pliegue"], validate="one_to_one")
    assert len(control) == 50
    for _, row in control.iterrows():
        assert json.loads(row.parametros)["alpha"] == row.alpha
        orden = [row[f"rmse_interno_alpha_{a:g}"] for a in (100., 10., 1., .1, .01)]
        np.testing.assert_allclose(json.loads(row.scores_internos), orden, atol=1e-8, rtol=0)


def test_metricas_pooled_no_promedia_predicciones_y_umbral_historico(ciencias):
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
    assert fn(distinto).RMSE == pytest.approx(np.sqrt(3.))
    assert np.mean([fn(distinto.iloc[:1]).RMSE, fn(distinto.iloc[1:]).RMSE]) == 1.


@pytest.mark.parametrize("y,p", [([], []), ([1., np.nan], [1., 2.]), ([1., 2.], [1., np.inf])])
def test_metricas_rechaza_vacios_y_no_finitos(ciencias, y, p):
    with pytest.raises(ValueError):
        ciencias["metricas"](pd.DataFrame({"observado": y, "predicho": p}))


def test_splits_y_9660_oof_full138_sin_ocultas_ni_etiquetas_inventadas(ciencias, tablas):
    ext, inner = tablas["externas"], tablas["internas"]
    etiquetas = tablas["etiquetas"].set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    assert len(etiquetas) == 138 and etiquetas.index.is_unique and np.isfinite(etiquetas).all()
    assert ext.shape == (6900, 4) and inner.shape == (22080, 5)
    assert set(ext.rol) == set(inner.rol) == {"entrenamiento", "validacion"}
    assert not ext.duplicated(CLAVES).any()
    assert not inner.duplicated(CLAVES[:2]+["pliegue_interno", "ID_POLIGONO"]).any()
    validaciones = ext.loc[ext.rol.eq("validacion")]
    assert validaciones.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()
    esperado = set(map(tuple, validaciones[CLAVES].to_numpy()))
    for (rep, fold), g in ext.groupby(CLAVES[:2]):
        tr = set(g.loc[g.rol.eq("entrenamiento"), "ID_POLIGONO"])
        va = set(g.loc[g.rol.eq("validacion"), "ID_POLIGONO"])
        assert not tr & va and tr | va == set(etiquetas.index)
        dentro = inner.loc[inner.repeticion.eq(rep) & inner.pliegue.eq(fold)]
        assert set(dentro.ID_POLIGONO) == tr and not set(dentro.ID_POLIGONO) & va
        assert set(dentro.pliegue_interno) == {0, 1, 2, 3}
        assert dentro.loc[dentro.rol.eq("validacion")].ID_POLIGONO.is_unique
        for _, q in dentro.groupby("pliegue_interno"):
            assert q.ID_POLIGONO.is_unique and set(q.ID_POLIGONO) == tr
    oof = tablas["oof"]
    assert len(oof) == 9660 and set(oof.modelo) == set(MODELOS)
    assert not oof.duplicated(["modelo"]+CLAVES).any()
    base = tablas["variables_base"].set_index("ID_POLIGONO")
    control = tablas["metricas_control"].set_index("modelo")
    sens = tablas["sensibilidad_control"].set_index("modelo")
    for name, q in oof.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple, q[CLAVES].to_numpy())) == esperado
        np.testing.assert_array_equal(q.observado, q.ID_POLIGONO.map(etiquetas))
        for campo in ["Municipio", "Estado"]:
            np.testing.assert_array_equal(q[campo], q.ID_POLIGONO.map(base[campo]))
        assert q.zona.eq(np.where(q.Municipio.eq("Chignahuapan"), "Chignahuapan", "Resto")).all()
        np.testing.assert_allclose(ciencias["metricas"](q), control.loc[name, ["RMSE", "MAE", "R2"]],
                                   atol=1e-12, rtol=0)
        subset = q.loc[~q.ID_POLIGONO.isin(["AGC_127", "AGC_171"])]
        assert len(subset) == 1360 and subset.ID_POLIGONO.nunique() == 136
        np.testing.assert_allclose(ciencias["metricas"](subset), sens.loc[name, ["RMSE", "MAE", "R2"]],
                                   atol=1e-12, rtol=0)
        pd.testing.assert_frame_equal(subset, q.loc[subset.index])


def test_oof_control_rb_e2_y_referencias_no_solo_metricas(tablas):
    aliases = {"GLOBAL": "Media global", "MUN": "Media municipal", "MIX": "Municipio + IDW fijo"}
    for actual, previo in {"R_B": "E2", **aliases}.items():
        origen = tablas["oof_ronda1"] if actual == "R_B" else tablas["referencias"]
        a = tablas["oof"].query("modelo == @actual").set_index(CLAVES).sort_index()
        b = origen.query("modelo == @previo").set_index(CLAVES).sort_index()
        assert a.index.is_unique and a.index.equals(b.index) and len(a) == 1380
        np.testing.assert_array_equal(a.observado, b.observado)
        np.testing.assert_allclose(a.predicho, b.predicho, atol=1e-8, rtol=0)


def test_dos_factores_pareados_regla_negativa_y_sensibilidad_no_reajusta(ciencias, tablas):
    oof = tablas["oof"]
    metricas = pd.DataFrame({k: ciencias["metricas"](g) for k, g in oof.groupby("modelo")}).T
    rep = pd.DataFrame([{"modelo":k,"repeticion":r,**ciencias["metricas"](g).to_dict()}
                        for (k,r),g in oof.groupby(["modelo","repeticion"])])
    rmse = rep.pivot(index="repeticion", columns="modelo", values="RMSE")
    mae = rep.pivot(index="repeticion", columns="modelo", values="MAE")
    control = tablas["contrastes_control"].set_index(["modelo", "base"])
    for (name, base), fila in control.iterrows():
        np.testing.assert_allclose([metricas.loc[name,"RMSE"]-metricas.loc[base,"RMSE"],
                                   metricas.loc[name,"MAE"]-metricas.loc[base,"MAE"]],
                                  fila[["delta_RMSE", "delta_MAE"]], atol=1e-12, rtol=0)
        assert (rmse[name] < rmse[base]).sum() == fila.reps_menor_RMSE
        assert (mae[name] < mae[base]).sum() == fila.reps_menor_MAE
    assert (rmse.R_T < rmse.R_B).sum() == 1
    assert (rmse.H_T < rmse.H_B).sum() == 6
    assert (rmse.H_B < rmse.R_B).sum() == (rmse.H_T < rmse.R_T).sum() == 0
    for name in ["R_B", "R_T", "H_B", "H_T"]:
        cumple = metricas.loc[name,"RMSE"] < metricas.loc["MIX","RMSE"] and (
            metricas.loc[name,"MAE"] <= metricas.loc["MUN","MAE"]) and (
            (rmse[name] < rmse.MIX).sum() >= 8) and ((mae[name] <= mae.MUN).sum() >= 8)
        assert not cumple
    sens = tablas["sensibilidad_control"].set_index("modelo")
    assert metricas.loc["H_T", "RMSE"] < metricas.loc["H_B", "RMSE"]
    assert sens.loc["H_T", "RMSE"] > sens.loc["H_B", "RMSE"]
    assert oof.loc[oof.zona.eq("Chignahuapan"), "ID_POLIGONO"].nunique() == 71
    assert oof.loc[oof.zona.eq("Resto"), "ID_POLIGONO"].nunique() == 67


def test_cronologia_limites_presupuesto_y_cierre_honesto(notebook, config, insumos):
    texto = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split()).lower()
    for concepto in ["cuatro", "originales", "no sustituimos", "sin filtro de nubes", "calendáric",
                     "julio", "scores", "exploratori", "intervalos de confianza", "no adoptar", "59"]:
        assert concepto in texto
    assert "no repet" in texto or "no reproduc" in texto
    man = json.loads(insumos["manifiesto"]["contenido"])
    reg = json.loads(insumos["registro"]["contenido"])
    assert man["variantes"]["R_B"]["variables"] == OLD
    assert man["variantes"]["R_T"]["variables"] == OLD+NEW
    assert man["variantes"]["H_B"]["variables"] == OLD
    assert man["variantes"]["H_T"]["variables"] == OLD+NEW
    assert sum(man["presupuesto"].values()) == 3800
    assert config["ajustes_internos_historicos"] == 3600
    assert config["reajustes_exteriores_historicos"] == 200
    assert man["registrado_utc"].startswith("2026-09-29T")
    assert reg["inicio_utc"].startswith("2026-09-30T02:")
    assert reg["versiones"]["python"] == "3.12.14" and reg["versiones"]["sklearn"] == "1.9.1"
    campos = {}
    for node in ast.walk(ast.parse(_celda(notebook, "cierre").source)):
        if isinstance(node, ast.Dict):
            campos.update({k.value: v.value for k, v in zip(node.keys, node.values, strict=True)
                           if isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Constant)})
    assert campos["ajustes_actuales"] == campos["predicciones_finales_generadas"] == 0
    assert campos["scores_interiores_recalculados"] is campos["predicciones_recalculadas"] is False
    assert campos["procedimientos"] == 7 and campos["poblacion"] == "FULL138"
    assert "\"variantes_adoptadas\":[]" in _celda(notebook, "cierre").source
