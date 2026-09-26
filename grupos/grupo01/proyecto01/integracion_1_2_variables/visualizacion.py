import io
import os
import tempfile
import subprocess
import matplotlib
matplotlib.use('Agg')  # Backend sin interfaz gráfica
import matplotlib.pyplot as plt
import numpy as np
import sympy as sp

def generar_grafico_png(expr_sp, x_min: float, x_max: float, y_min: float = None, y_max: float = None) -> bytes:
    """Genera un gráfico PNG, lo abre automáticamente en macOS y devuelve sus bytes."""
    fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
    
    x = sp.Symbol('x')
    f_num = sp.lambdify(x, expr_sp, modules=['numpy', 'math'])
    
    margin = (x_max - x_min) * 0.2 if x_max != x_min else 1.0
    x_plot = np.linspace(x_min - margin, x_max + margin, 300)
    
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
    
    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.axvline(0, color='black', linewidth=0.8, linestyle='--')
    ax.set_title("Área bajo la curva", fontsize=11, fontweight='bold')
    ax.set_xlabel("x")
    ax.set_ylabel("f(x)")
    ax.legend(loc='upper right')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    # 1. Guardar en un archivo temporal local
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, "grafico_integral.png")
    plt.savefig(filepath, format='png', bbox_inches='tight')
    
    # 2. Guardar en memoria para devolver a Claude MCP
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    # 3. Abrir automáticamente la imagen en macOS
    try:
        subprocess.run(["open", filepath])
    except Exception:
        pass
    
    return buf.getvalue()
