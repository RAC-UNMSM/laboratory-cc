import os
import io
import matplotlib
# CRÍTICO: Forzamos a Matplotlib a usar el motor "Agg" (Anti-Grain Geometry).
# Este motor no requiere pantalla ni ventanas emergentes, ideal para servidores.
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

def graficar_lotka_volterra_bytes(tiempo, presas, depredadores) -> bytes:
    """
    Genera los gráficos de Lotka-Volterra y retorna los bytes en memoria.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=120)
    
    # Gráfico de series temporales
    ax1.plot(tiempo, presas, 'b-', label='Presas', linewidth=2)
    ax1.plot(tiempo, depredadores, 'r-', label='Depredadores', linewidth=2)
    ax1.set_title('Dinámica de Poblaciones en el Tiempo')
    ax1.set_xlabel('Tiempo (meses)')
    ax1.set_ylabel('Población')
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend()
    
    # Retrato de fase
    ax2.plot(presas, depredadores, 'g-', linewidth=1.5)
    ax2.set_title('Plano de Fase (Depredador vs Presa)')
    ax2.set_xlabel('Presas')
    ax2.set_ylabel('Depredadores')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Guardar en buffer de memoria
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    png_bytes = buf.getvalue()
    
    plt.close(fig)
    return png_bytes



def graficar_calor_2d_bytes(matriz_temperaturas, tiempo_hist, temp_centro_hist) -> bytes:
    """
    Genera el heatmap y la curva térmica, y retorna la imagen cruda en bytes en memoria.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), dpi=120)
    
    # Mapa de calor
    cax = ax1.imshow(matriz_temperaturas, cmap='inferno', origin='lower', interpolation='bilinear')
    ax1.set_title('Distribución Final de Temperatura 2D')
    ax1.set_xlabel('Posición X')
    ax1.set_ylabel('Posición Y')
    fig.colorbar(cax, ax=ax1, fraction=0.046, pad=0.04).set_label('Temperatura (°C)')
    
    # Curva de enfriamiento
    ax2.plot(tiempo_hist, temp_centro_hist, 'r-', linewidth=2)
    ax2.set_title('Evolución Térmica del Núcleo')
    ax2.set_xlabel('Tiempo (s)')
    ax2.set_ylabel('Temperatura del Centro (°C)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    
    # Guardar en buffer de memoria
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    png_bytes = buf.getvalue()
    
    plt.close(fig)
    return png_bytes


def graficar_decaimiento(t, n) -> io.BytesIO:
    """
    Genera la gráfica del decaimiento radiactivo y la devuelve como un buffer de memoria (PNG).
    
    Parámetros:
        t: Array de NumPy con los puntos temporales.
        n: Array de NumPy con la cantidad de sustancia en cada instante.
    """
    # 1. Crear la figura y los ejes
    fig, ax = plt.subplots(figsize=(8, 5))
    
    # 2. Trazar la curva exponencial
    ax.plot(t, n, color='#d62728', linewidth=2.5, label='Cantidad restante ($N$)')
    
    # 3. Formatear la gráfica para que sea presentable en el reporte HTML
    ax.set_title('Curva de Decaimiento Radiactivo', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Tiempo ($t$)', fontsize=12)
    ax.set_ylabel('Cantidad de Sustancia', fontsize=12)
    
    # Sombreado bajo la curva para mejorar la visualización (opcional pero estético)
    ax.fill_between(t, n, color='#d62728', alpha=0.1)
    
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper right')
    
    # Ajustar márgenes automáticamente
    fig.tight_layout()
    
# 4. Guardar la imagen en memoria RAM
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=150)
    
    # Extraer los bytes exactos de la imagen
    png_bytes = buffer.getvalue()
    
    # 5. Liberar la memoria RAM
    buffer.close()
    plt.close(fig)
    
    return png_bytes