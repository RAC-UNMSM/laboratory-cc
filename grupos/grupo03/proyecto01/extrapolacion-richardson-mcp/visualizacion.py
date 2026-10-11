"""Gráficos (PNG en bytes) para convergencia, tablas de Richardson/Romberg y trayectorias."""
from __future__ import annotations

import io
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def grafico_convergencia(res: dict, titulo: str | None = None) -> bytes:
    """Error vs. h en escala log-log, antes y después de extrapolar."""
    hs = np.array(res["hs"], dtype=float)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for clave, etiqueta, marca in (("error_base", f"base ({res.get('base', 'método base')})", "o-"),
                                   ("error_extrapolado", "extrapolado (Richardson)", "s-")):
        e = np.array(res[clave], dtype=float)
        ok = e > 0
        ax.loglog(hs[ok], e[ok], marca, label=etiqueta)
    ax.set_xlabel("h")
    ax.set_ylabel("error absoluto")
    ax.set_title(titulo or "Convergencia: antes vs. después de extrapolar")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    return _png(fig)


def heatmap_tabla(tabla: list[list[float]], titulo: str = "Tabla de extrapolación") -> bytes:
    """Mapa de calor de log10 del error de cada celda respecto al valor final de la tabla."""
    n = len(tabla)
    final = tabla[-1][-1]
    M = np.full((n, n), np.nan)
    for i, fila in enumerate(tabla):
        for j, v in enumerate(fila):
            M[i, j] = math.log10(abs(v - final) + 1e-17)
    fig, ax = plt.subplots(figsize=(1.0 + 0.8 * n, 1.0 + 0.7 * n))
    im = ax.imshow(np.ma.masked_invalid(M), cmap="viridis_r", aspect="auto")
    for i in range(n):
        for j in range(i + 1):
            ax.text(j, i, f"{M[i, j]:.1f}", ha="center", va="center", fontsize=8, color="white")
    ax.set_xlabel("columna j (nivel de extrapolación)")
    ax.set_ylabel("fila i (h0 / 2^i)")
    ax.set_title(titulo)
    fig.colorbar(im, ax=ax, label="log10 |T[i][j] - resultado|")
    return _png(fig)


def grafico_trayectoria(t, y, titulo: str = "Solución numérica", exacta=None) -> bytes:
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    for k in range(y.shape[1]):
        ax.plot(t, y[:, k], "o-", ms=4, label=f"y{k + 1}(t)" if y.shape[1] > 1 else "Bulirsch-Stoer")
    if exacta is not None:
        tt = np.linspace(t[0], t[-1], 400)
        ax.plot(tt, [exacta(v) for v in tt], "--", color="gray", label="exacta")
    ax.set_xlabel("t")
    ax.set_ylabel("y")
    ax.set_title(titulo)
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _png(fig)
