import math
from metodos.homotopia import homotopia_continuacion
from resultado import EstadoMetodo


def test_homotopia_circunferencia_recta():
    def f1(x):
        return x[0]**2 + x[1]**2 - 1.0

    def f2(x):
        return x[0] - x[1]

    funciones = [f1, f2]
    res = homotopia_continuacion(
        funciones, x0=[0.9, 0.4], tolerancia=1e-8, max_iter=50
    )

    assert res.status == EstadoMetodo.CONVERGED
    esperado = 1.0 / math.sqrt(2.0)
    assert abs(res.solution[0] - esperado) < 1e-6
    assert abs(res.solution[1] - esperado) < 1e-6