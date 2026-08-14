# MCP reference server "github" (semanas 1-12, sección 1.6 del plan:
# mapeado a ACLs/token con scope). ghcr.io/github/github-mcp-server es una
# imagen "distroless" (sin shell, binario Go estático) — verificado con
# `docker pull` + inspección de que el binario es ELF estático, así que se
# puede copiar a una base normal (node:alpine) para instalarle supergateway
# encima (stdio -> SSE). No se puede extender la imagen original in-place
# porque no tiene ni shell para correr comandos de instalación.
#
# TODO antes de la clase piloto: probar con Inspector real y con un token
# de solo-lectura de verdad.
FROM ghcr.io/github/github-mcp-server AS ghms

FROM node:20-alpine
RUN npm install -g supergateway
COPY --from=ghms /server/github-mcp-server /usr/local/bin/github-mcp-server

ENTRYPOINT ["supergateway", "--stdio", "github-mcp-server stdio", "--port", "8000", "--outputTransport", "sse"]
