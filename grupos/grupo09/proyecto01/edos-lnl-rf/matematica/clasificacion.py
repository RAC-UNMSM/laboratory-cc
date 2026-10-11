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
balotario desarrolla: los cinco temas, sus 25 problemas. Lo que no pertenece a
ninguno de esos temas (una ecuación en derivadas parciales, una ecuación
estocástica, un sistema de más de tres variables) está en `FUERA_DEL_PROYECTO`,
para responder con un mensaje ordenado que dice qué abarca el proyecto en lugar
de improvisar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from matematica import (analisis_bifurcaciones, analisis_caos, atractores_fractales, caos_en_flujos,
                        conservativos, primer_orden, segundo_orden, sistemas_planos)


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


def _espectro(problema):
    """El 4.5 se pide por su nombre, o como "exponentes de Lyapunov" de un flujo 3D."""
    if problema.tipo == "edo" and problema.dimension == 3 and problema.pedidos & {"lyapunov", "caos"} \
            and problema.autonomo:
        return {}
    return caos_en_flujos.identificar_espectro(problema)


T1 = "Tema 1 · EDOs lineales y no lineales"
T2 = "Tema 2 · Retratos de fase y análisis cualitativo"
T3 = "Tema 3 · Teoría de bifurcaciones"
T4 = "Tema 4 · Sistemas dinámicos caóticos"
T5 = "Tema 5 · Atractores extraños y geometría fractal"

#: Familias del balotario, en orden de prioridad. Las que solo se reconocen
#: cuando el enunciado nombra su tema (Kaplan-Yorke, el espectro, Feigenbaum,
#: la sección de Poincaré, la disipatividad...) van primero: si se piden, son
#: la respuesta, aunque el sistema tenga también otra forma.
FAMILIAS = (
    Familia("kaplan_yorke", "Dimensión de Kaplan-Yorke", T5, ("5.5",),
            atractores_fractales.identificar_kaplan_yorke, atractores_fractales.desarrollar_kaplan_yorke,
            ("kaplan_yorke", "kaplan", "dimension_de_lyapunov")),
    Familia("espectro_lyapunov", "Espectro de Lyapunov de un flujo 3D", T4, ("4.5",),
            _espectro, caos_en_flujos.desarrollar_espectro,
            ("espectro_lyapunov", "espectro", "exponentes_de_lyapunov")),
    Familia("feigenbaum", "Cascada de Feigenbaum", T4, ("4.3",),
            analisis_caos.identificar_feigenbaum, analisis_caos.desarrollar_feigenbaum,
            ("feigenbaum", "cascada", "acumulacion")),
    Familia("dimension_fractal", "Dimensión de caja de un fractal autosemejante", T5, ("5.1",),
            atractores_fractales.identificar_dimension_fractal, atractores_fractales.desarrollar_dimension_fractal,
            ("dimension_fractal", "box_counting", "dimension_de_caja", "cantor")),
    Familia("herradura", "Herradura de Smale", T5, ("5.2",),
            atractores_fractales.identificar_herradura, atractores_fractales.desarrollar_herradura,
            ("herradura", "smale", "dinamica_simbolica")),
    Familia("seccion_poincare", "Sección de Poincaré y mapa de retorno", T5, ("5.4",),
            atractores_fractales.identificar_seccion_poincare, atractores_fractales.desarrollar_seccion_poincare,
            ("seccion_poincare", "seccion_de_poincare", "mapa_de_retorno")),
    Familia("disipatividad", "Flujo disipativo y región atrapante", T4, ("4.4",),
            caos_en_flujos.identificar_disipatividad, caos_en_flujos.desarrollar_disipatividad,
            ("disipatividad", "disipativo", "elipsoide", "region_atrapante")),
    Familia("duplicacion_periodo", "Mapa con parámetro: duplicación de periodo", T4, ("4.2",),
            analisis_caos.identificar_duplicacion_periodo, analisis_caos.desarrollar_duplicacion_periodo,
            ("duplicacion_periodo", "duplicacion_de_periodo", "logistico")),
    Familia("mapa_2d", "Mapa del plano (Hénon)", T5, ("5.3",),
            atractores_fractales.identificar_mapa_2d, atractores_fractales.desarrollar_mapa_2d,
            ("mapa_2d", "henon", "mapa_bidimensional")),
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

#: Los cinco temas del proyecto, para decir con orden qué abarca.
TEMAS = (
    ("Tema 1", "EDOs lineales y no lineales",
     "separables (con intervalo maximal), lineales, Bernoulli, Riccati, Cauchy-Euler y sistemas conservativos "
     "como el péndulo"),
    ("Tema 2", "Retratos de fase y análisis cualitativo en el plano",
     "sistemas lineales y no lineales, equilibrios y su estabilidad, hamiltonianos y ciclos límite"),
    ("Tema 3", "Teoría de bifurcaciones",
     "silla-nodo, transcrítica, horquilla, Hopf y homoclínica"),
    ("Tema 4", "Sistemas dinámicos caóticos",
     "exponente de Lyapunov de mapas, duplicación de periodo, cascada de Feigenbaum, disipatividad de Lorenz "
     "y espectro de Lyapunov de flujos"),
    ("Tema 5", "Atractores extraños y geometría fractal",
     "dimensión de caja de fractales, herradura de Smale, mapa de Hénon, secciones de Poincaré y dimensión de "
     "Kaplan-Yorke"),
)

#: Lo que no pertenece a ninguno de los temas. Clave → (descripción, patrones).
#: Los patrones se buscan en el enunciado sin tildes y en minúsculas.
FUERA_DEL_PROYECTO = {
    "edp": ("ecuaciones en derivadas parciales",
            (r"derivadas parciales", r"\bedps?\b", r"ecuacion del calor", r"ecuacion de (la )?onda",
             r"ecuacion de laplace", r"ecuacion de poisson", r"schrodinger", r"navier")),
    "estocastica": ("ecuaciones diferenciales estocásticas",
                    (r"estocastic", r"browniano", r"ruido blanco", r"proceso de wiener")),
    "retardo": ("ecuaciones diferenciales con retardo", (r"con retardo", r"con retraso", r"\bretardad")),
    "integral": ("ecuaciones integrales e integro-diferenciales",
                 (r"ecuacion(es)? integral", r"integro.?diferencial")),
    # "valor fraccionario" (la dimensión de 5.5) no lo es: solo el cálculo fraccionario.
    "fraccionaria": ("ecuaciones de orden fraccionario",
                     (r"orden fraccionari", r"derivadas? fraccionari", r"calculo fraccionari",
                      r"ecuacion(es)? (diferencial(es)? )?fraccionari")),
    "fourier": ("series y transformadas de Fourier", (r"serie(s)? de fourier", r"transformada de fourier")),
    "control": ("teoría de control", (r"control optimo", r"controlabilidad", r"observabilidad")),
}

#: Métodos de resolución que existen pero que el balotario no trabaja.
METODOS_NO_TRABAJADOS = {
    "laplace": "transformada de Laplace",
    "series_de_potencias": "series de potencias",
    "frobenius": "método de Frobenius",
    "coeficientes_indeterminados": "coeficientes indeterminados",
}


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Hénon' y 'henon' son lo mismo para buscar."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def clave_de_metodo(texto: str | None) -> str | None:
    """'Cauchy-Euler', 'variables separables' → clave de familia, o None.

    Un método conocido que el balotario no trabaja (Laplace, Frobenius) vuelve
    como "no_trabajado:<clave>", para decirlo en vez de ignorarlo.
    """
    if not texto:
        return None
    clave = normalizar(texto).strip().replace("-", "_").replace(" ", "_")
    if clave in ("numerico", "numerica", "solo_numerico"):
        return "numerico"
    for familia in FAMILIAS:
        if clave == familia.clave or clave in familia.alias:
            return familia.clave
    for no_trabajado in METODOS_NO_TRABAJADOS:
        if no_trabajado in clave:
            return f"no_trabajado:{no_trabajado}"
    return None


def describir_alcance() -> list[str]:
    """Una línea por tema: 'Tema 1 — EDOs lineales y no lineales: separables, ...'."""
    return [f"{numero} — {titulo}: {contenido}." for numero, titulo, contenido in TEMAS]


def mensaje_de_alcance(motivo: str | None = None, no_matematico: bool = False) -> str:
    """El mensaje, ordenado por temas, de algo que el proyecto no resuelve."""
    if no_matematico:
        cabeza = ("Esta consulta no es un problema matemático. Este asistente está hecho para resolver, paso a "
                  "paso, los problemas de ecuaciones diferenciales y sistemas dinámicos del balotario del grupo 09.")
        cola = "Si tiene un problema de alguno de estos temas, escríbalo con su ecuación o sus datos."
    else:
        cabeza = ("Problema fuera del alcance de los temas trabajados"
                  + (f": {motivo}." if motivo else ".")
                  + " Queda fuera de las limitaciones del proyecto, así que no se resuelve.")
        cola = "Si su pregunta encaja en uno de estos temas, reformúlela con la ecuación o los datos del problema."
    return "\n".join([cabeza, "El proyecto abarca:", *[f"  • {linea}" for linea in describir_alcance()], cola])


#: Rastros de que un texto es un problema de matemáticas (sin tildes, minúsculas).
_SENALES_MATEMATICAS = re.compile(
    r"ecuacion|derivad|integral|funcion|sistema|matriz|variable|solucion|resuelv|resolver|calcul|demuestr|"
    r"grafi|equilibri|estabilidad|mapa|atractor|caos|lyapunov|fractal|dimension|bifurcacion|orbita|parametro|"
    r"exponente|trayectoria|retrato|fase|edo|lineal|\bdx\b|\bdy\b|\bdt\b|[=^]|\d\s*[+\-*/]\s*\d|\bx\s*\(")


def parece_matematica(texto: str | None) -> bool:
    return bool(texto and _SENALES_MATEMATICAS.search(normalizar(texto)))


def detectar_fuera_de_alcance(problema) -> dict | None:
    """Lo pedido que no pertenece a ninguno de los temas del proyecto, o None."""
    texto = normalizar(problema.enunciado or "")
    for clave, (descripcion, patrones) in FUERA_DEL_PROYECTO.items():
        if any(re.search(p, texto) for p in patrones):
            return {"clave": clave, "descripcion": descripcion,
                    "motivo": f"el enunciado trata de {descripcion}, que no forman parte de los cinco temas"}
    if problema.tipo == "mapa" and problema.dimension >= 3:
        return {"clave": "mapa_3d", "descripcion": "mapas iterados de tres variables",
                "motivo": "el balotario trabaja mapas de una y dos variables, no de tres"}
    if problema.tipo == "mapa" and problema.dimension == 1 and problema.trozos and problema.tiene_parametro:
        return {"clave": "mapa_a_trozos_parametrico", "descripcion": "mapas definidos a trozos con un parámetro simbólico",
                "motivo": "la duplicación de periodo (4.2) se estudia en mapas con una fórmula única; un mapa "
                          "a trozos se analiza con un valor numérico del parámetro (4.1)"}
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
    if fuera is not None:
        return Clasificacion(None, fuera_de_alcance=fuera, motivo=mensaje_de_alcance(fuera["motivo"]))
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

    pedido = clave_de_metodo(problema.metodo_pedido)
    rechazado = None
    if pedido == "numerico":
        return Clasificacion(None, compatibles=compatibles,
                             motivo="Se pidió explícitamente el tratamiento numérico.")
    if pedido is not None and pedido.startswith("no_trabajado:"):
        rechazado = METODOS_NO_TRABAJADOS[pedido.split(":", 1)[1]]
        aviso = (f"El método pedido ({rechazado}) no es uno de los métodos trabajados en el balotario; "
                 "se resuelve con el procedimiento que le corresponde a la forma de la ecuación. ")
        pedido = None
    else:
        aviso = None
    if pedido is not None:
        elegida = next(((f, d) for f, d in compatibles if f.clave == pedido), None)
        if elegida is not None:
            return Clasificacion(elegida[0], elegida[1], compatibles,
                                 motivo=f"El enunciado pide el método: {elegida[0].nombre}.")
        rechazado = POR_CLAVE[pedido].nombre if pedido in POR_CLAVE else problema.metodo_pedido
        aviso = f"El método pedido ({rechazado}) no corresponde a la forma de la ecuación. "

    for familia, datos in compatibles:
        if familia.solo_si_se_pide:
            activa = PEDIDOS_QUE_ACTIVAN.get(familia.clave, set())
            if not (problema.pedidos & activa) and pedido != familia.clave:
                continue
        motivo = (f"Tiene la forma de: {familia.nombre}." if len(compatibles) == 1 else
                  f"Tiene la forma de {', '.join(f.nombre for f, _ in compatibles)}; se aplica "
                  f"{familia.nombre}, que es el procedimiento que el balotario usa para este tipo.")
        if problema.tipo == "teorico":
            motivo = f"El enunciado pregunta por: {familia.nombre} ({familia.tema}, problema {', '.join(familia.balotario)})."
        if aviso:
            motivo = aviso + motivo
        return Clasificacion(familia, datos, compatibles, motivo=motivo, metodo_rechazado=rechazado)

    if problema.tipo == "teorico":
        return Clasificacion(None, compatibles=compatibles, motivo="", fuera_de_alcance={
            "clave": "sin_tema", "descripcion": "una pregunta sin ecuación que no corresponde a ningún tema",
            "motivo": "la pregunta no trae una ecuación y no corresponde a ninguno de los temas del proyecto"})
    motivo = "Ninguna familia del balotario corresponde a esta ecuación: se trata numéricamente."
    if aviso:
        motivo = aviso + motivo
    return Clasificacion(None, compatibles=compatibles, motivo=motivo, metodo_rechazado=rechazado)


def anteponer_clasificacion(d, problema, clasificacion):
    """Primera sección del desarrollo: la ecuación, su forma y el método elegido.

    Es la parte "clasificación → selección del método" del recorrido, escrita
    con los datos que la clasificación calculó, no con una plantilla.
    """
    from matematica.desarrollo import L, Seccion
    from matematica.problema import nombre_derivada
    seccion = Seccion("clasificacion", "Planteamiento y clasificación")
    if problema.tipo == "teorico":
        datos = {k: v for k, v in (problema.datos or {}).items() if v is not None}
        if datos:
            seccion.formula(r",\quad ".join(
                rf"\text{{{k.replace('_', ' ')}}} = {L(v) if not isinstance(v, (list, tuple)) else L(list(v))}"
                for k, v in datos.items()))
    elif problema.tipo == "mapa":
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
    if len(compatibles) > 1 and problema.tipo != "teorico":
        seccion.texto("La ecuación tiene la forma de: " + "; ".join(compatibles) + ".")
    seccion.texto(clasificacion.motivo)
    d.secciones.insert(0, seccion)
    d.clasificacion = clasificacion.a_dict()


def alcance_del_problema(identificador: str) -> dict:
    """Si un problema del balotario está dentro del alcance y con qué familias se resuelve."""
    familias = [f.clave for f in FAMILIAS if identificador in f.balotario]
    if familias:
        return {"alcance": "dentro", "familias": familias}
    return {"alcance": "desconocido"}


def inventario():
    """Lo que el agente resuelve, por temas, y lo que queda fuera del proyecto."""
    return {
        "temas": [{"tema": numero, "titulo": titulo, "contenido": contenido} for numero, titulo, contenido in TEMAS],
        "familias": [{**f.a_dict(), "metodo_pedido": list(f.alias[:3])} for f in FAMILIAS],
        "fuera_del_proyecto": [descripcion for descripcion, _ in FUERA_DEL_PROYECTO.values()]
                              + ["sistemas de más de 3 variables", "mapas iterados de 3 variables"],
        "metodos_no_trabajados": list(METODOS_NO_TRABAJADOS.values()),
    }
