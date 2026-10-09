"""
validacion.py - Validación de entradas con sugerencias ("Tal vez quisiste poner...").

Mantiene las firmas que ya usa server.py:
    validar_y_parsear_expresion(expresion_str)  -> sp.Expr
    validar_limites_numericos(lim_min, lim_max, nombre_var="x")

y agrega validadores para integra_doble_general (variables y fronteras g1, g2).
Todos los errores son ErrorDeEntrada, que hereda de ValueError.
"""
import re
import math
import difflib
import numbers

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, convert_xor, implicit_multiplication,
)

x, y = sp.symbols('x y')
VARIABLES_PERMITIDAS = ('x', 'y')
SIMBOLOS = {'x': x, 'y': y}

FUNCIONES = {
    'sin': sp.sin, 'cos': sp.cos, 'tan': sp.tan, 'cot': sp.cot,
    'sec': sp.sec, 'csc': sp.csc, 'asin': sp.asin, 'acos': sp.acos,
    'atan': sp.atan, 'sinh': sp.sinh, 'cosh': sp.cosh, 'tanh': sp.tanh,
    'exp': sp.exp, 'log': sp.log, 'sqrt': sp.sqrt, 'Abs': sp.Abs,
}
CONSTANTES = {'pi': sp.pi, 'E': sp.E}

# Notación alternativa / en español que se acepta sin quejarse
ALIAS = {
    'sen': 'sin', 'tg': 'tan', 'ctg': 'cot', 'ln': 'log',
    'raiz': 'sqrt', 'raíz': 'sqrt', 'arcsin': 'asin', 'arcsen': 'asin',
    'arccos': 'acos', 'arctan': 'atan', 'arctg': 'atan',
    'abs': 'Abs', 'e': 'E', 'π': 'pi',
}
PALABRAS_NUMERO = {
    'cero': 0, 'uno': 1, 'un': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
    'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
}

LOCAL = {**FUNCIONES, **CONSTANTES, **SIMBOLOS}
TRANSFORMACIONES = standard_transformations + (convert_xor, implicit_multiplication)
ID_RE = re.compile(r'[^\W\d_]+')                 # palabras (letras, incl. ñ, á, π)
CARACTERES_INVALIDOS = r'[^\w\s+\-*/^().]|_'


class ErrorDeEntrada(ValueError):
    """Error de validación: 'Introdujiste mal ... / Tal vez quisiste poner ...'.
    Hereda de ValueError, así que cualquier `except ValueError` existente sigue funcionando."""

    def __init__(self, etiqueta, introducido, problemas, sugerencia=None):
        self.etiqueta = etiqueta
        self.introducido = introducido
        self.problemas = problemas
        self.sugerencia = sugerencia
        msg = f"Introdujiste mal {etiqueta}: '{introducido}'"
        for p in problemas:
            msg += f"\n  - {p}"
        if sugerencia:
            msg += f"\nTal vez quisiste poner: {sugerencia}"
        super().__init__(msg)


# ----------------------------------------------------------------------
# Utilidades internas
# ----------------------------------------------------------------------
def _normalizar(texto):
    t = str(texto).strip()
    for a, b in (('×', '*'), ('·', '*'), ('÷', '/'), ('−', '-'),
                 ('[', '('), (']', ')'), ('{', '('), ('}', ')')):
        t = t.replace(a, b)
    return re.sub(r'(?<=\d),(?=\d)', '.', t)        # 1,5 -> 1.5


def _arreglar_confusiones(texto):
    """'1O' -> '10', 'l5' -> '15' (letras que parecen números)."""
    problemas = []

    def cambiar(m):
        letra = m.group(0)
        num = '0' if letra in 'Oo' else '1'
        problemas.append(f"la letra '{letra}' parece el número {num}")
        return num

    patron = r'(?<=\d)[OolI](?![^\W\d_])|(?<![^\W\d_])[OolI](?=\d)'
    return re.sub(patron, cambiar, texto), problemas


def _arreglar_potencias_pegadas(texto, variables):
    """'x2' -> 'x^2' (sympy lo leería como una variable llamada x2)."""
    problemas = []
    letras = ''.join(variables)
    if not letras:
        return texto, problemas

    def cambiar(m):
        problemas.append(f"'{m.group(0)}' no es válido; ¿quisiste '{m.group(1)}^{m.group(2)}'?")
        return f"{m.group(1)}^{m.group(2)}"

    patron = rf'(?<![\w.])([{letras}{letras.upper()}])(\d+)(?![\w.])'
    return re.sub(patron, cambiar, texto), problemas


def _resolver_identificador(tok, variables, usadas):
    """Devuelve (reemplazo, motivo). motivo=None significa que estaba bien."""
    bajo = tok.lower()
    if tok in FUNCIONES or tok in CONSTANTES:
        return tok, None
    if bajo in variables or bajo in FUNCIONES:
        return bajo, None
    if bajo in ALIAS:
        return ALIAS[bajo], None
    if bajo in PALABRAS_NUMERO:
        return str(PALABRAS_NUMERO[bajo]), "escribiste el número con letras"
    # 'xy' -> x*y (multiplicación implícita, es válido, no se reporta)
    if len(tok) > 1 and variables and all(c in variables for c in bajo):
        return '*'.join(bajo), None
    # 'sinx' -> sin(x): falta el paréntesis
    for f in sorted(FUNCIONES, key=len, reverse=True):
        resto = bajo[len(f):]
        if bajo.startswith(f.lower()) and resto and variables and all(c in variables for c in resto):
            arg = '*'.join(resto)
            return f"{f}({arg})", f"faltan paréntesis; ¿quisiste '{f}({arg})'?"

    candidatos = [*FUNCIONES, *CONSTANTES, *ALIAS, *variables]
    cerca = difflib.get_close_matches(bajo, candidatos, n=1, cutoff=0.7)
    if cerca:
        return ALIAS.get(cerca[0], cerca[0]), "no se reconoce"

    if not variables:
        return None, "aquí solo se admiten números (y constantes como pi), no variables"

    lista = ", ".join(variables)
    if len(tok) == 1:
        libres = [v for v in variables if v not in usadas]
        opciones = libres or list(variables)
        if len(opciones) == 1:
            return opciones[0], f"no es una variable válida (se admiten: {lista})"
        return None, f"no es una variable válida (se admiten: {lista})"
    return None, "no se reconoce como función, constante ni variable"


def _revisar_identificadores(texto, variables):
    usadas = {t.lower() for t in ID_RE.findall(texto) if t.lower() in variables}
    problemas = []

    def sustituir(m):
        tok = m.group(0)
        reemplazo, motivo = _resolver_identificador(tok, variables, usadas)
        if motivo is not None:
            extra = f" -> ¿quisiste '{reemplazo}'?" if reemplazo and "quisiste" not in motivo else ""
            problemas.append(f"'{tok}': {motivo}{extra}")
        return reemplazo if reemplazo is not None else tok

    return ID_RE.sub(sustituir, texto), problemas


def _balancear(texto):
    nivel, salida = 0, []
    for c in texto:
        if c == '(':
            nivel += 1
        elif c == ')':
            if nivel == 0:
                continue                  # paréntesis de cierre sobrante
            nivel -= 1
        salida.append(c)
    return ''.join(salida) + ')' * nivel


def _parsear(texto):
    return parse_expr(texto, local_dict=LOCAL, transformations=TRANSFORMACIONES)


def _sugerencia_valida(texto, variables):
    """Devuelve la sugerencia solo si realmente se puede interpretar."""
    try:
        e = _parsear(texto)
        if isinstance(e, sp.Expr) and {str(s) for s in e.free_symbols} <= set(variables):
            return texto
    except Exception:
        pass
    return None


def _validar_texto(valor, variables, etiqueta):
    original = str(valor)
    if not original.strip():
        raise ErrorDeEntrada(etiqueta, original, ["no escribiste nada"])

    problemas = []
    texto = _normalizar(original)

    invalidos = sorted(set(re.findall(CARACTERES_INVALIDOS, texto)))
    if invalidos:
        problemas.append("caracteres no válidos: " + " ".join(invalidos))
        texto = re.sub(CARACTERES_INVALIDOS, '', texto)

    texto, p = _arreglar_confusiones(texto)
    problemas += p
    texto, p = _arreglar_potencias_pegadas(texto, variables)
    problemas += p
    texto, p = _revisar_identificadores(texto, variables)
    problemas += p

    limpio = re.sub(r'^[*/^\s]+|[+\-*/^\s]+$', '', texto)
    if limpio != texto.strip():
        problemas.append("sobra un operador al inicio o al final")
    texto = limpio

    balanceado = _balancear(texto)
    if balanceado != texto:
        problemas.append("los paréntesis no están balanceados")
        texto = balanceado

    if problemas:
        raise ErrorDeEntrada(etiqueta, original, problemas,
                             _sugerencia_valida(texto, variables))

    try:
        expr = _parsear(texto)
    except Exception:
        raise ErrorDeEntrada(etiqueta, original,
                             ["no pude interpretarlo como una expresión matemática"])
    if not isinstance(expr, sp.Expr):
        raise ErrorDeEntrada(etiqueta, original, ["no es una expresión matemática válida"])
    ajenos = {str(s) for s in expr.free_symbols} - set(variables)
    if ajenos:
        raise ErrorDeEntrada(etiqueta, original,
                             [f"variables no permitidas: {', '.join(sorted(ajenos))}"])
    return expr


def _como_numero(valor, etiqueta, variables_permitidas=()):
    """Convierte un límite (número o texto como '2,5', 'pi/2', 'dos') a objeto SymPy."""
    if isinstance(valor, bool):
        raise ErrorDeEntrada(etiqueta, valor, ["debe ser un número, no un valor lógico"])
    if isinstance(valor, numbers.Real):
        if not math.isfinite(valor):
            raise ErrorDeEntrada(etiqueta, valor, ["debe ser un número finito"])
        return sp.sympify(valor)
    if not isinstance(valor, str):
        raise ErrorDeEntrada(etiqueta, valor, ["debe ser un número"])

    expr = _validar_texto(valor, tuple(variables_permitidas), etiqueta)
    if not expr.free_symbols:
        try:
            v = complex(expr.evalf())
            if v.imag != 0 or not math.isfinite(v.real):
                raise ValueError
        except Exception:
            raise ErrorDeEntrada(etiqueta, valor, ["no se evalúa a un número real finito"])
    return expr


# ----------------------------------------------------------------------
# Funciones públicas
# ----------------------------------------------------------------------
def validar_y_parsear_expresion(expresion_str: str, variables=VARIABLES_PERMITIDAS) -> sp.Expr:
    """Convierte el texto en una expresión SymPy, verificando que solo use las
    variables permitidas. Para una integral simple puedes pasar variables=('x',)."""
    return _validar_texto(expresion_str, tuple(variables), "la expresión")


def validar_limites_numericos(lim_min, lim_max, nombre_var: str = "x"):
    """Valida que ambos límites sean números (acepta '2,5', 'pi/2', 'dos', etc.)
    y que lim_min < lim_max. Devuelve (lim_min, lim_max) como float."""
    a = _como_numero(lim_min, f"el límite inferior de {nombre_var}")
    b = _como_numero(lim_max, f"el límite superior de {nombre_var}")
    va, vb = float(a), float(b)

    if va > vb:
        sug = f"límite inferior = {lim_max} y límite superior = {lim_min}"
        if -va < vb:
            sug += f"\n   (o, si solo olvidaste un signo: límite inferior = {sp.sstr(-a)})"
        raise ErrorDeEntrada(
            f"los límites de {nombre_var}", f"{lim_min} y {lim_max}",
            ["el límite inferior es mayor que el superior"], sug)
    if va == vb:
        raise ErrorDeEntrada(
            f"los límites de {nombre_var}", f"{lim_min} y {lim_max}",
            ["los dos límites son iguales (la integral daría 0); "
             "probablemente uno de ellos está mal"])
    return va, vb


def validar_variable(nombre, etiqueta="la variable", expr=None, excluir=None):
    """Valida un nombre de variable ('x' o 'y'). Usa `expr` (la expresión ya
    validada) para adivinar cuál quisiste, y `excluir` para no repetir la otra variable."""
    t = str(nombre).strip()
    if t.lower() in VARIABLES_PERMITIDAS and t.lower() != excluir:
        return SIMBOLOS[t.lower()]

    problemas, sugerencia = [], None
    if t.lower() in VARIABLES_PERMITIDAS and t.lower() == excluir:
        otra = [v for v in VARIABLES_PERMITIDAS if v != excluir]
        problemas.append(f"'{t}' ya la usaste como la otra variable; deben ser distintas")
        sugerencia = otra[0]
        raise ErrorDeEntrada(etiqueta, t, problemas, sugerencia)

    problemas.append(f"'{t}' no es una variable válida (se admiten: x, y)")
    candidatas = [v for v in VARIABLES_PERMITIDAS if v != excluir]
    if expr is not None:
        usadas = [str(s) for s in sorted(expr.free_symbols, key=str) if str(s) in candidatas]
        if len(usadas) == 1:
            problemas.append(f"tu expresión usa '{usadas[0]}'")
            sugerencia = usadas[0]
        elif len(usadas) > 1:
            problemas.append("tu expresión usa " + " y ".join(f"'{u}'" for u in usadas))
            sugerencia = " o ".join(usadas)
    if sugerencia is None and len(candidatas) == 1:
        sugerencia = candidatas[0]
    if sugerencia is None:
        cerca = difflib.get_close_matches(t.lower(), candidatas, n=1, cutoff=0.5)
        sugerencia = cerca[0] if cerca else None
    raise ErrorDeEntrada(etiqueta, t, problemas, sugerencia)


def validar_frontera(g_str, variable_externa, etiqueta="la frontera"):
    """Valida una frontera g(variable_externa) de integra_doble_general
    (puede ser constante o depender solo de la variable externa)."""
    ve = str(variable_externa).strip().lower()
    expr = _validar_texto(g_str, (ve,), etiqueta)
    return expr


def validar_dominio_general(expresion, var_interna, g1_str, g2_str, var_externa,
                            ext_min, ext_max):
    """Valida todos los datos de integra_doble_general de una vez.
    Devuelve (expr, v_int, v_ext, g1, g2, ext_min, ext_max)."""
    expr = validar_y_parsear_expresion(expresion)
    v_ext = validar_variable(var_externa, "la variable externa", expr=expr)
    v_int = validar_variable(var_interna, "la variable interna", expr=expr,
                             excluir=str(v_ext))
    g1 = validar_frontera(g1_str, v_ext, f"la frontera inferior g1 (debe depender solo de {v_ext})")
    g2 = validar_frontera(g2_str, v_ext, f"la frontera superior g2 (debe depender solo de {v_ext})")
    a, b = validar_limites_numericos(ext_min, ext_max, str(v_ext))
    return expr, v_int, v_ext, g1, g2, a, b


if __name__ == "__main__":
    pruebas = [
        lambda: validar_y_parsear_expresion("x^2 + z*sn(x)"),
        lambda: validar_y_parsear_expresion("2xy + (3*y"),
        lambda: validar_y_parsear_expresion("sen(x) * 2 +"),
        lambda: validar_y_parsear_expresion("sinx + x2"),
        lambda: validar_limites_numericos("1O", 5),
        lambda: validar_limites_numericos(5, 2),
        lambda: validar_limites_numericos("dos", "pi/2"),
        lambda: validar_variable("z", "la variable de integración", expr=sp.sympify("x**2")),
        lambda: validar_dominio_general("x*y", "x", "0", "x**2", "x", 0, 1),
        lambda: validar_dominio_general("x*y", "y", "0", "z**2", "x", 0, 1),
    ]
    for prueba in pruebas:
        try:
            print("OK:", prueba(), "\n")
        except ErrorDeEntrada as e:
            print(e, "\n")
