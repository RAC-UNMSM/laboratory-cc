"""Un servidor HTTP mínimo para que el informe local sea un enlace de verdad.

El problema
-----------
Sin el storage del laboratorio, el informe queda en un archivo y lo único que se
le puede dar al usuario es una ruta: `C:\\...\\informes\\informe-....html`. Eso
tiene dos defectos que no son cosméticos:

1. **No se puede abrir con un clic.** El cliente de chat corre en el navegador,
   y un navegador no navega a `file://` desde una página https. Hay que copiar
   la ruta y pegarla a mano.
2. **La página no puede actualizarse sola.** Un documento abierto como `file://`
   tiene prohibido leer un archivo vecino con `fetch`, así que la plantilla cae
   al plan B: recargarse entera cada pocos segundos. Funciona, pero parpadea y
   vuelve a dibujar las gráficas.

Los dos defectos vienen de lo mismo: `file://`. Servir la carpeta por HTTP en
`127.0.0.1` los resuelve de golpe -- el enlace se abre con un clic y la página
puede pedir su JSON y **agregar** la sección nueva sin recargar, igual que en el
despliegue del laboratorio.

Qué expone y qué no
-------------------
Escucha **solo en 127.0.0.1**, en un puerto que elige el sistema operativo, y
sirve únicamente la carpeta de informes. No acepta conexiones de la red, no
escribe nada y no ejecuta nada. El hilo es demonio: no retrasa el cierre del
proceso cuando la conversación termina.

Se puede apagar con `EDOS_SIN_SERVIDOR_LOCAL=1`, y entonces se vuelve a entregar
la ruta del archivo como antes.
"""

import logging
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

registro = logging.getLogger("edos-grupo09")

#: Dirección de escucha. No es configurable a propósito: abrir esto a la red
#: convertiría una comodidad local en una carpeta compartida sin autenticación.
INTERFAZ = "127.0.0.1"

_candado = threading.Lock()
_base = None          # la URL base, una vez levantado
_intentado = False    # para no reintentar en cada análisis si ya falló


class _Manejador(SimpleHTTPRequestHandler):
    """Sirve la carpeta de informes y no imprime nada por stdout.

    `SimpleHTTPRequestHandler` escribe sus trazas con `sys.stderr.write`, pero
    aquí se redirigen al logger de todos modos: en stdio, cualquier cosa que
    acabe en stdout rompe el protocolo, y no conviene depender de que una clase
    de la biblioteca estándar siga eligiendo bien el canal.
    """

    def log_message(self, formato, *args):
        registro.debug("informe http: " + formato, *args)

    def end_headers(self):
        # El informe se reescribe entero en cada análisis. Sin esto el navegador
        # sirve la copia que ya tiene y el usuario ve el informe de hace tres
        # preguntas sin saber por qué.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def url_base(carpeta):
    """URL donde se sirve `carpeta`, levantando el servidor la primera vez.

    Devuelve None si está desactivado o si no se pudo abrir el puerto. En ese
    caso quien llama entrega la ruta del archivo, que es lo que se hacía antes:
    esto es una mejora del enlace, no un requisito para que el informe exista.
    """
    global _base, _intentado

    if os.environ.get("EDOS_SIN_SERVIDOR_LOCAL"):
        return None

    with _candado:
        if _base is not None or _intentado:
            return _base
        _intentado = True
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
            # Puerto 0: lo elige el sistema. Fijar uno invitaría a chocar con
            # otro grupo que tuviera su agente levantado en la misma máquina.
            servidor = ThreadingHTTPServer(
                (INTERFAZ, 0), partial(_Manejador, directory=str(carpeta)))
        except OSError as exc:
            registro.warning("No se pudo levantar el servidor del informe: %s", exc)
            return None

        hilo = threading.Thread(target=servidor.serve_forever,
                                name="informe-http", daemon=True)
        hilo.start()
        _base = f"http://{INTERFAZ}:{servidor.server_address[1]}"
        registro.info("Informe servido en %s", _base)
        return _base


def reiniciar():
    """Olvida el servidor levantado. Solo para las pruebas."""
    global _base, _intentado
    with _candado:
        _base, _intentado = None, False
