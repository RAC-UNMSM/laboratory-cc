from pathlib import Path

import threading

from storage import persist_pdf

_PDF_LOCK = threading.Lock()


def generar_reporte_latex(result, report_name="interpolacion"):
    """Conserva la API histórica de interpolación y genera el PDF con ReportLab."""
    points = result.get("points") or []
    inputs = {"points": points, "x_eval": result.get("x_eval")}
    values = {key: result.get(key) for key in (
        "value", "polynomial", "lagrange_value", "newton_value", "difference")}
    difference_rows = result.get("difference_table") or []
    columns = ["x", "f(x)"]
    extra = sorted({key for row in difference_rows for key in row if key.startswith("d")},
                   key=lambda key: int(key[1:]) if key[1:].isdigit() else 0)
    columns.extend(extra)
    tables = [{"name": "Puntos utilizados", "columns": ["x", "f(x)"],
               "rows": [[point.get("x"), point.get("y")] for point in points]}]
    if difference_rows:
        tables.append({"name": "Diferencias divididas", "columns": columns,
                       "rows": [[row.get(column) for column in columns]
                                for row in difference_rows]})
    curve = result.get("curve") or {}
    charts = ([{"name": "Polinomio interpolante", "series": [
        {"label": "P(x)", "x": curve.get("x", []), "y": curve.get("y", [])},
        {"label": "Puntos", "type": "scatter",
         "x": [p.get("x") for p in points], "y": [p.get("y") for p in points]}]}]
        if curve.get("x") and curve.get("y") else [])
    normalized = {"schema_version": "1.1", "level": result.get("level", "inicial"),
        "problem_type": "interpolacion", "method": result.get("method", "Interpolación"),
        "status": "success", "inputs": inputs, "result": values,
        "diagnostics": {"difference": result.get("difference")},
        "steps": ["Se construyó el polinomio interpolante.",
                  f"Se evaluó en x={result.get('x_eval')}.",
                  f"P(x)={result.get('polynomial')}.",
                  f"Resultado: {result.get('value')}."],
        "tables": tables, "charts": charts, "warnings": []}
    return generar_reporte_numerico(normalized, report_name)


def _generar_reporte_numerico_unlocked(result, report_name="resolucion_numerica"):
    """Genera un informe PDF común para cualquier familia del MCP."""
    import json
    import math
    import tempfile
    from pathlib import Path
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Preformatted
    )
    from reportlab.graphics.shapes import Drawing, String, Line, PolyLine, Rect

    def text(value, limit=1800):
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=True, indent=2)
        output = str(value)
        replacements = {"−": "-", "₂": "2", "₁": "1", "⁴": "^4",
                        "²": "^2", "→": "->", "≈": "~", "≤": "<=",
                        "≥": ">=", "λ": "lambda", "α": "alpha",
                        "π": "pi", "·": "*", "…": "..."}
        for source, target in replacements.items():
            output = output.replace(source, target)
        return output if len(output) <= limit else output[:limit] + "\n... (contenido resumido)"

    def paragraph(value, style):
        return Paragraph(escape(text(value)).replace("\n", "<br/>"), style)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallMono", parent=styles["Code"],
                              fontName="Courier", fontSize=7, leading=9,
                              wordWrap="CJK", spaceAfter=2))
    styles.add(ParagraphStyle(name="SectionBlue", parent=styles["Heading2"],
                              textColor=colors.HexColor("#174a7e"), spaceBefore=8))
    story = []
    story.append(Paragraph("Informe de resolución numérica", styles["Title"]))
    story.append(Paragraph(
        f"Familia: {escape(str(result.get('problem_type', 'problema')))}"
        f" &nbsp; | &nbsp; Método: {escape(str(result.get('method', '')))}"
        f" &nbsp; | &nbsp; Nivel: {escape(str(result.get('level', 'inicial')))}"
        f" &nbsp; | &nbsp; Estado: {escape(str(result.get('status', '')))}",
        styles["Normal"]))
    story.append(Spacer(1, 5 * mm))

    for key, label in (("inputs", "Datos de entrada"),
                       ("result", "Resultado"),
                       ("diagnostics", "Diagnóstico")):
        value = result.get(key)
        if value is not None:
            story.append(Paragraph(label, styles["SectionBlue"]))
            story.append(Preformatted(text(value), styles["SmallMono"]))

    steps = result.get("steps") or []
    if steps:
        story.append(Paragraph("Desarrollo", styles["SectionBlue"]))
        for i, step in enumerate(steps, 1):
            story.append(paragraph(f"{i}. {step}", styles["BodyText"]))

    for item in (result.get("tables") or [])[:5]:
        columns = item.get("columns") or []
        rows = item.get("rows") or []
        if not columns:
            continue
        story.append(Paragraph(escape(str(item.get("name", "Tabla"))),
                               styles["SectionBlue"]))
        data = [[paragraph(v, styles["BodyText"]) for v in columns]]
        for row in rows[:60]:
            data.append([paragraph(v, styles["SmallMono"]) for v in row[:len(columns)]])
        col_width = (A4[0] - 36 * mm) / len(columns)
        tab = Table(data, colWidths=[col_width] * len(columns), repeatRows=1,
                    hAlign="LEFT")
        tab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce8f5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17365d")),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#aab4bf")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f4f7fa")]),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(tab)
        story.append(Spacer(1, 3 * mm))
        if len(rows) > 60:
            story.append(paragraph("Tabla recortada a 60 filas en este PDF.",
                                   styles["Italic"]))

    chart_data = None
    chart_title = "Datos"
    charts = result.get("charts") or []
    for chart in charts:
        candidates = [series for series in (chart.get("series") or [])
                      if series.get("x") and series.get("y")]
        if candidates:
            chart_data = candidates[0]
            chart_title = str(chart.get("name", chart_title))
            break
    heatmap = next((chart for chart in charts
                    if chart.get("type") == "heatmap" and chart.get("z")), None)
    if heatmap:
        grid = heatmap.get("z") or []
        valid = []
        for row in grid:
            for value in row:
                try: number = float(value)
                except (TypeError, ValueError, OverflowError): continue
                if math.isfinite(number): valid.append(number)
        if valid and grid:
            low, high = min(valid), max(valid)
            rows_n = len(grid)
            cols_n = max((len(row) for row in grid), default=0)
            row_step = max(1, math.ceil(rows_n/30))
            col_step = max(1, math.ceil(cols_n/30))
            sample = [row[::col_step][:30] for row in grid[::row_step][:30]]
            sample_rows = len(sample); sample_cols = max((len(row) for row in sample), default=0)
            drawing = Drawing(470, 230)
            left, bottom, width, height = 55, 40, 350, 150
            cell_w, cell_h = width/max(1,sample_cols), height/max(1,sample_rows)
            for j, row in enumerate(sample):
                for i, value in enumerate(row):
                    try: number = float(value)
                    except (TypeError, ValueError, OverflowError): continue
                    t = (number-low)/(high-low) if high != low else 0.5
                    drawing.add(Rect(left+i*cell_w, bottom+j*cell_h,
                        cell_w+0.3, cell_h+0.3,
                        fillColor=colors.Color(0.15+0.75*t, 0.35, 0.85-0.7*t),
                        strokeColor=None))
            drawing.add(Line(left, bottom, left, bottom+height,
                             strokeColor=colors.HexColor("#68778a")))
            drawing.add(Line(left, bottom, left+width, bottom,
                             strokeColor=colors.HexColor("#68778a")))
            drawing.add(String(left, 210, text(heatmap.get("name", "Mapa de calor"), 120),
                               fontSize=9, fillColor=colors.HexColor("#333333")))
            drawing.add(String(left+width-35, 20, text(heatmap.get("x_label", "x"), 20),
                               fontSize=8, fillColor=colors.HexColor("#555555")))
            drawing.add(String(12, bottom+height-5, text(heatmap.get("y_label", "y"), 20),
                               fontSize=8, fillColor=colors.HexColor("#555555")))
            story.append(Paragraph("Mapa de calor", styles["SectionBlue"]))
            story.append(drawing)
    elif chart_data:
        raw_x, raw_y = chart_data.get("x", []), chart_data.get("y", [])
        pairs = []
        for x_value, y_value in zip(raw_x, raw_y):
            try:
                px, py = float(x_value), float(y_value)
            except (TypeError, ValueError, OverflowError):
                continue
            if math.isfinite(px) and math.isfinite(py):
                pairs.append((px, py))
        if pairs:
            if len(pairs) > 300:
                stride = max(1, len(pairs) // 300)
                pairs = pairs[::stride][:300]
            xmin, xmax = min(p[0] for p in pairs), max(p[0] for p in pairs)
            ymin, ymax = min(p[1] for p in pairs), max(p[1] for p in pairs)
            if xmin == xmax: xmin, xmax = xmin-1, xmax+1
            if ymin == ymax: ymin, ymax = ymin-1, ymax+1
            drawing = Drawing(470, 230)
            left, bottom, width, height = 48, 38, 385, 155
            drawing.add(Line(left, bottom, left, bottom+height,
                             strokeColor=colors.HexColor("#68778a")))
            drawing.add(Line(left, bottom, left+width, bottom,
                             strokeColor=colors.HexColor("#68778a")))
            scaled = [(left+(x-xmin)/(xmax-xmin)*width,
                       bottom+(y-ymin)/(ymax-ymin)*height) for x,y in pairs]
            flat_points = [coordinate for pair in scaled for coordinate in pair]
            if len(flat_points) >= 4:
                drawing.add(PolyLine(flat_points, strokeColor=colors.HexColor("#1769aa"),
                                     strokeWidth=1.6))
            drawing.add(String(left, 210, text(chart_title, 120), fontSize=9,
                               fillColor=colors.HexColor("#333333")))
            drawing.add(String(left, 20, text(f"x: {xmin:.5g} a {xmax:.5g}", 80),
                               fontSize=7, fillColor=colors.HexColor("#555555")))
            drawing.add(String(left+width-120, 20, text(f"y: {ymin:.5g} a {ymax:.5g}", 80),
                               fontSize=7, fillColor=colors.HexColor("#555555")))
            story.append(Paragraph("Gráfica", styles["SectionBlue"]))
            story.append(drawing)

    warnings = result.get("warnings") or []
    if warnings:
        story.append(Paragraph("Advertencias y límites", styles["SectionBlue"]))
        for warning in warnings:
            story.append(paragraph("• " + str(warning), styles["BodyText"]))

    story.append(Spacer(1, 4 * mm))
    story.append(paragraph(
        "El resultado es una aproximación numérica. Revise el método, los parámetros "
        "y el diagnóstico antes de usarlo en una aplicación sensible.",
        styles["Italic"]))

    with tempfile.TemporaryDirectory() as temp:
        pdf_path = Path(temp) / "resultado.pdf"
        document = SimpleDocTemplate(
            str(pdf_path), pagesize=A4,
            rightMargin=18 * mm, leftMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
            title="Informe de resolución numérica",
            author="grupo04-mcp-test")
        document.build(story)
        return persist_pdf(pdf_path, report_name)


def generar_reporte_numerico(result, report_name="resolucion_numerica"):
    """Serializa el renderizado PDF para mantener acotado el pico de memoria."""
    with _PDF_LOCK:
        return _generar_reporte_numerico_unlocked(result, report_name)
