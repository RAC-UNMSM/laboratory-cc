from flask import Flask, render_template, request, jsonify
from interpolation import solve_interpolation

app = Flask(__name__)

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "INTERPOLA-MCP", "mcp": True})

@app.post("/api/interpolate")
def interpolate():
    try:
        data = request.get_json(force=True)
        points = data.get("points", [])
        x_eval = float(data.get("x_eval"))
        method = data.get("method", "lagrange")
        result = solve_interpolation(points, x_eval, method)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
