"""Pruebas de las skills (skill/*.md) del servidor MCP-Calculo.

Igual que test_estructura.py: NO requieren sympy, ni el SDK de mcp, ni PyYAML.
Solo libreria estandar (`ast`, `re`, `pathlib`, `unittest`), y corren en menos
de un segundo:

    python -m unittest discover -s tests -v

Que protegen: las skills son instrucciones para la IA, y una instruccion que
cita una tool que no existe, o un parametro que ya no esta en el codigo, no
falla en ningun lado: la IA simplemente llama mal a la tool y el alumno recibe
una respuesta rota. Estas pruebas cruzan lo que dicen las skills con lo que
hay de verdad en `server.py` y en `tools/calculo<N>.py`.

Los modulos de `tools/` que todavia no existen se saltan (no es error).
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
SKILL_DIR = APP_DIR / "skill"
TOOLS_DIR = APP_DIR / "tools"
SERVER = APP_DIR / "server.py"

MODULOS_CALCULO = ("calculo1", "calculo2", "calculo3", "calculo4")

# Secciones que cada skill tiene que tener (se busca en los titulos Markdown).
SECCIONES = {
    "skill_resolver_examen.md": (
        "Propósito", "Cuándo se activa", "Flujo de trabajo", "Formato de salida",
        "Mapeo de ejercicios", "Si el módulo no está disponible",
        "Manejo de errores", "Ejemplo",
    ),
    "skill_paso_a_paso.md": (
        "Propósito", "Cuándo se activa", "Flujo de trabajo", "Formato de salida",
        "Relación con las tools", "Si el módulo no está disponible",
        "Manejo de errores", "Ejemplo",
    ),
    "skill_tutor_interactivo.md": (
        "Propósito", "Modalidades", "Ciclo de interacción",
        "Reglas de comportamiento", "Temario", "Verificación con tools", "Ejemplo",
    ),
}

# Piezas literales de la plantilla de salida de cada skill.
PLANTILLAS = {
    "skill_resolver_examen.md": (
        "### Solución", "**Planteamiento:**", "**Desarrollo:**", "**Respuesta final:**",
    ),
    "skill_paso_a_paso.md": (
        "### Vamos a resolverlo juntos", "**Respuesta final:**",
        "**Idea clave para recordar:**",
    ),
    "skill_tutor_interactivo.md": (),
}

# Los cinco pasos del ciclo del tutor.
CICLO_TUTOR = ("Teoría", "Ejemplo resuelto", "Ejercicio de práctica",
               "Verificación", "Retroalimentación")

NOMBRE_DE_MODULO = re.compile(r"(?<![\w])calculo[1-4]_[A-Za-z][A-Za-z0-9_]*")
NOMBRE_BASE = re.compile(r"(?<![\w])(?:(?:calcular|verificar)_[a-z_]+|estado_del_servidor)")
LLAMADA = re.compile(r"(?<![\w])((?:calculo[1-4]_)?[A-Za-z][A-Za-z0-9_]*)\(")
IDENTIFICADOR = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", re.ASCII)


# ---------------------------------------------------------------------------
# Utilidades: lo que hay de verdad en el codigo
# ---------------------------------------------------------------------------
def _leer(ruta: Path) -> str:
    return ruta.read_text(encoding="utf-8")


def _sin_codigo(texto: str) -> str:
    """El Markdown sin los bloques ``` (las plantillas traen '###' falsos)."""
    return re.sub(r"```.*?```", "", texto, flags=re.DOTALL)


def _parametros_de(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = fn.args
    return [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]


def _funciones_de_primer_nivel(arbol: ast.Module) -> dict[str, list[str]]:
    return {
        n.name: _parametros_de(n)
        for n in arbol.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _tools_base_y_firmas() -> tuple[set[str], dict[str, list[str]]]:
    """(nombres en TOOLS_BASE, firmas de esas funciones) leidos de server.py."""
    arbol = ast.parse(_leer(SERVER))
    nombres: set[str] = set()
    for nodo in arbol.body:
        destino = None
        if isinstance(nodo, ast.Assign):
            destino = nodo.targets[0]
        elif isinstance(nodo, ast.AnnAssign):
            destino = nodo.target
        if isinstance(destino, ast.Name) and destino.id == "TOOLS_BASE" and nodo.value:
            nombres = {c.value for c in ast.walk(nodo.value)
                       if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    firmas = {n: p for n, p in _funciones_de_primer_nivel(arbol).items() if n in nombres}
    return nombres, firmas


def _tools_de_modulo(modulo: str) -> dict[str, list[str]] | None:
    """{nombre_de_tool_con_prefijo: parametros} de un modulo, o None si no existe.

    Misma regla que server.py: si el modulo declara HERRAMIENTAS (strings o
    funciones) se respeta esa lista; si no, valen todas las funciones publicas
    definidas en el archivo.
    """
    ruta = TOOLS_DIR / f"{modulo}.py"
    if not ruta.is_file():
        return None
    arbol = ast.parse(_leer(ruta))
    funciones = {n: p for n, p in _funciones_de_primer_nivel(arbol).items()
                 if not n.startswith("_")}
    declaradas: set[str] | None = None
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "HERRAMIENTAS" for t in nodo.targets):
            declaradas = (
                {n.id for n in ast.walk(nodo.value) if isinstance(n, ast.Name)}
                | {c.value for c in ast.walk(nodo.value)
                   if isinstance(c, ast.Constant) and isinstance(c.value, str)}
            )
    if declaradas is not None:
        funciones = {n: p for n, p in funciones.items() if n in declaradas}
    return {f"{modulo}_{n}": p for n, p in funciones.items()}


def _llamadas(texto: str, conocidas: set[str]):
    """Genera (nombre_de_tool, texto_entre_parentesis) por cada `tool(...)`.

    Recorre los parentesis con balance e ignora los que van dentro de comillas,
    porque los ejemplos traen cosas como expresion="x*exp(x)".
    """
    for m in LLAMADA.finditer(texto):
        nombre = m.group(1)
        if nombre not in conocidas:
            continue
        inicio, profundidad, comilla, i = m.end(), 1, None, m.end()
        while i < len(texto) and profundidad:
            c = texto[i]
            if comilla:
                comilla = None if c == comilla else comilla
            elif c in "\"'":
                comilla = c
            elif c == "(":
                profundidad += 1
            elif c == ")":
                profundidad -= 1
            i += 1
        interior = texto[inicio:i - 1]
        if profundidad == 0 and len(interior) <= 400:
            yield nombre, interior


def _parametros_citados(interior: str) -> list[str]:
    """Nombres de parametro en 'a, b=1, c="x"'. Ignora valores, '...' y texto
    que no sea un identificador (por ejemplo 'límites')."""
    sin_cadenas = re.sub(r'"[^"]*"|\'[^\']*\'', '""', interior)
    nombres = []
    for pieza in sin_cadenas.split(","):
        pieza = pieza.split("=", 1)[0].strip()
        if IDENTIFICADOR.fullmatch(pieza):
            nombres.append(pieza)
    return nombres


# ---------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------
class TestContenidoDeLasSkills(unittest.TestCase):
    def setUp(self) -> None:
        self.skills: dict[str, str] = {}
        for nombre in SECCIONES:
            ruta = SKILL_DIR / nombre
            self.assertTrue(ruta.is_file(), f"falta skill/{nombre}")
            self.skills[nombre] = _leer(ruta)

    def test_tienen_las_secciones_obligatorias(self) -> None:
        for nombre, esperadas in SECCIONES.items():
            titulos = [l.lower() for l in _sin_codigo(self.skills[nombre]).splitlines()
                       if l.lstrip().startswith("#")]
            for seccion in esperadas:
                with self.subTest(skill=nombre, seccion=seccion):
                    self.assertTrue(
                        any(seccion.lower() in t for t in titulos),
                        f"skill/{nombre} no tiene una seccion '{seccion}'",
                    )

    def test_conservan_su_plantilla_de_salida(self) -> None:
        for nombre, piezas in PLANTILLAS.items():
            for pieza in piezas:
                with self.subTest(skill=nombre, pieza=pieza):
                    self.assertIn(pieza, self.skills[nombre],
                                  f"skill/{nombre} perdio '{pieza}' de su plantilla")

    def test_el_tutor_define_el_ciclo_y_la_verificacion(self) -> None:
        texto = self.skills["skill_tutor_interactivo.md"]
        for paso in CICLO_TUTOR:
            with self.subTest(paso=paso):
                self.assertIn(paso, texto, f"el tutor no menciona el paso '{paso}'")
        for termino in ("verificar_respuesta", "expresion", "referencia"):
            with self.subTest(termino=termino):
                self.assertIn(termino, texto,
                              f"el tutor no explica '{termino}' de verificar_respuesta")

    def test_documentan_los_tres_estados_de_las_tools(self) -> None:
        for nombre, texto in self.skills.items():
            for estado in ('"exito"', '"parcial"', '"error"'):
                with self.subTest(skill=nombre, estado=estado):
                    self.assertIn(estado, texto,
                                  f"skill/{nombre} no documenta el estado {estado}")

    def test_los_bloques_de_codigo_estan_cerrados(self) -> None:
        for nombre, texto in self.skills.items():
            with self.subTest(skill=nombre):
                vallas = [l for l in texto.splitlines() if l.lstrip().startswith("```")]
                self.assertEqual(len(vallas) % 2, 0,
                                 f"skill/{nombre} tiene un bloque ``` sin cerrar")

    def test_no_quedan_marcas_de_pendiente(self) -> None:
        for nombre, texto in self.skills.items():
            with self.subTest(skill=nombre):
                self.assertIsNone(re.search(r"\b(TODO|FIXME|XXX|PENDIENTE)\b", texto),
                                  f"skill/{nombre} tiene una marca de pendiente")


class TestSkillsContraElCodigo(unittest.TestCase):
    """Lo que las skills le dicen a la IA contra lo que el codigo hace."""

    @classmethod
    def setUpClass(cls) -> None:
        assert SERVER.is_file(), "falta server.py"
        cls.base, cls.firmas_base = _tools_base_y_firmas()
        cls.modulos = {m: _tools_de_modulo(m) for m in MODULOS_CALCULO}
        cls.firmas: dict[str, list[str]] = dict(cls.firmas_base)
        for tools in cls.modulos.values():
            cls.firmas.update(tools or {})
        cls.skills = {n: _leer(SKILL_DIR / n) for n in SECCIONES if (SKILL_DIR / n).is_file()}

    def test_server_declara_tools_base(self) -> None:
        self.assertTrue(self.base, "no se pudo leer TOOLS_BASE de server.py")
        for nombre in ("verificar_respuesta", "estado_del_servidor"):
            self.assertIn(nombre, self.firmas_base)

    def test_las_tools_base_citadas_existen(self) -> None:
        for nombre, texto in self.skills.items():
            for cita in sorted(set(NOMBRE_BASE.findall(texto))):
                with self.subTest(skill=nombre, tool=cita):
                    self.assertIn(cita, self.base,
                                  f"skill/{nombre} cita la tool base '{cita}', "
                                  "que no esta en TOOLS_BASE de server.py")

    def test_las_tools_de_modulo_citadas_existen(self) -> None:
        for nombre, texto in self.skills.items():
            for cita in sorted(set(NOMBRE_DE_MODULO.findall(texto))):
                modulo = cita.split("_", 1)[0]
                tools = self.modulos.get(modulo)
                if tools is None:
                    continue  # ese modulo todavia no existe: no se puede comprobar
                with self.subTest(skill=nombre, tool=cita):
                    self.assertIn(cita, tools,
                                  f"skill/{nombre} cita '{cita}', pero tools/{modulo}.py "
                                  "no registra una tool con ese nombre")

    def test_los_parametros_citados_existen(self) -> None:
        conocidas = set(self.firmas)
        for nombre, texto in self.skills.items():
            for tool, interior in _llamadas(texto, conocidas):
                for param in _parametros_citados(interior):
                    with self.subTest(skill=nombre, tool=tool, parametro=param):
                        self.assertIn(
                            param, self.firmas[tool],
                            f"skill/{nombre} llama {tool}(... {param} ...), pero esa tool "
                            f"solo recibe: {', '.join(self.firmas[tool]) or '(nada)'}",
                        )

    def test_server_lee_skills_que_existen(self) -> None:
        arbol = ast.parse(_leer(SERVER))
        leidos = {
            n.args[0].value for n in ast.walk(arbol)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "leer_skill" and n.args
            and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)
        }
        self.assertTrue(leidos, "server.py no llama a leer_skill() con ningun archivo")
        for archivo in sorted(leidos):
            with self.subTest(archivo=archivo):
                self.assertTrue((SKILL_DIR / archivo).is_file(),
                                f"server.py lee skill/{archivo}, que no existe")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
