# -*- coding: utf-8 -*-
"""
validacion.py — Módulo de Validación de Entradas Matemáticas
============================================================
Contiene funciones de sanitización, parser de expresiones
y validación de argumentos para evitar inyecciones o errores sintácticos en SymPy.
"""

import re
from typing import Any, Dict


class FormatoEntradaInvalidoError(ValueError):
    """Excepción lanzada cuando una expresión matemática o parámetro es inválido."""
    pass


def validar_expresion_matematica(expresion: str) -> bool:
    """
    Sanea y verifica que la cadena de texto no contenga símbolos prohibidos
    o comandos no seguros antes de ser evaluada por SymPy.
    """
    if not expresion or not isinstance(expresion, str):
        raise FormatoEntradaInvalidoError("La expresión vectorial o función no puede estar vacía.")

    patrones_prohibidos = [r"import", r"eval", r"exec", r"sys", r"os", r"__", r"subprocess"]
    for patron in patrones_prohibidos:
        if re.search(patron, expresion, re.IGNORECASE):
            raise FormatoEntradaInvalidoError(f"La expresión contiene símbolos o palabras no permitidas: {patron}")

    return True


def validar_punto_evaluacion(t0_val: Any) -> str:
    """Valida y normaliza el punto de evaluación t0."""
    t0_str = str(t0_val).strip()
    if not t0_str:
        return "0"
    
    validar_expresion_matematica(t0_str)
    return t0_str


def validar_constantes(constantes: Dict[str, Any] | None) -> Dict[str, float]:
    """Valida que el diccionario de constantes contenga pares clave-valor numéricos."""
    if constantes is None:
        return {}

    if not isinstance(constantes, dict):
        raise FormatoEntradaInvalidoError("El argumento 'constantes' debe ser un diccionario.")

    constantes_validadas = {}
    for clave, valor in constantes.items():
        try:
            constantes_validadas[str(clave)] = float(valor)
        except (ValueError, TypeError):
            raise FormatoEntradaInvalidoError(f"El valor para la constante '{clave}' debe ser un número válido.")

    return constantes_validadas
