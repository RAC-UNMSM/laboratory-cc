# Guía de ejecución y despliegue

## Modo local: Docker Compose

Este proyecto se ejecuta en Docker. app.py, host.exe y config.yml no son parte
del modo de ejecución. El contenedor inicia server.py; para producción, la
infraestructura del laboratorio configura el acceso público.

En PowerShell, desde mcp-test:

    $env:LAB_CONTAINER_NAME = "lab-grupo04_proyecto01_mcp-test"
    docker network inspect lab_net
    docker compose up --build

Si lab_net no existe, créala una vez con docker network create lab_net. Crear
la red no inicia SeaweedFS. Para generar PDF localmente, SeaweedFS también debe
estar activo y conectado a lab_net. Sin ese servicio, usa include_report=false
para probar los cálculos. El Compose publica el puerto interno 8000 en un puerto
local aleatorio. En una segunda ventana consulta el asignado:

    docker compose port mcp-test 8000

Abre Inspector en otra ventana con npx @modelcontextprotocol/inspector@latest
y conecta por Streamable HTTP a http://127.0.0.1:<puerto>/mcp. Reemplaza
<puerto> por el valor de docker compose port.

Para detener: Ctrl+C en la ventana de Docker y luego docker compose down.
Los informes PDF están en SeaweedFS y permanecen al recrear el contenedor.

## Despliegue del laboratorio

El servidor escucha en 0.0.0.0:8000 dentro del contenedor y usa la red externa
lab_net. En producción, el agente del curso inyecta LAB_CONTAINER_NAME,
LAB_DOMAIN y LAB_PUBLIC_PATH. Caddy reenvía la ruta pública de la app al
contenedor y elimina el prefijo antes de enviar la solicitud. El acceso MCP
termina en /mcp; las rutas /reports/<archivo>/preview y
/reports/<archivo>/download deben llegar al mismo contenedor.

No se requiere puerto fijo en el host. Compose publica el puerto 8000 sin fijar
un puerto de Windows; el despliegue de producción usa el puerto interno del
contenedor en lab_net.

## Informes y persistencia

ReportLab genera los PDF en memoria. storage.py los sube con timeout al
SeaweedFS de lab_net, al bucket grupo04-mcp-test-imgs. El servidor los recupera
desde SeaweedFS y entrega la vista previa con Content-Disposition inline o la
descarga como attachment. No hay volumen local reports_data ni archivos
temporales persistentes en el contenedor.

Las URL de informes se construyen con LAB_DOMAIN y LAB_PUBLIC_PATH. El acceso
público requiere que Caddy enrute también /reports hacia este servidor y que
SeaweedFS esté disponible. Si la subida falla, el cálculo numérico se conserva
y la respuesta indica que el PDF no pudo generarse o almacenarse.

## Diagnóstico

- Herramientas MCP: en Inspector, abre Tools después de conectar.
- Puerto local: docker compose port mcp-test 8000.
- Estado: docker compose ps.
- Logs: docker compose logs --since 5m --timestamps mcp-test.
- 400 Missing session ID en un navegador: usa Inspector; /mcp no es una web.
- Sesión desconocida luego de reiniciar: reconecta el Inspector.
- HTTP 502 en reportes: revisa SeaweedFS y la red lab_net.
