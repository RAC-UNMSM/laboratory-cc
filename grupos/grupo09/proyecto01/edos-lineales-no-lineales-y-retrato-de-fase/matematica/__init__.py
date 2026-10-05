"""Capa matemática del agente de EDOs: interpretación, métodos, análisis y verificación.

No depende de `orquestacion` ni de MCP, de modo que cada pieza se pueda usar y
probar por separado. Las familias de problemas que resuelve son exactamente las
que el balotario del grupo desarrolla (Temas 1 a 3 y el problema 4.1); el resto
se declara fuera de alcance con `FueraDeAlcance`, en vez de inventarse.
"""


class FueraDeAlcance(Exception):
    """Lo pedido corresponde a un tema que el balotario todavía no desarrolla.

    Lleva la referencia al problema del balotario (`problema`, p. ej. "4.4") y
    el `motivo`, para que la respuesta pueda decir con precisión qué falta en
    lugar de ofrecer un sustituto con apariencia de solución.
    """

    def __init__(self, motivo, problema=None, tema=None):
        super().__init__(motivo)
        self.motivo = motivo
        self.problema = problema
        self.tema = tema


class MetodoNoAplicable(ValueError):
    """El método pedido no corresponde a la forma de la ecuación.

    Por ejemplo, pedir Bernoulli para y' = sin(x·y). El mensaje dice qué forma
    se esperaba y cuál tiene la ecuación, para que el agente lo explique.
    """


#: Tope de variables de estado, heredado de la propuesta del grupo. Es el único
#: lugar donde vive el número: `modelo_edos` lo aplica al entrar al solver y
#: `orquestacion.contratos` al validar la solicitud.
MAX_DIMENSION = 3
