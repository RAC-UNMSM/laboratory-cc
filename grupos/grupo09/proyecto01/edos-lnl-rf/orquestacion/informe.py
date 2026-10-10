"""Informe de cada análisis: una página HTML publicada en el storage del laboratorio.

Qué resuelve
------------
El HTML que devuelve una herramienta MCP no lo dibuja ningún cliente de chat:
es texto que el modelo lee. Para que el usuario **vea** su problema hay que
darle un enlace que abra en el navegador. Este módulo compone esa página (las
gráficas, el desarrollo con sus fórmulas y la verificación) y la sube a
SeaweedFS con `storage.subir_html`, que devuelve la URL pública.

Un análisis, una página
-----------------------
El servidor está desplegado: todos los usuarios comparten el mismo proceso y
las herramientas corren en paralelo. Un informe "de la sesión" mezclaría los
análisis de personas distintas, así que cada análisis publica su propia página
con un nombre aleatorio (`uuid`), igual que el piloto del laboratorio hace con
cada imagen. Nada se guarda en disco: el contenedor no conserva archivos.

Sin storage (ejecución local, fuera de la red del laboratorio) no hay enlace:
`publicar` devuelve None y la herramienta responde igual, sin él.
"""

import logging
from datetime import datetime

import storage
from visualizacion.plantilla import documento

registro = logging.getLogger("edos-grupo09")

#: Título de la página.
TITULO = "Informe del análisis"


def publicar(entrada):
    """Compone la página de un análisis y la sube. Devuelve su URL, o None.

    Nunca levanta: si el informe no se puede publicar, el análisis que lo
    originó sigue siendo válido y debe devolverse igual.
    """
    entrada = dict(entrada)
    entrada.setdefault("momento", datetime.now().strftime("%H:%M:%S"))
    try:
        html = documento([entrada], titulo=TITULO, refresco=0)
    except Exception as exc:                 # una entrada rara no tumba la respuesta
        registro.warning("No se pudo componer el informe: %s", exc)
        return None
    return storage.subir_html(html)
