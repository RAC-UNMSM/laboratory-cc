import os
import matplotlib
# CRÍTICO: Forzamos a Matplotlib a usar el motor "Agg" (Anti-Grain Geometry).
# Este motor no requiere pantalla ni ventanas emergentes, ideal para servidores.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

def graficar_lotka_volterra(tiempo, presas, depredadores):
    """
    Genera gráficos de series de tiempo y plano de fase.
    Guarda la imagen localmente y retorna un mensaje con la ruta.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # 1. Gráfico de series de tiempo (Población vs Tiempo)
    ax1.plot(tiempo, presas, 'b-', label='Presas', linewidth=2)
    ax1.plot(tiempo, depredadores, 'r-', label='Depredadores', linewidth=2)
    ax1.set_title('Evolución de las Poblaciones')
    ax1.set_xlabel('Tiempo')
    ax1.set_ylabel('Población')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()
    
    # 2. Gráfico del plano de fase (Depredadores vs Presas)
    ax2.plot(presas, depredadores, 'g-', linewidth=2)
    ax2.set_title('Plano de Fase (Órbitas)')
    ax2.set_xlabel('Población de Presas')
    ax2.set_ylabel('Población de Depredadores')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Forzamos que la ruta de guardado sea EXACTAMENTE la misma carpeta 
    # donde reside este archivo visualizacion.py
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_absoluta = os.path.join(directorio_actual, "lotka_volterra_resultado.png")
    
    plt.savefig(ruta_absoluta, dpi=300, bbox_inches='tight')
    plt.close(fig) # Limpiamos la figura explícitamente para liberar memoria
    
    return f"Gráficos generados exitosamente. Imagen guardada en: {ruta_absoluta}"

def graficar_calor_2d(matriz_temperaturas, tiempo_hist, temp_centro_hist):
    """
    Genera un heatmap estático y una gráfica de la evolución del centro.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Mapa de calor (Heatmap)
    cax = ax1.imshow(matriz_temperaturas, cmap='inferno', origin='lower', interpolation='bilinear')
    ax1.set_title('Distribución Final de Temperatura 2D')
    ax1.set_xlabel('Posición X')
    ax1.set_ylabel('Posición Y')
    fig.colorbar(cax, ax=ax1, fraction=0.046, pad=0.04).set_label('Temperatura (°C)')
    
    # 2. Curva de enfriamiento (Temperatura vs Tiempo)
    ax2.plot(tiempo_hist, temp_centro_hist, 'r-', linewidth=2)
    ax2.set_title('Evolución Térmica del Núcleo (Disipación)')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Temperatura del Centro (°C)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_absoluta = os.path.join(directorio_actual, "calor_2d_resultado.png")
    
    plt.savefig(ruta_absoluta, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    return f"Gráficos generados exitosamente. Imagen guardada en: {ruta_absoluta}"