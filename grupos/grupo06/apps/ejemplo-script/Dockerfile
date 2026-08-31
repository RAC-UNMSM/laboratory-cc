# Plantilla para "scripts/pipelines propios" (a diferencia de ejemplo-n8n,
# que despliega una app open source ya armada). El alumno modifica script.py
# — el resto (Dockerfile, docker-compose.yml) normalmente no hace falta
# tocarlo. Imagen base mínima y confiable: python:3.11-slim.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY script.py .

CMD ["python", "script.py"]
