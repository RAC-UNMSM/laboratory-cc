import sympy as sp
from validacion import EntradaError, interval, variable, vector

from tools.common import definite, iterated, pack


def curl(f):
    x, y, z = [variable(n) for n in ("x", "y", "z")]
    return sp.Matrix(
        [
            sp.diff(f[2], y) - sp.diff(f[1], z),
            sp.diff(f[0], z) - sp.diff(f[2], x),
            sp.diff(f[1], x) - sp.diff(f[0], y),
        ]
    )


def run(p):
    op = p["operacion"]
    size = len(p["campo"])
    names = ("x", "y", "z")[:size]
    f = vector(p["campo"], names)
    vs = [variable(n) for n in names]
    if op in ("divergencia", "gauss"):
        div = sum(sp.diff(c, v) for c, v in zip(f, vs))
        if op == "divergencia":
            return pack(div)
        r, steps = iterated(div, p["limites"], names)
        return pack(
            r,
            steps,
            [
                "Gauss: este es el lado volumétrico. El flujo exterior coincide solo para volumen y campo que satisfacen las hipótesis del teorema; no se verifican automáticamente."
            ],
        )
    if op == "rotacional":
        if size != 3:
            raise EntradaError("Rotacional requiere tres componentes.")
        return pack(curl(f))
    if op == "green":
        x, y = vs
        e = sp.diff(f[1], x) - sp.diff(f[0], y)
        r, steps = iterated(e, p["limites"], names)
        return pack(
            r,
            steps,
            [
                "Green: lado de área. Coincide con circulación de la frontera positiva si se cumplen las hipótesis; no verifica frontera ni regularidad del campo."
            ],
        )
    if op == "integral_linea":
        t = variable("t")
        curve = vector(p["curva"], ("t",), size)
        a, b = interval(p["inferior"], p["superior"])
        substituted = f.subs(dict(zip(vs, curve)), simultaneous=True)
        e = sp.simplify(substituted.dot(curve.diff(t)))
        r = definite(e, t, a, b)
        return pack(
            r,
            [
                {
                    "descripcion": "Sustituir r(t), obtener r'(t) y luego integrar F(r(t)) · r'(t).",
                    "entrada_latex": sp.latex(sp.Integral(e, (t, a, b))),
                    "resultado_latex": sp.latex(r),
                }
            ],
            [
                "La orientación es la de la parametrización para t creciente. Se supone curva regular por tramos."
            ],
        )
    if size != 3:
        raise EntradaError("El flujo de superficie requiere tres componentes.")
    s = vector(p["superficie"], ("u", "v"), 3)
    u, v = variable("u"), variable("v")
    normal = s.diff(u).cross(s.diff(v))
    if normal == sp.zeros(3, 1):
        raise EntradaError("Parametrización degenerada: normal idénticamente nula.")
    if op == "stokes":
        f = curl(f)
    e = sp.simplify(f.subs(dict(zip(vs, s)), simultaneous=True).dot(normal))
    r, steps = iterated(e, p["limites"], ("u", "v"))
    return pack(
        r,
        [
            {
                "descripcion": "Normal orientada r_u × r_v, sin normalizar.",
                "resultado_latex": sp.latex(normal),
            },
            *steps,
        ],
        [
            "Orientación r_u × r_v. Deben comprobarse regularidad por tramos y ausencia de coberturas múltiples."
        ]
        + (
            [
                "Stokes: lado superficial del rotacional; no certifica automáticamente las hipótesis ni la curva frontera."
            ]
            if op == "stokes"
            else []
        ),
    )
