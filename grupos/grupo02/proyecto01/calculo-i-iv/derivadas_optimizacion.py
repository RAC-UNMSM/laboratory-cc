"""Grupo 02 — Cálculo I: derivación y optimización univariada.

Requiere Python >=3.10, SymPy 1.14 y limites_continuidad.py en el mismo
paquete/directorio. 
"""
from __future__ import annotations
import sympy as sp
if __package__:
    from .limites_continuidad import (_api, _simbolo, _parsear, _punto,
                                     _dominio, _dato, _igual, _salida, _lateral)
else:
    from limites_continuidad import (_api, _simbolo, _parsear, _punto,
                                    _dominio, _dato, _igual, _salida, _lateral)


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


def registrar_herramientas(mcp) -> None:
    """Registrar después de crear FastMCP; este módulo no inicia servidores."""
    for fn in (calcular_derivada, derivada_implicita, recta_tangente,
               optimizar_polinomio, verificar_derivada):
        mcp.tool()(fn)


if __name__ == '__main__':
    import json
    print(json.dumps(optimizar_polinomio('x**3-3*x', '-2', '2'),
                     ensure_ascii=False, indent=2))
