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
        F_plus = np.array([f(x_plus) for f in funciones], dtype=float)
        F_minus = np.array([f(x_minus) for f in funciones], dtype=float)
        J[:, j] = (F_plus - F_minus) / (2 * h)
    return J


def newton_sistemas(
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
        norm_F = float(np.linalg.norm(F))

        if norm_F < tolerancia:
            return ResultadoMetodo(
                method="newton_sistemas",
                status=EstadoMetodo.CONVERGED,
                solution=x.tolist(),
                iterations=k,
                final_error=norm_F,
                final_residual=norm_F,
                trajectory=trayectoria,
                warnings=warnings,
                message="Convergencia alcanzada."
            )

        J = _jacobiano_numerico(funciones, x)
        try:
            dx = np.linalg.solve(J, -F)
        except np.linalg.LinAlgError:
            return ResultadoMetodo(
                method="newton_sistemas",
                status=EstadoMetodo.SINGULAR_JACOBIAN,
                solution=x.tolist(),
                iterations=k,
                final_error=norm_F,
                final_residual=norm_F,
                trajectory=trayectoria,
                warnings=warnings + ["Jacobiano singular."],
                message="Jacobiano singular en la iteración."
            )

        x = x + dx
        trayectoria.append(x.tolist())

        if not np.all(np.isfinite(x)):
            return ResultadoMetodo(
                method="newton_sistemas",
                status=EstadoMetodo.DIVERGED,
                solution=x.tolist(),
                iterations=k + 1,
                trajectory=trayectoria,
                warnings=warnings + ["Valor no finito en la iteración."],
                message="Divergencia detectada."
            )

    F = np.array([f(x) for f in funciones], dtype=float)
    norm_F = float(np.linalg.norm(F))
    return ResultadoMetodo(
        method="newton_sistemas",
        status=EstadoMetodo.MAX_ITER,
        solution=x.tolist(),
        iterations=max_iter,
        final_error=norm_F,
        final_residual=norm_F,
        trajectory=trayectoria,
        warnings=warnings,
        message="Máximo de iteraciones alcanzado."
    )