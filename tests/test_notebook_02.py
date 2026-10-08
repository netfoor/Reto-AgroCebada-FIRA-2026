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
import numpy as np
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
    cabecera, salto, cuerpo = celda.source.partition("\n")
    assert cabecera.startswith("# @title ") and '{ display-mode: "form" }' in cabecera
    assert salto == "\n" and cuerpo == derivado
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


def test_bloques_tecnicos_plegados_en_colab_sin_alterar_cuerpo(notebook):
    tags_tecnicos = {"soporte-colab", "modulos-tecnicos", "referencias-tecnicas"}
    encontradas = set()
    for celda in notebook.cells:
        tags = set(celda.metadata.get("tags", [])) & tags_tecnicos
        if tags:
            assert len(tags) == 1
            encontradas.update(tags)
            assert celda.metadata.cellView == "form"
            assert celda.metadata.jupyter.source_hidden is True
            titulo, salto, cuerpo = celda.source.partition("\n")
            assert titulo.startswith("# @title ")
            assert titulo.endswith('{ display-mode: "form" }') and salto == "\n"
            assert len(titulo) < 160
            ast.parse(cuerpo)
            assert ast.dump(ast.parse(celda.source)) == ast.dump(ast.parse(cuerpo))
    assert encontradas == tags_tecnicos


def test_codigo_didactico_permanece_visible_y_sin_formulario(notebook):
    visibles = [c for c in notebook.cells if c.cell_type == "code"
                and not c.metadata.get("jupyter", {}).get("source_hidden")]
    assert len(visibles) == 25
    for celda in visibles:
        assert "cellView" not in celda.metadata
        assert not celda.source.startswith("# @title ")


def test_puentes_tienen_calculo_contraste_y_permanecen_visibles(notebook):
    tags = ["geometria-calculo-visible", "afin-interseccion-visible", "satelite-calculo-visible",
            "lai-calidad-visible", "tiempo-calculo-visible", "lluvia-calculo-visible",
            "nodata-calculo-visible", "clima-tiempo-visible", "topografia-calculo-visible",
            "union-calculo-visible"]
    for tag in tags:
        celda = _celda(notebook, tag)
        assert celda.cell_type == "code"
        assert not celda.metadata.get("jupyter", {}).get("source_hidden", False)
        assert "display(" in celda.source
        assert "assert" in celda.source
        tree = ast.parse(celda.source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                assert node.id not in {"etiquetas", "referencia_base", "referencia_postciclo"}
                if isinstance(node.ctx, ast.Store):
                    assert node.id not in {"CONFIG", "meta", "basico", "pro", "geoms", "tabla_base"}
    texto = "\n".join(c.source for c in notebook.cells if c.cell_type == "markdown")
    assert "contraste aritmético" in texto
    assert "no una reimplementación independiente" in texto
    assert "no agregan variables" in texto
    for modulo in ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite", "fuentes_02"):
        assert f"`{modulo}`" in texto


def test_operaciones_geometricas_explicitas_no_desplazan_malla(notebook):
    geo = _celda(notebook, "geometria-calculo-visible").source
    assert "always_xy=True" in geo and ".area / 10_000" in geo and ".centroid" in geo
    afin = _celda(notebook, "afin-interseccion-visible").source
    assert "a * columna + b * fila + c, d * columna + e * fila + f" in afin
    assert "col_pixel + .5, fila_pixel + .5" in afin
    assert "parcela_en_raster.intersection(pixel_manual)" in afin
    lluvia = _celda(notebook, "lluvia-calculo-visible").source
    assert '[PARCELA, "AGC_051"]' in lluvia
    assert 'transformar_geometria(transformar_utm, p["interseccion"]).area' in lluvia
    assert 'piezas_validas.area_m2 / area_valida' in lluvia
    assert 'control_lluvia["pond"]' in lluvia


def test_filtros_y_denominador_lai_se_explican_sin_cambiar_receta(notebook):
    sat = _celda(notebook, "satelite-calculo-visible").source
    assert 'pro_uno.sensor.eq("Planet")' in sat
    assert '.FECHA.between(inicio_ciclo, fin_ciclo)' in sat
    assert 'if umbral_nube_planet is not None:' in sat
    assert 'dropna(subset=["ndvi_promedio"])' in sat
    assert 'planet_ndvi.ndvi_std.mean()' in sat
    lai = _celda(notebook, "lai-calidad-visible").source
    assert 's2_para_bandera = s2_admitidas.dropna(subset=["ndvi_promedio"])' in lai
    assert 'lai_negativos / len(s2_para_bandera)' in lai
    assert 's2_admitidas.lai_promedio.dropna().mean()' in lai
    assert '.clip(' not in sat + lai and '.fillna(' not in sat + lai


def test_tiempo_visible_conserva_huecos_y_meses_ausentes(notebook):
    tiempo = _celda(notebook, "tiempo-calculo-visible").source
    assert '.reindex(meses_ciclo)' in tiempo
    assert '.sum(min_count=len(meses_ciclo))' in tiempo
    assert 'tramos.dias.gt(0) & tramos.dias.le(CONFIG["integral_hueco_max_dias"])' in tiempo
    assert 'planet_ndvi.groupby("FECHA", as_index=False).ndvi_promedio.mean()' in tiempo
    assert 'if len(admitidos) else np.nan' in tiempo
    clima = _celda(notebook, "clima-tiempo-visible").source
    assert 'prec.sum(min_count=len(meses_numeros))' in clima
    assert 'tmin_por_dias.sum(min_count=len(meses_numeros))' in clima
    assert '.dropna(' not in tiempo + clima and '.fillna(' not in tiempo + clima


def test_nodata_sintetico_y_dispersion_poblacional_sin_imputar_fuentes(notebook):
    demo = _celda(notebook, "nodata-calculo-visible").source
    assert 'pd.DataFrame({"valor": [10., np.nan, 30.], "area": [1., 2., 1.]})' in demo
    assert 'media_valida_sintetica == 20. and media_cero_erronea == 10.' in demo
    assert '.fillna(0)' in demo  # Solo contraejemplo sintético, no la extracción.
    assert "rasters" not in demo and "clima_uno" not in demo
    topo = _celda(notebook, "topografia-calculo-visible").source
    assert '(elev_visible.valor - media_elev_visible) ** 2' in topo
    assert 'np.sqrt(varianza_elev_visible)' in topo
    assert 'area_elev_valida / piezas_elev["area_malla"]' in topo
    assert 'area_elev_valida / piezas_elev["area_parcela"]' in topo


def test_union_visible_es_por_clave_y_no_alimenta_base(notebook):
    union = _celda(notebook, "union-calculo-visible").source
    assert 'on="ID_POLIGONO", how="left", validate="one_to_one"' in union
    assert 'pd.testing.assert_frame_equal(' in union
    assert 'tabla_base.set_index("ID_POLIGONO").loc[[PARCELA]' in union
    ensamblar = _celda(notebook, "ensamblar-197").source
    assert "fila_visible" not in ensamblar
    for nombre in ("stats_manuales", "mensual_visible", "lluvia_visible", "stats_elev_visibles"):
        assert nombre not in ensamblar


@pytest.mark.parametrize("mes_ausente", [False, True])
def test_clima_visible_compara_numeros_en_tabla_mixta_y_propaga_nan(notebook, mes_ausente):
    meses = pd.period_range("2025-04", "2025-10", freq="M")
    largo = pd.DataFrame([
        {"anio": 2025, "mes": mes, "variable": variable,
         "pond": np.nan if mes_ausente and mes == 6 else valor}
        for mes in meses.month for variable, valor in (("prec", 10.), ("tmin", 5.), ("tmax", 20.))
    ])
    clima = pd.DataFrame({"clim_prec_ciclo_mm": [np.nan if mes_ausente else 70.],
                          "clim_tmin_ciclo_C": [np.nan if mes_ausente else 5.],
                          "control_celda": ["R37_C27"]}, index=["AGC_001"])
    salidas = []
    ns = {"pd": pd, "np": np, "meses_ciclo": meses, "inicio_ciclo": pd.Timestamp("2025-04-01"),
          "clima_uno_largo": largo, "clima_uno": clima, "PARCELA": "AGC_001", "display": salidas.append}
    exec(compile(_celda(notebook, "clima-tiempo-visible").source, "<clima-visible>", "exec"), ns)
    assert len(salidas) == 2
    if mes_ausente:
        assert np.isnan(ns["lluvia_ciclo_visible"]) and np.isnan(ns["tmin_ciclo_visible"])
    else:
        assert ns["lluvia_ciclo_visible"] == 70. and ns["tmin_ciclo_visible"] == 5.


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
