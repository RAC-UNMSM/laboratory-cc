import numpy as np
from resultado import ResultadoMetodo, EstadoMetodo


def cuasi_newton_broyden(
    funciones: list,
    x0: list[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> ResultadoMetodo:
    x = np.array(x0, dtype=float)
    n = len(x)
    F = np.array([f(x) for f in funciones], dtype=float)
    B = np.eye(n)
    trayectoria = [x.tolist()]
    warnings = []

    for k in range(max_iter):
        norm_F = np.linalg.norm(F)
        if norm_F < tolerancia:
            return ResultadoMetodo(
                method="cuasi_newton_broyden",
                status=EstadoMetodo.CONVERGED,
                solution=x.tolist(),
                iterations=k,
                final_error=float(norm_F),
                final_residual=float(norm_F),
                trajectory=trayectoria,
                warnings=warnings,
                message="Convergencia alcanzada."
            )

        try:
            dx = np.linalg.solve(B, -F)
        except np.linalg.LinAlgError:
            return ResultadoMetodo(
                method="cuasi_newton_broyden",
                status=EstadoMetodo.SINGULAR_JACOBIAN,
                solution=x.tolist(),
                iterations=k,
                final_error=float(norm_F),
                final_residual=float(norm_F),
                trajectory=trayectoria,
                warnings=warnings + ["Matriz B singular."],
                message="Jacobiano aproximado singular."
            )

        x_new = x + dx
        F_new = np.array([f(x_new) for f in funciones], dtype=float)
        y = F_new - F
        denom = np.dot(dx, dx)

        if denom > 1e-14:
            B = B + np.outer(y - B @ dx, dx) / denom
        else:
            warnings.append("Paso dx muy pequeño; no se actualiza B.")

        x, F = x_new, F_new
        trayectoria.append(x.tolist())

    return ResultadoMetodo(
        method="cuasi_newton_broyden",
        status=EstadoMetodo.MAX_ITER,
        solution=x.tolist(),
        iterations=max_iter,
        final_error=float(np.linalg.norm(F)),
        final_residual=float(np.linalg.norm(F)),
        trajectory=trayectoria,
        warnings=warnings,
        message="Máximo de iteraciones alcanzado."
    )