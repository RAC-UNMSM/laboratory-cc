"""
methods/metodo_lagrange.py — Multiplicadores de Lagrange y optimización condicionada.

Solo contiene MATEMÁTICA: recibe texto, devuelve objetos SymPy (``resolver``) o un dict
serializable (``a_dict`` / ``resolver_lagrange``). No dibuja ni genera HTML: los gráficos
viven en ``core/visualizacion.py`` y los reportes en ``core/reporte.py``.

Pasos del método:
  1. Lagrangiana  L(x, λ) = f(x) − Σ λ_i g_i(x)
  2. Sistema ∇_x L = 0, g_i = 0  (Gröbner lex si es polinómico; solve/nonlinsolve si no)
  3. Hessiano orlado y clasificación por los últimos (n − m) menores principales orlados
  4. Verificación independiente: Hessiano de L restringido al espacio tangente
  5. Puntos singulares de la restricción (∇g_i dependientes), donde Lagrange no aplica
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
import sympy as sp

from core.utils_math import (
    algebraico as _algebraico,
    es_real as _es_real,
    limpiar as _limpiar,
    num as _num,
    parsear_seguro,
    resolver_sistema as _resolver_sistema,
    signo,
    sust_latex as _sust_latex,
)

__all__ = ["resolver", "a_dict", "resolver_lagrange", "ProblemaLagrange", "PuntoCritico", "DEMOS",
           "MAX_LOCAL", "MIN_LOCAL", "SILLA", "NO_CONCLUYENTE", "AISLADO"]

TOL = 1e-10

# Nombres de clasificación (constantes que comparan verificador.py, visualizacion.py y server.py)
MAX_LOCAL = "máximo local condicionado"
MIN_LOCAL = "mínimo local condicionado"
SILLA = "punto de silla condicionado (no es extremo)"
NO_CONCLUYENTE = "no concluyente (criterio de 2º orden degenerado)"
AISLADO = "punto aislado (m = n: la restricción no deja grados de libertad)"


def _signo(v) -> int:
    return signo(v, tol=1e-12)


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
# 2. Entrada
# ════════════════════════════════════════════════════════════════════════════
def _parse(texto: str) -> sp.Expr:
    return parsear_seguro(texto)


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
# 3. Resolución del sistema de Lagrange
# ════════════════════════════════════════════════════════════════════════════
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
# 4. Motor principal
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
# 5. Serialización a JSON (formato MCP)
# ════════════════════════════════════════════════════════════════════════════
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
    """Atajo: resuelve y devuelve el dict JSON (opcionalmente con los datos para graficar)."""
    P = resolver(f, restricciones, variables, metodo)
    out = a_dict(P)
    if incluir_grafico:
        from core.visualizacion import datos_lagrange   # import diferido: evita ciclos
        out["grafico"] = datos_lagrange(P, rango=rango)
    return out


# ════════════════════════════════════════════════════════════════════════════
# 6. Ejemplos
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
