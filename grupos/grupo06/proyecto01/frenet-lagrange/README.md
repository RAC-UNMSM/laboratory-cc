# grupo06-frenet-lagrange — Servidor MCP «Frenet, Lagrange y Puntos Críticos» (Grupo 06 · UNMSM)

Es un agente de IA para Cálculo en varias variables. El **LLM** (Claude, DeepSeek, Gemini…) entiende el
enunciado y explica la solución. Toda la matemática la hace este **servidor MCP**, con **SymPy exacto**:
fracciones y raíces, nunca decimales inventados.

En el entorno del laboratorio el servidor corre en Docker, en la red `lab_net`, detrás de **Caddy**, y
guarda los reportes en **SeaweedFS** (API S3). Las URLs que devuelve son públicas, así que el chat
puede mostrar el gráfico y enlazar el reporte interactivo.

```
Cliente MCP (Claude, agente.py…)
      │  HTTPS  https://rac-unmsm.vekthos.org/grupo06/frenet-lagrange/mcp
      ▼
   Caddy ──────────────▶ grupo06-frenet-lagrange:8000/mcp   (streamable-http, sin estado)
      │                          │
      │                          ├─ capa 1: core/validacion.py (Pydantic)   ¿la petición está bien formada?
      │                          ├─ capa 2: core/verificador.py             ¿tiene sentido matemático?
      │                          ├─ pool de procesos de cálculo (core/trabajador.py → core/motor.py)
      │                          │     methods/* → core/visualizacion.py → core/reporte.py (Jinja2)
      │                          └─ storage.py ──PUT S3──▶ seaweedfs:8333 / frenet-lagrange-imgs /
      │                                                      grupo06/<id>/reporte.html, grafico.png, …
      └─ /img/frenet-lagrange/grupo06/<id>/…  ◀── Caddy sirve esos objetos al navegador y al chat
```

## Qué cambió respecto al avance anterior

| Requisito | Dónde |
|---|---|
| Nombre del servidor `grupo06-frenet-lagrange` | `server.py` (`FastMCP(NOMBRE_SERVIDOR, …)`) |
| Transporte **streamable-http** en `0.0.0.0:8000` (ruta `/mcp`) | `server.py`; STDIO sigue disponible con `--stdio` |
| Almacenamiento en **SeaweedFS (S3)** con `urllib` | `storage.py` → `BackendS3` |
| `ensure_bucket()` tolerante a que SeaweedFS aún no arranque | `BackendS3.preparar()` (alias `ensure_bucket`) |
| Claves `grupo06/<id_resultado>/reporte.html · grafico.png · resultado.json` | `Almacen.clave()` |
| URLs **públicas** (Caddy) en Markdown + bloque **Image** de respaldo | `server.py::_calcular` |
| Ids con `uuid4` (8 hex) y fecha UTC | `storage.nuevo_id()` |
| **Sin `indice.json`**: el listado se pide a S3 (`ListObjectsV2` + delimitador) | `Almacen.listar()` |
| Varias peticiones a la vez | pool de `MCP_MATH_WORKERS` procesos + modo sin estado |
| Dockerfile / compose en `lab_net` | `Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml` |
| Pruebas con SeaweedFS simulado | `tests/s3_simulado.py`, `tests/test_reporte_y_storage.py`, `tests/test_servidor_mcp.py` |

**Nota técnica sobre `mcp.run(...)`.** En el SDK oficial (`mcp` 1.x), `FastMCP.run()` acepta **solo**
el transporte. Escribir `mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)` da `TypeError`.
Por eso `host` y `port` se pasan al **constructor**, `FastMCP(..., host="0.0.0.0", port=8000)`, y luego
se llama `mcp.run(transport="streamable-http")`. El resultado es el mismo. Además, con `host="0.0.0.0"`
el SDK no activa su protección anti DNS-rebinding de localhost, y por eso acepta el `Host` público que
reenvía Caddy.

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
│   ├── combinado.py         varios ejercicios en UNA página (se publica en grupo06/lote-…/)
│   ├── motor.py             un cálculo completo: verificar → resolver → graficar → reportar
│   └── trabajador.py        proceso de cálculo (tuberías propias; se mata si excede el tiempo)
├── templates/               base.html.j2, combinado*.html.j2, static/ (CSS y JS)
├── server.py                servidor MCP (FastMCP) — streamable-http o STDIO
├── storage.py               SeaweedFS S3 (o carpeta local con la misma estructura)
├── agente.py                agente IA (DeepSeek, Gemini, Claude, OpenAI, Ollama o --simulado); local o --url
├── cli.py                   uso desde la terminal, sin LLM
├── tests/                   79 pruebas (pytest), con SeaweedFS simulado
├── despliegue/              Caddyfile.ejemplo (laboratorio) y Caddyfile.local (prueba)
├── ejemplos/                configuración de Claude Desktop (local y remota)
├── legado/                  los tres metodos_*.py originales
├── Dockerfile · docker-compose.yml · docker-compose.local.yml · requirements*.txt
```

## Almacenamiento: estructura en SeaweedFS

```
s3://frenet-lagrange-imgs/
└── grupo06/
    ├── hessiana-20261006-153012-a1b2c3d4/
    │   ├── reporte.html      página interactiva (pestañas: resumen, procedimiento LaTeX, 3D, 2D, JSON)
    │   ├── grafico.png       lámina estática
    │   ├── resultado.json    resultado exacto
    │   ├── entrada.json      solicitud validada
    │   └── meta.json         id, método, fecha, descripción, resumen y URLs (se escribe AL FINAL)
    └── lote-20261006-153500-9f8e7d6c/
        ├── reporte_combinado.html
        └── lote.json
```

**Por qué no hay índice compartido.** Con un `indice.json` único, dos réplicas que guardan a la vez
leen la misma versión, cada una agrega su cálculo y la última en escribir borra el de la otra. Ahora
cada cálculo escribe **solo** en su propio prefijo, con claves que nadie más usa. Para listar se le
pregunta a S3 qué prefijos existen. `meta.json` se sube al final: si un cálculo quedó a medias, no
aparece en el listado.

## Respuesta de una herramienta de cálculo

- **Texto 1 (Markdown)**, para copiarlo al chat:
  ```
  ![Reporte de cálculo](https://rac-unmsm.vekthos.org/img/frenet-lagrange/grupo06/<id>/reporte.html)
  ![Gráfico — hessiana](https://rac-unmsm.vekthos.org/img/frenet-lagrange/grupo06/<id>/grafico.png)
  [Abrir el reporte interactivo (procedimiento + gráfico 3D)](https://…/grupo06/<id>/reporte.html)
  ```
  Una imagen Markdown solo se dibuja si apunta a una imagen. Por eso, además del enlace al HTML que
  pide el enunciado, se agrega la del PNG, que es la que el chat muestra. El HTML se abre con el enlace.
- **Texto 2:** el JSON del resultado (también va como `structuredContent`).
- **Image:** el PNG (≤1024 px, ~150–250 KB) como respaldo si el cliente no puede abrir las URLs.
  Se desactiva con `salida.incluir_imagen = false`.

Si SeaweedFS no responde, el cálculo igual se devuelve, con una advertencia y sin enlaces.

## Despliegue en el laboratorio

```bash
docker compose build
docker compose up -d          # se une a la red externa lab_net; Caddy lo encuentra como grupo06-frenet-lagrange:8000
docker compose logs -f
```
Caddy necesita dos rutas: los archivos públicos hacia SeaweedFS y el endpoint MCP hacia este
contenedor. Están en `despliegue/Caddyfile.ejemplo`. Para comprobar que el servidor responde:
`GET /salud` (lo usa también el `HEALTHCHECK` del Dockerfile).

### Prueba completa en tu PC (SeaweedFS + Caddy + servidor)
```bash
docker compose -f docker-compose.local.yml up -d --build
python agente.py --simulado --url http://localhost:8080/grupo06/frenet-lagrange/mcp
```

## Uso local (sin Docker)

```bash
pip install -r requirements-dev.txt          # servidor, agente y pruebas
python -m pytest -q                          # 79 pruebas
python agente.py --simulado --abrir          # lanza server.py por STDIO con almacenamiento local
python server.py --stdio                     # lo que ejecuta Claude Desktop (ver ejemplos/)
python server.py                             # HTTP en 0.0.0.0:8000 (necesita SeaweedFS o MCP_MATH_STORAGE=local)
python cli.py frenet -r "cos t, sin t, t" --t0 pi/4 --html helice.html
```

- **Claude Desktop con el servidor en tu PC:** `ejemplos/claude_desktop_config.json`.
  Pasa `--stdio` y `MCP_MATH_STORAGE=local`.
- **Claude Desktop con el servidor desplegado:** `ejemplos/claude_desktop_config_remoto.json`.
  Usa el puente `mcp-remote` y necesita Node.js.

## Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `MCP_TRANSPORT` | `streamable-http` | `stdio` para Claude Desktop / agente local (o `--stdio`) |
| `MCP_HOST` / `MCP_PORT` / `MCP_HTTP_PATH` | `0.0.0.0` / `8000` / `/mcp` | dónde escucha el servidor HTTP |
| `MCP_STATELESS` | `1` | sin sesiones en memoria → cualquier réplica atiende cualquier petición |
| `MCP_MATH_STORAGE` | `auto` | `s3`, `local`, o `auto` (S3 si es HTTP, local si es STDIO) |
| `SEAWEEDFS_S3_URL` | `http://seaweedfs:8333` | API S3 (DNS interno de Docker) |
| `IMG_BUCKET` | `frenet-lagrange-imgs` | bucket asignado |
| `PUBLIC_IMG_BASE_URL` | `https://rac-unmsm.vekthos.org/img/frenet-lagrange` | base de las URLs públicas |
| `MCP_GRUPO` | `grupo06` | prefijo de todas las claves |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | — | solo si SeaweedFS exige credenciales (firma AWS SigV4) |
| `MCP_MATH_WORKERS` | `2` | cálculos simultáneos por contenedor |
| `MCP_MATH_TIMEOUT` | `120` | segundos máximos por cálculo |
| `MCP_MATH_PROCESOS` | `1` | `0` = calcular en el mismo proceso (depuración, sin límite de tiempo) |
| `MCP_MATH_RESULTADOS` | `./resultados` | carpeta del modo local |

## Herramientas MCP

| Herramienta | Cuándo la elige el LLM |
|---|---|
| `diagnosticar_problema` | enunciado ambiguo en lenguaje natural → recomienda método y extrae argumentos |
| `optimizar_con_restricciones` | máx/mín de f **sujeto a** igualdades g = c (Lagrange) |
| `analizar_puntos_criticos` | máx/mín relativos, sillas, Hessiana, **sin** restricciones |
| `analizar_curva_frenet` | curva r(t): T, N, B, curvatura, torsión, planos |
| `listar_resultados` / `obtener_resultado` | historial (listado directo desde S3) |
| `combinar_reportes` | varios ejercicios en un mensaje → un solo HTML con navegación |

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

`python -m pytest -q` ejecuta 79 pruebas. Las de almacenamiento y servidor usan
`tests/s3_simulado.py`, un SeaweedFS de mentira en un hilo que registra cada petición. Verifican:

- **el bucket:** `PUT /frenet-lagrange-imgs/` al arrancar y la tolerancia a SeaweedFS caído;
- **las claves:** que existan las de `grupo06/<id>/` y que no haya `indice.json`;
- **la respuesta:** los Content-Type, las URLs públicas en Markdown y el bloque Image;
- **el listado:** `ListObjectsV2` con prefijo y delimitador;
- **la firma:** SigV4 cuando hay credenciales;
- **la concurrencia:** 4 clientes simultáneos con ids distintos.

Durante el desarrollo también se comprobó contra un **SeaweedFS 4.48 real**, en modo anónimo y con
credenciales, y a través de **Caddy 2.10**.
