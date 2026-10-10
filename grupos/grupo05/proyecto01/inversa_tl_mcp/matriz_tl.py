import sympy as sp


def crear_variables(n: int):
    """
    Crea las variables x1, x2, ..., xn.
    """
    return sp.symbols(f"x1:{n + 1}")


def construir_matriz_estandar(componentes, variables):
    """
    Construye la matriz estándar de una transformación lineal
    T: R^n -> R^n a partir de sus componentes.

    Las columnas de la matriz son:
    T(e1), T(e2), ..., T(en).
    """
    n = len(variables)

    columnas = []

    for i in range(n):
        sustitucion = {
            variables[j]: 1 if i == j else 0
            for j in range(n)
        }

        imagen_ei = sp.Matrix([
            sp.simplify(expr.subs(sustitucion))
            for expr in componentes
        ])

        columnas.append(imagen_ei)

    matriz = sp.Matrix.hstack(*columnas)

    return matriz


def analizar_invertibilidad(matriz):
    """
    Calcula el determinante de la matriz estándar y determina
    si la transformación lineal es invertible.
    """
    determinante = sp.simplify(matriz.det())

    return {
        "determinante": determinante,
        "invertible": determinante != 0
    }