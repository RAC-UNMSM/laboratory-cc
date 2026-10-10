# Arquitectura y decisiones

1. El SDK valida el objeto tipado y publica el JSON Schema discriminado.
2. `server.py` llama al ejecutor asíncrono sin hacer cálculos en el bucle HTTP.
3. `runtime.py` admite un cálculo; solicitudes simultáneas reciben `ocupado`,
   evitando colas sin límite dentro de una cuota de 512 MiB.
4. Un proceso Python independiente recibe JSON por stdin y vuelve a validar.
   El parser recorre AST con una lista cerrada de nodos y construye objetos
   SymPy. No usa eval, exec, sympify(texto) ni parse_expr.
5. El módulo del curso calcula y genera resultados y etapas verificables.
6. Tras 20 segundos el padre mata y recoge el proceso; en Linux el hijo tiene
   15 s de CPU y 448 MiB de espacio de direcciones. Al cancelar una petición
   también se mata el hijo. No se utiliza un timeout de hilo que siga calculando.
7. El resultado sale como JSON sin trazas del servidor. Gráficos viajan como PNG
   codificado, se publican opcionalmente y se adjuntan siempre al protocolo.

El contenedor limita memoria total, procesos y CPU, ejecuta UID 10001 sin
privilegios, raíz de solo lectura y /tmp efímero para la caché de Matplotlib.
Una instancia del servidor por contenedor. No iniciar múltiples workers sin
redimensionar memoria y revisar el límite global de concurrencia.

La enseñanza está separada del cálculo: tres archivos Markdown se exponen como
prompts. Ninguno de ellos fuerza el comportamiento del modelo cliente ni crea
una nueva ventana de contexto. Los resultados de herramientas contienen datos,
no órdenes para el modelo. La solución no necesita un proveedor LLM en el servidor.

## Correspondencia con responsabilidades

| Responsabilidad propuesta | Módulos implementados |
|---|---|
| Hiron Ortega: arquitectura | server, models, runtime, worker, engine, despliegue |
| Cristhian Saico: Cálculo I | limites_continuidad, derivadas_optimizacion |
| Yhin Rosales: Cálculo II | integrales, integrales_aplicaciones |
| Jefferson Vilcapoma: Cálculo III | calculo_multivariable |
| Angel Meza: Cálculo IV | integrales_multiples, campos_vectoriales |
| Carlos Lau: tutor y QA | skills, tutor, tests, documentación |

Esta tabla conserva la distribución de la propuesta; no atribuye autoría de
los cambios actuales a los integrantes.
