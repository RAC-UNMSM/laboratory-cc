"""Valores conocidos de los tres métodos (resultados exactos)."""
import sympy as sp

from methods import metodo_frenet as MF, metodo_hessiana as MH, metodo_lagrange as ML


def test_lagrange_xy_circunferencia():
    r = ML.resolver_lagrange("x*y", ["x^2 + y^2 = 8"])
    valores = sorted(sp.sympify(p["valor_f"]) for p in r["puntos_criticos"])
    assert valores == [-4, -4, 4, 4]
    assert {p["clasificacion"] for p in r["puntos_criticos"]} == {ML.MAX_LOCAL, ML.MIN_LOCAL}


def test_lagrange_distancia_al_plano():
    r = ML.resolver_lagrange("x^2 + y^2 + z^2", ["x + y + z = 3"])
    (p,) = r["puntos_criticos"]
    assert sp.sympify(p["valor_f"]) == 3 and p["clasificacion"] == ML.MIN_LOCAL


def test_hessiana_demo1():
    r = MH.resolver_hessiana("x^4 + y^4 - 4xy + 1")
    clases = sorted(p["clasificacion"] for p in r["puntos_criticos"])
    assert clases == sorted([MH.MIN_LOCAL, MH.MIN_LOCAL, MH.SILLA])
    assert sp.sympify(r["analisis_global"]["minimo_global"]) == -1


def test_hessiana_peano_es_silla():
    r = MH.resolver_hessiana("(y - x^2)*(y - 2x^2)")
    assert r["puntos_criticos"][0]["clasificacion"] == MH.SILLA


def test_frenet_helice():
    r = MF.resolver_frenet("cos t, sin t, t", t0="0")
    assert sp.sympify(r["curvatura"]["expr"]) == sp.Rational(1, 2)
    assert sp.sympify(r["torsion"]["expr"]) == sp.Rational(1, 2)
    assert r["verificacion"]["correcto"]


def test_frenet_parabola_plana():
    r = MF.resolver_frenet("t, t^2", t0="0")
    assert sp.sympify(r["en_t0"]["curvatura"]["expr"]) == 2
