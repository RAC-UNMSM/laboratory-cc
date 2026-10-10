import json
from datetime import datetime, timezone
from pathlib import Path


RUTA_DATOS = (
    Path(__file__).resolve().parent
    / "data"
    / "historial.jsonl"
)


def guardar_registro(
    n,
    regla,
    estado,
    resultado=None
):
    """
    Guarda un registro de una consulta realizada al sistema.

    Parámetros
    ----------
    n:
        Dimensión de la transformación.

    regla:
        Regla de correspondencia recibida.

    estado:
        Resultado general de la operación.
        Ejemplos:
            "invertible"
            "no_invertible"
            "entrada_invalida"

    resultado:
        Información adicional opcional.
    """

    RUTA_DATOS.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    registro = {
        "fecha_hora": datetime.now(
            timezone.utc
        ).isoformat(),
        "n": n,
        "regla": regla,
        "estado": estado,
        "resultado": resultado
    }

    with RUTA_DATOS.open(
        "a",
        encoding="utf-8"
    ) as archivo:

        archivo.write(
            json.dumps(
                registro,
                ensure_ascii=False
            )
            + "\n"
        )

    return registro


def leer_historial():
    """
    Lee todos los registros almacenados.

    Si todavía no existe el archivo,
    devuelve una lista vacía.
    """

    if not RUTA_DATOS.exists():
        return []

    registros = []

    with RUTA_DATOS.open(
        "r",
        encoding="utf-8"
    ) as archivo:

        for linea in archivo:

            linea = linea.strip()

            if linea:
                registros.append(
                    json.loads(linea)
                )

    return registros