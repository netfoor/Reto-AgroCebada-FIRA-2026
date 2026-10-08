"""EXP_05: fórmulas y evaluación histórica visibles, sin entrenar modelos.

Las etiquetas oficiales solo verifican OOF ya guardadas; los casos sintéticos
ejercitan aritmética, selección y errores de entrada sin ajustar pendientes.
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
CONFIG = "config/exp_05_historico_octubre.json"
BASE = "notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb"
BASE_SHA = "b5086d1acaab17ae53dd9e260692b754bc198f7976dd372696e4b2ba88730f39"
CLAVES = ["repeticion", "pliegue", "ID_POLIGONO"]
GRID = ["baseline", .01, .1, 1., 10., 100.]
CANDIDATOS = ["R9_PCT", "R9_P", "R9_H", "R9_HP"]
MODELOS = ["MUN", "MIX", "J5_PCT"] + CANDIDATOS
VARIABLES = {"R9_PCT": ["A_pct"], "R9_P": ["P_actual_mm"],
             "R9_H": ["H_mm"], "R9_HP": ["H_mm", "P_actual_mm"]}
VISIBLE = ["variables-visibles", "recetas-visibles", "particiones-visibles", "seleccion-visible",
           "parametros-visibles", "escenarios-visibles", "metricas-visibles", "regla-visible",
           "contrastes-visibles", "territorio-visible", "soporte-visible", "concentracion-visible", "cierre"]


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _cell(nb, tag):
    found = [c for c in nb.cells if tag in c.metadata.get("tags", [])]
    assert len(found) == 1, f"Celda única requerida: {tag}"
    return found[0]


def _functions(nb, names, **extra):
    found = {}
    for c in nb.cells:
        if c.cell_type != "code":
            continue
        for n in ast.parse(c.source).body:
            if isinstance(n, ast.FunctionDef) and n.name in names:
                assert n.name not in found
                if n.name not in {"bytes_insumo", "leer_csv"}:
                    assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
                found[n.name] = copy.deepcopy(n)
    assert set(found) == set(names)
    module = ast.fix_missing_locations(ast.Module(body=list(found.values()), type_ignores=[]))
    ns = {"np": np, "pd": pd, "GRID": GRID.copy(), "ALPHAS": GRID.copy(),
          "MODELOS": MODELOS.copy(), "CANDIDATOS": CANDIDATOS.copy(), "VARIABLES": VARIABLES.copy(),
          "SPECS": VARIABLES.copy(), "CLAVES": CLAVES.copy(), "KEY": CLAVES.copy(), "ID": "ID_POLIGONO",
          "base64": base64, "zlib": zlib, "hashlib": hashlib, "io": io, **extra}
    exec(compile(module, "<EXP_05:funciones-visibles>", "exec"), ns)
    return ns


def _indexed(df):
    return df.set_index("modelo") if "modelo" in df.columns else df


def _scene(tablas, name):
    o = tablas["oof"]
    if name == "todas":
        return o
    return o.loc[o.municipio_visto if name == "municipio_visto" else ~o.municipio_visto]


def _seen(tablas):
    mun = tablas["variables_fuente"].set_index("ID_POLIGONO").Municipio
    rows = []
    for _, q in tablas["externas"].groupby(["repeticion", "pliegue"]):
        known = set(q.loc[q.rol.eq("entrenamiento"), "ID_POLIGONO"].map(mun))
        v = q.loc[q.rol.eq("validacion"), CLAVES].copy()
        v["municipio_visto"] = v.ID_POLIGONO.map(mun).isin(known)
        rows.append(v)
    return pd.concat(rows, ignore_index=True)


def _alpha(v):
    return "baseline" if str(v) == "baseline" else float(v)


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("exp05_generador_pruebas", ROOT / "scripts/construir_exp_05.py")
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


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
    return _functions(notebook, ["variables_octubre", "seleccionar_alpha_guardado",
                                 "metricas", "tabla_metricas", "regla_avance", "soporte_entrega"])


@pytest.fixture(scope="module")
def tablas(insumos):
    return {k: pd.read_csv(io.BytesIO(v["contenido"]), encoding="utf-8-sig", float_precision="round_trip")
            for k, v in insumos.items() if v["ruta_local"].endswith(".csv")}


def _records(nb):
    for n in ast.parse(_cell(nb, "insumos-tecnicos").source).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "INSUMOS_INCRUSTADOS"
                                             for t in n.targets):
            return ast.literal_eval(n.value)
    raise AssertionError("Faltan insumos incrustados")


def _toy():
    return pd.DataFrame({"ID_POLIGONO": ["AGC_001", "AGC_002"], "P_2022_mm": [30., 60.],
                         "P_2023_mm": [60., 90.], "P_2024_mm": [90., 120.], "P_2025_mm": [90., 45.]})


def _scores():
    return pd.DataFrame({"modelo": ["R9_PCT"]*6, "repeticion": [0]*6, "pliegue": [0]*6,
                         "alpha": [str(a) for a in GRID], "RMSE_interior": [1.]*6})


def test_construccion_limpia_metadata_y_determinismo(builder, notebook, config):
    nbformat.validate(notebook)
    assert builder.huella(b"V3") == _sha(b"V3")
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == [] and "execution" not in c.metadata
    reg = notebook.metadata.agrocebada
    assert reg.id == "EXP_05" and reg.modo == "lector_retrospectivo_sin_ajustes"
    assert reg.fecha_adaptacion == "2026-10-08" and reg.ajustes_actuales == 0
    assert reg.colab_real_probado is False
    assert config["fecha_original_mexico"] == "2026-10-01" and config["fecha_original_utc"] == "2026-10-02"
    assert config["poblacion_principal"] == "SEEN135" and config["poblacion_secundaria"] == "FULL138"
    assert set(reg.dependencias_requeridas) == {"numpy", "pandas", "matplotlib"}
    new = builder.construir()
    assert [(c.id, c.cell_type, c.source) for c in new.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells]


def test_soporte_copiado_y_anterior_inmutable(builder, notebook):
    assert builder.BASE_SHA256 == BASE_SHA == _sha((ROOT / BASE).read_bytes())
    base = nbformat.read(ROOT / BASE, as_version=4)
    for tag in ("soporte-colab", "preparar-colab", "entorno", "particiones-visibles"):
        assert _cell(notebook, tag).source == _cell(base, tag).source
    assert notebook.metadata.agrocebada.fuentes_sha256[BASE] == BASE_SHA
    assert notebook.metadata.agrocebada.soporte_sha256 == base.metadata.agrocebada.soporte_sha256
    assert notebook.metadata.agrocebada.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())


def test_dos_celdas_tecnicas_plegadas_ciencia_visible(notebook):
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
        c = _cell(notebook, tag)
        assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
        assert c.metadata.get("cellView") != "form"


def test_sin_ajuste_descarga_activa_ni_archivos_runtime(notebook):
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


def test_21_contratos_exactos_y_round_trip(notebook, config, insumos):
    records = _records(notebook)
    assert len(records) == len(config["insumos"]) == len(insumos) == 21
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
    assert 'float_precision="round_trip"' in _cell(notebook, "insumos-tecnicos").source


@pytest.mark.parametrize("name,key", [("variables.csv", "variables_fuente"), ("etiquetas.csv", "etiquetas"),
                                     ("exteriores.csv", "externas"), ("interiores.csv", "internas"),
                                     ("referentes_v2.csv", "v2_oof"), ("protocolo.md", "protocolo")])
def test_manifiesto_historico_fuentes_no_se_modifica(name, key, config, insumos):
    manifest = json.loads(insumos["manifiesto"]["contenido"])
    old = manifest["archivos"][name]
    c = config["insumos"][key]
    assert old["bytes"] == c["bytes"] and old["sha256"] == c["sha256"]
    assert _sha(insumos[key]["contenido"]) == old["sha256"]
    assert manifest["DataSet.zip_sha256"] == "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"


def test_registro_interno_anterior_a_corrida_y_no_sello_terceros(insumos):
    prior = json.loads(insumos["registro_previo"]["contenido"])
    run = json.loads(insumos["registro_ejecucion"]["contenido"])
    assert pd.Timestamp(prior["registrado_utc"]) < pd.Timestamp(run["inicio_utc"]) < pd.Timestamp(run["fin_utc"])
    assert _sha(insumos["registro_previo"]["contenido"]) == run["registro_previo_sha256"]
    assert prior["sha256"]["protocolo.md"] == _sha(insumos["protocolo"]["contenido"])
    assert prior["sha256"]["insumos_v3.zip"] == run["paquete_sha256"]
    assert "exploratorio" in prior["naturaleza"] and "no sello externo" in prior["naturaleza"]


def test_hashes_salidas_historicas_explicitas(config, insumos):
    run = json.loads(insumos["registro_ejecucion"]["contenido"])
    mapping = {"oof": "predicciones_oof.csv", "parametros": "parametros_exteriores.csv",
               "seleccion": "seleccion_interna.csv", "metricas_control": "metricas_escenario.csv",
               "repeticiones_control": "metricas_repeticion.csv", "municipios_control": "metricas_municipio.csv",
               "zonas_control": "metricas_zona.csv", "regla_control": "regla_avance.csv",
               "contrastes_control": "contrastes.csv", "soporte_control": "soporte_entrega.csv",
               "deltas_control": "deltas_parcela.csv", "concentracion_control": "concentracion.csv"}
    for key, old in mapping.items():
        assert run["sha256_salidas"][old] == config["insumos"][key]["sha256"] == _sha(insumos[key]["contenido"])


@pytest.mark.parametrize("change", ["contenido", "bytes", "sha", "ausente"])
def test_loader_no_acepta_insumo_modificado(builder, tmp_path, change):
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


def test_variables_manual_positiva_negativa_orden_independiente(ciencias):
    src = _toy()
    old = src.copy(deep=True)
    result = ciencias["variables_octubre"](src)
    assert result.index.name == "ID_POLIGONO" and result.index.tolist() == ["AGC_001", "AGC_002"]
    np.testing.assert_allclose(result.loc["AGC_001", ["H_mm", "P_actual_mm", "A_mm", "A_pct"]],
                               [60., 90., 30., 50.], atol=1e-12, rtol=0)
    np.testing.assert_allclose(result.loc["AGC_002", ["H_mm", "P_actual_mm", "A_mm", "A_pct"]],
                               [90., 45., -45., -50.], atol=1e-12, rtol=0)
    pd.testing.assert_frame_equal(src, old)
    pd.testing.assert_frame_equal(result, ciencias["variables_octubre"](src.iloc[::-1]))


@pytest.mark.parametrize("change", ["vacio", "duplicado", "id_ausente", "anio_ausente", "nan",
                                   "inf", "negativa", "H_cero", "H_menor_uno", "id_formato"])
def test_variables_rechazan_entradas_sin_imputar(ciencias, change):
    src = _toy()
    if change == "vacio":
        src = src.iloc[:0]
    elif change == "duplicado":
        src.loc[1, "ID_POLIGONO"] = "AGC_001"
    elif change == "id_ausente":
        src.loc[1, "ID_POLIGONO"] = None
    elif change == "id_formato":
        src.loc[1, "ID_POLIGONO"] = "AGC2"
    elif change == "anio_ausente":
        src = src.drop(columns="P_2023_mm")
    elif change in {"nan", "inf", "negativa"}:
        src.loc[1, "P_2025_mm"] = {"nan": np.nan, "inf": np.inf, "negativa": -1.}[change]
    else:
        src.loc[1, ["P_2022_mm", "P_2023_mm", "P_2024_mm"]] = 0 if change == "H_cero" else .99
    with pytest.raises(ValueError):
        ciencias["variables_octubre"](src)


def test_H_un_mm_es_frontera_inclusiva_y_puede_no_llover_actual(ciencias):
    src = _toy()
    src.loc[1, ["P_2022_mm", "P_2023_mm", "P_2024_mm"]] = 1.
    src.loc[1, "P_2025_mm"] = 0.
    r = ciencias["variables_octubre"](src)
    np.testing.assert_allclose(r.loc["AGC_002", ["H_mm", "P_actual_mm", "A_mm", "A_pct"]], [1., 0., -1., -100.])


def test_variables_reales_197_roles_etiquetas_aparte(ciencias, tablas):
    x = tablas["variables_fuente"]
    y = tablas["etiquetas"]
    result = ciencias["variables_octubre"](x)
    assert len(result) == 197 and result.index.is_unique
    assert "RENDIMIENTO_T_HA" not in x and "RENDIMIENTO_T_HA" not in result
    pd.testing.assert_frame_equal(result, x.set_index("ID_POLIGONO").sort_index()[result.columns],
                                  check_exact=False, atol=1e-9, rtol=0)
    assert len(y) == 138 and y.ID_POLIGONO.is_unique and np.isfinite(y.RENDIMIENTO_T_HA).all()
    assert set(x.loc[x.CONJUNTO.eq("ENTRENAMIENTO"), "ID_POLIGONO"]) == set(y.ID_POLIGONO)
    assert x.CONJUNTO.eq("PREDICCION").sum() == 59
    assert x.cobertura_min.ge(.99).all() and x.estado.eq("ok").all() and result.H_mm.ge(1).all()


def test_mismo_exceso_porcentajes_distintos_no_causa(ciencias):
    x = _toy()
    x.loc[0, ["P_2022_mm", "P_2023_mm", "P_2024_mm", "P_2025_mm"]] = [50., 50., 50., 70.]
    x.loc[1, ["P_2022_mm", "P_2023_mm", "P_2024_mm", "P_2025_mm"]] = [100., 100., 100., 120.]
    r = ciencias["variables_octubre"](x)
    np.testing.assert_allclose(r.A_mm, [20., 20.])
    np.testing.assert_allclose(r.A_pct, [40., 20.])


@pytest.mark.parametrize("ties,choice", [(["baseline", "100.0"], "baseline"),
                                         (["0.01", "0.1", "10.0"], 10.), (["1.0"], 1.)])
def test_selector_empate_baseline_y_mayor_penalizacion(ciencias, ties, choice):
    s = _scores()
    s.RMSE_interior = [1. if a in ties else 2. for a in s.alpha]
    r = ciencias["seleccionar_alpha_guardado"](s)
    assert len(r) == 1 and _alpha(r.alpha_elegido.iloc[0]) == choice


def test_selector_usa_total_y_no_cifra_solo_visto(ciencias):
    s = _scores()
    s.RMSE_interior = [2., 1., 3., 4., 5., 6.]
    s["RMSE_interior_visto"] = [1., 2., 3., 4., 5., 6.]
    r = ciencias["seleccionar_alpha_guardado"](s)
    assert _alpha(r.alpha_elegido.iloc[0]) == .01


@pytest.mark.parametrize("change", ["vacio", "duplicado", "alpha_ausente", "alpha_invalido", "nan", "inf", "negativo"])
def test_selector_rechaza_grid_incompleto_y_scores_invalidos(ciencias, change):
    s = _scores()
    if change == "vacio":
        s = s.iloc[:0]
    elif change == "duplicado":
        s = pd.concat([s, s.iloc[:1]])
    elif change == "alpha_ausente":
        s = s.iloc[:5]
    elif change == "alpha_invalido":
        s.loc[0, "alpha"] = "999"
    elif change == "negativo":
        s.loc[0, "RMSE_interior"] = -1.
    else:
        s.loc[0, "RMSE_interior"] = np.nan if change == "nan" else np.inf
    with pytest.raises(ValueError):
        ciencias["seleccionar_alpha_guardado"](s)


def test_200_elecciones_guardadas_1200_scores_y_ceros(ciencias, tablas):
    s = tablas["seleccion"]
    assert len(s) == 1200 and not s.duplicated(["modelo", "repeticion", "pliegue", "alpha"]).any()
    r = ciencias["seleccionar_alpha_guardado"](s).set_index(["modelo", "repeticion", "pliegue"])
    assert len(r) == 200 and set(r.index.get_level_values("modelo")) == set(CANDIDATOS)
    assert r.groupby("modelo").size().eq(50).all()
    for key, q in s.groupby(["modelo", "repeticion", "pliegue"]):
        assert len(q) == 6 and set(map(_alpha, q.alpha)) == set(GRID)
        assert q.elegido.sum() == 1
        assert _alpha(r.loc[key, "alpha_elegido"]) == _alpha(q.loc[q.elegido, "alpha"].iloc[0])
    baselines = r.alpha_elegido.map(_alpha).eq("baseline").groupby("modelo").sum().to_dict()
    assert baselines == {"R9_H": 13, "R9_HP": 15, "R9_P": 32, "R9_PCT": 1}


def test_parametros_250_filas_no_son_250_reajustes(tablas, insumos):
    p = tablas["parametros"]
    assert len(p) == 250 and not p.duplicated(["modelo", "repeticion", "pliegue", "variable"]).any()
    assert len(p.groupby(["modelo", "repeticion", "pliegue"])) == 200
    assert p.groupby("modelo").size().to_dict() == {"R9_H": 50, "R9_HP": 100, "R9_P": 50, "R9_PCT": 50}
    for model, q in p.groupby("modelo"):
        assert set(q.variable) == set(VARIABLES[model])
    assert np.isfinite(p[["beta_estandarizada", "escala", "pendiente_unidad_original"]]).all().all()
    assert p.escala.gt(0).all() and not p.columna_degenerada.any()
    np.testing.assert_allclose(p.beta_estandarizada/p.escala, p.pendiente_unidad_original, atol=1e-12, rtol=0)
    assert set(p.n_entrenamiento) == {110, 111}
    reg = json.loads(insumos["registro_ejecucion"]["contenido"])
    assert reg["presupuesto"] == {"evaluaciones_internas": 4800, "baseline_interno": 800,
                                 "ajustes_ridge_internos": 4000, "reajustes_exteriores": 200, "controles_MUN": 50}
    assert reg["python"] == "3.12.14" and reg["inicio_utc"].startswith("2026-10-02")


def test_particiones_50_exteriores_200_interiores_y_contencion(tablas):
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
    for (r, f, _), q in inner.groupby(["repeticion", "pliegue", "pliegue_interno"]):
        assert set(q.ID_POLIGONO) == tr[(r, f)] and not q.ID_POLIGONO.duplicated().any()
        assert not set(q.loc[q.rol.eq("entrenamiento"), "ID_POLIGONO"]) & set(
            q.loc[q.rol.eq("validacion"), "ID_POLIGONO"])
    for key, q in inner.loc[inner.rol.eq("validacion")].groupby(["repeticion", "pliegue"]):
        counts = q.groupby("ID_POLIGONO").size()
        assert set(counts.index) == tr[key] and counts.eq(1).all()
    v = e.loc[e.rol.eq("validacion")]
    assert len(v) == 1380 and v.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()


def test_oof_9660_mismas_claves_etiquetas_metadata_y_poblaciones(tablas):
    o, x = tablas["oof"], tablas["variables_fuente"].set_index("ID_POLIGONO")
    y = tablas["etiquetas"].set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    keys = set(map(tuple, tablas["externas"].loc[tablas["externas"].rol.eq("validacion"), CLAVES].to_numpy()))
    mask = _seen(tablas).set_index(CLAVES).municipio_visto
    assert len(o) == 9660 and set(o.modelo) == set(MODELOS)
    assert not o.duplicated(["modelo"]+CLAVES).any()
    for _, q in o.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple, q[CLAVES].to_numpy())) == keys and np.isfinite(q.predicho).all()
        np.testing.assert_array_equal(q.observado, q.ID_POLIGONO.map(y))
        for col in ["Municipio", "grupo_J5", "celda_centroide"]:
            np.testing.assert_array_equal(q[col], q.ID_POLIGONO.map(x[col]))
        np.testing.assert_array_equal(q.zona, np.where(q.Municipio.eq("Chignahuapan"), "Chignahuapan", "resto"))
        np.testing.assert_array_equal(q.municipio_visto, mask.reindex(pd.MultiIndex.from_frame(q[CLAVES])))
        assert q.municipio_visto.sum() == 1350 and q.loc[q.municipio_visto, "ID_POLIGONO"].nunique() == 135
        assert set(q.loc[~q.municipio_visto, "ID_POLIGONO"]) == {"AGC_164", "AGC_048", "AGC_047"}


@pytest.mark.parametrize("model,old", [("MUN", "MUN"), ("MIX", "MIX"), ("J5_PCT", "J5_PCT"),
                                      ("R9_PCT", "R9_PCT"), ("R9_P", "R9_RAW")])
def test_controles_oof_v2_y_100_alphas_en_alpha_estado(tablas, model, old):
    a = tablas["oof"].loc[tablas["oof"].modelo.eq(model)].set_index(CLAVES).sort_index()
    b = tablas["v2_oof"].loc[tablas["v2_oof"].modelo.eq(old)].set_index(CLAVES).sort_index()
    assert a.index.equals(b.index)
    np.testing.assert_allclose(a.predicho, b.predicho, atol=1e-8, rtol=0)
    if model in {"R9_PCT", "R9_P"}:
        counts = 0
        for key, q in a.groupby(["repeticion", "pliegue"]):
            oq = b.loc[key]
            ctl = oq.alpha_estado.astype(str).str.split("|", regex=False).str[0].unique()
            assert len(ctl) == 1 and q.alpha.nunique() == 1
            assert _alpha(ctl[0]) == _alpha(q.alpha.iloc[0])
            counts += 1
        assert counts == 50


def test_metricas_manual_agrupadas_y_r2_estandar(ciencias):
    t = pd.DataFrame({"ID_POLIGONO": ["A", "B", "C"], "observado": [1., 2., 3.], "predicho": [1., 2., 5.]})
    m = ciencias["metricas"](t)
    assert m["n_oof"] == 3 and m["n_parcelas"] == 3
    np.testing.assert_allclose([m[k] for k in ["RMSE", "MAE", "R2"]], [np.sqrt(4/3), 2/3, -1.], atol=1e-15, rtol=0)
    assert np.isnan(ciencias["metricas"](t.assign(observado=1))["R2"])
    repeated = pd.concat([t, t], ignore_index=True)
    r = ciencias["metricas"](repeated)
    assert r["n_oof"] == 6 and r["n_parcelas"] == 3
    assert r["RMSE"] == m["RMSE"]


def test_metricas_no_promedian_predicciones_repetidas_por_parcela(ciencias):
    t = pd.DataFrame({"ID_POLIGONO": ["A", "A"], "observado": [2., 2.], "predicho": [1., 3.]})
    r = ciencias["metricas"](t)
    assert r["n_oof"] == 2 and r["n_parcelas"] == 1
    assert r["RMSE"] == r["MAE"] == 1.
    assert np.isnan(r["R2"])


def test_r2_no_usa_residuo_de_redondeo_como_varianza_real(ciencias):
    t = pd.DataFrame({"ID_POLIGONO": ["A"]*10, "observado": [3.01]*10, "predicho": [3.5]*10})
    assert np.sum((t.observado-t.observado.mean())**2) < 1e-12
    assert np.isnan(ciencias["metricas"](t)["R2"])


def test_14_r2_municipales_no_definidos_conservan_gold_sin_mutarlo(ciencias, tablas, notebook):
    ctl = tablas["municipios_control"]
    old = ctl.copy(deep=True)
    afectados = 0
    for _, r in ctl.iterrows():
        q = _scene(tablas, r.escenario)
        q = q.loc[q.modelo.eq(r.modelo)&q.Municipio.eq(r.Municipio)]
        m = ciencias["metricas"](q)
        if np.isnan(m.R2) and np.isfinite(r.R2):
            afectados += 1
            assert r.Municipio == "Tepeapulco" and set(q.ID_POLIGONO) == {"AGC_047"}
            np.testing.assert_allclose(m[["RMSE","MAE"]],r[["RMSE","MAE"]].to_numpy(float),atol=1e-12,rtol=0)
    assert afectados == 14
    pd.testing.assert_frame_equal(ctl,old)
    assert notebook.metadata.agrocebada.r2_municipales_presentacion_nan == 14


@pytest.mark.parametrize("change", ["vacio", "y_nan", "p_inf"])
def test_metricas_rechazan_no_finitos_y_vacio(ciencias, change):
    t = pd.DataFrame({"ID_POLIGONO": ["A", "B"], "observado": [1., 2.], "predicho": [1., 3.]})
    if change == "vacio":
        t = t.iloc[:0]
    elif change == "y_nan":
        t.loc[0, "observado"] = np.nan
    else:
        t.loc[0, "predicho"] = np.inf
    with pytest.raises(ValueError):
        ciencias["metricas"](t)


@pytest.mark.parametrize("scene", ["todas", "municipio_visto", "municipio_no_visto"])
def test_metricas_tres_escenarios_exactos(ciencias, tablas, scene):
    r = _indexed(ciencias["tabla_metricas"](_scene(tablas, scene))).sort_index()
    ctl = tablas["metricas_control"].loc[tablas["metricas_control"].escenario.eq(scene)].set_index("modelo").sort_index()
    for col in ["n_oof", "n_parcelas", "RMSE", "MAE", "R2"]:
        np.testing.assert_allclose(r[col], ctl[col], atol=1e-12, rtol=0, equal_nan=True)


@pytest.mark.parametrize("scene", ["todas", "municipio_visto"])
def test_regla_nula_en_principal_y_secundario(ciencias, tablas, scene):
    r = _indexed(ciencias["regla_avance"](_scene(tablas, scene))).sort_index()
    ctl = tablas["regla_control"].loc[tablas["regla_control"].escenario.eq(scene)].set_index("modelo").sort_index()
    assert set(r.index) == set(CANDIDATOS) and not r.cumple.any()
    for col in ["RMSE", "MAE", "delta_RMSE_MIX", "delta_MAE_MUN", "reps_RMSE_MIX", "reps_MAE_MUN"]:
        np.testing.assert_allclose(r[col], ctl[col], atol=1e-12, rtol=0)
    np.testing.assert_array_equal(r.cumple, ctl.cumple)


def test_regla_exige_diez_repeticiones_y_mismas_claves(ciencias, tablas):
    o = _scene(tablas, "municipio_visto")
    with pytest.raises(ValueError):
        ciencias["regla_avance"](o.loc[o.repeticion.ne(9)])


def test_todos_los_contrastes_pareados_sin_causalidad(ciencias, tablas):
    labels = {("R9_HP", "R9_H"): "adición de P a H", ("R9_HP", "R9_P"): "adición de H a P",
              ("R9_H", "R9_PCT"): "histórico frente a razón", ("R9_HP", "R9_PCT"): "aditivo frente a razón"}
    ctl = tablas["contrastes_control"]
    assert len(ctl) == 16 and set(zip(ctl.modelo, ctl.referencia)) == set(labels)
    for _, c in ctl.iterrows():
        o = _scene(tablas, c.escenario)
        m = _indexed(ciencias["tabla_metricas"](o))
        per = {r: _indexed(ciencias["tabla_metricas"](q)) for r, q in o.groupby("repeticion")}
        assert labels[(c.modelo, c.referencia)] == c.contraste
        np.testing.assert_allclose(m.loc[c.modelo, c.metrica]-m.loc[c.referencia, c.metrica],
                                   c.delta_agrupado, atol=1e-12, rtol=0)
        assert sum(q.loc[c.modelo, c.metrica] < q.loc[c.referencia, c.metrica] for q in per.values()) == c.repeticiones_mejora


def test_metricas_por_municipio_zona_y_repeticion(ciencias, tablas):
    for name, key in [("municipios_control", "Municipio"), ("zonas_control", "zona"),
                      ("repeticiones_control", "repeticion")]:
        ctl = tablas[name]
        for _, r in ctl.iterrows():
            o = _scene(tablas, r.escenario)
            q = o.loc[o.modelo.eq(r.modelo) & o[key].eq(r[key])]
            m = ciencias["metricas"](q)
            for col in ["n_oof", "n_parcelas", "RMSE", "MAE", "R2"]:
                # La implementación histórica solo comprobaba SST>0; un único
                # rendimiento repetido puede dejar residuos de redondeo ~1e-29.
                # R² no está definido en esa población, no se reproduce ese ruido.
                if col == "R2" and np.sum((q.observado-q.observado.mean())**2) <= 1e-12:
                    assert np.isnan(m[col])
                    continue
                np.testing.assert_allclose(m[col], r[col], atol=1e-12, rtol=0, equal_nan=True)
    o = _scene(tablas, "municipio_visto")
    assert o.loc[o.modelo.eq("MUN") & o.zona.eq("Chignahuapan"), "ID_POLIGONO"].nunique() == 71
    assert o.loc[o.modelo.eq("MUN") & o.zona.eq("resto"), "ID_POLIGONO"].nunique() == 64


def test_soporte_59_metadatos_y_caso_nanacamilpa_no_evaluado(ciencias, tablas):
    x, e = tablas["variables_fuente"], tablas["externas"]
    oldx, olde = x.copy(deep=True), e.copy(deep=True)
    s = ciencias["soporte_entrega"](x, e).set_index("Municipio").sort_index()
    ctl = tablas["soporte_control"].set_index("Municipio").sort_index()
    assert len(s) == 9 and s.n_etiquetadas.sum() == 138 and s.n_ocultas.sum() == 59
    for c in ctl.columns:
        if c == "nota":
            np.testing.assert_array_equal(s[c].fillna(""), ctl[c].fillna(""))
        elif ctl[c].dtype == bool:
            np.testing.assert_array_equal(s[c], ctl[c])
        else:
            np.testing.assert_allclose(s[c], ctl[c], atol=1e-12, rtol=0)
    pd.testing.assert_frame_equal(x, oldx)
    pd.testing.assert_frame_equal(e, olde)
    n = s.loc["Nanacamilpa de Mariano Arista"]
    assert n.n_etiquetadas == n.n_ocultas == 1
    assert n.n_oof_municipio_visto == n.n_oof_train_una_etiqueta == 0
    assert n.caso_singleton_sin_validacion
    assert n.H_mm_fuera_rango_municipal == n.P_actual_mm_fuera_rango_municipal == n.A_pct_fuera_rango_municipal == 1
    local = x.loc[x.Municipio.eq("Nanacamilpa de Mariano Arista")].set_index("ID_POLIGONO")
    assert set(local.index) == {"AGC_048", "AGC_120"}
    assert local.loc["AGC_048", "celda_centroide"] != local.loc["AGC_120", "celda_centroide"]


def test_ganancias_sse_por_parcela_y_concentracion_denominador_bruto(tablas):
    ctl = tablas["deltas_control"]
    assert len(ctl) == 1104
    for (scene, model), q in ctl.groupby(["escenario", "modelo"]):
        o = _scene(tablas, scene)
        ref = o.loc[o.modelo.eq("MIX")].set_index(CLAVES).sort_index()
        cand = o.loc[o.modelo.eq(model)].set_index(CLAVES).sort_index()
        assert ref.index.equals(cand.index)
        gain = (ref.predicho-ref.observado)**2-(cand.predicho-cand.observado)**2
        sums = gain.groupby("ID_POLIGONO").sum()
        q = q.set_index("ID_POLIGONO").sort_index()
        np.testing.assert_allclose(q.ganancia_SSE_vs_MIX, sums.sort_index(), atol=1e-12, rtol=0)
        c = tablas["concentracion_control"].loc[lambda t: t.escenario.eq(scene) & t.modelo.eq(model)].iloc[0]
        positive = sums.clip(lower=0).sum()
        cell = q.groupby("celda_centroide").ganancia_SSE_vs_MIX.sum()
        positive_cells = cell.clip(lower=0).sum()
        np.testing.assert_allclose(c.ganancia_SSE_neta, sums.sum(), atol=1e-12, rtol=0)
        np.testing.assert_allclose(c.ganancia_SSE_bruta_positiva, positive, atol=1e-12, rtol=0)
        np.testing.assert_allclose(c.fraccion_mejora_bruta_top5_parcelas,
                                   sums.nlargest(5).clip(lower=0).sum()/positive if positive else np.nan,
                                   atol=1e-12, rtol=0, equal_nan=True)
        np.testing.assert_allclose(c.fraccion_mejora_bruta_top2_celdas_centroide,
                                   cell.nlargest(2).clip(lower=0).sum()/positive_cells if positive_cells else np.nan,
                                   atol=1e-12, rtol=0, equal_nan=True)
        assert c.n_parcelas_mejoran == (sums > 0).sum() and c.n_parcelas_empeoran == (sums < 0).sum()


def test_fechas_historicas_y_limites_presentes(notebook):
    prose = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split()).lower()
    for phrase in ["normal climatológica", "nanacamilpa", "exploratorio", "no equivale", "no modelo final"]:
        assert phrase in prose
    closure = _cell(notebook, "cierre").source
    assert "RESUMEN_EXP_05_JSON=" in closure and "allow_nan=False" in closure
    assign = next(n for n in ast.parse(closure).body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "resumen" for t in n.targets))
    constants = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(assign.value.keys, assign.value.values)
                 if isinstance(v, (ast.Constant, ast.List))}
    for key in ["ajustes_actuales", "predicciones_finales_generadas"]:
        assert constants[key] == 0
    for key in ["predicciones_recalculadas", "scores_interiores_recalculados", "intersecciones_recalculadas"]:
        assert constants[key] is False
    assert constants["variantes_adoptadas"] == []
