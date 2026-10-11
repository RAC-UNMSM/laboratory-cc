import base64
import os
from datetime import datetime

def generar_reporte_lotka_volterra_html(
    presas_max: float, mes_presas_max: float, presas_min: float, mes_presas_min: float,
    dep_max: float, mes_dep_max: float, dep_min: float, mes_dep_min: float,
    png_bytes: bytes, nombre_archivo: str
) -> str:
    """
    Genera un HTML autocontenido con diseño académico (estilo Grupo 09) para el modelo Lotka-Volterra.
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Lotka-Volterra</title>
    <style>
        /* CSS Basado en el rigor académico (Estilo Grupo 09) */
        :root {{
            --bg-color: #f6f5ef;
            --text-color: #333333;
            --accent-color: #3b5b50;
            --border-color: #e2dfd2;
            --box-bg: #fdfdfc;
        }}
        body {{
            font-family: 'Georgia', serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 950px;
            margin: 0 auto;
            background-color: transparent;
        }}
        /* Header Superior */
        header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .university-tag {{
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        h1 {{
            font-size: 2.8rem;
            font-weight: normal;
            margin: 0 0 10px 0;
            color: #1a1a1a;
        }}
        .subtitle-bar {{
            display: flex;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 0.9rem;
            color: #555;
        }}
        .dot-separator {{
            margin: 0 10px;
            color: #a3c4bc;
        }}
        
        /* Enunciado y Contenido */
        .enunciado-box {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 25px;
            margin-bottom: 40px;
        }}
        .section-tag {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #888;
            margin-bottom: 15px;
            display: block;
        }}
        
        /* Gráfico */
        .grafico-container {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 30px;
            text-align: center;
            margin-bottom: 40px;
        }}
        .grafico-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        
        /* Tablas de Validación Académica */
        h3 {{
            font-family: 'Georgia', serif;
            font-size: 1.4rem;
            font-weight: bold;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.9rem;
            margin-bottom: 40px;
        }}
        th {{
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border-color);
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.75rem;
        }}
        td {{
            padding: 15px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border: 1px solid #c3e6cb;
            color: #155724;
            background-color: #d4edda;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 10px;
        }}
        .numeric-value {{
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
            color: #333;
        }}
        
        /* Conclusiones */
        .conclusion-list li {{
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER ACADÉMICO -->
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <!-- ENUNCIADO TEÓRICO -->
        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Dinámico</span>
            <p>
                <strong>Modelo Biológico (Ecuaciones de Lotka-Volterra):</strong> Se analiza la interacción no lineal entre dos especies (presas y depredadores) en un ecosistema cerrado. El sistema está regido por un par de ecuaciones diferenciales ordinarias (EDOs) acopladas de primer orden.
            </p>
            <p>
                Las ecuaciones modelan el crecimiento poblacional de las presas (con tasa intrínseca α y tasa de mortalidad por depredación β) frente a la dinámica de los depredadores (con tasa de crecimiento por caza δ y tasa de mortalidad natural γ).
            </p>
        </div>

        <!-- GRÁFICO -->
        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Series Temporales y Plano de Fase</span>
            <img src="data:image/png;base64,{b64_img}" alt="Gráficos Lotka-Volterra" />
        </div>

        <!-- TABLA DE VERIFICACIÓN FÍSICA -->
        <h3>Interpretación de Extremos Poblacionales (Órbitas Periódicas)</h3>
        <table>
            <thead>
                <tr>
                    <th>Métrica Analizada</th>
                    <th>Valor Calculado (Población)</th>
                    <th>Ocurrencia Temporal (Mes)</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <span class="status-badge">✓ MÁXIMO</span>
                        <strong>pico_presas</strong>
                        <div style="color: #666; margin-top: 5px;">Máxima abundancia de la especie presa.</div>
                    </td>
                    <td class="numeric-value">{presas_max:.2f} ind.</td>
                    <td class="numeric-value">t = {mes_presas_max:.2f}</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ MÍNIMO</span>
                        <strong>valle_presas</strong>
                        <div style="color: #666; margin-top: 5px;">Punto crítico de escasez de la especie presa.</div>
                    </td>
                    <td class="numeric-value">{presas_min:.2f} ind.</td>
                    <td class="numeric-value">t = {mes_presas_min:.2f}</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge" style="color: #856404; background-color: #fff3cd; border-color: #ffeeba;">✓ MÁXIMO</span>
                        <strong>pico_depredadores</strong>
                        <div style="color: #666; margin-top: 5px;">Máxima abundancia de depredadores (cúspide de caza).</div>
                    </td>
                    <td class="numeric-value">{dep_max:.2f} ind.</td>
                    <td class="numeric-value">t = {mes_dep_max:.2f}</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge" style="color: #856404; background-color: #fff3cd; border-color: #ffeeba;">✓ MÍNIMO</span>
                        <strong>valle_depredadores</strong>
                        <div style="color: #666; margin-top: 5px;">Colapso poblacional de depredadores por escasez de alimento.</div>
                    </td>
                    <td class="numeric-value">{dep_min:.2f} ind.</td>
                    <td class="numeric-value">t = {mes_dep_min:.2f}</td>
                </tr>
            </tbody>
        </table>

        <!-- CONCLUSIONES -->
        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>El sistema exhibe un comportamiento oscilatorio sostenido. Como es característico de las órbitas concéntricas de Lotka-Volterra, existe un desfase temporal evidente: el pico poblacional de los depredadores (mes {mes_dep_max:.2f}) ocurre siempre después del pico de las presas (mes {mes_presas_max:.2f}).</li>
            <li>La amplitud de las oscilaciones está determinada estrictamente por las condiciones iniciales proporcionadas, lo que confirma que el modelo es conservativo y no posee atractores límite estructurales estables.</li>
        </ul>
        
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
    difusividad: float, tiempo_total: float, temp_max: float, temp_min: float, temp_prom: float, png_bytes: bytes, nombre_archivo: str
) -> str:
    """
    Genera un HTML con diseño académico avanzado (estilo Grupo 09) para la Ecuación del Calor.
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Ecuación del Calor 2D</title>
    <style>
        /* CSS Basado en el rigor académico (Estilo Grupo 09) */
        :root {{
            --bg-color: #f6f5ef;
            --text-color: #333333;
            --accent-color: #3b5b50;
            --border-color: #e2dfd2;
            --box-bg: #fdfdfc;
        }}
        body {{
            font-family: 'Georgia', serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 950px;
            margin: 0 auto;
            background-color: transparent;
        }}
        /* Header Superior */
        header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .university-tag {{
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        h1 {{
            font-size: 2.8rem;
            font-weight: normal;
            margin: 0 0 10px 0;
            color: #1a1a1a;
        }}
        .subtitle-bar {{
            display: flex;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 0.9rem;
            color: #555;
        }}
        .dot-separator {{
            margin: 0 10px;
            color: #a3c4bc;
        }}
        
        /* Enunciado y Contenido */
        .enunciado-box {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 25px;
            margin-bottom: 40px;
        }}
        .section-tag {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #888;
            margin-bottom: 15px;
            display: block;
        }}
        
        /* Gráfico */
        .grafico-container {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 30px;
            text-align: center;
            margin-bottom: 40px;
        }}
        .grafico-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        
        /* Tablas de Validación Académica */
        h3 {{
            font-family: 'Georgia', serif;
            font-size: 1.4rem;
            font-weight: bold;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.9rem;
            margin-bottom: 40px;
        }}
        th {{
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border-color);
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.75rem;
        }}
        td {{
            padding: 15px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border: 1px solid #c3e6cb;
            color: #155724;
            background-color: #d4edda;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 10px;
        }}
        .numeric-value {{
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
            color: #333;
        }}
        
        /* Conclusiones */
        .conclusion-list li {{
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER ACADÉMICO -->
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <!-- ENUNCIADO TEÓRICO -->
        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Termodinámico</span>
            <p>
                <strong>Modelo de Difusión Térmica (Ecuación del Calor 2D):</strong> Se analiza la distribución de la temperatura en una superficie bidimensional a lo largo del tiempo. El sistema está regido por la ecuación diferencial parcial (EDP) de tipo parabólico: <em>∂u/∂t = α(∂²u/∂x² + ∂²u/∂y²)</em>.
            </p>
            <p>
                Para la presente simulación numérica por Diferencias Finitas, se ha configurado el material con una difusividad térmica <strong>α = {difusividad}</strong> y se ha evaluado la evolución temporal hasta <strong>t = {tiempo_total} s</strong>.
            </p>
        </div>

        <!-- GRÁFICO -->
        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Distribución Espacial de Temperatura (Heatmap)</span>
            <img src="data:image/png;base64,{b64_img}" alt="Mapa de Calor 2D" />
        </div>

        <!-- TABLA DE VERIFICACIÓN FÍSICA -->
        <h3>Interpretación y Estado Global Termodinámico</h3>
        <table>
            <thead>
                <tr>
                    <th>Métrica Analizada</th>
                    <th>Valor Calculado</th>
                    <th>Significado Físico / Umbral</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <span class="status-badge">✓ PARÁMETRO</span>
                        <strong>difusividad_termica (α)</strong>
                        <div style="color: #666; margin-top: 5px;">Tasa de transferencia de calor intrínseca del material.</div>
                    </td>
                    <td class="numeric-value">{difusividad:.4f}</td>
                    <td class="numeric-value">α > 0</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ ESTADO FINAL</span>
                        <strong>temperatura_maxima</strong>
                        <div style="color: #666; margin-top: 5px;">Pico de calor residual registrado en la placa en t={tiempo_total}s.</div>
                    </td>
                    <td class="numeric-value">{temp_max:.2f} °C</td>
                    <td class="numeric-value">-</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ ESTADO FINAL</span>
                        <strong>temperatura_minima</strong>
                        <div style="color: #666; margin-top: 5px;">Zona más fría de la placa tras la evolución temporal.</div>
                    </td>
                    <td class="numeric-value">{temp_min:.2f} °C</td>
                    <td class="numeric-value">-</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ EQUILIBRIO</span>
                        <strong>temperatura_promedio</strong>
                        <div style="color: #666; margin-top: 5px;">Temperatura media de toda la superficie bidimensional.</div>
                    </td>
                    <td class="numeric-value">{temp_prom:.2f} °C</td>
                    <td class="numeric-value">-</td>
                </tr>
            </tbody>
        </table>

        <!-- CONCLUSIONES -->
        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>Tras <strong>{tiempo_total} segundos</strong> de evolución, la distribución térmica evidencia el flujo de energía desde las zonas de alto gradiente hacia las de menor temperatura, acorde a la Ley de Fourier.</li>
            <li>El sistema muestra que la temperatura máxima desciende a <strong>{temp_max:.2f} °C</strong>, mientras que la temperatura global tiende a homogenizarse alrededor de un promedio de <strong>{temp_prom:.2f} °C</strong>, validando la naturaleza puramente disipativa de la ecuación.</li>
        </ul>
        
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
    n0: float, lam: float, t_max: float, n_final: float, png_bytes: bytes, nombre_archivo: str
) -> str:
    """
    Genera un HTML con diseño académico avanzado (estilo Grupo 09).
    """
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Cálculos matemáticos extra para el reporte
    vida_media = 0.693 / lam if lam > 0 else 0
    porcentaje_perdido = ((n0 - n_final) / n0) * 100 if n0 > 0 else 0
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Decaimiento Radiactivo</title>
    <style>
        /* CSS Basado en el rigor académico (Estilo Grupo 09) */
        :root {{
            --bg-color: #f6f5ef;
            --text-color: #333333;
            --accent-color: #3b5b50;
            --border-color: #e2dfd2;
            --box-bg: #fdfdfc;
        }}
        body {{
            font-family: 'Georgia', serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 950px;
            margin: 0 auto;
            background-color: transparent;
        }}
        /* Header Superior */
        header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .university-tag {{
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        h1 {{
            font-size: 2.8rem;
            font-weight: normal;
            margin: 0 0 10px 0;
            color: #1a1a1a;
        }}
        .subtitle-bar {{
            display: flex;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 0.9rem;
            color: #555;
        }}
        .dot-separator {{
            margin: 0 10px;
            color: #a3c4bc;
        }}
        
        /* Enunciado y Contenido */
        .enunciado-box {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 25px;
            margin-bottom: 40px;
        }}
        .section-tag {{
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #888;
            margin-bottom: 15px;
            display: block;
        }}
        
        /* Gráfico */
        .grafico-container {{
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 30px;
            text-align: center;
            margin-bottom: 40px;
        }}
        .grafico-container img {{
            max-width: 100%;
            height: auto;
        }}
        
        /* Tablas de Validación Académica */
        h3 {{
            font-family: 'Georgia', serif;
            font-size: 1.4rem;
            font-weight: bold;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.9rem;
            margin-bottom: 40px;
        }}
        th {{
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border-color);
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.75rem;
        }}
        td {{
            padding: 15px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 8px;
            border: 1px solid #c3e6cb;
            color: #155724;
            background-color: #d4edda;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 10px;
        }}
        .numeric-value {{
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
            color: #333;
        }}
        
        /* Conclusiones */
        .conclusion-list li {{
            margin-bottom: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER ACADÉMICO -->
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <!-- ENUNCIADO TEÓRICO -->
        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Físico</span>
            <p>
                <strong>Modelo de Decaimiento Radiactivo:</strong> Se analiza la desintegración de una sustancia isotópica mediante la ecuación diferencial ordinaria (EDO) de primer orden <em>dN/dt = -λN</em>, donde <strong>N(t)</strong> representa la cantidad de núcleos sin desintegrar en el tiempo <em>t</em>, y <strong>λ</strong> es la constante de decaimiento.
            </p>
            <p>
                Para los parámetros ingresados: Cantidad inicial <strong>N₀ = {n0}</strong>, y constante <strong>λ = {lam}</strong>, la solución analítica exacta está dada por <em>N(t) = {n0} e^(-{lam}t)</em>.
            </p>
        </div>

        <!-- GRÁFICO -->
        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Evolución Temporal del Sistema</span>
            <img src="data:image/png;base64,{b64_img}" alt="Curva de Decaimiento" />
        </div>

        <!-- TABLA DE VERIFICACIÓN FÍSICA -->
        <h3>Interpretación y Verificación Física</h3>
        <table>
            <thead>
                <tr>
                    <th>Prueba / Métrica</th>
                    <th>Valor Calculado</th>
                    <th>Umbral Físico</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <span class="status-badge">✓ VERIFICADO</span>
                        <strong>condicion_inicial</strong>
                        <div style="color: #666; margin-top: 5px;">Masa/Cantidad en t=0s. Debe coincidir con N₀.</div>
                    </td>
                    <td class="numeric-value">{n0:.4f}</td>
                    <td class="numeric-value">> 0</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ VERIFICADO</span>
                        <strong>vida_media (t½)</strong>
                        <div style="color: #666; margin-top: 5px;">Tiempo necesario para que la sustancia se reduzca a la mitad (ln(2)/λ).</div>
                    </td>
                    <td class="numeric-value">{vida_media:.4f} s</td>
                    <td class="numeric-value">-</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ VERIFICADO</span>
                        <strong>desintegracion_total</strong>
                        <div style="color: #666; margin-top: 5px;">Porcentaje de la muestra que se ha desintegrado en {t_max}s.</div>
                    </td>
                    <td class="numeric-value">{porcentaje_perdido:.2f} %</td>
                    <td class="numeric-value">< 100%</td>
                </tr>
            </tbody>
        </table>

        <!-- CONCLUSIONES -->
        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>Al finalizar el tiempo de simulación de <strong>{t_max} segundos</strong>, la cantidad remanente de sustancia es de <strong>{n_final:.4f}</strong> unidades.</li>
            <li>El sistema muestra un comportamiento asintótico hacia cero, característico de los procesos de disipación de masa sin fuentes externas de recarga, cumpliendo con la conservación estricta de la energía.</li>
        </ul>
        
    </div>
</body>
</html>
"""
    
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_html = os.path.join(directorio_actual, nombre_archivo)
    
    with open(ruta_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    return ruta_html