# INTERPOLA-MCP

Simulador web de **Interpolación Polinomial** inspirado en la interfaz entregada:
- HTML
- CSS
- JavaScript
- Python + Flask
- Herramientas MCP en `mcp_server.py`

## 1. Instalar

Se recomienda Python 3.10 o superior.

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/macOS:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 2. Ejecutar la interfaz

```bash
python app.py
```

Abrir:

```text
http://127.0.0.1:5000
```

## 3. Probar el servidor MCP

El archivo `mcp_server.py` expone:
- `interpolacion_lagrange`
- `interpolacion_newton`
- `comparar_metodos`

Con el CLI del SDK:

```bash
mcp dev mcp_server.py
```

La interfaz web usa Flask para comunicarse con el motor matemático. El servidor MCP queda separado para que el proyecto pueda conectarse posteriormente a un cliente/host MCP real.

## 4. Ejemplo inicial

Los datos vienen precargados:

| x | y |
|---:|---:|
| 1 | 2 |
| 2 | 5 |
| 3 | 10 |
| 4 | 17 |

Evaluación: `x = 2.5`

El polinomio correcto para esos puntos es:

`P(x) = x² + 1`

Por tanto:

`P(2.5) = 7.25`

## Estructura

```text
INTERPOLA-MCP/
├── app.py
├── interpolation.py
├── mcp_server.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── styles.css
    └── js/
        └── app.js
```
