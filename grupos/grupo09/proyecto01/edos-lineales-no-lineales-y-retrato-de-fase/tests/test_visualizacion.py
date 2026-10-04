"""Pruebas del documento HTML: lo que entra del cliente no puede ser código.

El HTML que arma `generar_html` no se queda en la respuesta: `storage.subir_html`
lo publica en una URL pública del laboratorio, bajo el mismo dominio que el
resto de los grupos. Todo lo que el cliente MCP controla -- el título, los
nombres de variable, los nombres de parámetro -- viaja hasta ese documento, así
que tiene que llegar como texto y no como marcado.
"""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from matematica.expresiones import compilar_campo
from visualizacion.html import construir_figuras, generar_html
from visualizacion.plantilla import figura_a_json


def _documento(**extra):
    campo = compilar_campo(["-y"], "t", ["y"])
    tiempos = np.linspace(0.0, 1.0, 50)
    estados = np.exp(-tiempos).reshape(1, -1)
    argumentos = {"campo": campo, "tiempos": tiempos, "estados": estados,
                  "parametros": {}, "variables": ["y"]}
    argumentos.update(extra)
    return generar_html(**argumentos)["html"]


class TestEscapadoDelDocumento(unittest.TestCase):

    def test_titulo_no_puede_cerrar_la_etiqueta_title(self):
        html = _documento(titulo="</title><script>alert(1)</script>")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;/title&gt;&lt;script&gt;", html)

    def test_nombre_de_variable_no_inyecta_marcado(self):
        html = _documento(variables=["<img src=x onerror=alert(1)>"])
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)

    def test_nombre_de_parametro_no_inyecta_marcado(self):
        html = _documento(parametros={"<b>r</b>": 2.0})
        self.assertNotIn("<b>r</b>", html)
        self.assertIn("&lt;b&gt;r&lt;/b&gt;", html)

    def test_un_titulo_normal_se_sigue_leyendo(self):
        self.assertIn("<title>Péndulo amortiguado</title>",
                      _documento(titulo="Péndulo amortiguado"))


class TestLasFigurasNoCocinanColores(unittest.TestCase):
    """El color lo pone la página, no el servidor.

    Cada traza declara su rol y la plantilla le asigna el color desde su propio
    CSS. Si una figura volviera a traer un color fijo habría dos fuentes para lo
    mismo, y la de aquí ganaría: la figura se vería mal en modo oscuro, que es
    justo lo que esta separación evita.
    """

    def _figuras(self):
        campo = compilar_campo(["v", "-sin(x)-0.1*v"], "t", ["x", "v"])
        tiempos = np.linspace(0.0, 10.0, 200)
        estados = np.vstack([np.cos(tiempos), -np.sin(tiempos)])
        return construir_figuras(
            campo, tiempos, estados, {}, ["x", "v"],
            [{"equilibrio": [0.0, 0.0], "clasificacion": "estable"}])

    def test_ninguna_traza_trae_color_fijo(self):
        for nombre, figura in self._figuras():
            spec = figura_a_json(figura)
            crudo = json.dumps(spec)
            self.assertNotRegex(crudo, r"#[0-9a-fA-F]{6}",
                                f"la figura {nombre} trae un color cocinado")

    def test_toda_traza_declara_su_rol(self):
        for nombre, figura in self._figuras():
            for traza in figura_a_json(figura)["data"]:
                self.assertIn("rol", traza.get("meta") or {},
                              f"una traza de {nombre} no dice qué es")

    def test_la_plantilla_de_plotly_no_viaja(self):
        """Son ~7 KB por figura que la página vuelve a decidir igual."""
        for _, figura in self._figuras():
            self.assertNotIn("template", figura_a_json(figura)["layout"])

    def test_la_pagina_sabe_pintar_todos_los_roles(self):
        """Un rol nuevo en el servidor sin color en la plantilla sale en negro."""
        pagina = (Path(__file__).resolve().parents[1] /
                  "visualizacion" / "plantillas" / "informe.html").read_text(encoding="utf-8")
        mapa = pagina.split("function colorDeRol")[1].split('\\n  }')[0]
        explicitos = set(re.findall(r'case "([a-z0-9]+)"', mapa))
        prefijos = set(re.findall(r'rol\.indexOf\("([a-z]+:)"\)', mapa))
        for _, figura in self._figuras():
            for traza in figura_a_json(figura)["data"]:
                rol = traza["meta"]["rol"]
                base = rol.split(":")[0] + ":" if ":" in rol else rol
                self.assertTrue(rol in explicitos or base in prefijos,
                                f"la plantilla no sabe de qué color va {rol!r}")


if __name__ == "__main__":
    unittest.main()
