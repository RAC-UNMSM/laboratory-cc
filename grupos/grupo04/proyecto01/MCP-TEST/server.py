"""
from mcp.server import MCPServer
mcp = MCPServer("Mi MCP")
@mcp.tool()
def sumar(a: int, b: int) -> int:
    #Suma dos números enteros.
    return a + b
@mcp.tool()
def multiplicar(a: int, b: int) -> int:
    #Multiplica dos números enteros.
    return a * b
@mcp.tool()
def saludar(nombre: str) -> str:
    #Devuelve un saludo.
    return f"Hola {nombre}, este mensaje viene desde Python mediante MCP."
if __name__ == "__main__":
    mcp.run()
"""
from pathlib import Path

from mcp.server import MCPServer
from mcp.server.apps import Apps

from interpolation import solve_interpolation
from report import generar_reporte_latex


BASE_DIR = Path(__file__).resolve().parent

UI_URI = "ui://interpolation/v2/main.html"
UI_FILE = BASE_DIR / "ui" / "interpolation.html"

if not UI_FILE.exists():
    raise FileNotFoundError(
        f"No se encontró la interfaz HTML: {UI_FILE}"
    )


apps = Apps()


def resolver_y_generar_reporte(
    points: list[dict[str, float]],
    x_eval: float,
    method: str,
    report_name: str = "interpolacion"
) -> dict:

    result = solve_interpolation(
        points,
        x_eval,
        method
    )

    try:
        report = generar_reporte_latex(
            result,
            report_name
        )

        result["report"] = report
        result["report_status"] = "ok"
        result["pdf_path"] = report["pdf"]

    except Exception as exc:
        result["report"] = None
        result["report_status"] = "error"
        result["report_error"] = str(exc)
        result["pdf_path"] = None

    return result


@apps.tool(
    resource_uri=UI_URI,
    name="resolver_interpolacion",
    title="Interpolación Newton/Lagrange",
    description=(
        "Resuelve interpolación mediante Newton o Lagrange "
        "y genera un reporte PDF. report_name permite elegir "
        "el nombre del archivo."
    )
)
def resolver_interpolacion(
    points: list[dict[str, float]],
    x_eval: float,
    method: str = "lagrange",
    report_name: str = "interpolacion"
) -> dict:

    return resolver_y_generar_reporte(
        points,
        x_eval,
        method,
        report_name
    )

@apps.tool(
    resource_uri=UI_URI,
    name="interpolacion_lagrange",
    title="Interpolación de Lagrange",
    description=(
        "Resuelve un problema mediante interpolación "
        "de Lagrange y genera un reporte LaTeX/PDF."
    )
)
def interpolacion_lagrange(
    points: list[dict[str, float]],
    x_eval: float
) -> dict:

    return resolver_y_generar_reporte(
        points,
        x_eval,
        "lagrange"
    )


@apps.tool(
    resource_uri=UI_URI,
    name="interpolacion_newton",
    title="Interpolación de Newton",
    description=(
        "Resuelve un problema mediante diferencias "
        "divididas de Newton y genera un reporte "
        "LaTeX/PDF."
    )
)
def interpolacion_newton(
    points: list[dict[str, float]],
    x_eval: float
) -> dict:

    return resolver_y_generar_reporte(
        points,
        x_eval,
        "newton"
    )


@apps.tool(
    resource_uri=UI_URI,
    name="comparar_interpolacion",
    title="Comparar Newton y Lagrange",
    description=(
        "Compara Newton y Lagrange para los mismos "
        "puntos, devuelve ambos resultados y genera "
        "un reporte PDF."
    )
)
def comparar_interpolacion(
    points: list[dict[str, float]],
    x_eval: float
) -> dict:

    result = resolver_y_generar_reporte(
        points,
        x_eval,
        "lagrange"
    )

    result["method"] = "Comparación"

    return result


apps.add_html_resource(
    UI_URI,
    UI_FILE.read_text(
        encoding="utf-8"
    ),
    name="interpolation-ui-v2",
    title="Interpolación Newton y Lagrange",
    description=(
        "Interfaz interactiva para visualizar "
        "problemas de interpolación polinomial "
        "mediante Newton y Lagrange."
    ),
    prefers_border=True
)


mcp = MCPServer(
    "INTERPOLA-MCP",
    extensions=[apps]
)


if __name__ == "__main__":
    mcp.run()