"""EXP07: lector sin ajustes, operaciones visibles y evidencia incrustada."""
from __future__ import annotations

import ast
import base64
import hashlib
import importlib.util
import io
import json
import re
import zlib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import matplotlib
import nbformat
import numpy as np
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("construir_exp_07", ROOT / "scripts/construir_exp_07.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
VISIBLE = ["fuentes-visibles", "parcela-visible", "variables-visibles", "factibilidad-visible",
           "calidad-soporte-visible", "registro-visible", "particiones-visibles", "seleccion-visible",
           "ecuacion-visible", "metricas-visibles", "reglas-visibles", "concentracion-visible", "cierre"]


@lru_cache(maxsize=1)
def notebook():
    return gen.construir(ROOT)


def cell(tag):
    found = [c for c in notebook().cells if tag in c.metadata.get("tags", [])]
    assert len(found) == 1
    return found[0]


def namespace_insumos():
    ns = {"np": np, "pd": pd, "hashlib": hashlib, "json": json, "base64": base64,
          "zlib": zlib, "io": io, "re": re, "Path": Path}
    exec(compile(cell("insumos-tecnicos").source, "insumos_07", "exec"), ns)
    return ns


def test_notebook_validado_y_metadata_alcance():
    nbformat.validate(notebook())
    m = notebook().metadata.agrocebada
    assert m.id == "EXP_07" and m.ajustes_actuales == 0 and m.colab_real_probado is False
    assert m.modo == "lector_resultados_experimento_registrado_sin_ajustes"
    assert len(m.insumos) == 29
    assert hashlib.sha256((ROOT / gen.BASE).read_bytes()).hexdigest() == gen.BASE_SHA


def test_solo_dos_celdas_tecnicas_plegadas():
    folded = [c for c in notebook().cells if c.metadata.get("cellView") == "form"]
    assert len(folded) == 2
    for tag in VISIBLE:
        assert cell(tag).metadata.get("cellView") != "form"
    assert all(c.execution_count is None and c.outputs == [] for c in notebook().cells if c.cell_type == "code")


def test_orden_QA_antes_de_etiquetas():
    code = [c for c in notebook().cells if c.cell_type == "code"]
    index = next(i for i, c in enumerate(code) if "calidad-soporte-visible" in c.metadata.get("tags", []))
    for c in code[:index+1]:
        assert 'csv_insumo("etiquetas")' not in c.source
    assert 'csv_insumo("etiquetas")' in cell("registro-visible").source


def test_no_ajustar_motor_ni_modelos_en_lector():
    forbidden = {"fit", "fit_predict", "fit_transform", "ajustar", "ejecutar_comparacion", "evaluar"}
    for c in notebook().cells:
        if c.cell_type != "code":
            continue
        tree = ast.parse(c.source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fun = node.func
                name = fun.attr if isinstance(fun, ast.Attribute) else fun.id if isinstance(fun, ast.Name) else ""
                assert name not in forbidden
            if isinstance(node, ast.Import):
                assert not any(n.name.startswith(("modelo_07", "experimento_07", "sklearn")) for n in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(("modelo_07", "experimento_07", "sklearn"))
    for tag in VISIBLE:
        text = cell(tag).source
        assert "exec(" not in text and "gdown" not in text and "read_bytes(" not in text


def test_insumos_hash_tamano_y_roles_coinciden():
    ns = namespace_insumos()
    cfg = json.loads((ROOT / gen.CONFIG).read_text())
    for k, rec in cfg["insumos"].items():
        b = ns["bytes_insumo"](k, rec["uso"])
        assert b == (ROOT / rec["ruta_local"]).read_bytes()
        assert len(b) == rec["bytes"] and hashlib.sha256(b).hexdigest() == rec["sha256"]
        assert len(b) <= 2 * 1024 * 1024


@pytest.mark.parametrize("key", ["modelo_fuente", "experimento_fuente"])
def test_fuente_completa_comentada_no_ejecutada(key):
    ns = namespace_insumos()
    fuente = ns["bytes_insumo"](key, ns["INSUMOS_INCRUSTADOS"][key]["uso"]).decode()
    src = cell("insumos-tecnicos").source
    marker = "# Fuente completa solo para inspección: " + key + "\n"
    bloque = src.split(marker, 1)[1].split("\n# Fuente completa solo para inspección:", 1)[0]
    reconstruida = "\n".join(line[3:] for line in bloque.splitlines() if line.startswith("#| "))
    assert reconstruida == fuente.rstrip("\n")
    assert "ajustar" not in ns and "ejecutar_comparacion" not in ns


@pytest.mark.parametrize("corrupt", ["rol", "sha", "bytes", "base64"])
def test_decoder_rechaza_corrupcion(corrupt):
    ns = namespace_insumos()
    entry = ns["INSUMOS_INCRUSTADOS"]["capturas"]
    if corrupt == "rol":
        with pytest.raises(ValueError):
            ns["bytes_insumo"]("capturas", "otro_rol")
        return
    campo, valor = {"sha": ("sha256", "0" * 64), "bytes": ("bytes", 3), "base64": ("bytes_zlib_base64", "!!!")}[corrupt]
    entry[campo] = valor
    with pytest.raises((ValueError, zlib.error)):
        ns["bytes_insumo"]("capturas", entry["uso"])


def test_generacion_determinista():
    assert nbformat.writes(gen.construir(ROOT)) == nbformat.writes(gen.construir(ROOT))


def test_no_exportar_tablas_no_rutas_externas_no_descargas_ciencia():
    for tag in VISIBLE:
        calls = [n for n in ast.walk(ast.parse(cell(tag).source)) if isinstance(n, ast.Call)]
        for n in calls:
            name = n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id if isinstance(n.func, ast.Name) else ""
            assert name not in {"to_csv", "write_text", "write_bytes", "download", "open", "get", "urlopen"}


def test_recorrido_cientifico_completo_sin_motor_entrenamiento(capsys):
    plt.close("all")
    ns = namespace_insumos()
    ns.update({"display": lambda *args: None, "plt": plt, "datetime": datetime, "timezone": timezone})
    for tag in VISIBLE:
        exec(compile(cell(tag).source, tag, "exec"), ns)
    resumen = ns["resumen"]
    assert resumen["ajustes_actuales"] == 0 and resumen["predicciones_finales_generadas"] == 0
    assert resumen["oof_total"] == 5520 and resumen["scores_guardados_verificados"] == 600
    assert resumen["sse_interiores_verificadas"] == 2400 and resumen["ecuaciones_oof_reproducidas"] == 1
    assert resumen["aporte_H7_regla"] is False and resumen["competitivos_prospectivos"] == []
    assert resumen["variantes_adoptadas"] == []
    assert len(plt.get_fignums()) == 2
    plt.close("all")
    assert "RESUMEN_EXP_07_JSON=" in capsys.readouterr().out


def test_metricas_constantes_y_vacias():
    ns = {"np": np, "pd": pd}
    tree = ast.parse(cell("metricas-visibles").source)
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "metricas"]
    exec(compile(ast.Module(body=defs, type_ignores=[]), "metricas", "exec"), ns)
    d = pd.DataFrame({"ID_POLIGONO": ["A", "B"], "observado": [4.45, 4.45], "predicho": [4.4, 4.5]})
    assert np.isnan(ns["metricas"](d)["R2"])
    assert np.isclose(ns["metricas"](d)["RMSE"], .05)
    with pytest.raises(ValueError):
        ns["metricas"](d.iloc[:0])


def test_corrida_guardada_no_modificada_por_lector():
    cfg = json.loads((ROOT / gen.CONFIG).read_text())
    for key in ["registro_previo", "registro_ejecucion", "oof", "scores", "scores_pliegue", "seleccion", "parametros"]:
        rec = cfg["insumos"][key]
        assert hashlib.sha256((ROOT / rec["ruta_local"]).read_bytes()).hexdigest() == rec["sha256"]


def test_ejecutor_alcance_y_proteccion_salida():
    s = (ROOT / "scripts/ejecutar_notebook_exp_07.py").read_text()
    assert "KernelManager" in s and '"transport": "ipc"' in s
    assert "destino.exists()" in s and "colab_real_probado" in s
    assert '"ajustes_actuales": 0' in s and '"predicciones_finales_generadas": 0' in s
    assert "modelo_07" not in s and "experimento_07" not in s


def test_leyenda_cierre_no_descarta_toda_heterogeneidad():
    textos = "\n".join(c.source for c in notebook().cells if c.cell_type == "markdown")
    assert "Cierre sin adopción" in textos
    assert "no para toda heterogeneidad" in textos
    assert "no reentrena" in textos and "registro previo" in textos


def test_bootstrap_copia_soporte_verificado():
    anterior = nbformat.read(ROOT / gen.BASE, as_version=4)
    for tag in ["soporte-colab", "preparar-colab", "entorno"]:
        old = next(c for c in anterior.cells if tag in c.metadata.get("tags", []))
        assert cell(tag).source == old.source


def test_tablas_controles_solo_abiertas_despues_de_calcular():
    s = cell("variables-visibles").source
    assert s.index("medias =") < s.index('csv_insumo("variables_control")')
    s = cell("metricas-visibles").source
    assert s.index("met =") < s.index('contrastar(met,"metricas_control"')
    s = cell("concentracion-visible").source
    assert s.index("deltas_rows.extend") < s.index('contrastar(deltas,"contrastes_control"')


def test_resumen_no_confunde_scores_sse_con_ajustes():
    src = cell("cierre").source
    assert '"scores_desde_sse_recalculados":600' in src
    assert '"errores_interiores_regenerados":False' in src
    assert '"oof_regeneradas":False' in src
    assert '"ajustes_actuales":0' in src
