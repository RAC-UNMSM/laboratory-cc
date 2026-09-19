# TRABAJO CON RAMAS GRUPALES E INDIVIDUALES EN GIT

Por el momento, se nos indicó subir los cambios de una rama grupal, trabajando cada integrante desde una rama individual.

## 1. CLONAR LA RAMA GRUPAL

Lo primero que hacemos es clonar el repositorio utilizando la rama correspondiente a nuestro grupo:

```bash
git clone -b grupo04 --single-branch https://github.com/RAC-UNMSM/laboratory-cc.git
```

Este comando clona el repositorio y descarga específicamente la rama `grupo04` como rama de trabajo inicial.

Al ejecutar el comando, Git creará una carpeta llamada:

```text
laboratory-cc
```

dentro del directorio donde nos encontremos.

Por ejemplo:

```text
CARPETA DONDE EJECUTAMOS git clone
|
|---> laboratory-cc
      |
      |---> .git\
      |---> .github\
      |---> ci\
      |---> grupos\
      |---> templates\
      |---> README.md
      ...
```

La carpeta `.git` es la que contiene la información que permite a Git reconocer `laboratory-cc` como un repositorio.

### IMPORTANTE

Para ejecutar comandos Git relacionados con este repositorio debemos estar dentro de `laboratory-cc` o en alguno de sus subdirectorios.

Por ejemplo:

```text
C:\Users\User\Desktop\EJEMPLO\
|
|---> laboratory-cc\
      |
      |---> .git\
      |---> grupos\
      |---> templates\
```

Podemos ejecutar comandos Git desde:

```text
C:\Users\User\Desktop\EJEMPLO\laboratory-cc>
```

o desde:

```text
C:\Users\User\Desktop\EJEMPLO\laboratory-cc\grupos>
```

Pero no desde:

```text
C:\Users\User\Desktop\EJEMPLO>
```

porque ese directorio no pertenece al repositorio.

Si ejecutamos un comando Git fuera de un repositorio, podemos obtener un error como:

```text
fatal: not a git repository (or any of the parent directories): .git
```

---

# 2. COMPROBAR EN QUÉ RAMA ESTAMOS

Podemos utilizar:

```bash
git branch --show-current
```

Por ejemplo:

```text
C:\Users\User\Desktop\EJEMPLO\laboratory-cc>git branch --show-current
grupo04
```

También podemos utilizar:

```bash
git status
```

que además de mostrarnos la rama actual nos indica el estado de nuestros archivos.

---

# 3. MOSTRAR LAS RAMAS

Para mostrar las ramas locales podemos utilizar:

```bash
git branch
```

Por ejemplo:

```text
C:\Users\User\Desktop\EJEMPLO\laboratory-cc>git branch
* grupo04
```

El símbolo `*` indica la rama en la que estamos actualmente.

---

# 4. CREAR UNA NUEVA RAMA

Para crear una nueva rama y cambiar automáticamente a ella podemos utilizar:

```bash
git checkout -b nombre-de-la-rama
```

Por ejemplo:

```bash
git checkout -b grupo04-cristopher-catalan
```

Git mostrará:

```text
Switched to a new branch 'grupo04-cristopher-catalan'
```

También existe una alternativa más moderna y explícita:

```bash
git switch -c grupo04-cristopher-catalan
```

---

# 5. REALIZAR Y REGISTRAR CAMBIOS

Una vez que estamos en nuestra rama individual, podemos modificar, crear o eliminar archivos.

Por ejemplo, si se nos solicita crear un archivo `.md` con nuestro nombre y modificar el archivo de integrantes, realizamos esos cambios normalmente.

Después utilizamos:

```bash
git add .
```

Este comando coloca los cambios en el área de preparación (*staging*).

> IMPORTANTE: el espacio entre `add` y `.` es obligatorio.

Luego realizamos el commit:

```bash
git commit -m "Adicionado nombre de integrante"
```

El `commit` registra los cambios en nuestro repositorio **local**.

Finalmente, enviamos el commit al repositorio remoto:

```bash
git push -u origin grupo04-cristopher-catalan
```

El parámetro `-u` establece la relación entre nuestra rama local y la rama remota, por lo que posteriormente podremos utilizar simplemente:

```bash
git push
```

---

# ================================================================

# RUTA PARA REGISTRAR NUEVOS CAMBIOS

# ================================================================

## RAMA INDIVIDUAL

Partimos de la rama grupal:

```bash
git checkout grupo04
```

Creamos nuestra rama individual:

```bash
git checkout -b grupo04-cristopher-catalan
```

Podemos comprobar las ramas con:

```bash
git branch
```

Debería aparecer algo similar a:

```text
* grupo04-cristopher-catalan
  grupo04
```

El `*` indica que actualmente estamos trabajando en nuestra rama individual.

Realizamos nuestros cambios y posteriormente:

```bash
git add .
```

```bash
git commit -m "Adicionado nombre de integrante"
```

Finalmente:

```bash
git push -u origin grupo04-cristopher-catalan
```

De esta manera, nuestros cambios quedan publicados en nuestra rama individual del repositorio remoto.

---

# ================================================================

# RAMA GRUPAL

# ================================================================

Una vez que nuestros cambios están en la rama individual, podemos incorporarlos a la rama grupal.

Primero debemos asegurarnos de tener una versión actualizada de la rama grupal.

Podemos cambiar a nuestra rama individual:

```bash
git checkout grupo04-cristopher-catalan
```

Si tenemos cambios pendientes, primero debemos registrarlos:

```bash
git add .
```

```bash
git commit -m "Adicionado nombre de integrante"
```

Luego actualizamos la información del repositorio remoto:

```bash
git fetch origin
```

Después cambiamos a la rama grupal:

```bash
git checkout grupo04
```

Actualizamos nuestra rama grupal con los últimos cambios:

```bash
git pull origin grupo04
```

Ahora podemos incorporar los cambios de nuestra rama individual:

```bash
git merge grupo04-cristopher-catalan
```

Si el `merge` se realiza correctamente, finalmente enviamos la actualización de la rama grupal al repositorio remoto:

```bash
git push origin grupo04
```

Podemos comprobar las ramas locales con:

```bash
git branch
```

Por ejemplo:

```text
* grupo04
  grupo04-cristopher-catalan
```

El `*` indica que ahora estamos posicionados en la rama grupal.

---

# 6. ¿QUÉ HACE CADA COMANDO?

Una forma sencilla de recordar el flujo es:

```text
MODIFICAR ARCHIVOS
       |
       v
   git add .
       |
       v
git commit -m "..."
       |
       v
    git push
       |
       v
 REPOSITORIO REMOTO
```

### `git add .`

Prepara los cambios para ser incluidos en el próximo commit.

### `git commit -m "mensaje"`

Registra los cambios preparados en el repositorio local.

### `git push`

Envía nuestros commits locales al repositorio remoto, por ejemplo, GitHub.

### `git pull`

Descarga los cambios del repositorio remoto y los integra en nuestra rama local.

### `git merge`

Integra los cambios de una rama en otra.

---

# ================================================================

# ERRORES DE AUTENTICACIÓN

# ================================================================

Pueden aparecer diversos errores al intentar hacer `push`.

Uno de ellos puede ser:

```text
remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed for 'https://github.com/RAC-UNMSM/laboratory-cc.git/'
```

Este error está relacionado con la autenticación con GitHub.

También debemos verificar que:

* nuestra cuenta de GitHub sea la correcta;
* hayamos aceptado la invitación al repositorio;
* nuestra cuenta tenga los permisos necesarios para realizar `push`;
* estemos utilizando correctamente las credenciales de GitHub.

Actualmente, GitHub no permite utilizar la contraseña normal de la cuenta como autenticación para operaciones Git mediante HTTPS.

Una alternativa sencilla es utilizar GitHub CLI (`gh`).

---

# 7. INSTALAR GITHUB CLI EN WINDOWS

Si el comando:

```bash
gh auth login
```

produce:

```text
"gh" no se reconoce como un comando interno o externo,
programa o archivo por lotes ejecutable.
```

significa que GitHub CLI no está instalado o no está disponible en el `PATH`.

En Windows podemos instalarlo mediante `winget`:

```bash
winget install --id GitHub.cli
```

Por ejemplo:

```text
C:\Users\User\Desktop\EJEMPLO\laboratory-cc>winget install --id GitHub.cli
```

Durante la instalación, `winget` puede solicitar aceptar los términos de uso de la fuente correspondiente.

Una vez terminada la instalación, podemos comprobar que `gh` está disponible con:

```bash
gh --version
```

---

# 8. AUTENTICARSE CON GITHUB CLI

Una vez instalado GitHub CLI, ejecutamos:

```bash
gh auth login
```

Nos aparecerán varias preguntas.

Una configuración habitual es:

```text
? Where do you use GitHub? GitHub.com
? What is your preferred protocol for Git operations on this host? HTTPS
? Authenticate Git with your GitHub credentials? Yes
? How would you like to authenticate GitHub CLI? Login with a web browser
```

GitHub CLI mostrará un código de un solo uso, por ejemplo:

```text
! First copy your one-time code: XXXX-XXXX
Press Enter to open https://github.com/login/device in your browser...
```

Al completar correctamente el proceso, podemos obtener algo similar a:

```text
✓ Authentication complete.
- gh config set -h github.com git_protocol https
✓ Configured git protocol
✓ Logged in as cristopher-catalan
```

Después de autenticarnos correctamente y siempre que nuestra cuenta tenga permisos sobre el repositorio, podremos realizar operaciones como:

```bash
git push
```

para enviar nuestros commits.

---

# 9. CONSIDERACIÓN SOBRE MAYÚSCULAS Y MINÚSCULAS EN WINDOWS

En Windows, el sistema de archivos normalmente no distingue entre mayúsculas y minúsculas.

Por ejemplo, puede tratar:

```text
Carpeta
```

y:

```text
carpeta
```

como el mismo directorio.

Sin embargo, Git trabaja con repositorios que pueden utilizarse también en sistemas donde sí se distingue entre mayúsculas y minúsculas, como Linux.

Por ello, debemos evitar crear archivos o carpetas cuyos nombres se diferencien únicamente por mayúsculas y minúsculas.

---

# 10. RESUMEN DEL FLUJO

Para trabajar individualmente:

```bash
git checkout grupo04
git checkout -b grupo04-cristopher-catalan

# Realizar cambios

git add .
git commit -m "Adicionado nombre de integrante"
git push -u origin grupo04-cristopher-catalan
```

Para incorporar posteriormente los cambios a la rama grupal:

```bash
git checkout grupo04
git pull origin grupo04
git merge grupo04-cristopher-catalan
git push origin grupo04
```

En resumen:

```text
                RAMA GRUPAL
                  grupo04
                     |
                     | checkout -b
                     v
          RAMA INDIVIDUAL
       grupo04-cristopher-catalan
                     |
                     | modificar archivos
                     v
                  git add
                     |
                     v
                 git commit
                     |
                     v
                  git push
                     |
                     v
              GitHub / remoto
                     |
                     | merge
                     v
                grupo04
```

**IMPORTANTE:** antes de hacer `merge` hacia `grupo04`, debemos asegurarnos de tener la rama grupal actualizada para reducir la posibilidad de conflictos con los cambios realizados por otros integrantes.
