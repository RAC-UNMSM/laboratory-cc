"""Herramientas MCP integradas con el motor de INTERPOLA-MCP."""
from mcp.server import MCPServer

from interpolation import solve_interpolation
from reports import generate_reports

mcp = MCPServer("INTEGRACION-MCP")


def _solve(points, x_eval, method, generate_report=True, report_name="reporte_interpolacion"):
    result = solve_interpolation(points, x_eval, method)
    result["reports"] = generate_reports(result, report_name) if generate_report else None
    return result


@mcp.tool()
def resolver_interpolacion(points: list[dict[str, float]], x_eval: float, method: str = "lagrange", generate_report: bool = True, report_name: str = "reporte_interpolacion") -> dict:
    """Calcula por Newton o Lagrange y genera HTML, SVG de la gráfica y PDF opcional."""
    return _solve(points, x_eval, method, generate_report, report_name)


@mcp.tool()
def interpolacion_lagrange(points: list[dict[str, float]], x_eval: float, generate_report: bool = True, report_name: str = "reporte_lagrange") -> dict:
    """Interpola por Lagrange; devuelve resultados y rutas de HTML, SVG y PDF."""
    return _solve(points, x_eval, "lagrange", generate_report, report_name)


@mcp.tool()
def interpolacion_newton(points: list[dict[str, float]], x_eval: float, generate_report: bool = True, report_name: str = "reporte_newton") -> dict:
    """Interpola por Newton y devuelve su tabla, HTML, SVG de gráfica y PDF opcional."""
    return _solve(points, x_eval, "newton", generate_report, report_name)


@mcp.tool()
def comparar_interpolacion(points: list[dict[str, float]], x_eval: float, generate_report: bool = True, report_name: str = "comparacion_interpolacion") -> dict:
    """Calcula ambos métodos, los compara y guarda HTML, SVG y PDF opcional."""
    return _solve(points, x_eval, "lagrange", generate_report, report_name)


if __name__ == "__main__":
    mcp.run()
