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
from matematica.clasificacion import alcance_del_problema
from orquestacion.catalogo import cargar_catalogo
from orquestacion.contratos import Trozo
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
        "Resuelve problemas de ecuaciones diferenciales ordinarias (1 a 3 variables) y de "
        "mapas unidimensionales con el DESARROLLO MATEMÁTICO del balotario del grupo: "
        "clasifica el problema, elige el método que le corresponde, lo ejecuta con cálculo "
        "simbólico (sympy) y numérico (scipy), lo verifica y lo dibuja.\n\n"
        "QUÉ RESUELVE (familias del balotario, Temas 1 a 3 y el problema 4.1):\n"
        "  - Tema 1: separables (con intervalo maximal), lineales de primer orden (factor "
        "integrante), Bernoulli, Riccati (con una solución particular), Cauchy-Euler "
        "(ecuación indicial y variación de parámetros), y sistemas conservativos como el "
        "péndulo (energía, separatriz, periodo con la integral elíptica K).\n"
        "  - Tema 2: sistemas lineales planos (autovalores, autovectores, clasificación, "
        "trayectorias, variedades), clasificación según un parámetro, sistemas no "
        "lineales (equilibrios, jacobiano, linealización, nulclinas, cuencas), "
        "hamiltonianos (órbita homoclínica) y ciclos límite por Poincaré-Bendixson.\n"
        "  - Tema 3: bifurcaciones silla-nodo, transcrítica y de horquilla (condiciones de "
        "Sotomayor, histéresis), Hopf (coeficiente de Lyapunov) y homoclínica (Melnikov y "
        "disparo numérico).\n"
        "  - Problema 4.1: exponente de Lyapunov y horizonte de predictibilidad de un mapa "
        "unidimensional (por ejemplo el mapa tienda).\n\n"
        "QUÉ HERRAMIENTA USAR: `resolver_graficar_y_analizar_edo` para resolver, hallar la "
        "solución general, graficar o analizar un problema (la condición inicial es "
        "OPCIONAL: 'halle la solución general' no la necesita). `analizar_equilibrios` "
        "cuando la pregunta sea solo sobre equilibrios, estabilidad o una bifurcación.\n\n"
        "PASE EL ENUNCIADO Y LO QUE SE PIDE. Copie el enunciado del usuario en `enunciado`: "
        "de él se lee el método que nombra (Bernoulli, Riccati, Hopf...) y lo que pide "
        "(intervalo máximo, trayectorias, separatriz, periodo...), que decide qué partes "
        "tiene el desarrollo. Si el enunciado nombra un método, póngalo también en "
        "`metodo_analitico`. Para un estudio según un parámetro (γ, μ) declárelo en "
        "`parametro` (y su dominio en `rango_parametro`, p. ej. [0, null] para γ ≥ 0); "
        "para una constante que deba quedar simbólica (ω₀) también, con [0, null]. Para "
        "Riccati, la solución particular conocida va en `solucion_particular`. Para una "
        "región (cuadrante biológico) use `region`.\n\n"
        "CÓMO PRESENTAR LA RESPUESTA: la respuesta trae `desarrollo`, el procedimiento "
        "que el servidor REALMENTE calculó. Preséntelo siguiendo `desarrollo.secciones` "
        "en orden: el título de cada sección y sus fórmulas (vienen en LaTeX), con las "
        "conclusiones al final. Puede explicar, enlazar los pasos y redactar, pero NO "
        "agregue operaciones, sustituciones ni resultados que no estén en el desarrollo: "
        "si un paso no está, el servidor no lo hizo. Las fórmulas destacadas son los "
        "resultados que el balotario encuadra.\n\n"
        "FUERA DE ALCANCE POR AHORA (el balotario todavía no los resuelve): duplicación "
        "de periodo y Feigenbaum (4.2, 4.3), disipatividad y elipsoide de Lorenz (4.4), "
        "espectro de Lyapunov de flujos (4.5) y todo el Tema 5 (dimensión fractal, "
        "herradura de Smale, Hénon, secciones de Poincaré, Kaplan-Yorke). Si el usuario "
        "pide uno de ellos, el servidor lo marca como fuera de alcance: dígaselo así, sin "
        "ofrecer un sustituto como si fuera la respuesta. Un sistema que no pertenece a "
        "ninguna familia se resuelve numéricamente, y el desarrollo lo dice.\n\n"
        "MAPAS ITERADOS: x_{n+1} = f(x_n) y dx/dt = f(x) se escriben con el mismo lado "
        "derecho, así que el servidor no puede distinguirlos: quien lo sabe es el usuario. "
        "Si el enunciado usa notación de recurrencia (x_{n+1}, x_n, 'iterar', 'el mapa "
        "tienda'), declare tipo_de_sistema='mapa_discreto'; un mapa definido a trozos va en "
        "`trozos` (o con Abs/Min/Max) y la separación δ₀ en `separacion_inicial`. Si no "
        "puede determinarlo del enunciado, declare 'no_estoy_seguro': el servidor "
        "devolverá la pregunta que hay que hacerle al usuario. PREGUNTE al usuario en ese "
        "caso, no adivine: el mapa logístico con r=3.8 es caótico, mientras que la EDO "
        "continua con el mismo lado derecho converge a un equilibrio.\n\n"
        "Si una respuesta llega con etapa='aclaracion_necesaria', no reintente con una "
        "suposición: traslade la pregunta al usuario y vuelva a llamar con su respuesta.\n\n"
        "CÓMO ESCRIBIR EL SISTEMA: forma explícita de primer orden x' = F(t, x), una "
        "expresión por variable de estado. Una EDO de orden n se reduce antes a un "
        "sistema de n ecuaciones; por ejemplo theta'' = -sin(theta) se escribe como "
        "ecuaciones=['v', '-sin(theta)'] con variables_estado=['theta', 'v'], y "
        "x²y'' − 2xy' + 2y = x³ ln x como ecuaciones=['yp', '(2*x*yp - 2*y + "
        "x**3*log(x))/x**2'] con variables_estado=['y', 'yp'] y variable_independiente='x'. "
        "El servidor reconoce esa forma y la trata como la EDO de orden n que es.\n\n"
        "VERIFICACIÓN: toda respuesta trae un bloque `verificacion`, con las comprobaciones "
        "simbólicas del desarrollo (sustituir la solución en la EDO, conservación de "
        "integrales primeras, identidades) y las numéricas. Si `ok` es false, el servidor "
        "no entrega conclusiones y hay que explicar al usuario qué comprobación falló en "
        "lugar de interpretar números inválidos.\n\n"
        "NO REHAGA EL CÁLCULO POR SU CUENTA. No vuelva a integrar el sistema con "
        "scipy, ni dibuje la figura con matplotlib, ni escriba código para "
        "reproducir lo que esta herramienta ya devolvió. El servidor ya calculó el "
        "desarrollo, integró con control de error y lo verificó; un cálculo que usted "
        "haga aparte NO pasó por ese portón, así que presentarlo al usuario deshace la "
        "única garantía que este agente ofrece. Si lo que le falta es una imagen que el "
        "usuario pueda ver, ya existe: es el informe, y basta con darle el enlace.\n\n"
        "Lo que sí le toca a usted es redactar: ordenar y explicar el desarrollo, "
        "interpretar los equilibrios y la dinámica, y relacionar los resultados con la "
        "pregunta. Los números y las fórmulas salen de la respuesta, no de un cálculo suyo.\n\n"
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
        "Use `ping` para obtener el inventario exacto de familias y de lo que queda fuera de "
        "alcance."),
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
                "resolver una EDO o un sistema de EDOs (analíticamente o resolver "
                "numéricamente), hallar su solución general o particular, graficar x(t), "
                "dibujar un plano de fase o retrato de fase, un campo de direcciones, una "
                "línea de fase o una trayectoria 3D, encontrar o clasificar puntos de "
                "equilibrio, o estudiar estabilidad, bifurcaciones, ciclos límite, "
                "atractores y sensibilidad a condiciones iniciales. Clasifica el problema "
                "(separable, lineal, Bernoulli, Riccati, Cauchy-Euler, conservativo, sistema "
                "lineal o no lineal, Hopf, homoclínica, mapa) y hace el DESARROLLO "
                "MATEMÁTICO completo con sympy: transformaciones, ecuaciones intermedias, "
                "constantes, autovalores, separatrices. Si hay condición inicial, además "
                "integra con control de error (RK45, DOP853, Radau, BDF, LSODA) y contrasta "
                "la solución analítica con la numérica; verifica todo y genera las figuras. "
                "NO uses scipy, solve_ivp ni matplotlib para esto: lo que calcules por "
                "tu cuenta no pasa por esas verificaciones y no debe mostrarse al "
                "usuario como resultado. Reduce EDOs de orden n a sistemas de primer "
                "orden antes de llamarla.")
@sin_contaminar_stdout
def analizar_edo(
    ecuaciones: list[str],
    variables_estado: list[str],
    y0: list[float] | None = None,
    intervalo: list[float] | None = None,
    variable_independiente: str = "t",
    parametros: dict[str, float] | None = None,
    enunciado: str | None = None,
    metodo_analitico: str | None = None,
    pedidos: list[str] | None = None,
    parametro: str | None = None,
    rango_parametro: list[float | None] | None = None,
    region: dict[str, list[float | None]] | None = None,
    solucion_particular: str | None = None,
    trozos: list[Trozo] | None = None,
    separacion_inicial: float | None = None,
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
    """Interpreta, clasifica, desarrolla, calcula, verifica y dibuja un problema.

    Args:
        ecuaciones: Lado derecho de x' = F(t, x), una expresión por variable de
            estado, en el mismo orden. Se escriben con `**` para la potencia y
            pueden usar sin, cos, tan, exp, log, sqrt, sinh, cosh, tanh, Abs,
            sign, Min, Max, pi. Ejemplos: ["-2*y"], ["y**3 - y"],
            ["yp", "(2*x*yp - 2*y + x**3*log(x))/x**2"], ["v", "-w0**2*sin(theta)"].
        variables_estado: Nombres de las variables de estado, de 1 a 3.
        y0: Condición inicial, un valor por variable. OPCIONAL: "halle la
            solución general" o "clasifique el equilibrio" no la tienen.
        intervalo: [t_inicial, t_final]; t_inicial es donde vale la condición
            inicial. Obligatorio si se da y0; sin y0 solo fija la ventana de las
            gráficas.
        variable_independiente: Nombre de la variable independiente. Use "x"
            cuando el problema está escrito como dy/dx.
        parametros: Valores de los parámetros con nombre, p. ej. {"r": 1.0}.
            Todo nombre que no sea variable de estado debe estar aquí o en
            `parametro`.
        enunciado: El enunciado tal como lo escribió el usuario. Decide el
            método que se nombra y qué partes tiene el desarrollo.
        metodo_analitico: Método que pide el enunciado: separable, lineal,
            bernoulli, riccati, cauchy_euler, conservativo, lineal_plano,
            no_lineal, ciclo_limite, bifurcacion, hopf, homoclinica, mapa o
            numerico. Si la ecuación no tiene esa forma, el servidor lo dice y
            usa el método que sí corresponde.
        pedidos: Lo que pide el enunciado, si quiere precisarlo: solucion_general,
            intervalo_maximo, trayectorias, separatriz, periodo, energia,
            hamiltoniano, equilibrios, ciclo_limite, homoclinica,
            diagrama_bifurcacion, lyapunov, horizonte.
        parametro: Parámetro que se estudia de forma simbólica (γ de un
            oscilador, μ de una bifurcación) o constante que debe quedar
            simbólica (ω₀). Su valor en `parametros`, si se da, se usa para
            integrar y graficar.
        rango_parametro: [mínimo, máximo] del parámetro, null = no acotado.
            Ejemplos: [0, null] para γ ≥ 0 o para ω₀ > 0.
        region: Cotas de las variables, p. ej. {"x": [0, null], "y": [0, null]}
            para el cuadrante biológico.
        solucion_particular: Solución particular conocida de una Riccati
            (p. ej. "x"). Si falta, se busca una polinómica.
        trozos: Mapa definido a trozos: [{"expresion": "2*x", "desde": 0,
            "hasta": 0.5}, {"expresion": "2*(1 - x)", "desde": 0.5, "hasta": 1}].
        separacion_inicial: δ₀ del horizonte de predictibilidad de un mapa.
        analisis: Bloques adicionales: "estabilidad" (equilibrios con los
            parámetros dados, por defecto), "solucion_analitica",
            "bifurcaciones", "caos". El desarrollo matemático se hace siempre.
        equilibrios: Equilibrios a clasificar en el bloque de estabilidad. Si se
            omite, se resuelven de forma exacta.
        solucion_exacta: Solución analítica conocida para contrastar con la
            numérica (si no se da, se usa la que obtiene el desarrollo).
        metodo: Integrador de SciPy: RK45, RK23, DOP853, Radau, BDF, LSODA.
        rtol: Tolerancia relativa del integrador.
        atol: Tolerancia absoluta del integrador.
        puntos: Puntos de la malla de salida.
        visualizar: Generar las figuras del informe.
        titulo: Título para el informe.
        tipo_de_sistema: "edo_continua" (por defecto), "mapa_discreto" para una
            recurrencia x_{n+1} = f(x_n) (notación x_n, "iterar", "el mapa
            tienda"), o "no_estoy_seguro": el servidor devuelve la pregunta que
            hay que hacerle al usuario en lugar de un resultado.

    Returns:
        Si `ok` es true: `desarrollo` (familia, método, `secciones` con las
        fórmulas en LaTeX en el orden en que se presentan, `resultados` con
        nombre, `conclusiones`), `clasificacion`, `verificacion` (comprobaciones
        simbólicas y numéricas), `solucion` (trayectoria si hubo condición
        inicial), `analisis` y `visualizacion` con el enlace al informe.
        Presente el desarrollo siguiendo `desarrollo.secciones`, sin agregar
        operaciones que no estén ahí.

        Si `ok` es false: `etapa` y `error`, y ninguna conclusión. Las etapas
        posibles son validacion_solicitud, compilacion, interpretacion,
        resolucion y verificacion.

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
        "enunciado": enunciado,
        "metodo_analitico": metodo_analitico,
        "pedidos": pedidos,
        "parametro": parametro,
        "rango_parametro": rango_parametro,
        "region": region,
        "solucion_particular": solucion_particular,
        "trozos": [t.model_dump() if hasattr(t, "model_dump") else t for t in trozos] if trozos else None,
        "separacion_inicial": separacion_inicial,
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
                "estable o inestable) con Jacobiano y autovalores, o para estudiar una "
                "bifurcación (silla-nodo, transcrítica, horquilla, Hopf, homoclínica) "
                "según un parámetro, SIN integrar ninguna trayectoria. Hace el desarrollo "
                "matemático completo. Es la indicada cuando la pregunta es sobre "
                "equilibrios, estabilidad o bifurcaciones y NO hay condición inicial; si "
                "la hay, usa `resolver_graficar_y_analizar_edo`.")
@sin_contaminar_stdout
def analizar_equilibrios(
    ecuaciones: list[str],
    variables_estado: list[str],
    variable_independiente: str = "t",
    parametros: dict[str, float] | None = None,
    enunciado: str | None = None,
    metodo_analitico: str | None = None,
    pedidos: list[str] | None = None,
    parametro: str | None = None,
    rango_parametro: list[float | None] | None = None,
    region: dict[str, list[float | None]] | None = None,
    equilibrios: list[list[float]] | None = None,
    tipo_de_sistema: str = "edo_continua",
) -> dict:
    """Equilibrios, estabilidad y bifurcaciones, con su desarrollo.

    Args:
        ecuaciones: Lado derecho de x'=F(x), una expresión por variable de
            estado. El sistema debe ser autónomo.
        variables_estado: Nombres de las variables de estado, de 1 a 3.
        variable_independiente: Nombre de la variable independiente.
        parametros: Valores de los parámetros que usan las ecuaciones.
        enunciado: El enunciado del usuario (decide qué partes tiene el desarrollo).
        metodo_analitico: Método que nombra el enunciado (bifurcacion, hopf,
            homoclinica, lineal_plano, no_lineal, ciclo_limite...).
        pedidos: Lo que pide el enunciado (equilibrios, diagrama_bifurcacion...).
        parametro: El parámetro de la bifurcación o de la clasificación (μ, γ).
            Para estudiar una bifurcación basta UNA llamada con el parámetro
            declarado: el servidor calcula las ramas, los valores críticos y el
            tipo de bifurcación.
        rango_parametro: [mínimo, máximo] del parámetro; null = no acotado.
        region: Cotas de las variables (p. ej. el cuadrante x ≥ 0, y ≥ 0).
        equilibrios: Equilibrios a clasificar. Si se omite, se resuelven F(x)=0
            de forma exacta con sympy.
        tipo_de_sistema: Igual que en `resolver_graficar_y_analizar_edo`.

    Returns:
        Si `ok` es true: `desarrollo` con el procedimiento calculado,
        `analisis.estabilidad.equilibrios` con los equilibrios para los valores
        dados de los parámetros y `verificacion`, que comprueba entre otras
        cosas que cada punto anule de verdad el campo. Si `ok` es false,
        `etapa` dice qué no se superó y no hay conclusiones.
    """
    registro.info("analizar_equilibrios: %s variables, parametros=%s",
                  len(variables_estado), sorted((parametros or {})))
    return _analizar_equilibrios({
        "ecuaciones": ecuaciones,
        "variables_estado": variables_estado,
        "variable_independiente": variable_independiente,
        "parametros": parametros or {},
        "enunciado": enunciado,
        "metodo_analitico": metodo_analitico,
        "pedidos": pedidos,
        "parametro": parametro,
        "rango_parametro": rango_parametro,
        "region": region,
        "equilibrios": equilibrios,
        "tipo_de_sistema": tipo_de_sistema,
    })


@servidor.tool(
    description="Lista los problemas del balotario del grupo, que definen qué resuelve el "
                "agente (y qué queda fuera de alcance por ahora), con su enunciado y su "
                "ecuación lista para pasar a las otras herramientas.")
@sin_contaminar_stdout
def listar_balotario(tema: str | None = None, incluir_solucion: bool = False) -> dict:
    """Problemas del balotario con su ecuación, condiciones iniciales y alcance.

    Args:
        tema: Identificador de un tema concreto, por ejemplo "tema_01". Si se
            omite, se listan todos los temas disponibles.
        incluir_solucion: Incluir la solución esperada de cada problema. Son las
            respuestas del balotario, útiles para contrastar un cálculo propio.

    Returns:
        Los temas con sus problemas. Cada problema trae id, enunciado, tipo,
        dificultad, el bloque `ecuacion` listo para pasar a `resolver_graficar_y_analizar_edo`, sus
        condiciones iniciales y `alcance`: "dentro" (con las `familias` que lo
        resuelven) o "fuera_de_alcance". El campo `ci_derivada` indica si la
        condición inicial viene del enunciado original o se fijó para concretar
        un PVI. Si el balotario tiene un error en ese problema, viene
        `revision_matematica` con lo que el agente calcula en su lugar.
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
            resumen.update(alcance_del_problema(problema["id"]))
            if "revision_matematica" in problema:
                resumen["revision_matematica"] = problema["revision_matematica"]["resumen"]
            if incluir_solucion:
                resumen["solucion_esperada"] = problema.get("solucion_esperada")
            problemas.append(resumen)
        salida.append({"tema": contenido["tema"], "problemas": problemas})
    return {"ok": True, "temas": salida,
            "nota": "Las ecuaciones vienen en forma de sistema de primer orden: "
                    "`campo`, `variables_estado` y `variable_independiente` se pasan "
                    "tal cual, junto con el `enunciado`. Un problema CON "
                    "`condiciones_iniciales` va a `resolver_graficar_y_analizar_edo`; uno SIN "
                    "ellas puede ir a cualquiera de las dos (la solución general no necesita "
                    "condición inicial). Las familias paramétricas del Tema 3 van a "
                    "`analizar_equilibrios` con `parametro` declarado: una sola llamada estudia "
                    "la bifurcación entera. El 4.1 es un mapa: tipo_de_sistema='mapa_discreto' y "
                    "el mapa en `trozos` ([{expresion, desde, hasta}]). Los problemas con "
                    "`alcance: fuera_de_alcance` todavía no tienen solución en el balotario: "
                    "el agente lo dice y no los resuelve."}


def main():
    """Arranca el servidor sobre stdio."""
    registro.info("Iniciando servidor MCP edos-grupo09 sobre stdio")
    servidor.run(transport="stdio")


if __name__ == "__main__":
    main()
