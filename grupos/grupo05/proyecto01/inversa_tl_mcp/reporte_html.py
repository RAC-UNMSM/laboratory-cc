"""Reporte autocontenido para estudiar y exponer los ejemplos sin conexión."""
import base64
from html import escape
from pathlib import Path


def tabla_matriz(filas, corte=None):
    return '<div class="matrix"><table>' + ''.join('<tr>'+''.join(
        f'<td class="{"cut" if j == corte else ""}">{escape(str(v))}</td>'
        for j,v in enumerate(fila))+'</tr>' for fila in filas) + '</table></div>'


def generar_reporte(r, hill, recuperado, png, destino):
    inv = r["inversa"]
    regla_texto = "(" + ", ".join(inv["regla_en_coordenadas_canonicas"]) + ")"
    pasos = ''.join(f'<details><summary>{i}. {escape(p["operacion"])}</summary>'
                    f'{tabla_matriz(p["matriz_aumentada"],r["columnas"])}</details>'
                    for i,p in enumerate(inv["pasos_gauss_jordan"]))
    bloques = ''.join('<tr>'+''.join(f'<td>{escape(str(p[k]))}</td>' for k in
                     ("bloque_entrada","vector_columna","producto_sin_modulo","residuos","bloque_salida"))+'</tr>'
                     for p in hill["pasos"])
    b64 = base64.b64encode(png).decode("ascii")
    html = f'''<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grupo 05 · Álgebra lineal y cifrado de matrices</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f4f6f9;color:#17283c;font:16px/1.6 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:40px 24px}}header{{background:#132c45;color:white;padding:36px;border-radius:18px}}
h1{{font-size:clamp(28px,4vw,42px);line-height:1.18;max-width:780px;margin:10px 0 18px}}h2{{font-size:26px;margin:0 0 12px}}
.tag{{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#78d5c6}}section{{background:white;padding:28px;margin-top:22px;border:1px solid #dce4ec;border-radius:16px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.item{{background:#f4f7fa;border-radius:12px;padding:18px}}
.matrix{{display:inline-block;overflow:auto;max-width:100%;border-left:2px solid #0d9488;border-right:2px solid #0d9488;margin:10px 0;padding:2px 8px}}
table{{border-collapse:collapse;max-width:100%;font-size:14px}}td,th{{padding:9px 14px;text-align:center;border-bottom:1px solid #dde5ee}}th{{background:#eef4f8}}.cut{{border-left:2px solid #64748b}}
code{{font-size:15px;color:#105f60;overflow-wrap:anywhere}}details{{padding:8px 14px;border:1px solid #dde5ee;border-radius:9px;margin:8px 0}}summary{{cursor:pointer;font-weight:600}}
.good{{color:#087b66;font-weight:600}}img{{width:100%;height:auto}}.scroll{{overflow:auto}}.flow{{font-size:26px;word-spacing:10px;color:#105f60;font-weight:700}}
footer{{margin:24px 0;color:#526578;font-size:13px}}@media(max-width:680px){{main{{padding:16px}}header,section{{padding:22px}}.grid{{grid-template-columns:1fr}}}}
@media print{{body{{background:white}}main{{padding:0}}section{{break-inside:avoid}}details{{break-inside:avoid}}}}
</style><main><header><div class="tag">UNMSM · Grupo 05 · Servidor MCP</div>
<h1>De la transformación lineal al cifrado con matrices</h1>
<p>Invertibilidad, bases y Gauss-Jordan. Una aplicación a mensajes mediante el cifrado Hill.</p></header>
<section><h2>1. Construir la transformación</h2><p>En el ejemplo del proyecto, T(x1,x2) = (2x1 + x2, x1 - x2).</p>
<div class="grid"><div class="item"><strong>Matriz estándar A</strong><br>{tabla_matriz(r['matriz_canonica'])}
<p>Sus columnas son T(e1) = (2,1) y T(e2) = (1,-1).</p></div>
<div class="item"><strong>¿Existe la inversa?</strong><p>det(A) = {escape(r['determinante'])}; rango(A) = {r['rango']}.</p>
<p class="good">El determinante es distinto de cero. T es biyectiva.</p><p>Dominio R2 y codominio R2: ambas dimensiones son 2.</p></div></div></section>
<section><h2>2. Invertir con Gauss-Jordan</h2><p>Partimos de [A | I] y operamos sobre filas hasta obtener [I | A⁻¹]. Abre cada paso para ver la matriz aumentada.</p>
{pasos}<div class="grid"><div class="item"><strong>Matriz inversa</strong><br>{tabla_matriz(inv['matriz_canonica'])}</div>
<div class="item"><strong>Transformación inversa</strong><p><code>T⁻¹(y1,y2) = {escape(regla_texto)}</code></p></div></div></section>
<section><h2>3. Comprobar y visualizar</h2><p class="good">A⁻¹ A = I y A A⁻¹ = I: ambas composiciones verificadas exactamente.</p>
<p>En el gráfico se observa la base, la cuadrícula y el vector v=(1,2). La inversa recupera el vector inicial.</p>
<img src="data:image/png;base64,{b64}" alt="Cuadrícula original y transformada, vectores de la base y vector 1,2"></section>
<section><h2>4. Cifrar un mensaje con Hill</h2><p>Alfabeto A=0, B=1, ..., Z=25. Separamos HOLA en bloques columna de dos letras y calculamos c = Kp mod 26.</p>
<div class="grid"><div class="item"><strong>Clave K</strong><br>{tabla_matriz(hill['clave'])}
<p>det(K) = {hill['determinante']}; mcd(det(K),26) = {hill['mcd_determinante_modulo']}.</p></div>
<div class="item"><strong>Inversa módulo 26</strong><br>{tabla_matriz(hill['clave_inversa'])}
<p>Para descifrar: p = K⁻¹ c mod 26.</p></div></div>
<div class="scroll"><table><thead><tr><th>Bloque</th><th>Vector p</th><th>Kp</th><th>mod 26</th><th>Cifrado</th></tr></thead><tbody>{bloques}</tbody></table></div>
<p class="flow">HOLA → {escape(hill['texto_cifrado'])} → {escape(recuperado['texto_descifrado'])}</p>
<p>Si se agrega relleno para completar un bloque, su cantidad se conserva para descifrar sin borrar letras originales.</p>
<p><strong>Uso educativo:</strong> Hill es un cifrado histórico vulnerable a texto conocido y no protege datos reales.</p></section>
<section><h2>5. Conectar las ideas</h2><p>En los números reales, det(A) ≠ 0 garantiza una inversa. En el cifrado módulo m, necesitamos mcd(det(K),m)=1.
Por ejemplo, una clave con determinante 2 es invertible sobre los reales, pero no módulo 26.</p>
<p>El servidor también admite polinomios Pn, matrices Mpxq y bases personalizadas; utiliza A = C⁻¹ M B para pasar entre coordenadas.</p></section>
<footer>Reporte generado con operaciones racionales exactas. Grupo 05 · Álgebra lineal · Redes, Arquitectura y Comunicaciones.</footer></main></html>'''
    destino = Path(destino)
    destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_text(html,encoding="utf-8")
    return destino
