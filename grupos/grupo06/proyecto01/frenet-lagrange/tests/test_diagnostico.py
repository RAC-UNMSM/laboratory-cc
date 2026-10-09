"""Ruteo semántico: lenguaje natural → método y argumentos."""
import pytest

from core.diagnostico import diagnosticar


@pytest.mark.parametrize("enunciado, metodo", [
    ("Maximiza f(x,y) = x*y sujeto a x^2 + y^2 = 8", "lagrange"),
    ("Minimiza x^2+y^2 con x + y = 10", "lagrange"),
    ("Usa multiplicadores de Lagrange para optimizar f(x,y,z) = xyz s.a. x+y+z=12", "lagrange"),
    ("Halla y clasifica los puntos críticos de f(x,y) = x^3 + y^3 - 3xy", "hessiana"),
    ("¿Dónde tiene máximos y mínimos relativos la función x^4+y^4-4xy+1?", "hessiana"),
    ("f(x,y)=x² + 3y² ¿es la Hessiana definida positiva?", "hessiana"),
    ("Calcula la curvatura y la torsión de r(t) = (cos t, sin t, t) en t = 0", "frenet"),
    ("Dada la hélice r(t)=<3cos t, 3sin t, 4t>, halla el plano osculador en t=pi/2", "frenet"),
    ("quiero el triedro de frenet de la cúbica alabeada", "frenet"),
])
def test_ruteo(enunciado, metodo):
    assert diagnosticar(enunciado).metodo_recomendado == metodo


def test_extraccion_de_argumentos():
    d = diagnosticar("Encuentra los extremos de f(x,y,z)=x+y+z sobre la curva x^2+y^2=2 y x+z=1")
    assert d.argumentos_sugeridos == {"funcion": "x+y+z", "restricciones": ["x^2+y^2=2", "x+z=1"]}
    d = diagnosticar("Calcula T, N y B de r(t)=(t, t^2, t^3) para t = 1")
    assert d.argumentos_sugeridos == {"curva": ["t", "t^2", "t^3"], "t0": "1"}


def test_sin_indicios():
    d = diagnosticar("hola, ¿cómo estás?")
    assert d.metodo_recomendado is None and d.confianza == 0
