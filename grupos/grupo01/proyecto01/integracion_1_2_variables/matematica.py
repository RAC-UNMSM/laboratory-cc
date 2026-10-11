import sympy as sp
import concurrent.futures

TIMEOUT_INTEGRATION = 10  # Tiempo máximo en segundos

def _ejecutar_con_timeout(func, args, timeout_segundos=TIMEOUT_INTEGRATION):
    """Ejecuta una función de integración simbólica dentro de un hilo con límite de tiempo."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        try:
            return future.result(timeout=timeout_segundos)
        except concurrent.futures.TimeoutError:
            raise TimeoutError("El cálculo simbólico excedió el tiempo límite (integral demasiado compleja o sin forma cerrada).")

def _integrar_simple_sym(expr: sp.Expr, x_min: float, x_max: float):
    x = sp.Symbol('x')
    res = sp.integrate(expr, (x, x_min, x_max))
    latex_str = rf"\int_{{{sp.latex(x_min)}}}^{{{sp.latex(x_max)}}} {sp.latex(expr)} \, dx"
    return res, latex_str

def integrar_simple(expr: sp.Expr, x_min: float, x_max: float):
    return _ejecutar_con_timeout(_integrar_simple_sym, (expr, x_min, x_max))

def _integrar_doble_rec_sym(expr: sp.Expr, x_min: float, x_max: float, y_min: float, y_max: float):
    x, y = sp.symbols('x y')
    res = sp.integrate(expr, (y, y_min, y_max), (x, x_min, x_max))
    latex_str = (
        rf"\int_{{{sp.latex(x_min)}}}^{{{sp.latex(x_max)}}} "
        rf"\int_{{{sp.latex(y_min)}}}^{{{sp.latex(y_max)}}} "
        rf"{sp.latex(expr)} \, dy \, dx"
    )
    return res, latex_str

def integrar_doble_rectangular(expr: sp.Expr, x_min: float, x_max: float, y_min: float, y_max: float):
    return _ejecutar_con_timeout(_integrar_doble_rec_sym, (expr, x_min, x_max, y_min, y_max))

def _integrar_doble_gen_sym(
    expr: sp.Expr, var_int_str: str, g1_str: str, g2_str: str,
    var_ext_str: str, ext_min: float, ext_max: float
):
    v_int = sp.Symbol(var_int_str)
    v_ext = sp.Symbol(var_ext_str)
    g1_sp = sp.sympify(g1_str)
    g2_sp = sp.sympify(g2_str)

    res = sp.integrate(expr, (v_int, g1_sp, g2_sp), (v_ext, ext_min, ext_max))
    latex_str = (
        rf"\int_{{{sp.latex(ext_min)}}}^{{{sp.latex(ext_max)}}} "
        rf"\int_{{{sp.latex(g1_sp)}}}^{{{sp.latex(g2_sp)}}} "
        rf"{sp.latex(expr)} \, d{var_int_str} \, d{var_ext_str}"
    )
    return res, latex_str

def integrar_doble_general(
    expr: sp.Expr, var_int_str: str, g1_str: str, g2_str: str,
    var_ext_str: str, ext_min: float, ext_max: float
):
    return _ejecutar_con_timeout(
        _integrar_doble_gen_sym,
        (expr, var_int_str, g1_str, g2_str, var_ext_str, ext_min, ext_max)
    )
