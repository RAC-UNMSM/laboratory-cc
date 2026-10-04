"""
core/trabajador.py — Proceso de cálculo independiente (lo lanza server.py).

Protocolo muy simple por tuberías PROPIAS (no las del cliente MCP):
    entrada  (stdin)  : una línea JSON por pedido  {"metodo": ..., "solicitud": {...}, "carpeta": "..."}
    salida   (stdout) : una línea JSON por respuesta (la de core.motor.ejecutar)

¿Por qué un proceso aparte?  Para poder MATARLO si un cálculo simbólico se eterniza
(el servidor responde 'TIEMPO_AGOTADO' y lanza otro trabajador limpio).

¿Por qué no multiprocessing?  En Windows, crear procesos con multiprocessing desde un
servidor que está leyendo su propio stdin (como hace todo servidor MCP STDIO) puede dejar
la creación del proceso bloqueada para siempre. Con subprocess y tuberías explícitas no pasa.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.environ.setdefault("MPLBACKEND", "Agg")


def main() -> None:
    entrada, salida = sys.stdin.buffer, sys.stdout.buffer
    sys.stdout = sys.stderr                       # cualquier print accidental va a stderr, nunca a la respuesta
    from core.motor import ejecutar, inicializar_proceso
    inicializar_proceso()                         # precarga SymPy, NumPy, matplotlib, Jinja2
    salida.write(b'{"listo": true}\n')
    salida.flush()
    for linea in entrada:
        if not linea.strip():
            continue
        try:
            p = json.loads(linea)
            r = ejecutar(p["metodo"], p["solicitud"], p.get("carpeta"))
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "error": {"tipo": "interno", "codigo": "ERROR_INTERNO",
                                        "mensaje": f"{type(e).__name__}: {e}", "sugerencia": ""}}
        salida.write(json.dumps(r, ensure_ascii=True, default=str).encode("ascii") + b"\n")
        salida.flush()


if __name__ == "__main__":
    main()
