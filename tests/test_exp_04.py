"""EXP_04: aritmética visible y evaluación de resultados guardados, sin ajustes.

Reconstruir lluvia desde áreas registradas no vuelve a intersectar geometrías.
Verificar selecciones desde scores no vuelve a producir sus errores interiores.
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
CONFIG = "config/exp_04_lluvia_octubre.json"
BASE = "notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb"
BASE_SHA = "ca84ad2999bda26496848898a4e77385423e8a544699a1c2883ec28267457fc0"
CLAVES = ["repeticion", "pliegue", "ID_POLIGONO"]
GRID = ["baseline", .01, .1, 1., 10., 100.]
CANDIDATOS = ["J5_PCT", "J9_PCT", "R9_PCT", "R9_MM", "R9_RAW"]
MODELOS = ["GLOBAL", "MUN", "MIX", "G5", "R_B"] + CANDIDATOS
J5 = {"Chignahuapan": "Chignahuapan", "Singuilucan": "Singuilucan", "Almoloya": "Almoloya",
      "Calpulalpan": "Tlaxcala", "Nanacamilpa de Mariano Arista": "Tlaxcala",
      "Cuautepec de Hinojosa": "Otros_Hidalgo", "Emiliano Zapata": "Otros_Hidalgo",
      "Apan": "Otros_Hidalgo", "Tepeapulco": "Otros_Hidalgo"}
VISIBLE = ["insumos-visibles", "lluvia-visible", "ejemplo-area", "variables-visibles",
           "recetas-visibles", "parametros-visibles", "particiones-visibles", "seleccion-visible",
           "metricas-visibles", "regla-visible", "contrastes-visibles", "escenarios-visibles",
           "concentracion-visible", "sensibilidad-visible", "cierre"]


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _cell(nb, tag):
    found = [c for c in nb.cells if tag in c.metadata.get("tags", [])]
    assert len(found) == 1, f"Celda única requerida: {tag}"
    return found[0]


def _functions(nb, names, **extra):
    found = {}
    for c in nb.cells:
        if c.cell_type != "code":
            continue
        for node in ast.parse(c.source).body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                assert node.name not in found
                if node.name not in {"bytes_insumo", "leer_csv"}:
                    assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
                found[node.name] = copy.deepcopy(node)
    assert set(found) == set(names)
    module = ast.fix_missing_locations(ast.Module(body=list(found.values()), type_ignores=[]))
    ns = {"np": np, "pd": pd, "GRID": GRID.copy(), "MODELOS": MODELOS.copy(),
          "CANDIDATOS": CANDIDATOS.copy(), "base64": base64, "zlib": zlib,
          "hashlib": hashlib, "io": io, **extra}
    exec(compile(module, "<EXP_04:funciones-visibles>", "exec"), ns)
    return ns


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("exp04_generador_pruebas", ROOT / "scripts/construir_exp_04.py")
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
    return _functions(notebook, ["lluvia_ponderada", "variables_octubre", "seleccionar_alpha_guardado",
                                 "metricas", "tabla_metricas", "regla_avance"])


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
    w = pd.DataFrame({"ID_POLIGONO": ["A", "A"], "fila": [0, 0], "col": [0, 1],
                      "area_m2_utm14n": [3., 7.]})
    p = pd.DataFrame([{"anio": a, "fila": 0, "col": c, "P_pixel_mm": v}
                      for a in (2022, 2023, 2024, 2025) for c, v in [(0, 10.), (1, 20.)]])
    area = pd.DataFrame({"ID_POLIGONO": ["A"], "area_parcela_m2": [10.]})
    return w, p, area


def _areas(tablas):
    return tablas["lluvia_control"][["ID_POLIGONO", "area_parcela_m2"]].drop_duplicates()


def _seen(tablas):
    groups = tablas["grupos"].set_index("ID_POLIGONO")
    rows = []
    for _, q in tablas["externas"].groupby(["repeticion", "pliegue"]):
        known = set(q.loc[q.rol.eq("entrenamiento"), "ID_POLIGONO"].map(groups.Municipio))
        v = q.loc[q.rol.eq("validacion"), CLAVES].copy()
        v["municipio_visto"] = v.ID_POLIGONO.map(groups.Municipio).isin(known)
        rows.append(v)
    return pd.concat(rows, ignore_index=True)


def test_builder_celdas_limpias_metadata_y_determinismo(builder, notebook, config):
    nbformat.validate(notebook)
    assert builder.huella(b"V2") == _sha(b"V2")
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == [] and "execution" not in c.metadata
    reg = notebook.metadata.agrocebada
    assert reg.id == "EXP_04" and reg.modo == "lector_retrospectivo_sin_ajustes"
    assert reg.fecha_original == "2026-10-01" and reg.fecha_adaptacion == "2026-10-08"
    assert reg.ajustes_actuales == 0 and reg.colab_real_probado is False
    assert reg.recorte_pixeles == config["recorte_pixeles"]
    assert set(reg.dependencias_requeridas) == {"numpy", "pandas", "matplotlib"}
    new = builder.construir()
    assert [(c.id, c.cell_type, c.source) for c in new.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells]


def test_soporte_copiado_sin_dependencia_runtime_ni_cambio_anterior(builder, notebook):
    assert builder.BASE_SHA256 == BASE_SHA == _sha((ROOT / BASE).read_bytes())
    base = nbformat.read(ROOT / BASE, as_version=4)
    for tag in ("soporte-colab", "preparar-colab", "entorno", "particiones-visibles"):
        assert _cell(notebook, tag).source == _cell(base, tag).source
    assert notebook.metadata.agrocebada.fuentes_sha256[BASE] == BASE_SHA
    assert notebook.metadata.agrocebada.soporte_sha256 == base.metadata.agrocebada.soporte_sha256
    assert notebook.metadata.agrocebada.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())


def test_solo_dos_celdas_tecnicas_plegadas(notebook):
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


def test_no_ajustes_descargas_activas_ni_lecturas_locales_runtime(notebook):
    fit = {"fit", "fit_transform", "fit_predict", "predict", "predict_proba", "partial_fit",
           "GridSearchCV", "RandomizedSearchCV"}
    download = {"download", "obtener_dataset", "urlopen", "urlretrieve"}
    for c in notebook.cells:
        if c.cell_type != "code":
            continue
        support = "soporte-colab" in c.metadata.get("tags", [])
        tree = ast.parse(c.source)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                name = n.func.attr if isinstance(n.func, ast.Attribute) else (
                    n.func.id if isinstance(n.func, ast.Name) else None)
                assert name not in fit
                if not support:
                    assert name not in download | {"open", "read_bytes", "read_text", "read_json", "read_pickle"}
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
                    assert name not in download


def test_22_contratos_exactos_y_precision_round_trip(notebook, config, insumos):
    records = _records(notebook)
    assert len(records) == len(config["insumos"]) == len(insumos) == 22
    assert set(records) == set(config["insumos"]) == set(insumos)
    ns = _functions(notebook, ["bytes_insumo", "leer_csv"], INSUMOS_INCRUSTADOS=records)
    for k, c in config["insumos"].items():
        b = insumos[k]["contenido"]
        assert type(c["bytes"]) is int and 0 < c["bytes"] <= 2*1024*1024
        assert b == (ROOT / c["ruta_local"]).read_bytes()
        assert len(b) == c["bytes"] and _sha(b) == c["sha256"]
        assert ns["bytes_insumo"](k, c["uso"]) == b
        if c["ruta_local"].endswith(".csv"):
            expected = pd.read_csv(io.BytesIO(b), encoding="utf-8-sig", float_precision="round_trip")
            pd.testing.assert_frame_equal(ns["leer_csv"](k, c["uso"]), expected)
    assert 'float_precision="round_trip"' in _cell(notebook, "insumos-tecnicos").source


def test_recorte_actual_identifica_originales_y_no_se_confunde_con_pre_registro(config, tablas):
    r = config["recorte_pixeles"]
    assert r["fecha_recorte"] == "2026-10-08" and r["filas"] == 116 and r["celdas"] == 29
    assert r["sha256_recorte"] == config["insumos"]["pixeles"]["sha256"]
    assert set(r["fuentes_tif"]) == {"2022", "2023", "2024", "2025"}
    for a, s in r["fuentes_tif"].items():
        q = tablas["pixeles"].loc[tablas["pixeles"].anio.eq(int(a))]
        ref = tablas["lluvia_control"].loc[tablas["lluvia_control"].anio.eq(int(a))]
        assert len(q) == 29 and ref.sha256_tif.eq(s["sha256_tif"]).all()
        assert s["sha256_tif"] != r["sha256_recorte"]
        assert s["miembro_original"].endswith(f"PREC_{a}_10.tif")
    assert r["malla"]["epsg"] == 4326 and r["malla"]["nodata"] == -9999


@pytest.mark.parametrize("change", ["contenido", "bytes", "sha", "ausente"])
def test_loader_rechaza_fixture_modificada(builder, tmp_path, change):
    b = b"dato\n1\n"
    c = {"ruta_local": "dato.csv", "bytes": len(b), "sha256": _sha(b), "uso": "prueba"}
    if change == "bytes":
        c["bytes"] += 1
    elif change == "sha":
        c["sha256"] = "0"*64
    (tmp_path / "config").mkdir()
    (tmp_path / CONFIG).write_text(json.dumps({"insumos": {"dato": c}}), encoding="utf-8")
    if change != "ausente":
        (tmp_path / "dato.csv").write_bytes(b"dato\n2\n" if change == "contenido" else b)
    with pytest.raises((ValueError, FileNotFoundError)):
        builder.cargar_insumos(tmp_path)


@pytest.mark.parametrize("change", ["uso", "sha", "bytes_menos", "bytes_mas", "bytes_cero",
    "bytes_negativo", "bytes_bool", "bytes_float", "bytes_limite", "base64", "base64_limite",
    "truncado", "concatenado", "sobrante"])
def test_decoder_acotado_rechaza_corrupcion(notebook, change):
    b = b"dato\n1\n"
    compressed = zlib.compress(b)
    r = {"uso": "prueba", "bytes": len(b), "sha256": _sha(b),
         "bytes_zlib_base64": base64.b64encode(compressed).decode()}
    if change == "uso":
        r["uso"] = "otro"
    elif change == "sha":
        r["sha256"] = "0"*64
    elif change.startswith("bytes_"):
        r["bytes"] = {"bytes_menos": len(b)-1, "bytes_mas": len(b)+1, "bytes_cero": 0,
                      "bytes_negativo": -1, "bytes_bool": True, "bytes_float": float(len(b)),
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


def test_ponderacion_manual_3_7_y_orden_independiente(ciencias):
    w, p, area = _toy()
    out = ciencias["lluvia_ponderada"](w, p, area)
    np.testing.assert_array_equal(out.P_mm, [17.]*4)
    np.testing.assert_array_equal(out.cobertura, [1.]*4)
    assert out.estado.eq("ok").all() and out.n_celdas.eq(2).all()
    perm = ciencias["lluvia_ponderada"](w.iloc[::-1], p.sample(frac=1, random_state=7), area)
    pd.testing.assert_frame_equal(out, perm)


def test_campo_constante_y_parcela_de_una_celda(ciencias):
    w, p, area = _toy()
    p["P_pixel_mm"] = 123.5
    out = ciencias["lluvia_ponderada"](w, p, area)
    assert out.P_mm.eq(123.5).all()
    w = w.iloc[:1].copy()
    p = p.loc[p.col.eq(0)]
    area["area_parcela_m2"] = 3.
    out = ciencias["lluvia_ponderada"](w, p, area)
    assert out.n_celdas.eq(1).all() and out.P_mm.eq(123.5).all()


@pytest.mark.parametrize("invalid", [-9999., np.nan, np.inf])
def test_nodata_parcial_detiene_por_area_total_no_renormaliza_cobertura(ciencias, invalid):
    w, p, area = _toy()
    p.loc[p.col.eq(1), "P_pixel_mm"] = invalid
    out = ciencias["lluvia_ponderada"](w, p, area)
    assert out.P_mm.isna().all() and out.estado.eq("cobertura_insuficiente").all()
    np.testing.assert_array_equal(out.cobertura, [.3]*4)
    assert out.n_celdas_validas.eq(1).all()


def test_sin_dato_ninguna_celda_y_no_imputacion(ciencias):
    w, p, area = _toy()
    p["P_pixel_mm"] = -9999.
    out = ciencias["lluvia_ponderada"](w, p, area)
    assert out.estado.eq("sin_dato").all() and out.P_mm.isna().all()
    assert out.cobertura.eq(0).all() and out.n_celdas_validas.eq(0).all()


@pytest.mark.parametrize("coverage,ok", [(.99, True), (.990001, True), (.989999, False), (1.0000035, True)])
def test_umbral_99_inclusivo_y_cobertura_sin_recorte(ciencias, coverage, ok):
    w, p, area = _toy()
    area["area_parcela_m2"] = 10/coverage
    out = ciencias["lluvia_ponderada"](w, p, area)
    np.testing.assert_allclose(out.cobertura, coverage, atol=1e-15, rtol=0)
    assert out.estado.eq("ok").all() == ok
    assert out.P_mm.notna().all() == ok


@pytest.mark.parametrize("change", ["peso_columna", "pixel_columna", "area_columna", "peso_vacio",
    "id_vacio", "peso_duplicado", "pixel_duplicado", "fila_fraccional", "col_negativa", "anio_fraccional",
    "anio_ausente", "pixel_ausente", "pixel_extra", "area_duplicada", "area_id_ajeno", "area_cero",
    "area_nan", "pieza_cero", "pieza_infinita"])
def test_ponderacion_rechaza_datos_ambiguos_o_incompletos(ciencias, change):
    w, p, a = _toy()
    if change == "peso_columna":
        w = w.drop(columns="fila")
    elif change == "pixel_columna":
        p = p.drop(columns="P_pixel_mm")
    elif change == "area_columna":
        a = a.drop(columns="area_parcela_m2")
    elif change == "peso_vacio":
        w = w.iloc[:0]
    elif change == "id_vacio":
        w.loc[0, "ID_POLIGONO"] = None
    elif change == "peso_duplicado":
        w = pd.concat([w, w.iloc[:1]], ignore_index=True)
    elif change == "pixel_duplicado":
        p = pd.concat([p, p.iloc[:1]], ignore_index=True)
    elif change == "fila_fraccional":
        w = w.astype({"fila": float})
        w.loc[0, "fila"] = .5
    elif change == "col_negativa":
        p.loc[0, "col"] = -1
    elif change == "anio_fraccional":
        p = p.astype({"anio": float})
        p.loc[0, "anio"] = 2022.5
    elif change == "anio_ausente":
        p = p.loc[p.anio.ne(2022)]
    elif change == "pixel_ausente":
        p = p.iloc[1:]
    elif change == "pixel_extra":
        p = pd.concat([p, p.iloc[:1].assign(col=2)], ignore_index=True)
    elif change == "area_duplicada":
        a = pd.concat([a, a], ignore_index=True)
    elif change == "area_id_ajeno":
        a.loc[0, "ID_POLIGONO"] = "B"
    elif change.startswith("area_"):
        a.loc[0, "area_parcela_m2"] = 0 if change == "area_cero" else np.nan
    elif change.startswith("pieza_"):
        w.loc[0, "area_m2_utm14n"] = 0 if change == "pieza_cero" else np.inf
    with pytest.raises(ValueError):
        ciencias["lluvia_ponderada"](w, p, a)


def test_788_lluvias_reales_reconstruidas_desde_116_pixeles_y_230_areas(ciencias, tablas):
    w, p = tablas["pesos"], tablas["pixeles"]
    assert len(w) == 230 and len(p) == 116 and w.ID_POLIGONO.nunique() == 197
    assert len(w[["fila", "col"]].drop_duplicates()) == 29
    assert w.groupby("ID_POLIGONO").size().value_counts().to_dict() == {1: 166, 2: 29, 3: 2}
    out = ciencias["lluvia_ponderada"](w, p, _areas(tablas)).set_index(["ID_POLIGONO", "anio"])
    ctl = tablas["lluvia_control"].set_index(["ID_POLIGONO", "anio"])
    assert len(out) == 788 and out.index.equals(ctl.index)
    for c in ("P_mm", "cobertura", "n_celdas", "n_celdas_validas"):
        np.testing.assert_allclose(out[c], ctl[c], atol=1e-12, rtol=0)
    assert out.estado.eq("ok").all() and out.cobertura.ge(.99).all()
    assert out.cobertura.max() > 1 and out.cobertura.min() < 1


def test_variables_manuales_y_h_umbral_inclusivo(ciencias):
    t = pd.DataFrame({"ID_POLIGONO": ["A"]*4, "anio": [2022, 2023, 2024, 2025],
                      "P_mm": [1., 1., 1., 2.], "estado": ["ok"]*4})
    v = ciencias["variables_octubre"](t)
    assert v.loc["A", "H_mm"] == 1 and v.loc["A", "A_mm"] == 1
    assert v.loc["A", "A_pct"] == 100 and v.loc["A", "P_actual_mm"] == 2


@pytest.mark.parametrize("change", ["vacio", "duplicado", "estado", "anio_falta", "parcela_anio_falta",
                                    "infinito", "nan", "h_menor", "columna"])
def test_variables_no_sustituyen_anos_ni_referencias_invalidas(ciencias, change):
    t = pd.DataFrame({"ID_POLIGONO": ["A"]*4, "anio": [2022, 2023, 2024, 2025],
                      "P_mm": [10., 20., 30., 40.], "estado": ["ok"]*4})
    if change == "vacio":
        t = t.iloc[:0]
    elif change == "duplicado":
        t = pd.concat([t, t.iloc[:1]], ignore_index=True)
    elif change == "estado":
        t.loc[0, "estado"] = "sin_dato"
    elif change == "anio_falta":
        t = t.iloc[1:]
    elif change == "parcela_anio_falta":
        t = pd.concat([t, t.iloc[:1].assign(ID_POLIGONO="B")], ignore_index=True)
    elif change in {"infinito", "nan"}:
        t.loc[0, "P_mm"] = np.inf if change == "infinito" else np.nan
    elif change == "h_menor":
        t.loc[:2, "P_mm"] = .99
    elif change == "columna":
        t = t.drop(columns="estado")
    with pytest.raises(ValueError):
        ciencias["variables_octubre"](t)


def test_197_formulas_contra_control_y_ejemplos(ciencias, tablas):
    rain = ciencias["lluvia_ponderada"](tablas["pesos"], tablas["pixeles"], _areas(tablas))
    v = ciencias["variables_octubre"](rain)
    ctl = tablas["variables_control"].set_index("ID_POLIGONO")
    assert len(v) == 197 and v.index.equals(ctl.index)
    np.testing.assert_allclose(v, ctl[v.columns], atol=1e-12, rtol=0)
    np.testing.assert_allclose(v.loc["AGC_001", ["H_mm", "A_mm", "A_pct"]],
                               [72.25919596354167, 3.375912984212235, 4.671949278145234], atol=1e-12, rtol=0)
    assert v.H_mm.ge(1).all() and v.A_pct.gt(0).all()


def test_catalogo_etiquetas_aparte_59_faltantes_y_j5_fijo(tablas):
    c, g = tablas["catalogo"], tablas["grupos"]
    assert len(c) == len(g) == 197 and c.ID_POLIGONO.is_unique and g.ID_POLIGONO.is_unique
    assert set(c.ID_POLIGONO) == set(g.ID_POLIGONO)
    assert c.RENDIMIENTO_T_HA.notna().equals(c.CONJUNTO.eq("ENTRENAMIENTO"))
    assert c.RENDIMIENTO_T_HA.notna().sum() == 138 and c.RENDIMIENTO_T_HA.isna().sum() == 59
    assert not any("rendimiento" in k.lower() for k in g.columns)
    np.testing.assert_array_equal(g.Municipio.map(J5), g.grupo_J5)
    assert g.Municipio.nunique() == 9 and g.grupo_J5.nunique() == 5
    train = g.loc[g.CONJUNTO.eq("ENTRENAMIENTO")].groupby("Municipio").size()
    assert set(train.index[train.eq(1)]) == {"Apan", "Nanacamilpa de Mariano Arista", "Tepeapulco"}
    assert set(g.loc[g.CONJUNTO.eq("PREDICCION"), "Municipio"]) <= set(train.index)
    assert g.set_index("ID_POLIGONO").loc["AGC_120", "CONJUNTO"] == "PREDICCION"


@pytest.mark.parametrize("scores,expected", [([1, 2, 3, 4, 5, 6], "baseline"),
    ([6, 1, 2, 3, 4, 5], .01), ([6, 2, 1, 1, 1, 1], 100.),
    ([1, 1, 1, 1, 1, 1], "baseline"), ([2, 1, 1+5e-13, 2, 2, 2], .1)])
def test_selector_empates_baseline_luego_alpha_mayor(ciencias, scores, expected):
    assert ciencias["seleccionar_alpha_guardado"](scores) == expected


@pytest.mark.parametrize("scores", [[], [1]*5, [1]*7, [[1]*6], [1, 1, 1, 1, 1, np.inf],
                                    [1, 1, 1, 1, 1, np.nan], [1, 1, 1, 1, 1, -1]])
def test_selector_exige_seis_scores_finitos_no_negativos(ciencias, scores):
    with pytest.raises(ValueError):
        ciencias["seleccionar_alpha_guardado"](scores)


def test_150_decisiones_desde_900_scores_y_32_baseline_raw(ciencias, tablas):
    s, params = tablas["seleccion"], tablas["parametros"]
    assert len(s) == 900 and len(params) == 250
    counts = {m: 0 for m in ["R9_PCT", "R9_MM", "R9_RAW"]}
    baselines = dict.fromkeys(counts, 0)
    for (m, r, f), q in s.groupby(["modelo", "repeticion", "pliegue"]):
        q = q.copy()
        q["key"] = q.alpha.map(lambda v: "baseline" if v == "baseline" else float(v))
        assert len(q) == 6 and set(q.key) == set(GRID)
        chosen = ciencias["seleccionar_alpha_guardado"](q.set_index("key").loc[GRID, "rmse_interior"])
        elected = q.loc[q.elegido]
        assert len(elected) == 1 and elected.key.iloc[0] == chosen
        p = params.loc[params.modelo.eq(m) & params.repeticion.eq(r) & params.pliegue.eq(f)]
        assert len(p) == 1
        value = p.alpha_elegido.iloc[0]
        assert chosen == (value if value == "baseline" else float(value))
        counts[m] += 1
        baselines[m] += chosen == "baseline"
    assert counts == {"R9_PCT": 50, "R9_MM": 50, "R9_RAW": 50}
    assert baselines["R9_RAW"] == 32


def test_rb_50_decisiones_250_scores_conciliadas_con_v1(tablas):
    a = tablas["rb_seleccion"]
    b = tablas["v1_seleccion"].query("modelo == 'R_B'")
    merged = a.merge(b, on=["repeticion", "pliegue"], validate="one_to_one")
    assert len(merged) == 50
    scores = 0
    for _, r in merged.iterrows():
        v = json.loads(r.scores_internos_x)
        old = json.loads(r.scores_internos_y)
        assert len(v) == len(old) == 5
        np.testing.assert_allclose(v, old, atol=1e-8, rtol=0)
        pos = next(i for i, s in enumerate(v) if s <= min(v)+1e-12)
        assert [100., 10., 1., .1, .01][pos] == r.alpha == json.loads(r.parametros)["alpha"]
        scores += len(v)
    assert scores == 250


def test_presupuesto_y_parametros_guardados_no_estimados(insumos, tablas):
    reg = json.loads(insumos["registro_ejecucion"]["contenido"])
    assert reg["presupuesto"] == {"evaluaciones_internas": 3600, "evaluaciones_baseline": 600,
                                 "ajustes_ridge_internos": 3000, "reajustes_exteriores": 250}
    p = tablas["parametros"]
    assert len(p) == 250 and not p.duplicated(["modelo", "repeticion", "pliegue"]).any()
    assert set(p.modelo) == set(CANDIDATOS)
    assert np.isfinite(p[["beta", "escala"]]).all().all() and p.escala.gt(0).all()
    assert not p.degenerada.any()


def test_particiones_50_exteriores_200_interiores_y_contencion(tablas):
    e, inner = tablas["externas"], tablas["internas"]
    ids = set(tablas["catalogo"].loc[tablas["catalogo"].CONJUNTO.eq("ENTRENAMIENTO"), "ID_POLIGONO"])
    assert len(e.groupby(["repeticion", "pliegue"])) == 50
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
    valid = e.loc[e.rol.eq("validacion")]
    assert len(valid) == 1380 and valid.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()


def test_13800_oof_mismas_claves_etiquetas_y_controles_v1(tablas):
    o = tablas["oof"]
    g = tablas["grupos"].set_index("ID_POLIGONO")
    y = tablas["catalogo"].set_index("ID_POLIGONO").RENDIMIENTO_T_HA
    keys = set(map(tuple, tablas["externas"].loc[tablas["externas"].rol.eq("validacion"), CLAVES].to_numpy()))
    assert len(o) == 13800 and set(o.modelo) == set(MODELOS)
    assert not o.duplicated(["modelo"]+CLAVES).any()
    for _, q in o.groupby("modelo"):
        assert len(q) == 1380 and q.ID_POLIGONO.nunique() == 138
        assert set(map(tuple, q[CLAVES].to_numpy())) == keys and np.isfinite(q.predicho).all()
        np.testing.assert_array_equal(q.observado, q.ID_POLIGONO.map(y))
        for c, source in [("Municipio", "Municipio"), ("grupo_J5", "grupo_J5"), ("celda", "celda_centroide")]:
            np.testing.assert_array_equal(q[c], q.ID_POLIGONO.map(g[source]))
        np.testing.assert_array_equal(q.zona, np.where(q.Municipio.eq("Chignahuapan"), "Chignahuapan", "Resto"))
    for m in ["GLOBAL", "MUN", "MIX", "R_B"]:
        a = o.loc[o.modelo.eq(m)].set_index(CLAVES).sort_index()
        b = tablas["v1_oof"].loc[tablas["v1_oof"].modelo.eq(m)].set_index(CLAVES).sort_index()
        assert a.index.equals(b.index)
        np.testing.assert_allclose(a.predicho, b.predicho, atol=1e-8, rtol=0)


def test_metricas_manuales_agrupadas_y_r2_estandar(ciencias):
    t = pd.DataFrame({"observado": [1., 2., 3.], "predicho": [1., 2., 5.]})
    m = ciencias["metricas"](t)
    np.testing.assert_allclose(m, [np.sqrt(4/3), 2/3, -1.], atol=1e-15, rtol=0)
    assert np.isnan(ciencias["metricas"](t.assign(observado=1)).R2)


@pytest.mark.parametrize("change", ["vacio", "y_nan", "p_inf"])
def test_metricas_rechazan_no_finitos_y_vacio(ciencias, change):
    t = pd.DataFrame({"observado": [1., 2.], "predicho": [1., 3.]})
    if change == "vacio":
        t = t.iloc[:0]
    elif change == "y_nan":
        t.loc[0, "observado"] = np.nan
    else:
        t.loc[0, "predicho"] = np.inf
    with pytest.raises(ValueError):
        ciencias["metricas"](t)


def test_metricas_reales_y_regla_full138_conservan_j5(ciencias, tablas):
    metrics = ciencias["tabla_metricas"](tablas["oof"])
    ctl = tablas["metricas_control"].set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(metrics, ctl[["RMSE", "MAE", "R2"]], atol=1e-12, rtol=0)
    rule = ciencias["regla_avance"](tablas["oof"])
    assert rule.index[rule.cumple].tolist() == ["J5_PCT"]
    assert rule.loc["J5_PCT", "reps_RMSE_menor_MIX"] == 10
    assert rule.loc["J5_PCT", "reps_MAE_menor_o_igual_MUN"] == 10
    assert metrics.loc["R9_PCT", "RMSE"] < metrics.loc["R9_MM", "RMSE"]
    assert metrics.loc["R9_PCT", "MAE"] > metrics.loc["R9_MM", "MAE"]
    np.testing.assert_allclose(metrics.loc["J5_PCT", ["RMSE", "MAE"]], [.4797, .3291], atol=5e-5, rtol=0)


def test_regla_incompleta_no_adopta_criterio_silencioso(ciencias, tablas):
    with pytest.raises(ValueError):
        ciencias["regla_avance"](tablas["oof"].loc[tablas["oof"].repeticion.ne(9)])


def test_seen135_mask_metadata_posterior_sin_reentrenar(ciencias, tablas):
    mask = _seen(tablas)
    assert len(mask) == 1380 and mask.municipio_visto.sum() == 1350
    assert set(mask.loc[~mask.municipio_visto, "ID_POLIGONO"]) == {"AGC_164", "AGC_048", "AGC_047"}
    merged = tablas["oof"].merge(mask, on=CLAVES, validate="many_to_one")
    seen = merged.loc[merged.municipio_visto]
    assert len(seen) == 13500 and seen.ID_POLIGONO.nunique() == 135
    metrics = ciencias["tabla_metricas"](seen)
    c = tablas["metricas_escenarios_control"]
    c = c.loc[c.escenario.eq("solo municipio visto (posterior)")].set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(metrics, c[["RMSE", "MAE", "R2"]], atol=1e-12, rtol=0)
    rule = ciencias["regla_avance"](seen)
    assert not rule.cumple.any()
    assert rule.loc["J5_PCT", "reps_RMSE_menor_MIX"] == 8
    assert rule.loc["J5_PCT", "reps_MAE_menor_o_igual_MUN"] == 0
    assert metrics.loc["J5_PCT", "RMSE"] < metrics.loc["MIX", "RMSE"]
    assert metrics.loc["J5_PCT", "MAE"] > metrics.loc["MUN", "MAE"]


def test_no_vistos_de_candidatos_coinciden_con_roles_no_con_errores(tablas):
    joined = tablas["oof"].merge(_seen(tablas), on=CLAVES, validate="many_to_one")
    for m in ["J9_PCT", "R9_PCT", "R9_MM", "R9_RAW"]:
        q = joined.loc[joined.modelo.eq(m)]
        np.testing.assert_array_equal(q.grupo_no_visto, ~q.municipio_visto)
        assert q.grupo_no_visto.sum() == 30
    assert not joined.loc[joined.modelo.eq("J5_PCT"), "grupo_no_visto"].any()


def test_pocos_pixeles_y_concentracion_no_equivalen_a_n_efectiva(tablas):
    o = tablas["oof"]
    a = o.loc[o.modelo.eq("J5_PCT")].set_index(CLAVES).sort_index()
    b = o.loc[o.modelo.eq("MIX")].set_index(CLAVES).sort_index()
    delta = (a.predicho-a.observado)**2 - (b.predicho-b.observado)**2
    per = delta.groupby("ID_POLIGONO").sum()
    net = per.sum()
    assert net < 0 and per.loc["AGC_164"] > 0
    assert net-per.nsmallest(5).sum() > 0
    np.testing.assert_allclose(per.loc[["AGC_164", "AGC_048", "AGC_047"]].sum()/net, .5849, atol=5e-5, rtol=0)
    ids = set(a.index.get_level_values("ID_POLIGONO"))
    groups = tablas["grupos"].set_index("ID_POLIGONO")
    w = tablas["pesos"]
    assert groups.loc[list(ids), "celda_centroide"].nunique() == 23
    assert len(w.loc[w.ID_POLIGONO.isin(ids), ["fila", "col"]].drop_duplicates()) == 27
    assert len(w[["fila", "col"]].drop_duplicates()) == 29


def test_sensibilidad_previa_retirar127171_solo_al_evaluar(ciencias, tablas):
    o = tablas["oof"]
    q = o.loc[~o.ID_POLIGONO.isin(["AGC_127", "AGC_171"])]
    assert len(q) == 13600 and q.ID_POLIGONO.nunique() == 136
    metrics = ciencias["tabla_metricas"](q)
    ctl = tablas["sensibilidad_control"].set_index("modelo").loc[MODELOS]
    np.testing.assert_allclose(metrics, ctl[["RMSE", "MAE", "R2"]], atol=1e-12, rtol=0)
    assert len(o) == 13800 and o.ID_POLIGONO.nunique() == 138


def test_resumen_bandera_exacta_y_limites_explicitados(notebook):
    assign = next(n for n in ast.parse(_cell(notebook, "cierre").source).body
                  if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "resumen" for t in n.targets))
    constants = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(assign.value.keys, assign.value.values)
                 if isinstance(v, (ast.Constant, ast.List))}
    expected = {"id": "EXP_04", "modo": "lector_retrospectivo_sin_ajustes", "parcelas": 197, "etiquetas": 138,
                "piezas_guardadas": 230, "pixeles_derivados": 116, "lluvias_recalculadas": 788,
                "procedimientos": 10, "oof_por_procedimiento": 1380, "oof_total": 13800,
                "particiones_externas": 50, "particiones_internas": 200,
                "decisiones_verificadas": 200, "scores_guardados_verificados": 1150,
                "ajustes_actuales": 0, "predicciones_finales_generadas": 0, "poblacion": "FULL138",
                "scores_interiores_recalculados": False, "predicciones_recalculadas": False,
                "intersecciones_recalculadas": False, "variables_recalculadas": True, "metricas_recalculadas": True,
                "candidato_con_reservas": ["J5_PCT"], "variantes_adoptadas": [],
                "diagnostico_posterior": "SEEN135", "oof_seen_por_procedimiento": 1350,
                "fecha_original": "2026-10-01", "fecha_adaptacion": "2026-10-08"}
    assert constants == expected
    source = _cell(notebook, "cierre").source
    assert "RESUMEN_EXP_04_JSON=" in source and "allow_nan=False" in source
    prose = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split())
    for phrase in ["no recalculamos geometrías", "no de una prueba independiente", "no equivale a las 59",
                   "no es modelo final", "No borra", "normal climatológica"]:
        if phrase == "No borra":
            assert "no borra" in prose
        else:
            assert phrase in prose
