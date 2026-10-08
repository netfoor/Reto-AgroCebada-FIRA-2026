"""Recalcula referencias en un kernel nuevo y conserva una ejecución aparte."""

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
    "etiquetas": 138,
    "por_predecir": 59,
    "repeticiones": 10,
    "pliegues_externos": 50,
    "pliegues_internos": 200,
    "referencias": 3,
    "oof_por_referencia": 1380,
    "oof_total": 4140,
    "parcelas_seen": 135,
    "oof_seen_por_referencia": 1350,
    "referencias_reproducidas": True,
    "modelos_nuevos": 0,
    "hiperparametros_seleccionados": 0,
    "predicciones_finales_generadas": 0,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    raiz = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--entrada", type=Path, default=raiz / "notebooks/03_referencias_y_validacion.ipynb"
    )
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    marca = ahora.strftime("%Y%m%dT%H%M%S_%fZ")
    destino = args.salida or raiz / "resultados_locales/referencias_03" / marca / args.entrada.name
    if (
        destino.resolve() == args.entrada.resolve()
        or destino.exists()
        or destino.with_suffix(".verificacion.json").exists()
    ):
        raise ValueError(
            "La ejecución exige una salida nueva; no sobrescribe el cuaderno ni su registro"
        )
    cuaderno = nbformat.read(args.entrada, as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-referencias03-kernel-") as runtime:
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
    codigos = [c for c in cuaderno.cells if c.cell_type == "code"]
    if any(c.execution_count is None for c in codigos):
        raise ValueError("Hay celdas sin ejecutar")
    if any(o.output_type == "error" for c in codigos for o in c.outputs):
        raise ValueError("Hay errores en las salidas")
    resumen = None
    for c in codigos:
        for o in c.outputs:
            for linea in o.get("text", "").splitlines():
                if linea.startswith("RESUMEN_REFERENCIAS_03_JSON="):
                    resumen = json.loads(linea.split("=", 1)[1])
    if resumen is None:
        raise ValueError("No se encontró el resumen estructurado del cuaderno 03")
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
        "modo": "recalcular_referencias_fijas_y_evaluacion",
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
