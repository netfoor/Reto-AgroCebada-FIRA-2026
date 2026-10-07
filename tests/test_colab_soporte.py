"""Soporte de ejecución y transporte; mocks sin red ni datos agrícolas reales."""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import importlib.util
from pathlib import Path

import pytest


def _modulo():
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "colab_soporte.py"
    spec = importlib.util.spec_from_file_location("colab_soporte", ruta)
    modulo = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(modulo)
    return modulo


soporte = _modulo()
VERSIONES = {
    "numpy": "2.4.4", "pandas": "2.2.3", "matplotlib": "3.11.2",
    "pyshp": "3.1.6", "shapely": "2.1.2", "pyproj": "3.8.0", "gdown": "5.2.2",
}
PERFIL = "\n".join(f"{nombre}=={version}" for nombre, version in VERSIONES.items()) + "\n"
CONTENIDO = b"ZIP sintetico: prueba de identidad de bytes, sin etiquetas."
SHA = hashlib.sha256(CONTENIDO).hexdigest()
FILE_ID = "archivo_autorizado_1234567890"


def _sin_importar(*args, **kwargs):
    """Los mocks comprueban lógica de preparación sin importar binarios científicos."""


def _consultar(estado):
    def consultar(nombre):
        if nombre not in estado:
            raise metadata.PackageNotFoundError(nombre)
        return estado[nombre]

    return consultar


def _preparar(estado, *, en_colab=True, habilitar=True, modulos=None, ejecutar=None):
    return soporte.preparar_colab(
        PERFIL, en_colab=en_colab, habilitar=habilitar,
        consultar_version=_consultar(estado), modulos={} if modulos is None else modulos,
        ejecutar=ejecutar or (lambda argv: pytest.fail(f"pip no autorizado: {argv}")),
        informar=lambda mensaje: None, verificar_importaciones=_sin_importar,
    )


def _obtener(destino, descargar, **cambios):
    opciones = {
        "file_id": FILE_ID, "sha256_esperado": SHA,
        "bytes_esperados": len(CONTENIDO), "permitir_descarga": True,
        "descargar": descargar,
    }
    opciones.update(cambios)
    return soporte.obtener_dataset(destino, **opciones)


def test_versiones_requeridas_ignora_transitivas_y_preserva_pins():
    perfil = PERFIL + "urllib3==2.8.0\n"
    assert soporte.versiones_requeridas(perfil) == VERSIONES


def test_versiones_requeridas_permite_subconjunto_explicito():
    assert soporte.versiones_requeridas(PERFIL, nombres=("numpy",)) == {"numpy": "2.4.4"}


def test_versiones_requeridas_rechaza_pin_duplicado():
    with pytest.raises(ValueError):
        soporte.versiones_requeridas(PERFIL + "numpy==1.0.0\n")


def test_versiones_requeridas_rechaza_dependencia_obligatoria_ausente():
    with pytest.raises(ValueError):
        soporte.versiones_requeridas("numpy==2.4.4\n")


def test_local_nunca_instala_aunque_se_solicite_preparacion():
    salida = _preparar({}, en_colab=False)
    assert salida["estado"] == "local_sin_instalar"
    assert salida["cambios"] == []


def test_colab_compatible_reutiliza_entorno_sin_pip():
    salida = _preparar(dict(VERSIONES))
    assert salida["estado"] == "colab_existente"
    assert salida["cambios"] == []
    assert salida["instaladas"] == VERSIONES
    assert salida["reinicio_requerido"] is False


def test_colab_desactivado_con_versiones_correctas_no_instala():
    assert _preparar(dict(VERSIONES), habilitar=False)["estado"] == "colab_existente"


def test_colab_desactivado_con_diferencias_falla_sin_instalar():
    estado = {**VERSIONES, "numpy": "1.0.0"}
    with pytest.raises(RuntimeError):
        _preparar(estado, habilitar=False)


def test_pip_solo_corrige_raices_necesarias_con_perfil_completo_como_restriccion():
    estado = {**VERSIONES, "pandas": "1.0.0"}
    del estado["gdown"]
    llamadas = []

    def ejecutar(argv):
        llamadas.append(argv)
        assert "--only-binary=:all:" in argv
        assert "-c" in argv or "--constraint" in argv
        posicion = argv.index("-c") if "-c" in argv else argv.index("--constraint")
        assert Path(argv[posicion + 1]).read_text(encoding="utf-8") == PERFIL
        pins = {argumento for argumento in argv if "==" in argumento}
        assert pins == {"pandas==2.2.3", "gdown==5.2.2"}
        assert "-r" not in argv and "--requirement" not in argv
        estado.update(VERSIONES)

    salida = _preparar(estado, ejecutar=ejecutar)
    assert len(llamadas) == 1
    assert set(salida["cambios"]) == {"pandas==2.2.3", "gdown==5.2.2"}
    assert salida["instaladas"] == VERSIONES
    assert salida["estado"] == "colab_instalado"


def test_instalacion_no_declara_exito_si_pip_no_corrige_versiones():
    estado = {**VERSIONES, "numpy": "1.0.0"}
    with pytest.raises(RuntimeError):
        _preparar(estado, ejecutar=lambda argv: None)


@pytest.mark.parametrize("nombre_modulo", ["numpy", "numpy.core"])
def test_binario_precargado_exige_reinicio_explicito_sin_matar_sesion(nombre_modulo):
    estado = {**VERSIONES, "numpy": "1.0.0"}

    def ejecutar(argv):
        estado.update(VERSIONES)

    with pytest.raises(soporte.ReinicioColabRequerido) as error:
        _preparar(estado, modulos={nombre_modulo: object()}, ejecutar=ejecutar)
    assert error.value.cambios
    assert error.value.modulos_cargados


def test_fallo_pip_no_se_oculta():
    estado = {**VERSIONES, "numpy": "1.0.0"}

    def fallar(argv):
        raise RuntimeError("pip fallo controlado")

    with pytest.raises(RuntimeError, match="pip fallo controlado"):
        _preparar(estado, ejecutar=fallar)


def test_validar_dataset_exige_hash_y_tamano(tmp_path):
    destino = tmp_path / "DataSet.zip"
    destino.write_bytes(CONTENIDO)
    soporte.validar_dataset(destino, SHA, len(CONTENIDO))
    with pytest.raises(ValueError):
        soporte.validar_dataset(destino, "0" * 64, len(CONTENIDO))
    with pytest.raises(ValueError):
        soporte.validar_dataset(destino, SHA, len(CONTENIDO) + 1)


def test_cache_verificada_no_descarga_ni_requiere_id(tmp_path):
    destino = tmp_path / "DataSet.zip"
    destino.write_bytes(CONTENIDO)

    def no_descargar(**kwargs):
        pytest.fail("No debe haber red cuando existe una copia verificada.")

    assert _obtener(destino, no_descargar, file_id=None, permitir_descarga=False) == destino
    assert destino.read_bytes() == CONTENIDO


def test_cache_corrupta_no_se_sobrescribe_ni_descarga(tmp_path):
    destino = tmp_path / "DataSet.zip"
    destino.write_bytes(b"contenido anterior preservado")

    def no_descargar(**kwargs):
        pytest.fail("Una copia distinta debe preservarse, no ser reemplazada.")

    with pytest.raises(ValueError):
        _obtener(destino, no_descargar)
    assert destino.read_bytes() == b"contenido anterior preservado"


@pytest.mark.parametrize("opciones", [{"file_id": None}, {"permitir_descarga": False}])
def test_archivo_ausente_no_descarga_sin_id_y_permiso(tmp_path, opciones):
    destino = tmp_path / "DataSet.zip"

    def no_descargar(**kwargs):
        pytest.fail("La ausencia de configuración o permiso debe impedir la descarga.")

    with pytest.raises((ValueError, RuntimeError, FileNotFoundError)):
        _obtener(destino, no_descargar, **opciones)
    assert not destino.exists()


def test_descarga_autorizada_valida_temporal_antes_de_publicar(tmp_path):
    destino = tmp_path / "cache" / "DataSet.zip"
    llamadas = []

    def descargar(**kwargs):
        llamadas.append(kwargs)
        assert kwargs["id"] == FILE_ID
        assert kwargs["use_cookies"] is False
        temporal = Path(kwargs["output"])
        assert temporal != destino
        assert not destino.exists()
        temporal.write_bytes(CONTENIDO)
        return str(temporal)

    assert _obtener(destino, descargar) == destino
    assert len(llamadas) == 1
    assert destino.read_bytes() == CONTENIDO


@pytest.mark.parametrize("contenido", [b"pagina HTML o enlace equivocado", b"x" * len(CONTENIDO)])
def test_descarga_incorrecta_no_materializa_dataset(tmp_path, contenido):
    destino = tmp_path / "DataSet.zip"

    def descargar(**kwargs):
        Path(kwargs["output"]).write_bytes(contenido)
        return kwargs["output"]

    with pytest.raises(RuntimeError):
        _obtener(destino, descargar)
    assert not destino.exists()
    rechazados = list(tmp_path.glob("*.rechazado*"))
    assert rechazados, "Una descarga rechazada debe identificarse sin sustituir el ZIP fuente."
    assert any(ruta.read_bytes() == contenido for ruta in rechazados)


def test_fallo_de_descarga_no_crea_archivo_final(tmp_path):
    destino = tmp_path / "DataSet.zip"

    def descargar(**kwargs):
        raise RuntimeError("permiso de Drive insuficiente")

    with pytest.raises(RuntimeError):
        _obtener(destino, descargar)
    assert not destino.exists()


@pytest.mark.parametrize("file_id", ["", "abc", "https://drive.google.com/file/d/123/view"])
def test_descarga_rechaza_configuracion_no_id_sin_acceder_a_red(tmp_path, file_id):
    def no_descargar(**kwargs):
        pytest.fail("Una URL o un ID incompleto no es configuración de transporte válida.")

    with pytest.raises(ValueError):
        _obtener(tmp_path / "DataSet.zip", no_descargar, file_id=file_id)


@pytest.mark.parametrize("contrato", [
    {"sha256_esperado": "sha_incompleto"}, {"bytes_esperados": 0},
])
def test_descarga_no_acepta_contrato_de_integridad_invalido(tmp_path, contrato):
    def no_descargar(**kwargs):
        pytest.fail("El contrato de integridad debe validarse antes de descargar.")

    with pytest.raises(ValueError):
        _obtener(tmp_path / "DataSet.zip", no_descargar, **contrato)


@pytest.mark.parametrize("concurrente", [CONTENIDO, b"copia concurrente diferente"])
def test_publicacion_no_reemplaza_aparicion_concurrente(tmp_path, monkeypatch, concurrente):
    destino = tmp_path / "DataSet.zip"
    enlazar_original = soporte.os.link

    def aparecer_y_enlazar(origen, objetivo):
        destino.write_bytes(concurrente)
        return enlazar_original(origen, objetivo)

    monkeypatch.setattr(soporte.os, "link", aparecer_y_enlazar)

    def descargar(**kwargs):
        Path(kwargs["output"]).write_bytes(CONTENIDO)
        return kwargs["output"]

    if concurrente == CONTENIDO:
        assert _obtener(destino, descargar) == destino
    else:
        with pytest.raises(RuntimeError):
            _obtener(destino, descargar)
    assert destino.read_bytes() == concurrente


def test_reinicio_detecta_transitiva_precargada_modificada_por_pip():
    perfil = PERFIL + "python-dateutil==2.9.0.post0\n"
    estado = {**VERSIONES, "pandas": "1.0.0", "python-dateutil": "2.8.0"}

    def ejecutar(argv):
        estado.update(VERSIONES)
        estado["python-dateutil"] = "2.9.0.post0"

    with pytest.raises(soporte.ReinicioColabRequerido) as error:
        soporte.preparar_colab(
            perfil, en_colab=True, consultar_version=_consultar(estado),
            modulos={"dateutil.parser": object()}, ejecutar=ejecutar,
            informar=lambda mensaje: None, verificar_importaciones=_sin_importar,
        )
    assert "python-dateutil" in error.value.modulos_cargados
