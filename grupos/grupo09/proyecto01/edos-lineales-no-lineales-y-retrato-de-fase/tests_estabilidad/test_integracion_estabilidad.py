"""
Pruebas de la INTEGRACIÓN de analisis_estabilidad.py en el proyecto del grupo.

Complementan a test_analisis_estabilidad.py (que prueba la matemática simbólica)
y cubren: contrato numérico del grupo (jacobiano / analizar_equilibrios),
adaptador de modelos de referencia, formato de consola y conexión con server.py.

Ejecución (desde la carpeta del proyecto):
    python -m unittest discover -s tests_estabilidad -v
"""

import contextlib
import io
import os
import sys
import unittest

os.environ.setdefault("MPLBACKEND", "Agg")  # server.py importa matplotlib; evita abrir ventanas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from analisis_estabilidad import (  # noqa: E402
    analizar_equilibrios,
    analizar_estabilidad,
    analizar_estabilidad_referencia,
    formatear_equilibrios_numericos,
    formatear_reporte_estabilidad,
    jacobiano,
)
from modelos_referencia import modelo_logistico  # noqa: E402


def _resta(t, y, p):
    """x' = -a x (1D) para probar el contrato numérico."""
    return [-p["a"] * y[0]]


def _centro(t, y, p):
    """x' = -y, y' = x (autovalores imaginarios puros)."""
    return [-y[1], y[0]]


class TestContratoNumerico(unittest.TestCase):
    def test_jacobiano_lineal_es_exacto(self):
        j = jacobiano(_resta, [0.7], {"a": 3.0})
        self.assertEqual(j.shape, (1, 1))
        self.assertAlmostEqual(j[0, 0], -3.0, places=6)

    def test_jacobiano_2d(self):
        j = jacobiano(_centro, [0.3, -0.2])
        np.testing.assert_allclose(j, [[0, -1], [1, 0]], atol=1e-6)

    def test_modelo_con_dimension_incorrecta_falla(self):
        with self.assertRaises(ValueError):
            jacobiano(lambda t, y, p: [0.0, 0.0], [1.0])

    def test_logistico_clasificacion(self):
        res = analizar_equilibrios(modelo_logistico, [[0.0], [10.0]], {"r": 1.0, "K": 10.0})
        self.assertEqual(res[0]["clasificacion"], "inestable")
        self.assertEqual(res[1]["clasificacion"], "estable")

    def test_centro_es_no_concluyente(self):
        res = analizar_equilibrios(_centro, [[0.0, 0.0]])
        self.assertTrue(res[0]["clasificacion"].startswith("no concluyente"))

    def test_clave_de_resultado_se_conserva(self):
        # server.py y analisis_bifurcaciones.py dependen de estas claves.
        r = analizar_equilibrios(_resta, [[0.0]], {"a": 1.0})[0]
        for clave in ("equilibrio", "jacobiano", "autovalores", "clasificacion"):
            self.assertIn(clave, r)


class TestAdaptadorReferencia(unittest.TestCase):
    def test_logistico_equilibrios_y_estabilidad(self):
        r = analizar_estabilidad_referencia("logistico", {"r": 2.0, "K": 5.0})
        self.assertTrue(r["valid"])
        estab = {tuple(str(v) for v in e["point"]): e["classification"]["stability"] for e in r["equilibria"]}
        self.assertEqual(estab[("0",)], "unstable")
        self.assertEqual(estab[("5",)], "local_asymptotically_stable")

    def test_lineal(self):
        r = analizar_estabilidad_referencia("lineal")
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["equilibria"]), 1)
        self.assertEqual(r["equilibria"][0]["classification"]["stability"], "local_asymptotically_stable")

    def test_lorenz_tiene_tres_equilibrios_inestables(self):
        r = analizar_estabilidad_referencia("lorenz")
        self.assertTrue(r["valid"])
        self.assertEqual(len(r["equilibria"]), 3)
        for e in r["equilibria"]:
            self.assertEqual(e["classification"]["stability"], "unstable")

    def test_lorenz_rho_bajo_origen_estable(self):
        r = analizar_estabilidad_referencia("lorenz", {"rho": 0.5})
        self.assertEqual(len(r["equilibria"]), 1)
        self.assertEqual(r["equilibria"][0]["classification"]["stability"], "local_asymptotically_stable")

    def test_modelo_desconocido_devuelve_error_estructurado(self):
        r = analizar_estabilidad_referencia("no_existe")
        self.assertFalse(r["valid"])
        self.assertEqual(r["reason"], "invalid_input")


class TestReporteConsola(unittest.TestCase):
    CASOS = [
        {"variables": ["x"], "equations": ["mu*x - x**3"]},
        {"variables": ["x", "y"], "equations": ["-y", "x"]},
        {"variables": ["x", "y"], "equations": ["x", "-y"]},
    ]

    def test_reporte_tiene_secciones_clave(self):
        txt = formatear_reporte_estabilidad(analizar_estabilidad(self.CASOS[2]))
        for frag in ("ANÁLISIS DE ESTABILIDAD LOCAL", "Equilibrio 1 de 1", "Jacobiano", "Autovalores",
                     "RESULTADO", "RESUMEN", "punto silla"):
            self.assertIn(frag, txt)

    def test_reporte_se_puede_imprimir_en_consola_windows(self):
        # cp1252 es la codificación típica de consolas de Windows en español.
        for caso in self.CASOS:
            txt = formatear_reporte_estabilidad(analizar_estabilidad(caso))
            txt.encode("cp1252")  # no debe lanzar UnicodeEncodeError

    def test_reporte_de_error_explica_el_motivo(self):
        txt = formatear_reporte_estabilidad(analizar_estabilidad({"variables": ["x"], "equations": ["x + t"]}))
        self.assertIn("No se pudo completar", txt)
        self.assertIn("Motivo", txt)

    def test_parametro_libre_no_aparece_como_re(self):
        txt = formatear_reporte_estabilidad(analizar_estabilidad(self.CASOS[0]))
        self.assertNotIn("re(mu)", txt)
        self.assertIn("mu", txt)
        self.assertIn("NO CONCLUYENTE", txt)  # el signo depende de mu: no se inventa un valor

    def test_condicion_parametrica_para_horquilla(self):
        r = analizar_estabilidad(self.CASOS[0])
        origen = [e for e in r["equilibria"] if str(e["point"][0]) == "0"][0]
        condiciones = origen["classification"]["parametric_conditions"]
        self.assertTrue(condiciones)
        self.assertIn("mu", condiciones[0])

    def test_centro_se_informa_como_no_concluyente(self):
        txt = formatear_reporte_estabilidad(analizar_estabilidad(self.CASOS[1]))
        self.assertIn("NO CONCLUYENTE", txt)

    def test_lineas_de_texto_no_se_desbordan(self):
        txt = formatear_reporte_estabilidad(analizar_estabilidad(self.CASOS[0]))
        self.assertLessEqual(max(len(l) for l in txt.splitlines()), 90)

    def test_tabla_numerica(self):
        res = analizar_equilibrios(modelo_logistico, [[0.0], [10.0]], {"r": 1.0, "K": 10.0})
        txt = formatear_equilibrios_numericos(res)
        self.assertIn("INESTABLE", txt)
        self.assertIn("ESTABLE", txt)
        self.assertEqual(formatear_equilibrios_numericos([]), "No hay equilibrios para analizar.")


class TestConexionServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import server
        except ImportError as exc:  # dependencia de otro módulo (p. ej. matplotlib)
            raise unittest.SkipTest(f"No se pudo importar server.py: {exc}")
        cls.server = server

    def test_server_despacha_estabilidad(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.server.ejecutar_estabilidad("logistico")
        self.assertIn("ANÁLISIS DE ESTABILIDAD LOCAL", buf.getvalue())

    def test_server_no_depende_de_playground(self):
        ruta = os.path.join(os.path.dirname(self.server.__file__), "server.py")
        with open(ruta, encoding="utf-8") as f:
            self.assertNotIn("playground", f.read())


if __name__ == "__main__":
    unittest.main()
