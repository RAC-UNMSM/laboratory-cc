# Plantilla de grupo

Para un grupo nuevo (`grupoNN`):

1. Copiar esta carpeta a `grupos/grupoNN/`.
2. Dentro de esa carpeta, una subcarpeta **por semana**, y dentro de cada
   semana, una subcarpeta **por tema** (proyecto/app puntual de esa
   semana), con su `docker-compose.yml`:
   ```
   grupos/grupoNN/
     semanaNN/
       <tema>/
         docker-compose.yml
   ```
   El identificador completo de esa app, en todos lados (Dagster, Portainer,
   la URL pública), sale de concatenar los tres niveles con `_`:
   **`grupoNN_semanaNN_<tema>`** (ej. `grupo01_semana02_mcpn8n`) — a
   propósito repetido con el número de grupo adentro, para que sea
   inconfundible sin importar dónde se lo vea (una captura, un log, una
   notificación), sin depender de que el agrupador esté visible al lado.
3. Dos puntos de partida según el caso, dentro de `semanaNN/<tema>/`:
   - **`semanaNN/ejemplo-n8n/`** — desplegar una app open source ya armada
     (imagen ya existente, ej. n8n, o cualquier otra herramienta).
   - **`semanaNN/ejemplo-script/`** — un script/pipeline propio (Python) que se
     empaqueta en un contenedor con una imagen base simple
     (`python:3.11-slim`) y corre una vez (`restart: "no"`). Para un
     servicio que debe quedarse corriendo (un servidor, una API), usar en
     su lugar el patrón de `ejemplo-n8n`.
4. Reglas obligatorias del `docker-compose.yml` (las valida el CI en el PR,
   y de nuevo el propio despliegue antes de tocar Docker — ver
   `ci/compose_policy.py`):
   - **`mem_limit`** en todo servicio.
   - Nada de `privileged: true`, `network_mode: host`, `pid: host`, ni
     `cap_add` peligroso (`SYS_ADMIN`, `ALL`, `NET_ADMIN`, `SYS_PTRACE`,
     `SYS_MODULE`).
   - Solo **volúmenes nombrados** (nunca bind-mounts a una ruta del host:
     nada de `./algo:/algo` ni `/ruta/absoluta:/algo`).
   - `container_name: lab-grupoNN_semanaNN_<tema>` fijo (el identificador
     completo del punto 2), y unirse a la red externa `lab_net` (copiar el
     bloque `networks:` del ejemplo).
5. **No hace falta tocar nada del repo de infraestructura.** El asset de
   Dagster se genera solo: el code-location escanea
   `grupos/<grupo>/<semana>/<tema>/docker-compose.yml` en cada recarga (que
   dispara el agente de deploy tras cada merge a `main`) y crea el asset
   automáticamente, con el identificador completo del punto 2 — agregar la
   carpeta con su `docker-compose.yml` ya es suficiente.
6. Si la app necesita ruta pública (para que el grupo la use en el
   navegador), agregar la ruta correspondiente en `caddy/Caddyfile` del
   repo de infraestructura (`handle /grupoNN/<identificador-completo>* { ...
   reverse_proxy lab-<identificador-completo>:<puerto> }`) — esa parte sí la
   hace el profesor, no va en este repo.
7. Abrir PR contra `main`. El profesor (CODEOWNERS) revisa y mergea — el
   despliegue real ocurre solo, automáticamente, cuando el agente de deploy
   detecta el merge (nunca hay botón de "Materialize" que un alumno pueda
   apretar).
