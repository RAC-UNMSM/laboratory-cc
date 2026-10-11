"""Matriz asociada, invertibilidad, Gauss-Jordan y reconstrucción exacta."""
from dataclasses import dataclass
import json

import sympy as sp

from bases import base_validada, describir_base, matriz_json, objeto_desde_coordenadas
from validacion import MAX_DIM, ErrorDeEntrada, especificacion_espacio, matriz_de_regla, matriz_validada


def inversa_gauss_jordan(A):
    """Adaptación modular del notebook InversaTL: registra cada operación."""
    if A.rows != A.cols:
        raise ErrorDeEntrada("Solo una matriz cuadrada puede tener inversa bilateral.")
    n = A.rows
    M = A.row_join(sp.eye(n))
    pasos = [{"operacion": "Matriz aumentada inicial [A | I]", "matriz_aumentada": matriz_json(M)}]
    for col in range(n):
        pivote_fila = next((i for i in range(col,n) if M[i,col] != 0), None)
        if pivote_fila is None:
            raise ErrorDeEntrada("La matriz es singular: no existe inversa.")
        if pivote_fila != col:
            M.row_swap(pivote_fila, col)
            pasos.append({"operacion": f"F{col+1} <-> F{pivote_fila+1}", "matriz_aumentada": matriz_json(M)})
        pivote = M[col,col]
        if pivote != 1:
            M.row_op(col, lambda valor,j: valor/pivote)
            pasos.append({"operacion": f"F{col+1} <- ({1/pivote}) F{col+1}", "matriz_aumentada": matriz_json(M)})
        for fila in range(n):
            if fila != col and M[fila,col] != 0:
                factor = M[fila,col]
                M.row_op(fila, lambda valor,j: valor - factor*M[col,j])
                pasos.append({"operacion": f"F{fila+1} <- F{fila+1} - ({factor}) F{col+1}", "matriz_aumentada": matriz_json(M)})
    return M[:,n:], pasos


def analizar_matriz(A):
    cuadrada = A.rows == A.cols
    det = A.det() if cuadrada else None
    invertible = cuadrada and det != 0
    return {
        "filas": A.rows, "columnas": A.cols, "rango": A.rank(),
        "determinante": str(det) if det is not None else None,
        "invertible": bool(invertible),
        "conclusion": ("El determinante es distinto de cero: existe inversa."
                       if invertible else "El determinante es cero: no existe inversa."
                       if cuadrada else "Las dimensiones son distintas: no existe una inversa global bilateral."),
    }


@dataclass
class Transformacion:
    dominio: dict
    codominio: dict
    M: sp.Matrix
    B: sp.Matrix
    C: sp.Matrix
    A: sp.Matrix


def preparar_transformacion(dominio, codominio, regla="", matriz="", base_dominio="", base_codominio=""):
    V, W = especificacion_espacio(dominio), especificacion_espacio(codominio)
    if bool(regla) == bool(matriz):
        raise ErrorDeEntrada("Proporciona exactamente una entrada: regla o matriz canónica.")
    n, m = V["dimension"], W["dimension"]
    M = matriz_de_regla(regla,n,m) if regla else matriz_validada(matriz,m,n)
    B, C = base_validada(V,base_dominio), base_validada(W,base_codominio)
    return Transformacion(V,W,M,B,C,C.inv()*M*B)


def preparar_regla_cuadrada(n, regla):
    """Entrada n/lista del proyecto paralelo, con la validación matemática común."""
    if type(n) is not int or not 1 <= n <= MAX_DIM:
        raise ErrorDeEntrada(f"n debe ser un entero entre 1 y {MAX_DIM}.")
    if not isinstance(regla, list) or len(regla) != n or not all(isinstance(v, str) for v in regla):
        raise ErrorDeEntrada(f"regla debe ser una lista de {n} expresiones de texto.")
    return preparar_transformacion(f"R{n}", f"R{n}", regla=json.dumps(regla))


def construir_datos(T):
    imagenes = []
    for j in range(T.B.cols):
        imagen = T.M*T.B[:,j]
        imagenes.append({"elemento_base_dominio": j+1,
                         "imagen": objeto_desde_coordenadas(T.codominio,imagen),
                         "coordenadas_en_C": [str(v) for v in T.A[:,j]]})
    return {
        "dominio": T.dominio, "codominio": T.codominio,
        "base_B": describir_base(T.dominio,T.B), "base_C": describir_base(T.codominio,T.C),
        "imagenes_de_B": imagenes,
        "matriz_canonica": matriz_json(T.M), "matriz_asociada": matriz_json(T.A),
        "regla_en_coordenadas_canonicas": objeto_desde_coordenadas(
            T.codominio, T.M*sp.Matrix(sp.symbols(f"x1:{T.M.cols+1}"))),
        "formula": "[T]_(C<-B) = C^(-1) M B; [T(v)]_C = A [v]_B",
    }


def analizar(T, incluir_inversa=False):
    resultado = construir_datos(T)
    resultado.update(analizar_matriz(T.A))
    if incluir_inversa:
        resultado["inversa"] = None
        if resultado["invertible"]:
            Ainv, pasos = inversa_gauss_jordan(T.A)
            Minv = T.B*Ainv*T.C.inv()
            variables = sp.Matrix(sp.symbols(f"y1:{T.M.rows+1}"))
            resultado["inversa"] = {
                "matriz_asociada": matriz_json(Ainv),
                "matriz_canonica": matriz_json(Minv),
                "regla_en_coordenadas_canonicas": objeto_desde_coordenadas(T.dominio,Minv*variables),
                "entrada_y": describir_base(T.codominio,sp.eye(T.M.rows))["orden_coordenadas"].replace("x1, x2", "y1, y2"),
                "formula": "[T^(-1)]_(B<-C) = A^(-1); M^(-1) = B A^(-1) C^(-1)",
                "pasos_gauss_jordan": pasos,
                "verificacion": verificar_producto(T.M,Minv),
            }
    return resultado


def verificar_producto(A, candidata):
    if A.rows != A.cols or candidata.shape != A.shape:
        raise ErrorDeEntrada("La matriz y su candidata a inversa deben ser cuadradas y del mismo tamaño.")
    izquierda, derecha = candidata*A, A*candidata
    return {"T_inversa_compuesta_T": matriz_json(izquierda),
            "T_compuesta_T_inversa": matriz_json(derecha),
            "ambas_identidades": izquierda == sp.eye(A.cols) and derecha == sp.eye(A.rows)}
