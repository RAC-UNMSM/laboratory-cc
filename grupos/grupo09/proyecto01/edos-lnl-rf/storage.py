"""Storage del informe (SeaweedFS): rol "Storage/infra" del grupo 09.

Mismo patrón que el piloto del laboratorio (`grupos/g01/semana01/derivadas1/
storage.py`): subir el resultado a un storage compartido → devolver una URL
pública → nunca romper el flujo principal si el storage falla. Lo que cambia es
el *tipo de dato*: la propuesta de este grupo entrega un informe HTML
interactivo (plotly + KaTeX), no un PNG, así que aquí se sube HTML.

El bucket y la URL pública los pone el despliegue a partir de la carpeta del
proyecto (`LAB_IMG_BUCKET` y `LAB_PUBLIC_IMG_URL`, pasadas por el
`docker-compose.yml`). En local, sin esas variables, no se sube nada y la
herramienta responde igual, sin enlace.
"""

import os
import urllib.error
import urllib.request
import uuid

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"                      # igual para todos
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")               # lo pone el despliegue
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")  # lo pone el despliegue


def ensure_bucket() -> None:
    """Crea el bucket si no existe. El despliegue ya lo crea; esto no hace daño.

    Falla en silencio: si SeaweedFS no responde o el bucket ya existe, no es
    motivo para tumbar el servidor.
    """
    if not IMG_BUCKET:
        return
    try:
        req = urllib.request.Request(f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/", method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        pass


def subir_html(html: str) -> str | None:
    """Sube la página con un nombre aleatorio y devuelve su URL pública, o None.

    Cada informe lleva su propio `uuid` para no pisar el de otro análisis (u
    otro usuario). Devolver None no es un error que haya que propagar: quien
    llama lo trata como "no hay enlace".
    """
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
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None
    return f"{PUBLIC_IMG_BASE_URL}/{key}"
