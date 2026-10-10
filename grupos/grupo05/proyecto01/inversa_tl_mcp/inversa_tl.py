import sympy as sp


def construir_regla_inversa(matriz_inversa, variables):
    """
    Construye la regla de correspondencia de T^(-1)
    a partir de la matriz inversa A^(-1).

    Calcula:

        A^(-1) * [x1, x2, ..., xn]^T

    Devuelve el vector de entrada y el vector que representa T^(-1).
    """

    A_inversa = sp.Matrix(matriz_inversa)
    vector_x = sp.Matrix(variables)

    if A_inversa.rows != A_inversa.cols:
        raise ValueError("La matriz inversa debe ser cuadrada.")

    if A_inversa.cols != len(variables):
        raise ValueError(
            "La dimensión de la matriz no coincide con "
            "el número de variables."
        )

    regla_inversa = A_inversa * vector_x

    regla_inversa = sp.Matrix([
        sp.simplify(expr)
        for expr in regla_inversa
    ])

    return {
        "vector_x": vector_x,
        "regla_inversa": regla_inversa
    }


def verificar_inversa(componentes, regla_inversa, variables):
    """
    Verifica que T^(-1) sea realmente la inversa de T.

    Comprueba:

        T(T^(-1)(x)) = x

    y

        T^(-1)(T(x)) = x

    Devuelve ambas composiciones y el resultado de las verificaciones.
    """

    vector_x = sp.Matrix(variables)
    T_x = sp.Matrix(componentes)
    T_inversa_x = sp.Matrix(regla_inversa)

    n = len(variables)

    if len(componentes) != n:
        raise ValueError(
            "La transformación debe tener el mismo número "
            "de componentes que variables."
        )

    if len(regla_inversa) != n:
        raise ValueError(
            "La transformación inversa debe tener "
            "el mismo número de componentes que variables."
        )

    # ----------------------------------------------------------
    # 1. Calcular T(T^(-1)(x))
    # ----------------------------------------------------------

    sustitucion_inversa = {
        variables[i]: T_inversa_x[i]
        for i in range(n)
    }

    composicion_1 = sp.Matrix([
        sp.simplify(
            expr.subs(
                sustitucion_inversa,
                simultaneous=True
            )
        )
        for expr in T_x
    ])

    # ----------------------------------------------------------
    # 2. Calcular T^(-1)(T(x))
    # ----------------------------------------------------------

    sustitucion_directa = {
        variables[i]: T_x[i]
        for i in range(n)
    }

    composicion_2 = sp.Matrix([
        sp.simplify(
            expr.subs(
                sustitucion_directa,
                simultaneous=True
            )
        )
        for expr in T_inversa_x
    ])

    # ----------------------------------------------------------
    # 3. Verificar que ambas composiciones sean iguales a x.
    # ----------------------------------------------------------

    verificacion_1 = composicion_1.equals(vector_x)
    verificacion_2 = composicion_2.equals(vector_x)

    es_inversa = bool(
        verificacion_1 and verificacion_2
    )

    return {
        "T_de_T_inversa": composicion_1,
        "T_inversa_de_T": composicion_2,
        "verificacion_1": verificacion_1,
        "verificacion_2": verificacion_2,
        "es_inversa": es_inversa
    }


def analizar_transformacion_inversa(
    componentes,
    variables,
    matriz_inversa
):
    """
    Reúne la construcción y la verificación de T^(-1).

    Este módulo no imprime resultados.
    Solo realiza los cálculos y devuelve los datos.
    """

    construccion = construir_regla_inversa(
        matriz_inversa,
        variables
    )

    verificacion = verificar_inversa(
        componentes,
        construccion["regla_inversa"],
        variables
    )

    return {
        "vector_x": construccion["vector_x"],
        "matriz_inversa": sp.Matrix(matriz_inversa),
        "regla_inversa": construccion["regla_inversa"],
        "T_de_T_inversa": verificacion["T_de_T_inversa"],
        "T_inversa_de_T": verificacion["T_inversa_de_T"],
        "verificacion_1": verificacion["verificacion_1"],
        "verificacion_2": verificacion["verificacion_2"],
        "es_inversa": verificacion["es_inversa"]
    }