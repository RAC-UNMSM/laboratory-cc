from convergencia import (
    norma_euclidiana, norma_infinita, error_absoluto, residuo, clasificar_estado
)
from resultado import EstadoMetodo


def test_normas():
    v = [3.0, 4.0]
    assert abs(norma_euclidiana(v) - 5.0) < 1e-12
    assert abs(norma_infinita(v) - 4.0) < 1e-12


def test_error_absoluto():
    assert abs(error_absoluto([1.0, 2.0], [1.5, 1.0]) - 1.0) < 1e-12


def test_residuo():
    def f1(x):
        return x[0] - 1.0
    def f2(x):
        return x[1] - 2.0
    assert abs(residuo([f1, f2], [1.0, 2.0])) < 1e-12


def test_clasificar_estado():
    assert clasificar_estado(1e-12, 1e-8, 3, 100) == EstadoMetodo.CONVERGED
    assert clasificar_estado(1.0, 1e-8, 100, 100) == EstadoMetodo.MAX_ITER
    assert clasificar_estado(1.0, 1e-8, 3, 100, divergio=True) == EstadoMetodo.DIVERGED
    assert clasificar_estado(1.0, 1e-8, 3, 100, jacobiano_singular=True) == EstadoMetodo.SINGULAR_JACOBIAN