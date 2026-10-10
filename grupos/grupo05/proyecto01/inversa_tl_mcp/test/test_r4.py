from pathlib import Path
import sys

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
# 1. TRANSFORMACIÓN DE PRUEBA EN R^4
# ============================================================

variables = crear_variables(4)
x1, x2, x3, x4 = variables

componentes = [
    x1 + x2,
    x2 + x3,
    x3 + x4,
    x4
]


# ============================================================
# 2. MATRIZ ESTÁNDAR
# ============================================================

A = construir_matriz_estandar(
    componentes,
    variables
)


# ============================================================
# 3. ANÁLISIS DE INVERTIBILIDAD
# ============================================================

analisis = analizar_invertibilidad(A)


# ============================================================
# 4. GAUSS-JORDAN
# ============================================================

resultado_gauss = invertir_gauss_jordan(A)


# ============================================================
# 5. CONSTRUIR Y VERIFICAR T^(-1)
# ============================================================

resultado_inversa = analizar_transformacion_inversa(
    componentes,
    variables,
    resultado_gauss["inversa"]
)


# ============================================================
# 6. GENERAR PRESENTACIÓN
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
# 7. GUARDAR RESULTADO
# ============================================================

archivo_salida = (
    Path(__file__).parent
    / "salida_r4.md"
)

archivo_salida.write_text(
    respuesta,
    encoding="utf-8"
)

print("Prueba en R4 completada correctamente.")
print(f"Resultado guardado en: {archivo_salida}")