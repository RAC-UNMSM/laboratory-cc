"""Recorrido del agente: del problema al desarrollo matemático verificado.

    PROBLEMA → INTERPRETACIÓN → CLASIFICACIÓN → SELECCIÓN DEL MÉTODO →
    DESARROLLO (cálculo simbólico) → CÁLCULO NUMÉRICO (cuando corresponde) →
    ANÁLISIS → VALIDACIÓN → VISUALIZACIÓN → INFORME → RESPUESTA

Este módulo solo ordena ese recorrido; cada etapa vive en su capa:

* interpretación: `orquestacion.interpretacion` (solicitud → `Problema`);
* clasificación y método: `matematica.clasificacion`;
* desarrollo: la familia del balotario que corresponda (`matematica.*`);
* cálculo numérico: `matematica.modelo_edos`, que ya no sustituye al
  desarrollo sino que lo contrasta o, si no hay método analítico, lo hace;
* validación: las comprobaciones simbólicas de cada familia más el portón
  numérico de `matematica.validacion_solucion`;
* visualización: `visualizacion.html`; informe: `orquestacion.informe`.

El orden no es decorativo: la verificación va **antes** de entregar
conclusiones. Si una comprobación concluyente falla, la respuesta lleva la
etapa y el error, nunca el desarrollo como si fuera válido.
"""

import logging

import numpy as np
import sympy as sp

import storage
from matematica import MAX_DIMENSION, DatoInvalido, FueraDeAlcance, MetodoNoAplicable
from matematica.analisis_estabilidad import Equilibrio, buscar_equilibrios, linealizar
from matematica.clasificacion import (anteponer_clasificacion, clasificar, describir_alcance, inventario,
                                      mensaje_de_alcance, parece_matematica)
from matematica.desarrollo import a_json
from matematica.espectro_lyapunov import espectro_flujo, espectro_mapa
from matematica.expresiones import ExpresionInvalida, compilar_escalar
from matematica.modelo_edos import desarrollar_numerico, resolver_edo, seccion_solucion_numerica
from matematica.validacion_solucion import (verificar, verificar_integral_primera,
                                             verificar_solucion_exacta)
from orquestacion.contratos import (ALIAS_ANALISIS, SolicitudEDO, SolicitudEquilibrios, SolicitudTema,
                                    respuesta_aclaracion, respuesta_error, respuesta_fuera_de_alcance,
                                    respuesta_ok, serializable, solucion_a_datos)
from orquestacion.informe import SESION
from orquestacion.interpretacion import interpretar
from visualizacion.html import (MAXIMO_PUNTOS_TRAZA, construir_figuras, figuras_del_desarrollo,
                                generar_html)
from visualizacion.plantilla import figura_a_json

registro = logging.getLogger("edos-grupo09")

#: Puntos máximos de trayectoria que se devuelven como datos.
MAXIMO_PUNTOS_DATOS = 1200

#: Tamaño máximo del HTML que viaja inline por el transporte.
LIMITE_HTML_INLINE = 400_000

#: Cuánto puede alejarse de cero el campo en un punto para seguir siendo equilibrio.
TOLERANCIA_EQUILIBRIO = 1e-9

#: Margen con que se recorta la integración antes de una singularidad.
MARGEN_SINGULARIDAD = 0.02


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------

def analizar_edo(solicitud):
    """Problema completo: desarrollo, trayectoria si hay CI, verificación y figuras."""
    return resolver_problema(solicitud, enfoque="completo")


def analizar_equilibrios_sistema(solicitud):
    """Equilibrios, estabilidad o bifurcaciones, sin integrar ninguna trayectoria."""
    return resolver_problema(solicitud, enfoque="equilibrios")


def analizar_caos_y_fractales(solicitud):
    """Temas 4 y 5: con la ecuación, o solo con el enunciado (Cantor, Feigenbaum, un sistema con nombre)."""
    return resolver_problema(solicitud, enfoque="tema")


def _fuera_de_alcance(motivo, configuracion=None, no_matematico=False, enunciado=None):
    """La respuesta, y el aviso en el informe si era una pregunta de matemáticas.

    Una consulta que no es matemática no se registra: el informe es del trabajo
    del usuario, y "dónde queda el baño" no lo es.
    """
    mensaje = mensaje_de_alcance(motivo, no_matematico)
    if not no_matematico:
        _registrar_en_informe("Fuera del alcance del proyecto", configuracion or {}, ok=False,
                              etapa="fuera_de_alcance", error=mensaje, enunciado=enunciado)
    return respuesta_fuera_de_alcance(mensaje, describir_alcance(), configuracion, motivo, no_matematico)


def resolver_problema(solicitud, enfoque="completo"):
    """El recorrido entero. Nunca levanta por entrada inválida: el error viaja en el resultado."""
    # --- 0. ¿Cabe en el proyecto? -------------------------------------------------
    crudo = solicitud if isinstance(solicitud, dict) else getattr(solicitud, "__dict__", {})
    variables = crudo.get("variables_estado") or []
    if isinstance(variables, list) and len(variables) > MAX_DIMENSION:
        return _fuera_de_alcance(f"el sistema tiene {len(variables)} variables de estado y el proyecto trabaja "
                                 f"sistemas de hasta {MAX_DIMENSION}")

    # --- 1. Validación de la solicitud --------------------------------------------
    clase = {"equilibrios": SolicitudEquilibrios, "tema": SolicitudTema}.get(enfoque, SolicitudEDO)
    try:
        if not isinstance(solicitud, clase):
            solicitud = clase.model_validate(solicitud if isinstance(solicitud, dict)
                                             else solicitud.model_dump())
    except Exception as exc:
        return respuesta_error("validacion_solicitud", exc)
    configuracion = solicitud.configuracion()
    aclaracion = _consultar_tipo_de_sistema(solicitud, configuracion)
    if aclaracion is not None:
        return aclaracion

    # --- 2. Interpretación ---------------------------------------------------------
    try:
        problema, lectura = interpretar(solicitud)
    except ExpresionInvalida as exc:
        return respuesta_error("compilacion", exc, configuracion)
    except (ValueError, TypeError) as exc:
        return respuesta_error("interpretacion", exc, configuracion)
    if enfoque == "equilibrios":
        # Usar esta herramienta ya es decir qué se pregunta.
        problema.pedidos.add("equilibrios")
    if enfoque == "equilibrios" and problema.tipo == "edo" and not problema.autonomo:
        return respuesta_error(
            "no_aplica",
            f"El sistema no es autónomo: depende explícitamente de "
            f"{solicitud.variable_independiente}, así que sus equilibrios no están definidos.",
            configuracion,
            {"sugerencia": "Para un sistema no autónomo use `resolver_graficar_y_analizar_edo` "
                           "(función analizar_edo), que lo resuelve o lo integra."})

    # --- 3 y 4. Clasificación y desarrollo ----------------------------------------
    clasificacion = clasificar(problema)
    if clasificacion.fuera_de_alcance is not None:
        fuera = clasificacion.fuera_de_alcance
        no_matematico = fuera["clave"] == "sin_tema" and not parece_matematica(problema.enunciado)
        return _fuera_de_alcance(fuera["motivo"], configuracion, no_matematico, problema.enunciado)
    try:
        desarrollo = _desarrollar(problema, clasificacion)
    except DatoInvalido as exc:
        return respuesta_error("datos", exc, configuracion, {
            "mensaje_para_el_usuario": f"Revise los datos del problema: {exc}",
            "sugerencia": "Pídale al usuario el valor correcto y vuelva a llamar; no lo reemplace por uno "
                          "inventado."})
    except FueraDeAlcance as exc:
        return _fuera_de_alcance(exc.motivo, configuracion, enunciado=problema.enunciado)

    # --- 5. Cálculo numérico cuando corresponde -------------------------------------
    numerico = None
    if enfoque == "completo" and problema.tipo == "edo" and problema.ci is not None:
        numerico = _tratamiento_numerico(problema, solicitud, desarrollo)
        if numerico.get("error"):
            _registrar_en_informe(_titulo(solicitud, desarrollo), configuracion, ok=False,
                                  etapa="resolucion", error=numerico["error"],
                                  desarrollo=desarrollo)
            return respuesta_error("resolucion", numerico["error"], configuracion, {
                "sugerencia": "Si la solución explota, acorte el intervalo: puede haber una "
                              "singularidad dentro del rango pedido.",
                "desarrollo": desarrollo.a_dict()})

    # --- 6. Validación global: el portón -----------------------------------------------
    verificacion = _verificacion_global(desarrollo, numerico, problema, enfoque,
                                        getattr(solicitud, "equilibrios", None))
    if not verificacion["ok"]:
        _registrar_en_informe(_titulo(solicitud, desarrollo), configuracion, ok=False,
                              etapa="verificacion", error=verificacion["resumen"],
                              verificacion=verificacion, desarrollo=desarrollo)
        detalles = {"verificacion": verificacion}
        if numerico and numerico.get("solucion") is not None:
            detalles["solucion"] = solucion_a_datos(numerico["solucion"], solicitud.variables_estado,
                                                    MAXIMO_PUNTOS_DATOS)
        return respuesta_error("verificacion", verificacion["resumen"], configuracion, detalles)

    # --- 7. Análisis adicionales ------------------------------------------------------
    analisis = _analisis_pedidos(solicitud, problema, clasificacion, desarrollo, enfoque)

    # --- 8 y 9. Visualización e informe -------------------------------------------------
    notas = list(desarrollo.advertencias)
    if numerico:
        notas += [p["nota"] for p in numerico["verificacion"]["pruebas"] if p.get("nota")]
        if numerico.get("recorte"):
            notas.append(numerico["recorte"])
    figuras = _figuras(problema, solicitud, desarrollo, numerico, analisis) if \
        getattr(solicitud, "visualizar", True) else []
    visualizacion = {"figuras": [nombre for nombre, figura in figuras if not isinstance(figura, Exception)]}
    fallidas = [{"figura": nombre, "error": str(figura)} for nombre, figura in figuras
                if isinstance(figura, Exception)]
    if fallidas:
        visualizacion["fallidas"] = fallidas
    informe = _registrar_en_informe(_titulo(solicitud, desarrollo), configuracion,
                                    verificacion=verificacion, analisis=analisis, notas=notas,
                                    desarrollo=desarrollo, figuras=figuras,
                                    enunciado=problema.enunciado)
    if informe:
        visualizacion["informe"] = informe
        visualizacion["nota"] = (
            "El documento no viaja en esta respuesta: no hay cliente de chat que dibuje el HTML "
            "de una herramienta. Entréguele al usuario el enlace de `informe` como enlace "
            "markdown; allí están las gráficas y el desarrollo con las fórmulas compuestas.")
        notas = [*notas, f"Informe de la sesión: {informe}"]
    elif numerico and getattr(solicitud, "visualizar", True):
        visualizacion.update(_html_inline(problema, solicitud, numerico, analisis))

    # --- 10. Respuesta -------------------------------------------------------------------
    return respuesta_ok(configuracion, _solucion_para_respuesta(problema, solicitud, desarrollo, numerico,
                                                                analisis, enfoque),
                        verificacion, analisis, visualizacion, notas,
                        desarrollo=desarrollo.a_dict(), clasificacion=clasificacion.a_dict(),
                        interpretacion=lectura,
                        presentacion=("Presente el desarrollo siguiendo `desarrollo.secciones` en "
                                      "orden: cada sección con su título y sus fórmulas (LaTeX). "
                                      "Puede explicar y redactar transiciones, pero no agregue "
                                      "operaciones que no estén en el desarrollo."))


# ---------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------

def _desarrollar(problema, clasificacion):
    """Ejecuta la familia elegida; si su método no se puede completar, lo dice y pasa a numérico."""
    familia = clasificacion.familia
    if familia is None:
        desarrollo = desarrollar_numerico(problema, clasificacion.motivo, clasificacion.fuera_de_alcance)
    else:
        try:
            desarrollo = familia.desarrollar(problema, clasificacion.datos)
        except MetodoNoAplicable as exc:
            desarrollo = desarrollar_numerico(
                problema, f"{familia.nombre}: {exc} Se trata numéricamente.")
        except (DatoInvalido, FueraDeAlcance):
            raise                             # los responde `resolver_problema` con su mensaje
        except Exception as exc:              # un fallo de sympy no tumba al agente
            registro.warning("El desarrollo de %s falló: %s", familia.clave, exc)
            desarrollo = desarrollar_numerico(
                problema, f"El desarrollo de {familia.nombre} no pudo completarse ({exc}); "
                          "se trata numéricamente.")
            desarrollo.advertir(f"El procedimiento de {familia.nombre} falló en el cálculo "
                                f"simbólico: {exc}")
    # Lo fuera de alcance ya lo advierte `desarrollar_numerico`, que es el único
    # desarrollo que se hace en ese caso.
    anteponer_clasificacion(desarrollo, problema, clasificacion)
    return desarrollo


def _tratamiento_numerico(problema, solicitud, desarrollo):
    """Integra la trayectoria, la verifica y la contrasta con el desarrollo analítico."""
    campo = problema.campo_numerico()
    t0, tf = problema.intervalo
    recorte = None
    intervalo_maximal = desarrollo.resultados.get("intervalo_maximal")
    if isinstance(intervalo_maximal, sp.Interval):
        inferior, superior = intervalo_maximal.inf, intervalo_maximal.sup
        ancho = float(superior - inferior) if inferior.is_finite and superior.is_finite else 1.0
        nuevo_tf = tf
        if superior.is_finite and tf >= float(superior):
            nuevo_tf = float(superior) - MARGEN_SINGULARIDAD * ancho
        if nuevo_tf != tf:
            recorte = (f"El intervalo pedido [{t0:g}, {tf:g}] pasa la singularidad x = "
                       f"{sp.sstr(superior)}: la solución no existe allí, así que se integra solo "
                       f"hasta {nuevo_tf:.4g}, dentro del intervalo maximal.")
            tf = nuevo_tf
    y0 = [float(sp.N(v)) for v in problema.ci[1]]
    try:
        solucion = resolver_edo(campo, y0, (t0, tf), None, puntos=solicitud.puntos,
                                metodo=solicitud.metodo, rtol=solicitud.rtol, atol=solicitud.atol)
    except (ValueError, RuntimeError, ExpresionInvalida) as exc:
        return {"error": str(exc)}

    exacta, componente = _solucion_exacta(problema, solicitud, desarrollo)
    try:
        # Los valores de los parámetros hacen falta para evaluar una solución
        # exacta dada por el cliente (la logística usa r y K).
        verificacion = verificar(campo, solucion, y0, _valores_parametros(problema),
                                 rtol=solicitud.rtol, atol=solicitud.atol,
                                 metodo=solicitud.metodo, exacta=exacta,
                                 variable_independiente=problema.x.name)
    except Exception as exc:
        return {"error": f"La verificación numérica falló: {exc}"}
    if exacta is not None and componente:
        for prueba in verificacion["pruebas"]:
            if prueba["nombre"] == "solucion_exacta":
                prueba["descripcion"] = ("La trayectoria numérica coincide con la solución analítica "
                                         "obtenida en el desarrollo.")
    # Sistema lineal plano: la segunda componente de la solución analítica.
    analitica = desarrollo.resultados.get("solucion_particular")
    if isinstance(analitica, sp.MatrixBase) and analitica.shape[0] > 1:
        for indice in range(1, analitica.shape[0]):
            funcion = _como_funcion(analitica[indice], problema.x)
            if funcion is not None:
                prueba = verificar_solucion_exacta(solucion, funcion, problema.x.name, componente=indice)
                prueba["nombre"] = f"solucion_exacta_{problema.estados[indice].name}"
                prueba["descripcion"] = (f"La componente {problema.estados[indice].name}(t) numérica "
                                         "coincide con la analítica.")
                verificacion["pruebas"].append(prueba)
    hamiltoniano = desarrollo.resultados.get("hamiltoniano")
    if isinstance(hamiltoniano, sp.Basic) and problema.dimension == 2:
        H = hamiltoniano
        if problema.parametro is not None:
            H = H.subs({s: problema.valor_representativo() for s in H.free_symbols
                        if s.name == problema.parametro.name})
        verificacion["pruebas"].append(
            verificar_integral_primera(solucion, H, problema.estados, problema.x))
    # El veredicto del portón numérico se conserva tal cual; las pruebas que se
    # agregaron aquí solo pueden sumarle fallos.
    fallidas = list(dict.fromkeys([*verificacion.get("fallidas", []),
                                   *(p["nombre"] for p in verificacion["pruebas"]
                                     if not p["ok"] and p.get("concluyente", True))]))
    verificacion["fallidas"] = fallidas
    verificacion["ok"] = bool(verificacion.get("ok", True)) and not fallidas
    seccion_solucion_numerica(desarrollo, solucion, problema, solicitud.metodo, solicitud.rtol,
                              solicitud.atol, recorte)
    return {"solucion": solucion, "verificacion": verificacion, "campo": campo, "recorte": recorte}


def _como_funcion(expresion, x):
    """Una expresión de la variable independiente como función para la verificación."""
    expresion = sp.sympify(expresion)
    if expresion.free_symbols - {x} or expresion.has(sp.Symbol("C")):
        return None
    numerica = sp.lambdify(x, expresion, "numpy")

    def evaluar(**valores):
        return numerica(np.asarray(valores[x.name], dtype=float))
    return evaluar


def _valores_parametros(problema):
    """Nombre → valor de todos los parámetros, el simbólico con su valor representativo."""
    valores = dict(problema.parametros)
    if problema.parametro is not None:
        valores[problema.parametro.name] = problema.valor_representativo()
    return valores


def _solucion_exacta(problema, solicitud, desarrollo):
    """(función, es_del_desarrollo) para contrastar con la trayectoria numérica."""
    texto = getattr(solicitud, "solucion_exacta", None)
    if texto:
        exacta = compilar_escalar(texto, [problema.x.name, *[s.name for s in problema.estados],
                                          *_valores_parametros(problema)])
        return exacta, False
    analitica = desarrollo.resultados.get("solucion_particular")
    if isinstance(analitica, sp.MatrixBase):
        analitica = analitica[0]
    if isinstance(analitica, sp.Basic):
        funcion = _como_funcion(analitica, problema.x)
        if funcion is not None:
            return funcion, True
    return None, False


def _verificacion_global(desarrollo, numerico, problema, enfoque, aportados=None):
    """Las comprobaciones simbólicas del desarrollo y las numéricas, en un solo veredicto."""
    pruebas = []
    for v in desarrollo.validaciones:
        entrada = v.a_dict()
        if v.medida is not None:
            entrada["medida"] = v.medida
        pruebas.append(entrada)
    if numerico:
        pruebas += numerico["verificacion"]["pruebas"]
    if (enfoque == "equilibrios" or aportados) and problema.tipo == "edo" and problema.autonomo:
        pruebas += _comprobar_equilibrios(problema, aportados)
    fallidas = [p["nombre"] for p in pruebas if not p["ok"] and p.get("concluyente", True)]
    if numerico:
        fallidas += [n for n in numerico["verificacion"].get("fallidas", []) if n not in fallidas]
        if not numerico["verificacion"].get("ok", True) and not fallidas:
            fallidas.append("verificacion_numerica")
    return {
        "ok": not fallidas,
        "pruebas": pruebas,
        "fallidas": fallidas,
        "resumen": ("Todas las verificaciones se superaron." if not fallidas else
                    f"No se superaron: {', '.join(fallidas)}. No se emiten conclusiones."),
    }


def _equilibrios_numericos(problema):
    """Equilibrios del sistema con los parámetros numéricos, clasificados."""
    if problema.tipo != "edo" or not problema.autonomo:
        return [], {"metodo": "ninguno"}
    campo = problema.campo_con()
    try:
        hallados, informe = buscar_equilibrios(campo, problema.estados, region=problema.region)
    except Exception as exc:
        return [], {"metodo": "simbolico", "nota": f"sympy no pudo resolver F = 0: {exc}"}
    J = sp.Matrix(campo).jacobian(problema.estados)
    resultados = []
    for e in hallados:
        if any(sp.sympify(c).free_symbols for c in e.punto):
            continue
        lin = linealizar(campo, problema.estados, e.punto, matriz_general=J, con_vectores=False)
        resultados.append((e, lin))
    return resultados, informe


def _comprobar_equilibrios(problema, aportados=None):
    """F(x*) = 0 en cada equilibrio informado: la verificación propia de esa pregunta.

    Si el cliente dio los equilibrios, se comprueban esos: un punto que no anula
    el campo no puede presentarse como equilibrio.
    """
    pruebas = []
    campo = problema.campo_numerico()
    puntos = ([[float(c) for c in p] for p in aportados] if aportados else
              [[float(sp.N(c)) for c in e.punto] for e, _ in _equilibrios_numericos(problema)[0]])
    for punto in puntos:
        residuo = float(np.max(np.abs(np.asarray(campo(0.0, punto), dtype=float))))
        pruebas.append({"nombre": f"F(x*)=0 en {punto}", "ok": residuo <= TOLERANCIA_EQUILIBRIO,
                        "residuo": residuo, "umbral": TOLERANCIA_EQUILIBRIO, "tipo": "numerica",
                        "descripcion": "El punto anula el campo, así que es un equilibrio de verdad."})
    return pruebas


def _analisis_pedidos(solicitud, problema, clasificacion, desarrollo, enfoque):
    """Bloques auxiliares: equilibrios clasificados y el estado de lo pedido en `analisis`."""
    pedidos = list(getattr(solicitud, "analisis", ["estabilidad"]))
    if enfoque == "equilibrios" and "estabilidad" not in pedidos:
        pedidos.insert(0, "estabilidad")
    analisis = {}
    tratamiento = set(desarrollo.tratamiento)
    for nombre in pedidos:
        if nombre == "estabilidad" and problema.tipo == "teorico":
            continue
        if nombre == "estabilidad":
            analisis["estabilidad"] = _bloque_estabilidad(problema, solicitud)
        elif nombre == "solucion_analitica":
            analisis[nombre] = ({"disponible": True, "familia": desarrollo.familia,
                                 "nota": "El desarrollo analítico está en `desarrollo`."}
                                if "analitico" in tratamiento else
                                {"disponible": False, "familia": desarrollo.familia,
                                 "nota": "Ninguna familia analítica del balotario corresponde a esta "
                                         "ecuación: el tratamiento es numérico."})
        elif nombre == "bifurcaciones":
            analisis[nombre] = ({"disponible": True, "familia": desarrollo.familia,
                                 "nota": "El análisis de bifurcación está en `desarrollo`."}
                                if desarrollo.familia in ("bifurcacion_1d", "hopf", "homoclinica",
                                                          "lineal_plano_parametrico") else
                                {"disponible": False,
                                 "nota": "Para estudiar una bifurcación indique en `parametro` el "
                                         "parámetro que varía (y, si quiere, `rango_parametro`)."})
        elif nombre == "caos":
            analisis[nombre] = _bloque_caos(problema, desarrollo)
    return analisis


#: Familias cuyo desarrollo ya contiene los exponentes de Lyapunov.
_FAMILIAS_CON_EXPONENTES = {"mapa_1d", "espectro_lyapunov", "kaplan_yorke", "mapa_2d", "seccion_poincare"}


def _bloque_caos(problema, desarrollo):
    """Exponentes de Lyapunov del sistema: los del desarrollo, o calculados aquí por el método QR."""
    if desarrollo.familia in _FAMILIAS_CON_EXPONENTES:
        return {"disponible": True, "familia": desarrollo.familia,
                "nota": "Los exponentes de Lyapunov están en `desarrollo`."}
    if problema.tipo == "teorico" or problema.dimension < 2 or not problema.autonomo:
        return {"disponible": False,
                "nota": "Los exponentes de Lyapunov se calculan para mapas o para flujos autónomos de 2 o 3 "
                        "variables."}
    x0 = tuple(float(sp.N(v)) for v in problema.ci[1]) if problema.ci is not None else None
    try:
        espectro = (espectro_flujo(problema.campo_con(), problema.estados, x0) if problema.tipo == "edo"
                    else espectro_mapa(problema.campo_con(), problema.estados, x0))
    except MetodoNoAplicable as exc:
        return {"disponible": False, "nota": str(exc)}
    l1 = espectro.exponentes[0]
    caotico = l1 > max(5 * espectro.errores[0], 0.01)
    return {"disponible": True, "metodo": "QR (Benettin)", "exponentes": espectro.exponentes,
            "errores": espectro.errores, "suma": espectro.suma, "divergencia_media": espectro.divergencia_media,
            "caotico": caotico,
            "nota": ("λ₁ > 0: dependencia sensible a las condiciones iniciales (caos)." if caotico else
                     "λ₁ ≤ 0 dentro del error: la dinámica es regular (equilibrio, ciclo o toro).")
                    + (" Un flujo plano no puede ser caótico (Poincaré–Bendixson)."
                       if problema.tipo == "edo" and problema.dimension == 2 else "")}


def _bloque_estabilidad(problema, solicitud):
    """Equilibrios del sistema con sus parámetros numéricos (la forma que usaba el agente)."""
    if problema.tipo != "edo":
        return {"disponible": False, "nota": "Los puntos fijos del mapa están en el desarrollo."}
    if not problema.autonomo:
        return {"disponible": False, "origen": {"metodo": "ninguno"},
                "nota": f"El sistema no es autónomo (depende de {problema.x.name}): el análisis de "
                        "equilibrios no aplica."}
    aportados = getattr(solicitud, "equilibrios", None)
    if aportados:
        campo = problema.campo_con()
        J = sp.Matrix(campo).jacobian(problema.estados)
        lista = [(Equilibrio(tuple(sp.nsimplify(c) for c in punto)),
                  linealizar(campo, problema.estados, punto, matriz_general=J, con_vectores=False))
                 for punto in aportados]
        origen = {"metodo": "aportados_por_el_cliente"}
    else:
        lista, origen = _equilibrios_numericos(problema)
    if not lista:
        return {"disponible": not aportados and origen.get("metodo") == "simbolico",
                "origen": a_json(origen), "equilibrios": [],
                "nota": "No se identificaron equilibrios reales para estos valores de los parámetros."}
    return {"disponible": True, "origen": a_json(origen),
            "equilibrios": [{"punto": [float(sp.N(c)) for c in e.punto],
                             "clasificacion": lin.estabilidad_corta,
                             "tipo": lin.tipo, "estabilidad": lin.estabilidad,
                             "autovalores": [complex(sp.N(v)) for v in lin.autovalores],
                             "jacobiano": np.array(lin.jacobiano.evalf(), dtype=float)
                             if lin.jacobiano is not None else None}
                            for e, lin in lista]}


def _solucion_para_respuesta(problema, solicitud, desarrollo, numerico, analisis, enfoque):
    if numerico and numerico.get("solucion") is not None:
        return solucion_a_datos(numerico["solucion"], solicitud.variables_estado, MAXIMO_PUNTOS_DATOS)
    if enfoque == "equilibrios":
        equilibrios = analisis.get("estabilidad", {}).get("equilibrios", [])
        return {"equilibrios": [e["punto"] for e in equilibrios], "cantidad": len(equilibrios)}
    claves = ("solucion_general", "solucion_particular", "solucion_homogenea", "hamiltoniano",
              "lyapunov", "horizonte", "mu_critico", "mu_melnikov", "mu_numerico", "radio_ciclo",
              # Temas 4 y 5
              "r_1", "r_2", "r_infinito", "r_infinito_numerico", "divergencia", "V_estrella",
              "funcion_lyapunov", "espectro", "dimension", "dimension_numerica", "determinante", "inverso",
              "exponentes_lyapunov", "dimension_kaplan_yorke", "maximo_de_g", "tiempo_de_retorno",
              "dimension_lyapunov", "k", "entropia")
    return {"tipo": "desarrollo", "familia": desarrollo.familia,
            "resultados": {k: a_json(desarrollo.resultados[k]) for k in claves if k in desarrollo.resultados}}


# ---------------------------------------------------------------------------
# Visualización e informe
# ---------------------------------------------------------------------------

def _figuras(problema, solicitud, desarrollo, numerico, analisis):
    """Las figuras del desarrollo primero (son las que responden la pregunta) y luego las numéricas."""
    graficas = [dict(g) for g in desarrollo.graficas]
    if numerico:
        solucion = numerico["solucion"]
        # La trayectoria numérica sobre la curva analítica: es la comparación a la vista.
        for grafica in graficas:
            if grafica.get("clave") == "solucion" and problema.dimension <= 2:
                paso = max(1, solucion.t.size // 40)
                grafica["capas"] = list(grafica["capas"]) + [{
                    "tipo": "puntos", "rol": "numerica", "nombre": f"Numérica ({solicitud.metodo})",
                    "x": solucion.t[::paso].tolist(), "y": solucion.y[0, ::paso].tolist()}]
    figuras = figuras_del_desarrollo(graficas)
    if numerico:
        claves = {g.get("clave", "") for g in graficas}
        equilibrios = [{"equilibrio": e["punto"], "clasificacion": e["clasificacion"]}
                       for e in analisis.get("estabilidad", {}).get("equilibrios", []) or []]
        for nombre, figura in construir_figuras(
                numerico["campo"], numerico["solucion"].t, numerico["solucion"].y, {},
                solicitud.variables_estado, equilibrios, _titulo(solicitud, desarrollo),
                solicitud.variable_independiente, MAXIMO_PUNTOS_TRAZA):
            if nombre in ("plano_fase", "linea_fase") and any(c.startswith(("retrato", "diagrama")) for c in claves):
                continue
            # Una línea de fase o un campo de direcciones solo describen la
            # dinámica si el campo no depende del tiempo: evaluados en t₀ para
            # una ecuación no autónoma (3xy², Cauchy-Euler) engañan.
            if nombre in ("plano_fase", "linea_fase") and not problema.autonomo:
                continue
            if nombre == "series" and "solucion" in claves and problema.dimension == 1:
                continue
            figuras.append((nombre, figura))
    return figuras


def _titulo(solicitud, desarrollo):
    return getattr(solicitud, "titulo", None) or desarrollo.nombre


def _html_inline(problema, solicitud, numerico, analisis):
    """Respaldo sin informe: el HTML de las figuras numéricas, acotado en tamaño."""
    puntos = MAXIMO_PUNTOS_TRAZA
    for intento in range(3):
        resultado = generar_html(numerico["campo"], numerico["solucion"].t, numerico["solucion"].y, {},
                                 solicitud.variables_estado, (), getattr(solicitud, "titulo", None),
                                 solicitud.variable_independiente, maximo_puntos=puntos)
        if resultado["bytes"] <= LIMITE_HTML_INLINE:
            salida = {"html": resultado["html"], "bytes": resultado["bytes"], "puntos_por_traza": puntos}
            if intento:
                salida["nota"] = (f"Se redujo la resolución a {puntos} puntos por traza para que el "
                                  "HTML cupiera en el transporte.")
            return salida
        puntos //= 4
    return {"html_omitido": True, "motivo": "El HTML supera el límite del transporte."}


def _registrar_en_informe(titulo, configuracion, *, verificacion=None, analisis=None, notas=None,
                          ok=True, etapa=None, error=None, desarrollo=None, figuras=None,
                          enunciado=None):
    """Agrega este análisis al informe de la sesión y devuelve su enlace. Nunca levanta."""
    entrada = serializable({
        "titulo": titulo, "configuracion": configuracion, "ok": ok,
        "verificacion": verificacion, "analisis": analisis, "notas": notas,
        "etapa": etapa, "error": error, "enunciado": enunciado})
    if desarrollo is not None:
        try:
            entrada["desarrollo"] = desarrollo.a_dict()
        except Exception as exc:
            registro.warning("No se pudo serializar el desarrollo: %s", exc)
    if figuras:
        try:
            entrada["figuras"] = [{"nombre": nombre, "spec": figura_a_json(figura)}
                                  for nombre, figura in figuras if not isinstance(figura, Exception)]
        except Exception as exc:
            registro.warning("No se pudieron preparar las figuras del informe: %s", exc)
    try:
        return SESION.registrar(entrada)
    except Exception as exc:
        registro.warning("No se pudo registrar en el informe: %s", exc)
        return None


def _consultar_tipo_de_sistema(solicitud, configuracion):
    """¿EDO continua o recurrencia? Devuelve la pregunta si no está claro, o None."""
    indicios = solicitud.notacion_sugiere_mapa() if solicitud.tipo_de_sistema == "edo_continua" else []
    if solicitud.tipo_de_sistema == "no_estoy_seguro" or indicios:
        return respuesta_aclaracion(
            "¿El problema es una ecuación diferencial continua o una recurrencia iterada? Las dos "
            "se escriben con el mismo lado derecho pero tienen dinámicas distintas, así que necesito "
            "saberlo antes de calcular.",
            [
                {"respuesta": "Es una EDO continua, dx/dt = f(x)",
                 "accion": "repetir la llamada con tipo_de_sistema='edo_continua'",
                 "consecuencia": "se desarrolla y se resuelve como ecuación diferencial"},
                {"respuesta": "Es un mapa iterado, x_{n+1} = f(x_n)",
                 "accion": "repetir la llamada con tipo_de_sistema='mapa_discreto'",
                 "consecuencia": "se itera como mapa: puntos fijos y exponente de Lyapunov (4.1), "
                                 "duplicación de periodo si tiene un parámetro (4.2) o, si es del plano, "
                                 "jacobiano, inverso y exponentes (5.3)"},
            ],
            configuracion,
            indicios or ["el cliente declaró que no podía determinarlo"])
    return None


def describir_capacidades():
    """Qué sabe hacer el agente hoy, por familias del balotario, y qué queda fuera."""
    alcance = inventario()
    return serializable({
        "alcance": describir_alcance(),
        "desarrollo_matematico": {
            "descripcion": "Cada problema se clasifica en una familia del balotario y se resuelve con "
                           "su procedimiento: el desarrollo (fórmulas intermedias calculadas con "
                           "sympy) viaja en `desarrollo.secciones`.",
            "familias": alcance["familias"],
        },
        "resolucion": {
            "analitica": {"implementado": True,
                          "familias": [f["familia"] for f in alcance["familias"]
                                       if f["tema"].startswith("Tema 1")]},
            "numerica": {"implementado": True,
                         "descripcion": "solve_ivp con control de error; métodos RK45, RK23, DOP853, "
                                        "Radau, BDF y LSODA. Contrasta la solución analítica cuando la "
                                        "hay y resuelve los problemas sin familia analítica."},
        },
        "analisis": {
            "estabilidad": {"implementado": True,
                            "descripcion": "Equilibrios exactos, jacobiano, autovalores y clasificación "
                                           "fina (silla, nodo, foco, centro)."},
            "bifurcaciones": {"implementado": True,
                              "descripcion": "Silla-nodo, transcrítica, horquilla, Hopf y homoclínica "
                                             "(Tema 3), indicando el parámetro en `parametro`."},
            "caos": {"implementado": True,
                     "descripcion": "Exponente de Lyapunov y horizonte de mapas (4.1), duplicación de periodo "
                                    "(4.2), Feigenbaum (4.3), disipatividad y elipsoide atrapante (4.4), "
                                    "espectro de Lyapunov de flujos por el método QR (4.5)."},
            "atractores_y_fractales": {"implementado": True,
                                       "descripcion": "Dimensión de caja (5.1), herradura de Smale (5.2), mapas "
                                                      "del plano como Hénon (5.3), secciones de Poincaré (5.4) y "
                                                      "dimensión de Kaplan-Yorke (5.5)."},
        },
        "fuera_del_proyecto": alcance["fuera_del_proyecto"],
        "metodos_no_trabajados": alcance["metodos_no_trabajados"],
        "verificacion": ["validaciones simbólicas de cada familia (sustitución, invariantes, "
                         "identidades)", "condicion_inicial", "residuo", "convergencia",
                         "metodo_alternativo", "solucion_exacta (analítica vs numérica)",
                         "integral_primera (numérica)"],
        "visualizacion": ["solución analítica y numérica", "retratos de fase con nulclinas, "
                          "variedades y separatrices", "diagramas de bifurcación", "plano "
                          "traza-determinante", "diagrama de telaraña", "series temporales",
                          "trayectoria 3D", "cascada de duplicaciones", "convergencia del espectro de "
                          "Lyapunov", "atractores y fractales", "mapas de retorno", "conteo de cajas"],
        "alias_aceptados": dict(sorted(ALIAS_ANALISIS.items())),
        "limites": {
            "dimension_maxima": 3,
            "transporte": "stdio",
            "solo_primer_orden": "Una EDO de orden n se reduce antes a un sistema de n ecuaciones "
                                 "de primer orden; el agente reconoce esa forma (y' = yp, yp' = ...) "
                                 "y la trata como EDO escalar de orden n.",
            "mapas_discretos": "Mapas de una variable (4.1, 4.2, 4.3) y del plano (5.3). x_{n+1} = f(x_n) y "
                               "dx/dt = f(x) se escriben igual, así que hay que declararlo en "
                               "`tipo_de_sistema`; el mapa logístico con r = 3.8 es caótico y la EDO "
                               "continua no.",
        },
    })
