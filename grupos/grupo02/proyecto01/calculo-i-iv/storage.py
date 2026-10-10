"""Storage de imágenes (SeaweedFS): subida y generación de enlaces Markdown.

Conecta con el servidor interno SeaweedFS (http://seaweedfs:8333) vía HTTP PUT.
El despliegue inyecta LAB_IMG_BUCKET y LAB_PUBLIC_IMG_URL.
En local, si las variables no están definidas, falla en silencio y devuelve None.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
import uuid

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"

IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")


def ensure_bucket() -> None:
    """Crea el bucket en SeaweedFS si aún no existe."""
    if not IMG_BUCKET:
        return
    try:
        req = urllib.request.Request(f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/", method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, urllib.error.HTTPError):
        pass


def subir_imagen(png_bytes: bytes) -> str | None:
    """Sube el PNG a SeaweedFS con una clave aleatoria y devuelve la URL pública.

    Devuelve None si el storage no respondió o si no está configurado (ej. en local).
    """
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None
    key = f"{uuid.uuid4().hex}.png"
    try:
        req = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
            data=png_bytes,
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None
    return f"{PUBLIC_IMG_BASE_URL}/{key}"
