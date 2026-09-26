"""Cálculo numérico de Jacobiano y estabilidad local."""

import numpy as np


def jacobiano(modelo, punto, parametros=None, t=0.0, paso=1e-6):
    """Aproxima el Jacobiano respecto del estado mediante diferencias centrales."""
    parametros = parametros or {}
    punto = np.asarray(punto, dtype=float)
    n = len(punto)
    matriz = np.empty((n, n), dtype=float)
    for j in range(n):
        delta = np.zeros(n)
        delta[j] = paso * max(1.0, abs(punto[j]))
        arriba = np.asarray(modelo(t, punto + delta, parametros), dtype=float)
        abajo = np.asarray(modelo(t, punto - delta, parametros), dtype=float)
        if arriba.shape != (n,) or abajo.shape != (n,):
            raise ValueError("El modelo debe devolver una derivada por variable.")
        matriz[:, j] = (arriba - abajo) / (2 * delta[j])
    return matriz


def analizar_equilibrios(modelo, equilibrios, parametros=None, tolerancia=1e-8):
    """Clasifica equilibrios proporcionados por el modelo o por el usuario."""
    parametros = parametros or {}
    resultados = []
    for equilibrio in equilibrios:
        punto = np.atleast_1d(np.asarray(equilibrio, dtype=float))
        j = jacobiano(modelo, punto, parametros)
        valores = np.linalg.eigvals(j)
        partes_reales = valores.real
        if np.all(partes_reales < -tolerancia):
            clasificacion = "estable"
        elif np.any(partes_reales > tolerancia):
            clasificacion = "inestable"
        else:
            clasificacion = "no concluyente (hay autovalor con parte real cercana a cero)"
        resultados.append({"equilibrio": punto.tolist(), "jacobiano": j,
                           "autovalores": valores, "clasificacion": clasificacion})
    return resultados
