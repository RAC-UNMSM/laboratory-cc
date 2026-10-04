import pytest

from resultado import EstadoMetodo, ResultadoMetodo
from visualizacion import (
    generar_grafico_trayectoria,
    generar_visualizacion_html,
    guardar_visualizacion_html,
)


def _resultado():
    return ResultadoMetodo(
        method="newton_sistemas",
        status=EstadoMetodo.CONVERGED,
        solution=[1.0, 2.0],
        iterations=2,
        trajectory=[[0.0, 0.5], [0.7, 1.5], [1.0, 2.0]],
    )


def test_grafico_incluye_series_y_puntos_interactivos():
    grafico = generar_grafico_trayectoria(_resultado())

    assert "<svg" in grafico
    assert "x1" in grafico
    assert "x2" in grafico
    assert "Iteracion 2; x2 = 2" in grafico


def test_visualizacion_acepta_diccionario_y_escapa_titulo():
    html = generar_visualizacion_html(
        {"trajectory": [[1.0], [2.0]]},
        titulo="<script>alert(1)</script>",
    )

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)</script>" not in html
    assert "<svg" in html


def test_visualizacion_sin_trayectoria_muestra_estado_vacio():
    html = generar_visualizacion_html({"trajectory": []})

    assert "No hay trayectoria disponible" in html


def test_grafico_rechaza_dimensiones_inconsistentes():
    with pytest.raises(ValueError, match="misma dimension"):
        generar_grafico_trayectoria({"trajectory": [[1.0], [1.0, 2.0]]})


def test_guardar_visualizacion_crea_directorio(tmp_path):
    destino = tmp_path / "graficos" / "trayectoria.html"

    escrita = guardar_visualizacion_html(_resultado(), destino)

    assert escrita == destino
    assert "<svg" in destino.read_text(encoding="utf-8")