"""Módulo de cálculo multivariable en R³ y optimización.

Este módulo implementa funciones para calcular gradientes en R³
y determinar/clasificar puntos críticos usando el criterio de la matriz Hessiana.
"""

from __future__ import annotations

from typing import Any
import sympy as sp

# Herramientas a registrar en el servidor MCP
HERRAMIENTAS = ["gradiente", "puntos_criticos_optimizacion"]


def gradiente(expresion: str, variables: str = "x, y, z") -> dict[str, Any]:
    """Calcula el vector gradiente de una función en R³.

    Args:
        expresion: Expresión matemática en formato SymPy (ej. 'x**2 + y**2 - z**2').
        variables: Variables de la función separadas por coma (ej. 'x, y, z').

    Returns:
        Diccionario con el resultado del cálculo o mensaje de error.
    """
    try:
        # Convertimos las variables ingresadas en símbolos de SymPy
        lista_vars = [sp.Symbol(v.strip()) for v in variables.split(",")]
        f = sp.sympify(expresion)

        # Calculamos la derivada parcial respecto a cada variable
        vec_gradiente = [sp.diff(f, v) for v in lista_vars]

        # Formateamos el gradiente en notación vectorial LaTeX
        componentes_latex = ", ".join(sp.latex(g) for g in vec_gradiente)
        latex_str = f"\\nabla f = \\begin{{pmatrix}} {componentes_latex} \\end{{pmatrix}}"

        return {
            "estado": "exito",
            "funcion": sp.sstr(f),
            "variables": [sp.sstr(v) for v in lista_vars],
            "gradiente": [sp.sstr(g) for g in vec_gradiente],
            "latex": latex_str,
        }
    except Exception as err:
        return {"estado": "error", "mensaje": f"{type(err).__name__}: {err}"}


def puntos_criticos_optimizacion(
    expresion: str, variables: str = "x, y"
) -> dict[str, Any]:
    """Encuentra y clasifica los puntos críticos de una función multivariable.

    Aplica el criterio de la segunda derivada (matriz Hessiana) para funciones de 2 variables.

    Args:
        expresion: Función objetivo en formato SymPy (ej. 'x**3 + y**3 - 3*x - 12*y').
        variables: Variables separadas por coma (ej. 'x, y').

    Returns:
        Diccionario con la lista de puntos críticos hallados y su tipo.
    """
    try:
        lista_vars = [sp.Symbol(v.strip()) for v in variables.split(",")]
        f = sp.sympify(expresion)

        # 1. Hallar derivadas parciales e igualar a cero (∇f = 0)
        grad = [sp.diff(f, v) for v in lista_vars]
        eqs = [sp.Eq(g, 0) for g in grad]

        # 2. Resolver el sistema
        soluciones = sp.solve(eqs, lista_vars, dict=True)

        if not soluciones:
            return {
                "estado": "parcial",
                "funcion": sp.sstr(f),
                "puntos_criticos": [],
                "mensaje": "No se encontraron puntos críticos analíticos.",
            }

        resultados = []

        # 3. Clasificación para funciones en R² mediante el determinante del Hessiano
        if len(lista_vars) == 2:
            var1, var2 = lista_vars[0], lista_vars[1]
            f_xx = sp.diff(f, var1, var1)
            f_yy = sp.diff(f, var2, var2)
            f_xy = sp.diff(f, var1, var2)

            # D = f_xx * f_yy - (f_xy)^2
            det_hessiano = f_xx * f_yy - (f_xy**2)

            for sol in soluciones:
                # Evaluamos el determinante y f_xx en cada punto crítico
                d_val = det_hessiano.subs(sol)
                fxx_val = f_xx.subs(sol)

                if d_val > 0:
                    tipo = "Mínimo local" if fxx_val > 0 else "Máximo local"
                elif d_val < 0:
                    tipo = "Punto silla"
                else:
                    tipo = "Inconcluso (D = 0)"

                pto = {sp.sstr(k): sp.sstr(v) for k, v in sol.items()}
                resultados.append({"punto": pto, "tipo": tipo})
        else:
            # Para dimensiones mayores (R³, etc.)
            for sol in soluciones:
                pto = {sp.sstr(k): sp.sstr(v) for k, v in sol.items()}
                resultados.append(
                    {"punto": pto, "tipo": "No clasificado (requiere análisis n-dimensional)"}
                )

        return {
            "estado": "exito",
            "funcion": sp.sstr(f),
            "puntos_criticos": resultados,
            "latex": sp.latex(soluciones),
        }
    except Exception as err:
        return {"estado": "error", "mensaje": f"{type(err).__name__}: {err}"}


# =============================================================================
# Pruebas de ejecución directa
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"Módulo: {__name__.rsplit('.', 1)[-1]}")
    print("=" * 60)

    # 1. Gradiente de prueba en R³
    print("\n[1] Gradiente de f(x, y, z) = x**2*y + y*z**3")
    print("   ", gradiente("x**2*y + y*z**3", variables="x, y, z"))

    # 2. Optimización en R²
    print("\n[2] Optimización de f(x, y) = x**3 + y**3 - 3*x - 12*y")
    print("   ", puntos_criticos_optimizacion("x**3 + y**3 - 3*x - 12*y"))

    # 3. Función sin puntos críticos
    print("\n[3] Optimización de f(x, y) = x + y")
    print("   ", puntos_criticos_optimizacion("x + y"))

    # 4. Prueba de manejo de errores
    print("\n[4] Sintaxis errónea")
    print("   ", gradiente("x**2 ++ y"))