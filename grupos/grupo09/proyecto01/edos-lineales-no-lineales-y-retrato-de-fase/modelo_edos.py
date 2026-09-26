"""Resolución numérica de EDOs con scipy.integrate.solve_ivp."""

from scipy.integrate import solve_ivp

from datos_validacion import validar_entrada


def resolver_edo(modelo, y0, intervalo, parametros=None, *, puntos=300,
                 metodo="RK45", rtol=1e-6, atol=1e-9):
    """Resuelve x'=f(t,x,p) y devuelve el objeto estándar de SciPy.

    Ejemplo: resolver_edo(modelo_lineal, [1], (0, 5), {"a": 2})
    El resultado contiene `solucion.t` (tiempos) y `solucion.y` (estados).
    """
    estado, (t0, tf), parametros = validar_entrada(modelo, y0, intervalo, parametros)
    if not isinstance(puntos, int) or puntos < 2:
        raise ValueError("puntos debe ser un entero mayor o igual a 2.")
    if rtol <= 0 or atol <= 0:
        raise ValueError("rtol y atol deben ser positivos.")
    import numpy as np

    tiempos = np.linspace(t0, tf, puntos)
    try:
        solucion = solve_ivp(
            fun=lambda t, y: modelo(t, y, parametros),
            t_span=(t0, tf), y0=estado, method=metodo, t_eval=tiempos,
            rtol=rtol, atol=atol,
        )
    except Exception as exc:
        raise ValueError(f"No se pudo evaluar el modelo: {exc}") from exc
    if not solucion.success:
        raise RuntimeError(f"Falló la integración: {solucion.message}")
    if solucion.y.shape[0] != len(estado):
        raise ValueError("El modelo debe devolver una derivada por cada variable de estado.")
    return solucion
