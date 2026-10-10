"""Ejecuta los cinco metodos y genera un informe HTML para cada resultado.

Ejecutar desde la carpeta del proyecto:
    python -m examples.generar_reportes_metodos --salida salida-metodos
"""

import argparse
from pathlib import Path

from metodos.cuasi_newton import cuasi_newton_broyden
from metodos.descenso import descenso_mas_rapido
from metodos.homotopia import homotopia_continuacion
from metodos.newton_sistemas import newton_sistemas
from metodos.punto_fijo import punto_fijo_varias_variables
from reportes import guardar_reporte_html
from resultado import ResultadoMetodo


def ejecutar_metodos() -> list[ResultadoMetodo]:
    """Calcula resultados con los mismos casos numericos usados por los tests."""
    resultado_punto_fijo = punto_fijo_varias_variables(
        [
            lambda x: (x[0] + x[1] + 1.0) / 3.0,
            lambda x: (x[0] - x[1] + 2.0) / 3.0,
        ],
        x0=[0.0, 0.0],
        tolerancia=1e-10,
        max_iter=200,
    )

    def f1(x):
        return x[0] ** 2 + x[1] ** 2 - 1.0

    def f2(x):
        return x[0] - x[1]

    funciones = [f1, f2]
    return [
        resultado_punto_fijo,
        newton_sistemas(funciones, [1.0, 0.5], tolerancia=1e-10, max_iter=50),
        cuasi_newton_broyden(funciones, [1.0, 0.5], tolerancia=1e-8, max_iter=100),
        descenso_mas_rapido(funciones, [1.0, 0.5], tolerancia=1e-6, max_iter=1000),
        homotopia_continuacion(funciones, [0.9, 0.4], tolerancia=1e-8, max_iter=50),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=Path("salida-metodos"))
    args = parser.parse_args()
    args.salida.mkdir(parents=True, exist_ok=True)

    for resultado in ejecutar_metodos():
        destino = guardar_reporte_html(
            resultado,
            args.salida / f"reporte_{resultado.method}.html",
            titulo=f"Reporte: {resultado.method}",
        )
        residuo = (
            "no disponible"
            if resultado.final_residual is None
            else f"{resultado.final_residual:.3e}"
        )
        print(
            f"{resultado.method}: {resultado.status.value}; "
            f"residuo={residuo}; archivo={destino}"
        )


if __name__ == "__main__":
    main()