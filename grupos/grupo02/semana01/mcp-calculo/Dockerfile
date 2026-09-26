# Servidor MCP propio del Grupo 02 (ver README.md).
#
# Misma imagen base que TEMPLATE/semana01/ejemplo-script (python:3.11-slim),
# pero de larga duracion: es un servidor HTTP que queda escuchando en el 8000,
# no un script que corre una vez y termina.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# El servidor importa los modulos de calculo de tools/ por ruta (ver
# SECCION 3 de server.py), asi que la carpeta se copia completa. skill/ tambien
# se copia: los 3 contextos de comportamiento se leen en tiempo de ejecucion.
COPY server.py .
COPY tools/ tools/
COPY skill/ skill/

# Puerto de streamable-http. No se publica con `ports:` en el compose porque no
# hace falta: el contenedor se une a la red externa lab_net y es el reverse
# proxy (Caddy) del repo de infraestructura el que lo alcanza por nombre de
# contenedor. Ver punto 6 de grupos/TEMPLATE/README.md.
EXPOSE 8000

# MCP_TRANSPORT=streamable-http y no el default stdio: dentro del contenedor no
# hay consola que alimente el proceso, asi que en stdio el container terminaria
# al instante. Ver SECCION 4 de server.py.
ENV MCP_TRANSPORT=streamable-http \
    MCP_PORT=8000

CMD ["python", "server.py"]
