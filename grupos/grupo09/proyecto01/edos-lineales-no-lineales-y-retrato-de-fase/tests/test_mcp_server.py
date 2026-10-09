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
import math
import unittest
from pathlib import Path

import mcp_server


def _ejecutar(corutina):
    return asyncio.run(corutina)


class RegistroDeHerramientasTests(unittest.TestCase):
    def test_las_herramientas_estan_registradas(self):
        herramientas = {h.name for h in _ejecutar(mcp_server.servidor.list_tools())}
        self.assertEqual(herramientas, {"ping", "informe", "nuevo_informe",
                                        "resolver_graficar_y_analizar_edo",
                                        "analizar_equilibrios", "listar_balotario",
                                        "resolver_caos_fractales_y_atractores"})

    def test_el_nombre_de_la_herramienta_de_caos_dice_sus_temas(self):
        """Mismo motivo que el de la herramienta principal: el modelo elige por el nombre."""
        nombres = {h.name for h in _ejecutar(mcp_server.servidor.list_tools())}
        caos = next(n for n in nombres if "caos" in n)
        for palabra in ("resolver", "caos", "fractales", "atractores"):
            self.assertIn(palabra, caos)

    def test_la_herramienta_de_caos_solo_exige_el_enunciado(self):
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "resolver_caos_fractales_y_atractores")
        self.assertEqual(set(herramienta.input_schema["required"]), {"enunciado"})
        for campo in ("datos", "seccion_poincare", "ecuaciones", "parametros", "parametro"):
            self.assertIn(campo, herramienta.input_schema["properties"])

    def test_el_nombre_dice_lo_que_piden_los_enunciados(self):
        """El nombre es lo único que el modelo ve al decidir; no lo acorte.

        Observado en Claude Desktop: las herramientas del conector llegan
        diferidas (`ToolSearch`), así que al elegir el modelo solo ve
        `..._edos__<nombre>`, sin la descripción. Con `analizar_edo`, los
        prompts "Analiza el sistema..." usaban el agente, pero los enunciados
        "Resuelve... Grafica... Haz una gráfica 3D" se resolvían con Python.
        """
        nombres = {h.name for h in _ejecutar(mcp_server.servidor.list_tools())}
        principal = next(n for n in nombres if n.endswith("_edo"))
        for verbo in ("resolver", "graficar", "analizar"):
            self.assertIn(verbo, principal)

    def test_las_instrucciones_prohiben_rehacer_el_calculo(self):
        """Sin esto el agente reintegra por su cuenta y enseña números sin verificar.

        Observado en una sesión real: el modelo llamó a `analizar_edo`, ignoró el
        resultado y corrió su propio `solve_ivp` con matplotlib para armar un PNG.
        Esa trayectoria no pasó por las cinco verificaciones, así que la figura
        que vio el usuario no tenía detrás la garantía del agente.
        """
        texto = mcp_server.servidor.instructions
        self.assertIn("NO REHAGA EL CÁLCULO", texto)
        for palabra in ("scipy", "matplotlib", "informe"):
            self.assertIn(palabra, texto)

    def test_las_instrucciones_piden_abrir_informe_nuevo_en_cada_chat(self):
        """Sin esto el informe nunca empieza de cero.

        El cliente MCP levanta este servidor una vez y lo mantiene vivo para
        todas las conversaciones, así que la sesión del servidor NO coincide con
        la conversación: hay que decírselo.
        """
        texto = mcp_server.servidor.instructions
        self.assertIn("nuevo_informe", texto)
        self.assertIn("sigue vivo entre conversaciones", texto)
        # Y que el modo por defecto quede dicho: una pregunta, un documento.
        self.assertIn("LA ÚLTIMA PREGUNTA", texto)

    def test_ping_dice_que_build_esta_corriendo(self):
        """Un cliente MCP deja el servidor vivo; tras editar es fácil probar lo viejo.

        `revision` cambia en cuanto cambia cualquier fuente, así que comparar dos
        pings dice si el reinicio surtió efecto. Y `modo` evita discutir si el
        informe acumula o no: lo dice el propio servidor.
        """
        respuesta = mcp_server.ping()
        self.assertRegex(respuesta["revision"], r"^[0-9a-f]{8}$")
        self.assertIn(respuesta["informe"]["modo"], ("ultimo", "acumula"))

    def test_la_revision_cambia_si_cambia_el_codigo(self):
        original = mcp_server._revision()
        plantilla = (Path(mcp_server.__file__).resolve().parent /
                     "visualizacion" / "plantillas" / "informe.html")
        guardado = plantilla.read_bytes()
        try:
            plantilla.write_bytes(guardado + b"\n<!-- cambio de prueba -->\n")
            self.assertNotEqual(mcp_server._revision(), original)
        finally:
            plantilla.write_bytes(guardado)
        self.assertEqual(mcp_server._revision(), original)

    def test_la_descripcion_usa_las_palabras_del_usuario(self):
        """El modelo elige herramienta leyendo la descripción, no el código.

        Observado: con las herramientas precargadas, el conector encendido y el
        build al día, pedir "resuelve numéricamente, grafica x(t) y muestra el
        plano de fase" seguía sin disparar esta herramienta -- su descripción no
        contenía ninguna de esas palabras y el modelo escribía su propio
        `solve_ivp`. La regla es que la descripción diga lo que el usuario dice,
        no lo que dice el código.
        """
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "resolver_graficar_y_analizar_edo")
        texto = herramienta.description.lower()
        for palabra in ("resolver numéricamente", "graficar", "x(t)", "plano de fase",
                        "retrato de fase", "campo de direcciones", "línea de fase",
                        "trayectoria 3d", "equilibrio", "estabilidad", "ciclos límite"):
            self.assertIn(palabra, texto, f"la descripción no dice {palabra!r}")

    def test_la_descripcion_desaconseja_calcular_por_su_cuenta(self):
        """Lo que el modelo calcule aparte no pasa por el portón de verificación."""
        textos = {h.name: h.description.lower()
                  for h in _ejecutar(mcp_server.servidor.list_tools())}
        self.assertIn("no escribas código", textos["resolver_graficar_y_analizar_edo"])
        self.assertIn("solve_ivp", textos["resolver_graficar_y_analizar_edo"])
        self.assertIn("matplotlib", textos["resolver_graficar_y_analizar_edo"])
        self.assertIn("no escribas código", textos["analizar_equilibrios"])

    def test_informe_no_pide_argumentos(self):
        """Se llama para entregarle el enlace al usuario; no debe exigir nada."""
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "informe")
        self.assertEqual(set(herramienta.input_schema.get("required") or []), set())

    def test_analizar_equilibrios_no_exige_condicion_inicial(self):
        """Es la razón de que exista: preguntar por equilibrios sin inventar un PVI."""
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "analizar_equilibrios")
        requeridos = set(herramienta.input_schema["required"])
        self.assertEqual(requeridos, {"ecuaciones", "variables_estado"})
        self.assertNotIn("y0", requeridos)
        self.assertNotIn("intervalo", requeridos)

    def test_analizar_edo_declara_sus_parametros_obligatorios(self):
        """La condición inicial es opcional: 'halle la solución general' no la tiene."""
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "resolver_graficar_y_analizar_edo")
        esquema = herramienta.input_schema
        self.assertEqual(set(esquema["required"]), {"ecuaciones", "variables_estado"})
        for campo in ("y0", "intervalo", "parametros", "solucion_exacta", "enunciado", "metodo_analitico",
                      "pedidos", "parametro", "rango_parametro", "region", "solucion_particular",
                      "trozos", "separacion_inicial"):
            self.assertIn(campo, esquema["properties"], f"falta {campo}")

    def test_analizar_equilibrios_recibe_el_problema_completo(self):
        herramienta = next(h for h in _ejecutar(mcp_server.servidor.list_tools())
                           if h.name == "analizar_equilibrios")
        for campo in ("enunciado", "metodo_analitico", "pedidos", "parametro", "rango_parametro", "region"):
            self.assertIn(campo, herramienta.input_schema["properties"], f"falta {campo}")

    def test_las_instrucciones_explican_el_desarrollo_y_el_alcance(self):
        """El modelo debe presentar lo que el servidor calculó, y decir lo que no pertenece al proyecto."""
        texto = mcp_server.servidor.instructions
        self.assertIn("desarrollo.secciones", texto)
        self.assertIn("FUERA DEL ALCANCE DEL PROYECTO", texto)
        self.assertIn("mensaje_para_el_usuario", texto)
        self.assertIn("enunciado", texto)
        self.assertNotIn("pendiente de implementación", texto.lower())
        self.assertNotIn("POR AHORA", texto)
        for tema in ("Tema 1", "Tema 2", "Tema 3", "Tema 4", "Tema 5"):
            self.assertIn(tema, texto)

    def test_las_instrucciones_dicen_que_hacer_con_lo_que_no_es_matematica(self):
        texto = mcp_server.servidor.instructions
        self.assertIn("NO ES DE MATEMÁTICAS", texto)
        self.assertIn("etapa='datos'", texto)

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
        familias = {f["familia"] for f in resultado["capacidades"]["desarrollo_matematico"]["familias"]}
        self.assertTrue({"separable", "bernoulli", "riccati", "cauchy_euler", "hopf", "mapa_1d"} <= familias)

    def test_la_llamada_por_el_protocolo_valida_y_resuelve(self):
        """Lo que llega por JSON-RPC (trozos como diccionarios, sin condición inicial) funciona."""
        respuesta = _ejecutar(mcp_server.servidor.call_tool("resolver_graficar_y_analizar_edo", {
            "ecuaciones": ["x"], "variables_estado": ["x"], "tipo_de_sistema": "mapa_discreto",
            "trozos": [{"expresion": "2*x", "desde": 0, "hasta": 0.5},
                       {"expresion": "2*(1 - x)", "desde": 0.5, "hasta": 1}],
            "separacion_inicial": 1e-10, "visualizar": False}))
        resultado = json.loads(respuesta.content[0].text)
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "mapa_1d")
        self.assertEqual(resultado["solucion"]["resultados"]["horizonte"], 34)

    def test_la_herramienta_de_caos_por_el_protocolo(self):
        """Solo el enunciado, como lo mandaría Claude: el tema se lee de él."""
        respuesta = _ejecutar(mcp_server.servidor.call_tool("resolver_caos_fractales_y_atractores", {
            "enunciado": "Calcule rigurosamente la dimensión de caja del conjunto ternario de Cantor.",
            "visualizar": False}))
        resultado = json.loads(respuesta.content[0].text)
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "dimension_fractal")
        self.assertAlmostEqual(resultado["solucion"]["resultados"]["dimension"]["valor"],
                               math.log(2) / math.log(3), places=12)

    def test_una_pregunta_ajena_vuelve_con_el_alcance_del_proyecto(self):
        respuesta = _ejecutar(mcp_server.servidor.call_tool("resolver_caos_fractales_y_atractores", {
            "enunciado": "Dame un color bonito para pintar mi cuarto"}))
        resultado = json.loads(respuesta.content[0].text)
        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["etapa"], "no_es_un_problema_del_proyecto")
        self.assertIn("no es un problema matemático", resultado["mensaje_para_el_usuario"])
        self.assertEqual(len(resultado["alcance"]), 5)

    def test_la_solucion_general_se_pide_sin_condicion_inicial(self):
        resultado = mcp_server.analizar_edo(
            ecuaciones=["yp", "(2*x*yp - 2*y + x**3*log(x))/x**2"], variables_estado=["y", "yp"],
            variable_independiente="x", visualizar=False,
            enunciado="Halle la solución general de x^2 y'' - 2x y' + 2y = x^3 ln x")
        self.assertTrue(resultado["ok"], resultado.get("error"))
        self.assertEqual(resultado["desarrollo"]["familia"], "cauchy_euler")

    def test_listar_balotario_dice_el_alcance_de_cada_problema(self):
        resultado = mcp_server.listar_balotario()
        problemas = {p["id"]: p for t in resultado["temas"] for p in t["problemas"]}
        self.assertEqual(problemas["1.2"]["alcance"], "dentro")
        self.assertIn("bernoulli", problemas["1.2"]["familias"])
        self.assertEqual(problemas["4.1"]["familias"], ["mapa_1d"])
        self.assertTrue(all(p["alcance"] == "dentro" for p in problemas.values()))
        self.assertEqual(len(problemas), 25)
        for identificador, familia in (("4.2", "duplicacion_periodo"), ("4.3", "feigenbaum"),
                                       ("4.4", "disipatividad"), ("4.5", "espectro_lyapunov"),
                                       ("5.1", "dimension_fractal"), ("5.2", "herradura"), ("5.3", "mapa_2d"),
                                       ("5.4", "seccion_poincare"), ("5.5", "kaplan_yorke")):
            self.assertEqual(problemas[identificador]["familias"], [familia])
            self.assertEqual(problemas[identificador]["solicitud"]["herramienta"],
                             "resolver_caos_fractales_y_atractores")
        self.assertIn("Poincaré-Bendixson no aplica", problemas["2.5"]["revision_matematica"])
        self.assertIn("36/35", problemas["3.5"]["revision_matematica"])
        self.assertIn("−1.1314", problemas["5.3"]["revision_matematica"])
        self.assertIn("ẏ < 0", problemas["5.4"]["revision_matematica"])
        self.assertEqual(len(resultado["alcance"]), 5)

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
