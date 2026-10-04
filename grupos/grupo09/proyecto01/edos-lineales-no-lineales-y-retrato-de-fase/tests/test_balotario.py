"""Pasa cada ejercicio del balotario por el solver y lo compara con su solución esperada.

Las expectativas no se escriben aquí: se leen de `balotario/tema_*.json`, que a su
vez transcribe `balotario.tex`. Este archivo solo sabe *cómo* verificar cada tipo
de solución esperada, no *cuál* es la respuesta de cada problema.

Las expresiones del JSON se compilan con `matematica.expresiones`, el mismo
módulo que usa el servidor MCP para las EDOs que llegan de un cliente: así el
balotario ejercita la ruta real de entrada y no una copia paralela.
"""

import math
import unittest

import numpy as np
import sympy as sp
from scipy.special import ellipk

from matematica.analisis_estabilidad import analizar_equilibrios
from matematica.expresiones import campo_desde_catalogo, escalar_desde_catalogo
from matematica.modelo_edos import resolver_edo
from orquestacion.capacidades import buscar_equilibrios
from orquestacion.catalogo import cargar_catalogo


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
    valores = np.asarray(exacta(**{ecuacion["variable_independiente"]: solucion.t}),
                         dtype=float)
    componente = ecuacion["variables_estado"].index(esperada["componente"])
    return np.abs(solucion.y[componente] - np.broadcast_to(valores, solucion.t.shape)).max()


def _ecuacion_del_caso(problema, variante=None):
    """Bloque `ecuacion` del problema, o el de una de sus variantes."""
    if variante is None:
        return problema["ecuacion"]
    for bloque in problema.get("variantes", []):
        if bloque["id"] == variante:
            return bloque
    raise AssertionError(f"El problema {problema['id']} no declara la variante {variante!r}")


def _equilibrios_calculados(ecuacion, parametros):
    """Equilibrios exactos del campo más su clasificación, ordenados."""
    campo = campo_desde_catalogo({**ecuacion, "parametros": parametros})
    puntos, origen = buscar_equilibrios(campo, parametros)
    resultados = analizar_equilibrios(campo, sorted(puntos), parametros) if puntos else []
    return resultados, origen


def _clasificacion_corta(texto):
    """Normaliza el veredicto del motor al vocabulario del catálogo."""
    return "no concluyente" if texto.startswith("no concluyente") else texto


def _radio_final(ecuacion, radio_inicial, intervalo, numerico, fraccion=0.25):
    """Integra desde un radio dado y devuelve el radio en el tramo final."""
    campo = campo_desde_catalogo(ecuacion)
    parametros = ecuacion.get("parametros", {})
    solucion = resolver_edo(campo, [radio_inicial, 0.0], intervalo, parametros,
                            puntos=numerico.get("puntos", 4000),
                            metodo=numerico.get("metodo", "RK45"),
                            rtol=numerico.get("rtol", 1e-10),
                            atol=numerico.get("atol", 1e-12))
    radios = np.hypot(solucion.y[0], solucion.y[1])
    desde = int(len(radios) * (1 - fraccion))
    return radios[desde:]


def _problemas():
    """Todos los problemas de todos los temas, aplanados."""
    for tema in cargar_catalogo():
        for problema in tema["problemas"]:
            yield problema


def _indice():
    return {problema["id"]: problema for problema in _problemas()}


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
        self.assertEqual(sum(len(t["problemas"]) for t in temas), 25)

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
                self.assertTrue(problema.get("motivo_no_verificable", "").strip(),
                                "declarar no verificable exige decir el motivo")

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
                    self.assertTrue(ci.get("notas", "").strip(),
                                    "una CI derivada necesita notas que la justifiquen")


class SolucionAnaliticaTests(unittest.TestCase):
    """Compara la trayectoria numérica contra la solución cerrada del balotario."""

    def test_solucion_numerica_coincide_con_la_esperada(self):
        casos = [p for p in _problemas()
                 if p["solucion_esperada"]["tipo"] == "analitica_explicita"]
        self.assertTrue(casos, "no hay soluciones analíticas que verificar")
        for problema in casos:
            esperada = problema["solucion_esperada"]
            with self.subTest(problema=problema["id"], tipo=problema["tipo"]):
                error = _error_maximo(problema)
                self.assertLess(error, esperada["tolerancia"],
                                f"error máximo {error:.3e} supera la tolerancia")

    def test_error_observado_registrado_sigue_siendo_representativo(self):
        """Detecta una degradación silenciosa del integrador."""
        for problema in _problemas():
            esperada = problema["solucion_esperada"]
            if esperada["tipo"] != "analitica_explicita" or "error_observado" not in esperada:
                continue
            with self.subTest(problema=problema["id"]):
                registrado = esperada["error_observado"]
                self.assertLessEqual(_error_maximo(problema), max(10 * registrado, 1e-14),
                                     f"el error creció frente al registrado ({registrado:.1e})")


class VerificacionesEspecificasTests(unittest.TestCase):
    """Comprobaciones que el enunciado pide y que no son comparación puntual."""

    def test_1_1_explota_fuera_del_intervalo_maximal(self):
        problema = _indice()["1.1"]
        singularidad = problema["solucion_esperada"]["datos_adicionales"]["singularidad_positiva"]
        self.assertAlmostEqual(singularidad, math.sqrt(2 / 3), places=12)
        ecuacion, ci = problema["ecuacion"], problema["condiciones_iniciales"]
        with self.assertRaises(RuntimeError):
            resolver_edo(campo_desde_catalogo(ecuacion), ci["y0"],
                         (ci["t0"], singularidad + 0.4), ecuacion["parametros"], puntos=200)

    def test_1_2_la_condicion_inicial_es_un_equilibrio_exacto(self):
        problema = _indice()["1.2"]
        ecuacion, ci = problema["ecuacion"], problema["condiciones_iniciales"]
        derivada = campo_desde_catalogo(ecuacion)(ci["t0"], ci["y0"], ecuacion["parametros"])
        self.assertEqual(float(derivada[0]), 0.0)

    def test_1_4_la_solucion_particular_anula_el_residuo(self):
        """y_1(x) = x debe satisfacer la EDO de Riccati, como pide el enunciado."""
        problema = _indice()["1.4"]
        ecuacion = problema["ecuacion"]
        particular = problema["solucion_esperada"]["datos_adicionales"]["solucion_particular_expresion"]
        x = sp.Symbol(ecuacion["variable_independiente"])
        y1 = sp.sympify(particular, locals={str(x): x})
        campo = sp.sympify(ecuacion["campo"][0],
                           locals={str(x): x, ecuacion["variables_estado"][0]: y1})
        self.assertEqual(sp.simplify(sp.diff(y1, x) - campo), 0)

    def test_1_5_conserva_la_energia(self):
        problema = _indice()["1.5"]
        invariante = next(i for i in problema["solucion_esperada"]["invariantes"]
                          if i["tipo"] == "conservado")
        ecuacion = problema["ecuacion"]
        solucion = _resolver(problema)
        funcion = escalar_desde_catalogo(invariante["expresion"], ecuacion)
        valores = {ecuacion["variable_independiente"]: solucion.t, **ecuacion["parametros"]}
        valores.update({nombre: solucion.y[i]
                        for i, nombre in enumerate(ecuacion["variables_estado"])})
        energia = np.asarray(funcion(**valores), dtype=float)
        self.assertAlmostEqual(energia[0], invariante["valor_inicial"], places=10)
        self.assertLess(np.abs(energia - energia[0]).max(), invariante["tolerancia"])

    def test_1_5_periodo_coincide_con_la_integral_eliptica(self):
        """Recalcula T con scipy: el JSON no es la única fuente de verdad."""
        problema = _indice()["1.5"]
        invariante = next(i for i in problema["solucion_esperada"]["invariantes"]
                          if i["tipo"] == "periodo")
        ci = problema["condiciones_iniciales"]
        theta0, w0 = ci["y0"][0], problema["ecuacion"]["parametros"]["w0"]
        k = math.sin(theta0 / 2)
        periodo = 4 / w0 * float(ellipk(k * k))
        self.assertAlmostEqual(periodo, invariante["valor"], places=10)
        # El intervalo del catálogo cubre exactamente tres periodos teóricos.
        self.assertAlmostEqual(ci["intervalo_sugerido"][1], 3 * periodo, places=9)
        solucion = _resolver(problema)
        retorno = np.abs(solucion.y[:, -1] - np.asarray(ci["y0"], dtype=float)).max()
        self.assertLess(retorno, invariante["tolerancia"],
                        f"tras 3 periodos el estado no regresó (desvío {retorno:.3e})")

    def test_1_5_la_separatriz_esta_sobre_su_nivel_de_energia(self):
        problema = _indice()["1.5"]
        datos = problema["solucion_esperada"]["datos_adicionales"]
        ecuacion = problema["ecuacion"]
        separatriz = escalar_desde_catalogo(datos["separatriz_expresion"], ecuacion)
        energia = escalar_desde_catalogo(
            next(i for i in problema["solucion_esperada"]["invariantes"]
                 if i["tipo"] == "conservado")["expresion"], ecuacion)
        parametros = ecuacion["parametros"]
        for theta in (-2.0, -0.5, 0.0, 0.5, 2.0):
            with self.subTest(theta=theta):
                velocidad = float(separatriz(theta=theta, **parametros))
                nivel = float(energia(theta=theta, thetapunto=velocidad, **parametros))
                self.assertAlmostEqual(nivel, datos["energia_separatriz"], places=12)


class ClasificacionEquilibriosTests(unittest.TestCase):
    """Tema 2: los equilibrios y su estabilidad, contra lo que demuestra el .tex."""

    def _comparar(self, etiqueta, ecuacion, parametros, esperados):
        resultados, origen = _equilibrios_calculados(ecuacion, parametros)
        self.assertEqual(len(resultados), len(esperados),
                         f"{etiqueta}: se esperaban {len(esperados)} equilibrios "
                         f"y se hallaron {len(resultados)} ({origen})")
        orden_esperado = sorted(esperados, key=lambda e: e["punto"])
        for calculado, esperado in zip(resultados, orden_esperado):
            with self.subTest(caso=etiqueta, punto=esperado["punto"]):
                np.testing.assert_allclose(calculado["equilibrio"], esperado["punto"],
                                           atol=1e-9)
                self.assertEqual(_clasificacion_corta(calculado["clasificacion"]),
                                 esperado["clasificacion_motor"])
                if "autovalores" in esperado:
                    self._comparar_autovalores(calculado["autovalores"],
                                               esperado["autovalores"])

    def _comparar_autovalores(self, calculados, esperados):
        def normalizar(valor):
            if isinstance(valor, dict):
                return complex(valor["re"], valor["im"])
            return complex(valor)
        np.testing.assert_allclose(
            np.sort_complex(np.asarray(calculados)),
            np.sort_complex(np.asarray([normalizar(v) for v in esperados])),
            atol=1e-8)

    def test_equilibrios_de_los_problemas_con_clasificacion(self):
        casos = [p for p in _problemas()
                 if p["solucion_esperada"]["tipo"] == "clasificacion_equilibrios"]
        self.assertTrue(casos)
        for problema in casos:
            esperada = problema["solucion_esperada"]
            with self.subTest(problema=problema["id"]):
                self._comparar(problema["id"], problema["ecuacion"],
                               problema["ecuacion"]["parametros"],
                               esperada["equilibrios"])

    def test_equilibrios_declarados_junto_a_invariantes(self):
        """El 2.4 trae hamiltoniano y equilibrios a la vez."""
        for problema in _problemas():
            esperada = problema["solucion_esperada"]
            if esperada["tipo"] != "invariantes" or "equilibrios" not in esperada:
                continue
            with self.subTest(problema=problema["id"]):
                self._comparar(problema["id"], problema["ecuacion"],
                               problema["ecuacion"]["parametros"],
                               esperada["equilibrios"])

    def test_energia_de_los_equilibrios_del_2_4(self):
        """H(0,0)=0 en la silla y H(mas/menos 1,0)=-1/4 en los centros."""
        problema = _indice()["2.4"]
        esperada = problema["solucion_esperada"]
        invariante = next(i for i in esperada["invariantes"] if i["tipo"] == "conservado")
        energia = escalar_desde_catalogo(invariante["expresion"], problema["ecuacion"])
        for equilibrio in esperada["equilibrios"]:
            with self.subTest(punto=equilibrio["punto"]):
                valores = dict(zip(problema["ecuacion"]["variables_estado"],
                                   equilibrio["punto"]))
                self.assertAlmostEqual(float(energia(**valores)),
                                       equilibrio["energia"], places=12)


class BifurcacionesTests(unittest.TestCase):
    """Tema 3: como cambian los equilibrios al mover el parametro."""

    def _verificar_casos(self, problema, casos, ecuacion):
        comparador = ClasificacionEquilibriosTests()
        for caso in casos:
            etiqueta = f"{problema['id']} {caso['parametros']}"
            with self.subTest(problema=problema["id"], parametros=caso["parametros"]):
                comparador._comparar(etiqueta, ecuacion, caso["parametros"],
                                     caso["equilibrios"])

    def test_casos_del_parametro(self):
        casos = [p for p in _problemas()
                 if p["solucion_esperada"]["tipo"] == "bifurcacion"]
        self.assertTrue(casos)
        for problema in casos:
            self._verificar_casos(problema, problema["solucion_esperada"]["casos"],
                                  problema["ecuacion"])

    def test_casos_de_las_variantes(self):
        """El 3.3 compara dos sistemas distintos: la horquilla subcritica es variante."""
        for problema in _problemas():
            esperada = problema["solucion_esperada"]
            for variante, casos in esperada.get("casos_variante", {}).items():
                with self.subTest(problema=problema["id"], variante=variante):
                    self._verificar_casos(problema, casos,
                                          _ecuacion_del_caso(problema, variante))

    def test_el_3_1_no_tiene_equilibrios_reales_para_mu_negativo(self):
        problema = _indice()["3.1"]
        caso = next(c for c in problema["solucion_esperada"]["casos"]
                    if c["parametros"]["mu"] < 0)
        resultados, _ = _equilibrios_calculados(problema["ecuacion"], caso["parametros"])
        self.assertEqual(resultados, [])

    def test_el_3_3b_tiene_cinco_equilibrios_en_la_zona_biestable(self):
        """La histeresis exige que el origen y dos pares de ramas coexistan."""
        problema = _indice()["3.3"]
        casos = problema["solucion_esperada"]["casos_variante"]["3.3B"]
        caso = next(c for c in casos if len(c["equilibrios"]) == 5)
        resultados, _ = _equilibrios_calculados(_ecuacion_del_caso(problema, "3.3B"),
                                                caso["parametros"])
        self.assertEqual(len(resultados), 5)

    def test_amplitud_del_ciclo_limite_de_hopf(self):
        """El ciclo que nace del Hopf tiene radio sqrt(mu)."""
        problema = _indice()["3.4"]
        esperada = problema["solucion_esperada"]
        for caso in esperada["casos"]:
            ciclo = caso.get("ciclo_limite")
            if not ciclo:
                continue
            with self.subTest(parametros=caso["parametros"]):
                ecuacion = {**problema["ecuacion"], "parametros": caso["parametros"]}
                radios = _radio_final(ecuacion, ciclo["radio_inicial_de_prueba"],
                                      (0.0, 120.0), {"puntos": 6000, "rtol": 1e-11,
                                                     "atol": 1e-13})
                self.assertAlmostEqual(float(radios[-1]), ciclo["radio"], places=6)
                self.assertAlmostEqual(ciclo["radio"],
                                       math.sqrt(caso["parametros"]["mu"]), places=12)

    def test_periodo_del_ciclo_de_hopf_es_dos_pi(self):
        problema = _indice()["3.4"]
        datos = problema["solucion_esperada"]["datos_adicionales"]
        periodo = datos["periodo"]
        self.assertAlmostEqual(periodo, 2 * math.pi, places=12)
        ecuacion = {**problema["ecuacion"], "parametros": {"mu": 1.0}}
        solucion = resolver_edo(campo_desde_catalogo(ecuacion), [1.0, 0.0],
                                (0.0, periodo), {"mu": 1.0}, puntos=4000,
                                rtol=1e-12, atol=1e-14)
        desvio = np.abs(solucion.y[:, -1] - np.array([1.0, 0.0])).max()
        self.assertLess(desvio, 1e-8, f"tras T=2pi el ciclo no cerro (desvio {desvio:.2e})")

    def test_la_traza_del_3_5_cambia_de_signo_en_el_hopf_local(self):
        """Tr J(1,0) = mu + 1, asi que el Hopf local esta en mu = -1."""
        problema = _indice()["3.5"]
        datos = problema["solucion_esperada"]["datos_adicionales"]
        self.assertEqual(datos["hopf_local"], -1.0)
        for caso in problema["solucion_esperada"]["casos"]:
            mu = caso["parametros"]["mu"]
            esperado = next(e for e in caso["equilibrios"] if e["punto"] == [1.0, 0.0])
            resultados, _ = _equilibrios_calculados(problema["ecuacion"], caso["parametros"])
            calculado = next(r for r in resultados
                             if np.allclose(r["equilibrio"], [1.0, 0.0]))
            with self.subTest(mu=mu):
                self.assertAlmostEqual(float(np.trace(calculado["jacobiano"])),
                                       mu + 1.0, places=9)
                self.assertEqual(_clasificacion_corta(calculado["clasificacion"]),
                                 esperado["clasificacion_motor"])

    def test_el_mu_critico_del_3_5_es_menos_cinco_septimos(self):
        datos = _indice()["3.5"]["solucion_esperada"]["datos_adicionales"]
        self.assertAlmostEqual(datos["mu_critico"], -5 / 7, places=15)


class CicloLimiteTests(unittest.TestCase):
    """Tema 2.5: convergencia al ciclo desde dentro y desde fuera del anillo."""

    def test_convergencia_al_ciclo_limite(self):
        casos = [p for p in _problemas()
                 if p["solucion_esperada"]["tipo"] == "ciclo_limite"]
        self.assertTrue(casos)
        for problema in casos:
            esperada = problema["solucion_esperada"]
            intervalo = problema["condiciones_iniciales"]["intervalo_sugerido"]
            for radio_inicial in esperada["radios_iniciales_de_prueba"]:
                with self.subTest(problema=problema["id"], r0=radio_inicial):
                    radios = _radio_final(problema["ecuacion"], radio_inicial,
                                          intervalo, problema["numerico"],
                                          esperada["fraccion_final_evaluada"])
                    desvio = float(np.abs(radios - esperada["radio"]).max())
                    self.assertLess(desvio, esperada["tolerancia"],
                                    f"el radio no converge a {esperada['radio']} "
                                    f"(desvio {desvio:.2e})")


class ProblemasDiscretosTests(unittest.TestCase):
    """Temas 4 y 5: mapas y demostraciones que el motor todavia no cubre."""

    def test_los_mapas_discretos_declaran_sus_trozos(self):
        for problema in _problemas():
            ecuacion = problema["ecuacion"]
            if ecuacion["forma"] != "mapa_discreto":
                continue
            with self.subTest(problema=problema["id"]):
                self.assertFalse(problema["verificable_con_solver"])
                self.assertTrue(ecuacion["trozos"])
                for trozo in ecuacion["trozos"]:
                    self.assertTrue(trozo["expresion"].strip())
                    self.assertTrue(trozo["condicion"].strip())

    def test_el_exponente_de_lyapunov_del_mapa_tienda_es_log_dos(self):
        """Unico problema del Tema 4 resuelto en el .tex: lambda = ln 2."""
        esperada = _indice()["4.1"]["solucion_esperada"]
        self.assertTrue(esperada["solucion_en_tex"])
        valores = esperada["valores"]
        self.assertAlmostEqual(valores["exponente_lyapunov"], math.log(2), places=15)
        self.assertAlmostEqual(valores["entropia_kolmogorov_sinai"], math.log(2), places=15)
        esperadas = math.ceil(math.log(1 / valores["delta_inicial"]) / math.log(2))
        self.assertEqual(valores["iteraciones_hasta_orden_uno"], esperadas)

    def test_los_puntos_fijos_del_mapa_tienda(self):
        """x=0 y x=2/3 son los puntos fijos de la tienda, ambos inestables."""
        esperada = _indice()["4.1"]["solucion_esperada"]
        puntos = [p["punto"][0] for p in esperada["puntos_fijos"]]
        self.assertAlmostEqual(puntos[0], 0.0, places=15)
        self.assertAlmostEqual(puntos[1], 2 / 3, places=15)
        for fijo in esperada["puntos_fijos"]:
            self.assertEqual(fijo["clasificacion_balotario"], "inestable")

    def test_los_sistemas_continuos_de_los_temas_4_y_5_siguen_siendo_integrables(self):
        """Lorenz (4.4) y Rossler (5.4) no son verificables, pero su campo si compila."""
        for identificador in ("4.4", "5.4", "5.5"):
            problema = _indice()[identificador]
            ecuacion = problema["ecuacion"]
            with self.subTest(problema=identificador):
                self.assertEqual(ecuacion["forma"], "sistema_primer_orden")
                solucion = resolver_edo(campo_desde_catalogo(ecuacion), [1.0, 1.0, 1.0],
                                        (0.0, 5.0), ecuacion["parametros"], puntos=200)
                self.assertTrue(solucion.success)


if __name__ == "__main__":
    unittest.main()
