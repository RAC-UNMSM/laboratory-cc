"""Lógica matemática: rol "Lógica matemática" del pilotaje MCP.

Todo acá es sympy/numpy puro -- sin I/O, sin red -- para que quien tenga
este rol pueda probarlo con un test normal, sin levantar el servidor
completo ni depender de los otros módulos.
"""

import numpy as np
import sympy as sp

# Símbolo matemático "x" -- se define una sola vez acá porque toda la
# matemática del servidor (derivar, evaluar, y la validación de que la
# expresión sea de una sola variable) gira en torno a él.
x = sp.symbols("x")


class EvaluationError(Exception):
    """La función no se pudo evaluar numéricamente en el rango pedido."""


def derivar_simbolico(f: sp.Expr) -> sp.Expr:
    """Derivada EXACTA (simbólica), no una aproximación numérica -- por eso
    vale la pena tener esto en un MCP: es un resultado garantizado-correcto,
    no algo que la IA "calculó a ojo"."""
    return sp.diff(f, x)


def evaluar_numerico(
    f: sp.Expr, derivada: sp.Expr, x_min: float, x_max: float, n: int = 400
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """sp.lambdify() convierte la expresión simbólica en una función Python
    normal (evaluable con arrays de numpy) -- sympy es para el resultado
    exacto, numpy es para graficar rápido sobre muchos puntos a la vez."""
    try:
        f_num = sp.lambdify(x, f, "numpy")
        df_num = sp.lambdify(x, derivada, "numpy")
        xs = np.linspace(x_min, x_max, n)
        ys = np.asarray(f_num(xs), dtype=float)
        dys = np.asarray(df_num(xs), dtype=float)
    except Exception as exc:
        # Ej: la función tiene una operación inválida para ciertos valores
        # (raíz de negativo, etc.) que numpy no puede evaluar en el rango.
        raise EvaluationError(
            f"Error: la función no se pudo evaluar en [{x_min}, {x_max}]: {exc}"
        ) from exc
    return xs, ys, dys
