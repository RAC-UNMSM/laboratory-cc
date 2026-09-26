"""Validaciones simples para problemas de valor inicial de EDOs."""

import math


def validar_entrada(modelo, y0, intervalo, parametros=None):
    """Valida un modelo, sus condiciones iniciales, intervalo y parámetros."""
    if not callable(modelo):
        raise TypeError("El modelo debe ser una función f(t, y, parametros).")
    if y0 is None:
        raise ValueError("Debe indicar una condición inicial y0.")
    try:
        estado = [float(valor) for valor in y0]
    except (TypeError, ValueError) as exc:
        raise ValueError("y0 debe ser una secuencia de números.") from exc
    if not estado or not all(math.isfinite(valor) for valor in estado):
        raise ValueError("y0 debe tener al menos un valor numérico finito.")
    if len(estado) > 3:
        raise ValueError("El proyecto admite sistemas de hasta 3 variables.")
    if intervalo is None or len(intervalo) != 2:
        raise ValueError("El intervalo debe tener la forma (t_inicial, t_final).")
    try:
        t0, tf = map(float, intervalo)
    except (TypeError, ValueError) as exc:
        raise ValueError("Los extremos del intervalo deben ser numéricos.") from exc
    if not math.isfinite(t0) or not math.isfinite(tf) or tf <= t0:
        raise ValueError("Se requiere t_final > t_inicial y ambos deben ser finitos.")
    parametros = dict(parametros or {})
    for nombre, valor in parametros.items():
        if not isinstance(nombre, str) or not nombre:
            raise ValueError("Cada parámetro debe tener un nombre de texto.")
        try:
            numero = float(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"El parámetro {nombre!r} debe ser numérico.") from exc
        if not math.isfinite(numero):
            raise ValueError(f"El parámetro {nombre!r} debe ser finito.")
        parametros[nombre] = numero
    return estado, (t0, tf), parametros
