"""Servidor MCP del Grupo 02 -- plataforma de Calculo I a IV.

Este archivo es el ORQUESTADOR: no contiene logica matematica propia (salvo las
cuatro tools base, que existen para que el servidor sirva aunque `tools/` este
vacio). Su trabajo es poner en contacto tres cosas:

  1. Los MODULOS DE CALCULO en `tools/` -- uno por area, uno por integrante:
     calculo1.py (Calculo I), calculo2.py (Calculo II), calculo3.py (Calculo
     III), calculo4.py (Calculo IV). Se cargan de forma DINAMICA: el servidor
     registra como tool MCP toda funcion publica definida en esos archivos.
     Asi el servidor funciona desde el primer dia y crece solo a medida que
     cada integrante sube su modulo, sin que nadie tenga que tocar este archivo.
  2. Los CONTEXTOS DE COMPORTAMIENTO en `skill/` (Markdown), expuestos como
     prompts MCP: modo examen, modo paso a paso y modo tutor.
  3. Las tools base (resolucion en SymPy + verificacion de respuestas del
     alumno), que ya funcionan sin ningun modulo de `tools/`.

Division del trabajo (ver README.md):
  - Ortega Yucra Hiron Axl --> este `server.py` + Docker + repo
  - Saico Cristhian       --> tools/calculo1.py   (Calculo I)
  - Rosales Yhin           --> tools/calculo2.py   (Calculo II)
  - Vilcapoma Jefferson   --> tools/calculo3.py   (Calculo III)
  - Meza Angel             --> tools/calculo4.py   (Calculo IV)
  - Lau Huamantoma Carlos --> skill/*.md + QA

SDK: `mcp` v2. En la v2 la clase `FastMCP` del modulo `mcp.server.fastmcp` se
llama `MCPServer` y vive en `mcp.server.mcpserver` -- el import anterior ya no
existe. Misma API que el servidor de referencia del repo
(`grupos/g01/semana01/derivadas1/server.py`).
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import sympy as sp
from mcp.server.mcpserver import MCPServer

# --- Rutas base del proyecto -------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"
SKILLS_DIR = BASE_DIR / "skill"

# Modulos de calculo, en orden. El nombre del archivo es el prefijo del nombre
# de cada tool que se registra desde el ("calculo1_limite_lateral"), para que
# dos personas del equipo nunca colisionen con el mismo nombre de tool.
MODULOS_CALCULO = ("calculo1", "calculo2", "calculo3", "calculo4")

mcp = MCPServer("grupo02-mcp-calculo")


def _normalizar(expr: Any) -> str:
    """Expresion de sympy en texto plano imprimible (sstr, no repr)."""
    return sp.sstr(sp.sympify(expr))


# =========================================================================
# SECCION 1: CONTEXTOS DE COMPORTAMIENTO (skill/ -> prompts MCP)
# =========================================================================
# Cada skill es un Markdown que le dice a la IA como comportarse: que tools
# usar, que formato dar, que no inventar. Vive en un archivo aparte para que
# Carlos (Prompts & QA) lo pueda editar sin tocar codigo.
def leer_skill(nombre_archivo: str) -> str:
    """Lee un contexto desde `skill/`. Nunca lanza: si falta, avisa y sigue."""
    ruta = SKILLS_DIR / nombre_archivo
    if not ruta.is_file():
        return (
            f"[AVISO] No se encontro el contexto '{nombre_archivo}' en {SKILLS_DIR}. "
            "Este modo responde con el comportamiento por defecto del servidor."
        )
    return ruta.read_text(encoding="utf-8")


@mcp.prompt(title="Resolutor - Modo Examen")
def contexto_resolutor_examen() -> str:
    """Resolucion formal de examen: directa, rigurosa, en LaTeX. Sin rodeos."""
    return leer_skill("skill_resolver_examen.md")


@mcp.prompt(title="Resolutor - Modo Paso a Paso")
def contexto_paso_a_paso() -> str:
    """Explicacion pedagogica: cada paso justificado, con avisos de errores comunes."""
    return leer_skill("skill_paso_a_paso.md")


@mcp.prompt(title="Tutor Academico Interactivo")
def contexto_tutor_interactivo() -> str:
    """Tutor: ensena desde cero o repasa temas avanzados, y verifica respuestas."""
    return leer_skill("skill_tutor_interactivo.md")


# =========================================================================
# SECCION 2: TOOLS BASE DEL SERVIDOR (resolucion en SymPy)
# =========================================================================
# Estas cuatro no dependen de `tools/`: son el piso minimo, para que el
# servidor resuelva algo aunque los modulos de los companeros aun no existan.
#
# Se llevan aqui los nombres de las tools base para poder (a) detectar
# colisiones de nombres al registrar los modulos de `tools/` y (b) responder
# el diagnostico de `estado_del_servidor`. No se consulta `mcp.list_tools()`
# para eso porque en el SDK v2 ese metodo es una corrutina: no se puede
# llamar al importar el modulo, que es justo cuando se registran las tools.
TOOLS_BASE: set[str] = {
    "calcular_derivada",
    "calcular_integral",
    "calcular_gradiente",
    "verificar_respuesta",
    "estado_del_servidor",
}
_TOOLS_REGISTRADAS: set[str] = set(TOOLS_BASE)


def _error(exc: Exception) -> dict[str, Any]:
    """Respuesta de error unificada para todas las tools.

    Recorta el mensaje: los errores de SymPy pueden traer el volcado completo
    de un solver (kilometros de texto con ecuaciones intermedias), y eso
    consume la ventana de contexto de la IA en vez de ayudar a corregir.
    """
    detalle = f"{type(exc).__name__}: {exc}"
    if len(detalle) > 300:
        detalle = detalle[:300] + "..."
    return {"estado": "error", "mensaje": detalle}


@mcp.tool(name="calcular_derivada")
def calcular_derivada(expresion: str, variable: str = "x", orden: int = 1) -> dict[str, Any]:
    """Deriva simbolicamente una funcion de una variable, hasta el orden pedido.

    `expresion` va en sintaxis de sympy/Python: "x**3*sin(x)", "exp(x)/x".
    NO uses "x^2" (en Python ^ es potencia bitwise, no exponente) ni nombres en
    espanol: sympy entiende "sin", "cos", "tan", "log", "sqrt", no "sen" ni "ln".

    Ademas de la derivada, si esta tiene ceros reales evidentes, devuelve los
    puntos criticos (sirve para los ejercicios tipo "donde f es estacionaria").

    OJO: si la derivada esta bien pero SymPy no logra resolver f'=0 (pasa con
    casi toda ecuacion transcendental, ej. "3*x**2*sin(x) + x**3*cos(x) = 0"),
    NO es un error: la tool responde igual con la derivada y agrega
    "puntos_criticos": null. La derivada es lo que se pidio; los puntos
    criticos son un extra.
    """
    try:
        if orden < 1:
            raise ValueError("'orden' debe ser >= 1")
        v = sp.Symbol(variable)
        f = sp.sympify(expresion)
        df = sp.diff(f, v, orden)
        resultado: dict[str, Any] = {
            "estado": "exito",
            "funcion": _normalizar(f),
            "derivada": _normalizar(df),
            "latex": sp.latex(df),
        }
        # Los puntos criticos van en su propio try/except: `sp.solve` sobre
        # ecuaciones trascendentales es lentisimo y falla Constantemente, y si
        # eso cayera en el try de arriba SE PERDERIA la derivada, que ya esta
        # calculada y es lo que el alumno pidio. Un extra jamas puede
        # arruinar el resultado principal.
        resultado["puntos_criticos"] = None
        try:
            criticos = [c for c in sp.solve(sp.Eq(df, 0), v) if c.is_real]
            if criticos:
                resultado["puntos_criticos"] = [_normalizar(c) for c in criticos]
        except Exception:
            pass  # sin puntos criticos, pero con la derivada: eso es lo importante
        return resultado
    except Exception as exc:  # la tool nunca debe tumbar el servidor
        return _error(exc)


@mcp.tool(name="calcular_integral")
def calcular_integral(
    expresion: str,
    variable: str = "x",
    limite_inferior: str | None = None,
    limite_superior: str | None = None,
) -> dict[str, Any]:
    """Integra simbolicamente una funcion: indefinida o definida en un intervalo.

    Para la integral INDEFINIDA deja `limite_inferior` y `limite_superior` en
    None. Para la DEFINIDA pasa los dos limites como texto, ej. "0" y "pi/2".

    Sintaxis de la expresion: "x**2*exp(x)", "1/(1+x**2)", "sqrt(x)".
    Devuelve el resultado exacto en texto y en LaTeX. Si SymPy no logra
    resolverla, devuelve estado "parcial" con lo que si pudo calcular, en vez
    de fallar.
    """
    try:
        v = sp.Symbol(variable)
        f = sp.sympify(expresion)
        definido = limite_inferior is not None or limite_superior is not None
        if definido and (limite_inferior is None or limite_superior is None):
            raise ValueError("para la integral definida hay que pasar los dos limites")

        if definido:
            a = sp.sympify(limite_inferior)
            b = sp.sympify(limite_superior)
            r = sp.integrate(f, (v, a, b))
            return {
                "estado": "exito",
                "tipo": "definida",
                "funcion": _normalizar(f),
                "limites": [_normalizar(a), _normalizar(b)],
                "resultado": _normalizar(r),
                "latex": sp.latex(r),
            }

        r = sp.integrate(f, v)
        return {
            "estado": "parcial" if r.has(sp.Integral) else "exito",
            "tipo": "indefinida",
            "funcion": _normalizar(f),
            "resultado": f"{_normalizar(r)} + C",
            "latex": f"{sp.latex(r)} + C",
        }
    except Exception as exc:  # la tool nunca debe tumbar el servidor
        return _error(exc)


@mcp.tool(name="calcular_gradiente")
def calcular_gradiente(expresion: str, variables: list[str]) -> dict[str, Any]:
    """Gradiente de una funcion multivariable; y su laplaciano si son 2 variables.

    `expresion` en sintaxis sympy con los nombres de `variables`, ej:
    expresion="x**2*y+z**3", variables=["x", "y", "z"].
    `variables` es una lista de nombres sueltos, ej. ["x", "y"].
    """
    try:
        if not variables:
            raise ValueError("'variables' no puede estar vacia")
        simbolos = [sp.Symbol(n) for n in variables]
        f = sp.sympify(expresion)
        grad = [sp.diff(f, v) for v in simbolos]
        salida: dict[str, Any] = {
            "estado": "exito",
            "funcion": _normalizar(f),
            "gradiente": [_normalizar(g) for g in grad],
            "latex": r"\nabla f = \left(" + ", ".join(sp.latex(g) for g in grad) + r"\right)",
        }
        if len(simbolos) == 2:
            laplaciano = sp.diff(grad[0], simbolos[0]) + sp.diff(grad[1], simbolos[1])
            salida["laplaciano"] = _normalizar(laplaciano)
        return salida
    except Exception as exc:  # la tool nunca debe tumbar el servidor
        return _error(exc)


@mcp.tool(name="verificar_respuesta")
def verificar_respuesta(
    respuesta_alumno: str,
    expresion: str | None = None,
    referencia: str | None = None,
    variable: str = "x",
) -> dict[str, Any]:
    """Verifica si la respuesta del alumno es CORRECTA. Usar solo en modo tutor.

    Se le pasan dos cosas:
      - `respuesta_alumno`: lo que escribio el alumno, en sintaxis sympy
        ("x*exp(x) - exp(x) + C", "sqrt(2)/2", "pi/4").
      - y UNA de estas dos referencias:
        * `expresion`: la funcion cuya integral se pidio. El servidor calcula
          la referencia exacta con sympy y compara.
        * `referencia`: el valor correcto que ya te dio otra tool, para
          comparar contra ese sin recalcularlo.
      - `variable`: variable de integracion o derivacion (default "x").

    La comparacion es SIMBOLICA, no numerica: "2/pi" y "0.6366" se consideran
    distintos (que es lo correcto: no son el mismo numero), pero "3*x**2" y
    "x**2*3" se consideran iguales. Devuelve "correcta": true/false mas la
    diferencia simplificada, que es lo que permite decirle al alumno en que se
    equivoco.

    OJO CON LA CONSTANTE DE INTEGRACION -- es la trampa clasica de esta tool.
    Si el alumno escribe "x*exp(x) - exp(x) + C", la `C` es un simbolo libre:
    la diferencia symbolica da "C", NO cero, y una comparacion ingenua le
    diria al alumno que esta mal cuando esta perfecto. Por eso, cuando se
    compara contra una ANTIDERIVADA (o sea, cuando pasaste `expresion`), dos
    respuestas que solo difieren en una constante se consideran CORRECTAS:
    lo que importa es que no dependan de la variable. Cuando comparas contra un
    valor concreto (`referencia`), ahi si la diferencia tiene que ser
    exactamente cero, porque en un valor fijo la constante SI importa.
    """
    try:
        if not respuesta_alumno:
            raise ValueError("'respuesta_alumno' no puede estar vacia")
        v = sp.Symbol(variable)
        alumno = sp.sympify(respuesta_alumno)

        if expresion is not None:
            objetivo = sp.integrate(sp.sympify(expresion), v)
            tipo = "integral indefinida"
            # Dos antiderivadas de la misma funcion difieren en una constante,
            # asi que lo que se compara es "no depende de la variable".
            correcta = v not in sp.simplify(alumno - objetivo).free_symbols
        elif referencia is not None:
            objetivo = sp.sympify(referencia)
            tipo = "valor de referencia"
            correcta = sp.simplify(alumno - objetivo) == 0
        else:
            raise ValueError("hay que pasar 'expresion' o 'referencia'")

        diferencia = sp.simplify(alumno - objetivo)
        return {
            "estado": "exito",
            "correcta": bool(correcta),
            "tipo": tipo,
            "respuesta_alumno": _normalizar(alumno),
            "respuesta_correcta": _normalizar(objetivo),
            "diferencia": _normalizar(diferencia),
            "nota": (
                "comparacion de antiderivadas: se acepta cualquier diferencia "
                "que sea constante"
                if tipo == "integral indefinida"
                else "comparacion de valor exacto: la diferencia debe ser cero"
            ),
        }
    except Exception as exc:  # la tool nunca debe tumbar el servidor
        return _error(exc)


@mcp.tool(name="estado_del_servidor")
async def estado_del_servidor() -> dict[str, Any]:
    """Diagnostico: que modulos de `tools/` cargaron y cuantas tools hay registradas.

    Usar como primer paso cuando algo no aparece en el cliente MCP: si un
    modulo no esta en "modulos_cargados", es que el archivo no existe, no
    compila, o sus funciones no cumplen el contrato de `tools/README.md`.
    """
    return {
        "estado": "exito",
        "servidor": "grupo02-mcp-calculo",
        "herramientas_base": sorted(TOOLS_BASE),
        "modulos_cargados": sorted(_MODULOS_CARGADOS),
        "modulos_faltantes": sorted(set(MODULOS_CALCULO) - set(_MODULOS_CARGADOS)),
        "total_tools": len(await mcp.list_tools()),
    }


# =========================================================================
# SECCION 3: CARGA DINAMICA DE tools/calculo1..4.py
# =========================================================================
# Contrato (detalle completo en tools/README.md):
#   - un .py por area en tools/, con el nombre calculo<N>.py
#   - toda funcion PUBLICA DEFINIDA EN ESE ARCHIVO (no importada de otro modulo)
#     se registra automaticamente como tool MCP
#   - el nombre de la tool es "<modulo>_<nombre_de_la_funcion>"
#   - el docstring se usa como descripcion (es lo que lee la IA) y los type
#     hints como schema de argumentos
#   - opcionalmente el modulo puede definir HERRAMIENTAS = ["nombre", ...]
#     para exponer solo algunas
#   - las tools devuelven SIEMPRE un dict con la clave "estado"
#     ("exito" / "parcial" / "error") y nunca lanzan excepciones
_MODULOS_CARGADOS: set[str] = set()


def _descripcion(fn: Any) -> str:
    """Docstring de la funcion como descripcion de la tool (lo que lee la IA)."""
    doc = (fn.__doc__ or "").strip()
    return doc or f"Tool del area {fn.__module__} (sin documentar: agregale un docstring)."


def _cargar_modulo(nombre_modulo: str) -> bool:
    """Importa `tools/<nombre_modulo>.py` y registra sus funciones como tools."""
    ruta = TOOLS_DIR / f"{nombre_modulo}.py"
    if not ruta.is_file():
        return False

    # Importar con el nombre real del modulo (no como "_carga_calculo1") para
    # que sus imports internos tipo "import comun" funcionen.
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    try:
        modulo = importlib.import_module(nombre_modulo)
    except Exception as exc:  # un modulo roto no debe tumbar el servidor
        print(f"[AVISO] tools/{nombre_modulo}.py no se pudo importar: {type(exc).__name__}: {exc}")
        return False

    # Si el modulo declara HERRAMIENTAS se respeta esa lista; si no, se toman
    # todas las funciones publicas definidas en el propio archivo.
    declaradas = getattr(modulo, "HERRAMIENTAS", None)
    if declaradas is None:
        candidatas = [
            (nombre, obj)
            for nombre, obj in vars(modulo).items()
            if not nombre.startswith("_")
            and callable(obj)
            and getattr(obj, "__module__", None) == modulo.__name__
        ]
    else:
        candidatas = [(nombre, getattr(modulo, nombre, None)) for nombre in declaradas]

    registradas = 0
    for nombre, fn in candidatas:
        if not callable(fn):
            print(f"[AVISO] {nombre_modulo}.HERRAMIENTAS lista '{nombre}', que no es una funcion")
            continue
        nombre_tool = f"{nombre_modulo}_{nombre}"
        if nombre_tool in _TOOLS_REGISTRADAS:
            print(f"[AVISO] tool duplicada {nombre_tool}, se omite")
            continue
        try:
            mcp.tool(name=nombre_tool, description=_descripcion(fn))(fn)
            _TOOLS_REGISTRADAS.add(nombre_tool)
            registradas += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[AVISO] no se pudo registrar {nombre_tool}: {type(exc).__name__}: {exc}")

    if registradas:
        _MODULOS_CARGADOS.add(nombre_modulo)
        print(f"[OK] tools/{nombre_modulo}.py -> {registradas} tool(s)")
    return True


for _nombre_modulo in MODULOS_CALCULO:
    _cargar_modulo(_nombre_modulo)


# =========================================================================
# SECCION 4: ARRANQUE
# =========================================================================
# El transporte se elige por variable de entorno porque los dos entornos son
# distintos y NO pueden usar el mismo:
#   - stdio (default, `python server.py`): el cliente MCP -- Claude Desktop,
#     Claude Code, MCP Inspector -- lanza al servidor como proceso hijo y
#     habla por entrada/salida estandar. Es el modo de pruebas locales.
#   - streamable-http (dentro de Docker): el servidor es un proceso de larga
#     duracion escuchando en un puerto y el cliente se conecta por HTTP. Sin
#     esto el contenedor terminaria al instante (en stdio, en cuanto se cierra
#     la consola el proceso muere) y no habria nada que proxyar.
# streamable-http y no "sse": la variante SSE del SDK esta poco mantenida; la
# que usan de verdad los clientes MCP actuales es streamable-http (mismo
# criterio que el servidor de referencia del repo).
TRANSPORTE = os.environ.get("MCP_TRANSPORT", "stdio")
PUERTO = int(os.environ.get("MCP_PORT", "8000"))


if __name__ == "__main__":
    print("=" * 68)
    print(" Servidor MCP-Calculo (Grupo 02)")
    print(f" contextos en skill/ : {len(list(SKILLS_DIR.glob('*.md')))} archivo(s)")
    print(f" modulos de tools/   : {', '.join(sorted(_MODULOS_CARGADOS)) or '(ninguno aun)'}")
    print(f" tools registradas   : {len(_TOOLS_REGISTRADAS)}")
    if TRANSPORTE == "stdio":
        print(" transporte          : stdio (cliente MCP local)")
    else:
        print(f" transporte          : {TRANSPORTE} en 0.0.0.0:{PUERTO}")
    print("=" * 68)
    if TRANSPORTE == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=PUERTO)
