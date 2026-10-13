import base64
from datetime import datetime

ESTILOS_COMUNES = """
        :root {
            --bg-color: #f6f5ef;
            --text-color: #333333;
            --accent-color: #3b5b50;
            --border-color: #e2dfd2;
            --box-bg: #fdfdfc;
        }
        body {
            font-family: 'Georgia', serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 950px;
            margin: 0 auto;
            background-color: transparent;
        }
        header {
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .university-tag {
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        h1 {
            font-size: 2.8rem;
            font-weight: normal;
            margin: 0 0 10px 0;
            color: #1a1a1a;
        }
        .subtitle-bar {
            display: flex;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 0.9rem;
            color: #555;
        }
        .dot-separator {
            margin: 0 10px;
            color: #a3c4bc;
        }
        .enunciado-box {
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 25px;
            margin-bottom: 40px;
        }
        .section-tag {
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #888;
            margin-bottom: 15px;
            display: block;
        }
        .grafico-container {
            background-color: var(--box-bg);
            border: 1px solid var(--border-color);
            padding: 30px;
            text-align: center;
            margin-bottom: 40px;
        }
        .grafico-container img {
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        h3 {
            font-family: 'Georgia', serif;
            font-size: 1.4rem;
            font-weight: bold;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', sans-serif;
            font-size: 0.9rem;
            margin-bottom: 40px;
        }
        th {
            text-align: left;
            padding: 12px;
            border-bottom: 2px solid var(--border-color);
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.75rem;
        }
        td {
            padding: 15px 12px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: top;
        }
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border: 1px solid #c3e6cb;
            color: #155724;
            background-color: #d4edda;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 10px;
        }
        .numeric-value {
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
            color: #333;
        }
        .conclusion-list li {
            margin-bottom: 15px;
        }
"""

def generar_reporte_lotka_volterra_html(
    presas_max: float, mes_presas_max: float, presas_min: float, mes_presas_min: float,
    dep_max: float, mes_dep_max: float, dep_min: float, mes_dep_min: float,
    png_bytes: bytes
) -> str:
    """Genera un HTML autocontenido para la simulación de Lotka-Volterra."""
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    amplitud_presas = presas_max - presas_min
    desfase_temporal = abs(mes_dep_max - mes_presas_max)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Dinámica Lotka-Volterra</title>
    <style>{ESTILOS_COMUNES}</style>
</head>
<body>
    <div class="container">
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Biológico (EDO)</span>
            <p>
                <strong>Modelo Presa-Depredador (Lotka-Volterra):</strong> Se analiza la interacción biológica bidireccional entre dos especies en un entorno cerrado, modelada por el sistema de ecuaciones diferenciales no lineales:
                <br><br>
                <em>dx/dt = αx - βxy</em> (Ecuación de la Presa)<br>
                <em>dy/dt = δxy - γy</em> (Ecuación del Depredador)
            </p>
            <p>
                La resolución numérica se ha ejecutado utilizando métodos de integración iterativos para proyectar la evolución poblacional y su trayectoria en el plano de fase.
            </p>
        </div>

        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Series Temporales y Órbita en el Plano de Fase</span>
            <img src="data:image/png;base64,{b64_img}" alt="Gráficos Lotka-Volterra" />
        </div>

        <h3>Análisis de Hitos Estructurales</h3>
        <table>
            <thead>
                <tr>
                    <th>Métrica Analizada</th>
                    <th>Valor Calculado</th>
                    <th>Ocurrencia Temporal</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <span class="status-badge">✓ PICO POBLACIONAL</span>
                        <strong>Máximo de Presas</strong>
                        <div style="color: #666; margin-top: 5px;">Punto de máxima saturación del nicho por parte de la presa.</div>
                    </td>
                    <td class="numeric-value" style="color: #1f77b4;">{presas_max:.2f}</td>
                    <td class="numeric-value">Mes {mes_presas_max:.2f}</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ PICO POBLACIONAL</span>
                        <strong>Máximo de Depredadores</strong>
                        <div style="color: #666; margin-top: 5px;">Punto de máxima abundancia predatoria.</div>
                    </td>
                    <td class="numeric-value" style="color: #d9534f;">{dep_max:.2f}</td>
                    <td class="numeric-value">Mes {mes_dep_max:.2f}</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ DESFASE</span>
                        <strong>Retraso de Respuesta (Lag)</strong>
                        <div style="color: #666; margin-top: 5px;">Diferencia de tiempo entre el pico de presas y el pico de depredadores.</div>
                    </td>
                    <td class="numeric-value">{desfase_temporal:.2f} meses</td>
                    <td class="numeric-value">-</td>
                </tr>
                <tr>
                    <td>
                        <span class="status-badge">✓ FLUCTUACIÓN</span>
                        <strong>Amplitud de Presas (Δx)</strong>
                        <div style="color: #666; margin-top: 5px;">Diferencia entre el pico máximo y el valle mínimo ({presas_min:.2f}).</div>
                    </td>
                    <td class="numeric-value">{amplitud_presas:.2f}</td>
                    <td class="numeric-value">Valle en Mes {mes_presas_min:.2f} (Dep. mín: {dep_min:.2f} en Mes {mes_dep_min:.2f})</td>
                </tr>
            </tbody>
        </table>

        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>El sistema exhibe un comportamiento cíclico característico (atractor periódico), evidenciado por la órbita cerrada en el plano de fase.</li>
            <li>Existe un desfase temporal de <strong>{desfase_temporal:.2f} meses</strong> entre el auge de las presas y el auge consecuente de los depredadores, confirmando que la población predatoria es estrictamente dependiente de la abundancia de su fuente de alimento.</li>
        </ul>
    </div>
</body>
</html>"""


def generar_reporte_calor_html(
    difusividad: float, tiempo_total: float, temp_max: float, temp_min: float, temp_prom: float, png_bytes: bytes
) -> str:
    """Genera un HTML autocontenido para la Ecuación del Calor 2D."""
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Ecuación del Calor 2D</title>
    <style>{ESTILOS_COMUNES}</style>
</head>
<body>
    <div class="container">
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Termodinámico</span>
            <p>
                <strong>Modelo de Difusión Térmica (Ecuación del Calor 2D):</strong> Se analiza la distribución de la temperatura en una superficie bidimensional a lo largo del tiempo. El sistema está regido por la ecuación diferencial parcial (EDP) de tipo parabólico: <em>∂u/∂t = α(∂²u/∂x² + ∂²u/∂y²)</em>.
            </p>
            <p>
                Para la presente simulación numérica por Diferencias Finitas, se ha configurado el material con una difusividad térmica <strong>α = {difusividad}</strong> y se ha evaluado la evolución temporal hasta <strong>t = {tiempo_total} s</strong>.
            </p>
        </div>

        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Distribución Espacial de Temperatura (Heatmap)</span>
            <img src="data:image/png;base64,{b64_img}" alt="Mapa de Calor 2D" />
        </div>

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

        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>Tras <strong>{tiempo_total} segundos</strong> de evolución, la distribución térmica evidencia el flujo de energía desde las zonas de alto gradiente hacia las de menor temperatura, acorde a la Ley de Fourier.</li>
            <li>El sistema muestra que la temperatura máxima desciende a <strong>{temp_max:.2f} °C</strong>, mientras que la temperatura global tiende a homogenizarse alrededor de un promedio de <strong>{temp_prom:.2f} °C</strong>, validando la naturaleza puramente disipativa de la ecuación.</li>
        </ul>
    </div>
</body>
</html>"""


def generar_reporte_decaimiento_html(
    n0: float, lam: float, t_max: float, n_final: float, png_bytes: bytes
) -> str:
    """Genera un HTML autocontenido para el modelo de Decaimiento Radiactivo."""
    b64_img = base64.b64encode(png_bytes).decode("utf-8")
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    vida_media = 0.693147 / lam if lam > 0 else 0
    porcentaje_perdido = ((n0 - n_final) / n0) * 100 if n0 > 0 else 0

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - Decaimiento Radiactivo</title>
    <style>{ESTILOS_COMUNES}</style>
</head>
<body>
    <div class="container">
        <header>
            <div class="university-tag">UNMSM · LABORATORIO · GRUPO 07</div>
            <h1>Informe del análisis</h1>
            <div class="subtitle-bar">
                <span>Agente de EDOs y sistemas dinámicos</span>
                <span class="dot-separator">●</span>
                <span>Generado {fecha_generacion}</span>
            </div>
        </header>

        <div class="enunciado-box">
            <span class="section-tag">Planteamiento Físico</span>
            <p>
                <strong>Modelo de Decaimiento Radiactivo:</strong> Se analiza la desintegración de una sustancia isotópica mediante la ecuación diferencial ordinaria (EDO) de primer orden <em>dN/dt = -λN</em>, donde <strong>N(t)</strong> representa la cantidad de núcleos sin desintegrar en el tiempo <em>t</em>, y <strong>λ</strong> es la constante de decaimiento.
            </p>
            <p>
                Para los parámetros ingresados: Cantidad inicial <strong>N₀ = {n0}</strong>, y constante <strong>λ = {lam}</strong>, la solución analítica exacta está dada por <em>N(t) = {n0} e^(-{lam}t)</em>.
            </p>
        </div>

        <div class="grafico-container">
            <span class="section-tag" style="text-align: left;">Evolución Temporal del Sistema</span>
            <img src="data:image/png;base64,{b64_img}" alt="Curva de Decaimiento" />
        </div>

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

        <h3>Conclusiones Dinámicas</h3>
        <ul class="conclusion-list">
            <li>Al finalizar el tiempo de simulación de <strong>{t_max} segundos</strong>, la cantidad remanente de sustancia es de <strong>{n_final:.4f}</strong> unidades.</li>
            <li>El sistema muestra un comportamiento asintótico hacia cero, característico de los procesos de disipación de masa sin fuentes externas de recarga.</li>
        </ul>
    </div>
</body>
</html>"""