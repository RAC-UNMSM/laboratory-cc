# Grupo 03 — Tema

**Integrantes:** Lidia Galán · Priscila Cossio · Katherin Cardenas · Stive Choccare · Camila Morán · Andre Carrillo

---

## **Extrapolación de Richardson y aplicaciones en métodos numéricos**

> **Curso de origen:** Métodos Numéricos

La idea principal es usar la **extrapolación de Richardson** para mejorar la precisión de distintos métodos numéricos, combinando cálculos con diferentes tamaños de paso en lugar de solo reducir $h$. Lo elegimos porque nos permite cubrir varios métodos relacionados entre sí y repartir bien el trabajo.

Los módulos que vamos a desarrollar son:

| Módulo | Descripción |
|--------|-------------|
| **Derivación con Richardson** | Diferencias centradas con extrapolación para subir el orden de precisión |
| **Integración de Romberg** | Regla del trapecio + Richardson iterado, con criterio de parada por tolerancia |
| **Richardson genérico** | Función que aplica la extrapolación a cualquier método numérico que se le pase |
| **Bulirsch-Stoer (EDOs)** | Resolución de ecuaciones diferenciales usando Runge-Kutta + Richardson |
| **Análisis de convergencia** | Comparación gráfica del error antes y después de extrapolar |

*La selección está sujeta a ajustes según la retroalimentación del docente.*

---

## Funcionamiento y arquitectura

La herramienta recibe la definición de un problema numérico (función, parámetros, tolerancia) y devuelve resultados refinados, gráficos de convergencia y explicaciones en lenguaje natural.

`server.py` funciona como el orquestador principal del proyecto: recibe la entrada del usuario, coordina la ejecución de los distintos módulos y construye la respuesta final.

El flujo general se organiza de la siguiente manera:

```text
Entrada del usuario (función, parámetros, tolerancia)
    │
    ▼
server.py  →  validacion.py
(orquestador)   (valida entrada)
    │
    ├──────────────────────────────────────┐
    │                                      │
    ▼  (según la tool invocada)            │
    │                                      │
 derivacion_richardson.py                  │
 romberg.py                                │
 richardson_generico.py          convergencia.py
 bulirsch_stoer.py               (análisis de error)
    │                                      │
    └──────────────────────────────────────┘
                    │
                    ▼
          visualizacion.py  +  explicacion.py
          (gráficos, tablas)   (texto explicativo)
                    │
                    ▼
          Resultado final (JSON + imágenes + texto)
```

---

## Ejemplo de uso

La idea es que un usuario le haga una pregunta a un modelo de IA (Claude, por ejemplo) y este internamente invoque las tools del servidor MCP:

| El usuario escribe... | El MCP hace... | El modelo responde... |
|---|---|---|
| *"Calcula la derivada de sin(x) en x=1 con Richardson"* | Llama a `derivacion_richardson` con la función y el punto | Resultado numérico + tabla de aproximaciones + gráfico de convergencia |
| *"Integra e^(-x²) entre 0 y 1 con Romberg, tolerancia 1e-8"* | Llama a `romberg` con los parámetros | Valor de la integral + tabla de Romberg completa |
| *"Resuelve y' = -y, y(0)=1 en [0,5]"* | Llama a `bulirsch_stoer` con la EDO | Solución numérica + gráfico de la trayectoria |

---

## Arquitectura propuesta

```text
grupo03/
└── semanaNN/
    └── extrapolacion-richardson-mcp/
        ├── server.py
        ├── validacion.py
        ├── derivacion_richardson.py
        ├── romberg.py
        ├── richardson_generico.py
        ├── bulirsch_stoer.py
        ├── convergencia.py
        ├── visualizacion.py
        ├── explicacion.py
        │
        ├── requirements.txt
        ├── Dockerfile
        └── docker-compose.yml
```

### Formato de salida

- **Resultados numéricos** en formato estructurado (JSON), para que el modelo de IA los interprete y presente.
- **Gráficos** exportados como imágenes o SVG, embebidos en la respuesta.
- **Tablas de resultados** (ej. tabla de Romberg) en formato tabular legible.
- **Explicación** en lenguaje natural del procedimiento y el error estimado.

---

## Integrantes y roles

| Integrante | Rol | Archivo(s) principal(es) |
|---|---|---|
| Lidia Galán | Derivación numérica | `derivacion_richardson.py` |
| Priscila Cossio | Integración de Romberg | `romberg.py` |
| Katherin Cardenas | Richardson genérico y Bulirsch-Stoer | `richardson_generico.py`, `bulirsch_stoer.py` |
| Stive Choccare | Servidor MCP (infraestructura) | `server.py`, `validacion.py` |
| Camila Morán | Visualización y explicación | `visualizacion.py`, `explicacion.py` |
| Andre Carrillo | Convergencia, pruebas y despliegue | `convergencia.py`, `Dockerfile`, `docker-compose.yml` |

---

## Archivos y responsables

- **`server.py`** — **Stive Choccare**

  Orquestador principal de la aplicación. Define las tools MCP, recibe la entrada, coordina los módulos y construye la respuesta final.

- **`validacion.py`** — **Stive Choccare**

  Manejo, validación y preparación de los parámetros de entrada: funciones, tolerancias, intervalos y condiciones.

- **`derivacion_richardson.py`** — **Estela Galán**

  Implementación de la derivada numérica con extrapolación de Richardson: diferencias centradas, tabla de aproximaciones y resultado refinado.

- **`romberg.py`** — **Priscila Cossio**

  Implementación de la integración de Romberg con tabla triangular completa y criterio de parada por tolerancia.

- **`richardson_generico.py`** — **Katherin Cardenas**

  Función de orden superior que recibe cualquier método numérico y le aplica extrapolación de Richardson de forma genérica.

- **`bulirsch_stoer.py`** — **Katherin Cardenas**

  Resolución de EDOs combinando Runge-Kutta con extrapolación de Richardson (método de Bulirsch-Stoer).

- **`convergencia.py`** — **Andre Carrillo**

  Análisis y comparación de convergencia entre métodos base y extrapolados: error vs. tamaño de paso, orden observado vs. teórico.

- **`visualizacion.py`** — **Camila Morán**

  Generación de gráficos de convergencia (escala log-log), tablas de Romberg como heatmaps y trayectorias de solución.

- **`explicacion.py`** — **Camila Morán**

  Construcción de explicaciones en lenguaje natural del procedimiento aplicado, niveles de extrapolación y mejora de orden obtenida.

- **`requirements.txt`** — **Andre Carrillo**

  Dependencias del proyecto: NumPy, SciPy, Matplotlib, MCP SDK (FastMCP), pytest.

- **`Dockerfile`** y **`docker-compose.yml`** — **Andre Carrillo**

  Empaquetado del servidor en contenedor Docker, desplegable vía Portainer.

---

## Stack técnico

- **Lenguaje:** Python
- **SDK:** MCP SDK oficial (FastMCP), para definir las tools con decoradores
- **Librerías matemáticas:** NumPy, SciPy (validación cruzada de resultados)
- **Visualización:** Matplotlib
- **Contenedor:** Docker, gestionado con Portainer
- **Pruebas:** pytest, para validar las funciones matemáticas contra casos conocidos
