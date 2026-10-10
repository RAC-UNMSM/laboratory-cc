from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from validacion import validar_transformacion


def probar_caso(nombre, n, regla, debe_ser_valido):
    """
    Ejecuta un caso de prueba y muestra si el resultado
    coincide con lo esperado.
    """

    print("=" * 70)
    print(nombre)
    print(f"n = {n}")
    print(f"regla = {regla}")

    try:
        resultado = validar_transformacion(
            n,
            regla
        )

        if debe_ser_valido:
            print("RESULTADO: CORRECTO")
            print("La transformación fue aceptada.")

            print(
                "Variables:",
                resultado["variables"]
            )

            print(
                "Componentes:",
                resultado["componentes"]
            )

        else:
            print("RESULTADO: ERROR EN LA PRUEBA")
            print(
                "La transformación debía ser rechazada, "
                "pero fue aceptada."
            )

    except ValueError as error:

        if debe_ser_valido:
            print("RESULTADO: ERROR EN LA PRUEBA")
            print(
                "La transformación debía ser aceptada."
            )
            print("Mensaje:", error)

        else:
            print("RESULTADO: CORRECTO")
            print(
                "La transformación fue rechazada "
                "como se esperaba."
            )
            print("Motivo:", error)

    print()


# ============================================================
# CASO 1
# Transformación lineal válida usando *
# ============================================================

probar_caso(
    nombre="CASO 1 - TL válida con multiplicación explícita",
    n=2,
    regla=[
        "2*x1 + x2",
        "x1 - x2"
    ],
    debe_ser_valido=True
)


# ============================================================
# CASO 2
# Transformación lineal válida sin escribir *
# ============================================================

probar_caso(
    nombre="CASO 2 - TL válida escribiendo 2x1",
    n=2,
    regla=[
        "2x1 + x2",
        "x1 - x2"
    ],
    debe_ser_valido=True
)


# ============================================================
# CASO 3
# Transformación en R4
# ============================================================

probar_caso(
    nombre="CASO 3 - TL válida en R4",
    n=4,
    regla=[
        "x1 + x2",
        "x2 + x3",
        "x3 + x4",
        "x4"
    ],
    debe_ser_valido=True
)


# ============================================================
# CASO 4
# Tiene término independiente
# ============================================================

probar_caso(
    nombre="CASO 4 - Constante distinta de cero",
    n=2,
    regla=[
        "x1 + 5",
        "x2"
    ],
    debe_ser_valido=False
)


# ============================================================
# CASO 5
# Producto entre variables
# ============================================================

probar_caso(
    nombre="CASO 5 - Producto x1*x2",
    n=2,
    regla=[
        "x1*x2",
        "x2"
    ],
    debe_ser_valido=False
)


# ============================================================
# CASO 6
# Potencia de una variable
# ============================================================

probar_caso(
    nombre="CASO 6 - Potencia x1^2",
    n=2,
    regla=[
        "x1^2",
        "x2"
    ],
    debe_ser_valido=False
)


# ============================================================
# CASO 7
# Cantidad incorrecta de componentes
# ============================================================

probar_caso(
    nombre="CASO 7 - Número incorrecto de componentes",
    n=2,
    regla=[
        "x1",
        "x2",
        "x1 + x2"
    ],
    debe_ser_valido=False
)


# ============================================================
# CASO 8
# Variable que no pertenece al dominio
# ============================================================

probar_caso(
    nombre="CASO 8 - Variable no permitida",
    n=2,
    regla=[
        "x1 + x3",
        "x2"
    ],
    debe_ser_valido=False
)


# ============================================================
# CASO 9
# Componente igual a cero: sí está permitida
# ============================================================

probar_caso(
    nombre="CASO 9 - Componente cero",
    n=2,
    regla=[
        "x1",
        "0"
    ],
    debe_ser_valido=True
)


# ============================================================
# CASO 10
# Construcción que no debe ejecutarse como código
# ============================================================

probar_caso(
    nombre="CASO 10 - Función no permitida",
    n=2,
    regla=[
        "sin(x1)",
        "x2"
    ],
    debe_ser_valido=False
)