"""Identificadores unicos para los archivos del proyecto y sus ejercicios."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4


_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def crear_identificador() -> str:
    """Crea un UUID hexadecimal de 32 caracteres, compatible con nombres en Rclone."""
    return uuid4().hex


def ruta_con_identificador(
    ruta: str | Path,
    identificador: str | None = None,
) -> tuple[Path, str]:
    """Devuelve una ruta con ID antes de la extension y el ID utilizado."""
    destino = Path(ruta)
    id_archivo = identificador or crear_identificador()
    if not _ID_PATTERN.fullmatch(id_archivo):
        raise ValueError("El identificador debe contener 32 caracteres hexadecimales.")

    ruta_identificada = destino.with_name(
        f"{destino.stem}_{id_archivo}{destino.suffix}"
    )
    return ruta_identificada, id_archivo


def guardar_archivo_identificado(
    ruta: str | Path,
    contenido: str | bytes,
    identificador: str | None = None,
    encoding: str = "utf-8",
) -> Path:
    """Guarda texto o bytes con un UUID en el nombre; sirve para ejercicios nuevos."""
    destino, _ = ruta_con_identificador(ruta, identificador)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contenido, bytes):
        destino.write_bytes(contenido)
    else:
        destino.write_text(contenido, encoding=encoding)
    return destino