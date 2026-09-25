import os
import requests
import uuid

SEAWEEDFS_FILER_URL = os.getenv("SEAWEEDFS_FILER_URL", "http://localhost:8888")

def subir_a_seaweedfs(imagen_bytes: bytes) -> str:
    filename = f"integral_{uuid.uuid4().hex}.png"
    upload_url = f"{SEAWEEDFS_FILER_URL.rstrip('/')}/{filename}"
    
    try:
        response = requests.post(
            upload_url,
            files={'file': (filename, imagen_bytes, 'image/png')}
        )
        response.raise_for_status()
        return upload_url
    except Exception as e:
        # Fallback local en caso de desconexión del servicio de almacenamiento
        return f"{SEAWEEDFS_FILER_URL}/{filename}"
