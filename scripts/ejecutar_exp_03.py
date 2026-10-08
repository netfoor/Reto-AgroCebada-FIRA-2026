"""Ejecuta el lector EXP_03 en un kernel nuevo, sin reentrenar modelos."""
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
    "id":"EXP_03", "modo":"lector_retrospectivo_sin_ajustes",
    "parcelas":197, "etiquetas":138, "medias_mensuales":2758,
    "variables_base":["C_PL_ndvi_media","C_PL_ndvi_pico_prom","C_PL_ndvi_doy_pico_prom",
                      "C_S2_ndvi_media","C_S2_ndwi_media","C_LS_vi6t_media"],
    "variables_nuevas":["PL_ndvi_junjul_menos_abrmay","PL_ndvi_sepoct_menos_julago",
                        "PL_ndvi_amplitud_mensual","S2_ndwi_sepoct_menos_julago"],
    "procedimientos":7, "oof_por_procedimiento":1380, "oof_total":9660,
    "particiones_externas":50, "particiones_internas":200,
    "decisiones_verificadas":200, "scores_guardados_verificados":900,
    "ajustes_actuales":0, "predicciones_finales_generadas":0, "poblacion":"FULL138",
    "scores_interiores_recalculados":False, "predicciones_recalculadas":False,
    "variables_recalculadas":True, "metricas_recalculadas":True, "variantes_adoptadas":[],
}


def main():
    raiz = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada",type=Path,default=raiz / "notebooks/experimentos/exp_03_variables_y_familias/exp_03_variables_y_familias.ipynb")
    parser.add_argument("--salida",type=Path)
    args = parser.parse_args()
    ahora = datetime.now(timezone.utc)
    destino = args.salida or raiz / "resultados_locales/exp_03_variables_y_familias" / ahora.strftime("%Y%m%dT%H%M%S_%fZ") / args.entrada.name
    if destino.resolve() == args.entrada.resolve() or destino.exists() or destino.with_suffix(".verificacion.json").exists():
        raise ValueError("Elige una salida nueva; no se sobrescribe notebook ni registro")
    nb = nbformat.read(args.entrada,as_version=4)
    with tempfile.TemporaryDirectory(prefix="agrocebada-exp03-kernel-") as runtime:
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
                if linea.startswith("RESUMEN_EXP_03_JSON="):
                    resumen = json.loads(linea.split("=",1)[1])
    if resumen is None or any(resumen.get(k) != v for k,v in ESPERADO.items()):
        raise ValueError("El resumen no cumple el alcance del lector EXP_03")
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
