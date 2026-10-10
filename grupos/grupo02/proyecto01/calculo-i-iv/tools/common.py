"""Formato de resultados y operaciones matemáticas compartidas."""

import sympy as sp
from sympy.calculus.util import continuous_domain
from validacion import EntradaError, parse, scalar, variable


def pack(value, steps=(), notes=()):
    if isinstance(value, sp.Basic) and value.has(sp.AccumBounds):
        return {
            "estado": "no_existe",
            "exacto": None,
            "latex": None,
            "decimal": None,
            "pasos": list(steps),
            "observaciones": [*notes, "Resultado oscilatorio sin límite único."],
        }
    unresolved = isinstance(value, sp.Basic) and value.has(
        sp.Integral, sp.Limit, sp.Derivative, sp.ConditionSet
    )
    invalid = isinstance(value, sp.Basic) and value.has(sp.nan, sp.zoo)
    infinite = isinstance(value, sp.Basic) and value.has(sp.oo, -sp.oo)
    status = (
        "no_resuelto"
        if unresolved
        else "indefinido"
        if invalid
        else "no_finito"
        if infinite
        else "calculado"
    )
    decimal = None
    if (
        status == "calculado"
        and isinstance(value, sp.Expr)
        and not value.free_symbols
        and value.is_real is True
    ):
        decimal = str(sp.N(value, 12))
    return {
        "estado": status,
        "exacto": str(value),
        "latex": sp.latex(value),
        "decimal": decimal,
        "pasos": list(steps),
        "observaciones": list(notes),
    }


def unique(names):
    if len(set(names)) != len(names):
        raise EntradaError("No repita variables.")
    return [variable(v) for v in names]


def definite(expr, v, a, b):
    """Separar singularidades evita interpretar una integral impropia como VP."""
    if a == b:
        return sp.S.Zero
    sign = 1
    if not a.free_symbols and not b.free_symbols and (a - b).is_positive:
        a, b, sign = b, a, -1
    if a.free_symbols or b.free_symbols:
        return sp.integrate(expr, (v, a, b))
    domain = continuous_domain(expr, v, sp.S.Reals)
    region = sp.Interval.open(a, b)
    missing = region - domain
    if missing is sp.S.EmptySet or missing.is_empty is True:
        return sign * sp.integrate(expr, (v, a, b))
    if not isinstance(missing, sp.FiniteSet):
        raise EntradaError(
            "No se ha certificado un dominio real continuo por tramos en este intervalo."
        )
    points = [a] + sorted(missing, key=lambda p: float(p)) + [b]
    parts = [
        sp.integrate(expr, (v, lower, upper))
        for lower, upper in zip(points, points[1:])
    ]
    if any(p.has(sp.oo, -sp.oo, sp.zoo, sp.nan) for p in parts):
        raise EntradaError(
            "Integral impropia divergente; no se calcula valor principal de Cauchy."
        )
    return sign * sum(parts, sp.S.Zero)


def iterated(expr, bounds, names=None):
    order = [b["variable"] for b in bounds]
    unique(order)
    if names is not None and set(order) != set(names):
        raise EntradaError("Variables de integración incompatibles con el dominio.")
    result = expr
    steps = []
    for i, b in enumerate(bounds):
        outer = order[i + 1 :]
        a = parse(b["inferior"], outer, True)
        c = parse(b["superior"], outer, True)
        if not outer:
            scalar(b["inferior"], True)
            scalar(b["superior"], True)
        for bound in (a, c):
            if (
                not bound.free_symbols
                and bound not in (sp.oo, -sp.oo)
                and bound.is_real is not True
            ):
                raise EntradaError("Los límites numéricos deben ser reales.")
        v = variable(b["variable"])
        integral = sp.Integral(result, (v, a, c))
        result = definite(result, v, a, c)
        steps.append(
            {
                "descripcion": f"Integrar respecto de {v} (orden de dentro hacia fuera).",
                "entrada_latex": sp.latex(integral),
                "resultado_latex": sp.latex(result),
            }
        )
    return result, steps
