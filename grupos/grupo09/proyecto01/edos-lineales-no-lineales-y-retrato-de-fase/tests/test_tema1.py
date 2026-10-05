"""Tema 1 del balotario: EDOs de primer orden, Cauchy-Euler y el péndulo.

Cada familia se prueba con el ejercicio del balotario y con al menos uno
equivalente con otros datos. Lo que se comprueba no es solo la respuesta
final: también los resultados intermedios que el procedimiento produce (las
primitivas, el factor integrante, la sustitución, la ecuación indicial, el
wronskiano...), porque son los que el agente presenta como desarrollo.
"""

import math
import unittest

import sympy as sp
from scipy.special import ellipk

from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_edo

x, t, C = sp.symbols("x t C")


def desarrollar(**solicitud):
    """(clasificación, desarrollo) del problema, por la misma ruta que usa el agente."""
    problema = construir_problema(**solicitud)
    clasificacion = clasificar(problema)
    return clasificacion, clasificacion.familia.desarrollar(problema, clasificacion.datos)


def plano(expresion):
    """La expresión con símbolos sin supuestos, para compararla con una escrita a mano."""
    expresion = sp.sympify(expresion)
    return expresion.subs({s: sp.Symbol(s.name) for s in expresion.free_symbols})


class Tema1(unittest.TestCase):
    def assertIgual(self, calculada, esperada):
        diferencia = sp.simplify(plano(calculada) - sp.sympify(esperada))
        self.assertEqual(diferencia, 0, f"{calculada} no es {esperada}")

    def assertValidado(self, desarrollo, *nombres):
        hechas = {v.nombre: v for v in desarrollo.validaciones}
        for nombre in nombres:
            self.assertIn(nombre, hechas, f"falta la validación {nombre}")
            self.assertTrue(hechas[nombre].ok, f"la validación {nombre} falló")
            self.assertTrue(hechas[nombre].concluyente, f"la validación {nombre} no fue concluyente")


class SeparableTests(Tema1):
    """1.1: dy/dx = 3xy², y(0) = 1, con intervalo maximal."""

    BALOTARIO = dict(ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x",
                     y0=[1], intervalo=[0, 0.7], pedidos=["intervalo_maximo"])

    def test_balotario_1_1_separacion_e_integracion(self):
        clasificacion, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.familia, "separable")
        self.assertIn("bernoulli", [f.clave for f, _ in clasificacion.compatibles])
        self.assertIgual(d.resultados["g"], "3*x")
        self.assertIgual(d.resultados["h"], "y**2")
        self.assertIgual(d.resultados["primitiva_y"], "-1/y")
        self.assertIgual(d.resultados["primitiva_x"], "3*x**2/2")
        self.assertEqual(d.resultados["soluciones_constantes"], [0])

    def test_balotario_1_1_constante_solucion_e_intervalo_maximal(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertIgual(d.resultados["solucion_general"], "-2/(2*C + 3*x**2)")
        self.assertEqual(d.resultados["constante"], -1)
        self.assertIgual(d.resultados["solucion_particular"], "2/(2 - 3*x**2)")
        intervalo = d.resultados["intervalo_maximal"]
        self.assertEqual(intervalo, sp.Interval.open(-sp.sqrt(6) / 3, sp.sqrt(6) / 3))
        self.assertAlmostEqual(float(intervalo.sup), math.sqrt(2 / 3), places=14)
        self.assertValidado(d, "integracion_correcta", "solucion_general_satisface_la_edo",
                            "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")
        self.assertEqual([s.clave for s in d.secciones],
                         ["separacion", "integracion", "despeje", "condicion_inicial", "intervalo_maximal"])

    def test_equivalente_sin_singularidad(self):
        """dy/dx = −2xy², y(0) = 1: misma familia, solución 1/(1 + x²) definida en todo ℝ."""
        _, d = desarrollar(ecuaciones=["-2*x*y**2"], variables_estado=["y"], variable_independiente="x",
                           y0=[1], intervalo=[0, 2])
        self.assertEqual(d.familia, "separable")
        self.assertIgual(d.resultados["primitiva_x"], "-x**2")
        self.assertIgual(d.resultados["solucion_particular"], "1/(1 + x**2)")
        self.assertNotIn("intervalo_maximal", d.resultados)
        self.assertValidado(d, "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")

    def test_equivalente_con_otro_intervalo_maximal(self):
        """dy/dx = 2xy², y(0) = 1 explota en x = ±1."""
        _, d = desarrollar(ecuaciones=["2*x*y**2"], variables_estado=["y"], variable_independiente="x",
                           y0=[1], intervalo=[0, 0.5], pedidos=["intervalo_maximo"])
        self.assertIgual(d.resultados["solucion_particular"], "1/(1 - x**2)")
        self.assertEqual(d.resultados["intervalo_maximal"], sp.Interval.open(-1, 1))
        self.assertTrue(any("explota en x = -1, x = 1" in c for c in d.conclusiones))

    def test_condicion_inicial_sobre_una_solucion_constante(self):
        """y(0) = 0 está sobre h(y) = 0: por unicidad la solución es y ≡ 0."""
        _, d = desarrollar(ecuaciones=["3*x*y**2"], variables_estado=["y"], variable_independiente="x",
                           y0=[0], intervalo=[0, 1])
        self.assertEqual(d.resultados["solucion_particular"], 0)
        self.assertNotIn("solucion_general", d.resultados)
        self.assertValidado(d, "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")


class LinealTests(Tema1):
    """y' + P(x)y = Q(x): factor integrante, como en los pasos 5 y 6 del 1.2."""

    def test_factor_integrante_con_coeficiente_variable(self):
        _, d = desarrollar(ecuaciones=["-y/x + x**2"], variables_estado=["y"], variable_independiente="x",
                           y0=[1], intervalo=[1, 3])
        self.assertEqual(d.familia, "lineal")
        self.assertIgual(d.resultados["P"], "1/x")
        self.assertIgual(d.resultados["Q"], "x**2")
        self.assertIgual(d.resultados["factor_integrante"], "x")
        self.assertIgual(d.resultados["solucion_general"], "C/x + x**3/4")
        self.assertEqual(d.resultados["constante"], sp.Rational(3, 4))
        self.assertIgual(d.resultados["solucion_particular"], "(x**4 + 3)/(4*x)")
        self.assertEqual(d.resultados["intervalo_maximal"], sp.Interval.open(0, sp.oo))
        self.assertValidado(d, "solucion_general_satisface_la_edo", "solucion_particular_satisface_la_edo",
                            "condicion_inicial_exacta")

    def test_factor_integrante_exponencial(self):
        _, d = desarrollar(ecuaciones=["-2*y + exp(-t)"], variables_estado=["y"], y0=[0], intervalo=[0, 3])
        self.assertEqual(d.familia, "lineal")
        self.assertIgual(d.resultados["factor_integrante"], "exp(2*t)")
        self.assertIgual(d.resultados["solucion_general"], "C*exp(-2*t) + exp(-t)")
        self.assertIgual(d.resultados["solucion_particular"], "exp(-t) - exp(-2*t)")


class BernoulliTests(Tema1):
    """1.2: y' + y = y³, y(0) = 1."""

    BALOTARIO = dict(ecuaciones=["y**3 - y"], variables_estado=["y"], variable_independiente="x",
                     y0=[1], intervalo=[0, 5], metodo="bernoulli",
                     enunciado="Resuelva la ecuación diferencial ordinaria de Bernoulli y' + y = y^3, y(0) = 1")

    def test_balotario_1_2_el_metodo_pedido_se_respeta(self):
        """La ecuación también es separable, pero el enunciado pide Bernoulli."""
        clasificacion, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.familia, "bernoulli")
        self.assertEqual({f.clave for f, _ in clasificacion.compatibles}, {"separable", "bernoulli"})

    def test_balotario_1_2_cambio_de_variable_y_ecuacion_lineal(self):
        _, d = desarrollar(**self.BALOTARIO)
        v = sp.Symbol("v")
        self.assertEqual(d.resultados["n"], 3)
        self.assertIgual(d.resultados["P"], 1)
        self.assertIgual(d.resultados["Q"], 1)
        self.assertEqual(plano(d.resultados["sustitucion"]), sp.Eq(v, sp.Symbol("y") ** -2))
        self.assertIgual(d.resultados["ecuacion_lineal"].rhs, -2)
        self.assertIgual(d.resultados["v_factor_integrante"], "exp(-2*x)")
        self.assertIgual(d.resultados["v_solucion_general"], "C*exp(2*x) + 1")
        self.assertIgual(d.resultados["solucion_general"], "1/sqrt(1 + C*exp(2*x))")
        self.assertEqual(d.resultados["solucion_trivial"], 0)

    def test_balotario_1_2_la_condicion_inicial_cae_en_el_equilibrio(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.resultados["constante"], 0)
        self.assertEqual(d.resultados["solucion_particular"], 1)
        self.assertTrue(any("equilibrio" in c for c in d.conclusiones))
        self.assertValidado(d, "solucion_general_satisface_la_edo", "solucion_particular_satisface_la_edo",
                            "condicion_inicial_exacta")

    def test_equivalente_con_n_igual_a_dos(self):
        """y' = y² − 2y, y(0) = 1: v = 1/y y la logística."""
        _, d = desarrollar(ecuaciones=["y**2 - 2*y"], variables_estado=["y"], variable_independiente="x",
                           y0=[1], intervalo=[0, 3], metodo="bernoulli")
        self.assertEqual(d.resultados["n"], 2)
        self.assertIgual(d.resultados["v_solucion_general"], "C*exp(2*x) + 1/2")
        self.assertIgual(d.resultados["solucion_particular"], "2/(exp(2*x) + 1)")
        self.assertValidado(d, "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")

    def test_equivalente_con_coeficiente_variable(self):
        """y' − y = −xy³: Q depende de x y la ecuación lineal en v necesita integrar por partes."""
        clasificacion, d = desarrollar(ecuaciones=["y - x*y**3"], variables_estado=["y"],
                                       variable_independiente="x", y0=[1], intervalo=[0, 2])
        self.assertEqual(d.familia, "bernoulli")
        self.assertEqual([f.clave for f, _ in clasificacion.compatibles], ["bernoulli"])
        self.assertIgual(d.resultados["v_solucion_general"], "C*exp(-2*x) + x - 1/2")
        self.assertIgual(d.resultados["solucion_general"], "1/sqrt(C*exp(-2*x) + x - 1/2)")
        self.assertEqual(d.resultados["constante"], sp.Rational(3, 2))
        self.assertValidado(d, "solucion_general_satisface_la_edo", "solucion_particular_satisface_la_edo",
                            "condicion_inicial_exacta")


class RiccatiTests(Tema1):
    """1.4: y' = y² − 2xy + x² + 1 con y₁ = x."""

    BALOTARIO = dict(ecuaciones=["y**2 - 2*x*y + x**2 + 1"], variables_estado=["y"],
                     variable_independiente="x", solucion_particular="x", y0=[-1], intervalo=[0, 3])

    def test_balotario_1_4_verifica_la_particular_y_linealiza(self):
        _, d = desarrollar(**self.BALOTARIO)
        u = sp.Symbol("u")
        self.assertEqual(d.familia, "riccati")
        self.assertIgual(d.resultados["q2"], 1)
        self.assertIgual(d.resultados["q1"], "-2*x")
        self.assertIgual(d.resultados["q0"], "x**2 + 1")
        self.assertIgual(d.resultados["solucion_particular_conocida"], "x")
        self.assertEqual(plano(d.resultados["sustitucion"]), sp.Eq(sp.Symbol("y"), x + 1 / u))
        self.assertIgual(d.resultados["ecuacion_lineal"].rhs, -1)
        self.assertIgual(d.resultados["u_solucion_general"], "C - x")
        self.assertIgual(d.resultados["solucion_general"], "x + 1/(C - x)")
        self.assertValidado(d, "particular_satisface_la_edo", "solucion_general_satisface_la_edo")

    def test_balotario_1_4_pvi_y_su_intervalo(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.resultados["constante"], -1)
        self.assertIgual(d.resultados["solucion_particular"], "x - 1/(1 + x)")
        self.assertEqual(d.resultados["intervalo_maximal"], sp.Interval.open(-1, sp.oo))
        self.assertValidado(d, "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")

    def test_equivalente_sin_particular_dada_la_busca(self):
        """y' = y² − 2x²y + x⁴ + 2x: la particular polinómica y₁ = x² se encuentra sola."""
        _, d = desarrollar(ecuaciones=["y**2 - 2*x**2*y + x**4 + 2*x"], variables_estado=["y"],
                           variable_independiente="x", y0=[1], intervalo=[0, 0.5])
        self.assertIgual(d.resultados["solucion_particular_conocida"], "x**2")
        self.assertIgual(d.resultados["solucion_general"], "x**2 + 1/(C - x)")
        self.assertIgual(d.resultados["solucion_particular"], "x**2 + 1/(1 - x)")
        self.assertValidado(d, "solucion_particular_satisface_la_edo", "condicion_inicial_exacta")

    def test_la_condicion_inicial_sobre_la_particular_da_la_particular(self):
        """y(0) = 0 con y₁ = x²: C no es finita y la solución es y₁ misma."""
        _, d = desarrollar(ecuaciones=["y**2 - 2*x**2*y + x**4 + 2*x"], variables_estado=["y"],
                           variable_independiente="x", y0=[0], intervalo=[0, 1])
        self.assertIgual(d.resultados["solucion_particular"], "x**2")

    def test_una_particular_falsa_no_se_acepta(self):
        """Si y₁ no satisface la ecuación, el método no se aplica (y lo dice)."""
        from matematica import MetodoNoAplicable
        with self.assertRaises(MetodoNoAplicable):
            desarrollar(**{**self.BALOTARIO, "solucion_particular": "x + 1"})


class CauchyEulerTests(Tema1):
    """1.3: x²y'' − 2xy' + 2y = x³ ln x."""

    BALOTARIO = dict(ecuaciones=["yp", "(2*x*yp - 2*y + x**3*log(x))/x**2"], variables_estado=["y", "yp"],
                     variable_independiente="x")

    def test_balotario_1_3_ecuacion_indicial_y_homogenea(self):
        _, d = desarrollar(**self.BALOTARIO)
        m = sp.Symbol("m")
        self.assertEqual(d.familia, "cauchy_euler")
        self.assertEqual((d.resultados["a"], d.resultados["b"], d.resultados["c"]), (1, -2, 2))
        self.assertIgual(d.resultados["ecuacion_indicial"], m ** 2 - 3 * m + 2)
        self.assertEqual(d.resultados["raices"], [1, 2])
        self.assertEqual(d.resultados["caso_raices"], "reales distintas")
        self.assertIgual(d.resultados["solucion_homogenea"], "c_1*x + c_2*x**2")

    def test_balotario_1_3_variacion_de_parametros(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertIgual(d.resultados["wronskiano"], "x**2")
        self.assertIgual(d.resultados["g"], "x*log(x)")
        self.assertIgual(d.resultados["u1_prima"], "-x*log(x)")
        self.assertIgual(d.resultados["u2_prima"], "log(x)")
        self.assertIgual(d.resultados["u1"], "-x**2*log(x)/2 + x**2/4")
        self.assertIgual(d.resultados["u2"], "x*log(x) - x")
        self.assertIgual(d.resultados["solucion_particular_no_homogenea"], "x**3*log(x)/2 - 3*x**3/4")
        self.assertIgual(d.resultados["solucion_general"], "c_1*x + c_2*x**2 + x**3*log(x)/2 - 3*x**3/4")
        self.assertValidado(d, "solucion_satisface_la_edo")

    def test_equivalente_con_raices_de_signo_opuesto(self):
        """x²y'' + xy' − 4y = x²: m = ±2."""
        _, d = desarrollar(ecuaciones=["yp", "(-x*yp + 4*y + x**2)/x**2"], variables_estado=["y", "yp"],
                           variable_independiente="x")
        self.assertEqual(d.resultados["raices"], [-2, 2])
        self.assertIgual(d.resultados["wronskiano"], "4/x")
        self.assertIgual(d.resultados["solucion_particular_no_homogenea"], "x**2*log(x)/4 - x**2/16")
        self.assertValidado(d, "solucion_satisface_la_edo")

    def test_equivalente_con_raiz_doble(self):
        """x²y'' + 3xy' + y = ln x: m = −1 doble, sistema fundamental {1/x, ln x/x}."""
        _, d = desarrollar(ecuaciones=["yp", "(-3*x*yp - y + log(x))/x**2"], variables_estado=["y", "yp"],
                           variable_independiente="x")
        self.assertEqual(d.resultados["caso_raices"], "doble")
        self.assertIgual(d.resultados["sistema_fundamental"][1], "log(x)/x")
        self.assertIgual(d.resultados["solucion_particular_no_homogenea"], "log(x) - 2")
        self.assertValidado(d, "solucion_satisface_la_edo")

    def test_con_condicion_inicial_fija_las_constantes(self):
        """y(1) = −3/4, y'(1) = −7/4 aísla y_p (c₁ = c₂ = 0), como el catálogo."""
        _, d = desarrollar(**self.BALOTARIO, y0=[-0.75, -1.75], intervalo=[1, 3])
        self.assertIgual(d.resultados["solucion_particular"], "x**3*log(x)/2 - 3*x**3/4")


class PenduloTests(Tema1):
    """1.5: θ'' + ω₀² sen θ = 0 con ω₀ simbólico."""

    BALOTARIO = dict(ecuaciones=["thetapunto", "-w0**2*sin(theta)"], variables_estado=["theta", "thetapunto"],
                     parametros={"w0": 1.0}, parametro="w0", rango_parametro=[0, None],
                     pedidos=["energia", "separatriz", "periodo"], y0=[math.pi / 3, 0], intervalo=[0, 20])

    def test_balotario_1_5_integral_primera_y_separatriz(self):
        _, d = desarrollar(**self.BALOTARIO)
        self.assertEqual(d.familia, "conservativo")
        self.assertIgual(d.resultados["hamiltoniano"], "thetapunto**2/2 - w0**2*cos(theta)")
        self.assertIgual(d.resultados["separatriz"], "2*w0*cos(theta/2)")
        self.assertIgual(d.resultados["energia_separatriz"], "w0**2")
        tipos = {tuple(plano(c) for c in e["punto"]): e["tipo"] for e in d.resultados["equilibrios"]}
        self.assertEqual(tipos[(-sp.pi, 0)], "punto silla")
        self.assertEqual(tipos[(sp.pi, 0)], "punto silla")
        self.assertIn("centro", tipos[(0, 0)])
        self.assertValidado(d, "integral_primera_conservada", "identidad_angulo_mitad")

    def test_balotario_1_5_periodo_exacto_con_la_integral_eliptica(self):
        _, d = desarrollar(**self.BALOTARIO)
        k = math.sin(math.pi / 6)
        self.assertAlmostEqual(d.resultados["modulo_eliptico"], k, places=12)
        self.assertAlmostEqual(d.resultados["periodo"], 4 * float(ellipk(k * k)), places=10)
        self.assertIgual(d.resultados["periodo_pequenas_oscilaciones"], "2*pi/w0")
        self.assertValidado(d, "identidad_angulo_mitad_periodo", "periodo_por_retorno")

    def test_equivalente_con_otra_frecuencia_y_amplitud(self):
        """θ'' + 4 sen θ = 0 desde θ₀ = π/2: ω₀ = 2, T = 2K(sen π/4)."""
        _, d = desarrollar(ecuaciones=["v", "-4*sin(theta)"], variables_estado=["theta", "v"],
                           pedidos=["energia", "separatriz", "periodo"], y0=[math.pi / 2, 0], intervalo=[0, 10])
        self.assertIgual(d.resultados["separatriz"], "4*cos(theta/2)")
        self.assertIgual(d.resultados["energia_separatriz"], 4)
        k = math.sin(math.pi / 4)
        self.assertAlmostEqual(d.resultados["periodo"], 4 / 2 * float(ellipk(k * k)), places=10)
        self.assertIgual(d.resultados["periodo_pequenas_oscilaciones"], "pi")
        self.assertValidado(d, "integral_primera_conservada", "periodo_por_retorno")


class FlujoDelTema1Tests(unittest.TestCase):
    """El recorrido entero: desarrollo, integración, contraste analítico-numérico y figuras."""

    def test_la_trayectoria_numerica_coincide_con_la_solucion_del_desarrollo(self):
        for nombre, solicitud in (("separable", SeparableTests.BALOTARIO), ("riccati", RiccatiTests.BALOTARIO)):
            with self.subTest(familia=nombre):
                resultado = analizar_edo({**solicitud, "visualizar": False})
                self.assertTrue(resultado["ok"], resultado.get("error"))
                self.assertEqual(resultado["desarrollo"]["familia"], nombre)
                pruebas = {p["nombre"]: p for p in resultado["verificacion"]["pruebas"]}
                self.assertTrue(pruebas["solucion_exacta"]["ok"])
                self.assertLess(pruebas["solucion_exacta"]["error_relativo_maximo"], 1e-6)

    def test_se_integra_solo_hasta_antes_de_la_singularidad(self):
        """Pedir [0, 1.2] en el 1.1 no rompe nada: la solución deja de existir en √(2/3)."""
        resultado = analizar_edo({**SeparableTests.BALOTARIO, "intervalo": [0, 1.2], "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertLess(resultado["solucion"]["t"][-1], math.sqrt(2 / 3))
        self.assertTrue(any("singularidad" in n for n in resultado["notas"]))

    def test_cauchy_euler_sin_condicion_inicial_da_la_solucion_general(self):
        resultado = analizar_edo({**CauchyEulerTests.BALOTARIO, "visualizar": False,
                                  "enunciado": "Halle la solución general de x^2 y'' - 2x y' + 2y = x^3 ln x"})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["solucion"]["tipo"], "desarrollo")
        self.assertIn("solucion_general", resultado["solucion"]["resultados"])
        self.assertEqual(resultado["desarrollo"]["secciones"][0]["clave"], "clasificacion")

    def test_el_pendulo_conserva_su_integral_primera_en_la_trayectoria(self):
        resultado = analizar_edo({**PenduloTests.BALOTARIO, "visualizar": True})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        pruebas = {p["nombre"]: p for p in resultado["verificacion"]["pruebas"]}
        self.assertTrue(pruebas["integral_primera"]["ok"])
        self.assertEqual(resultado["visualizacion"]["figuras"][0], "retrato_fase")


if __name__ == "__main__":
    unittest.main()
