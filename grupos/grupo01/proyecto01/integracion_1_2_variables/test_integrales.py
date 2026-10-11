import pytest
import sympy as sp
from matematica import integrar_simple, integrar_doble_rectangular, integrar_doble_general
from validacion import validar_y_parsear_expresion, validar_limites_numericos, ErrorDeEntrada

def test_integral_simple():
    expr = validar_y_parsear_expresion("x**2", variables=('x',))
    res, _ = integrar_simple(expr, 0, 3)
    assert float(res) == pytest.approx(9.0)

def test_integral_doble_rectangular():
    expr = validar_y_parsear_expresion("x*y")
    res, _ = integrar_doble_rectangular(expr, 0, 1, 0, 2)
    assert float(res) == pytest.approx(1.0)

def test_integral_doble_circular():
    # Integral de f(x,y)=1 sobre un semicírculo superior de radio 1 -> Área = pi/2
    expr = validar_y_parsear_expresion("1")
    res, _ = integrar_doble_general(expr, "y", "0", "sqrt(1-x**2)", "x", -1, 1)
    assert float(res) == pytest.approx(float(sp.pi / 2))

def test_validacion_limites_invertidos():
    with pytest.raises(ErrorDeEntrada):
        validar_limites_numericos(5, 2, "x")

def test_validacion_sugerencia_alias():
    expr = validar_y_parsear_expresion("sen(x) + cos(x)", variables=('x',))
    assert 'sin' in str(expr)