"""Almacenamiento remoto de reportes PDF en SeaweedFS para el MCP del grupo04."""
from __future__ import annotations

import os
import re
import secrets
import urllib.error
import urllib.request
from urllib.parse import quote, urlsplit

SEAWEEDFS_S3_URL = "http://seaweedfs:8333"
IMG_BUCKET = "grupo04-mcp-test-imgs"
PUBLIC_IMG_BASE_URL = "https://rac-unmsm.vekthos.org/img/grupo04-mcp-test"


def clean_report_name(name: str) -> str:
    """Normaliza el nombre visible del informe, sin aceptar rutas."""
    value = str(name or "").strip()
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", "_", value).strip(" ._")
    return value[:120] or "resolucion_numerica"


def resolve_pdf(filename: str) -> str | None:
    """Valida el nombre de un objeto PDF y devuelve su clave segura."""
    value = str(filename or "")
    if (
        not value
        or "/" in value
        or "\\" in value
        or value in {".", ".."}
        or not value.lower().endswith(".pdf")
        or any(ord(character) < 32 for character in value)
    ):
        return None
    return value


def public_base_url() -> str:
    """Construye la URL pública de la app con variables que inyecta el despliegue."""
    domain = os.environ.get("LAB_DOMAIN", "").strip()
    public_path = os.environ.get("LAB_PUBLIC_PATH", "").strip()
    if not domain:
        domain = "127.0.0.1:8000"

    if "://" in domain:
        parsed = urlsplit(domain)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return "http://127.0.0.1:8000"
        scheme, netloc = parsed.scheme, parsed.netloc
    else:
        netloc = domain.split("/", 1)[0].strip()
        if not netloc or any(character.isspace() for character in netloc):
            return "http://127.0.0.1:8000"
        scheme = "http" if netloc.startswith(
            ("localhost", "127.0.0.1", "[::1]")
        ) else "https"

    segments = [
        segment for segment in public_path.strip("/").split("/")
        if segment and segment not in {".", ".."}
    ]
    path = "/" + "/".join(segments) if segments else ""
    return f"{scheme}://{netloc}{path}".rstrip("/")


def public_origin() -> str:
    """Devuelve el origen para la política de contenido de las MCP Apps."""
    parsed = urlsplit(public_base_url())
    return f"{parsed.scheme}://{parsed.netloc}"


def _object_url(key: str) -> str:
    return (
        f"{SEAWEEDFS_S3_URL.rstrip('/')}/"
        f"{quote(IMG_BUCKET, safe='')}/{quote(key, safe='')}"
    )


def ensure_bucket() -> None:
    """Crea el bucket si aún no existe; la operación es idempotente."""
    bucket_url = f"{SEAWEEDFS_S3_URL.rstrip('/')}/{quote(IMG_BUCKET, safe='')}/"
    request = urllib.request.Request(bucket_url, method="PUT")
    try:
        with urllib.request.urlopen(request, timeout=5):
            pass
    except urllib.error.HTTPError as exc:
        if exc.code not in {409, 412}:
            raise RuntimeError(
                f"SeaweedFS no pudo preparar el bucket ({exc.code})."
            ) from exc


def report_metadata(filename: str) -> dict:
    """Devuelve enlaces públicos de vista previa y descarga del PDF."""
    key = resolve_pdf(filename)
    if key is None:
        raise ValueError("El nombre del PDF no es válido.")
    encoded_name = quote(key, safe="")
    base = public_base_url()
    return {
        "pdf": key,
        "name": key,
        "preview_url": f"{base}/reports/{encoded_name}/preview",
        "download_url": f"{base}/reports/{encoded_name}/download",
        "mime_type": "application/pdf",
        "storage": "seaweedfs",
    }


def persist_pdf(pdf_bytes: bytes, report_name: str) -> dict:
    """Sube un PDF generado en memoria a SeaweedFS y devuelve sus enlaces."""
    if not isinstance(pdf_bytes, (bytes, bytearray)) or not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("El contenido generado no tiene formato PDF.")
    base_name = clean_report_name(report_name)
    key = f"{base_name}_{secrets.token_urlsafe(18)}.pdf"

    ensure_bucket()
    request = urllib.request.Request(
        _object_url(key),
        data=bytes(pdf_bytes),
        headers={"Content-Type": "application/pdf"},
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=15):
            pass
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise RuntimeError("No se pudo guardar el PDF en SeaweedFS.") from exc

    return report_metadata(key)


def load_pdf(filename: str) -> bytes | None:
    """Descarga de SeaweedFS el PDF indicado; devuelve None si no existe."""
    key = resolve_pdf(filename)
    if key is None:
        return None
    request = urllib.request.Request(
        _object_url(key),
        headers={"Accept": "application/pdf"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(
            f"SeaweedFS no pudo leer el PDF ({exc.code})."
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("No se pudo conectar con SeaweedFS.") from exc
