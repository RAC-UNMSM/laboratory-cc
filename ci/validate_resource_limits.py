#!/usr/bin/env python3
"""Validador de CI: recorre los docker-compose.yml de cada grupo y rechaza
cualquiera que no cumpla la política de recursos/privilegios (ver
compose_policy.py). Se corre en cada PR contra `main` (ver
.github/workflows/ci.yml) — es lo que hace cumplir, de forma automática,
las reglas descritas en grupos/TEMPLATE/README.md.

Dos convenciones de carpetas, según el grupo:
  - grupos/_referencia/apps/<app>/docker-compose.yml (2 niveles, curado por
    el profesor, sin "semana").
  - grupos/<grupo>/<semana>/<tema>/docker-compose.yml (3 niveles, para
    grupos de alumnos).

Uso: python3 ci/validate_resource_limits.py
Sale con código != 0 si hay al menos una violación (falla el job de CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_policy import CompolicyViolation, resolve_within_group, validate_compose_policy  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
GROUPS_ROOT = REPO_ROOT / "grupos"


def find_compose_files() -> list[tuple[str, Path]]:
    found = []
    if not GROUPS_ROOT.is_dir():
        return found
    for group_dir in sorted(GROUPS_ROOT.iterdir()):
        if not group_dir.is_dir() or group_dir.name == "TEMPLATE":
            continue
        group = group_dir.name

        if group == "_referencia":
            apps_dir = group_dir / "apps"
            if not apps_dir.is_dir():
                continue
            for app_dir in sorted(apps_dir.iterdir()):
                compose_file = app_dir / "docker-compose.yml"
                if compose_file.is_file():
                    found.append((group, compose_file))
            continue

        for semana_dir in sorted(group_dir.iterdir()):
            if not semana_dir.is_dir():
                continue
            for tema_dir in sorted(semana_dir.iterdir()):
                compose_file = tema_dir / "docker-compose.yml"
                if compose_file.is_file():
                    found.append((group, compose_file))
    return found


def main() -> int:
    compose_files = find_compose_files()
    if not compose_files:
        print("No se encontraron docker-compose.yml bajo grupos/ — nada que validar.")
        return 0

    had_errors = False
    for group, compose_file in compose_files:
        rel = compose_file.relative_to(REPO_ROOT)
        try:
            resolve_within_group(compose_file, GROUPS_ROOT, group)
        except CompolicyViolation as exc:
            print(f"FALLO [{rel}]: {exc}")
            had_errors = True
            continue

        violations = validate_compose_policy(compose_file)
        if violations:
            had_errors = True
            print(f"FALLO [{rel}]:")
            for v in violations:
                print(f"  - {v}")
        else:
            print(f"OK    [{rel}]")

    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
