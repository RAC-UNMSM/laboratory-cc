"""Visualización: rol "Visualización" del pilotaje MCP."""

import io

# matplotlib.use("Agg") ANTES de importar pyplot: le dice que dibuje a un
# archivo/buffer en memoria en vez de abrir una ventana -- el contenedor no
# tiene pantalla, así que sin esto pyplot fallaría al importarse.
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp


def graficar(
    f: sp.Expr, derivada: sp.Expr, xs: np.ndarray, ys: np.ndarray, dys: np.ndarray
) -> bytes:
    """Un solo gráfico con f(x) y f'(x) superpuestas, para comparar la forma
    de la función original contra la de su derivada. Devuelve el PNG como
    bytes -- nunca se guarda en disco, el contenedor no persiste nada entre
    llamadas, la imagen viaja directo en la respuesta de la tool (y ahora
    también se sube a storage.py)."""
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, ys, label=f"f(x) = {f}")
    ax.plot(xs, dys, label=f"f'(x) = {derivada}", linestyle="--")
    ax.axhline(0, color="black", linewidth=0.5)  # eje X de referencia
    ax.axvline(0, color="black", linewidth=0.5)  # eje Y de referencia
    ax.legend()
    ax.set_title("f(x) y su derivada")
    ax.grid(True, alpha=0.3)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)  # libera la figura de memoria; si no, se acumulan
    return buf.getvalue()
