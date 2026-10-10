"""Atractores extraños y geometría fractal: el Tema 5 del balotario (5.1 a 5.5).

Cinco familias, cada una con el procedimiento del balotario:

* `dimension_fractal` (5.1): dimensión de caja de un conjunto autosemejante
  (el conjunto ternario de Cantor y sus parientes) por conteo exacto en las
  escalas sⁿ, paso al límite y ecuación de autosemejanza N·s^D = 1;
* `herradura` (5.2): el modelo lineal de la herradura de Smale, su conjunto
  invariante Cantor × Cantor y la conjugación con el desplazamiento de dos
  símbolos (se cuentan de verdad los 2ⁿ puntos de periodo n);
* `mapa_2d` (5.3): jacobiano y determinante de un mapa del plano, contracción
  de áreas, inverso explícito comprobado por composición, puntos fijos y
  exponentes de Lyapunov (Hénon);
* `seccion_poincare` (5.4): reducción de un flujo 3D a un mapa de retorno
  unidimensional por una sección transversal (Rössler);
* `kaplan_yorke` (5.5): dimensión de Lyapunov a partir del espectro, con la
  suma de exponentes contrastada contra la divergencia media del sistema.

Las comprobaciones son de verdad: el conteo de cajas se hace sobre el conjunto
construido, los puntos periódicos de la herradura se resuelven uno por uno, el
inverso de Hénon se compone con el mapa, y la sección de Poincaré se obtiene
integrando el flujo con detección de eventos.
"""

from __future__ import annotations

import itertools
import math
import re

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from matematica import DatoInvalido, MetodoNoAplicable
from matematica.analisis_estabilidad import describir_conjunto
from matematica.desarrollo import Desarrollo, F, L
from matematica.espectro_lyapunov import espectro_flujo, espectro_mapa
from matematica.problema import exacto

TEMA = "Tema 5 · Atractores extraños y geometría fractal"


def _dato(datos, *claves):
    for clave in claves:
        if datos.get(clave) is not None:
            return datos[clave]
    return None


def _ajuste_pendiente(xs, ys):
    pendiente, ordenada = np.polyfit(np.asarray(xs, float), np.asarray(ys, float), 1)
    return float(pendiente), float(ordenada)


# ===========================================================================
# 5.1 · Dimensión de caja de un conjunto autosemejante
# ===========================================================================

#: Conjuntos con nombre: copias N, razón s, dimensión del espacio que los
#: contiene y, para los del plano o el espacio, el sistema de funciones
#: iteradas con que se construyen (para el conteo de cajas numérico).
FRACTALES = {
    "alfombra": {"nombre": "alfombra de Sierpinski", "copias": 8, "razon": sp.Rational(1, 3), "ambiente": 2,
                 "palabras": ("alfombra", "carpet")},
    "menger": {"nombre": "esponja de Menger", "copias": 20, "razon": sp.Rational(1, 3), "ambiente": 3,
               "palabras": ("menger",)},
    "sierpinski": {"nombre": "triángulo de Sierpinski", "copias": 3, "razon": sp.Rational(1, 2), "ambiente": 2,
                   "palabras": ("sierpinski", "sierpinsky")},
    "koch": {"nombre": "curva de Koch", "copias": 4, "razon": sp.Rational(1, 3), "ambiente": 2,
             "palabras": ("koch",)},
    "cantor": {"nombre": "conjunto ternario de Cantor", "copias": 2, "razon": sp.Rational(1, 3), "ambiente": 1,
               "palabras": ("cantor",)},
}


def identificar_dimension_fractal(problema):
    if "dimension_fractal" not in problema.pedidos or problema.tipo != "teorico":
        return None
    return {}


def _conjunto_pedido(problema):
    from matematica.sistemas_conocidos import normalizar
    texto = normalizar(problema.enunciado or "")
    datos = problema.datos or {}
    copias, razon = _dato(datos, "copias", "N", "n_copias"), _dato(datos, "razon", "escala", "s")
    # "3 copias", "razón 1/3", "escala 0.25": las cifras también pueden venir escritas.
    if copias is None:
        leido = re.search(r"(\d+)\s+(?:copias|piezas|partes)", texto)
        copias = int(leido.group(1)) if leido else None
    if razon is None:
        leido = re.search(r"(?:razon|escala|factor)(?: de semejanza)?\s*(?:de\s*|=\s*|s\s*=\s*)?"
                          r"(\d+\s*/\s*\d+|\d*[.,]\d+)", texto)
        if leido:
            cifra = leido.group(1).replace(",", ".").replace(" ", "")
            razon = (float(cifra.split("/")[0]) / float(cifra.split("/")[1])) if "/" in cifra else float(cifra)
    for clave, conjunto in FRACTALES.items():
        if any(p in texto for p in conjunto["palabras"]):
            if copias is None and razon is None:
                return clave, dict(conjunto)
            break
    if copias is None and razon is None:
        if re.search(r"autosemejan|copias|razon de semejanza", texto):
            raise DatoInvalido("Para un conjunto autosemejante hacen falta dos cifras: cuántas copias (N) lo "
                               "forman y a qué escala (razón s, entre 0 y 1).")
        return "cantor", dict(FRACTALES["cantor"])
    if copias is None or razon is None:
        falta = "a qué escala está cada copia (razón s, entre 0 y 1)" if razon is None else \
            "cuántas copias (N) lo forman"
        raise DatoInvalido(f"Para un conjunto autosemejante hacen falta dos cifras; falta {falta}.")
    if float(copias) != int(float(copias)) or int(float(copias)) < 2:
        raise DatoInvalido(f"El número de copias debe ser un entero ≥ 2; llegó N = {copias}.")
    if not 0 < float(razon) < 1:
        raise DatoInvalido(f"La razón de semejanza debe estar entre 0 y 1 (cada copia es más pequeña que el "
                           f"conjunto); llegó s = {razon}.")
    N, s = int(float(copias)), exacto(float(razon))
    ambiente = next((dim for dim in (1, 2, 3) if N * float(s) ** dim <= 1 + 1e-12), None)
    if ambiente is None:
        raise DatoInvalido(f"{N} copias a escala {sp.sstr(s)} no caben sin solaparse en un espacio de dimensión "
                           f"≤ 3: la dimensión de semejanza ln N/ln(1/s) = {math.log(N) / math.log(1 / float(s)):.3f} "
                           "supera 3.")
    return "autosemejante", {"nombre": f"conjunto autosemejante de {N} copias a escala {sp.sstr(s)}",
                             "copias": N, "razon": s, "ambiente": ambiente, "palabras": ()}


def _cantor_intervalos(N, s, niveles):
    """Extremos izquierdos de los Nⁿ intervalos de Cₙ (copias equiespaciadas en [0, 1])."""
    s = float(s)
    paso = (1 - s) / (N - 1)
    izquierdos = np.array([0.0])
    longitud = 1.0
    for _ in range(niveles):
        izquierdos = np.concatenate([paso * i + s * izquierdos for i in range(N)])
        longitud *= s
    return np.sort(izquierdos), longitud


def _conteo_1d(izquierdos, longitud, epsilon):
    """N(ε): cajas [kε, (k+1)ε) que tocan algún intervalo [a, a + longitud]."""
    # La holgura absorbe el redondeo de un extremo que cae justo en el borde de una caja.
    inicio = np.floor(izquierdos / epsilon + 1e-6).astype(np.int64)
    fin = np.floor((izquierdos + longitud) / epsilon - 1e-6).astype(np.int64)
    cajas = set()
    for a, b in zip(inicio, fin):
        cajas.update(range(int(a), int(b) + 1))
    return len(cajas)


def _ifs(clave):
    """Mapas afines (A, b) del conjunto con nombre en el plano o el espacio."""
    if clave == "sierpinski":
        vertices = [(0, 0), (1, 0), (0.5, math.sqrt(3) / 2)]
        return [(np.eye(2) / 2, np.array(v) / 2) for v in vertices]
    if clave == "alfombra":
        return [(np.eye(2) / 3, np.array([i, j]) / 3) for i in range(3) for j in range(3) if (i, j) != (1, 1)]
    if clave == "menger":
        return [(np.eye(3) / 3, np.array([i, j, k]) / 3) for i in range(3) for j in range(3) for k in range(3)
                if [i, j, k].count(1) <= 1]
    if clave == "koch":
        def similitud(angulo, desplazamiento):
            c, s = math.cos(angulo), math.sin(angulo)
            return np.array([[c, -s], [s, c]]) / 3, np.array(desplazamiento)
        return [similitud(0, (0, 0)), similitud(math.pi / 3, (1 / 3, 0)),
                similitud(-math.pi / 3, (0.5, math.sqrt(3) / 6)), similitud(0, (2 / 3, 0))]
    return None


def _juego_del_caos(mapas, puntos=120_000, semilla=7):
    generador = np.random.default_rng(semilla)
    dimension = mapas[0][0].shape[0]
    actual = np.zeros(dimension)
    salida = np.empty((puntos, dimension))
    elecciones = generador.integers(0, len(mapas), size=puntos + 50)
    for k, i in enumerate(elecciones):
        A, b = mapas[i]
        actual = A @ actual + b
        if k >= 50:
            salida[k - 50] = actual
    return salida


def _conteo_nd(puntos, epsilon):
    return len({tuple(fila) for fila in np.floor(puntos / epsilon).astype(np.int64)})


def desarrollar_dimension_fractal(problema, datos=None) -> Desarrollo:
    if identificar_dimension_fractal(problema) is None:
        raise MetodoNoAplicable("Se esperaba la pregunta por la dimensión de un conjunto autosemejante.")
    clave, conjunto = _conjunto_pedido(problema)
    N, s, ambiente, nombre = conjunto["copias"], sp.nsimplify(conjunto["razon"]), conjunto["ambiente"], conjunto["nombre"]
    d = Desarrollo("dimension_fractal", "Dimensión de caja de un conjunto autosemejante", TEMA,
                   "Conteo exacto de cajas en las escalas sⁿ, paso al límite y ecuación de autosemejanza",
                   tratamiento=["analitico", "numerico"], balotario=["5.1"])
    n = sp.Symbol("n", positive=True, integer=True)
    D_exacta = sp.log(N) / sp.log(1 / s)
    d.guardar("conjunto", nombre)
    d.guardar("copias", N)
    d.guardar("razon", s)

    # --- 1. Construcción --------------------------------------------------------------
    sec = d.seccion("construccion", f"Construcción: {nombre}")
    if ambiente == 1:
        paso = (1 - s) / (N - 1)
        copias = r" \;\cup\; ".join(
            (L(s) + "C_n" if i == 0 else rf"\left({L(paso * i)} + {L(s)}C_n\right)") for i in range(N))
        sec.formula(rf"C_0 = [0, 1], \qquad C_{{n+1}} = {copias}, \qquad C = \bigcap_{{n=0}}^\infty C_n")
        sec.texto(f"Cₙ consta de {N}ⁿ intervalos cerrados disjuntos, cada uno de longitud ({sp.sstr(s)})ⁿ.")
    else:
        sec.texto(f"El conjunto es la unión de {N} copias de sí mismo reducidas por {sp.sstr(s)}: en la etapa n "
                  f"hay {N}ⁿ piezas semejantes a la inicial, de tamaño ({sp.sstr(s)})ⁿ.")

    # --- 2. Definición ----------------------------------------------------------------
    sec = d.seccion("definicion", "Definición de la dimensión de caja")
    sec.formula(r"D_0 = \lim_{\varepsilon \to 0} \frac{\ln N(\varepsilon)}{\ln(1/\varepsilon)}", destacada=True)
    sec.texto("donde N(ε) es el número mínimo de cajas de lado ε necesarias para cubrir el conjunto.")

    # --- 3. Conteo exacto ----------------------------------------------------------------
    sec = d.seccion("conteo", rf"Conteo exacto para $\varepsilon_n = \left({L(s)}\right)^n$")
    sec.texto(f"Las {N}ⁿ piezas de la etapa n cubren el conjunto, y no pueden cubrirse con menos cajas de lado "
              f"({sp.sstr(s)})ⁿ: piezas distintas están separadas y cada caja cubre a lo sumo un número acotado "
              "de ellas, lo que solo cambia la cuenta por un factor constante.")
    cociente = sp.simplify(n * sp.log(N) / (n * sp.log(1 / s)))
    sec.formula(rf"N\left(\left({L(s)}\right)^{{n}}\right) = {N}^{{n}} \implies \frac{{\ln N(\varepsilon_n)}}{{\ln(1/\varepsilon_n)}}"
                rf" = \frac{{n \ln {N}}}{{n \ln {L(1 / s)}}} = {L(cociente)}")

    # --- 4. Paso al límite --------------------------------------------------------------
    sec = d.seccion("limite", "Paso al límite continuo")
    inferior = n * sp.log(N) / ((n + 1) * sp.log(1 / s))
    superior = (n + 1) * sp.log(N) / (n * sp.log(1 / s))
    limite_inf, limite_sup = sp.limit(inferior, n, sp.oo), sp.limit(superior, n, sp.oo)
    sec.texto(f"Para cualquier ε con ({sp.sstr(s)})ⁿ⁺¹ < ε ≤ ({sp.sstr(s)})ⁿ se tiene {N}ⁿ ≤ N(ε) ≤ {N}ⁿ⁺¹ y "
              f"n·ln({sp.sstr(1 / s)}) ≤ ln(1/ε) ≤ (n+1)·ln({sp.sstr(1 / s)}). Entonces:")
    sec.formula(rf"{L(inferior)} \le \frac{{\ln N(\varepsilon)}}{{\ln(1/\varepsilon)}} \le {L(superior)} "
                rf"\xrightarrow{{n \to \infty}} {L(D_exacta)}")
    sec.formula(rf"D_0 = {L(D_exacta)} \approx {float(D_exacta):.4f}", destacada=True, ref="dimension")
    d.validar("limite_de_las_cotas", sp.simplify(limite_inf - D_exacta) == 0 and sp.simplify(limite_sup - D_exacta) == 0,
              "Las dos cotas tienden al mismo límite ln N / ln(1/s) (sympy).")
    d.guardar("dimension", D_exacta)

    # --- 5. Autosemejanza y medida ------------------------------------------------------
    sec = d.seccion("autosemejanza", "Verificación por autosemejanza")
    Dsym = sp.Symbol("D", positive=True)
    solucion = sp.solve(sp.Eq(N * s ** Dsym, 1), Dsym)
    sec.texto(f"El conjunto se compone de {N} copias de sí mismo a escala {sp.sstr(s)}, de modo que:")
    sec.formula(rf"{N}\left({L(s)}\right)^{{D}} = 1 \implies D = {L(solucion[0])}")
    d.validar("ecuacion_de_autosemejanza", len(solucion) == 1 and sp.simplify(solucion[0] - D_exacta) == 0,
              "La ecuación N·s^D = 1 tiene la misma solución que el conteo de cajas.")
    medida = N * s ** ambiente
    sec.formula(rf"\mu_{{{ambiente}}}(C_n) = \left({N} \cdot {L(s ** ambiente)}\right)^n = \left({L(medida)}\right)^n "
                + (r"\xrightarrow{n\to\infty} 0" if medida < 1 else r"= 1"))
    if ambiente == 1 and medida < 1:
        sec.texto("El conjunto tiene longitud nula y, sin embargo, es no numerable y de dimensión D₀ > 0.")
    elif medida < 1:
        sec.texto(f"Tiene medida nula en el espacio de dimensión {ambiente} y, aun así, D₀ > {ambiente - 1}.")
    if ambiente >= 2 and N * s ** (ambiente - 1) > 1:
        sec.texto(f"Su medida de dimensión {ambiente - 1} crece como ({sp.sstr(N * s ** (ambiente - 1))})ⁿ → ∞: "
                  "el objeto es demasiado grande para esa dimensión y demasiado pequeño para la siguiente.")

    # --- 6. Conteo de cajas numérico ------------------------------------------------------
    sec = d.seccion("conteo_numerico", "Construcción gráfica y conteo de cajas")
    escalas, cuentas = [], []
    if ambiente == 1:
        niveles = max(4, int(math.log(2 ** 15) / math.log(N)))
        izquierdos, longitud = _cantor_intervalos(N, s, niveles)
        alineado = all(abs((float((1 - s) / (N - 1)) * i / float(s)) - round(float((1 - s) / (N - 1)) * i / float(s)))
                       < 1e-9 for i in range(N))
        if alineado:
            hasta = min(niveles - 3, 10)
            exactos = [(_conteo_1d(izquierdos, longitud, float(s) ** k), N ** k) for k in range(1, hasta + 1)]
            d.validar("conteo_exacto", all(a == b for a, b in exactos),
                      f"Contando cajas de lado ({sp.sstr(s)})ᵏ sobre C_{niveles}: N = {N}ᵏ exactamente para "
                      f"k = 1..{hasta}.", tipo="numerica")
        for j in range(3, 16):
            epsilon = 2.0 ** (-j)
            if epsilon < longitud * 4:
                break
            escalas.append(epsilon)
            cuentas.append(_conteo_1d(izquierdos, longitud, epsilon))
        _grafica_cantor(d, N, s)
    else:
        mapas = _ifs(clave)
        if mapas is not None:
            puntos = _juego_del_caos(mapas)
            for j in range(2, 8 if ambiente == 2 else 6):
                epsilon = 2.0 ** (-j)
                escalas.append(epsilon)
                cuentas.append(_conteo_nd(puntos, epsilon))
            if ambiente == 2:
                muestra = puntos[:: max(1, len(puntos) // 15000)]
                d.grafica({"clave": "conjunto", "titulo": f"{nombre[0].upper()}{nombre[1:]} (juego del caos)",
                           "ejes": {"x": "x", "y": "y"}, "cuadrada": True,
                           "capas": [{"tipo": "puntos", "rol": "trayectoria", "nombre": nombre,
                                      "x": muestra[:, 0].tolist(), "y": muestra[:, 1].tolist(), "tamano": 2}]})
        else:
            sec.texto("Sin la geometría concreta de las copias no se construye el conjunto: la dimensión sale solo "
                      "de N y s.")
    if len(escalas) >= 4:
        logx = [math.log(1 / e) for e in escalas]
        logy = [math.log(c) for c in cuentas]
        pendiente, ordenada = _ajuste_pendiente(logx, logy)
        tolerancia = 0.03 if ambiente == 1 else 0.06
        sec.formula(rf"\text{{Ajuste de }} \ln N(\varepsilon) \text{{ frente a }} \ln(1/\varepsilon) "
                    rf"\text{{ con }} \varepsilon = 2^{{-j}}:\quad D_0 \approx {pendiente:.4f}")
        d.validar("dimension_por_conteo", abs(pendiente - float(D_exacta)) < tolerancia,
                  f"La pendiente del conteo de cajas sobre el conjunto construido ({pendiente:.4f}) coincide con "
                  f"ln N/ln(1/s) = {float(D_exacta):.4f}.", medida=abs(pendiente - float(D_exacta)),
                  umbral=tolerancia, tipo="numerica")
        d.guardar("dimension_numerica", pendiente)
        d.grafica({"clave": "conteo_de_cajas", "titulo": "Conteo de cajas: ln N(ε) frente a ln(1/ε)",
                   "ejes": {"x": "ln(1/ε)", "y": "ln N(ε)"},
                   "capas": [{"tipo": "puntos", "rol": "numerica", "nombre": "Conteo", "x": logx, "y": logy},
                             {"tipo": "linea", "rol": "referencia", "nombre": f"pendiente {float(D_exacta):.4f}",
                              "x": logx, "y": [ordenada + float(D_exacta) * v for v in logx]}]})
    articulo = "La" if nombre.split()[0] in ("curva", "alfombra", "esponja") else "El"
    d.concluir(f"{articulo} {nombre} tiene dimensión de caja D₀ = {sp.sstr(D_exacta)} ≈ {float(D_exacta):.4f}, "
               f"estrictamente entre {math.floor(float(D_exacta))} y {math.floor(float(D_exacta)) + 1}. Esta dimensión "
               "no entera es la firma de la estructura fractal que se observa en los cortes transversales de los "
               "atractores extraños.")
    return d


def _grafica_cantor(d, N, s, niveles=5):
    capas = []
    for nivel in range(niveles + 1):
        izquierdos, longitud = _cantor_intervalos(N, s, nivel)
        xs, ys = [], []
        for a in izquierdos:
            xs += [float(a), float(a + longitud), None]
            ys += [-nivel, -nivel, None]
        capas.append({"tipo": "linea", "rol": "trayectoria", "nombre": f"C{nivel}", "x": xs, "y": ys})
    d.grafica({"clave": "construccion", "titulo": "Construcción: C₀, C₁, ..., C₅",
               "ejes": {"x": "x", "y": "etapa n (hacia abajo)"}, "capas": capas})


# ===========================================================================
# 5.2 · Herradura de Smale
# ===========================================================================

def identificar_herradura(problema):
    if "herradura" not in problema.pedidos or problema.tipo != "teorico":
        return None
    return {}


def _mapas_herradura(lam, mu):
    """Las dos ramas afines del modelo lineal: (factor x, término x, factor y, término y)."""
    return {0: (lam, 0.0, mu, 0.0), 1: (-lam, 1.0, -mu, mu)}


def _puntos_periodicos(lam, mu, n):
    """Los puntos fijos de fⁿ en Λ, uno por cada palabra de n símbolos."""
    ramas = _mapas_herradura(lam, mu)
    puntos = []
    for palabra in itertools.product((0, 1), repeat=n):
        ax, bx, ay, by = 1.0, 0.0, 1.0, 0.0
        for simbolo in palabra:
            fx, tx, fy, ty = ramas[simbolo]
            ax, bx, ay, by = fx * ax, fx * bx + tx, fy * ay, fy * by + ty
        x, y = bx / (1 - ax), by / (1 - ay)
        # El itinerario: el punto debe recorrer las franjas H_{s₀}, H_{s₁}, ...
        valido, px, py = True, x, y
        for simbolo in palabra:
            en_h0 = -1e-12 <= py <= 1 / mu + 1e-12
            en_h1 = 1 - 1 / mu - 1e-12 <= py <= 1 + 1e-12
            if not (0 - 1e-12 <= px <= 1 + 1e-12) or not (en_h0 if simbolo == 0 else en_h1):
                valido = False
                break
            fx, tx, fy, ty = ramas[simbolo]
            px, py = fx * px + tx, fy * py + ty
        if valido:
            puntos.append((x, y, palabra, abs(ax), abs(ay)))
    return puntos


def desarrollar_herradura(problema, datos=None) -> Desarrollo:
    if identificar_herradura(problema) is None:
        raise MetodoNoAplicable("Se esperaba la pregunta por la herradura de Smale.")
    datos_p = problema.datos or {}
    lam = exacto(float(_dato(datos_p, "contraccion", "lambda", "λ") or 1 / 3))
    mu = exacto(float(_dato(datos_p, "expansion", "mu", "μ") or 3))
    if not 0 < lam < sp.Rational(1, 2):
        raise DatoInvalido(f"La contracción horizontal debe cumplir 0 < λ < 1/2 para que las dos bandas verticales "
                           f"V₀ y V₁ queden separadas; llegó λ = {sp.sstr(lam)}.")
    if not mu > 2:
        raise DatoInvalido(f"La expansión vertical debe cumplir μ > 2 para que el pliegue quede fuera del "
                           f"cuadrado y f(S) ∩ S sean dos bandas; llegó μ = {sp.sstr(mu)}.")
    d = Desarrollo("herradura", "Herradura de Smale y dinámica simbólica", TEMA,
                   "Modelo lineal de la herradura, conjunto invariante de Cantor × Cantor y conjugación con el "
                   "desplazamiento de dos símbolos", tratamiento=["analitico", "numerico"], balotario=["5.2"])
    x, y = sp.symbols("x y", real=True)

    # --- 1. Construcción geométrica ---------------------------------------------------
    s = d.seccion("construccion", "Construcción geométrica del mapa")
    s.texto("Sea S = [0,1]² un cuadrado. El difeomorfismo f actúa en tres etapas: (i) estiramiento vertical "
            f"por μ = {sp.sstr(mu)} > 2 y contracción horizontal por λ = {sp.sstr(lam)} < 1/2; (ii) plegado de "
            "la banda en forma de herradura; (iii) colocación: la herradura se superpone a S de modo que "
            "f(S) ∩ S consta de dos bandas verticales V₀ y V₁ y el pliegue queda fuera de S.")
    s.texto("En el modelo lineal, las franjas horizontales H₀ y H₁ son las que f lleva dentro de S:")
    s.formula(rf"H_0 = [0,1] \times \left[0, {L(1 / mu)}\right],\qquad "
              rf"H_1 = [0,1] \times \left[{L(1 - 1 / mu)}, 1\right]")
    s.formula(rf"f|_{{H_0}}(x, y) = \left({L(lam * x)},\; {L(mu * y)}\right),\qquad "
              rf"f|_{{H_1}}(x, y) = \left({L(1 - lam * x)},\; {L(sp.expand(mu * (1 - y)))}\right)")
    s.formula(rf"f(S) \cap S = V_0 \cup V_1,\qquad V_0 = \left[0, {L(lam)}\right] \times [0,1],\qquad "
              rf"V_1 = \left[{L(1 - lam)}, 1\right] \times [0,1]", destacada=True)
    d.validar("bandas_disjuntas", lam < 1 - lam and 1 / mu < 1 - 1 / mu,
              "λ < 1/2 separa V₀ de V₁ y μ > 2 separa H₀ de H₁.")

    # --- 2. Conjunto invariante ---------------------------------------------------------
    s = d.seccion("invariante", "Construcción del conjunto invariante")
    s.formula(r"\Lambda = \bigcap_{n = -\infty}^{\infty} f^n(S)")
    s.texto(f"Cada iteración hacia adelante corta S en 2ⁿ bandas verticales de ancho λⁿ (la intersección "
            "∩ₙ≥₀ fⁿ(S) es un conjunto de Cantor en horizontal por un intervalo), y cada iteración hacia atrás "
            "corta en 2ⁿ bandas horizontales de altura μ⁻ⁿ. Por tanto:")
    s.formula(r"\Lambda \cong \text{(Conjunto de Cantor)} \times \text{(Conjunto de Cantor)}", destacada=True)
    D = sp.log(2) / sp.log(1 / lam) + sp.log(2) / sp.log(mu)
    D_simple = sp.nsimplify(sp.simplify(D))
    s.formula(rf"D_0(\Lambda) = \frac{{\ln 2}}{{\ln(1/\lambda)}} + \frac{{\ln 2}}{{\ln \mu}} = {L(D_simple)} "
              rf"\approx {float(D):.4f}", ref="dimension")
    area = sp.simplify((2 * lam) * (2 / mu))
    s.formula(rf"\text{{Área de la etapa }} n:\; \left(2\lambda \cdot \tfrac{{2}}{{\mu}}\right)^n = \left({L(area)}\right)^n "
              r"\xrightarrow{n\to\infty} 0")
    s.texto("Λ es un conjunto totalmente disconexo, perfecto y de área nula.")
    d.guardar("dimension", D_simple)

    # --- 3. Conjugación ---------------------------------------------------------------
    s = d.seccion("conjugacion", "Conjugación con el desplazamiento de Bernoulli")
    s.texto("Se codifica cada punto p ∈ Λ por su itinerario:")
    s.formula(r"\phi: \Lambda \to \Sigma_2 = \{0,1\}^{\mathbb{Z}}, \qquad \phi(\mathbf{p}) = (\dots s_{-1}\, s_0\, "
              r"s_1 \dots), \quad s_k = i \iff f^k(\mathbf{p}) \in H_i")
    s.formula(r"\phi \circ f = \sigma \circ \phi, \qquad \sigma(\dots s_{-1} . s_0 s_1 \dots) = "
              r"(\dots s_{-1} s_0 . s_1 \dots)", destacada=True)
    s.texto("φ es un homeomorfismo: f restringido a Λ es topológicamente conjugado al desplazamiento completo en "
            "dos símbolos.")

    # --- 4. Consecuencias --------------------------------------------------------------
    s = d.seccion("consecuencias", "Consecuencias dinámicas (heredadas del desplazamiento)")
    filas = []
    for periodo in range(1, 9):
        puntos = _puntos_periodicos(float(lam), float(mu), periodo)
        minimos = sum(sp.mobius(periodo // k) * 2 ** k for k in sp.divisors(periodo)) // periodo
        silla = all(abs(ax - float(lam) ** periodo) < 1e-9 and abs(ay - float(mu) ** periodo) < 1e-6 * float(mu) ** periodo
                    for _, _, _, ax, ay in puntos)
        filas.append([str(periodo), str(len(puntos)), str(2 ** periodo), str(minimos),
                      f"λⁿ = {float(lam) ** periodo:.3g}, μⁿ = {float(mu) ** periodo:.3g}"])
        d.validar(f"puntos_de_periodo_{periodo}", len(puntos) == 2 ** periodo and silla,
                  f"Resolviendo fⁿ(p) = p por itinerario: {len(puntos)} puntos de periodo {periodo} en Λ "
                  f"(= 2^{periodo}), todos sillas.", tipo="numerica")
    s.tabla(["n", "Puntos fijos de fⁿ hallados", "2ⁿ", "Órbitas de periodo mínimo n", "Autovalores de Dfⁿ"], filas)
    s.texto("Hay 2ⁿ puntos de periodo n (las secuencias periódicas de periodo n): infinitas órbitas periódicas, "
            "densas en Λ (toda secuencia se aproxima por una periódica que coincide en una ventana central "
            "larga) y todas inestables de tipo silla (contracción λ < 1/2, expansión μ > 2). Existe una órbita "
            "densa (una secuencia que contiene todos los bloques finitos), dos secuencias que difieren en un "
            "símbolo lejano se separan en O(1) tras pocas iteraciones (dependencia sensible), y Λ es no "
            "numerable: hay órbitas aperiódicas.")
    s.formula(r"h_{top} = \lim_{n\to\infty} \frac{\ln 2^n}{n} = \ln 2 > 0", destacada=True)
    d.guardar("entropia", sp.log(2))

    # --- 5. Relación con los atractores extraños ------------------------------------------
    s = d.seccion("atractores", "Relación con los atractores extraños")
    s.texto("Λ es un conjunto invariante de tipo silla (de medida cero y no atractor), pero es el esqueleto del "
            "caos en los atractores extraños: por el teorema de Smale–Birkhoff, una intersección transversal de "
            "las variedades estable e inestable de un punto silla implica la existencia de una herradura; en un "
            "sistema disipativo, la clausura de la variedad inestable de ese tejido homoclínico forma el "
            "atractor, que hereda la estructura de Cantor transversal, las órbitas periódicas inestables densas y "
            "la sensibilidad a las condiciones iniciales (como en Hénon y Rössler).")

    # Dimensión del conjunto construido: conteo de cajas de cada factor de Cantor.
    estimaciones = []
    for razon in (float(lam), 1 / float(mu)):
        izquierdos, longitud = _cantor_intervalos(2, sp.nsimplify(razon), 13)
        escalas = [2.0 ** (-j) for j in range(3, 16) if 2.0 ** (-j) > 4 * longitud]
        cuentas = [_conteo_1d(izquierdos, longitud, e) for e in escalas]
        estimaciones.append(_ajuste_pendiente([math.log(1 / e) for e in escalas], [math.log(c) for c in cuentas])[0])
    d.validar("dimension_por_conteo", abs(sum(estimaciones) - float(D)) < 0.05,
              f"El conteo de cajas de los dos factores de Cantor da {estimaciones[0]:.4f} + {estimaciones[1]:.4f} = "
              f"{sum(estimaciones):.4f} ≈ {float(D):.4f}.", medida=abs(sum(estimaciones) - float(D)), umbral=0.05,
              tipo="numerica")
    _grafica_herradura(d, float(lam), float(mu))
    d.concluir("El mecanismo de la herradura (estirar, contraer, plegar y volver a insertar) convierte un cuadrado "
               "en una U que solo reintersecta el cuadrado original en dos bandas. Iterándolo se produce un "
               f"conjunto Cantor × Cantor (dimensión {float(D):.3f}) sobre el que la dinámica es equivalente al "
               "desplazamiento de Bernoulli de dos símbolos: infinitas órbitas periódicas inestables densas (2ⁿ "
               "de periodo n, comprobadas una a una), órbitas aperiódicas, entropía ln 2 y dependencia sensible. "
               "Es el modelo geométrico de la dinámica caótica simbólica en los atractores extraños.")
    return d


def _rectangulo(x0, x1, y0, y1):
    return [x0, x1, x1, x0, x0, None], [y0, y0, y1, y1, y0, None]


def _grafica_herradura(d, lam, mu):
    capas = []
    xs, ys = _rectangulo(0, 1, 0, 1)
    capas.append({"tipo": "linea", "rol": "frontera", "nombre": "S = [0,1]²", "x": xs, "y": ys})
    for nombre, (y0, y1) in (("H₀", (0, 1 / mu)), ("H₁", (1 - 1 / mu, 1))):
        xs, ys = _rectangulo(0, 1, y0, y1)
        capas.append({"tipo": "linea", "rol": "variedad_estable", "nombre": nombre, "x": xs, "y": ys})
    for nombre, (x0, x1) in (("V₀", (0, lam)), ("V₁", (1 - lam, 1))):
        xs, ys = _rectangulo(x0, x1, 0, 1)
        capas.append({"tipo": "linea", "rol": "variedad_inestable", "nombre": nombre, "x": xs, "y": ys})
    puntos = _puntos_periodicos(lam, mu, 8)
    capas.append({"tipo": "puntos", "rol": "orbita", "nombre": "Puntos de periodo 8 (aproximan Λ)",
                  "x": [p[0] for p in puntos], "y": [p[1] for p in puntos], "tamano": 4})
    d.grafica({"clave": "herradura", "titulo": "Franjas H₀, H₁, bandas V₀, V₁ y el conjunto invariante Λ",
               "ejes": {"x": "x", "y": "y"}, "rango": {"x": [-0.05, 1.05], "y": [-0.05, 1.05]}, "cuadrada": True,
               "capas": capas})


# ===========================================================================
# 5.3 · Mapas del plano (Hénon)
# ===========================================================================

def identificar_mapa_2d(problema):
    if problema.tipo != "mapa" or problema.dimension != 2:
        return None
    return {}


def _forma_henon(campo, x, y):
    """(F(x), c) si el mapa es (F(x) + y, c·x): admite la descomposición en tres pasos."""
    f1, f2 = (sp.expand(e) for e in campo)
    c = sp.simplify(f2 / x)
    if c.free_symbols & {x, y} or c == 0:
        return None
    resto = sp.expand(f1 - y)
    if y in resto.free_symbols:
        return None
    return resto, c


def desarrollar_mapa_2d(problema, datos=None) -> Desarrollo:
    if identificar_mapa_2d(problema) is None:
        raise MetodoNoAplicable("Se esperaba un mapa del plano (x, y) ↦ (F₁, F₂).")
    x, y = problema.estados
    campo = problema.campo_simbolico or problema.campo
    valores = problema.valores_simbolicos()
    campo_num = [sp.nsimplify(sp.sympify(e).subs(valores)) for e in campo]
    d = Desarrollo("mapa_2d", "Mapa del plano: contracción de áreas e inverso", TEMA,
                   "Jacobiano y determinante, cambio de variables para las áreas, despeje del inverso y "
                   "exponentes de Lyapunov", tratamiento=["analitico", "numerico"], balotario=["5.3"])
    T = sp.Matrix(campo)

    # --- a) 1. Jacobiana ------------------------------------------------------------------
    s = d.seccion("jacobiana", "a) Matriz jacobiana")
    s.formula(rf"T({L(x)},{L(y)}) = \bigl({L(campo[0])},\; {L(campo[1])}\bigr)")
    J = T.jacobian([x, y])
    s.formula(rf"DT({L(x)},{L(y)}) =", J, destacada=True, ref="jacobiana")
    d.guardar("jacobiana", J)

    # --- a) 2. Determinante -----------------------------------------------------------------
    s = d.seccion("determinante", "a) Determinante")
    det = sp.simplify(J.det())
    s.formula(rf"\det DT = ({L(J[0, 0])})({L(J[1, 1])}) - ({L(J[0, 1])})({L(J[1, 0])}) = {L(det)}")
    constante = not (det.free_symbols & {x, y})
    s.formula(rf"\det DT \equiv {L(det)}" + (r" \quad (\text{constante, independiente de } (x,y))" if constante else ""),
              destacada=True, ref="determinante")
    d.guardar("determinante", det)

    # --- a) 3. Contracción de áreas -----------------------------------------------------
    s = d.seccion("areas", "a) Contracción de áreas")
    s.texto("Para un conjunto Ω del plano, el área de su imagen es |det DT|·Área(Ω) (cambio de variables):")
    espectro = None
    try:
        espectro = espectro_mapa(campo_num, [x, y])
    except MetodoNoAplicable as exc:
        d.advertir(str(exc))
    if constante:
        det_num = sp.nsimplify(det.subs(valores))
        s.formula(rf"\mathrm{{Área}}(T^n(\Omega)) = {L(sp.Abs(det))}^n\,\mathrm{{Área}}(\Omega)")
        if valores:
            s.texto(f"Para {', '.join(f'{k.name} = {sp.sstr(v)}' for k, v in valores.items())}:")
        modulo = abs(det_num)
        if modulo < 1:
            s.formula(rf"|\det DT| = {L(modulo)} < 1 \implies \mathrm{{Área}}(T^n(\Omega)) = \left({L(modulo)}"
                      rf"\right)^n\,\mathrm{{Área}}(\Omega) \xrightarrow{{n\to\infty}} 0", destacada=True)
            s.texto(f"Cada iteración reduce el área al {100 * float(modulo):.4g} % (una contracción del "
                    f"{100 * (1 - float(modulo)):.4g} %)."
                    + (" El signo negativo del determinante indica además que T invierte la orientación."
                       if det_num < 0 else ""))
        elif modulo == 1:
            s.formula(r"|\det DT| = 1 \implies T \text{ conserva el área}", destacada=True)
        else:
            s.formula(rf"|\det DT| = {L(modulo)} > 1 \implies T \text{{ expande áreas}}", destacada=True)
        if det_num != 0:
            s.texto("Como consecuencia, la suma de los exponentes de Lyapunov es:")
            s.formula(rf"\lambda_1 + \lambda_2 = \ln|\det DT| = \ln {L(modulo)} \approx {math.log(float(modulo)):.4f}")
        d.guardar("factor_de_area", modulo)
    if espectro is not None and not all(math.isfinite(v) for v in espectro.exponentes):
        s.texto("La órbita cae en un punto donde det DT = 0: allí se pierde una dirección por completo y el "
                "exponente correspondiente es −∞ (la órbita converge a un punto, no a un atractor extraño).")
        d.guardar("exponentes_lyapunov", espectro.exponentes)
        espectro = None
    if espectro is not None:
        l1, l2 = espectro.exponentes
        s.formula(rf"\text{{Numéricamente (método QR sobre el atractor): }} \lambda_1 \approx {l1:.4f},\quad "
                  rf"\lambda_2 \approx {l2:.4f},\quad \lambda_1 + \lambda_2 \approx {l1 + l2:.4f}")
        d.validar("suma_de_exponentes", abs(espectro.suma - espectro.divergencia_media) < 1e-9 * max(1, abs(l1 + l2)),
                  "La suma de los exponentes medidos coincide con la media de ln|det DT| sobre la órbita.",
                  medida=abs(espectro.suma - espectro.divergencia_media), tipo="numerica")
        if l1 > 0 and l2 < 0:
            DL = 1 + l1 / abs(l2)
            s.formula(rf"D_{{KY}} = 1 + \frac{{\lambda_1}}{{|\lambda_2|}} \approx {DL:.3f}"
                      r"\quad \text{(dimensión de Kaplan-Yorke del atractor)}")
            d.guardar("dimension_kaplan_yorke", DL)
        d.guardar("exponentes_lyapunov", espectro.exponentes)

    # --- b) Inverso -------------------------------------------------------------------------
    Xp, Yp = sp.Symbol(x.name + "'", real=True), sp.Symbol(y.name + "'", real=True)
    inverso = _inverso(d, campo, x, y, Xp, Yp, valores)

    # --- Descomposición geométrica -------------------------------------------------------
    forma = _forma_henon(campo, x, y)
    if forma is not None and inverso is not None:
        F_x, c = forma
        s = d.seccion("descomposicion", "b) Descomposición geométrica (estirar, plegar, contraer)")
        T1 = (x, F_x + y)
        T2 = (c * x, y)
        T3 = (y, x)
        s.formula(rf"T = T_3 \circ T_2 \circ T_1: \quad \begin{{cases}} T_1({L(x)},{L(y)}) = ({L(T1[0])},\; "
                  rf"{L(T1[1])}) & \text{{(pliegue no lineal, área conservada)}} \\ T_2({L(x)},{L(y)}) = "
                  rf"({L(T2[0])},\; {L(T2[1])}) & \text{{(contracción en }} {L(x)} \text{{ por }} |{L(c)}|\text{{)}} \\ "
                  rf"T_3({L(x)},{L(y)}) = ({L(y)},\; {L(x)}) & \text{{(reflexión respecto de }} y = x\text{{)}} "
                  r"\end{cases}")
        paso1 = [T1[0], T1[1]]
        paso2 = [c * paso1[0], paso1[1]]
        paso3 = [paso2[1], paso2[0]]
        d.validar("descomposicion", all(sp.simplify(a - b) == 0 for a, b in zip(paso3, campo)),
                  "T₃∘T₂∘T₁ reproduce T (sympy).")
        s.texto("Esta composición reproduce el mecanismo de la herradura: pliegue, contracción y reubicación.")

    # --- Puntos fijos ---------------------------------------------------------------------
    _puntos_fijos_2d(d, campo, campo_num, x, y, valores)

    # --- Gráfica ---------------------------------------------------------------------------
    if espectro is not None and espectro.orbita:
        orbita = np.asarray(espectro.orbita)
        capas = [{"tipo": "puntos", "rol": "trayectoria", "nombre": "Atractor (20 000 iteraciones)",
                  "x": orbita[:, 0].tolist(), "y": orbita[:, 1].tolist(), "tamano": 2}]
        for i, fijo in enumerate(d.resultados.get("puntos_fijos", []), 1):
            capas.append({"tipo": "puntos", "rol": "equilibrio:inestable" if fijo["tipo"] != "atractor"
                          else "equilibrio:estable", "nombre": f"P{i} ({fijo['tipo']})",
                          "x": [fijo["valor"][0]], "y": [fijo["valor"][1]]})
        d.grafica({"clave": "atractor", "titulo": "Atractor del mapa y puntos fijos",
                   "ejes": {"x": x.name, "y": y.name}, "capas": capas})

    # --- Conclusión ----------------------------------------------------------------------
    texto = f"El mapa tiene determinante jacobiano {'constante ' if constante else ''}{sp.sstr(det)}"
    if constante and "factor_de_area" in d.resultados:
        modulo = d.resultados["factor_de_area"]
        texto += f": {'contrae' if modulo < 1 else 'conserva' if modulo == 1 else 'expande'} áreas por un factor " \
                 f"{sp.sstr(modulo)} en cada paso"
    if inverso is not None:
        texto += (f" y es invertible con inverso explícito T⁻¹(x, y) = ({sp.sstr(inverso[0])}, {sp.sstr(inverso[1])})")
    texto += "."
    if "dimension_kaplan_yorke" in d.resultados:
        texto += (f" Es un difeomorfismo disipativo cuyo atractor tiene área nula y dimensión fractal ≈ "
                  f"{d.resultados['dimension_kaplan_yorke']:.2f}: un modelo bidimensional del mecanismo de "
                  "estiramiento y plegado.")
    d.concluir(texto)
    return d


def _inverso(d, campo, x, y, Xp, Yp, valores):
    """Despeje de (x, y) en función de (x', y'), mostrando el orden en que se hace."""
    s = d.seccion("inverso", "b) Despeje de (xₙ, yₙ) en función de (xₙ₊₁, yₙ₊₁)")
    ecuaciones = [sp.Eq(Xp, campo[0]), sp.Eq(Yp, campo[1])]
    s.texto(f"Dado ({Xp.name}, {Yp.name}) = T({x.name}, {y.name}):")
    resuelto = {}
    pendientes = list(ecuaciones)
    dichas = set()
    for _ in range(2):
        avance = False
        for ecuacion in list(pendientes):
            incognitas = (ecuacion.rhs.free_symbols & {x, y}) - set(resuelto)
            if len(incognitas) != 1:
                continue
            incognita = incognitas.pop()
            sustituida = sp.Eq(ecuacion.lhs, ecuacion.rhs.subs(resuelto))
            soluciones = sp.solve(sustituida, incognita)
            if len(soluciones) != 1:
                continue
            valor = sp.simplify(soluciones[0])
            denominador = sp.fraction(sp.together(valor))[1]
            nuevas = [factor.as_base_exp()[0] for factor in sp.Mul.make_args(sp.factor(denominador))
                      if factor.free_symbols and factor.as_base_exp()[0] not in dichas]
            dichas.update(nuevas)
            condicion = (r"\qquad (" + r",\; ".join(rf"{L(c)} \ne 0" for c in nuevas) + ")" if nuevas else "")
            s.formula(rf"{L(ecuacion.lhs)} = {L(ecuacion.rhs)} \implies {L(incognita)} = {L(valor)}" + condicion)
            resuelto[incognita] = valor
            pendientes.remove(ecuacion)
            avance = True
        if not avance:
            break
    if len(resuelto) < 2:
        soluciones = sp.solve(ecuaciones, [x, y], dict=True)
        if len(soluciones) != 1:
            s.texto("El sistema (x', y') = T(x, y) no tiene una única solución (x, y): el mapa no es invertible "
                    "globalmente" + (" con estos valores de los parámetros." if valores else "."))
            d.guardar("invertible", False)
            return None
        resuelto = {k: sp.simplify(v) for k, v in soluciones[0].items()}
    # El inverso, con las variables renombradas a (x, y).
    inverso = [sp.simplify(resuelto[x].subs({Xp: x, Yp: y}, simultaneous=True)),
               sp.simplify(resuelto[y].subs({Xp: x, Yp: y}, simultaneous=True))]
    s = d.seccion("mapa_inverso", "b) Mapa inverso")
    s.formula(rf"T^{{-1}}({L(x)}, {L(y)}) = \left({L(inverso[0])},\; {L(inverso[1])}\right)", destacada=True,
              ref="inverso")
    s = d.seccion("verificacion_inverso", "b) Verificación")
    ida = [sp.simplify(e.subs({x: inverso[0], y: inverso[1]}, simultaneous=True)) for e in campo]
    vuelta = [sp.simplify(e.subs({x: campo[0], y: campo[1]}, simultaneous=True)) for e in inverso]
    s.formula(rf"T\bigl(T^{{-1}}(x,y)\bigr) = ({L(ida[0])},\; {L(ida[1])})"
              + (r" \;\checkmark" if ida == [x, y] else ""))
    s.formula(rf"T^{{-1}}\bigl(T(x,y)\bigr) = ({L(vuelta[0])},\; {L(vuelta[1])})"
              + (r" \;\checkmark" if vuelta == [x, y] else ""))
    d.validar("inverso_por_la_derecha", ida == [x, y], "T(T⁻¹(x, y)) = (x, y) (sympy).")
    d.validar("inverso_por_la_izquierda", vuelta == [x, y], "T⁻¹(T(x, y)) = (x, y) (sympy).")
    det_inv = sp.simplify(sp.Matrix(inverso).jacobian([x, y]).det())
    s.texto("Ambas composiciones dan la identidad, y T y T⁻¹ son suaves, de modo que T es un difeomorfismo "
            "del plano" + (" (con la condición indicada sobre el parámetro)." if det_inv.free_symbols else "."))
    s.formula(rf"\det DT^{{-1}} = {L(det_inv)}")
    d.guardar("inverso", inverso)
    d.guardar("invertible", True)
    if valores and any(sp.simplify(sp.sympify(v)) == 0 for v in valores.values()):
        raise DatoInvalido("Con un parámetro nulo el determinante se anula y el mapa no es invertible.")
    return inverso


def _puntos_fijos_2d(d, campo, campo_num, x, y, valores):
    s = d.seccion("puntos_fijos", "Puntos fijos" + (" para los parámetros dados" if valores else ""))
    soluciones = sp.solve([sp.Eq(campo[0], x), sp.Eq(campo[1], y)], [x, y], dict=True)
    despeje = sp.solve(sp.Eq(campo[1], y), y)
    if len(despeje) == 1 and x in sp.sympify(despeje[0]).free_symbols:
        eliminada = sp.expand((campo[0] - x).subs(y, despeje[0]))
        try:
            if sp.Poly(eliminada, x).LC().could_extract_minus_sign():
                eliminada = -eliminada
            s.formula(rf"{L(y)}^* = {L(despeje[0])},\qquad {L(sp.collect(eliminada, x))} = 0")
        except sp.PolynomialError:
            pass
    J = sp.Matrix(campo_num).jacobian([x, y])
    lista = []
    for i, sol in enumerate(soluciones, 1):
        punto = (sp.simplify(sol.get(x, x)), sp.simplify(sol.get(y, y)))
        if any(sp.sympify(c).subs(valores).free_symbols & {x, y} for c in punto):
            s.formula(rf"\left({L(punto[0])},\; {L(punto[1])}\right) \text{{ es fijo para todo valor libre: una "
                      r"curva entera de puntos fijos, no puntos aislados}}")
            continue
        numerico = [complex(sp.N(sp.sympify(c).subs(valores))) for c in punto]
        if any(abs(c.imag) > 1e-12 for c in numerico):
            continue
        px, py = (c.real for c in numerico)
        autovalores = [complex(v) for v in np.linalg.eigvals(np.array(J.subs({x: px, y: py}), dtype=float))]
        modulos = sorted(abs(v) for v in autovalores)
        tipo = ("silla" if modulos[0] < 1 < modulos[1] else "atractor" if modulos[1] < 1 else
                "repulsor" if modulos[0] > 1 else "no hiperbólico")
        lista.append({"punto": punto, "valor": [px, py], "autovalores": autovalores, "tipo": tipo})
    for i, fijo in enumerate(lista, 1):
        px, py = fijo["valor"]
        valores_propios = r",\; ".join(f"{v.real:.4f}" if abs(v.imag) < 1e-12 else f"{v.real:.4f} \\pm {abs(v.imag):.4f}i"
                                      for v in fijo["autovalores"][:2 if abs(fijo['autovalores'][0].imag) < 1e-12 else 1])
        s.formula(rf"P_{i}:\; {L(x)}^* = {L(fijo['punto'][0])} \approx {px:.4f},\quad {L(y)}^* \approx {py:.4f}"
                  rf"\qquad \mu = {valores_propios} \implies \text{{{fijo['tipo']}}}", destacada=True)
        residuo = max(abs(float(sp.N(sp.sympify(e).subs({x: px, y: py}))) - v)
                      for e, v in zip(campo_num, (px, py)))
        d.validar(f"punto_fijo_{i}", residuo < 1e-9, f"T(P{i}) = P{i} con residuo {residuo:.1e}.",
                  medida=residuo, umbral=1e-9, tipo="numerica")
    if lista and all(f["tipo"] == "silla" for f in lista):
        s.texto("Todos los puntos fijos son sillas (inestables); el atractor se organiza alrededor de ellos.")
    d.guardar("puntos_fijos", [{"valor": f["valor"], "tipo": f["tipo"]} for f in lista])


# ===========================================================================
# 5.4 · Sección de Poincaré y mapa de retorno
# ===========================================================================

def identificar_seccion_poincare(problema):
    if problema.tipo != "edo" or not problema.autonomo or problema.dimension != 3:
        return None
    if "seccion_poincare" not in problema.pedidos and not problema.seccion:
        return None
    return {}


#: Tiempo de integración para recoger cruces, y transitorio descartado.
DURACION_SECCION = 2500.0
TRANSITORIO_SECCION = 200.0


def _cruces(campo_num, estados, variable, valor, sentido, x0):
    f = sp.lambdify([estados], campo_num, "numpy")
    indice = estados.index(variable)

    def evento(t, v):
        return v[indice] - valor
    evento.direction = 1 if sentido == "creciente" else -1
    sol = solve_ivp(lambda t, v: np.asarray(f(v), dtype=float), (0, DURACION_SECCION), x0, method="DOP853",
                    events=evento, rtol=1e-10, atol=1e-12, max_step=0.1, dense_output=False)
    if not sol.success:
        raise MetodoNoAplicable(f"La integración del flujo falló: {sol.message}")
    tiempos, puntos = sol.t_events[0], sol.y_events[0]
    utiles = tiempos > TRANSITORIO_SECCION
    trayectoria = sol.y[:, (sol.t > TRANSITORIO_SECCION) & (sol.t < TRANSITORIO_SECCION + 300)]
    return tiempos[utiles], puntos[utiles], trayectoria


def _mapa_de_retorno(u):
    """Ajuste polinómico de u_{n+1} = g(u_n) y su calidad relativa."""
    ancho = float(u.max() - u.min())
    mejor = None
    for grado in (6, 8, 10):
        coef = np.polyfit(u[:-1], u[1:], grado)
        residuo = float(np.std(u[1:] - np.polyval(coef, u[:-1])))
        mejor = (coef, residuo / ancho, grado)
        if residuo / ancho < 2e-3:
            break
    return mejor


def _es_rossler(campo, estados):
    x, y, z = estados
    a, b, c = (sp.Symbol(n, positive=True) for n in "abc")
    plantilla = [-y - z, x + a * y, b + z * (x - c)]
    libres = {s.name: s for e in campo for s in sp.sympify(e).free_symbols}
    cambio = {plantilla_s: libres[plantilla_s.name] for plantilla_s in (a, b, c) if plantilla_s.name in libres}
    return all(sp.simplify(sp.sympify(e) - p.subs(cambio)) == 0 for e, p in zip(campo, plantilla))


def desarrollar_seccion_poincare(problema, datos=None) -> Desarrollo:
    if identificar_seccion_poincare(problema) is None:
        raise MetodoNoAplicable("Se esperaba un flujo autónomo tridimensional y una sección de Poincaré.")
    from matematica.sistemas_conocidos import leer_seccion
    estados = list(problema.estados)
    campo = problema.campo_simbolico or problema.campo
    valores = problema.valores_simbolicos()
    campo_num = [sp.nsimplify(sp.sympify(e).subs(valores)) for e in campo]
    seccion_pedida = problema.seccion or leer_seccion(problema.enunciado) or \
        {"variable": estados[1].name, "valor": 0.0, "sentido": "creciente"}
    variable = next((v for v in estados if v.name == seccion_pedida["variable"]), None)
    if variable is None:
        raise DatoInvalido(f"La sección menciona {seccion_pedida['variable']!r}, que no es una variable del sistema "
                           f"({', '.join(v.name for v in estados)}).")
    valor = float(seccion_pedida.get("valor", 0.0))
    sentido = seccion_pedida.get("sentido", "creciente")
    x0 = [float(sp.N(v)) for v in problema.ci[1]] if problema.ci is not None else [1.0, 1.0, 0.0]
    d = Desarrollo("seccion_poincare", "Sección de Poincaré y mapa de retorno", TEMA,
                   "Sección transversal del flujo, mapa de primer retorno y reducción a un mapa unidimensional "
                   "por la contracción transversal", tratamiento=["analitico", "numerico"], balotario=["5.4"])

    # --- 1. Disipación y equilibrios ------------------------------------------------------
    s = d.seccion("disipacion", "Disipación y equilibrios")
    div = sp.simplify(sum(sp.diff(e, v) for e, v in zip(campo, estados)))
    div_num = sp.nsimplify(div.subs(valores))
    s.formula(rf"\nabla\cdot\mathbf{{f}} = {L(div)}" + (rf" = {L(div_num)}" if div != div_num else ""))
    espectro = None
    try:
        espectro = espectro_flujo(campo_num, estados, tuple(x0))
    except MetodoNoAplicable as exc:
        raise MetodoNoAplicable(f"{exc} Sin un atractor acotado no hay sección de Poincaré que estudiar.")
    if div_num.free_symbols:
        region = None
        variables = sorted(div_num.free_symbols, key=str)
        if len(variables) == 1:
            region = sp.solveset(div_num < 0, variables[0], sp.S.Reals)
            s.formula(rf"\nabla\cdot\mathbf{{f}} < 0 \iff {describir_conjunto(region, variables[0])}")
        s.texto("La divergencia cambia de signo, pero su media sobre el atractor es negativa: el flujo es "
                "disipativo.")
    s.formula(rf"\langle\nabla\cdot\mathbf{{f}}\rangle \approx {espectro.divergencia_media:.4f}")
    equilibrios = sp.solve(campo_num, estados, dict=True)
    reales = []
    for sol in equilibrios:
        punto = [complex(sp.N(sol.get(v, v))) for v in estados]
        if all(abs(c.imag) < 1e-12 for c in punto):
            reales.append([c.real for c in punto])
    simbolicos = sp.solve(campo, estados, dict=True) if campo != campo_num else []
    for sol in simbolicos[:2]:
        primera = estados[0]
        if primera in sol:
            s.formula(rf"{L(primera)}^* = {L(sp.simplify(sol[primera]))}")
    J = sp.Matrix(campo_num).jacobian(estados)
    reales.sort(key=lambda p: sum(c * c for c in p))
    for i, punto in enumerate(reales, 1):
        autovalores = np.linalg.eigvals(np.array(J.subs(dict(zip(estados, punto))), dtype=float))
        texto_valores = ",\\; ".join(f"{v.real:.3f}" + (f" \\pm {abs(v.imag):.3f}i" if abs(v.imag) > 1e-9 else "")
                                     for v in autovalores if v.imag >= -1e-9)
        s.formula(rf"P_{i} \approx ({', '.join(f'{c:.3f}' for c in punto)}):\quad \lambda = {texto_valores}")
    if reales:
        cercano = reales[0]
        autovalores = np.linalg.eigvals(np.array(J.subs(dict(zip(estados, cercano))), dtype=float))
        complejos = [v for v in autovalores if abs(v.imag) > 1e-9]
        reales_v = [v.real for v in autovalores if abs(v.imag) <= 1e-9]
        if complejos and complejos[0].real > 0 and reales_v and min(reales_v) < 0:
            s.texto(f"Cerca de P₁ la linealización da un foco inestable (parte real {complejos[0].real:.3f} > 0, "
                    f"frecuencia {abs(complejos[0].imag):.3f}) y una dirección estable fuerte (λ ≈ "
                    f"{min(reales_v):.3f}).")
    d.guardar("equilibrios", reales)

    # --- 2. Mecanismo cualitativo (Rössler) ----------------------------------------------
    if _es_rossler(campo, estados):
        a_val = next((float(v) for k, v in valores.items() if k.name == "a"), None)
        c_val = next((float(v) for k, v in valores.items() if k.name == "c"), None)
        s = d.seccion("mecanismo", "Mecanismo cualitativo (espiral y excursión)")
        s.texto(f"Fase de espiral: mientras z ≈ 0, el sistema se comporta como ẋ ≈ −y, ẏ ≈ x + a·y: una espiral "
                f"que se expande (a = {a_val:g} > 0 amplifica la amplitud).")
        s.texto(f"Fase de excursión: cuando x supera c = {c_val:g}, el término z(x − c) de ż se vuelve positivo y "
                "z crece explosivamente (impulsado por b > 0); ẋ = −y − z se hace muy negativo y la trayectoria es "
                "expulsada hacia valores grandes de z.")
        s.texto("Reinyección: al crecer z, x cae por debajo de c y ż < 0; z decae casi exponencialmente y la "
                "trayectoria regresa cerca del plano (x, y), a una distancia del centro que depende de dónde partió. "
                "Esta alternancia de estirar (la espiral) y plegar (la excursión) da lugar al caos.")

    # --- 3. La sección -------------------------------------------------------------------
    otras = [v for v in estados if v != variable]
    indice = estados.index(variable)
    normal = sp.simplify(campo_num[indice].subs(variable, valor))
    normal_simbolica = sp.simplify(campo[indice].subs(variable, valor))
    intentos = [sentido, "decreciente" if sentido == "creciente" else "creciente"]
    elegido = primero = None
    for intento, sentido_i in enumerate(intentos):
        tiempos, puntos, trayectoria = _cruces(campo_num, estados, variable, valor, sentido_i, x0)
        if len(tiempos) < 80:
            continue
        rangos = [float(np.ptp(puntos[:, estados.index(v)])) for v in otras]
        principal = otras[int(np.argmax(rangos))]
        transversal = otras[1 - int(np.argmax(rangos))]
        u = puntos[:, estados.index(principal)]
        signo = -1.0 if np.all(u < 0) else 1.0
        u = signo * u
        coef, calidad, grado = _mapa_de_retorno(u)
        registro = {"sentido": sentido_i, "tiempos": tiempos, "puntos": puntos, "trayectoria": trayectoria,
                    "principal": principal, "transversal": transversal, "signo": signo, "u": u,
                    "coef": coef, "calidad": calidad, "grado": grado, "rangos": rangos}
        if intento == 0:
            primero = registro
        if calidad < 0.02:
            elegido = registro
            break
    if elegido is None:
        raise MetodoNoAplicable("Ninguna de las dos mitades de la sección deja un mapa de retorno unidimensional: "
                                "los cruces no caen sobre una curva.")
    s = d.seccion("seccion", rf"La sección de Poincaré $\Sigma: {L(variable)} = {L(sp.nsimplify(valor))}$")
    condicion = sp.solveset(normal > 0 if sentido == "creciente" else normal < 0,
                            next(iter(normal.free_symbols), otras[0]), sp.S.Reals) if normal.free_symbols else None
    punto = r"\dot{" + L(variable) + "}"
    s.formula(rf"\text{{Sobre }} {L(variable)} = {L(sp.nsimplify(valor))}:\quad {punto} = {L(normal_simbolica)}"
              + (rf" = {L(normal)}" if normal != normal_simbolica else ""))
    if condicion is not None and normal.free_symbols:
        var_n = next(iter(normal.free_symbols))
        signo_txt = ">" if sentido == "creciente" else "<"
        s.formula(rf"{punto} {signo_txt} 0 \iff {describir_conjunto(condicion, var_n)}")
    s.formula(rf"P: \Sigma \to \Sigma, \qquad ({L(otras[0])}_n, {L(otras[1])}_n) \mapsto "
              rf"({L(otras[0])}_{{n+1}}, {L(otras[1])}_{{n+1}})")
    s.texto("Toda órbita del atractor cruza Σ transversalmente, una vez por vuelta. Reducción de dimensión de 3 a 2: "
            "la sección elimina una variable (el flujo es continuo y la sección solo registra el cruce).")
    if primero is not None and elegido is not primero:
        derivada_txt = f"d{variable.name}/dt"
        tramos = ", ".join(f"{v.name} va de {primero['puntos'][:, estados.index(v)].min():.3g} a "
                           f"{primero['puntos'][:, estados.index(v)].max():.3g}" for v in otras)
        aviso = (f"Con {derivada_txt} {'>' if sentido == 'creciente' else '<'} 0 la sección corta el pliegue del "
                 f"atractor (en ella {tramos}): los cruces no caen sobre una curva recorrida por una sola coordenada "
                 f"y el retorno de un cruce al siguiente no es una función (dispersión relativa "
                 f"{100 * primero['calidad']:.0f} %). La reducción a un mapa unidimensional funciona en la otra mitad, "
                 f"{derivada_txt} {'<' if sentido == 'creciente' else '>'} 0, que es la que se usa a continuación.")
        s.texto(aviso)
        d.advertir(aviso)
        d.guardar("mitad_corregida", elegido["sentido"])
    tiempos, puntos = elegido["tiempos"], elegido["puntos"]
    T = float(np.mean(np.diff(tiempos)))
    principal, transversal, signo, u = elegido["principal"], elegido["transversal"], elegido["signo"], elegido["u"]

    # --- 4. Reducción de 2D a 1D ------------------------------------------------------------
    s = d.seccion("reduccion", "Reducción de 2D a 1D por disipación fuerte")
    l3 = espectro.exponentes[-1]
    contraccion = math.exp(l3 * T)
    s.formula(rf"\lambda_3 \approx {l3:.3f},\qquad T \approx {T:.3f} \implies e^{{\lambda_3 T}} \approx "
              rf"{L(contraccion)}")
    rango_t = float(np.ptp(puntos[:, estados.index(transversal)]))
    rango_p = float(np.ptp(puntos[:, estados.index(principal)]))
    s.texto(f"Numéricamente ({len(tiempos)} cruces), los puntos de la sección quedan sobre una curva casi "
            f"unidimensional: {transversal.name} varía solo {rango_t:.3g} mientras {principal.name} recorre "
            f"{rango_p:.3g}. La dinámica se resume en una función escalar:")
    s.formula(rf"u_{{n+1}} = g(u_n), \qquad {('u = -' + L(principal)) if signo < 0 else ('u = ' + L(principal))}",
              destacada=True)
    d.validar("seccion_delgada", elegido["calidad"] < 0.02,
              f"El ajuste u_(n+1) = g(u_n) (polinomio de grado {elegido['grado']}) deja un residuo del "
              f"{100 * elegido['calidad']:.2g} % del rango: los cruces caen sobre una curva.",
              medida=elegido["calidad"], umbral=0.02, tipo="numerica")
    d.guardar("tiempo_de_retorno", T)
    d.guardar("contraccion_por_vuelta", contraccion)

    # --- 5. Forma de g ---------------------------------------------------------------------
    s = d.seccion("forma_de_g", "Forma de g: unimodal con máximo (cúspide)")
    coef = elegido["coef"]
    derivada = np.polyder(coef)
    malla = np.linspace(u.min(), u.max(), 4000)
    valores_g = np.polyval(coef, malla)
    pendientes = np.polyval(derivada, malla)
    cambios = int(np.sum(np.diff(np.sign(pendientes)) != 0))
    u_c = float(malla[np.argmax(valores_g)])
    diferencia = valores_g - malla
    cruces_fijo = np.where(np.diff(np.sign(diferencia)) != 0)[0]
    u_fijo = float(malla[cruces_fijo[-1]]) if len(cruces_fijo) else None
    pendiente_fijo = float(np.polyval(derivada, u_fijo)) if u_fijo is not None else None
    lyap_mapa = float(np.mean(np.log(np.abs(np.polyval(derivada, u[:-1])))))
    l1 = espectro.exponentes[0]
    u_min, u_max = float(u.min()), float(u.max())
    ramas = (np.polyval(coef, u_min) > u_min and np.polyval(derivada, u_min) > 0
             and np.polyval(derivada, u_max) < 0)
    if ramas:
        s.texto("Para u pequeño la amplitud crece de una vuelta a otra: g(u) > u y g'(u) > 0 (rama creciente). "
                "Para u grande la excursión es más pronunciada y el reingreso ocurre más cerca del centro: "
                "g'(u) < 0 (rama decreciente).")
    d.validar("ramas_de_g", bool(ramas),
              f"En u = {u_min:.3f}: g(u) = {np.polyval(coef, u_min):.3f} > u y g' > 0; en u = {u_max:.3f}: "
              f"g' = {np.polyval(derivada, u_max):.3f} < 0.", tipo="numerica")
    s.formula(rf"g'(u_c) = 0 \text{{ en }} u_c \approx {u_c:.3f}\quad (\text{{máximo único: la cúspide}})",
              destacada=True)
    if u_fijo is not None:
        s.formula(rf"\text{{Punto fijo: }} g(u^*) = u^* \text{{ en }} u^* \approx {u_fijo:.3f},\qquad "
                  rf"g'(u^*) \approx {pendiente_fijo:.3f}")
    s.formula(rf"\langle \ln|g'| \rangle \approx {lyap_mapa:.4f} \implies \lambda_1 \approx "
              rf"\frac{{\langle\ln|g'|\rangle}}{{T}} \approx {lyap_mapa / T:.4f}\qquad "
              rf"(\text{{flujo: }} \lambda_1 \approx {l1:.4f})", destacada=True)
    s.texto("g es unimodal, estructuralmente igual a un mapa logístico (estirar la rama creciente, plegar en el "
            "máximo): por eso el caos del flujo es esencialmente el de un mapa unimodal.")
    d.validar("unimodal", cambios == 1, f"g' cambia de signo una sola vez en el rango de los cruces "
                                          f"({cambios} cambio(s)): un único máximo.", tipo="numerica")
    d.validar("lyapunov_por_el_mapa", abs(lyap_mapa / T - l1) < 0.25 * abs(l1) + 0.01,
              f"⟨ln|g'|⟩/T = {lyap_mapa / T:.4f} reproduce el λ₁ = {l1:.4f} del flujo (método QR).",
              medida=abs(lyap_mapa / T - l1), umbral=0.25 * abs(l1) + 0.01, tipo="numerica")
    d.guardar("maximo_de_g", u_c)
    d.guardar("lyapunov_del_mapa", lyap_mapa)
    d.guardar("lambda1_flujo", l1)

    # --- Gráficas ----------------------------------------------------------------------------
    trayectoria = elegido["trayectoria"]
    paso = max(1, trayectoria.shape[1] // 6000)
    d.grafica({"clave": "atractor_y_seccion", "titulo": "Atractor y puntos de la sección",
               "ejes": {"x": estados[0].name, "y": estados[1].name, "z": estados[2].name},
               "capas": [{"tipo": "linea3d", "rol": "trayectoria3d", "nombre": "Atractor",
                          "x": trayectoria[0, ::paso].tolist(), "y": trayectoria[1, ::paso].tolist(),
                          "z": trayectoria[2, ::paso].tolist()},
                         {"tipo": "puntos3d", "rol": "critico", "nombre": "Cruces con Σ",
                          "x": puntos[:400, 0].tolist(), "y": puntos[:400, 1].tolist(), "z": puntos[:400, 2].tolist()}]})
    d.grafica({"clave": "puntos_de_la_seccion", "titulo": "Puntos de la sección",
               "ejes": {"x": principal.name, "y": transversal.name},
               "capas": [{"tipo": "puntos", "rol": "trayectoria", "nombre": "Cruces",
                          "x": puntos[:, estados.index(principal)].tolist(),
                          "y": puntos[:, estados.index(transversal)].tolist(), "tamano": 4}]})
    d.grafica({"clave": "mapa_de_retorno", "titulo": "Mapa de retorno u_{n+1} = g(u_n)",
               "ejes": {"x": "uₙ", "y": "uₙ₊₁"}, "cuadrada": True,
               "capas": [{"tipo": "puntos", "rol": "numerica", "nombre": "Cruces sucesivos",
                          "x": u[:-1].tolist(), "y": u[1:].tolist(), "tamano": 4},
                         {"tipo": "linea", "rol": "mapa", "nombre": f"g ajustada (grado {elegido['grado']})",
                          "x": malla.tolist(), "y": valores_g.tolist()},
                         {"tipo": "linea", "rol": "diagonal", "nombre": "u_{n+1} = u_n",
                          "x": [float(u.min()), float(u.max())], "y": [float(u.min()), float(u.max())]}]})
    d.concluir(f"La sección {variable.name} = {valor:g} ({'creciente' if elegido['sentido'] == 'creciente' else 'decreciente'}) "
               f"reduce el flujo a un mapa bidimensional y, gracias a la fuerte contracción transversal "
               f"(λ₃ ≈ {l3:.2f}, e^(λ₃T) ≈ {contraccion:.0e} por vuelta), a un mapa unidimensional unimodal "
               f"u_(n+1) = g(u_n) con máximo en u ≈ {u_c:.2f}. Esa estructura de pliegue explica la cascada de "
               "duplicaciones de periodo y la universalidad de Feigenbaum: el caos del flujo es esencialmente el "
               "de un mapa logístico.")
    return d


# ===========================================================================
# 5.5 · Dimensión de Kaplan-Yorke
# ===========================================================================

def identificar_kaplan_yorke(problema):
    if "kaplan_yorke" not in problema.pedidos:
        return None
    if problema.tipo == "teorico":
        return {} if _dato(problema.datos or {}, "exponentes", "exponentes_lyapunov") else None
    if problema.tipo == "edo" and problema.autonomo and problema.dimension >= 2:
        return {}
    if problema.tipo == "mapa" and problema.dimension >= 2:
        return {}
    return None


def desarrollar_kaplan_yorke(problema, datos=None) -> Desarrollo:
    if identificar_kaplan_yorke(problema) is None:
        raise MetodoNoAplicable("Se esperaba un espectro de Lyapunov (dado o calculable a partir del sistema).")
    d = Desarrollo("kaplan_yorke", "Dimensión de Lyapunov (Kaplan-Yorke)", TEMA,
                   "Suma de exponentes contra la divergencia media; sumas parciales y fórmula de Kaplan-Yorke",
                   tratamiento=["analitico", "numerico"], balotario=["5.5"])
    dados = _dato(problema.datos or {}, "exponentes", "exponentes_lyapunov")
    dados = [float(v) for v in dados] if dados else None
    if dados is not None and dados != sorted(dados, reverse=True):
        d.advertir("Los exponentes no venían ordenados de mayor a menor: se ordenan antes de aplicar la fórmula.")
        dados = sorted(dados, reverse=True)
    if dados is not None and problema.tipo in ("edo", "mapa") and len(dados) != problema.dimension:
        raise DatoInvalido(f"El sistema tiene {problema.dimension} variables y llegaron {len(dados)} exponentes: "
                           "hace falta uno por dimensión.")
    calculado = None

    # --- a) Suma de exponentes = divergencia media -----------------------------------------
    if problema.tipo in ("edo", "mapa"):
        estados = problema.estados
        campo = problema.campo_simbolico or problema.campo
        valores = problema.valores_simbolicos()
        campo_num = [sp.nsimplify(sp.sympify(e).subs(valores)) for e in campo]
        try:
            calculado = (espectro_flujo(campo_num, estados, _x0_problema(problema)) if problema.tipo == "edo"
                         else espectro_mapa(campo_num, estados))
        except MetodoNoAplicable as exc:
            d.advertir(str(exc))
        s = d.seccion("divergencia", "a) Divergencia del sistema" if problema.tipo == "edo" else
                      "a) Determinante del mapa")
        if problema.tipo == "edo":
            div = sp.simplify(sum(sp.diff(e, v) for e, v in zip(campo, estados)))
            constante = not (div.free_symbols & set(estados))
            s.formula(rf"\nabla\cdot\mathbf{{f}} = {L(div)}" + (r" \equiv \text{constante}" if constante else ""))
            if constante:
                div_num = sp.nsimplify(div.subs(valores))
                s.texto("Al ser constante, su media temporal a lo largo de cualquier órbita es igual a ella misma:")
                s.formula(rf"\langle\nabla\cdot\mathbf{{f}}\rangle = {L(div_num)} \approx {float(div_num):.4f}")
                media = float(div_num)
            else:
                media = calculado.divergencia_media if calculado else None
                if media is not None:
                    s.formula(rf"\langle\nabla\cdot\mathbf{{f}}\rangle \approx {media:.4f}"
                              r"\quad\text{(media a lo largo de la órbita)}")
        else:
            media = calculado.divergencia_media if calculado else None
            if media is not None:
                s.formula(rf"\langle \ln|\det DT| \rangle \approx {media:.4f}")
        s = d.seccion("suma", "a) Suma de los exponentes")
        s.texto("Por la fórmula de Liouville (problema 4.5), Σλᵢ = ⟨∇·f⟩.")
        exponentes = dados if dados is not None else (calculado.exponentes if calculado else None)
        if exponentes is None:
            raise MetodoNoAplicable("No se pudo obtener el espectro: ni viene en el enunciado ni se pudo calcular.")
        total = sum(exponentes)
        s.formula(r"\lambda_1 + \dots + \lambda_n \approx " + " + ".join(f"({v:g})" for v in exponentes)
                  + rf" = {total:.4f}")
        if media is not None:
            coincide = abs(total - media) < max(2e-3 * abs(media), 1e-3)
            s.formula(rf"\sum_i \lambda_i = {total:.4f} " + (r"\approx" if coincide else r"\ne")
                      + rf" {media:.4f} = \langle\nabla\cdot\mathbf{{f}}\rangle"
                      + (r" \quad \checkmark" if coincide else ""), destacada=True)
            d.validar("suma_igual_divergencia", coincide,
                      f"La suma de los exponentes ({total:.5f}) coincide con la divergencia media ({media:.5f}).",
                      medida=abs(total - media), tipo="numerica")
            if dados is not None and coincide and problema.tipo == "edo" and len(dados) == 3:
                s.texto("Esto sirve además como control de calidad del cálculo numérico: dado que λ₂ = 0 y λ₁ se "
                        f"obtiene numéricamente, λ₃ = ⟨∇·f⟩ − λ₁ ≈ {media - dados[0]:.4f} queda determinado.")
            if not coincide and dados is not None:
                d.advertir(f"Los exponentes dados suman {total:.4f}, pero la divergencia media del sistema es "
                           f"{media:.4f}: alguno de los valores no corresponde a este sistema.")
        if calculado is not None and dados is not None:
            tolerancia = [max(0.05, 5 * e, 0.02 * abs(v)) for e, v in zip(calculado.errores, dados)]
            s.formula(r"\text{Espectro calculado (método QR): }" + r",\; ".join(
                rf"\lambda_{i + 1} \approx {v:.4f}" for i, v in enumerate(calculado.exponentes)))
            d.validar("espectro_dado_vs_calculado",
                      all(abs(a - b) < t for a, b, t in zip(dados, calculado.exponentes, tolerancia)),
                      "Los exponentes del enunciado coinciden con los que se calculan para el sistema.",
                      tipo="numerica")
    else:
        exponentes = dados
        d.seccion("datos", "Espectro dado").formula(
            r",\; ".join(rf"\lambda_{i + 1} = {v:g}" for i, v in enumerate(exponentes)))

    # --- b) 1. Determinación de k ----------------------------------------------------------
    s = d.seccion("k", "b) Determinación de k")
    parciales, acumulado = [], 0.0
    for i, v in enumerate(exponentes, 1):
        acumulado += v
        parciales.append(acumulado)
        relacion = r"\ge" if acumulado >= 0 else "<"
        s.formula(rf"S_{i} = " + " + ".join(rf"\lambda_{j}" for j in range(1, i + 1))
                  + rf" = {acumulado:.4f} {relacion} 0")
    k = max((i for i, v in enumerate(parciales, 1) if v >= 0), default=0)
    s.formula(rf"k = {k}", destacada=True, ref="k")
    n = len(exponentes)

    # --- b) 2. D_L -------------------------------------------------------------------------
    s = d.seccion("dimension", "b) Cálculo de D_L")
    if k == 0:
        D_L = 0.0
        s.texto("Ya λ₁ < 0: todas las direcciones contraen y el atractor es un punto (D_L = 0).")
    elif k == n:
        D_L = float(n)
        s.texto("La suma de todos los exponentes no es negativa: el sistema no contrae volumen y la fórmula da "
                f"la dimensión completa D_L = {n}.")
        d.advertir("Con Σλᵢ ≥ 0 el sistema no es disipativo: la dimensión de Kaplan-Yorke no describe un atractor.")
    else:
        fraccion = parciales[k - 1] / abs(exponentes[k])
        D_L = k + fraccion
        s.formula(rf"D_L = k + \frac{{S_{k}}}{{|\lambda_{k + 1}|}} = {k} + \frac{{{parciales[k - 1]:.4f}}}"
                  rf"{{{abs(exponentes[k]):.4f}}}")
        s.formula(rf"\frac{{{parciales[k - 1]:.4f}}}{{{abs(exponentes[k]):.4f}}} \approx {fraccion:.5f}")
        s.formula(rf"D_L \approx {D_L:.4f}", destacada=True, ref="dimension_lyapunov")
    d.guardar("k", k)
    d.guardar("dimension_lyapunov", D_L)
    d.guardar("exponentes", exponentes)
    if calculado is not None and dados is not None and 0 < k < n:
        propio = k + sum(calculado.exponentes[:k]) / abs(calculado.exponentes[k])
        d.validar("dimension_con_el_espectro_calculado", abs(propio - D_L) < 0.02,
                  f"Con el espectro calculado D_L ≈ {propio:.4f}, frente a {D_L:.4f} con los exponentes dados.",
                  medida=abs(propio - D_L), umbral=0.02, tipo="numerica")

    # --- b) 3. Interpretación ---------------------------------------------------------------
    if 0 < k < n:
        s = d.seccion("interpretacion", "b) Interpretación física")
        s.texto(f"{k} < D_L < {k + 1}: el atractor no es una variedad de dimensión {k} ni llena una región de "
                f"dimensión {k + 1}. Esto concuerda con la disipación: el volumen se contrae a cero, así que "
                f"D_L < {n}.")
        if problema.tipo == "edo" and k == 2 and n == 3:
            s.texto("Dimensión 2 de base: la expansión a lo largo de λ₁ y la dirección neutra del flujo (λ₂ = 0) "
                    "dan una variedad bidimensional (lámina).")
            s.texto(f"Fracción ≈ {D_L - k:.3f}: la lámina no es lisa: está formada por infinitas capas muy próximas, "
                    "cada una plegada sobre sí misma (estirar y plegar). Un corte transversal es un conjunto de "
                    f"Cantor, con la dimensión fraccionaria adicional λ₁/|λ₃| que mide cuánto de la expansión no "
                    "es absorbida por la contracción. Como |λ₃| es mucho mayor que λ₁, las capas se aplastan mucho "
                    "más rápido de lo que se separan y el atractor es casi una superficie.")
        s.texto(f"Un valor entero ({k}) sería periodicidad o cuasiperiodicidad; el exceso D_L − {k} > 0 es la "
                "medida de la complejidad caótica.")
    parciales_x = list(range(0, n + 1))
    parciales_y = [0.0, *parciales]
    capas = [{"tipo": "linea", "rol": "trayectoria", "nombre": "S(j) = λ₁ + ... + λⱼ", "x": parciales_x,
              "y": parciales_y, "marcadores": True},
             {"tipo": "linea", "rol": "referencia", "nombre": "S = 0", "x": [0, n], "y": [0, 0]}]
    if 0 < k < n:
        capas.append({"tipo": "puntos", "rol": "critico", "nombre": f"D_L ≈ {D_L:.4f}", "x": [D_L], "y": [0]})
    d.grafica({"clave": "sumas_parciales", "titulo": "Sumas parciales del espectro: D_L es donde S cruza 0",
               "ejes": {"x": "j", "y": "S(j)"}, "capas": capas})
    if 0 < k < n:
        d.concluir(f"D_L = {k} + {parciales[k - 1]:.4f}/{abs(exponentes[k]):.4f} ≈ {D_L:.4f} es fraccionaria: el "
                   f"atractor es un objeto fractal ligeramente más complejo que una variedad de dimensión {k}, "
                   "formado por una infinidad de láminas plegadas con corte transversal de tipo Cantor, que ocupa "
                   "un volumen nulo.")
    return d


def _x0_problema(problema):
    if problema.ci is not None:
        return tuple(float(sp.N(v)) for v in problema.ci[1])
    return None
