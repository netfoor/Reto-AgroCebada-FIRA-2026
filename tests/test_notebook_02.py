"""Contrato de autonomía, procedencia y alcance del cuaderno de fuentes."""

from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import io
import json
import re
import sys
import zlib
from pathlib import Path

import nbformat
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("construir_notebook_02", ROOT / "scripts/construir_notebook_02.py")
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


@pytest.fixture(scope="module")
def notebook():
    return BUILDER.construir(ROOT)


def _celda(notebook, tag):
    candidatas = [c for c in notebook.cells if tag in c.metadata.get("tags", [])]
    assert len(candidatas) == 1
    return candidatas[0]


def _literal(celda, nombre):
    for nodo in ast.parse(celda.source).body:
        if isinstance(nodo, ast.Assign) and any(isinstance(t, ast.Name) and t.id == nombre for t in nodo.targets):
            return ast.literal_eval(nodo.value)
    raise AssertionError(f"No existe una constante literal llamada {nombre}.")


def _fuente(notebook):
    return "\n".join(c.source for c in notebook.cells if c.cell_type == "code")


def test_notebook_valido_sin_ejecucion_con_ids_unicos(notebook):
    nbformat.validate(notebook)
    ids = [c.id for c in notebook.cells]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"fuentes02-\d+", name) for name in ids)
    assert len(notebook.cells) >= 30
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == []


def test_modulos_incrustados_tienen_hash_y_orden_correctos(notebook):
    celda = _celda(notebook, "modulos-tecnicos")
    fuentes = _literal(celda, "FUENTES_MODULOS")
    assert list(fuentes) == list(BUILDER.MODULOS)
    for nombre, registro in fuentes.items():
        original = (ROOT / "scripts" / f"{nombre}.py").read_bytes()
        assert registro["source"].encode() == original
        assert registro["sha256"] == hashlib.sha256(original).hexdigest()
        assert notebook.metadata.agrocebada.modulos_sha256[nombre] == registro["sha256"]
        ast.parse(registro["source"])
    assert "types.ModuleType" in celda.source and "sys.modules[nombre]" in celda.source
    assert '"<notebook02/"' in celda.source
    assert celda.metadata.jupyter.source_hidden is True


def test_preparacion_deriva_solo_una_tupla_y_preserva_soporte_compartido(notebook):
    original = (ROOT / "scripts/colab_soporte.py").read_text()
    derivado = BUILDER.derivar_soporte(original)
    celda = _celda(notebook, "soporte-colab")
    assert celda.source == derivado
    assert (ROOT / "scripts/colab_soporte.py").read_text() == original
    before = _literal(nbformat.v4.new_code_cell(original), "REQUERIDOS_AUDITORIA")
    after = _literal(celda, "REQUERIDOS_AUDITORIA")
    assert before == BUILDER.REQUERIDOS[:-1]
    assert after == BUILDER.REQUERIDOS and len(after) == 8
    assert derivado.replace(', "rasterio",\n)', ',\n)', 1) == original
    registro = notebook.metadata.agrocebada
    assert registro.soporte_base_sha256 == hashlib.sha256(original.encode()).hexdigest()
    assert registro.soporte_derivado_sha256 == hashlib.sha256(derivado.encode()).hexdigest()
    assert "ReinicioColabRequerido" in derivado and "--only-binary=:all:" in derivado
    assert "modulos_cargados" in derivado and "permitir_descarga" in derivado
    assert celda.metadata.jupyter.source_hidden is True
    with pytest.raises(ValueError, match="soporte compartido cambió"):
        BUILDER.derivar_soporte(original.replace("REQUERIDOS_AUDITORIA", "OTRA_TUPLA"))


def test_perfil_config_y_versiones_son_los_archivos_identificados(notebook):
    prep = _celda(notebook, "preparar-colab")
    perfil = (ROOT / "requirements-colab-auditoria.txt").read_text()
    assert _literal(prep, "REQUIREMENTS_COLAB") == perfil
    versiones = _literal(prep, "VERSIONES")
    assert set(versiones) == set(BUILDER.REQUERIDOS)
    assert len(dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)", perfil, re.MULTILINE))) == 40
    registro = notebook.metadata.agrocebada
    assert registro.perfil_colab_sha256 == hashlib.sha256(perfil.encode()).hexdigest()
    assert dict(registro.dependencias_requeridas) == versiones
    assert "PREPARAR_COLAB = True" in prep.source
    assert "en_colab=EN_COLAB" in prep.source
    assert prep.source.index("sys.version_info[:2]") < prep.source.index("preparar_colab(")
    assert "sys.version_info[:2] == (3, 13)" in _fuente(notebook)
    config = _celda(notebook, "config-recetas")
    original = (ROOT / "config/fuentes_02_recetas.json").read_text()
    assert _literal(config, "CONFIG_JSON") == original
    assert registro.config_recetas_sha256 == hashlib.sha256(original.encode()).hexdigest()
    expected = json.loads(original)
    assert expected["lai_negativos"] == "conservar"
    assert set(expected["nubosidad_max_por_sensor"].values()) == {None}
    assert expected["integral_hueco_max_dias"] == 30


def test_descarga_usa_identidad_del_dataset_y_local_no_red(notebook):
    contrato_path = ROOT / "config/auditoria_01_dataset.json"
    contrato = json.loads(contrato_path.read_text())
    acceso = _celda(notebook, "acceso-dataset")
    assert _literal(acceso, "ID_DRIVE_DATASET") == contrato["transporte"]["drive"]["file_id"]
    assert "DESCARGAR_DATASET = EN_COLAB" in acceso.source
    assert "bytes_esperados=29_687_194" in acceso.source
    assert "sha256_esperado=SHA256_DATASET" in acceso.source
    assert "permitir_descarga=DESCARGAR_DATASET" in acceso.source
    registro = notebook.metadata.agrocebada
    assert registro.dataset_config_sha256 == hashlib.sha256(contrato_path.read_bytes()).hexdigest()
    assert registro.dataset_sha256 == contrato["sha256"] and registro.dataset_bytes == contrato["bytes"]


def test_fixtures_identificados_solo_de_salida_y_descompresion_acotada(notebook):
    celda = _celda(notebook, "referencias-tecnicas")
    referencias = _literal(celda, "REFERENCIAS_INCRUSTADAS")
    config = json.loads((ROOT / "config/fuentes_02_recetas.json").read_text())
    assert set(referencias) == {"base", "postciclo"}
    assert len(celda.source.encode()) < 550_000
    for nombre, referencia in referencias.items():
        contenido = zlib.decompress(base64.b64decode(referencia["bytes_zlib_base64"], validate=True))
        assert len(contenido) == referencia["bytes"] == config["referencias"][nombre]["bytes"]
        assert hashlib.sha256(contenido).hexdigest() == referencia["sha256"]
        assert contenido == (ROOT / config["referencias"][nombre]["ruta_local"]).read_bytes()
        assert dict(notebook.metadata.agrocebada.referencias[nombre]) == {
            k: referencia[k] for k in ("sha256", "bytes", "origen")
        }
    assert 'registro["bytes"] + 1' in celda.source
    assert celda.source.index('hashlib.sha256(contenido)') < celda.source.index('pd.read_csv(')
    ns = {"base64": base64, "zlib": zlib, "hashlib": hashlib, "pd": pd, "io": io}
    exec(compile(celda.source, "<control-referencias>", "exec"), ns)
    assert ns["leer_referencia"]("base").shape == (197, 539)
    assert ns["leer_referencia"]("postciclo").shape == (197, 122)
    ns["REFERENCIAS_INCRUSTADAS"]["base"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        ns["leer_referencia"]("base")
    ns["REFERENCIAS_INCRUSTADAS"]["postciclo"]["bytes"] -= 1
    with pytest.raises(ValueError, match="límite de bytes"):
        ns["leer_referencia"]("postciclo")
    assert celda.metadata.jupyter.source_hidden is True


def test_no_aprendizaje_exportacion_ni_transporte_fuera_soporte(notebook):
    llamadas_prohibidas = {"fit", "predict", "fit_predict", "fit_transform", "train_test_split",
                          "to_csv", "to_excel", "to_pickle", "to_file", "extractall", "kill"}
    modulos_prohibidos = {"sklearn", "xgboost", "lightgbm", "catboost", "requests"}
    sources = []
    for c in notebook.cells:
        if c.cell_type == "code":
            sources.append((c.source, "soporte-colab" in c.metadata.get("tags", [])))
    for registro in _literal(_celda(notebook, "modulos-tecnicos"), "FUENTES_MODULOS").values():
        sources.append((registro["source"], False))
    for source, soporte in sources:
        for nodo in ast.walk(ast.parse(source)):
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else [nodo.module or ""]
                assert all(n.split(".")[0] not in modulos_prohibidos for n in names)
                if not soporte:
                    assert all(n.split(".")[0] != "gdown" for n in names)
            if isinstance(nodo, ast.Call):
                nombre = getattr(nodo.func, "attr", getattr(nodo.func, "id", ""))
                assert nombre not in llamadas_prohibidas
                if nombre == "download":
                    assert soporte


def test_referencias_no_se_utilizan_para_transformaciones(notebook):
    ciencia = [c for c in notebook.cells if c.cell_type == "code"
               and not set(c.metadata.get("tags", [])) & {"referencias-tecnicas", "contraste-referencias"}]
    for c in ciencia:
        assert "referencia_base" not in c.source and "referencia_postciclo" not in c.source
        assert "leer_referencia(" not in c.source
    orden_tags = [c.metadata.get("tags", []) for c in notebook.cells]
    assert next(i for i, tags in enumerate(orden_tags) if "ensamblar-197" in tags) < next(
        i for i, tags in enumerate(orden_tags) if "contraste-referencias" in tags
    )
    codigo = _celda(notebook, "ensamblar-197").source
    tree = ast.parse(codigo)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "ensamblar_variables":
            assert len(node.args) == 5
            assert all(not isinstance(arg, ast.Name) or arg.id not in {"etiquetas", "referencia_base"} for arg in node.args)


def test_alcance_base_diccionario_postciclo_y_cierre(notebook):
    base = _celda(notebook, "ensamblar-197").source
    assert "tabla_base.shape == (197, 539)" in base
    assert "tabla_postciclo.shape == (197, 122)" in base
    assert 'c.startswith("P_")' in base
    assert '"RENDIMIENTO" in c.upper()' in base
    assert "28_368" in base
    dic = _celda(notebook, "diccionario-660")
    assert _literal(dic, "CAMPOS_DICCIONARIO") == [
        "variable", "bloque", "rol", "fuente", "sensor", "indice", "ventana", "agregacion",
        "filtro", "unidad", "archivo", "faltantes", "origen",
    ]
    assert "diccionario.shape == (660, 13)" in dic.source
    assert "list(tabla_base) + list(postciclo)" in dic.source
    assert '"pendiente_admisibilidad"' in dic.source
    cierre = _celda(notebook, "cierre-verificable").source
    assert "RESUMEN_FUENTES_02_JSON=" in cierre
    assert "hash_final == hash_inicial == SHA256_DATASET" in cierre
    assert '"modelos_entrenados": 0' in cierre
    assert '"predicciones_finales_generadas": 0' in cierre
    assert '"objetivos_imputados": 0' in cierre
    assert '"tablas_exportadas": 0' in cierre
    assert "zip_fuente.close()" in cierre
    for field in ("parcelas", "columnas_base", "columnas_postciclo", "variables_diccionario",
                  "etiquetas", "por_predecir", "rasteres", "filas_clima", "sha256_dataset"):
        assert f'"{field}"' in cierre


def test_narrativa_autocontenida_con_fuentes_limites_y_mallas_correctas(notebook):
    texto = "\n".join(c.source for c in notebook.cells if c.cell_type == "markdown")
    assert len(re.findall(r"^## \d+\.", texto, re.MULTILINE)) == 12
    for frase in ("Andrea", "Codex", "NoData", "214 días", "213 días", "660", "197 × 539",
                  "0.993", "0.836", "2.1 %", "0 %", "sin modelo", "NB03"):
        assert frase in texto
    assert "Lluvia y temperatura tienen dos mallas distintas" in texto
    assert "elevación y pendiente comparten la misma malla" in texto
    assert "ya utilizada en T1" not in texto
    assert "no constituye un preregistro" in texto
    assert "no lo" in texto and "biomasa" in texto
    for url in ("https://rasterio.readthedocs.io/en/stable/topics/memory-files.html",
                "https://rasterio.readthedocs.io/en/stable/topics/transforms.html",
                "https://pyproj4.github.io/pyproj/stable/api/transformer.html",
                "https://shapely.readthedocs.io/en/stable/reference/shapely.intersection.html"):
        assert url in texto
    registro = notebook.metadata.agrocebada
    assert registro.crisp_dm == [3] and registro.modo == "recalcular_sin_entrenar"
    assert registro.trabajo_original == "2026-09-21" and registro.adaptacion == "2026-10-07"
    assert registro.antecedente_geo == "2026-10-01" and registro.verificacion_actual == "2026-10-07"


def test_generador_rechaza_sobrescritura_antes_de_construir(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["construir_notebook_02.py", "--salida", "/tmp/control-existente.ipynb"])
    monkeypatch.setattr(Path, "exists", lambda self: True)
    called = []
    monkeypatch.setattr(BUILDER, "construir", lambda *_: called.append(True))
    with pytest.raises(ValueError, match="no se sobrescribe"):
        BUILDER.main()
    assert called == []
