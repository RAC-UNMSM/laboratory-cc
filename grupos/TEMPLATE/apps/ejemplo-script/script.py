"""Plantilla mínima de script/pipeline propio.

Reemplazar esta lógica por la del ejercicio del grupo (ej. un paso de un
pipeline ETL, un procesamiento de datos, lo que pida la semana del sílabo).
Al desplegarse (mismo patrón automático de Fase 5), esto corre una vez y
termina — para algo de larga duración (un servidor, una API), usar en su
lugar algo como el ejemplo de n8n (un proceso que se queda corriendo).
"""

import datetime


def main() -> None:
    print(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] script propio del grupo ejecutado")
    # TODO (alumnos): reemplazar con la lógica real del ejercicio.


if __name__ == "__main__":
    main()
