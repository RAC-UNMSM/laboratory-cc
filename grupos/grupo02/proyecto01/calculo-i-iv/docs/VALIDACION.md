# Evidencia de validación

Fecha: 10 de octubre de 2026 UTC (sesión iniciada el 9 de octubre en Lima).

## Resultado ejecutado

- **97 pruebas aprobadas**, Python 3.11.17, Linux x86_64.
- Entorno limpio instalado desde `requirements.lock` con verificación de hashes:
  MCP 2.1.1, SymPy 1.14.0, Pydantic 2.12.5, NumPy 2.3.5 y Matplotlib 3.10.8.
- Ruff: comprobación de código y formato. Sin errores tras las correcciones.
- Política `ci/compose_policy.py` aplicada solo al Compose del grupo02: conforme.
- Validador original del repositorio aplicado a grupo02. Informe literal:
  [VALIDADOR.txt](VALIDADOR.txt).
- Integración MCP en memoria y por **HTTP real**, arrancando `python server.py`.
  Listado y llamada de herramientas, esquema inválido, prompts, recursos,
  respuesta estructurada, initialize legado 2025-03-26 y cliente SDK actual.
- Rechazo HTTP de Host no autorizado (421) y cuerpo excesivo (413).
- Timeout duro con un proceso lento, recuperación posterior, cancelación y
  rechazo de trabajo concurrente. Parser: intentos de ejecución de código,
  atributos, indexación, expresiones profundas/grandes y funciones no permitidas.
- Casos de los cuatro cursos: resultados exactos, límites laterales y oscilatorios,
  continuidad con huecos, integrales impropias, orientación y límites dependientes.
- Lecciones y verificación del tutor, PNG reales y almacenamiento con mocks.

Comando reproducible, desde la carpeta del proyecto:

```bash
python -m pytest -q
```

Salida de la última ejecución:

```text
........................................................................ [ 74%]
.........................                                                [100%]
97 passed in 5.80s
```

## Qué no está verificado

**No hay Docker disponible en este entorno.** No se ejecutó `docker build`,
Compose, healthcheck dentro del contenedor ni una medición bajo cgroups de
512 MiB. Se comprobó instalación en Python 3.11 y arranque real del mismo
`server.py`, pero eso no sustituye el build de la imagen.

**No se dispone de acceso a SeaweedFS ni al proxy del profesor.** Subida,
URL pública, autenticación, TLS, rate limiting, retención de imágenes y carga
real quedan pendientes. La URL documentada es esperada, no un despliegue activo.

El ZIP no incluye `.git` ni una referencia `origin/main`: no se realizó fetch
ni validación de historial/diff frente a una rama remota. No se fabricó un
historial para ocultar esa limitación. El validador avisa de ello. También
avisa de URLs localhost que aquí son orígenes permitidos para clientes locales,
no destinos de almacenamiento; el destino real es `seaweedfs:8333`.

Los tests no certifican todos los ejercicios posibles, hipótesis de teoremas,
ni ausencia universal de vulnerabilidades. La aceptación final de producción
está descrita en DESPLIEGUE.md. No se efectuó push, PR, merge ni despliegue.
