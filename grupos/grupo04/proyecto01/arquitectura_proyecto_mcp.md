# MCP – Suite Avanzada de Interpolación y Aproximación (Grupo 04)

> **Curso base:** Métodos Numéricos II
> **Visión del Proyecto:** Un servidor MCP escalable que permite a los LLMs (como Claude, Gemini o ChatGPT) analizar grandes conjuntos de datos (Big Data), aplicar diversos métodos de interpolación/aproximación, renderizar gráficos avanzados y exportar reportes completos.

## 1. Alcance Escalado (Características Ambiciosas)

Para que el proyecto soporte "grandes cantidades de datos, visualizaciones y descargas", el servidor MCP expondrá **múltiples tools**:

1. **`analyze_and_clean_data`**: Recibe grandes arrays o rutas de archivos (CSV/JSON), limpia valores atípicos (outliers), datos nulos y prepara la data.

2. **`interpolate_dataset`**: Permite elegir el método (*Lagrange, Newton, Trazadores Cúbicos, Mínimos Cuadrados*). Usa `SciPy` y `NumPy` para operaciones vectorizadas (alto rendimiento) cuando la data es masiva.

3. **`generate_visualizations`**: Devuelve tanto imágenes estáticas (Matplotlib en base64) para el chat de la IA, como enlaces a gráficos interactivos (Plotly/HTML) para exploración profunda.

4. **`download_report`**: Genera un archivo PDF con todo el análisis (fórmulas en LaTeX, tablas de errores, gráficos) y lo disponibiliza para descarga local.

## 2. Arquitectura del Sistema

```
flowchart TD
    A["Cliente MCP (LLM)"] <-->|Protocolo stdio/HTTP| B["Servidor MCP (Router)"]
    
    B -->|Tool: analyze_data| C["Módulo de Datos (Pandas)"]
    B -->|Tool: interpolate| D["Núcleo Matemático (NumPy/SciPy/SymPy)"]
    B -->|Tool: visualize| E["Motor Visual (Matplotlib/Plotly)"]
    B -->|Tool: export| F["Generador de Reportes (FPDF/ReportLab)"]
    
    C --> G[(Archivos Temporales / CSV)]
    D --> |Cálculo en Paralelo| D
    E --> |Imágenes Base64| B
    E --> |HTML Interactivo| G
    F --> |PDF Generado| G
    
    G --> |Descarga de Archivos| A

```

## 3. División del Trabajo — 7 Integrantes

Cada integrante es "dueño" de un microservicio o módulo dentro del ecosistema del MCP para trabajar sin bloqueos.

| Integrante | Rol en el Proyecto | Responsabilidades (Alcance) | Archivos Clave | 
 | ----- | ----- | ----- | ----- | 
| **Roussy Aguilar** | **Project Manager & MCP Architect** | Define el servidor base, los schemas JSON de las tools (entradas/salidas) y el enrutamiento. Asegura que el servidor hable correctamente el protocolo MCP. | `server.py`, `schemas/` | 
| **Jardiny Guerra** | **Data Engineer (Ingesta y Limpieza)** | Implementa lógica para recibir arrays gigantes o leer CSVs. Limpia datos (NaNs, duplicados), normaliza escalas y particiona la data si es muy grande. | `src/data_handler.py` | 
| **Cristopher Catalan** | **Core Matemático I (Interpolación Simbólica)** | Implementa métodos exactos: **Lagrange y Diferencias Divididas de Newton**. Genera las expresiones algebraicas (SymPy) y representaciones en LaTeX. | `src/math_exact.py` | 
| **Omar Supo** | **Core Matemático II (Big Data y Splines)** | Implementa métodos para grandes datos: **Trazadores Cúbicos (Splines) y Mínimos Cuadrados**. Usa SciPy para procesamiento matricial de alto rendimiento. | `src/math_numeric.py` | 
| **Alexander Benavente** | **Motor de Visualización** | Crea gráficos estáticos (PNG base64 para la IA) y gráficos **interactivos** (HTML exportable con Plotly) para que el usuario haga zoom en los datos. | `src/visualization.py` | 
| **Jano Huallpa** | **Exportación y Descargas (Reportes)** | Desarrolla la tool que toma los resultados matemáticos y gráficos, ensamblando un PDF profesional (tablas, fórmulas, gráficos) listo para descargar. | `src/export_report.py` | 
| **Jose Salazar** | **DevOps, QA y Formateador MCP** | Formatea las respuestas combinadas hacia la IA. Crea los tests unitarios (`pytest`), maneja el manejo de excepciones y la "Dockerización" del servidor. | `src/formatter.py`, `tests/` | 

## 4. Estructura de Directorios del Proyecto

```
mcp-metodos-numericos-g4/
├── README.md
├── requirements.txt
├── Dockerfile                  # Para despliegue aislado
├── server.py                   # Registro de las tools MCP
├── src/
│   ├── __init__.py
│   ├── data_handler.py         # Pandas, limpieza de datos
│   ├── math_exact.py           # SymPy, Lagrange, Newton
│   ├── math_numeric.py         # SciPy, Splines, Mínimos Cuadrados
│   ├── visualization.py        # Matplotlib, Plotly
│   ├── export_report.py        # Generación de PDF
│   ├── formatter.py            # Estructuración de la respuesta MCP
│   └── exception_handler.py    # Control centralizado de errores
├── storage/                    # Carpeta temporal para guardar PDFs/HTMLs
├── tests/
│   ├── test_data.py
│   ├── test_math.py
│   └── test_integration.py
└── examples/
    └── big_data_sample.csv     # Dataset de prueba con 10,000+ filas

```

## 5. Especificación de Tools y Casos de Excepción

### Tool Principal: `interpolate_and_analyze`

**Entrada esperada (JSON Schema):**

```
{
  "data_source": {"type": "file", "path": "dataset_10k.csv"},
  "method": "cubic_spline",
  "eval_points": [0.5, 1.5, 1.8],
  "generate_report": true
}

```

### Casos de Excepción y Manejo de Errores (Edge Cases)

El sistema debe ser robusto para no detener el servidor MCP ante errores del usuario o de los datos. Se controlarán los siguientes casos:

1. **Puntos Duplicados en X (División por cero):**

   * *Error:* En Lagrange y Newton, tener el mismo valor de X genera infinitos.

   * *Manejo:* El módulo `data_handler.py` detectará colisiones en X. Si los valores de Y son iguales, eliminará el duplicado; si son distintos, lanzará un error MCP informando al LLM sobre la inconsistencia matemática ("No es una función").

2. **Datasets Masivos con Métodos Simbólicos (Sobrecarga de RAM):**

   * *Error:* Usar SymPy (Lagrange) con más de 50 puntos colapsa la memoria o tarda demasiado.

   * *Manejo:* Si el usuario pide `lagrange` y $N > 50$, el servidor intercepta la petición, cambia automáticamente el método a `cubic_spline` (SciPy) y devuelve un `warning` en el JSON informando que se adaptó el método por razones de rendimiento.

3. **Archivos Corruptos o Formatos Inválidos:**

   * *Error:* Rutas de archivos inexistentes o CSVs con texto en lugar de números.

   * *Manejo:* Bloque `try-except` en la ingesta. Se devuelve un error claro a la IA indicando las filas corruptas para que la IA le pida al usuario que corrija el archivo.

4. **Extrapolación Peligrosa:**

   * *Error:* Evaluar puntos muy alejados del dominio original de los datos.

   * *Manejo:* Se calculará el resultado, pero la respuesta MCP incluirá una bandera `"extrapolation_warning": true`, indicando que el margen de error probabilístico es alto.

## 6. Stack Tecnológico

* **Core / Servidor:** `Python 3.11+`, `mcp` (SDK oficial).

* **Big Data & Data Science:** `pandas`, `numpy`.

* **Matemáticas:** `sympy` (exactas), `scipy` (numéricas).

* **Visualización:** `matplotlib` (estáticas base64), `plotly` (interactivas HTML).

* **Reportes:** `fpdf2` o `reportlab` (PDF).

* **Testing & Ops:** `pytest`, `Docker`.

## 7. Hitos del Proyecto (Roadmap Grupal)

1. **Fase 1: Arquitectura y Mock Inicial (Semana 1)**

   * Configuración del repositorio base y estructura de carpetas.

   * Levantamiento del servidor MCP básico que responde exitosamente al cliente (Inspector/Claude Desktop).

   * Definición estricta de los esquemas JSON de entrada y salida entre módulos.

2. **Fase 2: Procesamiento de Datos y Núcleo Matemático (Semana 2)**

   * Implementación de la lectura de archivos pesados y limpieza automatizada de datos (manejo de las excepciones de ingesta).

   * Desarrollo de los algoritmos matemáticos (tanto los simbólicos como los numéricos optimizados).

   * Pruebas unitarias independientes de los motores matemáticos.

3. **Fase 3: Visualización, Reportes y Ensamblaje (Semana 3)**

   * Generación de los gráficos dinámicos (HTML) y estáticos (Base64) a partir de los arrays interpolados.

   * Diseño y programación de la plantilla PDF (integrando tablas, texto y gráficos).

4. **Fase 4: Integración MCP, Casos Borde y Entrega (Semana 4)**

   * Integración de todos los módulos en el enrutador central de tools (`server.py`).

   * Implementación del gestor global de excepciones (para evitar caídas del servidor).

   * Prueba integral (End-to-End) interactuando con un LLM, enviando un CSV de 5,000 filas y verificando la descarga correcta del reporte final.