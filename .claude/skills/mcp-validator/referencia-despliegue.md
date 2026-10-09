# Referencia: cómo se despliega una app de grupo

Resumen del contrato entre este repo y el servidor. El ejemplo completo y
funcionando es `grupos/g01/semana01/derivadas1/`.

## De la carpeta sale todo lo demás

El despliegue solo busca este patrón, exactamente dos niveles bajo el grupo:

```
grupos/grupoNN/<semana>/<tema>/docker-compose.yml
```

`<semana>` es `proyectoNN` (o `semanaNN`). Una app en otro nivel
(`grupos/grupoNN/mi-app/` o más profunda) no se despliega. Todo el proyecto
(código, archivos de despliegue, datos) va dentro de la carpeta del tema;
en `grupos/grupoNN/` y en `proyectoNN/` solo queda documentación.

Los nombres de `<semana>` y `<tema>` solo pueden llevar minúsculas, dígitos,
`-` y `_`. Sin espacios, mayúsculas ni tildes: forman el nombre de proyecto
de Docker Compose, que no los acepta.

A partir de la ruta se calcula, sin que nadie lo escriba a mano:

| Cosa | Fórmula | Ejemplo (`grupos/grupo04/proyecto01/interpolacion/`) |
|---|---|---|
| Identificador de la app | `<grupo>_<semana>_<tema>` | `grupo04_proyecto01_interpolacion` |
| Nombre del contenedor | `lab-<identificador>` | `lab-grupo04_proyecto01_interpolacion` |
| Ruta pública | `/<grupo>/<identificador>` | `/grupo04/grupo04_proyecto01_interpolacion` |
| URL para conectar el MCP | `https://rac-unmsm.vekthos.org<ruta>/mcp` | `https://rac-unmsm.vekthos.org/grupo04/grupo04_proyecto01_interpolacion/mcp` |

Renombrar la carpeta cambia el contenedor y la URL: hay que avisar al
administrador.

## Qué se copia del piloto y qué se cambia

| Archivo | Se deja igual | Se cambia |
|---|---|---|
| `docker-compose.yml` | `build: .`, `container_name: ${LAB_CONTAINER_NAME}`, `restart: unless-stopped`, `mem_limit: 512m`, bloque `environment` con `LAB_IMG_BUCKET` y `LAB_PUBLIC_IMG_URL` (si hay `storage.py`), bloque `networks` | Solo el nombre del servicio |
| `Dockerfile` | `FROM python:3.11-slim`, instalación de `requirements.txt`, `CMD` | La línea `COPY` con los módulos propios |
| `requirements.txt` | `mcp==2.1.1` | Las librerías que el grupo importa |
| `server.py` | El import de `MCPServer` y la línea `mcp.run(...)` | Nombre del servidor y las tools |
| `storage.py` | Todo: el bucket y la URL llegan por `LAB_IMG_BUCKET` y `LAB_PUBLIC_IMG_URL` | Nada |

## `docker-compose.yml`

```yaml
services:
  servidor:
    build: .
    container_name: ${LAB_CONTAINER_NAME}
    restart: unless-stopped
    mem_limit: 512m
    environment:                               # solo si hay storage.py
      LAB_IMG_BUCKET: ${LAB_IMG_BUCKET}
      LAB_PUBLIC_IMG_URL: ${LAB_PUBLIC_IMG_URL}

networks:
  default:
    name: lab_net
    external: true
```

- `container_name: ${LAB_CONTAINER_NAME}` va **literal**. El despliegue
  inyecta el valor; escribir el nombre a mano es el error más común.
- `mem_limit` es obligatorio en cada servicio (el CI lo rechaza si falta).
- Sin `ports:` que publiquen en el servidor (`"8000:8000"` choca con otros
  grupos). Caddy llega al contenedor por la red `lab_net`.
- Prohibido: `privileged`, `network_mode: host`, `pid: host`, `devices`,
  `cap_add` peligroso, `env_file` y montar rutas del host (`./algo:/algo`).
  Solo volúmenes nombrados.
- El archivo se llama exactamente `docker-compose.yml`.
- `restart: unless-stopped` para un servidor. Con `restart: "no"` el
  despliegue lo trata como un script que debe terminar solo, y a un servidor
  lo marca como fallido.
- Variables: el despliegue solo entrega `${LAB_CONTAINER_NAME}`,
  `${LAB_PUBLIC_PATH}`, `${LAB_DOMAIN}`, `${LAB_IMG_BUCKET}` y
  `${LAB_PUBLIC_IMG_URL}`. Cualquier otra `${VAR}` llega vacía
  aunque exista en el servidor; si hace falta una, se pide al administrador.

## `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py validacion.py matematica.py visualizacion.py storage.py .

CMD ["python", "server.py"]
```

- La línea `COPY` debe incluir **todos** los módulos que `server.py` importa,
  directa o indirectamente. Las carpetas se copian aparte:
  `COPY tools/ tools/`. Lo que no se copia no existe en el contenedor.
- El `CMD` es `["python", "server.py"]`. Con `fastmcp run server.py` (o
  `mcp run`) el bloque `if __name__ == "__main__"` no se ejecuta, así que el
  transporte, el host y el puerto serían los del `CMD`, no los de `mcp.run`.
- Sin rutas de Windows ni nada de la laptop del alumno.
- Si el código ejecuta un programa del sistema, se instala aquí con
  `RUN apt-get update && apt-get install -y --no-install-recommends <paquete> && rm -rf /var/lib/apt/lists/*`,
  y se avisa al administrador.

## `requirements.txt`

```
mcp==2.1.1
sympy
numpy
matplotlib
```

- Un paquete por línea. Nunca comandos (`pip install ...`).
- **Todas** las librerías que el código importa y que no son de la librería
  estándar de Python. Lo que funciona en la laptop porque ya estaba instalado
  falla en el contenedor con `ModuleNotFoundError`.
- Sin paquetes repetidos: `pip` aborta con "Double requirement given".
- Solo lo que el proyecto importa. No la salida de `pip freeze`, que vuelca
  todo lo instalado en la laptop.
- Sin paquetes exclusivos de Windows (`pywin32` y similares): el servidor es
  Linux y la imagen no se construye.
- Sin instalaciones desde rutas locales (`-e .`, `C:\...`, `file://`).
- Las herramientas de desarrollo (black, jupyter, pyinstaller…) van en un
  `requirements-dev.txt` aparte.
- `mcp==2.1.1` fijo. En la 2.x la clase es `MCPServer` y vive en
  `mcp.server.mcpserver`; en la 1.x era `FastMCP` en `mcp.server.fastmcp`.
  Sin fijar la versión, un build futuro puede romper los imports.
- El nombre de pip no siempre es el del import: `PIL` → `pillow`,
  `cv2` → `opencv-python`, `sklearn` → `scikit-learn`, `yaml` → `pyyaml`.

## `server.py`

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("grupoNN-<tema>")


@mcp.tool()
def mi_calculo(expresion: str, x_min: float = -10, x_max: float = 10):
    """Qué hace la tool y en qué formato espera cada parámetro, con ejemplos.

    Este docstring es lo que lee la IA para decidir cuándo y cómo usarla.
    """
    ...


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

- Nombre del servidor: `grupoNN-<tema>`, con el grupo y el nombre de la
  carpeta del proyecto (el piloto es `g01-derivadas1`). Sin el grupo delante,
  o con el nombre del piloto, es error.
- `transport="streamable-http"`: sin él, `mcp.run()` usa stdio y el
  contenedor termina al instante. `"sse"` no funciona en este laboratorio.
- `host="0.0.0.0"`: con `127.0.0.1` Caddy no puede llegar al contenedor.
- `port=8000`: la ruta pública se crea sola al desplegar y apunta a ese puerto.
- Cada tool con docstring.
- Nada de `app.run(debug=True)`, ni abrir archivos con el visor del sistema,
  ni interfaces web aparte: el entregable es el servidor MCP.

## `storage.py`

Solo hace falta si la app genera imágenes o archivos. Se copia el del piloto
**tal cual**: ya no hay nombres que cambiar.

```python
SEAWEEDFS_S3_URL = "http://seaweedfs:8333"                      # igual para todos
IMG_BUCKET = os.environ.get("LAB_IMG_BUCKET", "")               # lo pone el despliegue
PUBLIC_IMG_BASE_URL = os.environ.get("LAB_PUBLIC_IMG_URL", "")  # lo pone el despliegue
```

- El despliegue calcula los dos nombres de la carpeta del proyecto: grupo +
  nombre de la carpeta, con guiones en lugar de cualquier otro signo. Para
  `grupos/grupo04/proyecto01/interpolacion/` son
  `grupo04-interpolacion-imgs` y `https://rac-unmsm.vekthos.org/img/grupo04-interpolacion`.
- Llegan al contenedor porque el `docker-compose.yml` los pasa. Este bloque
  se copia tal cual dentro del servicio; sin él, llegan vacíos y no se sube
  nada:

  ```yaml
      environment:
        LAB_IMG_BUCKET: ${LAB_IMG_BUCKET}
        LAB_PUBLIC_IMG_URL: ${LAB_PUBLIC_IMG_URL}
  ```
- La ruta pública `/img/grupoNN-<carpeta>/` se crea sola al desplegar, con
  ese mismo nombre.
- **Forma anterior, todavía válida:** escribir los dos nombres a mano en
  `storage.py`. Tienen que seguir la misma regla (`grupoNN-<carpeta>-imgs` y
  `/img/grupoNN-<carpeta>`); si no coinciden con lo que la app usa de verdad,
  las imágenes no se ven. Quien ya lo tenga así no necesita cambiarlo.
- `seaweedfs:8333` es la API S3 dentro de la red `lab_net`. No `localhost`
  (dentro del contenedor es el propio contenedor) ni el puerto 8888.
- En local, sin esas variables, el módulo no sube nada y la tool responde
  igual, sin enlace.
- `server.py` tiene que usarlo: llamar a `subir_imagen()` y agregar la URL al
  texto de respuesta. Un `storage.py` que nadie importa no sube nada.
- La subida es un `PUT` con los bytes como cuerpo (API S3), no un `POST` de
  formulario, y cada archivo lleva un nombre aleatorio (`uuid`) para no pisar
  el anterior. El bucket se crea al arrancar (`ensure_bucket()`).
- Si el storage no responde, `subir_imagen()` devuelve `None` y la tool sigue
  respondiendo. Con `timeout` en cada llamada.
- Nunca subir a servicios públicos de terceros (tmpfiles.org, imgur, etc.).
- Nada se guarda en disco: el contenedor no conserva archivos. Los gráficos
  se generan en memoria (`io.BytesIO`).

## Qué pasa después del PR

1. El CI valida el compose y hace un arranque de prueba (construye, levanta,
   muestra los logs y baja). El resultado queda como comentario en el PR.
2. El administrador revisa y fusiona. Solo él puede actualizar `main`.
3. GitHub avisa por webhook al servidor, que descarga `main` y despliega solo
   las apps cuya carpeta cambió.
4. Por cada app: vuelve a validar el compose, construye y levanta (límite de
   15 minutos) y comprueba durante 60 segundos que el contenedor quede
   corriendo. Si falla, el contenedor anterior sigue en pie y el error queda
   en el log del servidor; el alumno no lo ve, hay que preguntarle al
   administrador.
5. El servidor genera la ruta pública del MCP (y la de imágenes) y recarga
   el proxy. No hay que pedirla.
6. El grupo prueba con MCP Inspector o
   `claude mcp add --transport http <nombre> <URL>/mcp`.

Si una app se elimina o se renombra su carpeta, el contenedor anterior no se
baja solo: hay que avisar al administrador.
