"""Tema 4 del balotario: sistemas dinámicos caóticos (4.1 a 4.5).

Cada problema se prueba con los datos del balotario y con otros equivalentes,
para que el procedimiento no esté hecho a la medida de un solo enunciado:

* 4.1, exponente de Lyapunov y horizonte de un mapa (tienda y parientes);
* 4.2, duplicación de periodo (logístico y un mapa cúbico);
* 4.3, Feigenbaum (con el mapa, con los datos y con datos imposibles);
* 4.4, disipatividad y elipsoide atrapante (Lorenz simbólico y numérico);
* 4.5, el teorema del espectro de Lyapunov y su comprobación numérica.

Y lo que ya no es "fuera de alcance por ahora" sino de verdad ajeno al proyecto.
"""

import math
import unittest

import numpy as np
import sympy as sp

from matematica import DatoInvalido
from matematica.clasificacion import clasificar
from matematica.problema import construir_problema
from orquestacion.capacidades import analizar_caos_y_fractales, analizar_edo

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


LOGISTICO = dict(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametro="r", rango_parametro=[0, 4],
                 region={"x": [0, 1]}, tipo_de_sistema="mapa_discreto")
LORENZ = dict(ecuaciones=["sigma*(y - x)", "r*x - y - x*z", "x*y - b*z"], variables_estado=["x", "y", "z"],
              parametros={"sigma": 10, "r": 28, "b": 8 / 3})


def sin_fallos(test, desarrollo):
    test.assertEqual([v.nombre for v in desarrollo.validaciones if not v.ok and v.concluyente], [])


class DuplicacionDePeriodoTests(unittest.TestCase):
    """4.2: puntos fijos, multiplicadores, órbita de periodo 2 por Vieta, r₁ y r₂."""

    def test_balotario_4_2_mapa_logistico(self):
        c, d = desarrollar(**LOGISTICO)
        self.assertEqual(d.familia, "duplicacion_periodo")
        r = sp.Symbol("r")
        resultados = {k: v.subs({s: sp.Symbol(s.name) for s in getattr(v, "free_symbols", ())})
                      if isinstance(v, sp.Basic) else v for k, v in d.resultados.items()}
        self.assertEqual(resultados["r_1"], 3)
        self.assertEqual(sp.simplify(resultados["r_2"] - (1 + sp.sqrt(6))), 0)
        self.assertEqual(sp.expand(resultados["multiplicador_periodo_2"] - (-r ** 2 + 2 * r + 4)), 0)
        self.assertEqual(sp.factor(resultados["discriminante"]), sp.factor(r ** 2 * (r - 3) * (r + 1)))
        self.assertEqual(d.resultados["intervalo_periodo_2"], sp.Interval.open(3, 1 + sp.sqrt(6)))
        self.assertEqual(d.resultados["intervalos_estabilidad"][1], sp.Interval.open(1, 3))
        sin_fallos(self, d)
        self.assertEqual({v.nombre for v in d.validaciones},
                         {"nace_del_punto_fijo", "factorizacion_f2", "orbita_periodo_2_iterada",
                          "periodo_4_tras_r2", "punto_fijo_antes_de_r1"})
        self.assertEqual([g["clave"] for g in d.graficas], ["diagrama_bifurcacion", "f_y_f2"])

    def test_mapa_cubico_sin_forma_cerrada_del_periodo_2(self):
        """x → r·x − x³: r₁ = 2 (3 − 2r = −1); f²(x) − x deja un factor de grado 6, sin fórmula."""
        _, d = desarrollar(ecuaciones=["r*x - x**3"], variables_estado=["x"], parametro="r",
                           rango_parametro=[0, 3], tipo_de_sistema="mapa_discreto")
        self.assertEqual(d.familia, "duplicacion_periodo")
        self.assertEqual(d.resultados["r_1"], 2)
        self.assertNotIn("r_2", d.resultados)
        sin_fallos(self, d)

    def test_con_valor_numerico_el_logistico_es_un_mapa_concreto(self):
        """Con r = 3.8 y sin preguntar por el periodo 2 es el 4.1: λ ≈ 0.43."""
        resultado = analizar_caos_y_fractales({"enunciado": "Calcule el exponente de Lyapunov del mapa "
                                                            "logístico con r = 3.8", "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "mapa_1d")
        self.assertAlmostEqual(resultado["desarrollo"]["resultados"]["lyapunov_valor"], 0.4318, delta=0.01)


class FeigenbaumTests(unittest.TestCase):
    """4.3: r_∞ ≈ r₂ + (r₂ − r₁)/(δ − 1), contrastado con los rₙ numéricos."""

    def test_con_los_datos_explicitos(self):
        resultado = analizar_caos_y_fractales({
            "enunciado": "Estime el umbral de acumulación con la constante de Feigenbaum.",
            "datos": {"r_1": 3, "r_2": 1 + math.sqrt(6), "delta": 4.6692016}, "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        resultados = resultado["desarrollo"]["resultados"]
        self.assertAlmostEqual(resultados["r_infinito"], 3.571993, places=5)
        self.assertEqual(sp.sympify(resultados["r_2"]["texto"]), 1 + sp.sqrt(6))
        self.assertEqual(resultado["verificacion"]["fallidas"], [])

    def test_con_el_mapa_los_umbrales_salen_exactos(self):
        _, d = desarrollar(**LOGISTICO, pedidos=["feigenbaum"])
        self.assertEqual(d.familia, "feigenbaum")
        self.assertEqual(d.resultados["r_1"], 3)
        self.assertAlmostEqual(d.resultados["umbrales_numericos"][3], 3.564407266, places=7)
        self.assertLess(abs(d.resultados["razones"][-1] - 4.6692), 0.01)
        sin_fallos(self, d)

    def test_datos_de_otro_mapa_se_usan_tal_cual(self):
        """r₁ = 2, r₂ = 2.5 no son del logístico: se estima, pero no hay contra qué comparar."""
        _, d = desarrollar(ecuaciones=[], variables_estado=[], pedidos=["feigenbaum"],
                           datos={"r_1": 2, "r_2": 2.5})
        self.assertAlmostEqual(d.resultados["r_infinito"], 2.5 + 0.5 / (4.669201609102990 - 1), places=9)
        self.assertNotIn("umbrales_numericos", d.resultados)

    def test_los_datos_imposibles_se_rechazan_diciendo_cual(self):
        for datos, frase in (({"r_1": 3.5, "r_2": 3.2}, "deben crecer"),
                             ({"r_1": 3, "r_2": 3.45, "delta": 0.8}, "mayor que 1")):
            with self.subTest(datos=datos):
                resultado = analizar_caos_y_fractales({"enunciado": "Estime r_infinito con Feigenbaum",
                                                       "datos": datos})
                self.assertFalse(resultado["ok"])
                self.assertEqual(resultado["etapa"], "datos")
                self.assertIn(frase, resultado["error"])
        with self.assertRaises(DatoInvalido):
            desarrollar(ecuaciones=[], variables_estado=[], pedidos=["feigenbaum"], datos={"r_1": 3, "r_2": 2})

    def test_datos_que_contradicen_el_mapa_se_advierten(self):
        _, d = desarrollar(**LOGISTICO, pedidos=["feigenbaum"], datos={"r_1": 3.1, "r_2": 3.5})
        self.assertEqual(d.resultados["r_1"], 3)
        self.assertTrue(any("no coinciden" in a for a in d.advertencias))


class DisipatividadTests(unittest.TestCase):
    """4.4: divergencia, Liouville y la función de Lyapunov del elipsoide atrapante."""

    def test_balotario_4_4_lorenz_simbolico(self):
        _, d = desarrollar(**LORENZ, pedidos=["disipatividad"])
        self.assertEqual(d.familia, "disipatividad")
        x, y, z, sigma, r, b = sp.symbols("x y z sigma r b")
        plano = {s: sp.Symbol(s.name) for k in ("divergencia", "funcion_lyapunov", "Q")
                 for s in d.resultados[k].free_symbols}
        self.assertEqual(sp.simplify(d.resultados["divergencia"].subs(plano) + sigma + 1 + b), 0)
        self.assertEqual(sp.simplify(d.resultados["funcion_lyapunov"].subs(plano)
                                     - (r * x ** 2 + sigma * y ** 2 + sigma * (z - 2 * r) ** 2)), 0)
        self.assertEqual(sp.simplify(d.resultados["Q"].subs(plano) - (r * x ** 2 + y ** 2 + b * (z - r) ** 2)), 0)
        self.assertAlmostEqual(d.resultados["V_estrella_valor"], 2 * (8 / 3) * 28 ** 2 / 0.1, places=6)
        sin_fallos(self, d)
        self.assertTrue({"liouville_numerico", "derivada_de_V", "cota_de_gronwall", "terminan_en_el_elipsoide"}
                        <= {v.nombre for v in d.validaciones})

    def test_lorenz_con_otros_parametros(self):
        _, d = desarrollar(**{**LORENZ, "parametros": {"sigma": 16, "r": 45.92, "b": 4}}, pedidos=["disipatividad"])
        self.assertAlmostEqual(d.resultados["contraccion_por_unidad_de_tiempo"], math.exp(-21), places=15)
        sin_fallos(self, d)

    def test_rossler_es_disipativo_en_promedio_y_sin_elipsoide_cuadratico(self):
        _, d = desarrollar(ecuaciones=["-y - z", "x + a*y", "b + z*(x - c)"], variables_estado=["x", "y", "z"],
                           parametros={"a": 0.2, "b": 0.2, "c": 5.7}, pedidos=["disipatividad"])
        self.assertTrue(d.resultados["disipativo"])
        self.assertLess(d.resultados["divergencia_media"], 0)
        self.assertNotIn("funcion_lyapunov", d.resultados)
        self.assertTrue(any("no se encontró una función de lyapunov" in a.lower() for a in d.advertencias))

    def test_un_flujo_que_conserva_volumen_no_es_disipativo(self):
        _, d = desarrollar(ecuaciones=["y", "-x"], variables_estado=["x", "y"], pedidos=["disipatividad"])
        self.assertFalse(d.resultados["disipativo"])
        self.assertTrue(any("no es disipativo" in c for c in d.conclusiones))
        sin_fallos(self, d)


class EspectroDeLyapunovTests(unittest.TestCase):
    """4.5: el teorema (+, 0, −) demostrado y comprobado con el método QR."""

    def test_con_el_sistema_de_lorenz_dado(self):
        resultado = analizar_edo({**LORENZ, "enunciado": "Calcule el espectro de exponentes de Lyapunov del "
                                                         "flujo y compruebe el teorema", "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "espectro_lyapunov")
        l1, l2, l3 = resultado["desarrollo"]["resultados"]["espectro"]["exponentes"]
        self.assertGreater(l1, 0.8)
        self.assertLess(abs(l2), 0.02)
        self.assertLess(l3, -l1)

    def test_un_ciclo_limite_no_es_caotico_pero_tiene_su_exponente_nulo(self):
        """Hopf en (x, y) y z contractivo: el espectro es (0, −1, −2), sin λ₁ > 0."""
        _, d = desarrollar(ecuaciones=["x - y - x*(x**2 + y**2)", "x + y - y*(x**2 + y**2)", "-z"],
                           variables_estado=["x", "y", "z"], pedidos=["espectro_lyapunov"])
        l1, l2, l3 = d.resultados["espectro"]["exponentes"]
        self.assertLess(abs(l1), 0.02)
        self.assertAlmostEqual(l2, -1, delta=0.05)
        self.assertAlmostEqual(l3, -2, delta=0.05)
        sin_fallos(self, d)
        self.assertTrue(any("no es caótica" in c for c in d.conclusiones))

    def test_un_flujo_que_cae_en_un_equilibrio_no_cumple_la_hipotesis(self):
        _, d = desarrollar(ecuaciones=["-x", "-2*y", "-3*z"], variables_estado=["x", "y", "z"],
                           pedidos=["espectro_lyapunov"])
        np.testing.assert_allclose(d.resultados["espectro"]["exponentes"], [-1, -2, -3], atol=0.02)
        sin_fallos(self, d)
        self.assertTrue(any("converge a un equilibrio" in c for c in d.conclusiones))


class FueraDelProyectoTests(unittest.TestCase):
    """Lo que no pertenece a ningún tema se dice, ordenado por temas; no se sustituye por otra cosa."""

    def assertFuera(self, resultado, etapa="fuera_de_alcance"):
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], etapa)
        for tema in ("Tema 1", "Tema 2", "Tema 3", "Tema 4", "Tema 5"):
            self.assertIn(tema, resultado["mensaje_para_el_usuario"])
        self.assertEqual(len(resultado["alcance"]), 5)

    def test_una_ecuacion_en_derivadas_parciales(self):
        resultado = analizar_edo(dict(ecuaciones=["-x"], variables_estado=["x"], visualizar=False,
                                      enunciado="Resuelva la ecuación del calor u_t = u_xx con u(0, t) = 0"))
        self.assertFuera(resultado)
        self.assertIn("derivadas parciales", resultado["mensaje_para_el_usuario"])

    def test_mas_de_tres_variables(self):
        resultado = analizar_edo(dict(ecuaciones=["y", "z", "w", "-x"], variables_estado=["x", "y", "z", "w"]))
        self.assertFuera(resultado)
        self.assertIn("4 variables", resultado["mensaje_para_el_usuario"])

    def test_un_mapa_de_tres_variables(self):
        resultado = analizar_edo(dict(ecuaciones=["y", "z", "x/2"], variables_estado=["x", "y", "z"],
                                      tipo_de_sistema="mapa_discreto", visualizar=False))
        self.assertFuera(resultado)

    def test_una_pregunta_que_no_es_de_matematicas(self):
        for texto in ("¿Dónde queda el baño?", "Recomiéndame un color para la sala"):
            with self.subTest(texto=texto):
                self.assertFuera(analizar_caos_y_fractales({"enunciado": texto}), "no_es_un_problema_del_proyecto")

    def test_una_pregunta_de_matematicas_de_otro_tema(self):
        self.assertFuera(analizar_caos_y_fractales({"enunciado": "Calcule la integral de x^2 entre 0 y 1"}))

    def test_un_enunciado_vacio_se_rechaza_en_la_frontera(self):
        resultado = analizar_caos_y_fractales({"enunciado": ""})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "validacion_solicitud")


if __name__ == "__main__":
    unittest.main()
