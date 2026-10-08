"""Autonomía, contratos de insumos y alcance de NB03 sin ejecutar un kernel."""

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
import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "construir_notebook_03", ROOT / "scripts/construir_notebook_03.py"
)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


@pytest.fixture(scope="module")
def notebook():
    protegidos = [
        ROOT / "scripts/colab_soporte.py",
        ROOT / "scripts/construir_notebook_01.py",
        ROOT / "scripts/construir_notebook_02.py",
    ]
    originales = {p: p.read_bytes() for p in protegidos}
    resultado = BUILDER.construir(ROOT)
    assert all(p.read_bytes() == contenido for p, contenido in originales.items())
    return resultado


def _celda(notebook, tag):
    celdas = [c for c in notebook.cells if tag in c.metadata.get("tags", [])]
    assert len(celdas) == 1
    return celdas[0]


def _literal(celda, nombre):
    for nodo in ast.parse(celda.source).body:
        if isinstance(nodo, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == nombre for t in nodo.targets
        ):
            return ast.literal_eval(nodo.value)
    raise AssertionError(f"No existe una constante literal llamada {nombre}.")


def _llamadas(source):
    return [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)]


def test_formato_valido_ids_estables_y_celdas_sin_ejecutar(notebook):
    nbformat.validate(notebook)
    assert len(notebook.cells) >= 30
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    assert all(re.fullmatch(r"referencias03-\d+", c.id) for c in notebook.cells)
    for c in notebook.cells:
        if c.cell_type == "code":
            ast.parse(c.source)
            assert c.execution_count is None and c.outputs == []
    registro = notebook.metadata.agrocebada
    assert registro.id == "REFERENCIAS_03" and registro.crisp_dm == [4, 5]
    assert registro.python_minor == "3.13" and registro.python_local == "3.13.13"
    assert registro.colab_real_probado is False
    assert registro.particiones_originales == "2026-09-20"
    assert registro.trabajo_original == "2026-09-21"
    assert registro.adaptacion == registro.verificacion_actual == "2026-10-07"
    assert registro.edicion_didactica == "2026-10-08"
    assert BUILDER.construir().metadata.agrocebada.id == "REFERENCIAS_03"


def test_puentes_visibles_con_calculo_contraste_y_fuentes_sin_mutacion(notebook):
    tags = ["particiones-calculo-visible", "referencias-calculo-visible", "oof-fila-visible",
            "metricas-calculo-visible", "agregacion-sintetica-visible", "escenario-mascara-visible"]
    assert len(notebook.cells) == 53
    codigos = [c for c in notebook.cells if c.cell_type == "code"]
    assert len(codigos) == 23
    for tag in tags:
        celda = _celda(notebook, tag)
        assert not celda.metadata.get("jupyter", {}).get("source_hidden", False)
        assert celda.metadata.get("cellView") != "form"
        assert "display(" in celda.source and "assert" in celda.source
        for node in ast.walk(ast.parse(celda.source)):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                assert node.id not in {"tabla138", "externas", "internas", "CONFIG", "oof", "metricas_full", "metricas_seen"}
    construir = _celda(notebook, "construir-oof").source
    assert "predicciones_visibles" not in construir and "filas_oof_visibles" not in construir
    texto = " ".join("\n".join(c.source for c in notebook.cells if c.cell_type == "markdown").split())
    for fragmento in ("todo el entrenamiento", "no solo el municipio", "salidas de control",
                      "no una cuarta", "ni borra decisiones adaptativas", "El piso de 1 m",
                      "no tiene que ser igual a GLOBAL", "sin reentrenar"):
        assert fragmento in texto


def test_referencia_manual_preserva_receta_y_no_abre_objetivo(notebook):
    manual = _celda(notebook, "referencias-calculo-visible").source
    assert 'objetivo_visible = tabla138.loc[tabla138.ID_POLIGONO.eq("AGC_001"),' in manual
    assert '["ID_POLIGONO", "Municipio", "x_m", "y_m"]' in manual
    assert 'assert "RENDIMIENTO_T_HA" not in objetivo_visible' in manual
    assert 'np.argsort(distancias_visibles)' in manual
    assert 'np.maximum(distancias_vecinos, receta_mix_visible["distancia_minima_m"])' in manual
    assert 'if len(y_municipio_visible) else global_visible' in manual
    assert manual.index('predicciones_visibles =') < manual.index('validacion.predecir_referencias(')
    assert "observado_demo" not in manual


def _validacion_module():
    spec = importlib.util.spec_from_file_location("validacion03_didactica", ROOT / "scripts/validacion_03.py")
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize("municipio,x_objetivo", [("A", 1.), ("N", 1.), ("A", 0.)])
def test_referencia_manual_ejecuta_municipio_nuevo_y_distancia_cero(notebook, municipio, x_objetivo):
    tabla = pd.DataFrame({"ID_POLIGONO": ["T1", "T2", "T3", "AGC_001"],
                          "Municipio": ["A", "A", "B", municipio], "x_m": [0., 3., 9., x_objetivo],
                          "y_m": [0., 0., 0., 0.], "RENDIMIENTO_T_HA": [1., 5., 8., 999.]})
    displays = []
    ns = {"pd": pd, "np": np, "tabla138": tabla, "ids_train_visible": {"T1", "T2", "T3"},
          "CONFIG": json.loads((ROOT / "config/validacion_03_recetas.json").read_text()),
          "validacion": _validacion_module(), "display": displays.append}
    source = _celda(notebook, "referencias-calculo-visible").source
    exec(compile(source, "<referencias-visibles>", "exec"), ns)
    assert len(displays) == 2 and len(ns["vecinos_visibles"]) == 3
    assert ns["global_visible"] == 14. / 3.
    assert ns["mun_visible"] == (3. if municipio == "A" else 14. / 3.)
    if x_objetivo == 0:
        assert ns["idw_visible"] != 1.  # El piso de 1 m no interpola exactamente.
    tabla.loc[tabla.ID_POLIGONO.eq("AGC_001"), "RENDIMIENTO_T_HA"] = -999.
    repetido = dict(ns)
    exec(compile(source, "<referencias-visibles-mutadas>", "exec"), repetido)
    assert repetido["predicciones_visibles"] == ns["predicciones_visibles"]


@pytest.mark.parametrize("constante", [False, True])
def test_metricas_visibles_ejecutan_y_respetan_r2_indefinido(notebook, constante):
    validacion = _validacion_module()
    observado = [2., 2., 2.] if constante else [1., 3., 5.]
    oof = pd.DataFrame([{"modelo": m, "ID_POLIGONO": f"P{i}", "repeticion": 0, "pliegue": 0,
                         "observado": y, "predicho": p}
                        for m in ("GLOBAL", "MUN", "MIX")
                        for i, (y, p) in enumerate(zip(observado, [2., 3., 3.], strict=True))])
    full = validacion.resumen_metricas(oof)
    salidas = []
    ns = {"np": np, "pd": pd, "oof": oof, "metricas_full": full, "display": salidas.append}
    exec(compile(_celda(notebook, "metricas-calculo-visible").source, "<metricas-visibles>", "exec"), ns)
    assert len(salidas) == 2
    if constante:
        assert ns["metricas_visibles"].R2.isna().all()
    else:
        assert ns["metricas_visibles"].R2.eq(.375).all()
        np.testing.assert_allclose(ns["metricas_visibles"].RMSE, np.sqrt(5 / 3), rtol=0, atol=1e-12)
        assert ns["metricas_visibles"].MAE.eq(1.).all()


def test_sintetico_promedios_cambia_objeto_sin_tocar_oof(notebook):
    ns = {"np": np, "pd": pd, "display": lambda *_: None}
    source = _celda(notebook, "agregacion-sintetica-visible").source
    assert 'oof' not in {n.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Name)}
    exec(compile(source, "<promedios-sinteticos>", "exec"), ns)
    assert ns["rmse_antes_promediar"] == 1. and ns["rmse_despues_promediar"] == 0.


def test_escenario_visible_usa_pertenencia_no_errores_ni_reajuste(notebook):
    source = _celda(notebook, "escenario-mascara-visible").source
    assert '["AGC_001", "AGC_048"]' in source
    assert 'visto_visible = n_municipales > 0' in source
    assert 'municipio_visto.eq(visto_visible)' in source
    for termino in ('predicho', 'observado', 'RENDIMIENTO_T_HA', 'predecir_referencias', 'construir_oof'):
        assert termino not in source


def test_modulos_embebidos_identidad_orden_y_loader_autonomo(notebook):
    celda = _celda(notebook, "modulos-tecnicos")
    modulos = _literal(celda, "FUENTES_MODULOS")
    assert (
        tuple(modulos)
        == BUILDER.MODULOS
        == ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite", "fuentes_02", "validacion_03")
    )
    for nombre, registro in modulos.items():
        original = (ROOT / "scripts" / f"{nombre}.py").read_bytes()
        assert registro["source"].encode() == original
        assert registro["sha256"] == hashlib.sha256(original).hexdigest()
        assert notebook.metadata.agrocebada.modulos_sha256[nombre] == registro["sha256"]
        ast.parse(registro["source"])
    assert "types.ModuleType" in celda.source and "sys.modules[nombre]" in celda.source
    assert '"<notebook03/"' in celda.source
    assert celda.source.index('hashlib.sha256(registro["source"]') < celda.source.index(
        "exec(compile("
    )
    assert "validar_recetas_referencias(CONFIG)" in celda.source
    assert celda.metadata.jupyter.source_hidden is True


def test_soporte_derivado_una_tupla_ocho_raices_y_guardas_intactas(notebook):
    original = (ROOT / "scripts/colab_soporte.py").read_text()
    derivado = BUILDER.derivar_soporte(original)
    celda = _celda(notebook, "soporte-colab")
    encabezado, cuerpo = celda.source.split("\n", 1)
    assert encabezado.startswith("# @title ")
    assert cuerpo == derivado
    assert (
        _literal(nbformat.v4.new_code_cell(original), "REQUERIDOS_AUDITORIA")
        == BUILDER.REQUERIDOS[:-1]
    )
    assert _literal(celda, "REQUERIDOS_AUDITORIA") == BUILDER.REQUERIDOS
    assert len(BUILDER.REQUERIDOS) == 8 and BUILDER.REQUERIDOS[-1] == "rasterio"
    assert derivado.replace(', "rasterio",\n)', ",\n)", 1) == original
    assert (ROOT / "scripts/colab_soporte.py").read_text() == original
    registro = notebook.metadata.agrocebada
    assert registro.soporte_base_sha256 == hashlib.sha256(original.encode()).hexdigest()
    assert registro.soporte_derivado_sha256 == hashlib.sha256(cuerpo.encode()).hexdigest()
    assert "ReinicioColabRequerido" in derivado and "--only-binary=:all:" in derivado
    assert "modulos_cargados" in derivado and "permitir_descarga" in derivado
    assert celda.metadata.jupyter.source_hidden is True
    with pytest.raises(ValueError, match="soporte compartido cambió"):
        BUILDER.derivar_soporte(original.replace("REQUERIDOS_AUDITORIA", "OTRA_TUPLA"))
    with pytest.raises(ValueError, match="soporte compartido cambió"):
        BUILDER.derivar_soporte(original + original)


def test_perfil_40_y_config_fija_hashes_y_preparacion_antes_fuentes(notebook):
    prep = _celda(notebook, "preparar-colab")
    perfil = (ROOT / "requirements-colab-auditoria.txt").read_text()
    assert _literal(prep, "REQUIREMENTS_COLAB") == perfil
    versiones = _literal(prep, "VERSIONES")
    assert set(versiones) == set(BUILDER.REQUERIDOS)
    assert len(dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s;]+)", perfil, re.MULTILINE))) == 40
    registro = notebook.metadata.agrocebada
    assert registro.perfil_colab_sha256 == hashlib.sha256(perfil.encode()).hexdigest()
    assert dict(registro.dependencias_requeridas) == versiones
    assert "PREPARAR_COLAB = True" in prep.source and "en_colab=EN_COLAB" in prep.source
    assert prep.source.index("sys.version_info[:2]") < prep.source.index("preparar_colab(")
    config = _celda(notebook, "config-recetas")
    original = (ROOT / "config/validacion_03_recetas.json").read_text()
    assert _literal(config, "CONFIG_JSON") == original
    assert registro.config_recetas_sha256 == hashlib.sha256(original.encode()).hexdigest()
    posiciones = {
        tag: next(i for i, c in enumerate(notebook.cells) if tag in c.metadata.get("tags", []))
        for tag in (
            "soporte-colab",
            "preparar-colab",
            "modulos-tecnicos",
            "acceso-dataset",
            "construir-oof",
        )
    }
    assert list(posiciones.values()) == sorted(posiciones.values())


def test_dataset_original_local_sin_red_y_etiquetas_solo_entrenamiento(notebook):
    contrato_path = ROOT / "config/auditoria_01_dataset.json"
    contrato = json.loads(contrato_path.read_text())
    acceso = _celda(notebook, "acceso-dataset")
    assert _literal(acceso, "ID_DRIVE_DATASET") == contrato["transporte"]["drive"]["file_id"]
    assert "DESCARGAR_DATASET = EN_COLAB" in acceso.source
    assert "bytes_esperados=29_687_194" in acceso.source
    assert "sha256_esperado=SHA256_DATASET" in acceso.source
    assert "permitir_descarga=DESCARGAR_DATASET" in acceso.source
    assert "fuentes02.cargar_fuentes(zip_fuente)" in acceso.source
    assert 'meta.CONJUNTO.eq("ENTRENAMIENTO")' in acceso.source
    assert 'meta.CONJUNTO.eq("PREDICCION"), ["ID_POLIGONO", "Municipio"]' in acceso.source
    assert 'validate="one_to_one"' in acceso.source
    registro = notebook.metadata.agrocebada
    assert registro.dataset_config_sha256 == hashlib.sha256(contrato_path.read_bytes()).hexdigest()
    assert (
        registro.dataset_sha256 == contrato["sha256"]
        and registro.dataset_bytes == contrato["bytes"]
    )


def test_cuatro_insumos_hash_bytes_y_uso_correctos(notebook):
    celda = _celda(notebook, "insumos-tecnicos")
    insumos = _literal(celda, "INSUMOS_INCRUSTADOS")
    config = json.loads((ROOT / "config/validacion_03_recetas.json").read_text())
    assert set(insumos) == {"externas", "internas", "oof_historico", "metricas_historicas"}
    assert len(celda.source.encode()) < 550_000
    for nombre, insumo in insumos.items():
        contenido = zlib.decompress(base64.b64decode(insumo["bytes_zlib_base64"], validate=True))
        contrato = config["insumos"][nombre]
        assert len(contenido) == insumo["bytes"] == contrato["bytes"]
        assert hashlib.sha256(contenido).hexdigest() == insumo["sha256"] == contrato["sha256"]
        assert contenido == (ROOT / contrato["ruta_local"]).read_bytes()
        assert insumo["uso"] == (
            "particiones" if nombre in {"externas", "internas"} else "control_de_salida"
        )
        assert dict(notebook.metadata.agrocebada.insumos[nombre]) == {
            k: insumo[k] for k in ("sha256", "bytes", "uso", "origen")
        }
    assert 'registro["bytes"] + 1' in celda.source
    assert celda.source.index("hashlib.sha256(contenido)") < celda.source.index("pd.read_csv(")
    assert celda.metadata.jupyter.source_hidden is True


def test_decoder_rechaza_uso_hash_tamano_y_datos_extra_antes_de_parsear(notebook):
    celda = _celda(notebook, "insumos-tecnicos")
    ns = {"base64": base64, "zlib": zlib, "hashlib": hashlib, "pd": pd, "io": io}
    exec(compile(celda.source, "<control-insumos>", "exec"), ns)
    assert ns["leer_insumo"]("externas", "particiones").shape == (6900, 4)
    assert ns["leer_insumo"]("internas", "particiones").shape == (22080, 5)
    assert ns["leer_insumo"]("oof_historico", "control_de_salida").shape[0] == 5520
    with pytest.raises(ValueError, match="uso solicitado"):
        ns["leer_insumo"]("oof_historico", "particiones")
    registros = ns["INSUMOS_INCRUSTADOS"]
    registros["externas"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256"):
        ns["leer_insumo"]("externas", "particiones")
    registros["internas"]["bytes"] -= 1
    with pytest.raises(ValueError, match="límite de bytes"):
        ns["leer_insumo"]("internas", "particiones")
    comprimido = base64.b64decode(registros["metricas_historicas"]["bytes_zlib_base64"])
    registros["metricas_historicas"]["bytes_zlib_base64"] = base64.b64encode(
        comprimido + b"extra"
    ).decode()
    with pytest.raises(ValueError, match="límite de bytes"):
        ns["leer_insumo"]("metricas_historicas", "control_de_salida")


def test_controles_de_salida_se_abren_despues_del_calculo_y_no_lo_alimentan(notebook):
    filas = [(i, c) for i, c in enumerate(notebook.cells) if c.cell_type == "code"]
    indice_calculo = next(i for i, c in filas if "construir-oof" in c.metadata.get("tags", []))
    indice_contraste = next(
        i for i, c in filas if "contraste-historico" in c.metadata.get("tags", [])
    )
    assert indice_calculo < indice_contraste
    for i, c in filas:
        if i != indice_contraste and "insumos-tecnicos" not in c.metadata.get("tags", []):
            assert "oof_control" not in c.source and "metricas_control" not in c.source
        for llamada in _llamadas(c.source):
            if isinstance(llamada.func, ast.Name) and llamada.func.id == "leer_insumo":
                nombre = ast.literal_eval(llamada.args[0])
                assert (nombre in {"externas", "internas"} and i < indice_calculo) or (
                    nombre in {"oof_historico", "metricas_historicas"} and i == indice_contraste
                )
            if isinstance(llamada.func, ast.Attribute) and llamada.func.attr == "construir_oof":
                assert [n.id for n in llamada.args] == ["tabla138", "externas"]
            if (
                isinstance(llamada.func, ast.Attribute)
                and llamada.func.attr == "predecir_referencias"
            ):
                assert all(
                    not isinstance(n, ast.Name)
                    or n.id not in {"ocultas", "oof_control", "metricas_control"}
                    for n in llamada.args
                )
    contraste = _celda(notebook, "contraste-historico").source
    assert "ALIAS_HISTORICOS_03" in contraste and "comparar_oof(oof, oof_control" in contraste
    assert "n_parcelas.eq(metricas_control.n_parcelas)" in contraste
    assert "n_oof.eq(metricas_control.n_oof)" in contraste
    assert "diferencia_absoluta.le(1e-8)" in contraste


def test_parcela_apartada_y_doble_control_invariancia(notebook):
    ejemplo = _celda(notebook, "parcela-apartada").source
    assert _literal(_celda(notebook, "parcela-apartada"), "PARCELA") == "AGC_001"
    assert 'externas.ID_POLIGONO.eq(PARCELA) & externas.rol.eq("validacion")' in ejemplo
    assert 'drop(columns="RENDIMIENTO_T_HA")' in ejemplo
    assert "PARCELA not in set(a_demo.ID_POLIGONO)" in ejemplo
    assert ejemplo.index("pred_demo = validacion.predecir_referencias") < ejemplo.index(
        "observado_demo ="
    )
    control = _celda(notebook, "invariancia-validacion").source
    assert "a_sintetico" in control and "t_sintetico" in control
    assert "assign(RENDIMIENTO_T_HA=-999.)" in control
    assert "t_demo.assign(RENDIMIENTO_T_HA=12345.)" in control
    assert "assert_array_equal" in control and "[3., 14. / 3.]" in control


def test_no_algoritmos_nuevos_exportacion_rasteres_o_red_fuera_soporte(notebook):
    prohibidas = {
        "fit",
        "predict",
        "fit_predict",
        "fit_transform",
        "train_test_split",
        "GridSearchCV",
        "RandomizedSearchCV",
        "to_csv",
        "to_excel",
        "to_pickle",
        "to_file",
        "extractall",
        "kill",
        "ensamblar_variables",
        "construir_satelite",
        "extraer_clima",
        "extraer_topografia",
    }
    modulos_prohibidos = {"sklearn", "xgboost", "lightgbm", "catboost", "requests"}
    modulos = [
        r["source"]
        for r in _literal(_celda(notebook, "modulos-tecnicos"), "FUENTES_MODULOS").values()
    ]
    sources = [
        (c.source, "soporte-colab" in c.metadata.get("tags", []))
        for c in notebook.cells
        if c.cell_type == "code"
    ]
    sources.extend((source, False) for source in modulos)
    for source, soporte in sources:
        assert "/home/netfoor/" not in source and "ObsidianVault" not in source
        for nodo in ast.walk(ast.parse(source)):
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                names = (
                    [a.name for a in nodo.names]
                    if isinstance(nodo, ast.Import)
                    else [nodo.module or ""]
                )
                assert all(n.split(".")[0] not in modulos_prohibidos for n in names)
                if not soporte:
                    assert all(n.split(".")[0] != "gdown" for n in names)
            if isinstance(nodo, ast.Call):
                nombre = getattr(nodo.func, "attr", getattr(nodo.func, "id", ""))
                # Las funciones de extracción existen en fuentes02; no se llaman en las celdas de NB03.
                if source not in modulos:
                    assert nombre not in prohibidas
                else:
                    assert nombre not in prohibidas - {
                        "ensamblar_variables",
                        "construir_satelite",
                        "extraer_clima",
                        "extraer_topografia",
                    }
                if nombre == "download":
                    assert soporte


def test_mismos_errores_oof_escenarios_y_cierre_estricto(notebook):
    calcular = _celda(notebook, "construir-oof").source
    assert "len(oof) == 4140" in calcular and "size().eq(1380)" in calcular
    full = _celda(notebook, "metricas-full").source
    assert 'resumen_metricas(oof, escenario="FULL138")' in full
    assert 'sort_values("R2", ascending=False)' in full
    assert "habilidad_vs_media_train, 0." in full
    seen = _celda(notebook, "escenarios-full-seen").source
    assert 'resumen_metricas(oof, escenario="SEEN135")' in seen
    assert "oof.loc[oof.municipio_visto]" in seen
    assert "n_parcelas.eq(135)" in seen and "n_oof.eq(1350)" in seen
    assert '{"AGC_047", "AGC_048", "AGC_164"}' in seen
    assert "len(removidas) == 30" in seen and '["AGC_048", "AGC_120"]' in seen
    cierre = _celda(notebook, "cierre-verificable").source
    assert "RESUMEN_REFERENCIAS_03_JSON=" in cierre
    assert "hash_final == hash_inicial == SHA256_DATASET" in cierre
    assert '"fecha_ejecucion_utc": FECHA_EJECUCION_UTC' in cierre
    for field in (
        "parcelas",
        "etiquetas",
        "por_predecir",
        "repeticiones",
        "pliegues_externos",
        "pliegues_internos",
        "referencias",
        "oof_por_referencia",
        "oof_total",
        "parcelas_seen",
        "oof_seen_por_referencia",
        "sha256_dataset",
        "referencias_reproducidas",
        "ajustes_referencia",
    ):
        assert f'"{field}"' in cierre
    for field in (
        "modelos_nuevos",
        "hiperparametros_seleccionados",
        "predicciones_finales_generadas",
        "tablas_exportadas",
    ):
        assert f'"{field}": 0' in cierre
    assert '"modelos_entrenados": 0' not in cierre
    assert "zip_fuente.close()" in cierre


def test_narrativa_limites_formulas_fuentes_y_tres_figuras(notebook):
    texto = "\n".join(c.source for c in notebook.cells if c.cell_type == "markdown")
    assert len(re.findall(r"^## \d+\.", texto, re.MULTILINE)) == 11
    for fragmento in (
        "150 ajustes",
        "138 parcelas",
        "no 1,380 casos independientes",
        "no estratificado",
        "No conocemos",
        "No reajustamos",
        "no constituyen un preregistro",
        "dos evidencias predictivas independientes",
        "MAE sí puede preferir MUN",
        "no una ecuación oficial",
        "automáticamente un error de extracción",
        "No promediamos",
        "SEEN135",
        "AGC_120",
        "una sola etiqueta",
        "p-valores",
    ):
        assert fragmento in texto
    for url in (
        "https://scikit-learn.org/stable/modules/cross_validation.html",
        "https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics",
        "https://www.jmlr.org/papers/v11/cawley10a.html",
    ):
        assert url in texto
    assert "2079–2107" in texto
    assert "07T1" not in texto and "split estratificado" not in texto
    assert sum("plt.subplots(" in c.source for c in notebook.cells if c.cell_type == "code") == 3


def test_cli_exige_salida_y_no_sobrescribe_ni_construye_si_existe(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["construir_notebook_03.py"])
    with pytest.raises(SystemExit) as falta:
        BUILDER.main()
    assert falta.value.code == 2
    existente = ROOT / "scripts/construir_notebook_03.py"
    original = existente.read_bytes()
    monkeypatch.setattr(sys, "argv", ["construir_notebook_03.py", "--salida", str(existente)])
    monkeypatch.setattr(
        BUILDER,
        "construir",
        lambda *args: pytest.fail("No debe construir antes de rechazar overwrite"),
    )
    with pytest.raises(ValueError, match="no se sobrescribe"):
        BUILDER.main()
    assert existente.read_bytes() == original


def test_colab_pliega_solo_las_tres_celdas_tecnicas_y_mantiene_codigo_inspeccionable(notebook):
    tecnicas = {"soporte-colab", "modulos-tecnicos", "insumos-tecnicos"}
    plegadas = []
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        if tecnicas.intersection(cell.metadata.get("tags", [])):
            encabezado, cuerpo = cell.source.split("\n", 1)
            assert re.fullmatch(r'# @title .+ \{ display-mode: "form" \}', encabezado)
            assert cell.metadata.cellView == "form"
            assert cell.metadata.jupyter.source_hidden is True
            assert not cuerpo.startswith("# @title ")
            compile(cuerpo, "<cuerpo-tecnico>", "exec")
            plegadas.append(cell)
        else:
            assert not cell.source.startswith("# @title ")
            assert cell.metadata.get("cellView") != "form"
            assert cell.metadata.get("jupyter", {}).get("source_hidden") is not True
    assert len(plegadas) == 3
    assert "«Mostrar código»" in "\n".join(
        c.source for c in notebook.cells if c.cell_type == "markdown"
    )


def test_formulario_colab_preserva_cuerpo_literal_y_ast_del_bootstrap(notebook):
    original = (ROOT / "scripts/colab_soporte.py").read_text(encoding="utf-8")
    derivado = BUILDER.derivar_soporte(original)
    encabezado, cuerpo = _celda(notebook, "soporte-colab").source.split("\n", 1)
    assert encabezado.startswith("# @title ")
    assert cuerpo.encode("utf-8") == derivado.encode("utf-8")
    assert ast.dump(ast.parse(cuerpo), include_attributes=False) == ast.dump(
        ast.parse(derivado), include_attributes=False
    )
    assert (
        notebook.metadata.agrocebada.soporte_derivado_sha256
        == hashlib.sha256(cuerpo.encode("utf-8")).hexdigest()
    )
