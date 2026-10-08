"""Recalcula fuentes → variables en un kernel nuevo; conserva una ejecución aparte."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ESPERADO = {
    "parcelas": 197,
    "columnas_base": 539,
    "columnas_postciclo": 121,
    "variables_diccionario": 660,
    "etiquetas": 138,
    "por_predecir": 59,
    "rasteres": 146,
    "filas_clima": 28368,
    "modelos_entrenados": 0,
    "predicciones_finales_generadas": 0,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    raiz = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--entrada", type=Path, default=raiz / "notebooks/02_fuentes_a_variables.ipynb"
    )
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    marca = ahora.strftime("%Y%m%dT%H%M%S_%fZ")
    destino = args.salida or raiz / "resultados_locales/fuentes_02" / marca / args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists():
        raise ValueError("La ejecución exige una salida nueva; no sobrescribe el cuaderno")
    cuaderno = nbformat.read(args.entrada, as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-fuentes02-kernel-") as runtime:
        opciones = (
            {"transport": "ipc", "ip": str(Path(runtime) / "kernel")}
            if (sys.platform != "win32")
            else {"ip": "127.0.0.1"}
        )
        km = KernelManager(kernel_name="python3", **opciones)
        km.kernel_spec.argv = [
            sys.executable,
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ]
        cliente = NotebookClient(
            cuaderno,
            km=km,
            timeout=300,
            startup_timeout=30,
            allow_errors=False,
            resources={
                "metadata": {"path": str(args.entrada.parent)},
            },
        )
        try:
            cliente.execute()
        finally:
            if km.has_kernel:
                km.shutdown_kernel(now=True)
            km.cleanup_resources()
    nbformat.validate(cuaderno)
    codigos = [celda for celda in cuaderno.cells if celda.cell_type == "code"]
    if any(celda.execution_count is None for celda in codigos):
        raise ValueError("Hay celdas sin ejecutar")
    if any(salida.output_type == "error" for celda in codigos for salida in celda.outputs):
        raise ValueError("Hay errores en las salidas")
    resumen = None
    for celda in codigos:
        for salida in celda.outputs:
            for linea in salida.get("text", "").splitlines():
                if linea.startswith("RESUMEN_FUENTES_02_JSON="):
                    resumen = json.loads(linea.split("=", 1)[1])
    if resumen is None:
        raise ValueError("No se encontró el resumen estructurado del cuaderno 02")
    for clave, esperado in ESPERADO.items():
        if resumen.get(clave) != esperado:
            raise ValueError(f"No coincide {clave}: {resumen.get(clave)} frente a {esperado}")
    if resumen.get("sha256_dataset") != (
        "d74dbaba1764e026da8ce38f7f3476f80523f479a6c141827887e09326061bb5"
    ):
        raise ValueError("No se utilizó el dataset original")
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(cuaderno, destino)
    registro = {
        "ejecutado_utc": ahora.isoformat(),
        "modo": "recalcular_fuentes_sin_entrenamiento",
        "python": sys.version.split()[0],
        "celdas_codigo_ejecutadas": len(codigos),
        "errores": 0,
        "resumen": resumen,
        "notebook_sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
        "colab_real_probado": False,
    }
    destino.with_suffix(".verificacion.json").write_text(
        json.dumps(registro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(registro, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
