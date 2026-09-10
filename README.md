# lab — Lab IA/MCP (curso UNMSM 183083)

Repo **público** de contenido del curso: una carpeta por grupo con las apps
que despliegan. Este repo es intencionalmente independiente del repo de
infraestructura (Dagster, Caddy, oauth2-proxy, agente de deploy) — ver
sección 1.3 del plan (`docs/plan-infraestructura.md` en el repo de
infraestructura) para el razonamiento completo.

## Estructura

```
grupos/
  TEMPLATE/           <- copiar para un grupo nuevo (ver su README.md)
  _referencia/         <- MCP servers de referencia, curados por el profesor (2 niveles: apps/<app>/)
  grupo01/, grupo02/, ...  <- un grupo por carpeta
    semanaNN/              <- una subcarpeta por semana
      <tema>/                <- proyecto puntual de esa semana
        docker-compose.yml     <- obligatorio, ver reglas abajo
                                   (identificador completo: grupoNN_semanaNN_<tema>)
templates/
  simple_mcp_server/    <- plantilla de MCP server propio (semana 13+)
ci/
  validate_resource_limits.py   <- corre en cada PR (ver .github/workflows/ci.yml)
  compose_policy.py             <- reglas (copia del repo de infraestructura)
.github/
  CODEOWNERS           <- bloquea merges a main sin revisión del profesor
  workflows/ci.yml
```

## Primera tarea de cada grupo

El plan detallado de cada semana (qué investigar, qué desplegar, entregables)
vive en `docs/semana-01/plan.md` y `docs/semana-02/plan.md` **del repo de
infraestructura** (`architecture-sm`, privado) — no en este repo. Resumen:

- **Semana 1**: sin despliegue todavía — cada grupo investiga el repo, la
  documentación y el grafo de conocimiento del laboratorio para encontrar
  por su cuenta dónde está aplicado el modelo cliente-servidor visto en
  clase.
- **Semana 2**: primer despliegue real — cada grupo crea `grupos/grupoNN/`
  vía PR y despliega un servidor MCP de referencia (sin necesidad de
  tokens ni cuentas pagas).

## Reglas de todo `docker-compose.yml` de grupo

Ver `grupos/TEMPLATE/README.md` para el detalle completo. Resumen:
`mem_limit` obligatorio, nada de `privileged`/`network_mode: host`/`cap_add`
peligroso, solo volúmenes nombrados (sin bind-mounts a rutas del host),
`container_name: lab-grupoNN_semanaNN_<tema>` fijo (identificador completo),
red externa `lab_net`.

## Cómo llega esto a producción

1. Un grupo abre PR contra `main` con su carpeta `grupos/grupoNN/semanaNN/<tema>/`.
2. CI (`.github/workflows/ci.yml`) valida las reglas de arriba y hace un
   "dev-run" efímero (build + up + logs + down) publicando el resultado
   como comentario en el PR.
3. El profesor (único CODEOWNER) revisa y mergea.
4. En la laptop del profesor, el agente de deploy del repo de
   infraestructura detecta el merge (`git pull` de este repo) y dispara,
   vía un sensor de Dagster, el despliegue real — nunca hay un botón de
   "Materialize" que un alumno pueda apretar (sección 1.2 del plan).

Este repo **nunca** ejecuta código en la laptop del profesor directamente:
el CI corre en runners de GitHub, no en la laptop (sección 1.4 del plan) —
evita que un PR malicioso tenga RCE sobre el servidor real.

<!-- prueba: dispara el primer CI para poder seleccionar status checks en el ruleset -->
