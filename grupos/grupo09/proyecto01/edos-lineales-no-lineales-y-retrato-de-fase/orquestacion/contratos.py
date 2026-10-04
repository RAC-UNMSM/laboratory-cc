"""Contratos de solicitud y resultado del agente, y conversión a JSON.

Separa dos responsabilidades que antes no existían:

* **Qué puede pedir un cliente** (`SolicitudEDO`): se valida en la frontera, de
  modo que un pedido mal formado se rechace antes de tocar el solver.
* **Qué devuelve el agente** (`respuesta_ok` / `respuesta_error`): una forma
  estable, siempre serializable, con la configuración usada incluida para que
  cualquier resultado sea reproducible.

`serializable` existe porque los objetos que produce la capa matemática
(`OdeResult` de SciPy, `ndarray`, autovalores complejos, `Path`) no pasan a
JSON. Convertirlos es requisito del transporte MCP, no un adorno.
"""

import math
import re
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

#: Análisis que el agente sabe ejecutar hoy.
ANALISIS_IMPLEMENTADOS = ("estabilidad",)

#: Análisis que el agente sabe enrutar pero todavía no calcula. Pedirlos es
#: válido: la respuesta dice que están pendientes, en vez de inventar números.
ANALISIS_PENDIENTES = ("caos", "bifurcaciones", "solucion_analitica")

#: Todo lo que `analisis` acepta.
ANALISIS_DISPONIBLES = ANALISIS_IMPLEMENTADOS + ANALISIS_PENDIENTES

#: Nombres con los que un usuario pide de forma natural algo que el agente
#: agrupa bajo otro nombre. Sin esto, pedir "lyapunov" daba un error de
#: nombre desconocido que remitía a "caos", obligando a un segundo intento
#: para enterarse de que tampoco está implementado.
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

#: Tope de variables de estado, heredado de la propuesta del grupo.
MAX_DIMENSION = 3

#: Cómo declara el cliente la naturaleza del sistema.
#:
#: `x_{n+1} = r·x_n(1 - x_n)` y `dx/dt = r·x(1 - x)` se escriben con el mismo
#: lado derecho, así que el servidor no puede distinguirlos mirando las
#: ecuaciones. Quien sí lo sabe es el usuario. Por eso la distinción es un campo
#: del contrato y no una suposición: "no_estoy_seguro" es una respuesta válida
#: que hace que el agente devuelva la pregunta en vez de un número.
TIPOS_DE_SISTEMA = ("edo_continua", "mapa_discreto", "no_estoy_seguro")

#: Nombres de variable independiente que delatan una recurrencia en vez de un
#: flujo continuo: nadie escribe dx/dn. Sirven para detectar un mapa declarado
#: por error como EDO continua.
INDICES_DISCRETOS = ("n", "k", "i", "j", "m")

#: Variables de estado con sufijo de índice (`x_n`, `theta_k`), propias de una
#: sucesión. Solo la forma explícita con guion bajo, para no confundir `x1` y
#: `x2`, que son nombres habituales de componentes de un sistema continuo.
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


class SolicitudEDO(BaseModel):
    """Un problema de valor inicial tal como lo pide un cliente.

    Ejemplo mínimo: ecuaciones=["-2*y"], variables_estado=["y"], y0=[1.0],
    intervalo=[0.0, 5.0].
    """

    ecuaciones: list[str] = Field(
        ..., description="Lado derecho de x'=F(t,x). Una expresión por variable de estado.")
    variables_estado: list[str] = Field(
        ..., description="Nombres de las variables de estado, en el mismo orden que las ecuaciones.")
    y0: list[float] = Field(..., description="Condición inicial, un valor por variable.")
    intervalo: list[float] = Field(
        ..., description="Par [t_inicial, t_final] con t_final > t_inicial.")
    variable_independiente: str = Field(
        "t", description="Nombre de la variable independiente (t, x, ...).")
    parametros: dict[str, float] = Field(
        default_factory=dict, description="Parámetros con nombre que usan las ecuaciones.")
    analisis: list[str] = Field(
        default_factory=lambda: ["estabilidad"],
        description=f"Análisis solicitados. Disponibles: {', '.join(ANALISIS_DISPONIBLES)}.")
    equilibrios: list[list[float]] | None = Field(
        None, description="Equilibrios a clasificar. Si se omite, se buscan numéricamente.")
    solucion_exacta: str | None = Field(
        None, description="Solución analítica conocida, para contrastar la numérica.")
    metodo: str = Field("RK45", description=f"Integrador. Opciones: {', '.join(METODOS)}.")
    rtol: float = Field(1e-8, gt=0, description="Tolerancia relativa del integrador.")
    atol: float = Field(1e-10, gt=0, description="Tolerancia absoluta del integrador.")
    puntos: int = Field(400, ge=2, le=200_000,
                        description="Número de puntos de la malla de salida.")
    visualizar: bool = Field(True, description="Generar la visualización HTML.")
    titulo: str | None = Field(None, description="Título para la gráfica y el reporte.")
    tipo_de_sistema: str = Field(
        "edo_continua",
        description="Cómo planteó el usuario el problema: 'edo_continua' para una "
                    "ecuación diferencial dx/dt = f(x); 'mapa_discreto' para una "
                    "recurrencia x_{n+1} = f(x_n), que está fuera de alcance; "
                    "'no_estoy_seguro' si no se puede determinar, y entonces el "
                    "servidor devuelve la pregunta que hay que hacerle al usuario "
                    "en vez de un resultado.")

    @field_validator("tipo_de_sistema")
    @classmethod
    def _tipo_conocido(cls, valor):
        if valor not in TIPOS_DE_SISTEMA:
            raise ValueError(f"tipo_de_sistema debe ser uno de "
                             f"{', '.join(TIPOS_DE_SISTEMA)}; llegó {valor!r}.")
        return valor

    def notacion_sugiere_mapa(self):
        """Indicios de que esto es una recurrencia aunque se declare continua.

        Nadie escribe dx/dn: si la variable independiente es un índice, o las
        variables de estado llevan sufijo de índice, lo más probable es que el
        usuario haya planteado un mapa iterado.
        """
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
                f"Implementados: {', '.join(ANALISIS_IMPLEMENTADOS)}. "
                f"Reconocidos pero pendientes de implementación: "
                f"{', '.join(ANALISIS_PENDIENTES)}.")
        return list(dict.fromkeys(resueltos))

    @model_validator(mode="after")
    def _coherencia(self):
        n = len(self.variables_estado)
        if n == 0:
            raise ValueError("Debe declarar al menos una variable de estado.")
        if n > MAX_DIMENSION:
            raise ValueError(f"El proyecto admite sistemas de hasta {MAX_DIMENSION} variables.")
        if len(self.ecuaciones) != n:
            raise ValueError(f"Se esperaban {n} ecuaciones (una por variable de estado) "
                             f"y llegaron {len(self.ecuaciones)}.")
        if len(self.y0) != n:
            raise ValueError(f"La condición inicial debe tener {n} valores, "
                             f"no {len(self.y0)}.")
        if len(self.intervalo) != 2:
            raise ValueError("El intervalo debe tener la forma [t_inicial, t_final].")
        if self.intervalo[1] <= self.intervalo[0]:
            raise ValueError("Se requiere t_final > t_inicial.")
        if self.equilibrios is not None:
            for equilibrio in self.equilibrios:
                if len(equilibrio) != n:
                    raise ValueError(f"Cada equilibrio debe tener {n} coordenadas.")
        return self

    def configuracion(self):
        """Configuración de cálculo que se adjunta al resultado, para reproducirlo."""
        return serializable({
            "ecuaciones": self.ecuaciones,
            "variable_independiente": self.variable_independiente,
            "variables_estado": self.variables_estado,
            "y0": self.y0,
            "intervalo": self.intervalo,
            "parametros": self.parametros,
            "analisis": self.analisis,
            "metodo": self.metodo,
            "rtol": self.rtol,
            "atol": self.atol,
            "puntos": self.puntos,
        })


def respuesta_error(etapa, mensaje, configuracion=None, detalles=None):
    """Resultado de un fallo. No lleva conclusiones, por diseño.

    La propuesta exige que si una validación falla el agente informe el problema
    y evite emitir conclusiones basadas en resultados inválidos: esta forma hace
    imposible devolver ambas cosas a la vez.
    """
    return serializable({
        "ok": False,
        "etapa": etapa,
        "error": str(mensaje),
        "detalles": detalles or {},
        "configuracion": configuracion or {},
        "advertencia": "No se emiten conclusiones: la etapa indicada no se superó.",
    })


class SolicitudEquilibrios(BaseModel):
    """Una pregunta sobre equilibrios y estabilidad, sin trayectoria.

    Existe porque "clasifique los equilibrios de x' = mu - x^2" no es un
    problema de valor inicial: no hay condición inicial ni intervalo, y exigirlos
    obligaría a integrar una trayectoria que nadie pidió. Es la forma de los
    problemas del Tema 3 del balotario, que son familias paramétricas.
    """

    ecuaciones: list[str] = Field(
        ..., description="Lado derecho de x'=F(x). Una expresión por variable de estado.")
    variables_estado: list[str] = Field(
        ..., description="Nombres de las variables de estado, de 1 a 3.")
    variable_independiente: str = Field(
        "t", description="Nombre de la variable independiente.")
    parametros: dict[str, float] = Field(
        default_factory=dict,
        description="Valores de los parámetros. Para estudiar una bifurcación, "
                    "repita la llamada variando el parámetro de interés.")
    equilibrios: list[list[float]] | None = Field(
        None, description="Equilibrios a clasificar. Si se omite, se resuelven "
                          "F(x)=0 de forma exacta con sympy.")
    tipo_de_sistema: str = Field(
        "edo_continua",
        description="'edo_continua' o 'mapa_discreto' (fuera de alcance) o "
                    "'no_estoy_seguro' para que el servidor devuelva la pregunta.")

    @field_validator("tipo_de_sistema")
    @classmethod
    def _tipo_conocido(cls, valor):
        if valor not in TIPOS_DE_SISTEMA:
            raise ValueError(f"tipo_de_sistema debe ser uno de "
                             f"{', '.join(TIPOS_DE_SISTEMA)}; llegó {valor!r}.")
        return valor

    @model_validator(mode="after")
    def _coherencia(self):
        n = len(self.variables_estado)
        if n == 0:
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
        return self

    notacion_sugiere_mapa = SolicitudEDO.notacion_sugiere_mapa

    def configuracion(self):
        """Configuración que se adjunta al resultado, para reproducirlo."""
        return serializable({
            "ecuaciones": self.ecuaciones,
            "variable_independiente": self.variable_independiente,
            "variables_estado": self.variables_estado,
            "parametros": self.parametros,
            "equilibrios_aportados": self.equilibrios,
        })


def respuesta_aclaracion(pregunta, opciones, configuracion=None, motivos=None):
    """Resultado que pide una aclaración al usuario en lugar de adivinar.

    Existe porque hay una ambigüedad que el servidor no puede resolver por
    cuenta propia y que cambia la respuesta por completo. Devolver la pregunta
    es más honesto que elegir una interpretación y presentarla como la única.
    """
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
                 visualizacion=None, notas=None):
    """Resultado completo de un análisis superado."""
    return serializable({
        "ok": True,
        "configuracion": configuracion,
        "solucion": solucion,
        "verificacion": verificacion,
        "analisis": analisis or {},
        "visualizacion": visualizacion or {},
        "notas": notas or [],
    })


def solucion_a_datos(solucion, variables_estado, maximo_puntos=None):
    """Convierte un `OdeResult` de SciPy en datos JSON.

    `maximo_puntos` submuestrea la malla cuando la trayectoria es larga, para no
    enviar cientos de miles de números por el transporte; el estado final y el
    conteo original se conservan intactos.
    """
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
