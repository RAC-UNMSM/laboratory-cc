# Grupo 08: Sistemas No Lineales MCP

Servidor MCP en Python para resolver sistemas no lineales con cinco métodos
numéricos y generar un reporte HTML de cada ejercicio enviado desde Claude
Desktop.

## Qué hace

La herramienta MCP `resolver_ejercicio` recibe el enunciado, las expresiones,
las variables, el punto inicial, el método y los parámetros numéricos. Claude
debe convertir el enunciado a esos datos estructurados; si faltan el método o
el punto inicial, debe preguntarlos antes de llamar a la herramienta.

Al resolver un ejercicio, el servidor:

- Ejecuta el método y devuelve estado, solución, trayectoria, error y residuo.
- Genera un HTML con formulación y pasos en LaTeX mediante MathJax, tabla de
  iteraciones, verificación y gráfica de trayectoria SVG.
- Guarda el HTML en `salida-mathjax/` con un UUID en el nombre.
- Registra el enunciado, resultado y ruta del reporte en
  `sistemas-no-lineales/config/proyecto_config.json`.

También están disponibles las herramientas de cálculo directo: `newton_sistemas`,
`punto_fijo_varias_variables`, `cuasi_newton_broyden`, `descenso_mas_rapido` y
`homotopia_continuacion`. Estas devuelven resultados numéricos; para generar el
HTML y actualizar el JSON, usar `resolver_ejercicio`.

## Métodos

| Método MCP | Módulo |
| --- | --- |
| `newton_sistemas` | `metodos/newton_sistemas.py` |
| `punto_fijo_varias_variables` | `metodos/punto_fijo.py` |
| `cuasi_newton_broyden` | `metodos/cuasi_newton.py` |
| `descenso_mas_rapido` | `metodos/descenso.py` |
| `homotopia_continuacion` | `metodos/homotopia.py` |

## Estructura

```text
sistemas-no-lineales/
├── server.py                 # Herramientas MCP
├── metodos/                  # Algoritmos numéricos
├── resultado.py              # Contrato común de resultados
├── validacion.py             # Validación de parámetros
├── convergencia.py           # Normas y criterios de convergencia
├── visualizacion.py          # Trayectorias SVG y HTML
├── reportes.py               # Reportes HTML y LaTeX
├── identificadores.py        # IDs únicos para archivos generados
├── config/proyecto_config.json
├── salida-mathjax/            # Reportes generados
├── examples/                 # Ejemplos reproducibles
└── tests/                    # Pruebas
```

## Instalación y pruebas en Windows

Desde PowerShell, en esta carpeta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest tests -v
```

## Conectar Claude Desktop

En Claude Desktop, abre **Configuración → Desarrollador → Editar configuración**.
Agrega el bloque `mcpServers` al JSON existente, sin reemplazar otras
preferencias. Sustituye las rutas por las de tu computadora:

```json
{
  "mcpServers": {
    "sistemas-no-lineales": {
      "command": "C:\\ruta\\a\\python.exe",
      "args": [
        "C:\\ruta\\al\\proyecto\\sistemas-no-lineales\\server.py"
      ],
      "env": {
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Guarda el archivo y reinicia Claude Desktop. En un chat nuevo, envía el
ejercicio e indica el método; Claude debe llamar a `resolver_ejercicio` para
que se genere el reporte.

## Ejemplo de solicitud

```text
Usa resolver_ejercicio para resolver x^2 + y^2 = 1, x - y = 0 con
Newton-Raphson, variables x,y, x0=[1, 0.5], tolerancia 1e-8 y máximo
100 iteraciones. Genera el HTML en salida-mathjax.
```

Expresiones que se pasan al servidor:

```json
{
  "expresiones": ["x**2 + y**2 - 1", "x - y"],
  "variables": ["x", "y"],
  "x0": [1.0, 0.5],
  "metodo": "newton_sistemas",
  "tolerancia": 1e-8,
  "max_iter": 100
}
```

## Ejecutar ejemplos

```powershell
python -m examples.ejemplo_reportes --salida salida-mathjax/ejemplo
python -m examples.generar_reportes_metodos --salida salida-mathjax/metodos
```

Estos comandos generan demostraciones; Claude crea reportes de ejercicios reales
mediante `resolver_ejercicio`.

## Límites actuales

- La gráfica se incrusta como SVG en el HTML; todavía no se genera un PNG aparte.
- No hay carga automática a Rclone ni creación de archivos RAR.
- MathJax se descarga desde un CDN, por lo que requiere conexión a internet para
  renderizar las fórmulas.
- El servidor MCP usa STDIO; `docker-compose.yml` construye el contenedor para
  el entorno del laboratorio y requiere la red externa `lab_net`.