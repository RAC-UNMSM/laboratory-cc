"""Storage de imágenes (SeaweedFS): rol "Storage/infra" del pilotaje MCP.

El bloque ImageContent de MCP (bytes crudos) llega al modelo pero ningún
cliente de chat (Claude Code, Desktop, web) lo pinta solo en el hilo
principal. Lo único que un cliente de chat renderiza solo es una URL https
normal dentro del texto de respuesta. Por eso este módulo sube cada PNG a
SeaweedFS (mismo storage que ya usa el lab) y server.py arma el link markdown
con lo que devuelve. "seaweedfs" resuelve por DNS interno de Docker porque
este contenedor comparte la red "lab_net" con él.

SEAWEEDFS_S3_URL es igual para todos los grupos; IMG_BUCKET y PUBLIC_IMG_BASE_URL
son propios del grupo.
"""

import os
import urllib.error
import urllib.request
import uuid

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "grupo03-extrapolacion-richardson-mcp-imgs")
# Ruta pública en Caddy (ver caddy/Caddyfile), solo lectura, sin login: el
# fetch de la imagen lo hace el cliente de chat de forma anónima.
PUBLIC_IMG_BASE_URL = os.environ.get(
    "LAB_PUBLIC_IMG_URL",
    "https://rac-unmsm.vekthos.org/img/grupo03-extrapolacion-richardson-mcp",
)


def ensure_bucket() -> None:
    """Crea el bucket si no existe. Falla en silencio: si SeaweedFS no está
    listo todavía (orden de arranque de contenedores) o el bucket ya existe,
    no es motivo para tumbar el servidor -- subir_imagen() reintenta la
    conexión en cada llamada."""
    try:
        req = urllib.request.Request(f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/", method="PUT")
        urllib.request.urlopen(req, timeout=5).close()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        pass


def subir_imagen(png_bytes: bytes) -> str | None:
    """Sube el PNG con una key random (no adivinable, no secuencial) y
    devuelve la URL pública, o None si el storage no respondió -- en ese caso
    las tools siguen funcionando igual, solo sin link (el ImageContent de
    respaldo todavía llega al modelo)."""
    key = f"{uuid.uuid4().hex}.png"
    try:
        req = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
            data=png_bytes,
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        urllib.request.urlopen(req, timeout=10).close()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None
    return f"{PUBLIC_IMG_BASE_URL}/{key}"
