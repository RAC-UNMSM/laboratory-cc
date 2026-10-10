import ast
import re

import sympy as sp


# ============================================================
# LÍMITES DE CÓMPUTO
# ============================================================

MAX_DIMENSION = 6
MAX_LONGITUD_COMPONENTE = 120
MAX_NODOS_AST = 80
MAX_VALOR_NUMERICO = 1_000_000
MAX_EXPONENTE = 10


# ============================================================
# VALIDACIÓN DE DIMENSIÓN
# ============================================================

def validar_dimension(n):
    """
    Comprueba que n sea un entero positivo y que no exceda
    el límite de cómputo permitido.

    El proyecto trabaja con transformaciones:
        T: R^n -> R^n
    """

    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError(
            "La dimensión n debe ser un número entero."
        )

    if n < 1:
        raise ValueError(
            "La dimensión n debe ser mayor que 0."
        )

    if n > MAX_DIMENSION:
        raise ValueError(
            f"La dimensión máxima permitida es {MAX_DIMENSION}."
        )

    return n


def crear_variables_validacion(n):
    """
    Crea las variables:
        x1, x2, ..., xn
    """

    return sp.symbols(f"x1:{n + 1}")


# ============================================================
# NORMALIZACIÓN DE LA REGLA
# ============================================================

def _separar_componentes(texto):
    """
    Separa una regla por comas respetando paréntesis.

    Ejemplo:
        x1, (x2+x3)/2, x2-x3
    """

    componentes = []
    actual = []
    nivel = 0

    for caracter in texto:

        if caracter in "([{":
            nivel += 1

        elif caracter in ")]}":
            nivel -= 1

            if nivel < 0:
                raise ValueError(
                    "La regla contiene paréntesis o corchetes mal cerrados."
                )

        if caracter == "," and nivel == 0:
            componente = "".join(actual).strip()

            if componente:
                componentes.append(componente)

            actual = []

        else:
            actual.append(caracter)

    if nivel != 0:
        raise ValueError(
            "La regla contiene paréntesis o corchetes mal cerrados."
        )

    componente_final = "".join(actual).strip()

    if componente_final:
        componentes.append(componente_final)

    return componentes


def _separar_regla_texto(regla):
    """
    Convierte una regla escrita como texto en una lista.

    Ejemplos admitidos:

        [x1, x2+x3, x2-x3]

        (x1, x2+x3, x2-x3)

        x1, x2+x3, x2-x3
    """

    texto = regla.strip()

    if not texto:
        return []

    if (
        (texto.startswith("[") and texto.endswith("]"))
        or
        (texto.startswith("(") and texto.endswith(")"))
    ):
        texto = texto[1:-1].strip()

    if not texto:
        return []

    return _separar_componentes(texto)


def normalizar_regla(regla):
    """
    Convierte la regla recibida a una lista.

    Se admiten:

    1. Lista:
        ["x1", "x2+x3", "x2-x3"]

    2. Tupla:
        ("x1", "x2+x3", "x2-x3")

    3. Texto:
        "[x1, x2+x3, x2-x3]"
    """

    if isinstance(regla, str):
        return _separar_regla_texto(regla)

    if isinstance(regla, (list, tuple)):
        return list(regla)

    raise ValueError(
        "La regla de correspondencia debe enviarse "
        "como una lista, tupla o texto."
    )


# ============================================================
# NORMALIZACIÓN DE EXPRESIONES
# ============================================================

def _normalizar_expresion_texto(texto):
    """
    Realiza normalizaciones sencillas antes de analizar
    la expresión.

    Permite, por ejemplo:

        2x1 + x2

    convirtiéndolo internamente en:

        2*x1 + x2
    """

    texto = texto.strip()

    if not texto:
        raise ValueError(
            "Se recibió una componente vacía."
        )

    if len(texto) > MAX_LONGITUD_COMPONENTE:
        raise ValueError(
            "La componente supera la longitud máxima permitida "
            f"de {MAX_LONGITUD_COMPONENTE} caracteres."
        )

    # Permitir ^ como forma habitual de escribir potencias.
    texto = texto.replace("^", "**")

    # 2x1 -> 2*x1
    texto = re.sub(
        r"(?<=\d)(?=x\d+\b)",
        "*",
        texto
    )

    # 2(x1+x2) -> 2*(x1+x2)
    texto = re.sub(
        r"(?<=\d)(?=\()",
        "*",
        texto
    )

    # x1(x2+x3) -> x1*(x2+x3)
    texto = re.sub(
        r"(x\d+)\s*(?=\()",
        r"\1*",
        texto
    )

    # )( -> )*(
    texto = re.sub(
        r"\)\s*(?=\()",
        ")*",
        texto
    )

    return texto


# ============================================================
# LÍMITES DEL ÁRBOL SINTÁCTICO
# ============================================================

def _validar_limites_ast(arbol):
    """
    Limita la complejidad de la expresión recibida para evitar
    solicitudes excesivamente grandes.
    """

    nodos = list(ast.walk(arbol))

    if len(nodos) > MAX_NODOS_AST:
        raise ValueError(
            "La expresión es demasiado compleja para ser procesada."
        )

    for nodo in nodos:

        if isinstance(nodo, ast.Constant):

            if isinstance(nodo.value, bool):
                continue

            if isinstance(nodo.value, (int, float)):
                if abs(nodo.value) > MAX_VALOR_NUMERICO:
                    raise ValueError(
                        "La expresión contiene un valor numérico "
                        "demasiado grande."
                    )


# ============================================================
# EVALUACIÓN SEGURA DEL AST
# ============================================================

def _evaluar_ast(nodo, variables_permitidas):
    """
    Convierte un árbol sintáctico de Python a una expresión
    de SymPy utilizando únicamente operaciones matemáticas
    permitidas.

    No se permiten llamadas a funciones, atributos, imports,
    acceso a objetos ni ejecución de código.
    """

    if isinstance(nodo, ast.Expression):
        return _evaluar_ast(
            nodo.body,
            variables_permitidas
        )

    if isinstance(nodo, ast.Constant):

        if isinstance(nodo.value, bool):
            raise ValueError(
                "No se permiten valores booleanos."
            )

        if isinstance(nodo.value, int):
            return sp.Integer(nodo.value)

        if isinstance(nodo.value, float):
            return sp.Rational(str(nodo.value))

        raise ValueError(
            "Solo se permiten constantes numéricas."
        )

    if isinstance(nodo, ast.Name):

        if nodo.id not in variables_permitidas:
            raise ValueError(
                f"La variable '{nodo.id}' no está permitida."
            )

        return variables_permitidas[nodo.id]

    if isinstance(nodo, ast.UnaryOp):

        operando = _evaluar_ast(
            nodo.operand,
            variables_permitidas
        )

        if isinstance(nodo.op, ast.UAdd):
            return operando

        if isinstance(nodo.op, ast.USub):
            return -operando

        raise ValueError(
            "Operación unaria no permitida."
        )

    if isinstance(nodo, ast.BinOp):

        izquierda = _evaluar_ast(
            nodo.left,
            variables_permitidas
        )

        derecha = _evaluar_ast(
            nodo.right,
            variables_permitidas
        )

        if isinstance(nodo.op, ast.Add):
            return izquierda + derecha

        if isinstance(nodo.op, ast.Sub):
            return izquierda - derecha

        if isinstance(nodo.op, ast.Mult):
            return izquierda * derecha

        if isinstance(nodo.op, ast.Div):

            if derecha == 0:
                raise ValueError(
                    "No se permite división entre cero."
                )

            return izquierda / derecha

        if isinstance(nodo.op, ast.Pow):

            if derecha.free_symbols:
                raise ValueError(
                    "El exponente debe ser numérico."
                )

            if not derecha.is_integer:
                raise ValueError(
                    "El exponente debe ser un número entero."
                )

            if abs(int(derecha)) > MAX_EXPONENTE:
                raise ValueError(
                    f"El exponente máximo permitido es {MAX_EXPONENTE}."
                )

            return izquierda ** derecha

        raise ValueError(
            "La expresión contiene una operación no permitida."
        )

    raise ValueError(
        "La expresión contiene una construcción no permitida."
    )


def _interpretar_expresion_segura(texto, variables):
    """
    Interpreta una expresión matemática sin utilizar eval(),
    sympify() ni parse_expr() sobre la entrada del usuario.
    """

    texto = _normalizar_expresion_texto(texto)

    variables_permitidas = {
        str(variable): variable
        for variable in variables
    }

    try:
        arbol = ast.parse(
            texto,
            mode="eval"
        )

    except SyntaxError as error:
        raise ValueError(
            f"No se pudo interpretar la expresión: {texto}"
        ) from error

    _validar_limites_ast(arbol)

    return sp.simplify(
        _evaluar_ast(
            arbol,
            variables_permitidas
        )
    )


# ============================================================
# INTERPRETACIÓN DE COMPONENTES
# ============================================================

def interpretar_componentes(regla, variables):
    """
    Convierte las componentes recibidas a expresiones de SymPy.
    """

    componentes_entrada = normalizar_regla(regla)

    n = len(variables)

    if len(componentes_entrada) != n:
        raise ValueError(
            f"Para una transformación de R^{n} a R^{n}, "
            f"la regla debe tener exactamente {n} componentes. "
            f"Se recibieron {len(componentes_entrada)}."
        )

    componentes = []

    for i, componente in enumerate(
        componentes_entrada,
        start=1
    ):

        try:

            if isinstance(componente, sp.Expr):
                expresion = sp.simplify(componente)

            else:
                expresion = _interpretar_expresion_segura(
                    str(componente),
                    variables
                )

        except ValueError as error:
            raise ValueError(
                f"Error en la componente {i}: {error}"
            ) from error

        componentes.append(expresion)

    return componentes


# ============================================================
# VALIDACIÓN DE SÍMBOLOS
# ============================================================

def validar_simbolos(componentes, variables):
    """
    Comprueba que no aparezcan variables distintas de:
        x1, x2, ..., xn.
    """

    variables_permitidas = set(variables)

    for i, expresion in enumerate(
        componentes,
        start=1
    ):

        simbolos_extra = (
            expresion.free_symbols
            - variables_permitidas
        )

        if simbolos_extra:
            nombres = ", ".join(
                sorted(
                    str(simbolo)
                    for simbolo in simbolos_extra
                )
            )

            raise ValueError(
                f"La componente {i} contiene variables "
                f"no permitidas: {nombres}."
            )

    return True


# ============================================================
# VALIDACIÓN DE LINEALIDAD
# ============================================================

def validar_linealidad(componentes, variables):
    """
    Verifica que cada componente sea lineal y homogénea
    en x1, ..., xn.

    Se permiten:

        2*x1 + 3*x2
        2x1 + 3x2
        x1 - x3
        x2/2
        0

    No se permiten:

        x1*x2
        x1**2
        x1 + 5
    """

    sustitucion_cero = {
        variable: 0
        for variable in variables
    }

    for i, expresion in enumerate(
        componentes,
        start=1
    ):

        # Condición necesaria para una TL:
        # T(0) = 0.
        valor_en_cero = sp.simplify(
            expresion.subs(sustitucion_cero)
        )

        if valor_en_cero != 0:
            raise ValueError(
                f"La componente {i} no es lineal porque "
                f"contiene un término independiente distinto de 0."
            )

        try:
            polinomio = sp.Poly(
                expresion,
                *variables
            )

        except sp.PolynomialError as error:
            raise ValueError(
                f"La componente {i} no es lineal: "
                f"{expresion}."
            ) from error

        if polinomio.total_degree() > 1:
            raise ValueError(
                f"La componente {i} no es lineal: "
                f"{expresion}."
            )

    return True


# ============================================================
# VALIDACIÓN COMPLETA
# ============================================================

def validar_transformacion(n, regla):
    """
    Valida completamente una transformación candidata:

        T: R^n -> R^n

    Si todo es correcto, devuelve los datos preparados
    para los módulos matemáticos.
    """

    n = validar_dimension(n)

    variables = crear_variables_validacion(n)

    componentes = interpretar_componentes(
        regla,
        variables
    )

    validar_simbolos(
        componentes,
        variables
    )

    validar_linealidad(
        componentes,
        variables
    )

    return {
        "n": n,
        "variables": variables,
        "componentes": componentes,
        "valida": True
    }