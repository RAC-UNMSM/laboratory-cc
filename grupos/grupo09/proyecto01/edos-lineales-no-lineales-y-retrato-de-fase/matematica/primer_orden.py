"""EDO escalares de primer orden: los métodos analíticos del Tema 1.

Familias y su procedimiento, reconstruido de los problemas del balotario:

* **Separable** (1.1) — y' = g(x)·h(y): separar, integrar ambos miembros,
  despejar, aplicar la condición inicial y hallar el intervalo maximal.
* **Lineal** (pasos 5 y 6 del 1.2) — y' + P(x)y = Q(x): factor integrante
  μ = e^{∫P}, (μy)' = μQ, integrar.
* **Bernoulli** (1.2) — y' + P(x)y = Q(x)yⁿ: v = y^{1−n}, dividir entre yⁿ,
  obtener la ecuación lineal en v, resolverla y volver a y.
* **Riccati** (1.4) — y' = q₂y² + q₁y + q₀ con una solución particular y₁:
  verificar y₁, sustituir y = y₁ + 1/u, obtener la ecuación lineal en u.

Cada función `identificar_*` decide si la ecuación tiene la forma y devuelve
los coeficientes; cada `desarrollar_*` realiza el método con sympy y registra
cada resultado intermedio en un `Desarrollo`. Nada de lo que se presenta se
escribe a mano: toda fórmula sale de un objeto calculado.
"""

from __future__ import annotations

import sympy as sp
from sympy.calculus.util import continuous_domain
from sympy.integrals.manualintegrate import integral_steps

from matematica import MetodoNoAplicable
from matematica.desarrollo import (Desarrollo, L, bonita, intervalo_latex, intervalo_texto, numero,
                                   suma, sustituir_a_la_vista)
from matematica import muestreo

TEMA = "Tema 1 · EDOs lineales y no lineales"
C = sp.Symbol("C", real=True)


# ---------------------------------------------------------------------------
# Notación
# ---------------------------------------------------------------------------

def prima(simbolo: sp.Symbol, orden: int = 1) -> sp.Symbol:
    """y', u'', ... como símbolos de presentación."""
    return sp.Symbol(simbolo.name + "'" * orden)


def dydx(y, x) -> str:
    return rf"\frac{{d{L(y)}}}{{d{L(x)}}}"


def con_valor_absoluto(expresion):
    """ln(u) → ln|u| en una primitiva: es la antiderivada válida a ambos lados de u = 0."""
    return expresion.replace(lambda e: isinstance(e, sp.log) and not isinstance(e.args[0], sp.Abs),
                             lambda e: sp.log(sp.Abs(e.args[0])))


# ---------------------------------------------------------------------------
# Detección de la forma
# ---------------------------------------------------------------------------

def potencias(f, y):
    """Descompone f como Σ aₖ(x)·yᵏ. Devuelve {k: aₖ} o None si no tiene esa forma."""
    terminos = {}
    for termino in sp.Add.make_args(sp.expand(f)):
        coeficiente, resto = termino.as_independent(y, as_Add=False)
        if resto == 1:
            k = sp.Integer(0)
        elif resto == y:
            k = sp.Integer(1)
        elif isinstance(resto, sp.Pow) and resto.base == y and not resto.exp.has(y):
            k = resto.exp
        else:
            return None
        terminos[k] = terminos.get(k, 0) + coeficiente
    return {k: sp.simplify(v) for k, v in terminos.items() if sp.simplify(v) != 0}


def identificar_separable(f, x, y):
    partes = sp.separatevars(sp.sympify(f), [x, y], dict=True)
    if not partes:
        return None
    g = sp.simplify(partes["coeff"] * partes[x])
    h = sp.simplify(partes[y])
    return {"g": g, "h": h}


def identificar_lineal(f, x, y):
    terminos = potencias(f, y)
    if terminos is None or not set(terminos) <= {0, 1}:
        return None
    return {"P": sp.simplify(-terminos.get(1, 0)), "Q": sp.simplify(terminos.get(0, 0))}


def identificar_bernoulli(f, x, y):
    terminos = potencias(f, y)
    if terminos is None:
        return None
    exponentes = [k for k in terminos if k not in (0, 1)]
    if len(exponentes) != 1 or 0 in terminos:
        return None
    n = exponentes[0]
    return {"P": sp.simplify(-terminos.get(1, 0)), "Q": terminos[n], "n": n}


def identificar_riccati(f, x, y):
    terminos = potencias(f, y)
    if terminos is None or not set(terminos) <= {0, 1, 2} or 2 not in terminos:
        return None
    return {"q2": terminos[2], "q1": terminos.get(1, sp.Integer(0)),
            "q0": terminos.get(0, sp.Integer(0))}


# ---------------------------------------------------------------------------
# Piezas compartidas
# ---------------------------------------------------------------------------

def integrar(integrando, variable):
    """Primitiva y, si sympy la obtuvo por partes, el detalle de la técnica.

    El detalle es el que escribe el balotario en el 1.3:
    ∫ x ln x dx = (x²/2) ln x − ∫ (x²/2)(1/x) dx.
    """
    integrando = sp.simplify(integrando)
    primitiva = sp.integrate(integrando, variable)
    detalle = None
    try:
        regla = integral_steps(integrando, variable)
        # c·∫f: el detalle interesante está dentro (−∫x ln x es "por partes"),
        # pero la constante se conserva para escribir −(uv − ∫v du).
        constante = sp.Integer(1)
        while type(regla).__name__ == "ConstantTimesRule":
            constante *= regla.constant
            regla = regla.substep
        candidatas = getattr(regla, "alternatives", None) or [regla]
        for candidata in candidatas:
            if type(candidata).__name__ == "PartsRule":
                u, dv = candidata.u, candidata.dv
                v = sp.integrate(dv, variable)
                resto = sp.simplify(v * sp.diff(u, variable))
                detalle = {"tecnica": "partes", "u": u, "dv": dv, "v": v,
                           "resto": resto, "constante": constante}
                break
    except Exception:                        # el detalle es opcional; la primitiva no
        detalle = None
    return primitiva, detalle


def formula_integral(seccion, integrando, variable, primitiva, detalle, prefijo=None, ref=None):
    """Escribe ∫ ... = ... y, si fue por partes, el paso intermedio."""
    izquierda = (L(prefijo) + " " if prefijo is not None else "") + \
        rf"\int {L(integrando)}\, d{L(variable)}"
    if detalle and detalle["tecnica"] == "partes":
        partes = rf"{L(detalle['v'] * detalle['u'])} - \int {L(detalle['resto'])}\, d{L(variable)}"
        constante = detalle.get("constante", 1)
        if constante == -1:
            partes = rf"-\left({partes}\right)"
        elif constante != 1:
            partes = rf"{L(constante)}\left({partes}\right)"
        seccion.formula(izquierda, "=", partes)
        seccion.texto(f"Por partes, con u = {sp.sstr(detalle['u'])} y "
                      f"dv = {sp.sstr(detalle['dv'])} d{variable}.")
    seccion.formula(izquierda, "=", primitiva, destacada=ref is not None, ref=ref)


def resolver_lineal(d: Desarrollo, P, Q, x, funcion: sp.Symbol, *, prefijo_clave=""):
    """Factor integrante para w' + P w = Q. Registra sus secciones y devuelve w(x) con C.

    Es el procedimiento de los pasos 5 y 6 del 1.2, y lo reutilizan Bernoulli
    (en v) y Riccati (en u): por eso vive aparte y recibe el nombre de la
    función incógnita.
    """
    w, wp = funcion, prima(funcion)
    clave = (prefijo_clave + "_") if prefijo_clave else ""
    seccion = d.seccion(f"{clave}factor_integrante",
                        f"Factor integrante de la ecuación lineal en ${L(w)}$")
    seccion.formula(wp, "+", rf"P({L(x)})\, {L(w)}", "=", rf"Q({L(x)})")
    seccion.formula(rf"P({L(x)}) = {L(P)},\qquad Q({L(x)}) = {L(Q)}")
    integral_p = sp.integrate(P, x)
    mu = sp.simplify(sp.exp(integral_p))
    pasos_mu = [r"\mu(" + L(x) + r") = e^{\int P\, d" + L(x) + "}", "=", rf"e^{{{L(integral_p)}}}"]
    if sp.simplify(mu - sp.exp(integral_p)) != 0 or mu != sp.exp(integral_p):
        pasos_mu += ["=", mu]
    seccion.formula(*pasos_mu, destacada=True, ref=f"{clave}factor_integrante")
    d.guardar(f"{clave}factor_integrante", mu)

    seccion = d.seccion(f"{clave}integracion",
                        "Multiplicación por el factor integrante e integración")
    seccion.formula(suma((mu, wp), (sp.simplify(mu * P), w)), "=", sp.simplify(mu * Q))
    seccion.formula(rf"\frac{{d}}{{d{L(x)}}}\left[{L(sp.Mul(mu, w, evaluate=False))}\right]",
                    "=", sp.simplify(mu * Q))
    primitiva, detalle = integrar(mu * Q, x)
    formula_integral(seccion, sp.simplify(mu * Q), x, primitiva, detalle)
    seccion.formula(sp.Mul(mu, w, evaluate=False), "=", primitiva + C)
    solucion = sp.expand(sp.simplify((primitiva + C) / mu))
    seccion.formula(w, "=", solucion, destacada=True, ref=f"{clave}solucion_general")
    d.guardar(f"{clave}solucion_general", solucion)
    return solucion


def raices_reales(expresion, variable):
    try:
        conjunto = sp.solveset(expresion, variable, domain=sp.S.Reals)
    except (NotImplementedError, ValueError, TypeError):
        return []
    return sorted(conjunto, key=lambda v: float(v)) if isinstance(conjunto, sp.FiniteSet) else []


def aplicar_condicion_inicial(d, candidatas, x, y, x0, y0, *, titulo=None):
    """Fija C con y(x0) = y0 sobre la(s) rama(s) de la solución general.

    Si la solución general tiene varias ramas (±√), se queda con la que puede
    satisfacer la condición, que es como el balotario elige el signo en el 1.2.
    Devuelve la solución particular o None si ninguna rama la satisface.
    """
    seccion = d.seccion("condicion_inicial",
                        titulo or f"Aplicación de la condición inicial ${L(y)}({L(x0)}) = {L(y0)}$")
    for candidata in candidatas:
        ecuacion = sp.Eq(y0, candidata.subs(x, x0))
        try:
            valores = [v for v in sp.solve(ecuacion, C) if v.is_real is not False]
        except NotImplementedError:
            valores = []
        if not valores:
            continue
        # Primero la sustitución tal cual (x0 sin evaluar, como 3(0)² en el
        # balotario) y después la ecuación ya reducida que determina C.
        seccion.formula(y0, "=", sustituir_a_la_vista(candidata, x, x0))
        reducida = sp.simplify(candidata.subs(x, x0))
        if sp.srepr(reducida) != sp.srepr(candidata.subs(x, x0)):
            seccion.formula(y0, "=", reducida)
        constante = sp.nsimplify(valores[0])
        seccion.formula(C, "=", constante, destacada=True, ref="constante")
        sustituida = candidata.subs(C, constante)
        # La forma más corta: simplify a veces empeora (x + 1/(C − x) con C = −1
        # se lee mejor así que como (x(x + 1) − 1)/(x + 1)).
        particular = min((sustituida, sp.simplify(sustituida)), key=sp.count_ops)
        if sp.srepr(sustituida) != sp.srepr(particular):
            seccion.formula(y, "=", sustituida)
        seccion.formula(sp.Symbol(f"{y.name}({x.name})"), "=", bonita(particular), destacada=True,
                        ref="solucion_particular")
        d.guardar("constante", constante)
        d.guardar("solucion_particular", particular)
        return particular
    seccion.texto("Ninguna rama de la solución general satisface la condición inicial.")
    return None


#: Valores de prueba de C y de x cuando sympy no reduce el residuo a 0.
_PRUEBAS_C = (sp.Rational(1, 3), sp.Rational(7, 5), -sp.Rational(2, 7))
_PRUEBAS_X = (sp.Rational(3, 10), sp.Rational(7, 10), sp.Rational(13, 10), sp.Rational(5, 2))


def _residuo_nulo_en_muestras(residuo, solucion, x):
    """(nulo, concluyente) evaluando el residuo con 30 cifras en puntos de prueba.

    Solo cuentan los puntos donde la solución es real y finita; si no hay
    ninguno, la comprobación no es concluyente.
    """
    libres = sorted(residuo.free_symbols - {x}, key=lambda s: s.name)
    muestras = 0
    for valor_c in _PRUEBAS_C:
        fijos = {s: valor_c for s in libres}
        for valor_x in _PRUEBAS_X:
            try:
                y_valor = complex(sp.N(sp.sympify(solucion).subs(fijos).subs(x, valor_x), 30))
                r_valor = complex(sp.N(residuo.subs(fijos).subs(x, valor_x), 30))
            except (TypeError, ValueError, ZeroDivisionError):
                continue
            if not (abs(y_valor.imag) < 1e-20 and abs(y_valor) < 1e12) or r_valor != r_valor:
                continue
            muestras += 1
            if abs(r_valor) > 1e-15 * (1 + abs(y_valor)):
                return False, True
    return muestras > 0, muestras > 0


def validar_solucion(d, nombre, solucion, f, x, y, que="La solución"):
    """Sustituye y(x) en y' = f(x, y): el residuo y' − f debe anularse idénticamente."""
    solucion = sp.sympify(solucion)
    residuo = sp.diff(solucion, x) - sp.sympify(f).subs(y, solucion)
    try:
        nulo = sp.simplify(residuo) == 0
    except Exception:                       # sympy puede fallar con ramas y raíces
        nulo = False
    concluyente = True
    if not nulo:
        nulo, concluyente = _residuo_nulo_en_muestras(residuo, solucion, x)
    d.validar(nombre, nulo, f"{que} sustituida en la ecuación da y' − f(x, y) ≡ 0.",
              concluyente=concluyente)
    return nulo


def validar_condicion_inicial(d, particular, x, y, x0, y0):
    cumple = sp.simplify(sp.sympify(particular).subs(x, x0) - y0) == 0
    d.validar("condicion_inicial_exacta", cumple,
              f"La solución particular cumple {y}({sp.sstr(x0)}) = {sp.sstr(y0)} exactamente.")
    return cumple


def validar_soluciones(d, f, x, y, general=None, particular=None, ci=None):
    """Las comprobaciones simbólicas comunes a las familias escalares de primer orden."""
    ramas = general if isinstance(general, list) else [general] if general is not None else []
    for i, rama in enumerate(ramas, 1):
        validar_solucion(d, "solucion_general_satisface_la_edo" + (f"_{i}" if len(ramas) > 1 else ""),
                         rama, f, x, y, "La solución general (con C arbitraria)")
    if particular is not None:
        validar_solucion(d, "solucion_particular_satisface_la_edo", particular, f, x, y,
                         "La solución particular")
        if ci is not None:
            validar_condicion_inicial(d, particular, x, y, *ci)


def intervalo_maximal(d, particular, f, x, y, x0):
    """Intervalo más grande que contiene a x0 donde la solución existe.

    Se intersecan el dominio de continuidad de la solución y el del campo
    evaluado sobre ella: la solución deja de existir donde explota (2 − 3x² = 0
    en el 1.1) o donde el campo deja de estar definido.
    """
    try:
        dominio = continuous_domain(particular, x, sp.S.Reals)
        campo = sp.sympify(f).subs(y, particular)
        if campo.has(x):
            dominio = dominio.intersect(continuous_domain(campo, x, sp.S.Reals))
    except (NotImplementedError, ValueError, TypeError):
        return None
    piezas = dominio.args if isinstance(dominio, sp.Union) else (dominio,)
    for pieza in piezas:
        if isinstance(pieza, sp.Interval) and pieza.contains(x0) == sp.true:
            return pieza
    return None


def seccion_intervalo_maximal(d, particular, f, x, y, x0):
    intervalo = intervalo_maximal(d, particular, f, x, y, x0)
    if intervalo is None:
        return None
    seccion = d.seccion("intervalo_maximal", "Intervalo maximal de existencia")
    _, denominador = sp.fraction(sp.together(particular))
    ceros = raices_reales(denominador, x) if denominador.has(x) else []
    if ceros:
        seccion.formula(denominador, "= 0", r"\implies", rf"{L(x)} \in \left\{{{L(ceros)}\right\}}")
    extremos = [e for e in (intervalo.start, intervalo.end) if e.is_finite]
    for extremo in extremos:
        lado = "-" if extremo == intervalo.end else "+"
        try:
            limite = sp.limit(particular, x, extremo, dir=lado)
        except (NotImplementedError, ValueError):
            limite = None
        if limite is not None and limite.is_infinite:
            seccion.formula(rf"\lim_{{{L(x)} \to {L(extremo)}^{{{lado}}}}} {L(y)}({L(x)})",
                            "=", limite)
    seccion.formula(L(x) + "_0 = " + L(x0), r"\in", intervalo_latex(intervalo))
    seccion.formula("I", "=", intervalo_latex(intervalo), destacada=True, ref="intervalo_maximal")
    d.guardar("intervalo_maximal", intervalo)
    if extremos:
        d.concluir(f"La solución solo existe en I = {intervalo_texto(intervalo)}: "
                   f"explota en {', '.join(f'{x} = {sp.sstr(e)}' for e in extremos)}.")
    return intervalo


def grafica_escalar(d, x, y, particular=None, general=None, ci=None, intervalo=None,
                    singularidades=(), particular_conocida=None, titulo=None, valores_c=None):
    """Curva de la solución, miembros de la familia general, asíntotas y la CI."""
    a, b = muestreo.ventana_escalar(ci, intervalo, singularidades)
    capas = []
    if general is not None and general.has(C):
        base = d.resultados.get("constante")
        valores = valores_c or muestreo.valores_de_familia(base)
        for valor in valores:
            expresion = general.subs(C, valor)
            if particular is not None and sp.simplify(expresion - particular) == 0:
                continue
            xs, ys = muestreo.curva(expresion, x, a, b)
            if any(v is not None for v in ys):
                capas.append({"tipo": "linea", "rol": "familia", "nombre": f"C = {sp.sstr(valor)}",
                              "x": xs, "y": ys})
    if particular_conocida is not None:
        xs, ys = muestreo.curva(particular_conocida, x, a, b)
        capas.append({"tipo": "linea", "rol": "particular",
                      "nombre": f"{y}₁ = {sp.sstr(particular_conocida)}", "x": xs, "y": ys})
    if particular is not None:
        xs, ys = muestreo.curva(particular, x, a, b)
        capas.append({"tipo": "linea", "rol": "analitica",
                      "nombre": f"{y}({x}) = {sp.sstr(particular)}", "x": xs, "y": ys})
    for s in singularidades:
        valor = numero(s)
        if isinstance(valor, float) and a < valor < b:
            capas.append({"tipo": "vertical", "rol": "asintota", "x": valor,
                          "nombre": f"{x} = {sp.sstr(s)}"})
    if ci is not None:
        capas.append({"tipo": "puntos", "rol": "condicion_inicial", "nombre": "Condición inicial",
                      "x": [float(ci[0])], "y": [float(ci[1])],
                      "etiquetas": [f"({sp.sstr(ci[0])}, {sp.sstr(ci[1])})"]})
    if capas:
        d.grafica({"clave": "solucion", "titulo": titulo or "Solución analítica",
                   "ejes": {"x": x.name, "y": f"{y.name}({x.name})"},
                   "rango": {"x": [a, b], "y": muestreo.rango_vertical(capas)},
                   "capas": capas})


def _datos_ci(problema):
    if problema.ci is None:
        return None, None
    return problema.ci[0], problema.ci[1][0]


# ---------------------------------------------------------------------------
# Separable (1.1)
# ---------------------------------------------------------------------------

def desarrollar_separable(problema, datos=None) -> Desarrollo:
    x, y = problema.x, problema.estados[0]
    f = problema.campo[0]
    datos = datos or identificar_separable(f, x, y)
    if datos is None:
        raise MetodoNoAplicable(f"{sp.sstr(f)} no se puede escribir como g({x})·h({y}).")
    g, h = datos["g"], datos["h"]
    d = Desarrollo("separable", "EDO separable", TEMA,
                   "Separación de variables e integración de ambos miembros",
                   tratamiento=["analitico"], balotario=["1.1"])
    d.guardar("g", g)
    d.guardar("h", h)
    x0, y0 = _datos_ci(problema)

    seccion = d.seccion("separacion", "Separación de variables")
    seccion.formula(dydx(y, x), "=", f)
    seccion.formula(dydx(y, x), "=", rf"g({L(x)})\, h({L(y)})", r"\qquad",
                    rf"g({L(x)}) = {L(g)},\quad h({L(y)}) = {L(h)}")
    integrando_y = sp.simplify(1 / h)
    seccion.formula(rf"\frac{{d{L(y)}}}{{{L(h)}}}", "=", rf"{L(g)}\, d{L(x)}")
    seccion.formula(rf"{L(integrando_y)}\, d{L(y)}", "=", rf"{L(g)}\, d{L(x)}", destacada=True,
                    ref="ecuacion_separada")
    constantes = raices_reales(h, y)
    d.guardar("soluciones_constantes", constantes)
    if constantes:
        seccion.texto("Al dividir entre h(y) se excluyen los valores donde h se anula; cada uno "
                      "es una solución constante de la ecuación:")
        seccion.formula(L(h), "= 0", r"\implies",
                        r",\; ".join(rf"{L(y)} \equiv {L(c)}" for c in constantes))

    if y0 is not None and any(sp.simplify(y0 - c) == 0 for c in constantes):
        # La condición inicial cae sobre una solución constante: por unicidad,
        # es la solución del PVI, y la fórmula general (que dividió entre h)
        # no la contiene.
        seccion = d.seccion("condicion_inicial",
                            f"Aplicación de la condición inicial ${L(y)}({L(x0)}) = {L(y0)}$")
        seccion.formula(rf"h({L(y0)}) = {L(h.subs(y, y0))}", r"\implies",
                        rf"{L(y)}({L(x)}) \equiv {L(y0)}", destacada=True, ref="solucion_particular")
        d.guardar("solucion_particular", sp.sympify(y0))
        validar_soluciones(d, f, x, y, particular=sp.sympify(y0), ci=(x0, y0))
        d.concluir(f"La condición inicial está sobre la solución constante {y} ≡ {y0}; por "
                   "unicidad, esa es la solución del problema.")
        grafica_escalar(d, x, y, particular=sp.sympify(y0), ci=(x0, y0), intervalo=problema.intervalo)
        return d

    seccion = d.seccion("integracion", "Integración de ambos miembros")
    seccion.formula(rf"\int {L(integrando_y)}\, d{L(y)}", "=", rf"\int {L(g)}\, d{L(x)}")
    primitiva_y, detalle_y = integrar(integrando_y, y)
    primitiva_x, detalle_x = integrar(g, x)
    if not integrando_y.has(sp.log):
        primitiva_y = con_valor_absoluto(primitiva_y)
    if not g.has(sp.log):
        primitiva_x = con_valor_absoluto(primitiva_x)
    if detalle_x:
        formula_integral(seccion, g, x, primitiva_x, detalle_x)
    implicita = sp.Eq(primitiva_y, primitiva_x + C)
    seccion.formula(primitiva_y, "=", primitiva_x + C, destacada=True, ref="solucion_implicita")
    d.guardar("primitiva_y", primitiva_y)
    d.guardar("primitiva_x", primitiva_x)
    d.guardar("solucion_implicita", implicita)
    # Derivar la solución implícita respecto de x debe devolver la ecuación:
    # comprueba las dos integrales sin depender del despeje.
    # d/du ln|u| = 1/u: se deriva sin los valores absolutos, que sympy convierte
    # en sign(u)/|u| y luego no simplifica.
    sin_abs_y = primitiva_y.replace(sp.Abs, lambda a: a)
    sin_abs_x = primitiva_x.replace(sp.Abs, lambda a: a)
    d.validar("integracion_correcta",
              sp.simplify(sp.diff(sin_abs_y, y) * f - sp.diff(sin_abs_x, x)) == 0,
              "Derivar la solución implícita respecto de x reproduce y' = g(x)h(y): las dos "
              "primitivas son correctas.")
    if any(isinstance(p, sp.Integral) for p in (primitiva_x, primitiva_y)):
        d.advertir("Una de las integrales no tiene primitiva elemental: la solución queda "
                   "expresada con la integral indicada.")

    # Despeje. Se resuelve sin los valores absolutos (son ramas de la misma
    # familia) y la constante e^C se renombra, como hace el balotario en el 2.1.
    sin_abs = sp.Eq(primitiva_y.replace(sp.Abs, lambda a: a), primitiva_x.replace(sp.Abs, lambda a: a) + C)
    try:
        candidatas = sp.solve(sin_abs, y)
    except (NotImplementedError, ValueError):
        candidatas = []
    candidatas = [sp.simplify(c) for c in candidatas if c.has(x) or c.has(C)]
    renombrada = False
    explicitas = []
    for candidata in candidatas:
        if candidata.has(sp.exp(C)):
            candidata = sp.simplify(candidata.subs(sp.exp(C), C))
            renombrada = True
        explicitas.append(candidata)
    if explicitas:
        seccion = d.seccion("despeje", f"Despeje de ${L(y)}({L(x)})$")
        if renombrada:
            seccion.texto("La constante e^C se renombra como C (una constante arbitraria).")
        for candidata in explicitas:
            seccion.formula(y, "=", bonita(candidata), destacada=True, ref="solucion_general")
        d.guardar("solucion_general", explicitas if len(explicitas) > 1 else explicitas[0])
    else:
        d.advertir("No se pudo despejar y(x): la solución general queda en forma implícita.")

    particular = None
    if y0 is not None:
        if explicitas:
            particular = aplicar_condicion_inicial(d, explicitas, x, y, x0, y0)
        else:
            seccion = d.seccion("condicion_inicial",
                                f"Aplicación de la condición inicial ${L(y)}({L(x0)}) = {L(y0)}$")
            valor_c = sp.solve(implicita.subs({x: x0, y: y0}), C)
            if valor_c:
                seccion.formula(C, "=", valor_c[0], destacada=True, ref="constante")
                d.guardar("constante", valor_c[0])
                seccion.formula(implicita.lhs, "=", implicita.rhs.subs(C, valor_c[0]), destacada=True)

    validar_soluciones(d, f, x, y, general=explicitas or None, particular=particular,
                       ci=(x0, y0) if particular is not None else None)
    singularidades = []
    if particular is not None:
        if "intervalo_maximo" in problema.pedidos or _tiene_singularidad(particular, x):
            intervalo = seccion_intervalo_maximal(d, particular, f, x, y, x0)
            if intervalo is not None:
                singularidades = [e for e in (intervalo.start, intervalo.end) if e.is_finite]
    general = d.resultados.get("solucion_general")
    grafica_escalar(d, x, y, particular=particular,
                    general=general if not isinstance(general, list) else None,
                    ci=(x0, y0) if y0 is not None else None, intervalo=problema.intervalo,
                    singularidades=singularidades)
    return d


def _tiene_singularidad(expresion, x):
    _, denominador = sp.fraction(sp.together(expresion))
    return bool(denominador.has(x) and raices_reales(denominador, x)) or expresion.has(sp.log, sp.sqrt)


# ---------------------------------------------------------------------------
# Lineal de primer orden (sub-procedimiento del 1.2)
# ---------------------------------------------------------------------------

def desarrollar_lineal(problema, datos=None) -> Desarrollo:
    x, y = problema.x, problema.estados[0]
    f = problema.campo[0]
    datos = datos or identificar_lineal(f, x, y)
    if datos is None:
        raise MetodoNoAplicable(f"{sp.sstr(f)} no es lineal en {y}.")
    P, Q = datos["P"], datos["Q"]
    d = Desarrollo("lineal", "EDO lineal de primer orden", TEMA,
                   "Factor integrante μ = e^{∫P dx}", tratamiento=["analitico"], balotario=["1.2"])
    d.guardar("P", P)
    d.guardar("Q", Q)
    seccion = d.seccion("forma_estandar", "Forma estándar")
    seccion.formula(dydx(y, x), "=", f)
    seccion.formula(suma(prima(y), (P, y)), "=", Q, destacada=True)
    general = resolver_lineal(d, P, Q, x, y)
    x0, y0 = _datos_ci(problema)
    particular = aplicar_condicion_inicial(d, [general], x, y, x0, y0) if y0 is not None else None
    validar_soluciones(d, f, x, y, general=general, particular=particular,
                       ci=(x0, y0) if particular is not None else None)
    singularidades = []
    if particular is not None and ("intervalo_maximo" in problema.pedidos or _tiene_singularidad(particular, x)):
        intervalo = seccion_intervalo_maximal(d, particular, f, x, y, x0)
        if intervalo is not None:
            singularidades = [e for e in (intervalo.start, intervalo.end) if e.is_finite]
    grafica_escalar(d, x, y, particular=particular, general=general,
                    ci=(x0, y0) if y0 is not None else None, intervalo=problema.intervalo,
                    singularidades=singularidades)
    return d


# ---------------------------------------------------------------------------
# Bernoulli (1.2)
# ---------------------------------------------------------------------------

def desarrollar_bernoulli(problema, datos=None) -> Desarrollo:
    x, y = problema.x, problema.estados[0]
    f = problema.campo[0]
    datos = datos or identificar_bernoulli(f, x, y)
    if datos is None:
        raise MetodoNoAplicable(f"{sp.sstr(f)} no tiene la forma de Bernoulli "
                                f"-P({x}){y} + Q({x}){y}^n con n ≠ 0, 1.")
    P, Q, n = datos["P"], datos["Q"], datos["n"]
    v = sp.Symbol("v", real=True)
    vp, yp = prima(v), prima(y)
    d = Desarrollo("bernoulli", "Ecuación de Bernoulli", TEMA,
                   "Cambio de variable v = y^{1−n} y factor integrante",
                   tratamiento=["analitico"], balotario=["1.2"])
    for clave, valor in (("P", P), ("Q", Q), ("n", n)):
        d.guardar(clave, valor)

    seccion = d.seccion("identificacion", "Identificación de la ecuación de Bernoulli")
    seccion.formula(yp, "+", rf"P({L(x)}){L(y)}", "=", rf"Q({L(x)}){L(y)}^{{n}}", destacada=True)
    seccion.formula(suma(yp, (P, y)), "=", suma((Q, y ** n)))
    seccion.formula(rf"P({L(x)}) = {L(P)},\qquad Q({L(x)}) = {L(Q)},\qquad n = {L(n)}")

    exponente = 1 - n
    sustitucion = y ** exponente
    seccion = d.seccion("cambio_de_variable", "Cambio de variable $v = y^{1-n}$")
    seccion.formula("v", "=", rf"{L(y)}^{{1-n}}", "=", sustitucion, destacada=True, ref="sustitucion")
    derivada = sp.diff(sustitucion, y)
    seccion.formula(rf"\frac{{dv}}{{d{L(x)}}}", "=", derivada, rf"\frac{{d{L(y)}}}{{d{L(x)}}}")
    seccion.formula(vp, "=", sp.Mul(derivada, yp, evaluate=False), destacada=True)
    relacion = sp.simplify(vp / exponente)
    seccion.formula(sp.Mul(y ** (-n), yp, evaluate=False), "=", relacion)
    d.guardar("sustitucion", sp.Eq(v, sustitucion))

    seccion = d.seccion("division", f"División de la ecuación entre ${L(y ** n)}$")
    seccion.formula(suma(yp, (P, y)), "=", suma((Q, y ** n)))
    seccion.formula(suma((y ** (-n), yp), (P, y ** exponente)), "=", Q)
    seccion.formula(sp.Mul(y ** (-n), yp, evaluate=False), "=", relacion, r",\qquad",
                    y ** exponente, "=", v)
    en_v = sp.Eq(relacion + P * v, Q)
    seccion.formula(en_v.lhs, "=", en_v.rhs)

    P_v = sp.simplify(exponente * P)
    Q_v = sp.simplify(exponente * Q)
    seccion = d.seccion("ecuacion_lineal", "Ecuación lineal en $v$")
    seccion.formula(suma(vp, (P_v, v)), "=", Q_v, destacada=True, ref="ecuacion_lineal")
    d.guardar("ecuacion_lineal", sp.Eq(vp + P_v * v, Q_v))
    v_general = resolver_lineal(d, P_v, Q_v, x, v, prefijo_clave="v")

    seccion = d.seccion("regreso", f"Regreso a la variable original ${L(y)}$")
    seccion.formula(sustitucion, "=", v_general)
    potencia = sp.Integer(1) / exponente          # y = v^{1/(1−n)}
    if potencia.is_integer:
        ramas = [sp.simplify(v_general ** potencia)]
    elif potencia.is_Rational and potencia.q % 2 == 0:
        # Raíz de índice par: dos ramas, ±v^{1/(1−n)} (el ± del balotario).
        ramas = [v_general ** potencia, -v_general ** potencia]
    else:
        try:
            ramas = [sp.simplify(r) for r in sp.solve(sp.Eq(sustitucion, v_general), y)]
        except NotImplementedError:
            ramas = []
    if not ramas:
        ramas = [v_general ** (1 / exponente)]
    if len(ramas) > 1:
        seccion.formula(y, "=", r"\pm", sp.Abs(ramas[0]).replace(sp.Abs, lambda a: a))
    x0, y0 = _datos_ci(problema)
    elegidas = ramas
    if y0 is not None and len(ramas) > 1:
        elegidas = [r for r in ramas if _rama_compatible(r, x, x0, y0)] or ramas
    for rama in elegidas:
        seccion.formula(sp.Symbol(f"{y.name}({x.name})"), "=", rama, destacada=True,
                        ref="solucion_general")
    d.guardar("solucion_general", elegidas[0] if len(elegidas) == 1 else elegidas)
    if n.is_positive:
        d.guardar("solucion_trivial", sp.Integer(0))
        seccion.texto(f"Además, {y} ≡ 0 es solución: se excluyó al dividir entre {y}^{n}.")

    particular = None
    if y0 is not None:
        if sp.simplify(y0) == 0 and n.is_positive:
            seccion = d.seccion("condicion_inicial", "Aplicación de la condición inicial")
            seccion.formula(rf"{L(y)}({L(x0)}) = 0 \implies {L(y)} \equiv 0", destacada=True)
            particular = sp.Integer(0)
            d.guardar("solucion_particular", particular)
        else:
            particular = aplicar_condicion_inicial(d, elegidas, x, y, x0, y0)
        if particular is not None and particular.is_number:
            d.concluir(f"La solución es constante, {y} ≡ {particular}: la condición inicial "
                       "está sobre un equilibrio de la ecuación.")
    validar_soluciones(d, f, x, y, general=elegidas, particular=particular,
                       ci=(x0, y0) if particular is not None else None)
    singularidades = []
    if particular is not None and not particular.is_number and (
            "intervalo_maximo" in problema.pedidos or _tiene_singularidad(particular, x)):
        intervalo = seccion_intervalo_maximal(d, particular, f, x, y, x0)
        if intervalo is not None:
            singularidades = [e for e in (intervalo.start, intervalo.end) if e.is_finite]
    grafica_escalar(d, x, y, particular=particular,
                    general=elegidas[0] if len(elegidas) == 1 else None,
                    ci=(x0, y0) if y0 is not None else None, intervalo=problema.intervalo,
                    singularidades=singularidades)
    return d


def _rama_compatible(rama, x, x0, y0):
    try:
        return bool(sp.solve(sp.Eq(rama.subs(x, x0), y0), C))
    except NotImplementedError:
        return False


# ---------------------------------------------------------------------------
# Riccati (1.4)
# ---------------------------------------------------------------------------

def buscar_particular_polinomica(f, x, y, grado_maximo=2):
    """y₁ = a + bx + cx² por coeficientes indeterminados, o None.

    Es un recurso para cuando el enunciado no da la solución particular: si
    existe una polinómica de grado bajo, se encuentra; si no, se dice.
    """
    for grado in range(grado_maximo + 1):
        coeficientes = sp.symbols(f"a0:{grado + 1}")
        candidata = sum(c * x ** k for k, c in enumerate(coeficientes))
        residuo = sp.expand(sp.diff(candidata, x) - sp.sympify(f).subs(y, candidata))
        try:
            ecuaciones = sp.Poly(residuo, x).coeffs()
        except sp.PolynomialError:
            return None
        soluciones = sp.solve(ecuaciones, coeficientes, dict=True)
        for solucion in soluciones:
            if len(solucion) == len(coeficientes) and all(v.is_real for v in solucion.values()):
                return sp.expand(candidata.subs(solucion))
    return None


def desarrollar_riccati(problema, datos=None) -> Desarrollo:
    x, y = problema.x, problema.estados[0]
    f = problema.campo[0]
    datos = datos or identificar_riccati(f, x, y)
    if datos is None:
        raise MetodoNoAplicable(f"{sp.sstr(f)} no es cuadrática en {y}: no es de Riccati.")
    q2, q1, q0 = datos["q2"], datos["q1"], datos["q0"]
    u = sp.Symbol("u", real=True)
    up, yp = prima(u), prima(y)
    d = Desarrollo("riccati", "Ecuación de Riccati", TEMA,
                   "Solución particular conocida y cambio linealizante y = y₁ + 1/u",
                   tratamiento=["analitico"], balotario=["1.4"])
    for clave, valor in (("q2", q2), ("q1", q1), ("q0", q0)):
        d.guardar(clave, valor)

    seccion = d.seccion("identificacion", "Identificación de la ecuación de Riccati")
    seccion.formula(yp, "=", rf"q_2({L(x)}){L(y)}^2 + q_1({L(x)}){L(y)} + q_0({L(x)})", destacada=True)
    seccion.formula(yp, "=", f)
    seccion.formula(rf"q_2({L(x)}) = {L(q2)},\qquad q_1({L(x)}) = {L(q1)},\qquad q_0({L(x)}) = {L(q0)}")

    y1 = problema.solucion_particular
    seccion = d.seccion("particular", "Verificación de la solución particular $y_1$"
                        if y1 is not None else "Búsqueda de una solución particular $y_1$")
    if y1 is None:
        y1 = buscar_particular_polinomica(f, x, y)
        if y1 is None:
            raise MetodoNoAplicable(
                "La ecuación de Riccati necesita una solución particular y₁ y no se halló una "
                "polinómica de grado ≤ 2. Indíquela en `solucion_particular`.")
        seccion.texto(f"Se prueba y₁ = a₀ + a₁{x} + a₂{x}² por coeficientes indeterminados y se "
                      f"obtiene y₁ = {sp.sstr(y1)}.")
    derivada_y1 = sp.diff(y1, x)
    evaluada = sp.expand(sp.sympify(f).subs(y, y1))
    seccion.formula(rf"{L(y)}_1({L(x)}) = {L(y1)}", r"\implies", rf"{L(y)}_1'({L(x)}) = {L(derivada_y1)}")
    seccion.formula(rf"q_2 {L(y)}_1^2 + q_1 {L(y)}_1 + q_0", "=", evaluada)
    verificada = sp.simplify(derivada_y1 - evaluada) == 0
    d.validar("particular_satisface_la_edo", verificada,
              f"y₁ = {sp.sstr(y1)} satisface la ecuación: y₁' − f(x, y₁) se simplifica a 0.")
    if not verificada:
        raise MetodoNoAplicable(f"y₁ = {sp.sstr(y1)} no es solución: y₁' − f(x, y₁) = "
                                f"{sp.sstr(sp.simplify(derivada_y1 - evaluada))} ≠ 0.")
    seccion.formula(rf"{L(y)}_1'({L(x)}) = {L(derivada_y1)}", "=",
                    rf"q_2 {L(y)}_1^2 + q_1 {L(y)}_1 + q_0", destacada=True)
    d.guardar("solucion_particular_conocida", y1)

    seccion = d.seccion("cambio_de_variable", "Cambio de variable linealizante")
    sustitucion = y1 + 1 / u
    seccion.formula(y, "=", rf"{L(y)}_1 + \frac{{1}}{{u}}", "=", sustitucion, destacada=True,
                    ref="sustitucion")
    lado_izquierdo = derivada_y1 - up / u ** 2
    seccion.formula(yp, "=", lado_izquierdo, destacada=True)
    d.guardar("sustitucion", sp.Eq(y, sustitucion))

    seccion = d.seccion("sustitucion", "Sustitución en la ecuación diferencial")
    terminos = [sp.expand(q2 * sustitucion ** 2), sp.expand(q1 * sustitucion), q0]
    seccion.formula(lado_izquierdo, "=",
                    suma((q2, sp.Pow(sustitucion, 2, evaluate=False)), (q1, sustitucion), q0))
    seccion.formula(lado_izquierdo, "=", suma(*[t for termino in terminos
                                                 for t in sp.sympify(termino).as_ordered_terms()]))
    derecha = sp.expand(sum(terminos))
    seccion.formula(lado_izquierdo, "=", derecha)
    despejada = sp.solve(sp.Eq(lado_izquierdo, derecha), up)
    if not despejada:
        raise MetodoNoAplicable("La sustitución no produjo una ecuación para u'.")
    u_prima = sp.expand(despejada[0])
    coeficiente = sp.simplify(-sp.diff(u_prima, u))
    independiente = sp.simplify(u_prima + coeficiente * u)
    seccion.formula(up, "=", u_prima, destacada=True, ref="ecuacion_lineal")
    d.guardar("ecuacion_lineal", sp.Eq(up, u_prima))

    if coeficiente == 0:
        seccion = d.seccion("u_integracion", "Resolución de la ecuación para $u$")
        seccion.formula(rf"\int du", "=", rf"\int {L(independiente)}\, d{L(x)}")
        u_general = sp.integrate(independiente, x) + C
        seccion.formula(u, "=", u_general, destacada=True, ref="u_solucion_general")
        d.guardar("u_solucion_general", u_general)
    else:
        u_general = resolver_lineal(d, coeficiente, independiente, x, u, prefijo_clave="u")

    seccion = d.seccion("solucion_general", f"Solución general ${L(y)}({L(x)})$")
    general = y1 + 1 / u_general
    seccion.formula(y, "=", rf"{L(y)}_1 + \frac{{1}}{{u}}", "=", general, destacada=True)
    compacta = sp.factor_terms(sp.together(general))
    numerador, denominador = sp.fraction(compacta)
    compacta = sp.expand(numerador) / denominador
    seccion.formula(sp.Symbol(f"{y.name}({x.name})"), "=", compacta, destacada=True,
                    ref="solucion_general")
    d.guardar("solucion_general", general)

    x0, y0 = _datos_ci(problema)
    particular = None
    if y0 is not None:
        if sp.simplify(y1.subs(x, x0) - y0) == 0:
            seccion = d.seccion("condicion_inicial", "Aplicación de la condición inicial")
            seccion.formula(rf"{L(y)}_1({L(x0)}) = {L(y0)} \implies {L(y)} = {L(y)}_1 = {L(y1)}",
                            destacada=True)
            particular = y1
            d.guardar("solucion_particular", y1)
        else:
            particular = aplicar_condicion_inicial(d, [general], x, y, x0, y0)
    validar_soluciones(d, f, x, y, general=general, particular=particular,
                       ci=(x0, y0) if particular is not None else None)
    singularidades = []
    if particular is not None and particular != y1:
        intervalo = seccion_intervalo_maximal(d, particular, f, x, y, x0)
        if intervalo is not None:
            singularidades = [e for e in (intervalo.start, intervalo.end) if e.is_finite]
    elif particular is None:
        polo = raices_reales(sp.fraction(sp.together(u_general.subs(C, 1)))[0], x)
        singularidades = polo
    grafica_escalar(d, x, y, particular=particular, general=general,
                    ci=(x0, y0) if y0 is not None else None, intervalo=problema.intervalo,
                    singularidades=singularidades, particular_conocida=y1,
                    valores_c=None if y0 is not None else [sp.Integer(1), sp.Integer(3), sp.Integer(-1)])
    return d
