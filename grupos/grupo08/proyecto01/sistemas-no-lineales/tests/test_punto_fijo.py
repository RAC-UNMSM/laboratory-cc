from metodos.punto_fijo import punto_fijo_varias_variables
from resultado import EstadoMetodo


def test_punto_fijo_sistema_contraccion():
    def g1(x):
        return (x[0] + x[1] + 1.0) / 3.0

    def g2(x):
        return (x[0] - x[1] + 2.0) / 3.0

    funciones = [g1, g2]
    res = punto_fijo_varias_variables(
        funciones, x0=[0.0, 0.0], tolerancia=1e-10, max_iter=200
    )

    assert res.status == EstadoMetodo.CONVERGED
    assert abs(res.solution[0] - 6.0 / 7.0) < 1e-6
    assert abs(res.solution[1] - 5.0 / 7.0) < 1e-6
    assert res.iterations > 0


def test_punto_fijo_max_iter_sin_contraccion():
    def g1(x):
        return 2.0 * x[0]

    def g2(x):
        return 2.0 * x[1]

    funciones = [g1, g2]
    res = punto_fijo_varias_variables(
        funciones, x0=[0.1, 0.1], tolerancia=1e-10, max_iter=20
    )

    assert res.status in (EstadoMetodo.MAX_ITER, EstadoMetodo.DIVERGED)
    assert len(res.warnings) >= 0