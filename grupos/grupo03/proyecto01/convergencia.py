"""
Módulo: convergencia.py
Descripción: Análisis y comparación de convergencia entre métodos base y extrapolados.
             Calcula errores absolutos/relativos vs. tamaño de paso (h) y determina
             el orden de convergencia observado vs. el teórico.
"""

import numpy as np
from typing import Callable, Dict, List, Any, Union, Tuple


def estimar_orden_empirico(pasos: np.ndarray, errores: np.ndarray) -> np.ndarray:
    """
    Calcula el orden empírico de convergencia (p_obs) entre pasos consecutivos.
    
    Formula: p_obs = log(E(h_i) / E(h_{i+1})) / log(h_i / h_{i+1})
    """
    # Evitamos ceros o valores no válidos
    validez = (errores > 1e-15) & (pasos > 0)
    if np.sum(validez) < 2:
        return np.array([])

    h_val = pasos[validez]
    err_val = errores[validez]

    log_h_ratio = np.log(h_val[:-1] / h_val[1:])
    log_err_ratio = np.log(err_val[:-1] / err_val[1:])

    # Manejo de divisiones por cero o logaritmos con valores <= 0
    with np.errstate(divide='ignore', invalid='ignore'):
        ordenes = log_err_ratio / log_h_ratio
        ordenes = np.nan_to_num(ordenes, nan=0.0, posinf=0.0, neginf=0.0)

    return ordenes


def analizar_convergencia(
    metodo: Callable[[Callable, float, float], float],
    f: Callable[[float], float],
    x_o_params: Any,
    valor_exacto: float,
    pasos_h: Union[List[float], np.ndarray],
    metodo_extrapolado: Callable = None
) -> Dict[str, Any]:
    """
    Analiza la convergencia de un método numérico dado evaluando cómo decrece
    el error a medida que el tamaño de paso h disminuye.

    Parámetros:
        metodo: Función que recibe (f, x, h) y devuelve una aproximación.
        f: Función matemática a evaluar.
        x_o_params: Punto x0 o intervalo (según si es derivada o integral).
        valor_exacto: Valor analítico verdadero para calcular el error absoluto.
        pasos_h: Lista o array de tamaños de paso h (ej: [0.8, 0.4, 0.2, 0.1, 0.05]).
        metodo_extrapolado: (Opcional) Función con Richardson aplicado para comparar.

    Retorna:
        Dict con arreglos de pasos, aproximaciones, errores absolutos y órdenes observados.
    """
    pasos = np.array(pasos_h, dtype=float)
    aproximaciones = []
    errores = []

    for h in pasos:
        aprox = metodo(f, x_o_params, h)
        err = float(np.abs(aprox - valor_exacto))
        aproximaciones.append(aprox)
        errores.append(err)

    aproximaciones = np.array(aproximaciones)
    errores = np.array(errores)

    orden_observado = estimar_orden_empirico(pasos, errores)

    resultado = {
        "pasos_h": pasos,
        "aproximaciones": aproximaciones,
        "errores_absolutos": errores,
        "orden_observado_promedio": float(np.mean(orden_observado)) if len(orden_observado) > 0 else 0.0,
        "ordenes_locales": orden_observado
    }

    # Si se provee una versión extrapolada, también la evaluamos para comparar
    if metodo_extrapolado is not None:
        aprox_ext = []
        err_ext = []
        for h in pasos:
            ap_ex = metodo_extrapolado(f, x_o_params, h)
            e_ex = float(np.abs(ap_ex - valor_exacto))
            aprox_ext.append(ap_ex)
            err_ext.append(e_ex)

        aprox_ext = np.array(aprox_ext)
        err_ext = np.array(err_ext)
        orden_ext = estimar_orden_empirico(pasos, err_ext)

        resultado["extrapolado"] = {
            "aproximaciones": aprox_ext,
            "errores_absolutos": err_ext,
            "orden_observado_promedio": float(np.mean(orden_ext)) if len(orden_ext) > 0 else 0.0,
            "ordenes_locales": orden_ext
        }

    return resultado


# =====================================================================
# DEMOSTRACIÓN / PRUEBAS LOCALES (Ejecutar con `python convergencia.py`)
# =====================================================================
if __name__ == "__main__":
    print("=========================================================")
    print("  PRUEBA LOCAL DE CONVERGENCIA Y EXTRAPOLACIÓN DE RICHARDSON  ")
    print("=========================================================\n")

    # 1. Definición del problema: Derivada de f(x) = sin(x) en x = 1.0
    # Valor exacto: cos(1.0)
    f = np.sin
    x0 = 1.0
    exacto = float(np.cos(1.0))

    # 2. Método base: Diferencias centradas f'(x) ≈ (f(x+h) - f(x-h)) / (2h) -> Orden O(h^2)
    def dif_centradas(func, x, h):
        return (func(x + h) - func(x - h)) / (2 * h)

    # 3. Método extrapolado de Richardson de 1er nivel: N_2(h) = (4*D(h/2) - D(h)) / 3 -> Orden O(h^4)
    def dif_centradas_richardson(func, x, h):
        d_h = dif_centradas(func, x, h)
        d_h2 = dif_centradas(func, x, h / 2)
        return (4 * d_h2 - d_h) / 3

    # Pasos h a evaluar
    pasos = [0.4, 0.2, 0.1, 0.05, 0.025]

    # Ejecutamos el análisis
    res = analizar_convergencia(
        metodo=dif_centradas,
        f=f,
        x_o_params=x0,
        valor_exacto=exacto,
        pasos_h=pasos,
        metodo_extrapolado=dif_centradas_richardson
    )

    # 4. Presentación de resultados
    print(f"Función: f(x) = sin(x) | Eval en x = {x0} | Valor exacto: {exacto:.10f}\n")
    print(f"{'h':<8} | {'Err Base (O(h²))':<18} | {'Err Extrapolado (O(h⁴))':<22} | {'Mejora (Veces)':<15}")
    print("-" * 72)

    for i, h in enumerate(res["pasos_h"]):
        e_base = res["errores_absolutos"][i]
        e_ext = res["extrapolado"]["errores_absolutos"][i]
        ratio = e_base / e_ext if e_ext > 0 else np.nan
        print(f"{h:<8.3f} | {e_base:<18.10e} | {e_ext:<22.10e} | {ratio:<15.2f}x")

    print("-" * 72)
    print(f"\nOrden observado base (Teórico: 2.0): {res['orden_observado_promedio']:.2f}")
    print(f"Orden observado con Richardson (Teórico: 4.0): {res['extrapolado']['orden_observado_promedio']:.2f}")
    print("\n[OK] Módulo convergencia.py funcionando correctamente en local.")