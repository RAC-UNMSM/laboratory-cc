import pytest
from engine import solve
from validacion import EntradaError


def calc(op, **kwargs):
    return solve({"problema": {"operacion": op, **kwargs}, "modo": "paso_a_paso"})


def bounds(*rows):
    return [dict(variable=v, inferior=a, superior=b) for v, a, b in rows]


@pytest.mark.parametrize(
    "op,args,expected",
    [
        ("limite", dict(expresion="sin(x)/x", punto="0"), "1"),
        ("limite", dict(expresion="1/x", punto="0", direccion="+"), "oo"),
        ("limite", dict(expresion="1/x", punto="oo"), "0"),
        ("derivada", dict(expresion="sin(x**2)"), "2*x*cos(x**2)"),
        ("derivada", dict(expresion="x**5", orden=3), "60*x**2"),
        ("integral", dict(expresion="x**2", inferior="0", superior="3"), "9"),
        ("integral", dict(expresion="sin(x)", inferior="0", superior="pi"), "2"),
        ("integral", dict(expresion="x", inferior="2", superior="0"), "-2"),
        ("integral", dict(expresion="x", inferior="1", superior="1"), "0"),
        ("integral", dict(expresion="exp(-x)", inferior="0", superior="oo"), "1"),
        ("integral", dict(expresion="1/sqrt(x)", inferior="0", superior="1"), "2"),
        ("area", dict(expresion="x", inferior="-1", superior="1"), "1"),
        ("longitud_arco", dict(expresion="x", inferior="0", superior="1"), "sqrt(2)"),
        ("volumen_revolucion", dict(expresion="x", inferior="0", superior="1"), "pi/3"),
        (
            "gradiente",
            dict(expresion="x**2+y**2", variables=["x", "y"]),
            "Matrix([[2*x], [2*y]])",
        ),
        (
            "hessiano",
            dict(expresion="x**2+x*y+y**2", variables=["x", "y"]),
            "Matrix([[2, 1], [1, 2]])",
        ),
        (
            "direccional",
            dict(
                expresion="x**2+y**2",
                variables=["x", "y"],
                punto=["1", "2"],
                direccion=["3", "4"],
            ),
            "22/5",
        ),
        (
            "integral_multiple",
            dict(expresion="1", limites=bounds(("y", "0", "x"), ("x", "0", "1"))),
            "1/2",
        ),
        (
            "integral_multiple",
            dict(expresion="1", limites=bounds(("x", "0", "y"), ("y", "0", "1"))),
            "1/2",
        ),
        (
            "integral_multiple",
            dict(
                expresion="1",
                limites=bounds(("z", "0", "1-x-y"), ("y", "0", "1-x"), ("x", "0", "1")),
            ),
            "1/6",
        ),
        ("divergencia", dict(campo=["x", "y", "z"]), "3"),
        ("rotacional", dict(campo=["-y", "x", "0"]), "Matrix([[0], [0], [2]])"),
        (
            "integral_linea",
            dict(
                campo=["-y", "x"],
                curva=["cos(t)", "sin(t)"],
                inferior="0",
                superior="2*pi",
            ),
            "2*pi",
        ),
        (
            "integral_linea",
            dict(
                campo=["-y", "x"],
                curva=["cos(t)", "-sin(t)"],
                inferior="0",
                superior="2*pi",
            ),
            "-2*pi",
        ),
        (
            "flujo_superficie",
            dict(
                campo=["0", "0", "1"],
                superficie=["u", "v", "0"],
                limites=bounds(("u", "0", "1"), ("v", "0", "1")),
            ),
            "1",
        ),
        (
            "flujo_superficie",
            dict(
                campo=["0", "0", "1"],
                superficie=["v", "u", "0"],
                limites=bounds(("u", "0", "1"), ("v", "0", "1")),
            ),
            "-1",
        ),
        (
            "green",
            dict(
                campo=["-y/2", "x/2"], limites=bounds(("y", "0", "1"), ("x", "0", "1"))
            ),
            "1",
        ),
        (
            "stokes",
            dict(
                campo=["-y/2", "x/2", "0"],
                superficie=["u", "v", "0"],
                limites=bounds(("u", "0", "1"), ("v", "0", "1")),
            ),
            "1",
        ),
        (
            "gauss",
            dict(
                campo=["x", "y", "z"],
                limites=bounds(("z", "0", "1"), ("y", "0", "1"), ("x", "0", "1")),
            ),
            "3",
        ),
    ],
)
def test_exact(op, args, expected):
    assert calc(op, **args)["exacto"] == expected


@pytest.mark.parametrize(
    "expr,point,expected",
    [
        ("x**2", "0", True),
        ("1/x", "0", False),
        ("x/x", "0", False),
        ("(x**2-1)/(x-1)", "1", False),
    ],
)
def test_continuity(expr, point, expected):
    assert calc("continuidad", expresion=expr, punto=point)["continua"] is expected


def test_two_sided():
    assert calc("limite", expresion="1/x", punto="0")["estado"] == "no_existe"


def test_extrema():
    r = calc("extremos", expresion="x**2", inferior="-1", superior="2")
    assert r["minimo"] == "0" and r["maximo"] == "4"


def test_constant_extrema():
    assert calc("extremos", expresion="3", inferior="-1", superior="2")["minimo"] == "3"


def test_lagrange():
    r = calc(
        "lagrange", expresion="x+y", variables=["x", "y"], restriccion="x**2+y**2-1"
    )
    assert {p["valor"] for p in r["candidatos"]} == {"sqrt(2)", "-sqrt(2)"}


def test_antiderivative():
    r = calc("integral", expresion="2*x")
    assert r["verificacion"] == "0" and r["constante_integracion"] == "C"


@pytest.mark.parametrize(
    "op,args",
    [
        ("integral", dict(expresion="1/x", inferior="-1", superior="1")),
        ("integral", dict(expresion="x", inferior="0")),
        ("integral", dict(expresion="sqrt(x)", inferior="-1", superior="1")),
        (
            "direccional",
            dict(
                expresion="x+y",
                variables=["x", "y"],
                punto=["0", "0"],
                direccion=["0", "0"],
            ),
        ),
        ("gradiente", dict(expresion="x", variables=["x", "x"])),
        (
            "integral_multiple",
            dict(expresion="x+y", limites=bounds(("y", "0", "y"), ("x", "0", "1"))),
        ),
        (
            "integral_linea",
            dict(campo=["x", "y"], curva=["t", "t", "t"], inferior="0", superior="1"),
        ),
        (
            "flujo_superficie",
            dict(
                campo=["x", "y", "z"],
                superficie=["u", "u", "0"],
                limites=bounds(("u", "0", "1"), ("v", "0", "1")),
            ),
        ),
        ("rotacional", dict(campo=["x", "y"])),
    ],
)
def test_invalid_math(op, args):
    with pytest.raises(EntradaError):
        calc(op, **args)


def test_area_complex_domain_rejected():
    with pytest.raises(EntradaError):
        calc("area", expresion="sqrt(x)", inferior="-1", superior="0")


def test_complex_inner_bound_rejected():
    with pytest.raises(EntradaError):
        calc(
            "integral_multiple",
            expresion="1",
            limites=bounds(("y", "0", "sqrt(-1)"), ("x", "0", "1")),
        )


def test_oscillatory_limit():
    assert calc("limite", expresion="sin(x)", punto="oo")["estado"] == "no_existe"
