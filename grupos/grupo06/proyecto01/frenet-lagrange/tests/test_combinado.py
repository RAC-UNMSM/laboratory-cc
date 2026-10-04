"""Reporte combinado: varios ejercicios en un solo HTML, en una carpeta aparte."""
import asyncio
import json
import os
import re
import sys

import pytest

from core.combinado import Combinador, ErrorCombinado, ID_LOTE
from core.motor import ejecutar
from storage import Almacen

PROBLEMAS = [
    ("lagrange", {"funcion": "3x + 4y", "restricciones": ["x^2 + y^2 = 25"]}),
    ("hessiana", {"funcion": "x^2 + x*y + y^2 - 3x"}),
    ("frenet", {"curva": ["cos t", "sin t", "t"]}),
]


def _resolver(almacen, metodo, solicitud):
    id_, carpeta = almacen.nueva_carpeta(metodo)
    r = ejecutar(metodo, solicitud, str(carpeta))
    assert r["ok"], r
    almacen.guardar(id_, metodo, f"prueba {metodo}", r["solicitud"], r["resultado"], r["resumen"], r["archivos"])
    return id_


@pytest.fixture(scope="module")
def almacen_con_tres(tmp_path_factory):
    base = tmp_path_factory.mktemp("res")
    a = Almacen(base / "resultados")
    ids = [_resolver(a, m, s) for m, s in PROBLEMAS]
    return a, ids, base


def _ejercicios(html):
    m = re.search(r"const EJ = (\[.*?\]), TITULO = ", html, re.S)
    assert m, "no se encontró el arreglo de ejercicios en el HTML"
    return json.loads(m.group(1))


def test_combinado_tres_metodos(almacen_con_tres):
    a, ids, base = almacen_con_tres
    c = Combinador(a, base / "combinados")
    r = c.combinar(ids, "Práctica <3> & 'prueba'", ["$f = 3x+4y$", "Hessiana de f", "Hélice"])
    assert r["ok"] and r["n_ejercicios"] == 3 and ID_LOTE.match(r["id_lote"])
    # carpeta APARTE de resultados/, con el HTML y lote.json
    carpeta = base / "combinados" / r["id_lote"]
    assert (carpeta / "reporte_combinado.html").is_file() and (carpeta / "lote.json").is_file()
    assert not str(carpeta).startswith(str(a.base))
    # los reportes individuales siguen intactos
    for id_ in ids:
        assert (a.base / id_ / "reporte.html").is_file()
        assert "postMessage" not in (a.base / id_ / "reporte.html").read_text(encoding="utf-8")

    html = (carpeta / "reporte_combinado.html").read_text(encoding="utf-8")
    assert html.lower().startswith("<!doctype html>")
    assert not re.search(r"\{\{\s*\w+|\{%", html)                      # Jinja2 sin restos
    assert "Práctica &lt;3&gt; &amp; &#39;prueba&#39;" in html            # título escapado
    script = html.split("const EJ = ", 1)[1]
    assert script.count("</script>") == 1                              # solo el cierre real
    ej = _ejercicios(html)
    assert [e["id"] for e in ej] == ids and [e["n"] for e in ej] == [1, 2, 3]
    assert [e["metodo"] for e in ej] == ["lagrange", "hessiana", "frenet"]
    # cada reporte copiado conserva sus 5 pestañas y lleva el pie de navegación
    for e in ej:
        for pestaña in ("resumen", "proc", "g3d", "g2d", "json"):
            assert f'data-tab="{pestaña}"' in e["html"]
        assert "postMessage" in e["html"] and "Ejercicio" in e["html"]
    assert "Siguiente ejercicio (2)" in ej[0]["html"] and "volver al índice" in ej[2]["html"]

    lote = json.loads((carpeta / "lote.json").read_text(encoding="utf-8"))
    assert [x["id"] for x in lote["ejercicios"]] == ids


def test_combinado_errores(almacen_con_tres):
    a, ids, base = almacen_con_tres
    c = Combinador(a, base / "combinados")
    with pytest.raises(ErrorCombinado) as e:
        c.combinar([ids[0], "hessiana-20000101-000000-abcdef"])
    assert e.value.codigo == "NO_ENCONTRADO" and "hessiana-20000101-000000-abcdef" in e.value.mensaje


def test_validacion_combinar():
    from pydantic import ValidationError
    from core.validacion import SolicitudCombinar
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["frenet-20261003-184624-5794a3", "frenet-20261003-184624-5794a3"])
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["../../etc"])
    with pytest.raises(ValidationError):
        SolicitudCombinar(ids=["frenet-20261003-184624-5794a3"], enunciados=["a", "b"])


async def _por_mcp(tmp):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from conftest import RAIZ
    env = {**os.environ, "MCP_MATH_RESULTADOS": str(tmp / "resultados"),
           "MCP_MATH_COMBINADOS": str(tmp / "combinados"), "MCP_MATH_LOG": "WARNING"}
    params = StdioServerParameters(command=sys.executable, args=[str(RAIZ / "server.py")], env=env, cwd=str(RAIZ))
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        assert "combinar_reportes" in {t.name for t in (await s.list_tools()).tools}
        ids = []
        for herr, sol in (("analizar_puntos_criticos", {"funcion": "x^3 + y^3 - 3x*y"}),
                          ("analizar_curva_frenet", {"curva": ["t", "t^2", "t^3"], "t0": "1"})):
            res = await s.call_tool(herr, {"solicitud": sol})
            assert not res.isError
            ids.append((res.structuredContent or json.loads(res.content[0].text))["id_resultado"])
        res = await s.call_tool("combinar_reportes", {"solicitud": {"ids": ids, "titulo": "Prueba MCP"}})
        assert not res.isError, res.content[0].text
        d = res.structuredContent or json.loads(res.content[0].text)
        assert d["n_ejercicios"] == 2 and os.path.isfile(d["archivos"]["html"])
        assert d["archivos"]["html"].startswith(str(tmp / "combinados"))
        assert len([p for p in (tmp / "resultados").iterdir() if p.is_dir()]) == 2   # individuales intactos
        res = await s.call_tool("combinar_reportes", {"solicitud": {"ids": ["lagrange-20000101-000000-abcdef"]}})
        assert res.isError and "NO_ENCONTRADO" in res.content[0].text


def test_combinar_por_mcp(tmp_path):
    asyncio.run(_por_mcp(tmp_path))
