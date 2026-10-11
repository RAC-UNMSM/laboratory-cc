"""Derivación numérica con extrapolación de Richardson.

Base: diferencia centrada  D(h) = (f(x+h) - f(x-h)) / (2h) = f'(x) + c2 h^2 + c4 h^4 + ...
Como el error solo tiene potencias pares, cada columna j elimina h^(2j):

    T[i][0] = D(h0 / 2^i)
    T[i][j] = (4^j T[i][j-1] - T[i-1][j-1]) / (4^j - 1)      (orden O(h^(2j+2)))
"""
from __future__ import annotations

import math
from typing import Callable


def derivada_richardson(f: Callable[[float], float], x0: float, h: float = 0.5,
                        niveles: int = 6, tol: float | None = None) -> dict:
    if niveles < 1:
        raise ValueError("niveles debe ser >= 1")
    tabla: list[list[float]] = []
    error = math.inf
    convergio = False
    for i in range(niveles):
        hi = h / 2 ** i
        fila = [(f(x0 + hi) - f(x0 - hi)) / (2 * hi)]
        for j in range(1, i + 1):
            fac = 4 ** j
            fila.append((fac * fila[j - 1] - tabla[i - 1][j - 1]) / (fac - 1))
        tabla.append(fila)
        if i >= 1:
            error = abs(fila[-1] - fila[-2])
            if tol is not None and error < tol:
                convergio = True
                break
    return {
        "metodo": "derivacion_richardson",
        "x0": x0,
        "h0": h,
        "resultado": tabla[-1][-1],
        "error_estimado": error if math.isfinite(error) else None,
        "tolerancia": tol,
        "convergio": convergio if tol is not None else None,
        "niveles_usados": len(tabla),
        "evaluaciones": 2 * len(tabla),
        "orden_final": 2 * len(tabla),
        "tabla": tabla,
    }
