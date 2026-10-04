"""
server.py — Servidor MCP «Frenet, Lagrange y Puntos Críticos» (Grupo 06).

Expone, con el SDK oficial de MCP para Python (FastMCP) y transporte STDIO, las herramientas:

    diagnosticar_problema         → lenguaje natural ⇒ qué método usar y con qué argumentos
    optimizar_con_restricciones   → Multiplicadores de Lagrange   (methods/metodo_lagrange.py)
    analizar_puntos_criticos      → Puntos críticos + Hessiana    (methods/metodo_hessiana.py)
    analizar_curva_frenet         → Triedro de Frenet, κ y τ      (methods/metodo_frenet.py)
    listar_resultados / obtener_resultado → historial guardado por storage.py
    combinar_reportes             → UN reporte HTML con varios ejercicios ya resueltos (core/combinado.py)

Cualquier cliente MCP (Claude Desktop, Claude Code, Cursor, agente.py con DeepSeek/Gemini...)
lo lanza como subproceso y le habla por stdin/stdout con JSON-RPC.

Validación en dos capas antes de calcular:
    1) estructural  — core/validacion.py (Pydantic): el SDK rechaza argumentos incompletos o mal tipados;
    2) lógica       — core/verificador.py: división por cero, curvatura nula, más restricciones que variables...

Ejecutar:   python server.py            (lo normal: lo lanza el cliente MCP)
Variables:  MCP_MATH_RESULTADOS  carpeta de resultados   (def. ./resultados)
            MCP_MATH_COMBINADOS  carpeta de reportes combinados (def. ./resultados_combinados)
            MCP_MATH_TIMEOUT     segundos por cálculo    (def. 120)
            MCP_MATH_PROCESOS    0 = calcular en el mismo proceso, sin límite de tiempo (depuración)
            MCP_MATH_LOG         nivel de log en stderr  (def. INFO)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

# Ejecutable desde cualquier carpeta:  python ruta/a/server.py
RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MPLBACKEND", "Agg")

from mcp.server.fastmcp import Context, FastMCP  # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import Field  # noqa: E402

from core.combinado import Combinador, ErrorCombinado  # noqa: E402
from core.diagnostico import diagnosticar  # noqa: E402
from core.motor import compactar, ejecutar  # noqa: E402
from core.validacion import (SolicitudCombinar, SolicitudConsulta, SolicitudDiagnostico,  # noqa: E402
                             SolicitudFrenet, SolicitudHessiana, SolicitudLagrange)
from storage import Almacen  # noqa: E402

# ════════════════════════════════════════════════════════════════════════════
# Configuración. ¡Nunca imprimir en stdout! Es el canal del protocolo.
# ════════════════════════════════════════════════════════════════════════════
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass
logging.basicConfig(stream=sys.stderr, level=os.environ.get("MCP_MATH_LOG", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mcp_math")

TIMEOUT_S = float(os.environ.get("MCP_MATH_TIMEOUT", "120"))
USAR_PROCESOS = os.environ.get("MCP_MATH_PROCESOS", "1") != "0"
Metodo = Literal["lagrange", "hessiana", "frenet"]
Detalle = Literal["compacto", "completo"]

almacen = Almacen()
combinador = Combinador(almacen)

INSTRUCCIONES = """\
Servidor de cálculo simbólico EXACTO (SymPy) para tres temas de Cálculo en varias variables.
Elige la herramienta según la ESTRUCTURA del problema, no solo según las palabras:

• ¿Hay una función f(x, y, …) a maximizar/minimizar Y una o más condiciones de IGUALDAD
  (sujeto a, sobre la curva/superficie, con la restricción, presupuesto fijo, volumen fijo)?
  → optimizar_con_restricciones  (Multiplicadores de Lagrange).
• ¿Hay una función f(x, y, …) SIN restricciones y se piden puntos críticos, máximos/mínimos
  relativos, puntos de silla, matriz Hessiana, criterio de la segunda derivada?
  → analizar_puntos_criticos  (gradiente = 0 + Hessiana).
• ¿Hay una CURVA parametrizada r(t) = (x(t), y(t), z(t)) y se pide tangente, normal, binormal,
  curvatura, torsión, planos osculador/normal/rectificante o triedro de Frenet?
  → analizar_curva_frenet.
• Si el enunciado es ambiguo o está en lenguaje natural, llama primero a diagnosticar_problema:
  devuelve el método recomendado y los argumentos ya extraídos.
• Si el usuario envía DOS O MÁS ejercicios en un mismo mensaje: resuelve CADA UNO con su
  herramienta (cada uno conserva su carpeta y su reporte individual) y, al final, llama UNA vez a
  combinar_reportes con todos los id_resultado en el orden del enunciado. Menciona ambas rutas:
  los reportes individuales y el reporte combinado.

Sintaxis de las expresiones (tipo calculadora): ^ potencia, * producto (se acepta 2x y x y),
sin cos tan exp log sqrt, pi, E. Las restricciones se escriben como igualdades 'x^2 + y^2 = 8'.
Si una herramienta devuelve un error de verificación, explícale al usuario el 'mensaje' y la
'sugerencia' con tus palabras: significa que el problema, tal como está planteado, no tiene sentido
matemático para ese método (no es un fallo del servidor). Presenta los resultados EXACTOS
(fracciones, raíces) tal como los devuelve el servidor y menciona la ruta del reporte HTML.
"""

mcp = FastMCP("frenet-lagrange-puntos-criticos", instructions=INSTRUCCIONES)


# ════════════════════════════════════════════════════════════════════════════
# Ejecución con límite de tiempo en procesos aparte
# ════════════════════════════════════════════════════════════════════════════
class _Ejecutor:
    """Un proceso trabajador (core/trabajador.py) con tuberías propias, reutilizado entre llamadas
    para no recargar SymPy cada vez. Si un cálculo excede el tiempo, el proceso se mata y se
    lanza otro: el servidor nunca se queda colgado.

    Se usa subprocess con stdin/stdout/stderr EXPLÍCITOS (y no multiprocessing) porque en
    Windows crear un proceso mientras el servidor está leyendo su stdin (el canal MCP) puede
    bloquearse indefinidamente."""

    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._candado: asyncio.Lock | None = None
        self._listo = False

    def iniciar(self) -> subprocess.Popen[bytes]:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = subprocess.Popen(
                [sys.executable, "-u", str(RAIZ / "core" / "trabajador.py")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr.fileno() if _stderr_real() else None,
                cwd=str(RAIZ), env={**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._listo = False
        return self._proc

    def _matar(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                pass

    def _pedir(self, pedido: bytes) -> dict:
        """Bloqueante (se ejecuta en un hilo): envía un pedido y lee una respuesta."""
        proc = self.iniciar()
        assert proc.stdin is not None and proc.stdout is not None
        if not self._listo:                          # primera línea: el trabajador terminó de importar
            if not proc.stdout.readline():
                raise RuntimeError("el proceso de cálculo no arrancó")
            self._listo = True
        proc.stdin.write(pedido)
        proc.stdin.flush()
        linea = proc.stdout.readline()
        if not linea:
            raise RuntimeError("el proceso de cálculo terminó inesperadamente")
        return json.loads(linea)

    async def correr(self, metodo: str, solicitud: dict, carpeta: str | None) -> dict:
        if not USAR_PROCESOS:
            return await asyncio.to_thread(ejecutar, metodo, solicitud, carpeta)
        if self._candado is None:
            self._candado = asyncio.Lock()
        pedido = json.dumps({"metodo": metodo, "solicitud": solicitud, "carpeta": carpeta},
                            ensure_ascii=True).encode("ascii") + b"\n"
        async with self._candado:                    # un cálculo a la vez por trabajador
            try:
                return await asyncio.wait_for(asyncio.to_thread(self._pedir, pedido), timeout=TIMEOUT_S)
            except asyncio.TimeoutError:
                log.warning("Calculo %s cancelado tras %.0f s", metodo, TIMEOUT_S)
                self._matar()                        # el hilo bloqueado en readline se libera al morir el proceso
                return {"ok": False, "error": {
                    "tipo": "tiempo", "codigo": "TIEMPO_AGOTADO",
                    "mensaje": f"El cálculo simbólico superó {TIMEOUT_S:.0f} s y se canceló.",
                    "sugerencia": "Simplifica el problema (menos variables, grados más bajos) o prueba "
                                  "metodo='solve' / 'nonlinsolve'. El administrador puede subir MCP_MATH_TIMEOUT."}}
            except Exception as e:  # noqa: BLE001
                log.exception("Fallo del proceso de cálculo")
                self._matar()
                return {"ok": False, "error": {"tipo": "interno", "codigo": "PROCESO_CAIDO",
                                               "mensaje": f"El proceso de cálculo falló: {e}",
                                               "sugerencia": "Vuelve a intentarlo; si persiste, simplifica la "
                                                             "expresión."}}

    def cerrar(self) -> None:
        self._matar()


def _stderr_real() -> bool:
    try:
        sys.stderr.fileno()
        return True
    except (AttributeError, OSError, ValueError):
        return False


ejecutor = _Ejecutor()


def _descripcion(metodo: str, s: Any) -> str:
    if metodo == "lagrange":
        return f"f = {s.funcion}; sujeto a {'; '.join(s.restricciones)}"
    if metodo == "hessiana":
        return f"f = {s.funcion}"
    return f"r({s.parametro}) = ({', '.join(s.curva)}), t0 = {s.t0}"


async def _calcular(metodo: Metodo, s: Any, detalle: Detalle, ctx: Context | None) -> dict[str, Any]:
    """Común a las tres herramientas: crea la carpeta, calcula, guarda y arma la respuesta."""
    if ctx is not None:
        await ctx.info(f"Verificando y resolviendo con el método de {metodo}…")
    id_, carpeta = almacen.nueva_carpeta(metodo)
    r = await ejecutor.correr(metodo, s.model_dump(mode="json"), str(carpeta))
    if not r.get("ok"):
        try:
            carpeta.rmdir() if not any(carpeta.iterdir()) else None
        except OSError:
            pass
        e = r["error"]
        # ToolError ⇒ el cliente recibe isError=true y el LLM lee el texto para explicárselo al usuario.
        raise ToolError(json.dumps({"ok": False, "metodo": metodo, **e}, ensure_ascii=False))
    reg = almacen.guardar(id_, metodo, _descripcion(metodo, s), r["solicitud"], r["resultado"], r["resumen"],
                          r["archivos"])
    return {
        "ok": True,
        "metodo": metodo,
        "id_resultado": id_,
        "resumen": r["resumen"],
        "verificacion_previa": r["verificacion_previa"],
        "resultado": r["resultado"] if detalle == "completo" else compactar(r["resultado"]),
        "archivos": reg.archivos,
        "tiempo_s": r["tiempo_s"],
        **({"datos_grafico": r["datos_grafico"]} if "datos_grafico" in r else {}),
    }


_DETALLE = Annotated[Detalle, Field(description="'compacto' (por defecto) omite el LaTeX y los pasos (quedan en "
                                                "resultado.json y en el HTML); 'completo' lo devuelve todo.")]
_ANOT_CALCULO = dict(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)


# ════════════════════════════════════════════════════════════════════════════
# Herramientas (Tools). El docstring ES la descripción que lee el LLM para decidir.
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool(title="Diagnosticar qué método usar",
          annotations=ToolAnnotations(title="Diagnosticar problema", readOnlyHint=True, idempotentHint=True,
                                      openWorldHint=False))
def diagnosticar_problema(solicitud: SolicitudDiagnostico) -> dict[str, Any]:
    """Analiza un enunciado en LENGUAJE NATURAL y decide cuál de los tres métodos corresponde
    (Lagrange, Hessiana o Frenet), con qué confianza y por qué. Además extrae los argumentos
    (función, restricciones, curva, t0) listos para pasarlos a la herramienta recomendada.

    ÚSALA PRIMERO cuando:
      • el usuario pega un ejercicio redactado ("una caja de volumen 32…", "¿dónde alcanza su máximo…?");
      • no está claro si hay restricciones o si se trata de una curva;
      • quieres confirmar tu elección antes de calcular.
    NO calcula nada: es rápida y no tiene efectos. Si 'faltantes' no está vacío, pide esos datos
    al usuario en vez de inventarlos. Revisa 'argumentos_sugeridos' antes de usarlos.
    """
    return diagnosticar(solicitud.enunciado).como_dict()


@mcp.tool(title="Optimizar con restricciones (Lagrange)",
          annotations=ToolAnnotations(title="Multiplicadores de Lagrange", **_ANOT_CALCULO))
async def optimizar_con_restricciones(solicitud: SolicitudLagrange, detalle: _DETALLE = "compacto",
                                      ctx: Context | None = None) -> dict[str, Any]:
    """MÉTODO DE MULTIPLICADORES DE LAGRANGE — optimización CONDICIONADA (con restricciones de igualdad).

    Úsala cuando se pida maximizar o minimizar una función f(x, y, …) SUJETA A una o varias
    condiciones de IGUALDAD g_i(x, y, …) = c_i. Pistas en el enunciado: "sujeto a", "s.a.",
    "con la restricción", "sobre la circunferencia/esfera/elipse/plano/curva", "presupuesto fijo",
    "volumen/área/perímetro dado", "distancia mínima de un punto a una superficie", "multiplicadores".
    Ejemplos: máx/mín de xy sobre x²+y²=8; punto del plano x+y+z=3 más cercano al origen;
    extremos de x+y+z sobre la intersección x²+y²=2, x+z=1.

    NO la uses si no hay restricción (→ analizar_puntos_criticos) ni con DESIGUALDADES (≤, ≥):
    este método solo trata igualdades.

    Qué hace (exacto, con SymPy): arma L = f − Σ λᵢ gᵢ, resuelve ∇L = 0 (bases de Gröbner, raíces
    exactas), clasifica cada punto con el HESSIANO ORLADO (menores principales), compara valores
    para el máximo/mínimo global entre candidatos y detecta puntos singulares de la restricción
    (∇g = 0) que Lagrange no ve. Hasta 6 variables y 5 restricciones.

    Devuelve: id_resultado, resumen en frases, verificación previa, resultado (puntos, λ, f,
    clasificación) y rutas del reporte HTML interactivo (procedimiento en LaTeX + gráfico 3D).
    Errores de verificación típicos: RESTRICCION_IMPOSIBLE, SOBREDETERMINADO, DIVISION_POR_CERO.
    """
    return await _calcular("lagrange", solicitud, detalle, ctx)


@mcp.tool(title="Puntos críticos y Hessiana",
          annotations=ToolAnnotations(title="Puntos críticos y matriz Hessiana", **_ANOT_CALCULO))
async def analizar_puntos_criticos(solicitud: SolicitudHessiana, detalle: _DETALLE = "compacto",
                                   ctx: Context | None = None) -> dict[str, Any]:
    """PUNTOS CRÍTICOS Y MATRIZ HESSIANA — optimización LIBRE (sin restricciones).

    Úsala cuando se pida encontrar y CLASIFICAR los puntos críticos de una función f(x, y, …)
    en todo su dominio: máximos y mínimos relativos/locales, puntos de silla, "criterio de la
    segunda derivada", "discriminante D = f_xx f_yy − f_xy²", "matriz Hessiana definida positiva",
    "extremos relativos", "¿dónde alcanza f su mínimo?" (sin condiciones extra).
    Ejemplos: x³ + y³ − 3xy; x⁴ + y⁴ − 4xy + 1; x·y·e^{−(x²+y²)/2}; x² + y² + z² − 2xyz.

    NO la uses si el problema impone una igualdad que deben cumplir las variables
    (→ optimizar_con_restricciones) ni para curvas paramétricas (→ analizar_curva_frenet).

    Qué hace (exacto): resuelve ∇f = 0 con raíces exactas, calcula la Hessiana en cada punto y la
    clasifica (Sylvester/autovalores; para n = 2 el discriminante D). Si el criterio no decide
    (D = 0, Hessiana semidefinida) NO se rinde: usa términos de Taylor de orden superior y curvas
    de prueba, y certifica extremos GLOBALES cuando puede (coercividad). Indica la 'certeza' de
    cada conclusión (demostrado / evidencia numérica). Hasta 6 variables.

    Devuelve: id_resultado, resumen, verificación previa, resultado y rutas del reporte HTML
    (superficie 3D, curvas de nivel, flujo del gradiente). Errores típicos: FUNCION_CONSTANTE,
    DIVISION_POR_CERO, HESSIANA_NO_CUADRADA, DEMASIADAS_VARIABLES.
    """
    return await _calcular("hessiana", solicitud, detalle, ctx)


@mcp.tool(title="Curva: triedro de Frenet, curvatura y torsión",
          annotations=ToolAnnotations(title="Triedro de Frenet", **_ANOT_CALCULO))
async def analizar_curva_frenet(solicitud: SolicitudFrenet, detalle: _DETALLE = "compacto",
                                ctx: Context | None = None) -> dict[str, Any]:
    """GEOMETRÍA DIFERENCIAL DE CURVAS — triedro de Frenet–Serret, curvatura y torsión.

    Úsala cuando haya una CURVA PARAMETRIZADA r(t) = (x(t), y(t)[, z(t)]) — en el plano o en el
    espacio — y se pida: vector tangente unitario T, normal principal N, binormal B, curvatura κ,
    torsión τ, radio/círculo de curvatura, planos osculador, normal o rectificante, "triedro móvil",
    "fórmulas de Frenet–Serret", componentes tangencial y normal de la aceleración.
    Ejemplos: hélice (cos t, sin t, t) en t = 0; cúbica alabeada (t, t², t³) en t = 1; parábola (t, t²).
    Admite constantes simbólicas (a cos t, a sin t, b t): las fórmulas salen generales.

    NO la uses para optimizar funciones (→ Lagrange o Hessiana).

    Qué hace (exacto): r', r'', r''', T, N, B, κ = |r'×r''|/|r'|³, τ = (r'×r'')·r'''/|r'×r''|²,
    longitud de arco cuando existe en forma cerrada, todo en general y evaluado en t0, las
    ecuaciones de los tres planos en t0 y la verificación numérica (50 dígitos) de las fórmulas
    de Frenet–Serret y de la ortonormalidad de {T, N, B}.

    Validación previa: si la curva es una RECTA (κ ≡ 0) o t0 es un punto singular o de inflexión,
    responde con un error explicativo (CURVATURA_CERO, PUNTO_SINGULAR, CURVATURA_CERO_EN_T0) y una
    sugerencia, porque N y B no existen ahí.
    """
    return await _calcular("frenet", solicitud, detalle, ctx)


@mcp.tool(title="Listar resultados guardados",
          annotations=ToolAnnotations(title="Listar resultados", readOnlyHint=True, openWorldHint=False))
def listar_resultados(metodo: Annotated[Metodo | None, Field(description="Filtra por método (opcional).")] = None,
                      limite: Annotated[int, Field(ge=1, le=100, description="Máximo de resultados.")] = 20
                      ) -> dict[str, Any]:
    """Lista los cálculos ya realizados (más recientes primero) con su id, método, fecha y una
    descripción. Úsala cuando el usuario pregunte por un ejercicio anterior ("¿qué salió en el de
    la hélice?", "muéstrame el último de Lagrange") y luego llama a obtener_resultado con el id."""
    return {"resultados": almacen.listar(metodo, limite), "carpeta": str(almacen.base)}


@mcp.tool(title="Obtener un resultado guardado",
          annotations=ToolAnnotations(title="Obtener resultado", readOnlyHint=True, openWorldHint=False))
def obtener_resultado(solicitud: SolicitudConsulta, detalle: _DETALLE = "compacto") -> dict[str, Any]:
    """Recupera un cálculo guardado por su id_resultado: la entrada, el resultado exacto, el
    resumen y las rutas de sus archivos (HTML, PNG). Evita recalcular lo que ya se resolvió."""
    try:
        r = almacen.obtener(solicitud.id_resultado)
    except KeyError as e:
        raise ToolError(json.dumps({"ok": False, "codigo": "NO_ENCONTRADO", "mensaje": str(e).strip("'\""),
                                    "sugerencia": "Usa listar_resultados para ver los ids disponibles."},
                                   ensure_ascii=False)) from e
    if detalle == "compacto" and r.get("resultado"):
        r["resultado"] = compactar(r["resultado"])
    return r


@mcp.tool(title="Combinar varios ejercicios en un solo reporte",
          annotations=ToolAnnotations(title="Reporte combinado", readOnlyHint=False, destructiveHint=False,
                                      idempotentHint=False, openWorldHint=False))
async def combinar_reportes(solicitud: SolicitudCombinar) -> dict[str, Any]:
    """REPORTE COMBINADO — reúne en UNA página HTML los reportes de varios ejercicios YA resueltos.

    ÚSALA SIEMPRE que el usuario envíe 2 o más ejercicios en un mismo mensaje (aunque sean de
    métodos distintos): primero resuelve cada ejercicio con su herramienta (optimizar_con_restricciones,
    analizar_puntos_criticos o analizar_curva_frenet) — así cada uno conserva su carpeta y su
    reporte.html individual en resultados/ — y DESPUÉS llama a esta herramienta UNA sola vez con
    todos los id_resultado, en el mismo orden en que el usuario planteó los ejercicios. Úsala también
    si el usuario pide juntar ejercicios resueltos antes (búscalos con listar_resultados).

    Qué hace: copia el reporte completo de cada ejercicio (sus 5 pestañas: Resumen, Procedimiento,
    Gráfico 3D, Gráficos 2D y JSON) dentro de una sola página con barra de navegación
    «← Anterior / Siguiente ejercicio →», índice y atajos de teclado. NO recalcula nada ni modifica
    los reportes individuales. Lo guarda en una carpeta APARTE:
    resultados_combinados/lote-AAAAMMDD-HHMMSS-xxxxxx/reporte_combinado.html (+ lote.json).

    Pasa en 'enunciados' el texto de cada ejercicio (mismo orden) para que se vea en el índice.
    Devuelve: id_lote, la lista de ejercicios incluidos y la ruta del HTML combinado.
    Error típico: NO_ENCONTRADO (algún id no existe; usa listar_resultados).
    """
    try:
        return await asyncio.to_thread(combinador.combinar, solicitud.ids, solicitud.titulo, solicitud.enunciados)
    except ErrorCombinado as e:
        raise ToolError(json.dumps({"ok": False, "codigo": e.codigo, "mensaje": e.mensaje,
                                    "sugerencia": e.sugerencia}, ensure_ascii=False)) from e


# ════════════════════════════════════════════════════════════════════════════
# Recursos y prompts
# ════════════════════════════════════════════════════════════════════════════
@mcp.resource("resultados://{id_resultado}", mime_type="application/json",
              description="JSON completo de un resultado guardado.")
def recurso_resultado(id_resultado: str) -> str:
    try:
        return json.dumps(almacen.obtener(id_resultado), ensure_ascii=False, indent=2)
    except KeyError as e:
        raise ValueError(str(e)) from e


@mcp.resource("ayuda://metodos", mime_type="text/markdown", description="Cuándo usar cada método y sintaxis.")
def recurso_ayuda() -> str:
    return "# Guía de métodos\n\n" + INSTRUCCIONES


@mcp.prompt(title="Resolver un problema paso a paso")
def resolver_problema(enunciado: str) -> str:
    """Plantilla para que el LLM diagnostique, calcule y explique un ejercicio."""
    return (f"Resuelve este ejercicio usando el servidor MCP de cálculo exacto:\n\n«{enunciado}»\n\n"
            "1) Llama a diagnosticar_problema con el enunciado.\n"
            "2) Confirma o corrige los argumentos sugeridos y llama a la herramienta recomendada.\n"
            "3) Explica el procedimiento con los resultados EXACTOS que devuelva el servidor, interpreta "
            "cada punto o vector y menciona la ruta del reporte HTML.\n"
            "4) Si hay un error de verificación, explica por qué el planteamiento no tiene sentido y propone "
            "la corrección que sugiere el servidor.")


def main() -> None:
    log.info("Servidor MCP listo (STDIO). Resultados en %s · combinados en %s · timeout %.0f s · procesos=%s",
             almacen.base, combinador.base, TIMEOUT_S, USAR_PROCESOS)
    if USAR_PROCESOS:
        ejecutor.iniciar()            # arranca (y precarga SymPy) ANTES de abrir el canal STDIO
    try:
        mcp.run(transport="stdio")
    finally:
        ejecutor.cerrar()


if __name__ == "__main__":
    main()
