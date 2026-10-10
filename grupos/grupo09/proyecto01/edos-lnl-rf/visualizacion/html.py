"""Visualizaciones HTML interactivas con plotly.

La propuesta del grupo pide las visualizaciones en HTML, no en PNG: este es el
único módulo de visualización del agente.

Cada función devuelve una figura de plotly; `generar_html` las compone en un
documento autocontenido. La malla se submuestrea antes de dibujar: una
trayectoria de Lorenz con 20 000 puntos produce megabytes de JSON que no
aportan nada visible y que inflarían el informe que se sube al storage.
"""

import html as _html
import math

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from plotly.offline.offline import get_plotlyjs_version

#: `pio.to_html(..., include_plotlyjs="cdn")` enlaza por defecto a
#: `cdn.plot.ly`, que no figura entre los CDN que un artifact puede cargar
#: (cdnjs, jsDelivr, unpkg). Se fija aquí la URL exacta en jsDelivr, con la
#: misma versión de plotly.js que esta versión de plotly.py espera — jsDelivr
#: espeja el paquete "plotly.js" de npm versión a versión, así que no hace
#: falta adivinar si cdnjs tiene ese build en concreto.
URL_PLOTLY_JS = (f"https://cdn.jsdelivr.net/npm/plotly.js@{get_plotlyjs_version()}"
                 f"/dist/plotly.min.js")

#: Puntos máximos por traza. Por encima, se submuestrea de forma uniforme.
MAXIMO_PUNTOS_TRAZA = 2000

#: Cada traza declara QUE ES, no de que color va: el color lo pone la pagina
#: al dibujarla, leyendolo de su propio CSS. Asi la paleta vive en un solo
#: sitio y la misma figura se ve bien en claro y en oscuro, que con un color
#: fijo cocinado aqui seria imposible.
#:
#: Roles: "serie:<i>" una variable de estado - "campo" el campo de
#: direcciones - "trayectoria" - "inicio" / "final" sus extremos -
#: "equilibrio:<estado>" - "crece" / "decrece" las flechas de la linea de fase.
def _rol(nombre):
    return {"rol": nombre}


def _estado(clasificacion):
    """Estable, inestable o indefinido, a partir del texto de la clasificacion."""
    texto = str(clasificacion or "")
    if texto.startswith("estable"):
        return "estable"
    if texto.startswith("inestable"):
        return "inestable"
    return "indefinido"


def _simbolo(clasificacion):
    """Forma del marcador de un equilibrio.

    El verde y el rojo que separan estable de inestable quedan en la banda de
    advertencia para daltonismo deutan, asi que el color NO puede ir solo: un
    disco lleno para lo estable, un aspa para lo inestable y un rombo hueco
    para lo que no se puede concluir.
    """
    return {"estable": "circle", "inestable": "x",
            "indefinido": "diamond-open"}[_estado(clasificacion)]


#: Diseno neutro: sin `template`, para que la pagina mande en fondo, rejilla y
#: tipografia. Lo que se fija aqui es geometria, no apariencia.
_DISENO = {
    "margin": {"l": 62, "r": 24, "t": 54, "b": 48},
    "hovermode": "x unified",
}


def _submuestrear(tiempos, estados, maximo=MAXIMO_PUNTOS_TRAZA):
    """Reduce la malla conservando siempre el primer y el último punto."""
    tiempos = np.asarray(tiempos, dtype=float)
    estados = np.asarray(estados, dtype=float)
    if tiempos.size <= maximo:
        return tiempos, estados
    paso = int(np.ceil(tiempos.size / maximo))
    indices = np.unique(np.append(np.arange(0, tiempos.size, paso), tiempos.size - 1))
    return tiempos[indices], estados[:, indices]


def _lista(valores):
    """Convierte a lista plana de Python antes de pasarla a una traza.

    Un array de numpy hace que plotly.py codifique la serie como `bdata`
    binario en base64 dentro del HTML. Es más compacto, pero ese texto no
    tokeniza como lenguaje natural: si alguien tiene que reproducirlo a mano
    (por ejemplo, para publicarlo como artifact fuera de este servidor), un
    solo carácter mal puesto corrompe el array sin avisar. Una lista plana
    serializa como JSON normal, legible y seguro de volver a transcribir.
    """
    return np.asarray(valores).tolist()


def figura_series(tiempos, estados, variables, titulo="Solución numérica",
                  variable_independiente="t", maximo=MAXIMO_PUNTOS_TRAZA):
    """Serie temporal de cada variable de estado."""
    tiempos, estados = _submuestrear(tiempos, estados, maximo)
    figura = go.Figure()
    tiempos_lista = _lista(tiempos)
    for i, nombre in enumerate(variables):
        figura.add_trace(go.Scatter(
            x=tiempos_lista, y=_lista(estados[i]), mode="lines", name=nombre,
            meta=_rol("serie:%d" % i), line={"width": 2}))
    figura.update_layout(title=titulo, xaxis_title=variable_independiente,
                         yaxis_title="Estado", **_DISENO)
    return figura


def figura_linea_fase(campo, estados, parametros, variables, equilibrios=()):
    """Línea de fase 1D: signo del campo, flechas de dirección y equilibrios."""
    valores_estado = np.asarray(estados, dtype=float)[0]
    minimo, maximo = float(valores_estado.min()), float(valores_estado.max())
    if maximo - minimo < 1e-12:
        minimo, maximo = minimo - 1.0, maximo + 1.0
    margen = 0.25 * (maximo - minimo)
    malla = np.linspace(minimo - margen, maximo + margen, 220)
    derivada = np.array([float(np.atleast_1d(campo(0.0, [x], parametros))[0]) for x in malla])

    figura = go.Figure()
    figura.add_trace(go.Scatter(
        x=_lista(malla), y=_lista(derivada), mode="lines", name="F(x)",
        meta=_rol("serie:0"), line={"width": 2}))
    figura.add_hline(y=0, line={"width": 1, "dash": "dot"})
    figura.add_trace(go.Scatter(
        x=_lista(malla[derivada > 0]), y=[0.0] * int((derivada > 0).sum()),
        mode="markers", name="F > 0: x crece", meta=_rol("crece"),
        marker={"symbol": "triangle-right", "size": 9}))
    figura.add_trace(go.Scatter(
        x=_lista(malla[derivada < 0]), y=[0.0] * int((derivada < 0).sum()),
        mode="markers", name="F < 0: x decrece", meta=_rol("decrece"),
        marker={"symbol": "triangle-left", "size": 9}))
    for equilibrio in equilibrios:
        x = float(np.atleast_1d(equilibrio["equilibrio"])[0])
        clasificacion = equilibrio.get("clasificacion", "")
        figura.add_trace(go.Scatter(
            x=[x], y=[0.0], mode="markers+text",
            name=f"x={x:g} ({clasificacion or '?'})",
            meta=_rol(f"equilibrio:{_estado(clasificacion)}"),
            text=[f"x={x:g}"], textposition="top center",
            marker={"size": 15, "symbol": _simbolo(clasificacion),
                    "line": {"width": 2}}))
    figura.update_layout(title="Línea de fase: hacia dónde evoluciona el estado",
                         xaxis_title=variables[0], yaxis_title="F(x)", **_DISENO)
    return figura


def figura_plano_fase(campo, tiempos, estados, parametros, variables, equilibrios=(),
                      maximo=MAXIMO_PUNTOS_TRAZA):
    """Plano de fase 2D: trayectoria, campo de direcciones y equilibrios."""
    _, estados = _submuestrear(tiempos, estados, maximo)
    x, y = estados[0], estados[1]
    figura = go.Figure()

    # Campo de direcciones normalizado, como segmentos cortos.
    rango_x = (float(x.min()), float(x.max()))
    rango_y = (float(y.min()), float(y.max()))
    margen_x = 0.15 * max(rango_x[1] - rango_x[0], 1e-9)
    margen_y = 0.15 * max(rango_y[1] - rango_y[0], 1e-9)
    malla_x = np.linspace(rango_x[0] - margen_x, rango_x[1] + margen_x, 16)
    malla_y = np.linspace(rango_y[0] - margen_y, rango_y[1] + margen_y, 16)
    paso = 0.4 * min(malla_x[1] - malla_x[0], malla_y[1] - malla_y[0])
    segmentos_x, segmentos_y = [], []
    for px in malla_x:
        for py in malla_y:
            derivada = np.asarray(campo(float(tiempos[0]), [px, py], parametros), dtype=float)
            norma = float(np.hypot(derivada[0], derivada[1]))
            if norma < 1e-12:
                continue
            dx, dy = derivada[0] / norma * paso, derivada[1] / norma * paso
            segmentos_x += [px - dx / 2, px + dx / 2, None]
            segmentos_y += [py - dy / 2, py + dy / 2, None]
    figura.add_trace(go.Scatter(x=segmentos_x, y=segmentos_y, mode="lines",
                                name="Campo de direcciones", hoverinfo="skip",
                                meta=_rol("campo"), line={"width": 1}))
    figura.add_trace(go.Scatter(x=_lista(x), y=_lista(y), mode="lines",
                                name="Trayectoria", meta=_rol("trayectoria"),
                                line={"width": 2}))
    figura.add_trace(go.Scatter(x=[float(x[0])], y=[float(y[0])], mode="markers",
                                name="Inicio", meta=_rol("inicio"),
                                marker={"size": 12, "line": {"width": 2}}))
    figura.add_trace(go.Scatter(x=[float(x[-1])], y=[float(y[-1])], mode="markers",
                                name="Final", meta=_rol("final"),
                                marker={"size": 12, "symbol": "square",
                                        "line": {"width": 2}}))
    for equilibrio in equilibrios:
        punto = np.atleast_1d(np.asarray(equilibrio["equilibrio"], dtype=float))
        if punto.size < 2:
            continue
        clasificacion = equilibrio.get("clasificacion", "")
        figura.add_trace(go.Scatter(
            x=[punto[0]], y=[punto[1]], mode="markers",
            name=f"Equilibrio {clasificacion or '?'}",
            meta=_rol(f"equilibrio:{_estado(clasificacion)}"),
            marker={"size": 15, "symbol": _simbolo(clasificacion),
                    "line": {"width": 2}}))
    figura.update_layout(title="Retrato de fase", xaxis_title=variables[0],
                         yaxis_title=variables[1], **_DISENO)
    return figura


def figura_trayectoria_3d(tiempos, estados, variables,
                          titulo="Trayectoria en el espacio de fases",
                          maximo=MAXIMO_PUNTOS_TRAZA):
    """Trayectoria 3D, coloreada por tiempo para distinguir el transitorio."""
    tiempos, estados = _submuestrear(tiempos, estados, maximo)
    figura = go.Figure(go.Scatter3d(
        x=_lista(estados[0]), y=_lista(estados[1]), z=_lista(estados[2]),
        mode="lines",
        line={"color": _lista(tiempos), "colorscale": "Viridis", "width": 4,
              "colorbar": {"title": "t", "thickness": 12, "outlinewidth": 0}},
        meta=_rol("trayectoria3d"), name="Trayectoria"))
    figura.add_trace(go.Scatter3d(
        x=[float(estados[0, 0])], y=[float(estados[1, 0])], z=[float(estados[2, 0])],
        mode="markers", name="Inicio", meta=_rol("inicio"),
        marker={"size": 6, "line": {"width": 2}}))
    figura.update_layout(title=titulo, **{k: v for k, v in _DISENO.items()
                                          if k != "hovermode"},
                         scene={"xaxis_title": variables[0],
                                "yaxis_title": variables[1],
                                "zaxis_title": variables[2]})
    return figura


def construir_figuras(campo, tiempos, estados, parametros, variables,
                      equilibrios=(), titulo=None, variable_independiente="t",
                      maximo=MAXIMO_PUNTOS_TRAZA):
    """Elige las figuras según la dimensión del sistema."""
    estados = np.asarray(estados, dtype=float)
    dimension = estados.shape[0]
    figuras = [("series", figura_series(tiempos, estados, variables,
                                        titulo or "Solución numérica",
                                        variable_independiente, maximo))]
    try:
        if dimension == 1:
            figuras.append(("linea_fase",
                            figura_linea_fase(campo, estados, parametros, variables,
                                              equilibrios)))
        elif dimension == 2:
            figuras.append(("plano_fase",
                            figura_plano_fase(campo, tiempos, estados, parametros,
                                              variables, equilibrios, maximo)))
        elif dimension == 3:
            figuras.append(("trayectoria_3d",
                            figura_trayectoria_3d(tiempos, estados, variables,
                                                  maximo=maximo)))
    except Exception as exc:                 # una figura no debe tumbar el análisis
        figuras.append(("error_retrato", exc))
    return figuras


# ---------------------------------------------------------------------------
# Figuras del desarrollo matemático
# ---------------------------------------------------------------------------
#
# Las familias de `matematica` describen sus gráficas como datos con sentido
# (una rama estable, una separatriz, una nulclina), sin saber nada de plotly.
# Aquí cada capa se vuelve una traza que declara su rol; el color lo pone la
# plantilla, como en las figuras numéricas.

#: Trazo discontinuo para lo que no es un estado observable (ramas inestables,
#: fronteras de una región, curvas de referencia).
_TRAZO = {"rama:inestable": "dash", "frontera": "dot", "referencia": "dash", "asintota": "dash",
          "direccion": "dot", "lazo": "dashdot", "diagonal": "dot"}

#: Grosor por rol: lo que el problema pregunta va más grueso que el contexto.
_GROSOR = {"campo": 1, "orbita": 1.2, "nivel": 1, "familia": 1.4, "telarana": 1.3,
           "separatriz": 3, "ciclo": 3, "lazo": 2.6, "analitica": 2.8, "rama:estable": 3,
           "rama:inestable": 2.6, "variedad_estable": 2.4, "variedad_inestable": 2.4}

#: Forma de los marcadores. El color no va solo (estable/inestable caen en la
#: banda de advertencia para daltonismo deutan): la forma también cambia.
_MARCADOR = {"critico": "star", "condicion_inicial": "circle-open", "numerica": "circle",
             "crece": "triangle-up", "decrece": "triangle-down"}


def _redondear(valores, cifras=6):
    """Menos cifras, menos bytes: el ojo no distingue la séptima cifra de un trazo."""
    salida = []
    for v in valores:
        if v is None or (isinstance(v, float) and not math.isfinite(v)):
            salida.append(None)
        else:
            salida.append(float(f"{float(v):.{cifras}g}"))
    return salida


def _traza(capa, rango_y):
    rol = capa.get("rol", "")
    tipo = capa.get("tipo", "linea")
    nombre = capa.get("nombre", rol)
    meta = _rol(rol)
    if tipo == "linea":
        modo = "lines+markers" if capa.get("marcadores") else "lines"
        return go.Scatter(x=_redondear(capa["x"]), y=_redondear(capa["y"]), mode=modo, name=nombre,
                          meta=meta, connectgaps=False, hoverinfo="skip" if rol in ("campo", "nivel") else None,
                          line={"width": _GROSOR.get(rol, 2), "dash": _TRAZO.get(rol, "solid")})
    if tipo == "puntos":
        simbolo = capa.get("simbolo") or _MARCADOR.get(rol)
        if simbolo is None and rol.startswith("equilibrio:"):
            simbolo = _simbolo(rol.split(":", 1)[1])
        tamano = capa.get("tamano") or (9 if rol in ("crece", "decrece", "numerica") else 13)
        texto = capa.get("etiquetas")
        # Una nube densa (diagrama de bifurcación, atractor) va en WebGL, con
        # puntos pequeños y sin aro: miles de marcadores SVG ahogan la página.
        nube = tamano <= 4 and len(capa["x"]) > 1500
        clase = go.Scattergl if nube else go.Scatter
        return clase(x=_redondear(capa["x"], 5 if nube else 6), y=_redondear(capa["y"], 5 if nube else 6),
                     mode="markers+text" if texto else "markers", name=nombre, meta=meta,
                     text=texto, textposition="top right", hoverinfo="skip" if nube else None,
                     marker={"size": tamano, "symbol": simbolo or "circle",
                             "line": {"width": 0 if tamano <= 4 else 2}})
    if tipo in ("linea3d", "puntos3d"):
        linea = tipo == "linea3d"
        return go.Scatter3d(x=_redondear(capa["x"]), y=_redondear(capa["y"]), z=_redondear(capa["z"]),
                            mode="lines" if linea else "markers", name=nombre, meta=meta,
                            line={"width": 2} if linea else None,
                            marker=None if linea else {"size": capa.get("tamano") or 3, "line": {"width": 0}})
    if tipo == "contorno":
        return go.Contour(x=_redondear(capa["x"]), y=_redondear(capa["y"]),
                          z=[_redondear(fila) for fila in capa["z"]], name=nombre, meta=meta,
                          contours={"coloring": "lines"}, ncontours=26, showscale=False,
                          line={"width": 1}, hoverinfo="skip")
    if tipo == "vertical":
        bajo, alto = rango_y or (-1.0, 1.0)
        return go.Scatter(x=[capa["x"], capa["x"]], y=[bajo, alto], mode="lines", name=nombre,
                          meta=meta, line={"width": 1.6, "dash": _TRAZO.get(rol, "dash")})
    if tipo == "banda":
        bajo, alto = rango_y or (-1.0, 1.0)
        x0, x1 = capa["x0"], capa["x1"]
        return go.Scatter(x=[x0, x1, x1, x0, x0], y=[bajo, bajo, alto, alto, bajo], mode="lines",
                          fill="toself", name=nombre, meta=meta, line={"width": 0}, hoverinfo="skip")
    raise ValueError(f"Tipo de capa desconocido: {tipo!r}")


def figura_de_especificacion(especificacion):
    """Una figura de plotly a partir de la especificación que produce una familia."""
    rango = especificacion.get("rango") or {}
    rango_y = rango.get("y")
    if rango_y is None:
        valores = [v for c in especificacion["capas"] if c.get("tipo") in ("linea", "puntos")
                   for v in c.get("y", []) if v is not None and math.isfinite(v)]
        rango_y = [min(valores), max(valores)] if valores else None
    figura = go.Figure()
    for capa in especificacion["capas"]:
        figura.add_trace(_traza(capa, rango_y))
    ejes = especificacion.get("ejes", {})
    if any(c.get("tipo") in ("linea3d", "puntos3d") for c in especificacion["capas"]):
        figura.update_layout(title=especificacion.get("titulo", ""),
                             **{k: v for k, v in _DISENO.items() if k != "hovermode"},
                             scene={"xaxis_title": ejes.get("x", ""), "yaxis_title": ejes.get("y", ""),
                                    "zaxis_title": ejes.get("z", "")})
        return figura
    diseno = dict(_DISENO, hovermode="closest")
    figura.update_layout(title=especificacion.get("titulo", ""), xaxis_title=ejes.get("x", ""),
                         yaxis_title=ejes.get("y", ""), **diseno)
    if rango.get("x"):
        figura.update_xaxes(range=list(rango["x"]))
    if rango.get("y") and especificacion.get("escala_y") != "log":
        figura.update_yaxes(range=list(rango["y"]))
    if especificacion.get("escala_y") == "log":
        figura.update_yaxes(type="log")
    if especificacion.get("cuadrada"):
        figura.update_yaxes(scaleanchor="x", scaleratio=1)
    return figura


def figuras_del_desarrollo(graficas):
    """[(clave, figura)] de las gráficas de un desarrollo. Una que falla no tumba al resto."""
    figuras = []
    for especificacion in graficas or []:
        try:
            figuras.append((especificacion.get("clave", "figura"), figura_de_especificacion(especificacion)))
        except Exception as exc:
            figuras.append((especificacion.get("clave", "figura"), exc))
    return figuras


def bloques_de_figuras(campo, tiempos, estados, parametros, variables,
                       equilibrios=(), titulo=None, variable_independiente="t",
                       maximo_puntos=MAXIMO_PUNTOS_TRAZA, incluir_plotly="cdn"):
    """Los `<div>` de cada figura, sin el documento que los envuelve.

    Separado de `generar_html` porque el informe de sesión compone **varias**
    tandas de figuras en una sola página, y la librería de plotly solo puede ir
    una vez por documento: quien compone decide en qué bloque la incluye. Pasar
    `incluir_plotly=False` devuelve los `<div>` sin ella.

    Devuelve `bloques` (HTML), `generadas` (nombres) y `fallidas` (la figura que
    no se pudo dibujar no tumba al resto del análisis).
    """
    if incluir_plotly == "cdn":
        incluir_plotly = URL_PLOTLY_JS
    figuras = construir_figuras(campo, tiempos, estados, parametros, variables,
                                equilibrios, titulo, variable_independiente,
                                maximo_puntos)
    bloques, generadas, fallidas = [], [], []
    primera = True
    for nombre, figura in figuras:
        if isinstance(figura, Exception):
            fallidas.append({"figura": nombre, "error": str(figura)})
            continue
        bloques.append(pio.to_html(
            figura, full_html=False,
            include_plotlyjs=(incluir_plotly if (primera and incluir_plotly) else False),
            config={"displaylogo": False, "responsive": True}))
        generadas.append(nombre)
        primera = False
    return {"bloques": bloques, "generadas": generadas, "fallidas": fallidas}


def generar_html(campo, tiempos, estados, parametros, variables, equilibrios=(),
                 titulo=None, variable_independiente="t", incluir_plotly="cdn",
                 maximo_puntos=MAXIMO_PUNTOS_TRAZA):
    """Documento HTML autocontenido con todas las figuras del análisis.

    `incluir_plotly="cdn"` (por defecto) enlaza `URL_PLOTLY_JS`: el documento
    pesa unos pocos KB en vez de varios MB, y el host es uno que un cliente
    puede cargar al publicar este HTML como artifact. Con `"inline"` la
    librería completa queda embebida, utilizable sin red.
    """
    render = bloques_de_figuras(campo, tiempos, estados, parametros, variables,
                                equilibrios, titulo, variable_independiente,
                                maximo_puntos, incluir_plotly)
    bloques, generadas, fallidas = render["bloques"], render["generadas"], render["fallidas"]

    # El título y los nombres de variable llegan del cliente MCP, y este
    # documento se publica en una URL pública del lab: sin escapar, un título
    # con `</title><script>` se ejecuta en el navegador de quien lo abra.
    encabezado = _html.escape(titulo or "Análisis de EDO")
    variables_texto = ", ".join(_html.escape(str(v)) for v in variables)
    parametros_texto = ", ".join(f"{_html.escape(str(k))}={v:g}"
                                 for k, v in (parametros or {}).items())
    documento = (
        "<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{encabezado}</title>\n<style>\n"
        "body{margin:0;padding:24px;background:#f8fafc;color:#0f172a;"
        "font:14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}\n"
        "h1{font-size:20px;margin:0 0 4px}\n"
        "p.meta{color:#475569;margin:0 0 20px;font-size:13px}\n"
        ".figura{background:#fff;border:1px solid #e2e8f0;border-radius:10px;"
        "padding:8px;margin-bottom:20px;overflow-x:auto}\n"
        "</style>\n</head>\n<body>\n"
        f"<h1>{encabezado}</h1>\n"
        f"<p class=\"meta\">Variables: {variables_texto}"
        f"{' &middot; Parámetros: ' + parametros_texto if parametros_texto else ''}"
        f" &middot; {len(np.asarray(tiempos))} puntos</p>\n"
        + "\n".join(f"<div class=\"figura\">{bloque}</div>" for bloque in bloques)
        + "\n</body>\n</html>\n")
    return {"html": documento, "figuras": generadas, "fallidas": fallidas,
            "bytes": len(documento.encode("utf-8")),
            "puntos_por_traza": maximo_puntos}
