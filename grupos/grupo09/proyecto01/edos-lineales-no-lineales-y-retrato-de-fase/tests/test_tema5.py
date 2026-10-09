"""Tema 5 del balotario: atractores extraños y geometría fractal (5.1 a 5.5).

Como en los otros temas, cada procedimiento se prueba con los datos del
balotario y con otros, para que no esté hecho a la medida de un enunciado:

* 5.1, dimensión de caja: Cantor, Sierpinski, Koch, un conjunto dado por N y s,
  y datos imposibles;
* 5.2, herradura de Smale: otra contracción y otra expansión, y valores que no
  dan una herradura;
* 5.3, mapas del plano: Hénon con otros parámetros, un mapa que conserva área
  y uno no invertible;
* 5.4, sección de Poincaré: la del balotario (que hay que corregir) y la buena
  pedida directamente;
* 5.5, Kaplan-Yorke: con el sistema, solo con los exponentes, desordenados,
  y los casos límite k = 0 y k = n.
"""

import math
import unittest

import sympy as sp

from matematica import DatoInvalido
from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_caos_y_fractales

HENON = dict(ecuaciones=["1 - a*x**2 + y", "b*x"], variables_estado=["x", "y"], parametros={"a": 1.4, "b": 0.3},
             tipo_de_sistema="mapa_discreto")
ROSSLER = dict(ecuaciones=["-y - z", "x + a*y", "b + z*(x - c)"], variables_estado=["x", "y", "z"],
               parametros={"a": 0.2, "b": 0.2, "c": 5.7})
LORENZ = dict(ecuaciones=["sigma*(y - x)", "x*(r - z) - y", "x*y - b*z"], variables_estado=["x", "y", "z"],
              parametros={"sigma": 10, "r": 28, "b": 8 / 3})


def desarrollar(**solicitud):
    problema = construir_problema(**solicitud)
    clasificacion = clasificar(problema)
    return clasificacion.familia.desarrollar(problema, clasificacion.datos)


def teorico(pedido, enunciado="", **datos):
    return desarrollar(ecuaciones=[], variables_estado=[], pedidos=[pedido], enunciado=enunciado,
                       datos=datos or None)


class SinFallos:
    def assertSinFallos(self, desarrollo, *exigidas):
        self.assertEqual([v.nombre for v in desarrollo.validaciones if not v.ok and v.concluyente], [])
        hechas = {v.nombre for v in desarrollo.validaciones}
        for nombre in exigidas:
            self.assertIn(nombre, hechas)


class DimensionFractalTests(SinFallos, unittest.TestCase):
    def test_balotario_5_1_cantor(self):
        d = teorico("dimension_fractal", "Calcule la dimensión de caja del conjunto ternario de Cantor")
        self.assertEqual(d.familia, "dimension_fractal")
        self.assertEqual(d.resultados["dimension"], sp.log(2) / sp.log(3))
        self.assertAlmostEqual(d.resultados["dimension_numerica"], math.log(2) / math.log(3), delta=0.03)
        self.assertSinFallos(d, "conteo_exacto", "limite_de_las_cotas", "ecuacion_de_autosemejanza",
                             "dimension_por_conteo")

    def test_conjuntos_del_plano_con_nombre(self):
        for nombre, esperada in (("triángulo de Sierpinski", sp.log(3) / sp.log(2)),
                                 ("curva de Koch", sp.log(4) / sp.log(3)),
                                 ("alfombra de Sierpinski", sp.log(8) / sp.log(3))):
            with self.subTest(conjunto=nombre):
                d = teorico("dimension_fractal", f"Calcule la dimensión de caja de la {nombre}")
                self.assertEqual(sp.simplify(d.resultados["dimension"] - esperada), 0)
                self.assertSinFallos(d, "dimension_por_conteo")

    def test_un_conjunto_dado_por_sus_cifras(self):
        """Cantor de los quintos: 3 copias a escala 1/5, D = ln 3/ln 5."""
        d = teorico("dimension_fractal", "dimensión de un conjunto autosemejante", copias=3, razon=0.2)
        self.assertEqual(sp.simplify(d.resultados["dimension"] - sp.log(3) / sp.log(5)), 0)
        self.assertSinFallos(d, "conteo_exacto", "dimension_por_conteo")

    def test_las_cifras_tambien_se_leen_del_enunciado(self):
        d = teorico("dimension_fractal", "Un conjunto autosemejante formado por 4 copias a escala 1/5")
        self.assertEqual(sp.simplify(d.resultados["dimension"] - sp.log(4) / sp.log(5)), 0)

    def test_datos_imposibles(self):
        for datos, frase in (({"copias": 3}, "falta"), ({"copias": 1, "razon": 0.5}, "entero ≥ 2"),
                             ({"copias": 2, "razon": 1.5}, "entre 0 y 1"),
                             ({"copias": 30, "razon": 0.5}, "no caben")):
            with self.subTest(datos=datos):
                with self.assertRaisesRegex(DatoInvalido, frase):
                    teorico("dimension_fractal", "conjunto autosemejante", **datos)


class HerraduraTests(SinFallos, unittest.TestCase):
    def test_balotario_5_2(self):
        d = teorico("herradura", "Describa el mecanismo de la herradura de Smale")
        self.assertEqual(d.familia, "herradura")
        self.assertEqual(sp.simplify(d.resultados["dimension"] - 2 * sp.log(2) / sp.log(3)), 0)
        self.assertEqual(d.resultados["entropia"], sp.log(2))
        self.assertSinFallos(d, *[f"puntos_de_periodo_{n}" for n in range(1, 9)], "dimension_por_conteo")

    def test_otra_herradura(self):
        """λ = 1/4, μ = 4: D = 2·ln 2/ln 4 = 1."""
        d = teorico("herradura", "herradura de Smale", contraccion=0.25, expansion=4)
        self.assertEqual(sp.simplify(d.resultados["dimension"] - 1), 0)
        self.assertSinFallos(d, "puntos_de_periodo_8")

    def test_valores_que_no_dan_una_herradura(self):
        with self.assertRaisesRegex(DatoInvalido, "λ < 1/2"):
            teorico("herradura", "herradura", contraccion=0.6, expansion=3)
        with self.assertRaisesRegex(DatoInvalido, "μ > 2"):
            teorico("herradura", "herradura", contraccion=0.3, expansion=1.5)


class MapaDelPlanoTests(SinFallos, unittest.TestCase):
    def test_balotario_5_3_henon(self):
        d = desarrollar(**HENON)
        self.assertEqual(d.familia, "mapa_2d")
        a, b, x, y = sp.symbols("a b x y")
        plano = lambda e: e.subs({s: sp.Symbol(s.name) for s in e.free_symbols})  # noqa: E731
        self.assertEqual(plano(d.resultados["determinante"]), -b)
        self.assertEqual(d.resultados["factor_de_area"], sp.Rational(3, 10))
        inverso = [plano(e) for e in d.resultados["inverso"]]
        self.assertEqual(sp.simplify(inverso[0] - y / b), 0)
        self.assertEqual(sp.simplify(inverso[1] - (x - 1 + a * y ** 2 / b ** 2)), 0)
        l1, l2 = d.resultados["exponentes_lyapunov"]
        self.assertAlmostEqual(l1, 0.42, delta=0.01)
        self.assertAlmostEqual(l2, -1.62, delta=0.01)
        self.assertAlmostEqual(d.resultados["dimension_kaplan_yorke"], 1.26, delta=0.01)
        fijos = sorted(f["valor"][0] for f in d.resultados["puntos_fijos"])
        self.assertAlmostEqual(fijos[0], (-0.7 - math.sqrt(6.09)) / 2.8, places=12)
        self.assertAlmostEqual(fijos[1], (-0.7 + math.sqrt(6.09)) / 2.8, places=12)
        self.assertSinFallos(d, "inverso_por_la_derecha", "inverso_por_la_izquierda", "descomposicion",
                             "suma_de_exponentes")

    def test_henon_con_otros_parametros(self):
        d = desarrollar(**{**HENON, "parametros": {"a": 1.2, "b": 0.2}})
        self.assertEqual(d.resultados["factor_de_area"], sp.Rational(1, 5))
        self.assertAlmostEqual(sum(d.resultados["exponentes_lyapunov"]), math.log(0.2), places=9)
        self.assertSinFallos(d)

    def test_un_mapa_que_conserva_area(self):
        """(x, y) → (y, −x + 2y + ...)? El mapa estándar lineal (x + y, y) tiene det = 1."""
        d = desarrollar(ecuaciones=["x + y", "y"], variables_estado=["x", "y"], tipo_de_sistema="mapa_discreto")
        self.assertEqual(d.resultados["determinante"], 1)
        self.assertTrue(any("conserva" in c for c in d.conclusiones))

    def test_un_mapa_no_invertible(self):
        d = desarrollar(ecuaciones=["x**2 + y", "x**2"], variables_estado=["x", "y"],
                        tipo_de_sistema="mapa_discreto")
        self.assertFalse(d.resultados["invertible"])

    def test_el_enunciado_basta(self):
        resultado = analizar_caos_y_fractales({"enunciado": "Para el mapa de Hénon con a = 1.2 y b = 0.2 calcule "
                                                            "el determinante jacobiano y el inverso",
                                               "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["interpretacion"]["sistema_reconocido"]["parametros"], {"a": 1.2, "b": 0.2})


class SeccionDePoincareTests(SinFallos, unittest.TestCase):
    def test_balotario_5_4_corrige_la_mitad_de_la_seccion(self):
        d = desarrollar(**ROSSLER, pedidos=["seccion_poincare"],
                        seccion={"variable": "y", "valor": 0, "sentido": "creciente"})
        self.assertEqual(d.familia, "seccion_poincare")
        self.assertEqual(d.resultados["mitad_corregida"], "decreciente")
        self.assertAlmostEqual(d.resultados["maximo_de_g"], 5.78, delta=0.05)
        self.assertAlmostEqual(d.resultados["tiempo_de_retorno"], 5.86, delta=0.05)
        self.assertSinFallos(d, "seccion_delgada", "unimodal", "ramas_de_g", "lyapunov_por_el_mapa")

    def test_la_mitad_buena_pedida_directamente_no_se_corrige(self):
        d = desarrollar(**ROSSLER, pedidos=["seccion_poincare"],
                        seccion={"variable": "y", "valor": 0, "sentido": "decreciente"})
        self.assertNotIn("mitad_corregida", d.resultados)
        self.assertEqual(d.advertencias, [])
        self.assertSinFallos(d, "unimodal")

    def test_una_variable_que_no_existe(self):
        with self.assertRaisesRegex(DatoInvalido, "no es una variable"):
            desarrollar(**ROSSLER, seccion={"variable": "w", "valor": 0, "sentido": "creciente"})


class KaplanYorkeTests(SinFallos, unittest.TestCase):
    def test_balotario_5_5_con_el_sistema(self):
        d = desarrollar(**LORENZ, pedidos=["kaplan_yorke"], datos={"exponentes": [0.9056, 0.0, -14.5723]})
        self.assertEqual(d.familia, "kaplan_yorke")
        self.assertEqual(d.resultados["k"], 2)
        self.assertAlmostEqual(d.resultados["dimension_lyapunov"], 2 + 0.9056 / 14.5723, places=12)
        self.assertSinFallos(d, "suma_igual_divergencia", "espectro_dado_vs_calculado",
                             "dimension_con_el_espectro_calculado")

    def test_solo_con_los_exponentes(self):
        d = teorico("kaplan_yorke", "dimensión de Kaplan-Yorke", exponentes=[0.42, -1.62])
        self.assertEqual(d.resultados["k"], 1)
        self.assertAlmostEqual(d.resultados["dimension_lyapunov"], 1 + 0.42 / 1.62, places=12)

    def test_exponentes_desordenados_se_ordenan_y_se_avisa(self):
        d = teorico("kaplan_yorke", "Kaplan-Yorke", exponentes=[-14.5723, 0.9056, 0.0])
        self.assertAlmostEqual(d.resultados["dimension_lyapunov"], 2 + 0.9056 / 14.5723, places=12)
        self.assertTrue(any("ordenados" in a for a in d.advertencias))

    def test_casos_limite(self):
        d = teorico("kaplan_yorke", "Kaplan-Yorke", exponentes=[-0.5, -1.0])
        self.assertEqual((d.resultados["k"], d.resultados["dimension_lyapunov"]), (0, 0.0))
        d = teorico("kaplan_yorke", "Kaplan-Yorke", exponentes=[0.5, 0.1])
        self.assertEqual((d.resultados["k"], d.resultados["dimension_lyapunov"]), (2, 2.0))
        self.assertTrue(any("no es disipativo" in a for a in d.advertencias))

    def test_exponentes_que_no_son_del_sistema_se_advierten(self):
        d = desarrollar(**LORENZ, pedidos=["kaplan_yorke"], datos={"exponentes": [1.5, 0.0, -10.0]})
        self.assertTrue(any("no corresponde" in a for a in d.advertencias))
        nombres = {v.nombre: v.ok for v in d.validaciones}
        self.assertFalse(nombres["suma_igual_divergencia"])

    def test_cuantos_exponentes(self):
        with self.assertRaisesRegex(DatoInvalido, "uno por dimensión"):
            desarrollar(**LORENZ, pedidos=["kaplan_yorke"], datos={"exponentes": [0.9, -14.5]})


if __name__ == "__main__":
    unittest.main()
