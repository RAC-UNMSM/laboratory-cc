"""Demo local que conecta modelo, validación, solución, estabilidad y gráfica."""

import argparse
from pathlib import Path

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Demo local de modelos de EDO del grupo 09")
    parser.add_argument("--modelo", choices=("lineal", "logistico", "lorenz"), default="logistico")
    args = parser.parse_args()
    ejecutar_demo(args.modelo)
