"""Ejecuta el lector EXP_02 en un kernel nuevo; no reentrena modelos."""
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
    "id": "EXP_02", "modo": "lector_retrospectivo_sin_ajustes",
    "parcelas": 197, "etiquetas": 138, "medias_mensuales": 4137,
    "variables_modificadas": ["C_PL_ndvi_media", "C_S2_ndvi_media", "C_S2_ndwi_media"],
    "variables_fijas": ["C_PL_ndvi_pico_prom", "C_PL_ndvi_doy_pico_prom", "C_LS_vi6t_media"],
    "procedimientos": 6, "oof_por_procedimiento": 1380, "oof_total": 8280,
    "particiones_externas": 50, "particiones_internas": 200,
    "decisiones_alpha_verificadas": 100, "cambios_alpha_T1_E2": 13,
    "ajustes_actuales": 0, "predicciones_finales_generadas": 0, "poblacion": "FULL138",
    "scores_interiores_recalculados": False, "predicciones_recalculadas": False,
    "variables_recalculadas": True, "metricas_recalculadas": True, "T1_adoptado": False,
}


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=raiz / "notebooks/experimentos/exp_02_ponderacion_temporal/exp_02_ponderacion_temporal.ipynb")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    destino = args.salida or raiz / "resultados_locales/exp_02_ponderacion_temporal" / ahora.strftime("%Y%m%dT%H%M%S_%fZ") / args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists() or destino.with_suffix(".verificacion.json").exists():
        raise ValueError("Elige una salida nueva; no se sobrescribe notebook ni registro")
    nb = nbformat.read(args.entrada, as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-exp02-kernel-") as runtime:
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
                if linea.startswith("RESUMEN_EXP_02_JSON="):
                    resumen = json.loads(linea.split("=", 1)[1])
    if resumen is None or any(resumen.get(k) != v for k, v in ESPERADO.items()):
        raise ValueError("El resumen no cumple el alcance del lector EXP_02")
    nbformat.validate(nb)
    destino.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, destino)
    registro = {"ejecutado_utc": ahora.isoformat(), "modo": ESPERADO["modo"],
                "python": sys.version.split()[0], "celdas_codigo_ejecutadas": len(codigos),
                "errores": 0, "resumen": resumen,
                "notebook_sha256": hashlib.sha256(destino.read_bytes()).hexdigest(), "colab_real_probado": False}
    destino.with_suffix(".verificacion.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps(registro, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
