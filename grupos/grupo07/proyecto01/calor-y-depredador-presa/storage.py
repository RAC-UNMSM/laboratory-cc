import os
import urllib.error
import urllib.request
import uuid

# URL interna de SeaweedFS en la red Docker (NO TOCAR)
SEAWEEDFS_S3_URL = "http://seaweedfs:8333"

# Variables de entorno inyectadas por el despliegue (respaldo vacío para entorno local)
IMG_BUCKET = os.getenv("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.getenv("LAB_PUBLIC_IMG_URL", "")


def subir_imagen(png_bytes: bytes) -> str | None:
    """
    Sube los bytes del PNG a SeaweedFS con una key única.
    Devuelve la URL pública para que Claude la renderice, o None si falla.
    """
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None

    key = f"{uuid.uuid4().hex}.png"
    url_subida = f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}"

    try:
        req = urllib.request.Request(
            url_subida,
            data=png_bytes,
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        urllib.request.urlopen(req, timeout=5)

        base_url = PUBLIC_IMG_BASE_URL.rstrip("/")
        return f"{base_url}/{key}"

    except (urllib.error.URLError, urllib.error.HTTPError):
        return None


def subir_reporte(html: str) -> str | None:
    """Sube el reporte HTML a SeaweedFS y devuelve su URL pública, o None si falla."""
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None

    key = f"{uuid.uuid4().hex}.html"
    try:
        req = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
            data=html.encode("utf-8"),
            method="PUT",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        urllib.request.urlopen(req, timeout=10)
        return f"{PUBLIC_IMG_BASE_URL.rstrip('/')}/{key}"
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None