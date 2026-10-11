"""Equilibrios, linealización y clasificación de estabilidad.

Es la maquinaria que comparten los Temas 2 y 3 del balotario: hallar los puntos
de equilibrio, construir la matriz jacobiana, evaluarla en cada punto, obtener
el polinomio característico, los autovalores y autovectores, y clasificar.

Qué cambió respecto del prototipo
---------------------------------
La versión anterior derivaba el Jacobiano por diferencias finitas y solo sabía
decir "estable", "inestable" o "no concluyente". El balotario pide más: un
punto silla no es lo mismo que un nodo inestable, ni un foco que un centro, y
la diferencia se lee en la traza, el determinante y el discriminante. Aquí todo
es exacto (sympy): el Jacobiano, los autovalores (−1 ± √2 en el 2.3, no
−2.414) y la clasificación, que sigue las reglas del plano traza-determinante.

Las funciones devuelven objetos con significado (`Linealizacion`, `Regimen`),
no texto: quien presenta el desarrollo decide cómo escribirlos.
"""

from __future__ import annotations

import functools
import itertools
import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp

from matematica.desarrollo import L, a_json, numero

#: Símbolo del autovalor en los polinomios característicos.
LAMBDA = sp.Symbol("lambda")

#: Ventana donde se buscan representantes cuando hay infinitos equilibrios
#: (sen θ = 0). Dos periodos a cada lado bastan para el retrato de fase.
VENTANA_PERIODICA = (-2 * sp.pi, 2 * sp.pi)

#: Tope de equilibrios que se clasifican. Por encima se informa el recorte.
MAXIMO_EQUILIBRIOS = 12


# ---------------------------------------------------------------------------
# Utilidades de signo exacto
# ---------------------------------------------------------------------------

def signo(valor) -> int | None:
    """Signo exacto de un número sympy: -1, 0, 1, o None si no es real o no se decide."""
    valor = sp.nsimplify(valor) if isinstance(valor, float) else sp.sympify(valor)
    if valor.is_zero:
        return 0
    if valor.is_positive:
        return 1
    if valor.is_negative:
        return -1
    aproximado = numero(valor)
    if isinstance(aproximado, (int, float)):
        if abs(aproximado) < 1e-12:
            return 0
        return 1 if aproximado > 0 else -1
    return None


def es_autonomo(expresiones, independiente) -> bool:
    """True si ninguna ecuación depende de la variable independiente."""
    return not any(independiente in sp.sympify(e).free_symbols for e in expresiones)


def jacobiano(campo, estados) -> sp.Matrix:
    """Matriz jacobiana exacta del campo respecto del estado."""
    return sp.Matrix(list(campo)).jacobian(list(estados))


# ---------------------------------------------------------------------------
# Clasificación
# ---------------------------------------------------------------------------

def clasificar_2x2(traza, determinante, discriminante, matriz=None):
    """Tipo y estabilidad de un equilibrio plano a partir de τ, Δ y D = τ² − 4Δ.

    Devuelve (tipo, estabilidad, hiperbolico). Las palabras son las del
    balotario. Un centro lineal no decide la estabilidad de un sistema no
    lineal: eso lo marca `hiperbolico=False` y la familia que lo use tiene que
    argumentarlo por otra vía (energía, función de Lyapunov).
    """
    s_tau, s_delta, s_disc = signo(traza), signo(determinante), signo(discriminante)
    if None in (s_tau, s_delta, s_disc):
        return "no determinado", "no concluyente", False
    if s_delta < 0:
        return "punto silla", "inestable", True
    if s_delta == 0:
        return "no hiperbólico (autovalor nulo)", "no concluyente", False
    if s_tau == 0:
        return "centro", "estable (no asintóticamente)", False
    sentido = "estable" if s_tau < 0 else "inestable"
    estabilidad = "asintóticamente estable" if s_tau < 0 else "inestable"
    if s_disc < 0:
        return f"foco {sentido}", estabilidad, True
    if s_disc > 0:
        return f"nodo {sentido}", estabilidad, True
    # D = 0: autovalor doble. Si la matriz es múltiplo de la identidad, todas
    # las direcciones son propias (nodo estrella); si no, nodo impropio.
    if matriz is not None:
        lam = traza / 2
        if (sp.Matrix(matriz) - lam * sp.eye(2)).is_zero_matrix:
            return f"nodo estrella {sentido}", estabilidad, True
    return f"nodo impropio (degenerado) {sentido}", estabilidad, True


def clasificar_1d(derivadas):
    """Estabilidad de un equilibrio de x' = f(x) a partir de f', f'', f''' en x*.

    `derivadas` es la lista [f'(x*), f''(x*), ...]. Si f'(x*) ≠ 0 decide su
    signo; si se anula, decide la primera derivada no nula: de orden par da
    un equilibrio semiestable (el caso del balotario en el punto de una
    silla-nodo), de orden impar estable o inestable según el signo.
    """
    for orden, valor in enumerate(derivadas, start=1):
        s = signo(valor)
        if s is None:
            return "no determinado", "no concluyente", False, orden
        if s == 0:
            continue
        if orden == 1:
            return (("atractor", "asintóticamente estable", True, 1) if s < 0
                    else ("repulsor", "inestable", True, 1))
        if orden % 2 == 0:
            return "semiestable", "semiestable (no hiperbólico)", False, orden
        return (("atractor no hiperbólico", "asintóticamente estable", False, orden) if s < 0
                else ("repulsor no hiperbólico", "inestable", False, orden))
    return "no determinado", "no concluyente", False, len(derivadas)


# ---------------------------------------------------------------------------
# Linealización en un punto
# ---------------------------------------------------------------------------

@dataclass
class Linealizacion:
    """Todo lo que la linealización en un equilibrio produce."""

    punto: tuple
    jacobiano: sp.Matrix | None
    polinomio: sp.Expr | None = None
    autovalores: list = field(default_factory=list)
    autovectores: list = field(default_factory=list)      # [(λ, vector)]
    traza: sp.Expr | None = None
    determinante: sp.Expr | None = None
    discriminante: sp.Expr | None = None
    tipo: str = "no determinado"
    estabilidad: str = "no concluyente"
    hiperbolico: bool = False
    definida: bool = True
    nota: str | None = None

    @property
    def estable(self) -> bool:
        return self.estabilidad.startswith("asintóticamente estable")

    @property
    def estabilidad_corta(self) -> str:
        """estable / inestable / no concluyente: el vocabulario del motor anterior."""
        if self.estabilidad.startswith("asintóticamente estable"):
            return "estable"
        if self.estabilidad.startswith("inestable"):
            return "inestable"
        return "no concluyente"

    def autovalores_numericos(self) -> list[complex]:
        return [complex(sp.N(v)) for v in self.autovalores]

    def direcciones(self):
        """Direcciones propias reales: [(λ, vector unitario numpy)]."""
        salida = []
        for valor, vector in self.autovectores:
            if sp.im(sp.N(valor)) != 0:
                continue
            v = np.array([float(sp.N(c)) for c in vector], dtype=float)
            norma = np.linalg.norm(v)
            if norma > 0:
                salida.append((float(sp.N(valor)), v / norma))
        return salida

    def a_dict(self):
        salida = {
            "punto": [a_json(c) for c in self.punto],
            "tipo": self.tipo,
            "estabilidad": self.estabilidad,
            "hiperbolico": self.hiperbolico,
            "autovalores": [a_json(v) for v in self.autovalores],
        }
        if self.jacobiano is not None:
            salida["jacobiano"] = a_json(self.jacobiano)
        if self.polinomio is not None:
            salida["polinomio_caracteristico"] = a_json(self.polinomio)
        if self.autovectores:
            salida["autovectores"] = [{"autovalor": a_json(l), "vector": a_json(v)}
                                      for l, v in self.autovectores]
        for clave in ("traza", "determinante", "discriminante"):
            valor = getattr(self, clave)
            if valor is not None:
                salida[clave] = a_json(valor)
        if self.nota:
            salida["nota"] = self.nota
        if not self.definida:
            salida["definida"] = False
        return salida


def _simplificar_vector(vector):
    """Autovector como lo escribe el balotario: sin denominadores y con la última
    componente no nula positiva ((−√2, 1) y no (√2, −1))."""
    vector = sp.Matrix([sp.nsimplify(sp.simplify(c)) for c in vector])
    if all(c.is_Rational for c in vector):
        mcm = functools.reduce(sp.ilcm, [sp.fraction(c)[1] for c in vector], 1)
        vector = vector * mcm
        divisor = functools.reduce(math.gcd, [abs(int(c)) for c in vector if c != 0], 0) or 1
        vector = vector / divisor
    no_nulos = [c for c in vector if not c.is_zero]
    if no_nulos and signo(no_nulos[-1]) == -1:
        vector = -vector
    return sp.Matrix([sp.simplify(c) for c in vector])


def autovalores_exactos(matriz):
    """Autovalores con su multiplicidad, exactos cuando sympy los da en forma cerrada."""
    try:
        valores = matriz.eigenvals()
    except (NotImplementedError, sp.polys.polyerrors.PolynomialError):
        valores = None
    if not valores or any(v.has(sp.CRootOf) or sp.count_ops(v) > 40 for v in valores):
        numericos = np.linalg.eigvals(np.array(matriz.evalf(), dtype=float))
        return [sp.Float(v.real, 12) + sp.I * sp.Float(v.imag, 12) if abs(v.imag) > 1e-14
                else sp.Float(v.real, 12) for v in numericos]
    lista = []
    for valor, multiplicidad in valores.items():
        lista.extend([sp.simplify(valor)] * multiplicidad)
    return sorted(lista, key=_clave_de_orden)


def _clave_de_orden(valor):
    """Orden por parte real e imaginaria; con parámetros simbólicos, por el signo de i."""
    try:
        aproximado = complex(sp.N(valor))
        return (0, aproximado.real, aproximado.imag, "")
    except (TypeError, ValueError):
        imaginaria = sp.im(valor)
        return (1, 0.0, -1.0 if imaginaria.could_extract_minus_sign() else 1.0, sp.sstr(valor))


def linealizar(campo, estados, punto, *, matriz_general=None, con_vectores=True) -> Linealizacion:
    """Linealiza el campo en `punto` y clasifica el equilibrio.

    `matriz_general` permite reutilizar un Jacobiano ya calculado. Si el
    Jacobiano no existe en el punto (el campo no es diferenciable allí, como el
    origen del problema 2.5), se informa con `definida=False` en vez de
    devolver números que no significan nada.
    """
    estados = list(estados)
    punto = tuple(sp.nsimplify(c) if isinstance(c, float) else sp.sympify(c) for c in punto)
    general = matriz_general if matriz_general is not None else jacobiano(campo, estados)
    sustitucion = dict(zip(estados, punto))
    try:
        evaluado = general.subs(sustitucion).applyfunc(sp.simplify)
    except (ZeroDivisionError, TypeError):
        evaluado = None
    if evaluado is None or any(e.has(sp.nan, sp.zoo, sp.oo, -sp.oo) for e in evaluado):
        return Linealizacion(punto=punto, jacobiano=None, definida=False,
                             nota="El campo no es diferenciable en este punto: la matriz "
                                  "jacobiana no existe y la linealización no aplica.")

    n = len(estados)
    resultado = Linealizacion(punto=punto, jacobiano=evaluado)
    if n == 1:
        derivada = evaluado[0, 0]
        resultado.autovalores = [derivada]
        resultado.polinomio = LAMBDA - derivada
        orden_superior = [derivada]
        expresion = sp.sympify(campo[0])
        for k in (2, 3, 4):
            orden_superior.append(sp.diff(expresion, estados[0], k).subs(sustitucion))
        tipo, estabilidad, hiperbolico, orden = clasificar_1d(orden_superior)
        resultado.tipo, resultado.estabilidad, resultado.hiperbolico = tipo, estabilidad, hiperbolico
        if orden > 1:
            resultado.nota = (f"f'(x*) = 0: decide la derivada de orden {orden}, que es la "
                              "primera que no se anula.")
        return resultado

    resultado.polinomio = sp.expand((evaluado - LAMBDA * sp.eye(n)).det())
    resultado.autovalores = autovalores_exactos(evaluado)
    if n == 2:
        resultado.traza = sp.simplify(evaluado.trace())
        resultado.determinante = sp.simplify(evaluado.det())
        resultado.discriminante = sp.simplify(resultado.traza ** 2 - 4 * resultado.determinante)
        tipo, estabilidad, hiperbolico = clasificar_2x2(
            resultado.traza, resultado.determinante, resultado.discriminante, evaluado)
    else:
        tipo, estabilidad, hiperbolico = _clasificar_n(resultado.autovalores)
    resultado.tipo, resultado.estabilidad, resultado.hiperbolico = tipo, estabilidad, hiperbolico
    if con_vectores and all(e.is_number for e in evaluado):
        try:
            for valor, _, vectores in evaluado.eigenvects():
                for vector in vectores:
                    resultado.autovectores.append((sp.simplify(valor), _simplificar_vector(vector)))
        except (NotImplementedError, ValueError):
            pass
    return resultado


def _clasificar_n(autovalores):
    """Clasificación por signos de las partes reales, para n ≥ 3."""
    reales = [float(sp.re(sp.N(v))) for v in autovalores]
    positivos = sum(1 for r in reales if r > 1e-12)
    negativos = sum(1 for r in reales if r < -1e-12)
    if positivos == 0 and negativos == len(reales):
        return "sumidero", "asintóticamente estable", True
    if negativos == 0 and positivos == len(reales):
        return "fuente", "inestable", True
    if positivos and negativos and positivos + negativos == len(reales):
        return f"silla (índice {positivos})", "inestable", True
    if positivos:
        return "no hiperbólico con dirección inestable", "inestable", False
    return "no hiperbólico", "no concluyente", False


# ---------------------------------------------------------------------------
# Búsqueda de equilibrios
# ---------------------------------------------------------------------------

@dataclass
class Equilibrio:
    """Un equilibrio hallado, con el caso de la factorización que lo produjo."""

    punto: tuple
    caso: list = field(default_factory=list)      # [ecuación de cada factor usado]

    def a_dict(self):
        return {"punto": [a_json(c) for c in self.punto],
                "caso": [a_json(c) for c in self.caso]}


def _factores(expresion, estados=None):
    """Factores que pueden anularse (x(3 − x − 2y) → [x, 3 − x − 2y]).

    Un factor que no contiene variables de estado (ω₀² en −ω₀² sin θ) no
    produce equilibrios: es un parámetro, que se supone no nulo.
    """
    expresion = sp.factor(sp.together(expresion))
    numerador, _ = sp.fraction(expresion)
    try:
        _, lista = sp.factor_list(numerador)
    except (sp.PolynomialError, NotImplementedError):
        return [numerador]
    factores = [f for f, _ in lista if not f.is_number
                and (estados is None or f.has(*estados))]
    return factores or [numerador]


def igualdad_de_factor(factor, estados):
    """Escribe `factor = 0` como lo escribe el balotario: x + 2y = 3, no −x − 2y + 3 = 0."""
    factor = sp.expand(factor)
    constante = factor.as_independent(*estados, as_Add=True)[0]
    variable = sp.expand(factor - constante)
    if variable == 0:
        return sp.Eq(factor, 0, evaluate=False)
    principal = sp.Poly(variable, *estados).coeffs()[0] if variable.is_polynomial(*estados) else 1
    if signo(principal) == -1:
        variable, constante = -variable, -constante
    if constante == 0:
        return sp.Eq(variable, 0, evaluate=False)
    return sp.Eq(variable, -constante, evaluate=False)


def _dentro(punto, estados, region):
    for estado, valor in zip(estados, punto):
        inferior, superior = region.get(estado, (None, None))
        aproximado = numero(valor)
        if not isinstance(aproximado, (int, float)):
            return False
        if inferior is not None and aproximado < inferior - 1e-12:
            return False
        if superior is not None and aproximado > superior + 1e-12:
            return False
    return True


def _es_real(valor):
    valor = sp.sympify(valor)
    if valor.free_symbols:
        return True
    return valor.is_real is not False and abs(complex(sp.N(valor)).imag) < 1e-12


def buscar_equilibrios(campo, estados, region=None, ventana=None):
    """Resuelve F(x) = 0 de forma exacta y devuelve (equilibrios, informe).

    En el plano sigue el procedimiento del balotario (2.3): factorizar cada
    ecuación, combinar un factor de ẋ = 0 con uno de ẏ = 0 y resolver cada
    caso. Así cada punto llega con el par de ecuaciones que lo produjo, que es
    lo que el desarrollo muestra. Si el campo no factoriza, se resuelve el
    sistema completo. Con infinitos equilibrios (sen θ = 0) se dan los de una
    ventana y se informa la forma general.
    """
    estados = list(estados)
    campo = [sp.sympify(e) for e in campo]
    region = region or {}
    informe = {"metodo": "simbolico"}
    hallados: list[Equilibrio] = []
    complejos = set()          # el respaldo vuelve a resolver: no contar dos veces

    def agregar(punto, caso):
        punto = tuple(sp.nsimplify(sp.simplify(c)) if not sp.sympify(c).free_symbols
                      else sp.simplify(c) for c in punto)
        if not all(_es_real(c) for c in punto):
            complejos.add(punto)
            informe["descartados"] = len(complejos)
            return
        if region and not _dentro(punto, estados, region):
            informe.setdefault("fuera_de_region", 0)
            informe["fuera_de_region"] += 1
            return
        for previo in hallados:
            if all(sp.simplify(a - b) == 0 for a, b in zip(previo.punto, punto)):
                return
        hallados.append(Equilibrio(punto, caso))

    if len(estados) == 1:
        variable, expresion = estados[0], campo[0]
        dominio = sp.S.Reals
        soluciones = sp.solveset(expresion, variable, domain=dominio)
        if isinstance(soluciones, sp.FiniteSet):
            for valor in soluciones:
                agregar((valor,), [sp.Eq(expresion, 0)])
        else:
            informe["general"] = soluciones
            a, b = ventana or VENTANA_PERIODICA
            if variable in region:
                inferior, superior = region[variable]
                a = sp.nsimplify(inferior) if inferior is not None else a
                b = sp.nsimplify(superior) if superior is not None else b
            locales = sp.solveset(expresion, variable, domain=sp.Interval(a, b))
            if isinstance(locales, sp.FiniteSet):
                for valor in sorted(locales, key=lambda v: float(v)):
                    agregar((valor,), [sp.Eq(expresion, 0)])
                informe["ventana"] = (a, b)
            else:
                informe["nota"] = "sympy no pudo enumerar los equilibrios."
    else:
        listas = [_factores(e, estados) for e in campo]
        if len(estados) == 2:
            casos = [(a, b) for a in listas[0] for b in listas[1]]
        else:
            casos = [tuple(combinacion) for combinacion in itertools.product(*listas)]
        if len(casos) > 64:              # demasiadas combinaciones: resolver el sistema entero
            casos = [tuple(campo)]
        for caso in casos:
            try:
                soluciones = sp.solve(list(caso), estados, dict=True)
            except (NotImplementedError, sp.PolynomialError, TypeError, ValueError):
                soluciones = []
            for solucion in soluciones:
                if len(solucion) < len(estados) or any(
                        v.free_symbols & set(estados) for v in solucion.values()):
                    informe["no_aislados"] = True
                    continue
                agregar(tuple(solucion[s] for s in estados),
                        [igualdad_de_factor(f, estados) for f in caso])
        if not hallados and not informe.get("no_aislados"):
            # Respaldo para campos que no factorizan como producto útil.
            try:
                for solucion in sp.solve(campo, estados, dict=True):
                    if len(solucion) == len(estados):
                        agregar(tuple(solucion[s] for s in estados), [])
            except (NotImplementedError, TypeError, ValueError):
                informe["nota"] = "sympy no pudo resolver F = 0."

    hallados.sort(key=lambda e: tuple(float(sp.N(c)) if not sp.sympify(c).free_symbols else 0.0
                                      for c in e.punto))
    avisos = []
    if informe.get("descartados"):
        avisos.append(f"{informe['descartados']} solución(es) compleja(s) de F = 0 descartada(s): un "
                      "equilibrio tiene que ser un punto real del espacio de fases.")
    if len(hallados) > MAXIMO_EQUILIBRIOS:
        informe["recortados"] = len(hallados) - MAXIMO_EQUILIBRIOS
        hallados = hallados[:MAXIMO_EQUILIBRIOS]
        avisos.append(f"Hay más de {MAXIMO_EQUILIBRIOS} equilibrios: se reportan los primeros "
                      f"{MAXIMO_EQUILIBRIOS}.")
    if avisos:
        informe["nota"] = " ".join(filter(None, [informe.get("nota"), *avisos]))
    informe["encontrados"] = len(hallados)
    return hallados, informe


def nulclinas(campo, estados):
    """Curvas ẋᵢ = 0 de cada ecuación, como igualdades legibles."""
    return [[igualdad_de_factor(f, estados) for f in _factores(e, estados)] for e in campo]


# ---------------------------------------------------------------------------
# Clasificación según un parámetro (2.2 y la parte local de 3.5)
# ---------------------------------------------------------------------------

@dataclass
class Regimen:
    """Un tramo del parámetro con su clasificación."""

    conjunto: sp.Set                   # Interval o FiniteSet de un punto
    traza: sp.Expr
    determinante: sp.Expr
    discriminante: sp.Expr
    tipo: str
    estabilidad: str
    autovalores: list

    @property
    def es_punto(self) -> bool:
        return isinstance(self.conjunto, sp.FiniteSet)

    def a_dict(self):
        return {"conjunto": a_json(self.conjunto), "tipo": self.tipo,
                "estabilidad": self.estabilidad,
                "traza": a_json(self.traza), "determinante": a_json(self.determinante),
                "discriminante": a_json(self.discriminante),
                "autovalores": [a_json(v) for v in self.autovalores]}


def _valor_de_prueba(intervalo: sp.Interval):
    a, b = intervalo.start, intervalo.end
    if a.is_infinite and b.is_infinite:
        return sp.Integer(0)
    if a.is_infinite:
        return b - 1
    if b.is_infinite:
        return a + 1
    return (a + b) / 2


def _autovalores_por_regimen(traza, discriminante, signo_disc):
    if signo_disc is not None and signo_disc < 0:
        parte_real = sp.simplify(traza / 2)
        imaginaria = sp.simplify(sp.sqrt(-discriminante) / 2)
        return [parte_real - sp.I * imaginaria, parte_real + sp.I * imaginaria]
    raiz = sp.sqrt(discriminante)
    return [sp.simplify((traza - raiz) / 2), sp.simplify((traza + raiz) / 2)]


def regimenes_por_parametro(matriz, parametro, rango=None):
    """Clasifica un equilibrio plano en cada tramo del parámetro.

    Es el procedimiento del 2.2: τ(p), Δ(p) y D(p) = τ² − 4Δ; sus ceros
    reales dentro del dominio son los valores críticos, y en cada tramo entre
    ellos el signo de los tres es constante, así que basta un valor de prueba
    para clasificar el tramo entero. Tramos vecinos con la misma
    clasificación se funden.

    Devuelve (traza, determinante, discriminante, críticos, regímenes).
    """
    matriz = sp.Matrix(matriz)
    traza = sp.simplify(matriz.trace())
    determinante = sp.simplify(matriz.det())
    discriminante = sp.factor(sp.expand(traza ** 2 - 4 * determinante))
    inferior, superior = (rango or (None, None))
    dominio = sp.Interval(sp.nsimplify(inferior) if inferior is not None else -sp.oo,
                          sp.nsimplify(superior) if superior is not None else sp.oo)

    criticos = set()
    for expresion in (traza, determinante, discriminante):
        if parametro not in sp.sympify(expresion).free_symbols:
            continue
        ceros = sp.solveset(expresion, parametro, domain=dominio)
        if isinstance(ceros, sp.FiniteSet):
            criticos.update(ceros)
    # Los extremos finitos del dominio también son tramos propios: en el 2.2,
    # γ = 0 (el borde de γ ≥ 0) es justamente el centro.
    criticos.update(c for c in (dominio.start, dominio.end) if c.is_finite)
    criticos = sorted(criticos, key=lambda v: float(v))
    cortes = [dominio.start, *[c for c in criticos if c not in (dominio.start, dominio.end)],
              dominio.end]
    tramos = [sp.FiniteSet(c) for c in criticos]
    tramos += [sp.Interval.open(a, b) for a, b in zip(cortes[:-1], cortes[1:]) if a != b]
    tramos.sort(key=lambda s: (float(s.inf), 0 if isinstance(s, sp.FiniteSet) else 1))

    regimenes = []
    for tramo in tramos:
        prueba = next(iter(tramo)) if isinstance(tramo, sp.FiniteSet) else _valor_de_prueba(tramo)
        t, d, disc = (sp.simplify(e.subs(parametro, prueba)) for e in (traza, determinante, discriminante))
        tipo, estabilidad, _ = clasificar_2x2(t, d, disc, matriz.subs(parametro, prueba))
        if isinstance(tramo, sp.FiniteSet):
            autovalores = _autovalores_por_regimen(t, disc, signo(disc))
        else:
            autovalores = _autovalores_por_regimen(traza, discriminante, signo(disc))
        regimenes.append(Regimen(tramo, t if isinstance(tramo, sp.FiniteSet) else traza,
                                 d if isinstance(tramo, sp.FiniteSet) else determinante,
                                 disc if isinstance(tramo, sp.FiniteSet) else discriminante,
                                 tipo, estabilidad, autovalores))

    fundidos = []
    for regimen in regimenes:
        if fundidos and fundidos[-1].tipo == regimen.tipo and \
                fundidos[-1].estabilidad == regimen.estabilidad:
            previo = fundidos[-1]
            previo.conjunto = sp.Union(previo.conjunto, regimen.conjunto)
            previo.traza, previo.determinante, previo.discriminante = traza, determinante, discriminante
            previo.autovalores = _autovalores_por_regimen(traza, discriminante, None)
            continue
        fundidos.append(regimen)
    return traza, determinante, discriminante, criticos, fundidos


def describir_conjunto(conjunto, parametro) -> str:
    """'0 < γ < 4', 'γ = 4', 'γ > 4' en LaTeX, como en el balotario."""
    p = L(parametro)
    if isinstance(conjunto, sp.FiniteSet):
        return r",\; ".join(f"{p} = {L(v)}" for v in conjunto)
    if isinstance(conjunto, sp.Interval):
        a, b = conjunto.start, conjunto.end
        menor_izq = "<" if conjunto.left_open else r"\le"
        menor_der = "<" if conjunto.right_open else r"\le"
        izquierda = "" if a.is_infinite else f"{L(a)} {menor_izq} "
        derecha = "" if b.is_infinite else f" {menor_der} {L(b)}"
        if not izquierda and not derecha:
            return p + r" \in \mathbb{R}"
        return f"{izquierda}{p}{derecha}"
    if isinstance(conjunto, sp.Union):
        return r" \;\lor\; ".join(describir_conjunto(a, parametro) for a in conjunto.args)
    return rf"{p} \in {L(conjunto)}"
