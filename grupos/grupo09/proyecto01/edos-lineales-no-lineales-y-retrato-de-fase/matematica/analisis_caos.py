"""Indicadores de caos: sensibilidad, Lyapunov y secciones de Poincaré.

MÓDULO NO IMPLEMENTADO. Responsable según la propuesta: Yanac Minaya Junior
Alberto, con apoyo de Tisnado Yarleque Christian David en la interpretación.

Es un stub deliberado: `estimar_indicadores` levanta `AnalisisNoImplementado`
en vez de devolver números. Un valor inventado de Lyapunov sería peor que la
ausencia del dato, porque el agente lo presentaría como evidencia calculada.

Lo que falta implementar, según la propuesta:

* Comparación de trayectorias cercanas en intervalos cortos.
* Máximo exponente de Lyapunov con perturbación renormalizada y descarte de
  transitorio.
* Cruces de la sección de Poincaré.

Pieza ya disponible para construirlo: `validacion_solucion.verificar_convergencia`
ya detecta y reporta la sensibilidad a condiciones iniciales (`sensibilidad_detectada`,
con el instante en que dos integraciones se separan). Ese es el punto de partida
natural para la estimación de Lyapunov.
"""

from matematica import AnalisisNoImplementado

#: Lo que este módulo ofrecerá cuando esté implementado.
CAPACIDADES_PREVISTAS = ("sensibilidad", "lyapunov", "poincare")


def estimar_indicadores(campo, y0, intervalo, parametros=None, **opciones):
    """Reservado. Levanta AnalisisNoImplementado con el detalle de lo que falta."""
    raise AnalisisNoImplementado(
        "El análisis de caos no está implementado. Faltan: "
        f"{', '.join(CAPACIDADES_PREVISTAS)}. "
        "Mientras tanto, la verificación sí reporta sensibilidad a condiciones "
        "iniciales cuando dos integraciones correctas se separan.")
