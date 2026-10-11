"""Los sistemas que el balotario nombra, y los datos que un enunciado trae escritos.

Un enunciado como "Para el atractor de Lorenz con σ = 10, b = 8/3, r = 28..."
ya dice qué sistema es y con qué valores. Pedirle al usuario que además escriba
las ecuaciones sería pedirle lo que el enunciado contiene, así que aquí están:

* `SISTEMAS`: Lorenz, Rössler, Hénon, el mapa logístico y el mapa tienda, con
  sus ecuaciones y los parámetros canónicos que usa el balotario;
* `reconocer_sistema`: cuál de ellos nombra un texto;
* `valores_asignados`: las asignaciones "a = b = 0.2", "σ = 10", "δ ≈ 4.669",
  "λ₁ ≈ 0.9056" que trae un enunciado, para no usar un valor canónico cuando el
  enunciado da otro;
* `leer_seccion`: la sección de Poincaré "y = 0, ẏ > 0".

Nada de esto adivina: si el texto no nombra un sistema, no se completa nada, y
los valores explícitos de la solicitud siempre mandan sobre lo leído.
"""

from __future__ import annotations

import re
import unicodedata

#: Sistemas con nombre. `parametros` son los canónicos del balotario; los
#: que el enunciado escriba los reemplazan. `parametro` es el que se estudia de
#: forma simbólica (la r del mapa logístico en 4.2 y 4.3).
SISTEMAS = {
    "lorenz": {
        "nombre": "sistema de Lorenz (1963)",
        "palabras": ("lorenz",),
        "ecuaciones": ["sigma*(y - x)", "r*x - y - x*z", "x*y - b*z"],
        "variables_estado": ["x", "y", "z"],
        "parametros": {"sigma": 10.0, "r": 28.0, "b": 8.0 / 3.0},
        "alias": {"sigma": ("sigma", "σ"), "r": ("r", "rho", "ρ"), "b": ("b", "beta", "β")},
        "tipo_de_sistema": "edo_continua",
    },
    "rossler": {
        "nombre": "sistema de Rössler (1976)",
        "palabras": ("rossler",),
        "ecuaciones": ["-y - z", "x + a*y", "b + z*(x - c)"],
        "variables_estado": ["x", "y", "z"],
        "parametros": {"a": 0.2, "b": 0.2, "c": 5.7},
        "alias": {"a": ("a",), "b": ("b",), "c": ("c",)},
        "tipo_de_sistema": "edo_continua",
    },
    "henon": {
        "nombre": "mapa de Hénon (1976)",
        "palabras": ("henon",),
        "ecuaciones": ["1 - a*x**2 + y", "b*x"],
        "variables_estado": ["x", "y"],
        "parametros": {"a": 1.4, "b": 0.3},
        "alias": {"a": ("a",), "b": ("b",)},
        "tipo_de_sistema": "mapa_discreto",
    },
    "logistico": {
        "nombre": "mapa logístico",
        "palabras": ("mapa logistico", "logistic map", "aplicacion logistica"),
        "ecuaciones": ["r*x*(1 - x)"],
        "variables_estado": ["x"],
        "parametros": {},
        "parametro": "r",
        "rango_parametro": [0.0, 4.0],
        "region": {"x": [0.0, 1.0]},
        "alias": {"r": ("r",)},
        "tipo_de_sistema": "mapa_discreto",
    },
    "tienda": {
        "nombre": "mapa tienda",
        "palabras": ("mapa tienda", "tent map", "mapa de la tienda"),
        "ecuaciones": ["1 - Abs(1 - 2*x)"],
        "variables_estado": ["x"],
        "parametros": {},
        "alias": {},
        "tipo_de_sistema": "mapa_discreto",
    },
}

_GRIEGAS = {"σ": "sigma", "ρ": "rho", "β": "beta", "δ": "delta", "λ": "lambda", "μ": "mu",
            "ε": "epsilon", "γ": "gamma", "α": "alpha"}
_SUBINDICES = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes (la ö de Rössler y la é de Hénon incluidas)."""
    sin_tildes = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).lower()


def reconocer_sistema(texto: str | None) -> str | None:
    """La clave del sistema que nombra el texto, o None."""
    plano = normalizar(texto or "")
    for clave, sistema in SISTEMAS.items():
        if any(p in plano for p in sistema["palabras"]):
            return clave
    return None


# ---------------------------------------------------------------------------
# Asignaciones escritas en el enunciado
# ---------------------------------------------------------------------------

#: Un nombre: letra latina o griega, o una macro de LaTeX (\sigma), con un
#: subíndice opcional (r_1, r_{2}, \lambda_3).
_NOMBRE = r"(?:\\[A-Za-z]+|[A-Za-zσρβδλμεγα])(?:_\{?[A-Za-z0-9]+\}?)?"
#: Un número: entero, decimal (con punto o coma) o fracción 8/3.
_NUMERO = r"[-+]?\d+(?:[.,]\d+)?(?:\s*/\s*\d+(?:[.,]\d+)?)?"
_IGUAL = r"\s*(?:=|≈|\\approx|\\simeq|~)\s*"
_ASIGNACION = re.compile(rf"((?:{_NOMBRE}{_IGUAL})+)({_NUMERO})")


def _nombre_canonico(nombre: str) -> str:
    nombre = nombre.translate(_SUBINDICES).replace("{", "").replace("}", "").strip()
    nombre = nombre.lstrip("\\")
    for griega, latina in _GRIEGAS.items():
        nombre = nombre.replace(griega, latina)
    return nombre


def _a_numero(texto: str) -> float:
    texto = texto.replace(",", ".").replace(" ", "")
    if "/" in texto:
        numerador, denominador = texto.split("/")
        return float(numerador) / float(denominador)
    return float(texto)


def valores_asignados(texto: str | None) -> dict[str, float]:
    """{nombre: valor} de las asignaciones "a = b = 0.2", "σ = 10", "δ ≈ 4.669".

    Un número seguido de un operador (r₂ = 1 + √6) no es el valor de la
    variable: se descarta en lugar de quedarse con el 1. Si la misma variable
    aparece dos veces, la segunda escritura ("≈ 3.44949") completa a la
    primera.
    """
    if not texto:
        return {}
    limpio = texto.replace("−", "-").replace("–", "-").translate(_SUBINDICES)
    valores = {}
    for coincidencia in _ASIGNACION.finditer(limpio):
        nombres_texto, numero = coincidencia.groups()
        resto = limpio[coincidencia.end():].lstrip()
        if resto[:1] in ("+", "-", "*", "/", "^", "(", "}", "x") or resto.startswith("\\cdot") \
                or resto.startswith("\\sqrt") or resto.startswith("\\times"):
            continue
        try:
            valor = _a_numero(numero)
        except ValueError:
            continue
        for nombre in re.split(_IGUAL, nombres_texto):
            if nombre.strip():
                valores[_nombre_canonico(nombre)] = valor
    # "r_2 = 1 + \sqrt{6} \approx 3.44949": el valor viene tras el ≈.
    for coincidencia in re.finditer(rf"({_NOMBRE})\s*=[^=,;$\n]*?(?:≈|\\approx)\s*({_NUMERO})", limpio):
        nombre, numero = coincidencia.groups()
        clave = _nombre_canonico(nombre)
        if clave not in valores:
            try:
                valores[clave] = _a_numero(numero)
            except ValueError:
                pass
    return valores


def parametros_del_enunciado(clave: str, texto: str | None) -> dict[str, float]:
    """Los parámetros del sistema `clave` que el enunciado fija con otro valor."""
    sistema = SISTEMAS[clave]
    leidos = valores_asignados(texto)
    encontrados = {}
    for parametro, alias in sistema["alias"].items():
        for nombre in alias:
            canonico = _nombre_canonico(nombre)
            if canonico in leidos:
                encontrados[parametro] = leidos[canonico]
                break
    return encontrados


def exponentes_del_enunciado(texto: str | None) -> list[float] | None:
    """[λ₁, λ₂, ...] si el enunciado los escribe ("λ_1 ≈ 0.9056, λ_2 = 0, ...")."""
    leidos = valores_asignados(texto)
    indices = sorted(int(k.split("_")[1]) for k in leidos
                     if re.fullmatch(r"lambda_\d+", k))
    if len(indices) < 2 or indices != list(range(1, len(indices) + 1)):
        return None
    return [leidos[f"lambda_{i}"] for i in indices]


_DOMINIO_UNIDAD = re.compile(r"\\in\s*\[\s*0\s*,\s*1\s*\]|∈\s*\[\s*0\s*,\s*1\s*\]")


def dominio_unidad(texto: str | None) -> bool:
    """True si el enunciado dice x ∈ [0, 1]."""
    return bool(texto and _DOMINIO_UNIDAD.search(texto))


_SECCION = re.compile(r"\b([xyz])\s*=\s*(" + _NUMERO + r")\s*[,;]?\s*(?:\\dot\{?([xyz])\}?|([xyz])'|([xyz])̇)\s*([<>])\s*0")


def leer_seccion(texto: str | None) -> dict | None:
    """{"variable", "valor", "sentido"} de "y = 0, ẏ > 0" o "y = 0,\\ \\dot{y} > 0"."""
    if not texto:
        return None
    # NFD separa la ẏ precompuesta en y + punto combinante.
    limpio = unicodedata.normalize("NFD", texto).replace("$", " ").replace("\\ ", " ").replace("\\,", " ")
    coincidencia = _SECCION.search(limpio)
    if not coincidencia:
        return None
    variable, valor, d1, d2, d3, signo = coincidencia.groups()
    derivada = d1 or d2 or d3
    if derivada != variable:
        return None
    return {"variable": variable, "valor": _a_numero(valor),
            "sentido": "creciente" if signo == ">" else "decreciente"}
