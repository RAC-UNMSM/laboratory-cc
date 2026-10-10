"""Verificación independiente de una solución numérica ya calculada.

Es el portón del agente: si estas comprobaciones no se superan, el servidor
informa el problema y **no emite conclusiones**. Ninguna de las pruebas confía
en el integrador que produjo la solución; cada una la contrasta contra algo
externo:

* la condición inicial pedida,
* el propio campo vectorial (residuo por diferencias finitas),
* una reintegración con tolerancias más finas (convergencia),
* una reintegración con otro método (independencia del integrador),
* una solución analítica, cuando el cliente la aporta.

Es el criterio de verificación que fija la propuesta del grupo: contraste con
casos exactos, revisión de residuos calculada de forma independiente y
comparación al reducir tolerancias o cambiar de método.
"""

import numpy as np

from matematica.modelo_edos import resolver_edo

#: Umbrales por defecto. El del residuo es holgado a propósito: se calcula por
#: diferencias finitas sobre la malla de salida, cuyo error es O(h^2) y no
#: depende de la calidad del integrador.
UMBRAL_CONDICION_INICIAL = 1e-10
UMBRAL_CONVERGENCIA = 1e-5
UMBRAL_METODO_ALTERNATIVO = 1e-5
UMBRAL_RESIDUO = 1e-6

#: Tramo inicial sobre el que se exige coincidencia punto a punto al reintegrar.
#: A tiempo largo un sistema caótico se separa aunque ambas integraciones sean
#: correctas, así que el veredicto se decide en esta ventana.
FRACCION_VENTANA = 0.15

#: Tolerancia para la comparación de medias y desviaciones, que es la que sí
#: debe cumplirse a tiempo largo porque describe el atractor.
UMBRAL_ESTADISTICO = 0.15

#: Margen sobre el error teórico de la derivada por diferencias finitas antes de
#: considerar que un residuo delata un problema real.
MARGEN_RESIDUO_MALLA = 5.0


def _escala(valores):
    """Escala para normalizar un desvío, evitando dividir por casi cero."""
    return max(1.0, float(np.max(np.abs(valores))) if np.size(valores) else 1.0)


def verificar_condicion_inicial(solucion, y0, umbral=UMBRAL_CONDICION_INICIAL):
    """La trayectoria debe empezar exactamente donde se pidió."""
    inicial = np.asarray(solucion.y[:, 0], dtype=float)
    pedida = np.asarray(y0, dtype=float)
    desvio = float(np.max(np.abs(inicial - pedida))) if pedida.size else 0.0
    return {"nombre": "condicion_inicial", "ok": desvio <= umbral,
            "desvio": desvio, "umbral": umbral,
            "descripcion": "La solución arranca en la condición inicial pedida."}


def verificar_residuo(campo, solucion, parametros=None, umbral=UMBRAL_RESIDUO):
    """Sustituye la trayectoria en la EDO y mide cuánto falla la igualdad.

    Deriva la solución por diferencias finitas sobre la malla de salida y la
    compara con el campo evaluado en esos mismos puntos.

    La derivada central tiene un error de truncamiento de −(h²/6)·x''', que no
    dice nada sobre la calidad del integrador: una malla gruesa sobre una
    trayectoria muy curvada produce un residuo grande aunque la solución sea
    correcta. Para no confundir ambas cosas, la prueba **estima su propio error**
    usando x''' (obtenido derivando dos veces el campo a lo largo de la
    trayectoria) y solo denuncia el residuo cuando supera ese error esperado por
    un margen. Así el umbral deja de ser un número arbitrario.
    """
    tiempos = np.asarray(solucion.t, dtype=float)
    estados = np.asarray(solucion.y, dtype=float)
    if tiempos.size < 5:
        return {"nombre": "residuo", "ok": True, "residuo_relativo": 0.0,
                "umbral": umbral, "concluyente": False,
                "descripcion": "Malla demasiado corta para estimar el residuo."}
    derivada_numerica = np.gradient(estados, tiempos, axis=1)
    derivada_campo = np.empty_like(derivada_numerica)
    for j, t in enumerate(tiempos):
        derivada_campo[:, j] = np.asarray(campo(float(t), estados[:, j], parametros),
                                          dtype=float)

    # Los extremos usan diferencias de un solo lado, menos precisas.
    interior = slice(1, -1)
    escala = _escala(derivada_campo[:, interior])
    residuo = float(np.max(np.abs(derivada_numerica[:, interior]
                                  - derivada_campo[:, interior]))) / escala

    # x''' a lo largo de la trayectoria: el campo evaluado sobre ella es x'(t).
    tercera = np.gradient(np.gradient(derivada_campo, tiempos, axis=1), tiempos, axis=1)
    paso = float(np.max(np.diff(tiempos))) if tiempos.size > 1 else 0.0
    esperado = (paso ** 2 / 6.0) * float(np.max(np.abs(tercera[:, interior]))) / escala
    permitido = max(umbral, MARGEN_RESIDUO_MALLA * esperado)
    return {"nombre": "residuo", "ok": residuo <= permitido, "concluyente": True,
            "residuo_relativo": residuo, "umbral": umbral,
            "error_esperado_por_malla": esperado, "umbral_efectivo": permitido,
            "paso_malla": paso,
            "descripcion": "La trayectoria satisface x' = F(t, x) al sustituirla, "
                           "descontando el error de la derivada por diferencias finitas."}


def _comparar_reintegracion(campo, solucion, parametros, fraccion_ventana, **ajustes):
    """Reintegra con otra configuración y compara de tres formas distintas.

    La distinción es esencial para sistemas caóticos. Dos integraciones
    correctas de un sistema sensible a condiciones iniciales **tienen** que
    separarse a tiempo largo: exigir coincidencia punto a punto en todo el
    intervalo marcaría como inválido el atractor de Lorenz, que es justamente
    uno de los casos de demostración del proyecto. Por eso se devuelven:

    * `ventana`: desvío en el tramo inicial, donde dos integraciones correctas
      del mismo problema sí deben coincidir. Es el que decide el veredicto.
    * `total`: desvío en todo el intervalo. Informativo; su crecimiento frente
      al de la ventana es **evidencia de sensibilidad**, no de un fallo.
    * `estadistico`: diferencia de medias y desviaciones por variable. A tiempo
      largo es lo que sí debe coincidir, porque describe el atractor y no la
      trayectoria concreta.
    """
    tiempos = np.asarray(solucion.t, dtype=float)
    propia = np.asarray(solucion.y, dtype=float)
    referencia = resolver_edo(campo, solucion.y[:, 0], (tiempos[0], tiempos[-1]),
                              parametros, puntos=tiempos.size, **ajustes)
    otra = np.asarray(referencia.y, dtype=float)
    diferencia = np.abs(otra - propia)
    escala = _escala(propia)

    corte = max(3, int(np.ceil(tiempos.size * fraccion_ventana)))
    estadistico = 0.0
    for fila_propia, fila_otra in zip(propia, otra):
        estadistico = max(
            estadistico,
            abs(float(fila_propia.mean() - fila_otra.mean())) / escala,
            abs(float(fila_propia.std() - fila_otra.std())) / escala)
    return {
        "ventana": float(np.max(diferencia[:, :corte])) / escala,
        "total": float(np.max(diferencia)) / escala,
        "estadistico": estadistico,
        "t_ventana": float(tiempos[corte - 1]),
        "fraccion_ventana": fraccion_ventana,
    }


def _resultado_reintegracion(nombre, comparacion, umbral, umbral_estadistico, extra):
    """Arma el veredicto a partir de los tres desvíos, distinguiendo caos de error."""
    ok = comparacion["ventana"] <= umbral
    sensibilidad = ok and comparacion["total"] > umbral
    resultado = {
        "nombre": nombre, "ok": ok, "umbral": umbral,
        "desvio_ventana": comparacion["ventana"],
        "desvio_total": comparacion["total"],
        "desvio_estadistico": comparacion["estadistico"],
        "umbral_estadistico": umbral_estadistico,
        "t_ventana": comparacion["t_ventana"],
        "estadisticas_coinciden": comparacion["estadistico"] <= umbral_estadistico,
        "sensibilidad_detectada": sensibilidad,
        **extra,
    }
    if sensibilidad:
        resultado["nota"] = (
            f"Coinciden hasta t={comparacion['t_ventana']:g} y se separan después "
            f"(desvío total {comparacion['total']:.2e}). Es evidencia de sensibilidad "
            f"a condiciones iniciales, no de un error de integración; a tiempo largo "
            f"la comparación válida es la estadística.")
    return resultado


def verificar_convergencia(campo, solucion, parametros=None, rtol=1e-8, atol=1e-10,
                           metodo="RK45", factor=100.0, umbral=UMBRAL_CONVERGENCIA,
                           fraccion_ventana=FRACCION_VENTANA,
                           umbral_estadistico=UMBRAL_ESTADISTICO):
    """Reintegra con tolerancias `factor` veces más finas y compara."""
    try:
        comparacion = _comparar_reintegracion(campo, solucion, parametros, fraccion_ventana,
                                              metodo=metodo, rtol=rtol / factor,
                                              atol=atol / factor)
    except (RuntimeError, ValueError) as exc:
        return {"nombre": "convergencia", "ok": False, "umbral": umbral, "error": str(exc),
                "descripcion": "No se pudo reintegrar con tolerancias más finas."}
    return _resultado_reintegracion(
        "convergencia", comparacion, umbral, umbral_estadistico,
        {"factor_tolerancia": factor,
         "descripcion": f"La solución no cambia al afinar las tolerancias {factor:g} veces."})


def verificar_metodo_alternativo(campo, solucion, parametros=None, rtol=1e-8, atol=1e-10,
                                 metodo="RK45", umbral=UMBRAL_METODO_ALTERNATIVO,
                                 fraccion_ventana=FRACCION_VENTANA,
                                 umbral_estadistico=UMBRAL_ESTADISTICO):
    """Reintegra con un método distinto: el resultado no debe depender del integrador."""
    alternativo = "DOP853" if metodo != "DOP853" else "Radau"
    try:
        comparacion = _comparar_reintegracion(campo, solucion, parametros, fraccion_ventana,
                                              metodo=alternativo, rtol=rtol, atol=atol)
    except (RuntimeError, ValueError) as exc:
        return {"nombre": "metodo_alternativo", "ok": False, "umbral": umbral,
                "metodo": alternativo, "error": str(exc),
                "descripcion": f"No se pudo reintegrar con {alternativo}."}
    return _resultado_reintegracion(
        "metodo_alternativo", comparacion, umbral, umbral_estadistico,
        {"metodo": alternativo,
         "descripcion": f"{metodo} y {alternativo} coinciden en el tramo inicial."})


def verificar_solucion_exacta(solucion, exacta, variable_independiente, componente=0,
                              umbral=1e-6, parametros=None):
    """Contrasta contra una solución analítica aportada por el cliente.

    `exacta` es una función compilada por `matematica.expresiones`, que se llama
    por nombre de símbolo. Se le pasan también los parámetros del modelo, porque
    una solución cerrada suele depender de ellos: la del logístico es
    K/(1 + (K/y0 - 1)e^{-rt}), que no se puede evaluar sin r ni K.
    """
    tiempos = np.asarray(solucion.t, dtype=float)
    valores_simbolos = {**(parametros or {}), variable_independiente: tiempos}
    try:
        valores = np.asarray(exacta(**valores_simbolos), dtype=float)
    except Exception as exc:                       # expresión válida pero no evaluable aquí
        return {"nombre": "solucion_exacta", "ok": False, "error": str(exc),
                "descripcion": "No se pudo evaluar la solución exacta sobre la malla."}
    valores = np.broadcast_to(valores, tiempos.shape)
    # Criterio mixto, absoluto cerca de cero y relativo donde la solución es
    # grande: junto a una explosión (y = 2/(2 − 3x²) cerca de x = √6/3) el error
    # absoluto de una integración correcta crece con |y|.
    diferencia = np.abs(np.asarray(solucion.y[componente], dtype=float) - valores)
    relativo = float(np.max(diferencia / (1.0 + np.abs(valores))))
    return {"nombre": "solucion_exacta", "ok": relativo <= umbral,
            "error_maximo": float(np.max(diferencia)), "error_relativo_maximo": relativo,
            "umbral": umbral, "criterio": "|y_num - y_exacta| <= umbral*(1 + |y_exacta|) en cada punto",
            "descripcion": "La solución numérica coincide con la analítica aportada."}


#: Variación relativa admitida de una integral primera a lo largo de la trayectoria.
UMBRAL_INTEGRAL_PRIMERA = 1e-6


def verificar_integral_primera(solucion, integral, estados, independiente=None,
                               umbral=UMBRAL_INTEGRAL_PRIMERA):
    """Una cantidad que el desarrollo probó constante debe serlo en la trayectoria numérica.

    El desarrollo demuestra dH/dt ≡ 0 de forma simbólica; esto lo contrasta con
    lo que el integrador produjo, que es independiente de esa demostración.
    """
    import sympy as sp
    variables = list(estados) + ([independiente] if independiente is not None else [])
    try:
        funcion = sp.lambdify(variables, integral, "numpy")
        argumentos = [np.asarray(solucion.y[i], dtype=float) for i in range(len(estados))]
        if independiente is not None:
            argumentos.append(np.asarray(solucion.t, dtype=float))
        valores = np.broadcast_to(np.asarray(funcion(*argumentos), dtype=float), solucion.t.shape)
    except Exception as exc:
        return {"nombre": "integral_primera", "ok": False, "concluyente": False,
                "error": str(exc), "descripcion": "No se pudo evaluar la integral primera."}
    deriva = float(np.max(np.abs(valores - valores[0]))) / max(1.0, abs(float(valores[0])))
    return {"nombre": "integral_primera", "ok": deriva <= umbral, "desvio": deriva, "umbral": umbral,
            "tipo": "numerica",
            "descripcion": f"H = {sp.sstr(integral)} se conserva a lo largo de la trayectoria numérica."}


def verificar(campo, solucion, y0, parametros=None, rtol=1e-8, atol=1e-10, metodo="RK45",
              exacta=None, variable_independiente="t", umbrales=None):
    """Ejecuta todas las comprobaciones aplicables y resume el veredicto.

    Devuelve un diccionario con `ok` global y el detalle de cada prueba. `ok` es
    la conjunción de las pruebas concluyentes: quien llame debe negarse a emitir
    conclusiones si resulta falso.
    """
    umbrales = umbrales or {}
    pruebas = [
        verificar_condicion_inicial(solucion, y0,
                                    umbrales.get("condicion_inicial", UMBRAL_CONDICION_INICIAL)),
        verificar_residuo(campo, solucion, parametros,
                          umbrales.get("residuo", UMBRAL_RESIDUO)),
        verificar_convergencia(campo, solucion, parametros, rtol, atol, metodo,
                               umbral=umbrales.get("convergencia", UMBRAL_CONVERGENCIA)),
        verificar_metodo_alternativo(campo, solucion, parametros, rtol, atol, metodo,
                                     umbral=umbrales.get("metodo_alternativo",
                                                         UMBRAL_METODO_ALTERNATIVO)),
    ]
    if exacta is not None:
        pruebas.append(verificar_solucion_exacta(
            solucion, exacta, variable_independiente,
            umbral=umbrales.get("solucion_exacta", 1e-6), parametros=parametros))

    fallidas = [p["nombre"] for p in pruebas if not p["ok"]]
    return {
        "ok": not fallidas,
        "pruebas": pruebas,
        "fallidas": fallidas,
        "resumen": ("Todas las verificaciones se superaron."
                    if not fallidas else
                    f"No se superaron: {', '.join(fallidas)}. No se emiten conclusiones."),
    }
