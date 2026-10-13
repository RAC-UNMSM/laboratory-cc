"""Carga la plantilla del informe y le inyecta los datos de la sesión.

Por qué el informe existe
-------------------------
Un resultado de herramienta MCP es **datos para el modelo**, no algo que la
interfaz dibuje: ningún cliente de chat renderiza el HTML que devuelve una
tool. Mandar la figura dentro de la respuesta no sirve para que el usuario la
vea, y encima gasta contexto. Lo que sí funciona es un enlace a una página.

Por qué la plantilla está en un `.html` y no aquí
-------------------------------------------------
`plantillas/informe.html` es HTML de verdad: se abre, se edita y se previsualiza
como cualquier página. No contiene ningún dato del problema, y este módulo no
contiene ninguna etiqueta. La división importa por tres razones:

* Cambiar el diseño no obliga a tocar Python, ni al revés.
* El render ocurre en el navegador a partir de un JSON, así que la página puede
  **agregar** la sección nueva sin reconstruirse entera: no se pierde el scroll
  ni el zoom que hiciste sobre una gráfica.
* Lo que el cliente MCP controla (títulos, nombres de variable) se inserta con
  `textContent`, nunca como marcado. Es una garantía más fuerte que escapar a
  mano cada f-string, porque no depende de acordarse en cada punto de inserción.

Este módulo solo serializa: recibe las entradas ya en forma de JSON (listas y
diccionarios) y devuelve el documento con el JSON embebido.
"""

import json
from datetime import datetime
from pathlib import Path

import plotly.io as pio

#: La plantilla. Un archivo, no un string: `PLANTILLA.read_text()` es todo lo
#: que este módulo sabe de HTML.
PLANTILLA = Path(__file__).resolve().parent / "plantillas" / "informe.html"

#: Marcador que la plantilla trae como contenido del `<script id="datos">`.
_MARCADOR = ('{"entradas": [], "sesion": null, "refresco": 0, "datos_url": null}')

#: Cada cuántos segundos la página busca novedades. Servida por http pide solo
#: el JSON y agrega lo nuevo; abierta como archivo local recarga, porque el
#: navegador prohíbe que un `file://` lea a su vecino.
SEGUNDOS_DE_REFRESCO = 15


def figura_a_json(figura):
    """Una figura de plotly como diccionario, lista para viajar en el JSON.

    Se manda la *especificación* de la figura, no el `<div>` ya renderizado que
    produce `pio.to_html`: así la página la dibuja cuando quiere, la plantilla
    decide la configuración, y la librería de plotly se carga una sola vez
    desde la propia plantilla en vez de venir incrustada en cada bloque.
    """
    spec = json.loads(pio.to_json(figura))
    # Fuera la plantilla por defecto de plotly. Son ~7 KB por figura de valores
    # que la página vuelve a decidir de todos modos, y su `colorway` y sus
    # fondos pelean con el CSS: dos fuentes para el mismo color es una de más.
    spec.get("layout", {}).pop("template", None)
    return spec


def _json_seguro(payload):
    """JSON listo para ir dentro de un `<script>` sin poder escaparse de él.

    `</script>` dentro de una cadena cerraría la etiqueta y el resto del JSON
    pasaría a interpretarse como HTML. Escapar `<` como `\\u003c` lo impide y
    sigue siendo JSON válido, así que `JSON.parse` lo lee igual.
    """
    texto = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    return texto.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace(
        "\u2029", "\\u2029")


def documento(entradas, titulo="Informe del análisis", refresco=SEGUNDOS_DE_REFRESCO,
              datos_url=None):
    """El informe completo: la plantilla con los datos de la sesión dentro.

    `refresco` en segundos; con 0 el documento queda fijo, que es lo que
    conviene para archivar o imprimir. `datos_url` es de dónde pedir las
    novedades cuando la página se sirve por http: si falta, o si se abrió como
    archivo, la plantilla recarga en su lugar.
    """
    payload = {
        "titulo": titulo,
        "entradas": list(entradas),
        "momento": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "refresco": int(refresco),
        "datos_url": datos_url,
    }
    plantilla = PLANTILLA.read_text(encoding="utf-8")
    if _MARCADOR not in plantilla:
        raise ValueError(
            f"La plantilla {PLANTILLA.name} ya no trae el marcador de datos; "
            "revise el <script id=\"datos\">.")
    return plantilla.replace(_MARCADOR, _json_seguro(payload), 1)
