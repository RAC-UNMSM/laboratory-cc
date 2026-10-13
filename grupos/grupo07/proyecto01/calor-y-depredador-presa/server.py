from mcp.server import MCPServer
import matematica
import storage
import visualizacion
import reporte
import validacion
import numpy as np

mcp = MCPServer("grupo07-calor-y-depredador-presa")


@mcp.tool()
def simular_lotka_volterra(
    alpha: float, beta: float, delta: float, gamma: float, 
    presas_inicial: float, depredadores_inicial: float, tiempo_max: float
) -> str:
    """
    Simula el modelo presa-depredador de Lotka-Volterra y devuelve una imagen con las
    series temporales y el plano de fase, un enlace al reporte HTML completo y los datos
    numéricos de picos y valles poblacionales.

    Parámetros:
    - alpha: Tasa de crecimiento de las presas (1/mes). Debe ser > 0.
    - beta: Tasa de depredación (1/(presa·mes)). Debe ser > 0.
    - delta: Tasa de crecimiento de los depredadores por presa consumida (1/(depredador·mes)). Debe ser > 0.
    - gamma: Tasa de mortalidad de los depredadores (1/mes). Debe ser > 0.
    - presas_inicial: Población inicial de presas (individuos). Debe ser > 0.
    - depredadores_inicial: Población inicial de depredadores (individuos). Debe ser > 0.
    - tiempo_max: Tiempo total de simulación en meses. Debe estar entre 0 y 5000.

    Límites adicionales validados por el servidor:
    - El producto de la tasa más grande por el tiempo (max(alpha, beta, delta, gamma) * tiempo_max)
      debe ser menor o igual a 20000.

    Muestra al usuario la imagen y el enlace del reporte tal como vienen en la respuesta.
    """

    # Filtro de validación estricto
    try:
        validacion.validar_parametros_lotka(
            alpha, beta, delta, gamma, presas_inicial, depredadores_inicial, tiempo_max
        )
    except validacion.ValidationError as e:
        return f"Error de validación rechazado por el servidor: {str(e)}\nPor favor, corrige los parámetros y vuelve a intentar."

    # 1. Cálculos matemáticos locales
    tiempo, presas, depredadores = matematica.resolver_lotka_volterra(
        alpha, beta, delta, gamma, presas_inicial, depredadores_inicial, tiempo_max
    )
    
    # 2. Extraer TODOS los datos (picos y valles)
    idx_max_presas = np.argmax(presas)
    idx_min_presas = np.argmin(presas)
    idx_max_dep = np.argmax(depredadores)
    idx_min_dep = np.argmin(depredadores)
    
    presas_max = presas[idx_max_presas]
    mes_presas_max = tiempo[idx_max_presas]
    presas_min = presas[idx_min_presas]
    mes_presas_min = tiempo[idx_min_presas]
    
    dep_max = depredadores[idx_max_dep]
    mes_dep_max = tiempo[idx_max_dep]
    dep_min = depredadores[idx_min_dep]
    mes_dep_min = tiempo[idx_min_dep]
    
    # 3. Generar gráficos y reporte HTML en MEMORIA
    png_bytes = visualizacion.graficar_lotka_volterra_bytes(tiempo, presas, depredadores)
    html = reporte.generar_reporte_lotka_volterra_html(
        presas_max, mes_presas_max, presas_min, mes_presas_min,
        dep_max, mes_dep_max, dep_min, mes_dep_min, png_bytes
    )

    # 4. INTEGRACIÓN CON SEAWEEDFS (Subimos imagen y reporte)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    url_reporte = storage.subir_reporte(html)
    
    datos_numericos = (
        f"--- Datos Numéricos ---\n"
        f"- Presas: Pico {presas_max:.2f} (mes {mes_presas_max:.2f}), VALLE {presas_min:.2f} (mes {mes_presas_min:.2f})\n"
        f"- Depredadores: Pico {dep_max:.2f} (mes {mes_dep_max:.2f}), VALLE {dep_min:.2f} (mes {mes_dep_min:.2f})\n"
    )

    if url_imagen_nube and url_reporte:
        encabezado = (
            f"Simulación exitosa.\n\n"
            f"![Gráfico de Resultados]({url_imagen_nube})\n\n"
            f"[Abrir el reporte completo]({url_reporte})\n\n"
        )
    else:
        encabezado = "Simulación exitosa. No se pudo publicar la imagen ni el reporte.\n\n"
    
    return encabezado + datos_numericos


@mcp.tool()
def simular_calor_2d(
    difusividad: float, tamaño_malla: int, tiempo_total: float, 
    longitud_placa: float, radio_fuente: float
) -> str:
    """
    Simula la difusión térmica bidimensional (Ecuación del Calor 2D) en una placa cuadrada
    y devuelve una imagen con el mapa de calor y la evolución del centro, un enlace al
    reporte HTML completo y los datos numéricos de temperatura.
    La temperatura inicial está fija en el modelo: 20 °C en la placa (con bordes fijos a 20 °C)
    y 100 °C en la fuente circular central.

    Parámetros:
    - difusividad: Coeficiente de difusividad térmica del material (m²/s). Debe ser > 0.
    - tamaño_malla: Número de nodos por lado de la malla (entero entre 5 y 200).
    - tiempo_total: Tiempo total de simulación en segundos. Debe ser > 0.
    - longitud_placa: Longitud del lado de la placa cuadrada (m). Debe ser > 0.
    - radio_fuente: Radio de la fuente térmica central (m). Debe ser > 0 y menor que la mitad de longitud_placa.

    Límites adicionales validados por el servidor:
    - Tope de cómputo: la cantidad de pasos de tiempo (tiempo_total / dt, donde
      dt = 0.9 * dx² / (4 * difusividad) y dx = longitud_placa / (tamaño_malla - 1))
      no debe superar los 20000 pasos.

    Muestra al usuario la imagen y el enlace del reporte tal como vienen en la respuesta.
    """

    # Filtro de validación termodinámica
    try:
        validacion.validar_parametros_calor(
            difusividad, tamaño_malla, tiempo_total, longitud_placa, radio_fuente
        )
    except validacion.ValidationError as e:
        return f"Error de validación rechazado por el servidor: {str(e)}\nPor favor, ajusta la configuración física."

    # 1. Cálculos matemáticos
    matriz_final, tiempo_hist, temp_centro = matematica.resolver_calor_2d(
        difusividad, tamaño_malla, tiempo_total, longitud_placa, radio_fuente
    )
    
    # 2. Extraer hitos termodinámicos
    temp_max = np.max(matriz_final)
    temp_min = np.min(matriz_final)
    temp_prom = np.mean(matriz_final)
    idx_mitad = len(tiempo_hist) // 2
    temp_centro_mitad = temp_centro[idx_mitad]
    
    # 3. Generar gráficos y reporte HTML en MEMORIA
    png_bytes = visualizacion.graficar_calor_2d_bytes(matriz_final, tiempo_hist, temp_centro)
    html = reporte.generar_reporte_calor_html(
        difusividad, tiempo_total, temp_max, temp_min, temp_prom, png_bytes
    )
    
    # 4. INTEGRACIÓN CON SEAWEEDFS (Subimos imagen y reporte)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    url_reporte = storage.subir_reporte(html)
    
    datos_numericos = (
        f"--- Evolución del Núcleo ---\n"
        f"- t=0.0s: {temp_centro[0]:.2f} °C\n"
        f"- t={tiempo_hist[idx_mitad]:.3f}s: {temp_centro_mitad:.2f} °C\n"
        f"- t={tiempo_hist[-1]:.3f}s: {temp_centro[-1]:.2f} °C\n\n"
        f"--- Estado Global Final ---\n"
        f"- Máxima: {temp_max:.2f} °C | Mínima: {temp_min:.2f} °C | Promedio: {temp_prom:.2f} °C"
    )

    if url_imagen_nube and url_reporte:
        encabezado = (
            f"Simulación térmica completada.\n\n"
            f"![Mapa de Calor 2D]({url_imagen_nube})\n\n"
            f"[Abrir el reporte completo]({url_reporte})\n\n"
        )
    else:
        encabezado = "Simulación térmica completada. No se pudo publicar la imagen ni el reporte.\n\n"
    
    return encabezado + datos_numericos


@mcp.tool()
def simular_decaimiento(
    n0: float, lam: float, t_max: float
) -> str:
    """
    Simula el decaimiento radiactivo exponencial (dN/dt = -lam * N) y devuelve una imagen
    con la curva de desintegración, un enlace al reporte HTML completo y los datos cinéticos.

    :param n0: Cantidad inicial de partículas o masa (debe ser > 0).
    :param lam: Constante de decaimiento lambda en 1/s (debe ser > 0).
    :param t_max: Tiempo total de la simulación en segundos (debe ser > 0 y menor o igual a 100000).

    Muestra al usuario la imagen y el enlace del reporte tal como vienen en la respuesta.
    """
    # Filtro de validación estricto
    try:
        validacion.validar_parametros_decaimiento(n0, lam, t_max)
    except validacion.ValidationError as e:
        return f"Error de validación rechazado por el servidor: {str(e)}\nPor favor, corrige los parámetros y vuelve a intentar."

    # 1. Cálculos matemáticos locales
    tiempo, n = matematica.resolver_decaimiento_radiactivo(n0, lam, t_max)
    
    # 2. Extraer datos finales para el reporte
    n_final = n[-1]
    
    # 3. Generar gráficos y reporte HTML en MEMORIA
    png_bytes = visualizacion.graficar_decaimiento(tiempo, n)
    html = reporte.generar_reporte_decaimiento_html(
        n0, lam, t_max, n_final, png_bytes
    )

    # 4. INTEGRACIÓN CON SEAWEEDFS (Subimos imagen y reporte)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    url_reporte = storage.subir_reporte(html)
    
    vida_media = 0.693147 / lam
    porcentaje_perdido = ((n0 - n_final) / n0) * 100 if n0 > 0 else 0

    datos_numericos = (
        f"--- Datos Cinéticos ---\n"
        f"- Cantidad Inicial (N0): {n0:.2f}\n"
        f"- Constante Lambda: {lam:g}\n"
        f"- Vida Media (t½): {vida_media:.2f}\n"
        f"- Cantidad Restante Final (t={t_max}): {n_final:.4f} ({porcentaje_perdido:.2f}% desintegrado)\n"
    )

    if url_imagen_nube and url_reporte:
        encabezado = (
            f"Simulación de decaimiento radiactivo exitosa.\n\n"
            f"![Curva de Decaimiento]({url_imagen_nube})\n\n"
            f"[Abrir el reporte completo]({url_reporte})\n\n"
        )
    else:
        encabezado = "Simulación de decaimiento radiactivo exitosa. No se pudo publicar la imagen ni el reporte.\n\n"
    
    return encabezado + datos_numericos


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)