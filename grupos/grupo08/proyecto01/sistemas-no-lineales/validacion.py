from typing import List, Sequence
from resultado import ResultadoMetodo, EstadoMetodo


def validar_entrada(
    expresiones: Sequence[str],
    variables: Sequence[str],
    x0: Sequence[float],
    tolerancia: float,
    max_iter: int
) -> List[str]:
    errores = []

    if not expresiones:
        errores.append("La lista de expresiones no puede estar vacía.")
    if not variables:
        errores.append("La lista de variables no puede estar vacía.")
    if len(expresiones) != len(variables):
        errores.append("El número de expresiones debe coincidir con el número de variables.")
    if not x0:
        errores.append("x0 no puede estar vacío.")
    if len(x0) != len(variables):
        errores.append("La dimensión de x0 debe coincidir con el número de variables.")
    if tolerancia <= 0:
        errores.append("La tolerancia debe ser positiva.")
    if max_iter <= 0:
        errores.append("max_iter debe ser positivo.")

    return errores


def resultado_error(method: str, errores: List[str]) -> ResultadoMetodo:
    return ResultadoMetodo(
        method=method,
        status=EstadoMetodo.INVALID_INPUT,
        warnings=errores,
        message="Parámetros inválidos."
    )