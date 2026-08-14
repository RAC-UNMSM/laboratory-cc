# MCP reference server "filesystem" (semanas 1-12, sección 1.6 del plan:
# mapeado a VLANs/segmentación). Imagen base verificada por `docker pull`
# (Alpine, ya trae node/npm) durante la construcción de este proyecto.
#
# Se envuelve con supergateway (stdio -> SSE) para que MCP Inspector pueda
# conectarse por URL en vez de que el propio Inspector tenga que spawnear
# el proceso. TODO antes de la clase piloto: probar con Inspector real que
# el wrapping SSE funciona con la versión vigente de la imagen.
FROM mcp/filesystem

RUN npm install -g supergateway

# /data es un volumen nombrado (ver docker-compose.yml) con contenido de
# muestra — el server de filesystem solo puede leer/escribir ahí dentro,
# nunca rutas del host (por diseño: no hay bind-mounts, sección de reglas
# del plan).
ENTRYPOINT ["supergateway", "--stdio", "node /app/dist/index.js /data", "--port", "8000", "--outputTransport", "sse"]
