"""Referencias fijas y evaluación OOF: contención, ausencia de fuga y paridad."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


RAIZ = Path(__file__).resolve().parents[1]


def cargar_modulo(nombre):
    ruta = RAIZ / "scripts" / f"{nombre}.py"
    if not ruta.is_file():
        ruta = Path(__file__).with_name(f"{nombre}.py")
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


V = cargar_modulo("validacion_03")


@pytest.fixture
def sinteticos():
    ids = [f"AGC_{i:03d}" for i in range(1, 9)]
    tabla = pd.DataFrame(
        {
            "ID_POLIGONO": ids,
            "Municipio": ["A"] * 4 + ["B"] * 3 + ["S"],
            "x_m": np.arange(8) * 100.0,
            "y_m": np.zeros(8),
            "RENDIMIENTO_T_HA": [1.0, 2.0, 3.0, 5.0, 2.0, 3.0, 5.0, 6.0],
        }
    )
    externas, internas = [], []
    for r in range(2):
        for f in range(2):
            val = set(ids[f::2])
            tr = [identificador for identificador in ids if identificador not in val]
            for identificador in ids:
                externas.append(
                    {
                        "repeticion": r,
                        "pliegue": f,
                        "rol": "validacion" if identificador in val else "entrenamiento",
                        "ID_POLIGONO": identificador,
                    }
                )
            for k in range(2):
                va = set(tr[k::2])
                for identificador in tr:
                    internas.append(
                        {
                            "repeticion": r,
                            "pliegue": f,
                            "pliegue_interno": k,
                            "rol": "validacion" if identificador in va else "entrenamiento",
                            "ID_POLIGONO": identificador,
                        }
                    )
    return tabla, pd.DataFrame(externas), pd.DataFrame(internas)


def test_particiones_completas_y_orden_original(sinteticos):
    tabla, externas, internas = sinteticos
    resumen = V.validar_externas(externas, tabla.ID_POLIGONO, 2, 2)
    assert resumen["filas"] == 32 and resumen["validacion_por_pliegue"] == [4]
    resumen_i = V.validar_internas(internas, externas, tabla.ID_POLIGONO, 2, 2, 2)
    assert resumen_i["filas"] == 32 and resumen_i["contencion_ok"]
    invertida = tabla.iloc[::-1]
    splits = V.particiones_desde_csv(externas.iloc[::-1], invertida, 2, 2)
    for r, f, tr, va in splits:
        assert np.all(np.diff(tr) > 0) and np.all(np.diff(va) > 0)
        assert not set(tr) & set(va)
        esperado = set(
            externas.loc[
                externas.repeticion.eq(r) & externas.pliegue.eq(f) & externas.rol.eq("validacion"),
                "ID_POLIGONO",
            ]
        )
        assert set(invertida.iloc[va].ID_POLIGONO) == esperado


@pytest.mark.parametrize(
    "problema",
    [
        "duplicado",
        "solapado",
        "rol",
        "no_entero",
        "no_finito",
        "negativo",
        "no_cero",
        "incompleto",
        "id_extra",
        "validacion_repetida",
    ],
)
def test_externas_rechazan_contratos_invalidos(sinteticos, problema):
    tabla, externas, _ = sinteticos
    e = externas.copy()
    if problema == "duplicado":
        e = pd.concat([e, e.iloc[:1]])
    elif problema == "solapado":
        fila = e.iloc[:1].copy()
        fila["rol"] = "entrenamiento" if fila.rol.iloc[0] == "validacion" else "validacion"
        e = pd.concat([e, fila])
    elif problema == "rol":
        e.loc[0, "rol"] = "prueba"
    elif problema in ("no_entero", "no_finito", "negativo"):
        e["pliegue"] = e.pliegue.astype(float)
        e.loc[0, "pliegue"] = {"no_entero": 0.5, "no_finito": np.nan, "negativo": -1}[problema]
    elif problema == "no_cero":
        e["pliegue"] += 1
    elif problema == "incompleto":
        e = e.iloc[1:]
    elif problema == "id_extra":
        e.loc[0, "ID_POLIGONO"] = "AGC_999"
    else:
        for f in (0, 1):
            seleccion = e.repeticion.eq(0) & e.pliegue.eq(f) & e.ID_POLIGONO.eq("AGC_001")
            e.loc[seleccion, "rol"] = "validacion"
    with pytest.raises(ValueError):
        V.validar_externas(e, tabla.ID_POLIGONO, 2, 2)


@pytest.mark.parametrize(
    "problema",
    ["externa_adentro", "duplicado", "interna_faltante", "externa_faltante", "val_repetida"],
)
def test_internas_jamas_contienen_validacion_externa(sinteticos, problema):
    tabla, e, internas = sinteticos
    i = internas.copy()
    if problema == "externa_adentro":
        i.loc[0, "ID_POLIGONO"] = e.loc[
            e.repeticion.eq(0) & e.pliegue.eq(0) & e.rol.eq("validacion"), "ID_POLIGONO"
        ].iloc[0]
    elif problema == "duplicado":
        i = pd.concat([i, i.iloc[:1]])
    elif problema == "interna_faltante":
        i = i.loc[~(i.repeticion.eq(0) & i.pliegue.eq(0) & i.pliegue_interno.eq(0))]
    elif problema == "externa_faltante":
        i = i.loc[~(i.repeticion.eq(0) & i.pliegue.eq(0))]
    else:
        identificador = i.ID_POLIGONO.iloc[0]
        i.loc[i.repeticion.eq(0) & i.pliegue.eq(0) & i.ID_POLIGONO.eq(identificador), "rol"] = (
            "validacion"
        )
    with pytest.raises(ValueError):
        V.validar_internas(i, e, tabla.ID_POLIGONO, 2, 2, 2)


def test_referencias_no_consultan_etiquetas_de_validacion(sinteticos):
    tabla, e, _ = sinteticos
    _, _, tr, va = V.particiones_desde_csv(e, tabla, 2, 2)[0]
    a, t = tabla.iloc[tr].copy(), tabla.iloc[va].copy()
    primero = V.predecir_referencias(a, t)
    t["RENDIMIENTO_T_HA"] = [np.nan, np.inf, -999.0, 777.0]
    segundo = V.predecir_referencias(a, t)
    for modelo in V.MODELOS_03:
        np.testing.assert_array_equal(primero[modelo], segundo[modelo])
    original = V.construir_oof(tabla, e, 2, 2)
    cambiada = tabla.copy()
    cambiada.loc[cambiada.ID_POLIGONO.isin(tabla.iloc[va].ID_POLIGONO), "RENDIMIENTO_T_HA"] += 100
    diferente = V.construir_oof(cambiada, e, 2, 2)
    seleccion = original.repeticion.eq(0) & original.pliegue.eq(0)
    np.testing.assert_array_equal(
        original.loc[seleccion, "predicho"], diferente.loc[seleccion, "predicho"]
    )
    np.testing.assert_array_equal(original.municipio_visto, diferente.municipio_visto)


def test_idw_k20_potencia2_distancia_minima_y_fallback():
    a = pd.DataFrame(
        {
            "Municipio": ["A"] * 25,
            "x_m": np.arange(25, dtype=float),
            "y_m": np.zeros(25),
            "RENDIMIENTO_T_HA": np.arange(25, dtype=float),
        }
    )
    t = pd.DataFrame({"Municipio": ["nuevo"], "x_m": [0.0], "y_m": [0.0]})
    p = V.predecir_referencias(a, t)
    w = 1 / np.maximum(np.arange(20), 1.0) ** 2
    idw = np.sum(w / w.sum() * np.arange(20))
    assert p["GLOBAL"][0] == p["MUN"][0] == 12.0
    assert np.isclose(p["MIX"][0], 0.5 * 12 + 0.5 * idw, rtol=0, atol=1e-12)
    with pytest.raises(ValueError):
        V.predecir_referencias(a.assign(x_m=np.nan), t)
    with pytest.raises(ValueError):
        V.predecir_referencias(a.assign(RENDIMIENTO_T_HA=np.inf), t)


def test_config_no_puede_declarar_coeficientes_distintos():
    config = {
        "referencias": {
            "MUN": {"municipio_no_visto": "GLOBAL"},
            "MIX": {
                "peso_municipal": 0.5,
                "idw_k": 20,
                "idw_potencia": 2,
                "distancia_minima_m": 1.0,
                "crs_distancias": "EPSG:32614",
            },
        }
    }
    assert V.validar_recetas_referencias(config)
    for campo, valor in [
        ("peso_municipal", np.nan),
        ("idw_k", 30),
        ("idw_potencia", np.inf),
        ("distancia_minima_m", 0.0),
    ]:
        cambiada = json.loads(json.dumps(config))
        cambiada["referencias"]["MIX"][campo] = valor
        with pytest.raises(ValueError):
            V.validar_recetas_referencias(cambiada)


@pytest.mark.parametrize(
    "problema", ["faltante", "duplicado", "infinito", "dimension", "observado", "mascara"]
)
def test_oof_rechaza_claves_y_valores_inconsistentes(sinteticos, problema):
    tabla, e, _ = sinteticos
    o = V.construir_oof(tabla, e, 2, 2)
    if problema == "faltante":
        o = o.iloc[1:]
    elif problema == "duplicado":
        o = pd.concat([o, o.iloc[:1]])
    elif problema == "infinito":
        o.loc[0, "predicho"] = np.inf
    elif problema == "dimension":
        o.loc[0, "n_entrenamiento"] += 1
    elif problema == "observado":
        o.loc[0, "observado"] += 1
    else:
        o.loc[0, "municipio_visto"] = not o.loc[0, "municipio_visto"]
    with pytest.raises(ValueError):
        V.validar_oof(o, e, 2, 2)


def test_metricas_r2_estandar_negativo_y_escala_degenerada():
    assert V.metricas_regresion([1.0, 3.0], [5.0, 5.0])["R2"] == -9.0
    assert np.isnan(V.metricas_regresion([3.0, 3.0], [4.0, 4.0])["R2"])
    for y, p in [([], []), ([1.0, 2.0], [1.0]), ([np.nan], [1.0]), ([1.0], [np.inf])]:
        with pytest.raises(ValueError):
            V.metricas_regresion(y, p)


def test_oof_rechaza_flag_falsa_compartida_por_los_tres_modelos(sinteticos):
    tabla, e, _ = sinteticos
    o = V.construir_oof(tabla, e, 2, 2)
    seleccion = o.repeticion.eq(0) & o.pliegue.eq(0) & o.ID_POLIGONO.eq("AGC_001")
    assert seleccion.sum() == 3 and o.loc[seleccion, "municipio_visto"].all()
    o.loc[seleccion, "municipio_visto"] = False
    with pytest.raises(ValueError, match="municipios de entrenamiento"):
        V.validar_oof(o, e, 2, 2)


def test_rmse_agrupado_no_es_media_pliegues_ni_error_de_prediccion_promediada():
    o = pd.DataFrame(
        {
            "modelo": ["GLOBAL"] * 4,
            "ID_POLIGONO": ["A", "B", "A", "B"],
            "repeticion": [0, 0, 1, 1],
            "pliegue": [0, 1, 0, 1],
            "observado": [1.0, 3.0, 1.0, 3.0],
            "predicho": [0.0, 3.0, 2.0, 3.0],
        }
    )
    r = V.resumen_metricas(o).iloc[0]
    assert r.n_parcelas == 2 and r.n_oof == 4
    assert r.RMSE == np.sqrt(0.5)
    media_pliegues = np.mean(
        [
            V.metricas_regresion(q.observado, q.predicho)["RMSE"]
            for _, q in o.groupby(["repeticion", "pliegue"])
        ]
    )
    assert media_pliegues == 0.5 and r.RMSE != media_pliegues
    promedio = o.groupby("ID_POLIGONO")[["observado", "predicho"]].mean()
    assert V.metricas_regresion(promedio.observado, promedio.predicho)["RMSE"] == 0


def test_comparar_oof_claves_observados_conteos_exactos_y_predicciones_a_tolerancia(sinteticos):
    tabla, e, _ = sinteticos
    o = V.construir_oof(tabla, e, 2, 2)
    control = o.copy()
    control["modelo"] = control.modelo.replace({v: k for k, v in V.ALIAS_HISTORICOS_03.items()})
    assert V.comparar_oof(o.iloc[::-1], control).coincide.all()
    control.loc[0, "predicho"] += 5e-9
    assert V.comparar_oof(o, control).coincide.all()
    control.loc[0, "predicho"] += 1e-6
    assert not V.comparar_oof(o, control).coincide.all()
    control.loc[0, "observado"] += 1e-10
    with pytest.raises(ValueError, match="observado"):
        V.comparar_oof(o, control)


@pytest.fixture(scope="session")
def reales():
    archivo = RAIZ / "data/raw/DataSet.zip"
    config_path = RAIZ / "config/validacion_03_recetas.json"
    if not archivo.is_file() or not config_path.is_file():
        pytest.skip("No están los insumos reales de NB03 en el proyecto")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    V.validar_recetas_referencias(config)
    assert hashlib.sha256(archivo.read_bytes()).hexdigest() == config["zip_sha256"]
    fuentes = {}
    for nombre, metadatos in config["insumos"].items():
        ruta = RAIZ / metadatos["ruta_local"]
        if not ruta.is_file():
            pytest.skip(f"Falta fixture real: {ruta.name}")
        bruto = ruta.read_bytes()
        assert (
            len(bruto) == metadatos["bytes"]
            and hashlib.sha256(bruto).hexdigest() == metadatos["sha256"]
        )
        fuentes[nombre] = pd.read_csv(ruta)
    modulos = {
        nombre: cargar_modulo(nombre)
        for nombre in ("auditoria_01", "fuentes_02_geo", "fuentes_02_satelite", "fuentes_02")
    }
    with modulos["auditoria_01"].cargar_zip(archivo) as z:
        datos = modulos["fuentes_02"].cargar_fuentes(z)
    tabla = (
        datos["etiquetas"]
        .merge(
            datos["metadatos"][["ID_POLIGONO", "Municipio", "x_m", "y_m"]],
            on="ID_POLIGONO",
            validate="one_to_one",
        )
        .sort_values("ID_POLIGONO")
        .reset_index(drop=True)
    )
    externas, internas = fuentes["externas"], fuentes["internas"]
    oof = V.construir_oof(tabla, externas)
    return {
        "tabla": tabla,
        "externas": externas,
        "internas": internas,
        "oof": oof,
        "control": fuentes["oof_historico"],
        "metricas_control": fuentes["metricas_historicas"],
    }


def test_particiones_reales_5x10_internas4_y_ningun_id_oculto(reales):
    r = reales
    exterior = V.validar_externas(r["externas"], r["tabla"].ID_POLIGONO)
    interior = V.validar_internas(r["internas"], r["externas"], r["tabla"].ID_POLIGONO)
    assert (
        exterior["filas"] == 6900
        and exterior["parcelas"] == 138
        and exterior["n_particiones"] == 50
    )
    assert interior["filas"] == 22080 and interior["sin_validacion_externa_en_internas"]


def test_oof_real_paridad_completa_y_modelos_fijos(reales):
    resumen = V.validar_oof(reales["oof"], reales["externas"])
    assert resumen["filas_por_modelo"] == 1380 and resumen["filas"] == 4140
    contraste = V.comparar_oof(reales["oof"], reales["control"])
    assert contraste.coincide.all(), contraste
    assert contraste.max_abs_dif_predicho.max() < 1e-8
    assert set(reales["oof"].modelo) == {"GLOBAL", "MUN", "MIX"}


def test_metricas_reales_full138_y_seen135(reales):
    full = V.resumen_metricas(reales["oof"]).set_index("modelo")
    seen = V.resumen_metricas(reales["oof"], "SEEN135").set_index("modelo")
    assert full.n_parcelas.eq(138).all() and full.n_oof.eq(1380).all()
    assert seen.n_parcelas.eq(135).all() and seen.n_oof.eq(1350).all()
    control = reales["metricas_control"].copy()
    control["modelo"] = control.modelo.replace(V.ALIAS_HISTORICOS_03)
    control = control.set_index("modelo")
    for modelo in V.MODELOS_03:
        for metrica in ("RMSE", "MAE", "R2"):
            assert (
                abs(full.loc[modelo, metrica] - control.loc[modelo, f"{metrica}_agrupado"]) < 1e-8
            )
    assert abs(full.loc["GLOBAL", "R2"] - (-0.015042909859176223)) < 1e-8
    assert full.loc["GLOBAL", "R2"] < 0
    assert len(V.por_repeticion(reales["oof"])) == 30
    assert V.por_municipio(reales["oof"]).n_oof.sum() == 4140
