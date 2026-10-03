import io
import os
import platform
import subprocess
import tempfile
import numpy as np
import sympy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def abrir_imagen_sistema(filepath: str):
    """Abre el archivo de imagen según el sistema operativo del usuario."""
    sistema = platform.system().lower()
    try:
        if sistema == "darwin":      # macOS
            subprocess.run(["open", filepath], check=False)
        elif sistema == "windows":  # Windows
            os.startfile(filepath)
        elif sistema == "linux":    # Linux
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception:
        pass  # Si no hay entorno gráfico disponible, ignora la apertura.

def generar_grafico_png(
    expr: sp.Expr,
    x_min: float,
    x_max: float,
    y_min: float = None,
    y_max: float = None,
    g1_str: str = None,
    g2_str: str = None,
    mostrar_local: bool = True
) -> bytes:
    """
    Genera un gráfico PNG de la función dada.
    - Si es de 1 variable, genera un gráfico 2D con el área sombreada.
    - Si es de 2 variables, genera una superficie 3D recortada con proyección en el suelo.
    """
    es_1d = (y_min is None and g1_str is None)
    fig = plt.figure(figsize=(8, 6), dpi=120)

    if es_1d:
        ax = fig.add_subplot(111)
        x_vals = np.linspace(x_min, x_max, 400)
        f_lamb = sp.lambdify(sp.Symbol('x'), expr, modules=['numpy'])
        try:
            y_vals = f_lamb(x_vals)
            if np.isscalar(y_vals):
                y_vals = np.full_like(x_vals, y_vals)
        except Exception:
            y_vals = np.zeros_like(x_vals)

        ax.plot(x_vals, y_vals, label=f"$f(x) = {sp.latex(expr)}$", color='#1f77b4', lw=2)
        ax.fill_between(x_vals, y_vals, alpha=0.3, color='#1f77b4')
        ax.axhline(0, color='black', lw=0.8, ls='--')
        ax.axvline(0, color='black', lw=0.8, ls='--')
        ax.set_title("Área Bajo la Curva (Integral Simple)", fontsize=12, fontweight='bold')
        ax.set_xlabel("x")
        ax.set_ylabel("f(x)")
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend()

    else:
        ax = fig.add_subplot(111, projection='3d')
        x_vals = np.linspace(x_min, x_max, 150)

        # Determinar límites en Y
        if g1_str is not None and g2_str is not None:
            x_sym = sp.Symbol('x')
            g1_lamb = sp.lambdify(x_sym, sp.sympify(g1_str), modules=['numpy'])
            g2_lamb = sp.lambdify(x_sym, sp.sympify(g2_str), modules=['numpy'])

            g1_eval = g1_lamb(x_vals)
            g2_eval = g2_lamb(x_vals)
            if np.isscalar(g1_eval): g1_eval = np.full_like(x_vals, g1_eval)
            if np.isscalar(g2_eval): g2_eval = np.full_like(x_vals, g2_eval)

            y_m = float(np.nanmin(g1_eval)) if y_min is None else y_min
            y_M = float(np.nanmax(g2_eval)) if y_max is None else y_max
        else:
            y_m = y_min if y_min is not None else -1.0
            y_M = y_max if y_max is not None else 1.0

        y_vals = np.linspace(y_m, y_M, 150)
        X, Y = np.meshgrid(x_vals, y_vals)

        f_lamb = sp.lambdify((sp.Symbol('x'), sp.Symbol('y')), expr, modules=['numpy'])
        try:
            Z = f_lamb(X, Y)
            if np.isscalar(Z):
                Z = np.full_like(X, Z)
        except Exception:
            Z = np.zeros_like(X)

        # Máscara para dominios no rectangulares g1(x) <= y <= g2(x)
        if g1_str is not None and g2_str is not None:
            x_sym = sp.Symbol('x')
            g1_l = sp.lambdify(x_sym, sp.sympify(g1_str), modules=['numpy'])
            g2_l = sp.lambdify(x_sym, sp.sympify(g2_str), modules=['numpy'])
            G1 = g1_l(X)
            G2 = g2_l(X)
            mask = (Y >= G1) & (Y <= G2)
            Z = np.where(mask, Z, np.nan)

        surf = ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.85, edgecolor='k', linewidth=0.1)

        # Sombra proyectada del dominio en el suelo z_min
        z_min_val = np.nanmin(Z) if not np.all(np.isnan(Z)) else 0
        if not np.isnan(z_min_val):
            ax.contourf(X, Y, Z, zdir='z', offset=z_min_val, cmap='viridis', alpha=0.3)
            ax.set_zlim(z_min_val, np.nanmax(Z) if not np.all(np.isnan(Z)) else z_min_val + 1)

        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label='f(x, y)')
        ax.set_title("Volumen Bajo la Superficie (Integral Doble)", fontsize=12, fontweight='bold')
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_zlabel("f(x, y)")

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=120)
    buf.seek(0)
    png_bytes = buf.getvalue()

    if mostrar_local:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name
        abrir_imagen_sistema(tmp_path)

    plt.close(fig)
    return png_bytes
