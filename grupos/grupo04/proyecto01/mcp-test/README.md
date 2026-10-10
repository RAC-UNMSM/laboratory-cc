# grupo04-mcp-test — Métodos Numéricos

Servidor MCP educativo para Métodos Numéricos I y II. Registra 27 herramientas, dos MCP Apps e informes PDF con vista previa y descarga.

## Herramientas y alcance

Las herramientas cubren interpolación, errores, raíces, sistemas lineales, ajuste de datos, derivación, integración, EDO, valores propios, optimización, problemas de frontera y PDE. El catálogo completo está en docs/CATALOGO_HERRAMIENTAS.md. Los métodos, supuestos y límites están en docs/REFERENCIA_ALGORITMOS.md.

Las expresiones matemáticas se evalúan con un parser limitado; no se ejecuta código Python proporcionado por quien llama la herramienta. Los problemas de frontera y PDE se limitan a los casos descritos en el catálogo.

## Ejecución local en Docker

El proyecto se ejecuta con Docker Compose. app.py, host.exe y config.yml ya no forman parte del flujo: el servidor MCP corre en el contenedor y la exposición pública de producción la administra la infraestructura del laboratorio.

Requisitos: Docker Desktop iniciado, Python no es necesario para ejecutar el contenedor y la red externa lab_net disponible. En PowerShell, desde esta carpeta:

    $env:LAB_CONTAINER_NAME = "lab-grupo04_proyecto01_mcp-test"
    docker network inspect lab_net
    docker compose up --build

Si la red lab_net no existe, créala una sola vez. Crear esa red no inicia SeaweedFS; para generar PDFs en local, también debe haber un servicio SeaweedFS conectado a lab_net. Si no está disponible, prueba las herramientas con include_report=false.

    docker network create lab_net

El Compose publica el puerto 8000 del contenedor en un puerto libre del equipo para evitar conflictos con otros procesos. Consulta el puerto asignado con:

    docker compose port mcp-test 8000

Conecta MCP Inspector al puerto que imprima el comando, con la ruta /mcp. Por ejemplo, si muestra 0.0.0.0:49153, conecta a http://127.0.0.1:49153/mcp. Para detener, pulsa Ctrl+C y después ejecuta docker compose down. Los PDFs nuevos se guardan en SeaweedFS.

## Informes PDF y almacenamiento

Los PDF se generan en memoria con ReportLab y se suben a SeaweedFS. No se guardan en el disco del contenedor ni requieren volumen de reportes. Las respuestas incluyen report.preview_url y report.download_url. Las rutas de la app sirven el PDF como vista previa inline o descarga.

En producción, los enlaces se forman con LAB_DOMAIN y LAB_PUBLIC_PATH, variables que inyecta el despliegue del laboratorio. El almacenamiento usa el bucket grupo04-mcp-test-imgs. La ruta pública de informes requiere que la ruta de la app en Caddy reenvíe /reports/... al mismo contenedor que atiende /mcp. La ruta pública de imágenes configurada por el contrato del laboratorio es https://rac-unmsm.vekthos.org/img/grupo04-mcp-test.

En local, si SeaweedFS no está activo, las herramientas matemáticas funcionan con include_report=false, pero no se almacenan informes. El puerto publicado puede ser aleatorio. Si el enlace del PDF devuelto apunta al puerto local 8000, sustituye su host y puerto por el que mostró docker compose port.

## MCP Inspector

Con Docker ya activo, abre otra ventana de PowerShell y ejecuta:

    npx @modelcontextprotocol/inspector@latest

En Inspector, agrega una conexión Streamable HTTP a http://127.0.0.1:<puerto-asignado>/mcp. Selecciona Tools y ejecuta una herramienta. Para la lista de ejemplos consulta docs/GUIA_DE_USO.md y pruebas.txt.

## Documentación

- docs/CATALOGO_HERRAMIENTAS.md: nombres, argumentos y límites de las 27 herramientas.
- docs/GUIA_DE_USO.md: ejemplos de solicitudes.
- docs/REFERENCIA_ALGORITMOS.md: métodos numéricos implementados.
- docs/GUIA_DESPLIEGUE.md: Docker local y publicación en la infraestructura del curso.
- ejecucion.txt: pasos detallados de Docker, Inspector y diagnóstico.

La integración pública requiere que el administrador despliegue la app en lab_net, configure Caddy y asigne LAB_DOMAIN/LAB_PUBLIC_PATH.
