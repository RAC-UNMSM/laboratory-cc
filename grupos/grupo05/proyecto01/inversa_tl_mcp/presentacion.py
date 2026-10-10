import re
import sympy as sp


def _latex_vector(vector):
    """
    Convierte un vector o lista a LaTeX en forma de vector columna.
    """
    return sp.latex(sp.Matrix(vector))


def _latex_matriz(matriz):
    """
    Convierte una matriz de SymPy a LaTeX.
    """
    return sp.latex(sp.Matrix(matriz))


def _latex_matriz_aumentada(matriz_aumentada, n):
    """
    Convierte una matriz aumentada [A | B] a LaTeX,
    mostrando una línea vertical entre ambos bloques.
    """
    M = sp.Matrix(matriz_aumentada)

    filas = []

    for i in range(M.rows):
        elementos = [
            sp.latex(M[i, j])
            for j in range(M.cols)
        ]

        filas.append(" & ".join(elementos))

    contenido = r" \\ ".join(filas)

    columnas_izquierda = "c" * n
    columnas_derecha = "c" * (M.cols - n)

    return (
        r"\left[\begin{array}{"
        + columnas_izquierda
        + "|"
        + columnas_derecha
        + "}"
        + contenido
        + r"\end{array}\right]"
    )


def _base_canonica(n):
    """
    Genera la base canónica de R^n.
    """
    base = []

    for i in range(n):
        vector = [0] * n
        vector[i] = 1
        base.append(sp.Matrix(vector))

    return base


def _operacion_a_latex(operacion):
    """
    Convierte una operación elemental escrita como texto
    a una expresión LaTeX más natural.

    Ejemplos:

    F1 ← 1/2*F1
        ->
    F_{1}\\leftarrow \\frac{1}{2}F_{1}

    F2 ← F2 - F1
        ->
    F_{2}\\leftarrow F_{2}-F_{1}
    """

    texto = operacion.strip()

    # Convertir fracciones como 1/2, -3/4, etc.
    def reemplazar_fraccion(coincidencia):
        numerador = coincidencia.group(1)
        denominador = coincidencia.group(2)

        if numerador.startswith("-"):
            return (
                r"-\frac{"
                + numerador[1:]
                + "}{"
                + denominador
                + "}"
            )

        return (
            r"\frac{"
            + numerador
            + "}{"
            + denominador
            + "}"
        )

    texto = re.sub(
        r"(-?\d+)/(\d+)",
        reemplazar_fraccion,
        texto
    )

    # F1 -> F_{1}, F2 -> F_{2}, etc.
    texto = re.sub(
        r"F(\d+)",
        r"F_{\1}",
        texto
    )

    # Símbolos de operaciones elementales.
    texto = texto.replace(
        "←",
        r"\leftarrow"
    )

    texto = texto.replace(
        "↔",
        r"\leftrightarrow"
    )

    # En notación matemática no necesitamos "*".
    texto = texto.replace("*", "")

    # Mejorar casos como 1F_i y -1F_i.
    texto = re.sub(
        r"(?<!\d)1F_",
        r"F_",
        texto
    )

    texto = re.sub(
        r"(?<!\d)-1F_",
        r"-F_",
        texto
    )

    return texto


def construir_presentacion(
    componentes,
    variables,
    matriz_estandar,
    analisis_invertibilidad,
    resultado_gauss=None,
    resultado_inversa=None
):
    """
    Construye la solución completa en Markdown + LaTeX.

    No realiza nuevamente los cálculos matemáticos.
    Solo organiza y presenta los resultados obtenidos
    por los demás módulos.
    """

    n = len(variables)

    componentes = sp.Matrix(componentes)
    vector_x = sp.Matrix(variables)
    A = sp.Matrix(matriz_estandar)

    determinante = analisis_invertibilidad["determinante"]
    invertible = analisis_invertibilidad["invertible"]

    partes = []

    # ==========================================================
    # TÍTULO
    # ==========================================================

    partes.append(
        "# Inversa de una transformación lineal"
    )

    partes.append(
        f"Se analiza la transformación lineal "
        f"$T:\\mathbb{{R}}^{n}\\to\\mathbb{{R}}^{n}$."
    )

    # ==========================================================
    # 1. TRANSFORMACIÓN LINEAL
    # ==========================================================

    partes.append(
        "## 1. Transformación lineal"
    )

    partes.append(
        "$$"
        + r"T\left("
        + _latex_vector(vector_x)
        + r"\right)"
        + "="
        + _latex_vector(componentes)
        + "$$"
    )

    # ==========================================================
    # 2. BASE CANÓNICA
    # ==========================================================

    partes.append(
        "## 2. Base canónica"
    )

    base = _base_canonica(n)

    for i, vector in enumerate(base, start=1):
        partes.append(
            "$$"
            + rf"e_{{{i}}}="
            + _latex_vector(vector)
            + "$$"
        )

    # ==========================================================
    # 3. IMÁGENES DE LA BASE CANÓNICA
    # ==========================================================

    partes.append(
        "## 3. Imágenes de los vectores de la base canónica"
    )

    for i in range(n):
        imagen = A[:, i]

        partes.append(
            "$$"
            + rf"T(e_{{{i + 1}}})="
            + _latex_vector(imagen)
            + "$$"
        )

    # ==========================================================
    # 4. MATRIZ ESTÁNDAR
    # ==========================================================

    partes.append(
        "## 4. Matriz estándar"
    )

    partes.append(
        "Las columnas de la matriz estándar son "
        "$T(e_1),T(e_2),\\ldots,T(e_n)$."
    )

    partes.append(
        "$$"
        + "A="
        + _latex_matriz(A)
        + "$$"
    )

    # ==========================================================
    # 5. ANÁLISIS DE INVERTIBILIDAD
    # ==========================================================

    partes.append(
        "## 5. Análisis de invertibilidad"
    )

    partes.append(
        "$$"
        + r"\det(A)="
        + sp.latex(determinante)
        + "$$"
    )

    if not invertible:

        partes.append("Como")

        partes.append(
            "$$"
            + r"\det(A)=0"
            + "$$"
        )

        partes.append(
            "la matriz estándar no es invertible. "
            "Por lo tanto, la transformación lineal no es biyectiva "
            "y **no existe** $T^{-1}$."
        )

        return "\n\n".join(partes)

    partes.append("Como")

    partes.append(
        "$$"
        + r"\det(A)\neq 0"
        + "$$"
    )

    partes.append(
        "la matriz $A$ es invertible y, por lo tanto, "
        "la transformación lineal es biyectiva. "
        "Se puede calcular $T^{-1}$."
    )

    # ==========================================================
    # 6. GAUSS-JORDAN
    # ==========================================================

    if resultado_gauss is not None:

        partes.append(
            "## 6. Cálculo de $A^{-1}$ mediante Gauss-Jordan"
        )

        matriz_inicial = resultado_gauss["matriz_inicial"]

        partes.append(
            "Se forma la matriz aumentada:"
        )

        partes.append(
            "$$"
            + _latex_matriz_aumentada(
                matriz_inicial,
                n
            )
            + "$$"
        )

        for numero, paso in enumerate(
            resultado_gauss["pasos"],
            start=1
        ):

            operacion_latex = _operacion_a_latex(
                paso["operacion"]
            )

            partes.append(
                "$$"
                + rf"\text{{Paso {numero}:}}\qquad "
                + operacion_latex
                + "$$"
            )

            partes.append(
                "$$"
                + _latex_matriz_aumentada(
                    paso["matriz"],
                    n
                )
                + "$$"
            )

        partes.append(
            "Al finalizar el proceso se obtiene:"
        )

        partes.append(
            "$$"
            + _latex_matriz_aumentada(
                resultado_gauss["matriz_final"],
                n
            )
            + "$$"
        )

        # ======================================================
        # 7. MATRIZ INVERSA
        # ======================================================

        partes.append(
            "## 7. Matriz inversa"
        )

        A_inversa = resultado_gauss["inversa"]

        partes.append(
            "$$"
            + r"A^{-1}="
            + _latex_matriz(A_inversa)
            + "$$"
        )

    # ==========================================================
    # 8. TRANSFORMACIÓN LINEAL INVERSA
    # ==========================================================

    if resultado_inversa is not None:

        partes.append(
            "## 8. Transformación lineal inversa"
        )

        A_inversa = resultado_inversa["matriz_inversa"]
        regla_inversa = resultado_inversa["regla_inversa"]

        partes.append(
            "Multiplicamos la matriz inversa por el vector de entrada:"
        )

        partes.append(
            "$$"
            + _latex_matriz(A_inversa)
            + r"\,"
            + _latex_vector(vector_x)
            + "="
            + _latex_vector(regla_inversa)
            + "$$"
        )

        partes.append(
            "Por lo tanto:"
        )

        partes.append(
            "$$"
            + r"T^{-1}\left("
            + _latex_vector(vector_x)
            + r"\right)"
            + "="
            + _latex_vector(regla_inversa)
            + "$$"
        )

        # ======================================================
        # 9. VERIFICACIÓN
        # ======================================================

        partes.append(
            "## 9. Verificación"
        )

        partes.append(
            "Verificamos primero:"
        )

        partes.append(
            "$$"
            + r"T\left("
            + r"T^{-1}\left("
            + _latex_vector(vector_x)
            + r"\right)"
            + r"\right)"
            + "="
            + _latex_vector(
                resultado_inversa["T_de_T_inversa"]
            )
            + "$$"
        )

        partes.append(
            "$$"
            + r"T\left(T^{-1}(x)\right)=x"
            + "$$"
        )

        partes.append(
            "Ahora verificamos la otra composición:"
        )

        partes.append(
            "$$"
            + r"T^{-1}\left("
            + r"T\left("
            + _latex_vector(vector_x)
            + r"\right)"
            + r"\right)"
            + "="
            + _latex_vector(
                resultado_inversa["T_inversa_de_T"]
            )
            + "$$"
        )

        partes.append(
            "$$"
            + r"T^{-1}\left(T(x)\right)=x"
            + "$$"
        )

        if resultado_inversa["es_inversa"]:
            partes.append(
                "$$"
                + r"\boxed{\text{Por lo tanto, }"
                + r"T^{-1}"
                + r"\text{ es la inversa de }T.}"
                + "$$"
            )

    return "\n\n".join(partes)