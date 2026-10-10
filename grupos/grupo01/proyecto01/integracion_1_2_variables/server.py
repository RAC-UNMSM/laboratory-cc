import sympy as sp
from mcp.server.mcpserver import MCPServer
import storage
from validacion import (
    validar_y_parsear_expresion,
    validar_limites_numericos,
    validar_dominio_general,
    ErrorDeEntrada,
)
from matematica import (
    integrar_simple,
    integrar_doble_rectangular,
    integrar_doble_general,
)
from visualizacion import generar_grafico_png

# Instancia del servidor MCP usando el SDK oficial del laboratorio
mcp = MCPServer("grupo01-integracion-1-2-variables")


@mcp.tool()
def integra_simple(expresion: str, x_min: str, x_max: str) -> str:
    """Calcula una integral definida simple sobre la variable x.

    Ejemplo de uso:
      expresion: "x**2 + 3*x"
      x_min: "0"
      x_max: "2"
    """
    try:
        xmin_num, xmax_num = validar_limites_numericos(x_min, x_max, "x")
        expr_sp = validar_y_parsear_expresion(expresion, variables=("x",))

        resultado, latex_str = integrar_simple(expr_sp, xmin_num, xmax_num)
        png_bytes = generar_grafico_png(
            expr_sp, xmin_num, xmax_num, mostrar_local=False
        )

        texto = (
            f"### Resultado - Integral Simple\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
        )

        if png_bytes:
            imagen_url = storage.subir_a_seaweedfs(png_bytes)
            if imagen_url:
                texto += f"\n![Gráfico de la integral]({imagen_url})\n"

        return texto
    except ErrorDeEntrada as e:
        return f"Error de validación:\n{e}"
    except Exception as e:
        return f"Error durante la integración: {e}"


@mcp.tool()
def integra_doble_rectangular(
    expresion: str, x_min: str, x_max: str, y_min: str, y_max: str
) -> str:
    """Calcula una integral doble sobre un dominio rectangular [x_min, x_max] x [y_min, y_max].

    Ejemplo de uso:
      expresion: "x*y"
      x_min: "0"
      x_max: "1"
      y_min: "0"
      y_max: "2"
    """
    try:
        xmin_num, xmax_num = validar_limites_numericos(x_min, x_max, "x")
        ymin_num, ymax_num = validar_limites_numericos(y_min, y_max, "y")
        expr_sp = validar_y_parsear_expresion(expresion, variables=("x", "y"))

        resultado, latex_str = integrar_doble_rectangular(
            expr_sp, xmin_num, xmax_num, ymin_num, ymax_num
        )
        png_bytes = generar_grafico_png(
            expr_sp,
            xmin_num,
            xmax_num,
            y_min=ymin_num,
            y_max=ymax_num,
            mostrar_local=False,
        )

        texto = (
            f"### Resultado - Integral Doble Rectangular\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
        )

        if png_bytes:
            imagen_url = storage.subir_a_seaweedfs(png_bytes)
            if imagen_url:
                texto += f"\n![Gráfico de la integral]({imagen_url})\n"

        return texto
    except ErrorDeEntrada as e:
        return f"Error de validación:\n{e}"
    except Exception as e:
        return f"Error durante la integración: {e}"


@mcp.tool()
def integra_doble_general(
    expresion: str,
    var_interna: str,
    g1_str: str,
    g2_str: str,
    var_externa: str,
    ext_min: str,
    ext_max: str,
) -> str:
    """Calcula una integral doble sobre un dominio general definido por curvas g1 <= var_interna <= g2.

    Ejemplo de uso:
      expresion: "x + y"
      var_interna: "y"
      g1_str: "0"
      g2_str: "x**2"
      var_externa: "x"
      ext_min: "0"
      ext_max: "1"
    """
    try:
        expr_sp, v_int, v_ext, g1_sp, g2_sp, ext_min_num, ext_max_num = (
            validar_dominio_general(
                expresion, var_interna, g1_str, g2_str, var_externa, ext_min, ext_max
            )
        )

        resultado, latex_str = integrar_doble_general(
            expr_sp,
            str(v_int),
            str(g1_sp),
            str(g2_sp),
            str(v_ext),
            ext_min_num,
            ext_max_num,
        )
        png_bytes = generar_grafico_png(
            expr_sp,
            ext_min_num,
            ext_max_num,
            g1_str=str(g1_sp),
            g2_str=str(g2_sp),
            mostrar_local=False,
        )

        texto = (
            f"### Resultado - Integral Doble General\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
        )

        if png_bytes:
            imagen_url = storage.subir_a_seaweedfs(png_bytes)
            if imagen_url:
                texto += f"\n![Gráfico de la integral]({imagen_url})\n"

        return texto
    except ErrorDeEntrada as e:
        return f"Error de validación:\n{e}"
    except Exception as e:
        return f"Error durante la integración: {e}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)