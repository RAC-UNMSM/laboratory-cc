# Propuesta  — Servidor MCP para Resolución de Sistemas de Ecuaciones No Lineales

## Integrantes

1. **Nicanor Yalo Palomino**
2. **Arroni Guadalupe Dylan Eval**
3. **Salvador Damián Navarro**
4. **Francisco Alonso Olaya Girón**
5. **Calixto Luna Jhovany**

**Curso de origen:** Métodos Numéricos
**Referencia base:** Burden, Capítulo 10 — Soluciones numéricas de sistemas de ecuaciones no lineales

---

## 1. Idea general del proyecto

El objetivo del proyecto es desarrollar un **servidor MCP (Model Context Protocol)** capaz de resolver sistemas de ecuaciones no lineales de la forma

$$
F(x)=0
$$

utilizando métodos numéricos estudiados en el Capítulo 10 de Burden.

El servidor expondrá diferentes herramientas (*tools*) que podrán ser invocadas desde un cliente compatible con MCP. Cada herramienta ejecutará el método numérico correspondiente y devolverá resultados estructurados.

Los métodos considerados serán:

* Punto fijo para varias variables.
* Método de Newton.
* Método cuasi-Newton de Broyden.
* Descenso más rápido.
* Homotopía y continuación.

El proyecto tendrá tres niveles de salida:

1. **Resultados numéricos estructurados**, para que puedan ser procesados por el cliente o por el modelo.
2. **Visualización interactiva en HTML**, para observar la convergencia y las trayectorias.
3. **Informe en LaTeX y PDF**, para presentar los resultados de manera académica.

La generación de explicaciones en lenguaje natural quedará separada del cálculo numérico: el servidor produce los resultados y el modelo puede interpretarlos utilizando dichos resultados.

---

# 2. Módulos y herramientas MCP

| Tool                          | Entrada principal                                                                                 | Salida principal                                                      |
| ----------------------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `punto_fijo_varias_variables` | Sistema \(F(x)\), función de iteración \(G(x)\), punto inicial, tolerancia, máximo de iteraciones | Solución, error, trayectoria, estado de convergencia                  |
| `newton_sistemas`             | Sistema \(F(x)\), punto inicial, tolerancia, máximo de iteraciones, Jacobiano opcional            | Solución, error, residuo, trayectoria y estado                        |
| `cuasi_newton_broyden`        | Sistema \(F(x)\), punto inicial, tolerancia, máximo de iteraciones                                | Solución, error, residuo y aproximación del Jacobiano                 |
| `descenso_mas_rapido`         | Sistema \(F(x)\), punto inicial, tolerancia, máximo de iteraciones y parámetros de paso           | Solución, trayectoria, valor de la función objetivo y convergencia    |
| `homotopia_continuacion`      | Sistema objetivo, función homotópica \(H(x,t)\), punto inicial y parámetros de continuación       | Solución, trayectoria de continuación y diagnóstico de singularidades |

### Parámetros comunes

Las herramientas utilizarán, según el método:

* punto inicial;
* tolerancia;
* máximo número de iteraciones;
* criterio de convergencia;
* parámetros específicos del método;
* mensajes de advertencia o error.

---

# 3. Entrada de los problemas

Los sistemas podrán representarse mediante expresiones matemáticas estructuradas.

Por ejemplo:

```text
variables:
    ["x", "y"]

equations:
    ["x**2 + y**2 - 1", "x**2 - y"]

x0:
    [0.5, 0.5]

tol:
    1e-8

max_iter:
    100
```

El servidor deberá comprobar que el número de ecuaciones sea compatible con el número de variables y que los parámetros proporcionados sean válidos.

Las expresiones matemáticas serán procesadas mediante un mecanismo controlado, evitando la ejecución arbitraria de código.

---

# 4. Validación y manejo de errores

El módulo `validacion.py` se encargará de verificar:

* cantidad de variables y ecuaciones;
* dimensiones del punto inicial;
* expresiones matemáticas válidas;
* tolerancias positivas;
* máximo de iteraciones razonable;
* valores numéricos finitos;
* consistencia del Jacobiano cuando sea proporcionado;
* parámetros específicos de cada método.

El servidor deberá detectar situaciones como:

```text
converged
max_iter
diverged
singular_jacobian
invalid_input
non_finite_value
```

De esta manera, una falla numérica no será confundida con una solución correcta.

---

# 5. Arquitectura general

```text
                         Usuario
                            │
                            ▼
                  Cliente / Modelo MCP
                            │
                            ▼
                       server.py
                    Servidor MCP
                            │
                            ▼
                     validacion.py
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
          ▼                                   ▼
   Métodos numéricos                   Diagnóstico común
          │                            convergencia.py
          │
          ├── punto_fijo.py
          ├── newton_sistemas.py
          ├── cuasi_newton.py
          ├── descenso.py
          └── homotopia.py
          │
          ▼
               Resultado estructurado
          │
          ├──────────────┬───────────────┐
          ▼              ▼               ▼
     Cliente MCP    HTML interactivo   LaTeX / PDF
          │              │               │
          ▼              ▼               ▼
     Explicación      Gráficos        Informe académico
     pedagógica       dinámicos
```

La arquitectura separa:

**MCP:** comunicación y exposición de las herramientas.
**Métodos numéricos:** cálculo matemático.
**Validación:** control de entradas y errores.
**Visualización:** gráficos y tablas.
**Reportes:** generación de HTML y LaTeX/PDF.
**Modelo:** interpretación y explicación de los resultados.

---


# 6. Prompts MCP

Se definirán prompts reutilizables para ayudar al modelo a interpretar los resultados.

### `explicar_convergencia_newton`

Permitirá generar una explicación del comportamiento observado en el método de Newton, utilizando los resultados producidos por la herramienta.

### `comparar_metodos_no_lineales`

Permitirá comparar métodos utilizando información realmente obtenida durante las ejecuciones, por ejemplo:

* número de iteraciones;
* error final;
* residuo;
* comportamiento de convergencia;
* costo computacional observado.

La comparación se realizará sobre resultados calculados por el servidor y no mediante valores inventados por el modelo.

---

# 7. Ejemplos de uso

| Solicitud del usuario                                                | Tool utilizada                | Resultado esperado                                    |
| -------------------------------------------------------------------- | ----------------------------- | ----------------------------------------------------- |
| “Resuelve \(x^2+y^2=1,\;x^2-y=0\) con Newton”                        | `newton_sistemas`             | Solución, iteraciones, error y residuo                |
| “Aplica Broyden al sistema \(F(x,y)\)”                               | `cuasi_newton_broyden`        | Solución y evolución de la aproximación del Jacobiano |
| “Usa punto fijo con esta función de iteración”                       | `punto_fijo_varias_variables` | Trayectoria y condición de convergencia               |
| “Resuelve el sistema minimizando la norma del residuo”               | `descenso_mas_rapido`         | Trayectoria y evolución de la función objetivo        |
| “Continúa la solución desde un sistema sencillo al sistema objetivo” | `homotopia_continuacion`      | Curva de continuación y diagnóstico                   |

---

# 8. Arquitectura del proyecto

```text
grupoXX/
└── semanaNN/
    └── sistemas-no-lineales-mcp/
        ├── server.py
        ├── validacion.py
        │
        ├── metodos/
        │   ├── punto_fijo.py
        │   ├── newton_sistemas.py
        │   ├── cuasi_newton.py
        │   ├── descenso.py
        │   └── homotopia.py
        │
        ├── convergencia.py
        ├── visualizacion.py
        ├── reportes.py
        ├── prompts.py
        │
        ├── tests/
        ├── examples/
        │
        ├── requirements.txt
        ├── Dockerfile
        └── README.md
```

### Función de los principales archivos

`server.py`
Expone las herramientas MCP y coordina las operaciones.

`validacion.py`
Verifica las entradas y parámetros.

`punto_fijo.py`, `newton_sistemas.py`, `cuasi_newton.py`, `descenso.py`, `homotopia.py`
Implementan los métodos numéricos.

`convergencia.py`
Realiza cálculos y diagnósticos relacionados con error, residuo y comportamiento de convergencia.

`visualizacion.py`
Genera tablas y gráficos.

`reportes.py`
Genera los informes HTML y LaTeX.

`prompts.py`
Contiene los prompts reutilizables para la interpretación pedagógica.

`tests/`
Contiene las pruebas unitarias y de integración.

`examples/`
Contiene ejemplos de sistemas utilizados para demostraciones y validación.

`Dockerfile`
Permite ejecutar el servidor dentro de un contenedor.

El uso de `docker-compose.yml` se deja como opcional y solo se incorporará si el proyecto termina utilizando varios servicios que justifiquen su uso.

---

# 9. Pruebas

Cada método será probado con sistemas conocidos o construidos específicamente para evaluar:

* convergencia;
* divergencia;
* máximo de iteraciones;
* diferentes tolerancias;
* puntos iniciales;
* Jacobiano singular;
* entradas inválidas;
* problemas de dimensiones;
* valores no finitos.

También se realizará una prueba de integración para comprobar:

```text
Cliente MCP
     ↓
Tool
     ↓
Método numérico
     ↓
Resultado estructurado
     ↓
Visualización / reporte
```

---

# 10. Resultado final del proyecto

El usuario podrá realizar una solicitud en lenguaje natural como:

> “Resuelve este sistema con Newton y muestra cómo converge.”

El flujo será:

```text
Usuario
   │
   ▼
Modelo / Cliente MCP
   │
   ▼
newton_sistemas
   │
   ▼
Servidor MCP
   │
   ▼
Método numérico
   │
   ▼
Resultado estructurado
   │
   ├── solución
   ├── iteraciones
   ├── error
   ├── residuo
   ├── trayectoria
   └── estado
   │
   ├──────────────► HTML interactivo
   │
   ├──────────────► LaTeX / PDF
   │
   └──────────────► Modelo
                         │
                         ▼
                 Explicación pedagógica
```

De esta manera, un mismo cálculo puede producir diferentes salidas sin volver a ejecutar el método.

---

# 11. Integrantes y roles

| Integrante                       | Rol                                 | Responsabilidades principales                                                              |
| -------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------ |
| **Nicanor Yalo Palomino**        | **Arquitectura MCP e integración**  | `server.py`, definición de las tools, estructura de entradas/salidas e integración general |
| **Arroni Guadalupe Dylan Eval**  | **Métodos de punto fijo y Newton**  | `punto_fijo.py`, `newton_sistemas.py` y pruebas numéricas                                  |
| **Salvador Damián Navarro**      | **Métodos cuasi-Newton y descenso** | `cuasi_newton.py`, `descenso.py` y pruebas correspondientes                                |
| **Francisco Alonso Olaya Girón** | **Homotopía y convergencia**        | `homotopia.py`, `convergencia.py` y análisis del comportamiento numérico                   |
| **Calixto Luna Jhovany**         | **Visualización, reportes y QA**    | `visualizacion.py`, `reportes.py`, `tests/`, `Dockerfile` y pruebas de integración         |

Aunque cada integrante tendrá archivos principales asignados, el proyecto se desarrollará de manera integrada para que cada módulo pueda ser probado junto con el servidor MCP.

---
