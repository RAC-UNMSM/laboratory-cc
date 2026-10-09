import os
import uuid
import requests

# Configuración del almacenamiento obtenida desde las variables de entorno del servidor
SEAWEEDFS_URL = os.getenv("SEAWEEDFS_URL", "http://seaweedfs:8333")
IMG_BUCKET = os.getenv("LAB_IMG_BUCKET", "grupo01-integracion-1-2-variables-imgs")
PUBLIC_IMG_BASE_URL = os.getenv(
    "LAB_PUBLIC_IMG_URL",
    "https://rac-unmsm.vekthos.org/img/grupo01-integracion-1-2-variables",
)


def subir_a_seaweedfs(
    imagen_bytes: bytes, nombre_archivo: str | None = None
) -> str | None:
    """Sube una imagen al bucket de SeaweedFS del grupo01 y retorna la URL pública.

    Si la subida falla, devuelve None para no interrumpir el flujo.
    """
    # Si no se especifica nombre, genera una clave única con UUID
    if not nombre_archivo:
        nombre_archivo = f"{uuid.uuid4().hex}.png"

    url_subida = f"{SEAWEEDFS_URL}/{IMG_BUCKET}/{nombre_archivo}"

    try:
        # Petición PUT con los bytes en el cuerpo de la solicitud
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

    # Falla en silencio devolviendo None si SeaweedFS no responde
    return None