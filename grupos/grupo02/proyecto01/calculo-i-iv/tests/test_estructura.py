"""Pruebas de estructura del servidor MCP-Calculo.

NO requieren sympy, ni el SDK de mcp, ni PyYAML: solo la libreria estandar
(`ast`, `pathlib`, `unittest`). La idea es que estos tests corran en 1 segundo
y detecten el error mas comun de todos -- que alguien rompio el compose, borro
un skill, o escribio un modulo de `tools/` que no compila -- sin necesidad de
instalar nada ni de levantar el servidor.

    python -m unittest discover -s tests -v

Las pruebas que si necesitan `sympy` o `mcp` (probar que las tools devuelven
lo correcto) van aparte, en el modulo de cada area: esas son pruebas de
matematicas, no de estructura.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent

SKILLS_ESPERADOS = (
    "skill_resolver_examen.md",
    "skill_paso_a_paso.md",
    "skill_tutor_interactivo.md",
)
MODULOS_CALCULO = ("calculo1", "calculo2", "calculo3", "calculo4")


class TestEstructura(unittest.TestCase):
    def test_archivos_esenciales_existen(self) -> None:
        for nombre in ("server.py", "requirements.txt", "Dockerfile", "docker-compose.yml"):
            with self.subTest(archivo=nombre):
                self.assertTrue((APP_DIR / nombre).is_file(), f"falta {nombre}")

    def test_los_tres_skills_existen_y_no_estan_vacios(self) -> None:
        for nombre in SKILLS_ESPERADOS:
            with self.subTest(skill=nombre):
                ruta = APP_DIR / "skill" / nombre
                self.assertTrue(ruta.is_file(), f"falta skill/{nombre}")
                self.assertGreater(
                    len(ruta.read_text(encoding="utf-8").strip()), 200,
                    f"skill/{nombre} esta demasiado corto para ser un contexto util",
                )

    def test_python_compila(self) -> None:
        """Un error de sintaxis en server.py no se ve hasta que corre el server:
        en Docker eso significa un contenedor que muere al instante y un CI en
        rojo. Compilar aqui es mas barato que descubrirlo ahi."""
        for ruta in [APP_DIR / "server.py", APP_DIR / "tools" / "_plantilla.py", *(
            APP_DIR / "tools" / f"{m}.py" for m in MODULOS_CALCULO
        )]:
            if not ruta.is_file():
                continue  # el modulo de un area todavia no existe: no es error
            with self.subTest(archivo=ruta.name):
                ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))

    def test_carpeta_de_modulos_existe(self) -> None:
        self.assertTrue((APP_DIR / "tools").is_dir())
        self.assertTrue((APP_DIR / "tools" / "README.md").is_file(),
                        "falta tools/README.md (el contrato de los programadores)")


class TestModulosDeHerramientas(unittest.TestCase):
    """Las reglas que tools/README.md le promete a la IA que va a leer el
    docstring de cada tool. Un modulo que las incumple no es 'un poco menos
    util': la IA no va a poder llamarlo bien."""

    def test_cumple_el_contrato(self) -> None:
        """Valida SOLO las funciones que se van a registrar como tools, que es
        lo mismo que hace `server.py`: si el modulo declara `HERRAMIENTAS`, se
        respetan esos nombres y el resto son helpers internos que nunca llegan
        al cliente MCP (y por lo tanto no tienen por qué cumplir el contrato).
        Exigirle el contrato a un helper interno es hacer fallar el test por
        algo que no importa."""
        for nombre in MODULOS_CALCULO:
            ruta = APP_DIR / "tools" / f"{nombre}.py"
            if not ruta.is_file():
                continue  # area todavia sin empezar
            with self.subTest(modulo=nombre):
                arbol = ast.parse(ruta.read_text(encoding="utf-8"))
                declaradas = self._herramientas_declaradas(arbol)
                funciones = self._a_registrar(arbol, declaradas)
                self.assertTrue(
                    funciones,
                    f"tools/{nombre}.py no tiene ninguna funcion publica: "
                    "el servidor no registraria ninguna tool",
                )
                for fn in funciones:
                    self.assertIsNotNone(
                        ast.get_docstring(fn),
                        f"{nombre}.{fn.name}() no tiene docstring: es lo que lee la IA "
                        "para saber como usarla",
                    )
                    self.assertIsNotNone(
                        fn.returns,
                        f"{nombre}.{fn.name}() no anota el tipo de retorno: sin el, "
                        "pydantic no arma el schema de la tool",
                    )
                    for arg in fn.args.args + fn.args.kwonlyargs:
                        if arg.arg in ("self", "cls"):
                            continue
                        self.assertIsNotNone(
                            arg.annotation,
                            f"{nombre}.{fn.name}() no anota el tipo de '{arg.arg}': "
                            "el cliente MCP no sabria que argumento pasar",
                        )

    @staticmethod
    def _herramientas_declaradas(arbol: ast.AST) -> set[str] | None:
        """Nombres del manifiesto de tools, o None si el modulo no declara uno.

        Misma regla que `server.py`: se acepta cualquier variable de nivel de
        modulo que empiece por `HERRAMIENTAS` (cada area le pone su sufijo), y
        dentro se aceptan las dos formas:
          - strings:  HERRAMIENTAS = ["limite", "dominio"]
          - objetos:  HERRAMIENTAS_CALCULO2 = (calcular_integral, riemann)
        """
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Assign):
                continue
            nombres_obj = [
                t.id for t in nodo.targets
                if isinstance(t, ast.Name) and t.id.startswith("HERRAMIENTAS")
            ]
            if not nombres_obj:
                continue
            nombres = {
                n.id for n in ast.walk(nodo.value)
                if isinstance(n, ast.Name)
            } | {
                c.value for c in ast.walk(nodo.value)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)
            }
            return nombres or None
        return None

    def _a_registrar(self, arbol: ast.AST, declaradas: set[str] | None) -> list[ast.FunctionDef]:
        """Las FunctionDef que el servidor convertiria en tools."""
        todas = {
            n.name: n for n in ast.walk(arbol)
            if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
        }
        if declaradas is None:
            return list(todas.values())
        return [todas[n] for n in sorted(declaradas) if n in todas]


class TestCompose(unittest.TestCase):
    """Las mismas reglas que valida el CI (ci/compose_policy.py), replicadas
    para poder correrlas localmente sin instalar nada.

    Ver la nota de `_servicios` sobre por que no se usa PyYAML."""

    def setUp(self) -> None:
        self.compose = (APP_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    def _servicios(self) -> dict[str, list[str]]:
        """Devuelve {nombre_del_servicio: [sus lineas]} leidos del bloque
        `services:` del compose.

        No se usa PyYAML a proposito: un `import yaml` convierte un test de 1
        segundo en un test que depende de que el interprete tenga un paquete
        instalado, y el que no lo tiene se lo salta en silencio (peor que
        fallar). El compose de este proyecto tiene forma conocida y fija, asi
        que alcanza con mirarlo por indentacion."""
        self.assertIn("services:", self.compose, "el compose no define 'services:'")
        bloque = self.compose.split("services:", 1)[1]
        for clave in ("networks:", "volumes:"):
            if clave in bloque:
                bloque = bloque.split(clave, 1)[0]

        servicios: dict[str, list[str]] = {}
        nombre_actual: str | None = None
        for linea in bloque.splitlines():
            if linea.startswith("  ") and not linea.startswith("   ") and linea.rstrip().endswith(":"):
                nombre_actual = linea.strip()[:-1]
                servicios[nombre_actual] = []
            elif nombre_actual is not None and linea.strip():
                servicios[nombre_actual].append(linea)
        return servicios

    def test_declara_al_menos_un_servicio(self) -> None:
        self.assertTrue(self._servicios(), "el compose no define ningun servicio")

    def test_usa_variables_de_entorno_del_despliegue(self) -> None:
        self.assertIn("${LAB_CONTAINER_NAME}", self.compose,
                      "el despliegue inyecta el container_name; no debe escribirse a mano")
        self.assertIn("lab_net", self.compose, "falta unirse a la red externa lab_net")
        self.assertIn("external: true", self.compose,
                      "la red lab_net debe declararse external, no crearse")

    def test_cumple_la_politica_de_recursos(self) -> None:
        """Reglas de ci/compose_policy.py: mem_limit obligatorio en TODO
        servicio, nada de privilegios peligrosos, y cero bind-mounts."""
        for nombre, lineas in self._servicios().items():
            with self.subTest(servicio=nombre):
                cuerpo = "\n".join(lineas)
                # -- mem_limit (o la forma larga, deploy.resources.limits.memory)
                self.assertTrue(
                    "mem_limit:" in cuerpo or "memory:" in cuerpo,
                    f"servicio '{nombre}': falta mem_limit "
                    "(el CI lo rechaza: ver ci/compose_policy.py)",
                )
                # -- prohibiciones explicitas
                for prohibido in ("privileged: true", "network_mode: host",
                                  "pid: host", "cap_add:", "devices:"):
                    self.assertNotIn(
                        prohibido, cuerpo,
                        f"servicio '{nombre}': '{prohibido}' no esta permitido",
                    )
                # -- cero bind-mounts: ningun volumen puede arrancar con una
                #    ruta del host (/, ./, ../, ~)
                for linea in lineas:
                    vol = linea.strip()
                    if not vol.startswith("- "):
                        continue
                    origen = vol[2:].split(":", 1)[0].strip()
                    self.assertFalse(
                        origen.startswith(("/", "./", "../", "~")) or origen == ".",
                        f"servicio '{nombre}': bind-mount no permitido: {vol}",
                    )

    def test_el_transporte_no_es_stdio(self) -> None:
        """El error de configuracion mas caro: dejar MCP_TRANSPORT en stdio
        dentro del contenedor hace que el proceso muera al instante, porque no
        hay consola que alimente el puerto."""
        self.assertIn("streamable-http", self.compose)
        dockerfile = (APP_DIR / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("MCP_TRANSPORT", dockerfile)

    def test_la_salida_del_servidor_no_queda_en_el_buffer(self) -> None:
        """El CI lee `docker compose logs` para ver si la app arranco. Sin
        PYTHONUNBUFFERED, los `print` del banner de arranque de server.py se
        quedan en el buffer de stdout -- porque cuando la salida no es una
        terminal Python no hace flush, y el proceso nunca termina -- y el
        profesor ve un log vacio aunque el servidor este andaando."""
        dockerfile = (APP_DIR / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn(
            "PYTHONUNBUFFERED", dockerfile,
            "falta PYTHONUNBUFFERED=1 en el Dockerfile: el banner de arranque "
            "no va a aparecer en docker compose logs",
        )


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
