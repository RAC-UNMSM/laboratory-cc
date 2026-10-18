# Catálogo de herramientas MCP

Las herramientas nuevas devuelven schema_version, problem_type, status, method, inputs, result, diagnostics, steps, tables, charts, warnings y report. Las cuatro tools de interpolación mantienen la respuesta histórica.

## analizar_aritmetica_flotante
Argumentos: values, precision_digits. Compara referencia decimal, suma float secuencial, math.fsum y acumulación redondeada en cada operación. Úsala para cancelación, por ejemplo values=[1e16,1,-1e16]. precision_digits entre 1 y 50.

## analizar_error_numerico
Argumentos: exact, approximation. Devuelve error absoluto, relativo y porcentual; el relativo es null si el exacto es cero.

## propagar_error_numerico
Argumentos: a, b, error_a, error_b, operation. operation: add, subtract, multiply o divide. Supone incertidumbres independientes y usa propagación lineal de primer orden; las incertidumbres son absolutas y no negativas.

## resolver_raiz
Argumentos: expression, method, a, b, x0, x1, g_expression, tolerance, max_iter. Métodos: bisection, false_position, fixed_point, newton, secant. Bisección/falsa posición requieren a,b con cambio de signo; punto fijo requiere g_expression; Newton requiere x0; secante requiere x0,x1. Ejemplo: x**2-2 en [1,2] por bisection.

## resolver_sistema_lineal
Argumentos: matrix, vector, method, tolerance, max_iter, preconditioner. Métodos: gaussian, lu, jacobi, gauss_seidel, conjugate_gradient, gmres, qr, svd. Jacobi como precondicionador solo para CG/GMRES. CG necesita matriz simétrica definida positiva. Máximo 250 filas para matrices densas; usa resolver_sistema_disperso para tamaño 1–5000, con entries COO [fila,columna,valor] e índices base 0. CG exige matriz simétrica; permite CG o GMRES y precondicionador Jacobi. Ejemplo: size=2, entries=[[0,0,4],[0,1,1],[1,0,1],[1,1,3]], vector=[1,2], método cg.

## resolver_sistema_disperso
Argumentos: size, entries, vector, method, tolerance, max_iter, preconditioner. entries es una lista COO de tripletas [fila,columna,valor] con índices base 0; las entradas duplicadas se suman. Métodos cg o gmres; preconditioner none o jacobi. CG requiere una matriz simétrica definida positiva. Límite 5000 filas y 100000 tripletas. Ejemplo pequeño: size=2, entries=[[0,0,4],[0,1,1],[1,0,1],[1,1,3]], vector=[1,2].

## Interpolación heredada
- resolver_interpolacion(points,x_eval,method)
- interpolacion_lagrange(points,x_eval)
- interpolacion_newton(points,x_eval)
- comparar_interpolacion(points,x_eval)
Puntos en objetos {x,y}; x no se repite.

## ajustar_datos
Argumentos: points, method, degree, evaluation_points. Métodos least_squares, least_squares_qr, least_squares_svd, cubic_spline, linear_piecewise. QR/SVD informan rango y condición del diseño; sus coeficientes usan x normalizada. El grado debe ser menor que la cantidad de puntos. Fuera del rango de datos se marca extrapolación.

## derivar_numericamente
Argumentos: expression, x, h, method. Métodos forward, backward, central, richardson. La variación con h es un indicador numérico, no una cota rigurosa.

## derivar_tabla_numericamente
Argumentos: points (lista de {x,y}), method. Métodos forward, backward o central; la fórmula central admite malla no uniforme. Devuelve derivadas en los nodos donde la fórmula esté definida.

## integrar_numericamente
Argumentos: expression, a, b, n, method. Métodos trapezoid, simpson, gauss_legendre. Simpson requiere n par; n máximo 20000 y Gauss-Legendre máximo 64 nodos. Trapecio/Simpson estiman error comparando refinamientos.

## integrar_tabla_numericamente
Argumentos: points (lista de {x,y}), method. Métodos trapezoid para malla no uniforme o simpson para malla uniforme con número par de subintervalos. Sin estimación de error si no se entrega una tabla refinada.

## resolver_edo
Argumentos: equations, initial_state, t0, t_end, step, method, state_names, tolerance. Métodos euler, heun, midpoint, rk4, rk45, bdf. Una expresión por estado; nombres por defecto y0, y1, etc. Variables independientes t y x. Máximo 10 estados y 10000 pasos estimados.

## resolver_valores_propios
Argumentos: matrix, method, count, tolerance, max_iter, shift. Métodos power, inverse y qr. Matriz cuadrada hasta 100. Devuelve parte real/imaginaria de valor y vector y residuo.

## optimizar_funcion
Argumentos: expression, initial, variables, method, tolerance, max_iter. Métodos gradient_descent, newton, bfgs. De 1 a 5 variables; gradiente/Hessiano numéricos y búsqueda Armijo.

## resolver_problema_frontera
Argumentos: rhs_expression,a,b,alpha,beta,n,method. Resuelve y''=f(...), con condiciones Dirichlet. Shooting admite x,y,yp; finite_difference solo f(x). De 3 a 300 subintervalos.

## resolver_pde
Argumentos: problem_type,length,nx,nt,diffusivity,speed,initial_values,initial_expression,boundary_left,boundary_right,dt. Tipos heat, wave y laplace 1D. Calor requiere alpha*dt/dx²<=0.5; onda c*dt/dx<=1 y supone velocidad inicial cero. nx 4–100, nt 2–300.

## Expresiones seguras
Operadores +,-,*,/,**,%; constantes pi/e; sin, cos, tan, asin, acos, atan, sinh, cosh, tanh, exp, log, log10, sqrt, abs, fabs, floor, ceil, erf. No se permite import, atributo, indexación ni ejecución de Python.


## Herramientas incorporadas en la ampliación integrada

| Herramienta | Tema y datos principales | Alcance |
|---|---|---|
| `resolver_sistema_no_lineal` | Una residual por variable, nombres e inicial | Newton multivariable con Jacobiano numérico y amortiguamiento opcional; 1–5 variables |
| `analizar_condicionamiento` | Matriz cuadrada, vector y perturbación opcionales | Número de condición en norma 1, 2 o infinito y sensibilidad observada |
| `resolver_edo_multipaso` | Sistema, estado inicial, intervalo y paso | Adams-Bashforth 2/4 y ABM4 con arranque RK4; paso fijo |
| `resolver_pde_2d` | Dominio rectangular, fronteras y fuente f(x,y) | Laplace/Poisson 2D, Dirichlet y stencil de cinco puntos; malla máxima 50×50 |
| `optimizar_funcion_restringida` | Objetivo, inicial, bounds y restricciones | SLSQP; igualdades g(x)=0 y desigualdades h(x)>=0 |
| `resolver_valores_propios_dispersos` | Tripletas COO simétricas base 0 | Lanczos/ARPACK; requiere matriz simétrica y count<size |
| `integrar_adaptativamente` | Integrando, límites y tolerancias | Gauss-Kronrod adaptativa; devuelve error estimado y subintervalos |

Todas las herramientas aceptan `level` (`inicial` o `intermedio`) e `include_report` para solicitar u omitir el PDF.
