import io
import os
import tempfile
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Habilita proyección 3D
import numpy as np
import sympy as sp

def generar_grafico_png(
    expr_sp, 
    x_min: float, 
    x_max: float, 
    y_min: float = None, 
    y_max: float = None,
    g1_str: str = None,
    g2_str: str = None
) -> bytes:
    """
    Genera gráficos 2D para 1 variable o gráficos 3D (superficie/volumen) 
    para integrales dobles sobre dominios rectangulares o generales.
    """
    x, y = sp.symbols('x y')
    simbolos = expr_sp.free_symbols
    es_2d = (y in simbolos) or (y_min is not None) or (g1_str is not None)

    # -------------------------------------------------------------
    # CASO INTEGRALES DOBLES: Superficie 3D z = f(x, y)
    # -------------------------------------------------------------
    if es_2d:
        fig = plt.figure(figsize=(7, 5.5), dpi=100)
        ax = fig.add_subplot(111, projection='3d')
        
        # Malla en X
        margin_x = (x_max - x_min) * 0.15 if x_max != x_min else 1.0
        x_plot = np.linspace(x_min - margin_x, x_max + margin_x, 120)
        
        # Determinar rango y funciones para Y
        if g1_str and g2_str:
            g1_sym = sp.sympify(g1_str)
            g2_sym = sp.sympify(g2_str)
            g1_func = sp.lambdify(x, g1_sym, modules=['numpy', 'math'])
            g2_func = sp.lambdify(x, g2_sym, modules=['numpy', 'math'])
            
            g1_vals = g1_func(x_plot)
            g2_vals = g2_func(x_plot)
            if np.isscalar(g1_vals): g1_vals = np.full_like(x_plot, g1_vals)
            if np.isscalar(g2_vals): g2_vals = np.full_like(x_plot, g2_vals)
            
            y_min_val = float(np.nanmin(g1_vals))
            y_max_val = float(np.nanmax(g2_vals))
        else:
            y_min_val = y_min if y_min is not None else -2.0
            y_max_val = y_max if y_max is not None else 2.0
            
        margin_y = (y_max_val - y_min_val) * 0.15 if y_max_val != y_min_val else 1.0
        y_plot = np.linspace(y_min_val - margin_y, y_max_val + margin_y, 120)
        
        X, Y = np.meshgrid(x_plot, y_plot)
        f_num = sp.lambdify((x, y), expr_sp, modules=['numpy', 'math'])
        
        try:
            Z = f_num(X, Y)
            if np.isscalar(Z):
                Z = np.full_like(X, Z)
        except Exception:
            Z = np.zeros_like(X)

        # Máscara para dominios generales (ej. círculos): descarta puntos fuera de [g1(x), g2(x)]
        if g1_str and g2_str:
            G1 = g1_func(X)
            G2 = g2_func(X)
            mask = (Y >= G1) & (Y <= G2) & (X >= x_min) & (X <= x_max)
            Z[~mask] = np.nan

        # Dibujar superficie 3D
        surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.85, edgecolor='k', linewidth=0.1)
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, pad=0.1, label=f"$z = {sp.latex(expr_sp)}$")
        
        ax.set_title(f"Volumen: $z = {sp.latex(expr_sp)}$", fontsize=11, fontweight='bold')
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")

    # -------------------------------------------------------------
    # CASO INTEGRALES SIMPLES: Curva y Área 2D
    # -------------------------------------------------------------
    else:
        fig, ax = plt.subplots(figsize=(6, 4.5), dpi=100)
        margin_x = (x_max - x_min) * 0.2 if x_max != x_min else 1.0
        x_plot = np.linspace(x_min - margin_x, x_max + margin_x, 200)
        
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
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.axvline(0, color='black', linewidth=0.8, linestyle='--')
        ax.grid(True, linestyle=':', alpha=0.6)

    # Exportación y apertura local
    temp_dir = tempfile.gettempdir()
    filepath = os.path.join(temp_dir, "grafico_integral.png")
    plt.savefig(filepath, format='png', bbox_inches='tight')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    try:
        subprocess.run(["open", filepath])
    except Exception:
        pass
        
    return buf.getvalue()
