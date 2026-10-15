"""Pruebas de la API: `uv run pytest api/tests` desde la raíz del repositorio."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

import empaquetar  # noqa: E402
from agrocebada_api import datos, handler  # noqa: E402


def evento(ruta, consulta=None, metodo="GET"):
    return {"version": "2.0", "rawPath": ruta, "queryStringParameters": consulta,
            "requestContext": {"http": {"method": metodo, "path": ruta}}}


@pytest.fixture(scope="module")
def carpeta(tmp_path_factory):
    c = tmp_path_factory.mktemp("insumos")
    empaquetar.reunir_insumos(c)
    handler._DATOS = datos.cargar(c)
    return c


def test_reentrenar_reproduce_la_entrega(carpeta):
    cuerpo = json.loads(handler.handler(evento("/api/reentrenar"), None)["body"])
    assert cuerpo["coincide"] and cuerpo["csv_sha256"] == cuerpo["esperado_sha256"]
    assert cuerpo["parcelas_entrenamiento"] == 138 and len(cuerpo["predicciones"]) == 59
    assert all(abs(p["E_JK"] - 0.5 * (p["J"] + p["K"])) < 1e-12 for p in cuerpo["predicciones"])


def test_csv_igual_al_archivo(carpeta):
    r = handler.handler(evento("/api/reentrenar", {"formato": "csv"}), None)
    assert r["headers"]["Content-Type"].startswith("text/csv")
    assert r["body"] == empaquetar.ENTREGA.read_text(encoding="utf-8")


def test_insumo_alterado_detiene_la_carga(carpeta, tmp_path):
    copia = tmp_path / "insumos"
    empaquetar.reunir_insumos(copia)
    archivo = copia / "etiquetas.csv"
    contenido = bytearray(archivo.read_bytes())
    contenido[-2] = ord("9") if contenido[-2] != ord("9") else ord("8")  # cambia un dígito del último rendimiento
    archivo.write_bytes(bytes(contenido))
    with pytest.raises(datos.InsumoAlterado):
        datos.cargar(copia)


def test_metodos_y_rutas(carpeta):
    assert handler.handler(evento("/api/reentrenar", metodo="POST"), None)["statusCode"] == 405
    assert handler.handler(evento("/api/nada"), None)["statusCode"] == 404
    assert handler.handler(evento("/api/salud", metodo="HEAD"), None)["body"] == ""
