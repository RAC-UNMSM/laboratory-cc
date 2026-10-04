"""Servidor MCP del agente de EDOs del grupo 09. Transporte stdio.

Claude interpreta el pedido del usuario y llama a estas herramientas; el
servidor calcula, verifica y devuelve resultados estructurados; Claude redacta
la explicación final a partir de ellos.

Registro en Claude Code (desde esta carpeta):

    claude mcp add edos-grupo09 -- python mcp_server.py

Prueba con el inspector:

    npx @modelcontextprotocol/inspector python mcp_server.py

Sobre stdout: en el transporte stdio, stdout es el canal del protocolo JSON-RPC.
Cualquier `print` de una dependencia lo corrompería, así que el cuerpo de cada
herramienta se ejecuta con stdout redirigido a stderr.
"""

import contextlib
import functools
import hashlib
import io
import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

import storage
from orquestacion.capacidades import analizar_edo as _analizar_edo
from orquestacion.capacidades import analizar_equilibrios_sistema as _analizar_equilibrios
from orquestacion.capacidades import describir_capacidades
from orquestacion.catalogo import cargar_catalogo
from orquestacion.informe import MODO as MODO_INFORME
from orquestacion.informe import SESION

def _revision():
    """Huella corta del código que está corriendo.

    Existe porque un cliente MCP arranca el servidor una vez y lo deja vivo: tras
    editar el código es fácil creer que se está probando lo nuevo cuando el
    proceso sigue siendo el de antes, y el síntoma es un comportamiento viejo sin
    ninguna pista de por qué. Con esto basta pedir `ping` y comparar.
    """
    raiz = Path(__file__).resolve().parent
    resumen = hashlib.sha256()
    for archivo in sorted(raiz.rglob("*.py")) + sorted(raiz.rglob("*.html")):
        if "__pycache__" in archivo.parts or "tests" in archivo.parts:
            continue
        resumen.update(archivo.read_bytes())
    return resumen.hexdigest()[:8]


REVISION = _revision()

# El log va a stderr: stdout está reservado para el protocolo.
logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
registro = logging.getLogger("edos-grupo09")

# Prepara el bucket de visualizaciones. Falla en silencio si no hay storage
# (ejecución local por stdio): el HTML se sigue mandando inline.
storage.ensure_bucket()

servidor = MCPServer(
    name="edos-grupo09",
    title="Agente de EDOs y sistemas dinámicos (grupo 09)",
    instructions=(
        "Resuelve y analiza ecuaciones diferenciales ordinarias de 1 a 3 variables.\n\n"
        "QUÉ ESTÁ IMPLEMENTADO: integración numérica con control de error, y el "
        "análisis de estabilidad (equilibrios exactos, Jacobiano, autovalores y "
        "clasificación).\n\n"
        "QUÉ HERRAMIENTA USAR: `resolver_graficar_y_analizar_edo` cuando haya condición inicial y se "
        "quiera la trayectoria. `analizar_equilibrios` cuando la pregunta sea sobre "
        "equilibrios, estabilidad o una bifurcación y NO haya condición inicial: así "
        "no hay que inventar una trayectoria que nadie pidió. Para una bifurcación, "
        "llame a `analizar_equilibrios` varias veces variando el parámetro.\n\n"
        "QUÉ NO ESTÁ IMPLEMENTADO TODAVÍA. Si el usuario pide algo de esta lista, "
        "dígaselo claramente en vez de ofrecer un sustituto como si fuera la "
        "respuesta:\n"
        "  - Exponente de Lyapunov, secciones de Poincaré, cuantificación del caos "
        "(pida analisis=['caos'] y el servidor devolverá el detalle de lo pendiente).\n"
        "  - Diagramas de bifurcación y barridos paramétricos automáticos "
        "(analisis=['bifurcaciones']). Sí se puede, mientras tanto, llamar varias "
        "veces con distintos valores del parámetro: cada llamada da los equilibrios "
        "exactos y su estabilidad para ese valor.\n"
        "  - Resolución ANALÍTICA o simbólica (analisis=['solucion_analitica']). El "
        "agente integra numéricamente; no deriva soluciones cerradas. Si el usuario "
        "pide 'resuélvelo analíticamente', no presente el resultado numérico como si "
        "fuera la solución simbólica.\n\n"
        "MAPAS ITERADOS: fuera de alcance, y hay que declararlo. El parámetro "
        "`tipo_de_sistema` existe porque x_{n+1} = f(x_n) y dx/dt = f(x) se escriben "
        "con el mismo lado derecho, así que el servidor no puede distinguirlos: quien "
        "lo sabe es el usuario. Si el enunciado usa notación de recurrencia (x_{n+1}, "
        "x_n, 'iterar', 'el mapa logístico'), declare tipo_de_sistema='mapa_discreto' "
        "y el servidor dirá que está fuera de alcance. Si no puede determinarlo del "
        "enunciado, declare 'no_estoy_seguro': el servidor devolverá la pregunta que "
        "hay que hacerle al usuario, con las dos opciones y sus consecuencias. "
        "PREGUNTE al usuario en ese caso, no adivine: el mapa logístico con r=3.8 es "
        "caótico, mientras que la EDO continua con el mismo lado derecho converge a un "
        "equilibrio. Los problemas 4.1 a 4.3 y 5.3 del balotario son mapas.\n\n"
        "Si una respuesta llega con etapa='aclaracion_necesaria', no reintente con una "
        "suposición: traslade la pregunta al usuario y vuelva a llamar con su respuesta.\n\n"
        "CÓMO ESCRIBIR EL SISTEMA: forma explícita de primer orden x' = F(t, x), una "
        "expresión por variable de estado. Una EDO de orden n se reduce antes a un "
        "sistema de n ecuaciones; por ejemplo theta'' = -sin(theta) se escribe como "
        "ecuaciones=['v', '-sin(theta)'] con variables_estado=['theta', 'v'].\n\n"
        "VERIFICACIÓN: toda respuesta trae un bloque `verificacion`. Si `ok` es false, "
        "el servidor no entrega conclusiones y hay que explicar al usuario qué "
        "comprobación falló en lugar de interpretar números inválidos.\n\n"
        "NO REHAGA EL CÁLCULO POR SU CUENTA. No vuelva a integrar el sistema con "
        "scipy, ni dibuje la figura con matplotlib, ni escriba código para "
        "reproducir lo que esta herramienta ya devolvió. El servidor ya integró "
        "con control de error y pasó la solución por cinco verificaciones "
        "independientes; una trayectoria que usted reintegre aparte NO pasó por "
        "ese portón, así que presentarla al usuario deshace la única garantía que "
        "este agente ofrece. Si lo que le falta es una imagen que el usuario pueda "
        "ver, ya existe: es el informe, y basta con darle el enlace.\n\n"
        "Lo que sí le toca a usted es redactar: interpretar los equilibrios, "
        "explicar la dinámica y relacionar los números con la matemática del "
        "problema. Los números salen de la respuesta, no de un cálculo suyo.\n\n"
        "AL EMPEZAR UNA CONVERSACIÓN, LLAME A `nuevo_informe`. Este servidor sigue "
        "vivo entre conversaciones: no se reinicia con cada chat. Si no lo llama, "
        "las preguntas de este chat se acumulan en el mismo documento que las del "
        "anterior y el usuario ve un informe que no empieza de cero. Una sola vez, "
        "antes del primer análisis, y le devuelve ya el enlace que hay que "
        "entregarle.\n\n"
        "EL INFORME ENSEÑA LA ÚLTIMA PREGUNTA, no un historial: cada análisis "
        "reemplaza al anterior en el mismo documento y en la misma dirección. El "
        "usuario puede dejar la pestaña abierta toda la conversación. Si el laboratorio "
        "lo configuró en modo acumulativo (lo dirá `informe` en su campo `modo`), las "
        "secciones se apilan con la más reciente arriba.\n\n"
        "EL INFORME ES LA ÚNICA FORMA EN QUE EL USUARIO VE SU TRABAJO. Ningún "
        "cliente de chat dibuja el HTML que devuelve una herramienta: ese HTML es "
        "texto que usted lee, no una figura que el usuario vea. Lo que sí puede "
        "abrir es un enlace. Por eso cada análisis se agrega a un informe de la "
        "conversación, y su dirección vuelve en `visualizacion.informe`.\n\n"
        "  - ENTREGUE ESA DIRECCIÓN AL USUARIO la primera vez que aparezca, como "
        "enlace markdown: `[Ver el informe](<direccion>)`. Dígale que puede dejar "
        "la pestaña abierta: la página se recarga sola y los análisis siguientes "
        "van apareciendo ahí.\n"
        "  - Es una dirección fija para toda la conversación. No la repita en cada "
        "respuesta; vuelva a darla solo si el usuario la pide o la pierde.\n"
        "  - Es una URL: dese tal cual, como enlace markdown, para que se abra con "
        "un clic. Una dirección 127.0.0.1 es del propio equipo del usuario y "
        "funciona igual. Solo si llegara una ruta de archivo (el servidor no pudo "
        "abrir su puerto) hay que decirle que abra ese archivo a mano.\n"
        "  - `informe` como herramienta devuelve la dirección en cualquier momento, "
        "y sirve para dársela ANTES del primer análisis si el usuario quiere mirar "
        "cómo se va llenando.\n\n"
        "Use `ping` para obtener el inventario exacto de capacidades y pendientes."),
)


def sin_contaminar_stdout(funcion):
    """Protege el canal del protocolo de cualquier `print` de una dependencia."""
    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        capturado = io.StringIO()
        try:
            with contextlib.redirect_stdout(capturado):
                return funcion(*args, **kwargs)
        finally:
            escrito = capturado.getvalue()
            if escrito:
                registro.warning("Se descartó salida a stdout: %r", escrito[:500])
    return envoltura


@servidor.tool(
    description="Comprueba que el servidor responde y describe qué sabe hacer hoy. "
                "Úsalo para verificar la conexión antes de un análisis largo.")
@sin_contaminar_stdout
def ping() -> dict:
    """Latido del servidor, con la versión y el inventario de capacidades."""
    return {
        "ok": True,
        "servidor": "edos-grupo09",
        "revision": REVISION,
        "transporte": "stdio",
        "informe": {"modo": MODO_INFORME,
                    "nota": ("Cada análisis reemplaza al anterior: el informe enseña "
                             "solo la última pregunta."
                             if MODO_INFORME != "acumula" else
                             "Las secciones se acumulan, la más reciente arriba.")},
        "mensaje": "El agente de EDOs responde.",
        "capacidades": describir_capacidades(),
    }


@servidor.tool(
    description="Abre un informe nuevo y vacío para esta conversación. Llámalo UNA vez, "
                "al empezar un chat, antes del primer análisis: el servidor sigue vivo "
                "entre conversaciones y si no, las preguntas de chats distintos se "
                "acumulan en el mismo documento.")
@sin_contaminar_stdout
def nuevo_informe() -> dict:
    """Cierra el informe en curso y empieza uno limpio.

    Hace falta porque el cliente MCP levanta este servidor **una vez** y lo
    mantiene vivo para todas las conversaciones: sin esto, el informe nunca
    empieza de cero. El protocolo no le dice al servidor en qué conversación
    está, así que quien lo sabe es usted.

    No se pierde nada: el informe anterior queda en su archivo, con la fecha y
    la hora en el nombre.

    Returns:
        `destino` con la dirección del informe nuevo, ya vacío y listo para que
        el usuario lo abra desde el principio.
    """
    destino = SESION.empezar_de_nuevo()
    return {"ok": bool(destino), "destino": destino, **SESION.estado(),
            "nota": "Informe nuevo y vacío. Entréguele el enlace al usuario: puede "
                    "dejarlo abierto y verá aparecer cada análisis."}


@servidor.tool(
    description="Devuelve el enlace a la página donde el usuario VE sus gráficas, ya "
                "dibujadas por este servidor. Se actualiza sola con cada análisis. "
                "Úsala para darle el enlace, incluso antes del primer análisis.")
@sin_contaminar_stdout
def informe() -> dict:
    """Dónde está el informe de la sesión y qué lleva acumulado.

    El informe existe porque el HTML que devuelve una herramienta no lo dibuja
    ningún cliente de chat. Esta herramienta entrega la dirección que el usuario
    sí puede abrir, y la publica vacía si todavía no hay ningún análisis, para
    que pueda dejar la pestaña abierta desde el principio.

    Returns:
        `destino` con la URL o la ruta del archivo, `es_url` para distinguirlas,
        `analisis_registrados` y los `titulos` ya incluidos.
    """
    destino = SESION.asegurar_publicado()
    estado = SESION.estado()
    if not destino:
        return {**estado, "ok": False,
                "nota": "No se pudo publicar el informe: no hay storage y tampoco se "
                        "pudo escribir el archivo local."}
    return {
        **estado, "ok": True,
        "nota": ("Entréguele esta dirección al usuario como enlace markdown. La "
                 "página se recarga sola, así que puede dejarla abierta mientras "
                 "siguen trabajando."
                 if estado["es_url"] else
                 "No se pudo servir por http, así que es una ruta de archivo: dígale "
                 "al usuario que la abra a mano."),
    }


@servidor.tool(
    name="resolver_graficar_y_analizar_edo",
    description="USA ESTA HERRAMIENTA, NO ESCRIBAS CÓDIGO, siempre que haya que "
                "resolver numéricamente una EDO o un sistema de EDOs con condición "
                "inicial, graficar x(t), dibujar un plano de fase o retrato de fase, "
                "un campo de direcciones, una línea de fase o una trayectoria 3D, "
                "encontrar o clasificar puntos de equilibrio, o estudiar estabilidad, "
                "ciclos límite, atractores y sensibilidad a condiciones iniciales. "
                "Hace todo eso de una sola llamada: integra con control de error "
                "(RK45, DOP853, Radau, BDF, LSODA), resuelve F(x)=0 de forma exacta "
                "con sympy, calcula Jacobiano y autovalores, verifica la solución con "
                "cinco pruebas independientes y genera las figuras. "
                "NO uses scipy, solve_ivp ni matplotlib para esto: lo que calcules por "
                "tu cuenta no pasa por esas verificaciones y no debe mostrarse al "
                "usuario como resultado. Reduce EDOs de orden n a sistemas de primer "
                "orden antes de llamarla.")
@sin_contaminar_stdout
def analizar_edo(
    ecuaciones: list[str],
    variables_estado: list[str],
    y0: list[float],
    intervalo: list[float],
    variable_independiente: str = "t",
    parametros: dict[str, float] | None = None,
    analisis: list[str] | None = None,
    equilibrios: list[list[float]] | None = None,
    solucion_exacta: str | None = None,
    metodo: str = "RK45",
    rtol: float = 1e-8,
    atol: float = 1e-10,
    puntos: int = 400,
    visualizar: bool = True,
    titulo: str | None = None,
    tipo_de_sistema: str = "edo_continua",
) -> dict:
    """Recorre validar → resolver → verificar → analizar → visualizar.

    Args:
        ecuaciones: Lado derecho de x' = F(t, x), una expresión por variable de
            estado, en el mismo orden. Se escriben con `**` para la potencia y
            pueden usar sin, cos, tan, exp, log, sqrt, sinh, cosh, tanh, Abs,
            sign, pi. Ejemplos: ["-2*y"], ["r*y*(1 - y/K)"],
            ["v", "-w0**2*sin(theta)"].
        variables_estado: Nombres de las variables de estado, de 1 a 3.
        y0: Condición inicial, un valor por variable de estado.
        intervalo: Par [t_inicial, t_final] con t_final > t_inicial.
        variable_independiente: Nombre de la variable independiente. Usa "x"
            cuando el problema está escrito como dy/dx.
        parametros: Valores de los parámetros con nombre que usan las ecuaciones,
            por ejemplo {"r": 1.0, "K": 10.0}. Todo nombre que aparezca en las
            ecuaciones y no sea variable de estado debe estar aquí.
        analisis: Análisis a ejecutar. Implementado: "estabilidad". Reconocidos
            pero PENDIENTES de implementación, que informan qué falta en lugar
            de devolver números: "caos" (Lyapunov, Poincaré, sensibilidad),
            "bifurcaciones" (barridos y ramas) y "solucion_analitica"
            (resolución simbólica). Se aceptan alias naturales: "lyapunov" y
            "poincare" se resuelven a "caos", "hopf" y "barrido" a
            "bifurcaciones", "simbolica" a "solucion_analitica". Por defecto
            ["estabilidad"].
        equilibrios: Equilibrios a clasificar. Si se omite, se resuelven de forma
            exacta con sympy cuando el sistema es autónomo.
        solucion_exacta: Solución analítica conocida, en función de la variable
            independiente, para contrastarla con la numérica. Ejemplo:
            "exp(-2*t)". Si no coincide, la verificación falla y no se emiten
            conclusiones.
        metodo: Integrador de SciPy. Opciones: RK45, RK23, DOP853, Radau, BDF,
            LSODA. Radau o BDF para problemas rígidos.
        rtol: Tolerancia relativa del integrador.
        atol: Tolerancia absoluta del integrador.
        puntos: Puntos de la malla de salida.
        visualizar: Generar la visualización HTML interactiva.
        titulo: Título para la gráfica y el reporte.
        tipo_de_sistema: Cómo planteó el usuario el problema. Importa porque
            x_{n+1} = r*x_n*(1-x_n) y dx/dt = r*x*(1-x) se escriben con el
            mismo lado derecho pero tienen dinámicas distintas, y el servidor
            no puede distinguirlos solo. Valores:
              - "edo_continua" (por defecto): el usuario planteó una ecuación
                diferencial, con derivadas respecto de un tiempo continuo.
              - "mapa_discreto": el usuario planteó una recurrencia o iteración
                (notación x_{n+1}, x_n, "iterar", "el mapa logístico"). Está
                fuera de alcance y el servidor lo dirá en vez de calcular.
              - "no_estoy_seguro": no se puede determinar del enunciado. El
                servidor devolverá la pregunta que hay que hacerle al usuario,
                con las dos opciones y sus consecuencias, en lugar de un
                resultado. Úselo en vez de adivinar.

    Returns:
        Si `ok` es true: `configuracion` (para reproducir el cálculo),
        `solucion` (malla, estado inicial y final), `verificacion` (el detalle de
        cada comprobación), `analisis` y `visualizacion` con el HTML.

        Si `visualizacion` trae un campo `url`, es la visualización interactiva
        que este servidor acaba de generar y publicar en el storage del
        laboratorio (mismo dominio que este MCP), a máxima resolución.
        Entrégala al usuario como enlace markdown, por ejemplo
        `[Ver la visualización interactiva](<url>)`, en vez de solo
        describirla: ningún cliente de chat ofrece ese enlace por su cuenta a
        partir del resultado de la tool. Cuando además venga `html_omitido`,
        el documento no entró inline y el enlace es la única forma de verlo.
        Si `ok` es false: `etapa` y `error`, y ninguna conclusión. Las etapas
        posibles son validacion_solicitud, compilacion, resolucion y verificacion.

        Nota sobre sistemas caóticos: la verificación compara punto a punto solo
        en el tramo inicial. Si dos integraciones coinciden al principio y se
        separan después, se reporta `sensibilidad_detectada` y es un hallazgo
        legítimo, no un fallo.
    """
    registro.info("analizar_edo: %s variables, intervalo %s", len(variables_estado), intervalo)
    return _analizar_edo({
        "ecuaciones": ecuaciones,
        "variables_estado": variables_estado,
        "y0": y0,
        "intervalo": intervalo,
        "variable_independiente": variable_independiente,
        "parametros": parametros or {},
        "analisis": analisis or ["estabilidad"],
        "equilibrios": equilibrios,
        "solucion_exacta": solucion_exacta,
        "metodo": metodo,
        "rtol": rtol,
        "atol": atol,
        "puntos": puntos,
        "visualizar": visualizar,
        "titulo": titulo,
        "tipo_de_sistema": tipo_de_sistema,
    })


@servidor.tool(
    description="USA ESTA HERRAMIENTA, NO ESCRIBAS CÓDIGO, para encontrar y clasificar "
                "puntos de equilibrio y su estabilidad (nodo, silla, foco, centro, "
                "estable o inestable) con Jacobiano y autovalores, SIN integrar ninguna "
                "trayectoria. Es la indicada cuando la pregunta es sobre equilibrios, "
                "estabilidad o bifurcaciones y NO hay condición inicial; si la hay, usa "
                "`resolver_graficar_y_analizar_edo`, que también los clasifica. Para una bifurcación, "
                "llámala varias veces variando el parámetro.")
@sin_contaminar_stdout
def analizar_equilibrios(
    ecuaciones: list[str],
    variables_estado: list[str],
    variable_independiente: str = "t",
    parametros: dict[str, float] | None = None,
    equilibrios: list[list[float]] | None = None,
    tipo_de_sistema: str = "edo_continua",
) -> dict:
    """Resuelve F(x)=0 de forma exacta y clasifica cada equilibrio.

    Use esta herramienta en lugar de `resolver_graficar_y_analizar_edo` cuando el enunciado pregunte
    por equilibrios, estabilidad o una bifurcación y **no** dé una condición
    inicial. Pedir aquí no obliga a inventar una trayectoria.

    Para estudiar una bifurcación, llame varias veces variando el parámetro de
    interés: cada llamada da los equilibrios exactos y su estabilidad para ese
    valor. El barrido automático está pendiente de implementación.

    Args:
        ecuaciones: Lado derecho de x'=F(x), una expresión por variable de
            estado. El sistema debe ser autónomo: si depende de la variable
            independiente, sus equilibrios no están definidos.
        variables_estado: Nombres de las variables de estado, de 1 a 3.
        variable_independiente: Nombre de la variable independiente.
        parametros: Valores de los parámetros que usan las ecuaciones.
        equilibrios: Equilibrios a clasificar. Si se omite, se resuelven F(x)=0
            de forma exacta con sympy.
        tipo_de_sistema: Igual que en `resolver_graficar_y_analizar_edo`; vea su documentación.

    Returns:
        Si `ok` es true: `analisis.estabilidad.equilibrios` con el punto, su
        clasificación, sus autovalores y el Jacobiano, más `verificacion`, que
        comprueba que cada punto anule de verdad el campo. Si `ok` es false,
        `etapa` dice qué no se superó y no hay conclusiones.
    """
    registro.info("analizar_equilibrios: %s variables, parametros=%s",
                  len(variables_estado), sorted((parametros or {})))
    return _analizar_equilibrios({
        "ecuaciones": ecuaciones,
        "variables_estado": variables_estado,
        "variable_independiente": variable_independiente,
        "parametros": parametros or {},
        "equilibrios": equilibrios,
        "tipo_de_sistema": tipo_de_sistema,
    })


@servidor.tool(
    description="Lista los problemas del balotario del grupo, que sirven como vara de "
                "nivel y como casos de referencia ya resueltos.")
@sin_contaminar_stdout
def listar_balotario(tema: str | None = None, incluir_solucion: bool = False) -> dict:
    """Problemas del balotario con su ecuación y condiciones iniciales.

    Args:
        tema: Identificador de un tema concreto, por ejemplo "tema_01". Si se
            omite, se listan todos los temas disponibles.
        incluir_solucion: Incluir la solución esperada de cada problema. Son las
            respuestas del balotario, útiles para contrastar un cálculo propio.

    Returns:
        Los temas con sus problemas. Cada problema trae id, enunciado, tipo,
        dificultad, el bloque `ecuacion` listo para pasar a `resolver_graficar_y_analizar_edo`, y sus
        condiciones iniciales. El campo `ci_derivada` indica si la condición
        inicial viene del enunciado original o se fijó para concretar un PVI.
    """
    temas = cargar_catalogo()
    if tema is not None:
        temas = [t for t in temas if t["tema"]["id"] == tema]
        if not temas:
            return {"ok": False,
                    "error": f"No existe el tema {tema!r}.",
                    "disponibles": [t["tema"]["id"] for t in cargar_catalogo()]}
    salida = []
    for contenido in temas:
        problemas = []
        for problema in contenido["problemas"]:
            resumen = {clave: problema.get(clave) for clave in
                       ("id", "titulo", "enunciado", "tipo", "dificultad",
                        "ecuacion", "condiciones_iniciales")}
            if incluir_solucion:
                resumen["solucion_esperada"] = problema.get("solucion_esperada")
            problemas.append(resumen)
        salida.append({"tema": contenido["tema"], "problemas": problemas})
    return {"ok": True, "temas": salida,
            "nota": "Las ecuaciones vienen en forma de sistema de primer orden: "
                    "`campo`, `variables_estado` y `variable_independiente` se pasan "
                    "tal cual. Un problema CON `condiciones_iniciales` va a "
                    "`resolver_graficar_y_analizar_edo`; uno SIN ellas (las familias paramétricas del "
                    "Tema 3) va a `analizar_equilibrios`, usando el `parametros` de "
                    "cada caso de su `solucion_esperada`. Los que traen "
                    "`verificable_con_solver: false` no son resolubles por este "
                    "motor y dicen por qué en `motivo_no_verificable`."}


def main():
    """Arranca el servidor sobre stdio."""
    registro.info("Iniciando servidor MCP edos-grupo09 sobre stdio")
    servidor.run(transport="stdio")


if __name__ == "__main__":
    main()
