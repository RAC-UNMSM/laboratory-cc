from pathlib import Path
import sys

# Permite importar los módulos de la carpeta principal
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from matriz_tl import (
    crear_variables,
    construir_matriz_estandar,
    analizar_invertibilidad
)

from presentacion import construir_presentacion


# ============================================================
# 1. PROBLEMA DE PRUEBA NO INVERTIBLE
# ============================================================

variables = crear_variables(2)
x1, x2 = variables

componentes = [
    x1 + x2,
    2*x1 + 2*x2
]


# ============================================================
# 2. MATRIZ ESTÁNDAR
# ============================================================

A = construir_matriz_estandar(
    componentes,
    variables
)


# ============================================================
# 3. ANALIZAR INVERTIBILIDAD
# ============================================================

analisis = analizar_invertibilidad(A)


# ============================================================
# 4. GENERAR PRESENTACIÓN
# ============================================================

respuesta = construir_presentacion(
    componentes=componentes,
    variables=variables,
    matriz_estandar=A,
    analisis_invertibilidad=analisis
)


# ============================================================
# 5. GUARDAR RESULTADO
# ============================================================

archivo_salida = (
    Path(__file__).parent
    / "salida_no_invertible.md"
)

archivo_salida.write_text(
    respuesta,
    encoding="utf-8"
)

print("Prueba de transformación no invertible completada.")
print(f"Resultado guardado en: {archivo_salida}")