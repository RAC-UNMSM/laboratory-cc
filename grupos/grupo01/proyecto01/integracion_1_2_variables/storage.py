import os
import uuid
import requests

# URL interna fija de SeaweedFS en la red Docker del laboratorio (lab_net)
SEAWEEDFS_URL = "http://seaweedfs:8333"

# Variables de entorno inyectadas por el despliegue
IMG_BUCKET = os.getenv("LAB_IMG_BUCKET", "grupo01-integracion-1-2-variables-imgs")
PUBLIC_IMG_BASE_URL = os.getenv(
    "LAB_PUBLIC_IMG_URL",
    "https://rac-unmsm.vekthos.org/img/grupo01-integracion-1-2-variables",
)


def subir_a_seaweedfs(
    imagen_bytes: bytes, nombre_archivo: str | None = None
) -> str | None:
    """Sube una imagen al bucket de SeaweedFS del grupo y retorna la URL pública.

    Si la subida falla, devuelve None para no interrumpir el flujo.
    """
    if not nombre_archivo:
        nombre_archivo = f"{uuid.uuid4().hex}.png"

    url_subida = f"{SEAWEEDFS_URL}/{IMG_BUCKET}/{nombre_archivo}"

    try:
        response = requests.put(
            url_subida,
            data=imagen_bytes,
            headers={"Content-Type": "image/png"},
            timeout=3,
        )
        if response.status_code in (200, 201):
            base_url = PUBLIC_IMG_BASE_URL.rstrip("/")
            return f"{base_url}/{nombre_archivo}"
    except Exception:
        pass

    return None