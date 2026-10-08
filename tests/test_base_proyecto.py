"""Controles de la base documental y del entorno; no utilizan datos agrícolas."""

import json
import re
import tomllib
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def configuracion():
    with (RAIZ / "pyproject.toml").open("rb") as archivo:
        return tomllib.load(archivo)


def test_python_y_versiones_de_referencia():
    proyecto = configuracion()["project"]
    rango = proyecto["requires-python"].replace(" ", "")
    assert ">=3.13" in rango and "<3.14" in rango
    assert (RAIZ / ".python-version").read_text().strip() == "3.13.13"
    assert configuracion()["tool"]["ruff"]["target-version"] == "py313"
    dependencias = {valor.replace(" ", "") for valor in proyecto["dependencies"]}
    assert {"numpy==2.4.4", "pandas==2.2.3", "scikit-learn==1.9.1"} <= dependencias
    assert any(re.match(r"scipy(?:[<>=!~]|$)", valor) for valor in dependencias)


def test_grupos_sin_stack_de_produccion_ni_nuevas_familias():
    config = configuracion()
    grupos = config["dependency-groups"]
    assert {"notebooks", "geo", "colab", "dev"} <= set(grupos)
    declaradas = list(config["project"]["dependencies"])
    for grupo in grupos.values():
        declaradas.extend(valor for valor in grupo if isinstance(valor, str))
    nombres = {re.split(r"[\[<>=!~; ]", valor, maxsplit=1)[0].lower() for valor in declaradas}
    no_autorizadas = {
        "fastapi", "flask", "django", "starlette", "uvicorn", "sanic",
        "xgboost", "lightgbm", "catboost", "tensorflow", "torch",
    }
    assert not (nombres & no_autorizadas)


def test_catalogo_conserva_identidad_y_migra_tres_lectores_sin_ajustes():
    indice = json.loads((RAIZ / "config/indice_experimentos.json").read_text())
    experimentos = indice["experimentos"]
    assert len(experimentos) == 6
    assert [experimento["id_historico"] for experimento in experimentos] == [
        f"AGC-EXP-{nombre}" for nombre in ("RONDA1", "T1", "V1", "V2", "V3", "V4")
    ]
    assert [experimento["alias"] for experimento in experimentos] == [
        "exp_01_bloques", "exp_02_ponderacion_temporal", "exp_03_variables_y_familias",
        "exp_04_lluvia_octubre", "exp_05_historico_octubre", "exp_06_pico_soportado",
    ]
    primero = experimentos[0]
    assert primero["estado_migracion"] == "lector_verificado_sin_reentrenar"
    assert primero["fecha_trabajo_segun_fuente_mexico"] == "2026-09-21"
    assert primero["fecha_catalogacion"] == "2026-10-07"
    assert primero["fecha_adaptacion"] == "2026-10-08"
    assert primero["ruta_cuaderno"] == (
        "notebooks/experimentos/exp_01_bloques/exp_01_bloques.ipynb"
    )
    assert primero["estado_predictivo"] == "cerrado_sin_adopcion"
    segundo = experimentos[1]
    assert segundo["estado_migracion"] == "lector_verificado_sin_reentrenar"
    assert segundo["fecha_trabajo_segun_fuente_mexico"] == "2026-09-29"
    assert segundo["fecha_catalogacion"] == "2026-10-07"
    assert segundo["fecha_adaptacion"] == "2026-10-08"
    assert segundo["ruta_cuaderno"] == (
        "notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb"
    )
    assert segundo["estado_predictivo"] == "cerrado_sin_adopcion"
    tercero = experimentos[2]
    assert tercero["estado_migracion"] == "lector_verificado_sin_reentrenar"
    assert tercero["fecha_trabajo_segun_fuente_mexico"] == "2026-09-29"
    assert tercero["fecha_catalogacion"] == "2026-10-07"
    assert tercero["fecha_adaptacion"] == "2026-10-08"
    assert tercero["ruta_cuaderno"] == (
        "notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb"
    )
    assert tercero["modalidad_cuaderno_fuente"] == "ejecutable_con_ajustes_no_presentar_como_lector"
    assert tercero["modo_futuro_por_defecto"] == "lector_sin_ajustes"
    assert tercero["estado_predictivo"] == "cerrado_sin_adopcion"
    assert all(experimento["estado_migracion"] == "pendiente" for experimento in experimentos[3:])
    assert indice["experimentos_copiados"] == 3
    assert indice["ajustes_al_catalogar"] == 0
    assert indice["fecha_corte"] == "2026-10-08"


def test_manifest_de_insumos_no_activa_descargas():
    manifest = json.loads((RAIZ / "config/insumos.example.json").read_text())
    assert manifest["estado"] == "pendiente"
    assert manifest["assets"] == []


def test_documentacion_y_verificacion_presentes():
    archivos = (
        "README.md",
        "docs/01_contexto_y_estado.md",
        "docs/02_metodologia.md",
        "docs/03_plan_de_trabajo.md",
        "docs/04_notebooks_y_colab.md",
        "notebooks/README.md",
        "notebooks/experimentos/exp_02_ponderacion_temporal/README.md",
        "notebooks/experimentos/exp_03_variables_y_familias/README.md",
        "scripts/verificar_entorno.py",
    )
    for nombre in archivos:
        archivo = RAIZ / nombre
        assert archivo.is_file(), nombre
        assert archivo.stat().st_size > 0, nombre
