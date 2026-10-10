"""Cliente MCP real: habla con server.py por stdio, como lo haria Claude.

Sirve para dos cosas:

  1. PROBAR que el servidor funciona fuera de su propio proceso. Todo lo otro
     que hay en la carpeta llama a las tools importando `server` en el mismo
     interprete; esto las llama por el protocolo MCP de verdad (initialize ->
     tools/list -> tools/call, sobre stdio), que es lo que hace un cliente real.

  2. TENER ALGO DONDE MANDAR UN EJERCICIO HOY, sin instalar Claude Desktop.

Ejercicios de ejemplo:
    python _cliente.py
    python _cliente.py limite     sin(x)/x en 0
    python _cliente.py derivada   x**3*sin(x)
    python _cliente.py integral   x*exp(x)
    python _cliente.py doble      x*y en [0,1]x[0,1]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

APP_DIR = Path(__file__).resolve().parent

# Las tools devuelven simbolos matematicos que la consola de Windows (cp1252)
# no sabe imprimir: el primo de la derivada (y'), las raices, los signos de
# grado. Sin esto, el cliente revienta con UnicodeEncodeError al mostrar una
# respuesta que era CORRECTA.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Cada caso: (etiqueta, tool, argumentos, que hay que ver en la respuesta)
EJERCICIOS = {
    "limite": (
        "limite de sin(x)/x en x->0  (Cálculo I)",
        "calculo1_calcular_limite",
        {"expresion": "sin(x)/x", "punto": "0", "modo": "paso_a_paso"},
    ),
    "continuidad": (
        "tipo de discontinuidad de x/x en x=0  (Cálculo I)",
        "calculo1_analizar_continuidad",
        {"expresion": "x/x", "punto": "0", "modo": "paso_a_paso"},
    ),
    "tangente": (
        "recta tangente a x**2 en x=2  (Cálculo I)",
        "calculo1_recta_tangente",
        {"expresion": "x**2", "punto": "2", "modo": "paso_a_paso"},
    ),
    "derivada": (
        "derivada de x**3*sin(x)  (Cálculo I)",
        "calculo1_calcular_derivada",
        {"expresion": "x**3*sin(x)", "modo": "paso_a_paso"},
    ),
    "integral": (
        "integral indefinida de x*exp(x)  (Cálculo II)",
        "calculo2_calcular_integral_indefinida",
        {"expresion": "x*exp(x)", "modo": "paso_a_paso"},
    ),
    "riemann": (
        "integral de x**2 en [0,1] por sumas de Riemann  (Cálculo II)",
        "calculo2_riemann_y_teorema_fundamental",
        {"expresion": "x**2", "a_str": "0", "b_str": "1",
         "n_particiones": 4, "regla_riemann": "derecha", "modo": "paso_a_paso"},
    ),
    "doble": (
        "integral doble de x*y en [0,1]x[0,1]  (Cálculo IV)",
        "calculo4_integral_doble",
        {"expresion": "x*y", "x_inferior": "0", "x_superior": "1",
         "y_inferior": "0", "y_superior": "1"},
    ),
    "green": (
        "teorema de Green con P=-y, Q=x sobre el cuadrado unidad  (Cálculo IV)",
        "calculo4_green",
        {"P": "-y", "Q": "x", "x_inferior": "0", "x_superior": "1",
         "y_inferior": "0", "y_superior": "1"},
    ),
    "verificar": (
        "el alumno respondio x*exp(x) - exp(x) + C: es correcto?  (tutor)",
        "verificar_respuesta",
        {"respuesta_alumno": "x*exp(x) - exp(x) + C", "expresion": "x*exp(x)"},
    ),
}


def _bonito(d, sangria=0):
    """Imprime un dict de tool como texto legible."""
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)):
                print("  " * sangria + "{}:".format(k))
                _bonito(v, sangria + 1)
            else:
                texto = str(v)
                if len(texto) > 150:
                    texto = texto[:150] + "..."
                print("  " * sangria + "{}: {}".format(k, texto))
    elif isinstance(d, list):
        for i, v in enumerate(d):
            print("  " * sangria + "[{}]".format(i))
            _bonito(v, sangria + 1)
    else:
        print("  " * sangria + str(d))


async def main() -> int:
    elegidos = sys.argv[1:] or list(EJERCICIOS)
    desconocidos = [k for k in elegidos if k not in EJERCICIOS]
    if desconocidos:
        print("Ejercicios desconocidos: {}".format(", ".join(desconocidos)))
        print("Disponibles: {}".format(", ".join(EJERCICIOS)))
        return 2

    print("=" * 74)
    print("CLIENTE MCP REAL -- conectando con server.py por stdio")
    print("=" * 74)

    parametros = StdioServerParameters(
        command=sys.executable,
        args=[str(APP_DIR / "server.py")],
        env=None,
    )
    async with stdio_client(parametros) as (lectura, escritura):
        async with ClientSession(lectura, escritura) as sesion:
            await sesion.initialize()

            info = sesion.initialize_result
            print("\n[1] Servidor: {} {}".format(
                info.server_info.name, info.server_info.version))

            herramientas = (await sesion.list_tools()).tools
            print("[2] tools announcements por el protocolo: {}".format(
                len(herramientas)))

            for clave in elegidos:
                etiqueta, tool, args = EJERCICIOS[clave]
                print("\n" + "-" * 74)
                print("EJERCICIO [{}]: {}".format(clave, etiqueta))
                print("  -> tool: {}".format(tool))
                try:
                    resultado = await sesion.call_tool(tool, args)
                except Exception as exc:
                    print("  ERROR: {}: {}".format(type(exc).__name__, exc))
                    continue
                if getattr(resultado, "is_error", False):
                    print("  la tool devolvio error")
                    for bloque in (resultado.content or []):
                        print("  " + str(getattr(bloque, "text", bloque))[:300])
                    continue
                datos = resultado.structured_content
                if datos is None:
                    for bloque in (resultado.content or []):
                        try:
                            datos = json.loads(bloque.text)
                            break
                        except Exception:
                            continue
                print("  respuesta:")
                _bonito(datos)

    print("\n" + "=" * 74)
    print("OK: {} ejercicios resueltos a traves del protocolo MCP".format(
        len(elegidos)))
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
