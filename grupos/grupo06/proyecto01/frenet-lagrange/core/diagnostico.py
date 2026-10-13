"""
core/diagnostico.py — Diagnóstico del problema y selección del método.

Recibe un enunciado en lenguaje natural (o semi-formal) y decide qué herramienta usar:

* **Lagrange**  — optimizar f sujeta a restricciones de IGUALDAD ("sujeto a", "sobre la
  circunferencia", "con x + y = 10", "perímetro fijo", ...).
* **Hessiana**  — puntos críticos / extremos LIBRES ("puntos críticos", "máximos y mínimos
  relativos", "punto de silla", "Hessiana", ...).
* **Frenet**    — curvas parametrizadas r(t) ("curvatura", "torsión", "triedro", "binormal",
  "plano osculador", "r(t) = (...)", ...).

Combina palabras clave con pistas estructurales (¿hay un vector de componentes en t?, ¿hay
igualdades además de la función?) y además EXTRAE las expresiones para proponer los
argumentos de la herramienta. Es determinista: no necesita ningún LLM.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from core.utils_math import ErrorEntrada, normalizar_unicode, parsear_seguro

__all__ = ["Diagnostico", "diagnosticar", "HERRAMIENTAS"]

Metodo = Literal["lagrange", "hessiana", "frenet"]
HERRAMIENTAS: dict[str, str] = {"lagrange": "optimizar_con_restricciones", "hessiana": "analizar_puntos_criticos",
                                "frenet": "analizar_curva_frenet"}

# (patrón, peso, explicación)
_CLAVES: dict[str, list[tuple[str, float, str]]] = {
    "lagrange": [
        (r"\bsujet[oa]s? a\b|\bs\.?\s?a\.?\b(?=\s)|\bsujeta\b", 3.0, "aparece 'sujeto a' (restricción)"),
        (r"\brestricci[oó]n|\brestringid|\bcondicionad|\bligadura|\bv[ií]nculo", 3.0, "habla de restricciones"),
        (r"\blagrange\b|\bmultiplicador", 4.0, "menciona multiplicadores de Lagrange"),
        (r"\bsobre (la|el|una|un) (circunferencia|c[ií]rculo|esfera|elipse|elipsoide|plano|recta|curva|superficie|par[aá]bola)",
         3.0, "pide extremos SOBRE un conjunto (curva o superficie)"),
        (r"\b(per[ií]metro|[aá]rea|volumen|presupuesto|costo|superficie) (fij[oa]|dad[oa]|constante|de \d)", 2.5,
         "hay una cantidad fija (típica restricción)"),
        (r"\bcon la condici[oó]n\b|\btal(es)? que\b|\bdado que\b|\bsiempre que\b", 1.5, "impone una condición"),
        (r"\bdistancia (m[ií]nima|m[aá]xima)", 1.5, "distancia extrema a un conjunto"),
    ],
    "hessiana": [
        (r"\bpuntos? cr[ií]tico|\bpuntos? estacionari", 3.0, "pide puntos críticos"),
        (r"\bhessian|\bdiscriminante|\bsegunda derivada|\bcriterio de (la )?segunda", 3.5, "menciona la Hessiana / 2ª derivada"),
        (r"\bpunto de silla|\bsillas?\b", 2.5, "menciona puntos de silla"),
        (r"\bextremos? (relativ|local|libre|absolut)|\bm[aá]ximos? y m[ií]nimos? (relativ|local)", 2.5,
         "pide extremos relativos/libres"),
        (r"\bclasific", 1.5, "pide clasificar puntos"),
        (r"\bm[aá]xim|\bm[ií]nim|\boptimi", 0.8, "busca máximos o mínimos"),
    ],
    "frenet": [
        (r"\bfrenet|\btriedro|\bserret", 4.0, "menciona el triedro de Frenet"),
        (r"\bcurvatura|\btorsi[oó]n", 3.5, "pide curvatura o torsión"),
        (r"\bbinormal|\bnormal principal|\btangente unitari|\bvector tangente", 3.0, "pide vectores T, N o B"),
        (r"\bplano (osculador|normal|rectificante)|\bc[ií]rculo osculador", 3.5, "pide planos o círculo osculador"),
        (r"\bcurva param|\bparametrizad|\bparam[eé]tric|\btrayectoria|\bh[eé]lice", 2.5, "es una curva parametrizada"),
        (r"\blongitud de arco|\bvelocidad y aceleraci", 1.5, "pide longitud de arco o cinemática"),
    ],
}


@dataclass
class Diagnostico:
    metodo_recomendado: Metodo | None
    herramienta: str | None
    confianza: float
    puntuaciones: dict[str, float]
    razones: list[str] = field(default_factory=list)
    argumentos_sugeridos: dict[str, Any] = field(default_factory=dict)
    faltantes: list[str] = field(default_factory=list)
    nota: str = ""

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalizar(t: str) -> str:
    t = normalizar_unicode(t).replace("≤", "<=").replace("≥", ">=")
    return unicodedata.normalize("NFKC", t)


def _es_expr(s: str) -> bool:
    try:
        parsear_seguro(s)
        return True
    except ErrorEntrada:
        return False


def _limpiar_expr(s: str) -> str:
    s = s.strip().strip(".;:¿?¡!")
    s = re.sub(r"\s+(en|para|cuando|donde|y halla|y calcula|y clasifica)\b.*$", "", s, flags=re.I)
    return s.strip().strip(".;:")


def _dividir_top(texto: str) -> list[str]:
    """Divide por comas que no estén dentro de paréntesis."""
    partes, nivel, act = [], 0, ""
    for ch in texto:
        if ch in "([":
            nivel += 1
        elif ch in ")]":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append(act)
            act = ""
        else:
            act += ch
    partes.append(act)
    return [p.strip() for p in partes if p.strip()]


_RE_EXPR = re.compile(r"[\w^*+\-/().]+(?:\s*[+\-*/^=]\s*[\w^*+\-/().]+)*")
_PALABRAS = re.compile(r"[a-záéíóúñ]{4,}", re.I)


def _candidatos(texto: str) -> list[str]:
    """Trozos con aspecto de expresión (operandos unidos por operadores), del más largo al más corto."""
    out = []
    for m in _RE_EXPR.finditer(texto):
        c = m.group(0).strip(" .,;")
        if not re.search(r"[A-Za-z]", c) or not re.search(r"[+\-*/^]|\d[a-z]", c):
            continue
        if any(w.lower() not in _FUNCIONES for w in _PALABRAS.findall(c)):
            continue
        out.append(c)
    return sorted(out, key=len, reverse=True)


_FUNCIONES = {"sqrt", "sinh", "cosh", "tanh", "asin", "acos", "atan", "atan2", "cbrt", "root", "ceiling", "floor",
              "sign", "arcsin", "arccos", "arctan"}


def _extraer_curva(t: str) -> tuple[list[str] | None, str | None, str | None]:
    """r(t) = (x(t), y(t), z(t)) → componentes, parámetro y t0 (si aparece)."""
    comps, par = None, None
    m = re.search(r"\b[rRγαc]\s*\(\s*([a-zA-Z])\s*\)\s*=\s*([\(<\[])", t)
    if m:
        par = m.group(1)
        abre = m.group(2)
        cierra = {"(": ")", "<": ">", "[": "]"}[abre]
        ini, nivel, fin = m.end(), 1, None
        for k in range(ini, len(t)):
            ch = t[k]
            if ch == abre and abre != "<":
                nivel += 1
            elif ch == cierra:
                nivel -= 1
                if nivel == 0:
                    fin = k
                    break
        if fin is not None:
            partes = _dividir_top(t[ini:fin])
            if 2 <= len(partes) <= 3 and all(_es_expr(p) for p in partes):
                comps = partes
    t0 = None
    m0 = re.search(r"\b(?:t_?0|en\s+t|para\s+t|cuando\s+t)\s*=\s*([-+]?[\w./*^()]+)", t)
    if m0 and _es_expr(m0.group(1).rstrip(".,")):
        t0 = m0.group(1).rstrip(".,")
    return comps, par, t0


_FIN = r"(?=\s+(?:sujet|s\.\s?a\.|con\b|sobre\b|restringid|tal que|en el|en la)|[;\n¿?]|,\s*(?:y\s+)?(?:halla|encuentra|calcula|clasifica|determina)|$)"


def _extraer_funcion(t: str) -> str | None:
    m = re.search(r"\b[fFgGuUzZ]\s*\(\s*[a-z](?:\s*,\s*[a-z])*\s*\)\s*=\s*(.+?)" + _FIN, t)
    if m:
        e = _limpiar_expr(m.group(1))
        if _es_expr(e):
            return e
    m = re.search(r"(?:maximiz\w*|minimiz\w*|optimiz\w*|extremos de|cr[ií]ticos de|m[aá]ximo de|m[ií]nimo de|"
                  r"funci[oó]n)\s+(?:la funci[oó]n\s+)?(?:f\s*=\s*)?(.+?)" + _FIN, t, flags=re.I)
    if m:
        cands = _candidatos(_limpiar_expr(m.group(1)))
        for c in cands:
            if "=" not in c and _es_expr(c):
                return c
    for c in _candidatos(re.split(r"sujet|s\.\s?a\.|\bcon\b|\bsobre\b|tal que", t, maxsplit=1, flags=re.I)[0]):
        if "=" not in c and _es_expr(c):
            return c
    return None


def _extraer_restricciones(t: str) -> list[str]:
    m = re.search(r"(?:sujet[oa]s? a|s\.\s?a\.|con la (?:restricci[oó]n|condici[oó]n)|restringid[oa] a|sobre|tal que|"
                  r"\bcon)\s+(?:la\s+[a-záéíóú]+\s+|el\s+[a-záéíóú]+\s+)?(.+)$", t, flags=re.I)
    if not m:
        return []
    cola = re.split(r"[¿?]|,\s*(?:halla|encuentra|calcula|clasifica|determina)", m.group(1))[0]
    trozos = re.split(r"(\s+y\s+|;|,)", cola)
    out, actual = [], ""
    for tr in trozos:
        if re.fullmatch(r"\s+y\s+|;|,", tr):
            if "=" in actual:                       # el separador cierra una igualdad completa
                out.append(actual)
                actual = ""
            else:                                   # 'y' era una variable: se conserva
                actual += tr
        else:
            actual += tr
    if actual:
        out.append(actual)
    res = []
    for tr in out:
        tr = _limpiar_expr(tr)
        if "=" in tr and "<" not in tr and ">" not in tr:
            a, b = tr.split("=", 1)
            if _es_expr(a) and _es_expr(b):
                res.append(tr)
    return res


def diagnosticar(enunciado: str) -> Diagnostico:
    """Elige el método más adecuado y propone los argumentos de la herramienta."""
    t = _normalizar(enunciado)
    tl = t.lower()
    punt = {m: 0.0 for m in _CLAVES}
    razones: list[str] = []
    for metodo, reglas in _CLAVES.items():
        for patron, peso, explic in reglas:
            if re.search(patron, tl):
                punt[metodo] += peso
                razones.append(f"[{metodo}] {explic}")

    comps, par, t0 = _extraer_curva(t)
    f = _extraer_funcion(t)
    gs = _extraer_restricciones(t) if f else []
    if comps:
        punt["frenet"] += 4.0
        razones.append(f"[frenet] se reconoce una curva {par}↦({', '.join(comps)})")
    if gs:
        punt["lagrange"] += 3.0
        razones.append(f"[lagrange] además de f hay {len(gs)} igualdad(es): {'; '.join(gs)}")
    elif f and not comps:
        punt["hessiana"] += 1.0
        razones.append("[hessiana] hay una función y ninguna restricción de igualdad")
    if punt["lagrange"] > 0 and punt["hessiana"] > 0 and not gs and not re.search(r"sujet|restric|sobre|lagrange", tl):
        punt["lagrange"] *= 0.5

    total = sum(punt.values())
    if total == 0:
        return Diagnostico(None, None, 0.0, punt, ["no se reconoció ningún indicio"],
                           nota="No se pudo decidir el método. Pide al usuario la función (y restricciones, si las hay) "
                                "o la curva r(t).")
    mejor: Metodo = max(punt, key=punt.get)          # type: ignore[assignment]
    orden = sorted(punt.values(), reverse=True)
    confianza = round(min(1.0, (orden[0] - orden[1]) / max(orden[0], 1e-9) * 0.6 + min(orden[0], 8) / 8 * 0.4), 2)

    args: dict[str, Any] = {}
    faltan: list[str] = []
    if mejor == "frenet":
        if comps:
            args["curva"] = comps
            if par and par != "t":
                args["parametro"] = par
        else:
            faltan.append("curva r(t) = (x(t), y(t), z(t))")
        if t0:
            args["t0"] = t0
        else:
            faltan.append("t0 (se usará 0 por defecto)")
    elif mejor == "lagrange":
        if f:
            args["funcion"] = f
        else:
            faltan.append("función objetivo f")
        if gs:
            args["restricciones"] = gs
        else:
            faltan.append("restricción de igualdad g = 0")
    else:
        if f:
            args["funcion"] = f
        else:
            faltan.append("función f")
    nota = ("Argumentos extraídos automáticamente: confírmalos antes de llamar a la herramienta."
            if args else "Faltan datos para llamar a la herramienta.")
    return Diagnostico(mejor, HERRAMIENTAS[mejor], confianza, {k: round(v, 2) for k, v in punt.items()},
                       razones, args, faltan, nota)
