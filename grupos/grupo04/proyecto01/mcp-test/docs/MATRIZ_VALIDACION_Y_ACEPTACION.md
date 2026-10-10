# Matriz de validación y aceptación

Lista de aceptación de las 27 herramientas y del despliegue Docker.

## 1. Controles comunes

Validar forma, tipos, dimensiones, dominio y números finitos; comparar con
solución conocida o referencia; verificar método, tolerancia, máximo de
iteraciones, residuo y estado; controlar límites antes de reservar memoria;
evitar que un fallo numérico detenga el servidor; conservar el resultado
matemático si falla el PDF; comparar UI con la respuesta MCP.

## 2. Familias cubiertas

| Familia | Caso de aceptación |
|---|---|
| Error | exacto 1/3 frente a aproximación decimal; errores absoluto y relativo correctos |
| Propagación | suma y producto con incertidumbres independientes |
| Raíz | x²−2 en [1,2]; raíz y residuo dentro de tolerancia |
| Sistema | matriz pequeña densa con solución conocida |
| Disperso | sistema COO; CG/GMRES coinciden con referencia |
| Interpolación | datos de y=x²; Newton y Lagrange coinciden |
| Ajuste | datos lineales con ruido; coeficientes y residuos reproducibles |
| Derivación | derivada de x² en 3; derivadas tabulares en mallas uniformes y no uniformes |
| Integración | integral de x² en [0,1]; resultado 1/3 y condiciones de malla |
| EDO | y'=y, y(0)=1; error baja al reducir el paso |
| Valores propios | matriz diagonal 2x2; valores y residuos correctos |
| Optimización | cuadrática definida positiva; minimizador y gradiente correctos |
| Frontera | solución fabricada 1D; error disminuye al refinar |
| PDE | casos 1D/2D del catálogo; frontera, estabilidad y límites respetados |

## 3. Interfaz y clientes

- Cada problem_type abre el diseño correcto.
- No aparecen campos vacíos silenciosos por una envoltura distinta del resultado.
- Se distinguen éxito, advertencia, no convergencia y entrada inválida.
- Tablas truncadas lo indican; gráficas tienen ejes y leyendas.
- Resultado, desarrollo, tabla, gráfica y PDF corresponden a una ejecución.
- La respuesta MCP sigue siendo útil aunque el cliente no renderice MCP Apps.

## 4. PDF y persistencia

- El PDF se genera en memoria y no se escribe en el sistema de archivos.
- La subida al bucket grupo04-mcp-test-imgs usa timeout y devuelve un error claro
  si SeaweedFS no responde.
- Vista previa devuelve application/pdf con Content-Disposition inline.
- Descarga devuelve application/pdf con Content-Disposition attachment.
- Una clave manipulada no puede convertirse en una ruta ni escapar del bucket.
- Un PDF sigue disponible después de recrear el contenedor mientras permanezca
  en SeaweedFS.
- Las rutas públicas /reports llegan al mismo contenedor que /mcp.

## 5. Ejecución

Docker Compose: imagen construye desde requirements.txt, inicia server.py,
limita memoria, usa lab_net y recibe LAB_CONTAINER_NAME, LAB_DOMAIN y
LAB_PUBLIC_PATH. La prueba local consulta el puerto asignado con
docker compose port mcp-test 8000. No deben incluirse entornos virtuales,
cachés, PDF locales, app.py, host.exe ni config.yml en la imagen.

Despliegue público: Caddy enruta el prefijo LAB_PUBLIC_PATH al contenedor en
lab_net; /mcp y /reports deben llegar al servidor. SeaweedFS debe ser
resoluble como seaweedfs:8333 desde el contenedor.

## 6. Herramientas nuevas

| Herramienta | Caso recomendado |
|---|---|
| resolver_sistema_no_lineal | x0²+x1²=5, x0−x1=1, inicial (2,1) |
| analizar_condicionamiento | matriz diagonal con condición elevada y perturbación pequeña en b |
| resolver_edo_multipaso | y'=y, y(0)=1; comparar ABM4 con e en t=1 |
| resolver_pde_2d | Laplace con frontera u(x,y)=x |
| optimizar_funcion_restringida | cuadrática con igualdad x0+x1=3 y desigualdad x0>=0 |
| resolver_valores_propios_dispersos | matriz simétrica diagonal COO |
| integrar_adaptativamente | integral de x² entre 0 y 1, comparar con 1/3 |

## 7. Estado de la verificación

La batería anterior verificó las 27 herramientas y un build Docker antes de
migrar el almacenamiento a SeaweedFS. La migración descrita requiere una
verificación de integración con SeaweedFS activo y la prueba de las rutas PDF
en el despliegue.
