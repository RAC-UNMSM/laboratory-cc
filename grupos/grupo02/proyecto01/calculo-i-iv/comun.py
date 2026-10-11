"""Lectura segura de expresiones: unico punto por el que entra texto del cliente.

Construye la expresion nodo por nodo con una lista blanca. No usa eval,
sympify ni parse_expr sobre texto.
"""
from __future__ import annotations

import ast

import sympy as sp

FUNCIONES = {n: getattr(sp, n) for n in (
    'sin', 'cos', 'tan', 'sec', 'csc', 'cot', 'asin', 'acos', 'atan',
    'sinh', 'cosh', 'tanh', 'exp', 'log', 'Abs', 'gamma')}
CONSTANTES = {'pi': sp.pi, 'E': sp.E, 'oo': sp.oo}
MAX_LONGITUD = 500
MAX_NODOS = 120


def simbolo(nombre, real=True):
    if (not isinstance(nombre, str) or not nombre.isidentifier()
            or nombre.startswith('_') or nombre in FUNCIONES
            or nombre in CONSTANTES or nombre in ('sqrt', 'beta') or len(nombre) > 24):
        raise ValueError('Nombre de variable inválido o reservado.')
    return sp.Symbol(nombre, real=True) if real else sp.Symbol(nombre)


def _arbol(texto):
    if not isinstance(texto, str) or not texto.strip() or len(texto) > MAX_LONGITUD:
        raise ValueError(f'La expresión debe tener entre 1 y {MAX_LONGITUD} caracteres.')
    try:
        arbol = ast.parse(texto.strip().replace('^', '**'), mode='eval')
    except (SyntaxError, RecursionError, MemoryError) as exc:
        raise ValueError('Expresión mal escrita: use sintaxis tipo x**2, sin(x), sqrt(x).') from exc
    if sum(1 for _ in ast.walk(arbol)) > MAX_NODOS:
        raise ValueError('Expresión demasiado compleja.')
    return arbol.body


def _visitar(n, nombres):
    if isinstance(n, ast.Constant) and type(n.value) in (int, float):
        valor = sp.Rational(str(n.value))
        if abs(valor) > 1000000:
            raise ValueError('Constante numérica fuera del límite permitido.')
        return valor
    if isinstance(n, ast.Name):
        if n.id in nombres:
            return nombres[n.id]
        if n.id in CONSTANTES:
            return CONSTANTES[n.id]
        raise ValueError(f'Símbolo no permitido: {n.id}.')
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
        v = _visitar(n.operand, nombres)
        return v if isinstance(n.op, ast.UAdd) else -v
    if isinstance(n, ast.BinOp):
        a, b = _visitar(n.left, nombres), _visitar(n.right, nombres)
        if isinstance(n.op, ast.Add):
            return a + b
        if isinstance(n.op, ast.Sub):
            return a - b
        if isinstance(n.op, ast.Mult):
            return a * b
        if isinstance(n.op, ast.Div):
            if b == 0:
                raise ValueError('División entre cero.')
            return a / b
        if isinstance(n.op, ast.Pow):
            if b.is_number and (b.is_finite is not True or abs(b) > 100):
                raise ValueError('Exponente numérico fuera de [-100, 100].')
            return a ** b
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and not n.keywords:
        args = [_visitar(a, nombres) for a in n.args]
        if n.func.id == 'sqrt' and len(args) == 1:
            return sp.sqrt(args[0])
        if n.func.id == 'beta' and len(args) == 2:
            return sp.beta(*args)
        if n.func.id in FUNCIONES and len(args) == 1:
            return FUNCIONES[n.func.id](args[0])
    raise ValueError('Sintaxis no admitida: use solo operaciones y funciones documentadas.')


def parsear(texto, variables=()):
    """Texto -> expresión de SymPy. `variables` son los símbolos permitidos."""
    return _visitar(_arbol(texto), {str(v): v for v in variables})


def parsear_vector(texto, variables=(), tamanos=(2, 3)):
    """'[a, b, c]' o '(a, b, c)' -> sp.Matrix columna."""
    cuerpo = _arbol(texto)
    if not isinstance(cuerpo, (ast.List, ast.Tuple)) or len(cuerpo.elts) not in tamanos:
        raise ValueError(f'El vector debe escribirse como [a, b, c] con {" o ".join(map(str, tamanos))} componentes.')
    nombres = {str(v): v for v in variables}
    return sp.Matrix([_visitar(e, nombres) for e in cuerpo.elts])
