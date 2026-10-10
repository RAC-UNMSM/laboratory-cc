import sympy as sp
from validacion import EntradaError, parse, scalar, variable

from tools.common import definite, pack


def run(p):
    v = variable(p["variable"])
    e = parse(p["expresion"], (p["variable"],))
    a, b = p["inferior"], p["superior"]
    if (a is None) != (b is None):
        raise EntradaError("Indique ambos límites o ninguno.")
    if a is None:
        r = sp.integrate(e, v)
        out = pack(
            r,
            [
                {
                    "descripcion": "Obtener una primitiva; añadir la constante arbitraria C.",
                    "resultado_latex": sp.latex(r),
                }
            ],
            [
                "Primitiva formal F + C. Verifique la rama y el intervalo donde F es real y derivable; no se certifica todo el dominio original."
            ],
        )
        out["constante_integracion"] = "C"
        if not r.has(sp.Integral):
            out["verificacion"] = str(sp.simplify(sp.diff(r, v) - e))
        return out
    a, b = scalar(a, True), scalar(b, True)
    r = definite(e, v, a, b)
    return pack(
        r,
        [
            {
                "descripcion": "Integral definida (con separación de singularidades interiores).",
                "entrada_latex": sp.latex(sp.Integral(e, (v, a, b))),
                "resultado_latex": sp.latex(r),
            }
        ],
        ["Una integral con signo no equivale siempre a un área geométrica."],
    )
