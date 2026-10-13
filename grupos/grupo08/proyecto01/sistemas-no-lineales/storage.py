"""Sube los reportes HTML al storage del laboratorio (SeaweedFS)."""

import os
import urllib.error
import urllib.request

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
# El despliegue calcula el bucket y su URL pública a partir de la carpeta del
# proyecto y los entrega en estas dos variables (ver docker-compose.yml).
# En local, sin esas variables, quedan vacías y no se sube nada.
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")


def subir_reporte(html: str, identificador: str) -> str | None:
    """Sube el HTML y devuelve su URL pública, o None si no se pudo."""
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None
    key = f"reporte_{identificador}.html"
    peticion = urllib.request.Request(
        f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
        data=html.encode("utf-8"),
        method="PUT",
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    try:
        urllib.request.urlopen(peticion, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None
    return f"{PUBLIC_IMG_BASE_URL}/{key}"
