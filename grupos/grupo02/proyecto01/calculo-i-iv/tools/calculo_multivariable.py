import sympy as sp
from validacion import EntradaError, parse, scalar

from tools.common import pack, unique


def run(p):
    vs = unique(p["variables"])
    e = parse(p["expresion"], p["variables"])
    g = sp.Matrix([sp.diff(e, v) for v in vs])
    op = p["operacion"]
    if op == "gradiente":
        return pack(
            g,
            [
                {
                    "descripcion": "Derivar parcialmente en el orden declarado.",
                    "resultado_latex": sp.latex(g),
                }
            ],
        )
    if op == "hessiano":
        return pack(
            sp.hessian(e, vs), notes=["Las variables siguen el orden solicitado."]
        )
    if op == "direccional":
        if len(p["punto"]) != len(vs) or len(p["direccion"]) != len(vs):
            raise EntradaError(
                "Punto y dirección deben tener la misma dimensión que las variables."
            )
        point = [scalar(t) for t in p["punto"]]
        d = sp.Matrix([scalar(t) for t in p["direccion"]])
        norm = sp.sqrt(d.dot(d))
        if norm == 0:
            raise EntradaError("La dirección no puede ser nula.")
        r = sp.simplify(g.subs(dict(zip(vs, point)), simultaneous=True).dot(d / norm))
        return pack(
            r,
            [
                {
                    "descripcion": "Normalizar la dirección y calcular gradiente(punto) · dirección unitaria.",
                    "resultado_latex": sp.latex(r),
                }
            ],
            [
                "Fórmula válida si la función es diferenciable en el punto; no certifica esa hipótesis."
            ],
        )
    c = parse(p["restriccion"], p["variables"])
    if not e.is_polynomial(*vs) or not c.is_polynomial(*vs):
        raise EntradaError("Lagrange admite polinomios; restricción g=0.")
    lam = sp.Symbol("lambda", real=True)
    eq = [sp.diff(e, v) - lam * sp.diff(c, v) for v in vs] + [c]
    solutions = sp.solve(eq, [*vs, lam], dict=True)
    candidates = []
    for sol in solutions:
        if all(
            v in sol and not sol[v].free_symbols and sol[v].is_real is True for v in vs
        ):
            candidates.append(
                {str(v): str(sol[v]) for v in vs}
                | {"valor": str(sp.simplify(e.subs(sol)))}
            )
    return {
        "estado": "candidatos",
        "candidatos": candidates,
        "pasos": [
            {
                "descripcion": "Resolver grad(f)=lambda grad(g), g=0.",
                "entrada_latex": sp.latex(sp.Tuple(*eq)),
            }
        ],
        "observaciones": [
            "No certifica extremos globales ni exhaustividad. Revisar puntos singulares de g, regularidad, compacidad y clasificar candidatos."
        ],
    }
