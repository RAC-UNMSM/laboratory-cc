# Referencia: cómo se despliega una app de grupo

Resumen del contrato entre este repo y el servidor. El ejemplo completo y
funcionando es `grupos/g01/semana01/derivadas1/`.

## De la carpeta sale todo lo demás

El despliegue solo busca este patrón, exactamente dos niveles bajo el grupo:

```
grupos/grupoNN/<semana>/<tema>/docker-compose.yml
```

`<semana>` es `semanaNN` o `proyectoNN`. Una app en otro nivel
(`grupos/grupoNN/mi-app/` o más profunda) no se despliega.

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
| `docker-compose.yml` | `build: .`, `container_name: ${LAB_CONTAINER_NAME}`, `restart: unless-stopped`, `mem_limit: 512m`, bloque `networks` | Solo el nombre del servicio |
| `Dockerfile` | `FROM python:3.11-slim`, instalación de `requirements.txt`, `CMD` | La línea `COPY` con los módulos propios |
| `requirements.txt` | `mcp==2.1.1` | Las librerías que el grupo importa |
| `server.py` | El import de `MCPServer` y la línea `mcp.run(...)` | Nombre del servidor y las tools |
| `storage.py` | `SEAWEEDFS_S3_URL` y la lógica de subida | `IMG_BUCKET` y `PUBLIC_IMG_BASE_URL` |

## `docker-compose.yml`

```yaml
services:
  servidor:
    build: .
    container_name: ${LAB_CONTAINER_NAME}
    restart: unless-stopped
    mem_limit: 512m

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

- Nombre del servidor: `grupoNN-<tema>`.
- `transport="streamable-http"`: sin él, `mcp.run()` usa stdio y el
  contenedor termina al instante. `"sse"` no funciona en este laboratorio.
- `host="0.0.0.0"`: con `127.0.0.1` Caddy no puede llegar al contenedor.
- `port=8000`: es el que el administrador pone en la ruta de Caddy.
- Cada tool con docstring.
- Nada de `app.run(debug=True)`, ni abrir archivos con el visor del sistema,
  ni interfaces web aparte: el entregable es el servidor MCP.

## `storage.py`

Solo hace falta si la app genera imágenes o archivos. Se copia el del piloto
y se cambian dos constantes:

```python
SEAWEEDFS_S3_URL = "http://seaweedfs:8333"                    # igual para todos
IMG_BUCKET = "grupoNN-<tema>-imgs"                            # propio del grupo
PUBLIC_IMG_BASE_URL = "https://rac-unmsm.vekthos.org/img/grupoNN-<tema>"
```

- `seaweedfs:8333` es la API S3 dentro de la red `lab_net`. No `localhost`
  (dentro del contenedor es el propio contenedor) ni el puerto 8888.
- El bucket solo admite minúsculas, dígitos y `-` (de 3 a 63 caracteres), e
  incluye el grupo para no chocar con otro.
- La ruta `/img/grupoNN-<tema>/*` la crea el administrador en Caddy apuntando
  al bucket. Hasta entonces las imágenes se suben pero no se ven: hay que
  pedírsela.
- Si el storage no responde, `subir_imagen()` devuelve `None` y la tool sigue
  respondiendo. Con `timeout` en cada llamada.
- Nunca subir a servicios públicos de terceros (tmpfiles.org, imgur, etc.).
- Nada se guarda en disco: el contenedor no conserva archivos. Los gráficos
  se generan en memoria (`io.BytesIO`).

## Qué pasa después del PR

1. El CI valida el compose y hace un arranque de prueba (construye, levanta,
   muestra los logs y baja). El resultado queda como comentario en el PR.
2. El administrador revisa y fusiona.
3. El agente de despliegue detecta el cambio en `main` y levanta la app.
4. El administrador agrega la ruta pública (y la de imágenes) en el servidor.
5. El grupo prueba con MCP Inspector o
   `claude mcp add --transport http <nombre> <URL>/mcp`.
