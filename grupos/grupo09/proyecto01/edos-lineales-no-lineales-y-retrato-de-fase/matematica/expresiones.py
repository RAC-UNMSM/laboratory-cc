"""Compilación de expresiones matemáticas de texto a funciones numéricas.

Es la puerta de entrada del agente: el texto que llega aquí puede venir de un
cliente MCP arbitrario, no solo del balotario del repositorio. Por eso **no se
usa `eval`** y la validación es en tres capas:

1. Léxica: se rechazan caracteres fuera de una lista blanca y cualquier `__`.
2. De nombres: todo identificador debe ser un símbolo declarado o una función
   matemática explícitamente permitida.
3. Simbólica: después de parsear con sympy se comprueba que la expresión no
   dejó símbolos libres ni funciones ajenas a la lista blanca.

Las tres capas son necesarias: la primera corta la sintaxis de ataque, la
segunda los nombres, y la tercera atrapa lo que el parser haya construido por
su cuenta.
"""

import re

import sympy as sp

#: Funciones y constantes que una EDO puede usar. Todo lo demás se rechaza.
FUNCIONES_PERMITIDAS = {
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
    "exp", "log", "ln", "sqrt", "cbrt",
    "Abs", "abs", "sign", "floor", "ceiling", "Max", "Min",
    "pi", "E", "oo",
}

#: Alias de escritura habitual hacia el nombre que entiende sympy.
ALIAS = {"ln": "log", "abs": "Abs"}

_IDENTIFICADOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CARACTERES_VALIDOS = re.compile(r"^[0-9A-Za-z_+\-*/%(),.\s]*$")


class ExpresionInvalida(ValueError):
    """La expresión no se pudo aceptar. El mensaje explica por qué."""


def _validar_texto(texto, permitidos):
    """Capas 1 y 2: revisión léxica y de nombres, antes de tocar sympy."""
    if not isinstance(texto, str) or not texto.strip():
        raise ExpresionInvalida("La expresión debe ser un texto no vacío.")
    if "__" in texto:
        raise ExpresionInvalida("La expresión no puede contener '__'.")
    if "^" in texto:
        raise ExpresionInvalida(
            "Use '**' para la potencia; en sympy '^' significa XOR bit a bit.")
    if not _CARACTERES_VALIDOS.match(texto):
        sobrantes = sorted(set(re.sub(r"[0-9A-Za-z_+\-*/%(),.\s]", "", texto)))
        raise ExpresionInvalida(f"Caracteres no permitidos en la expresión: {sobrantes}")
    desconocidos = sorted({n for n in _IDENTIFICADOR.findall(texto) if n not in permitidos})
    if desconocidos:
        raise ExpresionInvalida(
            f"Nombres no declarados: {desconocidos}. "
            f"Declare las variables y parámetros, o use una función permitida "
            f"({', '.join(sorted(FUNCIONES_PERMITIDAS))}).")


def _parsear(texto, simbolos):
    """Capa 3: parseo con sympy y comprobación de lo que quedó en la expresión."""
    entorno = dict(simbolos)
    # Se recorre ordenado para que el entorno no dependa del orden de iteración
    # del conjunto, que varía entre procesos. El guard mira `nombre`, no el
    # destino del alias: comparar el destino haría que 'abs' se saltara porque
    # 'Abs' ya estaba puesto, y el alias quedaría sin registrar.
    for nombre in sorted(FUNCIONES_PERMITIDAS):
        if nombre in entorno:                  # un símbolo declarado tiene prioridad
            continue
        atributo = getattr(sp, ALIAS.get(nombre, nombre), None)
        if atributo is not None:
            entorno[nombre] = atributo
    _validar_texto(texto, set(entorno))
    try:
        expresion = sp.sympify(texto, locals=entorno)
    except (sp.SympifyError, SyntaxError, TypeError) as exc:
        raise ExpresionInvalida(f"No se pudo interpretar {texto!r}: {exc}") from exc

    libres = expresion.free_symbols - set(simbolos.values())
    if libres:
        raise ExpresionInvalida(
            f"Símbolos libres no declarados en {texto!r}: {sorted(map(str, libres))}")
    permitidas = {getattr(sp, ALIAS.get(n, n), None) for n in FUNCIONES_PERMITIDAS}
    for funcion in expresion.atoms(sp.Function):
        if type(funcion) not in permitidas:
            raise ExpresionInvalida(
                f"Función no permitida en {texto!r}: {type(funcion).__name__}")
    return expresion


def _simbolos(nombres):
    """Diccionario nombre -> símbolo, rechazando nombres repetidos o inválidos."""
    limpios = []
    for nombre in nombres:
        if not isinstance(nombre, str) or not _IDENTIFICADOR.fullmatch(nombre or ""):
            raise ExpresionInvalida(f"Nombre de variable inválido: {nombre!r}")
        if nombre in FUNCIONES_PERMITIDAS:
            raise ExpresionInvalida(
                f"{nombre!r} es el nombre de una función matemática; elija otro.")
        if nombre in limpios:
            raise ExpresionInvalida(f"Nombre de variable repetido: {nombre!r}")
        limpios.append(nombre)
    return {nombre: sp.Symbol(nombre) for nombre in limpios}


def compilar_escalar(texto, nombres):
    """Compila una expresión escalar en una función que se llama por nombre.

    Solo exige los símbolos que la expresión usa de verdad, de modo que una
    solución exacta `f(x=...)` y un invariante `g(theta=..., w0=...)` se
    construyan con la misma herramienta.

    Ejemplo: compilar_escalar("2/(2 - 3*x**2)", ["x"])(x=0.5)
    """
    simbolos = _simbolos(nombres)
    expresion = _parsear(texto, simbolos)
    usados = [n for n in simbolos if simbolos[n] in expresion.free_symbols]
    numerico = sp.lambdify([simbolos[n] for n in usados], expresion, "numpy")

    def evaluar(**valores):
        faltantes = [n for n in usados if n not in valores]
        if faltantes:
            raise ExpresionInvalida(f"Faltan valores para {faltantes} en {texto!r}")
        return numerico(*[valores[n] for n in usados])

    evaluar.usados = tuple(usados)
    evaluar.expresion = expresion
    evaluar.texto = texto
    return evaluar


def compilar_campo(expresiones, variable_independiente, variables_estado, parametros=()):
    """Compila el campo vectorial F de x' = F(t, x; p) en f(t, y, parametros).

    La firma devuelta es la que espera `matematica.modelo_edos.resolver_edo`.

    Ejemplo: compilar_campo(["thetapunto", "-w0**2*sin(theta)"], "t",
                            ["theta", "thetapunto"], ["w0"])
    """
    expresiones = list(expresiones)
    if not expresiones:
        raise ExpresionInvalida("Debe indicar al menos una ecuación.")
    if len(expresiones) != len(variables_estado):
        raise ExpresionInvalida(
            f"Se esperaban {len(variables_estado)} ecuaciones "
            f"(una por variable de estado) y llegaron {len(expresiones)}.")
    nombres_parametros = list(parametros)
    simbolos = _simbolos([variable_independiente, *variables_estado, *nombres_parametros])
    compiladas = [_parsear(texto, simbolos) for texto in expresiones]

    simbolo_t = simbolos[variable_independiente]
    simbolos_estado = [simbolos[n] for n in variables_estado]
    simbolos_parametros = [simbolos[n] for n in nombres_parametros]
    numerico = sp.lambdify([simbolo_t, simbolos_estado, *simbolos_parametros],
                           compiladas, "numpy")

    def campo(t, y, valores_parametros=None):
        valores_parametros = valores_parametros or {}
        faltantes = [n for n in nombres_parametros if n not in valores_parametros]
        if faltantes:
            raise ExpresionInvalida(f"Faltan valores para los parámetros {faltantes}.")
        return numerico(t, list(y), *[valores_parametros[n] for n in nombres_parametros])

    campo.expresiones = tuple(compiladas)
    campo.variables_estado = tuple(variables_estado)
    campo.variable_independiente = variable_independiente
    campo.parametros = tuple(nombres_parametros)
    return campo


def campo_desde_catalogo(ecuacion):
    """Construye el campo a partir del bloque `ecuacion` de un `tema_*.json`."""
    return compilar_campo(ecuacion["campo"], ecuacion["variable_independiente"],
                          ecuacion["variables_estado"], ecuacion.get("parametros", {}))


def escalar_desde_catalogo(texto, ecuacion):
    """Compila una expresión auxiliar del catálogo (solución exacta, invariante)."""
    nombres = dict.fromkeys([ecuacion["variable_independiente"],
                             *ecuacion["variables_estado"],
                             *ecuacion.get("parametros", {})])
    return compilar_escalar(texto, list(nombres))


def jacobiano_simbolico(campo):
    """Jacobiano exacto del campo compilado, o None si no se pudo derivar.

    Permite contrastar el Jacobiano numérico de `analisis_estabilidad` contra la
    derivada exacta cuando la expresión lo admite.
    """
    simbolos = [sp.Symbol(n) for n in campo.variables_estado]
    try:
        matriz = sp.Matrix(list(campo.expresiones)).jacobian(simbolos)
    except (TypeError, ValueError, sp.SympifyError):
        return None
    return matriz
