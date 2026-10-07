"""Recalcula la auditoría en un kernel nuevo; guarda una ejecución separada."""

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
    "filas_basico": 107666,
    "filas_pro": 47804,
    "geometrias_validas": 197,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    raiz = Path(__file__).resolve().parents[1]
    parser.add_argument("--entrada", type=Path,
                        default=raiz / "notebooks/01_auditoria_y_unidad_parcela.ipynb")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    marca = ahora.strftime("%Y%m%dT%H%M%S_%fZ")
    destino = args.salida or (
        raiz / "resultados_locales/auditoria_01" / marca / args.entrada.name
    )
    if destino.resolve() == args.entrada.resolve() or destino.exists():
        raise ValueError("La ejecución requiere una salida nueva; no sobrescribe el cuaderno")
    cuaderno = nbformat.read(args.entrada, as_version=4)
    # El kernel usa exactamente el Python que invoca este script (uv/.venv).
    with tempfile.TemporaryDirectory(prefix="agrocebada-kernel-") as runtime:
        # En Linux/macOS, IPC evita abrir puertos TCP para comprobar un cuaderno local.
        ajustes = {"transport": "ipc", "ip": str(Path(runtime) / "kernel")} if (
            sys.platform != "win32"
        ) else {"ip": "127.0.0.1"}
        km = KernelManager(kernel_name="python3", **ajustes)
        km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        cliente = NotebookClient(cuaderno, km=km, timeout=300, startup_timeout=30,
                                 allow_errors=False, resources={
                                     "metadata": {"path": str(args.entrada.parent)},
                                 })
        try:
            cliente.execute()
        finally:
            if km.has_kernel:
                km.shutdown_kernel(now=True)
            km.cleanup_resources()
    nbformat.validate(cuaderno)
    codigos = [c for c in cuaderno.cells if c.cell_type == "code"]
    if any(c.execution_count is None for c in codigos):
        raise ValueError("Hay celdas de código sin ejecutar")
    errores = [o for c in codigos for o in c.get("outputs", []) if o.output_type == "error"]
    if errores:
        raise ValueError("Hay errores en las salidas del cuaderno")
    resumen = None
    for celda in codigos:
        for salida in celda.get("outputs", []):
            for linea in salida.get("text", "").splitlines():
                if linea.startswith("RESUMEN_AUDITORIA_JSON="):
                    resumen = json.loads(linea.split("=", 1)[1])
    if resumen is None:
        raise ValueError("No se encontró el resumen estructurado de auditoría")
    for clave, valor in ESPERADO.items():
        if resumen.get(clave) != valor:
            raise ValueError(f"No coincide {clave}: {resumen.get(clave)} frente a {valor}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(cuaderno, destino)
    registro = {
        "ejecutado_utc": ahora.isoformat(),
        "modo": "recalcular_auditoria_sin_entrenamiento",
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
    print(json.dumps(registro, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
