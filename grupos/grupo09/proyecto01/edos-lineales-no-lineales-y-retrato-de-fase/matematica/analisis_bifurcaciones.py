"""Teoría de bifurcaciones: el Tema 3 del balotario.

Tres familias, cada una con el procedimiento del balotario:

* **Bifurcaciones de equilibrios en 1D** (3.1, 3.2, 3.3) — ẋ = f(x; μ).
  Ramas de equilibrio x*(μ) y dónde existen; estabilidad lineal con
  f_x(x*(μ); μ) en cada tramo; puntos críticos (f = f_x = 0) y las
  condiciones de Sotomayor, que deciden el tipo: silla-nodo (f_μ ≠ 0,
  f_xx ≠ 0), transcrítica (f_μ = 0, f_xμ ≠ 0, f_xx ≠ 0) u horquilla
  (f_μ = f_xx = 0, f_xμ ≠ 0, f_xxx ≠ 0; supercrítica si f_xxx·f_xμ < 0).
  Si hay tramos con dos atractores se calculan la biestabilidad, los saltos y
  el ancho de la histéresis (3.3B).
* **Hopf** (3.4) — linealización en el equilibrio, λ(μ) = α(μ) ± iω(μ),
  condición espectral α(μc) = 0 con ω(μc) ≠ 0, transversalidad α'(μc) ≠ 0,
  forma polar (radio y periodo exactos del ciclo cuando el sistema es
  rotacionalmente simétrico) y primer coeficiente de Lyapunov, que decide si
  es supercrítica o subcrítica.
* **Homoclínica** (3.5) — equilibrios y su clasificación según μ, sistema
  hamiltoniano no perturbado y su lazo homoclínico, integral de Melnikov
  M(μ) y su cero. Como la perturbación de 3.5 no es pequeña, Melnikov es una
  estimación de primer orden: aquí se contrasta con el valor que da un
  **disparo numérico** sobre las variedades de la silla, y se mide del lado en
  que existe el ciclo la divergencia logarítmica del periodo.
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from sympy.calculus.util import continuous_domain

from matematica import MetodoNoAplicable
from matematica import muestreo
from matematica.analisis_estabilidad import (buscar_equilibrios, clasificar_1d, linealizar,
                                             regimenes_por_parametro, signo)
from matematica.desarrollo import Desarrollo, F, L, intervalo_texto, punto_latex, suma
from matematica.problema import exacto
from matematica.sistemas_planos import (R_POLAR, THETA, _pmatrix, descripcion, forma_polar,
                                        seccion_clasificacion_parametrica, seccion_equilibrios,
                                        seccion_jacobiano, seccion_polar)

TEMA = "Tema 3 · Teoría de bifurcaciones"


def _rel(valor):
    return {1: ">", -1: "<", 0: "="}.get(signo(valor), r"\gtrless")


# ---------------------------------------------------------------------------
# Bifurcaciones en 1D
# ---------------------------------------------------------------------------

def identificar_bifurcacion_1d(problema):
    if problema.tipo != "edo" or problema.dimension != 1 or not problema.autonomo:
        return None
    if not problema.tiene_parametro:
        return None
    return {"parametro": problema.parametro}


def dominio_real(expresion, parametro):
    """Valores del parámetro donde la expresión es real (raíces de índice par ≥ 0)."""
    dominio = sp.S.Reals
    potencias = sorted([p for p in sp.sympify(expresion).atoms(sp.Pow)
                        if p.exp.is_Rational and p.exp.q % 2 == 0],
                       key=lambda p: sp.count_ops(p))
    for potencia in potencias:
        try:
            conjunto = sp.solve_univariate_inequality(potencia.base >= 0, parametro, relational=False)
        except (NotImplementedError, ValueError, TypeError):
            continue
        dominio = dominio.intersect(conjunto)
    return dominio


def _intervalos(conjunto):
    if isinstance(conjunto, sp.Union):
        return [a for a in conjunto.args]
    return [conjunto]


def _prueba_en(intervalo):
    a, b = intervalo.inf, intervalo.sup
    if a.is_infinite and b.is_infinite:
        return sp.Integer(0)
    if a.is_infinite:
        return b - 1
    if b.is_infinite:
        return a + 1
    return (a + b) / 2


def _texto_rango(conjunto, p):
    from matematica.analisis_estabilidad import describir_conjunto
    if isinstance(conjunto, sp.Interval) and conjunto.inf == conjunto.sup:
        return f"{L(p)} = {L(conjunto.inf)}"
    return describir_conjunto(conjunto, p)


def desarrollar_bifurcacion_1d(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_bifurcacion_1d(problema)
    if datos is None:
        raise MetodoNoAplicable("Hace falta una ecuación autónoma ẋ = f(x; μ) con el parámetro μ simbólico.")
    x = problema.estados[0]
    mu = problema.parametro
    f = sp.sympify(problema.campo[0])
    d = Desarrollo("bifurcacion_1d", "Bifurcación de equilibrios en una dimensión", TEMA,
                   "Ramas de equilibrio, estabilidad lineal y condiciones de Sotomayor",
                   tratamiento=["analitico", "cualitativo"], balotario=["3.1", "3.2", "3.3"])
    simetrica = sp.simplify(f.subs(x, -x) + f) == 0

    # --- 1. Ramas de equilibrio -------------------------------------------------
    seccion = d.seccion("equilibrios", f"Puntos de equilibrio en función del parámetro ${L(mu)}$")
    factorizada = sp.factor(f)
    if sp.srepr(factorizada) != sp.srepr(f):
        seccion.formula(rf"f({L(x)}; {L(mu)}) = {L(f)}", "=", factorizada, "= 0")
    else:
        seccion.formula(rf"f({L(x)}; {L(mu)}) = {L(f)} = 0")
    if simetrica:
        seccion.formula(rf"f(-{L(x)}; {L(mu)}) = -f({L(x)}; {L(mu)})", r"\implies",
                        rf"\text{{invarianza bajo la simetría }} {L(x)} \to -{L(x)}", destacada=True)
        d.guardar("simetria", True)
    ramas = []
    for factor in sp.Mul.make_args(factorizada):
        base = factor.base if isinstance(factor, sp.Pow) else factor
        if not base.has(x):
            continue
        ramas += _ramas_de_factor(seccion, base, x, mu)
    unicas = []
    for rama in ramas:
        if not any(sp.simplify(rama - previa) == 0 for previa in unicas):
            unicas.append(rama)
    anulan = all(sp.simplify(f.subs(x, r)) == 0 for r in unicas)
    d.validar("ramas_anulan_el_campo", anulan,
              "Cada rama x*(μ) sustituida en f(x; μ) da 0 idénticamente: son equilibrios para todo μ "
              "donde existen.")
    dominios = [dominio_real(r, mu) for r in unicas]
    # Orden: por el valor en un parámetro donde existan (arriba la mayor).
    prueba = _prueba_comun(dominios)
    orden = sorted(range(len(unicas)), key=lambda i: _valor_rama(unicas[i], mu, prueba, dominios[i]))
    unicas = [unicas[i] for i in orden]
    dominios = [dominios[i] for i in orden]
    d.guardar("ramas", [{"expresion": r, "existe_para": D} for r, D in zip(unicas, dominios)])

    fx = sp.diff(f, x)
    estabilidades = [sp.simplify(fx.subs(x, r)) for r in unicas]
    criticos = _puntos_criticos(f, fx, x, mu)
    cortes = set()
    for D in dominios:
        for intervalo in _intervalos(D):
            cortes.update(e for e in (intervalo.inf, intervalo.sup) if e.is_finite)
    for s, D in zip(estabilidades, dominios):
        try:
            ceros = sp.solveset(s, mu, domain=D)
            if isinstance(ceros, sp.FiniteSet):
                cortes.update(ceros)
        except (NotImplementedError, ValueError, TypeError):
            pass
    cortes.update(m for m, _ in criticos)
    inferior, superior = problema.rango_parametro or (None, None)
    cortes = sorted((c for c in cortes if (inferior is None or c >= inferior) and
                     (superior is None or c <= superior)), key=float)
    regimenes = _regimenes(cortes, inferior, superior)

    seccion = d.seccion("casos", f"Equilibrios según ${L(mu)}$")
    tabla = []
    for regimen in regimenes:
        valor = _prueba_en(regimen) if not (isinstance(regimen, sp.FiniteSet)) else next(iter(regimen))
        presentes = [(i, r) for i, (r, D) in enumerate(zip(unicas, dominios)) if valor in D]
        texto = _describir_regimen(regimen, mu)
        if not presentes:
            muestra = sp.simplify(f.subs(mu, valor).subs(x, 0))
            seccion.formula(rf"{texto} \implies \nexists\, {L(x)}^* \in \mathbb{{R}}", destacada=True)
            sentido = "decrece" if signo(muestra) == -1 else "crece"
            seccion.texto(f"Sin equilibrios f no cambia de signo: el flujo {sentido} monótonamente "
                          f"(f(0; {sp.sstr(valor)}) = {sp.sstr(muestra)}).")
            tabla.append((texto, "ninguno"))
            continue
        if isinstance(regimen, sp.FiniteSet):
            valores = []
            for _, r in presentes:
                v = sp.simplify(r.subs(mu, valor))
                if not any(sp.simplify(v - w) == 0 for w in valores):
                    valores.append(v)
            valores.sort(key=float)
            coinciden = len(valores) < len(presentes)
            lista = rf"{L(x)}^* \in \left\{{{L(valores)}\right\}}"
            if coinciden:
                lista += r"\quad (\text{ramas que colisionan})"
        else:
            lista = r",\quad ".join(rf"{L(x)}_{{{i + 1}}}^* = {L(r)}" for i, r in presentes)
        seccion.formula(rf"{texto} \implies {lista}", destacada=True)
        tabla.append((texto, len(presentes)))

    # --- 2. Estabilidad lineal ---------------------------------------------------
    seccion = d.seccion("estabilidad", "Análisis de estabilidad lineal")
    seccion.formula(rf"f'({L(x)}; {L(mu)}) = \frac{{\partial}}{{\partial {L(x)}}}\left({L(f)}\right)", "=", fx,
                    destacada=True, ref="derivada")
    d.guardar("derivada", fx)
    resumen_ramas = []
    for i, (rama, D, s) in enumerate(zip(unicas, dominios, estabilidades), 1):
        seccion.rotulo(rf"\text{{Rama }} {L(x)}_{{{i}}}^*({L(mu)}) = {L(rama)}")
        seccion.formula(rf"f'\left({L(rama)}; {L(mu)}\right) = {L(s)}")
        tramos = []
        for intervalo in _partir(D, s, mu, cortes):
            if isinstance(intervalo, sp.FiniteSet) or intervalo.inf == intervalo.sup:
                continue
            valor = _prueba_en(intervalo)
            signo_s = signo(s.subs(mu, valor))
            estado = "estable" if signo_s == -1 else "inestable" if signo_s == 1 else "no hiperbólico"
            palabra = {"estable": "asintóticamente estable (atractor)",
                       "inestable": "inestable (repulsor)"}.get(estado, "no hiperbólico")
            seccion.formula(rf"{_texto_rango(intervalo, mu)} \implies f' {_rel(s.subs(mu, valor))} 0 "
                            rf"\implies \text{{{palabra}}}", destacada=True)
            tramos.append({"intervalo": intervalo, "estado": estado})
        resumen_ramas.append({"expresion": rama, "existe_para": D, "derivada": s, "tramos": tramos})
    d.guardar("estabilidad_ramas", resumen_ramas)
    d.validar("ramas_contra_muestreo_numerico", _ramas_coherentes(f, x, mu, unicas, dominios, regimenes),
              "En un valor de prueba de cada tramo del parámetro, f(x; μ) muestreada en una malla fina "
              "cambia de signo exactamente en los equilibrios que predicen las ramas, y el sentido del "
              "cambio coincide con la estabilidad calculada.", tipo="numerica")

    # --- 3. Puntos críticos y condiciones de Sotomayor ----------------------------
    clases = []
    for k, (mu_c, x_c) in enumerate(criticos, 1):
        seccion = d.seccion(f"sotomayor_{k}",
                            rf"Condiciones de no degeneración en $({L(mu)}_c, {L(x)}^*) = ({L(mu_c)}, {L(x_c)})$")
        punto = {x: x_c, mu: mu_c}
        derivadas = {
            "f": sp.simplify(f.subs(punto)),
            "f_x": sp.simplify(fx.subs(punto)),
            "f_mu": sp.simplify(sp.diff(f, mu).subs(punto)),
            "f_xx": sp.simplify(sp.diff(f, x, 2).subs(punto)),
            "f_xmu": sp.simplify(sp.diff(f, x, mu).subs(punto)),
            "f_xxx": sp.simplify(sp.diff(f, x, 3).subs(punto)),
        }
        tipo, motivos = _tipo_de_bifurcacion(derivadas)
        etiqueta = rf"({L(x_c)}; {L(mu_c)})"
        seccion.formula(rf"f{etiqueta} = {L(derivadas['f'])},\qquad f_{{{L(x)}}}{etiqueta} = {L(derivadas['f_x'])}"
                        r"\implies \lambda = 0\ (\text{pérdida de hiperbolicidad})")
        nombres = {"f_mu": rf"f_{{{L(mu)}}}", "f_xx": rf"f_{{{L(x)}{L(x)}}}", "f_xmu": rf"f_{{{L(x)}{L(mu)}}}",
                   "f_xxx": rf"f_{{{L(x)}{L(x)}{L(x)}}}"}
        for clave, motivo in motivos:
            valor = derivadas[clave]
            texto_valor = "0" if valor == 0 else rf"{L(valor)} \neq 0"
            seccion.formula(rf"{nombres[clave]}{etiqueta} = {texto_valor}", rf"\quad (\text{{{motivo}}})")
        seccion.formula(rf"\text{{Bifurcación {tipo} en }} ({L(mu)}_c, {L(x)}^*) = ({L(mu_c)}, {L(x_c)})",
                        destacada=True, ref=f"tipo_{k}")
        clases.append({"mu_c": mu_c, "x_c": x_c, "tipo": tipo, "derivadas": derivadas})
    d.guardar("puntos_criticos", clases)

    # --- 4. Biestabilidad e histéresis --------------------------------------------
    _histeresis(d, resumen_ramas, x, mu, cortes, simetrica)
    vistas = set()
    for clase in clases:
        clave = (clase["tipo"], clase["mu_c"])
        if clave in vistas:
            continue
        vistas.add(clave)
        d.concluir(_conclusion_tipo(clase, x, mu))
    _diagrama_1d(d, f, x, mu, unicas, dominios, estabilidades, clases, problema)
    return d


def _ramas_coherentes(f, x, mu, ramas, dominios, regimenes):
    """Contraste numérico de las ramas: ceros y signo de f en una malla, régimen por régimen.

    Es independiente de la resolución simbólica: si una rama tuviera mal su
    dominio de existencia o su estabilidad, el número de cambios de signo o su
    sentido no coincidiría.
    """
    funcion = sp.lambdify((x, mu), f, "numpy")
    for regimen in regimenes:
        if isinstance(regimen, sp.FiniteSet) or regimen.inf == regimen.sup:
            continue                       # en μc los ceros son dobles: no cambian de signo
        valor = _prueba_en(regimen)
        presentes = sorted({float(sp.N(r.subs(mu, valor))) for r, D in zip(ramas, dominios) if valor in D})
        derivada_x = sp.diff(f, x)
        if any(abs(float(sp.N(derivada_x.subs({x: v, mu: valor})))) < 1e-12 for v in presentes):
            continue                       # raíz múltiple: el muestreo de signo no la ve
        radio = 2.0 + 2.0 * max((abs(v) for v in presentes), default=0.0)
        xs = np.linspace(-radio, radio, 40001)
        # Desplazada una fracción irracional del paso: una raíz racional no cae
        # justo en un nodo (donde el signo sería 0 y el cambio no se vería).
        xs = xs + (xs[1] - xs[0]) * (math.sqrt(2) - 1) / 2
        with np.errstate(all="ignore"):
            ys = np.asarray(funcion(xs, float(valor)), dtype=float) * np.ones_like(xs)
        cambios = np.flatnonzero(np.sign(ys[:-1]) * np.sign(ys[1:]) < 0)
        if len(cambios) != len(presentes):
            return False
        for indice, equilibrio in zip(cambios, presentes):
            if abs(xs[indice] - equilibrio) > 2 * (xs[1] - xs[0]):
                return False
            # De + a − al crecer x: atractor (f' < 0); de − a +: repulsor.
            atrae = ys[indice] > 0 > ys[indice + 1]
            derivada = float(sp.N(derivada_x.subs({x: equilibrio, mu: valor})))
            if atrae != (derivada < 0):
                return False
    return True


def _ramas_de_factor(seccion, factor, x, mu):
    """Soluciones x*(μ) de factor = 0, con el cambio u = x² si el factor es par en x."""
    factor = sp.expand(factor)
    if factor.is_polynomial(x) and sp.degree(factor, x) == 4 and sp.simplify(factor.subs(x, -x) - factor) == 0:
        u = sp.Symbol("u", real=True)
        en_u = sp.expand(factor.subs(x ** 2, u).subs(x ** 4, u ** 2))
        if not en_u.has(x):
            principal = sp.Poly(en_u, u).LC()
            normalizada = sp.expand(en_u / principal)
            if signo(sp.Poly(normalizada, u).LC()) == -1:
                normalizada = -normalizada
            raices = sp.solve(normalizada, u)
            seccion.formula(rf"u = {L(x)}^2:\quad {L(normalizada)} = 0", r"\implies",
                            rf"u = {L(x)}^2 = {L(raices)}")
            return [s * sp.sqrt(r) for r in raices for s in (1, -1)]
    soluciones = sp.solve(factor, x)
    return [sp.simplify(s) for s in soluciones]


def _prueba_comun(dominios):
    candidatos = []
    for D in dominios:
        for intervalo in _intervalos(D):
            if isinstance(intervalo, sp.Interval) and intervalo.measure > 0:
                candidatos.append(_prueba_en(intervalo))
    for c in candidatos:
        if all(c in D for D in dominios):
            return c
    return candidatos[0] if candidatos else sp.Integer(1)


def _valor_rama(rama, mu, prueba, dominio):
    valor = prueba if prueba in dominio else _prueba_en(_intervalos(dominio)[0])
    try:
        return float(sp.N(rama.subs(mu, valor)))
    except (TypeError, ValueError):
        return 0.0


def _puntos_criticos(f, fx, x, mu):
    try:
        soluciones = sp.solve([f, fx], [x, mu], dict=True)
    except (NotImplementedError, ValueError):
        return []
    puntos = []
    for s in soluciones:
        if x in s and mu in s and all(sp.im(sp.N(v)) == 0 for v in (s[x], s[mu])):
            par = (sp.nsimplify(s[mu]), sp.nsimplify(s[x]))
            if par not in puntos:
                puntos.append(par)
    return sorted(puntos, key=lambda p: (float(p[0]), float(p[1])))


def _regimenes(cortes, inferior, superior):
    a = sp.nsimplify(inferior) if inferior is not None else -sp.oo
    b = sp.nsimplify(superior) if superior is not None else sp.oo
    bordes = [a, *[c for c in cortes if c not in (a, b)], b]
    tramos = [sp.FiniteSet(c) for c in cortes]
    tramos += [sp.Interval.open(p, q) for p, q in zip(bordes[:-1], bordes[1:]) if p != q]
    return sorted(tramos, key=lambda s: (float(s.inf), 0 if isinstance(s, sp.FiniteSet) else 1))


def _describir_regimen(regimen, mu):
    from matematica.analisis_estabilidad import describir_conjunto
    return describir_conjunto(regimen, mu)


def _partir(dominio, derivada, mu, cortes):
    """El dominio de una rama, cortado en los ceros de su derivada y los valores críticos."""
    piezas = []
    for intervalo in _intervalos(dominio):
        if not isinstance(intervalo, sp.Interval):
            continue
        internos = sorted({c for c in cortes if intervalo.inf < c < intervalo.sup}, key=float)
        bordes = [intervalo.inf, *internos, intervalo.sup]
        piezas += [sp.Interval.open(p, q) for p, q in zip(bordes[:-1], bordes[1:]) if p != q]
    return piezas


def _tipo_de_bifurcacion(derivadas):
    """Tipo según las condiciones de Sotomayor, y qué condición se usó para decidirlo."""
    f_mu, f_xx, f_xmu, f_xxx = (derivadas[k] for k in ("f_mu", "f_xx", "f_xmu", "f_xxx"))
    if f_mu != 0 and f_xx != 0:
        return "silla-nodo", [("f_mu", "transversalidad del parámetro"),
                              ("f_xx", "no degeneración cuadrática")]
    if f_mu == 0 and f_xx != 0 and f_xmu != 0:
        return "transcrítica", [("f_mu", "persistencia del equilibrio"),
                                ("f_xmu", "transversalidad: el autovalor cambia de signo"),
                                ("f_xx", "curvatura cuadrática no nula")]
    if f_mu == 0 and f_xx == 0 and f_xmu != 0 and f_xxx != 0:
        sentido = "supercrítica" if signo(f_xxx * f_xmu) == -1 else "subcrítica"
        return f"de horquilla {sentido}", [("f_mu", "persistencia del equilibrio"),
                                           ("f_xx", "simetría: sin término cuadrático"),
                                           ("f_xmu", "transversalidad"),
                                           ("f_xxx", "no degeneración cúbica")]
    return "degenerada (no genérica)", [("f_mu", "derivada respecto del parámetro"),
                                        ("f_xx", "segunda derivada")]


def _conclusion_tipo(clase, x, mu):
    tipo, mu_c = clase["tipo"], sp.sstr(clase["mu_c"])
    if tipo == "silla-nodo":
        return (f"En {mu} = {mu_c} dos equilibrios de estabilidad opuesta colisionan y se aniquilan: "
                f"de un lado de {mu_c} existen, del otro no (bifurcación silla-nodo).")
    if tipo == "transcrítica":
        return (f"En {mu} = {mu_c} las dos ramas se cruzan e intercambian su estabilidad; ninguna "
                "desaparece (bifurcación transcrítica).")
    if "supercrítica" in tipo:
        return (f"En {mu} = {mu_c} el equilibrio central pierde estabilidad y nacen dos ramas "
                "simétricas estables: la transición es continua y reversible (horquilla supercrítica).")
    if "subcrítica" in tipo:
        return (f"En {mu} = {mu_c} las ramas no triviales que se unen al equilibrio central son "
                "inestables: al perder estabilidad el estado salta lejos (horquilla subcrítica).")
    return f"En {mu} = {mu_c} la bifurcación es degenerada: las condiciones genéricas no se cumplen."


def _histeresis(d, ramas, x, mu, cortes, simetrica):
    """Tramos finitos con dos atractores, saltos en sus extremos y ancho de la histéresis.

    Dos ramas simétricas (±√μ de una horquilla) coexisten sin histéresis: el
    estado no salta de una a otra al mover μ. Por eso solo cuentan los solapes
    de longitud finita entre ramas que no son imagen especular una de otra.
    """
    estables = []
    for rama in ramas:
        conjunto = sp.EmptySet
        for tramo in rama["tramos"]:
            if tramo["estado"] == "estable":
                conjunto = sp.Union(conjunto, tramo["intervalo"])
        for c in cortes:
            if c in rama["existe_para"] and signo(rama["derivada"].subs(mu, c)) == -1:
                conjunto = sp.Union(conjunto, sp.FiniteSet(c))
        estables.append(conjunto)

    def intervalos_de(conjunto):
        return [a for a in (conjunto.args if isinstance(conjunto, sp.Union) else (conjunto,))
                if isinstance(a, sp.Interval)]

    solapes = []
    for i in range(len(ramas)):
        for j in range(i + 1, len(ramas)):
            if simetrica and sp.simplify(ramas[i]["expresion"] + ramas[j]["expresion"]) == 0:
                continue
            for comun in intervalos_de(estables[i].intersect(estables[j])):
                if comun.measure > 0 and comun.measure.is_finite:
                    solapes.append((comun, i, j))
    if not solapes:
        return
    comun, i, j = solapes[0]
    a, b = comun.inf, comun.sup
    seccion = d.seccion("histeresis", "Biestabilidad, salto de estado e histéresis")
    seccion.formula(rf"{L(a)} < {L(mu)} < {L(b)} \implies \text{{coexisten dos atractores}}", destacada=True)
    saltos = []
    for extremo, sentido in ((b, 1), (a, -1)):
        for k, rama in enumerate(ramas):
            # La rama k deja de ser estable al cruzar el extremo en ese sentido.
            if not any((I.sup == extremo if sentido == 1 else I.inf == extremo)
                       for I in intervalos_de(estables[k])):
                continue
            mas_alla = extremo + sentido * sp.Rational(1, 1000)
            destinos = [m for m in range(len(ramas)) if m != k and mas_alla in estables[m]]
            if not destinos:
                continue
            origen = sp.simplify(rama["expresion"].subs(mu, extremo))
            valores = sorted({sp.simplify(ramas[m]["expresion"].subs(mu, extremo)) for m in destinos}, key=float)
            if all(sp.simplify(v - origen) == 0 for v in valores):
                continue
            saltos.append((extremo, sentido, origen, valores))
            break
    for extremo, sentido, origen, valores in saltos:
        flecha = "^+" if sentido == 1 else "^-"
        destino = L(valores[0]) if len(valores) == 1 else (r"\pm " + L(abs(valores[-1]))
                                                          if simetrica and len(valores) == 2 else L(valores))
        origen_texto = (r"\pm " + L(abs(origen))) if simetrica and origen != 0 else L(origen)
        seccion.formula(rf"{L(mu)} \to {L(extremo)}{flecha}:\quad {L(x)}^* = {origen_texto} \;\longrightarrow\; "
                        rf"{L(x)}^* = {destino} \quad (\text{{salto}})", destacada=True)
    ancho = sp.simplify(b - a)
    seccion.formula(rf"\text{{Ciclo de histéresis: }} \Delta{L(mu)} = {L(b)} - \left({L(a)}\right) = {L(ancho)}",
                    destacada=True, ref="ancho_histeresis")
    d.guardar("biestabilidad", comun)
    d.guardar("ancho_histeresis", ancho)
    d.guardar("saltos", [{"mu": e, "desde": o, "hasta": v} for e, _, o, v in saltos])
    d.concluir(f"Entre {mu} = {sp.sstr(a)} y {mu} = {sp.sstr(b)} coexisten dos atractores: el estado "
               f"depende de la historia (histéresis de ancho {sp.sstr(ancho)}).")


def _diagrama_1d(d, f, x, mu, ramas, dominios, derivadas, clases, problema):
    criticos = [float(c["mu_c"]) for c in clases] + [float(e) for D in dominios for I in _intervalos(D)
                                                    for e in (I.inf, I.sup) if e.is_finite]
    centro = sum(criticos) / len(criticos) if criticos else 0.0
    ancho = max((max(criticos) - min(criticos)) if criticos else 0.0, 1.0)
    inferior, superior = problema.rango_parametro or (None, None)
    a = float(inferior) if inferior is not None else centro - 1.6 * ancho
    b = float(superior) if superior is not None else centro + 2.6 * ancho
    valores = np.linspace(a, b, 600)
    capas = []
    for rama, s in zip(ramas, derivadas):
        xs_rama = np.broadcast_to(muestreo.funcion(rama, [mu])(valores), valores.shape)
        ss = np.broadcast_to(muestreo.funcion(s, [mu])(valores), valores.shape)
        for rol, mascara in (("rama:estable", ss < 0), ("rama:inestable", ss > 0)):
            ys = np.where(mascara & np.isfinite(xs_rama), xs_rama, np.nan)
            mx, my = muestreo._cortar(valores, ys, salto=1e9)
            if any(v is not None for v in my):
                capas.append({"tipo": "linea", "rol": rol,
                              "nombre": f"{x}* = {sp.sstr(rama)} ({'estable' if rol.endswith(':estable') else 'inestable'})",
                              "x": mx, "y": my})
    alto = [v for c in capas for v in c["y"] if v is not None]
    y_min = min(alto) if alto else -1.0
    y_max = max(alto) if alto else 1.0
    margen = 0.25 * max(y_max - y_min, 1.0)
    flecha_x, flecha_y, sentido = [], [], []
    for m in np.linspace(a + 0.08 * (b - a), b - 0.08 * (b - a), 7):
        for xv in np.linspace(y_min - 0.6 * margen, y_max + 0.6 * margen, 9):
            valor = float(np.real(muestreo.funcion(f, [x, mu])(np.array(xv), np.array(m))))
            if np.isfinite(valor) and abs(valor) > 1e-9:
                flecha_x.append(float(m))
                flecha_y.append(float(xv))
                sentido.append(valor > 0)
    capas.append({"tipo": "puntos", "rol": "crece", "nombre": f"{x}' > 0",
                  "x": [p for p, s in zip(flecha_x, sentido) if s], "y": [q for q, s in zip(flecha_y, sentido) if s],
                  "simbolo": "triangle-up"})
    capas.append({"tipo": "puntos", "rol": "decrece", "nombre": f"{x}' < 0",
                  "x": [p for p, s in zip(flecha_x, sentido) if not s],
                  "y": [q for q, s in zip(flecha_y, sentido) if not s], "simbolo": "triangle-down"})
    for clase in clases:
        capas.append({"tipo": "puntos", "rol": "critico", "nombre": f"{clase['tipo']} ({mu} = {sp.sstr(clase['mu_c'])})",
                      "x": [float(clase["mu_c"])], "y": [float(clase["x_c"])]})
    if d.resultados.get("biestabilidad") is not None:
        zona = d.resultados["biestabilidad"]
        capas.insert(0, {"tipo": "banda", "rol": "region", "nombre": "Biestabilidad",
                         "x0": float(zona.inf), "x1": float(zona.sup)})
    d.grafica({"clave": "diagrama_bifurcacion", "titulo": "Diagrama de bifurcación",
               "ejes": {"x": sp.pretty(mu), "y": f"{x}*"},
               "rango": {"x": [a, b], "y": [y_min - margen, y_max + margen]}, "capas": capas})


# ---------------------------------------------------------------------------
# Equilibrios de una ecuación escalar autónoma: la línea de fase
# ---------------------------------------------------------------------------

#: Ventana donde se estudian los equilibrios cuando f tiene infinitos ceros (sen x).
VENTANA_1D = (-10, 10)

#: Hasta qué derivada se busca la primera no nula en un equilibrio no hiperbólico.
ORDEN_MAXIMO_1D = 5


def identificar_equilibrios_1d(problema):
    """ẋ = f(x) autónoma, con los parámetros fijados y sin condición inicial.

    Es la pregunta "¿cuáles son los equilibrios y cómo son?", que el balotario
    responde en cada régimen de 3.1–3.3 con el parámetro ya fijado. Con
    condición inicial, o si se pide la solución general, lo que se pregunta es
    resolver la ecuación, y eso lo hace su familia del Tema 1.
    """
    if problema.tipo != "edo" or problema.dimension != 1 or not problema.autonomo:
        return None
    if problema.tiene_parametro or problema.ci is not None or "solucion_general" in problema.pedidos:
        return None
    return {}


def desarrollar_equilibrios_1d(problema, datos=None) -> Desarrollo:
    if identificar_equilibrios_1d(problema) is None:
        raise MetodoNoAplicable("Hace falta una ecuación escalar autónoma ẋ = f(x), sin parámetro "
                                "simbólico ni condición inicial.")
    x = problema.estados[0]
    f = sp.sympify(problema.campo[0])
    d = Desarrollo("equilibrios_1d", "Equilibrios y línea de fase", TEMA,
                   "Ceros de f, estabilidad lineal con f'(x*) y signo de f entre equilibrios",
                   tratamiento=["analitico", "cualitativo"], balotario=["3.1", "3.2", "3.3"])
    inferior, superior = problema.region.get(x, (None, None))
    dominio = sp.Interval(sp.S.NegativeInfinity if inferior is None else exacto(inferior),
                          sp.S.Infinity if superior is None else exacto(superior))
    try:
        continuo = continuous_domain(f, x, dominio)
    except (NotImplementedError, ValueError, TypeError):
        continuo = dominio

    # --- 1. Equilibrios: f(x*) = 0 ------------------------------------------------
    seccion = d.seccion("equilibrios", "Puntos de equilibrio")
    factorizada = sp.factor(f)
    if sp.srepr(factorizada) != sp.srepr(f):
        seccion.formula(rf"f({L(x)}) = {L(f)}", "=", factorizada, "= 0")
    else:
        seccion.formula(rf"f({L(x)}) = {L(f)} = 0")
    ceros = sp.solveset(f, x, continuo)
    en_ventana = False
    if not isinstance(ceros, (sp.FiniteSet, sp.EmptySet.__class__)):
        general = ceros
        ventana = sp.Interval(*VENTANA_1D)
        ceros = sp.solveset(f, x, continuo.intersect(ventana))
        if not isinstance(ceros, (sp.FiniteSet, sp.EmptySet.__class__)):
            raise MetodoNoAplicable(f"Los ceros de f = {sp.sstr(f)} no se pueden obtener de forma exacta.")
        if not isinstance(general, sp.ConditionSet):
            seccion.formula(rf"{L(x)}^* \in {L(general)}")
        seccion.texto(f"f tiene infinitos ceros: se estudian los de la ventana "
                      f"[{VENTANA_1D[0]}, {VENTANA_1D[1]}].")
        dominio = dominio.intersect(ventana)
        continuo = continuo.intersect(ventana)
        en_ventana = True
    equilibrios = sorted(ceros, key=lambda c: float(sp.N(c)))
    d.validar("equilibrios_anulan_el_campo", all(sp.simplify(f.subs(x, c)) == 0 for c in equilibrios),
              "Cada equilibrio sustituido en f da 0 exactamente.")
    if equilibrios:
        seccion.formula(rf"{L(x)}^* \in \left\{{{L(equilibrios)}\right\}}", destacada=True, ref="equilibrios")
    else:
        seccion.formula(rf"f({L(x)}) \neq 0 \text{{ en todo el dominio}}", r"\implies",
                        rf"\nexists\, {L(x)}^*", destacada=True)

    # --- 2. Estabilidad lineal: signo de f'(x*) ----------------------------------------
    clasificados = []
    if equilibrios:
        fx = sp.diff(f, x)
        seccion = d.seccion("estabilidad", "Análisis de estabilidad lineal")
        seccion.formula(rf"f'({L(x)})", "=", fx, ref="derivada")
        d.guardar("derivada", fx)
        for punto in equilibrios:
            derivadas = [sp.simplify(sp.diff(f, x, k).subs(x, punto)) for k in range(1, ORDEN_MAXIMO_1D + 1)]
            tipo, estabilidad, hiperbolico, orden = clasificar_1d(derivadas)
            palabra = {"atractor": "asintóticamente estable (atractor)",
                       "repulsor": "inestable (repulsor)"}.get(tipo, f"{tipo}, {estabilidad}")
            seccion.formula(rf"f'({L(punto)}) = {L(derivadas[0])} {_rel(derivadas[0])} 0",
                            r"\implies", rf"\text{{{palabra}}}" if hiperbolico else
                            r"\text{no hiperbólico}", destacada=hiperbolico)
            if not hiperbolico and orden <= len(derivadas):
                seccion.formula(rf"f^{{({orden})}}({L(punto)}) = {L(derivadas[orden - 1])}", r"\implies",
                                rf"\text{{{palabra}}}", destacada=True)
            clasificados.append({"punto": punto, "derivada": derivadas[0], "tipo": tipo,
                                 "estabilidad": estabilidad, "hiperbolico": hiperbolico, "orden": orden})
        d.guardar("equilibrios", clasificados)

    # --- 3. Línea de fase: signo de f entre equilibrios ------------------------------------
    cortes = sorted({*equilibrios, *(e for I in _intervalos(continuo)
                                     for e in (I.inf, I.sup) if e.is_finite)}, key=lambda c: float(sp.N(c)))
    extremos = [dominio.inf, *[c for c in cortes if dominio.inf < c < dominio.sup], dominio.sup]
    seccion = d.seccion("linea_fase", "Línea de fase")
    tramos, filas = [], []
    for a, b in zip(extremos, extremos[1:]):
        tramo = sp.Interval.open(a, b)
        prueba = _prueba_en(tramo)
        if prueba not in continuo:
            continue
        s = signo(f.subs(x, prueba))
        sentido = "crece" if s == 1 else "decrece" if s == -1 else "indefinido"
        tramos.append({"intervalo": tramo, "signo": s, "sentido": sentido})
        flecha = {1: " (→)", -1: " (←)"}.get(s, "")
        filas.append([tramo, F(rf"f {_rel(f.subs(x, prueba))} 0"), f"{x} {sentido}{flecha}"])
    seccion.tabla(["Intervalo", "Signo de f", "Sentido del flujo"], filas)
    d.guardar("linea_de_fase", tramos)

    # La línea de fase decide la estabilidad sin linealizar: estable si el flujo
    # llega desde los dos lados. Es una comprobación independiente de f'(x*).
    coherente = True
    for c in clasificados:
        izquierda = next((t for t in tramos if t["intervalo"].sup == c["punto"]), None)
        derecha = next((t for t in tramos if t["intervalo"].inf == c["punto"]), None)
        llega_izq = izquierda is None or izquierda["signo"] == 1
        llega_der = derecha is None or derecha["signo"] == -1
        c["por_linea_de_fase"] = ("estable" if llega_izq and llega_der else
                                  "inestable" if not llega_izq and not llega_der else "semiestable")
        esperado = {"atractor": "estable", "atractor no hiperbólico": "estable", "repulsor": "inestable",
                    "repulsor no hiperbólico": "inestable", "semiestable": "semiestable"}.get(c["tipo"])
        if esperado is not None:
            coherente &= c["por_linea_de_fase"] == esperado
        if c["por_linea_de_fase"] == "estable":
            a = izquierda["intervalo"].inf if izquierda is not None else c["punto"]
            b = derecha["intervalo"].sup if derecha is not None else c["punto"]
            # En una ventana, un extremo de la ventana no es el borde de la cuenca.
            if not (en_ventana and (a == dominio.inf or b == dominio.sup)):
                c["cuenca"] = sp.Interval.open(a, b)
    d.validar("linea_de_fase_coherente", coherente,
              "El signo de f a cada lado de cada equilibrio confirma la estabilidad que dan las derivadas "
              "en x*: el flujo llega desde ambos lados a los atractores, sale de los repulsores y "
              "atraviesa los semiestables.")

    for c in clasificados:
        texto = f"{x}* = {sp.sstr(c['punto'])}: {c['estabilidad']}"
        if c["tipo"] not in c["estabilidad"]:
            texto += f" ({c['tipo']})"
        if not c["hiperbolico"]:
            texto += (f"; f'({sp.sstr(c['punto'])}) = 0 y la primera derivada no nula es la de orden "
                      f"{c['orden']}")
        if c.get("cuenca") is not None:
            texto += f"; atrae a toda solución que empieza en {intervalo_texto(c['cuenca'])}"
        d.concluir(texto + ".")
    if not equilibrios and tramos:
        d.concluir(f"No hay equilibrios: f no cambia de signo y {x} {tramos[0]['sentido']} monótonamente.")
    _grafica_linea_de_fase(d, f, x, clasificados, dominio)
    return d


def _grafica_linea_de_fase(d, f, x, clasificados, dominio):
    valores = [float(sp.N(c["punto"])) for c in clasificados]
    if valores:
        ancho = max(max(valores) - min(valores), 2.0)
        a, b = min(valores) - 0.35 * ancho, max(valores) + 0.35 * ancho
    else:
        a, b = -3.0, 3.0
    if dominio.inf.is_finite:
        a = max(a, float(dominio.inf))
    if dominio.sup.is_finite:
        b = min(b, float(dominio.sup))
    xs, ys = muestreo.curva(f, x, a, b)
    capas = [{"tipo": "linea", "rol": "serie:0", "nombre": f"f({x}) = {sp.sstr(f)}", "x": xs, "y": ys}]
    flechas = np.linspace(a, b, 25)
    signos = muestreo.funcion(f, [x])(flechas)
    for rol, mascara, simbolo, nombre in (("crece", signos > 0, "triangle-right", f"f > 0: {x} crece"),
                                          ("decrece", signos < 0, "triangle-left", f"f < 0: {x} decrece")):
        capas.append({"tipo": "puntos", "rol": rol, "nombre": nombre, "simbolo": simbolo,
                      "x": flechas[mascara].tolist(), "y": [0.0] * int(mascara.sum())})
    for c in clasificados:
        estado = ("estable" if c["tipo"] == "atractor" else "inestable" if c["tipo"] == "repulsor"
                  else "indefinido")
        capas.append({"tipo": "puntos", "rol": f"equilibrio:{estado}",
                      "nombre": f"{x}* = {sp.sstr(c['punto'])} ({c['estabilidad']})",
                      "x": [float(sp.N(c["punto"]))], "y": [0.0]})
    d.grafica({"clave": "linea_fase", "titulo": "Línea de fase", "ejes": {"x": str(x), "y": f"f({x})"},
               "rango": {"x": [a, b], "y": muestreo.rango_vertical(capas)}, "capas": capas})


# ---------------------------------------------------------------------------
# Hopf (3.4)
# ---------------------------------------------------------------------------

def coeficiente_lyapunov(f, g, u, w, omega):
    """Primer coeficiente de Lyapunov (Guckenheimer–Holmes) en la forma canónica.

    Para u' = −ωw + f(u, w), w' = ωu + g(u, w):
    a = (1/16)[f_uuu + f_uww + g_uuw + g_www]
        + (1/(16ω))[f_uw(f_uu + f_ww) − g_uw(g_uu + g_ww) − f_uu g_uu + f_ww g_ww].
    a < 0: Hopf supercrítica; a > 0: subcrítica.
    """
    def d(expresion, *variables):
        return sp.diff(expresion, *variables).subs({u: 0, w: 0})
    cubico = d(f, u, u, u) + d(f, u, w, w) + d(g, u, u, w) + d(g, w, w, w)
    cuadratico = (d(f, u, w) * (d(f, u, u) + d(f, w, w)) - d(g, u, w) * (d(g, u, u) + d(g, w, w))
                  - d(f, u, u) * d(g, u, u) + d(f, w, w) * d(g, w, w))
    return sp.simplify(cubico / 16 + cuadratico / (16 * omega)), {"cubico": cubico, "cuadratico": cuadratico}


def forma_canonica(campo, estados, punto, J0):
    """Cambio lineal que lleva J0 a [[0, −ω], [ω, 0]] y las no linealidades en esas coordenadas."""
    u, w = sp.symbols("u w", real=True)
    for valor, _, vectores in J0.eigenvects():
        if sp.im(valor) > 0:
            omega = sp.im(valor)
            v = vectores[0]
            break
    else:
        return None
    parte_real = v.applyfunc(sp.re)
    parte_imag = v.applyfunc(sp.im)
    P = sp.Matrix.hstack(parte_imag, parte_real)
    desplazado = sp.Matrix(punto) + P * sp.Matrix([u, w])
    sustitucion = dict(zip(estados, desplazado))
    no_lineal = P.inv() * (sp.Matrix(campo).subs(sustitucion, simultaneous=True) - J0 * P * sp.Matrix([u, w]))
    no_lineal = no_lineal.applyfunc(sp.expand)
    return {"P": P, "omega": sp.simplify(omega), "u": u, "w": w, "f": no_lineal[0], "g": no_lineal[1],
            "canonica": sp.simplify(P.inv() * J0 * P)}


def identificar_hopf(problema):
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo or not problema.tiene_parametro:
        return None
    candidatos = _candidatos_hopf(problema)
    return {"candidatos": candidatos} if candidatos else None


def _candidatos_hopf(problema):
    x, y = problema.estados
    mu = problema.parametro
    campo = [sp.sympify(e) for e in problema.campo]
    equilibrios, _ = buscar_equilibrios(campo, [x, y])
    J = sp.Matrix(campo).jacobian([x, y])
    candidatos = []
    for e in equilibrios:
        matriz = J.subs({x: e.punto[0], y: e.punto[1]}).applyfunc(sp.simplify)
        tau, delta = sp.simplify(matriz.trace()), sp.simplify(matriz.det())
        if not tau.has(mu):
            continue
        for mu_c in sp.solveset(tau, mu, domain=sp.S.Reals):
            if not mu_c.is_number:
                continue
            delta_c = sp.simplify(delta.subs(mu, mu_c))
            if signo(delta_c) == 1:
                candidatos.append({"punto": e.punto, "mu_c": mu_c, "matriz": matriz,
                                   "traza": tau, "determinante": delta})
    return candidatos


def desarrollar_hopf(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_hopf(problema)
    if not datos:
        raise MetodoNoAplicable("No hay un equilibrio cuya traza se anule con determinante positivo: "
                                "no hay bifurcación de Hopf.")
    x, y = problema.estados
    mu = problema.parametro
    f, g = (sp.sympify(e) for e in problema.campo)
    candidato = datos["candidatos"][0]
    punto, mu_c = candidato["punto"], candidato["mu_c"]
    d = Desarrollo("hopf", "Bifurcación de Hopf", TEMA,
                   "Condiciones espectral y de transversalidad, forma polar y coeficiente de Lyapunov",
                   tratamiento=["analitico", "cualitativo", "numerico"], balotario=["3.4"])
    lam = sp.Symbol("lambda")

    seccion = d.seccion("linealizacion", f"Linealización en ${punto_latex(punto)}$ y condiciones de Hopf")
    J = sp.Matrix([f, g]).jacobian([x, y])
    seccion.formula(rf"J({L(x)}, {L(y)}) = {_pmatrix(J.applyfunc(sp.expand))}")
    matriz = candidato["matriz"]
    seccion.formula(rf"J{punto_latex(punto)} = {_pmatrix(matriz)}", destacada=True)
    polinomio = sp.expand((matriz - lam * sp.eye(2)).det())
    autovalores = sp.solve(polinomio, lam)
    alfa = sp.simplify(candidato["traza"] / 2)
    omega = sp.simplify(sp.sqrt(candidato["determinante"] - alfa ** 2))
    seccion.rotulo(r"\text{Ecuación característica y autovalores}")
    seccion.formula(rf"\det(J - \lambda I) = {L(sp.factor(polinomio))} = 0 \implies "
                    rf"\lambda_{{1,2}}({L(mu)}) = {L(alfa)} \pm {L(omega * sp.I)} = \alpha({L(mu)}) \pm i\omega({L(mu)})")
    seccion.formula(rf"\alpha({L(mu)}) = \mathrm{{Re}}(\lambda) = {L(alfa)},\qquad "
                    rf"\omega({L(mu)}) = \mathrm{{Im}}(\lambda) = {L(omega)}", destacada=True)
    omega_c = sp.simplify(omega.subs(mu, mu_c))
    seccion.rotulo(r"\text{Condición espectral en } " + rf"{L(mu)}_c = {L(mu_c)}")
    seccion.formula(rf"\alpha({L(mu_c)}) = 0,\qquad \omega({L(mu_c)}) = \omega_0 = {L(omega_c)} \neq 0 "
                    rf"\implies \lambda_{{1,2}}({L(mu_c)}) = \pm {L(omega_c * sp.I)}", destacada=True)
    transversal = sp.simplify(sp.diff(alfa, mu).subs(mu, mu_c))
    seccion.rotulo(r"\text{Condición de transversalidad}")
    seccion.formula(rf"\left.\frac{{d\alpha}}{{d{L(mu)}}}\right|_{{{L(mu)} = {L(mu_c)}}} = {L(transversal)} "
                    rf"{_rel(transversal)} 0", destacada=True)
    d.guardar("punto", punto)
    d.guardar("mu_critico", mu_c)
    d.guardar("alfa", alfa)
    d.guardar("omega", omega)
    d.guardar("transversalidad", transversal)
    d.validar("condicion_espectral", omega_c != 0 and sp.simplify(alfa.subs(mu, mu_c)) == 0,
              "En μc los autovalores son imaginarios puros no nulos.")
    d.validar("condicion_transversalidad", transversal != 0, "α'(μc) ≠ 0: el par cruza el eje imaginario.")

    # --- Forma polar: exacta si el sistema es rotacionalmente simétrico ----------
    desplazado = [e.subs({x: x + punto[0], y: y + punto[1]}, simultaneous=True) for e in (f, g)]
    r_punto, theta_punto, _, _ = forma_polar(*desplazado, x, y)
    r, th = R_POLAR, THETA
    simetrico = not r_punto.has(th) and not theta_punto.has(r)
    radio = None
    if simetrico:
        r_punto, theta_punto, _, _ = seccion_polar(d, *desplazado, x, y,
                                                    titulo="Transformación canónica a coordenadas polares")
        seccion = d.seccion("ciclo", "Existencia, radio y estabilidad del ciclo límite")
        # Del lado donde el equilibrio es estable, ṙ < 0 para todo r > 0: el
        # equilibrio atrae todo (lo que el balotario escribe para μ ≤ 0).
        antes = (_prueba_en(sp.Interval(-sp.oo, mu_c)) if signo(transversal) == 1
                 else _prueba_en(sp.Interval(mu_c, sp.oo)))
        if all(signo(sp.simplify(r_punto.subs(mu, antes).subs(r, v))) == -1
               for v in (sp.Rational(1, 10), 1, 5)):
            lado = r"\le" if signo(transversal) == 1 else r"\ge"
            seccion.formula(rf"{L(mu)} {lado} {L(mu_c)}:\quad \dot{{r}} = {L(sp.factor_terms(r_punto))} < 0\quad "
                            r"\forall r > 0 \implies \text{el equilibrio es el único atractor (foco estable)}",
                            destacada=True)
        raices = [v for v in sp.solve(sp.simplify(r_punto / r), r) if v != 0]
        if raices:
            radio = sp.simplify(raices[0])
            existe = dominio_real(radio, mu)
            seccion.formula(rf"\dot{{r}} = 0 \iff {L(sp.factor_terms(r_punto))} = 0 \implies R({L(mu)}) = {L(radio)}"
                            rf"\quad ({_texto_rango(existe, mu)})", destacada=True, ref="radio_ciclo")
            derivada = sp.diff(r_punto, r)
            en_ciclo = sp.simplify(derivada.subs(r, radio))
            seccion.formula(rf"\left.\frac{{d\dot{{r}}}}{{dr}}\right|_{{r = R}} = \left.{L(derivada)}\right|"
                            rf"_{{r={L(radio)}}} = {L(en_ciclo)}")
            prueba = _prueba_en(_intervalos(existe)[0])
            estable = signo(en_ciclo.subs(mu, prueba)) == -1
            seccion.formula(rf"R({L(mu)}) = {L(radio)} \implies \text{{ciclo límite "
                            rf"{'asintóticamente estable (atractor)' if estable else 'inestable (repulsor)'}}}",
                            destacada=True)
            d.guardar("radio_ciclo", radio)
            d.guardar("ciclo_estable", estable)
            d.guardar("existe_ciclo_para", existe)
            if not theta_punto.has(th):
                periodo = sp.simplify(sp.integrate(1 / theta_punto, (th, 0, 2 * sp.pi)))
                seccion.formula(rf"T = \int_0^{{2\pi}} \frac{{d\theta}}{{\dot{{\theta}}}} = {L(periodo)}",
                                destacada=True, ref="periodo")
                d.guardar("periodo", periodo)

    # --- Coeficiente de Lyapunov --------------------------------------------------
    J0 = matriz.subs(mu, mu_c)
    canonica = forma_canonica([e.subs(mu, mu_c) for e in (f, g)], [x, y], punto, J0)
    if canonica is not None:
        a, partes = coeficiente_lyapunov(canonica["f"], canonica["g"], canonica["u"], canonica["w"],
                                         canonica["omega"])
        seccion = d.seccion("lyapunov", "Primer coeficiente de Lyapunov y tipo de Hopf")
        if canonica["P"] != sp.eye(2):
            seccion.formula(rf"\mathbf{{x}} = {punto_latex(punto)} + P\begin{{pmatrix}} u \\ w \end{{pmatrix}},\quad "
                            rf"P = {_pmatrix(canonica['P'])},\quad P^{{-1}}J_0P = {_pmatrix(canonica['canonica'])}")
        seccion.formula(rf"\dot u = {suma((-canonica['omega'], canonica['w']), canonica['f'])},\qquad "
                        rf"\dot w = {suma((canonica['omega'], canonica['u']), canonica['g'])}")
        seccion.formula(r"a = \tfrac{1}{16}\left[f_{uuu} + f_{uww} + g_{uuw} + g_{www}\right] + "
                        r"\tfrac{1}{16\omega}\left[f_{uw}(f_{uu} + f_{ww}) - g_{uw}(g_{uu} + g_{ww}) - "
                        r"f_{uu}g_{uu} + f_{ww}g_{ww}\right]")
        seccion.formula(rf"a = \tfrac{{1}}{{16}}\left({L(partes['cubico'])}\right) + "
                        rf"\tfrac{{1}}{{16 \cdot {L(canonica['omega'])}}}\left({L(partes['cuadratico'])}\right) = {L(a)}",
                        destacada=True, ref="coeficiente_lyapunov")
        tipo = "supercrítica" if signo(a) == -1 else "subcrítica" if signo(a) == 1 else "degenerada"
        lado = "μ > μc" if signo(transversal) == 1 else "μ < μc"
        seccion.formula(rf"a {_rel(a)} 0 \implies \text{{la bifurcación de Hopf es {tipo}}}", destacada=True)
        d.guardar("coeficiente_lyapunov", a)
        d.guardar("tipo_hopf", tipo)
        if radio is None and signo(a) != 0:
            aproximado = sp.sqrt(-transversal * (mu - mu_c) / a)
            seccion.formula(rf"R({L(mu)}) \approx \sqrt{{-\frac{{\alpha'({L(mu_c)})}}{{a}}({L(mu)} - {L(mu_c)})}} = {L(aproximado)}",
                            r"\quad (\text{forma normal, cerca de } \mu_c)")
            seccion.formula(rf"T \approx \frac{{2\pi}}{{\omega_0}} = {L(2 * sp.pi / omega_c)}")
            d.guardar("radio_aproximado", aproximado)
        if tipo == "supercrítica":
            d.concluir(f"Hopf supercrítica en {mu} = {sp.sstr(mu_c)}: el equilibrio pierde estabilidad y "
                       f"nace un ciclo límite estable para {lado}, cuya amplitud crece desde cero.")
        elif tipo == "subcrítica":
            d.concluir(f"Hopf subcrítica en {mu} = {sp.sstr(mu_c)}: el ciclo que se une al equilibrio es "
                       "inestable y existe del lado donde el equilibrio todavía es estable.")
    _validar_y_graficar_hopf(d, problema, punto, mu_c, radio)
    return d


def _validar_y_graficar_hopf(d, problema, punto, mu_c, radio):
    x, y = problema.estados
    mu = problema.parametro
    transversal = d.resultados.get("transversalidad", 1)
    supercritica = d.resultados.get("tipo_hopf") == "supercrítica"
    lado = 1 if signo(transversal) == 1 else -1
    if not supercritica:
        lado = -lado
    mu_ciclo = float(mu_c) + lado * 0.5
    mu_sin = float(mu_c) - lado * 0.5
    centro = [float(sp.N(c)) for c in punto]
    capas_diagrama = []
    valores = np.linspace(float(mu_c) - 1.5, float(mu_c) + 1.5, 300)
    estable_antes = signo(sp.diff(d.resultados["alfa"], mu).subs(mu, mu_c)) == 1
    izquierda = valores <= float(mu_c)
    capas_diagrama.append({"tipo": "linea", "rol": "rama:estable" if estable_antes else "rama:inestable",
                           "nombre": "Equilibrio", "x": valores[izquierda].tolist(), "y": [0.0] * int(izquierda.sum())})
    capas_diagrama.append({"tipo": "linea", "rol": "rama:inestable" if estable_antes else "rama:estable",
                           "nombre": "Equilibrio", "x": valores[~izquierda].tolist(), "y": [0.0] * int((~izquierda).sum())})
    amplitud = radio if radio is not None else d.resultados.get("radio_aproximado")
    if amplitud is not None:
        rs = np.broadcast_to(muestreo.funcion(amplitud, [mu])(valores), valores.shape)
        rol = "rama:estable" if d.resultados.get("ciclo_estable", supercritica) else "rama:inestable"
        for s in (1, -1):
            mx, my = muestreo._cortar(valores, s * rs, salto=1e9)
            capas_diagrama.append({"tipo": "linea", "rol": rol, "nombre": "Amplitud del ciclo R(μ)",
                                   "x": mx, "y": my})
    capas_diagrama.append({"tipo": "puntos", "rol": "critico", "nombre": f"Hopf ({mu} = {sp.sstr(mu_c)})",
                           "x": [float(mu_c)], "y": [0.0]})
    d.grafica({"clave": "diagrama_bifurcacion", "titulo": "Diagrama de bifurcación de Hopf",
               "ejes": {"x": sp.pretty(mu), "y": "amplitud"}, "capas": capas_diagrama})

    for valor, clave, titulo in ((mu_sin, "retrato_antes", "antes"), (mu_ciclo, "retrato_despues", "después")):
        campo = [sp.sympify(e).subs(mu, valor) for e in problema.campo]
        f = muestreo.campo_plano(campo, [x, y])
        escala = max(1.0, 1.6 * float(sp.N(amplitud.subs(mu, mu_ciclo)))) if amplitud is not None else 1.5
        caja = ((centro[0] - escala, centro[0] + escala), (centro[1] - escala, centro[1] + escala))
        semillas = [(centro[0] + 0.05, centro[1]), (centro[0] + 0.95 * escala, centro[1])]
        capas = [muestreo.campo_de_direcciones(f, caja)]
        for i, semilla in enumerate(semillas):
            orbita = muestreo.trayectoria(f, semilla, 40.0, caja, maximo_puntos=1200)
            if orbita:
                capas.append({"tipo": "linea", "rol": "trayectoria" if i == 0 else "orbita",
                              "nombre": f"Desde ({semilla[0]:.2f}, {semilla[1]:.2f})", "x": orbita["x"], "y": orbita["y"]})
        if amplitud is not None and clave == "retrato_despues":
            R = float(sp.N(amplitud.subs(mu, valor)))
            angulos = np.linspace(0, 2 * np.pi, 200)
            capas.append({"tipo": "linea", "rol": "ciclo", "nombre": f"Ciclo r = {R:.4g}",
                          "x": (centro[0] + R * np.cos(angulos)).tolist(),
                          "y": (centro[1] + R * np.sin(angulos)).tolist()})
            # Un ciclo inestable (Hopf subcrítica) atrae en tiempo inverso.
            estable = d.resultados.get("ciclo_estable", supercritica)
            final = muestreo.trayectoria(f, [centro[0] + 0.05, centro[1]], 200.0 if estable else -200.0)
            if final:
                radio_final = math.dist(final["estado_final"], centro)
                sentido = "" if estable else " hacia atrás en el tiempo (el ciclo es inestable)"
                d.validar("radio_del_ciclo_numerico", abs(radio_final - R) < 1e-3 * max(1.0, R),
                          f"Integrando con {mu} = {valor:g} desde cerca del equilibrio{sentido}, el radio "
                          f"converge a R = {R:.6g}.", medida=abs(radio_final - R), umbral=1e-3, tipo="numerica")
        capas.append({"tipo": "puntos", "rol": "equilibrio:indefinido", "nombre": "Equilibrio",
                      "x": [centro[0]], "y": [centro[1]]})
        d.grafica({"clave": clave, "titulo": f"Retrato de fase {titulo} de la bifurcación ({mu} = {valor:g})",
                   "ejes": {"x": x.name, "y": y.name}, "rango": {"x": list(caja[0]), "y": list(caja[1])},
                   "capas": capas, "cuadrada": True})


# ---------------------------------------------------------------------------
# Homoclínica (3.5)
# ---------------------------------------------------------------------------

def identificar_homoclinica(problema):
    """ẋ = y, ẏ = F(x) + g(x, y; μ) con g(x, 0; μ) = 0 y una silla con lazo homoclínico."""
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo or not problema.tiene_parametro:
        return None
    x, y = problema.estados
    mu = problema.parametro
    f, G = (sp.sympify(e) for e in problema.campo)
    if sp.simplify(f - y) != 0:
        return None
    F = sp.expand(G.subs(y, 0))
    if F.has(mu) or not F.has(x):
        return None
    perturbacion = sp.expand(G - F)
    if sp.simplify(perturbacion.subs(y, 0)) != 0:
        return None
    return {"F": F, "g": perturbacion}


def desarrollar_homoclinica(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_homoclinica(problema)
    if datos is None:
        raise MetodoNoAplicable("El sistema no tiene la forma ẋ = y, ẏ = F(x) + g(x, y; μ) con g(x, 0; μ) = 0.")
    x, y = problema.estados
    mu = problema.parametro
    f, G = (sp.sympify(e) for e in problema.campo)
    F, g = datos["F"], datos["g"]
    d = Desarrollo("homoclinica", "Bifurcación homoclínica de silla", TEMA,
                   "Lazo homoclínico no perturbado, integral de Melnikov y disparo numérico",
                   tratamiento=["analitico", "cualitativo", "numerico"], balotario=["3.5"])

    # --- 1. Equilibrios y clasificación según μ ----------------------------------
    equilibrios = seccion_equilibrios(d, f, G, x, y, problema.region)
    J = seccion_jacobiano(d, f, G, x, y)
    clasificados = seccion_clasificacion_parametrica(d, f, G, x, y, equilibrios, J, mu, problema)
    sillas = [c for c in clasificados if all(r.tipo == "punto silla" for r in c["regimenes"])]
    if not sillas:
        raise MetodoNoAplicable("Ningún equilibrio es silla para todo μ: no hay lazo homoclínico que romper.")
    silla = sillas[0]["punto"]
    # Hopf local en algún otro equilibrio: su tipo dice de qué lado vive el ciclo.
    hopf_local = None
    for c in clasificados:
        if c is sillas[0]:
            continue
        for regimen in c["regimenes"]:
            if regimen.es_punto and regimen.tipo == "centro":
                mu_h = next(iter(regimen.conjunto))
                J0 = J.subs({x: c["punto"][0], y: c["punto"][1], mu: mu_h})
                canonica = forma_canonica([e.subs(mu, mu_h) for e in (f, G)], [x, y], c["punto"], J0)
                if canonica is not None:
                    a, _ = coeficiente_lyapunov(canonica["f"], canonica["g"], canonica["u"], canonica["w"],
                                                canonica["omega"])
                    hopf_local = {"punto": c["punto"], "mu": mu_h, "a": a,
                                  "transversalidad": sp.diff(c["traza"] / 2, mu).subs(mu, mu_h)}
    if hopf_local is not None:
        seccion = d.seccion("hopf_local", f"Bifurcación de Hopf local en ${punto_latex(hopf_local['punto'])}$")
        tipo = "supercrítica" if signo(hopf_local["a"]) == -1 else "subcrítica"
        seccion.formula(rf"\mathrm{{Tr}}\,J = 0 \iff {L(mu)} = {L(hopf_local['mu'])},\qquad "
                        rf"a = {L(hopf_local['a'])} {_rel(hopf_local['a'])} 0 \implies \text{{Hopf {tipo}}}",
                        destacada=True)
        lado = ">" if signo(hopf_local["transversalidad"]) == 1 else "<"
        if tipo == "supercrítica":
            seccion.texto(f"Para {mu} {lado} {sp.sstr(hopf_local['mu'])} nace un ciclo límite estable alrededor "
                          f"de {hopf_local['punto']}.")
        d.guardar("hopf_local", hopf_local)

    # --- 2. Sistema no perturbado -------------------------------------------------
    seccion = d.seccion("no_perturbado", "Sistema hamiltoniano no perturbado")
    seccion.formula(rf"\dot{{{L(y)}}} = \underbrace{{{L(F)}}}_{{F({L(x)})}} + "
                    rf"\underbrace{{{L(sp.factor(g))}}}_{{g({L(x)}, {L(y)}; {L(mu)})}}")
    seccion.formula(rf"\dot{{{L(x)}}} = {L(y)},\qquad \dot{{{L(y)}}} = {L(F)}")
    V = sp.expand(-sp.integrate(F, x))
    H0 = sp.Rational(1, 2) * y ** 2 + V
    seccion.formula(rf"H({L(x)}, {L(y)})", "=", H0, r"= E = \text{cte}", destacada=True, ref="hamiltoniano")
    d.guardar("hamiltoniano", H0)
    d.guardar("perturbacion", g)

    # --- 3. Lazo homoclínico --------------------------------------------------------
    x_s = silla[0]
    energia = sp.simplify(H0.subs({x: x_s, y: 0}))
    cuadrado = sp.expand(2 * (energia - V))
    resto = sp.factor(sp.cancel(cuadrado / (x - x_s) ** 2))
    giros = [r for r in sp.solveset(sp.Eq(V, energia), x, domain=sp.S.Reals) if sp.simplify(r - x_s) != 0]
    if not giros:
        raise MetodoNoAplicable("El nivel de energía de la silla no tiene punto de retorno: no hay lazo homoclínico.")
    x_t = giros[0]
    resto = sp.expand(resto)
    y0 = (x - x_s) * sp.sqrt(resto)
    a_lazo, b_lazo = sorted((x_s, x_t), key=float)
    seccion = d.seccion("lazo", rf"Lazo homoclínico no perturbado ($H = {L(energia)}$)")
    seccion.formula(H0, "=", energia, r"\iff", rf"{L(y)}^2 = {L(sp.Mul((x - x_s) ** 2, resto, evaluate=False))}")
    seccion.formula(rf"{L(y)}_0({L(x)}) = \pm {L(y0)},\qquad {L(x)} \in \left[{L(a_lazo)},\, {L(b_lazo)}\right]",
                    destacada=True, ref="lazo_homoclinico")
    centro = [c for c in sp.solveset(F, x, domain=sp.Interval(a_lazo, b_lazo)) if sp.simplify(c - x_s) != 0]
    if centro:
        altura = sp.simplify(y0.subs(x, centro[0]))
        seccion.formula(rf"{L(x)}_{{\mathrm{{vértice}}}} = {L(x_t)},\qquad {L(y)}_{{\max}} = \pm {L(sp.Abs(altura))} "
                        rf"\approx {float(sp.N(sp.Abs(altura))):.4g}\quad (\text{{en }} {L(x)} = {L(centro[0])})")
    d.guardar("lazo_homoclinico", y0)
    d.guardar("dominio_lazo", sp.Interval(a_lazo, b_lazo))

    # --- 4. Integral de Melnikov ------------------------------------------------------
    seccion = d.seccion("melnikov", "Integral de perturbación de Melnikov")
    seccion.formula(rf"g({L(x)}, {L(y)}; {L(mu)}) = {L(sp.factor(g))}")
    seccion.formula(rf"M({L(mu)}) = \int_{{-\infty}}^{{\infty}} {L(y)}_0(t)\, g\left({L(x)}_0(t), {L(y)}_0(t); {L(mu)}\right) dt "
                    rf"= \oint_{{\Gamma_0}} g\, d{L(x)}")
    integrando = sp.expand(g.subs(y, y0) - g.subs(y, -y0))
    M = sp.expand(sp.integrate(integrando, (x, a_lazo, b_lazo)))
    if signo(sp.sympify(x_t - x_s)) == -1:
        M = -M
    polinomio = sp.Poly(M, mu) if M.is_polynomial(mu) else None
    if polinomio is not None and polinomio.degree() == 1:
        I1, I2 = polinomio.coeff_monomial(mu), polinomio.coeff_monomial(1)
        coeficiente_mu = sp.expand(sp.diff(g, mu))
        resto_g = sp.expand(g - mu * coeficiente_mu)
        seccion.formula(rf"M({L(mu)}) = {L(mu)}\oint_{{\Gamma_0}} {L(coeficiente_mu)}\, d{L(x)} + "
                        rf"\oint_{{\Gamma_0}} {L(resto_g)}\, d{L(x)} = {L(mu)} I_1 + I_2")
        seccion.formula(rf"I_1 = 2\int_{{{L(a_lazo)}}}^{{{L(b_lazo)}}} {L(sp.expand(coeficiente_mu.subs(y, y0)))}\, d{L(x)} = {L(I1)}",
                        destacada=True, ref="I1")
        seccion.formula(rf"I_2 = 2\int_{{{L(a_lazo)}}}^{{{L(b_lazo)}}} {L(sp.expand(resto_g.subs(y, y0)))}\, d{L(x)} = {L(I2)}",
                        destacada=True, ref="I2")
        d.guardar("I1", I1)
        d.guardar("I2", I2)
    seccion.formula(rf"M({L(mu)}) = {L(M)}", destacada=True, ref="melnikov")
    d.guardar("melnikov", M)
    ceros = [c for c in sp.solve(M, mu) if c.is_real]
    if not ceros:
        d.advertir("La función de Melnikov no se anula: no hay valor crítico de primer orden.")
        return d
    mu_m = sp.nsimplify(ceros[0])
    seccion.formula(rf"M({L(mu)}_c) = 0 \implies {L(mu)}_c = {L(mu_m)} \approx {float(mu_m):.5g}", destacada=True,
                    ref="mu_melnikov")
    seccion.texto("El método de Melnikov supone que la perturbación es pequeña. Aquí g no lleva un factor "
                  "ε pequeño, así que este valor es una estimación de primer orden: se contrasta abajo con "
                  "un cálculo numérico directo de la conexión homoclínica.")
    d.guardar("mu_melnikov", mu_m)

    # --- 5. Disparo numérico y mecanismo ---------------------------------------------
    resultado = _disparo_homoclinico(problema, silla, centro[0] if centro else x_t, float(mu_m))
    seccion = d.seccion("disparo", "Verificación numérica: disparo sobre las variedades de la silla")
    seccion.texto("Se integra la variedad inestable de la silla hacia adelante y la estable hacia atrás "
                  "hasta su primer cruce con y = 0 más allá del centro; la diferencia d(μ) entre ambos "
                  "cruces se anula exactamente cuando las variedades se conectan.")
    if resultado is None:
        seccion.texto("El disparo no encontró un cambio de signo de d(μ) cerca de la estimación de Melnikov.")
        d.advertir("No se pudo localizar numéricamente la conexión homoclínica.")
    else:
        filas = [[f"{m:.4f}", f"{v:+.4f}"] for m, v in resultado["muestras"]]
        seccion.tabla([f"{mu}", "d(μ) = x_u − x_s"], filas)
        mu_n = resultado["mu"]
        seccion.formula(rf"d({L(mu)}^*) = 0 \implies {L(mu)}^* \approx {mu_n:.6f}", destacada=True, ref="mu_numerico")
        seccion.formula(rf"\left|{L(mu)}^* - {L(mu)}_c^{{\mathrm{{Melnikov}}}}\right| \approx {abs(mu_n - float(mu_m)):.2e}")
        d.guardar("mu_numerico", mu_n)
        d.validar("melnikov_vs_disparo", abs(mu_n - float(mu_m)) < 0.05,
                  "El cero de la función de Melnikov (primer orden) está cerca del valor numérico de la conexión.",
                  medida=abs(mu_n - float(mu_m)), umbral=0.05, tipo="numerica")
        _mecanismo(d, problema, resultado, silla, hopf_local, centro[0] if centro else None)
    _grafica_homoclinica(d, problema, H0, x, y, silla, resultado)
    return d


def _campo_numerico(problema, valor):
    campo = problema.campo_numerico(valor)
    return lambda t, s: campo(t, s)


def _separacion(problema, silla, mu_valor, x_seccion, eps=1e-7):
    """d(μ): diferencia entre los cruces de Wᵘ (adelante) y Wˢ (atrás) con y = 0, x > x_seccion."""
    x, y = problema.estados
    J = sp.Matrix(problema.campo_con(mu_valor)).jacobian([x, y]).subs({x: silla[0], y: silla[1]})
    valores, vectores = np.linalg.eig(np.array(J.evalf(), dtype=float))
    iu, is_ = int(np.argmax(valores.real)), int(np.argmin(valores.real))
    vu, vs = vectores[:, iu].real, vectores[:, is_].real
    if vu[0] < 0:
        vu = -vu
    if vs[0] < 0:
        vs = -vs
    f = _campo_numerico(problema, mu_valor)
    base = np.array([float(silla[0]), float(silla[1])])

    def cruce_bajando(t, s):
        return s[1]
    cruce_bajando.terminal, cruce_bajando.direction = True, -1

    def cruce_subiendo(t, s):
        return s[1]
    cruce_subiendo.terminal, cruce_subiendo.direction = True, 1

    def escapa(t, s):
        return 60.0 - abs(s[0]) - abs(s[1])
    escapa.terminal = True
    adelante = solve_ivp(f, (0, 200), base + eps * vu, events=[cruce_bajando, escapa], rtol=1e-11, atol=1e-13)
    atras = solve_ivp(f, (0, -200), base + eps * vs, events=[cruce_subiendo, escapa], rtol=1e-11, atol=1e-13)
    if not (adelante.t_events[0].size and atras.t_events[0].size):
        return None
    xu, xs = adelante.y_events[0][0][0], atras.y_events[0][0][0]
    if xu < x_seccion or xs < x_seccion:
        return None
    return float(xu - xs)


def _disparo_homoclinico(problema, silla, centro, mu_estimado):
    x_seccion = float(sp.N(centro))
    muestras = []
    for desplazamiento in (-0.3, -0.15, -0.05, 0.0, 0.05, 0.15, 0.3):
        valor = mu_estimado + desplazamiento
        separacion = _separacion(problema, silla, valor, x_seccion)
        if separacion is not None:
            muestras.append((valor, separacion))
    cambio = [(a, b) for a, b in zip(muestras[:-1], muestras[1:]) if a[1] * b[1] < 0]
    if not cambio:
        return None
    (m1, _), (m2, _) = cambio[0]
    raiz = brentq(lambda m: _separacion(problema, silla, m, x_seccion), m1, m2, xtol=1e-10)
    signo_antes = np.sign(next(v for m, v in muestras if m < raiz))
    return {"mu": float(raiz), "muestras": muestras, "signo_antes": int(signo_antes)}


def _mecanismo(d, problema, resultado, silla, hopf_local, centro):
    """De qué lado de μ* existe el ciclo, con evidencia numérica, y la divergencia del periodo."""
    x, y = problema.estados
    mu = problema.parametro
    mu_n = resultado["mu"]
    seccion = d.seccion("mecanismo", "Mecanismo de la bifurcación y divergencia del periodo")
    inicio = [float(sp.N(centro)) + 0.01, 0.0] if centro is not None else [0.5, 0.0]
    evidencias = {}
    for desplazamiento, etiqueta in ((-0.02, "antes"), (0.02, "despues")):
        valor = mu_n + desplazamiento
        f = _campo_numerico(problema, valor)

        def escapa(t, s):
            return 50.0 - abs(s[0]) - abs(s[1])
        escapa.terminal = True
        solucion = solve_ivp(f, (0, 400), inicio, events=escapa, rtol=1e-10, atol=1e-12, dense_output=True)
        if solucion.t_events[0].size:
            evidencias[etiqueta] = {"mu": valor, "escapa": True}
        else:
            tramo = solucion.sol(np.linspace(300, 400, 4000))
            evidencias[etiqueta] = {"mu": valor, "escapa": False,
                                    "amplitud": float(tramo[0].max() - tramo[0].min())}
    lado_ciclo = None
    for etiqueta, signo_texto in (("antes", "<"), ("despues", ">")):
        e = evidencias[etiqueta]
        if e["escapa"]:
            seccion.formula(rf"{L(mu)} = {e['mu']:.4f} {signo_texto} {L(mu)}^*: \text{{las órbitas escapan (no hay ciclo)}}")
        else:
            seccion.formula(rf"{L(mu)} = {e['mu']:.4f} {signo_texto} {L(mu)}^*: \text{{ciclo límite estable de amplitud }}"
                            rf"\approx {e['amplitud']:.3f}")
            lado_ciclo = signo_texto
    d.guardar("evidencia_ciclo", evidencias)
    if lado_ciclo is not None:
        texto_lado = f"{mu} {lado_ciclo} {mu_n:.4f}"
        conjunto = (sp.Interval.open(-sp.oo, sp.Float(mu_n, 8)) if lado_ciclo == "<"
                    else sp.Interval.open(sp.Float(mu_n, 8), sp.oo))
        origen = ""
        if hopf_local is not None:
            seccion.formula(rf"\text{{El ciclo nace en el Hopf de }} {L(mu)} = {L(hopf_local['mu'])} \text{{, crece y }}"
                            rf"\text{{choca con la silla en }} {L(mu)}^* \approx {mu_n:.4f}\text{{, donde se destruye}}",
                            destacada=True)
            mu_h = float(sp.N(hopf_local["mu"]))
            if (lado_ciclo == "<") == (mu_h < mu_n):
                # El ciclo vive entre el Hopf local que lo crea y la conexión que lo destruye.
                (_, menor), (_, mayor) = sorted([(mu_h, sp.sstr(hopf_local["mu"])), (mu_n, f"{mu_n:.4f}")])
                texto_lado = f"{menor} < {mu} < {mayor}"
                conjunto = conjunto.intersect(sp.Interval.open(hopf_local["mu"], sp.oo) if mu_h < mu_n
                                              else sp.Interval.open(-sp.oo, hopf_local["mu"]))
                origen = f"nace en el Hopf de {mu} = {sp.sstr(hopf_local['mu'])} y, "
        d.concluir(f"El ciclo límite estable existe para {texto_lado}: {origen}al acercarse a μ* ≈ {mu_n:.4f} "
                   "se convierte en el lazo homoclínico de la silla y desaparece; del otro lado de μ* las órbitas "
                   "escapan.")
        d.guardar("lado_del_ciclo", lado_ciclo)
        d.guardar("existe_ciclo_para", conjunto)
    # Divergencia logarítmica del periodo, medida del lado del ciclo.
    J = sp.Matrix(problema.campo_con(mu_n)).jacobian([x, y]).subs({x: silla[0], y: silla[1]})
    lambda_u = float(max(np.linalg.eigvals(np.array(J.evalf(), dtype=float)).real))
    seccion.formula(rf"\lambda_u({L(mu)}^*) \approx {lambda_u:.4f} > 0")
    seccion.formula(rf"T({L(mu)}) \approx -\frac{{1}}{{\lambda_u}}\ln\left|{L(mu)} - {L(mu)}^*\right| + C "
                    rf"\implies T \to \infty \text{{ cuando }} {L(mu)} \to {L(mu)}^*", destacada=True)
    d.guardar("lambda_u", lambda_u)
    if lado_ciclo is not None and centro is not None:
        pendiente = _pendiente_del_periodo(problema, mu_n, -1 if lado_ciclo == "<" else 1, inicio)
        if pendiente is not None:
            seccion.formula(rf"\text{{Ajuste numérico: }} \frac{{dT}}{{d\ln|{L(mu)} - {L(mu)}^*|}} \approx {pendiente:.3f}"
                            rf",\qquad -\frac{{1}}{{\lambda_u}} \approx {-1 / lambda_u:.3f}")
            d.guardar("pendiente_periodo", pendiente)
            d.validar("divergencia_logaritmica_del_periodo", abs(pendiente + 1 / lambda_u) < 0.35 / lambda_u,
                      "El periodo medido crece como −(1/λᵤ)·ln|μ − μ*| al acercarse a la conexión.",
                      medida=abs(pendiente + 1 / lambda_u), umbral=0.35 / lambda_u, tipo="numerica")


def _pendiente_del_periodo(problema, mu_n, lado, inicio):
    """Pendiente de T frente a ln|μ − μ*|, midiendo el periodo del ciclo a varias distancias."""
    distancias, periodos = [], []
    for delta in (0.04, 0.02, 0.01, 0.005):
        valor = mu_n + lado * delta
        f = _campo_numerico(problema, valor)

        def cruce(t, s):
            return s[1]
        cruce.direction = -1
        solucion = solve_ivp(f, (0, 900), inicio, events=cruce, rtol=1e-10, atol=1e-12)
        tiempos = solucion.t_events[0]
        if tiempos.size < 6:
            continue
        diferencias = np.diff(tiempos[-4:])
        if np.std(diferencias) > 1e-3 * np.mean(diferencias):
            continue
        distancias.append(math.log(delta))
        periodos.append(float(np.mean(diferencias)))
    if len(distancias) < 3:
        return None
    pendiente, _ = np.polyfit(distancias, periodos, 1)
    return float(pendiente)


def _grafica_homoclinica(d, problema, H0, x, y, silla, resultado):
    lazo = d.resultados["lazo_homoclinico"]
    dominio = d.resultados["dominio_lazo"]
    a, b = float(dominio.inf), float(dominio.sup)
    ancho = b - a
    caja = ((a - 0.5 * ancho, b + 0.4 * ancho), (-0.9 * ancho, 0.9 * ancho))
    capas = []
    xs1, ys1 = muestreo.curva(lazo, x, a, b, n=300)
    xs2, ys2 = muestreo.curva(-lazo, x, a, b, n=300)
    capas.append({"tipo": "linea", "rol": "separatriz", "nombre": "Lazo homoclínico no perturbado (H = 0)",
                  "x": xs1 + [None] + xs2, "y": ys1 + [None] + ys2})
    if resultado is not None:
        mu_n = resultado["mu"]
        f = _campo_numerico(problema, mu_n)
        J = sp.Matrix(problema.campo_con(mu_n)).jacobian([x, y]).subs({x: silla[0], y: silla[1]})
        lin = linealizar(problema.campo_con(mu_n), [x, y], silla, matriz_general=sp.Matrix(problema.campo_con(mu_n)).jacobian([x, y]))
        direcciones = dict((("s" if v < 0 else "u"), w) for v, w in lin.direcciones())
        ramas = muestreo.variedades(f, [float(silla[0]), float(silla[1])], direcciones.get("s"),
                                    direcciones.get("u"), caja, tiempo=40.0, eps=1e-6)
        for clave, rol in (("estable", "variedad_estable"), ("inestable", "variedad_inestable")):
            xs, ys = [], []
            for rama in ramas[clave]:
                xs += rama["x"] + [None]
                ys += rama["y"] + [None]
            capas.append({"tipo": "linea", "rol": rol, "nombre": f"W{'ˢ' if clave == 'estable' else 'ᵘ'} en μ* ≈ {mu_n:.4f}",
                          "x": xs, "y": ys})
        evidencia = d.resultados.get("evidencia_ciclo", {})
        for etiqueta, e in evidencia.items():
            if not e.get("escapa"):
                fc = _campo_numerico(problema, e["mu"])
                orbita = solve_ivp(fc, (0, 400), [float(a + 0.66 * ancho), 0.0], rtol=1e-10, atol=1e-12,
                                   t_eval=np.linspace(330, 400, 1500))
                capas.append({"tipo": "linea", "rol": "ciclo", "nombre": f"Ciclo límite (μ = {e['mu']:.4f})",
                              "x": orbita.y[0].tolist(), "y": orbita.y[1].tolist()})
        muestras = resultado["muestras"]
        d.grafica({"clave": "separacion", "titulo": "Separación de las variedades d(μ)",
                   "ejes": {"x": "μ", "y": "d(μ)"},
                   "capas": [{"tipo": "linea", "rol": "trayectoria", "nombre": "d(μ) = x_u − x_s",
                              "x": [m for m, _ in muestras], "y": [v for _, v in muestras], "marcadores": True},
                             {"tipo": "puntos", "rol": "critico", "nombre": f"μ* ≈ {mu_n:.4f}", "x": [mu_n], "y": [0.0]},
                             {"tipo": "puntos", "rol": "referencia", "nombre": f"Melnikov μc = {sp.sstr(d.resultados['mu_melnikov'])}",
                              "x": [float(d.resultados["mu_melnikov"])], "y": [0.0]}]})
    for e in d.resultados.get("equilibrios", []):
        capas.append({"tipo": "puntos", "rol": "equilibrio:indefinido", "nombre": f"Equilibrio ({sp.sstr(e[0])}, {sp.sstr(e[1])})",
                      "x": [float(sp.N(e[0]))], "y": [float(sp.N(e[1]))]})
    d.grafica({"clave": "retrato_fase", "titulo": "Conexión homoclínica y ciclo límite",
               "ejes": {"x": x.name, "y": y.name}, "rango": {"x": list(caja[0]), "y": list(caja[1])},
               "capas": capas})
