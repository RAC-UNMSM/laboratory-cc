# Referencia de algoritmos implementados

Resumen de numerical_methods.py y de la interpolación heredada. No es una demostración de exactitud universal.

## Punto flotante y error
La suma de referencia usa Decimal con alta precisión; se compara acumulación float IEEE-754, math.fsum y redondeo decimal por operación. El ejemplo [1e16,1,-1e16] ilustra cancelación y pérdida de un término pequeño. Error absoluto y relativo se informan aparte; el relativo no se define para referencia cero.

## Error
Error absoluto |x-x_aprox|; relativo |x-x_aprox|/|x| cuando x no es cero. El porcentaje es 100 veces el relativo. Si x=0, el relativo queda indefinido.

## Raíces
Bisección requiere continuidad y cambio de signo; conserva encierro. Falsa posición conserva encierro mediante interpolación lineal y puede estancarse. Punto fijo itera g(x); convergencia local se favorece si |g'|<1. Newton aproxima derivada por diferencia central y necesita estimación inicial razonable. Secante usa dos aproximaciones previas. La tabla y motivo de parada acompañan el resultado.

## Sistemas
Gaussian y LU usan pivoteo parcial. Jacobi y Gauss-Seidel dependen de condiciones de convergencia; diagonal dominante es suficiente común. CG necesita matriz simétrica definida positiva y admite precondicionamiento Jacobi. GMRES usa Arnoldi y mínimos cuadrados; permite precondicionamiento diagonal por izquierda. QR y SVD usan factorizaciones de NumPy. Se devuelve norma de residuo y condición si es finita.
El solver denso admite hasta 250 por 250. resolver_sistema_disperso recibe tripletas COO [fila,columna,valor], índices base 0, calcula en CSR y limita a 5000 filas y 100000 entradas; CG requiere simetría.

## Interpolación y ajuste
Lagrange usa bases polinómicas; Newton usa diferencias divididas. La diferencia entre sus valores no es error verdadero. Splines cúbicos usan condición natural. Mínimos cuadrados devuelve residuos y R². Interpolación lineal conecta nodos. Evaluar fuera del rango es extrapolación.

## Derivación e integración
Forward/backward son de primer orden; central, segundo. Richardson combina diferencias centrales. El indicador de variación con h no es cota rigurosa.
Trapecio compuesto es orden h² para funciones suaves; Simpson compuesto es orden h⁴ y requiere subintervalos pares. Gauss-Legendre usa nodos/pesos de Legendre. Errores estimados por refinamiento son empíricos.

## ODE
Euler orden 1; Heun y midpoint orden 2; RK4 orden 4. RK45/BDF delegados a SciPy solve_ivp con tolerancias indicadas. Las variables de estado deben ser nombres únicos y no pueden usar t, x, pi o e. Se limita a 10 estados y un máximo estimado de 10000 pasos.

## Valores propios
Power aproxima valor dominante por magnitud; inverse se acerca al valor más próximo al shift; QR obtiene varios por la rutina LAPACK usada por NumPy. Se devuelve residuo del par y partes real/imaginaria.

## Optimización
Gradiente y Hessiano se aproximan numéricamente. Gradient descent, Newton y BFGS usan búsqueda Armijo. El problema puede ser no convexo; el resultado depende del inicio y no demuestra mínimo global.

## Frontera
Shooting integra sistema de primer orden y usa secante para la pendiente inicial. finite_difference cubre y''=f(x) con Dirichlet y malla uniforme; no cubre dependencia de y/y'.

## PDE
Calor usa FTCS explícito con r=alpha*dt/dx²<=0.5. Onda explícita exige CFL=c*dt/dx<=1 y supone velocidad inicial cero. Laplace 1D entrega perfil lineal. Sin fuente, condiciones mixtas o geometría 2D en esta versión.
