# Agente de EDOs del grupo 09, empaquetado para transporte stdio.
#
#   docker build -t edos-grupo09 .
#   docker run -i --rm -v "$PWD/informes:/datos/informes" edos-grupo09
#
# El `-i` no es opcional: en stdio el protocolo JSON-RPC viaja por stdin y
# stdout, así que cerrar stdin deja al servidor sin canal. Y **nunca `-t`**: un
# TTY traduce saltos de línea y reescribe bytes, lo que corrompe el JSON-RPC sin
# dar ningún error claro -- el cliente simplemente ve un servidor que no
# responde. Es la contraparte de lo que `mcp_server.sin_contaminar_stdout` hace
# dentro del proceso: las dos defensas protegen el mismo canal, una del lado del
# contenedor y otra del lado del código.

# --- Etapa 1: las dependencias, en un entorno virtual aparte -----------------
# Separarlas de la imagen final significa que un cambio en el código no vuelve a
# compilar numpy, scipy ni sympy, que es casi todo el tiempo de build.
FROM python:3.12-slim AS dependencias

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/entorno
ENV PATH="/opt/entorno/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


# --- Etapa 2: la imagen que se publica --------------------------------------
FROM python:3.12-slim

LABEL org.opencontainers.image.title="edos-grupo09" \
      org.opencontainers.image.description="Agente MCP de EDOs y sistemas dinámicos: integración verificada, estabilidad e informe HTML" \
      org.opencontainers.image.source="https://github.com/RAC-UNMSM/laboratory-cc"

ENV PATH="/opt/entorno/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    EDOS_INFORMES=/datos/informes

# PYTHONUNBUFFERED importa aquí más que de costumbre: con el buffer puesto, una
# respuesta se queda esperando en el búfer de stdout y el cliente MCP interpreta
# el silencio como que el servidor se colgó.

COPY --from=dependencias /opt/entorno /opt/entorno

# Usuario sin privilegios. El servidor ejecuta expresiones matemáticas que llegan
# de un cliente arbitrario: `matematica/expresiones.py` las valida en tres capas
# y no usa `eval`, pero esa es la primera barrera, no la única que conviene tener.
RUN useradd --create-home --uid 1000 edos \
    && mkdir -p /datos/informes \
    && chown -R edos:edos /datos

WORKDIR /app

# Solo lo que el agente necesita en ejecución. Las pruebas no entran: hacen falta
# para desarrollar, no para servir, y arrastrarlas engorda la imagen y amplía lo
# que hay dentro sin motivo.
COPY --chown=edos:edos matematica/      matematica/
COPY --chown=edos:edos orquestacion/    orquestacion/
COPY --chown=edos:edos visualizacion/   visualizacion/
COPY --chown=edos:edos balotario/       balotario/
COPY --chown=edos:edos mcp_server.py storage.py ./

USER edos
VOLUME ["/datos/informes"]

# Que el build falle aquí y no en la primera pregunta del usuario. Comprueba tres
# cosas que se rompen en silencio: que todo importe, que el balotario esté
# dentro de la imagen (se localiza por `Path(__file__)`, no por el directorio de
# trabajo) y que la plantilla del informe haya viajado con su carpeta.
RUN python -c "\
import mcp_server, storage; \
from orquestacion.catalogo import cargar_catalogo; \
from visualizacion.plantilla import PLANTILLA; \
temas = cargar_catalogo(); \
assert len(temas) == 5, temas; \
assert PLANTILLA.is_file(), PLANTILLA; \
print('imagen lista:', len(temas), 'temas del balotario')"

# Sin CMD con argumentos: el cliente MCP lanza el contenedor y le habla por
# stdin. No hay nada que pasarle por la línea de órdenes.
ENTRYPOINT ["python", "mcp_server.py"]
