"""Script de verificación de la arquitectura MCP.

No forma parte del servidor. Sirve para comprobar tres cosas:

1. Que las cinco tools están registradas en el servidor MCP.
2. Que llamar a una tool con entrada válida y módulo no implementado
   devuelve el contrato esperado (status = invalid_input).
3. Que llamar a una tool con entrada inválida también devuelve el contrato.
"""

import asyncio

from server import mcp, _ejecutar_metodo


def listar_tools():
    print("=== Tools registradas en el servidor MCP ===")
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        print(f"  - {t.name}: {t.description}")


def caso_modulo_ausente():
    print("\n=== Entrada válida, módulo aún no implementado ===")
    r = _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        ["x**2 + y**2 - 1", "x - y"],
        ["x", "y"],
        [1.0, 0.5],
        1e-8,
        100,
    )
    print(r)


def caso_entrada_invalida():
    print("\n=== Entrada inválida (tolerancia negativa) ===")
    r = _ejecutar_metodo(
        "newton_sistemas",
        "metodos.newton_sistemas",
        "newton_sistemas",
        ["x**2 + y**2 - 1", "x - y"],
        ["x", "y"],
        [1.0, 0.5],
        -1.0,
        100,
    )
    print(r)


if __name__ == "__main__":
    listar_tools()
    caso_modulo_ausente()
    caso_entrada_invalida()