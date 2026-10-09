import base64


def generar_reporte_html(
    tipo_integral: str,
    latex_str: str,
    resultado_exacto: str,
    resultado_decimal: float,
    png_bytes: bytes,
    nombre_archivo: str = "reporte_integral.html",
    abrir_en_navegador: bool = False,
) -> str:
    """Genera una cadena HTML autocontenida con renderizado MathJax para las fórmulas

    y la imagen embebida en formato Base64.

    Retorna la cadena de texto con el HTML completo generado en memoria.
    """
    # Convierte los bytes de la imagen a Base64 para embeberla directamente
    b64_img = base64.b64encode(png_bytes).decode("utf-8")

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte - {tipo_integral}</title>
    <!-- MathJax para renderizado LaTeX -->
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f6f8; color: #333; }}
        .card {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f77b4; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; font-size: 22px; }}
        .math-box {{ background: #f8fafc; padding: 15px; border-left: 4px solid #1f77b4; font-size: 20px; margin: 20px 0; text-align: center; overflow-x: auto; }}
        .info {{ margin: 15px 0; font-size: 16px; line-height: 1.6; }}
        .info code {{ background: #edf2f7; padding: 3px 8px; border-radius: 4px; font-family: monospace; color: #2d3748; }}
        .grafico {{ text-align: center; margin-top: 25px; }}
        .grafico img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Reporte de Cálculo: {tipo_integral}</h1>
        
        <div class="math-box">
            $${latex_str} = {resultado_exacto}$$
        </div>
        
        <div class="info">
            <p><strong>Resultado exacto:</strong> <code>{resultado_exacto}</code></p>
            <p><strong>Resultado decimal:</strong> <code>{resultado_decimal:.4f}</code></p>
        </div>
        
        <div class="grafico">
            <h2>Visualización del Dominio / Superficie</h2>
            <img src="data:image/png;base64,{b64_img}" alt="Gráfico de la integral" />
        </div>
    </div>
</body>
</html>
"""

    return html_content