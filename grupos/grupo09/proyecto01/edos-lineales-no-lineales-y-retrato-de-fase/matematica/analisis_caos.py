"""Caos en mapas unidimensionales: el problema 4.1 del balotario.

Es el único problema del Tema 4 con solución desarrollada en el balotario, así
que es lo único de "caos" que se implementa. Su procedimiento, generalizado a
cualquier mapa x_{n+1} = f(x_n) de una variable (también definido a trozos):

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

Lo que sigue del Tema 4 (duplicación de periodo, Feigenbaum, disipatividad y
espectro de Lyapunov de flujos) no tiene solución en el balotario: queda FUERA
DE ALCANCE POR AHORA y lo declara `matematica.clasificacion`.
"""

from __future__ import annotations

import math

import mpmath
import numpy as np
import sympy as sp

from matematica import MetodoNoAplicable
from matematica.desarrollo import Desarrollo, L, intervalo_latex

TEMA = "Tema 4 · Sistemas dinámicos caóticos"

#: Iteraciones para estimar el exponente y transitorio descartado.
ITERACIONES = 1500
TRANSITORIO = 100

#: Semilla por defecto: irracional, para no caer en una preimagen del quiebre.
SEMILLA_POR_DEFECTO = (math.sqrt(2) - 1) / 2


def identificar_mapa_1d(problema):
    if problema.tipo != "mapa" or problema.dimension != 1:
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
