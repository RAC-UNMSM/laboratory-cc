# Servidor MCP del grupo 03 (extrapolación de Richardson). Mismo patrón que el piloto
# g01/semana01/derivadas1: python:3.11-slim, servidor de larga duración en el puerto 8000.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py validacion.py derivacion_richardson.py romberg.py richardson_generico.py bulirsch_stoer.py convergencia.py visualizacion.py explicacion.py storage.py .

CMD ["python", "server.py"]
