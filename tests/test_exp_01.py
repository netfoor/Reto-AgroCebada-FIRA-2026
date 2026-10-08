"""EXP_01: contratos y aritmética visible, sin kernel ni ajustes de modelos.

Solo se construye el NotebookNode y se extraen por AST funciones aritméticas.
Los fixtures reales son resultados históricos: validarlos y volver a puntuar
sus errores no equivale a reproducir entrenamiento o predicciones Ridge.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import io
import json
import re
import shutil
import sys
from collections.abc import Mapping
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
ALPHAS = (.01, .1, 1., 10., 100.)
CLAVES = ["modelo", "repeticion", "pliegue", "ID_POLIGONO"]
VISIBLES = ("historia-visible", "diseno-visible", "seleccion-visible", "oof-validacion",
            "metricas-visibles", "sensibilidad-visible", "cierre")


def _sha(bruto):
    return hashlib.sha256(bruto).hexdigest()


@pytest.fixture(scope="module")
def builder():
    ruta = ROOT / "scripts/construir_exp_01.py"
    assert ruta.is_file(), "Falta scripts/construir_exp_01.py"
    spec = importlib.util.spec_from_file_location("exp01_generador_pruebas", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def config():
    return json.loads((ROOT / "config/exp_01_bloques.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def insumos(builder):
    return builder.cargar_insumos(ROOT)


@pytest.fixture(scope="module")
def notebook(builder, config):
    protegidos = [ROOT / "scripts/colab_soporte.py", ROOT / "requirements-colab-auditoria.txt"]
    protegidos += list((ROOT / "scripts").glob("construir_notebook_0[123].py"))
    protegidos += [ROOT / c["ruta_local"] for c in config["insumos"].values()]
    antes = {p: p.read_bytes() for p in protegidos}
    nb = builder.construir(ROOT)
    assert all(p.read_bytes() == contenido for p, contenido in antes.items())
    return nb


def _celda(nb, tag):
    celdas = [c for c in nb.cells if tag in c.metadata.get("tags", [])]
    assert len(celdas) == 1, f"Celda única requerida: {tag}"
    return celdas[0]


def _funcion(nb, nombre):
    definiciones = []
    for c in nb.cells:
        if c.cell_type == "code":
            for n in ast.parse(c.source).body:
                if isinstance(n, ast.FunctionDef) and n.name == nombre:
                    assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
                    definiciones.append(n)
    assert len(definiciones) == 1, f"Función visible única requerida: {nombre}"
    arbol = ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(definiciones[0])], type_ignores=[]))
    ns = {"np": np, "pd": pd, "ALPHAS": ALPHAS}
    exec(compile(arbol, f"<EXP_01:{nombre}>", "exec"), ns)
    return ns[nombre]


def _metricas(r):
    if isinstance(r, pd.DataFrame):
        assert len(r) == 1
        r = r.iloc[0]
    if isinstance(r, pd.Series):
        r = r.to_dict()
    if not isinstance(r, Mapping):
        r = dict(zip(("RMSE", "MAE", "R2"), r, strict=True))
    return {k: float(r[k]) for k in ("RMSE", "MAE", "R2")}


def _bruto(reg):
    b = reg["contenido"]
    assert isinstance(b, (bytes, str))
    return b.encode("utf-8") if isinstance(b, str) else b


def _csvs(insumos):
    tablas = []
    for reg in insumos.values():
        try:
            tablas.append(pd.read_csv(io.BytesIO(_bruto(reg)), encoding="utf-8-sig"))
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError):
            pass
    return tablas


def _tabla(tablas, condicion, descripcion):
    candidatas = [d for d in tablas if condicion(d)]
    assert len(candidatas) == 1, f"Insumo único requerido: {descripcion}"
    return candidatas[0]


def test_api_notebook_valido_metadatos_y_construccion_determinista(builder, notebook):
    assert builder.REQUERIDOS == ("numpy", "pandas", "matplotlib")
    assert tuple(builder.ALPHAS) == ALPHAS
    assert all(callable(getattr(builder, n)) for n in ("construir", "cargar_insumos", "derivar_soporte"))
    nbformat.validate(notebook)
    assert notebook.cells and len({c.id for c in notebook.cells}) == len(notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == []
    reg = notebook.metadata.agrocebada
    assert reg.id == "EXP_01" and reg.modo == "lector_retrospectivo_sin_ajustes"
    assert reg.ajustes_actuales == 0 and reg.fecha_original == "2026-09-21"
    assert reg.fecha_adaptacion == "2026-10-08"
    nuevo = builder.construir()
    assert [(c.id, c.cell_type, c.source) for c in nuevo.cells] == [
        (c.id, c.cell_type, c.source) for c in notebook.cells
    ]


def test_solo_dos_tecnicas_plegadas_y_operaciones_visibles(notebook):
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
    for tag in ("preparar-colab",) + VISIBLES:
        c = _celda(notebook, tag)
        assert c.cell_type == "code" and c.metadata.get("cellView") != "form"
        assert not c.metadata.get("jupyter", {}).get("source_hidden", False)
    for tag in VISIBLES[:-1]:
        assert "display(" in _celda(notebook, tag).source


def test_no_entrenamiento_prediccion_ni_importaciones_sklearn(notebook):
    prohibidas = {"fit", "fit_transform", "fit_predict", "partial_fit", "predict", "predict_proba",
                  "GridSearchCV", "RandomizedSearchCV"}
    for c in notebook.cells:
        if c.cell_type != "code":
            continue
        for n in ast.walk(ast.parse(c.source)):
            if isinstance(n, ast.Call):
                nombre = n.func.attr if isinstance(n.func, ast.Attribute) else (
                    n.func.id if isinstance(n.func, ast.Name) else None)
                assert nombre not in prohibidas, f"Llamada prohibida: {nombre}"
            if isinstance(n, ast.Import):
                assert all(a.name.split(".")[0] != "sklearn" for a in n.names)
            if isinstance(n, ast.ImportFrom):
                assert (n.module or "").split(".")[0] != "sklearn"


def test_soporte_hashes_y_guardas_de_derivacion(builder, notebook):
    original = (ROOT / "scripts/colab_soporte.py").read_text(encoding="utf-8")
    derivado = builder.derivar_soporte(original)
    assert _celda(notebook, "soporte-colab").source.partition("\n")[2] == derivado
    assert (ROOT / "scripts/colab_soporte.py").read_text(encoding="utf-8") == original
    asignaciones = [n for n in ast.parse(derivado).body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == "REQUERIDOS_AUDITORIA" for t in n.targets)]
    assert len(asignaciones) == 1 and ast.literal_eval(asignaciones[0].value) == builder.REQUERIDOS
    assert "ReinicioColabRequerido" in derivado and "--only-binary=:all:" in derivado
    assert notebook.metadata.agrocebada.soporte_sha256 == _sha(derivado.encode())
    assert notebook.metadata.agrocebada.perfil_sha256 == _sha((ROOT / "requirements-colab-auditoria.txt").read_bytes())
    for invalido in (original.replace("REQUERIDOS_AUDITORIA", "OTRA_TUPLA"), original + original):
        with pytest.raises(ValueError):
            builder.derivar_soporte(invalido)


def test_insumos_fuentes_y_contratos_viajan_en_notebook(notebook, config, insumos):
    assert set(insumos) == set(config["insumos"])
    fuentes = notebook.metadata.agrocebada.fuentes_sha256
    assert isinstance(fuentes, Mapping) and fuentes
    for ruta, esperado in fuentes.items():
        assert re.fullmatch(r"[0-9a-f]{64}", esperado) and _sha((ROOT / ruta).read_bytes()) == esperado
    codigo = "\n".join(c.source for c in notebook.cells if c.cell_type == "code")
    assert str(ROOT) not in codigo and "/home/netfoor/" not in codigo
    for nombre, contrato in config["insumos"].items():
        b = _bruto(insumos[nombre])
        assert b == (ROOT / contrato["ruta_local"]).read_bytes()
        assert insumos[nombre]["sha256"] == contrato["sha256"] == _sha(b)
        assert insumos[nombre]["bytes"] == contrato["bytes"] == len(b)
        assert insumos[nombre]["uso"] == contrato["uso"]
        assert contrato["sha256"] in codigo


@pytest.mark.parametrize("alteracion", ["hash", "truncado", "ausente"])
def test_insumo_alterado_se_rechaza_solo_en_copia_temporal(builder, config, tmp_path, alteracion):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/exp_01_bloques.json").write_text(json.dumps(config), encoding="utf-8")
    for reg in config["insumos"].values():
        relativa = Path(reg["ruta_local"])
        assert not relativa.is_absolute() and ".." not in relativa.parts
        destino = tmp_path / relativa
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relativa, destino)
    destino = tmp_path / next(iter(config["insumos"].values()))["ruta_local"]
    b = destino.read_bytes()
    assert b
    if alteracion == "hash":
        destino.write_bytes(bytes([b[0] ^ 1]) + b[1:])
    elif alteracion == "truncado":
        destino.write_bytes(b[:-1])
    else:
        destino.unlink()  # Solo una copia temporal propia de pytest.
    with pytest.raises((ValueError, RuntimeError, FileNotFoundError)):
        builder.cargar_insumos(tmp_path)


def test_historia_visible_skipna_por_fila_y_tres_anios_ausentes(notebook):
    medias = [n for n in ast.walk(ast.parse(_celda(notebook, "historia-visible").source))
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "mean"
              and any(k.arg == "axis" and isinstance(k.value, ast.Constant) and k.value.value == 1 for k in n.keywords)]
    assert medias
    n = copy.deepcopy(medias[0])
    assert any(k.arg == "skipna" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords)
    n.func.value = ast.Name(id="historia", ctx=ast.Load())
    expresion = ast.fix_missing_locations(ast.Expression(body=n))
    historia = pd.DataFrame({"2022": [1., np.nan, np.nan, -2.],
                             "2023": [2., 4., np.nan, 0.], "2024": [3., np.nan, np.nan, 2.]})
    r = eval(compile(expresion, "<historia-sintetica>", "eval"), {"historia": historia, "np": np, "pd": pd})
    np.testing.assert_allclose(r.to_numpy(), [2., 4., np.nan, 0.], equal_nan=True)


def test_diseno_mediana_ddof0_onehot_completo_y_categoria_desconocida(notebook):
    calls = [n for n in ast.walk(ast.parse(_celda(notebook, "diseno-visible").source)) if isinstance(n, ast.Call)]
    nombres = {n.func.attr for n in calls if isinstance(n.func, ast.Attribute)}
    assert {"get_dummies", "median", "fillna", "mean", "std", "reindex"} <= nombres
    for metodo, argumento in (("std", "ddof"), ("reindex", "fill_value")):
        assert any(isinstance(n.func, ast.Attribute) and n.func.attr == metodo and any(
            k.arg == argumento and isinstance(k.value, ast.Constant) and k.value.value == 0 for k in n.keywords) for n in calls)
    assert not any(isinstance(n.func, ast.Attribute) and n.func.attr == "get_dummies" and any(
        k.arg == "drop_first" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords) for n in calls)


@pytest.mark.parametrize("scores,esperado", [([1., 1., 1., 1., 1.], 100.),
    ([1., 1.+5e-13, 1.+2e-12, 2., 3.], .1), ([3., 2., 1., 4., 5.], 1.), ([5., 4., 3., 2., 1.], 100.)])
def test_selector_minimo_empate_y_orden_de_alphas(notebook, scores, esperado):
    fila = pd.Series({f"rmse_interno_alpha_{a:g}": v for a, v in zip(ALPHAS, scores, strict=True)})
    fila["alpha"] = -999.
    assert _funcion(notebook, "seleccionar_alpha")(fila.iloc[::-1]) == esperado


@pytest.mark.parametrize("valor", [np.nan, np.inf, -np.inf])
def test_selector_rechaza_scores_no_finitos(notebook, valor):
    fila = pd.Series({f"rmse_interno_alpha_{a:g}": valor for a in ALPHAS})
    with pytest.raises((ValueError, AssertionError)):
        _funcion(notebook, "seleccionar_alpha")(fila)


def test_metricas_r2_estandar_negativo(notebook):
    r = _metricas(_funcion(notebook, "metricas")(pd.DataFrame({"observado": [1., 2., 3.], "predicho": [10., 10., 10.]})))
    np.testing.assert_allclose(list(r.values()), [np.sqrt(194/3), 8., -96.], atol=1e-12, rtol=0)


@pytest.mark.parametrize("y,nan", [([2., 2., 2.], True), ([0., 1e-6], True), ([0., 2e-6], False)])
def test_metricas_umbral_historico_sst_1e_menos12(notebook, y, nan):
    r = _metricas(_funcion(notebook, "metricas")(pd.DataFrame({"observado": y, "predicho": np.zeros(len(y))})))
    assert bool(np.isnan(r["R2"])) == nan
    if not nan:
        assert np.isclose(r["R2"], -1., atol=1e-12, rtol=0)
    assert np.isfinite(r["RMSE"]) and np.isfinite(r["MAE"])


@pytest.mark.parametrize("y,p", [([], []), ([1., np.nan], [1., 2.]), ([1., 2.], [1., np.inf])])
def test_metricas_rechaza_vacios_y_no_finitos(notebook, y, p):
    with pytest.raises((ValueError, AssertionError)):
        _funcion(notebook, "metricas")(pd.DataFrame({"observado": y, "predicho": p}))


def test_pooled_no_promedia_predicciones_ni_rmse_de_pliegues(notebook):
    fn = _funcion(notebook, "metricas")
    d = pd.DataFrame({"ID_POLIGONO": ["A", "A", "B", "B"], "observado": [1., 1., 3., 3.], "predicho": [0., 2., 2., 4.]})
    assert _metricas(fn(d))["RMSE"] == 1.
    assert _metricas(fn(d.groupby("ID_POLIGONO", as_index=False)[["observado", "predicho"]].mean()))["RMSE"] == 0.
    desiguales = pd.DataFrame({"observado": [0., 0., 0., 0.], "predicho": [0., 2., 2., 2.]})
    pooled = _metricas(fn(desiguales))["RMSE"]
    media = np.mean([_metricas(fn(g))["RMSE"] for g in (desiguales.iloc[:1], desiguales.iloc[1:])])
    assert np.isclose(pooled, np.sqrt(3.), atol=1e-12, rtol=0) and media == 1.


def test_reales_oof_internas_alpha_y_metricas_guardadas(insumos, notebook):
    ts = _csvs(insumos)
    oof = _tabla(ts, lambda d: set(CLAVES+["observado", "predicho", "alpha"]) <= set(d), "OOF E0–E4")
    ext = _tabla(ts, lambda d: {"repeticion", "pliegue", "rol", "ID_POLIGONO"} <= set(d)
                 and "pliegue_interno" not in d and "modelo" not in d, "roles externos")
    inner = _tabla(ts, lambda d: {"repeticion", "pliegue", "pliegue_interno", "rol", "ID_POLIGONO"} <= set(d), "roles interiores")
    sel = _tabla(ts, lambda d: {"modelo", "repeticion", "pliegue", "alpha"} <= set(d)
                 and all(f"rmse_interno_alpha_{a:g}" in d for a in ALPHAS), "scores guardados")
    control = _tabla(ts, lambda d: {"modelo", "RMSE_agrupado", "MAE_agrupado", "R2_agrupado"} <= set(d)
                     and not {"Municipio", "Estado", "zona"} & set(d), "control global")
    assert len(oof) == 6900 and oof.ID_POLIGONO.nunique() == 138
    assert set(oof.modelo) == {"E0", "E1", "E2", "E3", "E4"}
    assert not oof.duplicated(CLAVES).any() and not oof[CLAVES].isna().any().any()
    assert np.isfinite(oof[["observado", "predicho", "alpha"]].to_numpy()).all()
    assert oof.groupby("ID_POLIGONO").observado.nunique().eq(1).all()
    assert set(oof.alpha) <= set(ALPHAS)
    assert len(ext) == 6900 and len(inner) == 22080 and len(sel) == 250
    assert set(ext.rol) == set(inner.rol) == {"entrenamiento", "validacion"}
    assert not ext.duplicated(CLAVES[1:]).any()
    assert not inner.duplicated(["repeticion", "pliegue", "pliegue_interno", "ID_POLIGONO"]).any()
    esperado = ext.loc[ext.rol.eq("validacion"), CLAVES[1:]].sort_values(CLAVES[1:]).reset_index(drop=True)
    calcular, elegir = _funcion(notebook, "metricas"), _funcion(notebook, "seleccionar_alpha")
    for nombre, g in oof.groupby("modelo"):
        assert len(g) == 1380 and g[CLAVES[1:]].sort_values(CLAVES[1:]).reset_index(drop=True).equals(esperado)
        assert g.groupby(["repeticion", "ID_POLIGONO"]).size().eq(1).all()
        fila = control.loc[control.modelo.eq(nombre)]
        assert len(fila) == 1
        for metrica, valor in _metricas(calcular(g)).items():
            np.testing.assert_allclose(valor, fila.iloc[0][metrica+"_agrupado"], atol=1e-12, rtol=0)
    assert not sel.duplicated(CLAVES[:3]).any()
    assert all(elegir(fila) == fila.alpha for _, fila in sel.iterrows())
    union = oof.merge(sel[CLAVES[:3]+["alpha"]], on=CLAVES[:3], validate="many_to_one", suffixes=("", "_sel"))
    assert len(union) == len(oof) and union.alpha.eq(union.alpha_sel).all()
    for (r, f), g in ext.groupby(["repeticion", "pliegue"]):
        tr = set(g.loc[g.rol.eq("entrenamiento"), "ID_POLIGONO"])
        va = set(g.loc[g.rol.eq("validacion"), "ID_POLIGONO"])
        sub = inner.loc[inner.repeticion.eq(r) & inner.pliegue.eq(f)]
        assert len(tr) in (110, 111) and len(va) in (27, 28)
        assert set(sub.ID_POLIGONO) == tr and not set(sub.ID_POLIGONO) & va
        assert set(sub.pliegue_interno) == {0, 1, 2, 3}
        assert sub.loc[sub.rol.eq("validacion"), "ID_POLIGONO"].is_unique
        for _, dentro in sub.groupby("pliegue_interno"):
            assert set(dentro.ID_POLIGONO) == tr and dentro.ID_POLIGONO.is_unique


def test_aliases_de_las_tres_referencias_tambien_concilian_control(insumos, notebook):
    ref = pd.read_csv(io.BytesIO(_bruto(insumos["referencias"])), encoding="utf-8-sig")
    control = pd.read_csv(io.BytesIO(_bruto(insumos["metricas_control"])), encoding="utf-8-sig").set_index("modelo")
    alias = {"Media global": "GLOBAL", "Media municipal": "MUN", "Municipio + IDW fijo": "MIX"}
    ref = ref.loc[ref.modelo.isin(alias)].copy()
    ref["modelo"] = ref.modelo.map(alias)
    control = control.rename(index=alias)
    assert control.index.is_unique and set(control.index) == {"E0", "E1", "E2", "E3", "E4", "GLOBAL", "MUN", "MIX"}
    assert "rename(index=alias)" in _celda(notebook, "control-posterior").source
    calcular = _funcion(notebook, "metricas")
    for modelo, grupo in ref.groupby("modelo"):
        assert len(grupo) == 1380
        for metrica, valor in _metricas(calcular(grupo)).items():
            np.testing.assert_allclose(valor, control.loc[modelo, metrica+"_agrupado"], atol=1e-12, rtol=0)


def test_narrativa_limites_cero_ajustes_y_predicciones_finales(notebook):
    texto = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split()).lower()
    for palabra in ("e0", "e1", "e2", "e3", "e4", "ridge", "intercepto", "regulariz",
                    "exploratori", "guardad", "mediana", "138", "59"):
        assert palabra in texto
    assert re.search(r"e0.{0,250}(?:no|distint|equivale).{0,140}(?:media municipal|mun)", texto)
    assert re.search(r"(?:scores|errores|rmse).{0,180}(?:intern|interior)", texto)
    assert re.search(r"(?:no|sin).{0,140}(?:reentren|entren|reproduc|recalcul)", texto)
    assert "intervalo de confianza" in texto or "intervalos de confianza" in texto
    assert "posterior" in texto or "post hoc" in texto or "post-hoc" in texto
    sensibilidad = _celda(notebook, "sensibilidad-visible").source
    assert "AGC_127" in sensibilidad and "AGC_171" in sensibilidad
    campos = {}
    for n in ast.walk(ast.parse(_celda(notebook, "cierre").source)):
        if isinstance(n, ast.Dict):
            campos.update({k.value: v.value for k, v in zip(n.keys, n.values, strict=True)
                           if isinstance(k, ast.Constant) and isinstance(k.value, str) and isinstance(v, ast.Constant)})
    assert campos.get("ajustes_actuales") == 0
    assert any("predic" in k and "final" in k and v == 0 for k, v in campos.items())
