"""Pruebas del compilador de expresiones, incluida la entrada hostil.

Este módulo es la frontera del servidor: recibe texto de un cliente MCP
cualquiera. Lo que importa no es solo que compile lo válido, sino que rechace
lo inválido con un error explicable en vez de ejecutarlo.
"""

import math
import unittest

from matematica.expresiones import (ExpresionInvalida, compilar_campo,
                                    compilar_escalar, jacobiano_simbolico)


class CompilacionValidaTests(unittest.TestCase):
    def test_campo_escalar_autonomo(self):
        campo = compilar_campo(["r*y*(1 - y/K)"], "t", ["y"], ["r", "K"])
        self.assertAlmostEqual(campo(0.0, [1.0], {"r": 1.0, "K": 10.0})[0], 0.9)

    def test_campo_vectorial_con_parametro(self):
        campo = compilar_campo(["thetapunto", "-w0**2*sin(theta)"], "t",
                               ["theta", "thetapunto"], ["w0"])
        derivada = campo(0.0, [math.pi / 2, 0.0], {"w0": 2.0})
        self.assertAlmostEqual(float(derivada[0]), 0.0)
        self.assertAlmostEqual(float(derivada[1]), -4.0)

    def test_campo_no_autonomo_usa_la_variable_independiente(self):
        campo = compilar_campo(["3*x*y**2"], "x", ["y"])
        self.assertAlmostEqual(campo(2.0, [1.0])[0], 6.0)

    def test_escalar_solo_exige_los_simbolos_que_usa(self):
        exacta = compilar_escalar("2/(2 - 3*x**2)", ["x", "y", "w0"])
        self.assertEqual(exacta.usados, ("x",))
        self.assertAlmostEqual(exacta(x=0.5), 1.6)

    def test_escalar_constante(self):
        constante = compilar_escalar("1", ["x"])
        self.assertEqual(constante.usados, ())
        self.assertEqual(constante(), 1)

    def test_alias_de_escritura_habitual(self):
        self.assertAlmostEqual(compilar_escalar("ln(x) + abs(0 - x)", ["x"])(x=2.0),
                               math.log(2.0) + 2.0)

    def test_jacobiano_simbolico_exacto(self):
        campo = compilar_campo(["y", "-w0**2*sin(x1)"], "t", ["x1", "y"], ["w0"])
        self.assertEqual(str(jacobiano_simbolico(campo).tolist()),
                         "[[0, 1], [-w0**2*cos(x1), 0]]")

    def test_falta_un_parametro_se_reporta(self):
        campo = compilar_campo(["a*y"], "t", ["y"], ["a"])
        with self.assertRaisesRegex(ExpresionInvalida, "par"):
            campo(0.0, [1.0], {})


class EntradaRechazadaTests(unittest.TestCase):
    """Cada caso debe fallar con ExpresionInvalida, nunca ejecutarse."""

    def _rechaza(self, expresion, variables=("y",), independiente="x", parametros=()):
        with self.assertRaises(ExpresionInvalida):
            compilar_campo([expresion], independiente, list(variables), list(parametros))

    def test_rechaza_dunder(self):
        self._rechaza("__import__")

    def test_rechaza_comillas_y_llamadas_a_builtins(self):
        self._rechaza("open('archivo')")

    def test_rechaza_nombres_con_punto(self):
        self._rechaza("os.path")

    def test_rechaza_punto_y_coma(self):
        self._rechaza("y + 1; y")

    def test_rechaza_simbolo_no_declarado(self):
        self._rechaza("3*x*z**2")

    def test_rechaza_funcion_no_permitida(self):
        self._rechaza("gamma(y)")

    def test_rechaza_potencia_con_circunflejo(self):
        with self.assertRaisesRegex(ExpresionInvalida, r"\*\*"):
            compilar_campo(["y^2"], "x", ["y"])

    def test_rechaza_texto_vacio(self):
        self._rechaza("   ")

    def test_rechaza_numero_de_ecuaciones_distinto_del_estado(self):
        with self.assertRaisesRegex(ExpresionInvalida, "esperaban"):
            compilar_campo(["y", "y"], "x", ["y"])

    def test_rechaza_lista_de_ecuaciones_vacia(self):
        with self.assertRaisesRegex(ExpresionInvalida, "al menos una"):
            compilar_campo([], "x", [])

    def test_rechaza_variable_con_nombre_de_funcion(self):
        with self.assertRaisesRegex(ExpresionInvalida, "funci"):
            compilar_campo(["sin"], "x", ["sin"])

    def test_rechaza_variable_repetida(self):
        with self.assertRaisesRegex(ExpresionInvalida, "repetido"):
            compilar_campo(["y", "y"], "x", ["y", "y"])

    def test_rechaza_nombre_de_variable_invalido(self):
        with self.assertRaisesRegex(ExpresionInvalida, "inv"):
            compilar_campo(["1"], "x", ["2y"])


if __name__ == "__main__":
    unittest.main()
