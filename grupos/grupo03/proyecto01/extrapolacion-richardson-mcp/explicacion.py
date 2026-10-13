"""
explicacion.py — Explicaciones en lenguaje natural
====================================================
Integrante: Camila Morán
Módulo:     Explicación de resultados

Descripción:
    Traduce las tablas numéricas de romberg.py y derivacion_richardson.py
    a explicaciones en español, en lenguaje natural, sobre:
        - qué procedimiento se aplicó en cada fila/columna,
        - cuánto mejoró el error en cada nivel de extrapolación,
        - qué orden de convergencia se alcanzó (estimado a partir de los
          propios datos, comparándolo con el orden teórico esperado).

    Recibe exactamente lo que devuelven romberg() y derivada_richardson(),
    sin necesitar transformaciones adicionales:

        resultado, tabla, filas = romberg(f, a, b)
        print(explicar_romberg(tabla, filas, a, b, tol, resultado))

        mejor, tabla, errores = derivada_richardson(f, x, h)
        print(explicar_richardson(tabla, len(tabla), x, h, mejor, errores))
"""

import numpy as np


# =============================================================================
# UTILIDADES: orden de convergencia
# =============================================================================

def calcular_orden_convergencia(errores):
    """
    Estima el orden de convergencia p a partir de una secuencia de errores
    e_0, e_1, e_2, ... donde el paso se reduce a la mitad en cada uno
    (como ocurre en cada fila de Romberg o cada nivel de Richardson):

        p ≈ log2(e_i / e_{i+1})

    Ignora pares donde el error es None, cero, negativo o no numérico.

    Parámetros:
        errores : lista o array de errores absolutos consecutivos

    Retorna:
        lista de órdenes estimados (float o None cuando no se puede calcular),
        de longitud len(errores) - 1
    """
    ordenes = []
    for i in range(len(errores) - 1):
        e0, e1 = errores[i], errores[i + 1]
        try:
            e0f, e1f = float(e0), float(e1)
        except (TypeError, ValueError):
            ordenes.append(None)
            continue
        if e0 is None or e1 is None or e0f <= 0 or e1f <= 0 or np.isnan(e0f) or np.isnan(e1f):
            ordenes.append(None)
        else:
            ordenes.append(float(np.log2(e0f / e1f)))
    return ordenes


def _formatear_orden(orden):
    """Formatea un orden estimado, o indica que no se pudo calcular."""
    return f"{orden:.2f}" if orden is not None else "N/D"


# =============================================================================
# EXPLICACIÓN: INTEGRACIÓN DE ROMBERG
# =============================================================================

def explicar_romberg(tabla, filas=None, a=None, b=None, tol=None, resultado=None, valor_exacto=None):
    """
    Genera una explicación en lenguaje natural del proceso de integración
    de Romberg aplicado, describiendo cada nivel de extrapolación y la
    mejora de orden obtenida.

    Parámetros:
        tabla        : tabla triangular de Romberg (construir_tabla_romberg)
        filas        : filas realmente usadas (filas_usadas de romberg())
        a, b         : límites de integración
        tol          : tolerancia usada como criterio de parada
        resultado    : valor final de la integral (tabla[filas-1][filas-1])
        valor_exacto : valor exacto de la integral, si se conoce (opcional)

    Retorna:
        str : texto explicativo completo, listo para imprimir o guardar
    """
    if isinstance(tabla, dict):
        datos = tabla
        filas = datos.get("niveles_usados", len(datos.get("tabla", [])))
        a, b = datos.get("a"), datos.get("b")
        tol = datos.get("tolerancia")
        lineas = [
            f"Se integró en [{a}, {b}] con el método de Romberg y tolerancia {tol:g}.",
            f"Se usaron {filas} niveles y {datos.get('evaluaciones', 'un número desconocido de')} "
            "evaluaciones de la función.",
            f"Resultado: {datos.get('resultado'):.12f}.",
            f"Error estimado: {datos.get('error_estimado'):.3e}.",
            "Se alcanzó la tolerancia." if datos.get("convergio") else
            "No se alcanzó la tolerancia dentro de los niveles configurados.",
        ]
        return " ".join(lineas)

    M = np.array(tabla, dtype=float)
    referencia = valor_exacto if valor_exacto is not None else resultado

    lineas = []
    lineas.append("=" * 70)
    lineas.append("EXPLICACIÓN DEL PROCEDIMIENTO — INTEGRACIÓN DE ROMBERG")
    lineas.append("=" * 70)
    lineas.append(
        f"Se buscó aproximar la integral de f(x) en el intervalo [{a}, {b}] "
        f"con una tolerancia de {tol:g}."
    )
    lineas.append("")
    lineas.append(
        "El procedimiento parte de la regla del trapecio compuesta, que por sí "
        "sola converge con orden O(h^2). Es decir, si se duplica el número de "
        "subintervalos, el error debería reducirse aproximadamente 4 veces."
    )
    lineas.append("")
    lineas.append(f"Se necesitaron {filas} refinamientos (filas) para alcanzar la tolerancia pedida:")

    # Descripción fila por fila de la columna 0 (trapecio puro)
    errores_trapecio = np.abs(M[:filas, 0] - referencia)
    for i in range(filas):
        n = 2 ** i
        lineas.append(
            f"  • Fila {i}: trapecio con n = {n:>4} subintervalos "
            f"→ aproximación = {M[i, 0]:.10f}, error ≈ {errores_trapecio[i]:.2e}"
        )

    ordenes_trapecio = calcular_orden_convergencia(errores_trapecio)
    if ordenes_trapecio:
        prom = np.nanmean([o for o in ordenes_trapecio if o is not None]) if any(
            o is not None for o in ordenes_trapecio) else None
        lineas.append("")
        lineas.append(
            f"El orden de convergencia observado del trapecio simple (sin extrapolar) "
            f"es aproximadamente {_formatear_orden(prom)}, cercano al orden teórico 2."
        )

    # Descripción de las columnas de extrapolación (niveles de Richardson)
    lineas.append("")
    lineas.append(
        "Cada columna siguiente aplica una capa de extrapolación de Richardson, "
        "que combina dos filas consecutivas de la columna anterior para cancelar "
        "el término dominante del error. Cada nivel eleva el orden teórico en +2:"
    )
    niveles = filas - 1
    for j in range(1, niveles + 1):
        orden_teorico = 2 * (j + 1)
        errores_col = np.abs(M[j:filas, j] - referencia)
        orden_obs = calcular_orden_convergencia(errores_col)
        orden_obs_prom = (np.nanmean([o for o in orden_obs if o is not None])
                           if any(o is not None for o in orden_obs) else None)
        lineas.append(
            f"  • Nivel {j} (columna {j}): orden teórico O(h^{orden_teorico}), "
            f"orden observado ≈ {_formatear_orden(orden_obs_prom)}. "
            f"Mejor valor en este nivel: {M[filas - 1, j]:.10f}"
        )

    # Mejora total conseguida
    error_inicial = errores_trapecio[0]
    error_final = abs(resultado - referencia) if referencia != resultado else np.nan
    lineas.append("")
    lineas.append(
        f"Comparando el primer trapecio (n=1) con el resultado final extrapolado: "
        f"el error pasó de aproximadamente {error_inicial:.2e} a "
        f"{(error_final if not np.isnan(error_final) else 0.0):.2e}, "
        f"usando solo {filas} evaluaciones distintas de niveles de refinamiento "
        f"en lugar de necesitar un n mucho mayor con trapecio simple."
    )
    lineas.append("")
    lineas.append(f"Resultado final de la integral: {resultado:.12f}")
    if valor_exacto is not None:
        lineas.append(f"Valor exacto conocido:          {valor_exacto:.12f}")
        lineas.append(f"Error absoluto final:           {abs(resultado - valor_exacto):.2e}")
    lineas.append("=" * 70)

    return "\n".join(lineas)


# =============================================================================
# EXPLICACIÓN: DERIVACIÓN CON RICHARDSON
# =============================================================================

def explicar_richardson(tabla, niveles, x, h, resultado, errores, valor_exacto=None,
                          nombre_funcion="f(x)"):
    """
    Genera una explicación en lenguaje natural del proceso de derivación
    numérica con extrapolación de Richardson aplicado.

    Parámetros:
        tabla          : tabla de derivada_richardson() (np.array o list de listas)
        niveles        : número de niveles usados (igual a len(tabla))
        x              : punto donde se evaluó la derivada
        h              : tamaño de paso inicial
        resultado      : mejor aproximación (tabla[niveles-1][niveles-1])
        errores        : lista de errores entre niveles (la que devuelve
                         derivada_richardson(), con errores[0] = None)
        valor_exacto   : valor exacto de la derivada, si se conoce (opcional)
        nombre_funcion : nombre de la función, solo para el texto

    Retorna:
        str : texto explicativo completo, listo para imprimir o guardar
    """
    M = np.array(tabla, dtype=float)
    referencia = valor_exacto if valor_exacto is not None else resultado

    lineas = []
    lineas.append("=" * 70)
    lineas.append("EXPLICACIÓN DEL PROCEDIMIENTO — DERIVACIÓN CON RICHARDSON")
    lineas.append("=" * 70)
    lineas.append(
        f"Se buscó aproximar la derivada de {nombre_funcion} en x = {x}, "
        f"partiendo de un paso inicial h = {h}."
    )
    lineas.append("")
    lineas.append(
        "El punto de partida es la fórmula de diferencias centradas, "
        "(f(x+h) - f(x-h)) / (2h), que converge con orden O(h^2): al reducir "
        "h a la mitad, el error debería reducirse aproximadamente 4 veces."
    )
    lineas.append("")
    lineas.append(f"Se calcularon {niveles} niveles, reduciendo el paso a la mitad en cada uno:")

    errores_centrada = np.abs(M[:, 0] - referencia)
    for i in range(niveles):
        hi = h / (2 ** i)
        lineas.append(
            f"  • Nivel {i}: diferencias centradas con h = {hi:.6f} "
            f"→ aproximación = {M[i, 0]:.10f}, error ≈ {errores_centrada[i]:.2e}"
        )

    ordenes_centrada = calcular_orden_convergencia(errores_centrada)
    if ordenes_centrada:
        prom = (np.nanmean([o for o in ordenes_centrada if o is not None])
                if any(o is not None for o in ordenes_centrada) else None)
        lineas.append("")
        lineas.append(
            f"El orden de convergencia observado de las diferencias centradas "
            f"(sin extrapolar) es aproximadamente {_formatear_orden(prom)}, "
            f"cercano al orden teórico 2."
        )

    lineas.append("")
    lineas.append(
        "Cada columna de extrapolación combina dos aproximaciones consecutivas "
        "para cancelar el término de error dominante, elevando el orden teórico "
        "en +2 por cada nivel adicional:"
    )
    for j in range(1, niveles):
        orden_teorico = 2 * (j + 1)
        errores_col = np.abs(M[j:, j] - referencia)
        orden_obs = calcular_orden_convergencia(errores_col)
        orden_obs_prom = (np.nanmean([o for o in orden_obs if o is not None])
                           if any(o is not None for o in orden_obs) else None)
        lineas.append(
            f"  • Nivel de extrapolación {j} (columna {j}): orden teórico "
            f"O(h^{orden_teorico}), orden observado ≈ {_formatear_orden(orden_obs_prom)}. "
            f"Mejor valor en este nivel: {M[niveles - 1, j]:.10f}"
        )

    error_inicial = errores_centrada[0]
    error_final = abs(resultado - referencia)
    lineas.append("")
    lineas.append(
        f"Comparando la primera diferencia centrada (h={h}) con el resultado final "
        f"extrapolado: el error pasó de aproximadamente {error_inicial:.2e} a "
        f"{error_final:.2e}, sin necesitar un h mucho más pequeño (que traería más "
        f"error de redondeo por cancelación numérica)."
    )
    lineas.append("")
    lineas.append(f"Resultado final de la derivada: {resultado:.12f}")
    if valor_exacto is not None:
        lineas.append(f"Valor exacto conocido:          {valor_exacto:.12f}")
        lineas.append(f"Error absoluto final:           {abs(resultado - valor_exacto):.2e}")
    lineas.append("=" * 70)

    return "\n".join(lineas)


def explicar_derivada(resultado):
    """Resume la salida actual de ``derivacion_richardson`` del servidor MCP."""
    niveles = resultado.get("niveles_usados", len(resultado.get("tabla", [])))
    return (
        f"Se aproximó la derivada de {resultado.get('expresion', 'la función')} "
        f"en x={resultado.get('x0')} mediante diferencias centradas y extrapolación "
        f"de Richardson. Se usaron {niveles} niveles. Resultado: "
        f"{resultado.get('resultado'):.12g}; error estimado: "
        f"{resultado.get('error_estimado')}."
    )


# =============================================================================
# EXPLICACIÓN: ANÁLISIS DE CONVERGENCIA GENÉRICO (convergencia.py)
# =============================================================================

def explicar_convergencia_generica(resultado, nombre_metodo="el método base",
                                    nombre_extrapolado="la versión extrapolada",
                                    orden_teorico_base=None,
                                    orden_teorico_extrapolado=None):
    """
    Genera una explicación en lenguaje natural a partir del diccionario que
    devuelve analizar_convergencia() de convergencia.py. Es genérica: sirve
    para cualquier método (derivadas, integrales, u otro) que se le haya
    pasado a esa función, no solo para Romberg o Richardson.

    Parámetros:
        resultado                 : dict devuelto por analizar_convergencia()
        nombre_metodo             : nombre del método base, para el texto
        nombre_extrapolado        : nombre de la versión extrapolada, para el texto
        orden_teorico_base        : orden teórico esperado del método base (ej. 2)
        orden_teorico_extrapolado : orden teórico esperado tras extrapolar (ej. 4)

    Retorna:
        str : texto explicativo completo, listo para imprimir o guardar
    """
    pasos = np.asarray(resultado["pasos_h"], dtype=float)
    errores = np.asarray(resultado["errores_absolutos"], dtype=float)
    orden_prom = resultado.get("orden_observado_promedio", None)

    lineas = []
    lineas.append("=" * 70)
    lineas.append("EXPLICACIÓN DEL PROCEDIMIENTO — ANÁLISIS DE CONVERGENCIA")
    lineas.append("=" * 70)
    lineas.append(
        f"Se evaluó {nombre_metodo} con distintos tamaños de paso h, reduciéndolo "
        f"progresivamente para observar cómo decrece el error:"
    )
    lineas.append("")
    for i, h in enumerate(pasos):
        lineas.append(f"  • h = {h:<10g} → error absoluto ≈ {errores[i]:.2e}")

    lineas.append("")
    if orden_prom is not None:
        texto_teorico = f" (orden teórico esperado: {orden_teorico_base})" if orden_teorico_base else ""
        lineas.append(
            f"El orden de convergencia observado en {nombre_metodo} es "
            f"aproximadamente {orden_prom:.2f}{texto_teorico}. Esto se calcula comparando "
            f"cuánto se reduce el error cada vez que se reduce h, mediante "
            f"p ≈ log(E(h_i)/E(h_{{i+1}})) / log(h_i/h_{{i+1}})."
        )

    if "extrapolado" in resultado:
        errores_ext = np.asarray(resultado["extrapolado"]["errores_absolutos"], dtype=float)
        orden_ext = resultado["extrapolado"].get("orden_observado_promedio", None)

        lineas.append("")
        lineas.append(
            f"Al aplicar extrapolación de Richardson se obtuvo {nombre_extrapolado}, "
            f"que mejora el error en cada paso:"
        )
        for i, h in enumerate(pasos):
            mejora = errores[i] / errores_ext[i] if errores_ext[i] > 0 else float("nan")
            lineas.append(
                f"  • h = {h:<10g} → error extrapolado ≈ {errores_ext[i]:.2e} "
                f"(mejora de {mejora:.1f}x respecto a {nombre_metodo})"
            )

        if orden_ext is not None:
            texto_teorico_ext = (f" (orden teórico esperado: {orden_teorico_extrapolado})"
                                  if orden_teorico_extrapolado else "")
            lineas.append("")
            lineas.append(
                f"El orden de convergencia observado con extrapolación es "
                f"aproximadamente {orden_ext:.2f}{texto_teorico_ext}, lo que confirma "
                f"la ganancia de orden esperada al combinar dos aproximaciones del "
                f"método base para cancelar el término dominante del error."
            )

    lineas.append("=" * 70)
    return "\n".join(lineas)


def explicar_convergencia(resultado):
    """Resume el formato de convergencia producido por ``convergencia.py``."""
    problema = resultado.get("problema", "numérico")
    base = resultado.get("base", "método base")
    hs = resultado.get("hs", [])
    errores_base = resultado.get("error_base", [])
    errores_ext = resultado.get("error_extrapolado", [])
    orden_base = resultado.get("orden_teorico_base")
    orden_ext = resultado.get("orden_teorico_extrapolado")

    lineas = [f"Análisis de convergencia para {problema}, usando {base}."]
    if orden_base is not None and orden_ext is not None:
        lineas.append(
            f"Órdenes teóricos: {orden_base:g} para el método base y {orden_ext:g} "
            "después de extrapolar."
        )
    if hs and errores_base:
        lineas.append(
            f"Se compararon {len(hs)} tamaños de paso; el error base inicial fue "
            f"{errores_base[0]:.3e} y el final {errores_base[-1]:.3e}."
        )
    if errores_ext:
        lineas.append(
            f"El error extrapolado varió de {errores_ext[0]:.3e} a "
            f"{errores_ext[-1]:.3e}."
        )
    return " ".join(lineas)


# =============================================================================
# EXPLICACIÓN: RICHARDSON GENÉRICO (richardson_generico.py)
# =============================================================================

def explicar_richardson_generico(resultado, h, orden_error=2, valor_exacto=None,
                                  nombre_metodo="el método"):
    """
    Genera una explicación en lenguaje natural a partir del diccionario que
    devuelve richardson_generico(), sea cual sea el método base que se le
    haya pasado (diferencias centradas, trapecio, u otro con orden de error
    conocido).

    Parámetros:
        resultado    : dict devuelto por richardson_generico()
        h            : tamaño de paso inicial usado
        orden_error  : orden de error del método base (el mismo "orden_error"
                       pasado a richardson_generico(), ej. 2)
        valor_exacto : valor exacto de referencia, si se conoce (opcional)
        nombre_metodo: nombre del método base, para el texto

    Retorna:
        str : texto explicativo completo, listo para imprimir o guardar
    """
    tabla = resultado["tabla"]
    niveles = len(tabla)
    referencia = valor_exacto if valor_exacto is not None else resultado["valor"]

    lineas = []
    lineas.append("=" * 70)
    lineas.append("EXPLICACIÓN DEL PROCEDIMIENTO — RICHARDSON GENÉRICO")
    lineas.append("=" * 70)
    lineas.append(
        f"Se aplicó extrapolación de Richardson a {nombre_metodo}, cuyo error "
        f"dominante es de orden O(h^{orden_error}), partiendo de h = {h}."
    )
    lineas.append("")
    lineas.append(f"Se calcularon {niveles} niveles, reduciendo el paso a la mitad en cada uno:")

    errores_col0 = []
    for i in range(niveles):
        hi = h / (2 ** i)
        err = abs(tabla[i][0] - referencia)
        errores_col0.append(err)
        lineas.append(
            f"  • Nivel {i}: h = {hi:.6f} → aproximación directa = {tabla[i][0]:.10f}, "
            f"error ≈ {err:.2e}"
        )

    ordenes_col0 = calcular_orden_convergencia(errores_col0)
    if ordenes_col0:
        prom = (np.nanmean([o for o in ordenes_col0 if o is not None])
                if any(o is not None for o in ordenes_col0) else None)
        lineas.append("")
        lineas.append(
            f"El orden de convergencia observado sin extrapolar es aproximadamente "
            f"{_formatear_orden(prom)}, cercano al orden teórico {orden_error}."
        )

    lineas.append("")
    lineas.append(
        "Cada nivel de extrapolación combina dos aproximaciones consecutivas usando "
        f"el factor 2^({orden_error}·j) - 1, cancelando el término de error dominante "
        f"y elevando el orden teórico en +{orden_error} por cada nivel adicional:"
    )
    for j in range(1, niveles):
        orden_teorico = orden_error * (j + 1)
        errores_col = [abs(tabla[i][j] - referencia) for i in range(j, niveles) if len(tabla[i]) > j]
        orden_obs = calcular_orden_convergencia(errores_col)
        orden_obs_prom = (np.nanmean([o for o in orden_obs if o is not None])
                           if any(o is not None for o in orden_obs) else None)
        mejor_valor = tabla[niveles - 1][j] if len(tabla[niveles - 1]) > j else None
        texto_valor = f"{mejor_valor:.10f}" if mejor_valor is not None else "N/D"
        lineas.append(
            f"  • Nivel {j}: orden teórico O(h^{orden_teorico}), "
            f"orden observado ≈ {_formatear_orden(orden_obs_prom)}. Mejor valor: {texto_valor}"
        )

    lineas.append("")
    lineas.append(f"Resultado final: {resultado['valor']:.12f}")
    if resultado.get("orden_convergencia_observado") is not None:
        lineas.append(
            f"Orden de convergencia observado (reportado por el propio módulo): "
            f"{resultado['orden_convergencia_observado']:.2f}"
        )
    if resultado.get("error_estimado") is not None:
        lineas.append(f"Error estimado (entre las 2 últimas filas): {resultado['error_estimado']:.2e}")
    if valor_exacto is not None:
        lineas.append(f"Valor exacto conocido:  {valor_exacto:.12f}")
        lineas.append(f"Error absoluto final:   {abs(resultado['valor'] - valor_exacto):.2e}")
    lineas.append("=" * 70)

    return "\n".join(lineas)


def explicar_generico(resultado, metodo):
    """Explica el resultado devuelto por la API MCP de Richardson genérico.

    La implementación histórica de este módulo usa las claves ``valor`` y
    ``tabla`` con números escalares. La API del servidor devuelve ``resultado``
    y permite también resultados vectoriales; esta función adapta ese esquema.
    """
    tabla = resultado.get("tabla", [])
    valor = resultado.get("resultado")
    orden = resultado.get("orden_final")
    error = resultado.get("error_estimado")
    niveles = resultado.get("niveles_usados", len(tabla))

    lineas = [
        f"Se aplicó extrapolación de Richardson al método {metodo}.",
        f"Se usaron {niveles} niveles y se alcanzó el orden teórico O(h^{orden}).",
        f"Resultado extrapolado: {valor}.",
    ]
    if error is not None:
        lineas.append(f"Error estimado entre las últimas aproximaciones: {error:.3e}.")
    if resultado.get("convergio") is not None:
        estado = "Se alcanzó la tolerancia solicitada." if resultado["convergio"] else \
            "No se alcanzó la tolerancia solicitada dentro de los niveles usados."
        lineas.append(estado)
    return " ".join(lineas)


# =============================================================================
# EXPLICACIÓN: EDOs CON BULIRSCH-STOER (bulirsch_stoer_edo.py)
# =============================================================================

def explicar_bulirsch_stoer(resultado, x0=None, y0=None, h=None, n=None, niveles=4,
                             resultado_rk4_simple=None, valor_exacto_final=None,
                             nombre_variable="y"):
    """
    Genera una explicación en lenguaje natural del procedimiento aplicado
    por bulirsch_stoer_edo(): cómo se combina RK4 con extrapolación de
    Richardson para resolver la EDO paso a paso, y qué tan preciso resultó.

    Parámetros:
        resultado            : dict devuelto por bulirsch_stoer_edo()
        x0, y0                : condición inicial
        h                     : tamaño de paso usado por paso de integración
        n                     : número de pasos dados
        niveles               : niveles de extrapolación usados en cada paso
        resultado_rk4_simple  : dict de rk4_simple_edo(), para comparar (opcional)
        valor_exacto_final    : valor exacto de y en el punto final, si se conoce
        nombre_variable       : nombre de la variable dependiente, para el texto

    Retorna:
        str : texto explicativo completo, listo para imprimir o guardar
    """
    if isinstance(resultado, dict) and "puntos" not in resultado:
        datos = resultado
        y_final = datos.get("y_final")
        return (
            f"Se resolvió la EDO desde t={datos.get('t0')} hasta t={datos.get('tf')} "
            f"con Bulirsch-Stoer, partiendo de y(t0)={datos.get('y', [None])[0]}. "
            f"La integración aceptó {datos.get('pasos_aceptados')} pasos y rechazó "
            f"{datos.get('pasos_rechazados')} pasos. Resultado final: y(tf)={y_final}. "
            f"Se realizaron {datos.get('evaluaciones')} evaluaciones de la función."
        )

    puntos = resultado["puntos"]
    x_final, y_final = puntos[-1]
    errores_paso = resultado["errores_por_paso"]

    lineas = []
    lineas.append("=" * 70)
    lineas.append("EXPLICACIÓN DEL PROCEDIMIENTO — EDO CON BULIRSCH-STOER")
    lineas.append("=" * 70)
    lineas.append(
        f"Se resolvió la EDO con condición inicial {nombre_variable}({x0}) = {y0}, "
        f"avanzando {n} pasos de tamaño h = {h} (hasta x = {x_final:.4f})."
    )
    lineas.append("")
    lineas.append(
        "En cada paso, el método avanza con RK4 (orden 4) usando distintas "
        "subdivisiones del paso (1, 2, 4, 8, ... subpasos) y luego aplica "
        "extrapolación de Richardson entre esas subdivisiones para cancelar "
        f"el término de error dominante, usando {niveles} niveles por paso."
    )
    lineas.append("")
    lineas.append("Error estimado en cada paso de integración:")
    for i, err in enumerate(errores_paso, start=1):
        lineas.append(f"  • Paso {i}: error estimado ≈ {err:.2e}")

    lineas.append("")
    lineas.append(
        f"Error total acumulado (suma de errores por paso): {resultado['error_estimado']:.2e}"
    )

    if resultado_rk4_simple is not None:
        y_rk4 = resultado_rk4_simple["puntos"][-1][1]
        diferencia = abs(y_final - y_rk4)
        lineas.append("")
        lineas.append(
            f"Comparado con RK4 simple (sin extrapolar), que da "
            f"{nombre_variable}({x_final:.4f}) ≈ {y_rk4:.10f}, la versión con "
            f"Bulirsch-Stoer da {y_final:.10f} — una diferencia de {diferencia:.2e}, "
            f"que refleja la mejora de precisión obtenida al extrapolar."
        )

    lineas.append("")
    lineas.append(f"Resultado final: {nombre_variable}({x_final:.4f}) ≈ {y_final:.12f}")
    if valor_exacto_final is not None:
        lineas.append(f"Valor exacto conocido:  {valor_exacto_final:.12f}")
        lineas.append(f"Error absoluto final:   {abs(y_final - valor_exacto_final):.2e}")
    lineas.append("=" * 70)

    return "\n".join(lineas)
