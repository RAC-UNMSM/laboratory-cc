# MCP-Cálculo — Grupo 02 — semana 01

Servidor **MCP (Model Context Protocol)** que conecta una IA con motores de
cálculo simbólico en Python (**SymPy**) para resolver y enseñar Cálculo I a IV
de forma **exacta**, no aproximada.

- **Identificador de la app:** `grupo02_semana01_mcp-calculo`
- **Contenedor:** `lab-grupo02_semana01_mcp-calculo`
- **Red:** `lab_net` (externa)
- **Transporte:** `streamable-http` en el puerto 8000 (dentro de Docker);
  `stdio` en local

## Qué hace

| Apartado | Qué es | Dónde se configura |
|---|---|---|
| **1. Resolutor de ejercicios** | modo **Examen** (formal, LaTeX, sin rodeos) y modo **Paso a paso** (pedagógico, con comprobación) | `skill/skill_resolver_examen.md`, `skill/skill_paso_a_paso.md` |
| **2. Tutor académico interactivo** | aprendizaje progresivo, desde cero o avanzado, **verificando** las respuestas del alumno con SymPy | `skill/skill_tutor_interactivo.md` + tool `verificar_respuesta` |

La diferencia con un chatbot que "sabe cálculo": aquí **ningún resultado se
inventa**. Cada número que sale de la respuesta pasó por SymPy, que es un motor
de álgebra simbólica: no calcula, **deduce**. `integral(x*exp(x), x)` da
`x*exp(x) - exp(x)` exacto, no `4.3` como haría un cálculo de punto flotario.

## Arquitectura

```text
                    +---------------------------------------+
   Cliente MCP      |    Servidor MCP (server.py)           |
   (Claude Code,    |                                       |
    Claude Desktop, |  SECCION 1  skill/*.md  -> prompts     |
    Inspector)      |                                       |
                    |  SECCION 2  tools base (SymPy)         |
                    |            - calcular_derivada         |
                    |            - calcular_integral         |
                    |            - calcular_gradiente        |
                    |            - verificar_respuesta        |
                    |            - estado_del_servidor        |
                    |                                       |
                    |  SECCION 3  carga dinamica:            |
                    |    tools/calculo1.py  -> calculo1_*    |
                    |    tools/calculo2.py  -> calculo2_*    |
                    |    tools/calculo3.py  -> calculo3_*    |
                    |    tools/calculo4.py  -> calculo4_*    |
                    +---------------------------------------+
                                      |
                                      v
                                    SymPy
```

**Lo importante de este diseño:** los módulos de `tools/` se cargan **en tiempo
de arranque**, no están escritos en `server.py`. Cada compañero sube su
`calculo<N>.py` y sus tools aparecen en el servidor, sin que nadie toque el
código del servidor y sin conflictos entre las 4 áreas. Es lo que hace posible
que 5 personas trabajen en paralelo.

## Estructura

```text
mcp-calculo/
  server.py               # orquestador: skills + tools base + carga dinamica
  requirements.txt        # mcp==2.1.1 (pinned), sympy, numpy
  Dockerfile              # python:3.11-slim
  docker-compose.yml      # mem_limit 512m, red lab_net
  .dockerignore
  skill/                  # contextos de comportamiento (Markdown)
    skill_resolver_examen.md
    skill_paso_a_paso.md
    skill_tutor_interactivo.md
  tools/                  # motores matematicos, uno por area
    README.md             # EL CONTRATO -- leer antes de escribir tu modulo
    _plantilla.py         # copiar -> calculo<N>.py
    calculo1.py           # (Saico Cristhian)
    calculo2.py           # (Rosales Yhin)
    calculo3.py           # (Vilcapoma Jefferson)
    calculo4.py           # (Meza Angel)
  tests/                  # pruebas de estructura (no necesitan sympy)
    test_estructura.py
  README.md
```

## Quién hace qué

| Integrante | Rol | Archivo |
|---|---|---|
| **Ortega Yucra Hiron Axl** | Líder / arquitectura MCP | `server.py`, `Dockerfile`, `docker-compose.yml`, repo |
| **Saico Merma Cristhian** | Cálculo I | `tools/calculo1.py` |
| **Rosales Izquierdo Yhin** | Cálculo II | `tools/calculo2.py` |
| **Vilcapoma Pariona Jefferson** | Cálculo III | `tools/calculo3.py` |
| **Meza Nolorbe Angel** | Cálculo IV | `tools/calculo4.py` |
| **Lau Huamantoma Carlos Yang Hu** | Prompts & QA | `skill/*.md`, `tests/` |

## Cómo probarlo en local

Sin Docker, con Python 3.11+ y las dependencias instaladas
(`pip install -r requirements.txt`):

```bash
cd grupos/grupo02/semana01/mcp-calculo
python server.py
```

Sale un resumen de qué se cargó y se queda escuchando **por stdio**, que es lo
que habla un cliente MCP. Para probarlo a mano:

```bash
npx @modelcontextprotocol/inspector
# Transport: stdio | Command: python | Args: server.py
```

En el Inspector: pestaña **Tools** para ver las 5 tools base, **Prompts** para
probar los 3 modos.

Para correr un módulo suelto sin el servidor (lo que el profesor pide ver en la
terminal):

```bash
python tools/calculo1.py
```

Tests de estructura (no necesitan SymPy ni PyYAML, corren en 1 segundo):

```bash
python -m unittest discover -s tests -v
```

## Cómo probarlo en Docker

```bash
docker network create lab_net        # la red externa, una sola vez
cd grupos/grupo02/semana01/mcp-calculo
docker compose up --build
```

El servidor queda escuchando en el puerto 8000 (dentro de la red `lab_net`).
El CI del repo hace exactamente este `up`, lee los logs y hace `down`.

## Comprobación de que todo carga

La tool `estado_del_servidor` es el diagnóstico oficial:

```json
{
  "estado": "exito",
  "modulos_cargados": ["calculo1", "calculo3"],
  "modulos_faltantes": ["calculo2", "calculo4"],
  "total_tools": 9
}
```

Si un módulo no aparece en `modulos_cargados`, el problema está en ese
archivo: no existe, no compila, o sus funciones no cumplen el contrato de
`tools/README.md`. **Nunca en `server.py`** — y eso es a propósito: el servidor
no se toca.

## Notas de implementación (por qué está así)

1. **`mcp==2.1.1` pinneado.** En la v2 del SDK, `FastMCP` pasó a llamarse
   `MCPServer` y se mudó de `mcp.server.fastmcp` a `mcp.server.mcpserver`. Con
   el pin, el import no puede romperse por una resolución de versión.
2. **`streamable-http`, no `stdio`, dentro del contenedor.** En `stdio` el
   proceso muere en cuanto se cierra la consola, así que el contenedor
   terminaría al instante y no habría nada que proxyar. `stdio` se sigue
   usando en local, con `MCP_TRANSPORT` decides cuál.
3. **`streamable-http`, no `sse`.** La variante SSE del SDK está poco
   mantenida; la que usan los clientes MCP actuales es `streamable-http`.
4. **Sin `ports:` en el compose.** El contenedor se une a `lab_net` y es el
   reverse proxy (Caddy) del repo de infraestructura el que lo alcanza por
   nombre de contenedor.
5. **Las tools devuelven `dict`, nunca lanzan.** Una excepción dentro de una
   tool MCP rompe la sesión del cliente completa, no solo esa llamada.
   Devolver `{"estado": "error", "mensaje": ...}` la convierte en algo que la
   IA puede leer y explicar.
6. **El `docstring` de cada tool es documentación para la IA**, no para
   humanos: es lo que lee el cliente MCP para saber cómo llamar la tool y qué
   sintaxis espera. Por eso el contrato de `tools/README.md` insiste en él.

## Pendiente

- Los 4 módulos de `tools/` (`calculo1.py` … `calculo4.py`) están pendientes:
  hasta que existan, el servidor funciona solo con las 5 tools base.
