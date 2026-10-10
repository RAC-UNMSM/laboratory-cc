"""Caos en flujos: los problemas 4.4 y 4.5 del balotario.

* `disipatividad` (4.4): divergencia del campo y contracción de volumen por
  Liouville; después, una función de Lyapunov cuadrática V = Σ aᵢ(xᵢ − cᵢ)²
  cuya derivada a lo largo del flujo es −k(Q − K) con Q definida positiva, de
  donde sale el elipsoide atrapante. Para Lorenz la búsqueda encuentra la del
  balotario, V = r x² + σ y² + σ(z − 2r)², con los parámetros simbólicos.
* `espectro_lyapunov` (4.5): el teorema "atractor caótico acotado sin
  equilibrios de un flujo 3D disipativo ⟹ espectro (+, 0, −) con suma < 0",
  demostrado paso a paso y contrastado con el espectro calculado (método QR de
  `matematica.espectro_lyapunov`) de Lorenz, de Rössler o del sistema dado.

La función de Lyapunov no se escribe a mano: se plantea V con coeficientes
aᵢ, cᵢ desconocidos, se exige que en V̇ se anulen los términos cúbicos y los
cruzados (lineales en cᵢ una vez fijados los aᵢ) y, entre las soluciones con
aᵢ > 0 y V̇ negativa en los cuadrados, se elige la de forma más simple.
"""

from __future__ import annotations

import itertools
import math

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from matematica import MetodoNoAplicable
from matematica.analisis_estabilidad import describir_conjunto
from matematica.desarrollo import Desarrollo, L, suma
from matematica.espectro_lyapunov import espectro_flujo

TEMA = "Tema 4 · Sistemas dinámicos caóticos"


def _nombre_vector(estados):
    return r"\mathbf{f}(" + ",".join(L(s) for s in estados) + ")"


def _divergencia(campo, estados):
    return sp.simplify(sum(sp.diff(e, v) for e, v in zip(campo, estados)))


def _sustituir(expresion, valores):
    return sp.sympify(expresion).subs(valores)


# ===========================================================================
# 4.4 · Disipatividad y región atrapante
# ===========================================================================

def identificar_disipatividad(problema):
    if problema.tipo != "edo" or not problema.autonomo or problema.dimension not in (2, 3):
        return None
    if "disipatividad" not in problema.pedidos:
        return None
    return {}


def _candidatos(campo, estados):
    """Valores para los coeficientes aᵢ: 1, los parámetros, o los coeficientes del campo."""
    parametros = sorted({s for e in campo for s in sp.sympify(e).free_symbols} - set(estados), key=str)
    if parametros:
        return [sp.Integer(1), *parametros][:5]
    numeros = set()
    for e in campo:
        for termino in sp.Add.make_args(sp.expand(e)):
            coeficiente = abs(termino.as_coeff_Mul()[0])
            if coeficiente not in (0, 1) and coeficiente.is_Rational:
                numeros.add(coeficiente)
    return [sp.Integer(1), *sorted(numeros)[:3]]


def buscar_funcion_lyapunov(campo, estados):
    """V = Σ aᵢ(xᵢ − cᵢ)² con V̇ = −k(Q − K), Q = Σ qᵢ(xᵢ − eᵢ)² definida positiva, o None."""
    n = len(estados)
    c = sp.symbols(f"c1:{n + 1}")
    mejores = []
    for combo in itertools.product(_candidatos(campo, estados), repeat=n):
        medio = sum(ai * (xi - ci) * fi for ai, xi, ci, fi in zip(combo, estados, c, campo))
        try:
            polinomio = sp.Poly(sp.expand(medio), *estados)
        except sp.PolynomialError:
            return None                      # campo no polinómico: el método no aplica
        cruzados = [coef for monomio, coef in polinomio.terms()
                    if sum(monomio) >= 3 or (sum(monomio) == 2 and max(monomio) == 1)]
        solucion = sp.solve(cruzados, c, dict=True) if cruzados else [{}]
        if not solucion:
            continue
        solucion = solucion[0]
        if any(sp.simplify(e.subs(solucion)) != 0 for e in cruzados):
            continue
        centros = [sp.simplify(ci.subs(solucion)).subs({cj: 0 for cj in c}) for ci in c]
        mitad = sp.expand(medio.subs(dict(zip(c, centros))))
        A = [mitad.coeff(xi, 2) for xi in estados]
        if not all(sp.simplify(Ai).is_negative for Ai in A):
            continue
        cero = {xi: 0 for xi in estados}
        B = [mitad.coeff(xi, 1).subs(cero) for xi in estados]
        constante = mitad.subs(cero)
        e = [sp.simplify(-Bi / (2 * Ai)) for Ai, Bi in zip(A, B)]
        q = [sp.simplify(-2 * Ai) for Ai in A]
        K = sp.simplify(2 * (constante - sum(Bi ** 2 / (4 * Ai) for Ai, Bi in zip(A, B))))
        comun = sp.gcd_list(q)
        qt = [sp.simplify(qi / comun) for qi in q]
        Kt = sp.simplify(K / comun)
        V = sum(ai * (xi - ci) ** 2 for ai, xi, ci in zip(combo, estados, centros))
        Q = sum(qi * (xi - ei) ** 2 for qi, xi, ei in zip(qt, estados, e))
        puntaje = (sp.count_ops(V) + sp.count_ops(Q) + sp.count_ops(Kt), -sp.count_ops(comun))
        mejores.append((puntaje, {"a": list(combo), "c": centros, "medio": medio.subs(dict(zip(c, centros))),
                                  "mitad": mitad, "q": qt, "e": e, "comun": comun, "K": Kt, "V": V, "Q": Q}))
    if not mejores:
        return None
    mejores.sort(key=lambda t: t[0])
    return mejores[0][1]


def _desplazada(x, centro):
    """LaTeX de x − c en ese orden (sympy escribiría −2r + z)."""
    centro = sp.sympify(centro)
    if centro == 0:
        return L(x)
    if centro.could_extract_minus_sign():
        return f"{L(x)} + {L(-centro)}"
    return f"{L(x)} - {L(centro) if not isinstance(centro, sp.Add) else '(' + L(centro) + ')'}"


def _suma_de_cuadrados(coeficientes, estados, centros):
    """a₁(x − c₁)² + a₂(y − c₂)² + ... en el orden de las variables."""
    terminos = []
    for a, x, c in zip(coeficientes, estados, centros):
        factor = f"{L(x)}^{{2}}" if sp.sympify(c) == 0 else rf"\left({_desplazada(x, c)}\right)^{{2}}"
        terminos.append((a, factor))
    return suma(*terminos)


_GRIEGAS = {"sigma": "σ", "rho": "ρ", "beta": "β", "gamma": "γ", "mu": "μ", "delta": "δ", "omega": "ω"}


def _texto(expresion) -> str:
    """Texto plano con letras griegas: −(σ + 1 + b) en lugar de -b - sigma - 1."""
    expresion = sp.sympify(expresion)
    if isinstance(expresion, sp.Add) and expresion.could_extract_minus_sign():
        texto = f"−({sp.sstr(-expresion)})"
    else:
        texto = sp.sstr(expresion)
    for nombre, letra in _GRIEGAS.items():
        texto = texto.replace(nombre, letra)
    return texto.replace("*", "·")


def _latex_signo(expresion) -> str:
    """−(σ + 1 + b) en LaTeX, agrupado como lo escribe el balotario."""
    expresion = sp.sympify(expresion)
    if isinstance(expresion, sp.Add) and expresion.could_extract_minus_sign():
        return rf"-\left({L(-expresion)}\right)"
    return L(expresion)


def desarrollar_disipatividad(problema, datos=None) -> Desarrollo:
    if identificar_disipatividad(problema) is None:
        raise MetodoNoAplicable("Se esperaba un flujo autónomo de 2 o 3 variables.")
    estados = problema.estados
    campo = problema.campo_simbolico or problema.campo
    valores = problema.valores_simbolicos()
    if problema.parametro is not None:
        valores[problema.parametro] = sp.nsimplify(problema.valor_representativo())
    d = Desarrollo("disipatividad", "Flujo disipativo y región atrapante", TEMA,
                   "Divergencia y teorema de Liouville; función de Lyapunov cuadrática y lema de Gronwall",
                   tratamiento=["analitico", "numerico"], balotario=["4.4"])
    espacio = r"\mathbb{R}^{" + str(len(estados)) + "}"
    tupla = "(" + ",".join(L(s) for s in estados) + ")"

    # --- a) 1. Divergencia -----------------------------------------------------------
    s = d.seccion("divergencia", "a) Divergencia del campo vectorial")
    s.formula(_nombre_vector(estados) + r" = \bigl(" + r",\; ".join(L(e) for e in campo) + r"\bigr)")
    s.formula(r"\nabla \cdot \mathbf{f} = " + " + ".join(
        rf"\frac{{\partial}}{{\partial {L(v)}}}\bigl[{L(e)}\bigr]" for v, e in zip(estados, campo)))
    div = _divergencia(campo, estados)
    constante = not (div.free_symbols & set(estados))
    div_num = sp.nsimplify(_sustituir(div, valores)) if constante else None
    negativa = constante and (div.is_negative or (div_num is not None and div_num.is_negative))
    d.guardar("divergencia", div)
    if constante and div.is_negative:
        s.formula(rf"\nabla \cdot \mathbf{{f}} = {L(div)} < 0 \quad \forall {tupla} \in {espacio}",
                  destacada=True, ref="divergencia")
    elif constante:
        s.formula(rf"\nabla \cdot \mathbf{{f}} = {L(div)}", destacada=True, ref="divergencia")
    else:
        s.formula(rf"\nabla \cdot \mathbf{{f}} = {L(div)}", destacada=True, ref="divergencia")
        div_valores = sp.simplify(_sustituir(div, valores))
        variables = sorted(div_valores.free_symbols & set(estados), key=str)
        s.texto("La divergencia no es constante: depende del punto del espacio de fases.")
        if len(variables) == 1:
            region = sp.solveset(div_valores < 0, variables[0], sp.S.Reals)
            s.formula(rf"\nabla \cdot \mathbf{{f}} = {L(div_valores)} < 0 \iff "
                      rf"{describir_conjunto(region, variables[0])}")

    # --- a) 2. Liouville -------------------------------------------------------------
    s = d.seccion("liouville", "a) Contracción del volumen (teorema de Liouville)")
    s.texto("Sea Ω(t) = φₜ(Ω₀) y V(t) = vol(Ω(t)). Entonces:")
    s.formula(rf"\frac{{dV}}{{dt}} = \int_{{\Omega(t)}} \nabla \cdot \mathbf{{f}}\; d^{len(estados)}x"
              + (rf" = {_latex_signo(div)}\,V" if constante else ""))
    if constante:
        s.formula(rf"V(t) = V(0)\, e^{{{_latex_signo(div)}\,t}}", destacada=True, ref="volumen")
        if valores and div.free_symbols:
            asignados = r",\; ".join(rf"{L(k)} = {L(v)}" for k, v in valores.items() if k in div.free_symbols)
            s.texto("Para los valores del problema:")
            s.formula(rf"{asignados} \implies \nabla\cdot\mathbf{{f}} = {L(div_num)} \approx {float(div_num):.4g}"
                      rf" \implies V(t) = V(0)\,e^{{{float(div_num):.5g}\,t}}")
        if div_num is not None and div_num < 0:
            s.formula(rf"\text{{En una unidad de tiempo: }} \frac{{V(1)}}{{V(0)}} = e^{{{L(div_num)}}} \approx "
                      rf"{L(float(sp.exp(div_num)))}")
            s.texto("El flujo es estrictamente disipativo: todo volumen colapsa exponencialmente a cero, por lo "
                    "que los atractores tienen volumen nulo.")
            d.guardar("contraccion_por_unidad_de_tiempo", float(sp.exp(div_num)))
    campo_num = [sp.nsimplify(_sustituir(e, valores)) for e in campo]
    espectro = None
    if not constante:
        try:
            espectro = espectro_flujo(campo_num, estados, _x0(problema))
            s.formula(rf"\langle \nabla \cdot \mathbf{{f}} \rangle \approx {espectro.divergencia_media:.4f}"
                      r"\quad \text{(media a lo largo de la órbita sobre el atractor)}", destacada=True)
            negativa = espectro.divergencia_media < 0
            d.guardar("divergencia_media", espectro.divergencia_media)
            if negativa:
                s.texto("En promedio la divergencia es negativa: el flujo es disipativo sobre el atractor, "
                        "aunque localmente haya zonas que expanden volumen.")
        except MetodoNoAplicable as exc:
            s.texto(str(exc))
    d.guardar("disipativo", bool(negativa))
    if constante and div_num is not None:
        _validar_liouville(d, campo_num, estados, float(div_num), problema)

    # --- b) Función de Lyapunov y elipsoide -------------------------------------------
    funcion = buscar_funcion_lyapunov(campo, estados) if negativa else None
    if funcion is None:
        if negativa:
            d.seccion("region_atrapante", "b) Región atrapante").texto(
                "No se encontró una función cuadrática V = Σ aᵢ(xᵢ − cᵢ)² cuya derivada a lo largo del "
                "flujo anule los términos cruzados y cúbicos y sea negativa en los cuadrados: con este "
                "método no se puede demostrar que exista un elipsoide atrapante para este sistema.")
            d.advertir("La región atrapante no se demuestra: no se encontró una función de Lyapunov "
                       "cuadrática diagonal para este sistema.")
        _conclusion_disipatividad(d, div, constante, negativa, None)
        return d
    _seccion_lyapunov(d, funcion, campo, estados, valores, problema)
    _conclusion_disipatividad(d, div, constante, negativa, funcion)
    return d


def _x0(problema):
    if problema.ci is not None:
        return tuple(float(sp.N(v)) for v in problema.ci[1])
    return None


def _validar_liouville(d, campo_num, estados, div, problema, tiempo=0.5):
    """det Φ_t = e^{div·t}: se integra la ecuación variacional y se compara."""
    n = len(estados)
    f = sp.lambdify([estados], campo_num, "numpy")
    J = sp.lambdify([estados], sp.Matrix(campo_num).jacobian(estados).tolist(), "numpy")

    def extendido(t, v):
        x = v[:n]
        Phi = v[n:].reshape(n, n)
        return np.concatenate([np.asarray(f(x), dtype=float), (np.asarray(J(x), dtype=float) @ Phi).ravel()])

    x0 = list(_x0(problema) or [1.0] * n)
    sol = solve_ivp(extendido, (0, tiempo), np.concatenate([x0, np.eye(n).ravel()]), method="DOP853",
                    rtol=1e-11, atol=1e-13)
    if not sol.success:
        return
    determinante = float(np.linalg.det(sol.y[n:, -1].reshape(n, n)))
    esperado = math.exp(div * tiempo)
    error = abs(determinante - esperado) / esperado
    d.validar("liouville_numerico", error < 1e-6,
              f"Integrando la ecuación variacional durante t = {tiempo}: det Φ = {determinante:.6e} frente a "
              f"e^(div·t) = {esperado:.6e}.", medida=error, umbral=1e-6, tipo="numerica")


def _seccion_lyapunov(d, funcion, campo, estados, valores, problema):
    a, c, q, e = funcion["a"], funcion["c"], funcion["q"], funcion["e"]
    comun, K, V, Q = funcion["comun"], funcion["K"], funcion["V"], funcion["Q"]
    n = len(estados)
    # --- b) 1. V y su derivada -------------------------------------------------------
    s = d.seccion("lyapunov", "b) Función de Lyapunov cuadrática")
    positivos = sorted({sym for ai in a for sym in sp.sympify(ai).free_symbols}, key=str)
    if positivos:
        s.texto("Se define (con " + ", ".join(_texto(p) for p in positivos) + " > 0):")
    else:
        s.texto("Se define:")
    V_latex = _suma_de_cuadrados(a, estados, c)
    Q_latex = _suma_de_cuadrados(q, estados, e)
    argumentos = ",".join(L(x) for x in estados)
    s.formula(rf"V({argumentos}) = {V_latex},\qquad Q({argumentos}) = {Q_latex}")
    s.texto("Derivando a lo largo del flujo:")
    s.formula(r"\frac{1}{2}\dot{V} = " + suma(*[(ai, rf"\left({_desplazada(xi, ci)}\right)\left({L(fi)}\right)")
                                               for ai, xi, ci, fi in zip(a, estados, c, campo)]))
    sin_cancelar = sp.expand(sum(ai * (xi - ci) * fi for ai, xi, ci, fi in zip(a, estados, c, campo)))
    piezas = [sp.expand(ai * (xi - ci) * fi) for ai, xi, ci, fi in zip(a, estados, c, campo)]
    monomios = {}
    for pieza in piezas:
        for monomio, coef in sp.Poly(pieza, *estados).terms():
            if sum(monomio) >= 3 or (sum(monomio) == 2 and max(monomio) == 1):
                monomios.setdefault(monomio, []).append(coef)
    frases = []
    for monomio, coeficientes in monomios.items():
        nombre = r"\,".join(L(x) + ("^{%d}" % k if k > 1 else "") for x, k in zip(estados, monomio) if k)
        frases.append(rf"\text{{términos }} {nombre}:\; {suma(*coeficientes)} = 0")
    if frases:
        s.texto("Al expandir, los términos cruzados y cúbicos se cancelan:")
        s.formula(r",\qquad ".join(frases))
        s.texto("quedando:")
    mitad = sp.expand(sin_cancelar)
    s.formula(r"\frac{1}{2}\dot{V} = " + L(mitad) + " = " + L(-comun / 2) + r"\left[" + Q_latex + r"\right] + "
              + L(comun * K / 2))
    Vdot = -comun * (sp.Symbol("Q") - K)
    s.formula(rf"\dot{{V}} = -{L(comun)}\left(Q - {L(K)}\right)", destacada=True, ref="derivada_V")
    d.validar("derivada_de_V", sp.simplify(2 * mitad - (-comun * (Q - K))) == 0,
              "V̇ = −k(Q − K) por expansión directa (los términos cruzados y cúbicos se anulan).")
    d.guardar("funcion_lyapunov", V)
    d.guardar("Q", Q)
    d.guardar("derivada_V", Vdot.subs(sp.Symbol("Q"), Q))

    # --- b) 2. Acotación de Q en términos de V -----------------------------------------
    s = d.seccion("acotacion", "b) Acotación de Q en términos de V")
    coef_cota, D = [], sp.Integer(0)
    desigualdades = []
    for xi, ci, ei, qi in zip(estados, c, e, q):
        if sp.simplify(ei - ci) == 0:
            coef_cota.append(qi)
            continue
        coef_cota.append(qi / 2)
        D += qi * (ei - ci) ** 2
        desigualdades.append((xi, ci, ei))
        resto = sp.expand(2 * (xi - ei) ** 2 + 2 * (ei - ci) ** 2 - (xi - ci) ** 2)
        d.validar(f"desigualdad_{xi.name}", sp.simplify(resto - (xi - 2 * ei + ci) ** 2) == 0,
                  f"2({xi.name} − e)² + 2(e − c)² − ({xi.name} − c)² es un cuadrado perfecto, luego ≥ 0.")
    for xi, ci, ei in desigualdades:
        dos = sp.expand(2 * (ei - ci) ** 2)
        uno = sp.expand((ei - ci) ** 2)
        s.formula(rf"\text{{Como }} \left({_desplazada(xi, ci)}\right)^2 \le 2\left({_desplazada(xi, ei)}"
                  rf"\right)^2 + {L(dos)} \implies \left({_desplazada(xi, ei)}\right)^2 \ge "
                  rf"\tfrac{{1}}{{2}}\left({_desplazada(xi, ci)}\right)^2 - {L(uno)}")
    D = sp.simplify(D)
    razones = [sp.simplify(cc / ai) for cc, ai in zip(coef_cota, a)]
    kappa = sp.Min(*razones)
    s.formula(rf"Q \ge {_suma_de_cuadrados(coef_cota, estados, c)} - {L(D)} \ge \kappa V - {L(D)}, \qquad "
              r"\kappa = \min\left\{" + r",\; ".join(L(rz) for rz in razones) + r"\right\} > 0")
    V_estrella = sp.simplify((D + K) / sp.Symbol("kappa"))
    s.texto("Sustituyendo en V̇:")
    s.formula(rf"\dot{{V}} \le -{L(comun)}\left(\kappa V - {L(sp.simplify(D + K))}\right) = "
              rf"-{L(comun)}\kappa\,(V - V^*), \qquad V^* = {L(V_estrella)}", ref="V_estrella")
    d.validar("kappa_positivo", all(sp.sympify(rz).is_positive for rz in razones),
              "Todos los cocientes que definen κ son positivos, así que κ > 0.")

    # --- b) 3. Región atrapante -------------------------------------------------------
    s = d.seccion("region_atrapante", "b) Región atrapante")
    s.texto("Por comparación (lema de Gronwall):")
    s.formula(rf"V(t) - V^* \le \bigl(V(0) - V^*\bigr)\, e^{{-{L(comun)}\kappa\, t}}", destacada=True)
    s.texto("Luego lim sup V(t) ≤ V*. Para todo ε > 0, el elipsoide")
    tupla = "(" + ",".join(L(x) for x in estados) + ")"
    s.formula(rf"E_\varepsilon = \left\{{{tupla} \in \mathbb{{R}}^{{{n}}} : {V_latex} \le V^* + \varepsilon\right\}}",
              destacada=True, ref="elipsoide")
    s.texto("es acotado; toda trayectoria entra en E_ε en tiempo finito (pues V(t) tiende a un valor ≤ V*) y, "
            f"en su frontera V = V* + ε, se cumple V̇ ≤ −{_texto(comun)}κε < 0, de modo que E_ε es "
            "positivamente invariante: una vez dentro, la trayectoria no sale.")
    # Valores del problema.
    kappa_num = float(sp.N(kappa.subs(valores)))
    V_num = float(sp.N(((D + K) / kappa).subs(valores)))
    tasa = float(sp.N((comun * kappa).subs(valores)))
    if valores:
        asignados = r",\; ".join(rf"{L(k)} = {L(v)}" for k, v in valores.items())
        s.formula(rf"{asignados}:\quad \kappa = {kappa_num:.6g},\quad V^* = {V_num:.6g},\quad "
                  rf"\text{{tasa }} {L(comun)}\kappa = {tasa:.6g}")
    d.guardar("kappa", kappa)
    d.guardar("V_estrella", (D + K) / kappa)
    d.guardar("V_estrella_valor", V_num)
    _validar_atrapamiento(d, funcion, campo, estados, valores, V_num, tasa)


def _validar_atrapamiento(d, funcion, campo, estados, valores, V_num, tasa):
    """Trayectorias desde lejos cumplen la cota de Gronwall y terminan dentro del elipsoide."""
    n = len(estados)
    campo_num = [sp.nsimplify(_sustituir(e, valores)) for e in campo]
    f = sp.lambdify([estados], campo_num, "numpy")
    Vf = sp.lambdify([estados], _sustituir(funcion["V"], valores), "numpy")
    escala = math.sqrt(V_num) * 1.5
    iniciales = [[escala * s for s in signos] for signos in itertools.product((1, -1), repeat=n)][:6]
    peor, dentro, trayectorias = 0.0, True, []
    duracion = min(40.0, 12.0 / max(tasa, 1e-3))
    for x0 in iniciales:
        sol = solve_ivp(lambda t, v: np.asarray(f(v), dtype=float), (0, duracion), x0, method="LSODA",
                        rtol=1e-9, atol=1e-9, t_eval=np.linspace(0, duracion, 800))
        if not sol.success:
            continue
        Vs = np.asarray([Vf(sol.y[:, k]) for k in range(sol.y.shape[1])], dtype=float)
        cota = V_num + (Vs[0] - V_num) * np.exp(-tasa * sol.t)
        peor = max(peor, float(np.max((Vs - cota) / max(Vs[0], V_num))))
        dentro = dentro and Vs[-1] <= 1.01 * V_num
        trayectorias.append((sol.t, Vs, sol.y))
    if not trayectorias:
        return
    d.validar("cota_de_gronwall", peor < 1e-6,
              f"{len(trayectorias)} trayectorias que parten fuera del elipsoide cumplen V(t) − V* ≤ "
              "(V(0) − V*)e^(−kκt) en todos los instantes.", medida=max(peor, 0.0), umbral=1e-6, tipo="numerica")
    d.validar("terminan_en_el_elipsoide", dentro,
              f"Todas terminan con V ≤ 1.01·V* (V* = {V_num:.4g}).", tipo="numerica")
    capas = []
    for i, (t, Vs, _) in enumerate(trayectorias):
        capas.append({"tipo": "linea", "rol": f"serie:{i}", "nombre": f"V(t), trayectoria {i + 1}",
                      "x": t.tolist(), "y": Vs.tolist()})
    capas.append({"tipo": "linea", "rol": "frontera", "nombre": "V*", "x": [0, float(trayectorias[0][0][-1])],
                  "y": [V_num, V_num]})
    d.grafica({"clave": "V_en_el_tiempo", "titulo": "V(t) a lo largo de trayectorias que parten lejos",
               "ejes": {"x": "t", "y": "V"}, "escala_y": "log", "capas": capas})
    if n == 3:
        a, c = funcion["a"], funcion["c"]
        a_num = [float(sp.N(_sustituir(ai, valores))) for ai in a]
        c_num = [float(sp.N(_sustituir(ci, valores))) for ci in c]
        angulos = np.linspace(0, 2 * math.pi, 300)
        ex = c_num[0] + np.sqrt(V_num / a_num[0]) * np.cos(angulos)
        ez = c_num[2] + np.sqrt(V_num / a_num[2]) * np.sin(angulos)
        t, Vs, y = trayectorias[0]
        d.grafica({"clave": "elipsoide", "titulo": f"Corte del elipsoide V = V* en {estados[1].name} = "
                                                  f"{c_num[1]:g} y una trayectoria",
                   "ejes": {"x": estados[0].name, "y": estados[2].name},
                   "capas": [{"tipo": "linea", "rol": "frontera", "nombre": "V = V*", "x": ex.tolist(),
                              "y": ez.tolist()},
                             {"tipo": "linea", "rol": "trayectoria", "nombre": "Trayectoria",
                              "x": y[0].tolist(), "y": y[2].tolist()}]})


def _conclusion_disipatividad(d, div, constante, negativa, funcion):
    if constante and negativa:
        texto = (f"El flujo es globalmente disipativo (∇·f = {_texto(div)} < 0): todo volumen se contrae "
                 "exponencialmente y los atractores tienen volumen nulo.")
    elif negativa:
        texto = ("La divergencia cambia de signo, pero su media sobre el atractor es negativa: el flujo es "
                 "disipativo en promedio.")
    else:
        texto = "El flujo no contrae volumen: no es disipativo."
    if funcion is not None:
        texto += (" Además existe un elipsoide acotado que atrapa todas las órbitas, así que el conjunto "
                  "ω-límite de cualquier trayectoria es compacto: un atractor extraño de dimensión fractal "
                  "entre 2 y 3 es compatible con ambas propiedades.")
    d.concluir(texto)


# ===========================================================================
# 4.5 · Espectro de Lyapunov de un flujo caótico tridimensional
# ===========================================================================

def identificar_espectro(problema):
    if "espectro_lyapunov" not in problema.pedidos:
        return None
    if problema.tipo == "teorico":
        return {}
    if problema.tipo == "edo" and problema.autonomo and problema.dimension == 3:
        return {}
    return None


def _sistemas_de_ejemplo():
    """Lorenz y Rössler canónicos, como los cita el balotario."""
    from matematica.problema import construir_problema
    from matematica.sistemas_conocidos import SISTEMAS
    salida = []
    for clave in ("lorenz", "rossler"):
        sistema = SISTEMAS[clave]
        p = construir_problema(ecuaciones=sistema["ecuaciones"], variables_estado=sistema["variables_estado"],
                               parametros=sistema["parametros"])
        salida.append((sistema["nombre"], p.campo, p.estados, None))
    return salida


def desarrollar_espectro(problema, datos=None) -> Desarrollo:
    if identificar_espectro(problema) is None:
        raise MetodoNoAplicable("Se esperaba un flujo autónomo tridimensional o el enunciado del teorema.")
    d = Desarrollo("espectro_lyapunov", "Espectro de Lyapunov de un flujo 3D disipativo", TEMA,
                   "Ecuación variacional, exponente nulo de la dirección del flujo, fórmula de Liouville "
                   "y método QR para el contraste numérico", tratamiento=["analitico", "numerico"],
                   balotario=["4.5"])
    if problema.tipo == "edo":
        sistemas = [("el sistema dado", problema.campo_con(), problema.estados, _x0(problema))]
    else:
        sistemas = _sistemas_de_ejemplo()
    espectros = []
    for nombre, campo, estados, x0 in sistemas:
        espectros.append((nombre, campo, estados, espectro_flujo(campo, estados, x0)))

    # --- 1. Hipótesis y definiciones ------------------------------------------------------
    s = d.seccion("hipotesis", "Hipótesis y definiciones")
    s.texto("Sea A ⊂ ℝ³ el atractor: compacto, invariante, sin equilibrios. Sea Φₜ(x₀) la matriz "
            "fundamental de la ecuación variacional:")
    s.formula(r"\dot{\boldsymbol\delta} = D\mathbf{f}(\mathbf{x}(t))\,\boldsymbol\delta, \qquad "
              r"\lambda_i = \lim_{t \to \infty} \frac{1}{t} \ln \|\Phi_t \mathbf{v}_i\|, \qquad "
              r"\lambda_1 \ge \lambda_2 \ge \lambda_3")
    s.texto("Los exponentes existen para casi todo punto respecto a la medida invariante (teorema "
            "multiplicativo ergódico de Oseledets). Caótico significa dependencia sensible a las condiciones "
            "iniciales: λ₁ > 0.")

    # --- 2. Exponente nulo ----------------------------------------------------------------
    s = d.seccion("exponente_nulo", "Existe un exponente nulo (dirección del flujo)")
    s.texto("Sea x(t) una trayectoria en A y δ(t) = f(x(t)). Entonces:")
    s.formula(r"\dot{\boldsymbol\delta} = D\mathbf{f}(\mathbf{x}(t))\,\dot{\mathbf{x}}(t) = "
              r"D\mathbf{f}(\mathbf{x}(t))\,\boldsymbol\delta")
    nombre0, campo0, estados0, esp0 = espectros[0]
    t = sp.Symbol("t", real=True)
    funciones = [sp.Function(v.name)(t) for v in estados0]
    cambio = dict(zip(estados0, funciones))
    f_t = [sp.sympify(e).subs(cambio) for e in campo0]
    derivada = [sp.diff(fi, t).subs({sp.Derivative(fn, t): fe for fn, fe in zip(funciones, f_t)}) for fi in f_t]
    J_f = (sp.Matrix(campo0).jacobian(estados0) * sp.Matrix(campo0)).subs(cambio)
    d.validar("f_resuelve_la_variacional", all(sp.simplify(a - b) == 0 for a, b in zip(derivada, J_f)),
              f"Para {nombre0}: d/dt f(x(t)) = Df(x(t))·f(x(t)) componente a componente (sympy).")
    s.texto("Es decir, f(x(t)) es solución de la ecuación variacional. Como A es compacto y no contiene "
            "equilibrios, f no se anula en A:")
    s.formula(r"0 < m \le \|\mathbf{f}(\mathbf{x})\| \le M < \infty \quad \forall \mathbf{x} \in A")
    s.formula(r"\lim_{t \to \infty} \frac{1}{t}\ln\|\boldsymbol\delta(t)\| = 0 \implies "
              r"\text{uno de los exponentes } \lambda_i \text{ es exactamente } 0", destacada=True)
    s.texto(f"En la órbita calculada de {nombre0}: m ≈ {esp0.norma_minima:.3g} y M ≈ {esp0.norma_maxima:.3g}.")

    # --- 3. Suma = divergencia media ------------------------------------------------------
    s = d.seccion("suma", "Suma de exponentes = divergencia media")
    s.texto("Por la fórmula de Liouville:")
    s.formula(r"\det \Phi_t = \exp\left(\int_0^t \nabla\cdot\mathbf{f}(\mathbf{x}(s))\,ds\right) \implies "
              r"\lambda_1 + \lambda_2 + \lambda_3 = \lim_{t\to\infty}\frac{1}{t}\ln|\det\Phi_t| = "
              r"\left\langle \nabla \cdot \mathbf{f} \right\rangle")
    s.texto("Para un flujo disipativo, ⟨∇·f⟩ < 0:")
    s.formula(r"\lambda_1 + \lambda_2 + \lambda_3 < 0", destacada=True)

    # --- 4. Ubicación del exponente nulo -------------------------------------------------
    s = d.seccion("ubicacion", "Ubicación del exponente nulo")
    s.texto("Se sabe que λ₁ > 0 (caos) y que algún exponente es 0. Hay tres posibilidades: λ₁ = 0 contradice "
            "λ₁ > 0; λ₃ = 0 obliga a λ₁ ≥ λ₂ ≥ 0 y la suma sería ≥ λ₁ > 0, contra Σλᵢ < 0; queda λ₂ = 0, "
            "la única compatible.")
    s.formula(r"\lambda_1 > 0, \qquad \lambda_2 = 0", destacada=True)

    # --- 5. Signo de λ₃ ---------------------------------------------------------------------
    s = d.seccion("signo_lambda3", "Signo de λ₃")
    s.formula(r"\lambda_3 = \underbrace{(\lambda_1 + \lambda_2 + \lambda_3)}_{<0} - \lambda_1 - \lambda_2 "
              r"< -\lambda_1 < 0")
    s.formula(r"\lambda_3 < -\lambda_1 < 0", destacada=True)

    # --- 6. Necesidad de λ₁ > 0 ---------------------------------------------------------
    s = d.seccion("necesidad", "Necesidad de λ₁ > 0 en la caracterización")
    s.texto("Si en cambio λ₁ ≤ 0, el paso 2 fuerza λ₁ = λ₂ = 0 y λ₃ < 0: no hay expansión exponencial, y los "
            "atractores acotados sin equilibrios son órbitas periódicas o toros cuasiperiódicos, no caóticos.")

    # --- Comprobación numérica -----------------------------------------------------------
    s = d.seccion("comprobacion", "Comprobación numérica del espectro (método QR)")
    filas, resumen = [], []
    for nombre, campo, estados, esp in espectros:
        l1, l2, l3 = esp.exponentes
        e1, e2, e3 = esp.errores
        filas.append([nombre, f"{l1:+.4f} ± {e1:.4f}", f"{l2:+.4f} ± {e2:.4f}", f"{l3:+.4f} ± {e3:.4f}",
                      f"{esp.suma:.4f}", f"{esp.divergencia_media:.4f}"])
        tolerancia_neutro = max(5 * e2, 0.02)
        caotico = l1 > max(5 * e1, 0.01)
        # Si la órbita cae en un equilibrio, f(x(t)) → 0 y el argumento del
        # exponente nulo no aplica: es justo la hipótesis "sin equilibrios".
        en_equilibrio = esp.norma_minima < 1e-6 * max(esp.norma_maxima, 1.0)
        d.validar(f"suma_igual_divergencia ({nombre})",
                  abs(esp.suma - esp.divergencia_media) < 1e-3 * max(1.0, abs(esp.divergencia_media)),
                  f"{nombre}: λ₁ + λ₂ + λ₃ = {esp.suma:.5f} y ⟨∇·f⟩ = {esp.divergencia_media:.5f} sobre la misma "
                  "órbita.", medida=abs(esp.suma - esp.divergencia_media), tipo="numerica")
        if not en_equilibrio:
            neutro = min(esp.exponentes, key=abs)
            d.validar(f"exponente_nulo ({nombre})", abs(neutro) < tolerancia_neutro,
                      f"{nombre}: hay un exponente compatible con 0 ({neutro:+.4f}), el de la dirección del flujo.",
                      medida=abs(neutro), umbral=tolerancia_neutro, tipo="numerica")
        if caotico:
            d.validar(f"lambda3_menor_que_menos_lambda1 ({nombre})", l3 < -l1,
                      f"{nombre}: λ₃ = {l3:.4f} < −λ₁ = {-l1:.4f}.", tipo="numerica")
        resumen.append((nombre, esp, caotico, en_equilibrio))
        d.guardar("espectro" if len(espectros) == 1 else f"espectro_{len(resumen)}",
                  {"sistema": nombre, "exponentes": esp.exponentes, "errores": esp.errores,
                   "suma": esp.suma, "divergencia_media": esp.divergencia_media})
    s.tabla(["Sistema", "λ₁", "λ₂", "λ₃", "Σλᵢ", "⟨∇·f⟩"], filas)
    s.texto(f"Integración RK4 de la órbita y de la ecuación variacional, reortonormalizando cada 10 pasos; "
            f"el ± es el error estándar entre {10} bloques de la misma órbita.")
    for i, (nombre, campo, estados, esp) in enumerate(espectros):
        d.grafica({"clave": f"convergencia_espectro_{i + 1}",
                   "titulo": f"Convergencia de los exponentes: {nombre}",
                   "ejes": {"x": "t", "y": "λᵢ(t)"},
                   "capas": [{"tipo": "linea", "rol": f"serie:{k}", "nombre": f"λ{k + 1}(t)",
                              "x": esp.historia_t, "y": [fila[k] for fila in esp.historia]}
                             for k in range(3)]})

    # --- Conclusión -------------------------------------------------------------------------
    ejemplos = ", ".join(f"{nombre} ({', '.join(f'{v:+.3f}' for v in esp.exponentes)})"
                         for nombre, esp, caotico, _ in resumen if caotico)
    if ejemplos:
        d.concluir("Todo atractor caótico acotado, sin equilibrios, de un flujo disipativo tridimensional tiene "
                   "espectro (+, 0, −) con λ₃ < −λ₁: una dirección expansiva (estiramiento), una neutra (a lo "
                   "largo del flujo) y una contractiva más intensa que la expansión (la disipación). Es lo que "
                   f"se calcula en {ejemplos}.")
    for nombre, esp, caotico, en_equilibrio in resumen:
        if en_equilibrio:
            d.concluir(f"En {nombre} la órbita converge a un equilibrio (λ₁ = {esp.exponentes[0]:.4f}): el atractor "
                       "contiene un punto donde f = 0, así que no se cumple la hipótesis del teorema y no hay "
                       "exponente nulo.")
        elif not caotico:
            d.concluir(f"En {nombre} λ₁ = {esp.exponentes[0]:.4f} no es positivo: la órbita no es caótica; su "
                       "espectro es el de un ciclo o un toro (con el exponente nulo del flujo), fuera de la "
                       "hipótesis de caos del teorema.")
    if any(nombre.startswith("sistema de Lorenz") for nombre, *_ in resumen):
        d.concluir("En Lorenz hay equilibrios en la clausura del atractor, pero el mismo espectro se obtiene para "
                   "casi toda trayectoria.")
    return d
