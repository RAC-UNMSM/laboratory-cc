from pathlib import Path
import sys

import sympy as sp

# Permite importar los módulos que están en la carpeta principal
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from matriz_tl import (
    crear_variables,
    construir_matriz_estandar,
    analizar_invertibilidad
)

from gauss_jordan import invertir_gauss_jordan

from inversa_tl import analizar_transformacion_inversa

from presentacion import construir_presentacion


# ============================================================
# 1. DEFINIR UN PROBLEMA DE PRUEBA
# ============================================================

variables = crear_variables(2)
x1, x2 = variables

componentes = [
    2*x1 + x2,
    x1 + x2
]


# ============================================================
# 2. MATRIZ ESTÁNDAR E INVERTIBILIDAD
# ============================================================

A = construir_matriz_estandar(
    componentes,
    variables
)

analisis = analizar_invertibilidad(A)


# ============================================================
# 3. GAUSS-JORDAN
# ============================================================

resultado_gauss = invertir_gauss_jordan(A)


# ============================================================
# 4. CONSTRUIR Y VERIFICAR T^(-1)
# ============================================================

resultado_inversa = analizar_transformacion_inversa(
    componentes,
    variables,
    resultado_gauss["inversa"]
)


# ============================================================
# 5. GENERAR PRESENTACIÓN TIPO LIBRO
# ============================================================

respuesta = construir_presentacion(
    componentes=componentes,
    variables=variables,
    matriz_estandar=A,
    analisis_invertibilidad=analisis,
    resultado_gauss=resultado_gauss,
    resultado_inversa=resultado_inversa
)


# ============================================================
# 6. GUARDAR LA RESPUESTA EN UN ARCHIVO MARKDOWN
# ============================================================

archivo_salida = Path(__file__).parent / "salida_presentacion.md"

archivo_salida.write_text(
    respuesta,
    encoding="utf-8"
)

print("Prueba completada correctamente.")
print(f"Resultado guardado en: {archivo_salida}")