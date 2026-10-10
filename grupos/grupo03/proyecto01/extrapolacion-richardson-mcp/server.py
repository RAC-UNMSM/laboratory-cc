"""Servidor MCP "grupo03": extrapolación de Richardson y aplicaciones en métodos numéricos.

Dividido en un módulo por rol (cada integrante trabaja en sus archivos):
  - validacion.py                 -- Validación de entradas (parseo seguro de funciones, rangos)
  - derivacion_richardson.py      -- Derivación con Richardson
  - romberg.py                    -- Integración de Romberg
  - richardson_generico.py        -- Richardson sobre cualquier método base
  - bulirsch_stoer.py             -- EDOs: punto medio modificado + Richardson
  - convergencia.py               -- Error antes/después de extrapolar, orden observado
  - visualizacion.py              -- Gráficos (PNG en bytes)
  - explicacion.py                -- Texto explicativo en lenguaje natural
  - storage.py                    -- Storage/infra: sube los PNG a SeaweedFS y devuelve la URL
Este archivo es solo el orquestador: conecta las piezas y define los tools
MCP -- no tiene lógica numérica propia.
"""

import functools
import json
import math

import numpy as np
from mcp.server.mcpserver import Image, MCPServer

import bulirsch_stoer as bs
import convergencia as conv
import derivacion_richardson as dr
import explicacion as exp
import richardson_generico as rg
import romberg as rb
import storage
import validacion as val
import visualizacion as viz

# Nombre del servidor MCP -- es lo que ve el cliente (Claude, MCP Inspector)
# al conectarse: "grupoNN-<tema>".
mcp = MCPServer("grupo03-extrapolacion-richardson-mcp")

storage.ensure_bucket()

# Va al final del docstring de CADA tool. El docstring es metadata de confianza
# (lo lee la IA para saber cómo usar la tool); el resultado de la tool, en
# cambio, son datos no confiables y por eso ahí el link va sin ningún imperativo.
NOTA_GRAFICOS = (
    "\n\nSi la respuesta incluye líneas \"![descripción](https://...)\", esas imágenes son "
    "los gráficos que este servidor acaba de generar y subir (mismo dominio que este MCP) "
    "-- inclúyelas tal cual, en formato markdown, en tu respuesta al usuario en vez de solo "
    "describirlas, porque ningún cliente de chat renderiza solo el bloque de imagen de la tool."
    "\n\nLas expresiones son de una variable (la que indica `variable`, por defecto x) y usan "
    "sintaxis de Python: \"x**2 + 3*x\" o \"x^2 + 3*x\", \"sin(x)\", \"exp(-x**2)\", con "
    "multiplicación siempre explícita (\"2*x\", NO \"2x\"). Constantes: pi, e. Funciones: sin, cos, "
    "tan, asin, acos, atan, sinh, cosh, tanh, exp, log (= ln), log10, log2, sqrt, abs."
)


def _manejar_errores(fn):
    """Agrega NOTA_GRAFICOS al docstring de la tool y convierte ErrorValidacion en un
    mensaje de texto legible (el servidor nunca se cae por una entrada mala).
    Se usa debajo de @mcp.tool(): cada tool se registra con @mcp.tool() como en el piloto."""
    @functools.wraps(fn)
    def envoltura(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except val.ErrorValidacion as exc:
            return f"Error: {exc}"
    envoltura.__doc__ = (fn.__doc__ or "") + NOTA_GRAFICOS
    return envoltura


# ----------------------------------------------------------------------------- utilidades
def _limpiar(obj):
    """Hace serializable a JSON estándar: numpy -> python, nan/inf -> None."""
    if isinstance(obj, dict):
        return {k: _limpiar(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_limpiar(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return _limpiar(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def _respuesta(datos: dict, texto: str, *graficos: tuple[str, bytes]):
    """Arma el resultado: JSON + (si storage respondió) links markdown + ImageContent de respaldo."""
    datos = dict(datos)
    datos["explicacion"] = texto
    resultado: list = [json.dumps(_limpiar(datos), ensure_ascii=False, indent=2)]
    # El link se agrega como un dato más, sin imperativos (ver NOTA_GRAFICOS).
    links = []
    for descripcion, png in graficos:
        url = storage.subir_imagen(png)
        if url:
            links.append(f"![{descripcion}]({url})")
    if links:
        resultado.append("\n".join(links))
    resultado += [Image(data=png, format="png") for _, png in graficos]
    return resultado


def _convergencia_segura(fn, *args):
    """El análisis de convergencia es un extra: si falla (p. ej. dominio), no rompe la tool."""
    try:
        return fn(*args)
    except (val.ErrorValidacion, ArithmeticError, ValueError):
        return None


# ----------------------------------------------------------------------------- tools
@mcp.tool()
@_manejar_errores
def derivacion_richardson(expresion: str, x0: float, h: float = 0.5, niveles: int = 6,
                          tolerancia: float | None = None, variable: str = "x"):
    """Deriva numéricamente f en x0 con diferencias centradas + extrapolación de Richardson.

    Devuelve la derivada aproximada, la tabla de aproximaciones (una fila por h, h/2, h/4...),
    el error estimado, el análisis de convergencia y gráficos (tabla como mapa de calor y
    error vs. h antes/después de extrapolar). `tolerancia` (opcional) detiene el refinamiento
    cuando la diferencia entre extrapolaciones consecutivas baja de ese valor.
    """
    f = val.envolver_finita(val.compilar_funcion(expresion, (variable,)))
    x0 = val.validar_real(x0, "x0")
    h = val.validar_paso(h)
    niveles = val.validar_entero(niveles, "niveles", 2, 15)
    tol = None if tolerancia is None else val.validar_tolerancia(tolerancia)

    res = dr.derivada_richardson(f, x0, h, niveles, tol)
    res["expresion"] = expresion
    analisis = _convergencia_segura(conv.convergencia_derivada, f, x0)
    graficos = [("Tabla de Richardson (derivada)", viz.heatmap_tabla(res["tabla"], "Tabla de Richardson (derivada)"))]
    texto = exp.explicar_derivada(res)
    if analisis:
        res["convergencia"] = analisis
        graficos.append(("Convergencia de la derivada",
                         viz.grafico_convergencia(analisis, "Derivada: diferencia central vs. Richardson")))
        texto += " " + exp.explicar_convergencia(analisis)
    return _respuesta(res, texto, *graficos)


@mcp.tool()
@_manejar_errores
def romberg(expresion: str, a: float, b: float, tolerancia: float = 1e-8,
            max_niveles: int = 12, variable: str = "x"):
    """Integra f en [a, b] con el método de Romberg (trapecio + Richardson iterado).

    Devuelve el valor de la integral, la tabla triangular de Romberg completa, el error
    estimado, el análisis de convergencia y gráficos (tabla como mapa de calor y error vs. h
    del trapecio y del trapecio extrapolado).
    """
    f = val.envolver_finita(val.compilar_funcion(expresion, (variable,)))
    a, b = val.validar_intervalo(a, b)
    tol = val.validar_tolerancia(tolerancia)
    max_niveles = val.validar_entero(max_niveles, "max_niveles", 2, 20)

    res = rb.romberg(f, a, b, tol, max_niveles)
    res["expresion"] = expresion
    analisis = _convergencia_segura(conv.convergencia_integral, f, a, b)
    graficos = [("Tabla de Romberg", viz.heatmap_tabla(res["tabla"], "Tabla de Romberg"))]
    texto = exp.explicar_romberg(res)
    if analisis:
        res["convergencia"] = analisis
        graficos.append(("Convergencia de la integral",
                         viz.grafico_convergencia(analisis, "Integral: trapecio vs. Romberg (1 nivel)")))
        texto += " " + exp.explicar_convergencia(analisis)
    return _respuesta(res, texto, *graficos)


@mcp.tool()
@_manejar_errores
def richardson_generico(metodo: str, expresion: str, h0: float = 0.5, niveles: int = 5,
                        x0: float | None = None, a: float | None = None, b: float | None = None,
                        tolerancia: float | None = None, variable: str = "x"):
    """Aplica extrapolación de Richardson a un método base elegido por `metodo`:
    "diferencia_adelante" o "diferencia_central" (requieren x0) o "trapecio" (requiere a y b;
    h0 se ajusta a (b-a)/n0 con n0 entero). Devuelve el resultado, la tabla de extrapolación,
    el orden final alcanzado y un gráfico de la tabla.
    """
    if metodo not in rg.METODOS_BASE:
        raise val.ErrorValidacion(f"Método desconocido '{metodo}'. Opciones: {sorted(rg.METODOS_BASE)}.")
    f = val.envolver_finita(val.compilar_funcion(expresion, (variable,)))
    h0 = val.validar_paso(h0, "h0")
    niveles = val.validar_entero(niveles, "niveles", 2, 15)
    tol = None if tolerancia is None else val.validar_tolerancia(tolerancia)
    orden, incremento = rg.METODOS_BASE[metodo]

    if metodo == "trapecio":
        if a is None or b is None:
            raise val.ErrorValidacion("El método 'trapecio' requiere a y b.")
        a, b = val.validar_intervalo(a, b)
        n0 = max(1, round((b - a) / h0))
        h0 = (b - a) / n0
        base = rg.trapecio(f, a, b)
    else:
        if x0 is None:
            raise val.ErrorValidacion(f"El método '{metodo}' requiere x0.")
        x0 = val.validar_real(x0, "x0")
        base = rg.diferencia_central(f, x0) if metodo == "diferencia_central" else rg.diferencia_adelante(f, x0)

    res = rg.richardson(base, h0, orden, niveles, 2.0, incremento, tol)
    res.update(metodo_base=metodo, expresion=expresion)
    titulo = f"Richardson genérico — {metodo}"
    return _respuesta(res, exp.explicar_generico(res, metodo), (titulo, viz.heatmap_tabla(res["tabla"], titulo)))


@mcp.tool()
@_manejar_errores
def bulirsch_stoer(expresion: str, t0: float, y0: float, tf: float, tolerancia: float = 1e-8):
    """Resuelve la EDO y' = f(t, y) con y(t0) = y0 en [t0, tf] con Bulirsch-Stoer (punto medio
    modificado + Richardson). `expresion` es f(t, y) con las variables t e y, p. ej. "-y" o
    "t*y + sin(t)". Devuelve la solución en cada paso aceptado, y(tf), estadísticas del
    integrador y el gráfico de la trayectoria.
    """
    g = val.envolver_finita(val.compilar_funcion(expresion, ("t", "y")))
    t0, tf = val.validar_real(t0, "t0"), val.validar_real(tf, "tf")
    y0 = val.validar_real(y0, "y0")
    if tf <= t0:
        raise val.ErrorValidacion("Se requiere tf > t0.")
    tol = val.validar_tolerancia(tolerancia)

    def f(t, y):
        return np.array([g(t, float(y[0]))])

    try:
        res = bs.bulirsch_stoer(f, t0, y0, tf, tol)
    except RuntimeError as exc:
        raise val.ErrorValidacion(str(exc)) from exc
    res["expresion"] = f"y' = {expresion}"
    titulo = f"y' = {expresion}, y({t0:g}) = {y0:g}"
    return _respuesta(res, exp.explicar_bulirsch_stoer(res),
                      ("Trayectoria de la solución", viz.grafico_trayectoria(res["t"], res["y"], titulo)))


@mcp.tool()
@_manejar_errores
def analisis_convergencia(problema: str, expresion: str, x0: float | None = None,
                          a: float | None = None, b: float | None = None,
                          valor_exacto: float | None = None, variable: str = "x"):
    """Compara el error antes y después de extrapolar. `problema` es "derivada" (requiere x0;
    base: diferencia central) o "integral" (requiere a y b; base: trapecio compuesto). Si no se
    da `valor_exacto` se calcula una referencia de alta precisión. Devuelve errores por paso,
    órdenes observados vs. teóricos y el gráfico log-log del error.
    """
    f = val.envolver_finita(val.compilar_funcion(expresion, (variable,)))
    exacto = None if valor_exacto is None else val.validar_real(valor_exacto, "valor_exacto")
    if problema == "derivada":
        if x0 is None:
            raise val.ErrorValidacion("problema='derivada' requiere x0.")
        res = conv.convergencia_derivada(f, val.validar_real(x0, "x0"), exacto)
    elif problema == "integral":
        if a is None or b is None:
            raise val.ErrorValidacion("problema='integral' requiere a y b.")
        a, b = val.validar_intervalo(a, b)
        res = conv.convergencia_integral(f, a, b, exacto)
    else:
        raise val.ErrorValidacion("problema debe ser 'derivada' o 'integral'.")
    res["expresion"] = expresion
    return _respuesta(res, exp.explicar_convergencia(res),
                      ("Error antes y después de extrapolar", viz.grafico_convergencia(res)))


if __name__ == "__main__":
    # transport="streamable-http": expone el servidor por HTTP en vez de stdio, así
    # Caddy puede reverse-proxearlo con una URL pública (host 0.0.0.0, puerto 8000).
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
