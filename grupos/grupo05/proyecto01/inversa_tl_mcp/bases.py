"""Bases como columnas y objetos expresados en coordenadas canónicas."""
import sympy as sp
from validacion import ErrorDeEntrada, matriz_validada


def matriz_json(matriz):
    return [[str(matriz[i,j]) for j in range(matriz.cols)] for i in range(matriz.rows)]


def objeto_desde_coordenadas(espacio, coordenadas):
    if espacio["tipo"] == "vector":
        return [str(v) for v in coordenadas]
    if espacio["tipo"] == "polinomio":
        t = sp.Symbol("t")
        return str(sp.expand(sum(v*t**i for i,v in enumerate(coordenadas))))
    p, q = espacio["parametros"]
    return [[str(coordenadas[i*q+j]) for j in range(q)] for i in range(p)]


def base_validada(espacio, texto=""):
    n = espacio["dimension"]
    base = matriz_validada(texto, n, n) if texto else sp.eye(n)
    if base.det() == 0:
        raise ErrorDeEntrada("Los vectores de una base deben ser linealmente independientes.")
    return base


def describir_base(espacio, base):
    return {
        "matriz_columnas": matriz_json(base),
        "elementos": [objeto_desde_coordenadas(espacio, base[:,j]) for j in range(base.cols)],
        "orden_coordenadas": {"vector": "x1, x2, ...",
                              "polinomio": "coeficientes de 1, t, t^2, ...",
                              "matriz": "por filas: E11, E12, ..., E21, E22, ..."}[espacio["tipo"]],
    }
