# Reporte del Proyecto: Servidor MCP para Cálculo Integral (I - IV)

**Identificación del Equipo**  
**Grupo 02**  
*Líder del Proyecto: Ortega Yucra Hiron Axl*

**Integrantes (6 miembros):**
1. **Ortega Yucra Hiron Axl** (Líder del Grupo 02 / Arquitectura MCP)
2. **Saico Merma Cristhian** (Desarrollador Python - Cálculo I)
3. **Rosales Izquierdo Yhin** (Desarrollador Python - Cálculo II)
4. **Vilcapoma Pariona Jefferson** (Desarrollador Python - Cálculo III)
5. **Meza Nolorbe Angel** (Desarrollador Python - Cálculo IV)
6. **Lau Huamantoma Carlos Yang Hu** (Ingeniero de Prompts & QA / Skills)

## 1. Idea General del Proyecto

El objetivo del Grupo 02 es desarrollar un **Servidor MCP (Model Context Protocol)** que actúe como una plataforma integral de resolución y enseñanza para todo el ciclo universitario de Cálculo (Cálculo I, II, III y IV).

Para cumplir con la complejidad adecuada solicitada a un equipo de 6 personas, el sistema no dependerá únicamente de respuestas generativas de texto. En su lugar, el MCP conectará el modelo de lenguaje con motores de cálculo simbólico programados en Python (usando librerías científicas como **SymPy** y **NumPy**).

De este modo, los cálculos matemáticos (límites, integrales, gradientes, integrales dobles/triples o teoremas de campos vectoriales) son resueltos de forma exacta por código Python, mientras que el modelo de IA se encarga de dar el formato matemático adecuado y la explicación pedagógica requerida.

## 2. Estructura de los 2 Apartados Principales

El proyecto se dividirá internamente en dos apartados funcionales independientes:

```text
                       +----------------------------------------+
                       |       SERVIDOR MCP (server.py)         |
                       +------------------+---------------------+
                                          |
           +------------------------------+------------------------------+
           v                                                             v
+--------------------------------+                            +--------------------------------+
|           APARTADO 1           |                            |           APARTADO 2           |
|    Resolutor de Ejercicios     |                            |  Tutor Académico Interactivo   |
+----------------+---------------+                            +---------------+----------------+
                 |                                                            |
        +--------+--------+                                          +--------+--------+
        v                 v                                          v                 v
  [Modo Examen]     [Paso a Paso]                              [Desde Cero]       [Avanzado]
```

### APARTADO 1: Resolutor de Ejercicios Prácticos

Este módulo está pensado para procesar cualquier ejercicio específico que proporcione el usuario y resolverlo en tiempo real mediante dos modalidades de visualización:

* **Opción A - Respuesta Formal de Examen:**
  * **Objetivo:** Entregar la resolución directa y rigurosa, tal como se exigiría en una evaluación presencial o examen escrito.
  * **Formato:** Notación matemática limpia en LaTeX, pasos algebraicos resumidos, citación de teoremas clave y respuesta final bien destacada.

* **Opción B - Explicación Paso a Paso:**
  * **Objetivo:** Explicar detalladamente el procedimiento al estudiante.
  * **Formato:** Desglose minucioso de cada cambio de variable, justificación de propiedades, recomendaciones para evitar errores comunes y explicaciones didácticas en cada etapa del cálculo.

### APARTADO 2: Tutor Académico Interactivo (Aprendizaje Progresivo)

Este módulo funciona con una ventana de contexto (*skill*) independiente, diseñada específicamente para guiar al usuario en el aprendizaje teórico y práctico de los cursos.

* **Ventana de Contexto Independiente:** Posee sus propias reglas de interacción, comportamiento y evaluación, aisladas de la herramienta de examen.
* **Modalidades de Aprendizaje:**
  * **Modo Desde Cero:** Guía al estudiante tema por tema desde los conceptos fundamentales (límites, funciones, integrales básicas) de manera progresiva.
  * **Modo Avanzado:** Permite al usuario seleccionar temas complejos específicos (ej. Multiplicadores de Lagrange, Teorema de Green, Stokes o Gauss) para repasarlos directamente.
* **Interacción y Verificación:** El tutor expone la teoría, muestra ejemplos y plantea ejercicios prácticos. Cuando el usuario responde, el MCP ejecuta las herramientas en Python en segundo plano para verificar matemáticamente si la respuesta del usuario es correcta antes de retroalimentarlo.

## 3. Estructura Modular de Archivos y Componentes

> **Nota:** esta sección se actualizó para reflejar la estructura que se
> construyó finalmente. La partición inicial era de 7 módulos (uno por tema);
> se cambió a **4 módulos, uno por área y por persona**, que es como quedó
> repartido el trabajo y lo que hace que 5 personas puedan escribir en paralelo
> sin pisarse. La carpeta también cambió de nombre: el profesor pidió que el
> proyecto viva dentro de `proyecto01/`.

El repositorio del Grupo 02 se organiza bajo la siguiente arquitectura de directorios:

```text
calculo-i-iv/
|-- server.py               # Servidor principal MCP (orquestador)
|-- requirements.txt        # mcp==2.1.1 (pinned), sympy, numpy
|-- Dockerfile
|-- docker-compose.yml
|-- skill/                  # Contextos de comportamiento (Markdown)
|   |-- skill_resolver_examen.md   # Instrucciones de examen formal
|   |-- skill_paso_a_paso.md       # Instrucciones de paso a paso
|   `-- skill_tutor_interactivo.md # Contexto del tutor
|-- tools/                  # Motores matemáticos (SymPy / NumPy)
|   |-- README.md           # El contrato que debe cumplir cada módulo
|   |-- _plantilla.py       # Plantilla a copiar por cada integrante
|   |-- calculo1.py         # Cálculo I   (Saico Cristhian)
|   |-- calculo2.py         # Cálculo II  (Rosales Yhin)
|   |-- calculo3.py         # Cálculo III (Vilcapoma Jefferson)
|   `-- calculo4.py         # Cálculo IV  (Meza Angel)
`-- tests/                  # Pruebas de estructura
```

`server.py` carga los módulos de `tools/` **de forma dinámica al arrancar**:
recorre `calculo1.py` … `calculo4.py`, registra sus funciones públicas como
tools MCP con el prefijo del módulo (`calculo4_green`, `calculo1_limite`…) y
no hay que tocar el servidor para agregar una función nueva.

## 4. Organización de Tareas para el Grupo 02

Para asegurar una carga de trabajo equilibrada y orientada al desarrollo técnico, la división de tareas queda definida de la siguiente manera:

* **Ortega Yucra Hiron Axl (Líder / Grupo 02):**
  * Diseño de la arquitectura del MCP y programación del archivo principal `server.py`.
  * Integración del flujo de comunicación entre las *Tools* en Python y los prompts (*Skills*).
* **Saico Merma Cristhian:**
  * Programación de las herramientas computacionales para Cálculo I (`limites_continuidad.py`, `derivadas_optimizacion.py`).
* **Rosales Izquierdo Yhin:**
  * Programación de las herramientas computacionales para Cálculo II (`integrales.py`, `integrales_aplicaciones.py`).
* **Vilcapoma Pariona Jefferson:**
  * Programación de las herramientas computacionales para Cálculo III (`calculo_multivariable.py`).
* **Meza Nolorbe Angel:**
  * Programación de las herramientas computacionales para Cálculo IV (`integrales_multiples.py`, `campos_vectoriales.py`).
* **Lau Huamantoma Carlos Yang Hu:**
  * Redacción y calibración lógica de las *Skills* en la carpeta respectiva (`skill_resolver_examen.md`, etc.).
  * Realización de pruebas unitarias (*tests*) y control de calidad de las respuestas entregadas por el MCP (QA).