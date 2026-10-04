"""Pruebas de la capa MCP: registro de herramientas y limpieza de stdout.

El handshake stdio real se prueba aparte lanzando el proceso; aquí se cubre lo
que puede romperse en silencio:

* que las herramientas queden registradas con su esquema,
* que **nada** escape a stdout, porque en stdio ese canal es el protocolo
  JSON-RPC y un solo `print` de una dependencia rompe la conexión entera.
"""

import asyncio
import contextlib
import io
import json
import unittest

import mcp_server


def _ejecutar(corutina):
    return asyncio.run(corutina)


class RegistroDeHerramientasTests(unittest.TestCase):
    def test_las_herramientas_estan_registradas(self):
        herramientas = {h.name for h in _ejecutar(mcp_server.servidor.list_tools())}
        self.assertEqual(herramientas, {"ping", "analizar_edo", "analizar_equilibrios",
                                        "listar_balotario"})

    def test_analizar_equilibrios_no_exige_condicion_inicial(self):
        """Es la razón de que exista: preguntar por equilibrios sin inventar un PVI."""
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "analizar_equilibrios")
        requeridos = set(herramienta.input_schema["required"])
        self.assertEqual(requeridos, {"ecuaciones", "variables_estado"})
        self.assertNotIn("y0", requeridos)
        self.assertNotIn("intervalo", requeridos)

    def test_analizar_edo_declara_sus_parametros_obligatorios(self):
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "analizar_edo")
        esquema = herramienta.input_schema
        self.assertEqual(set(esquema["required"]),
                         {"ecuaciones", "variables_estado", "y0", "intervalo"})
        self.assertIn("parametros", esquema["properties"])
        self.assertIn("solucion_exacta", esquema["properties"])

    def test_las_herramientas_se_describen_para_el_cliente(self):
        for herramienta in _ejecutar(mcp_server.servidor.list_tools()):
            with self.subTest(herramienta=herramienta.name):
                self.assertTrue((herramienta.description or "").strip())

    def test_las_instrucciones_advierten_sobre_la_verificacion(self):
        instrucciones = mcp_server.servidor.instructions or ""
        self.assertIn("verificacion", instrucciones)
        self.assertIn("no entrega conclusiones", instrucciones)


class StdoutLimpioTests(unittest.TestCase):
    """stdout es el canal del protocolo: nada más puede escribir en él."""

    def test_el_decorador_atrapa_un_print_de_una_dependencia(self):
        @mcp_server.sin_contaminar_stdout
        def herramienta_sucia():
            print("esto rompería el protocolo JSON-RPC")
            return {"ok": True}

        real = io.StringIO()
        with contextlib.redirect_stdout(real):
            resultado = herramienta_sucia()
        self.assertEqual(resultado, {"ok": True})
        self.assertEqual(real.getvalue(), "")

    def test_ping_no_escribe_en_stdout(self):
        real = io.StringIO()
        with contextlib.redirect_stdout(real):
            resultado = mcp_server.ping()
        self.assertEqual(real.getvalue(), "")
        self.assertTrue(resultado["ok"])

    def test_analizar_edo_no_escribe_en_stdout(self):
        real = io.StringIO()
        with contextlib.redirect_stdout(real):
            resultado = mcp_server.analizar_edo(
                ecuaciones=["-2*y"], variables_estado=["y"], y0=[1.0],
                intervalo=[0.0, 2.0], visualizar=False)
        self.assertEqual(real.getvalue(), "")
        self.assertTrue(resultado["ok"], resultado.get("error"))


class HerramientasTests(unittest.TestCase):
    def test_ping_informa_las_capacidades(self):
        resultado = mcp_server.ping()
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["transporte"], "stdio")
        self.assertIn("estabilidad", resultado["capacidades"]["analisis"])

    def test_listar_balotario_devuelve_ecuaciones_listas_para_el_solver(self):
        resultado = mcp_server.listar_balotario(tema="tema_01")
        self.assertTrue(resultado["ok"])
        problemas = resultado["temas"][0]["problemas"]
        self.assertEqual([p["id"] for p in problemas],
                         ["1.1", "1.2", "1.3", "1.4", "1.5"])
        for problema in problemas:
            with self.subTest(problema=problema["id"]):
                self.assertIn("campo", problema["ecuacion"])
                self.assertNotIn("solucion_esperada", problema)

    def test_listar_balotario_puede_incluir_las_soluciones(self):
        resultado = mcp_server.listar_balotario(incluir_solucion=True)
        problema = resultado["temas"][0]["problemas"][0]
        self.assertIn("solucion_esperada", problema)

    def test_listar_balotario_rechaza_un_tema_inexistente(self):
        resultado = mcp_server.listar_balotario(tema="tema_99")
        self.assertFalse(resultado["ok"])
        self.assertIn("tema_01", resultado["disponibles"])

    def test_toda_respuesta_de_herramienta_es_json_estricto(self):
        for etiqueta, resultado in (
            ("ping", mcp_server.ping()),
            ("balotario", mcp_server.listar_balotario()),
            ("analizar", mcp_server.analizar_edo(
                ecuaciones=["r*y*(1 - y/K)"], variables_estado=["y"], y0=[1.0],
                intervalo=[0.0, 10.0], parametros={"r": 1.0, "K": 10.0})),
        ):
            with self.subTest(herramienta=etiqueta):
                json.dumps(resultado, allow_nan=False, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
