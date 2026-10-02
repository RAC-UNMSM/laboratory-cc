# Grupo 09 — Propuesta de proyecto

## EDOs lineales y no lineales, retratos de fase, sistemas dinámicos caóticos, atractores extraños y bifurcaciones

El proyecto propone un agente computacional que permita definir y resolver ecuaciones diferenciales ordinarias (EDOs) y sistemas de EDOs, analizar su comportamiento y visualizar sus soluciones mediante gráficas y retratos de fase. En atención a la retroalimentación del profesor, el alcance incorpora el estudio de **sistemas dinámicos caóticos, atractores extraños y bifurcaciones**, con métodos de análisis y verificación específicos.

El agente integrará resolución matemática, simulación numérica, análisis cualitativo y explicaciones sustentadas en los resultados calculados. Permitirá explorar cómo cambian las soluciones al modificar las condiciones iniciales o los parámetros del modelo.

## Objetivo general

Desarrollar un agente para resolver y analizar EDOs lineales y no lineales que permita estudiar estabilidad, retratos de fase, sensibilidad a condiciones iniciales, atractores extraños y bifurcaciones, mediante herramientas matemáticas y computacionales verificables.

## Formulación del problema

La herramienta trabajará con problemas de valor inicial de la forma:

$$
\mathbf{x}'=\mathbf{F}(t,\mathbf{x};\boldsymbol{\theta}),
\qquad \mathbf{x}(t_0)=\mathbf{x}_0,
\qquad t\in[t_0,t_f].
$$

Donde:

- $\mathbf{x}$ representa las variables de estado.
- $t$ representa la variable independiente.
- $\boldsymbol{\theta}$ representa los parámetros del modelo.
- $\mathbf{F}$ define el sistema de ecuaciones diferenciales.

Para el análisis de equilibrios y bifurcaciones se priorizarán sistemas autónomos, de la forma $\mathbf{x}'=\mathbf{F}(\mathbf{x};\boldsymbol{\theta})$. Las EDOs de orden superior podrán tratarse cuando se puedan transformar en sistemas explícitos de primer orden.

Además de las ecuaciones, condiciones iniciales e intervalo, el usuario podrá indicar el análisis solicitado, las tolerancias numéricas y, cuando corresponda, el parámetro que desea variar, su rango y la cantidad de valores a evaluar.

## Alcance funcional

- **Resolución:** soluciones analíticas cuando sea posible e integración Runge–Kutta con control del error.
- **Estabilidad:** equilibrios, Jacobiano, autovalores y retratos de fase 1D–3D.
- **Caos:** sensibilidad a condiciones iniciales y estimación del máximo exponente de Lyapunov con renormalización y descarte de transitorios.
- **Atractores extraños:** simulación de Lorenz, visualización 3D, proyecciones 2D y secciones de Poincaré.
- **Bifurcaciones:** barridos paramétricos, diagramas de equilibrio y máximos locales; casos silla-nodo, horquilla y Hopf.

**Alcance:** sistemas suaves de 1–3 variables; análisis avanzado en sistemas autónomos. Los indicadores de caos se reportarán como evidencia numérica.

## Funcionamiento y arquitectura

`server.py` será el orquestador principal: recibirá la solicitud, seleccionará los módulos pertinentes y construirá una respuesta explicativa a partir de sus resultados. Los cálculos y las conclusiones deberán conservar la configuración utilizada para poder reproducirse.

```text
Entrada: EDO o sistema, condiciones iniciales, parámetros y análisis
                              |
                              v
                         server.py
                              |
                              v
                    datos_validacion.py
                              |
                              v
                       modelo_edos.py
                  Solución y trayectorias base
                              |
                              v
                  validacion_solucion.py
                  Comprobación del cálculo base
                              |
                              v
              Módulos según el análisis solicitado
             /                |                   \
            v                 v                    v
 analisis_estabilidad.py  analisis_caos.py  analisis_bifurcaciones.py
 Equilibrios, Jacobiano   Sensibilidad,     Barridos, ramas y
 y estabilidad local     Lyapunov y        cambios de comportamiento
                         Poincaré
             \                |                   /
                              v
                  validacion_solucion.py
                 Comprobación de los indicadores
                              |
                              v
                      visualizacion.py
                              |
                              v
                         server.py
                              |
                              v
      Soluciones, gráficas, interpretación y reporte de verificación
```

Los módulos de caos y bifurcaciones reutilizarán `modelo_edos.py` para ejecutar las simulaciones adicionales necesarias. Si una validación falla, el servidor informará el problema y evitará emitir conclusiones basadas en resultados inválidos.

## Integrantes y roles

| Integrante | Rol | Responsabilidad principal |
| --- | --- | --- |
| **Yanac Minaya Junior Alberto** | Matemático I — Modelado, resolución y simulación dinámica | Formular las EDOs, implementar los métodos de resolución y los modelos de referencia, y desarrollar el cálculo de sensibilidad, Lyapunov y secciones de Poincaré. |
| **Tisnado Yarleque Christian David** | Matemático II — Estabilidad y bifurcaciones | Analizar equilibrios, Jacobiano y autovalores; desarrollar los barridos paramétricos y la clasificación de bifurcaciones; sustentar la interpretación matemática de los indicadores de caos y atractores. |
| **Quispe Gonzales Mark** | Orquestador / Backend / Datos | Integrar los módulos, validar las entradas, gestionar simulaciones y barridos, conservar la configuración de cada ejecución y construir la respuesta final del agente. |
| **David Alejandro Tejada Ossio** | Visualización de soluciones y dinámica | Generar gráficas temporales, retratos de fase, trayectorias y atractores 3D, secciones de Poincaré, comparación de trayectorias y diagramas de bifurcación en HTML. |
| **Illescas Vicente Alexander George** | Verificación de soluciones y resultados dinámicos | Comprobar soluciones analíticas y numéricas, evaluar convergencia y sensibilidad a tolerancias, y verificar los indicadores de caos y las bifurcaciones mediante casos de referencia. |

## Arquitectura propuesta

```text
grupo09/
└── semanaNN/
    └── edos-lineales-no-lineales-y-retrato-de-fase/
        ├── server.py
        ├── datos_validacion.py
        ├── modelo_edos.py
        ├── modelos_referencia.py
        ├── validacion_solucion.py
        ├── analisis_estabilidad.py
        ├── analisis_caos.py
        ├── analisis_bifurcaciones.py
        ├── visualizacion.py
        ├── tests/
        ├── requirements.txt
        ├── Dockerfile
        └── docker-compose.yml
```

## Archivos y responsables

| Archivo o carpeta | Responsable principal | Función |
| --- | --- | --- |
| `server.py` | **Quispe Gonzales Mark** | Orquestar el agente, seleccionar los análisis, manejar errores y reunir soluciones, evidencias y explicaciones. |
| `datos_validacion.py` | **Quispe Gonzales Mark** | Validar ecuaciones, dimensiones, parámetros, condiciones iniciales, intervalo, tolerancias y configuración de barridos. |
| `modelo_edos.py` | **Yanac Minaya Junior Alberto** | Implementar resolución analítica cuando sea posible e integración numérica reutilizable para todos los análisis. |
| `modelos_referencia.py` | **Yanac Minaya Junior Alberto** | Definir casos lineales, no lineales, Lorenz y formas normales de bifurcación, con sus parámetros y condiciones iniciales. Christian apoyará en la formulación de los casos de bifurcación. |
| `analisis_estabilidad.py` | **Tisnado Yarleque Christian David** | Calcular equilibrios, Jacobiano y autovalores; clasificar estabilidad local e identificar casos no concluyentes. |
| `analisis_caos.py` | **Yanac Minaya Junior Alberto** | Comparar trayectorias cercanas, estimar Lyapunov mediante perturbaciones renormalizadas y calcular cruces de Poincaré. Christian apoyará en la interpretación matemática. |
| `analisis_bifurcaciones.py` | **Tisnado Yarleque Christian David** | Ejecutar barridos, calcular ramas de equilibrio y su estabilidad, detectar candidatos a bifurcación y obtener máximos locales de las trayectorias. |
| `validacion_solucion.py` | **Illescas Vicente Alexander George** | Verificar condiciones iniciales, residuos, convergencia numérica y consistencia de los indicadores dinámicos. |
| `visualizacion.py` | **David Alejandro Tejada Ossio** | Crear las visualizaciones en HTML, con ejes, parámetros, leyendas y distinción entre transitorio y comportamiento posterior. |
| `tests/` | **Illescas Vicente Alexander George** | Mantener pruebas de los casos de referencia y de entradas inválidas, con apoyo de cada responsable de módulo. |
| `requirements.txt` | **Quispe Gonzales Mark** | Registrar las dependencias y versiones necesarias para reproducir los cálculos. |
| `Dockerfile` | **Quispe Gonzales Mark** | Empaquetar la aplicación y sus dependencias. |
| `docker-compose.yml` | **Quispe Gonzales Mark** | Configurar la ejecución de la aplicación y su conexión con la infraestructura del curso. |

## Verificación y casos de demostración

| Caso | Resultado que se verificará |
| --- | --- |
| EDO lineal $x'=-2x$, con $x(0)=1$ | Comparación con la solución exacta $x(t)=e^{-2t}$ y reducción del error al ajustar la precisión. |
| Modelo logístico $x'=rx(1-x/K)$, con $r,K>0$ | Equilibrios, estabilidad y convergencia a $K$ para condiciones iniciales positivas. |
| Silla-nodo $x'=\mu-x^2$ | Ausencia de equilibrios para $\mu<0$ y aparición de las ramas $x=\pm\sqrt{\mu}$ para $\mu>0$, con distinta estabilidad. |
| Horquilla $x'=\mu x-x^3$ | Cambio de estabilidad del origen y aparición de dos ramas estables para $\mu>0$. |
| Hopf: $x'=\mu x-y-x(x^2+y^2)$, $y'=x+\mu y-y(x^2+y^2)$ | Cambio de estabilidad del origen en $\mu=0$ y aparición de un ciclo límite estable de radio $\sqrt{\mu}$ para $\mu>0$. |
| Sistema de Lorenz | Trayectorias 3D, sensibilidad a condiciones iniciales, estimación de Lyapunov y comparación de regímenes al variar $\rho$. |

La verificación incluirá:

- **Soluciones analíticas:** sustitución en la EDO y comprobación de las condiciones iniciales.
- **Soluciones numéricas:** contraste con casos exactos, revisión de residuos calculados de forma independiente y comparación al reducir tolerancias o utilizar otro método de integración.
- **Caos:** comparación de trayectorias en intervalos cortos y de indicadores a tiempos largos. Se revisará la estabilidad de Lyapunov y de estadísticas como medias y dispersión; no se exigirá coincidencia punto a punto de trayectorias caóticas a largo plazo.
- **Bifurcaciones:** contraste con valores críticos conocidos, refinamiento del barrido y comprobación de las ramas y su estabilidad. Para los diagramas de máximos se documentarán el transitorio descartado y la condición inicial usada en cada simulación.

## Resultado final esperado

El agente entregará una respuesta que incluya:

1. El problema interpretado y su configuración de cálculo.
2. La solución analítica o numérica, cuando pueda obtenerse.
3. El análisis de estabilidad y las visualizaciones pertinentes.
4. Los indicadores de caos, la exploración del atractor y los resultados del barrido de parámetros, cuando se soliciten y sean aplicables.
5. Una explicación matemática de los resultados, acompañada de su verificación y de las limitaciones detectadas.

La entrega del proyecto incluirá el agente integrado, las visualizaciones en HTML y los casos de demostración reproducibles. Así, la ampliación solicitada quedará reflejada en las funciones, los módulos, las responsabilidades y las evidencias de validación del proyecto.