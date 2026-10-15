"""Arma el paquete de la Lambda: código, insumos verificados y dependencias para arm64.

Ejecutar desde la raíz del repositorio:

    uv run python api/empaquetar.py

Resultado: `api/dist/agrocebada_api.zip`, que Terraform sube como código de la función.

- Los insumos se toman de las rutas de `config/04_seleccion_modelo_final.json`. La carpeta
  `data/` no se publica en GitHub; en un clon sin ella se extraen de la copia que el cuaderno 04
  lleva incrustada. En ambos casos se verifican con su SHA-256, y la Lambda vuelve a verificarlos.
- Las dependencias salen de `api/uv.lock` (las mismas versiones de numpy y pandas que el
  repositorio) y se instalan con `uv pip install --target` para Linux arm64 y Python 3.13.
- El ZIP es determinista: mismas entradas producen el mismo archivo y Terraform no redespliega.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = Path(os.environ.get("AGRO_REPO", API.parent)).resolve()
BUILD = API / "build"
PAQUETE = BUILD / "paquete"
DIST = API / "dist"
ZIP = DIST / "agrocebada_api.zip"
CONFIG = REPO / "config/04_seleccion_modelo_final.json"
RESUMEN = REPO / "resultados/04_seleccion_modelo_final/resumen.json"
ENTREGA = REPO / "resultados/04_seleccion_modelo_final/predicciones_59.csv"
CUADERNO = REPO / "notebooks/04_seleccion_modelo_final.ipynb"
PLATAFORMA = os.environ.get("AGRO_PLATAFORMA", "aarch64-manylinux_2_28")  # Lambda arm64 (Graviton), Amazon Linux 2023
PYTHON = "3.13"
LIMITE_DESCOMPRIMIDO = 250 * 1024 * 1024  # límite de Lambda para paquetes .zip

sys.path.insert(0, str(API))
from agrocebada_api.datos import CLAVES  # noqa: E402


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def commit() -> str | None:
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def insumos_del_cuaderno() -> dict:
    """Insumos incrustados en el cuaderno 04 (zlib + base64), para clones sin la carpeta data/."""
    nb = json.loads(CUADERNO.read_text(encoding="utf-8"))
    for celda in nb["cells"]:
        fuente = "".join(celda.get("source", ""))
        if "INSUMOS_INCRUSTADOS = {" not in fuente:
            continue
        for nodo in ast.parse(fuente).body:
            if isinstance(nodo, ast.Assign) and getattr(nodo.targets[0], "id", None) == "INSUMOS_INCRUSTADOS":
                return ast.literal_eval(nodo.value)
    raise SystemExit("El cuaderno 04 no trae la celda INSUMOS_INCRUSTADOS")


def reunir_insumos(destino: Path) -> dict:
    """Copia los insumos del ajuste final a `destino` y escribe `insumos.json`."""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))["insumos"]
    resumen = json.loads(RESUMEN.read_text(encoding="utf-8"))
    entrega = ENTREGA.read_bytes()
    if sha256(entrega) != resumen["sha256"]["predicciones_59.csv"]:
        raise SystemExit("predicciones_59.csv no coincide con resumen.json: no se empaqueta")
    destino.mkdir(parents=True, exist_ok=True)
    registro, incrustados = {}, None
    for clave in CLAVES:
        reg = cfg[clave]
        ruta = REPO / reg["ruta_local"]
        if ruta.exists():
            contenido, origen = ruta.read_bytes(), reg["ruta_local"]
        else:
            incrustados = incrustados or insumos_del_cuaderno()
            contenido = zlib.decompress(base64.b64decode(incrustados[clave]["bytes_zlib_base64"], validate=True))
            origen = "notebooks/04_seleccion_modelo_final.ipynb (copia incrustada)"
        if len(contenido) != reg["bytes"] or sha256(contenido) != reg["sha256"]:
            raise SystemExit(f"{clave}: el contenido de {origen} no coincide con config/04_seleccion_modelo_final.json")
        archivo = f"{clave}.csv"
        (destino / archivo).write_bytes(contenido)
        registro[clave] = {"archivo": archivo, "ruta_repo": reg["ruta_local"], "origen": origen, "bytes": reg["bytes"], "sha256": reg["sha256"]}
    manifiesto = {
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "commit": commit(),
        "insumos": registro,
        "esperado": {"predicciones_59.csv": {"sha256": sha256(entrega), "bytes": len(entrega)}},
    }
    (destino / "insumos.json").write_text(json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifiesto


def instalar_dependencias(destino: Path) -> None:
    req = BUILD / "requirements.txt"
    subprocess.run(["uv", "export", "--project", str(API), "--frozen", "--no-dev", "--no-hashes",
                    "--no-emit-project", "--quiet", "-o", str(req)], check=True)
    # --python: el intérprete que corre este script (3.13 del proyecto); evita que uv busque o descargue otro
    subprocess.run(["uv", "pip", "install", "--quiet", "-r", str(req), "--target", str(destino), "--python", sys.executable,
                    "--python-platform", PLATAFORMA, "--python-version", PYTHON, "--only-binary", ":all:"], check=True)


def podar(raiz: Path) -> None:
    """Quita pruebas, cachés y ejecutables de las dependencias: no se usan en la función."""
    shutil.rmtree(raiz / "bin", ignore_errors=True)
    (raiz / ".lock").unlink(missing_ok=True)
    for p in sorted(raiz.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if p.is_dir() and p.name in {"tests", "__pycache__"}:
            shutil.rmtree(p, ignore_errors=True)
        elif p.is_file() and p.suffix in {".pyc", ".pyo"}:
            p.unlink()


def comprimir(origen: Path, zip_path: Path) -> None:
    """ZIP determinista: orden fijo, fecha fija y permisos fijos."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(origen.rglob("*")):
            if p.is_file():
                info = zipfile.ZipInfo(p.relative_to(origen).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    PAQUETE.mkdir(parents=True)
    instalar_dependencias(PAQUETE)
    shutil.copytree(API / "agrocebada_api", PAQUETE / "agrocebada_api", ignore=shutil.ignore_patterns("__pycache__", "insumos"))
    manifiesto = reunir_insumos(PAQUETE / "agrocebada_api" / "insumos")
    # la fecha de generación cambia en cada corrida; se fija para que el ZIP sea reproducible
    manifiesto["generado"] = None
    (PAQUETE / "agrocebada_api" / "insumos" / "insumos.json").write_text(
        json.dumps(manifiesto, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    podar(PAQUETE)
    tam = sum(p.stat().st_size for p in PAQUETE.rglob("*") if p.is_file())
    if tam > LIMITE_DESCOMPRIMIDO:
        raise SystemExit(f"El paquete descomprimido mide {tam / 2**20:.0f} MB; Lambda acepta hasta 250 MB")
    comprimir(PAQUETE, ZIP)
    print(f"Paquete: {ZIP.relative_to(REPO) if ZIP.is_relative_to(REPO) else ZIP}")
    print(f"  descomprimido {tam / 2**20:.1f} MB, ZIP {ZIP.stat().st_size / 2**20:.1f} MB, sha256 {sha256(ZIP.read_bytes())[:16]}…")
    print(f"  insumos verificados: {len(manifiesto['insumos'])}; commit {manifiesto['commit']}")


if __name__ == "__main__":
    main()
