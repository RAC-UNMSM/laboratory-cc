"""Análisis seguro de expresiones matemáticas recibidas por el servidor.

`sympy.sympify` evalúa el texto con `eval`, así que una expresión como
``__import__('os').system(...)`` ejecutaría código. Aquí se parsea con un
espacio de nombres cerrado (solo funciones y constantes matemáticas) y se
rechaza cualquier cosa que no parezca una fórmula.
"""

from __future__ import annotations

import re
from typing import Sequence

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    parse_expr,
    standard_transformations,
)

MAX_LONGITUD = 300

_TRANSFORMACIONES = standard_transformations + (convert_xor,)

_PERMITIDOS = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]+$")
_ATRIBUTO = re.compile(r"\.\s*[A-Za-z_]")
# Un nombre no empieza tras un dígito o punto: así "1e-3" no cuenta como nombre.
_NOMBRE = re.compile(r"(?<![\w.])[A-Za-z_]\w*")

_FUNCIONES = {
    nombre: getattr(sp, nombre)
    for nombre in (
        "sin", "cos", "tan", "cot", "sec", "csc",
        "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
        "exp", "log", "ln", "sqrt", "cbrt", "Abs", "sign",
        "floor", "ceiling", "Min", "Max",
    )
}
# Los literales numéricos se reescriben como Integer(...)/Float(...)/Rational(...).
_CONSTRUCTORES = {n: getattr(sp, n) for n in ("Integer", "Float", "Rational", "Symbol")}
_CONSTANTES = {"pi": sp.pi, "E": sp.E, "e": sp.E, "oo": sp.oo}


class ExpresionInvalida(ValueError):
    """La expresión no es una fórmula matemática aceptable."""


def parsear_expresion(texto: str, variables: Sequence[str]) -> sp.Expr:
    """Convierte `texto` en una expresión de sympy usando solo `variables`."""
    if not isinstance(texto, str) or not texto.strip():
        raise ExpresionInvalida("La expresión no puede estar vacía.")
    if len(texto) > MAX_LONGITUD:
        raise ExpresionInvalida(f"La expresión supera {MAX_LONGITUD} caracteres.")
    if not _PERMITIDOS.match(texto) or "__" in texto or _ATRIBUTO.search(texto):
        raise ExpresionInvalida(f"Expresión no permitida: {texto!r}.")

    simbolos = {v: sp.Symbol(v) for v in variables}
    nombres_libres = set(_NOMBRE.findall(texto))
    desconocidos = nombres_libres - set(simbolos) - set(_FUNCIONES) - set(_CONSTANTES)
    if desconocidos:
        raise ExpresionInvalida(
            f"Nombres no reconocidos en {texto!r}: {sorted(desconocidos)}."
        )

    global_dict = {"__builtins__": {}, **_CONSTRUCTORES, **_FUNCIONES, **_CONSTANTES}
    try:
        expr = parse_expr(
            texto,
            local_dict=simbolos,
            global_dict=global_dict,
            transformations=_TRANSFORMACIONES,
        )
    except Exception as exc:
        raise ExpresionInvalida(f"No se pudo interpretar {texto!r}: {exc}") from exc

    if not isinstance(expr, sp.Expr):
        raise ExpresionInvalida(f"{texto!r} no es una expresión matemática.")
    return expr


def parsear_expresiones(
    textos: Sequence[str], variables: Sequence[str]
) -> list[sp.Expr]:
    return [parsear_expresion(t, variables) for t in textos]

