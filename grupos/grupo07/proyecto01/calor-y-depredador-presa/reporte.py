import base64
import os

def generar_reporte_lotka_volterra_html(
    presas_max, mes_presas_max, presas_min, mes_presas_min,
    dep_max, mes_dep_max, dep_min, mes_dep_min,
    png_bytes, nombre_archivo
) -> str:
    """
    Genera un HTML autocontenido con la imagen de Lotka-Volterra embebida en base64.
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte - Lotka-Volterra</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f6f8; color: #333; }}
        .card {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f77b4; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; font-size: 24px; }}
        .stats-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-box {{ background: #f0f7fb; padding: 15px; border-left: 4px solid #1f77b4; border-radius: 6px; text-align: center; }}
        .stat-box strong {{ display: block; font-size: 13px; color: #555; text-transform: uppercase; margin-bottom: 5px; }}
        .stat-box span {{ font-size: 20px; font-weight: bold; color: #025aa5; }}
        .grafico {{ text-align: center; margin-top: 30px; }}
        .grafico img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Dinámica de Poblaciones: Ecuaciones de Lotka-Volterra</h1>
        
        <div class="stats-container">
            <div class="stat-box">
                <strong>Pico Presas</strong>
                <span>{presas_max:.2f} (Mes {mes_presas_max:.2f})</span>
            </div>
            <div class="stat-box">
                <strong>Valle Presas (Mínimo)</strong>
                <span>{presas_min:.2f} (Mes {mes_presas_min:.2f})</span>
            </div>
            <div class="stat-box" style="background: #fdf2f2; border-left-color: #d9534f;">
                <strong>Pico Depredadores</strong>
                <span style="color: #c9302c;">{dep_max:.2f} (Mes {mes_dep_max:.2f})</span>
            </div>
            <div class="stat-box" style="background: #fdf2f2; border-left-color: #d9534f;">
                <strong>Valle Depredadores</strong>
                <span style="color: #c9302c;">{dep_min:.2f} (Mes {mes_dep_min:.2f})</span>
            </div>
        </div>
        
        <div class="grafico">
            <h2 style="color: #666; font-size: 18px;">Series Temporales y Plano de Fase</h2>
            <img src="data:image/png;base64,{b64_img}" alt="Gráficos Lotka-Volterra" />
        </div>
    </div>
</body>
</html>
"""
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_html = os.path.join(directorio_actual, nombre_archivo)
    
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return ruta_html



def generar_reporte_calor_html(
    difusividad, tiempo_total, temp_max, temp_min, temp_prom, png_bytes, nombre_archivo
) -> str:
    """
    Genera un HTML autocontenido con la imagen térmica embebida en base64.
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte - Ecuación del Calor 2D</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f6f8; color: #333; }}
        .card {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #d9534f; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; font-size: 24px; }}
        .stats-container {{ display: flex; gap: 20px; margin: 20px 0; justify-content: space-between; flex-wrap: wrap; }}
        .stat-box {{ background: #fdf2f2; padding: 15px 20px; border-left: 4px solid #d9534f; border-radius: 6px; flex: 1; min-width: 200px; text-align: center; }}
        .stat-box strong {{ display: block; font-size: 13px; color: #777; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }}
        .stat-box span {{ font-size: 24px; font-weight: bold; color: #c9302c; }}
        .grafico {{ text-align: center; margin-top: 30px; }}
        .grafico img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Análisis Termodinámico: Difusión 2D</h1>
        
        <div class="stats-container">
            <div class="stat-box">
                <strong>Temp. Máxima Final</strong>
                <span>{temp_max:.2f} °C</span>
            </div>
            <div class="stat-box">
                <strong>Temp. Mínima Final</strong>
                <span>{temp_min:.2f} °C</span>
            </div>
            <div class="stat-box">
                <strong>Promedio Placa</strong>
                <span>{temp_prom:.2f} °C</span>
            </div>
        </div>
        
        <div class="grafico">
            <h2 style="color: #666; font-size: 18px;">Simulación para t = {tiempo_total}s | α = {difusividad}</h2>
            <img src="data:image/png;base64,{b64_img}" alt="Mapa de Calor 2D" />
        </div>
    </div>
</body>
</html>
"""
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_html = os.path.join(directorio_actual, nombre_archivo)
    
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return ruta_html


def generar_reporte_decaimiento_html(
    n0, lam, t_max, n_final, png_bytes, nombre_archivo
) -> str:
    """
    Genera un HTML autocontenido con la curva de decaimiento embebida en base64.
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte - Decaimiento Radiactivo</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f4f6f8; color: #333; }}
        .card {{ max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; font-size: 24px; }}
        .stats-container {{ display: flex; gap: 20px; margin: 20px 0; justify-content: space-between; flex-wrap: wrap; }}
        .stat-box {{ background: #f8f9fa; padding: 15px 20px; border-left: 4px solid #3498db; border-radius: 6px; flex: 1; min-width: 200px; text-align: center; }}
        .stat-box strong {{ display: block; font-size: 13px; color: #777; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 1px; }}
        .stat-box span {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
        .grafico {{ text-align: center; margin-top: 30px; }}
        .grafico img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.12); }}
    </style>
</head>
<body>
    <div class="card">
        <h1>Análisis Cinético: Decaimiento Radiactivo</h1>
        
        <div class="stats-container">
            <div class="stat-box">
                <strong>Cantidad Inicial ($N_0$)</strong>
                <span>{n0:.2f}</span>
            </div>
            <div class="stat-box">
                <strong>Constante ($\lambda$)</strong>
                <span>{lam:.4f}</span>
            </div>
            <div class="stat-box">
                <strong>Sustancia Restante</strong>
                <span>{n_final:.4f}</span>
            </div>
        </div>
        
        <div class="grafico">
            <h2 style="color: #666; font-size: 18px;">Simulación para t = {t_max}s</h2>
            <img src="data:image/png;base64,{b64_img}" alt="Curva de Decaimiento Radiactivo" />
        </div>
    </div>
</body>
</html>
"""
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_html = os.path.join(directorio_actual, nombre_archivo)
    
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return ruta_html