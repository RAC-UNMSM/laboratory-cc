# Reporte del Proyecto: Servidor MCP para Modelado Matemático Computacional

**Identificación del Equipo**

**Grupo 07**

*Líder del Proyecto: Luis*

**Integrantes (3 miembros):**

1. **Luis** (Líder del Grupo 07 / Infraestructura MCP)
2. **Piero** (Desarrollador Python - Resolución Numérica)
3. **Alejandro** (Desarrollador Python - Visualización de Datos)

## 1. Idea General del Proyecto

El objetivo del Grupo 07 es desarrollar un **Servidor MCP (Model Context Protocol)** que dote a los modelos de lenguaje de capacidades reales de cálculo y graficación para sistemas dinámicos.

Para garantizar un desarrollo progresivo y escalable, el servidor procesará tres modelos matemáticos complementarios, abarcando desde principios fundamentales hasta dinámicas complejas:

1. **Módulo Fundamental:** **Decaimiento Radiactivo**, que sirve como introducción a los sistemas dinámicos dependientes del tiempo mediante una EDO lineal.
2. **Módulo Intermedio:** El modelo biológico de **Lotka-Volterra**, introduciendo sistemas de EDOs acopladas y dinámicas no lineales.
3. **Módulo Avanzado:** La **Ecuación del Calor en 2D**, un problema físico complejo que requiere discretización espaciotemporal mediante EDPs.

En lugar de que la IA intente predecir números (lo cual genera alucinaciones), el MCP interceptará las peticiones, resolverá las ecuaciones en Python con métodos numéricos/analíticos exactos y devolverá gráficos interpretativos y reportes HTML.

## 2. Los Modelos Matemáticos a Implementar

### A. Decaimiento Radiactivo (Nivel Fundamental)

Ecuación Diferencial Ordinaria (EDO) de primer orden que modela la desintegración de isótopos inestables en el tiempo.

* **Modelo:** $\frac{dN}{dt} = -\lambda N$
* **Solución Matemática:** Implementación de su solución analítica exacta ($N(t) = N_0 e^{-\lambda t}$) utilizando operaciones vectorizadas en `numpy`.
* **Visualización:** Curva de decaimiento exponencial (2D) con sombreado de área para ilustrar la pérdida de masa/partículas.

### B. Ecuaciones de Lotka-Volterra (Nivel Intermedio)

Sistema de Ecuaciones Diferenciales Ordinarias (EDO) acopladas que modela la interacción biológica entre dos especies.

* **Modelo:**
$\frac{dx}{dt} = \alpha x - \beta xy$ (Presas)
$\frac{dy}{dt} = \delta xy - \gamma y$ (Depredadores)
* **Solución Numérica:** Implementación mediante integradores iterativos (usando `scipy.integrate`).
* **Visualización:** Gráficos de series de tiempo y diagramas de plano de fase.

### C. Ecuación del Calor 2D (Nivel Avanzado)

Ecuación Diferencial Parcial (EDP) parabólica que modela la propagación térmica en una superficie.

* **Modelo:**
$\frac{\partial u}{\partial t} = \alpha \left( \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} \right)$
* **Solución Numérica:** Discretización mediante el método de Diferencias Finitas operando sobre mallas matriciales en `numpy`.
* **Visualización:** Mapas de calor (heatmaps) estáticos ilustrando el gradiente de temperatura.

## 3. Estructura Modular de Archivos

El repositorio mantendrá una arquitectura contenerizada y modular, alineada con el estándar del curso y lista para el despliegue automático:

```text
calor-y-depredador-presa/
|-- docs/                            # Documentación detallada del código
|-- Dockerfile                       # Instrucciones de empaquetado del contenedor
|-- docker-compose.yml               # Orquestación del servicio en lab_net (con variables de entorno)
|-- README.md                        # Propuesta y manual del proyecto
|-- matematica.py                    # Motor de cálculo (Soluciones exactas, EDOs y EDPs)
|-- requirements.txt                 # Dependencias (numpy, scipy, matplotlib, mcp, anyio)
|-- server.py                        # Servidor principal MCP (orquestador FastMCP)
|-- storage.py                       # Gestión de subida a SeaweedFS
|-- validacion.py                    # Validaciones de seguridad física y límites matemáticos
`-- visualizacion.py                 # Generador de representaciones gráficas en memoria RAM (BytesIO)
`-- reporte.py                       # Generador de reportes HTML locales con imágenes Base64

```

### Flujo de Ejecución Arquitectónica

```text
Entrada del usuario (parámetros físicos, condiciones iniciales)
   |
   v
server.py   ->   validacion.py
(orquestador)    (filtra valores absurdos o físicos irreales)
   |
   |-----------------------------------------------------------------------|
   |                                                                       |
   v (según la tool invocada)                                              |
   |                                                                       |
simular_decaimiento          simular_lotka_volterra       simular_calor_2d
matematica.py                matematica.py                matematica.py
(Solución Exponencial)       (Integración Numérica)       (Diferencias Finitas)
   |                                                                       |
   |-----------------------------------------------------------------------|
   |
   v
visualizacion.py       ->      storage.py
(generación en RAM)            (subida a la nube SeaweedFS)
   |
   v
reporte.py (Generación de HTML de respaldo local)
   |
   v
Resultado final (Markdown para Claude con URL de imagen + Datos estadísticos)

```