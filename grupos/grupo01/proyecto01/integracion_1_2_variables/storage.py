import os
import requests

SEAWEEDFS_FILER_URL = os.getenv("SEAWEEDFS_FILER_URL", "http://localhost:8888")

def subir_a_seaweedfs(imagen_bytes: bytes) -> str:
    # 1. Intenta subir a SeaweedFS local si está activo
    try:
        response = requests.post(
            f"{SEAWEEDFS_FILER_URL.rstrip('/')}/integral.png",
            files={'file': ('integral.png', imagen_bytes, 'image/png')},
            timeout=1
        )
        if response.status_code in (200, 201):
            return f"{SEAWEEDFS_FILER_URL.rstrip('/')}/integral.png"
    except Exception:
        pass

    # 2. Fallback: sube a un servidor público gratuito para generar una URL https:// directa
    try:
        response = requests.post(
            "https://tmpfiles.org/api/v1/upload",
            files={"file": ("integral.png", imagen_bytes, "image/png")},
            timeout=5
        )
        if response.status_code == 200:
            url_pagina = response.json()["data"]["url"]
            # Convertir URL de vista previa a URL de descarga directa
            direct_url = url_pagina.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            return direct_url
    except Exception as e:
        print(f"Error al subir imagen: {e}")
        
    return "http://localhost:8888/integral.png"
