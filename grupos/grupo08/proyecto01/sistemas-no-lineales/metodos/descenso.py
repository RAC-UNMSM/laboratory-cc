import numpy as np
from resultado import ResultadoMetodo, EstadoMetodo


def _jacobiano_numerico(funciones, x, h=1e-7):
    n = len(x)
    m = len(funciones)
    J = np.zeros((m, n))
    for j in range(n):
        x_plus = x.copy()
        x_minus = x.copy()
        x_plus[j] += h
        x_minus[j] -= h
        F_plus = np.array([f(x_plus) for f in funciones])
        F_minus = np.array([f(x_minus) for f in funciones])
        J[:, j] = (F_plus - F_minus) / (2 * h)
    return J


def descenso_mas_rapido(
    funciones: list,
    x0: list[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> ResultadoMetodo:
    x = np.array(x0, dtype=float)
    trayectoria = [x.tolist()]
    warnings = []

    for k in range(max_iter):
        F = np.array([f(x) for f in funciones], dtype=float)
        norm_F = np.linalg.norm(F)

        if norm_F < tolerancia:
            return ResultadoMetodo(
                method="descenso_mas_rapido",
                status=EstadoMetodo.CONVERGED,
                solution=x.tolist(),
                iterations=k,
                final_error=float(norm_F),
                final_residual=float(norm_F),
                trajectory=trayectoria,
                warnings=warnings,
                message="Convergencia alcanzada."
            )

        J = _jacobiano_numerico(funciones, x)
        grad = 2 * J.T @ F

        if np.linalg.norm(grad) < tolerancia:
            return ResultadoMetodo(
                method="descenso_mas_rapido",
                status=EstadoMetodo.CONVERGED,
                solution=x.tolist(),
                iterations=k,
                final_error=float(norm_F),
                final_residual=float(norm_F),
                trajectory=trayectoria,
                warnings=warnings,
                message="Gradiente cercano a cero."
            )

        direccion = -grad
        alpha = 1.0
        c = 1e-4
        rho = 0.5

        while alpha > 1e-12:
            x_new = x + alpha * direccion
            F_new = np.array([f(x_new) for f in funciones], dtype=float)
            if np.linalg.norm(F_new) < (1 - c * alpha) * norm_F:
                break
            alpha *= rho
        else:
            warnings.append("Búsqueda de línea no mejoró; se toma paso pequeño.")
            alpha = 1e-6
            x_new = x + alpha * direccion

        x = x_new
        trayectoria.append(x.tolist())

    F = np.array([f(x) for f in funciones], dtype=float)
    return ResultadoMetodo(
        method="descenso_mas_rapido",
        status=EstadoMetodo.MAX_ITER,
        solution=x.tolist(),
        iterations=max_iter,
        final_error=float(np.linalg.norm(F)),
        final_residual=float(np.linalg.norm(F)),
        trajectory=trayectoria,
        warnings=warnings,
        message="Máximo de iteraciones alcanzado."
    )