# grupo04-mcp-test — Métodos Numéricos

Servidor MCP educativo para familias de problemas de Métodos Numéricos I y II. Expone resultados estructurados, una interfaz MCP App e informes PDF con vista previa y descarga.

## Herramientas
El servidor registra 27 herramientas para interpolación, error, raíces, sistemas lineales/no lineales, aproximación, derivación, cuadratura, EDO, valores propios, optimización, frontera y PDE. Consulta docs/CATALOGO_HERRAMIENTAS.md para argumentos, métodos y límites.

## Alcance y expresiones
Incluye métodos de las familias definidas en los syllabus del proyecto. Las expresiones admiten operaciones aritméticas, pi/e y funciones matemáticas comunes; no ejecutan código Python del usuario. BVP y PDE se limitan a los casos 1D descritos en el catálogo. Revisar docs/REFERENCIA_ALGORITMOS.md para hipótesis y límites.

## Instalación local
Requisitos: Python 3.11 o superior y dependencias de requirements.txt. La generación de PDF usa ReportLab y no requiere pdflatex ni TeX Live.
En PowerShell desde esta carpeta:
    .\.ENTORNO\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python app.py
app.py inicia el MCP local en 127.0.0.1:8000 y busca host.exe/cloudflared para iniciar Cloudflare Tunnel. Para ejecutar sin túnel usa server.py directamente. No ejecutes app.py y Docker simultáneamente porque ocupan el mismo puerto.

## Docker
Inicia Docker Desktop y, en PowerShell:
    $env:LAB_CONTAINER_NAME = "lab-grupo04_proyecto01_mcp-test"
    docker network create lab_net
    docker compose up --build
Si lab_net ya existe, omite su creación. Compose usa un nombre válido por defecto, publica el puerto 8000 para pruebas y conserva PDF en el volumen reports_data. La variable LAB_CONTAINER_NAME se vuelve a definir en cada ventana. Para detener: Ctrl+C y docker compose down. No uses docker compose down -v si quieres conservar los PDF.
Endpoint local: http://localhost:8000/mcp.

## Informes y publicación
La respuesta incluye report.preview_url y report.download_url. Cada tool acepta level='inicial'|'intermedio' e include_report=true|false; omite el PDF con include_report=false para llamadas sin reporte. storage.py administra los PDF; las rutas HTTP son /reports/<archivo>/preview y /reports/<archivo>/download. Cloudflare config debe dirigir /mcp y /reports a http://127.0.0.1:8000 antes de la regla final 404. Reinicia cloudflared al cambiar config.yml.

## Inspector y documentación
Con el servidor arriba, usa MCP Inspector en modo Streamable HTTP con http://localhost:8000/mcp y selecciona grupo04-mcp-test. Ver pruebas.txt y docs/GUIA_DE_USO.md para ejemplos. El proyecto incluye catálogo, guía, algoritmos, despliegue, diseños, contrato, matriz de aceptación e historial de cambios.

La cobertura descrita es la implementada en numerical_methods.py y el catálogo; no se anuncian otros métodos o geometrías.
