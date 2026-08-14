"""Plantilla de MCP server propio (semana 13+ del sílabo, Python).

Misma plantilla para todos los grupos, para que la dificultad sea pareja
(sección 1.6 del plan). Cada grupo la copia, le agrega 1-2 tools propias, y
la despliega con el mismo patrón de asset de Fase 5 (docker compose vía
Dagster, nunca a mano).

Corre en transporte SSE directamente (sin necesitar supergateway, a
diferencia de los MCP servers de referencia de Fase 6 que ya venían
empaquetados en stdio) para que MCP Inspector se conecte por URL.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lab-grupo-mcp-server")


@mcp.tool()
def echo(text: str) -> str:
    """Devuelve el mismo texto que se le pase (ejemplo mínimo de tool)."""
    return text


@mcp.tool()
def suma(a: float, b: float) -> float:
    """Suma dos números (ejemplo mínimo de tool con más de un argumento)."""
    return a + b


# TODO (alumnos): reemplazar/agregar tools propias del ejercicio del grupo.


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
