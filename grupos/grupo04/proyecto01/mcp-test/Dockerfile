
# Imagen base de Python
FROM python:3.11-slim

# Directorio de trabajo
WORKDIR /app

# Evitar archivos .pyc y activar salida inmediata de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Los informes PDF se generan con ReportLab; no se requiere TeX Live.
ENV PIP_NO_CACHE_DIR=1

# Copiar dependencias
COPY requirements.txt ./

# Instalar librerias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar archivos necesarios para el servidor MCP
COPY server.py interpolation.py numerical_methods.py report.py storage.py ./
COPY ui/ ./ui/

# Puerto del servidor MCP
EXPOSE 8000

# Ejecutar el servidor
CMD ["python", "server.py"]
