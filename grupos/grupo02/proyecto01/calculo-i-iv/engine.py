"""Despacho cerrado a módulos; cada ejecución valida el contrato nuevamente."""

from models import Problem
from pydantic import TypeAdapter, ValidationError
from tools import (
    calculo_multivariable,
    campos_vectoriales,
    derivadas_optimizacion,
    integrales,
    integrales_aplicaciones,
    integrales_multiples,
    limites_continuidad,
)
from validacion import EntradaError

MODULES = {
    "limite": limites_continuidad,
    "continuidad": limites_continuidad,
    "derivada": derivadas_optimizacion,
    "extremos": derivadas_optimizacion,
    "integral": integrales,
    "area": integrales_aplicaciones,
    "longitud_arco": integrales_aplicaciones,
    "volumen_revolucion": integrales_aplicaciones,
    "gradiente": calculo_multivariable,
    "hessiano": calculo_multivariable,
    "direccional": calculo_multivariable,
    "lagrange": calculo_multivariable,
    "integral_multiple": integrales_multiples,
    "divergencia": campos_vectoriales,
    "rotacional": campos_vectoriales,
    "integral_linea": campos_vectoriales,
    "flujo_superficie": campos_vectoriales,
    "green": campos_vectoriales,
    "stokes": campos_vectoriales,
    "gauss": campos_vectoriales,
}


def solve(payload):
    mode = payload.get("modo", "examen")
    if mode not in ("examen", "paso_a_paso"):
        raise EntradaError("Modo inválido.")
    try:
        p = TypeAdapter(Problem).validate_python(payload["problema"]).model_dump()
    except (ValidationError, KeyError) as exc:
        raise EntradaError(
            "Problema inválido; consulte el esquema de resolver."
        ) from exc
    out = MODULES[p["operacion"]].run(p)
    out["operacion"] = p["operacion"]
    out["modo"] = mode
    if mode == "examen":
        out.pop("pasos", None)
    else:
        out.setdefault("pasos", [])
    out.setdefault("observaciones", [])
    out["observaciones"].append(
        "Los pasos muestran operaciones verificables del motor; no son una derivación completa de sus algoritmos internos."
    )
    return out
