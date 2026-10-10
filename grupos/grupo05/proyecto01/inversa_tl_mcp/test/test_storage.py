from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import storage


# ============================================================
# 1. USAR UN ARCHIVO DE PRUEBA DENTRO DE test
# ============================================================

ruta_prueba = (
    Path(__file__).parent
    / "historial_prueba.jsonl"
)

storage.RUTA_DATOS = ruta_prueba


# ============================================================
# 2. LIMPIAR UNA PRUEBA ANTERIOR
# ============================================================

if ruta_prueba.exists():
    ruta_prueba.unlink()


# ============================================================
# 3. GUARDAR REGISTROS DE PRUEBA
# ============================================================

storage.guardar_registro(
    n=2,
    regla=[
        "2*x1 + x2",
        "x1 + x2"
    ],
    estado="invertible",
    resultado={
        "determinante": 1
    }
)

storage.guardar_registro(
    n=2,
    regla=[
        "x1 + x2",
        "2*x1 + 2*x2"
    ],
    estado="no_invertible",
    resultado={
        "determinante": 0
    }
)

storage.guardar_registro(
    n=2,
    regla=[
        "x1 + 5",
        "x2"
    ],
    estado="entrada_invalida",
    resultado={
        "motivo": (
            "La componente 1 contiene "
            "un término independiente distinto de 0."
        )
    }
)


# ============================================================
# 4. LEER EL HISTORIAL
# ============================================================

historial = storage.leer_historial()


# ============================================================
# 5. COMPROBAR RESULTADOS
# ============================================================

print("Prueba de almacenamiento completada.")
print(f"Cantidad de registros: {len(historial)}")
print()

for numero, registro in enumerate(
    historial,
    start=1
):
    print(f"REGISTRO {numero}")
    print("Fecha:", registro["fecha_hora"])
    print("n:", registro["n"])
    print("Regla:", registro["regla"])
    print("Estado:", registro["estado"])
    print("Resultado:", registro["resultado"])
    print("-" * 60)


if len(historial) == 3:
    print("RESULTADO: CORRECTO")
else:
    print("RESULTADO: ERROR EN LA PRUEBA")