import math
from metodos.newton_sistemas import newton_sistemas
from resultado import EstadoMetodo


def test_newton_circunferencia_recta():
    def f1(x):
        return x[0]**2 + x[1]**2 - 1.0

    def f2(x):
        return x[0] - x[1]

    funciones = [f1, f2]
    res = newton_sistemas(funciones, x0=[1.0, 0.5], tolerancia=1e-10, max_iter=50)

    assert res.status == EstadoMetodo.CONVERGED
    esperado = 1.0 / math.sqrt(2.0)
    assert abs(res.solution[0] - esperado) < 1e-8
    assert abs(res.solution[1] - esperado) < 1e-8
    assert res.iterations < 15


def test_newton_jacobiano_singular():
    # F(x,y) = (x + y - 1, x + y - 1): Jacobiano singular en todas partes.
    def f1(x):
        return x[0] + x[1] - 1.0

    def f2(x):
        return x[0] + x[1] - 1.0

    funciones = [f1, f2]
    res = newton_sistemas(funciones, x0=[0.0, 0.0], tolerancia=1e-10, max_iter=20)

    assert res.status == EstadoMetodo.SINGULAR_JACOBIAN