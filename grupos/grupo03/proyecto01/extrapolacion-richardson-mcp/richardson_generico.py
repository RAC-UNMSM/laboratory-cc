"""Extrapolación de Richardson genérica (función de orden superior).

Dado ``metodo(h)`` cuyo error es  c1 h^p + c2 h^(p+q) + c3 h^(p+2q) + ...  se construye

    A[i][0] = metodo(h0 / r^i)
    A[i][j] = (r^pj A[i][j-1] - A[i-1][j-1]) / (r^pj - 1),   pj = p + (j-1) q

``orden`` = p, ``incremento`` = q (1 si el error tiene todas las potencias, 2 si solo pares).
``metodo`` puede devolver float o ndarray.
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np


def _norma(x) -> float:
    return float(np.max(np.abs(x)))


def _a_lista(x):
    return np.asarray(x, dtype=float).tolist()


def richardson(metodo: Callable[[float], object], h0: float, orden: float,
               niveles: int = 5, razon: float = 2.0, incremento: float = 1.0,
               tol: float | None = None) -> dict:
    if niveles < 1:
        raise ValueError("niveles debe ser >= 1")
    if razon <= 1:
        raise ValueError("razon debe ser > 1")
    tabla: list[list] = []
    error = math.inf
    convergio = False
    for i in range(niveles):
        fila = [np.asarray(metodo(h0 / razon ** i), dtype=float)]
        for j in range(1, i + 1):
            fac = razon ** (orden + (j - 1) * incremento)
            fila.append((fac * fila[j - 1] - tabla[i - 1][j - 1]) / (fac - 1))
        tabla.append(fila)
        if i >= 1:
            error = _norma(fila[-1] - fila[-2])
            if tol is not None and error < tol:
                convergio = True
                break
    n = len(tabla)
    return {
        "metodo": "richardson_generico",
        "h0": h0,
        "razon": razon,
        "orden_base": orden,
        "incremento": incremento,
        "orden_final": orden + (n - 1) * incremento,
        "resultado": _a_lista(tabla[-1][-1]),
        "error_estimado": error if math.isfinite(error) else None,
        "convergio": convergio if tol is not None else None,
        "niveles_usados": n,
        "tabla": [_a_lista(fila) for fila in tabla],
    }


# --- Métodos base listos para usar -------------------------------------------------
def diferencia_adelante(f, x0):
    return lambda h: (f(x0 + h) - f(x0)) / h          # error O(h), todas las potencias


def diferencia_central(f, x0):
    return lambda h: (f(x0 + h) - f(x0 - h)) / (2 * h)  # error O(h^2), potencias pares


def trapecio_compuesto(f, a, b, n):
    h = (b - a) / n
    return h * (0.5 * f(a) + 0.5 * f(b) + sum(f(a + k * h) for k in range(1, n)))


def trapecio(f, a, b):
    """Trapecio como función del paso h (n = round((b-a)/h)); error O(h^2), potencias pares."""
    return lambda h: trapecio_compuesto(f, a, b, max(1, round((b - a) / h)))


METODOS_BASE = {
    # nombre: (orden p, incremento q)
    "diferencia_adelante": (1, 1),
    "diferencia_central": (2, 2),
    "trapecio": (2, 2),
}
