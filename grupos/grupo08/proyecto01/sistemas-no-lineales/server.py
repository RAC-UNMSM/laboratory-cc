from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Any
import importlib
import sympy as sp
import numpy as np

from resultado import ResultadoMetodo, EstadoMetodo
from validacion import validar_entrada, resultado_error

mcp = FastMCP("sistemas-no-lineales")


def _compilar_funciones(expresiones: List[str], variables: List[str]):
    simbolos = sp.symbols(' '.join(variables))
    if not isinstance(simbolos, (tuple, list)):
        simbolos = (simbolos,)

    funciones = []
    for expr in expresiones:
        f_sym = sp.sympify(expr)
        f_num = sp.lambdify(simbolos, f_sym, modules=['numpy'])

        def wrapper(x, f_num=f_num):
            return float(f_num(*x))

        funciones.append(wrapper)
    return funciones


def _ejecutar_metodo(
    nombre_metodo: str,
    modulo: str,
    funcion: str,
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float,
    max_iter: int,
) -> Dict[str, Any]:
    errores = validar_entrada(expresiones, variables, x0, tolerancia, max_iter)
    if errores:
        return resultado_error(nombre_metodo, errores).model_dump()

    try:
        funciones = _compilar_funciones(expresiones, variables)
        mod = importlib.import_module(modulo)
        impl = getattr(mod, funcion)
        resultado = impl(funciones, x0, tolerancia, max_iter)
        return resultado.model_dump()
    except ImportError:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[f"Módulo no implementado: {modulo}"],
            message="Método no disponible aún."
        ).model_dump()
    except Exception as e:
        return ResultadoMetodo(
            method=nombre_metodo,
            status=EstadoMetodo.INVALID_INPUT,
            warnings=[str(e)],
            message="Error al ejecutar el método."
        ).model_dump()


@mcp.tool()
def cuasi_newton_broyden(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando el método de Broyden."""
    return _ejecutar_metodo(
        "cuasi_newton_broyden",
        "metodos.cuasi_newton",
        "cuasi_newton_broyden",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def descenso_mas_rapido(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando descenso más rápido."""
    return _ejecutar_metodo(
        "descenso_mas_rapido",
        "metodos.descenso",
        "descenso_mas_rapido",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def newton_sistemas(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando Newton-Raphson."""
    return _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def punto_fijo_varias_variables(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando punto fijo."""
    return _ejecutar_metodo(
        "punto_fijo_varias_variables",
        "metodos.punto_fijo",
        "punto_fijo_varias_variables",
        expresiones, variables, x0, tolerancia, max_iter
    )


@mcp.tool()
def homotopia_continuacion(
    expresiones: List[str],
    variables: List[str],
    x0: List[float],
    tolerancia: float = 1e-8,
    max_iter: int = 100,
) -> Dict[str, Any]:
    """Resuelve un sistema no lineal usando homotopía."""
    return _ejecutar_metodo(
        "homotopia_continuacion",
        "metodos.homotopia",
        "homotopia_continuacion",
        expresiones, variables, x0, tolerancia, max_iter
    )


if __name__ == "__main__":
    mcp.run()