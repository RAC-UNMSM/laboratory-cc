"""Módulo de Cálculo 3: Funciones Multivariable, Geometría en R³ y Optimización.

Este módulo provee herramientas simbólicas con SymPy para:
  - Vector gradiente en R² y R³.
  - Derivadas direccionales en cualquier dirección vectorial.
  - Planos tangentes a superficies z = f(x,y).
  - Puntos críticos y su clasificación con el determinante del Hessiano.
  - Optimización restringida mediante multiplicadores de Lagrange.
"""

from __future__ import annotations

import ast
from functools import wraps
import sympy as sp

# Diccionarios de funciones y constantes permitidas para el análisis del AST
FUNCIONES_ADMITIDAS = {
    nombre: getattr(sp, nombre)
    for nombre in (
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'exp', 'log', 'Abs'
    )
}

CONSTANTES_ADMITIDAS = {'pi': sp.pi, 'E': sp.E, 'oo': sp.oo}


def _crear_simbolo(nom: str) -> sp.Symbol:
    """Valida y genera un símbolo real de SymPy."""
    if (
        not isinstance(nom, str)
        or not nom.strip()
        or not nom.isidentifier()
        or nom.startswith('_')
        or nom in FUNCIONES_ADMITIDAS
        or nom in CONSTANTES_ADMITIDAS
        or nom == 'sqrt'
        or len(nom) > 20
    ):
        raise ValueError(f"El nombre '{nom}' no es válido para una variable.")
    return sp.Symbol(nom, real=True)


def _obtener_variables(cadena_vars: str) -> list[sp.Symbol]:
    """Convierte una cadena de texto separada por comas en una lista de símbolos."""
    if not isinstance(cadena_vars, str) or not cadena_vars.strip():
        raise ValueError("Se debe especificar al menos una variable.")
    elementos = [v.strip() for v in cadena_vars.split(',') if v.strip()]
    if not elementos:
        raise ValueError("La lista de variables no contiene elementos válidos.")
    return [_crear_simbolo(v) for v in elementos]


def _parsear_expr(texto: str, vars_permitidas: list[sp.Symbol]) -> sp.Expr:
    """Analiza el texto y genera un árbol AST seguro sin usar eval ni sympify directo."""
    if not isinstance(texto, str) or not texto.strip() or len(texto) > 500:
        raise ValueError("La expresión debe ser texto no vacío y tener menos de 500 caracteres.")

    # Reemplazamos acentos de potencia si el usuario escribe ^ en vez de **
    arbol = ast.parse(texto.replace('^', '**'), mode='eval')
    if sum(1 for _ in ast.walk(arbol)) > 150:
        raise ValueError("La estructura matemática es demasiado compleja.")

    mapa_vars = {str(v): v for v in vars_permitidas}

    def _evaluar_nodo(nodo):
        if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
            val = sp.Rational(str(nodo.value))
            if abs(val) > 1000000:
                raise ValueError("Constante numérica fuera del rango aceptado.")
            return val

        if isinstance(nodo, ast.Name):
            if nodo.id in mapa_vars:
                return mapa_vars[nodo.id]
            if nodo.id in CONSTANTES_ADMITIDAS:
                return CONSTANTES_ADMITIDAS[nodo.id]
            raise ValueError(f"Variable o símbolo no declarado: '{nodo.id}'.")

        if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.UAdd, ast.USub)):
            sub_v = _evaluar_nodo(nodo.operand)
            return sub_v if isinstance(nodo.op, ast.UAdd) else sp.Mul(-1, sub_v, evaluate=False)

        if isinstance(nodo, ast.BinOp):
            izq, der = _evaluar_nodo(nodo.left), _evaluar_nodo(nodo.right)
            if isinstance(nodo.op, ast.Add):
                return sp.Add(izq, der, evaluate=False)
            if isinstance(nodo.op, ast.Sub):
                return sp.Add(izq, sp.Mul(-1, der, evaluate=False), evaluate=False)
            if isinstance(nodo.op, ast.Mult):
                return sp.Mul(izq, der, evaluate=False)
            if isinstance(nodo.op, ast.Div):
                return sp.Mul(izq, sp.Pow(der, -1, evaluate=False), evaluate=False)
            if isinstance(nodo.op, ast.Pow):
                if der.is_number and (der.is_finite is not True or abs(der) > 100):
                    raise ValueError("Exponente fuera de límites seguros.")
                return sp.Pow(izq, der, evaluate=False)

        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and not nodo.keywords:
            if len(nodo.args) != 1:
                raise ValueError("Las funciones matemáticas deben tener un único argumento.")
            arg_v = _evaluar_nodo(nodo.args[0])
            if nodo.func.id == 'sqrt':
                return sp.Pow(arg_v, sp.Rational(1, 2), evaluate=False)
            if nodo.func.id in FUNCIONES_ADMITIDAS:
                return FUNCIONES_ADMITIDAS[nodo.func.id](arg_v, evaluate=False)

        raise ValueError("Operación o sintaxis no reconocida.")

    return _evaluar_nodo(arbol.body)


def _convertir_valores(texto_vector: str, dim_esperada: int) -> list[sp.Expr]:
    """Procesa un punto o vector ingresado como texto y verifica sus dimensiones."""
    if not isinstance(texto_vector, str) or not texto_vector.strip():
        raise ValueError("Vector/punto inválido o vacío.")
    componentes = [c.strip() for c in texto_vector.split(',') if c.strip()]
    if len(componentes) != dim_esperada:
        raise ValueError(f"Dimensión incorrecta: se esperaban {dim_esperada} componentes y se leyeron {len(componentes)}.")

    lista_num = []
    for c in componentes:
        num = sp.simplify(_parsear_expr(c, []))
        if num.is_real is not True or num.is_finite is not True:
            raise ValueError("Las componentes deben ser valores reales finitos.")
        lista_num.append(num)
    return lista_num


def _formatear_dato(v) -> dict[str, str]:
    """Devuelve representación en texto legible y LaTeX de un objeto SymPy."""
    return {'exacto': sp.sstr(v), 'latex': sp.latex(v)}


def _construir_respuesta(nombre_op: str, datos: dict, historial_pasos: list[str], modo_trabajo: str) -> dict:
    """Empaqueta la salida respetando el formato de estado y modo."""
    if modo_trabajo not in ('examen', 'paso_a_paso'):
        raise ValueError("El modo debe ser 'examen' o 'paso_a_paso'.")
    return {
        'estado': 'ok',
        'operacion': nombre_op,
        'modo': modo_trabajo,
        'datos': datos,
        'pasos': historial_pasos if modo_trabajo == 'paso_a_paso' else historial_pasos[-1:]
    }


def _manejador_errores(func):
    """Decorador para capturar fallos sin romper el servidor MCP."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (ValueError, SyntaxError, TypeError, RecursionError) as err:
            return {'estado': 'error', 'mensaje': str(err)}
        except (NotImplementedError, RuntimeError, ArithmeticError) as err:
            return {'estado': 'no_determinado', 'mensaje': str(err)}
    return wrapper


# =============================================================================
# FUNCIONES PRINCIPALES DE CÁLCULO 3
# =============================================================================

@_manejador_errores
def calcular_gradiente(
    expresion: str, variables: str = "x, y, z", punto: str | None = None, modo: str = "paso_a_paso"
) -> dict:
    """Calcula el vector gradiente (∇f) y opcionalmente evalúa sus componentes en un punto."""
    vars_simb = _obtener_variables(variables)
    f = _parsear_expr(expresion, vars_simb)

    pasos = [f"Función objetivo f({', '.join(sp.sstr(v) for v in vars_simb)}) = {f}."]
    gradiente_sym = [sp.simplify(sp.diff(f, v)) for v in vars_simb]
    pasos.append(f"Cálculo de derivadas parciales para el gradiente: ∇f = {gradiente_sym}.")

    datos_salida = {
        'funcion': _formatear_dato(f),
        'variables': [_formatear_dato(v) for v in vars_simb],
        'gradiente': [_formatear_dato(g) for g in gradiente_sym],
        'gradiente_vector': _formatear_dato(sp.Matrix(gradiente_sym))
    }

    if punto:
        valores_punto = _convertir_valores(punto, len(vars_simb))
        mapa_sust = dict(zip(vars_simb, valores_punto))
        gradiente_eval = [sp.simplify(g.subs(mapa_sust)) for g in gradiente_sym]
        pasos.append(f"Evaluación del gradiente en el punto {valores_punto}: ∇f(P) = {gradiente_eval}.")
        datos_salida['punto'] = [_formatear_dato(p) for p in valores_punto]
        datos_salida['gradiente_evaluado'] = [_formatear_dato(ge) for ge in gradiente_eval]

    return _construir_respuesta('gradiente', datos_salida, pasos, modo)


@_manejador_errores
def calcular_derivada_direccional(
    expresion: str, punto: str, direccion: str, variables: str = "x, y, z", modo: str = "paso_a_paso"
) -> dict:
    """Calcula la derivada direccional de f en un punto P a lo largo de un vector v."""
    vars_simb = _obtener_variables(variables)
    f = _parsear_expr(expresion, vars_simb)
    p_num = _convertir_valores(punto, len(vars_simb))
    v_num = _convertir_valores(direccion, len(vars_simb))

    mat_v = sp.Matrix(v_num)
    magnitud_v = sp.simplify(mat_v.norm())
    if magnitud_v == 0:
        raise ValueError("El vector dirección no puede ser nulo.")

    mat_u = sp.simplify(mat_v / magnitud_v)
    pasos = [
        f"Punto de evaluación P = {p_num}.",
        f"Vector dirección v = {v_num} con norma ||v|| = {magnitud_v}.",
        f"Vector unitario u = {list(mat_u)}."
    ]

    grad_sym = [sp.simplify(sp.diff(f, v)) for v in vars_simb]
    mapa_p = dict(zip(vars_simb, p_num))
    grad_eval = sp.Matrix([sp.simplify(g.subs(mapa_p)) for g in grad_sym])

    pasos.append(f"Gradiente en P: ∇f(P) = {list(grad_eval)}.")

    d_u_f = sp.simplify(grad_eval.dot(mat_u))
    pasos.append(f"Producto escalar D_u f(P) = ∇f(P) · u = {d_u_f}.")

    datos_salida = {
        'funcion': _formatear_dato(f),
        'punto': [_formatear_dato(p) for p in p_num],
        'vector_direccion': [_formatear_dato(v) for v in v_num],
        'vector_unitario': [_formatear_dato(u) for u in mat_u],
        'gradiente_en_punto': [_formatear_dato(g) for g in grad_eval],
        'derivada_direccional': _formatear_dato(d_u_f)
    }

    return _construir_respuesta('derivada_direccional', datos_salida, pasos, modo)


@_manejador_errores
def plano_tangente(
    expresion: str, punto: str, variables: str = "x, y", modo: str = "paso_a_paso"
) -> dict:
    """Calcula el plano tangente a la superficie z = f(x,y) en un punto (x0, y0)."""
    vars_simb = _obtener_variables(variables)
    if len(vars_simb) != 2:
        raise ValueError("El plano tangente z = f(x,y) aplica únicamente para 2 variables de entrada.")

    var_x, var_y = vars_simb[0], vars_simb[1]
    f = _parsear_expr(expresion, vars_simb)
    p_num = _convertir_valores(punto, 2)
    px, py = p_num[0], p_num[1]

    pz = sp.simplify(f.subs({var_x: px, var_y: py}))
    df_dx = sp.simplify(sp.diff(f, var_x).subs({var_x: px, var_y: py}))
    df_dy = sp.simplify(sp.diff(f, var_y).subs({var_x: px, var_y: py}))

    eje_z = sp.Symbol('z', real=True)
    eq_plano = sp.simplify(pz + df_dx * (var_x - px) + df_dy * (var_y - py))
    forma_implicita = sp.simplify(df_dx * (var_x - px) + df_dy * (var_y - py) - (eje_z - pz))

    pasos = [
        f"Superficie f({var_x}, {var_y}) = {f}.",
        f"Punto base: ({px}, {py}), con z0 = {pz}.",
        f"Pendientes parciales: f_x({px},{py}) = {df_dx}, f_y({px},{py}) = {df_dy}.",
        f"Ecuación explícita del plano: z = {eq_plano}."
    ]

    datos_salida = {
        'funcion': _formatear_dato(f),
        'punto_xy': [_formatear_dato(px), _formatear_dato(py)],
        'z0': _formatear_dato(pz),
        'fx_eval': _formatear_dato(df_dx),
        'fy_eval': _formatear_dato(df_dy),
        'plano_tangente_z': _formatear_dato(eq_plano),
        'plano_forma_general': _formatear_dato(sp.Eq(forma_implicita, 0))
    }

    return _construir_respuesta('plano_tangente', datos_salida, pasos, modo)


@_manejador_errores
def analizar_puntos_criticos(
    expresion: str, variables: str = "x, y", modo: str = "paso_a_paso"
) -> dict:
    """Encuentra los puntos críticos resolviendo ∇f = 0 y los clasifica mediante la matriz Hessiana."""
    vars_simb = _obtener_variables(variables)
    f = _parsear_expr(expresion, vars_simb)

    grad = [sp.simplify(sp.diff(f, v)) for v in vars_simb]
    sistema = [sp.Eq(g, 0) for g in grad]

    pasos = [
        f"Gradiente f: ∇f = {grad}.",
        "Igualando componentes a cero para buscar puntos estacionarios."
    ]

    soluciones = sp.solve(sistema, vars_simb, dict=True)
    if not soluciones:
        return _construir_respuesta('puntos_criticos', {'puntos': []}, pasos + ["No existen puntos críticos reales."], modo)

    matriz_h = sp.Matrix([[sp.diff(f, v1, v2) for v2 in vars_simb] for v1 in vars_simb])
    pasos.append(f"Matriz Hessiana de f: H = {matriz_h}.")

    lista_clasificada = []
    for sol in soluciones:
        pto_str = {sp.sstr(k): sp.sstr(v) for k, v in sol.items()}
        h_evaluada = matriz_h.subs(sol)

        if len(vars_simb) == 2:
            det_h = sp.simplify(h_evaluada.det())
            f_xx = sp.simplify(h_evaluada[0, 0])

            if det_h > 0:
                categoria = "Mínimo local" if f_xx > 0 else "Máximo local"
            elif det_h < 0:
                categoria = "Punto silla"
            else:
                categoria = "Indeterminado (det H = 0)"

            pasos.append(f"Punto {pto_str} -> det(H) = {det_h}, f_xx = {f_xx} => {categoria}.")
            lista_clasificada.append({'punto': pto_str, 'det_hessiano': _formatear_dato(det_h), 'tipo': categoria})
        else:
            pasos.append(f"Punto crítico hallado: {pto_str}.")
            lista_clasificada.append({'punto': pto_str, 'tipo': "Analizar autovalores de la Hessiana para dimensiones superiores"})

    datos_salida = {
        'funcion': _formatear_dato(f),
        'hessiana': _formatear_dato(matriz_h),
        'puntos_criticos': lista_clasificada
    }

    return _construir_respuesta('puntos_criticos', datos_salida, pasos, modo)


@_manejador_errores
def optimizar_lagrange(
    expresion: str, restriccion: str, variables: str = "x, y", modo: str = "paso_a_paso"
) -> dict:
    """Aplica multiplicadores de Lagrange para optimizar f(x,y) sujeta a g(x,y) = 0."""
    vars_simb = _obtener_variables(variables)
    f = _parsear_expr(expresion, vars_simb)
    g = _parsear_expr(restriccion, vars_simb)

    lam = sp.Symbol('lambda', real=True)
    f_lagrange = f - lam * g
    sistema_lagrange = [sp.simplify(sp.diff(f_lagrange, v)) for v in vars_simb] + [sp.simplify(-g)]

    pasos = [
        f"Función objetivo: f = {f}.",
        f"Restricción: g = {g} = 0.",
        "Construyendo el sistema de ecuaciones ∇f = λ∇g junto con g = 0."
    ]

    eqs_lagrange = [sp.Eq(eq, 0) for eq in sistema_lagrange]
    soluciones = sp.solve(eqs_lagrange, vars_simb + [lam], dict=True)

    lista_candidatos = []
    for sol in soluciones:
        coordenadas = {sp.sstr(v): _formatear_dato(sp.simplify(sol[v])) for v in vars_simb}
        val_objetivo = sp.simplify(f.subs(sol))
        val_lambda = _formatear_dato(sp.simplify(sol[lam]))
        lista_candidatos.append({
            'punto': coordenadas,
            'lambda': val_lambda,
            'valor_f': _formatear_dato(val_objetivo)
        })
        pasos.append(f"Solución encontrada en {coordenadas}: f = {val_objetivo}, λ = {val_lambda['exacto']}.")

    datos_salida = {
        'funcion': _formatear_dato(f),
        'restriccion_cero': _formatear_dato(g),
        'candidatos': lista_candidatos
    }

    return _construir_respuesta('optimizar_lagrange', datos_salida, pasos, modo)


# =============================================================================
# REGISTRO Y TEST
# =============================================================================

HERRAMIENTAS = (
    calcular_gradiente,
    calcular_derivada_direccional,
    plano_tangente,
    analizar_puntos_criticos,
    optimizar_lagrange,
)


def registrar_herramientas(mcp) -> None:
    """Registra las 5 herramientas en el servidor FastMCP."""
    for herramienta in HERRAMIENTAS:
        mcp.tool()(herramienta)


def ejecutar_pruebas() -> bool:
    """Ejecuta los tests unitarios locales."""
    import json
    import unittest

    class TestCalculo3Custom(unittest.TestCase):
        def test_gradiente(self):
            res = calcular_gradiente("x**2*y + z**3", "x, y, z")
            self.assertEqual(res['estado'], 'ok')
            grads = [g['exacto'] for g in res['datos']['gradiente']]
            self.assertEqual(grads, ['2*x*y', 'x**2', '3*z**2'])

        def test_derivada_direccional(self):
            res = calcular_derivada_direccional("x**2 + y**2", "1, 1", "3, 4", "x, y")
            self.assertEqual(res['estado'], 'ok')
            self.assertEqual(res['datos']['derivada_direccional']['exacto'], '14/5')

        def test_plano_tangente(self):
            res = plano_tangente("x**2 + y**2", "1, 2", "x, y")
            self.assertEqual(res['estado'], 'ok')
            self.assertEqual(res['datos']['plano_tangente_z']['exacto'], '2*x + 4*y - 5')

        def test_puntos_criticos(self):
            res = analizar_puntos_criticos("x**3 + y**3 - 3*x - 12*y", "x, y")
            self.assertEqual(res['estado'], 'ok')
            self.assertEqual(len(res['datos']['puntos_criticos']), 4)

        def test_lagrange(self):
            res = optimizar_lagrange("x*y", "x**2 + y**2 - 1", "x, y")
            self.assertEqual(res['estado'], 'ok')
            self.assertTrue(len(res['datos']['candidatos']) >= 4)

        def test_json(self):
            res = calcular_gradiente("x**2 + y**2", "x, y")
            self.assertEqual(json.loads(json.dumps(res)), res)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestCalculo3Custom)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main() -> int:
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Módulo de Cálculo Multivariable R³ - Grupo 02')
    grupo_opciones = parser.add_mutually_exclusive_group()
    grupo_opciones.add_argument('--test', action='store_true', help='Ejecuta las pruebas unitarias.')
    grupo_opciones.add_argument('--demo', action='store_true', help='Imprime salidas JSON de demostración.')
    args = parser.parse_args()

    if args.test:
        return 0 if ejecutar_pruebas() else 1
    if args.demo:
        demo_json = {
            'gradiente': calcular_gradiente("x**2*y + z**3", "x, y, z", "1, 2, 3"),
            'derivada_direccional': calcular_derivada_direccional("x**2 + y**2", "1, 1", "3, 4", "x, y"),
            'plano_tangente': plano_tangente("x**2 + y**2", "1, 2", "x, y"),
            'puntos_criticos': analizar_puntos_criticos("x**3 + y**3 - 3*x - 12*y", "x, y"),
            'lagrange': optimizar_lagrange("x*y", "x**2 + y**2 - 1", "x, y")
        }
        print(json.dumps(demo_json, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
