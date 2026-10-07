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


def test_catalogo_conserva_identidad_y_no_declara_migraciones():
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
    assert all(experimento["estado_migracion"] == "pendiente" for experimento in experimentos)


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
        "scripts/verificar_entorno.py",
    )
    for nombre in archivos:
        archivo = RAIZ / nombre
        assert archivo.is_file(), nombre
        assert archivo.stat().st_size > 0, nombre
