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
herramienta se ejecuta con stdout redirigido a stderr. `server.py` (la demo por
terminal) conserva sus `print` y sigue funcionando aparte.
"""

import contextlib
import functools
import io
import json
import logging
import sys

from mcp.server.mcpserver import MCPServer

from orquestacion.capacidades import analizar_edo as _analizar_edo
from orquestacion.capacidades import analizar_equilibrios_sistema as _analizar_equilibrios
from orquestacion.capacidades import describir_capacidades
from orquestacion.catalogo import cargar_catalogo
from orquestacion.contratos import ANALISIS_DISPONIBLES, METODOS

# El log va a stderr: stdout está reservado para el protocolo.
logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
registro = logging.getLogger("edos-grupo09")

servidor = MCPServer(
    name="edos-grupo09",
    title="Agente de EDOs y sistemas dinámicos (grupo 09)",
    instructions=(
        "Resuelve y analiza ecuaciones diferenciales ordinarias de 1 a 3 variables.\n\n"
        "QUÉ ESTÁ IMPLEMENTADO: integración numérica con control de error, y el "
        "análisis de estabilidad (equilibrios exactos, Jacobiano, autovalores y "
        "clasificación).\n\n"
        "QUÉ HERRAMIENTA USAR: `analizar_edo` cuando haya condición inicial y se "
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
        "transporte": "stdio",
        "mensaje": "El agente de EDOs responde.",
        "capacidades": describir_capacidades(),
    }


@servidor.tool(
    description="Resuelve y analiza un problema de valor inicial de EDOs, verificando "
                "el resultado antes de emitir conclusiones. Devuelve datos "
                "estructurados y una visualización HTML.")
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
    description="Clasifica los equilibrios y su estabilidad SIN integrar ninguna "
                "trayectoria. Úsalo cuando la pregunta sea sobre equilibrios, "
                "estabilidad o bifurcaciones y no haya condición inicial.")
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

    Use esta herramienta en lugar de `analizar_edo` cuando el enunciado pregunte
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
        tipo_de_sistema: Igual que en `analizar_edo`; vea su documentación.

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
        dificultad, el bloque `ecuacion` listo para pasar a `analizar_edo`, y sus
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
                    "`analizar_edo`; uno SIN ellas (las familias paramétricas del "
                    "Tema 3) va a `analizar_equilibrios`, usando el `parametros` de "
                    "cada caso de su `solucion_esperada`. Los que traen "
                    "`verificable_con_solver: false` no son resolubles por este "
                    "motor y dicen por qué en `motivo_no_verificable`."}


@servidor.resource("balotario://temas", mime_type="application/json",
                   description="Catálogo completo del balotario del grupo 09.")
def recurso_balotario() -> str:
    """El balotario como recurso, para que el cliente lo lea sin llamar una tool."""
    return json.dumps(cargar_catalogo(), ensure_ascii=False, indent=2)


def main():
    """Arranca el servidor sobre stdio."""
    registro.info("Iniciando servidor MCP edos-grupo09 sobre stdio")
    servidor.run(transport="stdio")


if __name__ == "__main__":
    main()
