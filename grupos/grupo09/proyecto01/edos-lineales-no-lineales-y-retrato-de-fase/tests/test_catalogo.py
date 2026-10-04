"""Pruebas de consistencia del catálogo; no verifican matemática."""

import json
from pathlib import Path
import tempfile
import unittest

from orquestacion.catalogo import cargar_catalogo


class CatalogoTests(unittest.TestCase):
    def test_sin_ejercicios_inventados(self):
        """Cada problema del catálogo debe existir en el .tex del balotario.

        Antes este test exigía que el catálogo estuviera vacío, porque el .tex
        todavía no estaba disponible y esa era la única forma de garantizar que
        nadie inventara ejercicios. Ahora el .tex sí está, así que la garantía
        se comprueba contra la fuente en vez de prohibir los datos.

        Si el .tex se borra del proyecto, esta comprobación deja de ser posible
        y el test se salta: la procedencia ya no se puede verificar contra nada.
        Las comprobaciones estructurales de los otros tests siguen aplicando.
        """
        fuente = Path(__file__).resolve().parents[1] / "balotario" / "balotario.tex"
        if not fuente.is_file():
            self.skipTest("balotario.tex no está en el proyecto: la procedencia de los "
                          "enunciados ya no se puede comprobar contra la fuente")
        texto = fuente.read_text(encoding="utf-8")
        temas = cargar_catalogo()
        self.assertTrue(temas, "el catálogo no debe estar vacío")
        for tema in temas:
            for problema in tema["problemas"]:
                with self.subTest(problema=problema["id"]):
                    self.assertIn(f"Problema {problema['id']}", texto,
                                  "el problema no aparece en balotario.tex")

    def test_cada_tema_registra_de_donde_salio(self):
        """La procedencia viaja en el JSON, para que sobreviva al borrado del .tex."""
        for tema in cargar_catalogo():
            with self.subTest(tema=tema["tema"]["id"]):
                origen = tema["tema"]["origen"]
                self.assertEqual(origen["archivo"], "balotario.tex")
                self.assertTrue(origen["seccion_latex"].strip())
                inicio, fin = origen["lineas"]
                self.assertLess(inicio, fin)

    def test_rechaza_problemas_duplicados_entre_temas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            for n in (1, 2):
                contenido = {"schema_version": 1, "tema": {"id": f"tema_{n}"},
                             "problemas": [{"id": "duplicado"}]}
                Path(carpeta, f"tema_{n:02}.json").write_text(json.dumps(contenido), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicado"):
                cargar_catalogo(carpeta)

    def test_rechaza_json_invalido(self):
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "tema_01.json").write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON inválido"):
                cargar_catalogo(carpeta)

    def test_rechaza_directorio_inexistente(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaisesRegex(ValueError, "No existe"):
                cargar_catalogo(Path(carpeta) / "ausente")


if __name__ == "__main__":
    unittest.main()
