# Imagen base liviana de Python
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y asegura que los logs se muestren en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Forzar a Matplotlib a funcionar en modo headless (sin interfaz gráfica)
ENV MPLBACKEND=Agg

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Puerto expuesto para la comunicación MCP por SSE (Server-Sent Events)
EXPOSE 8000

# Ejecutar FastMCP expuesto a la red
CMD ["fastmcp", "run", "server.py", "--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
