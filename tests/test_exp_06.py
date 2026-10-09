"""EXP_06: extracción visible de pico y lectura de OOF, sin nuevos ajustes.

Los casos sintéticos aíslan las guardas; los controles reales contrastan datos
sellados. Ninguna prueba ajusta un predictor ni calcula las 59 predicciones.
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
CONFIG = "config/exp_06_pico_soportado.json"
BASE = "notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb"
BASE_SHA = "f99e113361c5546929eadb9c43abf92ecc1944592fc2fb84860d9c7b469ba6f2"
KEY = ["repeticion", "pliegue", "ID_POLIGONO"]
NUM = ["C_PL_ndvi_media", "C_PL_ndvi_pico_prom", "C_PL_ndvi_doy_pico_prom",
       "C_S2_ndvi_media", "C_S2_ndwi_media", "C_LS_vi6t_media"]
PEAK = NUM[2]
ALPHAS = [.01, .1, 1., 10., 100.]
MODELOS = ["E2", "V4", "GLOBAL", "MUN", "MIX"]
VISIBLE = ["capturas-visibles", "diarios-visibles", "pico-visible", "variables-visibles",
           "particiones-visibles", "seleccion-visible", "metricas-visibles", "regla-visible",
           "soporte-visible", "cierre"]


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _cell(nb, tag):
    found = [c for c in nb.cells if tag in c.metadata.get("tags", [])]
    assert len(found) == 1, f"Celda única requerida: {tag}"
    return found[0]


def _functions(nb, names=None, **extra):
    found = {}
    for c in nb.cells:
        if c.cell_type != "code":
            continue
        hidden = c.metadata.get("jupyter", {}).get("source_hidden", False)
        for n in ast.parse(c.source).body:
            if isinstance(n, ast.FunctionDef) and (names is None and not hidden or names and n.name in names):
                assert n.name not in found
                if n.name not in {"bytes_insumo", "leer_csv"}:
                    assert not hidden
                found[n.name] = copy.deepcopy(n)
    if names:
        assert set(found) == set(names)
    module = ast.fix_missing_locations(ast.Module(body=list(found.values()), type_ignores=[]))
    ns = {"np": np, "pd": pd, "ALPHAS": ALPHAS.copy(), "GRID": ALPHAS.copy(),
          "MODELOS": MODELOS.copy(), "NUM": NUM.copy(), "PEAK": PEAK, "KEY": KEY.copy(),
          "CLAVES": KEY.copy(), "ID": "ID_POLIGONO", "Y": "RENDIMIENTO_T_HA",
          "SCORE_COLS": [f"rmse_interno_alpha_{a:g}" for a in ALPHAS],
          "base64": base64, "zlib": zlib, "hashlib": hashlib, "io": io, **extra}
    exec(compile(module, "<EXP_06:funciones-visibles>", "exec"), ns)
    return ns


def _records(nb):
    for n in ast.parse(_cell(nb, "insumos-tecnicos").source).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSUMOS_INCRUSTADOS"
                                             for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError("Faltan insumos incrustados")


def _scene(tablas, name):
    return tablas["oof"] if name == "FULL138" else tablas["oof"].loc[tablas["oof"].municipio_visto]


def _metricas(q):
    e = q.predicho.to_numpy(float) - q.observado.to_numpy(float)
    sst = float(np.sum((q.observado.to_numpy(float)-q.observado.mean())**2))
    return {"n_oof": len(q), "n_parcelas": q.ID_POLIGONO.nunique(),
            "RMSE": float(np.sqrt(np.mean(e**2))), "MAE": float(np.mean(np.abs(e))),
            "R2": float(1-np.sum(e**2)/sst) if sst > 1e-12 else np.nan}


def _curve(t=None, x=None):
    t = np.arange(91., 302., 7.) if t is None else np.asarray(t, float)
    x = -.1 + .8*np.maximum(0, 1-np.abs(t-196)/50) if x is None else np.asarray(x, float)
    n = len(t)
    return pd.DataFrame({"ID_POLIGONO": ["AGC_001"]*n,
        "fecha": pd.Timestamp("2025-01-01")+pd.to_timedelta(t-1, unit="D"), "doy": t,
        "ndvi_diario": x, "ndvi_min_del_dia": x, "ndvi_max_del_dia": x,
        "n_filas": np.ones(n, int), "n_indice_finito": np.ones(n, int),
        "n_fuera_rango": np.zeros(n, int), "n_qa_desconocida": np.zeros(n, int),
        "n_qa_100": np.zeros(n, int), "n_qa_gt20": np.zeros(n, int),
        "qa_min": np.zeros(n), "qa_max": np.zeros(n), "n_filas_duplicadas_exactas": np.zeros(n, int)})


def _identity_recipe(recipe):
    r = copy.deepcopy(recipe)
    r["curva"].update(semiventana_dias=0, minimo_dias_en_ventana=1)
    return r


def _scores():
    return pd.DataFrame({"modelo": ["V4"], "repeticion": [0], "pliegue": [0], "alpha": [.01],
        **{f"rmse_interno_alpha_{a:g}": [1.] for a in ALPHAS}})


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("exp06_generador_pruebas", ROOT / "scripts/construir_exp_06.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def config():
    return json.loads((ROOT / CONFIG).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def insumos(builder):
    return builder.cargar_insumos(ROOT)


@pytest.fixture(scope="module")
def notebook(builder, config):
    paths = [ROOT / BASE, ROOT / CONFIG, ROOT / "scripts/colab_soporte.py",
             ROOT / "requirements-colab-auditoria.txt"]
    paths += [ROOT / c["ruta_local"] for c in config["insumos"].values()]
    old = {p: _sha(p.read_bytes()) for p in paths}
    nb = builder.construir(ROOT)
    assert all(_sha(p.read_bytes()) == h for p, h in old.items())
    return nb


@pytest.fixture(scope="module")
def ciencias(notebook):
    ns = _functions(notebook)
    assert {"agregar_diario", "mediana_movil", "pico_soportado", "seleccionar_alpha_guardado", "metricas"} <= set(ns)
    return ns


@pytest.fixture(scope="module")
def tablas(insumos):
    return {k: pd.read_csv(io.BytesIO(v["contenido"]), encoding="utf-8-sig", float_precision="round_trip")
            for k, v in insumos.items() if v["ruta_local"].endswith(".csv")}


@pytest.fixture(scope="module")
def receta(insumos):
    return json.loads(insumos["receta"]["contenido"])


@pytest.fixture(scope="module")
def reconstruccion(ciencias, tablas, receta):
    diarios = ciencias["agregar_diario"](tablas["capturas"])
    results = [ciencias["pico_soportado"](q, receta) for _, q in diarios.groupby("ID_POLIGONO", sort=True)]
    return diarios, pd.DataFrame([row for row, _ in results]), pd.concat([curve for _, curve in results], ignore_index=True)


def test_construccion_limpia_determinista_metadata(builder, notebook, config):
    nbformat.validate(notebook)
    assert builder.huella(b"V4") == _sha(b"V4")
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == [] and "execution" not in c.metadata
    r = notebook.metadata.agrocebada
    assert r.id == "EXP_06" and r.modo == "lector_retrospectivo_sin_ajustes"
    assert r.fecha_adaptacion == "2026-10-08" and r.ajustes_actuales == 0
    assert r.colab_real_probado is False
    assert config["fecha_original"] == "2026-10-06" and config["fecha_factibilidad"] == "2026-10-02"
    assert config["poblacion_principal"] == "SEEN135" and config["poblacion_secundaria"] == "FULL138"
    assert set(r.dependencias_requeridas) == {"numpy", "pandas", "matplotlib"}
    new = builder.construir(ROOT)
    assert [(c.id, c.cell_type, c.source) for c in new.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells]


def test_soporte_y_particiones_copiados_sin_mutar_anterior(builder, notebook):
    assert builder.BASE_SHA256 == BASE_SHA == _sha((ROOT / BASE).read_bytes())
    base = nbformat.read(ROOT / BASE, as_version=4)
    for tag in ("soporte-colab", "preparar-colab", "entorno", "particiones-visibles"):
        assert _cell(notebook, tag).source == _cell(base, tag).source
    assert notebook.metadata.agrocebada.base_sha256 == BASE_SHA
    assert notebook.metadata.agrocebada.soporte_sha256 == base.metadata.agrocebada.soporte_sha256
    assert notebook.metadata.agrocebada.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())


def test_solo_dos_celdas_tecnicas_plegadas_ciencia_visible(notebook):
    hidden = [c for c in notebook.cells if c.cell_type == "code"
              and c.metadata.get("jupyter", {}).get("source_hidden", False)]
    assert len(hidden) == 2
    for tag in ("soporte-colab", "insumos-tecnicos"):
        c = _cell(notebook, tag)
        title, _, code = c.source.partition("\n")
        assert c in hidden and c.metadata.cellView == "form"
        assert title.startswith("# @title ") and title.endswith('{ display-mode: "form" }')
        assert len(title) < 180 and ast.dump(ast.parse(c.source)) == ast.dump(ast.parse(code))
    for tag in ["preparar-colab", "entorno"] + VISIBLE:
        assert not _cell(notebook, tag).metadata.get("jupyter", {}).get("source_hidden", False)


def test_sin_ajustar_descargar_archivos_ni_importar_modelos_runtime(notebook):
    fits = {"fit", "fit_transform", "fit_predict", "predict", "predict_proba", "partial_fit",
            "GridSearchCV", "RandomizedSearchCV", "ajustar", "predecir", "solve", "lstsq"}
    downloads = {"download", "obtener_dataset", "urlopen", "urlretrieve"}
    for c in notebook.cells:
        if c.cell_type != "code":
            continue
        support = "soporte-colab" in c.metadata.get("tags", [])
        tree = ast.parse(c.source)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                name = n.func.attr if isinstance(n.func, ast.Attribute) else (
                    n.func.id if isinstance(n.func, ast.Name) else None)
                assert name not in fits
                if not support:
                    assert name not in downloads | {"open", "read_bytes", "read_text", "read_json", "read_pickle"}
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                banned = {"sklearn", "rasterio", "shapely", "pyproj", "scripts"} | (
                    set() if support else {"gdown", "requests", "google"})
                assert not any(m.split(".")[0] in banned or "construir_exp" in m for m in names)
        if support:
            active = ast.Module(body=[n for n in tree.body if not isinstance(
                n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))], type_ignores=[])
            for n in ast.walk(active):
                if isinstance(n, ast.Call):
                    name = n.func.attr if isinstance(n.func, ast.Attribute) else (
                        n.func.id if isinstance(n.func, ast.Name) else None)
                    assert name not in downloads


def test_24_contratos_y_decoder_round_trip(notebook, config, insumos):
    records = _records(notebook)
    assert len(records) == len(config["insumos"]) == len(insumos) == 24
    assert set(records) == set(config["insumos"]) == set(insumos)
    ns = _functions(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS=records)
    for k, c in config["insumos"].items():
        blob = insumos[k]["contenido"]
        assert type(c["bytes"]) is int and 0 < c["bytes"] <= 2*1024*1024
        assert blob == (ROOT / c["ruta_local"]).read_bytes()
        assert len(blob) == c["bytes"] and _sha(blob) == c["sha256"]
        assert ns["bytes_insumo"](k, c["uso"]) == blob
        if c["ruta_local"].endswith(".csv"):
            expected = pd.read_csv(io.BytesIO(blob), encoding="utf-8-sig", float_precision="round_trip")
            pd.testing.assert_frame_equal(ns["leer_csv"](k, c["uso"]), expected)


@pytest.mark.parametrize("change", ["uso", "sha", "bytes_menos", "bytes_mas", "bytes_cero",
    "bytes_negativo", "bytes_bool", "bytes_float", "bytes_limite", "base64", "base64_limite",
    "truncado", "concatenado", "sobrante"])
def test_decoder_acotado_corrupcion(notebook, change):
    blob = b"dato\n1\n"
    compressed = zlib.compress(blob)
    r = {"uso": "prueba", "bytes": len(blob), "sha256": _sha(blob),
         "bytes_zlib_base64": base64.b64encode(compressed).decode()}
    if change == "uso":
        r["uso"] = "otro"
    elif change == "sha":
        r["sha256"] = "0"*64
    elif change.startswith("bytes_"):
        r["bytes"] = {"bytes_menos": len(blob)-1, "bytes_mas": len(blob)+1, "bytes_cero": 0,
                      "bytes_negativo": -1, "bytes_bool": True, "bytes_float": float(len(blob)),
                      "bytes_limite": 2*1024*1024+1}[change]
    elif change == "base64":
        r["bytes_zlib_base64"] = "!no_base64!"
    elif change == "base64_limite":
        r["bytes_zlib_base64"] = "A"*(4*1024*1024+1)
    else:
        r["bytes_zlib_base64"] = base64.b64encode({"truncado": compressed[:-1],
            "concatenado": compressed+zlib.compress(b"otra"), "sobrante": compressed+b"extra"}[change]).decode()
    ns = _functions(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS={"dato": r})
    with pytest.raises((ValueError, zlib.error)):
        ns["bytes_insumo"]("dato", "prueba")


@pytest.mark.parametrize("change", ["contenido", "bytes", "sha", "ausente"])
def test_loader_rechaza_modificacion(builder, tmp_path, change):
    blob = b"dato\n1\n"
    c = {"ruta_local": "dato.csv", "bytes": len(blob), "sha256": _sha(blob), "uso": "prueba"}
    if change == "bytes":
        c["bytes"] += 1
    elif change == "sha":
        c["sha256"] = "0"*64
    (tmp_path / "config").mkdir()
    (tmp_path / CONFIG).write_text(json.dumps({"insumos": {"dato": c}}), encoding="utf-8")
    if change != "ausente":
        (tmp_path / "dato.csv").write_bytes(b"dato\n2\n" if change == "contenido" else blob)
    with pytest.raises((ValueError, FileNotFoundError)):
        builder.cargar_insumos(tmp_path)


@pytest.mark.parametrize("name,key", [("variables.csv", "variables_fuente"), ("etiquetas.csv", "etiquetas"),
    ("outer.csv", "externas"), ("inner.csv", "internas"), ("e2_oof.csv", "e2_oof"),
    ("e2_alpha.csv", "e2_alpha"), ("receta_fenologia.json", "receta"),
    ("descriptores.csv", "descriptores_control"), ("referencias.csv", "referencias")])
def test_manifiesto_historico_exactamente_conservado(name, key, config, insumos):
    manifest = json.loads(insumos["manifiesto"]["contenido"])
    old = manifest["archivos"][name]
    c = config["insumos"][key]
    assert old["bytes"] == c["bytes"] and old["sha256"] == c["sha256"]
    assert _sha(insumos[key]["contenido"]) == old["sha256"]


def test_registro_anterior_local_presupuesto_y_cero_predicciones(insumos):
    prior = json.loads(insumos["registro_previo"]["contenido"])
    run = json.loads(insumos["registro_ejecucion"]["contenido"])
    assert pd.Timestamp(prior["registrado_utc"]) < pd.Timestamp(run["inicio_utc"]) < pd.Timestamp(run["fin_utc"])
    assert run["registro_sha256"] == _sha(insumos["registro_previo"]["contenido"])
    assert prior["archivos_sellados"]["protocolo.md"] == _sha(insumos["protocolo"]["contenido"])
    assert prior["archivos_sellados"]["receta_fenologia.json"] == _sha(insumos["receta"]["contenido"])
    assert "No sello externo" in prior["naturaleza"] and "adaptativa" in prior["naturaleza"]
    assert prior["reproducciones_programadas"] == 2 and prior["ajustes_fisicos_programados"] == 4200
    assert run["presupuesto"] == {"E2": {"interiores": 1000, "exteriores": 50},
                                  "V4": {"interiores": 1000, "exteriores": 50}, "total_ajustes": 2100}
    assert run["predicciones_oficiales_generadas"] == 0 and run["entorno"]["python"] == "3.12.14"
    assert prior["pruebas_previas"]["pruebas_ejecutadas"] == 46
    assert prior["pruebas_previas"]["etiquetas_reales_utilizadas"] is False


def test_hashes_ocho_salidas_y_factibilidad(insumos):
    run = json.loads(insumos["registro_ejecucion"]["contenido"])
    mapping = {"oof": "predicciones_oof.csv", "alphas": "alphas.csv", "metricas_control": "metricas.csv",
        "repeticiones_control": "metricas_repeticion.csv", "region_control": "metricas_region.csv",
        "concentracion_control": "concentracion.csv", "sensibilidad_control": "sensibilidad.csv",
        "soporte_control": "soporte_59_solo_X.csv"}
    assert set(run["archivos_resultados"]) == set(mapping.values())
    for key, name in mapping.items():
        assert run["archivos_resultados"][name] == _sha(insumos[key]["contenido"])
    fact = json.loads(insumos["registro_factibilidad"]["contenido"])
    assert fact["receta_sha256"] == _sha(insumos["receta"]["contenido"])
    assert fact["salidas_sha256"]["curvas.csv"] == _sha(insumos["curvas_control"]["contenido"])
    assert fact["salidas_sha256"]["descriptores.csv"] == _sha(insumos["descriptores_control"]["contenido"])


def test_recorte_capturas_de_hoy_no_finge_fecha_historica(config, tablas):
    r = config["recorte_capturas"]
    x = tablas["capturas"]
    assert r["fecha_recorte"] == "2026-10-08" and r["filas_fuente"] == 47804
    assert len(x) == r["filas_recorte"] == 26255 and x.ID_POLIGONO.nunique() == 197
    assert set(x.columns) == set(r["columnas"]) and len(x.columns) == 5
    assert r["recorte_sha256"] == config["insumos"]["capturas"]["sha256"]
    assert r["fuente_original_sha256"] == "91697f8f8d4ad5e59f766acbce2ef76f3c405eb02b41c1de92d62a07e8321888"
    assert set(x.sensor) == {"Planet"} and "RENDIMIENTO_T_HA" not in x
    dates = pd.to_datetime(x.fecha_captura, format="%d/%m/%Y", errors="raise")
    assert dates.between("2025-04-01", "2025-10-31").all()
    assert not x.duplicated(["ID_POLIGONO", "fecha_captura"]).any()


def test_media_diaria_no_filtra_nubes_duplicados_ni_rellena_indice(ciencias):
    raw = pd.DataFrame({"ID_POLIGONO": ["AGC_001"]*6,
        "fecha_captura": ["01/04/2025"]*4+["02/04/2025"]*2, "sensor": ["Planet"]*6,
        "ndvi_promedio": [.2, .8, .8, np.nan, np.nan, np.inf],
        "porcentaje_nubosidad": [0., 100., 100., np.nan, 100., 30.]})
    old = raw.copy(deep=True)
    d = ciencias["agregar_diario"](raw).set_index("doy")
    assert len(d) == 2 and d.loc[91, "n_filas"] == 4 and d.loc[91, "n_indice_finito"] == 3
    assert d.loc[91, "ndvi_diario"] == pytest.approx(.6)
    assert d.loc[91, "n_qa_100"] == 2 and d.loc[91, "n_qa_gt20"] == 2
    assert d.loc[91, "n_qa_desconocida"] == 1 and d.loc[91, "n_filas_duplicadas_exactas"] == 2
    assert d.loc[92, "n_indice_finito"] == 0 and np.isnan(d.loc[92, "ndvi_diario"])
    pd.testing.assert_frame_equal(raw, old)


def test_ndvi_extremo_se_conserva_y_no_se_recorta(ciencias):
    raw = pd.DataFrame({"ID_POLIGONO": ["AGC_001"]*2,
        "fecha_captura": ["01/04/2025"]*2, "sensor": ["Planet"]*2,
        "ndvi_promedio": [-1.2, .8], "porcentaje_nubosidad": [0., 100.]})
    d = ciencias["agregar_diario"](raw)
    assert d.n_fuera_rango.iloc[0] == 1
    assert d.ndvi_min_del_dia.iloc[0] == -1.2 and d.ndvi_diario.iloc[0] == pytest.approx(-.2)


def test_suavizado_en_dias_no_filas_minimo_inclusivo(ciencias):
    t = np.array([91., 92., 93., 110., 111., 117.])
    x = np.array([.1, .3, .9, .7, .5, .2])
    oldt, oldx = t.copy(), x.copy()
    r = ciencias["mediana_movil"](t, x, 7, 3)
    np.testing.assert_allclose(r, [.3, .3, .3, .5, .5, .5], atol=0, rtol=0)
    assert np.isnan(ciencias["mediana_movil"](t[:2], x[:2], 7, 3)).all()
    np.testing.assert_array_equal(t, oldt)
    np.testing.assert_array_equal(x, oldx)


@pytest.mark.parametrize("t,x", [(np.array([2., 1.]), np.array([.1, .2])),
    (np.array([1., 2.]), np.array([.1])), (np.array([[1., 2.]]), np.array([.1, .2])),
    (np.array([1., 2.]), np.array([.1, np.nan])), (np.array([1., np.inf]), np.array([.1, .2]))])
def test_suavizado_rechaza_forma_orden_y_no_finitos(ciencias, t, x):
    with pytest.raises(ValueError):
        ciencias["mediana_movil"](t, x, 7, 3)


def test_pico_soportado_curva_valida_no_muta_receta(ciencias, receta):
    r = _identity_recipe(receta)
    g = _curve()
    oldg, oldr = g.copy(deep=True), copy.deepcopy(r)
    d, curve = ciencias["pico_soportado"](g, r)
    assert d["estado_pico"] == "ok" and d["pico_soportado_doy"] == 196.
    assert d["baseline_q10"] == pytest.approx(-.1) and d["amplitud"] == pytest.approx(.8)
    assert d["n_soporte_izq"] == d["n_soporte_der"] == 3
    np.testing.assert_allclose(curve.ndvi_suavizado, g.ndvi_diario, atol=0, rtol=0)
    pd.testing.assert_frame_equal(g, oldg)
    assert r == oldr


@pytest.mark.parametrize("case,flag", [("pocos", "pocos_dias"), ("extremo", "ndvi_fuera_rango"),
    ("hueco", "hueco_global"), ("incompleta", "ventana_incompleta"),
    ("plana", "amplitud_baja"), ("meseta", "pico_ambiguo"),
    ("censura", "pico_censurado"), ("sin_lado", "pico_sin_soporte_bilateral"),
    ("sin_curva", "sin_curva_suavizada")])
def test_guardas_dejan_nan_no_cero(ciencias, receta, case, flag):
    r = _identity_recipe(receta)
    g = _curve()
    if case == "pocos":
        g = g.iloc[5:20].copy()
    elif case == "extremo":
        g.loc[g.index[0], "n_fuera_rango"] = 1
    elif case == "hueco":
        g = g.loc[~g.doy.between(147, 175)].copy()
    elif case == "incompleta":
        g = g.loc[g.doy.ge(112)].copy()
    elif case == "plana":
        g.ndvi_diario = .4
    elif case == "meseta":
        g.loc[g.doy.between(168, 196), "ndvi_diario"] = .8
    elif case == "censura":
        g.ndvi_diario = np.where(g.doy.eq(98), .8, -.1)
    elif case == "sin_lado":
        g = g.loc[~g.doy.isin([175, 182])].copy()
    else:
        r["curva"]["minimo_dias_en_ventana"] = 100
    d, _ = ciencias["pico_soportado"](g, r)
    assert flag in d["estado_pico"].split("|")
    assert np.isnan(d["pico_soportado_doy"])


def test_meseta_centro_medio_dia_y_limite_catorce_inclusivo(ciencias, receta):
    r = _identity_recipe(receta)
    g = _curve()
    g.ndvi_diario = np.where(g.doy.isin([189, 196]), .8, -.1)
    d, _ = ciencias["pico_soportado"](g, r)
    assert d["estado_pico"] == "ok" and d["pico_soportado_doy"] == 192.5
    g.ndvi_diario = np.where(g.doy.isin([182, 196]), .8, -.1)
    d, _ = ciencias["pico_soportado"](g, r)
    assert d["estado_pico"] == "ok" and d["pico_soportado_doy"] == 189.
    g.ndvi_diario = np.where(g.doy.eq(105), .8, -.1)
    d, _ = ciencias["pico_soportado"](g, r)
    assert d["estado_pico"] == "ok" and d["pico_soportado_doy"] == 105.


def test_pico_usa_percentil_de_crudo_no_suavizado(ciencias, receta):
    g = _curve(np.arange(91., 304.))
    g.loc[g.index[::5], "ndvi_diario"] = -.7
    d, curve = ciencias["pico_soportado"](g, receta)
    assert d["baseline_q10"] == np.quantile(g.ndvi_diario, .1, method="linear")
    assert d["baseline_q10"] != np.quantile(curve.ndvi_suavizado.dropna(), .1, method="linear")


def test_reconstruccion_diaria_curvas_y_guardas_exactas(reconstruccion, tablas):
    daily, desc, curves = reconstruccion
    assert len(daily) == 26255 and daily.ID_POLIGONO.nunique() == 197
    assert len(curves) == 18248 and len(desc) == 197 and desc.ID_POLIGONO.is_unique
    ctl_curve = tablas["curvas_control"].copy()
    ctl_curve.fecha = pd.to_datetime(ctl_curve.fecha, format="%Y-%m-%d")
    for col in ctl_curve.columns:
        assert col in curves
    a = curves.set_index(["ID_POLIGONO", "fecha"]).sort_index()[ctl_curve.columns.drop(["ID_POLIGONO", "fecha"])]
    b = ctl_curve.set_index(["ID_POLIGONO", "fecha"]).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a.to_numpy(float), b.to_numpy(float), atol=1e-12, rtol=0, equal_nan=True)
    control = tablas["descriptores_control"].set_index("ID_POLIGONO").sort_index()
    actual = desc.set_index("ID_POLIGONO").sort_index()
    assert "estado_pico" in actual and "pico_soportado_doy" in actual
    assert actual.index.equals(control.index)
    for c in actual.columns:
        assert c in control.columns
        if c == "estado_pico":
            np.testing.assert_array_equal(actual[c], control[c])
        else:
            np.testing.assert_allclose(actual[c], control[c], atol=1e-12, rtol=0, equal_nan=True)


def test_disponibilidad197_y_bandera_diagnostica_no_predictor(reconstruccion, tablas):
    _, desc, _ = reconstruccion
    x, y = tablas["variables_fuente"], tablas["etiquetas"]
    desc = desc.set_index("ID_POLIGONO")
    assert desc.pico_soportado_doy.notna().sum() == 158 and desc.pico_soportado_doy.isna().sum() == 39
    assert desc.loc[y.ID_POLIGONO].pico_soportado_doy.notna().sum() == 108
    hidden = x.loc[~x.ID_POLIGONO.isin(y.ID_POLIGONO), "ID_POLIGONO"]
    assert len(hidden) == 59 and desc.loc[hidden].pico_soportado_doy.notna().sum() == 50
    base = x[["ID_POLIGONO", "Municipio", "Estado"]+NUM].set_index("ID_POLIGONO").sort_index()
    alt = base.copy(deep=True)
    alt[PEAK] = desc.pico_soportado_doy.reindex(alt.index)
    pd.testing.assert_frame_equal(base.drop(columns=PEAK), alt.drop(columns=PEAK), check_exact=True)
    assert list(alt.columns) == ["Municipio", "Estado"]+NUM
    assert "estado_pico" not in alt and "pico_ausente" not in alt and "anchura_lobulo_50_dias" not in alt
    assert base.loc["AGC_001", PEAK] == 245. and alt.loc["AGC_001", PEAK] == 262.5


def test_anchura_ausente_no_invalida_pico_y_nan_no_se_descarta(reconstruccion, tablas):
    _, d, _ = reconstruccion
    a = d.set_index("ID_POLIGONO").loc["AGC_001"]
    c = tablas["descriptores_control"].set_index("ID_POLIGONO").loc["AGC_001"]
    assert a.estado_pico == "ok" and a.pico_soportado_doy == 262.5
    assert np.isnan(c.anchura_lobulo_50_dias) and c.estado_anchura == "sin_cruce_derecho"
    assert d.ID_POLIGONO.nunique() == 197 and len(tablas["etiquetas"]) == 138


@pytest.mark.parametrize("ties,choice", [([.01, .1], .1), ([.01, 10.], 10.), ([1.], 1.), (ALPHAS, 100.)])
def test_selector_empata_con_alpha_mayor_no_baseline(ciencias, ties, choice):
    s = _scores()
    for a in ALPHAS:
        s[f"rmse_interno_alpha_{a:g}"] = 1. if a in ties else 2.
    r = ciencias["seleccionar_alpha_guardado"](s)
    assert len(r) == 1 and float(r.alpha_elegido.iloc[0]) == choice


def test_selector_tolerancia_absoluta_un_e_menos12(ciencias):
    s = _scores()
    for a in ALPHAS:
        s[f"rmse_interno_alpha_{a:g}"] = 2.
    s["rmse_interno_alpha_0.01"] = 1.
    s["rmse_interno_alpha_0.1"] = 1.+.5e-12
    s["rmse_interno_alpha_100"] = 1.+2e-12
    assert ciencias["seleccionar_alpha_guardado"](s).alpha_elegido.iloc[0] == .1


@pytest.mark.parametrize("case", ["vacio", "duplicado", "score_ausente", "nan", "inf", "negativo"])
def test_selector_rechaza_scores_incompletos_o_invalidos(ciencias, case):
    s = _scores()
    if case == "vacio":
        s = s.iloc[:0]
    elif case == "duplicado":
        s = pd.concat([s, s])
    elif case == "score_ausente":
        s = s.drop(columns="rmse_interno_alpha_100")
    else:
        s["rmse_interno_alpha_0.01"] = {"nan": np.nan, "inf": np.inf, "negativo": -1.}[case]
    with pytest.raises(ValueError):
        ciencias["seleccionar_alpha_guardado"](s)


def test_cien_selecciones_quinientos_scores_y_control_e2(ciencias, tablas):
    s = tablas["alphas"]
    assert len(s) == 100 and set(s.modelo) == {"E2", "V4"}
    assert not s.duplicated(["modelo", "repeticion", "pliegue"]).any()
    out = ciencias["seleccionar_alpha_guardado"](s)
    assert len(out) == 100
    idx = ["modelo", "repeticion", "pliegue"]
    a = out.set_index(idx).sort_index()
    b = s.set_index(idx).sort_index()
    np.testing.assert_array_equal(a.alpha_elegido, b.alpha)
    for name, expected in [("E2", {.01: 6, .1: 37, 1.: 7}), ("V4", {.01: 9, .1: 33, 1.: 8})]:
        assert a.loc[name].alpha_elegido.value_counts().to_dict() == expected
    previous = tablas["e2_alpha"].loc[tablas["e2_alpha"].modelo.eq("E2")].set_index(idx).sort_index()
    assert len(previous) == 50
    assert b.loc["E2"].shape == previous.loc["E2"].shape
    np.testing.assert_allclose(b.loc["E2"], previous.loc["E2"], atol=1e-8, rtol=0)
    assert len(s)*len(ALPHAS) == 500


def test_particiones50_200_cubren_solo_etiquetas_y_son_anidadas(tablas, reconstruccion):
    e, inner = tablas["externas"], tablas["internas"]
    ids = set(tablas["etiquetas"].ID_POLIGONO)
    assert set(map(tuple, e[["repeticion", "pliegue"]].drop_duplicates().to_numpy())) == {
        (r, f) for r in range(10) for f in range(5)}
    assert len(inner.groupby(["repeticion", "pliegue", "pliegue_interno"])) == 200
    tr = {}
    for key, q in e.groupby(["repeticion", "pliegue"]):
        assert set(q.ID_POLIGONO) == ids and not q.ID_POLIGONO.duplicated().any()
        tr[key] = set(q.loc[q.rol.eq("entrenamiento"), "ID_POLIGONO"])
        assert not tr[key] & set(q.loc[q.rol.eq("validacion"), "ID_POLIGONO"])
    supports = []
    d = reconstruccion[1].set_index("ID_POLIGONO").pico_soportado_doy
    for (r, f, _), q in inner.groupby(["repeticion", "pliegue", "pliegue_interno"]):
        assert set(q.ID_POLIGONO) == tr[(r, f)] and not q.ID_POLIGONO.duplicated().any()
        a = set(q.loc[q.rol.eq("entrenamiento"), "ID_POLIGONO"])
        assert not a & set(q.loc[q.rol.eq("validacion"), "ID_POLIGONO"])
        supports.append(d.loc[sorted(a)].notna().sum())
    assert min(supports) == 59
    v = e.loc[e.rol.eq("validacion")]
    assert len(v) == 1380 and v.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()
    for key, q in inner.loc[inner.rol.eq("validacion")].groupby(["repeticion", "pliegue"]):
        counts = q.groupby("ID_POLIGONO").size()
        assert set(counts.index) == tr[key] and counts.eq(1).all()


def test_oof_6900_claves_y_etiquetas_metadata_138_no59(tablas):
    o, x = tablas["oof"], tablas["variables_fuente"].set_index("ID_POLIGONO")
    y = tablas["etiquetas"].set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    keys = set(map(tuple, tablas["externas"].loc[tablas["externas"].rol.eq("validacion"), KEY].to_numpy()))
    seen = []
    for (r, f), roles in tablas["externas"].groupby(["repeticion", "pliegue"]):
        known = set(roles.loc[roles.rol.eq("entrenamiento"), "ID_POLIGONO"].map(x.Municipio))
        q = roles.loc[roles.rol.eq("validacion"), KEY].copy()
        q["municipio_visto"] = q.ID_POLIGONO.map(x.Municipio).isin(known)
        seen.append(q)
    seen = pd.concat(seen).set_index(KEY).municipio_visto
    assert len(o) == 6900 and set(o.modelo) == set(MODELOS)
    assert not o.duplicated(["modelo"]+KEY).any()
    for _, q in o.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple, q[KEY].to_numpy())) == keys and np.isfinite(q.predicho).all()
        np.testing.assert_array_equal(q.observado, q.ID_POLIGONO.map(y))
        np.testing.assert_array_equal(q.Municipio, q.ID_POLIGONO.map(x.Municipio))
        np.testing.assert_array_equal(q.municipio_visto, seen.reindex(pd.MultiIndex.from_frame(q[KEY])))
        assert q.municipio_visto.sum() == 1350 and q.loc[q.municipio_visto, "ID_POLIGONO"].nunique() == 135
        assert set(q.loc[~q.municipio_visto, "ID_POLIGONO"]) == {"AGC_164", "AGC_048", "AGC_047"}


@pytest.mark.parametrize("model,old", [("GLOBAL", "Media global"), ("MUN", "Media municipal"),
    ("MIX", "Municipio + IDW fijo"), ("E2", "E2")])
def test_predicciones_control_referencias_y_e2_sin_reajustar(tablas, model, old):
    a = tablas["oof"].loc[tablas["oof"].modelo.eq(model)].set_index(KEY).sort_index()
    src = tablas["e2_oof"] if model == "E2" else tablas["referencias"]
    b = src.loc[src.modelo.eq(old)].set_index(KEY).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a.predicho, b.predicho, atol=1e-8, rtol=0)
    if model == "E2":
        np.testing.assert_array_equal(a.alpha, b.alpha)


def test_metricas_formula_pooled_no_promedio_por_parcela(ciencias):
    t = pd.DataFrame({"ID_POLIGONO": ["A", "B", "C"], "observado": [1., 2., 3.], "predicho": [1., 2., 5.]})
    m = ciencias["metricas"](t)
    np.testing.assert_allclose([m[k] for k in ["RMSE", "MAE", "R2"]], [np.sqrt(4/3), 2/3, -1.], atol=1e-15, rtol=0)
    assert m["n_oof"] == m["n_parcelas"] == 3
    repeated = pd.DataFrame({"ID_POLIGONO": ["A", "A"], "observado": [2., 2.], "predicho": [1., 3.]})
    r = ciencias["metricas"](repeated)
    assert r["n_oof"] == 2 and r["n_parcelas"] == 1 and r["RMSE"] == r["MAE"] == 1.
    assert np.isnan(r["R2"])


@pytest.mark.parametrize("case", ["vacio", "nan_y", "inf_pred"])
def test_metricas_rechazan_datos_incompletos(ciencias, case):
    t = pd.DataFrame({"ID_POLIGONO": ["A", "B"], "observado": [1., 2.], "predicho": [1., 3.]})
    if case == "vacio":
        t = t.iloc[:0]
    elif case == "nan_y":
        t.loc[0, "observado"] = np.nan
    else:
        t.loc[0, "predicho"] = np.inf
    with pytest.raises(ValueError):
        ciencias["metricas"](t)


@pytest.mark.parametrize("scene", ["SEEN135", "FULL138"])
def test_metricas_escenarios_repeticiones_y_territorio_exactas(ciencias, tablas, scene):
    o = _scene(tablas, scene)
    for name, group_col in [("metricas_control", None), ("repeticiones_control", "repeticion"),
                            ("region_control", "region")]:
        control = tablas[name].loc[tablas[name].escenario.eq(scene)]
        for _, r in control.iterrows():
            q = o.loc[o.modelo.eq(r.modelo)]
            if group_col == "repeticion":
                q = q.loc[q.repeticion.eq(r.repeticion)]
            elif group_col == "region":
                q = q.loc[q.Municipio.eq("Chignahuapan") if r.region == "Chignahuapan" else ~q.Municipio.eq("Chignahuapan")]
            m = ciencias["metricas"](q)
            independent = _metricas(q)
            for col in ["n_oof", "n_parcelas", "RMSE", "MAE", "R2"]:
                np.testing.assert_allclose(m[col], r[col], atol=1e-12, rtol=0, equal_nan=True)
                np.testing.assert_allclose(m[col], independent[col], atol=1e-12, rtol=0, equal_nan=True)


def test_regla_no_adopta_mejora_pequena_e2(tablas, insumos):
    o = _scene(tablas, "SEEN135")
    m = {n: _metricas(q) for n, q in o.groupby("modelo")}
    rep = {r: {n: _metricas(q) for n, q in g.groupby("modelo")} for r, g in o.groupby("repeticion")}
    decision = {"escenario_principal": "SEEN135", "mejora_E2_RMSE": m["V4"]["RMSE"] < m["E2"]["RMSE"],
        "mejora_E2_repeticiones": sum(q["V4"]["RMSE"] < q["E2"]["RMSE"] for q in rep.values()),
        "supera_MIX_RMSE_agrupado": m["V4"]["RMSE"] < m["MIX"]["RMSE"],
        "no_empeora_MUN_MAE_agrupado": m["V4"]["MAE"] <= m["MUN"]["MAE"],
        "rep_RMSE_mejor_MIX": sum(q["V4"]["RMSE"] < q["MIX"]["RMSE"] for q in rep.values()),
        "rep_MAE_no_peor_MUN": sum(q["V4"]["MAE"] <= q["MUN"]["MAE"] for q in rep.values()),
        "cumple_regla": False}
    run = json.loads(insumos["registro_ejecucion"]["contenido"])
    assert decision == run["decision"]
    assert len(rep) == 10 and decision["mejora_E2_repeticiones"] == 9
    assert decision["rep_RMSE_mejor_MIX"] == decision["rep_MAE_no_peor_MUN"] == 0
    assert m["V4"]["RMSE"]-m["E2"]["RMSE"] == pytest.approx(-.005040, abs=1e-6)
    assert m["V4"]["MAE"] > m["E2"]["MAE"]


def test_concentracion_y_sensibilidad_solo_evaluacion_no_reentrena(tablas):
    groups = {}
    for _, row in tablas["concentracion_control"].iterrows():
        q = _scene(tablas, row.escenario)
        a = q.loc[q.modelo.eq("V4")].set_index(KEY).sort_index()
        b = q.loc[q.modelo.eq(row.comparador)].set_index(KEY).sort_index()
        assert a.index.equals(b.index)
        gains = (b.predicho-b.observado)**2-(a.predicho-a.observado)**2
        parcels = gains.groupby("ID_POLIGONO").sum().sort_values(ascending=False)
        chosen = parcels.head(row.top_n).index.tolist()
        assert row.ids == ";".join(chosen)
        np.testing.assert_allclose([row.ganancia_sse_neta, row.ganancia_sse_top, row.fraccion_ganancia_positiva_top],
            [parcels.sum(), parcels.head(row.top_n).sum(), parcels.head(row.top_n).clip(lower=0).sum()/parcels.clip(lower=0).sum()],
            atol=1e-12, rtol=0)
        groups[(row.escenario, f"sin_top{row.top_n}_favorables_V4_vs_{row.comparador}")] = chosen
    for _, row in tablas["sensibilidad_control"].iterrows():
        q = _scene(tablas, row.escenario)
        ids = ["AGC_127", "AGC_171"] if row.sensibilidad == "sin_AGC_127_171" else groups[(row.escenario, row.sensibilidad)]
        q = q.loc[q.modelo.eq(row.modelo)&~q.ID_POLIGONO.isin(ids)]
        m = _metricas(q)
        for col in ["n_oof", "n_parcelas", "RMSE", "MAE", "R2"]:
            np.testing.assert_allclose(m[col], row[col], atol=1e-12, rtol=0, equal_nan=True)
    c = tablas["concentracion_control"].query("escenario == 'SEEN135' and comparador == 'E2' and top_n == 5").iloc[0]
    assert c.ids == "AGC_185;AGC_069;AGC_152;AGC_049;AGC_160"
    assert c.ganancia_sse_top > c.ganancia_sse_neta
    s = tablas["sensibilidad_control"].query("escenario == 'SEEN135' and sensibilidad == 'sin_top5_favorables_V4_vs_E2'").set_index("modelo")
    assert s.loc["V4", "RMSE"] > s.loc["E2", "RMSE"]


def test_soporte59_solo_x_nueve_nan_cuatro_fuera_un_singleton(tablas, reconstruccion):
    x, labels = tablas["variables_fuente"].set_index("ID_POLIGONO"), set(tablas["etiquetas"].ID_POLIGONO)
    d = reconstruccion[1].set_index("ID_POLIGONO").pico_soportado_doy
    support = tablas["soporte_control"].set_index("ID_POLIGONO")
    hidden = set(x.index)-labels
    assert set(support.index) == hidden and len(support) == 59
    assert "predicho" not in support and "RENDIMIENTO_T_HA" not in support
    assert support.pico_ausente.sum() == 9 and support.caso_singleton.sum() == 1
    assert support.fuera_rango_municipal.eq(True).sum() == 4
    np.testing.assert_allclose(support.pico_soportado_doy, d.reindex(support.index), atol=1e-12, rtol=0, equal_nan=True)
    for pid, h in support.iterrows():
        known = x.loc[x.index.isin(labels)&x.Municipio.eq(h.Municipio)]
        peak = d.loc[known.index].dropna()
        assert h.Municipio == x.loc[pid, "Municipio"]
        assert h.n_etiquetas_municipio == len(known) and h.n_picos_soportados_municipio == len(peak)
        if h.pico_ausente or not len(peak):
            assert pd.isna(h.fuera_rango_municipal)
        else:
            assert bool(h.fuera_rango_municipal) == bool(h.pico_soportado_doy < peak.min() or h.pico_soportado_doy > peak.max())
    missing = support.loc[support.pico_ausente].Municipio.value_counts().to_dict()
    assert missing == {"Chignahuapan": 4, "Cuautepec de Hinojosa": 4, "Singuilucan": 1}
    assert support.loc["AGC_120", "caso_singleton"] and support.loc["AGC_120", "n_etiquetas_municipio"] == 1
