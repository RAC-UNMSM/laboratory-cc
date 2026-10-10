import pytest
import sympy as sp
from validacion import EntradaError, parse


@pytest.mark.parametrize(
    "value",
    [
        '__import__("os").system("id")',
        "x.__class__",
        "[x][0]",
        "lambda: 1",
        'open("a")',
        "[x for x in (1,2)]",
        "sin(x, y)",
        "f(x)",
        "x;1",
        "True",
        "None",
        "1e999",
        "10**10000",
        "10**(10**100)",
        "y",
        "x" * 513,
        "1/0",
        "sin(x=1)",
        "2x",
    ],
)
def test_rejected(value):
    with pytest.raises((EntradaError, OverflowError)):
        parse(value, ("x",))


def test_exact_decimals():
    assert parse("0.1+0.2", ()) == sp.Rational(3, 10)


def test_caret():
    assert str(parse("x^2")) == "x**2"


def test_no_builtin_execution(tmp_path):
    target = tmp_path / "owned"
    with pytest.raises(EntradaError):
        parse(f'__import__("pathlib").Path("{target}").touch()')
    assert not target.exists()
