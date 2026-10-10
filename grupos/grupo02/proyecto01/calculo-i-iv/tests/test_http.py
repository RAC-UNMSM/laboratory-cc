"""Integración real con el mismo comando de arranque del contenedor."""

import asyncio
import socket
import subprocess
import sys
from pathlib import Path

import httpx
from mcp import Client


async def test_streamable_http(monkeypatch):
    # Las pruebas solo hablan con loopback; no heredar proxies externos.
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        assert probe.connect_ex(("127.0.0.1", 8000)) != 0, (
            "Puerto 8000 ocupado; detenga el servidor antes de correr tests."
        )
    process = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            assert process.poll() is None, "El servidor terminó durante el arranque."
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", 8000)) == 0:
                    break
            await asyncio.sleep(0.05)
        else:
            raise AssertionError("El servidor no arrancó en 5 segundos.")
        async with Client("http://127.0.0.1:8000/mcp") as client:
            listed = await client.list_tools()
            assert len(listed.tools) == 5
            answer = await client.call_tool(
                "resolver", {"problema": {"operacion": "derivada", "expresion": "x**3"}}
            )
            assert (
                not answer.is_error and answer.structured_content["exacto"] == "3*x**2"
            )
            assert (await client.list_prompts()).prompts
            assert (await client.read_resource("calculo://guia")).contents
            bad = await client.call_tool(
                "resolver",
                {
                    "problema": {
                        "operacion": "derivada",
                        "expresion": '__import__("os")',
                    }
                },
            )
            assert bad.structured_content["codigo"] == "entrada"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/mcp",
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "legacy-check", "version": "1"},
                    },
                },
            )
            assert response.status_code == 200
            assert (
                response.json()["result"]["serverInfo"]["name"]
                == "grupo02-calculo-i-iv"
            )
            response = await client.post(
                "http://127.0.0.1:8000/mcp",
                headers={"host": "evil.invalid", "content-type": "application/json"},
                content="{}",
            )
            assert response.status_code == 421
            response = await client.post(
                "http://127.0.0.1:8000/mcp",
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                },
                content="x" * 70000,
            )
            assert response.status_code == 413
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
