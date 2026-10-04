"""Capa matemática del agente de EDOs: compilación, integración y análisis.

No depende de `orquestacion` ni de MCP, de modo que cada pieza se pueda usar y
probar por separado.
"""


class AnalisisNoImplementado(NotImplementedError):
    """Un análisis previsto por la propuesta que todavía no se calcula.

    Vive aquí, y no en cada stub, porque `orquestacion.capacidades` necesita
    atrapar una sola excepción para reportar "pendiente de implementación" en
    vez de inventar números. Tres clases con el mismo nombre en tres módulos
    distintos daban la ilusión de un tipo compartido que no existía.
    """


#: Tope de variables de estado, heredado de la propuesta del grupo. Es el único
#: lugar donde vive el número: `datos_validacion` lo aplica al entrar al solver
#: y `orquestacion.contratos` al validar la solicitud.
MAX_DIMENSION = 3
