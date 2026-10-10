import sympy as sp
from validacion import EntradaError, parse, scalar, variable

from tools.common import pack


def run(p):
    v = variable(p["variable"])
    e = parse(p["expresion"], (p["variable"],))
    a = scalar(p["punto"], True)
    if p["operacion"] == "limite" and (
        p["direccion"] != "ambos" or a in (sp.oo, -sp.oo)
    ):
        direction = p["direccion"] if p["direccion"] != "ambos" else "+"
        r = sp.limit(e, v, a, dir=direction)
        return pack(
            r,
            [
                {
                    "descripcion": "Evaluar el límite indicado.",
                    "resultado_latex": sp.latex(r),
                }
            ],
        )
    if p["operacion"] == "continuidad" and a in (sp.oo, -sp.oo):
        raise EntradaError("La continuidad puntual requiere un punto finito.")
    left, right = sp.limit(e, v, a, dir="-"), sp.limit(e, v, a, dir="+")
    same = sp.simplify(left - right) == 0 or left == right
    steps = [
        {"descripcion": "Límite lateral izquierdo.", "resultado_latex": sp.latex(left)},
        {"descripcion": "Límite lateral derecho.", "resultado_latex": sp.latex(right)},
    ]
    if p["operacion"] == "limite":
        if same:
            return pack(left, steps)
        return {
            "estado": "no_existe",
            "exacto": None,
            "latex": None,
            "decimal": None,
            "pasos": steps,
            "observaciones": ["Los límites laterales difieren."],
        }
    # Domain check uses the original expression before SymPy cancellation below.
    from sympy.calculus.util import continuous_domain

    domain = continuous_domain(e, v, sp.S.Reals)
    val = e.subs(v, a)
    from validacion import defined_at

    ok = (
        defined_at(p["expresion"], p["variable"], a)
        and same
        and left.is_finite is True
        and domain.contains(a) == sp.true
        and sp.simplify(val - left) == 0
    )
    result = pack(
        val,
        steps,
        [
            "Se conservan exclusiones de denominadores de la expresión ingresada; declarar aparte otras restricciones del enunciado."
        ],
    )
    result["continua"] = bool(ok)
    return result
