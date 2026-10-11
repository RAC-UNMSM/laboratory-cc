FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=10001:10001 . .

# El servidor escribe reportes y el historial de ejercicios en estos
# directorios; deben existir y pertenecer al usuario no-root (los volúmenes
# nombrados del compose heredan este dueño la primera vez que se montan).
RUN mkdir -p /app/config /app/salida-mathjax \
    && chown 10001:10001 /app /app/config /app/salida-mathjax

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3).close()"]

CMD ["python", "server.py"]
