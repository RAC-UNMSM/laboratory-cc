"""
core/visualizacion.py — Lógica CENTRALIZADA de gráficos.

Los métodos (``methods/``) solo devuelven objetos matemáticos; este módulo los convierte en:

* **Datos numéricos para graficar** (``datos_lagrange``, ``datos_hessiana``, ``datos_frenet``):
  mallas, curvas de restricción, flujo del gradiente, cuencas, triedro muestreado, etc.
  Son los arreglos que usan las plantillas web (Plotly.js) y que el MCP puede devolver.
* **Imágenes PNG** con matplotlib (``png_lagrange``, ``png_hessiana``, ``png_frenet``).
* Un **despachador** común: ``datos_grafico(metodo, objeto)`` y ``generar_png(metodo, objeto, ruta)``.

Paleta única (sobria, terracota) compartida con las plantillas HTML: ``PALETA`` y ``TERRA``.
"""
from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
import sympy as sp

from core.utils_math import num as _num, texto as _s, vnum as _vnum
from methods import metodo_hessiana as MH
from methods import metodo_lagrange as ML
from methods.metodo_frenet import CurvaFrenet
from methods.metodo_hessiana import ProblemaHessiana
from methods.metodo_lagrange import ProblemaLagrange

__all__ = ["datos_grafico", "generar_png", "datos_lagrange", "datos_hessiana", "datos_frenet",
           "png_lagrange", "png_hessiana", "png_frenet", "PALETA", "TERRA"]

Metodo = Literal["lagrange", "hessiana", "frenet"]

#: Colores semánticos (mismos valores que las variables CSS de templates/static/estilos.css).
PALETA: dict[str, str] = {
    "minimo": "#3f6e7d", "maximo": "#b0502c", "silla": "#7a5873", "indeterminado": "#8c8279",
    "singular": "#c38d35", "terracota": "#b0502c", "terracota_oscuro": "#8c3d20", "texto": "#2b2420",
}
TERRA: list[str] = ["#2c2420", "#4c2c21", "#7a3a24", "#ab4f2c", "#cf8660", "#e7bf9e", "#f7ece0"]
_TERRA = TERRA
PALETA_CUENCAS: list[str] = ["#3f6e7d", "#6b7a4f", "#a07b4f", "#5f6f8a", "#8a5a44", "#7a5873", "#4f7d6a"]


def _cmap_terra():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("terra", TERRA)


# ════════════════════════════════════════════════════════════════════════════
# Utilidades numéricas comunes
# ════════════════════════════════════════════════════════════════════════════
def _eval(fn, args, shape):
    with np.errstate(all="ignore"):
        try:
            r = np.asarray(fn(*args), dtype=complex)
        except Exception:  # noqa: BLE001
            return np.full(shape, np.nan)
    r = np.broadcast_to(r, shape)
    out = np.where(np.abs(r.imag) < 1e-9, r.real, np.nan).astype(float)
    out[~np.isfinite(out)] = np.nan
    return out


def _lista(a, dec=5):
    a = np.round(np.asarray(a, dtype=float), dec)
    if a.ndim == 1:
        return [None if not math.isfinite(x) else float(x) for x in a]
    return [_lista(fila, dec) for fila in a]


# ════════════════════════════════════════════════════════════════════════════
# Lagrange · datos para graficar
# ════════════════════════════════════════════════════════════════════════════
def _rango_lagrange(P: ProblemaLagrange, rango):
    n = P.n
    if rango:
        return [tuple(map(float, r)) for r in rango]
    pts = [[_num(p.coords[v]) for v in P.variables] for p in P.puntos + P.singulares]
    pts = [q for q in pts if all(c is not None for c in q)]
    out = []
    for i in range(n):
        if pts:
            c = [q[i] for q in pts]
            lo, hi = min(c), max(c)
            marg = max(1.5, 0.6 * (hi - lo))
            out.append((lo - marg, hi + marg))
        else:
            out.append((-3.0, 3.0))
    # misma escala en todos los ejes (así los círculos se ven círculos)
    ancho = max(b - a for a, b in out)
    return [((a + b) / 2 - ancho / 2, (a + b) / 2 + ancho / 2) for a, b in out]


def _proyectar_a_restriccion(P: ProblemaLagrange, caja, n_pts=6000, iters=40, semilla=0):
    """Muestrea puntos sobre {g = 0} proyectando puntos aleatorios con Newton
    (Gauss-Newton de norma mínima: x ← x − Jᵀ(JJᵀ)⁻¹ g). Sirve para cualquier m."""
    rng = np.random.default_rng(semilla)
    n = P.n
    lo = np.array([a for a, _ in caja]); hi = np.array([b for _, b in caja])
    X = lo + (hi - lo) * rng.random((n_pts, n))
    gf = [sp.lambdify(P.variables, g, "numpy") for g in P.restricciones]
    Jf = [[sp.lambdify(P.variables, sp.diff(g, v), "numpy") for v in P.variables]
          for g in P.restricciones]
    for _ in range(iters):
        args = [X[:, j] for j in range(n)]
        G = np.stack([_eval(fn, args, (len(X),)) for fn in gf], axis=1)          # N×m
        J = np.stack([np.stack([_eval(fn, args, (len(X),)) for fn in fila], axis=1)
                      for fila in Jf], axis=1)                                    # N×m×n
        ok = np.all(np.isfinite(G), axis=1) & np.all(np.isfinite(J), axis=(1, 2))
        X, G, J = X[ok], G[ok], J[ok]
        if len(X) == 0:
            break
        paso = np.einsum("pij,pj->pi", np.linalg.pinv(J), G)                    # N×n
        X = X - paso
    args = [X[:, j] for j in range(n)]
    G = np.stack([_eval(fn, args, (len(X),)) for fn in gf], axis=1)
    escala = float(np.max(hi - lo))
    dentro = np.all((X >= lo - 0.05 * escala) & (X <= hi + 0.05 * escala), axis=1)
    return X[np.all(np.abs(G) < 1e-7, axis=1) & dentro]


def datos_lagrange(P: ProblemaLagrange, rango=None, resolucion: int = 121) -> dict:
    """Genera arreglos numéricos listos para graficar en JS:
      n = 2 → malla de f (contorno y superficie), curvas g = 0, curvas elevadas
              sobre la superficie, puntos y vectores ∇f, ∇g (para ver que son paralelos).
      n = 3 → nube de puntos sobre la superficie/curva {g = 0} coloreada por f.
      n > 3 → solo los puntos (no hay gráfico geométrico)."""
    n = P.n
    vars_ = P.variables
    f_np = sp.lambdify(vars_, P.f, "numpy")
    puntos = []
    ids = [f"P{i + 1}" for i in range(len(P.puntos))] + [f"S{i + 1}" for i in range(len(P.singulares))]
    for pid, p in zip(ids, P.puntos + P.singulares):
        c = [_num(p.coords[v]) for v in vars_]
        if any(x is None for x in c):
            continue
        item = {"id": pid, "coords": c, "f": _num(p.valor_f), "tipo": p.tipo,
                "clasificacion": p.clasificacion, "global": p.global_,
                "etiqueta": "(" + ", ".join(str(p.coords[v]) for v in vars_) + ")"}
        gf = [_num(sp.diff(P.f, v).subs(p.coords)) for v in vars_]
        gg = [[_num(sp.diff(g, v).subs(p.coords)) for v in vars_] for g in P.restricciones]
        item["grad_f"], item["grad_g"] = gf, gg
        puntos.append(item)

    base = {"n": n, "variables": [str(v) for v in vars_], "f": str(P.f),
            "restricciones": [str(g) for g in P.restricciones], "puntos": puntos}
    if n > 3:
        base["tipo"] = "sin_grafico"
        return base
    caja = _rango_lagrange(P, rango)
    base["rango"] = [list(r) for r in caja]

    if n == 2:
        (x0, x1), (y0, y1) = caja
        xs = np.linspace(x0, x1, resolucion); ys = np.linspace(y0, y1, resolucion)
        X, Y = np.meshgrid(xs, ys)
        Z = _eval(f_np, (X, Y), X.shape)
        curvas = []
        try:
            import contourpy
            for g in P.restricciones:
                Gm = _eval(sp.lambdify(vars_, g, "numpy"), (X, Y), X.shape)
                gen = contourpy.contour_generator(xs, ys, np.nan_to_num(Gm, nan=1e30),
                                                  line_type=contourpy.LineType.Separate)
                for seg in gen.lines(0.0):
                    if len(seg) < 2:
                        continue
                    zf = _eval(f_np, (seg[:, 0], seg[:, 1]), (len(seg),))
                    curvas.append({"restriccion": str(g), "x": _lista(seg[:, 0]),
                                   "y": _lista(seg[:, 1]), "z": _lista(zf)})
        except ImportError:
            pts = _proyectar_a_restriccion(P, caja)
            zf = _eval(f_np, (pts[:, 0], pts[:, 1]), (len(pts),))
            curvas.append({"restriccion": "g=0 (muestreo)", "x": _lista(pts[:, 0]),
                           "y": _lista(pts[:, 1]), "z": _lista(zf), "dispersa": True})
        fin = np.sort(Z[np.isfinite(Z)])
        if len(fin):          # escala de color por cuantiles (resalta el detalle)
            zr = np.where(np.isfinite(Z), np.searchsorted(fin, Z, side="right") / len(fin), np.nan)
            qs = np.linspace(0, 1, 9)
            base.update({"z_rango": _lista(zr, 4), "ticks_color": {
                "vals": [float(q) for q in qs], "text": [f"{v:.3g}" for v in np.quantile(fin, qs)]}})
        base.update({"tipo": "2d", "x": _lista(xs), "y": _lista(ys), "z": _lista(Z),
                     "curvas_restriccion": curvas,
                     "niveles_criticos": sorted({round(p["f"], 8) for p in puntos
                                                 if p["f"] is not None})})
        return base

    # n == 3
    pts = _proyectar_a_restriccion(P, caja)
    if len(pts) > 4000:
        pts = pts[:: int(math.ceil(len(pts) / 4000))]
    fv = _eval(f_np, tuple(pts[:, j] for j in range(3)), (len(pts),))
    mv = 26                   # volumen de f para las superficies de nivel f = c
    ejes = [np.linspace(a, b, mv) for a, b in caja]
    VX, VY, VZ = np.meshgrid(*ejes, indexing="ij")
    base["vol"] = {"ejes": [_lista(e, 4) for e in ejes], "valor": _lista(_eval(f_np, (VX, VY, VZ), VX.shape).ravel(), 5)}
    base.update({"tipo": "3d_nube", "x": _lista(pts[:, 0]), "y": _lista(pts[:, 1]),
                 "z": _lista(pts[:, 2]), "f_en_restriccion": _lista(fv),
                 "descripcion": ("Superficie g = 0" if P.m == 1 else "Curva intersección g1 = g2 = 0")})
    return base


# ════════════════════════════════════════════════════════════════════════════
# Lagrange · PNG
# ════════════════════════════════════════════════════════════════════════════
_COLOR_L = {ML.MAX_LOCAL: "#b0502c", ML.MIN_LOCAL: "#3f6e7d", ML.SILLA: "#7a5873"}
def _color_l(p):
    if p["tipo"] == "singular":
        return "#c38d35"
    return _COLOR_L.get(p["clasificacion"], "#8c8279")


def png_lagrange(P: ProblemaLagrange, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    D = datos or datos_lagrange(P)
    titulo = f"f = {_s(P.f)}   s.a.  " + ",  ".join(f"{_s(g)} = 0" for g in P.restricciones)
    if D["tipo"] == "2d":
        xs, ys = np.array(D["x"]), np.array(D["y"])
        Z = np.array(D["z"], dtype=float)
        X, Y = np.meshgrid(xs, ys)
        fig = plt.figure(figsize=(14, 6.2))
        ax = fig.add_subplot(1, 2, 1)
        cf = ax.contourf(X, Y, Z, levels=30, cmap=_cmap_terra(), alpha=0.85)
        fig.colorbar(cf, ax=ax, label="f(x, y)")
        if D["niveles_criticos"]:
            niv = sorted(set(D["niveles_criticos"]))
            try:
                cs = ax.contour(X, Y, Z, levels=niv, colors="white", linestyles="--", linewidths=1.2)
                ax.clabel(cs, fmt="f=%.3g", fontsize=8)
            except ValueError:
                pass
        for c in D["curvas_restriccion"]:
            estilo = dict(color="black", lw=2.6) if not c.get("dispersa") else dict(color="black", s=2)
            (ax.scatter if c.get("dispersa") else ax.plot)(c["x"], c["y"], **estilo)
        ancho = (D["rango"][0][1] - D["rango"][0][0]) * 0.12
        for p in D["puntos"]:
            (px, py), col = p["coords"], _color_l(p)
            ax.plot(px, py, "o", ms=11, color=col, mec="white", mew=2, zorder=5)
            for vec, cl, lw in [(g, "#3f6e7d", 4.5) for g in p["grad_g"]] + \
                               [(p["grad_f"], "#e0a64a", 2.0)]:
                nv = math.hypot(*(vec if None not in vec else [0, 0]))
                if nv > 1e-12:
                    ax.annotate("", xy=(px + ancho * vec[0] / nv, py + ancho * vec[1] / nv),
                                xytext=(px, py),
                                arrowprops=dict(arrowstyle="->", color=cl, lw=lw), zorder=6)
            ax.annotate(f"{p['etiqueta']}\nf={p['f']:.4g}", (px, py), textcoords="offset points",
                        xytext=(8, 8), fontsize=8, color="white",
                        bbox=dict(boxstyle="round", fc=col, alpha=0.85))
        ax.set_xlim(*D["rango"][0]); ax.set_ylim(*D["rango"][1]); ax.set_aspect("equal")
        ax.set_xlabel(D["variables"][0]); ax.set_ylabel(D["variables"][1])
        ax.set_title("Curvas de nivel de f, restricción (negro)\n"
                     "flechas: ∇f (ocre) ∥ ∇g (petróleo) en los puntos críticos", fontsize=10)

        ax3 = fig.add_subplot(1, 2, 2, projection="3d", computed_zorder=False)
        ax3.plot_surface(X, Y, np.ma.masked_invalid(Z), cmap=_cmap_terra(), alpha=0.55,
                         linewidth=0, rstride=3, cstride=3)
        for c in D["curvas_restriccion"]:
            z = np.array([np.nan if v is None else v for v in c["z"]], dtype=float)
            ax3.plot(c["x"], c["y"], z, color="black", lw=2.5)
        for p in D["puntos"]:
            ax3.scatter(*p["coords"], p["f"], s=70, color=_color_l(p),
                        edgecolor="white", depthshade=False, zorder=10)
        ax3.set_xlabel(D["variables"][0]); ax3.set_ylabel(D["variables"][1]); ax3.set_zlabel("f")
        ax3.set_title("Superficie z = f(x, y) y la restricción elevada sobre ella", fontsize=10)
    elif D["tipo"] == "3d_nube":
        fig = plt.figure(figsize=(9, 7.5))
        ax3 = fig.add_subplot(1, 1, 1, projection="3d", computed_zorder=False)
        fv = np.array([np.nan if v is None else v for v in D["f_en_restriccion"]], dtype=float)
        sc = ax3.scatter(D["x"], D["y"], D["z"], c=fv, cmap=_cmap_terra(), s=3, alpha=0.35, zorder=1)
        fig.colorbar(sc, ax=ax3, shrink=0.7, label="valor de f sobre la restricción")
        for p in D["puntos"]:
            ax3.scatter(*p["coords"], s=160, color=_color_l(p), edgecolor="white",
                        linewidth=1.5, depthshade=False, zorder=10)
            ax3.text(*p["coords"], f"  {p['etiqueta']}\n  f={p['f']:.4g}", fontsize=9,
                     zorder=11, bbox=dict(boxstyle="round", fc="white", alpha=0.8))
        v = D["variables"]
        ax3.set_xlabel(v[0]); ax3.set_ylabel(v[1]); ax3.set_zlabel(v[2])
        ax3.set_title(f"{D['descripcion']} coloreada por f", fontsize=10)
    else:
        raise ValueError("Con más de 3 variables no hay representación geométrica.")
    from matplotlib.lines import Line2D
    leyenda = [Line2D([0], [0], marker="o", ls="", color=c, label=l, ms=9) for l, c in
               [("máximo local", _COLOR_L[ML.MAX_LOCAL]), ("mínimo local", _COLOR_L[ML.MIN_LOCAL]),
                ("silla", _COLOR_L[ML.SILLA]), ("no concluyente", "#8c8279"),
                ("singular (∇g=0)", "#c38d35")]]
    fig.legend(handles=leyenda, loc="lower center", ncol=5, fontsize=9, frameon=False)
    fig.suptitle(titulo, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(ruta, dpi=dpi)
    plt.close(fig)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# Hessiana · datos para graficar
# ════════════════════════════════════════════════════════════════════════════
def _rango_hessiana(P, rango, igualar=True):
    if rango:
        return [tuple(map(float, r)) for r in rango]
    pts = [[_num(p.coords[v]) for v in P.variables] for p in P.todos]
    pts = [q for q in pts if all(c is not None for c in q)]
    out = []
    for i in range(P.n):
        if pts:
            c = [q[i] for q in pts]
            lo, hi = min(c), max(c)
            marg = max(1.5, 0.6 * (hi - lo))
            out.append((lo - marg, hi + marg))
        else:
            out.append((-3.0, 3.0))
    if not igualar:
        return out
    ancho = max(b - a for a, b in out)
    return [((a + b) / 2 - ancho / 2, (a + b) / 2 + ancho / 2) for a, b in out]


def _flujo(gx, gy, caja, minimos, n_sem=11, pasos=700):
    """Líneas de descenso del gradiente (x' = −∇f/‖∇f‖), integradas con RK4.
    Cada línea se etiqueta con el mínimo al que llega → cuencas de atracción."""
    (x0, x1), (y0, y1) = caja
    w = x1 - x0
    h = w / 180
    xs = np.linspace(x0 + w / (2 * n_sem), x1 - w / (2 * n_sem), n_sem)
    ys = np.linspace(y0 + w / (2 * n_sem), y1 - w / (2 * n_sem), n_sem)
    S = np.array([(a, b) for a in xs for b in ys], dtype=float)

    def F(Q):
        g = np.stack([_eval(gx, (Q[:, 0], Q[:, 1]), (len(Q),)),
                      _eval(gy, (Q[:, 0], Q[:, 1]), (len(Q),))], axis=1)
        nr = np.linalg.norm(g, axis=1, keepdims=True)
        with np.errstate(all="ignore"):
            return -g / nr, nr[:, 0]

    X = S.copy()
    vivo = np.ones(len(X), bool)
    caminos = [[tuple(p)] for p in X]
    dir_prev = np.zeros_like(X)
    M = np.array(minimos, dtype=float).reshape(-1, 2)
    for _ in range(pasos):
        if not vivo.any():
            break
        idx = np.where(vivo)[0]
        Q = X[idx]
        k1, nr = F(Q)
        k2, _ = F(Q + h / 2 * k1)
        k3, _ = F(Q + h / 2 * k2)
        k4, _ = F(Q + h * k3)
        paso = h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        malos = ~np.all(np.isfinite(paso), axis=1) | (nr < 1e-9)
        giro = np.einsum("ij,ij->i", k1, dir_prev[idx]) < -0.5
        Qn = Q + np.where(malos[:, None], 0, paso)
        fuera = (Qn[:, 0] < x0) | (Qn[:, 0] > x1) | (Qn[:, 1] < y0) | (Qn[:, 1] > y1)
        cerca = np.zeros(len(Q), bool)
        if len(M):
            dmin = np.min(np.linalg.norm(Qn[:, None, :] - M[None, :, :], axis=2), axis=1)
            cerca = dmin < 1.5 * h
        for j, i in enumerate(idx):
            if not malos[j] and not fuera[j]:
                caminos[i].append(tuple(Qn[j]))
        X[idx] = Qn
        dir_prev[idx] = np.where(np.isfinite(k1), k1, 0)
        vivo[idx[malos | fuera | cerca | giro]] = False
    lineas = []
    for c in caminos:
        if len(c) < 4:
            continue
        A = np.array(c)
        destino = None
        if len(M):
            d = np.linalg.norm(M - A[-1], axis=1)
            if d.min() < 4 * h:
                destino = int(d.argmin())
        A = A[::3] if len(A) > 6 else A
        lineas.append({"x": _lista(A[:, 0], 4), "y": _lista(A[:, 1], 4), "destino": destino})
    return lineas


def datos_hessiana(P: ProblemaHessiana, rango=None, resolucion: int = 121) -> dict:
    """Arreglos listos para JS/Plotly:
      n=1 → curva y = f(x);  n=2 → malla de f, flujo del gradiente, mapa de D, Taylor local;
      n=3 → volumen de f para isosuperficies;  n>3 → solo puntos."""
    vars_, n = P.variables, P.n
    fnp = sp.lambdify(vars_, P.f, "numpy")
    puntos = []
    for i, p in enumerate(P.todos):
        c = [_num(p.coords[v]) for v in vars_]
        if any(x is None for x in c):
            continue
        it = {"id": f"P{i + 1}", "coords": c, "f": _num(p.valor_f), "tipo": p.tipo,
              "clasificacion": p.clasificacion, "certeza": p.certeza, "global": p.global_,
              "etiqueta": "(" + ", ".join(_s(p.coords[v]) for v in vars_) + ")"}
        testigos = []
        for c in p.orden_superior.get("_testigos", []):
            fns = [sp.lambdify(c["_t"], g, "numpy") for g in c["_gamma"]]
            testigos.append({"curva": c["curva"], "comportamiento": c["comportamiento"], "fns": fns})
        if testigos:
            it["_testigos"] = testigos
        if p.hessiana is not None and p.autovectores:
            it["autovalores"] = p.verif_autovalores.get("valores")
            it["autovectores"] = p.autovectores
            try:
                it["hessiana_num"] = np.array(p.hessiana.evalf(), dtype=float).tolist()
            except (TypeError, ValueError):
                pass
        puntos.append(it)
    base = {"n": n, "variables": [str(v) for v in vars_], "f": _s(P.f), "puntos": puntos}
    if n > 3:
        base["tipo"] = "sin_grafico"
        return base
    caja = _rango_hessiana(P, rango, igualar=(n == 2))
    base["rango"] = [list(r) for r in caja]

    if n == 1:
        xs = np.linspace(*caja[0], 600)
        base.update({"tipo": "1d", "x": _lista(xs), "y": _lista(_eval(fnp, (xs,), xs.shape))})
        return base

    if n == 2:
        (x0, x1), (y0, y1) = caja
        xs, ys = np.linspace(x0, x1, resolucion), np.linspace(y0, y1, resolucion)
        X, Y = np.meshgrid(xs, ys)
        Z = _eval(fnp, (X, Y), X.shape)
        gx = sp.lambdify(vars_, P.gradiente[0], "numpy")
        gy = sp.lambdify(vars_, P.gradiente[1], "numpy")
        H = P.hessiana_general
        fxx = _eval(sp.lambdify(vars_, H[0, 0], "numpy"), (X, Y), X.shape)
        fyy = _eval(sp.lambdify(vars_, H[1, 1], "numpy"), (X, Y), X.shape)
        fxy = _eval(sp.lambdify(vars_, H[0, 1], "numpy"), (X, Y), X.shape)
        Dm = fxx * fyy - fxy ** 2
        esc = np.nanmax(np.abs(Dm)) if np.any(np.isfinite(Dm)) else 1.0
        clase = np.where(np.abs(Dm) < 1e-9 * max(esc, 1.0), 0.0,
                         np.where(Dm < 0, -1.0, np.where(fxx > 0, 1.0, 2.0)))
        clase[~np.isfinite(Dm)] = np.nan
        minimos = [q["coords"] for q in puntos if q["clasificacion"] == MH.MIN_LOCAL]
        flujo = _flujo(gx, gy, caja, minimos)
        for ln in flujo:          # altura de cada línea de flujo sobre la superficie (bolitas 3D)
            lx = np.array([np.nan if v is None else v for v in ln["x"]], dtype=float)
            ly = np.array([np.nan if v is None else v for v in ln["y"]], dtype=float)
            ln["z"] = _lista(_eval(fnp, (lx, ly), lx.shape), 5)
        # curvas principales: f a lo largo de cada autovector de H (curvatura + / −)
        for q in puntos:
            if not q.get("autovectores"):
                continue
            r = (x1 - x0) * 0.22
            ss = np.linspace(-r, r, 41)
            q["curvas_principales"] = []
            for lam, vec in zip(q["autovalores"], q["autovectores"]):
                cx, cy = q["coords"][0] + ss * vec[0], q["coords"][1] + ss * vec[1]
                q["curvas_principales"].append({"lam": lam, "x": _lista(cx, 4), "y": _lista(cy, 4),
                                                "z": _lista(_eval(fnp, (cx, cy), cx.shape), 5)})
        # aproximación cuadrática de Taylor en cada punto estacionario
        for q in puntos:
            Hn = q.get("hessiana_num")
            if Hn is None:
                continue
            r = (x1 - x0) * 0.2
            u = np.linspace(-r, r, 23)
            U, V = np.meshgrid(u, u)
            Zq = q["f"] + 0.5 * (Hn[0][0] * U ** 2 + 2 * Hn[0][1] * U * V + Hn[1][1] * V ** 2)
            q["taylor"] = {"x": _lista(q["coords"][0] + u), "y": _lista(q["coords"][1] + u), "z": _lista(Zq)}
        for q in puntos:
            lst = []
            for c in q.pop("_testigos", []):
                ts = np.linspace(-(x1 - x0) * 0.6, (x1 - x0) * 0.6, 300)
                cx = _eval(c["fns"][0], (ts,), ts.shape)
                cy = _eval(c["fns"][1], (ts,), ts.shape)
                ok = (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
                cx, cy = np.where(ok, cx, np.nan), np.where(ok, cy, np.nan)
                lst.append({"curva": c["curva"], "comportamiento": c["comportamiento"],
                            "x": _lista(cx, 4), "y": _lista(cy, 4)})
            if lst:
                q["curvas_testigo"] = lst
        fams = []
        for fa in P.familias:
            if len(fa["parametros"]) == 1:
                t = fa["parametros"][0]
                idx = vars_.index(t) if t in vars_ else 0
                ts = np.linspace(*caja[idx], 200)
                cols = []
                for v in vars_:
                    fn_ = sp.lambdify(t, fa["expr"][v], "numpy")
                    cols.append(_eval(fn_, (ts,), ts.shape))
                fams.append({"x": _lista(cols[0]), "y": _lista(cols[1]),
                             "z": _lista(_eval(fnp, (cols[0], cols[1]), ts.shape))})
        # escala de color por cuantiles (ECDF): resalta el detalle sin falsear los valores
        fin = np.sort(Z[np.isfinite(Z)])
        if len(fin):
            zr = np.where(np.isfinite(Z), np.searchsorted(fin, Z, side="right") / len(fin), np.nan)
            qs = np.linspace(0, 1, 9)
            ticks = {"vals": [float(q) for q in qs],
                     "text": [f"{v:.3g}" for v in np.quantile(fin, qs)]}
        else:
            zr, ticks = Z, None
        base.update({"z_rango": _lista(zr, 4), "ticks_color": ticks})
        base.update({"tipo": "2d", "x": _lista(xs), "y": _lista(ys), "z": _lista(Z),
                     "clase_D": _lista(clase, 0), "flujo": flujo, "familias": fams,
                     "niveles_criticos": sorted({round(q["f"], 8) for q in puntos if q["f"] is not None})})
        return base

    # n == 3: volumen
    m = 30
    ejes = [np.linspace(a, b, m) for a, b in caja]
    X, Y, Zg = np.meshgrid(*ejes, indexing="ij")
    V = _eval(fnp, (X, Y, Zg), X.shape)
    cortes = []               # cortes planos EXACTOS por cada punto crítico (x = x0, y = y0, z = z0)
    for q in (puntos or [{"coords": [(a + b) / 2 for a, b in caja]}]):
        c, item = q["coords"], []
        for fijo, ia, ib in [(2, 0, 1), (1, 0, 2), (0, 1, 2)]:
            A, B = np.linspace(*caja[ia], 61), np.linspace(*caja[ib], 61)
            AA, BB = np.meshgrid(A, B)
            args = [None] * 3
            args[ia], args[ib], args[fijo] = AA, BB, np.full_like(AA, c[fijo])
            item.append({"fijo": fijo, "a": ia, "b": ib, "valor_fijo": c[fijo], "A": _lista(A, 4), "B": _lista(B, 4),
                         "z": _lista(_eval(fnp, args, AA.shape), 5)})
        cortes.append(item)
    base["cortes"] = cortes
    base.update({"tipo": "3d_volumen", "ejes": [_lista(e, 4) for e in ejes], "valor": _lista(V.ravel(), 5),
                 "niveles_criticos": sorted({round(q["f"], 8) for q in puntos if q["f"] is not None})})
    return base


# ════════════════════════════════════════════════════════════════════════════
# Hessiana · PNG
# ════════════════════════════════════════════════════════════════════════════
_COLOR_H = {MH.MIN_LOCAL: "#3f6e7d", MH.MAX_LOCAL: "#b0502c", MH.SILLA: "#7a5873",
           MH.INDETERMINADO: "#8c8279", MH.DUDOSO: "#8c8279"}
def _color_h(p):
    if p["tipo"] == "no diferenciable":
        return "#c38d35"
    return _COLOR_H.get(p["clasificacion"], "#8c8279")


def png_hessiana(P: ProblemaHessiana, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D

    D = datos or datos_hessiana(P)
    titulo = f"f({', '.join(D['variables'])}) = {_s(P.f)}"
    if D["tipo"] == "1d":
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(D["x"], [np.nan if v is None else v for v in D["y"]], color="#2b2420", lw=2)
        for p in D["puntos"]:
            ax.plot(p["coords"][0], p["f"], "o", ms=11, color=_color_h(p), mec="white", mew=2)
            ax.annotate(f"{p['etiqueta']}\n{p['clasificacion']}", (p["coords"][0], p["f"]),
                        textcoords="offset points", xytext=(8, 8), fontsize=9)
        ax.grid(alpha=0.3)
    elif D["tipo"] == "2d":
        (x0, x1), (y0, y1) = D["rango"]
        xs, ys = np.linspace(x0, x1, len(D["x"])), np.linspace(y0, y1, len(D["y"]))
        X, Y = np.meshgrid(xs, ys)
        Z = np.array(D["z"], dtype=float)
        # niveles por cuantiles: resaltan el detalle cerca de los puntos críticos
        niveles = np.unique(np.nanquantile(Z, np.linspace(0, 1, 42))) if np.isfinite(Z).any() else 30
        if not np.isscalar(niveles) and len(niveles) < 3:
            niveles = 30
        fig = plt.figure(figsize=(16, 13))
        # (a) curvas de nivel + flujo
        ax = fig.add_subplot(2, 2, 1)
        cf = ax.contourf(X, Y, Z, levels=niveles, cmap=_cmap_terra(), alpha=0.9)
        fig.colorbar(cf, ax=ax, label="f (niveles por cuantiles)", format="%.3g")
        try:
            ax.contour(X, Y, Z, levels=niveles, colors="white", linewidths=0.35, alpha=0.45)
        except ValueError:
            pass
        gx = sp.lambdify(P.variables, P.gradiente[0], "numpy")
        gy = sp.lambdify(P.variables, P.gradiente[1], "numpy")
        U, V = -_eval(gx, (X, Y), X.shape), -_eval(gy, (X, Y), X.shape)
        try:
            ax.streamplot(xs, ys, np.nan_to_num(U), np.nan_to_num(V), color=(1, 1, 1, 0.75),
                          density=1.4, linewidth=0.9, arrowsize=1.0, zorder=3)
        except Exception as e:  # noqa: BLE001
            print("(aviso: no se pudo dibujar el flujo:", e, ")")
        if D.get("niveles_criticos"):
            try:
                cs = ax.contour(X, Y, Z, levels=sorted(set(D["niveles_criticos"])), colors="black",
                                linewidths=1.6, linestyles="--", zorder=4)
                ax.clabel(cs, fmt="f=%.3g", fontsize=8)
            except ValueError:
                pass
        for p in D["puntos"]:
            for c in p.get("curvas_testigo", []):
                cc = {"sube": "#6b7a4f", "baja": "#b0502c"}.get(c["comportamiento"], "#c38d35")
                ax.plot([np.nan if v is None else v for v in c["x"]], [np.nan if v is None else v for v in c["y"]],
                        color=cc, lw=2.5, zorder=5, label=f"{c['curva']} ({c['comportamiento']})")
        if any(p.get("curvas_testigo") for p in D["puntos"]):
            ax.legend(loc="lower left", fontsize=7, framealpha=0.85)
        L = (xs[-1] - xs[0]) * 0.07
        for p in D["puntos"]:
            px, py = p["coords"]
            for val, vec in zip(p.get("autovalores") or [], p.get("autovectores") or []):
                c = "#e0a64a" if val > 0 else "#3f6e7d" if val < 0 else "#bdb2a6"
                ax.plot([px - L * vec[0], px + L * vec[0]], [py - L * vec[1], py + L * vec[1]],
                        color=c, lw=3, solid_capstyle="round", zorder=6)
            ax.plot(px, py, "o", ms=12, color=_color_h(p), mec="white", mew=2, zorder=7)
            ax.annotate(f"{p['id']} {p['etiqueta']}", (px, py), textcoords="offset points", xytext=(9, 9),
                        fontsize=8, color="white", bbox=dict(boxstyle="round", fc=_color_h(p), alpha=0.9))
        ax.set_xlim(xs[0], xs[-1]); ax.set_ylim(ys[0], ys[-1]); ax.set_aspect("equal")
        ax.set_xlabel(D["variables"][0]); ax.set_ylabel(D["variables"][1])
        ax.set_title("Curvas de nivel y flujo de descenso −∇f\n"
                     "ejes: direcciones principales de H (ocre λ>0 · petróleo λ<0) · "
                     "- - - nivel f = f(P)", fontsize=10)
        # (b) superficie 3D
        ax3 = fig.add_subplot(2, 2, 2, projection="3d", computed_zorder=False)
        ax3.plot_surface(X, Y, np.ma.masked_invalid(Z), cmap=_cmap_terra(), alpha=0.75, linewidth=0,
                         rstride=2, cstride=2, zorder=1)
        for p in D["puntos"]:
            ax3.scatter(*p["coords"], p["f"], s=90, color=_color_h(p), edgecolor="white", depthshade=False,
                        zorder=10)
        ax3.set_xlabel(D["variables"][0]); ax3.set_ylabel(D["variables"][1]); ax3.set_zlabel("f")
        ax3.set_title("Superficie z = f(x, y)", fontsize=10)
        # (c) mapa de D
        ax = fig.add_subplot(2, 2, 3)
        C = np.array(D["clase_D"], dtype=float)
        cmap = ListedColormap(["#d9c7d4", "#e6ddd2", "#bcd2d8", "#eec3ad"])
        ax.contour(X, Y, Z, levels=niveles, colors="k", linewidths=0.3, alpha=0.35)
        ax.pcolormesh(X, Y, C, cmap=cmap, vmin=-1.5, vmax=2.5, shading="auto")
        for p in D["puntos"]:
            ax.plot(*p["coords"], "o", ms=11, color=_color_h(p), mec="white", mew=2)
            ax.annotate(p["id"], p["coords"], textcoords="offset points", xytext=(8, 6), fontsize=9)
        ax.set_aspect("equal"); ax.set_xlabel(D["variables"][0]); ax.set_ylabel(D["variables"][1])
        ax.legend(handles=[Line2D([0], [0], marker="s", ls="", ms=12, color=c, label=l) for c, l in
                           [("#bcd2d8", "D>0, f_xx>0 (forma de cuenco ∪)"),
                            ("#eec3ad", "D>0, f_xx<0 (forma de cúpula ∩)"),
                            ("#d9c7d4", "D<0 (forma de silla)"), ("#e6ddd2", "D=0")]],
                  loc="upper right", fontsize=8, framealpha=0.9)
        ax.set_title("Mapa del discriminante D(x,y) = f_xx·f_yy − f_xy²", fontsize=10)
        # (d) tabla resumen
        ax = fig.add_subplot(2, 2, 4)
        ax.axis("off")
        filas = []
        for p, pc in zip(D["puntos"], P.todos):
            dval = "—" if pc.D is None else _s(pc.D)
            filas.append([p["id"], p["etiqueta"], f"{p['f']:.5g}", dval, p["clasificacion"],
                          p["certeza"] + (f"\n{p['global']}" if p["global"] else "")])
        if filas:
            tb = ax.table(cellText=filas, colLabels=["", "punto", "f", "D", "clasificación", "certeza"],
                          loc="upper center", cellLoc="center")
            tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 2.2)
            for (r, c), cell in tb.get_celld().items():
                if r == 0:
                    cell.set_facecolor("#6f341f"); cell.set_text_props(color="white", weight="bold")
                elif c == 4:
                    cell.set_facecolor(_color_h(D["puntos"][r - 1])); cell.set_text_props(color="white")
        G = P.analisis_global
        txt = "Análisis global:\n" + "\n".join("• " + _envolver(_s(j), 80) for j in G["justificacion"])
        ax.text(0.0, 0.02, txt, fontsize=9, va="bottom", ha="left", transform=ax.transAxes, wrap=True)
    elif D["tipo"] == "3d_volumen":
        fig = plt.figure(figsize=(16, 5.5))
        caja = D["rango"]
        p0 = D["puntos"][0]["coords"] if D["puntos"] else [(a + b) / 2 for a, b in caja]
        fn = sp.lambdify(P.variables, P.f, "numpy")
        nombres = D["variables"]
        for k in range(3):
            ax = fig.add_subplot(1, 3, k + 1)
            i, j = [q for q in range(3) if q != k]
            a = np.linspace(*caja[i], 150); b = np.linspace(*caja[j], 150)
            A, B = np.meshgrid(a, b)
            args = [None] * 3
            args[i], args[j], args[k] = A, B, np.full_like(A, p0[k])
            Zs = _eval(fn, args, A.shape)
            cf = ax.contourf(A, B, Zs, levels=30, cmap=_cmap_terra())
            fig.colorbar(cf, ax=ax)
            for p in D["puntos"]:
                if abs(p["coords"][k] - p0[k]) < 1e-9:
                    ax.plot(p["coords"][i], p["coords"][j], "o", ms=11, color=_color_h(p), mec="white", mew=2)
                    ax.annotate(p["id"], (p["coords"][i], p["coords"][j]), textcoords="offset points",
                                xytext=(7, 7), color="white", fontsize=9)
            ax.set_xlabel(nombres[i]); ax.set_ylabel(nombres[j])
            ax.set_title(f"corte {nombres[k]} = {p0[k]:.4g}", fontsize=10)
    else:
        raise ValueError("Con más de 3 variables no hay representación geométrica.")
    leyenda = [Line2D([0], [0], marker="o", ls="", ms=10, color=c, label=l) for l, c in
               [("mínimo local", _COLOR_H[MH.MIN_LOCAL]), ("máximo local", _COLOR_H[MH.MAX_LOCAL]),
                ("punto de silla", _COLOR_H[MH.SILLA]), ("indeterminado", "#8c8279"),
                ("no diferenciable", "#c38d35")]]
    fig.legend(handles=leyenda, loc="lower center", ncol=5, fontsize=10, frameon=False)
    fig.suptitle(titulo, fontsize=15, fontweight="bold")
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(ruta, dpi=dpi)
    plt.close(fig)
    return ruta


def _envolver(t, w):
    import textwrap
    return "\n  ".join(textwrap.wrap(t, w))


# ════════════════════════════════════════════════════════════════════════════
# Frenet · datos para graficar
# ════════════════════════════════════════════════════════════════════════════
def _rango_t(C: CurvaFrenet, rango):
    t0 = _num(C.t0.subs(C.valores)) or 0.0
    if rango:
        return float(rango[0]), float(rango[1])
    if C.r.has(sp.sin, sp.cos):
        return t0 - math.pi, t0 + math.pi if not C.r.has(sp.Symbol) else t0 + math.pi
    return t0 - 1.5, t0 + 1.5


def _vec_np(M: sp.Matrix, C: CurvaFrenet):
    fns = [sp.lambdify(C.t, c.subs(C.valores), "numpy") for c in M]

    def ev(ts):
        cols = []
        for f in fns:
            with np.errstate(all="ignore"):
                v = np.asarray(f(ts), dtype=float)
            cols.append(np.broadcast_to(v, ts.shape).astype(float))
        return np.stack(cols, axis=1)
    return ev


def datos_frenet(C: CurvaFrenet, rango=None, n: int = 481) -> dict:
    """Muestras de la curva con T, N, B, κ, τ, rapidez, centros de curvatura (evoluta) y datos de t0."""
    a, b = _rango_t(C, rango)
    if C.r.has(sp.sin, sp.cos) and not rango:
        a, b = a - math.pi, b + math.pi          # dos vueltas completas
    ts = np.linspace(a, b, n)
    R = _vec_np(C.r, C)(ts)
    D1, D2, D3 = (_vec_np(M, C)(ts) for M in (C.d1, C.d2, C.d3))
    v = np.linalg.norm(D1, axis=1)
    X = np.cross(D1, D2)
    nx = np.linalg.norm(X, axis=1)
    esc = float(np.nanmax(nx)) if np.isfinite(nx).any() else 1.0
    with np.errstate(all="ignore"):
        kap = nx / v ** 3
        tau = np.einsum("ij,ij->i", X, D3) / nx ** 2
        T = D1 / v[:, None]
        B = X / nx[:, None]
        N = np.cross(B, T)
    malo = nx < 1e-10 * max(esc, 1.0)
    tau[malo] = np.nan
    B[malo] = np.nan
    N[malo] = np.nan
    ext = np.nanmax(R, axis=0) - np.nanmin(R, axis=0)
    diag = float(np.linalg.norm(ext)) or 1.0
    with np.errstate(all="ignore"):
        rho = 1 / kap
        cen = R + rho[:, None] * N
    lejos = ~np.isfinite(rho) | (rho > 2.5 * diag)
    cen[lejos] = np.nan
    t0n = _num(C.t0.subs(C.valores))
    i0 = int(np.argmin(np.abs(ts - t0n))) if t0n is not None else n // 2
    # longitud de arco numérica en el rango mostrado
    try:
        import mpmath
        fv = sp.lambdify(C.t, C.rapidez.subs(C.valores), "mpmath")
        L = float(mpmath.quad(fv, [a, t0n if t0n is not None and a < t0n < b else (a + b) / 2, b]))
    except Exception:  # noqa: BLE001
        L = float(np.trapezoid(v, ts)) if hasattr(np, "trapezoid") else float(np.trapz(v, ts))
    E = C.en_t0
    t0d = {"t": t0n, "indice": i0}
    for k in ("r", "T", "N", "B", "centro"):
        if k in E:
            t0d[k] = _vnum(E[k].subs(C.valores))
    for k in ("kappa", "tau", "rho", "rapidez"):
        if k in E:
            t0d[k] = _num(E[k].subs(C.valores))
    planos = {}
    for k in ("plano_osculador", "plano_normal", "plano_rectificante"):
        if k in E:
            nn = [_num(c.subs(C.valores)) for c in E[k]["normal"]]
            planos[k.replace("plano_", "")] = {"normal": nn}
    return {"tipo": "curva", "parametro": str(C.t), "rango": [a, b], "t": _lista(ts, 5),
            "x": _lista(R[:, 0]), "y": _lista(R[:, 1]), "z": _lista(R[:, 2]),
            "T": _lista(T.T, 5), "N": _lista(N.T, 5), "B": _lista(B.T, 5),
            "kappa": _lista(kap, 6), "tau": _lista(tau, 6), "rapidez": _lista(v, 5),
            "centro": _lista(cen.T, 5), "diag": diag, "longitud_rango": L, "plana": bool(C.plana or C.plana_entrada),
            "t0": t0d, "planos": planos, "constantes": {str(k): val for k, val in C.valores.items()},
            "inflexiones": [_num(x.subs(C.valores)) for x in C.inflexiones],
            "singulares": [_num(x.subs(C.valores)) for x in C.singulares]}


# ════════════════════════════════════════════════════════════════════════════
# Frenet · PNG
# ════════════════════════════════════════════════════════════════════════════
_CT, _CN, _CB = "#b0502c", "#3f6e7d", "#c38d35"


def png_frenet(C: CurvaFrenet, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    D = datos or datos_frenet(C)
    cm = LinearSegmentedColormap.from_list("terra", _TERRA[1:])
    arr = lambda k: np.array([np.nan if q is None else q for q in D[k]], dtype=float)  # noqa: E731
    ts, x, y, z, kap, tau = arr("t"), arr("x"), arr("y"), arr("z"), arr("kappa"), arr("tau")
    fig = plt.figure(figsize=(16, 11))
    ax = fig.add_subplot(2, 2, 1, projection="3d", computed_zorder=False)
    P = np.stack([x, y, z], axis=1)
    seg = np.stack([P[:-1], P[1:]], axis=1)
    kk = np.nan_to_num(kap[:-1], nan=0.0)
    lc = Line3DCollection(seg, cmap=cm, norm=Normalize(np.nanmin(kap), np.nanmax(kap)), linewidth=3)
    lc.set_array(kk)
    ax.add_collection(lc)
    fig.colorbar(lc, ax=ax, shrink=0.6, label="curvatura κ")
    t0 = D["t0"]
    L = 0.18 * D["diag"]
    if "T" in t0 and t0.get("r"):
        p = np.array(t0["r"], dtype=float)
        for k, col in (("T", _CT), ("N", _CN), ("B", _CB)):
            if t0.get(k) and None not in t0[k]:
                d = np.array(t0[k], dtype=float) * L
                ax.quiver(*p, *d, color=col, linewidth=2.5, arrow_length_ratio=0.18, zorder=10)
                ax.text(*(p + d * 1.12), k, color=col, fontsize=13, fontweight="bold", zorder=11)
        if t0.get("centro") and None not in t0["centro"] and t0.get("rho"):
            c, rho = np.array(t0["centro"]), t0["rho"]
            Tn, Nn = np.array(t0["T"]), np.array(t0["N"])
            th = np.linspace(0, 2 * np.pi, 120)
            circ = c[None, :] + rho * (np.cos(th)[:, None] * (-Nn)[None, :] + np.sin(th)[:, None] * Tn[None, :])
            if rho < 1.2 * D["diag"]:
                ax.plot(circ[:, 0], circ[:, 1], circ[:, 2], "--", color=_CN, lw=1.5, zorder=9)
        ax.scatter(*p, s=80, color="white", edgecolor="#2b2420", zorder=12)
    lims = []
    for q in (x, y, z):
        f = q[np.isfinite(q)]
        lims.append([f.min() - 0.25 * L, f.max() + 0.25 * L])
    ext = [b - a for a, b in lims]
    mx = max(ext)
    for j, (a, b) in enumerate(lims):          # ningún eje menor al 35 % del mayor
        if ext[j] < 0.35 * mx:
            c = (a + b) / 2
            lims[j] = [c - 0.175 * mx, c + 0.175 * mx]
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_zlim(*lims[2])
    ax.set_box_aspect([b - a for a, b in lims])
    ax.set_xlabel("x"); ax.set_ylabel("y"); ax.set_zlabel("z")
    ax.set_title("Curva coloreada por κ, triedro en t0 y círculo osculador", fontsize=10)

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.plot(ts, kap, color=_CT, lw=2.2, label="curvatura κ(t)")
    if not D["plana"]:
        ax2.plot(ts, tau, color=_CN, lw=2.2, label="torsión τ(t)")
    if t0.get("t") is not None:
        ax2.axvline(t0["t"], color="#8c8279", ls="--", lw=1)
        if t0.get("kappa") is not None:
            ax2.plot(t0["t"], t0["kappa"], "o", color=_CT, ms=9, mec="white")
        if t0.get("tau") is not None and not D["plana"]:
            ax2.plot(t0["t"], t0["tau"], "o", color=_CN, ms=9, mec="white")
    ax2.axhline(0, color="#bdb2a6", lw=0.8)
    ax2.set_xlabel(D["parametro"]); ax2.legend(); ax2.grid(alpha=0.3)
    ax2.set_title("Curvatura y torsión a lo largo de la curva", fontsize=10)

    ax3 = fig.add_subplot(2, 2, 3)
    ax3.plot(x, y, color=_CT, lw=2)
    if "centro" in D:
        cx, cy = np.array([np.nan if q is None else q for q in D["centro"][0]]), \
                 np.array([np.nan if q is None else q for q in D["centro"][1]])
        fx, fy = x[np.isfinite(x)], y[np.isfinite(y)]
        mx_, my_ = 0.6 * (np.ptp(fx) or 1), 0.6 * (np.ptp(fy) or 1)
        fuera = (cx < fx.min() - mx_) | (cx > fx.max() + mx_) | (cy < fy.min() - my_) | (cy > fy.max() + my_)
        cx, cy = np.where(fuera, np.nan, cx), np.where(fuera, np.nan, cy)
        ax3.plot(cx, cy, ":", color=_CN, lw=1.5, label="evoluta (centros de curvatura)")
    if t0.get("r"):
        ax3.plot(t0["r"][0], t0["r"][1], "o", color="white", mec="#2b2420", ms=9)
    ax3.set_aspect("equal", adjustable="datalim"); ax3.grid(alpha=0.3); ax3.legend(fontsize=8)
    ax3.set_xlabel("x"); ax3.set_ylabel("y"); ax3.set_title("Proyección en el plano xy", fontsize=10)

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis("off")
    E = C.en_t0
    lin = [f"r(t) = ({', '.join(_s(c) for c in C.r)})", f"t0 = {C.t0}", f"tipo: {C.tipo}", ""]
    if "T" in E:
        lin.append(f"r(t0) = ({', '.join(_s(c) for c in E['r'])})")
        lin.append(f"T(t0) = ({', '.join(_s(c) for c in E['T'])})")
    if "N" in E:
        lin += [f"N(t0) = ({', '.join(_s(c) for c in E['N'])})", f"B(t0) = ({', '.join(_s(c) for c in E['B'])})",
                f"κ(t0) = {_s(E['kappa'])}  ≈ {_num(E['kappa'].subs(C.valores)):.6g}",
                f"τ(t0) = {_s(E['tau'])}  ≈ {_num(E['tau'].subs(C.valores)):.6g}", "",
                f"osculador:    {_s(E['plano_osculador']['lhs'])} = {_s(E['plano_osculador']['rhs'])}",
                f"normal:       {_s(E['plano_normal']['lhs'])} = {_s(E['plano_normal']['rhs'])}",
                f"rectificante: {_s(E['plano_rectificante']['lhs'])} = {_s(E['plano_rectificante']['rhs'])}"]
    import textwrap
    ax4.text(0, 1, "\n".join(textwrap.fill(q, 78, subsequent_indent="    ") for q in lin), va="top", ha="left",
             family="monospace", fontsize=9.5, transform=ax4.transAxes)
    fig.suptitle(f"Triedro de Frenet · r({C.t}) = ({', '.join(_s(c) for c in C.r)})", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(ruta, dpi=dpi)
    plt.close(fig)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# Despachadores
# ════════════════════════════════════════════════════════════════════════════
def datos_grafico(metodo: Metodo, objeto: Any, rango=None) -> dict:
    """Despachador: datos numéricos para graficar según el método."""
    if metodo == "lagrange":
        return datos_lagrange(objeto, rango=rango)
    if metodo == "hessiana":
        return datos_hessiana(objeto, rango=rango)
    if metodo == "frenet":
        return datos_frenet(objeto, rango=rango)
    raise ValueError(f"Método desconocido: {metodo}")


def generar_png(metodo: Metodo, objeto: Any, ruta: str, datos: dict | None = None) -> str:
    """Despachador: guarda la lámina PNG del método en ``ruta`` y devuelve la ruta."""
    fn = {"lagrange": png_lagrange, "hessiana": png_hessiana, "frenet": png_frenet}.get(metodo)
    if fn is None:
        raise ValueError(f"Método desconocido: {metodo}")
    if datos is not None and datos.get("tipo") == "sin_grafico":
        raise ValueError("Con más de 3 variables no hay representación geométrica.")
    return fn(objeto, ruta, datos)
