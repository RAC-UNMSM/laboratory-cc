#!/usr/bin/env python3
"""Validador de entregas del repo `lab` (ver ../SKILL.md).

Revisa la carpeta de un grupo ANTES de abrir o actualizar un PR contra
`main` y responde tres preguntas:

  1. ¿Hay algo que NO debe subirse? (entornos virtuales, binarios, archivos
     fuera de la carpeta del grupo, lo que el .gitignore de main ignora)
  2. ¿La app va a desplegar? (estructura grupoNN/<semana>/<tema>/, compose,
     Dockerfile, requirements.txt, server.py, storage.py)
  3. ¿Qué tiene que hacer el administrador en el repo de infraestructura
     para que el despliegue funcione? (rutas de Caddy, variables, etc.)

Uso (desde cualquier carpeta del repo):

    python .claude/skills/mcp-validator/scripts/validar_entrega.py [grupoNN]

Sin dependencias obligatorias: solo la librería estándar. Si PyYAML está
instalado, el docker-compose.yml se valida completo; si no, con un chequeo
de texto más simple.

Las reglas de despliegue son las mismas que aplica el repo de
infraestructura (lab_deploy/naming.py, apps.py, compose_policy.py)
y el CI de este repo (.github/workflows/ci.yml). Si cambian allá, hay que
actualizarlas acá.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # el alumno puede no tener PyYAML
    yaml = None

# --- Constantes del despliegue (deben coincidir con el repo de infraestructura) ---

ADMIN = "Julios Castillo Melchor"
DOMINIO = "rac-unmsm.vekthos.org"
PUERTO_MCP = 8000
MCP_PIN = "mcp==2.1.1"
SEAWEEDFS_URL = "http://seaweedfs:8333"
MEM_LIMIT_BASE_MB = 512
# deployer.py del repo de infraestructura: BUILD_TIMEOUT y HEALTH_TIMEOUT.
BUILD_MIN = 15
SALUD_SEG = 60
# Docker Compose exige esto para el nombre de proyecto (lab-<grupo>-<app>).
NOMBRE_VALIDO = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
# Variables que inyecta el propio despliegue: no hay que pedirlas.
VARS_AUTOMATICAS = {"LAB_CONTAINER_NAME", "LAB_PUBLIC_PATH", "LAB_DOMAIN"}
# Carpetas bajo grupos/ que no son la entrega de un grupo de alumnos.
NO_GRUPOS = {"TEMPLATE", "_referencia"}
PILOTO_BUCKET = "derivadas1-imgs"
PILOTO_NOMBRE = "g01-derivadas1"

# Servicios públicos de subida de archivos: los resultados del laboratorio
# no deben salir a servidores de terceros.
HOSTS_SUBIDA_PUBLICA = {
    "tmpfiles.org", "0x0.st", "file.io", "transfer.sh", "catbox.moe",
    "litterbox.catbox.moe", "imgur.com", "api.imgur.com", "imgbb.com",
    "api.imgbb.com", "uguu.se", "pastebin.com", "bashupload.com",
}
HOSTS_LOCALES = {"localhost", "127.0.0.1", "0.0.0.0"}
HOSTS_INTERNOS = {"seaweedfs", DOMINIO}

# import -> paquete de pip, cuando no se llaman igual.
IMPORT_A_PAQUETE = {
    "PIL": "pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
    "skimage": "scikit-image", "yaml": "pyyaml", "bs4": "beautifulsoup4",
    "dotenv": "python-dotenv", "mpl_toolkits": "matplotlib", "pylab": "matplotlib",
    "dateutil": "python-dateutil", "serial": "pyserial", "fitz": "pymupdf",
    "docx": "python-docx", "pptx": "python-pptx", "jwt": "pyjwt",
    "Crypto": "pycryptodome", "attr": "attrs", "google": "google-*",
    "starlette": "starlette", "multipart": "python-multipart",
}
# Paquetes que traen otros módulos importables (no hace falta listarlos aparte).
PAQUETE_PROVEE = {
    "mcp": {"mcp", "pydantic", "starlette", "uvicorn", "anyio", "httpx"},
    "fastapi": {"fastapi", "starlette", "pydantic"},
    "matplotlib": {"matplotlib", "mpl_toolkits", "pylab"},
}
# Extensiones habituales en una entrega; lo demás se le menciona al administrador.
EXT_HABITUALES = {
    ".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".json",
    ".png", ".jpg", ".jpeg", ".svg", ".gif", "", ".gitignore", ".dockerignore",
}
BINARIOS_GUI = {"open", "xdg-open", "start", "explorer", "explorer.exe", "notepad", "cmd"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) or {
    "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib", "copy",
    "csv", "dataclasses", "datetime", "decimal", "enum", "fractions", "functools",
    "glob", "hashlib", "io", "itertools", "json", "logging", "math", "os", "pathlib",
    "random", "re", "shutil", "statistics", "string", "subprocess", "sys", "tempfile",
    "textwrap", "time", "typing", "unittest", "urllib", "uuid", "warnings", "__future__",
}


class Reporte:
    """Acumula hallazgos. Niveles: ERROR bloquea el PR, FALTA es lo que le
    falta a una app para desplegar (no impide subir un avance), AVISO
    conviene corregir, INFO es contexto, y `admin` son cosas que debe hacer
    el administrador."""

    def __init__(self) -> None:
        self.items: list[list[str]] = []  # [seccion, nivel, texto]
        self.admin: list[str] = []
        self.seccion = "General"
        self.forzados: set[str] = set()

    def en(self, seccion: str) -> None:
        self.seccion = seccion

    def error(self, texto: str, siempre: bool = False) -> None:
        """`siempre=True`: bloquea el PR aunque la app todavía no despliegue."""
        self.items.append([self.seccion, "ERROR", texto])
        if siempre:
            self.forzados.add(texto)

    def falta(self, texto: str) -> None:
        self.items.append([self.seccion, "FALTA", texto])

    def aviso(self, texto: str) -> None:
        self.items.append([self.seccion, "AVISO", texto])

    def info(self, texto: str) -> None:
        self.items.append([self.seccion, "INFO", texto])

    def ok(self, texto: str) -> None:
        self.items.append([self.seccion, "OK", texto])

    def degradar(self, seccion: str) -> None:
        """Una app sin docker-compose.yml no la construye ni el CI ni el
        despliegue: sus errores son pendientes, no motivo para frenar el PR."""
        for item in self.items:
            if item[0] == seccion and item[1] == "ERROR" and item[2] not in self.forzados:
                item[1] = "FALTA"

    def para_admin(self, texto: str) -> None:
        if texto not in self.admin:
            self.admin.append(texto)

    def n(self, nivel: str) -> int:
        return sum(1 for _, lvl, _ in self.items if lvl == nivel)


# --- Utilidades ------------------------------------------------------------------


def git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        r = subprocess.run(
            ["git", "-c", "core.quotepath=off", *args], cwd=repo,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return 127, ""
    return r.returncode, r.stdout.strip()


def leer(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def normalizar_paquete(nombre: str) -> str:
    return re.sub(r"[-_.]+", "-", nombre).lower()


def mem_a_mb(valor) -> float | None:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmg]?)b?\s*", str(valor).lower())
    if not m:
        return None
    n = float(m.group(1))
    return {"": n / 1048576, "k": n / 1024, "m": n, "g": n * 1024}[m.group(2)]


def resumir_rutas(rutas: list[str], niveles: int = 4, tope: int = 12) -> list[str]:
    """Agrupa miles de rutas (ej. un venv) por su carpeta para que el reporte
    no sea ilegible."""
    grupos: dict[str, int] = {}
    for r in rutas:
        partes = r.split("/")
        clave = "/".join(partes[:niveles]) + ("/…" if len(partes) > niveles else "")
        grupos[clave] = grupos.get(clave, 0) + 1
    filas = sorted(grupos.items(), key=lambda kv: -kv[1])
    out = [f"{k}  ({v} archivo{'s' if v != 1 else ''})" for k, v in filas[:tope]]
    if len(filas) > tope:
        out.append(f"… y {len(filas) - tope} carpetas más")
    return out


# --- 1. Git: qué no debe subirse -------------------------------------------------


def revisar_git(repo: Path, grupo: str, base: str, rep: Reporte) -> dict:
    rep.en("Git: qué se está subiendo")
    ctx = {"nuevos": [], "base_ok": False, "ignorados": set()}

    code, rama = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0:
        rep.aviso("No se pudo consultar git; se revisa solo el contenido de la carpeta.")
        return ctx
    if rama == "main":
        rep.aviso("Estás en `main`. El trabajo va en la rama de tu grupo o en una rama personal que salga de ella.")

    code, _ = git(repo, "rev-parse", "--verify", "--quiet", base)
    if code != 0:
        rep.aviso(f"No existe `{base}` en tu copia. Ejecuta `git fetch origin` y vuelve a correr la revisión.")
        return ctx
    ctx["base_ok"] = True

    _, detras = git(repo, "rev-list", "--count", f"HEAD..{base}")
    if detras and detras != "0":
        rep.aviso(
            f"Tu rama está {detras} commits detrás de `{base}`. Actualízala antes del PR: "
            f"`git merge {base}` (así recibes también el .gitignore actual)."
        )
    else:
        rep.ok(f"La rama está al día con `{base}`.")

    # Qué cambia este PR respecto de main. Fuera de la carpeta del grupo solo
    # cuenta lo que la rama tocó Y además quedaría distinto de main: lo demás
    # es herencia de un main antiguo y desaparece solo al actualizar la rama.
    prefijo = f"grupos/{grupo}/"
    _, diff = git(repo, "diff", "--name-status", "-M", f"{base}...HEAD")
    _, distinto = git(repo, "diff", "--name-only", base, "HEAD")
    distinto_de_main = set(distinto.splitlines())
    tocados = {l.split("\t")[-1] for l in diff.splitlines() if "\t" in l}

    # Archivos ya subidos que el .gitignore de main ignora. Se usa el de main
    # (no el de la rama) porque una rama atrasada puede no tenerlo todavía.
    code, ignore_main = git(repo, "show", f"{base}:.gitignore")
    ignorados: list[str] = []
    if code == 0 and ignore_main:
        with tempfile.NamedTemporaryFile("w", suffix=".gitignore", delete=False, encoding="utf-8") as fh:
            fh.write(ignore_main + "\n")
            tmp = fh.name
        try:
            _, out = git(repo, "ls-files", "-c", "-i", f"--exclude-from={tmp}")
        finally:
            os.unlink(tmp)
        _, en_main = git(repo, "ls-tree", "-r", "--name-only", base)
        ya_en_main = set(en_main.splitlines())
        ignorados = [
            p for p in out.splitlines()
            if p and p not in ya_en_main and (p.startswith(prefijo) or p in tocados)
        ]
        ctx["ignorados"] = set(ignorados)
    if ignorados:
        rep.error(
            f"Hay {len(ignorados)} archivos subidos que no deben estar en el repo "
            "(entornos virtuales, caches, binarios, generados):\n      "
            + "\n      ".join(resumir_rutas(ignorados))
            + "\n    Se quitan de git sin borrarlos de tu disco con "
            "`git rm -r --cached <carpeta>` y un commit."
        )
    else:
        rep.ok("No hay entornos virtuales, caches ni binarios subidos.")

    fuera, nuevos = [], []
    for linea in diff.splitlines():
        partes = linea.split("\t")
        if len(partes) < 2:
            continue
        estado, ruta = partes[0], partes[-1]
        if not ruta.startswith(prefijo):
            if ruta in distinto_de_main:
                fuera.append(f"{estado[0]}  {ruta}")
        elif estado.startswith("A"):
            nuevos.append(ruta)
    ctx["nuevos"] = nuevos
    # Apps que este PR elimina o renombra: el contenedor viejo no se baja solo.
    for linea in diff.splitlines():
        partes = linea.split("\t")
        if partes[0][:1] in ("D", "R") and len(partes) >= 2:
            trozos = partes[1].split("/")
            if len(trozos) == 5 and trozos[1] == grupo and trozos[4] == "docker-compose.yml":
                viejo = f"{grupo}_{trozos[2]}_{trozos[3]}"
                rep.info(f"Este PR elimina o renombra la app `{viejo}`: su contenedor seguirá corriendo en el servidor hasta que el administrador lo baje.")
                rep.para_admin(
                    f"La app `{viejo}` deja de existir en el repo (eliminada o renombrada). Su contenedor no se baja solo: "
                    f"`docker compose -p lab-{grupo}-{viejo} down`, y quitar su ruta de Caddy."
                )
    if fuera:
        rep.error(
            f"El PR toca {len(fuera)} archivos fuera de `{prefijo}` (A=agrega, M=modifica, D=borra):\n      "
            + "\n      ".join(fuera[:15]) + ("\n      …" if len(fuera) > 15 else "")
            + "\n    Un grupo solo cambia su propia carpeta. Si actualizar con "
            f"`git merge {base}` no los hace desaparecer, restáuralos con "
            f"`git checkout {base} -- <archivo>` (o `git rm <archivo>` si lo creaste tú)."
        )
    else:
        rep.ok(f"El PR solo toca `{prefijo}`.")

    # ¿Se podrá fusionar? Simula el merge con main sin tocar nada.
    code_mt, salida_mt = git(repo, "merge-tree", "--write-tree", "--name-only", base, "HEAD")
    if code_mt == 1:
        en_conflicto = [l for l in salida_mt.splitlines()[1:] if l.strip()]
        en_conflicto = en_conflicto[: en_conflicto.index("")] if "" in en_conflicto else en_conflicto
        archivos = [l for l in en_conflicto if "/" in l or "." in l][:10]
        rep.error(
            f"Tu rama tiene conflictos con `{base}`: el PR no se podrá fusionar tal cual.\n      "
            + "\n      ".join(archivos)
            + f"\n    Ejecuta `git merge {base}`, resuelve esos archivos y confirma."
        )
    elif code_mt == 0:
        rep.ok(f"La rama se puede fusionar con `{base}` sin conflictos.")

    # Cambios hechos pero todavía sin confirmar (commit).
    _, porcelana = git(repo, "status", "--porcelain")
    pend_fuera, pend_dentro = [], []
    for linea in porcelana.splitlines():
        ruta = linea[2:].strip().split(" -> ")[-1].strip('"')
        (pend_dentro if ruta.startswith(prefijo) else pend_fuera).append(f"{linea[:2].strip() or '?'}  {ruta}")
    if pend_fuera:
        rep.aviso(
            f"Tienes {len(pend_fuera)} cambio(s) sin confirmar FUERA de tu carpeta. No los agregues al commit "
            "(revisa con `git status` antes de `git add`):\n      " + "\n      ".join(pend_fuera[:10])
        )
    if pend_dentro:
        rep.info(
            f"Tienes {len(pend_dentro)} cambio(s) en tu carpeta sin confirmar: todavía no forman parte del PR.\n      "
            + "\n      ".join(pend_dentro[:8]) + ("\n      …" if len(pend_dentro) > 8 else "")
        )

    # Archivos pesados dentro de la carpeta del grupo.
    _, tracked = git(repo, "ls-files", "--", prefijo)
    pesados = []
    for p in tracked.splitlines():
        if p in ignorados:
            continue
        f = repo / p
        if f.is_file() and f.stat().st_size > 1_000_000:
            pesados.append(f"{p}  ({f.stat().st_size / 1048576:.1f} MB)")
    if pesados:
        rep.aviso("Archivos de más de 1 MB (¿de verdad hacen falta en el repo?):\n      " + "\n      ".join(pesados[:10]))

    return ctx


# --- 2. Estructura ----------------------------------------------------------------


MARCADORES_APP = ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml", "Dockerfile", "server.py", "requirements.txt")
CARPETAS_OMITIDAS = {".git", "__pycache__", "node_modules", "site-packages", ".pytest_cache"}


def es_venv(d: Path) -> bool:
    return (d / "pyvenv.cfg").is_file()


def archivos_py(raiz_dir: Path) -> list[Path]:
    """Los .py de una carpeta, sin entrar a entornos virtuales ni caches."""
    encontrados: list[Path] = []
    for raiz, dirs, archivos in os.walk(raiz_dir):
        actual = Path(raiz)
        dirs[:] = sorted(d for d in dirs if d not in CARPETAS_OMITIDAS and not es_venv(actual / d))
        encontrados.extend(actual / a for a in sorted(archivos) if a.endswith(".py"))
    return encontrados


def buscar_apps(grupo_dir: Path) -> list[Path]:
    """Carpetas que parecen una app (tienen compose, Dockerfile o server.py),
    sin contar las que están dentro de otra app."""
    apps: list[Path] = []
    for raiz, dirs, archivos in os.walk(grupo_dir):
        actual = Path(raiz)
        dirs[:] = sorted(d for d in dirs if d not in CARPETAS_OMITIDAS and not es_venv(actual / d))
        if actual != grupo_dir and any(m in archivos for m in MARCADORES_APP):
            apps.append(actual)
            dirs[:] = []  # lo que haya debajo es parte de esta app
    return apps


def revisar_estructura(repo: Path, grupo_dir: Path, rep: Reporte) -> tuple[list[Path], list[Path]]:
    rep.en("Estructura de carpetas")
    grupo = grupo_dir.name
    apps = buscar_apps(grupo_dir)
    bien_ubicadas, mal_ubicadas = [], []
    for app in apps:
        partes = app.relative_to(grupo_dir).parts
        if len(partes) == 2:
            bien_ubicadas.append(app)
        else:
            mal_ubicadas.append(app)
            if len(partes) == 1:
                destino = f"grupos/{grupo}/proyecto01/{partes[0].lower().replace(' ', '-')}/"
            else:
                destino = f"grupos/{grupo}/{partes[0]}/{partes[-1].lower()}/"
            rep.falta(
                f"`{rel(app, repo)}` no se va a desplegar: el despliegue solo busca "
                f"`grupos/{grupo}/<semana>/<tema>/docker-compose.yml` (exactamente dos niveles "
                f"bajo la carpeta del grupo). Muévela a algo como `{destino}`."
            )

    for app in bien_ubicadas:
        semana, tema = app.relative_to(grupo_dir).parts
        for etiqueta, nombre in (("semana/proyecto", semana), ("tema", tema)):
            if not NOMBRE_VALIDO.match(nombre):
                sugerido = re.sub(r"[^a-z0-9_-]+", "-", nombre.lower()).strip("-")
                (rep.error if (app / "docker-compose.yml").is_file() else rep.falta)(
                    f"La carpeta de {etiqueta} `{nombre}` rompe el despliegue: su nombre forma el "
                    "nombre de proyecto de Docker Compose, que solo admite minúsculas, dígitos, "
                    f"`-` y `_` (sin espacios, mayúsculas ni tildes). Renómbrala a `{sugerido}`."
                )

    # Código suelto que no pertenece a ninguna app.
    sueltos = []
    for py in archivos_py(grupo_dir):
        if not any(app == py.parent or app in py.parents for app in apps):
            sueltos.append(rel(py, repo))
    # También cuentan los archivos que no son documentación dejados en la
    # carpeta del grupo o en la del proyecto, fuera de la carpeta del tema.
    niveles = [grupo_dir] + [d for d in sorted(grupo_dir.iterdir()) if d.is_dir() and d.name.lower() != "integrantes" and not es_venv(d)]
    for nivel in niveles:
        if nivel in apps:
            continue
        for f in sorted(nivel.iterdir()):
            if f.is_file() and f.suffix.lower() not in {".md", ".py"} and f.name not in {".gitignore", ".gitkeep"}:
                sueltos.append(rel(f, repo))
    if sueltos:
        rep.falta(
            "Archivos del proyecto fuera de su carpeta (no entran en ninguna imagen ni se despliegan):\n      "
            + "\n      ".join(sorted(set(sueltos))[:12])
            + f"\n    Todo el proyecto va dentro de `grupos/{grupo}/proyecto01/<nombre-del-proyecto>/`."
        )
    for app in bien_ubicadas:
        semana = app.relative_to(grupo_dir).parts[0]
        if grupo != "g01" and not re.fullmatch(r"(proyecto|semana)\d{2}", semana):
            rep.aviso(f"La carpeta `{semana}` debería llamarse `proyectoNN` (ej. `proyecto01`), como en el resto del repo.")

    if not apps:
        rep.info(
            "No hay ninguna app en la carpeta (ni compose, ni Dockerfile, ni server.py): "
            "esta entrega es solo documentación y no despliega nada."
        )
    elif bien_ubicadas and not mal_ubicadas:
        rep.ok("Las apps están en `<semana>/<tema>/` como espera el despliegue.")
    return bien_ubicadas, mal_ubicadas


# --- 3. Análisis del código Python ------------------------------------------------


class Codigo:
    """Todo lo que se necesita saber de los .py de una app, leído con ast."""

    def __init__(self, app: Path, rep: Reporte, repo: Path) -> None:
        self.app = app
        self.archivos: dict[Path, ast.Module] = {}
        self.fuentes: dict[Path, str] = {}
        for py in archivos_py(app):
            fuente = leer(py)
            self.fuentes[py] = fuente
            try:
                self.archivos[py] = ast.parse(fuente, filename=str(py))
            except SyntaxError as exc:
                rep.error(f"`{rel(py, repo)}` tiene un error de sintaxis en la línea {exc.lineno}: {exc.msg}. No arranca.")
        # Módulos propios de la app: sus .py y las carpetas que los contienen.
        self.locales = {p.stem for p in self.fuentes} | {
            d.name for p in self.fuentes for d in p.parents if app in d.parents
        }

    @staticmethod
    def es_test(py: Path) -> bool:
        return (
            py.name.startswith("test_") or py.name.endswith("_test.py") or py.name == "conftest.py"
            or any(p in {"tests", "test"} for p in py.parts)
        )

    def imports(self, py: Path) -> set[str]:
        nombres: set[str] = set()
        arbol = self.archivos.get(py)
        if not arbol:
            return nombres
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres.update(a.name.split(".")[0] for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                nombres.add(nodo.module.split(".")[0])
        return nombres

    def imports_completos(self, py: Path) -> set[str]:
        nombres: set[str] = set()
        arbol = self.archivos.get(py)
        if not arbol:
            return nombres
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres.update(a.name for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                nombres.add(nodo.module)
        return nombres

    def terceros(self, solo_tests: bool) -> dict[str, list[Path]]:
        usados: dict[str, list[Path]] = {}
        for py in self.archivos:
            if self.es_test(py) != solo_tests:
                continue
            for mod in self.imports(py):
                if mod in STDLIB or mod in self.locales or mod.startswith("_"):
                    continue
                usados.setdefault(mod, []).append(py)
        return usados

    def modulos_locales_de(self, entrada: Path) -> set[str]:
        """Nombres de primer nivel (archivo.py o carpeta/) que `entrada`
        importa, directa o indirectamente, dentro de la app."""
        vistos: set[Path] = set()
        necesarios: set[str] = set()
        pendientes = [entrada]
        while pendientes:
            py = pendientes.pop()
            if py in vistos or py not in self.archivos:
                continue
            vistos.add(py)
            for mod in self.imports_completos(py):
                raiz = mod.split(".")[0]
                como_archivo = self.app / f"{raiz}.py"
                como_carpeta = self.app / raiz
                if como_archivo.is_file():
                    necesarios.add(f"{raiz}.py")
                    pendientes.append(como_archivo)
                elif como_carpeta.is_dir():
                    necesarios.add(f"{raiz}/")
                    pendientes.extend(p for p in self.archivos if como_carpeta in p.parents)
        return necesarios

    def cadenas(self, py: Path) -> list[tuple[str, int]]:
        """Cadenas literales del archivo, sin contar docstrings."""
        arbol = self.archivos.get(py)
        if not arbol:
            return []
        docstrings = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                cuerpo = getattr(nodo, "body", [])
                if cuerpo and isinstance(cuerpo[0], ast.Expr) and isinstance(cuerpo[0].value, ast.Constant):
                    docstrings.add(id(cuerpo[0].value))
        return [
            (n.value, n.lineno) for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
        ]


class Resolver:
    """Averigua el valor que tendrá una expresión simple cuando el código
    corra en el contenedor: constantes, variables del módulo, f-strings y
    `os.getenv("X", "defecto")` (con lo que definan el compose y el Dockerfile)."""

    _GETENV = {"os.getenv", "os.environ.get", "environ.get", "getenv"}

    def __init__(self, arbol: ast.Module, env: dict[str, str]) -> None:
        self.env = env
        self.vars_usadas: list[str] = []
        self.asign: dict[str, ast.AST] = {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 and isinstance(nodo.targets[0], ast.Name):
                self.asign.setdefault(nodo.targets[0].id, nodo.value)
            elif isinstance(nodo, ast.AnnAssign) and isinstance(nodo.target, ast.Name) and nodo.value is not None:
                self.asign.setdefault(nodo.target.id, nodo.value)

    def valor(self, nodo: ast.AST | None, prof: int = 0):
        if nodo is None or prof > 8:
            return None
        if isinstance(nodo, ast.Constant):
            return nodo.value
        if isinstance(nodo, ast.Name):
            return self.valor(self.asign.get(nodo.id), prof + 1)
        if isinstance(nodo, ast.Subscript) and nombre_llamada(nodo.value) in {"os.environ", "environ"}:
            if isinstance(nodo.slice, ast.Constant):
                self.vars_usadas.append(str(nodo.slice.value))
                return self.env.get(str(nodo.slice.value))
            return None
        if isinstance(nodo, ast.Call):
            fn = nombre_llamada(nodo.func)
            if fn in self._GETENV and nodo.args and isinstance(nodo.args[0], ast.Constant):
                clave = str(nodo.args[0].value)
                self.vars_usadas.append(clave)
                if clave in self.env:
                    return self.env[clave]
                defecto = nodo.args[1] if len(nodo.args) > 1 else next((k.value for k in nodo.keywords if k.arg == "default"), None)
                return self.valor(defecto, prof + 1)
            if fn in {"int", "str", "float"} and nodo.args:
                interno = self.valor(nodo.args[0], prof + 1)
                try:
                    return {"int": int, "str": str, "float": float}[fn](interno) if interno is not None else None
                except (TypeError, ValueError):
                    return None
            if isinstance(nodo.func, ast.Attribute) and nodo.func.attr in {"strip", "lower", "rstrip", "lstrip"}:
                interno = self.valor(nodo.func.value, prof + 1)
                return getattr(interno, nodo.func.attr)() if isinstance(interno, str) and not nodo.args else interno
            return None
        if isinstance(nodo, ast.JoinedStr):
            partes = []
            for parte in nodo.values:
                trozo = self.valor(parte.value if isinstance(parte, ast.FormattedValue) else parte, prof + 1)
                if trozo is None:
                    return None
                partes.append(str(trozo))
            return "".join(partes)
        if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Add):
            izq, der = self.valor(nodo.left, prof + 1), self.valor(nodo.right, prof + 1)
            return izq + der if isinstance(izq, str) and isinstance(der, str) else None
        if isinstance(nodo, ast.BoolOp) and isinstance(nodo.op, ast.Or):
            for opcion in nodo.values:
                valor = self.valor(opcion, prof + 1)
                if valor:
                    return valor
        return None

    def resolver(self, nodo: ast.AST | None) -> tuple[object, str]:
        """(valor, nota): la nota dice si el valor viene de una variable de entorno."""
        self.vars_usadas = []
        valor = self.valor(nodo)
        definidas = [x for x in self.vars_usadas if x in self.env]
        nota = f" (valor de la variable `{definidas[0]}` del compose/Dockerfile)" if definidas else ""
        return valor, nota


def nombre_llamada(nodo: ast.AST) -> str:
    if isinstance(nodo, ast.Name):
        return nodo.id
    if isinstance(nodo, ast.Attribute):
        return f"{nombre_llamada(nodo.value)}.{nodo.attr}"
    return ""


# --- 4. Archivos de despliegue ----------------------------------------------------


def revisar_compose(app: Path, repo: Path, rep: Reporte, datos: dict) -> None:
    compose = app / "docker-compose.yml"
    otros = [n for n in ("docker-compose.yaml", "compose.yml", "compose.yaml") if (app / n).is_file()]
    if not compose.is_file():
        if otros:
            rep.error(f"El archivo debe llamarse exactamente `docker-compose.yml` (hay `{otros[0]}`): con otro nombre el despliegue no lo encuentra.")
        else:
            rep.error("Falta `docker-compose.yml`: sin él esta carpeta no se despliega (cópialo de `grupos/g01/semana01/derivadas1/`).")
        return
    texto = leer(compose)
    datos["compose"] = True

    variables = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", texto)) - VARS_AUTOMATICAS
    if variables:
        rep.para_admin(
            f"El compose interpola {', '.join('`${' + x + '}`' for x in sorted(variables))}. El despliegue solo pasa "
            "LAB_CONTAINER_NAME, LAB_PUBLIC_PATH y LAB_DOMAIN: para que lleguen hay que agregarlas a la lista blanca "
            "`_GROUP_ENV` de `lab_deploy/deployer.py` y definirlas en el `.env` de infraestructura."
        )
        rep.error(
            f"El compose usa {', '.join('`${' + x + '}`' for x in sorted(variables))}, pero el despliegue solo entrega "
            "`${LAB_CONTAINER_NAME}`, `${LAB_PUBLIC_PATH}` y `${LAB_DOMAIN}`. Cualquier otra variable llega vacía "
            "aunque exista en el servidor, hasta que el administrador la habilite. Nunca subas su valor al repo."
        )

    if yaml is None:
        rep.info("PyYAML no está instalado: el compose se revisó solo como texto (`pip install pyyaml` para la revisión completa).")
        if "${LAB_CONTAINER_NAME}" not in texto:
            rep.error("Falta `container_name: ${LAB_CONTAINER_NAME}` (tal cual, sin reemplazar a mano).")
        if "mem_limit" not in texto:
            rep.error("Falta `mem_limit` en el servicio.")
        if "lab_net" not in texto:
            rep.error("Falta la red externa `lab_net`.")
        return

    try:
        data = yaml.safe_load(texto) or {}
    except yaml.YAMLError as exc:
        rep.error(f"`docker-compose.yml` no es YAML válido: {str(exc).splitlines()[0]}")
        return
    servicios = data.get("services") or {}
    if not isinstance(servicios, dict) or not servicios:
        rep.error("El compose no define ningún servicio en `services:`.")
        return

    con_nombre_auto = 0
    for nombre, svc in servicios.items():
        svc = svc or {}
        mem = svc.get("mem_limit") or ((svc.get("deploy") or {}).get("resources", {}).get("limits", {}).get("memory"))
        if not mem:
            rep.error(f"Servicio `{nombre}`: falta `mem_limit` (el CI lo rechaza). Usa `mem_limit: 512m`.")
        else:
            mb = mem_a_mb(mem)
            if mb and mb > MEM_LIMIT_BASE_MB:
                rep.para_admin(f"El servicio `{nombre}` pide {mem} de memoria (más que los 512m habituales): confirmar que el servidor lo aguanta.")
        if svc.get("privileged") is True:
            rep.error(f"Servicio `{nombre}`: `privileged: true` no está permitido.")
        if svc.get("network_mode") == "host":
            rep.error(f"Servicio `{nombre}`: `network_mode: host` no está permitido.")
        if svc.get("pid") == "host":
            rep.error(f"Servicio `{nombre}`: `pid: host` no está permitido.")
        peligrosas = {str(c).upper() for c in (svc.get("cap_add") or [])} & {"SYS_ADMIN", "ALL", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE"}
        if peligrosas:
            rep.error(f"Servicio `{nombre}`: `cap_add` no permitido: {sorted(peligrosas)}.")
        if svc.get("devices"):
            rep.error(f"Servicio `{nombre}`: `devices` no está permitido.")
        for vol in svc.get("volumes") or []:
            origen = vol.get("source", "") if isinstance(vol, dict) else str(vol).split(":", 1)[0]
            es_bind = (isinstance(vol, dict) and vol.get("type") == "bind") or origen.startswith(("/", "./", "../", "~")) or origen == "."
            if es_bind:
                rep.error(f"Servicio `{nombre}`: el volumen `{vol}` monta una ruta del host. Solo se permiten volúmenes nombrados.")
            else:
                rep.para_admin(f"El servicio `{nombre}` usa el volumen nombrado `{origen}` (datos persistentes en el servidor).")
        if svc.get("env_file"):
            rep.error(f"Servicio `{nombre}`: usa `env_file`, pero los `.env` no se suben al repo, así que en el servidor no existirá. Pasa la configuración con `environment:` y pide los secretos al administrador.")

        cn = svc.get("container_name")
        if cn == "${LAB_CONTAINER_NAME}":
            con_nombre_auto += 1
        elif cn:
            rep.error(
                f"Servicio `{nombre}`: `container_name: {cn}` está escrito a mano. Debe ser literalmente "
                "`container_name: ${LAB_CONTAINER_NAME}`: el despliegue calcula el nombre desde la ruta de la carpeta."
            )

        for puerto in svc.get("ports") or []:
            if isinstance(puerto, dict):
                publica = puerto.get("published")
            else:
                publica = ":" in str(puerto)
            if publica:
                rep.error(
                    f"Servicio `{nombre}`: `ports: {puerto}` publica un puerto en el servidor y choca con otros grupos. "
                    "Quita `ports:` (o deja solo `- \"8000\"`): Caddy llega al contenedor por la red `lab_net`."
                )

        if svc.get("build") is None and svc.get("image"):
            rep.para_admin(f"El servicio `{nombre}` usa la imagen externa `{svc['image']}` (no se construye desde el repo).")
        elif svc.get("build") is None:
            rep.error(f"Servicio `{nombre}`: no tiene ni `build:` ni `image:`.")
        elif svc.get("build") not in (".", "./") and not isinstance(svc.get("build"), dict):
            rep.aviso(f"Servicio `{nombre}`: `build: {svc.get('build')}`; lo habitual es `build: .`.")

        if svc.get("restart") in ("no", False):
            datos["una_corrida"] = True
        elif svc.get("restart") is None:
            rep.aviso(f"Servicio `{nombre}`: sin `restart: unless-stopped` el servidor MCP no vuelve a levantarse si se cae o se reinicia la máquina.")
        entorno = svc.get("environment") or {}
        if isinstance(entorno, list):
            entorno = dict((str(e).split("=", 1) + [""])[:2] for e in entorno)
        datos["env_compose"].update(entorno.keys())
        datos["envv_compose"].update({str(k): "" if val is None else str(val) for k, val in entorno.items()})

    if con_nombre_auto == 0:
        rep.error("Ningún servicio tiene `container_name: ${LAB_CONTAINER_NAME}`: sin eso Caddy no encuentra el contenedor.")
    elif con_nombre_auto > 1:
        rep.error("Más de un servicio usa `container_name: ${LAB_CONTAINER_NAME}`: dos contenedores no pueden llamarse igual. Déjalo solo en el servidor MCP.")
    datos["sin_build"] = all((svc or {}).get("build") is None and (svc or {}).get("image") for svc in servicios.values())
    if len(servicios) > 1:
        rep.para_admin(f"El compose levanta {len(servicios)} servicios ({', '.join(servicios)}), no solo el servidor MCP.")

    red = ((data.get("networks") or {}).get("default") or {})
    if red.get("name") != "lab_net" or red.get("external") is not True:
        rep.error(
            "Falta la red externa `lab_net`. Copia este bloque al final del compose:\n"
            "      networks:\n        default:\n          name: lab_net\n          external: true"
        )
    else:
        if not any(s == rep.seccion and lvl == "ERROR" for s, lvl, _ in rep.items):
            rep.ok("`docker-compose.yml` cumple las reglas del despliegue.")


def revisar_dockerfile(app: Path, repo: Path, rep: Reporte, codigo: Codigo, datos: dict) -> None:
    dockerfile = app / "Dockerfile"
    if not dockerfile.is_file():
        if datos.get("compose"):
            rep.error("Falta `Dockerfile` (el compose usa `build: .`). Cópialo de `grupos/g01/semana01/derivadas1/` y ajusta la línea `COPY`.")
        else:
            rep.error("Falta `Dockerfile`: sin él no se puede construir la imagen.")
        return
    texto = leer(dockerfile)
    # Une las líneas partidas con "\" y descarta comentarios.
    lineas = [l.strip() for l in re.sub(r"\\\s*\n", " ", texto).splitlines() if l.strip() and not l.strip().startswith("#")]
    datos["dockerfile"] = texto

    froms = [l.split()[1] for l in lineas if l.upper().startswith("FROM ") and len(l.split()) > 1]
    if not froms:
        rep.error("El Dockerfile no tiene línea `FROM`.")
    elif not froms[-1].startswith("python:"):
        rep.aviso(f"La imagen base es `{froms[-1]}`; el patrón del laboratorio es `python:3.11-slim`.")
    elif "slim" not in froms[-1]:
        rep.aviso(f"Imagen base `{froms[-1]}`: usa la variante `-slim` (la completa pesa ~1 GB y alarga el build, que tiene {BUILD_MIN} minutos de límite).")

    if re.search(r"[A-Za-z]:\\\\?[A-Za-z]", texto):
        rep.error("El Dockerfile contiene una ruta de Windows (`C:\\...`). Dentro del contenedor todo es Linux.")

    tiene_req = (app / "requirements.txt").is_file()
    if tiene_req and not re.search(r"pip3?\s+install.*-r\s+\S*requirements\.txt", texto):
        rep.error("El Dockerfile no instala `requirements.txt` (falta `RUN pip install --no-cache-dir -r requirements.txt`).")

    fuentes_copy: list[str] = []
    for l in lineas:
        if l.upper().startswith(("COPY ", "ADD ")):
            args = [a for a in l.split()[1:] if not a.startswith("--")]
            if "--from=" in l:
                continue
            if args and args[0].startswith("["):
                try:
                    args = list(ast.literal_eval(" ".join(args)))
                except (ValueError, SyntaxError):
                    pass
            fuentes_copy.extend(a.rstrip("/").lstrip("./") or "." for a in args[:-1])
    copia_todo = "." in fuentes_copy
    datos["copia_todo"] = copia_todo

    def copiado(nombre: str) -> bool:
        limpio = nombre.rstrip("/")
        return copia_todo or any(fnmatch.fnmatch(limpio, f) or f == limpio for f in fuentes_copy)

    if tiene_req and not copiado("requirements.txt"):
        rep.error("El Dockerfile no copia `requirements.txt`.")
    server = app / "server.py"
    if server.is_file():
        faltan = sorted(m for m in codigo.modulos_locales_de(server) | {"server.py"} if not copiado(m))
        if faltan:
            rep.error(
                f"El Dockerfile no copia {', '.join('`' + f + '`' for f in faltan)}, que `server.py` necesita. "
                "En el contenedor fallará con `ModuleNotFoundError`. Agrégalos a la línea `COPY` "
                "(ej. `COPY server.py validacion.py matematica.py storage.py .`, y las carpetas como `COPY tools/ tools/`)."
            )
        else:
            rep.ok("El Dockerfile copia todos los módulos que usa `server.py`.")
    if copia_todo and not (app / ".dockerignore").is_file():
        rep.aviso("El Dockerfile hace `COPY . .` sin `.dockerignore`: mete en la imagen tests, caches y lo que haya en la carpeta. Copia solo lo necesario o agrega un `.dockerignore`.")

    arranque = [l for l in lineas if l.upper().startswith(("CMD", "ENTRYPOINT"))]
    if not arranque:
        rep.error("El Dockerfile no tiene `CMD`: el contenedor no sabe qué ejecutar. Usa `CMD [\"python\", \"server.py\"]`.")
    elif "server.py" not in arranque[-1] and server.is_file():
        rep.aviso(f"El `CMD` no arranca `server.py`: `{arranque[-1]}`.")
    for l in lineas:
        if not l.upper().startswith("ENV "):
            continue
        try:
            fichas = shlex.split(l[4:])
        except ValueError:
            fichas = l[4:].split()
        if fichas and "=" not in fichas[0] and len(fichas) > 1:
            datos["envv_docker"][fichas[0]] = " ".join(fichas[1:])
        else:
            datos["envv_docker"].update(f.split("=", 1) for f in fichas if "=" in f)
    datos["env_dockerfile"] = set(datos["envv_docker"])


def revisar_requirements(app: Path, repo: Path, rep: Reporte, codigo: Codigo) -> None:
    req = app / "requirements.txt"
    if not req.is_file():
        rep.error("Falta `requirements.txt` con las librerías que usa el código.")
        return
    declarados: dict[str, str] = {}
    for n, cruda in enumerate(leer(req).splitlines(), 1):
        linea = cruda.split("#", 1)[0].strip()
        if not linea:
            continue
        if linea.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$", linea)
        if not m or re.match(r"^(pip|pip3|python|py)\s", linea, re.I) or (m.group(3) and not re.match(r"^(==|>=|<=|~=|!=|<|>|@|;)", m.group(3))):
            rep.error(
                f"`requirements.txt` línea {n} no es válida: `{cruda.strip()}`. Va solo el nombre del paquete "
                "(y la versión), uno por línea: `mcp==2.1.1`, no un comando `pip install ...`."
            )
            continue
        nombre = normalizar_paquete(m.group(1))
        if nombre in declarados:
            rep.error(f"`requirements.txt` repite `{nombre}` (`{declarados[nombre]}` y `{linea}`): `pip install -r` falla con \"Double requirement given\". Deja una sola línea.")
        declarados[nombre] = linea

    provistos = set(declarados)
    for paquete in declarados:
        provistos |= {normalizar_paquete(p) for p in PAQUETE_PROVEE.get(paquete, ())}

    def falta(mod: str) -> str | None:
        paquete = normalizar_paquete(IMPORT_A_PAQUETE.get(mod, mod))
        if paquete.endswith("-*"):
            return None
        return None if (paquete in provistos or normalizar_paquete(mod) in provistos) else paquete

    faltan = {}
    for mod, archivos in codigo.terceros(solo_tests=False).items():
        paquete = falta(mod)
        if paquete:
            faltan[paquete] = (mod, archivos)
    for paquete, (mod, archivos) in sorted(faltan.items()):
        donde = ", ".join(sorted({a.name for a in archivos})[:3])
        rep.error(
            f"`requirements.txt` no incluye `{paquete}`, pero el código hace `import {mod}` ({donde}). "
            "En el contenedor fallará con `ModuleNotFoundError`."
        )
    solo_tests = sorted({falta(m) for m in codigo.terceros(solo_tests=True)} - {None} - set(faltan))
    if solo_tests:
        rep.info(f"Los tests usan {', '.join('`' + p + '`' for p in solo_tests)}, que no está en `requirements.txt`. Solo importa si quieres correr los tests dentro del contenedor.")
    if not faltan:
        rep.ok("`requirements.txt` cubre todas las librerías que importa el código.")

    usados = {normalizar_paquete(IMPORT_A_PAQUETE.get(m, m)) for solo in (False, True) for m in codigo.terceros(solo)}
    sobran = sorted(p for p in declarados if p not in usados and p not in {"uvicorn", "pytest", "mcp"})
    if sobran:
        rep.aviso(f"`requirements.txt` lista paquetes que ningún archivo importa ({', '.join(sobran)}): quítalos si no se usan, alargan el build.")

    imports = set()
    for py in codigo.archivos:
        imports |= codigo.imports_completos(py)
    if any(i == "fastmcp" or i.startswith("fastmcp.") for i in imports):
        rep.aviso(
            "El código importa el paquete `fastmcp` (un proyecto aparte del SDK oficial). El laboratorio usa el SDK "
            f"oficial: `from mcp.server.mcpserver import MCPServer` con `{MCP_PIN}`, como el piloto de g01."
        )
    if "mcp" not in declarados:
        if any(i == "mcp" or i.startswith("mcp.") for i in imports):
            return  # ya se reportó arriba como paquete faltante
        rep.aviso("`requirements.txt` no incluye `mcp`: ¿esta app es un servidor MCP?")
        return
    spec = declarados["mcp"]
    usa_v1 = any(i.startswith("mcp.server.fastmcp") for i in imports)
    usa_v2 = any(i.startswith("mcp.server.mcpserver") for i in imports)
    if usa_v1:
        rep.aviso(
            "El código importa `mcp.server.fastmcp` (SDK 1.x). El laboratorio usa la 2.x: "
            f"`from mcp.server.mcpserver import MCPServer` con `{MCP_PIN}`, como el piloto de g01."
        )
    if not re.search(r"==\s*\d", spec):
        rep.aviso(
            f"`{spec}` no fija la versión. Entre la 1.x y la 2.x del SDK cambian los imports, así que un "
            f"build futuro puede romperse solo. Usa `{MCP_PIN}` (la del piloto)."
        )
    elif usa_v2 and re.search(r"==\s*1\.", spec):
        rep.error(f"`{spec}` es la 1.x, pero el código importa `mcp.server.mcpserver`, que solo existe en la 2.x. Usa `{MCP_PIN}`.")


# --- 5. server.py y storage.py ----------------------------------------------------


def revisar_server(app: Path, repo: Path, grupo: str, tema: str, rep: Reporte, codigo: Codigo, datos: dict) -> None:
    server = app / "server.py"
    if not server.is_file():
        candidatos = sorted(p.name for p, f in codigo.fuentes.items() if re.search(r"\b(MCPServer|FastMCP)\(", f) and not codigo.es_test(p))
        pista = f" Parece que hoy es `{candidatos[0]}`: renómbralo a `server.py`." if candidatos else ""
        rep.error("Falta `server.py`: es el archivo que arranca el servidor MCP (el orquestador que define las tools)." + pista)
        return
    arbol = codigo.archivos.get(server)
    if arbol is None:
        return
    fuente = codigo.fuentes[server]

    res = Resolver(arbol, datos.get("env", {}))
    esperado = re.sub(r"[^a-z0-9]+", "-", f"{grupo}-{tema}".lower()).strip("-")

    def arg(llamada: ast.Call, clave: str) -> ast.AST | None:
        return next((k.value for k in llamada.keywords if k.arg == clave), None)

    # Nombre del servidor MCP: lo que ve quien se conecta. Debe identificar al
    # grupo y al proyecto, igual que el piloto se llama "g01-derivadas1".
    creaciones = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)
                  and nombre_llamada(n.func).split(".")[-1] in {"MCPServer", "FastMCP"}]
    if not creaciones:
        rep.error(f"`server.py` no crea el servidor. Debe tener `mcp = MCPServer(\"{esperado}\")`.")
    else:
        crea = creaciones[0]
        nombre, nota = res.resolver(crea.args[0] if crea.args else arg(crea, "name"))
        if not isinstance(nombre, str) or not nombre:
            rep.aviso(f"No pude determinar el nombre del servidor MCP en `server.py:{crea.lineno}`. Debe ser `{esperado}`: revísalo a mano.")
        elif grupo != "g01" and (nombre == PILOTO_NOMBRE or "derivadas1" in nombre or nombre.startswith("g01")):
            rep.error(f"`server.py:{crea.lineno}`: el servidor se llama `{nombre}`{nota}, que es el nombre del piloto. Cámbialo a `{esperado}`.")
        elif not nombre.lower().startswith(f"{grupo}-"):
            rep.error(
                f"`server.py:{crea.lineno}`: el servidor MCP se llama `{nombre}`{nota}. Debe llevar el grupo y el proyecto, "
                f"como el piloto (`{PILOTO_NOMBRE}`): `{esperado}`."
            )
        elif nombre != esperado:
            rep.aviso(f"`server.py:{crea.lineno}`: el servidor se llama `{nombre}`{nota}; para que coincida con la carpeta del proyecto debería ser `{esperado}`.")
        else:
            rep.ok(f"Nombre del servidor MCP: `{nombre}`.")
        if len(creaciones) > 1:
            rep.aviso(f"`server.py` crea el servidor {len(creaciones)} veces: parece código pegado dos veces. Deja una sola definición.")

    # Arranque: transporte, host y puerto (en `mcp.run(...)` o en el constructor).
    corridas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call) and nombre_llamada(n.func).endswith(".run")
                and not nombre_llamada(n.func).startswith(("subprocess", "asyncio", "uvicorn"))]
    if not corridas:
        rep.error("`server.py` nunca llama a `mcp.run(...)`: el contenedor arrancaría y terminaría sin servir nada.")
    else:
        transportes = []
        for c in corridas:
            nodo_t = arg(c, "transport") or (c.args[0] if c.args else None)
            valor_t, _ = res.resolver(nodo_t)
            transportes.append((c, nodo_t, valor_t))
        if any(t == "sse" for _, _, t in transportes):
            rep.error("`transport=\"sse\"` no funciona en este laboratorio (se queda colgado). Usa `transport=\"streamable-http\"`.")
        # Sirve una llamada con streamable-http, o una cuyo transporte no se
        # pudo resolver si el archivo al menos contempla streamable-http.
        http = [c for c, nodo_t, t in transportes if t == "streamable-http" or (nodo_t is not None and t is None and "streamable-http" in fuente)]
        if not http:
            rep.error(
                "`server.py` no arranca por HTTP. `mcp.run()` a secas usa stdio: sirve en tu laptop, pero en el "
                "contenedor no hay consola y termina al instante, y el despliegue lo da por fallido porque el "
                f"contenedor no queda corriendo (lo comprueba durante {SALUD_SEG} segundos). Debe ser:\n"
                f"      mcp.run(transport=\"streamable-http\", host=\"0.0.0.0\", port={PUERTO_MCP})"
            )
        else:
            llamada = http[-1]
            fuentes_kw = [llamada] + creaciones[:1]
            nodo_h = next((arg(c, "host") for c in fuentes_kw if arg(c, "host") is not None), None)
            nodo_p = next((arg(c, "port") for c in fuentes_kw if arg(c, "port") is not None), None)
            host, nota_h = res.resolver(nodo_h)
            puerto, nota_p = res.resolver(nodo_p)
            try:
                puerto = int(puerto) if puerto is not None else None
            except (TypeError, ValueError):
                puerto = None
            if nodo_h is None or host in ("127.0.0.1", "localhost"):
                rep.error(f"El servidor debe escuchar en `host=\"0.0.0.0\"`{nota_h}: con `127.0.0.1` (o sin host) Caddy no puede llegar al contenedor.")
            elif host is None:
                rep.aviso("No pude determinar en qué `host` escucha el servidor. En el contenedor debe ser `0.0.0.0`: revísalo a mano.")
            if nodo_p is None:
                rep.aviso(f"El servidor no indica `port={PUERTO_MCP}`; ponlo explícito.")
            elif puerto is None:
                rep.aviso(f"No pude determinar en qué puerto escucha el servidor. Debe ser {PUERTO_MCP}: revísalo a mano.")
            elif puerto != PUERTO_MCP:
                datos["puerto"] = puerto
                rep.aviso(f"El servidor escucha en el puerto {puerto}{nota_p}; el estándar del laboratorio es {PUERTO_MCP}. Si lo mantienes, avísale al administrador.")
            if host == "0.0.0.0" and puerto == PUERTO_MCP:
                rep.ok(f"Arranque correcto: streamable-http en 0.0.0.0:{PUERTO_MCP}.")
    if "__main__" not in fuente:
        rep.aviso("Falta `if __name__ == \"__main__\":` alrededor de `mcp.run(...)`: sin él, importar `server` (ej. desde un test) arranca el servidor.")

    # Tools y sus docstrings.
    tools = []
    for py, arb in codigo.archivos.items():
        if codigo.es_test(py):
            continue
        for nodo in ast.walk(arb):
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in nodo.decorator_list:
                    objetivo = dec.func if isinstance(dec, ast.Call) else dec
                    if nombre_llamada(objetivo).endswith(".tool"):
                        tools.append((nodo.name, bool(ast.get_docstring(nodo)), py))
    if not tools:
        rep.error("No hay ninguna tool (`@mcp.tool()`): un servidor MCP sin tools no ofrece nada.")
    else:
        sin_doc = [n for n, doc, _ in tools if not doc]
        if sin_doc:
            rep.error(
                f"Tools sin docstring: {', '.join('`' + n + '`' for n in sin_doc)}. El docstring es lo que lee la IA "
                "para saber qué hace la tool y en qué formato mandar los datos; sin él no la usa bien."
            )
        rep.info(f"Tools que expone el servidor ({len(tools)}): {', '.join(n for n, _, _ in tools)}.")
    datos["tools"] = [n for n, _, _ in tools]


def revisar_red_y_storage(app: Path, repo: Path, grupo: str, tema: str, rep: Reporte, codigo: Codigo, datos: dict) -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", f"{grupo}-{tema}".lower()).strip("-")
    bucket_sugerido = f"{slug}-imgs"

    # URLs y hosts en todo el código que corre (no tests).
    externos: dict[str, str] = {}
    vistos: set[tuple[str, str]] = set()
    libs_red = {"requests", "urllib", "httpx", "aiohttp", "socket", "http", "urllib3", "websockets"}
    for py in codigo.archivos:
        if codigo.es_test(py):
            continue
        hace_red = bool(codigo.imports(py) & libs_red)
        for cadena, linea in codigo.cadenas(py):
            for m in re.finditer(r"https?://([A-Za-z0-9.-]+)(?::(\d+))?", cadena):
                host, puerto = m.group(1).lower(), m.group(2)
                donde = f"{py.name}:{linea}"
                if (py.name, m.group(0)) in vistos:
                    continue
                vistos.add((py.name, m.group(0)))
                if host in HOSTS_SUBIDA_PUBLICA or any(host.endswith("." + h) for h in HOSTS_SUBIDA_PUBLICA):
                    rep.error(
                        f"`{donde}` sube archivos a `{host}`, un servicio público de terceros. Los resultados del "
                        f"laboratorio no salen del servidor: usa solo SeaweedFS (`{SEAWEEDFS_URL}`) y, si no responde, "
                        "devuelve `None` como hace el `storage.py` del piloto.",
                        siempre=True,
                    )
                elif host in HOSTS_LOCALES:
                    if py.name == "server.py" and host == "0.0.0.0":
                        continue
                    rep.aviso(
                        f"`{donde}` apunta a `{m.group(0)}`. Dentro del contenedor `localhost` es el propio contenedor, "
                        f"no el servidor: el storage se alcanza como `{SEAWEEDFS_URL}`."
                    )
                elif host == "seaweedfs":
                    if puerto != "8333":
                        rep.error(
                            f"`{donde}` usa `seaweedfs:{puerto or '80'}`. La ruta pública de imágenes está armada sobre la API S3, "
                            f"puerto 8333: usa `{SEAWEEDFS_URL}` como el piloto (con el filer 8888 las imágenes no se verán)."
                        )
                elif host not in HOSTS_INTERNOS and hace_red:
                    externos.setdefault(host, donde)
    if externos:
        lista = ", ".join(f"`{h}` ({d})" for h, d in sorted(externos.items()))
        rep.info(f"El código menciona servicios externos: {lista}. Si el servidor los llama, necesita salida a internet.")
        rep.para_admin(f"El código hace referencia a servicios externos: {', '.join(sorted(externos))}. Confirmar que el contenedor puede (y debe) salir a ellos.")

    # Restos del piloto: nombres de g01/derivadas1 copiados sin cambiar.
    if grupo != "g01":
        restos: list[str] = []
        for py in codigo.archivos:
            if py.name not in {"server.py", "storage.py"}:
                continue
            for cadena, linea in codigo.cadenas(py):
                ya_reportado = cadena in {PILOTO_NOMBRE, PILOTO_BUCKET} or "/img/derivadas1" in cadena
                if re.search(r"derivadas1|\bg01\b", cadena) and not ya_reportado:
                    restos.append(f"{py.name}:{linea}")
        for nombre_archivo in ("docker-compose.yml", "Dockerfile"):
            for n, linea_txt in enumerate(leer(app / nombre_archivo).splitlines(), 1):
                sin_comentario = linea_txt.split("#", 1)[0]
                if re.search(r"derivadas1|\bg01\b", sin_comentario):
                    restos.append(f"{nombre_archivo}:{n}")
        if restos:
            rep.error(
                "Quedan nombres del piloto (`g01` / `derivadas1`) sin cambiar en: " + ", ".join(sorted(set(restos)))
                + f". Cada grupo usa los suyos: `{grupo}` y el nombre de su proyecto."
            )

    # Variables de entorno que lee el código.
    variables: dict[str, bool] = {}
    for py, arb in codigo.archivos.items():
        if codigo.es_test(py):
            continue
        for nodo in ast.walk(arb):
            if isinstance(nodo, ast.Call) and nombre_llamada(nodo.func) in {"os.getenv", "os.environ.get", "environ.get", "getenv"}:
                if nodo.args and isinstance(nodo.args[0], ast.Constant):
                    variables[str(nodo.args[0].value)] = len(nodo.args) > 1 or bool(nodo.keywords)
            elif isinstance(nodo, ast.Subscript) and nombre_llamada(nodo.value) in {"os.environ", "environ"}:
                if isinstance(nodo.slice, ast.Constant):
                    variables[str(nodo.slice.value)] = False
    definidas = datos["env_compose"] | datos.get("env_dockerfile", set()) | VARS_AUTOMATICAS
    pendientes = sorted(v for v in variables if v not in definidas)
    obligatorias = [v for v in pendientes if not variables[v]]
    if obligatorias:
        rep.aviso(f"El código exige variables de entorno que ni el compose ni el Dockerfile definen: {', '.join(obligatorias)}. Sin ellas, falla al arrancar.")
    if pendientes:
        rep.para_admin(f"El código lee variables de entorno no definidas en el compose: {', '.join(pendientes)} (¿hay que configurarlas en el servidor?).")

    # Programas del sistema que el código ejecuta.
    binarios: dict[str, str] = {}
    for py, arb in codigo.archivos.items():
        if codigo.es_test(py):
            continue
        for nodo in ast.walk(arb):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = nombre_llamada(nodo.func)
            if nombre in {"subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_output", "subprocess.check_call", "os.system", "os.popen"} and nodo.args:
                arg = nodo.args[0]
                if isinstance(arg, (ast.List, ast.Tuple)) and arg.elts and isinstance(arg.elts[0], ast.Constant):
                    binarios.setdefault(str(arg.elts[0].value), f"{py.name}:{nodo.lineno}")
                elif isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.split():
                    binarios.setdefault(arg.value.split()[0], f"{py.name}:{nodo.lineno}")
    dockerfile = datos.get("dockerfile", "")
    for binario, donde in sorted(binarios.items()):
        base = Path(binario).name.lower()
        if base in BINARIOS_GUI:
            rep.aviso(f"`{donde}` ejecuta `{binario}` para abrir un archivo en el escritorio. En el servidor no hay escritorio: ese código no debe correr en el contenedor.")
        elif base.startswith("python"):
            continue
        else:
            instalado = re.search(r"(apt-get|apt|apk)\s+(install|add)", dockerfile)
            if not instalado:
                rep.error(
                    f"`{donde}` ejecuta el programa `{binario}`, que no existe en `python:3.11-slim`, y el Dockerfile no "
                    "instala nada con `apt-get`. Instálalo en el Dockerfile o quita esa dependencia."
                )
            rep.para_admin(
                f"La app necesita el programa de sistema `{binario}` dentro de su imagen. Si es pesado (ej. LaTeX), "
                f"el build puede superar el límite de {BUILD_MIN} minutos del despliegue."
            )

    # Escritura en disco.
    escribe = []
    for py, fuente in codigo.fuentes.items():
        if codigo.es_test(py):
            continue
        if re.search(r"savefig\(\s*[\"'fF]|open\([^)\n]*,\s*[\"'][wa]b?[\"']|\.write_(text|bytes)\(|\.mkdir\(", fuente):
            escribe.append(py.name)
    if escribe:
        rep.aviso(
            f"Parece que {', '.join('`' + e + '`' for e in sorted(set(escribe)))} guarda archivos en disco. El contenedor "
            "no conserva nada entre reinicios: genera en memoria (`io.BytesIO`) y sube el resultado con `storage.py`."
        )

    # storage.py
    storage = next((p for p in codigo.archivos if p.name == "storage.py"), None)
    usa_graficos = any(m in codigo.terceros(False) for m in ("matplotlib", "plotly", "PIL", "seaborn"))
    if storage is None:
        if usa_graficos:
            rep.aviso(
                "La app genera gráficos pero no tiene `storage.py`. Sin subir la imagen a SeaweedFS y devolver su URL, "
                "el cliente de chat no la muestra sola. Copia el `storage.py` del piloto y cambia bucket y URL."
            )
        return
    res = Resolver(codigo.archivos[storage], datos.get("env", {}))
    url_esperada = f"https://{DOMINIO}/img/{slug}"

    def constante(*claves: str) -> tuple[object, str, int] | None:
        for nombre_var, nodo in res.asign.items():
            if all(c in nombre_var.upper() for c in claves):
                valor, nota = res.resolver(nodo)
                return valor, nota, getattr(nodo, "lineno", 0)
        return None

    bucket = constante("BUCKET")
    publica = constante("PUBLIC", "URL")
    seaweed = constante("SEAWEED")
    es_piloto = grupo == "g01"
    bucket_ok = None

    if bucket is None or not isinstance(bucket[0], str):
        rep.aviso(f"No pude determinar el bucket en `storage.py`. Debe ser `IMG_BUCKET = \"{bucket_sugerido}\"`: revísalo a mano.")
    else:
        valor, nota, linea = bucket
        if not es_piloto and (valor == PILOTO_BUCKET or "derivadas1" in valor):
            rep.error(f"`storage.py:{linea}`: el bucket es `{valor}`{nota}, el del piloto de g01: sus imágenes se mezclarían con las de ustedes. Cámbialo a `{bucket_sugerido}`.")
        elif not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", valor):
            rep.error(f"`storage.py:{linea}`: el bucket `{valor}`{nota} no es un nombre S3 válido (solo minúsculas, dígitos y `-`, de 3 a 63 caracteres). Usa `{bucket_sugerido}`.")
        elif not es_piloto and not valor.startswith(f"{grupo}-"):
            rep.error(
                f"`storage.py:{linea}`: el bucket es `{valor}`{nota} y no lleva el nombre del grupo. Debe empezar con "
                f"`{grupo}-` para no chocar con otro grupo: `{bucket_sugerido}`."
            )
        else:
            bucket_ok = valor
            if not es_piloto and valor != bucket_sugerido:
                rep.aviso(f"`storage.py:{linea}`: el bucket es `{valor}`{nota}; para que coincida con la carpeta del proyecto debería ser `{bucket_sugerido}`.")

    if publica is None or not isinstance(publica[0], str):
        rep.aviso(f"No pude determinar `PUBLIC_IMG_BASE_URL` en `storage.py`. Debe ser `{url_esperada}`: revísalo a mano.")
    else:
        valor, nota, linea = publica
        m = re.fullmatch(rf"https://{re.escape(DOMINIO)}/img/([a-z0-9-]+)/?", valor)
        if not es_piloto and "derivadas1" in valor:
            rep.error(f"`storage.py:{linea}`: `PUBLIC_IMG_BASE_URL` es `{valor}`{nota}, la ruta del piloto. Cámbiala a `{url_esperada}`.")
        elif not m:
            rep.error(f"`storage.py:{linea}`: `PUBLIC_IMG_BASE_URL` es `{valor}`{nota} y no sirve en el servidor. Debe ser `{url_esperada}`.")
        elif not es_piloto and not m.group(1).startswith(f"{grupo}-"):
            rep.error(f"`storage.py:{linea}`: `PUBLIC_IMG_BASE_URL` es `{valor}`{nota} y no lleva el nombre del grupo. Debe ser `{url_esperada}`.")
        elif bucket_ok:
            if not es_piloto and bucket_ok != f"{m.group(1)}-imgs":
                rep.aviso(f"El bucket (`{bucket_ok}`) y la URL pública (`/img/{m.group(1)}`) no siguen el mismo nombre. Lo esperado: bucket `{m.group(1)}-imgs`.")
            rep.para_admin(
                f"Ruta pública de imágenes en Caddy (solo GET): `/img/{m.group(1)}/*` → bucket `{bucket_ok}` en `seaweedfs:8333` "
                "(mismo bloque que `/img/derivadas1/*`)."
            )
            rep.ok(f"Storage: bucket `{bucket_ok}`, URL pública `/img/{m.group(1)}`.")

    if seaweed is not None and isinstance(seaweed[0], str) and seaweed[0].rstrip("/") != SEAWEEDFS_URL and seaweed[1]:
        rep.error(f"`storage.py:{seaweed[2]}`: la URL del storage queda en `{seaweed[0]}`{seaweed[1]}. En el servidor debe ser `{SEAWEEDFS_URL}`.")
    fuente = codigo.fuentes[storage]
    if "seaweedfs" not in fuente:
        rep.error(f"`storage.py` no apunta a SeaweedFS. La URL interna es `{SEAWEEDFS_URL}` (el nombre `seaweedfs` se resuelve dentro de la red `lab_net`).")
    if "except" not in fuente:
        rep.aviso("`storage.py` no captura errores de red: si SeaweedFS no responde, la tool entera se cae. En el piloto `subir_imagen()` devuelve `None` y la tool sigue respondiendo.")
    if "timeout" not in fuente:
        rep.aviso("Las llamadas de `storage.py` no tienen `timeout`: si el storage se cuelga, la tool se queda esperando para siempre.")


# --- 6. Orquestación y reporte ----------------------------------------------------


def revisar_app(app: Path, repo: Path, grupo_dir: Path, rep: Reporte, nuevos: list[str]) -> dict:
    grupo = grupo_dir.name
    partes = app.relative_to(grupo_dir).parts
    ubicada = len(partes) == 2
    # Si está mal ubicada se revisa igual, como si ya estuviera en su sitio,
    # para que el grupo vea de una vez todo lo que tiene que corregir.
    semana, tema = partes if ubicada else ("proyecto01", re.sub(r"[^a-z0-9_-]+", "-", partes[-1].lower()).strip("-"))
    app_id = f"{grupo}_{semana}_{tema}"
    seccion = f"App `{rel(app, repo)}`"
    rep.en(seccion)
    datos = {"id": app_id, "compose": False, "env_compose": set(), "puerto": PUERTO_MCP, "dir": app,
             "ubicada": ubicada, "solo_imagen": False, "envv_compose": {}, "envv_docker": {}}

    codigo = Codigo(app, rep, repo)
    revisar_compose(app, repo, rep, datos)
    datos["solo_imagen"] = datos.get("sin_build", False) and not codigo.fuentes
    if datos.get("una_corrida") and (app / "server.py").is_file():
        rep.error(
            "El compose tiene `restart: \"no\"`, que el despliegue interpreta como un script de una sola corrida: "
            f"espera {SALUD_SEG} segundos a que termine y, como un servidor nunca termina, lo marca como fallido. "
            "Un servidor MCP lleva `restart: unless-stopped`."
        )
    if datos["solo_imagen"]:
        rep.info("Es una app ya hecha (imagen externa, sin código propio): no lleva Dockerfile, requirements.txt ni server.py.")
    else:
        revisar_dockerfile(app, repo, rep, codigo, datos)
        revisar_requirements(app, repo, rep, codigo)
        # Lo que vale en el contenedor: el compose pisa al Dockerfile.
        datos["env"] = {**datos["envv_docker"], **datos["envv_compose"]}
        pisadas = sorted(k for k in datos["envv_docker"] if k in datos["envv_compose"] and datos["envv_docker"][k] != datos["envv_compose"][k])
        if pisadas:
            rep.aviso(
                "El Dockerfile y el compose definen con valores distintos: " + ", ".join(f"`{k}`" for k in pisadas)
                + ". En el servidor gana el compose; deja un solo lugar para no confundirte."
            )
        revisar_server(app, repo, grupo, tema, rep, codigo, datos)
        revisar_red_y_storage(app, repo, grupo, tema, rep, codigo, datos)
    if not (datos["compose"] and ubicada):
        rep.degradar(seccion)
    datos["errores"] = sum(1 for s, lvl, _ in rep.items if s == seccion and lvl in ("ERROR", "FALTA"))

    if datos["solo_imagen"] and ubicada:
        ruta = f"/{grupo}/{app_id}"
        rep.para_admin(f"App de imagen externa `{app_id}`: si necesita ruta pública, en Caddy `handle {ruta}*` → `lab-{app_id}:<puerto de la app>`.")
    elif ubicada and datos["compose"] and NOMBRE_VALIDO.match(semana) and NOMBRE_VALIDO.match(tema):
        prefijo = rel(app, repo) + "/"
        es_nueva = any(n == prefijo + "docker-compose.yml" for n in nuevos)
        ruta = f"/{grupo}/{app_id}"
        rep.para_admin(
            f"{'App NUEVA' if es_nueva else 'App'} `{app_id}`: ruta en Caddy `handle {ruta}*` → "
            f"`reverse_proxy lab-{app_id}:{datos['puerto']}` (con `uri strip_prefix {ruta}`, sin login, igual que el piloto de g01)."
            + ("" if es_nueva else " Solo hace falta si todavía no existe o cambió el puerto.")
        )
        datos["url"] = f"https://{DOMINIO}{ruta}/mcp"
    return datos


def cosas_nuevas(nuevos: list[str], ignorados: set[str], rep: Reporte) -> None:
    """Lo que esta entrega agrega y no es lo de siempre: se le avisa al
    administrador para que sepa que hay algo distinto que mirar."""
    raras: dict[str, list[str]] = {}
    for ruta in nuevos:
        if ruta in ignorados:
            continue
        nombre = ruta.rsplit("/", 1)[-1]
        ext = Path(nombre).suffix.lower() if "." in nombre.lstrip(".") else ("" if not nombre.startswith(".") else nombre)
        if nombre in {"Dockerfile", "docker-compose.yml"} or ext in EXT_HABITUALES:
            continue
        raras.setdefault(ext or "(sin extensión)", []).append(ruta)
    if raras:
        detalle = "; ".join(f"{ext}: {len(rs)} (ej. `{rs[0]}`)" for ext, rs in sorted(raras.items()))
        rep.para_admin(f"Esta entrega agrega tipos de archivo fuera de lo habitual: {detalle}.")


def imprimir(rep: Reporte, grupo: str, apps: list[dict], repo: Path) -> int:
    marca = {"ERROR": "[ERROR]", "FALTA": "[FALTA]", "AVISO": "[AVISO]", "INFO": "[INFO] ", "OK": "[OK]   "}
    print(f"\nREVISIÓN DE ENTREGA: {grupo}\n" + "=" * 60)
    print("  [ERROR] bloquea el PR   [FALTA] falta para desplegar   [AVISO] conviene corregir")
    seccion = None
    for sec, nivel, texto in rep.items:
        if sec != seccion:
            seccion = sec
            print(f"\n## {sec}")
        print(f"  {marca[nivel]} {texto}")

    errores, faltas, avisos = rep.n("ERROR"), rep.n("FALTA"), rep.n("AVISO")
    print("\n" + "=" * 60 + "\n## ¿Qué se despliega si se fusiona este PR?\n")
    if not apps:
        print("  Nada: la entrega no tiene ninguna app (solo documentación).")
        print(f"  Para desplegar hace falta `grupos/{grupo}/<semana>/<tema>/` con docker-compose.yml,")
        print("  Dockerfile, requirements.txt y server.py (ver grupos/g01/semana01/derivadas1/).")
    completas = 0
    for a in apps:
        d = a["dir"]
        necesarios = ("docker-compose.yml",) if a["solo_imagen"] else ("docker-compose.yml", "Dockerfile", "requirements.txt", "server.py")
        faltan = [f for f in necesarios if not (d / f).is_file()]
        if not a["ubicada"]:
            extra = f" Además le falta: {', '.join(faltan)}." if faltan else ""
            print(f"  ✗ {rel(d, repo)}: NO despliega, está en una carpeta que el despliegue no mira.{extra}")
        elif faltan:
            print(f"  ✗ {a['id']}: NO despliega todavía. Le falta: {', '.join(faltan)}.")
        elif a["errores"]:
            print(f"  ✗ {a['id']}: tiene los archivos, pero {a['errores']} problema(s) impiden que funcione (ver arriba).")
        else:
            completas += 1
            print(f"  ✓ {a['id']}: completa. Contenedor `lab-{a['id']}`.")
            if a.get("url"):
                print(f"      URL del MCP cuando el administrador agregue la ruta: {a['url']}")

    print("\n## Veredicto\n")
    if errores:
        print(f"  NO SUBIR TODAVÍA: {errores} error(es) que bloquean el PR.")
        print("  Corrige los [ERROR] y vuelve a correr la revisión.")
    elif faltas:
        print("  SE PUEDE SUBIR COMO AVANCE, pero NO va a desplegar:")
        print(f"  quedan {faltas} pendiente(s) marcados [FALTA]. Dilo en la descripción del PR.")
    elif completas:
        print("  LISTO: se puede subir y va a desplegar.")
    else:
        print("  SE PUEDE SUBIR. No despliega nada porque no hay ninguna app.")
    if avisos:
        print(f"  Además hay {avisos} aviso(s) que conviene corregir.")

    print(f"\n## Mensaje para el administrador ({ADMIN})\n")
    if rep.admin:
        print("  Copia esto en la descripción del PR o envíaselo directamente:\n")
        print(f"  > {grupo}: para que nuestro despliegue funcione hace falta revisar en el repo de infraestructura:")
        for i, linea in enumerate(rep.admin, 1):
            print(f"  > {i}. {linea}")
    else:
        print("  Nada que pedirle en esta entrega.")
    print()
    return 1 if errores else 0


def detectar_grupo(repo: Path, base: str) -> str | None:
    _, rama = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    m = re.search(r"(grupo\d{2})", rama.lower())
    if m and (repo / "grupos" / m.group(1)).is_dir():
        return m.group(1)
    _, diff = git(repo, "diff", "--name-only", f"{base}...HEAD")
    grupos = {p.split("/")[1] for p in diff.splitlines() if p.startswith("grupos/") and p.count("/") >= 2}
    grupos -= NO_GRUPOS
    return grupos.pop() if len(grupos) == 1 else None


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")  # consola de Windows
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description="Revisa la entrega de un grupo antes del PR.")
    parser.add_argument("grupo", nargs="?", help="carpeta del grupo, ej. grupo04 (por defecto se deduce de la rama)")
    parser.add_argument("--base", default="origin/main", help="rama contra la que irá el PR (por defecto origin/main)")
    parser.add_argument("--repo", default=None, help="raíz del repo (por defecto, el repo actual)")
    args = parser.parse_args()

    inicio = Path(args.repo).resolve() if args.repo else Path.cwd()
    code, top = git(inicio, "rev-parse", "--show-toplevel")
    repo = Path(top) if code == 0 and top else inicio
    if not (repo / "grupos").is_dir():
        print("No se encontró la carpeta `grupos/`: ejecuta esto dentro del repo `lab`.", file=sys.stderr)
        return 2

    grupo = args.grupo or detectar_grupo(repo, args.base)
    if not grupo:
        disponibles = sorted(d.name for d in (repo / "grupos").iterdir() if d.is_dir() and d.name not in NO_GRUPOS)
        print("No pude deducir tu grupo por el nombre de la rama. Indícalo, ej.:", file=sys.stderr)
        print(f"  python {Path(__file__).as_posix()} grupo04\nGrupos: {', '.join(disponibles)}", file=sys.stderr)
        return 2
    grupo = grupo.strip("/").split("/")[-1]
    grupo_dir = repo / "grupos" / grupo
    if not grupo_dir.is_dir():
        print(f"No existe `grupos/{grupo}/`.", file=sys.stderr)
        return 2

    rep = Reporte()
    ctx = revisar_git(repo, grupo, args.base, rep)
    bien, mal = revisar_estructura(repo, grupo_dir, rep)
    apps = [revisar_app(app, repo, grupo_dir, rep, ctx["nuevos"]) for app in sorted(bien + mal)]
    cosas_nuevas(ctx["nuevos"], ctx["ignorados"], rep)
    return imprimir(rep, grupo, apps, repo)


if __name__ == "__main__":
    sys.exit(main())
