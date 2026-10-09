"""Lector EXP_11: insumos con hash correcto, ejecución sin errores y ningún entrenamiento."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nbformat

RAIZ = Path(__file__).resolve().parents[1]
CFG = json.loads((RAIZ / "config/exp_11_combinacion_modelos.json").read_text())
NB = RAIZ / "notebooks/experimentos/exp_11_combinacion_modelos/exp_11_combinacion_modelos.ipynb"


def test_insumos_del_lector_coinciden_con_sus_hashes():
    for clave, c in CFG["insumos"].items():
        b = (RAIZ / c["ruta_local"]).read_bytes()
        assert len(b) == c["bytes"] and hashlib.sha256(b).hexdigest() == c["sha256"], clave


def test_lector_sin_entrenamientos_y_ejecutado():
    nb = nbformat.read(NB, as_version=4)
    codigo = "\n".join(c.source for c in nb.cells if c.cell_type == "code" and "insumos-tecnicos" not in c.metadata.get("tags", []))
    for prohibido in (".fit(", "lstsq", "jared_completo", "predecir_fold", "experimento_11"):
        assert prohibido not in codigo
    assert "0.5 * w.J + 0.5 * w.K" in codigo and "0.5 * w.MUN + 0.5 * w.K" in codigo
    salidas = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs]
    assert salidas and not any(o.output_type == "error" for o in salidas)
    assert nb.metadata["agrocebada"]["colab_real_probado"] is False
