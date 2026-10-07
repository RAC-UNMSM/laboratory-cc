"""
core/combinado.py — Reporte COMBINADO: varios ejercicios en una sola página HTML.

Cada ejercicio ya tiene su ``reporte.html`` individual en el almacén (SeaweedFS o carpeta
local; eso no cambia). Este módulo los descarga, en el orden pedido, y arma una página con
navegación «← Anterior / Siguiente ejercicio →», un índice y atajos de teclado. El resultado se
sube a su PROPIO prefijo, al lado de los individuales y sin tocarlos:

    grupo06/
    └── lote-20261006-190512-a1b2c3d4/
        ├── reporte_combinado.html     ← los N ejercicios, cada uno con sus 5 pestañas
        └── lote.json                  ← qué ejercicios contiene y en qué orden

Cada reporte individual se COPIA completo dentro del combinado (se muestra en un iframe con
``srcdoc``): conserva intactas sus pestañas, gráficos y estilos, y el combinado sigue
funcionando aunque luego se borren los reportes individuales.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from storage import ID_LOTE, ErrorAlmacen, nuevo_id_lote

__all__ = ["Combinador", "ID_LOTE", "ErrorCombinado"]

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


def _fecha_legible(d: datetime) -> str:
    return f"{d.day} {_MESES[d.month - 1]} {d.year}, {d:%H:%M}"


class Combinador:
    """Arma reportes combinados a partir de resultados guardados por ``storage.Almacen``."""

    def __init__(self, almacen: Any) -> None:
        self.almacen = almacen

    def _cargar(self, ids: list[str], enunciados: list[str] | None) -> list[dict]:
        ejercicios, faltan, sin_html = [], [], []
        for i, id_ in enumerate(ids):
            try:
                r = self.almacen.obtener(id_)
            except KeyError:
                faltan.append(id_)
                continue
            try:
                html = self.almacen.leer(id_, "reporte.html").decode("utf-8")
            except KeyError:
                sin_html.append(id_)
                continue
            metodo = id_.split("-", 1)[0]
            ejercicios.append({
                "n": i + 1, "id": id_, "metodo": metodo, "nombre_metodo": NOMBRES.get(metodo, metodo),
                "descripcion": r.get("descripcion", ""), "resumen": (r.get("resumen") or [])[:6],
                "enunciado": (enunciados[i] if enunciados else "") or "",
                "html_individual": self.almacen.url(id_, "reporte.html"),
                "html": html,
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
        try:
            ejercicios = self._cargar(ids, enunciados)
        except ErrorAlmacen as e:
            raise ErrorCombinado("ALMACEN_NO_DISPONIBLE", str(e), "Verifica que SeaweedFS esté en línea.") from e
        total = len(ejercicios)
        for ej in ejercicios:                         # pie de navegación dentro de cada reporte copiado
            html, pie = ej["html"], self._pie(ej, total)
            k = html.lower().rfind("</body>")
            ej["html"] = html[:k] + pie + html[k:] if k >= 0 else html + pie

        id_lote = nuevo_id_lote()
        ahora = datetime.now(timezone.utc)
        titulo = titulo or f"Reporte combinado · {total} ejercicio{'s' if total != 1 else ''}"
        pagina = _entorno.get_template("combinado.html.j2").render(
            titulo=titulo, total=total, fecha=_fecha_legible(ahora.astimezone()), id_lote=id_lote,
            ejercicios_json=_json_para_script(ejercicios))
        lista = [{k: ej[k] for k in ("n", "id", "metodo", "descripcion", "enunciado", "html_individual")}
                 for ej in ejercicios]
        try:
            url_html = self.almacen.subir(id_lote, "reporte_combinado.html", pagina)
            url_lote = self.almacen.subir_json(id_lote, "lote.json", {
                "id": id_lote, "fecha": ahora.isoformat(timespec="seconds"), "titulo": titulo, "ejercicios": lista})
        except ErrorAlmacen as e:
            raise ErrorCombinado("ALMACEN_NO_DISPONIBLE", str(e), "Verifica que SeaweedFS esté en línea.") from e
        return {"ok": True, "id_lote": id_lote, "titulo": titulo, "n_ejercicios": total,
                "ejercicios": [{k: e[k] for k in ("n", "id", "metodo", "descripcion")} for e in lista],
                "archivos": {"html": url_html, "lote": url_lote},
                "markdown": f"[Reporte combinado ({total} ejercicios)]({url_html})"}
