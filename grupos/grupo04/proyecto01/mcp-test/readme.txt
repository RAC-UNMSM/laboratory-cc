MCP GRUPO04 — EJECUCIÓN DOCKER

Este proyecto se ejecuta con Docker Compose. Ya no se usa app.py, host.exe ni
config.yml. El contenedor inicia server.py; los PDF se generan en memoria y se
guardan en SeaweedFS.

Desde PowerShell:

    cd C:\Users\User\Desktop\laboratory-cc-grupo04\grupos\grupo04\proyecto01\mcp-test
    $env:LAB_CONTAINER_NAME = "lab-grupo04_proyecto01_mcp-test"
    docker network inspect lab_net
    docker compose up --build

Si lab_net no existe, créala una vez con docker network create lab_net. La red no inicia SeaweedFS; sin ese servicio usa include_report=false para probar los cálculos sin generar PDF.

En otra ventana, consulta el puerto publicado:

    docker compose port mcp-test 8000

Inicia MCP Inspector con npx @modelcontextprotocol/inspector@latest y conecta
por Streamable HTTP a http://127.0.0.1:<puerto>/mcp.

Detén con Ctrl+C y luego docker compose down. Los PDF nuevos quedan en
SeaweedFS y no dependen de un volumen local.
