"""Punto de entrada de AWS Lambda.

La función se expone con una URL de función (autenticación AWS_IAM) que solo CloudFront puede
firmar; el sitio la llama en el mismo dominio bajo `/api/`:

- `GET /api/reentrenar`             ajusta E_JK con las 138 parcelas conocidas y estima las 59.
- `GET /api/reentrenar?formato=csv` lo mismo, como `predicciones_59.csv`.
- `GET /api/salud`                  versiones e insumos verificados, sin reentrenar.

Cada llamada a `/api/reentrenar` vuelve a ajustar el modelo; no hay caché de resultados.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import time

import numpy as np
import pandas as pd

from . import datos as _datos
from . import recetas

log = logging.getLogger()
log.setLevel(logging.INFO)

_DATOS: _datos.Datos | None = None
_EN_FRIO = True  # la primera invocación de cada contenedor arranca en frío


def _cargar() -> _datos.Datos:
    global _DATOS
    if _DATOS is None:
        _DATOS = _datos.cargar()
    return _DATOS


def reentrenar(d: _datos.Datos | None = None) -> dict:
    """Ajusta E_JK con las 138 parcelas conocidas y estima las 59, como la sección 7 del cuaderno 04."""
    d = d or _cargar()
    t0 = time.perf_counter()
    pred, info = recetas.ajustar(d.T, d.y, d.FX, d.ETIQUETADAS, d.OCULTAS,
                                 recetas.internas(d.ETIQUETADAS, recetas.SEMILLA_FINAL))
    segundos = time.perf_counter() - t0
    tabla = pd.DataFrame(pred, index=pd.Index(d.OCULTAS, name=recetas.ID))
    csv = recetas.csv_entrega(tabla)
    sha = hashlib.sha256(csv.encode()).hexdigest()
    esperado = d.manifiesto["esperado"]["predicciones_59.csv"]["sha256"]
    return {
        "modelo": "E_JK = 0.5*J + 0.5*K",
        "parcelas_entrenamiento": int(len(d.ETIQUETADAS)),
        "parcelas_estimadas": int(len(d.OCULTAS)),
        "semilla_interna_K": recetas.SEMILLA_FINAL,
        "K": {k: (int(v) if k == "n_ajuste" else float(v)) for k, v in info["K"].items()},
        "J_variable": str(info["J_variable"]),
        "J_coeficientes": {str(k): float(v) for k, v in info["J_coef"].items()},
        "segundos_ajuste": round(segundos, 4),
        "csv_sha256": sha,
        "esperado_sha256": esperado,
        "coincide": sha == esperado,
        "csv": csv,
        "predicciones": [
            {"id": str(i), **{m: float(tabla.at[i, m]) for m in ["E_JK", "J", "K", "MIX", "MUN"]}}
            for i in tabla.index
        ],
    }


def _respuesta(estado: int, cuerpo, tipo="application/json; charset=utf-8", extra=None, head=False):
    texto = cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo, ensure_ascii=False)
    cabeceras = {"Content-Type": tipo, "Cache-Control": "no-store"}
    cabeceras.update(extra or {})
    return {"statusCode": estado, "headers": cabeceras, "body": "" if head else texto, "isBase64Encoded": False}


def _salud() -> dict:
    d = _cargar()
    return {
        "estado": "ok",
        "insumos_verificados": len(d.manifiesto["insumos"]),
        "commit": d.manifiesto.get("commit"),
        "empaquetado": d.manifiesto.get("generado"),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "region": os.environ.get("AWS_REGION"),
    }


def handler(event, context):
    global _EN_FRIO
    en_frio, _EN_FRIO = _EN_FRIO, False
    ruta = (event.get("rawPath") or "/").rstrip("/") or "/"
    metodo = event.get("requestContext", {}).get("http", {}).get("method", "GET").upper()
    qs = event.get("queryStringParameters") or {}
    head = metodo == "HEAD"
    if metodo not in ("GET", "HEAD"):
        return _respuesta(405, {"error": "Solo se aceptan GET y HEAD."}, extra={"Allow": "GET, HEAD"})
    try:
        if ruta.endswith("/salud"):
            return _respuesta(200, {**_salud(), "arranque_en_frio": en_frio}, head=head)
        if ruta.endswith("/reentrenar"):
            r = reentrenar()
            log.info(json.dumps({"evento": "reentrenar", "coincide": r["coincide"], "segundos": r["segundos_ajuste"], "en_frio": en_frio}))
            if qs.get("formato") == "csv":
                return _respuesta(200, r["csv"], tipo="text/csv; charset=utf-8", head=head,
                                  extra={"Content-Disposition": 'attachment; filename="predicciones_59.csv"'})
            return _respuesta(200, {**r, "arranque_en_frio": en_frio}, head=head)
        return _respuesta(404, {"error": "Ruta no encontrada.", "rutas": ["/api/reentrenar", "/api/reentrenar?formato=csv", "/api/salud"]}, head=head)
    except _datos.InsumoAlterado as e:
        log.exception("insumo alterado")
        return _respuesta(500, {"error": f"Un insumo no coincide con su registro: {e}"}, head=head)
    except Exception:  # noqa: BLE001 — el detalle queda en CloudWatch, no en la respuesta
        log.exception("error al atender %s", ruta)
        return _respuesta(500, {"error": "Error interno al reentrenar; el detalle quedó en el registro de la función."}, head=head)
