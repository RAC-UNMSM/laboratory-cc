# MCP reference server "everything" (semana 1 del sílabo: servidor DEMO
# oficial, sin tarea real — solo para ver el protocolo MCP funcionando en
# Inspector, comparándolo con una captura de Wireshark). Imagen base
# verificada por `docker pull` (Alpine, ya trae node/npm) durante la
# construcción de este proyecto.
#
# Mismo wrapping que filesystem/fetch/github (stdio -> SSE via supergateway)
# para que Inspector se conecte por URL. TODO antes de la clase piloto:
# probar con Inspector real.
FROM mcp/everything

RUN npm install -g supergateway

ENTRYPOINT ["supergateway", "--stdio", "node dist/index.js", "--port", "8000", "--outputTransport", "sse"]
