"""Pruebas de punta a punta con el cliente MCP oficial.

1) streamable-http (el modo del laboratorio): server.py en un puerto libre + SeaweedFS SIMULADO.
   Se verifica qué objetos llegaron al "S3", las URLs públicas en Markdown, el bloque Image,
   las dos capas de validación, el listado sin índice, el reporte combinado y la concurrencia.
2) STDIO (Claude Desktop / agente.py en la PC) con almacenamiento local.
"""
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from agente import esquema_portable
from conftest import RAIZ
from s3_simulado import SeaweedSimulado

BUCKET = "frenet-lagrange-imgs"
PUBLICA = "https://rac-unmsm.vekthos.org/img/frenet-lagrange"
HERRAMIENTAS = {"diagnosticar_problema", "optimizar_con_restricciones", "analizar_puntos_criticos",
                "analizar_curva_frenet", "listar_resultados", "obtener_resultado", "combinar_reportes"}


def _datos(res):
    texto = next((c.text for c in res.content if c.type == "text"), "")
    assert not res.isError, f"La herramienta devolvió un error: {texto[:500]}"
    return res.structuredContent or json.loads(texto)


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor_http():
    """server.py real por streamable-http, conectado a un SeaweedFS simulado."""
    with SeaweedSimulado() as s3:                     # sin bucket: el servidor debe crearlo al arrancar
        puerto = _puerto_libre()
        env = {**os.environ, "MCP_TRANSPORT": "streamable-http", "MCP_HOST": "127.0.0.1", "MCP_PORT": str(puerto),
               "MCP_MATH_STORAGE": "s3", "SEAWEEDFS_S3_URL": s3.url, "IMG_BUCKET": BUCKET,
               "PUBLIC_IMG_BASE_URL": PUBLICA, "MCP_MATH_WORKERS": "2", "MCP_MATH_LOG": "WARNING",
               "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"}
        proc = subprocess.Popen([sys.executable, str(RAIZ / "server.py")], env=env, cwd=str(RAIZ),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{puerto}"
        abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(120):
            try:
                with abridor.open(base + "/salud", timeout=2) as r:
                    salud = json.loads(r.read())
                break
            except OSError:
                time.sleep(0.5)
        else:
            proc.kill()
            pytest.fail("el servidor HTTP no arrancó")
        try:
            yield {"url": base + "/mcp", "s3": s3, "salud": salud}
        finally:
            proc.terminate()
            proc.wait(timeout=10)


def test_salud_y_nombre(servidor_http):
    assert servidor_http["salud"]["servidor"] == "grupo06-frenet-lagrange"
    assert servidor_http["salud"]["transporte"] == "streamable-http"
    assert f"/{BUCKET}/" in servidor_http["s3"].puts()              # ensure_bucket() al arrancar


async def _flujo_http(url, s3):
    async with streamable_http_client(url) as (r, w, _), ClientSession(r, w) as s:
        info = await s.initialize()
        assert info.serverInfo.name == "grupo06-frenet-lagrange"
        tools = (await s.list_tools()).tools
        assert HERRAMIENTAS <= {t.name for t in tools}
        assert all("$ref" not in json.dumps(esquema_portable(t.inputSchema)) for t in tools)

        d = _datos(await s.call_tool("diagnosticar_problema",
                                     {"solicitud": {"enunciado": "maximiza x*y sujeto a x^2 + y^2 = 8"}}))
        assert d["herramienta"] == "optimizar_con_restricciones"
        res = await s.call_tool(d["herramienta"], {"solicitud": d["argumentos_sugeridos"]})
        r = _datos(res)
        id_ = r["id_resultado"]
        assert r["ok"] and len(r["resultado"]["puntos_criticos"]) == 4

        # artefactos en SeaweedFS bajo grupo06/<id>/ …
        for nombre in ("reporte.html", "grafico.png", "resultado.json", "entrada.json", "meta.json"):
            assert (BUCKET, f"grupo06/{id_}/{nombre}") in s3.objetos, nombre
        assert not any("indice" in k for k in s3.claves())
        # … y URLs públicas en Markdown (texto) + bloque Image de respaldo
        url_html = f"{PUBLICA}/grupo06/{id_}/reporte.html"
        assert r["archivos"]["html"] == url_html
        assert f"![Reporte de cálculo]({url_html})" in r["markdown"]
        assert f"({PUBLICA}/grupo06/{id_}/grafico.png)" in r["markdown"]
        assert res.content[0].type == "text" and url_html in res.content[0].text
        imagenes = [c for c in res.content if c.type == "image"]
        assert len(imagenes) == 1 and imagenes[0].mimeType == "image/png"
        assert base64.b64decode(imagenes[0].data)[:8] == b"\x89PNG\r\n\x1a\n"

        # capa 2 (verificador) y capa 1 (Pydantic)
        e = await s.call_tool("analizar_curva_frenet", {"solicitud": {"curva": ["t", "2t", "3t"]}})
        assert e.isError and "CURVATURA_CERO" in e.content[0].text
        e = await s.call_tool("analizar_puntos_criticos", {"solicitud": {"funcion": "x^^2"}})
        assert e.isError and "No se pudo interpretar" in e.content[0].text

        # concurrencia: 4 usuarios a la vez → ids distintos, cada uno en su prefijo
        async def usuario(sol):
            async with streamable_http_client(url) as (r2, w2, _), ClientSession(r2, w2) as s2:
                await s2.initialize()
                return _datos(await s2.call_tool("analizar_curva_frenet",
                                                 {"solicitud": {**sol, "salida": {"incluir_imagen": False}}}))
        varios = await asyncio.gather(*[usuario({"curva": ["cos t", "sin t", f"{k}t"]}) for k in (1, 2, 3, 4)])
        ids = [v["id_resultado"] for v in varios]
        assert len(set(ids)) == 4
        assert all((BUCKET, f"grupo06/{i}/meta.json") in s3.objetos for i in ids)

        # listado sin índice + obtener + combinado
        lista = _datos(await s.call_tool("listar_resultados", {"limite": 10}))["resultados"]
        assert {x["id"] for x in lista} >= set(ids) | {id_}
        o = _datos(await s.call_tool("obtener_resultado", {"solicitud": {"id_resultado": id_}}))
        assert o["archivos"]["html"] == url_html and url_html in o["markdown"]
        c = _datos(await s.call_tool("combinar_reportes", {"solicitud": {"ids": [id_, ids[0]], "titulo": "Prueba"}}))
        assert c["archivos"]["html"] == f"{PUBLICA}/grupo06/{c['id_lote']}/reporte_combinado.html"
        assert (BUCKET, f"grupo06/{c['id_lote']}/reporte_combinado.html") in s3.objetos
        e = await s.call_tool("combinar_reportes", {"solicitud": {"ids": ["lagrange-20000101-000000-abcdef12"]}})
        assert e.isError and "NO_ENCONTRADO" in e.content[0].text


def test_servidor_http_con_seaweedfs_simulado(servidor_http):
    asyncio.run(_flujo_http(servidor_http["url"], servidor_http["s3"]))


def test_trabajador_directo(tmp_path):
    """El proceso de cálculo responde por sus propias tuberías (sin pasar por MCP)."""
    pedido = json.dumps({"metodo": "frenet", "solicitud": {"curva": ["cos t", "sin t", "t"]}, "carpeta": str(tmp_path)})
    r = subprocess.run([sys.executable, str(RAIZ / "core" / "trabajador.py")], input=(pedido + "\n").encode(),
                       capture_output=True, timeout=120)
    lineas = r.stdout.decode().splitlines()
    assert lineas[0] == '{"listo": true}'
    assert json.loads(lineas[1])["ok"]


async def _flujo_stdio(tmp):
    env = {**os.environ, "MCP_TRANSPORT": "stdio", "MCP_MATH_STORAGE": "local",
           "MCP_MATH_RESULTADOS": str(tmp), "MCP_MATH_LOG": "WARNING"}
    params = StdioServerParameters(command=sys.executable, args=[str(RAIZ / "server.py"), "--stdio"], env=env,
                                   cwd=str(RAIZ))
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        d = _datos(await s.call_tool("analizar_puntos_criticos", {"solicitud": {"funcion": "x^3 + y^3 - 3xy"}}))
        assert len(d["resultado"]["puntos_criticos"]) == 2              # '3xy' = 3·x·y
        assert d["archivos"]["html"].startswith("file://")
        assert (tmp / "grupo06" / d["id_resultado"] / "reporte.html").is_file()


def test_servidor_stdio_local(tmp_path):
    asyncio.run(_flujo_stdio(tmp_path))
