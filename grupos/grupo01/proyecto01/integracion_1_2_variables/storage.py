import os
import requests

# Configuración del almacenamiento para el servidor
SEAWEEDFS_URL = "http://seaweedfs:8333"
IMG_BUCKET = "grupo01-integracion-1-2-variables-imgs"
PUBLIC_IMG_BASE_URL = "https://rac-unmsm.vekthos.org/img/grupo01-integracion-1-2-variables"


def subir_a_seaweedfs(imagen_bytes: bytes, nombre_archivo: str = "integral.png") -> str | None:
    """
    Sube una imagen al bucket de SeaweedFS del grupo01 y retorna la URL pública.
    Si la subida falla, devuelve None para no interrumpir el flujo.
    """
    url_subida = f"{SEAWEEDFS_URL}/{IMG_BUCKET}/{nombre_archivo}"

    try:
        response = requests.post(
            url_subida,
            files={"file": (nombre_archivo, imagen_bytes, "image/png")},
            timeout=3,
        )
        if response.status_code in (200, 201):
            return f"{PUBLIC_IMG_BASE_URL}/{nombre_archivo}"
    except Exception:
        pass

    # Falla en silencio devolviendo None si SeaweedFS no responde
    return None