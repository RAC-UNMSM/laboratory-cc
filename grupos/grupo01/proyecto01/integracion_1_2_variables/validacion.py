import sympy as sp

x, y = sp.symbols('x y')

def validar_y_parsear_expresion(expresion_str: str) -> sp.Expr:
    """
    Convierte el texto de la expresión en un objeto SymPy y verifica que
    solo se utilicen las variables permitidas 'x' e 'y'.
    """
    try:
        expr = sp.sympify(expresion_str)
    except Exception as e:
        raise ValueError(f"Error al analizar la expresión '{expresion_str}': {e}")
    
    simbolos_presentes = expr.free_symbols
    simbolos_permitidos = {x, y}
    no_permitidos = simbolos_presentes - simbolos_permitidos
    
    if no_permitidos:
        raise ValueError(f"Variables no permitidas en la expresión: {no_permitidos}. Solo se admiten 'x' e 'y'.")
    
    return expr

def validar_limites_numericos(lim_min: float, lim_max: float, nombre_var: str = "x"):
    """
    Verifica que los límites sean numéricos y que lim_min < lim_max.
    """
    if not (isinstance(lim_min, (int, float)) and isinstance(lim_max, (int, float))):
        raise ValueError(f"Los límites para {nombre_var} deben ser valores numéricos.")
    if lim_min >= lim_max:
        raise ValueError(f"El límite inferior ({lim_min}) debe ser menor que el límite superior ({lim_max}) para {nombre_var}.")
