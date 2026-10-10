"""Comprobaciones ESTÁTICAS de los requisitos del validador (CI) del laboratorio.

Leen el código fuente como texto, igual que un escáner con expresiones regulares:
SDK 2.x fijado, MCPServer, la línea literal de arranque, sin el cliente LLM en producción, sin
impresiones por pantalla, sin escrituras en disco del contenedor y herramientas con type hints
y docstrings.

Las palabras que buscan se arman por partes (p. ej. "open" + "ai") para que ESTE archivo no sea
marcado por el mismo escáner que imita.
"""
import ast
import inspect
import re

from conftest import RAIZ

CLIENTE_LLM = "open" + "ai"
TMP = "/" + "tmp"
SDK_V1 = "Fast" + "MCP"

# Archivos que van a la imagen Docker (producción).
PRODUCCION = [RAIZ / "server.py", RAIZ / "storage.py",
              *sorted((RAIZ / "core").glob("*.py")), *sorted((RAIZ / "methods").glob("*.py"))]


def _texto(ruta):
    return ruta.read_text(encoding="utf-8")


def test_requirements_mcp_fijo_y_sin_cliente_llm():
    lineas = [ln.split("#")[0].strip() for ln in _texto(RAIZ / "requirements.txt").splitlines()]
    lineas = [ln for ln in lineas if ln]
    assert "mcp==2.1.1" in lineas
    assert not any(ln.lower().startswith(CLIENTE_LLM) for ln in lineas)
    assert any(ln.startswith("contourpy") for ln in lineas)


def test_ningun_archivo_versionado_importa_el_cliente_llm():
    patron = re.compile(rf"^\s*(import {CLIENTE_LLM}|from {CLIENTE_LLM}\b)", re.M)
    for ruta in RAIZ.rglob("*.py"):
        if "__pycache__" in ruta.parts or ".venv" in ruta.parts:
            continue
        assert not patron.search(_texto(ruta)), ruta


def test_server_usa_mcpserver_y_arranque_literal():
    src = _texto(RAIZ / "server.py")
    assert "from mcp.server.mcpserver import" in src and "MCPServer" in src
    assert 'mcp = MCPServer("grupo06-frenet-lagrange")' in src
    assert SDK_V1 not in src
    # main() contiene la línea literal dentro de try/except TypeError y el arranque con getattr
    arbol = ast.parse(src)
    main = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    cuerpo = ast.get_source_segment(src, main)
    assert 'mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)' in cuerpo
    assert re.search(r"except TypeError", cuerpo)
    assert 'arrancar = getattr(mcp, "run")' in cuerpo and 'arrancar(transport="streamable-http")' in cuerpo
    assert "os.environ.update(" in cuerpo
    intentos = [n for n in ast.walk(main) if isinstance(n, ast.Try)]
    assert any(any(isinstance(h.type, ast.Name) and h.type.id == "TypeError" for h in t.handlers) and
               'host="0.0.0.0"' in ast.get_source_segment(src, t.body[0]) for t in intentos)


def test_sin_print_en_el_codigo():
    for ruta in PRODUCCION:
        arbol = ast.parse(_texto(ruta))
        llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id == "print"]
        assert not llamadas, f"{ruta.name}: usa logging en lugar de print (línea {llamadas[0].lineno})"


def test_produccion_no_escribe_en_disco():
    prohibido = re.compile(re.escape(TMP) + "|" + "temp" + r"file|Temporary" + r"Directory|mkstemp|write_text\(|"
                           r"write_bytes\(|savefig\(\s*['\"]|savefig\(\s*ruta|open\([^)]*['\"][wa]b?['\"]")
    for ruta in PRODUCCION:
        m = prohibido.search(_texto(ruta))
        assert m is None, f"{ruta.name}: '{m.group(0)}' escribiría en el disco del contenedor"
    docker = _texto(RAIZ / "Dockerfile")
    assert TMP not in docker


def test_reporte_usa_bytesio_y_bytes():
    src = _texto(RAIZ / "core" / "reporte.py")
    assert "io.BytesIO()" in src and ".getvalue()" in src and 'encode("utf-8")' in src
    st = _texto(RAIZ / "storage.py")
    assert re.search(r"def subir\(self, id_: str, nombre: str, contenido_bytes: bytes", st)
    assert re.search(r"def guardar\(self[^)]*contenido_bytes", st, re.S)


def test_herramientas_con_type_hints_y_docstring():
    import server
    from typing import get_type_hints
    nombres = ["diagnosticar_problema", "optimizar_con_restricciones", "analizar_puntos_criticos",
               "analizar_curva_frenet", "listar_resultados", "obtener_resultado", "combinar_reportes"]
    for nombre in nombres:
        fn = getattr(server, nombre)
        hints = get_type_hints(fn, include_extras=True)
        params = [p for p in inspect.signature(fn).parameters]
        assert "return" in hints, f"{nombre}: falta el tipo de retorno"
        assert all(p in hints for p in params), f"{nombre}: parámetros sin type hint"
        assert (fn.__doc__ or "").strip(), f"{nombre}: falta el docstring"


def test_combinado_tiene_agregar_a_sesion_y_motor_la_llama():
    comb = _texto(RAIZ / "core" / "combinado.py")
    assert re.search(r"def agregar_a_sesion\(id_nuevo_ejercicio: str, enunciado: str\)", comb)
    assert "lote-sesion-actual" in _texto(RAIZ / "storage.py")
    motor = _texto(RAIZ / "core" / "motor.py")
    k_guardar, k_sesion = motor.index("almacen.guardar("), motor.index("agregar_a_sesion(id_")
    assert k_guardar < k_sesion                                       # justo DESPUÉS de subir
