# Grupo 02 · Servidor MCP de Cálculo I–IV

Implementación 1.0.0 de la propuesta del Grupo 02, UNMSM. Servidor
`grupo02-calculo-i-iv`, Python 3.11, SDK oficial MCP 2.1.1, SymPy.

**Estado:** implementación verificable y preparada para el contrato del
laboratorio. La aceptación final de producción requiere construir la imagen,
probar SeaweedFS y verificar el proxy/autenticación en la infraestructura real.
No se ha desplegado ni publicado el servicio desde esta entrega.

## Inicio local

Desde esta carpeta:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python server.py
```

En Windows: `.venv\Scripts\activate`. El servidor escucha en `0.0.0.0:8000`;
para pruebas utilice `http://127.0.0.1:8000/mcp` con un cliente MCP. No es una
página web. La ejecución local no incorpora autenticación: úsela en un equipo
confiable; para exposición remota siga [DESPLIEGUE.md](docs/DESPLIEGUE.md).

## Herramientas

| Herramienta MCP | Función |
|---|---|
| `resolver` | 20 operaciones mediante un esquema discriminado por `operacion` |
| `catalogo` | Operaciones, temas, gramática y límites |
| `leccion` | Teoría, ejemplo, ejercicio y pistas de nueve temas |
| `verificar_respuesta` | Equivalencia simbólica del ejercicio de cada lección |
| `graficar` | PNG de una función real continua y publicación opcional en SeaweedFS |

Tres prompts: `resolver_examen`, `resolver_paso_a_paso`, `tutor_interactivo`.
Un recurso: `calculo://guia`. No requiere una clave de OpenAI ni otra API de IA.
El cliente aporta el modelo de lenguaje y administra su contexto educativo.

Ejemplo de argumentos de `resolver`:

```json
{
  "problema": {
    "operacion": "integral_multiple",
    "expresion": "1",
    "limites": [
      {"variable": "y", "inferior": "0", "superior": "x"},
      {"variable": "x", "inferior": "0", "superior": "1"}
    ]
  },
  "modo": "paso_a_paso"
}
```

Resultado exacto: `1/2`. Los límites se escriben **de dentro hacia fuera**.

## Verificación

Detenga el servidor local antes de las pruebas: la integración real usa 8000.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Pruebas matemáticas, entradas maliciosas, dominio, orientación, cancelación,
concurrencia, tutor, PNG, almacenamiento simulado y comunicación MCP en memoria
y por HTTP. La evidencia ejecutada está en [VALIDACION.md](docs/VALIDACION.md).

## Organización

- `server.py`: herramientas, prompts y recursos; no implementa los algoritmos.
- `models.py`: validación estricta y JSON Schema de entrada.
- `validacion.py`: gramática AST cerrada sin `eval` ni `parse_expr`.
- `runtime.py`, `worker.py`: proceso por cálculo, tiempo y memoria limitados.
- `engine.py`, `tools/`: despacho y motores de Cálculo I, II, III y IV.
- `tutor.py`, `skills/`: catálogo didáctico y prompts independientes.
- `visualizacion.py`, `storage.py`: imágenes en memoria y SeaweedFS opcional.
- `tests/`: pruebas repetibles. `examples/`: solicitudes listas para adaptar.
- `requirements.lock`: dependencias transitivas fijadas con hashes.

Consulte [API](docs/API.md), [arquitectura](docs/ARQUITECTURA.md),
[seguridad](docs/SEGURIDAD.md), [despliegue](docs/DESPLIEGUE.md) y
[revisión de la entrega](docs/REVISION.md).
