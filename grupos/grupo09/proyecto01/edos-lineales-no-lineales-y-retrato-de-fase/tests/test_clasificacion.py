"""Interpretación del enunciado, clasificación del problema y selección del método.

Es la parte "entiende el tipo → elige el procedimiento" del recorrido. Lo que
importa probar:

* que se lean del enunciado el método que nombra y lo que pide;
* que se registre con qué familias es compatible una ecuación, no solo cuál se
  eligió (3xy² es separable y de Bernoulli);
* que un método pedido se respete si la ecuación tiene esa forma, y se
  rechace diciendo por qué si no la tiene;
* que lo que el balotario no resuelve quede marcado como fuera de alcance.
"""

import unittest

from matematica.clasificacion import (FAMILIAS, FUERA_DE_ALCANCE, clasificar, clave_de_metodo,
                                      detectar_fuera_de_alcance, inventario)
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_edo
from orquestacion.interpretacion import leer_enunciado


def clasificacion(**solicitud):
    return clasificar(construir_problema(**solicitud))


def clave(c):
    return c.familia.clave if c.familia else "numerico"


class LecturaDelEnunciadoTests(unittest.TestCase):
    def test_metodo_y_pedidos(self):
        metodo, pedidos, _ = leer_enunciado(
            "Resuelva la ecuación diferencial ordinaria separable dy/dx = 3xy^2, y(0) = 1 y determine "
            "el intervalo máximo de existencia de la solución.")
        self.assertEqual(metodo, "separable")
        self.assertIn("intervalo_maximo", pedidos)

    def test_tildes_y_mayusculas_no_importan(self):
        metodo, pedidos, _ = leer_enunciado("Clasifique sus PUNTOS FIJOS y determine la ÓRBITA HOMOCLÍNICA")
        self.assertEqual(metodo, "homoclinica")
        self.assertTrue({"equilibrios", "homoclinica"} <= pedidos)

    def test_separacion_inicial(self):
        for texto, valor in (("separadas por δ_0 = 10^{-10}", 1e-10), ("con delta0 = 1e-8", 1e-8)):
            with self.subTest(texto=texto):
                self.assertEqual(leer_enunciado(texto)[2], valor)

    def test_sin_enunciado_no_se_inventa_nada(self):
        self.assertEqual(leer_enunciado(None), (None, set(), None))

    def test_alias_de_metodo(self):
        for texto, esperado in (("Cauchy-Euler", "cauchy_euler"), ("variables separables", "separable"),
                                ("factor integrante", "lineal"), ("Bernoulli", "bernoulli"),
                                ("numérico", "numerico"), ("transformada de Laplace", None)):
            with self.subTest(texto=texto):
                self.assertEqual(clave_de_metodo(texto), esperado)


class SeleccionDelMetodoTests(unittest.TestCase):
    def test_se_registran_todas_las_familias_compatibles(self):
        c = clasificacion(ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x")
        self.assertEqual(clave(c), "separable")
        self.assertEqual([f.clave for f, _ in c.compatibles], ["separable", "bernoulli"])
        self.assertIn("separable", c.motivo.lower())

    def test_el_metodo_pedido_se_respeta(self):
        c = clasificacion(ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x",
                          metodo="Bernoulli")
        self.assertEqual(clave(c), "bernoulli")
        self.assertIsNone(c.metodo_rechazado)

    def test_un_metodo_que_no_corresponde_se_rechaza_y_se_usa_el_correcto(self):
        """El 1.4 no es de Bernoulli (q₀ = x² + 1 ≠ 0): se dice y se aplica Riccati."""
        c = clasificacion(ecuaciones=["y**2 - 2*x*y + x**2 + 1"], variables_estado=["y"],
                          variable_independiente="x", metodo="bernoulli", solucion_particular="x")
        self.assertEqual(clave(c), "riccati")
        self.assertEqual(c.metodo_rechazado, "Ecuación de Bernoulli")
        self.assertIn("no corresponde", c.motivo)

    def test_tratamiento_numerico_a_pedido(self):
        c = clasificacion(ecuaciones=["-2*y"], variables_estado=["y"], metodo="numerico")
        self.assertEqual(clave(c), "numerico")

    def test_sin_familia_se_trata_numericamente_y_se_dice(self):
        c = clasificacion(ecuaciones=["10*(y - x)", "28*x - y - x*z", "x*y - 8*z/3"],
                          variables_estado=["x", "y", "z"])
        self.assertEqual(clave(c), "numerico")
        self.assertIn("Ninguna familia", c.motivo)

    def test_la_forma_companera_se_reconoce_como_ecuacion_de_orden_dos(self):
        c = clasificacion(ecuaciones=["yp", "(2*x*yp - 2*y + x**3*log(x))/x**2"], variables_estado=["y", "yp"],
                          variable_independiente="x")
        self.assertEqual(clave(c), "cauchy_euler")

    def test_un_lineal_conservativo_se_resuelve_como_lineal(self):
        c = clasificacion(ecuaciones=["y", "-9*x"], variables_estado=["x", "y"])
        self.assertEqual(clave(c), "lineal_plano")
        self.assertIn("conservativo", [f.clave for f, _ in c.compatibles])

    def test_el_pendulo_es_conservativo(self):
        c = clasificacion(ecuaciones=["v", "-sin(theta)"], variables_estado=["theta", "v"])
        self.assertEqual(clave(c), "conservativo")

    def test_con_parametro_simbolico_es_una_bifurcacion(self):
        self.assertEqual(clave(clasificacion(ecuaciones=["mu - x**2"], variables_estado=["x"], parametro="mu")),
                         "bifurcacion_1d")
        self.assertEqual(clave(clasificacion(ecuaciones=["mu*x - y - x*(x**2 + y**2)", "x + mu*y - y*(x**2 + y**2)"],
                                             variables_estado=["x", "y"], parametro="mu")), "hopf")

    def test_familias_que_solo_se_aplican_a_pedido(self):
        """Poincaré–Bendixson y Melnikov no compiten con el análisis local si nadie los pide."""
        sistema = dict(ecuaciones=["4*x - y - x*(x**2 + y**2)", "x + 4*y - y*(x**2 + y**2)"],
                       variables_estado=["x", "y"])
        self.assertEqual(clave(clasificacion(**sistema)), "no_lineal_plano")
        self.assertEqual(clave(clasificacion(**sistema, pedidos=["ciclo_limite"])), "ciclo_limite")
        homoclinico = dict(ecuaciones=["y", "mu*y + x - x**2 + x*y"], variables_estado=["x", "y"], parametro="mu")
        self.assertNotEqual(clave(clasificacion(**homoclinico)), "homoclinica")
        self.assertEqual(clave(clasificacion(**homoclinico, metodo="homoclinica")), "homoclinica")

    def test_la_linea_de_fase_solo_si_la_pregunta_es_por_los_equilibrios(self):
        base = dict(ecuaciones=["y*(1 - y)"], variables_estado=["y"])
        self.assertEqual(clave(clasificacion(**base, pedidos=["equilibrios"])), "equilibrios_1d")
        # Con condición inicial, la pregunta es resolver: decide la familia del Tema 1.
        self.assertEqual(clave(clasificacion(**base, pedidos=["equilibrios"], y0=[0.5], intervalo=[0, 5])),
                         "separable")
        self.assertEqual(clave(clasificacion(**base, pedidos=["equilibrios", "solucion_general"])), "separable")

    def test_un_mapa_unidimensional(self):
        c = clasificacion(ecuaciones=["1 - Abs(1 - 2*x)"], variables_estado=["x"], tipo_de_sistema="mapa_discreto")
        self.assertEqual(clave(c), "mapa_1d")


class AlcanceTests(unittest.TestCase):
    def test_el_inventario_lista_familias_y_lo_que_falta(self):
        datos = inventario()
        claves = {f["familia"] for f in datos["familias"]}
        self.assertEqual(claves, {f.clave for f in FAMILIAS})
        self.assertEqual(sorted(f["problema"] for f in datos["fuera_de_alcance"]),
                         ["4.2", "4.3", "4.4", "4.5", "5.1", "5.2", "5.3", "5.4", "5.5"])

    def test_cada_familia_cita_los_problemas_del_balotario_que_la_definen(self):
        citados = {p for f in FAMILIAS for p in f.balotario}
        self.assertEqual(citados, {"1.1", "1.2", "1.3", "1.4", "1.5", "2.1", "2.2", "2.3", "2.4", "2.5",
                                   "3.1", "3.2", "3.3", "3.4", "3.5", "4.1"})
        self.assertFalse(citados & {problema for problema, *_ in FUERA_DE_ALCANCE.values()})

    def test_deteccion_por_el_enunciado_y_por_la_forma(self):
        lorenz = construir_problema(ecuaciones=["10*(y - x)", "28*x - y - x*z", "x*y - 8*z/3"],
                                    variables_estado=["x", "y", "z"],
                                    enunciado="Demuestre que el sistema es disipativo y halle el elipsoide atrapante")
        self.assertEqual(detectar_fuera_de_alcance(lorenz)["problema"], "4.4")
        henon = construir_problema(ecuaciones=["1 - 1.4*x**2 + y", "0.3*x"], variables_estado=["x", "y"],
                                   tipo_de_sistema="mapa_discreto")
        self.assertEqual(detectar_fuera_de_alcance(henon)["problema"], "5.3")
        tienda = construir_problema(ecuaciones=["1 - Abs(1 - 2*x)"], variables_estado=["x"],
                                    tipo_de_sistema="mapa_discreto")
        self.assertIsNone(detectar_fuera_de_alcance(tienda))

    def test_la_primera_seccion_del_desarrollo_es_la_clasificacion(self):
        resultado = analizar_edo(dict(ecuaciones=["y**3 - y"], variables_estado=["y"], variable_independiente="x",
                                      y0=[1], intervalo=[0, 5], visualizar=False,
                                      enunciado="Resuelva la ecuación diferencial ordinaria de Bernoulli "
                                                "y' + y = y^3, y(0) = 1"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        primera = resultado["desarrollo"]["secciones"][0]
        self.assertEqual(primera["clave"], "clasificacion")
        self.assertEqual(resultado["clasificacion"]["familia"], "bernoulli")
        self.assertEqual(resultado["interpretacion"]["metodo"], "bernoulli")
        self.assertTrue(resultado["interpretacion"]["metodo_desde_enunciado"])


if __name__ == "__main__":
    unittest.main()
