from pathlib import Path
import subprocess
import tempfile
import shutil
import re

BASE_DIR = Path(__file__).resolve().parent
REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def limpiar_nombre(nombre: str) -> str:
    nombre = str(nombre or "").strip()

    if not nombre:
        nombre = "interpolacion"

    # Caracteres inválidos en nombres de Windows
    nombre = re.sub(r'[<>:"/\\|?*]', "", nombre)

    # Espacios -> _
    nombre = re.sub(r"\s+", "_", nombre)

    # Evitar puntos o espacios finales
    nombre = nombre.strip(" ._")

    return nombre or "interpolacion"


def nombre_disponible(nombre_base: str) -> Path:
    """
    Si interpolacion.pdf ya existe:
    interpolacion_2.pdf
    interpolacion_3.pdf
    ...
    """
    destino = REPORT_DIR / f"{nombre_base}.pdf"

    if not destino.exists():
        return destino

    numero = 2

    while True:
        destino = REPORT_DIR / f"{nombre_base}_{numero}.pdf"

        if not destino.exists():
            return destino

        numero += 1


def generar_reporte_latex(result, report_name="interpolacion"):
    report_name = limpiar_nombre(report_name)

    pdf_final = nombre_disponible(report_name)

    # El nombre temporal puede ser distinto.
    nombre_temp = pdf_final.stem

    puntos = result["points"]

    filas = "\n".join(
        f"{p['x']} & {p['y']} \\\\"
        for p in puntos
    )

    diferencias = result.get("difference_table", [])

    tabla_diferencias = ""

    if diferencias:
        max_order = max(
            [
                int(k[1:])
                for row in diferencias
                for k in row.keys()
                if k.startswith("d")
            ],
            default=0
        )

        encabezado = "x & f(x)"

        for i in range(1, max_order + 1):
            encabezado += f" & $f[x_0,\\ldots,x_{i}]$"

        encabezado += r" \\"

        filas_dif = []

        for row in diferencias:
            fila = f"{row['x']} & {row['f']}"

            for i in range(1, max_order + 1):
                valor = row.get(f"d{i}", "")
                fila += f" & {valor}"

            fila += r" \\"
            filas_dif.append(fila)

        columnas = "c" * (max_order + 2)

        tabla_diferencias = f"""
\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{{columnas}}}
\\toprule
{encabezado}
\\midrule
{chr(10).join(filas_dif)}
\\bottomrule
\\end{{tabular}}
\\caption{{Tabla de diferencias divididas}}
\\end{{table}}
"""

    metodo = result.get("method", "Interpolación")
    x_eval = result["x_eval"]
    valor = result["value"]
    lagrange = result["lagrange_value"]
    newton = result["newton_value"]
    diferencia = result["difference"]
    polynomial = result["polynomial"]

    tex = rf"""
\documentclass[12pt]{{article}}

\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[spanish]{{babel}}
\usepackage{{amsmath}}
\usepackage{{amssymb}}
\usepackage{{geometry}}
\usepackage{{booktabs}}
\usepackage{{float}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}

\geometry{{margin=2.5cm}}

\title{{Reporte de Interpolación}}
\author{{INTERPOLA-MCP}}
\date{{}}

\begin{{document}}

\maketitle

\section{{Datos del problema}}

Método utilizado:

\[
\boxed{{\text{{{metodo}}}}}
\]

Valor donde se evalúa:

\[
x = {x_eval}
\]

\section{{Puntos utilizados}}

\begin{{table}}[H]
\centering
\begin{{tabular}}{{cc}}
\toprule
$x$ & $f(x)$ \\
\midrule
{filas}
\bottomrule
\end{{tabular}}
\end{{table}}

\section{{Polinomio interpolante}}

\[
P(x) = {polynomial}
\]

\section{{Resultado}}

\[
P({x_eval}) =
\boxed{{{valor}}}
\]

\section{{Comparación de métodos}}

Por Lagrange:

\[
P_L({x_eval}) = {lagrange}
\]

Por Newton:

\[
P_N({x_eval}) = {newton}
\]

Diferencia absoluta:

\[
|P_L-P_N| = {diferencia}
\]

\section{{Diferencias divididas}}

{tabla_diferencias}

\end{{document}}
"""

    # TODO se compila dentro de una carpeta temporal.
    # .aux, .log, .tex, etc. desaparecen automáticamente.
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)

        tex_path = temp_dir / f"{nombre_temp}.tex"

        tex_path.write_text(
            tex,
            encoding="utf-8"
        )

        process = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(temp_dir),
                str(tex_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:
            raise RuntimeError(
                "Error al compilar LaTeX:\n\n"
                + process.stdout
                + "\n"
                + process.stderr
            )

        pdf_temporal = temp_dir / f"{nombre_temp}.pdf"

        if not pdf_temporal.exists():
            raise RuntimeError(
                "pdflatex finalizó pero no generó el PDF."
            )

        shutil.copy2(
            pdf_temporal,
            pdf_final
        )

    return {
        "pdf": str(pdf_final),
        "name": pdf_final.name
    }