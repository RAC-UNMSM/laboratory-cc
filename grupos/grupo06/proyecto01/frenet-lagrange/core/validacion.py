"""
core/validacion.py — CAPA 1 de validación: estructura (Pydantic).

Cada herramienta MCP recibe UN modelo de este archivo. El SDK de MCP genera con él el JSON
Schema que ve el LLM (descripciones, ejemplos, mínimos y máximos) y, antes de ejecutar nada,
valida la petición: si falta un campo, sobra uno o una expresión no se puede interpretar,
la llamada se rechaza con un mensaje claro.

La CAPA 2 (sentido matemático: curvatura cero, función constante, más restricciones que
variables, división por cero, ...) está en ``core/verificador.py``.
"""
from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.utils_math import ErrorEntrada, parsear_seguro, parsear_tupla

__all__ = ["SolicitudLagrange", "SolicitudHessiana", "SolicitudFrenet", "SolicitudDiagnostico",
           "SolicitudConsulta", "SolicitudCombinar", "OpcionesSalida", "MetodoResolucion"]

MetodoResolucion = Literal["auto", "groebner", "solve", "nonlinsolve"]
_IDENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,15}$")
_RESERVADOS = {"pi", "E", "I", "oo", "sin", "cos", "tan", "exp", "log", "ln", "sqrt", "abs", "Abs"}

Expresion = Annotated[str, Field(min_length=1, max_length=400)]
#: Ids de resultado: 8 hex (uuid4) en los nuevos; se aceptan 6 hex de versiones anteriores.
_PATRON_ID = r"^(lagrange|hessiana|frenet)-\d{8}-\d{6}-[0-9a-f]{6}(?:[0-9a-f]{2})?$"


def _expresion_valida(texto: str, campo: str) -> str:
    try:
        parsear_seguro(texto)
    except ErrorEntrada as e:
        raise ValueError(f"{campo}: {e}") from e
    return texto


def _ecuacion_valida(texto: str, campo: str) -> str:
    t = texto.strip()
    for op in ("<=", ">=", "!=", "<", ">"):
        if op in t:
            raise ValueError(f"{campo}: '{t}' es una desigualdad; Lagrange solo admite restricciones de "
                             "IGUALDAD (g = 0). Escribe, por ejemplo, 'x^2 + y^2 = 1'.")
    lados = t.replace("==", "=").split("=")
    if len(lados) > 2:
        raise ValueError(f"{campo}: '{t}' tiene más de un signo '='.")
    for lado in lados:
        if not lado.strip():
            raise ValueError(f"{campo}: a '{t}' le falta un lado de la igualdad.")
        _expresion_valida(lado, campo)
    return t


def _variables_validas(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    if len(set(v)) != len(v):
        raise ValueError("variables: hay nombres repetidos.")
    for nombre in v:
        if not _IDENT.match(nombre) or nombre in _RESERVADOS:
            raise ValueError(f"variables: '{nombre}' no es un nombre válido (usa x, y, z, x1, ...).")
    return v


class OpcionesSalida(BaseModel):
    """Qué archivos generar además del resultado exacto en JSON."""
    model_config = ConfigDict(extra="forbid")

    generar_html: bool = Field(True, description="Genera la página web interactiva (procedimiento en LaTeX, "
                                                 "gráfico 3D dinámico, JSON). Devuelve su ruta.")
    generar_png: bool = Field(True, description="Genera una lámina PNG con los gráficos principales (se publica "
                                                "como imagen Markdown y se adjunta como bloque Image).")
    incluir_imagen: bool = Field(True, description="Adjunta en la respuesta una vista previa PNG (bloque Image) "
                                                   "como respaldo por si el cliente no puede abrir las URLs.")
    offline: bool = Field(False, description="Incrusta Plotly.js en el HTML para verlo sin internet (~5 MB).")
    incluir_datos_grafico: bool = Field(False, description="Incluye en la respuesta los arreglos numéricos de los "
                                                           "gráficos (grandes; normalmente innecesario para el LLM).")


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    salida: OpcionesSalida = Field(default_factory=OpcionesSalida, description="Archivos a generar.")


class SolicitudLagrange(_Base):
    """Optimizar f(x1..xn) sujeta a restricciones de IGUALDAD g_i(x) = 0."""

    funcion: Expresion = Field(..., description="Función objetivo f a maximizar/minimizar. Sintaxis tipo calculadora: "
                                                "'^' potencia, '*' producto (se acepta '2x'), sin, cos, exp, log, sqrt.",
                               examples=["x*y", "x^2 + y^2 + z^2", "x + 2y"])
    restricciones: list[Expresion] = Field(..., min_length=1, max_length=5,
                                           description="Restricciones de igualdad, una por elemento. Pueden escribirse "
                                                       "'x^2 + y^2 = 8' o como expresión igualada a cero 'x^2 + y^2 - 8'.",
                                           examples=[["x^2 + y^2 = 8"], ["x^2 + y^2 = 2", "x + z = 1"]])
    variables: list[str] | None = Field(None, min_length=1, max_length=6,
                                        description="Orden de las variables (opcional; por defecto, orden alfabético). "
                                                    "Todo símbolo que no sea variable se considera un error.",
                                        examples=[["x", "y"], ["x", "y", "z"]])
    metodo: MetodoResolucion = Field("auto", description="Estrategia para resolver el sistema. 'auto' prueba Gröbner "
                                                         "(polinomios), luego solve y nonlinsolve.")

    @field_validator("funcion")
    @classmethod
    def _f(cls, v: str) -> str:
        if "=" in v:
            v = v.split("=", 1)[1].strip()          # 'f(x,y) = x*y' → 'x*y'
        return _expresion_valida(v, "funcion")

    @field_validator("restricciones")
    @classmethod
    def _g(cls, v: list[str]) -> list[str]:
        return [_ecuacion_valida(g, f"restricciones[{i}]") for i, g in enumerate(v)]

    @field_validator("variables")
    @classmethod
    def _v(cls, v: list[str] | None) -> list[str] | None:
        return _variables_validas(v)


class SolicitudHessiana(_Base):
    """Puntos críticos de f(x1..xn) en un dominio abierto (sin restricciones)."""

    funcion: Expresion = Field(..., description="Función f cuyos puntos críticos se buscan y clasifican (máximos, "
                                                "mínimos, sillas). Sintaxis tipo calculadora.",
                               examples=["x^3 + y^3 - 3x*y", "x^4 + y^4 - 4x*y + 1", "x*y*exp(-(x^2+y^2)/2)"])
    variables: list[str] | None = Field(None, min_length=1, max_length=6,
                                        description="Orden de las variables (opcional; por defecto, alfabético).")
    metodo: MetodoResolucion = Field("auto", description="Estrategia para resolver ∇f = 0.")

    @field_validator("funcion")
    @classmethod
    def _f(cls, v: str) -> str:
        if "=" in v:
            v = v.split("=", 1)[1].strip()
        return _expresion_valida(v, "funcion")

    @field_validator("variables")
    @classmethod
    def _v(cls, v: list[str] | None) -> list[str] | None:
        return _variables_validas(v)


class SolicitudFrenet(_Base):
    """Curva parametrizada r(t) en R^2 o R^3 y el punto t0 donde calcular el triedro."""

    curva: list[Expresion] = Field(..., min_length=2, max_length=3,
                                   description="Componentes de r(t): [x(t), y(t)] o [x(t), y(t), z(t)]. "
                                               "También se acepta un solo texto 'cos t, sin t, t'.",
                                   examples=[["cos t", "sin t", "t"], ["t", "t^2", "t^3"]])
    t0: Expresion = Field("0", description="Valor del parámetro donde se evalúan T, N, B, κ, τ y los planos. "
                                           "Admite expresiones exactas: '0', '1', 'pi/4'.")
    parametro: str = Field("t", description="Nombre del parámetro de la curva.")
    constantes: dict[str, float] = Field(default_factory=dict,
                                         description="Valores numéricos SOLO para graficar constantes simbólicas "
                                                     "(las fórmulas quedan generales). Ej: {'a': 2, 'b': 1}.")
    rango: tuple[float, float] | None = Field(None, description="Intervalo [t_min, t_max] a graficar (opcional).")

    @field_validator("curva", mode="before")
    @classmethod
    def _texto_a_lista(cls, v):
        if isinstance(v, str):
            try:
                return [str(c) for c in parsear_tupla(v)]
            except ErrorEntrada as e:
                raise ValueError(f"curva: {e}") from e
        return v

    @field_validator("curva")
    @classmethod
    def _c(cls, v: list[str]) -> list[str]:
        return [_expresion_valida(c, f"curva[{i}]") for i, c in enumerate(v)]

    @field_validator("t0")
    @classmethod
    def _t0(cls, v: str) -> str:
        return _expresion_valida(v, "t0")

    @field_validator("parametro")
    @classmethod
    def _p(cls, v: str) -> str:
        if not _IDENT.match(v) or v in _RESERVADOS:
            raise ValueError(f"parametro: '{v}' no es un nombre válido.")
        return v

    @field_validator("constantes")
    @classmethod
    def _ctes(cls, v: dict[str, float]) -> dict[str, float]:
        for k in v:
            if not _IDENT.match(k):
                raise ValueError(f"constantes: '{k}' no es un nombre válido.")
        return v

    @model_validator(mode="after")
    def _rango_ok(self) -> "SolicitudFrenet":
        if self.rango is not None and not self.rango[0] < self.rango[1]:
            raise ValueError("rango: debe cumplirse t_min < t_max.")
        return self


class SolicitudDiagnostico(BaseModel):
    """Enunciado en lenguaje natural para decidir qué método aplicar."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    enunciado: str = Field(..., min_length=3, max_length=2000,
                           description="Problema tal como lo escribió el usuario, p. ej. 'maximiza xy sobre la "
                                       "circunferencia x^2+y^2=8' o 'curvatura de r(t)=(cos t, sin t, t) en t=0'.")


class SolicitudConsulta(BaseModel):
    """Identificador de un resultado guardado."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id_resultado: str = Field(..., pattern=_PATRON_ID,
                              description="Id devuelto por una herramienta de cálculo, p. ej. "
                                          "'hessiana-20261006-153012-a1b2c3d4'.")




class SolicitudCombinar(BaseModel):
    """Varios resultados ya calculados que se reúnen en UN reporte HTML con navegación."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ids: list[Annotated[str, Field(pattern=_PATRON_ID)]] = Field(
        ..., min_length=1, max_length=30,
        description="id_resultado de cada ejercicio, EN EL ORDEN en que el usuario los planteó "
                    "(el primero será el «Ejercicio 1»).",
        examples=[["lagrange-20261006-184603-938d92ab", "hessiana-20261006-184604-7c577c01"]])
    titulo: str | None = Field(None, max_length=120,
                               description="Título del reporte combinado (opcional), p. ej. 'Práctica 3 — Grupo 06'.")
    enunciados: list[Annotated[str, Field(max_length=600)]] | None = Field(
        None, max_length=30,
        description="Enunciado original de cada ejercicio, en el mismo orden que 'ids' (opcional). "
                    "Se muestra en el índice y en la barra de navegación.")

    @field_validator("ids")
    @classmethod
    def _sin_repetidos(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("ids: hay identificadores repetidos.")
        return v

    @model_validator(mode="after")
    def _mismo_largo(self) -> "SolicitudCombinar":
        if self.enunciados is not None and len(self.enunciados) != len(self.ids):
            raise ValueError("enunciados: debe tener un elemento por cada id (o no enviarse).")
        return self
