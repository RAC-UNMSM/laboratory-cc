"""Gráficas temporales de las soluciones numéricas."""

from pathlib import Path

import matplotlib

# La demo guarda PNGs y no requiere una ventana gráfica (útil en VS Code/terminal).
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from modelo_edos import resolver_edo


def graficar_solucion(solucion, nombre_variables=None, titulo="Solución numérica",
                     archivo_salida="solucion_edo.png", mostrar=False):
    """Guarda la gráfica de cada variable y devuelve la ruta del archivo."""
    n = solucion.y.shape[0]
    nombres = nombre_variables or [f"x{i + 1}" for i in range(n)]
    if len(nombres) != n:
        raise ValueError("Debe indicar un nombre por variable.")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, nombre in enumerate(nombres):
        ax.plot(solucion.t, solucion.y[i], label=nombre)
    ax.set(title=titulo, xlabel="t", ylabel="Estado")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    destino = Path(archivo_salida).resolve()
    fig.savefig(destino, dpi=140)
    if mostrar:
        plt.show()
    plt.close(fig)
    return destino


def graficar_retrato_fase_1d(modelo, equilibrios, parametros, intervalo_x,
                             intervalo_t, puntos_iniciales, archivo_salida):
    """Dibuja la línea de fase (flechas y equilibrios) y trayectorias 1D.

    Las flechas indican hacia dónde se mueve x. Los puntos verdes son
    atractores estables y los rojos equilibrios inestables.
    """
    xmin, xmax = intervalo_x
    xs = np.linspace(xmin, xmax, 29)
    valores = np.asarray([modelo(0.0, [x], parametros)[0] for x in xs], dtype=float)
    fig, (ax_fase, ax_tray) = plt.subplots(2, 1, figsize=(8, 6),
                                           gridspec_kw={"height_ratios": [1, 2]})

    # Línea de fase con flechas horizontales; los puntos se desplazan un poco
    # verticalmente para que se distingan sin alterar el eje de estado.
    ax_fase.axhline(0, color="black", linewidth=1)
    for x, dx in zip(xs, valores):
        if abs(dx) < 1e-10:
            continue
        direccion = np.sign(dx)
        longitud = 0.16 * (xmax - xmin)
        ax_fase.annotate("", xy=(x + direccion*longitud/2, 0),
                         xytext=(x - direccion*longitud/2, 0),
                         arrowprops={"arrowstyle": "->", "color": "#3569a8", "lw": 1.5})
    for eq in equilibrios:
        xeq = float(np.atleast_1d(eq)[0])
        eps = 1e-4 * max(1.0, abs(xeq))
        f_izq = modelo(0.0, [xeq-eps], parametros)[0]
        f_der = modelo(0.0, [xeq+eps], parametros)[0]
        estable = f_izq > 0 and f_der < 0
        color = "#2e8b57" if estable else "#c44747"
        ax_fase.scatter([xeq], [0], s=95, color=color, zorder=4)
        ax_fase.annotate(f"x={xeq:g}\n{'atractor' if estable else 'inestable'}",
                         (xeq, 0), xytext=(0, 12), textcoords="offset points",
                         ha="center", fontsize=9, color=color)
    ax_fase.set_xlim(xmin, xmax)
    ax_fase.set_ylim(-0.35, 0.45)
    ax_fase.set_yticks([])
    ax_fase.set_xlabel("Estado x")
    ax_fase.set_title("Retrato de fase: las flechas muestran hacia dónde evoluciona x")
    ax_fase.grid(axis="x", alpha=0.2)

    for x0 in puntos_iniciales:
        sol = resolver_edo(modelo, [x0], intervalo_t, parametros, puntos=250)
        ax_tray.plot(sol.t, sol.y[0], label=f"Empieza en x(0)={x0:g}")
    for eq in equilibrios:
        xeq = float(np.atleast_1d(eq)[0])
        ax_tray.axhline(xeq, linestyle="--", linewidth=1, alpha=0.55,
                        label=f"Equilibrio x={xeq:g}")
    ax_tray.set(title="Trayectorias: cómo cambia x con el tiempo", xlabel="Tiempo t", ylabel="Estado x")
    ax_tray.grid(True, alpha=0.25)
    ax_tray.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    destino = Path(archivo_salida).resolve()
    fig.savefig(destino, dpi=150)
    plt.close(fig)
    return destino
