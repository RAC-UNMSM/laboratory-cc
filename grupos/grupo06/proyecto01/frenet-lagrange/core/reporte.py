"""
core/reporte.py — Inyección de resultados en plantillas y reportes de texto.

* ``renderizar_html``: rellena ``templates/base.html.j2`` (Jinja2) con el JSON del resultado,
  los datos de los gráficos, la hoja de estilos y el JavaScript del método
  (``templates/static/*.js``). No hay HTML escrito a mano dentro del código Python.
* ``html_bytes``: calcula lo que falte (JSON + datos de gráficos) y devuelve la página como
  ``bytes`` UTF-8 (``html_string.encode('utf-8')``), lista para subirla a SeaweedFS.
* ``grafico_png_bytes``: la lámina PNG dibujada en un ``io.BytesIO`` (``.getvalue()``).
  TODO en memoria: este módulo no escribe nada en el disco del contenedor.
* ``resumen_breve``: frases cortas que el servidor MCP devuelve al LLM para que explique.
* ``texto_*``: reporte legible para la terminal.
*
* Plotly.js se carga desde 3 CDN con respaldo, o se incrusta (``offline=True``) desde el
* paquete de Python ``plotly`` para que la página funcione sin internet.
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import sympy as sp
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.utils_math import json_seguro, num as _num, texto as _s, vnum as _vnum
from methods import metodo_frenet as MF
from methods import metodo_hessiana as MH
from methods import metodo_lagrange as ML
from methods.metodo_frenet import CurvaFrenet
from methods.metodo_hessiana import ProblemaHessiana
from methods.metodo_lagrange import ProblemaLagrange

__all__ = ["renderizar_html", "html_bytes", "grafico_png_bytes", "figura_a_png_bytes", "resumen_breve", "texto", "texto_lagrange",
           "texto_hessiana", "texto_frenet", "a_dict"]

Metodo = Literal["lagrange", "hessiana", "frenet"]
DIR_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
DIR_STATIC = DIR_TEMPLATES / "static"

_entorno = Environment(loader=FileSystemLoader(str(DIR_TEMPLATES)),
                       autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)

#: Textos de cabecera y nombres por método.
CONFIG: dict[str, dict[str, str]] = {
    "lagrange": {"titulo": "Multiplicadores de Lagrange", "eyebrow": "Optimización condicionada · Cálculo exacto con SymPy",
                 "funcion": "resolver_lagrange()", "nombre_json": "lagrange_resultado.json"},
    "hessiana": {"titulo": "Puntos críticos y matriz Hessiana", "eyebrow": "Optimización libre · Cálculo exacto con SymPy",
                 "funcion": "resolver_hessiana()", "nombre_json": "hessiana_resultado.json"},
    "frenet": {"titulo": "Triedro de Frenet, curvatura y torsión",
               "eyebrow": "Geometría diferencial de curvas · Cálculo exacto con SymPy",
               "funcion": "resolver_frenet()", "nombre_json": "frenet_resultado.json"},
}
_PIE = "Generado por el servidor MCP del Grupo 06 · Frenet, Lagrange y Puntos Críticos"

_PLOTLY_CDN = (
    '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>\n'
    '<script>window.Plotly || document.write(\'<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"><\\/script>\')</script>\n'
    '<script>window.Plotly || document.write(\'<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.27.0/plotly.min.js"><\\/script>\')</script>')


@lru_cache(maxsize=None)
def _estatico(nombre: str) -> str:
    return (DIR_STATIC / nombre).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _plotly_local() -> str | None:
    """Código de Plotly.js incluido en el paquete de Python 'plotly' (pip install plotly)."""
    try:
        import importlib.resources as ir
        return (ir.files("plotly") / "package_data" / "plotly.min.js").read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None


def a_dict(metodo: Metodo, objeto: Any) -> dict:
    """JSON del resultado (delegado en el método correspondiente)."""
    return {"lagrange": ML.a_dict, "hessiana": MH.a_dict, "frenet": MF.a_dict}[metodo](objeto)


def renderizar_html(metodo: Metodo, resultado: dict, datos: dict, offline: bool = False) -> str:
    """Inyecta resultado (JSON del método) y datos (arreglos para graficar) en la plantilla."""
    if metodo not in CONFIG:
        raise ValueError(f"Método desconocido: {metodo}")
    if offline:
        codigo = _plotly_local()
        if codigo is None:
            raise RuntimeError("Modo offline: instala el paquete con  pip install plotly  y vuelve a intentar.")
        plotly_tag = "<script>" + codigo.replace("</script", "<\\/script") + "</script>"
    else:
        plotly_tag = _PLOTLY_CDN
    plantilla = _entorno.get_template("base.html.j2")
    return plantilla.render(
        metodo=metodo, pie=_PIE, plotly_tag=plotly_tag, css=_estatico("estilos.css"),
        resultado_json=json_seguro(resultado), datos_json=json_seguro(datos),
        js_base=_estatico("base.js"), js_modulo=_estatico(f"{metodo}.js"), js_arranque=_estatico("arranque.js"),
        **CONFIG[metodo])


def html_bytes(metodo: Metodo, objeto: Any, datos: dict | None = None, resultado: dict | None = None,
               offline: bool = False) -> bytes:
    """Página HTML completa del reporte, como bytes UTF-8 (en memoria, sin archivos)."""
    from core.visualizacion import datos_grafico
    resultado = resultado if resultado is not None else a_dict(metodo, objeto)
    datos = datos if datos is not None else datos_grafico(metodo, objeto)
    html_string = renderizar_html(metodo, resultado, datos, offline=offline)
    return html_string.encode("utf-8")


def figura_a_png_bytes(fig: Any, dpi: int = 130) -> bytes:
    """Convierte una figura de Matplotlib en bytes PNG usando un búfer en MEMORIA (io.BytesIO):
    no se escribe ningún archivo. Cierra la figura."""
    import matplotlib.pyplot as plt
    bufer = io.BytesIO()
    try:
        fig.savefig(bufer, format="png", dpi=dpi)
    finally:
        plt.close(fig)
    return bufer.getvalue()


def grafico_png_bytes(metodo: Metodo, objeto: Any, datos: dict | None = None) -> bytes:
    """Lámina PNG del método como ``bytes`` (generada en memoria con ``figura_a_png_bytes``)."""
    from core.visualizacion import generar_png
    return generar_png(metodo, objeto, datos)


def resumen_breve(metodo: Metodo, r: dict) -> list[str]:
    """Frases cortas y exactas para que el LLM explique el resultado sin leer todo el JSON."""
    out: list[str] = []
    if metodo == "lagrange":
        out.append(f"Lagrangiana: L = {r['lagrangiana']['expr']}. Sistema resuelto con {r['metodo_resolucion']}.")
        for i, p in enumerate(r["puntos_criticos"], 1):
            c = ", ".join(f"{k} = {v}" for k, v in p["coordenadas"].items())
            lam = ", ".join(f"{k} = {v}" for k, v in p["lambdas"].items())
            out.append(f"P{i}: ({c}), {lam}; f = {p['valor_f']} → {p['clasificacion']}"
                       + (f" [{p['comparacion_global']}]" if p.get("comparacion_global") else ""))
        for i, p in enumerate(r["puntos_singulares"], 1):
            c = ", ".join(f"{k} = {v}" for k, v in p["coordenadas"].items())
            out.append(f"S{i} (punto singular de la restricción): ({c}); f = {p['valor_f']}")
    elif metodo == "hessiana":
        pts = r["puntos_criticos"] + r["puntos_no_diferenciables"] + \
            [f["representante"] for f in r["familias"] if f.get("representante")]
        for i, p in enumerate(pts, 1):
            c = ", ".join(f"{k} = {v}" for k, v in p["coordenadas"].items())
            extra = f", D = {p['D']}" if "D" in p else ""
            out.append(f"P{i}: ({c}), f = {p['valor_f']}{extra} → {p['clasificacion']} ({p['certeza']}; {p['criterio']})"
                       + (f" [{p['comparacion_global']}]" if p.get("comparacion_global") else ""))
        G = r["analisis_global"]
        if G.get("minimo_global"):
            out.append(f"Mínimo global = {G['minimo_global']} ({G['certeza']}).")
        if G.get("maximo_global"):
            out.append(f"Máximo global = {G['maximo_global']} ({G['certeza']}).")
    else:
        e = r["en_t0"]
        out.append(f"Curva: {r['tipo']}. κ(t) = {r['curvatura']['expr']}" +
                   (f", τ(t) = {r['torsion']['expr']}" if r.get("torsion") else ""))
        if e.get("T"):
            out.append(f"En t0 = {r['entrada']['t0']}: r = ({', '.join(e['punto']['componentes'])}), "
                       f"T = ({', '.join(e['T']['componentes'])})")
        if e.get("N"):
            out.append(f"N = ({', '.join(e['N']['componentes'])}), B = ({', '.join(e['B']['componentes'])}), "
                       f"κ = {e['curvatura']['expr']}, τ = {e['torsion']['expr']}")
            pl = e["planos"]
            out.append(f"Planos: osculador {pl['osculador']['ecuacion']}; normal {pl['normal']['ecuacion']}; "
                       f"rectificante {pl['rectificante']['ecuacion']}")
        if r["verificacion"].get("correcto"):
            out.append("Fórmulas de Frenet–Serret y ortonormalidad verificadas con 50 dígitos.")
    out += [f"Advertencia: {a}" for a in r.get("advertencias", [])]
    return out


# ════════════════════════════════════════════════════════════════════════════
# Reportes de texto (terminal)
# ════════════════════════════════════════════════════════════════════════════
def _pp(e, ascii_: bool = False) -> str:
    return sp.pretty(e, use_unicode=not ascii_)


def texto_lagrange(P: ProblemaLagrange, ascii_: bool = False, detalle: bool = True) -> str:
    linea = "=" * 78
    s = [linea, " MULTIPLICADORES DE LAGRANGE", linea]
    s.append(f"f({', '.join(map(str, P.variables))}) = {P.f}")
    for i, g in enumerate(P.restricciones, 1):
        s.append(f"g{i} = {g} = 0")
    s.append(f"n = {P.n} variables, m = {P.m} restricciones  →  se revisan n − m = {P.n - P.m} menores orlados")
    s += ["", "1) Lagrangiana  L = f − Σ λ·g :", _pp(sp.Eq(sp.Symbol("L"), P.lagrangiana), ascii_)]
    s += ["", "2) Sistema ∇L = 0 :"]
    for e in P.ecuaciones:
        s.append("   " + _pp(sp.Eq(e, 0), ascii_).replace("\n", "\n   "))
    s += ["", f"3) Método de resolución: {P.metodo}"]
    if detalle and P.base_groebner:
        s.append("   Base de Gröbner (lex):")
        for g in P.base_groebner:
            s.append(f"     {g}")
    s += ["", "4) Hessiano orlado general:", _pp(P.hessiano_orlado_general, ascii_)]

    s += ["", f"5) Puntos críticos reales: {len(P.puntos)}", "-" * 78]
    for i, p in enumerate(P.puntos, 1):
        c = ", ".join(f"{v} = {p.coords[v]}" for v in P.variables)
        cn = ", ".join(f"{_num(p.coords[v]):.6g}" for v in P.variables)
        s.append(f"[P{i}]  {c}      (≈ {cn})")
        if p.lambdas:
            s.append("      " + ", ".join(f"{k} = {v}" for k, v in p.lambdas.items()))
        s.append(f"      f = {p.valor_f}   (≈ {_num(p.valor_f):.6g})")
        if detalle and p.hessiano_orlado is not None:
            s.append("      H_orlado en el punto:")
            s.append("      " + _pp(p.hessiano_orlado, ascii_).replace("\n", "\n      "))
        for k, d, sg in p.menores:
            s.append(f"      Δ{k} = {d}   (signo {'+' if sg > 0 else '−' if sg < 0 else '0'})")
        s.append(f"      ⇒ {p.clasificacion.upper()}")
        vt = p.verificacion_tangente
        if vt.get("autovalores") is not None and "coincide" in vt:
            ev = ", ".join(f"{x:.4g}" for x in vt["autovalores"])
            s.append(f"      Verificación (Hessiano de L en el espacio tangente): autovalores [{ev}] "
                     f"→ {'coincide ✔' if vt['coincide'] else 'DIFIERE ✘ (' + vt['clasificacion'] + ')'}")
        if p.global_:
            s.append(f"      Comparación global: {p.global_}")
        s.append("")
    if P.singulares:
        s += ["6) Puntos singulares de la restricción (candidatos que Lagrange NO ve):", "-" * 78]
        for p in P.singulares:
            c = ", ".join(f"{v} = {p.coords[v]}" for v in P.variables)
            s.append(f"[S]  {c}   f = {p.valor_f}   {p.global_}")
        s.append("")
    if P.familias:
        s.append("Familias de soluciones (parámetros libres):")
        for fam in P.familias:
            s.append(f"   {fam}")
    for a in P.advertencias:
        s.append(f"⚠ {a}")
    s.append("Nota: la comparación global solo vale si {g = 0} es cerrado y acotado (Weierstrass).")
    s.append(linea)
    return "\n".join(s)


def _bloque(texto, sangria="      "):
    return sangria + texto.replace("\n", "\n" + sangria)


def texto_hessiana(P: ProblemaHessiana, ascii_: bool = False, detalle: bool = True) -> str:
    L = "=" * 78
    vs = ", ".join(map(str, P.variables))
    s = [L, " PUNTOS CRÍTICOS Y MATRIZ HESSIANA (optimización libre)", L,
         f"f({vs}) = {P.f}", ""]
    s += ["1) Gradiente ∇f :"]
    for v, g in zip(P.variables, P.gradiente):
        s.append(_bloque(_pp(sp.Eq(sp.Symbol(f"∂f/∂{v}"), g), ascii_), "   "))
    s += ["", "2) Sistema ∇f = 0 (forma que se resolvió):"]
    for e in P.ecuaciones:
        s.append(_bloque(_pp(sp.Eq(e, 0), ascii_), "   "))
    if P.factores_descartados:
        s.append(f"   (se eliminaron factores que nunca se anulan: {', '.join(P.factores_descartados)})")
    s += [f"   Método: {P.metodo}"]
    if detalle and P.base_groebner:
        s.append("   Base de Gröbner (lex): " + " ; ".join(map(str, P.base_groebner)))
    s += ["", "3) Matriz Hessiana:", _pp(P.hessiana_general, ascii_)]
    if P.D_general is not None:
        s += ["   D(x, y) = f_xx·f_yy − (f_xy)² =", _bloque(_pp(P.D_general, ascii_), "   ")]

    todos = P.puntos + P.no_diferenciables
    s += ["", f"4) Puntos críticos: {len(todos)}" + (f"  (+ {len(P.familias)} familia(s))" if P.familias else ""),
          "-" * 78]
    for i, p in enumerate(todos, 1):
        s += _texto_punto_h(P, p, f"P{i}", ascii_, detalle)
    for fa in P.familias:
        par = ", ".join(f"{v} = {fa['expr'][v]}" for v in P.variables)
        s.append(f"[FAMILIA]  {par}   (parámetros libres: {', '.join(map(str, fa['parametros']))})")
        if fa.get("representante") is not None:
            s += _texto_punto_h(P, fa["representante"], "   representante", ascii_, detalle)
    G = P.analisis_global
    s += ["5) Análisis global:"]
    for j in G["justificacion"]:
        s.append(f"   • {j}")
    if G.get("minimo_global") is not None:
        s.append(f"   ⇒ MÍNIMO GLOBAL = {G['minimo_global']}")
    if G.get("maximo_global") is not None:
        s.append(f"   ⇒ MÁXIMO GLOBAL = {G['maximo_global']}")
    s.append(f"   (certeza: {G['certeza']})")
    for a in P.advertencias:
        s.append(f"⚠ {a}")
    s.append(L)
    return "\n".join(s)


def _texto_punto_h(P, p, nombre, ascii_, detalle):
    vs = P.variables
    c = ", ".join(f"{v} = {p.coords[v]}" for v in vs)
    cn = ", ".join(f"{_num(p.coords[v]):.6g}" for v in vs)
    s = [f"[{nombre}]  {c}      (≈ {cn})" + ("   ← NO DIFERENCIABLE" if p.tipo == "no diferenciable" else "")]
    s.append(f"      f = {p.valor_f}   (≈ {_num(p.valor_f):.6g})" +
             ("   ∇f = 0 verificado ✔" if p.verificado else ""))
    if detalle and p.hessiana is not None:
        s += ["      H en el punto:", _bloque(_pp(p.hessiana, ascii_))]
    if p.D is not None:
        s.append(f"      D = {p.D},  f_xx = {p.fxx}")
    elif p.menores:
        s.append("      menores: " + ", ".join(f"Δ{k} = {v}" for k, v, _ in p.menores))
    if p.autovalores:
        s.append("      autovalores: " + ", ".join(
            (str(a["exacto"]) if a["exacto"] is not None else f"≈{a['num']:.5g}") +
            (f" (×{a['mult']})" if a["mult"] > 1 else "") for a in p.autovalores))
    if p.clasif_segundo_orden and p.clasif_segundo_orden != p.clasificacion:
        s.append(f"      Criterio de 2º orden: {p.clasif_segundo_orden.upper()}")
    for paso in p.orden_superior.get("pasos", []):
        s.append(f"        → {_s(paso)}")
    s.append(f"      ⇒ {p.clasificacion.upper()}   [{p.certeza}; {p.criterio}]")
    va = p.verif_autovalores
    if va and va.get("clasificacion") != MH.DUDOSO and p.clasif_segundo_orden != MH.DUDOSO:
        s.append(f"      Verificación por autovalores: {'coincide ✔' if va['coincide'] else 'DIFIERE ✘'}")
    if p.certificado:
        s.append(f"      Certificado: {p.certificado[2:]}")
    if p.global_:
        s.append(f"      Global: {p.global_.upper()}")
    s.append("")
    return s


def _bl(txt, sang="   "):
    return sang + txt.replace("\n", "\n" + sang)


def _vt(v):
    return "(" + ", ".join(str(c) for c in v) + ")"


def texto_frenet(C: CurvaFrenet, ascii_: bool = False, detalle: bool = True) -> str:
    L = "=" * 78
    t = C.t
    s = [L, " TRIEDRO DE FRENET · CURVATURA · TORSIÓN", L, f"r({t}) = {_vt(C.r)}      t0 = {C.t0}"]
    if C.constantes:
        s.append("constantes (positivas): " + ", ".join(map(str, C.constantes)) +
                 "   valores usados en gráficos: " + ", ".join(f"{k}={v:g}" for k, v in C.valores.items()))
    s += ["", "1) Derivadas:", f"   r'   = {_vt(C.d1)}", f"   r''  = {_vt(C.d2)}", f"   r''' = {_vt(C.d3)}",
          "", "2) Rapidez  ‖r'‖ =", _bl(_pp(C.rapidez, ascii_))]
    if C.s_t is not None:
        s.append(f"   Longitud de arco desde t0:  s({t}) = {C.s_t}")
    s += ["", "3) r' × r'' = " + _vt(C.cruz), "   ‖r' × r''‖ =", _bl(_pp(C.norma_cruz, ascii_)),
          f"   (r' × r'') · r''' = {C.triple}", "", "4) Triedro de Frenet (general):"]
    if detalle:
        s += ["   T =", _bl(_pp(C.T.T, ascii_), "      ")]
        if not C.recta:
            s += ["   N =", _bl(_pp(C.N.T, ascii_), "      "), "   B =", _bl(_pp(C.B.T, ascii_), "      ")]
    s += ["", "5) Curvatura  κ = ‖r'×r''‖/‖r'‖³ =", _bl(_pp(C.kappa, ascii_))]
    if not C.recta:
        s += ["   Torsión  τ = (r'×r'')·r'''/‖r'×r''‖² =", _bl(_pp(C.tau, ascii_))]
    E = C.en_t0
    s += ["", f"6) En t0 = {C.t0}:", f"   r(t0)   = {_vt(E['r'])}"]
    if "T" in E:
        s.append(f"   ‖r'(t0)‖ = {E['rapidez']}")
        s.append(f"   T(t0) = {_vt(E['T'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['T'].subs(C.valores)))}")
    if "N" in E:
        s += [f"   N(t0) = {_vt(E['N'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['N'].subs(C.valores)))}",
              f"   B(t0) = {_vt(E['B'])}   ≈ {tuple(round(q, 5) for q in _vnum(E['B'].subs(C.valores)))}",
              f"   κ(t0) = {E['kappa']}   ≈ {_num(E['kappa'].subs(C.valores)):.8g}",
              f"   τ(t0) = {E['tau']}   ≈ {_num(E['tau'].subs(C.valores)):.8g}",
              f"   radio de curvatura ρ = {E['rho']},  centro de curvatura C = {_vt(E['centro'])}",
              "", "7) Planos en t0:",
              f"   osculador    (⟂ B): {E['plano_osculador']['lhs']} = {E['plano_osculador']['rhs']}",
              f"   normal       (⟂ T): {E['plano_normal']['lhs']} = {E['plano_normal']['rhs']}",
              f"   rectificante (⟂ N): {E['plano_rectificante']['lhs']} = {E['plano_rectificante']['rhs']}"]
    elif "plano_normal" in E:
        s += [f"   plano normal (⟂ T): {E['plano_normal']['lhs']} = {E['plano_normal']['rhs']}"]
    V = C.verificacion
    if V.get("frenet_serret_t0"):
        s += ["", "8) Verificación de Frenet–Serret (50 dígitos):"]
        for k, e in V["frenet_serret_t0"].items():
            s.append(f"   {k:<22} error = {e:.1e}  {'✔' if e < 1e-25 else '✘'}")
        s.append("   ortonormalidad: " + ("✔ T, N, B ortonormales y T × N = B" if V.get("correcto") else "revisar"))
    s += ["", f"9) Clasificación: {C.tipo.upper()}"] + [f"   • {c}" for c in C.clasificacion]
    for a in C.advertencias:
        s.append(f"⚠ {a}")
    s.append(L)
    return "\n".join(s)


def texto(metodo: Metodo, objeto: Any, ascii_: bool = False, detalle: bool = True) -> str:
    """Despachador del reporte de terminal."""
    fn = {"lagrange": texto_lagrange, "hessiana": texto_hessiana, "frenet": texto_frenet}[metodo]
    return fn(objeto, ascii_=ascii_, detalle=detalle)
