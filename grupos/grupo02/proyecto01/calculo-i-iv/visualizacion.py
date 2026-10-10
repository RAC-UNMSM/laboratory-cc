"""Gráfico 2D en memoria, con dominio real certificado antes de muestrear."""

import base64
from io import BytesIO

import numpy as np
import sympy as sp
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sympy.calculus.util import continuous_domain
from validacion import EntradaError, interval, parse, variable


def render(expresion, inferior, superior, variable_nombre="x"):
    v = variable(variable_nombre)
    e = parse(expresion, (variable_nombre,))
    a, b = interval(inferior, superior)
    if a == b or a in (-sp.oo, sp.oo) or b in (-sp.oo, sp.oo):
        raise EntradaError("Gráfico: intervalo finito no degenerado.")
    if sp.Interval(a, b).is_subset(continuous_domain(e, v, sp.S.Reals)) is not True:
        raise EntradaError(
            "Grafique un intervalo donde la función sea real y continua; divida en tramos en las discontinuidades."
        )
    xs = np.linspace(float(a), float(b), 600)
    with np.errstate(all="ignore"):
        ys = np.asarray(sp.lambdify(v, e, modules="numpy")(xs), dtype=np.complex128)
    ys = np.broadcast_to(ys, xs.shape)
    valid = np.isfinite(ys) & (np.abs(ys.imag) < 1e-10)
    if not np.any(valid):
        raise EntradaError(
            "No hay valores reales finitos representables en el intervalo."
        )
    yy = np.where(valid, ys.real, np.nan)
    fig = Figure(figsize=(8, 4.5), dpi=110)
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    ax.plot(xs, yy, color="#2563eb", linewidth=2)
    ax.axhline(0, color="#94a3b8", linewidth=0.8)
    ax.grid(alpha=0.2)
    ax.set(
        xlabel=variable_nombre,
        ylabel="f(" + variable_nombre + ")",
        title="Gráfica de la función (muestreo numérico)",
    )
    fig.tight_layout()
    stream = BytesIO()
    fig.savefig(stream, format="png")
    fig.clear()
    return {
        "estado": "calculado",
        "png_base64": base64.b64encode(stream.getvalue()).decode(),
        "observaciones": [
            "600 muestras. La gráfica no constituye una prueba matemática ni garantiza detectar oscilaciones entre muestras."
        ],
    }
