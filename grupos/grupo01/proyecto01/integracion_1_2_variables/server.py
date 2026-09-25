from mcp.server.fastmcp import FastMCP, Image
import sympy as sp

from validacion import validar_y_parsear_expresion, validar_limites_numericos
from matematica import integrar_simple, integrar_doble_rectangular, integrar_doble_general
from visualizacion import generar_grafico_png
from storage import subir_a_seaweedfs

mcp = FastMCP("Calculadora Integrales MCP")

@mcp.tool()
def integra_simple(expresion: str, x_min: float, x_max: float):
    """Calcula integrales definidas simples de una variable."""
    validar_limites_numericos(x_min, x_max, "x")
    expr_sp = validar_y_parsear_expresion(expresion)
    
    resultado, latex_str = integrar_simple(expr_sp, x_min, x_max)
    png_bytes = generar_grafico_png(expr_sp, x_min, x_max)
    public_url = subir_a_seaweedfs(png_bytes)
    
    texto = (
        f"### Resultado - Integral Simple\n"
        f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
        f"- **Resultado numérico/exacto:** `{resultado}`\n\n"
        f"![Gráfico Área]({public_url})"
    )
    return [texto, Image(data=png_bytes, format="png")]

@mcp.tool()
def integra_doble_rectangular(expresion: str, x_min: float, x_max: float, y_min: float, y_max: float):
    """Calcula integrales dobles sobre un dominio rectangular."""
    validar_limites_numericos(x_min, x_max, "x")
    validar_limites_numericos(y_min, y_max, "y")
    expr_sp = validar_y_parsear_expresion(expresion)
    
    resultado, latex_str = integrar_doble_rectangular(expr_sp, x_min, x_max, y_min, y_max)
    png_bytes = generar_grafico_png(expr_sp, x_min, x_max, y_min, y_max)
    public_url = subir_a_seaweedfs(png_bytes)
    
    texto = (
        f"### Resultado - Integral Doble Rectangular\n"
        f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
        f"- **Resultado numérico/exacto:** `{resultado}`\n\n"
        f"![Gráfico Volumen]({public_url})"
    )
    return [texto, Image(data=png_bytes, format="png")]

@mcp.tool()
def integra_doble_general(
    expresion: str, 
    var_interna: str, 
    g1_str: str, 
    g2_str: str, 
    var_externa: str, 
    ext_min: float, 
    ext_max: float
):
    """
    Calcula integrales dobles sobre dominios no rectangulares (Tipo X o Tipo Y).
    - var_interna: variable de la integral interna (ej: 'y')
    - g1_str, g2_str: límites funcional inferior e superior (ej: '0', 'x**2')
    - var_externa: variable externa (ej: 'x')
    - ext_min, ext_max: límites constantes externos
    """
    validar_limites_numericos(ext_min, ext_max, var_externa)
    expr_sp = validar_y_parsear_expresion(expresion)
    
    resultado, latex_str = integrar_doble_general(
        expr_sp, var_interna, g1_str, g2_str, var_externa, ext_min, ext_max
    )
    png_bytes = generar_grafico_png(expr_sp, ext_min, ext_max)
    public_url = subir_a_seaweedfs(png_bytes)
    
    texto = (
        f"### Resultado - Integral Doble General\n"
        f"- **Expresión LaTeX:** $${latex_str} = {sp.latex(resultado)}$$\n"
        f"- **Resultado numérico/exacto:** `{resultado}`\n\n"
        f"![Gráfico Volumen]({public_url})"
    )
    return [texto, Image(data=png_bytes, format="png")]

if __name__ == "__main__":
    mcp.run()
