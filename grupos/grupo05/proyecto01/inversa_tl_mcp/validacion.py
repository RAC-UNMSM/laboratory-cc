"""Entradas matemáticas exactas, sin eval ni sympify de texto del usuario."""
import ast
import json
import math
import re

import sympy as sp

MAX_DIM = 8


class ErrorDeEntrada(ValueError):
    """Error que puede explicarse al alumno o al cliente MCP."""


def leer_json(texto, etiqueta):
    if not isinstance(texto, str) or len(texto) > 16000:
        raise ErrorDeEntrada(f"{etiqueta}: se requiere texto JSON de hasta 16000 caracteres.")
    try:
        return json.loads(texto)
    except (ValueError, RecursionError) as exc:
        raise ErrorDeEntrada(f"{etiqueta}: JSON inválido; usa comillas dobles para expresiones.") from exc


def expresion_segura(texto, variables=()):
    """Solo números racionales, variables permitidas y + - * / ** (o ^)."""
    if isinstance(texto, bool) or not isinstance(texto, (str, int, float)):
        raise ErrorDeEntrada("Se esperaba un número o una expresión aritmética.")
    if isinstance(texto, float) and not math.isfinite(texto):
        raise ErrorDeEntrada("Los números deben ser finitos.")
    fuente = str(texto).strip().replace("^", "**")
    if not fuente or len(fuente) > 512:
        raise ErrorDeEntrada("Cada expresión debe contener entre 1 y 512 caracteres.")
    if variables:
        # Notación habitual del proyecto paralelo: 2x1, 2(x1+x2), (x1+x2)/2.
        # Solo se inserta la multiplicación; el mismo AST valida todo después.
        fuente = re.sub(r"(?<=[0-9)])\s*(?=x\d+\b|\()", "*", fuente)
    try:
        arbol = ast.parse(fuente, mode="eval")
    except (SyntaxError, RecursionError) as exc:
        raise ErrorDeEntrada("Expresión inválida; escribe, por ejemplo, 2*x1 + x2/3 o 2x1 + x2/3.") from exc
    if sum(1 for _ in ast.walk(arbol)) > 100:
        raise ErrorDeEntrada("La expresión es demasiado compleja.")
    simbolos = {str(v): v for v in variables}

    def visitar(nodo, profundidad=0):
        if profundidad > 16:
            raise ErrorDeEntrada("Demasiados niveles de operaciones.")
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            try:
                resultado = sp.Rational(str(nodo.value))
            except (ValueError, TypeError) as exc:
                raise ErrorDeEntrada("Número inválido.") from exc
        elif isinstance(nodo, ast.Name) and nodo.id in simbolos:
            resultado = simbolos[nodo.id]
        elif isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.UAdd, ast.USub)):
            a = visitar(nodo.operand, profundidad + 1)
            resultado = -a if isinstance(nodo.op, ast.USub) else a
        elif isinstance(nodo, ast.BinOp):
            a = visitar(nodo.left, profundidad + 1)
            b = visitar(nodo.right, profundidad + 1)
            if isinstance(nodo.op, ast.Add):
                resultado = a + b
            elif isinstance(nodo.op, ast.Sub):
                resultado = a - b
            elif isinstance(nodo.op, ast.Mult):
                if a.free_symbols and b.free_symbols:
                    raise ErrorDeEntrada("La regla no es lineal: no se permiten productos de variables.")
                resultado = a * b
            elif isinstance(nodo.op, ast.Div):
                if not b.is_Rational or b == 0:
                    raise ErrorDeEntrada("Solo se admite división entre constantes racionales no nulas.")
                resultado = a / b
            elif isinstance(nodo.op, ast.Pow):
                if not b.is_Integer or abs(b) > 8:
                    raise ErrorDeEntrada("El exponente debe ser un entero entre -8 y 8.")
                if a.free_symbols and b not in (0,1):
                    raise ErrorDeEntrada("La regla no es lineal: no se permiten potencias de variables.")
                if a == 0 and b < 0:
                    raise ErrorDeEntrada("No se puede dividir entre cero.")
                resultado = a ** int(b)
            else:
                raise ErrorDeEntrada("Operador no permitido.")
        else:
            raise ErrorDeEntrada("Usa solo aritmética y las variables x1, x2, ...; no funciones ni código.")
        if sp.count_ops(resultado) > 100:
            raise ErrorDeEntrada("La expresión es demasiado compleja.")
        if any(abs(int(v.p)).bit_length() > 256 or int(v.q).bit_length() > 256
               for v in resultado.atoms(sp.Rational)):
            raise ErrorDeEntrada("Número demasiado grande para esta herramienta educativa.")
        return resultado

    return sp.expand(visitar(arbol.body))


def matriz_validada(texto, filas=None, columnas=None):
    datos = leer_json(texto, "matriz")
    if not isinstance(datos, list) or not 1 <= len(datos) <= MAX_DIM:
        raise ErrorDeEntrada(f"La matriz debe tener entre 1 y {MAX_DIM} filas.")
    if not all(isinstance(f, list) and 1 <= len(f) <= MAX_DIM for f in datos):
        raise ErrorDeEntrada("La matriz debe ser una lista de filas no vacías.")
    ancho = len(datos[0])
    if any(len(f) != ancho for f in datos):
        raise ErrorDeEntrada("Todas las filas deben tener la misma longitud.")
    if (filas is not None and len(datos) != filas) or (columnas is not None and ancho != columnas):
        raise ErrorDeEntrada(f"Se esperaba una matriz {filas} x {columnas}.")
    return sp.Matrix([[expresion_segura(v) for v in f] for f in datos])


def vector_validado(texto, dimension):
    datos = leer_json(texto, "vector")
    if not isinstance(datos, list) or len(datos) != dimension:
        raise ErrorDeEntrada(f"El vector debe tener {dimension} componentes.")
    return sp.Matrix([expresion_segura(v) for v in datos])


def matriz_de_regla(texto, dimension_entrada, dimension_salida):
    componentes = leer_json(texto, "regla")
    if not isinstance(componentes, list) or len(componentes) != dimension_salida:
        raise ErrorDeEntrada(f"La regla debe tener {dimension_salida} componentes.")
    variables = sp.symbols(f"x1:{dimension_entrada + 1}")
    filas = []
    for componente in componentes:
        expr = expresion_segura(componente, variables)
        coeficientes = [sp.diff(expr, v) for v in variables]
        if any(c.free_symbols for c in coeficientes) or expr != sum(c*v for c,v in zip(coeficientes, variables)):
            raise ErrorDeEntrada("La regla no es lineal: debe tener coeficientes constantes y T(0)=0.")
        filas.append(coeficientes)
    return sp.Matrix(filas)


def especificacion_espacio(texto):
    nombre = str(texto).strip().upper().replace(" ", "").replace("^", "")
    if re.fullmatch(r"R\d+", nombre):
        n = int(nombre[1:]); tipo = "vector"; parametros = (n,)
    elif re.fullmatch(r"P\d+", nombre):
        grado = int(nombre[1:]); n = grado + 1; tipo = "polinomio"; parametros = (grado,)
    elif re.fullmatch(r"M\d+X\d+", nombre):
        p, q = map(int, nombre[1:].split("X")); n = p*q; tipo = "matriz"; parametros = (p, q)
        if p < 1 or q < 1:
            raise ErrorDeEntrada("Las dimensiones de una matriz deben ser positivas.")
    else:
        raise ErrorDeEntrada("Espacio inválido. Ejemplos: R2, P2 (grado <= 2), M2x3.")
    if not 1 <= n <= MAX_DIM:
        raise ErrorDeEntrada(f"La dimensión del espacio debe estar entre 1 y {MAX_DIM}.")
    return {"nombre": nombre.replace("X", "x"), "tipo": tipo, "dimension": n, "parametros": parametros}
