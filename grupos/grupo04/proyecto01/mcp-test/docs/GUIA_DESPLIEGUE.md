# Guía de ejecución y despliegue

## Local con app.py
1. Abre PowerShell en mcp-test.
2. Activa .ENTORNO si existe.
3. Instala/actualiza: python -m pip install -r requirements.txt.
4. Confirma hostname y rutas /mcp y /reports en config.yml.
5. Ejecuta python app.py y conserva abierta esa consola.
6. Inspector local: http://127.0.0.1:8000/mcp. Público: https://<hostname>/mcp.
7. Ctrl+C detiene MCP y cloudflared.

No ejecutar app.py y Docker al mismo tiempo por el puerto 8000. No subir credenciales del túnel.

## Docker
1. Inicia Docker Desktop.
2. Define LAB_CONTAINER_NAME en la misma ventana PowerShell.
3. Crea lab_net si falta.
4. Ejecuta docker compose up --build.
5. Usa http://localhost:8000/mcp para la prueba local.
6. Para público, ejecuta host.exe/cloudflared con config.yml desde otra ventana.
7. Mantén servidor y túnel activos.
8. Ctrl+C y docker compose down para detener.

reports_data es volumen nombrado. docker compose down -v elimina el volumen y los informes.

## Cloudflare ingress
Antes del fallback 404 deben existir:
- hostname + path ^/mcp(/.*)?$ a http://127.0.0.1:8000
- hostname + path ^/reports(/.*)?$ a http://127.0.0.1:8000
- fallback http_status:404

Reinicia cloudflared después de modificar config. Un GET /mcp en navegador no ejecuta una sesión MCP. Si /reports da 404, comprueba que PDF exista y que ingress incluya esa ruta.

## Problemas frecuentes
Connection refused: servidor/contendor apagado o puerto incorrecto.
LAB_CONTAINER_NAME vacío: definir variable en esa ventana.
lab_net no existe: crear red externa.
404 de sesión MCP vieja: reconectar el Inspector.
404 PDF: revisar enlace nuevo, storage/volumen e ingress.

## Reportes y recursos de ejecución

Los PDF se generan con ReportLab; no hace falta `pdflatex` ni instalar TeX Live. Docker Compose conserva los reportes en `reports_data` y usa `lab-grupo04_proyecto01_mcp-test` si no se define `LAB_CONTAINER_NAME`. La red externa `lab_net` debe existir en la máquina para el modo local del laboratorio.

`app.py` inicia el mismo `server.py` desde el entorno `.ENTORNO` y puede levantar `host.exe`/cloudflared usando `config.yml`. El servicio MCP escucha en 8000; el ingress de Cloudflare debe dirigir el hostname a `http://127.0.0.1:8000`, de modo que funcionen tanto `/mcp` como `/reports/...`. Mantén el proceso activo mientras quieras acceso público.
