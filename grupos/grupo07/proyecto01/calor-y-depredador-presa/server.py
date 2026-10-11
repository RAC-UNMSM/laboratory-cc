from mcp.server import MCPServer
import time
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
    Simula el modelo presa-depredador de Lotka-Volterra.
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
    
    # 3. Generar gráficos en MEMORIA (sin archivo PNG en disco)
    png_bytes = visualizacion.graficar_lotka_volterra_bytes(tiempo, presas, depredadores)
    
    # 4. Generar reporte HTML (único archivo físico con timestamp)
    timestamp = int(time.time())
    nombre_html_unico = f"reporte_lotka_{timestamp}.html"
    
    ruta_html_local = reporte.generar_reporte_lotka_volterra_html(
        presas_max, mes_presas_max, presas_min, mes_presas_min,
        dep_max, mes_dep_max, dep_min, mes_dep_min,
        png_bytes, nombre_html_unico
    )

    # 5. INTEGRACIÓN CON SEAWEEDFS (Subimos la imagen para el chat)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    
    # Armamos la respuesta para Claude
    if url_imagen_nube:
        resumen = (
            f"Simulación exitosa.\n\n"
            f"![Gráfico de Resultados]({url_imagen_nube})\n\n"
            f"El reporte HTML interactivo se guardó localmente en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
            f"--- Datos Numéricos ---\n"
            f"- Presas: Pico {presas_max:.2f} (mes {mes_presas_max:.2f}), VALLE {presas_min:.2f} (mes {mes_presas_min:.2f})\n"
            f"- Depredadores: Pico {dep_max:.2f} (mes {mes_dep_max:.2f}), VALLE {dep_min:.2f} (mes {mes_dep_min:.2f})\n"
        )
    else:
        # Fallback si falla la subida o estás trabajando sin conexión
        resumen = (
            f"Simulación exitosa (guardado estrictamente local).\n\n"
            f"El reporte HTML interactivo con las gráficas se guardó en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
            f"--- Datos Numéricos ---\n"
            f"- Presas: Pico {presas_max:.2f} (mes {mes_presas_max:.2f}), VALLE {presas_min:.2f} (mes {mes_presas_min:.2f})\n"
            f"- Depredadores: Pico {dep_max:.2f} (mes {mes_dep_max:.2f}), VALLE {dep_min:.2f} (mes {mes_dep_min:.2f})\n"
        )
    
    return resumen



@mcp.tool()
def simular_calor_2d(
    difusividad: float, tamaño_malla: int, tiempo_total: float, 
    longitud_placa: float, radio_fuente: float
) -> str:
    """
    Simula la difusión térmica (Ecuación del Calor) 
    """

    # NUEVO: Filtro de validación termodinámica
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
    
    # 3. Generar gráficos en MEMORIA (sin archivo PNG en disco)
    png_bytes = visualizacion.graficar_calor_2d_bytes(matriz_final, tiempo_hist, temp_centro)
    
    # 4. Generar reporte HTML (único archivo físico)
    timestamp = int(time.time())
    nombre_html_unico = f"reporte_calor_{timestamp}.html"
    ruta_html_local = reporte.generar_reporte_calor_html(
        difusividad, tiempo_total, temp_max, temp_min, temp_prom, png_bytes, nombre_html_unico
    )
    
# 5. INTEGRACIÓN CON SEAWEEDFS (Subimos la imagen para el chat)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    
    # Armamos la respuesta para Claude
    if url_imagen_nube:
        resumen = (
            f"Simulación térmica completada.\n\n"
            f"![Mapa de Calor 2D]({url_imagen_nube})\n\n"
            f"El reporte HTML interactivo se guardó localmente en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
            f"--- Evolución del Núcleo ---\n"
            f"- t=0.0s: {temp_centro[0]:.2f} °C\n"
            f"- t={tiempo_hist[idx_mitad]:.3f}s: {temp_centro_mitad:.2f} °C\n"
            f"- t={tiempo_hist[-1]:.3f}s: {temp_centro[-1]:.2f} °C\n\n"
            f"--- Estado Global Final ---\n"
            f"- Máxima: {temp_max:.2f} °C | Mínima: {temp_min:.2f} °C | Promedio: {temp_prom:.2f} °C"
        )
    else:
        # Fallback si falla la subida o estás trabajando sin conexión
        resumen = (
            f"Simulación térmica completada (guardado estrictamente local).\n\n"
            f"El reporte HTML interactivo con las gráficas se guardó en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
            f"--- Evolución del Núcleo ---\n"
            f"- t=0.0s: {temp_centro[0]:.2f} °C\n"
            f"- t={tiempo_hist[idx_mitad]:.3f}s: {temp_centro_mitad:.2f} °C\n"
            f"- t={tiempo_hist[-1]:.3f}s: {temp_centro[-1]:.2f} °C\n\n"
            f"--- Estado Global Final ---\n"
            f"- Máxima: {temp_max:.2f} °C | Mínima: {temp_min:.2f} °C | Promedio: {temp_prom:.2f} °C"
        )
    
    return resumen


@mcp.tool()
def simular_decaimiento(
    n0: float, lam: float, t_max: float
) -> str:
    """
    Simula el decaimiento radiactivo y genera un grafico y reporte.
    :param n0: Cantidad inicial de particulas o masa
    :param lam: Constante de decaimiento lambda
    :param t_max: Tiempo total de la simulacion
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
    
    # 3. Generar gráficos en MEMORIA (sin archivo PNG en disco)
    png_bytes = visualizacion.graficar_decaimiento(tiempo, n)
    
    # 4. Generar reporte HTML (único archivo físico con timestamp)
    timestamp = int(time.time())
    nombre_html_unico = f"reporte_decaimiento_{timestamp}.html"
    
    ruta_html_local = reporte.generar_reporte_decaimiento_html(
        n0, lam, t_max, n_final, png_bytes, nombre_html_unico
    )

    # 5. INTEGRACIÓN CON SEAWEEDFS (Subimos la imagen para el chat)
    url_imagen_nube = storage.subir_imagen(png_bytes)
    
    # Armamos la respuesta para Claude
    if url_imagen_nube:
        resumen = (
            f"Simulación de decaimiento radiactivo exitosa.\n\n"
            f"![Curva de Decaimiento]({url_imagen_nube})\n\n"
            f"El reporte HTML interactivo se guardó localmente en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
            f"--- Datos Cinéticos ---\n"
            f"- Cantidad Inicial (N0): {n0:.2f}\n"
            f"- Constante Lambda: {lam:.4f}\n"
            f"- Cantidad Restante Final (t={t_max}): {n_final:.4f}\n"
        )
    else:
        # Fallback si falla la subida o estás trabajando sin conexión
        resumen = (
            f"Simulación exitosa (guardado estrictamente local).\n\n"
            f"El reporte HTML interactivo con las gráficas se guardó en:\n"
            f"file:///{ruta_html_local.replace(chr(92), '/')}\n\n"
             f"--- Datos Cinéticos ---\n"
            f"- Cantidad Inicial (N0): {n0:.2f}\n"
            f"- Constante Lambda: {lam:.4f}\n"
            f"- Cantidad Restante Final (t={t_max}): {n_final:.4f}\n"
        )
    
    return resumen


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)