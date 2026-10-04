"""Plantillas Jinja2, gráficos y almacenamiento."""
import json
import re

import pytest

from core import reporte, visualizacion
from methods import metodo_frenet as MF, metodo_hessiana as MH, metodo_lagrange as ML
from storage import Almacen


@pytest.mark.parametrize("metodo, objeto", [
    ("lagrange", lambda: ML.resolver("x*y", ["x^2 + y^2 = 8"])),
    ("hessiana", lambda: MH.resolver("x^4 + y^4 - 4xy + 1")),
    ("frenet", lambda: MF.resolver("cos t, sin t, t", "0")),
])
def test_html_y_png(tmp_path, metodo, objeto):
    obj = objeto()
    datos = visualizacion.datos_grafico(metodo, obj)
    ruta = reporte.guardar_html(metodo, obj, tmp_path / "r.html", datos=datos)
    html = open(ruta, encoding="utf-8").read()
    assert html.lower().startswith("<!doctype html>") and "katex" in html.lower()
    assert not re.search(r"\{\{\s*\w+\s*\}\}|\{%", html)          # Jinja2 sin variables sin rellenar
    assert reporte.CONFIG[metodo]["titulo"] in html
    png = visualizacion.generar_png(metodo, obj, str(tmp_path / "g.png"), datos)
    assert open(png, "rb").read(8) == b"\x89PNG\r\n\x1a\n"
    assert reporte.resumen_breve(metodo, reporte.a_dict(metodo, obj))


def test_almacen(tmp_path):
    a = Almacen(tmp_path)
    id_, carpeta = a.nueva_carpeta("hessiana")
    a.guardar(id_, "hessiana", "f = x^2", {"funcion": "x^2"}, {"ok": 1}, ["P1: mínimo"])
    assert a.listar()[0]["id"] == id_
    assert a.obtener(id_)["resultado"] == {"ok": 1}
    assert json.loads((tmp_path / "indice.json").read_text(encoding="utf-8"))[0]["resumen"] == ["P1: mínimo"]
    for malo in ("../x", "hessiana-1-2-zz", "lagrange-20260101-000000-abcdef/../.."):
        with pytest.raises(KeyError):
            a.carpeta(malo)
