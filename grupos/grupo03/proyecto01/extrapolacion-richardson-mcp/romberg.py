"""Integración de Romberg: regla del trapecio + Richardson iterado.

    R[i][0] = trapecio con 2^i subintervalos (reutiliza evaluaciones previas)
    R[i][j] = (4^j R[i][j-1] - R[i-1][j-1]) / (4^j - 1)
Criterio de parada: |R[i][i] - R[i-1][i-1]| < tol.
"""
from __future__ import annotations

from typing import Callable


def romberg(f: Callable[[float], float], a: float, b: float,
            tol: float = 1e-8, max_niveles: int = 12) -> dict:
    if max_niveles < 2:
        raise ValueError("max_niveles debe ser >= 2")
    h = b - a
    R = [[0.5 * h * (f(a) + f(b))]]
    evaluaciones = 2
    error = float("inf")
    convergio = False
    for i in range(1, max_niveles):
        h /= 2
        suma = sum(f(a + (2 * k - 1) * h) for k in range(1, 2 ** (i - 1) + 1))
        evaluaciones += 2 ** (i - 1)
        fila = [0.5 * R[i - 1][0] + h * suma]
        for j in range(1, i + 1):
            fac = 4 ** j
            fila.append((fac * fila[j - 1] - R[i - 1][j - 1]) / (fac - 1))
        R.append(fila)
        error = abs(fila[-1] - R[i - 1][-1])
        if error < tol:
            convergio = True
            break
    return {
        "metodo": "romberg",
        "a": a,
        "b": b,
        "resultado": R[-1][-1],
        "error_estimado": error,
        "tolerancia": tol,
        "convergio": convergio,
        "niveles_usados": len(R),
        "evaluaciones": evaluaciones,
        "tabla": R,
    }
