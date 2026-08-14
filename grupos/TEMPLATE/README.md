# Plantilla de grupo

Para un grupo nuevo (`gNN`):

1. Copiar esta carpeta a `grupos/gNN/`.
2. Dentro de `apps/`, una subcarpeta por app a desplegar, con su
   `docker-compose.yml` (ver `apps/ejemplo-n8n/docker-compose.yml`).
3. Reglas obligatorias del `docker-compose.yml` (las valida el CI en el PR,
   y de nuevo el propio despliegue antes de tocar Docker — ver
   `dagster_project/lab_pipelines/compose_policy.py`):
   - **`mem_limit`** en todo servicio.
   - Nada de `privileged: true`, `network_mode: host`, `pid: host`, ni
     `cap_add` peligroso (`SYS_ADMIN`, `ALL`, `NET_ADMIN`, `SYS_PTRACE`,
     `SYS_MODULE`).
   - Solo **volúmenes nombrados** (nunca bind-mounts a una ruta del host:
     nada de `./algo:/algo` ni `/ruta/absoluta:/algo`).
   - `container_name: lab-gNN-<app>` fijo, y unirse a la red externa
     `lab_net` (copiar el bloque `networks:` del ejemplo).
4. Agregar una entrada en `dagster_project/lab_pipelines/assets/app_deploy.py`
   → `APP_REGISTRY`, con `group`, `app`, y `compose_relpath`.
5. Agregar la ruta correspondiente en `caddy/Caddyfile`
   (`handle /gNN/<app>* { ... reverse_proxy lab-gNN-<app>:<puerto> }`).
6. Abrir PR contra `main`. El profesor (CODEOWNERS) revisa y mergea — el
   despliegue real ocurre solo, automáticamente, cuando el agente de deploy
   detecta el merge (nunca hay botón de "Materialize" que un alumno pueda
   apretar).
