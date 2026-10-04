"""
methods/metodo_hessiana.py — Puntos críticos y optimización libre (matriz Hessiana).

Solo contiene MATEMÁTICA (sin gráficos ni HTML):
  1. Gradiente simbólico y sistema ∇f = 0 resuelto de forma exacta (se eliminan factores que
     nunca se anulan; Gröbner si es polinómico) y VERIFICADO sustituyendo en ∇f.
  2. Hessiana y discriminante D = f_xx f_yy − f_xy² (n = 2), Sylvester + autovalores (n ≥ 3).
  3. Casos dudosos (D = 0): Taylor de orden superior, certificado exacto de signo,
     curvas de prueba exactas y sondeo numérico de 40 dígitos.
  4. Puntos no diferenciables, familias de puntos críticos y análisis global (coercividad).
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp

from core.utils_math import (
    algebraico as _algebraico,
    es_real as _es_real,
    finito as _finito,
    limpiar as _limpiar,
    num as _num,
    parsear_seguro,
    resolver_sistema as _resolver_sistema,
    signo as _signo,
    sust_latex as _sust_latex,
    texto as _s,
)

__all__ = ["resolver", "a_dict", "resolver_hessiana", "ProblemaHessiana", "PuntoCritico", "DEMOS",
           "MIN_LOCAL", "MAX_LOCAL", "SILLA", "DUDOSO", "INDETERMINADO", "DEMOSTRADO", "NUMERICO"]

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
    return parsear_seguro(texto)


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


def _clave(coords, vars_):
    return tuple(round(_num(coords[v]) or 0.0, 9) for v in vars_)


# ════════════════════════════════════════════════════════════════════════════
# 3. Resolución de ∇f = 0
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


# ════════════════════════════════════════════════════════════════════════════
# 4. Criterio de segundo orden
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
# 5. Análisis de orden superior (casos dudosos)
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
# 6. Puntos no diferenciables
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
# 7. Análisis global
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
# 8. Motor principal
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
# 9. Serialización JSON (formato MCP)
# ════════════════════════════════════════════════════════════════════════════
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
    """Atajo: resuelve y devuelve el dict JSON (opcionalmente con los datos para graficar)."""
    P = resolver(f, variables, metodo)
    out = a_dict(P)
    if incluir_grafico:
        from core.visualizacion import datos_hessiana   # import diferido: evita ciclos
        out["grafico"] = datos_hessiana(P, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 10. Ejemplos
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
