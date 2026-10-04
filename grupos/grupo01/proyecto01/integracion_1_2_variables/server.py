import os
import base64
import subprocess
import sympy as sp
from fastmcp import FastMCP
from mcp.types import ImageContent
from validacion import (
    validar_y_parsear_expresion,
    validar_limites_numericos,
    validar_dominio_general,
    ErrorDeEntrada
)
from matematica import integrar_simple, integrar_doble_rectangular, integrar_doble_general
from visualizacion import generar_grafico_png
from reporte_html import generar_reporte_html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTE_PATH = os.path.join(BASE_DIR, "reporte_integral.html")

mcp = FastMCP("Calculadora Integrales")

def abrir_reporte_en_mac(ruta):
    """Fuerza la apertura del archivo HTML en el navegador predeterminado de macOS."""
    try:
        subprocess.Popen(["open", ruta])
    except Exception:
        pass

@mcp.tool()
def integra_simple(expresion: str, x_min: str, x_max: str):
    """Calcula una integral definida simple sobre la variable x."""
    try:
        xmin_num, xmax_num = validar_limites_numericos(x_min, x_max, "x")
        expr_sp = validar_y_parsear_expresion(expresion, variables=('x',))

        resultado, latex_str = integrar_simple(expr_sp, xmin_num, xmax_num)
        png_bytes = generar_grafico_png(expr_sp, xmin_num, xmax_num, mostrar_local=False)

        generar_reporte_html(
            tipo_integral="Integral Simple",
            latex_str=latex_str,
            resultado_exacto=sp.latex(resultado),
            resultado_decimal=float(resultado),
            png_bytes=png_bytes,
            nombre_archivo=REPORTE_PATH,
            abrir_en_navegador=False
        )
        abrir_reporte_en_mac(REPORTE_PATH)

        texto = (
            f"### Resultado - Integral Simple\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
            f"- **Informe HTML:** Guardado en `{REPORTE_PATH}`\n"
        )
        img_b64 = base64.b64encode(png_bytes).decode("utf-8")
        return [texto, ImageContent(type="image", data=img_b64, mimeType="image/png")]
    except ErrorDeEntrada as e:
        return f"Error de validación:\n{e}"
    except Exception as e:
        return f"Error durante la integración: {e}"

@mcp.tool()
def integra_doble_rectangular(expresion: str, x_min: str, x_max: str, y_min: str, y_max: str):
    """Calcula una integral doble sobre un dominio rectangular [x_min, x_max] x [y_min, y_max]."""
    try:
        xmin_num, xmax_num = validar_limites_numericos(x_min, x_max, "x")
        ymin_num, ymax_num = validar_limites_numericos(y_min, y_max, "y")
        expr_sp = validar_y_parsear_expresion(expresion, variables=('x', 'y'))

        resultado, latex_str = integrar_doble_rectangular(
            expr_sp, xmin_num, xmax_num, ymin_num, ymax_num
        )
        png_bytes = generar_grafico_png(
            expr_sp, xmin_num, xmax_num, y_min=ymin_num, y_max=ymax_num, mostrar_local=False
        )

        generar_reporte_html(
            tipo_integral="Integral Doble Rectangular",
            latex_str=latex_str,
            resultado_exacto=sp.latex(resultado),
            resultado_decimal=float(resultado),
            png_bytes=png_bytes,
            nombre_archivo=REPORTE_PATH,
            abrir_en_navegador=False
        )
        abrir_reporte_en_mac(REPORTE_PATH)

        texto = (
            f"### Resultado - Integral Doble Rectangular\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
            f"- **Informe HTML:** Guardado en `{REPORTE_PATH}`\n"
        )
        img_b64 = base64.b64encode(png_bytes).decode("utf-8")
        return [texto, ImageContent(type="image", data=img_b64, mimeType="image/png")]
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
    ext_max: str
):
    """Calcula una integral doble sobre un dominio general definido por curvas g1 <= var_interna <= g2."""
    try:
        expr_sp, v_int, v_ext, g1_sp, g2_sp, ext_min_num, ext_max_num = validar_dominio_general(
            expresion, var_interna, g1_str, g2_str, var_externa, ext_min, ext_max
        )

        resultado, latex_str = integrar_doble_general(
            expr_sp, str(v_int), str(g1_sp), str(g2_sp), str(v_ext), ext_min_num, ext_max_num
        )
        png_bytes = generar_grafico_png(
            expr_sp, ext_min_num, ext_max_num, g1_str=str(g1_sp), g2_str=str(g2_sp), mostrar_local=False
        )

        generar_reporte_html(
            tipo_integral="Integral Doble General",
            latex_str=latex_str,
            resultado_exacto=sp.latex(resultado),
            resultado_decimal=float(resultado),
            png_bytes=png_bytes,
            nombre_archivo=REPORTE_PATH,
            abrir_en_navegador=False
        )
        abrir_reporte_en_mac(REPORTE_PATH)

        texto = (
            f"### Resultado - Integral Doble General\n"
            f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
            f"- **Resultado exacto:** `{resultado}`\n"
            f"- **Resultado decimal:** `{float(resultado):.4f}`\n"
            f"- **Informe HTML:** Guardado en `{REPORTE_PATH}`\n"
        )
        img_b64 = base64.b64encode(png_bytes).decode("utf-8")
        return [texto, ImageContent(type="image", data=img_b64, mimeType="image/png")]
    except ErrorDeEntrada as e:
        return f"Error de validación:\n{e}"
    except Exception as e:
        return f"Error durante la integración: {e}"

if __name__ == "__main__":
    mcp.run()
