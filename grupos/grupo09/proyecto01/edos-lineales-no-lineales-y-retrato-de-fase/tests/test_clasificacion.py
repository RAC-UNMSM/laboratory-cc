"""Interpretación del enunciado, clasificación del problema y selección del método.

Es la parte "entiende el tipo → elige el procedimiento" del recorrido. Lo que
importa probar:

* que se lean del enunciado el método que nombra y lo que pide;
* que se registre con qué familias es compatible una ecuación, no solo cuál se
  eligió (3xy² es separable y de Bernoulli);
* que un método pedido se respete si la ecuación tiene esa forma, y se
  rechace diciendo por qué si no la tiene;
* que lo que no pertenece a los temas del proyecto quede marcado como fuera de alcance,
  y que cada problema de los Temas 4 y 5 llegue a su familia.
"""

import unittest

from matematica.clasificacion import (FAMILIAS, FUERA_DEL_PROYECTO, clasificar, clave_de_metodo,
                                      detectar_fuera_de_alcance, inventario, mensaje_de_alcance,
                                      parece_matematica)
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
                                ("numérico", "numerico"), ("variación de constantes", None),
                                # Un método que existe pero que el balotario no trabaja se reconoce, para decirlo.
                                ("transformada de Laplace", "no_trabajado:laplace")):
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
    def test_el_inventario_lista_familias_temas_y_lo_que_queda_fuera(self):
        datos = inventario()
        claves = {f["familia"] for f in datos["familias"]}
        self.assertEqual(claves, {f.clave for f in FAMILIAS})
        self.assertEqual([t["tema"] for t in datos["temas"]], ["Tema 1", "Tema 2", "Tema 3", "Tema 4", "Tema 5"])
        self.assertIn("ecuaciones en derivadas parciales", datos["fuera_del_proyecto"])
        self.assertIn("transformada de Laplace", datos["metodos_no_trabajados"])

    def test_cada_problema_del_balotario_tiene_su_familia(self):
        citados = {p for f in FAMILIAS for p in f.balotario}
        self.assertEqual(citados, {f"{tema}.{n}" for tema in range(1, 6) for n in range(1, 6)})

    def test_cada_tema_de_caos_y_fractales_llega_a_su_familia(self):
        """El tema que nombra el enunciado decide la familia, aunque el sistema tenga otra forma."""
        lorenz = dict(ecuaciones=["10*(y - x)", "28*x - y - x*z", "x*y - 8*z/3"], variables_estado=["x", "y", "z"])
        rossler = dict(ecuaciones=["-y - z", "x + 0.2*y", "0.2 + z*(x - 5.7)"], variables_estado=["x", "y", "z"])
        casos = (
            (dict(**lorenz, pedidos=["disipatividad"]), "disipatividad"),
            (dict(**lorenz, pedidos=["espectro_lyapunov"]), "espectro_lyapunov"),
            (dict(**lorenz, pedidos=["kaplan_yorke"]), "kaplan_yorke"),
            (dict(**rossler, pedidos=["seccion_poincare"]), "seccion_poincare"),
            (dict(ecuaciones=["1 - 1.4*x**2 + y", "0.3*x"], variables_estado=["x", "y"],
                  tipo_de_sistema="mapa_discreto"), "mapa_2d"),
            (dict(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametro="r",
                  tipo_de_sistema="mapa_discreto"), "duplicacion_periodo"),
            (dict(ecuaciones=["r*x*(1 - x)"], variables_estado=["x"], parametro="r", pedidos=["feigenbaum"],
                  tipo_de_sistema="mapa_discreto"), "feigenbaum"),
            (dict(ecuaciones=[], variables_estado=[], pedidos=["feigenbaum"]), "feigenbaum"),
            (dict(ecuaciones=[], variables_estado=[], pedidos=["dimension_fractal"]), "dimension_fractal"),
            (dict(ecuaciones=[], variables_estado=[], pedidos=["herradura"]), "herradura"),
            (dict(ecuaciones=[], variables_estado=[], pedidos=["espectro_lyapunov"]), "espectro_lyapunov"),
            (dict(ecuaciones=[], variables_estado=[], pedidos=["kaplan_yorke"],
                  datos={"exponentes": [0.9, 0, -14.6]}), "kaplan_yorke"),
        )
        for solicitud, esperada in casos:
            with self.subTest(esperada=esperada, pedidos=solicitud.get("pedidos")):
                self.assertEqual(clave(clasificacion(**solicitud)), esperada)

    def test_sin_el_tema_un_flujo_3d_sigue_siendo_numerico(self):
        lorenz = clasificacion(ecuaciones=["10*(y - x)", "28*x - y - x*z", "x*y - 8*z/3"],
                               variables_estado=["x", "y", "z"])
        self.assertEqual(clave(lorenz), "numerico")
        self.assertIsNone(lorenz.fuera_de_alcance)

    def test_lo_que_no_pertenece_a_los_temas(self):
        casos = (("Resuelva la ecuación del calor u_t = u_xx", "edp"),
                 ("Resuelva la ecuación en derivadas parciales de la onda", "edp"),
                 ("Simule la ecuación diferencial estocástica con ruido blanco", "estocastica"),
                 ("Resuelva la ecuación con retardo x'(t) = -x(t - 1)", "retardo"),
                 ("Calcule la serie de Fourier de la onda cuadrada", "fourier"))
        for enunciado, esperada in casos:
            with self.subTest(enunciado=enunciado):
                problema = construir_problema(ecuaciones=["-x"], variables_estado=["x"], enunciado=enunciado)
                self.assertEqual(detectar_fuera_de_alcance(problema)["clave"], esperada)
        mapa_3d = construir_problema(ecuaciones=["y", "z", "x"], variables_estado=["x", "y", "z"],
                                     tipo_de_sistema="mapa_discreto")
        self.assertEqual(detectar_fuera_de_alcance(mapa_3d)["clave"], "mapa_3d")

    def test_lo_que_parece_fuera_pero_no_lo_es(self):
        """'valor fraccionario' (5.5) no es cálculo fraccionario, ni 'Laplace' en 'transformada' una EDP."""
        for enunciado in ("Calcule D_L e interprete físicamente su valor fraccionario",
                          "Resuelva por transformada de Laplace y' = -2y",
                          "Considere el mapa tienda y su exponente de Lyapunov"):
            with self.subTest(enunciado=enunciado):
                problema = construir_problema(ecuaciones=["-x"], variables_estado=["x"], enunciado=enunciado)
                self.assertIsNone(detectar_fuera_de_alcance(problema))

    def test_el_mensaje_de_alcance_enumera_los_temas(self):
        mensaje = mensaje_de_alcance("ecuaciones en derivadas parciales")
        self.assertTrue(mensaje.startswith("Problema fuera del alcance de los temas trabajados"))
        for tema in ("Tema 1 —", "Tema 2 —", "Tema 3 —", "Tema 4 —", "Tema 5 —"):
            self.assertIn(tema, mensaje)
        self.assertIn("no es un problema matemático", mensaje_de_alcance(no_matematico=True))

    def test_distingue_una_pregunta_de_matematicas_de_una_ajena(self):
        for texto in ("Calcule la integral de x^2", "Resuelva y' = -2y", "¿Cuál es el exponente de Lyapunov?"):
            self.assertTrue(parece_matematica(texto), texto)
        for texto in ("¿Dónde queda el baño?", "Dame un color bonito", "Hola, ¿cómo estás?"):
            self.assertFalse(parece_matematica(texto), texto)

    def test_un_metodo_no_trabajado_se_dice_y_se_usa_el_del_balotario(self):
        self.assertEqual(clave_de_metodo("Transformada de Laplace"), "no_trabajado:laplace")
        c = clasificacion(ecuaciones=["-2*y"], variables_estado=["y"], metodo="laplace")
        self.assertIsNotNone(c.familia)
        self.assertEqual(c.metodo_rechazado, "transformada de Laplace")
        self.assertIn("no es uno de los métodos trabajados", c.motivo)

    def test_cada_patron_fuera_del_proyecto_tiene_descripcion(self):
        for clave_, (descripcion, patrones) in FUERA_DEL_PROYECTO.items():
            with self.subTest(clave=clave_):
                self.assertTrue(descripcion.strip())
                self.assertTrue(patrones)

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
