"""Ejecuta EXP05 en un kernel nuevo; no reentrena ni reextrae rásteres."""
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
    "id":"EXP_05","modo":"lector_retrospectivo_sin_ajustes","parcelas":197,"etiquetas":138,
    "variables_recalculadas":True,"lluvias_reextraidas":False,"intersecciones_recalculadas":False,
    "procedimientos":7,"candidatos":4,"oof_por_procedimiento":1380,"oof_total":9660,
    "particiones_externas":50,"particiones_internas":200,"decisiones_verificadas":200,
    "scores_guardados_verificados":1200,"parametros_guardados":250,
    "ajustes_actuales":0,"predicciones_finales_generadas":0,"predicciones_recalculadas":False,
    "scores_interiores_recalculados":False,"metricas_recalculadas":True,
    "r2_municipales_presentacion_nan":14,
    "poblacion":"SEEN135","oof_seen_por_procedimiento":1350,"poblacion_secundaria":"FULL138",
    "regla_seen_cumplen":[],"regla_full_cumplen":[],"variantes_adoptadas":[],
    "candidato_historico_con_reservas":["J5_PCT"],
    "fecha_original_mexico":"2026-10-01","fecha_original_utc":"2026-10-02","fecha_adaptacion":"2026-10-08",
}


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada",type=Path,default=raiz/"notebooks/experimentos/exp_05_historico_octubre/exp_05_historico_octubre.ipynb")
    parser.add_argument("--salida",type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    destino = args.salida or raiz/"resultados_locales/exp_05_historico_octubre"/ahora.strftime("%Y%m%dT%H%M%S_%fZ")/args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists() or destino.with_suffix(".verificacion.json").exists():
        raise ValueError("Elige una salida nueva; no se sobrescriben notebook ni registro")
    nb = nbformat.read(args.entrada,as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-exp05-kernel-") as runtime:
        opciones = {"transport":"ipc","ip":str(Path(runtime)/"kernel")} if sys.platform != "win32" else {"ip":"127.0.0.1"}
        km = KernelManager(kernel_name="python3",**opciones)
        km.kernel_spec.argv = [sys.executable,"-m","ipykernel_launcher","-f","{connection_file}"]
        cliente = NotebookClient(nb,km=km,timeout=300,startup_timeout=30,allow_errors=False,
            resources={"metadata":{"path":str(args.entrada.parent.resolve())}},
            on_cell_start=lambda cell,cell_index:print(f"Celda {cell_index+1}/{len(nb.cells)}",flush=True))
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
            for linea in o.get("text","").splitlines():
                if linea.startswith("RESUMEN_EXP_05_JSON="):
                    resumen = json.loads(linea.split("=",1)[1])
    if resumen is None or any(resumen.get(k) != v for k,v in ESPERADO.items()):
        raise ValueError("Resumen fuera del alcance del lector EXP05")
    nbformat.validate(nb)
    destino.parent.mkdir(parents=True,exist_ok=True)
    nbformat.write(nb,destino)
    reg = {"ejecutado_utc":ahora.isoformat(),"modo":ESPERADO["modo"],"python":sys.version.split()[0],
           "celdas_codigo_ejecutadas":len(codigos),"errores":0,"resumen":resumen,
           "notebook_sha256":hashlib.sha256(destino.read_bytes()).hexdigest(),"colab_real_probado":False}
    destino.with_suffix(".verificacion.json").write_text(json.dumps(reg,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(reg,indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main()
