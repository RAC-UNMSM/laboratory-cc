import sympy as sp


def _numero_a_texto(valor):
    """
    Convierte un número de SymPy a una representación legible
    para describir las operaciones elementales.
    """
    return str(sp.simplify(valor))


def _descripcion_eliminacion(fila_destino, fila_pivote, factor):
    """
    Genera una descripción legible de una operación elemental.

    Ejemplos:
    F2 ← F2 - 3*F1
    F3 ← F3 + F1
    """
    factor = sp.simplify(factor)

    if factor == 1:
        return f"F{fila_destino} ← F{fila_destino} - F{fila_pivote}"

    if factor == -1:
        return f"F{fila_destino} ← F{fila_destino} + F{fila_pivote}"

    if factor < 0:
        factor_positivo = -factor
        return (
            f"F{fila_destino} ← F{fila_destino} + "
            f"{_numero_a_texto(factor_positivo)}*F{fila_pivote}"
        )

    return (
        f"F{fila_destino} ← F{fila_destino} - "
        f"{_numero_a_texto(factor)}*F{fila_pivote}"
    )


def invertir_gauss_jordan(matriz):
    """
    Calcula la inversa de una matriz cuadrada mediante Gauss-Jordan.

    Devuelve:
    - la matriz aumentada inicial [A | I];
    - todas las operaciones elementales realizadas;
    - la matriz aumentada después de cada operación;
    - la matriz inversa A^(-1).

    No utiliza Matrix.inv(), ya que el objetivo es conservar
    el procedimiento paso a paso.
    """

    A = sp.Matrix(matriz)

    if A.rows != A.cols:
        raise ValueError("La matriz debe ser cuadrada.")

    n = A.rows

    if sp.simplify(A.det()) == 0:
        raise ValueError(
            "La matriz no es invertible porque su determinante es 0."
        )

    # Se construye primero la matriz aumentada [A | I].
    # Cualquier intercambio de filas se realiza sobre la fila completa.
    aumentada = A.row_join(sp.eye(n))

    matriz_inicial = aumentada.copy()
    pasos = []

    for columna in range(n):

        # ------------------------------------------------------
        # 1. Buscar un pivote distinto de cero.
        # ------------------------------------------------------
        if sp.simplify(aumentada[columna, columna]) == 0:
            fila_intercambio = None

            for fila in range(columna + 1, n):
                if sp.simplify(aumentada[fila, columna]) != 0:
                    fila_intercambio = fila
                    break

            if fila_intercambio is None:
                raise ValueError(
                    "No se encontró un pivote distinto de cero."
                )

            aumentada.row_swap(columna, fila_intercambio)

            pasos.append({
                "operacion": (
                    f"F{columna + 1} ↔ F{fila_intercambio + 1}"
                ),
                "matriz": aumentada.copy()
            })

        # ------------------------------------------------------
        # 2. Convertir el pivote en 1.
        # ------------------------------------------------------
        pivote = sp.simplify(aumentada[columna, columna])

        if pivote != 1:
            multiplicador = sp.simplify(1 / pivote)

            aumentada.row_op(
                columna,
                lambda valor, _: sp.simplify(
                    valor * multiplicador
                )
            )

            pasos.append({
                "operacion": (
                    f"F{columna + 1} ← "
                    f"{_numero_a_texto(multiplicador)}*F{columna + 1}"
                ),
                "matriz": aumentada.copy()
            })

        # ------------------------------------------------------
        # 3. Hacer cero los demás elementos de la columna.
        # ------------------------------------------------------
        for fila in range(n):

            if fila == columna:
                continue

            factor = sp.simplify(aumentada[fila, columna])

            if factor == 0:
                continue

            descripcion = _descripcion_eliminacion(
                fila + 1,
                columna + 1,
                factor
            )

            fila_pivote = aumentada.row(columna)

            aumentada.row_op(
                fila,
                lambda valor, j: sp.simplify(
                    valor - factor * fila_pivote[j]
                )
            )

            pasos.append({
                "operacion": descripcion,
                "matriz": aumentada.copy()
            })

    inversa = aumentada[:, n:]

    return {
        "matriz_inicial": matriz_inicial,
        "pasos": pasos,
        "matriz_final": aumentada,
        "inversa": inversa
    }