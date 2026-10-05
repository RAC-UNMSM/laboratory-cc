"""Interpretación de la solicitud: del pedido del cliente al problema matemático.

El modelo de lenguaje entiende el enunciado y llena los campos de la
solicitud; aquí se convierte eso en un `matematica.problema.Problema`. Como
el modelo no siempre llena todo, el enunciado (si viene) se lee además con
reglas simples y deterministas para recuperar dos cosas que deciden el
desarrollo:

* el **método** que nombra el enunciado ("Resuelva la ecuación de Bernoulli");
* lo que el enunciado **pide** ("determine el intervalo máximo", "halle la
  ecuación de las trayectorias", "exprese el periodo exacto"), que decide qué
  secciones aparecen.

Los campos explícitos de la solicitud mandan; lo leído del enunciado solo
completa lo que falte. No se adivina nada que cambie la matemática: una
ecuación sin forma de Bernoulli no se vuelve de Bernoulli porque el enunciado
lo diga, eso lo decide `matematica.clasificacion`.
"""

from __future__ import annotations

import re

from matematica.clasificacion import clave_de_metodo, normalizar
from matematica.problema import construir_problema

#: Frases del enunciado → pedido. Normalizadas: sin tildes y en minúsculas.
PEDIDOS = (
    ("intervalo maximo", "intervalo_maximo"), ("intervalo maximal", "intervalo_maximo"),
    ("intervalo de existencia", "intervalo_maximo"),
    ("solucion general", "solucion_general"),
    ("trayectorias", "trayectorias"), ("ecuacion de las orbitas", "trayectorias"),
    ("retrato de fase", "retrato_fase"), ("plano de fase", "retrato_fase"),
    ("separatriz", "separatriz"), ("homoclinica", "homoclinica"),
    ("periodo exacto", "periodo"), ("periodo de oscilacion", "periodo"),
    ("primera integral", "integral_primera"), ("energia", "energia"),
    ("hamiltonian", "hamiltoniano"),
    ("puntos fijos", "equilibrios"), ("puntos de equilibrio", "equilibrios"), ("clasifique", "equilibrios"),
    ("estabilidad", "estabilidad"), ("linealizacion", "linealizacion"),
    ("nulclina", "nulclinas"), ("variedad", "variedades"),
    ("diagrama de bifurcacion", "diagrama_bifurcacion"),
    ("ciclo limite", "ciclo_limite"), ("orbita periodica", "ciclo_limite"),
    ("poincare-bendixson", "ciclo_limite"), ("poincare bendixson", "ciclo_limite"),
    ("melnikov", "homoclinica"),
    ("exponente de lyapunov", "lyapunov"), ("tiempo caracteristico", "horizonte"),
    ("horizonte", "horizonte"),
)

#: Frases que nombran un método. El orden importa: la primera que aparece gana.
METODOS = (
    ("bernoulli", "bernoulli"), ("riccati", "riccati"), ("cauchy-euler", "cauchy_euler"),
    ("cauchy euler", "cauchy_euler"), ("separable", "separable"), ("variables separables", "separable"),
    ("factor integrante", "lineal"), ("homoclinica", "homoclinica"), ("hopf", "hopf"),
    ("silla-nodo", "bifurcacion_1d"), ("silla nodo", "bifurcacion_1d"), ("transcritica", "bifurcacion_1d"),
    ("horquilla", "bifurcacion_1d"), ("pitchfork", "bifurcacion_1d"),
    ("poincare-bendixson", "ciclo_limite"), ("hamiltoniana", "conservativo"),
    ("mapa tienda", "mapa_1d"), ("tent map", "mapa_1d"),
)

_DELTA = re.compile(r"(?:\\delta_?0|δ_?0|delta_?0|δ₀)\s*=\s*(?:10\s*\^\s*\{?\s*(-?\d+)\s*\}?|([0-9.]+e-?\d+))",
                    re.IGNORECASE)


def leer_enunciado(enunciado: str | None):
    """(método, pedidos, separación inicial) que se leen del enunciado."""
    if not enunciado:
        return None, set(), None
    texto = normalizar(enunciado)
    metodo = next((clave for frase, clave in METODOS if frase in texto), None)
    pedidos = {pedido for frase, pedido in PEDIDOS if frase in texto}
    separacion = None
    coincidencia = _DELTA.search(enunciado)
    if coincidencia:
        exponente, literal = coincidencia.groups()
        separacion = 10.0 ** int(exponente) if exponente else float(literal)
    return metodo, pedidos, separacion


def interpretar(solicitud):
    """`Problema` a partir de una solicitud ya validada por `contratos`.

    Devuelve (problema, lectura), donde `lectura` dice qué se tomó del
    enunciado, para mostrarlo en la respuesta y que el modelo pueda corregirlo.
    """
    metodo_leido, pedidos_leidos, separacion_leida = leer_enunciado(getattr(solicitud, "enunciado", None))
    metodo = getattr(solicitud, "metodo_analitico", None) or metodo_leido
    pedidos = set(getattr(solicitud, "pedidos", None) or []) | pedidos_leidos
    separacion = getattr(solicitud, "separacion_inicial", None) or separacion_leida
    problema = construir_problema(
        ecuaciones=solicitud.ecuaciones,
        variables_estado=solicitud.variables_estado,
        variable_independiente=solicitud.variable_independiente,
        parametros=solicitud.parametros,
        parametro=getattr(solicitud, "parametro", None),
        rango_parametro=getattr(solicitud, "rango_parametro", None),
        y0=getattr(solicitud, "y0", None),
        intervalo=getattr(solicitud, "intervalo", None),
        region=getattr(solicitud, "region", None),
        pedidos=pedidos,
        metodo=metodo,
        solucion_particular=getattr(solicitud, "solucion_particular", None),
        enunciado=getattr(solicitud, "enunciado", None),
        tipo_de_sistema=solicitud.tipo_de_sistema,
        trozos=[t.model_dump() if hasattr(t, "model_dump") else dict(t)
                for t in (getattr(solicitud, "trozos", None) or [])] or None,
        separacion_inicial=separacion,
    )
    lectura = {
        "metodo": metodo,
        "metodo_desde_enunciado": bool(metodo_leido and not getattr(solicitud, "metodo_analitico", None)),
        "metodo_reconocido": clave_de_metodo(metodo) if metodo else None,
        "pedidos": sorted(pedidos),
        "separacion_inicial": separacion,
    }
    return problema, lectura
