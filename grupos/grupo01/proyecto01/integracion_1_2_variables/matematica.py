import sympy as sp

x, y = sp.symbols('x y')

def integrar_simple(expr: sp.Expr, x_min: float, x_max: float):
    resultado = sp.integrate(expr, (x, x_min, x_max))
    latex_str = sp.latex(sp.Integral(expr, (x, x_min, x_max)))
    return resultado, latex_str

def integrar_doble_rectangular(expr: sp.Expr, x_min: float, x_max: float, y_min: float, y_max: float):
    resultado = sp.integrate(expr, (x, x_min, x_max), (y, y_min, y_max))
    latex_str = sp.latex(sp.Integral(expr, (x, x_min, x_max), (y, y_min, y_max)))
    return resultado, latex_str

def integrar_doble_general(expr: sp.Expr, var_int_str: str, g1_str: str, g2_str: str, var_ext_str: str, ext_min: float, ext_max: float):
    v_int = sp.symbols(var_int_str)
    v_ext = sp.symbols(var_ext_str)
    
    g1 = sp.sympify(g1_str)
    g2 = sp.sympify(g2_str)
    
    resultado = sp.integrate(expr, (v_int, g1, g2), (v_ext, ext_min, ext_max))
    latex_str = sp.latex(sp.Integral(expr, (v_int, g1, g2), (v_ext, ext_min, ext_max)))
    return resultado, latex_str
