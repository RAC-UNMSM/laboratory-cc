# grupo06-frenet-lagrange — Servidor MCP «Frenet, Lagrange y Puntos Críticos» (Grupo 06 · UNMSM)

Es un agente de IA para Cálculo en varias variables. El **LLM** (Claude, DeepSeek, Gemini…) entiende el
enunciado y explica la solución. Toda la matemática la hace este **servidor MCP**, con **SymPy exacto**:
fracciones y raíces, nunca decimales inventados.

En el entorno del laboratorio el servidor corre en Docker, en la red `lab_net`, detrás de **Caddy**, y
guarda los reportes en **SeaweedFS** (API S3). Las URLs que devuelve son públicas, así que el chat
puede mostrar el gráfico y enlazar el reporte interactivo.

```
Cliente MCP (Claude, MCP Inspector…)
      │  HTTPS  https://rac-unmsm.vekthos.org/grupo06/grupo06_proyecto01_frenet-lagrange/mcp
      ▼
   Caddy ──────────────▶ lab-grupo06_proyecto01_frenet-lagrange:8000/mcp   (streamable-http, sin estado)
      │                          │
      │                          ├─ capa 1: core/validacion.py (Pydantic)   ¿la petición está bien formada?
      │                          ├─ capa 2: core/verificador.py             ¿tiene sentido matemático?
      │                          ├─ pool de procesos de cálculo (core/trabajador.py → core/motor.py)
      │                          │     methods/* → core/visualizacion.py → core/reporte.py (Jinja2)
      │                          └─ storage.py ──PUT S3──▶ seaweedfs:8333 / grupo06-frenet-lagrange-imgs /
      │                                                      grupo06/<id>/reporte.html, grafico.png, …
      └─ /img/grupo06-frenet-lagrange/grupo06/<id>/…  ◀── Caddy sirve esos objetos al navegador y al chat
```

## Requisitos del validador (CI) — dónde se cumple cada uno

| Tarea | Requisito | Dónde |
|---|---|---|
| 1 | Reporte combinado **automático** en prefijo fijo `grupo06/lote-sesion-actual/` | `core/combinado.py` → `agregar_a_sesion(id_nuevo_ejercicio, enunciado)` |
| 1 | Se llama **justo después** de subir `reporte.html` y `grafico.png` | `core/motor.py` → `publicar()` (primero `almacen.guardar`, luego `agregar_a_sesion`) |
| 1 | Sobrescribe `reporte_combinado.html` y `lote.json` **sin crear un id de lote nuevo** | `Combinador.combinar(..., id_lote=ID_SESION)` |
| 2 | Sin cliente LLM ni dependencia `openai`: el servidor no usa ningún modelo de lenguaje | no existe `agente.py`; `requirements.txt` no incluye `openai` |
| 3 | `mcp==2.1.1` exacto | `requirements.txt` |
| 3 | `from mcp.server.mcpserver import MCPServer` y `mcp = MCPServer("grupo06-frenet-lagrange")` | `server.py` |
| 3 | Herramientas con type hints estrictos y docstrings | `server.py` (lo comprueba `tests/test_requisitos_ci.py`) |
| 4 | Gráficos con `io.BytesIO()` + `.getvalue()`; HTML con `.encode("utf-8")` | `core/reporte.py` → `figura_a_png_bytes`, `grafico_png_bytes`, `html_bytes` |
| 4 | `subir` / `guardar` reciben `contenido_bytes` y suben ese búfer a S3 | `storage.py` → `Almacen.subir(..., contenido_bytes: bytes)`, `Almacen.guardar(..., contenido_bytes=...)` |
| 4 | Nada se escribe en el disco del contenedor (tampoco en carpetas temporales) | el proceso de cálculo devuelve bytes; comprobado con `docker diff` |
| 5 | Línea literal `mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)` en `main()` | `server.py::main`, dentro de `try/except TypeError` |
| 5 | En el `except`: `os.environ.update()` + `arrancar = getattr(mcp, "run")` | `server.py::main` |
| — | Sin `print` (todo con `logging`) | todo el código versionado |

**Cómo funciona el arranque con el SDK 2.1.1.** En `mcp==2.1.1`, `MCPServer.run()` sí acepta `host` y
`port` (los pasa a `run_streamable_http_async`), así que la línea literal arranca el servidor
directamente y el `except TypeError` queda como respaldo para un SDK que no los acepte. Como
`MCPServer` se crea solo con su nombre, el resto de la configuración se aplica aparte:

- las instrucciones para el LLM se fijan en el servidor de bajo nivel (`mcp._lowlevel_server.instructions`);
- `_configurar_http()` completa el arranque HTTP con la ruta `/mcp`, el modo **sin estado** y, si
  existen, `MCP_HOST` / `MCP_PORT` (las pruebas usan otro puerto). Con `host="0.0.0.0"` el SDK no
  activa la protección anti DNS-rebinding, así que acepta el `Host` público que reenvía Caddy.

**Concurrencia del reporte de sesión.** Las actualizaciones de `lote-sesion-actual` pasan por un
candado del proceso: varios usuarios a la vez en el mismo contenedor no se pisan (probado con 8
clientes simultáneos). Con **varias réplicas** del contenedor, la última escritura gana, porque
`lote.json` es un objeto compartido. Además, el reporte de sesión crece con cada ejercicio; si hace
falta, `MCP_SESION_MAX` limita cuántos ejercicios recientes conserva (0 = todos, el valor por defecto).

## Estructura

```
frenet-lagrange/
├── methods/                 lógica matemática pura (sin gráficos ni HTML)
├── core/
│   ├── utils_math.py        parser SEGURO, resolución exacta de sistemas, formato LaTeX
│   ├── validacion.py        esquemas Pydantic (lo que ve el LLM)  ← capa 1
│   ├── verificador.py       validaciones lógicas con códigos de error ← capa 2
│   ├── diagnostico.py       lenguaje natural → método + argumentos
│   ├── visualizacion.py     todo lo gráfico (Plotly/matplotlib)
│   ├── reporte.py           inyecta resultados en las plantillas Jinja2
│   ├── combinado.py         varios ejercicios en UNA página; agregar_a_sesion (grupo06/lote-sesion-actual/)
│   ├── esquema.py           JSON Schema MCP portable (lo verifican las pruebas)
│   ├── motor.py             un cálculo completo (todo en bytes) y publicar(): subir + reporte de sesión
│   └── trabajador.py        proceso de cálculo (tuberías propias; se mata si excede el tiempo)
├── templates/               base.html.j2, combinado*.html.j2, static/ (CSS y JS)
├── server.py                servidor MCP (MCPServer, SDK 2.1.1) — streamable-http o STDIO
├── storage.py               SeaweedFS S3, subidas desde memoria (contenido_bytes)
├── tests/                   pruebas (pytest), con SeaweedFS simulado y chequeos estáticos del CI
├── despliegue/              Caddyfile.ejemplo (laboratorio) y Caddyfile.local (prueba)
├── ejemplos/                configuración de Claude Desktop (remota, con mcp-remote)
├── Dockerfile · docker-compose.yml · docker-compose.local.yml · requirements*.txt
```

## Almacenamiento: estructura en SeaweedFS

```
s3://grupo06-frenet-lagrange-imgs/
└── grupo06/
    ├── hessiana-20261006-153012-a1b2c3d4/
    │   ├── reporte.html      página interactiva (pestañas: resumen, procedimiento LaTeX, 3D, 2D, JSON)
    │   ├── grafico.png       lámina estática
    │   ├── resultado.json    resultado exacto
    │   ├── entrada.json      solicitud validada
    │   └── meta.json         id, método, fecha, descripción, resumen y URLs (se escribe AL FINAL)
    ├── lote-20261006-153500-9f8e7d6c/    reporte combinado pedido con combinar_reportes (id nuevo)
    │   ├── reporte_combinado.html
    │   └── lote.json
    └── lote-sesion-actual/               reporte combinado AUTOMÁTICO (mismo prefijo siempre)
        ├── reporte_combinado.html        todos los ejercicios de la sesión, en orden
        └── lote.json                     [{id, enunciado}, …]
```

**Por qué no hay índice compartido.** Con un `indice.json` único, dos réplicas que guardan a la vez
leen la misma versión, cada una agrega su cálculo y la última en escribir borra el de la otra. Ahora
cada cálculo escribe **solo** en su propio prefijo, con claves que nadie más usa. Para listar se le
pregunta a S3 qué prefijos existen. `meta.json` se sube al final: si un cálculo quedó a medias, no
aparece en el listado.

## Respuesta de una herramienta de cálculo

- **Texto 1 (Markdown)**, para copiarlo al chat:
  ```
  ![Reporte de cálculo](https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange/grupo06/<id>/reporte.html)
  ![Gráfico — hessiana](https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange/grupo06/<id>/grafico.png)
  [Abrir el reporte interactivo (procedimiento + gráfico 3D)](https://…/grupo06/<id>/reporte.html)
  [Reporte combinado de la sesión (N ejercicios)](https://…/grupo06/lote-sesion-actual/reporte_combinado.html)
  ```
  Una imagen Markdown solo se dibuja si apunta a una imagen. Por eso, además del enlace al HTML que
  pide el enunciado, se agrega la del PNG, que es la que el chat muestra. El HTML se abre con el enlace.
- **Texto 2:** el JSON del resultado (también va como `structured_content`), con `reporte_sesion`.
- **Image:** el PNG (≤1024 px, ~150–250 KB) como respaldo si el cliente no puede abrir las URLs.
  Se desactiva con `salida.incluir_imagen = false`.

Si SeaweedFS no responde, el cálculo igual se devuelve, con una advertencia y sin enlaces.

## Despliegue en el laboratorio

```bash
docker compose build
docker compose up -d          # se une a la red externa lab_net; Caddy lo encuentra como lab-grupo06_proyecto01_frenet-lagrange:8000
docker compose logs -f
```
Caddy necesita dos rutas: los archivos públicos hacia SeaweedFS y el endpoint MCP hacia este
contenedor. Están en `despliegue/Caddyfile.ejemplo`. Para comprobar que el servidor responde:
`GET /salud` (lo usa también el `HEALTHCHECK` del Dockerfile).

### Prueba completa en tu PC (SeaweedFS + Caddy + servidor)
```bash
docker compose -f docker-compose.local.yml up -d --build
curl http://localhost:8080/grupo06/grupo06_proyecto01_frenet-lagrange/salud
```

## Uso local (sin Docker)

```bash
python -m venv .venv
.venv\Scripts\activate                      # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements-dev.txt          # servidor y pruebas
python -m pytest -q                          # pruebas
```

- **Conectar Claude Desktop al servidor desplegado:** `ejemplos/claude_desktop_config_remoto.json`.
  Usa el puente `mcp-remote` y necesita Node.js.
- Para correr el servidor en tu PC necesitas SeaweedFS (levántalo con `docker-compose.local.yml`): el
  almacén de resultados es S3.

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `MCP_TRANSPORT` | `streamable-http` | `stdio` solo para pruebas locales (o `--stdio`) |
| `MCP_HOST` / `MCP_PORT` / `MCP_HTTP_PATH` | `0.0.0.0` / `8000` / `/mcp` | dónde escucha el servidor HTTP |
| `MCP_STATELESS` | `1` | sin sesiones en memoria → cualquier réplica atiende cualquier petición |
| `SEAWEEDFS_S3_URL` | `http://seaweedfs:8333` | API S3 (DNS interno de Docker) |
| `IMG_BUCKET` | `grupo06-frenet-lagrange-imgs` | bucket asignado |
| `PUBLIC_IMG_BASE_URL` | `https://rac-unmsm.vekthos.org/img/grupo06-frenet-lagrange` | base de las URLs públicas |
| `MCP_GRUPO` | `grupo06` | prefijo de todas las claves |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | — | solo si SeaweedFS exige credenciales (firma AWS SigV4) |
| `MCP_MATH_WORKERS` | `2` | cálculos simultáneos por contenedor |
| `MCP_MATH_TIMEOUT` | `120` | segundos máximos por cálculo |
| `MCP_MATH_PROCESOS` | `1` | `0` = calcular en el mismo proceso (depuración, sin límite de tiempo) |
| `MCP_SESION_MAX` | `0` | ejercicios que conserva el reporte de sesión (0 = todos) |

## Herramientas MCP

| Herramienta | Cuándo la elige el LLM |
|---|---|
| `diagnosticar_problema` | enunciado ambiguo en lenguaje natural → recomienda método y extrae argumentos |
| `optimizar_con_restricciones` | máx/mín de f **sujeto a** igualdades g = c (Lagrange) |
| `analizar_puntos_criticos` | máx/mín relativos, sillas, Hessiana, **sin** restricciones |
| `analizar_curva_frenet` | curva r(t): T, N, B, curvatura, torsión, planos |
| `listar_resultados` / `obtener_resultado` | historial (listado directo desde S3) |
| `combinar_reportes` | solo si el usuario pide un reporte APARTE con ejercicios concretos (el de la sesión es automático) |

## Validación en dos capas

1. **Estructural (Pydantic, `core/validacion.py`).** El SDK rechaza la llamada antes de ejecutar nada si:
   - falta un campo o sobra uno;
   - una expresión no se puede interpretar;
   - una restricción es una desigualdad.
2. **Lógica (`core/verificador.py`).** Cada error trae `codigo`, `mensaje` y `sugerencia`. Algunos códigos:
   - `DIVISION_POR_CERO`;
   - `RESTRICCION_IMPOSIBLE` (p. ej. x²+y² = −1);
   - `SOBREDETERMINADO`;
   - `FUNCION_CONSTANTE`;
   - `CURVATURA_CERO` (la curva es una recta);
   - `PUNTO_SINGULAR`.

## Pruebas

`python -m pytest -q` ejecuta las pruebas. Las de almacenamiento y servidor usan
`tests/s3_simulado.py`, un SeaweedFS de mentira en un hilo que registra cada petición. Verifican:

- **el bucket:** `PUT /grupo06-frenet-lagrange-imgs/` al arrancar y la tolerancia a SeaweedFS caído;
- **las claves:** que existan las de `grupo06/<id>/` y que no haya `indice.json`;
- **la respuesta:** los Content-Type, las URLs públicas en Markdown y el bloque Image;
- **el listado:** `ListObjectsV2` con prefijo y delimitador;
- **la firma:** SigV4 cuando hay credenciales;
- **la concurrencia:** 4 clientes simultáneos con ids distintos, y ninguno se pierde en la sesión;
- **el reporte de sesión:** mismo prefijo `lote-sesion-actual`, orden, sin ids de lote nuevos;
- **todo en memoria:** el HTML y el PNG son `bytes` y no aparece ningún archivo en disco;
- **los requisitos del CI** (`tests/test_requisitos_ci.py`): `mcp==2.1.1`, `MCPServer`, la línea
  literal de `run`, sin el cliente del LLM, sin impresiones por pantalla, sin carpetas temporales,
  type hints y docstrings.

También se comprobó la imagen Docker real con `docker-compose.local.yml` (SeaweedFS 4.48 + Caddy 2.10):
8 clientes simultáneos, todos los archivos públicos con 200, la sesión con los 8 ejercicios y
`docker diff` sin ningún archivo escrito por el servidor.
