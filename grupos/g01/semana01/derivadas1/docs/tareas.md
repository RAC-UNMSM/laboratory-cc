# Tareas sobre derivadas1

Antes de tocar código, lean [`README.md`](./README.md) de esta carpeta:
explica cómo está dividido el proyecto y por qué.

Estas tareas están pensadas para que cada quien practique sobre **su rol**
tocando solo su archivo, y para que el grupo practique el flujo completo
(PR, revisión, entender un módulo que no escribiste) antes de construir el
servidor MCP propio con el tema que les toque.

## 0. Levantar el proyecto en local (todos)

1. `pip install -r requirements.txt` (usen un virtualenv).
2. Corran `python server.py` — el servidor queda escuchando en
   `http://localhost:8000` con `transport="streamable-http"`.
3. Prueben la tool `derivar` con un cliente MCP (ej. MCP Inspector, o Claude
   Code apuntando a ese endpoint) mandando expresiones como `"x**2 + 3*x"`,
   `"sin(x)"`, `"exp(x)*x"`.
4. **Ojo**: `storage.py` va a intentar subir la imagen a un SeaweedFS que en
   local no existe. Va a fallar en silencio (`subir_imagen` devuelve `None`)
   y el gráfico igual les va a llegar como `ImageContent` — no hace falta
   levantar SeaweedFS para probar el resto.

## 1. Rol "Validación de entradas" (`validacion.py`)

- Agreguen una validación de que `expresion` no esté vacía, con su propio
  `ValidationError` y mensaje.
- Agreguen un límite razonable al rango (ej. `x_max - x_min` no puede ser
  mayor a un valor fijo) para evitar gráficos con un dominio absurdo.
- Escriban 3-4 casos de prueba a mano (válidos e inválidos) y verifiquen a
  ojo que el mensaje de error tenga sentido para alguien que no leyó el
  código.

## 2. Rol "Lógica matemática" (`matematica.py`)

- Agreguen una función `derivar_segunda(f)` que calcule la segunda derivada
  (pista: `sp.diff(f, x, 2)` o derivar dos veces).
- Extiendan `evaluar_numerico` para que también devuelva los valores de la
  segunda derivada.
- Como este módulo no tiene I/O, escriban un test con `assert` comparando
  `derivar_simbolico(sp.sympify("x**2"))` contra el resultado esperado
  (`2*x`), sin necesidad de levantar el servidor.

## 3. Rol "Visualización" (`visualizacion.py`)

- Agreguen la segunda derivada como una tercera curva en el mismo gráfico
  (una vez que el rol de matemática la exponga).
- Marquen en el gráfico los puntos donde `f'(x) = 0` (candidatos a máximo o
  mínimo) — pueden usar `np.where` sobre un cambio de signo en `dys`.
- Prueben qué pasa si `ys` o `dys` tienen `NaN` (ej. con `"1/x"` en un rango
  que cruza el 0) y decidan cómo se debería ver el gráfico en ese caso.

## 4. Rol "Storage/infra" (`storage.py`)

- Sin depender de SeaweedFS real: agreguen un `try/except` de prueba que
  simule que `urlopen` tira timeout, y verifiquen que `derivar()` en
  `server.py` sigue respondiendo bien (sin el link, pero sin caerse).
- Lean `docker-compose.yml` y `Dockerfile` y expliquen con sus palabras, en
  un comentario o en un README propio, qué hace `container_name:
  ${LAB_CONTAINER_NAME}` y por qué no se reemplaza a mano (ver
  `grupos/TEMPLATE/README.md` del repo, punto 4).

## 5. Orquestador (`server.py`) — para quien conecte todo

- Una vez que los otros roles agreguen la segunda derivada, actualicen
  `derivar()` para que la incluya en el texto de resumen.
- Relean el comentario sobre por qué la URL del storage se agrega como
  "un dato más" y no como una instrucción imperativa, y expliquen esa idea
  al resto del grupo con sus propias palabras (es el punto más importante
  de seguridad del proyecto).

## 6. De este piloto a su propio proyecto más grande

Cuando les toque construir su propio servidor MCP (con el tema que les
asignen, no derivadas), repliquen **el patrón**, no el tema:

1. Un módulo por rol, y `server.py` (o como lo llamen) como orquestador que
   no tiene lógica propia — solo conecta piezas.
2. El rol de lógica de negocio (equivalente a `matematica.py` acá) sin I/O,
   para poder testearlo sin levantar el servidor completo.
3. Su carpeta real va en `grupos/grupoNN/semanaNN/<tema>/` (no en `g01/`,
   esa es solo la del profesor) — sigan `grupos/TEMPLATE/README.md` para la
   estructura y las reglas obligatorias del `docker-compose.yml`:
   `mem_limit`, sin `privileged`/`network_mode: host`, solo volúmenes
   nombrados, `container_name: ${LAB_CONTAINER_NAME}` tal cual, red externa
   `lab_net`.
4. Abren PR contra `main` del repo del curso — el CI valida las reglas del
   `docker-compose.yml` y hace un dev-run efímero; el profesor revisa y
   mergea. El despliegue real es automático después del merge, nadie del
   grupo lo dispara a mano.

### 6.1 Archivo por archivo: qué copiar tal cual, qué editar y qué reescribir

Los 7 archivos de este piloto no se tratan todos igual al pasar a un
proyecto real. Se dividen en tres niveles según cuánto de "derivadas1"
queda adentro:

#### Nivel 1 — Tal cual (boilerplate fijo del curso, no se inventa nada nuevo)

- **`Dockerfile`**: se copia con la misma estructura exacta:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY server.py validacion.py matematica.py visualizacion.py storage.py .
  CMD ["python", "server.py"]
  ```
  Lo único que cambia es la lista de nombres en la línea `COPY` si el grupo
  nombra sus módulos de rol distinto (ej. `procesamiento.py` en vez de
  `matematica.py`). La imagen base (`python:3.11-slim`), el orden de capas
  (requirements antes que el código, para aprovechar la cache de Docker) y
  el `CMD` se mantienen siempre.

- **`docker-compose.yml`**: esto **no es una sugerencia, lo valida el CI**
  (`ci/compose_policy.py`). Se copia el esqueleto completo y solo se
  decide el nombre del servicio y el valor de `mem_limit`:
  ```yaml
  services:
    <tema>:
      build: .
      container_name: ${LAB_CONTAINER_NAME}   # NUNCA se reemplaza a mano
      restart: unless-stopped
      mem_limit: 512m                          # ajustable según el stack

  networks:
    default:
      name: lab_net
      external: true
  ```
  `container_name: ${LAB_CONTAINER_NAME}` y el bloque `networks:` se copian
  literal, palabra por palabra. Prohibido agregar `ports:`,
  `privileged: true`, `network_mode: host`, `pid: host`, `cap_add`
  peligroso, o bind-mounts al host (`./algo:/algo`, `/ruta:/algo`) — solo
  volúmenes nombrados si hace falta persistencia.

#### Nivel 2 — Se edita (mismo esqueleto, cambian constantes o nombres puntuales)

- **`storage.py`**: la lógica completa (`ensure_bucket`, `subir_imagen`,
  fallar en silencio si SeaweedFS no responde, key random con `uuid4`) es
  genérica y se copia casi entera — es infraestructura compartida del lab,
  no algo específico de derivadas. Solo cambian estas constantes
  (líneas 18-23 en este piloto):
  ```python
  SEAWEEDFS_S3_URL = "http://seaweedfs:8333"   # queda igual, infra del lab
  IMG_BUCKET = "derivadas1-imgs"                # → nombre único del bucket del grupo/tema
  PUBLIC_IMG_BASE_URL = "https://rac-unmsm.vekthos.org/img/derivadas1"  # → ruta que asigne el profesor en Caddy
  ```
  Si el resultado de la tool del grupo no es una imagen (texto, JSON,
  video, etc.), el *contenido* de este módulo cambia para subir ese tipo de
  dato, pero el *patrón* se mantiene: subir a un storage compartido →
  devolver una URL pública → nunca romper el flujo principal si el storage
  falla.

- **`requirements.txt`**: se reescribe con las librerías del tema del
  grupo, pero siempre con `mcp==2.1.1` (o la versión que fije el curso) como
  base. `sympy`, `numpy` y `matplotlib` son específicas de este piloto
  (matemática con gráficos) y no se copian si el tema no las necesita.

- **`server.py` (el orquestador)**: la *estructura* es fija — un
  `MCPServer(...)`, uno o más `@mcp.tool()` que solo llaman a los módulos
  de rol, y el bloque final de arranque — pero el *contenido* se reescribe
  por completo para el tema nuevo:
  - `MCPServer("g01-derivadas1")` → `MCPServer("grupoNN-<tema>")`.
  - La firma y el **docstring** de cada `@mcp.tool()` según la tool real
    del grupo — este es el cambio más importante de reescribir bien, porque
    es lo que la IA lee para saber cómo llamar la tool (ver la sección
    "Dos detalles no obvios" en `README.md`).
  - Las llamadas a los módulos de rol (nombres de función, número de pasos)
    según cómo el grupo divida su propia lógica.
  - Lo que **no** cambia: la idea de que este archivo no tiene lógica
    propia, solo conecta piezas; y el bloque de arranque
    `mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)` —
    ese transporte es requisito para que Caddy pueda exponer el servidor
    con una URL pública (no usar `stdio` ni `sse`).

#### Nivel 3 — Se reescribe entero (nada que copiar, solo el patrón)

- **`validacion.py`**, **`matematica.py`** (el rol de lógica de negocio) y
  **`visualizacion.py`** (si el tema produce gráficos) son 100%
  específicos de derivadas. Para un tema distinto son módulos nuevos con
  contenido nuevo de cero. Lo único que se replica de acá es el *patrón*:
  un módulo por rol, con el rol de lógica de negocio sin I/O ni llamadas de
  red (para poder testearlo con `assert` normal sin levantar el servidor
  completo), y cada módulo enfocado en una sola responsabilidad.

#### Resumen en una tabla

| Archivo | Nivel | Qué cambia |
|---|---|---|
| `Dockerfile` | 1 — tal cual | Nada, salvo la lista de módulos en `COPY` si cambian de nombre |
| `docker-compose.yml` | 1 — tal cual | Nombre del servicio y `mem_limit`; el resto es obligatorio y fijo |
| `storage.py` | 2 — se edita | 2-3 constantes (`IMG_BUCKET`, `PUBLIC_IMG_BASE_URL`); la lógica se mantiene |
| `requirements.txt` | 2 — se edita | Librerías del tema, siempre con `mcp` como base |
| `server.py` | 2 — se edita | Nombre del server, tool(s), docstring(s), llamadas a los módulos — la estructura de orquestador no cambia |
| `validacion.py` | 3 — se reescribe | Contenido 100% nuevo, solo se conserva el rol "validar entradas sin lógica de negocio" |
| `matematica.py` (lógica de negocio) | 3 — se reescribe | Contenido 100% nuevo, solo se conserva "sin I/O, testeable con `assert`" |
| `visualizacion.py` | 3 — se reescribe | Contenido 100% nuevo (o no existe, si el tema no grafica nada) |
