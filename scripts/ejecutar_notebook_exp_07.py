"""Ejecuta la lectura de EXP07 en kernel limpio, sin entrenar candidatos."""
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
    "id": "EXP_07", "modo": "lector_resultados_experimento_registrado_sin_ajustes",
    "parcelas": 197, "etiquetas": 138, "capturas_incorporadas": 26255, "capturas_pareadas": 18248,
    "variables_recalculadas": 2, "mascaras_pareadas_identicas": True, "factibilidad_apta": True,
    "entrenamientos_X_verificados": 250, "procedimientos": 4, "candidatos": 1, "controles_modelo": 1,
    "oof_total": 5520, "oof_por_procedimiento": 1380, "poblacion": "SEEN135",
    "oof_seen_por_procedimiento": 1350, "poblacion_secundaria": "FULL138",
    "decisiones_verificadas": 100, "scores_guardados_verificados": 600,
    "sse_interiores_verificadas": 2400, "ecuaciones_oof_reproducidas": 1,
    "ajustes_actuales": 0, "predicciones_finales_generadas": 0, "oof_regeneradas": False,
    "errores_interiores_regenerados": False, "scores_desde_sse_recalculados": 600,
    "metricas_recalculadas": True, "variantes_adoptadas": [],
}


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=raiz / "notebooks/experimentos/exp_07_heterogeneidad_parcela/exp_07_heterogeneidad_parcela.ipynb")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    destino = args.salida or raiz / "resultados_locales/exp_07_heterogeneidad_parcela" / ahora.strftime("%Y%m%dT%H%M%S_%fZ") / args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists() or destino.with_suffix(".verificacion.json").exists():
        raise ValueError("Elige una salida nueva; no sobrescribir notebook ni registro")
    nb = nbformat.read(args.entrada, as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-exp07-kernel-") as runtime:
        opciones = {"transport": "ipc", "ip": str(Path(runtime) / "kernel")} if sys.platform != "win32" else {"ip": "127.0.0.1"}
        km = KernelManager(kernel_name="python3", **opciones)
        km.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
        cliente = NotebookClient(nb, km=km, timeout=300, startup_timeout=30, allow_errors=False,
            resources={"metadata": {"path": str(args.entrada.parent.resolve())}},
            on_cell_start=lambda cell, cell_index: print(f"Celda {cell_index+1}/{len(nb.cells)}", flush=True))
        try:
            cliente.execute()
        finally:
            if km.has_kernel:
                km.shutdown_kernel(now=True)
            km.cleanup_resources()
    codigos = [c for c in nb.cells if c.cell_type == "code"]
    if any(c.execution_count is None or any(o.output_type == "error" for o in c.outputs) for c in codigos):
        raise ValueError("Hay celdas sin ejecutar o errores")
    resumen = None
    for c in codigos:
        for o in c.outputs:
            for linea in o.get("text", "").splitlines():
                if linea.startswith("RESUMEN_EXP_07_JSON="):
                    resumen = json.loads(linea.split("=", 1)[1])
    if resumen is None or any(resumen.get(k) != v for k, v in ESPERADO.items()):
        raise ValueError("Resumen fuera del alcance del lector EXP07")
    nbformat.validate(nb)
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, destino)
    reg = {"ejecutado_utc": ahora.isoformat(), "modo": ESPERADO["modo"], "python": sys.version.split()[0],
           "celdas_codigo_ejecutadas": len(codigos), "errores": 0, "resumen": resumen,
           "notebook_sha256": hashlib.sha256(destino.read_bytes()).hexdigest(), "colab_real_probado": False}
    destino.with_suffix(".verificacion.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(reg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
