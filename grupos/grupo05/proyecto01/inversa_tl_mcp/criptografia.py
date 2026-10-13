"""Cifrado Hill didáctico: bloques columna, aritmética exacta módulo m."""
import math

import sympy as sp
from bases import matriz_json
from validacion import ErrorDeEntrada, matriz_validada

ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
AVISO = "Hill es un cifrado histórico educativo, vulnerable a texto conocido; no protege datos reales."


def validar_alfabeto(alfabeto):
    if not isinstance(alfabeto,str) or not 2 <= len(alfabeto) <= 100 or len(set(alfabeto)) != len(alfabeto):
        raise ErrorDeEntrada("El alfabeto debe tener de 2 a 100 símbolos únicos y distinguir mayúsculas/minúsculas.")


def analizar_clave(clave, alfabeto=ALFABETO):
    validar_alfabeto(alfabeto)
    K = matriz_validada(clave)
    if K.rows != K.cols or not 2 <= K.rows <= 4 or any(not v.is_Integer for v in K):
        raise ErrorDeEntrada("La clave debe ser una matriz de enteros cuadrada de tamaño 2, 3 o 4.")
    modulo = len(alfabeto)
    K = K.applyfunc(lambda v: v % modulo)
    det = int(K.det())
    mcd = math.gcd(det,modulo)
    datos = {"clave": matriz_json(K), "modulo": modulo, "alfabeto": alfabeto,
             "determinante": det, "mcd_determinante_modulo": mcd,
             "invertible_modular": mcd == 1, "aviso": AVISO}
    inversa = None
    if mcd == 1:
        # Adjunta válida incluso si módulo es compuesto y no hay pivote unidad.
        det_inv = pow(det,-1,modulo)
        inversa = (det_inv*K.adjugate()).applyfunc(lambda v: v % modulo)
        datos.update({"inverso_del_determinante": det_inv, "clave_inversa": matriz_json(inversa),
                      "formula": "K^(-1) = det(K)^(-1) adj(K) mod m",
                      "verificacion": matriz_json((inversa*K).applyfunc(lambda v:v%modulo))})
    return K,inversa,datos


def transformar_bloques(texto, K, alfabeto):
    n, m = K.rows, len(alfabeto)
    indice = {c:i for i,c in enumerate(alfabeto)}
    salida, pasos = [], []
    for inicio in range(0,len(texto),n):
        bloque = texto[inicio:inicio+n]
        v = sp.Matrix([indice[c] for c in bloque])
        producto = K*v
        residuos = [int(x % m) for x in producto]
        letras = ''.join(alfabeto[x] for x in residuos)
        salida.append(letras)
        pasos.append({"bloque_entrada": bloque, "vector_columna": list(map(int,v)),
                      "producto_sin_modulo": list(map(int,producto)), "residuos": residuos,
                      "bloque_salida": letras})
    return ''.join(salida),pasos


def validar_texto(texto,alfabeto,limite=512):
    if not isinstance(texto,str) or not 1 <= len(texto) <= limite:
        raise ErrorDeEntrada(f"El texto debe tener entre 1 y {limite} caracteres.")
    ajenos = sorted(set(texto)-set(alfabeto))
    if ajenos:
        raise ErrorDeEntrada(f"Símbolos fuera del alfabeto: {ajenos}. No se eliminan ni normalizan automáticamente.")


def cifrar(texto,clave,alfabeto=ALFABETO,relleno="X"):
    K,inv,datos = analizar_clave(clave,alfabeto)
    if inv is None:
        raise ErrorDeEntrada(f"Clave no invertible módulo {len(alfabeto)}: mcd(det,m)={datos['mcd_determinante_modulo']}.")
    validar_texto(texto,alfabeto)
    if len(relleno) != 1 or relleno not in alfabeto:
        raise ErrorDeEntrada("El relleno debe ser un símbolo del alfabeto.")
    cantidad = (-len(texto)) % K.rows
    preparado = texto + relleno*cantidad
    cifrado,pasos = transformar_bloques(preparado,K,alfabeto)
    datos.update({"texto_original": texto, "texto_preparado": preparado, "texto_cifrado": cifrado,
                  "relleno": relleno, "cantidad_relleno": cantidad, "pasos": pasos,
                  "ecuacion": "c = K p mod m; A=0, B=1, ... para el alfabeto predeterminado"})
    return datos


def descifrar(texto,clave,alfabeto=ALFABETO,cantidad_relleno=0,relleno="X"):
    K,inv,datos = analizar_clave(clave,alfabeto)
    if inv is None:
        raise ErrorDeEntrada("La clave no tiene inversa modular; no se puede descifrar.")
    validar_texto(texto,alfabeto,limite=515)
    if len(texto) % K.rows:
        raise ErrorDeEntrada("La longitud del texto cifrado debe ser múltiplo del tamaño del bloque.")
    if type(cantidad_relleno) is not int or not 0 <= cantidad_relleno < K.rows:
        raise ErrorDeEntrada("La cantidad de relleno debe ser un entero entre 0 y tamaño_bloque-1.")
    if len(relleno) != 1 or relleno not in alfabeto:
        raise ErrorDeEntrada("El relleno debe ser un símbolo del alfabeto.")
    preparado,pasos = transformar_bloques(texto,inv,alfabeto)
    if cantidad_relleno and not preparado.endswith(relleno*cantidad_relleno):
        raise ErrorDeEntrada("El relleno declarado no coincide con el texto recuperado.")
    original = preparado[:-cantidad_relleno] if cantidad_relleno else preparado
    datos.update({"texto_descifrado": original, "texto_con_relleno": preparado,
                  "cantidad_relleno": cantidad_relleno, "pasos": pasos,
                  "ecuacion": "p = K^(-1) c mod m"})
    return datos
