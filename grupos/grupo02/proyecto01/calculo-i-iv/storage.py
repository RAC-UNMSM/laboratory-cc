"""SeaweedFS opcional: sin persistencia local ni destinos elegidos por el usuario."""

import asyncio
import logging
import os
import re
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
IMG_BUCKET = os.getenv("LAB_IMG_BUCKET", "")
PUBLIC_IMG_BASE_URL = os.getenv("LAB_PUBLIC_IMG_URL", "")


def subir_imagen(png: bytes) -> str | None:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", IMG_BUCKET):
        return None
    if urlparse(PUBLIC_IMG_BASE_URL).scheme not in ("http", "https"):
        return None
    name = uuid4().hex + ".png"
    try:
        req = Request(
            f"{SEAWEEDFS_S3_URL}/{IMG_BUCKET}/{name}",
            data=png,
            headers={"Content-Type": "image/png"},
            method="PUT",
        )
        with urlopen(req, timeout=3) as response:
            if response.status not in (200, 201, 204):
                return None
        return PUBLIC_IMG_BASE_URL.rstrip("/") + "/" + name
    except (OSError, URLError, ValueError):
        logging.getLogger(__name__).warning("Publicación de imagen no disponible.")
        return None


async def upload(png):
    return await asyncio.to_thread(subir_imagen, png)
