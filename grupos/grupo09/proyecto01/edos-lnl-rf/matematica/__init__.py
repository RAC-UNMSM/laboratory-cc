"""Capa matemática del agente de EDOs: interpretación, métodos, análisis y verificación.

No depende de `orquestacion` ni de MCP, de modo que cada pieza se pueda usar y
probar por separado. Las familias de problemas que resuelve son exactamente las
que el balotario del grupo desarrolla (los cinco temas, 25 problemas). Lo que
cae fuera de esos temas se declara con `FueraDeAlcance`, en vez de inventarse.
"""


class FueraDeAlcance(Exception):
    """Lo pedido no pertenece a ninguno de los temas que el proyecto trabaja.

    Lleva el `motivo` (y, si viene al caso, el `tema` o el `problema` más
    cercano), para que la respuesta diga con precisión por qué no se resuelve
    en lugar de ofrecer un sustituto con apariencia de solución.
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


class DatoInvalido(ValueError):
    """Un dato del problema hace imposible el cálculo que se pide.

    Por ejemplo r₂ ≤ r₁ en la estimación de Feigenbaum, una razón de semejanza
    fuera de (0, 1) o b = 0 en el inverso de Hénon. No es un fallo del método:
    el mensaje dice qué valor está mal y qué rango se esperaba, para que el
    usuario lo corrija.
    """


#: Tope de variables de estado, heredado de la propuesta del grupo. Es el único
#: lugar donde vive el número: `modelo_edos` lo aplica al entrar al solver y
#: `orquestacion.contratos` al validar la solicitud.
MAX_DIMENSION = 3
