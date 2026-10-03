import numpy as np
from resultado import ResultadoMetodo, EstadoMetodo


def punto_fijo_varias_variables(
    funciones: list,
    x0: list[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> ResultadoMetodo:
    """Itera x_{k+1} = G(x_k). Las `funciones` son las componentes de G."""
    x = np.array(x0, dtype=float)
    trayectoria = [x.tolist()]
    warnings = []

    for k in range(max_iter):
        try:
            x_new = np.array([float(f(x)) for f in funciones], dtype=float)
        except Exception as e:
            return ResultadoMetodo(
                method="punto_fijo_varias_variables",
                status=EstadoMetodo.INVALID_INPUT,
                solution=x.tolist(),
                iterations=k,
                trajectory=trayectoria,
                warnings=warnings + [str(e)],
                message="Error al evaluar G(x)."
            )

        if not np.all(np.isfinite(x_new)):
            return ResultadoMetodo(
                method="punto_fijo_varias_variables",
                status=EstadoMetodo.DIVERGED,
                solution=x.tolist(),
                iterations=k,
                trajectory=trayectoria,
                warnings=warnings + ["Valor no finito en la iteración."],
                message="Divergencia detectada."
            )

        error = float(np.linalg.norm(x_new - x, ord=np.inf))
        trayectoria.append(x_new.tolist())

        if error < tolerancia:
            return ResultadoMetodo(
                method="punto_fijo_varias_variables",
                status=EstadoMetodo.CONVERGED,
                solution=x_new.tolist(),
                iterations=k + 1,
                final_error=error,
                final_residual=error,
                trajectory=trayectoria,
                warnings=warnings,
                message="Convergencia alcanzada."
            )

        if np.linalg.norm(x_new, ord=np.inf) > 1e12:
            return ResultadoMetodo(
                method="punto_fijo_varias_variables",
                status=EstadoMetodo.DIVERGED,
                solution=x_new.tolist(),
                iterations=k + 1,
                final_error=error,
                final_residual=error,
                trajectory=trayectoria,
                warnings=warnings + ["Norma de x crece sin control."],
                message="Divergencia detectada."
            )

        x = x_new

    return ResultadoMetodo(
        method="punto_fijo_varias_variables",
        status=EstadoMetodo.MAX_ITER,
        solution=x.tolist(),
        iterations=max_iter,
        trajectory=trayectoria,
        warnings=warnings,
        message="Máximo de iteraciones alcanzado."
    )