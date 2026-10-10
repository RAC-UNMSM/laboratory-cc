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

Además, una pregunta de los Temas 4 y 5 puede llegar sin ecuación: el
enunciado nombra el sistema ("el atractor de Lorenz", "el mapa de Hénon") y
trae sus datos escritos ("a = 1.4 y b = 0.3", "λ₁ ≈ 0.9056"). Entonces se
completa con `matematica.sistemas_conocidos`: las ecuaciones del sistema
nombrado con los valores que el enunciado fija, los datos numéricos (r₁, r₂,
δ, exponentes) y la sección de Poincaré.

Los campos explícitos de la solicitud mandan; lo leído del enunciado solo
completa lo que falte. No se adivina nada que cambie la matemática: una
ecuación sin forma de Bernoulli no se vuelve de Bernoulli porque el enunciado
lo diga, eso lo decide `matematica.clasificacion`.
"""

from __future__ import annotations

import re

from matematica.clasificacion import clave_de_metodo, normalizar
from matematica.problema import construir_problema
from matematica.sistemas_conocidos import (SISTEMAS, dominio_unidad, exponentes_del_enunciado, leer_seccion,
                                           parametros_del_enunciado, reconocer_sistema, valores_asignados)

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
    # Tema 4
    ("duplicacion de periodo", "duplicacion_periodo"), ("periodo 2", "duplicacion_periodo"),
    ("periodo dos", "duplicacion_periodo"), ("orbita de periodo", "duplicacion_periodo"),
    ("feigenbaum", "feigenbaum"), ("acumulacion", "feigenbaum"), ("r_\\infty", "feigenbaum"),
    ("r_infinito", "feigenbaum"), ("cascada", "feigenbaum"),
    ("disipativ", "disipatividad"), ("contraccion de volumen", "disipatividad"),
    ("contraccion del volumen", "disipatividad"), ("elipsoide", "disipatividad"),
    ("region atrapante", "disipatividad"), ("conjunto absorbente", "disipatividad"),
    ("espectro de lyapunov", "espectro_lyapunov"), ("espectro de exponentes", "espectro_lyapunov"),
    ("exponentes de lyapunov", "espectro_lyapunov"),
    # Tema 5
    ("dimension de caja", "dimension_fractal"), ("box-counting", "dimension_fractal"),
    ("box counting", "dimension_fractal"), ("conteo de cajas", "dimension_fractal"),
    ("cantor", "dimension_fractal"), ("koch", "dimension_fractal"), ("sierpinski", "dimension_fractal"),
    ("menger", "dimension_fractal"), ("dimension fractal", "dimension_fractal"),
    ("autosemejan", "dimension_fractal"),
    ("herradura", "herradura"), ("smale", "herradura"),
    ("seccion de poincare", "seccion_poincare"), ("mapa de retorno", "seccion_poincare"),
    ("mapa de primer retorno", "seccion_poincare"),
    ("kaplan", "kaplan_yorke"), ("yorke", "kaplan_yorke"), ("dimension de lyapunov", "kaplan_yorke"),
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
    # Métodos que existen pero que el balotario no trabaja: se dice, no se ignora.
    ("transformada de laplace", "laplace"), ("series de potencias", "series_de_potencias"),
    ("frobenius", "frobenius"), ("coeficientes indeterminados", "coeficientes_indeterminados"),
)

#: Pedidos para los que el parámetro de un mapa se estudia de forma simbólica.
PEDIDOS_PARAMETRICOS = {"duplicacion_periodo", "feigenbaum"}

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


#: Temas que se responden sin un sistema concreto aunque el enunciado nombre uno
#: de pasada ("la herradura de Smale que aparece en Hénon"). La dimensión
#: fractal no está aquí: "la dimensión fractal del atractor de Lorenz" es una
#: pregunta sobre Lorenz.
SIN_SISTEMA = {"herradura"}

#: Datos de Feigenbaum que un enunciado escribe como asignaciones.
_CLAVES_DE_DATOS = {"r_1": "r_1", "r1": "r_1", "r_2": "r_2", "r2": "r_2", "delta": "delta"}


def _datos_del_enunciado(enunciado, datos_explicitos, pedidos):
    """r₁, r₂, δ y los exponentes que el enunciado escribe, sin pisar los explícitos."""
    datos = dict(datos_explicitos or {})
    leidos = valores_asignados(enunciado)
    if pedidos & {"feigenbaum"}:
        for nombre, clave in _CLAVES_DE_DATOS.items():
            if nombre in leidos and clave not in datos:
                datos[clave] = leidos[nombre]
    if "exponentes" not in datos and "exponentes_lyapunov" not in datos:
        exponentes = exponentes_del_enunciado(enunciado)
        if exponentes:
            datos["exponentes"] = exponentes
    return datos


def _completar_sistema(solicitud, enunciado, pedidos):
    """Las ecuaciones del sistema que el enunciado nombra, si la solicitud no trae ninguna."""
    if solicitud.ecuaciones or pedidos & SIN_SISTEMA:
        return None
    clave = reconocer_sistema(enunciado)
    if clave is None:
        return None
    sistema = SISTEMAS[clave]
    parametros = dict(sistema["parametros"])
    del_enunciado = parametros_del_enunciado(clave, enunciado)
    parametros.update(del_enunciado)
    parametros.update(solicitud.parametros or {})
    parametro = solicitud.parametro
    rango = solicitud.rango_parametro
    if sistema.get("parametro") and parametro is None:
        nombre = sistema["parametro"]
        # La r del mapa logístico se estudia simbólica en 4.2 y 4.3 (o si no se
        # da su valor); con un valor dado y otra pregunta es un mapa concreto (4.1).
        if pedidos & PEDIDOS_PARAMETRICOS or nombre not in parametros:
            parametro = nombre
            rango = rango or sistema.get("rango_parametro")
    return {
        "clave": clave, "nombre": sistema["nombre"], "ecuaciones": list(sistema["ecuaciones"]),
        "variables_estado": list(sistema["variables_estado"]), "parametros": parametros,
        "parametro": parametro, "rango_parametro": rango,
        "region": solicitud.region or sistema.get("region"),
        "tipo_de_sistema": sistema["tipo_de_sistema"], "del_enunciado": del_enunciado,
    }


def interpretar(solicitud):
    """`Problema` a partir de una solicitud ya validada por `contratos`.

    Devuelve (problema, lectura), donde `lectura` dice qué se tomó del
    enunciado, para mostrarlo en la respuesta y que el modelo pueda corregirlo.
    """
    enunciado = getattr(solicitud, "enunciado", None)
    metodo_leido, pedidos_leidos, separacion_leida = leer_enunciado(enunciado)
    metodo = getattr(solicitud, "metodo_analitico", None) or metodo_leido
    pedidos = set(getattr(solicitud, "pedidos", None) or []) | pedidos_leidos
    separacion = getattr(solicitud, "separacion_inicial", None) or separacion_leida
    completado = _completar_sistema(solicitud, enunciado, pedidos)
    ecuaciones = completado["ecuaciones"] if completado else solicitud.ecuaciones
    variables = completado["variables_estado"] if completado else solicitud.variables_estado
    parametros = completado["parametros"] if completado else dict(solicitud.parametros or {})
    parametro = completado["parametro"] if completado else getattr(solicitud, "parametro", None)
    rango = completado["rango_parametro"] if completado else getattr(solicitud, "rango_parametro", None)
    region = completado["region"] if completado else getattr(solicitud, "region", None)
    tipo = completado["tipo_de_sistema"] if completado else solicitud.tipo_de_sistema
    # Un mapa de un parámetro al que se le pregunta por la duplicación de
    # periodo o por Feigenbaum: ese parámetro es el que se estudia.
    if tipo == "mapa_discreto" and parametro is None and pedidos & PEDIDOS_PARAMETRICOS and len(parametros) == 1:
        parametro = next(iter(parametros))
    if tipo == "mapa_discreto" and not region and len(variables) == 1 and dominio_unidad(enunciado):
        region = {variables[0]: [0.0, 1.0]}
    datos = _datos_del_enunciado(enunciado, getattr(solicitud, "datos", None), pedidos)
    seccion = getattr(solicitud, "seccion_poincare", None)
    seccion = seccion.model_dump() if hasattr(seccion, "model_dump") else seccion
    seccion = seccion or leer_seccion(enunciado)
    problema = construir_problema(
        ecuaciones=ecuaciones,
        variables_estado=variables,
        variable_independiente=solicitud.variable_independiente,
        parametros=parametros,
        parametro=parametro,
        rango_parametro=rango,
        y0=getattr(solicitud, "y0", None),
        intervalo=getattr(solicitud, "intervalo", None),
        region=region,
        pedidos=pedidos,
        metodo=metodo,
        solucion_particular=getattr(solicitud, "solucion_particular", None),
        enunciado=enunciado,
        tipo_de_sistema=tipo,
        trozos=[t.model_dump() if hasattr(t, "model_dump") else dict(t)
                for t in (getattr(solicitud, "trozos", None) or [])] or None,
        separacion_inicial=separacion,
        datos=datos,
        seccion=seccion,
    )
    lectura = {
        "metodo": metodo,
        "metodo_desde_enunciado": bool(metodo_leido and not getattr(solicitud, "metodo_analitico", None)),
        "metodo_reconocido": clave_de_metodo(metodo) if metodo else None,
        "pedidos": sorted(pedidos),
        "separacion_inicial": separacion,
    }
    if completado:
        lectura["sistema_reconocido"] = {
            "sistema": completado["nombre"], "ecuaciones": ecuaciones, "variables_estado": variables,
            "parametros": parametros, "parametro": parametro, "tipo_de_sistema": tipo,
            "valores_del_enunciado": completado["del_enunciado"]}
    if datos:
        lectura["datos"] = datos
    if seccion:
        lectura["seccion_poincare"] = seccion
    return problema, lectura
