"""Tema 4 del balotario: el problema 4.1 y el límite del alcance.

Del Tema 4 solo el 4.1 tiene solución en el balotario (exponente de Lyapunov
y horizonte de predictibilidad de un mapa unidimensional), así que es lo único
que el agente resuelve. Se prueba con el mapa tienda y con mapas equivalentes
con otros datos. Lo demás del Tema 4 y todo el Tema 5 debe quedar marcado como
FUERA DE ALCANCE POR AHORA, sin que el agente invente un resultado.
"""

import math
import unittest

import sympy as sp

from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_edo, analizar_equilibrios_sistema
from orquestacion.catalogo import cargar_catalogo

TIENDA = dict(ecuaciones=["1 - Abs(1 - 2*x)"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
              enunciado="Considere el mapa tienda. Calcule su exponente de Lyapunov y determine el tiempo "
                        "característico en que dos condiciones iniciales separadas por δ_0 = 10^{-10} divergen "
                        "hasta una distancia de orden 1.")


def desarrollar(**solicitud):
    problema = construir_problema(**solicitud)
    clasificacion = clasificar(problema)
    return clasificacion, clasificacion.familia.desarrollar(problema, clasificacion.datos)


class MapaUnidimensionalTests(unittest.TestCase):
    def assertSinFallos(self, desarrollo, *exigidas):
        hechas = {v.nombre for v in desarrollo.validaciones}
        self.assertEqual([v.nombre for v in desarrollo.validaciones if not v.ok and v.concluyente], [])
        for nombre in exigidas:
            self.assertIn(nombre, hechas)

    def test_balotario_4_1_derivada_y_puntos_fijos(self):
        _, d = desarrollar(**TIENDA, separacion_inicial=1e-10)
        self.assertEqual(d.familia, "mapa_1d")
        self.assertEqual(d.resultados["modulo_derivada"], 2)
        self.assertEqual(d.resultados["quiebres"], [sp.Rational(1, 2)])
        fijos = {f["punto"]: (f["multiplicador"], f["estabilidad"]) for f in d.resultados["puntos_fijos"]}
        self.assertEqual(fijos, {0: (2, "inestable (repulsor)"),
                                 sp.Rational(2, 3): (-2, "inestable (repulsor)")})

    def test_balotario_4_1_exponente_exacto_y_horizonte(self):
        _, d = desarrollar(**TIENDA, separacion_inicial=1e-10)
        self.assertEqual(d.resultados["lyapunov"], sp.log(2))
        self.assertEqual(d.resultados["horizonte"], 34)
        self.assertAlmostEqual(float(d.resultados["horizonte_exacto"]), math.log(1e10) / math.log(2), places=10)
        self.assertAlmostEqual(d.resultados["bits_por_iteracion"], 1.0, places=12)
        self.assertSinFallos(d, "lyapunov_numerico", "separacion_exponencial")
        self.assertEqual([g["clave"] for g in d.graficas], ["telarana", "convergencia_lyapunov", "separacion"])

    def test_el_enunciado_aporta_delta_cero(self):
        """δ₀ = 10^{-10} se lee del enunciado aunque no venga en `separacion_inicial`."""
        resultado = analizar_edo({**TIENDA, "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["interpretacion"]["separacion_inicial"], 1e-10)
        self.assertEqual(resultado["solucion"]["resultados"]["horizonte"], 34)

    def test_la_tienda_definida_a_trozos_da_lo_mismo(self):
        _, d = desarrollar(ecuaciones=["x"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
                           trozos=[{"expresion": "2*x", "desde": 0, "hasta": 0.5},
                                   {"expresion": "2*(1 - x)", "desde": 0.5, "hasta": 1}],
                           separacion_inicial=1e-10)
        self.assertEqual(d.resultados["lyapunov"], sp.log(2))
        self.assertEqual(d.resultados["horizonte"], 34)

    def test_equivalente_tienda_de_pendiente_tres_medios(self):
        _, d = desarrollar(ecuaciones=["x"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
                           trozos=[{"expresion": "3*x/2", "desde": 0, "hasta": 0.5},
                                   {"expresion": "3*(1 - x)/2", "desde": 0.5, "hasta": 1}],
                           separacion_inicial=1e-8)
        self.assertEqual(d.resultados["modulo_derivada"], sp.Rational(3, 2))
        self.assertEqual(d.resultados["lyapunov"], sp.log(sp.Rational(3, 2)))
        self.assertEqual(d.resultados["horizonte"], math.ceil(math.log(1e8) / math.log(1.5)))
        fijos = sorted(f["punto"] for f in d.resultados["puntos_fijos"])
        self.assertEqual(fijos, [0, sp.Rational(3, 5)])
        self.assertSinFallos(d, "lyapunov_numerico")

    def test_equivalente_asimetrico_se_estima_numericamente(self):
        """Pendientes 3 y −3/2: |f'| no es constante; λ = ln3/3 + (2/3)ln(3/2) ≈ 0.6365."""
        _, d = desarrollar(ecuaciones=["x"], variables_estado=["x"], tipo_de_sistema="mapa_discreto",
                           trozos=[{"expresion": "3*x", "desde": 0, "hasta": 1 / 3},
                                   {"expresion": "3*(1 - x)/2", "desde": 1 / 3, "hasta": 1}])
        self.assertNotIn("modulo_derivada", d.resultados)
        teorico = math.log(3) / 3 + 2 / 3 * math.log(1.5)
        estimado = d.resultados["lyapunov_estimado"]
        self.assertLess(abs(estimado["valor"] - teorico), 4 * estimado["error"] + 2e-3)
        self.assertSinFallos(d, "lyapunov_entre_orbitas")

    def test_mapa_logistico_caotico_y_periodico(self):
        """r = 3.8 da λ ≈ 0.43 > 0; r = 3.2 tiene un 2-ciclo estable: λ = ln(0.16)/2."""
        _, caotico = desarrollar(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametros={"r": 3.8},
                                 tipo_de_sistema="mapa_discreto")
        self.assertAlmostEqual(caotico.resultados["lyapunov_valor"], 0.4318, delta=0.01)
        _, periodico = desarrollar(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametros={"r": 3.2},
                                   tipo_de_sistema="mapa_discreto")
        self.assertAlmostEqual(periodico.resultados["lyapunov_valor"], math.log(0.16) / 2, places=4)
        self.assertTrue(any("no caótica" in c for c in periodico.conclusiones))

    def test_orbita_superestable(self):
        """x → 1 − x² converge al 2-ciclo {0, 1}, que pasa por f'(0) = 0: λ = −∞."""
        _, d = desarrollar(ecuaciones=["1 - x**2"], variables_estado=["x"], tipo_de_sistema="mapa_discreto")
        self.assertEqual(d.resultados["lyapunov"], -sp.oo)
        self.assertTrue(any("λ = −∞" in c for c in d.conclusiones))


class FueraDeAlcanceTests(unittest.TestCase):
    """Lo que el balotario no resuelve todavía se dice; no se sustituye por otra cosa."""

    @classmethod
    def setUpClass(cls):
        cls.indice = {p["id"]: p for t in cargar_catalogo() for p in t["problemas"]}

    def assertFueraDeAlcance(self, resultado, problema):
        self.assertTrue(resultado["ok"], resultado.get("error"))
        fuera = resultado["clasificacion"]["fuera_de_alcance"]
        self.assertIsNotNone(fuera)
        self.assertEqual(fuera["problema"], problema)
        desarrollo = resultado["desarrollo"]
        self.assertEqual(desarrollo["familia"], "numerico")
        self.assertEqual(sum("FUERA DE ALCANCE POR AHORA" in a for a in desarrollo["advertencias"]), 1)
        self.assertEqual(desarrollo["conclusiones"], [])

    def test_lorenz_disipativo_4_4(self):
        problema = self.indice["4.4"]
        e = problema["ecuacion"]
        resultado = analizar_edo(dict(ecuaciones=e["campo"], variables_estado=e["variables_estado"],
                                      parametros=e["parametros"], enunciado=problema["enunciado"],
                                      y0=[1, 1, 1], intervalo=[0, 20], visualizar=False))
        self.assertFueraDeAlcance(resultado, "4.4")
        # La integración numérica sí se hace, y se dice que es solo eso.
        self.assertIn("solucion_numerica", [s["clave"] for s in resultado["desarrollo"]["secciones"]])

    def test_duplicacion_de_periodo_4_2(self):
        resultado = analizar_equilibrios_sistema(dict(
            ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametro="r",
            tipo_de_sistema="mapa_discreto", enunciado=self.indice["4.2"]["enunciado"]))
        self.assertFueraDeAlcance(resultado, "4.2")

    def test_un_mapa_con_parametro_simbolico_es_4_2_aunque_no_haya_enunciado(self):
        resultado = analizar_equilibrios_sistema(dict(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"],
                                                      parametro="r", tipo_de_sistema="mapa_discreto"))
        self.assertFueraDeAlcance(resultado, "4.2")

    def test_henon_5_3(self):
        resultado = analizar_edo(dict(ecuaciones=["1 - a*x**2 + y", "b*x"], variables_estado=["x", "y"],
                                      parametros={"a": 1.4, "b": 0.3}, tipo_de_sistema="mapa_discreto",
                                      enunciado=self.indice["5.3"]["enunciado"], visualizar=False))
        self.assertFueraDeAlcance(resultado, "5.3")
        self.assertTrue(any("no se itera" in a for a in resultado["desarrollo"]["advertencias"]))

    def test_rossler_seccion_de_poincare_5_4(self):
        problema = self.indice["5.4"]
        e = problema["ecuacion"]
        resultado = analizar_edo(dict(ecuaciones=e["campo"], variables_estado=e["variables_estado"],
                                      parametros=e["parametros"], enunciado=problema["enunciado"],
                                      y0=[1, 1, 1], intervalo=[0, 50], visualizar=False))
        self.assertFueraDeAlcance(resultado, "5.4")

    def test_pedidos_de_temas_sin_resolver_en_texto_libre(self):
        casos = (("Calcule la dimensión de caja del conjunto de Cantor", "5.1"),
                 ("Describa la herradura de Smale", "5.2"),
                 ("Estime la dimensión de Kaplan-Yorke del atractor", "5.5"),
                 ("Halle el umbral de acumulación de la cascada de Feigenbaum", "4.3"))
        for enunciado, problema in casos:
            with self.subTest(problema=problema):
                resultado = analizar_equilibrios_sistema(dict(ecuaciones=["-x"], variables_estado=["x"],
                                                              enunciado=enunciado))
                self.assertFueraDeAlcance(resultado, problema)

    def test_el_bloque_de_caos_de_un_flujo_lo_declara(self):
        resultado = analizar_edo(dict(ecuaciones=["10*(y - x)", "28*x - y - x*z", "x*y - 8*z/3"],
                                      variables_estado=["x", "y", "z"], y0=[1, 1, 1], intervalo=[0, 20],
                                      analisis=["lyapunov"], visualizar=False))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        bloque = resultado["analisis"]["caos"]
        self.assertFalse(bloque["disponible"])
        self.assertEqual(bloque["estado"], "fuera_de_alcance")
        self.assertIn("FUERA DE ALCANCE POR AHORA", bloque["motivo"])


if __name__ == "__main__":
    unittest.main()
