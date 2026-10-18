"""Grupo 02 — Cálculo I: módulo unificado con pruebas (Python >= 3.10).

Dependencia: pip install sympy==1.14.0
API pública: calcular_limite, analizar_continuidad, analizar_asintotas,
calcular_derivada, derivada_implicita, recta_tangente, optimizar_polinomio,
verificar_derivada, registrar_herramientas. Resultados serializables como JSON.

Uso:
    python calculo1.py --test       # pruebas automáticas incorporadas
    python calculo1.py --demo       # ejemplos de resultados JSON
    python calculo1.py --help       # ayuda

No necesita los dos módulos originales. Importar este archivo no ejecuta
pruebas, ejemplos ni servidores. Solo requiere SymPy.
Optimización: polinomios de grado <=6 con coeficientes y extremos racionales.
Asíntotas: funciones racionales. No incluye funciones definidas por tramos,
L'Hospital, teorema del valor medio ni un tutor conversacional completo.

Sintaxis: x**2 o x^2, sin(x), cos(x), tan(x), exp(x), log(x), sqrt(x),
Abs(x), pi, E y oo. Multiplicación explícita: 2*x. No acepta LaTeX,
funciones por tramos ni parámetros libres. Todos los ángulos están en radianes.
La continuidad se estudia respecto al dominio real natural de la expresión.
Los pasos son una traza verificable del cálculo, no una derivación completa
por épsilon-delta ni una simulación de los algoritmos internos de SymPy.

Integración en server.py:
    from calculo1 import registrar_herramientas
    registrar_herramientas(mcp)  # objeto FastMCP creado por server.py

El parser no usa eval ni sympify sobre texto. Para un servidor público,
ejecutar el cálculo en procesos con límites de tiempo y memoria: los límites
de entrada aquí no sustituyen el aislamiento de recursos del servidor.
Referencias: https://docs.sympy.org/latest/tutorials/intro-tutorial/calculus.html
https://docs.sympy.org/latest/modules/calculus/index.html
"""
from __future__ import annotations
import ast
from functools import wraps
import sympy as sp
from sympy.calculus.util import continuous_domain

FUNCIONES = {n: getattr(sp, n) for n in
             ('sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'exp', 'log', 'Abs')}
CONSTANTES = {'pi': sp.pi, 'E': sp.E, 'oo': sp.oo}


def _simbolo(nombre):
    if (not isinstance(nombre, str) or not nombre.isidentifier()
            or nombre.startswith('_') or nombre in FUNCIONES
            or nombre in CONSTANTES or nombre == 'sqrt' or len(nombre) > 24):
        raise ValueError('Nombre de variable inválido o reservado.')
    return sp.Symbol(nombre, real=True)


def _parsear(texto, variables):
    """Construye un AST aritmético permitido sin ejecutar código del usuario."""
    if not isinstance(texto, str) or not texto.strip() or len(texto) > 500:
        raise ValueError('La expresión debe tener entre 1 y 500 caracteres.')
    arbol = ast.parse(texto.replace('^', '**'), mode='eval')
    if sum(1 for _ in ast.walk(arbol)) > 120:
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
                    raise ValueError('Exponente numérico fuera de [-100,100].')
                return sp.Pow(a, b, evaluate=False)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and not n.keywords:
            if len(n.args) != 1:
                raise ValueError('Las funciones admiten exactamente un argumento.')
            a = visitar(n.args[0])
            if n.func.id == 'sqrt':
                return sp.Pow(a, sp.Rational(1, 2), evaluate=False)
            if n.func.id in FUNCIONES:
                return FUNCIONES[n.func.id](a, evaluate=False)
        raise ValueError('Sintaxis no admitida. Use operaciones y funciones documentadas.')
    resultado = visitar(arbol.body)
    if variables:
        for sub in sp.preorder_traversal(resultado):
            if isinstance(sub, sp.Expr) and sub.is_number:
                valor = sp.simplify(sub)
                if valor.is_finite is not True or valor.is_real is not True:
                    raise ValueError('La función contiene una constante no real o no finita.')
    return resultado


def _punto(texto):
    p = sp.simplify(_parsear(texto, []))
    if p not in (sp.oo, -sp.oo) and (p.is_real is not True or p.is_finite is not True):
        raise ValueError('El punto debe ser real finito, oo o -oo.')
    return p


def _dominio(f, x):
    # Intersecar los dominios de cada subexpresión conserva huecos incluso
    # cuando una simplificación algebraica posterior cancela denominadores.
    d = sp.S.Reals
    for sub in sp.preorder_traversal(f):
        if isinstance(sub, sp.Expr) and sub.has(x):
            d = d.intersect(continuous_domain(sub, x, sp.S.Reals))
    return d


def _dato(v):
    return {'exacto': sp.sstr(v), 'latex': sp.latex(v)}


def _igual(a, b):
    if a == b:
        return True
    r = sp.simplify(a - b)
    return True if r.is_zero is True else False if r.is_zero is False else None


def _salida(operacion, datos, pasos, modo):
    if modo not in ('examen', 'paso_a_paso'):
        raise ValueError('modo debe ser examen o paso_a_paso.')
    return {'estado': 'ok', 'operacion': operacion, 'modo': modo,
            'datos': datos, 'pasos': pasos if modo == 'paso_a_paso' else pasos[-1:]}


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


def _lateral(f, x, p, lado, dominio):
    # Exigir un entorno lateral real completo evita límites complejos espurios
    # (p.ej. sqrt(x) desde la izquierda en cero).
    # Componentes de intervalos del dominio natural admitido.
    partes = dominio.args if isinstance(dominio, sp.Union) else (dominio,)
    disponible = False
    for i in partes:
        if not isinstance(i, sp.Interval):
            continue
        a, b = (i.start <= p, p < i.end) if lado == '+' else (i.start < p, p <= i.end)
        if a is sp.S.true and b is sp.S.true:
            disponible = True
    if not disponible:
        return None
    return sp.limit(f, x, p, dir=lado)


def _conocido(v):
    return v is not None and not v.has(sp.Limit, sp.AccumBounds, sp.nan, sp.zoo) and (v.is_real is True or v in (sp.oo, -sp.oo))


@_api
def calcular_limite(expresion: str, punto: str, variable: str = 'x',
                    direccion: str = 'bilateral', modo: str = 'paso_a_paso') -> dict:
    """Límite real bilateral/lateral; direccion: bilateral, + o -."""
    if direccion not in ('bilateral', '+', '-'):
        raise ValueError('direccion debe ser bilateral, + o -.')
    x = _simbolo(variable)
    f, p = _parsear(expresion, [x]), _punto(punto)
    d = _dominio(f, x)
    pasos = [f'Dominio real de la expresión original: {d}.']
    datos = {'funcion': _dato(f), 'dominio': _dato(d), 'punto': _dato(p)}
    if p in (sp.oo, -sp.oo):
        partes = d.args if isinstance(d, sp.Union) else (d,)
        if not any(isinstance(i, sp.Interval) and (i.end == p or i.start == p) for i in partes):
            return {'estado': 'no_determinado', 'mensaje': 'No se certificó un intervalo real hacia ese infinito.'}
        v = sp.limit(f, x, p)
    else:
        lados = ('-', '+') if direccion == 'bilateral' else (direccion,)
        valores = {s: _lateral(f, x, p, s, d) for s in lados}
        datos['laterales'] = {s: _dato(v) if v is not None else None for s, v in valores.items()}
        for s, v in valores.items():
            pasos.append(f'Límite lateral {s}: {v if v is not None else "sin entorno real certificado"}.')
        if any(v is None for v in valores.values()):
            return {'estado': 'no_determinado', 'datos': datos,
                    'mensaje': 'Falta un entorno lateral real. Solicite el lado disponible.'}
        if any(not _conocido(v) for v in valores.values()):
            return {'estado': 'no_determinado', 'datos': datos, 'mensaje': 'Límite oscilatorio o no resuelto.'}
        if direccion == 'bilateral':
            iguales = _igual(valores['-'], valores['+'])
            if iguales is not True:
                datos['existe'] = False if iguales is False else None
                return _salida('limite', datos, pasos + ['Los límites laterales no coinciden.' if iguales is False else 'Comparación no decidida.'], modo)
        v = next(iter(valores.values()))
    if not _conocido(v):
        return {'estado': 'no_determinado', 'datos': datos, 'mensaje': 'SymPy no produjo un límite real determinado.'}
    datos.update(resultado=_dato(v), existe=True, finito=v.is_finite is True)
    pasos.append(f'Conclusión: límite = {v}' + (' (infinito, no es un límite finito).' if v in (sp.oo, -sp.oo) else '.'))
    return _salida('limite', datos, pasos, modo)


@_api
def analizar_continuidad(expresion: str, punto: str, variable: str = 'x',
                         modo: str = 'paso_a_paso') -> dict:
    """Continuidad en un punto; reconoce extremos del dominio y huecos."""
    x, p = _simbolo(variable), _punto(punto)
    if p.is_finite is not True:
        raise ValueError('La continuidad se estudia en puntos finitos.')
    f = _parsear(expresion, [x])
    d = _dominio(f, x)
    dentro = d.contains(p)
    l, r = (_lateral(f, x, p, s, d) for s in ('-', '+'))
    valor = sp.simplify(f.subs(x, p)) if dentro is sp.S.true else None
    disponibles = [v for v in (l, r) if v is not None]
    continua = None
    tipo = 'no_determinado'
    if dentro is sp.S.false:
        continua = False
        tipo = 'punto_fuera_del_dominio'
    if disponibles and all(_conocido(v) for v in disponibles):
        if dentro is sp.S.true:
            comprobaciones = [_igual(v, valor) for v in disponibles]
            continua = True if all(c is True for c in comprobaciones) else False if False in comprobaciones else None
            tipo = 'continua_relativa_al_dominio' if continua is True else 'no_determinado'
        if any(v in (sp.oo, -sp.oo) for v in disponibles):
            tipo = 'infinita'
        elif l is not None and r is not None:
            iguales = _igual(l, r)
            if iguales is False:
                tipo = 'salto'
            elif iguales is True and continua is False:
                tipo = 'removible'
    datos = {'dominio': _dato(d), 'valor': _dato(valor) if valor is not None else None,
             'izquierda': _dato(l) if l is not None else None,
             'derecha': _dato(r) if r is not None else None,
             'continua': continua, 'clasificacion': tipo}
    return _salida('continuidad', datos, [f'Dominio: {d}.', f'f({p}) = {valor}.',
                   f'Límites laterales: izquierda={l}, derecha={r}.',
                   f'Comparar los límites disponibles con f({p}): {tipo}.'], modo)


@_api
def analizar_asintotas(expresion: str, variable: str = 'x',
                       modo: str = 'paso_a_paso') -> dict:
    """Asíntotas de funciones racionales; candidatos verticales y rectas al infinito."""
    x = _simbolo(variable)
    original = _parsear(expresion, [x])
    f = sp.cancel(original)
    if not f.is_rational_function(x):
        raise ValueError('Esta herramienta certifica únicamente funciones racionales.')
    d = _dominio(original, x)
    polos = sp.solveset(sp.denom(f), x, domain=sp.S.Reals)
    if not isinstance(polos, sp.FiniteSet) and polos != sp.S.EmptySet:
        raise NotImplementedError('No se pudieron enumerar todos los polos reales.')
    verticales = []
    for p in polos:
        limites = [_lateral(original, x, p, s, d) for s in ('-', '+')]
        if any(v in (sp.oo, -sp.oo) for v in limites):
            verticales.append(_dato(p))
    rectas = []
    for extremo in (sp.oo, -sp.oo):
        m = sp.limit(f/x, x, extremo)
        if m.is_finite is True:
            b = sp.limit(f-m*x, x, extremo)
            if b.is_finite is True:
                rectas.append({'hacia': str(extremo), 'tipo': 'horizontal' if m == 0 else 'oblicua',
                               'ecuacion_y': _dato(m*x+b)})
    return _salida('asintotas', {'verticales_x': verticales, 'rectas': rectas},
                   ['Cancelar factores para distinguir polos de huecos.',
                    'Comprobar límites infinitos en los polos reales.',
                    'Calcular m=lim(f/x), b=lim(f-m*x); la asíntota es y=m*x+b.'], modo)



# DERIVADAS Y OPTIMIZACIÓN

def _traza(f, x):
    """Árbol de reglas: cada igualdad se calcula simbólicamente."""
    pasos, vistos = [], set()
    def visitar(g):
        if g in vistos:
            return
        vistos.add(g)
        for arg in g.args:
            if isinstance(arg, sp.Expr) and arg.has(x):
                visitar(arg)
        if not g.has(x):
            regla = 'Derivada de una constante: cero'
        elif g == x:
            regla = 'Derivada de la variable: uno'
        elif isinstance(g, sp.Add):
            regla = 'Linealidad: derivar cada sumando'
        elif isinstance(g, sp.Mul):
            regla = 'Producto: sumar cada factor derivado por los demás factores'
        elif isinstance(g, sp.Pow):
            regla = 'Potencia y cadena (o diferenciación logarítmica para exponente variable)'
        else:
            regla = 'Derivada de función elemental y regla de la cadena'
        pasos.append(f'{regla}: d/d{x}({g}) = {sp.diff(g, x)}.')
    visitar(f)
    return pasos


@_api
def calcular_derivada(expresion: str, variable: str = 'x', orden: int = 1,
                      modo: str = 'paso_a_paso') -> dict:
    """Derivada simbólica y dominios certificados de la función y del resultado."""
    if type(orden) is not int or not 1 <= orden <= 6:
        raise ValueError('orden debe ser un entero entre 1 y 6.')
    x = _simbolo(variable)
    f = _parsear(expresion, [x])
    d = _dominio(f, x)
    actual, pasos = f, [f'Dominio original: {d}.']
    for k in range(1, orden+1):
        pasos.extend(_traza(actual, x))
        actual = sp.simplify(sp.diff(actual, x))
        pasos.append(f'Derivada de orden {k}: {actual}.')
    # Dominio de la fórmula != conjunto completo de diferenciabilidad:
    # Abs, sign, DiracDelta o derivadas no evaluadas requieren otro análisis.
    regular = not f.has(sp.Abs) and not actual.has(sp.Derivative, sp.DiracDelta, sp.sign)
    certificado = None
    if regular:
        try:
            certificado = _dominio(actual, x).intersect(d).interior
        except NotImplementedError:
            pass
    datos = {'funcion': _dato(f), 'orden': orden, 'derivada': _dato(actual),
             'dominio_original': _dato(d),
             'dominio_regular_certificado': _dato(certificado) if certificado is not None else None,
             'advertencia': 'La fórmula se interpreta en puntos regulares; fronteras, valores absolutos y derivadas generalizadas requieren límites laterales.'}
    return _salida('derivada', datos, pasos, modo)


@_api
def derivada_implicita(ecuacion: str, variable: str = 'x', dependiente: str = 'y',
                       modo: str = 'paso_a_paso') -> dict:
    """Recibe F(x,y) (sin '=0'); devuelve y'=-F_x/F_y donde F_y != 0."""
    x, y = _simbolo(variable), _simbolo(dependiente)
    if x == y:
        raise ValueError('Las variables independiente y dependiente deben ser distintas.')
    f = _parsear(ecuacion, [x, y])
    fx, fy = sp.diff(f, x), sp.diff(f, y)
    if sp.simplify(fy) == 0:
        raise ValueError('F_y es idénticamente cero; no se puede despejar esta derivada.')
    r = sp.simplify(-fx/fy)
    return _salida('derivada_implicita',
                   {'ecuacion_cero': _dato(f), 'Fx': _dato(fx), 'Fy': _dato(fy),
                    'derivada': _dato(r),
                    'condicion': f'F({x},{y})=0 y {fy} != 0, en un entorno donde F sea C1.'},
                   [f'Derivar F({x},{y}({x}))=0 aplicando la cadena.',
                    f'F_x + F_y*{y}\u2032 = 0: ({fx}) + ({fy})*{y}\u2032 = 0.',
                    f'Despejar, si F_y != 0: {y}\u2032 = {r}.'], modo)


@_api
def recta_tangente(expresion: str, punto: str, variable: str = 'x',
                   modo: str = 'paso_a_paso') -> dict:
    """Recta tangente con pendiente finita bilateral; detecta no derivabilidad."""
    x, p = _simbolo(variable), _punto(punto)
    if p.is_finite is not True:
        raise ValueError('El punto debe ser finito.')
    f = _parsear(expresion, [x])
    d = _dominio(f, x)
    if d.contains(p) is not sp.S.true:
        raise ValueError('El punto no pertenece al dominio real certificado.')
    valor = sp.simplify(f.subs(x, p))
    cociente = (f - valor)/(x-p)
    izq, der = (_lateral(cociente, x, p, s, d) for s in ('-', '+'))
    datos = {'punto_x': _dato(p), 'punto_y': _dato(valor),
             'pendiente_izquierda': _dato(izq) if izq is not None else None,
             'pendiente_derecha': _dato(der) if der is not None else None}
    if izq is None or der is None:
        return {'estado': 'no_determinado', 'datos': datos,
                'mensaje': 'Se requieren dos lados; las tangentes unilaterales no se incluyen.'}
    if izq.is_finite is not True or der.is_finite is not True:
        return {'estado': 'no_determinado', 'datos': datos,
                'mensaje': 'No se certificó una pendiente finita; comprobar tangente vertical u oscilación.'}
    iguales = _igual(izq, der)
    if iguales is not True:
        datos['derivable'] = False if iguales is False else None
        return _salida('tangente', datos, ['Los cocientes incrementales laterales no dan una misma pendiente certificada.'], modo)
    recta = sp.expand(valor + izq*(x-p))
    datos.update(derivable=True, pendiente=_dato(izq), ecuacion_y=_dato(recta))
    return _salida('tangente', datos,
                   [f'Evaluar f({p}) = {valor}.', f'Formar (f({x})-f({p}))/({x}-{p}).',
                    f'Límites laterales del cociente: {izq} y {der}.',
                    f'Usar y-f({p})=f\u2032({p})*({x}-{p}): y={recta}.'], modo)


@_api
def optimizar_polinomio(expresion: str, inicio: str, fin: str,
                        variable: str = 'x', modo: str = 'paso_a_paso') -> dict:
    """Extremos absolutos en [inicio,fin] para polinomios de grado <= 6.

    Coeficientes y extremos racionales; raíces algebraicas exactas admitidas.
    Incluye empates y el caso constante. No confunde punto crítico con extremo.
    """
    x, a, b = _simbolo(variable), _punto(inicio), _punto(fin)
    if a.is_Rational is not True or b.is_Rational is not True or not a < b:
        raise ValueError('Se requieren extremos racionales finitos con inicio < fin.')
    original = _parsear(expresion, [x])
    intervalo = sp.Interval(a, b)
    d = _dominio(original, x)
    if intervalo.is_subset(d) is not True:
        raise ValueError('La expresión original debe estar definida y ser continua en todo [a,b].')
    f = sp.simplify(original)
    if not f.is_polynomial(x):
        raise ValueError('La optimización de esta versión admite solo polinomios.')
    pol = sp.Poly(f, x)
    if pol.degree() > 6 or any(c.is_Rational is not True for c in pol.all_coeffs()):
        raise ValueError('Use grado <=6 y coeficientes racionales.')
    df = sp.diff(f, x)
    pasos = ['Por Weierstrass, un polinomio continuo en [a,b] alcanza máximo y mínimo.',
             f'Calcular f\u2032({x})={df} y resolver f\u2032({x})=0 en el interior.']
    if df == 0:
        return _salida('optimizacion', {'funcion_constante': True,
                       'minimo': _dato(f), 'maximo': _dato(f),
                       'donde': _dato(intervalo)}, pasos + ['Todos los puntos alcanzan ambos extremos (no estrictos).'], modo)
    raices = sp.polys.polytools.real_roots(df, x)
    criticos = sorted(set(c for c in raices if a < c < b))
    clasificados = []
    for c in criticos:
        tipo = 'no_determinado'
        for k in range(2, int(pol.degree())+1):
            valor = sp.simplify(sp.diff(f, x, k).subs(x, c))
            if valor.is_zero is True:
                continue
            if valor.is_zero is None:
                break
            if k % 2:
                tipo = 'sin_extremo_local'
            elif valor.is_positive is True:
                tipo = 'minimo_local'
            elif valor.is_negative is True:
                tipo = 'maximo_local'
            pasos.append(f'En x={c}, primera derivada superior no nula: orden {k}, valor {valor}; {tipo}.')
            break
        clasificados.append({'x': _dato(c), 'tipo': tipo})
    candidatos = [a, *criticos, b]
    valores = [sp.simplify(f.subs(x, c)) for c in candidatos]
    menor, mayor = sp.Min(*valores), sp.Max(*valores)
    # SymPy puede conservar Min/Max para números algebraicos difíciles.
    # No inventar qué punto alcanza un extremo si no se decide la igualdad.
    tabla = [{'x': _dato(c), 'f_x': _dato(v)} for c, v in zip(candidatos, valores)]
    def extremo(v):
        comparaciones = [_igual(w, v) for w in valores]
        return {'valor': _dato(v), 'puntos': [_dato(c) for c, eq in zip(candidatos, comparaciones) if eq is True],
                'ubicaciones_completas': all(eq is not None for eq in comparaciones)}
    pasos.extend([f'Evaluar extremos del intervalo y puntos críticos: {list(zip(candidatos, valores))}.',
                  f'Comparar todos los candidatos: mínimo={menor}; máximo={mayor}.'])
    return _salida('optimizacion', {'intervalo': _dato(intervalo), 'derivada': _dato(df),
                   'criticos': clasificados, 'candidatos': tabla,
                   'minimo': extremo(menor), 'maximo': extremo(mayor)}, pasos, modo)


@_api
def verificar_derivada(expresion: str, respuesta: str, variable: str = 'x') -> dict:
    """Verifica una primera derivada en el dominio regular certificado.

    Reconoce equivalencia solo con prueba simbólica de cero y cobertura del
    dominio. correcta=None significa que se necesita revisión, no rechazo.
    """
    x = _simbolo(variable)
    f, propuesta = _parsear(expresion, [x]), _parsear(respuesta, [x])
    if f.has(sp.Abs):
        return {'estado': 'no_determinado', 'correcta': None,
                'mensaje': 'Para valores absolutos se requiere análisis por tramos.'}
    esperada = sp.diff(f, x)
    d = _dominio(f, x).intersect(_dominio(esperada, x)).interior
    dp = _dominio(propuesta, x)
    if d == sp.S.EmptySet:
        return {'estado': 'no_determinado', 'correcta': None, 'mensaje': 'Dominio regular vacío.'}
    faltantes = d - dp
    cobertura = True if faltantes == sp.S.EmptySet else False if faltantes.is_empty is False else None
    diferencia = sp.simplify(esperada-propuesta)
    if cobertura is False:
        correcta, mensaje = False, 'La respuesta pierde puntos del dominio donde debe existir la derivada.'
    elif diferencia.is_zero is True and cobertura is True:
        correcta, mensaje = True, 'Equivalencia simbólica demostrada en el dominio regular.'
    elif diferencia.is_polynomial(x) and diferencia != 0:
        correcta, mensaje = False, 'La diferencia es un polinomio no nulo; no puede anularse en todo un intervalo.'
    else:
        correcta, mensaje = None, 'No se demostró equivalencia; requiere análisis adicional.'
    return {'estado': 'ok' if correcta is not None else 'no_determinado',
            'correcta': correcta, 'mensaje': mensaje,
            'dominio_comprobado': _dato(d), 'diferencia': _dato(diferencia)}


# REGISTRO MCP Y PRUEBAS INCORPORADAS
HERRAMIENTAS = (
    calcular_limite, analizar_continuidad, analizar_asintotas,
    calcular_derivada, derivada_implicita, recta_tangente,
    optimizar_polinomio, verificar_derivada,
)


def registrar_herramientas(mcp) -> None:
    """Registrar las ocho herramientas una sola vez en el objeto FastMCP.

    El servidor crea y ejecuta mcp; este módulo aporta el motor matemático.
    Las pruebas usan un registro simulado, no una conexión MCP de extremo a extremo.
    """
    for fn in HERRAMIENTAS:
        mcp.tool()(fn)


def ejecutar_pruebas() -> bool:
    """Ejecutar pruebas de regresión sin archivos auxiliares; True si pasan."""
    import json
    import unittest

    class PruebasCalculo1(unittest.TestCase):
        def test_limite_trigonometrico(self):
            r = calcular_limite('sin(x)/x', '0')
            self.assertEqual(r['datos']['resultado']['exacto'], '1')

        def test_laterales_distintos(self):
            r = calcular_limite('1/x', '0')
            self.assertIs(r['datos']['existe'], False)
            self.assertEqual(r['datos']['laterales']['-']['exacto'], '-oo')
            self.assertEqual(r['datos']['laterales']['+']['exacto'], 'oo')

        def test_limite_infinito(self):
            r = calcular_limite('1/x**2', '0')
            self.assertEqual(r['datos']['resultado']['exacto'], 'oo')
            self.assertIs(r['datos']['finito'], False)

        def test_limite_unilateral(self):
            self.assertEqual(calcular_limite('sqrt(x)', '0')['estado'], 'no_determinado')
            r = calcular_limite('sqrt(x)', '0', direccion='+')
            self.assertEqual(r['datos']['resultado']['exacto'], '0')

        def test_limite_exponencial(self):
            self.assertEqual(calcular_limite('(1+1/x)**x', 'oo')['datos']['resultado']['exacto'], 'E')

        def test_oscilacion_no_se_inventa_resultado(self):
            self.assertEqual(calcular_limite('sin(1/x)', '0')['estado'], 'no_determinado')

        def test_discontinuidades_removibles(self):
            for f, p in [('x/x', '0'), ('(x**2-1)/(x-1)', '1')]:
                with self.subTest(funcion=f):
                    r = analizar_continuidad(f, p)['datos']
                    self.assertEqual(r['clasificacion'], 'removible')
                    self.assertIs(r['continua'], False)
                    self.assertIsNone(r['valor'])

        def test_continuidad_extremo_dominio(self):
            self.assertIs(analizar_continuidad('sqrt(x)', '0')['datos']['continua'], True)

        def test_discontinuidad_infinita(self):
            self.assertEqual(analizar_continuidad('1/x', '0')['datos']['clasificacion'], 'infinita')

        def test_discontinuidad_salto(self):
            self.assertEqual(analizar_continuidad('Abs(x)/x', '0')['datos']['clasificacion'], 'salto')

        def test_asintotas(self):
            r = analizar_asintotas('(x**2+1)/(x-1)')['datos']
            self.assertEqual(r['verticales_x'][0]['exacto'], '1')
            self.assertEqual(len(r['rectas']), 2)
            for recta in r['rectas']:
                self.assertEqual(recta['ecuacion_y']['exacto'], 'x + 1')
                self.assertEqual(recta['tipo'], 'oblicua')

        def test_hueco_no_es_asintota(self):
            self.assertEqual(analizar_asintotas('(x**2-1)/(x-1)')['datos']['verticales_x'], [])

        def test_derivada_producto_y_cadena(self):
            r = calcular_derivada('sin(x**2)*exp(x)')['datos']
            x = _simbolo('x')
            obtenido = _parsear(r['derivada']['exacto'], [x])
            esperado = sp.exp(x)*(2*x*sp.cos(x**2)+sp.sin(x**2))
            self.assertEqual(sp.simplify(obtenido-esperado), 0)

        def test_derivada_orden_superior(self):
            self.assertEqual(calcular_derivada('x**3', orden=2)['datos']['derivada']['exacto'], '6*x')

        def test_derivada_conserva_hueco(self):
            r = calcular_derivada('x/x')['datos']
            self.assertEqual(r['derivada']['exacto'], '0')
            self.assertEqual(r['dominio_original']['exacto'], 'Union(Interval.open(-oo, 0), Interval.open(0, oo))')

        def test_derivada_implicita(self):
            r = derivada_implicita('x**2+y**2-25')['datos']
            self.assertEqual(r['derivada']['exacto'], '-x/y')
            self.assertIn('2*y != 0', r['condicion'])

        def test_esquina_no_derivable(self):
            self.assertIs(recta_tangente('Abs(x)', '0')['datos']['derivable'], False)

        def test_tangente(self):
            self.assertEqual(recta_tangente('x**2', '2')['datos']['ecuacion_y']['exacto'], '4*x - 4')

        def test_extremos_absolutos_y_empates(self):
            r = optimizar_polinomio('x**3-3*x', '-2', '2')['datos']
            self.assertEqual(r['minimo']['valor']['exacto'], '-2')
            self.assertEqual(r['maximo']['valor']['exacto'], '2')
            self.assertEqual([p['exacto'] for p in r['minimo']['puntos']], ['-2', '1'])
            self.assertEqual([p['exacto'] for p in r['maximo']['puntos']], ['-1', '2'])

        def test_segunda_derivada_nula(self):
            r = optimizar_polinomio('x**4', '-1', '1')['datos']
            self.assertEqual(r['criticos'][0]['tipo'], 'minimo_local')
            self.assertEqual(r['minimo']['valor']['exacto'], '0')

        def test_estacionario_sin_extremo(self):
            r = optimizar_polinomio('x**3', '-1', '1')['datos']
            self.assertEqual(r['criticos'][0]['tipo'], 'sin_extremo_local')

        def test_funcion_constante(self):
            r = optimizar_polinomio('5', '-1', '1')['datos']
            self.assertIs(r['funcion_constante'], True)
            self.assertEqual(r['minimo']['exacto'], '5')
            self.assertEqual(r['maximo']['exacto'], '5')

        def test_optimizar_rechaza_huecos(self):
            self.assertEqual(optimizar_polinomio('x/x', '-1', '1')['estado'], 'error')

        def test_verificacion_correcta(self):
            self.assertIs(verificar_derivada('x**2', '2*x')['correcta'], True)

        def test_verificacion_detecta_dominio_perdido(self):
            self.assertIs(verificar_derivada('x**2', '2*x*x/x')['correcta'], False)

        def test_verificacion_incorrecta(self):
            for respuesta in ('2*x+1', 'x'):
                with self.subTest(respuesta=respuesta):
                    self.assertIs(verificar_derivada('x**2', respuesta)['correcta'], False)

        def test_entradas_invalidas(self):
            for entrada in ('__import__("os").system("id")', '1/0', 'sqrt(-1)', 'x.__class__'):
                with self.subTest(entrada=entrada):
                    self.assertEqual(calcular_limite(entrada, '0')['estado'], 'error')
            self.assertEqual(calcular_derivada('x**2', orden=0)['estado'], 'error')

        def test_modos_mismo_resultado(self):
            for fn, args in [(calcular_limite, ('sin(x)/x', '0')),
                             (calcular_derivada, ('x**3',)),
                             (optimizar_polinomio, ('x**2', '-1', '1'))]:
                with self.subTest(herramienta=fn.__name__):
                    detallado = fn(*args, modo='paso_a_paso')
                    examen = fn(*args, modo='examen')
                    self.assertEqual(detallado['datos'], examen['datos'])
                    self.assertEqual(len(examen['pasos']), 1)

        def test_json_serializable(self):
            casos = [(calcular_limite, ('sin(x)/x', '0')),
                     (analizar_continuidad, ('x/x', '0')),
                     (analizar_asintotas, ('1/x',)),
                     (calcular_derivada, ('sin(x)',)),
                     (derivada_implicita, ('x**2+y**2-1',)),
                     (recta_tangente, ('x**2', '1')),
                     (optimizar_polinomio, ('x**2', '-1', '1')),
                     (verificar_derivada, ('x**2', '2*x'))]
            for fn, args in casos:
                with self.subTest(herramienta=fn.__name__):
                    resultado = fn(*args)
                    self.assertEqual(resultado['estado'], 'ok')
                    self.assertEqual(json.loads(json.dumps(resultado)), resultado)

        def test_registro_ocho_herramientas(self):
            class RegistroSimulado:
                def __init__(self):
                    self.funciones = []
                def tool(self):
                    def decorar(fn):
                        self.funciones.append(fn)
                        return fn
                    return decorar
            registro = RegistroSimulado()
            registrar_herramientas(registro)
            self.assertEqual(len(registro.funciones), 8)
            self.assertEqual(len({f.__name__ for f in registro.funciones}), 8)
            self.assertEqual(tuple(registro.funciones), HERRAMIENTAS)

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PruebasCalculo1)
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


def main() -> int:
    """Interfaz local; el transporte MCP pertenece a server.py."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description='Grupo 02: motor simbólico de Cálculo I.')
    opciones = parser.add_mutually_exclusive_group()
    opciones.add_argument('--test', action='store_true', help='Ejecutar las 30 pruebas incorporadas.')
    opciones.add_argument('--demo', action='store_true', help='Mostrar ejemplos en JSON.')
    args = parser.parse_args()
    if args.test:
        return 0 if ejecutar_pruebas() else 1
    if args.demo:
        ejemplos = {
            'limite': calcular_limite('sin(x)/x', '0'),
            'continuidad': analizar_continuidad('(x**2-1)/(x-1)', '1'),
            'derivada': calcular_derivada('sin(x**2)*exp(x)'),
            'optimizacion': optimizar_polinomio('x**3-3*x', '-2', '2'),
        }
        print(json.dumps(ejemplos, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
