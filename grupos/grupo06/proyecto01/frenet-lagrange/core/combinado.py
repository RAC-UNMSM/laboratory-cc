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

REPORTE DE SESIÓN AUTOMÁTICO
----------------------------
Además de los lotes pedidos explícitamente (``Combinador.combinar`` → id nuevo ``lote-…``), hay un
lote de SESIÓN con prefijo FIJO que se actualiza solo después de cada cálculo:

    grupo06/lote-sesion-actual/
        ├── reporte_combinado.html     ← todos los ejercicios de la sesión, en orden
        └── lote.json                  ← lista {id, enunciado} de esos ejercicios

``agregar_a_sesion(id_nuevo_ejercicio, enunciado)`` (la llama core/motor.publicar justo después de
subir los archivos individuales) descarga ese lote.json (o empieza con una lista vacía), añade el
ejercicio y vuelve a llamar a ``Combinador.combinar`` con la lista completa, SOBRESCRIBIENDO
reporte_combinado.html y lote.json en el mismo prefijo (no se crea un id de lote nuevo).

Concurrencia: dentro de un proceso, un candado serializa las actualizaciones de la sesión (dos
cálculos simultáneos no se pisan). Si se despliegan varias réplicas del contenedor, la última
escritura gana; para una sesión exacta entre réplicas habría que usar escrituras condicionales.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from storage import ID_LOTE, ID_SESION, ErrorAlmacen, nuevo_id_lote

__all__ = ["Combinador", "ID_LOTE", "ID_SESION", "ErrorCombinado", "configurar_sesion", "agregar_a_sesion"]

log = logging.getLogger("mcp_math.combinado")

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
                 enunciados: list[str] | None = None, id_lote: str | None = None) -> dict[str, Any]:
        """Une los reportes de ``ids`` en una página. ``id_lote``: prefijo donde publicarla; si es None
        se genera un id NUEVO (lote pedido explícitamente); con ``ID_SESION`` se sobrescribe el lote fijo
        de la sesión."""
        try:
            ejercicios = self._cargar(ids, enunciados)
        except ErrorAlmacen as e:
            raise ErrorCombinado("ALMACEN_NO_DISPONIBLE", str(e), "Verifica que SeaweedFS esté en línea.") from e
        total = len(ejercicios)
        for ej in ejercicios:                         # pie de navegación dentro de cada reporte copiado
            html, pie = ej["html"], self._pie(ej, total)
            k = html.lower().rfind("</body>")
            ej["html"] = html[:k] + pie + html[k:] if k >= 0 else html + pie

        id_lote = id_lote or nuevo_id_lote()
        ahora = datetime.now(timezone.utc)
        titulo = titulo or f"Reporte combinado · {total} ejercicio{'s' if total != 1 else ''}"
        pagina = _entorno.get_template("combinado.html.j2").render(
            titulo=titulo, total=total, fecha=_fecha_legible(ahora.astimezone()), id_lote=id_lote,
            ejercicios_json=_json_para_script(ejercicios))
        lista = [{k: ej[k] for k in ("n", "id", "metodo", "descripcion", "enunciado", "html_individual")}
                 for ej in ejercicios]
        try:
            url_html = self.almacen.subir(id_lote, "reporte_combinado.html", pagina.encode("utf-8"))
            url_lote = self.almacen.subir_json(id_lote, "lote.json", {
                "id": id_lote, "fecha": ahora.isoformat(timespec="seconds"), "titulo": titulo, "ejercicios": lista})
        except ErrorAlmacen as e:
            raise ErrorCombinado("ALMACEN_NO_DISPONIBLE", str(e), "Verifica que SeaweedFS esté en línea.") from e
        return {"ok": True, "id_lote": id_lote, "titulo": titulo, "n_ejercicios": total,
                "ejercicios": [{k: e[k] for k in ("n", "id", "metodo", "descripcion")} for e in lista],
                "archivos": {"html": url_html, "lote": url_lote},
                "markdown": f"[Reporte combinado ({total} ejercicios)]({url_html})"}


# ════════════════════════════════════════════════════════════════════════════
# Reporte combinado AUTOMÁTICO de la sesión (prefijo fijo grupo06/lote-sesion-actual/)
# ════════════════════════════════════════════════════════════════════════════
_combinador_sesion: Combinador | None = None
_candado_sesion = threading.Lock()
TITULO_SESION = "Sesión actual · ejercicios resueltos"
#: Opcional: conservar solo los N ejercicios más recientes (0 = todos, como pide el enunciado).
SESION_MAX = int(os.environ.get("MCP_SESION_MAX", "0") or 0)


def configurar_sesion(almacen: Any) -> None:
    """Indica qué almacén usa la sesión (lo hace server.py una vez, al arrancar)."""
    global _combinador_sesion
    _combinador_sesion = Combinador(almacen)


def agregar_a_sesion(id_nuevo_ejercicio: str, enunciado: str) -> dict[str, Any]:
    """Añade un ejercicio recién publicado al reporte combinado de la sesión y lo regenera.

    1. Descarga ``grupo06/lote-sesion-actual/lote.json`` (si no existe, empieza con lista vacía).
    2. Añade ``id_nuevo_ejercicio`` (con su ``enunciado``) al final de la lista.
    3. Llama a ``Combinador.combinar`` con la lista actualizada y ``id_lote=ID_SESION``, que
       SOBRESCRIBE reporte_combinado.html y lote.json en ese mismo prefijo fijo.

    Devuelve lo mismo que ``combinar`` (URL pública del HTML combinado, lista de ejercicios...)."""
    if _combinador_sesion is None:
        raise RuntimeError("Sesión sin configurar: llama antes a configurar_sesion(almacen).")
    comb = _combinador_sesion
    with _candado_sesion:                        # una actualización de la sesión a la vez
        try:
            lote = comb.almacen.leer_json(ID_SESION, "lote.json")
            ejercicios = [{"id": e["id"], "enunciado": e.get("enunciado") or ""}
                          for e in lote.get("ejercicios", []) if e.get("id")]
        except KeyError:                          # primer ejercicio de la sesión
            ejercicios = []
        except (ValueError, TypeError) as e:     # lote.json ilegible: se reinicia la sesión
            log.warning("lote.json de la sesión ilegible (%s); se empieza una lista nueva.", e)
            ejercicios = []
        ejercicios = [e for e in ejercicios if e["id"] != id_nuevo_ejercicio]
        ejercicios.append({"id": id_nuevo_ejercicio, "enunciado": enunciado or ""})
        if SESION_MAX > 0:
            ejercicios = ejercicios[-SESION_MAX:]
        try:
            return comb.combinar([e["id"] for e in ejercicios], TITULO_SESION,
                                 [e["enunciado"] for e in ejercicios], id_lote=ID_SESION)
        except ErrorCombinado as e:
            if e.codigo != "NO_ENCONTRADO":
                raise
            # Algún ejercicio viejo de la sesión ya no existe: se descartan los que falten y se reintenta.
            vivos = [x for x in ejercicios if x["id"] not in e.mensaje]
            return comb.combinar([x["id"] for x in vivos], TITULO_SESION, [x["enunciado"] for x in vivos],
                                 id_lote=ID_SESION)
