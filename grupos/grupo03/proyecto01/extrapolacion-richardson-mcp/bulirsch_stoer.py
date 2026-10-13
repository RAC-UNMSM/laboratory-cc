"""Método de Bulirsch-Stoer para EDOs  y' = f(t, y).

Cada paso grande H se calcula con el punto medio modificado (Gragg) usando
n_k = 2, 4, 6, ... subpasos, y se extrapola a h -> 0 con Richardson en h^2
(esquema de Aitken-Neville). El paso se rechaza y se reduce si la extrapolación
no converge dentro de ``kmax`` columnas.
"""
from __future__ import annotations

import numpy as np

SECUENCIA = [2, 4, 6, 8, 10, 12, 14, 16]


def punto_medio_modificado(f, t, y, H, n):
    h = H / n
    z_prev, z = y, y + h * f(t, y)
    for i in range(1, n):
        z_prev, z = z, z_prev + 2 * h * f(t + i * h, z)
    return 0.5 * (z + z_prev + h * f(t + H, z))


def _paso(f, t, y, H, kmax, rtol, atol):
    """Intenta un paso H. Devuelve (y_nuevo, columnas_usadas, error) o None si no converge."""
    T: list[list[np.ndarray]] = []
    for k in range(kmax):
        fila = [punto_medio_modificado(f, t, y, H, SECUENCIA[k])]
        for j in range(1, k + 1):
            razon = (SECUENCIA[k] / SECUENCIA[k - j]) ** 2
            fila.append(fila[j - 1] + (fila[j - 1] - T[k - 1][j - 1]) / (razon - 1))
        T.append(fila)
        if k >= 1:
            escala = atol + rtol * np.maximum(np.abs(y), np.abs(fila[-1]))
            err = float(np.max(np.abs(fila[-1] - fila[-2]) / escala))
            if err <= 1.0:
                return fila[-1], k + 1, err
    return None


def bulirsch_stoer(f, t0: float, y0, tf: float, tol: float = 1e-8,
                   H0: float | None = None, kmax: int = 8, max_pasos: int = 100000) -> dict:
    if tf <= t0:
        raise ValueError("Se requiere tf > t0.")
    kmax = max(2, min(kmax, len(SECUENCIA)))
    escalar = np.ndim(y0) == 0
    y = np.atleast_1d(np.asarray(y0, dtype=float))
    contador = {"n": 0}

    def F(t, yy):
        contador["n"] += 1
        return np.atleast_1d(np.asarray(f(t, yy), dtype=float))

    H = (tf - t0) / 10 if H0 is None else H0
    t = t0
    ts, ys = [t], [y.copy()]
    rechazados = 0
    pasos = 0
    while t < tf:
        if pasos + rechazados >= max_pasos:
            raise RuntimeError("Se superó max_pasos; reduzca el intervalo o relaje la tolerancia.")
        ultimo = t + H >= tf
        if ultimo:
            H = tf - t
        res = _paso(F, t, y, H, kmax, tol, tol)
        if res is None:
            H *= 0.5
            rechazados += 1
            if H < 1e-14 * max(1.0, abs(t)):
                raise RuntimeError("Paso demasiado pequeño: el problema parece singular o muy rígido.")
            continue
        y, cols, _ = res
        t = tf if ultimo else t + H
        pasos += 1
        ts.append(t)
        ys.append(y.copy())
        if cols <= 3:
            H *= 1.5
        elif cols >= 7:
            H *= 0.7
    Y = np.array(ys)
    return {
        "metodo": "bulirsch_stoer",
        "t0": t0,
        "tf": tf,
        "tolerancia": tol,
        "pasos_aceptados": pasos,
        "pasos_rechazados": rechazados,
        "evaluaciones": contador["n"],
        "t": ts,
        "y": (Y[:, 0] if escalar else Y).tolist(),
        "y_final": float(Y[-1, 0]) if escalar else Y[-1].tolist(),
    }
