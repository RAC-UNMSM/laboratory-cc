"""
playground.py
==============

Script para comprobar TÚ MISMO que analisis_estabilidad.py funciona,
agregando tus propios casos / funciones y viendo el resultado en consola.

Cómo usarlo
-----------
1. Corre el archivo tal cual:

       python3 playground.py

   Esto imprime en consola varios casos de ejemplo ya resueltos.

2. Agrega tus propios modelos en la lista MIS_CASOS más abajo. Cada caso
   es un diccionario con este formato mínimo:

       {
           "variables": ["x"],
           "equations": ["x*(1-x)"],
           # opcional:
           "parameters": {"r": 2, "K": 100},
           "independent_variable": "t",
           "autonomous": True,
       }

3. Si quieres agregar tus PROPIAS FUNCIONES que usen piezas internas del
   módulo (no solo analizar_estabilidad de punta a punta), este archivo ya
   importa todas las funciones públicas al inicio. Ejemplos de funciones
   internas reutilizables: calcular_equilibrios, calcular_jacobiano,
   calcular_autovalores, clasificar_estabilidad. Abajo tienes un ejemplo
   (mi_funcion_personalizada) que las combina y hace print() de cada paso.
"""

import json
import pprint

from analisis_estabilidad import (
    analizar_estabilidad,
    ErrorAnalisisEstabilidad,
    # piezas internas por si quieres construir tus propias funciones:
    _normalizar_modelo,
    calcular_equilibrios,
    calcular_jacobiano,
    calcular_autovalores,
    clasificar_estabilidad,
    formatear_reporte_estabilidad,
)


def imprimir_resultado(nombre_caso: str, modelo: dict) -> None:
    """Corre analizar_estabilidad sobre un modelo y muestra el resultado
    completo en consola, de forma legible."""
    print("=" * 70)
    print(f"CASO: {nombre_caso}")
    print("-" * 70)
    print("Modelo de entrada:")
    print(json.dumps(modelo, indent=2, ensure_ascii=False))
    print()

    try:
        resultado = analizar_estabilidad(modelo)
    except ErrorAnalisisEstabilidad as e:
        print(f"[ERROR ESPERADO / CONTROLADO] {e}")
        print()
        return
    except Exception as e:  # cualquier error inesperado, para que lo veas
        print(f"[EXCEPCIÓN NO CONTROLADA] {type(e).__name__}: {e}")
        print()
        return

    # Reporte ordenado (el diccionario completo sigue disponible en `resultado`;
    # para verlo crudo descomenta la línea de pprint).
    print(formatear_reporte_estabilidad(resultado))
    # pprint.pprint(resultado, sort_dicts=False, width=100)
    print()


def mi_funcion_personalizada(modelo: dict) -> None:
    """
    Ejemplo de función propia que llama a las piezas internas del módulo
    paso a paso (en vez de usar analizar_estabilidad de una sola vez),
    imprimiendo cada etapa: normalización -> equilibrios -> jacobiano ->
    autovalores -> clasificación.

    Úsala como plantilla para tus propias funciones de verificación.
    """
    print("#" * 70)
    print("FUNCIÓN PERSONALIZADA paso a paso")
    print("#" * 70)

    modelo_norm = _normalizar_modelo(modelo)
    print(f"Variables normalizadas: {modelo_norm.variables_symbols}")
    print(f"Ecuaciones normalizadas: {modelo_norm.F}")

    # calcular_equilibrios recibe (F, variables_symbols) por SEPARADO, y
    # devuelve una tupla (lista_de_equilibrios, info_metadata). Cada
    # equilibrio es un dict {symbolo: expresión}, no una tupla de valores.
    equilibrios, info_equilibrios = calcular_equilibrios(
        modelo_norm.F, modelo_norm.variables_symbols
    )
    print(f"\nInfo del cálculo de equilibrios: {info_equilibrios}")
    print(f"Equilibrios encontrados ({len(equilibrios)}): {equilibrios}")

    J_simbolico = calcular_jacobiano(modelo_norm.F, modelo_norm.variables_symbols)

    for punto in equilibrios:
        # punto es un dict {symbolo: expresión}; sustituimos directamente.
        J_en_punto = J_simbolico.subs(punto)
        print(f"\nEn el punto {punto}:")
        print(f"  Jacobiano evaluado:\n{J_en_punto}")

        autovalores_info = calcular_autovalores(J_en_punto)
        print(f"  Autovalores: {autovalores_info}")

        clasificacion = clasificar_estabilidad(autovalores_info, len(modelo_norm.variables_symbols))
        print(f"  Clasificación: {clasificacion}")

    print()


# ---------------------------------------------------------------------
# CASOS DE EJEMPLO YA INCLUIDOS (puedes borrarlos o dejarlos)
# ---------------------------------------------------------------------
CASOS_EJEMPLO = [
    ("Lineal estable: x' = -2x", {"variables": ["x"], "equations": ["-2*x"]}),
    ("Logístico: x' = x(1-x)", {"variables": ["x"], "equations": ["x*(1-x)"]}),
    (
        "Sistema silla: x'=x, y'=-y",
        {"variables": ["x", "y"], "equations": ["x", "-y"]},
    ),
    (
        "Foco estable: x'=-x-y, y'=x-y",
        {"variables": ["x", "y"], "equations": ["-x - y", "x - y"]},
    ),
    (
        "Logístico con parámetros: r*x*(1-x/K)",
        {
            "variables": ["x"],
            "equations": ["r*x*(1 - x/K)"],
            "parameters": {"r": 2, "K": 100},
        },
    ),
    (
        "Parámetro simbólico mu: mu*x - x**3",
        {"variables": ["x"], "equations": ["mu*x - x**3"]},
    ),
    (
        "Caso inválido: no autónomo (depende de t)",
        {"variables": ["x"], "equations": ["x + t"]},
    ),
]

# ---------------------------------------------------------------------
# TUS PROPIOS CASOS: agrega aquí lo que quieras comprobar
# ---------------------------------------------------------------------
MIS_CASOS = [
    # ---- 1D: bifurcación transcrítica (silla-nodo con parámetro mu) ----
    (
        "1D transcrítica: x' = mu*x - x**2",
        {"variables": ["x"], "equations": ["mu*x - x**2"]},
    ),

    # ---- 1D: bifurcación de horca (pitchfork) supercrítica ----
    (
        "1D horca supercrítica: x' = mu*x - x**3",
        {"variables": ["x"], "equations": ["mu*x - x**3"]},
    ),

    # ---- 1D: parámetros numéricos conocidos (crecimiento logístico) ----
    (
        "1D logístico con r y K numéricos",
        {
            "variables": ["x"],
            "equations": ["r*x*(1 - x/K)"],
            "parameters": {"r": 0.8, "K": 50},
        },
    ),

    # ---- 2D: oscilador armónico amortiguado (nodo/foco según amortiguamiento) ----
    (
        "2D oscilador amortiguado: x'=y, y'=-k*x - c*y",
        {
            "variables": ["x", "y"],
            "equations": ["y", "-k*x - c*y"],
            "parameters": {"k": 1, "c": 0.5},
        },
    ),

    # ---- 2D: depredador-presa tipo Lotka-Volterra ----
    (
        "2D Lotka-Volterra: x'=x(a-by), y'=y(cx-d)",
        {
            "variables": ["x", "y"],
            "equations": ["x*(a - b*y)", "y*(c*x - d)"],
            "parameters": {"a": 1, "b": 0.5, "c": 0.5, "d": 1},
        },
    ),

    # ---- 2D: centro puro (autovalores imaginarios puros, no concluyente) ----
    (
        "2D centro: x'=-y, y'=x (no concluyente por linealización)",
        {"variables": ["x", "y"], "equations": ["-y", "x"]},
    ),

    # ---- 2D: van der Pol linealizado alrededor del origen ----
    (
        "2D van der Pol: x'=y, y'=mu*(1-x**2)*y - x",
        {
            "variables": ["x", "y"],
            "equations": ["y", "mu*(1 - x**2)*y - x"],
            "parameters": {"mu": 1},
        },
    ),

    # ---- 3D: sistema lineal desacoplado, todo estable ----
    (
        "3D lineal estable: x'=-x, y'=-2y, z'=-3z",
        {"variables": ["x", "y", "z"], "equations": ["-x", "-2*y", "-3*z"]},
    ),

    # ---- 3D: variante simplificada tipo Lorenz (para ver qualitative_type=None en 3D) ----
    (
        "3D tipo Lorenz simplificado",
        {
            "variables": ["x", "y", "z"],
            "equations": ["sigma*(y - x)", "x*(rho - z) - y", "x*y - beta*z"],
            "parameters": {"sigma": 10, "rho": 0.5, "beta": 2.667},
        },
    ),

    # ---- Caso con parámetro simbólico libre (no se debe inventar valor) ----
    (
        "1D con parámetro totalmente simbólico: x' = a*x + b",
        {"variables": ["x"], "equations": ["a*x + b"]},
    ),

    # ---- Caso inválido esperado: dimensión no soportada (4 variables) ----
    (
        "Inválido: 4 variables (fuera de rango soportado)",
        {
            "variables": ["a", "b", "c", "d"],
            "equations": ["-a", "-b", "-c", "-d"],
        },
    ),

    # ---- Caso inválido esperado: sistema no autónomo ----
    (
        "Inválido: depende explícitamente de t",
        {"variables": ["x", "y"], "equations": ["x - t", "y + x"]},
    ),
    (
    "x' = A - (B+1)x + x²y , y' = Bx - x²y" , {
    "variables": ["x", "y"],
    "equations": ["A - (B+1)*x + x**2*y", "B*x - x**2*y"],
    "parameters": {"A": 1, "B": 3},
}
        
        ),
]


if __name__ == "__main__":
    print("\n>>> CORRIENDO CASOS DE EJEMPLO INCLUIDOS <<<\n")
    for nombre, modelo in CASOS_EJEMPLO:
        imprimir_resultado(nombre, modelo)

    if MIS_CASOS:
        print("\n>>> CORRIENDO MIS_CASOS (agregados por el usuario) <<<\n")
        for nombre, modelo in MIS_CASOS:
            imprimir_resultado(nombre, modelo)

    # Ejemplo de uso de la función personalizada paso a paso:
    print("\n>>> EJEMPLO DE FUNCIÓN PERSONALIZADA PASO A PASO <<<\n")
    mi_funcion_personalizada({"variables": ["x"], "equations": ["x*(1-x)"]})

    # Opcional: barrido de bifurcaciones. Solo funciona si este archivo está en la
    # carpeta del proyecto (necesita modelo_edos.py); si no, se omite sin error.
    # playground.py NO es usado por server.py: es solo para pruebas manuales.
    try:
        from analisis_bifurcaciones import ejecutar_forma_normal, imprimir_reporte_bifurcaciones
    except ImportError:
        print("\n(analisis_bifurcaciones.py no disponible aquí: se omite el ejemplo de bifurcaciones)")
    else:
        print("\n>>> EJEMPLO DE BIFURCACIONES (forma normal de horquilla) <<<\n")
        imprimir_reporte_bifurcaciones(ejecutar_forma_normal("horquilla"))
