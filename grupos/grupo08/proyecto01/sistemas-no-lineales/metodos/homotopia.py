import numpy as np
from resultado import ResultadoMetodo, EstadoMetodo
from convergencia import norma_euclidiana


def _jacobiano_numerico(funciones, x, h=1e-7):
    n = len(x)
    m = len(funciones)
    J = np.zeros((m, n))
    for j in range(n):
        x_plus = x.copy()
        x_minus = x.copy()
        x_plus[j] += h
        x_minus[j] -= h
        F_plus = np.array([f(x_plus) for f in funciones], dtype=float)
        F_minus = np.array([f(x_minus) for f in funciones], dtype=float)
        J[:, j] = (F_plus - F_minus) / (2 * h)
    return J


def _newton_paso(funciones, x0, t, F_x0, tolerancia, max_iter):
    """Resuelve H(x, t) = F(x) - (1-t)*F(x0) = 0 por Newton."""
    x = np.array(x0, dtype=float)
    for k in range(max_iter):
        F = np.array([f(x) for f in funciones], dtype=float)
        H = F - (1.0 - t) * F_x0
        if norma_euclidiana(H) < tolerancia:
            return x, k, True
        J = _jacobiano_numerico(funciones, x)
        try:
            dx = np.linalg.solve(J, -H)
        except np.linalg.LinAlgError:
            return x, k, False
        x = x + dx
        if not np.all(np.isfinite(x)):
            return x, k, False
    return x, max_iter, False


def homotopia_continuacion(
    funciones: list,
    x0: list[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> ResultadoMetodo:
    x_actual = np.array(x0, dtype=float)
    F_x0 = np.array([f(x_actual) for f in funciones], dtype=float)
    trayectoria = [x_actual.tolist()]
    warnings = []

    n_pasos = 20
    iter_total = 0
    for i in range(1, n_pasos + 1):
        t = i / n_pasos
        x_nuevo, iter_paso, ok = _newton_paso(
            funciones, x_actual, t, F_x0, tolerancia, max_iter
        )
        iter_total += iter_paso
        trayectoria.append(x_nuevo.tolist())

        if not ok:
            return ResultadoMetodo(
                method="homotopia_continuacion",
                status=EstadoMetodo.DIVERGED,
                solution=x_nuevo.tolist(),
                iterations=iter_total,
                trajectory=trayectoria,
                warnings=warnings + [f"Fallo al resolver H(x, {t:.3f}) = 0."],
                message="Continuación interrumpida."
            )
        x_actual = x_nuevo

    F_final = np.array([f(x_actual) for f in funciones], dtype=float)
    residuo_final = norma_euclidiana(F_final)

    if residuo_final < tolerancia:
        estado = EstadoMetodo.CONVERGED
        msg = "Continuación completada."
    else:
        estado = EstadoMetodo.MAX_ITER
        msg = "Continuación terminada sin tolerancia alcanzada."

    return ResultadoMetodo(
        method="homotopia_continuacion",
        status=estado,
        solution=x_actual.tolist(),
        iterations=iter_total,
        final_error=residuo_final,
        final_residual=residuo_final,
        trajectory=trayectoria,
        warnings=warnings,
        message=msg
    )