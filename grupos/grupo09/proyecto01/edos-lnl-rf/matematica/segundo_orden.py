"""EDO lineales de segundo orden: la familia de Cauchy-Euler del balotario (1.3).

    a x² y'' + b x y' + c y = f(x),   x > 0

Procedimiento, tal como lo desarrolla el balotario:

1. identificar a, b, c y f(x);
2. resolver la homogénea con el ansatz y = xᵐ, que lleva a la ecuación
   indicial a·m(m−1) + b·m + c = 0; según sus raíces (reales distintas,
   doble o complejas) se obtiene el sistema fundamental {y₁, y₂};
3. si f ≠ 0: normalizar (dividir entre a x²) para leer g(x), calcular el
   Wronskiano y aplicar variación de parámetros, u₁' = −y₂g/W, u₂' = y₁g/W;
4. y_p = u₁y₁ + u₂y₂ y la solución general y = y_h + y_p;
5. con condiciones iniciales, fijar c₁ y c₂.

La ecuación llega como sistema de primer orden [y, y'] (así la reduce el
cliente); `Problema.es_compania` reconoce esa forma y aquí se reconstruye
y'' = F(x, y, y'). La forma de Cauchy-Euler se detecta por lo que es: F lineal
en y, y' con x·p(x) y x²·q(x) constantes.
"""

from __future__ import annotations

import functools

import sympy as sp

from matematica import MetodoNoAplicable
from matematica.desarrollo import Desarrollo, L, bonita, punto_latex, suma, sustituir_a_la_vista
from matematica.primer_orden import formula_integral, grafica_escalar, integrar, prima

TEMA = "Tema 1 · EDOs lineales y no lineales"
C1, C2 = sp.symbols("c_1 c_2", real=True)
M = sp.Symbol("m")


def identificar_cauchy_euler(problema):
    """Coeficientes (a, b, c, f) si el sistema es una Cauchy-Euler, o None."""
    if not (problema.tipo == "edo" and problema.es_compania and problema.dimension == 2):
        return None
    x = problema.x
    y, yp = problema.estados
    F = sp.sympify(problema.campo[1])
    p = sp.simplify(-sp.diff(F, yp))
    q = sp.simplify(-sp.diff(F, y))
    if p.has(y, yp) or q.has(y, yp) or (p == 0 and q == 0):
        return None
    g = sp.simplify(F + p * yp + q * y)
    if g.has(y, yp):
        return None
    relativo_b = sp.simplify(x * p)
    relativo_c = sp.simplify(x ** 2 * q)
    if relativo_b.has(x) or relativo_c.has(x):
        return None
    # Se limpian denominadores para escribir a, b, c enteros cuando se puede:
    # 2x²y'' + 3xy' − y = 0 y no x²y'' + (3/2)xy' − (1/2)y = 0.
    denominadores = [sp.fraction(sp.nsimplify(v))[1] for v in (relativo_b, relativo_c)]
    a = functools.reduce(sp.ilcm, [int(d) for d in denominadores if d.is_Integer], 1) \
        if all(d.is_Integer for d in denominadores) else 1
    a = sp.Integer(a)
    return {"a": a, "b": sp.nsimplify(a * relativo_b), "c": sp.nsimplify(a * relativo_c),
            "f": sp.simplify(a * x ** 2 * g), "g": g}


def _sistema_fundamental(raices, x):
    """{y₁, y₂} y el caso, según las raíces de la ecuación indicial."""
    m1, m2 = raices
    if sp.im(m1) != 0:
        alfa, beta = sp.re(m1), abs(sp.im(m1))
        return ("complejas", x ** alfa * sp.cos(beta * sp.log(x)),
                x ** alfa * sp.sin(beta * sp.log(x)))
    if sp.simplify(m1 - m2) == 0:
        return "doble", x ** m1, x ** m1 * sp.log(x)
    return "reales distintas", x ** m1, x ** m2


def desarrollar_cauchy_euler(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_cauchy_euler(problema)
    if datos is None:
        raise MetodoNoAplicable("La ecuación no tiene la forma a x² y'' + b x y' + c y = f(x).")
    x_original = problema.x
    if problema.ci is not None and sp.N(problema.ci[0]) <= 0:
        raise MetodoNoAplicable("El desarrollo de Cauchy-Euler se hace en x > 0 y la condición "
                                "inicial está en x ≤ 0.")
    # En x > 0 sympy puede simplificar ln y potencias sin valores absolutos:
    # es el mismo dominio que fija el balotario.
    x = sp.Symbol(x_original.name, positive=True)
    y = problema.estados[0]
    a, b, c = datos["a"], datos["b"], datos["c"]
    f = sp.simplify(datos["f"].subs(x_original, x))
    yp, ypp = prima(y), prima(y, 2)

    d = Desarrollo("cauchy_euler", "Ecuación de Cauchy-Euler", TEMA,
                   "Ansatz y = xᵐ (ecuación indicial) y variación de parámetros",
                   tratamiento=["analitico"], balotario=["1.3"])
    for clave, valor in (("a", a), ("b", b), ("c", c), ("f", f)):
        d.guardar(clave, valor)

    seccion = d.seccion("identificacion", "Identificación de la ecuación de Cauchy-Euler")
    seccion.formula(r"a x^2 y'' + b x y' + c y = f(x)", destacada=True)
    ecuacion_izquierda = suma((a * x ** 2, ypp), (b * x, yp), (c, y))
    seccion.formula(ecuacion_izquierda, "=", f, r",\qquad", rf"{L(x)} > 0")
    seccion.formula(rf"a = {L(a)},\qquad b = {L(b)},\qquad c = {L(c)}")

    # --- homogénea --------------------------------------------------------------
    seccion = d.seccion("homogenea", "Solución de la ecuación homogénea asociada")
    seccion.formula(ecuacion_izquierda, "= 0")
    seccion.formula(rf"{L(y)} = {L(x)}^m \implies {L(yp)} = m {L(x)}^{{m-1}} \implies "
                    rf"{L(ypp)} = m(m-1){L(x)}^{{m-2}}")
    sustituida = suma((a * x ** 2, rf"\left[m(m-1){L(x)}^{{m-2}}\right]"),
                      (b * x, rf"\left[m {L(x)}^{{m-1}}\right]"),
                      (c, rf"\left[{L(x)}^{{m}}\right]"))
    seccion.formula(sustituida, "= 0")
    indicial = sp.expand(a * M * (M - 1) + b * M + c)
    seccion.formula(rf"{L(x)}^m\left[{suma((a, M * (M - 1)), (b, M), c)}\right] = 0")
    seccion.formula(suma((a, M * (M - 1)), (b, M), c), "= 0")
    seccion.formula(indicial, "= 0", destacada=True, ref="ecuacion_indicial")
    factorizada = sp.factor(indicial)
    if factorizada != indicial:
        seccion.formula(factorizada, "= 0")
    raices = sp.roots(sp.Poly(indicial, M))
    lista = sorted([r for r, k in raices.items() for _ in range(k)],
                   key=lambda r: (float(sp.re(r)), float(sp.im(r))))
    d.guardar("ecuacion_indicial", indicial)
    d.guardar("raices", lista)
    caso, y1, y2 = _sistema_fundamental(lista, x)
    d.guardar("caso_raices", caso)
    if caso == "complejas":
        seccion.formula(rf"m = {L(sp.re(lista[0]))} \pm {L(abs(sp.im(lista[0])))}\, i")
        seccion.texto("Raíces complejas α ± iβ: las soluciones reales son x^α cos(β ln x) y "
                      "x^α sin(β ln x).")
    elif caso == "doble":
        seccion.formula(rf"m_1 = m_2 = {L(lista[0])}")
        seccion.texto("Raíz doble: la segunda solución se obtiene multiplicando por ln x.")
    else:
        seccion.formula(rf"m_1 = {L(lista[0])},\qquad m_2 = {L(lista[1])}")
    seccion.formula(rf"{L(y)}_1({L(x)}) = {L(y1)},\qquad {L(y)}_2({L(x)}) = {L(y2)}")
    homogenea = C1 * y1 + C2 * y2
    seccion.formula(rf"{L(y)}_h({L(x)})", "=", homogenea, destacada=True, ref="solucion_homogenea")
    d.guardar("sistema_fundamental", [y1, y2])
    d.guardar("solucion_homogenea", homogenea)

    particular = sp.Integer(0)
    if sp.simplify(f) != 0:
        g = sp.simplify(f / (a * x ** 2))
        seccion = d.seccion("normalizacion", "Normalización de la ecuación")
        seccion.formula(rf"{L(ypp)} + P({L(x)}){L(yp)} + Q({L(x)}){L(y)} = g({L(x)})")
        seccion.formula(rf"\frac{{{ecuacion_izquierda}}}{{{L(a * x ** 2)}}}", "=",
                        rf"\frac{{{L(f)}}}{{{L(a * x ** 2)}}}")
        seccion.formula(suma(ypp, (sp.simplify(b / (a * x)), yp), (sp.simplify(c / (a * x ** 2)), y)),
                        "=", g)
        seccion.formula(rf"g({L(x)})", "=", g, destacada=True, ref="g")
        d.guardar("g", g)

        seccion = d.seccion("wronskiano", "Wronskiano")
        matriz = sp.Matrix([[y1, y2], [sp.diff(y1, x), sp.diff(y2, x)]])
        seccion.formula(rf"W({L(y)}_1, {L(y)}_2)({L(x)}) = \begin{{vmatrix}} {L(y)}_1 & {L(y)}_2 \\ "
                        rf"{L(y)}_1' & {L(y)}_2' \end{{vmatrix}}", "=",
                        rf"\begin{{vmatrix}} {L(matriz[0, 0])} & {L(matriz[0, 1])} \\ "
                        rf"{L(matriz[1, 0])} & {L(matriz[1, 1])} \end{{vmatrix}}")
        W = sp.simplify(matriz.det())
        seccion.formula(rf"W({L(x)})", "=",
                        rf"{L(matriz[0, 0])}\left({L(matriz[1, 1])}\right) - "
                        rf"{L(matriz[1, 0])}\left({L(matriz[0, 1])}\right)", "=",
                        suma(sp.expand(matriz[0, 0] * matriz[1, 1]),
                             -sp.expand(matriz[1, 0] * matriz[0, 1])))
        seccion.formula(rf"W({L(x)})", "=", W, destacada=True, ref="wronskiano")
        d.guardar("wronskiano", W)

        seccion = d.seccion("variacion_de_parametros",
                            "Variación de parámetros: $u_1(x)$ y $u_2(x)$")
        u1p = sp.simplify(-y2 * g / W)
        u2p = sp.simplify(y1 * g / W)
        seccion.formula(r"u_1'(x) = -\frac{y_2(x)\, g(x)}{W(x)}", destacada=True)
        seccion.formula(r"u_1'(x)", "=", rf"-\frac{{{L(y2)}\left({L(g)}\right)}}{{{L(W)}}}", "=", u1p)
        u1, detalle1 = integrar(u1p, x)
        formula_integral(seccion, u1p, x, u1, detalle1)
        seccion.formula(r"u_1(x)", "=", u1, destacada=True, ref="u1")
        seccion.formula(r"u_2'(x) = \frac{y_1(x)\, g(x)}{W(x)}", destacada=True)
        seccion.formula(r"u_2'(x)", "=", rf"\frac{{{L(y1)}\left({L(g)}\right)}}{{{L(W)}}}", "=", u2p)
        u2, detalle2 = integrar(u2p, x)
        formula_integral(seccion, u2p, x, u2, detalle2)
        seccion.formula(r"u_2(x)", "=", u2, destacada=True, ref="u2")
        d.guardar("u1_prima", u1p)
        d.guardar("u2_prima", u2p)
        d.guardar("u1", u1)
        d.guardar("u2", u2)

        seccion = d.seccion("solucion_particular", "Solución particular $y_p(x)$")
        seccion.formula(r"y_p(x) = u_1(x)\, y_1(x) + u_2(x)\, y_2(x)", destacada=True)
        seccion.formula(r"y_p(x)", "=", suma((u1, y1), (u2, y2)))
        desarrollada = [t for producto in (sp.expand(u1 * y1), sp.expand(u2 * y2))
                        for t in sp.sympify(producto).as_ordered_terms()]
        seccion.formula(r"y_p(x)", "=", suma(*desarrollada))
        particular = sp.collect(sp.expand(u1 * y1 + u2 * y2), sp.log(x))
        seccion.formula(r"y_p(x)", "=", particular, destacada=True, ref="solucion_particular_no_homogenea")
        d.guardar("solucion_particular_no_homogenea", particular)

    seccion = d.seccion("solucion_general", "Solución general")
    general = homogenea + particular
    if particular != 0:
        seccion.formula(rf"{L(y)}({L(x)}) = {L(y)}_h({L(x)}) + {L(y)}_p({L(x)})", destacada=True)
    seccion.formula(rf"{L(y)}({L(x)})", "=", general, r",\qquad", rf"{L(x)} > 0", destacada=True,
                    ref="solucion_general")
    d.guardar("solucion_general", general)

    # Comprobación por sustitución: la solución general anula la ecuación.
    residuo = sp.simplify(a * x ** 2 * sp.diff(general, x, 2) + b * x * sp.diff(general, x)
                          + c * general - f)
    d.validar("solucion_satisface_la_edo", residuo == 0,
              "Al sustituir y(x) en a x² y'' + b x y' + c y − f(x) el residuo se simplifica a 0.",
              detalle=f"residuo = {sp.sstr(residuo)}")

    concreta = None
    if problema.ci is not None:
        x0 = sp.sympify(problema.ci[0])
        y0, dy0 = problema.ci[1][0], problema.ci[1][1]
        seccion = d.seccion("condiciones_iniciales",
                            f"Aplicación de las condiciones iniciales "
                            f"${L(y)}({L(x0)}) = {L(y0)}$, ${L(yp)}({L(x0)}) = {L(dy0)}$")
        derivada = sp.diff(general, x)
        ecuaciones = [sp.Eq(sp.simplify(general.subs(x, x0)), y0),
                      sp.Eq(sp.simplify(derivada.subs(x, x0)), dy0)]
        seccion.formula(y0, "=", sustituir_a_la_vista(general, x, x0))
        seccion.formula(dy0, "=", sustituir_a_la_vista(derivada, x, x0))
        for ecuacion in ecuaciones:
            seccion.formula(ecuacion.lhs, "=", ecuacion.rhs)
        constantes = sp.solve(ecuaciones, [C1, C2], dict=True)
        if constantes:
            valores = constantes[0]
            seccion.formula(rf"c_1 = {L(valores[C1])},\qquad c_2 = {L(valores[C2])}", destacada=True,
                            ref="constantes")
            concreta = sp.simplify(general.subs(valores))
            seccion.formula(rf"{L(y)}({L(x)})", "=", bonita(concreta), destacada=True,
                            ref="solucion_particular")
            d.guardar("constantes", {"c_1": valores[C1], "c_2": valores[C2]})
            d.guardar("solucion_particular", concreta.subs(x, x_original))

    # Las gráficas: con CI, la solución de ese PVI; sin CI, y_p (c₁ = c₂ = 0,
    # la curva que dibuja el balotario) y algunos miembros de la familia.
    muestra = concreta if concreta is not None else general.subs({C1: 0, C2: 0})
    familia = None if concreta is not None else general.subs(C2, 0).subs(C1, sp.Symbol("C", real=True))
    intervalo = problema.intervalo or (0.05, 5.0)
    grafica_escalar(d, x, y, particular=muestra, general=familia,
                    ci=(problema.ci[0], problema.ci[1][0]) if problema.ci else None,
                    intervalo=(max(1e-3, float(intervalo[0])), float(intervalo[1])),
                    titulo="Solución particular" if concreta is None else "Solución del PVI",
                    valores_c=[sp.Integer(-2), sp.Integer(2)])
    # El resto de la capa matemática trabaja con la x original del problema.
    def a_x_original(valor):
        if isinstance(valor, sp.Basic):
            return valor.subs(x, x_original)
        if isinstance(valor, list):
            return [a_x_original(v) for v in valor]
        if isinstance(valor, dict):
            return {k: a_x_original(v) for k, v in valor.items()}
        return valor
    d.resultados = {k: a_x_original(v) for k, v in d.resultados.items()}
    return d
