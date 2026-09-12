# Frenet, Lagrange y Puntos Críticos —  (Grupo 06) 

## Objetivo y Alcances

**Objetivo:** Desarrollar un servidor MCP (Model Context Protocol) que delega en SymPy el cálculo simbólico exacto, la resolución rigurosa de sistemas algebraicos no lineales y la generación de gráficos en temas de cálculo multivariable donde los LLM fallan por alucinación, truncamiento o pérdida de términos algebraicos.

**Alcances y Funcionamiento del Sistema:**

El servidor actúa como un motor de ejecución matemática determinista que recibe expresiones simbólicas, valida su consistencia y aplica métodos de álgebra computacional pura:

* **Triedro de Frenet y geometría diferencial de curvas en R^3 (`metodos_frenet.py`):**
  * **Qué hace:** Analiza curvas parametrizadas r(t) = (x(t), y(t), z(t)) calculando de manera simbólica sus propiedades geométricas intrínsecas y el marco móvil ortonormal.
  * **Cómo funciona:** Evalúa derivadas sucesivas r'(t), r''(t) y r'''(t), ejecuta productos vectoriales y escalares sobre árboles algebraicos de SymPy y simplifica expresiones sin introducir aproximaciones decimales.
  * **Métodos analíticos incluidos:**
    * Vector tangente unitario: T(t) = r'(t) / ||r'(t)||
    * Vector binormal: B(t) = (r'(t) x r''(t)) / ||r'(t) x r''(t)||
    * Vector normal principal: N(t) = B(t) x T(t)
    * Curvatura escalar: kappa(t) = ||r'(t) x r''(t)|| / ||r'(t)||^3
    * Torsión: tau(t) = [(r'(t) x r''(t)) . r'''(t)] / ||r'(t) x r''(t)||^2
    * Ecuaciones de planos fundamentales en un punto t0: osculador (perpendicular a B), normal (perpendicular a T) y rectificante (perpendicular a N).

* **Multiplicadores de Lagrange y optimización condicionada (`metodos_lagrange.py`):**
  * **Qué hace:** Determina extremos locales de un campo escalar f(x, y, ...) sujeto a una o más restricciones de igualdad g(x, y, ...) = 0.
  * **Cómo funciona:** Construye la función Lagrangiana L(x, lambda) = f(x) - lambda * g(x), plantea el sistema gradiente ampliado grad(L) = 0 y utiliza solvers analíticos exactos (como nonlinsolve o bases de Gröbner) para obtener exhaustivamente todas las ramas de soluciones sin omitir puntos críticos.
  * **Métodos analíticos incluidos:**
    * Resolución completa del sistema no lineal: grad(f) = lambda * grad(g) junto con la restricción g = 0.
    * Construcción simbólica de la matriz del Hessiano Orlado (H_orlado) agregando las derivadas de la restricción como bordes.
    * Clasificación formal mediante el signo de los determinantes de los menores principales orlados para distinguir máximos y mínimos locales condicionados.

* **Puntos críticos y optimización libre (`metodos_hessiana.py`):**
  * **Qué hace:** Identifica y clasifica todos los puntos estacionarios de campos escalares f(x, y) en dominios abiertos.
  * **Cómo funciona:** Calcula analíticamente las derivadas parciales de primer y segundo orden, resuelve de forma exacta el sistema grad(f) = (0, 0) asegurando que no se descarten soluciones algebraicas y analiza la curvatura local.
  * **Métodos analíticos incluidos:**
    * Cálculo simbólico del gradiente: grad(f) = (df/dx, df/dy) = (0, 0).
    * Construcción de la matriz Hessiana simétrica H(x, y) con las derivadas f_xx, f_yy y mixtas f_xy.
    * Clasificación por discriminante D = f_xx * f_yy - (f_xy)^2 y signo de f_xx: mínimo local (D > 0, f_xx > 0), máximo local (D > 0, f_xx < 0), punto de silla (D < 0) o caso dudoso (D = 0).


## Repartición de Tareas

| Integrante            | Tarea principal                                                                                           | Archivos                                                                        |
|-----------------------|-----------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| **Marcela Ventura**   | Diagnóstico del problema, selección del método y validación sintáctica de entradas.                       | `diagnostico.py`, `validacion.py`                                               |
| **Dylan Lucar**       | Triedro de Frenet (T, N, B), curvatura, torsión y planos asociados (máxima carga simbólica).              | `metodos_frenet.py`                                                             |
| **Ximena Quispe**     | Multiplicadores de Lagrange, resolución de sistemas no lineales y matriz del Hessiano Orlado.             | `metodos_lagrange.py`                                                           |
| **Sean Leiva**        | Gradiente, resolución exhaustiva de puntos críticos y clasificación por matriz Hessiana.                  | `metodos_hessiana.py`                                                           |
| **Alejandro Ramírez** | Renderizado de gráficos (curvas 3D, superficies, curvas de nivel) y exportación a PNG, texto, HTML y PDF. | `visualizacion.py`, `reporte.py`                                                |
| **Juan Chipana**      | Servidor MCP, conexión entre módulos, verificación de resultados, almacenamiento y despliegue en Docker.  | `server.py`, `storage.py`, `verificador.py`, `Dockerfile`, `docker-compose.yml` |
