# Imagen base oficial y liviana de Python 3.11
FROM python:3.11-slim

# Configuraciones de optimización para Python en Docker
# PYTHONDONTWRITEBYTECODE: Evita que Python contamine el contenedor con archivos .pyc
# PYTHONUNBUFFERED: Fuerza a que los prints/logs salgan inmediatamente en la consola (vital para debug)
# MPLBACKEND: Obliga a matplotlib a generar las gráficas en RAM sin buscar una pantalla física
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLBACKEND=Agg

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar primero solo los requerimientos para optimizar la caché de Docker
COPY requirements.txt .

# Instalar dependencias (pip usará las versiones exactas que definimos antes)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente del proyecto
COPY . .

# # Exponer el puerto estándar de FastMCP (streamable-http)
EXPOSE 8000

# Ejecutar el servidor. 
CMD ["python", "server.py"]