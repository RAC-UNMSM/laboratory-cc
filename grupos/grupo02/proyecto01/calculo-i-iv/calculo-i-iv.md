# Propuesta de Proyecto: Servidor MCP-Cálculo (Cálculo I - IV)

**Identificación del Equipo:**  
**Grupo 02 — Curso de Inteligencia Artificial / MCP (UNMSM)**  
*Líder del Proyecto: Ortega Yucra Hiron Axl*

**Integrantes (6 miembros):**
1. **Ortega Yucra Hiron Axl** — *Líder / Arquitectura MCP, Servidor, Docker y Storage*
2. **Saico Merma Cristhian** — *Desarrollador Python: Cálculo I*
3. **Rosales Izquierdo Yhin** — *Desarrollador Python: Cálculo II*
4. **Vilcapoma Pariona Jefferson** — *Desarrollador Python: Cálculo III*
5. **Meza Nolorbe Angel** — *Desarrollador Python: Cálculo IV*
6. **Lau Huamantoma Carlos Yang Hu** — *Ingeniero de Prompts, Skills y QA / Suite de Pruebas*

---

## 1. Fundamentación y Justificación de Complejidad (24 Temas Clave)

Para un equipo de **6 integrantes**, un proyecto centrado en un único tema elemental (como derivadas simples de una variable que los modelos de lenguaje suelen resolver por texto) no satisface la complejidad técnica exigida.

Por ello, **MCP-Cálculo** aborda de manera integral la secuencia completa de la matemática universitaria: **Cálculo I, II, III y IV**, seleccionando **6 temas fundamentales por cada curso** (24 temas en total), rigurosamente fundamentados en los sílabos oficiales de la Facultad de Ingeniería de Sistemas e Informática:

### 1.1 Cálculo I — Fundamentos y Análisis en $\mathbb{R}$ (`tools/calculo1.py`)
1. **Relaciones y funciones reales:** Determinación exacta de dominio, rango y biyectividad.
2. **Límites y cálculo asintótico:** Límites laterales, límites al infinito y determinación de asíntotas verticales, horizontales y oblicuas.
3. **Límites especiales e indeterminaciones:** Formas trigonométricas ($\lim \frac{\sin x}{x}$), exponenciales y logarítmicas.
4. **Continuidad y teoremas de discontinuidad:** Clasificación formal de discontinuidades (evitables, de salto, esenciales).
5. **Cálculo diferencial:** Regla de la cadena, derivación implícita de curvas algebraicas y derivadas de orden superior.
6. **Aplicaciones de la derivada:** Teoremas de Rolle y del Valor Medio, extremos relativos y optimización exacta de polinomios.

### 1.2 Cálculo II — Cálculo Integral y Series (`tools/calculo2.py`)
1. **Antiderivadas e integrales indefinidas:** Integración inmediata, método de sustitución y por partes.
2. **Técnicas avanzadas de integración:** Fracciones parciales, sustituciones trigonométricas, sustituciones de Euler y diferenciales binomias (Chebyshev).
3. **Sumas de Riemann y Teorema Fundamental:** Deducción rigurosa del TFC e integración definida exacta.
4. **Aplicaciones geométricas de la integral:** Áreas entre curvas planas, volúmenes de sólidos de revolución (métodos de discos y arandelas) y longitud de arco.
5. **Centro de masa e integración numérica:** Teoremas de Pappus-Guldin, centroides de láminas planas, aproximación por regla del trapecio y Simpson.
6. **Integrales impropias y funciones especiales:** Convergencia de integrales impropias de 1ra y 2da especie, funciones Gamma $\Gamma(p)$ y Beta $\mathrm{B}(p, q)$.

### 1.3 Cálculo III — Geometría en $\mathbb{R}^3$ y Cálculo Multivariable (`tools/calculo3.py`)
1. **Geometría analítica en $\mathbb{R}^3$:** Operaciones vectoriales exactas (producto escalar, vectorial y mixto), rectas, planos y distancias mínimas.
2. **Superficies en el espacio:** Identificación y ecuaciones de superficies cilíndricas, cuádricas y esféricas; cálculo de vectores normales.
3. **Funciones vectoriales y cinemática de curvas:** Triedro de Frenet-Serret ($\mathbf{T}, \mathbf{N}, \mathbf{B}$), cálculo exacto de rapidez, curvatura $\kappa(t)$ y torsión $\tau(t)$.
4. **Cálculo diferencial multivariable:** Dominios en $\mathbb{R}^n$, derivadas parciales de primer y segundo orden y vector gradiente $\nabla f$.
5. **Plano tangente y aproximación lineal:** Ecuación del plano tangente $\pi_T$ y recta normal a superficies diferenciables $z = f(x, y)$.
6. **Optimización multivariable:** Matriz Hessiana $H(f)$, criterio del discriminante para puntos de silla/extremos y Multiplicadores de Lagrange $\nabla f = \lambda \nabla g$.

### 1.4 Cálculo IV — Cálculo Vectorial e Integrales Múltiples (`tools/calculo4.py`)
1. **Parametrización de curvas y campos vectoriales:** Representación paramétrica de trayectorias en el plano y espacio.
2. **Integrales de línea y campos conservativos:** Cálculo de trabajo $\int_C \mathbf{F} \cdot d\mathbf{r}$, rotacional nulo y reconstrucción de la función potencial $\phi$.
3. **Integrales dobles y cambio de variable:** Integración sobre regiones generales y transformaciones mediante el determinante Jacobiano $J(u, v)$.
4. **Teorema de Green en el plano:** Relación entre integrales de línea sobre curvas cerradas y flujo/circulación sobre regiones simplemente conexas.
5. **Integrales triples y de superficie:** Integrales de volumen y flujo de campos vectoriales a través de superficies parametrizadas o explícitas.
6. **Teoremas integrales vectoriales clásicos:** Teorema de la Divergencia de Gauss ($\iint \mathbf{F} \cdot d\mathbf{S} = \iiint \nabla \cdot \mathbf{F} \, dV$) y Teorema de Stokes ($\oint \mathbf{F} \cdot d\mathbf{r} = \iint (\nabla \times \mathbf{F}) \cdot d\mathbf{S}$).

---

## 2. Acciones y Alcance del Servidor MCP

El servidor actúa como un intermediario riguroso entre los modelos de lenguaje (LLMs) y el motor simbólico de **SymPy**, garantizando que **ningún cálculo matemático sea inventado ni aproximado erróneamente**:

```text
                                 +---------------------------------------+
                                 |       SERVIDOR MCP (server.py)         |
                                 +-------------------+-------------------+
                                                     |
                     +-------------------------------+-------------------------------+
                     v                                                               v
      +-----------------------------+                                 +-----------------------------+
      |         APARTADO 1          |                                 |         APARTADO 2          |
      |   Resolutor de Ejercicios   |                                 |  Tutor Académico Interactivo|
      +--------------+--------------+                                 +--------------+--------------+
                     |                                                               |
            +--------+--------+                                             +--------+--------+
            v                 v                                             v                 v
      [Modo Examen]     [Paso a Paso]                                 [Nivel Cero]      [Avanzado]
            |                 |                                             |                 |
            +--------+--------+                                             +--------+--------+
                     |                                                               |
                     +-------------------------------+-------------------------------+
                                                     v
                                         +-----------------------+
                                         | Motores SymPy (tools/)|
                                         | calculo1 a calculo4   |
                                         +-----------+-----------+
                                                     |
                                                     v
                                         +-----------------------+
                                         | Storage SeaweedFS     |
                                         | Generación Gráfica    |
                                         +-----------------------+
```

### Funcionalidades Principales:
1. **Deducción Algebraica Exacta:** Integrales, derivadas, límites y matrices son evaluados con SymPy. Los resultados se entregan en expresiones simplificadas exactas (ej. $\frac{1}{3}$, no $0.3333$; $\sqrt{2}$, no $1.4142$).
2. **Generación de Respuestas en LaTeX:** Todas las herramientas devuelven la representación formal en $\LaTeX$ para renderizado de alta fidelidad matemática.
3. **Visualización y Subida de Gráficos (SeaweedFS):**
   * El módulo `storage.py` interactúa con el clúster interno de SeaweedFS (`http://seaweedfs:8333`) mediante peticiones HTTP `PUT`.
   * Asigna claves aleatorias seguras (`uuid.uuid4().hex.png`) para evitar colisiones entre usuarios.
   * Devuelve enlaces Markdown públicos directos:  
     `![Gráfico](https://rac-unmsm.vekthos.org/img/grupo02-calculo-i-iv/<key>.png)`
4. **Verificación Simbólica en Tiempo Real:** La herramienta base `verificar_respuesta` calcula la diferencia simbólica entre la respuesta del estudiante y la solución de referencia (`simplify(diff) == 0`), tolerando constantes de integración $+ C$ y reordenamientos algebraicos.

---

## 3. Los 2 Apartados Principales del Sistema

### Apartado 1: Resolutor de Ejercicios Prácticos
* **Modo Examen (Respuesta Formal — `skill_resolver_examen.md`):**
  * Presenta soluciones directas, elegantes y rigurosas estructuradas para una prueba escrita universitaria.
  * Notación $\LaTeX$ impecable, sin explicaciones redundantes y con mención explícita de teoremas y resultados finales recuadrados.
* **Modo Paso a Paso (`skill_paso_a_paso.md`):**
  * Desglose pedagógico detallado: explicita la elección del cambio de variable, la descomposición en fracciones, la parametrización de curvas y la comprobación del resultado por derivación o diferenciación inversa.

### Apartado 2: Tutor Académico Interactivo (`skill_tutor_interactivo.md`)
* Funciona bajo una ventana de contexto aislada.
* **Progresión pedagógica flexible:**
  * *Nivel Cero:* Guía al estudiante desde los axiomas y conceptos base hacia la resolución de ejercicios elementales.
  * *Nivel Avanzado:* Salta directamente a problemas de nivel de examen final o de olimpiada matemática.
* **Ciclo socrático con verificación:** Expone la teoría, plantea un ejercicio concreto y suspende la respuesta hasta que el alumno proponga su desarrollo. En segundo plano ejecuta `verificar_respuesta` para confirmar con SymPy si la propuesta es correcta antes de retroalimentar.

---

## 4. Arquitectura de Archivos y Despliegue

```text
grupos/grupo02/proyecto01/calculo-i-iv/
├── server.py               # Orquestador MCP: herramientas base + carga dinámica de tools
├── storage.py              # Cliente SeaweedFS: subida PUT HTTP de imágenes y generación de URLs
├── requirements.txt        # Dependencias fijadas: mcp==2.1.1, sympy==1.12
├── Dockerfile              # python:3.11-slim, CMD ["python", "server.py"], streamable-http
├── docker-compose.yml      # mem_limit: 512m, container_name: ${LAB_CONTAINER_NAME}, red lab_net
├── skill/                  # Prompts / Skills de comportamiento
│   ├── skill_resolver_examen.md
│   ├── skill_paso_a_paso.md
│   └── skill_tutor_interactivo.md
├── tools/                  # Motores matemáticos modulares (1 por curso)
│   ├── README.md           # Contrato técnico obligatorio
│   ├── _plantilla.py       # Plantilla de referencia
│   ├── calculo1.py         # Cálculo I (8 tools públicas)
│   ├── calculo2.py         # Cálculo II (6 tools públicas)
│   ├── calculo3.py         # Cálculo III (6 tools públicas)
│   └── calculo4.py         # Cálculo IV (6 tools públicas)
└── test/                   # Suite unificada de pruebas locales (excluida del repo por .gitignore)
    ├── test_estructura.py  # Validación estática AST, Dockerfile y políticas de recursos
    ├── test_skills.py      # Verificación de consistencia entre skills y firmas de tools
    ├── _prueba_matematica.py # 40 casos de prueba simbólica exacta
    ├── _smoke.py           # Smoke test de herramientas MCP
    └── _cliente.py         # Cliente MCP de integración
```

---

## 5. Distribución de Tareas y Responsabilidades (Equipo de 6)

| Integrante | Rol Principal | Componentes y Responsabilidades |
|---|---|---|
| **Ortega Yucra Hiron Axl** | Líder / Arquitectura MCP | Diseño de la arquitectura del servidor MCP (`server.py`), orquestación dinámica con `importlib`, integración con el almacenamiento de imágenes SeaweedFS (`storage.py`), configuración de Docker, `docker-compose.yml` y CI/CD. |
| **Saico Merma Cristhian** | Desarrollador Python: Cálculo I | Implementación del motor `tools/calculo1.py` (límites, continuidad, asíntotas, derivación implícita, recta tangente y optimización) con retornos en LaTeX. |
| **Rosales Izquierdo Yhin** | Desarrollador Python: Cálculo II | Implementación de `tools/calculo2.py` (integración indefinida, técnicas avanzadas, sumas de Riemann / TFC, aplicaciones geométricas, integración numérica y Gamma/Beta). |
| **Vilcapoma Pariona Jefferson** | Desarrollador Python: Cálculo III | Implementación de `tools/calculo3.py` (vectores en $\mathbb{R}^3$, superficies, triedro de Frenet-Serret, derivadas parciales y gradiente, plano tangente y optimización de Lagrange / Hessiano). |
| **Meza Nolorbe Angel** | Desarrollador Python: Cálculo IV | Implementación de `tools/calculo4.py` (curvas paramétricas, integrales de línea, integrales dobles/triples, Teorema de Green y teoremas integrales de Gauss y Stokes). |
| **Lau Huamantoma Carlos Yang Hu** | Ingeniero de Prompts & QA | Diseño, calibración y redacción de las 3 skills en `skill/`, construcción de la suite de pruebas matemáticas y de estructura en `test/`, y validación continua con `mcp-validator`. |