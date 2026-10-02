"""
tests/test_analisis_estabilidad.py

Pruebas unitarias del módulo analisis_estabilidad.py, cubriendo los casos de
referencia exigidos en el prompt del integrante (sección 25 y 26) y en la
tabla de verificación de Grupo_09_Propuesta_actualizada.md.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analisis_estabilidad import analizar_estabilidad, ErrorAnalisisEstabilidad  # noqa: E402


class TestCasos1D(unittest.TestCase):
    def test_lineal_estable(self):
        # x' = -2x  ->  x* = 0, J = [-2], lambda = -2, estable.
        modelo = {"variables": ["x"], "equations": ["-2*x"]}
        r = analizar_estabilidad(modelo)
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["equilibria"]), 1)
        eq = r["equilibria"][0]
        self.assertEqual(eq["point"], ["0"])
        self.assertEqual(eq["classification"]["stability"], "local_asymptotically_stable")
        self.assertTrue(eq["classification"]["conclusive"])
        self.assertEqual(eq["classification"]["qualitative_type"], "stable_node")

    def test_lineal_inestable(self):
        modelo = {"variables": ["x"], "equations": ["x"]}
        r = analizar_estabilidad(modelo)
        eq = r["equilibria"][0]
        self.assertEqual(eq["classification"]["stability"], "unstable")
        self.assertEqual(eq["classification"]["qualitative_type"], "unstable_node")

    def test_logistico(self):
        # x' = x(1-x): x*=0 inestable, x*=1 estable.
        modelo = {"variables": ["x"], "equations": ["x*(1-x)"]}
        r = analizar_estabilidad(modelo)
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["equilibria"]), 2)
        por_punto = {eq["point"][0]: eq for eq in r["equilibria"]}
        self.assertIn("0", por_punto)
        self.assertIn("1", por_punto)
        self.assertEqual(por_punto["0"]["classification"]["stability"], "unstable")
        self.assertEqual(
            por_punto["1"]["classification"]["stability"], "local_asymptotically_stable"
        )


class TestCasos2D(unittest.TestCase):
    def test_silla(self):
        # x'=x, y'=-y  -> (0,0) silla, inestable.
        modelo = {"variables": ["x", "y"], "equations": ["x", "-y"]}
        r = analizar_estabilidad(modelo)
        self.assertTrue(r["valid"])
        eq = r["equilibria"][0]
        self.assertEqual(eq["classification"]["stability"], "unstable")
        self.assertEqual(eq["classification"]["qualitative_type"], "saddle")

    def test_foco_estable(self):
        # x'=-x-y, y'=x-y -> autovalores -1±i, foco estable.
        modelo = {"variables": ["x", "y"], "equations": ["-x - y", "x - y"]}
        r = analizar_estabilidad(modelo)
        eq = r["equilibria"][0]
        self.assertEqual(eq["classification"]["stability"], "local_asymptotically_stable")
        self.assertEqual(eq["classification"]["qualitative_type"], "stable_focus")

    def test_centro_parte_real_cero(self):
        # x'=-y, y'=x -> autovalores +-i, no concluyente.
        modelo = {"variables": ["x", "y"], "equations": ["-y", "x"]}
        r = analizar_estabilidad(modelo)
        eq = r["equilibria"][0]
        self.assertFalse(eq["classification"]["conclusive"])
        self.assertIsNone(eq["classification"]["stability"])
        self.assertIn("no permite determinar", eq["classification"]["reason"])


class TestParametrosSimbolicos(unittest.TestCase):
    def test_mu_no_se_inventa(self):
        # x' = mu*x - x**3 : equilibrios 0, sqrt(mu), -sqrt(mu); mu debe
        # permanecer simbólico (nunca sustituido por un valor inventado).
        modelo = {"variables": ["x"], "equations": ["mu*x - x**3"]}
        r = analizar_estabilidad(modelo)
        self.assertTrue(r["valid"])
        puntos = sorted(eq["point"][0] for eq in r["equilibria"])
        self.assertIn("0", puntos)
        self.assertTrue(any("mu" in p for p in puntos))
        # En x*=0 el autovalor es 'mu': el signo no puede determinarse.
        eq_cero = next(eq for eq in r["equilibria"] if eq["point"] == ["0"])
        self.assertFalse(eq_cero["classification"]["conclusive"])
        self.assertIn("mu", eq_cero["eigenvalues"][0]["value"])

    def test_parametros_numericos_no_se_modifican(self):
        # x' = r*x*(1 - x/K) con r=2, K=100: equilibrios 0 y 100 exactos.
        modelo = {
            "variables": ["x"],
            "equations": ["r*x*(1 - x/K)"],
            "parameters": {"r": 2, "K": 100},
        }
        r = analizar_estabilidad(modelo)
        self.assertTrue(r["valid"])
        puntos = sorted(eq["point"][0] for eq in r["equilibria"])
        self.assertEqual(puntos, ["0", "100"])
        por_punto = {eq["point"][0]: eq for eq in r["equilibria"]}
        self.assertEqual(por_punto["0"]["classification"]["stability"], "unstable")
        self.assertEqual(
            por_punto["100"]["classification"]["stability"], "local_asymptotically_stable"
        )


class TestSistemaNoAutonomo(unittest.TestCase):
    def test_dependencia_explicita_de_t(self):
        modelo = {"variables": ["x"], "equations": ["x + t"]}
        r = analizar_estabilidad(modelo)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "non_autonomous_system")

    def test_bandera_autonomous_false(self):
        modelo = {"variables": ["x"], "equations": ["-x"], "autonomous": False}
        r = analizar_estabilidad(modelo)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "non_autonomous_system")


class TestEntradaInvalida(unittest.TestCase):
    def test_variables_y_ecuaciones_no_coinciden(self):
        modelo = {"variables": ["x", "y"], "equations": ["-x"]}
        r = analizar_estabilidad(modelo)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "invalid_input")

    def test_expresion_insegura_rechazada(self):
        modelo = {"variables": ["x"], "equations": ["__import__('os')"]}
        r = analizar_estabilidad(modelo)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "invalid_input")

    def test_dimension_no_soportada(self):
        modelo = {
            "variables": ["a", "b", "c", "d"],
            "equations": ["-a", "-b", "-c", "-d"],
        }
        r = analizar_estabilidad(modelo)
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "invalid_input")


class TestAdicionales2D(unittest.TestCase):
    def test_x_prima_x_y_prima_menos_y_es_silla(self):
        # Ya cubierto en TestCasos2D.test_silla; se repite explícito por
        # estar listado en la sección 26 del prompt como caso mínimo.
        modelo = {"variables": ["x", "y"], "equations": ["x", "-y"]}
        r = analizar_estabilidad(modelo)
        self.assertEqual(r["equilibria"][0]["classification"]["qualitative_type"], "saddle")


if __name__ == "__main__":
    unittest.main()
