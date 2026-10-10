# extrapolacion-richardson-mcp

Servidor MCP del grupo 03: extrapolación de Richardson aplicada a derivación, integración (Romberg),
EDOs (Bulirsch-Stoer) y análisis de convergencia. La propuesta del grupo está en
[`extrapolacion-de-richardson.md`](../extrapolacion-de-richardson/extrapolacion-de-richardson.md).

- Identificador: `grupo03_proyecto01_extrapolacion-richardson-mcp`
- URL del MCP: `https://rac-unmsm.vekthos.org/grupo03/grupo03_proyecto01_extrapolacion-richardson-mcp/mcp`
- Conectar: `claude mcp add --transport http grupo03-richardson <URL>`

## Tools

| Tool | Entrada típica |
|---|---|
| `derivacion_richardson` | `expresion="sin(x)", x0=1` |
| `romberg` | `expresion="exp(-x^2)", a=0, b=1, tolerancia=1e-8` |
| `richardson_generico` | `metodo="trapecio", expresion="sin(x)", a=0, b=3.14159` |
| `bulirsch_stoer` | `expresion="-y", t0=0, y0=1, tf=5` |
| `analisis_convergencia` | `problema="derivada"` o `"integral"`, `expresion=...` |

Cada una devuelve JSON (resultado, tabla, error estimado, explicación), el link markdown de los
gráficos subidos a SeaweedFS y los mismos gráficos como `ImageContent`.

## Módulos por rol

`server.py` solo orquesta. `validacion.py` (parseo seguro de funciones y rangos) · `derivacion_richardson.py` ·
`romberg.py` · `richardson_generico.py` · `bulirsch_stoer.py` · `convergencia.py` · `visualizacion.py` ·
`explicacion.py` · `storage.py` (SeaweedFS). Los módulos numéricos no importan `mcp` ni hacen red: se
prueban sin levantar el servidor.

## Probar en local

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python server.py                                       # http://localhost:8000/mcp
claude mcp add --transport http richardson-local http://localhost:8000/mcp
```

Fuera del lab no hay SeaweedFS: `storage.subir_imagen()` devuelve `None`, las tools responden igual
y los gráficos llegan solo como `ImageContent`.

Con Docker (opcional): `docker build -t richardson . && docker run --rm -p 8000:8000 richardson`.
