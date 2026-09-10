"""Piloto de servidor MCP propio (ver docs/semana-02/plan.md): deriva una
función de una variable de forma simbólica exacta (sympy, no numérica) y la
grafica junto a la función original. Referencia concreta de cómo se ve el
patrón "grupoNN construye su propio MCP" antes de que los grupos reales lo
hagan con su tema asignado.

Dividido en un módulo por rol -- pensado para que un grupo de 6-7 personas
pueda trabajar en paralelo sin pisarse el mismo archivo:
  - validacion.py    -- rol "Validación de entradas"
  - matematica.py    -- rol "Lógica matemática"
  - visualizacion.py -- rol "Visualización"
  - storage.py       -- rol "Storage/infra"
Este archivo es solo el orquestador: conecta las piezas y define el tool
MCP -- no tiene lógica propia de ningún rol.
"""

import sympy as sp
from mcp.server.mcpserver import Image, MCPServer

import matematica
import storage
import visualizacion
from validacion import ValidationError, parsear_expresion, validar_rango

# Nombre del servidor MCP -- es lo que ve el cliente (Claude, MCP Inspector)
# al conectarse. Cada grupo lo cambia a "grupoNN-<tema>".
mcp = MCPServer("g01-derivadas1")

storage.ensure_bucket()


@mcp.tool()
def derivar(expresion: str, x_min: float = -10, x_max: float = 10):
    """Deriva una función f(x) de una variable (primera derivada) de forma
    simbólica exacta y grafica f(x) junto a f'(x) en el rango dado.

    `expresion` debe estar en sintaxis de Python/sympy, ej: "x**2 + 3*x - 5",
    "sin(x)", "exp(x)*x" -- NO uses notación como "x^2" ni "senx".

    Devuelve un texto con la derivada (en notación normal y en LaTeX) y un
    gráfico con f(x) y f'(x) superpuestas.

    Si la respuesta incluye una línea "![Gráfico de f(x) y f'(x)](https://...)",
    esa imagen es el propio gráfico que este servidor acaba de generar y
    subir (mismo dominio que este MCP) -- inclúyela tal cual, en formato
    markdown, en tu respuesta al usuario en vez de solo describirla, porque
    ningún cliente de chat la renderiza sola a partir del bloque de imagen
    de la tool.

    OJO: este docstring no es solo documentación para humanos — es lo que
    lee la IA para saber en qué formato mandarle la expresión y qué
    significa el resultado (ver "Cómo se le pasa la información al MCP" en
    el plan). Por eso hay que ser explícito con la sintaxis esperada.
    """
    # --- 1-2. Validación de entradas (validacion.py) ---
    try:
        validar_rango(x_min, x_max)
        f = parsear_expresion(expresion)
    except ValidationError as exc:
        return str(exc)

    # --- 3-4. Lógica matemática (matematica.py) ---
    derivada = matematica.derivar_simbolico(f)
    try:
        xs, ys, dys = matematica.evaluar_numerico(f, derivada, x_min, x_max)
    except matematica.EvaluationError as exc:
        return str(exc)

    # --- 5. Visualización (visualizacion.py) ---
    png_bytes = visualizacion.graficar(f, derivada, xs, ys, dys)

    # --- 6. Armar la respuesta ---
    # sp.latex() da la derivada en formato LaTeX (útil si el cliente MCP la
    # quiere renderizar bonito). El resultado de la tool es una lista con
    # texto + imagen: MCP soporta devolver varios bloques de contenido a la
    # vez, no solo uno.
    resumen = (
        f"f(x) = {f}\n"
        f"f'(x) = {derivada}\n"
        f"f'(x) en LaTeX: {sp.latex(derivada)}"
    )

    # El link (si storage.py respondió) se agrega como un dato más del
    # resultado, sin ningún imperativo -- una instrucción tipo "debes
    # mostrar esto" dentro del *resultado* de una tool tiene la forma de un
    # prompt injection (el resultado es datos no confiables por diseño, a
    # diferencia del docstring de arriba, que sí es metadata de confianza).
    # La indicación de cómo tratar este link vive en el docstring, no acá.
    imagen_url = storage.subir_imagen(png_bytes)
    if imagen_url:
        resumen += f"\n\n![Gráfico de f(x) y f'(x)]({imagen_url})"

    return [resumen, Image(data=png_bytes, format="png")]


if __name__ == "__main__":
    # transport="streamable-http": expone el servidor por HTTP en vez de
    # por stdio -- así Caddy puede reverse-proxearlo con una URL pública.
    # (No "sse": esa variante del SDK está poco mantenida -- ver commit que
    # cambió esto -- y se quedaba sin responder. streamable-http es la que
    # de verdad usan los clientes MCP actuales, incluido Claude Code.)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
