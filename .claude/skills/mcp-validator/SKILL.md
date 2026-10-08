---
name: mcp-validator
description: Revisa la entrega de un grupo del laboratorio antes de abrir o actualizar un PR contra main. Úsala cuando un alumno diga "revisa mi entrega", "voy a subir mi PR", "actualicé mi rama", "¿está listo para desplegar?", "¿por qué no despliega?", o pida validar su carpeta grupos/grupoNN, su docker-compose.yml, Dockerfile, requirements.txt, server.py o storage.py. Detecta lo que no debe subirse (entornos virtuales, binarios, archivos fuera de su carpeta), dice qué falta para que la app despliegue y arma el mensaje con lo que el administrador debe configurar en el servidor.
---

# Revisar la entrega de un grupo

Estás ayudando a un alumno del laboratorio (repo `lab`, curso de MCP) a dejar
su carpeta `grupos/grupoNN/` lista para un PR contra `main`. Solo el profesor
fusiona a `main`; al hacerlo, GitHub avisa por webhook al servidor, que
descarga `main` y levanta cada app que cambió. El alumno no ve ese servidor:
lo que no cumpla el contrato de abajo simplemente no despliega, y él no sabrá
por qué.

El objetivo es uno: decirle al alumno **si lo que tiene en su rama va a subir
bien y a desplegar, y si no, qué le falta exactamente**. Para eso respondes
tres cosas, en este orden:

1. **¿Hay algo que no debe subirse, o cambios fuera de su carpeta?**
2. **¿Va a desplegar? Si no, ¿qué falta exactamente?**
3. **¿Qué tiene que pedirle al administrador (Julios Castillo Melchor)?**

Lo que tiene que cumplir toda entrega:

- **Todo el proyecto dentro de su carpeta:**
  `grupos/grupoNN/proyecto01/<nombre-del-proyecto>/`. Nada del proyecto suelto
  en `grupos/grupoNN/` ni en `proyecto01/`.
- **Nada fuera de `grupos/grupoNN/`.** Si la rama toca la raíz, `.github/`,
  `ci/` o la carpeta de otro grupo, se le avisa y se deshace.
- **Los cuatro archivos de despliegue, bien armados:** `docker-compose.yml`,
  `Dockerfile`, `requirements.txt` (con lo que el grupo usa de verdad, ni más
  ni menos) y `server.py`. `storage.py` si genera imágenes o archivos.
- **Sus propios nombres en `server.py` y `storage.py`.** El piloto se llama
  `g01-derivadas1` porque es del grupo `g01` y su proyecto es `derivadas1`.
  Cada grupo pone los suyos, con su grupo y el nombre de su carpeta:

  | Dónde | Piloto | Grupo `grupo04`, carpeta `interpolacion` |
  |---|---|---|
  | `server.py`: `MCPServer(...)` | `g01-derivadas1` | `grupo04-interpolacion` |
  | `storage.py`: `IMG_BUCKET` | `derivadas1-imgs` | `grupo04-interpolacion-imgs` |
  | `storage.py`: `PUBLIC_IMG_BASE_URL` | `.../img/derivadas1` | `.../img/grupo04-interpolacion` |

  Que quede `g01` o `derivadas1` en esos archivos es error: significa que se
  copió el piloto sin renombrar.

Responde siempre en español y en lenguaje llano: muchos alumnos usan git y
Docker por primera vez.

## Paso 1: correr el validador

Desde la raíz del repo:

```bash
git fetch origin
python .claude/skills/mcp-validator/scripts/validar_entrega.py grupoNN
```

- En Linux/macOS puede ser `python3`. No necesita instalar nada.
- Si no sabes el grupo, míralo en el nombre de la rama (`git branch --show-current`)
  o pregúntale al alumno. Nunca lo adivines.
- `git fetch` solo descarga; no cambia sus archivos. Hazlo siempre, porque el
  validador compara contra `origin/main`.

El validador marca cada hallazgo así:

| Marca | Significa |
|---|---|
| `[ERROR]` | Bloquea el PR. No debe subirse hasta corregirlo. |
| `[FALTA]` | Lo que le falta a la app para desplegar. Se puede subir como avance, pero no desplegará. |
| `[AVISO]` | Conviene corregirlo; no bloquea. |
| `[INFO]` / `[OK]` | Contexto y lo que ya está bien. |

Al final imprime **qué se despliega**, el **veredicto** y el **mensaje para el
administrador**.

## Paso 2: leer lo que el validador no puede juzgar

El validador revisa forma, no sentido. Lee tú **solo `server.py` y
`storage.py`** de cada app (`grupos/grupoNN/<semana>/<tema>/`) y compáralos
con los del piloto `grupos/g01/semana01/derivadas1/`, que es el ejemplo a
imitar. No revises la parte matemática ni el resto de módulos: si el cálculo
es correcto lo evalúa el profesor, no esta revisión.

- **`server.py`**: debe ser solo el orquestador (define las tools y llama a
  los otros módulos). Revisa que el docstring de cada tool diga qué formato
  de entrada espera, con ejemplos: es lo único que lee la IA para usarla.
  Revisa que el *resultado* de la tool no traiga órdenes ("debes mostrar
  esto"): eso tiene forma de prompt injection; las indicaciones van en el
  docstring.
- **`storage.py`**: bucket y URL pública propios del grupo, nunca los del
  piloto; que falle en silencio (devuelva `None`) si el storage no responde.

Qué cambia y qué no respecto del piloto está en
[referencia-despliegue.md](referencia-despliegue.md). Léelo antes de proponer
correcciones a los archivos de despliegue.

## Paso 3: explicar y corregir

Presenta el resultado así:

1. **Veredicto en una frase**: no subir todavía / se puede subir como avance
   pero no despliega / listo y despliega.
2. **Lo que bloquea** (`[ERROR]`), cada uno con el comando o cambio exacto.
3. **Lo que falta para desplegar** (`[FALTA]`), en orden de trabajo.
4. **Avisos**, agrupados y breves.
5. **Mensaje para el administrador**, tal cual lo imprime el validador, más
   lo que hayas detectado tú en el paso 2.

Ofrece corregir tú lo que sea mecánico (compose, Dockerfile,
`requirements.txt`, nombres, `git rm --cached`). Después de corregir, vuelve
a correr el validador y muestra el veredicto nuevo.

### Recetas frecuentes

**Entorno virtual o caches ya subidos** (el `.gitignore` no quita lo que ya
está en git). `--cached` los saca del repo sin borrarlos del disco:

```bash
git rm -r --cached grupos/grupoNN/<ruta-del-venv>
git commit -m "Quitar entorno virtual del repo"
```

**Rama atrasada respecto de main**:

```bash
git fetch origin
git merge origin/main
```

**Archivo fuera de la carpeta del grupo** (creado, modificado o borrado por
error). Para dejarlo como está en `main`:

```bash
git checkout origin/main -- <archivo>     # si existe en main
git rm <archivo>                          # si lo creó el alumno y no debe existir
```

**Carpeta en el nivel equivocado o con mayúsculas/espacios**:

```bash
git mv "grupos/grupoNN/MI-APP" grupos/grupoNN/proyecto01/mi-app
```

## Límites: qué no hacer

- **No toques nada fuera de `grupos/grupoNN/` del alumno**: ni `.github/`, ni
  `ci/`, ni el `.gitignore` de la raíz, ni la carpeta de otro grupo.
- **No hagas `git push`, ni abras o fusiones PRs, sin que el alumno lo pida.**
  Tampoco `push --force` ni reescribir historial de la rama `grupoNN`: es
  compartida por todo el grupo.
- **No inventes infraestructura.** Si la app necesita algo que no sea el
  servidor MCP en el puerto 8000 más SeaweedFS (una base de datos, otro
  servicio, un token, más memoria, un programa del sistema, salida a internet,
  un puerto distinto), no lo resuelvas por tu cuenta: agrégalo al mensaje para
  el administrador y dile al alumno que el despliegue no funcionará hasta que
  él lo configure.
- **Nunca subas secretos** (tokens, contraseñas, `.env`). Si el código
  necesita uno, se pide al administrador y se lee con `os.getenv`.
- **No copies código del piloto cambiándole el nombre.** Se copia el patrón
  (un módulo por rol, `server.py` como orquestador), no el tema.

## El `.gitignore`: lo local nunca se sube

El validador recorre la carpeta del grupo buscando lo que se instala o se
genera en la laptop: entornos virtuales con cualquier nombre, `node_modules`,
librerías instaladas con pip, caches, instaladores, comprimidos, modelos
entrenados, bases de datos locales, `.env`, archivos de más de 5 MB. Para cada
cosa comprueba si el `.gitignore` la cubre.

- **Cubierto:** no hay nada que hacer.
- **Cubierto solo por el `.gitignore` de `main`:** la rama está atrasada; se
  arregla con `git merge origin/main`.
- **Sin cubrir:** es error, porque un `git add .` lo subiría. El alumno agrega
  el patrón a **`grupos/grupoNN/.gitignore`** (el suyo). El de la raíz no lo
  toca: el validador le pasa esos patrones al administrador para que los
  agregue al general.

Lo mismo aplica a lo que la rama haya tocado fuera de `grupos/grupoNN/`: si es
algo generado o local, se le dice al administrador qué patrón falta; si es un
cambio real a un archivo del repo, se deshace.

## Cuándo avisar al administrador

Cada grupo hace algo distinto, así que el servidor no puede adivinarlo. El
alumno debe avisar a **Julios Castillo Melchor** (en la descripción del PR)
siempre que la entrega incluya algo de esta lista. El validador detecta la
mayoría; tú completa lo que veas al leer el código:

- Una app nueva (hay que crear su ruta pública en Caddy).
- Imágenes o archivos generados (hay que crear la ruta `/img/...` de su bucket).
- Un puerto distinto de 8000, o más de un servicio en el compose.
- Variables de entorno, tokens o claves de API. El despliegue solo entrega al
  compose `LAB_CONTAINER_NAME`, `LAB_PUBLIC_PATH` y `LAB_DOMAIN`; cualquier
  otra `${VAR}` llega vacía hasta que él la habilite.
- Una app eliminada o una carpeta renombrada: el contenedor anterior sigue
  corriendo hasta que él lo baje a mano.
- Volúmenes (datos que deben sobrevivir a un reinicio) o más de 512 MB de memoria.
- Programas del sistema instalados con `apt-get` (LaTeX, ffmpeg…): imagen
  pesada, y el build tiene un límite de 15 minutos.
- **Algo que haya que instalar o configurar en el servidor.** El servidor solo
  ofrece SeaweedFS. Si el proyecto usa una base de datos (PostgreSQL, MongoDB,
  Redis…), un modelo o una API de IA (OpenAI, Anthropic, Ollama…) u otro
  servicio, no funcionará hasta que el administrador lo instale y le pase la
  conexión. El validador lo deduce de `requirements.txt`.
- Librerías muy pesadas (torch, tensorflow, opencv…): disco, tiempo de build y
  memoria.
- Llamadas a servicios externos de internet.
- Cualquier tipo de archivo o carpeta que no sea código, documentación o los
  archivos de despliegue.
