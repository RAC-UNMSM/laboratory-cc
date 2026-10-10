"""Verificacion manual del servidor (no forma parte de la entrega).

Corre el servidor de verdad: importa el modulo, lista tools y prompts por la
API real del SDK, y llama a cada tool base para comprobar que devuelve un dict
con "estado" y que el resultado es el matematicamente correcto.

Es lo que hace falta para cazar los bugs que NO aparecen al importar -- que
son los caros, porque en Docker aparecen como un contenedor que muere.

    python _smoke.py
"""

import asyncio
import json

import server

# (tool, argumentos, "correcta" esperado o None si no aplica)
CASOS = [
    ("calcular_derivada", {"expresion": "x**3*sin(x)"}, None),
    ("calcular_derivada", {"expresion": "x**2 + 3*x", "orden": 2}, None),
    ("calcular_integral", {"expresion": "x*exp(x)"}, None),
    ("calcular_integral",
     {"expresion": "x**2", "limite_inferior": "0", "limite_superior": "1"}, None),
    ("calcular_gradiente",
     {"expresion": "x**2*y+z**3", "variables": ["x", "y", "z"]}, None),
    # Antiderivadas: con "+C" es CORRECTA, sin el termino x tambien, y con un
    # termino de x faltando es INCORRECTA. (La C es la trampa clasica.)
    ("verificar_respuesta",
     {"respuesta_alumno": "x*exp(x) - exp(x) + C", "expresion": "x*exp(x)"}, True),
    ("verificar_respuesta",
     {"respuesta_alumno": "exp(x)*(x - 1)", "expresion": "x*exp(x)"}, True),
    ("verificar_respuesta",
     {"respuesta_alumno": "x*exp(x) + C", "expresion": "x*exp(x)"}, False),
    # Valores exactos: aqui la diferencia tiene que ser cero, la C si cuenta.
    ("verificar_respuesta", {"respuesta_alumno": "2", "referencia": "2"}, True),
    ("verificar_respuesta", {"respuesta_alumno": "3", "referencia": "2"}, False),
    ("estado_del_servidor", {}, None),
]


def extraer(resultado) -> dict:
    """Saca el dict de la tool de un CallToolResult del SDK v2.

    En la v2 `call_tool` NO devuelve el dict de la tool sino un
    CallToolResult: el dict va en `structured_content` y el texto JSON en
    `content`. Esta funcion existe porque el error tipico al probar un server
    MCP a mano es asumir que vuelve el dict.
    """
    datos = getattr(resultado, "structured_content", None)
    if isinstance(datos, dict):
        return datos
    for bloque in (getattr(resultado, "content", None) or []):
        try:
            posible = json.loads(bloque.text)
        except Exception:
            continue
        if isinstance(posible, dict):
            return posible
    raise TypeError(f"no se pudo extraer el dict de {type(resultado).__name__}")


async def main() -> int:
    print("=" * 72)
    print("SMOKE TEST -- servidor MCP-Calculo (Grupo 02)")
    print("=" * 72)

    tools = await server.mcp.list_tools()
    print(f"\n[1] tools registradas: {len(tools)}")
    for t in tools:
        print(f"    - {t.name}")

    prompts = await server.mcp.list_prompts()
    print(f"\n[2] prompts: {len(prompts)}")
    for p in prompts:
        print(f"    - {p.name}")

    print("\n[3] llamada a cada tool base:")
    fallos = 0
    for nombre, args, correcta_esperada in CASOS:
        try:
            datos = extraer(await server.mcp.call_tool(nombre, args))
        except Exception as exc:
            fallos += 1
            print(f"    XX {nombre}({list(args)}) -> {type(exc).__name__}: {exc}")
            continue

        estado = datos.get("estado")
        if estado not in ("exito", "parcial"):
            fallos += 1
            marca = "XX"
        else:
            marca = "ok"

        if correcta_esperada is not None and datos.get("correcta") is not correcta_esperada:
            fallos += 1
            marca = "XX"

        resumen = json.dumps(datos, ensure_ascii=False, default=str)
        if len(resumen) > 140:
            resumen = resumen[:140] + "..."
        print(f"    {marca} {nombre}({', '.join(args) or 'sin args'})")
        print(f"       {resumen}")

    print("\n" + "=" * 72)
    print(f"FALLOS: {fallos} / {len(CASOS)}")
    print("=" * 72)
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
