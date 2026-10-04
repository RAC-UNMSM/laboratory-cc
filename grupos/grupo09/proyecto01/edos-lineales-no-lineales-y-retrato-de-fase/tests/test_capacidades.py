"""Pruebas del flujo del agente: validar → resolver → verificar → analizar → visualizar.

El foco está en dos cosas que ninguna otra prueba cubre:

* que el resultado sea **serializable en JSON estricto**, porque viaja por el
  transporte MCP;
* que el **portón de verificación** se cierre, es decir que un resultado
  inválido nunca llegue acompañado de conclusiones.
"""

import json
import unittest
from unittest import mock

from orquestacion.capacidades import (analizar_edo, analizar_equilibrios_sistema,
                                      buscar_equilibrios, describir_capacidades,
                                      es_autonomo)
from matematica.expresiones import compilar_campo
from orquestacion import capacidades
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

    def test_solucion_exacta_que_depende_de_los_parametros(self):
        """La solución cerrada del logístico usa r y K: hay que pasárselos.

        Los casos del Tema 1 tienen soluciones exactas sin parámetros, así que
        este hueco no se veía hasta probar el logístico, cuya solución es
        K/(1 + (K/y0 - 1)e^{-rt}).
        """
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
        puntos = sorted(e["punto"][0] for e in equilibrios)
        self.assertEqual(puntos, [0.0, 10.0])
        clasificacion = {e["punto"][0]: e["clasificacion"] for e in equilibrios}
        self.assertEqual(clasificacion[0.0], "inestable")
        self.assertEqual(clasificacion[10.0], "estable")

    def test_lorenz_halla_sus_tres_equilibrios_y_pasa_la_verificacion(self):
        """Los equilibrios de Lorenz son el origen y (±sqrt(b(r-1)), ·, r-1)."""
        resultado = analizar_edo(_sin_visualizar(LORENZ))
        self.assertTrue(resultado["ok"], resultado.get("error"))
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
        self.assertFalse(resultado["analisis"]["estabilidad"]["disponible"])
        self.assertTrue(any("no es autónomo" in nota for nota in resultado["notas"]))

    def test_los_analisis_pendientes_se_reportan_como_tales(self):
        resultado = analizar_edo(_sin_visualizar(
            LOGISTICO, analisis=["caos", "bifurcaciones", "solucion_analitica"]))
        self.assertTrue(resultado["ok"])
        for nombre in ("caos", "bifurcaciones", "solucion_analitica"):
            with self.subTest(analisis=nombre):
                bloque = resultado["analisis"][nombre]
                self.assertFalse(bloque["implementado"])
                self.assertEqual(bloque["estado"], "pendiente_de_implementacion")
                self.assertIn("no está implementad", bloque["motivo"])
                self.assertTrue(bloque["capacidades_previstas"])


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
        self.assertEqual(analisis["caos"]["estado"], "pendiente_de_implementacion")

    def test_pedir_lyapunov_explica_que_esta_pendiente_en_un_solo_paso(self):
        bloque = self._analisis(["lyapunov"])["caos"]
        self.assertEqual(bloque["estado"], "pendiente_de_implementacion")
        self.assertIn("lyapunov", bloque["capacidades_previstas"])

    def test_pedir_resolucion_simbolica_no_devuelve_numeros_como_si_lo_fueran(self):
        bloque = self._analisis(["solucion_analitica"])["solucion_analitica"]
        self.assertFalse(bloque["implementado"])
        self.assertIn("no está implementada", bloque["motivo"])
        # El mensaje debe ofrecer la alternativa real, no solo negar.
        self.assertIn("solucion_exacta", bloque["motivo"])
        self.assertIn("dsolve", bloque["capacidades_previstas"])

    def test_un_analisis_de_verdad_desconocido_se_rechaza_con_el_inventario(self):
        resultado = analizar_edo(_sin_visualizar(
            LOGISTICO, analisis=["transformada_de_fourier"]))
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "validacion_solicitud")
        self.assertIn("Implementados: estabilidad", resultado["error"])
        self.assertIn("pendientes de implementación", resultado["error"])

    def test_un_mapa_declarado_como_tal_se_rechaza_con_la_diferencia_explicada(self):
        resultado = analizar_edo(dict(
            ecuaciones=["r*x*(1-x)"], variables_estado=["x"], y0=[0.5],
            intervalo=[0, 30], parametros={"r": 3.8}, visualizar=False,
            tipo_de_sistema="mapa_discreto"))
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "fuera_de_alcance")
        self.assertNotIn("analisis", resultado)
        self.assertIn("caótico", resultado["detalles"]["sugerencia"])

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

    def test_el_inventario_declara_el_limite_de_los_mapas_discretos(self):
        """El motor no itera mapas; eso tiene que estar dicho, no supuesto."""
        limites = describir_capacidades()["limites"]
        self.assertIn("sin_mapas_discretos", limites)
        self.assertIn("x_{n+1}", limites["sin_mapas_discretos"])
        self.assertIn("solo_primer_orden", limites)

    def test_el_inventario_separa_resolucion_numerica_de_analitica(self):
        resolucion = describir_capacidades()["resolucion"]
        self.assertTrue(resolucion["numerica"]["implementado"])
        self.assertFalse(resolucion["analitica"]["implementado"])
        self.assertEqual(resolucion["analitica"]["estado"],
                         "pendiente_de_implementacion")


class PortonVerificacionTests(unittest.TestCase):
    """Un resultado que no se verifica nunca viaja con conclusiones."""

    def _rechaza_en(self, etapa, solicitud):
        resultado = analizar_edo(solicitud)
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], etapa)
        self.assertNotIn("analisis", resultado)
        self.assertIn("No se emiten conclusiones", resultado["advertencia"])
        return resultado

    def test_solicitud_incoherente(self):
        self._rechaza_en("validacion_solicitud",
                         {"ecuaciones": ["y", "y"], "variables_estado": ["y"],
                          "y0": [1.0], "intervalo": [0.0, 1.0]})

    def test_dimension_por_encima_del_limite(self):
        self._rechaza_en("validacion_solicitud",
                         {"ecuaciones": ["a", "b", "c", "d"],
                          "variables_estado": ["a", "b", "c", "d"],
                          "y0": [0.0] * 4, "intervalo": [0.0, 1.0]})

    def test_expresion_hostil(self):
        self._rechaza_en("compilacion",
                         {"ecuaciones": ["__import__('os')"], "variables_estado": ["y"],
                          "y0": [1.0], "intervalo": [0.0, 1.0]})

    def test_singularidad_dentro_del_intervalo(self):
        resultado = self._rechaza_en("resolucion", {
            "ecuaciones": ["3*x*y**2"], "variables_estado": ["y"], "y0": [1.0],
            "intervalo": [0.0, 1.2], "variable_independiente": "x"})
        self.assertIn("singularidad", resultado["detalles"]["sugerencia"])

    def test_solucion_exacta_que_no_coincide(self):
        resultado = self._rechaza_en("verificacion",
                                     _sin_visualizar(LINEAL, solucion_exacta="exp(-3*t)"))
        self.assertIn("solucion_exacta", resultado["detalles"]["verificacion"]["fallidas"])


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
        """La respuesta lleva el enlace al informe, no el documento.

        El HTML de una herramienta no lo dibuja ningún cliente de chat, así que
        mandarlo inline gastaba el 75 % de la respuesta en algo que el modelo no
        puede usar. Lo que sí necesita para redactar es qué se dibujó; lo que el
        usuario necesita para verlo es el enlace.
        """
        visualizacion = analizar_edo({**LOGISTICO, "visualizar": True})["visualizacion"]
        self.assertIn("series", visualizacion["figuras"])
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
    def test_detecta_dependencia_de_la_variable_independiente(self):
        self.assertFalse(es_autonomo(compilar_campo(["3*x*y**2"], "x", ["y"])))
        self.assertTrue(es_autonomo(compilar_campo(["y**3 - y"], "x", ["y"])))

    def test_equilibrios_simbolicos_del_logistico(self):
        campo = compilar_campo(["r*y*(1 - y/K)"], "t", ["y"], ["r", "K"])
        equilibrios, origen = buscar_equilibrios(campo, {"r": 1.0, "K": 7.0})
        self.assertEqual(sorted(p[0] for p in equilibrios), [0.0, 7.0])
        self.assertEqual(origen["metodo"], "simbolico")

    def test_sin_equilibrios_reales_se_informa(self):
        """x' = 1 + x**2 no tiene equilibrios reales."""
        campo = compilar_campo(["1 + y**2"], "t", ["y"])
        equilibrios, origen = buscar_equilibrios(campo, {})
        self.assertEqual(equilibrios, [])
        self.assertEqual(origen["metodo"], "simbolico")

    def test_no_autonomo_no_tiene_equilibrios_definidos(self):
        campo = compilar_campo(["3*x*y**2"], "x", ["y"])
        equilibrios, origen = buscar_equilibrios(campo, {})
        self.assertEqual(equilibrios, [])
        self.assertIn("no es autónomo", origen["nota"])

    def test_describir_capacidades_es_honesto(self):
        capacidades = describir_capacidades()
        self.assertTrue(capacidades["analisis"]["estabilidad"]["implementado"])
        self.assertFalse(capacidades["analisis"]["caos"]["implementado"])
        self.assertFalse(capacidades["analisis"]["bifurcaciones"]["implementado"])
        self.assertEqual(capacidades["limites"]["dimension_maxima"], 3)


class EquilibriosSinTrayectoriaTests(unittest.TestCase):
    """analizar_equilibrios responde preguntas que no son un PVI.

    "Clasifique los equilibrios de x' = mu - x^2" no trae condicion inicial.
    Antes habia que inventarla para poder preguntar, y el servidor integraba una
    trayectoria que nadie habia pedido.
    """

    SILLA_NODO = {"ecuaciones": ["mu - x**2"], "variables_estado": ["x"]}

    def test_clasifica_sin_pedir_condicion_inicial(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        equilibrios = resultado["analisis"]["estabilidad"]["equilibrios"]
        self.assertEqual(sorted(e["punto"][0] for e in equilibrios), [-1.0, 1.0])
        clases = {e["punto"][0]: e["clasificacion"] for e in equilibrios}
        self.assertEqual(clases[-1.0], "inestable")
        self.assertEqual(clases[1.0], "estable")

    def test_verifica_que_los_puntos_anulen_el_campo(self):
        """La verificacion propia de esta pregunta es F(x*) = 0."""
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 4.0}})
        self.assertTrue(resultado["verificacion"]["ok"])
        self.assertEqual(len(resultado["verificacion"]["pruebas"]), 2)
        for prueba in resultado["verificacion"]["pruebas"]:
            self.assertLess(prueba["residuo"], prueba["umbral"])

    def test_rechaza_un_punto_que_no_es_equilibrio(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}, "equilibrios": [[0.5]]})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "verificacion")
        self.assertNotIn("analisis", resultado)

    def test_sin_equilibrios_reales_lo_dice(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": -1.0}})
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["solucion"]["cantidad"], 0)
        self.assertTrue(any("no tiene equilibrios" in n for n in resultado["notas"]))

    def test_un_sistema_no_autonomo_no_tiene_equilibrios_definidos(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["3*x*y**2"], "variables_estado": ["y"],
             "variable_independiente": "x"})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "no_aplica")
        self.assertIn("analizar_edo", resultado["detalles"]["sugerencia"])

    def test_hereda_el_porton_de_los_mapas_discretos(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "tipo_de_sistema": "mapa_discreto"})
        self.assertEqual(resultado["etapa"], "fuera_de_alcance")
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "tipo_de_sistema": "no_estoy_seguro"})
        self.assertEqual(resultado["etapa"], "aclaracion_necesaria")

    def test_una_bifurcacion_se_estudia_repitiendo_la_llamada(self):
        """Es lo que el agente recomienda mientras el barrido no exista."""
        conteos = []
        for mu in (-1.0, 0.0, 1.0):
            resultado = analizar_equilibrios_sistema(
                {**self.SILLA_NODO, "parametros": {"mu": mu}})
            self.assertTrue(resultado["ok"])
            conteos.append(resultado["solucion"]["cantidad"])
        self.assertEqual(conteos, [0, 1, 2])

    def test_la_nota_remite_al_barrido_pendiente(self):
        resultado = analizar_equilibrios_sistema(
            {**self.SILLA_NODO, "parametros": {"mu": 1.0}})
        self.assertTrue(any("pendiente" in n for n in resultado["notas"]))

    def test_rechaza_dimension_por_encima_del_limite(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["a", "b", "c", "d"],
             "variables_estado": ["a", "b", "c", "d"]})
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "validacion_solicitud")

    def test_el_resultado_es_json_estricto(self):
        resultado = analizar_equilibrios_sistema(
            {"ecuaciones": ["mu*x - y - x*(x**2+y**2)", "x + mu*y - y*(x**2+y**2)"],
             "variables_estado": ["x", "y"], "parametros": {"mu": 1.0}})
        self.assertTrue(resultado["ok"], resultado.get("error"))
        json.dumps(resultado, allow_nan=False, ensure_ascii=False)


class TestAvisosDeBusquedaDeEquilibrios(unittest.TestCase):
    """Las advertencias de `buscar_equilibrios` se suman; no se pisan.

    x' = x**4 - 1 tiene cuatro raíces: dos reales (±1) y dos imaginarias, que se
    descartan. Si además se recortan por exceder el máximo, el resultado tiene
    dos cosas que advertir a la vez. Antes la segunda sobrescribía a la primera
    y el cliente no se enteraba de los descartes.
    """

    def test_descartes_y_recorte_se_reportan_juntos(self):
        campo = compilar_campo(["x**4 - 1"], "t", ["x"])
        with mock.patch.object(capacidades, "MAXIMO_EQUILIBRIOS", 1):
            equilibrios, nota = capacidades.buscar_equilibrios(campo, {})
        self.assertEqual(len(equilibrios), 1)
        self.assertEqual(nota["descartados"], 2)
        self.assertIn("descartada", nota["nota"])
        self.assertIn("se reportan", nota["nota"])


if __name__ == "__main__":
    unittest.main()
