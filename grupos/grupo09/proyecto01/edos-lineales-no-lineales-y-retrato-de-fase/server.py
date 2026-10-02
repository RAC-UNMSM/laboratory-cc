"""Demo local que conecta modelo, validación, solución, estabilidad y gráfica."""

import argparse
from pathlib import Path

from analisis_bifurcaciones import FORMAS_NORMALES, ejecutar_forma_normal, imprimir_reporte_bifurcaciones
from analisis_estabilidad import (
    analizar_equilibrios,
    analizar_estabilidad_referencia,
    formatear_equilibrios_numericos,
    imprimir_reporte_estabilidad,
)
from analisis_estabilidad import analizar_equilibrios
from modelo_edos import resolver_edo
from modelos_referencia import obtener_modelo
from visualizacion import graficar_retrato_fase_1d, graficar_solucion


def ejecutar_demo(nombre="logistico"):
    config = obtener_modelo(nombre)
    modelo = config["funcion"]
    print(f"Modelo: {nombre.capitalize()}")
    print(f"Parámetros: {config['parametros']}")
    print(f"Condición inicial: {config['y0']}")
    print(f"Intervalo: {config['intervalo']}")
    print("Resolviendo...", flush=True)
    solucion = resolver_edo(modelo, config["y0"], config["intervalo"], config["parametros"])
    print(f"Solución calculada correctamente ({len(solucion.t)} puntos).")
    print(f"Estado final: {solucion.y[:, -1]}")

    if "equilibrios" in config:
        resultados = analizar_equilibrios(modelo, config["equilibrios"](config["parametros"]), config["parametros"])
        print("\nEquilibrios y estabilidad local:")
        print(formatear_equilibrios_numericos(resultados))
        for resultado in resultados:
            eq = resultado["equilibrio"]
            print(f"  x = {eq[0]:g}: {resultado['clasificacion']}; autovalores = {resultado['autovalores']}")

    ruta = Path(__file__).resolve().parent / f"grafica_{nombre}.png"
    guardada = graficar_solucion(solucion, titulo=f"Modelo {nombre.capitalize()}", archivo_salida=ruta)
    print(f"\nGráfica guardada en: {guardada}")
    if config["dimension"] == 1 and "equilibrios" in config:
        equilibrios = config["equilibrios"](config["parametros"])
        escala = max(1.0, *(abs(float(e)) for e in equilibrios))
        rango_x = (-0.2 * escala, 1.4 * escala)
        iniciales = [config["y0"][0], 1.2 * escala]
        if nombre == "lineal":
            rango_x = (-1.5 * escala, 1.5 * escala)
            iniciales = [1.0, -1.0]
        ruta_fase = Path(__file__).resolve().parent / f"retrato_fase_{nombre}.png"
        fase = graficar_retrato_fase_1d(
            modelo, equilibrios, config["parametros"], rango_x,
            config["intervalo"], iniciales, ruta_fase,
        )
        print(f"Retrato de fase (flechas y puntos de equilibrio): {fase}")
    return solucion


def ejecutar_estabilidad(nombre):
    """Análisis de estabilidad simbólico (analisis_estabilidad.py) de un modelo de referencia."""
    imprimir_reporte_estabilidad(analizar_estabilidad_referencia(nombre))


def ejecutar_bifurcaciones(caso):
    """Barrido de bifurcación (analisis_bifurcaciones.py) de una forma normal de referencia."""
    resultado = ejecutar_forma_normal(caso)
    imprimir_reporte_bifurcaciones(resultado)
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo local de modelos de EDO del grupo 09")
    parser.add_argument("--modelo", choices=("lineal", "logistico", "lorenz"), default="logistico")
    parser.add_argument("--estabilidad", action="store_true",
                        help="Imprime además el análisis de estabilidad simbólico del modelo.")
    parser.add_argument("--bifurcacion", choices=tuple(FORMAS_NORMALES),
                        help="Ejecuta el barrido de bifurcación de una forma normal (en vez de la demo).")
    args = parser.parse_args()
    if args.bifurcacion:
        ejecutar_bifurcaciones(args.bifurcacion)
    else:
        ejecutar_demo(args.modelo)
        if args.estabilidad:
            print()
            ejecutar_estabilidad(args.modelo)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo local de modelos de EDO del grupo 09")
    parser.add_argument("--modelo", choices=("lineal", "logistico", "lorenz"), default="logistico")
    args = parser.parse_args()
    ejecutar_demo(args.modelo)
