# Plan de ampliación del MCP: Métodos Numéricos I y II

**Nota de vigencia (2026-10-10):** este archivo registra el plan histórico de ampliación. La ejecución vigente es solo con Docker; el uso local de app.py/host.exe/config.yml fue retirado y los PDF ahora se guardan en SeaweedFS. Consulta docs/GUIA_DESPLIEGUE.md y docs/ESTADO_IMPLEMENTACION.md para el flujo actual.

**Estado:** alcance implementado en la primera versión; ver docs/ESTADO_IMPLEMENTACION.md para los límites y verificaciones pendientes  
**Proyecto:** grupo04 / proyecto01 / mcp-test

## 1. Objetivo de la ampliación inicial (histórico)

Ampliar el MCP desde su alcance inicial de interpolación polinómica para cubrir las familias principales de Métodos Numéricos I y II. Antes del cambio existían cuatro herramientas; la primera versión ampliada registra 20 en total. interpolation.py conserva interpolación; numerical_methods.py implementa los métodos nuevos; server.py registra tools, interfaz y rutas PDF; report.py y storage.py generan y conservan informes; app.py inicia servidor local y Cloudflare; Docker empaqueta el mismo MCP.

La actualización conserva las cuatro herramientas originales y añade 16 herramientas. No significa aceptar cualquier problema matemático arbitrario: cada familia declara entradas, métodos, hipótesis y límites.

## 2. Cobertura académica implementada en la primera versión

### Métodos Numéricos I
- Error y aritmética: error absoluto/relativo, redondeo, propagación de primer orden para suma/resta/producto/cociente con incertidumbres independientes y cancelación. El código no calcula cotas de error analítico generales.
- Raíces: bisección, falsa posición, punto fijo, Newton-Raphson y secante.
- Sistemas lineales: eliminación gaussiana con pivoteo, LU, Jacobi y Gauss-Seidel.
- Interpolación: Lagrange, Newton/diferencias divididas, evaluación y comparación; la versión actual no calcula una cota ni diagnostica automáticamente Runge.
- Aproximación: interpolación lineal por tramos, splines cúbicos y mínimos cuadrados.
- Derivación: diferencias hacia delante, atrás y centradas para expresiones y tablas; efecto del paso; Richardson para expresiones.
- Integración: trapecio y Simpson para expresiones y tablas; Gauss-Legendre para expresiones; estimación empírica de error en funciones.
- ODE de valor inicial: Euler, Euler mejorado, punto medio y Runge-Kutta 4.

### Métodos Numéricos II
- Álgebra lineal avanzada: sistemas densos y dispersos (COO/CSR), gradiente conjugado, GMRES y precondicionador Jacobi; dimensiones limitadas.
- Mínimos cuadrados avanzado: QR, SVD y diagnóstico del rango del diseño polinómico.
- Valores propios: potencia, potencia inversa y cálculo de varios valores propios.
- Optimización no restringida: descenso por gradiente, Newton, búsqueda lineal y BFGS. Las restricciones quedan para una versión posterior.
- ODE avanzada: control adaptativo y problemas rígidos mediante métodos implícitos soportados.
- Problemas de frontera: disparo y diferencias finitas en casos unidimensionales.
- PDE modelo: diferencias finitas para calor, onda y Laplace 1D.
- Análisis de simulación: diagnósticos de convergencia, estabilidad y sensibilidad donde cada método los calcula; no hay estimación general de costo.

### Fuera del alcance inicial
Resolución simbólica general; cotas analíticas de error y diagnóstico automático de Runge; ejecución de código del usuario; optimización restringida; geometrías 2D/3D arbitrarias; elementos finitos, CFD y PDE no lineales generales. La herramienta debe explicar cuando una entrada no corresponde a un caso admitido. No debe prometer exactitud sin validación.

## 3. Arquitectura técnica

1. **Núcleo matemático puro:** algoritmos independientes de MCP, HTML, Docker y archivos.
2. **Validación:** estructura, números finitos, dimensiones, dominio, tolerancias y límites.
3. **Adaptadores MCP:** normalizan argumentos y producen resultados con esquema versionado.
4. **MCP App:** presenta cada familia; refleja el resultado y no recalcula silenciosamente.
5. **Informes/storage:** crea PDF, persiste de forma segura y publica preview/download.
6. **Ejecución:** app.py y Docker inician el mismo servidor y configuran ruta de informes y URL pública.

Estructura implementada en esta versión:
- numerical_methods.py concentra validación, evaluación segura y algoritmos numéricos por familia;
- interpolation.py conserva los cálculos de interpolación originales;
- server.py registra herramientas, Apps, recursos de interfaz y rutas HTTP de PDF;
- ui/interpolation.html preserva la experiencia anterior; ui/numerical.html presenta las nuevas familias con pestañas y gráficas según la respuesta;
- report.py genera PDFs; storage.py conserva los archivos y construye enlaces;
- app.py y Dockerfile arrancan el mismo server.py con configuración distinta.

La separación por submódulos internos (roots.py, linear.py, ode.py, etc.) queda para mantenimiento futuro; no es requisito para usar las herramientas.
Se conservaron los nombres MCP existentes de interpolación.

## 4. Catálogo de herramientas implementado

analizar_aritmetica_flotante, analizar_error_numerico, propagar_error_numerico, resolver_raiz, resolver_sistema_lineal, resolver_sistema_disperso, resolver_interpolacion, ajustar_datos, derivar_numericamente, derivar_tabla_numericamente, integrar_numericamente, integrar_tabla_numericamente, resolver_edo, resolver_valores_propios, optimizar_funcion, resolver_problema_frontera y resolver_pde.

Cada herramienta declara argumentos tipados, valores por defecto, métodos, límites y supuestos en docs/CATALOGO_HERRAMIENTAS.md. El servidor no cambia silenciosamente el método solicitado.

## 5. Fases implementadas

Las fases siguientes describen cambios presentes en el código. La matriz de aceptación y la ejecución real siguen pendientes.

### Fase 0 — Contrato y límites
Se definió salida común versionada, evaluación segura de expresiones, límites por dimensión/iteración y estados success, no_convergence, invalid_input y calculation_error.

### Fase 1 — Núcleo e interfaz
Se preservaron las cuatro tools de interpolación y se incorporaron el módulo numérico independiente, la interfaz MCP App de seis pestañas y el contrato común para las herramientas nuevas.

### Fase 2 — Error y raíces
Se añadieron análisis y propagación de error, suma/redondeo de punto flotante y raíces por bisección, falsa posición, punto fijo, Newton y secante, con historial y criterio de parada.

### Fase 3 — Sistemas y aproximación
Se añadieron eliminación Gaussiana con pivoteo, LU, Jacobi, Gauss-Seidel, CG, GMRES, QR, SVD, matriz dispersa COO/CSR, mínimos cuadrados estándar/QR/SVD, spline cúbico e interpolación lineal por tramos.

### Fase 4 — Derivación, integración y ODE
Se añadieron diferencias finitas y Richardson para funciones, derivación tabular; trapecio, Simpson y Gauss-Legendre para funciones, integración tabular; Euler, Heun, punto medio, RK4, RK45 y BDF.

### Fase 5 — Métodos avanzados
Se añadieron sistemas dispersos iterativos, valores propios, optimización no restringida y diagnósticos de convergencia/residuo.

### Fase 6 — Frontera y PDE
Se añadieron shooting y diferencias finitas para el caso BVP 1D definido, más calor/onda explícitos y Laplace 1D, con restricciones de estabilidad y malla.

### Fase 7 — PDF, storage y ejecución
Se añadieron informes ReportLab para las nuevas tools, persistencia compartida, preview/download, volumen Docker e ingreso Cloudflare para `/mcp` y `/reports`. La conectividad pública y la reconstrucción local aún deben validarse operativamente.
## 6. Criterios de finalización por módulo

Cada familia necesita: entrada validada; algoritmo aislado; ejemplo de uso; salida estructurada; diagnósticos y límites; interfaz MCP App común adaptada por familia; PDF legible; guía de uso; operación local y Docker. La verificación numérica y de despliegue queda pendiente. El cálculo debe permanecer disponible si falla el PDF.

## 7. Decisiones adoptadas y asuntos pendientes

- Se conservan los recursos de interpolación y se añade una MCP App común con pestañas, que presenta campos, tablas y gráficas según la familia.
- Se fijaron límites por herramienta; consultar el catálogo y la referencia de algoritmos.
- SciPy/NumPy para solvers robustos; se implementaron manualmente los métodos introductorios que muestran pasos.
- El storage usa volumen nombrado en Docker y carpeta local con nombres aleatorios; no se implementó caducidad automática.
- Interfaz y documentación en español; nombres de método/API conservan términos usuales del software.
- La primera versión muestra fórmulas/resumen y tablas de iteración; no genera derivaciones simbólicas generales.
- Expresiones evaluadas con una lista segura de operadores y funciones; no se ejecuta Python arbitrario.

## Ampliación integrada: contrato, herramientas y estabilidad

La ampliación posterior eleva el catálogo a 27 herramientas. Suma Newton multivariable para sistemas no lineales, análisis de condicionamiento y perturbaciones, Adams-Bashforth/ABM4, Laplace/Poisson 2D, SLSQP con restricciones, Lanczos para valores propios dispersos y cuadratura Gauss-Kronrod adaptativa.

Las siete tools nuevas, igual que las veinte existentes, llevan docstrings en español que sirven como descripción MCP completa e indican entradas, restricciones y formato de salida. Los adaptadores exponen `level` (`inicial`/`intermedio`) e `include_report` (activar/omitir PDF), y el esquema común se versiona como 1.1 manteniendo campos históricos de interpolación.

Se corrige la colisión de `problem_type` en el adaptador de PDE. La generación PDF de interpolación migra de pdflatex a ReportLab; el trazado vectorial limita puntos, las tablas se recortan para presentación y un bloqueo serializa la generación para controlar el pico de memoria. Docker no instala TeX Live y mantiene los PDF en su volumen nombrado. `app.py` sigue ejecutando el mismo servidor local y el túnel se limita a enrutar tráfico al puerto 8000.

La verificación de esta actualización incluye registro y esquemas de 27 tools, llamadas numéricas de humo, casos con resultado conocido, sintaxis de Python/JavaScript y generación de PDF común y legado. La disponibilidad pública del dominio depende de que el equipo del propietario mantenga MCP y Cloudflare Tunnel en ejecución.
