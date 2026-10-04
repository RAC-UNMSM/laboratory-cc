"""Registro de capacidades y flujo del agente.

Aquí vive el núcleo: `analizar_edo` recorre validar → resolver → verificar →
analizar → visualizar y devuelve un diccionario serializable. No imprime nada y
no sabe nada de MCP, de modo que el servidor y la terminal puedan compartirlo.

El orden no es decorativo. La verificación va **antes** del análisis: si no se
supera, la función regresa con el error y sin conclusiones, que es lo que exige
la propuesta del grupo.
"""

import logging

import numpy as np
import sympy as sp

import storage
from matematica import analisis_bifurcaciones, analisis_caos
from matematica.analisis_estabilidad import analizar_equilibrios
from matematica.expresiones import ExpresionInvalida, compilar_campo, compilar_escalar
from matematica.modelo_edos import (CAPACIDADES_PREVISTAS_ANALITICAS, resolver_analitico,
                                    resolver_edo)
from matematica.validacion_solucion import verificar
from orquestacion.contratos import (ALIAS_ANALISIS, SolicitudEDO, SolicitudEquilibrios,
                                    respuesta_aclaracion, respuesta_error, respuesta_ok,
                                    serializable, solucion_a_datos)
from orquestacion.informe import SESION
from visualizacion.html import MAXIMO_PUNTOS_TRAZA, construir_figuras, generar_html
from visualizacion.plantilla import figura_a_json

registro = logging.getLogger("edos-grupo09")

#: Puntos máximos de trayectoria que se devuelven como datos.
MAXIMO_PUNTOS_DATOS = 1200

#: Tamaño máximo del HTML que viaja inline por el transporte.
LIMITE_HTML_INLINE = 400_000

#: Máximo de equilibrios que se reportan de una búsqueda simbólica.
MAXIMO_EQUILIBRIOS = 12

#: Cuánto puede alejarse de cero el campo en un punto para seguir siendo equilibrio.
TOLERANCIA_EQUILIBRIO = 1e-9


def es_autonomo(campo):
    """True si ninguna ecuación depende de la variable independiente."""
    simbolo = sp.Symbol(campo.variable_independiente)
    return not any(simbolo in expresion.free_symbols for expresion in campo.expresiones)


def buscar_equilibrios(campo, parametros):
    """Resuelve F(x) = 0 de forma exacta con sympy y devuelve los puntos reales.

    Es búsqueda simbólica, no numérica: para el logístico devuelve exactamente
    {0, K} y no aproximaciones. Si sympy no puede resolver el sistema, se
    informa en vez de inventar un resultado.
    """
    if not es_autonomo(campo):
        return [], {"metodo": "ninguno", "nota": (
            "El sistema no es autónomo: depende explícitamente de "
            f"{campo.variable_independiente}, así que los equilibrios no están definidos.")}

    simbolos = [sp.Symbol(n) for n in campo.variables_estado]
    sustituciones = {sp.Symbol(n): sp.Float(v) for n, v in (parametros or {}).items()}
    ecuaciones = [expresion.subs(sustituciones) for expresion in campo.expresiones]
    try:
        soluciones = sp.solve(ecuaciones, simbolos, dict=True)
    except (NotImplementedError, sp.SympifyError, TypeError, ValueError) as exc:
        return [], {"metodo": "simbolico", "nota": f"sympy no pudo resolver F=0: {exc}"}

    equilibrios, descartados = [], 0
    for solucion in soluciones:
        punto = []
        for simbolo in simbolos:
            valor = sp.simplify(solucion.get(simbolo, simbolo))
            if valor.free_symbols:                      # rama paramétrica, no un punto
                punto = None
                break
            numero = complex(valor)
            if abs(numero.imag) > 1e-12:                # equilibrio complejo
                punto = None
                break
            punto.append(float(numero.real))
        if punto is None:
            descartados += 1
            continue
        if not any(np.allclose(punto, previo, atol=1e-12) for previo in equilibrios):
            equilibrios.append(punto)

    # Las dos advertencias se acumulan: antes la segunda pisaba a la primera, y
    # un sistema con soluciones complejas *y* más equilibrios de la cuenta
    # reportaba solo el recorte, ocultando los descartes.
    nota = {"metodo": "simbolico", "encontrados": len(equilibrios)}
    avisos = []
    if descartados:
        nota["descartados"] = descartados
        avisos.append(f"{descartados} solución(es) descartada(s) por ser compleja(s) "
                      "o depender de variables libres.")
    if len(equilibrios) > MAXIMO_EQUILIBRIOS:
        avisos.append(f"Se encontraron {len(equilibrios)} equilibrios; se reportan "
                      f"los primeros {MAXIMO_EQUILIBRIOS}.")
        equilibrios = equilibrios[:MAXIMO_EQUILIBRIOS]
    if avisos:
        nota["nota"] = " ".join(avisos)
    return equilibrios, nota


def _equilibrios_a_clasificar(campo, parametros, aportados):
    """Los equilibrios y de dónde salieron: del cliente, o de resolver F(x)=0.

    Las dos herramientas hacen la misma pregunta -- `analizar_edo` como parte
    del análisis de estabilidad y `analizar_equilibrios` como la pregunta
    entera -- así que la decisión vive una sola vez.
    """
    if aportados:
        return list(aportados), {"metodo": "aportados_por_el_cliente"}
    return buscar_equilibrios(campo, parametros)


def _resumen_de_equilibrios(resultados):
    """Forma en que un equilibrio clasificado viaja al cliente."""
    return [{"punto": r["equilibrio"], "clasificacion": r["clasificacion"],
             "autovalores": r["autovalores"], "jacobiano": r["jacobiano"]}
            for r in resultados]


def _capacidad_estabilidad(contexto):
    """Equilibrios, Jacobiano, autovalores y clasificación."""
    campo, parametros = contexto["campo"], contexto["parametros"]
    equilibrios, origen = _equilibrios_a_clasificar(
        campo, parametros, contexto["equilibrios_pedidos"])
    if not equilibrios:
        return {"disponible": False, "origen": origen,
                "nota": "No se identificaron equilibrios que clasificar."}
    resultados = analizar_equilibrios(campo, equilibrios, parametros)
    contexto["equilibrios_clasificados"] = resultados
    return {"disponible": True, "origen": origen,
            "equilibrios": _resumen_de_equilibrios(resultados)}


def _capacidad_pendiente(invocar, previstas):
    """Reporta un análisis previsto pero ausente, sin devolver números falsos.

    Llama de verdad al stub en vez de devolver un texto fijo: así el motivo que
    viaja al cliente sale del propio módulo responsable, y si alguien lo
    implementa, esta entrada deja de dar "pendiente" sin tocar nada más.
    """
    def ejecutar(contexto):
        try:
            invocar(contexto)
        except NotImplementedError as exc:
            return {"disponible": False, "implementado": False,
                    "estado": "pendiente_de_implementacion",
                    "motivo": str(exc),
                    "capacidades_previstas": list(previstas)}
        return {"disponible": False, "implementado": False,
                "estado": "inconsistente",
                "motivo": "El módulo ya no levanta el error de no implementado: "
                          "revise el registro de capacidades."}
    return ejecutar


#: Enrutador de análisis. Añadir una capacidad es añadir una entrada aquí.
REGISTRO = {
    "estabilidad": _capacidad_estabilidad,
    "caos": _capacidad_pendiente(
        lambda c: analisis_caos.estimar_indicadores(
            c["campo"], c["y0"], c["intervalo"], c["parametros"]),
        analisis_caos.CAPACIDADES_PREVISTAS),
    "bifurcaciones": _capacidad_pendiente(
        lambda c: analisis_bifurcaciones.barrido_parametrico(c["campo"], None, None),
        analisis_bifurcaciones.CAPACIDADES_PREVISTAS),
    "solucion_analitica": _capacidad_pendiente(
        lambda c: resolver_analitico(
            [str(e) for e in c["campo"].expresiones],
            c["campo"].variable_independiente,
            list(c["campo"].variables_estado), c["y0"], c["parametros"]),
        CAPACIDADES_PREVISTAS_ANALITICAS),
}


def _visualizar(contexto, solicitud):
    """Genera el HTML, lo publica si hay storage y lo manda inline si no.

    El HTML viaja inline por el transporte, así que no puede crecer sin límite.
    Antes de rendirse se reintenta con menos puntos por traza: una trayectoria
    dibujada con 1000 puntos en vez de 2000 se ve igual y pesa la mitad.
    No se escribe a disco a propósito: devolver una ruta local no sirve a un
    cliente MCP, que puede estar en otra máquina.

    Sí se intenta subirlo al storage compartido del lab (`storage.subir_html`),
    que no tiene el tope del transporte: si responde, se devuelve la URL de la
    figura a máxima resolución y ya no hace falta mandar el documento inline.
    Si no responde -- el caso normal en local, sin Docker -- se vuelve al
    camino de siempre, submuestreando hasta que quepa.
    """
    enlace = None
    puntos = MAXIMO_PUNTOS_TRAZA
    for intento in range(3):
        resultado = generar_html(
            contexto["campo"], contexto["solucion"].t, contexto["solucion"].y,
            contexto["parametros"], solicitud.variables_estado,
            contexto.get("equilibrios_clasificados", ()),
            solicitud.titulo, solicitud.variable_independiente,
            maximo_puntos=puntos)
        salida = {"figuras": resultado["figuras"], "bytes": resultado["bytes"],
                  "puntos_por_traza": puntos}
        if resultado["fallidas"]:
            salida["fallidas"] = resultado["fallidas"]
        if intento == 0:
            # Se sube la versión de máxima resolución, que es la que vale la
            # pena publicar, y una sola vez: los reintentos de abajo existen
            # solo por el tope del transporte, que al storage no le aplica.
            enlace = storage.subir_html(resultado["html"])
        if enlace:
            salida["url"] = enlace
        if resultado["bytes"] <= LIMITE_HTML_INLINE:
            salida["html"] = resultado["html"]
            if intento:
                salida["nota"] = (f"Se redujo la resolución a {puntos} puntos por traza "
                                  f"para que el HTML cupiera en el transporte.")
            return salida
        if enlace:
            salida["html_omitido"] = True
            salida["motivo"] = (f"El HTML pesa {resultado['bytes']} bytes, por encima "
                                f"del límite de {LIMITE_HTML_INLINE} para enviarlo "
                                f"inline, pero está publicado en `url` a máxima "
                                f"resolución.")
            return salida
        if intento < 2:
            puntos //= 4

    salida["html_omitido"] = True
    salida["motivo"] = (f"El HTML pesa {resultado['bytes']} bytes incluso con la "
                        f"resolución mínima, por encima del límite de "
                        f"{LIMITE_HTML_INLINE} para enviarlo inline.")
    return salida


def _solo_el_enlace(visualizacion, informe):
    """Cambia el HTML inline por el enlace al informe.

    Medido sobre un Van der Pol: la respuesta pesaba 114 KB, de los cuales 85 KB
    (el 75 %) eran el documento HTML. Ningún cliente de chat lo dibuja -- es
    texto que el modelo lee -- así que esos ~23 mil tokens no servían para que
    el usuario viera nada, y encima competían con el enlace de 143 caracteres
    que sí funciona. En la práctica el agente los ignoraba y se fabricaba su
    propia figura por otro lado.

    Se conserva lo que el modelo sí puede usar para redactar: qué figuras se
    dibujaron y cuánto pesaba el documento.
    """
    salida = {clave: valor for clave, valor in visualizacion.items()
              if clave not in ("html", "html_omitido", "motivo")}
    salida["informe"] = informe
    salida["nota"] = (
        "El documento no viaja en esta respuesta: no hay cliente de chat que "
        "dibuje el HTML de una herramienta. Entréguele al usuario el enlace de "
        "`informe` como enlace markdown. Es el mismo para toda la conversación y "
        "la página se actualiza sola, así que basta con darlo una vez.")
    return salida


def _registrar_en_informe(titulo, configuracion, contexto=None, solicitud=None,
                          verificacion=None, analisis=None, notas=None,
                          ok=True, etapa=None, error=None):
    """Agrega este análisis al informe de la conversación y devuelve su enlace.

    El informe es la única forma en que el usuario llega a *ver* su problema:
    el HTML que viaja en la respuesta lo lee el modelo, no lo dibuja el cliente.
    Por eso se registra tanto el análisis que salió bien como el que no: una
    etapa no superada también es parte de lo que se conversó, y esconderla
    dejaría el informe contando una historia más limpia que la real.

    Nunca levanta: si el informe falla, el análisis sigue siendo válido.
    """
    # La plantilla recibe exactamente la misma forma que el cliente MCP: datos
    # ya serializados. Sin esto le llegarían ndarrays y autovalores complejos
    # crudos, y algo tan inocente como `autovalores or []` revienta sobre un
    # array de numpy.
    entrada = serializable({
        "titulo": titulo, "configuracion": configuracion, "ok": ok,
        "verificacion": verificacion, "analisis": analisis,
        "notas": notas, "etapa": etapa, "error": error})
    # Las figuras ya salen como JSON de plotly; volver a recorrerlas con
    # `serializable` costaría una pasada sobre miles de puntos para nada.
    if ok and contexto is not None and solicitud is not None:
        try:
            # Al informe va la *especificación* de cada figura, no un `<div>` ya
            # renderizado: la plantilla la dibuja en el navegador cuando le toca,
            # y la librería de plotly se carga una sola vez desde la plantilla.
            figuras = construir_figuras(
                contexto["campo"], contexto["solucion"].t, contexto["solucion"].y,
                contexto["parametros"], solicitud.variables_estado,
                contexto.get("equilibrios_clasificados", ()),
                solicitud.titulo, solicitud.variable_independiente,
                MAXIMO_PUNTOS_TRAZA)
            entrada["figuras"] = [
                {"nombre": nombre, "spec": figura_a_json(figura)}
                for nombre, figura in figuras if not isinstance(figura, Exception)]
        except Exception as exc:
            registro.warning("No se pudieron preparar las figuras del informe: %s", exc)
    try:
        return SESION.registrar(entrada)
    except Exception as exc:
        registro.warning("No se pudo registrar en el informe: %s", exc)
        return None


def analizar_edo(solicitud):
    """Flujo completo del agente. Devuelve un diccionario serializable.

    `solicitud` es un `SolicitudEDO` o un diccionario con sus campos. Nunca
    levanta excepciones por entrada inválida: el error viaja en el resultado,
    indicando la etapa que no se superó.
    """
    # --- Etapa 1: validación de la solicitud --------------------------------
    try:
        if not isinstance(solicitud, SolicitudEDO):
            solicitud = SolicitudEDO.model_validate(solicitud)
    except Exception as exc:
        return respuesta_error("validacion_solicitud", exc)

    configuracion = solicitud.configuracion()

    # --- Etapa 1b: ¿es una EDO continua o una recurrencia? -------------------
    # El servidor no puede deducirlo de las ecuaciones, porque x_{n+1}=f(x_n) y
    # dx/dt=f(x) se escriben igual. Cuando hay duda se pregunta, en vez de
    # integrar un mapa y devolver números de la ecuación equivocada.
    aclaracion = _consultar_tipo_de_sistema(solicitud, configuracion)
    if aclaracion is not None:
        return aclaracion

    # --- Etapa 2: compilación del campo -------------------------------------
    try:
        campo = compilar_campo(solicitud.ecuaciones, solicitud.variable_independiente,
                               solicitud.variables_estado, solicitud.parametros)
        exacta = (compilar_escalar(solicitud.solucion_exacta,
                                   [solicitud.variable_independiente,
                                    *solicitud.variables_estado,
                                    *solicitud.parametros])
                  if solicitud.solucion_exacta else None)
    except ExpresionInvalida as exc:
        return respuesta_error("compilacion", exc, configuracion)

    # --- Etapa 3: resolución -------------------------------------------------
    try:
        solucion = resolver_edo(campo, solicitud.y0, solicitud.intervalo,
                                solicitud.parametros, puntos=solicitud.puntos,
                                metodo=solicitud.metodo, rtol=solicitud.rtol,
                                atol=solicitud.atol)
    except (ValueError, RuntimeError, ExpresionInvalida) as exc:
        return respuesta_error("resolucion", exc, configuracion, {
            "sugerencia": "Si la solución explota, acorte el intervalo: puede haber "
                          "una singularidad dentro del rango pedido."})

    # --- Etapa 4: verificación. Es un portón, no un adorno -------------------
    try:
        verificacion = verificar(campo, solucion, solicitud.y0, solicitud.parametros,
                                 rtol=solicitud.rtol, atol=solicitud.atol,
                                 metodo=solicitud.metodo, exacta=exacta,
                                 variable_independiente=solicitud.variable_independiente)
    except Exception as exc:
        return respuesta_error("verificacion", exc, configuracion)

    datos_solucion = solucion_a_datos(solucion, solicitud.variables_estado,
                                      MAXIMO_PUNTOS_DATOS)
    if not verificacion["ok"]:
        _registrar_en_informe(solicitud.titulo or "Problema de valor inicial",
                              configuracion, verificacion=verificacion, ok=False,
                              etapa="verificacion", error=verificacion["resumen"])
        return respuesta_error(
            "verificacion", verificacion["resumen"], configuracion,
            {"verificacion": verificacion, "solucion": datos_solucion})

    # --- Etapa 5: análisis solicitados ---------------------------------------
    contexto = {"campo": campo, "parametros": solicitud.parametros,
                "y0": solicitud.y0, "intervalo": solicitud.intervalo,
                "solucion": solucion,
                "equilibrios_pedidos": solicitud.equilibrios or []}
    analisis = {}
    for nombre in solicitud.analisis:
        try:
            analisis[nombre] = REGISTRO[nombre](contexto)
        except Exception as exc:
            analisis[nombre] = {"disponible": False, "error": str(exc),
                                "nota": "El análisis falló; los demás resultados siguen "
                                        "siendo válidos."}

    # --- Etapa 6: visualización ---------------------------------------------
    visualizacion = {}
    if solicitud.visualizar:
        try:
            visualizacion = _visualizar(contexto, solicitud)
        except Exception as exc:
            visualizacion = {"error": str(exc),
                             "nota": "No se pudo generar el HTML; los datos numéricos "
                                     "y la verificación siguen siendo válidos."}

    notas = [p["nota"] for p in verificacion["pruebas"] if p.get("nota")]
    if not es_autonomo(campo):
        notas.append(f"El sistema no es autónomo (depende de "
                     f"{solicitud.variable_independiente}): el análisis de equilibrios "
                     f"y bifurcaciones no aplica.")

    informe = _registrar_en_informe(
        solicitud.titulo or "Problema de valor inicial", configuracion,
        contexto=contexto, solicitud=solicitud, verificacion=verificacion,
        analisis=analisis, notas=notas)
    if informe:
        visualizacion = _solo_el_enlace(visualizacion, informe)
        notas = [*notas, f"Informe de la sesión: {informe}"]
    return respuesta_ok(configuracion, datos_solucion, verificacion, analisis,
                        visualizacion, notas)


def _consultar_tipo_de_sistema(solicitud, configuracion):
    """Portón compartido: ¿EDO continua o recurrencia? Devuelve None si está claro."""
    if solicitud.tipo_de_sistema == "mapa_discreto":
        return respuesta_error(
            "fuera_de_alcance",
            "Los mapas iterados x_{n+1} = f(x_n) no están soportados: este agente "
            "integra EDOs continuas y no itera recurrencias.",
            configuracion,
            {"sugerencia": "Si lo que quiere es la EDO continua dx/dt = f(x) con el "
                           "mismo lado derecho, vuelva a pedirlo con "
                           "tipo_de_sistema='edo_continua', sabiendo que su dinámica "
                           "es distinta: el mapa logístico con r=3.8 es caótico, "
                           "mientras que la EDO continua converge a un equilibrio.",
             "pendiente": "La iteración de mapas requiere un motor distinto del "
                          "integrador de EDOs."})
    indicios = solicitud.notacion_sugiere_mapa()
    if solicitud.tipo_de_sistema == "no_estoy_seguro" or indicios:
        return respuesta_aclaracion(
            "¿El problema es una ecuación diferencial continua o una recurrencia "
            "iterada? Las dos se escriben con el mismo lado derecho pero tienen "
            "dinámicas distintas, así que necesito saberlo antes de calcular.",
            [
                {"respuesta": "Es una EDO continua, dx/dt = f(x)",
                 "accion": "repetir la llamada con tipo_de_sistema='edo_continua'",
                 "consecuencia": "se calcula con normalidad"},
                {"respuesta": "Es un mapa iterado, x_{n+1} = f(x_n)",
                 "accion": "repetir la llamada con tipo_de_sistema='mapa_discreto'",
                 "consecuencia": "está fuera de alcance; el agente lo dirá en vez de "
                                 "devolver un resultado engañoso"},
            ],
            configuracion,
            indicios or ["el cliente declaró que no podía determinarlo"])
    return None


def analizar_equilibrios_sistema(solicitud):
    """Equilibrios y estabilidad sin integrar ninguna trayectoria.

    "Clasifique los equilibrios de x' = mu - x^2" no es un problema de valor
    inicial: no hay condición inicial que dar. Esta función responde esa
    pregunta directamente, que es la forma de los problemas del Tema 3 del
    balotario y la pieza con la que se construye un barrido paramétrico.

    La verificación aquí es distinta de la de una trayectoria: se sustituye cada
    equilibrio en el campo y se comprueba que F(x*) sea nulo.
    """
    try:
        if not isinstance(solicitud, SolicitudEquilibrios):
            solicitud = SolicitudEquilibrios.model_validate(solicitud)
    except Exception as exc:
        return respuesta_error("validacion_solicitud", exc)

    configuracion = solicitud.configuracion()
    aclaracion = _consultar_tipo_de_sistema(solicitud, configuracion)
    if aclaracion is not None:
        return aclaracion

    try:
        campo = compilar_campo(solicitud.ecuaciones, solicitud.variable_independiente,
                               solicitud.variables_estado, solicitud.parametros)
    except ExpresionInvalida as exc:
        return respuesta_error("compilacion", exc, configuracion)

    if not es_autonomo(campo):
        return respuesta_error(
            "no_aplica",
            f"El sistema no es autónomo: depende explícitamente de "
            f"{solicitud.variable_independiente}, así que sus equilibrios no están "
            f"definidos.",
            configuracion,
            {"sugerencia": "Para un sistema no autónomo use `resolver_graficar_y_analizar_edo`, que "
                           "integra la trayectoria."})

    puntos, origen = _equilibrios_a_clasificar(campo, solicitud.parametros,
                                               solicitud.equilibrios)
    if not puntos:
        return respuesta_ok(configuracion, {"equilibrios": [], "cantidad": 0},
                            {"ok": True, "pruebas": [], "fallidas": [],
                             "resumen": "No hay equilibrios que verificar."},
                            {"estabilidad": {"disponible": True, "origen": origen,
                                             "equilibrios": []}},
                            notas=["El sistema no tiene equilibrios reales para estos "
                                   "valores de los parámetros."])

    try:
        resultados = analizar_equilibrios(campo, sorted(puntos), solicitud.parametros)
    except Exception as exc:
        return respuesta_error("analisis", exc, configuracion)

    # Verificación propia de esta pregunta: F(x*) debe anularse.
    pruebas, fallidas = [], []
    for resultado in resultados:
        punto = resultado["equilibrio"]
        valor = np.asarray(campo(0.0, punto, solicitud.parametros), dtype=float)
        residuo = float(np.max(np.abs(valor)))
        ok = residuo <= TOLERANCIA_EQUILIBRIO
        pruebas.append({"nombre": f"F(x*)=0 en {punto}", "ok": ok,
                        "residuo": residuo, "umbral": TOLERANCIA_EQUILIBRIO,
                        "descripcion": "El punto anula el campo, así que es un "
                                       "equilibrio de verdad."})
        if not ok:
            fallidas.append(f"F(x*)=0 en {punto}")

    verificacion = {
        "ok": not fallidas, "pruebas": pruebas, "fallidas": fallidas,
        "resumen": ("Todos los puntos anulan el campo."
                    if not fallidas else
                    f"No son equilibrios: {', '.join(fallidas)}. "
                    "No se emiten conclusiones."),
    }
    if not verificacion["ok"]:
        return respuesta_error("verificacion", verificacion["resumen"], configuracion,
                               {"verificacion": verificacion})

    equilibrios = _resumen_de_equilibrios(resultados)
    analisis = {"estabilidad": {"disponible": True, "origen": origen,
                                "equilibrios": equilibrios}}
    notas = ["Para estudiar una bifurcación, repita esta llamada variando el "
             "parámetro: el barrido automático está pendiente de implementación."]
    informe = _registrar_en_informe(
        "Equilibrios y estabilidad", configuracion, verificacion=verificacion,
        analisis=analisis, notas=notas)
    if informe:
        notas = [*notas, f"Informe de la sesión: {informe}"]
    return respuesta_ok(
        configuracion,
        {"equilibrios": [e["punto"] for e in equilibrios], "cantidad": len(equilibrios)},
        verificacion, analisis, notas=notas)


def describir_capacidades():
    """Qué sabe hacer el agente hoy. Útil como herramienta de descubrimiento."""
    return serializable({
        "resolucion": {
            "numerica": {"implementado": True,
                         "descripcion": "solve_ivp con control de error; métodos "
                                        "RK45, RK23, DOP853, Radau, BDF y LSODA."},
            "analitica": {"implementado": False,
                          "estado": "pendiente_de_implementacion",
                          "previsto": list(CAPACIDADES_PREVISTAS_ANALITICAS),
                          "nota": "El agente no deriva soluciones cerradas. Sí verifica "
                                  "una que usted aporte en `solucion_exacta`."},
        },
        "analisis": {
            "estabilidad": {"implementado": True,
                            "descripcion": "Equilibrios exactos con sympy, Jacobiano "
                                           "numérico, autovalores y clasificación."},
            "caos": {"implementado": False,
                     "estado": "pendiente_de_implementacion",
                     "previsto": list(analisis_caos.CAPACIDADES_PREVISTAS),
                     "nota": "La verificación sí detecta y fecha la sensibilidad a "
                             "condiciones iniciales, pero no la cuantifica."},
            "bifurcaciones": {"implementado": False,
                              "estado": "pendiente_de_implementacion",
                              "previsto": list(analisis_bifurcaciones.CAPACIDADES_PREVISTAS),
                              "nota": "Las piezas existen: pedir el análisis con varios "
                                      "valores del parámetro da los equilibrios exactos "
                                      "de cada uno; lo que falta es automatizar el "
                                      "barrido y detectar los valores críticos."},
        },
        "verificacion": ["condicion_inicial", "residuo", "convergencia",
                         "metodo_alternativo", "solucion_exacta"],
        "visualizacion": ["series temporales", "línea de fase 1D",
                          "retrato de fase 2D", "trayectoria 3D"],
        "alias_aceptados": dict(sorted(ALIAS_ANALISIS.items())),
        "limites": {
            "dimension_maxima": 3,
            "transporte": "stdio",
            "solo_primer_orden": "Una EDO de orden n se debe reducir antes a un "
                                 "sistema de n ecuaciones de primer orden.",
            "sin_mapas_discretos": "No se iteran mapas x_{n+1} = f(x_n). El motor "
                                   "integra EDOs continuas, así que pasar un mapa como "
                                   "si fuera una EDO da una respuesta numéricamente "
                                   "válida para la ecuación equivocada: el mapa "
                                   "logístico con r=3.8 es caótico, mientras que la EDO "
                                   "continua del mismo lado derecho converge a un "
                                   "equilibrio. Los problemas 4.1 a 4.3 y 5.3 del "
                                   "balotario son mapas y están fuera de alcance.",
        },
    })
