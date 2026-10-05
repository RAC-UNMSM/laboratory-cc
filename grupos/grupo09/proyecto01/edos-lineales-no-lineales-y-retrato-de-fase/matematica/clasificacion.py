"""Clasificación matemática del problema y selección del método.

Es el paso entre "qué problema es" y "qué procedimiento se le aplica". Cada
familia del balotario sabe reconocerse (`identificar_*` en su módulo); aquí se
pregunta a todas, se registra con cuáles es compatible el problema (y = 3xy² es
separable y también de Bernoulli) y se elige una:

1. si el enunciado o el cliente nombran el método ("Resuelva la ecuación de
   Bernoulli"), ese, siempre que la ecuación tenga de verdad esa forma;
2. si no, por prioridad dentro del tipo de problema;
3. si ninguna familia del balotario aplica, tratamiento numérico, dicho como
   tal.

El alcance también se decide aquí. Las familias implementadas son las que el
balotario desarrolla (Temas 1 a 3 y el problema 4.1). Lo que el balotario
todavía no resuelve (4.2 a 4.5 y el Tema 5) está en `FUERA_DE_ALCANCE` con su
referencia, para responder "todavía no" en lugar de improvisar.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from matematica import (FueraDeAlcance, analisis_bifurcaciones, analisis_caos, conservativos,
                        primer_orden, segundo_orden, sistemas_planos)


@dataclass(frozen=True)
class Familia:
    clave: str
    nombre: str
    tema: str
    balotario: tuple
    identificar: Callable
    desarrollar: Callable
    alias: tuple = ()
    solo_si_se_pide: bool = False

    def a_dict(self):
        return {"familia": self.clave, "nombre": self.nombre, "tema": self.tema,
                "balotario": list(self.balotario)}


def _escalar(f):
    """Adapta un identificador f(campo, x, y) de primer orden al Problema."""
    def identificar(problema):
        if problema.tipo != "edo" or problema.dimension != 1:
            return None
        return f(problema.campo[0], problema.x, problema.estados[0])
    return identificar


def _riccati(problema):
    datos = _escalar(primer_orden.identificar_riccati)(problema)
    if datos is None or datos["q0"] == 0:     # q₀ = 0 es Bernoulli con n = 2
        return None
    return datos


def _conservativo(problema):
    datos = conservativos.identificar_conservativo(problema)
    if datos is None:
        return None
    # Con el parámetro como objeto de estudio y amortiguamiento, no es conservativo.
    return datos


def _hopf(problema):
    return analisis_bifurcaciones.identificar_hopf(problema)


def _no_lineal(problema):
    if sistemas_planos.identificar_lineal_plano(problema) is not None:
        return None
    return sistemas_planos.identificar_no_lineal_plano(problema)


def _ciclo(problema):
    if problema.tipo != "edo" or problema.dimension != 2 or not problema.autonomo:
        return None
    return {}


T1 = "Tema 1 · EDOs lineales y no lineales"
T2 = "Tema 2 · Retratos de fase y análisis cualitativo"
T3 = "Tema 3 · Teoría de bifurcaciones"
T4 = "Tema 4 · Sistemas dinámicos caóticos"

#: Familias del balotario, en orden de prioridad dentro de cada tipo de problema.
FAMILIAS = (
    Familia("bifurcacion_1d", "Bifurcación de equilibrios en 1D", T3, ("3.1", "3.2", "3.3"),
            analisis_bifurcaciones.identificar_bifurcacion_1d, analisis_bifurcaciones.desarrollar_bifurcacion_1d,
            ("bifurcacion", "bifurcaciones", "silla_nodo", "transcritica", "horquilla", "pitchfork",
             "diagrama_de_bifurcacion")),
    Familia("equilibrios_1d", "Equilibrios y línea de fase", T3, ("3.1", "3.2", "3.3"),
            analisis_bifurcaciones.identificar_equilibrios_1d, analisis_bifurcaciones.desarrollar_equilibrios_1d,
            ("linea_de_fase", "linea_fase", "equilibrios_1d"), solo_si_se_pide=True),
    Familia("lineal", "EDO lineal de primer orden", T1, ("1.2",),
            _escalar(primer_orden.identificar_lineal), primer_orden.desarrollar_lineal,
            ("lineal", "lineal_de_primer_orden", "factor_integrante")),
    Familia("separable", "EDO separable", T1, ("1.1",),
            _escalar(primer_orden.identificar_separable), primer_orden.desarrollar_separable,
            ("separable", "variables_separables", "separacion_de_variables")),
    Familia("bernoulli", "Ecuación de Bernoulli", T1, ("1.2",),
            _escalar(primer_orden.identificar_bernoulli), primer_orden.desarrollar_bernoulli,
            ("bernoulli",)),
    Familia("riccati", "Ecuación de Riccati", T1, ("1.4",),
            _riccati, primer_orden.desarrollar_riccati, ("riccati",)),
    Familia("cauchy_euler", "Ecuación de Cauchy-Euler", T1, ("1.3",),
            segundo_orden.identificar_cauchy_euler, segundo_orden.desarrollar_cauchy_euler,
            ("cauchy_euler", "euler", "equidimensional", "variacion_de_parametros")),
    Familia("lineal_plano", "Sistema lineal en el plano", T2, ("2.1", "2.2"),
            sistemas_planos.identificar_lineal_plano, sistemas_planos.desarrollar_lineal_plano,
            ("sistema_lineal", "lineal_plano", "matricial", "autovalores")),
    Familia("conservativo", "Sistema conservativo / hamiltoniano", T2, ("1.5", "2.4"),
            _conservativo, conservativos.desarrollar_conservativo,
            ("conservativo", "energia", "hamiltoniano", "hamiltoniana", "integral_primera", "pendulo")),
    Familia("homoclinica", "Bifurcación homoclínica", T3, ("3.5",),
            analisis_bifurcaciones.identificar_homoclinica, analisis_bifurcaciones.desarrollar_homoclinica,
            ("homoclinica", "melnikov", "bifurcacion_homoclinica"), solo_si_se_pide=True),
    Familia("hopf", "Bifurcación de Hopf", T3, ("3.4",),
            _hopf, analisis_bifurcaciones.desarrollar_hopf, ("hopf",)),
    Familia("ciclo_limite", "Ciclo límite por Poincaré–Bendixson", T2, ("2.5",),
            _ciclo, sistemas_planos.desarrollar_ciclo_limite,
            ("ciclo_limite", "poincare_bendixson", "orbita_periodica", "polares"), solo_si_se_pide=True),
    Familia("no_lineal_plano", "Sistema no lineal en el plano", T2, ("2.3",),
            _no_lineal, sistemas_planos.desarrollar_no_lineal_plano,
            ("no_lineal", "linealizacion", "jacobiano", "equilibrios", "estabilidad")),
    Familia("mapa_1d", "Mapa unidimensional (exponente de Lyapunov)", T4, ("4.1",),
            analisis_caos.identificar_mapa_1d, analisis_caos.desarrollar_mapa_1d,
            ("mapa", "lyapunov", "exponente_de_lyapunov", "tienda")),
)

POR_CLAVE = {f.clave: f for f in FAMILIAS}

#: Pedidos que activan una familia que no se elige por defecto.
PEDIDOS_QUE_ACTIVAN = {
    "equilibrios_1d": {"equilibrios", "estabilidad", "linea_fase"},
    "ciclo_limite": {"ciclo_limite", "orbita_periodica", "poincare_bendixson"},
    "homoclinica": {"homoclinica", "melnikov"},
}

#: Lo que el balotario todavía no desarrolla. Clave → (problema, tema, descripción, palabras).
FUERA_DE_ALCANCE = {
    "duplicacion_de_periodo": ("4.2", T4, "duplicación de periodo del mapa logístico",
                               ("duplicacion de periodo", "periodo 2", "periodo dos", "orbita de periodo")),
    "feigenbaum": ("4.3", T4, "cascada de Feigenbaum y umbral de acumulación",
                   ("feigenbaum", "cascada", "acumulacion caotica", "r_infinito")),
    "disipatividad": ("4.4", T4, "disipatividad y elipsoide atrapante del sistema de Lorenz",
                      ("disipativ", "contraccion de volumen", "elipsoide")),
    "espectro_de_lyapunov": ("4.5", T4, "espectro de exponentes de Lyapunov de un flujo",
                             ("espectro de lyapunov", "exponentes de lyapunov de un flujo")),
    "dimension_fractal": ("5.1", "Tema 5 · Atractores extraños y geometría fractal",
                          "dimensión de caja de conjuntos fractales",
                          ("dimension de caja", "box-counting", "box counting", "cantor", "fractal")),
    "herradura_de_smale": ("5.2", "Tema 5 · Atractores extraños y geometría fractal",
                           "herradura de Smale y dinámica simbólica", ("herradura", "smale")),
    "mapa_de_henon": ("5.3", "Tema 5 · Atractores extraños y geometría fractal",
                      "mapas bidimensionales (Hénon)", ("henon",)),
    "seccion_de_poincare": ("5.4", "Tema 5 · Atractores extraños y geometría fractal",
                            "secciones de Poincaré y mapas de retorno (Rössler)",
                            ("seccion de poincare", "rossler", "mapa de retorno")),
    "dimension_de_lyapunov": ("5.5", "Tema 5 · Atractores extraños y geometría fractal",
                              "dimensión de Kaplan-Yorke", ("kaplan", "yorke", "dimension de lyapunov")),
}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Hénon' y 'henon' son lo mismo para buscar."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def clave_de_metodo(texto: str | None) -> str | None:
    """'Cauchy-Euler', 'variables separables' → clave de familia, o None."""
    if not texto:
        return None
    clave = normalizar(texto).strip().replace("-", "_").replace(" ", "_")
    if clave in ("numerico", "numerica", "solo_numerico"):
        return "numerico"
    for familia in FAMILIAS:
        if clave == familia.clave or clave in familia.alias:
            return familia.clave
    return None


def detectar_fuera_de_alcance(problema) -> dict | None:
    """El tema pedido que el balotario todavía no desarrolla, o None."""
    texto = normalizar(" ".join(filter(None, [problema.enunciado or "", *sorted(problema.pedidos)])))
    for clave, (numero, tema, descripcion, palabras) in FUERA_DE_ALCANCE.items():
        if any(p in texto for p in palabras):
            return {"clave": clave, "problema": numero, "tema": tema, "descripcion": descripcion}
    if problema.tipo == "edo" and ("lyapunov" in texto or "caos" in problema.pedidos):
        numero, tema, descripcion, _ = FUERA_DE_ALCANCE["espectro_de_lyapunov"]
        return {"clave": "espectro_de_lyapunov", "problema": numero, "tema": tema,
                "descripcion": "exponentes de Lyapunov y cuantificación del caos en flujos continuos"}
    if problema.tipo == "mapa" and problema.dimension >= 2:
        numero, tema, descripcion, _ = FUERA_DE_ALCANCE["mapa_de_henon"]
        return {"clave": "mapa_de_henon", "problema": numero, "tema": tema, "descripcion": descripcion}
    if problema.tipo == "mapa" and problema.tiene_parametro:
        numero, tema, descripcion, _ = FUERA_DE_ALCANCE["duplicacion_de_periodo"]
        return {"clave": "duplicacion_de_periodo", "problema": numero, "tema": tema,
                "descripcion": "bifurcaciones de mapas en función de un parámetro"}
    return None


@dataclass
class Clasificacion:
    """Qué es el problema y qué procedimiento se le aplica."""

    familia: Familia | None
    datos: dict = field(default_factory=dict)
    compatibles: list = field(default_factory=list)
    motivo: str = ""
    fuera_de_alcance: dict | None = None
    metodo_rechazado: str | None = None

    @property
    def numerica(self) -> bool:
        return self.familia is None

    def a_dict(self):
        return {
            "familia": self.familia.clave if self.familia else "numerico",
            "nombre": self.familia.nombre if self.familia else "Tratamiento numérico",
            "tema": self.familia.tema if self.familia else None,
            "balotario": list(self.familia.balotario) if self.familia else [],
            "compatibles": [f.clave for f, _ in self.compatibles],
            "motivo": self.motivo,
            "fuera_de_alcance": self.fuera_de_alcance,
            "metodo_rechazado": self.metodo_rechazado,
        }


def clasificar(problema) -> Clasificacion:
    """Elige la familia del balotario que corresponde al problema."""
    fuera = detectar_fuera_de_alcance(problema)
    compatibles = []
    for familia in FAMILIAS:
        try:
            datos = familia.identificar(problema)
        except Exception:                   # un identificador que falla no descarta a los demás
            datos = None
        if datos is not None:
            compatibles.append((familia, datos))
    # Las familias genéricas o que solo se aplican a pedido no "compiten" en la
    # descripción: decir que todo sistema plano es compatible con Poincaré–
    # Bendixson no informa nada.
    pedido_previo = clave_de_metodo(problema.metodo_pedido)
    compatibles = [(f, d) for f, d in compatibles
                   if not f.solo_si_se_pide or pedido_previo == f.clave
                   or problema.pedidos & PEDIDOS_QUE_ACTIVAN.get(f.clave, set())]
    if any(f.clave not in ("no_lineal_plano",) and f.tema == T2 for f, _ in compatibles):
        compatibles = [(f, d) for f, d in compatibles if f.clave != "no_lineal_plano"] or compatibles

    if fuera is not None:
        return Clasificacion(None, compatibles=compatibles, fuera_de_alcance=fuera,
                             motivo=f"Lo pedido corresponde al problema {fuera['problema']} "
                                    f"({fuera['descripcion']}), que el balotario todavía no resuelve.")

    pedido = clave_de_metodo(problema.metodo_pedido)
    rechazado = None
    if pedido == "numerico":
        return Clasificacion(None, compatibles=compatibles,
                             motivo="Se pidió explícitamente el tratamiento numérico.")
    if pedido is not None:
        elegida = next(((f, d) for f, d in compatibles if f.clave == pedido), None)
        if elegida is not None:
            return Clasificacion(elegida[0], elegida[1], compatibles,
                                 motivo=f"El enunciado pide el método: {elegida[0].nombre}.")
        rechazado = POR_CLAVE[pedido].nombre if pedido in POR_CLAVE else problema.metodo_pedido

    for familia, datos in compatibles:
        if familia.solo_si_se_pide:
            activa = PEDIDOS_QUE_ACTIVAN.get(familia.clave, set())
            if not (problema.pedidos & activa) and pedido != familia.clave:
                continue
        motivo = (f"Tiene la forma de: {familia.nombre}." if len(compatibles) == 1 else
                  f"Tiene la forma de {', '.join(f.nombre for f, _ in compatibles)}; se aplica "
                  f"{familia.nombre}, que es el procedimiento que el balotario usa para este tipo.")
        if rechazado:
            motivo = (f"El método pedido ({rechazado}) no corresponde a la forma de la ecuación. "
                      + motivo)
        return Clasificacion(familia, datos, compatibles, motivo=motivo, metodo_rechazado=rechazado)

    motivo = "Ninguna familia del balotario corresponde a esta ecuación: se trata numéricamente."
    if rechazado:
        motivo = f"El método pedido ({rechazado}) no corresponde a la forma de la ecuación. " + motivo
    return Clasificacion(None, compatibles=compatibles, motivo=motivo, metodo_rechazado=rechazado)


def anteponer_clasificacion(d, problema, clasificacion):
    """Primera sección del desarrollo: la ecuación, su forma y el método elegido.

    Es la parte "clasificación → selección del método" del recorrido, escrita
    con los datos que la clasificación calculó, no con una plantilla.
    """
    from matematica.desarrollo import L, Seccion
    from matematica.problema import nombre_derivada
    seccion = Seccion("clasificacion", "Planteamiento y clasificación")
    if problema.tipo == "mapa":
        seccion.formula(r",\quad ".join(problema.sistema_latex()))
    elif problema.es_compania:
        superior = nombre_derivada(problema.estados[0], problema.dimension, problema.x)
        seccion.formula(L(superior), "=", problema.a_presentacion(problema.campo[-1]))
        seccion.texto(f"Ecuación de orden {problema.dimension} escrita como sistema de primer orden "
                      f"({', '.join(s.name for s in problema.estados)}).")
    else:
        for linea in problema.sistema_latex():
            seccion.formula(linea)
    if problema.parametro is not None and problema.tiene_parametro:
        rango = problema.rango_parametro
        texto = f"Parámetro simbólico: {problema.parametro}"
        if rango:
            texto += f" en [{'-∞' if rango[0] is None else rango[0]}, {'∞' if rango[1] is None else rango[1]}]"
        seccion.texto(texto + ".")
    compatibles = [f.nombre for f, _ in clasificacion.compatibles]
    if len(compatibles) > 1:
        seccion.texto("La ecuación tiene la forma de: " + "; ".join(compatibles) + ".")
    seccion.texto(clasificacion.motivo)
    d.secciones.insert(0, seccion)
    d.clasificacion = clasificacion.a_dict()


def alcance_del_problema(identificador: str) -> dict:
    """Si un problema del balotario está dentro del alcance y con qué familias se resuelve."""
    familias = [f.clave for f in FAMILIAS if identificador in f.balotario]
    if familias:
        return {"alcance": "dentro", "familias": familias}
    for numero, tema, descripcion, _ in FUERA_DE_ALCANCE.values():
        if numero == identificador:
            return {"alcance": "fuera_de_alcance", "descripcion": descripcion}
    return {"alcance": "desconocido"}


def inventario():
    """Lo que está dentro y fuera de alcance, para `ping` y la documentación."""
    return {
        "familias": [{**f.a_dict(), "metodo_pedido": list(f.alias[:3])} for f in FAMILIAS],
        "fuera_de_alcance": [{"tema": tema, "problema": numero, "descripcion": descripcion}
                             for numero, tema, descripcion, _ in FUERA_DE_ALCANCE.values()],
    }
