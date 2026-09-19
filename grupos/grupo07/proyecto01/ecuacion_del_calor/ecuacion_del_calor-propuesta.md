# Reporte del Proyecto: Servidor MCP para la Ecuación del Calor

**Identificación del Equipo**  
**Grupo 07**  
*Líder del Proyecto: Luis*

**Integrantes (3 miembros):**
1. **Luis** (Líder del Grupo 07 / Arquitectura MCP)
2. **Piero** (Desarrollador Python - Resolución Numérica)
3. **Alejandro** (Desarrollador Python - Visualización de Datos)

## 1. Idea General del Proyecto

El objetivo del Grupo 07 es desarrollar un **Servidor MCP (Model Context Protocol)** especializado en la simulación y análisis de la **Ecuación del Calor en 2D** (una ecuación diferencial parcial parabólica). 

El sistema permitirá que un modelo de lenguaje interactúe con motores matemáticos construidos en Python (usando librerías como **NumPy** y **SciPy**) para calcular la evolución térmica de una superficie. En lugar de solo generar respuestas de texto, el MCP resolverá la EDP mediante métodos numéricos exactos y devolverá los resultados procesados en formato visual e interpretativo.

## 2. Estructura de los 2 Apartados Principales

El proyecto se dividirá internamente en dos apartados funcionales independientes que se comunicarán a través del servidor principal:

### APARTADO 1: Resolutor Numérico (Motor Matemático)
Este módulo se encarga del cálculo pesado utilizando métodos de diferencias finitas.
* **Objetivo:** Discretizar el dominio espacial y temporal para resolver la ecuación paso a paso.
* **Características:** Podrá recibir diferentes condiciones (como temperaturas fijas en los bordes) y procesará los cálculos vectorizados mediante arreglos de NumPy para garantizar eficiencia.

### APARTADO 2: Generador de Visualizaciones (Renderizado)
Este módulo toma las matrices de temperatura calculadas y genera representaciones gráficas.
* **Objetivo:** Hacer comprensibles los datos numéricos mediante activos visuales.
* **Características:** Generación de mapas de calor (heatmaps) en 2D que muestran la distribución térmica en instantes de tiempo específicos, devolviéndolos al cliente para su visualización.

## 3. Estructura Modular de Archivos y Componentes

Para cumplir con las normas de nombrado (minúsculas, sin espacios ni tildes), el repositorio se organizará bajo la siguiente arquitectura:

```text
ecuacion_del_calor/
|-- ecuacion_del_calor-propuesta.md  # Propuesta del proyecto
|-- server.py                        # Servidor principal MCP (orquestador)
|-- matematica.py                    # Motor de cálculo numérico (EDP)
|-- grafica.py                       # Generador de visualizaciones
|-- requirements.txt                 # Dependencias (numpy, matplotlib, mcp)