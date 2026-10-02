"""
Pruebas de analisis_bifurcaciones.py (responsable: Tisnado Yarleque Christian David).

Qué se verifica
    1. Validación de la configuración (errores claros y estructurados).
    2. Formas normales de referencia contra sus resultados teóricos conocidos:
       silla-nodo, horquilla y Hopf.
    3. Honestidad de la evidencia: ningún candidato se marca como demostrado.
    4. Reproducibilidad: la configuración se conserva y el cálculo es determinista.
    5. Casos degenerados y modelos genéricos (logístico, Lorenz 3D).
    6. Utilidades (máximos locales, clasificación del comportamiento) y reporte.
    7. Conexión con server.py.

Ejecución (desde la carpeta del proyecto):
    python -m unittest discover -s tests_bifurcaciones -v
"""

import contextlib
import io
import math
import os
import sys
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from analisis_bifurcaciones import (  # noqa: E402
    FORMAS_NORMALES,
    analizar_bifurcaciones,
    buscar_equilibrios,
    clasificar_comportamiento,
    ejecutar_forma_normal,
    forma_horquilla,
    forma_silla_nodo,
    formatear_reporte_bifurcaciones,
    maximos_locales,
)
from modelos_referencia import modelo_logistico, modelo_lorenz  # noqa: E402

BASE = dict(parametros={"mu": 0.0}, parametro="mu", rango=(-1.0, 1.0), n_valores=11, region_busqueda=[(-3.0, 3.0)])


def con(**cambios):
    """Configuración válida de referencia con algunos campos cambiados."""
    return {**BASE, **cambios}


def estabilidades(rama):
    return {round(e["punto"][0], 6): e["estabilidad"] for e in rama["equilibrios"]}


def rama_cercana(res, mu):
    return min(res["ramas"], key=lambda r: abs(r["valor_parametro"] - mu))


# ---------------------------------------------------------------------------
# 1. Validación
# ---------------------------------------------------------------------------
class TestValidacion(unittest.TestCase):
    def assertError(self, res, razon):
        self.assertFalse(res["valid"], res)
        self.assertEqual(res["reason"], razon, res.get("message"))
        self.assertTrue(res["message"])
        self.assertFalse(res["can_continue"])

    def test_parametro_inexistente(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(parametro="zz")), "invalid_parameter")

    def test_parametro_no_numerico(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(parametros={"mu": "abc"})), "invalid_input")

    def test_parametro_no_finito(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(parametros={"mu": float("nan")})), "invalid_input")

    def test_modelo_que_no_usa_el_parametro(self):
        self.assertError(analizar_bifurcaciones(lambda t, y, p: [-y[0]], **BASE), "invalid_parameter")

    def test_rango_invertido(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(rango=(1.0, -1.0))), "invalid_range")

    def test_rango_con_infinito(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(rango=(0.0, float("inf")))), "invalid_input")

    def test_rango_mal_formado(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(rango=(1.0,))), "invalid_range")

    def test_pocos_valores(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(n_valores=2)), "invalid_range")

    def test_n_valores_no_entero(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(n_valores=5.5)), "invalid_range")

    def test_demasiados_valores(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(n_valores=10_000)), "invalid_range")

    def test_dimension_cuatro(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(region_busqueda=[(-1, 1)] * 4)), "invalid_dimension")

    def test_region_ausente(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(region_busqueda=None)), "invalid_input")

    def test_region_invertida(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(region_busqueda=[(3.0, -3.0)])), "invalid_input")

    def test_modelo_no_invocable(self):
        self.assertError(analizar_bifurcaciones("no soy funcion", **BASE), "invalid_input")

    def test_sistema_no_autonomo(self):
        self.assertError(analizar_bifurcaciones(lambda t, y, p: [p["mu"] * y[0] + t], **BASE), "non_autonomous_system")

    def test_modelo_con_dimension_incorrecta(self):
        self.assertError(analizar_bifurcaciones(lambda t, y, p: [p["mu"], 1.0], **BASE), "model_evaluation_error")

    def test_modelo_que_lanza_excepcion(self):
        def malo(t, y, p):
            raise RuntimeError("boom")
        self.assertError(analizar_bifurcaciones(malo, **BASE), "model_evaluation_error")

    def test_sin_equilibrios_en_toda_la_region(self):
        # x' = mu^2 + 1 > 0 siempre: ningún equilibrio -> resultado incompleto, no un éxito vacío.
        res = analizar_bifurcaciones(lambda t, y, p: [p["mu"] ** 2 + 1.0], **BASE)
        self.assertError(res, "incomplete_results")

    def test_dependencia_simetrica_del_parametro_es_valida(self):
        # F(mu=-1) == F(mu=+1): no debe confundirse con "el modelo no usa el parámetro".
        res = analizar_bifurcaciones(lambda t, y, p: [p["mu"] ** 2 - y[0] ** 2], **con(region_busqueda=[(-3, 3)]))
        self.assertTrue(res["valid"], res)

    def test_maximos_requieren_y0_e_intervalo(self):
        self.assertError(analizar_bifurcaciones(forma_horquilla, **con(calcular_maximos=True)), "invalid_input")

    def test_maximos_y0_dimension_incorrecta(self):
        res = analizar_bifurcaciones(forma_horquilla, **con(calcular_maximos=True, y0=[0.1, 0.2], intervalo=(0, 5)))
        self.assertError(res, "invalid_dimension")

    def test_maximos_variable_invalida(self):
        res = analizar_bifurcaciones(forma_horquilla, **con(calcular_maximos=True, y0=[0.1], intervalo=(0, 5),
                                                          variable_maximos=3))
        self.assertError(res, "invalid_input")

    def test_maximos_fraccion_transitorio_invalida(self):
        res = analizar_bifurcaciones(forma_horquilla, **con(calcular_maximos=True, y0=[0.1], intervalo=(0, 5),
                                                          fraccion_transitorio=1.0))
        self.assertError(res, "invalid_input")

    def test_caso_de_referencia_desconocido(self):
        res = ejecutar_forma_normal("no_existe")
        self.assertFalse(res["valid"])
        self.assertEqual(res["reason"], "unknown_case")

    def test_error_tambien_se_puede_formatear(self):
        res = analizar_bifurcaciones(forma_horquilla, **con(parametro="zz"))
        txt = formatear_reporte_bifurcaciones(res)
        self.assertIn("No se pudo completar", txt)


# ---------------------------------------------------------------------------
# 2. Formas normales
# ---------------------------------------------------------------------------
class TestSillaNodo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = ejecutar_forma_normal("silla_nodo")

    def test_resultado_valido(self):
        self.assertTrue(self.res["valid"])

    def test_sin_equilibrios_para_mu_negativo(self):
        for r in self.res["ramas"]:
            if r["valor_parametro"] < -1e-9:
                self.assertEqual(r["n_equilibrios"], 0, r["valor_parametro"])

    def test_dos_ramas_para_mu_positivo(self):
        for r in self.res["ramas"]:
            if r["valor_parametro"] > 1e-9:
                self.assertEqual(r["n_equilibrios"], 2, r["valor_parametro"])

    def test_posicion_y_estabilidad_de_las_ramas(self):
        r = rama_cercana(self.res, 1.0)
        raiz = math.sqrt(r["valor_parametro"])
        est = estabilidades(r)
        self.assertEqual(est[round(raiz, 6)], "estable")
        self.assertEqual(est[round(-raiz, 6)], "inestable")

    def test_un_candidato_que_contiene_mu_cero(self):
        cands = self.res["candidatos"]
        self.assertEqual(len(cands), 1)
        lo, hi = cands[0]["intervalo_refinado"]
        self.assertLessEqual(lo, 0.0 + 1e-9)
        self.assertGreaterEqual(hi, 0.0 - 1e-9)

    def test_tipo_sugerido_es_silla_nodo(self):
        self.assertIn("silla-nodo", self.res["candidatos"][0]["tipo_sugerido"])

    def test_contraste_con_teoria(self):
        v = self.res["verificacion_teorica"]
        self.assertLess(v["error_max_posicion_equilibrios"], 1e-8)
        self.assertTrue(v["mu_critico_dentro_de_un_candidato"])


class TestHorquilla(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = ejecutar_forma_normal("horquilla")

    def test_un_equilibrio_estable_para_mu_negativo(self):
        r = rama_cercana(self.res, -0.5)
        self.assertEqual(r["n_equilibrios"], 1)
        self.assertEqual(r["equilibrios"][0]["estabilidad"], "estable")

    def test_tres_equilibrios_para_mu_positivo(self):
        r = rama_cercana(self.res, 0.5)
        self.assertEqual(r["n_equilibrios"], 3)
        raiz = math.sqrt(r["valor_parametro"])
        est = estabilidades(r)
        self.assertEqual(est[0.0], "inestable")           # el origen pierde estabilidad
        self.assertEqual(est[round(raiz, 6)], "estable")   # dos ramas estables +-sqrt(mu)
        self.assertEqual(est[round(-raiz, 6)], "estable")

    def test_en_mu_cero_el_origen_es_no_concluyente(self):
        r = rama_cercana(self.res, 0.0)
        if abs(r["valor_parametro"]) < 1e-12:
            self.assertEqual(r["equilibrios"][0]["estabilidad"], "no concluyente")

    def test_candidato_contiene_mu_cero(self):
        cands = self.res["candidatos"]
        self.assertEqual(len(cands), 1)
        lo, hi = cands[0]["intervalo_refinado"]
        self.assertTrue(lo - 1e-9 <= 0.0 <= hi + 1e-9)
        self.assertIn("horquilla", cands[0]["tipo_sugerido"])

    def test_contraste_con_teoria(self):
        v = self.res["verificacion_teorica"]
        self.assertLess(v["error_max_posicion_equilibrios"], 1e-8)
        self.assertTrue(v["mu_critico_dentro_de_un_candidato"])


class TestHopf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = ejecutar_forma_normal("hopf")   # ~5 s: integra 12 trayectorias

    def test_el_origen_es_el_unico_equilibrio(self):
        for r in self.res["ramas"]:
            self.assertEqual(r["n_equilibrios"], 1)
            np.testing.assert_allclose(r["equilibrios"][0]["punto"], [0.0, 0.0], atol=1e-8)

    def test_cambio_de_estabilidad_del_origen(self):
        for r in self.res["ramas"]:
            est = r["equilibrios"][0]["estabilidad"]
            if r["valor_parametro"] < -1e-9:
                self.assertEqual(est, "estable")
            elif r["valor_parametro"] > 1e-9:
                self.assertEqual(est, "inestable")

    def test_candidato_hopf_en_mu_cero(self):
        cands = self.res["candidatos"]
        self.assertEqual(len(cands), 1)
        self.assertIn("Hopf", cands[0]["tipo_sugerido"])
        lo, hi = cands[0]["intervalo_refinado"]
        self.assertTrue(lo - 1e-9 <= 0.0 <= hi + 1e-9)

    def test_amplitud_del_ciclo_es_raiz_de_mu(self):
        filas = [f for f in self.res["verificacion_teorica"]["amplitud_ciclo"] if f["valor_parametro"] > 0.05]
        self.assertGreaterEqual(len(filas), 5)
        for f in filas:
            self.assertAlmostEqual(f["maximo_observado"], math.sqrt(f["valor_parametro"]), delta=1e-6)
            self.assertEqual(f["comportamiento"], "oscila (amplitud constante)")

    def test_mu_negativo_converge_sin_ciclo(self):
        for d in self.res["maximos"]["datos"]:
            if d["valor_parametro"] < -0.05:
                self.assertEqual(d["comportamiento"], "converge")
                self.assertEqual(d["maximos"], [])

    def test_configuracion_de_maximos_documentada(self):
        cfg = self.res["maximos"]["configuracion"]
        for clave in ("y0", "intervalo", "fraccion_transitorio", "tiempo_de_corte_transitorio", "metodo",
                      "rtol", "atol", "valores_usados"):
            self.assertIn(clave, cfg)
        self.assertEqual(self.res["maximos"]["fallos"], [])

    def test_diagrama_de_maximos_solo_con_tiempos_posteriores_al_transitorio(self):
        corte = self.res["maximos"]["configuracion"]["tiempo_de_corte_transitorio"]
        for d in self.res["maximos"]["datos"]:
            for t in d["tiempos"]:
                self.assertGreaterEqual(t, corte - 1e-6)


# ---------------------------------------------------------------------------
# 3. Honestidad de la evidencia
# ---------------------------------------------------------------------------
class TestHonestidad(unittest.TestCase):
    def test_ningun_candidato_se_declara_demostrado(self):
        for caso in FORMAS_NORMALES:
            if caso == "hopf":
                continue  # lento; la regla se prueba en los otros y en test_candidato_hopf
            res = ejecutar_forma_normal(caso)
            for c in res["candidatos"]:
                self.assertEqual(c["evidencia"], "numerica")
                self.assertIs(c["confirmado_matematicamente"], False)

    def test_reporte_advierte_que_son_indicios(self):
        txt = ejecutar_forma_normal("silla_nodo")["report"]
        self.assertIn("NO demostración", txt)
        self.assertIn("confirmado matemáticamente: NO", txt)
        self.assertIn("INDICIOS", txt)

    def test_contraste_teorico_solo_en_formas_normales(self):
        generico = analizar_bifurcaciones(modelo_logistico, {"r": 1.0, "K": 10.0}, "r", (-1, 1), 9, [(-1, 15)])
        self.assertIsNone(generico["verificacion_teorica"])
        self.assertIsNotNone(ejecutar_forma_normal("silla_nodo")["verificacion_teorica"])


# ---------------------------------------------------------------------------
# 4. Reproducibilidad
# ---------------------------------------------------------------------------
class TestReproducibilidad(unittest.TestCase):
    def test_config_conserva_lo_necesario(self):
        res = analizar_bifurcaciones(forma_silla_nodo, **con(n_valores=9))
        cfg = res["config"]
        self.assertEqual(cfg["parametro"], "mu")
        self.assertEqual(cfg["rango"], [-1.0, 1.0])
        self.assertEqual(cfg["n_valores"], 9)
        self.assertEqual(len(cfg["valores"]), 9)
        self.assertEqual(cfg["region_busqueda"], [[-3.0, 3.0]])
        for clave in ("tol_residuo", "tol_estabilidad", "tol_parametro", "parametros_base"):
            self.assertIn(clave, cfg)

    def test_dos_ejecuciones_dan_lo_mismo(self):
        a = analizar_bifurcaciones(forma_horquilla, **con(n_valores=15))
        b = analizar_bifurcaciones(forma_horquilla, **con(n_valores=15))
        self.assertEqual(a["candidatos"], b["candidatos"])
        self.assertEqual(a["diagrama_equilibrio"], b["diagrama_equilibrio"])
        self.assertEqual(a["config"], b["config"])

    def test_no_modifica_los_parametros_del_usuario(self):
        params = {"mu": 0.0}
        analizar_bifurcaciones(forma_horquilla, parametros=params, parametro="mu", rango=(-1, 1), n_valores=7,
                               region_busqueda=[(-3, 3)])
        self.assertEqual(params, {"mu": 0.0})

    def test_refinar_la_rejilla_no_cambia_el_valor_critico(self):
        for n in (7, 21, 41):
            c = analizar_bifurcaciones(forma_silla_nodo, **con(n_valores=n))["candidatos"]
            self.assertEqual(len(c), 1, n)
            lo, hi = c[0]["intervalo_refinado"]
            self.assertTrue(lo - 1e-9 <= 0.0 <= hi + 1e-9, n)

    def test_diagrama_de_equilibrio_es_consistente_con_las_ramas(self):
        res = ejecutar_forma_normal("silla_nodo")
        total = sum(r["n_equilibrios"] for r in res["ramas"])
        self.assertEqual(len(res["diagrama_equilibrio"]), total)
        for fila in res["diagrama_equilibrio"]:
            self.assertEqual(set(fila), {"valor_parametro", "punto", "estabilidad"})


# ---------------------------------------------------------------------------
# 5. Degenerados y modelos genéricos
# ---------------------------------------------------------------------------
class TestGenericosYDegenerados(unittest.TestCase):
    def test_logistico_transcritica_en_r_cero(self):
        res = analizar_bifurcaciones(modelo_logistico, {"r": 1.0, "K": 10.0}, "r", (-1, 1), 9, [(-1, 15)])
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["candidatos"]), 1)
        lo, hi = res["candidatos"][0]["intervalo_refinado"]
        self.assertTrue(lo - 1e-6 <= 0.0 <= hi + 1e-6)
        neg, pos = estabilidades(rama_cercana(res, -0.5)), estabilidades(rama_cercana(res, 0.5))
        self.assertEqual((neg[0.0], neg[10.0]), ("estable", "inestable"))
        self.assertEqual((pos[0.0], pos[10.0]), ("inestable", "estable"))

    def test_f_identicamente_cero_se_marca_como_continuo(self):
        # F = r*x*(1 - x/K) es 0 en todo x cuando r = 0: no hay equilibrios aislados.
        res = analizar_bifurcaciones(modelo_logistico, {"r": 1.0, "K": 10.0}, "r", (-1, 1), 9, [(-1, 15)])
        r0 = rama_cercana(res, 0.0)
        self.assertTrue(r0["continuo"])
        self.assertEqual(r0["n_equilibrios"], 0)
        self.assertIn("continuo", res["report"])
        self.assertTrue(any("continuo" in a for a in res["advertencias"]))

    def test_lorenz_horquilla_en_rho_uno(self):
        res = analizar_bifurcaciones(modelo_lorenz, {"sigma": 10.0, "rho": 0.5, "beta": 8.0 / 3.0}, "rho",
                                     (0.5, 3.0), 6, [(-10, 10), (-10, 10), (-5, 10)])
        self.assertTrue(res["valid"])
        self.assertEqual(rama_cercana(res, 0.5)["n_equilibrios"], 1)
        r2 = rama_cercana(res, 2.0)
        self.assertEqual(r2["n_equilibrios"], 3)
        c = math.sqrt((8.0 / 3.0) * (2.0 - 1.0))   # equilibrios C+- = (+-c, +-c, rho-1)
        puntos = sorted(tuple(np.round(e["punto"], 5)) for e in r2["equilibrios"])
        esperados = sorted([(-c, -c, 1.0), (0.0, 0.0, 0.0), (c, c, 1.0)])
        np.testing.assert_allclose(puntos, np.round(esperados, 5), atol=1e-4)
        lo, hi = res["candidatos"][0]["intervalo_refinado"]
        self.assertTrue(lo - 1e-6 <= 1.0 <= hi + 1e-6)

    def test_buscar_equilibrios_2d(self):
        # x' = x - y, y' = x + y - 2  -> unico equilibrio (2, 2)? resolver: x=y, 2x-2=... x' = 0 => x=y ; y'=2x-2=0 => x=1
        eqs = buscar_equilibrios(lambda t, y, p: [y[0] - y[1], y[0] + y[1] - 2.0], {}, [(-5, 5), (-5, 5)])
        self.assertEqual(len(eqs), 1)
        np.testing.assert_allclose(eqs[0], [1.0, 1.0], atol=1e-8)

    def test_buscar_equilibrios_1d_multiples(self):
        eqs = buscar_equilibrios(lambda t, y, p: [y[0] ** 3 - y[0]], {}, [(-2, 2)])
        np.testing.assert_allclose(sorted(e[0] for e in eqs), [-1.0, 0.0, 1.0], atol=1e-8)


# ---------------------------------------------------------------------------
# 6. Utilidades y reporte
# ---------------------------------------------------------------------------
class TestUtilidades(unittest.TestCase):
    def test_maximos_locales_de_seno(self):
        t = np.linspace(0, 6 * math.pi, 3000)
        pares = maximos_locales(t, np.sin(t))
        self.assertEqual(len(pares), 3)
        for k, (tm, ym) in enumerate(pares):
            self.assertAlmostEqual(tm, math.pi / 2 + 2 * math.pi * k, delta=2e-3)
            self.assertAlmostEqual(ym, 1.0, delta=1e-6)

    def test_maximos_locales_serie_monotona_no_tiene(self):
        t = np.linspace(0, 1, 50)
        self.assertEqual(maximos_locales(t, t), [])

    def test_clasificar_comportamiento(self):
        t = np.linspace(0, 60, 6000)
        self.assertEqual(clasificar_comportamiento(np.full(10, 2.0), [], 1e-6), "converge")
        s = np.sin(t)
        self.assertEqual(clasificar_comportamiento(s, [m for _, m in maximos_locales(t, s)], 1e-6),
                         "oscila (amplitud constante)")
        d = np.exp(-0.05 * t) * np.sin(t)
        self.assertEqual(clasificar_comportamiento(d, [m for _, m in maximos_locales(t, d)], 1e-6),
                         "amplitud decreciente")
        g = np.exp(0.05 * t) * np.sin(t)
        self.assertEqual(clasificar_comportamiento(g, [m for _, m in maximos_locales(t, g)], 1e-6), "otro")

    def test_reporte_se_puede_imprimir_en_consola_windows(self):
        for caso in ("silla_nodo", "horquilla"):
            ejecutar_forma_normal(caso)["report"].encode("cp1252")   # sin UnicodeEncodeError

    def test_reporte_tiene_secciones_y_no_se_desborda(self):
        txt = ejecutar_forma_normal("silla_nodo")["report"]
        for frag in ("ANÁLISIS DE BIFURCACIONES", "CONFIGURACIÓN", "RAMAS DE EQUILIBRIO", "CANDIDATOS A BIFURCACIÓN",
                     "CONTRASTE CON LA TEORÍA", "ADVERTENCIAS Y LIMITACIONES"):
            self.assertIn(frag, txt)
        self.assertLessEqual(max(len(l) for l in txt.splitlines()), 100)

    def test_tabla_larga_se_acota(self):
        res = analizar_bifurcaciones(forma_silla_nodo, **con(n_valores=200))
        filas = [l for l in res["report"].splitlines() if l.startswith("  ") and l[2:3] in "+-" and "(" in l]
        self.assertLess(len(filas), 60)
        self.assertIn("se muestran", res["report"])


# ---------------------------------------------------------------------------
# 7. Conexión con server.py
# ---------------------------------------------------------------------------
class TestConexionServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import server
        except ImportError as exc:
            raise unittest.SkipTest(f"No se pudo importar server.py: {exc}")
        cls.server = server

    def test_server_despacha_bifurcaciones(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = self.server.ejecutar_bifurcaciones("silla_nodo")
        self.assertTrue(res["valid"])
        self.assertIn("ANÁLISIS DE BIFURCACIONES", buf.getvalue())

    def test_server_no_depende_de_playground(self):
        with open(self.server.__file__, encoding="utf-8") as f:
            self.assertNotIn("playground", f.read())


if __name__ == "__main__":
    unittest.main()
