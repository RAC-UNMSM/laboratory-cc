import pytest
import sympy as sp

from expresiones import ExpresionInvalida, parsear_expresion
from server import _ejecutar_metodo


def test_parsea_formulas_normales():
    x, y = sp.symbols("x y")
    assert parsear_expresion("x**2 + y**2 - 1", ["x", "y"]) == x**2 + y**2 - 1
    assert parsear_expresion("x^2 - y", ["x", "y"]) == x**2 - y
    assert parsear_expresion("sin(x) + exp(y)", ["x", "y"]) == sp.sin(x) + sp.exp(y)
    assert parsear_expresion("pi*x - 1e-3", ["x"]) == sp.pi * x - sp.Float("1e-3")


@pytest.mark.parametrize(
    "texto",
    [
        "__import__('os').system('id')",
        "().__class__.__bases__",
        "x.__class__",
        "open('/etc/passwd')",
        "x; y",
        "lambda: 1",
        "x + z",
        "",
        "   ",
        "x" * 400,
    ],
)
def test_rechaza_expresiones_peligrosas_o_invalidas(texto):
    with pytest.raises(ExpresionInvalida):
        parsear_expresion(texto, ["x", "y"])


def test_server_no_ejecuta_codigo(tmp_path):
    marca = tmp_path / "pwned"
    res = _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        expresiones=[f"__import__('pathlib').Path(r'{marca}').touch()"],
        variables=["x"],
        x0=[1.0],
        tolerancia=1e-8,
        max_iter=10,
    )
    assert res["status"] == "invalid_input"
    assert not marca.exists()


def test_transporte_por_defecto_es_http():
    import server

    assert server.TRANSPORTE == "streamable-http"
    assert server.mcp.settings.port == 8000
    assert server.mcp.settings.host == "0.0.0.0"
