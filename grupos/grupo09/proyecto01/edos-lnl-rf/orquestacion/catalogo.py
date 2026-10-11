"""Carga y validación del balotario del grupo (`balotario/tema_*.json`).

Es el portero del catálogo: garantiza que los archivos estén bien formados y que
los identificadores no colisionen, pero no interpreta la matemática. Un `campo`
se vuelve función en `matematica.expresiones`, no aquí; esa separación permite
probar la consistencia del catálogo con datos de juguete, sin el solver.

La carpeta se localiza con `Path(__file__)` y no con el directorio de trabajo,
porque el servidor MCP se lanza con un cwd ajeno al proyecto: Claude Desktop y
`claude mcp add` arrancan el proceso desde donde les conviene.
"""

import json
from pathlib import Path

BALOTARIO = Path(__file__).resolve().parents[1] / "balotario"


def cargar_catalogo(directorio=None):
    """Carga los temas y rechaza identificadores duplicados o datos incompletos."""
    ruta = Path(directorio) if directorio is not None else BALOTARIO
    if not ruta.is_dir():
        raise ValueError(f"No existe el directorio del balotario: {ruta}")
    temas = []
    ids_temas, ids_problemas = set(), set()
    for archivo in sorted(ruta.glob("tema_*.json")):
        try:
            contenido = json.loads(archivo.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"JSON inválido: {archivo.name}") from exc
        if not isinstance(contenido, dict) or contenido.get("schema_version") != 1:
            raise ValueError(f"Versión de catálogo inválida: {archivo.name}")
        tema = contenido.get("tema")
        problemas = contenido.get("problemas")
        if not isinstance(tema, dict) or not isinstance(problemas, list):
            raise ValueError(f"Faltan tema o problemas: {archivo.name}")
        identificador = tema.get("id")
        if not isinstance(identificador, str) or not identificador.strip() or identificador in ids_temas:
            raise ValueError(f"Identificador de tema inválido o duplicado: {archivo.name}")
        ids_temas.add(identificador)
        for problema in problemas:
            identificador = problema.get("id") if isinstance(problema, dict) else None
            if not isinstance(identificador, str) or not identificador.strip() or identificador in ids_problemas:
                raise ValueError(f"Identificador de problema inválido o duplicado: {archivo.name}")
            ids_problemas.add(identificador)
        temas.append(contenido)
    return temas
