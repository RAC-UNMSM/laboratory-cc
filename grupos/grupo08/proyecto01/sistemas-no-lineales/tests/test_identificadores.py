import re

from identificadores import (
    crear_identificador,
    guardar_archivo_identificado,
    ruta_con_identificador,
)


def test_crear_identificador_es_uuid_hexadecimal_unico():
    primero = crear_identificador()
    segundo = crear_identificador()

    assert re.fullmatch(r"[0-9a-f]{32}", primero)
    assert re.fullmatch(r"[0-9a-f]{32}", segundo)
    assert primero != segundo


def test_ruta_con_identificador_preserva_extension_y_directorio(tmp_path):
    original = tmp_path / "ejercicio-01.html"

    identificada, identificador = ruta_con_identificador(original)

    assert identificada.parent == original.parent
    assert identificada.suffix == original.suffix
    assert identificada.stem == f"{original.stem}_{identificador}"


def test_ruta_con_identificador_rechaza_id_no_hexadecimal(tmp_path):
    try:
        ruta_con_identificador(tmp_path / "salida.html", "id-invalido")
    except ValueError as error:
        assert "32 caracteres hexadecimales" in str(error)
    else:
        raise AssertionError("Se esperaba ValueError para un ID invalido.")


def test_guardar_archivo_identificado_admite_texto_y_bytes(tmp_path):
    texto = guardar_archivo_identificado(tmp_path / "ejercicio.csv", "x,y\n1,2\n")
    binario = guardar_archivo_identificado(tmp_path / "grafico.png", b"PNG")

    assert texto.read_text(encoding="utf-8") == "x,y\n1,2\n"
    assert binario.read_bytes() == b"PNG"
    assert re.search(r"_[0-9a-f]{32}\.csv$", texto.name)
    assert re.search(r"_[0-9a-f]{32}\.png$", binario.name)