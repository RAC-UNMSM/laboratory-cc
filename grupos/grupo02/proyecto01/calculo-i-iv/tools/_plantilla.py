"""PLANTILLA de modulo de area -- copiar a `tools/calculo<N>.py` y reemplazar.

Este archivo NO se carga como tool (el servidor solo importa
`calculo1.py` ... `calculo4.py`, ver SECCION 3 de `server.py`): existe para
que los cuatro programadores empiecen del mismo patron y no tengan que
inventar el formato de retorno.

Reglas que NO se pueden romper (ver tools/README.md):
  - el nombre del archivo va a ser `calculo<N>.py`
  - toda funcion publica definida ACA se registra como tool MCP, con el nombre
    `<modulo>_<funcion>` (ej. `calculo1_limite_lateral`)
  - el docstring es lo que lee la IA para saber como usar la tool: tiene que
    decir que sintaxis espera, no solo para que sirve
  - se devuelve SIEMPRE un dict con la clave "estado" y nunca se lanza nada
  - parametros opcionales: `str | None = None`, nunca `str = None`
"""

from __future__ import annotations

from typing import Any

import sympy as sp

# Opcional: aca se declaran las funciones publicas del archivo, para no
# registrar las que sean solo auxiliares. Si se omite esta variable, el
# servidor registra todas las funciones publicas definidas en el archivo.
# HERRAMIENTAS = ["limite_lateral"]


def limite_lateral(expresion: str, variable: str = "x", hacia: str = "+") -> dict[str, Any]:
    """Ejemplo de tool: calcula el limite lateral de una funcion en un punto.

    Plantilla de docstring -- fijate en las tres cosas que tiene que responder:
      1. QUE hace: "limite lateral de una funcion en un punto"
      2. COMO se llama: los parametros y su tipo
      3. QUE sintaxis espera: "x**2" y no "x^2", "sin(x)" y no "sen(x)"

    Args:
        expresion: la funcion en sintaxis sympy, ej. "sin(x)/x" o
            "(x**2-1)/(x-1)". OJO: `**` para potencia, no `^`.
        variable: nombre de la variable, default "x".
        hacia: "+" (por la derecha) o "-" (por la izquierda).

    Returns:
        dict con "estado" ("exito"/"parcial"/"error"), el limite en texto y su
        LaTeX. Si el limite no existe, "estado" es "parcial" y
        "existe": False, no un error: que no exista es informacion, no una falla.
    """
    try:
        v = sp.Symbol(variable)
        f = sp.sympify(expresion)
        # limite_lateral(f, v, 0, dir="+")  ->  la derecha;  dir="-"  -> izquierda
        limite = sp.limit(f, v, 0, dir="+" if hacia == "+" else "-")
        existe = limite not in (sp.oo, -sp.oo, sp.zoo, sp.nan)
        return {
            "estado": "exito" if existe else "parcial",
            "funcion": sp.sstr(f),
            "punto": "0",
            "direccion": hacia,
            "limite": sp.sstr(limite),
            "existe": bool(existe),
            "latex": sp.latex(limite),
        }
    except Exception as exc:
        # Nunca `raise`: una excepcion aqui tumba la sesion MCP del cliente.
        return {"estado": "error", "mensaje": f"{type(exc).__name__}: {exc}"}


# =============================================================================
# Pruebas de terminal. El profesor pide ver esto funcionando sin levantar el
# servidor, asi que el bloque __main__ tiene que imprimir resultados reales.
# Reemplazar por las 2-3 funciones del area de cada uno.
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    # __name__ es "__main__" al ejecutarlo directo, y el nombre del modulo al
    # importarlo. Para que la demo se lea bien en ambos casos:
    print(f"Modulo: {__name__.rsplit('.', 1)[-1]}")
    print("=" * 60)

    # 1. limite lateral por la derecha
    print("\n[1] limite de sin(x)/x en 0 por la derecha")
    print("   ", limite_lateral("sin(x)/x", hacia="+"))

    # 2. limite lateral por la izquierda (da -1, o sea SI existe)
    print("\n[2] limite de (x**2-1)/(x-1) en 0 por la izquierda")
    print("   ", limite_lateral("(x**2-1)/(x-1)", hacia="-"))

    # 3. caso en que el limite no existe: el server no debe romperse
    print("\n[3] limite de 1/x en 0 por la derecha (no existe)")
    print("   ", limite_lateral("1/x", hacia="+"))

    # 4. caso de error: expresion mal escrita
    print("\n[4] expresion invalida (debe devolver estado=error, no romperse)")
    print("   ", limite_lateral("x^^2"))
