# Despliegue del grupo02

## Contrato

Ruta: `grupos/grupo02/proyecto01/calculo-i-iv/`. Nombre MCP:
`grupo02-calculo-i-iv`. Compose conserva `${LAB_CONTAINER_NAME}` y red externa
`lab_net`; no publica puertos del host. Memoria 512 MiB, CPU 1, 64 procesos.
Se usa el contrato específico `referencia-despliegue.md` y el CI actual; la
plantilla genérica antigua contiene instrucciones distintas de nombres y SSE.

| Parámetro | Valor o procedencia |
|---|---|
| Transporte | Streamable HTTP, stateless, JSON, puerto 8000, ruta /mcp |
| LAB_CONTAINER_NAME | Inyectado: lab-grupo02_proyecto01_calculo-i-iv |
| LAB_DOMAIN | Dominio del laboratorio, inyectado para validar Host/Origin |
| LAB_IMG_BUCKET | Inyectado: grupo02-calculo-i-iv-imgs |
| LAB_PUBLIC_IMG_URL | Inyectado: https://rac-unmsm.vekthos.org/img/grupo02-calculo-i-iv |
| Red | lab_net, externa, provista por infraestructura |
| Almacenamiento | SeaweedFS S3 http://seaweedfs:8333, bucket creado por infraestructura |

URL esperada después de la fusión y despliegue (no comprobada en esta entrega):
`https://rac-unmsm.vekthos.org/grupo02/grupo02_proyecto01_calculo-i-iv/mcp`.

## Construcción local con Docker

```bash
docker build -t grupo02-calculo-i-iv:1.0.0 .
docker run --rm --read-only --tmpfs /tmp:size=32m,mode=1777 \
  --memory=512m --cpus=1 --pids-limit=64 --cap-drop=ALL \
  --security-opt=no-new-privileges \
  -p 127.0.0.1:8000:8000 grupo02-calculo-i-iv:1.0.0
```

Este comando local deja almacenamiento opcional desactivado. La red y las
variables las prepara el despliegue del laboratorio; no crear sustitutos en
producción. No usar el ZIP como archivo dentro del repositorio: extraer y
subir solo los cambios de `grupos/grupo02/`.

## Flujo de entrega

Desde un clon real y su rama del grupo:

```bash
git fetch origin
python .claude/skills/mcp-validator/scripts/validar_entrega.py grupo02
```

Revisar el diff: solo grupo02. Abrir PR cuando el grupo lo decida. El profesor
fusiona; webhook, build y proxy pertenecen a infraestructura. No se ejecutó
push, PR ni merge desde la revisión del ZIP.

## Aceptación en el entorno real

1. Ejecutar pruebas y build con las dependencias fijadas. Comprobar salud,
   usuario no root y límites con Docker; el healthcheck TCP es solo vivacidad.
2. Con un cliente MCP verificar initialize, tools/list, resolver de x² entre
   0 y 3 (=9), prompts y recurso; HTTP 200 por sí solo no prueba que funcione.
3. Probar desde la URL del proxy con credenciales autorizadas; verificar
   rechazo de clientes sin acceso, Host correcto y rate limiting.
4. Graficar x² de 0 a 1, comprobar PNG embebido, subida al bucket y URL pública.
5. Revisar logs y consumo real bajo la carga esperada; esta entrega serializa
   cálculos y no está dimensionada como un servicio multiusuario de alta carga.
6. Conservar referencia de imagen/commit anterior para rollback. Ante fallo,
   el administrador restaura la versión previa y verifica el protocolo.

## Mensaje para Julios Castillo Melchor

> Grupo02 entrega la app grupo02_proyecto01_calculo-i-iv con MCP 2.1.1, puerto
> 8000 y 512 MiB. Usa solamente la red y SeaweedFS ya previstos. Favor comprobar
> la provisión de LAB_CONTAINER_NAME, LAB_DOMAIN, LAB_IMG_BUCKET y
> LAB_PUBLIC_IMG_URL, el bucket calculado y que Caddy preserve el Host público.
> El servicio usa usuario 10001, raíz read_only y tmpfs /tmp de 32 MiB.
> La autenticación, TLS, control de tráfico y retención de imágenes quedan en
> infraestructura. No solicita base de datos, claves de IA, volúmenes persistentes
> ni servicios adicionales. Falta ejecutar el build y las pruebas de aceptación
> contra el proxy/SeaweedFS reales antes de declarar producción validada.
