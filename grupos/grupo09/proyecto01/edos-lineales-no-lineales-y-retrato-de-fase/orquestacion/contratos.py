"""Contratos de solicitud y resultado del agente, y conversión a JSON.

Separa dos responsabilidades:

* **Qué puede pedir un cliente** (`SolicitudEDO`, `SolicitudEquilibrios`): se
  valida en la frontera, de modo que un pedido mal formado se rechace antes de
  tocar la matemática.
* **Qué devuelve el agente** (`respuesta_ok` / `respuesta_error`): una forma
  estable, siempre serializable, con la configuración usada incluida para que
  cualquier resultado sea reproducible.

La solicitud describe un **problema**, no solo un problema de valor inicial:
la condición inicial es opcional, porque "halle la solución general" o
"clasifique el equilibrio según γ" no la tienen. Los campos que permiten el
desarrollo matemático (el enunciado, el método que nombra, el parámetro que se
estudia, la región, la solución particular conocida) son opcionales; el
agente funciona sin ellos y los usa cuando llegan.

`serializable` existe porque los objetos que produce la capa matemática
(`OdeResult` de SciPy, `ndarray`, autovalores complejos, `Path`) no pasan a
JSON. Convertirlos es requisito del transporte MCP, no un adorno.
"""

import math
import re
from pathlib import Path
from typing import ClassVar

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from matematica import MAX_DIMENSION

#: Análisis adicionales que se pueden pedir. El desarrollo matemático se hace
#: siempre; esto agrega bloques auxiliares o fuerza un tratamiento.
ANALISIS_DISPONIBLES = ("estabilidad", "solucion_analitica", "bifurcaciones", "caos")

#: Nombres con los que un usuario pide de forma natural algo que el agente
#: agrupa bajo otro nombre.
ALIAS_ANALISIS = {
    "equilibrios": "estabilidad",
    "estabilidad_local": "estabilidad",
    "jacobiano": "estabilidad",
    "autovalores": "estabilidad",
    "retrato_de_fase": "estabilidad",
    "lyapunov": "caos",
    "exponente_de_lyapunov": "caos",
    "sensibilidad": "caos",
    "poincare": "caos",
    "seccion_de_poincare": "caos",
    "atractor": "caos",
    "bifurcacion": "bifurcaciones",
    "diagrama_de_bifurcacion": "bifurcaciones",
    "barrido": "bifurcaciones",
    "barrido_parametrico": "bifurcaciones",
    "hopf": "bifurcaciones",
    "silla_nodo": "bifurcaciones",
    "horquilla": "bifurcaciones",
    "analitica": "solucion_analitica",
    "simbolica": "solucion_analitica",
    "exacta": "solucion_analitica",
    "dsolve": "solucion_analitica",
}

#: Métodos de integración aceptados por scipy.integrate.solve_ivp.
METODOS = ("RK45", "RK23", "DOP853", "Radau", "BDF", "LSODA")

#: Cómo declara el cliente la naturaleza del sistema. `x_{n+1} = r·x_n(1 − x_n)`
#: y `dx/dt = r·x(1 − x)` se escriben con el mismo lado derecho, así que el
#: servidor no puede distinguirlos mirando las ecuaciones; quien lo sabe es el
#: usuario. "no_estoy_seguro" hace que el agente devuelva la pregunta.
TIPOS_DE_SISTEMA = ("edo_continua", "mapa_discreto", "no_estoy_seguro")

#: Nombres de variable independiente que delatan una recurrencia: nadie escribe dx/dn.
INDICES_DISCRETOS = ("n", "k", "i", "j", "m")

#: Variables de estado con sufijo de índice (`x_n`, `theta_k`), propias de una
#: sucesión. Solo la forma explícita con guion bajo, para no confundir `x1`.
_SUFIJO_INDICE = re.compile(r"^[A-Za-z]+_[" + "".join(INDICES_DISCRETOS) + r"]$",
                            re.IGNORECASE)


def serializable(objeto):
    """Convierte recursivamente a tipos que `json.dumps` acepta.

    Los no finitos (NaN, ±inf) se vuelven `None`: JSON estricto no los admite y
    un cliente MCP puede rechazar la respuesta entera por un solo valor.
    """
    if isinstance(objeto, (str, bool, type(None))):
        return objeto
    if isinstance(objeto, (int, np.integer)):
        return int(objeto)
    if isinstance(objeto, (float, np.floating)):
        valor = float(objeto)
        return valor if math.isfinite(valor) else None
    if isinstance(objeto, (complex, np.complexfloating)):
        real, imaginario = float(objeto.real), float(objeto.imag)
        return {"re": real if math.isfinite(real) else None,
                "im": imaginario if math.isfinite(imaginario) else None}
    if isinstance(objeto, np.ndarray):
        return [serializable(v) for v in objeto.tolist()]
    if isinstance(objeto, Path):
        return str(objeto)
    if isinstance(objeto, dict):
        return {str(clave): serializable(valor) for clave, valor in objeto.items()}
    if isinstance(objeto, (list, tuple, set, frozenset)):
        return [serializable(valor) for valor in objeto]
    if hasattr(objeto, "tolist"):          # escalares de numpy que no cayeron arriba
        return serializable(objeto.tolist())
    return str(objeto)


class Trozo(BaseModel):
    """Un tramo de un mapa definido a trozos: f(x) = expresion para desde ≤ x ≤ hasta."""

    expresion: str
    desde: float
    hasta: float

    @model_validator(mode="after")
    def _orden(self):
        if not self.hasta > self.desde:
            raise ValueError("En cada trozo debe ser hasta > desde.")
        return self


class SeccionPoincare(BaseModel):
    """Una sección transversal {variable = valor}, recorrida en un sentido."""

    variable: str
    valor: float = 0.0
    sentido: str = "creciente"

    @field_validator("sentido")
    @classmethod
    def _sentido(cls, valor):
        if valor not in ("creciente", "decreciente"):
            raise ValueError("El sentido de la sección debe ser 'creciente' o 'decreciente'.")
        return valor


class _SolicitudBase(BaseModel):
    """Lo que tienen en común las herramientas: el sistema y el problema."""

    #: Solo la herramienta de caos y fractales admite una pregunta sin ecuación.
    sin_ecuaciones: ClassVar[bool] = False

    ecuaciones: list[str] = Field(
        ..., description="Lado derecho de x'=F(t,x). Una expresión por variable de estado.")
    variables_estado: list[str] = Field(
        ..., description="Nombres de las variables de estado, de 1 a 3.")
    variable_independiente: str = Field(
        "t", description="Nombre de la variable independiente (t, x, ...).")
    parametros: dict[str, float] = Field(
        default_factory=dict, description="Parámetros con nombre que usan las ecuaciones.")
    equilibrios: list[list[float]] | None = Field(
        None, description="Equilibrios a clasificar. Si se omite, se resuelven F(x)=0 exactos.")
    tipo_de_sistema: str = Field(
        "edo_continua",
        description="'edo_continua' para dx/dt = f(x); 'mapa_discreto' para x_{n+1} = f(x_n); "
                    "'no_estoy_seguro' si no se puede determinar.")
    enunciado: str | None = Field(
        None, description="El enunciado del problema tal como lo escribió el usuario.")
    metodo_analitico: str | None = Field(
        None, description="Método que nombra el enunciado: separable, lineal, bernoulli, "
                          "riccati, cauchy_euler, conservativo, lineal_plano, no_lineal, "
                          "ciclo_limite, bifurcacion, hopf, homoclinica, mapa, numerico.")
    pedidos: list[str] | None = Field(
        None, description="Lo que pide el enunciado: solucion_general, intervalo_maximo, "
                          "trayectorias, separatriz, periodo, hamiltoniano, energia, "
                          "equilibrios, ciclo_limite, homoclinica, diagrama_bifurcacion, "
                          "lyapunov, horizonte...")
    parametro: str | None = Field(
        None, description="Parámetro que se estudia de forma simbólica (γ, μ, ω₀).")
    rango_parametro: list[float | None] | None = Field(
        None, description="[mínimo, máximo] del parámetro; null = no acotado.")
    region: dict[str, list[float | None]] | None = Field(
        None, description="Cotas de las variables, p. ej. {'x': [0, null], 'y': [0, null]}.")
    solucion_particular: str | None = Field(
        None, description="Solución particular conocida (Riccati), p. ej. 'x'.")
    trozos: list[Trozo] | None = Field(
        None, description="Mapa definido a trozos: [{expresion, desde, hasta}, ...].")
    separacion_inicial: float | None = Field(
        None, gt=0, description="δ₀ para el horizonte de predictibilidad de un mapa.")
    datos: dict[str, float | list[float]] | None = Field(
        None, description="Datos numéricos del enunciado que no son parámetros del campo: r_1, r_2, delta "
                          "(Feigenbaum), exponentes (Kaplan-Yorke), copias y razon (fractal autosemejante), "
                          "contraccion y expansion (herradura).")
    seccion_poincare: SeccionPoincare | None = Field(
        None, description="Sección de Poincaré: {variable, valor, sentido: creciente|decreciente}.")

    @field_validator("tipo_de_sistema")
    @classmethod
    def _tipo_conocido(cls, valor):
        if valor not in TIPOS_DE_SISTEMA:
            raise ValueError(f"tipo_de_sistema debe ser uno de "
                             f"{', '.join(TIPOS_DE_SISTEMA)}; llegó {valor!r}.")
        return valor

    @field_validator("rango_parametro")
    @classmethod
    def _rango(cls, valor):
        if valor is None:
            return valor
        if len(valor) != 2:
            raise ValueError("rango_parametro debe ser [mínimo, máximo].")
        if valor[0] is not None and valor[1] is not None and valor[1] <= valor[0]:
            raise ValueError("En rango_parametro debe ser máximo > mínimo.")
        return valor

    @model_validator(mode="after")
    def _coherencia_del_sistema(self):
        n = len(self.variables_estado)
        if n == 0 and not (self.sin_ecuaciones and not self.ecuaciones):
            raise ValueError("Debe declarar al menos una variable de estado.")
        if n > MAX_DIMENSION:
            raise ValueError(f"El proyecto admite sistemas de hasta {MAX_DIMENSION} variables.")
        if len(self.ecuaciones) != n:
            raise ValueError(f"Se esperaban {n} ecuaciones (una por variable de estado) "
                             f"y llegaron {len(self.ecuaciones)}.")
        if self.equilibrios is not None:
            for equilibrio in self.equilibrios:
                if len(equilibrio) != n:
                    raise ValueError(f"Cada equilibrio debe tener {n} coordenadas.")
        for nombre, cotas in (self.region or {}).items():
            if nombre not in self.variables_estado:
                raise ValueError(f"La región menciona {nombre!r}, que no es una variable de estado.")
            if len(cotas) != 2:
                raise ValueError("Cada cota de la región debe ser [mínimo, máximo].")
        return self

    def notacion_sugiere_mapa(self):
        """Indicios de que esto es una recurrencia aunque se declare continua."""
        motivos = []
        if self.variable_independiente.lower() in INDICES_DISCRETOS:
            motivos.append(f"la variable independiente es "
                           f"{self.variable_independiente!r}, que es un índice y no "
                           f"un tiempo continuo")
        sufijados = [v for v in self.variables_estado if _SUFIJO_INDICE.match(v)]
        if sufijados:
            motivos.append(f"las variables de estado {sufijados} llevan sufijo de "
                           f"índice, propio de una sucesión")
        return motivos

    def _configuracion_comun(self):
        return {
            "ecuaciones": self.ecuaciones,
            "variable_independiente": self.variable_independiente,
            "variables_estado": self.variables_estado,
            "parametros": self.parametros,
            "parametro": self.parametro,
            "rango_parametro": self.rango_parametro,
            "region": self.region,
            "tipo_de_sistema": self.tipo_de_sistema,
            "metodo_analitico": self.metodo_analitico,
            "pedidos": self.pedidos,
            "enunciado": self.enunciado,
            "trozos": [t.model_dump() for t in self.trozos] if self.trozos else None,
            "datos": self.datos,
            "seccion_poincare": self.seccion_poincare.model_dump() if self.seccion_poincare else None,
        }


class SolicitudEDO(_SolicitudBase):
    """Un problema con EDOs (o un mapa) tal como lo pide un cliente.

    La condición inicial es opcional. Con ella el agente además integra la
    trayectoria y contrasta la solución analítica con la numérica.
    """

    y0: list[float] | None = Field(None, description="Condición inicial, un valor por variable.")
    intervalo: list[float] | None = Field(
        None, description="Par [t_inicial, t_final]; t_inicial es donde vale la condición inicial.")
    analisis: list[str] = Field(
        default_factory=lambda: ["estabilidad"],
        description=f"Análisis adicionales. Disponibles: {', '.join(ANALISIS_DISPONIBLES)}.")
    solucion_exacta: str | None = Field(
        None, description="Solución analítica conocida, para contrastar la numérica.")
    metodo: str = Field("RK45", description=f"Integrador. Opciones: {', '.join(METODOS)}.")
    rtol: float = Field(1e-8, gt=0, description="Tolerancia relativa del integrador.")
    atol: float = Field(1e-10, gt=0, description="Tolerancia absoluta del integrador.")
    puntos: int = Field(400, ge=2, le=200_000,
                        description="Número de puntos de la malla de salida.")
    visualizar: bool = Field(True, description="Generar las figuras.")
    titulo: str | None = Field(None, description="Título para la gráfica y el reporte.")

    @field_validator("metodo")
    @classmethod
    def _metodo_conocido(cls, valor):
        if valor not in METODOS:
            raise ValueError(f"Método desconocido: {valor!r}. Opciones: {', '.join(METODOS)}")
        return valor

    @field_validator("analisis")
    @classmethod
    def _analisis_conocidos(cls, valor):
        """Resuelve alias y rechaza lo que no se reconoce, diciendo qué sí hay."""
        resueltos, desconocidos = [], []
        for pedido in valor:
            clave = str(pedido).strip().lower().replace(" ", "_").replace("-", "_")
            clave = ALIAS_ANALISIS.get(clave, clave)
            if clave in ANALISIS_DISPONIBLES:
                resueltos.append(clave)
            else:
                desconocidos.append(pedido)
        if desconocidos:
            raise ValueError(
                f"Análisis desconocidos: {desconocidos}. "
                f"Disponibles: {', '.join(ANALISIS_DISPONIBLES)}.")
        return list(dict.fromkeys(resueltos))

    @model_validator(mode="after")
    def _coherencia_del_problema(self):
        n = len(self.variables_estado)
        if self.y0 is not None:
            if len(self.y0) != n:
                raise ValueError(f"La condición inicial debe tener {n} valores, "
                                 f"no {len(self.y0)}.")
            if self.intervalo is None:
                raise ValueError("Con condición inicial hace falta el intervalo [t_inicial, "
                                 "t_final]: t_inicial es donde vale la condición.")
        if self.intervalo is not None:
            if len(self.intervalo) != 2:
                raise ValueError("El intervalo debe tener la forma [t_inicial, t_final].")
            if self.intervalo[1] <= self.intervalo[0]:
                raise ValueError("Se requiere t_final > t_inicial.")
        return self

    def configuracion(self):
        """Configuración de cálculo que se adjunta al resultado, para reproducirlo."""
        return serializable({
            **self._configuracion_comun(),
            "y0": self.y0,
            "intervalo": self.intervalo,
            "analisis": self.analisis,
            "metodo": self.metodo,
            "rtol": self.rtol,
            "atol": self.atol,
            "puntos": self.puntos,
        })


class SolicitudEquilibrios(_SolicitudBase):
    """Una pregunta sobre equilibrios, estabilidad o bifurcaciones, sin trayectoria.

    "Clasifique los equilibrios de x' = μ − x²" no es un problema de valor
    inicial: exigir una condición inicial obligaría a integrar una trayectoria
    que nadie pidió.
    """

    def configuracion(self):
        return serializable({**self._configuracion_comun(),
                             "equilibrios_aportados": self.equilibrios})


class SolicitudTema(SolicitudEDO):
    """Una pregunta de caos, fractales o atractores: la ecuación es opcional.

    "Calcule la dimensión de caja del conjunto de Cantor" o "estime r_∞ con
    r₁ = 3 y r₂ = 1 + √6" no tienen ecuación; "demuestre que el sistema de
    Lorenz es disipativo" la trae en el nombre del sistema. El enunciado es lo
    único obligatorio: de él se lee el tema, el sistema nombrado y sus datos.
    """

    sin_ecuaciones: ClassVar[bool] = True

    ecuaciones: list[str] = Field(
        default_factory=list, description="Lado derecho del sistema, si el enunciado da uno.")
    variables_estado: list[str] = Field(
        default_factory=list, description="Variables de estado, si hay ecuaciones.")
    enunciado: str = Field(..., min_length=1, description="El enunciado tal como lo escribió el usuario.")


def respuesta_error(etapa, mensaje, configuracion=None, detalles=None):
    """Resultado de un fallo. No lleva conclusiones, por diseño."""
    return serializable({
        "ok": False,
        "etapa": etapa,
        "error": str(mensaje),
        "detalles": detalles or {},
        "configuracion": configuracion or {},
        "advertencia": "No se emiten conclusiones: la etapa indicada no se superó.",
    })


def respuesta_fuera_de_alcance(mensaje, alcance, configuracion=None, motivo=None, no_matematico=False):
    """Lo pedido no pertenece a los temas del proyecto: se dice, con lo que sí abarca.

    No es un error del servidor ni un fallo de cálculo: `mensaje_para_el_usuario`
    ya está redactado para transmitirlo tal cual, y `alcance` enumera los temas.
    """
    return serializable({
        "ok": False,
        "etapa": "no_es_un_problema_del_proyecto" if no_matematico else "fuera_de_alcance",
        "error": mensaje,
        "mensaje_para_el_usuario": mensaje,
        "motivo": motivo,
        "alcance": alcance,
        "configuracion": configuracion or {},
        "advertencia": "No se resuelve: no pertenece a ninguno de los temas del proyecto. Transmita el mensaje "
                       "al usuario; no lo resuelva por otra vía.",
    })


def respuesta_aclaracion(pregunta, opciones, configuracion=None, motivos=None):
    """Resultado que pide una aclaración al usuario en lugar de adivinar."""
    return serializable({
        "ok": False,
        "etapa": "aclaracion_necesaria",
        "error": pregunta,
        "pregunta_para_el_usuario": pregunta,
        "opciones": opciones,
        "motivos": motivos or [],
        "configuracion": configuracion or {},
        "advertencia": "No se emiten conclusiones: hay que preguntar al usuario antes "
                       "de elegir una interpretación.",
    })


def respuesta_ok(configuracion, solucion, verificacion, analisis=None,
                 visualizacion=None, notas=None, **extra):
    """Resultado completo de un problema resuelto y verificado.

    `extra` lleva el desarrollo matemático, la clasificación y la lectura del
    enunciado: lo que el modelo necesita para presentar la solución sin
    inventar pasos.
    """
    return serializable({
        "ok": True,
        **extra,
        "configuracion": configuracion,
        "solucion": solucion,
        "verificacion": verificacion,
        "analisis": analisis or {},
        "visualizacion": visualizacion or {},
        "notas": notas or [],
    })


def solucion_a_datos(solucion, variables_estado, maximo_puntos=None):
    """Convierte un `OdeResult` de SciPy en datos JSON, submuestreando si hace falta."""
    tiempos = np.asarray(solucion.t, dtype=float)
    estados = np.asarray(solucion.y, dtype=float)
    paso = 1
    if maximo_puntos and tiempos.size > maximo_puntos:
        paso = int(np.ceil(tiempos.size / maximo_puntos))
    return serializable({
        "variables": list(variables_estado),
        "puntos": int(tiempos.size),
        "puntos_enviados": int(tiempos[::paso].size),
        "submuestreo": paso,
        "t": tiempos[::paso],
        "y": {nombre: estados[i, ::paso] for i, nombre in enumerate(variables_estado)},
        "estado_inicial": {nombre: estados[i, 0] for i, nombre in enumerate(variables_estado)},
        "estado_final": {nombre: estados[i, -1] for i, nombre in enumerate(variables_estado)},
    })
