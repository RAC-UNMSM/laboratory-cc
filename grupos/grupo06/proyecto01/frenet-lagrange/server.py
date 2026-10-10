"""
server.py — Servidor MCP «grupo06-frenet-lagrange» (Frenet, Lagrange y Puntos Críticos · Grupo 06).

Expone, con el SDK oficial de MCP para Python 2.x (mcp==2.1.1, clase MCPServer), las herramientas:

    diagnosticar_problema         → lenguaje natural ⇒ qué método usar y con qué argumentos
    optimizar_con_restricciones   → Multiplicadores de Lagrange   (methods/metodo_lagrange.py)
    analizar_puntos_criticos      → Puntos críticos + Hessiana    (methods/metodo_hessiana.py)
    analizar_curva_frenet         → Triedro de Frenet, κ y τ      (methods/metodo_frenet.py)
    listar_resultados / obtener_resultado → historial guardado por storage.py
    combinar_reportes             → UN reporte HTML con los ejercicios que se elijan (core/combinado.py)

Reporte combinado AUTOMÁTICO: después de publicar cada ejercicio, core/motor.publicar llama a
core/combinado.agregar_a_sesion, que regenera grupo06/lote-sesion-actual/reporte_combinado.html
con todos los ejercicios de la sesión (prefijo fijo; no se crea un id de lote nuevo cada vez).

Transporte (MCP_TRANSPORT):
    streamable-http (por defecto) — escucha en 0.0.0.0:8000, ruta /mcp, para la red Docker lab_net
                                    detrás de Caddy. Sin estado (stateless): cualquier réplica atiende
                                    cualquier petición.
    stdio                         — para Claude Desktop en la PC (python server.py --stdio).

Almacenamiento (storage.py): SeaweedFS por API S3, 100 % en MEMORIA (el HTML y el PNG se generan
como bytes y se suben directamente; el contenedor no escribe en disco). Cada cálculo se sube a
    <IMG_BUCKET>/grupo06/<id_resultado>/{reporte.html, grafico.png, resultado.json, entrada.json, meta.json}
y la respuesta trae las URLs PÚBLICAS (Caddy) en Markdown + la imagen PNG como bloque Image de respaldo.

Validación en dos capas antes de calcular:
    1) estructural  — core/validacion.py (Pydantic): el SDK rechaza argumentos incompletos o mal tipados;
    2) lógica       — core/verificador.py: división por cero, curvatura nula, más restricciones que variables...

Variables: MCP_TRANSPORT, MCP_HOST (0.0.0.0), MCP_PORT (8000), MCP_HTTP_PATH (/mcp), MCP_STATELESS (1),
           SEAWEEDFS_S3_URL, IMG_BUCKET, PUBLIC_IMG_BASE_URL, MCP_GRUPO,
           MCP_MATH_TIMEOUT (120 s), MCP_MATH_PROCESOS (1; 0 = sin procesos aparte), MCP_MATH_WORKERS (2),
           MCP_MATH_LOG (INFO).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
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

from mcp.server.mcpserver import Context, MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import CallToolResult, ImageContent, TextContent, ToolAnnotations  # noqa: E402
from pydantic import Field  # noqa: E402

from core.combinado import Combinador, ErrorCombinado, configurar_sesion  # noqa: E402
from core.diagnostico import diagnosticar  # noqa: E402
from core.motor import compactar, ejecutar, publicar  # noqa: E402
from core.validacion import (SolicitudCombinar, SolicitudConsulta, SolicitudDiagnostico,  # noqa: E402
                             SolicitudFrenet, SolicitudHessiana, SolicitudLagrange)
from storage import Almacen, ErrorAlmacen, elegir_backend  # noqa: E402

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


def _transporte_pedido() -> str:
    """--stdio / --http en la línea de comandos tienen prioridad sobre MCP_TRANSPORT."""
    if "--stdio" in sys.argv:
        return "stdio"
    if "--http" in sys.argv:
        return "streamable-http"
    return os.environ.get("MCP_TRANSPORT", "streamable-http")


NOMBRE_SERVIDOR = "grupo06-frenet-lagrange"
TRANSPORTE = _transporte_pedido()
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PUERTO = int(os.environ.get("MCP_PORT", "8000"))
RUTA_HTTP = os.environ.get("MCP_HTTP_PATH", "/mcp")
SIN_ESTADO = os.environ.get("MCP_STATELESS", "1") != "0"
TIMEOUT_S = float(os.environ.get("MCP_MATH_TIMEOUT", "120"))
USAR_PROCESOS = os.environ.get("MCP_MATH_PROCESOS", "1") != "0"
N_TRABAJADORES = max(1, int(os.environ.get("MCP_MATH_WORKERS", "2")))
Metodo = Literal["lagrange", "hessiana", "frenet"]
Detalle = Literal["compacto", "completo"]

almacen = Almacen(elegir_backend(TRANSPORTE))
combinador = Combinador(almacen)
configurar_sesion(almacen)                           # reporte combinado automático de la sesión

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
• REPORTE COMBINADO AUTOMÁTICO: cada ejercicio resuelto se añade solo al reporte de la sesión
  (grupo06/lote-sesion-actual/reporte_combinado.html); su enlace viene en 'reporte_sesion' y en el
  Markdown. No hace falta llamar a combinar_reportes para eso. Pasa en 'enunciado' el texto del
  ejercicio tal como lo escribió el usuario para que se vea en el índice. Menciona ambas rutas:
  el reporte individual y el reporte combinado de la sesión.

Sintaxis de las expresiones (tipo calculadora): ^ potencia, * producto (se acepta 2x y x y),
sin cos tan exp log sqrt, pi, e (número de Euler: e^t = exp(t)). Las restricciones se escriben como igualdades 'x^2 + y^2 = 8'.
Si una herramienta devuelve un error de verificación, explícale al usuario el 'mensaje' y la
'sugerencia' con tus palabras: significa que el problema, tal como está planteado, no tiene sentido
matemático para ese método (no es un fallo del servidor). Presenta los resultados EXACTOS
(fracciones, raíces) tal como los devuelve el servidor.
Cada cálculo devuelve un bloque 'markdown' con enlaces PÚBLICOS: copia ese Markdown tal cual en tu
respuesta (la imagen del gráfico se verá en el chat y el enlace abre el reporte interactivo).
"""

# SDK 2.x: el servidor se crea solo con su nombre. Lo demás se configura aparte:
#   • instructions → se fijan en el servidor de bajo nivel (MCPServer no tiene setter público);
#   • host/port/ruta/stateless → se aplican al ARRANCAR (MCPServer.run los pasa a
#     run_streamable_http_async). Ver _configurar_http() y main().
mcp = MCPServer("grupo06-frenet-lagrange")
mcp._lowlevel_server.instructions = INSTRUCCIONES      # lo que lee el LLM al conectarse


def _configurar_http(servidor: MCPServer) -> None:
    """Completa el arranque HTTP sin tocar la llamada literal de main():

    * host y puerto: MCP_HOST / MCP_PORT si están definidos (0.0.0.0:8000 por defecto, lo que exige
      la red Docker lab_net); así las pruebas pueden usar otro puerto;
    * ruta /mcp y modo SIN ESTADO (stateless): cualquier réplica detrás de Caddy atiende cualquier
      petición, sin sesiones guardadas en memoria;
    * Host público de Caddy aceptado: con 0.0.0.0 el SDK no activa la protección anti DNS-rebinding
      que solo deja pasar 'localhost'."""
    original = servidor.run_streamable_http_async

    async def run_streamable_http_async(**opciones: Any) -> None:
        opciones["host"] = os.environ.get("MCP_HOST") or opciones.get("host", HOST)
        opciones["port"] = int(os.environ.get("MCP_PORT") or opciones.get("port", PUERTO))
        opciones.setdefault("streamable_http_path", RUTA_HTTP)
        opciones.setdefault("stateless_http", SIN_ESTADO)
        await original(**opciones)

    servidor.run_streamable_http_async = run_streamable_http_async  # type: ignore[method-assign]


_configurar_http(mcp)


# ════════════════════════════════════════════════════════════════════════════
# Ejecución con límite de tiempo en procesos aparte
# ════════════════════════════════════════════════════════════════════════════
class _Trabajador:
    """Un proceso de cálculo (core/trabajador.py) con tuberías propias, reutilizado entre llamadas
    para no recargar SymPy cada vez. Si un cálculo excede el tiempo, el proceso se mata y se
    lanza otro.

    Se usa subprocess con stdin/stdout EXPLÍCITOS (y no multiprocessing) porque en Windows
    crear un proceso mientras el servidor lee su stdin (modo STDIO) puede bloquearse."""

    def __init__(self, n: int) -> None:
        self.n = n
        self._proc: subprocess.Popen[bytes] | None = None
        self._listos: set[int] = set()               # pids que ya avisaron que terminaron de importar

    def iniciar(self) -> subprocess.Popen[bytes]:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = subprocess.Popen(
                [sys.executable, "-u", str(RAIZ / "core" / "trabajador.py")],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=sys.stderr.fileno() if _stderr_real() else None,
                cwd=str(RAIZ), env={**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return self._proc

    def matar(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                pass

    def pedir(self, pedido: bytes) -> dict:
        """Bloqueante (se ejecuta en un hilo): envía un pedido y lee una respuesta."""
        proc = self.iniciar()
        assert proc.stdin is not None and proc.stdout is not None
        if proc.pid not in self._listos:            # primera línea: el trabajador terminó de importar
            if not proc.stdout.readline():
                raise RuntimeError("el proceso de cálculo no arrancó")
            self._listos.add(proc.pid)
        proc.stdin.write(pedido)
        proc.stdin.flush()
        linea = proc.stdout.readline()
        if not linea:
            raise RuntimeError("el proceso de cálculo terminó inesperadamente")
        return json.loads(linea)


class _Ejecutor:
    """Pool de N trabajadores: hasta N cálculos simultáneos (usuarios concurrentes por HTTP); los
    demás esperan su turno en una cola. Un cálculo que se cuelga solo afecta a SU trabajador."""

    def __init__(self, n: int) -> None:
        self.trabajadores = [_Trabajador(i) for i in range(n)]
        self._libres: asyncio.Queue[_Trabajador] | None = None

    def iniciar(self) -> None:
        for t in self.trabajadores:                 # arrancan ya: precargan SymPy mientras llega el 1.er pedido
            t.iniciar()

    def _cola(self) -> asyncio.Queue[_Trabajador]:
        if self._libres is None:                    # se crea dentro del bucle de eventos del servidor
            self._libres = asyncio.Queue()
            for t in self.trabajadores:
                self._libres.put_nowait(t)
        return self._libres

    async def correr(self, metodo: str, solicitud: dict) -> dict:
        """Calcula en un trabajador libre. El HTML y el PNG vuelven como bytes (en memoria)."""
        if not USAR_PROCESOS:
            return await asyncio.to_thread(ejecutar, metodo, solicitud, True)
        pedido = json.dumps({"metodo": metodo, "solicitud": solicitud, "generar_archivos": True},
                            ensure_ascii=True).encode("ascii") + b"\n"
        cola = self._cola()
        t = await cola.get()
        try:
            return await asyncio.wait_for(asyncio.to_thread(t.pedir, pedido), timeout=TIMEOUT_S)
        except asyncio.TimeoutError:
            log.warning("Calculo %s cancelado tras %.0f s (trabajador %d)", metodo, TIMEOUT_S, t.n)
            t.matar()                                # el hilo bloqueado en readline se libera al morir el proceso
            return {"ok": False, "error": {
                "tipo": "tiempo", "codigo": "TIEMPO_AGOTADO",
                "mensaje": f"El cálculo simbólico superó {TIMEOUT_S:.0f} s y se canceló.",
                "sugerencia": "Simplifica el problema (menos variables, grados más bajos) o prueba "
                              "metodo='solve' / 'nonlinsolve'. El administrador puede subir MCP_MATH_TIMEOUT."}}
        except Exception as e:  # noqa: BLE001
            log.exception("Fallo del proceso de cálculo")
            t.matar()
            return {"ok": False, "error": {"tipo": "interno", "codigo": "PROCESO_CAIDO",
                                           "mensaje": f"El proceso de cálculo falló: {e}",
                                           "sugerencia": "Vuelve a intentarlo; si persiste, simplifica la "
                                                         "expresión."}}
        finally:
            cola.put_nowait(t)

    def cerrar(self) -> None:
        for t in self.trabajadores:
            t.matar()


def _stderr_real() -> bool:
    try:
        sys.stderr.fileno()
        return True
    except (AttributeError, OSError, ValueError):
        return False


ejecutor = _Ejecutor(N_TRABAJADORES)


def _descripcion(metodo: str, s: Any) -> str:
    if metodo == "lagrange":
        return f"f = {s.funcion}; sujeto a {'; '.join(s.restricciones)}"
    if metodo == "hessiana":
        return f"f = {s.funcion}"
    return f"r({s.parametro}) = ({', '.join(s.curva)}), t0 = {s.t0}"


def _artefactos(crudos: dict[str, Any] | None) -> dict[str, bytes]:
    """Bytes del HTML/PNG: llegan en base64 desde el proceso de cálculo (o como bytes si
    MCP_MATH_PROCESOS=0). Todo queda en memoria."""
    out: dict[str, bytes] = {}
    for k, v in (crudos or {}).items():
        out[k] = v if isinstance(v, (bytes, bytearray)) else base64.b64decode(v)
    return out


def _miniatura(png: bytes | None, lado_max: int = 1024) -> bytes | None:
    """PNG reducido (≤1024 px, paleta de 256 colores, ~150-250 KB) para el bloque Image de respaldo,
    hecho en memoria a partir de los bytes de la lámina completa (que queda publicada en el almacén)."""
    if not png:
        return None
    try:
        from PIL import Image as PILImage
        with PILImage.open(io.BytesIO(png)) as im:
            im = im.convert("RGBA")
            fondo = PILImage.new("RGBA", im.size, (255, 255, 255, 255))
            im = PILImage.alpha_composite(fondo, im).convert("RGB")
            im.thumbnail((lado_max, lado_max))
            buf = io.BytesIO()
            im.quantize(256).save(buf, format="PNG", optimize=True)
            return buf.getvalue()
    except Exception:  # noqa: BLE001 — sin Pillow o PNG ilegible: se omite la miniatura
        return None


def _markdown(metodo: str, enlaces: dict[str, str], sesion: str | None = None, n_sesion: int | None = None) -> str:
    """Enlaces públicos listos para pegar en el chat (Markdown)."""
    lineas: list[str] = []
    if "html" in enlaces:
        lineas.append(f"![Reporte de cálculo]({enlaces['html']})")
    if "png" in enlaces:
        lineas.append(f"![Gráfico — {metodo}]({enlaces['png']})")
    if "html" in enlaces:
        lineas.append(f"[Abrir el reporte interactivo (procedimiento + gráfico 3D)]({enlaces['html']})")
    if "resultado" in enlaces:
        lineas.append(f"[Resultado en JSON]({enlaces['resultado']})")
    if sesion:
        cuantos = f" ({n_sesion} ejercicio{'s' if n_sesion != 1 else ''})" if n_sesion else ""
        lineas.append(f"[Reporte combinado de la sesión{cuantos}]({sesion})")
    return "\n\n".join(lineas)


async def _calcular(metodo: Metodo, s: Any, detalle: Detalle, ctx: Context | None) -> CallToolResult:
    """Común a las tres herramientas: calcula en un proceso aparte (HTML y PNG como bytes, en
    memoria), publica en grupo06/<id>/ y actualiza el reporte combinado de la sesión
    (core.motor.publicar), y arma la respuesta."""
    if ctx is not None:
        await ctx.info(f"Verificando y resolviendo con el método de {metodo}…")
    id_ = almacen.nuevo_id(metodo)
    r = await ejecutor.correr(metodo, s.model_dump(mode="json"))
    if not r.get("ok"):
        e = r["error"]
        # ToolError ⇒ el cliente recibe is_error=true y el LLM lee el texto para explicárselo al usuario.
        raise ToolError(json.dumps({"ok": False, "metodo": metodo, **e}, ensure_ascii=False))
    r["artefactos"] = _artefactos(r.get("artefactos"))
    descripcion = _descripcion(metodo, s)
    avisos: list[str] = []
    sesion: str | None = None
    n_sesion: int | None = None
    try:
        pub = await asyncio.to_thread(publicar, almacen, id_, metodo, descripcion, r, s.enunciado or descripcion)
        enlaces, sesion, n_sesion = pub["archivos"], pub["sesion"], pub.get("n_sesion")
        avisos.extend(pub["avisos"])
    except ErrorAlmacen as e:                        # el cálculo es válido aunque no se haya podido publicar
        log.error("No se pudo guardar %s: %s", id_, e)
        enlaces = {}
        avisos.append(f"Los archivos no se pudieron publicar ({e}). El resultado de abajo es correcto; "
                      "vuelve a intentarlo más tarde para obtener los enlaces.")
    png = _miniatura(r["artefactos"].get("png")) if s.salida.incluir_imagen else None

    md = _markdown(metodo, enlaces, sesion, n_sesion)
    datos: dict[str, Any] = {
        "ok": True,
        "metodo": metodo,
        "id_resultado": id_,
        "resumen": r["resumen"],
        "verificacion_previa": r["verificacion_previa"],
        "resultado": r["resultado"] if detalle == "completo" else compactar(r["resultado"]),
        "archivos": enlaces,
        "reporte_sesion": sesion,
        "markdown": md,
        "tiempo_s": r["tiempo_s"],
        **({"advertencias": avisos} if avisos else {}),
        **({"datos_grafico": r["datos_grafico"]} if "datos_grafico" in r else {}),
    }
    texto = "\n".join([md, "", "Resumen:", *[f"- {x}" for x in r["resumen"]], *[f"- ⚠ {a}" for a in avisos]])
    contenido: list[TextContent | ImageContent] = [
        TextContent(type="text", text=texto.strip()),
        TextContent(type="text", text=json.dumps(datos, ensure_ascii=False)),
    ]
    if png:                                          # respaldo: el cliente ve el gráfico aunque no abra la URL
        contenido.append(ImageContent(type="image", data=base64.b64encode(png).decode("ascii"), mime_type="image/png"))
    return CallToolResult(content=contenido, structured_content=datos)


_DETALLE = Annotated[Detalle, Field(description="'compacto' (por defecto) omite el LaTeX y los pasos (quedan en "
                                                "resultado.json y en el HTML); 'completo' lo devuelve todo.")]
_ANOT_CALCULO = dict(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)


# ════════════════════════════════════════════════════════════════════════════
# Herramientas (Tools). El docstring ES la descripción que lee el LLM para decidir.
# ════════════════════════════════════════════════════════════════════════════
@mcp.tool(title="Diagnosticar qué método usar",
          annotations=ToolAnnotations(title="Diagnosticar problema", read_only_hint=True, idempotent_hint=True,
                                      open_world_hint=False))
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
                                      ctx: Context | None = None) -> CallToolResult:
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
    clasificación), enlaces públicos en Markdown (reporte HTML interactivo + gráfico PNG) y la
    imagen del gráfico como bloque Image.
    Errores de verificación típicos: RESTRICCION_IMPOSIBLE, SOBREDETERMINADO, DIVISION_POR_CERO.
    """
    return await _calcular("lagrange", solicitud, detalle, ctx)


@mcp.tool(title="Puntos críticos y Hessiana",
          annotations=ToolAnnotations(title="Puntos críticos y matriz Hessiana", **_ANOT_CALCULO))
async def analizar_puntos_criticos(solicitud: SolicitudHessiana, detalle: _DETALLE = "compacto",
                                   ctx: Context | None = None) -> CallToolResult:
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

    Devuelve: id_resultado, resumen, verificación previa, resultado, enlaces públicos en Markdown
    (reporte HTML con superficie 3D, curvas de nivel y flujo del gradiente + gráfico PNG) y la imagen. Errores típicos: FUNCION_CONSTANTE,
    DIVISION_POR_CERO, HESSIANA_NO_CUADRADA, DEMASIADAS_VARIABLES.
    """
    return await _calcular("hessiana", solicitud, detalle, ctx)


@mcp.tool(title="Curva: triedro de Frenet, curvatura y torsión",
          annotations=ToolAnnotations(title="Triedro de Frenet", **_ANOT_CALCULO))
async def analizar_curva_frenet(solicitud: SolicitudFrenet, detalle: _DETALLE = "compacto",
                                ctx: Context | None = None) -> CallToolResult:
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
          annotations=ToolAnnotations(title="Listar resultados", read_only_hint=True, open_world_hint=False))
async def listar_resultados(metodo: Annotated[Metodo | None, Field(description="Filtra por método (opcional).")] = None,
                            limite: Annotated[int, Field(ge=1, le=100, description="Máximo de resultados.")] = 20
                            ) -> dict[str, Any]:
    """Lista los cálculos ya realizados (más recientes primero) con su id, método, fecha y una
    descripción. Úsala cuando el usuario pregunte por un ejercicio anterior ("¿qué salió en el de
    la hélice?", "muéstrame el último de Lagrange") y luego llama a obtener_resultado con el id."""
    try:
        return {"resultados": await asyncio.to_thread(almacen.listar, metodo, limite), "almacen": almacen.descripcion}
    except ErrorAlmacen as e:
        raise ToolError(json.dumps({"ok": False, "codigo": "ALMACEN_NO_DISPONIBLE", "mensaje": str(e),
                                    "sugerencia": "Verifica que SeaweedFS esté en línea."}, ensure_ascii=False)) from e


@mcp.tool(title="Obtener un resultado guardado",
          annotations=ToolAnnotations(title="Obtener resultado", read_only_hint=True, open_world_hint=False))
async def obtener_resultado(solicitud: SolicitudConsulta, detalle: _DETALLE = "compacto") -> dict[str, Any]:
    """Recupera un cálculo guardado por su id_resultado: la entrada, el resultado exacto, el
    resumen y los enlaces públicos de sus archivos (HTML, PNG). Evita recalcular lo ya resuelto."""
    try:
        r = await asyncio.to_thread(almacen.obtener, solicitud.id_resultado)
    except ErrorAlmacen as e:
        raise ToolError(json.dumps({"ok": False, "codigo": "ALMACEN_NO_DISPONIBLE", "mensaje": str(e),
                                    "sugerencia": "Verifica que SeaweedFS esté en línea."}, ensure_ascii=False)) from e
    except KeyError as e:
        raise ToolError(json.dumps({"ok": False, "codigo": "NO_ENCONTRADO", "mensaje": str(e).strip("'\""),
                                    "sugerencia": "Usa listar_resultados para ver los ids disponibles."},
                                   ensure_ascii=False)) from e
    if detalle == "compacto" and r.get("resultado"):
        r["resultado"] = compactar(r["resultado"])
    r["markdown"] = _markdown(str(r.get("metodo")), r.get("archivos", {}))
    return r


@mcp.tool(title="Combinar varios ejercicios en un solo reporte",
          annotations=ToolAnnotations(title="Reporte combinado", read_only_hint=False, destructive_hint=False,
                                      idempotent_hint=False, open_world_hint=False))
async def combinar_reportes(solicitud: SolicitudCombinar) -> dict[str, Any]:
    """REPORTE COMBINADO — reúne en UNA página HTML los reportes de varios ejercicios YA resueltos.

    NO hace falta para el reporte de la sesión: ese se actualiza SOLO después de cada cálculo
    (grupo06/lote-sesion-actual/reporte_combinado.html). Usa esta herramienta únicamente cuando el
    usuario pida un reporte APARTE con ejercicios concretos (por ejemplo, solo los de una tarea, o
    ejercicios resueltos otro día: búscalos con listar_resultados), en el orden que él indique.

    Qué hace: copia el reporte completo de cada ejercicio (sus 5 pestañas: Resumen, Procedimiento,
    Gráfico 3D, Gráficos 2D y JSON) dentro de una sola página con barra de navegación
    «← Anterior / Siguiente ejercicio →», índice y atajos de teclado. NO recalcula nada ni modifica
    los reportes individuales. Lo publica en su propio prefijo:
    grupo06/lote-AAAAMMDD-HHMMSS-xxxxxxxx/reporte_combinado.html (+ lote.json).

    Pasa en 'enunciados' el texto de cada ejercicio (mismo orden) para que se vea en el índice.
    Devuelve: id_lote, la lista de ejercicios incluidos, la URL pública del HTML combinado y su Markdown.
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
async def recurso_resultado(id_resultado: str) -> str:
    try:
        return json.dumps(await asyncio.to_thread(almacen.obtener, id_resultado), ensure_ascii=False, indent=2)
    except (KeyError, ErrorAlmacen) as e:
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


@mcp.custom_route("/salud", methods=["GET"])
async def salud(_request: Any) -> Any:
    """Sonda para Docker/Caddy: GET /salud → 200 si el proceso responde."""
    from starlette.responses import JSONResponse
    return JSONResponse({"ok": True, "servidor": NOMBRE_SERVIDOR, "transporte": TRANSPORTE,
                         "almacen": almacen.descripcion, "trabajadores": N_TRABAJADORES})


def main() -> None:
    """Arranca el servidor. En el contenedor: streamable-http en 0.0.0.0:8000 (red Docker lab_net)."""
    ap = argparse.ArgumentParser(description=f"Servidor MCP {NOMBRE_SERVIDOR}")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--stdio", action="store_true", help="transporte STDIO (solo para pruebas locales)")
    g.add_argument("--http", action="store_true", help="transporte streamable-http en 0.0.0.0:8000 (por defecto)")
    ap.parse_args()
    almacen.preparar()                # ensure_bucket(): tolera que SeaweedFS todavía esté arrancando
    if USAR_PROCESOS:
        ejecutor.iniciar()            # arranca (y precarga SymPy) ANTES de abrir el canal
    try:
        if TRANSPORTE == "stdio":
            log.info("%s listo (STDIO) · almacén: %s · %d trabajador(es)", NOMBRE_SERVIDOR, almacen.descripcion,
                     N_TRABAJADORES)
            mcp.run(transport="stdio")
            return
        log.info("%s arrancando en http://%s:%s%s · almacén: %s · %d trabajador(es) · stateless=%s",
                 NOMBRE_SERVIDOR, os.environ.get("MCP_HOST") or HOST, os.environ.get("MCP_PORT") or PUERTO,
                 RUTA_HTTP, almacen.descripcion, N_TRABAJADORES, SIN_ESTADO)
        try:
            mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
        except TypeError as e:
            # Un SDK cuyo run() no acepte host/port: se pasan por variables de entorno y se arranca igual.
            if "unexpected keyword" not in str(e) and "keyword argument" not in str(e):
                raise
            log.info("run() no acepta host/port en este SDK (%s); se usan MCP_HOST/MCP_PORT.", e)
            os.environ.update({"MCP_HOST": os.environ.get("MCP_HOST") or HOST,
                               "MCP_PORT": os.environ.get("MCP_PORT") or str(PUERTO)})
            arrancar = getattr(mcp, "run")
            arrancar(transport="streamable-http")
    finally:
        ejecutor.cerrar()


if __name__ == "__main__":
    main()
