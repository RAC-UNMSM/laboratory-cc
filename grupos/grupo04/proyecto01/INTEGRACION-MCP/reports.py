"""Exportación de informes web autocontenidos y PDF opcional."""
from __future__ import annotations

from html import escape
import re

from storage import STORAGE_DIR, artifact_path, ensure_storage

REPORT_DIR = STORAGE_DIR


def _safe_name(name):
    name = re.sub(r"[^\w.-]+", "_", str(name or "reporte_interpolacion"), flags=re.UNICODE).strip("._")
    return name[:80] or "reporte_interpolacion"


def _svg(result):
    width, height, pad = 900, 360, 48
    xs, ys = result["curve"]["x"], result["curve"]["y"]
    px = [p["x"] for p in result["points"]]
    py = [p["y"] for p in result["points"]]
    xlo, xhi = min(xs + px + [result["x_eval"]]), max(xs + px + [result["x_eval"]])
    ylo, yhi = min(ys + py + [result["value"]]), max(ys + py + [result["value"]])
    if yhi == ylo: ylo, yhi = ylo - 1, yhi + 1
    sx = lambda x: pad + (x - xlo) / (xhi - xlo or 1) * (width - 2 * pad)
    sy = lambda y: height - pad - (y - ylo) / (yhi - ylo) * (height - 2 * pad)
    path = " ".join(("M" if i == 0 else "L") + f"{sx(x):.2f},{sy(y):.2f}" for i, (x, y) in enumerate(zip(xs, ys)))
    points = "".join(f'<circle cx="{sx(x):.2f}" cy="{sy(y):.2f}" r="5" fill="#d28035"><title>({x:g}, {y:g})</title></circle>' for x, y in zip(px, py))
    ev = f'<circle cx="{sx(result["x_eval"]):.2f}" cy="{sy(result["value"]):.2f}" r="7" fill="#26856d"><title>Evaluación ({result["x_eval"]:g}, {result["value"]:.6g})</title></circle>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Gráfica del polinomio interpolante"><path d="M{pad},{pad}V{height-pad}H{width-pad}" fill="none" stroke="#cdd5df"/><path d="{path}" fill="none" stroke="#365fba" stroke-width="3"/><g fill="#526176" font-family="Arial,sans-serif" font-size="13">{points}{ev}<text x="{width/2}" y="{height-8}" text-anchor="middle">x</text><text x="14" y="20">f(x)</text></g></svg>'


def build_html(result, title="Reporte de interpolación"):
    rows = "".join(f"<tr><td>{i+1}</td><td>{p['x']:.8g}</td><td>{p['y']:.8g}</td></tr>" for i, p in enumerate(result["points"]))
    columns = max(0, len(result["points"]) - 1)
    headers = "".join(f"<th>Δ{order}</th>" for order in range(1, columns + 1))
    diff_rows = "".join("<tr>" + f"<td>{r['x']:.8g}</td><td>{r['f']:.8g}</td>" + "".join(f"<td>{r.get(f'd{order}', '—') if isinstance(r.get(f'd{order}'), str) else (format(r[f'd{order}'], '.8g') if f'd{order}' in r else '—')}</td>" for order in range(1, columns + 1)) + "</tr>" for r in result["difference_table"])
    safe_title = escape(title)
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe_title}</title><style>
      :root{{color-scheme:light;--ink:#172336;--muted:#627084;--line:#dce3eb;--accent:#365fba}}*{{box-sizing:border-box}}body{{margin:0;background:#f3f6fa;color:var(--ink);font:16px/1.5 system-ui,Segoe UI,sans-serif}}main{{max-width:1060px;margin:32px auto;padding:0 20px}}header,.card{{background:white;border:1px solid var(--line);border-radius:14px;padding:24px;margin-bottom:18px;box-shadow:0 5px 18px #1723360a}}h1,h2{{margin:0 0 12px}}h1{{font-size:clamp(1.6rem,4vw,2.2rem)}}h2{{font-size:1.15rem}}.muted{{color:var(--muted)}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.metric{{background:#f5f7fb;border-radius:10px;padding:14px}}.metric small{{display:block;color:var(--muted)}}.metric strong{{font-size:1.12rem;overflow-wrap:anywhere}}table{{border-collapse:collapse;width:100%;font-size:.93rem}}th,td{{padding:9px 11px;border-bottom:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}.scroll{{overflow:auto}}.chart{{width:100%;height:auto;min-height:240px}}code{{background:#f2f4f8;padding:4px 7px;border-radius:5px;overflow-wrap:anywhere}}@media print{{body{{background:white}}main{{margin:0;max-width:none}}header,.card{{box-shadow:none;break-inside:avoid}}}}
    </style></head><body><main><header><p class="muted">INTERPOLA-MCP · MCP-TEST</p><h1>{safe_title}</h1><p class="muted">Reporte de interpolación numérica · Método {escape(result['method'])}</p></header>
    <section class="card"><h2>Resultado</h2><div class="metrics"><div class="metric"><small>Valor interpolado</small><strong>P({result['x_eval']:.8g}) = {result['value']:.10g}</strong></div><div class="metric"><small>Polinomio</small><strong>P(x) = {escape(result['polynomial'])}</strong></div><div class="metric"><small>Comparación Newton / Lagrange</small><strong>{result['difference']:.4g}</strong></div><div class="metric"><small>Número de puntos</small><strong>{len(result['points'])}</strong></div></div></section>
    <section class="card"><h2>Gráfica</h2><p class="muted">Curva interpolante, puntos ingresados y evaluación indicada.</p>{_svg(result)}</section>
    <section class="card"><h2>Datos de entrada</h2><div class="scroll"><table><thead><tr><th>#</th><th>x</th><th>f(x)</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section class="card"><h2>Diferencias divididas de Newton</h2><div class="scroll"><table><thead><tr><th>x</th><th>f(x)</th>{headers}</tr></thead><tbody>{diff_rows}</tbody></table></div></section>
    <footer class="muted">Generado automáticamente por INTEGRACION-MCP. Archivo HTML autónomo, listo para guardar o publicar en un sitio web.</footer></main></body></html>'''


def generate_reports(result, name="reporte_interpolacion"):
    ensure_storage()
    stem = _safe_name(name)
    html_path = artifact_path(stem, ".html")
    svg_path = artifact_path(stem + "_grafica", ".svg")
    svg_markup = _svg(result)
    svg_path.write_text(svg_markup, encoding="utf-8")
    html_path.write_text(build_html(result, f"Reporte · {stem}"), encoding="utf-8")
    response = {
        "html": str(html_path.resolve()), "html_name": html_path.name,
        "html_url": f"/reports/{html_path.name}",
        "graph_svg": str(svg_path.resolve()), "graph_name": svg_path.name,
        "graph_url": f"/reports/{svg_path.name}",
        "pdf": None, "pdf_name": None, "pdf_status": "no_disponible",
    }
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.graphics.shapes import Drawing, PolyLine, Circle, String, Line
        from reportlab.graphics import renderPDF
        from reportlab.platypus import Flowable
        pdf_path = artifact_path(stem, ".pdf")
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, title=f"Reporte {stem}")
        styles = getSampleStyleSheet()
        story = [Paragraph(f"Reporte de interpolación · {escape(result['method'])}", styles["Title"]), Spacer(1, 12), Paragraph(f"P({result['x_eval']:.8g}) = {result['value']:.10g}", styles["Heading2"]), Paragraph(f"P(x) = {escape(result['polynomial'])}", styles["BodyText"]), Spacer(1, 12), Paragraph("Gráfica del polinomio", styles["Heading2"])]
        drawing = Drawing(480, 190)
        curve_x, curve_y = result["curve"]["x"], result["curve"]["y"]
        x_values = curve_x + [p["x"] for p in result["points"]] + [result["x_eval"]]
        y_values = curve_y + [p["y"] for p in result["points"]] + [result["value"]]
        x_min, x_max = min(x_values), max(x_values)
        y_min, y_max = min(y_values), max(y_values)
        if y_min == y_max:
            y_min, y_max = y_min - 1, y_max + 1
        sx = lambda x: 34 + (x - x_min) / (x_max - x_min or 1) * 430
        sy = lambda y: 24 + (y - y_min) / (y_max - y_min) * 145
        drawing.add(Line(34, 24, 464, 24, strokeColor=colors.HexColor("#a7b2c2")))
        drawing.add(Line(34, 24, 34, 169, strokeColor=colors.HexColor("#a7b2c2")))
        drawing.add(PolyLine([coord for pair in zip([sx(x) for x in curve_x], [sy(y) for y in curve_y]) for coord in pair], strokeColor=colors.HexColor("#365fba"), strokeWidth=2))
        for point in result["points"]:
            drawing.add(Circle(sx(point["x"]), sy(point["y"]), 3.5, fillColor=colors.HexColor("#d28035"), strokeColor=colors.white))
        drawing.add(Circle(sx(result["x_eval"]), sy(result["value"]), 5, fillColor=colors.HexColor("#19836f"), strokeColor=colors.white))
        drawing.add(String(200, 5, "x", fontSize=8, fillColor=colors.HexColor("#627084")))
        drawing.add(String(5, 170, "f(x)", fontSize=8, fillColor=colors.HexColor("#627084")))
        class DrawingFlowable(Flowable):
            def __init__(self, source):
                super().__init__()
                self.source = source
                self.width, self.height = source.width, source.height
            def draw(self):
                renderPDF.draw(self.source, self.canv, 0, 0)
        story.extend([DrawingFlowable(drawing), Spacer(1, 8), Paragraph("Puntos utilizados", styles["Heading2"])])
        data = [["#", "x", "f(x)"]] + [[str(i + 1), f"{p['x']:.8g}", f"{p['y']:.8g}"] for i, p in enumerate(result["points"])]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#365fba")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#ccd4df")), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5fa")])]))
        story.extend([table, Spacer(1, 16), Paragraph("Diferencias divididas de Newton", styles["Heading2"])])
        headings = ["x", "f(x)"] + [f"Δ{i}" for i in range(1, len(result["points"]))]
        diff_data = [headings] + [[f"{r['x']:.6g}", f"{r['f']:.6g}"] + [f"{r[f'd{j}']:.6g}" if f"d{j}" in r else "" for j in range(1, len(result["points"]))] for r in result["difference_table"]]
        dtable = Table(diff_data, repeatRows=1)
        dtable.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#365fba")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#ccd4df")), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
        story.append(dtable)
        doc.build(story)
        response.update({"pdf": str(pdf_path.resolve()), "pdf_name": pdf_path.name, "pdf_url": f"/reports/{pdf_path.name}", "pdf_status": "ok"})
    except ImportError:
        pass
    except Exception as exc:
        response["pdf_status"] = "error"
        response["pdf_error"] = str(exc)
    return response
