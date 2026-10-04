"""Ubicación y listado de archivos generados por MCP-TEST."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "reports"
ALLOWED_EXTENSIONS = {".html", ".pdf", ".svg"}


def ensure_storage() -> Path:
    """Crea el directorio persistente de reportes y lo devuelve."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    return STORAGE_DIR


def artifact_path(stem: str, extension: str) -> Path:
    """Devuelve la ruta de un archivo permitido dentro de reports/."""
    extension = extension.lower()
    if not extension.startswith("."):
        extension = "." + extension
    if extension not in ALLOWED_EXTENSIONS or Path(stem).name != stem:
        raise ValueError("Tipo o nombre de archivo no permitido.")
    return ensure_storage() / f"{stem}{extension}"


def list_artifacts():
    """Lista HTML, PDF e imágenes SVG guardados, del más reciente al más antiguo."""
    folder = ensure_storage()
    return sorted(
        (item for item in folder.iterdir() if item.is_file() and item.suffix.lower() in ALLOWED_EXTENSIONS),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
