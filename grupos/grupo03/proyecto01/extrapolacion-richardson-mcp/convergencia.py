"""Análisis de convergencia: método base vs. método extrapolado.

Para cada paso h se compara el error del método base, A(h), con el de una
extrapolación de un nivel que usa A(h) y A(h/r):

    R(h) = (r^p A(h/r) - A(h)) / (r^p - 1)

y se estima el orden observado  p_obs = log(e_i / e_{i+1}) / log(h_i / h_{i+1}).
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

from derivacion_richardson import derivada_richardson
from richardson_generico import trapecio_compuesto

PISO_ERROR = 1e-14  # por debajo de esto el error es ruido de redondeo


def orden_observado(hs: Sequence[float], errores: Sequence[float], piso: float = PISO_ERROR) -> list[float]:
    """Pendiente log-log entre pasos consecutivos (nan si el error está en el piso de redondeo)."""
    out = []
    for i in range(len(hs) - 1):
        e1, e2 = errores[i], errores[i + 1]
        if e1 > piso and e2 > piso and hs[i] != hs[i + 1]:
            out.append(math.log(e1 / e2) / math.log(hs[i] / hs[i + 1]))
        else:
            out.append(float("nan"))
    return out


def comparar(metodo: Callable[[float], float], exacto: float, hs: Sequence[float],
             orden_base: float, incremento: float = 2.0, razon: float = 2.0) -> dict:
    fac = razon ** orden_base
    err_base, err_extra = [], []
    for h in hs:
        a, b = metodo(h), metodo(h / razon)
        err_base.append(abs(a - exacto))
        err_extra.append(abs((fac * b - a) / (fac - 1) - exacto))
    ob = orden_observado(hs, err_base)
    oe = orden_observado(hs, err_extra)
    mejora = [eb / ee if ee > 0 else math.inf for eb, ee in zip(err_base, err_extra)]
    return {
        "hs": list(hs),
        "valor_exacto": exacto,
        "error_base": err_base,
        "error_extrapolado": err_extra,
        "orden_teorico_base": orden_base,
        "orden_teorico_extrapolado": orden_base + incremento,
        "orden_observado_base": ob,
        "orden_observado_extrapolado": oe,
        "factor_mejora": mejora,
    }


def convergencia_derivada(f, x0: float, exacto: float | None = None,
                          hs: Sequence[float] | None = None) -> dict:
    hs = list(hs) if hs is not None else [0.5 / 2 ** k for k in range(7)]
    if exacto is None:  # referencia de alta precisión
        exacto = derivada_richardson(f, x0, h=0.2, niveles=8, tol=1e-14)["resultado"]
    res = comparar(lambda h: (f(x0 + h) - f(x0 - h)) / (2 * h), exacto, hs, orden_base=2, incremento=2)
    res.update(problema="derivada", base="diferencia central", x0=x0)
    return res


def convergencia_integral(f, a: float, b: float, exacto: float | None = None,
                          hs: Sequence[float] | None = None) -> dict:
    hs = list(hs) if hs is not None else [(b - a) / 2 ** k for k in range(1, 8)]
    if exacto is None:
        from scipy.integrate import quad
        exacto = quad(f, a, b, epsabs=1e-14, epsrel=1e-14)[0]
    res = comparar(lambda h: trapecio_compuesto(f, a, b, max(1, round((b - a) / h))),
                   exacto, hs, orden_base=2, incremento=2)
    res.update(problema="integral", base="trapecio compuesto", a=a, b=b)
    return res
