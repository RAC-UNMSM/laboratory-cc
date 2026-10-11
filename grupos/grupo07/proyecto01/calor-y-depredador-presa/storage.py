import os
import urllib.error
import urllib.request
import uuid

# URL interna de SeaweedFS en la red Docker
SEAWEEDFS_S3_URL = "http://seaweedfs:8333"

# Variables de entorno inyectadas por el despliegue (Vital para tu PR)
# Usa un fallback con el nombre de tu proyecto por si se ejecuta en local
IMG_BUCKET = os.getenv("LAB_IMG_BUCKET", "grupo07-proyecto01-calor-y-depredador-presa-imgs")
PUBLIC_IMG_BASE_URL = os.getenv(
    "LAB_PUBLIC_IMG_URL",
    "https://rac-unmsm.vekthos.org/img/grupo07-proyecto01-calor-y-depredador-presa"
)

def subir_imagen(png_bytes: bytes) -> str | None:
    """
    Sube los bytes del PNG a SeaweedFS con una key única.
    Devuelve la URL pública para que Claude la renderice, o None si falla.
    """
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
        
        # Formatear y retornar la URL pública
        base_url = PUBLIC_IMG_BASE_URL.rstrip("/")
        return f"{base_url}/{key}"
        
    except (urllib.error.URLError, urllib.error.HTTPError):
        # Fallo silencioso: si la red Docker no está arriba, retorna None
        return None