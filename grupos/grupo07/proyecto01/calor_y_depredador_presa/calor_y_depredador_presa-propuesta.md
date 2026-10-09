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

Para garantizar un desarrollo progresivo y escalable, el servidor procesará dos modelos matemáticos complementarios:
1. **Módulo Introductorio (EDO):** El modelo presa-depredador de **Lotka-Volterra**, que sirve como un sistema dinámico dependiente únicamente del tiempo.
2. **Módulo Avanzado (EDP):** La **Ecuación del Calor en 2D**, un problema físico más complejo que requiere discretización espaciotemporal.

En lugar de que la IA intente predecir números, el MCP interceptará las peticiones, resolverá las ecuaciones en Python con métodos numéricos exactos y devolverá gráficos interpretativos.

## 2. Los Modelos Matemáticos a Implementar

### A. Ecuaciones de Lotka-Volterra (Nivel Básico)
Sistema de Ecuaciones Diferenciales Ordinarias (EDO) que modela la interacción biológica entre dos especies.
* **Modelo:** 
  $\frac{dx}{dt} = \alpha x - \beta xy$ (Presas)
  $\frac{dy}{dt} = \delta xy - \gamma y$ (Depredadores)
* **Solución Numérica:** Implementación mediante integradores iterativos (usando `scipy.integrate`).
* **Visualización:** Gráficos de series de tiempo y diagramas de plano de fase.

### B. Ecuación del Calor 2D (Nivel Avanzado)
Ecuación Diferencial Parcial (EDP) parabólica que modela la propagación térmica.
* **Modelo:** 
  $\frac{\partial u}{\partial t} = \alpha \left( \frac{\partial^2 u}{\partial x^2} + \frac{\partial^2 u}{\partial y^2} \right)$
* **Solución Numérica:** Discretización mediante el método de Diferencias Finitas operando sobre mallas matriciales en `numpy`.
* **Visualización:** Mapas de calor (heatmaps) estáticos y superficies térmicas 3D.

## 3. Estructura Modular de Archivos

El repositorio mantendrá una arquitectura contenerizada y modular, alineada con el estándar del curso:

```text
ecuacion_del_calor/
|-- docs/                            # Documentación detallada del código
|-- Dockerfile                       # Instrucciones de empaquetado del contenedor
|-- docker-compose.yml               # Orquestación del servicio MCP
|-- propuesta_grupo07.md             # Propuesta del proyecto
|-- matematica.py                    # Motor de cálculo (EDOs y EDPs)
|-- requirements.txt                 # Dependencias (numpy, scipy, matplotlib, mcp)
|-- server.py                        # Servidor principal MCP (orquestador)
|-- storage.py                       # Gestión de guardado de los gráficos generados
|-- validacion.py                    # Validaciones de esquemas JSON y datos de entrada
`-- visualizacion.py                 # Generador de representaciones gráficas


Entrada del usuario (parámetros físicos, condiciones iniciales)
   |
   v
server.py   ->   validacion.py
(orquestador)    (valida entrada)
   |
   |-------------------------------------------|
   |                                           |
   v (según la tool invocada)                  |
   |                                           |
simular_lotka_volterra                  simular_calor_2d
matematica.py                           matematica.py
(Runge-Kutta / EDOs)                    (Diferencias Finitas)
   |                                           |
   |-------------------------------------------|
   |
   v
visualizacion.py       ->       storage.py
(gráficos, heatmaps)            (gestión de archivos)
   |
   v
Resultado final (JSON + imágenes + texto explicativo)