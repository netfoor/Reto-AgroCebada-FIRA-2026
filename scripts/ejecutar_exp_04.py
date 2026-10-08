"""Ejecuta el lector EXP04 en un kernel nuevo; no reentrena ni reextrae geometrías."""
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
    "id":"EXP_04","modo":"lector_retrospectivo_sin_ajustes","parcelas":197,"etiquetas":138,
    "piezas_guardadas":230,"pixeles_derivados":116,"lluvias_recalculadas":788,
    "procedimientos":10,"oof_por_procedimiento":1380,"oof_total":13800,
    "particiones_externas":50,"particiones_internas":200,
    "decisiones_verificadas":200,"scores_guardados_verificados":1150,
    "ajustes_actuales":0,"predicciones_finales_generadas":0,"poblacion":"FULL138",
    "scores_interiores_recalculados":False,"predicciones_recalculadas":False,
    "intersecciones_recalculadas":False,"variables_recalculadas":True,"metricas_recalculadas":True,
    "candidato_con_reservas":["J5_PCT"],"variantes_adoptadas":[],
    "diagnostico_posterior":"SEEN135","oof_seen_por_procedimiento":1350,
    "regla_full_cumplen":["J5_PCT"],"regla_seen_cumplen":[],
}


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada",type=Path,default=raiz/"notebooks/experimentos/exp_04_lluvia_octubre/exp_04_lluvia_octubre.ipynb")
    parser.add_argument("--salida",type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    destino = args.salida or raiz/"resultados_locales/exp_04_lluvia_octubre"/ahora.strftime("%Y%m%dT%H%M%S_%fZ")/args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists() or destino.with_suffix(".verificacion.json").exists():
        raise ValueError("Elige una salida nueva; no se sobrescriben notebook ni registro")
    nb = nbformat.read(args.entrada,as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-exp04-kernel-") as runtime:
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
                if linea.startswith("RESUMEN_EXP_04_JSON="):
                    resumen = json.loads(linea.split("=",1)[1])
    if resumen is None or any(resumen.get(k) != v for k,v in ESPERADO.items()):
        raise ValueError("Resumen fuera del alcance del lector EXP04")
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
