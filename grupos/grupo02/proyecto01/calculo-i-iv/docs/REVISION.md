# Revisión y cambios

## Alcance de lectura

Se revisó el README raíz, la documentación del validador y su referencia de
despliegue, el CI/política de Compose y la plantilla MCP de `templates/`.
Dentro de `grupos/` se revisaron solo `grupo01` y `grupo02`: documentación,
propuestas, integrantes y código del proyecto del grupo01. No se revisaron
los proyectos de g01, TEMPLATE, _referencia ni los demás grupos. Los documentos
privados de infraestructura enlazados por el README no estaban adjuntos.

La habilidad local mcp-validator se aplicó respetando ese alcance: no se leyó
su piloto g01. El pedido del usuario de implementar y revisar matemáticas
prevalece sobre la limitación de esa habilidad a revisar solo despliegue.

## Hallazgos y respuesta

| Hallazgo inicial | Acción en grupo02 |
|---|---|
| Solo existía una propuesta; ningún servidor desplegable | Implementación completa modular con tests y archivos de despliegue |
| README de grupo era una plantilla genérica | Navegación y estado concretos del proyecto |
| Plantillas antiguas contradicen el contrato específico | SDK 2.1.1, MCPServer, Streamable HTTP y nombre inyectado |
| Promesa de resolver cualquier ejercicio exactamente | Alcance explícito de 20 operaciones y estados no_resuelto/no_finito |
| Una skill no crea otra ventana del LLM | Prompts separados, contexto/progreso administrados por el cliente |
| Un timeout con ThreadPoolExecutor no mata el cálculo | Procesos efímeros con cancelación, límite de tiempo/CPU/memoria |
| Parsing simbólico de texto requiere controles | AST cerrado y Pydantic; sin evaluación de Python recibido |
| Simplificaciones pueden borrar huecos del dominio | Conservación de restricciones en continuidad y tutor |
| Resultados numéricos pueden fallar para símbolos/infinito | Exacto/LaTeX y decimal solo cuando corresponde |
| Dependencias sin fijación completa dificultan reproducir | requirements directos más lock transitivo con hashes |
| Almacenamiento no siempre disponible | PNG embebido y fallo opcional de SeaweedFS |

El grupo01 se usó como referencia de organización, no se modificó ni se copió
su implementación. Tampoco se modificaron raíz, CI ni otros grupos.

## Datos de integrantes

Se corrigieron erratas de declaraciones y se completó el archivo vacío de
Jefferson a partir de su nombre ya incluido en la tabla. Se añadió la declaración
de Yhin a partir de la propuesta. Se mantuvo el archivo de Julios: su presencia
y el prefijo grupo01 contradicen la lista de seis integrantes; no hay evidencia
suficiente para eliminarlo o asignarle un rol. Confirmar administrativamente.
Los usuarios de GitHub de la tabla no se verificaron externamente y no deben
asumirse correctos solo porque coinciden con la parte inicial del correo.

## Fuentes técnicas de verificación

- Contrato y CI del ZIP suministrado (fuente principal para despliegue).
- SDK oficial: https://github.com/modelcontextprotocol/python-sdk
- Versión fijada: https://pypi.org/project/mcp/2.1.1/
- API y firmas comprobadas además sobre el paquete 2.1.1 instalado.

No se declara compatibilidad con versiones futuras ni con otras
infraestructuras sin pruebas. Ver VALIDACION.md para evidencia y pendientes.
