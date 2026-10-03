from metodos.cuasi_newton import cuasi_newton_broyden
from resultado import EstadoMetodo


def test_broyden_sistema_simple():
    def f1(x):
        return x[0]**2 + x[1]**2 - 1

    def f2(x):
        return x[0] - x[1]

    funciones = [f1, f2]
    x0 = [1.0, 0.5]

    res = cuasi_newton_broyden(funciones, x0, tolerancia=1e-8, max_iter=100)

    assert res.status == EstadoMetodo.CONVERGED
    assert abs(res.solution[0] - res.solution[1]) < 1e-6
    assert abs(res.solution[0]**2 + res.solution[1]**2 - 1) < 1e-6