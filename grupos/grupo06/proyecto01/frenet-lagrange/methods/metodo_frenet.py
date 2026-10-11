"""
methods/metodo_frenet.py — Triedro de Frenet y geometría diferencial de curvas en R^3.

Solo contiene MATEMÁTICA (sin gráficos ni HTML). Fórmulas válidas para cualquier
parametrización regular:
    T = r′/‖r′‖,  B = (r′×r″)/‖r′×r″‖,  N = B×T,
    κ = ‖r′×r″‖/‖r′‖³,  τ = [(r′×r″)·r‴]/‖r′×r″‖²
En t0: planos osculador (⟂B), normal (⟂T) y rectificante (⟂N), círculo osculador,
verificación de Frenet–Serret con 50 dígitos y clasificación (recta, circunferencia,
curva plana, hélice circular, hélice generalizada, curva alabeada).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import sympy as sp

from core.utils_math import (
    es_cero as _es_cero,
    num as _num,
    parsear_seguro,
    simplificar as _simp,
    vlat as _vlat,
    vnum as _vnum,
)

__all__ = ["resolver", "a_dict", "resolver_frenet", "CurvaFrenet", "DEMOS"]

X_, Y_, Z_ = sp.symbols("x y z", real=True)          # coordenadas para las ecuaciones de planos


# ════════════════════════════════════════════════════════════════════════════
# 1. Estructura de datos
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class CurvaFrenet:
    r: sp.Matrix                      # 3×1
    t: sp.Symbol
    t0: sp.Expr
    constantes: list = field(default_factory=list)
    valores: dict = field(default_factory=dict)      # valores numéricos de las constantes (solo gráficos)
    plana_entrada: bool = False                      # la entrada tenía 2 componentes
    d1: sp.Matrix | None = None
    d2: sp.Matrix | None = None
    d3: sp.Matrix | None = None
    rapidez: sp.Expr | None = None                   # ‖r'‖
    cruz: sp.Matrix | None = None                    # r' × r''
    norma_cruz: sp.Expr | None = None
    triple: sp.Expr | None = None                    # (r' × r'') · r'''
    T: sp.Matrix | None = None
    N: sp.Matrix | None = None
    B: sp.Matrix | None = None
    N_num: sp.Matrix | None = None                   # (r'·r') r'' − (r'·r'') r'
    kappa: sp.Expr | None = None
    tau: sp.Expr | None = None
    s_t: sp.Expr | None = None                       # longitud de arco desde t0
    en_t0: dict = field(default_factory=dict)
    clasificacion: list = field(default_factory=list)
    tipo: str = ""
    singulares: list = field(default_factory=list)
    inflexiones: list = field(default_factory=list)
    verificacion: dict = field(default_factory=dict)
    advertencias: list = field(default_factory=list)
    recta: bool = False
    plana: bool = False


# ════════════════════════════════════════════════════════════════════════════
# 2. Entrada
# ════════════════════════════════════════════════════════════════════════════
def _parse(texto: str):
    return parsear_seguro(texto)


def _componentes(r) -> list:
    """Acepta "cos t, sin t, t", "(t, t^2, t^3)", "r(t) = <...>" o una lista de expresiones."""
    if isinstance(r, (list, tuple, sp.Matrix)):
        return [sp.sympify(c) if isinstance(c, sp.Basic) else _parse(str(c)) for c in list(r)]
    txt = str(r).strip()
    if "=" in txt:
        txt = txt.split("=", 1)[1].strip()
    while txt and txt[0] in "(<[" and txt[-1] in ")>]":
        txt = txt[1:-1].strip()
    e = _parse("(" + txt + ",)")
    return list(e)


def _preparar(r, parametro=None, t0=0, constantes=None):
    comps = _componentes(r)
    if len(comps) not in (2, 3):
        raise ValueError(f"La curva debe tener 2 o 3 componentes; se recibieron {len(comps)}.")
    plana = len(comps) == 2
    if plana:
        comps.append(sp.Integer(0))
    libres = set().union(*[c.free_symbols for c in comps])
    nombres = {s.name for s in libres}
    if parametro:
        pnombre = str(parametro)
    elif "t" in nombres or not nombres:
        pnombre = "t"
    elif len(nombres) == 1:
        pnombre = next(iter(nombres))
    else:
        raise ValueError(f"No sé cuál es el parámetro entre {sorted(nombres)}: indícalo con --param.")
    t = sp.Symbol(pnombre, real=True)
    ctes = sorted(nombres - {pnombre})
    sim = {nm: sp.Symbol(nm, positive=True) for nm in ctes}
    sust = {s: (t if s.name == pnombre else sim[s.name]) for s in libres}
    comps = [c.subs(sust) for c in comps]
    if all(not c.has(t) for c in comps):
        raise ValueError("La curva no depende del parámetro: es un punto fijo.")
    t0e = sp.sympify(_parse(str(t0)) if not isinstance(t0, sp.Basic) else t0)
    t0e = t0e.subs({s: sim.get(s.name, s) for s in t0e.free_symbols})
    valores = {}
    for nm in ctes:
        v = (constantes or {}).get(nm, 1)
        valores[sim[nm]] = float(v)
    return sp.Matrix(comps), t, t0e, [sim[nm] for nm in ctes], valores, plana


# ════════════════════════════════════════════════════════════════════════════
# 3. Utilidades geométricas
# ════════════════════════════════════════════════════════════════════════════
def _norma(v: sp.Matrix):
    return _simp(sp.sqrt(_simp(v.dot(v))))


def _normal_limpia(n: sp.Matrix) -> sp.Matrix:
    """Vector normal proporcional con coeficientes lo más simples posible (enteros si se puede)."""
    n = n.applyfunc(_simp)
    nz = [c for c in n if c != 0]
    if not nz:
        return n
    try:
        if all(c.is_rational for c in nz):
            den = 1
            for c in nz:
                den = den * sp.Rational(c).q // math.gcd(den, sp.Rational(c).q)
            m = n * den
            g = 0
            for c in m:
                g = math.gcd(g, abs(int(c)))
            m = m / g
        else:
            g = sp.gcd_terms(nz[0]) if len(nz) == 1 else sp.gcd(nz[0], nz[1])
            for c in nz[2:]:
                g = sp.gcd(g, c)
            m = (n / g).applyfunc(_simp) if g not in (0, None) else n
        primero = next(c for c in m if c != 0)
        if _num(primero) is not None and _num(primero) < 0:
            m = -m
        return m.applyfunc(_simp)
    except Exception:  # noqa: BLE001
        return n


def _plano(normal: sp.Matrix, punto: sp.Matrix) -> dict:
    n = _normal_limpia(normal)
    lhs = n[0] * X_ + n[1] * Y_ + n[2] * Z_
    rhs = _simp(n.dot(punto))
    return {"normal": n, "ecuacion": sp.Eq(lhs, rhs, evaluate=False), "lhs": lhs, "rhs": rhs}


# ════════════════════════════════════════════════════════════════════════════
# 4. Motor principal
# ════════════════════════════════════════════════════════════════════════════
def resolver(r, t0=0, parametro=None, constantes=None) -> CurvaFrenet:
    """Calcula todo el aparato de Frenet (general y en t0). Devuelve objetos SymPy."""
    rv, t, t0e, ctes, valores, plana = _preparar(r, parametro, t0, constantes)
    C = CurvaFrenet(r=rv, t=t, t0=t0e, constantes=ctes, valores=valores, plana_entrada=plana)

    C.d1 = rv.diff(t).applyfunc(_simp)
    C.d2 = C.d1.diff(t).applyfunc(_simp)
    C.d3 = C.d2.diff(t).applyfunc(_simp)
    C.rapidez = _norma(C.d1)
    if _es_cero(C.rapidez):
        raise ValueError("r'(t) ≡ 0: la curva es constante.")
    C.cruz = C.d1.cross(C.d2).applyfunc(_simp)
    nc2 = _simp(C.cruz.dot(C.cruz))
    C.norma_cruz = _simp(sp.sqrt(nc2))
    C.triple = _simp(C.cruz.dot(C.d3))
    C.T = (C.d1 / C.rapidez).applyfunc(_simp)
    C.recta = _es_cero(nc2)

    if C.recta:
        C.kappa = sp.Integer(0)
        C.tau = sp.nan
        C.advertencias.append("r' × r'' ≡ 0: la curva es una RECTA (κ = 0). N, B y τ no están definidos.")
    else:
        C.kappa = _simp(C.norma_cruz / C.rapidez ** 3)
        C.tau = _simp(C.triple / nc2)
        C.B = (C.cruz / C.norma_cruz).applyfunc(_simp)
        C.N_num = (C.d1.dot(C.d1) * C.d2 - C.d1.dot(C.d2) * C.d1).applyfunc(_simp)
        C.N = (C.N_num / (C.norma_cruz * C.rapidez)).applyfunc(_simp)
        C.plana = _es_cero(C.triple)

    _evaluar_t0(C)
    _clasificar(C)
    _especiales(C)
    _longitud_arco(C)
    _verificar(C)
    return C


def _evaluar_t0(C: CurvaFrenet):
    t, t0 = C.t, C.t0
    E = {}
    E["r"] = C.r.subs(t, t0).applyfunc(_simp)
    E["d1"] = C.d1.subs(t, t0).applyfunc(_simp)
    E["d2"] = C.d2.subs(t, t0).applyfunc(_simp)
    E["d3"] = C.d3.subs(t, t0).applyfunc(_simp)
    E["rapidez"] = _norma(E["d1"])
    if _es_cero(E["rapidez"]):
        C.advertencias.append(f"En t0 = {t0} se anula r'(t0): punto SINGULAR, el triedro no está definido.")
        E["singular"] = True
        C.en_t0 = E
        return
    E["T"] = (E["d1"] / E["rapidez"]).applyfunc(_simp)
    E["cruz"] = E["d1"].cross(E["d2"]).applyfunc(_simp)
    nc2 = _simp(E["cruz"].dot(E["cruz"]))
    E["norma_cruz"] = _simp(sp.sqrt(nc2))
    E["triple"] = _simp(E["cruz"].dot(E["d3"]))
    E["kappa"] = _simp(E["norma_cruz"] / E["rapidez"] ** 3)
    E["plano_normal"] = _plano(E["d1"], E["r"])
    if _es_cero(nc2):
        if C.recta:
            E["inflexion"] = True
            C.en_t0 = E
            return
        C.advertencias.append(f"En t0 = {t0} se anula r' × r'': κ(t0) = 0 (punto de inflexión); "
                              "N, B, τ y los planos osculador y rectificante no están definidos.")
        E["inflexion"] = True
        C.en_t0 = E
        return
    E["tau"] = _simp(E["triple"] / nc2)
    E["B"] = (E["cruz"] / E["norma_cruz"]).applyfunc(_simp)
    E["N_num"] = (E["d1"].dot(E["d1"]) * E["d2"] - E["d1"].dot(E["d2"]) * E["d1"]).applyfunc(_simp)
    E["N"] = (E["N_num"] / (E["norma_cruz"] * E["rapidez"])).applyfunc(_simp)
    E["rho"] = _simp(1 / E["kappa"])
    E["sigma"] = _simp(1 / E["tau"]) if not _es_cero(E["tau"]) else sp.oo
    E["centro"] = (E["r"] + E["rho"] * E["N"]).applyfunc(_simp)
    E["plano_osculador"] = _plano(E["cruz"], E["r"])
    E["plano_rectificante"] = _plano(E["N_num"], E["r"])
    C.en_t0 = E


def _clasificar(C: CurvaFrenet):
    t = C.t
    if C.recta:
        C.tipo = "recta"
        C.clasificacion = ["Recta: r' × r'' ≡ 0, así que κ ≡ 0."]
        return
    k_cte = _es_cero(sp.diff(C.kappa, t))
    t_cte = (not C.plana) and _es_cero(sp.diff(C.tau, t))
    if C.plana:
        if k_cte:
            C.tipo = "circunferencia"
            C.clasificacion.append("τ ≡ 0 y κ constante: la curva es (un arco de) CIRCUNFERENCIA.")
        else:
            C.tipo = "curva plana"
            C.clasificacion.append("τ ≡ 0: la curva es PLANA (vive entera en su plano osculador).")
    elif k_cte and t_cte:
        C.tipo = "hélice circular"
        C.clasificacion.append("κ y τ constantes no nulas: HÉLICE CIRCULAR (teorema fundamental de curvas).")
    elif _es_cero(sp.diff(_simp(C.tau / C.kappa), t)):
        C.tipo = "hélice generalizada"
        C.clasificacion.append("τ/κ constante: HÉLICE GENERALIZADA (teorema de Lancret): sus tangentes forman "
                               "un ángulo fijo con una dirección del espacio.")
    else:
        C.tipo = "curva alabeada"
        C.clasificacion.append("τ ≢ 0: curva ALABEADA (no está contenida en ningún plano).")
    if k_cte and not C.plana and not t_cte:
        C.clasificacion.append("Su curvatura es constante.")


def _resolver_t(eqs, t):
    """Soluciones reales de un sistema de ecuaciones en t (lista vacía si no se puede)."""
    eqs = [e for e in eqs if not _es_cero(e)]
    if not eqs:
        return None                      # idénticamente cero
    try:
        sols = sp.solve(eqs, t, dict=True)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for s in sols:
        v = s.get(t)
        if v is not None and _num(v) is not None and not v.free_symbols - {t}:
            out.append(_simp(v))
    return sorted(set(out), key=lambda v: _num(v))


def _especiales(C: CurvaFrenet):
    t = C.t
    s = _resolver_t(list(C.d1), t) or []
    C.singulares = s
    if s:
        C.advertencias.append("Hay puntos SINGULARES (r' = 0) en t = " + ", ".join(map(str, s)) +
                              ": ahí la curva puede tener una cúspide y el triedro no existe.")
    if not C.recta:
        inf = _resolver_t(list(C.cruz), t) or []
        C.inflexiones = [v for v in inf if v not in s]
        if C.inflexiones:
            C.advertencias.append("κ = 0 (r' × r'' = 0) en t = " + ", ".join(map(str, C.inflexiones)) +
                                  ": puntos de inflexión, donde N y B no están definidos.")
    if C.r.has(sp.sin, sp.cos, sp.tan):
        C.advertencias.append("La curva tiene funciones periódicas: los puntos especiales se repiten con el período.")


def _longitud_arco(C: CurvaFrenet):
    t, v = C.t, C.rapidez
    raiz = any((p.exp.is_Rational and not p.exp.is_Integer and p.base.has(t)) for p in v.atoms(sp.Pow))
    if raiz:
        return
    u = sp.Dummy("u", real=True)
    try:
        s = sp.integrate(v.subs(t, u), (u, C.t0, t))
        if not s.has(sp.Integral):
            C.s_t = _simp(s)
    except Exception:  # noqa: BLE001
        pass


def _verificar(C: CurvaFrenet):
    """Fórmulas de Frenet–Serret en t0 y ortonormalidad del triedro, con 50 dígitos.
    Las derivadas de T, N, B se calculan por diferencias centrales (h = 1e-20): así la
    verificación es independiente de la fórmula simbólica y no falla si la expresión
    general tiene una singularidad evitable (0/0) justo en t0."""
    E = C.en_t0
    if C.recta or "N" not in E:
        return
    import mpmath
    mpmath.mp.dps = 50
    t = C.t
    val = {k: sp.nsimplify(v) for k, v in C.valores.items()}      # constantes exactas
    t0 = float(sp.N(C.t0.subs(val), 50)) if C.t0.free_symbols else C.t0
    t0m = mpmath.mpf(str(sp.N(sp.sympify(t0), 50)))
    try:
        fT, fN, fB = ([sp.lambdify(t, c.subs(val), "mpmath") for c in M] for M in (C.T, C.N, C.B))
        h = mpmath.mpf("1e-20")
        der = lambda fs: [(f(t0m + h) - f(t0m - h)) / (2 * h) for f in fs]  # noqa: E731
        ev = lambda fs: [f(t0m) if True else 0 for f in fs]                 # noqa: E731
        num = lambda e: mpmath.mpf(str(sp.N(e.subs(val), 50)))              # noqa: E731
        v, k, ta = num(E["rapidez"]), num(E["kappa"]), num(E["tau"])
        T0, N0, B0 = ([num(c) for c in E[q]] for q in ("T", "N", "B"))
        dT, dN, dB = der(fT), der(fN), der(fB)
        res = {
            "T' = v κ N": [dT[i] - v * k * N0[i] for i in range(3)],
            "N' = v (−κ T + τ B)": [dN[i] - v * (-k * T0[i] + ta * B0[i]) for i in range(3)],
            "B' = −v τ N": [dB[i] + v * ta * N0[i] for i in range(3)],
        }
        out = {nm: float(max(abs(x) for x in R)) for nm, R in res.items()}
        dot = lambda a, b: sum(x * y for x, y in zip(a, b))               # noqa: E731
        cr = [T0[1] * N0[2] - T0[2] * N0[1], T0[2] * N0[0] - T0[0] * N0[2], T0[0] * N0[1] - T0[1] * N0[0]]
        orto = {"T·N": dot(T0, N0), "T·B": dot(T0, B0), "N·B": dot(N0, B0), "‖T‖−1": dot(T0, T0) - 1,
                "‖N‖−1": dot(N0, N0) - 1, "‖B‖−1": dot(B0, B0) - 1,
                "T×N−B": max(abs(cr[i] - B0[i]) for i in range(3))}
        del ev
        C.verificacion = {"frenet_serret_t0": out, "ortonormalidad_t0": {q: float(abs(x)) for q, x in orto.items()},
                          "metodo": "50 dígitos; derivadas por diferencias centrales (h = 1e-20)"}
        C.verificacion["correcto"] = all(x < 1e-25 for x in list(out.values()) +
                                         list(C.verificacion["ortonormalidad_t0"].values()))
    except Exception as e:  # noqa: BLE001
        C.verificacion = {"error": str(e)}
    finally:
        mpmath.mp.dps = 15


# ════════════════════════════════════════════════════════════════════════════
# 5. JSON (formato MCP)
# ════════════════════════════════════════════════════════════════════════════
def _vec(v, nombre=""):
    if v is None:
        return None
    return {"componentes": [str(c) for c in v], "componentes_latex": [sp.latex(c) for c in v],
            "latex": _vlat(v), "num": _vnum(v), "nombre": nombre}


def _esc(e):
    if e is None:
        return None
    return {"expr": str(e), "latex": sp.latex(e), "num": _num(e)}


def _plano_dict(pl):
    if not pl:
        return None
    return {"normal": [str(c) for c in pl["normal"]], "normal_latex": _vlat(pl["normal"]),
            "normal_num": _vnum(pl["normal"]), "ecuacion": f"{pl['lhs']} = {pl['rhs']}",
            "ecuacion_latex": sp.latex(pl["lhs"]) + " = " + sp.latex(pl["rhs"]),
            "rhs_num": _num(pl["rhs"])}


def a_dict(C: CurvaFrenet) -> dict:
    t, E = C.t, C.en_t0
    tl = sp.latex(t)
    t0l = sp.latex(C.t0)
    def_ = not C.recta
    out = {
        "entrada": {"r": [str(c) for c in C.r], "r_latex": _vlat(C.r), "componentes_latex": [sp.latex(c) for c in C.r],
                    "parametro": str(t), "parametro_latex": tl, "t0": str(C.t0), "t0_latex": t0l, "t0_num": _num(C.t0),
                    "constantes": {str(k): v for k, v in C.valores.items()}, "curva_plana_entrada": C.plana_entrada},
        "derivadas": [{"orden": i, "vector": _vec(d)} for i, d in enumerate([C.d1, C.d2, C.d3], 1)],
        "rapidez": _esc(C.rapidez),
        "producto_cruz": _vec(C.cruz),
        "norma_cruz": _esc(C.norma_cruz),
        "triple_producto": _esc(C.triple),
        "T": _vec(C.T), "N": _vec(C.N) if def_ else None, "B": _vec(C.B) if def_ else None,
        "N_numerador": _vec(C.N_num) if def_ else None,
        "curvatura": _esc(C.kappa),
        "torsion": _esc(C.tau) if def_ else None,
        "longitud_arco": {"s_t": str(C.s_t) if C.s_t is not None else None,
                          "s_t_latex": sp.latex(C.s_t) if C.s_t is not None else None},
        "tipo": C.tipo, "clasificacion": C.clasificacion,
        "puntos_singulares": [{"t": str(v), "latex": sp.latex(v), "num": _num(v)} for v in C.singulares],
        "puntos_inflexion": [{"t": str(v), "latex": sp.latex(v), "num": _num(v)} for v in C.inflexiones],
        "verificacion": C.verificacion,
        "advertencias": C.advertencias,
    }
    e = {"punto": _vec(E.get("r")), "d1": _vec(E.get("d1")), "d2": _vec(E.get("d2")), "d3": _vec(E.get("d3")),
         "rapidez": _esc(E.get("rapidez")), "T": _vec(E.get("T"))}
    if "N" in E:
        e.update({"N": _vec(E["N"]), "B": _vec(E["B"]), "cruz": _vec(E["cruz"]), "norma_cruz": _esc(E["norma_cruz"]),
                  "triple": _esc(E["triple"]), "curvatura": _esc(E["kappa"]), "torsion": _esc(E["tau"]),
                  "radio_curvatura": _esc(E["rho"]), "radio_torsion": _esc(E["sigma"]) if E["sigma"] != sp.oo else None,
                  "centro_curvatura": _vec(E["centro"]),
                  "planos": {"osculador": _plano_dict(E["plano_osculador"]), "normal": _plano_dict(E["plano_normal"]),
                             "rectificante": _plano_dict(E["plano_rectificante"])},
                  "calculo_kappa_latex": (rf"\kappa({t0l}) = \frac{{\lVert r'\times r''\rVert}}{{\lVert r'\rVert^{{3}}}} = "
                                          rf"\frac{{{sp.latex(E['norma_cruz'])}}}{{\left({sp.latex(E['rapidez'])}\right)^{{3}}}} = {sp.latex(E['kappa'])}"),
                  "calculo_tau_latex": (rf"\tau({t0l}) = \frac{{(r'\times r'')\cdot r'''}}{{\lVert r'\times r''\rVert^{{2}}}} = "
                                        rf"\frac{{{sp.latex(E['triple'])}}}{{{sp.latex(_simp(E['norma_cruz'] ** 2))}}} = {sp.latex(E['tau'])}")})
    elif "plano_normal" in E:
        e.update({"curvatura": _esc(E["kappa"]), "planos": {"normal": _plano_dict(E["plano_normal"])}})
    out["en_t0"] = e
    return out



def resolver_frenet(r, t0=0, parametro=None, constantes=None, incluir_grafico: bool = False, rango=None) -> dict:
    """Atajo: resuelve y devuelve el dict JSON (opcionalmente con los datos para graficar)."""
    C = resolver(r, t0, parametro, constantes)
    out = a_dict(C)
    if incluir_grafico:
        from core.visualizacion import datos_frenet   # import diferido: evita ciclos
        out["grafico"] = datos_frenet(C, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 6. Ejemplos
# ════════════════════════════════════════════════════════════════════════════
DEMOS = {
    1: ("cos t, sin t, t", "0", None, "Hélice circular: κ y τ constantes (κ = τ = 1/2)."),
    2: ("t, t^2, t^3", "1", None, "Cúbica alabeada: el ejemplo clásico de curva no plana."),
    3: ("a cos t, a sin t, b t", "0", {"a": 2, "b": 1}, "Hélice con constantes simbólicas: κ = a/(a²+b²), τ = b/(a²+b²)."),
    4: ("t, t^2", "0", None, "Parábola (curva plana): τ ≡ 0, círculo osculador de radio 1/2."),
    5: ("exp(t) cos t, exp(t) sin t, exp(t)", "0", None, "Hélice cónica: τ/κ constante → hélice generalizada (Lancret)."),
    6: ("sin t + 2 sin(2t), cos t - 2 cos(2t), -sin(3t)", "0", None, "Nudo de trébol: curva alabeada con κ y τ variables."),
    7: ("t, t^3, 0", "1", None, "Cúbica plana: punto de inflexión en t = 0 (κ = 0, N y B no existen)."),
    8: ("1 + cos t, sin t, 2 sin(t/2)", "0", None, "Curva de Viviani: intersección de una esfera y un cilindro."),
}
