"""Grupo 02 — Cálculo I: límites y continuidad (Python >= 3.10).

Dependencia: pip install sympy==1.14.0
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


def registrar_herramientas(mcp) -> None:
    """Registra tres tools en un objeto compatible con FastMCP."""
    for fn in (calcular_limite, analizar_continuidad, analizar_asintotas):
        mcp.tool()(fn)


if __name__ == '__main__':
    import json
    print(json.dumps(calcular_limite('sin(x)/x', '0'), ensure_ascii=False, indent=2))
