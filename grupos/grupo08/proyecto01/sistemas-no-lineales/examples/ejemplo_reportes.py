"""Ejemplo: generar visualizacion y reportes para un resultado simulado.

Ejecutar desde la carpeta del proyecto:
    python -m examples.ejemplo_reportes --salida salida-ejemplo
"""

import argparse
from pathlib import Path

from reportes import guardar_reporte_html, guardar_reporte_latex
from resultado import EstadoMetodo, ResultadoMetodo
from visualizacion import guardar_visualizacion_html


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("salida-ejemplo"))
    args = parser.parse_args()

    resultado = ResultadoMetodo(
        method="newton_sistemas",
        status=EstadoMetodo.CONVERGED,
        solution=[0.70710678, 0.70710678],
        iterations=4,
        final_error=1e-10,
        final_residual=1e-10,
        trajectory=[
            [1.0, 0.5],
            [0.75, 0.75],
            [0.70833333, 0.70833333],
            [0.70710678, 0.70710678],
        ],
        message="Convergencia alcanzada.",
    )

    args.salida.mkdir(parents=True, exist_ok=True)
    visualizacion = guardar_visualizacion_html(resultado, args.salida / "trayectoria.html")
    html_path = guardar_reporte_html(resultado, args.salida / "reporte.html")
    latex_path = guardar_reporte_latex(resultado, args.salida / "reporte.tex")
    print(f"Visualizacion: {visualizacion}")
    print(f"Reporte HTML: {html_path}")
    print(f"Reporte LaTeX: {latex_path}")


if __name__ == "__main__":
    main()