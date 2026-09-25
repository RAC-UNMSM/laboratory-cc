import io
import numpy as np
import matplotlib.pyplot as plt
import sympy as sp

x, y = sp.symbols('x y')

def generar_grafico_png(expr: sp.Expr, x_min: float, x_max: float, y_min: float = None, y_max: float = None) -> bytes:
    fig = plt.figure(figsize=(7, 5))
    
    es_doble = (y in expr.free_symbols) or (y_min is not None and y_max is not None)
    
    if not es_doble:
        # Interpretación 2D: Área bajo la curva
        f_num = sp.lambdify(x, expr, 'numpy')
        x_vals = np.linspace(x_min, x_max, 300)
        y_vals = f_num(x_vals)
        if np.isscalar(y_vals):
            y_vals = np.full_like(x_vals, y_vals)
            
        ax = fig.add_subplot(111)
        ax.plot(x_vals, y_vals, 'b-', label=f"$f(x) = {sp.latex(expr)}$")
        ax.fill_between(x_vals, 0, y_vals, color='skyblue', alpha=0.5, label='Área de integración')
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
        ax.set_title("Área bajo la gráfica")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.grid(True)
        ax.legend()
    else:
        # Interpretación 3D: Volumen bajo la superficie
        y_min_val = y_min if y_min is not None else -5.0
        y_max_val = y_max if y_max is not None else 5.0
        
        f_num = sp.lambdify((x, y), expr, 'numpy')
        x_vals = np.linspace(x_min, x_max, 50)
        y_vals = np.linspace(y_min_val, y_max_val, 50)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = f_num(X, Y)
        if np.isscalar(Z):
            Z = np.full_like(X, Z)
            
        ax = fig.add_subplot(111, projection='3d')
        surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.85)
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        ax.set_title("Volumen bajo la superficie")
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("z")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()
