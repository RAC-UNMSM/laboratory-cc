"""Contrato público estricto: JSON Schema discriminado por operación."""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=512)]
Var = Literal["x", "y", "z", "t", "u", "v"]
Vec = Annotated[list[Text], Field(min_length=2, max_length=3)]
Vars = Annotated[list[Var], Field(min_length=1, max_length=3)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Function(Strict):
    expresion: Text
    variable: Var = "x"


class Limit(Function):
    operacion: Literal["limite"]
    punto: Text
    direccion: Literal["ambos", "+", "-"] = "ambos"


class Continuity(Function):
    operacion: Literal["continuidad"]
    punto: Text


class Derivative(Function):
    operacion: Literal["derivada"]
    orden: Annotated[int, Field(ge=1, le=6)] = 1


class Extrema(Function):
    operacion: Literal["extremos"]
    inferior: Text
    superior: Text


class Integral(Function):
    operacion: Literal["integral"]
    inferior: Text | None = None
    superior: Text | None = None


class Application(Function):
    operacion: Literal["area", "longitud_arco", "volumen_revolucion"]
    inferior: Text
    superior: Text


class Multi(Strict):
    operacion: Literal["gradiente", "hessiano"]
    expresion: Text
    variables: Vars


class Directional(Strict):
    operacion: Literal["direccional"]
    expresion: Text
    variables: Vars
    punto: Annotated[list[Text], Field(min_length=1, max_length=3)]
    direccion: Annotated[list[Text], Field(min_length=1, max_length=3)]


class Lagrange(Strict):
    operacion: Literal["lagrange"]
    expresion: Text
    variables: Vars
    restriccion: Text


class Bound(Strict):
    variable: Var
    inferior: Text
    superior: Text


class Multiple(Strict):
    operacion: Literal["integral_multiple"]
    expresion: Text
    limites: Annotated[list[Bound], Field(min_length=2, max_length=3)]


class FieldOperation(Strict):
    operacion: Literal["divergencia", "rotacional"]
    campo: Vec


class Line(Strict):
    operacion: Literal["integral_linea"]
    campo: Vec
    curva: Vec
    inferior: Text
    superior: Text


class Surface(Strict):
    operacion: Literal["flujo_superficie"]
    campo: Vec
    superficie: Vec
    limites: Annotated[list[Bound], Field(min_length=2, max_length=2)]


class Green(Strict):
    operacion: Literal["green"]
    campo: Annotated[list[Text], Field(min_length=2, max_length=2)]
    limites: Annotated[list[Bound], Field(min_length=2, max_length=2)]


class Gauss(Strict):
    operacion: Literal["gauss"]
    campo: Annotated[list[Text], Field(min_length=3, max_length=3)]
    limites: Annotated[list[Bound], Field(min_length=3, max_length=3)]


class Stokes(Strict):
    operacion: Literal["stokes"]
    campo: Annotated[list[Text], Field(min_length=3, max_length=3)]
    superficie: Annotated[list[Text], Field(min_length=3, max_length=3)]
    limites: Annotated[list[Bound], Field(min_length=2, max_length=2)]


Problem = Annotated[
    Union[
        Limit,
        Continuity,
        Derivative,
        Extrema,
        Integral,
        Application,
        Multi,
        Directional,
        Lagrange,
        Multiple,
        FieldOperation,
        Line,
        Surface,
        Green,
        Gauss,
        Stokes,
    ],
    Field(discriminator="operacion"),
]
