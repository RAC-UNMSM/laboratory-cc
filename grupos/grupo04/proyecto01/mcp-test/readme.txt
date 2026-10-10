GRUPO04 MCP — MÉTODOS NUMÉRICOS
================================

La documentación principal está en README.md. El plan, diseños de interfaz y documentos técnicos están en la carpeta docs.

HERRAMIENTAS
Se conservan las cuatro de interpolación Newton/Lagrange. Nuevas herramientas: analizar_aritmetica_flotante, analizar_error_numerico, propagar_error_numerico, resolver_raiz, resolver_sistema_lineal, resolver_sistema_disperso, ajustar_datos, derivar_numericamente, derivar_tabla_numericamente, integrar_numericamente, integrar_tabla_numericamente, resolver_edo, resolver_valores_propios, optimizar_funcion, resolver_problema_frontera y resolver_pde.

ACTUALIZAR DEPENDENCIAS LOCALES
Desde PowerShell, dentro de mcp-test:
    .\.ENTORNO\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python app.py

DOCKER
Inicia Docker Desktop. En PowerShell:
    $env:LAB_CONTAINER_NAME = "lab-grupo04_proyecto01_mcp-test"
    docker network create lab_net
    docker compose up --build
Si lab_net ya existe, omite la creación. No ejecutes app.py y Docker al mismo tiempo.

INSPECTOR
Con el servidor activo, conecta Streamable HTTP a http://localhost:8000/mcp. Selecciona grupo04-mcp-test y abre Tools.

PDF
Las nuevas herramientas devuelven enlaces report.preview_url y report.download_url. Cloudflare debe enrutar /mcp y /reports al puerto 8000. Docker guarda informes en el volumen reports_data.

LÍMITES
Expresiones matemáticas permitidas, no código Python. Sistemas densos limitados a 250x250; el solver disperso admite COO/CSR hasta 5000x5000 y 100000 entradas. BVP y PDE están acotados a casos 1D según docs/CATALOGO_HERRAMIENTAS.md. Revisa status y diagnostics, sobre todo cuando no converja.
