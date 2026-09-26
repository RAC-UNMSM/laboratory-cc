#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metodos_lagrange.py — Multiplicadores de Lagrange y optimización condicionada
==============================================================================
Proyecto: Frenet, Lagrange y Puntos Críticos (Grupo 06) — servidor MCP con SymPy.

Qué hace
--------
Encuentra y clasifica los extremos locales de un campo escalar f(x1, ..., xn)
sujeto a m restricciones de igualdad g_i(x1, ..., xn) = 0, usando SOLO álgebra
computacional exacta (SymPy). Los decimales aparecen únicamente como apoyo
(columna "≈") y en los datos para graficar.

Pasos del método (tal como se explican en clase):
  1. Lagrangiana:  L(x, λ) = f(x) − Σ λ_i · g_i(x)
  2. Sistema:      ∇_x L = 0   (⇔ ∇f = Σ λ_i ∇g_i)   y   g_i = 0
  3. Resolución exacta: bases de Gröbner si el sistema es polinómico,
     sympy.solve / nonlinsolve en otro caso. Se reportan TODAS las ramas.
  4. Hessiano orlado:     | 0      J_g   |
                          | J_gᵀ   H_x L |
  5. Clasificación por el signo de los últimos (n − m) menores principales
     orlados (órdenes 2m+1, ..., m+n).
  6. Verificación cruzada independiente: Hessiano de L restringido al espacio
     tangente de la restricción (autovalores de Zᵀ·H_L·Z).
  7. Detección de puntos singulares de la restricción (donde los ∇g_i son
     linealmente dependientes): allí Lagrange NO aplica y el extremo puede
     escaparse del sistema — se listan como candidatos extra.

Uso desde la terminal
---------------------
  python metodos_lagrange.py -f "x*y" -g "x^2 + y^2 = 8"
  python metodos_lagrange.py -f "x^2+y^2+z^2" -g "x+y+z=3" --png sol.png --html sol.html
  python metodos_lagrange.py -f "x+y+z" -g "x^2+y^2=2" -g "x+z=1" --json sol.json
  python metodos_lagrange.py --demo 1      (ejemplos 1..5; --demo 0 los corre todos)

Uso desde Python / MCP
----------------------
  from metodos_lagrange import resolver_lagrange
  res = resolver_lagrange("x*y", ["x^2+y^2=8"], incluir_grafico=True)
  # res es un dict 100% serializable a JSON (listo para devolver desde el MCP)

Dependencias: sympy, numpy  (matplotlib solo para --png)
"""
from __future__ import annotations

import argparse
import itertools
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

__all__ = [
    "resolver_lagrange",
    "resolver",
    "datos_grafico",
    "graficar_png",
    "exportar_html",
    "reporte_texto",
    "ProblemaLagrange",
    "PuntoCritico",
]

TOL = 1e-10
_TRANSF = standard_transformations + (implicit_multiplication, implicit_application, convert_xor)

# Nombres de clasificación (constantes para que el verificador/servidor los compare)
MAX_LOCAL = "máximo local condicionado"
MIN_LOCAL = "mínimo local condicionado"
SILLA = "punto de silla condicionado (no es extremo)"
NO_CONCLUYENTE = "no concluyente (criterio de 2º orden degenerado)"
AISLADO = "punto aislado (m = n: la restricción no deja grados de libertad)"


# ════════════════════════════════════════════════════════════════════════════
# 1. Estructuras de datos
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class PuntoCritico:
    """Una solución real del sistema de Lagrange (o un punto singular)."""
    coords: dict                      # {Symbol: expr exacta}
    lambdas: dict                     # {Symbol λ_i: expr exacta}
    valor_f: sp.Expr
    tipo: str = "lagrange"            # "lagrange" | "singular"
    hessiano_orlado: sp.Matrix | None = None
    menores: list = field(default_factory=list)   # [(orden, valor_exacto, signo)]
    clasificacion: str = ""
    verificacion_tangente: dict = field(default_factory=dict)
    global_: str = ""                 # "máximo global" / "mínimo global" entre candidatos


@dataclass
class ProblemaLagrange:
    f: sp.Expr
    restricciones: list               # [g_i] ya como expresiones "= 0"
    variables: list                   # [Symbol]
    lambdas: list                     # [Symbol]
    lagrangiana: sp.Expr
    ecuaciones: list                  # sistema ∇L = 0
    metodo: str = ""
    base_groebner: list | None = None
    puntos: list = field(default_factory=list)       # [PuntoCritico]
    singulares: list = field(default_factory=list)   # [PuntoCritico]
    familias: list = field(default_factory=list)     # soluciones con parámetros libres
    n_complejas: int = 0
    advertencias: list = field(default_factory=list)
    hessiano_orlado_general: sp.Matrix | None = None

    @property
    def n(self) -> int:
        return len(self.variables)

    @property
    def m(self) -> int:
        return len(self.restricciones)


# ════════════════════════════════════════════════════════════════════════════
# 2. Entrada: parseo y validación mínima
#    (la validación sintáctica completa vive en validacion.py)
# ════════════════════════════════════════════════════════════════════════════
def _parse(texto: str) -> sp.Expr:
    return parse_expr(texto, transformations=_TRANSF, evaluate=True)


def parsear(texto: str | sp.Basic) -> sp.Expr:
    """Convierte texto a expresión SymPy. Acepta '^' como potencia, '2x' como 2*x
    y ecuaciones 'lhs = rhs' (se devuelven como lhs − rhs)."""
    if isinstance(texto, sp.Basic):
        return sp.sympify(texto)
    t = str(texto).strip()
    if not t:
        raise ValueError("Expresión vacía.")
    for op in ("<=", ">=", "!=", "<", ">"):
        if op in t:
            raise ValueError(f"'{t}': solo se admiten restricciones de IGUALDAD (g = 0).")
    if "==" in t:
        izq, der = t.split("==", 1)
        return _parse(izq) - _parse(der)
    if "=" in t:
        izq, der = t.split("=", 1)
        return _parse(izq) - _parse(der)
    return _parse(t)


def _preparar(f, restricciones, variables):
    """Parsea todo y reemplaza los símbolos por símbolos reales (ayuda a simplificar)."""
    if isinstance(restricciones, (str, sp.Basic)):
        restricciones = [restricciones]
    f_e = parsear(f)
    g_e = [parsear(g) for g in restricciones]
    if not g_e:
        raise ValueError("Se necesita al menos una restricción g(x) = 0.")

    libres = set(f_e.free_symbols).union(*[g.free_symbols for g in g_e])
    if variables:
        if isinstance(variables, str):
            variables = variables.replace(",", " ").split()
        nombres = [str(v) for v in variables]
    else:
        nombres = sorted({s.name for s in libres})
    reales = {nm: sp.Symbol(nm, real=True) for nm in nombres}
    sust = {s: reales[s.name] for s in libres if s.name in reales}
    extra = [s.name for s in libres if s.name not in reales]
    if extra:
        raise ValueError(f"Símbolos no declarados como variables: {extra}. "
                         "Decláralos en --vars o quítalos de la expresión.")
    f_e = f_e.subs(sust)
    g_e = [g.subs(sust) for g in g_e]
    vars_ = [reales[nm] for nm in nombres]

    for i, g in enumerate(g_e, 1):
        if g.is_number:
            raise ValueError(f"La restricción {i} no depende de ninguna variable ({g} = 0).")
    if len(g_e) > len(vars_):
        raise ValueError(f"Hay {len(g_e)} restricciones y solo {len(vars_)} variables: "
                         "el sistema está sobredeterminado (m debe ser ≤ n).")
    return f_e, g_e, vars_


# ════════════════════════════════════════════════════════════════════════════
# 3. Utilidades numérico-simbólicas
# ════════════════════════════════════════════════════════════════════════════
def _complejo(v) -> complex | None:
    try:
        return complex(sp.N(v, 30))
    except (TypeError, ValueError):
        return None


def _es_real(v) -> bool:
    r = getattr(v, "is_real", None)
    if r is True:
        return True
    if r is False:
        return False
    c = _complejo(v)
    return c is not None and abs(c.imag) <= 1e-12 * (1 + abs(c.real))


def _limpiar(v):
    if isinstance(v, sp.Basic) and v.has(sp.CRootOf):
        return _algebraico(v)
    """Simplifica y, si la expresión es real pero contiene 'I' (p. ej. raíces de
    una cúbica por Cardano), intenta devolver una forma sin la unidad imaginaria."""
    v = sp.nsimplify(v, rational=False) if v.is_Float else v
    try:
        v = sp.simplify(v)
    except Exception:  # noqa: BLE001
        pass
    if v.has(sp.I) and _es_real(v):
        w = sp.simplify(sp.re(sp.expand_complex(v)))
        if not w.has(sp.I) and not w.has(sp.re):
            v = w
    return v


def _num(v) -> float | None:
    c = _complejo(v)
    if c is None or not math.isfinite(c.real):
        return None
    return float(c.real)


def _signo(v) -> int:
    """Signo exacto cuando se puede; si no, por evaluación con 30 dígitos."""
    try:
        if v.is_zero or sp.simplify(v) == 0:
            return 0
        if v.is_positive:
            return 1
        if v.is_negative:
            return -1
    except Exception:  # noqa: BLE001
        pass
    c = _complejo(v)
    if c is None:
        return 0
    if abs(c.real) < 1e-12:
        return 0
    return 1 if c.real > 0 else -1


# ════════════════════════════════════════════════════════════════════════════
# 4. Resolución del sistema de Lagrange
# ════════════════════════════════════════════════════════════════════════════
def _algebraico(e):
    """Expresa un número algebraico real como raíz exacta de su polinomio mínimo."""
    try:
        e = sp.nsimplify(e) if e.is_Float else e
        if e.is_Rational:
            return e
        X = sp.Dummy("X")
        mp = sp.minimal_polynomial(e, X, polys=True)
        if mp.degree() <= 2:
            cand = sp.solve(mp.as_expr(), X)
        else:
            cand = mp.real_roots()
        val = complex(sp.N(e, 30))
        return min(cand, key=lambda r: abs(complex(sp.N(r, 30)) - val))
    except Exception:  # noqa: BLE001
        return e


def _resolver_triangular(base, incognitas):
    """Base de Gröbner lex en 'posición normal': x_i = p_i(t) y q(t) = 0 (t = última incógnita).
    Se usan las raíces REALES exactas de q (CRootOf: números algebraicos exactos) y se sustituye
    hacia atrás. Evita que solve() se atasque con fórmulas de Cardano/Ferrari de grado ≥ 3."""
    t = incognitas[-1]
    q = [e for e in base if e.free_symbols <= {t}]
    otros = [e for e in base if not e.free_symbols <= {t}]
    if len(q) != 1 or len(otros) != len(incognitas) - 1:
        return None
    despeje = {}
    for v in incognitas[:-1]:
        cands = [e for e in otros if v in e.free_symbols and e.free_symbols <= {v, t}
                 and sp.Poly(e, v).degree() == 1]
        if not cands:
            return None
        a, b = sp.Poly(cands[0], v).all_coeffs()
        if not a.is_number:
            return None
        despeje[v] = -b / a
    sols = []
    for r in dict.fromkeys(sp.Poly(q[0], t).real_roots()):
        s = {t: _algebraico(r)}
        for v, ex in despeje.items():
            s[v] = _algebraico(sp.expand(ex.subs(t, r)))
        sols.append(s)
    return sols


def _resolver_sistema(ecs: list, incognitas: list, metodo: str):
    """Devuelve (lista_de_soluciones_dict, nombre_metodo, base_groebner|None)."""
    es_poli = all(sp.together(e).as_numer_denom()[1].is_number and
                  e.is_polynomial(*incognitas) for e in ecs)
    G = None

    if metodo in ("auto", "groebner") and es_poli:
        try:
            G = sp.groebner(ecs, *incognitas, order="lex")
            if list(G.exprs) == [1]:
                return [], "groebner (sistema inconsistente: base = {1})", list(G.exprs)
            base = list(G.exprs)
            ult = [e for e in base if e.free_symbols <= {incognitas[-1]}]
            if ult and max((sp.Poly(fa, incognitas[-1]).degree() for fa, _ in sp.factor_list(ult[0])[1]),
                           default=0) >= 3:
                tri = _resolver_triangular(base, incognitas)
                if tri is not None:
                    return tri, "groebner (orden lex) + raíces reales exactas (CRootOf)", base
            sols = sp.solve(base, incognitas, dict=True)
            return sols, "groebner (orden lex) + solve", base
        except Exception as e:  # noqa: BLE001
            if metodo == "groebner":
                raise RuntimeError(f"Falló Gröbner: {e}") from e

    if metodo in ("auto", "solve"):
        try:
            sols = sp.solve(ecs, incognitas, dict=True)
            return sols, "sympy.solve", None
        except (NotImplementedError, Exception) as e:  # noqa: BLE001
            if metodo == "solve":
                raise RuntimeError(f"Falló solve: {e}") from e

    # nonlinsolve como último recurso
    res = sp.nonlinsolve(ecs, incognitas)
    if isinstance(res, sp.ConditionSet) or not isinstance(res, sp.FiniteSet):
        raise RuntimeError("SymPy no pudo resolver el sistema en forma cerrada "
                           f"(nonlinsolve devolvió {type(res).__name__}).")
    sols = []
    for tupla in res:
        sols.append({x: v for x, v in zip(incognitas, tupla) if v != x})
    return sols, "sympy.nonlinsolve", None


def _hessiano_orlado(L, gs, vars_) -> sp.Matrix:
    m, n = len(gs), len(vars_)
    J = sp.Matrix([[sp.diff(g, v) for v in vars_] for g in gs])          # m × n
    HL = sp.hessian(L, vars_)                                             # n × n
    HB = sp.zeros(m + n, m + n)
    HB[:m, m:] = J
    HB[m:, :m] = J.T
    HB[m:, m:] = HL
    return HB


def _clasificar_orlado(HBp: sp.Matrix, m: int, n: int):
    """Criterio de los menores principales orlados.
    Se revisan los órdenes k = 2m+1, ..., m+n (son n − m menores):
      · MÍNIMO:  todos tienen signo (−1)^m
      · MÁXIMO:  el de orden k tiene signo (−1)^(k−m)  (alternan)
      · algún menor = 0  → no concluyente
      · todos ≠ 0 pero sin patrón → silla condicionada."""
    if n == m:
        return [], AISLADO
    menores = []
    for k in range(2 * m + 1, m + n + 1):
        d = HBp[:k, :k].det()
        d = _algebraico(d) if d.has(sp.CRootOf) else sp.simplify(d)
        menores.append((k, d, _signo(d)))
    signos = [s for _, _, s in menores]
    if any(s == 0 for s in signos):
        return menores, NO_CONCLUYENTE
    if all(s == (-1) ** m for s in signos):
        return menores, MIN_LOCAL
    if all(s == (-1) ** (k - m) for (k, _, s) in menores):
        return menores, MAX_LOCAL
    return menores, SILLA


def _verificar_tangente(Jp: np.ndarray, HLp: np.ndarray) -> dict:
    """Segunda prueba (independiente): restringe H_L al espacio tangente
    T = {d : J·d = 0} y mira los autovalores de Zᵀ H_L Z."""
    _, s, vh = np.linalg.svd(Jp)
    rango = int(np.sum(s > 1e-9))
    Z = vh[rango:].T
    if Z.shape[1] == 0:
        return {"autovalores": [], "clasificacion": AISLADO, "dim_tangente": 0}
    M = Z.T @ HLp @ Z
    ev = np.linalg.eigvalsh((M + M.T) / 2)
    esc = max(1.0, float(np.max(np.abs(ev))))
    if np.all(ev > 1e-9 * esc):
        c = MIN_LOCAL
    elif np.all(ev < -1e-9 * esc):
        c = MAX_LOCAL
    elif np.any(ev > 1e-9 * esc) and np.any(ev < -1e-9 * esc):
        c = SILLA
    else:
        c = NO_CONCLUYENTE
    return {"autovalores": [float(x) for x in ev], "clasificacion": c,
            "dim_tangente": int(Z.shape[1])}


def _puntos_singulares(gs, vars_, f):
    """Puntos de la restricción donde rango(J_g) < m (∇g_i dependientes).
    Se resuelve  g_i = 0  y  todos los menores m×m de J_g = 0."""
    m = len(gs)
    J = sp.Matrix([[sp.diff(g, v) for v in vars_] for g in gs])
    menores = [sp.simplify(J[:, list(c)].det())
               for c in itertools.combinations(range(len(vars_)), m)]
    menores = [e for e in menores if e != 0]
    if not menores:
        return [], True     # J idénticamente de rango < m: restricciones redundantes
    try:
        sols = sp.solve(list(gs) + menores, vars_, dict=True)
    except Exception:  # noqa: BLE001
        return [], False
    salida = []
    for s in sols:
        if len(s) < len(vars_) or not all(_es_real(v) for v in s.values()):
            continue
        coords = {v: _limpiar(s[v]) for v in vars_}
        fv = _limpiar(f.subs(coords))
        salida.append(PuntoCritico(coords=coords, lambdas={}, valor_f=fv, tipo="singular",
                                   clasificacion="singular: ∇g dependientes, Lagrange no aplica"))
    return salida, False


# ════════════════════════════════════════════════════════════════════════════
# 5. Motor principal
# ════════════════════════════════════════════════════════════════════════════
def resolver(f, restricciones, variables=None, metodo: str = "auto") -> ProblemaLagrange:
    """Resuelve el problema y devuelve un ProblemaLagrange con objetos SymPy.
    metodo ∈ {"auto", "groebner", "solve", "nonlinsolve"}."""
    f_e, gs, vars_ = _preparar(f, restricciones, variables)
    m, n = len(gs), len(vars_)
    lams = [sp.Symbol(f"lambda_{i}" if m > 1 else "lambda", real=True) for i in range(1, m + 1)]

    L = f_e - sum(l * g for l, g in zip(lams, gs))
    ecs = [sp.expand(sp.diff(L, v)) for v in vars_] + list(gs)
    P = ProblemaLagrange(f=f_e, restricciones=gs, variables=vars_, lambdas=lams,
                         lagrangiana=L, ecuaciones=ecs)
    HB = _hessiano_orlado(L, gs, vars_)
    P.hessiano_orlado_general = HB
    J = sp.Matrix([[sp.diff(g, v) for v in vars_] for g in gs])
    HL = sp.hessian(L, vars_)

    sols, P.metodo, P.base_groebner = _resolver_sistema(ecs, vars_ + lams, metodo)

    vistos = set()
    for s in sols:
        faltan_x = [v for v in vars_ if v not in s]
        if faltan_x:
            P.familias.append({str(k): str(v) for k, v in s.items()})
            continue
        if not all(_es_real(s[v]) for v in vars_):
            P.n_complejas += 1
            continue
        coords = {v: _limpiar(s[v]) for v in vars_}
        clave = tuple(round(_num(coords[v]) or 0.0, 9) for v in vars_)
        if clave in vistos:
            continue
        vistos.add(clave)
        lam_v = {l: _limpiar(s[l]) if l in s else l for l in lams}

        fv = f_e.subs(coords)
        if fv.has(sp.zoo, sp.oo, -sp.oo, sp.nan) or not _es_real(fv):
            P.advertencias.append(f"Se descartó {clave}: f no está definida/real allí.")
            continue
        pc = PuntoCritico(coords=coords, lambdas=lam_v, valor_f=_limpiar(fv))

        sust = {**coords, **lam_v}
        HBp = HB.subs(sust).applyfunc(sp.simplify)
        pc.hessiano_orlado = HBp
        if any(l not in s for l in lams):
            pc.clasificacion = NO_CONCLUYENTE + " — λ indeterminado"
            P.advertencias.append(f"En {clave} el multiplicador λ quedó libre "
                                  "(∇g se anula o es dependiente).")
        else:
            pc.menores, pc.clasificacion = _clasificar_orlado(HBp, m, n)
            try:
                Jp = np.array(J.subs(coords).evalf(), dtype=float)
                HLp = np.array(HL.subs(sust).evalf(), dtype=float)
                pc.verificacion_tangente = _verificar_tangente(Jp, HLp)
                pc.verificacion_tangente["coincide"] = (
                    pc.verificacion_tangente["clasificacion"] == pc.clasificacion)
            except (TypeError, ValueError):
                pc.verificacion_tangente = {"error": "no se pudo evaluar numéricamente"}
        P.puntos.append(pc)

    if P.n_complejas:
        P.advertencias.append(f"Se descartaron {P.n_complejas} soluciones complejas (no reales).")
    if P.familias:
        P.advertencias.append("Hay soluciones con parámetros libres (infinitos puntos críticos).")

    sing, redundante = _puntos_singulares(gs, vars_, f_e)
    if redundante:
        P.advertencias.append("Las restricciones son dependientes en todo punto (redundantes).")
    P.singulares = [s for s in sing
                    if tuple(round(_num(s.coords[v]) or 0.0, 9) for v in vars_) not in vistos]
    if P.singulares:
        P.advertencias.append("La restricción tiene puntos singulares (∇g = 0 o dependientes): "
                              "Lagrange no los detecta y deben compararse aparte.")

    # Comparación global entre candidatos (válida si el conjunto factible es compacto)
    cand = [p for p in P.puntos + P.singulares if _num(p.valor_f) is not None]
    if len(cand) >= 1:
        vals = [_num(p.valor_f) for p in cand]
        vmax, vmin = max(vals), min(vals)
        for p, v in zip(cand, vals):
            if abs(v - vmax) < 1e-9 and abs(v - vmin) < 1e-9:
                p.global_ = "único valor candidato"
            elif abs(v - vmax) < 1e-9:
                p.global_ = "máximo global (entre candidatos)"
            elif abs(v - vmin) < 1e-9:
                p.global_ = "mínimo global (entre candidatos)"
    periodicas = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
    if any(e.has(*periodicas) for e in [f_e] + list(gs)):
        P.advertencias.append("Hay funciones trigonométricas (periódicas): SymPy entrega solo las "
                              "soluciones de la rama principal; las demás se obtienen sumando "
                              "múltiplos del período (p. ej. + 2kπ).")
    if not P.puntos and not P.singulares and not P.familias:
        P.advertencias.append("No se hallaron puntos críticos reales.")
    return P


# ════════════════════════════════════════════════════════════════════════════
# 6. Serialización a JSON (formato para el servidor MCP)
# ════════════════════════════════════════════════════════════════════════════
def _sust_latex(expr, coords) -> str:
    """LaTeX de expr con los valores sustituidos SIN evaluar: f(2, -1) = 2 · (−1)^2 ..."""
    rep = {}
    for i, (v, val) in enumerate(coords.items()):
        t = sp.latex(val)
        simple = (val.is_Integer and val >= 0) or val.is_Symbol
        # el sufijo "{}" (invisible en LaTeX) hace únicos los símbolos: 2·2 no se colapsa en 2²
        rep[v] = sp.Symbol("{}" * (i + 1) + (t if simple else r"\left(" + t + r"\right)"))
    try:
        return sp.latex(expr.xreplace(rep), mul_symbol="dot")
    except Exception:  # noqa: BLE001
        return sp.latex(expr)


def _regla_tex(p: PuntoCritico, m: int, n: int) -> str:
    if n == m:
        return "Con $m = n$ la restricción no deja grados de libertad: el punto es aislado."
    ks = [k for k, _, _ in p.menores]
    signo = "+" if m % 2 == 0 else "-"
    t = (f"Regla: con $m = {m}$ se revisan los menores de orden ${ks[0]}$ a ${ks[-1]}$. "
         f"**Mínimo** si todos tienen el signo de $(-1)^{{{m}}}$, es decir ${signo}$; "
         f"**máximo** si $\\Delta_k$ tiene el signo de $(-1)^{{k-{m}}}$ (alternan). Aquí: ")
    t += ", ".join(f"$\\Delta_{{{k}}} {'> 0' if sg > 0 else '< 0' if sg < 0 else '= 0'}$" for k, _, sg in p.menores)
    return t + "."


def _pc_a_dict(p: PuntoCritico, P) -> dict:
    vars_ = P.variables
    todos = {**p.coords, **{k: v for k, v in p.lambdas.items() if v != k}}
    d = {
        "tipo": p.tipo,
        "coordenadas": {str(v): str(p.coords[v]) for v in vars_},
        "coordenadas_latex": {str(v): sp.latex(p.coords[v]) for v in vars_},
        "coordenadas_num": {str(v): _num(p.coords[v]) for v in vars_},
        "lambdas": {str(k): str(v) for k, v in p.lambdas.items()},
        "lambdas_num": {str(k): _num(v) for k, v in p.lambdas.items()},
        "lambdas_latex": {sp.latex(k): sp.latex(v) for k, v in p.lambdas.items()},
        "valor_f": str(p.valor_f),
        "valor_f_latex": sp.latex(p.valor_f),
        "valor_f_num": _num(p.valor_f),
        "clasificacion": p.clasificacion,
        "comparacion_global": p.global_,
        "sustitucion_latex": ",\\quad ".join(f"{sp.latex(k)} = {sp.latex(v)}" for k, v in todos.items()),
        "f_evaluada_latex": (f"f({', '.join(sp.latex(p.coords[v]) for v in vars_)}) = "
                             f"{_sust_latex(P.f, p.coords)} = {sp.latex(p.valor_f)}"),
    }
    if p.hessiano_orlado is not None:
        d["hessiano_orlado"] = [[str(x) for x in fila] for fila in p.hessiano_orlado.tolist()]
        d["hessiano_orlado_latex"] = sp.latex(p.hessiano_orlado)
        d["menores_orlados"] = [{"orden": k, "valor": str(v), "valor_latex": sp.latex(v),
                                 "submatriz_latex": sp.latex(p.hessiano_orlado[:k, :k], mat_str="vmatrix",
                                                             mat_delim=""),
                                 "valor_num": _num(v), "signo": s}
                                for k, v, s in p.menores]
        d["regla_tex"] = _regla_tex(p, P.m, P.n)
    if p.verificacion_tangente:
        d["verificacion_tangente"] = p.verificacion_tangente
    return d


def _criterio_tex(m: int, n: int) -> str:
    if n == m:
        return "Con $m = n$ no hay grados de libertad: cada solución es un punto aislado del conjunto factible."
    return (f"**Criterio.** Con $n = {n}$ variables y $m = {m}$ restricciones se revisan los últimos "
            f"$n - m = {n - m}$ menores principales orlados $\\Delta_k$, de orden $k = {2 * m + 1}, \\dots, {m + n}$. "
            f"**Mínimo local** si todos tienen el signo de $(-1)^{{m}}$; **máximo local** si $\\Delta_k$ tiene el signo "
            f"de $(-1)^{{k-m}}$ (alternan); si algún $\\Delta_k = 0$ el criterio no concluye; en otro caso es una silla condicionada.")


def a_dict(P: ProblemaLagrange) -> dict:
    return {
        "entrada": {
            "f": str(P.f), "f_latex": sp.latex(P.f),
            "restricciones": [f"{g} = 0" for g in P.restricciones],
            "restricciones_latex": [sp.latex(g) + " = 0" for g in P.restricciones],
            "variables": [str(v) for v in P.variables],
            "n": P.n, "m": P.m,
        },
        "variables_latex": [sp.latex(v) for v in P.variables],
        "lambdas_latex": [sp.latex(l) for l in P.lambdas],
        "lagrangiana": {"expr": str(P.lagrangiana), "latex": sp.latex(P.lagrangiana)},
        "derivadas": [{"lhs": r"\frac{\partial \mathcal{L}}{\partial " + sp.latex(v) + "}",
                       "rhs": sp.latex(sp.diff(P.lagrangiana, v))} for v in P.variables + P.lambdas],
        "base_groebner_latex": [sp.latex(g) for g in P.base_groebner] if P.base_groebner else None,
        "criterio_tex": _criterio_tex(P.m, P.n),
        "sistema": [{"expr": f"{e} = 0", "latex": sp.latex(e) + " = 0"} for e in P.ecuaciones],
        "hessiano_orlado_general_latex": sp.latex(P.hessiano_orlado_general),
        "metodo_resolucion": P.metodo,
        "base_groebner": [str(g) for g in P.base_groebner] if P.base_groebner else None,
        "puntos_criticos": [_pc_a_dict(p, P) for p in P.puntos],
        "puntos_singulares": [_pc_a_dict(p, P) for p in P.singulares],
        "familias_de_soluciones": P.familias,
        "soluciones_complejas_descartadas": P.n_complejas,
        "advertencias": P.advertencias,
        "nota_global": ("La comparación global solo es válida si el conjunto factible "
                        "{g = 0} es cerrado y acotado (Teorema de Weierstrass)."),
    }


def resolver_lagrange(f, restricciones, variables=None, metodo: str = "auto",
                      incluir_grafico: bool = False, rango=None) -> dict:
    """PUNTO DE ENTRADA PARA EL MCP. Devuelve un dict serializable a JSON."""
    P = resolver(f, restricciones, variables, metodo)
    out = a_dict(P)
    if incluir_grafico:
        out["grafico"] = datos_grafico(P, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 7. Datos numéricos para gráficos (JSON → Plotly / D3 / Chart.js)
# ════════════════════════════════════════════════════════════════════════════
def _eval(fn, args, shape) -> np.ndarray:
    with np.errstate(all="ignore"):
        try:
            r = np.asarray(fn(*args), dtype=complex)
        except Exception:  # noqa: BLE001
            return np.full(shape, np.nan)
    r = np.broadcast_to(r, shape)
    out = np.where(np.abs(r.imag) < 1e-9, r.real, np.nan)
    out[~np.isfinite(out)] = np.nan
    return out.astype(float)


def _lista(a: np.ndarray, dec: int = 5):
    a = np.round(np.asarray(a, dtype=float), dec)
    return [[None if not math.isfinite(x) else float(x) for x in fila] for fila in a] \
        if a.ndim == 2 else [None if not math.isfinite(x) else float(x) for x in a]


def _rango_auto(P: ProblemaLagrange, rango):
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


def datos_grafico(P: ProblemaLagrange, rango=None, resolucion: int = 121) -> dict:
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
    caja = _rango_auto(P, rango)
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
# 8. Imagen PNG (matplotlib)
# ════════════════════════════════════════════════════════════════════════════
_COLOR = {MAX_LOCAL: "#b0502c", MIN_LOCAL: "#3f6e7d", SILLA: "#7a5873"}
_TERRA = ["#2c2420", "#4c2c21", "#7a3a24", "#ab4f2c", "#cf8660", "#e7bf9e", "#f7ece0"]


def _cmap_terra():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("terra", _TERRA)


def _s(e) -> str:
    """Texto legible para títulos: x**2 → x^2."""
    return str(e).replace("**", "^")


def _color_punto(p):
    if p["tipo"] == "singular":
        return "#c38d35"
    return _COLOR.get(p["clasificacion"], "#8c8279")


def graficar_png(P: ProblemaLagrange, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    D = datos or datos_grafico(P)
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
            (px, py), col = p["coords"], _color_punto(p)
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
            ax3.scatter(*p["coords"], p["f"], s=70, color=_color_punto(p),
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
            ax3.scatter(*p["coords"], s=160, color=_color_punto(p), edgecolor="white",
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
               [("máximo local", _COLOR[MAX_LOCAL]), ("mínimo local", _COLOR[MIN_LOCAL]),
                ("silla", _COLOR[SILLA]), ("no concluyente", "#8c8279"),
                ("singular (∇g=0)", "#c38d35")]]
    fig.legend(handles=leyenda, loc="lower center", ncol=5, fontsize=9, frameon=False)
    fig.suptitle(titulo, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(ruta, dpi=dpi)
    plt.close(fig)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# 9. HTML interactivo (Plotly.js + KaTeX, un solo archivo)
# ════════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════════
# Página web (común a metodos_lagrange.py y metodos_hessiana.py)
#   Pestañas: Resumen · Procedimiento (LaTeX) · Gráfico 3D dinámico · 2D · JSON
#   Paleta sobria terracota; Plotly.js + KaTeX desde CDN (requiere internet).
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
    <p><code>pip install plotly</code><br><code>python ${NOMBRE_JSON.startsWith("lagrange") ? "metodos_lagrange.py" : "metodos_hessiana.py"} --demo 1 --html pagina.html --offline</code></p></div>`;
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


_JS_LAGRANGE = r"""/* ═════════════ Módulo: Multiplicadores de Lagrange ═════════════ */
const E = R.entrada, V = E.variables, VT = R.variables_latex, LT = R.lambdas_latex;
const CORTO = {"máximo local condicionado":"máximo local", "mínimo local condicionado":"mínimo local",
               "punto de silla condicionado (no es extremo)":"silla condicionada"};
const COLCL = {"máximo local condicionado":COLOR.max, "mínimo local condicionado":COLOR.min,
               "punto de silla condicionado (no es extremo)":COLOR.silla};
const colorDe = p => p.tipo === "singular" ? COLOR.sing : (COLCL[p.clasificacion] || COLOR.ind);
const corto = p => p.tipo === "singular" ? "punto singular" : (CORTO[p.clasificacion] || "no concluyente");
const TODOS = R.puntos_criticos.map((p, i) => Object.assign({id:"P" + (i + 1)}, p))
  .concat(R.puntos_singulares.map((p, i) => Object.assign({id:"S" + (i + 1)}, p)));
const ptTex = p => "\\left(" + V.map(v => p.coordenadas_latex[v]).join(",\\ ") + "\\right)";
const idTex = id => id.replace(/(\d+)/, "_{$1}");
const VARS = VT.join(",\\,");
const hov = p => `<b>${p.id}</b> ${p.etiqueta}<br>f = ${fmt(p.f, 6)}<br>${corto(p)}`;

$id("enunciado").innerHTML = tex("\\operatorname{optimizar}\\; f(" + VARS + ") = " + E.f_latex +
  "\\qquad \\text{sujeto a}\\qquad " + E.restricciones_latex.join(",\\quad "));
$id("meta").innerHTML = `<span>${E.n} variables</span><span>${E.m} restricción(es)</span><span>${esc(R.metodo_resolucion)}</span><span>${TODOS.length} candidato(s)</span>`;

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const cnt = c => R.puntos_criticos.filter(p => p.clasificacion === c).length;
  const nmax = cnt("máximo local condicionado"), nmin = cnt("mínimo local condicionado");
  const K = [[TODOS.length, "candidatos analizados", COLOR.ac], [nmax, "máximos locales", COLOR.max],
             [nmin, "mínimos locales", COLOR.min], [R.puntos_criticos.length - nmax - nmin, "sillas / no concluyentes", COLOR.silla],
             [R.puntos_singulares.length, "puntos singulares", COLOR.sing]];
  let h = `<div class="kpis">${K.map(([n, t, c]) => `<div class="kpi" style="--c:${c}"><b>${n}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="card"><h2>Puntos críticos</h2><p class="sub">Soluciones reales de ∇𝓛 = 0 y puntos singulares de la restricción, con su clasificación exacta.</p><div class="pts">`;
  TODOS.forEach(p => {
    h += `<div class="pt" style="--c:${colorDe(p)}"><div class="cab"><div><b>${p.id}</b>&nbsp; ${tex(ptTex(p))}</div><span class="chip">${corto(p)}</span></div><table class="kv">`;
    const lam = Object.entries(p.lambdas_latex || {}).map(([k, v]) => tex(k + " = " + v)).join(", ");
    if (lam) h += `<tr><td>multiplicador</td><td>${lam}</td></tr>`;
    h += `<tr><td>valor de f</td><td>${tex(p.valor_f_latex)} <span class="nota">≈ ${fmt(p.valor_f_num, 6)}</span></td></tr>`;
    if ((p.menores_orlados || []).length) h += `<tr><td>menores orlados</td><td>${p.menores_orlados.map(m => tex("\\Delta_{" + m.orden + "} = " + m.valor_latex)).join(", ")}</td></tr>`;
    const vt = p.verificacion_tangente;
    if (vt && vt.coincide !== undefined) h += `<tr><td>verificación</td><td>${vt.coincide ? "✔ coincide (espacio tangente)" : "✘ difiere"}</td></tr>`;
    if (p.comparacion_global) h += `<tr><td>global</td><td><b>${esc(p.comparacion_global)}</b></td></tr>`;
    h += `</table></div>`;
  });
  if (!TODOS.length) h += `<p>No se hallaron puntos críticos reales.</p>`;
  h += `</div></div>`;
  const conv = TODOS.filter(p => p.valor_f_num !== null);
  if (conv.length) {
    const vs = conv.map(p => p.valor_f_num), lo = Math.min(...vs), rg = (Math.max(...vs) - lo) || 1;
    h += `<div class="card"><h2>Comparación de valores de f</h2><p class="sub">${esc(R.nota_global)}</p><div class="barras">` +
      conv.slice().sort((a, b) => b.valor_f_num - a.valor_f_num).map(p => `<div class="barra" style="--c:${colorDe(p)}">
      <span><b>${p.id}</b> · ${corto(p)}</span><div class="t"><i style="width:${6 + 94 * (p.valor_f_num - lo) / rg}%"></i></div>
      <span>f = ${fmt(p.valor_f_num, 6)}</span></div>`).join("") + `</div></div>`;
  }
  if (R.advertencias.length) h += `<div class="card"><h2>Advertencias</h2>${R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("")}</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto que hizo SymPy; los decimales solo aparecen como apoyo.</p></div>`, k = 0;
  const paso = (t, cuerpo) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${cuerpo}</div></div>`;
  const grad = E.m > 1 ? "\\sum_{i=1}^{" + E.m + "} \\lambda_i \\nabla g_i" : "\\lambda\\, \\nabla g";
  paso("Planteamiento del problema",
    eq("\\begin{aligned} &\\text{optimizar} && f(" + VARS + ") = " + E.f_latex + "\\\\ &\\text{sujeto a} && " +
       E.restricciones_latex.join("\\\\ & && ") + "\\end{aligned}") +
    `<div class="idea">${mt("**Idea geométrica.** En un extremo condicionado la curva (o superficie) de nivel de $f$ es tangente a la restricción, así que los gradientes son paralelos: $\\nabla f = " + grad + "$.")}</div>`);
  paso("Función de Lagrange", `<p>${mt("Se introduce un multiplicador por cada restricción:")}</p>` +
    eq("\\mathcal{L}(" + VARS + ",\\," + LT.join(",") + ") = f - " + (E.m > 1 ? "\\sum_{i=1}^{" + E.m + "} \\lambda_i\\, g_i" : "\\lambda\\, g")) +
    eq("\\mathcal{L} = " + R.lagrangiana.latex));
  paso("Condiciones de primer orden: $\\nabla \\mathcal{L} = 0$",
    `<p>${mt("Se deriva $\\mathcal{L}$ respecto a cada variable y a cada multiplicador, y se iguala a cero:")}</p>` +
    eq("\\begin{aligned}" + R.derivadas.map(d => d.lhs + " &= " + d.rhs + " = 0").join("\\\\[10pt]") + "\\end{aligned}") +
    `<p class="nota">${mt("Las derivadas respecto a los multiplicadores devuelven las restricciones $g_i = 0$.")}</p>`);
  let r = `<p>${mt("Método: **" + esc(R.metodo_resolucion) + "**.")}</p>`;
  if (R.base_groebner_latex) r += `<p>${mt("Una **base de Gröbner** en orden lexicográfico convierte el sistema en uno *triangular*: la última ecuación tiene una sola incógnita; se resuelve y se sustituye hacia arriba (es la eliminación gaussiana generalizada a polinomios). Tiene exactamente las mismas soluciones que el sistema original:")}</p>` +
    eq("\\begin{cases}" + R.base_groebner_latex.map(g => g + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  if (R.puntos_criticos.length) {
    const cab = VT.concat(LT).concat(["f"]);
    const filas = TODOS.filter(p => p.tipo !== "singular").map(p => idTex(p.id) + " & " +
      V.map(v => p.coordenadas_latex[v]).concat(LT.map(l => (p.lambdas_latex || {})[l] || "\\cdot")).concat([p.valor_f_latex]).join(" & "));
    r += `<p>Soluciones <b>reales</b> del sistema:</p>` + eq("\\begin{array}{c|" + "c".repeat(VT.length + LT.length) + "|c} & " +
      cab.join(" & ") + " \\\\ \\hline " + filas.join(" \\\\[3pt] ") + "\\end{array}");
  } else r += `<p>El sistema no tiene soluciones reales.</p>`;
  if (R.soluciones_complejas_descartadas) r += `<p class="nota">Se descartaron ${R.soluciones_complejas_descartadas} soluciones complejas (no pertenecen a ℝⁿ).</p>`;
  paso("Resolución exacta del sistema", r);
  paso("Hessiano orlado",
    `<p>${mt("Para la condición de segundo orden se usa la matriz de segundas derivadas de $\\mathcal{L}$ **orlada** (enmarcada) con el jacobiano de las restricciones $J_g$:")}</p>` +
    eq("H_{\\text{orl}} = \\begin{pmatrix} 0_{m\\times m} & J_g \\\\ J_g^{\\,T} & \\nabla^2_{x}\\mathcal{L} \\end{pmatrix} = " + R.hessiano_orlado_general_latex) +
    `<div class="idea">${mt(R.criterio_tex)}</div>`);
  let c = "";
  TODOS.filter(p => p.tipo !== "singular").forEach((p, i) => {
    const col = colorDe(p);
    c += `<details class="sp" ${i === 0 ? "open" : ""}><summary><b>${p.id}</b> ${tex(ptTex(p))} <span class="chip" style="--c:${col}">${corto(p)}</span></summary><div class="in">`;
    c += `<p><b>a)</b> Se sustituye la solución del sistema:</p>` + eq(p.sustitucion_latex) + eq(p.f_evaluada_latex);
    if (p.hessiano_orlado_latex) c += `<p><b>b)</b> Hessiano orlado evaluado en el punto:</p>` + eq("H_{\\text{orl}}(" + idTex(p.id) + ") = " + p.hessiano_orlado_latex);
    (p.menores_orlados || []).forEach((m, j) => {
      if (j === 0) c += `<p><b>c)</b> Menores principales orlados que se revisan:</p>`;
      c += eq("\\Delta_{" + m.orden + "} = " + m.submatriz_latex + " = " + m.valor_latex + (m.signo > 0 ? " > 0" : m.signo < 0 ? " < 0" : " = 0"));
    });
    c += `<p>${mt(p.regla_tex)}</p>`;
    c += `<div class="concl" style="--c:${col}">${mt("⇒ $" + idTex(p.id) + " = " + ptTex(p) + "$ es **" + esc(p.clasificacion) + "**, con $f(" + idTex(p.id) + ") = " + p.valor_f_latex + "$.")}</div>`;
    const vt = p.verificacion_tangente;
    if (vt && vt.autovalores && vt.autovalores.length) c += `<p class="nota">${mt("Verificación independiente: los autovalores de $Z^{T}\\,\\nabla^2_x\\mathcal{L}\\,Z$ (Hessiano restringido al espacio tangente $J_g\\,d = 0$) son $" + vt.autovalores.map(x => fmt(x, 4)).join(",\\ ") + "$ → " + (vt.coincide ? "coincide ✔" : "difiere ✘"))}</p>`;
    c += `</div></details>`;
  });
  paso("Clasificación de cada punto crítico", c || "<p>No hay puntos que clasificar.</p>");
  if (R.puntos_singulares.length) paso("Puntos singulares de la restricción",
    `<p>${mt("Donde $\\nabla g = 0$ (o los $\\nabla g_i$ son linealmente dependientes) el teorema de Lagrange **no aplica**: puede haber un extremo que no cumpla $\\nabla f = \\lambda\\nabla g$. Se resuelven $g = 0$ junto con los menores del jacobiano:")}</p>` +
    TODOS.filter(p => p.tipo === "singular").map(p => eq(idTex(p.id) + " = " + ptTex(p) + ",\\qquad f(" + idTex(p.id) + ") = " + p.valor_f_latex)).join(""));
  const conv = TODOS.filter(p => p.valor_f_num !== null).sort((a, b) => b.valor_f_num - a.valor_f_num);
  if (conv.length) paso("Comparación global de candidatos",
    `<p>${mt("Si el conjunto factible $\\{g = 0\\}$ es cerrado y acotado, por el **teorema de Weierstrass** $f$ alcanza su máximo y su mínimo, y deben estar entre los candidatos:")}</p>
    <table class="kv" style="max-width:640px">${conv.map(p => `<tr><td><b>${p.id}</b> ${tex(ptTex(p))}</td><td>${tex("f = " + p.valor_f_latex)}</td><td>${esc(p.comparacion_global || corto(p))}</td></tr>`).join("")}</table>`);
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
const colorPunto = p => colorDe(p);
INIT.g3d = () => {
  const P = $id("tab-g3d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin representación geométrica</h2><p class="sub">Con más de 3 variables no hay gráfico; revisa el procedimiento y el JSON.</p></div>`; return; }
  if (D.tipo === "2d") g3dPlano(P); else g3dEspacio(P);
};

function g3dPlano(P) {
  const REC = [], pX = [], pY = [];
  let s = 0;
  D.curvas_restriccion.forEach(c => {
    let prev = null;
    c.x.forEach((x, i) => {
      const y = c.y[i], z = c.z[i];
      if (x === null || y === null || z === null) { prev = null; pX.push(null); pY.push(null); return; }
      if (prev) s += Math.hypot(x - prev[0], y - prev[1]);
      prev = [x, y]; REC.push({x, y, z, s}); pX.push(s); pY.push(z);
    });
    pX.push(null); pY.push(null);
  });
  const zs = D.z.flat().filter(v => v !== null).sort((a, b) => a - b), qz = t => zs[Math.floor(t * (zs.length - 1))];
  const [x0, x1] = D.rango[0], [y0, y1] = D.rango[1];
  const fr = REC.length ? REC.map(r => r.z) : zs;
  const zBot = zs[0], zTop = zs[zs.length - 1], rM = Math.max(...fr), rm = Math.min(...fr);
  const zCap = Math.min(zTop, Math.max(qz(0.55), rM + 0.25 * (rM - rm) + 0.12 * (zTop - zBot)));
  const zLow = Math.max(zBot, Math.min(qz(0.45), rm - 0.25 * (rM - rm) - 0.12 * (zTop - zBot)));
  const zmin = zLow, zmax = zCap;
  const Zc = D.z.map(f => f.map(v => v === null || v > zCap || v < zLow ? null : v));
  /* recorte limpio: fuera de [zLow, zCap] la superficie se aplana en el borde y se vuelve transparente */
  const Sb = D.z_rango || D.z, scV = Sb.flat().filter((v, k) => v !== null && Zc[Math.floor(k / D.x.length)][k % D.x.length] !== null);
  const scMin = Math.min(...scV), scMax = Math.max(...scV), SEN = scMin - 0.03 * ((scMax - scMin) || 1);
  const Zs = D.z.map(f => f.map(v => v === null ? null : Math.min(zCap, Math.max(zLow, v))));
  const Sc = Sb.map((f, i) => f.map((v, j) => Zc[i][j] === null ? SEN : v));
  const OPAC = [[0, 0], [0.02, 0], [0.03, 1], [1, 1]];
  let cmin = Math.min(...fr), cmax = Math.max(...fr); const pad = 0.12 * ((cmax - cmin) || 1); cmin -= pad; cmax += pad;
  const cDe = v => cmin + (cmax - cmin) * v / 400, vDe = c => Math.round(400 * (c - cmin) / (cmax - cmin));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(200);
  P.innerHTML = `<div class="card"><h2>Superficie z = f(${V.join(", ")}) y la restricción</h2>
    <p class="sub">La curva terracota es la restricción g = 0 “levantada” sobre la superficie: sus puntos más altos y más bajos son los extremos condicionados. Recórrela con el punto blanco o mueve el plano de nivel z = c: en un extremo, el plano <b>toca</b> la curva sin cruzarla (tangencia).</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Recorrer la restricción</label><button class="btn pri" id="bRec">▶ Reproducir</button>
        <input type="range" id="sRec" min="0" max="${Math.max(REC.length - 1, 0)}" value="0"><div class="lectura" id="lRec"></div></div>
      <div class="bloque"><label class="t">Perfil de f a lo largo de g = 0</label><div id="perfil" class="plot bajo"></div></div>
      <div class="bloque"><label class="t">Plano de nivel z = c</label><label class="chk"><input type="checkbox" id="cPlano" checked> mostrar plano</label>
        <input type="range" id="sC" min="0" max="400" value="${vDe(c0)}"><div class="lectura" id="lC"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cMuro" checked> muro vertical sobre g = 0</label>
        <label class="chk"><input type="checkbox" id="cSup" checked> superficie z = f</label>
        <label class="chk"><input type="checkbox" id="cRec" checked> recortar la superficie a ${fmt(zLow, 3)} ≤ z ≤ ${fmt(zCap, 3)}</label></div>
    </div></div></div>`;
  const EPS = 0.012 * (zmax - zmin), up = a => a.map(v => v === null ? null : v + EPS);
  const tr = [{type:"surface", x:D.x, y:D.y, z:Zs, surfacecolor:Sc, cmin:SEN, cmax:scMax, opacityscale:OPAC,
    colorscale:TERRA3D, opacity:1, showscale:false, name:"z = f", hoverinfo:"x+y+z",
    lighting:{ambient:0.78, diffuse:0.5, specular:0.06, roughness:0.95, fresnel:0.1}}];
  const iMuros = [];
  D.curvas_restriccion.forEach(c => { const n = c.x.length; iMuros.push(tr.length);
    tr.push({type:"surface", x:[c.x, c.x], y:[c.y, c.y], z:[Array(n).fill(zmin), Array(n).fill(zmax)],
      surfacecolor:[Array(n).fill(0), Array(n).fill(1)], colorscale:[[0, "#d9b99b"], [1, "#d9b99b"]], cmin:0, cmax:1,
      showscale:false, opacity:0.3, hoverinfo:"skip", name:"muro g = 0"}); });
  D.curvas_restriccion.forEach((c, i) => tr.push({type:"scatter3d", mode:"lines", x:c.x, y:c.y, z:up(c.z),
    line:{color:COLOR.ac, width:9}, name:"f sobre g = 0", showlegend:i === 0, hoverinfo:"x+y+z"}));
  tr.push({type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]),
    z:up(D.puntos.map(p => p.f)), text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
    marker:{size:9, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"});
  const iPlano = tr.length;
  tr.push({type:"surface", x:[x0, x1], y:[y0, y1], z:[[c0, c0], [c0, c0]], colorscale:[[0, "#f0d3bd"], [1, "#f0d3bd"]],
    showscale:false, opacity:0.5, hoverinfo:"skip", name:"plano z = c", showlegend:true});
  const iMov = tr.length, r0 = REC[0] || {x:0, y:0, z:0, s:0};
  tr.push({type:"scatter3d", mode:"markers", x:[r0.x], y:[r0.y], z:[r0.z], marker:{size:9, color:"#ffffff", line:{color:COLOR.ac2, width:4}},
    name:"punto móvil", hoverinfo:"skip", visible:REC.length > 0});
  tr.push({type:"scatter3d", mode:"lines", x:[r0.x, r0.x], y:[r0.y, r0.y], z:[zmin, r0.z], line:{color:COLOR.ac2, width:4, dash:"dash"},
    showlegend:false, hoverinfo:"skip", visible:REC.length > 0});
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:Object.assign(ejes3("f"), {range:[zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)]}),
           aspectmode:"manual", aspectratio:{x:1, y:1, z:0.75}, camera:{eye:{x:1.25, y:-1.3, z:1.2}}}}), CFG);
  $id("cRec").onchange = e => { Plotly.restyle(g3, e.target.checked ? {z:[Zs], surfacecolor:[Sc], cmin:[SEN], cmax:[scMax], opacityscale:[OPAC]} : {z:[D.z], surfacecolor:[Sb], cmin:[null], cmax:[null], opacityscale:[null]}, [0]);
    Plotly.relayout(g3, {"scene.zaxis.autorange": !e.target.checked, "scene.zaxis.range": e.target.checked ? [zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)] : undefined}); };
  const perf = reg("g3d", $id("perfil"));
  const crit = D.puntos.map(p => { let b = -1, bd = Infinity;
    REC.forEach((r, i) => { const d = Math.hypot(r.x - p.coords[0], r.y - p.coords[1]); if (d < bd) { bd = d; b = i; } });
    return bd < 0.03 * (x1 - x0) ? {p, s:REC[b].s} : null; }).filter(Boolean);
  const lineaC = c => ({type:"line", xref:"paper", x0:0, x1:1, y0:c, y1:c, line:{color:COLOR.ac2, width:1.5, dash:"dot"}});
  Plotly.newPlot(perf, [{x:pX, y:pY, mode:"lines", line:{color:COLOR.ac, width:2.5}, hoverinfo:"x+y"},
    {x:crit.map(c => c.s), y:crit.map(c => c.p.f), mode:"markers+text", text:crit.map(c => c.p.id), textposition:"top center",
     textfont:{size:11, color:COLOR.tx}, marker:{size:9, color:crit.map(c => colorPunto(c.p)), line:{color:"#fff", width:1.5}}, hoverinfo:"skip"},
    {x:[r0.s], y:[r0.z], mode:"markers", marker:{size:11, color:"#fff", line:{color:COLOR.ac2, width:3}}, hoverinfo:"skip"}],
    lay({margin:{l:42, r:8, t:8, b:34}, showlegend:false, shapes:[lineaC(c0)],
         xaxis:{title:{text:"longitud de arco s", font:{size:11}}, gridcolor:COLOR.bd}, yaxis:{title:{text:"f", font:{size:11}}, gridcolor:COLOR.bd}}),
    {displayModeBar:false, responsive:true});
  const sTot = REC.length ? REC[REC.length - 1].s : 1;
  const mover = i => { const r = REC[i]; if (!r) return;
    Plotly.restyle(g3, {x:[[r.x], [r.x, r.x]], y:[[r.y], [r.y, r.y]], z:[[r.z + 2 * EPS], [zmin, r.z]]}, [iMov, iMov + 1]);
    Plotly.restyle(perf, {x:[[r.s]], y:[[r.z]]}, [2]);
    const cerca = crit.find(c => Math.abs(c.s - r.s) < 0.012 * sTot);
    $id("lRec").innerHTML = `${V[0]} = ${fmt(r.x, 4)}<br>${V[1]} = ${fmt(r.y, 4)}<br>f = ${fmt(r.z, 6)}` +
      (cerca ? `<br><b style="color:${colorPunto(cerca.p)}">≈ ${cerca.p.id}: ${corto(cerca.p)}</b>` : ""); };
  if (REC.length) { reproductor($id("bRec"), $id("sRec"), mover, Math.max(1, Math.round(REC.length / 360))); mover(0); }
  else $id("lRec").textContent = "La restricción no tiene un trazo continuo en este rango.";
  const plano = v => { const c = cDe(v);
    Plotly.restyle(g3, {z:[[[c, c], [c, c]]]}, [iPlano]); Plotly.relayout(perf, {shapes:[lineaC(c)]});
    const toca = crit.filter(q => Math.abs(q.p.f - c) < 0.004 * (cmax - cmin));
    $id("lC").innerHTML = `c = ${fmt(c, 6)}` + (toca.length ? `<br><b>tangente en ${toca.map(q => q.p.id).join(", ")}</b>` : ""); };
  $id("sC").oninput = e => plano(+e.target.value);
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i];
    $id("sC").value = vDe(p.f); plano(vDe(p.f)); });
  plano(vDe(c0));
  $id("cPlano").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iPlano]);
  $id("cMuro").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, iMuros);
  $id("cSup").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

function g3dEspacio(P) {
  const fr = D.f_en_restriccion.filter(v => v !== null);
  let cmin = Math.min(...fr), cmax = Math.max(...fr); const pad = 0.06 * ((cmax - cmin) || 1); cmin -= pad; cmax += pad;
  const cDe = v => cmin + (cmax - cmin) * v / 300, vDe = c => Math.round(300 * (c - cmin) / (cmax - cmin));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(150);
  P.innerHTML = `<div class="card"><h2>${esc(D.descripcion)} y superficies de nivel de f</h2>
    <p class="sub">Los puntos forman la restricción, coloreados según el valor de f. La superficie translúcida es el nivel f = c: al barrer c, el primer y el último contacto con la restricción (contacto <b>tangente</b>) dan el mínimo y el máximo condicionados.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Superficie de nivel f = c</label><button class="btn pri" id="bIso">▶ Barrer c</button>
        <input type="range" id="sIso" min="0" max="300" value="${vDe(c0)}"><div class="lectura" id="lIso"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cIso" checked> superficie f = c</label>
        <label class="chk"><input type="checkbox" id="cNube" checked> restricción (nube de puntos)</label></div>
    </div></div></div>`;
  const [ex, ey, ez] = D.vol.ejes, X = [], Y = [], Z = [];
  ex.forEach(a => ey.forEach(b => ez.forEach(c => { X.push(a); Y.push(b); Z.push(c); })));
  const val = D.vol.valor.map(v => v === null ? NaN : v);
  const tr = [{type:"scatter3d", mode:"markers", x:D.x, y:D.y, z:D.z, name:"restricción", hoverinfo:"skip",
      marker:{size:2.6, color:D.f_en_restriccion, colorscale:TERRA, opacity:0.8, colorbar:{title:{text:"f"}, len:0.6, thickness:14}}},
    {type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.coords[2]),
      text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
      marker:{size:8, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"},
    {type:"isosurface", x:X, y:Y, z:Z, value:val, isomin:c0, isomax:c0, surface:{count:1}, showscale:false, opacity:0.32,
      colorscale:[[0, COLOR.min], [1, COLOR.min]], caps:{x:{show:false}, y:{show:false}, z:{show:false}}, name:"f = c", hoverinfo:"skip", showlegend:true}];
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:ejes3(V[2]), aspectmode:"cube", camera:{eye:{x:1.6, y:-1.5, z:1.0}}}}), CFG);
  const iso = v => { const c = cDe(v); Plotly.restyle(g3, {isomin:[c], isomax:[c]}, [2]);
    const tol = 0.01 * (cmax - cmin), n = fr.filter(q => Math.abs(q - c) < tol).length;
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.004 * (cmax - cmin));
    $id("lIso").innerHTML = `c = ${fmt(c, 6)}<br>` + (n ? `corta la restricción (~${n} puntos)` : "no toca la restricción") +
      (t.length ? `<br><b>contacto tangente en ${t.map(p => p.id).join(", ")}</b>` : ""); };
  reproductor($id("bIso"), $id("sIso"), iso, 2); iso(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sIso").value = vDe(p.f); iso(vDe(p.f)); });
  $id("cIso").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [2]);
  $id("cNube").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin gráfico</h2><p class="sub">Más de 3 variables.</p></div>`; return; }
  if (D.tipo === "2d") {
    P.innerHTML = `<div class="card"><h2>Curvas de nivel, restricción y gradientes</h2>
      <p class="sub">Colores por cuantiles de f. En cada punto crítico ∇f (ocre) y ∇g (petróleo) son <b>paralelos</b>: esa es la condición ∇f = λ∇g. La línea discontinua es la curva de nivel de f que pasa por el punto: es tangente a la restricción.</p>
      <div class="leyenda"><span><i style="background:${COLOR.max}"></i>máximo</span><span><i style="background:${COLOR.min}"></i>mínimo</span><span><i style="background:${COLOR.silla}"></i>silla</span><span><i style="background:${COLOR.ind}"></i>no concluyente</span><span><i style="background:${COLOR.sing}"></i>singular</span></div>
      <div id="g2" class="plot"></div></div>`;
    const cb = D.ticks_color ? {title:{text:"f"}, tickvals:D.ticks_color.vals, ticktext:D.ticks_color.text, thickness:14} : {title:{text:"f"}};
    const tr = [{type:"contour", x:D.x, y:D.y, z:D.z_rango || D.z, text:D.z, colorscale:TERRA, ncontours:34, colorbar:cb,
      contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, name:"f",
      hovertemplate:"x = %{x:.3f}<br>y = %{y:.3f}<br>f = %{text}<extra></extra>"}];
    [...new Set(D.niveles_criticos)].forEach((lv, i) => tr.push({type:"contour", x:D.x, y:D.y, z:D.z, showscale:false, hoverinfo:"skip",
      contours:{coloring:"none", start:lv, end:lv, size:1}, line:{color:"#fff", width:1.8, dash:"dash"}, name:"nivel f = f(P)", showlegend:i === 0}));
    D.curvas_restriccion.forEach((c, i) => tr.push({type:"scatter", mode:c.dispersa ? "markers" : "lines", x:c.x, y:c.y,
      line:{color:OSCURO ? "#f3e6d8" : "#2b2420", width:3.5}, marker:{size:2, color:"#2b2420"}, name:"g = 0", showlegend:i === 0}));
    const L = (D.rango[0][1] - D.rango[0][0]) * 0.11;
    const flecha = (px, py, v, col, nm, w) => { const n = Math.hypot(v[0], v[1]); if (!n) return;
      tr.push({type:"scatter", mode:"lines+markers", x:[px, px + L * v[0] / n], y:[py, py + L * v[1] / n], name:nm, showlegend:false,
        line:{color:col, width:w}, marker:{size:[0, 11], symbol:"arrow", angleref:"previous", color:col}, hoverinfo:"name"}); };
    D.puntos.forEach(p => { const [px, py] = p.coords;
      p.grad_g.forEach(g => flecha(px, py, g, COLOR.min, "∇g", 6)); flecha(px, py, p.grad_f, "#e0a64a", "∇f", 3);
      tr.push({type:"scatter", mode:"markers+text", x:[px], y:[py], text:[p.id], textposition:"top right", textfont:{color:"#fff", size:13},
        marker:{size:15, color:colorPunto(p), line:{color:"#fff", width:2}}, hovertext:[hov(p)], hoverinfo:"text", showlegend:false}); });
    Plotly.newPlot(reg("g2d", $id("g2")), tr, lay({xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain", gridcolor:COLOR.bd},
      yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain", gridcolor:COLOR.bd}}), CFG);
  } else {
    P.innerHTML = `<div class="card"><h2>Proyecciones de la restricción</h2><p class="sub">La restricción vista desde los tres planos coordenados, coloreada por f.</p><div class="grid2" id="proys"></div></div>`;
    [[0, 1], [0, 2], [1, 2]].forEach(([a, b]) => { const d = document.createElement("div"); d.className = "plot medio"; $id("proys").appendChild(d);
      const ej = [D.x, D.y, D.z];
      Plotly.newPlot(reg("g2d", d), [{type:"scattergl", mode:"markers", x:ej[a], y:ej[b], marker:{size:4, color:D.f_en_restriccion, colorscale:TERRA, opacity:0.75}, hoverinfo:"skip", name:"g = 0"},
        {type:"scatter", mode:"markers+text", x:D.puntos.map(p => p.coords[a]), y:D.puntos.map(p => p.coords[b]), text:D.puntos.map(p => p.id), textposition:"top right",
         marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos"}],
        lay({showlegend:false, xaxis:{title:{text:V[a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:V[b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG); });
  }
};
"""


def exportar_html(P: ProblemaLagrange, ruta: str, datos: dict | None = None, offline: bool = False) -> str:
    """Página web autocontenida: resumen, procedimiento en LaTeX, 3D dinámico, 2D y JSON."""
    D = datos or datos_grafico(P)
    html = _pagina(a_dict(P), D, titulo="Multiplicadores de Lagrange",
                   eyebrow="Optimización condicionada · Cálculo exacto con SymPy",
                   funcion="resolver_lagrange()", nombre_json="lagrange_resultado.json", js_modulo=_JS_LAGRANGE,
                   pie="Generado por metodos_lagrange.py · Grupo 06 · Frenet, Lagrange y Puntos Críticos", offline=offline)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# 10. Reporte legible en terminal
# ════════════════════════════════════════════════════════════════════════════
def _pp(e, ascii_=False) -> str:
    return sp.pretty(e, use_unicode=not ascii_)


def reporte_texto(P: ProblemaLagrange, ascii_: bool = False, detalle: bool = True) -> str:
    linea = "=" * 78
    s = [linea, " MULTIPLICADORES DE LAGRANGE", linea]
    s.append(f"f({', '.join(map(str, P.variables))}) = {P.f}")
    for i, g in enumerate(P.restricciones, 1):
        s.append(f"g{i} = {g} = 0")
    s.append(f"n = {P.n} variables, m = {P.m} restricciones  →  se revisan n − m = {P.n - P.m} menores orlados")
    s += ["", "1) Lagrangiana  L = f − Σ λ·g :", _pp(sp.Eq(sp.Symbol("L"), P.lagrangiana), ascii_)]
    s += ["", "2) Sistema ∇L = 0 :"]
    for e in P.ecuaciones:
        s.append("   " + _pp(sp.Eq(e, 0), ascii_).replace("\n", "\n   "))
    s += ["", f"3) Método de resolución: {P.metodo}"]
    if detalle and P.base_groebner:
        s.append("   Base de Gröbner (lex):")
        for g in P.base_groebner:
            s.append(f"     {g}")
    s += ["", "4) Hessiano orlado general:", _pp(P.hessiano_orlado_general, ascii_)]

    s += ["", f"5) Puntos críticos reales: {len(P.puntos)}", "-" * 78]
    for i, p in enumerate(P.puntos, 1):
        c = ", ".join(f"{v} = {p.coords[v]}" for v in P.variables)
        cn = ", ".join(f"{_num(p.coords[v]):.6g}" for v in P.variables)
        s.append(f"[P{i}]  {c}      (≈ {cn})")
        if p.lambdas:
            s.append("      " + ", ".join(f"{k} = {v}" for k, v in p.lambdas.items()))
        s.append(f"      f = {p.valor_f}   (≈ {_num(p.valor_f):.6g})")
        if detalle and p.hessiano_orlado is not None:
            s.append("      H_orlado en el punto:")
            s.append("      " + _pp(p.hessiano_orlado, ascii_).replace("\n", "\n      "))
        for k, d, sg in p.menores:
            s.append(f"      Δ{k} = {d}   (signo {'+' if sg > 0 else '−' if sg < 0 else '0'})")
        s.append(f"      ⇒ {p.clasificacion.upper()}")
        vt = p.verificacion_tangente
        if vt.get("autovalores") is not None and "coincide" in vt:
            ev = ", ".join(f"{x:.4g}" for x in vt["autovalores"])
            s.append(f"      Verificación (Hessiano de L en el espacio tangente): autovalores [{ev}] "
                     f"→ {'coincide ✔' if vt['coincide'] else 'DIFIERE ✘ (' + vt['clasificacion'] + ')'}")
        if p.global_:
            s.append(f"      Comparación global: {p.global_}")
        s.append("")
    if P.singulares:
        s += ["6) Puntos singulares de la restricción (candidatos que Lagrange NO ve):", "-" * 78]
        for p in P.singulares:
            c = ", ".join(f"{v} = {p.coords[v]}" for v in P.variables)
            s.append(f"[S]  {c}   f = {p.valor_f}   {p.global_}")
        s.append("")
    if P.familias:
        s.append("Familias de soluciones (parámetros libres):")
        for fam in P.familias:
            s.append(f"   {fam}")
    for a in P.advertencias:
        s.append(f"⚠ {a}")
    s.append("Nota: la comparación global solo vale si {g = 0} es cerrado y acotado (Weierstrass).")
    s.append(linea)
    return "\n".join(s)


# ════════════════════════════════════════════════════════════════════════════
# 11. Ejemplos y línea de comandos
# ════════════════════════════════════════════════════════════════════════════
DEMOS = {
    1: ("x*y", ["x^2 + y^2 = 8"], None,
        "Clásico 2D: 2 máximos y 2 mínimos sobre una circunferencia."),
    2: ("x^2 + y^2 + z^2", ["x + y + z = 3"], None,
        "3 variables, 1 restricción: distancia mínima del origen a un plano."),
    3: ("x + y + z", ["x^2 + y^2 = 2", "x + z = 1"], None,
        "3 variables, 2 restricciones: extremos sobre una elipse en el espacio."),
    4: ("x^3 + y", ["y = 0"], None,
        "Caso degenerado: el Hessiano orlado se anula → no concluyente (es una inflexión)."),
    5: ("x", ["y^2 = x^3"], None,
        "Restricción con cúspide: el mínimo está en un punto singular (∇g = 0) que Lagrange no detecta."),
}


def _ejecutar_cli(f, gs, vars_, args, sufijo=""):
    P = resolver(f, gs, vars_, metodo=args.metodo)
    print(reporte_texto(P, ascii_=args.ascii, detalle=not args.breve))
    datos = None
    if args.png or args.html or args.json or args.datos:
        if P.n <= 3:
            datos = datos_grafico(P, rango=args.rango)
    if args.png:
        if datos is None:
            print("(Sin PNG: con más de 3 variables no hay gráfico geométrico.)")
        else:
            print("PNG guardado en:", graficar_png(P, _con_sufijo(args.png, sufijo), datos))
    if args.html:
        print("HTML guardado en:", exportar_html(P, _con_sufijo(args.html, sufijo),
                                                  datos or datos_grafico(P), offline=args.offline))
    if args.json or args.datos:
        out = a_dict(P)
        if args.datos and datos is not None:
            out["grafico"] = datos
        texto = json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False)
        destino = args.json or args.datos
        if destino == "-":
            print(texto)
        else:
            ruta = _con_sufijo(destino, sufijo)
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(texto)
            print("JSON guardado en:", ruta)


def _con_sufijo(ruta: str, sufijo: str) -> str:
    if not sufijo:
        return ruta
    base, _, ext = ruta.rpartition(".")
    return f"{base}{sufijo}.{ext}" if base else f"{ruta}{sufijo}"


def main(argv: Sequence[str] | None = None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(
        description="Extremos condicionados por multiplicadores de Lagrange (SymPy exacto).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               '  python metodos_lagrange.py -f "x*y" -g "x^2+y^2=8" --png out.png --html out.html\n'
               '  python metodos_lagrange.py -f "x+y+z" -g "x^2+y^2=2" -g "x+z=1" --json -\n'
               "  python metodos_lagrange.py --demo 0 --png demo.png")
    ap.add_argument("-f", "--funcion", help="función objetivo, p. ej. \"x^2 + 3xy\"")
    ap.add_argument("-g", "--restriccion", action="append", default=[],
                    help="restricción (repetible), p. ej. \"x^2+y^2=1\" o \"x+y-2\"")
    ap.add_argument("-v", "--vars", nargs="+", help="orden de las variables (por defecto alfabético)")
    ap.add_argument("--metodo", default="auto", choices=["auto", "groebner", "solve", "nonlinsolve"])
    ap.add_argument("--png", help="guardar imagen PNG")
    ap.add_argument("--html", help="guardar HTML interactivo (Plotly.js)")
    ap.add_argument("--json", help="guardar resultado simbólico en JSON ('-' = pantalla)")
    ap.add_argument("--datos", help="como --json pero incluyendo los arreglos para graficar")
    ap.add_argument("--rango", nargs=2, type=float, action="append", metavar=("MIN", "MAX"),
                    help="rango por eje (repetir una vez por variable)")
    ap.add_argument("--demo", type=int, help="ejecutar ejemplo 1..5 (0 = todos)")
    ap.add_argument("--ascii", action="store_true", help="fórmulas sin Unicode")
    ap.add_argument("--breve", action="store_true", help="omite Hessianos por punto y base de Gröbner")
    ap.add_argument("--offline", action="store_true",
                    help="incrusta Plotly.js en el HTML (funciona sin internet; requiere  pip install plotly)")
    args = ap.parse_args(argv)

    if args.demo is not None:
        ids = list(DEMOS) if args.demo == 0 else [args.demo]
        for i in ids:
            f, gs, vs, desc = DEMOS[i]
            print(f"\n### DEMO {i}: {desc}")
            _ejecutar_cli(f, gs, vs, args, sufijo=f"_demo{i}" if len(ids) > 1 else "")
        return
    if not args.funcion or not args.restriccion:
        ap.error("indica -f FUNCION y al menos un -g RESTRICCION (o usa --demo).")
    try:
        _ejecutar_cli(args.funcion, args.restriccion, args.vars, args)
    except (ValueError, RuntimeError, sp.SympifyError, SyntaxError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
