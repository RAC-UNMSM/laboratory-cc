"""
storage.py — Persistencia de resultados en disco.

Cada cálculo recibe un id legible y ordenable ``<metodo>-AAAAMMDD-HHMMSS-<6 hex>`` y una carpeta:

    resultados/
    ├── indice.json                        ← lista resumida (lo que devuelve listar_resultados)
    └── hessiana-20261002-153012-a1b2c3/
        ├── entrada.json                   ← la solicitud validada (Pydantic)
        ├── resultado.json                 ← JSON exacto del método
        ├── reporte.html                   ← página interactiva (Jinja2)
        └── grafico.png                    ← lámina estática (opcional)

La carpeta base se toma de la variable de entorno ``MCP_MATH_RESULTADOS``
(por defecto ``resultados/`` junto a este archivo; en Docker, ``/data/resultados`` montado como volumen).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["Almacen", "RegistroResultado", "ID_PATRON", "nuevo_id"]

ID_PATRON = re.compile(r"^(lagrange|hessiana|frenet)-\d{8}-\d{6}-[0-9a-f]{6}$")
ARCHIVOS = {"entrada": "entrada.json", "resultado": "resultado.json", "html": "reporte.html", "png": "grafico.png"}
_MAX_INDICE = 500


def nuevo_id(metodo: str) -> str:
    return f"{metodo}-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"


@dataclass
class RegistroResultado:
    """Entrada del índice: lo justo para listar sin abrir cada carpeta."""
    id: str
    metodo: str
    fecha: str
    descripcion: str
    resumen: list[str] = field(default_factory=list)
    archivos: dict[str, str] = field(default_factory=dict)


class Almacen:
    """Guarda y recupera resultados. Seguro ante ids maliciosos (path traversal) y escrituras parciales."""

    def __init__(self, base: str | Path | None = None) -> None:
        # por defecto, junto a este archivo: no depende de la carpeta desde la que el cliente lance el servidor
        defecto = Path(__file__).resolve().parent / "resultados"
        self.base = Path(base or os.environ.get("MCP_MATH_RESULTADOS") or defecto).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self._candado = threading.Lock()

    # ── rutas ───────────────────────────────────────────────────────────────
    def carpeta(self, id_resultado: str) -> Path:
        if not ID_PATRON.match(id_resultado):
            raise KeyError(f"Id con formato inválido: '{id_resultado}'.")
        ruta = (self.base / id_resultado).resolve()
        if ruta.parent != self.base:                      # defensa adicional contra '..'
            raise KeyError("Id fuera del almacén.")
        return ruta

    def nueva_carpeta(self, metodo: str) -> tuple[str, Path]:
        for _ in range(5):
            id_ = nuevo_id(metodo)
            ruta = self.carpeta(id_)
            try:
                ruta.mkdir(parents=False, exist_ok=False)
                return id_, ruta
            except FileExistsError:
                continue
        raise RuntimeError("No se pudo crear una carpeta única para el resultado.")

    # ── escritura ───────────────────────────────────────────────────────────
    @staticmethod
    def _escribir_json(ruta: Path, datos: Any) -> None:
        """Escritura atómica: archivo temporal + os.replace (no deja JSON a medias)."""
        fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=2, default=str)
        os.chmod(tmp, 0o644)                      # mkstemp crea 0600; los demás archivos son legibles
        os.replace(tmp, ruta)

    def guardar(self, id_resultado: str, metodo: str, descripcion: str, entrada: dict, resultado: dict,
                resumen: list[str], archivos_extra: dict[str, str] | None = None) -> RegistroResultado:
        carpeta = self.carpeta(id_resultado)
        self._escribir_json(carpeta / ARCHIVOS["entrada"], entrada)
        self._escribir_json(carpeta / ARCHIVOS["resultado"], resultado)
        archivos = {"entrada": str(carpeta / ARCHIVOS["entrada"]), "resultado": str(carpeta / ARCHIVOS["resultado"])}
        archivos.update(archivos_extra or {})
        reg = RegistroResultado(id=id_resultado, metodo=metodo, fecha=datetime.now().isoformat(timespec="seconds"),
                                descripcion=descripcion[:200], resumen=resumen[:12], archivos=archivos)
        with self._candado:
            indice = self._leer_indice()
            indice.insert(0, asdict(reg))
            self._escribir_json(self.base / "indice.json", indice[:_MAX_INDICE])
        return reg

    # ── lectura ─────────────────────────────────────────────────────────────
    def _leer_indice(self) -> list[dict]:
        ruta = self.base / "indice.json"
        if not ruta.exists():
            return []
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            return datos if isinstance(datos, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def listar(self, metodo: str | None = None, limite: int = 20) -> list[dict]:
        regs = [r for r in self._leer_indice() if metodo is None or r.get("metodo") == metodo]
        return [{k: r.get(k) for k in ("id", "metodo", "fecha", "descripcion")} for r in regs[:limite]]

    def obtener(self, id_resultado: str) -> dict:
        carpeta = self.carpeta(id_resultado)
        if not carpeta.is_dir():
            raise KeyError(f"No existe el resultado '{id_resultado}'.")
        out: dict[str, Any] = {"id": id_resultado}
        for clave, nombre in (("entrada", ARCHIVOS["entrada"]), ("resultado", ARCHIVOS["resultado"])):
            ruta = carpeta / nombre
            out[clave] = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None
        out["archivos"] = {k: str(carpeta / v) for k, v in ARCHIVOS.items() if (carpeta / v).exists()}
        reg = next((r for r in self._leer_indice() if r.get("id") == id_resultado), None)
        if reg:
            out["resumen"] = reg.get("resumen", [])
            out["descripcion"] = reg.get("descripcion", "")
        return out
