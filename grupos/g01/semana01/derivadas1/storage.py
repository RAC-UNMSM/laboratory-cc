"""Storage de imágenes (SeaweedFS): rol "Storage/infra" del pilotaje MCP.

El bloque ImageContent de MCP (bytes crudos) llega al modelo pero ningún
cliente de chat (Claude Code, Desktop, web) lo pinta solo en el hilo
principal -- solo aparece si el usuario expande el detalle del tool call.
Lo único que un cliente de chat renderiza solo, sin pedirlo, es una URL
https normal dentro del texto de respuesta. Por eso este módulo sube el PNG
a SeaweedFS (mismo storage que ya usa este lab, ver docker-compose.yml) --
server.py arma el link markdown con lo que devuelve. "seaweedfs" resuelve
por DNS interno de Docker porque este contenedor comparte la red "lab_net"
con él.
"""

import os
import urllib.error
import urllib.request
import uuid

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
# El bucket y su URL pública NO se escriben a mano: el despliegue los calcula
# de la carpeta del proyecto (grupo + nombre de la carpeta, ej.
# "grupo04-interpolacion-imgs") y se los entrega al contenedor en estas dos
# variables -- ver el bloque `environment:` de docker-compose.yml. Con ese
# mismo nombre el servidor crea solo la ruta pública /img/<grupo>-<carpeta>/
# (solo lectura, sin login: el fetch de la imagen lo hace el cliente de chat
# de forma anónima, sin la cookie de sesión del usuario).
# En local (`python server.py`, sin esas variables) quedan vacías y este
# módulo simplemente no sube nada.
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")


def ensure_bucket() -> None:
    """Crea el bucket si no existe. Falla en silencio: si SeaweedFS no está
    listo todavía (orden de arranque de contenedores) o el bucket ya existe,
    no es motivo para tumbar el servidor -- subir_imagen() reintenta la
    conexión de todos modos en cada llamada."""
    if not IMG_BUCKET:
        return
    try:
        req = urllib.request.Request(f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/", method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, urllib.error.HTTPError):
        pass


def subir_imagen(png_bytes: bytes) -> str | None:
    """Sube el PNG a SeaweedFS con una key random (no adivinable, no
    secuencial) y devuelve la URL pública, o None si el storage no
    respondió -- en ese caso derivar() sigue funcionando igual, solo sin
    link (el ImageContent de respaldo todavía llega al modelo)."""
    if not IMG_BUCKET or not PUBLIC_IMG_BASE_URL:
        return None
    key = f"{uuid.uuid4().hex}.png"
    try:
        req = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{key}",
            data=png_bytes,
            method="PUT",
            headers={"Content-Type": "image/png"},
        )
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError):
        return None
    return f"{PUBLIC_IMG_BASE_URL}/{key}"
