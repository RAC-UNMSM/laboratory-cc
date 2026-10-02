"""
analisis_bifurcaciones.py
=========================

Responsable: Tisnado Yarleque Christian David (Matemático II - Estabilidad y
bifurcaciones), según "Grupo_09_Propuesta_actualizada.md".

QUÉ HACE
--------
Para un sistema autónomo x' = F(x; theta) de 1 a 3 variables y UN parámetro
numérico `p` que se hace variar en [p_min, p_max]:

    1. Barrido paramétrico       -> lista de valores de p (rejilla uniforme).
    2. Ramas de equilibrio       -> para cada p, todos los x* con F(x*; p) = 0
                                    hallados dentro de una región de búsqueda.
    3. Estabilidad local         -> Jacobiano y autovalores de cada x*
                                    (reutiliza `analizar_equilibrios` de
                                    analisis_estabilidad.py).
    4. Candidatos a bifurcación  -> cambios del número de equilibrios o de su
                                    estabilidad entre valores consecutivos de p,
                                    refinados por bisección.
    5. Máximos locales (opcional)-> para cada p se integra con `resolver_edo`
                                    (modelo_edos.py), se descarta un transitorio
                                    y se registran los máximos de una variable.
    6. Contraste con teoría      -> SOLO para las formas normales registradas
                                    (silla-nodo, horquilla, Hopf), donde el valor
                                    crítico es conocido analíticamente.

QUÉ NO AFIRMA (honestidad sobre la evidencia)
---------------------------------------------
Un barrido numérico solo da INDICIOS. Cada candidato se marca con
`evidencia = "numerica"` y `confirmado_matematicamente = False`; el "tipo
sugerido" es una hipótesis heurística. Solo en las formas normales de
`FORMAS_NORMALES` se compara el candidato con el valor crítico teórico conocido
y, aun así, eso es una verificación numérica de un caso de referencia, no una
demostración para un sistema general.
Limitaciones conocidas:
    - Solo se hallan equilibrios dentro de `region_busqueda` y con las
      semillas usadas: pueden faltar equilibrios fuera de la región, o
      equilibrios muy próximos entre sí (p. ej. un par que nace en un
      punto de silla-nodo con separación menor que la resolución).
    - En el valor exacto de una bifurcación el equilibrio es no hiperbólico y
      la raíz puede no detectarse; por eso el candidato se informa como un
      INTERVALO [p_inf, p_sup] y no como un valor exacto.
    - Los máximos locales dependen de la condición inicial, del transitorio
      descartado y de la resolución temporal; todo ello se guarda en `config`.

INTERFAZ (contrato del grupo: f(t, y, parametros) como en modelos_referencia.py)
-------------------------------------------------------------------------------
    resultado = analizar_bifurcaciones(
        modelo,                      # f(t, y, parametros) -> lista de derivadas
        parametros={"mu": 0.0},      # DEBE contener al parámetro variado
        parametro="mu",
        rango=(-1.0, 1.0),
        n_valores=21,
        region_busqueda=[(-3, 3)],   # (min, max) por variable de estado
    )
    imprimir_reporte_bifurcaciones(resultado)

    resultado = ejecutar_forma_normal("hopf")   # caso de referencia completo

Devuelve siempre un diccionario; si algo es inválido: {"valid": False,
"reason": ..., "message": ..., "stage": ...} (mismo estilo que
analisis_estabilidad.py). Los datos para dibujar (`diagrama_equilibrio`,
`diagrama_maximos`) son estructuras simples que `visualizacion.py` puede
consumir; este módulo NO dibuja nada.
"""

from __future__ import annotations

import math
import textwrap
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import brentq, root

from analisis_estabilidad import (
    ANCHO_CONSOLA,
    analizar_equilibrios,
    campo_consola,
    formatear_complejo,
    formatear_error_consola,
    separador_consola,
    titulo_consola,
    _tabla,
)
from modelo_edos import resolver_edo

# ---------------------------------------------------------------------------
# 1. CONSTANTES
# ---------------------------------------------------------------------------

RAZONES = {
    "invalid_input": "La configuración del barrido no tiene el formato requerido.",
    "invalid_dimension": "Se admiten sistemas de 1 a 3 variables de estado.",
    "invalid_parameter": "El parámetro a variar no es válido para este modelo.",
    "invalid_range": "El rango del parámetro o la cantidad de valores no es válida.",
    "non_autonomous_system": "El sistema depende explícitamente de t; el barrido de equilibrios requiere un sistema autónomo.",
    "model_evaluation_error": "No se pudo evaluar el modelo en la región de búsqueda.",
    "incomplete_results": "El barrido no produjo resultados utilizables.",
    "unknown_case": "Caso de referencia desconocido.",
}

MAX_VALORES = 400          # tope de valores del parámetro en el barrido de equilibrios
MAX_VALORES_MAXIMOS = 60   # tope de valores del parámetro para integrar trayectorias
_ETIQUETA_ESTAB = ("estable", "inestable", "no concluyente")


class ContinuoDeEquilibrios(Exception):
    """F se anula en una región extensa (p. ej. F identicamente 0): no hay equilibrios aislados."""


class ErrorBifurcaciones(Exception):
    """Error estructurado (qué pasó, en qué etapa, qué falta)."""

    def __init__(self, reason: str, message: Optional[str] = None, stage: str = "validacion",
                 missing: Optional[str] = None):
        self.reason = reason
        self.message = message or RAZONES.get(reason, "Error no especificado.")
        self.stage = stage
        self.missing = missing
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {"analysis": "bifurcations", "valid": False, "reason": self.reason,
                "message": self.message, "stage": self.stage, "can_continue": False,
                "missing": self.missing}


# ---------------------------------------------------------------------------
# 2. VALIDACIÓN DE LA CONFIGURACIÓN
# ---------------------------------------------------------------------------

def _numero_finito(valor: Any, nombre: str) -> float:
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise ErrorBifurcaciones("invalid_input", f"{nombre} debe ser numérico (recibido: {valor!r}).")
    if not math.isfinite(x):
        raise ErrorBifurcaciones("invalid_input", f"{nombre} debe ser finito (recibido: {valor!r}).")
    return x


def _evaluar(modelo: Callable, estado: np.ndarray, parametros: Dict[str, float], n: int) -> np.ndarray:
    """Evalúa F(x) (t=0) validando forma y finitud."""
    try:
        valor = np.asarray(modelo(0.0, list(estado), parametros), dtype=float)
    except Exception as exc:  # el modelo es código del usuario/otro módulo
        raise ErrorBifurcaciones("model_evaluation_error",
                                 f"El modelo falló en x = {np.round(estado, 6).tolist()}: {exc}", stage="evaluacion")
    if valor.shape != (n,):
        raise ErrorBifurcaciones("model_evaluation_error",
                                 f"El modelo debe devolver {n} derivada(s) y devolvió forma {valor.shape}.",
                                 stage="evaluacion")
    return valor


def validar_configuracion_barrido(modelo, parametros, parametro, rango, n_valores,
                                  region_busqueda) -> Dict[str, Any]:
    """
    Valida la configuración y la devuelve normalizada. Lanza `ErrorBifurcaciones`.

    Comprobaciones: modelo invocable, dimensión 1-3, parámetro numérico presente
    y realmente usado por el modelo, rango (p_min < p_max, finito), cantidad de
    valores, región de búsqueda y autonomía del sistema (sin dependencia de t).
    """
    if not callable(modelo):
        raise ErrorBifurcaciones("invalid_input", "El modelo debe ser una función f(t, y, parametros).")
    if region_busqueda is None:
        raise ErrorBifurcaciones("invalid_input", "Falta la región de búsqueda de equilibrios.",
                                 missing="region_busqueda")
    try:
        region = [(float(a), float(b)) for a, b in region_busqueda]
    except (TypeError, ValueError):
        raise ErrorBifurcaciones("invalid_input", "region_busqueda debe ser una lista de pares (min, max).")
    n = len(region)
    if n < 1 or n > 3:
        raise ErrorBifurcaciones("invalid_dimension", f"Se recibieron {n} variables; se admiten de 1 a 3.")
    for k, (a, b) in enumerate(region):
        if not (math.isfinite(a) and math.isfinite(b) and a < b):
            raise ErrorBifurcaciones("invalid_input", f"La región de la variable {k + 1} requiere min < max finitos.")

    if not isinstance(parametro, str) or not parametro:
        raise ErrorBifurcaciones("invalid_parameter", "El nombre del parámetro debe ser un texto no vacío.",
                                 missing="parametro")
    if not isinstance(parametros, dict) or parametro not in parametros:
        raise ErrorBifurcaciones("invalid_parameter",
                                 f"El parámetro {parametro!r} debe estar declarado en `parametros` "
                                 "(con un valor base numérico).", missing="parametros")
    base = {}
    for nombre, valor in parametros.items():
        base[nombre] = _numero_finito(valor, f"El parámetro {nombre!r}")

    try:
        p_min, p_max = rango
    except (TypeError, ValueError):
        raise ErrorBifurcaciones("invalid_range", "El rango debe ser un par (p_min, p_max).", missing="rango")
    p_min, p_max = _numero_finito(p_min, "p_min"), _numero_finito(p_max, "p_max")
    if p_min >= p_max:
        raise ErrorBifurcaciones("invalid_range", f"Se requiere p_min < p_max (recibido: {p_min}, {p_max}).")
    if isinstance(n_valores, bool) or not isinstance(n_valores, int) or n_valores < 3:
        raise ErrorBifurcaciones("invalid_range", "n_valores debe ser un entero >= 3.")
    if n_valores > MAX_VALORES:
        raise ErrorBifurcaciones("invalid_range", f"n_valores no puede superar {MAX_VALORES}.")

    # Autonomía y uso del parámetro, con puntos de prueba deterministas.
    rng = np.random.RandomState(12345)
    puntos = [np.array([a + (b - a) * u for (a, b), u in zip(region, rng.uniform(0.15, 0.85, n))])
              for _ in range(5)]
    for x in puntos:
        f0 = _evaluar(modelo, x, base, n)
        try:
            f1 = np.asarray(modelo(1.7, list(x), base), dtype=float)
            f2 = np.asarray(modelo(-3.1, list(x), base), dtype=float)
        except Exception as exc:
            raise ErrorBifurcaciones("model_evaluation_error", f"El modelo falló al variar t: {exc}", stage="evaluacion")
        escala = 1.0 + np.max(np.abs(f0))
        if np.max(np.abs(f1 - f0)) > 1e-9 * escala or np.max(np.abs(f2 - f0)) > 1e-9 * escala:
            raise ErrorBifurcaciones("non_autonomous_system")
    # Se compara F en varios valores del parámetro (no solo en los extremos: un modelo
    # simétrico en el parámetro, como mu^2 + 1 en [-1, 1], coincidiría en ambos).
    usa_parametro = False
    valores_prueba = [p_min + (p_max - p_min) * u for u in (0.0, 0.17, 0.5, 0.83, 1.0)]
    for x in puntos:
        ref = _evaluar(modelo, x, {**base, parametro: valores_prueba[0]}, n)
        for v in valores_prueba[1:]:
            otro = _evaluar(modelo, x, {**base, parametro: v}, n)
            if np.max(np.abs(otro - ref)) > 1e-12 * (1.0 + np.max(np.abs(ref))):
                usa_parametro = True
                break
        if usa_parametro:
            break
    if not usa_parametro:
        raise ErrorBifurcaciones("invalid_parameter",
                                 f"El modelo no cambia al variar {parametro!r}; no hay nada que barrer.")
    return {"region": region, "n": n, "base": base, "rango": (p_min, p_max)}


# ---------------------------------------------------------------------------
# 3. EQUILIBRIOS PARA UN VALOR DEL PARÁMETRO
# ---------------------------------------------------------------------------

def _deduplicar(puntos: List[np.ndarray], tol: float) -> List[np.ndarray]:
    unicos: List[np.ndarray] = []
    for p in sorted(puntos, key=lambda v: tuple(v)):
        if not any(np.max(np.abs(p - q)) <= tol for q in unicos):
            unicos.append(p)
    return unicos


def buscar_equilibrios(modelo, parametros: Dict[str, float], region: Sequence[Tuple[float, float]],
                       semillas_por_dim: Optional[int] = None, tol_residuo: float = 1e-9,
                       n_escaneo_1d: int = 801) -> List[np.ndarray]:
    """
    Equilibrios F(x)=0 dentro de `region`.

    1D: escaneo de signo de F en `n_escaneo_1d` puntos + Brent (robusto).
    2D/3D: Newton híbrido (`scipy.optimize.root`) desde una rejilla de semillas.
    Todo candidato se verifica con |F|_inf <= tol_residuo y se deduplica.
    """
    n = len(region)
    escala = max(b - a for a, b in region)
    hallados: List[np.ndarray] = []

    def F(x):
        return np.asarray(modelo(0.0, list(np.atleast_1d(x)), parametros), dtype=float)

    if n == 1:
        a, b = region[0]
        xs = np.linspace(a, b, n_escaneo_1d)
        fs = np.array([F(x)[0] for x in xs])
        if np.count_nonzero(np.isfinite(fs) & (np.abs(fs) <= tol_residuo)) >= 5:
            raise ContinuoDeEquilibrios()
        for i in range(len(xs)):
            if np.isfinite(fs[i]) and abs(fs[i]) <= tol_residuo:
                hallados.append(np.array([xs[i]]))
            if i + 1 < len(xs) and np.isfinite(fs[i]) and np.isfinite(fs[i + 1]) and fs[i] * fs[i + 1] < 0:
                raiz = brentq(lambda x: F(x)[0], xs[i], xs[i + 1], xtol=1e-14, rtol=1e-14, maxiter=200)
                hallados.append(np.array([raiz]))
    else:
        m = semillas_por_dim or (9 if n == 2 else 5)
        ejes = [np.linspace(a, b, m) for a, b in region]
        for semilla in np.array(np.meshgrid(*ejes, indexing="ij")).reshape(n, -1).T:
            try:
                sol = root(F, semilla, method="hybr", tol=1e-13)
            except Exception:
                continue
            x = np.asarray(sol.x, dtype=float)
            if not sol.success or not np.all(np.isfinite(x)):
                continue
            if any(not (a - 1e-9 <= xi <= b + 1e-9) for xi, (a, b) in zip(x, region)):
                continue
            if np.max(np.abs(F(x))) <= tol_residuo:
                hallados.append(x)
    verificados = [x for x in hallados if np.max(np.abs(F(x))) <= max(tol_residuo, 1e-12)]
    unicos = _deduplicar(verificados, 1e-6 * max(1.0, escala))
    if len(unicos) > 60:   # tantos "equilibrios" distintos indican una variedad continua de equilibrios
        raise ContinuoDeEquilibrios()
    return unicos


def _clasificar_punto(modelo, equilibrios, parametros, tol_estab):
    """Estabilidad de cada equilibrio con el módulo de estabilidad (contrato numérico)."""
    if not equilibrios:
        return []
    salida = []
    for r in analizar_equilibrios(modelo, [e.tolist() for e in equilibrios], parametros, tol_estab):
        etiqueta = r["clasificacion"].split(" (")[0]
        salida.append({
            "punto": [float(v) for v in r["equilibrio"]],
            "estabilidad": etiqueta,
            "autovalores": [complex(z) for z in r["autovalores"]],
            "max_re": float(np.max(np.real(r["autovalores"]))),
        })
    return salida


#: Marcador de un valor del parámetro donde F se anula en un continuo (caso degenerado).
MARCA_CONTINUO = {"punto": [], "estabilidad": "continuo", "autovalores": [], "max_re": float("nan")}


def _estado_en(modelo, base, parametro, valor, region, cfg) -> List[Dict[str, Any]]:
    params = {**base, parametro: float(valor)}
    try:
        eqs = buscar_equilibrios(modelo, params, region, cfg["semillas_por_dim"], cfg["tol_residuo"])
    except ContinuoDeEquilibrios:
        return [dict(MARCA_CONTINUO)]
    return _clasificar_punto(modelo, eqs, params, cfg["tol_estabilidad"])


def _es_continuo(estado: List[Dict[str, Any]]) -> bool:
    return any(e["estabilidad"] == "continuo" for e in estado)


# ---------------------------------------------------------------------------
# 4. CANDIDATOS A BIFURCACIÓN
# ---------------------------------------------------------------------------

def _firma(equilibrios: List[Dict[str, Any]]) -> Tuple[int, int, int, int]:
    """(nº equilibrios, nº estables, nº inestables, nº no concluyentes)."""
    return (len(equilibrios),
            sum(e["estabilidad"] == "estable" for e in equilibrios),
            sum(e["estabilidad"] == "inestable" for e in equilibrios),
            sum(e["estabilidad"] in ("no concluyente", "continuo") for e in equilibrios))


def _emparejar(a: List[Dict[str, Any]], b: List[Dict[str, Any]], umbral: float):
    """Emparejamiento uno a uno por cercanía. Devuelve (pares, sin_pareja_a, sin_pareja_b)."""
    candidatos = sorted(
        ((float(np.linalg.norm(np.array(x["punto"]) - np.array(y["punto"]))), i, j)
         for i, x in enumerate(a) for j, y in enumerate(b)), key=lambda t: t[0])
    usados_a, usados_b, pares = set(), set(), []
    for d, i, j in candidatos:
        if d <= umbral and i not in usados_a and j not in usados_b:
            pares.append((i, j)); usados_a.add(i); usados_b.add(j)
    return (pares, [i for i in range(len(a)) if i not in usados_a],
            [j for j in range(len(b)) if j not in usados_b])


def _describir_cambio(ea, eb, umbral) -> Dict[str, Any]:
    """Qué cambia entre dos estados consecutivos y qué tipo de bifurcación sugiere (hipótesis)."""
    if _es_continuo(ea) or _es_continuo(eb):
        return {"hechos": ["en uno de los extremos F se anula en todo un continuo (caso degenerado)"],
                "tipo_sugerido": "caso degenerado: F idénticamente nula para ese valor del parámetro",
                "razon": "no hay equilibrios aislados en ese valor; no se clasifica el cambio"}
    pares, perdidos, nuevos = _emparejar(ea, eb, umbral)
    cambios_estab = [(ea[i], eb[j]) for i, j in pares if ea[i]["estabilidad"] != eb[j]["estabilidad"]]
    complejo = any(abs(z.imag) > 1e-6 for x, y in cambios_estab for z in (x["autovalores"] + y["autovalores"]))
    hechos, tipo, razon = [], "cambio no clasificado", ""
    if nuevos or perdidos:
        hechos.append(f"se pierden {len(perdidos)} equilibrio(s) y aparecen {len(nuevos)}")
    for x, y in cambios_estab:
        punto = ", ".join(f"{v:.4f}" for v in x["punto"])
        hechos.append(f"el equilibrio en ({punto}) pasa de {x['estabilidad']} a {y['estabilidad']}")
    if len(nuevos) + len(perdidos) == 2 and not cambios_estab:
        tipo = "posible silla-nodo (fold): nacimiento/colisión de un par de equilibrios"
        razon = "un par de equilibrios aparece o desaparece sin que otra rama cambie de estabilidad"
    elif len(nuevos) + len(perdidos) >= 2 and cambios_estab:
        tipo = "posible horquilla (pitchfork): nacen/mueren ramas junto a un cambio de estabilidad de una rama continua"
        razon = "aparecen o desaparecen ramas y una rama continua cambia de estabilidad"
    elif cambios_estab and complejo:
        tipo = "posible Hopf: un par de autovalores complejos conjugados cruza el eje imaginario"
        razon = "cambia la estabilidad de un equilibrio con autovalores complejos y sin cambio en el número de equilibrios"
    elif cambios_estab:
        tipo = "posible transcrítica u horquilla: un autovalor real cruza 0 en una rama continua"
        razon = "cambia la estabilidad de una rama continua con autovalor real"
    elif nuevos or perdidos:
        tipo = "cambio en el número de equilibrios (sin clasificar)"
        razon = "cambia el número de equilibrios de forma no asociada a un par simple"
    return {"hechos": hechos, "tipo_sugerido": tipo, "razon": razon}


def _refinar_por_biseccion(modelo, base, parametro, a, b, ea, eb, region, cfg, max_iter=40):
    """
    Acota el cambio dentro de [a, b] bisecando el parámetro y comparando la firma
    (nº de equilibrios y su estabilidad). Se detiene si el punto medio presenta
    una tercera firma distinta (varios cambios en el intervalo) o si el ancho ya
    es menor que `tol_parametro`. Devuelve (inf, sup, nota).
    """
    fa, fb = _firma(ea), _firma(eb)
    nota = ""
    for _ in range(max_iter):
        if b - a <= cfg["tol_parametro"]:
            break
        m = 0.5 * (a + b)
        em = _estado_en(modelo, base, parametro, m, region, cfg)
        fm = _firma(em)
        if fm == fa:
            a, ea = m, em
        elif fm == fb:
            b, eb = m, em
        else:
            nota = ("Hay más de un cambio dentro del intervalo; el refinamiento se detuvo en una "
                    "firma intermedia. Conviene aumentar n_valores o acotar el rango.")
            break
    return a, b, nota


def detectar_candidatos(modelo, base, parametro, valores, estados, region, cfg) -> List[Dict[str, Any]]:
    """
    Candidatos a bifurcación entre valores consecutivos del parámetro.

    Si dos intervalos contiguos cambian y el valor de parámetro que comparten
    tiene un equilibrio "no concluyente" (no hiperbólico), se fusionan en un solo
    candidato: ocurre cuando la rejilla cae justo sobre el valor crítico.
    """
    umbral = 0.25 * max(b - a for a, b in region)
    cambios = [k for k in range(len(valores) - 1) if _firma(estados[k]) != _firma(estados[k + 1])]
    grupos: List[List[int]] = []
    for k in cambios:
        if grupos and k == grupos[-1][-1] + 1 and _firma(estados[k])[3] > 0:
            grupos[-1].append(k)
        else:
            grupos.append([k])
    candidatos = []
    for g in grupos:
        k0, k1 = g[0], g[-1] + 1
        ea, eb = estados[k0], estados[k1]
        desc = _describir_cambio(ea, eb, umbral)
        inf, sup, notas = None, None, []
        for k in g:
            a, b, nota = _refinar_por_biseccion(modelo, base, parametro, valores[k], valores[k + 1],
                                                estados[k], estados[k + 1], region, cfg)
            inf = a if inf is None else min(inf, a)
            sup = b if sup is None else max(sup, b)
            if nota:
                notas.append(nota)
        if len(g) > 1:
            notas.append("Dos intervalos contiguos se fusionaron: la rejilla cae sobre el valor crítico "
                         "(equilibrio no hiperbólico en el punto compartido).")
        candidatos.append({
            "intervalo_inicial": [float(valores[k0]), float(valores[k1])],
            "intervalo_refinado": [float(inf), float(sup)],
            "estimacion": float(0.5 * (inf + sup)),
            "firma_antes": list(_firma(ea)), "firma_despues": list(_firma(eb)),
            "que_cambia": desc["hechos"], "tipo_sugerido": desc["tipo_sugerido"],
            "razon_tipo": desc["razon"],
            "evidencia": "numerica", "confirmado_matematicamente": False,
            "nota": " ".join(notas),
        })
    return candidatos


# ---------------------------------------------------------------------------
# 5. MÁXIMOS LOCALES DE TRAYECTORIAS (reutiliza resolver_edo)
# ---------------------------------------------------------------------------

def maximos_locales(serie_t: np.ndarray, serie_y: np.ndarray) -> List[Tuple[float, float]]:
    """Máximos interiores de una serie muestreada, refinados con parábola de 3 puntos."""
    salida = []
    for i in range(1, len(serie_y) - 1):
        if serie_y[i - 1] < serie_y[i] >= serie_y[i + 1]:
            y0, y1, y2 = serie_y[i - 1], serie_y[i], serie_y[i + 1]
            den = y0 - 2 * y1 + y2
            delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
            delta = max(-1.0, min(1.0, delta))
            h = serie_t[i + 1] - serie_t[i]
            salida.append((float(serie_t[i] + delta * h), float(y1 - 0.25 * (y0 - y2) * delta)))
    return salida


def clasificar_comportamiento(serie: np.ndarray, maximos: List[float], tol: float) -> str:
    """
    Comportamiento de la serie DESPUÉS del transitorio:
      "converge"            : la serie casi no varía (rango <= tol*(1+|media|)); sin oscilación apreciable.
      "oscila (amplitud constante)" : máximos con variación relativa < 1e-3 (compatible con un ciclo).
      "amplitud decreciente": los máximos bajan de forma sostenida (convergencia lenta; no es un ciclo estable).
      "otro"                : cualquier otro patrón (crece, irregular...); requiere revisión manual.
    Es una heurística: no distingue un ciclo de una oscilación muy lenta.
    """
    if len(serie) == 0 or (np.max(serie) - np.min(serie)) <= tol * (1.0 + abs(float(np.mean(serie)))):
        return "converge"
    if len(maximos) < 3:
        return "otro"
    m = np.asarray(maximos)
    if (m.max() - m.min()) <= 1e-3 * max(abs(m.max()), 1e-300):
        return "oscila (amplitud constante)"
    if m[-1] < m[0] and np.all(np.diff(m) <= 1e-9 * max(abs(m[0]), 1e-300)):
        return "amplitud decreciente"
    return "otro"


def barrido_maximos(modelo, base, parametro, valores, y0, intervalo, variable_indice, cfg_max) -> Dict[str, Any]:
    """
    Para cada valor del parámetro integra con `resolver_edo` desde `y0`, descarta
    la fracción inicial `fraccion_transitorio` y registra los máximos locales de
    la variable `variable_indice`. Una integración fallida se anota y NO se omite
    en silencio.
    """
    t0, tf = float(intervalo[0]), float(intervalo[1])
    t_corte = t0 + cfg_max["fraccion_transitorio"] * (tf - t0)
    puntos = int(min(max(2, round(cfg_max["puntos_por_unidad_tiempo"] * (tf - t0))), 40000))
    datos, fallos = [], []
    for v in valores:
        params = {**base, parametro: float(v)}
        try:
            sol = resolver_edo(modelo, list(y0), (t0, tf), params, puntos=puntos, metodo=cfg_max["metodo"],
                               rtol=cfg_max["rtol"], atol=cfg_max["atol"])
        except Exception as exc:
            fallos.append({"valor_parametro": float(v), "error": str(exc)})
            continue
        mascara = sol.t >= t_corte
        serie = sol.y[variable_indice][mascara]
        pares = maximos_locales(sol.t[mascara], serie)
        maximos = [m for _, m in pares]
        comportamiento = clasificar_comportamiento(serie, maximos, cfg_max["tol_oscilacion"])
        if comportamiento == "converge":
            maximos, pares = [], []   # los "máximos" serían ruido de una oscilación extinguida
        datos.append({"valor_parametro": float(v), "maximos": maximos, "comportamiento": comportamiento,
                      "tiempos": [t for t, _ in pares], "estado_final": [float(z) for z in sol.y[:, -1]]})
    return {"configuracion": {**cfg_max, "y0": [float(z) for z in y0], "intervalo": [t0, tf],
                              "tiempo_de_corte_transitorio": t_corte, "puntos_integracion": puntos,
                              "variable_indice": variable_indice},
            "datos": datos, "fallos": fallos}


# ---------------------------------------------------------------------------
# 6. FUNCIÓN PRINCIPAL
# ---------------------------------------------------------------------------

def analizar_bifurcaciones(modelo, parametros, parametro, rango, n_valores, region_busqueda, *,
                           semillas_por_dim=None, tol_residuo=1e-9, tol_estabilidad=1e-8,
                           tol_parametro=None, calcular_maximos=False, y0=None, intervalo=None,
                           variable_maximos=0, n_valores_maximos=12, fraccion_transitorio=0.6,
                           puntos_por_unidad_tiempo=60, metodo="RK45", rtol=1e-9, atol=1e-12,
                           nombre_caso=None, verificar_teoria=None) -> Dict[str, Any]:
    """
    Barrido de un parámetro: ramas de equilibrio, estabilidad, candidatos a
    bifurcación y (opcional) máximos locales. Ver el docstring del módulo.

    Parámetros del cálculo (todos quedan guardados en `resultado["config"]`):
        semillas_por_dim : semillas de Newton por eje en 2D/3D (por defecto 9 y 5).
        tol_residuo      : |F(x*)|_inf máximo aceptado para un equilibrio.
        tol_estabilidad  : |Re(lambda)| <= tol => "no concluyente".
        tol_parametro    : ancho mínimo del intervalo al refinar (por defecto 1e-7*rango).
        calcular_maximos : si True requiere y0 e intervalo (t0, tf) para integrar.
    """
    try:
        cfg_val = validar_configuracion_barrido(modelo, parametros, parametro, rango, n_valores, region_busqueda)
        if calcular_maximos:
            if y0 is None or intervalo is None:
                raise ErrorBifurcaciones("invalid_input",
                                         "Para calcular máximos locales se requieren y0 e intervalo.", missing="y0/intervalo")
            if len(list(y0)) != cfg_val["n"]:
                raise ErrorBifurcaciones("invalid_dimension", "y0 debe tener una componente por variable de estado.")
            if not (isinstance(variable_maximos, int) and 0 <= variable_maximos < cfg_val["n"]):
                raise ErrorBifurcaciones("invalid_input", "variable_maximos debe ser un índice de variable válido.")
            if not (0.0 <= fraccion_transitorio < 1.0):
                raise ErrorBifurcaciones("invalid_input", "fraccion_transitorio debe estar en [0, 1).")
            if not (isinstance(n_valores_maximos, int) and 1 <= n_valores_maximos <= MAX_VALORES_MAXIMOS):
                raise ErrorBifurcaciones("invalid_range", f"n_valores_maximos debe estar entre 1 y {MAX_VALORES_MAXIMOS}.")
    except ErrorBifurcaciones as err:
        return err.to_dict()

    region, base = cfg_val["region"], cfg_val["base"]
    p_min, p_max = cfg_val["rango"]
    valores = np.linspace(p_min, p_max, n_valores)
    cfg = {
        "semillas_por_dim": semillas_por_dim, "tol_residuo": float(tol_residuo),
        "tol_estabilidad": float(tol_estabilidad),
        "tol_parametro": float(tol_parametro) if tol_parametro else 1e-7 * (p_max - p_min),
    }

    try:
        estados = [_estado_en(modelo, base, parametro, v, region, cfg) for v in valores]
        candidatos = detectar_candidatos(modelo, base, parametro, valores, estados, region, cfg)
    except ErrorBifurcaciones as err:
        return err.to_dict()
    except Exception as exc:
        return ErrorBifurcaciones("model_evaluation_error", f"Falló el cálculo de equilibrios: {exc}",
                                  stage="equilibrios").to_dict()
    if all(len(e) == 0 for e in estados):
        return ErrorBifurcaciones(
            "incomplete_results",
            "No se halló ningún equilibrio en toda la región de búsqueda para el rango dado. "
            "Amplíe la región o revise el modelo (puede que no existan equilibrios en ese rango).",
            stage="equilibrios").to_dict()

    advertencias = [
        "Los candidatos son INDICIOS numéricos; no demuestran una bifurcación.",
        "Solo se buscaron equilibrios dentro de la región " +
        "; ".join(f"x{i + 1} en [{a:g}, {b:g}]" for i, (a, b) in enumerate(region)) + ".",
    ]
    if any(_es_continuo(e) for e in estados):
        advertencias.append("En algunos valores del parámetro F se anula en un continuo (p. ej. F identicamente 0): "
                            "no hay equilibrios aislados y esos valores se marcan como 'continuo'.")
    ramas = []
    for v, eqs in zip(valores, estados):
        ramas.append({"valor_parametro": float(v), "n_equilibrios": 0 if _es_continuo(eqs) else len(eqs),
                      "continuo": _es_continuo(eqs), "equilibrios": [
            {"punto": e["punto"], "estabilidad": e["estabilidad"], "max_re": e["max_re"],
             "autovalores": [formatear_complejo(z) for z in e["autovalores"]]} for e in eqs if e["estabilidad"] != "continuo"]})
    diagrama_equilibrio = [{"valor_parametro": r["valor_parametro"], "punto": e["punto"], "estabilidad": e["estabilidad"]}
                           for r in ramas for e in r["equilibrios"]]

    maximos = None
    if calcular_maximos:
        idx = np.unique(np.round(np.linspace(0, n_valores - 1, min(n_valores_maximos, n_valores))).astype(int))
        cfg_max = {"fraccion_transitorio": float(fraccion_transitorio),
                   "puntos_por_unidad_tiempo": float(puntos_por_unidad_tiempo), "metodo": metodo,
                   "rtol": float(rtol), "atol": float(atol), "tol_oscilacion": 1e-6, "valores_usados": [float(valores[i]) for i in idx]}
        maximos = barrido_maximos(modelo, base, parametro, [valores[i] for i in idx], y0, intervalo,
                                  variable_maximos, cfg_max)
        advertencias.append("Máximos locales: dependen de y0, del transitorio descartado y de la resolución temporal "
                            "(ver config).")
        if maximos["fallos"]:
            advertencias.append(f"{len(maximos['fallos'])} integración(es) fallaron y se omitieron en el diagrama de máximos.")

    resultado = {
        "analysis": "bifurcations", "valid": True,
        "config": {"nombre_caso": nombre_caso, "parametro": parametro, "rango": [p_min, p_max],
                   "n_valores": int(n_valores), "valores": [float(v) for v in valores],
                   "region_busqueda": [list(r) for r in region], "parametros_base": base, **cfg},
        "ramas": ramas, "candidatos": candidatos,
        "diagrama_equilibrio": diagrama_equilibrio,
        "maximos": maximos,
        "diagrama_maximos": ([{"valor_parametro": d["valor_parametro"], "maximo": m}
                              for d in maximos["datos"] for m in d["maximos"]] if maximos else None),
        "verificacion_teorica": None, "advertencias": advertencias,
    }
    if verificar_teoria:
        resultado["verificacion_teorica"] = _contrastar_con_teoria(resultado, verificar_teoria)
    resultado["report"] = formatear_reporte_bifurcaciones(resultado)
    return resultado


# ---------------------------------------------------------------------------
# 7. FORMAS NORMALES DE REFERENCIA (silla-nodo, horquilla, Hopf)
# ---------------------------------------------------------------------------
# LIMITACIÓN: la propuesta ubica los casos de referencia en `modelos_referencia.py`
# (responsable: Yanac, con apoyo de Christian). Ese archivo no es de este módulo y
# hoy solo contiene lineal/logístico/Lorenz; por eso las formas normales se
# declaran aquí. Cambio mínimo sugerido: moverlas a modelos_referencia.py y que
# este módulo las importe desde allí.

def forma_silla_nodo(t, y, parametros):
    """x' = mu - x^2."""
    return [parametros.get("mu", 0.0) - y[0] ** 2]


def forma_horquilla(t, y, parametros):
    """x' = mu*x - x^3 (supercrítica)."""
    mu = parametros.get("mu", 0.0)
    return [mu * y[0] - y[0] ** 3]


def forma_hopf(t, y, parametros):
    """x' = mu*x - y - x(x^2+y^2),  y' = x + mu*y - y(x^2+y^2)."""
    mu = parametros.get("mu", 0.0)
    x, yy = y
    r2 = x * x + yy * yy
    return [mu * x - yy - x * r2, x + mu * yy - yy * r2]


def _eq_teoricos_silla_nodo(mu):
    return [] if mu < 0 else ([[0.0]] if mu == 0 else [[-math.sqrt(mu)], [math.sqrt(mu)]])


def _eq_teoricos_horquilla(mu):
    return [[0.0]] if mu <= 0 else [[-math.sqrt(mu)], [0.0], [math.sqrt(mu)]]


FORMAS_NORMALES: Dict[str, Dict[str, Any]] = {
    "silla_nodo": {
        "titulo": "Silla-nodo: x' = mu - x^2", "funcion": forma_silla_nodo, "parametro": "mu",
        "parametros": {"mu": 0.0}, "rango": (-1.0, 1.0), "n_valores": 21, "region": [(-3.0, 3.0)],
        "mu_critico": 0.0, "equilibrios_teoricos": _eq_teoricos_silla_nodo,
        "descripcion_teorica": "Sin equilibrios para mu<0; ramas x=+-sqrt(mu) para mu>0 (+sqrt estable, -sqrt inestable).",
    },
    "horquilla": {
        "titulo": "Horquilla supercrítica: x' = mu*x - x^3", "funcion": forma_horquilla, "parametro": "mu",
        "parametros": {"mu": 0.0}, "rango": (-1.0, 1.0), "n_valores": 21, "region": [(-3.0, 3.0)],
        "mu_critico": 0.0, "equilibrios_teoricos": _eq_teoricos_horquilla,
        "descripcion_teorica": "El origen pierde estabilidad en mu=0 y nacen dos ramas estables x=+-sqrt(mu) para mu>0.",
    },
    "hopf": {
        "titulo": "Hopf: x'=mu*x-y-x(x^2+y^2), y'=x+mu*y-y(x^2+y^2)", "funcion": forma_hopf, "parametro": "mu",
        "parametros": {"mu": 0.0}, "rango": (-0.5, 1.0), "n_valores": 16, "region": [(-2.0, 2.0), (-2.0, 2.0)],
        "mu_critico": 0.0, "equilibrios_teoricos": lambda mu: [[0.0, 0.0]],
        "maximos": {"y0": [0.1, 0.0], "intervalo": (0.0, 300.0), "variable": 0, "radio_teorico": lambda mu: math.sqrt(mu) if mu > 0 else 0.0},
        "descripcion_teorica": "El origen cambia de estabilidad en mu=0 y para mu>0 aparece un ciclo límite estable de radio sqrt(mu).",
    },
}


def _contrastar_con_teoria(resultado: Dict[str, Any], caso: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara el barrido con los resultados teóricos CONOCIDOS de una forma normal:
    (i) equilibrios por valor del parámetro, (ii) valor crítico dentro del
    intervalo candidato, (iii) amplitud del ciclo (Hopf). Es verificación de un
    caso de referencia, no demostración general.
    """
    salida: Dict[str, Any] = {"caso": caso["titulo"], "descripcion_teorica": caso["descripcion_teorica"]}
    # (i) equilibrios
    peor, discrepancias = 0.0, []
    for r in resultado["ramas"]:
        mu = r["valor_parametro"]
        teo = sorted(map(tuple, caso["equilibrios_teoricos"](mu)))
        obs = sorted(tuple(e["punto"]) for e in r["equilibrios"])
        if len(teo) != len(obs):
            # En el valor crítico exacto el equilibrio es doble/no hiperbólico y puede no detectarse.
            if abs(mu - caso["mu_critico"]) <= 1e-12:
                discrepancias.append({"valor_parametro": mu, "esperados": len(teo), "hallados": len(obs),
                                      "motivo": "valor crítico exacto: equilibrio no hiperbólico/doble, difícil de detectar"})
            else:
                discrepancias.append({"valor_parametro": mu, "esperados": len(teo), "hallados": len(obs), "motivo": "distinto número"})
            continue
        for a, b in zip(teo, obs):
            peor = max(peor, max(abs(x - y) for x, y in zip(a, b)))
    salida["error_max_posicion_equilibrios"] = peor
    salida["discrepancias_equilibrios"] = discrepancias
    # (ii) valor crítico
    mu_c = caso["mu_critico"]
    dentro, margen = False, None
    for c in resultado["candidatos"]:
        lo, hi = c["intervalo_refinado"]
        if lo - 1e-12 <= mu_c <= hi + 1e-12 or c["intervalo_inicial"][0] - 1e-12 <= mu_c <= c["intervalo_inicial"][1] + 1e-12:
            dentro, margen = True, c["intervalo_inicial"]
            break
    salida["mu_critico_teorico"] = mu_c
    salida["mu_critico_dentro_de_un_candidato"] = dentro
    salida["intervalo_candidato_que_lo_contiene"] = margen
    # (iii) Hopf
    if caso.get("maximos") and resultado.get("maximos"):
        radio = caso["maximos"]["radio_teorico"]
        filas = []
        for d in resultado["maximos"]["datos"]:
            teo = radio(d["valor_parametro"])
            if d["maximos"]:
                obs = max(d["maximos"])
                filas.append({"valor_parametro": d["valor_parametro"], "maximo_observado": obs, "radio_teorico": teo,
                              "error_abs": abs(obs - teo), "comportamiento": d["comportamiento"]})
            else:   # converge al equilibrio: la amplitud observada es 0
                filas.append({"valor_parametro": d["valor_parametro"], "maximo_observado": 0.0, "radio_teorico": teo,
                              "error_abs": abs(teo), "comportamiento": d["comportamiento"]})
        salida["amplitud_ciclo"] = filas
    return salida


def ejecutar_forma_normal(nombre: str, **opciones) -> Dict[str, Any]:
    """Ejecuta un caso de referencia completo ("silla_nodo", "horquilla", "hopf")."""
    clave = str(nombre).lower().strip().replace("-", "_")
    if clave not in FORMAS_NORMALES:
        return ErrorBifurcaciones("unknown_case", f"Caso desconocido: {nombre!r}. Opciones: "
                                  f"{', '.join(FORMAS_NORMALES)}.", stage="adaptador").to_dict()
    caso = FORMAS_NORMALES[clave]
    args = dict(parametros=dict(caso["parametros"]), parametro=caso["parametro"], rango=caso["rango"],
                n_valores=caso["n_valores"], region_busqueda=caso["region"], nombre_caso=caso["titulo"],
                verificar_teoria=caso)
    if caso.get("maximos"):
        args.update(calcular_maximos=True, y0=caso["maximos"]["y0"], intervalo=caso["maximos"]["intervalo"],
                    variable_maximos=caso["maximos"]["variable"])
    args.update(opciones)
    return analizar_bifurcaciones(caso["funcion"], **args)


# ---------------------------------------------------------------------------
# 8. REPORTE DE CONSOLA
# ---------------------------------------------------------------------------

def _texto_equilibrio(e: Dict[str, Any]) -> str:
    punto = ", ".join(f"{v + 0.0:+.4f}".replace("-0.0000", "+0.0000") for v in e["punto"])
    etiqueta = {"estable": "E", "inestable": "I", "no concluyente": "?"}[e["estabilidad"]]
    return f"({punto}) {etiqueta}"


def formatear_reporte_bifurcaciones(resultado: Dict[str, Any], max_filas: int = 30) -> str:
    """
    Reporte de consola: configuración reproducible, tabla de ramas de equilibrio
    (E = estable, I = inestable, ? = no concluyente), candidatos a bifurcación con
    su nivel de evidencia, máximos locales, contraste con teoría y advertencias.
    """
    if not resultado.get("valid"):
        return formatear_error_consola(resultado, "ANÁLISIS DE BIFURCACIONES")
    c = resultado["config"]
    titulo = "ANÁLISIS DE BIFURCACIONES" + (f"  -  {c['nombre_caso']}" if c.get("nombre_caso") else "")
    L = [titulo_consola(titulo), "CONFIGURACIÓN (para poder reproducir el cálculo)"]
    L.append(campo_consola("Parámetro variado", f"{c['parametro']} en [{c['rango'][0]:g}, {c['rango'][1]:g}], "
                                                f"{c['n_valores']} valores", "  ", 21))
    otros = {k: v for k, v in c["parametros_base"].items() if k != c["parametro"]}
    L.append(campo_consola("Otros parámetros", ", ".join(f"{k} = {v:g}" for k, v in otros.items()) or "ninguno", "  ", 21))
    L.append(campo_consola("Región de búsqueda", "; ".join(f"x{i + 1} en [{a:g}, {b:g}]" for i, (a, b) in enumerate(c["region_busqueda"])), "  ", 21))
    L.append(campo_consola("Tolerancias", f"residuo {c['tol_residuo']:g} | estabilidad {c['tol_estabilidad']:g} | "
                                          f"paso mín. {c['tol_parametro']:.0e}", "  ", 21))

    L += ["", separador_consola(), "RAMAS DE EQUILIBRIO   (E = estable, I = inestable, ? = no concluyente)", ""]
    ramas = resultado["ramas"]
    mostrar = set(range(len(ramas)))
    if len(ramas) > max_filas:  # tabla larga: primeras/últimas filas y vecindad de cada candidato
        mostrar = {0, len(ramas) - 1} | set(range(0, len(ramas), math.ceil(len(ramas) / max_filas)))
        for cand in resultado["candidatos"]:
            for i, r in enumerate(ramas):
                if cand["intervalo_inicial"][0] - 1e-12 <= r["valor_parametro"] <= cand["intervalo_inicial"][1] + 1e-12:
                    mostrar.add(i)
    filas = []
    for i, r in enumerate(ramas):
        if i in mostrar:
            if r.get("continuo"):
                detalle = "F = 0 en un continuo (caso degenerado; sin equilibrios aislados)"
            else:
                textos = [_texto_equilibrio(e) for e in r["equilibrios"]]
                detalle = "   ".join(textos[:4]) + (f"   ... (+{len(textos) - 4} más)" if len(textos) > 4 else "")
            filas.append([f"{r['valor_parametro']:+.4f}", "continuo" if r.get("continuo") else r["n_equilibrios"],
                          detalle or "(ninguno hallado)"])
    L += _tabla([c["parametro"], "N° eq.", "Equilibrios (x1, x2, ...) y estabilidad"], filas)
    if len(mostrar) < len(ramas):
        L.append(f"  (se muestran {len(mostrar)} de {len(ramas)} valores; el resultado completo está en `ramas`)")

    L += ["", separador_consola(), "CANDIDATOS A BIFURCACIÓN   (evidencia numérica, NO demostración)"]
    if not resultado["candidatos"]:
        L.append("  Ningún cambio de número o de estabilidad de equilibrios en este rango.")
    for k, cand in enumerate(resultado["candidatos"], start=1):
        lo, hi = cand["intervalo_refinado"]
        L += ["", f"  Candidato {k}: {c['parametro']} entre {lo:.9g} y {hi:.9g}"]
        L.append(campo_consola("Qué cambia", "; ".join(cand["que_cambia"]) or "cambia la firma de equilibrios", "    ", 17))
        L.append(campo_consola("Tipo (hipótesis)", cand["tipo_sugerido"], "    ", 17))
        L.append(campo_consola("Evidencia", "numérica; confirmado matemáticamente: NO", "    ", 17))
        if cand["nota"]:
            L.append(campo_consola("Nota", cand["nota"], "    ", 17))

    if resultado.get("maximos"):
        m = resultado["maximos"]
        mc = m["configuracion"]
        L += ["", separador_consola(), "MÁXIMOS LOCALES DE LA TRAYECTORIA (variable x%d)" % (mc["variable_indice"] + 1)]
        L.append(campo_consola("Condición inicial", mc["y0"], "  ", 22))
        L.append(campo_consola("Integración", f"t en [{mc['intervalo'][0]:g}, {mc['intervalo'][1]:g}], método {mc['metodo']}, "
                                              f"rtol {mc['rtol']:g}, atol {mc['atol']:g}, {mc['puntos_integracion']} puntos", "  ", 22))
        L.append(campo_consola("Transitorio descartado", f"t < {mc['tiempo_de_corte_transitorio']:g} "
                                                         f"({mc['fraccion_transitorio']:.0%} del intervalo)", "  ", 22))
        L.append("")
        filas = [[f"{d['valor_parametro']:+.4f}", d["comportamiento"], len(d["maximos"]) or "-",
                  f"{max(d['maximos']):.5f}" if d["maximos"] else "-",
                  f"{min(d['maximos']):.5f}" if d["maximos"] else "-"] for d in m["datos"]]
        L += _tabla([c["parametro"], "Comportamiento tras el transitorio", "N° máx.", "Máx. mayor", "Máx. menor"], filas)
        L.append("  ('converge' = sin oscilación apreciable; no se listan máximos. 'amplitud decreciente' = ")
        L.append("   convergencia lenta, p. ej. en el punto crítico; no es un ciclo estable.)")
        for f in m["fallos"]:
            L.append(f"  Integración fallida en {c['parametro']} = {f['valor_parametro']:+.4f}: {f['error']}")

    v = resultado.get("verificacion_teorica")
    if v:
        L += ["", separador_consola(), "CONTRASTE CON LA TEORÍA (solo para esta forma normal de referencia)",
              campo_consola("Teoría", v["descripcion_teorica"], "  ", 26),
              campo_consola("Valor crítico teórico", f"{c['parametro']} = {v['mu_critico_teorico']:g}", "  ", 26),
              campo_consola("¿Dentro de un candidato?", "sí" if v["mu_critico_dentro_de_un_candidato"] else "NO", "  ", 26),
              campo_consola("Error máx. en equilibrios", f"{v['error_max_posicion_equilibrios']:.2e}", "  ", 26)]
        for d in v["discrepancias_equilibrios"]:
            L.append(campo_consola("Discrepancia", f"{c['parametro']} = {d['valor_parametro']:+.4f}: esperados {d['esperados']}, "
                                                   f"hallados {d['hallados']} ({d['motivo']})", "  ", 26))
        if v.get("amplitud_ciclo"):
            L.append("  Amplitud del ciclo límite (máximo observado vs radio teórico):")
            L += _tabla([c["parametro"], "Observado", "Teórico", "Error abs.", "Comportamiento"],
                        [[f"{f['valor_parametro']:+.4f}", f"{f['maximo_observado']:.5f}", f"{f['radio_teorico']:.5f}",
                          f"{f['error_abs']:.1e}", f["comportamiento"]] for f in v["amplitud_ciclo"]], "    ")
    L += ["", separador_consola(), "ADVERTENCIAS Y LIMITACIONES"]
    for a in resultado["advertencias"]:
        L.append(textwrap.fill("- " + a, width=ANCHO_CONSOLA, initial_indent="  ", subsequent_indent="    "))
    return "\n".join(L)


def imprimir_reporte_bifurcaciones(resultado: Dict[str, Any], max_filas: int = 30) -> None:
    """Imprime por consola el reporte de `analizar_bifurcaciones`."""
    print(formatear_reporte_bifurcaciones(resultado, max_filas))


__all__ = [
    "analizar_bifurcaciones", "ejecutar_forma_normal", "validar_configuracion_barrido", "buscar_equilibrios",
    "detectar_candidatos", "barrido_maximos", "maximos_locales", "formatear_reporte_bifurcaciones",
    "imprimir_reporte_bifurcaciones", "FORMAS_NORMALES", "forma_silla_nodo", "forma_horquilla", "forma_hopf",
    "ErrorBifurcaciones", "RAZONES",
]
