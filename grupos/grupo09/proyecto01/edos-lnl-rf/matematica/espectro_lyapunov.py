"""Espectro de exponentes de Lyapunov de un flujo o de un mapa, por el método QR.

Lo usan el 4.5 (el teorema del espectro (+, 0, −) se contrasta con Lorenz y
Rössler), el 5.3 (exponentes del atractor de Hénon), el 5.4 (la contracción
transversal e^{λ₃T} de Rössler) y el 5.5 (la dimensión de Kaplan-Yorke).

El método (Benettin et al., 1980; Shimada y Nagashima, 1979): se integra la
órbita junto con la ecuación variacional Q' = Df(x(t))·Q y cada pocos pasos se
reortonormaliza Q = Q̃R. Los logaritmos de la diagonal de R, acumulados y
divididos por el tiempo, convergen a λ₁ ≥ λ₂ ≥ ... ≥ λₙ. Sin la
reortonormalización todas las columnas se alinearían con la dirección más
expansiva y solo se vería λ₁.

Por qué un RK4 de paso fijo y no `solve_ivp`: la QR se hace a intervalos fijos
y el sistema extendido (n + n² ecuaciones) es pequeño; un paso fijo elegido
por la escala del jacobiano es exacto de sobra para un promedio de miles de
unidades de tiempo, y unas diez veces más rápido.

Dos comprobaciones salen gratis y se devuelven: la suma de los exponentes debe
coincidir con la divergencia media a lo largo de la misma órbita (fórmula de
Liouville), y en un flujo uno de los exponentes debe ser ≈ 0 (la dirección del
propio flujo).
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from matematica import MetodoNoAplicable

#: Tiempo que se promedia en un flujo, con un mínimo y un máximo de pasos de
#: RK4, y cada cuántos pasos se reortonormaliza. El exponente pequeño de
#: Rössler (λ₁ ≈ 0.07) necesita del orden de mil unidades de tiempo para que su
#: error baje de ±0.005.
DURACION_FLUJO = 1500.0
PASOS_MINIMOS, PASOS_MAXIMOS = 30_000, 90_000
CADA_QR = 10

#: Iteraciones de un mapa (más el transitorio).
ITERACIONES_MAPA = 30_000
TRANSITORIO_MAPA = 1_000

#: Bloques en que se parte el promedio para estimar su error.
BLOQUES = 10

#: Norma a partir de la cual se considera que la órbita escapa.
ESCAPE = 1e6


@dataclass
class Espectro:
    """Lo que se midió: exponentes ordenados, su error y las comprobaciones."""

    exponentes: list
    errores: list
    divergencia_media: float
    duracion: float
    paso: float | None = None
    norma_minima: float | None = None
    norma_maxima: float | None = None
    historia_t: list = field(default_factory=list)
    historia: list = field(default_factory=list)          # [[λ₁(t), λ₂(t), ...], ...]
    orbita: list = field(default_factory=list)             # puntos submuestreados
    estado_final: list = field(default_factory=list)

    @property
    def suma(self) -> float:
        return float(sum(self.exponentes))

    @property
    def indice_neutro(self) -> int:
        """El exponente más cercano a cero: la dirección del flujo."""
        return int(np.argmin(np.abs(self.exponentes)))


def _funciones(campo, estados):
    f = sp.lambdify([estados], list(campo), "numpy")
    J = sp.lambdify([estados], sp.Matrix(campo).jacobian(estados).tolist(), "numpy")
    return (lambda e: np.asarray(f(e), dtype=float)), (lambda e: np.asarray(J(e), dtype=float))


@functools.lru_cache(maxsize=16)
def _espectro_flujo(clave_campo, nombres, x0, duracion_objetivo):
    estados = sp.symbols(nombres, real=True)
    campo = [sp.sympify(e, locals=dict(zip(nombres, estados))) for e in clave_campo]
    f, J = _funciones(campo, estados)
    n = len(estados)

    # Transitorio con un integrador adaptativo: lleva la órbita al atractor y
    # muestrea el jacobiano para elegir el paso fijo.
    previo = solve_ivp(lambda t, e: f(e), (0.0, 60.0), list(x0), method="LSODA",
                       rtol=1e-8, atol=1e-10, dense_output=False, max_step=0.5)
    if not previo.success or not np.all(np.isfinite(previo.y)) or np.abs(previo.y).max() > ESCAPE:
        raise MetodoNoAplicable("La trayectoria no permanece acotada: no hay un atractor sobre el cual "
                                "promediar los exponentes de Lyapunov.")
    radios = [max(abs(np.linalg.eigvals(J(previo.y[:, k])))) for k in
              range(previo.y.shape[1] // 2, previo.y.shape[1], max(1, previo.y.shape[1] // 200))]
    paso = float(np.clip(0.35 / max(max(radios), 1e-9), 0.002, 0.05))
    pasos = int(np.clip(duracion_objetivo / paso, PASOS_MINIMOS, PASOS_MAXIMOS)) // CADA_QR * CADA_QR

    def rk4(e, Q):
        k1, J1 = f(e), J(e)
        K1 = J1 @ Q
        e2 = e + paso / 2 * k1
        k2, K2 = f(e2), J(e2) @ (Q + paso / 2 * K1)
        e3 = e + paso / 2 * k2
        k3, K3 = f(e3), J(e3) @ (Q + paso / 2 * K2)
        e4 = e + paso * k3
        k4, K4 = f(e4), J(e4) @ (Q + paso * K3)
        return (e + paso / 6 * (k1 + 2 * k2 + 2 * k3 + k4), Q + paso / 6 * (K1 + 2 * K2 + 2 * K3 + K4),
                float(np.trace(J1)), float(np.linalg.norm(k1)))

    estado = previo.y[:, -1].copy()
    Q = np.eye(n)
    # Un transitorio más corto con QR para alinear las columnas con las direcciones de Oseledets.
    for k in range(pasos // 10):
        estado, Q, _, _ = rk4(estado, Q)
        if (k + 1) % CADA_QR == 0:
            Q, _ = np.linalg.qr(Q)

    sumas = np.zeros(n)
    por_bloque = np.zeros((BLOQUES, n))
    tamano_bloque = pasos // BLOQUES
    traza = 0.0
    norma_min, norma_max = math.inf, 0.0
    historia_t, historia, orbita = [], [], []
    cada_orbita = max(1, pasos // 3000)
    cada_historia = max(CADA_QR, (pasos // 400) // CADA_QR * CADA_QR)
    for k in range(pasos):
        estado, Q, tr, norma = rk4(estado, Q)
        traza += tr * paso
        norma_min, norma_max = min(norma_min, norma), max(norma_max, norma)
        if (k + 1) % CADA_QR == 0:
            Q, R = np.linalg.qr(Q)
            signos = np.sign(np.diag(R))
            signos[signos == 0] = 1
            Q = Q * signos
            logs = np.log(np.abs(np.diag(R)))
            sumas += logs
            por_bloque[min(k // tamano_bloque, BLOQUES - 1)] += logs
            if (k + 1) % cada_historia == 0:
                historia_t.append((k + 1) * paso)
                historia.append((sumas / ((k + 1) * paso)).tolist())
        if k % cada_orbita == 0:
            orbita.append(estado.tolist())
        if not np.all(np.isfinite(estado)) or np.abs(estado).max() > ESCAPE:
            raise MetodoNoAplicable("La trayectoria escapó durante el cálculo del espectro.")
    duracion = pasos * paso
    exponentes = sumas / duracion
    bloques = por_bloque / (tamano_bloque * paso)
    errores = bloques.std(axis=0, ddof=1) / math.sqrt(BLOQUES)
    orden = np.argsort(-exponentes)
    return Espectro(exponentes=[float(v) for v in exponentes[orden]],
                    errores=[float(v) for v in errores[orden]],
                    divergencia_media=traza / duracion, duracion=duracion, paso=paso,
                    norma_minima=norma_min, norma_maxima=norma_max, historia_t=historia_t,
                    historia=[[fila[i] for i in orden] for fila in historia], orbita=orbita,
                    estado_final=estado.tolist())


def espectro_flujo(campo, estados, x0=None, duracion=DURACION_FLUJO) -> Espectro:
    """Espectro de un flujo autónomo x' = f(x) a lo largo de la órbita que parte de x0."""
    nombres = tuple(s.name for s in estados)
    if x0 is None:
        x0 = tuple(1.0 if i == 0 else 1.0 / (i + 1) for i in range(len(estados)))
    clave = tuple(sp.sstr(sp.sympify(e)) for e in campo)
    return _espectro_flujo(clave, nombres, tuple(float(v) for v in x0), float(duracion))


@functools.lru_cache(maxsize=16)
def _espectro_mapa(clave_campo, nombres, x0, iteraciones):
    estados = sp.symbols(nombres, real=True)
    campo = [sp.sympify(e, locals=dict(zip(nombres, estados))) for e in clave_campo]
    f, J = _funciones(campo, estados)
    n = len(estados)
    estado = np.array(x0, dtype=float)
    for _ in range(TRANSITORIO_MAPA):
        estado = f(estado)
        if not np.all(np.isfinite(estado)) or np.abs(estado).max() > ESCAPE:
            raise MetodoNoAplicable("La órbita del mapa escapa al infinito: no hay atractor acotado para "
                                    "esos valores de los parámetros o esa condición inicial.")
    Q = np.eye(n)
    sumas = np.zeros(n)
    por_bloque = np.zeros((BLOQUES, n))
    tamano = iteraciones // BLOQUES
    log_det = 0.0
    orbita, historia_t, historia = [], [], []
    for k in range(iteraciones):
        Jk = J(estado)
        determinante = abs(np.linalg.det(Jk))
        Q, R = np.linalg.qr(Jk @ Q)
        signos = np.sign(np.diag(R))
        signos[signos == 0] = 1
        Q = Q * signos
        diagonal = np.abs(np.diag(R))
        if determinante == 0 or np.any(diagonal == 0):
            # La órbita pasa por un punto donde DT es singular: una dirección se
            # aplasta del todo y su exponente es −∞. No hay nada más que promediar.
            exponentes = sorted((sumas / max(k, 1)).tolist(), reverse=True)
            exponentes[-1] = -math.inf
            return Espectro(exponentes=exponentes, errores=[0.0] * n, divergencia_media=-math.inf,
                            duracion=float(k + 1), orbita=orbita, estado_final=estado.tolist())
        log_det += math.log(determinante)
        logs = np.log(diagonal)
        sumas += logs
        por_bloque[min(k // tamano, BLOQUES - 1)] += logs
        estado = f(estado)
        if not np.all(np.isfinite(estado)) or np.abs(estado).max() > ESCAPE:
            raise MetodoNoAplicable("La órbita del mapa escapa al infinito durante el cálculo.")
        if k < 20_000:
            orbita.append(estado.tolist())
        if (k + 1) % max(1, iteraciones // 300) == 0:
            historia_t.append(k + 1)
            historia.append((sumas / (k + 1)).tolist())
    exponentes = sumas / iteraciones
    errores = (por_bloque / tamano).std(axis=0, ddof=1) / math.sqrt(BLOQUES)
    orden = np.argsort(-exponentes)
    return Espectro(exponentes=[float(v) for v in exponentes[orden]],
                    errores=[float(v) for v in errores[orden]],
                    divergencia_media=log_det / iteraciones, duracion=float(iteraciones),
                    historia_t=historia_t, historia=[[fila[i] for i in orden] for fila in historia],
                    orbita=orbita, estado_final=estado.tolist())


def espectro_mapa(campo, estados, x0=None, iteraciones=ITERACIONES_MAPA) -> Espectro:
    """Espectro de un mapa x_{n+1} = F(x_n). `divergencia_media` es ⟨ln|det DF|⟩."""
    nombres = tuple(s.name for s in estados)
    if x0 is None:
        x0 = tuple(0.1 for _ in estados)
    clave = tuple(sp.sstr(sp.sympify(e)) for e in campo)
    return _espectro_mapa(clave, nombres, tuple(float(v) for v in x0), int(iteraciones))
