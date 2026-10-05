"""El balotario como especificación: integridad del catálogo y lo que el agente reproduce de él.

Las expectativas no se escriben aquí: se leen de `balotario/tema_*.json`, que a
su vez transcribe `balotario.tex`. Este archivo solo sabe *cómo* comparar cada
tipo de solución esperada, no *cuál* es la respuesta de cada problema.

Tres niveles:

1. el catálogo está completo y es coherente (estructura, procedencia, alcance);
2. sus soluciones son consistentes con una integración numérica independiente
   (el JSON no es la única fuente de verdad);
3. el agente, recibiendo el problema como lo recibiría de un cliente, llega a
   los mismos resultados que el balotario. Donde el balotario se equivoca
   (2.5 y 3.5, documentados en `revision_matematica`), el agente debe llegar al
   resultado correcto, no al del .tex.
"""

import math
import unittest

import numpy as np
import sympy as sp
from scipy.special import ellipk

from matematica.clasificacion import FAMILIAS, FUERA_DE_ALCANCE
from matematica.expresiones import campo_desde_catalogo, escalar_desde_catalogo
from matematica.modelo_edos import resolver_edo
from orquestacion.capacidades import analizar_edo, analizar_equilibrios_sistema
from orquestacion.catalogo import cargar_catalogo


def _problemas():
    """Todos los problemas de todos los temas, aplanados."""
    for tema in cargar_catalogo():
        for problema in tema["problemas"]:
            yield problema


def _indice():
    return {problema["id"]: problema for problema in _problemas()}


def _resolver(problema):
    """Integra el problema con la configuración numérica declarada en el catálogo."""
    ecuacion = problema["ecuacion"]
    ci = problema["condiciones_iniciales"]
    numerico = problema.get("numerico", {})
    return resolver_edo(
        campo_desde_catalogo(ecuacion), ci["y0"], ci["intervalo_sugerido"],
        ecuacion["parametros"],
        puntos=numerico.get("puntos", 300),
        metodo=numerico.get("metodo", "RK45"),
        rtol=numerico.get("rtol", 1e-6),
        atol=numerico.get("atol", 1e-9),
    )


def _error_maximo(problema):
    """Mayor desvío entre la trayectoria numérica y la solución esperada."""
    ecuacion, esperada = problema["ecuacion"], problema["solucion_esperada"]
    solucion = _resolver(problema)
    exacta = escalar_desde_catalogo(esperada["expresion"], ecuacion)
    valores = np.asarray(exacta(**{ecuacion["variable_independiente"]: solucion.t}), dtype=float)
    componente = ecuacion["variables_estado"].index(esperada["componente"])
    return np.abs(solucion.y[componente] - np.broadcast_to(valores, solucion.t.shape)).max()


def _texto(resultado):
    """Un resultado del desarrollo tal como viaja en JSON, de vuelta a sympy."""
    return sp.sympify(resultado["texto"])


def _plano(expresion):
    expresion = sp.sympify(expresion)
    return expresion.subs({s: sp.Symbol(s.name) for s in expresion.free_symbols})


def _solicitud(problema, **extra):
    """El problema del catálogo como lo pediría un cliente, con su enunciado."""
    ecuacion = problema["ecuacion"]
    solicitud = dict(ecuaciones=ecuacion["campo"], variables_estado=ecuacion["variables_estado"],
                     variable_independiente=ecuacion.get("variable_independiente", "t"),
                     parametros=ecuacion.get("parametros") or {}, enunciado=problema["enunciado"],
                     visualizar=False)
    ci = problema.get("condiciones_iniciales")
    if ci:
        solicitud.update(y0=ci["y0"], intervalo=ci["intervalo_sugerido"])
    solicitud.update(extra)
    return solicitud


def _casos_de_equilibrios(problema):
    """(etiqueta, ecuación, parámetros, equilibrios esperados) de un problema del catálogo."""
    esperada, ecuacion = problema["solucion_esperada"], problema["ecuacion"]
    if "equilibrios" in esperada and esperada["tipo"] != "ciclo_limite":
        yield problema["id"], ecuacion, ecuacion["parametros"], esperada["equilibrios"]
    for caso in esperada.get("casos", []):
        yield problema["id"], ecuacion, caso["parametros"], caso["equilibrios"]
    for variante, casos in esperada.get("casos_variante", {}).items():
        bloque = next(b for b in problema["variantes"] if b["id"] == variante)
        for caso in casos:
            yield variante, bloque, caso["parametros"], caso["equilibrios"]


class EstructuraBalotarioTests(unittest.TestCase):
    """El catálogo debe estar completo antes de poder verificar matemática."""

    def test_el_balotario_esta_completo(self):
        """Los cinco temas del .tex, con cinco problemas cada uno."""
        temas = cargar_catalogo()
        self.assertEqual([t["tema"]["id"] for t in temas],
                         ["tema_01", "tema_02", "tema_03", "tema_04", "tema_05"])
        for tema in temas:
            with self.subTest(tema=tema["tema"]["id"]):
                self.assertEqual(len(tema["problemas"]), 5)

    def test_cada_problema_declara_los_campos_requeridos(self):
        for problema in _problemas():
            with self.subTest(problema=problema["id"]):
                for clave in ("id", "orden", "titulo", "enunciado", "tipo", "dificultad",
                              "verificable_con_solver", "ecuacion", "solucion_esperada"):
                    self.assertIn(clave, problema)
                self.assertIn(problema["dificultad"], ("basica", "intermedia", "avanzada"))
                self.assertTrue(problema["enunciado"].strip())

    def test_los_identificadores_siguen_el_numero_de_tema(self):
        for tema in cargar_catalogo():
            numero = tema["tema"]["orden"]
            for problema in tema["problemas"]:
                with self.subTest(problema=problema["id"]):
                    self.assertEqual(problema["id"], f"{numero}.{problema['orden']}")

    def test_un_problema_no_verificable_explica_por_que(self):
        for problema in _problemas():
            if problema["verificable_con_solver"]:
                continue
            with self.subTest(problema=problema["id"]):
                self.assertTrue(problema.get("motivo_no_verificable", "").strip())

    def test_un_problema_pendiente_declara_que_el_tex_no_lo_resuelve(self):
        """Nueve problemas del .tex no traen solución; eso debe quedar explícito."""
        pendientes = []
        for problema in _problemas():
            esperada = problema["solucion_esperada"]
            if esperada["tipo"] != "pendiente":
                continue
            pendientes.append(problema["id"])
            with self.subTest(problema=problema["id"]):
                self.assertFalse(esperada["solucion_en_tex"])
                self.assertTrue(esperada.get("nota", "").strip())
        self.assertEqual(pendientes, ["4.2", "4.3", "4.4", "4.5",
                                      "5.1", "5.2", "5.3", "5.4", "5.5"])

    def test_el_alcance_del_agente_es_el_del_balotario(self):
        """Lo resuelto en el .tex es lo que las familias implementan; lo pendiente, lo fuera de alcance."""
        resueltos = {p["id"] for p in _problemas() if p["solucion_esperada"]["tipo"] != "pendiente"}
        pendientes = {p["id"] for p in _problemas() if p["solucion_esperada"]["tipo"] == "pendiente"}
        self.assertEqual({ref for f in FAMILIAS for ref in f.balotario}, resueltos)
        self.assertEqual({problema for problema, *_ in FUERA_DE_ALCANCE.values()}, pendientes)

    def test_las_revisiones_matematicas_estan_documentadas(self):
        revisados = {p["id"]: p["revision_matematica"] for p in _problemas() if "revision_matematica" in p}
        self.assertEqual(sorted(revisados), ["2.5", "3.5"])
        for identificador, revision in revisados.items():
            with self.subTest(problema=identificador):
                self.assertFalse(revision["tex_modificado"])
                self.assertTrue(revision["resumen"].strip())
                self.assertIn("tests/", revision["verificado_por"])

    def test_dimension_coincide_con_estado_y_campo(self):
        for problema in _problemas():
            ecuacion = problema["ecuacion"]
            if "campo" not in ecuacion:
                continue
            with self.subTest(problema=problema["id"]):
                n = ecuacion["dimension"]
                self.assertEqual(len(ecuacion["variables_estado"]), n)
                self.assertEqual(len(ecuacion["campo"]), n)

    def test_condicion_inicial_coherente_con_la_dimension(self):
        for problema in _problemas():
            if "condiciones_iniciales" not in problema:
                continue
            with self.subTest(problema=problema["id"]):
                self.assertEqual(len(problema["condiciones_iniciales"]["y0"]),
                                 problema["ecuacion"]["dimension"])

    def test_campo_se_construye_y_evalua(self):
        for problema in _problemas():
            ecuacion = problema["ecuacion"]
            if "campo" not in ecuacion or not ecuacion["campo"]:
                continue
            ci = problema.get("condiciones_iniciales")
            punto = ci["y0"] if ci else [0.1] * ecuacion["dimension"]
            t0 = ci["t0"] if ci else 0.0
            with self.subTest(problema=problema["id"]):
                derivada = campo_desde_catalogo(ecuacion)(t0, punto, ecuacion["parametros"])
                self.assertEqual(len(derivada), ecuacion["dimension"])
                self.assertTrue(all(math.isfinite(float(v)) for v in derivada))

    def test_condiciones_iniciales_derivadas_estan_justificadas(self):
        """Una CI que no está en el .tex debe declararlo y explicar de dónde sale."""
        for problema in _problemas():
            ci = problema.get("condiciones_iniciales")
            if ci is None:
                continue
            with self.subTest(problema=problema["id"]):
                self.assertIn("ci_derivada", ci)
                if ci["ci_derivada"]:
                    self.assertTrue(ci.get("notas", "").strip())


class ConsistenciaNumericaDelCatalogoTests(unittest.TestCase):
    """El JSON contra una integración independiente: no es la única fuente de verdad."""

    def test_solucion_numerica_coincide_con_la_esperada(self):
        casos = [p for p in _problemas() if p["solucion_esperada"]["tipo"] == "analitica_explicita"]
        self.assertTrue(casos)
        for problema in casos:
            esperada = problema["solucion_esperada"]
            with self.subTest(problema=problema["id"]):
                self.assertLess(_error_maximo(problema), esperada["tolerancia"])

    def test_1_1_explota_fuera_del_intervalo_maximal(self):
        problema = _indice()["1.1"]
        singularidad = problema["solucion_esperada"]["datos_adicionales"]["singularidad_positiva"]
        self.assertAlmostEqual(singularidad, math.sqrt(2 / 3), places=12)
        ecuacion, ci = problema["ecuacion"], problema["condiciones_iniciales"]
        with self.assertRaises(RuntimeError):
            resolver_edo(campo_desde_catalogo(ecuacion), ci["y0"],
                         (ci["t0"], singularidad + 0.4), ecuacion["parametros"], puntos=200)

    def test_1_5_conserva_la_energia_y_su_periodo_es_el_eliptico(self):
        problema = _indice()["1.5"]
        invariantes = {i["tipo"]: i for i in problema["solucion_esperada"]["invariantes"]}
        ecuacion, ci = problema["ecuacion"], problema["condiciones_iniciales"]
        solucion = _resolver(problema)
        energia = escalar_desde_catalogo(invariantes["conservado"]["expresion"], ecuacion)
        valores = {ecuacion["variable_independiente"]: solucion.t, **ecuacion["parametros"],
                   **{nombre: solucion.y[i] for i, nombre in enumerate(ecuacion["variables_estado"])}}
        e = np.asarray(energia(**valores), dtype=float)
        self.assertLess(np.abs(e - e[0]).max(), invariantes["conservado"]["tolerancia"])
        k = math.sin(ci["y0"][0] / 2)
        periodo = 4 / ecuacion["parametros"]["w0"] * float(ellipk(k * k))
        self.assertAlmostEqual(periodo, invariantes["periodo"]["valor"], places=10)
        self.assertAlmostEqual(ci["intervalo_sugerido"][1], 3 * periodo, places=9)

    def test_los_puntos_fijos_y_el_exponente_del_mapa_tienda(self):
        esperada = _indice()["4.1"]["solucion_esperada"]
        valores = esperada["valores"]
        self.assertAlmostEqual(valores["exponente_lyapunov"], math.log(2), places=15)
        self.assertEqual(valores["iteraciones_hasta_orden_uno"],
                         math.ceil(math.log(1 / valores["delta_inicial"]) / math.log(2)))
        puntos = [p["punto"][0] for p in esperada["puntos_fijos"]]
        self.assertAlmostEqual(puntos[1], 2 / 3, places=15)


class ElAgenteReproduceElTema1Tests(unittest.TestCase):
    """El agente recibe cada problema como un cliente y llega a la solución del balotario."""

    def _desarrollo(self, identificador, **extra):
        resultado = analizar_edo(_solicitud(_indice()[identificador], **extra))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        return resultado

    def test_soluciones_explicitas(self):
        extras = {"1.4": {"solucion_particular": "x"}}
        for identificador, familia in (("1.1", "separable"), ("1.2", "bernoulli"),
                                       ("1.3", "cauchy_euler"), ("1.4", "riccati")):
            with self.subTest(problema=identificador):
                problema = _indice()[identificador]
                resultado = self._desarrollo(identificador, **extras.get(identificador, {}))
                self.assertEqual(resultado["desarrollo"]["familia"], familia)
                calculada = _texto(resultado["desarrollo"]["resultados"]["solucion_particular"])
                esperada = sp.nsimplify(sp.sympify(problema["solucion_esperada"]["expresion"]), rational=True)
                self.assertEqual(sp.simplify(_plano(calculada) - esperada), 0)
                pruebas = {p["nombre"]: p for p in resultado["verificacion"]["pruebas"]}
                self.assertTrue(pruebas["solucion_exacta"]["ok"])

    def test_1_1_intervalo_maximal(self):
        resultado = self._desarrollo("1.1")
        esperado = _indice()["1.1"]["solucion_esperada"]["datos_adicionales"]["intervalo_maximal"]
        self.assertIn("intervalo_maximal", resultado["desarrollo"]["resultados"])
        intervalo = sp.sympify(resultado["desarrollo"]["resultados"]["intervalo_maximal"]["texto"])
        self.assertAlmostEqual(float(intervalo.inf), esperado[0], places=12)
        self.assertAlmostEqual(float(intervalo.sup), esperado[1], places=12)

    def test_1_5_energia_separatriz_y_periodo(self):
        problema = _indice()["1.5"]
        resultado = self._desarrollo("1.5", parametro="w0", rango_parametro=[0, None])
        resultados = resultado["desarrollo"]["resultados"]
        invariantes = {i["tipo"]: i for i in problema["solucion_esperada"]["invariantes"]}
        energia = sp.nsimplify(sp.sympify(invariantes["conservado"]["expresion"]), rational=True)
        diferencia = sp.simplify(_plano(_texto(resultados["hamiltoniano"])) - energia)
        self.assertFalse(diferencia.free_symbols & {sp.Symbol("theta"), sp.Symbol("thetapunto")},
                         "la energía puede diferir solo en una constante")
        separatriz = sp.sympify(problema["solucion_esperada"]["datos_adicionales"]["separatriz_expresion"])
        self.assertEqual(sp.simplify(_plano(_texto(resultados["separatriz"])) - separatriz), 0)
        self.assertAlmostEqual(resultados["periodo"], invariantes["periodo"]["valor"], places=9)


class ElAgenteReproduceLosEquilibriosTests(unittest.TestCase):
    """Temas 2 y 3: cada caso del catálogo, con los parámetros de ese caso."""

    def test_equilibrios_y_su_clasificacion_en_cada_caso(self):
        for identificador in ("2.1", "2.2", "2.3", "2.4", "3.1", "3.2", "3.3", "3.4", "3.5"):
            for etiqueta, ecuacion, parametros, esperados in _casos_de_equilibrios(_indice()[identificador]):
                with self.subTest(problema=etiqueta, parametros=parametros):
                    resultado = analizar_equilibrios_sistema(dict(
                        ecuaciones=ecuacion["campo"], variables_estado=ecuacion["variables_estado"],
                        parametros=parametros))
                    self.assertTrue(resultado["ok"], resultado.get("error"))
                    calculados = resultado["analisis"]["estabilidad"]["equilibrios"]
                    self.assertEqual(len(calculados), len(esperados))
                    for esperado in esperados:
                        calculado = next(c for c in calculados
                                         if np.allclose(c["punto"], esperado["punto"], atol=1e-12))
                        self._comparar(calculado, esperado)

    def _comparar(self, calculado, esperado):
        if esperado["clasificacion_motor"] == "no concluyente" and calculado["clasificacion"] != "no concluyente":
            # La linealización no decide; el agente sí, con derivadas de orden superior (ẋ = −x³).
            self.assertIn("no hiperbólico", calculado["tipo"])
        else:
            self.assertEqual(calculado["clasificacion"], esperado["clasificacion_motor"])
        if "autovalores" in esperado:
            def complejo(valor):
                return complex(valor["re"], valor["im"]) if isinstance(valor, dict) else complex(valor)
            np.testing.assert_allclose(
                np.sort_complex(np.array([complejo(v) for v in calculado["autovalores"]])),
                np.sort_complex(np.array([complejo(v) for v in esperado["autovalores"]])), atol=1e-9)

    def test_2_1_trayectorias(self):
        problema = _indice()["2.1"]
        resultado = analizar_edo(_solicitud(problema))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        invariante = next(i for i in problema["solucion_esperada"]["invariantes"] if i["nombre"] == "trayectorias")
        calculado = sp.sympify(resultado["desarrollo"]["resultados"]["ecuacion_trayectorias"]["texto"])
        self.assertEqual(sp.simplify(_plano(calculado.lhs) - sp.sympify(invariante["expresion"])), 0)

    def test_2_4_hamiltoniano_y_lazo(self):
        problema = _indice()["2.4"]
        resultado = analizar_edo(_solicitud(problema))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        resultados = resultado["desarrollo"]["resultados"]
        invariante = next(i for i in problema["solucion_esperada"]["invariantes"] if i["tipo"] == "conservado")
        H = sp.nsimplify(sp.sympify(invariante["expresion"]), rational=True)
        self.assertEqual(sp.simplify(_plano(_texto(resultados["hamiltoniano"])) - H), 0)
        lazo = sp.sympify(problema["solucion_esperada"]["datos_adicionales"]["separatriz_expresion"])
        self.assertEqual(sp.simplify(_plano(_texto(resultados["separatriz"])) - lazo), 0)

    def test_3_4_amplitud_y_periodo_del_ciclo(self):
        problema = _indice()["3.4"]
        resultado = analizar_equilibrios_sistema(_solicitud(problema, parametro="mu"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        resultados = resultado["desarrollo"]["resultados"]
        radio = _plano(_texto(resultados["radio_ciclo"]))
        self.assertEqual(_texto(resultados["periodo"]), 2 * sp.pi)
        self.assertAlmostEqual(resultados["periodo"]["valor"],
                               problema["solucion_esperada"]["datos_adicionales"]["periodo"], places=12)
        for caso in problema["solucion_esperada"]["casos"]:
            if caso.get("ciclo_limite"):
                with self.subTest(parametros=caso["parametros"]):
                    valor = float(radio.subs(sp.Symbol("mu"), caso["parametros"]["mu"]))
                    self.assertAlmostEqual(valor, caso["ciclo_limite"]["radio"], places=12)

    def test_4_1_exponente_y_horizonte(self):
        problema = _indice()["4.1"]
        resultado = analizar_edo(dict(ecuaciones=["1 - Abs(1 - 2*x)"], variables_estado=["x"],
                                      tipo_de_sistema="mapa_discreto", enunciado=problema["enunciado"],
                                      visualizar=False))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        valores = problema["solucion_esperada"]["valores"]
        resultados = resultado["solucion"]["resultados"]
        self.assertAlmostEqual(resultados["lyapunov"]["valor"], valores["exponente_lyapunov"], places=12)
        self.assertEqual(resultados["horizonte"], valores["iteraciones_hasta_orden_uno"])


class RevisionesDelBalotarioTests(unittest.TestCase):
    """Donde el .tex se equivoca, el agente llega al resultado correcto."""

    def test_2_5_no_hay_orbita_periodica(self):
        problema = _indice()["2.5"]
        resultado = analizar_edo(_solicitud(problema))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        desarrollo = resultado["desarrollo"]
        self.assertEqual(desarrollo["familia"], "ciclo_limite")
        self.assertEqual(desarrollo["resultados"]["conclusion_poincare_bendixson"], "no_aplica_equilibrio_en_K")
        self.assertTrue(any("Ninguna órbita es periódica" in c for c in desarrollo["conclusiones"]))
        # La trayectoria que el catálogo usaba para "ver el ciclo" termina en el equilibrio (1, 0).
        resultado = analizar_edo(_solicitud(problema, intervalo=[0, 400]))
        final = resultado["solucion"]["estado_final"]
        self.assertLess(math.hypot(final["x"] - 1, final["y"]), 0.05)

    def test_3_5_melnikov_corregido_y_disparo_numerico(self):
        problema = _indice()["3.5"]
        revision = problema["revision_matematica"]["valores_corregidos"]
        resultado = analizar_equilibrios_sistema(_solicitud(problema, parametro="mu", metodo_analitico="homoclinica"))
        self.assertTrue(resultado["ok"], resultado.get("error"))
        resultados = resultado["desarrollo"]["resultados"]
        self.assertEqual(_texto(resultados["I2"]), sp.Rational(36, 35))
        self.assertAlmostEqual(resultados["mu_melnikov"]["valor"], revision["mu_melnikov"], places=12)
        self.assertAlmostEqual(resultados["mu_numerico"], revision["mu_numerico"], places=3)
        # El .tex da μc = −5/7: lo que el agente calcula no es eso.
        self.assertNotAlmostEqual(resultados["mu_melnikov"]["valor"],
                                  problema["solucion_esperada"]["datos_adicionales"]["mu_critico"], places=3)


if __name__ == "__main__":
    unittest.main()
