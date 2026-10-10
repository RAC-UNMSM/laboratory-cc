"""Validación y preparación de parámetros de entrada.

Las funciones matemáticas llegan como texto (por ejemplo ``"sin(x)*exp(-x^2)"``).
Se analizan con ``ast`` y solo se permite una lista blanca de nodos, funciones y
constantes, de modo que nunca se ejecuta código arbitrario.
"""
from __future__ import annotations

import ast
import math
from typing import Callable, Sequence

import numpy as np


class ErrorValidacion(ValueError):
    """Entrada inválida (mensaje pensado para mostrarse al usuario)."""


_FUNCIONES = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan,
    "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh,
    "exp": np.exp, "log": np.log, "ln": np.log,
    "log10": np.log10, "log2": np.log2,
    "sqrt": np.sqrt, "abs": np.abs,
}
_CONSTANTES = {"pi": math.pi, "e": math.e}
_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_UNOPS = (ast.UAdd, ast.USub)
MAX_LONGITUD = 200


def _chequear(nodo: ast.AST, nombres: set[str]) -> None:
    if isinstance(nodo, ast.Expression):
        _chequear(nodo.body, nombres)
    elif isinstance(nodo, ast.BinOp):
        if not isinstance(nodo.op, _BINOPS):
            raise ErrorValidacion("Operador no permitido (use + - * / ^).")
        _chequear(nodo.left, nombres)
        _chequear(nodo.right, nombres)
    elif isinstance(nodo, ast.UnaryOp):
        if not isinstance(nodo.op, _UNOPS):
            raise ErrorValidacion("Operador unario no permitido.")
        _chequear(nodo.operand, nombres)
    elif isinstance(nodo, ast.Call):
        if (not isinstance(nodo.func, ast.Name) or nodo.func.id not in _FUNCIONES
                or nodo.keywords or len(nodo.args) != 1):
            raise ErrorValidacion(
                "Solo se permiten funciones de un argumento: " + ", ".join(sorted(_FUNCIONES)) + ".")
        _chequear(nodo.args[0], nombres)
    elif isinstance(nodo, ast.Name):
        if nodo.id not in nombres:
            raise ErrorValidacion(
                f"Nombre no permitido: '{nodo.id}'. Variables/constantes válidas: {sorted(nombres)}.")
    elif isinstance(nodo, ast.Constant):
        if isinstance(nodo.value, bool) or not isinstance(nodo.value, (int, float)):
            raise ErrorValidacion("Solo se permiten constantes numéricas.")
    else:
        raise ErrorValidacion(f"Construcción no permitida en la expresión: {type(nodo).__name__}.")


class _ConstAFloat(ast.NodeTransformer):
    """Convierte enteros a float (evita potencias enteras gigantes tipo 9**9**9)."""

    def visit_Constant(self, nodo: ast.Constant) -> ast.AST:
        return ast.copy_location(ast.Constant(float(nodo.value)), nodo)


def compilar_funcion(expresion: str, variables: Sequence[str] = ("x",)) -> Callable[..., float]:
    """Compila ``expresion`` a un callable ``f(*variables)`` seguro."""
    if not isinstance(expresion, str) or not expresion.strip():
        raise ErrorValidacion("La expresión está vacía.")
    if len(expresion) > MAX_LONGITUD:
        raise ErrorValidacion(f"La expresión supera {MAX_LONGITUD} caracteres.")
    for v in variables:
        if not v.isidentifier():
            raise ErrorValidacion(f"Nombre de variable inválido: '{v}'.")
    fuente = expresion.strip().replace("^", "**")
    try:
        arbol = ast.parse(fuente, mode="eval")
    except SyntaxError as exc:
        raise ErrorValidacion(
            f"Expresión mal formada: '{expresion}'. Use '*' explícito (2*x) y '^' o '**' para potencias."
        ) from exc
    _chequear(arbol, set(_CONSTANTES) | set(variables))
    arbol = ast.fix_missing_locations(_ConstAFloat().visit(arbol))
    codigo = compile(arbol, "<expresion>", "eval")
    base = {**_FUNCIONES, **_CONSTANTES}
    glob = {"__builtins__": {}}
    nvars = len(variables)

    def f(*args):
        if len(args) != nvars:
            raise TypeError(f"Se esperaban {nvars} argumentos ({', '.join(variables)}).")
        ns = dict(base)
        ns.update(zip(variables, args))
        return eval(codigo, glob, ns)  # noqa: S307 - árbol validado por lista blanca

    f.expresion = expresion  # type: ignore[attr-defined]
    return f


def envolver_finita(f: Callable[..., float]) -> Callable[..., float]:
    """Devuelve ``g`` que fuerza float y falla con mensaje claro si el valor no es finito."""
    def g(*args) -> float:
        try:
            v = float(f(*args))
        except (ArithmeticError, ValueError, TypeError) as exc:
            raise ErrorValidacion(f"No se pudo evaluar la función en {args}: {exc}") from exc
        if not math.isfinite(v):
            raise ErrorValidacion(f"La función no es finita en {args} (resultado {v}).")
        return v
    return g


def validar_real(valor, nombre: str) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion(f"'{nombre}' debe ser un número real.") from exc
    if not math.isfinite(v):
        raise ErrorValidacion(f"'{nombre}' debe ser finito.")
    return v


def validar_tolerancia(tol, nombre: str = "tolerancia") -> float:
    v = validar_real(tol, nombre)
    if not 0.0 < v < 1.0:
        raise ErrorValidacion(f"'{nombre}' debe estar en (0, 1), por ejemplo 1e-8.")
    return v


def validar_paso(h, nombre: str = "h") -> float:
    v = validar_real(h, nombre)
    if v <= 0.0:
        raise ErrorValidacion(f"'{nombre}' debe ser positivo.")
    return v


def validar_entero(n, nombre: str, minimo: int, maximo: int) -> int:
    try:
        v = int(n)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion(f"'{nombre}' debe ser un entero.") from exc
    if not minimo <= v <= maximo:
        raise ErrorValidacion(f"'{nombre}' debe estar entre {minimo} y {maximo}.")
    return v


def validar_intervalo(a, b) -> tuple[float, float]:
    a, b = validar_real(a, "a"), validar_real(b, "b")
    if a == b:
        raise ErrorValidacion("El intervalo es degenerado (a == b).")
    return a, b
