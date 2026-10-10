"""Gramática matemática acotada. Nunca evalúa texto como código Python."""

import ast
import math

import sympy as sp

SYMBOLS = {n: sp.Symbol(n, real=True) for n in ("x", "y", "z", "t", "u", "v")}
FUNCTIONS = {
    n: getattr(sp, n)
    for n in (
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "exp",
        "log",
        "sqrt",
        "Abs",
    )
}
CONSTANTS = {"pi": sp.pi, "E": sp.E}


class EntradaError(ValueError):
    """Entrada fuera del contrato de la herramienta."""


def variable(name):
    if name not in SYMBOLS:
        raise EntradaError("Variable permitida: x, y, z, t, u o v.")
    return SYMBOLS[name]


def parse(text, allowed=tuple(SYMBOLS), infinity=False):
    if not isinstance(text, str) or not text.strip() or len(text) > 512:
        raise EntradaError("Expresión requerida; máximo 512 caracteres.")
    text = text.strip().replace("^", "**")
    try:
        tree = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise EntradaError("Sintaxis inválida. Ejemplo: sin(x) + 2*x**2.") from exc
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise EntradaError("Expresión demasiado compleja (128 nodos).")
    names = {n: variable(n) for n in allowed}
    names.update(CONSTANTS)
    if infinity:
        names["oo"] = sp.oo

    def visit(node, depth=0):
        if depth > 24:
            raise EntradaError("Máximo 24 niveles de anidación.")

        def walk(n):
            return visit(n, depth + 1)

        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if abs(node.value) > 10**12 or not math.isfinite(node.value):
                raise EntradaError("Número fuera del rango permitido.")
            return sp.Rational(str(node.value))
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            a = walk(node.operand)
            return a if isinstance(node.op, ast.UAdd) else -a
        if isinstance(node, ast.BinOp):
            a, b = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                if b == 0:
                    raise EntradaError("División por cero.")
                return a / b
            if isinstance(node.op, ast.Pow):
                if not b.free_symbols and (b.is_real is not True or abs(b) > 100):
                    raise EntradaError("Exponente numérico limitado a [-100,100].")
                if a.is_number and b.is_number and a not in (0, 1, -1):
                    # Prevent nested powers producing huge intermediate integers.
                    if abs(a) > 10**12:
                        raise EntradaError("Base numérica demasiado grande.")
                return sp.Pow(a, b)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in FUNCTIONS
            and len(node.args) == 1
            and not node.keywords
        ):
            return FUNCTIONS[node.func.id](walk(node.args[0]))
        raise EntradaError(
            "Solo números, variables autorizadas, + - * / ** y funciones matemáticas de una entrada."
        )

    result = visit(tree.body)
    if result.has(sp.zoo, sp.nan) or (not infinity and result.has(sp.oo, -sp.oo)):
        raise EntradaError("Expresión indefinida o no finita.")
    return result


def scalar(text, infinity=False):
    value = parse(text, (), infinity)
    if value not in (sp.oo, -sp.oo) and value.is_real is not True:
        raise EntradaError("Se requiere un número real.")
    return value


def vector(texts, names, size=None):
    if size is not None and len(texts) != size:
        raise EntradaError(f"Se requieren {size} componentes.")
    return sp.Matrix([parse(t, names) for t in texts])


def interval(a, b):
    a, b = scalar(a, True), scalar(b, True)
    if a == b:
        return a, b
    if (b - a).is_positive is not True:
        raise EntradaError("Se requiere límite inferior menor o igual al superior.")
    return a, b


def original_domain(text, variable_name):
    """Intersección de dominios de subexpresiones, antes de cancelaciones."""
    from sympy.calculus.util import continuous_domain

    v = variable(variable_name)
    tree = ast.parse(text.strip().replace("^", "**"), mode="eval")
    domain = sp.S.Reals
    for node in ast.walk(tree):
        if not isinstance(node, (ast.BinOp, ast.Call, ast.UnaryOp)):
            continue
        sub = parse(ast.unparse(node))
        domain = domain.intersect(continuous_domain(sub, v, sp.S.Reals))
        denominator = None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            denominator = parse(ast.unparse(node.right))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
            power = parse(ast.unparse(node.right))
            if power.is_negative is True:
                denominator = parse(ast.unparse(node.left))
        if denominator is not None:
            domain = domain - sp.solveset(denominator, v, domain=sp.S.Reals)
    return domain


def defined_at(text, variable_name, point):
    try:
        return original_domain(text, variable_name).contains(point) == sp.true
    except NotImplementedError:
        return False
