import os
import numpy as np
import matplotlib.pyplot as plt


def _a_numpy_2x2(matriz):
    """
    Convierte la matriz de entrada a un arreglo numpy 2x2.
    Acepta lista de listas, tuplas, numpy array o matriz de SymPy.
    """
    try:
        # Si viene de SymPy
        matriz = np.array(matriz.tolist(), dtype=float)
    except AttributeError:
        matriz = np.array(matriz, dtype=float)

    if matriz.shape != (2, 2):
        raise ValueError("La visualización en este módulo solo está implementada para matrices 2x2.")

    return matriz


def _limites_grafica(vectores):
    """
    Calcula límites automáticos para la gráfica,
    dejando margen suficiente para etiquetas y flechas.
    """
    xs = [v[0] for v in vectores]
    ys = [v[1] for v in vectores]

    max_x = max(abs(x) for x in xs + [0])
    max_y = max(abs(y) for y in ys + [0])

    maximo = max(max_x, max_y, 1)
    margen = 0.8

    return -maximo - margen, maximo + margen, -maximo - margen, maximo + margen


def _dibujar_vector(ax, vector, color, etiqueta, grosor=2.2):
    """
    Dibuja un vector desde el origen y coloca su etiqueta cerca de la punta.
    """
    x, y = vector

    ax.arrow(
        0, 0, x, y,
        head_width=0.10,
        head_length=0.14,
        length_includes_head=True,
        linewidth=grosor,
        color=color,
        alpha=0.95
    )

    # Etiqueta al lado de la punta
    desplazamiento_x = 0.08 if x >= 0 else -0.28
    desplazamiento_y = 0.08 if y >= 0 else -0.20

    ax.text(
        x + desplazamiento_x,
        y + desplazamiento_y,
        etiqueta,
        fontsize=10,
        fontweight="bold",
        color=color
    )


def generar_visualizacion_r2(matriz_estandar, ruta_salida):
    """
    Genera una visualización de una transformación lineal en R^2.

    Parámetros:
    - matriz_estandar: matriz 2x2 de la transformación.
    - ruta_salida: ruta donde se guardará la imagen PNG.

    Retorna:
    Un diccionario con:
    - ruta
    - e1
    - e2
    - T_e1
    - T_e2
    """
    A = _a_numpy_2x2(matriz_estandar)

    e1 = np.array([1.0, 0.0])
    e2 = np.array([0.0, 1.0])

    T_e1 = A @ e1
    T_e2 = A @ e2

    vectores = [e1, e2, T_e1, T_e2]
    xmin, xmax, ymin, ymax = _limites_grafica(vectores)

    fig, ax = plt.subplots(figsize=(8, 8))

    # Dibujar ejes
    ax.axhline(0, color="gray", linewidth=1)
    ax.axvline(0, color="gray", linewidth=1)

    # Cuadrícula
    ax.grid(True, linestyle="--", alpha=0.4)

    # Dibujar vectores
    _dibujar_vector(ax, e1, "royalblue", "e1")
    _dibujar_vector(ax, e2, "seagreen", "e2")
    _dibujar_vector(ax, T_e1, "crimson", "T(e1)")
    _dibujar_vector(ax, T_e2, "darkorange", "T(e2)")

    # Configuración de ejes
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")

    ax.set_xlabel("x1", fontsize=11)
    ax.set_ylabel("x2", fontsize=11)
    ax.set_title("Visualización de la transformación lineal en R²", fontsize=13, fontweight="bold")

    # Texto con la matriz en la parte superior izquierda
    texto_matriz = (
        "Matriz estándar A =\n"
        f"[[{A[0,0]:.2f}, {A[0,1]:.2f}],\n"
        f" [{A[1,0]:.2f}, {A[1,1]:.2f}]]"
    )

    ax.text(
        0.02, 0.98,
        texto_matriz,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85)
    )

    # Asegurar que exista la carpeta destino
    carpeta = os.path.dirname(ruta_salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=200, bbox_inches="tight")
    plt.close(fig)

    return {
        "ruta": ruta_salida,
        "e1": e1.tolist(),
        "e2": e2.tolist(),
        "T_e1": T_e1.tolist(),
        "T_e2": T_e2.tolist(),
    }