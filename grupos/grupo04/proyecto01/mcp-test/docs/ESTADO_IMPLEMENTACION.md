# Estado de implementación

El servidor registra 27 herramientas para Métodos Numéricos I y II y ofrece
dos interfaces MCP App. El contrato de resultados permite nivel inicial o
intermedio, tablas, gráficas y generación opcional de informes PDF.

## Modo de ejecución actual

El modo soportado es Docker Compose. app.py, host.exe y config.yml se retiran
del flujo del proyecto. Docker inicia server.py en 0.0.0.0:8000. El Compose
usa las variables LAB_CONTAINER_NAME, LAB_DOMAIN y LAB_PUBLIC_PATH que admite
la infraestructura, la red externa lab_net y un puerto de host asignado por
Docker para las pruebas locales.

## Informes

report.py construye PDF con ReportLab en un objeto BytesIO. storage.py los
sube a SeaweedFS, bucket grupo04-mcp-test-imgs, con límites de tiempo. Las
rutas HTTP de vista previa y descarga recuperan los bytes del storage; no
dependen de un archivo ni de un volumen local del contenedor. LAB_DOMAIN y
LAB_PUBLIC_PATH forman los enlaces públicos en producción.

La verificación anterior de las 27 herramientas corresponde a una versión
previa al cambio de almacenamiento. La integración actualizada con SeaweedFS
requiere que el usuario la levante en su Docker/lab_net para confirmar el
acceso real al bucket y a las rutas PDF.
