"""Tutor sin estado: catálogo verificable, sin historial de otros estudiantes."""

from validacion import EntradaError

LESSONS = {
    "limites": {
        "curso": "I",
        "prerrequisitos": ["funciones", "dominio"],
        "teoria": "Un límite describe el comportamiento cerca de un punto. Para un límite bilateral, compare ambos laterales.",
        "ejemplo": {"operacion": "limite", "expresion": "sin(x)/x", "punto": "0"},
        "ejercicio": {"expresion": "(x**2-1)/(x-1)", "punto": "1"},
        "pregunta": "Calcule el límite al acercarse x a 1.",
        "respuesta": "2",
        "pista": "Factorice x²−1 y trabaje con x distinto de 1.",
        "tipo": "valor",
    },
    "derivadas": {
        "curso": "I",
        "prerrequisitos": ["limites"],
        "teoria": "La derivada es la razón de cambio local. La regla de la cadena combina las derivadas de funciones compuestas.",
        "ejemplo": {"operacion": "derivada", "expresion": "sin(x**2)"},
        "ejercicio": {"expresion": "x**3"},
        "pregunta": "Derive x³ respecto de x.",
        "respuesta": "3*x**2",
        "pista": "Use d(x^n)/dx = n*x^(n−1).",
        "tipo": "identidad",
    },
    "integrales": {
        "curso": "II",
        "prerrequisitos": ["derivadas"],
        "teoria": "Una primitiva F cumple F'=f. En un intervalo conectado, las primitivas difieren por una constante.",
        "ejemplo": {"operacion": "integral", "expresion": "2*x"},
        "ejercicio": {"expresion": "cos(x)"},
        "pregunta": "Dé una primitiva de cos(x), sin escribir +C.",
        "respuesta": "sin(x)",
        "pista": "Busque una función cuya derivada sea cos(x).",
        "tipo": "primitiva",
    },
    "gradiente": {
        "curso": "III",
        "prerrequisitos": ["derivadas"],
        "teoria": "El gradiente reúne las derivadas parciales. Su producto con un vector unitario da la derivada direccional donde la función es diferenciable.",
        "ejemplo": {
            "operacion": "gradiente",
            "expresion": "x**2+y**2",
            "variables": ["x", "y"],
        },
        "ejercicio": {},
        "pregunta": "Calcule ∂(x²+y²)/∂x.",
        "respuesta": "2*x",
        "pista": "Trate y como constante.",
        "tipo": "identidad",
    },
    "integrales_multiples": {
        "curso": "IV",
        "prerrequisitos": ["integrales", "gradiente"],
        "teoria": "Una integral iterada elimina una variable por etapa. Las fronteras de la integral interior pueden depender de las variables exteriores.",
        "ejemplo": {
            "operacion": "integral_multiple",
            "expresion": "1",
            "limites": [
                {"variable": "y", "inferior": "0", "superior": "x"},
                {"variable": "x", "inferior": "0", "superior": "1"},
            ],
        },
        "ejercicio": {},
        "pregunta": "Calcule la integral de 1 sobre 0≤y≤x≤1.",
        "respuesta": "1/2",
        "pista": "La integral interna da x. Integre luego entre 0 y 1.",
        "tipo": "valor",
    },
    "lagrange": {
        "curso": "III",
        "prerrequisitos": ["gradiente"],
        "teoria": "Los candidatos regulares restringidos satisfacen grad(f)=λ grad(g), g=0. Hay que estudiar por separado puntos singulares y existencia de extremos.",
        "ejemplo": {
            "operacion": "lagrange",
            "expresion": "x+y",
            "variables": ["x", "y"],
            "restriccion": "x**2+y**2-1",
        },
        "ejercicio": {},
        "pregunta": "¿Cuál es el valor máximo de x+y en x²+y²=1?",
        "respuesta": "sqrt(2)",
        "pista": "Use Cauchy–Schwarz o compare los candidatos de Lagrange.",
        "tipo": "valor",
    },
    "green": {
        "curso": "IV",
        "prerrequisitos": ["integrales_multiples"],
        "teoria": "Para una frontera positiva y campo C¹ en un entorno del dominio, ∮P dx+Q dy = ∬(Q_x−P_y)dA. Las orientaciones de huecos son opuestas a la exterior.",
        "ejemplo": {
            "operacion": "green",
            "campo": ["-y/2", "x/2"],
            "limites": [
                {"variable": "y", "inferior": "0", "superior": "1"},
                {"variable": "x", "inferior": "0", "superior": "1"},
            ],
        },
        "ejercicio": {},
        "pregunta": "Calcule la circulación del ejemplo sobre la frontera positiva del cuadrado unidad.",
        "respuesta": "1",
        "pista": "El integrando Q_x−P_y es 1.",
        "tipo": "valor",
    },
    "stokes": {
        "curso": "IV",
        "prerrequisitos": ["green", "gradiente"],
        "teoria": "La circulación de la frontera orientada coincide con el flujo del rotacional a través de una superficie regular orientada, bajo hipótesis de regularidad del campo.",
        "ejemplo": {
            "operacion": "stokes",
            "campo": ["-y/2", "x/2", "0"],
            "superficie": ["u", "v", "0"],
            "limites": [
                {"variable": "u", "inferior": "0", "superior": "1"},
                {"variable": "v", "inferior": "0", "superior": "1"},
            ],
        },
        "ejercicio": {},
        "pregunta": "Calcule el flujo del rotacional del ejemplo con normal hacia +z.",
        "respuesta": "1",
        "pista": "El rotacional es (0,0,1).",
        "tipo": "valor",
    },
    "gauss": {
        "curso": "IV",
        "prerrequisitos": ["integrales_multiples"],
        "teoria": "Para un campo C¹ y volumen con frontera cerrada regular por tramos, el flujo exterior es la integral triple de la divergencia.",
        "ejemplo": {
            "operacion": "gauss",
            "campo": ["x", "y", "z"],
            "limites": [
                {"variable": "z", "inferior": "0", "superior": "1"},
                {"variable": "y", "inferior": "0", "superior": "1"},
                {"variable": "x", "inferior": "0", "superior": "1"},
            ],
        },
        "ejercicio": {},
        "pregunta": "Calcule el flujo exterior de (x,y,z) en el cubo unidad.",
        "respuesta": "3",
        "pista": "La divergencia es 3 y el volumen es 1.",
        "tipo": "valor",
    },
}


def lesson(tema, nivel="desde_cero"):
    if tema not in LESSONS:
        raise EntradaError("Tema no disponible. Consulte catalogo.")
    if nivel not in ("desde_cero", "avanzado"):
        raise EntradaError("Nivel inválido.")
    out = {k: v for k, v in LESSONS[tema].items() if k not in ("respuesta", "tipo")}
    return {
        "tema": tema,
        "nivel": nivel,
        **out,
        "ruta_sugerida": list(LESSONS) if nivel == "desde_cero" else [tema],
    }


def verify(tema, respuesta):
    import sympy as sp
    from sympy.calculus.util import continuous_domain
    from validacion import parse, variable

    if tema not in LESSONS:
        raise EntradaError("Tema desconocido.")
    task = LESSONS[tema]
    expected = parse(task["respuesta"], ("x", "y"))
    actual = parse(
        respuesta,
        ("x",)
        if task["tipo"] == "primitiva"
        else ("x", "y")
        if task["tipo"] == "identidad"
        else (),
    )
    # Exercises in this catalog have full real domains; do not erase holes by simplification.
    if task["tipo"] in ("identidad", "primitiva"):
        # Symbolic domain is checked on the unsimplified syntax as well.
        from validacion import original_domain

        if original_domain(respuesta, "x") != sp.S.Reals:
            return {
                "estado": "no_concluyente",
                "correcta": None,
                "retroalimentacion": "La respuesta introduce restricciones de dominio; revise el intervalo de validez.",
            }
        for v in actual.free_symbols:
            if continuous_domain(actual, v, sp.S.Reals) != sp.S.Reals:
                return {
                    "estado": "no_concluyente",
                    "correcta": None,
                    "retroalimentacion": "No se ha certificado equivalencia en todo el dominio del ejercicio.",
                }
    diff = (
        sp.diff(actual - expected, variable("x"))
        if task["tipo"] == "primitiva"
        else actual - expected
    )
    reduced = sp.simplify(diff)
    ok = (
        True
        if reduced == 0
        else False
        if reduced.is_zero is False or (reduced.is_polynomial() and reduced != 0)
        else None
    )
    return {
        "estado": "verificado" if ok is not None else "no_concluyente",
        "correcta": ok,
        "retroalimentacion": "Correcto para el ejercicio y dominio indicados."
        if ok
        else task["pista"],
        "criterio": "Derivada de la diferencia igual a cero."
        if task["tipo"] == "primitiva"
        else "Equivalencia simbólica, sin tolerancia decimal.",
    }
