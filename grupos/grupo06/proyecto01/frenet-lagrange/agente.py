"""
agente.py — Agente de IA que usa el servidor MCP (cliente MCP + LLM intercambiable).

    Usuario ──texto──▶ LLM (DeepSeek / Gemini / Claude / OpenAI / Ollama)
                         │  decide qué herramienta usar (function calling)
                         ▼
                   cliente MCP ──STDIO──▶ server.py ──▶ SymPy exacto
                         ▲                                 │
                         └──────── resultado JSON ◀────────┘
                         │
                   LLM redacta la explicación final

El LLM NO calcula: solo elige la herramienta, le pasa los argumentos y explica la respuesta.
Toda la matemática la hace el servidor (exacta y verificada). Por eso se puede cambiar de LLM
sin tocar nada más: el agente es 100 % agnóstico.

Uso:
    python agente.py --simulado                        # sin API key: el ruteo lo hace core/diagnostico
    python agente.py --proveedor deepseek              # usa DEEPSEEK_API_KEY
    python agente.py --proveedor gemini --modelo <id>  # usa GEMINI_API_KEY
    python agente.py --proveedor claude --modelo <id>  # usa ANTHROPIC_API_KEY (endpoint compatible OpenAI)
    python agente.py --proveedor ollama --modelo <id>  # LLM local, sin internet
    python agente.py -p "curvatura de r(t)=(cos t, sin t, t) en t=0"   # una sola pregunta

Requiere además:  pip install -r requirements-agente.txt   (paquete 'openai', salvo en --simulado)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import webbrowser
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

RAIZ = Path(__file__).resolve().parent
MAX_RONDAS = 8
MAX_CARACTERES_HERRAMIENTA = 14000


# ════════════════════════════════════════════════════════════════════════════
# Proveedores (todos hablan el protocolo "chat completions" de OpenAI)
# ════════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class Proveedor:
    base_url: str | None
    env_clave: str | None
    env_modelo: str
    modelo_por_defecto: str | None = None

PROVEEDORES: dict[str, Proveedor] = {
    "deepseek": Proveedor("https://api.deepseek.com", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-chat"),
    "gemini": Proveedor("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "GEMINI_MODEL"),
    "claude": Proveedor("https://api.anthropic.com/v1/", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "openai": Proveedor(None, "OPENAI_API_KEY", "OPENAI_MODEL"),
    "ollama": Proveedor(os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"), None, "OLLAMA_MODEL"),
}


# ════════════════════════════════════════════════════════════════════════════
# JSON Schema de MCP → esquema de "function calling" aceptado por todos los proveedores
# ════════════════════════════════════════════════════════════════════════════
_CLAVES_OK = {"type", "description", "properties", "required", "items", "enum", "minItems", "maxItems",
              "minimum", "maximum"}


def esquema_portable(esquema: dict[str, Any]) -> dict[str, Any]:
    """Resuelve $ref/$defs, quita lo que algunos proveedores rechazan (additionalProperties,
    examples, title, prefixItems...) y aplana 'anyOf [X, null]' → X. Los valores por defecto se
    pasan a la descripción para no perder información."""
    defs = esquema.get("$defs", {})

    def conv(n: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in n:
            base = conv(defs[n["$ref"].split("/")[-1]])
            return {**base, **({"description": n["description"]} if "description" in n else {})}
        if "anyOf" in n:
            opciones = [o for o in n["anyOf"] if o.get("type") != "null"]
            base = conv(opciones[0]) if opciones else {"type": "string"}
            extra = {k: v for k, v in n.items() if k != "anyOf"}
            return conv({**base, **extra}) if extra else base
        out: dict[str, Any] = {}
        for k, v in n.items():
            if k == "properties":
                out[k] = {p: conv(s) for p, s in v.items()}
            elif k == "items" and isinstance(v, dict):
                out[k] = conv(v)
            elif k == "prefixItems":                       # tuplas (p. ej. rango [min, max])
                out["items"] = conv(v[0])
                out["minItems"] = out["maxItems"] = len(v)
            elif k == "additionalProperties" and isinstance(v, dict):   # dict[str, float] → objeto libre
                out.setdefault("description", "")
                out["description"] += f" (objeto: nombre → {v.get('type', 'valor')})"
            elif k in _CLAVES_OK:
                out[k] = v
        if "default" in n and n["default"] is not None:
            out["description"] = (out.get("description", "") + f" Por defecto: {json.dumps(n['default'])}.").strip()
        if out.get("type") == "object" and "properties" not in out:
            out["properties"] = {}
        return out

    return conv({k: v for k, v in esquema.items() if k != "$defs"})


def herramientas_openai(tools: list[Any]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description or "",
                                              "parameters": esquema_portable(t.inputSchema)}} for t in tools]


# ════════════════════════════════════════════════════════════════════════════
# Conexión con el servidor MCP
# ════════════════════════════════════════════════════════════════════════════
class ClienteMCP:
    """Conecta con el servidor MCP:
      • sin url → lo lanza como subproceso por STDIO (almacenamiento en carpeta local);
      • con url → se conecta por streamable-http a un servidor ya desplegado (p. ej. detrás de Caddy)."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url
        self._pila = AsyncExitStack()
        self.sesion: ClientSession | None = None
        self.instrucciones = ""
        self.tools: list[Any] = []

    async def __aenter__(self) -> "ClienteMCP":
        if self.url:
            from mcp.client.streamable_http import streamable_http_client
            lectura, escritura, _ = await self._pila.enter_async_context(streamable_http_client(self.url))
        else:
            entorno = {**os.environ, "MCP_TRANSPORT": "stdio",
                       "MCP_MATH_STORAGE": os.environ.get("MCP_MATH_STORAGE", "local"),
                       "MCP_MATH_LOG": os.environ.get("MCP_MATH_LOG", "WARNING")}
            params = StdioServerParameters(command=sys.executable, args=[str(RAIZ / "server.py"), "--stdio"],
                                           env=entorno, cwd=str(RAIZ))
            lectura, escritura = await self._pila.enter_async_context(stdio_client(params))
        self.sesion = await self._pila.enter_async_context(ClientSession(lectura, escritura))
        init = await self.sesion.initialize()
        self.instrucciones = init.instructions or ""
        self.tools = (await self.sesion.list_tools()).tools
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._pila.aclose()

    async def llamar(self, nombre: str, argumentos: dict[str, Any]) -> tuple[bool, dict[str, Any] | str]:
        """Devuelve (ok, datos). Si la herramienta falla, datos es el mensaje de error."""
        assert self.sesion is not None
        res = await self.sesion.call_tool(nombre, argumentos)
        texto = "\n".join(c.text for c in res.content if getattr(c, "type", "") == "text")
        if res.isError:
            return False, texto
        if res.structuredContent is not None:
            datos = res.structuredContent
            return True, datos.get("result", datos) if set(datos) == {"result"} else datos
        try:
            return True, json.loads(texto)
        except json.JSONDecodeError:
            return True, texto


# ════════════════════════════════════════════════════════════════════════════
# Presentación
# ════════════════════════════════════════════════════════════════════════════
def _gris(t: str) -> str:
    return f"\033[90m{t}\033[0m" if sys.stderr.isatty() else t


def _traza(t: str) -> None:
    print(_gris(t), file=sys.stderr)


def _explicar_error(texto: str) -> str:
    """Convierte el error JSON del servidor en una frase para la versión simulada."""
    try:
        e = json.loads(texto[texto.index("{"):])
        msg = f"No se puede aplicar el método: {e.get('mensaje', '')}"
        return msg + (f"\nSugerencia: {e['sugerencia']}" if e.get("sugerencia") else "")
    except (ValueError, json.JSONDecodeError):
        return "La solicitud no es válida:\n" + texto


def _abrir(ruta: str | None, abrir: bool) -> None:
    """Abre el reporte: acepta una URL pública (https://…, file://…) o una ruta local."""
    if ruta and abrir:
        webbrowser.open(ruta if "://" in ruta else Path(ruta).resolve().as_uri())


# ════════════════════════════════════════════════════════════════════════════
# Modo simulado: sin LLM. El ruteo semántico lo hace core/diagnostico vía MCP.
# ════════════════════════════════════════════════════════════════════════════
async def responder_simulado(cli: ClienteMCP, pregunta: str, abrir: bool) -> str:
    ok, d = await cli.llamar("diagnosticar_problema", {"solicitud": {"enunciado": pregunta}})
    if not ok or not isinstance(d, dict):
        return _explicar_error(str(d))
    _traza(f"  ↳ diagnosticar_problema → {d['metodo_recomendado']} (confianza {d['confianza']})")
    if not d["metodo_recomendado"]:
        return ("No reconozco un problema de Lagrange, Hessiana o Frenet en tu mensaje. Escribe, por ejemplo:\n"
                "  • maximiza x*y sujeto a x^2 + y^2 = 8\n  • puntos críticos de x^3 + y^3 - 3xy\n"
                "  • curvatura de r(t) = (cos t, sin t, t) en t = 0")
    args = d["argumentos_sugeridos"]
    requeridos = {"lagrange": ("funcion", "restricciones"), "hessiana": ("funcion",), "frenet": ("curva",)}
    if any(k not in args for k in requeridos[d["metodo_recomendado"]]):
        return (f"Parece un problema de {d['metodo_recomendado']}, pero me falta: " + ", ".join(d["faltantes"]) +
                ". Escríbelo con fórmulas, por ejemplo 'f(x,y) = ...' o 'r(t) = (..., ..., ...)'.")
    herramienta = d["herramienta"]
    _traza(f"  ↳ {herramienta}({json.dumps(args, ensure_ascii=False)})")
    ok, r = await cli.llamar(herramienta, {"solicitud": args})
    if not ok or not isinstance(r, dict):
        return _explicar_error(str(r))
    nombres = {"lagrange": "multiplicadores de Lagrange", "hessiana": "puntos críticos y matriz Hessiana",
               "frenet": "triedro de Frenet"}
    motivos = "; ".join(x.split("] ", 1)[-1] for x in d["razones"][:2])
    lineas = [f"Método aplicado: {nombres[r['metodo']]} (porque {motivos}).", ""]
    lineas += [f"  • {x}" for x in r["resumen"]]
    for a in r["verificacion_previa"].get("avisos", []):
        lineas.append(f"  ⚠ {a}")
    html = r["archivos"].get("html")
    if html:
        lineas += ["", f"Procedimiento completo y gráficos 3D: {html}"]
        if r["archivos"].get("png"):
            lineas.append(f"Gráfico (PNG): {r['archivos']['png']}")
        _abrir(html, abrir)
    lineas.append(f"(id del resultado: {r['id_resultado']})")
    return "\n".join(lineas)


# ════════════════════════════════════════════════════════════════════════════
# Modo LLM (function calling)
# ════════════════════════════════════════════════════════════════════════════
SISTEMA = """Eres el asistente matemático del Grupo 06 (UNMSM). Respondes en español, con claridad
pedagógica. Tienes herramientas MCP que hacen cálculo simbólico EXACTO: úsalas SIEMPRE para
calcular; nunca inventes ni redondees resultados. Si el enunciado es ambiguo, llama primero a
diagnosticar_problema. Si falta un dato imprescindible, pregúntalo. Al final explica el
procedimiento paso a paso con los valores exactos devueltos e indica la ruta del reporte HTML.
Si una herramienta devuelve un error de verificación, explica por qué el problema no tiene
sentido tal como está planteado y propone la corrección sugerida.

Guía del servidor:
"""


class AgenteLLM:
    def __init__(self, cli: ClienteMCP, proveedor: str, modelo: str | None, base_url: str | None,
                 clave_env: str | None, abrir: bool) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("Falta el paquete 'openai':  pip install -r requirements-agente.txt   (o usa --simulado)")
        p = PROVEEDORES[proveedor]
        self.modelo = modelo or os.environ.get(p.env_modelo) or p.modelo_por_defecto
        if not self.modelo:
            sys.exit(f"Indica el modelo con --modelo o la variable {p.env_modelo} (consulta el nombre exacto "
                     f"en la documentación de {proveedor}).")
        env = clave_env or p.env_clave
        clave = os.environ.get(env) if env else "ollama"
        if not clave:
            sys.exit(f"Falta la clave de API en la variable de entorno {env} (o usa --simulado).")
        self.llm = OpenAI(api_key=clave, base_url=base_url or p.base_url)
        self.cli, self.abrir = cli, abrir
        self.tools = herramientas_openai(cli.tools)
        self.mensajes: list[dict[str, Any]] = [{"role": "system", "content": SISTEMA + cli.instrucciones}]

    async def responder(self, pregunta: str) -> str:
        self.mensajes.append({"role": "user", "content": pregunta})
        for _ in range(MAX_RONDAS):
            resp = await asyncio.to_thread(self.llm.chat.completions.create, model=self.modelo,
                                           messages=self.mensajes, tools=self.tools, tool_choice="auto")
            msg = resp.choices[0].message
            llamadas = msg.tool_calls or []
            self.mensajes.append({"role": "assistant", "content": msg.content or "",
                                  **({"tool_calls": [{"id": c.id, "type": "function",
                                                      "function": {"name": c.function.name,
                                                                   "arguments": c.function.arguments}}
                                                     for c in llamadas]} if llamadas else {})})
            if not llamadas:
                return msg.content or ""
            for c in llamadas:
                try:
                    argumentos = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    argumentos = {}
                _traza(f"  ↳ {c.function.name}({json.dumps(argumentos, ensure_ascii=False)[:300]})")
                ok, datos = await self.cli.llamar(c.function.name, argumentos)
                if ok and isinstance(datos, dict):
                    _abrir(datos.get("archivos", {}).get("html"), self.abrir)
                contenido = datos if isinstance(datos, str) else json.dumps(datos, ensure_ascii=False)
                if not ok:
                    _traza("    ✗ " + contenido[:200])
                self.mensajes.append({"role": "tool", "tool_call_id": c.id,
                                      "content": contenido[:MAX_CARACTERES_HERRAMIENTA]})
        return "(Se alcanzó el máximo de pasos sin una respuesta final.)"


# ════════════════════════════════════════════════════════════════════════════
async def principal(a: argparse.Namespace) -> None:
    async with ClienteMCP(a.url) as cli:
        _traza(f"Conectado al servidor MCP · herramientas: {', '.join(t.name for t in cli.tools)}")
        if a.simulado:
            _traza("Modo simulado (sin LLM): el ruteo lo hace diagnosticar_problema.")

            async def responder(p: str) -> str:
                return await responder_simulado(cli, p, a.abrir)
        else:
            agente = AgenteLLM(cli, a.proveedor, a.modelo, a.base_url, a.clave_env, a.abrir)
            _traza(f"LLM: {a.proveedor} · modelo {agente.modelo}")
            responder = agente.responder

        if a.pregunta:
            print(await responder(" ".join(a.pregunta)))
            return
        print("Escribe tu problema (o 'salir'). Ejemplos:\n"
              "  maximiza x*y sujeto a x^2 + y^2 = 8\n  clasifica los puntos críticos de x^4 + y^4 - 4xy + 1\n"
              "  triedro de Frenet de r(t) = (cos t, sin t, t) en t = pi/4")
        while True:
            try:
                p = (await asyncio.to_thread(input, "\nTú › ")).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if p.lower() in {"salir", "exit", "quit"}:
                break
            if p:
                try:
                    print("\nAgente › " + await responder(p))
                except Exception as e:  # noqa: BLE001 — errores de red/API del proveedor
                    print(f"\nAgente › Error al consultar el LLM: {e}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="Agente IA (LLM + servidor MCP de cálculo exacto).")
    ap.add_argument("-p", "--pregunta", nargs="+", help="pregunta única (si no, modo conversación)")
    ap.add_argument("--simulado", action="store_true", help="sin LLM ni API key (ruteo por diagnóstico)")
    ap.add_argument("--proveedor", choices=sorted(PROVEEDORES), default=os.environ.get("AGENTE_PROVEEDOR", "deepseek"))
    ap.add_argument("--modelo", help="id del modelo del proveedor")
    ap.add_argument("--base-url", help="URL de una API compatible con OpenAI (sobrescribe la del proveedor)")
    ap.add_argument("--clave-env", help="nombre de la variable de entorno con la API key")
    ap.add_argument("--abrir", action="store_true", help="abrir el reporte HTML en el navegador")
    ap.add_argument("--url", default=os.environ.get("MCP_URL"),
                    help="servidor MCP desplegado (streamable-http), p. ej. "
                         "https://rac-unmsm.vekthos.org/grupo06/frenet-lagrange/mcp; sin esto se lanza server.py local")
    args = ap.parse_args()
    try:
        asyncio.run(principal(args))
    except KeyboardInterrupt:            # Ctrl + C: salir sin mostrar un traceback
        print("\nSesión terminada (Ctrl + C). Para salir normalmente escribe 'salir'.")


if __name__ == "__main__":
    main()
