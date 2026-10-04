"""Aplicación web integrada: formulario, cálculo y descarga de informes."""
from flask import Flask, jsonify, render_template, request, send_from_directory

from interpolation import solve_interpolation
from reports import generate_reports
from storage import ensure_storage, list_artifacts

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "INTEGRACION-MCP", "mcp_tools": ["resolver_interpolacion", "interpolacion_lagrange", "interpolacion_newton", "comparar_interpolacion"]})


@app.post("/api/interpolate")
def interpolate():
    try:
        data = request.get_json(silent=True) or {}
        result = solve_interpolation(data.get("points", []), data.get("x_eval"), data.get("method", "lagrange"))
        result["reports"] = generate_reports(result, data.get("report_name", "reporte_interpolacion")) if data.get("generate_report", True) else None
        return jsonify(result)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Error al procesar una interpolación")
        return jsonify({"error": "No fue posible completar el cálculo. Revisa los datos e inténtalo otra vez."}), 500


@app.get("/reports/<path:filename>")
def get_report(filename):
    from pathlib import Path
    if Path(filename).name != filename or filename.startswith("."):
        return jsonify({"error": "Nombre de reporte inválido."}), 400
    return send_from_directory(ensure_storage(), filename, as_attachment=False, download_name=filename)


@app.get("/api/reports")
def list_reports():
    items = [{"name": p.name, "url": f"/reports/{p.name}", "type": p.suffix.lstrip(".").upper(), "updated": p.stat().st_mtime} for p in list_artifacts()]
    return jsonify({"reports": items})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
