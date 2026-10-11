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
   El identificador completo de esa app, en todos lados (Portainer, los logs,
   la URL pública), sale de concatenar los tres niveles con `_`:
   **`grupoNN_semanaNN_<tema>`** (ej. `grupo01_semana02_mcpn8n`) — a
   propósito repetido con el número de grupo adentro, para que sea
   inconfundible sin importar dónde se lo vea (una captura, un log, una
   notificación), sin depender de que el agrupador esté visible al lado.
3. Dos puntos de partida según el caso, dentro de `semanaNN/<tema>/` (ver
   `semana01/` en esta misma plantilla como ejemplo concreto):
   - **`ejemplo-n8n/`** — desplegar una app open source ya armada
     (imagen ya existente, ej. n8n, o cualquier otra herramienta).
   - **`ejemplo-script/`** — un script/pipeline propio (Python) que se
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
   - `container_name: ${LAB_CONTAINER_NAME}` fijo tal cual (variable, no
     texto literal — el despliegue la calcula solo a partir de la ruta de
     la carpeta y la inyecta; no hay nada que reemplazar a mano ni riesgo
     de escribirla mal), y unirse a la red externa `lab_net` (copiar el
     bloque `networks:` del ejemplo). Si la app necesita conocer su propia
     ruta pública (como el `N8N_PATH`/`WEBHOOK_URL` del ejemplo de n8n),
     usar igual la variable automática `${LAB_PUBLIC_PATH}`. Para el
     storage de imágenes hay otras dos, `${LAB_IMG_BUCKET}` y
     `${LAB_PUBLIC_IMG_URL}`, que se pasan al contenedor con `environment:`
     (ver `grupos/g01/semana01/derivadas1/docker-compose.yml`).
5. **No hace falta tocar nada del repo de infraestructura.** El despliegue
   descubre la app solo: tras cada merge a `main` busca
   `grupos/<grupo>/<semana>/<tema>/docker-compose.yml` y despliega las
   carpetas que cambiaron, con el identificador completo del punto 2 —
   agregar la carpeta con su `docker-compose.yml` ya es suficiente.
6. La ruta pública de un servidor MCP propio (carpeta con `server.py`,
   escuchando en el puerto 8000) se crea sola al desplegar:
   `${LAB_PUBLIC_PATH}` hacia `${LAB_CONTAINER_NAME}:8000`, y la de imágenes
   si tiene `storage.py`. Cualquier otra app que necesite ruta pública (una
   imagen ya hecha, otro puerto) la agrega el profesor a mano en el repo de
   infraestructura: hay que pedírsela.
7. Abrir PR contra `main`. El profesor revisa y mergea (solo él
   puede actualizar `main`) — el despliegue real ocurre solo,
   automáticamente, al llegar el merge (nunca hay un botón de despliegue
   que un alumno pueda apretar).
