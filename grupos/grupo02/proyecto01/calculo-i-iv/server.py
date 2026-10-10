"""Orquestador MCP: validación de esquema, aislamiento y presentación."""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ImageContent, TextContent, ToolAnnotations
from models import Problem, Text, Var
from runtime import execute
from storage import upload
from tutor import LESSONS, lesson
from validacion import EntradaError

mcp = MCPServer(
    "grupo02-calculo-i-iv",
    version="1.0.0",
    instructions="Herramientas simbólicas de Cálculo I–IV. Consulte el catálogo y respete los estados no_resuelto y las hipótesis documentadas.",
)
READ = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
SKILLS = Path(__file__).parent / "skills"


@mcp.tool(annotations=READ)
async def resolver(
    problema: Problem, modo: Literal["examen", "paso_a_paso"] = "examen"
) -> dict[str, Any]:
    """Resuelve un problema estructurado de Cálculo I–IV. Use el esquema discriminado por operacion.

    Ejemplo: problema={"operacion":"derivada","expresion":"sin(x**2)"}.
    Potencias ** o ^, producto explícito 2*x, constantes pi/E; oo solo en límites.
    Integral múltiple: limites de dentro hacia fuera; cada frontera usa variables exteriores.
    Examen entrega resultado y condiciones; paso_a_paso añade etapas del motor, sin inventar una demostración.
    Green/Stokes/Gauss calculan un lado del teorema; requieren verificar sus hipótesis por separado.
    """
    return await execute("resolver", {"problema": problema.model_dump(), "modo": modo})


@mcp.tool(annotations=READ)
def catalogo() -> dict[str, Any]:
    """Lista temas del tutor, sintaxis y operaciones disponibles, sin modificar estado."""
    from engine import MODULES

    return {
        "operaciones": list(MODULES),
        "temas": list(LESSONS),
        "sintaxis": "x,y,z,t,u,v; + - * / **; sin cos tan asin acos atan sinh cosh tanh exp log sqrt Abs; pi E; oo en límites",
        "limites": {
            "caracteres_expresion": 512,
            "nodos_ast": 128,
            "segundos_solicitud": 20,
            "calculos_simultaneos": 1,
        },
        "dominio": "Variables reales. El cliente debe conservar restricciones del enunciado.",
    }


@mcp.tool(annotations=READ)
def leccion(
    tema: Text, nivel: Literal["desde_cero", "avanzado"] = "desde_cero"
) -> dict[str, Any]:
    """Teoría, ejemplo y ejercicio sin solución revelada; tema de catalogo, p.ej. derivadas o stokes.

    El cliente conserva el progreso del estudiante; el servidor no almacena sesiones educativas.
    """
    try:
        return lesson(tema, nivel)
    except EntradaError as exc:
        return {"estado": "error", "codigo": "entrada", "mensaje": str(exc)}


@mcp.tool(annotations=READ)
async def verificar_respuesta(tema: Text, respuesta: Text) -> dict[str, Any]:
    """Verifica la respuesta al ejercicio fijo de una lección, p.ej. derivadas, 3*x**2.

    Para primitivas omita +C; se acepta una constante numérica aditiva. No acepta pruebas en prosa.
    Devuelve correcta=null si no puede certificar equivalencia; no adivina por muestreo.
    """
    return await execute("verificar", {"tema": tema, "respuesta": respuesta})


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
    structured_output=False,
)
async def graficar(
    expresion: Text, inferior: Text, superior: Text, variable_nombre: Var = "x"
) -> list[TextContent | ImageContent]:
    """Grafica una función real continua en un intervalo finito. Ejemplo: x**2, -2, 2.

    Devuelve PNG en MCP y, si SeaweedFS está configurado, enlace público. La imagen se publica
    en el almacenamiento del laboratorio; no envíe información confidencial para graficar.
    """
    out = await execute(
        "grafica",
        {
            "expresion": expresion,
            "inferior": inferior,
            "superior": superior,
            "variable_nombre": variable_nombre,
        },
    )
    data = out.pop("png_base64", None)
    if data is None:
        return [TextContent(type="text", text=json.dumps(out, ensure_ascii=False))]
    url = await upload(base64.b64decode(data))
    out["imagen_url"] = url
    if url is None:
        out.setdefault("observaciones", []).append(
            "Sin enlace público; imagen incluida en la respuesta MCP."
        )
    return [
        TextContent(type="text", text=json.dumps(out, ensure_ascii=False)),
        ImageContent(type="image", data=data, mimeType="image/png"),
    ]


@mcp.resource("calculo://guia")
def guia() -> str:
    """Contrato resumido y límites del motor."""
    return (Path(__file__).parent / "docs" / "API.md").read_text(encoding="utf-8")


@mcp.prompt()
def resolver_examen() -> str:
    """Instrucciones de resolución formal con resultados verificados."""
    return (SKILLS / "skill_resolver_examen.md").read_text(encoding="utf-8")


@mcp.prompt()
def resolver_paso_a_paso() -> str:
    """Instrucciones para explicar cálculos sin inventar pasos del CAS."""
    return (SKILLS / "skill_paso_a_paso.md").read_text(encoding="utf-8")


@mcp.prompt()
def tutor_interactivo() -> str:
    """Contexto educativo separado, con verificación de ejercicios."""
    return (SKILLS / "skill_tutor_interactivo.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    domain = os.getenv("LAB_DOMAIN", "rac-unmsm.vekthos.org")
    container = os.getenv("LAB_CONTAINER_NAME", "lab-grupo02_proyecto01_calculo-i-iv")
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            domain,
            domain + ":443",
            container + ":8000",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "https://" + domain,
        ],
    )
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
        stateless_http=True,
        json_response=True,
        max_request_body_size=65536,
        transport_security=security,
    )
