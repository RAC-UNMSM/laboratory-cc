# Guía de uso

## Cómo pedir una resolución
Indica método, datos y parámetros conocidos. El servidor no inventa condiciones iniciales, dominios o tolerancias que falten. Si el problema no encaja en el formato soportado, pide que indique qué campo o supuesto hay que cambiar.

## Solicitudes de ejemplo
- Punto flotante: suma [1e16,1,-1e16] y compara float secuencial, suma compensada y redondeo con 8 cifras.
- Error: compara el exacto 1/3 con 0.3333; muestra absoluto y relativo.
- Propagación: multiplica a=2±0.1 por b=3±0.2; usa operation=multiply y declara la independencia de incertidumbres.
- Raíz: resuelve x**2-2 en [1,2] por bisection y presenta la tabla.
- Sistema denso: resuelve A=[[4,1],[1,3]], b=[1,2] por conjugate_gradient y muestra residuo.
- Sistema disperso: size=2, entries=[[0,0,4],[0,1,1],[1,0,1],[1,1,3]], vector=[1,2] con resolver_sistema_disperso y cg.
- Interpolación: interpola (0,1),(1,3),(2,7) por Newton en x=1.5.
- Ajuste: mínimos cuadrados lineal para (0,1),(1,2),(2,2.8); evalúa 1.5.
- Derivada de función: sin(x) en x=1 por central, h=0.001.
- Derivada tabular: deriva centralmente los puntos (0,0),(1,1),(2,4),(3,9).
- Integral de función: x**2 de 0 a 1 por Simpson con 20 subintervalos.
- Integral tabular: integra por Simpson (malla uniforme) o trapecio (malla no uniforme) puntos de una tabla.
- ODE: y'=y, y(0)=1, intervalo [0,1], RK4 con paso 0.1.
- Eigen: valor propio dominante de [[2,0],[0,1]] por potencia.
- Optimización: minimiza (x-2)**2+(y+1)**2 desde [0,0] con BFGS.
- Frontera: y''=-pi**2*sin(pi*x), y(0)=y(1)=0, diferencias finitas.
- PDE: calor 1D en [0,1], inicio sin(pi*x), fronteras cero y malla estable.

Argumentos exactos en CATALOGO_HERRAMIENTAS.md.

## Interpretar salida
status success significa completado; no_convergence significa que el criterio no se alcanzó; invalid_input identifica una entrada rechazada. result contiene la respuesta. diagnostics contiene residuo, iteraciones, estabilidad o error aproximado. steps explica operaciones principales. tables y charts representan historial y datos visuales. warnings declara hipótesis.

No confundas muchos decimales con exactitud. Revisa dominio, unidades y residuo. La diferencia entre Newton y Lagrange mide discrepancia numérica y no siempre el error verdadero.

## PDF
Usa los botones Abrir vista previa y Descargar PDF en la pestaña de informe. La URL requiere servidor/túnel activo y que el archivo continúe en storage. Si el host no muestra iframe, usa el enlace externo. La herramienta conserva el resultado aunque falle el PDF.

## Probar las herramientas incorporadas

En MCP Inspector conecta a `http://localhost:8000/mcp`, abre Tools y busca por nombre. Ejemplos que el asistente puede enviar:

- Sistema no lineal: ecuaciones `x0**2+x1**2-5` y `x0-x1-1`, variables `x0`,`x1`, inicial `[2,1]`.
- Condicionamiento: una matriz cuadrada, `vector` opcional y `perturbation` opcional con la misma longitud.
- EDO multipaso: ecuación `y0`, estado inicial `[1]`, intervalo `[0,1]`, `step=0.1`, `method=abm4`.
- Laplace 2D: `problem_type=laplace`, rectángulo, dimensiones de frontera; cada lado usa una lista de longitud `nx+1` o `ny+1`.
- Optimización restringida: desigualdades se escriben como expresiones que deben ser >=0; igualdades como expresiones que deben ser 0.
- Valores propios dispersos: entradas `[fila,columna,valor]` con índices base 0 y matriz simétrica.
- Integración adaptativa: integrando seguro en x, límites y tolerancias opcionales.

En cualquier tool se puede pedir `level=intermedio` para una exposición más técnica o `include_report=false` para evitar la creación de PDF durante una llamada.
