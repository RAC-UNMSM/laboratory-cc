import sympy as sp
from validacion import EntradaError, interval, parse, variable

from tools.common import pack


def run(p):
    v = variable(p["variable"])
    e = parse(p["expresion"], (p["variable"],))
    steps = []
    if p["operacion"] == "derivada":
        r = e
        for n in range(p["orden"]):
            r = sp.diff(r, v)
            steps.append(
                {
                    "descripcion": f"Derivada de orden {n + 1}.",
                    "resultado_latex": sp.latex(r),
                }
            )
        return pack(r, steps)
    a, b = interval(p["inferior"], p["superior"])
    if not e.is_polynomial(v) or a in (-sp.oo, sp.oo) or b in (-sp.oo, sp.oo):
        raise EntradaError("Extremos globales: polinomio en intervalo cerrado finito.")
    derivative = sp.diff(e, v)
    if derivative == 0:
        candidates = [a, b]
    else:
        roots = sp.solveset(derivative, v, domain=sp.Interval(a, b))
        if not isinstance(roots, sp.FiniteSet) and roots != sp.S.EmptySet:
            raise EntradaError("No se aislaron todos los puntos críticos.")
        candidates = list(dict.fromkeys([a, b, *roots]))
    values = [(c, sp.simplify(e.subs(v, c))) for c in candidates]
    out = pack(
        sp.Tuple(*[sp.Tuple(*pair) for pair in values]),
        notes=[
            "Se incluyen extremos del intervalo; si la función es constante, todos sus puntos son extremos."
        ],
    )
    out["minimo"] = str(sp.Min(*[val for _, val in values]))
    out["maximo"] = str(sp.Max(*[val for _, val in values]))
    out["pasos"] = [
        {
            "descripcion": "Derivar, resolver f'(x)=0 y evaluar candidatos y extremos.",
            "resultado_latex": sp.latex(derivative),
        }
    ]
    return out
