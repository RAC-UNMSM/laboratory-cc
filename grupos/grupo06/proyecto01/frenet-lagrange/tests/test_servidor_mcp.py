"""Prueba de punta a punta: cliente MCP oficial ⇄ server.py por STDIO."""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from agente import esquema_portable
from conftest import RAIZ


def _datos(res):
    texto = res.content[0].text if res.content else ""
    assert not res.isError, f"La herramienta devolvió un error: {texto[:500]}"
    return res.structuredContent or json.loads(texto)


async def _sesion_completa(tmp):
    env = {**os.environ, "MCP_MATH_RESULTADOS": str(tmp), "MCP_MATH_LOG": "WARNING"}
    params = StdioServerParameters(command=sys.executable, args=[str(RAIZ / "server.py")], env=env, cwd=str(RAIZ))
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        nombres = {t.name for t in (await s.list_tools()).tools}
        assert {"diagnosticar_problema", "optimizar_con_restricciones", "analizar_puntos_criticos",
                "analizar_curva_frenet", "listar_resultados", "obtener_resultado"} <= nombres

        d = _datos(await s.call_tool("diagnosticar_problema",
                                     {"solicitud": {"enunciado": "maximiza x*y sujeto a x^2 + y^2 = 8"}}))
        assert d["herramienta"] == "optimizar_con_restricciones"
        r = _datos(await s.call_tool(d["herramienta"], {"solicitud": d["argumentos_sugeridos"]}))
        assert r["ok"] and len(r["resultado"]["puntos_criticos"]) == 4
        assert os.path.exists(r["archivos"]["html"])

        r = await s.call_tool("analizar_curva_frenet", {"solicitud": {"curva": ["t", "2t", "3t"]}})
        assert r.isError and "CURVATURA_CERO" in r.content[0].text           # capa 2

        r = await s.call_tool("analizar_puntos_criticos", {"solicitud": {"funcion": "x^^2"}})
        assert r.isError and "No se pudo interpretar" in r.content[0].text   # capa 1

        lista = _datos(await s.call_tool("listar_resultados", {}))
        assert lista["resultados"][0]["metodo"] == "lagrange"
        tools = (await s.list_tools()).tools
        assert all("$ref" not in json.dumps(esquema_portable(t.inputSchema)) for t in tools)


def test_trabajador_directo(tmp_path):
    """El proceso de cálculo responde por sus propias tuberías (sin pasar por MCP)."""
    import subprocess
    pedido = json.dumps({"metodo": "frenet", "solicitud": {"curva": ["cos t", "sin t", "t"]}, "carpeta": str(tmp_path)})
    r = subprocess.run([sys.executable, str(RAIZ / "core" / "trabajador.py")], input=(pedido + "\n").encode(),
                       capture_output=True, timeout=120)
    lineas = r.stdout.decode().splitlines()
    assert lineas[0] == '{"listo": true}'
    assert json.loads(lineas[1])["ok"]


def test_servidor_stdio(tmp_path):
    asyncio.run(_sesion_completa(tmp_path))
