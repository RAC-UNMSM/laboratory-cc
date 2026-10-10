"""Caos en mapas unidimensionales: los problemas 4.1, 4.2 y 4.3 del balotario.

Tres familias, cada una con el procedimiento del balotario:

* `mapa_1d` (4.1): exponente de Lyapunov y horizonte de un mapa sin parámetro;
* `duplicacion_periodo` (4.2): un mapa con parámetro r, sus puntos fijos y
  multiplicadores, la órbita de periodo 2 (factorizando f²(x) − x por f(x) − x)
  y su estabilidad por Vieta, hasta los umbrales r₁ y r₂;
* `feigenbaum` (4.3): la estimación de r_∞ por la serie geométrica de razón
  1/δ, contrastada con los r_n calculados numéricamente.

El procedimiento del 4.1, generalizado a cualquier mapa x_{n+1} = f(x_n) de una
variable (también definido a trozos):

1. derivada en cada trozo y puntos donde no existe (la cúspide de la tienda);
2. puntos fijos f(x*) = x* en cada trozo y su multiplicador μ = f'(x*):
   |μ| < 1 atrae, |μ| > 1 repele;
3. exponente de Lyapunov λ = lim (1/n) Σ ln|f'(xᵢ)|, por la regla de la
   cadena. Si |f'| es constante c casi en todas partes, λ = ln c exactamente;
   si no, se estima sobre una órbita calculada con precisión arbitraria;
4. horizonte de predictibilidad: δₙ ≈ δ₀e^{nλ} llega a orden 1 en
   n* = ⌈ln(1/δ₀)/λ⌉ iteraciones.

Por qué precisión arbitraria: en un mapa lineal a trozos de pendiente ±2,
cada iteración desplaza un bit; en doble precisión la órbita colapsa a 0 en
unas 55 iteraciones y el promedio de Lyapunov sale mal. Con mpmath la órbita
es la verdadera.

La disipatividad de Lorenz (4.4) y el espectro de Lyapunov de flujos (4.5)
están en `matematica.caos_en_flujos`.
"""

from __future__ import annotations

import math

import mpmath
import numpy as np
import sympy as sp
from scipy.optimize import fsolve
from sympy.polys.polyfuncs import symmetrize

from matematica import DatoInvalido, MetodoNoAplicable
from matematica.analisis_estabilidad import describir_conjunto
from matematica.desarrollo import Desarrollo, F, L, intervalo_latex

TEMA = "Tema 4 · Sistemas dinámicos caóticos"

#: Constante de Feigenbaum δ (universal para mapas unimodales con máximo cuadrático).
DELTA_FEIGENBAUM = 4.669201609102990

#: Valores de referencia del mapa logístico (Feigenbaum 1978; Briggs 1991).
R_INFINITO_LOGISTICO = 3.569945671870944

#: Iteraciones para estimar el exponente y transitorio descartado.
ITERACIONES = 1500
TRANSITORIO = 100

#: Semilla por defecto: irracional, para no caer en una preimagen del quiebre.
SEMILLA_POR_DEFECTO = (math.sqrt(2) - 1) / 2


def identificar_mapa_1d(problema):
    # Con un parámetro simbólico no hay un λ que calcular: es el 4.2.
    if problema.tipo != "mapa" or problema.dimension != 1 or problema.tiene_parametro:
        return None
    return {}


def _trozos(problema):
    """[(expresión, intervalo)] del mapa, desde `trozos` o reescribiendo Abs/Min/Max."""
    x = problema.estados[0]
    dominio = _dominio(problema)
    if problema.trozos:
        piezas = []
        for i, (expresion, a, b) in enumerate(problema.trozos):
            abierto_izq = i > 0 and problema.trozos[i - 1][2] == a
            piezas.append((expresion, sp.Interval(a, b, left_open=abierto_izq)))
        return piezas, dominio
    expresion = sp.sympify(problema.campo[0])
    reescrita = sp.piecewise_fold(expresion.rewrite(sp.Piecewise))
    if not isinstance(reescrita, sp.Piecewise):
        return [(expresion, dominio)], dominio
    piezas, cubierto = [], sp.EmptySet
    for expresion_i, condicion in reescrita.args:
        conjunto = (condicion.as_set() if condicion is not sp.true else sp.S.Reals).intersect(dominio)
        conjunto = conjunto - cubierto
        cubierto = cubierto.union(conjunto)
        if conjunto is not sp.EmptySet and conjunto.measure > 0:
            piezas.append((sp.expand(expresion_i), conjunto))
    piezas.sort(key=lambda p: float(p[1].inf))
    return piezas, dominio


def _dominio(problema):
    x = problema.estados[0]
    if problema.trozos:
        return sp.Interval(problema.trozos[0][1], problema.trozos[-1][2])
    if x in problema.region:
        a, b = problema.region[x]
        return sp.Interval(sp.nsimplify(a) if a is not None else -sp.oo,
                           sp.nsimplify(b) if b is not None else sp.oo)
    return sp.Interval(0, 1)


def desarrollar_mapa_1d(problema, datos=None) -> Desarrollo:
    if identificar_mapa_1d(problema) is None:
        raise MetodoNoAplicable("Se esperaba un mapa unidimensional x_{n+1} = f(x_n).")
    x = problema.estados[0]
    piezas, dominio = _trozos(problema)
    d = Desarrollo("mapa_1d", "Mapa unidimensional: exponente de Lyapunov", TEMA,
                   "Derivada a trozos, puntos fijos, exponente de Lyapunov y horizonte de predictibilidad",
                   tratamiento=["analitico", "numerico"], balotario=["4.1"])
    d.guardar("dominio", dominio)

    # --- 1. Derivada ------------------------------------------------------------------
    seccion = d.seccion("derivada", "Diferenciabilidad y derivada casi en todas partes")
    filas = r" \\ ".join(rf"{L(e)}, & {L(x)} \in {intervalo_latex(I)}" for e, I in piezas)
    seccion.formula(rf"f({L(x)}) = \begin{{cases}} {filas} \end{{cases}}")
    derivadas = [sp.simplify(sp.diff(e, x)) for e, _ in piezas]
    filas = r" \\ ".join(rf"{L(dv)}, & {L(x)} \in {intervalo_latex(sp.Interval.open(I.inf, I.sup))}"
                         for dv, (_, I) in zip(derivadas, piezas))
    seccion.formula(rf"f'({L(x)}) = \begin{{cases}} {filas} \end{{cases}}")
    quiebres = []
    for (e1, I1), (e2, I2), d1, d2 in zip(piezas[:-1], piezas[1:], derivadas[:-1], derivadas[1:]):
        if sp.simplify(d1.subs(x, I1.sup) - d2.subs(x, I2.inf)) != 0:
            quiebres.append(I1.sup)
            seccion.formula(rf"f'_-\left({L(I1.sup)}\right) = {L(d1.subs(x, I1.sup))} \neq "
                            rf"{L(d2.subs(x, I2.inf))} = f'_+\left({L(I1.sup)}\right)",
                            r"\quad (\text{no derivable en el quiebre})")
    modulos = {sp.simplify(sp.Abs(dv)) for dv in derivadas}
    constante = next(iter(modulos)) if len(modulos) == 1 and next(iter(modulos)).is_number else None
    if constante is not None:
        excluidos = r",\; ".join(L(q) for q in quiebres)
        seccion.formula(rf"|f'({L(x)})| = {L(constante)}" +
                        (rf"\qquad \left(\forall {L(x)} \ne {excluidos}\right)" if quiebres else ""),
                        destacada=True, ref="modulo_derivada")
        d.guardar("modulo_derivada", constante)
    d.guardar("derivadas", list(zip(derivadas, [I for _, I in piezas])))
    d.guardar("quiebres", quiebres)

    # --- 2. Puntos fijos ---------------------------------------------------------------
    seccion = d.seccion("puntos_fijos", "Puntos fijos y su estabilidad")
    seccion.formula(rf"f({L(x)}^*) = {L(x)}^*")
    fijos = []
    for (expresion, I), dv in zip(piezas, derivadas):
        soluciones = [s for s in sp.solve(sp.Eq(expresion, x), x) if s.is_real and I.contains(s) == sp.true]
        for s in soluciones:
            fijos.append((s, dv))
            seccion.formula(rf"{L(x)} \in {intervalo_latex(I)}:\quad {L(expresion)} = {L(x)} \implies "
                            rf"{L(x)}^* = {L(s)}", destacada=True)
    resumen = []
    for i, (punto, dv) in enumerate(fijos, 1):
        if punto in quiebres:
            seccion.formula(rf"{L(x)}_{i}^* = {L(punto)}: \text{{f no es derivable; el multiplicador no existe}}")
            continue
        multiplicador = sp.simplify(dv.subs(x, punto))
        modulo = sp.Abs(multiplicador)
        estable = bool(modulo < 1)
        seccion.formula(rf"\mu_{i} = f'\left({L(punto)}\right) = {L(multiplicador)} \implies "
                        rf"|\mu_{i}| = {L(modulo)} {'<' if estable else ('>' if modulo > 1 else '=')} 1")
        resumen.append({"punto": punto, "multiplicador": multiplicador,
                        "estabilidad": "estable (atractor)" if estable else
                        ("inestable (repulsor)" if modulo > 1 else "no hiperbólico")})
    if resumen and all(r["estabilidad"].startswith("inestable") for r in resumen):
        seccion.formula(r"\text{Todos los puntos fijos son repulsores (inestables)}", destacada=True)
    d.guardar("puntos_fijos", resumen)

    # --- 3. Exponente de Lyapunov -------------------------------------------------------
    seccion = d.seccion("lyapunov", "Exponente de Lyapunov")
    seccion.formula(r"(f^n)'(x_0) = \prod_{i=0}^{n-1} f'(x_i) \implies "
                    r"\left|(f^n)'(x_0)\right| = \prod_{i=0}^{n-1} |f'(x_i)|")
    seccion.formula(r"\lambda(x_0) = \lim_{n \to \infty} \frac{1}{n} \ln\left|(f^n)'(x_0)\right| = "
                    r"\lim_{n \to \infty} \frac{1}{n} \sum_{i=0}^{n-1} \ln|f'(x_i)|")
    semilla = float(sp.N(problema.ci[1][0])) if problema.ci is not None else SEMILLA_POR_DEFECTO
    estimado = _lyapunov_numerico(piezas, derivadas, x, semilla)
    if constante is not None:
        lam = sp.log(constante)
        seccion.formula(rf"|f'(x_i)| = {L(constante)} \implies \lambda = \lim_{{n \to \infty}} "
                        rf"\frac{{1}}{{n}} \sum_{{i=0}}^{{n-1}} \ln {L(constante)} = "
                        rf"\lim_{{n \to \infty}} \frac{{n \ln {L(constante)}}}{{n}} = {L(lam)}")
        seccion.texto("Vale para toda órbita que no caiga en el conjunto numerable de preimágenes del "
                      "quiebre, es decir, para casi todo x₀.")
        valor = float(sp.N(lam))
        if estimado is not None:
            d.validar("lyapunov_numerico", abs(estimado["lambda"] - valor) < 3 * estimado["error"] + 1e-9,
                      f"El promedio de ln|f'| sobre {estimado['orbitas']} órbitas de {ITERACIONES} "
                      "iteraciones (precisión arbitraria) reproduce el valor exacto.",
                      medida=abs(estimado["lambda"] - valor), umbral=3 * estimado["error"] + 1e-9,
                      tipo="numerica")
    elif estimado is not None and estimado.get("superestable"):
        lam = -sp.oo
        valor = -math.inf
        seccion.formula(r"f'(x_i) = 0 \text{ en algún } x_i \implies \ln|f'(x_i)| = -\infty \implies "
                        r"\lambda = -\infty", destacada=True, ref="lyapunov")
        seccion.texto("La órbita pasa por un punto crítico de f (donde f' = 0) y converge a una órbita "
                      "superestable: las órbitas cercanas se acercan más rápido que cualquier exponencial.")
    else:
        if estimado is None:
            raise MetodoNoAplicable("No se pudo estimar el exponente: la órbita salió del dominio.")
        lam = sp.Float(estimado["lambda"], 6)
        seccion.formula(rf"\lambda \approx \frac{{1}}{{N}} \sum_{{i}} \ln|f'(x_i)| = {estimado['lambda']:.5f} "
                        rf"\pm {estimado['error']:.5f}")
        seccion.texto(f"|f'| no es constante: no hay forma cerrada inmediata y el exponente se estima "
                      f"promediando ln|f'| sobre {estimado['orbitas']} órbitas independientes de "
                      f"{ITERACIONES} iteraciones (precisión arbitraria, transitorio de {TRANSITORIO} "
                      "descartado); el ± es el error estándar entre órbitas.")
        valor = estimado["lambda"]
        d.validar("lyapunov_entre_orbitas", estimado["dispersion"] < 0.25 * max(abs(valor), 0.05),
                  "Las órbitas independientes dan exponentes consistentes entre sí.",
                  medida=estimado["dispersion"], umbral=0.25 * max(abs(valor), 0.05), tipo="numerica")
    signo_texto = ">" if valor > 0 else "<" if valor < 0 else "="
    if math.isfinite(valor):
        seccion.formula(rf"\lambda = {L(lam)} \approx {valor:.5f} {signo_texto} 0", destacada=True, ref="lyapunov")
    d.guardar("lyapunov", lam)
    d.guardar("lyapunov_valor", valor)
    if estimado is not None:
        d.guardar("lyapunov_estimado", {"valor": estimado["lambda"], "error": estimado["error"]})
    if valor > 0:
        d.concluir(f"λ ≈ {valor:.5f} > 0: dos órbitas cercanas se separan exponencialmente; el mapa "
                   "tiene dependencia sensible de las condiciones iniciales (caos determinista).")
    elif valor < 0:
        d.concluir(("λ = −∞" if not math.isfinite(valor) else f"λ ≈ {valor:.5f}") +
                   " < 0: las órbitas cercanas se acercan; la dinámica es regular (la órbita converge a "
                   "un atractor periódico), no caótica.")

    # --- 4. Horizonte de predictibilidad ---------------------------------------------
    delta0 = problema.separacion_inicial
    if delta0 is not None and valor > 0:
        delta0_exacto = sp.nsimplify(delta0)
        seccion = d.seccion("horizonte", "Divergencia exponencial y horizonte de predictibilidad")
        seccion.formula(rf"\delta_0 = {L(delta0_exacto)},\qquad \delta_n \approx \delta_0\, e^{{n\lambda}}"
                        + (rf" = \delta_0 \cdot {L(constante)}^n" if constante is not None else ""))
        seccion.formula(rf"\delta_0\, e^{{n^*\lambda}} = 1 \iff n^* = \frac{{\ln(1/\delta_0)}}{{\lambda}}")
        exacto = sp.log(1 / delta0_exacto) / lam
        numero_n = float(sp.N(exacto))
        n_estrella = math.ceil(numero_n - 1e-12)
        seccion.formula(rf"n^* = \frac{{{L(sp.log(1 / delta0_exacto))}}}{{{L(lam)}}} \approx {numero_n:.4f}",
                        r"\implies", rf"n^* = \lceil {numero_n:.2f} \rceil = {n_estrella}\ \text{{iteraciones}}",
                        destacada=True, ref="horizonte")
        bits = valor / math.log(2)
        seccion.formula(rf"\frac{{\lambda}}{{\ln 2}} = {bits:.4g}\ \text{{bit(s) de información perdidos por iteración}}")
        d.guardar("horizonte", n_estrella)
        d.guardar("horizonte_exacto", exacto)
        d.guardar("bits_por_iteracion", bits)
        d.concluir(f"Con δ₀ = {delta0:g}, la incertidumbre llega a orden 1 en n* = {n_estrella} "
                   f"iteraciones: el horizonte de predicción es finito y crece solo como ln(1/δ₀).")
        medida = _tasa_de_separacion(piezas, x, delta0, n_estrella + 6)
        if medida is not None:
            d.guardar("separacion_medida", medida["ejemplo"])
            d.guardar("tasa_de_separacion", medida["tasa"])
            tolerancia = max(0.1 * valor, 3 * medida["error"])
            d.validar("separacion_exponencial", abs(medida["tasa"] - valor) < tolerancia,
                      f"Pares de órbitas que empiezan a δ₀ se separan a una tasa media "
                      f"{medida['tasa']:.4f} ≈ λ ({medida['pares']} pares, hasta que la separación es "
                      "de orden 0.05).", medida=abs(medida["tasa"] - valor), umbral=tolerancia,
                      tipo="numerica")
            seccion.formula(rf"\text{{Medido: }} \frac{{1}}{{n}}\ln\frac{{\delta_n}}{{\delta_0}} \approx "
                            rf"{medida['tasa']:.4f}\quad (\text{{media de {medida['pares']} pares}}),\qquad "
                            rf"\text{{primer }} n \text{{ con }} \delta_n \ge 1/2:\ {medida['n_orden_uno']}")

    _graficas(d, piezas, derivadas, x, dominio, semilla, estimado, valor)
    return d


def _dentro(valor, intervalo):
    a, b = float(intervalo.inf), float(intervalo.sup)
    v = float(valor)
    izquierda = v > a if intervalo.left_open else v >= a
    derecha = v < b if intervalo.right_open else v <= b
    return izquierda and derecha


#: Órbitas independientes para el promedio de Lyapunov y pares para la separación.
ORBITAS = 8
PARES = 16


def _semillas(base, cantidad):
    """Semillas repartidas con la sucesión de razón áurea, que no repite ni cae en racionales simples."""
    paso = (math.sqrt(5) - 1) / 2
    return [(base + k * paso) % 1.0 for k in range(cantidad)]


def _orbita_media(funciones, semilla, bits):
    with mpmath.workprec(bits):
        actual = mpmath.mpf(semilla)
        suma = mpmath.mpf(0)
        recorrido = []
        for n in range(TRANSITORIO + ITERACIONES):
            elegida = next(((f, df) for f, df, I in funciones if _dentro(actual, I)), None)
            if elegida is None:
                return None
            f, df = elegida
            if n >= TRANSITORIO:
                derivada = abs(df(actual))
                if derivada == 0:              # punto crítico: ln|f'| = −∞
                    return -math.inf, recorrido
                suma += mpmath.log(derivada)
                recorrido.append(float(suma) / (n - TRANSITORIO + 1))
            actual = f(actual)
        return float(suma / ITERACIONES), recorrido


#: Iteraciones por órbita cuando basta la doble precisión.
ITERACIONES_DOBLE = 20000


def _diadico(derivadas, x):
    """True si todas las pendientes son constantes de módulo 2ᵏ (tienda, duplicación)."""
    for derivada in derivadas:
        if derivada.has(x):
            return False
        modulo = abs(float(sp.N(derivada)))
        if modulo == 0:
            return False
        exponente = math.log2(modulo)
        if abs(exponente - round(exponente)) > 1e-12:
            return False
    return True


def _orbita_media_doble(funciones, semilla, _bits=None):
    actual = float(semilla)
    suma = 0.0
    recorrido = []
    for n in range(TRANSITORIO + ITERACIONES_DOBLE):
        elegida = next(((f, df) for f, df, I in funciones if _dentro(actual, I)), None)
        if elegida is None:
            return None
        f, df = elegida
        if n >= TRANSITORIO:
            derivada = abs(df(actual))
            if derivada == 0:                  # punto crítico: ln|f'| = −∞
                return -math.inf, recorrido
            suma += math.log(derivada)
            if (n - TRANSITORIO) % 10 == 0:
                recorrido.append(suma / (n - TRANSITORIO + 1))
        actual = float(f(actual))
    return suma / ITERACIONES_DOBLE, recorrido


def _lyapunov_numerico(piezas, derivadas, x, semilla):
    """Promedio de ln|f'(xᵢ)| sobre varias órbitas con precisión suficiente para no colapsar.

    La precisión crece con la pendiente: cada iteración de una pendiente 2
    consume un bit. El error estándar entre órbitas acota cuánto se puede
    afirmar del valor.
    """
    a = min(float(I.inf) for _, I in piezas)
    b = max(float(I.sup) for _, I in piezas)
    pendiente = max(float(abs(sp.N(dv.subs(x, (I.inf + I.sup) / 2)))) for dv, (_, I) in zip(derivadas, piezas))
    if _diadico(derivadas, x):
        # Pendientes ±2ᵏ: en doble precisión cada iteración desplaza bits y la
        # órbita colapsa a un punto fijo; hace falta precisión arbitraria.
        bits = int((TRANSITORIO + ITERACIONES) * max(1.0, math.log2(max(pendiente, 1.0)))) + 128
        modulo = "mpmath"
        orbita = _orbita_media
    else:
        # El resto se promedia en doble precisión, que es lo habitual (el
        # redondeo no sesga el promedio) y permite órbitas mucho más largas.
        bits = None
        modulo = "math"
        orbita = _orbita_media_doble
    funciones = [(sp.lambdify(x, e, modulo), sp.lambdify(x, dv, modulo), I)
                 for (e, I), dv in zip(piezas, derivadas)]
    medias, recorrido = [], None
    for k, fraccion in enumerate(_semillas((semilla - a) / (b - a) if b > a else 0.3, ORBITAS)):
        resultado = orbita(funciones, a + fraccion * (b - a), bits)
        if resultado is None:
            continue
        medias.append(resultado[0])
        if recorrido is None:
            recorrido = resultado[1]
    if len(medias) < 2:
        return None
    if any(m == -math.inf for m in medias):
        # La órbita cae en un punto crítico (f' = 0) y converge a una órbita
        # superestable: la suma de ln|f'| diverge a −∞.
        return {"lambda": -math.inf, "error": 0.0, "dispersion": 0.0, "orbitas": len(medias),
                "promedios": recorrido, "superestable": True}
    media = float(np.mean(medias))
    dispersion = float(np.std(medias, ddof=1))
    return {"lambda": media, "error": dispersion / math.sqrt(len(medias)), "dispersion": dispersion,
            "orbitas": len(medias), "promedios": recorrido}


def _tasa_de_separacion(piezas, x, delta0, pasos):
    """Tasa media (1/n)·ln(δₙ/δ₀) de varios pares de órbitas, hasta que δₙ llega a 0.05.

    Un solo par no sirve: si cruza el quiebre de la tienda, o la pendiente
    local fluctúa, se desvía de δ₀e^{nλ} sin que nada esté mal. El promedio sobre
    pares independientes sí debe dar λ.
    """
    funciones = [(sp.lambdify(x, e, "mpmath"), I) for e, I in piezas]
    a = min(float(I.inf) for _, I in piezas)
    b = max(float(I.sup) for _, I in piezas)
    tasas, ejemplo, primeros = [], None, []
    with mpmath.workprec(64 + 4 * pasos + int(abs(math.log2(delta0))) + 64):
        for fraccion in _semillas(0.137, PARES):
            p, q = mpmath.mpf(a + fraccion * (b - a)), mpmath.mpf(a + fraccion * (b - a)) + mpmath.mpf(delta0)
            distancias = []
            for _ in range(pasos):
                distancias.append(float(abs(p - q)))
                fp = next((f for f, I in funciones if _dentro(p, I)), None)
                fq = next((f for f, I in funciones if _dentro(q, I)), None)
                if fp is None or fq is None:
                    break
                p, q = fp(p), fq(q)
            if ejemplo is None:
                ejemplo = distancias
            hasta = next((n for n, dn in enumerate(distancias) if dn >= 0.05), None)
            if hasta and hasta > 2:
                tasas.append(math.log(distancias[hasta] / delta0) / hasta)
            uno = next((n for n, dn in enumerate(distancias) if dn >= 0.5), None)
            if uno is not None:
                primeros.append(uno)
    if len(tasas) < 4:
        return None
    return {"tasa": float(np.mean(tasas)), "error": float(np.std(tasas, ddof=1) / math.sqrt(len(tasas))),
            "pares": len(tasas), "ejemplo": ejemplo,
            "n_orden_uno": int(np.median(primeros)) if primeros else None}


def _graficas(d, piezas, derivadas, x, dominio, semilla, estimado, valor):
    a, b = float(dominio.inf), float(dominio.sup)
    capas = []
    for expresion, I in piezas:
        xs = np.linspace(float(I.inf), float(I.sup), 120)
        ys = np.asarray(sp.lambdify(x, expresion, "numpy")(xs), dtype=float) * np.ones_like(xs)
        capas.append({"tipo": "linea", "rol": "mapa", "nombre": f"f(x) = {sp.sstr(expresion)}",
                      "x": xs.tolist(), "y": ys.tolist()})
    capas.append({"tipo": "linea", "rol": "diagonal", "nombre": "y = x", "x": [a, b], "y": [a, b]})
    funciones = [(sp.lambdify(x, e, "mpmath"), I) for e, I in piezas]
    with mpmath.workprec(256):
        actual = mpmath.mpf(semilla)
        tx, ty = [float(actual)], [0.0 if a <= 0 <= b else a]
        for _ in range(14):
            f = next((g for g, I in funciones if _dentro(actual, I)), None)
            if f is None:
                break
            siguiente = f(actual)
            tx += [float(actual), float(siguiente)]
            ty += [float(siguiente), float(siguiente)]
            actual = siguiente
    capas.append({"tipo": "linea", "rol": "telarana", "nombre": f"Órbita desde x₀ = {semilla:.4g}", "x": tx, "y": ty})
    for fijo in d.resultados.get("puntos_fijos", []):
        p = float(sp.N(fijo["punto"]))
        capas.append({"tipo": "puntos", "rol": "equilibrio:inestable" if fijo["estabilidad"].startswith("inestable")
                      else "equilibrio:estable", "nombre": f"x* = {sp.sstr(fijo['punto'])}", "x": [p], "y": [p]})
    d.grafica({"clave": "telarana", "titulo": "Diagrama de telaraña (cobweb)",
               "ejes": {"x": "xₙ", "y": "xₙ₊₁"}, "rango": {"x": [a, b], "y": [a, b]}, "capas": capas,
               "cuadrada": True})
    if estimado is not None and estimado.get("promedios"):
        promedios = estimado["promedios"]
        paso = max(1, len(promedios) // 400)
        n = list(range(1, len(promedios) + 1))[::paso]
        d.grafica({"clave": "convergencia_lyapunov", "titulo": "Convergencia del exponente de Lyapunov",
                   "ejes": {"x": "n", "y": "(1/n) Σ ln|f'(xᵢ)|"},
                   "capas": [{"tipo": "linea", "rol": "trayectoria", "nombre": "Promedio acumulado",
                              "x": n, "y": promedios[::paso]},
                             *([{"tipo": "linea", "rol": "referencia", "nombre": f"λ = {valor:.5f}",
                                 "x": [1, len(promedios)], "y": [valor, valor]}] if math.isfinite(valor) else [])]})
    separacion = d.resultados.get("separacion_medida")
    if separacion:
        ns = list(range(len(separacion)))
        delta0 = separacion[0]
        teorica = [min(delta0 * math.exp(k * valor), 10.0) for k in ns]
        d.grafica({"clave": "separacion", "titulo": "Crecimiento de la separación δₙ",
                   "ejes": {"x": "n", "y": "δₙ"}, "escala_y": "log",
                   "capas": [{"tipo": "linea", "rol": "trayectoria", "nombre": "|xₙ − yₙ| medida",
                              "x": ns, "y": [max(s, 1e-300) for s in separacion], "marcadores": True},
                             {"tipo": "linea", "rol": "referencia", "nombre": "δ₀ e^{nλ}", "x": ns, "y": teorica},
                             {"tipo": "vertical", "rol": "critico", "nombre": f"n* = {d.resultados.get('horizonte')}",
                              "x": float(d.resultados.get("horizonte", 0))}]})


# ===========================================================================
# 4.2 · Duplicación de periodo de un mapa con parámetro
# ===========================================================================

def identificar_duplicacion_periodo(problema):
    if problema.tipo != "mapa" or problema.dimension != 1 or not problema.tiene_parametro:
        return None
    if problema.trozos:
        return None
    return {}


def _intervalo(cotas):
    a, b = cotas
    return sp.Interval(sp.nsimplify(a) if a is not None else -sp.oo,
                       sp.nsimplify(b) if b is not None else sp.oo)


def _dominio_mapa(problema):
    x = problema.estados[0]
    return _intervalo(problema.region[x]) if x in problema.region else None


def _rango_parametro(problema):
    return _intervalo(problema.rango_parametro) if problema.rango_parametro else sp.S.Reals


def _clausura(conjunto):
    try:
        return conjunto.closure
    except (AttributeError, NotImplementedError):
        return conjunto


def _raiz_partida(discriminante):
    """√Δ = c·√Δ' con c fuera de la raíz: √(r²(r−3)(r+1)) = r·√((r−3)(r+1))."""
    raiz = sp.sqrt(discriminante)
    fuera, dentro = [], []
    for factor in sp.Mul.make_args(raiz):
        if isinstance(factor, sp.Pow) and factor.exp == sp.Rational(1, 2):
            dentro.append(factor.base)
        else:
            fuera.append(factor)
    return sp.Mul(*fuera), (sp.Mul(*dentro, evaluate=False) if len(dentro) > 1 else
                            (dentro[0] if dentro else sp.Integer(1)))


def _calculo_duplicacion(f, x, r, rango, dominio):
    """El cálculo del 4.2 sin presentación (lo reutiliza el 4.3).

    Devuelve los puntos fijos con su conjunto de existencia, multiplicador y
    conjunto de estabilidad, el umbral r₁ (multiplicador −1), la órbita de
    periodo 2 por factorización de f²(x) − x, su multiplicador por Vieta y el
    umbral r₂. Si f²(x) − x no deja un factor cuadrático (mapas no
    polinómicos o de grado alto), `periodo2` es None y r₂ se busca numéricamente.
    """
    derivada = sp.factor(sp.diff(f, x))
    fijos = []
    for punto in sp.solve(sp.Eq(f, x), x):
        punto = sp.simplify(punto)
        existe = rango
        # ±√(r − 1) solo es un punto real donde el radicando no es negativo.
        for potencia in punto.atoms(sp.Pow):
            if potencia.exp == sp.Rational(1, 2) and potencia.base.has(r):
                existe = existe.intersect(sp.solveset(potencia.base >= 0, r, rango))
        if dominio is not None:
            if dominio.inf.is_finite:
                existe = existe.intersect(sp.solveset(punto >= dominio.inf, r, rango))
            if dominio.sup.is_finite:
                existe = existe.intersect(sp.solveset(punto <= dominio.sup, r, rango))
        fijos.append({"punto": punto, "existe": existe})
    if not fijos:
        raise MetodoNoAplicable("El mapa no tiene puntos fijos reales: no hay órbita de periodo 1 que "
                                "pueda duplicarse.")
    # Un punto fijo que nace en el borde de su conjunto de existencia nace del
    # choque con otro: en ese valor todavía no es un punto nuevo.
    for fijo in fijos:
        if fijo["existe"] == rango:
            continue
        for otro in fijos:
            if otro is fijo:
                continue
            choques = sp.solveset(sp.Eq(fijo["punto"], otro["punto"]), r, rango)
            if isinstance(choques, sp.FiniteSet):
                fijo["existe"] = fijo["existe"] - choques
    for fijo in fijos:
        mu = sp.simplify(derivada.subs(x, fijo["punto"]))
        fijo["multiplicador"] = mu
        fijo["estable"] = (sp.solveset(mu < 1, r, fijo["existe"])
                           .intersect(sp.solveset(mu > -1, r, fijo["existe"])))
        fijo["duplica"] = sp.solveset(sp.Eq(mu, -1), r, _clausura(fijo["existe"]))
        fijo["tangente"] = sp.solveset(sp.Eq(mu, 1), r, _clausura(fijo["existe"]))
    candidatos = []
    for i, fijo in enumerate(fijos):
        if isinstance(fijo["duplica"], sp.FiniteSet):
            for valor in fijo["duplica"]:
                if _clausura(fijo["estable"]).contains(valor) == sp.true:
                    candidatos.append((valor, i))
    if not candidatos:
        raise MetodoNoAplicable("Ningún punto fijo estable alcanza el multiplicador −1 en el rango del "
                                "parámetro: el mapa no tiene una duplicación de periodo allí.")
    r1, indice = min(candidatos, key=lambda c: float(c[0]))

    resultado = {"derivada": derivada, "fijos": fijos, "r1": r1, "indice_r1": indice,
                 "f2": sp.factor(f.subs(x, f)), "periodo2": None, "r2": None}
    cociente = sp.cancel((f.subs(x, f) - x) / (f - x))
    if not (cociente.is_polynomial(x) and sp.degree(cociente, x) == 2):
        return resultado
    A, B, C = [sp.factor(c) for c in sp.Poly(cociente, x).all_coeffs()]
    discriminante = sp.factor(B ** 2 - 4 * A * C)
    fuera, dentro = _raiz_partida(discriminante)
    raices = [sp.simplify((-B + signo * sp.sqrt(discriminante)) / (2 * A)) for signo in (1, -1)]
    existe2 = sp.solveset(discriminante > 0, r, rango)
    p, q = sp.symbols("p q")
    producto = derivada.subs(x, p) * derivada.subs(x, q)
    simetrica, resto, definiciones = symmetrize(sp.expand(producto), [p, q], formal=True)
    if resto != 0:
        return resultado
    (s1, _), (s2, _) = definiciones
    multiplicador2 = sp.expand(sp.simplify(simetrica.subs({s1: -B / A, s2: C / A})))
    estable2 = (sp.solveset(multiplicador2 < 1, r, existe2)
                .intersect(sp.solveset(multiplicador2 > -1, r, existe2)))
    duplica2 = sp.solveset(sp.Eq(multiplicador2, -1), r, _clausura(existe2))
    r2 = min((v for v in duplica2 if float(v) > float(r1)), key=float, default=None) \
        if isinstance(duplica2, sp.FiniteSet) else None
    resultado.update({
        "cociente": cociente, "coeficientes": (A, B, C), "discriminante": discriminante,
        "raiz_fuera": fuera, "raiz_dentro": dentro, "raices": raices, "existe2": existe2,
        "producto": sp.factor(producto), "simetrica": simetrica, "s1": s1, "s2": s2,
        "multiplicador2": multiplicador2, "estable2": estable2, "r2": r2, "periodo2": True})
    return resultado


def _mapa_numerico(f, x, r):
    funcion = sp.lambdify((x, r), f, "numpy")
    derivada = sp.lambdify((x, r), sp.diff(f, x), "numpy")
    return funcion, derivada


def _semilla_mapa(dominio):
    if dominio is not None and dominio.inf.is_finite and dominio.sup.is_finite:
        a, b = float(dominio.inf), float(dominio.sup)
        return a + 0.3 * (b - a)
    return 0.3


def _iterar(funcion, x0, r, transitorio=4000, guardar=8):
    valor = float(x0)
    for _ in range(transitorio):
        valor = float(funcion(valor, r))
        if not math.isfinite(valor) or abs(valor) > 1e6:
            return None
    orbita = []
    for _ in range(guardar):
        valor = float(funcion(valor, r))
        orbita.append(valor)
    return orbita


def _periodo(orbita, tolerancia=1e-7):
    for p in (1, 2, 4, 8, 16):
        if all(abs(orbita[i + p] - orbita[i]) < tolerancia for i in range(len(orbita) - p)):
            return p
    return None


def _umbrales_numericos(funcion, derivada, r1, r2, x0, cantidad=7, delta=DELTA_FEIGENBAUM):
    """r₁, r₂, r₃, ...: donde la órbita de periodo 2^{n−1} tiene multiplicador −1.

    Se resuelve el sistema f^p(x) = x, (f^p)'(x) = −1 con p = 2^{n−1} por
    Newton, partiendo de la órbita estable que se obtiene iterando a mitad de
    camino entre r_{n−1} y el r_n que predice la razón δ.
    """
    valores = [float(r1), float(r2)]
    residuos = []
    for n in range(3, cantidad + 1):
        p = 2 ** (n - 1)
        paso = (valores[-1] - valores[-2]) / delta
        r_iter = valores[-1] + 0.5 * paso

        def ecuaciones(v, p=p):
            xx, rr = v
            valor, producto = xx, 1.0
            for _ in range(p):
                producto *= float(derivada(valor, rr))
                valor = float(funcion(valor, rr))
            return [valor - xx, producto + 1.0]

        orbita = _iterar(funcion, x0, r_iter, transitorio=20000, guardar=1)
        if orbita is None:
            break
        solucion, info, ok, _ = fsolve(ecuaciones, [orbita[-1], valores[-1] + paso], full_output=True,
                                       xtol=1e-13)
        nuevo = float(solucion[1])
        if ok != 1 or not valores[-1] < nuevo < valores[-1] + 3 * paso:
            break
        residuos.append(float(max(abs(v) for v in ecuaciones(solucion))))
        valores.append(nuevo)
    return valores, residuos


def _diagrama_bifurcacion(funcion, x0, r_min, r_max, columnas=260, filas=70):
    """Puntos (r, x) del atractor para una malla de r: se itera vectorizado en r."""
    rs = np.linspace(r_min, r_max, columnas)
    xs = np.full(columnas, float(x0))
    with np.errstate(all="ignore"):
        for _ in range(600):
            xs = funcion(xs, rs)
        puntos_r, puntos_x = [], []
        for _ in range(filas):
            xs = funcion(xs, rs)
            validos = np.isfinite(xs) & (np.abs(xs) < 1e6)
            puntos_r.extend(rs[validos].tolist())
            puntos_x.extend(xs[validos].tolist())
    return puntos_r, puntos_x


def desarrollar_duplicacion_periodo(problema, datos=None) -> Desarrollo:
    if identificar_duplicacion_periodo(problema) is None:
        raise MetodoNoAplicable("Se esperaba un mapa x_{n+1} = f(x_n; r) con un parámetro simbólico.")
    x, r = problema.estados[0], problema.parametro
    f = problema.campo[0]
    rango, dominio = _rango_parametro(problema), _dominio_mapa(problema)
    c = _calculo_duplicacion(f, x, r, rango, dominio)
    d = Desarrollo("duplicacion_periodo", "Mapa con parámetro: duplicación de periodo", TEMA,
                   "Puntos fijos y multiplicadores, órbita de periodo 2 por factorización de f²(x) − x "
                   "y su estabilidad por Vieta", tratamiento=["analitico", "numerico"], balotario=["4.2"])
    fx = sp.Function("f")(x)

    # --- 1. Puntos fijos ------------------------------------------------------------
    s = d.seccion("puntos_fijos", "Determinar los puntos fijos")
    s.formula(fx, "=", f, r",\qquad", sp.Function("f")(sp.Symbol(x.name + "^*")), "=", sp.Symbol(x.name + "^*"))
    s.formula(f, "=", x, r"\iff", sp.factor(f - x), "= 0")
    filas = []
    for i, fijo in enumerate(c["fijos"], 1):
        condicion = "" if fijo["existe"] == rango else rf"\quad \left({describir_conjunto(fijo['existe'], r)}\right)"
        filas.append(rf"{L(x)}_{i}^* = {L(_presentable(fijo['punto'], r))}{condicion}")
    s.formula(r",\qquad ".join(filas), destacada=True, ref="puntos_fijos")
    d.guardar("puntos_fijos", [{"punto": fijo["punto"], "existe": fijo["existe"]} for fijo in c["fijos"]])

    # --- 2. Estabilidad lineal ------------------------------------------------------
    s = d.seccion("estabilidad", "Estabilidad lineal de los puntos fijos")
    s.formula(rf"f'({L(x)})", "=", c["derivada"])
    for i, fijo in enumerate(c["fijos"], 1):
        mu = fijo["multiplicador"]
        estable = fijo["estable"]
        texto_estable = (describir_conjunto(estable, r) if estable is not sp.EmptySet
                         else r"\text{ningún valor del rango}")
        s.formula(rf"f'\left({L(x)}_{i}^*\right) = {L(mu)} \implies |{L(mu)}| < 1 \iff {texto_estable}",
                  destacada=estable is not sp.EmptySet)
    critico = c["fijos"][c["indice_r1"]]
    s.formula(rf"{L(r)} = {L(c['r1'])} \implies f'\left({L(x)}_{c['indice_r1'] + 1}^*\right) = -1",
              r"\quad \text{(multiplicador } \mu = -1\text{: condición de duplicación de periodo)}",
              destacada=True)
    tangentes = [v for fijo in c["fijos"] if isinstance(fijo["tangente"], sp.FiniteSet) for v in fijo["tangente"]]
    if tangentes:
        s.texto(f"En {r.name} = {', '.join(sp.sstr(v) for v in sorted(set(tangentes), key=float))} un "
                "multiplicador vale +1: allí los puntos fijos chocan e intercambian su estabilidad; esa "
                "bifurcación no duplica el periodo.")
    d.guardar("multiplicadores", [fijo["multiplicador"] for fijo in c["fijos"]])
    d.guardar("intervalos_estabilidad", [fijo["estable"] for fijo in c["fijos"]])

    funcion, derivada = _mapa_numerico(f, x, r)
    semilla = _semilla_mapa(dominio)
    r1 = c["r1"]
    if c["periodo2"]:
        # --- 3. Órbita de periodo 2 ---------------------------------------------------
        A, B, C = c["coeficientes"]
        s = d.seccion("periodo_2", "Ecuación de la órbita de periodo 2")
        s.formula(rf"f^2({L(x)}) = f\left(f({L(x)})\right) = {L(c['f2'])}")
        s.texto("Los puntos fijos de f también lo son de f²; factorizándolos (se comprueba por expansión "
                "directa):")
        s.formula(rf"f^2({L(x)}) - {L(x)} = {L(sp.factor(f.subs(x, f) - x))}")
        s.texto("Los puntos de periodo 2 son las raíces del factor cuadrático:")
        cuadratica = sp.Add(A * x ** 2, B * x, C, evaluate=False)
        s.formula(cuadratica, "= 0")
        s.formula(rf"\Delta = {L(sp.factor(B ** 2))} - {L(sp.factor(4 * A * C))} =", c["discriminante"])
        fuera, dentro = c["raiz_fuera"], c["raiz_dentro"]
        numerador = sp.simplify(-B / fuera)
        denominador = sp.simplify(2 * A / fuera)
        s.formula(rf"p,\, q = \frac{{{L(numerador)} \pm \sqrt{{{L(dentro)}}}}}{{{L(denominador)}}}",
                  destacada=True, ref="orbita_periodo_2")
        existe2 = c["existe2"]
        s.formula(rf"\Delta > 0 \iff {describir_conjunto(existe2, r)}", r"\implies",
                  r"\text{la órbita de periodo 2 existe (raíces reales y distintas) solo allí}", destacada=True)
        p_r1 = sp.nsimplify(sp.simplify(c["raices"][0].subs(r, r1)))
        q_r1 = sp.nsimplify(sp.simplify(c["raices"][1].subs(r, r1)))
        x_r1 = sp.simplify(critico["punto"].subs(r, r1))
        s.formula(rf"{L(r)} = {L(r1)} \implies p = q = {L(p_r1)} = {L(x)}_{c['indice_r1'] + 1}^*",
                  r"\quad (\text{la órbita de periodo 2 nace del punto fijo})")
        d.validar("nace_del_punto_fijo", sp.simplify(p_r1 - x_r1) == 0 and sp.simplify(q_r1 - x_r1) == 0,
                  "En r₁ las dos raíces del factor cuadrático coinciden con el punto fijo que pierde "
                  "estabilidad: la órbita de periodo 2 nace de él.")
        d.validar("factorizacion_f2", sp.simplify(sp.expand(f.subs(x, f) - x - (f - x) * c["cociente"])) == 0,
                  "f²(x) − x = (f(x) − x)·Q(x) por expansión directa.")
        d.guardar("orbita_periodo_2", c["raices"])
        d.guardar("discriminante", c["discriminante"])

        # --- 4. Estabilidad de la órbita de periodo 2 --------------------------------
        s = d.seccion("estabilidad_periodo_2", "Estabilidad de la órbita de periodo 2")
        suma, prod = sp.Symbol("(p + q)"), sp.Symbol("p q")
        corchete = sp.factor(c["simetrica"].subs({c["s1"]: suma, c["s2"]: prod}))
        s.formula(r"(f^2)'(p) = f'(p)\, f'(q) =", c["producto"], "=", corchete)
        s.formula(r"\text{Por Vieta: }\; p + q = ", sp.simplify(-B / A), r",\qquad p q = ", sp.simplify(C / A))
        m2 = c["multiplicador2"]
        s.formula(r"(f^2)'(p) = ", m2, ref="multiplicador_periodo_2")
        menor = sp.solveset(m2 < 1, r, existe2)
        mayor = sp.solveset(m2 > -1, r, existe2)
        s.formula(rf"\left|{L(m2)}\right| < 1 \iff \begin{{cases}} {L(sp.factor(m2 - 1))} < 0 \iff "
                  rf"{describir_conjunto(menor, r)} \\ {L(sp.factor(m2 + 1))} > 0 \iff "
                  rf"{describir_conjunto(mayor, r)} \end{{cases}}")
        s.formula(rf"\text{{La órbita de periodo 2 es estable para }} {describir_conjunto(c['estable2'], r)}",
                  destacada=True, ref="estabilidad_periodo_2")
        d.guardar("multiplicador_periodo_2", m2)
        d.guardar("intervalo_periodo_2", c["estable2"])

    # --- 5. Valor crítico ------------------------------------------------------------
    s = d.seccion("valor_critico", "Valor crítico")
    s.formula(rf"{L(r)}_1 = {L(r1)}", destacada=True, ref="r_1")
    d.guardar("r_1", r1)
    r2 = c["r2"]
    if r2 is not None:
        s.texto(f"En {r.name}₁ = {sp.sstr(r1)} el punto fijo {sp.sstr(_presentable(critico['punto'], r))} pierde "
                f"estabilidad con multiplicador −1 y, simultáneamente, nace una órbita de periodo 2 estable "
                "(duplicación de periodo supercrítica). La siguiente duplicación ocurre donde el multiplicador "
                "de la órbita de periodo 2 vale −1:")
        s.formula(c["multiplicador2"], "= -1", r"\implies", sp.factor(c["multiplicador2"] + 1), r"= 0 \implies",
                  rf"{L(r)}_2 = {L(r2)} \approx {float(r2):.5f}", destacada=True, ref="r_2")
        d.guardar("r_2", r2)
    else:
        s.texto("f²(x) − x no deja un factor cuadrático, así que la órbita de periodo 2 no tiene forma "
                "cerrada: el umbral r₂ no se obtiene analíticamente.")

    # --- Comprobaciones numéricas ----------------------------------------------------
    r1f = float(r1)
    r2f = float(r2) if r2 is not None else None
    if r2f is not None:
        medio = 0.5 * (r1f + r2f)
        orbita = _iterar(funcion, semilla, medio)
        if orbita is not None:
            esperado = sorted(float(sp.N(v.subs(r, medio))) for v in c["raices"])
            obtenido = sorted(set(round(v, 9) for v in orbita))
            ok = _periodo(orbita) == 2 and len(obtenido) == 2 and \
                max(abs(a - b) for a, b in zip(esperado, obtenido)) < 1e-6
            d.validar("orbita_periodo_2_iterada", ok,
                      f"Iterando el mapa en {r.name} = {medio:.4f} (entre r₁ y r₂) la órbita converge a un "
                      f"2-ciclo {{{obtenido[0]:.6f}, {obtenido[-1]:.6f}}} que coincide con p y q.",
                      tipo="numerica")
        despues = _iterar(funcion, semilla, r2f + 0.1 * (r2f - r1f) / DELTA_FEIGENBAUM)
        if despues is not None:
            d.validar("periodo_4_tras_r2", _periodo(despues) == 4,
                      f"Justo después de r₂ la órbita estable ya tiene periodo 4: la de periodo 2 perdió "
                      "estabilidad allí.", tipo="numerica")
    r_antes = r1f - 0.1 * (r2f - r1f if r2f else 0.4)
    antes = _iterar(funcion, semilla, r_antes)
    if antes is not None:
        # Puede haber más de un punto fijo estable (±√(r − 1) en un mapa impar): basta con llegar a uno.
        estables = [float(sp.N(fijo["punto"].subs(r, r_antes))) for fijo in c["fijos"]
                    if fijo["estable"].contains(sp.Float(r_antes)) == sp.true]
        d.validar("punto_fijo_antes_de_r1",
                  _periodo(antes) == 1 and any(abs(antes[-1] - e) < 1e-6 for e in estables),
                  "Antes de r₁ la órbita converge a un punto fijo estable calculado.", tipo="numerica")

    # --- Gráficas ----------------------------------------------------------------------
    r_inf = r1f + (r2f - r1f) * DELTA_FEIGENBAUM / (DELTA_FEIGENBAUM - 1) if r2f else r1f + 0.6
    r_min = max(float(rango.inf) if rango.inf.is_finite else -math.inf, r1f - (r_inf - r1f))
    r_max = min(float(rango.sup) if rango.sup.is_finite else math.inf, r_inf + 0.75 * (r_inf - r1f))
    rs, xs = _diagrama_bifurcacion(funcion, semilla, r_min, r_max)
    capas = [{"tipo": "puntos", "rol": "orbita", "nombre": "Atractor (iterado)", "x": rs, "y": xs, "tamano": 2}]
    malla = np.linspace(r_min, r_max, 300)
    for i, fijo in enumerate(c["fijos"], 1):
        valores = []
        for rv in malla:
            dentro = fijo["existe"].contains(sp.Float(rv)) == sp.true
            estable = fijo["estable"].contains(sp.Float(rv)) == sp.true
            valores.append((float(sp.N(fijo["punto"].subs(r, rv))) if dentro else None, estable))
        for estado in (True, False):
            capas.append({"tipo": "linea", "rol": "rama:estable" if estado else "rama:inestable",
                          "nombre": f"x{i}* {'estable' if estado else 'inestable'}", "x": malla.tolist(),
                          "y": [v if (v is not None and e == estado) else None for v, e in valores]})
    if r2f is not None:
        for raiz, nombre in zip(c["raices"], ("p", "q")):
            tramo = np.linspace(r1f, r2f, 60)
            capas.append({"tipo": "linea", "rol": "ciclo", "nombre": f"{nombre}(r): periodo 2 estable",
                          "x": tramo.tolist(), "y": [float(sp.N(raiz.subs(r, v))) for v in tramo]})
    capas.append({"tipo": "vertical", "rol": "critico", "nombre": f"r₁ = {sp.sstr(r1)}", "x": r1f})
    if r2f is not None:
        capas.append({"tipo": "vertical", "rol": "critico", "nombre": f"r₂ = {sp.sstr(r2)}", "x": r2f})
    d.grafica({"clave": "diagrama_bifurcacion", "titulo": "Diagrama de bifurcación del mapa",
               "ejes": {"x": r.name, "y": f"{x.name}*"}, "capas": capas})
    if r2f is not None:
        medio = 0.5 * (r1f + r2f)
        acotado = dominio is not None and dominio.inf.is_finite and dominio.sup.is_finite
        a, b = (float(dominio.inf), float(dominio.sup)) if acotado else (-0.5, 1.5)
        malla_x = np.linspace(a, b, 300)
        valores_f = funcion(malla_x, medio)
        valores_f2 = funcion(valores_f, medio)
        puntos = sorted(float(sp.N(v.subs(r, medio))) for v in c["raices"])
        d.grafica({"clave": "f_y_f2", "titulo": f"f y f² para {r.name} = {medio:.4f}: los puntos de periodo 2",
                   "ejes": {"x": x.name, "y": "f, f²"}, "rango": {"x": [a, b], "y": [a, b]}, "cuadrada": True,
                   "capas": [{"tipo": "linea", "rol": "mapa", "nombre": "f(x)", "x": malla_x.tolist(),
                              "y": np.asarray(valores_f, dtype=float).tolist()},
                             {"tipo": "linea", "rol": "particular", "nombre": "f²(x)", "x": malla_x.tolist(),
                              "y": np.asarray(valores_f2, dtype=float).tolist()},
                             {"tipo": "linea", "rol": "diagonal", "nombre": "y = x", "x": [a, b], "y": [a, b]},
                             {"tipo": "puntos", "rol": "equilibrio:estable", "nombre": "p, q (periodo 2)",
                              "x": puntos, "y": puntos}]})

    # --- Conclusión ----------------------------------------------------------------------
    texto = (f"El valor crítico es {r.name}₁ = {sp.sstr(r1)}. Allí el multiplicador del punto fijo "
             f"{x.name}* = {sp.sstr(_presentable(critico['punto'], r))} cruza −1 y se produce una duplicación "
             "de periodo: el punto fijo pasa a ser inestable y nace una órbita de periodo 2 estable.")
    if r2f is not None:
        texto += (f" Esa órbita es estable hasta {r.name}₂ = {sp.sstr(r2)} ≈ {r2f:.5f}, donde se repite el "
                  "mecanismo: es la primera etapa de la cascada 2ⁿ que conduce al caos.")
    d.concluir(texto)
    return d


def _presentable(expresion, r):
    """1 − 1/r en vez de (r − 1)/r, como en el balotario."""
    expresion = sp.sympify(expresion)
    if expresion.is_rational_function(r) and expresion.has(r):
        separada = sp.apart(expresion, r)
        if sp.count_ops(separada) <= sp.count_ops(expresion) + 1:
            return separada
    return expresion


# ===========================================================================
# 4.3 · Cascada de Feigenbaum y umbral de acumulación
# ===========================================================================

def identificar_feigenbaum(problema):
    if "feigenbaum" not in problema.pedidos:
        return None
    if problema.tipo == "teorico":
        return {}
    if problema.tipo == "mapa" and problema.dimension == 1 and problema.tiene_parametro and not problema.trozos:
        return {}
    return None


def _logistico():
    x = sp.Symbol("x", real=True)
    r = sp.Symbol("r", nonnegative=True)
    return r * x * (1 - x), x, r, sp.Interval(0, 4), sp.Interval(0, 1)


def _dato(datos, *claves):
    for clave in claves:
        if clave in datos and datos[clave] is not None:
            return datos[clave]
    return None


def _forma_cerrada(valor):
    """3.449489742783178 → 1 + √6 si lo es (dentro de 1e-12); si no, el decimal."""
    candidato = sp.nsimplify(valor, tolerance=1e-12)
    if candidato.is_number and abs(float(candidato) - valor) < 1e-11 and sp.count_ops(candidato) <= 6:
        return candidato
    return sp.Float(valor, 15)


def desarrollar_feigenbaum(problema, datos=None) -> Desarrollo:
    if identificar_feigenbaum(problema) is None:
        raise MetodoNoAplicable("Se esperaba un mapa con parámetro o los umbrales r₁, r₂ de una cascada.")
    d = Desarrollo("feigenbaum", "Cascada de Feigenbaum: umbral de acumulación", TEMA,
                   "Convergencia geométrica de los umbrales de duplicación y suma de la serie de razón 1/δ",
                   tratamiento=["analitico", "numerico"], balotario=["4.3"])
    datos_p = problema.datos or {}
    delta_dato = _dato(datos_p, "delta", "delta_feigenbaum", "δ")
    delta = float(delta_dato) if delta_dato is not None else DELTA_FEIGENBAUM
    if delta <= 1:
        raise DatoInvalido(f"La constante δ debe ser mayor que 1 (vale ≈ 4.669 para mapas unimodales); "
                           f"llegó δ = {delta:g}, con la que la serie geométrica no converge.")
    r1_dato, r2_dato = _dato(datos_p, "r_1", "r1"), _dato(datos_p, "r_2", "r2")

    # ¿De dónde salen r₁ y r₂: de un mapa o de los datos?
    if problema.tipo == "mapa":
        f, x, r = problema.campo[0], problema.estados[0], problema.parametro
        rango, dominio = _rango_parametro(problema), _dominio_mapa(problema)
        origen = "mapa"
    elif r1_dato is None or r2_dato is None:
        f, x, r, rango, dominio = _logistico()
        origen = "logistico"
    else:
        f = x = r = rango = dominio = None
        origen = "datos"
    if f is not None:
        calculo = _calculo_duplicacion(f, x, r, rango, dominio)
        if calculo["r2"] is None:
            raise MetodoNoAplicable("El mapa no deja una órbita de periodo 2 con forma cerrada: no se pueden "
                                    "obtener r₁ y r₂ exactos para la estimación.")
        r1, r2 = calculo["r1"], calculo["r2"]
        if r1_dato is not None and r2_dato is not None and \
                (abs(float(r1_dato) - float(r1)) > 1e-4 or abs(float(r2_dato) - float(r2)) > 1e-4):
            d.advertir(f"Los datos del enunciado (r₁ = {float(r1_dato):g}, r₂ = {float(r2_dato):g}) no coinciden "
                       f"con los umbrales del mapa (r₁ = {sp.sstr(r1)}, r₂ = {sp.sstr(r2)} ≈ {float(r2):.6f}): "
                       "se usan los del mapa, que son los que el cálculo demuestra.")
    else:
        r1, r2 = _forma_cerrada(float(r1_dato)), _forma_cerrada(float(r2_dato))
        # Si son los del mapa logístico, se puede contrastar con sus umbrales numéricos.
        f_l, x_l, r_l, rango_l, dominio_l = _logistico()
        if abs(float(r1) - 3) < 1e-6 and abs(float(r2) - (1 + math.sqrt(6))) < 1e-5:
            f, x, r, rango, dominio = f_l, x_l, r_l, rango_l, dominio_l
            origen = "datos_logistico"
    if not float(r2) > float(r1):
        raise DatoInvalido(f"Los umbrales deben crecer: llegó r₁ = {float(r1):g} y r₂ = {float(r2):g}. En la "
                           "cascada cada duplicación ocurre a un parámetro mayor que la anterior.")

    # --- 1. Ley de convergencia ------------------------------------------------------
    s = d.seccion("ley", "Ley de convergencia geométrica de Feigenbaum")
    s.formula(r"\delta = \lim_{n \to \infty} \frac{r_n - r_{n-1}}{r_{n+1} - r_n} \approx " + f"{delta:.7f}",
              destacada=True)
    s.texto("Sea dₙ = r_{n+1} − rₙ. Para n grande, dₙ ≈ d_{n−1}/δ: las distancias entre bifurcaciones forman "
            "(asintóticamente) una progresión geométrica de razón 1/δ.")
    if origen == "logistico":
        s.texto("El enunciado no da r₁ y r₂: se toman los del mapa logístico, el representante de los mapas "
                "unimodales, calculados exactamente como en el problema 4.2.")
    elif origen == "mapa":
        s.texto("r₁ y r₂ se obtienen exactamente del mapa dado, con el procedimiento del problema 4.2.")

    # --- 2. Datos ------------------------------------------------------------------------
    s = d.seccion("datos", "Datos")
    d1 = sp.simplify(r2 - r1)
    s.formula(rf"r_1 = {L(r1)},\qquad r_2 = {L(r2)}")
    s.formula(rf"d_1 = r_2 - r_1 = {L(r2)} - {L(r1)} = {L(d1)} \approx {float(d1):.6f}")
    d.guardar("r_1", r1)
    d.guardar("r_2", r2)
    d.guardar("d_1", d1)

    # --- 3. Serie geométrica ---------------------------------------------------------
    s = d.seccion("serie", "Serie geométrica para r_∞")
    k, dl = sp.Symbol("k", integer=True, positive=True), sp.Symbol("delta", positive=True)
    suma = sp.piecewise_fold(sp.summation(dl ** (-(k - 1)), (k, 2, sp.oo)))
    if isinstance(suma, sp.Piecewise):
        suma = suma.args[0].expr
    suma = sp.simplify(suma)
    d.validar("suma_geometrica", sp.simplify(suma - 1 / (dl - 1)) == 0,
              "La suma Σ_{k≥2} δ^{−(k−1)} vale 1/(δ − 1) para δ > 1 (sympy).")
    s.formula(r"r_\infty = r_2 + \sum_{k=2}^{\infty} d_k, \qquad d_k \approx \frac{d_1}{\delta^{\,k-1}}")
    s.formula(r"r_\infty \approx r_2 + d_1 \sum_{k=2}^\infty \delta^{-(k-1)} = r_2 + d_1\,"
              r"\frac{1/\delta}{1 - 1/\delta} = r_2 + d_1 \cdot " + L(suma))
    s.formula(r"r_\infty \approx r_2 + \frac{d_1}{\delta - 1}", destacada=True)

    # --- 4. Evaluación numérica ----------------------------------------------------------
    s = d.seccion("evaluacion", "Evaluación numérica")
    cociente = float(d1) / (delta - 1)
    r_inf = float(r2) + cociente
    r3 = float(r2) + float(d1) / delta
    s.formula(rf"\frac{{d_1}}{{\delta - 1}} = \frac{{{float(d1):.6f}}}{{{delta - 1:.7f}}} \approx {cociente:.6f}")
    s.formula(rf"r_\infty \approx {float(r2):.6f} + {cociente:.6f} \approx {r_inf:.5f}", destacada=True,
              ref="r_infinito")
    s.texto("Estimación de la tercera duplicación:")
    s.formula(rf"r_3 \approx r_2 + \frac{{d_1}}{{\delta}} = {float(r2):.6f} + \frac{{{float(d1):.6f}}}{{{delta:.7f}}}"
              rf" \approx {r3:.5f}")
    d.guardar("r_infinito", r_inf)
    d.guardar("r_3_estimado", r3)

    # --- 5. Comparación con los umbrales numéricos ------------------------------------
    if f is not None:
        funcion, derivada = _mapa_numerico(f, x, r)
        semilla = _semilla_mapa(dominio)
        umbrales, residuos = _umbrales_numericos(funcion, derivada, r1, r2, semilla)
        if len(umbrales) >= 4:
            s = d.seccion("comparacion", "Comparación con los valores numéricos")
            razones = [(umbrales[i] - umbrales[i - 1]) / (umbrales[i + 1] - umbrales[i])
                       for i in range(1, len(umbrales) - 1)]
            ultima = razones[-1]
            r_inf_num = umbrales[-1] + (umbrales[-1] - umbrales[-2]) / (ultima - 1)
            if origen in ("logistico", "datos_logistico") or _es_logistico(f, x, r):
                d.validar("extrapolacion_vs_referencia", abs(r_inf_num - R_INFINITO_LOGISTICO) < 2e-5,
                          f"La extrapolación de los umbrales numéricos ({r_inf_num:.6f}) coincide con el valor "
                          f"conocido r_∞ = {R_INFINITO_LOGISTICO:.6f} del mapa logístico.", tipo="numerica")
            s.tabla(["", "Estimación (Feigenbaum)", "Valor numérico"],
                    [[F("r_3"), f"{r3:.5f}", f"{umbrales[2]:.5f}"],
                     [F(r"r_\infty"), f"{r_inf:.5f}", f"{r_inf_num:.5f}"]])
            error = abs(r_inf - r_inf_num) / abs(r_inf_num)
            s.formula(rf"\text{{Error relativo en }} r_\infty:\quad \frac{{|{r_inf:.5f} - {r_inf_num:.5f}|}}"
                      rf"{{{r_inf_num:.5f}}} \approx {100 * error:.2g}\,\%")
            s.formula(r"\text{Umbrales calculados (multiplicador } -1 \text{ de la órbita de periodo } 2^{n-1}):\; "
                      + r",\; ".join(f"r_{{{i + 1}}} = {v:.6f}" for i, v in enumerate(umbrales)))
            s.formula(r"\frac{r_n - r_{n-1}}{r_{n+1} - r_n}:\; " + r",\; ".join(f"{v:.4f}" for v in razones),
                      r"\;\longrightarrow\; \delta")
            s.texto(f"La pequeña desviación se debe a que δ es un límite asintótico: los primeros cocientes no "
                    f"son exactamente δ (el primero vale ≈ {razones[0]:.2f}).")
            d.guardar("umbrales_numericos", umbrales)
            d.guardar("razones", razones)
            d.guardar("r_infinito_numerico", r_inf_num)
            d.guardar("error_relativo", error)
            d.validar("umbrales_numericos", max(residuos) < 1e-8,
                      f"Cada rₙ (n = 3..{len(umbrales)}) resuelve f^p(x) = x, (f^p)'(x) = −1 con p = 2^(n−1).",
                      medida=max(residuos), umbral=1e-8, tipo="numerica")
            d.validar("razones_tienden_a_delta", abs(ultima - delta) < 0.01,
                      f"El último cociente de distancias ({ultima:.5f}) ya está a menos de 0.01 de δ.",
                      medida=abs(ultima - delta), umbral=0.01, tipo="numerica")
            d.validar("estimacion_consistente", error < 0.02,
                      f"La estimación con dos umbrales difiere del valor numérico en {100 * error:.2g} %.",
                      medida=error, umbral=0.02, tipo="numerica")
            _graficas_feigenbaum(d, funcion, semilla, umbrales, r_inf, r1, r2, rango, x, r)
    d.concluir(f"Con solo dos bifurcaciones y la constante universal de Feigenbaum se estima r_∞ ≈ {r_inf:.4f}"
               + (f", con un error del orden de {100 * d.resultados['error_relativo']:.2g} % respecto al valor "
                  f"numérico {d.resultados['r_infinito_numerico']:.5f}" if "error_relativo" in d.resultados else "")
               + ". Para r > r_∞ comienza el régimen caótico, intercalado con ventanas periódicas. La constante "
                 "δ es universal: es la misma para toda la clase de mapas unimodales con máximo cuadrático.")
    return d


def _es_logistico(f, x, r):
    return sp.simplify(f - r * x * (1 - x)) == 0


def _graficas_feigenbaum(d, funcion, semilla, umbrales, r_inf, r1, r2, rango, x, r):
    r1f = float(r1)
    r_min = r1f - 0.15 * (r_inf - r1f)
    r_max = r_inf + 0.25 * (r_inf - r1f)
    if rango.sup.is_finite:
        r_max = min(r_max, float(rango.sup))
    rs, xs = _diagrama_bifurcacion(funcion, semilla, r_min, r_max, columnas=320, filas=80)
    capas = [{"tipo": "puntos", "rol": "orbita", "nombre": "Atractor (iterado)", "x": rs, "y": xs, "tamano": 2}]
    for i, valor in enumerate(umbrales, 1):
        capas.append({"tipo": "vertical", "rol": "critico" if i <= 2 else "referencia", "nombre": f"r{i} = {valor:.5f}",
                      "x": valor})
    capas.append({"tipo": "vertical", "rol": "frontera", "nombre": f"r∞ ≈ {r_inf:.5f} (estimado)", "x": r_inf})
    d.grafica({"clave": "cascada", "titulo": "Cascada de duplicaciones de periodo",
               "ejes": {"x": r.name, "y": x.name}, "capas": capas})
    distancias = [umbrales[i + 1] - umbrales[i] for i in range(len(umbrales) - 1)]
    n = list(range(1, len(distancias) + 1))
    d.grafica({"clave": "distancias", "titulo": "Distancias entre bifurcaciones: dₙ ≈ d₁/δⁿ⁻¹",
               "ejes": {"x": "n", "y": "dₙ = rₙ₊₁ − rₙ"}, "escala_y": "log",
               "capas": [{"tipo": "linea", "rol": "trayectoria", "nombre": "dₙ numérico", "x": n, "y": distancias,
                          "marcadores": True},
                         {"tipo": "linea", "rol": "referencia", "nombre": "d₁/δⁿ⁻¹", "x": n,
                          "y": [distancias[0] / DELTA_FEIGENBAUM ** (k - 1) for k in n]}]})
