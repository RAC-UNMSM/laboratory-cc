# Plantilla de grupo

Para un grupo nuevo (`gNN`):

1. Copiar esta carpeta a `grupos/gNN/`.
2. Dentro de `apps/`, una subcarpeta por app/script a desplegar, con su
   `docker-compose.yml`. Dos puntos de partida según el caso:
   - **`apps/ejemplo-n8n/`** — desplegar una app open source ya armada
     (imagen ya existente, ej. n8n, o cualquier otra herramienta).
   - **`apps/ejemplo-script/`** — un script/pipeline propio (Python) que se
     empaqueta en un contenedor con una imagen base simple
     (`python:3.11-slim`) y corre una vez (`restart: "no"`). Para un
     servicio que debe quedarse corriendo (un servidor, una API), usar en
     su lugar el patrón de `ejemplo-n8n`.
3. Reglas obligatorias del `docker-compose.yml` (las valida el CI en el PR,
   y de nuevo el propio despliegue antes de tocar Docker — ver
   `ci/compose_policy.py`):
   - **`mem_limit`** en todo servicio.
   - Nada de `privileged: true`, `network_mode: host`, `pid: host`, ni
     `cap_add` peligroso (`SYS_ADMIN`, `ALL`, `NET_ADMIN`, `SYS_PTRACE`,
     `SYS_MODULE`).
   - Solo **volúmenes nombrados** (nunca bind-mounts a una ruta del host:
     nada de `./algo:/algo` ni `/ruta/absoluta:/algo`).
   - `container_name: lab-gNN-<app>` fijo, y unirse a la red externa
     `lab_net` (copiar el bloque `networks:` del ejemplo).
4. **No hace falta tocar nada del repo de infraestructura.** El asset de
   Dagster se genera solo: el code-location escanea
   `grupos/*/apps/*/docker-compose.yml` en cada recarga (que dispara el
   agente de deploy tras cada merge a `main`) y crea el asset
   automáticamente — agregar la carpeta con su `docker-compose.yml` ya es
   suficiente.
5. Si la app necesita ruta pública (para que el grupo la use en el
   navegador), agregar la ruta correspondiente en `caddy/Caddyfile` del
   repo de infraestructura (`handle /gNN/<app>* { ... reverse_proxy
   lab-gNN-<app>:<puerto> }`) — esa parte sí la hace el profesor, no va en
   este repo.
6. Abrir PR contra `main`. El profesor (CODEOWNERS) revisa y mergea — el
   despliegue real ocurre solo, automáticamente, cuando el agente de deploy
   detecta el merge (nunca hay botón de "Materialize" que un alumno pueda
   apretar).
