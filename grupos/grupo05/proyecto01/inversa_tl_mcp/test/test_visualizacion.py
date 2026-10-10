from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from matriz_tl import (
    crear_variables,
    construir_matriz_estandar
)

from visualizacion import generar_visualizacion_r2


# ============================================================
# 1. TRANSFORMACIÓN DE PRUEBA EN R2
# ============================================================

variables = crear_variables(2)
x1, x2 = variables

componentes = [
    2*x1 + x2,
    x1 + x2
]


# ============================================================
# 2. MATRIZ ESTÁNDAR
# ============================================================

A = construir_matriz_estandar(
    componentes,
    variables
)


# ============================================================
# 3. GENERAR VISUALIZACIÓN
# ============================================================

ruta_salida = (
    Path(__file__).parent
    / "salida_visualizacion.png"
)

resultado = generar_visualizacion_r2(
    matriz_estandar=A,
    ruta_salida=ruta_salida
)


# ============================================================
# 4. MOSTRAR RESULTADOS
# ============================================================

print("Visualización generada correctamente.")
print(f"Archivo: {resultado['ruta']}")
print(f"e1 = {resultado['e1']}")
print(f"e2 = {resultado['e2']}")
print(f"T(e1) = {resultado['T_e1']}")
print(f"T(e2) = {resultado['T_e2']}")