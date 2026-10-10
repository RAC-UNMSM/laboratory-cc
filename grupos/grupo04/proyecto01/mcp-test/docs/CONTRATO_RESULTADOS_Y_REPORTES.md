# Contrato de resultados y documentación generada

## 1. Salida común

Todas las respuestas son consumibles sin la MCP App. Campos recomendados:

- schema_version, problem_type, status;
- method y motivo si se recomendó automáticamente;
- inputs normalizados, parámetros y unidades;
- result con los valores principales;
- diagnostics con residuo, error, iteraciones, convergencia o condición;
- steps con desarrollo pertinente;
- tables con columnas/unidades;
- charts con series acotadas, etiquetas y leyenda;
- warnings con hipótesis y limitaciones;
- report con estado y enlaces;
- error con código y explicación si falla la entrada o el cálculo.

No representar valores numéricos ausentes con guiones. Mantener precisión interna separada de cifras mostradas. Limitar tablas, iteraciones y muestras de gráfica; anunciar truncamiento.

## 2. Compatibilidad de clientes

Devolver estructura tipada si el SDK lo permite y resumen textual legible. UI tolerante a structuredContent, JSON textual y bloques content de texto. La respuesta funciona aunque un cliente no soporte MCP Apps; no prometer igual presentación entre ChatGPT, Claude e Inspector. Versionar el recurso UI al cambiar contratos.

## 3. Códigos de error

INVALID_SHAPE, NON_FINITE_VALUE, DUPLICATE_NODES, SINGULAR_SYSTEM, METHOD_NOT_APPLICABLE, NO_CONVERGENCE, OUT_OF_DOMAIN, RESOURCE_LIMIT, REPORT_FAILED y REPORT_NOT_FOUND. Cada error indica campo, formato esperado y ejemplo. No revelar trazas, rutas internas, credenciales ni variables de entorno.

## 4. Contenido del PDF de cada resolución

1. Tipo de problema, fecha UTC, versión y estado.
2. Enunciado y entradas normalizadas.
3. Método, parámetros y razón.
4. Supuestos y dominio.
5. Fórmulas y desarrollo.
6. Tabla numérica acotada.
7. Resultado principal y unidades disponibles.
8. Error/residuo, convergencia y condicionamiento pertinentes.
9. Gráfica rotulada.
10. Advertencias y datos necesarios para reproducir el cálculo.

En comparaciones, mostrar métodos lado a lado y no llamar error verdadero a la diferencia entre métodos sin justificación.

## 5. storage y enlaces

storage.py será la capa única para guardar y resolver PDFs; nombres impredecibles y rutas confinadas al directorio configurado. Preview usa inline; download, attachment. Docker monta volumen nombrado. app.py configura carpeta local y base HTTPS antes de iniciar server.py. Cloudflare ingress debe enrutar /mcp y /reports antes del fallback 404. Documentar que borrar el volumen elimina los informes. URLs configurables por entorno.

## 6. Documentación que acompaña las versiones

- README.md: alcance, requisitos, modo local/Docker, Inspector, persistencia y errores comunes.
- CATALOGO_HERRAMIENTAS.md: argumentos, defaults, métodos, límites y ejemplos por tool.
- GUIA_DE_USO.md: solicitudes en lenguaje natural y lectura de resultados, tablas, gráficas y PDF.
- REFERENCIA_ALGORITMOS.md: fórmulas, pseudocódigo, supuestos y orden de error solo de métodos implementados.
- GUIA_DESPLIEGUE.md: server local, Docker, túnel, rutas, volumen y reinicio.
- HISTORIAL_CAMBIOS.md: versiones, tools y cambios incompatibles.
- Cada ejecución puede producir PDF específico y, opcionalmente, JSON reproducible.

La documentación distingue lo implementado, lo planificado y lo que está fuera de alcance.

## Contrato 1.1 y nivel explicativo

El sobre común incluye `schema_version`, `problem_type`, `status`, `method`, `level`, `inputs`, `result`, `diagnostics`, `steps`, `tables`, `charts`, `warnings` y `report`. Las tools de interpolación conservan además sus campos históricos para no romper el recurso UI anterior.

`level` puede ser `inicial` o `intermedio`; indica la profundidad de explicación que presenta la interfaz y el PDF. Ambos niveles conservan los valores calculados por el método. `include_report=false` devuelve el resultado sin compilar ni persistir un PDF; el valor predeterminado sigue generando el reporte.

El reporte ofrece `preview_url` y `download_url` cuando la generación termina. ReportLab procesa reportes de forma serializada; tablas extensas y trazos se acotan para mantener un consumo controlado. `storage.py` genera nombres aleatorios, valida que la ruta permanezca dentro de `reports/` y sirve vista previa/descarga.
