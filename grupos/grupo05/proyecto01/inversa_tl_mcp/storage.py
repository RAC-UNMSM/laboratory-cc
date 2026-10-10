"""Publicación de gráficos en el SeaweedFS interno del laboratorio."""
import os
import urllib.error
import urllib.request
import uuid

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")


def subir_imagen(png_bytes: bytes) -> str | None:
    """Devuelve la URL pública; sin configuración o sin storage devuelve None."""
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None
    key = f"{uuid.uuid4().hex}.png"
    try:
        request = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
            data=png_bytes,
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        with urllib.request.urlopen(request, timeout=10):
            pass
    except (urllib.error.URLError, TimeoutError):
        return None
    return f"{PUBLIC_IMG_BASE_URL.rstrip('/')}/{key}"
