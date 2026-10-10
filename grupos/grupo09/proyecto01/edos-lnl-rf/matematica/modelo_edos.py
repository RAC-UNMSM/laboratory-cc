"""Tratamiento numérico de EDOs: validación de la entrada e integración con solve_ivp.

Los integradores de SciPy (RK45, DOP853, Radau, BDF, LSODA) siguen siendo la
herramienta numérica del agente, pero ya no sustituyen al desarrollo
matemático: se usan cuando corresponde, que es

* cuando el problema no pertenece a ninguna familia del balotario (entonces el
  desarrollo es el planteamiento numérico, `desarrollar_numerico`);
* para contrastar una solución analítica o un análisis cualitativo con una
  trayectoria calculada (lo hace `orquestacion.capacidades`).

Absorbe al antiguo `datos_validacion.py`: validar la entrada del integrador es
parte de integrar, y ese módulo no tenía otro usuario.
"""

import math

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from matematica import MAX_DIMENSION
from matematica.analisis_estabilidad import buscar_equilibrios, linealizar
from matematica.desarrollo import Desarrollo, L, punto_latex


def validar_entrada(modelo, y0, intervalo, parametros=None):
    """Valida un modelo, sus condiciones iniciales, intervalo y parámetros."""
    if not callable(modelo):
        raise TypeError("El modelo debe ser una función f(t, y, parametros).")
    if y0 is None:
        raise ValueError("Debe indicar una condición inicial y0.")
    try:
        estado = [float(valor) for valor in y0]
    except (TypeError, ValueError) as exc:
        raise ValueError("y0 debe ser una secuencia de números.") from exc
    if not estado or not all(math.isfinite(valor) for valor in estado):
        raise ValueError("y0 debe tener al menos un valor numérico finito.")
    if len(estado) > MAX_DIMENSION:
        raise ValueError(f"El proyecto admite sistemas de hasta {MAX_DIMENSION} variables.")
    if intervalo is None or len(intervalo) != 2:
        raise ValueError("El intervalo debe tener la forma (t_inicial, t_final).")
    try:
        t0, tf = map(float, intervalo)
    except (TypeError, ValueError) as exc:
        raise ValueError("Los extremos del intervalo deben ser numéricos.") from exc
    if not math.isfinite(t0) or not math.isfinite(tf) or tf <= t0:
        raise ValueError("Se requiere t_final > t_inicial y ambos deben ser finitos.")
    parametros = dict(parametros or {})
    for nombre, valor in parametros.items():
        if not isinstance(nombre, str) or not nombre:
            raise ValueError("Cada parámetro debe tener un nombre de texto.")
        try:
            numero = float(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"El parámetro {nombre!r} debe ser numérico.") from exc
        if not math.isfinite(numero):
            raise ValueError(f"El parámetro {nombre!r} debe ser finito.")
        parametros[nombre] = numero
    return estado, (t0, tf), parametros


def resolver_edo(modelo, y0, intervalo, parametros=None, *, puntos=300,
                 metodo="RK45", rtol=1e-6, atol=1e-9):
    """Resuelve x'=f(t,x,p) y devuelve el objeto estándar de SciPy.

    Ejemplo: resolver_edo(modelo_lineal, [1], (0, 5), {"a": 2})
    El resultado contiene `solucion.t` (tiempos) y `solucion.y` (estados).
    """
    estado, (t0, tf), parametros = validar_entrada(modelo, y0, intervalo, parametros)
    if not isinstance(puntos, int) or puntos < 2:
        raise ValueError("puntos debe ser un entero mayor o igual a 2.")
    if rtol <= 0 or atol <= 0:
        raise ValueError("rtol y atol deben ser positivos.")
    tiempos = np.linspace(t0, tf, puntos)
    try:
        solucion = solve_ivp(
            fun=lambda t, y: modelo(t, y, parametros),
            t_span=(t0, tf), y0=estado, method=metodo, t_eval=tiempos,
            rtol=rtol, atol=atol,
        )
    except Exception as exc:
        raise ValueError(f"No se pudo evaluar el modelo: {exc}") from exc
    if not solucion.success:
        raise RuntimeError(f"Falló la integración: {solucion.message}")
    if solucion.y.shape[0] != len(estado):
        raise ValueError("El modelo debe devolver una derivada por cada variable de estado.")
    return solucion


# ---------------------------------------------------------------------------
# Desarrollo del tratamiento numérico
# ---------------------------------------------------------------------------

def desarrollar_numerico(problema, motivo, fuera_de_alcance=None) -> Desarrollo:
    """Planteamiento de un problema que se resuelve numéricamente.

    No inventa un método analítico: dice por qué no lo hay, escribe el sistema
    de primer orden, las condiciones y, si el sistema es autónomo, el análisis
    local de sus equilibrios (la maquinaria del Tema 2, que vale en cualquier
    dimensión). La solución numérica la agrega después `seccion_solucion_numerica`.
    """
    d = Desarrollo("numerico", "Tratamiento numérico", "Fuera de las familias analíticas del balotario",
                   "Planteamiento del sistema de primer orden e integración numérica con control de error",
                   tratamiento=["numerico"])
    if fuera_de_alcance:
        d.tema = fuera_de_alcance.get("tema") or d.tema
        d.advertir(f"Fuera del alcance del proyecto: {fuera_de_alcance['descripcion']}. "
                   + ("Solo se plantea el mapa: no se itera ni se analiza." if problema.tipo == "mapa" else
                      "Solo se ofrece el tratamiento numérico del sistema."))
    seccion = d.seccion("planteamiento", "Planteamiento")
    seccion.texto(motivo)
    if problema.tipo == "mapa":
        seccion.formula(r",\quad ".join(problema.sistema_latex()))
        return d
    for linea in problema.sistema_latex():
        seccion.formula(linea)
    if problema.ci is not None:
        t0, valores = problema.ci
        condiciones = r",\quad ".join(f"{L(s)}({L(t0)}) = {L(v)}" for s, v in zip(problema.estados, valores))
        seccion.formula(condiciones, destacada=True)
    if problema.intervalo is not None:
        a, b = problema.intervalo
        seccion.formula(rf"{L(problema.x)} \in \left[{a:g},\, {b:g}\right]")
    if problema.autonomo and problema.dimension >= 2:
        _equilibrios_generales(d, problema)
    return d


def _equilibrios_generales(d, problema):
    campo = problema.campo_con()
    try:
        equilibrios, informe = buscar_equilibrios(campo, problema.estados, region=problema.region)
    except Exception:
        return
    if not equilibrios:
        return
    seccion = d.seccion("equilibrios", "Equilibrios y linealización")
    J = sp.Matrix(campo).jacobian(problema.estados)
    clasificados = []
    for i, e in enumerate(equilibrios, 1):
        lin = linealizar(campo, problema.estados, e.punto, matriz_general=J, con_vectores=False)
        if not lin.definida:
            continue
        valores = r",\; ".join(L(sp.nsimplify(v, tolerance=1e-10) if not isinstance(v, sp.Float) else v)
                               for v in lin.autovalores)
        seccion.formula(rf"P_{{{i}}} = {punto_latex(e.punto)}:\quad \lambda = {valores}",
                        r"\implies", rf"\text{{{lin.tipo} ({lin.estabilidad})}}", destacada=True)
        clasificados.append(lin)
    d.guardar("equilibrios", clasificados)


def seccion_solucion_numerica(d, solucion, problema, metodo, rtol, atol, recortado=None):
    """Resumen de la integración: método, tolerancias, malla y estado final."""
    seccion = d.seccion("solucion_numerica", "Solución numérica")
    seccion.formula(rf"\text{{Integrador {metodo}}},\quad \mathrm{{rtol}} = {L(rtol)},\quad "
                    rf"\mathrm{{atol}} = {L(atol)},\quad {solucion.t.size}\ \text{{puntos}}")
    if recortado is not None:
        seccion.texto(recortado)
    final = solucion.y[:, -1]
    seccion.formula(r",\quad ".join(rf"{L(s)}({float(solucion.t[-1]):.6g}) \approx {v:.8g}"
                                    for s, v in zip(problema.estados, final)), destacada=True,
                    ref="estado_final")
    d.guardar("estado_final", {s.name: float(v) for s, v in zip(problema.estados, final)})
    if "numerico" not in d.tratamiento:
        d.tratamiento.append("numerico")
