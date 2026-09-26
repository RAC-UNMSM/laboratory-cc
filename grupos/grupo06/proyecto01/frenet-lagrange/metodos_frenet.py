#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metodos_frenet.py — Triedro de Frenet y geometría diferencial de curvas en R^3
==============================================================================
Proyecto: Frenet, Lagrange y Puntos Críticos (Grupo 06) — servidor MCP con SymPy.

Qué hace
--------
Analiza una curva parametrizada r(t) = (x(t), y(t), z(t)) con álgebra computacional
EXACTA (SymPy): derivadas, marco móvil ortonormal, curvatura, torsión y planos.
Los decimales solo aparecen como apoyo y en los datos para graficar.

Fórmulas (válidas para cualquier parametrización regular, no solo por arco):
    T = r' / ‖r'‖                          (vector tangente unitario)
    B = (r' × r'') / ‖r' × r''‖             (vector binormal)
    N = B × T = ((r'×r'') × r') / (‖r'×r''‖ ‖r'‖)   (normal principal)
    κ = ‖r' × r''‖ / ‖r'‖³                  (curvatura)
    τ = [(r' × r'') · r'''] / ‖r' × r''‖²    (torsión)
En un punto t0:
    plano osculador    ⟂ B   (contiene a T y N)
    plano normal       ⟂ T   (contiene a N y B)
    plano rectificante ⟂ N   (contiene a T y B)

Lo que va MÁS ALLÁ de lo pedido
  • Círculo osculador (radio ρ = 1/κ, centro C = r + ρN) y evoluta (lugar de los centros).
  • Verificación de las fórmulas de Frenet–Serret  T' = vκN,  N' = v(−κT + τB),  B' = −vτN
    en t0 (40 dígitos) y a lo largo de toda la curva, más la ortonormalidad de T, N, B.
  • Clasificación: recta, circunferencia, curva plana, hélice circular, hélice generalizada
    (teorema de Lancret: τ/κ constante) o curva alabeada.
  • Puntos singulares (r' = 0) y puntos de inflexión (r' × r'' = 0, donde N y B no existen).
  • Longitud de arco s(t) exacta cuando la integral es elemental, y numérica en el rango.
  • Constantes simbólicas: r(t) = (a cos t, a sin t, b t) da κ = a/(a²+b²) en general.

Uso desde la terminal
---------------------
  python metodos_frenet.py -r "cos t, sin t, t" --t0 0 --html helice.html
  python metodos_frenet.py -r "t, t^2, t^3" --t0 1 --png cubica.png
  python metodos_frenet.py -r "a cos t, a sin t, b t" --const a=2 b=1 --html helice_ab.html
  python metodos_frenet.py --demo 0          (ejemplos 1..8)
  Agrega --offline para que la página funcione sin internet (requiere: pip install plotly).

Uso desde Python / MCP
----------------------
  from metodos_frenet import resolver_frenet
  res = resolver_frenet("cos t, sin t, t", t0=0, incluir_grafico=True)   # dict JSON

Dependencias: sympy, numpy, mpmath  (matplotlib solo para --png)
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_application,
    implicit_multiplication,
    parse_expr,
    standard_transformations,
)

__all__ = ["resolver_frenet", "resolver", "a_dict", "datos_grafico", "graficar_png",
           "exportar_html", "reporte_texto", "CurvaFrenet"]

_TRANSF = standard_transformations + (implicit_multiplication, implicit_application, convert_xor)
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
    return parse_expr(texto, transformations=_TRANSF, evaluate=True)


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
# 3. Utilidades simbólicas
# ════════════════════════════════════════════════════════════════════════════
_TRIG = (sp.sin, sp.cos, sp.tan, sp.sinh, sp.cosh, sp.tanh, sp.exp)


def _simp(e):
    """Simplificación robusta: trigsimp + simplify cuando la expresión no es enorme."""
    e = sp.sympify(e)
    try:
        if e.has(*_TRIG):
            e = sp.trigsimp(e)
        if sp.count_ops(e) <= 350:
            e2 = sp.simplify(e)
            if sp.count_ops(e2) <= sp.count_ops(e):
                e = e2
        else:
            e = sp.cancel(e)
    except Exception:  # noqa: BLE001
        pass
    return e


def _num(v):
    try:
        c = complex(sp.N(v, 30))
    except (TypeError, ValueError):
        return None
    if abs(c.imag) > 1e-12 * (1 + abs(c.real)) or not math.isfinite(c.real):
        return None
    return float(c.real)


_MUESTRAS_T = ("0.3719", "1.1287", "2.7043", "-0.8311", "1.9377", "-2.4103")


def _es_cero(e) -> bool:
    """¿e ≡ 0? Primero un test de identidad por evaluación (30 dígitos en 6 valores de t y
    de las constantes): si alguno da ≠ 0, NO es idénticamente cero (prueba segura).
    Solo si todos dan 0 se confirma con simplificación simbólica."""
    e = sp.sympify(e)
    if e == 0:
        return True
    libres = sorted(e.free_symbols, key=str)
    if libres:
        concluyente = 0
        for k, tv in enumerate(_MUESTRAS_T):
            sub = {x: sp.Float(tv, 30) if x.is_positive is not True else sp.Float(str(1.37 + 0.61 * j + 0.13 * k), 30)
                   for j, x in enumerate(libres)}
            try:
                val = complex(sp.N(e.subs(sub), 30))
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if not (math.isfinite(val.real) and math.isfinite(val.imag)):
                continue
            concluyente += 1
            if abs(val) > 1e-18:
                return False
        if concluyente >= 4:
            try:                              # confirmación simbólica barata
                z = _simp(e)
                if z == 0 or z.is_zero:
                    return True
            except Exception:  # noqa: BLE001
                pass
            return True                       # nulo en ≥ 4 puntos con 30 dígitos: identidad
    try:
        e = _simp(e)
        if e == 0 or e.is_zero:
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _norma(v: sp.Matrix):
    return _simp(sp.sqrt(_simp(v.dot(v))))


def _vlat(v) -> str:
    return r"\left(" + ",\\ ".join(sp.latex(c) for c in v) + r"\right)"


def _vnum(v):
    return [_num(c) for c in v]


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
def _s(e) -> str:
    return str(e).replace("**", "^")


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
    """PUNTO DE ENTRADA PARA EL MCP. Devuelve un dict 100 % serializable a JSON."""
    C = resolver(r, t0, parametro, constantes)
    out = a_dict(C)
    if incluir_grafico:
        out["grafico"] = datos_grafico(C, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 6. Datos numéricos para gráficos
# ════════════════════════════════════════════════════════════════════════════
def _lista(a, dec=5):
    a = np.round(np.asarray(a, dtype=float), dec)
    if a.ndim == 1:
        return [None if not math.isfinite(x) else float(x) for x in a]
    return [_lista(f, dec) for f in a]


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


def datos_grafico(C: CurvaFrenet, rango=None, n: int = 481) -> dict:
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
# 7. PNG (matplotlib)
# ════════════════════════════════════════════════════════════════════════════
_TERRA = ["#2c2420", "#4c2c21", "#7a3a24", "#ab4f2c", "#cf8660", "#e7bf9e", "#f7ece0"]
_CT, _CN, _CB = "#b0502c", "#3f6e7d", "#c38d35"


def graficar_png(C: CurvaFrenet, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, Normalize
    from mpl_toolkits.mplot3d.art3d import Line3DCollection

    D = datos or datos_grafico(C)
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
# 8. Página web (misma base que metodos_lagrange.py y metodos_hessiana.py)
# ════════════════════════════════════════════════════════════════════════════
_WEB_PLANTILLA = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITULO__</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
__PLOTLY__
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<style>
:root{--bg:#f4efe8;--card:#fffcf8;--tx:#2b2420;--mu:#7b6e64;--bd:#e5d9cc;--soft:#f8f2eb;--ac:#b0502c;--ac2:#8c3d20;
--sand:#e6d2bb;--code:#f3ebe1;--str:#5f6d3f;--min:#3f6e7d;--max:#b0502c;--silla:#7a5873;--ind:#8c8279;--sing:#c38d35;
--sh:0 1px 2px rgba(60,35,20,.05),0 10px 30px rgba(60,35,20,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#191512;--card:#221d19;--tx:#ece4da;--mu:#a4968a;--bd:#3a3029;--soft:#2a241f;
--ac:#d87a52;--ac2:#eaa07e;--sand:#4a3a2e;--code:#1e1a16;--str:#a9b98a;--min:#78a9b8;--max:#d87a52;--silla:#b58fae;--ind:#a39a91;--sing:#dcae5e;--sh:none}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
code{font:13px "JetBrains Mono",monospace;background:var(--code);padding:1px 6px;border-radius:5px}
.hero{background:radial-gradient(900px 380px at 88% -30%,rgba(255,214,186,.22),transparent 70%),linear-gradient(125deg,#3e2117 0%,#6f341f 42%,#a44a28 100%);color:#fbf1e8;padding:38px 0 32px}
.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;opacity:.78;font-weight:600}
.hero h1{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:32px;margin:6px 0 16px;letter-spacing:-.01em}
.enunciado{font-size:19px;overflow-x:auto;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:12px 20px;display:inline-block;max-width:100%}
.meta{margin-top:14px;font-size:13px;opacity:.82;display:flex;gap:18px;flex-wrap:wrap}.meta span:before{content:"◆ ";opacity:.6}
.tabs{position:sticky;top:0;z-index:30;background:var(--card);border-bottom:1px solid var(--bd);box-shadow:0 2px 10px rgba(60,35,20,.04)}
.tabs .wrap{display:flex;gap:2px;overflow-x:auto}
.tab{appearance:none;border:0;background:none;color:var(--mu);font:600 14px Inter,sans-serif;padding:15px 16px 12px;border-bottom:3px solid transparent;cursor:pointer;white-space:nowrap;transition:color .15s}
.tab:hover{color:var(--tx)}.tab.activo{color:var(--ac);border-bottom-color:var(--ac)}
.tab .n{display:inline-grid;place-items:center;width:20px;height:20px;border-radius:50%;background:var(--soft);border:1px solid var(--bd);font-size:11px;margin-right:6px}
.tab.activo .n{background:var(--ac);color:#fff;border-color:var(--ac)}
.panel{display:none;padding:24px 0 34px}.panel.activo{display:block;animation:fade .25s ease}
@keyframes fade{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:22px;margin:0 0 18px;box-shadow:var(--sh);min-width:0}
h2{font-family:"Source Serif 4",Georgia,serif;font-weight:600;font-size:22px;margin:0 0 4px;letter-spacing:-.01em}
h3{font-size:15.5px;margin:0 0 6px}.sub{color:var(--mu);font-size:14px;margin:0 0 16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden;box-shadow:var(--sh)}
.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c,var(--ac))}
.kpi b{display:block;font:600 30px/1.1 "Source Serif 4",serif}.kpi span{color:var(--mu);font-size:13px}
.chip{display:inline-block;padding:3px 11px;border-radius:99px;color:#fff;font-size:12px;font-weight:600;background:var(--c);white-space:nowrap}
.pts{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:14px}
.pt{border:1px solid var(--bd);border-radius:14px;padding:16px 18px;background:var(--soft);border-top:4px solid var(--c);min-width:0;overflow-x:auto}
.pt .cab{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}
table.kv{width:100%;border-collapse:collapse;font-size:14px}table.kv td{padding:7px 4px;border-bottom:1px dashed var(--bd);vertical-align:top}
table.kv td:first-child{color:var(--mu);width:32%}table.kv tr:last-child td{border-bottom:0}
.barras{display:flex;flex-direction:column;gap:8px}.barra{display:grid;grid-template-columns:190px 1fr 120px;gap:10px;align-items:center;font-size:14px}
.barra .t{height:12px;border-radius:6px;background:var(--soft);border:1px solid var(--bd);position:relative;overflow:hidden}
.barra .t i{position:absolute;top:0;bottom:0;left:0;border-radius:6px;background:var(--c)}
.paso{display:grid;grid-template-columns:46px 1fr;gap:14px;margin:0 0 18px}
.num{width:38px;height:38px;border-radius:50%;background:var(--ac);color:#fff;display:grid;place-items:center;font:600 16px "Source Serif 4",serif;box-shadow:0 0 0 6px color-mix(in srgb,var(--ac) 14%,transparent);margin-top:4px}
.paso .cuerpo{background:var(--card);border:1px solid var(--bd);border-radius:16px;padding:18px 22px;min-width:0;box-shadow:var(--sh)}
.paso .cuerpo>p{margin:6px 0}
.eq{background:var(--soft);border-left:3px solid var(--sand);border-radius:0 12px 12px 0;padding:4px 16px;margin:12px 0;overflow-x:auto;overflow-y:hidden}
.eq .katex-display{margin:.7em 0}.eq .katex{font-size:1.12em}
.nota{color:var(--mu);font-size:13.5px}
.concl{margin-top:12px;padding:11px 15px;border-radius:12px;background:color-mix(in srgb,var(--c) 11%,transparent);border:1px solid color-mix(in srgb,var(--c) 35%,transparent);font-weight:500}
.idea{border:1px dashed var(--sand);border-radius:12px;padding:10px 14px;font-size:14px;background:color-mix(in srgb,var(--sand) 18%,transparent);margin:10px 0}
details.sp{border:1px solid var(--bd);border-radius:14px;margin:12px 0;background:var(--card)}
details.sp>summary{cursor:pointer;padding:13px 16px;font-weight:600;list-style:none;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
details.sp>summary::-webkit-details-marker{display:none}
details.sp>summary:before{content:"▸";color:var(--ac);transition:transform .2s;display:inline-block}details.sp[open]>summary:before{transform:rotate(90deg)}
details.sp .in{padding:0 18px 16px;border-top:1px solid var(--bd)}
ol.pasos{margin:8px 0 0 20px;padding:0}ol.pasos li{margin:6px 0}
.visor{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:18px}@media(max-width:1000px){.visor{grid-template-columns:1fr}}
.plot{width:100%;height:620px}.visor .plot.alto{height:780px}@media(max-width:1000px){.visor .plot.alto{height:560px}}.plot.medio{height:520px}.plot.bajo{height:230px}
.ctrl{display:flex;flex-direction:column;gap:16px}.ctrl .bloque{border:1px solid var(--bd);border-radius:14px;padding:14px;background:var(--soft)}
.ctrl label.t{font-size:12px;color:var(--mu);font-weight:700;letter-spacing:.06em;text-transform:uppercase;display:block;margin-bottom:8px}
.ctrl .chk{font-size:14px;display:flex;gap:8px;align-items:center;margin:6px 0;cursor:pointer}
input[type=range]{width:100%;accent-color:var(--ac);margin:8px 0 2px}input[type=checkbox]{accent-color:var(--ac)}
.btn{appearance:none;border:1px solid var(--bd);background:var(--card);color:var(--tx);border-radius:10px;padding:7px 13px;font:600 13px Inter,sans-serif;cursor:pointer;transition:all .15s}
.btn:hover{border-color:var(--ac);color:var(--ac)}.btn.pri{background:var(--ac);border-color:var(--ac);color:#fff}.btn.pri:hover{background:var(--ac2);color:#fff}
.btn.mini{padding:4px 9px;font-size:12px}
.lectura{font:500 13px/1.75 "JetBrains Mono",monospace;background:var(--code);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;min-height:44px}
.fila{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
select{font:inherit;font-size:14px;padding:7px 9px;border-radius:10px;border:1px solid var(--bd);background:var(--card);color:var(--tx);width:100%}
.leyenda{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--mu);margin:4px 0 10px}.leyenda i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:6px;vertical-align:-1px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:920px){.grid2{grid-template-columns:1fr}}
.json-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.json{font:13px/1.6 "JetBrains Mono",ui-monospace,monospace;background:var(--code);border:1px solid var(--bd);border-radius:12px;padding:14px 16px 14px 30px;overflow:auto;max-height:72vh}
.json details{margin-left:18px}.json summary{cursor:pointer;list-style:none;margin-left:-18px}.json summary::-webkit-details-marker{display:none}
.json summary:before{content:"▸ ";color:var(--mu)}.json details[open]>summary:before{content:"▾ "}.json .h{margin-left:0}
.jk{color:var(--ac2)}.js{color:var(--str)}.jn{color:var(--min)}.jb{color:var(--silla)}.jz{color:var(--mu)}.jc{color:var(--mu);font-style:italic}
.warn{color:#a3621c;font-size:14px}
footer{color:var(--mu);font-size:13px;text-align:center;padding:4px 0 34px}
</style></head><body>
<header class="hero"><div class="wrap"><div class="eyebrow">__EYEBROW__</div><h1>__TITULO__</h1>
<div class="enunciado" id="enunciado"></div><div class="meta" id="meta"></div></div></header>
<nav class="tabs"><div class="wrap">
<button class="tab activo" data-tab="resumen"><span class="n">1</span>Resumen</button>
<button class="tab" data-tab="proc"><span class="n">2</span>Procedimiento</button>
<button class="tab" data-tab="g3d"><span class="n">3</span>Gráfico 3D dinámico</button>
<button class="tab" data-tab="g2d"><span class="n">4</span>Gráficos 2D</button>
<button class="tab" data-tab="json"><span class="n">5</span>JSON generado</button>
</div></nav>
<main class="wrap">
<section id="tab-resumen" class="panel activo"></section><section id="tab-proc" class="panel"></section>
<section id="tab-g3d" class="panel"></section><section id="tab-g2d" class="panel"></section><section id="tab-json" class="panel"></section>
</main>
<footer>__PIE__</footer>
<script>
const R = __RESULTADO__;
const D = __DATOS__;
const FUNCION_MCP = "__FUNCION__", NOMBRE_JSON = "__NOMBRE_JSON__";
/* ───────── utilidades comunes ───────── */
const $id = i => document.getElementById(i);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const COLOR = {min:css("--min"), max:css("--max"), silla:css("--silla"), ind:css("--ind"), sing:css("--sing"), ac:css("--ac"),
               ac2:css("--ac2"), sand:css("--sand"), tx:css("--tx"), mu:css("--mu"), bd:css("--bd"), soft:css("--soft")};
const TERRA = [[0,"#2c2420"],[0.15,"#4c2c21"],[0.32,"#7a3a24"],[0.5,"#ab4f2c"],[0.67,"#cf8660"],[0.83,"#e7bf9e"],[1,"#f7ece0"]];
const TERRA3D = [[0,"#3b1f17"],[0.2,"#6a3020"],[0.42,"#a0462a"],[0.62,"#c86d45"],[0.82,"#e3a47c"],[1,"#f1cfae"]];
const CUENCAS = ["#3f6e7d","#6b7a4f","#a07b4f","#5f6f8a","#8a5a44","#7a5873","#4f7d6a"];
const OSCURO = matchMedia("(prefers-color-scheme: dark)").matches;
const MACROS = {"\\R":"\\mathbb{R}"};
const tex = (s, d) => { try { return katex.renderToString(String(s), {displayMode:!!d, throwOnError:false, macros:MACROS}); } catch(e) { return String(s); } };
const esc = s => String(s).replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
const mt = s => String(s).replace(/\$\$([^$]+)\$\$/g, (_, m) => tex(m, true)).replace(/\$([^$]+)\$/g, (_, m) => tex(m))
                         .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>");
const eq = s => `<div class="eq">${tex(s, true)}</div>`;
const fmt = (v, p) => (v === null || v === undefined) ? "—" : (+v).toPrecision(p || 5).replace(/\.?0+(e|$)/, "$1");
const ejes3 = (t) => ({title:{text:t}, backgroundcolor:OSCURO ? "#221d19" : "#f8f2eb", showbackground:true, gridcolor:COLOR.bd, zerolinecolor:COLOR.mu});
const lay = extra => Object.assign({paper_bgcolor:"rgba(0,0,0,0)", plot_bgcolor:"rgba(0,0,0,0)",
    font:{family:"Inter, sans-serif", color:COLOR.tx, size:12}, margin:{l:52, r:20, t:20, b:44},
    legend:{orientation:"h", y:-0.14, font:{size:12}}, hoverlabel:{font:{family:"JetBrains Mono, monospace", size:12}},
    xaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}, extra || {});
const CFG = {responsive:true, displaylogo:false, modeBarButtonsToRemove:["lasso2d", "select2d"]};
/* ───────── pestañas (los gráficos se construyen al abrir su pestaña) ───────── */
const INIT = {}, HECHO = {}, PLOTS = {};
function mostrar(id) {
  if (!document.getElementById("tab-" + id)) id = "resumen";
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("activo", b.dataset.tab === id));
  document.querySelectorAll(".panel").forEach(p => p.classList.toggle("activo", p.id === "tab-" + id));
  if (!HECHO[id] && INIT[id]) { HECHO[id] = true; INIT[id](); }
  else (PLOTS[id] || []).forEach(d => Plotly.Plots.resize(d));
  try { history.replaceState(null, "", "#" + id); } catch (e) {}
}
document.querySelectorAll(".tab").forEach(b => b.onclick = () => mostrar(b.dataset.tab));

const reg = (tab, div) => ((PLOTS[tab] = PLOTS[tab] || []).push(div), div);
/* ───────── visor JSON ───────── */
function hojaJ(v) {
  if (v === null) return `<span class="jz">null</span>`;
  if (typeof v === "string") return `<span class="js">"${esc(v)}"</span>`;
  if (typeof v === "number") return `<span class="jn">${v}</span>`;
  return `<span class="jb">${v}</span>`;
}
function nodoJ(v, k, nivel) {
  const kk = k === undefined ? "" : `<span class="jk">"${esc(k)}"</span>: `;
  if (v === null || typeof v !== "object") return `<div>${kk}${hojaJ(v)}</div>`;
  const arr = Array.isArray(v), n = arr ? v.length : Object.keys(v).length, a = arr ? "[" : "{", c = arr ? "]" : "}";
  if (n === 0) return `<div>${kk}${a}${c}</div>`;
  if (arr && n <= 8 && v.every(x => x === null || typeof x !== "object")) return `<div>${kk}[${v.map(hojaJ).join(", ")}]</div>`;
  let hijos;
  if (arr && n > 40) hijos = `<div class="jc">… ${n} elementos, se muestran los 12 primeros …</div>` + v.slice(0, 12).map(x => nodoJ(x, undefined, nivel + 1)).join("");
  else hijos = (arr ? v.map(x => nodoJ(x, undefined, nivel + 1)) : Object.entries(v).map(([q, w]) => nodoJ(w, q, nivel + 1))).join("");
  return `<details ${nivel < 2 ? "open" : ""}><summary>${kk}${a} <span class="jc">${n} ${arr ? "elementos" : "claves"}</span></summary>${hijos}<div class="h">${c}</div></details>`;
}
INIT.json = () => {
  const P = $id("tab-json");
  P.innerHTML = `<div class="card"><h2>JSON generado</h2>
    <p class="sub">Salida exacta de <code>${FUNCION_MCP}</code>: es el objeto que el servidor MCP devolverá al modelo. Los valores exactos van como texto SymPy y LaTeX; los aproximados, como números.</p>
    <div class="json-bar"><button class="btn pri" id="jcop">Copiar</button><button class="btn" id="jbaj">Descargar .json</button>
    <button class="btn" id="jexp">Expandir todo</button><button class="btn" id="jcon">Contraer todo</button>
    <label class="fila" style="margin-left:auto;font-size:13px;color:var(--mu)"><input type="checkbox" id="jgra"> incluir los arreglos del gráfico</label></div>
    <div class="json" id="jarb"></div><p class="nota" id="jtam"></p></div>`;
  const obj = () => $id("jgra").checked ? Object.assign({}, R, {grafico: D}) : R;
  const pinta = () => { const o = obj(); $id("jarb").innerHTML = nodoJ(o, undefined, 0);
    $id("jtam").textContent = `Tamaño: ${(JSON.stringify(o).length / 1024).toFixed(1)} KB · ${Object.keys(o).length} claves de primer nivel`; };
  pinta(); $id("jgra").onchange = pinta;
  $id("jcop").onclick = () => { const t = JSON.stringify(obj(), null, 2), b = $id("jcop");
    const ok = () => { b.textContent = "¡Copiado!"; setTimeout(() => b.textContent = "Copiar", 1600); };
    if (navigator.clipboard) navigator.clipboard.writeText(t).then(ok, () => respaldo(t, ok)); else respaldo(t, ok); };
  const respaldo = (t, ok) => { const a = document.createElement("textarea"); a.value = t; document.body.appendChild(a); a.select();
    try { document.execCommand("copy"); ok(); } catch (e) {} a.remove(); };
  $id("jbaj").onclick = () => { const b = new Blob([JSON.stringify(obj(), null, 2)], {type:"application/json"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = NOMBRE_JSON; a.click(); };
  $id("jexp").onclick = () => $id("jarb").querySelectorAll("details").forEach(d => d.open = true);
  $id("jcon").onclick = () => $id("jarb").querySelectorAll("details").forEach(d => d.open = false);
};
/* ───────── reproductor genérico (botón ▶ + slider) ───────── */
function reproductor(boton, slider, alCambiar, paso) {
  let t = null;
  const parar = () => { clearInterval(t); t = null; boton.textContent = "▶ Reproducir"; };
  boton.onclick = () => {
    if (t) return parar();
    boton.textContent = "⏸ Pausar";
    t = setInterval(() => { let v = +slider.value + (paso || 1); if (v > +slider.max) v = +slider.min;
      slider.value = v; alCambiar(v); }, 40);
  };
  slider.oninput = () => alCambiar(+slider.value);
  return parar;
}
__JS_MODULO__
if (!window.Plotly) {
  const aviso = `<div class="card" style="border-color:var(--ac)"><h2>No se pudo cargar la librería de gráficos</h2>
    <p class="sub">Plotly.js se descarga de internet y no respondió (sin conexión, firewall o bloqueo del navegador). Las pestañas de Resumen, Procedimiento y JSON funcionan igual.</p>
    <p>Para ver los gráficos sin internet, genera la página en modo <b>offline</b>:</p>
    <p><code>pip install plotly</code><br><code>python metodos_${NOMBRE_JSON.replace("_resultado.json", "")}.py --demo 1 --html pagina.html --offline</code></p></div>`;
  INIT.g3d = () => { $id("tab-g3d").innerHTML = aviso; }; INIT.g2d = () => { $id("tab-g2d").innerHTML = aviso; };
}
mostrar(location.hash.slice(1) || "resumen");
</script></body></html>"""


def _json_seguro(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")


_PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>\n'
    '<script>window.Plotly || document.write(\'<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"><\\/script>\')</script>\n'
    '<script>window.Plotly || document.write(\'<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.27.0/plotly.min.js"><\\/script>\')</script>')


def _plotly_local() -> str | None:
    """Código de Plotly.js incluido en el paquete de Python 'plotly' (pip install plotly)."""
    try:
        import importlib.resources as ir
        return (ir.files("plotly") / "package_data" / "plotly.min.js").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def _pagina(R: dict, D: dict, titulo: str, eyebrow: str, funcion: str, nombre_json: str, js_modulo: str,
            pie: str, offline: bool = False) -> str:
    etiqueta = _PLOTLY_CDN
    if offline:
        codigo = _plotly_local()
        if codigo is None:
            raise RuntimeError("Modo --offline: instala el paquete con  pip install plotly  y vuelve a intentar.")
        etiqueta = "<script>" + codigo.replace("</script", "<\\/script") + "</script>"
    return (_WEB_PLANTILLA.replace("__PLOTLY__", etiqueta, 1).replace("__JS_MODULO__", js_modulo)
            .replace("__TITULO__", titulo).replace("__EYEBROW__", eyebrow).replace("__PIE__", pie)
            .replace("__FUNCION__", funcion).replace("__NOMBRE_JSON__", nombre_json)
            .replace("__RESULTADO__", _json_seguro(R)).replace("__DATOS__", _json_seguro(D)))


_JS_FRENET = r"""/* ═════════════ Módulo: Triedro de Frenet ═════════════ */
const E = R.entrada, P0 = R.en_t0, TL = E.parametro_latex, T0L = E.t0_latex;
const CT = COLOR.ac, CN = COLOR.min, CB = COLOR.sing;          // T terracota · N petróleo · B ocre
const tieneN = !!(P0 && P0.N);
const vl = v => v ? v.latex : "\\text{no definido}";
const cl = v => v ? v.componentes_latex : ["", "", ""];
const vmat = (f2, f3) => "\\begin{vmatrix} \\mathbf{i} & \\mathbf{j} & \\mathbf{k} \\\\ " + f2.join(" & ") + " \\\\ " + f3.join(" & ") + " \\end{vmatrix}";
const vmat3 = (a, b, c) => "\\begin{vmatrix} " + a.join(" & ") + " \\\\ " + b.join(" & ") + " \\\\ " + c.join(" & ") + " \\end{vmatrix}";
const dT = (n) => R.derivadas[n - 1].vector;
const approx = v => v && v.num ? "\\approx \\left(" + v.num.map(x => fmt(x, 4)).join(",\\ ") + "\\right)" : "";

$id("enunciado").innerHTML = tex("\\mathbf{r}(" + TL + ") = " + E.r_latex + "\\qquad " + TL + "_0 = " + T0L);
$id("meta").innerHTML = `<span>curva: ${esc(R.tipo)}</span><span>parámetro ${esc(E.parametro)}</span>` +
  (Object.keys(E.constantes).length ? `<span>constantes: ${Object.entries(E.constantes).map(([k, v]) => k + " = " + v).join(", ")} (gráficos)</span>` : "") +
  `<span>longitud en el rango ≈ ${fmt(D.longitud_rango, 5)}</span>`;

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const n = x => x ? fmt(x.num, 5) : "—";
  const K = [[esc(R.tipo), "tipo de curva", COLOR.ac], [n(P0.curvatura), `curvatura κ(${esc(E.t0)})`, CT],
             [tieneN ? n(P0.torsion) : "—", `torsión τ(${esc(E.t0)})`, CN], [tieneN ? n(P0.radio_curvatura) : "∞", "radio de curvatura ρ", CB],
             [n(P0.rapidez), "rapidez ‖r′(t₀)‖", COLOR.silla]];
  let h = `<div class="kpis">${K.map(([v, t, c]) => `<div class="kpi" style="--c:${c}"><b style="font-size:${String(v).length > 10 ? 20 : 30}px">${v}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="grid2"><div class="card"><h2>Triedro de Frenet en t₀ = ${esc(E.t0)}</h2><p class="sub">Base ortonormal móvil: T apunta hacia donde avanza la curva, N hacia donde se curva y B = T × N es perpendicular al plano en que se curva.</p><table class="kv">
    <tr><td>punto</td><td>${tex("\\mathbf r(" + T0L + ") = " + vl(P0.punto))}</td></tr>
    <tr><td><b style="color:${CT}">T</b> tangente</td><td>${tex(vl(P0.T))}<div class="nota">${tex(approx(P0.T))}</div></td></tr>
    <tr><td><b style="color:${CN}">N</b> normal</td><td>${tex(vl(P0.N))}<div class="nota">${tex(approx(P0.N))}</div></td></tr>
    <tr><td><b style="color:${CB}">B</b> binormal</td><td>${tex(vl(P0.B))}<div class="nota">${tex(approx(P0.B))}</div></td></tr></table></div>
    <div class="card"><h2>Curvatura y torsión</h2><p class="sub">κ mide cuánto se dobla la curva; τ, cuánto se “retuerce” fuera de su plano.</p><table class="kv">
    <tr><td>κ(t)</td><td>${tex("\\kappa(" + TL + ") = " + R.curvatura.latex)}</td></tr>
    ${R.torsion ? `<tr><td>τ(t)</td><td>${tex("\\tau(" + TL + ") = " + R.torsion.latex)}</td></tr>` : ""}
    <tr><td>en t₀</td><td>${tex("\\kappa = " + (P0.curvatura ? P0.curvatura.latex : "0") + (tieneN ? ",\\quad \\tau = " + P0.torsion.latex : ""))}</td></tr>
    ${tieneN ? `<tr><td>círculo osculador</td><td>${tex("\\rho = " + P0.radio_curvatura.latex + ",\\quad C = " + P0.centro_curvatura.latex)}</td></tr>` : ""}
    ${R.longitud_arco.s_t_latex ? `<tr><td>longitud de arco</td><td>${tex("s(" + TL + ") = " + R.longitud_arco.s_t_latex)}</td></tr>` : ""}</table></div></div>`;
  if (P0.planos) {
    const fila = (k, nom, perp, col) => P0.planos[k] ? `<tr><td><span class="chip" style="--c:${col}">${nom}</span></td><td>⟂ ${perp}</td><td>${tex(P0.planos[k].ecuacion_latex)}</td></tr>` : "";
    h += `<div class="card"><h2>Planos fundamentales en t₀</h2><table class="kv">${fila("osculador", "osculador", "B (contiene T y N)", CB)}${fila("normal", "normal", "T (contiene N y B)", CT)}${fila("rectificante", "rectificante", "N (contiene T y B)", CN)}</table></div>`;
  }
  const V = R.verificacion;
  h += `<div class="grid2"><div class="card"><h2>Clasificación</h2>${R.clasificacion.map(c => `<p>${esc(c)}</p>`).join("")}` +
    (R.puntos_singulares.length ? `<p>Puntos singulares: ${R.puntos_singulares.map(p => tex(TL + " = " + p.latex)).join(", ")}</p>` : "") +
    (R.puntos_inflexion.length ? `<p>Puntos de inflexión (κ = 0): ${R.puntos_inflexion.map(p => tex(TL + " = " + p.latex)).join(", ")}</p>` : "") + `</div>`;
  h += `<div class="card"><h2>Verificación independiente</h2>` + (V.frenet_serret_t0 ? `<table class="kv">` +
    Object.entries(V.frenet_serret_t0).map(([k, e]) => `<tr><td>${esc(k)}</td><td>error ${e.toExponential(1)} ${e < 1e-25 ? "✔" : "✘"}</td></tr>`).join("") +
    `<tr><td>T, N, B ortonormales, T × N = B</td><td>${V.correcto ? "✔" : "✘"}</td></tr></table><p class="nota">${esc(V.metodo || "")}</p>` : `<p class="nota">No aplica en este punto.</p>`) + `</div></div>`;
  if (R.advertencias.length) h += `<div class="card"><h2>Advertencias</h2>${R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("")}</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto de SymPy. Las fórmulas valen para cualquier parametrización regular (no hace falta que sea por longitud de arco).</p></div>`, k = 0;
  const paso = (t, c) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${c}</div></div>`;
  paso("Curva parametrizada", eq("\\mathbf r(" + TL + ") = " + E.r_latex) +
    (E.curva_plana_entrada ? `<p class="nota">Se ingresaron 2 componentes: la curva se trata en ℝ³ con z = 0.</p>` : "") +
    `<p>${mt("Punto de estudio: $" + TL + "_0 = " + T0L + "$, que da $\\mathbf r(" + T0L + ") = " + vl(P0.punto) + "$.")}</p>`);
  paso("Derivadas sucesivas", eq("\\begin{aligned} \\mathbf r'(" + TL + ") &= " + vl(dT(1)) + "\\\\[8pt] \\mathbf r''(" + TL + ") &= " + vl(dT(2)) +
    "\\\\[8pt] \\mathbf r'''(" + TL + ") &= " + vl(dT(3)) + "\\end{aligned}"));
  let s = eq("\\lVert \\mathbf r'(" + TL + ")\\rVert = \\sqrt{" + cl(dT(1)).map(c => "\\left(" + c + "\\right)^{2}").join(" + ") + "} = " + R.rapidez.latex);
  s += `<p>${mt("Es la **rapidez** con que se recorre la curva; el elemento de longitud de arco es $ds = \\lVert \\mathbf r'\\rVert\\, d" + TL + "$.")}</p>`;
  if (R.longitud_arco.s_t_latex) s += eq("s(" + TL + ") = \\int_{" + T0L + "}^{" + TL + "} \\lVert \\mathbf r'(u)\\rVert\\, du = " + R.longitud_arco.s_t_latex);
  paso("Rapidez y longitud de arco", s);
  paso("Vector tangente unitario $\\mathbf T$", eq("\\mathbf T = \\frac{\\mathbf r'}{\\lVert \\mathbf r'\\rVert} = " + vl(R.T)));
  paso("Producto vectorial $\\mathbf r' \\times \\mathbf r''$", eq("\\mathbf r' \\times \\mathbf r'' = " + vmat(cl(dT(1)), cl(dT(2))) + " = " + vl(R.producto_cruz)) +
    eq("\\lVert \\mathbf r' \\times \\mathbf r''\\rVert = " + R.norma_cruz.latex) +
    `<p class="nota">${mt("Si $\\mathbf r' \\times \\mathbf r'' = \\mathbf 0$ la curva no se dobla en ese punto (recta o inflexión) y $\\mathbf N$, $\\mathbf B$ no existen.")}</p>`);
  if (R.B) {
    paso("Vector binormal $\\mathbf B$", eq("\\mathbf B = \\frac{\\mathbf r' \\times \\mathbf r''}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert} = " + vl(R.B)));
    paso("Vector normal principal $\\mathbf N$", `<p>${mt("Se usa $\\mathbf N = \\mathbf B \\times \\mathbf T$; con la identidad del doble producto vectorial queda una fórmula sin normalizar dos veces:")}</p>` +
      eq("\\mathbf N = \\frac{(\\mathbf r' \\times \\mathbf r'') \\times \\mathbf r'}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert\\,\\lVert \\mathbf r'\\rVert} = \\frac{(\\mathbf r'\\cdot\\mathbf r')\\,\\mathbf r'' - (\\mathbf r'\\cdot\\mathbf r'')\\,\\mathbf r'}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert\\,\\lVert \\mathbf r'\\rVert}") +
      eq("(\\mathbf r'\\cdot\\mathbf r')\\,\\mathbf r'' - (\\mathbf r'\\cdot\\mathbf r'')\\,\\mathbf r' = " + vl(R.N_numerador)) + eq("\\mathbf N = " + vl(R.N)));
  }
  paso("Curvatura $\\kappa$", eq("\\kappa(" + TL + ") = \\frac{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert}{\\lVert \\mathbf r'\\rVert^{3}} = " + R.curvatura.latex));
  if (R.torsion) paso("Torsión $\\tau$", `<p>${mt("El numerador es el **triple producto escalar**, que es el determinante formado por $\\mathbf r'$, $\\mathbf r''$ y $\\mathbf r'''$:")}</p>` +
    eq("(\\mathbf r' \\times \\mathbf r'')\\cdot \\mathbf r''' = " + vmat3(cl(dT(1)), cl(dT(2)), cl(dT(3))) + " = " + R.triple_producto.latex) +
    eq("\\tau(" + TL + ") = \\frac{(\\mathbf r' \\times \\mathbf r'')\\cdot \\mathbf r'''}{\\lVert \\mathbf r' \\times \\mathbf r''\\rVert^{2}} = " + R.torsion.latex));
  let e = eq("\\begin{aligned} \\mathbf r'(" + T0L + ") &= " + vl(P0.d1) + "\\\\ \\mathbf r''(" + T0L + ") &= " + vl(P0.d2) + "\\\\ \\mathbf r'''(" + T0L + ") &= " + vl(P0.d3) + "\\end{aligned}");
  e += eq("\\lVert \\mathbf r'(" + T0L + ")\\rVert = " + (P0.rapidez ? P0.rapidez.latex : "0") + ",\\qquad \\mathbf T(" + T0L + ") = " + vl(P0.T));
  if (tieneN) e += eq("\\mathbf r' \\times \\mathbf r'' \\,(" + T0L + ") = " + vl(P0.cruz) + ",\\qquad \\lVert\\cdot\\rVert = " + P0.norma_cruz.latex) +
    eq("\\mathbf N(" + T0L + ") = " + vl(P0.N) + ",\\qquad \\mathbf B(" + T0L + ") = " + vl(P0.B)) + eq(P0.calculo_kappa_latex) + eq(P0.calculo_tau_latex) +
    `<p>${mt("**Círculo osculador:** es el círculo que mejor aproxima a la curva en $" + TL + "_0$. Radio $\\rho = 1/\\kappa$ y centro sobre la normal:")}</p>` +
    eq("\\rho = \\frac{1}{\\kappa} = " + P0.radio_curvatura.latex + ",\\qquad C = \\mathbf r(" + T0L + ") + \\rho\\,\\mathbf N(" + T0L + ") = " + vl(P0.centro_curvatura));
  paso("Evaluación en $" + TL + "_0 = " + T0L + "$", e);
  if (P0.planos) {
    const pl = (k, nom, n, col) => P0.planos[k] ? `<div class="idea" style="border-color:${col}"><b style="color:${col}">Plano ${nom}</b> — ${mt("normal $\\propto " + n + "$:")}` +
      eq("\\mathbf n = " + P0.planos[k].normal_latex + ",\\qquad \\mathbf n \\cdot (\\mathbf X - \\mathbf r(" + T0L + ")) = 0 \\;\\Longrightarrow\\; " + P0.planos[k].ecuacion_latex) + `</div>` : "";
    paso("Planos fundamentales", `<p>${mt("Cada plano pasa por $\\mathbf r(" + TL + "_0)$ y es perpendicular a uno de los vectores del triedro (se usa un múltiplo del vector con coeficientes simples):")}</p>` +
      pl("osculador", "osculador (contiene T y N)", "\\mathbf B \\propto \\mathbf r'\\times\\mathbf r''", CB) +
      pl("normal", "normal (contiene N y B)", "\\mathbf T \\propto \\mathbf r'", CT) +
      pl("rectificante", "rectificante (contiene T y B)", "\\mathbf N \\propto (\\mathbf r'\\times\\mathbf r'')\\times\\mathbf r'", CN));
  }
  if (R.verificacion.frenet_serret_t0) paso("Fórmulas de Frenet–Serret (verificación)",
    eq("\\begin{pmatrix} \\mathbf T' \\\\ \\mathbf N' \\\\ \\mathbf B' \\end{pmatrix} = \\lVert \\mathbf r'\\rVert \\begin{pmatrix} 0 & \\kappa & 0 \\\\ -\\kappa & 0 & \\tau \\\\ 0 & -\\tau & 0 \\end{pmatrix} \\begin{pmatrix} \\mathbf T \\\\ \\mathbf N \\\\ \\mathbf B \\end{pmatrix}") +
    `<p>${mt("Se comprobaron en $" + TL + "_0$ con 50 dígitos, derivando $\\mathbf T$, $\\mathbf N$, $\\mathbf B$ numéricamente (de forma independiente de las fórmulas anteriores):")}</p><table class="kv" style="max-width:520px">` +
    Object.entries(R.verificacion.frenet_serret_t0).map(([q, er]) => `<tr><td>${esc(q)}</td><td>error = ${er.toExponential(1)} ${er < 1e-25 ? "✔" : "✘"}</td></tr>`).join("") + `</table>`);
  paso("Clasificación de la curva", R.clasificacion.map(c => `<p>${esc(c)}</p>`).join("") +
    `<div class="idea">${mt("**Teorema fundamental de curvas:** $\\kappa(s)$ y $\\tau(s)$ determinan la curva salvo movimientos rígidos. $\\tau \\equiv 0$ ⇔ curva plana; $\\kappa$ y $\\tau$ constantes ⇔ hélice circular; $\\tau/\\kappa$ constante ⇔ hélice generalizada (Lancret).")}</div>` +
    R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join(""));
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
const arr = a => a.map(v => v === null ? NaN : v);
const nPts = D.t.length;
const pt = i => [D.x[i], D.y[i], D.z[i]];
const vec3 = (M, i) => [M[0][i], M[1][i], M[2][i]];
const suma = (a, b, s) => a.map((q, j) => q + s * b[j]);
const valido = v => v.every(q => q !== null && isFinite(q));

INIT.g3d = () => {
  const P = $id("tab-g3d");
  const L = 0.2 * D.diag;
  P.innerHTML = `<div class="card"><h2>El triedro de Frenet recorriendo la curva</h2>
    <p class="sub">La curva está coloreada según su curvatura κ (más claro = se dobla más). Al reproducir, el triedro <b style="color:${CT}">T</b>, <b style="color:${CN}">N</b>, <b style="color:${CB}">B</b> viaja por la curva; el círculo punteado es el círculo osculador (el que mejor la aproxima) y los planos se mueven con el punto.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Recorrer la curva</label><div class="fila"><button class="btn pri" id="bFr">▶ Reproducir</button><button class="btn" id="bT0">ir a t₀</button></div>
        <input type="range" id="sFr" min="0" max="${nPts - 1}" value="${D.t0.indice}"><div class="lectura" id="lFr"></div></div>
      <div class="bloque"><label class="t">κ(t) y τ(t)</label><div id="perfil" class="plot bajo"></div></div>
      <div class="bloque"><label class="t">Mostrar</label>
        <label class="chk"><input type="checkbox" id="cTri" checked> triedro T, N, B</label>
        <label class="chk"><input type="checkbox" id="cCir" checked> círculo osculador</label>
        <label class="chk"><input type="checkbox" id="cPO" checked> plano osculador <i style="color:${CB}">●</i></label>
        <label class="chk"><input type="checkbox" id="cPN"> plano normal <i style="color:${CT}">●</i></label>
        <label class="chk"><input type="checkbox" id="cPR"> plano rectificante <i style="color:${CN}">●</i></label>
        <label class="chk"><input type="checkbox" id="cEvo"> evoluta (centros de curvatura)</label>
        <label class="t" style="margin-top:10px">Color de la curva</label><select id="sCol"><option value="kappa">curvatura κ</option><option value="tau">torsión τ</option><option value="rapidez">rapidez ‖r′‖</option></select></div>
    </div></div></div>`;
  const X = arr(D.x), Y = arr(D.y), Z = arr(D.z);
  const tr = [];
  tr.push({type:"scatter3d", mode:"lines", x:X, y:Y, z:Z, name:"r(t)", hoverinfo:"skip",
    line:{width:8, color:arr(D.kappa), colorscale:TERRA, showscale:true, colorbar:{title:{text:"κ"}, thickness:12, len:0.55, x:1.0}}});
  tr.push({type:"scatter3d", mode:"lines", x:arr(D.centro[0]), y:arr(D.centro[1]), z:arr(D.centro[2]), line:{color:CN, width:3, dash:"dot"}, name:"evoluta", visible:false, hoverinfo:"skip"});
  const I0 = tr.length;                      // 0..2: ejes T N B · 3..5: conos · 6: círculo · 7..9: planos · 10: punto
  [["T", CT], ["N", CN], ["B", CB]].forEach(([nm, c]) => tr.push({type:"scatter3d", mode:"lines+text", x:[0, 0], y:[0, 0], z:[0, 0], text:["", nm],
    textposition:"top center", textfont:{color:c, size:15}, line:{color:c, width:9}, name:nm, hoverinfo:"skip"}));
  [CT, CN, CB].forEach(c => tr.push({type:"cone", x:[0], y:[0], z:[0], u:[1], v:[0], w:[0], anchor:"tip", sizemode:"absolute", sizeref:L * 0.28,
    colorscale:[[0, c], [1, c]], showscale:false, hoverinfo:"skip", name:"", showlegend:false}));
  tr.push({type:"scatter3d", mode:"lines", x:[], y:[], z:[], line:{color:CN, width:4, dash:"dash"}, name:"círculo osculador", hoverinfo:"skip"});
  [[CB, "plano osculador", true], [CT, "plano normal", false], [CN, "plano rectificante", false]].forEach(([c, nm, vis]) =>
    tr.push({type:"mesh3d", x:[0, 0, 0, 0], y:[0, 0, 0, 0], z:[0, 0, 0, 0], i:[0, 0], j:[1, 2], k:[2, 3], color:c, opacity:0.28, name:nm, visible:vis, hoverinfo:"skip", flatshading:true}));
  tr.push({type:"scatter3d", mode:"markers", x:[0], y:[0], z:[0], marker:{size:7, color:"#fff", line:{color:"#2b2420", width:3}}, name:"punto", hoverinfo:"skip"});
  if (D.t0.r) tr.push({type:"scatter3d", mode:"markers+text", x:[D.t0.r[0]], y:[D.t0.r[1]], z:[D.t0.r[2]], text:["t₀"], textposition:"bottom center",
    textfont:{color:COLOR.tx, size:13}, marker:{size:5, color:COLOR.tx}, name:"t₀", hoverinfo:"skip"});
  // rango y proporciones que respetan la geometría (con un mínimo para curvas planas)
  const lim = (A) => { const f = A.filter(isFinite); return [Math.min(...f) - L * 1.2, Math.max(...f) + L * 1.2]; };
  const rx = lim(X), ry = lim(Y), rz = lim(Z), ex = [rx, ry, rz].map(r => r[1] - r[0]), m = Math.max(...ex);
  const ar = ex.map(e => Math.max(e / m, 0.3));
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:Object.assign(ejes3("x"), {range:rx}), yaxis:Object.assign(ejes3("y"), {range:ry}), zaxis:Object.assign(ejes3("z"), {range:rz}),
           aspectmode:"manual", aspectratio:{x:ar[0] * 1.2, y:ar[1] * 1.2, z:ar[2] * 1.2}, camera:{eye:{x:1.15, y:-1.15, z:0.75}}}}), CFG);
  // perfil κ, τ
  const perf = reg("g3d", $id("perfil"));
  const pTr = [{x:D.t, y:D.kappa, mode:"lines", line:{color:CT, width:2.5}, name:"κ"}];
  if (!D.plana) pTr.push({x:D.t, y:D.tau, mode:"lines", line:{color:CN, width:2.5}, name:"τ"});
  pTr.push({x:[D.t[D.t0.indice]], y:[D.kappa[D.t0.indice]], mode:"markers", marker:{size:10, color:"#fff", line:{color:"#2b2420", width:2.5}}, showlegend:false});
  const vline = x => ({type:"line", x0:x, x1:x, yref:"paper", y0:0, y1:1, line:{color:COLOR.mu, width:1, dash:"dot"}});
  Plotly.newPlot(perf, pTr, lay({margin:{l:36, r:8, t:6, b:28}, legend:{orientation:"h", y:1.15, x:0}, shapes:[vline(D.t[D.t0.indice])],
    xaxis:{title:{text:E.parametro, font:{size:11}}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}), {displayModeBar:false, responsive:true});
  const iPer = pTr.length - 1;
  const mover = i => {
    const p = pt(i), T = vec3(D.T, i), N = vec3(D.N, i), B = vec3(D.B, i), k = D.kappa[i];
    const ok = valido(p) && valido(T), okN = ok && valido(N) && valido(B);
    const fx = [], fy = [], fz = [], cu = [];
    [T, N, B].forEach((v, j) => { const q = (j === 0 ? ok : okN) ? suma(p, v, L) : p; fx.push([p[0], q[0]]); fy.push([p[1], q[1]]); fz.push([p[2], q[2]]);
      cu.push((j === 0 ? ok : okN) ? v : [0, 0, 0]); });
    Plotly.restyle(g3, {x:fx, y:fy, z:fz}, [I0, I0 + 1, I0 + 2]);
    Plotly.restyle(g3, {x:[[fx[0][1]], [fx[1][1]], [fx[2][1]]], y:[[fy[0][1]], [fy[1][1]], [fy[2][1]]], z:[[fz[0][1]], [fz[1][1]], [fz[2][1]]],
      u:cu.map(v => [v[0]]), v:cu.map(v => [v[1]]), w:cu.map(v => [v[2]])}, [I0 + 3, I0 + 4, I0 + 5]);
    // círculo osculador
    let cx = [], cy = [], cz = [];
    const rho = 1 / k, C = vec3(D.centro, i);
    if (okN && isFinite(rho) && valido(C)) for (let a = 0; a <= 96; a++) { const th = 2 * Math.PI * a / 96;
      const q = p.map((_, j) => C[j] + rho * (-Math.cos(th) * N[j] + Math.sin(th) * T[j])); cx.push(q[0]); cy.push(q[1]); cz.push(q[2]); }
    Plotly.restyle(g3, {x:[cx], y:[cy], z:[cz]}, [I0 + 6]);
    // planos: cuadrados centrados en el punto, generados por dos vectores del triedro
    const s = L * 0.95, cuad = (u, v) => [suma(suma(p, u, -s), v, -s), suma(suma(p, u, s), v, -s), suma(suma(p, u, s), v, s), suma(suma(p, u, -s), v, s)];
    const pls = okN ? [cuad(T, N), cuad(N, B), cuad(T, B)] : [[p, p, p, p], [p, p, p, p], [p, p, p, p]];
    Plotly.restyle(g3, {x:pls.map(q => q.map(w => w[0])), y:pls.map(q => q.map(w => w[1])), z:pls.map(q => q.map(w => w[2]))}, [I0 + 7, I0 + 8, I0 + 9]);
    Plotly.restyle(g3, {x:[[p[0]]], y:[[p[1]]], z:[[p[2]]]}, [I0 + 10]);
    Plotly.restyle(perf, {x:[[D.t[i]]], y:[[k]]}, [iPer]); Plotly.relayout(perf, {shapes:[vline(D.t[i])]});
    $id("lFr").innerHTML = `${esc(E.parametro)} = ${fmt(D.t[i], 5)}<br>r = (${p.map(q => fmt(q, 4)).join(", ")})<br>‖r′‖ = ${fmt(D.rapidez[i], 5)}<br>` +
      `<span style="color:${CT}">κ = ${fmt(k, 5)}</span>` + (D.plana ? "" : ` · <span style="color:${CN}">τ = ${fmt(D.tau[i], 5)}</span>`) +
      `<br>ρ = ${okN && isFinite(rho) ? fmt(rho, 5) : "∞"}` + (okN ? "" : `<br><b class="warn">κ = 0: N y B no existen aquí</b>`);
  };
  reproductor($id("bFr"), $id("sFr"), mover, Math.max(1, Math.round(nPts / 320)));
  mover(D.t0.indice);
  $id("bT0").onclick = () => { $id("sFr").value = D.t0.indice; mover(D.t0.indice); };
  $id("cTri").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0, I0 + 1, I0 + 2, I0 + 3, I0 + 4, I0 + 5]);
  $id("cCir").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0 + 6]);
  [["cPO", 7], ["cPN", 8], ["cPR", 9]].forEach(([id, j]) => $id(id).onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [I0 + j]));
  $id("cEvo").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [1]);
  $id("sCol").onchange = e => { const k = e.target.value;
    Plotly.restyle(g3, {"line.color":[arr(D[k])], "line.colorbar.title.text":[{kappa:"κ", tau:"τ", rapidez:"‖r′‖"}[k]]}, [0]); };
};

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  P.innerHTML = `<div class="grid2"><div class="card"><h2>Curvatura y torsión</h2><p class="sub">La línea vertical marca t₀; los puntos grises, inflexiones (κ = 0).</p><div id="gk" class="plot medio"></div></div>
    <div class="card"><h2>Rapidez ‖r′(t)‖</h2><p class="sub">Área bajo la curva = longitud de arco (≈ ${fmt(D.longitud_rango, 6)} en el rango mostrado).</p><div id="gv" class="plot medio"></div></div></div>
    <div class="card"><h2>Proyecciones en los planos coordenados</h2><p class="sub">Curva coloreada por κ, evoluta punteada y, en t₀, T (terracota) y N (petróleo) proyectados con su círculo osculador.</p><div class="grid2" id="proy"></div></div>`;
  const t0 = D.t0, vl2 = x => ({type:"line", x0:x, x1:x, yref:"paper", y0:0, y1:1, line:{color:COLOR.mu, width:1.2, dash:"dash"}});
  const kt = [{x:D.t, y:D.kappa, mode:"lines", line:{color:CT, width:3}, name:"κ(t)"}];
  if (!D.plana) kt.push({x:D.t, y:D.tau, mode:"lines", line:{color:CN, width:3}, name:"τ(t)"});
  if (D.inflexiones.length) kt.push({x:D.inflexiones, y:D.inflexiones.map(() => 0), mode:"markers", marker:{size:10, color:COLOR.ind}, name:"inflexión"});
  Plotly.newPlot(reg("g2d", $id("gk")), kt, lay({shapes:t0.t !== null ? [vl2(t0.t)] : [], xaxis:{title:{text:E.parametro}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, zerolinecolor:COLOR.mu}}), CFG);
  Plotly.newPlot(reg("g2d", $id("gv")), [{x:D.t, y:D.rapidez, mode:"lines", fill:"tozeroy", fillcolor:"rgba(176,80,44,.15)", line:{color:CT, width:3}, name:"‖r′‖"}],
    lay({shapes:t0.t !== null ? [vl2(t0.t)] : [], xaxis:{title:{text:E.parametro}, gridcolor:COLOR.bd}, yaxis:{gridcolor:COLOR.bd, rangemode:"tozero"}}), CFG);
  const L = 0.16 * D.diag, C3 = [D.x, D.y, D.z];
  [[0, 1], [0, 2], [1, 2]].forEach(([a, b]) => {
    const d = document.createElement("div"); d.className = "plot medio"; $id("proy").appendChild(d);
    const nm = ["x", "y", "z"], tr = [{type:"scatter", mode:"markers", x:C3[a], y:C3[b], marker:{size:3.5, color:arr(D.kappa), colorscale:TERRA}, name:"r(t)", hoverinfo:"skip"},
      {type:"scatter", mode:"lines", x:D.centro[a], y:D.centro[b], line:{color:CN, width:1.5, dash:"dot"}, name:"evoluta", hoverinfo:"skip"}];
    if (t0.r && t0.T) {
      const p = t0.r;
      [[t0.T, CT, "T"], [t0.N, CN, "N"]].forEach(([v, c, n]) => { if (v && valido(v)) tr.push({type:"scatter", mode:"lines+markers", x:[p[a], p[a] + L * v[a]], y:[p[b], p[b] + L * v[b]],
        line:{color:c, width:4}, marker:{size:[0, 10], symbol:"arrow", angleref:"previous", color:c}, name:n}); });
      if (t0.N && valido(t0.N) && t0.rho && t0.rho < 3 * D.diag) { const cx = [], cy = [];
        for (let q = 0; q <= 120; q++) { const th = 2 * Math.PI * q / 120; cx.push(t0.centro[a] + t0.rho * (-Math.cos(th) * t0.N[a] + Math.sin(th) * t0.T[a]));
          cy.push(t0.centro[b] + t0.rho * (-Math.cos(th) * t0.N[b] + Math.sin(th) * t0.T[b])); }
        tr.push({type:"scatter", mode:"lines", x:cx, y:cy, line:{color:CN, width:1.5, dash:"dash"}, name:"círculo osculador (proyección)"}); }
      tr.push({type:"scatter", mode:"markers", x:[p[a]], y:[p[b]], marker:{size:10, color:"#fff", line:{color:"#2b2420", width:2}}, name:"r(t₀)"});
    }
    Plotly.newPlot(reg("g2d", d), tr, lay({showlegend:false, title:{text:`plano ${nm[a]}${nm[b]}`, font:{size:13}}, margin:{l:46, r:10, t:40, b:40},
      xaxis:{title:{text:nm[a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:nm[b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG);
  });
};
"""


def exportar_html(C: CurvaFrenet, ruta: str, datos: dict | None = None, offline: bool = False) -> str:
    """Página web autocontenida: resumen, procedimiento en LaTeX, 3D dinámico, 2D y JSON."""
    D = datos or datos_grafico(C)
    html = _pagina(a_dict(C), D, titulo="Triedro de Frenet, curvatura y torsión",
                   eyebrow="Geometría diferencial de curvas · Cálculo exacto con SymPy",
                   funcion="resolver_frenet()", nombre_json="frenet_resultado.json", js_modulo=_JS_FRENET,
                   pie="Generado por metodos_frenet.py · Grupo 06 · Frenet, Lagrange y Puntos Críticos",
                   offline=offline)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# 9. Reporte de terminal
# ════════════════════════════════════════════════════════════════════════════
def _pp(e, ascii_=False):
    return sp.pretty(e, use_unicode=not ascii_)


def _bl(txt, sang="   "):
    return sang + txt.replace("\n", "\n" + sang)


def _vt(v):
    return "(" + ", ".join(str(c) for c in v) + ")"


def reporte_texto(C: CurvaFrenet, ascii_: bool = False, detalle: bool = True) -> str:
    L = "=" * 78
    t = C.t
    s = [L, " TRIEDRO DE FRENET · CURVATURA · TORSIÓN", L, f"r({t}) = {_vt(C.r)}      t0 = {C.t0}"]
    if C.constantes:
        s.append("constantes (positivas): " + ", ".join(map(str, C.constantes)) +
                 "   valores usados en gráficos: " + ", ".join(f"{k}={v:g}" for k, v in C.valores.items()))
    s += ["", "1) Derivadas:", f"   r'   = {_vt(C.d1)}", f"   r''  = {_vt(C.d2)}", f"   r''' = {_vt(C.d3)}",
          "", "2) Rapidez  ‖r'‖ =", _bl(_pp(C.rapidez, ascii_))]
    if C.s_t is not None:
        s.append(f"   Longitud de arco desde t0:  s({t}) = {C.s_t}")
    s += ["", "3) r' × r'' = " + _vt(C.cruz), "   ‖r' × r''‖ =", _bl(_pp(C.norma_cruz, ascii_)),
          f"   (r' × r'') · r''' = {C.triple}", "", "4) Triedro de Frenet (general):"]
    if detalle:
        s += ["   T =", _bl(_pp(C.T.T, ascii_), "      ")]
        if not C.recta:
            s += ["   N =", _bl(_pp(C.N.T, ascii_), "      "), "   B =", _bl(_pp(C.B.T, ascii_), "      ")]
    s += ["", "5) Curvatura  κ = ‖r'×r''‖/‖r'‖³ =", _bl(_pp(C.kappa, ascii_))]
    if not C.recta:
        s += ["   Torsión  τ = (r'×r'')·r'''/‖r'×r''‖² =", _bl(_pp(C.tau, ascii_))]
    E = C.en_t0
    s += ["", f"6) En t0 = {C.t0}:", f"   r(t0)   = {_vt(E['r'])}"]
    if "T" in E:
        s.append(f"   ‖r'(t0)‖ = {E['rapidez']}")
        s.append(f"   T(t0) = {_vt(E['T'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['T'].subs(C.valores)))}")
    if "N" in E:
        s += [f"   N(t0) = {_vt(E['N'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['N'].subs(C.valores)))}",
              f"   B(t0) = {_vt(E['B'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['B'].subs(C.valores)))}",
              f"   κ(t0) = {E['kappa']}   ≈ {_num(E['kappa'].subs(C.valores)):.8g}",
              f"   τ(t0) = {E['tau']}   ≈ {_num(E['tau'].subs(C.valores)):.8g}",
              f"   radio de curvatura ρ = {E['rho']},  centro de curvatura C = {_vt(E['centro'])}",
              "", "7) Planos en t0:",
              f"   osculador    (⟂ B): {E['plano_osculador']['lhs']} = {E['plano_osculador']['rhs']}",
              f"   normal       (⟂ T): {E['plano_normal']['lhs']} = {E['plano_normal']['rhs']}",
              f"   rectificante (⟂ N): {E['plano_rectificante']['lhs']} = {E['plano_rectificante']['rhs']}"]
    elif "plano_normal" in E:
        s += [f"   plano normal (⟂ T): {E['plano_normal']['lhs']} = {E['plano_normal']['rhs']}"]
    V = C.verificacion
    if V.get("frenet_serret_t0"):
        s += ["", "8) Verificación de Frenet–Serret (50 dígitos):"]
        for k, e in V["frenet_serret_t0"].items():
            s.append(f"   {k:<22} error = {e:.1e}  {'✔' if e < 1e-25 else '✘'}")
        s.append("   ortonormalidad: " + ("✔ T, N, B ortonormales y T × N = B" if V.get("correcto") else "revisar"))
    s += ["", f"9) Clasificación: {C.tipo.upper()}"] + [f"   • {c}" for c in C.clasificacion]
    for a in C.advertencias:
        s.append(f"⚠ {a}")
    s.append(L)
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════════════
# 10. Ejemplos y CLI
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


def _con_sufijo(ruta, suf):
    if not suf:
        return ruta
    base, _, ext = ruta.rpartition(".")
    return f"{base}{suf}.{ext}" if base else ruta + suf


def _ejecutar(r, t0, ctes, args, suf=""):
    C = resolver(r, t0, args.param, ctes)
    print(reporte_texto(C, ascii_=args.ascii, detalle=not args.breve))
    datos = None
    if args.png or args.html or args.datos:
        datos = datos_grafico(C, rango=args.rango)
    if args.png:
        print("PNG guardado en:", graficar_png(C, _con_sufijo(args.png, suf), datos))
    if args.html:
        print("HTML guardado en:", exportar_html(C, _con_sufijo(args.html, suf), datos, offline=args.offline))
    if args.json or args.datos:
        out = a_dict(C)
        if args.datos:
            out["grafico"] = datos
        texto = json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)
        dest = args.json or args.datos
        if dest == "-":
            print(texto)
        else:
            with open(_con_sufijo(dest, suf), "w", encoding="utf-8") as fh:
                fh.write(texto)
            print("JSON guardado en:", _con_sufijo(dest, suf))


def _leer_constantes(lista):
    out = {}
    for item in lista or []:
        if "=" not in item:
            raise ValueError(f"Constante mal escrita: '{item}'. Usa el formato a=2.")
        k, v = item.split("=", 1)
        out[k.strip()] = float(sp.N(_parse(v)))
    return out


def main(argv: Sequence[str] | None = None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(
        description="Triedro de Frenet, curvatura, torsión y planos de una curva r(t) (SymPy exacto).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               '  python metodos_frenet.py -r "cos t, sin t, t" --t0 0 --html helice.html --offline\n'
               '  python metodos_frenet.py -r "t, t^2, t^3" --t0 1 --png cubica.png\n'
               '  python metodos_frenet.py -r "a cos t, a sin t, b t" --const a=2 b=1 --html ab.html\n'
               "  python metodos_frenet.py --demo 0 --html demo.html")
    ap.add_argument("-r", "--curva", help='curva, p. ej. "cos t, sin t, t" (2 o 3 componentes)')
    ap.add_argument("--t0", default="0", help="punto donde evaluar el triedro y los planos (p. ej. 0, 1, pi/4)")
    ap.add_argument("--param", help="nombre del parámetro (por defecto t)")
    ap.add_argument("--const", nargs="+", help="valores de constantes para los gráficos, p. ej. a=2 b=1")
    ap.add_argument("--rango", nargs=2, type=float, metavar=("TMIN", "TMAX"), help="rango del parámetro a graficar")
    ap.add_argument("--png", help="guardar imagen PNG")
    ap.add_argument("--html", help="guardar página web interactiva")
    ap.add_argument("--offline", action="store_true",
                    help="incrusta Plotly.js en el HTML (funciona sin internet; requiere  pip install plotly)")
    ap.add_argument("--json", help="guardar resultado en JSON ('-' = pantalla)")
    ap.add_argument("--datos", help="como --json pero con los arreglos para graficar")
    ap.add_argument("--demo", type=int, help=f"ejecutar ejemplo 1..{len(DEMOS)} (0 = todos)")
    ap.add_argument("--ascii", action="store_true", help="fórmulas sin Unicode")
    ap.add_argument("--breve", action="store_true", help="omite T, N, B generales (pueden ser largos)")
    args = ap.parse_args(argv)
    try:
        if args.demo is not None:
            ids = list(DEMOS) if args.demo == 0 else [args.demo]
            for i in ids:
                r, t0, ctes, desc = DEMOS[i]
                print(f"\n### DEMO {i}: {desc}")
                _ejecutar(r, t0, ctes, args, suf=f"_demo{i}" if len(ids) > 1 else "")
            return
        if not args.curva:
            ap.error('indica la curva con -r "x(t), y(t), z(t)" (o usa --demo).')
        _ejecutar(args.curva, args.t0, _leer_constantes(args.const), args)
    except (ValueError, RuntimeError, sp.SympifyError, SyntaxError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
