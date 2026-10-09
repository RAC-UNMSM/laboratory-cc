from mcp.server import MCPServer
import matematica
import storage
import visualizacion
import numpy as np

mcp = MCPServer("grupo07-calor_y_depredador_presa")

storage.ensure_bucket()

@mcp.tool()
def simular_lotka_volterra(
    alpha: float, beta: float, delta: float, gamma: float, 
    presas_inicial: float, depredadores_inicial: float, tiempo_max: float
) -> str:
    """
    Simula el modelo presa-depredador de Lotka-Volterra.
    Retorna información numérica enriquecida y la ruta de la imagen generada.
    """
    # 1. Llamar a matematica.py para los cálculos
    tiempo, presas, depredadores = matematica.resolver_lotka_volterra(
        alpha, beta, delta, gamma, presas_inicial, depredadores_inicial, tiempo_max
    )
    
    # 2. Llamar a visualizacion.py para generar los gráficos
    mensaje_imagen = visualizacion.graficar_lotka_volterra(tiempo, presas, depredadores)
    
    # 3. Cálculos analíticos adicionales usando NumPy para extraer los picos y valles
    idx_max_presas = np.argmax(presas)
    idx_min_presas = np.argmin(presas)
    
    idx_max_dep = np.argmax(depredadores)
    idx_min_dep = np.argmin(depredadores)
    
    # 4. Retornar los resultados detallados a Claude
    resumen = (
        f"{mensaje_imagen}\n\n"
        f"--- Datos analíticos de la simulación ---\n"
        f"Dinámica de Presas:\n"
        f"- Pico máximo: {presas[idx_max_presas]:.2f} (alcanzado en el mes {tiempo[idx_max_presas]:.2f})\n"
        f"- Valle mínimo: {presas[idx_min_presas]:.2f} (alcanzado en el mes {tiempo[idx_min_presas]:.2f})\n\n"
        f"Dinámica de Depredadores:\n"
        f"- Pico máximo: {depredadores[idx_max_dep]:.2f} (alcanzado en el mes {tiempo[idx_max_dep]:.2f})\n"
        f"- Valle mínimo: {depredadores[idx_min_dep]:.2f} (alcanzado en el mes {tiempo[idx_min_dep]:.2f})\n"
    )
    
    return resumen

@mcp.tool()
def simular_calor_2d(
    difusividad: float, tamaño_malla: int, tiempo_total: float, longitud: float
) -> str:
    """
    Simula la difusión térmica en una placa 2D usando diferencias finitas.
    longitud: El tamaño físico de un lado de la placa cuadrada (en metros).
    """
    # Pasamos el nuevo parámetro 'longitud' a matematica.py
    matriz_final, tiempo_hist, temp_centro = matematica.resolver_calor_2d(
        difusividad, tamaño_malla, tiempo_total, longitud
    )
    
    mensaje_imagen = visualizacion.graficar_calor_2d(matriz_final, tiempo_hist, temp_centro)
    
    idx_mitad = len(tiempo_hist) // 2
    
    resumen = (
        f"{mensaje_imagen}\n\n"
        f"--- Evolución Térmica del Núcleo (Centro) ---\n"
        f"- Temperatura Inicial (t=0.0s): {temp_centro[0]:.2f} °C\n"
        f"- Temperatura a la mitad del tiempo (t={tiempo_hist[idx_mitad]:.3f}s): {temp_centro[idx_mitad]:.2f} °C\n"
        f"- Temperatura Final (t={tiempo_hist[-1]:.3f}s): {temp_centro[-1]:.2f} °C\n\n"
        f"--- Estado Termodinámico General Final ---\n"
        f"- Temperatura máxima en la placa: {np.max(matriz_final):.2f} °C\n"
        f"- Temperatura mínima en la placa (bordes): {np.min(matriz_final):.2f} °C\n"
        f"- Temperatura promedio: {np.mean(matriz_final):.2f} °C"
    )
    
    return resumen