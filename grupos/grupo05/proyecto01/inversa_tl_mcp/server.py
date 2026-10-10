"""Servidor MCP del grupo 05. HTTP para el laboratorio y stdio para uso local."""
import argparse
from functools import wraps
import os
from typing import Any

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from validacion import ErrorDeEntrada, matriz_validada, vector_validado
from matematica import (preparar_transformacion, construir_datos, analizar,
                        analizar_matriz, inversa_gauss_jordan, verificar_producto,
                        preparar_regla_cuadrada)
from presentacion import construir_presentacion
from bases import matriz_json
from criptografia import ALFABETO, analizar_clave, cifrar, descifrar
from visualizacion import generar_grafico_png
import storage

mcp = MCPServer(
    "grupo05-inversa-tl-mcp", version="1.1.0",
    instructions="Tutor de álgebra lineal: usa coordenadas canónicas como entrada y bases como columnas. "
                 "Explica los pasos exactos y verifica las composiciones. Hill se usa solo con fines educativos.",
)


def entrada_controlada(funcion):
    @wraps(funcion)
    def envoltura(*args,**kwargs):
        try:
            return funcion(*args,**kwargs)
        except ErrorDeEntrada as exc:
            raise ToolError(str(exc)) from exc
    return envoltura


@mcp.tool()
@entrada_controlada
def calcular_inversa_tl(n: int, regla: list[str]) -> str:
    """Resuelve T:Rn->Rn en una sola llamada y devuelve la solución completa en Markdown y LaTeX.

    Incluye base canónica, imágenes, matriz, determinante, rango, Gauss-Jordan, inversa y ambas composiciones.
    n es un entero de 1 a 8; regla es una lista de n expresiones con x1,...,xn.
    Ejemplo: n=2, regla=["3x1+2x2", "x1+x2"]. También admite multiplicación explícita con *.
    Si la matriz es singular, explica que no hay inversa. Entradas no lineales producen un error MCP.
    """
    transformacion = preparar_regla_cuadrada(n, regla)
    return construir_presentacion(analizar(transformacion, incluir_inversa=True))


@mcp.tool()
@entrada_controlada
def analizar_transformacion(dominio: str, codominio: str, regla: str = "", matriz: str = "",
                            base_dominio: str = "", base_codominio: str = "") -> dict[str, Any]:
    """Analiza T entre Rn, Pn o Mpxq. Da exactamente regla (JSON de x1,x2,...) o matriz canónica (JSON).

    Ejemplo: dominio=R2, codominio=R2, regla='["2*x1+x2", "x1-x2"]'.
    P2 usa coeficientes de 1,t,t²; M2x3 usa entradas por filas. Las bases opcionales tienen vectores como columnas.
    """
    return analizar(preparar_transformacion(dominio,codominio,regla,matriz,base_dominio,base_codominio))


@mcp.tool()
@entrada_controlada
def construir_matriz_asociada(dominio: str, codominio: str, regla: str = "", matriz: str = "",
                             base_dominio: str = "", base_codominio: str = "") -> dict[str, Any]:
    """Muestra B, C, T(b_j) y A=C^(-1)MB. Espacios Rn, Pn o Mpxq y exactamente regla o matriz JSON.

    Ejemplo: dominio='R2', codominio='R2', matriz='[[2,1],[1,-1]]'.
    Las bases opcionales son matrices JSON con los vectores como columnas en coordenadas canónicas.
    """
    return construir_datos(preparar_transformacion(dominio,codominio,regla,matriz,base_dominio,base_codominio))


@mcp.tool()
@entrada_controlada
def verificar_invertibilidad(matriz: str) -> dict[str, Any]:
    """Determina rango, determinante e invertibilidad. Ejemplo matriz='[[2,1],[1,-1]]'; admite rectangulares."""
    return analizar_matriz(matriz_validada(matriz))


@mcp.tool()
@entrada_controlada
def hallar_inversa(dominio: str, codominio: str, regla: str = "", matriz: str = "",
                  base_dominio: str = "", base_codominio: str = "") -> dict[str, Any]:
    """Reconstruye T^(-1), muestra Gauss-Jordan y verifica ambas composiciones.

    Espacios Rn, Pn o Mpxq; exactamente regla o matriz canónica JSON.
    Ejemplo: dominio='R2', codominio='R2', regla='["2*x1+x2","x1-x2"]'.
    Las bases opcionales son matrices JSON cuyos vectores base son columnas.
    """
    return analizar(preparar_transformacion(dominio,codominio,regla,matriz,base_dominio,base_codominio),incluir_inversa=True)


@mcp.tool()
@entrada_controlada
def mostrar_gauss_jordan(matriz: str) -> dict[str, Any]:
    """Invierte una matriz JSON con los estados de [A|I] hasta [I|A^(-1)]. Ejemplo matriz='[[2,1],[1,-1]]'."""
    inversa,pasos = inversa_gauss_jordan(matriz_validada(matriz))
    return {"inversa": matriz_json(inversa), "pasos": pasos}


@mcp.tool()
@entrada_controlada
def verificar_inversa(matriz: str, candidata: str) -> dict[str, Any]:
    """Comprueba ambos productos identidad con matrices JSON y aritmética exacta.

    Ejemplo: matriz='[[3,2],[1,1]]', candidata='[[1,-2],[-1,3]]'.
    """
    return verificar_producto(matriz_validada(matriz),matriz_validada(candidata))


@mcp.tool()
@entrada_controlada
def visualizar_transformacion(matriz: str, vector: str = "") -> list:
    """Grafica R2->R2 o R3->R3. Ejemplo matriz='[[2,1],[1,-1]]', vector='[1,2]'.

    Devuelve un PNG MCP y, si el storage del laboratorio está configurado, su enlace público.
    El vector JSON es opcional, por defecto [1,1,...]. El enlace Markdown corresponde al gráfico
    generado y puede incluirse tal cual en la respuesta del cliente.
    """
    A = matriz_validada(matriz)
    v = vector_validado(vector or str([1]*A.cols),A.cols)
    png_bytes = generar_grafico_png(A,v)
    resultado = [Image(data=png_bytes,format="png")]
    imagen_url = storage.subir_imagen(png_bytes)
    if imagen_url:
        resultado.append(f"![Gráfico de la transformación lineal]({imagen_url})")
    return resultado


@mcp.tool()
@entrada_controlada
def analizar_clave_hill(clave: str, alfabeto: str = ALFABETO) -> dict[str, Any]:
    """Analiza una clave Hill entera 2x2, 3x3 o 4x4. Ejemplo clave='[[3,3],[2,5]]'.

    Invertible módulo m si y solo si mcd(det(K),m)=1. Alfabeto por defecto A-Z, A=0.
    """
    return analizar_clave(clave,alfabeto)[2]


@mcp.tool()
@entrada_controlada
def cifrar_hill(texto: str, clave: str, alfabeto: str = ALFABETO, relleno: str = "X") -> dict[str, Any]:
    """Cifra bloques columna: c=Kp mod m. Ejemplo texto=HOLA, clave='[[3,3],[2,5]]'. Respeta exactamente el alfabeto."""
    return cifrar(texto,clave,alfabeto,relleno)


@mcp.tool()
@entrada_controlada
def descifrar_hill(texto: str, clave: str, alfabeto: str = ALFABETO,
                  cantidad_relleno: int = 0, relleno: str = "X") -> dict[str, Any]:
    """Recupera p=K^(-1)c mod m. Ejemplo texto='LGHW', clave='[[3,3],[2,5]]', cantidad_relleno=0.

    Usa el mismo alfabeto y cantidad_relleno devuelta al cifrar; conserva letras finales originales.
    """
    return descifrar(texto,clave,alfabeto,cantidad_relleno,relleno)


@mcp.resource("algebra://guia",mime_type="text/markdown")
def guia() -> str:
    """Convenciones de coordenadas y diferencias entre inversa real y modular."""
    return ("# Grupo 05: álgebra lineal\n"
            "Rn tiene dimensión n; Pn tiene dimensión n+1; Mpxq tiene dimensión p*q.\n"
            "P2: a0+a1*t+a2*t² se ingresa como [a0,a1,a2]. Matrices se recorren por filas.\n"
            "Las columnas de B y C son vectores en coordenadas canónicas; A=C^(-1)MB.\n"
            "Una inversa global requiere dimensiones iguales y determinante distinto de cero.\n"
            "En Hill módulo m se necesita mcd(det(K),m)=1, una condición más fuerte.\n"
            "Se aceptan coeficientes racionales exactos y dimensión máxima 8; Hill admite bloques 2 a 4.\n")


@mcp.prompt()
def tutor_algebra() -> str:
    """Secuencia de estudio y demostración para la exposición del grupo."""
    return ("Analiza T:R2->R2, T(x1,x2)=(2*x1+x2,x1-x2). Construye su matriz, "
            "explica Gauss-Jordan, reconstruye la inversa, verifica ambas composiciones y grafica [1,2]. "
            "Luego cifra HOLA con [[3,3],[2,5]], descifra el resultado y explica la condición modular.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP de álgebra lineal del grupo 05")
    parser.add_argument("--transport",choices=["streamable-http","stdio"],default="streamable-http")
    parser.add_argument("--host",default=os.getenv("MCP_HOST","127.0.0.1"))
    parser.add_argument("--port",type=int,default=int(os.getenv("MCP_PORT","8000")))
    args=parser.parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http",host=args.host,port=args.port)
