"""Piloto de servidor MCP propio (ver docs/semana-02/plan.md): deriva una
función de una variable de forma simbólica exacta (sympy, no numérica) y la
grafica junto a la función original. Referencia concreta de cómo se ve el
patrón "grupoNN construye su propio MCP" antes de que los grupos reales lo
hagan con su tema asignado.
"""

import io

# matplotlib.use("Agg") ANTES de importar pyplot: le dice que dibuje a un
# archivo/buffer en memoria en vez de abrir una ventana — el contenedor no
# tiene pantalla, así que sin esto pyplot fallaría al importarse.
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from mcp.server.mcpserver import Image, MCPServer

# Nombre del servidor MCP — es lo que ve el cliente (Claude, MCP Inspector)
# al conectarse. Cada grupo lo cambia a "grupoNN-<tema>".
mcp = MCPServer("g01-derivadas1")

# Símbolo matemático "x" que usa sympy para el cálculo simbólico (derivar,
# evaluar, etc.) — se define una sola vez y se reusa en toda la tool.
x = sp.symbols("x")


@mcp.tool()
def derivar(expresion: str, x_min: float = -10, x_max: float = 10):
    """Deriva una función f(x) de una variable (primera derivada) de forma
    simbólica exacta y grafica f(x) junto a f'(x) en el rango dado.

    `expresion` debe estar en sintaxis de Python/sympy, ej: "x**2 + 3*x - 5",
    "sin(x)", "exp(x)*x" -- NO uses notación como "x^2" ni "senx".

    Devuelve un texto con la derivada (en notación normal y en LaTeX) y un
    gráfico con f(x) y f'(x) superpuestas.

    OJO: este docstring no es solo documentación para humanos — es lo que
    lee la IA para saber en qué formato mandarle la expresión y qué
    significa el resultado (ver "Cómo se le pasa la información al MCP" en
    el plan). Por eso hay que ser explícito con la sintaxis esperada.
    """
    # --- 1. Validar el rango (rol "Validación de entradas") ---
    if x_min >= x_max:
        return f"Error: x_min ({x_min}) debe ser menor que x_max ({x_max})."

    # --- 2. Convertir el texto en una expresión matemática real ---
    # sp.sympify() interpreta el string como matemática simbólica; si el
    # texto no tiene sentido matemático, lanza una excepción que atajamos
    # acá para devolver un mensaje de error legible en vez de que el
    # servidor se caiga.
    try:
        f = sp.sympify(expresion)
    except (sp.SympifyError, TypeError, SyntaxError) as exc:
        return (
            f"Error: no se pudo interpretar '{expresion}' como una función de x. "
            f"Usa sintaxis de Python/sympy (ej. 'x**2 + 3*x', 'sin(x)'). Detalle: {exc}"
        )

    # Esta tool solo maneja funciones de UNA variable ("x"). Si la expresión
    # trae otras letras (ej. "y", "z"), no tiene sentido derivar respecto a
    # "x" solamente — se avisa en vez de dar un resultado engañoso.
    variables_libres = f.free_symbols - {x}
    if variables_libres:
        return (
            f"Error: la expresión usa variables además de 'x': {variables_libres}. "
            "Esta tool solo deriva funciones de una variable."
        )

    # --- 3. Lógica matemática (rol "Lógica matemática") ---
    # sp.diff() calcula la derivada EXACTA (simbólica), no una aproximación
    # numérica — por eso vale la pena tener esto en un MCP: es un resultado
    # garantizado-correcto, no algo que la IA "calculó a ojo".
    derivada = sp.diff(f, x)

    # --- 4. Preparar los valores numéricos para graficar ---
    # sp.lambdify() convierte la expresión simbólica en una función Python
    # normal (evaluable con arrays de numpy) — sympy es para el resultado
    # exacto, numpy es para graficar rápido sobre muchos puntos a la vez.
    try:
        f_num = sp.lambdify(x, f, "numpy")
        df_num = sp.lambdify(x, derivada, "numpy")
        xs = np.linspace(x_min, x_max, 400)
        ys = np.asarray(f_num(xs), dtype=float)
        dys = np.asarray(df_num(xs), dtype=float)
    except Exception as exc:
        # Ej: la función tiene una operación inválida para ciertos valores
        # (raíz de negativo, etc.) que numpy no puede evaluar en el rango.
        return f"Error: la función no se pudo evaluar en [{x_min}, {x_max}]: {exc}"

    # --- 5. Visualización (rol "Visualización") ---
    # Un solo gráfico con f(x) y f'(x) superpuestas, para comparar la forma
    # de la función original contra la de su derivada.
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, ys, label=f"f(x) = {f}")
    ax.plot(xs, dys, label=f"f'(x) = {derivada}", linestyle="--")
    ax.axhline(0, color="black", linewidth=0.5)  # eje X de referencia
    ax.axvline(0, color="black", linewidth=0.5)  # eje Y de referencia
    ax.legend()
    ax.set_title("f(x) y su derivada")
    ax.grid(True, alpha=0.3)

    # Guardar el gráfico en un buffer en memoria (no en un archivo en
    # disco) porque el contenedor no persiste nada entre llamadas — la
    # imagen viaja directo en la respuesta de la tool.
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)  # libera la figura de memoria; si no, se acumulan

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
    return [resumen, Image(data=buf.getvalue(), format="png")]


if __name__ == "__main__":
    # transport="streamable-http": expone el servidor por HTTP en vez de
    # por stdio -- así Caddy puede reverse-proxearlo con una URL pública.
    # (No "sse": esa variante del SDK está poco mantenida -- ver commit que
    # cambió esto -- y se quedaba sin responder. streamable-http es la que
    # de verdad usan los clientes MCP actuales, incluido Claude Code.)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
