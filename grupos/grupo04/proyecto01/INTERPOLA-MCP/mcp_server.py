"""
Servidor MCP del proyecto.

Este archivo expone las mismas funciones matemáticas como herramientas MCP.
El navegador usa app.py para la interfaz HTTP; este servidor puede probarse
por separado con el MCP Inspector.

Requiere el SDK oficial de MCP v2:
    pip install "mcp[cli]"
"""

from mcp.server import MCPServer
from interpolation import solve_interpolation

mcp = MCPServer("INTERPOLA-MCP")

@mcp.tool()
def interpolacion_lagrange(points: list[dict[str, float]], x_eval: float) -> dict:
    """Calcula interpolación polinomial de Lagrange y devuelve datos para la interfaz."""
    return solve_interpolation(points, x_eval, "lagrange")

@mcp.tool()
def interpolacion_newton(points: list[dict[str, float]], x_eval: float) -> dict:
    """Calcula interpolación polinomial de Newton y devuelve diferencias divididas."""
    return solve_interpolation(points, x_eval, "newton")

@mcp.tool()
def comparar_metodos(points: list[dict[str, float]], x_eval: float) -> dict:
    """Compara los resultados de Lagrange y Newton."""
    result = solve_interpolation(points, x_eval, "lagrange")
    return {
        "lagrange": result["lagrange_value"],
        "newton": result["newton_value"],
        "difference": result["difference"],
    }

if __name__ == "__main__":
    mcp.run()
