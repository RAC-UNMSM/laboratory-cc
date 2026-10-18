import numpy as np
from resultado import EstadoMetodo


def norma_euclidiana(v) -> float:
    return float(np.linalg.norm(np.asarray(v, dtype=float)))


def norma_infinita(v) -> float:
    return float(np.linalg.norm(np.asarray(v, dtype=float), ord=np.inf))


def error_absoluto(x_new, x_old) -> float:
    return norma_infinita(np.asarray(x_new) - np.asarray(x_old))


def residuo(funciones, x) -> float:
    F = np.array([f(x) for f in funciones], dtype=float)
    return norma_euclidiana(F)


def clasificar_estado(
    residuo_actual: float,
    tolerancia: float,
    iteracion: int,
    max_iter: int,
    divergio: bool = False,
    jacobiano_singular: bool = False,
) -> EstadoMetodo:
    if jacobiano_singular:
        return EstadoMetodo.SINGULAR_JACOBIAN
    if divergio:
        return EstadoMetodo.DIVERGED
    if residuo_actual < tolerancia:
        return EstadoMetodo.CONVERGED
    if iteracion >= max_iter:
        return EstadoMetodo.MAX_ITER
    return EstadoMetodo.MAX_ITER