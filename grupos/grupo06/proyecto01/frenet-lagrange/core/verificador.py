"""
core/verificador.py — CAPA 2 de validación: sentido matemático.

La capa 1 (``validacion.py``) garantiza que la petición está bien FORMADA. Esta capa
comprueba, de forma rápida y antes del cálculo pesado, que el problema tenga SENTIDO:

* Lagrange: f depende de las variables, ninguna restricción es constante o imposible
  (p. ej. '1 = 2'), m ≤ n, sin divisiones por cero, ∇g no idénticamente nulo, tamaño razonable.
* Hessiana: f no constante, Hessiana cuadrada y simétrica (Schwarz), sin divisiones por cero,
  aviso de puntos no diferenciables (|x|, √).
* Frenet: la curva depende del parámetro, r' ≢ 0, curvatura no idénticamente cero (si no, es
  una recta y el triedro NO existe), t0 en el dominio, r'(t0) ≠ 0 y κ(t0) ≠ 0.

Si algo falla se lanza ``ErrorVerificacion`` con un código, un mensaje y una sugerencia,
pensados para que el LLM se los explique al usuario. Lo no fatal se devuelve como aviso.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from core.utils_math import ErrorEntrada, es_cero, num, parsear_seguro, parsear_tupla
from core.validacion import SolicitudFrenet, SolicitudHessiana, SolicitudLagrange

__all__ = ["ErrorVerificacion", "InformeVerificacion", "verificar_lagrange", "verificar_hessiana",
           "verificar_frenet", "verificar"]

MAX_VARIABLES = 6
MAX_GRADO_BEZOUT = 400          # producto de grados (cota de Bézout del n.º de soluciones)


class ErrorVerificacion(ValueError):
    """El problema no tiene sentido matemático tal como está planteado."""

    def __init__(self, codigo: str, mensaje: str, sugerencia: str = "") -> None:
        super().__init__(mensaje)
        self.codigo, self.mensaje, self.sugerencia = codigo, mensaje, sugerencia

    def como_dict(self) -> dict[str, str]:
        return {"tipo": "verificacion", "codigo": self.codigo, "mensaje": self.mensaje, "sugerencia": self.sugerencia}

    def __str__(self) -> str:
        return f"[{self.codigo}] {self.mensaje}" + (f" Sugerencia: {self.sugerencia}" if self.sugerencia else "")


@dataclass
class InformeVerificacion:
    """Resultado de una verificación superada: avisos no fatales y datos útiles."""
    avisos: list[str] = field(default_factory=list)
    datos: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {"superada": True, "avisos": self.avisos, **self.datos}


# ════════════════════════════════════════════════════════════════════════════
# Utilidades
# ════════════════════════════════════════════════════════════════════════════
def _expr(texto: str, campo: str) -> sp.Expr:
    try:
        return parsear_seguro(texto)
    except ErrorEntrada as e:
        raise ErrorVerificacion("SINTAXIS", f"{campo}: {e}") from e


def _ecuacion(texto: str, campo: str) -> sp.Expr:
    t = texto.replace("==", "=")
    if "=" in t:
        a, b = t.split("=", 1)
        return _expr(a, campo) - _expr(b, campo)
    return _expr(t, campo)


def _sin_division_por_cero(e: sp.Expr, campo: str) -> None:
    if e.has(sp.zoo, sp.nan) or e.has(sp.oo) and not e.is_number:
        raise ErrorVerificacion("DIVISION_POR_CERO", f"{campo} contiene una división por cero o un valor infinito "
                                f"({e}).", "Revisa los denominadores: no pueden ser idénticamente nulos.")
    _, den = sp.fraction(sp.together(e))
    if den.free_symbols and es_cero(den):
        raise ErrorVerificacion("DIVISION_POR_CERO", f"En {campo} el denominador {den} es idénticamente 0.",
                                "Simplifica la expresión o corrige el denominador.")


def _variables(exprs: list[sp.Expr], declaradas: list[str] | None, que: str) -> list[sp.Symbol]:
    libres = set().union(*[e.free_symbols for e in exprs])
    if declaradas:
        nombres = set(declaradas)
        extra = sorted(s.name for s in libres if s.name not in nombres)
        if extra:
            raise ErrorVerificacion("SIMBOLOS_NO_DECLARADOS", f"{que} usa símbolos que no están en 'variables': "
                                    f"{', '.join(extra)}.", "Agrégalos a 'variables' o reemplázalos por números.")
        return [sp.Symbol(n) for n in declaradas]
    return sorted(libres, key=lambda s: s.name)


def _grado(e: sp.Expr, vs: list[sp.Symbol]) -> int | None:
    try:
        return sp.Poly(sp.together(e).as_numer_denom()[0], *vs).total_degree()
    except (sp.PolynomialError, sp.GeneratorsNeeded, ValueError):
        return None


# ════════════════════════════════════════════════════════════════════════════
# Verificaciones por método
# ════════════════════════════════════════════════════════════════════════════
def verificar_lagrange(s: SolicitudLagrange) -> InformeVerificacion:
    inf = InformeVerificacion()
    f = _expr(s.funcion, "funcion")
    gs = [_ecuacion(g, f"restricciones[{i}]") for i, g in enumerate(s.restricciones)]
    _sin_division_por_cero(f, "la función objetivo")
    for i, g in enumerate(gs):
        _sin_division_por_cero(g, f"la restricción {i + 1}")
    vs = _variables([f, *gs], s.variables, "El problema")
    n, m = len(vs), len(gs)
    if n == 0:
        raise ErrorVerificacion("SIN_VARIABLES", "Ni la función ni las restricciones dependen de alguna variable.")
    if n > MAX_VARIABLES:
        raise ErrorVerificacion("DEMASIADAS_VARIABLES", f"Hay {n} variables; el máximo es {MAX_VARIABLES}.",
                                "Reduce el problema o fija algunas variables.")
    for i, g in enumerate(gs, 1):
        if not g.free_symbols:
            if es_cero(g):
                raise ErrorVerificacion("RESTRICCION_TRIVIAL", f"La restricción {i} es una identidad (0 = 0): no "
                                        "restringe nada.", "Elimínala o corrígela.")
            raise ErrorVerificacion("RESTRICCION_IMPOSIBLE", f"La restricción {i} es imposible ({g} = 0 nunca se "
                                    "cumple): el conjunto factible es vacío.", "Revisa los números de esa ecuación.")
        reales = {v: sp.Symbol(v.name, real=True) for v in g.free_symbols}
        gr = sp.expand(g.xreplace(reales))
        if gr.is_positive or gr.is_negative:
            raise ErrorVerificacion("RESTRICCION_IMPOSIBLE", f"La restricción {i} ({g} = 0) no tiene soluciones "
                                    f"reales: el lado izquierdo es siempre {'positivo' if gr.is_positive else 'negativo'}"
                                    ". El conjunto factible es vacío.",
                                    "Revisa el signo de la constante (¿quisiste escribir x^2 + y^2 = 1?).")
        if all(es_cero(sp.diff(g, v)) for v in vs):
            raise ErrorVerificacion("GRADIENTE_NULO", f"∇g{i} es idénticamente 0: la restricción no depende de "
                                    "las variables.", "Revisa la restricción.")
    if m > n:
        raise ErrorVerificacion("SOBREDETERMINADO", f"Hay {m} restricciones y solo {n} variables: el sistema está "
                                "sobredeterminado (debe cumplirse m ≤ n).",
                                "Quita restricciones redundantes o agrega variables.")
    if m == n:
        inf.avisos.append("m = n: las restricciones dejan solo puntos aislados; no hay optimización real que hacer.")
    if not f.free_symbols & set(vs):
        inf.avisos.append("La función objetivo es constante: todos los puntos factibles son a la vez máximos y mínimos.")
    if m > 1:
        J = sp.Matrix([[sp.diff(g, v) for v in vs] for g in gs])
        try:
            sub = {v: sp.Rational(3 + 2 * k, 7) for k, v in enumerate(vs)}
            if J.subs(sub).rank() < m and J.subs({v: sp.Rational(5 + 3 * k, 11) for k, v in enumerate(vs)}).rank() < m:
                inf.avisos.append("Las restricciones parecen linealmente dependientes (jacobiano de rango < m en "
                                  "puntos de prueba): podría haber una restricción redundante.")
        except Exception:  # noqa: BLE001
            pass
    grados = [_grado(e, vs) for e in [f, *gs]]
    if all(g is not None for g in grados):
        bez = max(grados[0] - 1, 1)
        for g in grados[1:]:
            bez *= max(g, 1)
        inf.datos["cota_bezout"] = bez
        if bez > MAX_GRADO_BEZOUT:
            inf.avisos.append(f"El sistema puede tener hasta ~{bez} soluciones (cota de Bézout): el cálculo exacto "
                              "puede tardar o superar el tiempo límite.")
    inf.datos.update({"n_variables": n, "n_restricciones": m, "variables": [v.name for v in vs]})
    return inf


def verificar_hessiana(s: SolicitudHessiana) -> InformeVerificacion:
    inf = InformeVerificacion()
    f = _expr(s.funcion, "funcion")
    _sin_division_por_cero(f, "la función")
    vs = _variables([f], s.variables, "La función")
    n = len(vs)
    if n == 0 or not f.free_symbols:
        raise ErrorVerificacion("FUNCION_CONSTANTE", f"f = {f} es constante: todos los puntos son críticos y no hay "
                                "nada que clasificar.", "Escribe una función que dependa de las variables.")
    if n > MAX_VARIABLES:
        raise ErrorVerificacion("DEMASIADAS_VARIABLES", f"Hay {n} variables; el máximo es {MAX_VARIABLES}.")
    grad = [sp.diff(f, v) for v in vs]
    if all(es_cero(g) for g in grad):
        raise ErrorVerificacion("FUNCION_CONSTANTE", "∇f ≡ 0: la función es constante en las variables indicadas.",
                                "Revisa la lista de variables.")
    H = sp.hessian(f, vs)
    if H.shape[0] != H.shape[1]:
        raise ErrorVerificacion("HESSIANA_NO_CUADRADA", f"La Hessiana resultó de tamaño {H.shape}.")
    asim = [(i, j) for i in range(n) for j in range(i + 1, n) if not es_cero(H[i, j] - H[j, i])]
    if asim:
        inf.avisos.append("La Hessiana no es simétrica en " + ", ".join(f"({i + 1},{j + 1})" for i, j in asim) +
                          ": f no es de clase C² en todo el dominio (teorema de Schwarz).")
    if f.has(sp.Abs, sp.sign) or any(p.exp.is_Rational and not p.exp.is_Integer for p in f.atoms(sp.Pow)):
        inf.avisos.append("f tiene |·| o raíces: puede haber puntos críticos donde ∇f no existe (se analizan aparte).")
    g = _grado(f, vs)
    if g is not None:
        inf.datos["grado"] = g
        if (g - 1) ** n > MAX_GRADO_BEZOUT:
            inf.avisos.append(f"∇f = 0 puede tener hasta ~{(g - 1) ** n} soluciones: el cálculo exacto puede tardar.")
    inf.datos.update({"n_variables": n, "variables": [v.name for v in vs]})
    return inf


def verificar_frenet(s: SolicitudFrenet) -> InformeVerificacion:
    inf = InformeVerificacion()
    comps = [_expr(c, f"curva[{i}]") for i, c in enumerate(s.curva)]
    if len(comps) == 2:
        comps.append(sp.Integer(0))
        inf.avisos.append("Curva plana: se trata en R³ con z = 0.")
    t = sp.Symbol(s.parametro)
    for i, c in enumerate(comps):
        _sin_division_por_cero(c, f"la componente {i + 1}")
    if not any(c.has(t) for c in comps):
        raise ErrorVerificacion("NO_DEPENDE_DEL_PARAMETRO", f"Ninguna componente depende de '{s.parametro}': la "
                                "curva es un punto fijo.", f"Usa '{s.parametro}' en las componentes o cambia 'parametro'.")
    otros = sorted({x.name for c in comps for x in c.free_symbols} - {s.parametro})
    if otros:
        faltan = [x for x in otros if x not in s.constantes]
        inf.avisos.append("Constantes simbólicas: " + ", ".join(otros) + " (las fórmulas quedan generales)." +
                          (f" Para los gráficos se usará 1 en {', '.join(faltan)}." if faltan else ""))
    r = sp.Matrix(comps)
    d1, d2 = r.diff(t), r.diff(t, 2)
    if all(es_cero(c) for c in d1):
        raise ErrorVerificacion("CURVA_CONSTANTE", "r'(t) ≡ 0: la curva no se mueve.", "Revisa las componentes.")
    cruz = d1.cross(d2)
    if all(es_cero(c) for c in cruz):
        raise ErrorVerificacion("CURVATURA_CERO", "r' × r'' ≡ 0, es decir, la curvatura es κ ≡ 0: la curva es una "
                                "RECTA. El triedro de Frenet no existe (N y B no están definidos) y la torsión no "
                                "tiene sentido.", "Para una recta solo existe el vector tangente T = r'/‖r'‖. Usa una "
                                "curva que se doble, p. ej. una hélice (cos t, sin t, t).")
    t0 = _expr(s.t0, "t0")
    if t0.free_symbols - set(sp.Symbol(x) for x in s.constantes) - set(sp.Symbol(x) for x in otros):
        raise ErrorVerificacion("T0_INVALIDO", f"t0 = {t0} contiene símbolos desconocidos.", "Usa un número o una "
                                "expresión como pi/4.")
    vals = {sp.Symbol(k): v for k, v in s.constantes.items()}
    vals.update({sp.Symbol(x): 1 for x in otros if x not in s.constantes})
    r0 = [num(c.subs(t, t0).subs(vals)) for c in comps]
    if any(v is None for v in r0):
        raise ErrorVerificacion("T0_FUERA_DEL_DOMINIO", f"r(t0) no está definido o no es real en t0 = {t0}.",
                                "Elige un t0 dentro del dominio de las componentes.")
    v0 = [num(c.subs(t, t0).subs(vals)) for c in d1]
    if all(abs(v) < 1e-12 for v in v0 if v is not None):
        raise ErrorVerificacion("PUNTO_SINGULAR", f"r'(t0) = 0 en t0 = {t0}: es un punto singular (posible cúspide) "
                                "y el triedro de Frenet no está definido ahí.",
                                f"Prueba otro t0, por ejemplo t0 = {sp.nsimplify(t0 + 1)}.")
    c0 = [num(c.subs(t, t0).subs(vals)) for c in cruz]
    if all(v is not None and abs(v) < 1e-12 for v in c0):
        raise ErrorVerificacion("CURVATURA_CERO_EN_T0", f"κ(t0) = 0 en t0 = {t0}: es un punto de inflexión; N, B, τ y "
                                "los planos osculador y rectificante no están definidos ahí.",
                                f"Prueba un t0 cercano, por ejemplo t0 = {sp.nsimplify(t0 + sp.Rational(1, 2))}.")
    inf.datos.update({"dimension_entrada": len(s.curva), "r_t0": r0})
    return inf


def verificar(metodo: str, solicitud: Any) -> InformeVerificacion:
    """Despachador de la capa lógica."""
    fn = {"lagrange": verificar_lagrange, "hessiana": verificar_hessiana, "frenet": verificar_frenet}.get(metodo)
    if fn is None:
        raise ErrorVerificacion("METODO_DESCONOCIDO", f"Método '{metodo}' no existe.")
    return fn(solicitud)


def componentes_de_texto(texto: str) -> list[str]:
    """Ayuda para clientes que envían la curva como un único texto."""
    return [str(c) for c in parsear_tupla(texto)]
