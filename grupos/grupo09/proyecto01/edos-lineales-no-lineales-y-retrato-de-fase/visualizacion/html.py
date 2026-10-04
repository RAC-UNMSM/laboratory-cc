"""Visualizaciones HTML interactivas con plotly.

La propuesta del grupo pide las visualizaciones en HTML, no en PNG: este es el
único módulo de visualización del agente.

Cada función devuelve una figura de plotly; `generar_html` las compone en un
documento autocontenido. La malla se submuestrea antes de dibujar: una
trayectoria de Lorenz con 20 000 puntos produce megabytes de JSON que no
aportan nada visible y que tendrían que viajar por el transporte stdio.
"""

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

#: Colores con suficiente contraste en fondo claro y oscuro.
PALETA = ("#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed")

_DISENO = {
    "template": "plotly_white",
    "margin": {"l": 60, "r": 20, "t": 60, "b": 50},
    "hovermode": "x unified",
    "font": {"size": 13},
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
            line={"color": PALETA[i % len(PALETA)], "width": 2}))
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
        line={"color": PALETA[0], "width": 2}))
    figura.add_hline(y=0, line={"color": "#64748b", "width": 1, "dash": "dot"})
    figura.add_trace(go.Scatter(
        x=_lista(malla[derivada > 0]), y=[0.0] * int((derivada > 0).sum()),
        mode="markers", name="F > 0: x crece",
        marker={"symbol": "triangle-right", "size": 7, "color": "#059669"}))
    figura.add_trace(go.Scatter(
        x=_lista(malla[derivada < 0]), y=[0.0] * int((derivada < 0).sum()),
        mode="markers", name="F < 0: x decrece",
        marker={"symbol": "triangle-left", "size": 7, "color": "#dc2626"}))
    for equilibrio in equilibrios:
        x = float(np.atleast_1d(equilibrio["equilibrio"])[0])
        estable = equilibrio.get("clasificacion", "").startswith("estable")
        figura.add_trace(go.Scatter(
            x=[x], y=[0.0], mode="markers+text",
            name=f"x={x:g} ({equilibrio.get('clasificacion', '?')})",
            text=[f"x={x:g}"], textposition="top center",
            marker={"size": 14, "color": "#059669" if estable else "#dc2626",
                    "line": {"width": 2, "color": "white"}}))
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
                                line={"color": "#cbd5e1", "width": 1}))
    figura.add_trace(go.Scatter(x=_lista(x), y=_lista(y), mode="lines",
                                name="Trayectoria",
                                line={"color": PALETA[0], "width": 2}))
    figura.add_trace(go.Scatter(x=[float(x[0])], y=[float(y[0])], mode="markers",
                                name="Inicio", marker={"size": 11, "color": "#059669"}))
    figura.add_trace(go.Scatter(x=[float(x[-1])], y=[float(y[-1])], mode="markers",
                                name="Final", marker={"size": 11, "color": "#dc2626",
                                                       "symbol": "square"}))
    for equilibrio in equilibrios:
        punto = np.atleast_1d(np.asarray(equilibrio["equilibrio"], dtype=float))
        if punto.size < 2:
            continue
        estable = equilibrio.get("clasificacion", "").startswith("estable")
        figura.add_trace(go.Scatter(
            x=[punto[0]], y=[punto[1]], mode="markers",
            name=f"Equilibrio {equilibrio.get('clasificacion', '?')}",
            marker={"size": 14, "symbol": "x",
                    "color": "#059669" if estable else "#dc2626"}))
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
        line={"color": _lista(tiempos), "colorscale": "Viridis", "width": 3,
              "colorbar": {"title": "t", "thickness": 14}},
        name="Trayectoria"))
    figura.add_trace(go.Scatter3d(
        x=[float(estados[0, 0])], y=[float(estados[1, 0])], z=[float(estados[2, 0])],
        mode="markers", name="Inicio", marker={"size": 5, "color": "#059669"}))
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


def generar_html(campo, tiempos, estados, parametros, variables, equilibrios=(),
                 titulo=None, variable_independiente="t", incluir_plotly="cdn",
                 maximo_puntos=MAXIMO_PUNTOS_TRAZA):
    """Documento HTML autocontenido con todas las figuras del análisis.

    `incluir_plotly="cdn"` (por defecto) enlaza `URL_PLOTLY_JS`: el documento
    pesa unos pocos KB en vez de varios MB, y el host es uno que un cliente
    puede cargar al publicar este HTML como artifact. Con `"inline"` la
    librería completa queda embebida, utilizable sin red.
    """
    incluir_plotly = URL_PLOTLY_JS if incluir_plotly == "cdn" else incluir_plotly
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
            include_plotlyjs=(incluir_plotly if primera else False),
            config={"displaylogo": False, "responsive": True}))
        generadas.append(nombre)
        primera = False

    encabezado = titulo or "Análisis de EDO"
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
        f"<p class=\"meta\">Variables: {', '.join(variables)}"
        f"{' &middot; Parámetros: ' + ', '.join(f'{k}={v:g}' for k, v in parametros.items()) if parametros else ''}"
        f" &middot; {len(np.asarray(tiempos))} puntos</p>\n"
        + "\n".join(f"<div class=\"figura\">{bloque}</div>" for bloque in bloques)
        + "\n</body>\n</html>\n")
    return {"html": documento, "figuras": generadas, "fallidas": fallidas,
            "bytes": len(documento.encode("utf-8")),
            "puntos_por_traza": maximo_puntos}
