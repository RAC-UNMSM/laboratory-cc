"""Generacion de graficos autocontenidos para resultados numericos."""

from __future__ import annotations

import html
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from resultado import ResultadoMetodo


_COLORES = ("#146c5a", "#c04b35", "#2864a5", "#b47613", "#68459a")


def _obtener_campo(resultado: ResultadoMetodo | Mapping[str, Any], nombre: str, default: Any = None) -> Any:
    if isinstance(resultado, Mapping):
        return resultado.get(nombre, default)
    return getattr(resultado, nombre, default)


def _normalizar_trayectoria(resultado: ResultadoMetodo | Mapping[str, Any]) -> list[list[float]]:
    trayectoria = _obtener_campo(resultado, "trajectory", [])
    if trayectoria is None:
        return []
    if isinstance(trayectoria, (str, bytes)) or not isinstance(trayectoria, Sequence):
        raise ValueError("La trayectoria debe ser una secuencia de vectores.")

    normalizada: list[list[float]] = []
    dimension: int | None = None
    for indice, punto in enumerate(trayectoria):
        if isinstance(punto, (str, bytes)) or not isinstance(punto, Sequence) or not punto:
            raise ValueError(f"El punto {indice} de la trayectoria debe ser un vector no vacio.")
        try:
            vector = [float(valor) for valor in punto]
        except (TypeError, ValueError) as error:
            raise ValueError(f"El punto {indice} contiene un valor no numerico.") from error
        if not all(math.isfinite(valor) for valor in vector):
            raise ValueError(f"El punto {indice} contiene un valor no finito.")
        if dimension is None:
            dimension = len(vector)
        elif len(vector) != dimension:
            raise ValueError("Todos los puntos de la trayectoria deben tener la misma dimension.")
        normalizada.append(vector)
    return normalizada


def _formatear_numero(valor: float) -> str:
    return f"{valor:.4g}"


def generar_grafico_trayectoria(
    resultado: ResultadoMetodo | Mapping[str, Any],
    titulo: str = "Trayectoria de iteraciones",
) -> str:
    """Devuelve un SVG con una serie por cada variable del sistema."""
    trayectoria = _normalizar_trayectoria(resultado)
    if not trayectoria:
        return ""

    ancho, alto = 800, 440
    izquierda, derecha, arriba, abajo = 76, 24, 48, 58
    ancho_grafico = ancho - izquierda - derecha
    alto_grafico = alto - arriba - abajo
    valores = [valor for punto in trayectoria for valor in punto]
    minimo, maximo = min(valores), max(valores)
    if minimo == maximo:
        margen = max(abs(minimo) * 0.1, 1.0)
    else:
        margen = (maximo - minimo) * 0.08
    minimo -= margen
    maximo += margen

    def coordenada_x(indice: int) -> float:
        if len(trayectoria) == 1:
            return izquierda + ancho_grafico / 2
        return izquierda + indice * ancho_grafico / (len(trayectoria) - 1)

    def coordenada_y(valor: float) -> float:
        return arriba + (maximo - valor) * alto_grafico / (maximo - minimo)

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'role="img" aria-label="{html.escape(titulo, quote=True)}">',
        f'<title>{html.escape(titulo)}</title>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    for indice in range(5):
        proporcion = indice / 4
        y = arriba + proporcion * alto_grafico
        valor = maximo - proporcion * (maximo - minimo)
        partes.append(
            f'<line x1="{izquierda}" y1="{y:.2f}" x2="{ancho - derecha}" y2="{y:.2f}" '
            'stroke="#dce4e1" stroke-width="1"/>'
        )
        partes.append(
            f'<text x="{izquierda - 10}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="12" fill="#53615c">{_formatear_numero(valor)}</text>'
        )

    partes.extend(
        [
            f'<line x1="{izquierda}" y1="{arriba}" x2="{izquierda}" '
            f'y2="{alto - abajo}" stroke="#65736d"/>',
            f'<line x1="{izquierda}" y1="{alto - abajo}" x2="{ancho - derecha}" '
            f'y2="{alto - abajo}" stroke="#65736d"/>',
            f'<text x="{izquierda + ancho_grafico / 2:.2f}" y="{alto - 14}" '
            'text-anchor="middle" font-size="13" fill="#34423c">Iteracion</text>',
        ]
    )

    dimension = len(trayectoria[0])
    for variable in range(dimension):
        color = _COLORES[variable % len(_COLORES)]
        puntos = [
            (coordenada_x(indice), coordenada_y(punto[variable]))
            for indice, punto in enumerate(trayectoria)
        ]
        coordenadas = " ".join(f"{x:.2f},{y:.2f}" for x, y in puntos)
        partes.append(
            f'<polyline points="{coordenadas}" fill="none" stroke="{color}" '
            'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        for indice, (x, y) in enumerate(puntos):
            texto = html.escape(
                f"Iteracion {indice}; x{variable + 1} = "
                f"{_formatear_numero(trayectoria[indice][variable])}"
            )
            partes.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}">'
                f"<title>{texto}</title></circle>"
            )
        leyenda_x = izquierda + variable * 112
        partes.extend(
            [
                f'<line x1="{leyenda_x}" y1="24" x2="{leyenda_x + 18}" y2="24" '
                f'stroke="{color}" stroke-width="3"/>',
                f'<text x="{leyenda_x + 24}" y="28" font-size="12" '
                f'fill="#34423c">x{variable + 1}</text>',
            ]
        )

    partes.append("</svg>")
    return "\n".join(partes)


def generar_visualizacion_html(
    resultado: ResultadoMetodo | Mapping[str, Any],
    titulo: str = "Visualizacion del metodo numerico",
) -> str:
    """Construye una pagina HTML independiente con el grafico de trayectoria."""
    grafico = generar_grafico_trayectoria(resultado)
    contenido = grafico or '<p class="empty">No hay trayectoria disponible para graficar.</p>'
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(titulo)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Georgia, 'Times New Roman', serif; color: #20342d; }}
    body {{ margin: 0; padding: 2rem; background: #f2f5f2; }}
    main {{ max-width: 900px; margin: 0 auto; }}
    h1 {{ font-size: 1.6rem; font-weight: 500; }}
    figure {{ margin: 1.5rem 0; padding: 1rem; background: #fff; border: 1px solid #dce4e1; }}
    svg {{ display: block; width: 100%; height: auto; }}
    .empty {{ padding: 2rem; background: #fff; border-left: 3px solid #b47613; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(titulo)}</h1>
    <figure aria-label="Grafico de la trayectoria de iteraciones">{contenido}</figure>
  </main>
</body>
</html>
"""


def guardar_visualizacion_html(
    resultado: ResultadoMetodo | Mapping[str, Any],
    ruta: str | Path,
    titulo: str = "Visualizacion del metodo numerico",
) -> Path:
    """Guarda la visualizacion HTML y devuelve la ruta escrita."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(generar_visualizacion_html(resultado, titulo), encoding="utf-8")
    return destino