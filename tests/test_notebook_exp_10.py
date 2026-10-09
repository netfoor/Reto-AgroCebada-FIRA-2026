"""Lector EXP_10: insumos con hash correcto y ninguna llamada de entrenamiento en celdas ejecutables."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nbformat

RAIZ = Path(__file__).resolve().parents[1]
CFG = json.loads((RAIZ / "config/exp_10_verificacion_contraste_vecinal.json").read_text())
NB = RAIZ / "notebooks/experimentos/exp_10_verificacion_contraste_vecinal/exp_10_verificacion_contraste_vecinal.ipynb"


def test_insumos_del_lector_coinciden_con_sus_hashes():
    for clave, c in CFG["insumos"].items():
        b = (RAIZ / c["ruta_local"]).read_bytes()
        assert len(b) == c["bytes"] and hashlib.sha256(b).hexdigest() == c["sha256"], clave


def test_lector_no_entrena_ni_genera_predicciones_finales():
    nb = nbformat.read(NB, as_version=4)
    codigo = "\n".join(c.source for c in nb.cells if c.cell_type == "code" and "insumos-tecnicos" not in c.metadata.get("tags", []))
    for prohibido in ("predecir_fold", "ajustar_correccion", "experimento_10", ".fit(", "predecir_referencias"):
        assert prohibido not in codigo
    assert nb.metadata["agrocebada"]["ajustes_actuales"] == 0 and nb.metadata["agrocebada"]["colab_real_probado"] is False
    salidas = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs]
    assert salidas and not any(o.output_type == "error" for o in salidas)
