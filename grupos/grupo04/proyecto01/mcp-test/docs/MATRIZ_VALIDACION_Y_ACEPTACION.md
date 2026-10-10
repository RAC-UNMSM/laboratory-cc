# Matriz de validación y aceptación

Lista de aceptación para la ampliación implementada. La lista documenta verificaciones recomendadas; no afirma que ya se ejecutaron.

## 1. Controles comunes

Validar forma, tipos, dimensiones, dominio y números finitos; comparar con solución conocida o referencia; verificar método, tolerancia, máximo de iteraciones, residuo y estado; controlar límites antes de reservar memoria; evitar que un fallo numérico detenga el servidor; conservar resultado si falla el PDF; comparar datos de UI con respuesta MCP.

## 2. Casos iniciales

| Familia | Caso de aceptación |
|---|---|
| Error | exacto 1/3 frente a aproximación decimal; error absoluto/relativo correcto |
| Propagación | suma y producto con incertidumbres independientes; revisar incertidumbre combinada y supuesto declarado |
| Raíz | x²−2 en [1,2]; raíz y residuo dentro de tolerancia |
| Sistema | matriz pequeña densa con solución conocida; residuo correcto |
| Iterativos | matriz diagonalmente dominante; converge y muestra historial |
| Disperso | tripletas COO pequeñas; CG/GMRES coinciden con referencia y respetan índice base 0 |
| Interpolación | datos de y=x²; Newton y Lagrange coinciden |
| Ajuste | datos lineales con ruido; coeficientes y residuos reproducibles; QR/SVD revelan rango y condición |
| Derivación | derivada de x² en 3; mejora al reducir h hasta redondeo; diferencias tabulares en malla uniforme y no uniforme |
| Integración | integral de x² de 0 a 1; Simpson dentro de tolerancia; tablas por trapecio/Simpson y requisitos de malla |
| ODE | y'=y, y(0)=1; error baja al reducir paso |
| Valores propios | matriz diagonal 2x2; valores y residuos correctos |
| Optimización | cuadrática definida positiva; minimizador y gradiente correctos |
| Frontera | solución fabricada 1D; error disminuye al refinar |
| PDE | calor 1D; frontera y estabilidad respetadas |

Guardar referencias esperadas junto con pruebas detalladas al implementar cada módulo.

## 3. Interfaz y clientes

- Cada problem_type abre diseño correcto.
- No aparecen campos vacíos silenciosos por una envoltura distinta del resultado.
- Diferencia éxito, advertencia, no convergencia y entrada inválida.
- Tabla truncada lo indica; gráficas tienen ejes y leyendas.
- Resultado, desarrollo, tabla, gráfica y PDF corresponden a una ejecución.
- Probar Inspector y clientes disponibles; documentar diferencias de host.
- La respuesta sigue útil sin MCP App.

## 4. PDF y persistencia

PDF legible por familia; preview inline y download adjunto; ruta manipulada no escapa del directorio; volumen sobrevive a recrear contenedor mientras no se borre; ruta pública /reports funciona; REPORT_FAILED no reemplaza estado matemático.

## 5. Ejecución

**app.py:** intérprete esperado, servidor y túnel iniciados, URL pública correcta, Ctrl+C detiene procesos.  
**Docker:** build con dependencias declaradas, puerto/transporte documentados, límites de recursos, volumen de reportes, sin .ENTORNO/cachés/archivos locales en imagen salvo decisión expresa, ingress para /mcp y /reports.

## 6. Liberación de cada módulo

Liberar solo cuando haya ejemplos documentados, referencias numéricas correctas, diagnósticos/límites visibles, vista completa, PDF funcional, modos local y Docker verificados y documentación actualizada.

## Casos de aceptación de las siete herramientas nuevas

| Herramienta | Caso verificado |
|---|---|
| `resolver_sistema_no_lineal` | Sistema `x0²+x1²=5`, `x0−x1=1`, inicial (2,1) |
| `analizar_condicionamiento` | Matriz diagonal con condición elevada y una perturbación pequeña en b |
| `resolver_edo_multipaso` | y'=y, y(0)=1; ABM4 se aproxima a e en t=1 |
| `resolver_pde_2d` | Laplace con frontera u(x,y)=x; interior reproduce el perfil lineal |
| `optimizar_funcion_restringida` | Cuadrática con igualdad x0+x1=3 y desigualdad x0>=0 |
| `resolver_valores_propios_dispersos` | Matriz diagonal simétrica COO; el valor propio dominante coincide |
| `integrar_adaptativamente` | Integral de x² entre 0 y 1; compara con 1/3 y revisa error estimado |

También se valida que cada tool aparezca en el registro MCP con docstring descriptivo y esquema de argumentos; las 27 herramientas aceptan omitir el PDF y devuelven el nivel solicitado. Se comprueba tanto el PDF genérico como el PDF legado de interpolación.


## Resultado de verificación 2026-10-10

Verificación completada: 27 esquemas MCP y docstrings válidos; llamadas de humo a las 27 herramientas; referencias numéricas conocidas correctas; interfaz JavaScript válida; PDF común, interpolación y PDE 2D creados; `docker compose config` y build de imagen correctos; el contenedor temporal anunció 27 herramientas por HTTP y ejecutó integración adaptativa y `resolver_pde`. El contenedor temporal fue detenido después de la prueba.
