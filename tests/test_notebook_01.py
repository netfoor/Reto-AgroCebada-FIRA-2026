"""Contrato del cuaderno educativo: integridad, autonomía y alcance descriptivo."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
from pathlib import Path

import nbformat


def _rutas_fuente():
    carpeta = Path(__file__).resolve().parent
    raiz = carpeta.parent
    if (raiz / "scripts" / "construir_notebook_01.py").is_file():
        return (
            raiz / "scripts" / "construir_notebook_01.py",
            raiz / "scripts" / "auditoria_01.py",
            raiz / "requirements-colab-auditoria.txt",
        )
    return (
        carpeta / "construir_notebook_01.py",
        carpeta / "auditoria_01.py",
        carpeta / "requirements-colab-auditoria.txt",
    )


def _cuaderno():
    builder, lector, perfil = _rutas_fuente()
    spec = importlib.util.spec_from_file_location("construir_notebook_01", builder)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo.construir(lector, perfil), lector, perfil


def test_cuaderno_es_valido_y_con_ids_unicos():
    cuaderno, _, _ = _cuaderno()
    nbformat.validate(cuaderno)
    ids = [celda.id for celda in cuaderno.cells]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"audit01-\d+", identificador) for identificador in ids)


def test_construir_no_ejecuta_y_cada_celda_es_python_parseable():
    cuaderno, _, _ = _cuaderno()
    codigos = [celda for celda in cuaderno.cells if celda.cell_type == "code"]
    assert len(codigos) >= 10
    for celda in codigos:
        ast.parse(celda.source)
        assert celda.execution_count is None
        assert celda.outputs == []


def test_lector_incrustado_es_exactamente_el_archivo_verificado():
    cuaderno, lector, perfil = _cuaderno()
    tecnicas = [celda for celda in cuaderno.cells if "lector-tecnico" in celda.metadata.get("tags", [])]
    assert len(tecnicas) == 1
    assert tecnicas[0].source == lector.read_text(encoding="utf-8")
    registro = cuaderno.metadata.agrocebada
    assert registro.lector_sha256 == hashlib.sha256(lector.read_bytes()).hexdigest()
    assert registro.perfil_colab_sha256 == hashlib.sha256(perfil.read_bytes()).hexdigest()


def test_no_modelos_ni_seleccion_y_transporte_solo_en_soporte_autorizado():
    cuaderno, _, _ = _cuaderno()
    modulos_prohibidos = {"sklearn", "xgboost", "lightgbm", "catboost", "requests"}
    llamadas_prohibidas = {
        "fit", "predict", "fit_predict", "fit_transform", "train_test_split", "kill",
    }
    for celda in cuaderno.cells:
        if celda.cell_type != "code":
            continue
        es_soporte = "soporte-colab" in celda.metadata.get("tags", [])
        for nodo in ast.walk(ast.parse(celda.source)):
            if isinstance(nodo, ast.Import):
                assert all(alias.name.split(".")[0] not in modulos_prohibidos for alias in nodo.names)
                if not es_soporte:
                    assert all(alias.name.split(".")[0] != "gdown" for alias in nodo.names)
            elif isinstance(nodo, ast.ImportFrom):
                assert (nodo.module or "").split(".")[0] not in modulos_prohibidos
                if not es_soporte:
                    assert (nodo.module or "").split(".")[0] != "gdown"
            elif isinstance(nodo, ast.Call):
                nombre = getattr(nodo.func, "attr", getattr(nodo.func, "id", ""))
                assert nombre not in llamadas_prohibidas
                if nombre == "download":
                    assert es_soporte


def test_preparacion_colab_es_visible_y_no_se_exportan_tablas():
    cuaderno, _, _ = _cuaderno()
    codigos = [celda.source for celda in cuaderno.cells if celda.cell_type == "code"]
    preparaciones = [
        celda for celda in cuaderno.cells if "preparar-colab" in celda.metadata.get("tags", [])
    ]
    assert len(preparaciones) == 1
    preparacion = preparaciones[0].source
    assert "PREPARAR_COLAB = True" in preparacion
    assert "preparar_colab(" in preparacion
    assert "en_colab=EN_COLAB" in preparacion
    assert "habilitar=PREPARAR_COLAB" in preparacion
    assert preparacion.index("sys.version_info[:2]") < preparacion.index("preparar_colab(")
    for codigo in codigos:
        for nodo in ast.walk(ast.parse(codigo)):
            if isinstance(nodo, ast.Call):
                nombre = getattr(nodo.func, "attr", getattr(nodo.func, "id", ""))
                assert nombre not in {"extract", "extractall", "to_csv", "to_excel", "to_pickle", "to_file"}


def test_soporte_incrustado_coincide_con_fuente_y_hash():
    cuaderno, lector, _ = _cuaderno()
    soporte = lector.with_name("colab_soporte.py")
    tecnicas = [celda for celda in cuaderno.cells if "soporte-colab" in celda.metadata.get("tags", [])]
    assert len(tecnicas) == 1
    assert tecnicas[0].source == soporte.read_text(encoding="utf-8")
    assert cuaderno.metadata.agrocebada.soporte_colab_sha256 == hashlib.sha256(
        soporte.read_bytes()
    ).hexdigest()


def test_un_solo_python_y_acceso_controlado_sin_enlaces_cientificos_alterados():
    cuaderno, _, _ = _cuaderno()
    fuente = "\n".join(c.source for c in cuaderno.cells if c.cell_type == "code")
    assert "Python 3.13." in fuente
    assert "sys.version_info[:2] == (3, 13)" in fuente
    accesos = [celda for celda in cuaderno.cells if "acceso-dataset" in celda.metadata.get("tags", [])]
    assert len(accesos) == 1
    assert "obtener_dataset(" in accesos[0].source
    assert "sha256_esperado=SHA256_DATASET" in accesos[0].source
    assert "bytes_esperados=29_687_194" in accesos[0].source


def test_fechas_diferencian_trabajo_original_y_adaptacion():
    cuaderno, _, _ = _cuaderno()
    registro = cuaderno.metadata.agrocebada
    assert registro.trabajo_original == "2026-09-15"
    assert registro.consolidacion_original == "2026-09-16"
    assert registro.adaptacion == "2026-10-07"
    texto = "\n".join(c.source for c in cuaderno.cells if c.cell_type == "markdown")
    assert "Esta adaptación no constituye" in texto
    assert "abril–octubre de 2025" in texto
    assert "no de inferirla" in texto


def test_conclusiones_no_atribuyen_mecanismo_o_causalidad():
    cuaderno, _, _ = _cuaderno()
    texto = "\n".join(c.source for c in cuaderno.cells if c.cell_type == "markdown")
    assert "no demuestra autocorrelación, causalidad ni que el split oficial" in texto
    assert "no prueba cómo se midió el rendimiento" in texto
    assert "no como validado para toda Hidalgo, Tlaxcala y Puebla" in texto
    assert "no elige la receta" in texto


def test_cierre_declara_y_controla_alcance_sin_modelos():
    cuaderno, _, _ = _cuaderno()
    fuente = "\n".join(c.source for c in cuaderno.cells if c.cell_type == "code")
    assert '"modelos_entrenados": 0' in fuente
    assert '"predicciones_finales_generadas": 0' in fuente
    assert '"objetivos_imputados": 0' in fuente
    assert '"extracciones_raster": 0' in fuente
    assert "assert hash_final == hash_inicial == SHA256_DATASET" in fuente
    assert "zip_fuente.close()" in fuente
