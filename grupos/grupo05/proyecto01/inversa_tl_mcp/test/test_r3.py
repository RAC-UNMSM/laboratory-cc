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


variables = crear_variables(3)
x1, x2, x3 = variables

componentes = [
    x1,
    x2 + x3,
    x2 - x3
]

A = construir_matriz_estandar(
    componentes,
    variables
)

analisis = analizar_invertibilidad(A)

resultado_gauss = invertir_gauss_jordan(A)

resultado_inversa = analizar_transformacion_inversa(
    componentes,
    variables,
    resultado_gauss["inversa"]
)

respuesta = construir_presentacion(
    componentes=componentes,
    variables=variables,
    matriz_estandar=A,
    analisis_invertibilidad=analisis,
    resultado_gauss=resultado_gauss,
    resultado_inversa=resultado_inversa
)

archivo_salida = (
    Path(__file__).parent
    / "salida_r3.md"
)

archivo_salida.write_text(
    respuesta,
    encoding="utf-8"
)

print("Prueba en R3 completada correctamente.")
print(f"Resultado guardado en: {archivo_salida}")