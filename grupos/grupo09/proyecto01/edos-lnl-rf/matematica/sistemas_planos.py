"""Sistemas planos: lineales, no lineales y ciclos límite (Tema 2 del balotario).

Tres familias, cada una con el procedimiento que desarrolla el balotario:

* **Lineal** (2.1, 2.2) — Ẋ = AX. Forma matricial, polinomio característico,
  autovalores y autovectores, clasificación por traza, determinante y
  discriminante; la solución general, las trayectorias en coordenadas
  cartesianas (eliminando t) y las variedades invariantes de una silla. Si A
  depende de un parámetro, la clasificación se hace por tramos del parámetro.
* **No lineal** (2.3) — equilibrios por factorización y casos, jacobiano
  general, linealización y clasificación en cada punto, direcciones propias de
  las sillas, nulclinas y cuencas de atracción separadas por variedades.
* **Ciclo límite** (2.5) — coordenadas polares (r ṙ = xẋ + yẏ,
  r² θ̇ = xẏ − yẋ), región anular atrapante y las hipótesis del teorema de
  Poincaré–Bendixson. Las hipótesis se **comprueban**, no se suponen: si el
  anillo contiene un equilibrio el teorema no se aplica, y el desarrollo lo
  dice en vez de concluir algo falso.
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp

from matematica import MetodoNoAplicable
from matematica import muestreo
from matematica.analisis_estabilidad import (buscar_equilibrios, describir_conjunto, igualdad_de_factor,
                                             jacobiano, linealizar, nulclinas,
                                             regimenes_por_parametro, signo)
from matematica.desarrollo import Desarrollo, L, punto_latex, suma

TEMA = "Tema 2 · Retratos de fase y análisis cualitativo"
C, C1, C2 = sp.symbols("C c_1 c_2", real=True)
T = sp.Symbol("t", real=True)


# ---------------------------------------------------------------------------
# Detección
# ---------------------------------------------------------------------------

def identificar_lineal_plano(problema):
    """{'A': A} si el sistema es Ẋ = AX con A constante (puede tener el parámetro)."""
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo:
        return None
    estados = problema.estados
    campo = [sp.sympify(e) for e in problema.campo]
    A = sp.Matrix(campo).jacobian(estados)
    if any(entrada.has(*estados) for entrada in A):
        return None
    if any(sp.simplify(e.subs({s: 0 for s in estados})) != 0 for e in campo):
        return None
    return {"A": A}


def identificar_no_lineal_plano(problema):
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo:
        return None
    return {}


def _nombre_punto(variable, independiente):
    return sp.Symbol(variable.name + "dot") if independiente.name == "t" else sp.Symbol(variable.name + "'")


def _vista_matricial(seccion, estados, A, nombre="A"):
    x, y = estados
    seccion.formula(r"\begin{pmatrix} \dot{" + L(x) + r"} \\ \dot{" + L(y) + r"} \end{pmatrix}", "=",
                    _pmatrix(A), r"\begin{pmatrix} " + L(x) + r" \\ " + L(y) + r" \end{pmatrix}")
    seccion.formula(rf"\dot{{\mathbf{{x}}}} = {nombre}\mathbf{{x}},\qquad {nombre} = {_pmatrix(A)}",
                    destacada=True, ref="matriz")


def _pmatrix(A):
    filas = [" & ".join(L(e) for e in A.row(i)) for i in range(A.rows)]
    return r"\begin{pmatrix} " + r" \\ ".join(filas) + r" \end{pmatrix}"


# ---------------------------------------------------------------------------
# Sistema lineal (2.1 y 2.2)
# ---------------------------------------------------------------------------

def desarrollar_lineal_plano(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_lineal_plano(problema)
    if datos is None:
        raise MetodoNoAplicable("El sistema no es lineal homogéneo con coeficientes constantes.")
    A = datos["A"]
    p = problema.parametro if problema.parametro is not None and A.has(problema.parametro) else None
    d = Desarrollo("lineal_plano", "Sistema lineal en el plano", TEMA,
                   "Autovalores, autovectores y clasificación por traza y determinante",
                   tratamiento=["analitico", "cualitativo"], balotario=["2.1", "2.2"])
    seccion = d.seccion("forma_matricial", "Representación matricial del sistema")
    _vista_matricial(seccion, problema.estados, A)
    d.guardar("matriz", A)
    if p is not None:
        _lineal_con_parametro(d, problema, A, p)
    else:
        _lineal_numerico(d, problema, A)
    return d


def _lineal_con_parametro(d, problema, A, p):
    """Clasificación del origen en cada tramo del parámetro (2.2)."""
    d.familia = "lineal_plano_parametrico"
    d.nombre = f"Sistema lineal con parámetro {p}"
    d.metodo = "Traza, determinante y discriminante en función del parámetro"
    lam = sp.Symbol("lambda")
    tau, delta, disc, criticos, regimenes = regimenes_por_parametro(A, p, problema.rango_parametro)
    seccion = d.seccion("traza_determinante", "Traza, determinante y ecuación característica")
    seccion.formula(rf"\tau = \mathrm{{Tr}}(A) = {L(tau)}")
    seccion.formula(rf"\Delta = \det(A) = {L(A[0, 0])}\left({L(A[1, 1])}\right) - "
                    rf"\left({L(A[0, 1])}\right)\left({L(A[1, 0])}\right) = {L(delta)}")
    caracteristica = sp.expand(lam ** 2 - tau * lam + delta)
    seccion.formula(r"\det(A - \lambda I) = \lambda^2 - \tau\lambda + \Delta = 0")
    seccion.formula(polinomio_ordenado(caracteristica, lam), "= 0", destacada=True,
                    ref="ecuacion_caracteristica")
    d.guardar("traza", tau)
    d.guardar("determinante", delta)
    d.guardar("ecuacion_caracteristica", caracteristica)

    seccion = d.seccion("discriminante", "Discriminante y autovalores")
    seccion.formula(rf"D = \tau^2 - 4\Delta = {L(sp.expand(tau ** 2))} - 4\left({L(delta)}\right)")
    seccion.formula("D", "=", sp.expand(disc), destacada=True, ref="discriminante")
    raiz = sp.sqrt(sp.expand(disc))
    seccion.formula(r"\lambda_{1,2}", "=", rf"\frac{{{L(tau)} \pm {L(raiz)}}}{{2}}", destacada=True)
    d.guardar("discriminante", sp.expand(disc))
    d.guardar("valores_criticos", criticos)

    seccion = d.seccion("clasificacion_por_parametro",
                        f"Clasificación según el parámetro ${L(p)}$")
    for regimen in regimenes:
        condicion = describir_conjunto(regimen.conjunto, p)
        signos = []
        if regimen.es_punto:
            signos.append(rf"\tau = {L(regimen.traza)}")
            signos.append(rf"D = {L(regimen.discriminante)}")
        else:
            prueba = _prueba(regimen.conjunto)
            signos.append(rf"\tau {_rel(regimen.traza.subs(p, prueba))} 0")
            signos.append(rf"D {_rel(regimen.discriminante.subs(p, prueba))} 0")
        seccion.formula(rf"{condicion} \implies " + r",\quad ".join(signos), r"\implies",
                        rf"\lambda_{{1,2}} = {L(regimen.autovalores)}")
        seccion.formula(rf"{condicion} \implies \text{{{descripcion(regimen.tipo, regimen.estabilidad)}}}",
                        destacada=True)
    d.guardar("regimenes", regimenes)
    coherentes = all(
        coherente_con_autovalores_numericos(
            A.subs(p, next(iter(r.conjunto)) if r.es_punto else _prueba(r.conjunto)), r.tipo, r.estabilidad)
        for r in regimenes)
    d.validar("regimenes_contra_autovalores_numericos", coherentes,
              "En un valor de prueba de cada régimen, los autovalores calculados con numpy tienen el "
              "tipo y la estabilidad de la clasificación.", tipo="numerica")
    d.concluir("Clasificación del origen: " + "; ".join(
        f"{_texto_conjunto(r.conjunto, p)}: {r.tipo}" for r in regimenes) + ".")

    # Gráficas: plano traza-determinante con el recorrido del parámetro, y un
    # retrato de fase por régimen con un valor representativo.
    _grafica_traza_determinante(d, tau, delta, p, regimenes, problema)
    for i, regimen in enumerate(regimenes[:5], 1):
        valor = next(iter(regimen.conjunto)) if regimen.es_punto else _prueba(regimen.conjunto)
        A_num = A.subs(p, valor)
        _retrato_lineal(d, problema, A_num, clave=f"retrato_fase_{i}",
                        titulo=f"{regimen.tipo.capitalize()} ({p} = {sp.sstr(valor)})")


def coherente_con_autovalores_numericos(matriz, tipo, estabilidad):
    """Contraste independiente de la clasificación exacta con los autovalores de numpy."""
    autovalores = np.linalg.eigvals(np.array(sp.Matrix(matriz).evalf(), dtype=float))
    reales = np.abs(autovalores.imag) < 1e-7
    partes_reales = autovalores.real
    if "silla" in tipo:
        forma = reales.all() and partes_reales.min() < 0 < partes_reales.max()
    elif tipo.startswith("centro"):
        forma = not reales.any() and np.abs(partes_reales).max() < 1e-9
    elif tipo.startswith("foco"):
        forma = not reales.any() and np.abs(partes_reales).min() > 1e-9
    elif tipo.startswith("nodo"):
        forma = reales.all() and (partes_reales.max() < 0 or partes_reales.min() > 0)
    else:
        return True        # autovalor nulo: no hay contraste numérico que decida
    if estabilidad.startswith("asintóticamente estable"):
        signo_ok = partes_reales.max() < 0
    elif estabilidad.startswith("inestable"):
        signo_ok = partes_reales.max() > 0
    else:
        signo_ok = True
    return bool(forma and signo_ok)


def descripcion(tipo, estabilidad):
    """'Nodo asintóticamente estable', 'Punto silla (inestable)', 'Centro, estable (no asintóticamente)'."""
    if tipo == "punto silla":
        return "Punto silla (inestable)"
    if estabilidad.startswith("asintóticamente estable") and tipo.endswith(" estable"):
        return _mayuscula(tipo[: -len("estable")] + "asintóticamente estable")
    if estabilidad == "inestable" and tipo.endswith("inestable"):
        return _mayuscula(tipo)
    return f"{_mayuscula(tipo)}, {estabilidad}"


def polinomio_ordenado(expresion, variable):
    """λ² + γλ + 4 (potencias decrecientes), no γλ + λ² + 4."""
    try:
        polinomio = sp.Poly(sp.expand(expresion), variable)
    except sp.PolynomialError:
        return L(expresion)
    terminos = [(sp.factor(c), variable ** k[0]) if k[0] else sp.factor(c)
                for k, c in sorted(polinomio.terms(), key=lambda t: -t[0][0])]
    return suma(*terminos)


def _rel(valor):
    s = signo(valor)
    return {1: ">", -1: "<", 0: "="}.get(s, r"\gtrless")


def _mayuscula(texto):
    return texto[:1].upper() + texto[1:]


def _texto_conjunto(conjunto, p):
    """El tramo del parámetro en texto plano: '0 < gamma < 4', 'gamma = 4'."""
    if isinstance(conjunto, sp.FiniteSet):
        return " o ".join(f"{p} = {sp.sstr(v)}" for v in conjunto)
    if isinstance(conjunto, sp.Interval):
        a, b = conjunto.start, conjunto.end
        izquierda = "" if a.is_infinite else f"{sp.sstr(a)} {'<' if conjunto.left_open else '≤'} "
        derecha = "" if b.is_infinite else f" {'<' if conjunto.right_open else '≤'} {sp.sstr(b)}"
        return f"{izquierda}{p}{derecha}" if (izquierda or derecha) else f"{p} ∈ ℝ"
    if isinstance(conjunto, sp.Union):
        return " o ".join(_texto_conjunto(a, p) for a in conjunto.args)
    return f"{p} ∈ {sp.sstr(conjunto)}"


def _prueba(conjunto):
    if isinstance(conjunto, sp.FiniteSet):
        return next(iter(conjunto))
    intervalo = conjunto if isinstance(conjunto, sp.Interval) else conjunto.args[0]
    a, b = intervalo.start, intervalo.end
    if a.is_infinite and b.is_infinite:
        return sp.Integer(0)
    if a.is_infinite:
        return b - 1
    if b.is_infinite:
        return a + 1
    return (a + b) / 2


def _lineal_numerico(d, problema, A):
    x, y = problema.estados
    lam = sp.Symbol("lambda")
    lin = linealizar(list(A * sp.Matrix([x, y])), [x, y], (0, 0))
    seccion = d.seccion("autovalores", "Autovalores y autovectores")
    seccion.formula(r"\det(A - \lambda I) = 0")
    matriz_lambda = A - lam * sp.eye(2)
    seccion.formula(r"\begin{vmatrix} " + " & ".join(L(e) for e in matriz_lambda.row(0)) + r" \\ "
                    + " & ".join(L(e) for e in matriz_lambda.row(1)) + r" \end{vmatrix}", "=",
                    sp.factor(lin.polinomio), "= 0")
    seccion.formula(r",\quad ".join(rf"\lambda_{{{i}}} = {L(v)}" for i, v in enumerate(lin.autovalores, 1)),
                    destacada=True, ref="autovalores")
    d.guardar("autovalores", lin.autovalores)
    for i, (valor, vector) in enumerate(lin.autovectores, 1):
        menos = A - valor * sp.eye(2)
        seccion.formula(rf"(A - \lambda_{{{i}}} I)\mathbf{{v}}_{{{i}}} = \mathbf{{0}} \implies {_pmatrix(menos)}"
                        rf"\begin{{pmatrix}} v_{{{i}1}} \\ v_{{{i}2}} \end{{pmatrix}} = "
                        r"\begin{pmatrix} 0 \\ 0 \end{pmatrix} \implies", rf"\mathbf{{v}}_{{{i}}} = {_pmatrix(vector)}",
                        destacada=True)
    d.guardar("autovectores", lin.autovectores)

    seccion = d.seccion("clasificacion", "Clasificación del punto de equilibrio $(0, 0)$")
    seccion.formula(rf"\det(A) = {L(lin.determinante)} {_rel(lin.determinante)} 0,\qquad "
                    rf"\mathrm{{Tr}}(A) = {L(lin.traza)},\qquad D = \tau^2 - 4\Delta = {L(lin.discriminante)}")
    if lin.tipo == "punto silla":
        orden = sorted(lin.autovalores, key=lambda v: float(sp.N(v)))
        seccion.formula(rf"\lambda = {L(orden[0])} < 0 < {L(orden[1])}")
    seccion.formula(rf"(0, 0) \text{{ es un {lin.tipo} ({lin.estabilidad})}}", destacada=True,
                    ref="clasificacion")
    d.guardar("clasificacion", {"tipo": lin.tipo, "estabilidad": lin.estabilidad})
    d.guardar("linealizacion", lin)
    d.validar("clasificacion_contra_autovalores_numericos",
              coherente_con_autovalores_numericos(A, lin.tipo, lin.estabilidad),
              "Los autovalores calculados con numpy tienen el tipo y la estabilidad de la clasificación "
              "exacta.", tipo="numerica")

    _solucion_general_lineal(d, problema, A, lin)
    if not problema.pedidos or problema.pedidos & {"trayectorias", "retrato_fase", "orbitas"}:
        _trayectorias_lineales(d, problema, A, lin)
    if lin.tipo == "punto silla":
        _variedades_lineales(d, problema, lin)
    d.concluir(f"El origen es un {lin.tipo} ({lin.estabilidad}).")
    _retrato_lineal(d, problema, A, clave="retrato_fase", titulo="Retrato de fase", lin=lin)


def _solucion_general_lineal(d, problema, A, lin):
    """X(t) = c₁e^{λ₁t}v₁ + c₂e^{λ₂t}v₂ (o su forma real), y la CI si se dio."""
    x, y = problema.estados
    t = problema.x
    valores = lin.autovalores
    reales = all(sp.im(v) == 0 for v in valores)
    if reales and len(lin.autovectores) == 2:
        (l1, v1), (l2, v2) = lin.autovectores
        solucion = C1 * sp.exp(l1 * t) * v1 + C2 * sp.exp(l2 * t) * v2
    elif reales:                                     # autovalor doble no diagonalizable
        l1, v1 = lin.autovectores[0]
        w = (A - l1 * sp.eye(2)).gauss_jordan_solve(v1)[0]
        w = w.subs({s: 0 for s in w.free_symbols})
        solucion = C1 * sp.exp(l1 * t) * v1 + C2 * sp.exp(l1 * t) * (t * v1 + w)
    else:
        valor = next(v for v in valores if sp.im(v) > 0)
        vector = (A - valor * sp.eye(2)).nullspace()[0]
        alfa, beta = sp.re(valor), sp.im(valor)
        a, b = vector.applyfunc(sp.re), vector.applyfunc(sp.im)
        uno = sp.exp(alfa * t) * (a * sp.cos(beta * t) - b * sp.sin(beta * t))
        dos = sp.exp(alfa * t) * (a * sp.sin(beta * t) + b * sp.cos(beta * t))
        solucion = C1 * uno + C2 * dos
    solucion = solucion.applyfunc(sp.simplify)
    seccion = d.seccion("solucion_general", "Solución general del sistema")
    seccion.formula(rf"{L(x)}({L(t)}) = {L(solucion[0])},\qquad {L(y)}({L(t)}) = {L(solucion[1])}",
                    destacada=True, ref="solucion_general")
    d.guardar("solucion_general", solucion)
    residuo = (solucion.diff(t) - A * solucion).applyfunc(sp.simplify)
    d.validar("solucion_general_satisface_el_sistema", residuo.is_zero_matrix,
              "X(t) sustituida en X' = AX da X' − AX ≡ 0 para todo c₁, c₂.")
    if problema.ci is not None:
        t0 = problema.ci[0]
        x0, y0 = problema.ci[1]
        constantes = sp.solve([sp.Eq(solucion[0].subs(t, t0), x0), sp.Eq(solucion[1].subs(t, t0), y0)],
                              [C1, C2], dict=True)
        if constantes:
            particular = solucion.subs(constantes[0]).applyfunc(sp.simplify)
            seccion.formula(rf"{L(x)}({L(t0)}) = {L(x0)},\quad {L(y)}({L(t0)}) = {L(y0)} \implies "
                            rf"c_1 = {L(constantes[0][C1])},\quad c_2 = {L(constantes[0][C2])}")
            seccion.formula(rf"{L(x)}({L(t)}) = {L(particular[0])},\qquad {L(y)}({L(t)}) = {L(particular[1])}",
                            destacada=True, ref="solucion_particular")
            d.guardar("solucion_particular", particular)
            d.validar("condicion_inicial_exacta",
                      (particular.subs(t, t0) - sp.Matrix([x0, y0])).applyfunc(sp.simplify).is_zero_matrix,
                      "La solución particular pasa por la condición inicial.")
    else:
        x0s, y0s = sp.symbols(f"{x.name}_0 {y.name}_0", real=True)
        constantes = sp.solve([sp.Eq(solucion[0].subs(t, 0), x0s), sp.Eq(solucion[1].subs(t, 0), y0s)],
                              [C1, C2], dict=True)
        if constantes:
            con_ci = solucion.subs(constantes[0]).applyfunc(sp.simplify)
            seccion.formula(rf"{L(x)}({L(t)}) = {L(con_ci[0])},\qquad {L(y)}({L(t)}) = {L(con_ci[1])}")


def _trayectorias_lineales(d, problema, A, lin):
    """Ecuación de las órbitas eliminando t: dy/dx = ẏ/ẋ (2.1)."""
    x, y = problema.estados
    f, g = list(A * sp.Matrix([x, y]))
    partes = sp.separatevars(sp.simplify(g / f), [x, y], dict=True) if f != 0 else None
    seccion = d.seccion("trayectorias", "Trayectorias en coordenadas cartesianas (órbitas)")
    if partes:
        k = sp.simplify(partes["coeff"] * partes[x])
        h = partes[y]
        seccion.formula(rf"\frac{{d{L(y)}}}{{d{L(x)}}} = \frac{{\dot{{{L(y)}}}}}{{\dot{{{L(x)}}}}}", "=",
                        rf"\frac{{{L(g)}}}{{{L(f)}}}")
        seccion.formula(rf"\frac{{d{L(y)}}}{{{L(h)}}}", "=", rf"{L(k)}\, d{L(x)}")
        izquierda = sp.integrate(1 / h, y).replace(sp.log, lambda u: sp.log(sp.Abs(u)))
        derecha = sp.integrate(k, x).replace(sp.log, lambda u: sp.log(sp.Abs(u)))
        seccion.formula(rf"\int \frac{{d{L(y)}}}{{{L(h)}}}", "=", rf"\int {L(k)}\, d{L(x)}")
        seccion.formula(izquierda, "=", derecha + sp.Symbol("C_1"))
        combinacion = sp.expand(izquierda - derecha)
        if combinacion.has(sp.log):
            invariante = _invariante_por_logaritmos(seccion, combinacion, [x, y])
        else:
            # Sin logaritmos la integración ya da un polinomio (el centro: y²/2 + 9x²/2 = C₁):
            # basta quitar denominadores.
            denominadores = [sp.fraction(sp.nsimplify(c))[1] for c in sp.Poly(combinacion, x, y).coeffs()]
            invariante = sp.expand(combinacion * sp.ilcm(*denominadores, 1))
            principal = sp.Poly(invariante, x, y).coeffs()[0]
            if principal.is_negative:
                invariante = -invariante
    else:
        invariante = _invariante_en_coordenadas_propias(seccion, lin, x, y)
    if invariante is None:
        seccion.texto("Las órbitas no admiten aquí una ecuación cartesiana cerrada; se describen "
                      "con la solución general y el retrato de fase.")
        return
    derivada = sp.simplify(sp.diff(invariante, x) * f + sp.diff(invariante, y) * g)
    d.validar("invariante_de_las_orbitas", derivada == 0,
              f"d/dt({sp.sstr(invariante)}) se anula a lo largo del flujo: es constante en cada órbita.")
    seccion.formula(invariante, "= C", destacada=True, ref="ecuacion_trayectorias")
    d.guardar("ecuacion_trayectorias", sp.Eq(invariante, C))
    explicita = sp.solve(sp.Eq(invariante, C), y)
    if explicita:
        seccion.formula(L(y), "=", r",\; ".join(L(e) for e in explicita))


def _invariante_por_logaritmos(seccion, combinacion, estados):
    """Σ aᵢ ln|uᵢ| = C₁ → Π |uᵢ|^{aᵢ} = K → exponentes enteros (y²x³ = C en el 2.1)."""
    coeficientes = {}
    for termino in sp.Add.make_args(combinacion):
        coeficiente, resto = termino.as_independent(*estados, as_Add=False)
        if not isinstance(resto, sp.log):
            return None
        coeficientes[sp.sympify(resto.args[0]).replace(sp.Abs, lambda u: u)] = coeficiente
    if not coeficientes or not all(c.is_Rational for c in coeficientes.values()):
        return None
    suma_logs = suma(*[(c, sp.log(sp.Abs(u))) for u, c in coeficientes.items()])
    seccion.formula(suma_logs, "= C_1")
    producto_abs = sp.Mul(*[sp.Pow(sp.Abs(u), c, evaluate=False) if c != 1 else sp.Abs(u)
                            for u, c in coeficientes.items()],
                          evaluate=False)
    seccion.formula(rf"\ln\left({L(producto_abs)}\right) = C_1 \implies {L(producto_abs)} = K")
    mcm = sp.ilcm(*[sp.fraction(c)[1] for c in coeficientes.values()]) if len(coeficientes) > 1 \
        else sp.fraction(list(coeficientes.values())[0])[1]
    enteros = {u: c * mcm for u, c in coeficientes.items()}
    if any(c < 0 for c in enteros.values()) and all(c <= 0 for c in enteros.values()):
        enteros = {u: -c for u, c in enteros.items()}
    invariante = sp.Mul(*[u ** c for u, c in enteros.items()])
    return invariante


def _invariante_en_coordenadas_propias(seccion, lin, x, y):
    """En la base de autovectores ξ' = λ₁ξ, η' = λ₂η, así que |η|^{λ₁}|ξ|^{−λ₂} es constante."""
    if len(lin.autovectores) != 2 or any(sp.im(v) != 0 for v, _ in lin.autovectores):
        return None
    (l1, v1), (l2, v2) = lin.autovectores
    P = sp.Matrix.hstack(v1, v2)
    xi, eta = (sp.expand(c) for c in P.inv() * sp.Matrix([x, y]))
    seccion.formula(rf"\begin{{pmatrix}} \xi \\ \eta \end{{pmatrix}} = P^{{-1}}\begin{{pmatrix}} {L(x)} \\ {L(y)} "
                    rf"\end{{pmatrix}}:\qquad \xi = {L(xi)},\quad \eta = {L(eta)}")
    seccion.formula(rf"\dot{{\xi}} = {L(l1)}\,\xi,\quad \dot{{\eta}} = {L(l2)}\,\eta \implies "
                    rf"|\eta|^{{{L(l1)}}}\,|\xi|^{{{L(-l2)}}} = K")
    # Los factores constantes de ξ y η se absorben en K: (y − 2x)³(2x + y) = C
    # en vez de (−x/2 + y/4)³(x/2 + y/4) = K.
    xi, eta = sp.primitive(xi)[1], sp.primitive(eta)[1]
    if l1.is_Rational and l2.is_Rational:
        mcm = sp.ilcm(sp.fraction(l1)[1], sp.fraction(l2)[1])
        p_eta, p_xi = l1 * mcm, -l2 * mcm
        if p_eta < 0 and p_xi < 0:
            p_eta, p_xi = -p_eta, -p_xi
        return sp.expand(eta) ** p_eta * sp.expand(xi) ** p_xi
    return sp.Abs(eta) ** l1 * sp.Abs(xi) ** (-l2)


def _variedades_lineales(d, problema, lin):
    x, y = problema.estados
    seccion = d.seccion("variedades", "Variedades invariantes $W^s$ y $W^u$")
    for valor, vector in lin.autovectores:
        estable = sp.N(valor) < 0
        recta = sp.simplify(vector[1] * x - vector[0] * y)
        nombre = "W^s" if estable else "W^u"
        limite = r"+\infty" if estable else r"-\infty"
        seccion.formula(rf"{nombre}(0,0) = \mathrm{{gen}}\left\{{{_pmatrix(vector)}\right\}} = "
                        rf"\left\{{({L(x)}, {L(y)}) : {L(igualdad_de_factor(recta, [x, y]))}\right\}}",
                        destacada=True, ref="variedad_estable" if estable else "variedad_inestable")
        seccion.formula(rf"\lim_{{t \to {limite}}} \mathbf{{x}}(t) = (0, 0)\quad \forall\, \mathbf{{x}}_0 \in {nombre}")
        d.guardar("variedad_estable" if estable else "variedad_inestable", igualdad_de_factor(recta, [x, y]))


def _retrato_lineal(d, problema, A, clave, titulo, lin=None):
    x, y = problema.estados
    f = muestreo.campo_plano(list(A * sp.Matrix([x, y])), [x, y])
    caja = ((-3.0, 3.0), (-3.0, 3.0))
    angulos = np.linspace(0, 2 * np.pi, 13)[:-1]
    semillas = [(2.6 * math.cos(a), 2.6 * math.sin(a)) for a in angulos] + \
               [(0.6 * math.cos(a), 0.6 * math.sin(a)) for a in angulos[::2]]
    orbitas = muestreo.retrato(f, caja, semillas, tiempo=8.0)
    capas = [muestreo.campo_de_direcciones(f, caja), muestreo.capas_de_orbitas(orbitas)]
    lin = lin or linealizar(list(A * sp.Matrix([x, y])), [x, y], (0, 0))
    for valor, direccion in lin.direcciones():
        rol = "variedad_estable" if valor < 0 else "variedad_inestable"
        if lin.tipo != "punto silla":
            rol = "direccion"
        capas.append({"tipo": "linea", "rol": rol, "nombre": f"Dirección propia λ = {valor:g}",
                      "x": [-3.2 * direccion[0], 3.2 * direccion[0]],
                      "y": [-3.2 * direccion[1], 3.2 * direccion[1]]})
    if problema.ci is not None and clave == "retrato_fase":
        orbita = muestreo.trayectoria(f, [float(sp.N(c)) for c in problema.ci[1]], 8.0, caja)
        if orbita:
            capas.append({"tipo": "linea", "rol": "trayectoria", "nombre": "Órbita con la CI dada",
                          "x": orbita["x"], "y": orbita["y"]})
    estado = {"asintóticamente estable": "estable", "inestable": "inestable"}.get(lin.estabilidad, "indefinido")
    capas.append({"tipo": "puntos", "rol": f"equilibrio:{estado}", "nombre": f"(0, 0): {lin.tipo}",
                  "x": [0.0], "y": [0.0]})
    d.grafica({"clave": clave, "titulo": titulo, "ejes": {"x": x.name, "y": y.name},
               "rango": {"x": list(caja[0]), "y": list(caja[1])}, "capas": capas, "cuadrada": True})


def _grafica_traza_determinante(d, tau, delta, p, regimenes, problema):
    """Plano (τ, Δ): la parábola Δ = τ²/4 y el recorrido del sistema al variar el parámetro."""
    inferior, superior = problema.rango_parametro or (None, None)
    criticos = [float(c) for c in d.resultados.get("valores_criticos", [])]
    a = inferior if inferior is not None else (min(criticos) - 2 if criticos else -4)
    b = superior if superior is not None else (max(criticos) + 3 if criticos else 4)
    valores = np.linspace(float(a), float(b), 200)
    ts = muestreo.funcion(tau, [p])(valores)
    ds = muestreo.funcion(delta, [p])(valores)
    ts, ds = np.broadcast_to(ts, valores.shape), np.broadcast_to(ds, valores.shape)
    ancho = max(abs(np.nanmin(ts)), abs(np.nanmax(ts)), 2.0) * 1.2
    parabola = np.linspace(-ancho, ancho, 200)
    capas = [{"tipo": "linea", "rol": "referencia", "nombre": "Δ = τ²/4 (D = 0)",
              "x": parabola.tolist(), "y": (parabola ** 2 / 4).tolist()},
             {"tipo": "linea", "rol": "trayectoria", "nombre": f"Recorrido con {p} ∈ [{a:g}, {b:g}]",
              "x": ts.tolist(), "y": ds.tolist()}]
    for c in criticos:
        capas.append({"tipo": "puntos", "rol": "critico", "nombre": f"{p} = {c:g}",
                      "x": [float(sp.N(tau.subs(p, c)))], "y": [float(sp.N(delta.subs(p, c)))]})
    alto = max(float(np.nanmax(ds)), ancho ** 2 / 4) * 1.15
    d.grafica({"clave": "traza_determinante", "titulo": "Plano traza-determinante",
               "ejes": {"x": "τ = Tr(A)", "y": "Δ = det(A)"},
               "rango": {"x": [-ancho, ancho], "y": [min(-1.0, float(np.nanmin(ds)) * 1.2), alto]},
               "capas": capas})


# ---------------------------------------------------------------------------
# Sistema no lineal (2.3)
# ---------------------------------------------------------------------------

def desarrollar_no_lineal_plano(problema, datos=None) -> Desarrollo:
    x, y = problema.estados
    p = problema.parametro if problema.tiene_parametro else None
    campo = [sp.sympify(e) for e in problema.campo] if p is not None else problema.campo_con()
    f, g = campo
    d = Desarrollo("no_lineal_plano", "Sistema no lineal en el plano", TEMA,
                   "Equilibrios, linealización (jacobiano) y clasificación; nulclinas y cuencas",
                   tratamiento=["cualitativo", "numerico"], balotario=["2.3"])
    region = problema.region
    equilibrios = seccion_equilibrios(d, f, g, x, y, region)
    J = seccion_jacobiano(d, f, g, x, y)
    if p is None:
        clasificados = seccion_clasificacion(d, f, g, x, y, equilibrios, J)
    else:
        clasificados = seccion_clasificacion_parametrica(d, f, g, x, y, equilibrios, J, p, problema)
    seccion = d.seccion("nulclinas", "Nulclinas y regiones de flujo")
    curvas = nulclinas([f, g], [x, y])
    seccion.formula(rf"\mathcal{{N}}_{{{L(x)}}}\; (\dot{{{L(x)}}} = 0):\quad " +
                    r" \;\lor\; ".join(L(c) for c in curvas[0]) + r"\quad (\text{flujo vertical})",
                    destacada=True)
    seccion.formula(rf"\mathcal{{N}}_{{{L(y)}}}\; (\dot{{{L(y)}}} = 0):\quad " +
                    r" \;\lor\; ".join(L(c) for c in curvas[1]) + r"\quad (\text{flujo horizontal})",
                    destacada=True)
    d.guardar("nulclinas", {x.name: curvas[0], y.name: curvas[1]})
    if p is None:
        retrato_no_lineal(d, problema, [f, g], x, y, clasificados, curvas)
    else:
        valor = problema.valor_representativo()
        numerico = [e.subs(p, valor) for e in (f, g)]
        puntos = [{"punto": tuple(sp.sympify(c).subs(p, valor) for c in e["punto"]),
                   "linealizacion": linealizar(numerico, [x, y],
                                               tuple(sp.sympify(c).subs(p, valor) for c in e["punto"]))}
                  for e in clasificados]
        for e in puntos:
            e["tipo"] = e["linealizacion"].tipo
        retrato_no_lineal(d, problema, numerico, x, y, puntos, nulclinas(numerico, [x, y]),
                          titulo=f"Retrato de fase ({p} = {valor:g})")
    return d


def seccion_equilibrios(d, f, g, x, y, region):
    seccion = d.seccion("equilibrios", "Puntos de equilibrio" + (" en la región" if region else ""))
    factores_f = nulclinas([f], [x, y])[0]
    factores_g = nulclinas([g], [x, y])[0]
    seccion.formula(rf"\dot{{{L(x)}}} = {L(f)} = 0 \iff " + r" \;\lor\; ".join(L(c) for c in factores_f))
    seccion.formula(rf"\dot{{{L(y)}}} = {L(g)} = 0 \iff " + r" \;\lor\; ".join(L(c) for c in factores_g))
    if region:
        partes = []
        for estado, (inferior, superior) in region.items():
            if inferior is not None:
                partes.append(rf"{L(estado)} \ge {L(sp.nsimplify(inferior))}")
            if superior is not None:
                partes.append(rf"{L(estado)} \le {L(sp.nsimplify(superior))}")
        seccion.formula(r"\text{Región: }" + r",\; ".join(partes))
    equilibrios, informe = buscar_equilibrios([f, g], [x, y], region=region)
    # Si una ecuación fija una variable (ẋ = y ⟹ y = 0), se sustituye en la
    # otra y se factoriza: ẏ|_{y=0} = x(1 − x) = 0, como en el 2.4 y el 3.5.
    fijada = _variable_fijada(factores_f, [x, y]) if len(factores_f) == 1 else None
    if fijada is not None and len(factores_g) == 1:
        variable, valor = fijada
        otra = y if variable == x else x
        reducida = sp.factor(sp.expand(g.subs(variable, valor)))
        raices = sp.solveset(reducida, otra, domain=sp.S.Reals)
        seccion.formula(rf"{L(variable)} = {L(valor)} \implies \dot{{{L(y)}}}\big|_{{{L(variable)} = {L(valor)}}} = "
                        rf"{L(reducida)} = 0 \iff {L(otra)} \in {L(raices)}")
        for i, e in enumerate(equilibrios, 1):
            seccion.formula(rf"P_{{{i}}} = {punto_latex(e.punto)}", destacada=True)
    else:
        for i, e in enumerate(equilibrios, 1):
            caso = r",\quad ".join(L(c) for c in e.caso) if e.caso else ""
            seccion.formula(caso, r"\implies" if caso else "", rf"P_{{{i}}} = {punto_latex(e.punto)}",
                            destacada=True)
    if informe.get("fuera_de_region"):
        seccion.texto(f"Se descartan {informe['fuera_de_region']} equilibrio(s) fuera de la región.")
    if informe.get("no_aislados"):
        d.advertir("El sistema tiene curvas de equilibrios (no aislados).")
    d.guardar("equilibrios", [e.punto for e in equilibrios])
    return equilibrios


def _variable_fijada(factores, estados):
    """(variable, valor) si la única nulclina es 'variable = constante'."""
    igualdad = factores[0]
    expresion = sp.expand(igualdad.lhs - igualdad.rhs)
    presentes = [s for s in estados if expresion.has(s)]
    if len(presentes) != 1 or sp.degree(expresion, presentes[0]) != 1:
        return None
    valor = sp.solve(expresion, presentes[0])
    return (presentes[0], valor[0]) if valor else None


def seccion_polar(d, f, g, x, y, titulo="Transformación a coordenadas polares"):
    """La deducción de ṙ y θ̇ como en el balotario (2.5, 3.4). Devuelve (ṙ, θ̇, rṙ, r²θ̇)."""
    r_punto, theta_punto, radial, angular = forma_polar(f, g, x, y)
    seccion = d.seccion("polares", titulo)
    seccion.formula(rf"{L(x)} = r\cos\theta,\qquad {L(y)} = r\sin\theta,\qquad r^2 = {L(x)}^2 + {L(y)}^2")
    seccion.formula(rf"r\dot{{r}} = {L(x)}\dot{{{L(x)}}} + {L(y)}\dot{{{L(y)}}},\qquad "
                    rf"r^2\dot{{\theta}} = {L(x)}\dot{{{L(y)}}} - {L(y)}\dot{{{L(x)}}}")
    seccion.rotulo(r"\text{Deducción de la ecuación radial}")
    seccion.formula(rf"{L(x)}\dot{{{L(x)}}} + {L(y)}\dot{{{L(y)}}} = {L(x)}\left[{L(f)}\right] + "
                    rf"{L(y)}\left[{L(g)}\right]")
    seccion.formula(r"=", sp.simplify(sp.expand(x * f + y * g)), "=", radial)
    seccion.formula(rf"r\dot{{r}} = {L(sp.factor_terms(radial))} \implies \dot{{r}}", "=", r_punto,
                    destacada=True, ref="r_punto")
    seccion.rotulo(r"\text{Deducción de la ecuación angular}")
    seccion.formula(rf"{L(x)}\dot{{{L(y)}}} - {L(y)}\dot{{{L(x)}}} = {L(x)}\left[{L(g)}\right] - "
                    rf"{L(y)}\left[{L(f)}\right]")
    seccion.formula(r"=", sp.simplify(sp.expand(x * g - y * f)), "=", angular)
    seccion.formula(rf"r^2\dot{{\theta}} = {L(angular)} \implies \dot{{\theta}}", "=", theta_punto,
                    destacada=True, ref="theta_punto")
    d.guardar("r_punto", r_punto)
    d.guardar("theta_punto", theta_punto)
    return r_punto, theta_punto, radial, angular


def seccion_jacobiano(d, f, g, x, y):
    seccion = d.seccion("jacobiano", "Matriz jacobiana general")
    fx, fy, gx, gy = (sp.expand(sp.diff(f, x)), sp.expand(sp.diff(f, y)),
                      sp.expand(sp.diff(g, x)), sp.expand(sp.diff(g, y)))
    seccion.formula(rf"f({L(x)}, {L(y)}) = {L(sp.expand(f))} \implies "
                    rf"\frac{{\partial f}}{{\partial {L(x)}}} = {L(fx)},\quad \frac{{\partial f}}{{\partial {L(y)}}} = {L(fy)}")
    seccion.formula(rf"g({L(x)}, {L(y)}) = {L(sp.expand(g))} \implies "
                    rf"\frac{{\partial g}}{{\partial {L(x)}}} = {L(gx)},\quad \frac{{\partial g}}{{\partial {L(y)}}} = {L(gy)}")
    J = sp.Matrix([[fx, fy], [gx, gy]])
    seccion.formula(rf"J({L(x)}, {L(y)}) = {_pmatrix(J)}", destacada=True, ref="jacobiano")
    d.guardar("jacobiano", J)
    return J


def seccion_clasificacion(d, f, g, x, y, equilibrios, J):
    seccion = d.seccion("clasificacion", "Clasificación y estabilidad de cada punto de equilibrio")
    clasificados = []
    for i, e in enumerate(equilibrios, 1):
        lin = linealizar([f, g], [x, y], e.punto, matriz_general=J)
        seccion.rotulo(rf"\text{{Análisis en }} P_{{{i}}}{punto_latex(e.punto)}")
        if not lin.definida:
            seccion.texto(lin.nota)
            clasificados.append({"punto": e.punto, "linealizacion": lin, "tipo": "no diferenciable"})
            continue
        seccion.formula(rf"J{punto_latex(e.punto)} = {_pmatrix(lin.jacobiano)}")
        seccion.formula(rf"\mathrm{{Tr}}(J) = {L(lin.traza)},\qquad \det(J) = {L(lin.determinante)}")
        seccion.formula(rf"\det(J - \lambda I) = {L(sp.factor(lin.polinomio))} = 0 \implies "
                        rf"\lambda = {L(lin.autovalores)}")
        if lin.tipo == "centro":
            # Hartman–Grobman no aplica: con λ imaginarios puros el sistema no
            # lineal puede tener un centro o un foco débil.
            lin.tipo, lin.estabilidad = "centro lineal", "no concluyente (no hiperbólico)"
        seccion.formula(r",\; ".join(_autovalor_con_signo(k, v) for k, v in enumerate(lin.autovalores, 1)),
                        r"\implies", rf"\text{{{descripcion(lin.tipo, lin.estabilidad)}}}", destacada=True)
        if lin.tipo == "centro lineal":
            seccion.texto("Los autovalores son imaginarios puros: el equilibrio no es hiperbólico y la "
                          "linealización no decide su estabilidad en el sistema no lineal (puede ser un "
                          "centro o un foco débil); hace falta un argumento no lineal, como una integral "
                          "primera.")
        if lin.tipo == "punto silla":
            for valor, vector in lin.autovectores:
                etiqueta = "s" if sp.N(valor) < 0 else "u"
                pendiente = sp.simplify(vector[1] / vector[0]) if vector[0] != 0 else sp.oo
                seccion.formula(rf"\mathbf{{v}}^{{({etiqueta})}} = {_pmatrix(vector)}\quad "
                                rf"(\lambda = {L(valor)},\ \text{{pendiente }} {L(pendiente)})")
        clasificados.append({"punto": e.punto, "linealizacion": lin, "tipo": lin.tipo})
    d.guardar("clasificacion", [{"punto": c["punto"], "tipo": c["tipo"],
                                 "estabilidad": c["linealizacion"].estabilidad,
                                 "autovalores": c["linealizacion"].autovalores}
                                for c in clasificados])
    d.guardar("linealizaciones", [c["linealizacion"] for c in clasificados])
    definidos = [c for c in clasificados if c["linealizacion"].definida]
    if definidos:
        d.validar("clasificacion_contra_autovalores_numericos",
                  all(coherente_con_autovalores_numericos(c["linealizacion"].jacobiano, c["tipo"],
                                                          c["linealizacion"].estabilidad) for c in definidos),
                  "En cada equilibrio, los autovalores del jacobiano calculados con numpy tienen el tipo "
                  "y la estabilidad de la clasificación exacta.", tipo="numerica")
        d.concluir("Equilibrios: " + "; ".join(
            f"P{i} = ({', '.join(sp.sstr(v) for v in c['punto'])}): "
            f"{descripcion(c['tipo'], c['linealizacion'].estabilidad)}"
            for i, c in enumerate(clasificados, 1) if c["linealizacion"].definida) + ".")
    return clasificados


def _autovalor_con_signo(k, valor):
    """λₖ = −1 + √2 ≈ 0.414 > 0, como lo escribe el balotario; sin '≈' si es racional."""
    texto = rf"\lambda_{{{k}}} = {L(valor)}"
    if sp.im(valor) != 0:
        return texto
    if not valor.is_Rational:
        texto += rf" \approx {float(sp.N(valor)):.4g}"
    return texto + rf" {_rel(valor)} 0"


def seccion_clasificacion_parametrica(d, f, g, x, y, equilibrios, J, p, problema):
    """Cada equilibrio clasificado por tramos del parámetro (3.5, paso 1)."""
    seccion = d.seccion("clasificacion", f"Clasificación de los equilibrios según ${L(p)}$")
    clasificados = []
    for i, e in enumerate(equilibrios, 1):
        matriz = J.subs({x: e.punto[0], y: e.punto[1]}).applyfunc(sp.simplify)
        tau, delta, disc, criticos, regimenes = regimenes_por_parametro(matriz, p, problema.rango_parametro)
        seccion.rotulo(rf"\text{{Análisis en }} P_{{{i}}}{punto_latex(e.punto)}")
        seccion.formula(rf"J{punto_latex(e.punto)} = {_pmatrix(matriz)}")
        seccion.formula(rf"\det(J) = {L(delta)},\qquad \mathrm{{Tr}}(J) = {L(tau)},\qquad D = {L(disc)}")
        autovalores = sp.solve(sp.Eq(sp.Symbol("lambda") ** 2 - tau * sp.Symbol("lambda") + delta, 0),
                               sp.Symbol("lambda"))
        seccion.formula(r"\lambda_{1,2}", "=", r",\; ".join(L(sp.simplify(a)) for a in autovalores))
        for regimen in regimenes:
            seccion.formula(rf"{describir_conjunto(regimen.conjunto, p)} \implies "
                            rf"\text{{{descripcion(regimen.tipo, regimen.estabilidad)}}}", destacada=True)
        clasificados.append({"punto": e.punto, "regimenes": regimenes, "traza": tau,
                             "determinante": delta, "criticos": criticos})
    d.guardar("clasificacion_por_parametro", clasificados)
    return clasificados


def retrato_no_lineal(d, problema, campo, x, y, clasificados, curvas, titulo="Retrato de fase"):
    """Retrato con nulclinas, equilibrios, variedades de las sillas y órbitas de muestra.

    Además deduce las cuencas: cada rama de la variedad inestable de una silla
    se integra hasta su destino; si las dos ramas acaban en atractores
    distintos, la variedad estable de esa silla es la frontera entre sus
    cuencas (la exclusión competitiva del 2.3).
    """
    f = muestreo.campo_plano(campo, [x, y])
    puntos = [tuple(float(sp.N(c)) for c in e["punto"]) for e in clasificados]
    region = problema.region
    caja = muestreo.caja_alrededor(puntos or [(0.0, 0.0)], margen=0.35, minimo=2.0)
    if region:
        (xa, xb), (ya, yb) = caja
        lx, hx = region.get(x, (None, None))
        ly, hy = region.get(y, (None, None))
        caja = ((max(xa, lx - 0.05 * (xb - xa)) if lx is not None else xa, xb),
                (max(ya, ly - 0.05 * (yb - ya)) if ly is not None else ya, yb))
    limites = [region.get(x, (None, None)), region.get(y, (None, None))] if region else None
    semillas = muestreo.semillas_en_caja(caja, n=5, region=limites)
    orbitas = muestreo.retrato(f, caja, semillas, tiempo=15.0, ambos_sentidos=False)
    capas = [muestreo.campo_de_direcciones(f, caja), muestreo.capas_de_orbitas(orbitas)]
    for indice, (lista, rol, nombre) in enumerate(((curvas[0], "nulclina_x", f"{x}' = 0"),
                                                    (curvas[1], "nulclina_y", f"{y}' = 0"))):
        xs, ys = [], []
        for curva in lista:
            cx, cy = _muestrear_igualdad(curva, x, y, caja)
            xs += cx + [None]
            ys += cy + [None]
        capas.append({"tipo": "linea", "rol": rol, "nombre": f"Nulclina {nombre}", "x": xs, "y": ys})
    atractores = [(punto, e) for punto, e in zip(puntos, clasificados)
                  if e["linealizacion"].definida and e["linealizacion"].estable]
    cuencas = []
    for punto, e in zip(puntos, clasificados):
        lin = e["linealizacion"]
        if not lin.definida or lin.tipo != "punto silla":
            continue
        direcciones = dict((("s" if v < 0 else "u"), w) for v, w in lin.direcciones())
        ramas = muestreo.variedades(f, punto, direcciones.get("s"), direcciones.get("u"), caja,
                                    tiempo=80.0)
        for clave, rol, nombre in (("estable", "variedad_estable", "W^s"), ("inestable", "variedad_inestable", "W^u")):
            xs, ys = [], []
            for rama in ramas[clave]:
                recorrido_x, recorrido_y = rama["x"], rama["y"]
                if clave == "estable":
                    recorrido_x, recorrido_y = recorrido_x[::-1], recorrido_y[::-1]
                xs += recorrido_x + [None]
                ys += recorrido_y + [None]
            capas.append({"tipo": "linea", "rol": rol, "nombre": f"{nombre} de ({punto[0]:g}, {punto[1]:g})",
                          "x": xs, "y": ys})
        destinos = []
        for rama in ramas["inestable"]:
            final = rama["estado_final"]
            cercano = min(atractores, key=lambda a: math.dist(a[0], final), default=None)
            if cercano is not None and math.dist(cercano[0], final) < 0.05 * (caja[0][1] - caja[0][0]):
                destinos.append(cercano[0])
        if len(destinos) == 2 and destinos[0] != destinos[1]:
            cuencas.append({"silla": punto, "atractores": destinos})
    for punto, e in zip(puntos, clasificados):
        lin = e["linealizacion"]
        estado = ("estable" if lin.definida and lin.estable else
                  "inestable" if lin.definida and lin.estabilidad.startswith("inestable") else "indefinido")
        capas.append({"tipo": "puntos", "rol": f"equilibrio:{estado}",
                      "nombre": f"({punto[0]:g}, {punto[1]:g}): {e.get('tipo', lin.tipo)}",
                      "x": [punto[0]], "y": [punto[1]]})
    if problema.ci is not None:
        orbita = muestreo.trayectoria(f, [float(sp.N(c)) for c in problema.ci[1]], 30.0, caja)
        if orbita:
            capas.append({"tipo": "linea", "rol": "trayectoria", "nombre": "Órbita con la CI dada",
                          "x": orbita["x"], "y": orbita["y"]})
    d.grafica({"clave": "retrato_fase", "titulo": titulo, "ejes": {"x": x.name, "y": y.name},
               "rango": {"x": list(caja[0]), "y": list(caja[1])}, "capas": capas})
    if cuencas:
        d.guardar("cuencas", cuencas)
        for c in cuencas:
            silla = c["silla"]
            a, b = c["atractores"]
            d.concluir(f"Las dos ramas de la variedad inestable de la silla ({silla[0]:g}, {silla[1]:g}) "
                       f"terminan en atractores distintos, ({a[0]:g}, {a[1]:g}) y ({b[0]:g}, {b[1]:g}): "
                       "su variedad estable es la frontera entre las dos cuencas de atracción, y el "
                       "estado final depende de la condición inicial.")
            d.validar("cuencas_separadas_por_variedad", True,
                      "Las ramas de W^u de la silla, integradas numéricamente, convergen a atractores "
                      "distintos.", tipo="numerica")


def _muestrear_igualdad(igualdad, x, y, caja):
    """Una nulclina lhs = rhs como curva: y en función de x, o x = constante."""
    expresion = sp.expand(igualdad.lhs - igualdad.rhs)
    (xa, xb), (ya, yb) = caja
    try:
        despeje = sp.solve(expresion, y)
    except NotImplementedError:
        despeje = []
    if despeje:
        xs, ys = [], []
        for rama in despeje:
            cx, cy = muestreo.curva(rama, x, xa, xb, n=200)
            xs += cx + [None]
            ys += cy + [None]
        return xs, ys
    despeje = sp.solve(expresion, x)
    xs, ys = [], []
    for rama in despeje:
        if not rama.has(y):
            valor = float(sp.N(rama))
            xs += [valor, valor, None]
            ys += [ya, yb, None]
        else:
            cy, cx = muestreo.curva(rama, y, ya, yb, n=200)
            xs += cx + [None]
            ys += cy + [None]
    return xs, ys


# ---------------------------------------------------------------------------
# Ciclo límite en coordenadas polares (2.5)
# ---------------------------------------------------------------------------

R_POLAR = sp.Symbol("r", positive=True)
THETA = sp.Symbol("theta", real=True)


def forma_polar(f, g, x, y):
    """(ṙ, θ̇, r·ṙ, r²·θ̇) del campo plano, exactos y en r > 0."""
    cambio = {x: R_POLAR * sp.cos(THETA), y: R_POLAR * sp.sin(THETA)}
    radial = sp.simplify(sp.expand((x * f + y * g).subs(cambio, simultaneous=True)))
    angular = sp.simplify(sp.expand((x * g - y * f).subs(cambio, simultaneous=True)))
    r_punto = sp.factor_terms(sp.simplify(radial / R_POLAR))
    theta_punto = sp.simplify(angular / R_POLAR ** 2)
    return r_punto, theta_punto, radial, angular


def desarrollar_ciclo_limite(problema, datos=None) -> Desarrollo:
    x, y = problema.estados
    f, g = problema.campo_con()
    d = Desarrollo("ciclo_limite", "Órbitas periódicas por Poincaré–Bendixson", TEMA,
                   "Coordenadas polares, región anular atrapante y teorema de Poincaré–Bendixson",
                   tratamiento=["analitico", "cualitativo", "numerico"], balotario=["2.5"])
    r, th = R_POLAR, THETA
    r_punto, theta_punto, radial, angular = seccion_polar(d, f, g, x, y)
    radial_solo = not r_punto.has(th)
    angular_solo = not theta_punto.has(r)

    # --- equilibrios -----------------------------------------------------------
    seccion = d.seccion("equilibrios", "Puntos de equilibrio del sistema")
    raices_r = sorted([v for v in sp.solveset(r_punto, r, domain=sp.Interval.open(0, sp.oo))
                       if v.is_number], key=float) if radial_solo else []
    if radial_solo:
        seccion.formula(r"\dot{r} = 0 \iff r = 0" + "".join(rf" \;\lor\; r = {L(v)}" for v in raices_r))
    ceros_theta = []
    if angular_solo:
        ceros_theta = sorted(sp.solveset(theta_punto, th, domain=sp.Interval.Ropen(0, 2 * sp.pi)), key=float)
        if ceros_theta:
            seccion.formula(r"\dot{\theta} = 0 \iff \theta \in \left\{" + L(ceros_theta) + r"\right\}"
                            r" + 2k\pi")
        else:
            seccion.formula(rf"\dot{{\theta}} = {L(theta_punto)} \ne 0")
    # El origen es equilibrio si el campo tiende a cero al acercarse a él; en
    # el 2.5 el campo no está definido en (0, 0) pero se extiende con valor 0.
    cambio = {x: r * sp.cos(th), y: r * sp.sin(th)}
    origen_es_equilibrio = all(sp.limit(sp.simplify(c.subs(cambio)), r, 0) == 0 for c in (f, g))
    equilibrios = [(sp.Integer(0), sp.Integer(0))] if origen_es_equilibrio else []
    if not (radial_solo and angular_solo):
        otros, _ = buscar_equilibrios([f, g], [x, y])
        equilibrios += [e.punto for e in otros if e.punto != (0, 0)]
    for radio in raices_r:
        for angulo in ceros_theta:
            if sp.simplify(theta_punto.subs({th: angulo, r: radio})) == 0:
                equilibrios.append((sp.simplify(radio * sp.cos(angulo)), sp.simplify(radio * sp.sin(angulo))))
    seccion.formula(r",\quad ".join(rf"P_{{{i}}} = {punto_latex(e)}" for i, e in enumerate(equilibrios)),
                    destacada=True)
    for e in equilibrios[1:]:
        anulado = [sp.simplify(c.subs({x: e[0], y: e[1]})) for c in (f, g)]
        d.validar("equilibrio_en_cartesianas", all(a == 0 for a in anulado),
                  f"El campo cartesiano se anula en {e}: es un equilibrio de verdad.")
    d.guardar("equilibrios", equilibrios)

    lin = linealizar([f, g], [x, y], (0, 0))
    seccion.rotulo(r"\text{Linealización en el origen}")
    if lin.definida:
        seccion.formula(rf"J(0, 0) = {_pmatrix(lin.jacobiano)}")
        seccion.formula(rf"\det(J - \lambda I) = {L(lin.polinomio)} = 0 \implies \lambda = {L(lin.autovalores)}")
        seccion.formula(rf"\text{{{descripcion(lin.tipo, lin.estabilidad)}}}", destacada=True)
    else:
        seccion.texto(lin.nota + " Se usa la forma polar cerca de r = 0.")
        if radial_solo:
            pendiente = sp.limit(r_punto / r, r, 0)
            seccion.formula(rf"\dot{{r}} \approx {L(pendiente)}\, r \quad (r \to 0^+)", r"\implies",
                            r"\text{el origen repele}" if signo(pendiente) == 1 else r"\text{el origen atrae}",
                            destacada=True)
    d.guardar("origen", lin)

    # --- región anular y Poincaré–Bendixson --------------------------------------
    ciclos = []
    if not radial_solo:
        d.advertir("ṙ depende de θ: la región anular se comprueba numéricamente en cada círculo.")
    for i, radio in enumerate(raices_r):
        anterior = raices_r[i - 1] if i > 0 else sp.Integer(0)
        siguiente = raices_r[i + 1] if i + 1 < len(raices_r) else None
        r1 = radio / 2 if anterior == 0 else (anterior + radio) / 2
        r2 = 2 * radio if siguiente is None else (radio + siguiente) / 2
        v1, v2 = sp.simplify(r_punto.subs(r, r1)), sp.simplify(r_punto.subs(r, r2))
        atrapante = signo(v1) == 1 and signo(v2) == -1
        repulsora = signo(v1) == -1 and signo(v2) == 1
        seccion = d.seccion(f"region_{i + 1}", "Construcción de la región anular $K$")
        seccion.formula(rf"K = \left\{{({L(x)}, {L(y)}) : {L(r1)} \le r \le {L(r2)}\right\}}", destacada=True)
        seccion.formula(rf"\left.\dot{{r}}\right|_{{r={L(r1)}}} = {L(v1)} {_rel(v1)} 0",
                        r"\implies", r"\text{el flujo entra a } K" if signo(v1) == 1 else r"\text{el flujo sale de } K")
        seccion.formula(rf"\left.\dot{{r}}\right|_{{r={L(r2)}}} = {L(v2)} {_rel(v2)} 0",
                        r"\implies", r"\text{el flujo entra a } K" if signo(v2) == -1 else r"\text{el flujo sale de } K")
        dentro = [e for e in equilibrios if r1 <= sp.sqrt(e[0] ** 2 + e[1] ** 2) <= r2]
        seccion = d.seccion(f"poincare_bendixson_{i + 1}", "Hipótesis del teorema de Poincaré–Bendixson")
        seccion.formula(r"K \text{ es cerrado y acotado} \implies K \text{ es compacto}", destacada=True)
        if atrapante:
            seccion.formula(r"\forall \mathbf{x}_0 \in K:\; \phi_t(\mathbf{x}_0) \in K\; \forall t \ge 0 "
                            r"\implies K \text{ es positivamente invariante}", destacada=True)
        elif repulsora:
            seccion.formula(r"K \text{ es negativamente invariante (atrapa el flujo hacia atrás en el tiempo)}",
                            destacada=True)
        if dentro:
            seccion.formula(r"\text{Equilibrios en } K:\; " + r",\; ".join(punto_latex(e) for e in dentro),
                            r"\implies", r"\textbf{la hipótesis no se cumple}", destacada=True)
            seccion.texto("K contiene un equilibrio, así que el teorema de Poincaré–Bendixson no "
                          "garantiza una órbita periódica en K.")
            _circulo_con_equilibrio(d, radio, theta_punto, ceros_theta, dentro, angular_solo)
            ciclos.append({"radio": radio, "region": (r1, r2), "periodico": False, "equilibrios": dentro})
            continue
        seccion.formula(r"(0, 0) \notin K \implies K \text{ no contiene puntos de equilibrio}", destacada=True)
        if not (atrapante or repulsora):
            seccion.texto("El flujo no entra (ni sale) de K por ambas fronteras: el teorema no se aplica.")
            continue
        seccion = d.seccion(f"ciclo_{i + 1}", "Ciclo límite")
        seccion.formula(r"\text{Poincaré–Bendixson} \implies \exists\ \text{órbita periódica } \gamma \subset K",
                        destacada=True)
        datos_ciclo = {"radio": radio, "region": (r1, r2), "periodico": True}
        if radial_solo:
            derivada = sp.diff(r_punto, r)
            valor = sp.simplify(derivada.subs(r, radio))
            seccion.formula(rf"\dot{{r}} = 0 \iff r^* = {L(radio)} \iff {L(x)}^2 + {L(y)}^2 = {L(radio ** 2)}",
                            destacada=True, ref="radio_ciclo")
            estable = signo(valor) == -1
            seccion.formula(rf"\left.\frac{{d\dot{{r}}}}{{dr}}\right|_{{r={L(radio)}}} = "
                            rf"\left.{L(derivada)}\right|_{{r={L(radio)}}} = {L(valor)} {_rel(valor)} 0")
            seccion.formula(rf"r^* = {L(radio)} \implies \text{{ciclo límite "
                            rf"{'asintóticamente estable (atractor)' if estable else 'inestable (repulsor)'}}}",
                            destacada=True)
            datos_ciclo["estable"] = estable
            if angular_solo or not theta_punto.has(th):
                integrando = sp.simplify(1 / theta_punto.subs(r, radio))
                periodo = sp.simplify(sp.integrate(integrando, (th, 0, 2 * sp.pi)))
                if periodo.is_finite:
                    seccion.formula(rf"T = \int_0^{{2\pi}} \frac{{d\theta}}{{\dot{{\theta}}}} = {L(periodo)}",
                                    destacada=True, ref="periodo")
                    datos_ciclo["periodo"] = periodo
                    d.guardar("periodo", periodo)
            d.guardar("radio_ciclo", radio)
            d.concluir(f"Existe una órbita periódica: el círculo r = {sp.sstr(radio)}, ciclo límite "
                       f"{'estable' if estable else 'inestable'}.")
        ciclos.append(datos_ciclo)
    d.guardar("ciclos", ciclos)
    _validar_y_graficar_polar(d, problema, [f, g], x, y, ciclos, equilibrios)
    return d


def _circulo_con_equilibrio(d, radio, theta_punto, ceros_theta, dentro, angular_solo):
    """Qué es el círculo invariante r = r* cuando contiene equilibrios (2.5)."""
    r, th = R_POLAR, THETA
    seccion = d.seccion("circulo_invariante", f"El círculo invariante $r = {L(radio)}$")
    seccion.formula(rf"\dot{{r}}\big|_{{r={L(radio)}}} = 0 \implies r = {L(radio)} \text{{ es invariante}}")
    sobre = sp.simplify(theta_punto.subs(r, radio))
    seccion.formula(rf"\dot{{\theta}}\big|_{{r={L(radio)}}} = {L(sobre)} \ge 0", r",\qquad",
                    r"\dot{\theta} = 0 \iff \theta \in \left\{" + L(ceros_theta) + r"\right\}")
    seccion.formula(r"\text{El círculo está formado por el equilibrio } " +
                    r",\; ".join(punto_latex(e) for e in dentro) +
                    r"\text{ y una órbita que sale de él y regresa a él (lazo homoclínico)}", destacada=True)
    d.concluir(f"El círculo r = {sp.sstr(radio)} es invariante pero NO es una órbita periódica: θ̇ se "
               f"anula en él, en el equilibrio {', '.join(str(e) for e in dentro)}. Es un lazo "
               "homoclínico a ese equilibrio.")
    if angular_solo:
        seccion.texto("Como θ̇ solo depende de θ y no es negativa, θ crece de forma monótona hacia el "
                      "siguiente cero de θ̇ sin alcanzarlo, mientras r tiende al radio invariante: toda "
                      "órbita con r > 0 converge al equilibrio, no a una oscilación.")
        d.concluir("Ninguna órbita es periódica: todas las trayectorias con r > 0 convergen al "
                   f"equilibrio {dentro[0]} (lo confirma la integración numérica).")
    d.guardar("conclusion_poincare_bendixson", "no_aplica_equilibrio_en_K")


def _validar_y_graficar_polar(d, problema, campo, x, y, ciclos, equilibrios):
    f = muestreo.campo_plano(campo, [x, y])
    radio_max = max([float(c["region"][1]) for c in ciclos] + [1.5])
    caja = ((-1.15 * radio_max, 1.15 * radio_max), (-1.15 * radio_max, 1.15 * radio_max))
    capas = [muestreo.campo_de_direcciones(f, caja)]
    semillas = []
    for c in ciclos:
        r1, r2 = float(c["region"][0]), float(c["region"][1])
        semillas += [(r1 * math.cos(1.0), r1 * math.sin(1.0)), (r2 * math.cos(2.5), r2 * math.sin(2.5))]
        angulos = np.linspace(0, 2 * np.pi, 200)
        for radio, rol, nombre in ((r1, "frontera", f"r = {sp.sstr(c['region'][0])}"),
                                   (r2, "frontera", f"r = {sp.sstr(c['region'][1])}"),
                                   (float(c["radio"]), "ciclo" if c["periodico"] else "lazo",
                                    f"r* = {sp.sstr(c['radio'])}" + ("" if c["periodico"] else " (con equilibrio)"))):
            capas.append({"tipo": "linea", "rol": rol, "nombre": nombre,
                          "x": (radio * np.cos(angulos)).tolist(), "y": (radio * np.sin(angulos)).tolist()})
    if not semillas:
        semillas = [(0.3, 0.2), (1.8, 1.0)]
    orbitas = []
    for i, semilla in enumerate(semillas):
        # Tiempo largo: cerca de un equilibrio sobre el círculo (2.5) la
        # aproximación es lenta, θ se acerca a 2π como 2/t.
        orbita = muestreo.trayectoria(f, semilla, 200.0, caja=None, maximo_puntos=1500)
        if orbita:
            orbitas.append(orbita)
            capas.append({"tipo": "linea", "rol": "trayectoria" if i % 2 == 0 else "orbita",
                          "nombre": f"Desde ({semilla[0]:.2f}, {semilla[1]:.2f})",
                          "x": orbita["x"], "y": orbita["y"]})
    for c in ciclos:
        finales = [o["estado_final"] for o in orbitas]
        radios = [math.hypot(*e) for e in finales]
        desvio = max(abs(rf - float(c["radio"])) for rf in radios) if radios else None
        if desvio is not None:
            d.validar("convergencia_al_radio_invariante", desvio < 1e-3,
                      f"Integrando desde dentro y desde fuera de K, el radio tiende a {sp.sstr(c['radio'])}.",
                      medida=desvio, umbral=1e-3, tipo="numerica")
        if not c["periodico"] and c.get("equilibrios"):
            objetivo = [float(sp.N(v)) for v in c["equilibrios"][0]]
            distancia = max(math.dist(e, objetivo) for e in finales) if finales else None
            if distancia is not None:
                d.validar("convergencia_al_equilibrio", distancia < 0.05,
                          f"Las trayectorias integradas terminan junto al equilibrio {c['equilibrios'][0]}, "
                          "no recorriendo una órbita cerrada.", medida=distancia, umbral=0.05, tipo="numerica")
    for e in equilibrios:
        capas.append({"tipo": "puntos", "rol": "equilibrio:inestable" if e == (0, 0) else "equilibrio:indefinido",
                      "nombre": f"Equilibrio {e}", "x": [float(sp.N(e[0]))], "y": [float(sp.N(e[1]))]})
    d.grafica({"clave": "retrato_fase", "titulo": "Retrato de fase y región anular",
               "ejes": {"x": x.name, "y": y.name}, "rango": {"x": list(caja[0]), "y": list(caja[1])},
               "capas": capas, "cuadrada": True})
