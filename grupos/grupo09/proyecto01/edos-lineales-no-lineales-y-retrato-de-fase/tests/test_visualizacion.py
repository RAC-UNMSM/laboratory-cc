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
        explicitos = set(re.findall(r'case "([a-z0-9_]+)"', mapa))
        prefijos = set(re.findall(r'rol\.indexOf\("([a-z]+:)"\)', mapa))
        for _, figura in self._figuras():
            for traza in figura_a_json(figura)["data"]:
                rol = traza["meta"]["rol"]
                base = rol.split(":")[0] + ":" if ":" in rol else rol
                self.assertTrue(rol in explicitos or base in prefijos,
                                f"la plantilla no sabe de qué color va {rol!r}")


#: Un problema por familia: sus figuras del desarrollo deben poder pintarse.
PROBLEMAS_CON_FIGURAS = {
    "separable": dict(ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x",
                      y0=[1], intervalo=[0, 0.7], pedidos=["intervalo_maximo"]),
    "lineal_plano": dict(ecuaciones=["2*x", "-3*y"], variables_estado=["x", "y"], pedidos=["trayectorias"]),
    "lineal_plano_parametrico": dict(ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"],
                                     parametro="gamma", rango_parametro=[0, None]),
    "no_lineal_plano": dict(ecuaciones=["x*(3 - x - 2*y)", "y*(2 - x - y)"], variables_estado=["x", "y"],
                            region={"x": [0, None], "y": [0, None]}),
    "conservativo": dict(ecuaciones=["y", "x - x**3"], variables_estado=["x", "y"], pedidos=["separatriz"]),
    "ciclo_limite": dict(ecuaciones=["4*x - y - x*(x**2 + y**2)", "x + 4*y - y*(x**2 + y**2)"],
                         variables_estado=["x", "y"], pedidos=["ciclo_limite"]),
    "bifurcacion_1d": dict(ecuaciones=["mu*x + x**3 - x**5"], variables_estado=["x"], parametro="mu"),
    "hopf": dict(ecuaciones=["mu*x - y - x*(x**2 + y**2)", "x + mu*y - y*(x**2 + y**2)"],
                 variables_estado=["x", "y"], parametro="mu"),
    "mapa_1d": dict(ecuaciones=["1 - Abs(1 - 2*x)"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
                    separacion_inicial=1e-10),
    "equilibrios_1d": dict(ecuaciones=["x*(1 - x)*(x - 2)"], variables_estado=["x"], pedidos=["equilibrios"]),
}


class TestFigurasDelDesarrollo(unittest.TestCase):
    """Las figuras que describe cada familia llegan a plotly con su rol y sin color."""

    @classmethod
    def setUpClass(cls):
        from matematica.clasificacion import clasificar
        from matematica.problema import construir_problema
        from visualizacion.html import figuras_del_desarrollo
        cls.figuras = {}
        for familia, solicitud in PROBLEMAS_CON_FIGURAS.items():
            problema = construir_problema(**solicitud)
            clasificacion = clasificar(problema)
            desarrollo = clasificacion.familia.desarrollar(problema, clasificacion.datos)
            cls.figuras[familia] = figuras_del_desarrollo(desarrollo.graficas)
        pagina = (Path(__file__).resolve().parents[1] /
                  "visualizacion" / "plantillas" / "informe.html").read_text(encoding="utf-8")
        mapa = pagina.split("function colorDeRol")[1].split('\\n  }')[0]
        cls.explicitos = set(re.findall(r'case "([a-z0-9_]+)"', mapa))
        cls.prefijos = set(re.findall(r'rol\.indexOf\("([a-z]+:)"\)', mapa))

    def test_cada_familia_dibuja_algo(self):
        for familia, figuras in self.figuras.items():
            with self.subTest(familia=familia):
                self.assertTrue(figuras)
                for nombre, figura in figuras:
                    self.assertNotIsInstance(figura, Exception, f"{familia}/{nombre}: {figura}")

    def test_los_roles_del_desarrollo_tienen_color_en_la_pagina(self):
        for familia, figuras in self.figuras.items():
            for nombre, figura in figuras:
                for traza in figura_a_json(figura)["data"]:
                    rol = (traza.get("meta") or {}).get("rol")
                    with self.subTest(familia=familia, figura=nombre, rol=rol):
                        self.assertTrue(rol, "una traza no dice qué es")
                        base = rol.split(":")[0] + ":" if ":" in rol else rol
                        self.assertTrue(rol in self.explicitos or base in self.prefijos)

    def test_las_figuras_del_desarrollo_no_cocinan_colores(self):
        for familia, figuras in self.figuras.items():
            for nombre, figura in figuras:
                with self.subTest(familia=familia, figura=nombre):
                    self.assertNotRegex(json.dumps(figura_a_json(figura)), r"#[0-9a-fA-F]{6}")


if __name__ == "__main__":
    unittest.main()
