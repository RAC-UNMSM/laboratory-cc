---
name: revisar-entrega
description: Revisa la entrega de un grupo del laboratorio antes de abrir o actualizar un PR contra main. Úsala cuando un alumno diga "revisa mi entrega", "voy a subir mi PR", "actualicé mi rama", "¿está listo para desplegar?", "¿por qué no despliega?", o pida validar su carpeta grupos/grupoNN, su docker-compose.yml, Dockerfile, requirements.txt, server.py o storage.py. Detecta lo que no debe subirse (entornos virtuales, binarios, archivos fuera de su carpeta), dice qué falta para que la app despliegue y arma el mensaje con lo que el administrador debe configurar en el servidor.
---

# Revisar la entrega de un grupo

Estás ayudando a un alumno del laboratorio (repo `lab`, curso de MCP) a dejar
su carpeta `grupos/grupoNN/` lista para un PR contra `main`. Al fusionarse, un
agente de despliegue toma lo que haya en `main` y levanta cada app en el
servidor del profesor. El alumno no ve ese servidor: lo que no cumpla el
contrato de abajo simplemente no despliega, y él no sabrá por qué.

Tu trabajo es responder tres cosas, en este orden:

1. **¿Hay algo que no debe subirse?**
2. **¿Va a desplegar? Si no, ¿qué falta exactamente?**
3. **¿Qué tiene que pedirle al administrador (Julios Castillo Melchor)?**

Responde siempre en español y en lenguaje llano: muchos alumnos usan git y
Docker por primera vez.

## Paso 1: correr el validador

Desde la raíz del repo:

```bash
git fetch origin
python .claude/skills/revisar-entrega/scripts/validar_entrega.py grupoNN
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

El validador revisa forma, no sentido. Lee tú estos archivos de cada app
(`grupos/grupoNN/<semana>/<tema>/`) y compáralos con el piloto
`grupos/g01/semana01/derivadas1/`, que es el ejemplo a imitar:

- **`server.py`**: debe ser solo el orquestador (define las tools y llama a
  los otros módulos). Revisa que el docstring de cada tool diga qué formato
  de entrada espera, con ejemplos: es lo único que lee la IA para usarla.
  Revisa que el *resultado* de la tool no traiga órdenes ("debes mostrar
  esto"): eso tiene forma de prompt injection; las indicaciones van en el
  docstring.
- **`storage.py`**: bucket y URL pública propios del grupo, nunca los del
  piloto; que falle en silencio (devuelva `None`) si el storage no responde.
- **Módulo de cálculo**: sin llamadas de red ni archivos; debe poder
  probarse sin levantar el servidor.
- **Entradas**: que se validen antes de calcular y que el error sea legible.

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

## Cuándo avisar al administrador

Cada grupo hace algo distinto, así que el servidor no puede adivinarlo. El
alumno debe avisar a **Julios Castillo Melchor** (en la descripción del PR)
siempre que la entrega incluya algo de esta lista. El validador detecta la
mayoría; tú completa lo que veas al leer el código:

- Una app nueva o una carpeta de tema renombrada (hay que crear su ruta pública).
- Imágenes o archivos generados (hay que crear la ruta `/img/...` de su bucket).
- Un puerto distinto de 8000, o más de un servicio en el compose.
- Variables de entorno, tokens o claves de API.
- Volúmenes (datos que deben sobrevivir a un reinicio) o más de 512 MB de memoria.
- Programas del sistema instalados con `apt-get` (LaTeX, ffmpeg…): imagen
  pesada, y el build tiene un límite de 5 minutos.
- Llamadas a servicios externos de internet.
- Cualquier tipo de archivo o carpeta que no sea código, documentación o los
  archivos de despliegue.
