#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
metodos_hessiana.py — Puntos críticos y optimización libre (matriz Hessiana)
==============================================================================
Proyecto: Frenet, Lagrange y Puntos Críticos (Grupo 06) — servidor MCP con SymPy.

Qué hace
--------
Encuentra TODOS los puntos críticos de un campo escalar f(x1, ..., xn) en un
dominio abierto y los clasifica con álgebra computacional exacta (SymPy).

Pasos del método
  1. Gradiente simbólico  ∇f = (∂f/∂x, ∂f/∂y, ...).
  2. Sistema ∇f = 0 resuelto de forma exacta: se eliminan primero los factores
     que nunca se anulan (p. ej. e^(...)), luego bases de Gröbner si el sistema
     es polinómico, o sympy.solve / nonlinsolve en otro caso. Cada solución se
     VERIFICA sustituyéndola en el gradiente original.
  3. Matriz Hessiana H(x, y) y discriminante D = f_xx·f_yy − (f_xy)².
  4. Criterio de la segunda derivada:
        D > 0, f_xx > 0 → mínimo local      D > 0, f_xx < 0 → máximo local
        D < 0           → punto de silla     D = 0           → caso dudoso
     (n ≥ 3: criterio de Sylvester con los menores principales + autovalores).

Lo que va MÁS ALLÁ del criterio clásico
  5. Casos dudosos (D = 0) resueltos con rigor, en este orden:
       a) Forma de Taylor de orden superior: se busca el primer término no nulo
          q_k(h) del desarrollo f(p+h) − f(p). Si k es impar → no es extremo;
          si q_k es definida positiva/negativa → mínimo/máximo estricto;
          si es indefinida → silla. (Prueba exacta de definición en 2D.)
       b) Certificado exacto de signo: SymPy intenta demostrar f − f(p) ≥ 0
          (o ≤ 0) para TODO x → extremo GLOBAL demostrado.
       c) Curvas de prueba exactas: rectas y parábolas γ(t) por el punto; se
          calcula el primer término de f(γ(t)) − f(p). Si una curva sube y otra
          baja → silla demostrada (resuelve p. ej. el contraejemplo de Peano).
       d) Sondeo numérico de alta precisión (mpmath, 40 dígitos) con testigos
          re-verificados en aritmética exacta. Se etiqueta como "numérico".
  6. Puntos críticos NO diferenciables (donde ∇f no existe, p. ej. el vértice
     de un cono √(x²+y²)).
  7. Familias de puntos críticos (infinitos puntos, p. ej. f = (x − y)²).
  8. Análisis global: para polinomios se estudia la forma de mayor grado
     (coercividad) y se decide con demostración si existen mín./máx. globales.

Salidas: reporte en terminal, JSON (MCP), PNG (matplotlib) y HTML interactivo
(Plotly.js + KaTeX) con curvas de nivel, líneas de flujo del gradiente (cuencas
de atracción), superficie 3D, aproximación cuadrática de Taylor y mapa de D(x,y).

Uso desde la terminal
---------------------
  python metodos_hessiana.py -f "x^4 + y^4 - 4xy + 1" --png sol.png --html sol.html
  python metodos_hessiana.py -f "x^3 + y^2 + z^2 + 12xy + 2z"
  python metodos_hessiana.py --demo 0          (ejemplos 1..8)

Uso desde Python / MCP
----------------------
  from metodos_hessiana import resolver_hessiana
  res = resolver_hessiana("x^3 + y^3 - 3xy", incluir_grafico=True)   # dict JSON

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
    "resolver_hessiana", "resolver", "a_dict", "datos_grafico", "graficar_png",
    "exportar_html", "reporte_texto", "ProblemaHessiana", "PuntoCritico",
]

_TRANSF = standard_transformations + (implicit_multiplication, implicit_application, convert_xor)

# Clasificaciones (constantes para que verificador.py / server.py las comparen)
MIN_LOCAL = "mínimo local"
MAX_LOCAL = "máximo local"
SILLA = "punto de silla"
DUDOSO = "caso dudoso"
INDETERMINADO = "indeterminado"
DEMOSTRADO = "demostrado"
NUMERICO = "evidencia numérica"


# ════════════════════════════════════════════════════════════════════════════
# 1. Estructuras de datos
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class PuntoCritico:
    coords: dict                         # {Symbol: valor exacto}
    valor_f: sp.Expr
    tipo: str = "estacionario"           # "estacionario" | "no diferenciable" | "familia"
    hessiana: sp.Matrix | None = None
    menores: list = field(default_factory=list)          # [(k, Δk exacto, signo)]
    D: sp.Expr | None = None
    fxx: sp.Expr | None = None
    autovalores: list = field(default_factory=list)      # [{exacto, num, mult}]
    autovectores: list = field(default_factory=list)     # [[...], ...] numéricos
    clasif_segundo_orden: str = ""       # lo que dice SOLO el criterio D / Sylvester
    clasificacion: str = ""              # conclusión final
    certeza: str = DEMOSTRADO
    criterio: str = ""
    verif_autovalores: dict = field(default_factory=dict)
    orden_superior: dict = field(default_factory=dict)   # análisis del caso dudoso
    certificado: str = ""                # "f - f(p) >= 0 para todo x" ...
    global_: str = ""
    verificado: bool = False
    familia: dict | None = None


@dataclass
class ProblemaHessiana:
    f: sp.Expr
    variables: list
    gradiente: list = field(default_factory=list)
    ecuaciones: list = field(default_factory=list)       # núcleos usados al resolver
    factores_descartados: list = field(default_factory=list)
    metodo: str = ""
    base_groebner: list | None = None
    hessiana_general: sp.Matrix | None = None
    D_general: sp.Expr | None = None
    puntos: list = field(default_factory=list)
    no_diferenciables: list = field(default_factory=list)
    familias: list = field(default_factory=list)
    n_complejas: int = 0
    advertencias: list = field(default_factory=list)
    analisis_global: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.variables)

    @property
    def todos(self) -> list:
        return self.puntos + self.no_diferenciables + [fa["representante"] for fa in self.familias
                                                       if fa.get("representante") is not None]


# ════════════════════════════════════════════════════════════════════════════
# 2. Entrada
# ════════════════════════════════════════════════════════════════════════════
def _parse(texto: str) -> sp.Expr:
    return parse_expr(texto, transformations=_TRANSF, evaluate=True)


def parsear(texto) -> sp.Expr:
    """Texto → SymPy. Acepta '^', '2x', 'e' no (usar exp()), y 'f = ...' / 'z = ...'."""
    if isinstance(texto, sp.Basic):
        return sp.sympify(texto)
    t = str(texto).strip()
    if not t:
        raise ValueError("Expresión vacía.")
    if "=" in t:                      # 'f(x,y) = ...'  → se toma el lado derecho
        t = t.split("=", 1)[1]
    return _parse(t)


def _preparar(f, variables):
    f_e = parsear(f)
    libres = f_e.free_symbols
    if variables:
        if isinstance(variables, str):
            variables = variables.replace(",", " ").split()
        nombres = [str(v) for v in variables]
    else:
        nombres = sorted(s.name for s in libres)
    if not nombres:
        raise ValueError("La función no depende de ninguna variable.")
    reales = {nm: sp.Symbol(nm, real=True) for nm in nombres}
    extra = [s.name for s in libres if s.name not in reales]
    if extra:
        raise ValueError(f"Símbolos no declarados como variables: {extra}.")
    f_e = f_e.subs({s: reales[s.name] for s in libres})
    return f_e, [reales[nm] for nm in nombres]


# ════════════════════════════════════════════════════════════════════════════
# 3. Utilidades exacto/numérico
# ════════════════════════════════════════════════════════════════════════════
def _complejo(v):
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


def _finito(v) -> bool:
    return not (v.has(sp.zoo, sp.oo, -sp.oo, sp.nan)) and _es_real(v)


def _limpiar(v):
    if isinstance(v, sp.Basic) and v.has(sp.CRootOf):
        return _algebraico(v)
    try:
        v = sp.simplify(v)
    except Exception:  # noqa: BLE001
        pass
    if v.has(sp.I) and _es_real(v):
        w = sp.simplify(sp.re(sp.expand_complex(v)))
        if not w.has(sp.I) and not w.has(sp.re):
            v = w
    return v


def _num(v):
    c = _complejo(v)
    if c is None or not math.isfinite(c.real):
        return None
    return float(c.real)


def _signo(v) -> int:
    try:
        v = sp.sympify(v)
        if v.is_zero:
            return 0
        if v.is_positive:
            return 1
        if v.is_negative:
            return -1
        if sp.simplify(v) == 0:
            return 0
    except Exception:  # noqa: BLE001
        pass
    c = _complejo(v)
    if c is None or abs(c.real) < 1e-25:
        return 0
    return 1 if c.real > 0 else -1


def _clave(coords, vars_):
    return tuple(round(_num(coords[v]) or 0.0, 9) for v in vars_)


# ════════════════════════════════════════════════════════════════════════════
# 4. Resolución de ∇f = 0
# ════════════════════════════════════════════════════════════════════════════
def _nucleo(e):
    """Devuelve (núcleo, denominador, factores_descartados).
    El núcleo tiene los MISMOS ceros reales que e, pero sin factores que nunca se
    anulan (e^u, constantes, x²+1, ...) y sin multiplicidades: facilita Gröbner."""
    e = sp.sympify(e)
    # sign(u) = 0 ⇔ u = 0 : se reemplaza para que el sistema quede algebraico
    e = e.replace(lambda a: isinstance(a, sp.sign), lambda a: a.args[0])
    e = sp.together(e)
    num, den = sp.fraction(e)
    num = sp.factor(num)
    utiles, fuera = [], []
    for fa in sp.Mul.make_args(num):
        base = fa.base if (fa.is_Pow and fa.exp.is_positive) else fa
        if base.is_number:
            if base != 0:
                continue
            utiles.append(base)
            continue
        if isinstance(base, sp.exp) or base.is_positive or base.is_negative:
            fuera.append(base)
            continue
        utiles.append(base)
    nucleo = sp.Mul(*utiles) if utiles else sp.Integer(1)
    return sp.expand(nucleo), den, fuera


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


def _resolver_sistema(ecs, incognitas, metodo):
    es_poli = all(e.is_polynomial(*incognitas) for e in ecs)
    if metodo in ("auto", "groebner") and es_poli:
        try:
            G = sp.groebner(ecs, *incognitas, order="lex")
            base = list(G.exprs)
            if base == [1]:
                return [], "groebner (sistema inconsistente: base = {1})", base
            ult = [e for e in base if e.free_symbols <= {incognitas[-1]}]
            if ult and max((sp.Poly(fa, incognitas[-1]).degree() for fa, _ in sp.factor_list(ult[0])[1]),
                           default=0) >= 3:
                tri = _resolver_triangular(base, incognitas)
                if tri is not None:
                    return tri, "groebner (orden lex) + raíces reales exactas (CRootOf)", base
            return sp.solve(base, incognitas, dict=True), "groebner (orden lex) + solve", base
        except Exception as e:  # noqa: BLE001
            if metodo == "groebner":
                raise RuntimeError(f"Falló Gröbner: {e}") from e
    if metodo in ("auto", "solve"):
        try:
            return sp.solve(ecs, incognitas, dict=True), "sympy.solve", None
        except Exception as e:  # noqa: BLE001
            if metodo == "solve":
                raise RuntimeError(f"Falló solve: {e}") from e
    res = sp.nonlinsolve(ecs, incognitas)
    if not isinstance(res, sp.FiniteSet):
        raise RuntimeError("SymPy no pudo resolver ∇f = 0 en forma cerrada.")
    return ([{x: v for x, v in zip(incognitas, tup) if v != x} for tup in res],
            "sympy.nonlinsolve", None)


# ════════════════════════════════════════════════════════════════════════════
# 5. Criterio de segundo orden
# ════════════════════════════════════════════════════════════════════════════
def _segundo_orden(Hp: sp.Matrix, n: int):
    """Devuelve (menores, clasificación, criterio)."""
    menores = []
    for k in range(1, n + 1):
        d = Hp[:k, :k].det()
        d = _algebraico(d) if d.has(sp.CRootOf) else sp.simplify(d)
        menores.append((k, d, _signo(d)))
    s = [m[2] for m in menores]
    if n == 1:
        c = MIN_LOCAL if s[0] > 0 else MAX_LOCAL if s[0] < 0 else DUDOSO
        return menores, c, "segunda derivada f''"
    if n == 2:
        D, fxx = menores[1][2], s[0]
        if D > 0:
            return menores, (MIN_LOCAL if fxx > 0 else MAX_LOCAL), "discriminante D y signo de f_xx"
        if D < 0:
            return menores, SILLA, "discriminante D < 0"
        return menores, DUDOSO, "discriminante D = 0"
    if s[-1] == 0:
        return menores, DUDOSO, "det H = 0 (Sylvester no concluye)"
    if all(x > 0 for x in s):
        return menores, MIN_LOCAL, "Sylvester: todos los Δk > 0"
    if all((-1) ** k * x > 0 for k, x in zip(range(1, n + 1), s)):
        return menores, MAX_LOCAL, "Sylvester: (−1)^k·Δk > 0"
    return menores, SILLA, "Sylvester: det H ≠ 0 sin patrón definido → indefinida"


def _autovalores(Hp: sp.Matrix, n: int):
    exactos = []
    if n <= 3 and not Hp.has(sp.CRootOf):     # con raíces CRootOf los autovalores exactos son carísimos
        try:
            for val, mult in Hp.eigenvals().items():
                v = _limpiar(val)
                ok = not v.has(sp.I) and len(str(v)) <= 70
                exactos.append({"exacto": v if ok else None, "num": _num(v), "mult": int(mult)})
        except Exception:  # noqa: BLE001
            exactos = []
    M = np.array(Hp.evalf(), dtype=float)
    vals, vecs = np.linalg.eigh((M + M.T) / 2)
    if not exactos:
        exactos = [{"exacto": None, "num": float(x), "mult": 1} for x in vals]
    exactos.sort(key=lambda d: d["num"] if d["num"] is not None else 0)
    esc = max(1.0, float(np.max(np.abs(vals))))
    tol = 1e-9 * esc
    if np.all(vals > tol):
        c = MIN_LOCAL
    elif np.all(vals < -tol):
        c = MAX_LOCAL
    elif np.any(vals > tol) and np.any(vals < -tol):
        c = SILLA
    else:
        c = DUDOSO
    return exactos, [list(map(float, vecs[:, i])) for i in range(n)], [float(x) for x in vals], c


# ════════════════════════════════════════════════════════════════════════════
# 6. Análisis de orden superior (casos dudosos)
# ════════════════════════════════════════════════════════════════════════════
def _simbolos_h(vars_):
    return [sp.Symbol(f"h_{v.name}", real=True) for v in vars_]


def _formas_taylor(f, vars_, coords, orden_max=8):
    """Formas homogéneas q_k(h) del desarrollo f(p + h) − f(p) = Σ q_k(h)."""
    s = sp.Dummy("s")
    hs = _simbolos_h(vars_)
    E = f.subs({v: coords[v] + s * h for v, h in zip(vars_, hs)}, simultaneous=True)
    if f.is_polynomial(*vars_):
        E = sp.expand(E)
    else:
        E = sp.expand(sp.series(E, s, 0, orden_max + 1).removeO())
    return {k: sp.expand(sp.simplify(E.coeff(s, k))) for k in range(1, orden_max + 1)}, hs


def _definicion_forma(q, hs):
    """Clasifica la forma homogénea q(h). Devuelve (tipo, exacto:bool, testigos)."""
    n = len(hs)
    if q == 0:
        return "nula", True, {}
    if n == 1:
        c = sp.Poly(q, hs[0]).LC()
        k = sp.Poly(q, hs[0]).degree()
        sg = _signo(c)
        if k % 2:
            return "indefinida", True, {"sube": [1], "baja": [-1] if sg > 0 else [1]}
        return ("definida positiva" if sg > 0 else "definida negativa"), True, {}
    if n == 2:
        t = sp.Dummy("t")
        a = sp.expand(q.subs({hs[0]: 1, hs[1]: t}))
        b = q.subs({hs[0]: 0, hs[1]: 1})
        exacto = True
        try:
            P = sp.Poly(a, t)
            try:
                raices = sorted({float(r) for r in sp.real_roots(P)})
                hay_cero = len(raices) > 0
            except Exception:  # noqa: BLE001
                exacto = False
                cs = [float(sp.N(c)) for c in P.all_coeffs()]
                raices = sorted({float(r.real) for r in np.roots(cs) if abs(r.imag) < 1e-9}) if len(cs) > 1 else []
                hay_cero = len(raices) > 0
        except sp.PolynomialError:
            return _definicion_numerica(q, hs)
        muestras = []
        if raices:
            muestras = [raices[0] - 1] + [(r1 + r2) / 2 for r1, r2 in zip(raices, raices[1:])] + [raices[-1] + 1]
        else:
            muestras = [0.0]
        signos, testigos = set(), {"sube": None, "baja": None}
        for tm in muestras:
            tr = sp.nsimplify(round(tm, 6))
            sg = _signo(a.subs(t, tr))
            if sg:
                signos.add(sg)
                testigos["sube" if sg > 0 else "baja"] = [1, float(tr)]
        sb = _signo(b)
        if sb:
            signos.add(sb)
            testigos["sube" if sb > 0 else "baja"] = [0, 1]
        else:
            hay_cero = True
        testigos = {k: v for k, v in testigos.items() if v}
        if {1, -1} <= signos:
            return "indefinida", exacto, testigos
        if signos == {1}:
            return ("semidefinida positiva" if hay_cero else "definida positiva"), exacto, testigos
        if signos == {-1}:
            return ("semidefinida negativa" if hay_cero else "definida negativa"), exacto, testigos
        return "nula", exacto, testigos
    return _definicion_numerica(q, hs)


def _definicion_numerica(q, hs):
    n = len(hs)
    rng = np.random.default_rng(1)
    U = rng.normal(size=(4000, n))
    U = np.vstack([U, np.eye(n), -np.eye(n)])
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    fq = sp.lambdify(hs, q, "numpy")
    v = np.broadcast_to(np.asarray(fq(*U.T), dtype=float), (len(U),))
    esc = float(np.max(np.abs(v))) or 1.0
    pos, neg = np.any(v > 1e-9 * esc), np.any(v < -1e-9 * esc)
    cero = float(np.min(np.abs(v))) < 1e-6 * esc
    test = {}
    if pos:
        test["sube"] = list(map(float, U[int(np.argmax(v))]))
    if neg:
        test["baja"] = list(map(float, U[int(np.argmin(v))]))
    if pos and neg:
        return "indefinida", False, test
    if pos:
        return ("semidefinida positiva" if cero else "definida positiva"), False, test
    if neg:
        return ("semidefinida negativa" if cero else "definida negativa"), False, test
    return "nula", False, test


def _certificado(f, fp, vars_):
    """Intenta DEMOSTRAR que f(x) − f(p) ≥ 0 (o ≤ 0) para todo x real."""
    E = sp.simplify(f - fp)
    for forma in (E, sp.factor(E), sp.expand(E)):
        try:
            if forma.is_nonnegative:
                return "≥", forma
            if forma.is_nonpositive:
                return "≤", forma
        except Exception:  # noqa: BLE001
            pass
    return "", None


def _curvas_prueba(f, fp, vars_, coords, orden=12):
    """Curvas exactas γ(t) por p: rectas y parábolas en cada par de coordenadas.
    Devuelve lista de {curva, termino, comportamiento: 'sube'|'baja'|'cambia'|'constante'}."""
    t = sp.Symbol("t", real=True)
    n = len(vars_)
    cs_rect = [0, 1, -1, 2, -2, sp.Rational(1, 2), -sp.Rational(1, 2)]
    cs_parab = [sp.Rational(1, 2), -sp.Rational(1, 2), 1, -1, sp.Rational(3, 2), -sp.Rational(3, 2),
                2, -2, 3, -3]
    pares = list(itertools.permutations(range(n), 2)) if n > 1 else [(0, 0)]
    curvas = []
    for i, j in pares:
        for c in cs_rect:
            curvas.append((i, j, c, 1, "recta"))
        if n > 1:
            for c in cs_parab:
                curvas.append((i, j, c, 2, "parábola"))
    resultados, vistos = [], set()
    es_poli = f.is_polynomial(*vars_)
    for i, j, c, pot, nombre in curvas:
        desp = [sp.Integer(0)] * n
        desp[i] += t
        if n > 1 and c != 0:
            desp[j] += c * t ** pot
        clave = tuple(str(d) for d in desp)
        if clave in vistos:
            continue
        vistos.add(clave)
        sust = {v: coords[v] + d for v, d in zip(vars_, desp)}
        phi = f.subs(sust, simultaneous=True) - fp
        try:
            if es_poli:
                phi = sp.expand(phi)
            else:
                phi = sp.expand(sp.series(phi, t, 0, orden + 1).removeO())
        except Exception:  # noqa: BLE001
            continue
        termino, comp = None, "constante"
        for k in range(1, orden + 1):
            ck = sp.simplify(phi.coeff(t, k))
            if ck != 0 and _signo(ck) != 0:
                termino = ck * t ** k
                comp = "cambia" if k % 2 else ("sube" if _signo(ck) > 0 else "baja")
                break
        gamma = "(" + ", ".join(str(sp.simplify(coords[v] + d)) for v, d in zip(vars_, desp)) + ")"
        resultados.append({"curva": f"{nombre}: γ(t) = {gamma}", "termino": termino,
                           "comportamiento": comp, "_gamma": [coords[v] + d for v, d in zip(vars_, desp)],
                           "_t": t})
    return resultados


def _sondeo_numerico(f, fp, vars_, coords):
    """Evalúa f(p + r·u) − f(p) con 40 dígitos en esferas de radio r decreciente.
    Los testigos encontrados se re-verifican con aritmética EXACTA (racionales)."""
    import mpmath
    mpmath.mp.dps = 40
    n = len(vars_)
    E = sp.lambdify(vars_, f - fp, "mpmath")
    p = [mpmath.mpf(str(sp.N(coords[v], 45))) for v in vars_]
    if n == 1:
        dirs = [np.array([1.0]), np.array([-1.0])]
    elif n == 2:
        th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
        dirs = [np.array([math.cos(a), math.sin(a)]) for a in th]
    else:
        rng = np.random.default_rng(7)
        U = rng.normal(size=(1500, n))
        dirs = list(U / np.linalg.norm(U, axis=1, keepdims=True))
    res = []
    for r in (1e-1, 1e-2, 1e-3):
        pos = neg = 0
        tp = tn = None
        for u in dirs:
            try:
                val = E(*[pi + mpmath.mpf(r) * mpmath.mpf(float(ui)) for pi, ui in zip(p, u)])
                val = mpmath.re(val)
            except Exception:  # noqa: BLE001
                continue
            if val > mpmath.mpf(10) ** -35:
                pos += 1
                tp = u if tp is None else tp
            elif val < -mpmath.mpf(10) ** -35:
                neg += 1
                tn = u if tn is None else tn
        res.append({"radio": r, "positivos": pos, "negativos": neg,
                    "testigo_mayor": (tp * r).tolist() if tp is not None else None,
                    "testigo_menor": (tn * r).tolist() if tn is not None else None})
    # re-verificación exacta de testigos en el radio más pequeño con ambos signos
    exacto = None
    for fila in reversed(res):
        if fila["testigo_mayor"] and fila["testigo_menor"]:
            try:
                pts = []
                for w in (fila["testigo_mayor"], fila["testigo_menor"]):
                    q = {v: coords[v] + sp.Rational(str(round(wi, 12))) for v, wi in zip(vars_, w)}
                    pts.append(_signo(sp.nsimplify(f.subs(q) - fp)))
                exacto = pts == [1, -1]
            except Exception:  # noqa: BLE001
                exacto = None
            break
    return res, exacto


def _analizar_orden_superior(f, vars_, coords, fp, diferenciable=True):
    """Pipeline riguroso para puntos donde el criterio de 2º orden no concluye.
    Devuelve (clasificación, certeza, criterio, pasos_texto, info). info["pasos_tex"] trae
    los mismos pasos con fórmulas en LaTeX entre $...$ (para la página web)."""
    pasos, ptex = [], []
    info = {"pasos_tex": ptex}
    L = sp.latex

    def add(plano, tx):
        pasos.append(plano)
        ptex.append(tx)

    def gam(c):
        return r"\gamma(t) = \left(" + ",\\ ".join(L(g) for g in c["_gamma"]) + r"\right)"
    # a) Formas de Taylor
    if diferenciable:
        try:
            formas, hs = _formas_taylor(f, vars_, coords)
            k, q = next(((k, q) for k, q in formas.items() if k >= 2 and q != 0), (None, None))
        except Exception:  # noqa: BLE001
            k, q, hs = None, None, None
        if k is not None:
            tipo, exacto, test = _definicion_forma(q, hs)
            info["taylor"] = {"orden": k, "forma": q, "tipo": tipo, "exacto": exacto}
            add(f"Taylor: el primer término no nulo de f(p+h) − f(p) es de orden {k}: "
                f"q_{k}(h) = {q}  →  forma {tipo}{'' if exacto else ' (numérico)'}.",
                f"**Taylor de orden superior.** El primer término no nulo del desarrollo es de orden ${k}$: "
                f"$$f(P+h) - f(P) = q_{{{k}}}(h) + O(\\|h\\|^{{{k + 1}}}),\\qquad q_{{{k}}}(h) = {L(q)}$$"
                f"La forma $q_{{{k}}}$ es **{tipo}**{'' if exacto else ' (verificación numérica)'}.")
            cert = DEMOSTRADO if exacto else NUMERICO
            if k % 2 == 1:
                add(f"Orden impar: q_{k}(−h) = −q_{k}(h), así que f toma valores mayores y "
                    "menores que f(p) arbitrariamente cerca → NO es extremo.",
                    f"Como ${k}$ es impar, $q_{{{k}}}(-h) = -q_{{{k}}}(h)$: en direcciones opuestas $f$ sube y baja, "
                    "así que **no es extremo** (punto de silla).")
                return SILLA, DEMOSTRADO, f"Taylor de orden {k} (impar)", pasos, info
            if tipo == "definida positiva":
                add("Forma definida positiva → mínimo local estricto.",
                    f"Como $q_{{{k}}}(h) > 0$ para todo $h \\neq 0$, domina al resto: **mínimo local estricto**.")
                return MIN_LOCAL, cert, f"Taylor de orden {k} (definida positiva)", pasos, info
            if tipo == "definida negativa":
                add("Forma definida negativa → máximo local estricto.",
                    f"Como $q_{{{k}}}(h) < 0$ para todo $h \\neq 0$: **máximo local estricto**.")
                return MAX_LOCAL, cert, f"Taylor de orden {k} (definida negativa)", pasos, info
            if tipo == "indefinida":
                add("Forma indefinida: hay direcciones donde f sube y otras donde baja → silla.",
                    f"$q_{{{k}}}$ toma valores positivos y negativos: hay direcciones en que $f$ sube y otras en que baja → **silla**.")
                return SILLA, cert, f"Taylor de orden {k} (indefinida)", pasos, info
            add("Forma semidefinida: hay direcciones 'planas', Taylor no decide. Se continúa.",
                f"$q_{{{k}}}$ se anula en algunas direcciones (\"planas\"): Taylor **no decide**. Se continúa.")
        elif diferenciable:
            add("Taylor hasta orden 8: no se encontró término no nulo concluyente.",
                "Taylor hasta orden $8$: no se encontró un término no nulo concluyente.")
    # b) Certificado exacto global
    sg, forma = _certificado(f, fp, vars_)
    if sg:
        info["certificado"] = f"f − f(p) = {forma} {sg} 0 para todo x"
        rel = r"\geq" if sg == "≥" else r"\leq"
        add(f"Certificado exacto: SymPy demuestra que f(x) − f(p) = {forma} {sg} 0 para TODO x real.",
            f"**Certificado exacto de signo.** SymPy demuestra que $$f(x) - f(P) = {L(forma)} \\;{rel}\\; 0 \\quad \\forall\\, x \\in \\mathbb{{R}}^{{{len(vars_)}}}$$"
            f"por lo tanto $P$ es un **{'mínimo' if sg == '≥' else 'máximo'} global**.")
        c = MIN_LOCAL if sg == "≥" else MAX_LOCAL
        return c, DEMOSTRADO, "certificado exacto de signo (global)", pasos, info
    # c) Curvas de prueba
    if diferenciable:
        curvas = _curvas_prueba(f, fp, vars_, coords)
        sube = [c for c in curvas if c["comportamiento"] == "sube"]
        baja = [c for c in curvas if c["comportamiento"] == "baja"]
        cambia = [c for c in curvas if c["comportamiento"] == "cambia"]
        info["curvas"] = [{"curva": c["curva"], "termino": str(c["termino"]),
                           "comportamiento": c["comportamiento"]} for c in curvas]
        info["_testigos"] = [c for c in (cambia[:1] or (sube[:1] + baja[:1]))]
        if cambia:
            c0 = cambia[0]
            add(f"Curva de prueba {c0['curva']}: f(γ(t)) − f(p) ≈ {c0['termino']} "
                "(potencia impar) → cambia de signo → NO es extremo.",
                f"**Curva de prueba** $${gam(c0)},\\qquad f(\\gamma(t)) - f(P) = {L(c0['termino'])} + \\dots$$"
                "La potencia es impar: cambia de signo en $t = 0$ → **no es extremo**.")
            return SILLA, DEMOSTRADO, "curvas de prueba exactas", pasos, info
        if sube and baja:
            add(f"Sobre {sube[0]['curva']}: f(γ(t)) − f(p) ≈ {sube[0]['termino']} > 0 (sube).",
                f"**Curva de prueba 1** $${gam(sube[0])},\\qquad f(\\gamma(t)) - f(P) = {L(sube[0]['termino'])} + \\dots > 0$$ (sube).")
            add(f"Sobre {baja[0]['curva']}: f(γ(t)) − f(p) ≈ {baja[0]['termino']} < 0 (baja).",
                f"**Curva de prueba 2** $${gam(baja[0])},\\qquad f(\\gamma(t)) - f(P) = {L(baja[0]['termino'])} + \\dots < 0$$ (baja).")
            add("Hay puntos arbitrariamente cercanos con valores mayores y menores → silla.",
                "Arbitrariamente cerca de $P$ hay puntos con valores mayores y menores que $f(P)$ → **punto de silla**.")
            return SILLA, DEMOSTRADO, "curvas de prueba exactas", pasos, info
        add(f"Curvas de prueba ({len(curvas)}): ninguna muestra cambio de signo "
            f"({len(sube)} suben, {len(baja)} bajan, {len(curvas) - len(sube) - len(baja)} constantes).",
            f"Se probaron ${len(curvas)}$ rectas y parábolas por $P$: ninguna muestra cambio de signo "
            f"(${len(sube)}$ suben, ${len(baja)}$ bajan).")
    # d) Sondeo numérico
    try:
        sondeo, testigo_exacto = _sondeo_numerico(f, fp, vars_, coords)
    except Exception as e:  # noqa: BLE001
        add(f"Sondeo numérico no disponible: {e}", f"Sondeo numérico no disponible: {e}")
        return INDETERMINADO, NUMERICO, "ningún criterio concluyó", pasos, info
    info["sondeo"] = sondeo
    ult = sondeo[-1]
    if ult["positivos"] and ult["negativos"]:
        extra = " (testigos re-verificados en aritmética exacta)" if testigo_exacto else ""
        add(f"Sondeo con 40 dígitos: incluso a distancia 10⁻³ hay valores mayores y menores que f(p){extra} → silla.",
            f"**Sondeo de alta precisión** (40 dígitos): incluso a distancia $10^{{-3}}$ hay valores mayores y menores "
            f"que $f(P)${extra} → **silla** (evidencia numérica).")
        return SILLA, NUMERICO, "sondeo numérico de alta precisión", pasos, info
    if ult["positivos"] and not ult["negativos"]:
        add("Sondeo con 40 dígitos: en radios 10⁻¹, 10⁻², 10⁻³ todos los valores son ≥ f(p) → probable mínimo (no demostrado).",
            "**Sondeo de alta precisión:** en radios $10^{-1}, 10^{-2}, 10^{-3}$ siempre $f \\geq f(P)$ → "
            "**probable mínimo** (no demostrado).")
        return MIN_LOCAL, NUMERICO, "sondeo numérico de alta precisión", pasos, info
    if ult["negativos"] and not ult["positivos"]:
        add("Sondeo con 40 dígitos: todos los valores cercanos son ≤ f(p) → probable máximo.",
            "**Sondeo de alta precisión:** siempre $f \\leq f(P)$ cerca de $P$ → **probable máximo**.")
        return MAX_LOCAL, NUMERICO, "sondeo numérico de alta precisión", pasos, info
    add("f parece constante alrededor del punto: no se puede clasificar.",
        "$f$ parece constante alrededor de $P$: no se puede clasificar.")
    return INDETERMINADO, NUMERICO, "ningún criterio concluyó", pasos, info


# ════════════════════════════════════════════════════════════════════════════
# 7. Puntos no diferenciables
# ════════════════════════════════════════════════════════════════════════════
def _candidatos_no_diferenciables(f, grad, vars_, P):
    """Puntos AISLADOS donde f existe pero ∇f no: ceros aislados de denominadores
    ≥ 0 (p. ej. x²+y² en √(x²+y²)) y anulación simultánea de argumentos de |·|."""
    cands, sistemas = [], []
    for g in grad:
        _, den = sp.fraction(sp.together(g))
        for fa in sp.Mul.make_args(sp.factor(den)):
            base = fa
            while base.is_Pow:
                base = base.base
            if base.is_number or not base.free_symbols:
                continue
            try:
                semidef = bool(base.is_nonnegative) or bool((-base).is_nonnegative)
            except Exception:  # noqa: BLE001
                semidef = False
            if semidef:
                sistemas.append([base] + [sp.diff(base, v) for v in vars_])
            else:
                P.advertencias.append(f"∇f no existe sobre el conjunto {base} = 0 "
                                      "(curva/superficie): esos puntos no se clasifican.")
    args_abs = list({a.args[0] for a in f.atoms(sp.Abs)} | {a.args[0] for a in f.atoms(sp.sign)})
    if args_abs:
        sistemas.append(args_abs)
    vistos = set()
    for sis in sistemas:
        try:
            sols = sp.solve(sis, vars_, dict=True)
        except Exception:  # noqa: BLE001
            continue
        for s in sols:
            if len(s) < len(vars_) or not all(_es_real(s[v]) for v in vars_):
                continue
            coords = {v: _limpiar(s[v]) for v in vars_}
            k = _clave(coords, vars_)
            if k in vistos:
                continue
            fv = f.subs(coords)
            if not _finito(fv):
                continue
            vistos.add(k)
            cands.append(PuntoCritico(coords=coords, valor_f=_limpiar(fv), tipo="no diferenciable"))
    return cands


# ════════════════════════════════════════════════════════════════════════════
# 8. Análisis global
# ════════════════════════════════════════════════════════════════════════════
def _analisis_global(P: ProblemaHessiana):
    f, vars_ = P.f, P.variables
    L = sp.latex
    G = {"acotada_inferiormente": None, "acotada_superiormente": None, "minimo_global": None,
         "maximo_global": None, "justificacion": [], "justificacion_tex": [], "certeza": DEMOSTRADO}

    def J(plano, tx):
        G["justificacion"].append(plano)
        G["justificacion_tex"].append(tx)
    cands = [p for p in P.todos if _num(p.valor_f) is not None]
    for p in cands:
        if p.certificado.startswith("≥"):
            G["acotada_inferiormente"] = True
            G["minimo_global"] = p.valor_f
            J(f"Certificado exacto: f(x) ≥ f(p) = {p.valor_f} para todo x.",
              f"**Certificado exacto:** $f(x) \\geq {L(p.valor_f)}$ para todo $x$, y se alcanza en un punto crítico.")
        if p.certificado.startswith("≤"):
            G["acotada_superiormente"] = True
            G["maximo_global"] = p.valor_f
            J(f"Certificado exacto: f(x) ≤ f(p) = {p.valor_f} para todo x.",
              f"**Certificado exacto:** $f(x) \\leq {L(p.valor_f)}$ para todo $x$, y se alcanza en un punto crítico.")

    es_poli = f.is_polynomial(*vars_)
    if es_poli and (G["minimo_global"] is None or G["maximo_global"] is None):
        Pp = sp.Poly(f, *vars_)
        d = Pp.total_degree()
        qd = sum((c * sp.Mul(*[v ** e for v, e in zip(vars_, m)])
                  for m, c in Pp.terms() if sum(m) == d), sp.Integer(0))
        G["forma_principal"] = {"grado": d, "forma": qd}
        qt = f"q_{{{d}}}(x) = {L(qd)}"
        if d == 0:
            J("f es constante.", "$f$ es constante.")
        elif d % 2 == 1:
            G["acotada_inferiormente"] = G["acotada_superiormente"] = False
            J(f"Polinomio de grado {d} (impar): a lo largo de una recta f(s·u) ≈ s^{d}·q_{d}(u) → ±∞. "
              "No hay extremos globales.",
              f"$f$ es un polinomio de grado ${d}$ (impar). Sobre una recta $x = s\\,u$ se tiene "
              f"$f(s\\,u) \\approx s^{{{d}}}\\, q_{{{d}}}(u) \\to \\pm\\infty$: **no hay extremos globales**.")
        else:
            hs = _simbolos_h(vars_)
            tipo, exacto, _ = _definicion_forma(qd.subs(dict(zip(vars_, hs))), hs)
            G["forma_principal"]["tipo"] = tipo
            if not exacto:
                G["certeza"] = NUMERICO
            if tipo == "definida positiva":
                G["acotada_inferiormente"], G["acotada_superiormente"] = True, False
                J(f"La parte de mayor grado q_{d} = {qd} es definida positiva: f es COERCIVA (f → +∞ cuando "
                  "‖x‖ → ∞), así que el mínimo global existe y se alcanza en un punto crítico.",
                  f"La parte de mayor grado $${qt}$$ es **definida positiva**, así que $f$ es **coerciva**: "
                  "$f(x) \\to +\\infty$ cuando $\\|x\\| \\to \\infty$. Por eso el mínimo global existe y se alcanza "
                  "en un punto crítico: basta comparar los valores críticos.")
                if cands and not P.familias:
                    G["minimo_global"] = min((p.valor_f for p in cands), key=_num)
            elif tipo == "definida negativa":
                G["acotada_superiormente"], G["acotada_inferiormente"] = True, False
                J(f"q_{d} = {qd} es definida negativa: f → −∞, el máximo global existe y se alcanza en un punto crítico.",
                  f"$${qt}$$ es **definida negativa**: $f \\to -\\infty$ y el máximo global existe y se alcanza en un punto crítico.")
                if cands and not P.familias:
                    G["maximo_global"] = max((p.valor_f for p in cands), key=_num)
            elif tipo == "indefinida":
                G["acotada_inferiormente"] = G["acotada_superiormente"] = False
                J(f"q_{d} = {qd} es indefinida: f → +∞ en unas direcciones y → −∞ en otras. No hay extremos globales.",
                  f"$${qt}$$ es **indefinida**: $f \\to +\\infty$ en unas direcciones y $f \\to -\\infty$ en otras. "
                  "**No hay extremos globales.**")
            elif tipo == "semidefinida positiva":
                G["acotada_superiormente"] = False
                J(f"q_{d} = {qd} es semidefinida positiva: f no está acotada superiormente; la cota inferior "
                  "no se decide con q_d.",
                  f"$${qt}$$ es **semidefinida positiva**: $f$ no está acotada superiormente; la cota inferior "
                  "no se decide solo con este término.")
            elif tipo == "semidefinida negativa":
                G["acotada_inferiormente"] = False
                J(f"q_{d} = {qd} es semidefinida negativa: f no está acotada inferiormente.",
                  f"$${qt}$$ es **semidefinida negativa**: $f$ no está acotada inferiormente.")
    elif not es_poli:
        try:                       # heurística numérica en esferas grandes
            n = len(vars_)
            fn = sp.lambdify(vars_, f, "numpy")
            rng = np.random.default_rng(3)
            U = rng.normal(size=(2000, n))
            U /= np.linalg.norm(U, axis=1, keepdims=True)
            filas = []
            for R in (5.0, 20.0, 100.0):
                with np.errstate(all="ignore"):
                    v = np.asarray(fn(*(R * U).T), dtype=float)
                v = v[np.isfinite(v)]
                if len(v):
                    filas.append((R, float(v.min()), float(v.max())))
            G["sondeo_lejano"] = filas
            if filas and cands:
                vmin = min(_num(p.valor_f) for p in cands)
                vmax = max(_num(p.valor_f) for p in cands)
                if all(fi[2] <= vmax + 1e-9 for fi in filas) and G["maximo_global"] is None:
                    J("Numérico: lejos del origen f nunca supera al mayor valor crítico → el máximo global parece ser ese valor.",
                      "**Numérico:** en esferas de radio $5, 20, 100$, $f$ nunca supera al mayor valor crítico → el máximo "
                      "global parece ser ese valor.")
                    G["maximo_global"] = max((p.valor_f for p in cands), key=_num)
                    G["certeza"] = NUMERICO
                if all(fi[1] >= vmin - 1e-9 for fi in filas) and G["minimo_global"] is None:
                    J("Numérico: lejos del origen f nunca baja del menor valor crítico → el mínimo global parece ser ese valor.",
                      "**Numérico:** en esferas de radio $5, 20, 100$, $f$ nunca baja del menor valor crítico → el mínimo "
                      "global parece ser ese valor.")
                    G["minimo_global"] = min((p.valor_f for p in cands), key=_num)
                    G["certeza"] = NUMERICO
            if filas and filas[-1][2] > 1e6:
                G["acotada_superiormente"] = False
            if filas and filas[-1][1] < -1e6:
                G["acotada_inferiormente"] = False
        except Exception:  # noqa: BLE001
            pass

    for p in cands:
        v = _num(p.valor_f)
        etiquetas = []
        if G["minimo_global"] is not None and abs(v - _num(G["minimo_global"])) < 1e-9 and p.clasificacion == MIN_LOCAL:
            etiquetas.append("mínimo global")
        if G["maximo_global"] is not None and abs(v - _num(G["maximo_global"])) < 1e-9 and p.clasificacion == MAX_LOCAL:
            etiquetas.append("máximo global")
        p.global_ = ", ".join(etiquetas)
    if not G["justificacion"]:
        J("No se pudo decidir el comportamiento global.", "No se pudo decidir el comportamiento global.")
    return G


# ════════════════════════════════════════════════════════════════════════════
# 9. Motor principal
# ════════════════════════════════════════════════════════════════════════════
def _clasificar_punto(P: ProblemaHessiana, p: PuntoCritico, H: sp.Matrix):
    n, vars_ = P.n, P.variables
    if p.tipo == "no diferenciable":
        p.clasif_segundo_orden = "no aplica (∇f no existe)"
        c, cert, crit, pasos, info = _analizar_orden_superior(P.f, vars_, p.coords, p.valor_f,
                                                              diferenciable=False)
        p.clasificacion, p.certeza, p.criterio, p.orden_superior = c, cert, crit, {"pasos": pasos, **info}
        if "certificado" in info:
            p.certificado = ("≥ " if c == MIN_LOCAL else "≤ ") + info["certificado"]
        return
    Hp = H.subs(p.coords).applyfunc(sp.simplify)
    p.hessiana = Hp
    p.menores, p.clasif_segundo_orden, p.criterio = _segundo_orden(Hp, n)
    if n == 2:
        p.fxx, p.D = p.menores[0][1], p.menores[1][1]
    try:
        p.autovalores, p.autovectores, vals, c_eig = _autovalores(Hp, n)
        p.verif_autovalores = {"clasificacion": c_eig, "coincide": c_eig == p.clasif_segundo_orden,
                               "valores": vals}
    except Exception:  # noqa: BLE001
        pass
    if p.clasif_segundo_orden != DUDOSO:
        p.clasificacion, p.certeza = p.clasif_segundo_orden, DEMOSTRADO
    else:
        c, cert, crit, pasos, info = _analizar_orden_superior(P.f, vars_, p.coords, p.valor_f)
        p.clasificacion, p.certeza = c, cert
        p.criterio = f"{p.criterio} → {crit}"
        p.orden_superior = {"pasos": pasos, **info}
        if "certificado" in info:
            p.certificado = ("≥ " if c == MIN_LOCAL else "≤ ") + info["certificado"]
    # certificado global para extremos (barato y muy informativo)
    if p.clasificacion in (MIN_LOCAL, MAX_LOCAL) and not p.certificado:
        sg, forma = _certificado(P.f, p.valor_f, vars_)
        if (sg == "≥" and p.clasificacion == MIN_LOCAL) or (sg == "≤" and p.clasificacion == MAX_LOCAL):
            p.certificado = f"{sg} f − f(p) = {forma} {sg} 0 para todo x"


def resolver(f, variables=None, metodo: str = "auto") -> ProblemaHessiana:
    """Resuelve y clasifica. Devuelve un ProblemaHessiana con objetos SymPy."""
    f_e, vars_ = _preparar(f, variables)
    P = ProblemaHessiana(f=f_e, variables=vars_)
    P.gradiente = [sp.simplify(sp.diff(f_e, v)) for v in vars_]
    H = sp.hessian(f_e, vars_).applyfunc(sp.simplify)
    P.hessiana_general = H
    if P.n == 2:
        P.D_general = sp.factor(sp.simplify(H.det()))

    args_abs = [a.args[0] for a in f_e.atoms(sp.Abs)]
    nucleos = []
    for g in P.gradiente:
        nuc, _, fuera = _nucleo(g)
        nucleos.append(nuc)
        P.factores_descartados += [str(x) for x in fuera if str(x) not in P.factores_descartados]
    P.ecuaciones = nucleos
    sols, P.metodo, P.base_groebner = _resolver_sistema(nucleos, vars_, metodo)

    vistos = set()
    for s in sols:
        faltan = [v for v in vars_ if v not in s]
        if faltan:
            _registrar_familia(P, s, faltan, H)
            continue
        if not all(_es_real(s[v]) for v in vars_):
            P.n_complejas += 1
            continue
        coords = {v: _limpiar(s[v]) for v in vars_}
        k = _clave(coords, vars_)
        if k in vistos:
            continue
        fv = f_e.subs(coords)
        if not _finito(fv):
            P.advertencias.append(f"Se descartó {k}: f no está definida allí.")
            continue
        algebraico = any(c.has(sp.CRootOf) for c in coords.values())
        grad_p = [g.subs(coords) if algebraico else sp.simplify(g.subs(coords)) for g in P.gradiente]
        if not all(_finito(x) for x in grad_p):
            continue        # ∇f no existe: lo recoge la búsqueda de puntos no diferenciables
        if any(_signo(a.subs(coords)) == 0 for a in args_abs):
            # está sobre un "pliegue" de |u|: ∇f no existe → punto crítico no diferenciable
            vistos.add(k)
            q = PuntoCritico(coords=coords, valor_f=_limpiar(fv), tipo="no diferenciable")
            _clasificar_punto(P, q, H)
            P.no_diferenciables.append(q)
            continue
        vistos.add(k)
        if algebraico:        # raíces CRootOf: verificación con 60 dígitos (simplify sería lentísimo)
            ok = all(abs(complex(sp.N(x, 60))) < 1e-45 for x in grad_p)
        else:
            ok = all(_signo(x) == 0 for x in grad_p)
        p = PuntoCritico(coords=coords, valor_f=_limpiar(fv), verificado=ok)
        _clasificar_punto(P, p, H)
        P.puntos.append(p)

    for p in _candidatos_no_diferenciables(f_e, P.gradiente, vars_, P):
        if _clave(p.coords, vars_) in vistos:
            continue
        _clasificar_punto(P, p, H)
        P.no_diferenciables.append(p)

    P.puntos.sort(key=lambda p: [(_num(p.coords[v]) or 0) for v in vars_])
    if P.n_complejas:
        P.advertencias.append(f"Se descartaron {P.n_complejas} soluciones complejas (no reales).")
    periodicas = (sp.sin, sp.cos, sp.tan, sp.cot, sp.sec, sp.csc)
    if f_e.has(*periodicas):
        P.advertencias.append("f contiene funciones periódicas: SymPy da las soluciones de la rama "
                              "principal; las demás se obtienen sumando múltiplos del período.")
    if not P.puntos and not P.no_diferenciables and not P.familias:
        P.advertencias.append("f no tiene puntos críticos reales.")
    P.analisis_global = _analisis_global(P)
    return P


def _registrar_familia(P, s, faltan, H):
    """Soluciones con parámetros libres: se guarda la familia y un representante."""
    vars_ = P.variables
    expr = {v: s.get(v, v) for v in vars_}
    params = sorted({x for e in expr.values() for x in e.free_symbols}, key=str)
    rep = None
    for val in (0, 1, -1, 2):
        c = {v: _limpiar(sp.sympify(e).subs({q: val for q in params})) for v, e in expr.items()}
        if all(_es_real(x) and _finito(x) for x in c.values()) and _finito(P.f.subs(c)):
            rep = PuntoCritico(coords=c, valor_f=_limpiar(P.f.subs(c)), tipo="familia")
            break
    fam = {"expr": expr, "parametros": params, "representante": rep}
    if rep is not None:
        _clasificar_punto(P, rep, H)
        valf = sp.simplify(P.f.subs(expr, simultaneous=True))
        fam["valor_f"] = valf
        fam["f_constante"] = not valf.free_symbols
        if fam["f_constante"] and rep.clasificacion in (MIN_LOCAL, MAX_LOCAL):
            rep.criterio += " · NO estricto: f es constante sobre toda la familia"
    P.familias.append(fam)
    P.advertencias.append("Hay una FAMILIA de puntos críticos (infinitos puntos, no aislados): "
                          "la Hessiana es singular en todos ellos.")


# ════════════════════════════════════════════════════════════════════════════
# 10. Serialización JSON (formato MCP)
# ════════════════════════════════════════════════════════════════════════════
def _s(e) -> str:
    return str(e).replace("**", "^")


def _sust_latex(expr, coords) -> str:
    """LaTeX de expr con los valores sustituidos SIN evaluar (p. ej. 2·(−1)^2)."""
    rep = {}
    for i, (v, val) in enumerate(coords.items()):
        t = sp.latex(val)
        simple = (val.is_Integer and val >= 0) or val.is_Symbol
        rep[v] = sp.Symbol("{}" * (i + 1) + (t if simple else r"\left(" + t + r"\right)"))
    try:
        return sp.latex(expr.xreplace(rep), mul_symbol="dot")
    except Exception:  # noqa: BLE001
        return sp.latex(expr)


def _par(v) -> str:
    return r"\left(" + sp.latex(v) + r"\right)"


def _regla_tex(p: PuntoCritico, n: int) -> str:
    L = sp.latex
    if p.hessiana is None:
        return "En este punto $\\nabla f$ no existe: el criterio de la segunda derivada **no aplica**."
    s = [m[2] for m in p.menores]
    if n == 1:
        v = p.menores[0][1]
        return (f"$f''(P) = {L(v)}$" + (" $> 0$ → la gráfica es cóncava hacia arriba: **mínimo local**." if s[0] > 0 else
                " $< 0$ → cóncava hacia abajo: **máximo local**." if s[0] < 0 else
                " $= 0$ → el criterio **no decide** (caso dudoso)."))
    if n == 2:
        D, fxx = p.D, p.fxx
        if s[1] > 0:
            return (f"Como $D = {L(D)} > 0$ y $f_{{xx}} = {L(fxx)} {'> 0' if s[0] > 0 else '< 0'}$, la superficie "
                    + ("es un *cuenco* ∪ alrededor de $P$: **mínimo local**." if s[0] > 0 else
                       "es una *cúpula* ∩ alrededor de $P$: **máximo local**."))
        if s[1] < 0:
            return (f"Como $D = {L(D)} < 0$, la Hessiana tiene autovalores de signos opuestos: la superficie sube en "
                    "una dirección y baja en otra → **punto de silla**.")
        return ("Como $D = 0$, el criterio de la segunda derivada **no decide** (caso dudoso): "
                "se pasa al análisis de orden superior.")
    txt = "**Criterio de Sylvester:** " + ", ".join(
        f"$\\Delta_{{{k}}} {'> 0' if sg > 0 else '< 0' if sg < 0 else '= 0'}$" for k, _, sg in p.menores) + ". "
    if p.clasif_segundo_orden == MIN_LOCAL:
        return txt + "Todos positivos → $H$ definida positiva → **mínimo local**."
    if p.clasif_segundo_orden == MAX_LOCAL:
        return txt + "Signos alternados empezando en negativo → $H$ definida negativa → **máximo local**."
    if p.clasif_segundo_orden == SILLA:
        return txt + "$\\det H \\neq 0$ sin ninguno de los dos patrones → $H$ indefinida → **punto de silla**."
    return txt + "$\\det H = 0$ → el criterio **no decide** (caso dudoso)."


def _pc_a_dict(p: PuntoCritico, P) -> dict:
    vars_ = P.variables
    d = {
        "tipo": p.tipo,
        "coordenadas": {str(v): str(p.coords[v]) for v in vars_},
        "coordenadas_latex": {str(v): sp.latex(p.coords[v]) for v in vars_},
        "coordenadas_num": {str(v): _num(p.coords[v]) for v in vars_},
        "valor_f": str(p.valor_f), "valor_f_latex": sp.latex(p.valor_f), "valor_f_num": _num(p.valor_f),
        "verificado_gradiente_cero": p.verificado,
        "clasificacion_segundo_orden": p.clasif_segundo_orden,
        "clasificacion": p.clasificacion,
        "certeza": p.certeza,
        "criterio": p.criterio,
        "certificado_global": _s(p.certificado),
        "comparacion_global": p.global_,
        "f_evaluada_latex": (f"f({', '.join(sp.latex(p.coords[v]) for v in vars_)}) = "
                             f"{_sust_latex(P.f, p.coords)} = {sp.latex(p.valor_f)}"),
        "regla_tex": _regla_tex(p, P.n),
    }
    if p.hessiana is not None:
        d["hessiana"] = [[str(x) for x in fila] for fila in p.hessiana.tolist()]
        d["hessiana_latex"] = sp.latex(p.hessiana)
        d["menores_principales"] = [{"orden": k, "valor": str(v), "valor_latex": sp.latex(v),
                                     "submatriz_latex": sp.latex(p.hessiana[:k, :k], mat_str="vmatrix", mat_delim=""),
                                     "valor_num": _num(v), "signo": s} for k, v, s in p.menores]
    if p.D is not None:
        d["D"], d["D_latex"], d["fxx"], d["fxx_latex"] = str(p.D), sp.latex(p.D), str(p.fxx), sp.latex(p.fxx)
        H = p.hessiana
        d["calculo_D_latex"] = (r"D(P) = f_{xx}\,f_{yy} - f_{xy}^{2} = " + _par(H[0, 0]) + _par(H[1, 1]) + " - "
                                + _par(H[0, 1]) + "^{2} = " + sp.latex(p.D))
    if p.autovalores:
        d["autovalores"] = [{"exacto": str(a["exacto"]) if a["exacto"] is not None else None,
                             "latex": sp.latex(a["exacto"]) if a["exacto"] is not None else None,
                             "num": a["num"], "multiplicidad": a["mult"]} for a in p.autovalores]
        d["autovectores_num"] = p.autovectores
        d["verificacion_autovalores"] = p.verif_autovalores
    if p.orden_superior:
        o = {k: v for k, v in p.orden_superior.items() if not k.startswith("_")}
        o["pasos"] = [_s(x) for x in o.get("pasos", [])]
        o["pasos_tex"] = list(p.orden_superior.get("pasos_tex", []))
        if "taylor" in o:
            t = o["taylor"]
            o["taylor"] = {"orden": t["orden"], "forma": str(t["forma"]),
                           "forma_latex": sp.latex(t["forma"]), "tipo": t["tipo"], "exacto": t["exacto"]}
        d["analisis_orden_superior"] = o
    return d


def a_dict(P: ProblemaHessiana) -> dict:
    G = dict(P.analisis_global)
    G["justificacion"] = [_s(j) for j in G["justificacion"]]
    for k in ("minimo_global", "maximo_global"):
        if G.get(k) is not None:
            G[k + "_latex"] = sp.latex(G[k])
            G[k] = str(G[k])
    if "forma_principal" in G:
        fp = dict(G["forma_principal"])
        fp["latex"] = sp.latex(fp["forma"])
        fp["forma"] = str(fp["forma"])
        G["forma_principal"] = fp
    familias = []
    for fa in P.familias:
        familias.append({  # noqa: E501
            "parametrizacion": {str(k): str(v) for k, v in fa["expr"].items()},
            "parametrizacion_latex": {str(k): sp.latex(v) for k, v in fa["expr"].items()},
            "parametros": [str(x) for x in fa["parametros"]],
            "valor_f": str(fa.get("valor_f", "")),
            "representante": _pc_a_dict(fa["representante"], P) if fa["representante"] else None,
        })
    return {
        "entrada": {"f": str(P.f), "f_latex": sp.latex(P.f), "variables": [str(v) for v in P.variables],
                    "n": P.n},
        "variables_latex": [sp.latex(v) for v in P.variables],
        "gradiente": [{"variable": str(v), "expr": str(g), "latex": sp.latex(g),
                       "lhs": r"\frac{\partial f}{\partial " + sp.latex(v) + "}"}
                      for v, g in zip(P.variables, P.gradiente)],
        "segundas_derivadas": [{"lhs": "f_{" + sp.latex(a) + sp.latex(b) + "}",
                                "latex": sp.latex(P.hessiana_general[i, j])}
                               for i, a in enumerate(P.variables) for j, b in enumerate(P.variables) if i <= j],
        "base_groebner_latex": [sp.latex(g) for g in P.base_groebner] if P.base_groebner else None,
        "factores_descartados_latex": [sp.latex(sp.sympify(x)) for x in P.factores_descartados],
        "sistema_resuelto": [{"expr": f"{e} = 0", "latex": sp.latex(e) + " = 0"} for e in P.ecuaciones],
        "factores_descartados": P.factores_descartados,
        "metodo_resolucion": P.metodo,
        "base_groebner": [_s(g) for g in P.base_groebner] if P.base_groebner else None,
        "hessiana_general": [[str(x) for x in fila] for fila in P.hessiana_general.tolist()],
        "hessiana_general_latex": sp.latex(P.hessiana_general),
        "D_general": str(P.D_general) if P.D_general is not None else None,
        "D_general_latex": sp.latex(P.D_general) if P.D_general is not None else None,
        "puntos_criticos": [_pc_a_dict(p, P) for p in P.puntos],
        "puntos_no_diferenciables": [_pc_a_dict(p, P) for p in P.no_diferenciables],
        "familias": familias,
        "soluciones_complejas_descartadas": P.n_complejas,
        "analisis_global": G,
        "advertencias": P.advertencias,
    }


def resolver_hessiana(f, variables=None, metodo: str = "auto", incluir_grafico: bool = False,
                      rango=None) -> dict:
    """PUNTO DE ENTRADA PARA EL MCP. Devuelve un dict 100 % serializable a JSON."""
    P = resolver(f, variables, metodo)
    out = a_dict(P)
    if incluir_grafico:
        out["grafico"] = datos_grafico(P, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 11. Datos numéricos para graficar
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


def _rango_auto(P, rango, igualar=True):
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


def datos_grafico(P: ProblemaHessiana, rango=None, resolucion: int = 121) -> dict:
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
    caja = _rango_auto(P, rango, igualar=(n == 2))
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
        minimos = [q["coords"] for q in puntos if q["clasificacion"] == MIN_LOCAL]
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
# 12. PNG (matplotlib)
# ════════════════════════════════════════════════════════════════════════════
COLORES = {MIN_LOCAL: "#3f6e7d", MAX_LOCAL: "#b0502c", SILLA: "#7a5873",
           INDETERMINADO: "#8c8279", DUDOSO: "#8c8279"}
PALETA_CUENCAS = ["#3f6e7d", "#6b7a4f", "#a07b4f", "#5f6f8a", "#8a5a44", "#7a5873", "#4f7d6a"]
_TERRA = ["#2c2420", "#4c2c21", "#7a3a24", "#ab4f2c", "#cf8660", "#e7bf9e", "#f7ece0"]


def _cmap_terra():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("terra", _TERRA)


def _col(p):
    if p["tipo"] == "no diferenciable":
        return "#c38d35"
    return COLORES.get(p["clasificacion"], "#8c8279")


def graficar_png(P: ProblemaHessiana, ruta: str, datos: dict | None = None, dpi: int = 130):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.lines import Line2D

    D = datos or datos_grafico(P)
    titulo = f"f({', '.join(D['variables'])}) = {_s(P.f)}"
    if D["tipo"] == "1d":
        fig, ax = plt.subplots(figsize=(9, 5.5))
        ax.plot(D["x"], [np.nan if v is None else v for v in D["y"]], color="#2b2420", lw=2)
        for p in D["puntos"]:
            ax.plot(p["coords"][0], p["f"], "o", ms=11, color=_col(p), mec="white", mew=2)
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
            ax.plot(px, py, "o", ms=12, color=_col(p), mec="white", mew=2, zorder=7)
            ax.annotate(f"{p['id']} {p['etiqueta']}", (px, py), textcoords="offset points", xytext=(9, 9),
                        fontsize=8, color="white", bbox=dict(boxstyle="round", fc=_col(p), alpha=0.9))
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
            ax3.scatter(*p["coords"], p["f"], s=90, color=_col(p), edgecolor="white", depthshade=False,
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
            ax.plot(*p["coords"], "o", ms=11, color=_col(p), mec="white", mew=2)
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
                    cell.set_facecolor(_col(D["puntos"][r - 1])); cell.set_text_props(color="white")
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
                    ax.plot(p["coords"][i], p["coords"][j], "o", ms=11, color=_col(p), mec="white", mew=2)
                    ax.annotate(p["id"], (p["coords"][i], p["coords"][j]), textcoords="offset points",
                                xytext=(7, 7), color="white", fontsize=9)
            ax.set_xlabel(nombres[i]); ax.set_ylabel(nombres[j])
            ax.set_title(f"corte {nombres[k]} = {p0[k]:.4g}", fontsize=10)
    else:
        raise ValueError("Con más de 3 variables no hay representación geométrica.")
    leyenda = [Line2D([0], [0], marker="o", ls="", ms=10, color=c, label=l) for l, c in
               [("mínimo local", COLORES[MIN_LOCAL]), ("máximo local", COLORES[MAX_LOCAL]),
                ("punto de silla", COLORES[SILLA]), ("indeterminado", "#8c8279"),
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
# 13. HTML interactivo (Plotly.js + KaTeX)
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


_JS_HESSIANA = r"""/* ═════════════ Módulo: Puntos críticos y matriz Hessiana ═════════════ */
const E = R.entrada, V = E.variables, VT = R.variables_latex, N = E.n;
const COLCL = {"mínimo local":COLOR.min, "máximo local":COLOR.max, "punto de silla":COLOR.silla};
const colorDe = p => p.tipo === "no diferenciable" ? COLOR.sing : (COLCL[p.clasificacion] || COLOR.ind);
const colorPunto = colorDe;
const TODOS = [...R.puntos_criticos, ...R.puntos_no_diferenciables, ...R.familias.filter(f => f.representante).map(f => f.representante)]
  .map((p, i) => Object.assign({id:"P" + (i + 1)}, p));
const ptTex = p => "\\left(" + V.map(v => p.coordenadas_latex[v]).join(",\\ ") + "\\right)";
const idTex = id => id.replace(/(\d+)/, "_{$1}");
const VARS = VT.join(",\\,");
const dudoso = p => (p.clasificacion_segundo_orden || "").startsWith("caso dudoso");
const hov = p => `<b>${p.id}</b> ${p.etiqueta}<br>f = ${fmt(p.f, 6)}<br>${p.clasificacion} (${p.certeza})`;
const LAM_POS = "#e0a64a", LAM_NEG = "#3f6e7d";

$id("enunciado").innerHTML = tex("f(" + VARS + ") = " + E.f_latex + "\\qquad \\text{en un abierto de }\\ \\mathbb{R}^{" + N + "}");
$id("meta").innerHTML = `<span>${N} variable(s)</span><span>${esc(R.metodo_resolucion)}</span><span>${TODOS.length} punto(s) crítico(s)</span>` +
  (R.familias.length ? `<span>${R.familias.length} familia(s)</span>` : "");

/* ─────────── 1. Resumen ─────────── */
INIT.resumen = () => {
  const cnt = c => TODOS.filter(p => p.clasificacion === c).length;
  const K = [[TODOS.length, "puntos críticos", COLOR.ac], [cnt("mínimo local"), "mínimos locales", COLOR.min],
             [cnt("máximo local"), "máximos locales", COLOR.max], [cnt("punto de silla"), "puntos de silla", COLOR.silla],
             [TODOS.filter(dudoso).length, "casos dudosos resueltos", COLOR.sing]];
  let h = `<div class="kpis">${K.map(([n, t, c]) => `<div class="kpi" style="--c:${c}"><b>${n}</b><span>${t}</span></div>`).join("")}</div>`;
  h += `<div class="card"><h2>Puntos críticos</h2><p class="sub">Soluciones reales de ∇f = 0 (y puntos donde ∇f no existe), con su clasificación y el grado de certeza.</p><div class="pts">`;
  TODOS.forEach(p => {
    h += `<div class="pt" style="--c:${colorDe(p)}"><div class="cab"><div><b>${p.id}</b>&nbsp; ${tex(ptTex(p))}</div><span class="chip">${esc(p.clasificacion)}</span></div><table class="kv">`;
    if (p.tipo !== "estacionario") h += `<tr><td>tipo</td><td><b>${esc(p.tipo)}</b></td></tr>`;
    h += `<tr><td>valor de f</td><td>${tex(p.valor_f_latex)} <span class="nota">≈ ${fmt(p.valor_f_num, 6)}</span></td></tr>`;
    if (p.D_latex !== undefined) h += `<tr><td>D · f<sub>xx</sub></td><td>${tex("D = " + p.D_latex + ",\\quad f_{xx} = " + p.fxx_latex)}</td></tr>`;
    else if (p.menores_principales) h += `<tr><td>menores Δ<sub>k</sub></td><td>${p.menores_principales.map(m => tex("\\Delta_{" + m.orden + "} = " + m.valor_latex)).join(", ")}</td></tr>`;
    if (p.autovalores) h += `<tr><td>autovalores de H</td><td>${p.autovalores.map(a => a.latex ? tex(a.latex) : fmt(a.num, 5)).join(", ")}</td></tr>`;
    h += `<tr><td>criterio</td><td>${esc(p.criterio)}</td></tr><tr><td>certeza</td><td>${esc(p.certeza)}${p.verificado_gradiente_cero ? " · ∇f(P) = 0 ✔" : ""}</td></tr>`;
    if (p.comparacion_global) h += `<tr><td>global</td><td><b>${esc(p.comparacion_global)}</b></td></tr>`;
    h += `</table></div>`;
  });
  R.familias.forEach(f => h += `<div class="pt" style="--c:${COLOR.sing}"><div class="cab"><b>Familia de puntos críticos</b><span class="chip">∞ puntos</span></div>
      ${eq("\\left(" + V.map(v => f.parametrizacion_latex[v]).join(",\\ ") + "\\right)")}<p class="nota">Parámetro(s) libre(s): ${f.parametros.join(", ")} · f en la familia = ${esc(f.valor_f)}</p></div>`);
  if (!TODOS.length && !R.familias.length) h += `<p>f no tiene puntos críticos reales.</p>`;
  h += `</div></div>`;
  const G = R.analisis_global;
  h += `<div class="card"><h2>Análisis global</h2>${G.justificacion_tex.map(j => `<p>${mt(j)}</p>`).join("")}`;
  if (G.minimo_global_latex) h += eq("\\boxed{\\min_{\\mathbb{R}^{" + N + "}} f = " + G.minimo_global_latex + "}");
  if (G.maximo_global_latex) h += eq("\\boxed{\\max_{\\mathbb{R}^{" + N + "}} f = " + G.maximo_global_latex + "}");
  h += `<p class="nota">Certeza: ${esc(G.certeza)}</p>` + R.advertencias.map(a => `<p class="warn">⚠ ${esc(a)}</p>`).join("") + `</div>`;
  $id("tab-resumen").innerHTML = h;
};

/* ─────────── 2. Procedimiento ─────────── */
INIT.proc = () => {
  let h = `<div class="card" style="margin-bottom:22px"><h2>Procedimiento completo</h2><p class="sub" style="margin:0">Cada paso reproduce el cálculo exacto que hizo SymPy; los decimales solo aparecen como apoyo.</p></div>`, k = 0;
  const paso = (t, cuerpo) => h += `<div class="paso"><div class="num">${++k}</div><div class="cuerpo"><h3>${mt(t)}</h3>${cuerpo}</div></div>`;
  paso("Función a optimizar", eq("f(" + VARS + ") = " + E.f_latex) +
    `<div class="idea">${mt("**Teorema de Fermat.** En un dominio abierto, todo extremo local es un **punto crítico**: un punto donde $\\nabla f = 0$ o donde $\\nabla f$ no existe. Primero se hallan todos; después se clasifican.")}</div>`);
  paso("Gradiente $\\nabla f$", `<p>${mt("Se calcula cada derivada parcial de forma simbólica:")}</p>` +
    eq("\\begin{aligned}" + R.gradiente.map(g => g.lhs + " &= " + g.latex).join("\\\\[10pt]") + "\\end{aligned}"));
  let s = eq("\\nabla f = 0 \\iff \\begin{cases}" + R.gradiente.map(g => g.latex + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  if (R.factores_descartados_latex.length) s += `<p>${mt("Los factores $" + R.factores_descartados_latex.join(",\\ ") + "$ **nunca se anulan**, así que se pueden eliminar sin perder soluciones. El sistema equivale a:")}</p>` +
    eq("\\begin{cases}" + R.sistema_resuelto.map(e => e.latex).join("\\\\[2pt]") + "\\end{cases}");
  s += `<p>${mt("Método: **" + esc(R.metodo_resolucion) + "**.")}</p>`;
  if (R.base_groebner_latex) s += `<p>${mt("La **base de Gröbner** (orden lexicográfico) deja el sistema *triangular*: la última ecuación tiene una sola incógnita; se resuelve y se sustituye hacia arriba. Tiene exactamente las mismas soluciones:")}</p>` +
    eq("\\begin{cases}" + R.base_groebner_latex.map(g => g + " = 0").join("\\\\[2pt]") + "\\end{cases}");
  const est = TODOS.filter(p => p.tipo === "estacionario");
  if (est.length) s += `<p>Soluciones <b>reales</b> (cada una se verificó sustituyéndola en ∇f):</p>` +
    eq("\\begin{array}{c|" + "c".repeat(VT.length) + "|c} & " + VT.join(" & ") + " & f \\\\ \\hline " +
       est.map(p => idTex(p.id) + " & " + V.map(v => p.coordenadas_latex[v]).join(" & ") + " & " + p.valor_f_latex).join(" \\\\[3pt] ") + "\\end{array}");
  R.familias.forEach(f => s += `<p>${mt("Además hay una **familia** de soluciones (infinitos puntos críticos, no aislados):")}</p>` +
    eq("\\left(" + V.map(v => f.parametrizacion_latex[v]).join(",\\ ") + "\\right),\\qquad " + f.parametros.join(",") + " \\in \\mathbb{R}"));
  if (R.soluciones_complejas_descartadas) s += `<p class="nota">Se descartaron ${R.soluciones_complejas_descartadas} soluciones complejas (no pertenecen a ℝⁿ).</p>`;
  if (R.puntos_no_diferenciables.length) s += `<p>${mt("Puntos donde $\\nabla f$ **no existe** (también son críticos): $" + TODOS.filter(p => p.tipo === "no diferenciable").map(p => idTex(p.id) + " = " + ptTex(p)).join(",\\ ") + "$.")}</p>`;
  paso("Sistema $\\nabla f = 0$ y su resolución exacta", s);
  let hs = `<p>${mt("Segundas derivadas parciales:")}</p>` + eq("\\begin{aligned}" + R.segundas_derivadas.map(d => d.lhs + " &= " + d.latex).join("\\\\[6pt]") + "\\end{aligned}") +
    eq("H(" + VARS + ") = " + R.hessiana_general_latex);
  if (R.D_general_latex) hs += `<p>${mt("El **discriminante** es el determinante de $H$:")}</p>` + eq("D(x,y) = f_{xx}\\,f_{yy} - f_{xy}^{2} = " + R.D_general_latex);
  paso("Matriz Hessiana", hs);
  let cr = "";
  if (N === 2) cr = `<table class="kv" style="max-width:560px"><tr><td>${tex("D > 0,\\ f_{xx} > 0")}</td><td>mínimo local (cuenco ∪)</td></tr>
      <tr><td>${tex("D > 0,\\ f_{xx} < 0")}</td><td>máximo local (cúpula ∩)</td></tr><tr><td>${tex("D < 0")}</td><td>punto de silla</td></tr>
      <tr><td>${tex("D = 0")}</td><td>caso dudoso → análisis de orden superior</td></tr></table>`;
  else if (N === 1) cr = `<p>${mt("$f''(P) > 0$ → mínimo; $f''(P) < 0$ → máximo; $f''(P) = 0$ → dudoso.")}</p>`;
  else cr = `<p>${mt("**Criterio de Sylvester** con los menores principales $\\Delta_k = \\det H_{k\\times k}$: todos $> 0$ → mínimo; $(-1)^k\\Delta_k > 0$ → máximo; $\\det H \\neq 0$ sin esos patrones → silla; $\\det H = 0$ → dudoso. Se confirma con el signo de los autovalores de $H$.")}</p>`;
  cr += `<div class="idea">${mt("**¿Por qué funciona?** Cerca de un punto crítico, $f(P+h) \\approx f(P) + \\tfrac{1}{2}\\,h^{T} H(P)\\, h$. El signo de esa forma cuadrática (definida positiva, negativa o indefinida) decide si $f$ sube en todas las direcciones, baja en todas, o sube en unas y baja en otras.")}</div>`;
  paso("Criterio de la segunda derivada", cr);
  let c = "";
  TODOS.forEach((p, i) => {
    const col = colorDe(p);
    c += `<details class="sp" ${i === 0 ? "open" : ""}><summary><b>${p.id}</b> ${tex(ptTex(p))} <span class="chip" style="--c:${col}">${esc(p.clasificacion)}</span>${dudoso(p) ? `<span class="chip" style="--c:${COLOR.sing}">D = 0 resuelto</span>` : ""}</summary><div class="in">`;
    c += `<p><b>a)</b> Valor de la función:</p>` + eq(p.f_evaluada_latex);
    if (p.hessiana_latex) {
      c += `<p><b>b)</b> Hessiana evaluada en el punto:</p>` + eq("H(" + idTex(p.id) + ") = " + p.hessiana_latex);
      if (p.calculo_D_latex) c += `<p><b>c)</b> Discriminante:</p>` + eq(p.calculo_D_latex) + eq("f_{xx}(" + idTex(p.id) + ") = " + p.fxx_latex);
      else if (N === 1) c += eq("f''(" + idTex(p.id) + ") = " + p.menores_principales[0].valor_latex);
      else p.menores_principales.forEach((m, j) => { if (j === 0) c += `<p><b>c)</b> Menores principales:</p>`;
        c += eq("\\Delta_{" + m.orden + "} = " + m.submatriz_latex + " = " + m.valor_latex); });
      if (p.autovalores) c += `<p><b>d)</b> Autovalores de la Hessiana (curvaturas principales):</p>` +
        eq("\\lambda(H) = \\left\\{" + p.autovalores.map(a => (a.latex || fmt(a.num, 5)) + (a.multiplicidad > 1 ? "\\ (\\times " + a.multiplicidad + ")" : "")).join(",\\ ") + "\\right\\}");
    } else c += `<p>${mt("En este punto $\\nabla f$ **no existe**, así que no hay Hessiana: se estudia directamente el signo de $f - f(P)$.")}</p>`;
    c += `<p>${mt(p.regla_tex)}</p>`;
    const a = p.analisis_orden_superior;
    if (a && a.pasos_tex && a.pasos_tex.length) c += `<div class="idea"><b>Análisis de orden superior</b><ol class="pasos">${a.pasos_tex.map(t => `<li>${mt(t)}</li>`).join("")}</ol></div>`;
    c += `<div class="concl" style="--c:${col}">${mt("⇒ $" + idTex(p.id) + " = " + ptTex(p) + "$ es **" + esc(p.clasificacion) + "** (" + esc(p.certeza) + "), con $f(" + idTex(p.id) + ") = " + p.valor_f_latex + "$." + (p.comparacion_global ? " Además es **" + esc(p.comparacion_global) + "**." : ""))}</div>`;
    const va = p.verificacion_autovalores;
    if (va && va.valores && !dudoso(p)) c += `<p class="nota">Verificación independiente por autovalores: ${va.valores.map(x => fmt(x, 4)).join(", ")} → ${va.coincide ? "coincide ✔" : "difiere ✘"}</p>`;
    c += `</div></details>`;
  });
  paso("Clasificación de cada punto crítico", c || "<p>No hay puntos que clasificar.</p>");
  const G = R.analisis_global;
  let g = G.justificacion_tex.map(j => `<p>${mt(j)}</p>`).join("");
  if (G.minimo_global_latex) g += eq("\\boxed{\\min f = " + G.minimo_global_latex + "}");
  if (G.maximo_global_latex) g += eq("\\boxed{\\max f = " + G.maximo_global_latex + "}");
  paso("Análisis global", g + `<p class="nota">Certeza: ${esc(G.certeza)}</p>`);
  $id("tab-proc").innerHTML = h;
};

/* ─────────── 3. Gráfico 3D dinámico ─────────── */
INIT.g3d = () => {
  const P = $id("tab-g3d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin representación geométrica</h2><p class="sub">Con más de 3 variables no hay gráfico; revisa el procedimiento y el JSON.</p></div>`; return; }
  if (D.tipo === "1d") { P.innerHTML = `<div class="card"><h2>Una sola variable</h2><p class="sub">La gráfica de f es una curva plana: está en la pestaña «Gráficos 2D».</p></div>`; return; }
  if (D.tipo === "2d") g3dSuperficie(P); else g3dVolumen(P);
};

/* curva de nivel f = c por "marching squares" sobre la malla (x, y, Z) */
function nivelSegs(xs, ys, Z, c) {
  const X = [], Y = [];
  for (let j = 0; j < ys.length - 1; j++) for (let i = 0; i < xs.length - 1; i++) {
    const v = [Z[j][i], Z[j][i + 1], Z[j + 1][i + 1], Z[j + 1][i]];
    if (v.some(q => q === null)) continue;
    const P = [[xs[i], ys[j]], [xs[i + 1], ys[j]], [xs[i + 1], ys[j + 1]], [xs[i], ys[j + 1]]], cut = [];
    for (let e = 0; e < 4; e++) { const a = v[e] - c, b = v[(e + 1) % 4] - c;
      if ((a < 0 && b >= 0) || (a >= 0 && b < 0)) { const t = a / (a - b), p = P[e], q = P[(e + 1) % 4];
        cut.push([p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]); } }
    for (let k = 0; k + 1 < cut.length; k += 2) { X.push(cut[k][0], cut[k + 1][0], null); Y.push(cut[k][1], cut[k + 1][1], null); }
  }
  return [X, Y];
}

function g3dSuperficie(P) {
  const zs = D.z.flat().filter(v => v !== null).sort((a, b) => a - b), qz = t => zs[Math.floor(t * (zs.length - 1))];
  const fcr = D.puntos.map(p => p.f).filter(v => v !== null);
  const fM = fcr.length ? Math.max(...fcr) : qz(0.5), fm = fcr.length ? Math.min(...fcr) : qz(0.5);
  const zBot = zs[0], zTop = zs[zs.length - 1];
  const zCap = Math.min(zTop, Math.max(qz(0.55), fM + 0.8 * (fM - fm) + 0.12 * (zTop - zBot)));
  const zLow = Math.max(zBot, Math.min(qz(0.45), fm - 0.8 * (fM - fm) - 0.12 * (zTop - zBot)));
  const dentro = v => v !== null && v <= zCap && v >= zLow;
  const recorta = M => M.map(f => f.map(v => dentro(v) ? v : null));
  const zmin = zLow, zmax = zCap;
  const [x0, x1] = D.rango[0], [y0, y1] = D.rango[1];
  const cDe = v => zmin + (zmax - zmin) * v / 500, vDe = c => Math.round(500 * (c - zmin) / ((zmax - zmin) || 1));
  const c0 = D.puntos.length ? D.puntos[0].f : cDe(250);
  const flujos = D.flujo.filter(l => l.x.length > 3);
  const bol = flujos.filter((_, i) => i % Math.max(1, Math.ceil(flujos.length / 60)) === 0);
  const T = Math.max(1, ...bol.map(l => l.x.length));
  const opts = D.puntos.filter(p => p.taylor);
  P.innerHTML = `<div class="card"><h2>Superficie z = f(${V.join(", ")})</h2>
    <p class="sub">Suelta bolitas sobre la superficie: ruedan siguiendo −∇f (máximo descenso) y se acumulan en los mínimos; cada color es una cuenca de atracción. Mueve la curva de nivel f = c: al pasar por un punto de silla la curva cambia de forma (se cruza consigo misma).</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Descenso por el gradiente</label><div class="fila"><button class="btn pri" id="bDesc">▶ Reproducir</button><button class="btn" id="bRein">⟲ Reiniciar</button></div>
        <input type="range" id="sT" min="0" max="${T - 1}" value="0"><div class="lectura" id="lT"></div></div>
      <div class="bloque"><label class="t">Curva de nivel f = c</label><label class="chk"><input type="checkbox" id="cPlano"> mostrar plano z = c</label>
        <input type="range" id="sC" min="0" max="500" value="${vDe(c0)}"><div class="lectura" id="lC"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Aproximación de Taylor</label><select id="sel"><option value="-1">ninguna</option>${opts.map((p, i) => `<option value="${i}">${p.id} — ${p.clasificacion}</option>`).join("")}</select>
        <p class="nota" style="margin:8px 0 0">${mt("Superficie $f(P) + \\tfrac12 h^{T}H(P)\\,h$: paraboloide en un extremo, silla en un punto de silla.")}</p></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cTray" checked> trayectorias de descenso</label>
        <label class="chk"><input type="checkbox" id="cCurv" checked> curvas principales (autovectores)</label><label class="chk"><input type="checkbox" id="cSup" checked> superficie</label>
        <label class="chk"><input type="checkbox" id="cRec" checked> recortar la superficie a ${fmt(zLow, 3)} ≤ z ≤ ${fmt(zCap, 3)}</label></div>
    </div></div></div>`;
  const EPS = 0.012 * (zmax - zmin), up = a => a.map(v => dentro(v) ? v + EPS : null);
  const Zc = recorta(D.z);
  /* recorte limpio: fuera de [zLow, zCap] la superficie se aplana en el borde y se vuelve transparente */
  const Sb = D.z_rango || D.z, scV = Sb.flat().filter((v, k) => v !== null && Zc[Math.floor(k / D.x.length)][k % D.x.length] !== null);
  const scMin = Math.min(...scV), scMax = Math.max(...scV), SEN = scMin - 0.03 * ((scMax - scMin) || 1);
  const Zs = D.z.map(f => f.map(v => v === null ? null : Math.min(zCap, Math.max(zLow, v))));
  const Sc = Sb.map((f, i) => f.map((v, j) => Zc[i][j] === null ? SEN : v));
  const OPAC = [[0, 0], [0.02, 0], [0.03, 1], [1, 1]];
  const tr = [{type:"surface", x:D.x, y:D.y, z:Zs, surfacecolor:Sc, cmin:SEN, cmax:scMax, opacityscale:OPAC,
    colorscale:TERRA3D, opacity:1, showscale:false, name:"z = f", hoverinfo:"x+y+z",
    lighting:{ambient:0.78, diffuse:0.5, specular:0.06, roughness:0.95, fresnel:0.1}}];
  tr.push({type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.f),
    text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
    marker:{size:9, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"});
  tr[1].z = up(tr[1].z);
  const cx = [], cy = [], cz = [], nx = [], ny = [], nz = [];
  D.puntos.forEach(p => (p.curvas_principales || []).forEach(c => { const [a, b, d] = c.lam >= 0 ? [cx, cy, cz] : [nx, ny, nz];
    a.push(...c.x, null); b.push(...c.y, null); d.push(...up(c.z), null); }));
  const iCurv = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:cx, y:cy, z:cz, line:{color:LAM_POS, width:8}, name:"dirección con λ > 0 (sube)", hoverinfo:"skip"});
  tr.push({type:"scatter3d", mode:"lines", x:nx, y:ny, z:nz, line:{color:LAM_NEG, width:8}, name:"dirección con λ < 0 (baja)", hoverinfo:"skip"});
  const tx = [], ty = [], tz = [];
  bol.forEach(l => { tx.push(...l.x, null); ty.push(...l.y, null); tz.push(...up(l.z), null); });
  const iTray = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:tx, y:ty, z:tz, line:{color:OSCURO ? "rgba(240,225,210,.45)" : "rgba(60,35,25,.35)", width:2}, name:"trayectorias −∇f", hoverinfo:"skip"});
  const minimos = D.puntos.filter(p => p.clasificacion === "mínimo local");
  const colB = bol.map(l => l.destino === null ? "#ffffff" : CUENCAS[l.destino % CUENCAS.length]);
  const iBol = tr.length;
  tr.push({type:"scatter3d", mode:"markers", x:[], y:[], z:[], marker:{size:6, color:colB, line:{color:"#fff", width:1.5}}, name:"bolitas", hoverinfo:"skip"});
  const iPlano = tr.length;
  tr.push({type:"surface", x:[x0, x1], y:[y0, y1], z:[[c0, c0], [c0, c0]], colorscale:[[0, "#f0d3bd"], [1, "#f0d3bd"]], showscale:false,
    opacity:0.45, hoverinfo:"skip", name:"plano z = c", visible:false});
  const iNivel = tr.length;
  tr.push({type:"scatter3d", mode:"lines", x:[], y:[], z:[], line:{color:"#ffffff", width:7}, name:"curva de nivel f = c", hoverinfo:"skip"});
  const iTay = tr.length;
  opts.forEach(p => tr.push({type:"surface", x:p.taylor.x, y:p.taylor.y, z:p.taylor.z, visible:false, showscale:false, opacity:0.85,
    colorscale:[[0, LAM_NEG], [1, "#bcd2d8"]], name:"Taylor " + p.id, hoverinfo:"skip"}));
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:Object.assign(ejes3("f"), {range:[zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)]}),
           aspectmode:"manual", aspectratio:{x:1, y:1, z:0.75}, camera:{eye:{x:1.25, y:-1.3, z:1.2}}}}), CFG);
  $id("cRec").onchange = e => { Plotly.restyle(g3, e.target.checked ? {z:[Zs], surfacecolor:[Sc], cmin:[SEN], cmax:[scMax], opacityscale:[OPAC]} : {z:[D.z], surfacecolor:[Sb], cmin:[null], cmax:[null], opacityscale:[null]}, [0]);
    Plotly.relayout(g3, {"scene.zaxis.autorange": !e.target.checked, "scene.zaxis.range": e.target.checked ? [zmin - 0.04 * (zmax - zmin), zmax + 0.06 * (zmax - zmin)] : undefined}); };
  const pos = t => { const X = [], Y = [], Z = [], C = [];
    bol.forEach((l, j) => { let k = Math.min(t, l.x.length - 1); while (k > 0 && l.z[k] === null) k--;
      if (dentro(l.z[k])) { X.push(l.x[k]); Y.push(l.y[k]); Z.push(l.z[k] + 1.5 * EPS); C.push(colB[j]); } });
    return [X, Y, Z, C]; };
  const paso = t => { const [X, Y, Z, C] = pos(t); Plotly.restyle(g3, {x:[X], y:[Y], z:[Z], "marker.color":[C]}, [iBol]);
    const lleg = bol.filter(l => l.destino !== null && t >= l.x.length - 1).length, tot = bol.filter(l => l.destino !== null).length;
    $id("lT").innerHTML = `paso t = ${t} / ${T - 1}<br>bolitas: ${bol.length}<br>llegaron a un mínimo: ${lleg} / ${tot}` +
      (minimos.length ? "<br>" + minimos.map((m, i) => `<span style="color:${CUENCAS[i % CUENCAS.length]}">●</span> cuenca de ${m.id}`).join(" &nbsp;") : ""); };
  const parar = reproductor($id("bDesc"), $id("sT"), paso, 1); paso(0);
  $id("bRein").onclick = () => { parar(); $id("sT").value = 0; paso(0); };
  const nivel = v => { const c = cDe(v);
    const [lx, ly] = nivelSegs(D.x, D.y, Zc, c);
    Plotly.restyle(g3, {x:[[x0, x1], lx], y:[[y0, y1], ly], z:[[[c, c], [c, c]], lx.map(v => v === null ? null : c + EPS)]}, [iPlano, iNivel]);
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.003 * (zmax - zmin));
    $id("lC").innerHTML = `c = ${fmt(c, 6)}` + (t.length ? `<br><b>pasa por ${t.map(p => p.id + " (" + p.clasificacion + ")").join(", ")}</b>` : ""); };
  $id("sC").oninput = e => nivel(+e.target.value); nivel(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sC").value = vDe(p.f); nivel(vDe(p.f)); });
  $id("sel").onchange = e => { const k = +e.target.value; if (opts.length) Plotly.restyle(g3, {visible:opts.map((_, i) => i === k)}, opts.map((_, i) => iTay + i)); };
  $id("cPlano").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iPlano]);
  $id("cTray").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iTray]);
  $id("cCurv").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [iCurv, iCurv + 1]);
  $id("cSup").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [0]);
}

function g3dVolumen(P) {
  const [ex, ey, ez] = D.ejes, X = [], Y = [], Z = [];
  ex.forEach(a => ey.forEach(b => ez.forEach(c => { X.push(a); Y.push(b); Z.push(c); })));
  const val = D.valor.map(v => v === null ? NaN : v);
  const fin = D.valor.filter(v => v !== null).sort((a, b) => a - b), q = t => fin[Math.floor(t * (fin.length - 1))];
  const fc = D.puntos.map(p => p.f);
  let cmin = fc.length ? Math.min(...fc) : q(0.05), cmax = fc.length ? Math.max(...fc) : q(0.6);
  const sp = Math.max((cmax - cmin) * 0.8, (q(0.6) - q(0.02)) * 0.35, 1e-6);
  cmin = Math.max(q(0.005), cmin - sp); cmax = Math.min(q(0.9), cmax + sp);
  const cDe = v => cmin + (cmax - cmin) * v / 300, vDe = c => Math.round(300 * (c - cmin) / ((cmax - cmin) || 1));
  const c0 = D.puntos.length ? D.puntos[0].f + 0.02 * (cmax - cmin) : cDe(150);
  P.innerHTML = `<div class="card"><h2>Superficies de nivel f(${V.join(", ")}) = c</h2>
    <p class="sub">En tres variables la “gráfica” vive en ℝ⁴, así que se muestran las superficies de nivel. Barre c: cerca de un mínimo la superficie es una pequeña esfera que nace en el punto; al cruzar el valor de un punto de silla la superficie cambia de forma y en ese instante tiene un vértice cónico en el punto.</p>
    <div class="visor"><div id="g3" class="plot alto"></div><div class="ctrl">
      <div class="bloque"><label class="t">Nivel c</label><button class="btn pri" id="bIso">▶ Barrer c</button>
        <input type="range" id="sIso" min="0" max="300" value="${vDe(c0)}"><div class="lectura" id="lIso"></div><div class="fila" id="saltos" style="margin-top:8px"></div></div>
      <div class="bloque"><label class="t">Capas</label><label class="chk"><input type="checkbox" id="cPts" checked> puntos críticos</label></div>
    </div></div></div>`;
  const tr = [{type:"isosurface", x:X, y:Y, z:Z, value:val, isomin:c0, isomax:c0, surface:{count:1}, showscale:false, opacity:0.55,
      colorscale:[[0, COLOR.ac], [1, COLOR.ac]], caps:{x:{show:false}, y:{show:false}, z:{show:false}},
      lighting:{ambient:0.55, diffuse:0.8, specular:0.2}, name:"f = c", hoverinfo:"skip", showlegend:true},
    {type:"scatter3d", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), z:D.puntos.map(p => p.coords[2]),
      text:D.puntos.map(p => p.id), textposition:"top center", textfont:{color:COLOR.tx, size:13},
      marker:{size:8, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"}];
  const g3 = reg("g3d", $id("g3"));
  Plotly.newPlot(g3, tr, lay({margin:{l:0, r:0, t:10, b:0}, legend:{orientation:"h", y:0.02, x:0.02},
    scene:{xaxis:ejes3(V[0]), yaxis:ejes3(V[1]), zaxis:ejes3(V[2]), aspectmode:"cube", camera:{eye:{x:1.55, y:-1.45, z:1.0}}}}), CFG);
  const iso = v => { const c = cDe(v); Plotly.restyle(g3, {isomin:[c], isomax:[c]}, [0]);
    const t = D.puntos.filter(p => Math.abs(p.f - c) < 0.004 * (cmax - cmin));
    const bajo = D.puntos.filter(p => p.f < c).map(p => p.id);
    $id("lIso").innerHTML = `c = ${fmt(c, 6)}` + (t.length ? `<br><b>pasa por ${t.map(p => p.id + " (" + p.clasificacion + ")").join(", ")}</b>` : "") +
      (bajo.length ? `<br>encierra: ${bajo.join(", ")}` : ""); };
  reproductor($id("bIso"), $id("sIso"), iso, 2); iso(vDe(c0));
  $id("saltos").innerHTML = D.puntos.map((p, i) => `<button class="btn mini" data-i="${i}">c = f(${p.id})</button>`).join("");
  $id("saltos").querySelectorAll("button").forEach(b => b.onclick = () => { const p = D.puntos[+b.dataset.i]; $id("sIso").value = vDe(p.f); iso(vDe(p.f)); });
  $id("cPts").onchange = e => Plotly.restyle(g3, {visible:e.target.checked}, [1]);
}

/* ─────────── 4. Gráficos 2D ─────────── */
INIT.g2d = () => {
  const P = $id("tab-g2d");
  if (D.tipo === "sin_grafico") { P.innerHTML = `<div class="card"><h2>Sin gráfico</h2><p class="sub">Más de 3 variables.</p></div>`; return; }
  const leyenda = `<div class="leyenda"><span><i style="background:${COLOR.min}"></i>mínimo</span><span><i style="background:${COLOR.max}"></i>máximo</span><span><i style="background:${COLOR.silla}"></i>silla</span><span><i style="background:${COLOR.ind}"></i>indeterminado</span><span><i style="background:${COLOR.sing}"></i>no diferenciable</span></div>`;
  if (D.tipo === "1d") {
    P.innerHTML = `<div class="card"><h2>Gráfica de f</h2>${leyenda}<div id="g1" class="plot medio"></div></div>`;
    Plotly.newPlot(reg("g2d", $id("g1")), [{x:D.x, y:D.y, mode:"lines", line:{color:COLOR.ac, width:3}, name:"f"},
      {x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.f), mode:"markers+text", text:D.puntos.map(p => p.id), textposition:"top center",
       marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", name:"puntos críticos"}],
      lay({xaxis:{title:{text:V[0]}, gridcolor:COLOR.bd}, yaxis:{title:{text:"f"}, gridcolor:COLOR.bd}}), CFG);
    return;
  }
  if (D.tipo === "3d_volumen") {
    P.innerHTML = `<div class="card"><h2>Cortes planos de f</h2><p class="sub">Curvas de nivel de f en los tres planos que pasan por el punto elegido.</p>
      <div style="max-width:320px;margin-bottom:12px"><select id="selC">${D.puntos.map((p, i) => `<option value="${i}">${p.id} ${p.etiqueta} — ${p.clasificacion}</option>`).join("")}</select></div>
      <div class="grid2" id="cortes"></div></div>`;
    const divs = [0, 1, 2].map(() => { const d = document.createElement("div"); d.className = "plot medio"; $id("cortes").appendChild(d); return reg("g2d", d); });
    const dibuja = () => { const k = +$id("selC").value || 0, cs = D.cortes[Math.min(k, D.cortes.length - 1)];
      cs.forEach((c, n) => {
        const fl = c.z.flat().filter(v => v !== null).sort((u, w) => u - w), q = t => fl[Math.floor(t * (fl.length - 1))];
        const en = D.puntos.filter(p => Math.abs(p.coords[c.fijo] - c.valor_fijo) < 1e-9);
        Plotly.react(divs[n], [{type:"contour", x:c.A, y:c.B, z:c.z, colorscale:TERRA, zmin:q(0), zmax:q(0.75), ncontours:30,
            contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, colorbar:{thickness:12}},
          {type:"scatter", mode:"markers+text", x:en.map(p => p.coords[c.a]), y:en.map(p => p.coords[c.b]), text:en.map(p => p.id), textposition:"top right",
           textfont:{color:"#fff"}, marker:{size:13, color:en.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:en.map(hov), hoverinfo:"text"}],
          lay({showlegend:false, title:{text:`corte ${V[c.fijo]} = ${fmt(c.valor_fijo, 4)}`, font:{size:13}}, margin:{l:50, r:10, t:40, b:44},
               xaxis:{title:{text:V[c.a]}, gridcolor:COLOR.bd}, yaxis:{title:{text:V[c.b]}, gridcolor:COLOR.bd, scaleanchor:"x"}}), CFG); }); };
    $id("selC").onchange = dibuja; dibuja(); return;
  }
  P.innerHTML = `<div class="card"><h2>Curvas de nivel, flujo del gradiente y cuencas de atracción</h2>
    <p class="sub">Colores por cuantiles de f. Cada línea sigue −∇f y su color indica a qué mínimo cae. En cada punto: direcciones principales de H (ocre λ &gt; 0, petróleo λ &lt; 0). La línea blanca discontinua es la curva de nivel que pasa por cada punto crítico.</p>${leyenda}
    <div id="g2" class="plot"></div></div>
    <div class="card"><h2>Mapa del discriminante D(x, y)</h2><p class="sub">Dónde la superficie tiene forma de cuenco, de cúpula o de silla.</p>
    <div class="leyenda"><span><i style="background:#8fb3bd"></i>D &gt; 0, f<sub>xx</sub> &gt; 0 (cuenco ∪)</span><span><i style="background:#e0a58a"></i>D &gt; 0, f<sub>xx</sub> &lt; 0 (cúpula ∩)</span><span><i style="background:#c3a8bd"></i>D &lt; 0 (silla)</span><span><i style="background:#ddd3c8"></i>D = 0</span></div>
    <div id="g4" class="plot medio"></div></div>`;
  const cb = D.ticks_color ? {title:{text:"f"}, tickvals:D.ticks_color.vals, ticktext:D.ticks_color.text, thickness:14} : {title:{text:"f"}};
  const tr = [{type:"contour", x:D.x, y:D.y, z:D.z_rango || D.z, text:D.z, colorscale:TERRA, ncontours:36, colorbar:cb,
    contours:{coloring:"heatmap", showlines:true}, line:{width:0.4, color:"rgba(255,255,255,.3)"}, name:"f",
    hovertemplate:"x = %{x:.3f}<br>y = %{y:.3f}<br>f = %{text}<extra></extra>"}];
  const grupos = {};
  D.flujo.forEach(l => { const k = l.destino === null ? "x" : l.destino; (grupos[k] = grupos[k] || {x:[], y:[]}); grupos[k].x.push(...l.x, null); grupos[k].y.push(...l.y, null); });
  const minimos = D.puntos.filter(p => p.clasificacion === "mínimo local");
  Object.entries(grupos).forEach(([k, g]) => tr.push({type:"scatter", mode:"lines", x:g.x, y:g.y, hoverinfo:"skip",
    line:{width:1.3, color:k === "x" ? "rgba(255,245,235,.55)" : CUENCAS[k % CUENCAS.length]}, name:k === "x" ? "flujo −∇f (sin mínimo)" : `cuenca de ${minimos[k] ? minimos[k].id : k}`}));
  D.familias.forEach(f => tr.push({type:"scatter", mode:"lines", x:f.x, y:f.y, line:{color:COLOR.sing, width:5, dash:"dot"}, name:"familia crítica"}));
  [...new Set(D.niveles_criticos)].forEach((lv, i) => tr.push({type:"contour", x:D.x, y:D.y, z:D.z, showscale:false, hoverinfo:"skip",
    contours:{coloring:"none", start:lv, end:lv, size:1}, line:{color:"#fff", width:2, dash:"dash"}, name:"nivel f = f(P)", showlegend:i === 0}));
  D.puntos.forEach(p => (p.curvas_testigo || []).forEach(c => tr.push({type:"scatter", mode:"lines", x:c.x, y:c.y,
    line:{color:c.comportamiento === "sube" ? "#8fa06a" : c.comportamiento === "baja" ? "#e07a52" : COLOR.sing, width:4}, name:`curva de prueba (${c.comportamiento})`})));
  const L = (D.rango[0][1] - D.rango[0][0]) * 0.07;
  D.puntos.forEach(p => {
    (p.autovectores || []).forEach((v, j) => { const lam = p.autovalores[j];
      tr.push({type:"scatter", mode:"lines", x:[p.coords[0] - L * v[0], p.coords[0] + L * v[0]], y:[p.coords[1] - L * v[1], p.coords[1] + L * v[1]],
        line:{color:lam > 0 ? LAM_POS : lam < 0 ? LAM_NEG : "#bdb2a6", width:5}, hoverinfo:"text", text:`λ = ${fmt(lam, 4)}`, showlegend:false}); });
    tr.push({type:"scatter", mode:"markers+text", x:[p.coords[0]], y:[p.coords[1]], text:[p.id], textposition:"top right", textfont:{color:"#fff", size:13},
      marker:{size:15, color:colorPunto(p), line:{color:"#fff", width:2}}, hovertext:[hov(p)], hoverinfo:"text", showlegend:false});
  });
  Plotly.newPlot(reg("g2d", $id("g2")), tr, lay({xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain", gridcolor:COLOR.bd},
    yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain", gridcolor:COLOR.bd}}), CFG);
  const cs = [[0, "#c3a8bd"], [0.33, "#c3a8bd"], [0.33, "#ddd3c8"], [0.5, "#ddd3c8"], [0.5, "#8fb3bd"], [0.75, "#8fb3bd"], [0.75, "#e0a58a"], [1, "#e0a58a"]];
  Plotly.newPlot(reg("g2d", $id("g4")), [{type:"heatmap", x:D.x, y:D.y, z:D.clase_D, zmin:-1, zmax:2, colorscale:cs, showscale:false, hoverinfo:"skip"},
    {type:"contour", x:D.x, y:D.y, z:D.z, contours:{coloring:"none"}, line:{color:"rgba(43,36,32,.35)", width:1}, ncontours:18, showscale:false, hoverinfo:"skip", showlegend:false},
    {type:"scatter", mode:"markers+text", x:D.puntos.map(p => p.coords[0]), y:D.puntos.map(p => p.coords[1]), text:D.puntos.map(p => p.id), textposition:"top right",
     marker:{size:13, color:D.puntos.map(colorPunto), line:{color:"#fff", width:2}}, hovertext:D.puntos.map(hov), hoverinfo:"text", showlegend:false}],
    lay({showlegend:false, xaxis:{title:{text:V[0]}, range:D.rango[0], constrain:"domain"}, yaxis:{title:{text:V[1]}, range:D.rango[1], scaleanchor:"x", constrain:"domain"}}), CFG);
};
"""


def exportar_html(P: ProblemaHessiana, ruta: str, datos: dict | None = None, offline: bool = False) -> str:
    """Página web autocontenida: resumen, procedimiento en LaTeX, 3D dinámico, 2D y JSON."""
    D = datos or datos_grafico(P)
    html = _pagina(a_dict(P), D, titulo="Puntos críticos y matriz Hessiana",
                   eyebrow="Optimización libre · Cálculo exacto con SymPy",
                   funcion="resolver_hessiana()", nombre_json="hessiana_resultado.json", js_modulo=_JS_HESSIANA,
                   pie="Generado por metodos_hessiana.py · Grupo 06 · Frenet, Lagrange y Puntos Críticos", offline=offline)
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(html)
    return ruta


# ════════════════════════════════════════════════════════════════════════════
# 14. Reporte de terminal
# ════════════════════════════════════════════════════════════════════════════
def _pp(e, ascii_=False):
    return sp.pretty(e, use_unicode=not ascii_)


def _bloque(texto, sangria="      "):
    return sangria + texto.replace("\n", "\n" + sangria)


def reporte_texto(P: ProblemaHessiana, ascii_: bool = False, detalle: bool = True) -> str:
    L = "=" * 78
    vs = ", ".join(map(str, P.variables))
    s = [L, " PUNTOS CRÍTICOS Y MATRIZ HESSIANA (optimización libre)", L,
         f"f({vs}) = {P.f}", ""]
    s += ["1) Gradiente ∇f :"]
    for v, g in zip(P.variables, P.gradiente):
        s.append(_bloque(_pp(sp.Eq(sp.Symbol(f"∂f/∂{v}"), g), ascii_), "   "))
    s += ["", "2) Sistema ∇f = 0 (forma que se resolvió):"]
    for e in P.ecuaciones:
        s.append(_bloque(_pp(sp.Eq(e, 0), ascii_), "   "))
    if P.factores_descartados:
        s.append(f"   (se eliminaron factores que nunca se anulan: {', '.join(P.factores_descartados)})")
    s += [f"   Método: {P.metodo}"]
    if detalle and P.base_groebner:
        s.append("   Base de Gröbner (lex): " + " ; ".join(map(str, P.base_groebner)))
    s += ["", "3) Matriz Hessiana:", _pp(P.hessiana_general, ascii_)]
    if P.D_general is not None:
        s += ["   D(x, y) = f_xx·f_yy − (f_xy)² =", _bloque(_pp(P.D_general, ascii_), "   ")]

    todos = P.puntos + P.no_diferenciables
    s += ["", f"4) Puntos críticos: {len(todos)}" + (f"  (+ {len(P.familias)} familia(s))" if P.familias else ""),
          "-" * 78]
    for i, p in enumerate(todos, 1):
        s += _reporte_punto(P, p, f"P{i}", ascii_, detalle)
    for fa in P.familias:
        par = ", ".join(f"{v} = {fa['expr'][v]}" for v in P.variables)
        s.append(f"[FAMILIA]  {par}   (parámetros libres: {', '.join(map(str, fa['parametros']))})")
        if fa.get("representante") is not None:
            s += _reporte_punto(P, fa["representante"], "   representante", ascii_, detalle)
    G = P.analisis_global
    s += ["5) Análisis global:"]
    for j in G["justificacion"]:
        s.append(f"   • {j}")
    if G.get("minimo_global") is not None:
        s.append(f"   ⇒ MÍNIMO GLOBAL = {G['minimo_global']}")
    if G.get("maximo_global") is not None:
        s.append(f"   ⇒ MÁXIMO GLOBAL = {G['maximo_global']}")
    s.append(f"   (certeza: {G['certeza']})")
    for a in P.advertencias:
        s.append(f"⚠ {a}")
    s.append(L)
    return "\n".join(s)


def _reporte_punto(P, p, nombre, ascii_, detalle):
    vs = P.variables
    c = ", ".join(f"{v} = {p.coords[v]}" for v in vs)
    cn = ", ".join(f"{_num(p.coords[v]):.6g}" for v in vs)
    s = [f"[{nombre}]  {c}      (≈ {cn})" + ("   ← NO DIFERENCIABLE" if p.tipo == "no diferenciable" else "")]
    s.append(f"      f = {p.valor_f}   (≈ {_num(p.valor_f):.6g})" +
             ("   ∇f = 0 verificado ✔" if p.verificado else ""))
    if detalle and p.hessiana is not None:
        s += ["      H en el punto:", _bloque(_pp(p.hessiana, ascii_))]
    if p.D is not None:
        s.append(f"      D = {p.D},  f_xx = {p.fxx}")
    elif p.menores:
        s.append("      menores: " + ", ".join(f"Δ{k} = {v}" for k, v, _ in p.menores))
    if p.autovalores:
        s.append("      autovalores: " + ", ".join(
            (str(a["exacto"]) if a["exacto"] is not None else f"≈{a['num']:.5g}") +
            (f" (×{a['mult']})" if a["mult"] > 1 else "") for a in p.autovalores))
    if p.clasif_segundo_orden and p.clasif_segundo_orden != p.clasificacion:
        s.append(f"      Criterio de 2º orden: {p.clasif_segundo_orden.upper()}")
    for paso in p.orden_superior.get("pasos", []):
        s.append(f"        → {_s(paso)}")
    s.append(f"      ⇒ {p.clasificacion.upper()}   [{p.certeza}; {p.criterio}]")
    va = p.verif_autovalores
    if va and va.get("clasificacion") != DUDOSO and p.clasif_segundo_orden != DUDOSO:
        s.append(f"      Verificación por autovalores: {'coincide ✔' if va['coincide'] else 'DIFIERE ✘'}")
    if p.certificado:
        s.append(f"      Certificado: {p.certificado[2:]}")
    if p.global_:
        s.append(f"      Global: {p.global_.upper()}")
    s.append("")
    return s


# ════════════════════════════════════════════════════════════════════════════
# 15. Ejemplos y CLI
# ════════════════════════════════════════════════════════════════════════════
DEMOS = {
    1: ("x^4 + y^4 - 4x*y + 1", None, "Dos mínimos globales y una silla; f es coerciva (mínimo global demostrado)."),
    2: ("x*y*exp(-(x^2 + y^2)/2)", None, "No polinómica: 2 máximos, 2 mínimos y 1 silla (se elimina el factor e^u)."),
    3: ("(y - x^2)*(y - 2x^2)", None, "Contraejemplo de Peano: D = 0 y es mínimo sobre TODA recta, pero es silla (curvas de prueba)."),
    4: ("x^4 + y^4", None, "D = 0: Taylor de orden 4 definida positiva → mínimo estricto (y global certificado)."),
    5: ("x^3 - 3x*y^2", None, "Silla de mono: D = 0 y el primer término de Taylor es de orden 3 (impar)."),
    6: ("x^2 + y^2 + z^2 - 2x*y*z", None, "3 variables: 1 mínimo y 4 sillas (Sylvester, autovalores e isosuperficies)."),
    7: ("sqrt(x^2 + y^2)", None, "Cono: el mínimo está en un punto donde ∇f NO existe."),
    8: ("(x - y)^2 + 1", None, "Familia de puntos críticos: toda la recta y = x (mínimo no estricto)."),
}


def _con_sufijo(ruta, suf):
    if not suf:
        return ruta
    base, _, ext = ruta.rpartition(".")
    return f"{base}{suf}.{ext}" if base else ruta + suf


def _ejecutar(f, vs, args, suf=""):
    P = resolver(f, vs, metodo=args.metodo)
    print(reporte_texto(P, ascii_=args.ascii, detalle=not args.breve))
    datos = None
    if args.png or args.html or args.datos:
        datos = datos_grafico(P, rango=args.rango)
    if args.png:
        if datos["tipo"] == "sin_grafico":
            print("(Sin PNG: más de 3 variables.)")
        else:
            print("PNG guardado en:", graficar_png(P, _con_sufijo(args.png, suf), datos))
    if args.html:
        print("HTML guardado en:", exportar_html(P, _con_sufijo(args.html, suf), datos, offline=args.offline))
    if args.json or args.datos:
        out = a_dict(P)
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


def main(argv: Sequence[str] | None = None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(
        description="Puntos críticos y clasificación por la matriz Hessiana (SymPy exacto).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Ejemplos:\n"
               '  python metodos_hessiana.py -f "x^3 + y^3 - 3xy" --png out.png --html out.html\n'
               '  python metodos_hessiana.py -f "x^2 + 3y^2 + z^2 - 2xz" --json -\n'
               "  python metodos_hessiana.py --demo 3 --html peano.html\n"
               "  python metodos_hessiana.py --demo 0 --png demo.png")
    ap.add_argument("-f", "--funcion", help='función, p. ej. "x^3 + y^3 - 3xy"')
    ap.add_argument("-v", "--vars", nargs="+", help="orden de las variables (por defecto alfabético)")
    ap.add_argument("--metodo", default="auto", choices=["auto", "groebner", "solve", "nonlinsolve"])
    ap.add_argument("--png", help="guardar imagen PNG")
    ap.add_argument("--html", help="guardar HTML interactivo")
    ap.add_argument("--json", help="guardar resultado en JSON ('-' = pantalla)")
    ap.add_argument("--datos", help="como --json pero con los arreglos para graficar")
    ap.add_argument("--rango", nargs=2, type=float, action="append", metavar=("MIN", "MAX"),
                    help="rango por eje (repetir una vez por variable)")
    ap.add_argument("--demo", type=int, help=f"ejecutar ejemplo 1..{len(DEMOS)} (0 = todos)")
    ap.add_argument("--ascii", action="store_true", help="fórmulas sin Unicode")
    ap.add_argument("--breve", action="store_true", help="omite las matrices por punto")
    ap.add_argument("--offline", action="store_true",
                    help="incrusta Plotly.js en el HTML (funciona sin internet; requiere  pip install plotly)")
    args = ap.parse_args(argv)

    if args.demo is not None:
        ids = list(DEMOS) if args.demo == 0 else [args.demo]
        for i in ids:
            f, vs, desc = DEMOS[i]
            print(f"\n### DEMO {i}: {desc}")
            _ejecutar(f, vs, args, suf=f"_demo{i}" if len(ids) > 1 else "")
        return
    if not args.funcion:
        ap.error('indica -f "FUNCION" (o usa --demo).')
    try:
        _ejecutar(args.funcion, args.vars, args)
    except (ValueError, RuntimeError, sp.SympifyError, SyntaxError, TypeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
