"""Reglas de seguridad para los docker-compose.yml de `grupos/*/apps/*/`.

COPIA — el original vive en el repo de infraestructura
(`dagster_project/lab_pipelines/compose_policy.py`), donde además lo usa
`docker_resource.py` como defensa en profundidad en el momento real del
despliegue. Este repo (`lab`) es público y solo tiene el contenido de los
alumnos + su CI, así que se duplica el archivo en vez de acoplar este repo
al de infraestructura (que puede ser privado). Si cambian las reglas, hay
que actualizar los dos.

Sin dependencias de Dagster a propósito: así el validador de CI no necesita
instalar nada más que PyYAML.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

# Prefijos que delatan un bind-mount (ruta de host) en vez de un volumen
# nombrado. Se exige volumen nombrado para que el despliegue -que corre
# dentro de un contenedor con acceso al socket de Docker del host- nunca
# pueda montar una ruta arbitraria del host de un PR no confiable, y para
# evitar el problema de traducción de rutas host/contenedor al usar
# docker-in-docker vía socket.
_BIND_MOUNT_PREFIXES = ("/", "./", "../", "~")

_DANGEROUS_CAPS = {"SYS_ADMIN", "ALL", "NET_ADMIN", "SYS_PTRACE", "SYS_MODULE"}


class CompolicyViolation(Exception):
    pass


def resolve_within_group(compose_path: os.PathLike, groups_root: os.PathLike, group: str) -> Path:
    """Resuelve compose_path y garantiza que caiga dentro de groups_root/<group>/.

    Bloquea path traversal (../../etc) y que un grupo apunte a la carpeta de otro.
    """
    groups_root = Path(groups_root).resolve()
    group_root = (groups_root / group).resolve()
    resolved = Path(compose_path).resolve()

    try:
        group_root.relative_to(groups_root)
    except ValueError as exc:
        raise CompolicyViolation(f"nombre de grupo inválido: {group!r}") from exc

    try:
        resolved.relative_to(group_root)
    except ValueError as exc:
        raise CompolicyViolation(
            f"{compose_path} está fuera de la carpeta permitida del grupo ({group_root})"
        ) from exc

    if not resolved.is_file():
        raise CompolicyViolation(f"{resolved} no existe o no es un archivo")

    return resolved


def _is_bind_mount(volume_entry) -> bool:
    if isinstance(volume_entry, dict):
        # forma larga: {type: bind, source: ..., target: ...}
        return volume_entry.get("type", "volume") == "bind"
    if isinstance(volume_entry, str):
        # "src:dst[:mode]" — si src empieza con uno de los prefijos de host, es bind mount.
        # "nombre_volumen:dst" (sin "/" al inicio ni ".") se considera volumen nombrado, válido.
        src = volume_entry.split(":", 1)[0]
        return src.startswith(_BIND_MOUNT_PREFIXES) or src == "."
    return False


def validate_compose_policy(compose_path: os.PathLike) -> list[str]:
    """Devuelve una lista de violaciones (vacía = cumple la política).

    Reglas (algunas del plan de infraestructura sección 1.4, otras endurecidas
    aquí porque el contenedor que ejecuta esto tiene acceso al socket de Docker
    del host):
      - todo servicio debe declarar mem_limit
      - ningún servicio puede usar privileged: true
      - ningún servicio puede usar network_mode/pid: host
      - ningún servicio puede agregar capabilities peligrosas (cap_add)
      - ningún volumen puede ser bind-mount de una ruta del host; solo
        volúmenes nombrados (evita montar rutas arbitrarias del host y evita
        el problema de traducción de rutas host/contenedor de docker-in-docker
        vía socket)
    """
    compose_path = Path(compose_path)
    with compose_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    violations: list[str] = []
    services = data.get("services") or {}
    if not services:
        violations.append("el compose no define ningún servicio en 'services:'")
        return violations

    for name, svc in services.items():
        svc = svc or {}

        has_mem_limit = bool(svc.get("mem_limit")) or bool(
            (svc.get("deploy") or {}).get("resources", {}).get("limits", {}).get("memory")
        )
        if not has_mem_limit:
            violations.append(f"servicio '{name}': falta mem_limit (o deploy.resources.limits.memory)")

        if svc.get("privileged") is True:
            violations.append(f"servicio '{name}': privileged: true no está permitido")

        if svc.get("network_mode") == "host":
            violations.append(f"servicio '{name}': network_mode: host no está permitido")

        if svc.get("pid") == "host":
            violations.append(f"servicio '{name}': pid: host no está permitido")

        cap_add = {str(c).upper() for c in (svc.get("cap_add") or [])}
        dangerous = cap_add & _DANGEROUS_CAPS
        if dangerous:
            violations.append(f"servicio '{name}': cap_add peligroso no permitido: {sorted(dangerous)}")

        if svc.get("devices"):
            violations.append(f"servicio '{name}': mapeo de 'devices' del host no está permitido")

        for vol in svc.get("volumes") or []:
            if _is_bind_mount(vol):
                violations.append(
                    f"servicio '{name}': volumen '{vol}' parece bind-mount de una ruta del host; "
                    "usar solo volúmenes nombrados (declarados en 'volumes:' top-level)"
                )

    return violations
