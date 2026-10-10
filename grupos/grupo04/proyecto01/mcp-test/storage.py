"""Almacenamiento local de informes PDF para modo Windows y Docker."""
from __future__ import annotations

import os
import re
import shutil
import secrets
from pathlib import Path
from urllib.parse import quote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REPORTS_DIR = BASE_DIR / "reports"

def reports_dir() -> Path:
    """Devuelve la carpeta configurable donde se conservan los informes."""
    configured = os.environ.get("MCP_REPORTS_DIR")
    directory = Path(configured).expanduser() if configured else DEFAULT_REPORTS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory.resolve()

def clean_report_name(name: str) -> str:
    """Normaliza un nombre base y evita nombres vacíos o rutas."""
    value = str(name or "").strip()
    value = re.sub(r'[<>:"/\\|?*]', "", value)
    value = re.sub(r"\s+", "_", value).strip(" ._")
    return value[:120] or "interpolacion"

def resolve_pdf(filename: str) -> Path | None:
    """Resuelve únicamente PDF cuyo nombre sea un archivo directo de reports/."""
    value = str(filename or "")
    if not value or Path(value).name != value or not value.lower().endswith(".pdf"):
        return None
    directory = reports_dir()
    candidate = (directory / value).resolve()
    if candidate.parent != directory or not candidate.is_file():
        return None
    return candidate

def public_base_url() -> str:
    """URL pública base configurada para construir enlaces de informe."""
    value = os.environ.get("MCP_PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "http://127.0.0.1:8000"
    return value

def public_origin() -> str:
    parsed = urlsplit(public_base_url())
    return f"{parsed.scheme}://{parsed.netloc}"

def report_metadata(filename: str) -> dict:
    """Devuelve metadatos y las URL de vista previa y descarga."""
    path = resolve_pdf(filename)
    if path is None:
        raise FileNotFoundError("No se encontró el PDF solicitado.")
    encoded_name = quote(path.name, safe="")
    base = public_base_url()
    return {
        "pdf": str(path),
        "name": path.name,
        "preview_url": f"{base}/reports/{encoded_name}/preview",
        "download_url": f"{base}/reports/{encoded_name}/download",
        "mime_type": "application/pdf",
    }

def persist_pdf(source: Path, report_name: str) -> dict:
    """Copia el PDF compilado a reports/ con un nombre único y seguro."""
    directory = reports_dir()
    base_name = clean_report_name(report_name)
    while True:
        # El nombre aleatorio evita que las URL públicas sean fáciles de adivinar.
        token = secrets.token_urlsafe(18)
        candidate = directory / f"{base_name}_{token}.pdf"
        try:
            descriptor = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as destination, Path(source).open("rb") as input_file:
                shutil.copyfileobj(input_file, destination)
        except Exception:
            candidate.unlink(missing_ok=True)
            raise
        return report_metadata(candidate.name)
