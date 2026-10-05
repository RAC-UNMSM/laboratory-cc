"""Tema 2 del balotario: retratos de fase y análisis cualitativo en el plano.

Sistemas lineales (2.1, 2.2), no lineales con linealización (2.3),
hamiltonianos con órbita homoclínica (2.4) y ciclos límite por
Poincaré–Bendixson (2.5). Cada uno con el ejercicio del balotario y uno o más
equivalentes con otros datos, comprobando los resultados intermedios.

El 2.5 del balotario tiene un error: su sistema tiene el equilibrio (1, 0)
sobre el círculo r = 1, así que no hay órbita periódica. La prueba exige que el
agente lo detecte en lugar de repetir la conclusión del balotario.
"""

import unittest

import numpy as np
import sympy as sp

from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_edo, analizar_equilibrios_sistema

x, y = sp.symbols("x y")


def desarrollar(**solicitud):
    problema = construir_problema(**solicitud)
    clasificacion = clasificar(problema)
    return clasificacion, clasificacion.familia.desarrollar(problema, clasificacion.datos)


def plano(expresion):
    expresion = sp.sympify(expresion)
    return expresion.subs({s: sp.Symbol(s.name) for s in expresion.free_symbols})


class Tema2(unittest.TestCase):
    def assertIgual(self, calculada, esperada):
        self.assertEqual(sp.simplify(plano(calculada) - sp.sympify(esperada)), 0,
                         f"{calculada} no es {esperada}")

    def assertValidado(self, desarrollo, *nombres):
        hechas = {v.nombre: v for v in desarrollo.validaciones}
        for nombre in nombres:
            self.assertIn(nombre, hechas, f"falta la validación {nombre}")
            self.assertTrue(hechas[nombre].ok and hechas[nombre].concluyente, f"falló {nombre}")

    def assertSinFallos(self, desarrollo):
        fallidas = [v.nombre for v in desarrollo.validaciones if not v.ok and v.concluyente]
        self.assertEqual(fallidas, [])


class SistemaLinealTests(Tema2):
    """2.1: ẋ = 2x, ẏ = −3y."""

    def test_balotario_2_1_autovalores_y_silla(self):
        _, d = desarrollar(ecuaciones=["2*x", "-3*y"], variables_estado=["x", "y"], pedidos=["trayectorias"])
        self.assertEqual(d.familia, "lineal_plano")
        self.assertEqual(d.resultados["matriz"], sp.Matrix([[2, 0], [0, -3]]))
        self.assertEqual(sorted(d.resultados["autovalores"]), [-3, 2])
        vectores = {valor: list(vector) for valor, vector in d.resultados["autovectores"]}
        self.assertEqual(vectores[2], [1, 0])
        self.assertEqual(vectores[-3], [0, 1])
        self.assertEqual(d.resultados["clasificacion"], {"tipo": "punto silla", "estabilidad": "inestable"})

    def test_balotario_2_1_trayectorias_y_variedades(self):
        _, d = desarrollar(ecuaciones=["2*x", "-3*y"], variables_estado=["x", "y"], pedidos=["trayectorias"])
        self.assertEqual(plano(d.resultados["ecuacion_trayectorias"]), sp.Eq(x ** 3 * y ** 2, sp.Symbol("C")))
        self.assertEqual(plano(d.resultados["variedad_estable"]), sp.Eq(x, 0))
        self.assertEqual(plano(d.resultados["variedad_inestable"]), sp.Eq(y, 0))
        self.assertValidado(d, "invariante_de_las_orbitas", "solucion_general_satisface_el_sistema",
                            "clasificacion_contra_autovalores_numericos")
        self.assertEqual([s.clave for s in d.secciones],
                         ["forma_matricial", "autovalores", "clasificacion", "solucion_general",
                          "trayectorias", "variedades"])

    def test_equivalente_silla_no_alineada_con_los_ejes(self):
        """ẋ = x + y, ẏ = 4x + y: λ = 3, −1 con autovectores (1, 2) y (−1, 2)."""
        _, d = desarrollar(ecuaciones=["x + y", "4*x + y"], variables_estado=["x", "y"], pedidos=["trayectorias"])
        self.assertEqual(sorted(d.resultados["autovalores"]), [-1, 3])
        self.assertEqual(d.resultados["clasificacion"]["tipo"], "punto silla")
        self.assertEqual(plano(d.resultados["variedad_inestable"]), sp.Eq(2 * x - y, 0))
        self.assertEqual(plano(d.resultados["variedad_estable"]), sp.Eq(2 * x + y, 0))
        invariante = plano(d.resultados["ecuacion_trayectorias"].lhs)
        self.assertEqual(sp.expand(invariante - (y - 2 * x) ** 3 * (2 * x + y)), 0)
        self.assertSinFallos(d)

    def test_equivalente_foco_estable(self):
        _, d = desarrollar(ecuaciones=["-x - 2*y", "2*x - y"], variables_estado=["x", "y"])
        self.assertEqual(set(d.resultados["autovalores"]), {-1 - 2 * sp.I, -1 + 2 * sp.I})
        self.assertEqual(d.resultados["clasificacion"],
                         {"tipo": "foco estable", "estabilidad": "asintóticamente estable"})
        self.assertValidado(d, "solucion_general_satisface_el_sistema")

    def test_equivalente_centro_con_orbitas_elipticas(self):
        """ẋ = y, ẏ = −9x: las órbitas son las elipses 9x² + y² = C."""
        _, d = desarrollar(ecuaciones=["y", "-9*x"], variables_estado=["x", "y"], pedidos=["trayectorias"])
        self.assertEqual(d.familia, "lineal_plano")
        self.assertEqual(d.resultados["clasificacion"]["tipo"], "centro")
        self.assertEqual(plano(d.resultados["ecuacion_trayectorias"]), sp.Eq(9 * x ** 2 + y ** 2, sp.Symbol("C")))
        self.assertValidado(d, "invariante_de_las_orbitas")

    def test_con_condicion_inicial_da_la_solucion_particular(self):
        _, d = desarrollar(ecuaciones=["2*x", "-3*y"], variables_estado=["x", "y"], y0=[1, 1],
                           intervalo=[0, 0.5])
        particular = d.resultados["solucion_particular"]
        t = sp.Symbol("t")
        self.assertIgual(particular[0], sp.exp(2 * t))
        self.assertIgual(particular[1], sp.exp(-3 * t))
        self.assertValidado(d, "condicion_inicial_exacta")


class ClasificacionParametricaTests(Tema2):
    """2.2: ẋ = y, ẏ = −4x − γy con γ ≥ 0."""

    def _regimenes(self, d):
        return [(r.conjunto, r.tipo) for r in d.resultados["regimenes"]]

    def test_balotario_2_2_traza_determinante_y_discriminante(self):
        _, d = desarrollar(ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"],
                           parametro="gamma", rango_parametro=[0, None])
        gamma = sp.Symbol("gamma")
        self.assertEqual(d.familia, "lineal_plano_parametrico")
        self.assertIgual(d.resultados["traza"], -gamma)
        self.assertIgual(d.resultados["determinante"], 4)
        self.assertIgual(d.resultados["discriminante"], gamma ** 2 - 16)
        self.assertEqual(d.resultados["valores_criticos"], [0, 4])

    def test_balotario_2_2_regimenes(self):
        _, d = desarrollar(ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"],
                           parametro="gamma", rango_parametro=[0, None])
        self.assertEqual(self._regimenes(d), [
            (sp.FiniteSet(0), "centro"),
            (sp.Interval.open(0, 4), "foco estable"),
            (sp.FiniteSet(4), "nodo impropio (degenerado) estable"),
            (sp.Interval.open(4, sp.oo), "nodo estable"),
        ])
        self.assertValidado(d, "regimenes_contra_autovalores_numericos")
        claves = [g["clave"] for g in d.graficas]
        self.assertIn("traza_determinante", claves)
        self.assertEqual(sum(1 for c in claves if c.startswith("retrato_fase_")), 4)

    def test_equivalente_con_otra_rigidez(self):
        """ẏ = −9x − γy: el amortiguamiento crítico se mueve a γ = 6."""
        _, d = desarrollar(ecuaciones=["y", "-9*x - gamma*y"], variables_estado=["x", "y"],
                           parametro="gamma", rango_parametro=[0, None])
        self.assertEqual(d.resultados["valores_criticos"], [0, 6])
        self.assertEqual(self._regimenes(d)[2], (sp.FiniteSet(6), "nodo impropio (degenerado) estable"))

    def test_sin_restriccion_de_signo_aparecen_los_regimenes_inestables(self):
        _, d = desarrollar(ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"], parametro="gamma")
        tipos = [tipo for _, tipo in self._regimenes(d)]
        self.assertIn("nodo inestable", tipos)
        self.assertIn("foco inestable", tipos)
        self.assertSinFallos(d)


class NoLinealTests(Tema2):
    """2.3: competencia de dos especies en el cuadrante x, y ≥ 0."""

    BALOTARIO = dict(ecuaciones=["x*(3 - x - 2*y)", "y*(2 - x - y)"], variables_estado=["x", "y"],
                     region={"x": [0, None], "y": [0, None]})

    def test_balotario_2_3_equilibrios_y_jacobiano(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.familia, "no_lineal_plano")
        self.assertEqual(d.resultados["equilibrios"], [(0, 0), (0, 2), (1, 1), (3, 0)])
        J = plano(d.resultados["jacobiano"])
        self.assertEqual(sp.expand(J - sp.Matrix([[3 - 2 * x - 2 * y, -2 * x], [-y, 2 - x - 2 * y]])),
                         sp.zeros(2, 2))

    def test_balotario_2_3_clasificacion_de_cada_punto(self):
        _, d = desarrollar(**self.BALOTARIO)
        tipos = {e["punto"]: e["tipo"] for e in d.resultados["clasificacion"]}
        self.assertEqual(tipos, {(0, 0): "nodo inestable", (0, 2): "nodo estable",
                                 (1, 1): "punto silla", (3, 0): "nodo estable"})
        silla = next(e for e in d.resultados["clasificacion"] if e["punto"] == (1, 1))
        self.assertEqual(set(silla["autovalores"]), {-1 - sp.sqrt(2), -1 + sp.sqrt(2)})

    def test_balotario_2_3_nulclinas_y_cuencas(self):
        _, d = desarrollar(**self.BALOTARIO)
        nulclinas = d.resultados["nulclinas"]
        self.assertIn(sp.Eq(x + 2 * y, 3), [plano(c) for c in nulclinas["x"]])
        self.assertIn(sp.Eq(x + y, 2), [plano(c) for c in nulclinas["y"]])
        cuenca = d.resultados["cuencas"][0]
        self.assertEqual(cuenca["silla"], (1.0, 1.0))
        self.assertEqual(sorted(cuenca["atractores"]), [(0.0, 2.0), (3.0, 0.0)])
        self.assertValidado(d, "cuencas_separadas_por_variedad", "clasificacion_contra_autovalores_numericos")

    def test_equivalente_con_coexistencia_estable(self):
        """ẋ = x(3 − 2x − y), ẏ = y(2 − x − y): ahora (1, 1) es un nodo estable."""
        _, d = desarrollar(ecuaciones=["x*(3 - 2*x - y)", "y*(2 - x - y)"], variables_estado=["x", "y"],
                           region={"x": [0, None], "y": [0, None]})
        tipos = {e["punto"]: e["tipo"] for e in d.resultados["clasificacion"]}
        self.assertEqual(tipos[(1, 1)], "nodo estable")
        self.assertEqual(tipos[(sp.Rational(3, 2), 0)], "punto silla")
        self.assertNotIn("cuencas", d.resultados)
        self.assertTrue(any("P3 = (1, 1): Nodo asintóticamente estable" in c for c in d.conclusiones))
        self.assertSinFallos(d)

    def test_un_centro_lineal_no_decide_en_un_sistema_no_lineal(self):
        """Lotka-Volterra: λ = ±i en (1, 1); la linealización no basta (no hiperbólico)."""
        _, d = desarrollar(ecuaciones=["x*(1 - y)", "y*(x - 1)"], variables_estado=["x", "y"])
        punto = next(e for e in d.resultados["clasificacion"] if e["punto"] == (1, 1))
        self.assertEqual(punto["tipo"], "centro lineal")
        self.assertIn("no concluyente", punto["estabilidad"])


class HamiltonianoTests(Tema2):
    """2.4: ẋ = y, ẏ = x − x³ (pozo doble)."""

    def test_balotario_2_4_hamiltoniano_y_equilibrios(self):
        _, d = desarrollar(ecuaciones=["y", "x - x**3"], variables_estado=["x", "y"],
                           pedidos=["hamiltoniano", "separatriz"])
        self.assertEqual(d.familia, "conservativo")
        self.assertIgual(d.resultados["hamiltoniano"], "y**2/2 - x**2/2 + x**4/4")
        tipos = {e["punto"]: (e["tipo"], e["energia"]) for e in d.resultados["equilibrios"]}
        self.assertEqual(tipos[(0, 0)], ("punto silla", 0))
        self.assertEqual(tipos[(1, 0)], ("centro no lineal", -sp.Rational(1, 4)))
        self.assertEqual(tipos[(-1, 0)], ("centro no lineal", -sp.Rational(1, 4)))
        self.assertValidado(d, "integral_primera_conservada")

    def test_balotario_2_4_orbita_homoclinica(self):
        _, d = desarrollar(ecuaciones=["y", "x - x**3"], variables_estado=["x", "y"],
                           pedidos=["hamiltoniano", "separatriz"])
        self.assertIgual(d.resultados["separatriz"], "x*sqrt(1 - x**2/2)")
        self.assertEqual(d.resultados["energia_separatriz"], 0)
        self.assertEqual(d.resultados["dominio_separatriz"], sp.Interval(-sp.sqrt(2), sp.sqrt(2)))
        self.assertTrue(any("homoclínica" in c for c in d.conclusiones))

    def test_equivalente_con_otro_pozo(self):
        """ẏ = 4x − x³: centros en ±2 con H = −4 y lazo y = ±x√(4 − x²/2)."""
        _, d = desarrollar(ecuaciones=["y", "4*x - x**3"], variables_estado=["x", "y"],
                           pedidos=["hamiltoniano", "separatriz"])
        self.assertIgual(d.resultados["hamiltoniano"], "y**2/2 - 2*x**2 + x**4/4")
        self.assertIgual(d.resultados["separatriz"], "x*sqrt(4 - x**2/2)")
        self.assertEqual(d.resultados["dominio_separatriz"], sp.Interval(-2 * sp.sqrt(2), 2 * sp.sqrt(2)))
        energias = {e["punto"]: e["energia"] for e in d.resultados["equilibrios"]}
        self.assertEqual(energias[(2, 0)], -4)


class CicloLimiteTests(Tema2):
    """2.5 y un sistema equivalente que sí tiene ciclo límite."""

    BALOTARIO = dict(ecuaciones=["x - y - x*(x**2 + y**2) + x*y/sqrt(x**2 + y**2)",
                                 "x + y - y*(x**2 + y**2) - x**2/sqrt(x**2 + y**2)"],
                     variables_estado=["x", "y"], pedidos=["ciclo_limite"])

    def test_balotario_2_5_forma_polar(self):
        _, d = desarrollar(**self.BALOTARIO)
        r, theta = sp.symbols("r theta")
        self.assertEqual(d.familia, "ciclo_limite")
        self.assertIgual(plano(d.resultados["r_punto"]), r * (1 - r ** 2))
        self.assertIgual(plano(d.resultados["theta_punto"]), 1 - sp.cos(theta))

    def test_balotario_2_5_el_equilibrio_en_el_anillo_invalida_poincare_bendixson(self):
        """θ̇ = 1 − cos θ se anula en θ = 0: (1, 0) es un equilibrio dentro de K."""
        _, d = desarrollar(**self.BALOTARIO)
        self.assertIn((1, 0), d.resultados["equilibrios"])
        self.assertEqual(d.resultados["conclusion_poincare_bendixson"], "no_aplica_equilibrio_en_K")
        ciclo = d.resultados["ciclos"][0]
        self.assertEqual(ciclo["radio"], 1)
        self.assertFalse(ciclo["periodico"])
        self.assertTrue(any("NO es una órbita periódica" in c for c in d.conclusiones))
        self.assertValidado(d, "equilibrio_en_cartesianas", "convergencia_al_equilibrio")

    def test_equivalente_con_ciclo_limite_de_radio_dos(self):
        """ẋ = 4x − y − x r², ẏ = x + 4y − y r²: ṙ = r(4 − r²), θ̇ = 1."""
        _, d = desarrollar(ecuaciones=["4*x - y - x*(x**2 + y**2)", "x + 4*y - y*(x**2 + y**2)"],
                           variables_estado=["x", "y"], pedidos=["ciclo_limite"])
        r = sp.Symbol("r")
        self.assertIgual(plano(d.resultados["r_punto"]), r * (4 - r ** 2))
        self.assertIgual(d.resultados["theta_punto"], 1)
        self.assertEqual(d.resultados["radio_ciclo"], 2)
        self.assertEqual(d.resultados["periodo"], 2 * sp.pi)
        ciclo = d.resultados["ciclos"][0]
        self.assertTrue(ciclo["periodico"])
        self.assertTrue(ciclo["estable"])
        self.assertValidado(d, "convergencia_al_radio_invariante")


class FlujoDelTema2Tests(unittest.TestCase):
    def test_retrato_de_fase_primero_y_trayectoria_verificada(self):
        resultado = analizar_edo(dict(ecuaciones=["x*(3 - x - 2*y)", "y*(2 - x - y)"], variables_estado=["x", "y"],
                                      region={"x": [0, None], "y": [0, None]}, y0=[0.5, 0.5],
                                      intervalo=[0, 20], visualizar=True))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["visualizacion"]["figuras"][0], "retrato_fase")
        final = resultado["solucion"]["estado_final"]
        # (0.5, 0.5) está por debajo de la variedad estable de la silla (1, 1), que
        # sale con pendiente √2/2: gana la especie x y la órbita termina en (3, 0).
        np.testing.assert_allclose([final["x"], final["y"]], [3.0, 0.0], atol=1e-3)
        # Y desde arriba de esa variedad gana y: el estado final depende de la condición inicial.
        otro = analizar_edo(dict(ecuaciones=["x*(3 - x - 2*y)", "y*(2 - x - y)"], variables_estado=["x", "y"],
                                 y0=[0.5, 1.0], intervalo=[0, 20], visualizar=False))
        final = otro["solucion"]["estado_final"]
        np.testing.assert_allclose([final["x"], final["y"]], [0.0, 2.0], atol=1e-3)

    def test_clasificacion_segun_el_parametro_en_una_sola_llamada(self):
        resultado = analizar_equilibrios_sistema(dict(
            ecuaciones=["y", "-4*x - gamma*y"], variables_estado=["x", "y"], parametro="gamma",
            rango_parametro=[0, None],
            enunciado="Clasifique el equilibrio (0,0) del oscilador lineal según el parámetro γ ≥ 0"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "lineal_plano_parametrico")
        self.assertTrue(any("gamma = 4: nodo impropio" in c for c in resultado["desarrollo"]["conclusiones"]))


if __name__ == "__main__":
    unittest.main()
