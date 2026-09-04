"""Validación de entradas: rol "Validación de entradas" del pilotaje MCP.

Nadie más debería tener que revisar sympy acá -- solo confirmar que lo que
mandó el usuario tiene sentido antes de que matematica.py lo procese.
"""

import sympy as sp

from matematica import x


class ValidationError(Exception):
    """Entrada inválida -- el mensaje ya viene listo para devolver al usuario."""


def validar_rango(x_min: float, x_max: float) -> None:
    if x_min >= x_max:
        raise ValidationError(f"Error: x_min ({x_min}) debe ser menor que x_max ({x_max}).")


def parsear_expresion(expresion: str) -> sp.Expr:
    """Convierte el texto en una expresión sympy real, validando que sea de
    una sola variable ('x'). Lanza ValidationError con un mensaje legible si
    no se pudo interpretar o si trae otras variables."""
    # sp.sympify() interpreta el string como matemática simbólica; si el
    # texto no tiene sentido matemático, lanza una excepción que atajamos
    # acá para devolver un mensaje de error legible en vez de que el
    # servidor se caiga.
    try:
        f = sp.sympify(expresion)
    except (sp.SympifyError, TypeError, SyntaxError) as exc:
        raise ValidationError(
            f"Error: no se pudo interpretar '{expresion}' como una función de x. "
            f"Usa sintaxis de Python/sympy (ej. 'x**2 + 3*x', 'sin(x)'). Detalle: {exc}"
        ) from exc

    # Esta tool solo maneja funciones de UNA variable ("x"). Si la expresión
    # trae otras letras (ej. "y", "z"), no tiene sentido derivar respecto a
    # "x" solamente -- se avisa en vez de dar un resultado engañoso.
    variables_libres = f.free_symbols - {x}
    if variables_libres:
        raise ValidationError(
            f"Error: la expresión usa variables además de 'x': {variables_libres}. "
            "Esta tool solo deriva funciones de una variable."
        )
    return f
