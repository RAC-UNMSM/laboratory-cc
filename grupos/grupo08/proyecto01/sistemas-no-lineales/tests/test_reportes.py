from resultado import EstadoMetodo, ResultadoMetodo
from reportes import (
    generar_reporte_html,
    generar_reporte_latex,
    guardar_reporte_html,
    guardar_reporte_latex,
)


def _resultado():
    return ResultadoMetodo(
        method="newton_sistemas",
        status=EstadoMetodo.CONVERGED,
        solution=[1.0, 2.0],
        iterations=2,
        final_error=1e-9,
        final_residual=2e-9,
        trajectory=[[0.0, 0.5], [1.0, 2.0]],
        warnings=["revision & control"],
        message="Convergencia alcanzada.",
    )


def test_reporte_html_incluye_resumen_trayectoria_y_escapado():
    html = generar_reporte_html(_resultado(), titulo="Informe <final>")

    assert "newton_sistemas" in html
    assert "converged" in html
    assert "<svg" in html
    assert "revision &amp; control" in html
    assert "Informe &lt;final&gt;" in html
    assert 'name="file-id" content="' in html
    assert "mathjax@3/es5/tex-svg.js" in html
    assert r"F(\mathbf{x})=\mathbf{0}" in html
    assert r"\mathbf{x}^{*}" in html


def test_reporte_html_acepta_diccionario_mcp():
    html = generar_reporte_html(
        {
            "method": "metodo_demo",
            "status": "max_iter",
            "solution": [3.0],
            "iterations": 4,
            "trajectory": [[0.0], [3.0]],
        }
    )

    assert "metodo_demo" in html
    assert "max_iter" in html
    assert "3" in html


def test_reporte_html_incluye_contexto_y_tabla_iteraciones():
    html = generar_reporte_html(
        _resultado(),
        contexto={
            "enunciado": "Resolver el sistema de la circunferencia y la recta.",
            "ecuaciones_tex": [r"x^2+y^2-1=0", r"x-y=0"],
            "punto_inicial": [1.0, 0.5],
            "tolerancia": 1e-8,
            "max_iteraciones": 50,
            "criterio_tex": r"\|F(\mathbf{x}_k)\|_2<\varepsilon",
            "error_final": 0.058925565,
            "iteraciones": [
                {"k": 0, "x": [1.0, 0.5], "error": None, "residuo": 0.25},
                {"k": 1, "x": [0.75, 0.75], "error": 0.35355, "residuo": 0.125},
            ],
            "verificacion_tex": r"F(\mathbf{x}^{*})=\mathbf{0}",
        },
    )

    assert "Resolver el sistema de la circunferencia" in html
    assert r"x^2+y^2-1=0" in html
    assert r"\mathbf{x}_k" in html
    assert "Maximo de iteraciones" in html
    assert "<th>k</th>" in html
    assert "0.058925565" in html
    assert "Verificacion" in html


def test_reporte_latex_escapa_caracteres_especiales():
    latex = generar_reporte_latex(_resultado(), titulo="Informe_50%")

    assert r"Informe\_50\%" in latex
    assert r"revision \& control" in latex
    assert r"\textbf{Identificador:}" in latex
    assert r"\begin{longtable}" in latex
    assert r"\end{document}" in latex


def test_guardar_reportes_crea_directorios(tmp_path):
    html_path = tmp_path / "informes" / "resultado.html"
    latex_path = tmp_path / "informes" / "resultado.tex"

    saved_html = guardar_reporte_html(_resultado(), html_path)
    saved_latex = guardar_reporte_latex(_resultado(), latex_path)

    assert saved_html.parent == html_path.parent
    assert saved_html.suffix == html_path.suffix
    assert html_path.stem in saved_html.stem
    assert saved_latex.parent == latex_path.parent
    assert saved_latex.suffix == latex_path.suffix
    assert latex_path.stem in saved_latex.stem
    assert len(saved_html.stem.removeprefix(html_path.stem + "_")) == 32
    assert len(saved_latex.stem.removeprefix(latex_path.stem + "_")) == 32
    assert saved_html.exists()
    assert saved_latex.exists()