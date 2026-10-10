# Mantenimiento

Mantener cada motor independiente del SDK. Agregar un modelo a `models.py`,
una entrada al despacho cerrado y pruebas matemáticas con valores conocidos
antes de ampliar la API. Regenerar JSON Schema si cambia el contrato.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Para regenerar lock con uv disponible, desde la carpeta del proyecto:

```bash
uv pip compile requirements.txt --python-version 3.11 --generate-hashes -o requirements.lock
```

Después instalar con `--require-hashes`, ejecutar pruebas y reconstruir Docker.
No actualizar el SDK mayor sin revisar las reglas del laboratorio y su API.
El Dockerfile instala primero el lock comprobando hashes y luego los directos
con `--no-deps`; esta segunda comprobación conserva compatibilidad con el
validador textual del laboratorio sin resolver dependencias nuevas.

Los tests de almacenamiento usan dobles controlados; no sustituyen una prueba
real con SeaweedFS. Los tests de HTTP arrancan `python server.py` en puerto 8000:
no deje otra instancia ejecutándose durante la suite.

Para uso sin MCP, dentro de esta carpeta:

```python
import asyncio
from runtime import execute
print(asyncio.run(execute("resolver", {
    "problema": {"operacion": "derivada", "expresion": "sin(x**2)"},
    "modo": "paso_a_paso"
})))
```

No exponer directamente `engine.solve` a entradas no confiables: se debe usar
el ejecutor que aplica límites de recursos. No sustituir el parser por eval,
sympify(texto), parse_expr ni ejecutar código recibido por un cliente.
