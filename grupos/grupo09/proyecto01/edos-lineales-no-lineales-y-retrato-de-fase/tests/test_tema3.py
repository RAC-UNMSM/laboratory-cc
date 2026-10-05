"""Tema 3 del balotario: teoría de bifurcaciones.

Silla-nodo (3.1), transcrítica (3.2), horquillas super y subcrítica con
histéresis (3.3), Hopf (3.4) y homoclínica (3.5), cada una con el ejercicio
del balotario y equivalentes con otros datos. Además, la línea de fase de una
ecuación escalar con el parámetro ya fijado, que es el procedimiento de cada
régimen de 3.1–3.3.

El 3.5 del balotario tiene un error aritmético: su integral I₂ no es la
correcta y de ahí sale μc = −5/7. Lo que el agente calcula (I₂ = 36/35,
μ_M = −6/7) y el disparo numérico (μ* ≈ −0.8645) se comprueban aquí.
"""

import math
import unittest

import sympy as sp

from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_edo, analizar_equilibrios_sistema

x, mu = sp.symbols("x mu")


def desarrollar(**solicitud):
    problema = construir_problema(**solicitud)
    clasificacion = clasificar(problema)
    return clasificacion, clasificacion.familia.desarrollar(problema, clasificacion.datos)


def plano(expresion):
    expresion = sp.sympify(expresion)
    return expresion.subs({s: sp.Symbol(s.name) for s in expresion.free_symbols})


class Tema3(unittest.TestCase):
    def assertIgual(self, calculada, esperada):
        self.assertEqual(sp.simplify(plano(calculada) - sp.sympify(esperada)), 0,
                         f"{calculada} no es {esperada}")

    def assertSinFallos(self, desarrollo, *exigidas):
        hechas = {v.nombre: v for v in desarrollo.validaciones}
        fallidas = [v.nombre for v in desarrollo.validaciones if not v.ok and v.concluyente]
        self.assertEqual(fallidas, [])
        for nombre in exigidas:
            self.assertIn(nombre, hechas, f"falta la validación {nombre}")

    def ramas(self, d):
        return [(plano(r["expresion"]), r["existe_para"]) for r in d.resultados["ramas"]]

    def tramos(self, d):
        """{rama: [(intervalo, estado)]} con la estabilidad de cada rama por tramos de μ."""
        return {plano(r["expresion"]): [(t["intervalo"], t["estado"]) for t in r["tramos"]]
                for r in d.resultados["estabilidad_ramas"]}

    def critico(self, d, indice=0):
        return d.resultados["puntos_criticos"][indice]


class SillaNodoTests(Tema3):
    def test_balotario_3_1(self):
        _, d = desarrollar(ecuaciones=["mu - x**2"], variables_estado=["x"], parametro="mu")
        self.assertEqual(d.familia, "bifurcacion_1d")
        positivo = sp.Interval(0, sp.oo)
        self.assertEqual(self.ramas(d), [(-sp.sqrt(mu), positivo), (sp.sqrt(mu), positivo)])
        self.assertIgual(d.resultados["derivada"], -2 * x)
        tramos = self.tramos(d)
        self.assertEqual(tramos[sp.sqrt(mu)], [(sp.Interval.open(0, sp.oo), "estable")])
        self.assertEqual(tramos[-sp.sqrt(mu)], [(sp.Interval.open(0, sp.oo), "inestable")])
        critico = self.critico(d)
        self.assertEqual((critico["mu_c"], critico["x_c"], critico["tipo"]), (0, 0, "silla-nodo"))
        self.assertEqual(critico["derivadas"]["f_mu"], 1)
        self.assertEqual(critico["derivadas"]["f_xx"], -2)
        self.assertSinFallos(d, "ramas_anulan_el_campo", "ramas_contra_muestreo_numerico")
        self.assertEqual([g["clave"] for g in d.graficas], ["diagrama_bifurcacion"])

    def test_equivalente_con_las_ramas_del_otro_lado(self):
        """ẋ = μ + x²: los equilibrios ±√(−μ) existen para μ < 0 y la estable es la negativa."""
        _, d = desarrollar(ecuaciones=["mu + x**2"], variables_estado=["x"], parametro="mu")
        negativo = sp.Interval(-sp.oo, 0)
        self.assertEqual(self.ramas(d), [(-sp.sqrt(-mu), negativo), (sp.sqrt(-mu), negativo)])
        tramos = self.tramos(d)
        self.assertEqual(tramos[-sp.sqrt(-mu)], [(sp.Interval.open(-sp.oo, 0), "estable")])
        self.assertEqual(self.critico(d)["tipo"], "silla-nodo")
        self.assertSinFallos(d, "ramas_contra_muestreo_numerico")


class TranscriticaTests(Tema3):
    def test_balotario_3_2_intercambio_de_estabilidad(self):
        _, d = desarrollar(ecuaciones=["mu*x - x**2"], variables_estado=["x"], parametro="mu")
        self.assertEqual(self.ramas(d), [(0, sp.Reals), (mu, sp.Reals)])
        tramos = self.tramos(d)
        self.assertEqual(tramos[0], [(sp.Interval.open(-sp.oo, 0), "estable"),
                                     (sp.Interval.open(0, sp.oo), "inestable")])
        self.assertEqual(tramos[mu], [(sp.Interval.open(-sp.oo, 0), "inestable"),
                                      (sp.Interval.open(0, sp.oo), "estable")])
        critico = self.critico(d)
        self.assertEqual(critico["tipo"], "transcrítica")
        self.assertEqual((critico["derivadas"]["f_mu"], critico["derivadas"]["f_xmu"]), (0, 1))
        self.assertSinFallos(d, "ramas_contra_muestreo_numerico")

    def test_equivalente_con_otra_pendiente(self):
        """ẋ = μx + 2x²: la rama no trivial es x* = −μ/2."""
        _, d = desarrollar(ecuaciones=["mu*x + 2*x**2"], variables_estado=["x"], parametro="mu")
        self.assertIn((-mu / 2, sp.Reals), self.ramas(d))
        self.assertEqual(self.critico(d)["tipo"], "transcrítica")
        self.assertEqual(self.critico(d)["derivadas"]["f_xx"], 4)


class HorquillaTests(Tema3):
    def test_balotario_3_3a_supercritica(self):
        _, d = desarrollar(ecuaciones=["mu*x - x**3"], variables_estado=["x"], parametro="mu")
        self.assertTrue(d.resultados["simetria"])
        self.assertEqual(len(self.ramas(d)), 3)
        critico = self.critico(d)
        self.assertEqual(critico["tipo"], "de horquilla supercrítica")
        self.assertEqual((critico["derivadas"]["f_xmu"], critico["derivadas"]["f_xxx"]), (1, -6))
        self.assertNotIn("biestabilidad", d.resultados)
        self.assertSinFallos(d, "ramas_contra_muestreo_numerico")

    def test_equivalente_subcritica(self):
        _, d = desarrollar(ecuaciones=["mu*x + x**3"], variables_estado=["x"], parametro="mu")
        self.assertEqual(self.critico(d)["tipo"], "de horquilla subcrítica")
        tramos = self.tramos(d)
        self.assertEqual(tramos[sp.sqrt(-mu)], [(sp.Interval.open(-sp.oo, 0), "inestable")])

    def test_balotario_3_3b_subcritica_con_histeresis(self):
        _, d = desarrollar(ecuaciones=["mu*x + x**3 - x**5"], variables_estado=["x"], parametro="mu")
        tipos = sorted({(c["mu_c"], c["tipo"]) for c in d.resultados["puntos_criticos"]}, key=lambda c: c[0])
        self.assertEqual(tipos, [(-sp.Rational(1, 4), "silla-nodo"), (0, "de horquilla subcrítica")])
        self.assertEqual(d.resultados["biestabilidad"], sp.Interval.open(-sp.Rational(1, 4), 0))
        self.assertEqual(d.resultados["ancho_histeresis"], sp.Rational(1, 4))
        saltos = {s["mu"]: s for s in d.resultados["saltos"]}
        self.assertEqual(sorted(saltos[0]["hasta"]), [-1, 1])
        self.assertEqual(saltos[-sp.Rational(1, 4)]["hasta"], [0])
        self.assertTrue(any("histéresis de ancho 1/4" in c for c in d.conclusiones))
        self.assertSinFallos(d, "ramas_contra_muestreo_numerico")


class HopfTests(Tema3):
    def test_balotario_3_4_supercritica(self):
        clasificacion, d = desarrollar(ecuaciones=["mu*x - y - x*(x**2 + y**2)", "x + mu*y - y*(x**2 + y**2)"],
                                       variables_estado=["x", "y"], parametro="mu")
        self.assertEqual(d.familia, "hopf")
        self.assertIgual(d.resultados["alfa"], mu)
        self.assertEqual(d.resultados["omega"], 1)
        self.assertEqual(d.resultados["transversalidad"], 1)
        self.assertIgual(d.resultados["radio_ciclo"], sp.sqrt(mu))
        self.assertEqual(d.resultados["periodo"], 2 * sp.pi)
        self.assertEqual(d.resultados["coeficiente_lyapunov"], -1)
        self.assertEqual(d.resultados["tipo_hopf"], "supercrítica")
        self.assertSinFallos(d, "condicion_espectral", "condicion_transversalidad", "radio_del_ciclo_numerico")

    def test_equivalente_con_otra_frecuencia(self):
        """ω = 2: el periodo del ciclo es π."""
        _, d = desarrollar(ecuaciones=["mu*x - 2*y - x*(x**2 + y**2)", "2*x + mu*y - y*(x**2 + y**2)"],
                           variables_estado=["x", "y"], parametro="mu")
        self.assertEqual(d.resultados["omega"], 2)
        self.assertEqual(d.resultados["periodo"], sp.pi)
        self.assertEqual(d.resultados["tipo_hopf"], "supercrítica")

    def test_equivalente_subcritica_con_ciclo_inestable(self):
        _, d = desarrollar(ecuaciones=["mu*x - y + x*(x**2 + y**2)", "x + mu*y + y*(x**2 + y**2)"],
                           variables_estado=["x", "y"], parametro="mu")
        self.assertEqual(d.resultados["coeficiente_lyapunov"], 1)
        self.assertEqual(d.resultados["tipo_hopf"], "subcrítica")
        self.assertIgual(d.resultados["radio_ciclo"], sp.sqrt(-mu))
        self.assertFalse(d.resultados["ciclo_estable"])
        self.assertSinFallos(d, "radio_del_ciclo_numerico")


class HomoclinicaTests(Tema3):
    """3.5: ẋ = y, ẏ = μy + x − x² + xy (es el caso más lento: incluye un disparo numérico)."""

    @classmethod
    def setUpClass(cls):
        _, cls.d = desarrollar(ecuaciones=["y", "mu*y + x - x**2 + x*y"], variables_estado=["x", "y"],
                               parametro="mu", metodo="homoclinica")

    def test_sistema_no_perturbado_y_lazo(self):
        d = self.d
        self.assertEqual(d.familia, "homoclinica")
        self.assertIgual(d.resultados["hamiltoniano"], "y**2/2 - x**2/2 + x**3/3")
        self.assertIgual(d.resultados["perturbacion"], "mu*y + x*y")
        self.assertIgual(d.resultados["lazo_homoclinico"], "x*sqrt(1 - 2*x/3)")
        self.assertEqual(d.resultados["dominio_lazo"], sp.Interval(0, sp.Rational(3, 2)))

    def test_hopf_local_previo(self):
        hopf = self.d.resultados["hopf_local"]
        self.assertEqual(hopf["punto"], (1, 0))
        self.assertEqual(hopf["mu"], -1)
        self.assertEqual(hopf["a"], -sp.Rational(1, 8))

    def test_integral_de_melnikov(self):
        d = self.d
        self.assertEqual(d.resultados["I1"], sp.Rational(6, 5))
        self.assertEqual(d.resultados["I2"], sp.Rational(36, 35))
        self.assertEqual(d.resultados["mu_melnikov"], -sp.Rational(6, 7))
        # El balotario escribe μc = −5/7; con I₂ = 36/35 el cero de M(μ) es −6/7.
        self.assertNotEqual(d.resultados["mu_melnikov"], -sp.Rational(5, 7))

    def test_disparo_numerico_y_existencia_del_ciclo(self):
        d = self.d
        self.assertAlmostEqual(d.resultados["mu_numerico"], -0.8645, places=3)
        self.assertEqual(d.resultados["lado_del_ciclo"], "<")
        existe = d.resultados["existe_ciclo_para"]
        self.assertEqual(existe.inf, -1)
        self.assertAlmostEqual(float(existe.sup), -0.8645, places=3)
        self.assertTrue(any("nace en el Hopf de mu = -1" in c for c in d.conclusiones))
        self.assertSinFallos(d, "melnikov_vs_disparo", "divergencia_logaritmica_del_periodo")


class LineaDeFaseTests(Tema3):
    """Equilibrios de ẋ = f(x) con el parámetro fijado: el procedimiento de cada régimen."""

    def test_silla_nodo_con_mu_fijado(self):
        _, d = desarrollar(ecuaciones=["mu - x**2"], variables_estado=["x"], parametros={"mu": 1.0},
                           pedidos=["equilibrios"])
        self.assertEqual(d.familia, "equilibrios_1d")
        clases = {e["punto"]: e["estabilidad"] for e in d.resultados["equilibrios"]}
        self.assertEqual(clases, {-1: "inestable", 1: "asintóticamente estable"})
        estable = next(e for e in d.resultados["equilibrios"] if e["punto"] == 1)
        self.assertEqual(estable["cuenca"], sp.Interval.open(-1, sp.oo))
        self.assertSinFallos(d, "equilibrios_anulan_el_campo", "linea_de_fase_coherente")

    def test_tres_equilibrios_alternados(self):
        _, d = desarrollar(ecuaciones=["x*(1 - x)*(x - 2)"], variables_estado=["x"], pedidos=["equilibrios"])
        tipos = [e["tipo"] for e in d.resultados["equilibrios"]]
        self.assertEqual(tipos, ["atractor", "repulsor", "atractor"])
        sentidos = [t["sentido"] for t in d.resultados["linea_de_fase"]]
        self.assertEqual(sentidos, ["crece", "decrece", "crece", "decrece"])

    def test_equilibrios_no_hiperbolicos(self):
        for campo, tipo, por_linea in (("x**2", "semiestable", "semiestable"),
                                       ("x**3", "repulsor no hiperbólico", "inestable"),
                                       ("-x**3", "atractor no hiperbólico", "estable")):
            with self.subTest(campo=campo):
                _, d = desarrollar(ecuaciones=[campo], variables_estado=["x"], pedidos=["equilibrios"])
                (equilibrio,) = d.resultados["equilibrios"]
                self.assertFalse(equilibrio["hiperbolico"])
                self.assertEqual(equilibrio["tipo"], tipo)
                self.assertEqual(equilibrio["por_linea_de_fase"], por_linea)
                self.assertSinFallos(d, "linea_de_fase_coherente")

    def test_infinitos_equilibrios_en_una_ventana(self):
        _, d = desarrollar(ecuaciones=["sin(x)"], variables_estado=["x"], pedidos=["equilibrios"])
        puntos = [e["punto"] for e in d.resultados["equilibrios"]]
        self.assertEqual(puntos, [k * sp.pi for k in range(-3, 4)])
        # Las cuencas que tocarían el borde de la ventana no se informan: no se conocen.
        extremo = next(e for e in d.resultados["equilibrios"] if e["punto"] == -3 * sp.pi)
        self.assertNotIn("cuenca", extremo)
        centro = next(e for e in d.resultados["equilibrios"] if e["punto"] == sp.pi)
        self.assertEqual(centro["cuenca"], sp.Interval.open(0, 2 * sp.pi))

    def test_sin_equilibrios(self):
        _, d = desarrollar(ecuaciones=["1 + x**2"], variables_estado=["x"], pedidos=["equilibrios"])
        self.assertNotIn("equilibrios", d.resultados)
        self.assertTrue(any("No hay equilibrios" in c for c in d.conclusiones))


class FlujoDelTema3Tests(unittest.TestCase):
    def test_una_sola_llamada_estudia_toda_la_bifurcacion(self):
        resultado = analizar_equilibrios_sistema(dict(
            ecuaciones=["mu - x**2"], variables_estado=["x"], parametro="mu",
            enunciado="Estudie los puntos fijos, su estabilidad y dibuje el diagrama de bifurcación"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "bifurcacion_1d")
        self.assertEqual(resultado["visualizacion"]["figuras"], ["diagrama_bifurcacion"])

    def test_con_el_parametro_fijado_la_herramienta_de_equilibrios_da_la_linea_de_fase(self):
        resultado = analizar_equilibrios_sistema(dict(ecuaciones=["mu - x**2"], variables_estado=["x"],
                                                      parametros={"mu": 1.0}))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "equilibrios_1d")
        self.assertEqual(resultado["visualizacion"]["figuras"], ["linea_fase"])

    def test_hopf_con_condicion_inicial_integra_ademas_la_trayectoria(self):
        resultado = analizar_edo(dict(
            ecuaciones=["mu*x - y - x*(x**2 + y**2)", "x + mu*y - y*(x**2 + y**2)"],
            variables_estado=["x", "y"], parametro="mu", parametros={"mu": 0.25},
            y0=[0.05, 0], intervalo=[0, 80], visualizar=False))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        final = resultado["solucion"]["estado_final"]
        self.assertAlmostEqual(math.hypot(final["x"], final["y"]), 0.5, places=4)


if __name__ == "__main__":
    unittest.main()
