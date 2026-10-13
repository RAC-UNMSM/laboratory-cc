"""Visualizacion: genera graficos PNG en memoria para los ejercicios que lo piden.

Rol "Visualizacion" (mismo patron que grupos/g01/semana01/derivadas1/): este
modulo NO sabe nada de MCP ni de red. Recibe expresiones de SymPy ya
validadas y devuelve los bytes de un PNG. `server.py` decide cuando graficar
y `storage.py` se encarga de subir el resultado a SeaweedFS.

Tres decisiones que no son obvias:

  - Backend "Agg": el contenedor no tiene pantalla. Sin esto matplotlib
    intenta abrir una ventana y falla.
  - API orientada a objetos (`Figure`), NO `pyplot`: pyplot guarda las
    figuras en un registro global y, si no se cierran a mano, se acumulan en
    RAM con cada llamada. Con `mem_limit: 512m` eso termina en un reinicio
    por OOM. Una `Figure` suelta se libera sola al salir de la funcion.
  - Nada se escribe en disco: el PNG va a un `io.BytesIO`. El contenedor no
    persiste archivos entre llamadas y no debe hacerlo.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import numpy as np  # noqa: E402  (despues de fijar el backend, a proposito)
import sympy as sp  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.mathtext import MathTextParser  # noqa: E402

PUNTOS_2D = 600   # resolucion de las curvas
PUNTOS_3D = 60    # malla de las superficies (60x60 es nitido y liviano)
FLECHAS = 18      # flechas por eje en los campos vectoriales
DPI = 110

_PARSER_MATH = MathTextParser("path")


class GraficoError(ValueError):
    """Error con un mensaje legible para el alumno (no un traceback)."""


# --- utilidades internas ------------------------------------------------------

def _evaluar(expr: sp.Expr, simbolos: list[sp.Symbol], *mallas: np.ndarray) -> np.ndarray:
    """Evalua `expr` sobre las mallas de numpy y devuelve un arreglo real.

    - Una constante (ej. "3") se expande a la forma de la malla.
    - Los valores complejos (ej. sqrt(x) con x < 0) quedan como NaN: fuera del
      dominio real no se dibuja nada, que es lo matematicamente correcto.
    """
    f = sp.lambdify(simbolos, expr, modules="numpy")
    with np.errstate(all="ignore"):
        valores = np.asarray(f(*mallas), dtype=complex)
    valores = np.broadcast_to(valores, mallas[0].shape)
    reales = np.where(np.abs(valores.imag) < 1e-9, valores.real, np.nan)
    reales[~np.isfinite(reales)] = np.nan
    return reales


def _limites_y(*series: np.ndarray) -> tuple[float, float] | None:
    """Rango vertical razonable, ignorando las explosiones cerca de asintotas."""
    datos = np.concatenate([s[np.isfinite(s)] for s in series]) if series else np.array([])
    if datos.size == 0:
        return None
    lo, hi = np.percentile(datos, [2, 98])
    if hi - lo < 1e-9:
        lo, hi = lo - 1.0, hi + 1.0
    margen = 0.15 * (hi - lo)
    return float(lo - margen), float(hi + margen)


def _cortar_asintotas(y: np.ndarray, limites: tuple[float, float] | None) -> np.ndarray:
    """Pone NaN muy fuera de la ventana para que no se dibuje la linea vertical
    falsa que une +inf con -inf en una asintota (ej. 1/x en x = 0)."""
    if limites is None:
        return y
    lo, hi = limites
    ancho = hi - lo
    y = y.copy()
    y[(y < lo - 3 * ancho) | (y > hi + 3 * ancho)] = np.nan
    return y


def _etiqueta(expr: sp.Expr) -> str:
    """LaTeX para la leyenda si matplotlib sabe dibujarlo; si no, texto plano."""
    candidato = f"${sp.latex(expr)}$"
    try:
        _PARSER_MATH.parse(candidato)
        return candidato
    except Exception:  # mathtext no soporta todo LaTeX (ej. \operatorname)
        return sp.sstr(expr)


def _a_png(fig: Figure) -> bytes:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, bbox_inches="tight")
    fig.clear()
    return buffer.getvalue()


def _sin_datos(*series: np.ndarray) -> bool:
    return all(not np.isfinite(s).any() for s in series)


# --- graficos -----------------------------------------------------------------

def funciones_2d(
    funciones: list[sp.Expr],
    x: sp.Symbol,
    x_min: float,
    x_max: float,
    sombrear: tuple[float, float] | None = None,
    marcar_x: list[float] | None = None,
    titulo: str | None = None,
) -> bytes:
    """Curvas y = f(x) en el plano (Calculo I y II).

    - `sombrear=(a, b)`: con una funcion sombrea el area bajo la curva; con dos
      o mas, el area ENTRE las dos primeras (problemas de area de Calculo II).
    - `marcar_x`: abscisas a resaltar sobre la PRIMERA funcion (puntos
      criticos, punto de tangencia, extremos del intervalo...).
    """
    xs = np.linspace(x_min, x_max, PUNTOS_2D)
    ys = [_evaluar(f, [x], xs) for f in funciones]
    if _sin_datos(*ys):
        raise GraficoError("ninguna funcion tiene valores reales en el intervalo pedido")
    limites = _limites_y(*ys)

    fig = Figure(figsize=(7, 4.5))
    ax = fig.add_subplot()
    for f, y in zip(funciones, ys):
        ax.plot(xs, _cortar_asintotas(y, limites), linewidth=2, label=_etiqueta(f))

    if sombrear is not None:
        a, b = sombrear
        zona = (xs >= min(a, b)) & (xs <= max(a, b))
        superior = ys[0]
        inferior = ys[1] if len(ys) > 1 else np.zeros_like(xs)
        ax.fill_between(xs, inferior, superior, where=zona, alpha=0.3,
                        interpolate=True, label="region")
        ax.axvline(a, color="gray", linestyle=":", linewidth=1)
        ax.axvline(b, color="gray", linestyle=":", linewidth=1)

    for x0 in marcar_x or []:
        y0 = _evaluar(funciones[0], [x], np.array([x0]))[0]
        if np.isfinite(y0):
            ax.plot([x0], [y0], "o", color="red", zorder=5)
            ax.annotate(f"({x0:.3g}, {y0:.3g})", (x0, y0),
                        textcoords="offset points", xytext=(6, 6), fontsize=9)

    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    if limites is not None:
        ax.set_ylim(*limites)
    ax.set_xlim(x_min, x_max)
    ax.set_xlabel(str(x))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    if titulo:
        ax.set_title(titulo)
    return _a_png(fig)


def superficie_3d(
    f: sp.Expr,
    x: sp.Symbol,
    y: sp.Symbol,
    rango_x: tuple[float, float],
    rango_y: tuple[float, float],
    plano: sp.Expr | None = None,
    punto: tuple[float, float, float] | None = None,
    titulo: str | None = None,
) -> bytes:
    """Superficie z = f(x, y), con su plano tangente opcional (Calculo III)."""
    xs = np.linspace(*rango_x, PUNTOS_3D)
    ys = np.linspace(*rango_y, PUNTOS_3D)
    X, Y = np.meshgrid(xs, ys)
    Z = _evaluar(f, [x, y], X, Y)
    if _sin_datos(Z):
        raise GraficoError("la superficie no tiene valores reales en la region pedida")

    fig = Figure(figsize=(7, 5.5))
    ax = fig.add_subplot(projection="3d")
    ax.plot_surface(X, Y, Z, cmap="viridis", alpha=0.85, linewidth=0)

    if plano is not None and punto is not None:
        # El plano se dibuja solo alrededor del punto: extendido a toda la
        # region tapa la superficie y no se ve la tangencia.
        x0, y0, _ = punto
        dx = (rango_x[1] - rango_x[0]) / 4
        dy = (rango_y[1] - rango_y[0]) / 4
        PX, PY = np.meshgrid(np.linspace(x0 - dx, x0 + dx, 12),
                             np.linspace(y0 - dy, y0 + dy, 12))
        PZ = _evaluar(plano, [x, y], PX, PY)
        ax.plot_surface(PX, PY, PZ, color="orange", alpha=0.6, linewidth=0)
    if punto is not None:
        ax.scatter([punto[0]], [punto[1]], [punto[2]], color="red", s=40, depthshade=False)

    ax.set_xlabel(str(x))
    ax.set_ylabel(str(y))
    ax.set_zlabel("z")
    ax.set_title(titulo or _etiqueta(f))
    return _a_png(fig)


def curva_parametrica(
    componentes: list[sp.Expr],
    t: sp.Symbol,
    t_min: float,
    t_max: float,
    titulo: str | None = None,
) -> bytes:
    """Curva r(t) en el plano (2 componentes) o en el espacio (3 componentes).

    Marca el punto inicial y una flecha con el sentido de recorrido, que es
    lo que importa en integrales de linea y en el Teorema de Green.
    """
    ts = np.linspace(t_min, t_max, PUNTOS_2D)
    puntos = [_evaluar(c, [t], ts) for c in componentes]
    if _sin_datos(*puntos):
        raise GraficoError("la curva no tiene valores reales en el intervalo del parametro")

    fig = Figure(figsize=(6.5, 5.5))
    if len(componentes) == 3:
        ax = fig.add_subplot(projection="3d")
        ax.plot(*puntos, linewidth=2)
        ax.scatter(*[[p[0]] for p in puntos], color="green", s=40, label="inicio")
        ax.set_zlabel("z")
    else:
        ax = fig.add_subplot()
        ax.plot(*puntos, linewidth=2)
        ax.plot(puntos[0][0], puntos[1][0], "o", color="green", label="inicio")
        medio = len(ts) // 2
        ax.annotate("", xy=(puntos[0][medio + 1], puntos[1][medio + 1]),
                    xytext=(puntos[0][medio], puntos[1][medio]),
                    arrowprops={"arrowstyle": "->", "color": "red", "lw": 2})
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, alpha=0.3)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(loc="best", fontsize=9)
    ax.set_title(titulo or "r(t) = (" + ", ".join(sp.sstr(c) for c in componentes) + ")")
    return _a_png(fig)


def campo_vectorial_2d(
    P: sp.Expr,
    Q: sp.Expr,
    x: sp.Symbol,
    y: sp.Symbol,
    rango_x: tuple[float, float],
    rango_y: tuple[float, float],
    curva: tuple[sp.Expr, sp.Expr, sp.Symbol, float, float] | None = None,
    titulo: str | None = None,
) -> bytes:
    """Campo F = (P, Q) con flechas, y opcionalmente una curva orientada
    encima (Calculo IV: integrales de linea, campos conservativos, Green).

    Las flechas se normalizan (todas del mismo largo) y el color indica la
    magnitud: si no, una zona donde |F| es grande tapa todo el resto.
    """
    xs = np.linspace(*rango_x, FLECHAS)
    ys = np.linspace(*rango_y, FLECHAS)
    X, Y = np.meshgrid(xs, ys)
    U = _evaluar(P, [x, y], X, Y)
    V = _evaluar(Q, [x, y], X, Y)
    if _sin_datos(U, V):
        raise GraficoError("el campo no tiene valores reales en la region pedida")
    magnitud = np.hypot(U, V)
    with np.errstate(all="ignore"):
        Un = np.where(magnitud > 0, U / magnitud, 0.0)
        Vn = np.where(magnitud > 0, V / magnitud, 0.0)

    fig = Figure(figsize=(6.5, 5.5))
    ax = fig.add_subplot()
    flechas = ax.quiver(X, Y, Un, Vn, magnitud, cmap="viridis", pivot="mid")
    fig.colorbar(flechas, ax=ax, label="|F|")

    if curva is not None:
        cx, cy, t, t0, t1 = curva
        ts = np.linspace(t0, t1, PUNTOS_2D)
        px, py = _evaluar(cx, [t], ts), _evaluar(cy, [t], ts)
        ax.plot(px, py, color="red", linewidth=2, label="curva C")
        medio = len(ts) // 2
        ax.annotate("", xy=(px[medio + 1], py[medio + 1]), xytext=(px[medio], py[medio]),
                    arrowprops={"arrowstyle": "->", "color": "red", "lw": 2})
        ax.legend(loc="upper right", fontsize=9)

    ax.set_xlim(*rango_x)
    ax.set_ylim(*rango_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel(str(x))
    ax.set_ylabel(str(y))
    ax.set_title(titulo or f"F = ({sp.sstr(P)}, {sp.sstr(Q)})")
    return _a_png(fig)
