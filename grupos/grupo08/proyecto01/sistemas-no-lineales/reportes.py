"""Generacion de informes HTML y LaTeX para resultados numericos."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from identificadores import crear_identificador, guardar_archivo_identificado
from resultado import ResultadoMetodo
from visualizacion import generar_grafico_trayectoria, mathjax_html_loader


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


def _generar_contexto_html(contexto: Mapping[str, Any]) -> tuple[str, bool]:
    secciones: list[str] = []
    enunciado = contexto.get("enunciado")
    if enunciado:
        secciones.append(
            '<section><h2>Enunciado</h2>'
            f'<p>{html.escape(str(enunciado))}</p></section>'
        )

    ecuaciones = contexto.get("ecuaciones_tex", [])
    if isinstance(ecuaciones, str):
        ecuaciones = [ecuaciones]
    ecuaciones_html = "".join(
        f'<div class="math-block">\\[{html.escape(str(ecuacion))}\\]</div>'
        for ecuacion in ecuaciones
    )
    if ecuaciones_html:
        secciones.append(f"<section><h2>Formulacion</h2>{ecuaciones_html}</section>")

    datos = [
        ("Punto inicial", contexto.get("punto_inicial")),
        ("Tolerancia", contexto.get("tolerancia")),
        ("Maximo de iteraciones", contexto.get("max_iteraciones")),
        ("Criterio de convergencia", contexto.get("criterio_tex")),
    ]
    filas_datos = []
    for etiqueta, valor in datos:
        if valor is None:
            continue
        if etiqueta == "Punto inicial" and isinstance(valor, Sequence):
            representacion = r"\(\mathbf{x}_0=\left(" + ", ".join(
                _formatear(item) for item in valor
            ) + r"\right)\)"
        elif etiqueta == "Criterio de convergencia":
            representacion = r"\(" + html.escape(str(valor)) + r"\)"
        else:
            representacion = html.escape(_formatear(valor))
        filas_datos.append(
            f"<tr><th scope=\"row\">{html.escape(etiqueta)}</th>"
            f"<td>{representacion}</td></tr>"
        )
    if filas_datos:
        secciones.append(
            "<section><h2>Datos del metodo</h2><table><tbody>"
            + "".join(filas_datos)
            + "</tbody></table></section>"
        )

    pasos = contexto.get("pasos", [])
    if pasos:
        filas_pasos = "".join(
            f"<li>{html.escape(str(paso))}</li>" for paso in pasos
        )
        secciones.append(f"<section><h2>Desarrollo</h2><ol>{filas_pasos}</ol></section>")

    iteraciones = contexto.get("iteraciones", [])
    if iteraciones:
        filas_iteraciones = []
        for iteracion in iteraciones:
            k = html.escape(str(iteracion.get("k", "")))
            punto = iteracion.get("x", [])
            vector_tex = r"\(\left(" + ", ".join(
                _formatear(valor) for valor in punto
            ) + r"\right)\)"
            error = iteracion.get("error")
            error_tex = (
                r"\(\text{inicial}\)"
                if error is None
                else r"\(" + _formatear(error) + r"\)"
            )
            residuo_tex = r"\(" + _formatear(iteracion.get("residuo")) + r"\)"
            filas_iteraciones.append(
                f"<tr><td>{k}</td><td>{vector_tex}</td>"
                f"<td>{error_tex}</td><td>{residuo_tex}</td></tr>"
            )
        secciones.append(
            "<section><h2>Iteraciones</h2><div class=\"table-scroll\"><table>"
            "<thead><tr><th>k</th><th>\\(\\mathbf{x}_k\\)</th>"
            "<th>\\(\\|\\mathbf{x}_k-\\mathbf{x}_{k-1}\\|_2\\)</th>"
            "<th>\\(\\|F(\\mathbf{x}_k)\\|_2\\)</th></tr></thead><tbody>"
            + "".join(filas_iteraciones)
            + "</tbody></table></div></section>"
        )

    for key, heading in (("verificacion_tex", "Verificacion"), ("conclusion", "Conclusion")):
        value = contexto.get(key)
        if value:
            contenido = (
                f'<div class="math-block">\\[{html.escape(str(value))}\\]</div>'
                if key == "verificacion_tex"
                else f"<p>{html.escape(str(value))}</p>"
            )
            secciones.append(f"<section><h2>{heading}</h2>{contenido}</section>")

    return "\n".join(secciones), bool(ecuaciones_html)


def generar_reporte_html(
    resultado: ResultadoMetodo | Mapping[str, Any],
    titulo: str = "Reporte de resultados numericos",
    identificador: str | None = None,
    contexto: Mapping[str, Any] | None = None,
) -> str:
    """Devuelve un informe HTML autocontenido con resumen y trayectoria."""
    identificador = identificador or crear_identificador()
    datos = _datos_resultado(resultado)
    solucion = datos.get("solution")
    solucion_texto = (
        ", ".join(_formatear(valor) for valor in solucion)
        if isinstance(solucion, Sequence) and not isinstance(solucion, (str, bytes))
        else "No disponible"
    )
    if isinstance(solucion, Sequence) and not isinstance(solucion, (str, bytes)) and all(
        isinstance(valor, (int, float)) and not isinstance(valor, bool)
        for valor in solucion
    ):
        solucion_texto = (
            r"\(\mathbf{x}^{*}=\left("
            + ", ".join(_formatear(valor) for valor in solucion)
            + r"\right)\)"
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
        (
            r"Error final \(e_f\)",
            (contexto or {}).get("error_final", datos.get("final_error")),
        ),
        (r"Residuo final \(\|F(\mathbf{x})\|_2\)", datos.get("final_residual")),
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

    contexto_html, tiene_ecuaciones = _generar_contexto_html(contexto or {})
    ecuacion_sistema = (
        ""
        if tiene_ecuaciones
        else r'<div class="math-block">\[F(\mathbf{x})=\mathbf{0}\]</div>'
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="file-id" content="{html.escape(identificador, quote=True)}">
  <title>{html.escape(titulo)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Georgia, 'Times New Roman', serif; color: #20342d; }}
    body {{ margin: 0; padding: 2rem; background: #f2f5f2; }}
    main {{ max-width: 920px; margin: 0 auto; }}
    h1 {{ margin-bottom: .35rem; font-size: 1.8rem; font-weight: 500; }}
    h2 {{ margin-top: 2rem; font-size: 1.15rem; font-weight: 600; }}
    .math-block {{ margin: 1.25rem 0; padding: .8rem 1rem; background: #fff; border-left: 3px solid #146c5a; overflow-x: auto; }}
    .message {{ color: #53615c; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{ padding: .7rem .85rem; border-bottom: 1px solid #dce4e1; text-align: left; }}
    th {{ width: 34%; color: #53615c; font-weight: 500; }}
    figure {{ margin: 0; padding: .75rem; background: #fff; border: 1px solid #dce4e1; }}
    svg {{ display: block; width: 100%; height: auto; }}
    li {{ margin: .4rem 0; }}
    .notice {{ padding: .8rem; border-left: 3px solid #b47613; background: #fff; }}
    .table-scroll {{ overflow-x: auto; }}
    @media (max-width: 600px) {{ body {{ padding: 1rem; }} th, td {{ padding: .55rem; white-space: nowrap; }} }}
  </style>
    {mathjax_html_loader()}
</head>
<body>
  <main>
    <h1>{html.escape(titulo)}</h1>
    <p class="file-id">ID de archivo: <code>{html.escape(identificador)}</code></p>
    {mensaje_html}
    {contexto_html}
    {ecuacion_sistema}
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
    contexto: Mapping[str, Any] | None = None,
) -> Path:
    """Guarda el informe HTML y devuelve la ruta escrita."""
    identificador = crear_identificador()
    return guardar_archivo_identificado(
        ruta,
        generar_reporte_html(resultado, titulo, identificador, contexto),
        identificador,
    )


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
    identificador: str | None = None,
) -> str:
    """Devuelve el fuente LaTeX del resumen y la trayectoria del resultado."""
    identificador = identificador or crear_identificador()
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
\\noindent \\textbf{{Identificador:}} {_escapar_latex(identificador)}\\par
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
    identificador = crear_identificador()
    return guardar_archivo_identificado(
        ruta,
        generar_reporte_latex(resultado, titulo, identificador),
        identificador,
    )
