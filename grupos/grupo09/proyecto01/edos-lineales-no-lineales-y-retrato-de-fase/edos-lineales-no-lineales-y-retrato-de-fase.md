
# Grupo 09 - Tema

#  **EDOs lineales, no lineales y retrato de fase**


El proyecto propone una herramienta que permita definir y resolver ecuaciones diferenciales ordinarias y sistemas de EDOs, analizar su comportamiento y visualizar sus soluciones mediante gráficas y retratos de fase.

La herramienta trabajará con problemas de la forma

$ \mathbf{x}' = \mathbf{F}(t,\mathbf{x};\boldsymbol{\theta}) $

donde:

- $\mathbf{x}$ representa las variables de estado.
- $t$ representa la variable independiente.
- $\boldsymbol{\theta}$ representa los parámetros del modelo.
- $\mathbf{F}$ define el sistema de ecuaciones diferenciales.

El problema se complementa con condiciones iniciales de la forma

$ \mathbf{x}(t_0)=\mathbf{x}_0 $

y un intervalo de análisis

$ t\in[t_0,t_f] $.

---

## Funcionamiento y arquitectura

La herramienta recibe una EDO o un sistema de EDOs junto con sus condiciones iniciales, parámetros e intervalo de análisis.

`server.py` funciona como el orquestador principal del proyecto: recibe la entrada del usuario, coordina la ejecución de los distintos módulos y construye la respuesta final.

El flujo general se organiza de la siguiente manera:

```text
Entrada del problema
        │
        ▼
server.py
Orquesta el flujo de la aplicación
        │
        ▼
datos_validacion.py
Valida ecuaciones, parámetros,
condiciones iniciales e intervalo
        │
        ▼
modelo_edos.py
Resuelve la EDO o sistema de EDOs
y obtiene las trayectorias
        │
        ▼
validacion_solucion.py
Verifica que las soluciones obtenidas
satisfagan la EDO y las
condiciones iniciales
        │
        ▼
analisis_estabilidad.py
Analiza puntos de equilibrio,
Jacobiano, autovalores
y estabilidad local
        │
        ▼
visualizacion.py
Genera gráficas temporales,
trayectorias y retratos de fase
        │
        ▼
server.py
Construye la respuesta final
        │
        ▼
Resultado final
````

---

# Integrantes y roles

| Integrante                            | Rol                                 | Responsabilidad principal                                                                                                 |
| ------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Yanac Minaya Junior Alberto**       | Matemático I — Modelado principal   | Formulación de las EDOs e implementación de los métodos de resolución.                                                    |
| **Tisnado Yarleque Christian David**  | Matemático II — Análisis matemático | Análisis de sistemas lineales y no lineales, puntos de equilibrio, Jacobiano, autovalores y estabilidad.                  |
| **Quispe Gonzales Mark**              | Orquestador / Backend / Datos       | Integración de módulos, servidor, manejo de entradas y construcción de la respuesta final.                                |
| **David Alejandro Tejada Ossio**      | Visualización                       | Generación de gráficas, trayectorias y retratos de fase en HTML.                                                          |
| **Illescas Vicente Alexander George** | Verificación de soluciones          | Verificación de las soluciones obtenidas para las EDOs mediante sustitución, comparación de resultados y casos de prueba. |

---

## Arquitectura propuesta

```text
grupo09/
└── semanaNN/
    └── edos-lineales-no-lineales-y-retrato-de-fase/
        │
        ├── server.py
        ├── datos_validacion.py
        │
        ├── modelo_edos.py
        ├── validacion_solucion.py
        ├── analisis_estabilidad.py
        │
        ├── visualizacion.py
        │
        ├── requirements.txt
        ├── Dockerfile
        └── docker-compose.yml
```

---

## Archivos y responsables

* `server.py` — **Quispe Gonzales Mark**

  Orquestador principal de la aplicación. Recibe la entrada, coordina la ejecución de los módulos y construye la respuesta final.

* `datos_validacion.py` — **Quispe Gonzales Mark**

  Manejo, validación y preparación de las ecuaciones, parámetros, condiciones iniciales e intervalo de análisis.

* `modelo_edos.py` — **Yanac Minaya Junior Alberto**

  Implementación del modelo matemático y de los métodos utilizados para resolver las EDOs y sistemas de EDOs.

* `validacion_solucion.py` — **Illescas Vicente Alexander George**

  Verificación de las soluciones obtenidas para las EDOs mediante sustitución, comparación de resultados y casos de prueba.

* `analisis_estabilidad.py` — **Tisnado Yarleque Christian David**

  Cálculo y análisis de puntos de equilibrio, matriz Jacobiana, autovalores y estabilidad local cuando el sistema lo permita.

* `visualizacion.py` — **David Alejandro Tejada Ossio**

  Generación de gráficas de las soluciones, trayectorias y retratos de fase en HTML.

* `requirements.txt` — **Quispe Gonzales Mark**

  Registro de las dependencias necesarias para instalar y ejecutar el proyecto.

* `Dockerfile` — **Quispe Gonzales Mark**

  Empaquetado de la aplicación y sus dependencias dentro de un contenedor.

* `docker-compose.yml` — **Quispe Gonzales Mark**

  Configuración del despliegue de la aplicación y su conexión con la infraestructura utilizada en el curso.

