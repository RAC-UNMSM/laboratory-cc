"""Solución Markdown/LaTeX adaptada de la presentación del proyecto paralelo.

Usa los resultados del motor común: no vuelve a invertir ni a verificar matrices.
"""
import sympy as sp

from validacion import expresion_segura


def _latex_matriz(filas, variables=(), corte=None):
    matriz = [[expresion_segura(v, variables) for v in fila] for fila in filas]
    if corte is None:
        return sp.latex(sp.Matrix(matriz))
    columnas = "c"*corte + "|" + "c"*(len(matriz[0])-corte)
    contenido = r" \\ ".join(" & ".join(sp.latex(v) for v in fila) for fila in matriz)
    return r"\left[\begin{array}{" + columnas + "}" + contenido + r"\end{array}\right]"


def _latex_vector(componentes, variables=()):
    return _latex_matriz([[v] for v in componentes], variables)


def _ecuacion(texto):
    return "$$\n" + texto + "\n$$"


def construir_presentacion(resultado):
    """Presenta una solución de Rn a Rn obtenida por analizar(..., True)."""
    n = resultado["columnas"]
    x = sp.symbols(f"x1:{n+1}")
    y = sp.symbols(f"y1:{n+1}")
    partes = [
        "# Inversa de una transformación lineal",
        _ecuacion(rf"T:\mathbb{{R}}^{n}\longrightarrow\mathbb{{R}}^{n}"),
        "## 1. Regla de correspondencia",
        _ecuacion(r"T(\mathbf{x})=" + _latex_vector(resultado["regla_en_coordenadas_canonicas"], x)),
        "## 2. Base canónica",
    ]
    for j, vector in enumerate(resultado["base_B"]["elementos"], 1):
        partes.append(_ecuacion(rf"e_{{{j}}}=" + _latex_vector(vector)))
    partes.append("## 3. Imágenes de la base canónica")
    for imagen in resultado["imagenes_de_B"]:
        j = imagen["elemento_base_dominio"]
        partes.append(_ecuacion(rf"T(e_{{{j}}})=" + _latex_vector(imagen["imagen"])))
    partes.extend([
        "## 4. Matriz estándar",
        "Las columnas de A son las imágenes de los vectores de la base canónica.",
        _ecuacion("A=" + _latex_matriz(resultado["matriz_canonica"])),
        "## 5. Invertibilidad",
        _ecuacion(r"\det(A)=" + sp.latex(expresion_segura(resultado["determinante"]))),
        f"El rango de A es {resultado['rango']}.",
    ])
    if not resultado["invertible"]:
        partes.append("El determinante es cero. La transformación no es biyectiva y no existe una inversa global.")
        return "\n\n".join(partes)

    inversa = resultado["inversa"]
    partes.extend([
        "El determinante es distinto de cero. La transformación es biyectiva.",
        "## 6. Gauss-Jordan",
        "Se transforma la matriz aumentada [A | I] en [I | A⁻¹].",
    ])
    for j, paso in enumerate(inversa["pasos_gauss_jordan"]):
        etiqueta = "Inicio" if j == 0 else f"Paso {j}"
        partes.extend([
            f"**{etiqueta}:** `{paso['operacion']}`",
            _ecuacion(_latex_matriz(paso["matriz_aumentada"], corte=n)),
        ])
    partes.extend([
        "## 7. Matriz inversa",
        _ecuacion(r"A^{-1}=" + _latex_matriz(inversa["matriz_canonica"])),
        "## 8. Transformación inversa",
        _ecuacion(r"T^{-1}(\mathbf{y})=" + _latex_vector(inversa["regla_en_coordenadas_canonicas"], y)),
        "## 9. Verificación de ambas composiciones",
        _ecuacion(r"A^{-1}A=" + _latex_matriz(inversa["verificacion"]["T_inversa_compuesta_T"])),
        _ecuacion(r"AA^{-1}=" + _latex_matriz(inversa["verificacion"]["T_compuesta_T_inversa"])),
    ])
    if inversa["verificacion"]["ambas_identidades"]:
        partes.extend([
            _ecuacion(r"T^{-1}(T(\mathbf{x}))=\mathbf{x}"),
            _ecuacion(r"T(T^{-1}(\mathbf{y}))=\mathbf{y}"),
            "Ambas composiciones son la identidad: la inversa queda verificada exactamente.",
        ])
    else:
        partes.append("La verificación no produjo ambas identidades.")
    return "\n\n".join(partes)
