"""
analisis_estabilidad.py

Responsable: Tisnado Yarleque Christian David (Matemático II — Estabilidad y
bifurcaciones), según "Grupo_09_Propuesta_actualizada.md".

RESPONSABILIDAD DE ESTE MÓDULO
-------------------------------
Dado un sistema autónomo de EDOs de primer orden

    x' = F(x; theta)

este módulo calcula:

    Equilibrios  ->  Jacobiano  ->  Autovalores  ->  Estabilidad local
                                                      (con casos no concluyentes)

y devuelve una estructura de datos que `server.py` puede usar para construir
una explicación, y que `visualizacion.py` puede usar para dibujar el retrato
de fase (puntos de equilibrio, clasificación, etc.).

Este módulo NO hace (queda para otros integrantes/módulos del grupo):
    - resolver la EDO en el tiempo (modelo_edos.py),
    - integración Runge-Kutta / soluciones numéricas de trayectorias,
    - análisis de caos / Lyapunov / Poincaré (analisis_caos.py),
    - barridos paramétricos / bifurcaciones (analisis_bifurcaciones.py),
    - generación de gráficas o HTML (visualizacion.py),
    - validación general de la solicitud del usuario (datos_validacion.py),
    - orquestación (server.py).

INTERFACES (integración con el proyecto del grupo)
---------------------------------------------------
Este módulo expone TRES puntos de entrada, sin cambiar la lógica matemática:

1) `analizar_estabilidad(modelo)`  -> análisis simbólico (SymPy)
       modelo = {
           "variables": ["x", "y"],          # nombres de las variables de estado
           "equations": ["x - y", "x + y"],  # F_i(x) como texto, mismo orden
           "parameters": {"r": 2, "K": 100}, # opcional: parámetros con valor
                                             # numérico. Todo símbolo de las
                                             # ecuaciones que NO esté aquí se
                                             # trata como parámetro simbólico
                                             # libre (p. ej. "mu") y se asume REAL.
           "independent_variable": "t",      # opcional (por defecto "t")
           "autonomous": True,               # opcional (por defecto True)
       }

2) `analizar_estabilidad_referencia(nombre, parametros=None)` -> adaptador para
   los modelos de `modelos_referencia.py` ("lineal", "logistico", "lorenz"),
   cuyas ecuaciones están como funciones y no como texto. Las ecuaciones en
   texto se declaran en `ECUACIONES_REFERENCIA` (ver limitación allí).

3) `jacobiano(...)` y `analizar_equilibrios(...)` -> contrato numérico original
   del grupo (funciones f(t, y, parametros)). Se conservan sin cambios porque
   `server.py` y `analisis_bifurcaciones.py` los usan.

Salida por consola: `formatear_reporte_estabilidad(resultado)` e
`imprimir_reporte_estabilidad(resultado)` dan un reporte ordenado (solo ASCII y
acentos Latin-1, para no fallar en terminales de Windows).

Principio rector (regla 22 del prompt): nunca se inventan valores para
parámetros, equilibrios o resultados. Si algo no puede determinarse de forma
concluyente con los datos disponibles, el resultado lo indica explícitamente
(`conclusive: False`) en lugar de forzar una clasificación.
"""

from __future__ import annotations

import re
import textwrap
from numbers import Number
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    auto_number,
    auto_symbol,
    convert_xor,
    factorial_notation,
    parse_expr,
    repeated_decimals,
)

# ---------------------------------------------------------------------------
# 1. CONSTANTES DE CONFIGURACIÓN Y SEGURIDAD
# ---------------------------------------------------------------------------

#: Razones de error/estado que este módulo puede reportar (sección 21).
RAZONES = {
    "invalid_input": "La entrada no tiene el formato mínimo requerido o contiene datos inconsistentes.",
    "non_autonomous_system": "El sistema depende explícitamente de la variable independiente y no puede analizarse mediante el criterio de equilibrio autónomo estándar.",
    "equilibrium_not_found": "No fue posible encontrar equilibrios mediante los métodos simbólicos/numéricos disponibles.",
    "equilibrium_not_verified": "Un candidato a equilibrio no satisfizo F(x*) = 0 dentro de la tolerancia establecida.",
    "symbolic_solution_incomplete": "SymPy no pudo resolver F(x) = 0 de forma completa (solución paramétrica o parcial).",
    "jacobian_error": "Ocurrió un error al construir o evaluar el Jacobiano.",
    "eigenvalue_error": "Ocurrió un error al calcular los autovalores del Jacobiano.",
    "inconclusive_linearization": "El criterio de linealización no permite concluir la estabilidad local de este equilibrio.",
}

# Transformaciones de parsing permitidas. Se excluye deliberadamente
# `lambda_notation` (no se necesita notación lambda en ecuaciones de EDOs y
# reduce superficie de ataque).
_TRANSFORMACIONES_PERMITIDAS = (
    auto_symbol,
    repeated_decimals,
    auto_number,
    factorial_notation,
    convert_xor,
)

# Funciones/constantes matemáticas permitidas dentro de las ecuaciones.
# Esta lista actúa como "global_dict" restringido para sympy.parse_expr,
# de modo que nunca se ejecuta código Python arbitrario (regla 24: no eval()).
_FUNCIONES_PERMITIDAS: Dict[str, Any] = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt,
    "Abs": sp.Abs, "abs": sp.Abs,
    "Min": sp.Min, "Max": sp.Max,
    "pi": sp.pi, "E": sp.E, "I": sp.I,
    "Rational": sp.Rational,
    "S": sp.S,
    # Nombres que las transformaciones estándar de sympy (auto_symbol,
    # auto_number) insertan en el código ya parseado (p. ej. Symbol('mu'),
    # Integer(3)). Deben estar disponibles en el global_dict restringido
    # para que el parseo funcione; no habilitan ejecución de código externo.
    "Symbol": sp.Symbol,
    "Integer": sp.Integer,
    "Float": sp.Float,
}

_IDENTIFICADOR_VALIDO = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Subcadenas que jamás deberían aparecer en una expresión matemática legítima.
# Es una capa adicional de defensa; la principal es no usar eval() y limitar
# el global_dict/local_dict de sympy.parse_expr (regla 24 y 25 del prompt).
_SUBCADENAS_PROHIBIDAS = (
    "__", "import", "exec", "eval(", "compile(", "open(", "os.", "sys.",
    "lambda", "globals(", "locals(", "getattr", "setattr", "delattr",
    ";", "\n", "\\", "`",
)

_TOLERANCIA_NUMERICA_DEFAULT = 1e-8


# ---------------------------------------------------------------------------
# 2. EXCEPCIÓN INTERNA PARA ERRORES ESTRUCTURADOS
# ---------------------------------------------------------------------------

class ErrorAnalisisEstabilidad(Exception):
    """
    Excepción interna usada para propagar un error ya estructurado según la
    sección 21 del prompt (qué ocurrió, en qué etapa, si se puede continuar,
    qué falta).
    """

    def __init__(
        self,
        reason: str,
        message: Optional[str] = None,
        stage: str = "unknown",
        can_continue: bool = False,
        missing: Optional[str] = None,
    ):
        self.reason = reason
        self.message = message or RAZONES.get(reason, "Error no especificado.")
        self.stage = stage
        self.can_continue = can_continue
        self.missing = missing
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": False,
            "reason": self.reason,
            "message": self.message,
            "stage": self.stage,
            "can_continue": self.can_continue,
            "missing": self.missing,
        }


# ---------------------------------------------------------------------------
# 3. PARSEO SEGURO DE EXPRESIONES (sin eval(), sin ejecutar código arbitrario)
# ---------------------------------------------------------------------------

def _validar_cadena_segura(texto: str, contexto: str) -> None:
    """Rechaza cadenas con patrones sospechosos antes de parsear con SymPy."""
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            f"{contexto}: se esperaba una cadena de texto no vacía.",
            stage="parsing",
        )
    minuscula = texto.lower()
    for patron in _SUBCADENAS_PROHIBIDAS:
        if patron in minuscula:
            raise ErrorAnalisisEstabilidad(
                "invalid_input",
                f"{contexto}: la expresión '{texto}' contiene un patrón no permitido ('{patron}').",
                stage="parsing",
            )


def _parsear_expresion(texto: str, simbolos_conocidos: Dict[str, sp.Symbol]) -> sp.Expr:
    """
    Convierte una cadena de texto en una expresión de SymPy sin usar eval()
    y sin permitir acceso a nombres/funciones fuera de la lista blanca.
    Cualquier identificador no reconocido se convierte automáticamente en un
    nuevo símbolo (parámetro simbólico libre, p. ej. 'mu'), nunca en código
    ejecutable.
    """
    _validar_cadena_segura(texto, "ecuación")
    local_dict = dict(simbolos_conocidos)
    try:
        expr = parse_expr(
            texto,
            local_dict=local_dict,
            global_dict=dict(_FUNCIONES_PERMITIDAS),
            transformations=_TRANSFORMACIONES_PERMITIDAS,
            evaluate=True,
        )
    except (SyntaxError, TypeError, ValueError, sp.SympifyError) as exc:
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            f"No se pudo interpretar la expresión '{texto}': {exc}",
            stage="parsing",
        ) from exc

    if not isinstance(expr, sp.Basic):
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            f"La expresión '{texto}' no produjo una expresión matemática válida.",
            stage="parsing",
        )
    return expr


# ---------------------------------------------------------------------------
# 4. NORMALIZACIÓN DEL MODELO DE ENTRADA
# ---------------------------------------------------------------------------

class ModeloNormalizado:
    """Contenedor interno con el sistema ya convertido a objetos SymPy."""

    __slots__ = (
        "variables_nombres", "variables_symbols", "F", "parametros_valores",
        "t_symbol", "autonomous_declarado", "raw",
    )

    def __init__(self, variables_nombres, variables_symbols, F,
                 parametros_valores, t_symbol, autonomous_declarado, raw):
        self.variables_nombres = variables_nombres
        self.variables_symbols = variables_symbols
        self.F = F
        self.parametros_valores = parametros_valores
        self.t_symbol = t_symbol
        self.autonomous_declarado = autonomous_declarado
        self.raw = raw


def _normalizar_modelo(modelo: Dict[str, Any]) -> ModeloNormalizado:
    """
    Valida y convierte el diccionario de entrada (ver docstring del módulo)
    en objetos SymPy. Este es el único lugar que debería modificarse para
    adaptarse a la representación real de `modelo_edos.py` / `datos_validacion.py`
    cuando esos módulos existan (regla 27 del prompt).
    """
    if not isinstance(modelo, dict):
        raise ErrorAnalisisEstabilidad(
            "invalid_input", "El modelo debe ser un diccionario.", stage="normalizacion"
        )

    variables = modelo.get("variables")
    equations = modelo.get("equations")

    if not isinstance(variables, (list, tuple)) or not variables:
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            "El modelo debe incluir 'variables' como lista no vacía de nombres.",
            stage="normalizacion",
            missing="variables",
        )
    if not isinstance(equations, (list, tuple)) or not equations:
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            "El modelo debe incluir 'equations' como lista no vacía de expresiones.",
            stage="normalizacion",
            missing="equations",
        )
    if len(variables) != len(equations):
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            f"El número de variables ({len(variables)}) no coincide con el número "
            f"de ecuaciones ({len(equations)}).",
            stage="normalizacion",
        )
    if len(variables) not in (1, 2, 3):
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            "Este módulo admite sistemas de 1, 2 o 3 variables de estado.",
            stage="normalizacion",
        )

    for nombre in variables:
        if not isinstance(nombre, str) or not _IDENTIFICADOR_VALIDO.match(nombre):
            raise ErrorAnalisisEstabilidad(
                "invalid_input",
                f"Nombre de variable inválido: {nombre!r}.",
                stage="normalizacion",
            )
    if len(set(variables)) != len(variables):
        raise ErrorAnalisisEstabilidad(
            "invalid_input", "Hay nombres de variables repetidos.", stage="normalizacion"
        )

    independiente = modelo.get("independent_variable", "t")
    if not isinstance(independiente, str) or not _IDENTIFICADOR_VALIDO.match(independiente):
        raise ErrorAnalisisEstabilidad(
            "invalid_input", "'independent_variable' debe ser un identificador válido.",
            stage="normalizacion",
        )
    if independiente in variables:
        raise ErrorAnalisisEstabilidad(
            "invalid_input",
            "'independent_variable' no puede coincidir con el nombre de una variable de estado.",
            stage="normalizacion",
        )

    autonomous_declarado = modelo.get("autonomous", True)
    if not isinstance(autonomous_declarado, bool):
        raise ErrorAnalisisEstabilidad(
            "invalid_input", "'autonomous' debe ser booleano si se proporciona.",
            stage="normalizacion",
        )

    parametros_raw = modelo.get("parameters", {}) or {}
    if not isinstance(parametros_raw, dict):
        raise ErrorAnalisisEstabilidad(
            "invalid_input", "'parameters' debe ser un diccionario.", stage="normalizacion"
        )
    for nombre, valor in parametros_raw.items():
        if not isinstance(nombre, str) or not _IDENTIFICADOR_VALIDO.match(nombre):
            raise ErrorAnalisisEstabilidad(
                "invalid_input", f"Nombre de parámetro inválido: {nombre!r}.",
                stage="normalizacion",
            )
        if nombre in variables or nombre == independiente:
            raise ErrorAnalisisEstabilidad(
                "invalid_input",
                f"El parámetro '{nombre}' no puede coincidir con una variable o con "
                "la variable independiente.",
                stage="normalizacion",
            )
        if not isinstance(valor, (int, float, Number)) or isinstance(valor, bool):
            raise ErrorAnalisisEstabilidad(
                "invalid_input",
                f"El parámetro '{nombre}' debe tener un valor numérico. "
                "Si es un parámetro simbólico, simplemente NO lo incluya en "
                "'parameters' y aparecerá libre en las ecuaciones.",
                stage="normalizacion",
            )

    # Símbolos: variables (reales, para que 'sign'/'re'/'im' se comporten bien),
    # variable independiente, y parámetros con valor numérico conocido.
    variables_symbols = [sp.Symbol(v, real=True) for v in variables]
    t_symbol = sp.Symbol(independiente, real=True)

    simbolos_conocidos: Dict[str, sp.Symbol] = {
        nombre: simb for nombre, simb in zip(variables, variables_symbols)
    }
    simbolos_conocidos[independiente] = t_symbol

    parametros_symbols: Dict[sp.Symbol, sp.Expr] = {}
    for nombre, valor in parametros_raw.items():
        simb = sp.Symbol(nombre, real=True)
        simbolos_conocidos[nombre] = simb
        parametros_symbols[simb] = sp.nsimplify(valor, rational=False)

    # Parsear cada ecuación. Cualquier símbolo nuevo encontrado (no declarado
    # como variable, parámetro conocido, o variable independiente) se
    # interpreta como PARÁMETRO SIMBÓLICO LIBRE (regla 8/22: nunca se le
    # asigna un valor inventado).
    # Los parámetros libres se declaran REALES: en la propuesta los parámetros
    # son números reales (datos_validacion.py exige float finito). Sin este
    # supuesto SymPy deja resultados como `re(mu)` en lugar de `mu`.
    F: List[sp.Expr] = []
    for eq_texto in equations:
        expr = _parsear_expresion(eq_texto, simbolos_conocidos)
        cambios = {}
        for s in expr.free_symbols:
            if s.name not in simbolos_conocidos:
                simbolos_conocidos[s.name] = sp.Symbol(s.name, real=True)
            if simbolos_conocidos[s.name] != s:
                cambios[s] = simbolos_conocidos[s.name]
        if cambios:
            expr = expr.subs(cambios)
        F.append(expr)

    return ModeloNormalizado(
        variables_nombres=list(variables),
        variables_symbols=variables_symbols,
        F=F,
        parametros_valores=parametros_symbols,
        t_symbol=t_symbol,
        autonomous_declarado=autonomous_declarado,
        raw=modelo,
    )


def _detectar_no_autonomo(modelo: ModeloNormalizado) -> bool:
    """
    Regla 6: si el sistema depende explícitamente de t, o el usuario lo
    marcó explícitamente como no autónomo, NO se elimina t arbitrariamente:
    se reporta como no analizable por este criterio.
    """
    if modelo.autonomous_declarado is False:
        return True
    for expr in modelo.F:
        if modelo.t_symbol in expr.free_symbols:
            return True
    return False


# ---------------------------------------------------------------------------
# 5. CÁLCULO DE EQUILIBRIOS (F(x*) = 0)
# ---------------------------------------------------------------------------

def calcular_equilibrios(
    F: Sequence[sp.Expr], variables_symbols: Sequence[sp.Symbol]
) -> Tuple[List[Dict[sp.Symbol, sp.Expr]], Dict[str, Any]]:
    """
    Resuelve F(x) = 0 para las variables de estado, conservando cualquier
    parámetro simbólico (regla 7/8: se usa SymPy, no se asignan valores
    arbitrarios a los parámetros).

    Devuelve (lista_de_equilibrios, info) donde cada equilibrio es un dict
    {symbol: expr}. `info` incluye metadatos sobre el método usado y si la
    solución es completa.
    """
    info: Dict[str, Any] = {"method": None, "complete": True, "note": None}

    try:
        soluciones = sp.solve(list(F), list(variables_symbols), dict=True)
    except NotImplementedError as exc:
        soluciones = None
        info["note"] = f"SymPy no pudo resolver el sistema simbólicamente: {exc}"

    equilibrios: List[Dict[sp.Symbol, sp.Expr]] = []

    if soluciones:
        info["method"] = "symbolic"
        for sol in soluciones:
            # Un equilibrio "completo" debe fijar todas las variables de estado.
            if all(v in sol for v in variables_symbols):
                equilibrios.append({v: sp.simplify(sol[v]) for v in variables_symbols})
            else:
                info["complete"] = False
                info["note"] = (
                    "SymPy devolvió una familia paramétrica de soluciones "
                    "(no todas las variables quedan fijas); no se reportan "
                    "como equilibrios puntuales para evitar inventar valores."
                )
        return equilibrios, info

    # --- Fallback numérico, SOLO si no quedan parámetros simbólicos libres ---
    parametros_libres = set()
    for expr in F:
        parametros_libres |= (expr.free_symbols - set(variables_symbols))

    if parametros_libres:
        info["method"] = "none"
        info["complete"] = False
        info["note"] = (
            "No se hallaron equilibrios simbólicos y no se intenta un método "
            "numérico porque el sistema aún depende de parámetros simbólicos "
            f"sin valor asignado: {sorted(s.name for s in parametros_libres)}."
        )
        return [], info

    info["method"] = "numeric"
    F_lamb = sp.lambdify(list(variables_symbols), list(F), modules="mpmath")
    n = len(variables_symbols)
    candidatos = []
    rejilla = [-5, -2, -1, -0.5, 0, 0.5, 1, 2, 5]
    import itertools

    intentos = list(itertools.product(rejilla, repeat=n))
    encontrados: List[Tuple[float, ...]] = []
    for punto_inicial in intentos:
        try:
            sol = sp.nsolve(list(F), list(variables_symbols), list(punto_inicial), tol=1e-12)
        except Exception:
            continue
        vector = tuple(float(sp.re(v)) for v in sol)
        if any(abs(v_i) > 1e6 for v_i in vector):
            continue
        # Deduplicar contra soluciones ya encontradas.
        es_nuevo = True
        for existente in encontrados:
            if max(abs(a - b) for a, b in zip(vector, existente)) < 1e-6:
                es_nuevo = False
                break
        if es_nuevo:
            residual = F_lamb(*vector)
            if max(abs(complex(r)) for r in residual) < 1e-8:
                encontrados.append(vector)
                equilibrios.append({v: sp.nsimplify(val, rational=False, tolerance=1e-9)
                                     for v, val in zip(variables_symbols, vector)})

    if not equilibrios:
        info["complete"] = False
        info["note"] = (
            "No se encontraron equilibrios mediante búsqueda numérica en la "
            "rejilla de puntos iniciales utilizada. Esto NO garantiza que no "
            "existan equilibrios fuera de la región explorada."
        )
    return equilibrios, info


def verificar_equilibrio(
    F: Sequence[sp.Expr],
    variables_symbols: Sequence[sp.Symbol],
    punto: Dict[sp.Symbol, sp.Expr],
    tolerancia: float = _TOLERANCIA_NUMERICA_DEFAULT,
) -> Dict[str, Any]:
    """
    Regla 10: todo equilibrio debe verificarse sustituyendo en F.
    - Si el residuo simplifica simbólicamente a 0 (posiblemente con
      parámetros libres), se considera verificado exactamente.
    - Si el residuo es puramente numérico, se compara contra una tolerancia.
    """
    residuales_simbolicos = [sp.simplify(f.subs(punto)) for f in F]

    todos_cero_simbolico = all(r == 0 for r in residuales_simbolicos)
    if todos_cero_simbolico:
        return {
            "valid": True,
            "residual": [0 for _ in F],
            "method": "symbolic",
            "tolerance": None,
        }

    # ¿El residuo es puramente numérico (sin parámetros libres)?
    if all(not r.free_symbols for r in residuales_simbolicos):
        residual_num = [complex(r.evalf()) for r in residuales_simbolicos]
        norma = max(abs(r) for r in residual_num)
        valido = norma < tolerancia
        return {
            "valid": valido,
            "residual": [float(r.real) if abs(r.imag) < tolerancia else complex(r) for r in residual_num],
            "method": "numeric",
            "tolerance": tolerancia,
            "norm": norma,
        }

    # El residuo sigue dependiendo de parámetros y no se simplificó a 0:
    # no se puede afirmar ni negar la verificación sin inventar valores.
    return {
        "valid": False,
        "residual": [str(r) for r in residuales_simbolicos],
        "method": "symbolic_incomplete",
        "tolerance": None,
        "note": (
            "El residuo no se simplificó a 0 y depende de parámetros "
            "simbólicos; no se puede verificar sin asignarles un valor."
        ),
    }


# ---------------------------------------------------------------------------
# 6. JACOBIANO Y AUTOVALORES
# ---------------------------------------------------------------------------

def calcular_jacobiano(F: Sequence[sp.Expr], variables_symbols: Sequence[sp.Symbol]) -> sp.Matrix:
    """
    Regla 11: J(x) = dF/dx, obtenido mediante diferenciación simbólica de
    SymPy (nunca mediante una API externa ni de forma manual).
    """
    try:
        F_vec = sp.Matrix(list(F))
        J = F_vec.jacobian(list(variables_symbols))
    except Exception as exc:  # pragma: no cover - defensivo
        raise ErrorAnalisisEstabilidad(
            "jacobian_error", f"No se pudo construir el Jacobiano: {exc}", stage="jacobiano"
        ) from exc
    return J


def _signo_parte_real(re_expr: sp.Expr) -> str:
    """
    Clasifica el signo de una parte real ya simplificada en:
    'neg', 'pos', 'zero' o 'undetermined' (si depende de parámetros
    simbólicos cuyo signo no puede determinarse sin asignarles un valor).
    """
    re_expr = sp.simplify(re_expr)
    if re_expr.free_symbols:
        # Puede que, aun con símbolos libres, sea idénticamente 0 (ya cubierto
        # por simplify) o que sympy pueda decidir el signo bajo supuestos
        # (por defecto no asumimos signo de parámetros: no inventamos info).
        return "undetermined"
    if re_expr == 0:
        return "zero"
    valor = re_expr.evalf()
    try:
        valor_float = float(valor)
    except TypeError:
        return "undetermined"
    if valor_float > 0:
        return "pos"
    if valor_float < 0:
        return "neg"
    return "zero"


def calcular_autovalores(J_en_punto: sp.Matrix) -> List[Dict[str, Any]]:
    """
    Regla 13: autovalores de J(x*) mediante SymPy, conservando valor exacto,
    parte real, parte imaginaria y multiplicidad algebraica.
    """
    try:
        autovalores_dict = J_en_punto.eigenvals()
    except Exception as exc:
        raise ErrorAnalisisEstabilidad(
            "eigenvalue_error", f"No se pudieron calcular los autovalores: {exc}",
            stage="autovalores",
        ) from exc

    resultado = []
    for valor, multiplicidad in autovalores_dict.items():
        valor_s = sp.simplify(valor)
        parte_real = sp.simplify(sp.re(valor_s)) if not valor_s.free_symbols else sp.simplify(sp.re(valor_s))
        parte_imag = sp.simplify(sp.im(valor_s)) if not valor_s.free_symbols else sp.simplify(sp.im(valor_s))
        signo = _signo_parte_real(parte_real)

        numerico = None
        if not valor_s.free_symbols:
            try:
                numerico = complex(valor_s.evalf())
            except TypeError:
                numerico = None

        resultado.append({
            "value": str(valor_s),
            "value_sympy": valor_s,
            "numeric_value": numerico,
            "real_part": str(parte_real),
            "real_part_sympy": parte_real,
            "imaginary_part": str(parte_imag),
            "multiplicity": int(multiplicidad),
            "real_part_sign": signo,
        })
    return resultado


# ---------------------------------------------------------------------------
# 7. CLASIFICACIÓN DE ESTABILIDAD LOCAL
# ---------------------------------------------------------------------------

def clasificar_estabilidad(autovalores_info: List[Dict[str, Any]], n_dim: int) -> Dict[str, Any]:
    """
    Regla 14: criterio de linealización (Hartman-Grobman) para equilibrios
    hiperbólicos, con manejo explícito de casos no concluyentes.

    Prioridad de las reglas (coherente con el teorema de Lyapunov indirecto):
      1. Si existe un autovalor con Re > 0 con signo DETERMINADO ->
         inestable (esto es concluyente sin importar los demás autovalores).
      2. Si no hay ninguno positivo pero existe alguno de signo
         INDETERMINADO (depende de un parámetro simbólico) -> no concluyente
         por dependencia paramétrica (no se inventa el signo).
      3. Si no hay positivos ni indeterminados, pero existe alguno con
         Re = 0 -> no concluyente por linealización (caso clásico, regla 14).
      4. Si todos son negativos -> estable asintóticamente.
    """
    signos = [a["real_part_sign"] for a in autovalores_info]

    if "pos" in signos:
        conclusive = True
        stability = "unstable"
        if "neg" in signos and "zero" not in signos and "undetermined" not in signos:
            reason = (
                "Existen autovalores con parte real positiva y otros con parte "
                "real negativa (punto de tipo silla)."
            )
        else:
            reason = "Existe al menos un autovalor con parte real positiva."
        return {"stability": stability, "conclusive": conclusive, "reason": reason}

    if "undetermined" in signos:
        parametros = set()
        return {
            "stability": None,
            "conclusive": False,
            "reason": (
                "El signo de la parte real de al menos un autovalor depende de "
                "uno o más parámetros simbólicos sin valor numérico asignado; "
                "no puede determinarse la estabilidad sin inventar dicho valor."
            ),
        }

    if "zero" in signos:
        return {
            "stability": None,
            "conclusive": False,
            "reason": (
                "La linealización presenta al menos un autovalor con parte real "
                "cero. Por lo tanto, el criterio lineal no permite determinar de "
                "forma concluyente la estabilidad local (Hartman-Grobman no aplica; "
                "el equilibrio no es hiperbólico)."
            ),
        }

    # Todos con signo determinado y estrictamente negativo.
    return {
        "stability": "local_asymptotically_stable",
        "conclusive": True,
        "reason": "Todos los autovalores tienen parte real negativa.",
    }


def clasificar_tipo_cualitativo(
    autovalores_info: List[Dict[str, Any]], n_dim: int, clasif_estabilidad: Dict[str, Any]
) -> Optional[str]:
    """
    Regla 15: clasificación cualitativa (node/focus/saddle/center), solo
    cuando esté matemáticamente respaldada por los autovalores. Se limita a
    sistemas 1D y 2D; en 3D no se fuerzan categorías 2D (regla 15, último
    párrafo).
    """
    signos = [a["real_part_sign"] for a in autovalores_info]
    if "undetermined" in signos:
        return None  # No hay base suficiente sin inventar el signo faltante.

    if n_dim == 1:
        signo = signos[0]
        if signo == "neg":
            return "stable_node"
        if signo == "pos":
            return "unstable_node"
        return "center_or_inconclusive"  # signo == "zero"

    if n_dim == 2:
        if "zero" in signos:
            return "center_or_inconclusive"
        if "pos" in signos and "neg" in signos:
            return "saddle"

        # Todos positivos o todos negativos: distinguir nodo de foco según
        # si los autovalores son reales o forman un par complejo conjugado.
        son_complejos = any(sp.simplify(a["imaginary_part_sympy"] if "imaginary_part_sympy" in a
                                          else sp.sympify(a["imaginary_part"])) != 0
                             for a in autovalores_info)
        if signos[0] == "neg":
            return "stable_focus" if son_complejos else "stable_node"
        else:
            return "unstable_focus" if son_complejos else "unstable_node"

    # n_dim == 3 (u otro): no se fuerza una categoría 2D.
    return None


# ---------------------------------------------------------------------------
# 8. REPORTE Y DATOS PARA VISUALIZACIÓN
# ---------------------------------------------------------------------------

# (el reporte de consola se construye en `formatear_reporte_estabilidad`, sección 10)


def _datos_visualizacion(resultado: Dict[str, Any]) -> Dict[str, Any]:
    """Regla 20: datos matemáticos listos para que `visualizacion.py` dibuje
    el retrato de fase, sin generar aquí ninguna gráfica ni HTML."""
    puntos = []
    for eq_info in resultado["equilibria"]:
        puntos.append({
            "point": eq_info["point"],
            "stability": eq_info["classification"]["stability"],
            "qualitative_type": eq_info["classification"].get("qualitative_type"),
            "conclusive": eq_info["classification"]["conclusive"],
        })
    return {
        "variables": resultado["system"]["variables"],
        "equilibrium_points": puntos,
    }


# ---------------------------------------------------------------------------
# 9. FUNCIÓN PRINCIPAL (interfaz para server.py)
# ---------------------------------------------------------------------------

def analizar_estabilidad(modelo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada principal del módulo (regla 29).

        resultado = analizar_estabilidad(modelo)

    `modelo` sigue la interfaz documentada al inicio del archivo. Devuelve
    siempre un diccionario JSON-serializable (salvo por las claves auxiliares
    que terminan en '_sympy', pensadas para uso interno/depuración y que
    `server.py` puede descartar antes de serializar).
    """
    try:
        modelo_norm = _normalizar_modelo(modelo)
    except ErrorAnalisisEstabilidad as err:
        return err.to_dict()

    if _detectar_no_autonomo(modelo_norm):
        return {
            "analysis": "stability",
            "valid": False,
            "reason": "non_autonomous_system",
            "message": RAZONES["non_autonomous_system"],
            "stage": "autonomy_check",
        }

    variables_symbols = modelo_norm.variables_symbols
    F_con_parametros = [f.subs(modelo_norm.parametros_valores) for f in modelo_norm.F]
    n_dim = len(variables_symbols)

    try:
        equilibrios, info_equilibrios = calcular_equilibrios(F_con_parametros, variables_symbols)
    except ErrorAnalisisEstabilidad as err:
        return err.to_dict()

    if not equilibrios:
        return {
            "analysis": "stability",
            "valid": False,
            "reason": "equilibrium_not_found",
            "message": RAZONES["equilibrium_not_found"],
            "stage": "equilibria",
            "details": info_equilibrios,
        }

    try:
        J = calcular_jacobiano(F_con_parametros, variables_symbols)
    except ErrorAnalisisEstabilidad as err:
        return err.to_dict()

    equilibria_resultado = []
    for punto in equilibrios:
        verificacion = verificar_equilibrio(F_con_parametros, variables_symbols, punto)

        punto_lista = [punto[v] for v in variables_symbols]
        try:
            J_en_punto = J.subs(punto)
            autovalores_info = calcular_autovalores(J_en_punto)
        except ErrorAnalisisEstabilidad as err:
            equilibria_resultado.append({
                "point": [str(v) for v in punto_lista],
                "verification": verificacion,
                "jacobian": None,
                "eigenvalues": [],
                "classification": None,
                "error": err.to_dict(),
            })
            continue

        clasif = clasificar_estabilidad(autovalores_info, n_dim)
        clasif["qualitative_type"] = clasificar_tipo_cualitativo(autovalores_info, n_dim, clasif)
        clasif["parametric_conditions"] = _condiciones_parametricas(autovalores_info)

        eq_dict = {
            "point": [str(v) for v in punto_lista],
            "point_numeric": [
                (float(v.evalf()) if v.is_number and not v.has(sp.I) else None)
                for v in punto_lista
            ],
            "verification": verificacion,
            "jacobian": [[str(J_en_punto[i, j]) for j in range(n_dim)] for i in range(n_dim)],
            "eigenvalues": [
                {
                    "value": av["value"],
                    "real_part": av["real_part"],
                    "imaginary_part": av["imaginary_part"],
                    "multiplicity": av["multiplicity"],
                    "approx": _aproximar_complejo(av["numeric_value"]),
                    "real_part_sign": av["real_part_sign"],
                }
                for av in autovalores_info
            ],
            "classification": clasif,
        }
        equilibria_resultado.append(eq_dict)

    resultado = {
        "analysis": "stability",
        "valid": True,
        "system": {
            "variables": modelo_norm.variables_nombres,
            "equations": [str(f) for f in modelo_norm.F],
            "parameters": {s.name: v for s, v in modelo_norm.parametros_valores.items()},
            "free_parameters": sorted(
                {s.name for f in F_con_parametros for s in f.free_symbols}
                - set(modelo_norm.variables_nombres)
            ),
        },
        "equilibria": equilibria_resultado,
        "equilibria_solution_info": info_equilibrios,
    }
    resultado["report"] = formatear_reporte_estabilidad(resultado)
    resultado["visualization_data"] = _datos_visualizacion(resultado)
    return resultado


# ---------------------------------------------------------------------------
# 10. FORMATO DE CONSOLA (reporte ordenado y entendible)
# ---------------------------------------------------------------------------
# Solo se usan caracteres ASCII y letras acentuadas Latin-1 (á é í ó ú ñ ¿):
# símbolos como "λ", "≈" o "→" provocan UnicodeEncodeError en terminales de
# Windows con codificación cp1252.

ANCHO_CONSOLA = 72

_ETIQUETA_ESTABILIDAD = {
    "local_asymptotically_stable": "ASINTÓTICAMENTE ESTABLE (local)",
    "unstable": "INESTABLE",
}
_ETIQUETA_TIPO = {
    "stable_node": "nodo estable (atractor)",
    "unstable_node": "nodo inestable (repulsor)",
    "stable_focus": "foco estable (espiral que converge)",
    "unstable_focus": "foco inestable (espiral que se aleja)",
    "saddle": "punto silla",
    "center_or_inconclusive": "centro o caso no concluyente",
}
_SIGNO_RE = {"neg": "negativa", "pos": "positiva", "zero": "cero", "undetermined": "depende del parámetro"}


def titulo_consola(texto: str) -> str:
    """Encabezado de sección: línea doble, título y línea doble."""
    return "\n".join(["=" * ANCHO_CONSOLA, " " + texto, "=" * ANCHO_CONSOLA])


def separador_consola(caracter: str = "-") -> str:
    return caracter * ANCHO_CONSOLA


def formatear_numero(valor: float, decimales: int = 4) -> str:
    """Número con signo y decimales fijos; los casi-cero se muestran como 0."""
    if abs(valor) < 10 ** (-(decimales + 2)):
        valor = 0.0
    return f"{valor:+.{decimales}f}"


def formatear_complejo(z, decimales: int = 4) -> str:
    """Complejo legible: '-1.0000+1.0000i'; si es real, solo la parte real."""
    z = complex(z)
    if abs(z.imag) < 1e-10:
        return formatear_numero(z.real, decimales)
    return f"{formatear_numero(z.real, decimales)}{formatear_numero(z.imag, decimales)}i"


def _aproximar_complejo(z) -> Optional[str]:
    return None if z is None else formatear_complejo(z)


def _texto_matematico(expr: Any) -> str:
    """Texto de SymPy más legible: 'I' -> 'i', '**' -> '^', '&' -> ' y '."""
    texto = str(expr).replace("**", "^").replace("&", " y ").replace("|", " o ")
    texto = re.sub(r"\b(\d+(?:\.\d+)?) < ([A-Za-z_]\w*)\b(?! <)", r"\2 > \1", texto)
    return re.sub(r"(?<![A-Za-z0-9_])I(?![A-Za-z0-9_])", "i", texto)


def _condiciones_parametricas(autovalores_info: List[Dict[str, Any]]) -> List[str]:
    """
    Cuando el signo de Re(lambda) depende de UN parámetro simbólico, indica para
    qué valores de ese parámetro es negativa/positiva (se deduce con SymPy; no
    se inventa ningún valor). Con varios parámetros libres no se intenta.
    """
    pendientes = [a for a in autovalores_info if a["real_part_sign"] == "undetermined"]
    if not pendientes:
        return []
    simbolos = set()
    for a in pendientes:
        simbolos |= a["real_part_sympy"].free_symbols
    if len(simbolos) != 1:
        return []
    s = next(iter(simbolos))
    condiciones = []
    for k, a in enumerate(autovalores_info, start=1):
        if a["real_part_sign"] != "undetermined":
            continue
        try:
            neg = sp.solve_univariate_inequality(a["real_part_sympy"] < 0, s, relational=True)
            pos = sp.solve_univariate_inequality(a["real_part_sympy"] > 0, s, relational=True)
        except Exception:
            continue
        condiciones.append(
            f"Re(lambda{k}) < 0 si {_texto_matematico(neg)};  Re(lambda{k}) > 0 si {_texto_matematico(pos)}"
        )
    return condiciones


def campo_consola(etiqueta: str, texto: Any, sangria: str = "", ancho_etiqueta: int = 20) -> str:
    """'Etiqueta : texto' con ajuste de línea; las continuaciones se alinean tras los dos puntos."""
    prefijo = f"{sangria}{etiqueta.ljust(ancho_etiqueta)} : "
    return textwrap.fill(str(texto), width=ANCHO_CONSOLA, initial_indent=prefijo,
                         subsequent_indent=" " * len(prefijo), break_on_hyphens=False)


def _formatear_matriz(filas: List[List[str]], sangria: str) -> List[str]:
    """Matriz de textos alineada a la derecha, entre corchetes."""
    if not filas:
        return []
    ancho = [max(len(_texto_matematico(f[j])) for f in filas) for j in range(len(filas[0]))]
    salida = []
    for f in filas:
        celdas = "  ".join(_texto_matematico(v).rjust(ancho[j]) for j, v in enumerate(f))
        salida.append(f"{sangria}[ {celdas} ]")
    return salida


def _tabla(encabezados: Sequence[str], filas: Sequence[Sequence[str]], sangria: str = "  ") -> List[str]:
    """Tabla de texto con columnas alineadas a la izquierda."""
    columnas = list(zip(*([encabezados] + [list(f) for f in filas])))
    ancho = [max(len(str(c)) for c in col) for col in columnas]
    def fila(valores):
        return sangria + "  ".join(str(v).ljust(ancho[j]) for j, v in enumerate(valores)).rstrip()
    return [fila(encabezados), sangria + "  ".join("-" * w for w in ancho)] + [fila(f) for f in filas]


def formatear_error_consola(resultado: Dict[str, Any], titulo: str) -> str:
    """Reporte de un resultado inválido (qué pasó, en qué etapa, qué falta)."""
    lineas = [titulo_consola(titulo), "No se pudo completar el análisis.", ""]
    lineas.append(campo_consola("Motivo", resultado.get("message", "Error no especificado."), "  ", 10))
    lineas.append(campo_consola("Código", resultado.get("reason", "desconocido"), "  ", 10))
    lineas.append(campo_consola("Etapa", resultado.get("stage", "desconocida"), "  ", 10))
    if resultado.get("missing"):
        lineas.append(campo_consola("Falta", resultado["missing"], "  ", 10))
    if "can_continue" in resultado:
        lineas.append(campo_consola("¿Continuar?", "sí" if resultado["can_continue"] else "no", "  ", 10))
    return "\n".join(lineas)


def formatear_reporte_estabilidad(resultado: Dict[str, Any]) -> str:
    """
    Reporte de consola del análisis de estabilidad: sistema, parámetros y, por
    cada equilibrio, verificación, Jacobiano, autovalores y conclusión; al final
    una tabla resumen. Recibe el diccionario de `analizar_estabilidad`.
    """
    titulo = "ANÁLISIS DE ESTABILIDAD LOCAL"
    if not resultado.get("valid"):
        return formatear_error_consola(resultado, titulo)

    sistema = resultado["system"]
    variables = sistema["variables"]
    equilibrios = resultado["equilibria"]
    info = resultado.get("equilibria_solution_info") or {}
    metodo = {"symbolic": "simbólico", "numeric": "numérico (búsqueda en rejilla)"}.get(info.get("method"), "-")
    L = [titulo_consola(titulo)]
    L.append(f"Sistema autónomo de {len(variables)} variable(s):")
    for var, eq in zip(variables, sistema["equations"]):
        L.append(f"    {var}' = {_texto_matematico(eq)}")
    params = sistema["parameters"]
    L.append("")
    L.append("Parámetros con valor : " + (", ".join(f"{k} = {v}" for k, v in params.items()) or "ninguno"))
    L.append("Parámetros libres    : " + (", ".join(sistema.get("free_parameters", [])) or "ninguno")
             + ("  (se tratan como símbolos reales; no se les asigna valor)" if sistema.get("free_parameters") else ""))
    L.append(f"Equilibrios hallados : {len(equilibrios)}   [método: {metodo}]")
    if info.get("note"):
        L.append(campo_consola("Aviso", info["note"]))

    for i, eq in enumerate(equilibrios, start=1):
        punto = ", ".join(_texto_matematico(v) for v in eq["point"])
        L += ["", separador_consola(), f"Equilibrio {i} de {len(equilibrios)}:  ({', '.join(variables)}) = ({punto})", ""]
        ver = eq["verification"]
        if ver["valid"] and ver["method"] == "symbolic":
            txt = "correcta, F(x*) = 0 exacto (simbólico)"
        elif ver["valid"]:
            txt = f"correcta, residuo máx = {ver.get('norm', 0):.2e} (tolerancia {ver['tolerance']:g})"
        else:
            txt = "NO VERIFICADA: " + str(ver.get("note", "F(x*) no se anula dentro de la tolerancia"))
        L.append(campo_consola("Verificación F(x*)=0", txt, "  "))
        if eq.get("error"):
            L.append(campo_consola("Error", eq["error"]["message"], "  "))
            continue
        L.append("  Jacobiano en x*      :")
        L += _formatear_matriz(eq["jacobian"], "      ")
        L.append("  Autovalores          :")
        for k, av in enumerate(eq["eigenvalues"], start=1):
            aprox = f"  ~ {av['approx']}" if av.get("approx") else ""
            mult = f"  (multiplicidad {av['multiplicity']})" if av["multiplicity"] > 1 else ""
            L.append(f"      lambda{k} = {_texto_matematico(av['value'])}{aprox}{mult}")
            L.append(f"             parte real: {_SIGNO_RE.get(av['real_part_sign'], av['real_part_sign'])}"
                     f"  [Re = {_texto_matematico(av['real_part'])}]")
        clasif = eq["classification"]
        etiqueta = _ETIQUETA_ESTABILIDAD.get(clasif["stability"], "NO CONCLUYENTE") if clasif["conclusive"] else "NO CONCLUYENTE"
        L.append("")
        L.append(f"  RESULTADO            : {etiqueta}")
        if clasif.get("qualitative_type"):
            L.append(f"  Tipo cualitativo     : {_ETIQUETA_TIPO.get(clasif['qualitative_type'], clasif['qualitative_type'])}")
        L.append(campo_consola("Motivo", clasif["reason"], "  "))
        for cond in clasif.get("parametric_conditions", []):
            L.append(campo_consola("Según el parámetro", cond, "  "))

    if equilibrios:
        filas = []
        for i, eq in enumerate(equilibrios, start=1):
            clasif = eq.get("classification")
            if not clasif:
                filas.append([i, "(" + ", ".join(_texto_matematico(v) for v in eq["point"]) + ")", "error", "-", "no"])
                continue
            concl = clasif["conclusive"]
            filas.append([
                i, "(" + ", ".join(_texto_matematico(v) for v in eq["point"]) + ")",
                _ETIQUETA_ESTABILIDAD.get(clasif["stability"], "NO CONCLUYENTE") if concl else "NO CONCLUYENTE",
                _ETIQUETA_TIPO.get(clasif.get("qualitative_type"), "-") if concl else "-",
                "sí" if concl else "no",
            ])
        L += ["", separador_consola("="), " RESUMEN", separador_consola("=")]
        L += _tabla(["N°", "Equilibrio", "Estabilidad local", "Tipo", "¿Concluyente?"], filas)
    L += ["", "Nota: la clasificación usa la linealización (Jacobiano); si algún autovalor tiene",
          "      parte real 0 o depende de un parámetro, el criterio no es concluyente."]
    return "\n".join(L)


def imprimir_reporte_estabilidad(resultado: Dict[str, Any]) -> None:
    """Imprime por consola el reporte de `analizar_estabilidad`."""
    print(formatear_reporte_estabilidad(resultado))


# ---------------------------------------------------------------------------
# 11. CONTRATO NUMÉRICO DEL GRUPO (funciones f(t, y, parametros))
# ---------------------------------------------------------------------------
# Estas dos funciones son las que ya existían en el proyecto compartido; se
# conservan SIN cambios de lógica porque `server.py` las importa y porque
# `analisis_bifurcaciones.py` las reutiliza para clasificar cada equilibrio de
# un barrido (el modelo llega como función, no como texto).

"""Cálculo numérico de Jacobiano y estabilidad local."""

import numpy as np


def jacobiano(modelo, punto, parametros=None, t=0.0, paso=1e-6):
    """Aproxima el Jacobiano respecto del estado mediante diferencias centrales."""
    parametros = parametros or {}
    punto = np.asarray(punto, dtype=float)
    n = len(punto)
    matriz = np.empty((n, n), dtype=float)
    for j in range(n):
        delta = np.zeros(n)
        delta[j] = paso * max(1.0, abs(punto[j]))
        arriba = np.asarray(modelo(t, punto + delta, parametros), dtype=float)
        abajo = np.asarray(modelo(t, punto - delta, parametros), dtype=float)
        if arriba.shape != (n,) or abajo.shape != (n,):
            raise ValueError("El modelo debe devolver una derivada por variable.")
        matriz[:, j] = (arriba - abajo) / (2 * delta[j])
    return matriz


def analizar_equilibrios(modelo, equilibrios, parametros=None, tolerancia=1e-8):
    """Clasifica equilibrios proporcionados por el modelo o por el usuario."""
    parametros = parametros or {}
    resultados = []
    for equilibrio in equilibrios:
        punto = np.atleast_1d(np.asarray(equilibrio, dtype=float))
        j = jacobiano(modelo, punto, parametros)
        valores = np.linalg.eigvals(j)
        partes_reales = valores.real
        if np.all(partes_reales < -tolerancia):
            clasificacion = "estable"
        elif np.any(partes_reales > tolerancia):
            clasificacion = "inestable"
        else:
            clasificacion = "no concluyente (hay autovalor con parte real cercana a cero)"
        resultados.append({"equilibrio": punto.tolist(), "jacobiano": j,
                           "autovalores": valores, "clasificacion": clasificacion})
    return resultados


def formatear_equilibrios_numericos(resultados, nombres_variables=None) -> str:
    """
    Tabla de consola para la salida de `analizar_equilibrios` (cálculo numérico):
    equilibrio, autovalores y clasificación, con columnas alineadas.
    """
    if not resultados:
        return "No hay equilibrios para analizar."
    n = len(resultados[0]["equilibrio"])
    nombres = nombres_variables or (["x"] if n == 1 else [f"x{i + 1}" for i in range(n)])
    filas = []
    for i, r in enumerate(resultados, start=1):
        punto = ", ".join(f"{nombres[k]} = {v:.6g}" for k, v in enumerate(r["equilibrio"]))
        autovalores = "; ".join(formatear_complejo(z) for z in r["autovalores"])
        clasif = r["clasificacion"].split(" (")[0].upper()
        filas.append([i, punto, autovalores, clasif])
    return "\n".join(_tabla(["N°", "Equilibrio", "Autovalores del Jacobiano", "Clasificación"], filas))


# ---------------------------------------------------------------------------
# 12. ADAPTADOR PARA LOS MODELOS DE REFERENCIA DEL GRUPO
# ---------------------------------------------------------------------------
# LIMITACIÓN: `modelos_referencia.py` define cada modelo solo como función
# numérica, sin su forma en texto, y no es un archivo de este módulo. Por eso
# las ecuaciones equivalentes se declaran aquí. Cambio mínimo sugerido al
# responsable de `modelos_referencia.py`: añadir a cada entrada de MODELOS una
# clave "ecuaciones" (lista de textos) y "variables"; entonces esta tabla puede
# eliminarse y leerse directamente de allí.

ECUACIONES_REFERENCIA: Dict[str, Dict[str, Any]] = {
    "lineal": {"variables": ["x"], "equations": ["-a*x"], "defaults": {"a": 2.0}},
    "logistico": {"variables": ["x"], "equations": ["r*x*(1 - x/K)"],
                  "defaults": {"r": 1.0, "K": 10.0}},
    "lorenz": {"variables": ["x", "y", "z"],
               "equations": ["sigma*(y - x)", "x*(rho - z) - y", "x*y - beta*z"],
               "defaults": {"sigma": 10.0, "rho": 28.0, "beta": 8.0 / 3.0}},
}


def analizar_estabilidad_referencia(nombre: str, parametros: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Análisis simbólico de un modelo de referencia ("lineal", "logistico", "lorenz")."""
    clave = str(nombre).lower().strip()
    if clave not in ECUACIONES_REFERENCIA:
        return {
            "analysis": "stability", "valid": False, "reason": "invalid_input",
            "message": f"Modelo de referencia desconocido: {nombre!r}. "
                       f"Opciones: {', '.join(ECUACIONES_REFERENCIA)}.",
            "stage": "adaptador",
        }
    base = ECUACIONES_REFERENCIA[clave]
    params = dict(base["defaults"])
    params.update(parametros or {})
    return analizar_estabilidad({
        "variables": list(base["variables"]),
        "equations": list(base["equations"]),
        "parameters": params,
    })


__all__ = [
    # contrato simbólico (Christian)
    "analizar_estabilidad",
    "analizar_estabilidad_referencia",
    "calcular_equilibrios",
    "verificar_equilibrio",
    "calcular_jacobiano",
    "calcular_autovalores",
    "clasificar_estabilidad",
    "clasificar_tipo_cualitativo",
    "ErrorAnalisisEstabilidad",
    "RAZONES",
    # contrato numérico del grupo
    "jacobiano",
    "analizar_equilibrios",
    # consola
    "formatear_reporte_estabilidad",
    "imprimir_reporte_estabilidad",
    "formatear_equilibrios_numericos",
    "formatear_error_consola",
    "titulo_consola",
    "separador_consola",
    "campo_consola",
    "formatear_numero",
    "formatear_complejo",
]
