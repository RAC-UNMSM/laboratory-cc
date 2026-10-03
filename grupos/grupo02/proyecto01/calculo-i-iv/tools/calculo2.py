"""Módulo de Cálculo II: Integral, Técnicas de Integración y Aplicaciones (Python >= 3.10).

Ruta recomendada: tools/calculo2.py
Dependencia: pip install sympy==1.14.0

API pública (6 herramientas correspondientes a los 6 temas):
  1. calcular_integral_indefinida   (Tema a: inmediatas, cambio de variable, por partes)
  2. tecnicas_avanzadas_integracion (Tema b: fracciones parciales, trigonométricas, Euler/Chebyshev)
  3. riemann_y_teorema_fundamental  (Tema c: sumas de Riemann finitas/límites y TFC I/II)
  4. aplicaciones_geometricas       (Tema d: área entre curvas, volumen de revolución, longitud de arco)
  5. centro_masa_e_integracion_num  (Tema e: centroide/Pappus y cuadratura Trapecio/Simpson)
  6. integrales_impropias_gamma_beta(Tema f: impropias tipo I/II, convergencia y Gamma/Beta)
  + registrar_herramientas

Uso por consola:
    python calculo2.py --test       # ejecuta las pruebas unitarias incorporadas
    python calculo2.py --demo       # muestra ejemplos de salida en formato JSON
    python calculo2.py --help       # ayuda de uso
"""
from __future__ import annotations
import ast
from functools import wraps
import json
import sys
import unittest
import sympy as sp
from sympy.calculus.util import continuous_domain

# Funciones y constantes admitidas en el analizador seguro
FUNCIONES = {
    n: getattr(sp, n)
    for n in (
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
        'sinh', 'cosh', 'tanh', 'exp', 'log', 'Abs',
        'gamma', 'beta'
    )
}
CONSTANTES = {'pi': sp.pi, 'E': sp.E, 'oo': sp.oo}


def _simbolo(nombre: str) -> sp.Symbol:
    if (not isinstance(nombre, str) or not nombre.isidentifier()
            or nombre.startswith('_') or nombre in FUNCIONES
            or nombre in CONSTANTES or nombre == 'sqrt' or len(nombre) > 24):
        raise ValueError('Nombre de variable inválido o reservado.')
    return sp.Symbol(nombre, real=True)


def _parsear(texto: str, variables: list[sp.Symbol]) -> sp.Expr:
    """Construye un AST seguro sin recurrir a eval o sympify sin filtrar."""
    if not isinstance(texto, str) or not texto.strip() or len(texto) > 500:
        raise ValueError('La expresión debe tener entre 1 y 500 caracteres.')
    arbol = ast.parse(texto.replace('^', '**'), mode='eval')
    if sum(1 for _ in ast.walk(arbol)) > 150:
        raise ValueError('Expresión demasiado compleja.')
    nombres = {str(v): v for v in variables}

    def visitar(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            valor = sp.Rational(str(n.value))
            if abs(valor) > 1000000:
                raise ValueError('Constante numérica fuera del límite permitido.')
            return valor
        if isinstance(n, ast.Name):
            if n.id in nombres:
                return nombres[n.id]
            if n.id in CONSTANTES:
                return CONSTANTES[n.id]
            raise ValueError(f'Símbolo no permitido: {n.id}.')
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = visitar(n.operand)
            return v if isinstance(n.op, ast.UAdd) else sp.Mul(-1, v, evaluate=False)
        if isinstance(n, ast.BinOp):
            a, b = visitar(n.left), visitar(n.right)
            if isinstance(n.op, ast.Add):
                return sp.Add(a, b, evaluate=False)
            if isinstance(n.op, ast.Sub):
                return sp.Add(a, sp.Mul(-1, b, evaluate=False), evaluate=False)
            if isinstance(n.op, ast.Mult):
                return sp.Mul(a, b, evaluate=False)
            if isinstance(n.op, ast.Div):
                return sp.Mul(a, sp.Pow(b, -1, evaluate=False), evaluate=False)
            if isinstance(n.op, ast.Pow):
                if b.is_number and (b.is_finite is not True or abs(b) > 100):
                    raise ValueError('Exponente numérico fuera de rango [-100, 100].')
                return sp.Pow(a, b, evaluate=False)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and not n.keywords:
            if n.func.id == 'sqrt':
                if len(n.args) != 1:
                    raise ValueError('sqrt admite solo un argumento.')
                return sp.Pow(visitar(n.args[0]), sp.Rational(1, 2), evaluate=False)
            if n.func.id == 'beta':
                if len(n.args) != 2:
                    raise ValueError('beta requiere exactamente 2 argumentos.')
                return sp.beta(visitar(n.args[0]), visitar(n.args[1]), evaluate=False)
            if n.func.id in FUNCIONES:
                if len(n.args) != 1:
                    raise ValueError(f'{n.func.id} admite solo 1 argumento.')
                return FUNCIONES[n.func.id](visitar(n.args[0]), evaluate=False)
        raise ValueError('Sintaxis u operación no permitida.')

    resultado = visitar(arbol.body)
    if variables:
        for sub in sp.preorder_traversal(resultado):
            if isinstance(sub, sp.Expr) and sub.is_number:
                val = sp.simplify(sub)
                if val.is_finite is not True or val.is_real is not True:
                    raise ValueError('La expresión contiene constantes no reales o no finitas.')
    return resultado


def _punto(texto: str) -> sp.Expr:
    p = sp.simplify(_parsear(texto, []))
    if p not in (sp.oo, -sp.oo) and (p.is_real is not True or p.is_finite is not True):
        raise ValueError('El punto/límite debe ser real finito o infinito (+oo, -oo).')
    return p


def _dato(v) -> dict[str, str]:
    return {'exacto': sp.sstr(v), 'latex': sp.latex(v)}


def _salida(operacion: str, datos: dict, pasos: list[str], modo: str) -> dict:
    if modo not in ('examen', 'paso_a_paso'):
        raise ValueError("modo debe ser 'examen' o 'paso_a_paso'.")
    return {
        'estado': 'ok',
        'operacion': operacion,
        'modo': modo,
        'datos': datos,
        'pasos': pasos if modo == 'paso_a_paso' else pasos[-1:]
    }


def _api(fn):
    @wraps(fn)
    def protegida(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, SyntaxError, TypeError, RecursionError) as exc:
            return {'estado': 'error', 'mensaje': str(exc)}
        except (NotImplementedError, RuntimeError, ArithmeticError) as exc:
            return {'estado': 'no_determinado', 'mensaje': str(exc)}
    return protegida


# =====================================================================
# TEMA A: Antiderivada e Integral Indefinida
# =====================================================================
@_api
def calcular_integral_indefinida(
    expresion: str,
    variable: str = 'x',
    metodo_sugerido: str = 'auto',
    modo: str = 'paso_a_paso'
) -> dict:
    """Calcula antiderivadas e integrales indefinidas reconociendo el método aplicable."""
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    pasos = [f'Integrando: f({x}) = {f}']

    # Clasificación didáctica del método
    metodo_detectado = 'inmediata'
    if metodo_sugerido != 'auto':
        metodo_detectado = metodo_sugerido
    elif isinstance(f, sp.Mul) and any(a.has(x) for a in f.args):
        sub_exprs = [a for a in f.args if a.has(x)]
        if len(sub_exprs) >= 2 and any(isinstance(a, (sp.exp, sp.sin, sp.cos, sp.log)) for a in sub_exprs):
            metodo_detectado = 'por_partes'
        else:
            metodo_detectado = 'cambio_de_variable'
    elif f.has(sp.log) or any(isinstance(sub, (sp.asin, sp.acos, sp.atan)) for sub in sp.preorder_traversal(f)):
        metodo_detectado = 'por_partes'

    pasos.append(f'Método principal identificado: {metodo_detectado}.')

    antiderivada = sp.integrate(f, x)
    if antiderivada.has(sp.Integral):
        return {'estado': 'no_determinado', 'mensaje': 'SymPy no pudo encontrar una primitiva elemental cerrada.'}

    antiderivada_simplificada = sp.simplify(antiderivada)
    pasos.append(f'Primitiva F({x}) = {antiderivada_simplificada}.')
    pasos.append(f'Resultado general: {antiderivada_simplificada} + C.')

    # Verificación por derivación
    verificacion = sp.simplify(sp.diff(antiderivada_simplificada, x) - f) == 0

    datos = {
        'integrando': _dato(f),
        'antiderivada': _dato(antiderivada_simplificada),
        'antiderivada_con_constante': f"{sp.sstr(antiderivada_simplificada)} + C",
        'metodo': metodo_detectado,
        'verificado_por_derivacion': verificacion
    }
    return _salida('integral_indefinida', datos, pasos, modo)


# =====================================================================
# TEMA B: Técnicas Avanzadas de Integración
# =====================================================================
@_api
def tecnicas_avanzadas_integracion(
    expresion: str,
    variable: str = 'x',
    tecnica: str = 'auto',
    modo: str = 'paso_a_paso'
) -> dict:
    """Resuelve integrales por fracciones parciales, trigonométricas, Euler o Chebyshev[cite: 1]."""
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    pasos = [f'Analizando integrando avanzado: {f}']
    datos_adicionales = {}

    r = sp.cancel(f)
    if tecnica == 'fracciones_parciales' or (tecnica == 'auto' and r.is_rational_function(x)):
        tecnica_real = 'fracciones_parciales'
        desc = sp.apart(f, x)
        pasos.append(f'Descomposición en fracciones simples: {desc}')
        datos_adicionales['fracciones_parciales'] = _dato(desc)
    elif tecnica == 'trigonometrica' or (tecnica == 'auto' and (f.has(sp.sin) or f.has(sp.cos) or f.has(sp.tan))):
        tecnica_real = 'trigonometrica'
        pasos.append('Aplicando identidades trigonométricas y sustituciones estándar (o Weierstrass t=tan(x/2)).')
    elif tecnica in ('euler', 'chebyshev') or (tecnica == 'auto' and f.has(sp.sqrt)):
        tecnica_real = 'sustitucion_irracional_euler_o_chebyshev'
        pasos.append('Identificado integrando con radicales: sustitución de Euler o monomios de Chebyshev.')
    else:
        tecnica_real = 'avanzada_general'

    resultado = sp.integrate(f, x)
    if resultado.has(sp.Integral):
        return {'estado': 'no_determinado', 'mensaje': f'Técnica {tecnica_real} no produjo primitiva elemental.'}

    resultado_simp = sp.simplify(resultado)
    pasos.append(f'Integración completada: {resultado_simp} + C.')

    datos = {
        'integrando': _dato(f),
        'tecnica_utilizada': tecnica_real,
        'resultado': _dato(resultado_simp),
        **datos_adicionales
    }
    return _salida('tecnicas_avanzadas', datos, pasos, modo)


# =====================================================================
# TEMA C: Sumas de Riemann y Teorema Fundamental del Cálculo (TFC)
# =====================================================================
@_api
def riemann_y_teorema_fundamental(
    expresion: str,
    a_str: str,
    b_str: str,
    n_particiones: int | None = None,
    regla_riemann: str = 'derecha',
    variable: str = 'x',
    modo: str = 'paso_a_paso'
) -> dict:
    """Calcula aproximaciones por sumas de Riemann y la integral exacta mediante el TFC[cite: 1]."""
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    a = _punto(a_str)
    b = _punto(b_str)
    pasos = [f'Función f({x}) = {f} en el intervalo [{a}, {b}].']

    # 1. TFC (Parte II): F(b) - F(a)
    F = sp.integrate(f, x)
    integral_exacta = sp.integrate(f, (x, a, b))
    pasos.append(f'Primitiva F({x}) = {F}.')
    pasos.append(f'Por TFC II: Integral exacta = F({b}) - F({a}) = {integral_exacta}.')

    datos = {
        'integral_exacta': _dato(integral_exacta),
        'primitiva_F': _dato(F),
        'tfc_evaluacion': f"F({b}) - F({a}) = {sp.sstr(integral_exacta)}"
    }

    # 2. Sumas de Riemann discretas (si se especifica n)
    if n_particiones is not None:
        if n_particiones <= 0 or n_particiones > 5000:
            raise ValueError('n_particiones debe ser un entero positivo <= 5000.')
        delta_x = (b - a) / n_particiones
        k = sp.Symbol('k', integer=True)
        if regla_riemann == 'izquierda':
            x_k = a + (k - 1) * delta_x
        elif regla_riemann == 'derecha':
            x_k = a + k * delta_x
        elif regla_riemann == 'medio':
            x_k = a + (k - sp.Rational(1, 2)) * delta_x
        else:
            raise ValueError("regla_riemann debe ser 'izquierda', 'derecha' o 'medio'.")

        termino_suma = f.subs(x, x_k)
        suma_simb = sp.Sum(termino_suma * delta_x, (k, 1, n_particiones))
        valor_suma = sp.N(suma_simb.doit())

        pasos.append(f'Suma de Riemann ({regla_riemann}, n={n_particiones}): Δx = {delta_x}.')
        pasos.append(f'Valor estimado de la suma: {valor_suma}.')
        datos['riemann'] = {
            'n': n_particiones,
            'regla': regla_riemann,
            'delta_x': _dato(delta_x),
            'valor_aproximado': str(valor_suma)
        }

    return _salida('riemann_tfc', datos, pasos, modo)


# =====================================================================
# TEMA D: Aplicaciones Geométricas de la Integral
# =====================================================================
@_api
def aplicaciones_geometricas(
    tipo: str,
    f_str: str,
    g_str: str = '0',
    a_str: str = '0',
    b_str: str = '1',
    eje_giro: str = 'x',
    variable: str = 'x',
    modo: str = 'paso_a_paso'
) -> dict:
    """Calcula áreas planas, volúmenes de revolución (discos/arandelas) o longitud de arco[cite: 1]."""
    x = _simbolo(variable)
    f = _parsear(f_str, [x])
    g = _parsear(g_str, [x])
    a = _punto(a_str)
    b = _punto(b_str)

    if a >= b:
        raise ValueError('Se requiere un intervalo con a < b.')

    pasos = []
    if tipo == 'area':
        pasos.append(f'Calculando área entre f({x})={f} y g({x})={g} en [{a}, {b}].')
        diff_fg = sp.simplify(f - g)
        integral_area = sp.integrate(sp.Abs(diff_fg), (x, a, b))
        pasos.append(f'Área = ∫ |f(x) - g(x)| dx = {integral_area}.')
        datos = {'area': _dato(integral_area)}

    elif tipo == 'volumen_revolucion':
        pasos.append(f'Calculando volumen al rotar f({x})={f} (radio sup.) y g({x})={g} (radio inf.) respecto al eje {eje_giro}.')
        if eje_giro == 'x':
            # Método de arandelas: V = pi * integral (R^2 - r^2) dx
            integrando = sp.pi * (f**2 - g**2)
            volumen = sp.integrate(integrando, (x, a, b))
            pasos.append(f'V = π ∫ (({f})² - ({g})²) dx de {a} a {b} = {volumen}.')
        elif eje_giro == 'y':
            # Método de cascarones cilíndricos: V = 2*pi * integral x * (f - g) dx
            integrando = 2 * sp.pi * x * (f - g)
            volumen = sp.integrate(integrando, (x, a, b))
            pasos.append(f'V = 2π ∫ x * ({f} - ({g})) dx de {a} a {b} = {volumen}.')
        else:
            raise ValueError("eje_giro debe ser 'x' o 'y'.")
        datos = {'volumen': _dato(volumen), 'eje': eje_giro}

    elif tipo == 'longitud_arco':
        pasos.append(f'Calculando longitud de arco de f({x})={f} en [{a}, {b}].')
        df = sp.diff(f, x)
        integrando = sp.sqrt(1 + df**2)
        longitud = sp.integrate(integrando, (x, a, b))
        pasos.append(f"L = ∫ √(1 + (f'({x}))²) dx = {longitud}.")
        datos = {'derivada': _dato(df), 'longitud': _dato(longitud)}

    else:
        raise ValueError("tipo debe ser 'area', 'volumen_revolucion' o 'longitud_arco'.")

    return _salida('aplicaciones_geometricas', datos, pasos, modo)


# =====================================================================
# TEMA E: Centro de Masa e Integración Numérica
# =====================================================================
@_api
def centro_masa_e_integracion_num(
    operacion_tipo: str,
    expresion: str,
    a_str: str,
    b_str: str,
    g_str: str = '0',
    n_tramos: int = 10,
    variable: str = 'x',
    modo: str = 'paso_a_paso'
) -> dict:
    """Centroide (teoremas de Pappus) e integración numérica (Trapecio y Simpson)[cite: 1]."""
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    a = _punto(a_str)
    b = _punto(b_str)

    if a >= b:
        raise ValueError('Se requiere a < b.')

    pasos = []
    if operacion_tipo == 'centro_masa':
        g = _parsear(g_str, [x])
        pasos.append(f'Calculando centroide de región entre f({x})={f} y g({x})={g} en [{a}, {b}].')
        h = f - g
        A = sp.integrate(h, (x, a, b))
        if sp.simplify(A) == 0:
            raise ValueError('El área de la región no puede ser cero.')
        # Momentos respecto a los ejes
        M_y = sp.integrate(x * h, (x, a, b))
        M_x = sp.Rational(1, 2) * sp.integrate(f**2 - g**2, (x, a, b))
        x_barra = sp.simplify(M_y / A)
        y_barra = sp.simplify(M_x / A)
        pasos.append(f'Área A = {A}; Momentos: My = {M_y}, Mx = {M_x}.')
        pasos.append(f'Centroide (x̄, ȳ) = ({x_barra}, {y_barra}).')
        datos = {
            'area': _dato(A),
            'centroide': {'x': _dato(x_barra), 'y': _dato(y_barra)},
            'pappus_volumen_eje_x': _dato(2 * sp.pi * y_barra * A)
        }

    elif operacion_tipo in ('trapecio', 'simpson'):
        if n_tramos <= 0:
            raise ValueError('n_tramos debe ser un entero positivo.')
        if operacion_tipo == 'simpson' and n_tramos % 2 != 0:
            raise ValueError('El método de Simpson requiere un número par de subintervalos (n_tramos).')

        h = float((b - a) / n_tramos)
        puntos_x = [float(a + i * h) for i in range(n_tramos + 1)]
        valores_y = [float(sp.N(f.subs(x, px))) for px in puntos_x]

        if operacion_tipo == 'trapecio':
            pasos.append(f'Regla del Trapecio compuesta con n={n_tramos}, h={h:.6f}.')
            aprox = (h / 2.0) * (valores_y[0] + 2 * sum(valores_y[1:-1]) + valores_y[-1])
        else:
            pasos.append(f'Regla de Simpson compuesta (1/3) con n={n_tramos}, h={h:.6f}.')
            suma_impares = sum(valores_y[i] for i in range(1, n_tramos, 2))
            suma_pares = sum(valores_y[i] for i in range(2, n_tramos, 2))
            aprox = (h / 3.0) * (valores_y[0] + 4 * suma_impares + 2 * suma_pares + valores_y[-1])

        pasos.append(f'Aproximación numérica calculada: {aprox:.8f}.')
        datos = {
            'metodo': operacion_tipo,
            'n_tramos': n_tramos,
            'h': str(h),
            'valor_aproximado': str(aprox)
        }
    else:
        raise ValueError("operacion_tipo debe ser 'centro_masa', 'trapecio' o 'simpson'.")

    return _salida('centro_masa_num', datos, pasos, modo)


# =====================================================================
# TEMA F: Integrales Impropias y Funciones Gamma / Beta
# =====================================================================
@_api
def integrales_impropias_gamma_beta(
    expresion: str,
    a_str: str,
    b_str: str,
    variable: str = 'x',
    modo: str = 'paso_a_paso'
) -> dict:
    """Evalúa integrales impropias (tipo I y II), convergencia y funciones Gamma/Beta[cite: 1]."""
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    a = _punto(a_str)
    b = _punto(b_str)

    pasos = [f'Analizando integral impropia de f({x}) = {f} entre {a} y {b}.']

    # Detección de tipo
    tipo_impropia = []
    if a == -sp.oo or b == sp.oo:
        tipo_impropia.append('Tipo I (límites infinitos)')

    # Revisar singularidades en el dominio (Tipo II)
    d = continuous_domain(f, x, sp.Interval(a if a != -sp.oo else -1000, b if b != sp.oo else 1000))
    if not isinstance(d, sp.Interval):
        tipo_impropia.append('Tipo II (discontinuidad infinita en integrando)')

    pasos.append(f"Clasificación: {', '.join(tipo_impropia) if tipo_impropia else 'Propia / Regular'}.")

    resultado = sp.integrate(f, (x, a, b))

    if resultado.has(sp.Integral) or resultado is sp.nan:
        convergente = False
        pasos.append('La integral diverge o no se pudo demostrar su convergencia.')
        datos = {'convergente': False, 'tipo': tipo_impropia}
    else:
        convergente = resultado.is_finite is True
        pasos.append(f'Valor exacto obtenido: {resultado}.')
        pasos.append('Conclusión: Integral convergente.' if convergente else 'Conclusión: Integral divergente.')
        datos = {
            'convergente': convergente,
            'valor': _dato(resultado),
            'tipo': tipo_impropia
        }

    return _salida('impropia_gamma_beta', datos, pasos, modo)


# =====================================================================
# REGISTRO FAST-MCP
# =====================================================================
HERRAMIENTAS_CALCULO2 = (
    calcular_integral_indefinida,
    tecnicas_avanzadas_integracion,
    riemann_y_teorema_fundamental,
    aplicaciones_geometricas,
    centro_masa_e_integracion_num,
    integrales_impropias_gamma_beta,
)


def registrar_herramientas(mcp) -> None:
    """Registra las 6 herramientas de Cálculo II en el servidor FastMCP[cite: 1]."""
    for fn in HERRAMIENTAS_CALCULO2:
        mcp.tool()(fn)


# =====================================================================
# PRUEBAS UNITARIAS
# =====================================================================
def ejecutar_pruebas() -> bool:
    class PruebasCalculo2(unittest.TestCase):
        def test_tema_a_inmediata_y_partes(self):
            # Inmediata
            r1 = calcular_integral_indefinida('x**2')
            self.assertEqual(r1['datos']['antiderivada']['exacto'], 'x**3/3')
            self.assertTrue(r1['datos']['verificado_por_derivacion'])
            # Por partes
            r2 = calcular_integral_indefinida('x*exp(x)')
            self.assertEqual(r2['datos']['metodo'], 'por_partes')
            self.assertTrue(r2['datos']['verificado_por_derivacion'])

        def test_tema_b_fracciones_parciales(self):
            r = tecnicas_avanzadas_integracion('1/(x**2 - 1)', tecnica='fracciones_parciales')
            self.assertEqual(r['estado'], 'ok')
            self.assertIn('fracciones_parciales', r['datos'])

        def test_tema_c_riemann_y_tfc(self):
            r = riemann_y_teorema_fundamental('x', '0', '2', n_particiones=4, regla_riemann='derecha')
            self.assertEqual(r['datos']['integral_exacta']['exacto'], '2')
            self.assertAlmostEqual(float(r['datos']['riemann']['valor_aproximado']), 2.5)

        def test_tema_d_area_y_volumen(self):
            # Área bajo y=x en [0, 2]
            ra = aplicaciones_geometricas('area', 'x', '0', '0', '2')
            self.assertEqual(ra['datos']['area']['exacto'], '2')
            # Volumen de revolución y=sqrt(x) en [0, 1] en eje x: V = pi * int(x) = pi/2
            rv = aplicaciones_geometricas('volumen_revolucion', 'sqrt(x)', '0', '0', '1', eje_giro='x')
            self.assertEqual(rv['datos']['volumen']['exacto'], 'pi/2')

        def test_tema_e_centroide_y_simpson(self):
            # Simpson integral de x**2 en [0, 2] -> 8/3 ~ 2.666666
            r_num = centro_masa_e_integracion_num('simpson', 'x**2', '0', '2', n_tramos=4)
            self.assertAlmostEqual(float(r_num['datos']['valor_aproximado']), 8.0 / 3.0, places=4)

        def test_tema_f_impropia_y_gamma(self):
            # Integral impropia e^(-x) de 0 a oo = 1 (Relacionada con Gamma(1))
            r = integrales_impropias_gamma_beta('exp(-x)', '0', 'oo')
            self.assertTrue(r['datos']['convergente'])
            self.assertEqual(r['datos']['valor']['exacto'], '1')

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PruebasCalculo2)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description='Cálculo II: Herramientas de Integración y Aplicaciones.')
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument('--test', action='store_true', help='Ejecutar las pruebas unitarias integradas.')
    grupo.add_argument('--demo', action='store_true', help='Mostrar respuestas demo en formato JSON.')
    args = parser.parse_args()

    if args.test:
        return 0 if ejecutar_pruebas() else 1
    if args.demo:
        demos = {
            'tema_a_indefinida': calcular_integral_indefinida('x*cos(x)'),
            'tema_b_avanzada': tecnicas_avanzadas_integracion('1/(x*(x+1))'),
            'tema_c_riemann_tfc': riemann_y_teorema_fundamental('x**2', '0', '3', n_particiones=6),
            'tema_d_volumen': aplicaciones_geometricas('volumen_revolucion', 'x', '0', '0', '2', eje_giro='x'),
            'tema_e_centroide': centro_masa_e_integracion_num('centro_masa', '4 - x**2', '-2', '2'),
            'tema_f_impropia': integrales_impropias_gamma_beta('1/x**2', '1', 'oo')
        }
        print(json.dumps(demos, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())