"""Servidor MCP del agente de EDOs del grupo 09: el orquestador.

Claude interpreta el pedido del usuario y llama a estas herramientas; el
servidor calcula, verifica y devuelve resultados estructurados; Claude redacta
la explicación final a partir de ellos. Cada análisis publica además un
informe HTML (gráficas, desarrollo y verificación) en el storage del
laboratorio, y su enlace vuelve en `visualizacion.informe`.

Desplegado, escucha por streamable-http en 0.0.0.0:8000 y se conecta en:

    https://rac-unmsm.vekthos.org/grupo09/grupo09_proyecto01_edos-lineales-no-lineales-y-retrato-de-fase/mcp
"""

import hashlib
import logging
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

import storage
from orquestacion.capacidades import analizar_caos_y_fractales as _analizar_caos
from orquestacion.capacidades import analizar_edo as _analizar_edo
from orquestacion.capacidades import analizar_equilibrios_sistema as _analizar_equilibrios
from orquestacion.capacidades import describir_capacidades
from matematica.clasificacion import alcance_del_problema, describir_alcance
from orquestacion.catalogo import cargar_catalogo
from orquestacion.contratos import SeccionPoincare, Trozo


def _revision():
    """Huella corta del código que está corriendo.

    Existe porque el contenedor desplegado sigue vivo entre despliegues fallidos:
    si un despliegue no levanta, sigue corriendo el anterior, y el síntoma es un
    comportamiento viejo sin ninguna pista de por qué. Con esto basta pedir
    `ping` y comparar.
    """
    raiz = Path(__file__).resolve().parent
    resumen = hashlib.sha256()
    for archivo in sorted(raiz.rglob("*.py")) + sorted(raiz.rglob("*.html")):
        if "__pycache__" in archivo.parts or "test" in archivo.parts or "tests" in archivo.parts:
            continue
        resumen.update(archivo.read_bytes())
    return resumen.hexdigest()[:8]


REVISION = _revision()

logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
registro = logging.getLogger("edos-grupo09")

# El bucket lo crea el despliegue; esto no hace daño y falla en silencio.
storage.ensure_bucket()

mcp = MCPServer(
    "grupo09-edos-lineales-no-lineales-y-retrato-de-fase",
    title="Agente de EDOs y sistemas dinámicos (grupo 09)",
    instructions=(
        "Resuelve problemas de ecuaciones diferenciales ordinarias (1 a 3 variables), de "
        "mapas iterados (1 y 2 variables) y de caos y geometría fractal con el DESARROLLO "
        "MATEMÁTICO del balotario del grupo: clasifica el problema, elige el método que le "
        "corresponde, lo ejecuta con cálculo simbólico (sympy) y numérico (scipy), lo verifica "
        "y lo dibuja.\n\n"
        "QUÉ RESUELVE (los cinco temas del balotario, sus 25 problemas):\n"
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
        "  - Tema 4: exponente de Lyapunov y horizonte de un mapa unidimensional (mapa tienda), "
        "duplicación de periodo del mapa logístico (r₁, r₂), cascada de Feigenbaum (r_∞), "
        "disipatividad y elipsoide atrapante de Lorenz, espectro de Lyapunov de un flujo 3D.\n"
        "  - Tema 5: dimensión de caja de fractales autosemejantes (Cantor, Koch, Sierpinski), "
        "herradura de Smale, mapa de Hénon (jacobiano, contracción de áreas, inverso), sección "
        "de Poincaré y mapa de retorno (Rössler), dimensión de Kaplan-Yorke.\n\n"
        "QUÉ HERRAMIENTA USAR: `resolver_graficar_y_analizar_edo` para resolver, hallar la "
        "solución general, graficar o analizar un problema (la condición inicial es "
        "OPCIONAL: 'halle la solución general' no la necesita). `analizar_equilibrios` "
        "cuando la pregunta sea solo sobre equilibrios, estabilidad o una bifurcación. "
        "`resolver_caos_fractales_y_atractores` para los Temas 4 y 5: basta el enunciado, aunque "
        "no traiga ecuación (Cantor, herradura, Feigenbaum, el teorema del espectro) o nombre "
        "el sistema en lugar de escribirlo (Lorenz, Rössler, Hénon, mapa logístico, mapa "
        "tienda: el servidor usa sus ecuaciones y los valores que el enunciado escribe). Los "
        "números que no son parámetros del sistema (r₁, r₂, δ, los exponentes de Lyapunov, las "
        "copias y la razón de un fractal) van en `datos`.\n\n"
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
        "FUERA DEL ALCANCE DEL PROYECTO: ecuaciones en derivadas parciales, estocásticas, con "
        "retardo o integrales, series de Fourier, sistemas de más de 3 variables. Si la "
        "respuesta llega con etapa='fuera_de_alcance' o 'no_es_un_problema_del_proyecto', "
        "transmita `mensaje_para_el_usuario` (dice qué abarca el proyecto, tema por tema) y no "
        "lo resuelva por otra vía. Un sistema de EDOs que no pertenece a ninguna familia sí se "
        "resuelve numéricamente, y el desarrollo lo dice.\n\n"
        "SI LA PREGUNTA NO ES DE MATEMÁTICAS (una dirección, un color, una charla), no llame a "
        "ninguna herramienta: diga en una o dos frases que este asistente resuelve los "
        "problemas de EDOs y sistemas dinámicos del balotario del grupo 09, nombre los cinco "
        "temas y ofrezca resolver uno. Si una respuesta llega con etapa='datos', un valor del "
        "problema es imposible (r₂ ≤ r₁, una razón de semejanza fuera de (0, 1)...): dígale al "
        "usuario cuál y pídale el correcto, sin inventar uno.\n\n"
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
        "EL INFORME ES LA FORMA EN QUE EL USUARIO VE SU TRABAJO. Ningún cliente de chat "
        "dibuja el HTML que devuelve una herramienta. Por eso cada análisis publica su propia "
        "página, con las gráficas interactivas, el desarrollo con las fórmulas compuestas y "
        "la verificación, y su dirección vuelve en `visualizacion.informe` (y, ya como enlace "
        "markdown, en `visualizacion.enlace`; en un fallo de resolución o de verificación, "
        "en `detalles`). Entréguele ese enlace al usuario en cada respuesta que lo traiga: "
        "cada análisis tiene el suyo. Si la respuesta no trae enlace, el storage no estaba "
        "disponible; responda igual con el desarrollo.\n\n"
        "Use `ping` para obtener el inventario exacto de familias y de lo que queda fuera del "
        "proyecto."),
)


@mcp.tool(
    description="Comprueba que el servidor responde y describe qué sabe hacer hoy. "
                "Úsalo para verificar la conexión antes de un análisis largo.")
def ping() -> dict:
    """Latido del servidor, con la versión y el inventario de capacidades."""
    return {
        "ok": True,
        "servidor": "grupo09-edos-lineales-no-lineales-y-retrato-de-fase",
        "revision": REVISION,
        "transporte": "streamable-http",
        "informe": "una página HTML por análisis, publicada en el storage del laboratorio",
        "mensaje": "El agente de EDOs responde.",
        "capacidades": describir_capacidades(),
    }


@mcp.tool(
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


@mcp.tool(
    description="USA ESTA HERRAMIENTA, NO ESCRIBAS CÓDIGO, para encontrar y clasificar "
                "puntos de equilibrio y su estabilidad (nodo, silla, foco, centro, "
                "estable o inestable) con Jacobiano y autovalores, o para estudiar una "
                "bifurcación (silla-nodo, transcrítica, horquilla, Hopf, homoclínica) "
                "según un parámetro, SIN integrar ninguna trayectoria. Hace el desarrollo "
                "matemático completo. Es la indicada cuando la pregunta es sobre "
                "equilibrios, estabilidad o bifurcaciones y NO hay condición inicial; si "
                "la hay, usa `resolver_graficar_y_analizar_edo`.")
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


@mcp.tool(
    name="resolver_caos_fractales_y_atractores",
    description="USA ESTA HERRAMIENTA, NO ESCRIBAS CÓDIGO, para los problemas de caos, fractales y "
                "atractores extraños: duplicación de periodo y diagrama de bifurcación del mapa "
                "logístico, constante de Feigenbaum y r∞, disipatividad y elipsoide atrapante de "
                "Lorenz, espectro y exponentes de Lyapunov de un flujo, dimensión de caja o fractal "
                "(Cantor, Koch, Sierpinski), herradura de Smale, mapa de Hénon (jacobiano, contracción "
                "de áreas, inverso), sección de Poincaré y mapa de retorno (Rössler), dimensión de "
                "Kaplan-Yorke. Basta el ENUNCIADO: si nombra el sistema (Lorenz, Rössler, Hénon, mapa "
                "logístico, mapa tienda) el servidor usa sus ecuaciones con los valores que el "
                "enunciado escribe, y si trae la ecuación, pásela. Hace el desarrollo paso a paso del "
                "balotario, lo verifica numéricamente y lo dibuja en el informe.")
def resolver_caos_fractales_y_atractores(
    enunciado: str,
    ecuaciones: list[str] | None = None,
    variables_estado: list[str] | None = None,
    tipo_de_sistema: str = "edo_continua",
    parametros: dict[str, float] | None = None,
    parametro: str | None = None,
    rango_parametro: list[float | None] | None = None,
    datos: dict[str, float | list[float]] | None = None,
    seccion_poincare: SeccionPoincare | None = None,
    pedidos: list[str] | None = None,
    metodo_analitico: str | None = None,
    region: dict[str, list[float | None]] | None = None,
    trozos: list[Trozo] | None = None,
    separacion_inicial: float | None = None,
    y0: list[float] | None = None,
    intervalo: list[float] | None = None,
    visualizar: bool = True,
    titulo: str | None = None,
) -> dict:
    """Temas 4 y 5 del balotario, con o sin ecuación.

    Args:
        enunciado: El enunciado tal como lo escribió el usuario. Es lo único
            obligatorio: de él se leen el tema, el sistema nombrado y sus datos.
        ecuaciones: Lado derecho del sistema, si el enunciado da uno que no es
            de los que el servidor conoce por su nombre.
        variables_estado: Variables de estado de esas ecuaciones.
        tipo_de_sistema: "edo_continua" o "mapa_discreto" (x_{n+1} = f(x_n)).
            Con un sistema nombrado se toma del sistema.
        parametros: Valores de los parámetros, p. ej. {"a": 1.4, "b": 0.3}.
            Mandan sobre los canónicos y sobre los que se leen del enunciado.
        parametro: Parámetro que se estudia de forma simbólica (la r del mapa
            logístico en la duplicación de periodo).
        rango_parametro: [mínimo, máximo] de ese parámetro.
        datos: Números del enunciado que no son parámetros del sistema:
            {"r_1": 3, "r_2": 3.449, "delta": 4.669} (Feigenbaum),
            {"exponentes": [0.9056, 0, -14.5723]} (Kaplan-Yorke),
            {"copias": 2, "razon": 0.3333} (fractal autosemejante),
            {"contraccion": 0.3333, "expansion": 3} (herradura).
        seccion_poincare: {"variable": "y", "valor": 0, "sentido": "creciente"}.
            Si falta, se lee del enunciado ("y = 0, ẏ > 0").
        pedidos: Lo que pide el enunciado, si quiere precisarlo:
            duplicacion_periodo, feigenbaum, disipatividad, espectro_lyapunov,
            dimension_fractal, herradura, seccion_poincare, kaplan_yorke.
        metodo_analitico: Familia que nombra el enunciado, si la nombra.
        region: Cotas de las variables, p. ej. {"x": [0, 1]}.
        trozos: Mapa definido a trozos: [{expresion, desde, hasta}].
        separacion_inicial: δ₀ del horizonte de predictibilidad de un mapa.
        y0: Condición inicial de la órbita, si se quiere fijar.
        intervalo: [t_inicial, t_final] si se da y0.
        visualizar: Generar las figuras del informe.
        titulo: Título para el informe.

    Returns:
        Como `resolver_graficar_y_analizar_edo`: `desarrollo` con las secciones
        en orden, `verificacion`, `visualizacion.informe`. Si `ok` es false,
        `etapa` dice por qué: 'fuera_de_alcance' o 'no_es_un_problema_del_proyecto'
        (con `mensaje_para_el_usuario`, que se transmite tal cual), 'datos' (un
        valor imposible: pídale el correcto al usuario) o 'validacion_solicitud'.
    """
    registro.info("resolver_caos_fractales_y_atractores: %s ecuaciones", len(ecuaciones or []))
    return _analizar_caos({
        "enunciado": enunciado,
        "ecuaciones": ecuaciones or [],
        "variables_estado": variables_estado or [],
        "tipo_de_sistema": tipo_de_sistema,
        "parametros": parametros or {},
        "parametro": parametro,
        "rango_parametro": rango_parametro,
        "datos": datos,
        "seccion_poincare": seccion_poincare.model_dump() if hasattr(seccion_poincare, "model_dump")
        else seccion_poincare,
        "pedidos": pedidos,
        "metodo_analitico": metodo_analitico,
        "region": region,
        "trozos": [t.model_dump() if hasattr(t, "model_dump") else t for t in trozos] if trozos else None,
        "separacion_inicial": separacion_inicial,
        "y0": y0,
        "intervalo": intervalo,
        "visualizar": visualizar,
        "titulo": titulo,
    })


@mcp.tool(
    description="Lista los problemas del balotario del grupo, que definen qué resuelve el "
                "agente, con su enunciado y su ecuación lista para pasar a las otras "
                "herramientas.")
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
        condiciones iniciales y `alcance`: "dentro", con las `familias` que lo
        resuelven. El campo `ci_derivada` indica si la
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
                        "ecuacion", "condiciones_iniciales", "solicitud")}
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
                    "el mapa en `trozos` ([{expresion, desde, hasta}]). Los Temas 4 y 5 van a "
                    "`resolver_caos_fractales_y_atractores` con el `enunciado`; los que no tienen "
                    "`campo` (4.3, 4.5, 5.1, 5.2) llevan sus números en `datos`.",
            "alcance": describir_alcance()}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
