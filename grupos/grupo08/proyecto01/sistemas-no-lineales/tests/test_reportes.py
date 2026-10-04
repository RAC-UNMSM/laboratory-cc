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


def test_reporte_latex_escapa_caracteres_especiales():
    latex = generar_reporte_latex(_resultado(), titulo="Informe_50%")

    assert r"Informe\_50\%" in latex
    assert r"revision \& control" in latex
    assert r"\begin{longtable}" in latex
    assert r"\end{document}" in latex


def test_guardar_reportes_crea_directorios(tmp_path):
    html_path = tmp_path / "informes" / "resultado.html"
    latex_path = tmp_path / "informes" / "resultado.tex"

    assert guardar_reporte_html(_resultado(), html_path) == html_path
    assert guardar_reporte_latex(_resultado(), latex_path) == latex_path
    assert html_path.exists()
    assert latex_path.exists()