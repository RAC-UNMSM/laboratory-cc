"""Configuración común de pytest: hace importable el proyecto desde cualquier carpeta."""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MPLBACKEND", "Agg")
