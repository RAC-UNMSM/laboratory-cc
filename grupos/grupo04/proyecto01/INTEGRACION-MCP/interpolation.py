"""Motor de interpolación integrado desde INTERPOLA-MCP."""
from __future__ import annotations


def _normalize_points(points):
    if not isinstance(points, list):
        raise ValueError("Los puntos deben ser una lista.")
    clean = []
    for point in points:
        try:
            x, y = (point.get("x"), point.get("y")) if isinstance(point, dict) else point[:2]
            x, y = float(x), float(y)
        except (TypeError, ValueError, IndexError, KeyError) as exc:
            raise ValueError("Cada punto debe incluir valores numéricos x e y.") from exc
        if not (float("-inf") < x < float("inf") and float("-inf") < y < float("inf")):
            raise ValueError("Los puntos deben tener valores numéricos finitos.")
        clean.append((x, y))
    if len(clean) < 2:
        raise ValueError("Se necesitan al menos 2 puntos.")
    if len({x for x, _ in clean}) != len(clean):
        raise ValueError("Los valores de x no pueden repetirse.")
    return clean


def _divided_differences(points):
    xs = [x for x, _ in points]
    table = [[y for _, y in points]]
    for order in range(1, len(points)):
        previous = table[-1]
        table.append([(previous[i + 1] - previous[i]) / (xs[i + order] - xs[i]) for i in range(len(previous) - 1)])
    return xs, table


def _coefficients(points):
    coeffs = [0.0]
    for i, (xi, yi) in enumerate(points):
        basis, denominator = [1.0], 1.0
        for j, (xj, _) in enumerate(points):
            if i == j:
                continue
            nxt = [0.0] * (len(basis) + 1)
            for k, coef in enumerate(basis):
                nxt[k] -= xj * coef
                nxt[k + 1] += coef
            basis = nxt
            denominator *= xi - xj
        if len(coeffs) < len(basis):
            coeffs.extend([0.0] * (len(basis) - len(coeffs)))
        for k, coef in enumerate(basis):
            coeffs[k] += yi * coef / denominator
    return coeffs


def _format_polynomial(coeffs):
    terms = []
    for power, coef in reversed(list(enumerate(coeffs))):
        if abs(coef) < 1e-10:
            continue
        magnitude = abs(coef)
        atom = f"{magnitude:.6g}" if power == 0 else ("x" if abs(magnitude - 1) < 1e-10 else f"{magnitude:.6g}x") if power == 1 else (f"x^{power}" if abs(magnitude - 1) < 1e-10 else f"{magnitude:.6g}x^{power}")
        terms.append(("-" if coef < 0 else "+", atom))
    if not terms:
        return "0"
    return ("-" if terms[0][0] == "-" else "") + terms[0][1] + "".join(f" {sign} {atom}" for sign, atom in terms[1:])


def solve_interpolation(points, x_eval, method="lagrange"):
    points = _normalize_points(points)
    try:
        x_eval = float(x_eval)
    except (TypeError, ValueError) as exc:
        raise ValueError("El valor de evaluación debe ser numérico.") from exc
    if not float("-inf") < x_eval < float("inf"):
        raise ValueError("El valor de evaluación debe ser finito.")
    method = str(method).lower().strip()
    if method not in ("lagrange", "newton"):
        raise ValueError("El método debe ser 'lagrange' o 'newton'.")
    xs, table = _divided_differences(points)
    newton_value, product = table[0][0], 1.0
    for order in range(1, len(xs)):
        product *= x_eval - xs[order - 1]
        newton_value += table[order][0] * product
    basis = []
    lagrange_value = 0.0
    for i, (xi, yi) in enumerate(points):
        weight = 1.0
        for j, (xj, _) in enumerate(points):
            if i != j:
                weight *= (x_eval - xj) / (xi - xj)
        basis.append(weight)
        lagrange_value += yi * weight
    coeffs = _coefficients(points)
    rows = []
    for i, x in enumerate(xs):
        row = {"x": x, "f": points[i][1]}
        for order in range(1, len(xs) - i):
            row[f"d{order}"] = table[order][i]
        rows.append(row)
    lo, hi = min(xs), max(xs)
    margin = (hi - lo) * .08 or .5
    curve_x = [lo - margin + (hi - lo + 2 * margin) * i / 199 for i in range(200)]
    def evaluate(x):
        value = 0.0
        for coefficient in reversed(coeffs):
            value = value * x + coefficient
        return value
    lagrange_dev = []
    for i, (xi, yi) in enumerate(points):
        factors = [xj for j, (xj, _) in enumerate(points) if i != j]
        lagrange_dev.append({"index": i, "xi": xi, "yi": yi, "basis_value": basis[i], "contribution": yi * basis[i], "factors": factors})
    newton_dev = [{"order": order, "coefficient": table[order][0], "factors": xs[:order]} for order in range(len(xs))]
    difference = abs(lagrange_value - newton_value)
    return {
        "method": "Lagrange" if method == "lagrange" else "Newton", "x_eval": x_eval,
        "value": lagrange_value if method == "lagrange" else newton_value,
        "lagrange_value": lagrange_value, "newton_value": newton_value,
        "difference": difference, "error": difference, "polynomial": _format_polynomial(coeffs),
        "coefficients": coeffs, "basis": basis,
        "points": [{"x": x, "y": y} for x, y in points],
        "curve": {"x": curve_x, "y": [evaluate(x) for x in curve_x]},
        "difference_table": rows, "divided_differences": table,
        "lagrange_development": lagrange_dev, "newton_development": newton_dev,
    }
