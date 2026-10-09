"""El problema matemático: la solicitud ya interpretada como objetos sympy.

Es el punto de entrada de la capa matemática. Todo lo que llega del cliente
(texto de ecuaciones, nombres, valores) se convierte aquí, una vez, en:

* símbolos reales para la variable independiente y el estado;
* el campo F(t, x) como expresiones exactas: los valores numéricos de los
  parámetros entran como racionales o múltiplos de π cuando lo son
  (`2.6666666666666665` → 8/3, `1.0471975511965976` → π/3), porque un método
  analítico con flotantes deja de ser exacto;
* el **parámetro simbólico**, si lo hay: el que se estudia (γ del oscilador, μ
  de una bifurcación) queda como símbolo y su valor, si se dio, solo se usa
  para el cálculo numérico y las gráficas;
* la **forma compañera**: un sistema [y, y'] con y' = yp, yp' = F(x, y, yp) es
  una EDO escalar de segundo orden, y así la ven las familias que la necesitan
  (Cauchy-Euler, el péndulo), con nombres de presentación y', θ̇.

La validación de seguridad (sin `eval`, lista blanca) la hace
`matematica.expresiones`; aquí solo se usa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np
import sympy as sp

from matematica import MAX_DIMENSION
from matematica.expresiones import ExpresionInvalida, parsear, simbolos

#: Denominador máximo para reconocer un racional "de enunciado" (8/3, 3/10).
_DENOMINADOR_MAXIMO = 1000


def exacto(valor):
    """Número exacto a partir de un flotante del cliente, sin inventar estructura.

    Solo se acepta una forma cerrada cuando reproduce el flotante dentro de
    1e-12 y es de las que un enunciado escribe: entero, racional de
    denominador pequeño, racional por π o raíz cuadrada de un racional. Si
    nada de eso encaja se usa el decimal exacto que el cliente escribió, que
    es lo que el número *es*. `nsimplify` a secas no sirve: con tolerancia
    convierte 0.123456789 en un producto de potencias sin sentido.
    """
    if isinstance(valor, sp.Basic):
        return valor
    valor = float(valor)
    if not np.isfinite(valor):
        raise ValueError(f"Valor no finito: {valor}")
    if valor.is_integer():
        return sp.Integer(int(valor))
    tolerancia = 1e-12 * max(1.0, abs(valor))

    def racional_simple(x):
        fraccion = Fraction(x).limit_denominator(_DENOMINADOR_MAXIMO)
        if abs(float(fraccion) - x) <= tolerancia and fraccion != 0:
            return sp.Rational(fraccion.numerator, fraccion.denominator)
        return None

    racional = racional_simple(valor)
    if racional is not None:
        return racional
    multiplo = racional_simple(valor / np.pi)
    if multiplo is not None and abs(float(multiplo * sp.pi) - valor) <= tolerancia:
        return multiplo * sp.pi
    cuadrado = racional_simple(valor * valor)
    if cuadrado is not None and abs(float(sp.sqrt(cuadrado)) - abs(valor)) <= tolerancia:
        return sp.sign(valor) * sp.sqrt(cuadrado)
    return sp.Rational(repr(valor))


def racionalizar(expresion):
    """0.5·x → x/2: los decimales escritos en una ecuación pasan a racionales exactos.

    Un método analítico con flotantes deja de ser exacto (sympy no simplifica
    3.333·x/x a un número limpio, ni reconoce 0.5 como 1/2 al factorizar). Se
    usa el decimal tal como se escribió, no una aproximación.
    """
    expresion = sp.sympify(expresion)
    if not expresion.has(sp.Float):
        return expresion
    return expresion.xreplace({f: sp.Rational(repr(float(f))) for f in expresion.atoms(sp.Float)})


def nombre_derivada(base: sp.Symbol, orden: int, independiente: sp.Symbol) -> sp.Symbol:
    """Símbolo de presentación de la derivada: θ̇ si la variable es t, y' si no."""
    nombre = base.name
    if independiente.name == "t" and orden <= 2 and "_" not in nombre and not nombre[-1].isdigit():
        return sp.Symbol(nombre + ("dot" if orden == 1 else "ddot"), real=True)
    return sp.Symbol(nombre + "'" * orden, real=True)


@dataclass
class Problema:
    """Un problema ya interpretado. Lo consumen la clasificación y las familias."""

    tipo: str                                   # "edo", "mapa" o "teorico" (sin ecuación)
    x: sp.Symbol                                # variable independiente
    estados: list                               # símbolos del estado
    campo: list                                 # F, con los parámetros numéricos sustituidos
    parametros: dict = field(default_factory=dict)       # nombre -> valor numérico
    parametro: sp.Symbol | None = None          # el parámetro que queda simbólico
    valor_parametro: float | None = None        # su valor representativo, si se dio
    rango_parametro: tuple | None = None        # (inferior, superior), None = no acotado
    ci: tuple | None = None                     # (x0, [y0, ...])
    intervalo: tuple | None = None
    region: dict = field(default_factory=dict)  # símbolo -> (inferior, superior)
    pedidos: set = field(default_factory=set)
    metodo_pedido: str | None = None
    solucion_particular: sp.Expr | None = None
    enunciado: str | None = None
    trozos: list | None = None                  # mapas: [(expresion, desde, hasta)]
    separacion_inicial: float | None = None
    textos: list = field(default_factory=list)  # las ecuaciones tal como llegaron
    #: Datos numéricos del enunciado que no son parámetros del campo: r₁, r₂ y δ
    #: de Feigenbaum, los exponentes de Kaplan-Yorke, las copias y la razón de un
    #: fractal autosemejante.
    datos: dict = field(default_factory=dict)
    #: Sección de Poincaré: {"variable", "valor", "sentido"}.
    seccion: dict | None = None
    #: El campo con TODOS los parámetros como símbolos (positivos si su valor
    #: lo es): el 4.4 demuestra la disipatividad para σ, r, b > 0 genéricos y
    #: solo al final sustituye los valores canónicos.
    campo_simbolico: list = field(default_factory=list)
    simbolos_parametros: dict = field(default_factory=dict)   # nombre -> Symbol

    # -- forma ----------------------------------------------------------------

    @property
    def dimension(self) -> int:
        return len(self.estados)

    @property
    def autonomo(self) -> bool:
        return not any(self.x in sp.sympify(e).free_symbols for e in self.campo)

    @property
    def es_compania(self) -> bool:
        """x1' = x2, ..., x_{n-1}' = x_n: el sistema es una EDO escalar de orden n."""
        if self.tipo != "edo" or self.dimension < 2:
            return False
        return all(sp.simplify(self.campo[i] - self.estados[i + 1]) == 0
                   for i in range(self.dimension - 1))

    @property
    def orden(self) -> int:
        return self.dimension if self.es_compania else 1

    def derivadas_mostradas(self) -> list:
        """[y, y', y'', ...] con los nombres de presentación de la forma compañera."""
        base = self.estados[0]
        return [base] + [nombre_derivada(base, k, self.x) for k in range(1, self.dimension)]

    def a_presentacion(self, expresion):
        """Reescribe una expresión del estado con y', y'' en vez de los nombres internos."""
        if not self.es_compania:
            return expresion
        cambio = dict(zip(self.estados[1:], self.derivadas_mostradas()[1:]))
        return sp.sympify(expresion).subs(cambio, simultaneous=True)

    # -- parámetro ------------------------------------------------------------

    @property
    def tiene_parametro(self) -> bool:
        return self.parametro is not None and any(
            self.parametro in sp.sympify(e).free_symbols for e in self.campo)

    def valor_representativo(self) -> float | None:
        """Valor del parámetro simbólico para integrar y graficar."""
        if self.parametro is None:
            return None
        if self.valor_parametro is not None:
            return float(self.valor_parametro)
        inferior, superior = self.rango_parametro or (None, None)
        if inferior is not None and superior is not None:
            return 0.5 * (inferior + superior)
        if inferior is not None:
            return float(inferior) + 1.0
        if superior is not None:
            return float(superior) - 1.0
        return 1.0

    def valores_simbolicos(self) -> dict:
        """Símbolo de `campo_simbolico` → valor exacto, para sustituir al final."""
        return {simbolo: exacto(self.parametros[nombre]) for nombre, simbolo in self.simbolos_parametros.items()
                if nombre in self.parametros and simbolo != self.parametro}

    def campo_con(self, valor=None) -> list:
        """El campo con el parámetro simbólico fijado en `valor` (o el representativo)."""
        if self.parametro is None:
            return list(self.campo)
        valor = self.valor_representativo() if valor is None else valor
        return [sp.sympify(e).subs(self.parametro, exacto(valor)) for e in self.campo]

    # -- numérico -------------------------------------------------------------

    def campo_numerico(self, valor=None):
        """f(t, y, parametros) para `modelo_edos.resolver_edo`, todo numérico.

        El tercer argumento existe por compatibilidad con la firma del
        integrador; los valores ya están dentro de las expresiones.
        """
        expresiones = self.campo_con(valor)
        funcion = sp.lambdify([self.x, self.estados], expresiones, "numpy")

        def campo(t, y, parametros=None):
            return np.asarray(funcion(t, list(y)), dtype=float)

        campo.expresiones = tuple(expresiones)
        campo.variables_estado = tuple(s.name for s in self.estados)
        campo.variable_independiente = self.x.name
        campo.parametros = ()
        return campo

    # -- descripción ----------------------------------------------------------

    def sistema_latex(self) -> list[str]:
        """Las ecuaciones del sistema en LaTeX, con el parámetro simbólico visible."""
        from matematica.desarrollo import L
        lineas = []
        for estado, expresion in zip(self.estados, self.campo):
            derivada = nombre_derivada(estado, 1, self.x) if self.tipo == "edo" else None
            izquierda = L(derivada) if derivada is not None else L(estado) + r"_{n+1}"
            lineas.append(f"{izquierda} = {L(expresion)}")
        return lineas


def construir_problema(*, ecuaciones, variables_estado, variable_independiente="t",
                       parametros=None, parametro=None, rango_parametro=None,
                       y0=None, intervalo=None, region=None, pedidos=(),
                       metodo=None, solucion_particular=None, enunciado=None,
                       tipo_de_sistema="edo_continua", trozos=None,
                       separacion_inicial=None, datos=None, seccion=None) -> Problema:
    """Interpreta una solicitud ya validada por `orquestacion.contratos`.

    Sin ecuaciones el problema es "teórico" (la dimensión del conjunto de
    Cantor, la herradura de Smale, una estimación con datos): no hay campo y las
    familias trabajan con el enunciado y `datos`.

    Levanta `ExpresionInvalida` si una expresión no se puede aceptar.
    """
    parametros = {str(k): float(v) for k, v in (parametros or {}).items()}
    if not ecuaciones and not trozos:
        x = simbolos([variable_independiente], real=True)[variable_independiente]
        return Problema(tipo="teorico", x=x, estados=[], campo=[], parametros=parametros,
                        pedidos=set(pedidos or ()), metodo_pedido=metodo, enunciado=enunciado,
                        datos=dict(datos or {}), seccion=seccion)
    if len(variables_estado) > MAX_DIMENSION:
        raise ExpresionInvalida(f"El proyecto admite sistemas de hasta {MAX_DIMENSION} variables.")

    # El parámetro simbólico hereda supuestos del rango que declare el cliente:
    # ω₀ ∈ [0, ∞) permite que sqrt(ω₀²) = ω₀, que es lo que escribe el balotario.
    supuestos_parametro = {"real": True}
    if rango_parametro is not None:
        inferior = rango_parametro[0]
        if inferior is not None and inferior > 0:
            supuestos_parametro = {"positive": True}
        elif inferior is not None and inferior == 0:
            supuestos_parametro = {"nonnegative": True}

    nombres_parametros = list(dict.fromkeys(
        [*parametros, *([parametro] if parametro else [])]))
    x = simbolos([variable_independiente], real=True)[variable_independiente]
    estados = simbolos(variables_estado, real=True)
    simbolos_parametros = {}
    for nombre in nombres_parametros:
        supuestos = supuestos_parametro if nombre == parametro else {"real": True}
        simbolos_parametros.update(simbolos([nombre], **supuestos))
    todos = {variable_independiente: x, **estados, **simbolos_parametros}
    if len(todos) != 1 + len(estados) + len(simbolos_parametros):
        raise ExpresionInvalida("Un nombre se repite entre variables y parámetros.")

    sustitucion = {simbolos_parametros[n]: exacto(v) for n, v in parametros.items()
                   if n != parametro}
    tipo = "mapa" if tipo_de_sistema == "mapa_discreto" else "edo"

    piezas = None
    if trozos:
        estado = estados[variables_estado[0]]
        piezas = []
        for trozo in trozos:
            expresion = racionalizar(parsear(trozo["expresion"], todos).subs(sustitucion))
            piezas.append((expresion, exacto(trozo["desde"]), exacto(trozo["hasta"])))
        piezas.sort(key=lambda p: float(p[1]))
        campo = [sp.Piecewise(*[(e, (estado >= a) & (estado <= b)) for e, a, b in piezas],
                              (sp.nan, True))]
    else:
        campo = [racionalizar(parsear(texto, todos).subs(sustitucion)) for texto in ecuaciones]

    # El mismo campo con los parámetros como símbolos: positivos si su valor lo
    # es, que es lo que permite a sympy decidir el signo de −2σr o de −(σ+1+b).
    simbolicos = {}
    for nombre in nombres_parametros:
        if nombre == parametro:
            simbolicos[nombre] = simbolos_parametros[nombre]
        elif parametros.get(nombre, 0) > 0:
            simbolicos[nombre] = sp.Symbol(nombre, positive=True)
        else:
            simbolicos[nombre] = sp.Symbol(nombre, real=True)
    cambio = {simbolos_parametros[n]: simbolicos[n] for n in nombres_parametros}
    campo_simbolico = ([racionalizar(parsear(texto, todos)).xreplace(cambio) for texto in ecuaciones]
                       if not trozos else list(campo))

    particular = None
    if solucion_particular:
        particular = racionalizar(parsear(solucion_particular, todos).subs(sustitucion))

    simbolo_parametro = simbolos_parametros.get(parametro) if parametro else None
    ci = None
    if y0 is not None and intervalo is not None:
        ci = (exacto(intervalo[0]), [exacto(v) for v in y0])

    limites = {}
    for nombre, (inferior, superior) in (region or {}).items():
        if nombre not in estados:
            raise ExpresionInvalida(f"La región menciona {nombre!r}, que no es una variable de estado.")
        limites[estados[nombre]] = (inferior, superior)

    return Problema(
        tipo=tipo, x=x, estados=[estados[n] for n in variables_estado], campo=campo,
        parametros=parametros, parametro=simbolo_parametro,
        valor_parametro=parametros.get(parametro) if parametro else None,
        rango_parametro=tuple(rango_parametro) if rango_parametro else None,
        ci=ci, intervalo=tuple(float(v) for v in intervalo) if intervalo else None,
        region=limites, pedidos=set(pedidos or ()), metodo_pedido=metodo,
        solucion_particular=particular, enunciado=enunciado, trozos=piezas,
        separacion_inicial=separacion_inicial, textos=list(ecuaciones or []),
        datos=dict(datos or {}), seccion=seccion, campo_simbolico=campo_simbolico,
        simbolos_parametros=simbolicos)
