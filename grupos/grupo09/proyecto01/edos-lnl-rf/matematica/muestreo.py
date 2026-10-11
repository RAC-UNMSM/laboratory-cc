"""Muestreo numérico de lo que el desarrollo describe: curvas, órbitas y campos.

Las familias producen objetos exactos (una solución, una separatriz, una rama
de equilibrios); para dibujarlos y para respaldar el análisis cualitativo con
evidencia numérica hay que evaluarlos sobre una malla o integrar trayectorias.
Ese trabajo es cálculo, no presentación, así que vive en la capa matemática:
`visualizacion` solo convierte estos números en figuras.

Las curvas se devuelven como listas con `None` en los cortes (una asíntota
vertical, un tramo donde la expresión no es real), que es como plotly
interrumpe un trazo sin unir los dos lados.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

#: Puntos por curva analítica.
PUNTOS_CURVA = 400

#: Salto relativo que se interpreta como discontinuidad al muestrear.
SALTO_DE_CORTE = 25.0


def _a_flotantes(valores):
    salida = []
    for v in np.atleast_1d(valores):
        if isinstance(v, complex) or np.iscomplexobj(v):
            v = complex(v)
            salida.append(v.real if abs(v.imag) < 1e-9 * max(1.0, abs(v.real)) else math.nan)
        else:
            try:
                salida.append(float(v))
            except (TypeError, ValueError):
                salida.append(math.nan)
    return np.array(salida, dtype=float)


def funcion(expresion, variables):
    """lambdify tolerante: complejos → NaN, errores de dominio → NaN."""
    numerica = sp.lambdify(list(variables), sp.sympify(expresion), modules=["numpy"])

    def evaluar(*argumentos):
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore")
            try:
                resultado = numerica(*[np.asarray(a, dtype=complex) for a in argumentos])
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                return np.full(np.shape(argumentos[0]) if argumentos else (), math.nan)
        resultado = np.asarray(resultado, dtype=complex)
        if resultado.shape != np.shape(argumentos[0]) and argumentos:
            resultado = np.broadcast_to(resultado, np.shape(argumentos[0]))
        reales = np.where(np.abs(resultado.imag) <= 1e-9 * np.maximum(1.0, np.abs(resultado.real)),
                          resultado.real, np.nan)
        return reales
    return evaluar


def _cortar(xs, ys, salto=SALTO_DE_CORTE):
    """Inserta None donde hay NaN o un salto brusco (polo), para no unir los lados."""
    salida_x, salida_y = [], []
    escala = np.nanpercentile(np.abs(ys), 90) if np.isfinite(ys).any() else 1.0
    escala = max(float(escala), 1e-9)
    previo = None
    for xi, yi in zip(xs, ys):
        if not np.isfinite(yi):
            if salida_y and salida_y[-1] is not None:
                salida_x.append(None)
                salida_y.append(None)
            previo = None
            continue
        if previo is not None and abs(yi - previo) > salto * escala and np.sign(yi) != np.sign(previo):
            salida_x.append(None)
            salida_y.append(None)
        salida_x.append(float(xi))
        salida_y.append(float(yi))
        previo = yi
    return salida_x, salida_y


def curva(expresion, x, a, b, n=PUNTOS_CURVA, recorte=None):
    """Muestras de y = expresión(x) en [a, b], cortadas en polos y tramos no reales."""
    xs = np.linspace(float(a), float(b), n)
    ys = funcion(expresion, [x])(xs)
    if recorte is not None:
        ys = np.where(np.abs(ys) > recorte, np.nan, ys)
    return _cortar(xs, ys)


def curva_parametrica(xs_expr, ys_expr, t, a, b, n=PUNTOS_CURVA):
    ts = np.linspace(float(a), float(b), n)
    xs = funcion(xs_expr, [t])(ts)
    ys = funcion(ys_expr, [t])(ts)
    validos = np.isfinite(xs) & np.isfinite(ys)
    return [float(v) if ok else None for v, ok in zip(xs, validos)], \
           [float(v) if ok else None for v, ok in zip(ys, validos)]


def ventana_escalar(ci, intervalo, singularidades=()):
    """Ventana horizontal para dibujar una solución escalar.

    Prioriza el intervalo pedido; si una singularidad cae dentro, la muestra con
    un margen a cada lado, porque es precisamente lo que hay que ver.
    """
    if intervalo is not None:
        a, b = float(intervalo[0]), float(intervalo[1])
    elif ci is not None:
        x0 = float(ci[0])
        a, b = x0 - 3.0, x0 + 3.0
    else:
        a, b = -3.0, 3.0
    valores = [float(sp.N(s)) for s in singularidades if sp.sympify(s).is_number]
    if valores:
        cerca = [v for v in valores if a - 2 <= v <= b + 2]
        if cerca:
            a = min(a, min(cerca) - 0.3 * max(1.0, abs(min(cerca))))
            b = max(b, max(cerca) + 0.3 * max(1.0, abs(max(cerca))))
    if b - a < 1e-9:
        a, b = a - 1.0, b + 1.0
    return a, b


def valores_de_familia(base=None):
    """Constantes para dibujar miembros de una familia de soluciones."""
    if base is None:
        return [sp.Integer(-2), sp.Integer(-1), sp.Integer(1), sp.Integer(2)]
    base = sp.sympify(base)
    paso = sp.Rational(1, 2) if base == 0 else abs(base) / 2
    return [base - 2 * paso, base - paso, base + paso, base + 2 * paso]


def rango_vertical(capas, percentil=95, margen=0.15):
    """Rango vertical robusto: ignora los valores enormes junto a una asíntota."""
    valores = [v for c in capas if c.get("tipo") in ("linea", "puntos")
               for v in c.get("y", []) if v is not None and np.isfinite(v)]
    if not valores:
        return None
    valores = np.asarray(valores)
    bajo, alto = np.percentile(valores, [100 - percentil, percentil])
    for c in capas:
        if c.get("tipo") == "puntos" or c.get("rol") == "analitica":
            puntos = [v for v in c.get("y", []) if v is not None and np.isfinite(v)]
            if puntos and c.get("tipo") == "puntos":
                bajo, alto = min(bajo, min(puntos)), max(alto, max(puntos))
    if alto - bajo < 1e-9:
        bajo, alto = bajo - 1.0, alto + 1.0
    extra = margen * (alto - bajo)
    return [float(bajo - extra), float(alto + extra)]


# ---------------------------------------------------------------------------
# Trayectorias y retratos de fase
# ---------------------------------------------------------------------------

def campo_plano(expresiones, estados):
    """f(t, [x, y]) numérico a partir de dos expresiones autónomas."""
    numerica = sp.lambdify(list(estados), list(expresiones), modules=["numpy"])

    def f(t, s):
        with np.errstate(all="ignore"):
            return np.asarray(numerica(*s), dtype=float)
    return f


def trayectoria(f, inicio, tiempo, caja=None, maximo_puntos=600, rtol=1e-8, atol=1e-10):
    """Integra hacia adelante (tiempo > 0) o atrás (tiempo < 0) hasta salir de la caja."""
    eventos = []
    if caja is not None:
        (xa, xb), (ya, yb) = caja
        ancho, alto = xb - xa, yb - ya

        def sale(t, s):
            return min(s[0] - (xa - 0.5 * ancho), (xb + 0.5 * ancho) - s[0],
                       s[1] - (ya - 0.5 * alto), (yb + 0.5 * alto) - s[1])
        sale.terminal = True
        eventos.append(sale)
    try:
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore")
            solucion = solve_ivp(f, (0.0, float(tiempo)), list(map(float, inicio)),
                                 events=eventos or None, rtol=rtol, atol=atol,
                                 max_step=abs(tiempo) / 200 if tiempo else np.inf)
    except (ValueError, RuntimeError, OverflowError):
        return None
    if solucion.y.size == 0:
        return None
    xs, ys = solucion.y[0], solucion.y[1]
    validos = np.isfinite(xs) & np.isfinite(ys)
    xs, ys = xs[validos], ys[validos]
    if xs.size < 2:
        return None
    paso = max(1, int(np.ceil(xs.size / maximo_puntos)))
    return {"x": xs[::paso].tolist() + [float(xs[-1])], "y": ys[::paso].tolist() + [float(ys[-1])],
            "t_final": float(solucion.t[-1]), "estado_final": [float(xs[-1]), float(ys[-1])]}


def semillas_en_caja(caja, n=5, region=None):
    """Condiciones iniciales repartidas en la caja (y dentro de la región, si la hay)."""
    (xa, xb), (ya, yb) = caja
    xs = np.linspace(xa, xb, n + 2)[1:-1]
    ys = np.linspace(ya, yb, n + 2)[1:-1]
    semillas = [(float(a), float(b)) for a in xs for b in ys]
    if region:
        semillas = [s for s in semillas if _en_region(s, region)]
    return semillas


def _en_region(punto, region):
    for valor, (inferior, superior) in zip(punto, region):
        if inferior is not None and valor < inferior:
            return False
        if superior is not None and valor > superior:
            return False
    return True


def retrato(f, caja, semillas, tiempo=12.0, ambos_sentidos=True):
    """Órbitas desde varias semillas, hacia adelante y (opcionalmente) hacia atrás."""
    orbitas = []
    for semilla in semillas:
        adelante = trayectoria(f, semilla, tiempo, caja)
        if adelante:
            orbitas.append({**adelante, "semilla": list(semilla), "sentido": 1})
        if ambos_sentidos:
            atras = trayectoria(f, semilla, -tiempo, caja)
            if atras:
                orbitas.append({**atras, "semilla": list(semilla), "sentido": -1})
    return orbitas


def capas_de_orbitas(orbitas, rol="orbita", nombre="Órbitas"):
    """Las órbitas como una sola capa (con cortes), para no inundar la leyenda."""
    xs, ys = [], []
    for orbita in orbitas:
        recorrido_x, recorrido_y = orbita["x"], orbita["y"]
        if orbita.get("sentido", 1) < 0:
            recorrido_x, recorrido_y = recorrido_x[::-1], recorrido_y[::-1]
        xs += list(recorrido_x) + [None]
        ys += list(recorrido_y) + [None]
    return {"tipo": "linea", "rol": rol, "nombre": nombre, "x": xs, "y": ys}


def variedades(f, punto, direccion_estable, direccion_inestable, caja, tiempo=25.0, eps=1e-4):
    """Variedades estable e inestable de una silla, integrando desde P ± ε·v."""
    punto = np.asarray(punto, dtype=float)
    salida = {"estable": [], "inestable": []}
    for signo in (1.0, -1.0):
        if direccion_estable is not None:
            inicio = punto + signo * eps * np.asarray(direccion_estable, dtype=float)
            rama = trayectoria(f, inicio, -tiempo, caja, rtol=1e-10, atol=1e-12)
            if rama:
                salida["estable"].append(rama)
        if direccion_inestable is not None:
            inicio = punto + signo * eps * np.asarray(direccion_inestable, dtype=float)
            rama = trayectoria(f, inicio, tiempo, caja, rtol=1e-10, atol=1e-12)
            if rama:
                salida["inestable"].append(rama)
    return salida


def campo_de_direcciones(f, caja, n=17):
    """Segmentos unitarios del campo, como una sola capa con cortes."""
    (xa, xb), (ya, yb) = caja
    malla_x = np.linspace(xa, xb, n)
    malla_y = np.linspace(ya, yb, n)
    largo = 0.38 * min((xb - xa) / (n - 1), (yb - ya) / (n - 1))
    xs, ys = [], []
    for px in malla_x:
        for py in malla_y:
            derivada = f(0.0, [px, py])
            if not np.all(np.isfinite(derivada)):
                continue
            norma = float(np.hypot(*derivada[:2]))
            if norma < 1e-12:
                continue
            dx, dy = derivada[0] / norma * largo, derivada[1] / norma * largo
            xs += [float(px - dx / 2), float(px + dx / 2), None]
            ys += [float(py - dy / 2), float(py + dy / 2), None]
    return {"tipo": "linea", "rol": "campo", "nombre": "Campo de direcciones", "x": xs, "y": ys}


def malla_de_nivel(expresion, estados, caja, n=161):
    """Valores de H(x, y) en una malla, para dibujar curvas de nivel."""
    (xa, xb), (ya, yb) = caja
    xs = np.linspace(xa, xb, n)
    ys = np.linspace(ya, yb, n)
    malla_x, malla_y = np.meshgrid(xs, ys)
    valores = funcion(expresion, estados)(malla_x, malla_y)
    return xs.tolist(), ys.tolist(), [[float(v) if np.isfinite(v) else None for v in fila]
                                      for fila in valores]


def caja_alrededor(puntos, margen=0.6, minimo=1.0):
    """Caja que contiene los puntos dados con margen proporcional."""
    puntos = [p for p in puntos if all(np.isfinite(c) for c in p)]
    if not puntos:
        return ((-2.0, 2.0), (-2.0, 2.0))
    xs = [p[0] for p in puntos]
    ys = [p[1] for p in puntos]
    ancho = max(max(xs) - min(xs), minimo)
    alto = max(max(ys) - min(ys), minimo)
    return ((min(xs) - margen * ancho, max(xs) + margen * ancho),
            (min(ys) - margen * alto, max(ys) + margen * alto))
