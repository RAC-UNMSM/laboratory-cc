"""Parser seguro y utilidades compartidas."""
import pytest
import sympy as sp

from core.utils_math import ErrorEntrada, es_cero, parsear_seguro, parsear_tupla

x, y, t = sp.symbols("x y t")


@pytest.mark.parametrize("malicioso", [
    "__import__('os').system('ls')", "().__class__.__bases__", "exec('1')", "eval('2')", "open('a')",
    "lambda: 1", "x.__class__", "os.system", "import os", "x; y", "x" * 401, "",
])
def test_rechaza_inyeccion(malicioso):
    with pytest.raises(ErrorEntrada):
        parsear_seguro(malicioso)


@pytest.mark.parametrize("texto, esperado", [
    ("x^2 + 3xy", x**2 + 3 * x * y),
    ("x² + 3y²", x**2 + 3 * y**2),
    ("2·x − π", 2 * x - sp.pi),
    ("sinx + cos t", sp.sin(x) + sp.cos(t)),
    ("exp(t) cos t", sp.exp(t) * sp.cos(t)),
    ("sqrt(x^2 + y^2)", sp.sqrt(x**2 + y**2)),
])
def test_sintaxis_tipo_calculadora(texto, esperado):
    assert sp.simplify(parsear_seguro(texto) - esperado) == 0


def test_tupla():
    assert parsear_tupla("<cos t, sin t, t>") == [sp.cos(t), sp.sin(t), t]


def test_es_cero_varias_variables():
    assert not es_cero(x - y)
    assert es_cero(sp.sin(x) ** 2 + sp.cos(x) ** 2 - 1)
    assert es_cero((x + y) ** 2 - x**2 - 2 * x * y - y**2)
