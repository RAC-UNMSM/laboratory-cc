"""Modelos de referencia definidos en la propuesta del grupo."""


def modelo_lineal(t, y, parametros):
    """EDO lineal x'=-a*x; por defecto a=2."""
    a = parametros.get("a", 2.0)
    return [-a * y[0]]


def equilibrios_lineal(parametros):
    return [0.0]


def modelo_logistico(t, y, parametros):
    """Modelo logístico x'=r*x*(1-x/K)."""
    r, k = parametros.get("r", 1.0), parametros.get("K", 10.0)
    if k == 0:
        raise ValueError("K debe ser distinto de cero.")
    return [r * y[0] * (1 - y[0] / k)]


def equilibrios_logistico(parametros):
    k = parametros.get("K", 10.0)
    if k == 0:
        raise ValueError("K debe ser distinto de cero.")
    return [0.0, float(k)]


def modelo_lorenz(t, y, parametros):
    """Sistema de Lorenz en su formulación clásica."""
    sigma = parametros.get("sigma", 10.0)
    rho = parametros.get("rho", 28.0)
    beta = parametros.get("beta", 8.0 / 3.0)
    x, yy, z = y
    return [sigma * (yy - x), x * (rho - z) - yy, x * yy - beta * z]


MODELOS = {
    "lineal": {"funcion": modelo_lineal, "dimension": 1, "parametros": {"a": 2.0},
               "y0": [1.0], "intervalo": (0.0, 5.0), "equilibrios": equilibrios_lineal},
    "logistico": {"funcion": modelo_logistico, "dimension": 1, "parametros": {"r": 1.0, "K": 10.0},
                  "y0": [1.0], "intervalo": (0.0, 10.0), "equilibrios": equilibrios_logistico},
    "lorenz": {"funcion": modelo_lorenz, "dimension": 3,
               "parametros": {"sigma": 10.0, "rho": 28.0, "beta": 8.0 / 3.0},
               "y0": [1.0, 1.0, 1.0], "intervalo": (0.0, 40.0)},
}


def obtener_modelo(nombre):
    """Devuelve una copia de configuración para poder personalizar parámetros."""
    clave = nombre.lower().strip()
    if clave not in MODELOS:
        raise ValueError(f"Modelo desconocido: {nombre!r}. Opciones: {', '.join(MODELOS)}")
    return dict(MODELOS[clave])
