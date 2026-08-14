# MCP reference server "fetch" (semanas 1-12, sección 1.6 del plan). Imagen
# base verificada por `docker pull` (Debian bookworm + venv de Python,
# entrypoint mcp-server-fetch) durante la construcción de este proyecto.
# nodejs 18.20.4 confirmado disponible via apt en esta base para poder
# instalar supergateway (stdio -> SSE).
#
# TODO antes de la clase piloto: probar con Inspector real.
FROM mcp/fetch

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g supergateway

ENTRYPOINT ["supergateway", "--stdio", "/app/.venv/bin/mcp-server-fetch", "--port", "8000", "--outputTransport", "sse"]
