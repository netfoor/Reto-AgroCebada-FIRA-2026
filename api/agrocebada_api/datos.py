"""Insumos del ajuste final, leídos como en el cuaderno 04 y verificados por tamaño y SHA-256.

`api/empaquetar.py` copia los insumos desde `config/04_seleccion_modelo_final.json` a la carpeta
`insumos/` del paquete y escribe `insumos.json` con su registro. Aquí no se descarga nada: si un
archivo no coincide con su registro, la carga se detiene.
"""
from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .recetas import ID, Y

CARPETA = Path(__file__).resolve().parent / "insumos"
FAMILIAS_J = ["clima_ventanas", "clima_anomalias", "sat_compuestos", "sat_sensor", "sat_indices17"]
CLAVES = ["metadatos", "k1", "etiquetas", "base_jared"] + [
    f"jared_{f}_{tipo}" for f in FAMILIAS_J for tipo in ("features", "hipotesis")
]


class InsumoAlterado(RuntimeError):
    """Un insumo no coincide con el tamaño o la SHA-256 registrados."""


@dataclass(frozen=True)
class Datos:
    T: pd.DataFrame            # 197 parcelas: Municipio, CONJUNTO, x_m, y_m, K1_corregido, grupo
    y: pd.Series               # 138 rendimientos conocidos (t/ha)
    FX: pd.DataFrame           # 148 variables candidatas del modelo J
    ETIQUETADAS: np.ndarray    # 138 IDs ordenados
    OCULTAS: np.ndarray        # 59 IDs ordenados
    manifiesto: dict


def _bytes(manifiesto: dict, carpeta: Path, clave: str) -> bytes:
    reg = manifiesto["insumos"][clave]
    contenido = (carpeta / reg["archivo"]).read_bytes()
    if len(contenido) != reg["bytes"] or hashlib.sha256(contenido).hexdigest() != reg["sha256"]:
        raise InsumoAlterado(f"{clave}: el archivo no coincide con su registro")
    return contenido


def _csv(manifiesto: dict, carpeta: Path, clave: str) -> pd.DataFrame:
    # misma lectura que `leer_csv` del cuaderno 04
    return pd.read_csv(io.BytesIO(_bytes(manifiesto, carpeta, clave)), encoding="utf-8-sig", float_precision="round_trip")


def cargar(carpeta: Path = CARPETA) -> Datos:
    carpeta = Path(carpeta)
    manifiesto = json.loads((carpeta / "insumos.json").read_text(encoding="utf-8"))
    faltan = set(CLAVES) - set(manifiesto["insumos"])
    if faltan:
        raise InsumoAlterado(f"faltan insumos: {sorted(faltan)}")

    meta = _csv(manifiesto, carpeta, "metadatos")
    etiquetas = _csv(manifiesto, carpeta, "etiquetas")
    k1 = _csv(manifiesto, carpeta, "k1")[[ID, "K1_corregido"]]
    grupo = _csv(manifiesto, carpeta, "base_jared")[[ID, "grupo"]]
    T = meta.merge(k1, on=ID, validate="1:1").merge(grupo, on=ID, validate="1:1").set_index(ID).sort_index()
    y = etiquetas.set_index(ID)[Y].sort_index()
    assert len(T) == 197 and T.index.is_unique and not any("RENDIMIENTO" in c or "Cultivo" in c for c in T.columns)
    assert len(y) == 138 and y.notna().all() and set(y.index) == set(T.index[T.CONJUNTO.eq("ENTRENAMIENTO")])
    OCULTAS = np.array(sorted(T.index[T.CONJUNTO.eq("PREDICCION")]))
    ETIQUETADAS = np.array(sorted(y.index))
    assert len(OCULTAS) == 59 and not set(OCULTAS) & set(y.index)

    # 148 candidatas de Jared, en el mismo orden que el cuaderno 04
    F, hip = None, []
    for f in FAMILIAS_J:
        d = _csv(manifiesto, carpeta, f"jared_{f}_features")
        F = d if F is None else F.merge(d, on=ID, how="left")
        hip.append(pd.read_csv(io.BytesIO(_bytes(manifiesto, carpeta, f"jared_{f}_hipotesis")), dtype=str, keep_default_na=False))
    hip = pd.concat(hip)
    hip = hip[(hip.spec == "lineal") & (hip.id != "HC2")]
    vars_j: list[str] = []
    for v in hip.variables:
        for x in v.replace(" ", "").split(";"):
            if x and x not in vars_j:
                vars_j.append(x)
    FX = F.set_index(ID)[vars_j]
    assert len(vars_j) == 148 and not FX.loc[ETIQUETADAS].isna().any().any()
    return Datos(T=T, y=y, FX=FX, ETIQUETADAS=ETIQUETADAS, OCULTAS=OCULTAS, manifiesto=manifiesto)
