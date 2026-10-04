"""
core/combinado.py — Reporte COMBINADO: varios ejercicios en una sola página HTML.

Cada ejercicio ya tiene su carpeta y su ``reporte.html`` individual en ``resultados/``
(eso no cambia). Este módulo toma esos reportes, en el orden pedido, y arma una página
con navegación «← Anterior / Siguiente ejercicio →», un índice y atajos de teclado:

    resultados_combinados/
    └── lote-20261003-190512-a1b2c3/
        ├── reporte_combinado.html     ← los N ejercicios, cada uno con sus 5 pestañas
        └── lote.json                  ← qué ejercicios contiene y en qué orden

Cada reporte individual se COPIA completo dentro del combinado (se muestra en un iframe con
``srcdoc``): conserva intactas sus pestañas, gráficos y estilos, y el combinado sigue
funcionando aunque luego se borren las carpetas individuales.

La carpeta base es ``MCP_MATH_COMBINADOS`` o, por defecto, ``resultados_combinados/`` al lado
de la carpeta de resultados individuales.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

__all__ = ["Combinador", "ID_LOTE", "ErrorCombinado"]

ID_LOTE = re.compile(r"^lote-\d{8}-\d{6}-[0-9a-f]{6}$")
DIR_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
NOMBRES = {"lagrange": "Multiplicadores de Lagrange", "hessiana": "Puntos críticos y Hessiana",
           "frenet": "Triedro de Frenet"}
_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

_entorno = Environment(loader=FileSystemLoader(str(DIR_TEMPLATES)),
                       autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)


class ErrorCombinado(Exception):
    """Error explicable al usuario (ids inexistentes, reportes sin HTML...)."""

    def __init__(self, codigo: str, mensaje: str, sugerencia: str) -> None:
        super().__init__(mensaje)
        self.codigo, self.mensaje, self.sugerencia = codigo, mensaje, sugerencia


def _json_para_script(datos: Any) -> str:
    """JSON seguro dentro de <script>: ningún '<', '>' o '&' puede cerrar la etiqueta."""
    return (json.dumps(datos, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _escribir(ruta: Path, texto: str) -> None:
    """Escritura atómica (archivo temporal + os.replace)."""
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(texto)
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def _fecha_legible(d: datetime) -> str:
    return f"{d.day} {_MESES[d.month - 1]} {d.year}, {d:%H:%M}"


class Combinador:
    """Arma reportes combinados a partir de resultados guardados por ``storage.Almacen``."""

    def __init__(self, almacen: Any, base: str | Path | None = None) -> None:
        self.almacen = almacen
        defecto = Path(almacen.base).parent / "resultados_combinados"
        self.base = Path(base or os.environ.get("MCP_MATH_COMBINADOS") or defecto).resolve()

    def _nueva_carpeta(self) -> tuple[str, Path]:
        self.base.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            id_ = f"lote-{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
            ruta = self.base / id_
            try:
                ruta.mkdir(exist_ok=False)
                return id_, ruta
            except FileExistsError:
                continue
        raise RuntimeError("No se pudo crear una carpeta única para el reporte combinado.")

    def _cargar(self, ids: list[str], enunciados: list[str] | None) -> list[dict]:
        ejercicios, faltan, sin_html = [], [], []
        for i, id_ in enumerate(ids):
            try:
                r = self.almacen.obtener(id_)
            except KeyError:
                faltan.append(id_)
                continue
            ruta_html = r.get("archivos", {}).get("html")
            if not ruta_html or not Path(ruta_html).is_file():
                sin_html.append(id_)
                continue
            metodo = id_.split("-", 1)[0]
            ejercicios.append({
                "n": i + 1, "id": id_, "metodo": metodo, "nombre_metodo": NOMBRES.get(metodo, metodo),
                "descripcion": r.get("descripcion", ""), "resumen": (r.get("resumen") or [])[:6],
                "enunciado": (enunciados[i] if enunciados else "") or "",
                "html_individual": str(Path(ruta_html).resolve()),
                "html": Path(ruta_html).read_text(encoding="utf-8"),
            })
        if faltan:
            raise ErrorCombinado("NO_ENCONTRADO", f"No existen estos resultados: {', '.join(faltan)}.",
                                 "Usa listar_resultados para ver los ids disponibles; si se borraron, vuelve a "
                                 "resolver esos ejercicios.")
        if sin_html:
            raise ErrorCombinado("SIN_HTML", f"Estos resultados no tienen reporte HTML: {', '.join(sin_html)}.",
                                 "Vuelve a resolverlos con salida.generar_html = true.")
        return ejercicios

    def _pie(self, ej: dict, total: int) -> str:
        """Botones «anterior / siguiente» que se añaden al final de cada reporte copiado."""
        return _entorno.get_template("combinado_pie.html.j2").render(
            n=ej["n"], total=total, siguiente=ej["n"] < total)

    def combinar(self, ids: list[str], titulo: str | None = None,
                 enunciados: list[str] | None = None) -> dict[str, Any]:
        ejercicios = self._cargar(ids, enunciados)
        total = len(ejercicios)
        for ej in ejercicios:                         # pie de navegación dentro de cada reporte copiado
            html, pie = ej["html"], self._pie(ej, total)
            k = html.lower().rfind("</body>")
            ej["html"] = html[:k] + pie + html[k:] if k >= 0 else html + pie

        id_lote, carpeta = self._nueva_carpeta()
        ahora = datetime.now()
        titulo = titulo or f"Reporte combinado · {total} ejercicio{'s' if total != 1 else ''}"
        pagina = _entorno.get_template("combinado.html.j2").render(
            titulo=titulo, total=total, fecha=_fecha_legible(ahora), id_lote=id_lote,
            ejercicios_json=_json_para_script(ejercicios))
        ruta_html = carpeta / "reporte_combinado.html"
        _escribir(ruta_html, pagina)

        lista = [{k: ej[k] for k in ("n", "id", "metodo", "descripcion", "enunciado", "html_individual")}
                 for ej in ejercicios]
        ruta_lote = carpeta / "lote.json"
        _escribir(ruta_lote, json.dumps({"id": id_lote, "fecha": ahora.isoformat(timespec="seconds"),
                                         "titulo": titulo, "ejercicios": lista}, ensure_ascii=False, indent=2))
        return {"ok": True, "id_lote": id_lote, "titulo": titulo, "n_ejercicios": total,
                "ejercicios": [{k: e[k] for k in ("n", "id", "metodo", "descripcion")} for e in lista],
                "archivos": {"html": str(ruta_html), "lote": str(ruta_lote)}, "carpeta": str(carpeta)}
