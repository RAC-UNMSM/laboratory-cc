"""Entrada interna por stdin; no es una herramienta ni ejecuta código del cliente."""

import json
import sys


def main():
    # Límite aplicado antes de importar el motor. El contenedor además limita RAM.
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        resource.setrlimit(resource.RLIMIT_AS, (448 * 1024**2, 448 * 1024**2))
    except ImportError:
        pass  # Windows: el timeout sigue activo; producción se ejecuta en Linux.
    from validacion import EntradaError

    try:
        data = json.loads(sys.stdin.buffer.read(24001))
        if data["action"] == "resolver":
            from engine import solve

            result = solve(data["payload"])
        elif data["action"] == "grafica":
            from visualizacion import render

            result = render(**data["payload"])
        elif data["action"] == "verificar":
            from tutor import verify

            result = verify(**data["payload"])
        else:
            raise EntradaError("Acción desconocida.")
        output = json.dumps(result, ensure_ascii=False, allow_nan=False)
        if len(output.encode()) > 900000:
            raise EntradaError("Resultado demasiado grande; reduzca la expresión.")
    except EntradaError as exc:
        output = json.dumps(
            {"estado": "error", "codigo": "entrada", "mensaje": str(exc)},
            ensure_ascii=False,
        )
    except (NotImplementedError, RecursionError, MemoryError):
        output = json.dumps(
            {
                "estado": "no_resuelto",
                "mensaje": "El motor no pudo resolver este caso dentro del alcance disponible.",
            }
        )
    except Exception:
        # No divulgar rutas internas ni trazas al cliente.
        output = json.dumps(
            {
                "estado": "error",
                "codigo": "interno",
                "mensaje": "No se pudo completar esta operación.",
            }
        )
    sys.stdout.write(output)


if __name__ == "__main__":
    main()
