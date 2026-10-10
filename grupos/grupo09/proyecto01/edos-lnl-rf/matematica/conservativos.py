"""Sistemas conservativos: integral primera, equilibrios, separatriz y periodo.

Familia de dos problemas del balotario que comparten la misma maquinaria:

* **1.5** — péndulo θ'' + ω₀² sin θ = 0: primera integral de la energía,
  separatriz en el plano (θ, θ̇) y periodo exacto con la integral elíptica.
* **2.4** — sistema ẋ = y, ẏ = x − x³: función hamiltoniana, clasificación de
  los puntos fijos y la órbita homoclínica.

En ambos el campo es ẋ = y, ẏ = F(x) (o, más en general, de divergencia nula),
y todo sale de H = ½y² + V(x) con V' = −F:

1. H se obtiene integrando (multiplicando por ẋ en el estilo "energía", o de
   ẋ = ∂H/∂y, ẏ = −∂H/∂x en el estilo "hamiltoniano"), y se comprueba que
   dH/dt ≡ 0 a lo largo del flujo;
2. los equilibrios son los ceros de F; la linealización da λ² = F'(x*): silla
   si F'(x*) > 0; si F'(x*) < 0 da un centro lineal, que la linealización
   sola no decide, y es V''(x*) > 0 (mínimo estricto de la energía potencial)
   lo que lo convierte en un centro no lineal estable en el sentido de
   Lyapunov — el argumento del balotario;
3. la separatriz es la curva de nivel de las sillas, H = H(silla);
4. el periodo de una oscilación de amplitud x₀ es T = 2∫dx/√(2(E − V)); para
   el potencial del péndulo, la transformación de Jacobi lo lleva a K(k).
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq
from scipy.special import ellipk
from sympy.calculus.util import periodicity

from matematica import MetodoNoAplicable
from matematica import muestreo
from matematica.analisis_estabilidad import buscar_equilibrios, linealizar, signo
from matematica.desarrollo import Desarrollo, L, punto_latex, suma
from matematica.problema import nombre_derivada

TEMA_1 = "Tema 1 · EDOs lineales y no lineales"
TEMA_2 = "Tema 2 · Retratos de fase y análisis cualitativo"

#: Nombres de la segunda variable que delatan que es la derivada de la
#: primera (θ y θ̇, y e y'): deciden el estilo "energía" frente a "hamiltoniano".
SUFIJOS_DE_DERIVADA = ("p", "punto", "dot", "prima", "prime")


def identificar_conservativo(problema):
    """{'forma': 'segundo_orden', 'F': F} si es ẋ = y, ẏ = F(x); {'forma': 'hamiltoniano'} si div ≡ 0."""
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo:
        return None
    x, v = problema.estados
    f, g = (sp.sympify(e) for e in problema.campo)
    if sp.simplify(f - v) == 0 and not g.has(v) and g.has(x):
        return {"forma": "segundo_orden", "F": sp.simplify(g)}
    if sp.simplify(sp.diff(f, x) + sp.diff(g, v)) == 0 and (f.has(v) or g.has(x)) \
            and not (f.is_polynomial(x, v) and g.is_polynomial(x, v)
                     and sp.Poly(f, x, v).total_degree() <= 1 and sp.Poly(g, x, v).total_degree() <= 1):
        return {"forma": "hamiltoniano"}
    return None


def _estilo(problema):
    pedidos = problema.pedidos
    if "hamiltoniano" in pedidos:
        return "hamiltoniano"
    if pedidos & {"energia", "integral_primera", "periodo"}:
        return "energia"
    segunda = problema.estados[1].name.lower()
    primera = problema.estados[0].name.lower()
    if segunda == "v" or (segunda.startswith(primera) and segunda[len(primera):] in SUFIJOS_DE_DERIVADA):
        return "energia"
    return "hamiltoniano"


def _hamiltoniano_general(f, g, x, v):
    """H con ẋ = ∂H/∂v, v̇ = −∂H/∂x, para un campo de divergencia nula."""
    parcial = sp.integrate(f, v)
    resto = sp.simplify(-g - sp.diff(parcial, x))
    if resto.has(v):
        raise MetodoNoAplicable("El campo no deriva de un hamiltoniano.")
    return sp.expand(parcial + sp.integrate(resto, x))


def _forma_pendulo(V, x):
    """k si V = −k·cos x + c con k > 0 (el potencial del péndulo); si no, None."""
    A, B = sp.Wild("A", exclude=[x]), sp.Wild("B", exclude=[x])
    coincidencia = sp.expand(V).match(A * sp.cos(x) + B)
    if not coincidencia or coincidencia.get(A) in (None, 0):
        return None
    k = -coincidencia[A]
    return k if signo(k) == 1 else None


def _con_signo_del_valor(problema, *expresiones):
    """Fija el signo de un parámetro simbólico que aquí es una constante física.

    En esta familia el parámetro (ω₀ del péndulo) no es el objeto de estudio:
    es una constante. Se toma con el signo de su valor dado, y se dice. Sin
    esto ω₀² podría ser nulo y ningún equilibrio se podría clasificar.
    """
    p = problema.parametro
    if p is None or not any(sp.sympify(e).has(p) for e in expresiones) or p.is_positive or p.is_negative:
        return expresiones, None
    valor = problema.valor_representativo()
    if not valor:
        return expresiones, None
    firmado = sp.Symbol(p.name, positive=True) if valor > 0 else sp.Symbol(p.name, negative=True)
    nota = (f"Se toma {p.name} {'>' if valor > 0 else '<'} 0, el signo de su valor dado "
            f"({valor:g}): en este problema es una constante, no un parámetro de bifurcación.")
    return tuple(sp.sympify(e).subs(p, firmado) for e in expresiones), nota


def desarrollar_conservativo(problema, datos=None) -> Desarrollo:
    datos = datos or identificar_conservativo(problema)
    if datos is None:
        raise MetodoNoAplicable("El sistema no es conservativo: no es ẋ = y, ẏ = F(x) ni tiene "
                                "divergencia nula.")
    x, v = problema.estados
    (f, g), nota_signo = _con_signo_del_valor(problema, *problema.campo)
    estilo = _estilo(problema)
    energia_estilo = estilo == "energia"
    # En el estilo "energía" el estado es (θ, θ̇): se escribe con esos nombres.
    punto = nombre_derivada(x, 1, problema.x) if energia_estilo else v
    dos_puntos = nombre_derivada(x, 2, problema.x)
    vista = (lambda e: sp.sympify(e).subs(v, punto)) if energia_estilo else (lambda e: sp.sympify(e))
    es_segundo_orden = datos["forma"] == "segundo_orden"

    d = Desarrollo("conservativo",
                   "Sistema conservativo (integral primera)" if energia_estilo else "Sistema hamiltoniano",
                   TEMA_1 if energia_estilo else TEMA_2,
                   "Integral primera de la energía, separatriz y periodo" if energia_estilo
                   else "Función hamiltoniana, clasificación de equilibrios y órbita homoclínica",
                   tratamiento=["analitico", "cualitativo"], balotario=["1.5", "2.4"])
    if nota_signo:
        d.advertir(nota_signo)

    # --- 1. Integral primera ---------------------------------------------------
    if es_segundo_orden:
        F = g
        V = sp.integrate(-F, x)
        V = sp.expand(V) if V.is_polynomial(x) else sp.simplify(V)
        H = sp.Rational(1, 2) * v ** 2 + V
    else:
        H = _hamiltoniano_general(f, g, x, v)
        F = V = None
    d.guardar("hamiltoniano", H)
    if V is not None:
        d.guardar("potencial", V)

    if energia_estilo and es_segundo_orden:
        seccion = d.seccion("integral_primera", "Primera integral de la energía")
        seccion.formula(suma(dos_puntos, -F), "= 0")
        seccion.formula(suma((punto, dos_puntos), (-F, punto)), "= 0")
        seccion.formula(rf"\frac{{d}}{{dt}}\left[{L(vista(H))}\right] = 0")
        seccion.formula("E", "=", vista(H), r"= \text{cte}", destacada=True, ref="hamiltoniano")
    else:
        seccion = d.seccion("hamiltoniano", f"Función hamiltoniana $H({L(x)}, {L(v)})$")
        if es_segundo_orden:
            seccion.formula(rf"\dot{{{L(x)}}} = \frac{{\partial H}}{{\partial {L(v)}}} = {L(v)}",
                            r"\implies", rf"H({L(x)}, {L(v)}) = \frac{{1}}{{2}}{L(v)}^2 + V({L(x)})")
            seccion.formula(rf"\dot{{{L(v)}}} = -\frac{{\partial H}}{{\partial {L(x)}}} = -V'({L(x)})",
                            "=", F, r"\implies", rf"V'({L(x)})", "=", sp.expand(-F))
            seccion.formula(rf"V({L(x)}) = \int \left({L(sp.expand(-F))}\right) d{L(x)}", "=", V)
        else:
            seccion.formula(rf"\dot{{{L(x)}}} = \frac{{\partial H}}{{\partial {L(v)}}} = {L(f)},\qquad "
                            rf"\dot{{{L(v)}}} = -\frac{{\partial H}}{{\partial {L(x)}}} = {L(g)}")
        seccion.formula(rf"H({L(x)}, {L(v)})", "=", H, destacada=True, ref="hamiltoniano")

    derivada_total = sp.simplify(sp.diff(H, x) * f + sp.diff(H, v) * g)
    nombre = "E" if energia_estilo else "H"
    seccion.formula(rf"\frac{{d{nombre}}}{{dt}}", "=",
                    suma((vista(sp.diff(H, x)), vista(f)), (vista(sp.diff(H, v)), vista(g))),
                    r"\equiv", derivada_total, destacada=not energia_estilo)
    d.validar("integral_primera_conservada", derivada_total == 0,
              f"d{nombre}/dt = {nombre}_x·ẋ + {nombre}_y·ẏ se simplifica a 0: es constante a lo "
              "largo del flujo.")

    # --- 2. Equilibrios ----------------------------------------------------------
    # Con ẋ = y, ẏ = F(x) son (x*, 0) con F(x*) = 0. Si F es periódica (sin θ)
    # hay infinitos: se estudia un periodo centrado en el origen.
    periodo_espacial = None
    if es_segundo_orden:
        try:
            periodo_espacial = periodicity(F, x)
        except (NotImplementedError, ValueError):
            periodo_espacial = None
        ventana = (-periodo_espacial / 2, periodo_espacial / 2) if periodo_espacial else None
        region_x = {x: problema.region[x]} if x in problema.region else None
        locales, informe = buscar_equilibrios([F], [x], region=region_x, ventana=ventana)
        equilibrios = [type(e)((e.punto[0], sp.Integer(0)), e.caso) for e in locales]
    else:
        equilibrios, informe = buscar_equilibrios([f, g], [x, v], region=problema.region)
    jacobiano_general = sp.Matrix([f, g]).jacobian([x, v])
    seccion = d.seccion("equilibrios", "Puntos de equilibrio y su clasificación")
    if es_segundo_orden:
        seccion.formula(rf"{L(punto)} = 0,\qquad {L(F)} = 0")
    else:
        seccion.formula(rf"\dot{{{L(x)}}} = {L(f)} = 0,\qquad \dot{{{L(v)}}} = {L(g)} = 0")
    if informe.get("general") is not None:
        seccion.formula(rf"{L(x)}^* \in {L(informe['general'])}")
        seccion.texto(f"El campo es periódico en {x} (periodo {sp.sstr(periodo_espacial)}): basta "
                      f"estudiar un periodo; los demás equilibrios repiten estos.")
    seccion.formula(r",\quad ".join(rf"P_{{{i}}} = {punto_latex(e.punto)}"
                                    for i, e in enumerate(equilibrios, 1)), destacada=True)
    seccion.formula(rf"J({L(x)}, {L(punto)})", "=", vista(jacobiano_general),
                    r",\qquad \mathrm{Tr}(J) \equiv", sp.simplify(jacobiano_general.trace()))
    clasificados = []
    for i, equilibrio in enumerate(equilibrios, 1):
        lin = linealizar([f, g], [x, v], equilibrio.punto, matriz_general=jacobiano_general)
        energia = sp.simplify(H.subs({x: equilibrio.punto[0], v: equilibrio.punto[1]}))
        tipo, estabilidad, segunda = lin.tipo, lin.estabilidad, None
        if lin.tipo == "centro" and V is not None:
            segunda = sp.simplify(sp.diff(V, x, 2).subs(x, equilibrio.punto[0]))
            if signo(segunda) == 1:
                tipo, estabilidad = "centro no lineal", "estable en el sentido de Lyapunov"
            else:
                segunda = None
        clasificados.append({"punto": equilibrio.punto, "tipo": tipo, "estabilidad": estabilidad,
                             "autovalores": lin.autovalores, "energia": energia,
                             "linealizacion": lin})
        seccion.rotulo(rf"\text{{Análisis en }} P_{{{i}}}{punto_latex(equilibrio.punto)}")
        seccion.formula(rf"J{punto_latex(equilibrio.punto)}", "=", lin.jacobiano)
        seccion.formula(rf"\det(J - \lambda I) = {L(lin.polinomio)} = 0", r"\implies",
                        rf"\lambda = {L(lin.autovalores)}")
        if segunda is not None:
            seccion.formula(rf"V''({L(x)}) = {L(sp.diff(V, x, 2))} \implies "
                            rf"V''({L(equilibrio.punto[0])}) = {L(segunda)} > 0")
            seccion.texto("La linealización da un centro, que por sí sola no decide; como "
                          "V'' > 0, el punto es un mínimo estricto de la energía potencial y la "
                          "conservación de H lo hace un centro no lineal.")
        seccion.formula(rf"\text{{{tipo} ({estabilidad})}},\qquad {nombre}{punto_latex(equilibrio.punto)}"
                        rf" = {L(energia)}", destacada=True)
    d.guardar("equilibrios", clasificados)

    # --- 3. Separatriz -------------------------------------------------------------
    sillas = [e for e in clasificados if e["tipo"] == "punto silla"]
    pedidos = problema.pedidos
    quiere_separatriz = (not pedidos or pedidos & {"separatriz", "homoclinica"}
                         or not energia_estilo)
    datos_separatriz = None
    if sillas and V is not None and quiere_separatriz:
        datos_separatriz = _seccion_separatriz(d, sillas, V, x, v, punto, H, vista, nombre)

    # --- 4. Periodo -----------------------------------------------------------------
    amplitud = None
    if problema.ci is not None and es_segundo_orden:
        x0, vel0 = problema.ci[1]
        if sp.simplify(vel0) == 0 and sp.simplify(F.subs(x, x0)) != 0:
            amplitud = x0
    if es_segundo_orden and (amplitud is not None or "periodo" in pedidos):
        centro = _centro_de_la_oscilacion(clasificados, amplitud)
        if centro is not None:
            _seccion_periodo(d, V, x, punto, amplitud, centro, problema,
                             [e["punto"][0] for e in sillas])

    _grafica(d, problema, [f, g], x, v, punto, H, clasificados, datos_separatriz)
    return d


def _seccion_separatriz(d, sillas, V, x, v, punto, H, vista, nombre):
    seccion = d.seccion("separatriz", "Separatriz: curva de nivel de las sillas")
    silla = sillas[0]
    energia = silla["energia"]
    seccion.formula(rf"{nombre}_{{\mathrm{{sep}}}} = {nombre}{punto_latex(silla['punto'])}", "=", energia,
                    destacada=True)
    seccion.formula(vista(H), "=", energia)
    cuadrado = sp.expand(2 * (energia - V))
    k = _forma_pendulo(V, x)
    if k is not None:
        # Identidad del ángulo mitad: 1 + cos θ = 2 cos²(θ/2).
        transformado = sp.factor(sp.expand(cuadrado.subs(sp.cos(x), 2 * sp.cos(x / 2) ** 2 - 1)))
        d.validar("identidad_angulo_mitad", sp.simplify(sp.expand_trig(transformado - cuadrado)) == 0,
                  "La sustitución cos θ = 2cos²(θ/2) − 1 reproduce la expresión original.")
        seccion.formula(rf"{L(punto)}^2", "=", cuadrado, "=", transformado)
        rama = sp.simplify(sp.sqrt(sp.factor(transformado / sp.cos(x / 2) ** 2)) * sp.cos(x / 2))
        seccion.formula(rf"{L(punto)}_{{\mathrm{{sep}}}}({L(x)})", "=", r"\pm", rama, destacada=True,
                        ref="separatriz")
        d.guardar("separatriz", rama)
        d.guardar("energia_separatriz", energia)
        nombres_sillas = " y ".join(f"({sp.sstr(s['punto'][0])}, {sp.sstr(s['punto'][1])})" for s in sillas)
        d.concluir(f"La separatriz es la curva de nivel {nombre} = {sp.sstr(energia)}, que une las "
                   f"sillas {nombres_sillas} y separa las oscilaciones (energía menor) de las "
                   "rotaciones (energía mayor).")
        return {"rama": rama, "intervalos": None, "energia": energia, "tipo": "heteroclinica"}

    if not (sp.sympify(V).is_polynomial(x) or sp.sympify(V).is_rational_function(x)):
        seccion.formula(rf"{L(punto)}^2", "=", cuadrado, destacada=True, ref="separatriz")
        seccion.texto("El potencial no es polinómico: la separatriz queda en forma implícita y se "
                      "dibuja como la curva de nivel correspondiente.")
        d.guardar("energia_separatriz", energia)
        return {"rama": None, "intervalos": None, "energia": energia, "tipo": "implicita"}

    seccion.formula(rf"{L(punto)}^2", "=", cuadrado)
    x_s = silla["punto"][0]
    resto = sp.expand(sp.cancel(cuadrado / (x - x_s) ** 2))
    seccion.formula(rf"{L(punto)}^2", "=", sp.Mul((x - x_s) ** 2, resto, evaluate=False))
    rama = (x - x_s) * sp.sqrt(resto)
    # La órbita homoclínica es la parte acotada de la curva de nivel: va de la
    # silla al punto de retorno (V = E) del lado de los centros. El resto del
    # nivel son ramas no acotadas de las variedades de la silla.
    giros = sorted([r for r in sp.solveset(sp.Eq(V, energia), x, domain=sp.S.Reals)
                    if sp.simplify(r - x_s) != 0], key=lambda r: float(r))
    intervalos = [sp.Interval(min(x_s, r, key=float), max(x_s, r, key=float)) for r in giros]
    lazo = sp.Union(*intervalos) if intervalos else None
    if lazo is not None:
        seccion.formula(L(resto), r"\ge 0", r"\;\text{entre la silla y los puntos de retorno:}\;",
                        rf"{L(x)} \in {L(lazo)}")
    tipo = "homoclinica" if giros else "variedades no acotadas"
    seccion.formula(rf"{L(punto)}_{{\mathrm{{hom}}}}({L(x)})" if giros else rf"{L(punto)}_{{\mathrm{{sep}}}}({L(x)})",
                    "=", r"\pm", rama, *( [r",\qquad", rf"{L(x)} \in {L(lazo)}"] if lazo is not None else []),
                    destacada=True, ref="separatriz")
    d.guardar("separatriz", rama)
    d.guardar("energia_separatriz", energia)
    if lazo is not None:
        d.guardar("dominio_separatriz", lazo)
    if giros:
        seccion = d.seccion("propiedades_separatriz", "Propiedades geométricas de la órbita homoclínica")
        seccion.formula(rf"{L(x)}_{{\mathrm{{vértice}}}}", "=", r"\left\{" + L(giros) + r"\right\}",
                        rf"\quad ({L(punto)} = 0)")
        criticos = [c for c in sp.solveset(sp.diff(cuadrado, x), x, domain=sp.S.Reals)
                    if sp.simplify(c - x_s) != 0 and any(
                        (float(c) - float(x_s)) * (float(r) - float(x_s)) > 0 for r in giros)]
        if criticos:
            alturas = [sp.simplify(sp.sqrt(cuadrado.subs(x, c))) for c in criticos]
            seccion.formula(rf"\frac{{d({L(punto)}^2)}}{{d{L(x)}}} = {L(sp.diff(cuadrado, x))} = 0 \implies "
                            rf"{L(x)} = {L(criticos)} \implies {L(punto)}_{{\max}} = \pm {L(alturas[0])}",
                            destacada=True)
            d.guardar("alturas_extremas", list(zip(criticos, alturas)))
        d.guardar("vertices", giros)
        centros = "a los centros" if len(giros) > 1 else "al centro"
        d.concluir(f"La órbita homoclínica vive en el nivel {nombre} = {sp.sstr(energia)} de la silla "
                   f"({sp.sstr(x_s)}, 0) y rodea {centros}: separa las órbitas cerradas de su interior "
                   "de las que pasan por fuera.")
    return {"rama": rama, "intervalos": intervalos, "energia": energia, "tipo": tipo, "silla": x_s}


def _centro_de_la_oscilacion(clasificados, amplitud):
    """El centro que rodea la órbita que parte de x₀: el más cercano sin una silla de por medio.

    En el pozo doble del 2.4 una órbita que parte de x₀ = 0.5 oscila alrededor
    de (1, 0), no de (−1, 0); tomar el primero de la lista daba un "periodo"
    que cruzaba la silla.
    """
    centros = [e["punto"][0] for e in clasificados if e["tipo"].startswith("centro")]
    sillas = [e["punto"][0] for e in clasificados if e["tipo"] == "punto silla"]
    if not centros:
        return None
    if amplitud is None:
        return min(centros, key=lambda c: abs(float(sp.N(c))))
    x0 = float(sp.N(amplitud))
    for c in sorted(centros, key=lambda c: abs(float(sp.N(c)) - x0)):
        extremos = sorted((x0, float(sp.N(c))))
        if not any(extremos[0] < float(sp.N(s)) < extremos[1] for s in sillas):
            return c
    return None


def _seccion_periodo(d, V, x, punto, amplitud, centro, problema, sillas=()):
    """Periodo de una oscilación de amplitud x₀ alrededor del centro."""
    x0 = sp.Symbol(f"{x.name}_0", positive=True)
    seccion = d.seccion("periodo", "Periodo exacto de oscilación")
    seccion.formula(rf"{L(punto)}({L(x0)}) = 0 \implies E = V({L(x0)})", "=", V.subs(x, x0))
    k = _forma_pendulo(V, x)
    if k is None:
        cuadrado = sp.simplify(2 * (V.subs(x, x0) - V))
        seccion.formula(rf"{L(punto)} = \pm\sqrt{{{L(cuadrado)}}}")
        seccion.formula(r"T = 2\int_{x_{\min}}^{x_{\max}} \frac{dx}{\sqrt{2\left(E - V(x)\right)}}",
                        destacada=True)
        if amplitud is not None:
            valor = _periodo_numerico(V, x, sp.sympify(amplitud), centro, problema, sillas)
            if valor is None:
                seccion.texto("Con esta energía la órbita no queda encerrada alrededor del centro (alcanza "
                              "o supera la energía de una silla): no es una oscilación periódica.")
            if valor is not None:
                seccion.formula(rf"T\left({L(x0)} = {L(amplitud)}\right) \approx {valor:.10g}",
                                destacada=True, ref="periodo")
                seccion.texto("Integral evaluada por cuadratura, con el cambio x = m + h·sin φ que "
                              "elimina la singularidad de los puntos de retorno.")
                d.guardar("periodo", valor)
                _validar_periodo(d, problema, valor)
        return

    # Péndulo: V = −k cos θ. Se sigue la transformación de Jacobi del balotario.
    raiz_k = sp.sqrt(k)
    cuadrado = sp.expand(2 * (V.subs(x, x0) - V))
    mitad = sp.expand(cuadrado.subs({sp.cos(x): 1 - 2 * sp.sin(x / 2) ** 2,
                                     sp.cos(x0): 1 - 2 * sp.sin(x0 / 2) ** 2}))
    d.validar("identidad_angulo_mitad_periodo",
              sp.simplify(sp.expand_trig(mitad - cuadrado)) == 0,
              "cos θ − cos θ₀ = 2(sin²(θ₀/2) − sin²(θ/2)): la reescritura es exacta.")
    diferencia = suma(sp.sin(x0 / 2) ** 2, -sp.sin(x / 2) ** 2)
    seccion.formula(rf"\frac{{1}}{{2}}{L(punto)}^2 = {L(sp.expand(V.subs(x, x0) - V))}")
    seccion.formula(rf"\cos{L(x)} - \cos{L(x0)} = 2\left({diferencia}\right)")
    seccion.formula(rf"{L(punto)}^2", "=", cuadrado, "=", rf"{L(4 * k)}\left({diferencia}\right)")
    velocidad = 2 * raiz_k * sp.sqrt(sp.sin(x0 / 2) ** 2 - sp.sin(x / 2) ** 2)
    raiz_latex = rf"{L(2 * raiz_k)}\sqrt{{{diferencia}}}"
    seccion.formula(L(punto), "=", r"\pm", raiz_latex, destacada=True)
    seccion.formula(r"T = 4\int_0^{" + L(x0) + r"} \frac{d" + L(x) + "}{" + raiz_latex + "}",
                    destacada=True)

    seccion = d.seccion("jacobi", "Transformación de Jacobi e integral elíptica $K(k)$")
    kk, phi = sp.Symbol("k", positive=True), sp.Symbol("phi", real=True)
    seccion.formula(rf"k = \sin\left(\frac{{{L(x0)}}}{{2}}\right),\qquad "
                    rf"\sin\left(\frac{{{L(x)}}}{{2}}\right) = k\sin\phi")
    seccion.formula(rf"\frac{{1}}{{2}}\cos\left(\frac{{{L(x)}}}{{2}}\right)d{L(x)} = k\cos\phi\, d\phi"
                    rf"\implies d{L(x)} = \frac{{2k\cos\phi\, d\phi}}{{\sqrt{{1 - k^2\sin^2\phi}}}}")
    seccion.formula(rf"{L(x)} = 0 \implies \phi = 0,\qquad {L(x)} = {L(x0)} \implies \phi = \frac{{\pi}}{{2}}")
    raiz = sp.sqrt(kk ** 2 - (kk * sp.sin(phi)) ** 2)
    reducida = sp.simplify(sp.sqrt(sp.factor(sp.expand(raiz ** 2).subs(sp.sin(phi) ** 2, 1 - sp.cos(phi) ** 2))))
    reducida = sp.simplify(reducida.subs(sp.Abs(sp.cos(phi)), sp.cos(phi)))
    seccion.formula(rf"\sqrt{{\sin^2\left(\frac{{{L(x0)}}}{{2}}\right) - \sin^2\left(\frac{{{L(x)}}}{{2}}\right)}}"
                    rf" = \sqrt{{k^2 - k^2\sin^2\phi}} = {L(reducida)}")
    integrando = sp.simplify((2 * kk * sp.cos(phi) / sp.sqrt(1 - kk ** 2 * sp.sin(phi) ** 2))
                             / (2 * raiz_k * reducida))
    seccion.formula(rf"T = 4\int_0^{{\pi/2}} {L(integrando)}\, d\phi")
    factor = sp.simplify(4 / raiz_k)
    seccion.formula(r"K(k) = \int_0^{\pi/2} \frac{d\phi}{\sqrt{1 - k^2\sin^2\phi}}")
    seccion.formula(rf"T = {L(factor)}\, K(k),\qquad k = \sin\left(\frac{{{L(x0)}}}{{2}}\right)",
                    destacada=True, ref="periodo_formula")
    d.guardar("periodo_formula", sp.Mul(factor, sp.Function("K")(sp.sin(x0 / 2)), evaluate=False))
    limite = sp.limit(factor * sp.elliptic_k(kk ** 2), kk, 0)
    seccion.formula(rf"\lim_{{k \to 0}} K(k) = \frac{{\pi}}{{2}} \implies T_0 = {L(limite)}",
                    destacada=True, ref="periodo_pequenas_oscilaciones")
    d.guardar("periodo_pequenas_oscilaciones", limite)

    if amplitud is not None:
        k_num = float(sp.N(_sustituir_parametro(k, problema)))
        modulo = math.sin(float(sp.N(amplitud)) / 2)
        periodo = 4 / math.sqrt(k_num) * float(ellipk(modulo ** 2))
        seccion.formula(rf"{L(x0)} = {L(amplitud)} \implies k = \sin\left({L(sp.sympify(amplitud) / 2)}"
                        rf"\right) = {modulo:.10g},\qquad T = {periodo:.10g}", destacada=True,
                        ref="periodo")
        seccion.texto("scipy.special.ellipk recibe el parámetro m = k², no el módulo k.")
        d.guardar("periodo", periodo)
        d.guardar("modulo_eliptico", modulo)
        _validar_periodo(d, problema, periodo)


def _sustituir_parametro(expresion, problema):
    """Reemplaza el parámetro (con cualquier supuesto de signo) por su valor representativo."""
    if problema.parametro is None:
        return expresion
    valor = problema.valor_representativo()
    return sp.sympify(expresion).subs({s: valor for s in sp.sympify(expresion).free_symbols
                                       if s.name == problema.parametro.name})


def _periodo_numerico(V, x, amplitud, centro, problema, sillas=()):
    """T = 2∫ dx/√(2(E − V)) entre los dos puntos de retorno, por cuadratura.

    Devuelve None si la energía alcanza la de una silla del pozo: entonces la
    órbita no se cierra alrededor del centro y no hay periodo que calcular.
    """
    V = _sustituir_parametro(V, problema)
    energia = float(sp.N(V.subs(x, amplitud)))
    potencial = sp.lambdify(x, V, "math")
    a, c = float(sp.N(amplitud)), float(sp.N(centro))
    # El otro punto de retorno está del otro lado del centro, donde V vuelve a
    # valer E: se avanza desde el centro hasta pasarlo y se acota con brentq.
    sentido = -1.0 if a > c else 1.0
    distancia = abs(a - c) or 1.0
    previo, b = c, None
    for paso in range(1, 80):
        z = c + sentido * distancia * (0.25 * paso)
        if potencial(z) >= energia:
            b = brentq(lambda s: potencial(s) - energia, min(previo, z), max(previo, z))
            break
        previo = z
    if b is None:
        return None
    menor, mayor = sorted((a, b))
    # Una silla entre los puntos de retorno significa que la energía la supera:
    # la órbita sale del pozo y no hay oscilación cerrada alrededor del centro.
    if any(menor < float(sp.N(_sustituir_parametro(s, problema))) < mayor for s in sillas):
        return None
    medio, radio = (menor + mayor) / 2, (mayor - menor) / 2

    def integrando(fase):
        diferencia = 2 * (energia - potencial(medio + radio * math.sin(fase)))
        return radio * math.cos(fase) / math.sqrt(max(diferencia, 1e-300))
    valor, _ = quad(integrando, -math.pi / 2, math.pi / 2, limit=200)
    return 2 * valor


def _validar_periodo(d, problema, periodo):
    """Integra exactamente un periodo y mide el regreso al estado inicial."""
    if not math.isfinite(periodo) or periodo <= 0 or periodo > 1e3:
        d.validar("periodo_por_retorno", False, f"El periodo calculado ({periodo:g}) no es razonable "
                  "para integrarlo; la comprobación por retorno no se hace.", tipo="numerica",
                  concluyente=False)
        return
    try:
        campo = problema.campo_numerico()
        x0 = [float(sp.N(v)) for v in problema.ci[1]]
        solucion = solve_ivp(lambda t, y: campo(t, y), (0.0, periodo), x0, rtol=1e-12, atol=1e-14)
        desvio = float(np.max(np.abs(solucion.y[:, -1] - np.asarray(x0))))
    except Exception as exc:                  # la validación numérica es un respaldo
        d.validar("periodo_por_retorno", False, f"No se pudo integrar un periodo: {exc}",
                  tipo="numerica", concluyente=False)
        return
    d.validar("periodo_por_retorno", desvio < 1e-6,
              "Integrando exactamente un periodo T el estado regresa a la condición inicial.",
              medida=desvio, umbral=1e-6, tipo="numerica")


def _grafica(d, problema, campo, x, v, punto, H, equilibrios, separatriz):
    """Retrato de fase: curvas de nivel de H, separatriz, equilibrios y la órbita pedida."""
    H_num = _sustituir_parametro(H, problema)
    puntos = [(float(sp.N(_sustituir_parametro(e["punto"][0], problema))),
               float(sp.N(_sustituir_parametro(e["punto"][1], problema)))) for e in equilibrios]
    caja = muestreo.caja_alrededor(puntos, margen=0.5, minimo=2.0)
    if separatriz is not None and separatriz["energia"] is not None:
        nivel = float(sp.N(_sustituir_parametro(separatriz["energia"], problema)))
        minimo = min(float(sp.N(H_num.subs({x: px, v: py}))) for px, py in puntos) if puntos else 0.0
        alto = 1.5 * math.sqrt(max(2 * (nivel - minimo), 1.0))
        caja = (caja[0], (min(caja[1][0], -alto), max(caja[1][1], alto)))
    xs, ys, zs = muestreo.malla_de_nivel(H_num, [x, v], caja)
    capas = [{"tipo": "contorno", "rol": "nivel", "nombre": "Curvas de nivel de H",
              "x": xs, "y": ys, "z": zs}]
    if separatriz is not None and separatriz.get("rama") is not None:
        rama = _sustituir_parametro(separatriz["rama"], problema)
        tramos = separatriz.get("intervalos") or [sp.Interval(*caja[0])]
        sx, sy = [], []
        for tramo in tramos:
            a = max(caja[0][0], float(tramo.start))
            b = min(caja[0][1], float(tramo.end))
            for signo_rama in (1, -1):
                cx, cy = muestreo.curva(signo_rama * rama, x, a, b)
                sx += cx + [None]
                sy += cy + [None]
        capas.append({"tipo": "linea", "rol": "separatriz", "nombre": "Separatriz", "x": sx, "y": sy})
    if problema.ci is not None:
        f = problema.campo_numerico()
        duracion = d.resultados.get("periodo") or 20.0
        orbita = muestreo.trayectoria(f, [float(sp.N(c)) for c in problema.ci[1]], duracion)
        if orbita:
            capas.append({"tipo": "linea", "rol": "trayectoria", "nombre": "Órbita con la CI dada",
                          "x": orbita["x"], "y": orbita["y"]})
    for e, (px, py) in zip(equilibrios, puntos):
        estado = "inestable" if e["tipo"] == "punto silla" else "estable"
        capas.append({"tipo": "puntos", "rol": f"equilibrio:{estado}",
                      "nombre": f"{e['tipo']} ({px:g}, {py:g})", "x": [px], "y": [py]})
    titulo = "Retrato de fase hamiltoniano"
    if problema.parametro is not None and any(s.name == problema.parametro.name
                                              for s in sp.sympify(H).free_symbols):
        titulo += f" ({problema.parametro} = {problema.valor_representativo():g})"
    d.grafica({"clave": "retrato_fase", "titulo": titulo,
               "ejes": {"x": sp.pretty(x), "y": sp.pretty(punto)},
               "rango": {"x": list(caja[0]), "y": list(caja[1])}, "capas": capas})
