"""Informe de la sesión: acumula los análisis y los publica en una dirección fija.

Qué resuelve
------------
El HTML que devuelve una herramienta MCP no lo dibuja ningún cliente de chat:
es texto que el modelo lee. Para que el usuario **vea** su problema hay que
darle un enlace que abra en el navegador. Y como una conversación suele tener
varios problemas, el enlace no debería cambiar en cada llamada: conviene uno
solo, que se vaya llenando.

Eso es lo que hace este módulo. Guarda las entradas de la conversación en
orden y, cada vez que llega una nueva, vuelve a escribir el documento entero
sobre la **misma** dirección. El usuario abre el enlace una vez, deja la
pestaña abierta, y la plantilla se encarga de refrescarla sola.

Dónde queda el documento
------------------------
Dos destinos, según dónde corra el servidor:

* **Con storage** (contenedor en la red del laboratorio): se sube a SeaweedFS
  con una clave estable derivada del id de sesión, así que cada reescritura
  pisa a la anterior y la URL pública no cambia. Se suben dos archivos: la
  página y, al lado, el JSON de la sesión. La página pide ese JSON cada pocos
  segundos y **agrega** la sección nueva sin recargarse, de modo que no se
  pierde el scroll ni el zoom que el usuario haya hecho sobre una gráfica.
* **Sin storage** (lo normal hoy: proceso local por stdio): se escribe en
  `informes/` junto al proyecto. Una ruta local sí le sirve al usuario en este
  caso, porque el servidor corre en su propia máquina -- es exactamente la
  situación en la que el transporte stdio tiene sentido. Aquí la página no
  puede pedir el JSON: el navegador prohíbe que un `file://` lea un archivo
  vecino. La plantilla lo detecta y recarga, conservando la posición del
  scroll.

Una sesión NO es un proceso
---------------------------
Esto se creyó al principio y es falso: un cliente MCP por stdio levanta el
servidor **una vez** y lo mantiene vivo para todas las conversaciones. Sin
corregirlo, el informe acumulaba las preguntas de chats distintos en un mismo
documento y no empezaba de cero nunca.

El protocolo no le dice al servidor en qué conversación está, así que hay que
decidirlo aquí. Dos mecanismos, en este orden:

1. **`empezar_de_nuevo()`**, que el agente invoca con la herramienta
   `nuevo_informe` al arrancar una conversación. Es el camino bueno: explícito
   y exacto.
2. **Relevo por inactividad**, como red de seguridad para cuando el agente no
   lo haga. Si entre dos análisis pasan más de `MINUTOS_DE_INACTIVIDAD`, el
   siguiente abre un informe nuevo por su cuenta.

Ninguno pierde nada: el informe anterior queda en su archivo, con su fecha y su
hora en el nombre.
"""

import logging
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

import storage
from orquestacion import servidor_local
from visualizacion.plantilla import datos_sueltos, documento

registro = logging.getLogger("edos-grupo09")

#: Carpeta de informes cuando no hay storage. Al lado del proyecto, no en el
#: directorio de trabajo: el cliente MCP arranca el proceso desde donde le
#: conviene, y el usuario no tiene por qué adivinar dónde quedó su archivo.
#: ...y se puede mover con EDOS_INFORMES, que es lo que necesita un contenedor:
#: dentro de la imagen el código va en un sitio de solo lectura y los informes
#: tienen que caer en un volumen para que sobrevivan al contenedor.
CARPETA_LOCAL = Path(os.environ.get(
    "EDOS_INFORMES", Path(__file__).resolve().parents[1] / "informes"))

#: Qué muestra el informe. Dos modos, y el de por defecto es "ultimo".
#:
#: "ultimo"   cada pregunta reemplaza a la anterior. El documento enseña UNA
#:            cosa: la que se acaba de preguntar. Es lo que se quiere la mayor
#:            parte del tiempo, y de paso hace irrelevante saber en qué chat
#:            estamos -- no hay historial que pueda mezclarse entre
#:            conversaciones.
#: "acumula"  cada pregunta agrega una sección, lo último arriba. Sirve cuando
#:            las respuestas se comparan entre sí: mientras el barrido
#:            paramétrico siga pendiente, estudiar una bifurcación es llamar
#:            varias veces variando el parámetro, y la bifurcación se ve
#:            precisamente al poner esas llamadas una al lado de otra.
MODO = os.environ.get("EDOS_INFORME_MODO", "ultimo").strip().lower()
ACUMULA = MODO == "acumula"

#: Cuánto silencio basta para dar por terminada una conversación. Generoso a
#: propósito: cortar un informe por la mitad porque alguien se fue a almorzar
#: es peor que arrastrar una pregunta de más. El camino fino es que el agente
#: llame a `nuevo_informe`; esto solo recoge lo que se le escape.
MINUTOS_DE_INACTIVIDAD = float(os.environ.get("EDOS_INACTIVIDAD_MIN", "120"))

#: Tope de análisis guardados. Una conversación larga no puede crecer sin
#: límite: el documento se vuelve a escribir entero en cada llamada, así que
#: su costo es proporcional a lo acumulado.
MAXIMO_ENTRADAS = 40


class InformeDeSesion:
    """Las entradas de una conversación y el documento que las muestra.

    Es seguro llamarlo desde varios hilos: el servidor MCP puede atender más de
    una herramienta a la vez, y dos análisis que terminan juntos escribirían el
    mismo archivo.
    """

    def __init__(self, identificador=None):
        # El nombre se lee: fecha, hora y cuatro dígitos para desempatar dos
        # conversaciones del mismo minuto. "informe-a3f91b2c4d5e" no decía
        # nada, y una carpeta con varios era imposible de ordenar a ojo.
        self.id = identificador or self._nuevo_id()
        self.entradas = []
        self._candado = threading.Lock()
        self._destino = None          # URL o ruta, una vez publicado
        self._ultimo_uso = datetime.now()

    # -- escritura ----------------------------------------------------------

    def registrar(self, entrada):
        """Agrega un análisis y reescribe el informe. Devuelve dónde quedó.

        Nunca levanta: si el informe no se puede publicar, el análisis que lo
        originó sigue siendo válido y debe devolverse igual. Un fallo aquí se
        reporta como `None` y el flujo principal lo trata como "no hay enlace".
        """
        with self._candado:
            ahora = datetime.now()
            # El relevo por inactividad solo tiene sentido si hay historial que
            # pueda arrastrarse de otra conversación. En modo "ultimo" no lo hay.
            if (ACUMULA and self.entradas
                    and (ahora - self._ultimo_uso).total_seconds()
                    > MINUTOS_DE_INACTIVIDAD * 60):
                registro.info("Informe relevado por inactividad (%s)", self.id)
                self._relevar()
            self._ultimo_uso = ahora
            entrada = dict(entrada)
            entrada.setdefault("momento", ahora.strftime("%H:%M:%S"))
            if ACUMULA:
                self.entradas.append(entrada)
                if len(self.entradas) > MAXIMO_ENTRADAS:
                    del self.entradas[0]
            else:
                self.entradas = [entrada]
            return self._publicar()

    def empezar_de_nuevo(self):
        """Cierra el informe actual y abre uno vacío. Devuelve su dirección.

        Es lo que hace la herramienta `nuevo_informe` al empezar una
        conversación. El informe anterior no se toca: queda en su archivo, y su
        nombre lleva la fecha y la hora en que se abrió.
        """
        with self._candado:
            anterior = self.id
            self._relevar()
            self._ultimo_uso = datetime.now()
            registro.info("Informe nuevo (%s); el anterior era %s", self.id, anterior)
            return self._publicar()

    def _relevar(self):
        """Identidad nueva y sin entradas. Llamar con el candado tomado."""
        self.id = self._nuevo_id()
        self.entradas = []
        self._destino = None

    @staticmethod
    def _nuevo_id():
        return "{}-{}".format(datetime.now().strftime("%Y%m%d-%H%M"),
                              uuid.uuid4().hex[:4])

    def _publicar(self):
        """Escribe el documento completo. Llamar con el candado tomado."""
        try:
            html = documento(self.entradas, datos_url=self._datos_url())
        except Exception as exc:                 # una entrada rara no borra el resto
            registro.warning("No se pudo componer el informe: %s", exc)
            return self._destino

        enlace = storage.subir_html(html, clave=self._nombre("html"))
        if enlace:
            # El JSON va al lado de la página, con el mismo nombre. Si falla, la
            # página sigue mostrando lo que ya trae embebido: pierde la
            # actualización en vivo, no el contenido.
            storage.subir_html(datos_sueltos(self.entradas, datos_url=self._datos_url()),
                               clave=self._nombre("json"),
                               tipo="application/json; charset=utf-8")
            self._destino = enlace
            return enlace

        try:
            CARPETA_LOCAL.mkdir(parents=True, exist_ok=True)
            ruta = CARPETA_LOCAL / self._nombre("html")
            ruta.write_text(html, encoding="utf-8")
            (CARPETA_LOCAL / self._nombre("json")).write_text(
                datos_sueltos(self.entradas, datos_url=self._datos_url()),
                encoding="utf-8")
        except OSError as exc:
            registro.warning("No se pudo escribir el informe local: %s", exc)
            return self._destino

        # Un enlace http se abre con un clic; una ruta de archivo hay que
        # copiarla y pegarla, porque el navegador no navega a file:// desde
        # una página https. Si el servidor no se pudo levantar se entrega la
        # ruta, que es lo que se hacía antes.
        base = servidor_local.url_base(CARPETA_LOCAL)
        self._destino = (f"{base}/{self._nombre('html')}" if base else str(ruta))
        return self._destino

    def _nombre(self, extension):
        return f"informe-{self.id}.{extension}"

    def _datos_url(self):
        """Dónde pedirá la página las novedades, si es que puede pedirlas.

        Servido por http -- el laboratorio, o el servidor local de aquí al
        lado -- el JSON está junto a la página, así que basta el nombre
        relativo y sirve para los dos casos sin saber cuál es.
        """
        return self._nombre("json")

    # -- lectura ------------------------------------------------------------

    @property
    def destino(self):
        """Dónde está el informe ahora, o None si todavía no se publicó."""
        return self._destino

    def estado(self):
        """Resumen para la herramienta `informe` del servidor."""
        with self._candado:
            return {
                "sesion": self.id,
                "analisis_registrados": len(self.entradas),
                "destino": self._destino,
                "es_url": bool(self._destino and self._destino.startswith("http")),
                "modo": MODO,
                "titulos": [e.get("titulo") for e in self.entradas],
                "ultimo_uso": self._ultimo_uso.strftime("%d/%m/%Y %H:%M"),
            }

    def asegurar_publicado(self):
        """Publica aunque no haya entradas, para poder entregar el enlace ya.

        Sirve para que el usuario abra la pestaña **antes** de pedir el primer
        análisis y la vea llenarse: el documento vacío explica qué va a pasar.
        """
        with self._candado:
            return self._publicar()


#: El informe de esta sesión. Un proceso, una conversación, un documento.
SESION = InformeDeSesion()
