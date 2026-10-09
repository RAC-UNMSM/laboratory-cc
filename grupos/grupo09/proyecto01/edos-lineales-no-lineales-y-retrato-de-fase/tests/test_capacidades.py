"""Pruebas del recorrido del agente: interpretar → clasificar → desarrollar → calcular → verificar → dibujar.

El foco está en lo que ninguna prueba de familia cubre:

* que el resultado sea **serializable en JSON estricto**, porque viaja por el
  transporte MCP;
* que el **portón de verificación** se cierre: un resultado inválido nunca
  llega acompañado de conclusiones;
* que lo que no se puede hacer se diga (fuera de alcance, aclaración
  necesaria) en vez de sustituirlo en silencio por otra cosa.
"""

import json
import unittest
from unittest import mock

import sympy as sp

from matematica import analisis_estabilidad
from matematica.analisis_estabilidad import buscar_equilibrios, es_autonomo
from matematica.expresiones import compilar_campo
from orquestacion import capacidades
from orquestacion.capacidades import analizar_edo, analizar_equilibrios_sistema, describir_capacidades
from visualizacion.html import generar_html

LINEAL = {"ecuaciones": ["-2*y"], "variables_estado": ["y"], "y0": [1.0],
          "intervalo": [0.0, 5.0]}
LOGISTICO = {"ecuaciones": ["r*y*(1 - y/K)"], "variables_estado": ["y"], "y0": [1.0],
             "intervalo": [0.0, 10.0], "parametros": {"r": 1.0, "K": 10.0}}
LORENZ = {"ecuaciones": ["sigma*(y1 - x1)", "x1*(rho - z1) - y1", "x1*y1 - beta*z1"],
          "variables_estado": ["x1", "y1", "z1"], "y0": [1.0, 1.0, 1.0],
          "intervalo": [0.0, 40.0], "puntos": 2000,
          "parametros": {"sigma": 10.0, "rho": 28.0, "beta": 8 / 3}}


def _sin_visualizar(base, **extra):
    return {**base, "visualizar": False, **extra}


class FlujoCompletoTests(unittest.TestCase):
    def test_lineal_con_solucion_exacta(self):
        resultado = analizar_edo(_sin_visualizar(LINEAL, solucion_exacta="exp(-2*t)"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertTrue(resultado["verificacion"]["ok"])
        self.assertAlmostEqual(resultado["solucion"]["estado_final"]["y"],
                               4.5399929762e-05, places=8)

    def test_la_respuesta_trae_el_desarrollo_y_como_presentarlo(self):
        resultado = analizar_edo(_sin_visualizar(LINEAL))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        desarrollo = resultado["desarrollo"]
        self.assertEqual(desarrollo["familia"], "lineal")
        self.assertEqual(desarrollo["secciones"][0]["clave"], "clasificacion")
        for seccion in desarrollo["secciones"]:
            self.assertTrue(seccion["titulo"].strip())
            self.assertTrue(seccion["bloques"])
        self.assertIn("desarrollo.secciones", resultado["presentacion"])
        self.assertEqual(resultado["clasificacion"]["familia"], "lineal")

    def test_solucion_exacta_que_depende_de_los_parametros(self):
        """La solución cerrada del logístico usa r y K: hay que pasárselos."""
        resultado = analizar_edo(_sin_visualizar(
            LOGISTICO, solucion_exacta="K/(1 + (K/1 - 1)*exp(-r*t))"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        prueba = next(p for p in resultado["verificacion"]["pruebas"]
                      if p["nombre"] == "solucion_exacta")
        self.assertTrue(prueba["ok"])
        self.assertLess(prueba["error_maximo"], 1e-6)

    def test_logistico_halla_equilibrios_exactos(self):
        resultado = analizar_edo(_sin_visualizar(LOGISTICO))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        equilibrios = resultado["analisis"]["estabilidad"]["equilibrios"]
        clasificacion = {e["punto"][0]: e["clasificacion"] for e in equilibrios}
        self.assertEqual(clasificacion, {0.0: "inestable", 10.0: "estable"})

    def test_lorenz_halla_sus_tres_equilibrios_y_pasa_la_verificacion(self):
        """Los equilibrios de Lorenz son el origen y (±sqrt(b(r-1)), ·, r-1)."""
        resultado = analizar_edo(_sin_visualizar(LORENZ))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "numerico")
        equilibrios = resultado["analisis"]["estabilidad"]["equilibrios"]
        self.assertEqual(len(equilibrios), 3)
        for equilibrio in equilibrios:
            self.assertEqual(equilibrio["clasificacion"], "inestable")
        alturas = sorted(round(e["punto"][2], 9) for e in equilibrios)
        self.assertEqual(alturas, [0.0, 27.0, 27.0])

    def test_lorenz_reporta_sensibilidad_en_vez_de_fallar(self):
        """Dos integraciones correctas de un sistema caótico se separan: es un hallazgo."""
        resultado = analizar_edo(_sin_visualizar(LORENZ))
        self.assertTrue(resultado["ok"])
        pruebas = {p["nombre"]: p for p in resultado["verificacion"]["pruebas"]}
        self.assertTrue(pruebas["convergencia"]["sensibilidad_detectada"])
        self.assertTrue(pruebas["convergencia"]["estadisticas_coinciden"])
        self.assertTrue(any("sensibilidad" in nota for nota in resultado["notas"]))

    def test_sistema_no_autonomo_no_reporta_equilibrios(self):
        resultado = analizar_edo(_sin_visualizar({
            "ecuaciones": ["3*x*y**2"], "variables_estado": ["y"], "y0": [1.0],
            "intervalo": [0.0, 0.7], "variable_independiente": "x",
            "solucion_exacta": "2/(2 - 3*x**2)"}))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        bloque = resultado["analisis"]["estabilidad"]
        self.assertFalse(bloque["disponible"])
        self.assertIn("no es autónomo", bloque["nota"])

    def test_los_analisis_adicionales_dicen_que_hay_y_que_no(self):
        resultado = analizar_edo(_sin_visualizar(
            LOGISTICO, analisis=["caos", "bifurcaciones", "solucion_analitica"]))
        self.assertTrue(resultado["ok"])
        analisis = resultado["analisis"]
        self.assertTrue(analisis["solucion_analitica"]["disponible"])
        # Una EDO escalar no tiene espectro de Lyapunov que calcular: se dice para qué sí lo hay.
        self.assertFalse(analisis["caos"]["disponible"])
        self.assertIn("flujos autónomos de 2 o 3", analisis["caos"]["nota"])
        self.assertFalse(analisis["bifurcaciones"]["disponible"])
        self.assertIn("parametro", analisis["bifurcaciones"]["nota"])

    def test_sin_condicion_inicial_no_se_integra_nada(self):
        resultado = analizar_edo({"ecuaciones": ["-y/x + x**2"], "variables_estado": ["y"],
                                  "variable_independiente": "x", "visualizar": False})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["solucion"]["tipo"], "desarrollo")
        self.assertIn("solucion_general", resultado["solucion"]["resultados"])
        nombres = {p["nombre"] for p in resultado["verificacion"]["pruebas"]}
        self.assertNotIn("residuo", nombres)
        self.assertIn("solucion_general_satisface_la_edo", nombres)


class DegradacionHonestaTests(unittest.TestCase):
    """Pedir algo que no existe debe dar un 'todavía no', no un sustituto callado."""

    def _analisis(self, pedido):
        resultado = analizar_edo(_sin_visualizar(LOGISTICO, analisis=pedido))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        return resultado["analisis"]

    def test_alias_naturales_llegan_a_la_capacidad_correcta(self):
        """Pedir 'lyapunov' no debe dar 'nombre desconocido, pruebe caos'."""
        for alias, destino in (("lyapunov", "caos"), ("poincare", "caos"),
                               ("sensibilidad", "caos"), ("hopf", "bifurcaciones"),
                               ("barrido", "bifurcaciones"),
                               ("simbolica", "solucion_analitica"),
                               ("analitica", "solucion_analitica"),
                               ("equilibrios", "estabilidad"),
                               ("autovalores", "estabilidad")):
            with self.subTest(alias=alias):
                self.assertIn(destino, self._analisis([alias]))

    def test_los_alias_toleran_mayusculas_guiones_y_espacios(self):
        analisis = self._analisis(["Estabilidad", "exponente-de-lyapunov"])
        self.assertTrue(analisis["estabilidad"]["disponible"])
        self.assertIn("caos", analisis)

    def test_un_analisis_de_verdad_desconocido_se_rechaza_con_el_inventario(self):
        resultado = analizar_edo(_sin_visualizar(
            LOGISTICO, analisis=["transformada_de_fourier"]))
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "validacion_solicitud")
        self.assertIn("Disponibles: estabilidad", resultado["error"])

    def test_un_mapa_declarado_como_tal_se_itera_como_mapa(self):
        """El logístico con r = 3.8 es caótico como mapa: λ > 0 (procedimiento del 4.1)."""
        resultado = analizar_edo(dict(
            ecuaciones=["r*x*(1-x)"], variables_estado=["x"], y0=[0.5],
            intervalo=[0, 30], parametros={"r": 3.8}, visualizar=False,
            tipo_de_sistema="mapa_discreto"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "mapa_1d")
        lyapunov = resultado["solucion"]["resultados"]["lyapunov"]
        self.assertGreater(lyapunov["valor"], 0.3)
        self.assertIn("latex", lyapunov)

    def test_la_duda_declarada_devuelve_la_pregunta_no_un_numero(self):
        """'no_estoy_seguro' es una respuesta válida: el agente pregunta."""
        resultado = analizar_edo(dict(
            ecuaciones=["r*x*(1-x)"], variables_estado=["x"], y0=[0.5],
            intervalo=[0, 30], parametros={"r": 3.8}, visualizar=False,
            tipo_de_sistema="no_estoy_seguro"))
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "aclaracion_necesaria")
        self.assertIn("pregunta_para_el_usuario", resultado)
        self.assertEqual(len(resultado["opciones"]), 2)
        self.assertNotIn("solucion", resultado)
        for opcion in resultado["opciones"]:
            self.assertTrue(opcion["accion"].strip())
            self.assertTrue(opcion["consecuencia"].strip())

    def test_la_notacion_de_sucesion_dispara_la_pregunta(self):
        """Nadie escribe dx/dn: si la notación delata un mapa, se pregunta."""
        for estado, independiente in ((["x"], "n"), (["x_n"], "t"), (["theta_k"], "t")):
            with self.subTest(estado=estado, independiente=independiente):
                resultado = analizar_edo(dict(
                    ecuaciones=["0.5*" + estado[0]], variables_estado=estado,
                    y0=[0.5], intervalo=[0, 10], visualizar=False,
                    variable_independiente=independiente))
                self.assertEqual(resultado["etapa"], "aclaracion_necesaria")
                self.assertTrue(resultado["motivos"])

    def test_la_heuristica_no_estorba_a_sistemas_continuos_legitimos(self):
        """x1, x2 y x, y son nombres normales de componentes: no deben disparar nada."""
        for estado in (["x1", "x2"], ["x", "y"], ["theta", "v"]):
            with self.subTest(estado=estado):
                resultado = analizar_edo(dict(
                    ecuaciones=["-" + estado[0], "-" + estado[1]],
                    variables_estado=estado, y0=[1.0, 1.0], intervalo=[0, 2],
                    visualizar=False))
                self.assertTrue(resultado["ok"], resultado.get("error"))

    def test_un_tipo_de_sistema_invalido_se_rechaza(self):
        resultado = analizar_edo(_sin_visualizar(LINEAL, tipo_de_sistema="cuantico"))
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "validacion_solicitud")
        self.assertIn("tipo_de_sistema", resultado["error"])

    def test_el_inventario_declara_los_limites(self):
        limites = describir_capacidades()["limites"]
        self.assertIn("x_{n+1}", limites["mapas_discretos"])
        self.assertIn("solo_primer_orden", limites)
        self.assertEqual(limites["dimension_maxima"], 3)

    def test_el_inventario_separa_lo_implementado_de_lo_fuera_del_proyecto(self):
        capacidades_ = describir_capacidades()
        self.assertTrue(capacidades_["resolucion"]["analitica"]["implementado"])
        self.assertTrue(capacidades_["resolucion"]["numerica"]["implementado"])
        self.assertTrue(capacidades_["analisis"]["bifurcaciones"]["implementado"])
        self.assertIs(capacidades_["analisis"]["caos"]["implementado"], True)
        self.assertIs(capacidades_["analisis"]["atractores_y_fractales"]["implementado"], True)
        self.assertEqual(len(capacidades_["alcance"]), 5)
        self.assertIn("ecuaciones en derivadas parciales", capacidades_["fuera_del_proyecto"])
        self.assertNotIn("fuera_de_alcance", capacidades_)

    def test_el_caos_de_un_flujo_se_calcula(self):
        """Antes era 'fuera de alcance por ahora'; ahora el espectro de un flujo 3D se calcula."""
        resultado = analizar_edo(_sin_visualizar(LORENZ, analisis=["lyapunov"]))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        bloque = resultado["analisis"]["caos"]
        self.assertTrue(bloque["disponible"])
        self.assertTrue(bloque["caotico"])
        l1, l2, l3 = bloque["exponentes"]
        self.assertGreater(l1, 0.8)
        self.assertLess(abs(l2), 0.03)
        self.assertAlmostEqual(bloque["suma"], -41 / 3, delta=0.01)


class PortonVerificacionTests(unittest.TestCase):
    """Un resultado que no se verifica nunca viaja con conclusiones."""

    def _rechaza_en(self, etapa, solicitud, herramienta=analizar_edo):
        resultado = herramienta(solicitud)
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], etapa)
        self.assertNotIn("analisis", resultado)
        self.assertNotIn("desarrollo", resultado)
        self.assertIn("No se emiten conclusiones", resultado["advertencia"])
        return resultado

    def test_solicitud_incoherente(self):
        self._rechaza_en("validacion_solicitud",
                         {"ecuaciones": ["y", "y"], "variables_estado": ["y"],
                          "y0": [1.0], "intervalo": [0.0, 1.0]})

    def test_condicion_inicial_sin_intervalo(self):
        resultado = self._rechaza_en("validacion_solicitud",
                                     {"ecuaciones": ["-y"], "variables_estado": ["y"], "y0": [1.0]})
        self.assertIn("intervalo", resultado["error"])

    def test_dimension_por_encima_del_limite(self):
        """Cuatro variables no es un error de la solicitud: es algo que el proyecto no abarca, y se dice."""
        resultado = analizar_edo({"ecuaciones": ["a", "b", "c", "d"], "variables_estado": ["a", "b", "c", "d"],
                                  "y0": [0.0] * 4, "intervalo": [0.0, 1.0]})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "fuera_de_alcance")
        self.assertNotIn("desarrollo", resultado)
        self.assertIn("hasta 3", resultado["mensaje_para_el_usuario"])

    def test_expresion_hostil(self):
        self._rechaza_en("compilacion",
                         {"ecuaciones": ["__import__('os')"], "variables_estado": ["y"],
                          "y0": [1.0], "intervalo": [0.0, 1.0]})

    def test_explosion_sin_solucion_analitica_que_la_anticipe(self):
        """y' = x² + y² no tiene familia analítica: el integrador choca con la explosión."""
        resultado = self._rechaza_en("resolucion", {
            "ecuaciones": ["x**2 + y**2"], "variables_estado": ["y"], "y0": [1.0],
            "intervalo": [0.0, 2.0], "variable_independiente": "x", "visualizar": False})
        self.assertIn("singularidad", resultado["detalles"]["sugerencia"])

    def test_solucion_exacta_que_no_coincide(self):
        resultado = self._rechaza_en("verificacion",
                                     _sin_visualizar(LINEAL, solucion_exacta="exp(-3*t)"))
        self.assertIn("solucion_exacta", resultado["detalles"]["verificacion"]["fallidas"])

    def test_el_veredicto_del_porton_numerico_no_se_pierde(self):
        """Aunque las pruebas agregadas después pasen, un 'no' de `verificar` cierra el portón."""
        with mock.patch("orquestacion.capacidades.verificar",
                        return_value={"ok": False, "pruebas": [], "fallidas": ["residuo"],
                                      "resumen": "No se superaron: residuo."}):
            resultado = self._rechaza_en("verificacion", _sin_visualizar(LINEAL))
        self.assertIn("residuo", resultado["detalles"]["verificacion"]["fallidas"])

    def test_un_punto_que_no_es_equilibrio_se_rechaza(self):
        self._rechaza_en("verificacion",
                         {"ecuaciones": ["mu - x**2"], "variables_estado": ["x"],
                          "parametros": {"mu": 1.0}, "equilibrios": [[0.5]]},
                         herramienta=analizar_equilibrios_sistema)


class SerializacionTests(unittest.TestCase):
    """Todo lo que devuelve el agente tiene que pasar por JSON estricto."""

    def test_resultado_completo_es_json_estricto(self):
        for etiqueta, solicitud in (("lineal", LINEAL), ("logistico", LOGISTICO),
                                    ("lorenz", LORENZ)):
            with self.subTest(caso=etiqueta):
                resultado = analizar_edo({**solicitud, "visualizar": True})
                texto = json.dumps(resultado, allow_nan=False, ensure_ascii=False)
                self.assertGreater(len(texto), 100)

    def test_resultado_de_error_es_json_estricto(self):
        resultado = analizar_edo({"ecuaciones": ["y^2"], "variables_estado": ["y"],
                                  "y0": [1.0], "intervalo": [0.0, 1.0]})
        json.dumps(resultado, allow_nan=False)
        self.assertFalse(resultado["ok"])

    def test_visualizacion_dice_que_dibujo_y_donde_verlo(self):
        """La respuesta lleva el enlace al informe, no el documento."""
        visualizacion = analizar_edo({**LOGISTICO, "visualizar": True})["visualizacion"]
        self.assertEqual(visualizacion["figuras"][0], "solucion")
        self.assertIn("linea_fase", visualizacion["figuras"])
        self.assertIn("informe", visualizacion)
        self.assertNotIn("html", visualizacion)

    def test_el_documento_sigue_generandose_entero(self):
        """Que no viaje en la respuesta no significa que no exista."""
        documento = generar_html(
            compilar_campo(["-y"], "t", ["y"]), [0.0, 0.5, 1.0],
            [[1.0, 0.6, 0.37]], {}, ["y"])["html"]
        self.assertTrue(documento.startswith("<!doctype html>"))
        self.assertIn("plotly", documento)


class EquilibriosYAutonomiaTests(unittest.TestCase):
    """La búsqueda exacta de equilibrios de `matematica.analisis_estabilidad`."""

    y, x = sp.symbols("y x", real=True)

    def test_detecta_dependencia_de_la_variable_independiente(self):
        self.assertFalse(es_autonomo([3 * self.x * self.y ** 2], self.x))
        self.assertTrue(es_autonomo([self.y ** 3 - self.y], self.x))

    def test_equilibrios_simbolicos_del_logistico(self):
        equilibrios, informe = buscar_equilibrios([self.y * (1 - self.y / 7)], [self.y])
        self.assertEqual([e.punto for e in equilibrios], [(0,), (7,)])
        self.assertEqual(informe["metodo"], "simbolico")

    def test_sin_equilibrios_reales_se_informa(self):
        equilibrios, informe = buscar_equilibrios([1 + self.y ** 2], [self.y])
        self.assertEqual(equilibrios, [])
        self.assertEqual(informe["encontrados"], 0)

    def test_infinitos_equilibrios_se_dan_en_una_ventana(self):
        equilibrios, informe = buscar_equilibrios([sp.sin(self.y)], [self.y])
        self.assertIn("general", informe)
        self.assertEqual([e.punto[0] for e in equilibrios], [k * sp.pi for k in range(-2, 3)])


class TestAvisosDeBusquedaDeEquilibrios(unittest.TestCase):
    """Las advertencias de `buscar_equilibrios` se suman; no se pisan.

    ẋ = y, ẏ = x² + 1 solo tiene soluciones complejas (x = ±i): se descartan y
    hay que decirlo. Si además se recorta por exceder el máximo, el resultado
    tiene dos cosas que advertir a la vez. (Con los símbolos reales que usa el
    agente sympy ya no devuelve las complejas; con símbolos sin supuestos sí, y
    es la ruta que se prueba aquí.)
    """

    x, y = sp.symbols("x y")

    def test_las_soluciones_complejas_se_descartan_y_se_dice(self):
        equilibrios, informe = buscar_equilibrios([self.y, self.x ** 2 + 1], [self.x, self.y])
        self.assertEqual(equilibrios, [])
        self.assertEqual(informe["descartados"], 2)
        self.assertIn("descartada", informe["nota"])

    def test_descartes_y_recorte_se_reportan_juntos(self):
        campo = [self.y, (self.x ** 2 + 1) * (self.x ** 2 - 1)]
        with mock.patch.object(analisis_estabilidad, "MAXIMO_EQUILIBRIOS", 1):
            equilibrios, informe = buscar_equilibrios(campo, [self.x, self.y])
        self.assertEqual(len(equilibrios), 1)
        self.assertEqual(informe["descartados"], 2)
        self.assertEqual(informe["recortados"], 1)
        self.assertIn("descartada", informe["nota"])
        self.assertIn("se reportan", informe["nota"])


class EquilibriosSinTrayectoriaTests(unittest.TestCase):
    """analizar_equilibrios responde preguntas que no son un PVI.

    "Clasifique los equilibrios de x' = mu - x^2" no trae condición inicial: no
    hay que inventarla ni integrar una trayectoria que nadie pidió.
    """

    SILLA_NODO = {"ecuaciones": ["mu - x**2"], "variables_estado": ["x"]}

    def test_clasifica_sin_pedir_condicion_inicial(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        equilibrios = resultado["analisis"]["estabilidad"]["equilibrios"]
        clases = {e["punto"][0]: e["clasificacion"] for e in equilibrios}
        self.assertEqual(clases, {-1.0: "inestable", 1.0: "estable"})
        self.assertEqual(resultado["desarrollo"]["familia"], "equilibrios_1d")

    def test_verifica_que_los_puntos_anulen_el_campo(self):
        """La verificación propia de esta pregunta es F(x*) = 0."""
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 4.0}})
        self.assertTrue(resultado["verificacion"]["ok"])
        anulan = [p for p in resultado["verificacion"]["pruebas"] if p["nombre"].startswith("F(x*)=0")]
        self.assertEqual(len(anulan), 2)
        for prueba in anulan:
            self.assertLess(prueba["residuo"], prueba["umbral"])

    def test_sin_equilibrios_reales_lo_dice(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": -1.0}})
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["solucion"]["cantidad"], 0)
        self.assertTrue(any("No hay equilibrios" in c for c in resultado["desarrollo"]["conclusiones"]))

    def test_un_sistema_no_autonomo_no_tiene_equilibrios_definidos(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["3*x*y**2"], "variables_estado": ["y"],
             "variable_independiente": "x"})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "no_aplica")
        self.assertIn("analizar_edo", resultado["detalles"]["sugerencia"])

    def test_un_mapa_da_sus_puntos_fijos_y_la_duda_se_pregunta(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}, "tipo_de_sistema": "mapa_discreto"})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "mapa_1d")
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}, "tipo_de_sistema": "no_estoy_seguro"})
        self.assertEqual(resultado["etapa"], "aclaracion_necesaria")

    def test_repetir_la_llamada_sigue_dando_cada_valor(self):
        conteos = []
        for mu in (-1.0, 0.0, 1.0):
            resultado = analizar_equilibrios_sistema(
                {**self.SILLA_NODO, "parametros": {"mu": mu}})
            self.assertTrue(resultado["ok"])
            conteos.append(resultado["solucion"]["cantidad"])
        self.assertEqual(conteos, [0, 1, 2])

    def test_con_el_parametro_declarado_basta_una_llamada(self):
        resultado = analizar_equilibrios_sistema({**self.SILLA_NODO, "parametro": "mu"})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "bifurcacion_1d")
        self.assertTrue(any("silla-nodo" in c for c in resultado["desarrollo"]["conclusiones"]))

    def test_rechaza_dimension_por_encima_del_limite(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["a", "b", "c", "d"],
             "variables_estado": ["a", "b", "c", "d"]})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "fuera_de_alcance")

    def test_el_resultado_es_json_estricto(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["mu*x - y - x*(x**2+y**2)", "x + mu*y - y*(x**2+y**2)"],
             "variables_estado": ["x", "y"], "parametros": {"mu": 1.0}})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        json.dumps(resultado, allow_nan=False, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
