FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py storage.py .
COPY matematica/ matematica/
COPY orquestacion/ orquestacion/
COPY visualizacion/ visualizacion/
COPY balotario/ balotario/

CMD ["python", "server.py"]
