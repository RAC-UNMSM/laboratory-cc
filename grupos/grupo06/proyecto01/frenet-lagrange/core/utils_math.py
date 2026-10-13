"""
core/utils_math.py — Lógica matemática compartida por los tres métodos.

Contiene lo que antes estaba duplicado en metodos_lagrange.py, metodos_hessiana.py y
metodos_frenet.py:

* ``parsear_seguro``: convierte texto en expresiones SymPy SIN ejecutar código arbitrario
  (``parse_expr`` usa ``eval`` por dentro; aquí se restringe a una lista blanca de funciones
  matemáticas y se bloquean ``__builtins__``, atributos y palabras peligrosas).
* Utilidades exacto/numérico: ``num``, ``signo``, ``es_real``, ``finito``, ``limpiar``,
  ``algebraico`` (números algebraicos exactos con CRootOf), ``es_cero`` (test de identidad).
* ``resolver_sistema``: Gröbner lex → raíces exactas → solve → nonlinsolve.
* Formateo: ``texto`` (x**2 → x^2), ``sust_latex`` (sustitución sin evaluar), ``vlat``.

Todo es determinista y sin efectos secundarios (no imprime nada: el servidor MCP usa STDIO).
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Iterable

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_application,
    implicit_multiplication,
    split_symbols_custom,
    parse_expr,
    standard_transformations,
)

__all__ = [
    "ErrorEntrada", "parsear_seguro", "parsear_tupla", "complejo", "es_real", "finito", "limpiar",
    "num", "signo", "algebraico", "resolver_triangular", "resolver_sistema", "simplificar", "es_cero",
    "texto", "sust_latex", "vlat", "vnum", "json_seguro", "FUNCIONES_PERMITIDAS",
]


class ErrorEntrada(ValueError):
    """La expresión no es válida (sintaxis, símbolos prohibidos, etc.)."""


# ════════════════════════════════════════════════════════════════════════════
# Parser seguro
# ════════════════════════════════════════════════════════════════════════════
_GRIEGAS = {"alpha", "beta", "gamma", "delta", "epsilon", "theta", "phi", "psi", "omega", "rho", "sigma", "mu",
            "nu", "tau", "kappa", "eta", "xi", "zeta", "chi"}


def _partir(nombre: str) -> bool:
    """'xy' → x*y, '3xyz' → 3*x*y*z (lo natural al escribir a mano). No se parten nombres con dígitos
    o guion bajo (x1, lambda_1), letras griegas ni funciones."""
    return nombre.isalpha() and len(nombre) > 1 and nombre not in _GRIEGAS and nombre not in FUNCIONES_PERMITIDAS


_TRANSF = standard_transformations + (split_symbols_custom(_partir), implicit_multiplication,
                                      implicit_application, convert_xor)

#: Funciones y constantes que un usuario (o un LLM) puede escribir.
FUNCIONES_PERMITIDAS: dict[str, Any] = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "cot": sp.cot, "sec": sp.sec, "csc": sp.csc,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "atan2": sp.atan2, "acot": sp.acot,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh, "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt, "cbrt": sp.cbrt, "root": sp.root,
    "Abs": sp.Abs, "abs": sp.Abs, "sign": sp.sign, "floor": sp.floor, "ceiling": sp.ceiling,
    "pi": sp.pi, "E": sp.E, "e": sp.E, "oo": sp.oo,   # 'e^t' = exp(t): la e minúscula es el número de Euler
}
# nombres que necesitan las transformaciones de parse_expr internamente
_INTERNOS: dict[str, Any] = {"Symbol": sp.Symbol, "Integer": sp.Integer, "Float": sp.Float,
                             "Rational": sp.Rational, "Function": sp.Function}
_GLOBALES_SEGUROS: dict[str, Any] = {"__builtins__": {}, **FUNCIONES_PERMITIDAS, **_INTERNOS}

_CARACTERES_OK = re.compile(r"^[A-Za-z0-9_+\-*/^().,=\s<>]*$")
_PROHIBIDO = re.compile(r"(__|\bimport\b|\blambda\b|\bexec\b|\beval\b|\bopen\b|\bglobals\b|\blocals\b|"
                        r"\bgetattr\b|\bsetattr\b|\bcompile\b|\bos\b|\bsys\b|\bsubprocess\b)")
_MAX_LONGITUD = 400


_UNICODE = {"²": "^2", "³": "^3", "⁴": "^4", "⁵": "^5", "⁻¹": "^(-1)", "·": "*", "×": "*", "÷": "/",
            "−": "-", "–": "-", "π": "pi", "√": "sqrt", "θ": "theta", "φ": "phi"}


def normalizar_unicode(t: str) -> str:
    """Convierte la notación 'bonita' que suelen escribir personas y LLMs (x², 2·y, π, √) a texto plano."""
    for a, b in _UNICODE.items():
        t = t.replace(a, b)
    return t


_RE_FUNC_PEGADA = None


def _separar_funciones(t: str) -> str:
    """'sinx' → 'sin x', 'cost' → 'cos t' (función pegada a una variable de 1–2 letras)."""
    global _RE_FUNC_PEGADA
    if _RE_FUNC_PEGADA is None:
        nombres = sorted((k for k in FUNCIONES_PERMITIDAS if k.isalpha() and len(k) > 1 and k not in ("pi", "oo")),
                         key=len, reverse=True)
        _RE_FUNC_PEGADA = re.compile(r"\b(" + "|".join(nombres) + r")([a-zA-Z]{1,2})\b")
    return _RE_FUNC_PEGADA.sub(lambda m: m.group(0) if m.group(0) in FUNCIONES_PERMITIDAS
                               else f"{m.group(1)} {m.group(2)}", t)


def _validar_texto(t: str) -> str:
    t = _separar_funciones(normalizar_unicode(str(t)).strip())
    if not t:
        raise ErrorEntrada("Expresión vacía.")
    if len(t) > _MAX_LONGITUD:
        raise ErrorEntrada(f"Expresión demasiado larga (máximo {_MAX_LONGITUD} caracteres).")
    if not _CARACTERES_OK.match(t):
        malos = sorted({c for c in t if not _CARACTERES_OK.match(c)})
        raise ErrorEntrada(f"Caracteres no permitidos: {' '.join(malos)}. Usa solo letras, números, "
                           "+ - * / ^ ( ) , y funciones como sin, cos, exp, log, sqrt.")
    if _PROHIBIDO.search(t):
        raise ErrorEntrada("La expresión contiene palabras reservadas no permitidas.")
    if re.search(r"\.\s*[A-Za-z_]", t):
        raise ErrorEntrada("No se permite acceder a atributos con '.' (usa 0.5 para decimales).")
    return t


def parsear_seguro(texto: str | sp.Basic) -> sp.Expr:
    """Texto → expresión SymPy, de forma segura. Acepta '^' como potencia y '2x' como 2*x."""
    if isinstance(texto, sp.Basic):
        return sp.sympify(texto)
    t = _validar_texto(texto)
    try:
        e = parse_expr(t, local_dict={}, global_dict=dict(_GLOBALES_SEGUROS), transformations=_TRANSF,
                       evaluate=True)
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de parseo es un error de entrada
        raise ErrorEntrada(f"No se pudo interpretar '{t}': revisa paréntesis y operadores.") from exc
    if not isinstance(e, (sp.Basic, tuple)):
        raise ErrorEntrada(f"'{t}' no es una expresión matemática.")
    return e


def parsear_tupla(texto: str) -> list[sp.Expr]:
    """'cos t, sin t, t' → [cos(t), sin(t), t]  (también acepta '(...)' o '<...>')."""
    t = _validar_texto(texto)
    if "=" in t:
        t = t.split("=", 1)[1].strip()
    while t and t[0] in "(<[" and t[-1] in ")>]":
        t = t[1:-1].strip()
    t = t.replace("<", "").replace(">", "")
    e = parsear_seguro("(" + t + ",)")
    return list(e)


# ════════════════════════════════════════════════════════════════════════════
# Exacto / numérico
# ════════════════════════════════════════════════════════════════════════════
def complejo(v) -> complex | None:
    try:
        return complex(sp.N(v, 30))
    except (TypeError, ValueError):
        return None


def es_real(v) -> bool:
    r = getattr(v, "is_real", None)
    if r is True:
        return True
    if r is False:
        return False
    c = complejo(v)
    return c is not None and abs(c.imag) <= 1e-12 * (1 + abs(c.real))


def finito(v) -> bool:
    return not (v.has(sp.zoo, sp.oo, -sp.oo, sp.nan)) and es_real(v)


def num(v) -> float | None:
    """Valor real aproximado (None si no es real o no es finito)."""
    c = complejo(v)
    if c is None or not math.isfinite(c.real):
        return None
    if abs(c.imag) > 1e-9 * (1 + abs(c.real)):
        return None
    return float(c.real)


def signo(v, tol: float = 1e-25) -> int:
    """Signo exacto cuando SymPy lo puede decidir; si no, con 30 dígitos."""
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
    c = complejo(v)
    if c is None or abs(c.real) < tol:
        return 0
    return 1 if c.real > 0 else -1


def algebraico(e):
    """Expresa un número algebraico real como raíz exacta (CRootOf) de su polinomio mínimo."""
    try:
        e = sp.nsimplify(e) if e.is_Float else e
        if e.is_Rational:
            return e
        X = sp.Dummy("X")
        mp = sp.minimal_polynomial(e, X, polys=True)
        cand = sp.solve(mp.as_expr(), X) if mp.degree() <= 2 else mp.real_roots()
        val = complex(sp.N(e, 30))
        return min(cand, key=lambda r: abs(complex(sp.N(r, 30)) - val))
    except Exception:  # noqa: BLE001
        return e


def limpiar(v):
    """Simplifica; si es real pero aparece 'I' (Cardano), intenta quitarla; si hay CRootOf, la compacta."""
    if isinstance(v, sp.Basic) and v.has(sp.CRootOf):
        return algebraico(v)
    v = sp.nsimplify(v, rational=False) if getattr(v, "is_Float", False) else v
    try:
        v = sp.simplify(v)
    except Exception:  # noqa: BLE001
        pass
    if v.has(sp.I) and es_real(v):
        w = sp.simplify(sp.re(sp.expand_complex(v)))
        if not w.has(sp.I) and not w.has(sp.re):
            v = w
    return v


_TRIG = (sp.sin, sp.cos, sp.tan, sp.sinh, sp.cosh, sp.tanh, sp.exp)


def simplificar(e, max_ops: int = 350):
    """trigsimp + simplify cuando la expresión no es enorme (evita bloqueos con expresiones grandes)."""
    e = sp.sympify(e)
    try:
        if e.has(*_TRIG):
            e = sp.trigsimp(e)
        if sp.count_ops(e) <= max_ops:
            e2 = sp.simplify(e)
            if sp.count_ops(e2) <= sp.count_ops(e):
                e = e2
        else:
            e = sp.cancel(e)
    except Exception:  # noqa: BLE001
        pass
    return e


_MUESTRAS_T = ("0.3719", "1.1287", "2.7043", "-0.8311", "1.9377", "-2.4103")
_DESFASE = ("0", "0.5813", "-0.9431", "1.3127", "-0.2671", "0.7759")


def es_cero(e) -> bool:
    """¿e ≡ 0?  Test de identidad por evaluación (30 dígitos en 6 puntos): si alguno da ≠ 0 la
    respuesta 'no' es segura; si todos dan 0 se confirma con simplificación simbólica."""
    e = sp.sympify(e)
    if e == 0:
        return True
    libres = sorted(e.free_symbols, key=str)
    if libres:
        concluyente = 0
        for k, tv in enumerate(_MUESTRAS_T):
            # cada símbolo recibe un valor DISTINTO (si no, x - y daría 0 en todos los puntos)
            sub = {x: (sp.Float(tv, 30) + sp.Float(_DESFASE[j % len(_DESFASE)], 30)) if x.is_positive is not True
                   else sp.Float(str(1.37 + 0.61 * j + 0.13 * k), 30)
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
            try:
                z = simplificar(e)
                if z == 0 or z.is_zero:
                    return True
            except Exception:  # noqa: BLE001
                pass
            return True
    try:
        z = simplificar(e)
        return bool(z == 0 or z.is_zero)
    except Exception:  # noqa: BLE001
        return False


# ════════════════════════════════════════════════════════════════════════════
# Sistemas de ecuaciones
# ════════════════════════════════════════════════════════════════════════════
def resolver_triangular(base: list, incognitas: list) -> list[dict] | None:
    """Base de Gröbner lex en 'posición normal' (x_i = p_i(t), q(t) = 0): raíces reales EXACTAS
    de q (CRootOf) y sustitución hacia atrás. Evita que solve() se atasque con Cardano/Ferrari."""
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
        s = {t: algebraico(r)}
        for v, ex in despeje.items():
            s[v] = algebraico(sp.expand(ex.subs(t, r)))
        sols.append(s)
    return sols


def resolver_sistema(ecs: list, incognitas: list, metodo: str = "auto") -> tuple[list[dict], str, list | None]:
    """Resuelve un sistema exacto. Devuelve (soluciones, nombre_del_método, base_groebner|None).
    metodo ∈ {"auto", "groebner", "solve", "nonlinsolve"}."""
    es_poli = all(sp.together(e).as_numer_denom()[1].is_number and e.is_polynomial(*incognitas) for e in ecs)
    if metodo in ("auto", "groebner") and es_poli:
        try:
            G = sp.groebner(ecs, *incognitas, order="lex")
            base = list(G.exprs)
            if base == [1]:
                return [], "groebner (sistema inconsistente: base = {1})", base
            ult = [e for e in base if e.free_symbols <= {incognitas[-1]}]
            if ult and max((sp.Poly(fa, incognitas[-1]).degree() for fa, _ in sp.factor_list(ult[0])[1]),
                           default=0) >= 3:
                tri = resolver_triangular(base, incognitas)
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
    if isinstance(res, sp.ConditionSet) or not isinstance(res, sp.FiniteSet):
        raise RuntimeError("SymPy no pudo resolver el sistema en forma cerrada "
                           f"(nonlinsolve devolvió {type(res).__name__}).")
    return ([{x: v for x, v in zip(incognitas, tup) if v != x} for tup in res], "sympy.nonlinsolve", None)


# ════════════════════════════════════════════════════════════════════════════
# Formateo
# ════════════════════════════════════════════════════════════════════════════
def texto(e) -> str:
    """Texto legible: x**2 → x^2."""
    return str(e).replace("**", "^")


def sust_latex(expr, coords: dict) -> str:
    """LaTeX de expr con los valores sustituidos SIN evaluar: f(2, −1) = 2·(−1)^2 …"""
    rep = {}
    for i, (v, val) in enumerate(coords.items()):
        t = sp.latex(val)
        simple = (val.is_Integer and val >= 0) or val.is_Symbol
        # el prefijo "{}" (invisible en LaTeX) hace únicos los símbolos: 2·2 no se colapsa en 2²
        rep[v] = sp.Symbol("{}" * (i + 1) + (t if simple else r"\left(" + t + r"\right)"))
    try:
        return sp.latex(expr.xreplace(rep), mul_symbol="dot")
    except Exception:  # noqa: BLE001
        return sp.latex(expr)


def vlat(v: Iterable) -> str:
    return r"\left(" + ",\\ ".join(sp.latex(c) for c in v) + r"\right)"


def vnum(v: Iterable) -> list[float | None]:
    return [num(c) for c in v]


def json_seguro(obj: Any) -> str:
    """JSON listo para incrustar dentro de <script> (sin NaN y sin cerrar la etiqueta)."""
    return json.dumps(obj, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
