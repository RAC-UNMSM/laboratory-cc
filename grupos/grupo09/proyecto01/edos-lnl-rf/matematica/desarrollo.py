"""El desarrollo matemático que realiza la capa matemática, en forma estructurada.

Por qué existe
--------------
Antes el agente integraba, verificaba y devolvía números: cualquier explicación
del procedimiento la redactaba después el modelo de lenguaje, sin que el sistema
hubiera hecho ninguna de esas operaciones. Este módulo es la otra mitad del
cambio: cada familia de problemas (`primer_orden`, `segundo_orden`,
`conservativos`, `sistemas_planos`, `analisis_bifurcaciones`, `analisis_caos`)
**calcula** su procedimiento con sympy/scipy y lo va registrando aquí, de modo
que lo que se presenta es exactamente lo que se calculó.

Dos vistas del mismo cálculo
----------------------------
Un `Desarrollo` guarda el resultado de dos formas, y las dos hacen falta:

* `resultados`: los objetos matemáticos con nombre semántico
  (`factor_integrante`, `autovalores`, `rama_estable`, `coeficiente_lyapunov`).
  Cada familia registra solo los que su método produce: un problema separable
  no tiene Jacobiano y uno de bifurcación no tiene factor integrante. Es lo que
  consultan las pruebas y lo que el modelo puede citar por su nombre.
* `secciones`: el orden en que ese cálculo se lee, como en el balotario. Cada
  sección tiene un título que depende del problema (no hay una plantilla fija
  de "Paso 1, Paso 2") y bloques que son fórmulas obtenidas de objetos sympy,
  no texto escrito a mano.

Nada en este módulo calcula: solo da forma y serializa lo que las familias
calculan.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, is_dataclass
from typing import Any

import numpy as np
import sympy as sp

# ---------------------------------------------------------------------------
# LaTeX y texto a partir de objetos sympy
# ---------------------------------------------------------------------------

#: Opciones de impresión comunes: `ln` como en el balotario y fracciones
#: compactas dentro de exponentes.
_OPCIONES_LATEX = {"ln_notation": True, "fold_short_frac": False}


def L(objeto) -> str:
    """LaTeX de un objeto matemático; las cadenas se toman como LaTeX ya escrito."""
    if isinstance(objeto, str):
        return objeto
    if isinstance(objeto, bool):
        return r"\text{" + ("verdadero" if objeto else "falso") + "}"
    if isinstance(objeto, (int, np.integer)):
        return str(int(objeto))
    if isinstance(objeto, (float, np.floating)):
        return _latex_float(float(objeto))
    if isinstance(objeto, (list, tuple)):
        return r",\; ".join(L(o) for o in objeto)
    try:
        return sp.latex(objeto, **_OPCIONES_LATEX)
    except Exception:                      # objeto que sympy no sabe imprimir
        return r"\text{" + str(objeto) + "}"


def _latex_float(valor: float) -> str:
    if not math.isfinite(valor):
        return r"\infty" if valor > 0 else (r"-\infty" if valor < 0 else r"\text{NaN}")
    if valor == 0:
        return "0"
    if abs(valor) >= 1e5 or abs(valor) < 1e-4:
        mantisa, exponente = f"{valor:.4e}".split("e")
        return rf"{mantisa} \times 10^{{{int(exponente)}}}"
    return f"{valor:.6g}"


def T(objeto) -> str:
    """Forma de texto plano (sintaxis sympy), legible por el modelo y por las pruebas."""
    if isinstance(objeto, str):
        return objeto
    if isinstance(objeto, (float, np.floating)):
        return f"{float(objeto):.10g}"
    try:
        return sp.sstr(objeto)
    except Exception:
        return str(objeto)


def numero(objeto):
    """Valor numérico de un objeto sympy, o None si no lo tiene.

    Real → float; complejo → {"re", "im"}. Sirve para que el JSON lleve el valor
    además de la fórmula, y el modelo no tenga que evaluar `sqrt(2)/2` a mano.
    """
    try:
        if isinstance(objeto, (int, float, np.integer, np.floating)):
            valor = float(objeto)
            return valor if math.isfinite(valor) else None
        if isinstance(objeto, sp.Basic) and objeto.is_number:
            complejo = complex(sp.N(objeto, 15))
            if abs(complejo.imag) < 1e-14 * max(1.0, abs(complejo.real)):
                return complejo.real if math.isfinite(complejo.real) else None
            return {"re": complejo.real, "im": complejo.imag}
    except (TypeError, ValueError):
        return None
    return None


# ---------------------------------------------------------------------------
# Bloques de presentación
# ---------------------------------------------------------------------------

@dataclass
class Formula:
    """Una relación o expresión calculada, en el orden en que se presenta.

    `ref` dice qué entrada de `resultados` muestra la fórmula, de modo que la
    presentación y el dato semántico no puedan contar cosas distintas.
    `destacada` equivale al recuadro (`\\boxed`) del balotario: lo marca la
    plantilla, no el LaTeX.
    """

    latex: str
    texto: str | None = None
    destacada: bool = False
    ref: str | None = None

    def a_dict(self):
        salida = {"tipo": "formula", "latex": self.latex}
        if self.texto:
            salida["texto"] = self.texto
        if self.destacada:
            salida["destacada"] = True
        if self.ref:
            salida["ref"] = self.ref
        return salida


@dataclass
class Texto:
    """Prosa breve que conecta fórmulas. La escribe la familia a partir de lo calculado."""

    texto: str

    def a_dict(self):
        return {"tipo": "texto", "texto": self.texto}


@dataclass
class Rotulo:
    """Encabezado corto dentro de una sección ("Análisis en P₁(0, 0)"), con LaTeX en línea."""

    latex: str

    def a_dict(self):
        return {"tipo": "rotulo", "latex": self.latex}


@dataclass
class Tabla:
    """Tabla de resultados: cada celda es texto o una fórmula (LaTeX)."""

    columnas: list[str]
    filas: list[list[Any]]

    def a_dict(self):
        def celda(valor):
            if isinstance(valor, Formula):
                return {"latex": valor.latex}
            if isinstance(valor, sp.Basic):
                return {"latex": L(valor)}
            return {"texto": str(valor)}
        return {"tipo": "tabla", "columnas": list(self.columnas),
                "filas": [[celda(c) for c in fila] for fila in self.filas]}


def F(*partes, destacada=False, ref=None, texto=None) -> Formula:
    """Construye una fórmula juntando objetos sympy (→ LaTeX) y LaTeX ya escrito.

    `F(lhs, "=", rhs)` es el caso común. Las cadenas son LaTeX literal
    (`r"\\implies"`, `r"\\quad"`), así que no hace falta escapar nada.
    """
    latex = " ".join(L(p) for p in partes)
    if texto is None and all(not isinstance(p, str) or p.strip() in ("=", "<", ">", r"\le", r"\ge")
                             for p in partes):
        texto = " ".join(T(p).replace(r"\le", "<=").replace(r"\ge", ">=") for p in partes)
    return Formula(latex=latex, texto=texto, destacada=destacada, ref=ref)


@dataclass
class Seccion:
    """Una parte del desarrollo con título propio del problema.

    `clave` es estable (las pruebas y la plantilla la usan); `titulo` se lee y
    puede llevar LaTeX en línea entre `$`.
    """

    clave: str
    titulo: str
    bloques: list = field(default_factory=list)

    def formula(self, *partes, destacada=False, ref=None, texto=None) -> Formula:
        bloque = F(*partes, destacada=destacada, ref=ref, texto=texto)
        self.bloques.append(bloque)
        return bloque

    def ecuacion(self, lhs, rhs, *, relacion="=", destacada=False, ref=None) -> Formula:
        return self.formula(lhs, relacion, rhs, destacada=destacada, ref=ref)

    def texto(self, contenido: str) -> Texto:
        bloque = Texto(contenido)
        self.bloques.append(bloque)
        return bloque

    def rotulo(self, *partes) -> Rotulo:
        """Encabezado dentro de la sección; las partes se unen como en `F`."""
        bloque = Rotulo(" ".join(L(p) for p in partes))
        self.bloques.append(bloque)
        return bloque

    def tabla(self, columnas, filas) -> Tabla:
        bloque = Tabla(list(columnas), [list(f) for f in filas])
        self.bloques.append(bloque)
        return bloque

    def a_dict(self):
        return {"clave": self.clave, "titulo": self.titulo,
                "bloques": [b.a_dict() for b in self.bloques]}


@dataclass
class Validacion:
    """Una comprobación hecha sobre el desarrollo, simbólica o numérica.

    `concluyente=False` significa que la comprobación no pudo decidir (por
    ejemplo, sympy no redujo un residuo a cero y el muestreo tampoco lo
    descartó): no cuenta como fallo, pero tampoco como respaldo.
    """

    nombre: str
    ok: bool
    descripcion: str
    medida: float | None = None
    umbral: float | None = None
    detalle: str | None = None
    concluyente: bool = True
    tipo: str = "simbolica"

    def a_dict(self):
        salida = {"nombre": self.nombre, "ok": bool(self.ok),
                  "descripcion": self.descripcion, "tipo": self.tipo,
                  "concluyente": bool(self.concluyente)}
        if self.medida is not None:
            salida["medida"] = a_json(self.medida)
        if self.umbral is not None:
            salida["umbral"] = a_json(self.umbral)
        if self.detalle:
            salida["detalle"] = self.detalle
        return salida


# ---------------------------------------------------------------------------
# El desarrollo
# ---------------------------------------------------------------------------

@dataclass
class Desarrollo:
    """Todo lo que una familia calculó para un problema concreto."""

    familia: str
    nombre: str
    tema: str
    metodo: str
    tratamiento: list[str] = field(default_factory=list)
    balotario: list[str] = field(default_factory=list)
    clasificacion: dict = field(default_factory=dict)
    resultados: dict = field(default_factory=dict)
    secciones: list[Seccion] = field(default_factory=list)
    conclusiones: list[str] = field(default_factory=list)
    validaciones: list[Validacion] = field(default_factory=list)
    graficas: list[dict] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    # -- construcción -------------------------------------------------------

    def seccion(self, clave: str, titulo: str) -> Seccion:
        nueva = Seccion(clave, titulo)
        self.secciones.append(nueva)
        return nueva

    def guardar(self, clave: str, valor):
        """Registra un resultado con nombre y lo devuelve, para usarlo en línea."""
        self.resultados[clave] = valor
        return valor

    def validar(self, nombre, ok, descripcion, **extra) -> Validacion:
        validacion = Validacion(nombre, bool(ok), descripcion, **extra)
        self.validaciones.append(validacion)
        return validacion

    def concluir(self, texto: str):
        self.conclusiones.append(texto)

    def advertir(self, texto: str):
        if texto not in self.advertencias:
            self.advertencias.append(texto)

    def grafica(self, especificacion: dict):
        self.graficas.append(especificacion)

    # -- consulta -----------------------------------------------------------

    def seccion_por_clave(self, clave: str) -> Seccion | None:
        return next((s for s in self.secciones if s.clave == clave), None)

    @property
    def validaciones_ok(self) -> bool:
        return all(v.ok for v in self.validaciones if v.concluyente)

    # -- serialización ------------------------------------------------------

    def a_dict(self, incluir_graficas=False):
        salida = {
            "familia": self.familia,
            "nombre": self.nombre,
            "tema": self.tema,
            "metodo": self.metodo,
            "tratamiento": list(self.tratamiento),
            "balotario": list(self.balotario),
            "clasificacion": a_json(self.clasificacion),
            "secciones": [s.a_dict() for s in self.secciones],
            "resultados": a_json(self.resultados),
            "conclusiones": list(self.conclusiones),
            "validaciones": [v.a_dict() for v in self.validaciones],
            "advertencias": list(self.advertencias),
        }
        if incluir_graficas:
            salida["graficas"] = a_json(self.graficas)
        return salida


def a_json(objeto):
    """Convierte resultados matemáticos a JSON estricto, conservando su LaTeX.

    Un objeto sympy viaja como `{"latex", "texto"}` y, si es un número, con su
    `valor`: el modelo lee la fórmula exacta y el valor sin tener que evaluarla.
    """
    if objeto is None or isinstance(objeto, (str, bool)):
        return objeto
    if isinstance(objeto, (int, np.integer)):
        return int(objeto)
    if isinstance(objeto, (float, np.floating)):
        valor = float(objeto)
        return valor if math.isfinite(valor) else None
    if isinstance(objeto, (complex, np.complexfloating)):
        return {"re": float(objeto.real), "im": float(objeto.imag)}
    if isinstance(objeto, (Formula, Texto, Rotulo, Tabla, Seccion, Validacion)):
        return objeto.a_dict()
    if hasattr(objeto, "a_dict") and callable(objeto.a_dict):
        return objeto.a_dict()
    if isinstance(objeto, sp.MatrixBase):
        salida = {"latex": L(objeto), "texto": T(objeto)}
        try:
            if all(e.is_number for e in objeto):
                salida["valores"] = [[a_json(numero(e)) for e in fila]
                                     for fila in objeto.tolist()]
        except (TypeError, AttributeError):
            pass
        return salida
    if isinstance(objeto, sp.Basic):
        salida = {"latex": L(objeto), "texto": T(objeto)}
        valor = numero(objeto)
        if valor is not None:
            salida["valor"] = valor
        return salida
    if isinstance(objeto, np.ndarray):
        return [a_json(v) for v in objeto.tolist()]
    if isinstance(objeto, dict):
        return {str(k if not isinstance(k, sp.Basic) else T(k)): a_json(v)
                for k, v in objeto.items()}
    if isinstance(objeto, (list, tuple, set, frozenset)):
        return [a_json(v) for v in objeto]
    if is_dataclass(objeto):
        return {k: a_json(v) for k, v in vars(objeto).items() if not k.startswith("_")}
    return str(objeto)


# ---------------------------------------------------------------------------
# Utilidades de presentación compartidas por las familias
# ---------------------------------------------------------------------------

def _envolver(expresion) -> str:
    texto = L(expresion)
    return rf"\left({texto}\right)" if isinstance(expresion, sp.Add) else texto


def suma(*terminos) -> str:
    """LaTeX de t₁ ± t₂ ± ... en el orden dado, sin '+ -' ni '1·y'.

    Cada término es una expresión o un par (coeficiente, factor). Sirve para
    escribir una ecuación en la forma del método (y' + P(x)y = Q(x)yⁿ) sin que
    sympy reordene ni combine los términos, que es justo lo que se quiere
    mostrar antes de simplificar.
    """
    partes = []
    for termino in terminos:
        if isinstance(termino, tuple):
            coeficiente, factor = termino
            coeficiente = sp.sympify(coeficiente)
            # El factor puede ser LaTeX ya escrito (un corchete como en el
            # balotario); solo se convierte si es un objeto matemático.
            if not isinstance(factor, str):
                factor = sp.sympify(factor)
            if coeficiente == 0:
                continue
            negativo = coeficiente.could_extract_minus_sign()
            absoluto = -coeficiente if negativo else coeficiente
            # θ̇·(−ω₀² sin θ) se escribe "− ω₀² sin θ · θ̇", no "+ θ̇ − ω₀² sin θ".
            if not isinstance(factor, str) and factor.could_extract_minus_sign():
                factor = -factor
                negativo = not negativo
            if absoluto == 1:
                cuerpo = L(factor)
            else:
                cuerpo = _envolver(absoluto) + r"\, " + _envolver(factor)
        else:
            expresion = sp.sympify(termino)
            if expresion == 0:
                continue
            negativo = expresion.could_extract_minus_sign()
            cuerpo = L(-expresion if negativo else expresion)
        partes.append((negativo, cuerpo))
    if not partes:
        return "0"
    texto = ("-" if partes[0][0] else "") + partes[0][1]
    for negativo, cuerpo in partes[1:]:
        texto += (" - " if negativo else " + ") + cuerpo
    return texto


def bonita(expresion):
    """Forma de presentación: 2/(2 − 3x²) en vez de −2/(3x² − 2).

    Solo cambia cómo se ve: si cambiar de signo numerador y denominador deja
    menos signos menos a la vista, se cambia. El valor es el mismo.
    """
    expresion = sp.sympify(expresion)
    if isinstance(expresion, sp.Add):
        # Término a término: x + 1/(−x − 1) se lee x − 1/(x + 1).
        terminos = sp.Add.make_args(expresion)
        arreglados = [bonita(t) for t in terminos]
        if any(a is not t for a, t in zip(arreglados, terminos)):
            return sp.Add(*arreglados, evaluate=False)
        return expresion
    numerador, denominador = sp.fraction(sp.together(expresion))
    denominador = sp.expand(denominador)
    if not (numerador.is_number and isinstance(denominador, sp.Add)):
        return expresion

    def signos(num, den):
        return int(bool(num.could_extract_minus_sign())) + sum(
            1 for t in sp.Add.make_args(den) if t.could_extract_minus_sign())

    if signos(-numerador, -denominador) < signos(numerador, denominador):
        return sp.Mul(-numerador, sp.Pow(sp.expand(-denominador), -1, evaluate=False),
                      evaluate=False)
    return expresion


def sustituir_a_la_vista(expresion, variable, valor):
    """La expresión con `variable` reemplazada por "(valor)" sin evaluar: −2/(3(0)² + 2C)."""
    valor = sp.sympify(valor)
    if valor.is_Rational:
        return sp.sympify(expresion).subs(variable, sp.Symbol(f"({valor})"))
    return sp.sympify(expresion).subs(variable, sp.UnevaluatedExpr(valor))


def intervalo_latex(conjunto) -> str:
    """Un conjunto de sympy (Interval, Union) en notación del balotario."""
    if isinstance(conjunto, sp.Interval):
        izquierda = "(" if conjunto.left_open else "["
        derecha = ")" if conjunto.right_open else "]"
        return rf"\left{izquierda}{L(conjunto.start)},\, {L(conjunto.end)}\right{derecha}"
    if isinstance(conjunto, sp.Union):
        return r" \cup ".join(intervalo_latex(a) for a in conjunto.args)
    return L(conjunto)


def intervalo_texto(conjunto) -> str:
    """Un intervalo en texto plano legible: (-sqrt(6)/3, sqrt(6)/3), (0, ∞)."""
    if isinstance(conjunto, sp.Interval):
        def extremo(valor):
            return "∞" if valor == sp.oo else "-∞" if valor == -sp.oo else sp.sstr(valor)
        izquierda = "(" if conjunto.left_open else "["
        derecha = ")" if conjunto.right_open else "]"
        return f"{izquierda}{extremo(conjunto.start)}, {extremo(conjunto.end)}{derecha}"
    if isinstance(conjunto, sp.Union):
        return " ∪ ".join(intervalo_texto(a) for a in conjunto.args)
    return sp.sstr(conjunto)


def punto_latex(coordenadas) -> str:
    return r"\left(" + ",\\, ".join(L(c) for c in coordenadas) + r"\right)"


def signo_texto(valor) -> str:
    """'> 0', '< 0' o '= 0' para un número (sympy o float)."""
    numero_ = numero(valor)
    if isinstance(numero_, dict) or numero_ is None:
        return ""
    if abs(numero_) < 1e-12:
        return "= 0"
    return "> 0" if numero_ > 0 else "< 0"
