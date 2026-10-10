# Seguridad y operación

## Controles implementados

- Gramática cerrada, límites de tamaño, profundidad y operaciones numéricas.
- Pydantic estricto y rechazo de campos adicionales; 64 KiB por petición HTTP.
- Un proceso efímero a la vez, timeout duro y cancelación, cuotas del contenedor.
- Host/Origin validados por el SDK, con `LAB_DOMAIN` y nombre del contenedor.
- Sin persistencia de expresiones, progreso o datos personales. Logs del SDK
  pueden incluir metadatos de solicitudes; revisar su retención en infraestructura.
- SeaweedFS es un destino interno fijo; el usuario no proporciona URLs de subida.
  Archivos UUID, PUT con timeout de 3 s; si falla, el PNG sigue incluido en MCP.
- UID sin privilegios, sin puertos publicados por Compose, sin bind mounts,
  sin secretos en código, sin dependencias desde rutas locales.
- Dependencias transitivas fijadas y hashes comprobados al instalar.

## Frontera de confianza

Este servidor **no incorpora autenticación ni autorización propias**. En el
laboratorio ambas pertenecen al proxy/infraestructura. No abrirlo directamente
al público: comprobar HTTPS, control de acceso, rate limiting y límites de
conexiones en el gateway del administrador. Host/Origin no sustituyen autenticación.
No se han auditado aquí las configuraciones del proxy, ya que no se adjuntaron.

El parser y los límites no constituyen aislamiento de kernel para código hostil.
No se ejecuta código proporcionado por usuarios; aun así, el motor simbólico y
sus dependencias requieren actualizaciones y revisión de vulnerabilidades.
El pin 2.1.1 sigue el contrato del laboratorio, no afirma ser la última versión.

Las imágenes publicadas en la ruta pública del laboratorio no deben contener
información confidencial. No hay borrado automático desde esta aplicación:
acordar retención y cuotas de SeaweedFS con el administrador.

## Diagnóstico

`ocupado`: repetir después; no abrir más procesos para evitarlo.
`tiempo`/`recursos`: simplificar la entrada; no elevar cuotas sin medir.
Sin URL de PNG: revisar variables, bucket y accesibilidad de SeaweedFS; la
herramienta conserva el resultado gráfico en la respuesta.
HTTP 421: Host no permitido; revisar `LAB_DOMAIN` y preservación del Host en Caddy.
HTTP 413: reducir solicitud. Errores internos: reproducir con el caso mínimo en
un entorno controlado; no habilitar debug en producción.
