"""Verifica el entorno del proyecto, sin leer datos ni entrenar modelos."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


CORE = {
    "numpy": "2.4.4",
    "pandas": "2.2.3",
    "scikit-learn": "1.9.1",
    "scipy": "1.18.0",
}
COMPLEMENTOS = (
    "matplotlib",
    "nbformat",
    "nbclient",
    "ipykernel",
    "jupyterlab",
    "rasterio",
    "shapely",
    "pyproj",
    "pyshp",  # La distribución pyshp proporciona el módulo shapefile.
    "gdown",
    "pytest",
    "ruff",
)


def verificar(completo: bool = False) -> dict:
    """Consulta metadatos instalados y hashes de configuración, no importa modelos."""
    proyecto = Path(__file__).resolve().parents[1]
    errores = []
    if sys.version_info[:2] != (3, 13):
        errores.append("Se requiere Python 3.13 para este entorno de referencia.")

    requeridos = dict(CORE)
    if completo:
        requeridos.update(dict.fromkeys(COMPLEMENTOS))
    paquetes = {}
    for nombre, esperada in requeridos.items():
        try:
            instalada = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            instalada = None
            errores.append(f"Falta la distribución {nombre}.")
        if instalada is not None and esperada is not None and instalada != esperada:
            errores.append(f"{nombre}: se esperaba {esperada}, se encontró {instalada}.")
        paquetes[nombre] = {"instalada": instalada, "esperada": esperada}

    hashes = {}
    for nombre in ("pyproject.toml", "uv.lock"):
        archivo = proyecto / nombre
        if archivo.is_file():
            hashes[nombre] = hashlib.sha256(archivo.read_bytes()).hexdigest()

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "proyecto": str(proyecto),
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "modo": "completo" if completo else "core",
        "paquetes": paquetes,
        "sha256": hashes,
        "correcto": not errores,
        "errores": errores,
        "alcance": "Presencia y versiones; no prueba Colab, datos, modelos ni despliegue.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--completo", action="store_true", help="Comprueba también los grupos de trabajo."
    )
    parser.add_argument(
        "--salida", type=Path, help="Guarda además el informe JSON en esta ruta explícita."
    )
    args = parser.parse_args()
    informe = verificar(args.completo)
    contenido = json.dumps(informe, ensure_ascii=False, indent=2) + "\n"
    if args.salida is not None:
        try:
            args.salida.write_text(contenido, encoding="utf-8")
        except OSError as error:
            parser.error(f"No se pudo escribir el informe: {error}")
    print(contenido, end="")
    return 0 if informe["correcto"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
