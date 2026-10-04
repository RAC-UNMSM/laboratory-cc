"""Pruebas del informe de sesión: lo que el usuario abre para ver su trabajo.

Lo que aquí se cubre es justamente lo que puede romperse sin que nadie se
entere, porque el informe no viaja en la respuesta de la herramienta:

* que los análisis se **acumulen** en un solo documento y en orden,
* que la dirección **no cambie** entre llamadas, que es lo que permite dejar
  la pestaña abierta,
* que la plantilla y los datos viajen **separados**: el `.html` no lleva nada
  del problema y el JSON no lleva nada de diseño,
* que el JSON no pueda escaparse de su `<script>`, que es la única vía de
  inyección que queda cuando el render es del navegador,
* que un análisis fallido también aparezca, en vez de desaparecer del relato.
"""

import json
import os
import re
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta

from orquestacion import capacidades, servidor_local
from orquestacion import informe as informe_mod
from orquestacion.informe import InformeDeSesion
from visualizacion.plantilla import PLANTILLA, documento

PENDULO = {"ecuaciones": ["v", "-sin(theta)-0.1*v"],
           "variables_estado": ["theta", "v"],
           "intervalo": [0, 10], "y0": [2.0, 0.0], "titulo": "Péndulo"}
LOGISTICO = {"ecuaciones": ["r*y*(1-y/K)"], "variables_estado": ["y"],
             "intervalo": [0, 8], "y0": [0.5],
             "parametros": {"r": 1.2, "K": 4.0}, "titulo": "Logístico"}


def _payload(html):
    """El JSON que la plantilla lleva dentro, tal como lo leerá el navegador."""
    crudo = re.search(r'<script type="application/json" id="datos">(.*?)</script>',
                      html, re.S).group(1)
    # La plantilla escapa `<` como < para no poder cerrar su propio
    # <script>; JSON.parse lo deshace, y json.loads también.
    return json.loads(crudo)


class TestSeparacionPlantillaDatos(unittest.TestCase):
    """La plantilla es un .html de verdad y no sabe nada del problema."""

    def test_la_plantilla_existe_como_archivo_html(self):
        self.assertTrue(PLANTILLA.is_file())
        self.assertEqual(PLANTILLA.suffix, ".html")

    def test_la_plantilla_no_contiene_datos_de_ningun_problema(self):
        texto = PLANTILLA.read_text(encoding="utf-8")
        self.assertIn('<script type="application/json" id="datos">', texto)
        self.assertNotIn("Péndulo", texto)
        self.assertNotIn("equilibrio", texto.split("<style>")[0])

    def test_el_modulo_python_no_contiene_etiquetas_html(self):
        """Si vuelve a aparecer HTML aquí, la separación se está deshaciendo."""
        fuente = (Path(PLANTILLA).resolve().parents[1] / "plantilla.py").read_text(
            encoding="utf-8")
        cuerpo = fuente.split('"""', 2)[2]          # sin el docstring del módulo
        self.assertNotRegex(cuerpo, r"<(div|section|table|h1|h2|p|span)")


class TestPayloadDelDocumento(unittest.TestCase):
    """Lo que viaja a la página: un JSON, no marcado ya armado."""

    def test_documento_vacio_trae_lista_vacia(self):
        datos = _payload(documento([]))
        self.assertEqual(datos["entradas"], [])
        self.assertEqual(datos["refresco"], 15)

    def test_refresco_cero_queda_fijo(self):
        self.assertEqual(_payload(documento([], refresco=0))["refresco"], 0)

    def test_el_titulo_del_cliente_no_puede_cerrar_el_script(self):
        hostil = "</script><img src=x onerror=alert(1)>"
        html = documento([{"titulo": hostil, "ok": True}])
        # Ni la etiqueta de cierre ni el marcado sobreviven como HTML...
        self.assertNotIn("</script><img", html)
        self.assertNotIn("<img src=x", html)
        # ...pero el dato sigue intacto para quien lo lea como JSON.
        self.assertEqual(_payload(html)["entradas"][0]["titulo"], hostil)

    def test_un_analisis_fallido_viaja_con_su_etapa(self):
        datos = _payload(documento([{"titulo": "Explota", "ok": False,
                                     "etapa": "resolucion",
                                     "error": "la solución diverge"}]))
        entrada = datos["entradas"][0]
        self.assertFalse(entrada["ok"])
        self.assertEqual(entrada["etapa"], "resolucion")

    def test_los_datos_viajan_en_orden_cronologico(self):
        """El JSON va en el orden en que se preguntó; la página lo invierte al pintar.

        Son dos cosas distintas y conviene no confundirlas: el dato conserva la
        cronología (el análisis 1 es el primero que se pidió, y su número no
        cambia nunca), y la presentación pone lo último arriba. Invertir aquí
        rompería la numeración de las secciones que el usuario ya tiene abiertas.
        """
        datos = _payload(documento([{"titulo": "uno"}, {"titulo": "dos"},
                                    {"titulo": "tres"}]))
        self.assertEqual([e["titulo"] for e in datos["entradas"]],
                         ["uno", "dos", "tres"])

    def test_la_pagina_pinta_lo_ultimo_arriba(self):
        """Al abrir el informe lo primero que se ve es la última pregunta."""
        pagina = PLANTILLA.read_text(encoding="utf-8")
        bucle = pagina.split("for (var i = dibujadas;")[1].split("}")[0]
        self.assertIn("contenedor.insertBefore(art, contenedor.firstChild)", bucle)
        self.assertNotIn("contenedor.appendChild(art)", bucle)
        # La numeración sigue siendo cronológica: el primero preguntado es el 1.
        self.assertIn("construirAnalisis(entradas[i], i + 1)", bucle)

    def test_el_indice_lateral_sigue_el_mismo_orden_que_el_cuerpo(self):
        pagina = PLANTILLA.read_text(encoding="utf-8")
        indice = pagina.split("function anotarIndice")[1].split('\\n  }')[0]
        self.assertIn("lista.insertBefore(li, lista.firstChild)", indice)


class TestAcumulacionDeLaSesion(unittest.TestCase):
    """El modo "acumula": varios análisis, un documento, una sola dirección.

    No es el de por defecto. Se usa cuando las respuestas se comparan entre sí:
    mientras el barrido paramétrico siga pendiente, estudiar una bifurcación es
    llamar varias veces variando el parámetro, y la bifurcación se ve al poner
    esas llamadas una junto a otra.
    """

    def setUp(self):
        self.directorio = Path(__file__).resolve().parent / "_informes_de_prueba"
        self.sesion = InformeDeSesion("prueba")
        # Sin storage y escribiendo en una carpeta propia, para no tocar la del
        # proyecto ni depender de la red.
        self.parches = [
            mock.patch("orquestacion.informe.CARPETA_LOCAL", self.directorio),
            mock.patch("orquestacion.informe.storage.subir_html", return_value=None),
            mock.patch.object(capacidades, "SESION", self.sesion),
            # Sin servidor http, el destino es la ruta del archivo y estas
            # pruebas pueden leerlo directamente.
            mock.patch.dict(os.environ, {"EDOS_SIN_SERVIDOR_LOCAL": "1"}),
            mock.patch.object(informe_mod, "ACUMULA", True),
        ]
        for parche in self.parches:
            parche.start()

    def tearDown(self):
        for parche in self.parches:
            parche.stop()
        for archivo in list(self.directorio.glob("*.html")) + list(
                self.directorio.glob("*.json")):
            archivo.unlink()
        if self.directorio.exists():
            self.directorio.rmdir()

    def _html(self):
        return Path(self.sesion.destino).read_text(encoding="utf-8")

    def _entradas(self):
        return _payload(self._html())["entradas"]

    def test_los_analisis_se_acumulan_en_orden(self):
        capacidades.analizar_edo(PENDULO)
        capacidades.analizar_edo(LOGISTICO)
        capacidades.analizar_equilibrios_sistema(
            {"ecuaciones": ["mu - x**2"], "variables_estado": ["x"],
             "parametros": {"mu": 0.5}})

        estado = self.sesion.estado()
        self.assertEqual(estado["analisis_registrados"], 3)
        self.assertEqual(estado["titulos"],
                         ["Péndulo", "Logístico", "Equilibrios y estabilidad"])
        entradas = self._entradas()
        self.assertEqual(len(entradas), 3)
        self.assertEqual([e["titulo"] for e in entradas],
                         ["Péndulo", "Logístico", "Equilibrios y estabilidad"])

    def test_el_html_no_viaja_en_la_respuesta_si_hay_informe(self):
        """Ocupaba el 75 % de la respuesta y el modelo no puede dibujarlo.

        Medido sobre un Van der Pol: 85 KB de los 114 KB totales eran el
        documento HTML, unos 23 mil tokens que no servían para que el usuario
        viera nada y que competían con el enlace que sí funciona.
        """
        resultado = capacidades.analizar_edo(PENDULO)
        visualizacion = resultado["visualizacion"]
        self.assertNotIn("html", visualizacion)
        self.assertIn("informe", visualizacion)
        # Lo que el modelo sí usa para redactar se conserva.
        self.assertIn("figuras", visualizacion)
        self.assertIn(visualizacion["informe"], resultado["notas"][-1])

    def test_sin_informe_el_html_sigue_viajando(self):
        """Si el informe no se pudo publicar, la figura no se pierde."""
        with mock.patch.object(Path, "write_text", side_effect=OSError("disco lleno")):
            visualizacion = capacidades.analizar_edo(PENDULO)["visualizacion"]
        self.assertIsNone(visualizacion.get("informe"))
        self.assertIn("html", visualizacion)

    def test_la_direccion_no_cambia_entre_llamadas(self):
        primera = capacidades.analizar_edo(PENDULO)["visualizacion"]["informe"]
        segunda = capacidades.analizar_edo(LOGISTICO)["visualizacion"]["informe"]
        self.assertEqual(primera, segunda)

    def test_plotly_se_carga_una_sola_vez_y_las_figuras_van_como_datos(self):
        """La librería la trae la plantilla; cada figura viaja como spec, no como div.

        Antes cada figura llegaba con su `<div>` ya renderizado y la librería
        incrustada en el primero. Eso obligaba a que el servidor supiera en qué
        bloque meterla, y un segundo `<script>` de plotly rompe las gráficas.
        """
        capacidades.analizar_edo(PENDULO)
        capacidades.analizar_edo(LOGISTICO)
        html = self._html()
        self.assertEqual(html.count("cdn.jsdelivr.net/npm/plotly"), 1)

        figuras = [f for e in self._entradas() for f in e.get("figuras", [])]
        self.assertEqual([f["nombre"] for f in figuras],
                         ["series", "plano_fase", "series", "linea_fase"])
        for figura in figuras:
            self.assertIn("data", figura["spec"])
            self.assertIn("layout", figura["spec"])

    def test_un_analisis_que_no_pasa_la_verificacion_igual_se_registra(self):
        # Un umbral imposible fuerza el fallo sin inventar un sistema roto.
        with mock.patch("orquestacion.capacidades.verificar",
                        return_value={"ok": False, "pruebas": [], "fallidas": ["residuo"],
                                      "resumen": "No se superaron: residuo."}):
            resultado = capacidades.analizar_edo(PENDULO)
        self.assertFalse(resultado["ok"])
        self.assertEqual(self.sesion.estado()["analisis_registrados"], 1)
        self.assertFalse(self._entradas()[0]["ok"])
        self.assertEqual(self._entradas()[0]["etapa"], "verificacion")

    def test_el_informe_se_puede_publicar_vacio(self):
        destino = self.sesion.asegurar_publicado()
        self.assertTrue(Path(destino).exists())
        self.assertEqual(self._entradas(), [])

    def test_un_chat_nuevo_empieza_de_cero(self):
        """El servidor sobrevive entre conversaciones; el informe no debe."""
        capacidades.analizar_edo(PENDULO)
        anterior = self.sesion.id
        self.sesion.empezar_de_nuevo()
        self.assertNotEqual(self.sesion.id, anterior)
        self.assertEqual(self.sesion.estado()["analisis_registrados"], 0)

        capacidades.analizar_edo(LOGISTICO)
        self.assertEqual(self.sesion.estado()["titulos"], ["Logístico"])

    def test_el_informe_anterior_no_se_borra(self):
        """Empezar de cero no es perder lo de antes: queda su archivo fechado."""
        capacidades.analizar_edo(PENDULO)
        anterior = self.sesion.id
        self.sesion.empezar_de_nuevo()
        capacidades.analizar_edo(LOGISTICO)
        nombres = sorted(p.name for p in self.directorio.glob("*.html"))
        self.assertIn(f"informe-{anterior}.html", nombres)
        self.assertIn(f"informe-{self.sesion.id}.html", nombres)

    def test_tras_mucho_silencio_se_releva_solo(self):
        """Red de seguridad para cuando el agente no llame a `nuevo_informe`."""
        capacidades.analizar_edo(PENDULO)
        anterior = self.sesion.id
        self.sesion._ultimo_uso = datetime.now() - timedelta(
            minutes=informe_mod.MINUTOS_DE_INACTIVIDAD + 1)
        capacidades.analizar_edo(LOGISTICO)
        self.assertNotEqual(self.sesion.id, anterior)
        self.assertEqual(self.sesion.estado()["titulos"], ["Logístico"])

    def test_una_pausa_corta_no_parte_la_conversacion(self):
        """Pensar un rato entre dos preguntas no es empezar otro chat."""
        capacidades.analizar_edo(PENDULO)
        anterior = self.sesion.id
        self.sesion._ultimo_uso = datetime.now() - timedelta(
            minutes=informe_mod.MINUTOS_DE_INACTIVIDAD - 1)
        capacidades.analizar_edo(LOGISTICO)
        self.assertEqual(self.sesion.id, anterior)
        self.assertEqual(len(self.sesion.entradas), 2)

    def test_no_crece_sin_limite(self):
        with mock.patch("orquestacion.informe.MAXIMO_ENTRADAS", 2):
            for _ in range(4):
                self.sesion.registrar({"titulo": "x", "ok": True})
        self.assertEqual(self.sesion.estado()["analisis_registrados"], 2)

    def test_un_fallo_al_publicar_no_tumba_el_analisis(self):
        with mock.patch.object(Path, "write_text", side_effect=OSError("disco lleno")):
            resultado = capacidades.analizar_edo(PENDULO)
        self.assertTrue(resultado["ok"])
        self.assertIsNone(resultado["visualizacion"].get("informe"))


class TestModoUltimo(unittest.TestCase):
    """El modo por defecto: el informe enseña UNA cosa, la recién preguntada."""

    def setUp(self):
        self.directorio = Path(__file__).resolve().parent / "_informes_ultimo"
        self.sesion = InformeDeSesion()
        self.parches = [
            mock.patch("orquestacion.informe.CARPETA_LOCAL", self.directorio),
            mock.patch("orquestacion.informe.storage.subir_html", return_value=None),
            mock.patch.object(capacidades, "SESION", self.sesion),
            mock.patch.dict(os.environ, {"EDOS_SIN_SERVIDOR_LOCAL": "1"}),
            mock.patch.object(informe_mod, "ACUMULA", False),
        ]
        for parche in self.parches:
            parche.start()

    def tearDown(self):
        for parche in self.parches:
            parche.stop()
        for archivo in self.directorio.glob("*"):
            archivo.unlink()
        if self.directorio.exists():
            self.directorio.rmdir()

    def test_cada_pregunta_reemplaza_a_la_anterior(self):
        capacidades.analizar_edo(PENDULO)
        capacidades.analizar_edo(LOGISTICO)
        self.assertEqual(self.sesion.estado()["titulos"], ["Logístico"])

    def test_el_documento_muestra_solo_la_ultima(self):
        capacidades.analizar_edo(PENDULO)
        capacidades.analizar_edo(LOGISTICO)
        entradas = _payload(Path(self.sesion.destino).read_text(encoding="utf-8"))["entradas"]
        self.assertEqual(len(entradas), 1)
        self.assertEqual(entradas[0]["titulo"], "Logístico")

    def test_la_direccion_no_cambia_al_preguntar_de_nuevo(self):
        """Una pestaña abierta sigue valiendo pregunta tras pregunta."""
        primera = capacidades.analizar_edo(PENDULO)["visualizacion"]["informe"]
        segunda = capacidades.analizar_edo(LOGISTICO)["visualizacion"]["informe"]
        self.assertEqual(primera, segunda)

    def test_sin_historial_no_hay_nada_que_relevar(self):
        """El relevo por inactividad sobra aquí: no hay historial que arrastrar."""
        capacidades.analizar_edo(PENDULO)
        anterior = self.sesion.id
        self.sesion._ultimo_uso = datetime.now() - timedelta(
            minutes=informe_mod.MINUTOS_DE_INACTIVIDAD + 60)
        capacidades.analizar_edo(LOGISTICO)
        self.assertEqual(self.sesion.id, anterior)
        self.assertEqual(self.sesion.estado()["titulos"], ["Logístico"])


class TestEnlaceYNombre(unittest.TestCase):
    """El informe tiene que poder abrirse con un clic, y llamarse algo legible."""

    def setUp(self):
        self.directorio = Path(__file__).resolve().parent / "_informes_enlace"
        self.sesion = InformeDeSesion()
        servidor_local.reiniciar()
        self.parches = [
            mock.patch("orquestacion.informe.CARPETA_LOCAL", self.directorio),
            mock.patch("orquestacion.informe.storage.subir_html", return_value=None),
        ]
        for parche in self.parches:
            parche.start()

    def tearDown(self):
        for parche in self.parches:
            parche.stop()
        for archivo in self.directorio.glob("*"):
            archivo.unlink()
        if self.directorio.exists():
            self.directorio.rmdir()

    def test_el_nombre_lleva_fecha_y_hora(self):
        """`informe-a3f91b2c4d5e` no decía nada ni se podía ordenar."""
        self.assertRegex(self.sesion.id, r"^\d{8}-\d{4}-[0-9a-f]{4}$")

    def test_sin_storage_el_destino_es_un_enlace_http_que_responde(self):
        destino = self.sesion.asegurar_publicado()
        self.assertTrue(destino.startswith("http://127.0.0.1:"), destino)
        with urllib.request.urlopen(destino, timeout=5) as respuesta:
            self.assertEqual(respuesta.status, 200)
            self.assertIn("no-store", respuesta.headers.get("Cache-Control", ""))
            self.assertIn("<!doctype html>", respuesta.read().decode("utf-8"))

    def test_el_json_se_sirve_al_lado_y_como_json(self):
        """Es lo que permite que la página se actualice sin recargarse."""
        destino = self.sesion.asegurar_publicado()
        self.sesion.registrar({"titulo": "Van der Pol", "ok": True})
        url = destino.rsplit("/", 1)[0] + "/" + self.sesion._nombre("json")
        with urllib.request.urlopen(url, timeout=5) as respuesta:
            self.assertIn("application/json", respuesta.headers.get("Content-Type", ""))
            datos = json.loads(respuesta.read().decode("utf-8"))
        self.assertEqual([e["titulo"] for e in datos["entradas"]], ["Van der Pol"])

    def test_se_puede_apagar_y_entonces_vuelve_la_ruta(self):
        with mock.patch.dict(os.environ, {"EDOS_SIN_SERVIDOR_LOCAL": "1"}):
            servidor_local.reiniciar()
            destino = self.sesion.asegurar_publicado()
        self.assertTrue(Path(destino).is_file(), destino)

    def test_el_servidor_solo_escucha_en_loopback(self):
        """Abrirlo a la red convertiría esto en una carpeta compartida sin clave."""
        self.assertEqual(servidor_local.INTERFAZ, "127.0.0.1")
        self.assertTrue(self.sesion.asegurar_publicado().startswith("http://127.0.0.1:"))


if __name__ == "__main__":
    unittest.main()
