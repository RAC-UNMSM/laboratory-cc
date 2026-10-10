import sympy as sp
from validacion import EntradaError, interval, parse, variable

from tools.common import definite, pack


def run(p):
    v = variable(p["variable"])
    e = parse(p["expresion"], (p["variable"],))
    a, b = interval(p["inferior"], p["superior"])
    op = p["operacion"]
    integrand = {
        "area": lambda: sp.Abs(e),
        "longitud_arco": lambda: sp.sqrt(1 + sp.diff(e, v) ** 2),
        "volumen_revolucion": lambda: sp.pi * e**2,
    }[op]()
    from sympy.calculus.util import continuous_domain

    if (
        sp.Interval.open(a, b).is_subset(continuous_domain(e, v, sp.S.Reals))
        is not True
    ):
        raise EntradaError(
            "La aplicación requiere una función real continua en el intervalo."
        )
    r = definite(integrand, v, a, b)
    return pack(
        r,
        [
            {
                "descripcion": "Plantear e integrar la fórmula geométrica.",
                "entrada_latex": sp.latex(sp.Integral(integrand, (v, a, b))),
                "resultado_latex": sp.latex(r),
            }
        ],
        [
            "Revolución: discos alrededor del eje de la variable, desde la gráfica hasta dicho eje."
        ]
        if op == "volumen_revolucion"
        else [],
    )
