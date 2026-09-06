# Piloto del proyecto de semana 2-3 (ver docs/semana-02/plan.md del repo de
# infraestructura) -- servidor MCP propio en Python con FastMCP, en vez de
# envolver un servidor de referencia ya hecho. Mismo patrón base que
# TEMPLATE/semana01/ejemplo-script (python:3.11-slim), pero de larga
# duración (expone SSE en el puerto 8000) en vez de correr una vez.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py validacion.py matematica.py visualizacion.py storage.py .

CMD ["python", "server.py"]
