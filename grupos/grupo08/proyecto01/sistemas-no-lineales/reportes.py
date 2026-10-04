"""Generacion de informes HTML y LaTeX para resultados numericos."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from resultado import ResultadoMetodo
from visualizacion import generar_grafico_trayectoria


def _datos_resultado(resultado: ResultadoMetodo | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(resultado, ResultadoMetodo):
        return resultado.model_dump(mode="json")
    if isinstance(resultado, Mapping):
        return dict(resultado)
    raise TypeError("El resultado debe ser ResultadoMetodo o un diccionario.")


def _formatear(valor: Any) -> str:
    if valor is None:
        return "No disponible"
    if isinstance(valor, float):
        return f"{valor:.8g}"
    return str(valor)


def _estado_texto(datos: Mapping[str, Any]) -> str:
    estado = datos.get("status", "desconocido")
    return str(getattr(estado, "value", estado))


def generar_reporte_html(
    resultado: ResultadoMetodo | Mapping[str, Any],
    titulo: str = "Reporte de resultados numericos",
) -> str:
    """Devuelve un informe HTML autocontenido con resumen y trayectoria."""
    datos = _datos_resultado(resultado)
    solucion = datos.get("solution")
    solucion_texto = (
        ", ".join(_formatear(valor) for valor in solucion)
        if isinstance(solucion, Sequence) and not isinstance(solucion, (str, bytes))
        else "No disponible"
    )
    mensaje = datos.get("message")
    warnings = datos.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    filas = [
        ("Metodo", datos.get("method", "No disponible")),
        ("Estado", _estado_texto(datos)),
        ("Solucion", solucion_texto),
        ("Iteraciones", datos.get("iterations", 0)),
        ("Error final", datos.get("final_error")),
        ("Residuo final", datos.get("final_residual")),
    ]
    filas_html = "\n".join(
        f"<tr><th scope=\"row\">{html.escape(str(etiqueta))}</th>"
        f"<td>{html.escape(_formatear(valor))}</td></tr>"
        for etiqueta, valor in filas
    )
    mensaje_html = (
        f'<p class="message">{html.escape(str(mensaje))}</p>' if mensaje else ""
    )
    warnings_html = "".join(f"<li>{html.escape(str(aviso))}</li>" for aviso in warnings)
    warnings_section = (
        f"<section><h2>Avisos</h2><ul>{warnings_html}</ul></section>" if warnings else ""
    )
    try:
        grafico = generar_grafico_trayectoria(resultado)
        visualizacion = (
            f"<section><h2>Trayectoria</h2><figure>{grafico}</figure></section>"
            if grafico
            else ""
        )
    except ValueError as error:
        visualizacion = (
            '<section><h2>Trayectoria</h2>'
            f'<p class="notice">No se pudo graficar: {html.escape(str(error))}</p></section>'
        )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(titulo)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Georgia, 'Times New Roman', serif; color: #20342d; }}
    body {{ margin: 0; padding: 2rem; background: #f2f5f2; }}
    main {{ max-width: 920px; margin: 0 auto; }}
    h1 {{ margin-bottom: .35rem; font-size: 1.8rem; font-weight: 500; }}
    h2 {{ margin-top: 2rem; font-size: 1.15rem; font-weight: 600; }}
    .message {{ color: #53615c; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: .7rem .85rem; border-bottom: 1px solid #dce4e1; text-align: left; }}
    th {{ width: 34%; color: #53615c; font-weight: 500; }}
    figure {{ margin: 0; padding: .75rem; background: #fff; border: 1px solid #dce4e1; }}
    svg {{ display: block; width: 100%; height: auto; }}
    li {{ margin: .4rem 0; }}
    .notice {{ padding: .8rem; border-left: 3px solid #b47613; background: #fff; }}
    @media (max-width: 600px) {{ body {{ padding: 1rem; }} th, td {{ padding: .55rem; }} }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(titulo)}</h1>
    {mensaje_html}
    <section><h2>Resumen</h2><table><tbody>{filas_html}</tbody></table></section>
    {warnings_section}
    {visualizacion}
  </main>
</body>
</html>
"""


def guardar_reporte_html(
    resultado: ResultadoMetodo | Mapping[str, Any],
    ruta: str | Path,
    titulo: str = "Reporte de resultados numericos",
) -> Path:
    """Guarda el informe HTML y devuelve la ruta escrita."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(generar_reporte_html(resultado, titulo), encoding="utf-8")
    return destino


def _escapar_latex(texto: Any) -> str:
    reemplazos = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(reemplazos.get(caracter, caracter) for caracter in str(texto))


def generar_reporte_latex(
    resultado: ResultadoMetodo | Mapping[str, Any],
    titulo: str = "Reporte de resultados numericos",
) -> str:
    """Devuelve el fuente LaTeX del resumen y la trayectoria del resultado."""
    datos = _datos_resultado(resultado)
    solucion = datos.get("solution")
    if isinstance(solucion, Sequence) and not isinstance(solucion, (str, bytes)):
        solucion_texto = ", ".join(_formatear(valor) for valor in solucion)
    else:
        solucion_texto = "No disponible"

    filas = [
        ("Metodo", datos.get("method", "No disponible")),
        ("Estado", _estado_texto(datos)),
        ("Solucion", solucion_texto),
        ("Iteraciones", datos.get("iterations", 0)),
        ("Error final", datos.get("final_error")),
        ("Residuo final", datos.get("final_residual")),
    ]
    tabla_resumen = "\n".join(
        f"{_escapar_latex(etiqueta)} & {_escapar_latex(_formatear(valor))} \\\\"
        for etiqueta, valor in filas
    )
    mensaje = datos.get("message")
    mensaje_latex = (
        f"\\textbf{{Mensaje:}} {_escapar_latex(mensaje)}\\par\n" if mensaje else ""
    )
    warnings = datos.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    avisos_latex = ""
    if warnings:
        elementos = "\n".join(f"\\item {_escapar_latex(aviso)}" for aviso in warnings)
        avisos_latex = f"\\subsection*{{Avisos}}\n\\begin{{itemize}}\n{elementos}\n\\end{{itemize}}\n"

    tabla_trayectoria = ""
    try:
        puntos = datos.get("trajectory") or []
        if puntos:
            dimensiones = len(puntos[0])
            columnas = "r" * (dimensiones + 1)
            encabezados = "Iteracion & " + " & ".join(f"$x_{indice + 1}$" for indice in range(dimensiones))
            renglones = [encabezados + r" \\"]
            renglones.append(r"\hline")
            for indice, punto in enumerate(puntos):
                celdas = " & ".join(_escapar_latex(_formatear(valor)) for valor in punto)
                renglones.append(f"{indice} & {celdas} " + r"\\")
            tabla_trayectoria = (
                "\\subsection*{Trayectoria}\n"
                f"\\begin{{longtable}}{{{columnas}}}\n"
                + "\n".join(renglones)
                + "\n\\end{longtable}\n"
            )
    except (TypeError, ValueError, IndexError):
        tabla_trayectoria = "\\subsection*{Trayectoria}\nNo disponible.\\par\n"

    return f"""\\documentclass{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage[margin=2.5cm]{{geometry}}
\\usepackage{{longtable}}
\\title{{{_escapar_latex(titulo)}}}
\\begin{{document}}
\\maketitle
{mensaje_latex}\\section*{{Resumen}}
\\begin{{tabular}}{{ll}}
\\hline
{tabla_resumen}
\\hline
\\end{{tabular}}
{avisos_latex}{tabla_trayectoria}\\end{{document}}
"""


def guardar_reporte_latex(
    resultado: ResultadoMetodo | Mapping[str, Any],
    ruta: str | Path,
    titulo: str = "Reporte de resultados numericos",
) -> Path:
    """Guarda el fuente LaTeX y devuelve la ruta escrita."""
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(generar_reporte_latex(resultado, titulo), encoding="utf-8")
    return destino