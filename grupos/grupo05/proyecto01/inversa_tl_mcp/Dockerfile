FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY server.py validacion.py matriz_tl.py gauss_jordan.py inversa_tl.py presentacion.py storage.py visualizacion.py .

CMD ["python", "server.py"]