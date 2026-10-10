from mcp.server import MCPServer

from validacion import validar_transformacion
from matriz_tl import (
    construir_matriz_estandar,
    analizar_invertibilidad
)
from gauss_jordan import invertir_gauss_jordan
from inversa_tl import analizar_transformacion_inversa
from presentacion import construir_presentacion
from storage import guardar_registro


# ============================================================
# SERVIDOR MCP
# ============================================================

mcp = MCPServer("inversa-tl-mcp")


# ============================================================
# HERRAMIENTA PRINCIPAL
# ============================================================

@mcp.tool()
def calcular_inversa_tl(
    n: int,
    regla: list[str]
) -> str:
    """
    Analiza una transformación lineal T: R^n -> R^n
    y, cuando es invertible, calcula su transformación
    inversa paso a paso.

    Parámetros
    ----------
    n:
        Dimensión del espacio R^n.

    regla:
        Lista con las n componentes de la regla de
        correspondencia, usando las variables
        x1, x2, ..., xn.

        Ejemplo para R^3:

        [
            "x1",
            "x2 + x3",
            "x2 - x3"
        ]

    Procedimiento
    -------------
    1. Valida la entrada.
    2. Comprueba que sea una transformación lineal.
    3. Construye la matriz estándar.
    4. Calcula el determinante.
    5. Determina si la transformación es invertible.
    6. Si es invertible, calcula A^(-1) mediante Gauss-Jordan.
    7. Construye T^(-1).
    8. Verifica las dos composiciones.
    9. Registra la consulta.
    10. Devuelve una solución detallada en Markdown + LaTeX.
    """

    try:
        # ----------------------------------------------------
        # 1. VALIDACIÓN
        # ----------------------------------------------------

        datos = validar_transformacion(
            n,
            regla
        )

        variables = datos["variables"]
        componentes = datos["componentes"]


        # ----------------------------------------------------
        # 2. MATRIZ ESTÁNDAR
        # ----------------------------------------------------

        matriz_estandar = construir_matriz_estandar(
            componentes,
            variables
        )


        # ----------------------------------------------------
        # 3. ANÁLISIS DE INVERTIBILIDAD
        # ----------------------------------------------------

        analisis = analizar_invertibilidad(
            matriz_estandar
        )

        determinante = analisis["determinante"]


        # ----------------------------------------------------
        # 4. CASO NO INVERTIBLE
        # ----------------------------------------------------

        if not analisis["invertible"]:

            guardar_registro(
                n=n,
                regla=regla,
                estado="no_invertible",
                resultado={
                    "determinante": str(determinante)
                }
            )

            return construir_presentacion(
                componentes=componentes,
                variables=variables,
                matriz_estandar=matriz_estandar,
                analisis_invertibilidad=analisis
            )


        # ----------------------------------------------------
        # 5. GAUSS-JORDAN
        # ----------------------------------------------------

        resultado_gauss = invertir_gauss_jordan(
            matriz_estandar
        )


        # ----------------------------------------------------
        # 6. CONSTRUIR Y VERIFICAR T^(-1)
        # ----------------------------------------------------

        resultado_inversa = analizar_transformacion_inversa(
            componentes,
            variables,
            resultado_gauss["inversa"]
        )


        # ----------------------------------------------------
        # 7. REGISTRO DE LA CONSULTA
        # ----------------------------------------------------

        guardar_registro(
            n=n,
            regla=regla,
            estado="invertible",
            resultado={
                "determinante": str(determinante),
                "matriz_inversa": str(
                    resultado_gauss["inversa"]
                ),
                "verificada": (
                    resultado_inversa["es_inversa"]
                )
            }
        )


        # ----------------------------------------------------
        # 8. PRESENTACIÓN FINAL
        # ----------------------------------------------------

        return construir_presentacion(
            componentes=componentes,
            variables=variables,
            matriz_estandar=matriz_estandar,
            analisis_invertibilidad=analisis,
            resultado_gauss=resultado_gauss,
            resultado_inversa=resultado_inversa
        )


    except ValueError as error:

        guardar_registro(
            n=n,
            regla=regla,
            estado="entrada_invalida",
            resultado={
                "motivo": str(error)
            }
        )

        return (
            "# No se pudo procesar la transformación\n\n"
            f"**Motivo:** {error}"
        )


# ============================================================
# EJECUCIÓN DEL SERVIDOR
# ============================================================

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )