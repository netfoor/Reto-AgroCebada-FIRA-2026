"""Comprueba, sin AWS, que la API reproduce la entrega.

Ejecutar desde la raíz del repositorio:

    uv run python api/verificar.py

Reúne los insumos como lo hace `empaquetar.py`, invoca el handler con un evento igual al que
manda la URL de la función y exige que el CSV reentrenado tenga la misma SHA-256 que
`resultados/04_seleccion_modelo_final/predicciones_59.csv`.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

import empaquetar  # noqa: E402
from agrocebada_api import datos, handler  # noqa: E402


def evento(ruta: str, consulta: dict | None = None) -> dict:
    return {"version": "2.0", "rawPath": ruta, "queryStringParameters": consulta,
            "requestContext": {"http": {"method": "GET", "path": ruta}}}


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp) / "insumos"
        empaquetar.reunir_insumos(carpeta)
        handler._DATOS = datos.cargar(carpeta)  # la Lambda los carga de su propia carpeta

        r = handler.handler(evento("/api/reentrenar"), None)
        assert r["statusCode"] == 200, r
        cuerpo = json.loads(r["body"])
        assert cuerpo["coincide"], f"SHA-256 distinta: {cuerpo['csv_sha256']} ≠ {cuerpo['esperado_sha256']}"
        assert cuerpo["J_variable"] == "anom_precip_pct_d" and cuerpo["K"]["beta"] < 0

        c = handler.handler(evento("/api/reentrenar", {"formato": "csv"}), None)
        assert c["statusCode"] == 200 and c["body"] == empaquetar.ENTREGA.read_text(encoding="utf-8")
        s = handler.handler(evento("/api/salud"), None)
        assert s["statusCode"] == 200 and json.loads(s["body"])["insumos_verificados"] == len(datos.CLAVES)
        assert handler.handler(evento("/api/otra"), None)["statusCode"] == 404

        print(f"Reentrenado con {cuerpo['parcelas_entrenamiento']} parcelas en {cuerpo['segundos_ajuste']:.2f} s")
        print(f"β de K = {cuerpo['K']['beta']:+.4f}; J eligió {cuerpo['J_variable']}")
        print(f"CSV de las {cuerpo['parcelas_estimadas']} estimaciones: sha256 {cuerpo['csv_sha256'][:16]}… idéntico a la entrega")


if __name__ == "__main__":
    main()
