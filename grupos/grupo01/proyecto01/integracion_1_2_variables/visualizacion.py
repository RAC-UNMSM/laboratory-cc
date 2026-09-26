import io
import os
import tempfile
import subprocess
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

def generar_grafico_png(expr_sp, x_min: float, x_max: float, y_min: float = None, y_max: float = None) -> bytes:
    """
    Genera un gráfico PNG adaptativo (1D o 2D) según las variables presentes en la expresión.
    Guarda la imagen, la abre en macOS y devuelve sus bytes.
    """
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=100)
    x, y = sp.symbols('x y')
    simbolos_presentes = expr_sp.free_symbols
    
    # Configuración de rango en X
    margin_x = (x_max - x_min) * 0.2 if x_max != x_min else 1.0
    x_plot = np.linspace(x_min - margin_x, x_max + margin_x, 200)
    
    # -------------------------------------------------------------
    # CASO A: FUNCIÓN DE 2 VARIABLES f(x, y) -> Mapa de contornos 2D
    # -------------------------------------------------------------
    if y in simbolos_presentes or y_min is not None:
        y_min_val = y_min if y_min is not None else -abs(x_max if x_max != 0 else 1)
        y_max_val = y_max if y_max is not None else abs(x_max if x_max != 0 else 1)
        margin_y = (y_max_val - y_min_val) * 0.2 if y_max_val != y_min_val else 1.0
        y_plot = np.linspace(y_min_val - margin_y, y_max_val + margin_y, 200)
        
        X, Y = np.meshgrid(x_plot, y_plot)
        f_num = sp.lambdify((x, y), expr_sp, modules=['numpy', 'math'])
        
        try:
            Z = f_num(X, Y)
            if np.isscalar(Z):
                Z = np.full_like(X, Z)
        except Exception:
            Z = np.zeros_like(X)
            
        cp = ax.contourf(X, Y, Z, levels=25, cmap='viridis')
        fig.colorbar(cp, ax=ax, label=f"$f(x,y) = {sp.latex(expr_sp)}$")
        
        ax.set_title("Superficie / Campo $f(x, y)$", fontsize=11, fontweight='bold')
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        
    # -------------------------------------------------------------
    # CASO B: FUNCIÓN DE 1 VARIABLE f(x) -> Curva y Área en 2D
    # -------------------------------------------------------------
    else:
        f_num = sp.lambdify(x, expr_sp, modules=['numpy', 'math'])
        try:
            y_plot = f_num(x_plot)
            if np.isscalar(y_plot):
                y_plot = np.full_like(x_plot, y_plot)
        except Exception:
            y_plot = np.zeros_like(x_plot)

        ax.plot(x_plot, y_plot, label=f"$f(x) = {sp.latex(expr_sp)}$", color='#1f77b4', linewidth=2)
        
        x_fill = np.linspace(x_min, x_max, 150)
        try:
            y_fill = f_num(x_fill)
            if np.isscalar(y_fill):
                y_fill = np.full_like(x_fill, y_fill)
        except Exception:
            y_fill = np.zeros_like(x_fill)
            
        ax.fill_between(x_fill, 0, y_fill, color='#1f77b4', alpha=0.3, label='Área de integración')
        ax.set_title("Área bajo la curva", fontsize=11, fontweight='bold')
        ax.set_xlabel("x")
        ax.set_ylabel("f(x)")
        ax.legend(loc='upper right')

    # Elementos comunes
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.axvline(0, color='black', linewidth=0.8, linestyle='--')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # 1. Guardar localmente para abrir con 'open' en macOS
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, "grafico_integral.png")
    plt.savefig(filepath, format='png', bbox_inches='tight')
    
    # 2. Guardar en memoria para FastMCP
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    try:
        subprocess.run(["open", filepath])
    except Exception:
        pass
        
    return buf.getvalue()
