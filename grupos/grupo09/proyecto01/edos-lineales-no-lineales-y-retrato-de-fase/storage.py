"""Storage de visualizaciones (SeaweedFS): rol "Storage/infra" del grupo 09.

Mismo patrón que el molde del laboratorio (`grupos/g01/semana01/derivadas1/
storage.py`): subir el resultado a un storage compartido → devolver una URL
pública → nunca romper el flujo principal si el storage falla. Lo que cambia es
el *tipo de dato*: la propuesta de este grupo pide visualizaciones HTML
interactivas con plotly, no PNG, así que acá se sube HTML.

Por qué hace falta: el HTML viaja inline por el transporte y por eso
`capacidades._visualizar` tiene un tope (`LIMITE_HTML_INLINE`) y submuestrea o
se rinde cuando una trayectoria pesa demasiado. Publicado en una URL no hay
tope: el cliente recibe un enlace corto a la figura de máxima resolución en vez
de 400 KB de JSON de plotly dentro de la respuesta.

"seaweedfs" resuelve por DNS interno de Docker cuando el contenedor comparte la
red "lab_net". Con el transporte stdio actual (proceso local, sin Docker) ese
nombre no resuelve, `subir_html` devuelve None y todo sigue funcionando igual
que antes, con el HTML inline. No hay nada que apagar para trabajar en local.
"""

import functools
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
import uuid

# Los tres se pueden sobreescribir por entorno. Hace falta porque el mismo
# código corre en dos sitios con direcciones distintas: como proceso local por
# stdio (donde "seaweedfs" no resuelve y no pasa nada) y dentro de un contenedor
# en la red del laboratorio. Cocinar la dirección obligaba a editar el fuente
# para desplegar, que es justo lo que no debe hacer falta.
SEAWEEDFS_S3_URL = os.environ.get("EDOS_STORAGE_URL", "http://seaweedfs:8333")
HTML_BUCKET = os.environ.get("EDOS_STORAGE_BUCKET", "grupo09-edos-html")

# Ruta pública en Caddy: solo lectura, sin login -- quien abre el enlace es el
# navegador del usuario (o el cliente de chat), de forma anónima y sin la
# cookie de sesión del lab. OJO: esta ruta la asigna el profesor en el
# Caddyfile; hay que confirmarla antes de desplegar, y por eso es una variable
# de entorno: corregirla no debería ser un commit.
PUBLIC_HTML_BASE_URL = os.environ.get(
    "EDOS_URL_PUBLICA", "https://rac-unmsm.vekthos.org/html/grupo09-edos")


@functools.lru_cache(maxsize=1)
def _hay_storage() -> bool:
    """¿Existe el host del storage? El resultado se cachea.

    Sin esto, cada llamada paga ~2 s de resolución DNS fallida en local, donde
    "seaweedfs" no es un nombre que exista: es un costo fijo por análisis a
    cambio de nada. Se cachea solo la *resolución del nombre*, no la conexión:
    si el host existe pero el servicio aún no levantó (orden de arranque de
    contenedores), `subir_html` sigue reintentando en cada llamada, igual que
    el molde del lab.
    """
    host = urllib.parse.urlsplit(SEAWEEDFS_S3_URL).hostname
    try:
        socket.getaddrinfo(host, None)
    except OSError:
        return False
    return True


def ensure_bucket() -> None:
    """Crea el bucket si no existe. Falla en silencio: si SeaweedFS todavía no
    está listo (orden de arranque de contenedores), si el bucket ya existe o si
    simplemente no hay storage (ejecución local por stdio), no es motivo para
    tumbar el servidor -- `subir_html` reintenta la conexión en cada llamada."""
    if not _hay_storage():
        return
    try:
        req = urllib.request.Request(f"{SEAWEEDFS_S3_URL}/{HTML_BUCKET}/", method="PUT")
        urllib.request.urlopen(req, timeout=5)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        pass


def subir_html(html: str, clave: str | None = None,
               tipo: str = "text/html; charset=utf-8") -> str | None:
    """Sube el documento HTML y devuelve la URL pública, o None si no respondió.

    Sin `clave` se genera una al azar (no adivinable, no secuencial): es lo que
    corresponde a una figura suelta, que no tiene por qué pisar a ninguna otra.

    Con `clave` se escribe siempre en la misma dirección, de modo que volver a
    subir **actualiza** el documento en vez de crear otro. Así el informe de la
    sesión conserva su URL mientras la conversación avanza y el usuario puede
    dejar la pestaña abierta.

    `tipo` es el Content-Type con que se sirve: el informe sube su página como
    HTML y, al lado, su JSON de datos, que debe llegar al navegador como JSON
    para que `fetch(...).json()` lo acepte.

    Devolver None no es un error que haya que propagar: es el caso normal en
    local. Quien llama lo trata como "no hay enlace" y busca otra salida.
    """
    if not _hay_storage():
        return None
    key = clave or f"{uuid.uuid4().hex}.html"
    try:
        req = urllib.request.Request(
            f"{SEAWEEDFS_S3_URL}/{HTML_BUCKET}/{key}",
            data=html.encode("utf-8"),
            method="PUT",
            headers={"Content-Type": tipo},
        )
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None
    return f"{PUBLIC_HTML_BASE_URL}/{key}"
