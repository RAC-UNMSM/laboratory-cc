# INTEGRACION-MCP

Integra el motor numérico de **INTERPOLA-MCP** con las herramientas MCP y reportes de **MCP-TEST** en una aplicación independiente. Los proyectos originales permanecen intactos.

## Qué incluye

- Interfaz web basada en la pantalla original de INTERPOLA-MCP, conservando su diseño, colores, menús y distribución. Añade el estado de conexión y la descripción de los proyectos MCP integrados, además de enlaces a reportes.
- Cálculo por Lagrange o Newton, comparación de resultados, gráfica Plotly y tabla de diferencias divididas.
- Informes HTML autocontenidos: incluyen resultados, tabla de datos, diferencias divididas y una gráfica vectorial; no usan CDN ni requieren conexión a Internet para visualizarse. Se pueden publicar como archivos estáticos o abrir en cualquier navegador.
- Archivo SVG independiente de la gráfica, además de la gráfica incrustada en el informe HTML y en el PDF.
- Informes PDF con gráfica, resultados y tablas, generados con ReportLab. El sistema siempre conserva HTML y SVG aunque el generador PDF no esté disponible.
- Herramientas MCP STDIO: `resolver_interpolacion`, `interpolacion_lagrange`, `interpolacion_newton` y `comparar_interpolacion`.
- Catálogo web de informes creados y rutas de salud para despliegue.

## Iniciar en Windows

Ejecuta `run.bat`. La primera ejecución crea un entorno virtual e instala las dependencias. La interfaz queda disponible en `http://localhost:5000`.

También se puede instalar manualmente:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Los archivos generados se guardan en `reports/` usando `storage.py`: cada cálculo crea un `.html` y un `.svg`, y también un `.pdf` si ReportLab está disponible. La interfaz permite abrir el HTML y la imagen SVG y descargar el PDF.

## Conectar un cliente MCP

Configura un servidor de tipo STDIO que ejecute `run_mcp.bat`, con `INTEGRACION-MCP` como directorio de trabajo. En clientes que acepten configuración JSON, sustituye `<RUTA_INTEGRACION_MCP>` por la ruta absoluta a esta carpeta:

```json
{
  "mcpServers": {
    "integracion-mcp": {
      "command": "<RUTA_INTEGRACION_MCP>\\run_mcp.bat",
      "args": [],
      "cwd": "<RUTA_INTEGRACION_MCP>"
    }
  }
}
```

Para iniciar el servidor MCP a mano, instala dependencias y ejecuta `python server.py` (también puedes usar `python mcp_server.py`). Las herramientas reciben `points` como lista de objetos `{"x": número, "y": número}`, además de `x_eval`, método y opciones para generar reportes. MCP devuelve cálculos y rutas locales para HTML, SVG y PDF.

## Despliegue web

La imagen incluida publica el servicio en el puerto 8000 mediante Gunicorn y guarda los reportes en `/app/reports`. Asigna un volumen persistente a esa carpeta en la plataforma de despliegue para conservar los informes entre reinicios. El endpoint de salud es `/api/health`.

```sh
docker build -t integracion-mcp .
docker run --rm -p 8000:8000 -v integracion_reportes:/app/reports integracion-mcp
```

Por seguridad, coloca el servicio detrás del proxy HTTPS del entorno de producción y restringe el acceso según las políticas del despliegue.

## Rutas principales

```text
INTEGRACION-MCP/
├── app.py                 # Interfaz HTTP y API
├── server.py              # Punto de entrada MCP
├── mcp_server.py          # Registro de herramientas MCP STDIO
├── interpolation.py       # Motor matemático
├── reports.py             # HTML, SVG y PDF opcional
├── storage.py             # Ubicación y listado de archivos generados
├── templates/index.html   # Menús y espacio de trabajo
├── static/                # Estilos y lógica del navegador
└── reports/               # Archivos generados (excluidos de Git)
```
